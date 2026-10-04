# Bài 28 — std::atomic: thao tác nguyên tử, compare_exchange và cờ dừng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::atomic<int>` (`++`, `load`, `store`, `fetch_add`, `exchange`) để các luồng cùng đếm mà không cần khóa; nối lại ví dụ đếm chung của [Bài 25](25-data-race-mutex.md): `int` thường có data race, `atomic<int>` thì đúng và ThreadSanitizer sạch. Biết atomic rẻ hơn mutex cỡ nào trên máy mình (đo thật) và vì sao con số đó đổi theo máy.
    - Viết vòng lặp `compare_exchange_weak` ("so sánh rồi đổi trong một nhịp") và giải thích vì sao `weak` được đặt trong vòng lặp; dùng `std::atomic<bool>` làm cờ dừng và nói được vì sao `bool` thường làm cờ là sai.
    - Chọn đúng giữa atomic và mutex: một biến đơn giản thì atomic; hai biến phải đổi cùng nhau thì mutex, vì hai atomic không giữ được bất biến (chạy thật để thấy).
    - Nhắc đúng mức về `memory_order` (người mới dùng mặc định), `volatile` (không thread-safe), lock-free (`is_lock_free`, `atomic_flag`) và ABA (chỉ tên).

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, `vector<thread>`, `sleep_for`, `std::chrono`), [Bài 25](25-data-race-mutex.md) (data race, `std::mutex`, `lock_guard`, lớp `BoDem`, TSan), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, sanitizer), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (ngoặc `<...>` cho biết kiểu, ngoặc nhọn `{...}` cho giá trị đầu), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (con trỏ hàm), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`auto`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến toàn cục), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (đã nhắc "thao tác nguyên tử" ở bộ đếm của `shared_ptr`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](25-data-race-mutex.md): cả bếp dùng chung bảng treo tường, và để đụng vào thớt chung phải lấy **thẻ vào thớt** (mutex). Nhưng có việc nhỏ hơn nhiều: đếm số đĩa đã ra khỏi bếp. Bắt mỗi người lấy thẻ thớt chỉ để cộng một vào một con số thì phí.

Vì vậy bếp gắn lên bảng một **bộ đếm bấm tay**. Bấm một cái là cộng một cái, trọn vẹn: hai đầu bếp bấm cùng lúc thì máy vẫn xếp thành hai lần bấm riêng, không ai làm mất lần bấm của ai. Không cần thẻ, không ai phải đứng chờ lâu. Bộ đếm đó chính là `std::atomic`.

!!! info "Chỗ nào ví von bộ đếm bấm tay không còn đúng?"
    Bộ đếm chỉ làm được **một phép trên đúng một con số**. Muốn đổi **hai** con số cùng lúc (trừ ở bảng này, cộng ở bảng kia) mà không ai thấy trạng thái dở dang thì máy bấm tay không đủ, phải quay lại thẻ thớt (phần 💻 ở dưới). Máy bấm thật chỉ cộng; `std::atomic` còn đặt số mới và "chỉ đổi nếu đúng số này" (mục 4). Cuối cùng, bấm máy cũng có giá: mục 3 đo giá đó.

## 📖 Giải thích

### 1. `std::atomic<int>`: mỗi thao tác là một khối không chia cắt

Một thao tác **nguyên tử** (atomic) là thao tác mà luồng khác chỉ có thể thấy **trước** hoặc **sau** nó, không bao giờ thấy giữa chừng. [Bài 25](25-data-race-mutex.md) cho thấy `++dem` trên `int` thường là ba bước (đọc, cộng, ghi) và luồng khác chen vào được. Kiểu `std::atomic<int>` (cần `#include <atomic>`) biến mỗi thao tác của nó thành một khối như vậy. Chuẩn C++ nói: các thao tác trên cùng một đối tượng atomic từ nhiều luồng **không** tạo ra data race.

Cú pháp `std::atomic<int> n{10};` tạo atomic với giá trị đầu 10 (cặp `<int>` cho biết kiểu, ngoặc nhọn là giá trị đầu, giống `vector` ở [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)). Chương trình dưới chạy **một luồng**, chỉ để xem từng thao tác làm gì và trả về gì.

```cpp
#include <atomic>
#include <iostream>

int main() {
    std::atomic<int> n{10};                 // (1) khởi tạo 10
    n.store(20);                            // (2) ghi 20
    int cu = n.fetch_add(5);                // (3) cộng 5, trả giá trị TRƯỚC khi cộng
    int truoc = n.exchange(100);            // (4) đặt 100, trả giá trị cũ
    ++n;                                    // (5) ++ cũng nguyên tử
    std::cout << "load: " << n.load() << "\n";                           // (6) đọc
    std::cout << "fetch_add tra " << cu << ", exchange tra " << truoc << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `n` lúc này |
|---|---|---|
| (2) | `store(20)` ghi 20, một khối không chia cắt | 20 |
| (3) | `fetch_add(5)` đọc rồi cộng trong **một** khối, `cu` nhận số cũ 20 | 25 |
| (4)(5) | `exchange(100)` đặt số mới, `truoc` nhận số cũ 25; `++n` cộng 1 | 101 |
| (6) | `load()` đọc `n` | 101 |

**Kết quả khi chạy** (mình chạy thật):

```text
load: 101
fetch_add tra 20, exchange tra 25
```

Hai điều hay nhầm: `fetch_add` trả giá trị **cũ** (trước khi cộng), và `std::atomic` **không sao chép được** (mình thử `std::atomic<int> b = a;`: `error: use of deleted function ‘std::atomic<int>::atomic(const std::atomic<int>&)’`).

### 2. Nối lại ví dụ đếm chung của Bài 25

Đây là chương trình của [Bài 25](25-data-race-mutex.md): bốn luồng, mỗi luồng tăng biến chung 100000 lần. Bài 25 cho kết quả sai (và TSan báo data race) vì biến là `int` thường. Lần này **chỉ đổi kiểu** của `dem`.

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

std::atomic<int> dem{0};                   // (1) chỉ đổi kiểu so với Bài 25: int -> atomic<int>

void tang() {
    for (int i = 0; i < 100000; ++i) {
        ++dem;                             // (2) một thao tác nguyên tử, không cần khóa
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "mong doi 400000, thuc te " << dem << "\n";   // (3)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `dem` lúc này |
|---|---|---|
| (2) | Bốn luồng cùng `++dem`; mỗi lần là một khối, xếp thành từng lần tăng riêng | tăng đúng 1 mỗi lần |
| `join` | Luồng chính chờ cả bốn xong (đồng bộ như Bài 25) | 400000 |
| (3) | Đưa `dem` cho `cout`: một lần `load()` ngầm (atomic tự đổi sang `int` khi bạn dùng nó như số) | 400000 |

**Kết quả khi chạy** (năm lần liền đều như nhau; không tối ưu và `-O2` đều vậy):

```text
mong doi 400000, thuc te 400000
```

Mình chạy với `-fsanitize=thread` (cả không tối ưu và `-O2`, qua `setarch $(uname -m) -R` như Bài 25): không cảnh báo, mã thoát 0. Khác với `int` thường ở `-O2` (có lúc ra đúng nhờ may mà TSan vẫn báo), ở đây đúng theo chuẩn.

**Thử thay đổi: đổi `++dem;` thành `dem = dem + 1;`.** Mình đã chạy:

- Kết quả: vẫn biên dịch, nhưng sai và đổi mỗi lần (`114247`, `113895`, `105750`, `104864`, `107086`); TSan **không** báo gì (mã thoát 0).
- Vì sao: `dem + 1` là một lần `load()`, rồi `=` là một lần `store()`. Mỗi lần là nguyên tử, nhưng **giữa hai lần** luồng khác chen vào được.
- Bài học: atomic bảo vệ từng thao tác, không bảo vệ cả câu lệnh gồm nhiều thao tác. Dùng `++dem`, `dem += 1` hoặc `fetch_add`.

!!! info "Bạn biết Go?"
    `sync/atomic` của Go làm đúng việc này: `atomic.AddInt64(&n, 1)` (hàm nhận con trỏ, cách cũ) hoặc kiểu `atomic.Int64` với `n.Add(1)`, `n.Load()`, `n.Store(v)`, `n.Swap(v)` (kiểu này có từ Go 1.19). Mình chạy bốn goroutine, mỗi cái tăng 100000 lần: cả hai cách ra `400000`, `go run -race` không báo gì; một biến `int64` thường cùng `thuong++` thì `-race` báo `WARNING: DATA RACE`.

    Khác chỗ:

    - `Add` của Go trả giá trị **mới** (mình chạy: `Store(10)` rồi `Add(5)` ra `15`), còn `fetch_add` của C++ trả giá trị **cũ**.
    - Go không có tham số `memory_order` để chọn. Tài liệu của Go (`go doc sync/atomic`) nói mọi thao tác atomic hành xử như thể chạy theo một thứ tự tuần tự chung, cùng ngữ nghĩa với atomic `seq_cst` của C++ và với `volatile` của Java.

### 3. Atomic và mutex: đo chi phí

Cùng một việc đếm, hai cách: `lock_guard` quanh `++` ([Bài 25](25-data-race-mutex.md)) hay atomic. Ta thêm bản thứ ba, `fetch_add(1, std::memory_order_relaxed)` (một **thứ tự bộ nhớ** yếu hơn, nói ở mục 6). Mỗi luồng tăng một triệu lần, bốn luồng; `chay` nhận một con trỏ hàm và đo bằng `std::chrono`, như Bài 25.

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

const int MOI_LUONG = 1000000;             // mỗi luồng tăng một triệu lần

std::mutex khoa;
long long demKhoa = 0;                     // bảo vệ bằng mutex
std::atomic<long long> demNguyenTu{0};     // (1) atomic, thứ tự mặc định
std::atomic<long long> demThongKe{0};      // (2) atomic, thứ tự relaxed

void bangMutex() {
    for (int i = 0; i < MOI_LUONG; ++i) { std::lock_guard<std::mutex> giu(khoa); ++demKhoa; }
}
void bangAtomic() {
    for (int i = 0; i < MOI_LUONG; ++i) ++demNguyenTu;
}
void bangRelaxed() {
    for (int i = 0; i < MOI_LUONG; ++i) demThongKe.fetch_add(1, std::memory_order_relaxed);
}

long long chay(void (*ham)()) {            // chạy 4 luồng, trả số mili giây
    auto bat = std::chrono::steady_clock::now();
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(ham);
    for (std::thread& t : cacLuong) t.join();
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();
}

int main() {
    long long msKhoa = chay(bangMutex);
    long long msNguyenTu = chay(bangAtomic);
    long long msRelaxed = chay(bangRelaxed);
    std::cout << "tong: " << demKhoa << " " << demNguyenTu << " " << demThongKe << "\n";
    std::cout << "mutex " << msKhoa << " ms, atomic " << msNguyenTu
              << " ms, relaxed " << msRelaxed << " ms\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Việc đang làm |
|---|---|---|
| `chay(bangMutex)` | Bốn luồng xếp hàng xin thẻ cho từng lần `++` | 4 triệu lần xin và trả khóa |
| `chay(bangAtomic)` | Bốn luồng cùng `++` một biến atomic, không thẻ | 4 triệu thao tác nguyên tử |
| `chay(bangRelaxed)` | Như trên nhưng thứ tự relaxed | 4 triệu thao tác nguyên tử |

**Kết quả khi chạy** (g++ 11, máy 8 lõi, CPU x86-64; ba lần liền, dòng đầu luôn như nhau):

```text
tong: 4000000 4000000 4000000
mutex 258 ms, atomic 57 ms, relaxed 52 ms
```

Dòng thứ hai là một lần chạy không tối ưu; hai lần kia ra `254/53/47` và `251/57/51` ms. Với `-O2` mình chạy ba lần: mutex 184 đến 204 ms, atomic 38 đến 46 ms, relaxed 38 đến 50 ms. Mọi con số đổi theo máy, số lõi, mức `-O` và độ bận lúc chạy, nên chỉ **mẫu** đáng nhớ: trên máy mình atomic nhanh hơn mutex cỡ bốn đến năm lần ở việc đếm này. Với `-fsanitize=thread` thời gian lên hẳn (một lần chạy của mình mất gần 5 s tổng), nên đừng đo hiệu năng khi đang bật TSan.

Hai quan sát khác. Một: `relaxed` **không** nhanh hơn rõ rệt trên máy mình; mình xem mã hợp ngữ ở `-O2`, cả hai bản đều ra cùng một lệnh `lock addq $1, ...` (lệnh cộng có tiền tố `lock`: CPU giữ riêng ô nhớ trong lúc cộng). Hai: atomic không miễn phí, vì các lõi vẫn phải tranh nhau cùng một ô nhớ; nó chỉ rẻ hơn việc xin khóa, nhả khóa và (khi tranh nhau) ngủ chờ.

### 4. `compare_exchange`: so sánh rồi đổi trong một nhịp

Bài toán: tăng `dem` thêm 1 **chỉ khi** nó còn nhỏ hơn một giới hạn (250000), từ bốn luồng, mỗi luồng cố tăng 100000 lần. Cách "kiểm rồi tăng" bằng hai lệnh atomic rời nhau (`if (dem.load() < GIOI_HAN) dem.fetch_add(1);`) là sai: giữa kiểm và tăng, luồng khác chen vào được.

Mình chạy đúng cách làm đó 10 lần ở mỗi mức tối ưu (không tối ưu và `-O2`): `dem` luôn **vượt** giới hạn, ra `250002` hoặc `250003`, và TSan (chạy một lần) **không** báo gì, mã thoát 0. Đây là **race condition** ([Bài 25](25-data-race-mutex.md)), không phải data race: từng lệnh đều nguyên tử, cái sai là kiểm và tăng thành hai bước.

Cách đúng là **`compare_exchange`**: "nếu `dem` **vẫn đang bằng** giá trị `cu` tôi đã thấy thì đổi thành `cu + 1` và báo `true`; nếu không thì **không đổi** và báo `false`". Cả việc so sánh lẫn việc đổi là **một nhịp** nguyên tử, không ai chen vào giữa. Khi thất bại, hàm còn **ghi giá trị hiện tại vào `cu`** (nên `cu` được truyền như tham chiếu) để bạn thử lại ngay.

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

const int GIOI_HAN = 250000;
std::atomic<int> dem{0};
std::atomic<int> thanhCong{0};             // tổng số lần tăng thật sự xảy ra

// Tăng dem thêm 1 NẾU nó còn nhỏ hơn GIOI_HAN. Trả true nếu đã tăng.
bool tangNeuConNho() {
    int cu = dem.load();                                       // (1) đọc giá trị hiện tại
    while (cu < GIOI_HAN) {                                    // (2) còn chỗ thì thử
        if (dem.compare_exchange_weak(cu, cu + 1)) {           // (3) "nếu vẫn là cu thì đổi thành cu+1"
            return true;                                       // (4) đổi được
        }
        // (5) thất bại: cu vừa được cập nhật thành giá trị hiện tại, vòng lại kiểm (2)
    }
    return false;                                              // (6) đã đầy
}

void tho() {
    for (int i = 0; i < 100000; ++i) {
        if (tangNeuConNho()) ++thanhCong;
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tho);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << dem << ", so lan tang thanh cong = " << thanhCong << "\n";
    return 0;
}
```

**Chạy từng dòng** (một cách xen kẽ có thể xảy ra, `dem` đang là 7)

| Dòng | Luồng A | Luồng B | `dem` lúc này |
|---|---|---|---|
| (1) | `cu = 7` | `cu = 7` | 7 |
| (3) | đổi 7 thành 8: thành công | | 8 |
| (3) | | `dem` là 8 chứ không phải 7: thất bại, `cu` thành 8 | 8 |
| (5)(2)(3) | | vòng lại, `cu = 8 < GIOI_HAN`, đổi 8 thành 9: thành công | 9 |

**Kết quả khi chạy** (năm lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
dem = 250000, so lan tang thanh cong = 250000
```

Tổng 400000 lần thử, đúng 250000 lần thành công, `dem` dừng đúng ở giới hạn. Khi mình đếm thêm số lần `compare_exchange_weak` thất bại (qua một biến đếm phụ), được từ 401896 đến 572745 lần trong năm lượt chạy: bốn luồng tranh nhau phải thử lại nhiều lần, và con số đổi theo lần chạy. Đó là giá của cách làm này khi tranh chấp nặng.

**`weak` hay `strong`?** Chuẩn C++ nói `compare_exchange_weak` **được phép thất bại giả** (spurious failure): trả `false` dù giá trị đang đúng bằng `cu`; `compare_exchange_strong` thì chỉ thất bại khi giá trị thật sự khác. Vì thế `weak` hợp với **vòng lặp thử lại** như trên.

Mình chạy một luồng, 100 triệu lần `weak` với giá trị đúng: **0** lần thất bại giả trên máy này, và đổi `weak` thành `strong` ở chương trình trên ra cùng kết quả. Đừng suy ra "`weak` không bao giờ giả": đó là chuyện của máy mình, chuẩn không hứa. Quy tắc dễ nhớ: trong vòng lặp dùng `weak`; một lần duy nhất không lặp thì dùng `strong`.

!!! info "Bạn biết Go?"
    `CompareAndSwap(old, new)` của Go (cả `atomic.CompareAndSwapInt64(&n, old, new)` lẫn `n.CompareAndSwap(old, new)`) chỉ trả `bool`; nó **không** cập nhật `old` như C++, nên vòng lặp của Go phải tự `Load()` lại ở đầu mỗi vòng. Mình chạy bản Go của bài toán trên: `250000 250000`, `go run -race` sạch. Go chỉ có một loại CAS, không có `weak`/`strong` để chọn.

### 5. Cờ dừng: `std::atomic<bool>`

Việc rất hay gặp: luồng nền chạy vòng lặp, luồng chính muốn báo "dừng đi". Luồng chính đặt một cờ thành `true`, luồng nền kiểm cờ ở mỗi vòng. Cờ phải là `std::atomic<bool>` vì hai luồng đụng cùng một ô nhớ, một bên ghi.

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

std::atomic<bool> dung{false};             // (1) cờ dừng: ban đầu chưa dừng

void luongNen() {
    while (!dung.load()) {                 // (2) mỗi vòng kiểm cờ
        std::this_thread::sleep_for(std::chrono::milliseconds(1));   // (3) "làm việc": ở đây chỉ là ngủ 1 ms
    }
}

int main() {
    std::thread t(luongNen);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));   // (4) cho luồng nền chạy một lúc
    dung.store(true);                      // (5) luồng chính báo dừng
    t.join();                              // (6) luồng nền thấy cờ, thoát vòng, join xong
    std::cout << "luong nen da dung\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `dung` lúc này |
|---|---|---|
| (2)(3) | Luồng nền lặp: kiểm cờ, làm việc, ngủ 1 ms | `false` |
| (4)(5) | Luồng chính ngủ 50 ms rồi đặt cờ | `true` |
| (2)(6) | Vòng sau luồng nền thấy `true`, thoát hàm; `join` trả về | `true` |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
luong nen da dung
```

Điều chương trình **bảo đảm**: sau `join`, luồng nền đã thoát, và việc ghi `true` rồi đọc cờ không phải data race. Về "bao lâu thì luồng nền thấy `true`", chuẩn chỉ *khuyến khích* cài đặt cho giá trị mới hiện ra trong thời gian hợp lý và không hứa con số; trên máy mình nó dừng ngay.

**Vì sao KHÔNG dùng `bool` thường?** Thử đúng chương trình trên với `bool dung = false;` và vòng `while (!dung) ++soVong;` (không ngủ, `soVong` là một `long long` thường), bỏ `atomic`:

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <thread>

bool dung = false;                         // (1) bool THƯỜNG làm cờ: data race
long long soVong = 0;

void luongNen() { while (!dung) ++soVong; }              // (2) luồng nền ĐỌC dung

int main() {
    std::thread t(luongNen);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    dung = true;                           // (3) luồng chính GHI dung, không đồng bộ
    t.join();
    std::cout << "da dung\n";
    return 0;
}
```

Chuẩn nói đây là **data race**, tức hành vi không xác định ([Bài 25](25-data-race-mutex.md)): chương trình không có nghĩa nào được bảo đảm. Mình chạy với `timeout 5`: không tối ưu thì in `da dung`, mã 0; còn `-O1` và `-O2` đều **treo** tới khi `timeout` giết, mã **124**.

Mã hợp ngữ của `-O2` cho thấy lý do trên máy mình: hàm `luongNen` đọc `dung` **một lần** (`cmpb $0, dung(%rip)`: so sánh một byte với 0), thấy `false` rồi nhảy vào một vòng lặp vô hạn không đọc lại nữa (`jmp`, lệnh nhảy, về chính nó). Trình biên dịch được phép làm vậy vì theo chuẩn, nếu không có đồng bộ thì không luồng nào khác ghi `dung` trong lúc ta lặp. TSan (`-fsanitize=thread`) báo `data race` ở cả hai mức tối ưu: một bên ghi `dung` ở `main`, bên kia đọc ở `luongNen`.

**Nối Go:** cờ dừng của Go cũng là `atomic.Bool` (Go 1.19); mình chạy `for !dung.Load() { ... }` với `dung.Store(true)` ở luồng chính, `go run -race` sạch. Trong chương trình Go thật bạn thường dùng `context` hoặc đóng một channel; C++ chuẩn không có channel.

### 6. `memory_order`: chỉ nhắc, người mới dùng mặc định

Mọi thao tác atomic nhận thêm một tham số tùy chọn **`std::memory_order`** (thứ tự bộ nhớ): nó nói thao tác đó ràng buộc thứ tự với các lần đọc ghi **khác** quanh nó mạnh đến đâu. Mặc định là **`std::memory_order_seq_cst`**, mạnh nhất và dễ suy luận nhất: mọi luồng thấy mọi thao tác atomic theo cùng một thứ tự chung. Bài này **không** dạy các mức giữa (`acquire`/`release`); đó là chủ đề riêng và dễ sai.

**Người mới dùng mặc định `seq_cst`** (tức là đừng ghi gì thêm, như ở mọi ví dụ trên).

Mức duy nhất bài nhắc là **`std::memory_order_relaxed`**: nó chỉ bảo đảm thao tác **nguyên tử**, không ràng buộc thứ tự với việc khác. Nó hợp với **bộ đếm thống kê** (như `demThongKe` ở mục 3: mọi luồng chỉ cộng, và bạn chỉ đọc kết quả sau `join`). Đừng dùng `relaxed` cho cờ báo hiệu "dữ liệu đã sẵn sàng", vì đọc cờ không kéo theo việc thấy dữ liệu kia. Và nhớ kết quả mục 3: ở máy mình, `relaxed` không nhanh hơn.

**`volatile` không phải atomic.** Từ khóa `volatile` của C++ dặn trình biên dịch đừng bỏ các lần đọc ghi biến (dùng cho thanh ghi phần cứng); nó **không** làm `++` nguyên tử và **không** tạo đồng bộ giữa luồng, nên data race trên biến `volatile` vẫn là hành vi không xác định.

Mình thử `volatile int dem` trong chương trình đếm của [Bài 25](25-data-race-mutex.md), `-O2`: ba lần ra `163455`, `131218`, `163086` (mong 400000), và TSan báo `data race`. Lưu ý trái ngược Java: `volatile` ở Java là công cụ đồng bộ luồng (mà `++` vẫn không nguyên tử); Go gọi thẳng `sync/atomic`. Ở C++, thứ tương đương là `std::atomic`.

### 7. Lock-free, `atomic_flag` và ABA

**Lock-free** có hai nghĩa đời thường, đừng lẫn. Với kiểu atomic: `is_lock_free()` trả `true` nếu thao tác chạy bằng lệnh CPU, **không** dùng khóa ngầm trong thư viện. Với thuật toán: lock-free nghĩa là luôn có ít nhất một luồng tiến lên được, dù luồng khác bị hoãn (mục phỏng vấn nói kỹ hơn).

Kiểu `std::atomic_flag` là atomic nhỏ nhất: một cờ hai trạng thái, với `test_and_set()` (đặt cờ lên, **trả giá trị cũ**) và `clear()` (hạ cờ). Chuẩn bảo đảm riêng `atomic_flag` là lock-free. Trong C++17 nó được khởi tạo bằng `ATOMIC_FLAG_INIT`. Chương trình dưới chạy một luồng để xem `test_and_set` trả gì, và in `is_lock_free()` của hai kiểu.

```cpp
#include <atomic>
#include <iostream>

int main() {
    std::atomic_flag co = ATOMIC_FLAG_INIT;    // (1) cờ nguyên tử, ban đầu "hạ"
    bool lan1 = co.test_and_set();             // (2) đặt cờ lên, trả giá trị cũ (hạ)
    bool lan2 = co.test_and_set();             // (3) cờ đang lên, trả giá trị cũ (lên)
    co.clear();                                // (4) hạ cờ
    bool lan3 = co.test_and_set();             // (5) lại như lần đầu
    std::cout << lan1 << lan2 << lan3 << "\n";

    std::atomic<int> a{0};
    std::atomic<long long> b{0};
    std::cout << "atomic<int>: " << a.is_lock_free() << "\n";
    std::cout << "atomic<long long>: " << b.is_lock_free() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Cờ `co` sau dòng |
|---|---|---|
| (2) | Cờ đang hạ: `test_and_set` trả `false` (in `0`) và đặt cờ lên | lên |
| (3) | Cờ đang lên: trả `true` (in `1`), cờ vẫn lên | lên |
| (4)(5) | `clear()` hạ cờ; `test_and_set` lại trả `false` và đặt lên | lên |

**Kết quả khi chạy** (mình chạy thật):

```text
010
atomic<int>: 1
atomic<long long>: 1
```

Hai dòng cuối là kết quả của g++ 11 trên x86-64 của mình, **không** phải điều chuẩn hứa (chỉ `atomic_flag` được bảo đảm). Mình thử thêm `std::atomic` của một `struct` 64 byte: phải thêm `-latomic` khi liên kết (không thì `undefined reference to '__atomic_is_lock_free'`), và `is_lock_free()` ra `0`: loại atomic lớn thường dùng khóa ngầm. Có người dùng `test_and_set` trong vòng `while` để dựng **khóa quay** (luồng chưa lấy được cờ thì quay vòng hỏi lại, đốt CPU như vòng chờ bận ở [Bài 27](27-condition-variable.md)); bài này không dạy, mặc định bạn dùng `std::mutex`.

**ABA** (chỉ nêu tên): luồng A đọc giá trị `A`, rồi luồng khác đổi `A` thành `B` rồi lại thành `A`; `compare_exchange` của A thấy "vẫn là `A`" nên thành công dù trạng thái đã đổi giữa chừng. Lỗi này hay gặp khi tự viết cấu trúc lock-free dùng con trỏ; người mới nên dùng mutex hoặc thư viện có sẵn thay vì tự viết.

## 💻 Ví dụ code

### Hai biến phải đổi cùng nhau: hai atomic không đủ, mutex đủ

Atomic bảo vệ **một** biến. Đời thực hay có **bất biến** (điều luôn phải đúng) liên quan nhiều biến; kết luận trước: một biến đơn giản (đếm, cờ) thì **atomic**, hai biến phải đổi cùng nhau hoặc một đoạn nhiều bước thì **mutex**. Ta chạy thật cả hai cách.

Bất biến: `a + b` luôn bằng 1000. Luồng `chuyen` làm 1000 lần "trừ `a`, cộng `b`". Luồng chính liên tục đọc cả hai rồi đếm số lần thấy tổng khác 1000. Bản đầu dùng hai `std::atomic<int>` (viết `a + b` là hai lần `load()` ngầm); mỗi biến đúng theo chuẩn (TSan không có gì để báo), nhưng cả cặp thì không.

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <iostream>
#include <thread>

std::atomic<int> a{1000};
std::atomic<int> b{0};
std::atomic<bool> xong{false};

void chuyen() {
    for (int i = 0; i < 1000; ++i) {
        --a;                               // (1) trừ a: từ đây tới (2), tổng chỉ còn 999
        ++b;                               // (2) cộng b
    }
    xong.store(true);
}

int main() {
    long long viPham = 0;
    std::thread t(chuyen);
    while (!xong.load()) {
        int x = a.load();                  // (3) đọc a
        int y = b.load();                  // (4) đọc b
        if (x + y != 1000) ++viPham;       // (5) thấy tổng sai
    }
    t.join();
    std::cout << "a + b cuoi cung = " << a + b << ", so lan thay tong sai = " << viPham << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `a + b` lúc này |
|---|---|---|
| (1) | Luồng `chuyen` trừ `a`; `b` chưa kịp cộng | 999 |
| (3)(4) | Luồng chính chen vào đúng lúc này, đọc `a` rồi `b` | thấy 999 |
| (2) | Luồng `chuyen` cộng `b` | 1000 |

Mình chạy 10 lần (năm không tối ưu, năm `-O2`): tổng cuối luôn `1000`, nhưng số lần luồng chính thấy tổng sai **lần nào cũng lớn hơn 0**, ví dụ `1987`, `273`, `964` (không tối ưu), `3174`, `1015` (`-O2`); số đổi theo lần chạy và máy bạn ra số khác. Với `-fsanitize=thread`: sạch, mã thoát 0. Vậy đây là **race condition** chứ không phải data race. Thứ tự mặc định `seq_cst` đã là mạnh nhất mà vẫn thấy tổng sai, vì lỗi nằm ở khoảng hở giữa hai lệnh chứ không ở thứ tự.

Cách sửa: để một mutex bảo vệ **cả hai** biến, và mọi chỗ đụng vào cả hai đi qua hàm tự khóa (như `BoDem` của [Bài 25](25-data-race-mutex.md), ở đây viết bằng hàm cho gọn). Bên trong khóa, hai biến là `int` thường vì mutex đã lo; cờ `xong` vẫn là `atomic<bool>`.

```cpp
#include <atomic>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;                           // một mutex cho CẢ HAI biến
int a = 1000;                              // int thường: đã có khóa lo
int b = 0;
std::atomic<bool> xong{false};

void chuyen() {
    for (int i = 0; i < 1000; ++i) {
        std::lock_guard<std::mutex> giu(khoa);    // (1) đổi CẢ HAI trong một vùng găng
        --a;
        ++b;
    }
    xong.store(true);
}

int tong() {
    std::lock_guard<std::mutex> giu(khoa);        // (2) đọc CẢ HAI trong một vùng găng
    return a + b;
}

int main() {
    long long viPham = 0;
    std::thread t(chuyen);
    while (!xong.load()) {
        if (tong() != 1000) ++viPham;      // (3) luôn thấy 1000
    }
    t.join();
    std::cout << "tong cuoi cung = " << tong() << ", so lan thay tong sai = " << viPham << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Khóa lúc này |
|---|---|---|
| (1) | Mỗi vòng `chuyen` xin khóa, trừ `a`, cộng `b`, nhả khóa | luồng `chuyen` cầm |
| (3)(2) | Luồng chính gọi `tong()`: chờ nếu `chuyen` đang giữ khóa, nên không thấy trạng thái dở | luồng chính cầm |

**Kết quả khi chạy** (năm lần liền đều như nhau; TSan sạch):

```text
tong cuoi cung = 1000, so lan thay tong sai = 0
```

Số `0` ổn định vì đọc cả hai biến và đổi cả hai biến đều nằm trong khóa, nên không thể xen vào giữa. Cặp (atomic cho cờ, mutex cho dữ liệu) là điển hình: mỗi công cụ ở đúng chỗ của nó.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::atomic` là gì, khác mutex thế nào?"
    `std::atomic<T>` làm mỗi thao tác trên **một** biến thành nguyên tử: luồng khác thấy trước hoặc sau, không thấy giữa chừng, và theo chuẩn không tạo data race. Nó thường chạy bằng lệnh CPU, không khóa, nên rẻ hơn mutex (mình đo cỡ bốn đến năm lần trên máy mình, con số đổi theo máy). Mutex bảo vệ cả **đoạn code** nhiều lệnh và nhiều biến, giữ một bất biến; luồng không có khóa phải chờ. Một biến đơn giản (bộ đếm, cờ) thì atomic; hai biến phải đổi cùng nhau thì mutex, vì hai atomic riêng vẫn có khoảng hở giữa hai lệnh. Atomic chỉ bảo vệ từng thao tác, nên `x = x + 1` vẫn mất lần tăng.

??? question "`compare_exchange` hoạt động thế nào?"
    `x.compare_exchange_strong(mongDoi, mong)` làm trong một nhịp nguyên tử: nếu `x == mongDoi` thì đặt `x = mong` và trả `true`; nếu không thì **không đổi `x`**, ghi giá trị hiện tại của `x` vào `mongDoi`, trả `false`. Dùng để tự viết thao tác "đọc, tính, ghi nếu chưa ai đổi" bằng vòng lặp thử lại (ví dụ tăng đến giới hạn). `weak` được phép thất bại giả dù giá trị đúng, nên dùng trong vòng lặp; `strong` chỉ thất bại khi giá trị khác. Điểm cần nêu thêm là **ABA**: giá trị đổi `A` thành `B` rồi về `A` thì CAS vẫn thành công dù trạng thái đã đổi.

??? question "`volatile` có thread-safe không?"
    **Không.** `volatile` của C++ chỉ bảo trình biên dịch giữ nguyên các lần đọc ghi (cho phần cứng); nó không làm `++` nguyên tử và không tạo quan hệ đồng bộ giữa luồng, nên data race trên biến `volatile` vẫn là hành vi không xác định (mình chạy: `volatile int` đếm vẫn ra thiếu, TSan báo data race). Muốn dùng chung giữa luồng thì dùng `std::atomic` hoặc mutex. Khác Java: `volatile` ở Java **là** công cụ đồng bộ (đọc ghi thấy nhau theo thứ tự), dù `++` vẫn không nguyên tử.

??? question "Lock-free là gì?"
    Nói về **kiểu atomic**: `is_lock_free()` là `true` khi thao tác chạy bằng lệnh CPU mà không dùng khóa ngầm; chuẩn chỉ bảo đảm điều này cho `std::atomic_flag`, còn kiểu khác tùy máy (`atomic<int>` ra `1` trên máy mình, `struct` 64 byte ra `0`). Nói về **thuật toán**: lock-free nghĩa là dù một luồng bị hoãn tùy ý, vẫn có ít nhất một luồng khác tiến lên được, nên không có deadlock; mạnh hơn nữa là wait-free (mọi luồng đều tiến lên). Lock-free không có nghĩa "nhanh hơn mutex" và rất khó viết đúng (ABA, thứ tự bộ nhớ), nên mặc định dùng mutex hoặc thư viện có sẵn.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Dùng `bool` thường làm cờ dừng"
    Là data race: mình chạy `-O2` thì luồng nền treo mãi (mã 124), không tối ưu thì lại dừng đúng. Dùng `std::atomic<bool>`.

!!! warning "Lỗi 2: Tưởng hai atomic giữ được bất biến, hoặc `x = x + 1`"
    Mỗi thao tác atomic riêng lẻ chỉ bảo vệ một biến và một thao tác. `dem = dem + 1` mình chạy ra thiếu (TSan vẫn sạch), và `--a; ++b;` để luồng khác thấy tổng sai lần nào cũng có. Nhiều biến hoặc nhiều bước thì dùng mutex, hoặc `compare_exchange` trên một biến.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="28" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. Hỏi `a` và `b` bằng bao nhiêu?

```text
std::atomic<int> n{7};
int a = n.fetch_add(3);
int b = n.exchange(0);
```

- `a` là 10, `b` là 10, vì mỗi hàm trả giá trị mới của `n`
- `a` là 7, `b` là 10, vì mỗi hàm trả giá trị cũ của `n`
- `a` là 7, `b` là 0, vì `exchange` trả giá trị vừa đặt
- `a` là 10, `b` là 0, vì `fetch_add` trả số mới, `exchange` trả số đặt

<p class="giai-thich" markdown>Cả `fetch_add` lẫn `exchange` trả giá trị **cũ**, tức giá trị của `n` ngay trước thao tác. `fetch_add(3)` thấy 7, đổi `n` thành 10 và trả 7; `exchange(0)` thấy 10, đặt 0 và trả 10. Nghĩ rằng chúng trả giá trị mới là nhầm với `Add` của Go (trả giá trị mới) hoặc với `++n`. Còn `exchange` không trả số vừa đặt; số đó bạn đã biết sẵn vì chính bạn truyền vào.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Sau ba dòng này, `ok`, `cu` và `x` là gì?

```text
std::atomic<int> x{5};
int cu = 3;
bool ok = x.compare_exchange_strong(cu, 9);
```

- `ok` là `false`, `cu` là 5, `x` vẫn là 5
- `ok` là `false`, `cu` vẫn là 3, `x` vẫn là 5
- `ok` là `true`, `cu` vẫn là 3, `x` thành 9
- `ok` là `false`, `cu` là 5, nhưng `x` thành 9

<p class="giai-thich" markdown>`x` đang là 5 mà ta mong 3, hai số khác nhau nên không đổi gì: `ok` là `false` và `x` vẫn là 5. Khi thất bại, hàm còn ghi giá trị hiện tại của `x` vào `cu`, nên `cu` thành 5; đó là điều giúp vòng lặp thử lại không phải `load()` lại. Nói `cu` vẫn là 3 bỏ sót việc cập nhật này. Còn `x` thành 9 chỉ xảy ra khi so sánh khớp.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Vì sao `compare_exchange_weak` thường được đặt trong một vòng lặp?

- Vì nó chỉ đổi được một phần của giá trị, nên phải gọi nhiều lần cho đủ
- Vì nó trả `true` khi thất bại, nên phải lặp đến khi trả `false` mới xong
- Vì chuẩn cho phép nó trả `false` dù giá trị đúng bằng giá trị mong đợi
- Vì nó chỉ chạy được khi có luồng khác đang giữ mutex, nên phải chờ

<p class="giai-thich" markdown>Chuẩn cho phép `weak` thất bại giả: trả `false` dù giá trị đang đúng bằng giá trị mong đợi. Vòng lặp thử lại biến tình huống đó thành vô hại. Nó vẫn đổi cả giá trị trong một nhịp nguyên tử, không đổi từng phần. Nó trả `true` khi đổi được, `false` khi thất bại. Và nó không cần mutex nào; atomic hoạt động mà không có khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. `dung` là biến toàn cục `bool` thường, bắt đầu `false`. Luồng nền chạy `while (!dung) { ++vong; }`; luồng chính ngủ 50 ms, rồi `dung = true;`, rồi `join`. Điều nào đúng theo chuẩn?

```text
bool dung = false;
// luồng nền:   while (!dung) { ++vong; }
// luồng chính: ngủ 50 ms; dung = true; join
```

- Luôn dừng sau cỡ 50 ms, vì luồng chính đã ghi `true` vào `dung`
- Có data race nên chuẩn không hứa gì: có thể dừng, có thể treo mãi
- Luôn treo mãi, vì luồng nền không bao giờ thấy giá trị mới của `dung`
- Luôn dừng đúng, chỉ riêng giá trị `vong` có thể sai vì thiếu đồng bộ

<p class="giai-thich" markdown>Một luồng đọc, luồng kia ghi cùng ô `dung` mà không có đồng bộ: đó là data race, hành vi không xác định, nên chuẩn không bảo đảm cách nào cả. Mình chạy cả hai kết quả: không tối ưu thì dừng, còn `-O2` thì treo. Vì thế "luôn dừng" và "luôn treo" đều quá chắc. Còn nói chỉ riêng `vong` sai thì sai ở chỗ coi phần còn lại của chương trình vẫn được bảo đảm, trong khi hành vi không xác định chạm cả chương trình.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn sau. Luồng 1 chạy `--a; ++b;` nhiều lần, luồng 2 chạy `x = a.load(); y = b.load();` rồi kiểm `x + y`. `a`, `b` đều là `std::atomic<int>` với thứ tự mặc định, `a + b` ban đầu là 1000. Điều nào đúng?

```text
// luồng 1:  --a;  ++b;
// luồng 2:  x = a.load();  y = b.load();   // kiểm x + y
```

- Luồng 2 luôn thấy `x + y` bằng 1000, vì mọi thao tác đều nguyên tử
- Có data race, vì hai biến khác nhau bị truy cập cùng lúc từ hai luồng
- Luồng 2 chỉ thấy tổng sai nếu đổi sang thứ tự `relaxed` ở cả hai luồng
- Không có data race, nhưng luồng 2 vẫn có thể thấy `x + y` khác 1000

<p class="giai-thich" markdown>Mỗi thao tác atomic không gây data race, nên chuẩn không coi đây là hành vi không xác định. Nhưng luồng 1 đổi hai biến bằng hai lệnh rời nhau, nên luồng 2 có thể đọc đúng lúc `a` đã trừ mà `b` chưa cộng, và thấy 999. Thứ tự mặc định `seq_cst` vẫn cho phép điều đó, vì khoảng hở nằm giữa hai lệnh chứ không do thứ tự. Mình chạy thật: lần nào luồng đọc cũng thấy tổng sai. Muốn cả cặp đổi như một khối thì cần mutex.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Bốn luồng cùng `++dem`, nhưng `dem` được khai báo `volatile int dem = 0;` (không có mutex hay atomic). Điều nào đúng?

- Vẫn là data race: `volatile` của C++ không nguyên tử hóa `++` và không đồng bộ luồng
- An toàn, vì `volatile` buộc mọi lần đọc ghi đi thẳng vào bộ nhớ chính
- An toàn với `int` vì ghi một số nguyên là một lệnh, chỉ kiểu lớn hơn mới có race
- An toàn như `std::atomic`, vì `volatile` là bản nhẹ hơn của `atomic` cho C++

<p class="giai-thich" markdown>Chuẩn C++ không cho `volatile` ý nghĩa đồng bộ giữa luồng, và `++` trên nó vẫn là đọc, cộng, ghi rời nhau. Mình chạy với `-O2`: kết quả thiếu so với 400000, và TSan báo data race. Việc "đi thẳng vào bộ nhớ" chỉ ngăn trình biên dịch bỏ lần đọc ghi, không ngăn luồng khác chen vào giữa. Còn ý "ghi một `int` là một lệnh" chỉ nói về lệnh ghi; `++` là ba bước, và chuẩn không cho phép dựa vào điều đó.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::atomic<T>` (`#include <atomic>`) làm mỗi thao tác trên **một** biến thành khối không chia cắt, nên không tạo data race: `++dem` trên `atomic<int>` ra đúng 400000 và TSan sạch, còn `x = x + 1` vẫn mất lần tăng vì là hai thao tác rời. `fetch_add` và `exchange` trả giá trị **cũ**; `atomic` không sao chép được.
2. Việc đếm: atomic rẻ hơn mutex (mình đo cỡ bốn đến năm lần trên g++ 11, x86-64; con số đổi theo máy, `-O`, số lõi). `compare_exchange_weak/strong` là "so sánh rồi đổi trong một nhịp"; thất bại thì ghi giá trị hiện tại vào biến mong đợi; `weak` được phép thất bại giả nên đặt trong vòng lặp.
3. Cờ dừng phải là `std::atomic<bool>`; `bool` thường là data race, mình chạy: `-O2` treo mãi (mã 124), không tối ưu thì dừng. `volatile` của C++ không thread-safe (khác Java); Go `sync/atomic`: `atomic.Int64` từ Go 1.19, `Add` trả giá trị **mới**.
4. Atomic cho một biến đơn giản; bất biến nhiều biến (như `a + b` luôn 1000) cần mutex, vì hai atomic vẫn có khoảng hở: mình chạy, luồng đọc thấy tổng sai lần nào cũng có, còn bản mutex ra đúng 0.
5. `memory_order`: mặc định `seq_cst`, người mới dùng mặc định; `relaxed` chỉ cho bộ đếm thống kê (máy mình không nhanh hơn). `is_lock_free()` tùy kiểu và máy (chuẩn chỉ bảo đảm cho `atomic_flag`); ABA chỉ cần biết tên: giá trị đổi `A` thành `B` rồi về `A` làm CAS đánh lừa.
