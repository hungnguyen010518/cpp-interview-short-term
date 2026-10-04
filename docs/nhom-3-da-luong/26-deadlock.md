# Bài 26 — Deadlock: khi các luồng chờ nhau mãi mãi

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng **deadlock** là gì và nêu **bốn điều kiện** cùng xảy ra mới có nó (chỉ ý chính, nhớ rằng phá một điều kiện là hết deadlock); thấy tận mắt chương trình chuyển tiền giữa hai tài khoản treo thật.
    - Tránh deadlock bằng cách khóa theo **thứ tự cố định**, hoặc khóa nhiều mutex một lần bằng `std::scoped_lock` (C++17) / `std::lock`; biết thêm ba hướng: giữ khóa ngắn và không gọi hàm lạ, `try_lock_for` có hạn chờ, giảm khóa lồng nhau.
    - Nhận ra **tự deadlock** (một luồng xin lại khóa mình đang giữ), và phân biệt deadlock với **livelock** và **starvation** (chỉ định nghĩa ngắn).
    - Tìm deadlock trong chương trình đang treo bằng `gdb` (`info threads`, `thread apply all bt`) và bằng ThreadSanitizer; so với Go, nơi runtime chỉ báo deadlock khi **mọi** goroutine đều ngủ.

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, `std::ref`, lambda làm hàm luồng, `sleep_for`), [Bài 25](25-data-race-mutex.md) (`std::mutex`, `lock_guard`, vùng găng, TSan, khóa hai lần trong một luồng là hành vi không xác định), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, hàm hủy), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (tham chiếu `&`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`{...}` điền các trường của struct, `điều kiện ? A : B`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) và [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda `[&]`, con trỏ hàm), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, sanitizer).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](25-data-race-mutex.md), nhưng giờ bếp có **hai thớt**, mỗi thớt một **thẻ vào thớt**. Món "chuyển hành từ thớt 1 sang thớt 2" cần cầm cả hai thẻ. Đầu bếp An lấy thẻ thớt 1 trước rồi mới đi xin thẻ thớt 2. Đầu bếp Bình lại lấy thẻ thớt 2 trước rồi mới đi xin thẻ thớt 1.

Nếu cả hai cùng lấy được thẻ đầu tiên của mình, An đứng chờ Bình trả thẻ thớt 2, còn Bình đứng chờ An trả thẻ thớt 1. Không ai chịu trả thẻ đang cầm khi chưa xong việc, nên cả bếp đứng im.

Đó là **deadlock** (khóa chết): các luồng chờ nhau theo vòng tròn nên không luồng nào chạy tiếp được.

!!! info "Chỗ nào ví von hai thẻ không còn đúng?"
    Đầu bếp thật nhìn thấy nhau, biết nhường nhau và biết xin lỗi trả thẻ. Luồng thì không: `lock()` chỉ biết đứng chờ, và g++ trên máy mình **không tự phát hiện** deadlock hay tự gỡ. Chương trình treo im lặng, không báo lỗi.

## 📖 Giải thích

### 1. Deadlock là gì: ví dụ chuyển tiền

**Deadlock** là tình trạng hai hay nhiều luồng chờ nhau mãi, mỗi luồng đang giữ thứ mà luồng khác cần.

Ví dụ kinh điển: hàm `chuyen(tu, den, tien)` khóa tài khoản gửi, rồi khóa tài khoản nhận, rồi trừ và cộng tiền. Một luồng chuyển `a → b`, luồng kia chuyển `b → a`: hai luồng khóa hai mutex theo thứ tự **ngược nhau**.

Cú pháp mới trong ví dụ: `TaiKhoan a{{}, 100};` điền các trường theo thứ tự như [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md): `{}` đầu cho mutex `khoa` (mutex mới, chưa bị khóa), `100` cho `soDu`. `std::ref(a)` ([Bài 24](24-thread-co-ban.md)) để luồng nhận chính `a`, không phải bản sao (mutex không sao chép được).

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

struct TaiKhoan {
    std::mutex khoa;
    int soDu;
};

void chuyen(TaiKhoan& tu, TaiKhoan& den, int tien) {
    std::lock_guard<std::mutex> g1(tu.khoa);                          // (1) khóa tài khoản gửi
    std::this_thread::sleep_for(std::chrono::milliseconds(50));       // (2) cho luồng kia kịp khóa
    std::lock_guard<std::mutex> g2(den.khoa);                         // (3) khóa tài khoản nhận
    tu.soDu -= tien;
    den.soDu += tien;
}

int main() {
    TaiKhoan a{{}, 100};
    TaiKhoan b{{}, 100};
    std::thread t1(chuyen, std::ref(a), std::ref(b), 10);   // a -> b
    std::thread t2(chuyen, std::ref(b), std::ref(a), 20);   // b -> a
    t1.join();
    t2.join();
    std::cout << "a = " << a.soDu << ", b = " << b.soDu << "\n";
    return 0;
}
```

**Chạy từng dòng** (một dòng thời gian có thể xảy ra, và dòng (2) làm nó xảy ra gần như chắc chắn)

| Lúc | Luồng `t1` (`a → b`) | Luồng `t2` (`b → a`) |
|---|---|---|
| 1 | (1) khóa `a.khoa`: được | (1) khóa `b.khoa`: được |
| 2 | (2) ngủ 50 ms | (2) ngủ 50 ms |
| 3 | (3) xin `b.khoa`: `t2` đang giữ, chờ | (3) xin `a.khoa`: `t1` đang giữ, chờ |
| 4 | chờ mãi (`t2` không bao giờ trả) | chờ mãi (`t1` không bao giờ trả) |

Luồng chính ở `t1.join()` chờ `t1`, nên cả chương trình đứng.

**Kết quả khi chạy:** mình biên dịch sạch cảnh báo (`g++ -std=c++17 -Wall -Wextra -pthread`) và chạy với `timeout 3 ./treo` (lệnh giết chương trình sau 3 giây). Chương trình **không in gì**, và `timeout` thoát với mã **124**, mã nó dùng khi hết giờ. Khối mã này đặt `// bo-qua-kiem-tra` vì nó treo.

!!! warning "Hay nhầm"
    Dòng (2) chỉ để bài này tái hiện được lỗi. Mình thử bỏ nó: chạy 40 lần liền, **không lần nào** treo, vì luồng đầu thường làm xong cả hai khóa trước khi luồng sau kịp bắt đầu. Đó chính là điểm đáng sợ: deadlock **hiếm và hên xui** nên lọt qua thử nghiệm rồi mới nổ khi chạy thật.

**Thử thay đổi: đưa `t1.join()` lên ngay sau dòng tạo `t1`** (luồng `t2` chỉ bắt đầu khi `t1` đã xong). Mình đã chạy: không treo, in `a = 110, b = 90` (a: 100 trừ 10 cộng 20; b: 100 cộng 10 trừ 20).

Nhưng chương trình **vẫn có lỗi thiết kế**, và ThreadSanitizer vẫn báo nó (mục 3).

!!! info "Bạn biết Go?"
    Go có đúng loại lỗi này: hai goroutine khóa hai `sync.Mutex` ngược thứ tự thì kẹt nhau. Điểm khác là **ai báo**, ở mục 4.

### 2. Bốn điều kiện của deadlock

Deadlock chỉ xảy ra khi **cả bốn** điều kiện dưới đây cùng đúng. Bạn chỉ cần nhớ ý và nhớ hệ quả: **phá một điều kiện là hết deadlock**.

| Điều kiện | Ý chính | Trong ví dụ chuyển tiền | Cách phá |
|---|---|---|---|
| Loại trừ lẫn nhau | Mỗi mutex chỉ một luồng giữ tại một lúc | `a.khoa`, `b.khoa` | Khó phá: chính vì dữ liệu chung nên mới có khóa |
| Giữ-và-chờ | Luồng đang giữ khóa này mà đi xin khóa khác | `t1` giữ `a.khoa` và xin `b.khoa` | Xin tất cả khóa cùng một lúc (`scoped_lock`) |
| Không bị giành lại | Không ai lấy khóa khỏi tay người đang giữ | Không ai ép `t1` trả `a.khoa` | Có hạn chờ rồi tự nhả (`try_lock_for`) |
| Chờ vòng tròn | `t1` chờ `t2`, `t2` chờ `t1` (hay một vòng dài hơn) | `a → b` gặp `b → a` | Khóa theo thứ tự cố định |

### 3. Tìm deadlock: TSan và gdb

**ThreadSanitizer** ([Bài 25](25-data-race-mutex.md)) cũng bắt được thứ tự khóa ngược nhau. Biên dịch kèm `-g -fsanitize=thread`.

Một lưu ý (mình quan sát được, không phải điều chuẩn hứa): TSan báo khi các khóa **thực sự được xin xong** theo hai thứ tự ngược nhau. Bản treo ở mục 1 không bao giờ xin xong khóa thứ hai, nên mình chạy nó với TSan thì **không ra báo cáo nào** và vẫn timeout mã 124. Bản "thử thay đổi" (chạy lần lượt, không treo) thì TSan báo ngay.

Báo cáo thật, mình rút gọn (bỏ các dòng ngăn xếp gọi của thư viện, đường dẫn tệp, số địa chỉ). Số dòng `:14` tính khi bỏ dòng chú thích `// bo-qua-kiem-tra` đầu tệp; nếu bạn chép cả dòng đó, nó thành 15 (mình đã thử):

```text
WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock)
  Cycle in lock order graph: M11 (0x...) => M12 (0x...) => M11

  Mutex M12 acquired here while holding mutex M11 in thread T1:
    #4 chuyen(TaiKhoan&, TaiKhoan&, int) tt.cpp:14
  Mutex M11 acquired here while holding mutex M12 in thread T2:
    #4 chuyen(TaiKhoan&, TaiKhoan&, int) tt.cpp:14

SUMMARY: ThreadSanitizer: lock-order-inversion (potential deadlock) ... in __gthread_mutex_lock
```

Đọc báo cáo: `T1` xin `M12` khi đang giữ `M11`, còn `T2` xin `M11` khi đang giữ `M12`; đó là chu trình. TSan chỉ **cảnh báo có thể deadlock** dù lần chạy này không treo, và thoát mã 66 như khi báo data race.

TSan trên máy mình phải chạy qua `setarch $(uname -m) -R ./chuongtrinh` ([Bài 25](25-data-race-mutex.md)).

Khi chương trình **đang treo** và bạn không có bản biên dịch với TSan, dùng **gdb**: trình gỡ lỗi (debugger) cho dừng chương trình đang chạy và xem từng luồng đang đứng ở đâu. Biên dịch thêm `-g` để gdb thấy tên hàm và số dòng.

Cách thông thường là gắn gdb vào tiến trình đang chạy bằng `gdb -p <số hiệu tiến trình>`. Máy mình chặn việc đó (`ptrace_scope` bằng 1, gdb báo `Could not attach to process`), nên mình chạy chương trình **ngay trong gdb** rồi bấm Ctrl+C. Ở lệnh dưới, mình gửi Ctrl+C từ ngoài sau 2 giây. `-batch` bảo gdb chạy các lệnh rồi thoát, và mỗi `-ex "lệnh"` bảo gdb chạy đúng lệnh đó (`run` là chạy chương trình).

```text
gdb -batch -ex run -ex "info threads" -ex "thread apply all bt 8" ./treo
```

- `info threads` liệt kê các luồng và chỗ mỗi luồng đang đứng; cột `Id` là số thứ tự gdb gán (1, 2, 3), dấu `*` đánh dấu luồng đang được chọn.
- `thread apply all bt` chạy `bt` (backtrace: chuỗi hàm đang gọi, từ trong ra ngoài) cho **mọi** luồng. Phần `8` chỉ lấy tám khung đầu.

Kết quả thật, rút gọn (cắt bớt cột; số dòng `treo.cpp:14`, `:24` cũng tính khi bỏ dòng chú thích đầu tệp, chép cả dòng đó thì thành 15 và 25; `LWP` là số hiệu luồng do hệ điều hành cấp, mỗi lần chạy một khác):

```text
Thread 1 "treo" received signal SIGINT, Interrupt.
  Id   Target Id                              Frame
* 1    Thread 0x7ffff7ea13c0 (LWP 2755456) "treo" __futex_abstimed_wait_common64 (...)
  2    Thread 0x7ffff77ff640 (LWP 2755459) "treo" futex_wait (...)
  3    Thread 0x7ffff6ffe640 (LWP 2755460) "treo" futex_wait (...)

Thread 2 (Thread 0x7ffff77ff640 (LWP 2755459) "treo"):
#3  ___pthread_mutex_lock (mutex=0x7fffffffd3b0) at ./nptl/pthread_mutex_lock.c:93
#5  0x... in std::mutex::lock (this=0x7fffffffd3b0) at /usr/include/c++/11/bits/std_mutex.h:100
#7  0x... in chuyen (tu=..., den=..., tien=10) at treo.cpp:14
Thread 3 (Thread 0x7ffff6ffe640 (LWP 2755460) "treo"):
#3  ___pthread_mutex_lock (mutex=0x7fffffffd380) at ./nptl/pthread_mutex_lock.c:93
#5  0x... in std::mutex::lock (this=0x7fffffffd380) at /usr/include/c++/11/bits/std_mutex.h:100
#7  0x... in chuyen (tu=..., den=..., tien=20) at treo.cpp:14
Thread 1 (Thread 0x7ffff7ea13c0 (LWP 2755456) "treo"):
#4  0x... in std::thread::join() () from /lib/x86_64-linux-gnu/libstdc++.so.6
#5  0x... in main () at treo.cpp:24
```

Ý nghĩa: hai luồng phụ cùng đứng trong `std::mutex::lock`, ở **cùng một dòng** của `chuyen` (dòng khóa tài khoản nhận) nhưng trên **hai mutex khác nhau** (địa chỉ `...d3b0` và `...d380`); luồng chính đứng ở `join`.

Để chắc rằng mỗi luồng chờ mutex do luồng kia giữ, mình hỏi gdb ai đang giữ mutex mà mỗi luồng chờ, bằng ba lệnh:

- `thread 2` chọn luồng có `Id` 2 trong `info threads`;
- `frame 7` nhảy tới khung `#7` trong `bt` của luồng đó, chính là hàm `chuyen` của ta (nhờ vậy mới dùng được tên `den`);
- `print den.khoa._M_mutex.__data.__owner` in giá trị biểu thức đó trong khung này, tức số hiệu luồng đang giữ `den.khoa`.

Ở luồng 2 nó ra `2755460`, đúng `LWP` của luồng 3; làm tương tự ở luồng 3 ra `2755459`, đúng `LWP` của luồng 2. `futex_wait` trong kết quả là lời gọi hệ điều hành để ngủ chờ; bạn chỉ cần tìm chữ `lock` và tên hàm của mình.

Tên trường `_M_mutex.__data.__owner` là chi tiết của g++ 11 và glibc trên máy mình, không phải chuẩn C++.

### 4. Cách tránh, theo thứ tự nên thử

1. **Luôn khóa theo thứ tự cố định.** Mọi luồng cần cả hai mutex thì cùng khóa cái "nhỏ hơn" trước (theo `id`), nên không thể có vòng chờ. Phá điều kiện chờ vòng tròn.
2. **Khóa nhiều mutex một lần**: `std::scoped_lock` (C++17) hoặc `std::lock` (C++11). Chuẩn bảo đảm chúng xin các mutex theo cách **không gây deadlock**, bất kể bạn liệt kê theo thứ tự nào. Phá điều kiện giữ-và-chờ.
3. **Giữ khóa ngắn, và không gọi hàm lạ khi đang giữ khóa** (mục 5).
4. **`try_lock` hoặc có hạn chờ**: thử xin, thất bại thì nhả những gì đang giữ (mục 💻, cuối).
5. **Giảm khóa lồng nhau và thiết kế lại**: nếu thấy mình cần khóa hai mutex cùng lúc, hỏi lại xem hai dữ liệu đó có thể dùng **chung một mutex** (đơn giản, nhưng các luồng chờ nhau nhiều hơn), hoặc có thể gom việc chuyển tiền về một luồng xử lý duy nhất không.

Hai cách đầu có ví dụ chạy được ở mục 💻. Trước đó là những chuyện dễ gặp ngoài ví dụ chuyển tiền.

### 5. Các dạng gần deadlock

**Gọi hàm lạ khi đang giữ khóa.** Hàm `duyet` dưới đây giữ khóa rồi gọi một hàm do người khác đưa vào (**callback**: hàm bạn đưa cho nơi khác gọi lại, qua con trỏ hàm như [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)). Nếu hàm đó lại xin chính mutex ấy, **một luồng** đã tự chờ chính mình.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>

std::mutex khoa;
int dem = 0;

void ghi() {
    std::lock_guard<std::mutex> giu(khoa);            // (3) xin khóa lần hai: cùng luồng
    ++dem;
}

void duyet(void (*callback)()) {
    std::lock_guard<std::mutex> giu(khoa);            // (1) đang giữ khóa
    callback();                                       // (2) gọi hàm do người khác đưa
}

int main() {
    duyet(ghi);
    std::cout << "dem = " << dem << "\n";
    return 0;
}
```

**Chạy từng dòng** (theo thứ tự thực thi, không theo thứ tự trong tệp)

| Dòng | Chuyện gì xảy ra | `khoa` lúc này |
|---|---|---|
| (1) | `duyet` xin `khoa`: được | luồng này giữ |
| (2) | `duyet` gọi `callback`, tức `ghi` | luồng này giữ |
| (3) | `ghi` xin `khoa` lần hai, cũng từ luồng này: chờ chính mình | luồng này giữ, không ai trả |

Mình biên dịch sạch và chạy `timeout 3`: không in gì, mã **124**.

[Bài 25](25-data-race-mutex.md) đã nói xin lại `std::mutex` đang giữ là hành vi không xác định: chuẩn không hứa gì, còn **trên máy mình** nó treo. Ta gọi đó là **tự deadlock** (self-deadlock): một luồng là đủ.

Một biến thể hay gặp khác: giữ khóa rồi `join` một luồng cần đúng khóa đó (luồng chờ khóa, `join` chờ luồng), như ví dụ treo ở [Bài 25](25-data-race-mutex.md).

Quy tắc: không gọi hàm mà bạn không kiểm soát (callback, hàm của thư viện khác) khi đang giữ khóa; lấy dữ liệu ra, nhả khóa, rồi mới gọi.

**`std::recursive_mutex`** (`#include <mutex>`) cho **cùng một luồng** xin lại nhiều lần (mỗi lần xin phải có một lần trả). Mình đổi `std::mutex` thành `std::recursive_mutex` ở khai báo `khoa` và ở hai `lock_guard` của chương trình trên: chạy được, in `dem = 1`. Nó chỉ che lỗi thiết kế, và vẫn không cứu hai luồng khóa ngược thứ tự; chỉ dùng khi thật cần.

**Livelock** (khóa sống): các luồng **vẫn chạy**, liên tục đổi trạng thái (nhường nhau, nhả rồi thử lại) nhưng không tiến được việc nào. Khác deadlock ở chỗ luồng không đứng im mà vẫn tốn CPU.

**Starvation** (đói tài nguyên): một luồng mãi không được khóa vì luồng khác luôn giành được trước, dù hệ thống không bị kẹt hẳn. Bài này chỉ cần nhớ hai định nghĩa.

## 💻 Ví dụ code

### Cách 1: khóa theo thứ tự cố định (theo `id`)

Mỗi tài khoản có một `id` khác nhau. `chuyen` luôn khóa tài khoản có `id` nhỏ hơn trước, nên hai luồng `a → b` và `b → a` khóa cùng một thứ tự.

```cpp
#include <iostream>
#include <mutex>
#include <thread>

struct TaiKhoan {
    int id;
    std::mutex khoa;
    int soDu;
};

void chuyen(TaiKhoan& tu, TaiKhoan& den, int tien) {
    TaiKhoan& dau = (tu.id < den.id) ? tu : den;      // (1) tài khoản có id nhỏ hơn
    TaiKhoan& sau = (tu.id < den.id) ? den : tu;      // (2) tài khoản còn lại
    std::lock_guard<std::mutex> g1(dau.khoa);         // (3) luôn khóa id nhỏ trước
    std::lock_guard<std::mutex> g2(sau.khoa);         // (4) rồi mới tới id lớn
    tu.soDu -= tien;
    den.soDu += tien;
}

int main() {
    TaiKhoan a{1, {}, 5000};
    TaiKhoan b{2, {}, 5000};
    std::thread t1([&] { for (int i = 0; i < 1000; ++i) chuyen(a, b, 3); });   // a -> b
    std::thread t2([&] { for (int i = 0; i < 1000; ++i) chuyen(b, a, 2); });   // b -> a
    t1.join();
    t2.join();
    std::cout << "a = " << a.soDu << ", b = " << b.soDu << ", tong = " << a.soDu + b.soDu << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Thứ tự khóa |
|---|---|---|
| (1), (2) | Chọn ra tài khoản `id` nhỏ (`dau`) và `id` lớn (`sau`), không phụ thuộc ai là gửi, ai là nhận | |
| (3) | Khóa `dau`: ở cả hai luồng đó đều là `a` (id 1) | `a` |
| (4) | Khóa `sau`: cả hai luồng đều là `b` (id 2) | `a` rồi `b` |
| sau (4) | Trừ tiền người gửi, cộng người nhận (dùng `tu`, `den` đúng chiều); cuối hàm nhả `b` rồi `a` | |

**Kết quả khi chạy** (ba lần liền đều như nhau; với `-fsanitize=thread` sạch cảnh báo, mã thoát 0):

```text
a = 4000, b = 6000, tong = 10000
```

Số dư cuối tính được bằng tay: `a` có 5000, mất 1000 lần 3 (3000), nhận 1000 lần 2 (2000) nên còn 4000; `b` ngược lại ra 6000; tổng không đổi. Kết quả chỉ được in sau `join`, nên ổn định.

### Cách 2: `std::scoped_lock`, khóa cả hai một lần

`std::scoped_lock` (C++17, `#include <mutex>`) nhận nhiều mutex, xin tất cả một lần và trả tất cả khi bị hủy (RAII như `lock_guard`). Bạn không cần kiểu trong `<...>`: g++ ở `-std=c++17` tự suy ra từ các đối số.

```cpp
#include <iostream>
#include <mutex>
#include <thread>

struct TaiKhoan {
    std::mutex khoa;
    int soDu;
};

void chuyen(TaiKhoan& tu, TaiKhoan& den, int tien) {
    std::scoped_lock giu(tu.khoa, den.khoa);   // (1) khóa CẢ HAI một lần, không deadlock
    tu.soDu -= tien;
    den.soDu += tien;
}

int main() {
    TaiKhoan a{{}, 5000};
    TaiKhoan b{{}, 5000};
    std::thread t1([&] { for (int i = 0; i < 1000; ++i) chuyen(a, b, 3); });   // a -> b
    std::thread t2([&] { for (int i = 0; i < 1000; ++i) chuyen(b, a, 2); });   // b -> a
    t1.join();
    t2.join();
    std::cout << "a = " << a.soDu << ", b = " << b.soDu << ", tong = " << a.soDu + b.soDu << "\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
a = 4000, b = 6000, tong = 10000
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `scoped_lock` xin cả `tu.khoa` và `den.khoa` cùng lúc; luồng nào tới sau thì chờ, không giữ một khóa rồi chờ khóa kia |
| sau (1) | Trừ và cộng tiền; cuối hàm hủy `giu` trả cả hai khóa |

Hai luồng truyền hai mutex theo thứ tự ngược nhau (`a, b` và `b, a`) mà không treo, vì chuẩn bảo đảm `scoped_lock` tránh deadlock bất kể thứ tự đối số. Chuẩn không quy định thuật toán bên trong; bạn chỉ dựa vào lời bảo đảm đó.

**`std::lock`** (C++11) làm đúng việc khóa nhiều mutex một lần nhưng **không** tự trả khóa; muốn RAII bạn phải bọc từng mutex bằng `std::lock_guard` với tham số thứ hai `std::adopt_lock` ("mutex này đã bị khóa rồi, chỉ nhận trách nhiệm trả"; coi nó như một thẻ đánh dấu, không cần hiểu sâu).

Mình ghép ba dòng dưới vào hàm `chuyen` của cách 2 và biên dịch ở `-std=c++11`: ra `a = 4000, b = 6000, tong = 10000`, TSan sạch.

```text
std::lock(tu.khoa, den.khoa);
std::lock_guard<std::mutex> g1(tu.khoa, std::adopt_lock);
std::lock_guard<std::mutex> g2(den.khoa, std::adopt_lock);
```

Từ C++17 cứ dùng `scoped_lock` cho gọn.

!!! warning "Hay nhầm"
    `scoped_lock` không cứu được trường hợp hai mutex **là một**. Mình thử `chuyen(a, a, 3)` (gửi cho chính mình) với `scoped_lock giu(tu.khoa, den.khoa)`: treo (`timeout 3` mã 124). Chuẩn không hứa gì ở đây: xin lại `std::mutex` đang giữ là hành vi không xác định ([Bài 25](25-data-race-mutex.md)), mình chỉ biết trên máy mình (g++ 11) nó treo. Cách 1 theo `id` cũng hỏng nếu hai `id` trùng, vì `dau` và `sau` khi đó là cùng một tài khoản. Cách tránh: `if (&tu == &den) return;` ở đầu hàm.

### `try_lock_for`: có hạn chờ thay vì chờ mãi

`std::timed_mutex` (`#include <mutex>`) là mutex có thêm `try_lock_for(khoảng thời gian)`: chờ tối đa khoảng đó, trả `true` nếu lấy được khóa, `false` nếu hết giờ. Luồng chính giữ khóa suốt, nên luồng phụ chắc chắn hết giờ:

```cpp
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

std::timed_mutex khoa;

int main() {
    khoa.lock();                                           // (1) luồng chính giữ khóa
    std::thread t([] {
        if (khoa.try_lock_for(std::chrono::milliseconds(50))) {   // (2) chờ tối đa 50 ms
            std::cout << "luong phu: lay duoc khoa\n";
            khoa.unlock();
        } else {
            std::cout << "luong phu: het gio, bo cuoc\n";         // (3) không treo mãi
        }
    });
    t.join();
    khoa.unlock();
    return 0;
}
```

**Kết quả khi chạy** (TSan sạch, mã thoát 0):

```text
luong phu: het gio, bo cuoc
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Luồng chính khóa `khoa` và không trả trong lúc `t` chạy |
| (2) | `t` chờ tối đa 50 ms; luồng chính vẫn giữ nên hết giờ, `try_lock_for` trả `false` |
| (3) | `t` in lời bỏ cuộc rồi kết thúc; `join` xong thì luồng chính mới trả khóa |

Có hạn chờ không tự giải quyết deadlock: nó chỉ cho luồng **cơ hội bỏ cuộc**, và bạn phải viết thêm cách xử lý (nhả khóa đang giữ, thử lại sau, báo lỗi). Thử lại ngay lập tức ở cả hai luồng chính là cách rơi vào livelock. Ở mức bài này, chỉ cần biết `try_lock`/`try_lock_for` tồn tại.

## Go: ai phát hiện deadlock?

!!! info "Bạn biết Go?"
    Mình chạy Go 1.27.1 thật. Ba kết quả:

    - `mu.Lock()` hai lần liền trong `main`, không còn goroutine nào khác: runtime in `fatal error: all goroutines are asleep - deadlock!` rồi thoát mã 2. (Mutex của Go không tái nhập, nên đây là deadlock **có định nghĩa rõ**, không phải hành vi không xác định như C++.)
    - Bản Go của ví dụ chuyển tiền (hai goroutine khóa ngược thứ tự, `main` đứng ở `wg.Wait()`): cũng bị bắt với đúng thông báo trên, kèm danh sách ba goroutine đang ngủ. Lý do: lúc đó **mọi** goroutine đều đang chờ.
    - Cùng ví dụ nhưng có **một goroutine khác còn sống** (vòng lặp in một dòng mỗi 200 ms): **không có báo cáo nào**. Hai thử nghiệm:
        - cho `main` chờ vô hạn bằng `select {}`: chương trình chạy tới khi `timeout 3` giết (mã 124);
        - để `main` ngủ 1 giây rồi thoát: chương trình thoát bình thường và số dư vẫn `100 100`, tức hai việc chuyển tiền không bao giờ xong, im lặng.

    Vậy runtime Go chỉ báo khi **mọi** goroutine không thể chạy tiếp; còn kẹt cục bộ trong khi chỗ khác vẫn sống thì không. g++ mặc định thì không tự phát hiện cả hai trường hợp. Cách phòng ở cả hai ngôn ngữ giống nhau: thứ tự khóa cố định. Go không có hàm kiểu `scoped_lock`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Deadlock là gì, bốn điều kiện, cách tránh?"
    Deadlock là hai hay nhiều luồng chờ nhau mãi, mỗi luồng giữ một tài nguyên (ở đây là mutex) mà luồng khác cần. Cần cả bốn điều kiện: loại trừ lẫn nhau (tài nguyên chỉ một luồng giữ), giữ-và-chờ (giữ cái này, xin cái khác), không bị giành lại (không ai cướp được khóa khỏi người giữ) và chờ vòng tròn (chuỗi luồng chờ khép kín); phá một điều kiện là hết deadlock. Tránh: khóa theo thứ tự cố định (phá chờ vòng tròn); khóa nhiều mutex một lần bằng `std::scoped_lock` (C++17) hay `std::lock`; giữ khóa ngắn, không gọi callback khi giữ khóa; dùng `try_lock`/`try_lock_for` để bỏ cuộc; hoặc thiết kế lại để khỏi cần khóa lồng nhau.

??? question "Livelock khác deadlock thế nào?"
    Deadlock: các luồng **bị chặn** (đứng chờ), không tiến và không tốn CPU. Livelock: các luồng **vẫn chạy**, liên tục phản ứng với nhau (ví dụ cùng nhả khóa rồi thử lại, lặp mãi) nhưng không có việc nào tiến triển. Hai bên giống nhau ở kết quả: công việc không xong. Starvation là chuyện khác: một luồng cụ thể mãi không được tài nguyên trong khi hệ thống nói chung vẫn chạy.

??? question "Làm sao tìm deadlock trong chương trình đang chạy?"
    Chương trình treo thì gắn `gdb -p <pid>` vào (cần quyền; nếu hệ điều hành chặn thì chạy chương trình trong gdb rồi Ctrl+C), dùng `info threads` và `thread apply all bt` để xem mỗi luồng đứng ở đâu. Dấu hiệu: các luồng cùng đứng trong lời gọi `lock` của nhiều mutex khác nhau và mỗi mutex do một luồng khác trong nhóm giữ (đọc chủ sở hữu mutex bằng `print`). Từ trước khi treo, biên dịch bản thử với ThreadSanitizer: nó báo `lock-order-inversion (potential deadlock)` ngay khi thấy hai thứ tự khóa ngược nhau, kể cả lần chạy không treo.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Khóa hai mutex theo thứ tự tùy hứng"
    Hai chỗ khóa cùng cặp mutex theo hai thứ tự khác nhau là mầm deadlock, và nó hiếm nên dễ lọt qua thử nghiệm (mình bỏ dòng ngủ thì 40 lần chạy đều ổn). Dùng `std::scoped_lock`, hoặc quy ước một thứ tự duy nhất.

!!! warning "Lỗi 2: Gọi hàm lạ khi đang giữ khóa"
    Callback hay hàm của thư viện khác có thể xin lại đúng mutex của bạn (mình đã chạy: treo, mã 124) hoặc xin một mutex khác mà tạo ra vòng chờ. Lấy dữ liệu ra, nhả khóa, rồi mới gọi.

!!! warning "Lỗi 3: Tưởng `scoped_lock` cứu được mọi chuyện"
    Nó chỉ lo thứ tự giữa các mutex trong **một** lời gọi. Nếu hai mutex là một (`chuyen(a, a)`: hành vi không xác định, trên máy mình treo), hoặc nếu bạn vừa giữ mutex từ trước vừa xin thêm bằng lời gọi khác, vẫn có thể deadlock.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="26" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Điều nào mô tả đúng một deadlock giữa hai luồng?

- Mỗi luồng giữ một khóa và chờ đúng khóa mà luồng kia đang giữ
- Hai luồng cùng ghi một biến không khóa nên kết quả khác nhau mỗi lần
- Một luồng chạy vòng lặp vô hạn nên luồng kia không có CPU để chạy
- Một luồng luôn bị luồng khác giành khóa trước nên chờ lâu hơn bình thường

<p class="giai-thich" markdown>Deadlock cần một vòng chờ: mỗi bên đang giữ thứ bên kia cần và không bên nào chịu trả. Hai luồng cùng ghi không khóa là data race, một lỗi khác và không làm ai đứng chờ. Một luồng chiếm CPU chỉ làm luồng kia chậm, không tạo ra vòng chờ khóa. Còn luồng luôn thua trong việc giành khóa là starvation: hệ thống vẫn chạy, chỉ riêng luồng đó bị bỏ đói.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau. Hai luồng cùng cần cả `A` và `B`. Cách sửa nào làm hết deadlock mà hai luồng vẫn khóa cả hai mutex?

```text
// luồng 1:  std::lock_guard<std::mutex> g1(A);  std::lock_guard<std::mutex> g2(B);
// luồng 2:  std::lock_guard<std::mutex> g1(B);  std::lock_guard<std::mutex> g2(A);
```

- Cho luồng 2 ngủ một giây trước khi bắt đầu, để luồng 1 làm xong trước
- Đổi cả hai luồng sang `std::unique_lock`, vì nó nhả khóa linh hoạt hơn
- Cho luồng 2 cũng khóa `A` trước rồi mới khóa `B`, giống luồng 1
- Tăng độ ưu tiên của luồng 2 để nó giành được `A` trước luồng 1

<p class="giai-thich" markdown>Khi cả hai luồng cùng khóa `A` rồi `B`, không thể có luồng giữ `B` mà chờ `A`, nên hết vòng chờ. Cho luồng 2 ngủ chỉ đổi xác suất: nếu luồng 1 chậm hơn một giây thì vẫn có thể kẹt. `unique_lock` đổi cách bọc RAII chứ không đổi thứ tự khóa, nên vòng chờ vẫn còn. Độ ưu tiên cũng không bảo đảm ai giành được `A` trước, và vẫn không đổi thứ tự khóa của luồng 2.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đoạn sau. Luồng 1 gọi `chuyen(a, b)` và luồng 2 gọi `chuyen(b, a)` cùng lúc. Chuyện gì xảy ra?

```text
void chuyen(TaiKhoan& tu, TaiKhoan& den) {
    std::scoped_lock giu(tu.khoa, den.khoa);
    // trừ tiền người gửi, cộng tiền người nhận
}
```

- Vẫn có thể treo, vì hai luồng đưa hai mutex theo thứ tự ngược nhau
- Không treo, vì `scoped_lock` khóa nhiều mutex một lần theo cách tránh deadlock
- Không treo, vì `scoped_lock` luôn khóa theo thứ tự đối số nên luồng 2 chờ luồng 1 xong
- Không biên dịch được, vì `scoped_lock` chỉ nhận đúng một mutex

<p class="giai-thich" markdown>Chuẩn bảo đảm `scoped_lock` xin các mutex theo cách không gây deadlock, bất kể thứ tự bạn liệt kê, nên hai luồng không kẹt nhau. Nếu nó khóa đúng thứ tự đối số thì đoạn này sẽ treo y như hai `lock_guard` ngược nhau, nên cách giải thích đó mâu thuẫn với chính kết quả. Còn nói nó chỉ nhận một mutex là sai: nhận nhiều mutex chính là lý do nó tồn tại. Thứ tự đối số ngược nhau không phải vấn đề với `scoped_lock`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Quy ước "luôn khóa mutex có `id` nhỏ hơn trước" phá điều kiện nào trong bốn điều kiện của deadlock?

- Loại trừ lẫn nhau, vì hai luồng không còn phải dùng chung một mutex
- Giữ-và-chờ, vì luồng không còn giữ khóa này trong khi chờ khóa kia
- Không bị giành lại, vì khóa được trả về theo đúng thứ tự `id` nhỏ tới lớn
- Chờ vòng tròn, vì ai đang chờ ai thì cũng chỉ chờ mutex có `id` lớn hơn

<p class="giai-thich" markdown>Nếu mọi luồng chỉ xin mutex có `id` lớn hơn mutex đang giữ, thì chuỗi chờ luôn đi theo hướng `id` tăng dần và không thể khép thành vòng. Hai luồng vẫn dùng chung mutex và vẫn giữ khóa này trong lúc xin khóa kia, nên hai điều kiện đầu vẫn đúng. Còn khóa vẫn không bị ai giành lại giữa chừng; thứ tự `id` chỉ quy định thứ tự xin, không phải thứ tự trả.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Hai luồng cùng thấy khóa kia đang bị chiếm thì nhả khóa mình đang giữ rồi thử lại ngay, lặp mãi. Cả hai luồng liên tục chạy và dùng CPU, nhưng việc không bao giờ xong. Đây là gì?

- Livelock, vì luồng vẫn chạy và đổi trạng thái nhưng việc không tiến
- Deadlock, vì cả hai luồng đều không hoàn thành được công việc của mình
- Starvation, vì cả hai luồng đều không bao giờ giành được khóa nào
- Data race, vì hai luồng cùng truy cập khóa mà không có đồng bộ nào

<p class="giai-thich" markdown>Luồng vẫn chạy và phản ứng với nhau nhưng không tiến, đó là livelock. Trong deadlock các luồng bị chặn, đứng chờ chứ không chạy. Starvation là một luồng cụ thể mãi không được tài nguyên trong khi bên kia làm việc bình thường, còn ở đây cả hai cùng kẹt. Còn data race là truy cập ô nhớ không đồng bộ; ở đây vấn đề nằm ở cách hai luồng nhường nhau chứ không ở một ô nhớ chung.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. `main` chỉ có một luồng và gọi `duyet(ghi)`. Điều nào đúng?

```text
std::mutex m;
void duyet(void (*cb)()) { std::lock_guard<std::mutex> g(m); cb(); }
void ghi() { std::lock_guard<std::mutex> g(m); /* sửa dữ liệu chung */ }
```

- Chạy xong bình thường, vì cùng một luồng thì `std::mutex` cho xin lại
- Chuẩn bắt buộc `lock()` ném ngoại lệ để báo lỗi khi xin lại
- Không thể treo, vì deadlock luôn cần ít nhất hai luồng và hai khóa
- Hành vi không xác định, vì luồng xin lại `std::mutex` mình đang giữ

<p class="giai-thich" markdown>Chuẩn nói luồng xin lại một `std::mutex` mà nó đang giữ là hành vi không xác định; trên máy mình kết quả là treo. `std::mutex` không cho cùng luồng xin lại, đó là việc của `std::recursive_mutex`. Chuẩn cũng không bắt buộc ném ngoại lệ trong trường hợp này. Còn một luồng tự chờ chính mình vẫn là kẹt, nên "deadlock cần hai luồng" chỉ đúng với cách hiểu hẹp của ví dụ chuyển tiền.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Chương trình đang treo. Bạn chạy `thread apply all bt` trong gdb. Kết quả nào ủng hộ mạnh nhất nghi ngờ deadlock giữa hai luồng?

- Luồng chính đứng ở `join` để chờ một luồng phụ còn chưa chạy xong
- Hai luồng phụ đứng trong `lock` của hai mutex, mỗi mutex do luồng kia giữ
- Một luồng phụ đứng trong `lock`, còn luồng giữ mutex đó đang tính toán
- Một luồng phụ đứng ở `sleep_for` ngay trong hàm xử lý dữ liệu

<p class="giai-thich" markdown>Hai luồng cùng chờ lock, mỗi luồng chờ mutex mà luồng kia giữ, là một vòng chờ khép kín, nên đó là deadlock. Luồng chính ở `join` thì chương trình nào còn luồng phụ đang chạy cũng thế. Một luồng chờ lock trong khi người giữ vẫn đang tính toán chỉ là chờ lâu, người giữ sẽ trả khi xong. Còn luồng đứng ở `sleep_for` là luồng đang ngủ có hạn, không phải đang chờ khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Chương trình Go: hai goroutine khóa hai `sync.Mutex` ngược thứ tự và kẹt nhau, trong khi một goroutine khác vẫn chạy vòng lặp in một dòng mỗi 200 ms. Runtime Go làm gì với hai goroutine kẹt?

- In `all goroutines are asleep - deadlock!` rồi thoát, vì phát hiện chu trình hai mutex
- Tự nhả một mutex sau vài giây để cho hai goroutine tiếp tục chạy
- Không báo gì: nó chỉ báo khi mọi goroutine đều ngủ, nên hai goroutine kẹt im lặng
- Gây `panic` trong hai goroutine đó, vì `sync.Mutex` phát hiện khóa chéo

<p class="giai-thich" markdown>Runtime Go chỉ in thông báo deadlock khi mọi goroutine đều không thể chạy tiếp; còn goroutine nào đó sống thì hai goroutine kẹt nằm im, và mình đã chạy ra đúng như vậy. Runtime không phân tích chu trình giữa các mutex. Nó cũng không tự nhả khóa của ai. Còn `sync.Mutex` chỉ chờ, không có cơ chế phát hiện khóa chéo hay gây panic.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Deadlock**: các luồng chờ nhau theo vòng tròn, mỗi luồng giữ thứ luồng khác cần, nên không luồng nào chạy tiếp; ví dụ chuyển tiền `a → b` và `b → a` khóa ngược thứ tự: mình chạy ra treo, `timeout` mã 124. Nó hiếm và hên xui: bỏ dòng ngủ thì 40 lần chạy đều ổn.
2. **Bốn điều kiện** phải cùng đúng: loại trừ lẫn nhau, giữ-và-chờ, không bị giành lại, chờ vòng tròn; phá một điều kiện là hết deadlock.
3. **Tránh**: khóa theo thứ tự cố định (theo `id`), hoặc `std::scoped_lock` (C++17) / `std::lock` khóa nhiều mutex một lần; giữ khóa ngắn và không gọi hàm lạ (callback) khi giữ khóa; `try_lock_for` có hạn chờ; giảm khóa lồng nhau. Xin lại `std::mutex` đang giữ (tự deadlock) là hành vi không xác định, mình thấy treo; `recursive_mutex` chỉ che lỗi.
4. **Livelock**: luồng vẫn chạy mà không tiến việc; **starvation**: một luồng mãi không được tài nguyên. Tìm deadlock: gdb (`info threads`, `thread apply all bt`) thấy các luồng cùng đứng trong `lock`; TSan báo `lock-order-inversion (potential deadlock)` kể cả khi chưa treo.
5. Go chỉ báo `all goroutines are asleep - deadlock!` khi **mọi** goroutine đều ngủ; còn một goroutine khác sống thì hai goroutine kẹt im lặng (mình đã chạy Go 1.27.1); C++ không tự phát hiện cả hai trường hợp.
