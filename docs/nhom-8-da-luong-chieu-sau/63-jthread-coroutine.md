# Bài 63 — jthread, stop_token và coroutine (C++20): nhận biết

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::jthread` (C++20): luồng tự `join` khi bị hủy, kèm `stop_token` để báo dừng theo kiểu hợp tác. Nói được nó bớt cho bạn những việc thủ công nào so với `std::thread` cộng cờ `atomic<bool>` của [Bài 28](../nhom-3-da-luong/28-atomic.md), và giới hạn của nó (`request_stop` không giết luồng).
    - Đánh thức luồng đang ngủ trong `condition_variable_any` bằng `stop_token` (cờ `atomic` không làm được), và nhận ra `stop_callback`.
    - Hiểu coroutine ở mức khái niệm: hàm tạm dừng được rồi chạy tiếp; `co_await`, `co_yield`, `co_return` là gì; trạng thái nằm ở "khung" thường trên heap. Chạy thật một generator nhỏ và một tác vụ nhỏ trên g++ 11 với `-std=c++20`.
    - Phân biệt coroutine với luồng (coroutine không tự song song), so stackful (goroutine) với stackless (coroutine C++) mà không nói sai về Go, và nói đúng mức về `std::execution` (senders/receivers): chỉ biết tên.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, hủy `thread` còn joinable gọi `std::terminate`, `sleep_for`, `std::chrono`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, TSan), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, `unique_lock`, `wait` có vị từ), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic<bool>` làm cờ dừng), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, hàm hủy), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (cú pháp `<...>` của template), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`= delete`, hàm tạo di chuyển, `noexcept`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda và `[&]`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, heap, `struct`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (sanitizer).

!!! note "Cờ biên dịch của bài này"
    `jthread`, `stop_token` và coroutine là **C++20**. Khóa này kiểm mọi khối code bằng `-std=c++17`, nên khối nào cần C++20 đều mở bằng dòng `// bo-qua-kiem-tra` (checker bỏ qua, không phải vì code sai). Mình đã tự biên dịch và chạy từng khối bằng `g++ -std=c++20 -Wall -pthread` (g++ 11.4); mọi đầu ra bên dưới là đầu ra thật của lần chạy đó, và các khối có luồng cũng sạch với `-fsanitize=thread`. Với g++ 11 thì `-std=c++20` là đủ cho coroutine, không cần thêm `-fcoroutines`; mình thử `-std=c++20 -fno-coroutines` thì header `<coroutine>` báo lỗi, còn `-std=c++17` trơn cũng báo `#error "the coroutine header requires -fcoroutines"`.

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp nhiều đầu bếp**. Ở [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) và [Bài 28](../nhom-3-da-luong/28-atomic.md), muốn một đầu bếp nền nghỉ việc đúng giờ, bạn làm ba việc bằng tay: treo một **chuông dừng bếp** (cờ `atomic<bool>`), dặn đầu bếp nhìn chuông, và nhớ đứng chờ (`join`) trước khi rời quầy. Quên việc cuối là chương trình chết bằng `std::terminate`.

C++20 bán sẵn **đầu bếp có dây đeo tự báo** (`std::jthread`): chuông dừng đã gắn kèm, và khi trưởng bếp rời quầy thì dây tự rung chuông rồi tự đứng chờ. Phần hai của bài là chuyện khác hẳn: **công thức có thể gác dở**. Đầu bếp ghi chỗ đang làm vào một **phiếu**, cất phiếu vào kho (heap), đi làm việc khác, lúc nào rảnh lấy phiếu ra làm tiếp. Đó là coroutine.

!!! info "Chỗ nào ví von không còn đúng?"
    Chuông dừng chỉ **nhờ**, không ép: đầu bếp đang nhào bột mà không nhìn chuông thì cứ nhào tiếp. Phiếu gác dở **không phải một đầu bếp mới**: không có thêm tay nào làm việc, ai cầm phiếu lên thì người đó làm tiếp. Và phiếu chỉ ghi dở ở **đúng công thức đó**; công thức con mà đầu bếp gọi ra (như "đi mua hành") không gác dở giữa chừng được. Mục 7 giải thích vì sao.

## 📖 Giải thích

### 1. Cách cũ: luồng, cờ và `join` làm bằng tay

Chương trình dưới đây là mẫu của [Bài 28](../nhom-3-da-luong/28-atomic.md), chạy được với C++17. Ba việc bạn tự lo được đánh số: cờ ở (1), kiểm cờ ở (2), `join` ở (5).

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

std::atomic<bool> dung{false};             // (1) cờ dừng tự quản

void luongNen() {
    while (!dung.load()) {                 // (2) mỗi vòng kiểm cờ
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

int main() {
    std::thread t(luongNen);               // (3) quên join/detach là std::terminate
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    dung.store(true);                      // (4) báo dừng
    t.join();                              // (5) chờ
    std::cout << "luong nen da dung\n";
    return 0;
}
```

**Kết quả khi chạy** (nhiều lần liền đều như nhau; TSan sạch, mã thoát 0; cả `-std=c++17` lẫn `-std=c++20`): một dòng `luong nen da dung`.

Cờ là biến toàn cục nên mọi luồng phải biết tên nó; muốn dừng riêng từng luồng thì phải tự làm một cờ cho mỗi luồng. `jthread` gom ba việc này vào một chỗ.

### 2. `std::jthread` và `std::stop_token`

`std::jthread` (`#include <thread>`, C++20, "joining thread" = luồng tự join) dùng như `std::thread` nhưng khác ở ba chỗ. Một: **hàm hủy của nó gọi `request_stop()` rồi `join()`**, nên không bao giờ `terminate` vì quên `join`. Hai: nó **sở hữu một "yêu cầu dừng"**. Ba: nếu hàm của luồng nhận `std::stop_token` làm **tham số đầu tiên**, `jthread` tự đưa token vào; hàm không nhận token vẫn chạy bình thường.

`std::stop_token` (`#include <stop_token>`) là "đèn báo dừng": chỉ đọc được, sao chép thoải mái, đọc từ nhiều luồng không gây data race. Hàm `stop_requested()` trả `true` khi ai đó đã yêu cầu dừng. Đèn nối với một **nút bấm** là `std::stop_source`; `jthread` có sẵn nút đó, bấm bằng `t.request_stop()`. Đã bấm thì không bỏ bấm được: yêu cầu dừng chỉ đi một chiều.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <stop_token>
#include <thread>

void luongNen(std::stop_token tk) {        // (1) tham số ĐẦU là stop_token: jthread tự đưa vào
    while (!tk.stop_requested()) {         // (2) hỏi "có ai yêu cầu dừng chưa?"
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

int main() {
    std::jthread t(luongNen);              // (3) không truyền gì, token vẫn tới được hàm
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    t.request_stop();                      // (4) bấm nút dừng (không chờ luồng xong)
    t.join();                              // (5) chờ; bỏ dòng này cũng được: ~jthread tự làm
    std::cout << "luong nen da dung\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Yêu cầu dừng lúc này |
|---|---|---|
| (3) | Luồng nền bắt đầu, nhận token từ `jthread` | chưa có |
| (2) | Luồng nền lặp: `stop_requested()` là `false`, ngủ 1 ms | chưa có |
| (4) | Luồng chính bấm nút; không chặn | đã có |
| (2)(5) | Vòng sau luồng nền thấy `true`, thoát hàm; `join` trả về | đã có |

**Kết quả khi chạy** (`-std=c++20`; nhiều lần liền đều như nhau; TSan sạch ở `-O0` và `-O2`, mã thoát 0):

```text
luong nen da dung
```

**Thử thay đổi (mình đã chạy cả ba):**

- *Bỏ dòng (4), giữ `join`:* chương trình **treo**; với `timeout 3` thì mã 124. Vì `join` ở (5) chờ luồng nền, mà không ai bấm nút nên luồng nền không bao giờ thoát. `jthread` chỉ tự bấm nút ở hàm hủy, không tự bấm trước `join` do bạn gọi.
- *Bỏ cả dòng (4) lẫn (5):* thoát ngay (mình đo cỡ 0,025 s), không treo. Hàm hủy `~jthread` gọi `request_stop()` rồi `join()` thay bạn.
- *Đổi `std::jthread` thành `std::thread`:* lỗi biên dịch, trong đó có `'class std::thread' has no member named 'request_stop'` (`std::thread` không có hàm này) và `static assertion failed: std::thread arguments must be invocable after conversion to rvalues`. Lỗi thứ hai là vì `std::thread` không biết đưa token vào: hàm đòi một `stop_token` mà không ai đưa thì không gọi được.

Mình chạy thêm một chương trình riêng: hai `jthread` chạy `viec(std::stop_token tk, int id)` trong một khối `{ }` đều tự dừng và `join` khi ra khỏi khối (`jthread a(viec, 1)` truyền `1` cho `id`, token tự đứng trước); `jthread` chạy lambda không nhận token vẫn bình thường; `request_stop()` trả `true` ở lần đầu, `false` ở lần hai.

!!! warning "Hay nhầm"
    `request_stop()` **không giết luồng và không ngắt hàm đang chạy**. Nó chỉ lật đèn báo. Luồng đang `sleep_for(10s)` hay đang chờ đọc dữ liệu mà không nhìn token thì vẫn ngủ hết hoặc chờ hết. Dừng ở C++ luôn là **hợp tác**: luồng phải tự hỏi. `jthread` cũng không làm hàm hủy nhanh hơn: nó vẫn chờ luồng thoát.

### 3. Đánh thức luồng đang ngủ: `condition_variable_any` + `stop_token`

Luồng nền hay ngủ chờ việc trong `cv.wait` ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)). Cờ `atomic<bool>` không đánh thức được ai: mình chạy bản dùng `std::thread`, cờ `atomic` và `condition_variable` (luồng nền `cv.wait` với vị từ đọc cờ; luồng chính chỉ đặt cờ, **không `notify`**): `join` treo, `timeout 3` cho mã 124. Muốn dừng đúng thì phải đặt cờ **và** `notify`, đúng thứ tự, đúng khóa.

C++20 cho `std::condition_variable_any` (bản của `condition_variable` chịu nhận mọi loại khóa) thêm cách gọi `wait(lk, tk, vi_tu)`: ngủ tới khi vị từ đúng **hoặc** có yêu cầu dừng, và `request_stop()` tự đánh thức luồng đang ngủ trong đó. Trả về giá trị của vị từ ở lúc dậy.

Mình chạy một chương trình riêng để thấy: luồng nền `jthread` giữ `unique_lock` rồi `cv.wait(lk, tk, [] { return coViec; })` với `coViec` không bao giờ thành `true`; luồng chính ngủ 50 ms rồi `t.request_stop()`. Kết quả: luồng nền **dậy**, `wait` trả `false` (vị từ vẫn sai, dậy vì yêu cầu dừng), `join` xong, mã thoát 0; `-std=c++20`, nhiều lần liền như nhau, TSan sạch ở `-O0` và `-O2`. Ví dụ đầy đủ, dùng đúng cách gọi này cho một hàng đợi việc, nằm ở phần 💻.

### 4. `stop_callback`: chỉ nhắc

`std::stop_callback cb(tk, hamNao);` đăng ký một hàm để **gọi khi có yêu cầu dừng**; dùng để đánh thức thứ không biết đọc token (đóng một socket, báo một `cv` khác). Hàm đó chạy ngay **trong luồng gọi `request_stop()`**, và nếu yêu cầu dừng đã có từ trước lúc đăng ký thì chạy **ngay lúc đăng ký**.

Mình chạy với `stop_source` và `stop_token` (`nguon.get_token()`) trong một luồng: đầu ra cho thấy callback chạy trên đúng luồng bấm nút (so số định danh luồng `std::this_thread::get_id()`, mục 6, ra `1`), chạy trước khi `request_stop()` trả về, và callback đăng ký muộn chạy tức thì. Callback nên ngắn và không ném ngoại lệ: mình thử ném từ callback thì in `terminate called after throwing an instance of 'std::runtime_error'` (mã 134), ngoại lệ không bay ra chỗ `request_stop()`.

### 5. Coroutine: hàm tạm dừng được

Hàm thường chạy từ đầu tới `return` một mạch; lúc nó chạy, biến cục bộ nằm trên stack, và `return` xóa hết. **Coroutine** là hàm được phép **tạm dừng giữa chừng và chạy tiếp sau**, với biến cục bộ còn nguyên. Hàm trở thành coroutine khi thân có một trong ba từ khóa:

| Từ khóa | Nghĩa |
|---|---|
| `co_yield giaTri` | đưa một giá trị ra cho người gọi rồi **tạm dừng** (generator) |
| `co_await bieuThuc` | **tạm dừng** chờ một thứ; khi thứ đó sẵn sàng thì chạy tiếp ngay chỗ này |
| `co_return giaTri` | kết thúc coroutine, có thể kèm kết quả |

Vì tạm dừng xong còn phải chạy tiếp, nơi cất trạng thái (biến cục bộ, chỗ đang dừng) không thể là stack của hàm gọi. Trình biên dịch cấp một **khung coroutine** (coroutine frame) và thường đặt nó trên **heap**. Chuẩn cho phép bỏ cấp phát khi trình biên dịch chứng minh được khung không sống quá người gọi; mình thử `-O0` và `-O2` thì cả hai đều vẫn cấp phát.

C++20 chỉ cho **bộ khung ngôn ngữ**: bạn tự viết kiểu trả về với một kiểu lồng tên chính xác là `promise_type` ("sổ ghi chép" của coroutine), cùng vài hàm mà trình biên dịch sẽ gọi vào các lúc cố định. Thư viện chuẩn C++20 gần như chỉ có header `<coroutine>`. `std::generator` là C++23, và g++ 11 của mình không có: `#include <generator>` báo `fatal error: generator: No such file or directory` (cả `-std=c++20` lẫn `-std=c++2b`). Vì thế dưới đây ta tự viết, và thấy tận mắt từng mảnh.

Ba từ mới sẽ xuất hiện: `std::suspend_always` ("lúc này hãy dừng"), `std::suspend_never` ("đừng dừng") và `std::coroutine_handle<promise_type>` (**tay cầm** điều khiển một coroutine: `resume()` chạy tiếp, `done()` hỏi đã xong chưa, `destroy()` giải phóng khung, `promise()` mở sổ ghi chép). Đoạn dưới còn dùng `std::exchange(a, {})` (đặt `a` về rỗng và trả giá trị cũ của `a`) để "chuyển" tay cầm sang đối tượng mới như hàm tạo di chuyển ở [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md).

Mấy chỗ cú pháp trong code: `return {};` trả một đối tượng vừa tạo mặc định (ở đây là `suspend_always`); `from_promise(*this)` dựng tay cầm từ chính sổ ghi chép; `explicit` trước hàm tạo chỉ cấm C++ tự đổi kiểu ngầm sang `Generator`.

```cpp
// bo-qua-kiem-tra
#include <coroutine>
#include <iostream>
#include <utility>

struct Generator {                                    // (1) kiểu trả về của coroutine
    struct promise_type {                             // (2) "sổ ghi chép", tên bắt buộc
        int giaTri = 0;                               //     chỗ co_yield đặt số vào
        Generator get_return_object() {               // (3) tạo Generator trả cho người gọi
            return Generator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        std::suspend_always initial_suspend() { return {}; }          // (4) tạo xong thì DỪNG ngay
        std::suspend_always final_suspend() noexcept { return {}; }   // (5) chạy hết thì dừng để ta dọn
        std::suspend_always yield_value(int v) {      // (6) co_yield v: cất v rồi dừng
            giaTri = v;
            return {};
        }
        void return_void() {}                         // (7) thân chạy hết, không co_return giá trị
        void unhandled_exception() { std::terminate(); }              // (8) ngoại lệ thoát khỏi thân
    };

    std::coroutine_handle<promise_type> tay;          // (9) tay cầm điều khiển coroutine

    explicit Generator(std::coroutine_handle<promise_type> h) : tay(h) {}
    Generator(Generator&& other) noexcept : tay(std::exchange(other.tay, {})) {}
    Generator(const Generator&) = delete;
    ~Generator() { if (tay) tay.destroy(); }          // (10) giải phóng khung coroutine

    bool tiep() {                                     // (11) chạy tới co_yield kế tiếp
        tay.resume();
        return !tay.done();
    }
    int giaTri() const { return tay.promise().giaTri; }
};

Generator fibonacci(int n) {                          // (12) thân có co_yield => đây là coroutine
    long long a = 0, b = 1;
    for (int i = 0; i < n; ++i) {
        co_yield static_cast<int>(a);                 // (13) đưa a ra ngoài, TẠM DỪNG tại đây
        long long c = a + b;
        a = b;
        b = c;
    }
}

int main() {
    Generator g = fibonacci(10);                      // (14) chưa chạy dòng nào của thân
    while (g.tiep()) {                                // (15) mỗi lần: chạy tới co_yield kế tiếp
        std::cout << g.giaTri() << " ";
    }
    std::cout << "\n";
    return 0;
}
```

**Chạy từng dòng** (địa chỉ minh họa, máy bạn sẽ in số khác)

| Dòng | Chuyện gì xảy ra | Khung coroutine (heap) |
|---|---|---|
| (14) | Gọi `fibonacci(10)`: cấp khung, tạo `promise`, (3) tạo `g`; (4) bảo dừng ngay. Trả `g` về `main` | `0x5000: n=10, dừng ở "đầu thân"` |
| (15)(11) | `resume()`: chạy từ đầu, `a=0`, `b=1`; tới (13) `co_yield 0` gọi (6), cất `giaTri=0`, dừng | `0x5000: a=0 b=1 i=0, dừng ở (13)` |
| (15)(11) | `resume()` lần hai: chạy tiếp ngay sau (13): `a=1`, `b=1`, `i=1`; `co_yield 1` | `a=1 b=1 i=1, dừng ở (13)` |
| ... | Cứ thế ra `1 2 3 5 8 13 21 34` | cùng một khung, biến đổi dần |
| lần thứ 11 | `i` tới 10, vòng `for` hết, thân chạy hết: (7), rồi (5) dừng lại; `done()` là `true`, `tiep` trả `false` | `0x5000: đã xong` |
| hết `main` | `~Generator`: (10) `destroy()` giải phóng khung | đã trả |

**Kết quả khi chạy** (`-std=c++20`; cả `-fsanitize=address,undefined` ở `-O0` và `-O2`: sạch, mã thoát 0):

```text
0 1 1 2 3 5 8 13 21 34 
```

Hai điều đáng chú ý. Một: `co_yield x` được trình biên dịch dịch thành `co_await promise.yield_value(x)`, nên hàm (6) mới là chỗ bạn quyết định chuyện gì xảy ra. Hai: vì (4) là `suspend_always`, coroutine này **lười**: gọi `fibonacci(10)` chưa chạy dòng nào của thân, chỉ `resume` mới chạy.

Thứ tự trình biên dịch gọi khi bạn gọi `fibonacci(10)`: cấp khung, `get_return_object`, `initial_suspend`; thân chạy; mỗi `co_yield` gọi `yield_value`; hết thân thì `return_void`, rồi `final_suspend`.

**Thử thay đổi (mình đã chạy):**

- *Bỏ `tay.destroy()` ở (10), biên dịch với `-fsanitize=address`:* chương trình vẫn in đúng dãy số, nhưng LeakSanitizer báo `Direct leak of 88 byte(s) in 1 object(s)` rồi `SUMMARY: AddressSanitizer: 88 byte(s) leaked in 1 allocation(s)`, dấu vết trỏ vào `fibonacci`. Khung nằm trên heap thì ai không giải phóng là rò rỉ. 88 byte là khung của generator nhỏ này (mình in thử bằng một `operator new` khai trong `promise_type`: `operator new(88)`, cả `-O0` lẫn `-O2`); khung to hay nhỏ tùy biến cục bộ.

### 6. `co_await` và `co_return`; coroutine không phải luồng

`co_await e` hỏi biểu thức `e` (gọi là **awaiter**, "thứ được chờ") qua ba hàm: `await_ready()` (trả `true` thì khỏi dừng), `await_suspend(h)` (chạy **sau khi** coroutine đã dừng, `h` là tay cầm của chính coroutine; kiểu `std::coroutine_handle<>` để trống là tay cầm không cần biết `promise_type`, vẫn `resume()` được), `await_resume()` (chạy khi coroutine được đánh thức; giá trị trả về là giá trị của cả biểu thức `co_await`). `suspend_always` là awaiter có `await_ready` trả `false`; `suspend_never` trả `true`.

Chương trình dưới dùng `co_await` và `co_return` và trả lời câu hỏi lớn nhất: coroutine chạy ở **luồng nào**? Coroutine `viec` ghi lại `id` luồng đang chạy nó ở ba chỗ (`std::this_thread::get_id()` trả một giá trị kiểu `std::thread::id` để so sánh). Giữa chừng nó `co_await` một awaiter tự viết có `await_suspend` **khởi một luồng mới** để chạy tiếp coroutine.

```cpp
// bo-qua-kiem-tra
#include <coroutine>
#include <iostream>
#include <thread>
#include <utility>

struct Task {
    struct promise_type {
        int ketQua = 0;
        Task get_return_object() {
            return Task{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        std::suspend_never initial_suspend() { return {}; }      // (1) chạy ngay tới co_await đầu tiên
        std::suspend_always final_suspend() noexcept { return {}; }
        void return_value(int v) { ketQua = v; }                 // (2) co_return v: cất v
        void unhandled_exception() { std::terminate(); }
    };
    std::coroutine_handle<promise_type> tay;
    explicit Task(std::coroutine_handle<promise_type> h) : tay(h) {}
    Task(Task&& o) noexcept : tay(std::exchange(o.tay, {})) {}
    ~Task() { if (tay) tay.destroy(); }
};

struct ChuyenLuong {                                 // (3) một awaiter: thứ đứng sau co_await
    std::jthread& noiGiu;                            //     chỗ giữ luồng mới (nằm NGOÀI coroutine)
    bool await_ready() const noexcept { return false; }          // (4) false = "hãy tạm dừng"
    void await_suspend(std::coroutine_handle<> h) {              // (5) coroutine đã dừng; h là tay cầm của nó
        noiGiu = std::jthread([h] { h.resume(); });              // (6) luồng MỚI chạy tiếp coroutine
    }
    void await_resume() const noexcept {}                        // (7) chạy khi coroutine được đánh thức
};

std::thread::id dau, giua, cuoi;

Task viec(std::jthread& giu) {
    dau = std::this_thread::get_id();                // (8) chạy ngay trong lúc main gọi viec(...)
    co_await std::suspend_always{};                  // (9) dừng; main sẽ resume bằng tay
    giua = std::this_thread::get_id();
    co_await ChuyenLuong{giu};                       // (10) dừng; luồng mới sẽ resume
    cuoi = std::this_thread::get_id();
    co_return 42;                                    // (11)
}

int main() {
    std::jthread giu;
    Task t = viec(giu);                              // (12) chạy tới (9) rồi trả quyền về main
    std::cout << "sau lan goi: done = " << t.tay.done() << "\n";
    t.tay.resume();                                  // (13) main chạy tiếp coroutine, tới (10)
    giu.join();                                      // (14) chờ luồng mới chạy nốt
    std::cout << "done = " << t.tay.done() << ", ket qua = " << t.tay.promise().ketQua << "\n";
    std::cout << "dau == giua: " << (dau == giua) << ", dau == cuoi: " << (dau == cuoi) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Luồng đang chạy thân |
|---|---|---|
| (12)(8) | `main` gọi `viec`; (1) bảo đừng dừng đầu thân nên chạy luôn: ghi `dau`; tới (9) thì dừng, quyền về `main` | luồng `main` |
| (13) | `main` gọi `resume()`: ghi `giua`; tới (10): `await_ready` false, dừng; (5) khởi luồng mới ở (6), rồi `resume()` của `main` trả về | luồng `main` |
| (6)(7) | Luồng mới gọi `h.resume()`: (7) chạy, rồi ghi `cuoi` và `co_return 42` cất `ketQua`; (final_suspend) dừng lại | luồng **mới** |
| (14) | `join` chờ luồng mới xong | — |

**Kết quả khi chạy** (`-std=c++20`; sáu lần liền đều như nhau; TSan sạch ở `-O0` và `-O2`; ASan và UBSan sạch):

```text
sau lan goi: done = 0
done = 1, ket qua = 42
dau == giua: 1, dau == cuoi: 0
```

Đây là điểm cốt lõi. Ở (9), `main` tự gọi `resume()` thì coroutine chạy tiếp **ngay trên luồng của `main`** (`dau == giua`). Ở (10), luồng mới gọi `resume()` thì cùng coroutine ấy chạy tiếp ở **luồng khác** (`dau != cuoi`). Coroutine không có luồng riêng; **ai gọi `resume()` thì thân chạy trên luồng người đó**. Tạm dừng thì luồng được trả lại để làm việc khác, đó là cái lợi: chờ mà không giữ luồng. Một lưu ý: mỗi lần coroutine dừng chỉ được có **một** bên gọi `resume`, không để hai luồng cùng `resume` một coroutine. Ở đây (9) chỉ `main` gọi, (10) chỉ luồng mới gọi, và `main` chỉ đụng lại coroutine sau `join`.

### 7. Stackful và stackless, so với Go

Hai cách làm "hàm tạm dừng được". **Stackful** (có stack riêng): mỗi coroutine giữ **cả một stack**, nên tạm dừng được ở bất kỳ độ sâu nào của chuỗi hàm gọi.

**Stackless** (không có stack riêng): chỉ giữ **khung của chính hàm coroutine**; hàm thường mà coroutine gọi chạy trên stack của luồng đang `resume`, và stack đó sẽ không còn khi coroutine dừng. Vì vậy hàm thường mà coroutine gọi không có cách nào dừng coroutine bên trên. Mình thử viết `co_await` trong một hàm trả `int`: `error: unable to find the promise type for this coroutine`, vì hàm có `co_await` bị coi là một coroutine khác, cần kiểu trả về riêng.

|  | goroutine của Go (stackful) | coroutine C++20 (stackless) |
|---|---|---|
| Thứ được giữ khi dừng | cả stack riêng, nhỏ lúc đầu và tự lớn | chỉ khung của coroutine |
| Chỗ được dừng | bất kỳ độ sâu hàm gọi | chỉ tại `co_await`/`co_yield` trong thân coroutine |
| Ai lập lịch | runtime của Go, trên nhiều luồng hệ điều hành | không ai: người gọi `resume()` quyết định |
| Tự chạy song song | có | không |

!!! info "Bạn biết Go?"
    Mọi con số dưới đây mình chạy với Go 1.27.2 (linux/amd64); đổi theo máy và phiên bản.

    - **Goroutine là stackful, và có bộ lập lịch của runtime.** Mình viết `tren` gọi `giua` gọi `sau`, hàm `sau` chặn ở `ch <- 1`: goroutine dừng ở độ sâu ba lần gọi rồi chạy tiếp được. Với coroutine C++ thì hàm `giua` thường không dừng được coroutine bên trên (đoạn trên).
    - **Rẻ nhưng không miễn phí:** mình mở 100000 goroutine cùng chờ: `StackInuse` tăng khoảng 205 triệu byte, trung bình khoảng **2050 byte mỗi goroutine** (bản `-race` thì cỡ 4100). So với 88 byte mỗi khung generator ở mục 5: khung C++ nhỏ hơn nhiều, vì chỉ giữ biến của một hàm. Hai con số không so công bằng được hoàn toàn, vì khung đổi theo hàm còn stack Go tự lớn.
    - **Goroutine bị ngắt được, coroutine C++ thì không:** mình đặt `GOMAXPROCS(1)`, chạy một goroutine `for {}` rồi `main` ngủ 50 ms: `main` vẫn tỉnh và in tiếp. Coroutine C++ chỉ nhường ở `co_await`; một coroutine không bao giờ `co_await` sẽ giữ luồng đến hết.
    - **Cặp tương đương:** `go` + `context.WithCancel` + `sync.WaitGroup` ≈ `jthread` + `stop_token` (mình chạy: goroutine thoát khi `ctx` bị hủy, `wg.Wait()` chờ xong). Khác chỗ: Go **không tự chờ** goroutine khi hàm thoát, bạn phải gọi `wg.Wait()`; `jthread` thì tự `join` ở hàm hủy.
    - **Generator của C++ ≈ `iter.Seq` của Go, không phải goroutine + channel:** `func(yield func(int) bool)` với `for v := range fibonacci(10)` (từ Go 1.23) in `0 1 1 2 3 5 8 13 21 34`; `iter.Pull` biến nó thành `next()`/`stop()` kéo từng giá trị, tương ứng `tiep()` ở trên (mình chạy cả hai, ra cùng dãy).

### 8. `std::execution` (senders/receivers): chỉ nhắc tên

Hướng tương lai là mô hình **senders/receivers** trong `std::execution`, dự kiến thuộc **C++26**: mô tả "việc sẽ làm" rồi gắn nó vào nơi chạy (luồng, pool) theo kiểu ghép khối, để phối hợp luồng và coroutine. Mình **không chạy** gì về nó và không dạy ở đây. Lưu ý trùng tên: trên g++ 11, `#include <execution>` là của **thuật toán song song C++17** (mình chạy `std::sort(std::execution::seq, ...)`: biên dịch và chạy được), còn `std::execution::sender_tag` báo `is not a member of 'std::execution'`.

### 9. Chọn gì, và khi nào KHÔNG dùng

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Luồng nền sống lâu, cần dừng sạch (C++20) | `jthread` + `stop_token` | tự `join`, token đi kèm, không cần cờ toàn cục |
| Luồng nền ngủ trong `cv` chờ việc | `condition_variable_any` + `stop_token` | `request_stop()` đánh thức; cờ `atomic` thì không |
| Chỉ có C++17 | `thread` + `atomic<bool>` + lớp bọc `join` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) | `jthread` không có |
| Chia việc tính toán lên nhiều lõi | luồng (`jthread`, `async`) | coroutine không tự chạy song song |
| Nhiều việc chờ I/O, mỗi việc "chờ rồi làm tiếp", không muốn mỗi việc một luồng | coroutine **kèm thư viện** hay vòng lặp sự kiện ([Bài 50](../nhom-6-he-dieu-hanh-tien-trinh/50-io-epoll-event-loop.md)) | mỗi việc chỉ tốn một khung nhỏ, chờ không giữ luồng |
| Dãy giá trị sinh lười | coroutine (C++23 có `std::generator`; g++ 11 chưa) | gọn hơn tự giữ trạng thái |

**Khi KHÔNG dùng coroutine:** việc tính toán thuần CPU (không có gì để chờ); code đồng bộ đơn giản chạy tốt rồi; khi nhóm chưa có thư viện hạ tầng, vì tự viết `promise_type` và quản lý vòng đời khung dễ sai (hai lỗi ở phần ⚠️). **Khi KHÔNG dùng `jthread`:** trình biên dịch chỉ C++17; hoặc khi bạn thật sự cần `detach`; và nó không thay được việc thiết kế điểm kiểm token đủ dày trong vòng lặp.

## 💻 Ví dụ code

### Hàng đợi việc dừng bằng `stop_token`: làm nốt việc còn lại rồi thoát

Mẫu thường hỏi: một luồng thợ lấy việc từ hàng đợi; tắt dịch vụ thì thợ phải **làm nốt việc còn trong hàng** rồi thoát, không bỏ việc, không treo. Với `jthread` và `condition_variable_any` ([Bài 27](../nhom-3-da-luong/27-condition-variable.md) cộng mục 3), cả việc dừng lẫn việc `join` nằm ở hàm hủy.

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>
#include <stop_token>
#include <thread>

class HangDoi {
public:
    void day(int v) {
        {
            std::lock_guard<std::mutex> giu(khoa);
            hang.push(v);
        }
        cv.notify_one();                              // (1) báo "có việc"
    }
    bool lay(std::stop_token tk, int& v) {            // (2) false = hết việc VÀ đã có yêu cầu dừng
        std::unique_lock<std::mutex> lk(khoa);
        if (!cv.wait(lk, tk, [this] { return !hang.empty(); })) return false;   // (3)
        v = hang.front();
        hang.pop();
        return true;
    }
private:
    std::mutex khoa;
    std::condition_variable_any cv;
    std::queue<int> hang;
};

int main() {
    HangDoi hd;
    std::atomic<long long> tong{0};
    {
        std::jthread tho([&](std::stop_token tk) {    // (4) lambda nhận token, jthread tự đưa vào
            int v;
            while (hd.lay(tk, v)) tong += v;          // (5) làm tới khi hết việc và có yêu cầu dừng
        });
        for (int i = 1; i <= 100; ++i) hd.day(i);     // (6) đẩy 100 việc: 1..100
    }                                                 // (7) ~jthread: request_stop() rồi join()
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Hàng đợi |
|---|---|---|
| (6)(1) | `main` đẩy việc và báo; thợ dậy lấy việc ở (3) khi hàng không rỗng | có việc |
| (7) | Hết khối: `~jthread` bấm dừng rồi `join`. Hàng còn việc thì vị từ ở (3) đúng, `wait` trả `true`, thợ vẫn lấy tiếp | đang vơi |
| (3)(2) | Hàng rỗng và đã có yêu cầu dừng: vị từ sai, `wait` trả `false`, `lay` trả `false` | rỗng |
| (5) | Vòng `while` thoát; thợ kết thúc; `join` xong; `main` in tổng | rỗng |

**Kết quả khi chạy** (`-std=c++20`; chạy 300 lần liền, lần nào cũng như nhau; TSan sạch ở `-O0` và `-O2`):

```text
tong = 5050
```

`5050` là tổng 1 đến 100: không việc nào bị bỏ, dù yêu cầu dừng có thể tới khi hàng còn việc. Chỗ quyết định là `wait` với token trả **giá trị của vị từ**, không trả "đã bị dừng". Nếu bạn muốn **bỏ** việc còn lại khi dừng, hãy kiểm `tk.stop_requested()` trong vòng `while` trước khi lấy tiếp.

### Bản SAI: coroutine giữ tham chiếu tới thứ đã chết

Tham số của coroutine được sao chép vào khung, nhưng tham số kiểu **tham chiếu** thì chỉ sao chép cái tham chiếu, không sao chép thứ nó trỏ tới. Với coroutine lười (mục 5), thân chạy **sau** lúc gọi, khi chuỗi tạm đã chết. Dùng lại nguyên kiểu `Generator` của mục 5 (cộng `#include <string>`) cho một coroutine khác:

```cpp
// bo-qua-kiem-tra
// ... Generator y như ở mục 5, thêm #include <string> ...
Generator doDai(const std::string& s) {              // (1) nhận THAM CHIẾU tới chuỗi
    co_yield static_cast<int>(s.size());              // (2) dùng s SAU khi bị tạm dừng một lần
}

int main() {
    Generator g = doDai(std::string(40, 'x'));        // (3) chuỗi tạm chết ngay khi hết câu lệnh này
    while (g.tiep()) {                                // (4) chạy thân: s đã treo
        std::cout << g.giaTri() << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Chuỗi `s` |
|---|---|---|
| (3) | Tạo chuỗi tạm, `doDai` dừng ngay đầu thân (lười), rồi hết câu lệnh nên chuỗi tạm bị hủy | đã chết |
| (4)(2) | `tiep()` chạy thân, đọc `s.size()` trên chuỗi đã chết | tham chiếu treo |

Mình chạy hai bản. Không sanitizer (`-O0`): in `40`, **đúng do may** vì chỗ nhớ chưa bị ghi đè. Với `-fsanitize=address -g`: dừng và báo `ERROR: AddressSanitizer: stack-use-after-scope`, `READ of size 8`, dấu vết đi qua `std::string::size()`, `doDai`, `coroutine_handle::resume()`, `Generator::tiep()`. Cách sửa: nhận **theo giá trị** (`std::string s`), để khung giữ bản sao của riêng nó.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::jthread` khác `std::thread` thế nào? `stop_token` hơn cờ `atomic<bool>` ở đâu?"
    Hàm hủy của `jthread` gọi `request_stop()` rồi `join()`, nên không `std::terminate` vì quên `join` (`std::thread` còn joinable bị hủy thì gọi `terminate`, mình đã chạy ở [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)); và nó có sẵn `stop_token`. `stop_source` là nút bấm, `stop_token` là đèn báo chung một trạng thái, lật một chiều, đọc từ nhiều luồng không có data race. Hơn cờ `atomic`: token đi kèm từng luồng thay vì một biến toàn cục; `request_stop` **đánh thức** luồng ngủ trong `condition_variable_any::wait(lk, tk, vi_tu)` (mình chạy: `wait` trả `false`), còn cờ `atomic` đặt mà không `notify` thì luồng ngủ mãi (mình chạy: treo, mã 124). Nối tiếp "dừng có đột ngột không?": không, dừng là **hợp tác**, `request_stop` không ngắt hàm đang chạy. Nối tiếp "với C++17?": không có, phải tự làm lớp bọc `join` và cờ `atomic<bool>`.

??? question "Coroutine khác thread thế nào?"
    Coroutine là **hàm tạm dừng được** và chạy tiếp được, trạng thái nằm trong một khung thường trên heap; nó **không phải một luồng thực thi** và không tự song song. Nó chạy trên luồng của ai gọi `resume()` (mình chạy: cùng một coroutine chạy tiếp ở luồng `main` rồi ở một luồng khác, `id` khác nhau). Luồng do hệ điều hành lập lịch và mỗi luồng có stack riêng; coroutine do code bạn (hoặc thư viện) lập lịch, tạm dừng chỉ tại `co_await`/`co_yield`. Muốn dùng nhiều lõi vẫn phải có nhiều luồng.

??? question "Stackful với stackless khác nhau thế nào? Go thuộc loại nào?"
    Stackful giữ **cả stack** của coroutine nên dừng được ở bất kỳ độ sâu hàm gọi; stackless chỉ giữ **khung của chính coroutine** nên chỉ dừng được tại `co_await`/`co_yield` trong thân nó, đổi lại khung nhỏ (khung generator mình đo là 88 byte). Goroutine là stackful, kèm bộ lập lịch của runtime Go (ngắt được, chạy song song). Coroutine C++20 là stackless và không có bộ lập lịch kèm theo: lập lịch là việc của thư viện. Nối tiếp "cái giá là gì?": phải tự dựng hạ tầng lập lịch (hoặc dùng thư viện), và hàm thường mà coroutine gọi không dừng được coroutine bên trên.

??? question "Khi nào bạn dùng coroutine, khi nào không?"
    Dùng khi có **nhiều việc phần lớn thời gian là chờ** (I/O mạng, hẹn giờ) và muốn viết tuần tự thay cho chuỗi callback, mỗi việc chỉ tốn một khung nhỏ thay vì một luồng; và khi cần generator sinh lười. Không dùng cho việc nặng CPU (nhiều lõi cần nhiều luồng), cho code đồng bộ đơn giản, hay khi chưa có thư viện hạ tầng và nhóm chưa quen vòng đời `promise_type`. Nối tiếp "g++ 11 có `std::generator` không?": không, đó là C++23; mình phải tự viết kiểu `Generator`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng `request_stop()` dừng được luồng ngay, hoặc quên kiểm token"
    Luồng không nhìn token thì không dừng. `request_stop` không ngắt `sleep_for` hay một lời gọi chặn; muốn đánh thức luồng đang chờ `cv` thì dùng `condition_variable_any` với token, còn `condition_variable` thường không nhận token. Mình chạy: bỏ lời gọi `request_stop` mà vẫn `join` thì `join` treo (mã 124).

!!! warning "Lỗi 2: Coroutine nhận tham chiếu/con trỏ tới thứ sẽ chết, hoặc quên `destroy()`"
    Thân coroutine lười chạy sau lúc gọi; tham số tham chiếu tới giá trị tạm là treo (ASan: `stack-use-after-scope`; không sanitizer thì có thể in đúng do may). Khung nằm trên heap, quên `destroy()` (hay kiểu bọc không gọi nó trong hàm hủy) là rò rỉ: LeakSanitizer báo 88 byte. Dùng tham số theo giá trị và đặt `destroy()` trong hàm hủy RAII.

!!! warning "Lỗi 3: Coi coroutine như luồng"
    Gọi coroutine không tạo luồng mới và không chạy song song. Muốn song song cần nhiều luồng; muốn coroutine chạy ở luồng khác thì phải có ai đó `resume()` ở luồng đó, và phải tự đảm bảo không hai luồng cùng `resume` một coroutine.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="63" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. Sau khi `main` ngủ 10 ms rồi chạy hết hàm (không gọi gì thêm lên `t`), điều gì xảy ra?

```text
std::jthread t([](std::stop_token tk) {
    while (!tk.stop_requested()) { /* làm việc */ }
});
// main: ngủ 10 ms, rồi return
```

- Chương trình gọi `std::terminate`, vì `t` còn joinable lúc bị hủy
- Hàm hủy của `t` bấm dừng rồi chờ, luồng thoát và chương trình kết thúc
- Chương trình treo mãi, vì không ai gọi `request_stop` trước `join`
- Luồng bị `detach` và chạy tiếp ngầm cho tới khi tiến trình kết thúc

<p class="giai-thich" markdown>`~jthread` gọi `request_stop()` rồi `join()`, nên vòng lặp thấy yêu cầu dừng, thoát, và chương trình kết thúc sạch. Gọi `std::terminate` là cách xử lý của `std::thread` còn joinable, không phải của `jthread`. Treo mãi chỉ xảy ra khi bạn tự gọi `t.join()` mà chưa ai bấm dừng, vì khi đó hàm hủy chưa chạy. Còn `detach` không bao giờ tự xảy ra.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Một luồng nền ngủ trong `cv.wait` chờ việc từ hàng đợi, và bạn cần tắt dịch vụ gọn gàng (C++20). Cách nào đúng và đủ?

- Đặt `atomic<bool> dung = true` rồi `join`; luồng nền sẽ tự thấy cờ ở lần ngủ sau
- Gọi `request_stop()` trên `std::thread`; hàm này đánh thức mọi `condition_variable` đang ngủ
- `detach` luồng nền rồi để tiến trình thoát; hệ điều hành sẽ dọn luồng đó
- Dùng `jthread` với `condition_variable_any::wait(lk, tk, vi_tu)` rồi `request_stop()`

<p class="giai-thich" markdown>`wait` với `stop_token` ngủ tới khi vị từ đúng hoặc có yêu cầu dừng, và `request_stop()` đánh thức luồng đang ngủ. Đặt cờ `atomic` rồi `join` không đánh thức ai, nên luồng đang ngủ trong `cv.wait` ngủ mãi nếu không ai `notify` (mình chạy: treo). `std::thread` không có `request_stop`; hàm đó thuộc `jthread` và `stop_source`. Còn `detach` để luồng chạm vào dữ liệu đang bị dọn lúc thoát, và bỏ qua việc làm nốt việc còn lại.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Điều nào mô tả đúng nhất quan hệ giữa coroutine C++ và luồng?

- Coroutine không có luồng riêng; thân nó chạy trên luồng của bên gọi `resume()`
- Mỗi lần gọi coroutine, trình biên dịch tạo một luồng nền để chạy phần còn lại
- Coroutine tự phân việc lên nhiều lõi khi có từ hai lần `co_await` trở lên
- Coroutine chạy trên một luồng cố định của thư viện chuẩn, cùng với mọi coroutine

<p class="giai-thich" markdown>Coroutine chỉ là hàm tạm dừng được; không có thứ gì trong ngôn ngữ tạo luồng hay lập lịch cho nó. `resume()` chạy thân ngay trên luồng của bên gọi, và mình chạy thấy cùng coroutine chạy tiếp ở luồng khác khi luồng khác gọi `resume()`. Ý "tạo luồng nền" và "tự phân việc lên nhiều lõi" đều nhầm coroutine với `async` hay thread pool. Còn "luồng cố định của thư viện chuẩn" sai vì C++20 không có bộ lập lịch kèm sẵn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Coroutine này dùng `Generator` của bài (`initial_suspend` là `suspend_always`, `tiep()` gọi `resume()`). Chương trình in gì?

```text
Generator dem() { cout << "A "; co_yield 1; cout << "B "; }
int main() {
    Generator g = dem();
    cout << "X ";  g.tiep();  cout << "Y ";  g.tiep();  cout << "Z\n";
}
```

- `A X B Y Z`, vì thân chạy tới `co_yield` ngay khi gọi `dem()`
- `A B X Y Z`, vì thân chạy hết ngay khi gọi, trước mọi lệnh in khác
- `X A Y B Z`, vì mỗi lần `tiep()` chạy tới điểm dừng kế tiếp
- `X Y A B Z`, vì thân chỉ chạy khi `main` đã in xong mọi thứ khác

<p class="giai-thich" markdown>Vì `initial_suspend` là `suspend_always`, gọi `dem()` chưa chạy dòng nào của thân, nên `X` in trước. Lần `tiep()` đầu chạy từ đầu thân: in `A` rồi dừng ở `co_yield`; `main` in `Y`; lần `tiep()` thứ hai in `B` rồi thân hết. Hai đáp án bắt đầu bằng `A` coi coroutine như hàm thường hoặc như coroutine chạy ngay (`suspend_never`). Còn `X Y A B` quên rằng mỗi `tiep()` chạy ngay tại chỗ chứ không hoãn tới cuối `main`. Mình đã chạy đúng đoạn này: `X A Y B Z`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Phỏng vấn: cần cộng một mảng 100 triệu số, máy có 8 lõi rảnh. Hướng nào hợp lý?

- Viết hàm cộng thành coroutine, `co_await` sau mỗi nghìn số để chạy song song
- Dùng một coroutine và `co_yield` từng tổng riêng, để trình biên dịch phân lõi
- Chia mảng cho vài `jthread` (hoặc `async`), mỗi luồng cộng một đoạn rồi gộp kết quả
- Dùng `jthread` duy nhất kèm `stop_token`, vì token giúp chia việc cho các lõi

<p class="giai-thich" markdown>Việc nặng CPU cần nhiều luồng để dùng nhiều lõi, nên chia đoạn cho vài luồng rồi gộp. Coroutine không tự chạy song song: `co_await` chỉ tạm dừng chứ không phân lõi, và trình biên dịch không tự chia coroutine lên lõi. Một `jthread` duy nhất chỉ chạy trên một lõi tại một lúc, còn `stop_token` là cờ dừng, không liên quan chuyện chia việc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Một dịch vụ cần xử lý 10 000 kết nối mạng, mỗi kết nối phần lớn thời gian chỉ chờ dữ liệu rồi xử lý nhẹ. Chọn nào hợp lý nhất?

- Mở 10 000 `jthread`, vì `jthread` rẻ hơn `thread` nên mỗi kết nối một luồng là ổn
- Dùng một coroutine duy nhất để `co_await` tuần tự từng kết nối, từ kết nối thứ nhất tới thứ 10 000
- Gọi `std::async` 10 000 lần, vì `async` dùng chung một luồng cho mọi việc
- Dùng coroutine kèm vòng lặp sự kiện: mỗi kết nối một khung nhỏ, chờ không giữ luồng

<p class="giai-thich" markdown>Việc chủ yếu là chờ hợp với coroutine: mỗi kết nối chỉ tốn một khung nhỏ trên heap, và lúc chờ thì luồng được trả cho việc khác, miễn là có vòng lặp sự kiện (hay thư viện) gọi `resume` khi dữ liệu tới. `jthread` chỉ thêm tiện ích dừng và `join`, mỗi luồng vẫn có stack riêng, nên 10 000 luồng vẫn nặng. Một coroutine duy nhất chờ tuần tự thì kết nối sau phải đợi kết nối trước. Còn `async` không dùng chung một luồng: mặc định có thể mở luồng cho mỗi việc, hoặc hoãn chạy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::jthread` (C++20): hàm hủy gọi `request_stop()` rồi `join()` nên không `terminate` vì quên `join`; hàm của luồng nhận `std::stop_token` làm tham số đầu thì `jthread` tự đưa vào. Dừng là **hợp tác**: `request_stop()` chỉ lật đèn (trả `true` ở lần đầu, `false` ở lần sau), không ngắt `sleep_for`, không giết luồng; bỏ nó mà vẫn `join` thì treo (mình chạy, mã 124).
2. `stop_source`/`stop_token`/`stop_callback`: nút, đèn, và hàm gọi ngay trong luồng bấm nút. `condition_variable_any::wait(lk, tk, vi_tu)` bị `request_stop()` đánh thức và trả giá trị của vị từ (nên hàng đợi vẫn được làm nốt, mình chạy 300 lần ra `5050`); cờ `atomic` đặt mà không `notify` thì luồng ngủ mãi.
3. Coroutine là hàm tạm dừng được với `co_yield`, `co_await`, `co_return`; trạng thái nằm trong khung thường trên heap (mình đo 88 byte cho generator nhỏ; quên `destroy()` là rò rỉ). Kiểu trả về cần `promise_type`; C++20 chỉ cho bộ khung, `std::generator` là C++23 và g++ 11 không có. Cờ: `-std=c++20` đủ trên g++ 11 (không cần `-fcoroutines`); `-std=c++17` báo lỗi nên khối coroutine đều `// bo-qua-kiem-tra`.
4. Coroutine **không phải luồng**: thân chạy trên luồng của bên gọi `resume()` (mình chạy: cùng coroutine chạy ở `main` rồi ở luồng khác), không tự song song. Tham số tham chiếu tới giá trị tạm sẽ treo (ASan: `stack-use-after-scope`); nhận theo giá trị.
5. Goroutine là stackful (stack riêng, dừng ở độ sâu bất kỳ, runtime lập lịch và ngắt được; mình đo cỡ 2050 byte mỗi goroutine); coroutine C++ là stackless (chỉ dừng tại `co_await`/`co_yield` trong thân, không bộ lập lịch kèm). `iter.Seq` của Go tương ứng generator. Dùng coroutine cho việc chủ yếu là chờ kèm thư viện; không dùng cho việc nặng CPU. `std::execution` (senders/receivers, C++26) chỉ nhắc tên, mình không chạy.
