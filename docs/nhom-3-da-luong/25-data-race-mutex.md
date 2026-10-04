# Bài 25 — Data race và std::mutex: nhiều luồng cùng sửa một biến

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng **data race** là gì theo chuẩn C++ (hai luồng cùng truy cập một ô nhớ, ít nhất một bên ghi, không đồng bộ) và vì sao nó là **hành vi không xác định**, chứ không chỉ là "kết quả sai"; thấy tận mắt `++dem` từ nhiều luồng ra kết quả khác nhau mỗi lần và ThreadSanitizer báo lỗi.
    - Bảo vệ dữ liệu chung bằng `std::mutex`, và biết vì sao nên dùng `std::lock_guard` (RAII) thay vì gọi `lock()`/`unlock()` bằng tay; biết khi nào cần `std::unique_lock`.
    - Giữ vùng khóa nhỏ nhất có thể, không giữ khóa lúc làm việc chậm, và đóng gói dữ liệu cùng mutex của nó trong một lớp an toàn luồng.
    - Tránh bẫy trả về tham chiếu tới dữ liệu đang được bảo vệ; phân biệt data race với race condition; nhận ra `thread_local` và `std::shared_mutex` khi gặp tên.

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, lambda làm hàm luồng, `vector<thread>`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, hàm hủy, `throw`/`catch`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, sanitizer), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (tham chiếu, hàm thành viên), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda `[&b]`, con trỏ hàm), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến toàn cục, `class` ≈ `struct`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`auto`), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`std::vector<int>`: ngoặc `<...>` cho biết kiểu).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 24](24-thread-co-ban.md): mỗi đầu bếp là một luồng, cả bếp dùng chung kho và bảng treo tường. Bài trước ta cố tình cho mỗi đầu bếp một **phần việc riêng**, không ai đụng món của ai. Giờ thêm một **thớt chung**: nhiều đầu bếp cùng muốn thái hành lên một món đang nằm trên thớt đó.

Nếu hai người thái cùng lúc, họ đụng dao, món bị thái dở, mỗi người tưởng mình đã làm xong phần của mình. Cách xử lý của bếp là một **thẻ vào thớt** duy nhất, treo ở cửa. Ai lấy được thẻ thì được thái; xong thì phải treo thẻ lại cho người sau. Chiếc thẻ đó chính là `std::mutex`, và đoạn việc làm khi đang cầm thẻ gọi là **vùng găng** (critical section).

!!! info "Chỗ nào ví von thẻ vào thớt không còn đúng?"
    Thẻ chỉ có tác dụng khi **mọi** đầu bếp đều chịu lấy thẻ trước khi thái; mutex cũng vậy, nó không ngăn được luồng nào cố tình (hay lỡ quên) đụng vào dữ liệu mà không xin khóa. Ngoài ra đầu bếp thật biết tự kiểm "mình có đang cầm thẻ không", còn chương trình thì quên trả thẻ là treo cả bếp (mục 3).

## 📖 Giải thích

### 1. Data race: khi hai luồng cùng đụng một ô nhớ

Chuẩn C++ định nghĩa: hai thao tác **xung đột** nếu cùng truy cập một ô nhớ và ít nhất một bên là **ghi**. Nếu hai thao tác xung đột đó đến từ hai luồng khác nhau mà **không có thứ tự nào được chuẩn bảo đảm** giữa chúng, ta có một **data race** (tranh chấp dữ liệu). Thứ tự được bảo đảm thì đến từ các công cụ **đồng bộ** như `mutex`, `join`, hay `std::atomic` (Bài 28); đồng bộ nghĩa là ép hai luồng xếp hàng theo một thứ tự rõ ràng.

Điểm quan trọng nhất: chuẩn nói chương trình có data race là **hành vi không xác định** ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Nghĩa là không chỉ "con số có thể sai": chuẩn không hứa gì về **cả chương trình**. Hai luồng cùng **đọc** thì không sao, vì không ai ghi.

Ta xem ví dụ kinh điển: bốn luồng cùng tăng một biến toàn cục `dem`, mỗi luồng tăng 100000 lần. Lệnh `++dem` trông như một bước, nhưng máy làm ba bước: **đọc** `dem` vào thanh ghi (chỗ chứa số tạm trong CPU), **cộng** 1, **ghi** lại. Ba bước đó gọi chung là **đọc-sửa-ghi**, và nó **không nguyên tử** (luồng khác có thể chen vào giữa).

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>
#include <vector>

int dem = 0;                               // biến toàn cục: mọi luồng cùng thấy

void tang() {
    for (int i = 0; i < 100000; ++i) {
        ++dem;                             // (1) mỗi luồng tăng 100000 lần
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);    // (2) bốn luồng
    for (std::thread& t : cacLuong) t.join();                   // (3) chờ cả bốn
    std::cout << "mong doi 400000, thuc te " << dem << "\n";    // (4)
    return 0;
}
```

**Chạy từng dòng** (một cách xen kẽ có thể xảy ra, không phải bảo đảm)

| Bước | Luồng A | Luồng B | `dem` lúc này |
|---|---|---|---|
| 1 | đọc `dem`, thấy 5 | | 5 |
| 2 | | đọc `dem`, thấy 5 | 5 |
| 3 | ghi 6 | | 6 |
| 4 | | ghi 6 | 6 |

Hai lần `++dem` mà `dem` chỉ tăng một. Đây chỉ là kiểu hỏng dễ hình dung nhất; vì là hành vi không xác định, chuẩn không giới hạn kết quả thật trong kiểu hỏng này.

**Kết quả khi chạy** (g++ -std=c++17 -Wall -pthread, không tối ưu, năm lần liền trên máy mình):

```text
mong doi 400000, thuc te 119185
mong doi 400000, thuc te 138962
mong doi 400000, thuc te 117855
mong doi 400000, thuc te 126351
mong doi 400000, thuc te 124915
```

Mỗi lần một số khác nhau và đều nhỏ hơn 400000; máy bạn sẽ ra số khác, nên chỉ cái **mẫu** (nhỏ hơn mong đợi, đổi theo lần) mới đáng nhớ. Khối mã này đặt `// bo-qua-kiem-tra` vì nó có data race.

**Thử thay đổi: biên dịch thêm `-O2`.**

- Kết quả: mình chạy 20 lần, **cả 20 lần đều ra đúng 400000**.
- Vì sao: mình xem mã hợp ngữ (assembly, các lệnh máy viết dạng chữ) do `g++ -O2 -S` sinh ra, hàm `tang` chỉ còn một lệnh `addl $100000, dem(%rip)` (cộng thẳng 100000 vào ô nhớ `dem`), nên cửa sổ cho luồng khác chen vào hẹp tới mức chưa thấy lỗi.
- Nhưng vẫn là data race: ThreadSanitizer (ngay dưới) vẫn báo khi biên dịch với `-O2`. Chạy ra đúng **không** chứng minh chương trình đúng.

**ThreadSanitizer (TSan)** là công cụ của [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) chuyên bắt data race. Biên dịch kèm `-g -fsanitize=thread` rồi chạy. Báo cáo thật, mình rút gọn (bỏ các dòng ngăn xếp gọi của thư viện, đường dẫn tệp, số địa chỉ):

```text
WARNING: ThreadSanitizer: data race
  Read of size 4 at 0x... by thread T2:
    #0 tang() dem_chung.cpp:9
  Previous write of size 4 at 0x... by thread T1:
    #0 tang() dem_chung.cpp:9
  Location is global 'dem' of size 4 at 0x...
SUMMARY: ThreadSanitizer: data race dem_chung.cpp:9 in tang()
```

Dòng được chỉ ra là dòng chứa `++dem;` (dòng 9 nếu bạn bỏ dòng chú thích đầu tệp). TSan chỉ ra: một luồng **đọc** `dem`, luồng kia **ghi** cùng ô nhớ trước đó, không có đồng bộ giữa hai việc. Chương trình vẫn chạy tiếp, in kết quả (khác nhau mỗi lần) và thoát với mã 66, mã mà TSan dùng khi đã báo lỗi.

Trên máy mình, TSan phải chạy qua `setarch $(uname -m) -R ./chuongtrinh` (tắt việc hệ điều hành xáo trộn địa chỉ); chạy trần thì nó dừng với `FATAL: ThreadSanitizer: unexpected memory mapping`.

!!! info "Bạn biết Go?"
    Chương trình Go tương đương (4 goroutine, mỗi cái `dem++` 100000 lần, chờ bằng `sync.WaitGroup`) cũng ra số khác nhau mỗi lần, mình đã chạy ba lần: `130174`, `145546`, `219512`. `go run -race` (hoặc `go test -race`) ứng với TSan: in `WARNING: DATA RACE` và chỉ ra hai dòng xung đột. Binary dựng bằng `go build -race` thoát mã 66 như TSan; `go run` tự thoát mã 1 và in thêm `exit status 66`. Công cụ của Go được xây trên cùng công nghệ ThreadSanitizer.

    Data race trong Go cũng nghiêm trọng: ghi đồng thời vào một `map` từ 4 goroutine (Go 1.27.1) chết cả 6 lần với `fatal error: concurrent map writes` (binary thoát mã 2).

### 2. `std::mutex`: cái thẻ vào thớt

Muốn dùng mutex cần `#include <mutex>`. **`std::mutex`** (mutual exclusion, "loại trừ lẫn nhau") là một đối tượng có hai thao tác chính: `lock()` xin khóa, `unlock()` trả khóa. Nếu mutex đang bị luồng khác giữ thì `lock()` **chặn** luồng gọi (bắt đứng chờ) tới khi khóa được trả.

Chuẩn bảo đảm: đoạn code giữa `lock()` và `unlock()` của một luồng **không chạy xen** với đoạn tương ứng của luồng khác trên cùng mutex; và mọi thứ luồng trước ghi trước `unlock()` đều được luồng sau thấy sau `lock()`. Đó chính là "thứ tự được bảo đảm" cần để hết data race. `std::mutex` không sao chép được (chỉ có một chiếc thẻ).

### 3. Vì sao không gọi `lock()`/`unlock()` bằng tay

Cách ngây thơ: gọi `khoa.lock()` đầu vùng găng và `khoa.unlock()` cuối. Vấn đề là hàm có thể thoát **trước** lệnh `unlock()`: `return` sớm, hay `throw` ném ngoại lệ ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)). Khi đó thẻ không bao giờ được trả.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
int dem = 0;

void ghi(int x) {
    khoa.lock();                           // (1) xin khóa bằng tay
    if (x < 0) return;                     // (2) return sớm: quên unlock
    dem += x;
    khoa.unlock();                         // (3) chỉ tới được khi x >= 0
}

int main() {
    ghi(-1);                               // (4) luồng chính bỏ quên khóa
    std::thread t(ghi, 5);                 // (5) luồng phụ xin khóa
    t.join();                              // (6) chờ mãi
    std::cout << "dem = " << dem << "\n";
    return 0;
}
```

Mình biên dịch (sạch cảnh báo) và chạy với `timeout 3` (lệnh giết chương trình sau 3 giây): chương trình **không bao giờ in gì**, và `timeout` thoát với mã **124**, mã nó dùng khi hết giờ. Luồng chính giữ khóa từ (4) mà không trả, luồng `t` đứng chờ ở (5) mãi mãi, và `join` ở (6) chờ `t`.

Mình cũng thử thay `return` bằng `throw x;` (bắt ở `main` bằng `try`/`catch`): vẫn treo, mã 124. Đây không phải deadlock cổ điển (Bài 26), nhưng cùng một hậu quả: treo.

### 4. `std::lock_guard`: RAII cho mutex

[Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) đã nêu `std::lock_guard` làm ví dụ RAII: nó **xin khóa trong hàm tạo, trả khóa trong hàm hủy**. Biến cục bộ bị hủy khi ra khỏi khối, kể cả khi thoát bằng `return`, hoặc bằng ngoại lệ được `catch` ở đâu đó (ngoại lệ không ai bắt thì chương trình gọi `std::terminate`, [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)); nên khóa được trả. Cú pháp: `std::lock_guard<std::mutex> giu(khoa);`. Cặp `<std::mutex>` cho biết kiểu mutex bị giữ, giống `<int>` trong `std::vector<int>` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)).

```cpp
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int dem = 0;
std::mutex khoa;                           // (1) một "thẻ vào thớt" cho biến dem

void tang() {
    for (int i = 0; i < 100000; ++i) {
        std::lock_guard<std::mutex> giu(khoa);   // (2) xin khóa; hàm hủy của giu sẽ nhả
        ++dem;                                   // (3) vùng găng: chỉ một luồng ở đây
    }                                            // (4) hết vòng lặp: giu bị hủy, khóa được nhả
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "mong doi 400000, thuc te " << dem << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Thẻ lúc này |
|---|---|---|
| (2) | `giu` dựng xong: luồng này lấy được thẻ (nếu luồng khác đang giữ, nó đứng chờ ở dòng này) | luồng này cầm |
| (3) | `++dem` chạy mà không luồng nào khác chạy xen trong cùng vùng găng | luồng này cầm |
| (4) | Hết thân vòng `for`, `giu` bị hủy, hàm hủy trả thẻ; vòng sau tạo `giu` mới | treo ở cửa |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
mong doi 400000, thuc te 400000
```

Mình chạy với `-fsanitize=thread`: không có cảnh báo, mã thoát 0. Kết quả giờ ổn định vì `++dem` của các luồng xếp hàng qua mutex, và `join` bảo đảm luồng chính thấy kết quả cuối.

**Thử thay đổi: xóa dòng (2).** Mình đã chạy: vẫn biên dịch được, nhưng kết quả lại nhỏ hơn 400000 và đổi mỗi lần (`106880`, `144583`, `118777`). Mutex `khoa` vẫn còn đó nhưng không ai xin, nên không bảo vệ gì.

!!! info "Bạn biết Go?"
    `sync.Mutex` ↔ `std::mutex`, `mu.Lock()` ↔ `lock()`. Go không có RAII (hàm hủy), nên thói quen là `mu.Lock()` rồi `defer mu.Unlock()`: `defer` chạy khi **hàm** kết thúc, kể cả `return` sớm hay `panic`, tương đương vai trò của `lock_guard`.

    Khác chỗ: `lock_guard` nhả khóa khi ra khỏi **khối** `{ }` chứa nó (như vòng `for` ở trên), còn `defer` nhả khi cả hàm kết thúc. Mình chạy bản Go có `sync.Mutex`: ra đúng 400000, và bản biên dịch với `-race` không báo gì.

### 5. `std::unique_lock`: khi cần nhả và xin lại

`std::unique_lock<std::mutex>` cũng là RAII (xin khóa khi tạo, trả khi hủy), nhưng có thêm `unlock()` và `lock()` để bạn **nhả sớm và xin lại** giữa chừng. Hàm hủy của nó chỉ trả khóa nếu lúc đó nó đang giữ. Đổi lại nó nặng hơn `lock_guard` một chút (phải nhớ trạng thái "đang giữ hay không").

Bài 27 sẽ dùng nó vì `std::condition_variable` bắt buộc phải có `unique_lock`. Ở đây ta dùng trường hợp đơn giản hơn: ba luồng chia nhau một hàng việc chung, lấy một số ra **trong** khóa, tính bình phương **ngoài** khóa, rồi xin lại khóa để cộng kết quả.

```cpp
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

std::mutex khoa;
std::vector<int> viec = {1, 2, 3, 4, 5, 6, 7, 8};    // hàng việc chung
long long tong = 0;                                   // tổng bình phương, chung

void tho() {
    while (true) {
        std::unique_lock<std::mutex> lk(khoa);        // (1) xin khóa, như lock_guard
        if (viec.empty()) return;                     // (2) hết việc: hàm hủy của lk nhả khóa
        int x = viec.back();
        viec.pop_back();
        lk.unlock();                                  // (3) nhả khóa sớm: phần tính sau không đụng dữ liệu chung
        int binhPhuong = x * x;                       // (4) việc "nặng" làm NGOÀI khóa
        lk.lock();                                    // (5) xin lại khóa để ghi kết quả
        tong += binhPhuong;
    }                                                 // (6) cuối vòng: lk bị hủy, nhả khóa
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 3; ++k) cacLuong.emplace_back(tho);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "tong binh phuong 1..8 = " << tong << "\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
tong binh phuong 1..8 = 204
```

Ai lấy số nào là việc của hệ điều hành và đổi theo lần chạy, nhưng tổng 1 + 4 + 9 + ... + 64 = 204 luôn đúng. Với đa số vùng găng ngắn, `lock_guard` là lựa chọn mặc định; chỉ dùng `unique_lock` khi cần `unlock()`/`lock()` hoặc `condition_variable`.

### 6. Vùng găng nhỏ nhất, và đừng giữ khóa lúc làm việc chậm

Mutex làm các luồng xếp hàng. Mỗi giây giữ khóa là một giây các luồng khác đứng chờ, nên vùng găng chỉ nên bọc **đúng phần đụng dữ liệu chung**. Việc chậm (đọc tệp, mạng, `sleep`, tính toán nặng) làm **ngoài** khóa. Ta đo: mỗi luồng cần "làm việc chậm" 50 ms rồi tăng `dem`. Bản đầu giữ khóa suốt cả lúc chậm; bản sau chỉ khóa khi tăng `dem`. Hàm `chay` nhận một con trỏ hàm ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)) và đo thời gian chạy bằng `std::chrono` ([Bài 24](24-thread-co-ban.md)). Chương trình chỉ in `0`/`1` trả lời các câu hỏi so sánh, vì mili giây thật đổi theo máy.

```cpp
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

std::mutex khoa;
int dem = 0;

void giuKhoaKhiCho() {
    std::lock_guard<std::mutex> giu(khoa);                                  // (1) khóa giữ suốt hàm
    std::this_thread::sleep_for(std::chrono::milliseconds(50));             // (2) việc chậm NẰM TRONG vùng găng
    ++dem;
}

void nhaKhoaKhiCho() {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));             // (3) việc chậm làm NGOÀI khóa
    std::lock_guard<std::mutex> giu(khoa);                                  // (4) khóa chỉ bọc đúng một lệnh
    ++dem;
}

long long chay(void (*ham)()) {
    auto bat = std::chrono::steady_clock::now();
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(ham);
    for (std::thread& t : cacLuong) t.join();
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();
}

int main() {
    long long msGiu = chay(giuKhoaKhiCho);
    long long msNha = chay(nhaKhoaKhiCho);
    std::cout << "dem = " << dem << "\n";                                   // luôn 8
    std::cout << "giu khoa khi cho: it nhat 200 ms? " << (msGiu >= 200) << "\n";
    std::cout << "nha khoa khi cho: duoi 200 ms? " << (msNha < 200) << "\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền, TSan sạch):

```text
dem = 8
giu khoa khi cho: it nhat 200 ms? 1
nha khoa khi cho: duoi 200 ms? 1
```

Giải thích: ở bản đầu bốn lần ngủ 50 ms phải nối đuôi nhau (4 x 50 = 200 ms trở lên). Ở bản sau cả bốn ngủ cùng lúc. Khi mình in thẳng số đo (năm lần liền), được `200` và `50` ms trên máy mình; bạn sẽ ra số khác, nhưng cái chênh lệch cỡ bốn lần thì có lý do rõ ràng.

### 7. Hai thứ chỉ cần nhận ra tên: `thread_local` và `std::shared_mutex`

**`thread_local`** đặt trước một khai báo biến cho **mỗi luồng một bản riêng** (không cần khóa, nhưng cũng không dùng để chia sẻ dữ liệu); câu 8 có ví dụ (mình đã chạy thử: mỗi luồng ra `1000`, luồng chính vẫn `0`, TSan sạch). **`std::shared_mutex`** (C++17, `#include <shared_mutex>`) là mutex "nhiều người đọc, một người ghi": nhiều luồng đọc cùng lúc (`std::shared_lock`), luồng ghi giữ riêng (`std::unique_lock`); `-std=c++14` báo `'shared_mutex' in namespace 'std' does not name a type`.

## 💻 Ví dụ code

### Lớp `BoDem` an toàn luồng: khóa đi theo dữ liệu

Cách làm bền hơn một mutex toàn cục đứng riêng là **đóng gói**: đặt dữ liệu và mutex bảo vệ nó vào **cùng một lớp**, giấu cả hai đi, và chỉ cho bên ngoài đụng vào qua các hàm tự khóa. Khi đó người dùng lớp không thể quên khóa, vì không có cách nào đụng vào dữ liệu mà không đi qua hàm.

Ta cần một thứ cú pháp mới. Với `struct` ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) nói `class` dùng như `struct`), mọi thành viên ai cũng truy cập được. Viết `class` rồi chia **`public:`** (ai cũng dùng được) và **`private:`** (chỉ hàm của chính lớp được đụng vào; từ ngoài truy cập là lỗi biên dịch). Ta dùng `private:` để giấu mutex và biến đếm. Dòng `int dem = 0;` trong lớp cho thành viên `dem` giá trị ban đầu 0. Trong thân lớp, hàm thành viên thấy mọi thành viên dù khai báo trước hay sau nó.

```cpp
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class BoDem {
public:
    void tang() {
        std::lock_guard<std::mutex> giu(khoa);   // (1) mọi hàm đụng tới dem đều khóa
        ++dem;
    }
    int doc() {
        std::lock_guard<std::mutex> giu(khoa);   // (2) đọc cũng phải khóa
        return dem;                              // (3) trả BẢN SAO của dem, không trả tham chiếu
    }

private:                                         // (4) từ đây trở xuống: chỉ hàm của BoDem được đụng
    std::mutex khoa;
    int dem = 0;
};

int main() {
    BoDem b;
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&b] {             // (5) bốn luồng dùng chung một BoDem
            for (int i = 0; i < 100000; ++i) b.tang();
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << b.doc() << "\n";    // (6)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu lúc này |
|---|---|---|
| (5) | Bốn luồng cùng gọi `b.tang()`; lambda giữ tham chiếu tới cùng một `b` | `dem` và `khoa` nằm trong `b` |
| (1) | Mỗi `tang()` xin khóa của **chính `b`**, tăng, rồi nhả | một luồng một lúc |
| (6) | Sau `join`, luồng chính gọi `doc()`: xin khóa, đọc, trả một bản sao | `dem = 400000` |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
dem = 400000
```

Hai chi tiết đáng chú ý. Ở (2): đọc `dem` cũng khóa, vì nếu luồng khác đang ghi mà ta đọc không khóa thì vẫn là data race (một bên ghi, một bên đọc, không đồng bộ). Ở (3): hàm trả `int` theo **giá trị**, tức một bản sao tại lúc đang giữ khóa; lý do nằm ở bẫy bên dưới.

**Thử thay đổi: ở `main` thêm dòng `b.dem = 5;`.** Mình đã chạy: lỗi biên dịch `error: 'int BoDem::dem' is private within this context`. Người dùng lớp không thể lách qua khóa.

### Bẫy: trả tham chiếu tới dữ liệu đang được bảo vệ

Giả sử `BoDem` có hàm `int& thamChieu()` khóa rồi trả `dem` bằng **tham chiếu**. Khóa nhả ngay khi hàm trả về, nhưng người gọi **vẫn cầm tham chiếu** và đọc/ghi qua nó ở ngoài khóa. Bảo vệ vỡ mà hàm trông vẫn "đúng". Con trỏ tới dữ liệu bên trong cũng bị tương tự.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>
class BoDemHong {
public:
    int& thamChieu() {
        std::lock_guard<std::mutex> giu(khoa);   // (1) khóa chỉ bọc lúc LẤY tham chiếu
        return dem;                              // (2) khóa nhả ngay khi hàm trả về
    }

private:
    std::mutex khoa;
    int dem = 0;
};
int main() {
    BoDemHong b;
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 2; ++k) {
        cacLuong.emplace_back([&b] {
            for (int i = 0; i < 100000; ++i) ++b.thamChieu();   // (3) ghi ra NGOÀI khóa
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << b.thamChieu() << "\n";
    return 0;
}
```

Mình biên dịch sạch và chạy năm lần: in `199646`, `198657`, `198225`, `198729`, `198857` (mong đợi 200000; máy bạn ra số khác). Với `-fsanitize=thread`, TSan báo `data race` ở dòng (3) (đọc và ghi cùng ô ở hai luồng). Ở (3), `thamChieu()` trả biệt danh của `dem`, nên `++` tăng đúng `dem` chứ không phải một bản sao.

Cách sửa, chọn một:

- giữ khóa suốt lúc **dùng** dữ liệu;
- trả bản sao;
- đưa việc cần làm vào **bên trong** lớp thành một hàm (như `tang()`).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Data race khác race condition thế nào?"
    Data race là khái niệm của chuẩn C++: hai luồng truy cập cùng một ô nhớ, ít nhất một bên ghi, không có đồng bộ giữa hai truy cập; hậu quả là hành vi không xác định. Race condition là lỗi logic: kết quả đúng hay sai phụ thuộc thứ tự các luồng chạy, và nó có thể xảy ra **dù không có data race**. Ví dụ: `if (b.doc() == 0) b.tang();`, mỗi hàm tự khóa nhưng giữa hai lệnh khóa bị nhả, hai luồng cùng thấy 0 rồi cùng tăng. Sửa data race bằng đồng bộ, còn race condition phải sửa bằng thiết kế (giữ khóa quanh cả chuỗi kiểm-rồi-làm).

??? question "Mutex và atomic khác nhau thế nào, khi nào dùng cái nào?"
    Mutex bảo vệ một **đoạn code** nhiều lệnh (có thể đụng nhiều biến, một bất biến phải giữ nguyên); luồng không có khóa phải chờ. `std::atomic` (Bài 28) làm **một** thao tác trên **một** biến thành nguyên tử, thường không cần khóa. Biến đếm đơn giản hợp với atomic; hễ cần giữ nhất quán giữa nhiều biến hay cả một cấu trúc thì dùng mutex. Cả hai đều là cách đồng bộ hợp lệ để tránh data race.

??? question "`lock_guard` khác `unique_lock` thế nào?"
    Cả hai là RAII: xin khóa lúc tạo, trả lúc hủy. `lock_guard` đơn giản và nhẹ, không nhả sớm được. `unique_lock` cho `unlock()` rồi `lock()` lại giữa chừng, có kiểu tạo không khóa ngay (không đi sâu ở đây), và là thứ `condition_variable` đòi (Bài 27); đổi lại nặng hơn một chút. Mặc định dùng `lock_guard`.

??? question "Tại sao nên dùng RAII cho mutex thay vì gọi `lock()`/`unlock()` tay?"
    Vì hàm có nhiều lối thoát: `return` sớm, ngoại lệ (kể cả từ chỗ ta không để ý, như cấp phát bộ nhớ). Gọi tay thì chỉ cần một lối thoát bỏ qua `unlock()` là khóa bị giữ mãi và các luồng khác treo, như ví dụ mục 3 mà mình đã chạy ra mã 124. Hàm hủy của biến cục bộ chạy trên mọi lối thoát bình thường và khi ngoại lệ được bắt, nên `lock_guard` trả khóa không phụ thuộc trí nhớ của lập trình viên. Đó cũng là cùng ý với `defer mu.Unlock()` của Go.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gọi `lock()`/`unlock()` bằng tay"
    `return` sớm hay ngoại lệ giữa hai lệnh làm khóa không bao giờ được trả (mình đã chạy: treo, mã 124). Dùng `std::lock_guard`.

!!! warning "Lỗi 2: Quên khóa ở một chỗ"
    Mutex chỉ bảo vệ khi **mọi** chỗ đụng tới dữ liệu đều xin khóa, kể cả chỗ chỉ **đọc**. Một chỗ quên là data race trở lại (mình đã chạy: xóa đúng một dòng `lock_guard` là kết quả sai ngay). Đóng gói dữ liệu cùng mutex trong một lớp để không ai quên được.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="25" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Theo chuẩn C++, điều kiện nào dưới đây tạo ra một data race?

- Hai luồng truy cập cùng một ô nhớ, một bên ghi, không có đồng bộ giữa chúng
- Hai luồng cùng ghi một ô nhớ, dù giữa hai lần ghi có `mutex` xếp thứ tự chúng
- Hai luồng cùng chạy một hàm và in ra kết quả khác nhau giữa các lần chạy
- Hai luồng cùng đọc một ô nhớ trong lúc không có luồng nào khác ghi vào nó

<p class="giai-thich" markdown>Data race cần đủ ba thứ: cùng một ô nhớ, có ít nhất một thao tác ghi, và không có thứ tự đồng bộ nào giữa hai truy cập. Có mutex xếp thứ tự hai lần ghi thì đã đồng bộ nên không còn là data race. Hai luồng chỉ đọc thì không ai ghi, nên cũng không phải. Còn in kết quả khác nhau là biểu hiện có thể có, nhưng nó không phải định nghĩa, và hai luồng không đụng chung ô nhớ nào có thể vẫn in thứ tự đổi theo lần chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau, `dem` là biến toàn cục `int` bắt đầu bằng 0, không có mutex hay atomic. Sau khi cả bốn luồng `join`, điều nào bảo vệ được?

```text
void tang() { for (int i = 0; i < 100000; ++i) ++dem; }
// main: tạo 4 luồng chạy tang, join cả bốn, rồi in dem
```

- `dem` chắc chắn nhỏ hơn 400000, vì các lần tăng bị mất
- `dem` chắc chắn bằng 400000, vì mỗi luồng cộng đúng 100000
- Chuẩn không hứa gì, vì chương trình có data race
- Chuẩn bảo đảm `dem` nằm giữa 100000 và 400000, vì mỗi luồng cộng phần mình

<p class="giai-thich" markdown>Có data race thì chương trình là hành vi không xác định, nên chuẩn không bảo đảm con số nào. Nói "chắc chắn nhỏ hơn" là sai ngay cả trên thực tế: với `-O2` mình chạy 20 lần đều ra đúng 400000. Nói "chắc chắn bằng 400000" thì sai vì không có đồng bộ nào bảo đảm. Còn khoảng 100000 đến 400000 là suy đoán dựa trên cách máy hay hỏng, không phải điều chuẩn cho phép tin.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đoạn sau. `main` gọi `f(-1)`, rồi tạo luồng `t` chạy `f(1)` và `t.join()`. Chuyện gì xảy ra?

```text
std::mutex m;
void f(int x) {
    m.lock();
    if (x < 0) return;
    m.unlock();
}
```

- Chương trình kết thúc bình thường, vì `m` tự nhả khi hàm `f` trả về
- Luồng `t` đứng chờ `m` mãi mãi, vì lần gọi đầu bỏ quên không nhả
- Không biên dịch được, vì có lối thoát không đi qua `m.unlock()`
- Lệnh `m.lock()` trong luồng `t` ném ngoại lệ, vì `m` đang bị khóa

<p class="giai-thich" markdown>`std::mutex` không tự nhả khi hàm kết thúc; việc đó là của `unlock()` hoặc của lớp RAII. Lần `f(-1)` giữ khóa rồi thoát sớm nên không ai trả, và `lock()` ở luồng `t` chặn đến khi khóa được trả, tức là mãi mãi. Trình biên dịch không kiểm tra cặp `lock`/`unlock` nên đây không phải lỗi biên dịch. Còn `lock()` trên mutex bị luồng khác giữ chỉ làm luồng gọi chờ, không ném ngoại lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Bạn muốn một lớp bọc RAII (tự trả khóa khi bị hủy) mà vẫn cho gọi `unlock()` rồi `lock()` lại giữa hàm. Nên dùng lớp nào?

- `std::lock_guard`, vì nó có `unlock()` và `lock()` như `unique_lock`
- `std::lock_guard`, vì hàm hủy của nó tự xin lại khóa sau khi nhả
- Không lớp bọc nào làm được, phải gọi tay trên chính mutex
- `std::unique_lock`, vì có `unlock()` và `lock()` mà vẫn tự nhả khi hủy

<p class="giai-thich" markdown>`unique_lock` cho nhả và xin lại giữa chừng mà vẫn là RAII: hàm hủy chỉ trả khóa nếu lúc đó nó còn giữ. `lock_guard` chỉ xin khóa lúc tạo và trả lúc hủy, không có `unlock()` hay `lock()`, và hàm hủy của nó cũng không xin khóa lại. Bỏ hết lớp bọc để gọi tay là bỏ luôn lợi ích RAII, trong khi đã có `unique_lock` làm đúng việc này.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Hai hàm sau cùng tăng một biến `dem` chung (đã có `std::mutex m`). `docTep()` mất 50 ms và không đụng `dem`. Bốn luồng, mỗi luồng gọi một hàm một lần. Khác biệt về thời gian?

```text
void a() { std::lock_guard<std::mutex> g(m); docTep(); ++dem; }
void b() { docTep(); std::lock_guard<std::mutex> g(m); ++dem; }
```

- Bốn luồng gọi `b` xong sau cỡ 50 ms, còn gọi `a` thì cỡ 200 ms
- Hai bản xong sau cùng thời gian, vì `++dem` vẫn bị khóa ở cả hai
- Bốn luồng gọi `a` xong nhanh hơn, vì xin khóa sớm thì được chạy trước
- Hàm `b` sai, vì `docTep()` chạy ngoài khóa nên gây data race trên `dem`

<p class="giai-thich" markdown>Ở `a` mỗi luồng giữ khóa suốt lúc `docTep()` chạy, nên bốn lần 50 ms phải nối đuôi nhau, cỡ 200 ms. Ở `b` bốn lần `docTep()` chạy cùng lúc rồi mới xếp hàng cho `++dem` rất ngắn, tổng cỡ 50 ms. Đề đã nói `docTep()` không đụng `dem`, nên chạy nó ngoài khóa không gây race. Xin khóa sớm không làm ai chạy nhanh hơn, nó chỉ làm người khác chờ lâu hơn.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. Lớp có `std::mutex khoa` và `int dem` là thành viên `private`. Hai luồng cùng chạy `++b.thamChieu()` nhiều lần. Vì sao vẫn có data race?

```text
int& thamChieu() {
    std::lock_guard<std::mutex> giu(khoa);
    return dem;
}
```

- `lock_guard` không khóa được khi hàm trả về một tham chiếu
- Mutex là thành viên `private` nên luồng khác không xin khóa được
- Hai luồng gọi cùng một hàm thì luôn có data race, bất kể khóa
- Khóa nhả khi hàm trả về, còn `++` chạy sau đó mà không có khóa

<p class="giai-thich" markdown>`lock_guard` vẫn khóa đúng lúc hàm chạy; vấn đề là hàm chỉ **trao** tham chiếu rồi nhả khóa, và phép `++` thực hiện sau, ở ngoài khóa, qua tham chiếu đó. `private` chỉ cấm bên ngoài đụng thẳng vào thành viên, không liên quan tới việc hàm của lớp xin khóa. Gọi cùng một hàm từ nhiều luồng vẫn an toàn nếu hàm giữ khóa suốt lúc dùng dữ liệu, như `tang()` của `BoDem`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Đọc đoạn sau. `b` là `BoDem` ở bài này (`tang()` và `doc()` đều tự khóa), `dem` bắt đầu bằng 0, hai luồng cùng chạy đúng dòng này một lần. Điều nào đúng?

```text
if (b.doc() == 0) { b.tang(); }
```

- Có data race, vì cả hai luồng cùng đọc `dem` cùng lúc
- Không có data race nhưng có race condition, vì `dem` có thể thành 2
- Không có lỗi nào, vì mỗi hàm đã tự khóa nên cả dòng an toàn
- Chắc chắn `dem` thành 1, vì luồng sau thấy `dem` đã khác 0

<p class="giai-thich" markdown>Mỗi lần đọc và mỗi lần tăng đều nằm trong khóa nên không có data race. Nhưng khóa nhả giữa `doc()` và `tang()`, nên hai luồng có thể cùng thấy 0 rồi cùng tăng, ra 2: kết quả phụ thuộc thứ tự chạy, tức là race condition. Hai hàm tự khóa không làm cả chuỗi kiểm-rồi-làm trở thành một khối. Còn "chắc chắn bằng 1" chỉ đúng với một thứ tự chạy cụ thể, không phải mọi thứ tự.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Đọc đoạn sau. Ba luồng, mỗi luồng chạy `for` tăng `dem` 1000 lần rồi in `dem` ngay trong luồng của nó. Mỗi luồng in gì?

```text
thread_local int dem = 0;
```

- Luồng nào in trước thì in 1000, luồng sau in 2000, rồi 3000
- `3000` ở cả ba luồng, vì cuối cùng mọi luồng thấy cùng biến
- `1000` ở cả ba luồng, vì mỗi luồng tăng bản `dem` riêng của nó
- Không xác định, vì ba luồng cùng ghi vào một biến mà không khóa

<p class="giai-thich" markdown>`thread_local` cho mỗi luồng một bản `dem` riêng bắt đầu từ 0, nên mỗi luồng chỉ tăng bản của mình và in 1000. Không có ô nhớ chung nên cũng không có data race và không cần khóa. Các phương án sai cùng nhầm ở chỗ coi `dem` là một biến chung của cả ba luồng, như biến toàn cục thường.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Data race** (chuẩn C++): hai luồng cùng truy cập một ô nhớ, ít nhất một bên ghi, không có đồng bộ giữa chúng; hậu quả là **hành vi không xác định**, không chỉ là kết quả sai. `++dem` là đọc-sửa-ghi không nguyên tử: mình chạy ra số nhỏ hơn mong đợi, khác mỗi lần; TSan chỉ ra dòng xung đột.
2. `std::mutex` (`lock`/`unlock`) cho các luồng xếp hàng qua một vùng găng và tạo thứ tự đồng bộ; gọi `lock`/`unlock` tay nguy hiểm vì `return` sớm hay ngoại lệ làm khóa không được trả (mình chạy: treo, mã 124).
3. Dùng `std::lock_guard` (RAII, nối [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md); Go dùng `defer mu.Unlock()`); `std::unique_lock` khi cần nhả/xin lại giữa chừng hoặc dùng với `condition_variable` (Bài 27). Giữ vùng găng nhỏ nhất, không giữ khóa lúc ngủ/I/O/tính nặng.
4. Khóa đi theo dữ liệu: đóng gói dữ liệu `private` cùng mutex trong một lớp (như `BoDem`), mọi hàm đụng dữ liệu đều khóa và trả **bản sao**; trả tham chiếu hay con trỏ tới dữ liệu được bảo vệ phá vỡ bảo vệ.
5. Race condition là lỗi logic theo thứ tự chạy, còn được dù hết data race (kiểm-rồi-làm giữa hai lần khóa); `thread_local` và `std::shared_mutex` (C++17) chỉ cần nhận ra tên; `-race` của Go ứng với TSan.
