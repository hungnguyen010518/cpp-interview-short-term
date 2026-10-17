# Bài 67 — Thực chiến: thread pool tự viết, trả future, dừng êm

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nghe đề "viết cho tôi một thread pool" mà không lao vào gõ: hỏi lại bốn câu (việc có kết quả không, ngoại lệ đi đâu, dừng thì việc còn lại ra sao, nộp muộn thì sao) rồi mới viết.
    - Viết `submit(f)` trả `std::future<R>` cho mọi kiểu `R` kể cả `void`, bằng `template`, `std::invoke_result_t`, `std::packaged_task` bọc trong `std::shared_ptr`; thấy lỗi biên dịch thật khi không bọc, và hiểu vì sao.
    - Làm **dừng êm**: `shutdown()` từ chối việc mới, làm hết việc đã nhận, `join`, gọi nhiều lần vẫn được, hàm hủy gọi lại nó; ngoại lệ trong việc đi qua `future` thay vì làm cả chương trình `std::terminate`.
    - Chạy thật năm bản SAI (việc chờ việc làm pool treo, đọc kết quả không qua `get()` bị TSan báo, bỏ việc còn lại làm `broken_promise`, không chặn nộp muộn làm `get()` treo, không bọc `shared_ptr` không biên dịch được), đếm chi phí của `submit`, và nói rõ chuẩn bảo đảm gì còn g++ 11 trên máy này cho gì.

**Bạn cần biết trước:** [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (pool tối thiểu: hàng đợi, worker chạy ngoài khóa, hủy = đặt cờ + `notify_all` + `join`; bài này **nâng cấp** nó, không dạy lại), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`future`, `get`, `packaged_task`, ngoại lệ đi qua future), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`wait` có vị từ), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`join`, `joinable`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template <class F>`), [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (`using` đặt bí danh kiểu), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`make_shared`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (`std::function`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, `throw`/`catch`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (TSan).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đẩy cây bút về phía bạn: "Mười lăm phút. Viết cho tôi một thread pool. Nộp việc nào cũng được, và tôi muốn lấy kết quả về. Khi đóng pool thì đừng làm mất việc của khách."

Quay lại **nhà bếp nhiều đầu bếp**. Bếp có một đội đầu bếp cố định và một bảng phiếu việc ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)). Bài này thêm hai thứ. Mỗi khi nộp phiếu, khách được cầm một **phiếu hẹn** (`future`) để lát nữa ra lấy món. Và có giờ **đóng cửa bếp**: treo biển "ngừng nhận món mới", đầu bếp làm nốt mọi phiếu còn trên bảng rồi mới về.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Phiếu hẹn thật chỉ mang món. Phiếu hẹn của C++ mang cả **sự cố**: món cháy thì khách cầm phiếu nhận lại đúng lỗi đó khi `get()`, chứ đầu bếp không la lên cho cả bếp nghe. Đầu bếp thật cũng biết món nào nặng nhẹ; worker chỉ thấy một cái hàm. Và bảng phiếu của ta có một khóa duy nhất, nên chuyện "đầu bếp chen nhau ở bảng" có thật (câu hỏi work stealing ở 🎤).

## 📖 Giải thích

### 1. Phản xạ đầu tiên: hỏi lại đề

Đề thread pool nghe quen nên dễ lao vào viết. Người phỏng vấn thường chấm xem bạn có hỏi bốn câu sau không, vì mỗi câu đổi thiết kế:

| Câu hỏi lại | Vì sao đổi thiết kế | Bài này chọn |
|---|---|---|
| Việc có kết quả và có thể ném ngoại lệ không? | Có thì cần `future`, không thì `std::function<void()>` đủ | trả `future<R>`, ngoại lệ đi qua nó |
| Việc có tham số không? | Quyết định chữ ký `submit` | không tham số; người gọi bọc bằng lambda `[=]` |
| Đóng pool thì việc còn trong hàng làm sao? | Làm hết hay bỏ | làm hết (drain) |
| Nộp việc sau khi đóng thì sao? | Im lặng nuốt, trả lỗi hay ném | ném `std::runtime_error` |

### 2. Đề (a): `submit` trả `future<R>`

!!! example "Đề (a): thread pool tối thiểu trả future"
    Viết lớp `NhomLuong` (thread pool). Hàm tạo nhận số worker `n`. Hàm `submit(f)` nhận **một thứ gọi được không đối số** (lambda, hàm, functor) kiểu bất kỳ và trả `std::future<R>`, với `R` là kiểu mà `f()` trả về, **kể cả `void`**. Worker chạy việc ngoài khóa; mỗi `future` giao đúng kết quả của việc của nó.

    - Đầu vào kiểm thử: pool 4 worker; nộp 8 việc, việc `i` trả `i * i`, rồi lấy kết quả **theo thứ tự phiếu**; nộp thêm 4 việc `void` mỗi việc ghi một ô `int` thường của mảng; nộp một việc trả `std::string`.
    - Đầu ra phải tất định: `1 4 9 16 25 36 49 64`, `tong = 204`, `bang = 100 200 300 400`, `xin chao`. TSan phải sạch.

??? tip "Gợi ý 1"
    Hàng đợi `std::function<void()>` của Bài 30 đã đủ để *chạy* việc. Cái thiếu là **chỗ để lấy giá trị về**. Trong Bài 29 mục 7, thứ nào bọc một hàm và đưa ra cho bạn một `future`?

??? tip "Gợi ý 2"
    `std::packaged_task` không sao chép được, còn `std::function` đòi thứ nó chứa phải sao chép được. Muốn cất một thứ không sao chép được vào một hộp sao chép được thì bọc nó vào thứ mà sao chép chỉ chép "tay cầm", rồi để hộp giữ tay cầm. Đó là loại con trỏ nào ở Bài 10?

??? tip "Gợi ý 3"
    Chữ ký: `template <class F> std::future<std::invoke_result_t<F>> submit(F f)`. Trong thân: `make_shared<packaged_task<R()>>(std::move(f))`, **`get_future()` trước**, rồi mới đẩy `[goi] { (*goi)(); }` vào hàng dưới khóa, `notify_one`, trả phiếu.

**Hướng giải.** Ba mảnh của Bài 30 giữ nguyên. Mảnh mới chỉ nằm trong `submit`, và nó trả lời đúng bốn thứ cần giải thích trước khi đọc code:

- `template <class F>`: `F` là chỗ trống cho kiểu của việc, trình biên dịch tự suy ra từ đối số ([Bài 34](../nhom-4-oop-patterns/34-template.md)). Mỗi lambda có kiểu riêng, nên mỗi lần gọi với lambda khác là một bản `submit` khác.
- `std::invoke_result_t<F>` (C++17, trong `<type_traits>`): "kiểu mà `f()` trả về khi gọi không đối số". Lambda `[] { return 3.5; }` cho `double`, lambda không có `return` cho `void`. Bí danh `using R = ...` ([Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md)) đặt tên ngắn cho kiểu đó.
- `std::packaged_task<R()>`: `R()` đọc như `int(int, int)` ở Bài 29, nghĩa là "hàm không nhận gì, trả `R`". Nó chạy khi được gọi và tự cất kết quả hay ngoại lệ vào `future`.
- `std::shared_ptr` bọc gói: sao chép `shared_ptr` rẻ, chỉ có **một** `packaged_task` thật, nên hộp `std::function<void()>` sao chép được mà không cần gói sao chép được. Lambda `[goi] { (*goi)(); }` giữ một `shared_ptr`; `*goi` lấy gói ra khỏi `shared_ptr` và `( )` gọi nó như một hàm, đúng như ở Bài 30.

### 3. Đề (b): dừng êm

!!! example "Đề (b): `shutdown()` êm, ngoại lệ đi qua future"
    Nâng cấp `NhomLuong`. Thêm `shutdown()` sao cho: (1) từ chối việc nộp mới, bằng cách `submit` ném `std::runtime_error("pool da dong")`; (2) làm hết mọi việc đã nhận; (3) `join` mọi worker; (4) gọi lần hai không sao; (5) hàm hủy cũng gọi `shutdown()`. Việc ném ngoại lệ phải đến tay người giữ `future` qua `get()`, và worker vẫn sống để làm việc tiếp.

    - Đầu vào kiểm thử: pool 3 worker; nộp 20 việc (mỗi việc tăng một `atomic<int>` và trả `i`), một việc ném `std::runtime_error("loi tinh toan")`; `shutdown()`; lấy kết quả; nộp thêm một việc; `shutdown()` lần hai.
    - Đầu ra: `da chay: 20 viec`, `tong = 210`, `viec loi: loi tinh toan`, `nop sau khi dong: bi tu choi (pool da dong)`, `shutdown lan hai: khong sao`. TSan sạch.

??? tip "Gợi ý 1"
    Hàm hủy của Bài 30 đã **làm hết việc rồi mới thoát** (worker chỉ `return` khi hàng rỗng *và* đã dừng). Bạn gần xong: việc cần làm là tách nó ra thành hàm gọi được tường minh và chặn `submit` sau khi cờ dừng đã bật.

??? tip "Gợi ý 2"
    Kiểm cờ `dung_` ở đâu? Trong `submit`, ở **cùng đoạn giữ khóa** với `push`. Đọc `dung_` ngoài khóa trong lúc `shutdown` ghi nó là data race. Còn `join` lần hai: `std::thread` đã `join` thì `joinable()` trả `false`, bỏ qua được.

??? tip "Gợi ý 3"
    Ngoại lệ: không cần viết thêm gì, `packaged_task` tự bắt rồi cất vào `future`. Worker không cần `try`/`catch (...)` như Bài 30 (ở đó việc nộp là `std::function` trần, nên `catch (...)` phải nuốt lỗi).

**Hướng giải.** Chỉ ba chỗ đổi, mỗi chỗ một câu hỏi bảng trắng:

- Cờ `dung_` được kiểm trong `submit` **dưới khóa**: không có khe giữa "đã kiểm chưa đóng" và "đã đẩy vào hàng".
- `shutdown()` = đặt cờ dưới khóa, `notify_all`, `join` (bỏ qua luồng đã `join`). Hàm hủy gọi nó, nên quên gọi cũng vẫn dừng êm (RAII).
- Policy "làm hết" nằm ở vị từ của `wait` và dòng `if (hang_.empty()) return;`: dừng **và** hết việc mới thoát. Policy "bỏ hết" chỉ cần đổi một dòng, và hậu quả thấy ở bản sai 4.

### 4. Chuẩn bảo đảm gì, máy này cho gì

Đa luồng dễ làm ta chép một lần chạy may mắn thành "luật". Bảng dưới tách hai thứ; cột phải là điều mình **đã chạy** (g++ 11.4, libstdc++, máy có 8 luồng phần cứng).

| Điều | Chuẩn bảo đảm | Máy này cho |
|---|---|---|
| Kết quả `get()` | Đúng giá trị (hoặc ngoại lệ) của việc đó; việc xong **đồng bộ-với** lúc `get()` trả về (mọi thứ việc ghi trước khi xong, luồng gọi `get()` đều thấy), nên đọc ô mà việc đã ghi, sau `get()`, là an toàn không cần khóa | `bang = 100 200 300 400`, TSan sạch (30 lần) |
| Không `get()`, chỉ `sleep_for` rồi đọc | Data race, hành vi không xác định | in vẫn đúng, nhưng TSan báo race ở 27 trên 30 lần, 3 lần im |
| Thứ tự **xong** của các việc | Không bảo đảm; chuẩn cũng không nói worker nào nhận việc nào | chương trình riêng nộp 9 việc ngủ 2 đến 4 ms: 5 trên 6 lần xong theo `0 1 3 2 4 6 5 7 8`, một lần `0 1 2 3 4 6 5 7 8` |
| `join` chính luồng đang chạy | Lỗi `resource_deadlock_would_occur` | `Resource deadlock avoided` |
| `packaged_task` hủy khi chưa chạy | `future` nhận `broken_promise` | `Broken promise` (bản sai 4) |

## 💻 Ví dụ code

### Lời giải (a): pool trả future

```cpp
#include <condition_variable>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

class NhomLuong {
public:
    NhomLuong(int n) {
        for (int i = 0; i < n; ++i) {
            worker_.emplace_back([this] { chay(); });
        }
    }

    template <class F>
    std::future<std::invoke_result_t<F>> submit(F f) {             // (1) F là kiểu gì cũng được
        using R = std::invoke_result_t<F>;                         // (2) kiểu f() trả về
        auto goi = std::make_shared<std::packaged_task<R()>>(std::move(f));  // (3)
        std::future<R> kq = goi->get_future();                     // (4) lấy phiếu TRƯỚC khi nộp
        {
            std::lock_guard<std::mutex> g(khoa_);
            hang_.push([goi] { (*goi)(); });                       // (5) hộp copy được, bên trong chỉ một gói
        }
        cv_.notify_one();
        return kq;                                                 // (6)
    }

    ~NhomLuong() {
        {
            std::lock_guard<std::mutex> g(khoa_);
            dung_ = true;
        }
        cv_.notify_all();
        for (std::thread& t : worker_) t.join();
    }

private:
    void chay() {
        while (true) {
            std::function<void()> viec;
            {
                std::unique_lock<std::mutex> lk(khoa_);
                cv_.wait(lk, [this] { return !hang_.empty() || dung_; });
                if (hang_.empty()) return;
                viec = std::move(hang_.front());
                hang_.pop();
            }
            viec();                                                // (7) chạy ngoài khóa
        }
    }

    std::mutex khoa_;
    std::condition_variable cv_;
    std::queue<std::function<void()>> hang_;
    bool dung_ = false;
    std::vector<std::thread> worker_;
};

int main() {
    NhomLuong nhom(4);
    std::vector<std::future<int>> cacPhieu;
    for (int i = 1; i <= 8; ++i) {
        cacPhieu.push_back(nhom.submit([i] { return i * i; }));    // (8) việc trả int
    }
    int tong = 0;
    for (std::future<int>& p : cacPhieu) {
        int v = p.get();                                           // (9) chờ đúng việc này xong
        std::cout << v << " ";
        tong += v;
    }
    std::cout << "\ntong = " << tong << "\n";

    std::vector<int> bang(4, 0);                                   // ô int thường, KHÔNG atomic, không khóa
    std::vector<std::future<void>> xong;
    for (int k = 0; k < 4; ++k) {
        xong.push_back(nhom.submit([&bang, k] { bang[k] = (k + 1) * 100; }));   // (10) việc void, ghi ô riêng
    }
    for (std::future<void>& p : xong) p.get();                     // (11) get() là cầu đồng bộ
    std::cout << "bang = " << bang[0] << " " << bang[1] << " " << bang[2] << " " << bang[3] << "\n";

    std::future<std::string> ten = nhom.submit([] { return std::string("xin chao"); });   // (12)
    std::cout << ten.get() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `submit` là template: `F` là kiểu lambda của người gọi; kiểu trả về là `future` của kiểu mà `F` trả |
| (2)-(3) | `R` là kiểu kết quả; `make_shared` dựng một `packaged_task<R()>` từ việc `f` (`std::move` vì `f` có thể cầm thứ chỉ-chuyển), cất trong `shared_ptr` |
| (4) | `get_future()` lấy phiếu **trước** khi nộp: sau khi nộp, worker có thể đang gọi gói, và hai luồng không được đụng một đối tượng cùng lúc |
| (5) | Dưới khóa, đẩy một lambda `[goi]` vào hàng; sao chép lambda chỉ sao chép `shared_ptr`, gói thật chỉ có một |
| (6) | Trả phiếu cho người gọi, ngoài khóa; `notify_one` đã gọi sau khi nhả khóa |
| (7) | Worker lấy hộp việc ra, nhả khóa rồi gọi; `packaged_task` chạy hàm của người dùng và cất kết quả vào trạng thái chung của `future` |
| (8)-(9) | Tám việc trả `int`; vòng `get()` chờ **đúng việc của phiếu đó**, theo thứ tự phiếu nên đầu ra tất định dù việc xong thứ tự nào |
| (10)-(12) | Bốn việc `void` mỗi việc ghi một ô `int` thường của `bang`; `get()` trên `future<void>` không trả gì nhưng **là cầu đồng bộ**: sau nó, `main` đọc `bang` an toàn. (12) cho `R` là `std::string`: cùng một `submit` làm cho mọi kiểu |

**Kết quả khi chạy** (g++ -std=c++17 -Wall -Wextra -pthread; `-O0` và `-O2` cho cùng đầu ra; 30 lần chạy dưới `setarch x86_64 -R` với `-fsanitize=thread` đều giống nhau và TSan không báo gì):

```text
1 4 9 16 25 36 49 64 
tong = 204
bang = 100 200 300 400
xin chao
```

**Thử thay đổi 1: nộp lambda có đối số, `nhom.submit([](int x) { return x; });`.** Mình đã chạy: lỗi biên dịch `no type named 'type' in 'struct std::invoke_result<main()::<lambda(int)> >'`, vì `invoke_result_t<F>` hỏi "gọi `F` không đối số trả gì" mà `F` đòi một `int`. Muốn truyền đối số, người gọi bọc lại: `submit([x] { return x; })`. Bản thư viện nhận thêm `Args&&... args` rồi chuyển tiếp; mình bỏ để bài không vướng cú pháp ngoài phạm vi.

**Thử thay đổi 2: nộp lambda chỉ-chuyển, `[p = std::move(p)] { return *p + 1; }` với `p` là `unique_ptr<int>`.** (Đây là init-capture của [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md): tạo biến `p` mới trong lambda từ biểu thức bên phải.) Mình đã chạy: ra `42`, vì `packaged_task` nhận được thứ chỉ-chuyển; chỉ cái hộp `std::function` mới đòi sao chép, và ta chỉ cho nó giữ `shared_ptr`.

### Bản SAI của (a): ba lỗi điển hình

**Sai 1: cất thẳng `packaged_task` vào hộp, không qua `shared_ptr`.** Thay (3)-(5) bằng đoạn dưới (`goi` là `packaged_task` thường; `mutable` cho phép gọi nó trong lambda; `[g = std::move(goi)]` chuyển gói vào lambda):

```cpp
// bo-qua-kiem-tra
std::packaged_task<R()> goi(std::move(f));
std::future<R> kq = goi.get_future();
hang_.push([g = std::move(goi)]() mutable { g(); });   // hang_ là queue<std::function<void()>>
```

Mình chạy: không biên dịch được, `error: static assertion failed: std::function target must be copy-constructible`. Gói chỉ-chuyển làm lambda chỉ-chuyển, mà `std::function` (C++17) đòi sao chép được. C++23 có `std::move_only_function` làm đúng việc này; mình chỉ nhắc tên, không chạy vì g++ 11 chưa có.

**Sai 2: việc chờ việc trong cùng pool.** Pool 2 worker, nộp hai việc, mỗi việc nộp thêm một việc con vào **cùng** pool rồi `get()` ngay:

```cpp
// bo-qua-kiem-tra
NhomLuong nhom(2);
for (int i = 1; i <= 2; ++i)
    cacPhieu.push_back(nhom.submit([&nhom, i] {
        std::future<int> trong = nhom.submit([i] { return i * 10; });   // việc con vào cùng pool
        return trong.get() + 1;                                          // worker này ngủ chờ việc con
    }));
```

Mình chạy ba lần với `timeout 3`: cả ba mã **124**, không in gì. Hai worker đều đang ngủ trong `get()` chờ hai việc con, mà hai việc con nằm trong hàng và chỉ worker mới chạy được chúng: không ai rảnh. Đổi `NhomLuong nhom(3)` thì ra `11` rồi `21` mã 0, **đúng vì may** (có worker thứ ba rảnh). Với ba việc ngoài thì ba worker cũng kẹt: đúng/sai tùy số worker so với độ sâu việc chờ việc.

**Sai 3: đọc kết quả mà không qua `get()`.** Thay dòng (11) bằng `std::this_thread::sleep_for(std::chrono::milliseconds(200));` (thêm `#include <chrono>`):

```cpp
// bo-qua-kiem-tra
for (int k = 0; k < 4; ++k) xong.push_back(nhom.submit([&bang, k] { bang[k] = (k + 1) * 100; }));
std::this_thread::sleep_for(std::chrono::milliseconds(200));   // "đủ lâu rồi", không phải đồng bộ
std::cout << "bang = " << bang[0] << " " << bang[1] << " " << bang[2] << " " << bang[3] << "\n";
```

Không bật TSan, chương trình vẫn in `bang = 100 200 300 400`. Dưới TSan (30 lần): 27 lần báo `WARNING: ThreadSanitizer: data race` với `Read of size 4 ... by main thread` đối chiếu `Previous write of size 4 ... by thread T3` và dòng `As if synchronized via sleep` (TSan nói thẳng: bạn đang coi `sleep` như đồng bộ). Số báo cáo mỗi lần từ 1 đến 4; 3 lần **không báo gì** dù lỗi vẫn còn. "TSan sạch" chỉ nghĩa là lần chạy đó không thấy, không chứng minh đúng.

### Chi phí và độ phức tạp của (a)

| Mặt | Kết quả |
|---|---|
| Độ phức tạp | `submit` O(1) trung bình (đẩy vào `queue`); lấy việc O(1); bộ nhớ O(số việc đang chờ) |
| Khóa | mỗi việc 2 lần khóa mutex (đẩy, lấy) và một `notify_one`; một hàng đợi chung nên khóa này là điểm nghẽn khi việc cực ngắn và nhiều worker |
| Cấp phát | mình thay `operator new` bằng bản đếm, nộp 1000 việc vào pool **không worker**: `submit` có future ra **4,07** lần cấp phát mỗi việc, còn `submit` kiểu `void` của Bài 30 ra 0,06 (chỉ là khối `deque` thỉnh thoảng xin thêm). Số 4 là của libstdc++ g++ 11, chuẩn không nói |
| Thời gian `submit` | cũng pool không worker, 200000 việc: kiểu `void` 21 đến 49 ns mỗi việc ở `-O2` (149 đến 244 ns không tối ưu), có future 152 đến 443 ns (1467 đến 1759 ns): đắt gấp **5 đến 10 lần**. Máy lúc đo bận nên đổi nhiều |
| Có đáng không | cỡ 0,2 đến 1,7 micro-giây là nhỏ so với việc đáng song song (từ hàng chục micro-giây, Bài 30); việc nhỏ hơn thì gộp lô |

Chỉ cần chạy mà không cần kết quả thì `submit` kiểu `void` rẻ hơn rõ.

### Lời giải (b): dừng êm

Lớp giữ nguyên ba mảnh. Chỉ khác ba chỗ so với (a): kiểm cờ trong `submit` (1), `shutdown()` tách riêng (2)-(3), hàm hủy gọi nó (4).

```cpp
#include <atomic>
#include <condition_variable>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <vector>

class NhomLuong {
public:
    NhomLuong(int n) {
        for (int i = 0; i < n; ++i) {
            worker_.emplace_back([this] { chay(); });
        }
    }

    template <class F>
    std::future<std::invoke_result_t<F>> submit(F f) {
        using R = std::invoke_result_t<F>;
        auto goi = std::make_shared<std::packaged_task<R()>>(std::move(f));
        std::future<R> kq = goi->get_future();
        {
            std::lock_guard<std::mutex> g(khoa_);
            if (dung_) throw std::runtime_error("pool da dong");   // (1) kiểm cờ CÙNG khóa với push
            hang_.push([goi] { (*goi)(); });
        }
        cv_.notify_one();
        return kq;
    }

    void shutdown() {                                              // (2) dừng êm, gọi bao nhiêu lần cũng được
        {
            std::lock_guard<std::mutex> g(khoa_);
            dung_ = true;
        }
        cv_.notify_all();
        for (std::thread& t : worker_) {
            if (t.joinable()) t.join();                            // (3) join lần hai: joinable() == false, bỏ qua
        }
    }

    ~NhomLuong() { shutdown(); }                                   // (4) RAII: hủy pool cũng dừng êm

private:
    void chay() {
        while (true) {
            std::function<void()> viec;
            {
                std::unique_lock<std::mutex> lk(khoa_);
                cv_.wait(lk, [this] { return !hang_.empty() || dung_; });
                if (hang_.empty()) return;                         // (5) chỉ thoát khi đã dừng VÀ hết việc
                viec = std::move(hang_.front());
                hang_.pop();
            }
            viec();                                                // (6) packaged_task tự bắt ngoại lệ
        }
    }

    std::mutex khoa_;
    std::condition_variable cv_;
    std::queue<std::function<void()>> hang_;
    bool dung_ = false;
    std::vector<std::thread> worker_;
};

int main() {
    std::atomic<int> daChay{0};
    std::vector<std::future<int>> cacPhieu;
    NhomLuong nhom(3);
    for (int i = 1; i <= 20; ++i) {
        cacPhieu.push_back(nhom.submit([&daChay, i] { ++daChay; return i; }));
    }
    std::future<int> loi = nhom.submit([]() -> int { throw std::runtime_error("loi tinh toan"); });  // (7)

    nhom.shutdown();                                               // (8) chờ hết 21 việc
    std::cout << "da chay: " << daChay << " viec\n";

    int tong = 0;
    for (std::future<int>& p : cacPhieu) tong += p.get();          // (9) phiếu vẫn lấy được sau khi pool đóng
    std::cout << "tong = " << tong << "\n";

    try {
        loi.get();                                                 // (10) ngoại lệ đi qua future
    } catch (const std::exception& e) {
        std::cout << "viec loi: " << e.what() << "\n";
    }

    try {
        nhom.submit([] { return 0; });                             // (11) nộp sau khi đóng
    } catch (const std::exception& e) {
        std::cout << "nop sau khi dong: bi tu choi (" << e.what() << ")\n";
    }

    nhom.shutdown();                                               // (12) gọi lần hai: không sao
    std::cout << "shutdown lan hai: khong sao\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `submit` kiểm `dung_` **dưới cùng khóa** với `push`: hoặc việc vào hàng trước khi cờ bật (sẽ được làm), hoặc bị từ chối; không có khe ở giữa |
| (2)-(3) | `shutdown()`: đặt cờ dưới khóa, đánh thức mọi worker, `join`; lần gọi hai thì `joinable()` là `false` nên bỏ qua |
| (4) | Hàm hủy gọi `shutdown()`: hết phạm vi là dừng êm, kể cả khi có ngoại lệ |
| (5) | Worker chỉ thoát khi hàng **rỗng** và cờ đã bật: việc còn lại được làm hết rồi mới thoát |
| (6) | Việc nộp qua `submit` là `packaged_task`: ngoại lệ của hàm người dùng bị nó bắt và cất vào `future`, nên không thoát ra khỏi hàm của worker |
| (7) | Lambda không có `return` sẽ bị suy ra là `void`, nên viết `-> int` để khẳng định nó trả `int` (và nhận `future<int>`); dòng này chỉ ném |
| (8)-(10) | `shutdown()` trả khi 21 việc đã chạy xong; các phiếu cũ **vẫn lấy được** sau khi pool đóng vì kết quả nằm trong trạng thái chung của `future`, không nằm trong pool; `get()` của việc lỗi ném lại đúng ngoại lệ |
| (11)-(12) | Nộp sau khi đóng bị từ chối bằng ngoại lệ; `shutdown()` lần hai trả ngay |

**Kết quả khi chạy** (30 lần dưới TSan, đầu ra giống nhau, TSan sạch; ba lần thường cũng giống):

```text
da chay: 20 viec
tong = 210
viec loi: loi tinh toan
nop sau khi dong: bi tu choi (pool da dong)
shutdown lan hai: khong sao
```

**Thử thay đổi 1: một việc gọi `shutdown()` của chính pool.** Pool 1 worker, việc `[&n2] { n2.shutdown(); }` bắt ngoại lệ rồi trả `e.what()`. Mình đã chạy: `Resource deadlock avoided` (một `std::system_error`): `shutdown()` bảo worker `join` mọi luồng, kể cả chính nó. Chuẩn quy định đây là lỗi `resource_deadlock_would_occur`, nên pool thật cấm hoặc phát hiện `shutdown` từ worker.

**Thử thay đổi 2: việc đang chạy nộp thêm việc khi pool đang dừng.** Pool 2 worker, việc A báo "đã bắt đầu", ngủ 100 ms rồi gọi `nhom.submit(...)`; `main` chờ tín hiệu rồi `shutdown()`. Mình đã chạy: A nhận ngoại lệ `pool da dong`, tức là việc đang dở cũng **không** nộp thêm được. Ai muốn cho phép việc con trong lúc dừng thì phải đổi policy (đếm "việc đang chạy" và chỉ đóng khi bằng 0): bài này không làm.

### Bản SAI của (b): hai lỗi điển hình

**Sai 4: dừng là bỏ, kệ việc còn trong hàng.** Đổi dòng (5) thành:

```cpp
// bo-qua-kiem-tra
if (dung_) return;      // SAI: cờ dừng bật là thoát, dù hàng còn việc
```

Kịch bản: pool 1 worker, việc 0 báo "đã bắt đầu" rồi ngủ 100 ms, nộp thêm bốn việc, `main` chờ tín hiệu rồi hủy pool, rồi `get()` cả năm phiếu. Mình chạy 100 lần, **cả 100 lần** ra đúng một kết quả:

```text
viec 0: 0
viec 1: future_error: std::future_error: Broken promise
viec 2: future_error: std::future_error: Broken promise
viec 3: future_error: std::future_error: Broken promise
viec 4: future_error: std::future_error: Broken promise
```

Việc 0 đang chạy nên xong; bốn việc còn lại bị bỏ trong hàng, hộp bị hủy kéo theo `packaged_task` bị hủy chưa chạy, nên mỗi `future` nhận `broken_promise` (đúng như bảng chuẩn). Cần "bỏ hết" cố ý thì làm rõ (xóa hàng dưới khóa) và nói với người dùng; vô tình thì là bug. Mình cần việc 0 báo "đã bắt đầu" để kịch bản tất định; thiếu tín hiệu đó, worker còn có thể chưa kịp lấy việc 0.

**Sai 5: không chặn việc nộp sau khi đóng.** Bỏ dòng `if (dung_) throw ...` ở (1), rồi nộp sau `shutdown()`:

```cpp
// bo-qua-kiem-tra
NhomLuong nhom(2);
nhom.shutdown();
std::future<int> p = nhom.submit([] { return 42; });   // không bị từ chối, không ai chạy
if (p.wait_for(std::chrono::milliseconds(300)) == std::future_status::timeout)
    std::cout << "sau 300 ms viec van chua chay\n";
std::cout << p.get() << "\n";                           // chờ mãi
```

Mình chạy với `timeout 3`: in `sau 300 ms viec van chua chay` rồi `get() ...`, mã thoát **124**. Việc nằm trong hàng, hết worker để chạy, và gói vẫn sống trong hàng của pool nên chưa bị coi là bỏ rơi: không có `broken_promise` để cứu, `get()` chờ mãi. Đây là lý do người phỏng vấn hay hỏi "nộp muộn thì sao".

### Chi phí và độ phức tạp của (b)

| Mặt | Kết quả |
|---|---|
| `shutdown()` | O(số worker + thời gian làm hết việc còn lại / số worker); không mất việc nào |
| Policy "làm hết" | an toàn cho người giữ phiếu nhưng `shutdown()` có thể mất lâu nếu hàng dài; muốn dừng nhanh thì policy "bỏ" (xóa hàng, người giữ phiếu nhận `broken_promise`) |
| Hàng đợi không giới hạn | người nộp nhanh hơn worker thì hàng phình mãi: bộ nhớ lớn dần. Giải pháp là hàng chặn có giới hạn ([Bài 66](66-bounded-queue.md)): `submit` chờ khi đầy |
| Gọi `shutdown()` từ hai luồng cùng lúc | chưa an toàn: hai luồng cùng `join` một `std::thread` là hành vi không xác định; pool thật thêm một khóa, hoặc quy ước một chủ sở hữu |

!!! info "Bạn biết Go?"
    Go không có `future` chuẩn. Quen thuộc nhất: `Submit` trả một **channel có đệm 1** (`ch := make(chan KetQua, 1)`) mà worker gửi kết quả (cả `error`) vào, `<-ch` thay `get()` ([Bài 29](../nhom-3-da-luong/29-async-future.md)). Dừng êm là `close(jobs)` rồi `wg.Wait()`: vòng `for job := range jobs` làm hết việc còn lại rồi thoát, cùng policy "làm hết" của bài này. Khác chỗ quan trọng: gửi vào channel **đã đóng** thì `panic` ("send on closed channel"), còn C++ ta tự chọn cách báo (bài này ném ngoại lệ). Mình đã chạy một pool nhỏ theo đúng mô tả này bằng `go run -race` (Go 1.27.2): 3 worker, `close(jobs)` rồi `wg.Wait()` làm hết cả 8 việc (một việc trả lỗi qua channel đệm 1), `-race` sạch; gửi thêm vào `jobs` đã đóng thì `panic: send on closed channel` (mình bắt bằng `recover`).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết cho tôi một thread pool có `submit` trả kết quả."
    Mình hỏi lại: việc có tham số và ngoại lệ không. Rồi vẽ ba mảnh: hàng đợi `std::function<void()>` dưới mutex, `condition_variable`, N worker chạy việc **ngoài khóa**. `submit` là template: `R = invoke_result_t<F>`, tạo `packaged_task<R()>` bọc trong `shared_ptr` (vì `std::function` đòi sao chép được mà `packaged_task` thì không), `get_future()` trước khi đẩy, đẩy `[goi] { (*goi)(); }` dưới khóa, `notify_one`, trả phiếu.
    **Nối tiếp 1:** "Vì sao phải bọc `shared_ptr`?" Vì `std::function` yêu cầu thứ nó chứa sao chép được; mình chạy bản không bọc ra `static assertion failed: ... must be copy-constructible`. C++23 có `std::move_only_function` để khỏi bọc.
    **Nối tiếp 2:** "Một việc trong pool nộp việc con rồi `get()` thì sao?" Có thể kẹt: mọi worker ngủ chờ việc con mà việc con không có worker nào chạy (mình chạy 2 worker, treo mã 124). Tránh bằng: việc không chờ việc cùng pool, hoặc worker rảnh tự "giúp" chạy việc con khi chờ, hoặc dùng hai pool.

??? question "Dừng pool thế nào cho êm?"
    Bốn việc: từ chối việc mới (`submit` kiểm cờ dưới **cùng khóa** với `push`), làm hết việc đã nhận (worker thoát khi dừng **và** hàng rỗng), `join` mọi worker, và để hàm hủy gọi lại `shutdown()` (RAII). Ngoại lệ không cần xử lý riêng vì `packaged_task` cất nó vào `future`.
    **Nối tiếp 1:** "Còn việc trong hàng khi đóng thì làm hay bỏ?" Là policy phải nói rõ: "làm hết" an toàn cho người giữ phiếu; "bỏ" thì người giữ phiếu nhận `broken_promise` (mình chạy bản bỏ vô tình: 4 phiếu `Broken promise`). 
    **Nối tiếp 2:** "Nộp việc khi đã đóng?" Phải từ chối rõ (ném, hay trả lỗi); im lặng nhận thì `get()` chờ mãi (mình chạy: mã 124). **Nối tiếp 3:** "Worker tự gọi `shutdown()`?" `join` chính nó: `Resource deadlock avoided`.

??? question "Bao nhiêu worker, và một hàng đợi chung có đủ không? Work stealing là gì?"
    Số worker theo Bài 30: việc nặng CPU xấp xỉ `hardware_concurrency()`, việc chờ I/O nhiều hơn; đo chứ không đoán. Một hàng đợi chung có **một khóa**: mỗi việc 2 lần khóa, nên khi việc cực ngắn và worker đông, khóa thành nút thắt. Cách giảm ở mức nguyên lý: mỗi worker một hàng đợi riêng (hầu như không tranh chấp), worker rảnh thì **trộm** việc từ đầu kia hàng của worker khác (**work stealing**). Chủ lấy một đầu, kẻ trộm lấy đầu kia nên ít đụng nhau.
    **Nối tiếp:** "Bạn có cài work stealing không?" Mình chỉ nói được nguyên lý; mình **không cài và không đo** ở bài này. Hàng đợi chung đủ cho đa số việc cỡ vừa; chỉ khi đo thấy khóa là nghẽn thì mới đổi, vì work stealing phức tạp hơn nhiều (và khó đúng, như mọi thứ gần lock-free).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Cất `packaged_task` thẳng vào `std::function`"
    Gói chỉ-chuyển làm lambda chỉ-chuyển, `std::function` (C++17) từ chối: `static assertion failed` lúc biên dịch. Bọc `shared_ptr`, hoặc dùng `move_only_function` (C++23).

!!! warning "Lỗi 2: Hứa quá lời khi nói trên bảng"
    Đừng nói "kết quả ra theo thứ tự nộp": chỉ **phiếu** theo thứ tự, thứ tự xong thì không (mình chạy: 5 trên 6 lần `0 1 3 2 ...`). Đừng nói "TSan sạch tức là đúng": mình có 3 trên 30 lần lỗi thật mà TSan im.

!!! warning "Lỗi 3: Việc chờ việc, và quên chuyện nộp muộn"
    Pool nhỏ + việc `get()` việc con của cùng pool là treo (mã 124), đúng hay sai tùy số worker. Và "dừng" mà không nói việc còn lại ra sao, nộp muộn ra sao là thiếu đúng hai câu người phỏng vấn sẽ hỏi.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="67" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau, trong `submit` của pool có hàng đợi `std::queue<std::function<void()>> hang_`. Điều gì xảy ra khi biên dịch?

```text
std::packaged_task<R()> goi(std::move(f));
std::future<R> kq = goi.get_future();
hang_.push([g = std::move(goi)]() mutable { g(); });
```

- Biên dịch được, vì `std::move` đã chuyển gói vào lambda một cách an toàn
- Lỗi biên dịch, vì `std::function` đòi thứ nó chứa phải sao chép được
- Biên dịch được nhưng hai worker có thể cùng gọi một gói, nên chạy sai
- Lỗi biên dịch, vì `mutable` không dùng chung được với init-capture

<p class="giai-thich" markdown>Lambda giữ một `packaged_task` chỉ-chuyển nên chính nó chỉ-chuyển, mà `std::function` (C++17) yêu cầu thứ nó chứa sao chép được: g++ báo `static assertion failed: ... must be copy-constructible`. `std::move` đúng nhưng không giúp qua yêu cầu đó của `std::function`. Hai worker cùng gọi một gói không xảy ra vì đây là lỗi lúc biên dịch, không chạy tới. Còn `mutable` và init-capture dùng chung được, đoạn này chỉ sai ở chỗ khác.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Worker của pool thoát ngay khi cờ dừng bật, kể cả khi hàng còn việc (`if (dung_) return;`). Pool có 1 worker, một việc đang chạy và bốn việc đang nằm trong hàng, rồi pool bị hủy. Người giữ phiếu của bốn việc đó gọi `get()`. Chuyện gì xảy ra?

- Treo mãi, vì phiếu chưa có kết quả và không ai đặt kết quả cho nó
- Nhận giá trị mặc định (`0` với `int`), vì việc bị bỏ nên trả giá trị rỗng
- Chương trình gọi `std::terminate`, vì phiếu bị hủy khi còn việc chưa chạy
- Nhận ngoại lệ `std::future_error` (`broken_promise`) ngay, không chờ

<p class="giai-thich" markdown>Khi pool bị hủy, hàng đợi bị hủy, các gói `packaged_task` chưa chạy bị hủy theo; chuẩn quy định một gói bị hủy khi chưa chạy thì `future` của nó nhận `future_error` với `broken_promise` (mình chạy: `Broken promise`). Không treo, vì trạng thái đã được đặt thành lỗi. Không có giá trị mặc định nào được bịa ra. Và `std::terminate` chỉ đến khi ngoại lệ thoát khỏi hàm của luồng, còn ở đây nó nằm gọn trong `future`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn sau. Pool có đúng 2 worker; hai việc ngoài được nộp, mỗi việc làm như dưới. Điều nào đúng?

```text
auto f = pool.submit(viecCon);   // nộp việc con vào CÙNG pool
return f.get();                  // rồi chờ ngay trên worker
```

- Có thể treo mãi: cả hai worker ngủ chờ việc con mà không ai chạy được
- Chạy bình thường, vì việc con xếp hàng và `get()` tự chạy nó trên luồng gọi
- Ném `broken_promise`, vì việc con bị nộp khi pool đang bận
- Chạy bình thường nhưng chậm, vì việc con chỉ được chạy khi worker rảnh

<p class="giai-thich" markdown>Cả hai worker đang kẹt trong `get()`, còn hai việc con nằm trong hàng và chỉ worker mới lấy được: không ai rảnh, nên treo (mình chạy ba lần, cả ba mã 124). `get()` chỉ chờ, không tự chạy việc. `broken_promise` chỉ khi gói bị hủy chưa chạy, mà ở đây gói còn sống trong hàng. Và "chậm" sai vì chờ **mãi mãi** khác với chờ lâu: không worker nào trở nên rảnh.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** `submit` không kiểm cờ dừng. Sau `shutdown()`, ai đó nộp một việc và giữ phiếu, pool vẫn còn sống. Kết quả cho người giữ phiếu khi gọi `get()` là gì?

- Việc chạy ngay trên luồng gọi `submit`, vì không còn worker nào khác
- Ném `broken_promise` ngay, vì pool đã đóng nên việc bị coi là bỏ rơi
- Chờ mãi, vì gói nằm trong hàng mà không còn worker nào chạy nó
- Trả giá trị rỗng, vì pool đã đóng nên việc bị hủy bỏ

<p class="giai-thich" markdown>Gói vẫn được giữ trong hàng đợi của pool còn sống nên chưa bị hủy và chưa bị coi là bỏ rơi, không có `broken_promise` nào được đặt; không worker nào còn để chạy nó nên `get()` chờ mãi (mình chạy: mã 124). Việc không tự chạy trên luồng gọi, vì `submit` chỉ đẩy vào hàng. Thư viện cũng không bịa giá trị rỗng. Cách sửa là chặn ngay lúc nộp, trong cùng khóa với `push`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Việc `void` ghi `bang[k]` (một `int` thường) và `main` đọc `bang[k]` sau `sleep_for(200ms)`, không gọi `get()`. Nhận xét nào đúng?

- An toàn, vì 200 ms đủ lâu để mọi việc chắc chắn đã xong
- Là data race theo chuẩn, và đầu ra đúng chỉ là may
- An toàn, vì mỗi việc ghi một ô riêng nên không đụng nhau
- Là data race, và TSan luôn báo ở mọi lần chạy

<p class="giai-thich" markdown>`sleep_for` không tạo quan hệ đồng bộ giữa luồng ghi và luồng đọc, nên đây vẫn là data race dù chương trình in đúng; TSan còn ghi `As if synchronized via sleep`. Ô riêng chỉ giúp các việc không đụng nhau, còn `main` đọc ô mà việc kia ghi thì cần đồng bộ (`get()` làm việc đó). "TSan luôn báo" sai: mình chạy 30 lần, 3 lần im, vì công cụ chỉ báo điều nó thấy trong lần chạy đó. Còn "200 ms đủ lâu" là suy nghĩ về thời gian, chuẩn thì chỉ nói về quan hệ đồng bộ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Một việc đang chạy trong pool tự gọi `pool.shutdown()`, trong đó mọi worker bị `join`. Điều nào đúng?

- Ném `std::system_error`: `join` lên chính luồng đó là lỗi deadlock
- Chạy êm, vì `join` luồng đang chạy sẽ trả ngay khi việc đó kết thúc
- Treo mãi ở `join`, vì chuẩn bảo đảm luồng tự `join` chính mình là treo
- Gọi `std::terminate`, vì hủy `std::thread` còn joinable khi đang chạy

<p class="giai-thich" markdown>`join` lên chính luồng đang chạy là lỗi mà chuẩn gọi tên là `resource_deadlock_would_occur`, và libstdc++ báo bằng `std::system_error` với thông điệp `Resource deadlock avoided` (mình chạy). Không phải chạy êm, vì việc đang chờ chính nó kết thúc nên không bao giờ trả ngay. Chuẩn không hứa "treo mãi" mà hứa một lỗi. `std::terminate` ở đây không do `join` này: ngoại lệ do `join` ném ra nằm trong một việc nộp qua `submit`, nên `packaged_task` bắt nó và cất vào `future`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Nâng cấp pool của [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md): `submit` là template, kiểu kết quả `R = std::invoke_result_t<F>`, gói `std::packaged_task<R()>` trong `std::shared_ptr` (vì `std::function` đòi sao chép được, mình chạy bản không bọc ra `static assertion failed`), `get_future()` trước khi đẩy, đẩy dưới khóa; `submit` kiểu future đắt cỡ 4 cấp phát và gấp 5 đến 10 lần `submit` `void` (mình đo, đổi theo máy).
2. Kết quả và ngoại lệ đi qua `future`: `get()` là **cầu đồng bộ** nên đọc dữ liệu việc đã ghi sau `get()` là an toàn; thay bằng `sleep_for` thì là data race (TSan báo 27 trên 30 lần, 3 lần im: "sạch" không chứng minh đúng). Thứ tự xong của việc không được bảo đảm, chỉ thứ tự phiếu.
3. Dừng êm = từ chối việc mới (kiểm cờ dưới **cùng khóa** với `push`), làm hết việc đã nhận (worker thoát khi dừng và hàng rỗng), `join`, gọi lại được, hàm hủy gọi `shutdown()`. Bỏ việc còn lại thì phiếu nhận `broken_promise`; không chặn nộp muộn thì `get()` treo (mã 124).
4. Bẫy bảng trắng: việc chờ việc trong cùng pool treo (đúng hay sai tùy số worker), `shutdown()` từ worker là `Resource deadlock avoided`, hai luồng cùng `shutdown()` chưa an toàn, hàng đợi không giới hạn phình bộ nhớ (cần hàng chặn, [Bài 66](66-bounded-queue.md)).
5. Nói được ở mức lời: số worker theo loại việc (đo), work stealing giảm tranh chấp khóa của một hàng đợi chung nhưng phức tạp (mình không cài, không đo), `move_only_function` là C++23. Go dùng channel có đệm 1 làm phiếu và `close` rồi `wg.Wait()` để dừng êm; gửi vào channel đã đóng là `panic` (mình chạy một pool Go nhỏ: `-race` sạch).
