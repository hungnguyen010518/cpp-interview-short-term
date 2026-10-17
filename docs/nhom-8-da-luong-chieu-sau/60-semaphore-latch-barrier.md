# Bài 60 — Semaphore, latch, barrier: đếm người vào, đếm cho đủ, hẹn nhau ở vạch

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được **semaphore** (bộ đếm có chờ) khác **mutex** ở đâu: mutex có chủ (ai khóa thì người đó mở), semaphore không có chủ (luồng nào cũng `release` được) và đếm được nhiều hơn một chỗ; tự viết lớp `Semaphore` bằng `mutex` + `condition_variable` chạy trong C++17.
    - Giới hạn "chỉ 3 luồng vào một khu vực" và **đo** được số luồng đồng thời lớn nhất bằng `atomic` (đỉnh không vượt 3 khi có semaphore, lên 8 khi bỏ nó); biết semaphore dùng được làm tín hiệu mà không bị mất thông báo như `notify` ở Bài 27.
    - Dùng `std::counting_semaphore`, `std::latch` (đếm ngược một lần), `std::barrier` (hẹn nhau ở vạch, lặp nhiều vòng) của C++20 với cờ `-std=c++20`, và chọn đúng trong ba cái.
    - Phân biệt `std::shared_mutex` (đọc nhiều, ghi một, nguy cơ đói ghi) với spinlock tự viết bằng `atomic_flag`, và nói được khi nào KHÔNG nên dùng chúng.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `vector<thread>`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, `unique_lock`, TSan, lớp bọc dữ liệu cùng mutex), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, predicate, notify bị mất), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, `compare_exchange_weak`, `atomic_flag`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda `[&]`, `[x]`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Ở đó chỉ có **một thớt**, nên chỉ có **một thẻ vào thớt** (mutex): ai cầm thẻ thì người đó cất thẻ, không ai cất hộ.

Giờ bếp có **khu bếp lò** với đúng **3 bếp**. Cửa treo **3 tấm thẻ bếp lò**: lấy một thẻ để vào, ra thì treo lại. Hết thẻ thì đứng chờ. Thẻ này **không ghi tên ai**: người trực cửa cũng có thể treo thẻ lại hộ một đầu bếp đã bận việc khác. Đó là **semaphore** (cột cờ hiệu có đếm): bộ đếm "còn mấy thẻ", không nhớ ai đang cầm.

Hai cảnh nữa. **Chuông đếm ngược**: chủ bếp chỉ mở tiệc khi đủ 4 món sơ chế; mỗi món xong thì gạch một vạch, vạch thứ tư làm chuông reo, và chuông chỉ reo **một lần** (`std::latch`). **Vạch hẹn**: ba đầu bếp làm nhiều công đoạn, tới vạch cuối công đoạn thì đứng đợi, đủ cả ba mới cùng sang công đoạn sau, rồi lại hẹn ở vạch tiếp (`std::barrier`).

!!! info "Chỗ nào ví von thẻ bếp lò không còn đúng?"
    Thẻ bếp thật là vật thể: có 3 thẻ nghĩa là 3 bếp cụ thể. Semaphore chỉ là một **số** đếm, nó không nói luồng nào đứng ở "bếp số mấy" và không kiểm tra ai trả. Vì thế semaphore còn có thể bắt đầu từ 0 (không có thẻ nào) và dùng làm tín hiệu "xong rồi", điều mà thẻ bếp vật lý không làm được.

## 📖 Giải thích

### 1. Semaphore là gì, và vì sao mutex hay atomic không đủ

**Semaphore** là một số nguyên không âm cùng hai thao tác:

- `acquire()`: nếu số **> 0** thì giảm 1 và đi tiếp; nếu số là 0 thì **ngủ** tới khi có người tăng.
- `release()`: tăng số lên 1 và đánh thức một người đang chờ.

Muốn "tối đa 3 luồng trong khu vực": đặt số ban đầu là 3, mỗi luồng `acquire` khi vào và `release` khi ra. Mutex chỉ chứa **một** luồng. `atomic` đếm được số luồng nhưng **không chặn** ai: luồng thứ tư vẫn xông vào. Cần thứ vừa **đếm** vừa **chờ**: đó là semaphore, cũng là thứ bạn đã thấy trong Go dưới dạng channel có đệm (hộp Go ở cuối bài).

| | `mutex` | semaphore đếm | semaphore nhị phân (số 0/1) |
|---|---|---|---|
| Cho vào cùng lúc | 1 luồng | N luồng (N tự chọn) | 1 luồng |
| Ai được trả | chính luồng đã khóa | luồng nào cũng được | luồng nào cũng được |
| Dùng làm tín hiệu "xong" | không | được | được |

### 2. Tự viết `Semaphore` bằng mutex + condition_variable (C++17)

C++17 chưa có semaphore trong thư viện chuẩn (C++20 mới có, mục 4). Nhưng ta đã có đủ đồ nghề của Bài 25 và Bài 27: một số đếm `dem_` được bảo vệ bởi mutex, và `condition_variable` để ngủ khi `dem_ == 0`.

Về cú pháp: `: dem_(chua)` sau hàm tạo là **danh sách khởi tạo** (gán thành viên lúc đối tượng được dựng); `explicit` chặn C++ tự biến một số `int` thành `Semaphore` ngầm; `[this]` cho lambda trong hàm thành viên đọc được `dem_`. Chương trình bên dưới cho 8 luồng cùng xin vào khu vực chứa 3 chỗ. Mỗi luồng cập nhật `toiDa` bằng vòng `compare_exchange_weak` của [Bài 28](../nhom-3-da-luong/28-atomic.md) để ghi lại số luồng đồng thời lớn nhất từng thấy.

```cpp
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class Semaphore {
public:
    explicit Semaphore(int chua) : dem_(chua) {}      // (1) bắt đầu với "chua" chỗ trống

    void acquire() {                                  // (2) xin một chỗ; hết chỗ thì ngủ
        std::unique_lock<std::mutex> lk(khoa_);
        cv_.wait(lk, [this] { return dem_ > 0; });
        --dem_;
    }

    void release() {                                  // (3) trả một chỗ, ai trả cũng được
        {
            std::lock_guard<std::mutex> g(khoa_);
            ++dem_;
        }
        cv_.notify_one();
    }

private:
    std::mutex khoa_;
    std::condition_variable cv_;
    int dem_;                                         // số chỗ còn trống, đổi dưới khóa
};

int main() {
    Semaphore cho(3);                                 // khu vực chỉ chứa 3 luồng
    std::atomic<int> dangVao{0};                      // số luồng đang ở trong khu vực
    std::atomic<int> toiDa{0};                        // số đồng thời lớn nhất từng thấy

    std::vector<std::thread> ds;
    for (int i = 0; i < 8; ++i) {
        ds.emplace_back([&] {
            cho.acquire();                            // (4) vào khu vực
            int now = ++dangVao;                      // (5) ++ trả giá trị mới
            int cu = toiDa.load();
            while (cu < now && !toiDa.compare_exchange_weak(cu, now)) {}   // (6) toiDa = max(toiDa, now)
            std::this_thread::sleep_for(std::chrono::milliseconds(30));    // (7) "làm việc" trong khu vực
            --dangVao;
            cho.release();                            // (8) ra khỏi khu vực, trả chỗ
        });
    }
    for (std::thread& t : ds) t.join();

    std::cout << "dong thoi toi da <= 3: " << (toiDa <= 3 ? "dung" : "sai") << "\n";
    std::cout << "con trong khu vuc: " << dangVao << "\n";
    return 0;
}
```

**Chạy từng dòng** (8 luồng chạy xen kẽ; bảng nói vai trò, không phải thứ tự cố định)

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `dem_ = 3`: ba thẻ treo ở cửa |
| (2) | Giống `wait` của Bài 27: chờ tới khi `dem_ > 0`, rồi lấy một thẻ (`--dem_`) dưới khóa |
| (4) | Ba luồng đầu lấy được thẻ; năm luồng còn lại ngủ trong `wait`, không tốn CPU |
| (5)-(6) | `dangVao` là số người trong khu vực lúc này; `toiDa` chỉ tăng, nên ghi lại đỉnh |
| (7) | 30 ms "làm việc" để các luồng chồng lên nhau, đủ thời gian cho cả ba chỗ đầy |
| (3)/(8) | Ra khỏi khu vực, tăng `dem_` và đánh thức một luồng đang chờ: một luồng mới vào |
| in kết quả | `điều_kiện ? a : b` cho `a` nếu điều kiện đúng, cho `b` nếu sai: in chữ `dung` hoặc `sai` |

**Kết quả khi chạy:**

```text
dong thoi toi da <= 3: dung
con trong khu vuc: 0
```

Mình biên dịch sạch cảnh báo, TSan sạch. Mình in `<= 3` chứ không in "đúng bằng 3" vì **chuẩn không hứa** đỉnh chạm 3 (ba luồng có thể không bao giờ trùng nhau). Mình đo riêng (thêm một dòng in `toiDa`): 100 lần chạy cho đủ 100 lần `3`, nhưng đó là chuyện của máy này.

**Thử thay đổi 1: xóa hai dòng `cho.acquire();` và `cho.release();`.** Mình đã chạy 5 lần: cả 5 lần `toiDa = 8`, và dòng kiểm ra `sai`. Không còn ai chặn, cả 8 luồng cùng vào khu vực.

**Thử thay đổi 2: đổi `Semaphore cho(3)` thành `Semaphore cho(1)`.** `toiDa` ra `1` (3 lần chạy): semaphore đếm với N = 1 cư xử như mutex (với khác biệt ở mục 3). Thời gian cả chương trình (đo bằng `time`, đổi theo máy): khoảng 0,093 giây với 3 chỗ (8 luồng chia ba đợt 30 ms) so với khoảng 0,245 giây với 1 chỗ (tám đợt).

### 3. Semaphore không có chủ: dùng làm tín hiệu, không mất thông báo

Mutex hỏi "ai đang cầm khóa". `std::mutex::unlock` phải do **chính luồng đã `lock`** gọi, luồng khác gọi là hành vi không xác định. Semaphore **không hỏi**: luồng chưa từng `acquire` vẫn `release` được. Nhờ vậy ta cho nó bắt đầu từ **0** (không có thẻ nào) và dùng làm tín hiệu "việc đã xong".

Còn một lợi nữa so với `notify` ở [Bài 27](../nhom-3-da-luong/27-condition-variable.md): `notify` gọi khi chưa ai chờ thì **mất**, còn `release` thì **được đếm lại** trong `dem_` (xem dòng (3) ở lớp trên: `++dem_` nằm lại dù không ai chờ). Ví dụ chạy ở mục 4: luồng phụ `release` trước, main tới `acquire` sau 100 ms vẫn không ngủ.

!!! warning "Hay nhầm"
    "Binary semaphore chính là mutex." **Không.** Đếm 0/1 giống nhau, nhưng mutex có chủ (chỉ người khóa mới mở) và dùng để **bảo vệ dữ liệu**. Binary semaphore dùng để **báo tin** hoặc nhường chỗ giữa các luồng khác nhau, nên luồng nào cũng `release` được. Dùng semaphore thay mutex để bảo vệ dữ liệu là mất luôn quy tắc "ai khóa thì người đó mở", nên lỗi mở nhầm không còn ai bắt.

### 4. C++20: `counting_semaphore` và `binary_semaphore`

Từ **C++20**, `#include <semaphore>` cho sẵn `std::counting_semaphore<N>` (N là trần của bộ đếm mà cài đặt **chắc chắn** hỗ trợ; có thể bỏ trống `<>`, khi đó cài đặt tự chọn) và `std::binary_semaphore` (`counting_semaphore<1>`). Các hàm: `acquire()`, `release()` (dạng `release(n)` trả nhiều thẻ), `try_acquire()` (không chờ, trả `true` nếu lấy được), và `try_acquire_for`/`try_acquire_until` (chờ có hạn).

Mình kiểm tra thật trên g++ 11.4: **`g++ -std=c++20` biên dịch `<semaphore>`, `<latch>`, `<barrier>` được**; với `-std=c++17`, `#include` vẫn qua nhưng dùng tên là lỗi, ví dụ `error: 'counting_semaphore' is not a member of 'std'` (tương tự `latch`, `barrier`). CI của bài dùng `-std=c++17`, nên **mọi khối C++20 trong bài** có `// bo-qua-kiem-tra` ở dòng đầu kèm dòng ghi lệnh biên dịch; mình đã chạy từng khối bằng `g++ -std=c++20 -Wall -pthread`, sạch cảnh báo, TSan sạch.

Mình thay lớp `Semaphore` ở mục 2 bằng `std::counting_semaphore<3> cho(3);` (giữ nguyên `cho.acquire()`/`cho.release()`) và chạy: ra cùng kết quả (`<= 3: dung`). Khối dưới thử ba thứ còn lại: `try_acquire`, `release(n)`, và tín hiệu từ luồng khác với số đếm 0.

```cpp
// bo-qua-kiem-tra
// Biên dịch: g++ -std=c++20 -Wall -pthread c5.cpp   (với -std=c++17 báo: 'binary_semaphore' is not a member of 'std')
#include <chrono>
#include <iostream>
#include <semaphore>
#include <thread>

int main() {
    std::counting_semaphore<3> cho(3);                // (1) trần 3, bắt đầu với 3 chỗ
    int lay = 0;
    for (int i = 0; i < 5; ++i) lay += cho.try_acquire();   // (2) không chờ: trả true nếu lấy được
    std::cout << "lay duoc " << lay << " cho tren 5 lan thu\n";
    cho.release(3);                                   // (3) trả cả 3 chỗ một lần

    std::binary_semaphore san(0);                     // (4) nhị phân, bắt đầu 0: "chưa có tin"
    int ketQua = 0;                                   // dữ liệu thường, không atomic
    std::thread tho([&] {
        ketQua = 42;
        san.release();                                // (5) luồng này chưa từng acquire
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(100));   // (6) main tới trễ
    san.acquire();                                    // (7) tin đã được đếm sẵn, không ngủ
    std::cout << "ket qua = " << ketQua << "\n";
    tho.join();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1)-(2) | `<3>` là trần của bộ đếm; số `3` trong ngoặc tròn là giá trị ban đầu. Năm lần `try_acquire`: ba lần lấy được, hai lần thất bại (không ngủ). `lay += true` cộng 1, `lay += false` cộng 0 |
| (3) | Trả ba chỗ một lần, đưa bộ đếm về 3. Trả vượt trần là vi phạm điều kiện (hành vi không xác định); mình thử `release()` thêm khi đã đầy trên g++ 11: không báo gì, bộ đếm lên 4, đừng dựa vào |
| (5)-(7) | Luồng phụ `release` lúc main còn ngủ; `acquire` ở main thấy số 1, đi tiếp ngay và in đúng 42 |

**Kết quả khi chạy** (`g++ -std=c++20`):

```text
lay duoc 3 cho tren 5 lan thu
ket qua = 42
```

Mình cũng chạy cùng kịch bản (luồng phụ `release`, main tới trễ 100 ms rồi `acquire`) với lớp `Semaphore` tự viết ở C++17: ra `ket qua = 42`, TSan sạch. Dữ liệu `ketQua` là biến thường mà không có data race, vì `release` rồi `acquire` đi qua cùng một cơ chế đồng bộ: ghi trước `release` thì thấy được sau `acquire` ([Bài 59](59-memory-model.md) giải thích nền tảng của chuyện này).

## 💻 Ví dụ code

### `std::latch`: đếm ngược một lần, rồi mở

`std::latch` (C++20, `#include <latch>`) khởi tạo với một số `n`. `count_down()` giảm 1 mà **không chờ**; `wait()` chờ tới khi số về 0; `arrive_and_wait()` là giảm rồi chờ. Về 0 là **xong vĩnh viễn**, không đặt lại được. Hai cách dùng kinh điển nằm trong cùng chương trình: **cổng xuất phát** (`latch(1)`, mọi luồng chờ, main mở) và **chờ đủ N luồng xong** (`latch(N)`). Lambda `[&, k]` bắt mọi thứ theo tham chiếu, riêng `k` theo giá trị: mỗi luồng giữ bản chép `k` của mình.

```cpp
// bo-qua-kiem-tra
// Biên dịch: g++ -std=c++20 -Wall -pthread c2.cpp   (với -std=c++17: 'latch' is not a member of 'std')
#include <iostream>
#include <latch>
#include <thread>
#include <vector>

int main() {
    std::latch batDau(1);                    // (1) cổng xuất phát: đếm ngược từ 1
    std::latch xongHet(4);                   // (2) chờ đủ 4 luồng: đếm ngược từ 4
    std::vector<long long> riengMoiLuong(4, 0);

    std::vector<std::thread> ds;
    for (int k = 0; k < 4; ++k) {
        ds.emplace_back([&, k] {
            batDau.wait();                   // (3) mọi luồng đứng chờ cổng mở
            long long s = 0;
            for (int i = k * 250 + 1; i <= (k + 1) * 250; ++i) s += i;   // đoạn 1..1000 của luồng k
            riengMoiLuong[k] = s;
            xongHet.count_down();            // (4) báo "tôi xong", không chờ ai
        });
    }

    batDau.count_down();                     // (5) mở cổng: đếm về 0, cả 4 luồng chạy
    xongHet.wait();                          // (6) main chờ tới khi đếm về 0
    long long tong = 0;
    for (long long s : riengMoiLuong) tong += s;
    std::cout << "tong 1..1000 = " << tong << "\n";
    for (std::thread& t : ds) t.join();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (3) | Luồng nào tới trước thì đứng chờ ở cổng, không tốn CPU |
| (5) | `count_down` đưa `batDau` về 0: mọi luồng đang chờ được thả cùng lúc |
| (4) | Mỗi luồng chỉ giảm `xongHet` một lần rồi đi tiếp, không chờ luồng khác |
| (6) | Main chờ tới khi cả 4 đã `count_down`; mọi ghi vào `riengMoiLuong` trước `count_down` thì main thấy |

**Kết quả khi chạy** (`g++ -std=c++20`): `tong 1..1000 = 500500`. Cả hai lần chạy mình thử đều giống nhau, TSan sạch.

So với `join`: `join` chờ luồng **kết thúc hẳn**; `latch` cho luồng báo "xong phần này" rồi **tiếp tục làm việc khác**. Gọi `count_down` quá số đếm là vi phạm điều kiện tiên quyết (hành vi không xác định): mình thử `latch l(1)` rồi `count_down` hai lần và `wait`, trên máy này nó **treo**; đừng dựa vào điều đó.

### `std::barrier`: hẹn nhau ở vạch, dùng nhiều vòng

`std::barrier` (C++20, `#include <barrier>`) khởi tạo với số luồng tham gia. Mỗi luồng gọi `arrive_and_wait()`: đến vạch và đợi tới khi **đủ số luồng** cùng đến, rồi tất cả đi tiếp; barrier **tự đặt lại** cho vòng sau. Có thể truyền thêm **hàm hoàn tất** (completion function, phải `noexcept`): nó chạy đúng **một lần** mỗi vòng, do một trong các luồng, **trước khi** mọi luồng được thả. Chương trình dưới dùng `std::barrier hen(3, hàm)` mà không viết kiểu trong `<...>`: g++ ở `-std=c++20` tự suy ra từ các đối số, như `scoped_lock` ở [Bài 26](../nhom-3-da-luong/26-deadlock.md).

```cpp
// bo-qua-kiem-tra
// Biên dịch: g++ -std=c++20 -Wall -pthread c3.cpp   (với -std=c++17: 'barrier' is not a member of 'std')
#include <barrier>
#include <iostream>
#include <thread>
#include <vector>

int main() {
    int a[3] = {0, 0, 0};
    int b[3] = {0, 0, 0};
    int soVong = 0;                                    // chỉ hàm hoàn tất đụng tới

    std::barrier hen(3, [&]() noexcept { ++soVong; }); // (1) hẹn 3 luồng; hàm hoàn tất chạy mỗi khi đủ 3

    std::vector<std::thread> ds;
    for (int k = 0; k < 3; ++k) {
        ds.emplace_back([&, k] {
            a[k] = k + 1;                              // (2) vòng 1: ghi phần của mình
            hen.arrive_and_wait();                     // (3) tới vạch, chờ đủ cả 3
            b[k] = a[(k + 1) % 3];                     // (4) vòng 2: đọc phần của người bên cạnh
            hen.arrive_and_wait();                     // (5) cùng barrier, dùng lại lần hai
        });
    }
    for (std::thread& t : ds) t.join();

    std::cout << "b = " << b[0] << " " << b[1] << " " << b[2] << "\n";
    std::cout << "so vong = " << soVong << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (2) | Mỗi luồng ghi ô `a[k]` của mình; chưa luồng nào đọc ô của người khác |
| (3) | Vạch thứ nhất: không luồng nào qua tới khi cả 3 đã ghi xong; hàm hoàn tất chạy, `soVong = 1` |
| (4) | Luồng `k` đọc `a[(k+1)%3]`: chắc chắn đã có giá trị, nhờ vạch ở (3) |
| (5) | Vạch thứ hai trên **cùng** `hen`; hàm hoàn tất chạy lần nữa, `soVong = 2` |

**Kết quả khi chạy** (`g++ -std=c++20`, ba lần giống nhau, TSan sạch):

```text
b = 2 3 1
so vong = 2
```

**Thử thay đổi: xóa dòng (3).** Mình đã chạy 2000 lần (`-O2`): **không lần nào** ra `b = 2 3 1`; kết quả đổi theo lần chạy, thường gặp nhất là `b = 0 0 1`, vì luồng đọc `a[...]` khi người bên cạnh chưa kịp ghi. TSan báo `WARNING: ThreadSanitizer: data race` giữa ghi `a[k]` và đọc `a[(k+1)%3]`. Barrier không phải để "tăng tốc", nó bảo đảm **bước trước của mọi người xong hẳn** rồi mới tới bước sau.

**Đối chiếu nhanh.** `latch` đếm **sự kiện** (`count_down` không chờ) và dùng **một lần**; `barrier` đếm **luồng tham gia** (mọi luồng chờ nhau) và **tự lặp**. Semaphore giới hạn số **đang ở trong**; latch "đủ rồi thì mở"; barrier "đợi nhau cùng qua" mỗi vòng.

### `std::shared_mutex`: đọc nhiều, ghi một, và nguy cơ đói ghi

`std::shared_mutex` (C++17, `<shared_mutex>`, đã nhận tên ở [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)) có **hai chế độ**: `std::shared_lock` cho **đọc** (nhiều luồng cùng lúc) và `std::unique_lock` cho **ghi** (giữ riêng, không ai khác vào, kể cả người đọc). Chương trình dưới: một luồng ghi tăng `a` và `b` cùng nhau 20000 lần; bốn luồng đọc kiểm bất biến `a == b` 20000 lần mỗi luồng.

```cpp
#include <iostream>
#include <mutex>
#include <shared_mutex>
#include <thread>
#include <vector>

std::shared_mutex khoa;
int a = 0, b = 0;                       // bất biến: lúc không ai đang ghi thì a == b

int main() {
    int viPham[4] = {0, 0, 0, 0};       // mỗi luồng đọc ghi vào ô riêng của mình

    std::thread ghi([] {
        for (int i = 0; i < 20000; ++i) {
            std::unique_lock<std::shared_mutex> lk(khoa);    // (1) ghi: giữ RIÊNG
            ++a;
            ++b;
        }
    });

    std::vector<std::thread> doc;
    for (int k = 0; k < 4; ++k) {
        doc.emplace_back([&viPham, k] {
            for (int i = 0; i < 20000; ++i) {
                std::shared_lock<std::shared_mutex> lk(khoa); // (2) đọc: nhiều luồng CÙNG lúc
                if (a != b) ++viPham[k];
            }
        });
    }
    ghi.join();
    for (std::thread& t : doc) t.join();

    std::cout << "a = " << a << ", b = " << b << "\n";
    std::cout << "vi pham bat bien = " << viPham[0] + viPham[1] + viPham[2] + viPham[3] << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `unique_lock` trên `shared_mutex`: chờ mọi người đọc ra hết, rồi giữ riêng; giữa `++a` và `++b` không ai chen vào |
| (2) | `shared_lock`: bốn luồng đọc có thể ở trong cùng lúc, nhưng không bao giờ cùng lúc với luồng ghi |

**Kết quả khi chạy:**

```text
a = 20000, b = 20000
vi pham bat bien = 0
```

Mình chạy ba lần giống nhau, TSan sạch. **Thử thay đổi 1:** đọc không khóa (xóa dòng (2)): TSan báo `data race` (đọc `a` song song với ghi dưới khóa); chương trình thường vẫn in `0` vi phạm vì cửa sổ lỗi hẹp, nên **một kết quả ra `0` không chứng minh gì**. **Thử thay đổi 2:** luồng ghi dùng `shared_lock` thay `unique_lock`: TSan báo `data race` giữa ghi `a` và đọc `a`, vì `shared_lock` không loại trừ người đọc. Sai chế độ khóa là lỗi hay gặp nhất với `shared_mutex`.

**Nguy cơ đói ghi (writer starvation).** Chuẩn C++ **không quy định** ai được ưu tiên khi người đọc liên tục đến trong lúc người ghi đang chờ: nếu cài đặt cho người đọc mới vào bất chấp người ghi đang chờ, người ghi có thể **không bao giờ** vào được. Mình thử trên g++ 11 / glibc (chương trình riêng, không đưa vào bài vì phụ thuộc cài đặt và thời gian): sáu luồng đọc, mỗi luồng lặp lại "`shared_lock`, ngủ 5 ms, nhả" gối đầu nhau; sau 100 ms một luồng ghi xin `unique_lock` rồi đặt một cờ `atomic`. Sau **1,5 giây** cờ vẫn chưa được đặt, ở cả 5 lần chạy; chỉ khi mình bảo các luồng đọc dừng hẳn, luồng ghi mới vào được.

Đó là kết quả của một cài đặt cụ thể, không phải điều chuẩn hứa; cái cần nhớ là **không được giả định** `shared_mutex` công bằng với người ghi. Cách chữa: giữ khóa đọc ngắn, tách bản sao dữ liệu ([Bài 61](61-mau-an-toan-luong.md)), hoặc dùng `mutex` thường nếu không chắc.

**Có nhanh hơn mutex không?** Khi vùng đọc **rất ngắn** (chỉ đọc một số nguyên), không. Mình đo (200000 lần đọc mỗi luồng, 8 lõi, 3 lần chạy, chương trình riêng không đưa vào bài): thời gian `shared_mutex` chia thời gian `mutex` ra 0,85 đến 2,6 lần với 1 luồng, khoảng 1,0 đến 1,5 với 4 luồng, 1,5 đến 1,7 với 8 luồng. Việc ghi nhận số người đọc cũng là một thao tác chung đang tranh chấp. `shared_mutex` đáng khi mỗi lần đọc **đủ dài** (tra bảng lớn, duyệt nhiều phần tử) để các lần đọc thật sự song song; không thì **đo trước**.

### Spinlock tự viết bằng `atomic_flag`

**Spinlock** là khóa mà luồng chờ **không ngủ**, mà quay vòng thử lại liên tục (chờ bận, [Bài 27](../nhom-3-da-luong/27-condition-variable.md) mục 1). Xây từ `std::atomic_flag` ([Bài 28](../nhom-3-da-luong/28-atomic.md) mục 7): `test_and_set()` đặt cờ lên và trả giá trị **cũ**; nếu cũ là `true` nghĩa là người khác đang giữ, quay lại thử. `clear()` hạ cờ. [Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md) đã giới thiệu spinlock và đo nó; ở đây ta xem kỹ cách nó đúng và đo lại bằng một lượt đo khác, nên số có thể khác số ở [Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md).

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

class Spinlock {
public:
    void lock() {
        while (co_.test_and_set()) {}      // (1) cờ đang lên: quay vòng thử lại, không ngủ
    }
    void unlock() {
        co_.clear();                       // (2) hạ cờ
    }
private:
    std::atomic_flag co_ = ATOMIC_FLAG_INIT;
};

Spinlock sl;
long long dem = 0;                         // biến thường, được spinlock bảo vệ

int main() {
    std::vector<std::thread> ds;
    for (int i = 0; i < 4; ++i) {
        ds.emplace_back([] {
            for (int k = 0; k < 100000; ++k) {
                sl.lock();                 // (3) vùng găng cực ngắn: một phép ++
                ++dem;
                sl.unlock();
            }
        });
    }
    for (std::thread& t : ds) t.join();
    std::cout << "dem = " << dem << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Một luồng thấy cờ xuống (`test_and_set` trả `false`) và tự đặt cờ lên: nó giữ khóa. Luồng khác thấy trả `true`, quay vòng |
| (2) | Hạ cờ: một trong các luồng đang quay sẽ thấy cờ xuống và vào |
| (3) | `dem` là biến thường mà không có data race, vì spinlock loại trừ lẫn nhau (như mutex) |

**Kết quả khi chạy:** `dem = 400000`, mình biên dịch sạch, TSan sạch. `ATOMIC_FLAG_INIT` là cách chuẩn khởi tạo cờ ở trạng thái "xuống" trước C++20 (C++20 không cần nữa).

**Khi nào dùng, khi nào KHÔNG.** Spinlock chỉ có lợi khi vùng găng **cực ngắn** và luồng giữ khóa **không bị hệ điều hành lấy mất lõi** (mỗi luồng có một lõi riêng); lúc đó quay vòng vài chục nano-giây rẻ hơn ngủ rồi dậy. Nó tệ khi có nhiều luồng hơn lõi hoặc vùng găng dài: luồng đang quay **đốt CPU** mà không giúp ai, và nếu luồng giữ khóa bị hoãn thì mọi người chờ vô ích.

Mình đo (`++` dưới khóa, 100000 lần mỗi luồng, 8 lõi, 4 lần chạy, chương trình riêng): spinlock chia mutex ra khoảng 0,6 đến 1,4 với 2 luồng; 1,6 đến 2,9 với 4; 2,6 đến 4,6 với 8; **9 đến 14** với 32 luồng. Quy tắc: **dùng `std::mutex`** (luồng chờ được hệ điều hành cho ngủ, không đốt CPU), spinlock chỉ khi đã đo và hiểu vì sao.

### Chọn cái nào

| Bạn cần | Dùng | Khi KHÔNG nên |
|---|---|---|
| Tối đa N luồng cùng ở trong một khu | `counting_semaphore` (C++17: tự viết) | Cần bảo vệ dữ liệu chung: dùng mutex |
| Báo "xong rồi" một lần, luồng báo không cần chờ ai | `latch`, hoặc `binary_semaphore` | Cần lặp nhiều vòng: `barrier` |
| Mọi luồng đợi nhau ở mỗi bước, lặp nhiều bước | `barrier` | Chỉ một luồng chờ: `latch` hoặc `join` |
| Đọc nhiều, ghi hiếm, mỗi lần đọc đủ dài | `shared_mutex` | Đọc cực ngắn hoặc cần công bằng với người ghi |
| Vùng găng cực ngắn, ít luồng hơn lõi | spinlock (sau khi đo) | Mọi trường hợp còn lại: `mutex` |

## Go: channel có đệm, `WaitGroup`, và mutex không có chủ

!!! info "Bạn biết Go?"
    Mình đã chạy Go 1.27.2 (`go run -race`, sạch):

    - **Semaphore trong Go là channel có đệm**: `cho := make(chan struct{}, 3)`; `cho <- struct{}{}` là `acquire` (đầy thì chặn), `<-cho` là `release`. Mình chạy đúng bài toán 8 goroutine, 3 chỗ, ghi đỉnh bằng `atomic.Int32`: ra `toi da <= 3: true 3`. Gói ngoài chuẩn `golang.org/x/sync/semaphore` có semaphore có trọng số.
    - **`sync.WaitGroup` gần nhất với `latch`**: `Add(n)`, `Done()` (giảm 1, không chờ), `Wait()`; khác `std::latch`, nó dùng lại được sau khi `Wait` trả về. Go **không có `barrier`** trong thư viện chuẩn: tự ghép bằng `WaitGroup` mỗi vòng hoặc channel.
    - **`sync.Mutex` của Go không có chủ**: tài liệu cho phép goroutine này `Lock`, goroutine khác `Unlock`; mình chạy `mu.Lock(); go func(){ mu.Unlock() }(); mu.Lock()` thì chạy bình thường. C++ thì không (mục 3).
    - `sync.RWMutex` ứng với `shared_mutex`; tài liệu Go nói khi một goroutine đang chờ `Lock`, các `RLock` mới bị chặn, tức Go **chống đói ghi**, khác lựa chọn "không quy định" của chuẩn C++.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Semaphore và mutex khác gì?"
    Mutex **loại trừ lẫn nhau** và **có chủ**: một luồng khóa thì chỉ luồng đó mở (luồng khác mở là hành vi không xác định); nó bảo vệ dữ liệu chung. Semaphore là **bộ đếm có chờ**, không có chủ: luồng nào cũng `release` được, cho tối đa N luồng vào cùng lúc, và làm được tín hiệu giữa các luồng khác nhau (khởi tạo 0). Binary semaphore đếm 0/1 giống mutex nhưng vẫn không có chủ, nên không thay mutex để bảo vệ dữ liệu. Nối tiếp "`release` bị mất thì sao": semaphore **nhớ** trong bộ đếm, không như `notify` của `condition_variable`.

??? question "Giới hạn tối đa 3 luồng gọi một dịch vụ ngoài; và tự viết semaphore."
    Một `counting_semaphore` giá trị đầu 3 (C++20): `acquire` trước khi gọi, `release` sau khi xong, qua một lớp RAII để không quên trả chỗ. Mutex chỉ cho 1; `atomic` đếm được nhưng không **chặn** luồng thứ tư. Ở C++17 tự viết: số đếm `dem_` dưới `mutex` + một `condition_variable`; `acquire` là `wait(lk, [this]{ return dem_ > 0; })` rồi `--dem_`; `release` là `++dem_` dưới khóa rồi `notify_one`. Predicate bắt buộc (spurious wakeup, và lúc dậy chỗ có thể đã bị người khác lấy). Kiểm chứng bằng một `atomic` ghi đỉnh đồng thời và khẳng định nó không vượt 3. [Bài 69](../nhom-9-thuc-chien-da-luong/69-semaphore-barrier-tu-cai.md) xây kỹ hơn.

??? question "`latch` khác `barrier` thế nào? Khi nào dùng `join` thay `latch`?"
    `latch` đếm ngược **một lần**: `count_down` không chờ, `wait` chờ tới 0, về 0 là xong vĩnh viễn; hợp với "chờ đủ N việc xong" hay "cổng xuất phát". `barrier` hẹn **các luồng tham gia** nhau, mỗi vòng mọi luồng chờ nhau rồi cùng đi tiếp, tự đặt lại cho vòng sau và có hàm hoàn tất mỗi vòng; hợp với tính toán chia bước. `join` chờ luồng **kết thúc hẳn**, đủ khi chỉ cần "chờ hết việc rồi gộp"; `latch` hơn ở chỗ luồng báo xong một phần mà vẫn chạy tiếp.

??? question "`shared_mutex` có thể gây vấn đề gì? Khi nào không đáng dùng?"
    Một: **đói ghi**, chuẩn không quy định ưu tiên, người đọc liên tục có thể giữ người ghi chờ mãi (mình tái hiện trên glibc). Hai: nó **không nhanh hơn `mutex`** khi vùng đọc rất ngắn, vì việc ghi nhận số người đọc cũng tranh chấp. Ba: lỗi hay gặp là dùng `shared_lock` để ghi. Câu trả lời an toàn: dùng `mutex`, đo, rồi mới cân nhắc `shared_mutex`.

??? question "Khi nào dùng spinlock?"
    Chỉ khi vùng găng **cực ngắn** (vài lệnh), số luồng không vượt số lõi và luồng giữ khóa không bị hoãn; khi đó quay vòng rẻ hơn ngủ-dậy. Ngược lại nó đốt CPU và chậm hơn mutex nhiều lần (mình đo 9 đến 14 lần với 32 luồng trên 8 lõi). `std::mutex` cho luồng chờ ngủ nên không đốt CPU; mặc định dùng mutex, spinlock chỉ sau khi đo.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên `release` khi thoát sớm"
    Gọi `acquire()` bằng tay rồi `return` sớm hoặc để ngoại lệ bay ra: chỗ không bao giờ được trả. Mình chạy một hàm `acquire`, `return false` mà không `release` trên `Semaphore(1)`: lần gọi thứ hai **treo** (`timeout 3` mã 124). Chữa bằng RAII như `lock_guard` của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md): lớp nhỏ gọi `acquire` ở hàm tạo, `release` ở hàm hủy; mình chạy lại với lớp đó, cả hai lần gọi xong bình thường.

!!! warning "Lỗi 2: Khóa sai chế độ, hoặc coi `shared_mutex` là mặc định"
    `shared_lock` để **ghi** là data race (TSan báo); đọc rất ngắn thì `mutex` thường vừa đơn giản vừa không chậm hơn; và đừng giả định người ghi sẽ được vào sớm.

!!! warning "Lỗi 3: Thiếu `-std=c++20`, đếm sai, hoặc spinlock quá nhiều luồng"
    Thiếu cờ thì `#include` qua nhưng `'latch' is not a member of 'std'`. Đặt `barrier(4)` mà chỉ 3 luồng đến thì mọi người chờ mãi; `count_down` quá số đếm là hành vi không xác định (mình thử: treo). Spinlock với nhiều luồng hơn lõi: CPU chạy hết công suất mà việc không xong nhanh hơn.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="60" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Một nhóm luồng mượn kết nối cơ sở dữ liệu, tổng cộng có 10 kết nối. Luồng nào cũng có thể xin một kết nối; xin lúc đã hết thì chờ; luồng giám sát cũng có lúc trả hộ kết nối đã bị bỏ quên. Nên dùng gì để giới hạn số kết nối đang mượn?

- Một `std::mutex` bọc mọi lần mượn và trả, để chỉ một luồng mượn tại một thời điểm
- Một `std::latch(10)`, mỗi lần mượn gọi `count_down` và chờ tới khi về 0
- Một `counting_semaphore` khởi tạo 10: `acquire` khi mượn, `release` khi trả
- Một `std::barrier(10)` để mười luồng cùng mượn và cùng trả một lượt

<p class="giai-thich" markdown>Bài toán là "tối đa N cùng lúc, hết thì chờ, ai trả cũng được": đúng chỗ của semaphore đếm, vì nó đếm chỗ trống và không có chủ nên luồng giám sát trả hộ được. Mutex chỉ cho một luồng vào, và `unlock` hộ người khác là hành vi không xác định. `latch` đếm ngược một lần rồi hết dùng, không phải giấy phép mượn-trả lặp lại. `barrier` bắt mười luồng đi cùng nhau, trong khi ở đây mỗi luồng mượn và trả theo lịch riêng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau, với `Semaphore` đếm như ở bài (bắt đầu từ 0). Luồng A chạy xong hẳn trước, rồi luồng B mới chạy. Điều gì xảy ra ở B?

```text
Semaphore san(0);
// luồng A:  san.release();
// luồng B:  san.acquire();  std::cout << "tiep";
```

- B in `tiep` ngay, vì `release` của A đã được đếm nên `acquire` không ngủ
- B ngủ mãi, vì `release` gọi khi chưa có luồng chờ thì bị mất như `notify`
- B ném ngoại lệ, vì một luồng chưa từng `acquire` không được phép gọi `release`
- B ngủ tới lần `release` kế tiếp, vì `acquire` chỉ nhận tín hiệu gửi sau khi nó bắt đầu chờ

<p class="giai-thich" markdown>`release` tăng bộ đếm từ 0 lên 1 và con số đó nằm lại; `acquire` thấy số lớn hơn 0 nên giảm xuống và đi tiếp, không ngủ. Chuyện "mất tín hiệu" là của `notify` trên `condition_variable`, vì chuông đó không giữ trạng thái. Semaphore không có chủ, nên luồng chưa từng `acquire` vẫn `release` hợp lệ, không có ngoại lệ nào. Và `acquire` không cần đợi tín hiệu đến sau, vì tín hiệu đã được ghi nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Chương trình chia 1..1000 cho 4 luồng cộng, mỗi luồng chỉ làm một lần rồi xong. Luồng chính cần đợi cả 4 xong rồi gộp kết quả, còn 4 luồng không cần chờ nhau. Công cụ phù hợp nhất trong C++20 là gì?

- `std::barrier(4)`, để bốn luồng hẹn nhau ở một vạch rồi cùng đi tiếp
- `std::binary_semaphore`, vì bốn luồng báo xong qua một thẻ duy nhất
- `std::shared_mutex`, để luồng chính giữ khóa đọc trong lúc gộp
- `std::latch(4)`, mỗi luồng `count_down` khi xong, luồng chính `wait`

<p class="giai-thich" markdown>Đây là "đếm cho đủ một lần": `latch(4)` cho mỗi luồng giảm một đơn vị mà không chờ ai, và luồng chính `wait` tới khi về 0. `barrier` bắt cả bốn luồng chờ nhau và dành cho nhiều vòng, nên thừa và gượng ở đây. Một `binary_semaphore` chỉ chứa 0 hoặc 1, không đếm được bốn lần báo. `shared_mutex` bảo vệ dữ liệu chứ không báo "việc đã xong".</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Mô phỏng 8 luồng, 1000 bước: ở mỗi bước, luồng nào cũng đọc kết quả bước trước của các luồng khác, nên không luồng nào được sang bước `t+1` trước khi cả 8 luồng hoàn thành bước `t`. Nên dùng gì?

- Tạo một `std::latch(8)` mới ở mỗi bước, vì latch dùng cho việc đếm đủ
- Một `std::barrier(8)` dùng chung cả 1000 bước, gọi `arrive_and_wait`
- Một `counting_semaphore<8>` để tối đa 8 luồng cùng chạy bước đó
- Một `std::mutex` khóa toàn bộ bước, để các luồng làm lần lượt

<p class="giai-thich" markdown>Cần "mọi người đợi nhau ở vạch, lặp nhiều vòng": `barrier` tự đặt lại sau mỗi vòng, nên một đối tượng phục vụ cả 1000 bước. Tạo latch mới mỗi bước chạy được nhưng rườm rà và tốn công, vì `latch` vốn dùng một lần. Semaphore chỉ giới hạn số luồng đang chạy, không bắt ai chờ ai, nên luồng nhanh vẫn chạy sang bước sau sớm. Mutex biến tám luồng thành tuần tự, mất hết ý nghĩa song song.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Một đoạn găng kéo dài khoảng 5 ms (đọc một tệp rồi ghi kết quả vào một bảng chung), có 16 luồng cùng tranh, máy có 8 lõi. Nên bảo vệ nó bằng gì?

- Spinlock tự viết bằng `atomic_flag`, vì spinlock luôn nhanh hơn mutex
- `std::shared_mutex` với `shared_lock`, vì đoạn này có đọc tệp
- `std::mutex`, để luồng chờ ngủ thay vì quay vòng đốt CPU
- Không cần khóa nào, vì đọc tệp chỉ là đọc nên không có gì tranh nhau

<p class="giai-thich" markdown>Vùng găng dài và số luồng gấp đôi số lõi là tình huống tệ nhất cho spinlock: 15 luồng chờ sẽ quay vòng hàng mili-giây mà không giúp được ai, nên `mutex` cho chúng ngủ mới hợp lý. Spinlock không "luôn nhanh hơn": mình đo nó chậm hơn mutex nhiều lần khi nhiều luồng. `shared_lock` chỉ đúng khi mọi người thực sự chỉ đọc dữ liệu chung, mà đoạn găng này còn ghi vào bảng chung, nên cần loại trừ nhau. Còn bỏ khóa thì không được: việc ghi vào bảng chung từ 16 luồng là data race.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Đọc đoạn sau. Hai luồng cùng chạy một lần mỗi luồng. Điều nào đúng?

```text
std::shared_mutex m;  int dem = 0;
// luồng 1:  { std::shared_lock<std::shared_mutex> lk(m);  ++dem; }
// luồng 2:  { std::shared_lock<std::shared_mutex> lk(m);  ++dem; }
```

- Luôn an toàn, vì cả hai đều xin khóa của cùng một `shared_mutex`
- Có data race, vì `shared_lock` cho cả hai vào cùng lúc để ghi `dem`
- Luồng 2 bị chặn tới khi luồng 1 xong, vì `shared_mutex` vẫn là một mutex
- Không biên dịch được, vì `shared_lock` không dùng để sửa biến

<p class="giai-thich" markdown>`shared_lock` là chế độ đọc nên nhiều luồng được vào cùng lúc; hai `++dem` đồng thời trên một biến thường là data race, và TSan sẽ báo. Chung một `shared_mutex` không đủ: chế độ khóa mới quyết định có loại trừ nhau hay không. Luồng 2 không bị chặn, vì khóa chia sẻ không loại trừ khóa chia sẻ khác. Còn trình biên dịch không kiểm tra ý định "chỉ đọc", nên đoạn này biên dịch bình thường rồi sai lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Luồng A gọi `m.lock()` trên một `std::mutex m`, rồi luồng B gọi `m.unlock()` để "nhường lại". Điều nào đúng?

- Là hành vi không xác định: `std::mutex` phải do chính luồng khóa mở
- Hợp lệ, vì mutex chỉ là một cờ nên luồng nào cũng mở được
- Hợp lệ, nhưng chỉ khi B gọi `unlock` ngay trước khi A thoát
- Chuẩn bắt `unlock` ném `std::system_error`, nên B nhận ngoại lệ có thể bắt được

<p class="giai-thich" markdown>Mutex có chủ: chuẩn yêu cầu luồng gọi `unlock` đang giữ khóa, vi phạm là hành vi không xác định, nên bạn không thể dựa vào kết quả nào. Nếu cần người khác báo hộ thì dùng semaphore hoặc `condition_variable`. Câu "chỉ là một cờ" nghe hợp lý vì mutex cài đặt đơn giản, nhưng chuẩn không cho phép dựa vào điều đó (Go thì cho, đó là khác biệt giữa hai ngôn ngữ). Chuẩn cũng không hứa ném ngoại lệ ở tình huống này, và thời điểm gọi không làm nó hợp lệ.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Semaphore là bộ đếm có chờ (`acquire` giảm, hết thì ngủ; `release` tăng và đánh thức), không có chủ: luồng nào cũng `release` được, khác `std::mutex` (phải do chính luồng khóa mở); `release` được đếm lại nên không mất như `notify`; C++17 tự viết bằng `mutex` + `condition_variable` (mình chạy: 8 luồng, 3 chỗ, đỉnh đồng thời `<= 3` đúng, bỏ semaphore thì đỉnh 8, TSan sạch).
2. C++20 có `std::counting_semaphore<N>`, `std::binary_semaphore`, `std::latch`, `std::barrier`; mình kiểm tra thật: `g++ -std=c++20` biên dịch được, `-std=c++17` báo `'...' is not a member of 'std'`, nên các khối C++20 trong bài đặt `// bo-qua-kiem-tra` kèm lệnh `-std=c++20` (đã chạy, sạch).
3. `latch` đếm ngược **một lần** (`count_down` không chờ, `wait` chờ tới 0: "chờ đủ N việc xong", "cổng xuất phát"); `barrier` hẹn các luồng tham gia **nhiều vòng** (`arrive_and_wait`, tự đặt lại, có hàm hoàn tất mỗi vòng); bỏ vạch thì đọc nhầm dữ liệu chưa ghi (mình chạy 2000 lần, TSan báo data race).
4. `shared_mutex` cho nhiều luồng đọc hoặc một luồng ghi; ghi dùng `unique_lock`, đọc dùng `shared_lock` (sai chế độ là data race); chuẩn không quy định ưu tiên nên có thể **đói ghi** (mình tái hiện trên glibc), và với vùng đọc rất ngắn nó không nhanh hơn `mutex`.
5. Spinlock tự viết bằng `atomic_flag` (`test_and_set` quay vòng, `clear` mở) chỉ hợp với vùng găng cực ngắn và ít luồng hơn lõi; mình đo nó chậm hơn `mutex` 9 đến 14 lần với 32 luồng trên 8 lõi, nên mặc định dùng `mutex` rồi mới đo; Go: channel có đệm làm semaphore, `WaitGroup` gần `latch`, `sync.Mutex` của Go không có chủ còn `std::mutex` thì có.
