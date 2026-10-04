# Bài 29 — std::async và std::future: lấy kết quả (và ngoại lệ) từ luồng khác

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao `std::thread` thuần khó lấy kết quả về (phải dùng biến chung) và làm ngoại lệ trong luồng gọi `std::terminate`; dùng `std::async` + `std::future` để giao việc và nhận kết quả bằng `get()`, kể cả khi tác vụ ném ngoại lệ.
    - Biết `get()` chỉ lấy được **một** lần (lần hai là lỗi, chạy thật), dùng `valid()`, `wait()`, `wait_for`, và nói đúng về `std::launch::async`, `deferred` và chế độ mặc định theo chuẩn.
    - Tránh cái bẫy "bỏ future đi thì tác vụ chạy tuần tự" (đo thật), và chia việc cộng một dãy lớn cho 4 `async` rồi gộp bằng `get()`.
    - Dùng `std::promise` (một luồng đặt giá trị hoặc ngoại lệ, luồng kia chờ), biết `broken_promise`, nhắc `packaged_task` và `shared_future`; nối với channel của Go.

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, `std::ref`, `sleep_for`, `std::chrono`, `std::terminate` vì ngoại lệ trong luồng), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (`throw`/`try`/`catch`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (`e.what()`, hành vi không xác định), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`auto`, lambda), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector<...>`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (`accumulate`, `std::function<bool(int)>`), [Bài 25](25-data-race-mutex.md) (data race, TSan).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](25-data-race-mutex.md). Đầu bếp chính giao một món cho đầu bếp phụ rồi nhận lại một **phiếu hẹn**. Chính tiếp tục việc của mình; khi cần món, chính ra quầy đưa phiếu. Món xong thì nhận ngay; chưa xong thì đứng chờ. Phiếu hẹn là `std::future`, việc đưa phiếu là `get()`.

Món đã giao đi thì không giao lần nữa: sau khi lấy món, phiếu hết hiệu lực. Nếu phụ làm cháy món, phụ để lại **biên bản cháy** thay cho món, và chính đọc biên bản đó khi đưa phiếu. Còn `std::promise` là cái khay ở quầy dành cho phụ đặt món (hoặc biên bản) lên, cho người đang cầm phiếu.

!!! info "Chỗ nào ví von phiếu hẹn không còn đúng?"
    Phiếu hẹn giấy thì photo được; `std::future` thì **không sao chép được** (chỉ chuyển, như `std::thread` ở Bài 24). Phiếu giấy vứt đi không sao; còn future do `std::async` trả về mà bị hủy khi món chưa xong thì chương trình **đứng chờ** món xong (mục 5). Việc "chia một sổ số lớn cho bốn phụ cộng mỗi người một đoạn" thì không cần thẻ thớt, vì ai cũng chỉ **đọc** sổ.

## 📖 Giải thích

### 1. Vấn đề của `std::thread` thuần

Hàm chạy trong `std::thread` không trả giá trị về cho ai: `std::thread` không có chỗ nào để nhận. Cách duy nhất là luồng ghi vào một biến chung rồi luồng chính đọc sau `join`.

```cpp
#include <iostream>
#include <thread>

int main() {
    int ketQua = 0;                                  // (1) biến chung để "lấy" kết quả
    std::thread t([&ketQua] { ketQua = 6 * 7; });    // (2) luồng ghi vào biến của main
    t.join();                                        // (3) join xong mới đọc: an toàn
    std::cout << "ket qua = " << ketQua << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | `ketQua` |
|---|---|---|
| (1) | `main` tạo biến | 0 |
| (2) | Luồng nhận tham chiếu tới `ketQua` (Bài 24: `[&x]`) và ghi 42 | 42 |
| (3) | `join` chờ luồng xong, nên đọc sau đó không có data race | 42 |

**Kết quả khi chạy:** `ket qua = 42`. Chạy đúng, nhưng mỗi kết quả cần một biến, phải nhớ `join` trước khi đọc, và nếu luồng chạy lâu thì không có cách "chờ riêng kết quả này". Nhiều luồng ghi chung một biến thì còn cần mutex.

Chuyện tệ hơn là ngoại lệ ([Bài 24](24-thread-co-ban.md)): ném ra khỏi hàm của luồng thì không `catch` nào ở `main` bắt được.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <stdexcept>
#include <thread>

int main() {
    try {
        std::thread t([] { throw std::runtime_error("loi trong luong"); });
        t.join();
    } catch (const std::exception& e) {
        std::cout << "bat duoc: " << e.what() << "\n";   // không bao giờ tới đây
    }
    return 0;
}
```

Mình chạy: in `terminate called after throwing an instance of 'std::runtime_error'` và `what():  loi trong luong`, mã thoát 134. Dòng `catch` của `main` không chạy. `std::future` giải quyết cả hai chuyện.

### 2. `std::async` trả về `std::future`

`std::async(std::launch::async, hàm, đối số...)` (cần `#include <future>`) bảo C++ chạy `hàm(đối số...)` trên một luồng riêng, và **ngay lập tức** trả về một `std::future<T>`, với `T` là kiểu trả về của hàm. Cặp `<T>` đọc như `vector<int>` ở [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md): `future<int>` là phiếu hẹn cho một `int`. Đối số được **sao chép** vào luồng như ở Bài 24 (muốn tham chiếu thì `std::ref`).

```cpp
#include <future>
#include <iostream>

int binhPhuong(int x) { return x * x; }

int main() {
    std::future<int> f = std::async(std::launch::async, binhPhuong, 7);   // (1)
    std::cout << "valid truoc get: " << f.valid() << "\n";                // (2)
    int kq = f.get();                                                     // (3)
    std::cout << "kq = " << kq << "\n";
    std::cout << "valid sau get: " << f.valid() << "\n";                  // (4)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Phiếu `f` |
|---|---|---|
| (1) | Một luồng bắt đầu tính `binhPhuong(7)`; `main` nhận phiếu ngay | đang giữ chỗ cho một `int` |
| (2) | `valid()` hỏi "phiếu này còn gắn với một kết quả không?" | `1` (có) |
| (3) | `get()` chờ luồng xong (nếu chưa) rồi trả 49 | kết quả đã được lấy ra |
| (4) | Sau `get()`, phiếu không còn gắn với gì | `0` |

**Kết quả khi chạy:**

```text
valid truoc get: 1
kq = 49
valid sau get: 0
```

TSan sạch (mã 0). `get()` chờ xong rồi mới trả, nên không cần `join`: luồng do `async` tạo được future lo.

Ba thao tác khác của future:

- `valid()`: `true` nếu future còn gắn với một kết quả chưa lấy.
- `wait()`: chờ cho tới khi có kết quả nhưng **không** lấy ra (sau đó vẫn `get()` được).
- `wait_for(thời gian)`: chờ tối đa chừng đó rồi trả `std::future_status::ready` (đã xong), `timeout` (chưa), hoặc `deferred` (mục 4). Mình chạy một tác vụ ngủ 200 ms: `wait_for` 50 ms ra `timeout`, sau `wait()` ra `ready`. Dùng `std::chrono` như Bài 24.

**`get()` chỉ lấy được một lần.** Lấy kết quả xong là món đã giao đi (nên `valid()` thành `0`).

```cpp
// bo-qua-kiem-tra
#include <future>
#include <iostream>

int main() {
    std::future<int> f = std::async(std::launch::async, [] { return 42; });
    std::cout << f.get() << "\n";
    try {
        std::cout << f.get() << "\n";                // (1) lần hai
    } catch (const std::future_error& e) {
        std::cout << "loi: " << e.what() << "\n";
    }
    return 0;
}
```

Mình chạy trên g++ 11: in `42`, rồi `loi: std::future_error: No associated state`. Chuẩn đòi `valid() == true` trước mỗi `get()`, nên gọi lần hai là lỗi của người gọi. Việc g++ ném `std::future_error` chỉ là cách cài đặt này xử lý; đừng viết code dựa vào nó.


### 3. Ngoại lệ đi qua future

Tác vụ ném ngoại lệ thì `async` **giữ** ngoại lệ lại trong future, và `get()` ném lại nó ở luồng gọi `get()`. Ở `main` bạn `catch` như bình thường.

```cpp
#include <future>
#include <iostream>
#include <stdexcept>

int chia(int a, int b) {
    if (b == 0) throw std::runtime_error("chia cho 0");     // (1) ném TRONG tác vụ
    return a / b;
}

int main() {
    std::future<int> tot = std::async(std::launch::async, chia, 10, 2);
    std::future<int> xau = std::async(std::launch::async, chia, 1, 0);
    std::cout << "tot = " << tot.get() << "\n";
    try {
        std::cout << xau.get() << "\n";                     // (2) ngoại lệ hiện ra ở đây
    } catch (const std::exception& e) {
        std::cout << "bat duoc o get: " << e.what() << "\n";
    }
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Ở luồng nào |
|---|---|---|
| (1) | `chia(1, 0)` ném `runtime_error`; `async` bắt lại và cất vào future | luồng của tác vụ |
| (2) | `get()` lấy ngoại lệ ra và ném lại; khối `catch` chạy | luồng `main` |

**Kết quả khi chạy:**

```text
tot = 5
bat duoc o get: chia cho 0
```

TSan sạch. Khác hẳn mục 1: không còn `terminate`. Mình cũng thử một tác vụ ném ngoại lệ mà chỉ `wait()` rồi bỏ future, không `get()`: chương trình thoát bình thường, ngoại lệ bị nuốt im lặng. Vậy đừng quên `get()` nếu bạn muốn biết tác vụ có lỗi.

### 4. `std::launch`: `async`, `deferred` và mặc định

`std::launch::async` yêu cầu chạy trên luồng riêng. `std::launch::deferred` nghĩa là **hoãn**: không có luồng nào cả, tác vụ chỉ chạy khi ai đó gọi `get()` hoặc `wait()`, và chạy ngay trên luồng gọi. Gọi `std::async(hàm)` không nêu policy thì chuẩn cho phép cả hai và **cài đặt tự chọn**; chuẩn không nói trước nó chọn gì.

```cpp
#include <chrono>
#include <future>
#include <iostream>

int viec() {
    std::cout << "  (viec dang chay)\n";
    return 5;
}

int main() {
    std::future<int> d = std::async(std::launch::deferred, viec);      // (1)
    bool hoan = d.wait_for(std::chrono::seconds(0)) == std::future_status::deferred;
    std::cout << "deferred, wait_for tra deferred? " << hoan << "\n";   // (2)
    std::cout << "truoc get\n";
    int kq = d.get();                                                  // (3) lúc này viec mới chạy
    std::cout << "get = " << kq << "\n";

    std::future<int> m = std::async([] { return 7; });                 // (4) không nói policy
    bool hoan2 = m.wait_for(std::chrono::seconds(0)) == std::future_status::deferred;
    std::cout << "mac dinh, wait_for tra deferred? " << hoan2 << "\n"; // (5)
    std::cout << "m = " << m.get() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Tác vụ |
|---|---|---|
| (1) | Chỉ ghi nhớ việc cần làm, chưa chạy | chưa chạy |
| (2) | `wait_for` không chờ gì và trả `deferred` | chưa chạy |
| (3) | `get()` chạy `viec` ngay tại đây rồi trả 5; dòng `(viec dang chay)` nằm giữa `truoc get` và `get = 5` | chạy trên luồng `main` |
| (4)(5) | Cài đặt chọn; chương trình hỏi `wait_for` để biết nó chọn gì | tùy cài đặt |

**Kết quả khi chạy** (ba lần liền như nhau, TSan sạch):

```text
deferred, wait_for tra deferred? 1
truoc get
  (viec dang chay)
get = 5
mac dinh, wait_for tra deferred? 0
m = 7
```

Dòng áp chót nói riêng cho g++ 11 trên máy mình: ở chế độ mặc định nó **không** chọn `deferred`. Đó là cách cài đặt này làm, chuẩn không hứa, và bản g++ khác có thể khác. Muốn chắc có luồng riêng, hãy viết `std::launch::async`. Lỗi hay gặp: tác vụ `deferred` mà không bao giờ `get()`/`wait()` thì **không bao giờ chạy**.

### 5. Cái bẫy: future tạm bị hủy thì phải chờ

Chuẩn nói: hàm hủy của future lấy từ `std::async`, nếu tác vụ chưa xong, sẽ **chờ** tác vụ xong. Bỏ kết quả của `async` đi, tức gọi mà không giữ future, thì future tạm bị hủy **ngay tại dòng đó**, nên dòng gọi chặn tới khi tác vụ xong. Hai tác vụ liền nhau thành tuần tự.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <future>
#include <iostream>
#include <thread>

void viec() { std::this_thread::sleep_for(std::chrono::milliseconds(300)); }

long long mili(std::chrono::steady_clock::time_point bat) {
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();
}

int main() {
    auto bat = std::chrono::steady_clock::now();
    {
        std::future<void> a = std::async(std::launch::async, viec);   // (1) giữ future
        std::future<void> b = std::async(std::launch::async, viec);
    }                                                                  // (2) hủy a, b: chờ cả hai
    std::cout << "giu future:  " << mili(bat) << " ms\n";

    bat = std::chrono::steady_clock::now();
    std::async(std::launch::async, viec);                              // (3) future tạm bị hủy ngay
    std::async(std::launch::async, viec);                              // (4) chỉ bắt đầu khi (3) xong
    std::cout << "bo future:   " << mili(bat) << " ms\n";
    return 0;
}
```

`future<void>` là phiếu hẹn cho tác vụ không trả gì. Mình chạy bốn lần: lần nào cũng 300 đến 303 ms và 600 đến 603 ms; một lần chạy thật:

```text
giu future:  300 ms
bo future:   600 ms
```

Dòng (1): hai tác vụ chạy song song nên cả khối mất khoảng 300 ms. Dòng (3), (4): mỗi dòng chờ 300 ms, tổng khoảng 600 ms. Con số đổi theo máy và độ bận lúc chạy; chỉ cái mẫu "gấp đôi" là ổn định, vì việc chính là `sleep_for`. Trình biên dịch còn cảnh báo ở hai dòng này: `ignoring return value of ... declared with attribute 'nodiscard'` (bỏ qua giá trị trả về của hàm đánh dấu "đừng bỏ"), nên chương trình này không nằm trong khối được kiểm tự động.

Mình thử thêm: hủy future lấy từ `std::promise` (mục 6) khi tác vụ còn ngủ 300 ms thì hàm hủy trả về ngay (0 ms); chờ trong hàm hủy là đặc điểm của future do `async` trả về.

### 6. `std::promise`: tự tay đặt giá trị

`async` tự chạy việc và tự đặt kết quả. Khi bạn đã có luồng riêng (hoặc kết quả đến từ nơi khác), dùng `std::promise<T>`: nó là **đầu ghi**, còn `get_future()` đưa ra **đầu đọc** (một `std::future<T>`). Luồng ghi gọi `set_value(giá trị)` hoặc `set_exception(...)`; luồng đọc gọi `get()` và chờ tới lúc đó.

```cpp
#include <future>
#include <iostream>
#include <stdexcept>
#include <thread>

int main() {
    std::promise<int> loiHua;                           // (1) đầu ghi
    std::future<int> ketQua = loiHua.get_future();      // (2) đầu đọc
    std::thread t([&loiHua] { loiHua.set_value(42); }); // (3) luồng đặt giá trị
    std::cout << "nhan " << ketQua.get() << "\n";       // (4) main chờ đến khi có
    t.join();

    std::promise<int> hong;                             // (5)
    std::future<int> fh = hong.get_future();
    std::thread t2([&hong] {
        try { throw std::runtime_error("khong tinh duoc"); }
        catch (...) { hong.set_exception(std::current_exception()); }   // (6)
    });
    try { fh.get(); }
    catch (const std::exception& e) { std::cout << "loi: " << e.what() << "\n"; }
    t2.join();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (1)(2) | Tạo cặp ghi/đọc | chưa có giá trị |
| (3)(4) | Luồng `set_value(42)`; `get()` ở `main` trả 42 | có giá trị |
| (6) | `catch (...)` (ba dấu chấm thật) bắt ngoại lệ **bất kỳ kiểu nào**; `std::current_exception()` gói ngoại lệ đang bắt, `set_exception` đặt nó vào promise | có ngoại lệ |

**Kết quả khi chạy** (TSan sạch):

```text
nhan 42
loi: khong tinh duoc
```

**Promise bị hủy mà chưa đặt gì.** Đây là món "chưa làm xong mà khay đã dọn": người chờ không thể chờ mãi, nên future nhận một lỗi.

```cpp
#include <future>
#include <iostream>

int main() {
    std::future<int> f;
    {
        std::promise<int> p;                           // (1)
        f = p.get_future();
    }                                                  // (2) p bị hủy mà chưa set
    try {
        f.get();
    } catch (const std::future_error& e) {
        std::cout << "loi: " << e.what() << "\n";
        std::cout << "la broken_promise? " << (e.code() == std::future_errc::broken_promise) << "\n";
    }
    return 0;
}
```

**Kết quả khi chạy** (chạy thật, TSan sạch):

```text
loi: std::future_error: Broken promise
la broken_promise? 1
```

Hàm hủy của `p` (dòng (2)) đặt lỗi `broken_promise` vào future, nên `get()` ném `std::future_error` thay vì treo mãi. Nghĩa là luồng ghi mà quên `set_value` (do `return` sớm, ngoại lệ...) thì luồng đọc nhận lỗi rõ ràng.

### 7. `packaged_task` và `shared_future` (chỉ nhắc)

`std::packaged_task<int(int, int)>` bọc một hàm; hàm đó **không** chạy lúc tạo, mà chạy khi bạn gọi nó (ở đây trao cho một luồng). Kết quả hoặc ngoại lệ tự vào future. Kiểu `int(int, int)` đọc như `std::function<bool(int)>` ở [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md): "nhận hai `int`, trả `int`".

```cpp
#include <future>
#include <iostream>
#include <thread>

int main() {
    std::packaged_task<int(int, int)> goi([](int a, int b) { return a + b; });   // (1)
    std::future<int> kq = goi.get_future();                                      // (2)
    std::thread t(std::move(goi), 3, 4);                                         // (3) chuyển gói cho luồng
    std::cout << "3 + 4 = " << kq.get() << "\n";
    t.join();
    return 0;
}
```

Mình chạy: `3 + 4 = 7`, TSan sạch. `packaged_task` không sao chép được nên phải `std::move` (Bài 12), như `unique_ptr` ở Bài 24. Nó hay dùng khi cài hàng đợi công việc (Bài 30). `std::shared_future<T>`: future sao chép được, nhiều luồng cùng `get()`; chỉ cần biết tên. Còn `std::future` thì không sao chép được (mình thử `std::future<int> b = a;`: `use of deleted function`).

!!! info "Bạn biết Go?"
    Go không có `future` trong thư viện chuẩn. Cách quen thuộc: một **channel** có đệm 1 để nhận kết quả (`ch := make(chan int, 1)`, goroutine làm `ch <- f()`, nơi cần thì `v := <-ch`). Phép nhận `<-ch` tương ứng `future.get()`: chờ tới khi có.

    Khác chỗ (mình đã chạy với Go 1.27.1):

    - Nhận lần hai từ channel còn đang mở **chờ mãi**; chương trình mẫu chỉ có `main` nên Go báo `fatal error: all goroutines are asleep - deadlock!` (binary thoát mã 2). `future.get()` lần hai là lỗi của người gọi (mục 2).
    - Channel đã `close` thì nhận ra giá trị 0 và `ok == false`; future không có khái niệm tương tự.
    - Lỗi trong goroutine không tự đi theo channel (ném `panic` làm cả chương trình chết, như Bài 24); bạn phải gửi `error` qua channel, hoặc dùng `errgroup` của module `golang.org/x/sync` (không thuộc thư viện chuẩn, mình không chạy ở bài này). `future` mang ngoại lệ sẵn.
    - `sync.WaitGroup` chỉ chờ xong, không mang kết quả: giống `join` hơn `get`.
    - Goroutine không phải thread (do runtime Go lập lịch), còn `std::async` với `launch::async` thường dùng luồng hệ điều hành.

## 💻 Ví dụ code

### Chia việc cộng một dãy lớn cho 4 `async`

Dãy 1, 2, ..., 1000000; mỗi `async` cộng một phần 250000 số; `main` gộp bằng `get()`. Tổng đúng là 500000500000, nên đầu ra ổn định.

```cpp
#include <functional>
#include <future>
#include <iostream>
#include <numeric>
#include <vector>

long long congDoan(const std::vector<int>& v, int dau, int cuoi) {   // cộng v[dau], ..., v[cuoi - 1]
    return std::accumulate(v.begin() + dau, v.begin() + cuoi, 0LL);  // 0LL: tổng kiểu long long
}

int main() {
    const int CO = 250000;                               // mỗi phần 250000 số, 4 phần = 1000000
    std::vector<int> so(4 * CO);
    for (int i = 0; i < 4 * CO; ++i) so[i] = i + 1;      // 1, 2, ..., 1000000

    std::vector<std::future<long long>> cacPhan;         // (1) bốn "phiếu hẹn" kiểu long long
    for (int k = 0; k < 4; ++k) {
        cacPhan.push_back(std::async(std::launch::async, congDoan, std::ref(so), k * CO, (k + 1) * CO));   // (2)
    }
    long long tong = 0;
    for (std::future<long long>& f : cacPhan) tong += f.get();   // (3) chờ từng phần rồi cộng
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

Chữ `LL` sau số là hậu tố "kiểu `long long`": tổng 500000500000 vượt quá `int`, nên phải cộng bằng `long long`. `std::ref(so)` ([Bài 24](24-thread-co-ban.md)) truyền chính `so` thay vì sao chép; `std::async(...)` trả một future tạm, `push_back` chuyển nó vào vector (future không sao chép được, nhưng chuyển được).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (1) | Vector chứa bốn phiếu hẹn | rỗng |
| (2) | Mỗi vòng giao một đoạn cho một luồng, `k * CO` đến `(k + 1) * CO` | 4 luồng chạy, mỗi cái cộng 250000 số |
| (3) | `get()` lần lượt chờ từng phần và cộng vào `tong` | `tong` tăng dần tới 500000500000 |

Các luồng chỉ **đọc** `so` và mỗi luồng trả kết quả riêng qua future, nên không cần mutex.

**Kết quả khi chạy** (ổn định; TSan sạch ở `-O1` và `-O2`):

```text
tong = 500000500000
```

**Thử thay đổi: bỏ `std::ref(so)`, viết `so`.** Mình đã chạy: vẫn đúng 500000500000, nhưng mỗi `async` sao chép cả vector 4 MB (đối số bị sao chép mặc định, Bài 24) mà không cần.

**Có nhanh hơn không?** Mình đo riêng cùng dãy này (chương trình khác, không đưa vào bài): không tối ưu thì 4 phần nhanh hơn cộng một luồng một chút (khoảng 6 đến 7 ms so với 10 ms), còn `-O2` thì ngang nhau (cả hai nửa mili giây): việc quá nhỏ so với chi phí tạo luồng. Số liệu đổi theo máy và `-O`; Bài 30 đo kỹ.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::async` khác tự tạo `std::thread` thế nào?"
    `std::thread` chỉ chạy một hàm; không trả kết quả, và ngoại lệ thoát ra khỏi hàm gọi `std::terminate`. `std::async` trả `std::future<T>`: `get()` chờ và trả kết quả, và nếu tác vụ ném ngoại lệ thì `get()` ném lại ở luồng gọi. Bù lại, `async` ít kiểm soát hơn: policy mặc định do cài đặt chọn, và future của `async` chặn trong hàm hủy. Dùng `thread` khi cần điều khiển luồng (RAII bọc luồng, luồng sống lâu); dùng `async` khi cần "chạy việc này, cho tôi kết quả".

??? question "`future` khác `promise` thế nào?"
    Hai đầu của cùng một kênh một lần. `promise` là đầu **ghi**: `set_value` hoặc `set_exception`, đặt đúng một lần. `future` là đầu **đọc**: `get()` chờ rồi lấy. `async` và `packaged_task` tự tạo cặp này; `promise` dùng khi bạn tự điều khiển luồng ghi. Promise bị hủy mà chưa đặt gì thì `get()` ném `future_error` (`broken_promise`).

??? question "`get()` gọi hai lần thì sao?"
    Lần đầu chờ và lấy kết quả (hoặc ném lại ngoại lệ); sau đó `valid()` là `false`. Chuẩn đòi `valid()` đúng trước `get()`, nên lần hai là lỗi của người gọi: trên g++ 11 mình thấy `std::future_error: No associated state`, nhưng đừng dựa vào đó. Muốn đọc nhiều lần hoặc từ nhiều luồng thì lấy kết quả ra biến một lần, hoặc `shared_future`.

??? question "Launch policy là gì?"
    `launch::async`: chạy trên luồng riêng (như thể một luồng mới). `launch::deferred`: hoãn, chạy trên luồng gọi `get()`/`wait()` (không `get` thì không chạy; `wait_for` trả `deferred`). Không nêu policy: chuẩn cho phép cả hai, cài đặt chọn. Cần song song thật thì nêu `launch::async`. Nhớ bẫy: future của `async` chặn trong hàm hủy, nên bỏ future đi làm hai tác vụ liền nhau thành tuần tự.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gọi `std::async` mà không giữ future"
    Future tạm bị hủy ngay và chờ tác vụ xong (mình đo: hai tác vụ 300 ms thành khoảng 600 ms). Gán vào biến và `get()` khi cần. g++ 11 còn cảnh báo `nodiscard` ở dòng đó.

!!! warning "Lỗi 2: Gọi `get()` hai lần"
    `get()` lấy kết quả **ra** khỏi future; lần hai là lỗi. Lưu vào biến ngay lần đầu.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="29" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Đọc đoạn sau. `a` và `ok` là gì?

```text
std::future<int> f = std::async(std::launch::async, [] { return 6; });
int a = f.get();
bool ok = f.valid();
```

- `a` là 6, `ok` là `false`, vì `get()` đã lấy kết quả ra khỏi future
- `a` là 6, `ok` là `true`, vì future vẫn giữ kết quả để lấy lại sau
- `a` là 6, `ok` là `true`, vì `valid()` chỉ cho biết tác vụ đã chạy xong
- `a` là 0, `ok` là `false`, vì kết quả chỉ có sau khi gọi `wait()`

<p class="giai-thich" markdown>`get()` chờ tác vụ rồi **lấy kết quả ra**, nên `a` là 6 và future không còn gắn với kết quả nào: `valid()` trả `false`. Nghĩ future giữ kết quả cho lần lấy sau là nhầm với `shared_future`, còn `future` thường chỉ cho lấy một lần. `valid()` cũng không nói gì về việc tác vụ xong hay chưa. Và `get()` tự chờ, không cần `wait()` trước.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau. `tacVuMot` và `tacVuHai` mỗi cái ngủ một giây. Hàm `chay()` mất khoảng bao lâu?

```text
void chay() {
    std::async(std::launch::async, tacVuMot);
    std::async(std::launch::async, tacVuHai);
}
```

- Gần 0 giây, vì `async` chạy nền và `chay()` trả về ngay
- Khoảng 1 giây, vì hai tác vụ chạy song song trên hai luồng
- Khoảng 2 giây, vì hàm hủy future tạm chờ tác vụ xong
- Gần 0 giây, vì future không được giữ nên tác vụ bị bỏ dở

<p class="giai-thich" markdown>Future do `async` trả về mà bị hủy khi tác vụ chưa xong thì hàm hủy **chờ** tác vụ xong. Ở đây mỗi future là một giá trị tạm, bị hủy ngay cuối dòng, nên dòng thứ hai chỉ bắt đầu sau khi dòng thứ nhất xong: tổng cỡ 2 giây. Nghĩ hai tác vụ chạy song song là quên mất việc chờ này, và "trả về ngay" cũng vậy. Còn tác vụ không hề bị bỏ dở khi future bị hủy; nó được chờ cho xong.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Tác vụ chạy bằng `std::async(std::launch::async, f)` ném một ngoại lệ. Ngoại lệ xuất hiện ở đâu?

- Ngay ở dòng gọi `std::async`, vì lúc đó tác vụ bắt đầu chạy
- Trong hàm hủy của future, nơi chương trình gọi `std::terminate`
- Không đâu cả: chương trình gọi `std::terminate` như với `std::thread`
- Ở lời gọi `get()`, được ném lại cho luồng đang gọi nó

<p class="giai-thich" markdown>`async` bắt ngoại lệ trong tác vụ và cất vào future; `get()` ném lại nó ở luồng gọi `get()`, nên ở đó bạn `catch` được. Dòng gọi `async` trả về ngay nên chưa thấy gì. Hàm hủy của future không ném ngoại lệ ra và cũng không gọi `terminate`. `terminate` là chuyện của `std::thread` thuần (Bài 24), nơi ngoại lệ thoát khỏi hàm của luồng không có chỗ để cất.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. Điều gì xảy ra ở dòng cuối?

```text
std::promise<int> p;
std::future<int> f = p.get_future();
// p bị hủy ở cuối khối, chưa gọi set_value
int x = f.get();
```

- `get()` trả 0, giá trị mặc định của `int`
- `get()` ném `std::future_error` (broken promise)
- `get()` chờ mãi vì không còn ai đặt giá trị
- Chương trình gọi `std::terminate` ngay khi `p` bị hủy

<p class="giai-thich" markdown>Hàm hủy của promise, khi chưa có giá trị, đặt lỗi `broken_promise` vào future, nên `get()` ném `std::future_error`; mình chạy và thấy `Broken promise`. Chờ mãi là hành xử của channel Go khi không ai gửi, còn ở C++ người chờ được báo lỗi. Trả 0 sẽ che mất lỗi nên chuẩn không làm vậy. Và hủy promise không gọi `terminate`; chỉ `std::thread` còn joinable mới như thế.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Bạn tự tạo một luồng `std::thread` và muốn luồng đó báo một kết quả về cho luồng chính ở lúc nó tự chọn. Dùng gì?

- `std::async`, vì nó lấy kết quả từ bất kỳ luồng nào đang chạy
- `std::future` một mình, vì nó có `set_value` cho luồng ghi
- `std::promise`, vì luồng đó tự gọi `set_value` lúc nào muốn
- `std::shared_future`, vì nó cho nhiều luồng cùng đặt giá trị

<p class="giai-thich" markdown>`promise` là đầu ghi: luồng của bạn giữ nó và gọi `set_value` (hoặc `set_exception`) khi sẵn sàng, còn luồng chính giữ future và `get()`. `async` tự tạo luồng và tự đặt kết quả, không nhận luồng có sẵn. `future` chỉ có phía đọc: không có `set_value`. `shared_future` cũng chỉ là phía đọc, cho nhiều luồng cùng đọc một kết quả.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Gọi `std::async(f)` mà không nêu policy. Chuẩn C++ nói gì?

- Cài đặt được chọn chạy ngay trên luồng riêng hoặc hoãn tới `get()` hay `wait()`
- Luôn chạy trên luồng mới, giống hệt khi nêu `std::launch::async`
- Luôn hoãn tới `get()` hay `wait()`, giống hệt `std::launch::deferred`
- Hệ điều hành chọn tùy lúc nào luồng chính rảnh, chuẩn không nói gì

<p class="giai-thich" markdown>Không nêu policy tương đương `async | deferred`: chuẩn cho phép cả hai và để cài đặt chọn, nên cùng đoạn code có thể chạy khác nhau giữa các trình biên dịch. Nói "luôn luồng mới" hay "luôn hoãn" đều khẳng định hơn chuẩn (g++ 11 trên máy mình thì không hoãn, nhưng đó chỉ là cách cài đặt này). Còn việc chọn do thư viện chuẩn quyết định, không phải do thời điểm luồng chính rảnh.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau. Chương trình in ra gì?

```text
auto f = std::async(std::launch::deferred, [] { std::cout << "A"; return 1; });
std::cout << "B";
f.get();
std::cout << "C";
```

- `ABC`, vì `async` bắt đầu tác vụ ngay lúc được gọi
- `BCA`, vì tác vụ chạy nền và thường xong sau cùng
- `BC`, vì tác vụ hoãn thì không bao giờ chạy
- `BAC`, vì tác vụ hoãn chạy lúc `get()` được gọi

<p class="giai-thich" markdown>Với `deferred` không có luồng nào: tác vụ chạy ngay tại `get()` trên luồng gọi, nên `A` in giữa `B` và `C`, ra `BAC`. `ABC` đúng với một tác vụ chạy ngay, không phải `deferred`. `BCA` cần một luồng riêng, mà ở đây không có. Còn `BC` chỉ đúng nếu không ai gọi `get()` hay `wait()`; vì đoạn này có `get()` nên tác vụ vẫn chạy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::thread` không trả kết quả (phải dùng biến chung và `join` trước khi đọc) và ngoại lệ thoát khỏi hàm luồng gọi `std::terminate` (mình chạy: mã 134). `std::async(std::launch::async, f, đối số...)` (`<future>`) trả `std::future<T>`; `get()` chờ và lấy kết quả **một** lần.
2. Sau `get()` thì `valid()` là `false`; `get()` lần hai là lỗi của người gọi (g++ 11 của mình ném `future_error: No associated state`). `wait()` chờ không lấy; `wait_for` trả `ready`/`timeout`/`deferred`.
3. Ngoại lệ ném trong tác vụ được cất vào future và `get()` ném lại ở luồng gọi; không `get()` thì ngoại lệ bị nuốt.
4. `launch::async` (luồng riêng), `deferred` (chạy tại `get()`/`wait()`), mặc định (chuẩn cho cài đặt chọn; g++ 11 của mình không hoãn, đừng dựa vào). Bẫy: future của `async` bị hủy thì chờ tác vụ xong, nên bỏ future thì hai tác vụ 300 ms thành khoảng 600 ms (số đo máy mình).
5. `std::promise` + `future`: một luồng `set_value`/`set_exception`, luồng kia `get()`; promise hủy chưa set thì `broken_promise`. `packaged_task` bọc hàm, `shared_future` cho nhiều người đọc (chỉ nhắc). Go không có future chuẩn: channel có đệm 1 thay thế, nhận lần hai từ channel mở thì chờ mãi.
