# Bài 64 — Gỡ lỗi đa luồng thực chiến: TSan, helgrind, gdb và đo tranh chấp

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Có một **quy trình** năm bước cho lỗi đa luồng (tái hiện, bắt bằng công cụ, khoanh vùng, sửa, chứng minh) và biết chọn công cụ đầu tiên theo triệu chứng: sai thỉnh thoảng, treo, hay chậm.
    - Đọc từng phần của báo cáo ThreadSanitizer (hai truy cập, `size`, `mutexes:`, `Location`, hai luồng) cho `data race` và `lock-order-inversion`, và biết khi nào một báo cáo là **dương tính giả** (báo lỗi dù code đúng).
    - Tái hiện lỗi hiếm (Heisenbug) bằng cách chèn trễ vào cửa sổ nghi ngờ và chạy lặp; đọc luồng treo bằng `gdb` và `core` để phân biệt "chờ khóa" với "chờ tín hiệu"; dùng nhật ký có số thứ tự và id luồng.
    - Đo tranh chấp khóa bằng đếm `try_lock` thất bại, và dùng checklist 10 điểm khi review code đa luồng.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `sleep_for`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`, TSan chạy qua `setarch -R`, `timeout`), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, `scoped_lock`), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`wait` có predicate, lost wakeup), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (sanitizer), và ba bài công cụ [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md) (gdb, core), [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md) (TSan, Valgrind), [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) (strace, perf). Bài này **không dạy lại** các công cụ đó: nó dạy cách dùng chúng thành một quy trình.

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** nhiều đầu bếp của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Một hôm quản lý báo: "Thỉnh thoảng một món ra sai, cả tuần mới gặp một lần. Hôm khác cả bếp đứng im, ai cũng đứng chờ." Bạn là người được giao điều tra, và bạn không thể bảo bếp "cứ nấu lại cho sai đi".

Người điều tra giỏi không đoán. Bạn làm cho lỗi **xảy ra theo yêu cầu** (nấu thử hàng trăm lần, cố tình làm chậm một đầu bếp), lắp **camera** ghi ai chạm thớt (TSan), **chụp ảnh** cả bếp lúc đứng im để xem từng người đang chờ gì (gdb, core), và đếm **bao lần đầu bếp phải xếp hàng chờ thẻ** (đo tranh chấp). Sửa xong còn phải chứng minh bằng cách nấu thử lại thật nhiều lần.

!!! info "Chỗ nào ví von điều tra bếp không còn đúng?"
    Camera trong bếp thật không làm bếp chậm đi, còn TSan làm chương trình chậm nhiều lần và đổi cả lịch chạy của các luồng. Ngoài ra bếp thật dừng lại để bạn chụp ảnh mà không đổi gì, còn chương trình bị `gdb` dừng thì các luồng khác cũng dừng theo.

## 📖 Giải thích

### 1. Quy trình năm bước và chọn công cụ theo triệu chứng

Lỗi đa luồng khó vì nó **không tái hiện đều**. Vì thế bước đầu tiên không phải là sửa code mà là **làm cho lỗi hiện ra theo ý mình**. Năm bước:

| Bước | Việc | Câu hỏi tự hỏi |
|---|---|---|
| 1. Tái hiện | Có cách chạy mà lỗi hiện thường xuyên (lặp, chèn trễ) | "Lỗi hiện mấy phần trăm?" |
| 2. Bắt | Công cụ chỉ ra chỗ nghi: TSan, gdb, đo tranh chấp | "Công cụ nói gì, đọc đúng chưa?" |
| 3. Khoanh vùng | Thu hẹp tới đúng dữ liệu chung hay đúng khóa/điều kiện | "Ai chạm vào, lúc nào, giữ khóa nào?" |
| 4. Sửa | Một thay đổi có lý do, không phải thêm `sleep` | "Nó chặn đúng cơ chế lỗi chưa?" |
| 5. Chứng minh | Chạy lại đúng cách tái hiện cũ, cộng TSan sạch | "Cách làm lỗi hiện chắc chắn giờ hết lỗi chưa?" |

Công cụ đầu tiên chọn theo **triệu chứng**, không theo thói quen:

| Triệu chứng | Công cụ đầu tiên | Vì sao |
|---|---|---|
| Kết quả sai thỉnh thoảng, đổi theo lần chạy | TSan (mục 2) | Bắt hai truy cập không đồng bộ, dù lần này chưa sai |
| Chương trình treo | gdb `thread apply all bt` (mục 4) | Cho thấy mỗi luồng đang chờ cái gì |
| Thêm luồng mà không nhanh hơn | Đo tranh chấp (mục 6) | Là chuyện hiệu năng, không phải đúng sai |
| Sai mà TSan sạch | Nhật ký có số thứ tự (mục 5) | Có thể là race condition logic, không phải data race ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)) |

### 2. Đọc báo cáo ThreadSanitizer

Biên dịch với `-g -fsanitize=thread` rồi chạy qua `setarch x86_64 -R` ([Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md)). Ta thử trên một lỗi quen thuộc: lớp `ThongKe` có mutex, nhưng hàm đọc **quên khóa**. (Số dòng trong báo cáo tính khi bỏ dòng `// bo-qua-kiem-tra` ở đầu khối.)

```cpp
// bo-qua-kiem-tra
#include <algorithm>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>

struct ThongKe {
    std::mutex khoa;
    long long tong = 0;
    void cong(int x) {
        std::lock_guard<std::mutex> giu(khoa);          // (1) bên ghi có khóa
        tong += x;
    }
    long long doc() {
        return tong;                                    // (2) bên đọc quên khóa
    }
};

int main() {
    auto tk = std::make_unique<ThongKe>();
    std::thread ghi([&tk] {
        for (int i = 0; i < 1000; ++i) tk->cong(1);     // (3) luồng ghi
    });
    std::thread doc([&tk] {
        long long toiDa = 0;
        for (int i = 0; i < 1000; ++i) toiDa = std::max(toiDa, tk->doc());   // (4) luồng đọc
        (void)toiDa;
    });
    ghi.join();
    doc.join();
    std::cout << "tong = " << tk->tong << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Mỗi lần cộng đều xin `khoa`, nên các lần **ghi** xếp hàng đúng |
| (2) | `doc()` đọc `tong` không xin khóa: một bên ghi, một bên đọc, không đồng bộ |
| (3), (4) | Hai luồng chạy song song trên cùng một đối tượng `ThongKe` nằm trên heap |

**Kết quả khi chạy thường** (`-O2`, năm lần liền): cả năm lần in `tong = 1000`. Lỗi **ẩn**: chạy thường không thấy gì, và `(void)toiDa;` chỉ để trình biên dịch khỏi cảnh báo biến không dùng. Dưới TSan (biên dịch như trên, **không** thêm `-O`), báo cáo thật, mình bỏ các khung thư viện và đường dẫn (thoát mã 66):

```text
WARNING: ThreadSanitizer: data race (pid=…)
  Read of size 8 at 0x7b0c00000028 by thread T2:
    #0 ThongKe::doc() race.cpp:15
    #1 operator() race.cpp:26

  Previous write of size 8 at 0x7b0c00000028 by thread T1 (mutexes: write M11):
    #0 ThongKe::cong(int) race.cpp:12
    #1 operator() race.cpp:22

  Location is heap block of size 48 at 0x7b0c00000000 allocated by main thread:

SUMMARY: ThreadSanitizer: data race race.cpp:15 in ThongKe::doc()
tong = 1000
```

Đọc theo thứ tự này, mỗi bước một câu hỏi:

| Phần của báo cáo | Cho bạn biết | Ở đây |
|---|---|---|
| `Read/Write of size N ... by thread T` | Hai truy cập xung đột và kích thước ô nhớ | Đọc 8 byte ở `doc()`, ghi 8 byte ở `cong()`: một `long long` |
| `(mutexes: write M11)` | Mutex mà luồng đó **đang giữ** lúc truy cập | Bên ghi giữ `M11`, bên đọc **không có** dòng này: bên đọc quên khóa |
| `Location is ...` | Dữ liệu nào bị đụng (global, stack, heap) và ai cấp phát | Khối heap 48 byte do `main` tạo: đối tượng `ThongKe` |
| `Mutex M11 created at`, `Thread T created by` | Mutex là cái nào; luồng được tạo ở dòng nào | `M11` là `khoa` của `ThongKe`; hai dòng tạo luồng |

Một bẫy: mình thử biên dịch thêm `-O1` hay `-O2` thì TSan **im lặng** (ba lần chạy, không báo gì), còn đổi `(void)toiDa;` thành `std::cerr << toiDa;` thì báo lại. Nhiều khả năng trình biên dịch bỏ luôn các lần đọc vì kết quả không ai dùng, nên khi săn race đừng để phép đọc cần kiểm bị tối ưu mất.

Điểm quan trọng nhất là dòng `(mutexes: ...)`: **bên không có mutex chung là bên cần sửa**. Sửa bằng cách thêm `std::lock_guard<std::mutex> giu(khoa);` vào đầu `doc()`, rồi chạy lại: không còn báo cáo, thoát mã 0 (mình đã chạy).

**Thử thay đổi: bỏ luôn khóa ở `cong()`.** Mình đã chạy: vẫn `data race` ở dòng 15, nhưng **cả hai** truy cập không còn dòng `(mutexes: ...)`: dấu hiệu "không ai khóa gì cả", khác với "một bên quên".

**Báo cáo thứ hai: `lock-order-inversion`** ([Bài 26](../nhom-3-da-luong/26-deadlock.md), [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md) đã cho ví dụ đầy đủ). Mình dùng lại ý đó với hai hàm: `ab()` khóa `khoaA` ở dòng 8 rồi `khoaB` ở dòng 9, `ba()` khóa `khoaB` ở dòng 13 rồi `khoaA` ở dòng 14, và `main` chạy chúng **lần lượt** (nên không treo). Mặc định TSan chỉ nêu dòng khóa **thứ hai** của mỗi hàm và gợi ý `TSAN_OPTIONS=second_deadlock_stack=1` để thấy cả dòng khóa thứ nhất. Mình chạy với tùy chọn đó, báo cáo thật rút gọn (thoát mã 66):

```text
WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=…)
  Cycle in lock order graph: M9 (0x…) => M10 (0x…) => M9

  Mutex M10 acquired here while holding mutex M9 in thread T1:
    #4 ab() order.cpp:9
  Mutex M9 previously acquired by the same thread here:
    #4 ab() order.cpp:8

  Mutex M9 acquired here while holding mutex M10 in thread T2:
    #4 ba() order.cpp:14
  Mutex M10 previously acquired by the same thread here:
    #4 ba() order.cpp:13
```

Đọc: `M9 => M10 => M9` là chu trình. T1 giữ `M9` (dòng 8) rồi xin `M10` (dòng 9); T2 giữ `M10` (dòng 13) rồi xin `M9` (dòng 14). Bốn dòng đó đủ để biết sửa chỗ nào: thống nhất thứ tự khóa hoặc dùng `std::scoped_lock`.

**Helgrind và DRD (Valgrind).** `valgrind --tool=helgrind ./prog` và `valgrind --tool=drd ./prog` là hai công cụ khác của Valgrind bắt data race và đảo thứ tự khóa; ưu điểm là chạy trên **tệp đã biên dịch sẵn**, không cần biên dịch lại. Mình kiểm tra bằng `which valgrind`: **máy này không có Valgrind, nên không chạy ở đây** và mình không dán báo cáo nào. Nếu bạn chạy, tên mục cần tìm là `Possible data race` và `Lock order violated` (theo [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md)); đọc cách tương tự: hai truy cập, hai ngăn xếp, khóa nào đang giữ.

### 3. Tái hiện lỗi hiếm: làm cho lỗi hiện theo ý mình

**Heisenbug** là lỗi biến mất hoặc đổi dạng khi bạn quan sát nó (thêm log, chạy dưới công cụ), vì các luồng chỉ cần lệch vài micro-giây là đường chạy đổi. Lỗi nằm ở một **cửa sổ** hẹp: khoảng thời gian giữa hai việc mà luồng khác có thể chen vào. Muốn tái hiện, ta **mở rộng cửa sổ** thay vì chờ may.

Ví dụ: luồng thợ chờ `main` báo tin bằng `condition_variable` ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)), nhưng `wait` **không kèm điều kiện**. Nếu `main` báo trước khi thợ kịp vào `wait`, tin bị mất và thợ ngủ mãi (lost wakeup). Chương trình nhận số micro-giây chèn trễ ở dòng lệnh: `main(int argc, char** argv)` cho `argc` là số phần tử gõ trên dòng lệnh (kể cả tên chương trình) và `argv[1]` là phần tử thứ hai dạng chuỗi, còn `std::atoi` đổi chuỗi đó thành số.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable chuong;
int treUs = 0;                                                    // số micro-giây chèn thử, lấy từ dòng lệnh

void tho() {
    std::this_thread::sleep_for(std::chrono::microseconds(treUs));   // (1) chèn thử: mở rộng cửa sổ
    std::unique_lock<std::mutex> lk(khoa);
    chuong.wait(lk);                                                 // (2) SAI: không kiểm điều kiện
    std::cout << "tho nhan duoc tin\n";
}

int main(int argc, char** argv) {
    if (argc > 1) treUs = std::atoi(argv[1]);
    std::thread t(tho);
    std::this_thread::sleep_for(std::chrono::microseconds(100));     // (3) main "chuẩn bị"
    chuong.notify_one();                                             // (4) báo, có thể trước khi thợ kịp chờ
    t.join();
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (3) | `main` mất cỡ 100 micro-giây chuẩn bị, thường đủ để thợ vào `wait` trước |
| (4) | `main` báo; nếu thợ chưa chờ thì tin rơi vào khoảng không |
| (1) | Dòng chèn thử: thợ ngủ thêm `treUs` micro-giây trước khi xin khóa, làm "thợ tới muộn" xảy ra chắc chắn |
| (2) | Thợ vào `wait` sau khi tin đã bay mất: ngủ mãi, `join` ở `main` chờ mãi |

Chạy lặp bằng vòng `for` của shell, mỗi lần có `timeout 1` giết sau 1 giây (mã thoát 124, [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)), đếm số lần treo:

```text
n=0; for i in $(seq 1 300); do timeout 1 ./treo_cv 0 > /dev/null; [ $? -eq 124 ] && n=$((n+1)); done; echo "treo $n/300"
```

**Kết quả thật** (một lần chạy mỗi dòng, đổi theo máy và theo lần): không chèn trễ, 300 lần chỉ treo **1** lần; chèn trễ 5000 micro-giây (`./treo_cv 5000`), 20 lần treo **19** lần. Chèn trễ đã **xác nhận cửa sổ** nằm giữa lúc thợ khởi động và lúc thợ vào `wait`.

!!! warning "Chèn trễ là để tái hiện, không phải để sửa"
    `sleep` chỉ đổi xác suất, không tạo thứ tự đồng bộ nào. Sau khi xác nhận cửa sổ, bạn **xóa** dòng chèn trễ và sửa bằng cơ chế đúng. Ca "chờ đủ lâu thì luồng kia chắc xong" đã bị TSan vạch mặt ở [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md).

Các kỹ thuật tái hiện, xếp theo tác dụng:

| Kỹ thuật | Làm gì | Khi nào hợp |
|---|---|---|
| Chạy lặp N lần (trong chương trình hoặc vòng `for` của shell) | Biến xác suất nhỏ thành chắc chắn gặp | Luôn là bước đầu |
| Chèn `sleep_for` hay `this_thread::yield()` vào cửa sổ nghi ngờ | Mở rộng cửa sổ, ép thứ tự xấu | Khi đã nghi một chỗ cụ thể |
| Chạy dưới TSan | Bắt race **kể cả khi chưa sai** | Lỗi sai dữ liệu; mục 2 |

### 4. Chương trình treo: gdb và core, phân biệt "chờ khóa" với "chờ tín hiệu"

Cách gắn `gdb` và đọc deadlock hai mutex đã dạy kỹ ở [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md) (`info threads`, `thread apply all bt`, `print mutex` với trường `__owner`). Ở đây ta dùng chúng cho một ca **không phải** deadlock: chương trình `treo_cv` ở mục 3 với `./treo_cv 5000`, chạy trong gdb, gửi `SIGINT` sau 2 giây (máy này chặn `gdb -p`, [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)), rồi lưu `core` bằng `generate-core-file` (tên khác của `gcore`). Báo cáo thật, rút gọn (số dòng `treo_cv.cpp:15` và `:24` tính khi bỏ dòng chú thích đầu tệp):

```text
Thread 2 (... "treo_cv"):
#4  ___pthread_cond_wait (cond=0x... <chuong>, mutex=0x... <khoa>) at ./nptl/pthread_cond_wait.c:627
#5  0x... in tho () at treo_cv.cpp:15
Thread 1 (... "treo_cv"):
#4  0x... in std::thread::join() () from /lib/x86_64-linux-gnu/libstdc++.so.6
#5  0x... in main (argc=2, ...) at treo_cv.cpp:24
```

Luồng 1 (`main`) đứng ở `join`, chờ luồng 2. Luồng 2 đứng trong `pthread_cond_wait` do `tho()` dòng 15 gọi. Khác với deadlock ở Bài 40 (luồng đứng trong `pthread_mutex_lock`), đây là **chờ tín hiệu**.

Câu hỏi tiếp theo là "ai giữ mutex `khoa`?". Mở `core` bằng `gdb ./treo_cv treo_cv.core`, chọn `thread 2`, `frame 5`, rồi `print khoa._M_mutex.__data.__owner`: mình được `$1 = 0` (và `__lock` cũng `0`), nghĩa là **không luồng nào đang giữ `khoa`**. Tên trường là chi tiết glibc trên máy mình, không phải chuẩn.

Đây là mấu chốt để phân loại luồng treo:

| Luồng đứng ở | Nó chờ gì | Hỏi gì tiếp | Nghi ngờ |
|---|---|---|---|
| `pthread_mutex_lock` | Một khóa | `__owner` là luồng nào? Luồng đó chờ gì? | Vòng tròn hai khóa: deadlock ([Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)); chủ khóa ngủ lâu khi giữ khóa |
| `pthread_cond_wait` | Tín hiệu | Điều kiện đã đúng chưa? `notify` đã bay trước? | Lost wakeup, quên `notify`, điều kiện không bao giờ đúng |
| `pthread_join` | Một luồng kết thúc | Luồng kia đang đứng ở đâu? | Chuỗi chờ nhau: lần theo luồng kia |
| `read`, `poll`, `epoll_wait` | Dữ liệu từ ngoài | Phía bên kia có gửi không? | Chờ mạng/tệp, không phải lỗi luồng; xem `strace` ([Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)) |

Treo **trên máy khách hàng** thì xin tệp `core` và mở lại nơi khác. Nhưng `core` chỉ chụp trạng thái cuối, không cho biết **vì sao** `notify` đến sớm: phần đó cần nhật ký ở mục 5.

### 5. Nhật ký theo thread id: thứ tự các sự kiện

Khi nghi vấn là **thứ tự** (ai tới trước), `printf` rải rác không đủ: dòng in của hai luồng lẫn lộn, thứ tự in không bảo đảm đúng thứ tự xảy ra. Cách tốt hơn: mỗi sự kiện ghi vào **một nhật ký chung có thứ tự thêm vào** (thêm trong khóa), kèm `std::this_thread::get_id()` (số định danh của luồng đang chạy, kiểu `std::thread::id`), và **in một lần sau `join`**.

`thread::id` in ra là một số dài vô nghĩa, đổi theo lần chạy (mình chạy hai lần: `130057191314368` rồi `129946211869632` cho luồng chính), nên ta **đánh số lại** theo thứ tự xuất hiện thành `luong0`, `luong1`. Ví dụ dưới là chính lỗi lost wakeup, có chèn trễ 5 ms và `wait_for` hết giờ để chương trình không treo.

```cpp
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

struct NhatKy {                                    // (1) nhật ký chung: thêm dòng trong khóa
    std::mutex khoa;
    std::vector<std::string> viec;
    std::vector<std::thread::id> ai;
    void ghi(const std::string& s) {
        std::lock_guard<std::mutex> giu(khoa);
        viec.push_back(s);
        ai.push_back(std::this_thread::get_id());  // (2) ghi luôn "luồng nào" gọi
    }
};
int main() {
    NhatKy nk;
    std::mutex khoaCho;
    std::condition_variable chuong;
    std::thread tho([&] {
        std::this_thread::sleep_for(std::chrono::milliseconds(5));   // (3) chèn trễ: cửa sổ nghi ngờ
        std::unique_lock<std::mutex> lk(khoaCho);
        nk.ghi("tho: vao cho");
        if (chuong.wait_for(lk, std::chrono::milliseconds(20)) == std::cv_status::timeout) {
            nk.ghi("tho: het gio");                // (4) SAI: chờ không kèm điều kiện
        }
    });
    std::this_thread::sleep_for(std::chrono::microseconds(100));
    nk.ghi("main: notify");
    chuong.notify_one();
    tho.join();
    std::vector<std::thread::id> daThay;           // (5) đánh số lại id dài thành luong0, luong1...
    for (std::size_t i = 0; i < nk.viec.size(); ++i) {
        std::size_t k = 0;
        while (k < daThay.size() && daThay[k] != nk.ai[i]) ++k;
        if (k == daThay.size()) daThay.push_back(nk.ai[i]);
        std::cout << "#" << i << " luong" << k << " " << nk.viec[i] << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (3) | Thợ ngủ 5 ms; `main` chỉ chuẩn bị 100 micro-giây, nên `main` tới trước |
| (1), (2) | Mỗi `ghi` khóa nhật ký, thêm nội dung và id luồng đang gọi vào hai vector song song |
| (4) | Thợ vào `wait_for` sau khi tin đã bay; `wait_for` không kèm vị từ trả `std::cv_status::timeout` khi hết 20 ms (hoặc `no_timeout` nếu được đánh thức), nên thợ ghi "het gio" |
| (5) | Sau `join` (chỉ còn một luồng), duyệt nhật ký, gán số cho mỗi `thread::id` lần đầu gặp |

**Kết quả khi chạy** (bốn lần liền đều như nhau; TSan sạch):

```text
#0 luong0 main: notify
#1 luong1 tho: vao cho
#2 luong1 tho: het gio
```

Nhật ký **chứng minh thứ tự**: `main: notify` (#0) đến trước `tho: vao cho` (#1). Chuỗi thứ tự này chính là cơ chế lỗi. Ta tự chèn trễ nên kết quả tất định; ở lỗi thật bạn đọc xem thứ tự có khớp giả thuyết không.

!!! warning "Ghi nhật ký cũng làm đổi lịch chạy"
    Nhật ký trên khóa một mutex, và `std::cout` thường đi qua khóa nội bộ hay lệnh hệ thống. Hai thứ đó đồng bộ ngầm các luồng và có thể **che** lỗi. Với lỗi cực nhạy thì dùng nhật ký nhẹ nhất có thể (ghi vào mảng đã cấp sẵn qua chỉ số `atomic`, in sau cùng) và nhớ rằng "thêm log là hết lỗi" **không** có nghĩa đã sửa.

### 6. Đo tranh chấp khóa

Có luồng chạy đúng nhưng **chậm**: nghi **tranh chấp khóa** (nhiều luồng cùng cần một mutex, nên phải xếp hàng). Với mutex, `try_lock()` thử xin khóa và trả `true` nếu được ngay, `false` nếu khóa đang bận, **không chờ** (chuẩn cho phép nó thất bại giả dù khóa rảnh, nhưng ở đây một luồng đo ra đúng 0). Đếm số lần `false` là một cách đo rẻ và trực tiếp: lần nào thất bại là lần luồng sẽ phải đứng chờ.

Công cụ chuyên dụng là `perf` ([Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)). Máy này có cài `perf` nhưng không dùng được: `perf stat ./prog` báo `Access to performance monitoring and observability operations is limited` kèm `perf_event_paranoid setting is 4`, và hạ cài đặt này cần quyền quản trị, việc đụng hệ thống mà mình không làm. Vì vậy **mình chưa chạy `perf` ở bài này**; cách đếm `try_lock` thì chạy ở mọi nơi, ở phần ví dụ ngay dưới.

## 💻 Ví dụ code

### Ví dụ 1: sửa lost wakeup và chứng minh bằng cách làm lỗi hiện chắc chắn

Sửa đúng cơ chế: điều kiện thật nằm trong một biến `sanSang`, `main` đổi nó **trong khóa**, thợ dùng `wait` có predicate ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)). Nếu `main` đã báo trước, predicate đã đúng và thợ không ngủ.

```cpp
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable chuong;
bool sanSang = false;                                             // (1) điều kiện thật nằm trong biến
int treUs = 0;
void tho() {
    std::this_thread::sleep_for(std::chrono::microseconds(treUs));
    std::unique_lock<std::mutex> lk(khoa);
    chuong.wait(lk, [] { return sanSang; });                      // (2) kiểm biến trước, rồi mới ngủ
    std::cout << "tho nhan duoc tin\n";
}
int main(int argc, char** argv) {
    if (argc > 1) treUs = std::atoi(argv[1]);
    std::thread t(tho);
    std::this_thread::sleep_for(std::chrono::microseconds(100));
    {
        std::lock_guard<std::mutex> giu(khoa);
        sanSang = true;                                           // (3) đổi điều kiện TRONG khóa
    }
    chuong.notify_one();
    t.join();
    std::cout << "xong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (3) | `main` đặt `sanSang = true` rồi nhả khóa, sau đó `notify` |
| (2) | Nếu thợ vào sau: predicate thấy `true`, không ngủ. Nếu thợ vào trước: ngủ, rồi `notify` đánh thức |
| (1) | Tin không còn là "sự kiện bay qua" mà là trạng thái nằm lại trong biến |

**Kết quả khi chạy** (không tham số, và `./cv_dung 5000`; TSan sạch ở cả hai):

```text
tho nhan duoc tin
xong
```

**Chứng minh**: chạy đúng cách làm lỗi hiện chắc chắn, không phải chạy thường. Với bản sai, chèn trễ 5000 cho 19/20 lần treo. Với bản sửa (biên dịch thành `cv_dung`) mình chạy đúng vòng ở mục 3: `./cv_dung 0` 300 lần ra **0** lần treo, và `./cv_dung 5000` 300 lần cũng **0** lần treo. Bằng chứng này mạnh hơn "chạy 1000 lần thường không thấy", vì lần này ta đã ép cửa sổ xấu nhất xảy ra.

!!! warning "Một báo cáo TSan sai: `double lock of a mutex` ở `wait_for` với predicate"
    Mình thử đổi dòng (2) của bản sửa (biên dịch thành `cv_wf`) thành `chuong.wait_for(lk, std::chrono::milliseconds(20), [] { return sanSang; });` (để có hạn chờ). Code vẫn **đúng**, nhưng chạy `./cv_wf 0` (không chèn trễ, nên `main` xin khóa lúc thợ đang ở trong `wait_for`) thì TSan (g++ 11) báo `WARNING: ThreadSanitizer: double lock of a mutex` rồi `data race` ở dòng `sanSang = true`, thoát mã 66; mình chạy ba lần đều vậy, còn `./cv_wf 5000` (không ai xin khóa lúc thợ đang chờ) thì sạch.

    Đây là **dương tính giả** (code đúng): mutex không bị khóa hai lần, vì `wait_for` nhả khóa khi ngủ.

    **Hiện tượng đã quan sát:** `wait_for` với `steady_clock` biên dịch ra lời gọi `pthread_cond_clockwait` (`nm -D` trên tệp thực thi: `U pthread_cond_clockwait`), và `nm -D` trên `libtsan` của g++ 11 liệt kê hàm bọc cho `pthread_cond_wait` và `pthread_cond_timedwait` nhưng không có cho `clockwait`.

    **Nguyên nhân là phỏng đoán của mình** (không đọc mã nguồn `libtsan`): vì không bọc hàm này nên TSan không thấy `wait_for` nhả khóa lúc ngủ, và coi lần xin khóa của `main` là khóa hai lần. Phỏng đoán khớp với hai phép thử khác: `wait_until` với `system_clock` (dùng `timedwait`) thì sạch, còn `wait_until` với `steady_clock` cũng báo như `wait_for`. Mình **không** khuyên đổi sang `system_clock` trong code thật vì nó nhảy theo giờ hệ thống.

    Bài học: **báo cáo công cụ phải được đối chiếu với code**. Hỏi "mutex này có thật bị khóa hai lần không?" trước khi sửa thứ đã đúng.

### Ví dụ 2: đo tranh chấp bằng `try_lock` và giảm nó

Mỗi luồng cộng vào một biến chung dưới một mutex. Hàm `thatBai` trả số lần `try_lock` thất bại của cả nhóm. Tham số `lo` là số đơn vị cộng mỗi lần xin khóa: `lo = 1` là xin khóa cho từng đơn vị, `lo = 1000` là gom 1000 đơn vị cho một lần xin.

```cpp
#include <atomic>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

std::mutex khoa;
long long tong = 0;
long long thatBai(int soLuong, int soLan, int lo) {
    std::atomic<long long> dem{0};
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < soLuong; ++k) {
        cacLuong.emplace_back([&dem, soLan, lo] {
            long long cucBo = 0;                          // (1) đếm riêng, không dùng chung
            for (int i = 0; i < soLan; i += lo) {
                if (khoa.try_lock()) {                    // (2) thử, không chờ
                    tong += lo;
                    khoa.unlock();
                } else {
                    ++cucBo;                              // (3) ghi nhận một lần tranh chấp
                    std::lock_guard<std::mutex> giu(khoa);
                    tong += lo;                           // rồi vẫn phải chờ khóa để làm việc
                }
            }
            dem += cucBo;                                 // (4) gộp một lần cuối luồng
        });
    }
    for (std::thread& t : cacLuong) t.join();
    return dem.load();
}
int main() {
    long long mot = thatBai(1, 200000, 1);
    long long tam = thatBai(8, 200000, 1);
    long long tamLo = thatBai(8, 200000, 1000);
    std::cout << "1 luong: that bai " << mot << "\n";
    std::cout << "8 luong, khoa moi lan: that bai nhieu hon 0? " << (tam > 0) << "\n";
    std::cout << "8 luong, khoa moi 1000 lan: it hon ban tren? " << (tamLo < tam) << "\n";
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (2) | Xin được ngay thì cộng và nhả; không tốn lần chờ |
| (3) | Khóa bận: ghi một lần tranh chấp vào biến **riêng của luồng** (không đụng biến chung), rồi vẫn chờ khóa để cộng |
| (4) | Mỗi luồng gộp số đếm riêng vào `dem` đúng một lần cuối cùng |

**Kết quả khi chạy** (bốn lần liền đều như nhau; TSan sạch; `-O2`):

```text
1 luong: that bai 0
8 luong, khoa moi lan: that bai nhieu hon 0? 1
8 luong, khoa moi 1000 lan: it hon ban tren? 1
tong = 3400000
```

Một luồng thì không thể tranh chấp với ai: đúng **0**. Con số thô (in ra `std::cerr` khi mình chạy ba lần, đổi theo máy và theo lần): với 8 luồng khóa từng đơn vị, thất bại **408982, 474599 và 417278** lần trong **1,6 triệu** lần xin (cỡ một phần tư); khi gom 1000 đơn vị mỗi lần xin thì chỉ có 1600 lần xin và thất bại **0**. Giảm số lần xin khóa (hoặc thời gian giữ) là cách giảm tranh chấp cơ bản ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md), thêm chia shard ở [Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md)).

Thất bại 0 ở bản gom một phần vì lần chạy ngắn, các luồng ít chồng lên nhau; đừng đọc nó thành "luôn bằng 0". Ngoài ra `/usr/bin/time -v ./prog` có dòng `Voluntary context switches` (số lần luồng tự ngủ, thường vì chờ khóa): mình đo bản trên được 22589, một con số đơn lẻ, chỉ có ý nghĩa khi so với bản sau khi sửa.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Chương trình thỉnh thoảng treo. Bạn làm gì?"
    Trước tiên làm cho nó treo theo ý mình: chạy lặp vài trăm lần với `timeout`, và chèn trễ vào chỗ nghi để tăng xác suất. Khi có một lần treo thì dừng nó trong gdb (hoặc lấy `core`), gõ `thread apply all bt` và xem từng luồng đứng ở đâu: `pthread_mutex_lock` nghĩa là chờ khóa (đọc `__owner`, lần theo xem có vòng tròn không), `pthread_cond_wait` nghĩa là chờ tín hiệu (nghi lost wakeup hay quên notify), `join` nghĩa là chờ luồng khác. Sau đó sửa đúng cơ chế, rồi chạy lại đúng cách làm lỗi hiện chắc chắn để chứng minh.

??? question "Lỗi chỉ xảy ra một lần trên một nghìn lần chạy. Làm sao tái hiện?"
    Mở rộng cửa sổ chạy đua: tìm khoảng giữa hai việc mà luồng khác có thể chen vào, chèn `sleep_for` hay `yield` vào đó (chỉ để thử), cộng với chạy lặp hàng trăm lần. Mình làm đúng vậy ở mục 3: 1/300 trở thành 19/20. Khi đã có cách tái hiện chắc, tìm nguyên nhân, xóa dòng chèn trễ và sửa bằng đồng bộ thật.

??? question "Thế nếu production không cho build lại bằng TSan thì sao?"
    Có vài đường. Lấy `core` của tiến trình đã treo hay sập để mở lại nơi khác. Dùng Helgrind/DRD của Valgrind vì chúng chạy trên tệp đã biên dịch (kèm `-g` cho số dòng; mình không có Valgrind ở đây nên chưa chạy). Thêm nhật ký có số thứ tự và id luồng (mục 5). Rồi tái hiện ở môi trường test bằng bản biên dịch có TSan, vì TSan chậm nhiều lần nên ít khi chạy được trên môi trường thật.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Sửa bằng `sleep`"
    Thêm `sleep_for` vào để "cho luồng kia kịp xong" chỉ giảm xác suất lỗi, không tạo thứ tự đồng bộ nào; TSan còn ghi thẳng `As if synchronized via sleep` ([Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md)). Dùng `join`, `wait` có predicate hay `future`.

!!! warning "Lỗi 2: Coi mỗi báo cáo công cụ là chân lý, hoặc phớt lờ nó vì từng thấy báo giả"
    Hai thái cực đều sai. Mỗi báo cáo phải khớp với code: dòng `(mutexes: ...)`, hai ngăn xếp, dữ liệu bị đụng. Nếu không khớp (như `double lock` ở `wait_for` bên trên), tìm giới hạn của công cụ trước khi sửa code đã đúng.

### Checklist 10 điểm khi review code đa luồng

| # | Câu hỏi khi đọc code | Bài gốc |
|---|---|---|
| 1 | Mỗi dữ liệu chung có đúng một mutex bảo vệ, ghi chú rõ không? | [25](../nhom-3-da-luong/25-data-race-mutex.md) |
| 2 | **Mọi** đường truy cập (đọc, ghi, getter, hàm hủy) có xin cùng khóa đó không? | [25](../nhom-3-da-luong/25-data-race-mutex.md) |
| 3 | Có trả tham chiếu hay con trỏ ra khỏi vùng khóa không? | [25](../nhom-3-da-luong/25-data-race-mutex.md) |
| 4 | Có gọi callback, I/O, `sleep` hay hàm lạ khi đang giữ khóa không? | [25](../nhom-3-da-luong/25-data-race-mutex.md), [26](../nhom-3-da-luong/26-deadlock.md) |
| 5 | Nhiều mutex: thứ tự cố định hay `scoped_lock`? | [26](../nhom-3-da-luong/26-deadlock.md) |
| 6 | Mỗi `wait` có predicate, điều kiện đổi **trong khóa**? | [27](../nhom-3-da-luong/27-condition-variable.md) |
| 7 | `atomic` chỉ dùng cho biến độc lập? Bất biến nhiều biến có nằm trong một mutex? | [28](../nhom-3-da-luong/28-atomic.md) |
| 8 | Mọi luồng đều `join` (hay `detach` có chủ đích); không giữ tham chiếu tới biến cục bộ đã chết; ngoại lệ trong luồng có chỗ bắt? | [24](../nhom-3-da-luong/24-thread-co-ban.md) |
| 9 | Dừng êm: cờ dừng `atomic` và đánh thức luồng đang ngủ trong `wait`? | [27](../nhom-3-da-luong/27-condition-variable.md), [30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) |
| 10 | Có test lặp N lần và TSan trong kiểm thử; không dùng `sleep` làm đồng bộ? | bài này |

!!! info "Bạn biết Go?"
    `go test -race -count=100` chạy bộ test 100 lần dưới bộ phát hiện data race (xây trên ThreadSanitizer, [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md)): ứng với "chạy lặp cộng TSan" ở mục 3. Chương trình Go treo thì gửi `SIGQUIT` để runtime in stack mọi goroutine, thay cho `thread apply all bt` ([Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)); `-mutexprofile` của `go test` đo tranh chấp mutex, thay cho đếm `try_lock`. Mình không chạy Go ở bài này, nên đây là kiến thức công cụ, không phải đầu ra đã chạy.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="64" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Một chương trình thỉnh thoảng treo (mình thấy cỡ 1 trong 300 lần chạy). Việc **đầu tiên** hợp lý nhất là gì?

- Thêm `sleep_for` 100 ms vào đầu mỗi luồng để chúng chạy tuần tự hơn
- Chạy lặp nhiều lần và chèn trễ vào chỗ nghi để lỗi hiện thường xuyên
- Chạy TSan đúng một lần và kết luận không có lỗi luồng nếu nó không báo gì
- Tăng thời hạn `timeout` của hệ thống lên để chương trình có thêm thời gian chạy

<p class="giai-thich" markdown>Lỗi hiếm cần một cách làm nó hiện theo ý mình trước khi sửa hay chứng minh được gì: chạy lặp và mở rộng cửa sổ chạy đua. Thêm `sleep` chỉ đổi xác suất chứ không tạo đồng bộ, nên là cách "sửa" sai. Một lần TSan sạch không chứng minh gì vì nó chỉ thấy các truy cập đã xảy ra trong lần đó. Kéo dài `timeout` chỉ che triệu chứng, chương trình đã treo vẫn không chạy tiếp.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn báo cáo TSan sau (rút gọn). Nên sửa ở đâu?

```text
Read of size 8 by thread T2:
    #0 ThongKe::doc() race.cpp:15
Previous write of size 8 by thread T1 (mutexes: write M11):
    #0 ThongKe::cong(int) race.cpp:12
```

- Bỏ khóa trong `cong()` để cả hai bên cùng không khóa cho giống nhau
- Thêm `sleep_for` vào `cong()` để luồng ghi chạy xong trước luồng đọc
- Chỉ tăng kích thước biến `tong` lên để việc ghi trở nên nguyên tử hơn
- Khóa cùng mutex `M11` trong `doc()`, vì bên đọc không giữ mutex nào

<p class="giai-thich" markdown>Dòng `(mutexes: write M11)` cho thấy bên ghi giữ `M11`, còn bên đọc không có dòng đó, nên bên cần sửa là `doc()`: phải xin cùng mutex. Bỏ khóa trong `cong()` làm cả hai bên không đồng bộ, tức là tệ hơn. `sleep_for` không tạo thứ tự đồng bộ nào. Kích thước biến không biến phép đọc và ghi từ hai luồng thành nguyên tử.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Một chương trình treo. Trong `core`, luồng phụ đứng ở `pthread_cond_wait`, `main` đứng ở `pthread_join`, và `print khoa._M_mutex.__data.__owner` ra `0`. Kết luận hợp lý nhất?

- Không ai giữ `khoa`; luồng phụ chờ một tín hiệu, nghi lost wakeup
- Deadlock hai mutex, vì hai luồng cùng đứng trong hàm của `pthread`
- Luồng phụ đang giữ `khoa` và không chịu nhả, nên `main` bị chặn
- `main` đã chết nên luồng phụ không còn ai báo, cần chạy lại chương trình

<p class="giai-thich" markdown>`pthread_cond_wait` là chờ tín hiệu, và `__owner` bằng 0 nghĩa là không ai giữ `khoa`; deadlock thật thì luồng phải đứng ở `pthread_mutex_lock` và `__owner` trỏ tới luồng kia. Cả hai luồng đứng trong hàm `pthread` chưa đủ kết luận deadlock vì mỗi hàm chờ một thứ khác nhau. Luồng đang chờ trong `wait` thì đã nhả khóa. `main` đứng ở `join` nghĩa là còn sống và đang chờ luồng phụ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Chương trình đếm bằng một mutex, 1 luồng thì nhanh nhưng 8 luồng lại chậm hơn. Bạn nghi tranh chấp khóa. Cách đo trực tiếp rẻ nhất là gì?

- Chạy TSan vì nó đo thời gian chờ của từng mutex trong chương trình
- Đo thời gian `join`, vì `join` lâu nghĩa là khóa đang bị tranh chấp
- Đếm số lần `try_lock` thất bại rồi gộp lại, so 1 luồng với 8 luồng
- Tăng số luồng lên 64 rồi xem chương trình có sập hay không

<p class="giai-thich" markdown>Mỗi lần `try_lock` thất bại là một lần luồng sẽ phải đứng chờ khóa, nên đếm nó đo đúng tranh chấp; so với 1 luồng (luôn 0) thấy rõ mức tăng. TSan tìm lỗi đúng sai, không đo hiệu năng và còn làm chương trình chậm. Thời gian `join` gộp mọi lý do chậm (tính toán, I/O, chờ khóa) nên không nói riêng về khóa. Tăng lên 64 luồng chỉ làm tranh chấp nhiều hơn chứ không đo gì.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc kết quả hai vòng chạy lặp (tham số là số micro-giây chèn thêm vào luồng thợ trước khi nó xin khóa). Điều gì suy ra đúng?

```text
./treo_cv 0     : treo 1/300
./treo_cv 5000  : treo 19/20
```

- Lỗi chỉ xảy ra khi thợ ngủ 5000, nên nguyên nhân gốc chính là lệnh `sleep` này
- Chèn trễ làm chương trình chạy chậm nên `timeout` giết nhầm nó khi đang chạy bình thường
- Lỗi đã được sửa xong vì ở tham số 0 chương trình hầu như không còn treo
- Cửa sổ nằm trước lúc thợ vào `wait`; chèn trễ làm nó xảy ra gần như chắc

<p class="giai-thich" markdown>Chèn trễ ở thợ làm "tin tới trước khi thợ chờ" xảy ra gần như mọi lần (19/20), xác nhận cửa sổ nằm giữa lúc thợ khởi động và lúc thợ vào `wait`. Lỗi không do `sleep`: nó vốn có sẵn (1/300), `sleep` chỉ mở rộng cửa sổ. Treo ở đây là ngủ mãi chứ không phải bị giết nhầm, vì `timeout 1` dư cho mỗi lần chạy bình thường. Và 1/300 là lỗi **hiếm chứ chưa hết**, nên không được coi là đã sửa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Bạn sửa lost wakeup bằng `wait_for(lk, 20ms, [] { return sanSang; })`. Code đúng, nhưng TSan (g++ 11) báo `double lock of a mutex` rồi `data race` trên `sanSang`. Bước tiếp theo đúng là gì?

- Nghi dương tính giả, vì TSan có thể chưa bọc `pthread_cond_clockwait`; thử lại bằng bản `wait` không hạn giờ
- Thêm một lần `lock()` nữa quanh `sanSang` cho khớp với báo cáo, vì TSan luôn đúng một khi nó đã báo lỗi
- Bỏ predicate đi vì predicate là nguyên nhân khiến mutex bị khóa hai lần, rồi chạy lại cho đến khi sạch
- Tắt hẳn TSan trong dự án, vì một công cụ đã từng báo sai thì không còn đáng tin để bắt race thật nữa

<p class="giai-thich" markdown>Mutex không thật sự bị khóa hai lần: `wait_for` nhả khóa khi ngủ; nhiều khả năng TSan của g++ 11 không thấy lời gọi `pthread_cond_clockwait` nên mất dấu việc nhả. Cách kiểm đúng là chạy bản `wait` không hạn giờ (lời gọi mà TSan bọc), thấy sạch thì báo cáo kia đáng ngờ là giả. Thêm `lock()` thừa có thể gây deadlock thật. Bỏ predicate đưa lỗi lost wakeup trở lại. Tắt TSan vì một dương tính giả đã biết là mất công cụ bắt race thật.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Quy trình cho lỗi đa luồng: tái hiện, bắt bằng công cụ, khoanh vùng, sửa, chứng minh; chọn công cụ đầu tiên theo triệu chứng (sai thỉnh thoảng: TSan; treo: gdb; chậm: đo tranh chấp), và **không** sửa bằng `sleep`.
2. Đọc báo cáo TSan: hai truy cập (`Read/Write of size N`), dòng `(mutexes: ...)` (bên thiếu mutex chung là bên cần sửa), `Location`, hai luồng tạo ở đâu; với `lock-order-inversion` đọc chu trình `M9 => M10 => M9` và dùng `second_deadlock_stack=1` để thấy cả hai dòng khóa; mình **không chạy** Helgrind/DRD vì máy này không có `valgrind`.
3. Lỗi hiếm (Heisenbug) ẩn trong một cửa sổ chạy đua hẹp: chạy lặp và chèn `sleep_for`/`yield` để mở rộng cửa sổ (mình đo: 1/300 thành 19/20); chứng minh sửa bằng cách chạy lại đúng cách làm lỗi hiện chắc, kèm TSan sạch.
4. Luồng treo trong gdb hay core: `pthread_mutex_lock` là chờ khóa (xem `__owner`, vòng tròn là deadlock), `pthread_cond_wait` là chờ tín hiệu (`__owner` bằng 0, nghi lost wakeup), `pthread_join` là chờ luồng khác; nhật ký có số thứ tự và `thread::id` đánh số lại cho biết thứ tự sự kiện, nhưng ghi log cũng đổi lịch chạy.
5. Đo tranh chấp bằng đếm `try_lock` thất bại (1 luồng: 0; 8 luồng: cỡ một phần tư; gom 1000 lần: 0), vì `perf` bị chặn ở máy này; không tin mù quáng báo cáo công cụ (`double lock` ở `wait_for` của g++ 11 là dương tính giả); review code bằng checklist 10 điểm.
