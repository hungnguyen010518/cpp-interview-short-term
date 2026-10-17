# Bài 50 — I/O chặn, epoll và event loop: một luồng một kết nối hay một vòng lặp cho tất cả

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng **blocking I/O** làm gì với luồng, và đo được chi phí của mô hình **một luồng một kết nối** (số luồng, bộ nhớ ảo, bộ nhớ thật).
    - Phân biệt `select`, `poll`, `epoll`; hiểu non-blocking socket, `EAGAIN`, level-triggered và edge-triggered (và cái bẫy của edge).
    - Tự viết một **event loop** (`epoll_wait` → xử lý → chờ tiếp) chạy thật với `socketpair`, và biết việc nặng CPU phải giao cho **thread pool**.
    - Chọn mô hình và số luồng theo việc **nặng CPU** hay **chờ I/O**; trả lời "server 10 000 kết nối đồng thời thiết kế sao"; nối với netpoller của Go.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `steady_clock`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, hàng đợi), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (thread pool, số worker), [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md) (socket là một `fd`, `recv` có thể trả ít hơn xin), [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) (lời gọi hệ thống, `/proc/PID`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, `struct`).

## 🧠 Câu chuyện mở đầu

Quay lại **tòa chung cư**: server của bạn là một **căn hộ**, các thành viên trong căn hộ là các luồng. Căn hộ có **1000 đường dây điện thoại** nối ra ngoài, mỗi đường là một kết nối tới một khách. Phần lớn thời gian các đường dây im lặng, thỉnh thoảng một đường đổ chuông.

Cách một: **mỗi đường dây một thành viên** ngồi cạnh máy, nhấc ống nghe chờ. Bạn cần 1000 người, mỗi người một ngăn bàn riêng (stack), và họ ngồi không gần hết ngày. Cách hai: **một người trực bảng đèn**. Đường dây nào có người nói thì đèn của nó sáng; người trực chạy tới máy sáng đèn, trả lời nhanh, rồi quay lại nhìn bảng. Bảng đèn là `epoll`, vòng "nhìn bảng, xử lý, nhìn bảng" là **event loop**.

!!! info "Chỗ nào ví von không còn đúng?"
    Người trực thật thấy ngay đèn nào sáng, còn chương trình phải **hỏi hệ điều hành** (`epoll_wait`) và ngủ tới khi có đèn sáng. Nếu một cuộc gọi cần suy nghĩ rất lâu, người trực kẹt ở máy đó và **mọi đèn khác cứ sáng mà không ai tới** (mục 6): việc lâu phải giao cho đội khác (thread pool).

## 📖 Giải thích

### 1. Blocking I/O: luồng đứng chờ thì làm gì

**I/O** (input/output) là mọi lần chương trình đưa dữ liệu vào ra: đọc mạng, đọc đĩa, đọc từ luồng khác. Chương trình phải **nhờ hệ điều hành** qua lời gọi hệ thống ([Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)), ví dụ `read(fd, buf, n)`: "đọc tối đa n byte từ `fd` vào `buf`" (`fd` là file descriptor, số nguyên đại diện một tệp/socket đang mở, [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md)). Nó trả một `ssize_t` (số nguyên có dấu): số byte đọc được, `0` khi hết dữ liệu, `-1` khi lỗi. Hàm ngược lại là `write(fd, data, n)`: ghi n byte vào `fd`.

Mặc định `read` là **blocking** (chặn): chưa có dữ liệu thì hệ điều hành đặt luồng gọi vào trạng thái **ngủ** tới khi có. Ngủ không tốn CPU, nhưng luồng đó **không làm được việc gì khác** và vẫn giữ nguyên stack. Ta thấy rõ với một **pipe** (ống: hai đầu `fd`, ghi vào đầu này thì đọc ra ở đầu kia; `pipe(ong)` điền `ong[0]` là đầu đọc, `ong[1]` là đầu ghi): ống rỗng thì `read` ngủ.

Khi **mọi** đầu ghi đã đóng và hết dữ liệu, `read` trả `0` (EOF, "hết dữ liệu"); ví dụ dưới dùng đúng điều này để đánh thức đám luồng.

### 2. Một luồng một kết nối: đo chi phí

Mô hình **thread-per-connection** (một luồng một kết nối) đơn giản nhất: có kết nối mới thì tạo luồng, luồng đó `read`/xử lý/`write` tuần tự như code thường. Ví dụ 1 dựng 1000 luồng cùng `read` trên một ống rỗng (như 1000 kết nối im lặng), rồi hỏi `/proc/self/status` (tệp ảo về chính tiến trình này, [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)) xem tốn bao nhiêu (hàm `doc_status` mở tệp đó bằng `std::ifstream`, đọc từng "từ" bằng `>>` tới khi gặp tên cần tìm rồi lấy số liền sau).

`VmSize` là bộ nhớ **ảo** đã đăng ký, `VmRSS` là bộ nhớ **thật** đang nằm trong RAM; `std::clock()` trả thời gian CPU tiến trình đã tiêu.

**Ví dụ 1: 1000 luồng cùng chờ một ống rỗng**

```cpp
#include <unistd.h>
#include <chrono>
#include <ctime>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

// Đọc một mục trong /proc/self/status, ví dụ "Threads" hoặc "VmSize" (đơn vị kB).
long doc_status(const std::string& ten) {
    std::ifstream f("/proc/self/status");
    std::string tu;
    long v;
    while (f >> tu) {
        if (tu == ten + ":") { f >> v; return v; }
    }
    return -1;
}

int main() {
    int ong[2];
    if (pipe(ong) != 0) return 1;                                   // (1) ống: ong[0] đọc, ong[1] ghi
    long vm0 = doc_status("VmSize"), rss0 = doc_status("VmRSS");

    std::vector<std::thread> luong;
    for (int i = 0; i < 1000; ++i) {
        luong.emplace_back([&ong] {
            char c;
            if (read(ong[0], &c, 1) < 0) return;                    // (2) ống rỗng: luồng NGỦ ở đây
        });
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(300));    // (3) cho 1000 luồng kịp ngủ

    std::cout << "so luong trong tien trinh: " << doc_status("Threads") << "\n";    // (4)
    std::cout << "VmSize tang (MB): " << (doc_status("VmSize") - vm0) / 1024 << "\n";
    std::cout << "VmRSS tang (MB): " << (doc_status("VmRSS") - rss0) / 1024 << "\n";
    std::cout << "CPU da tieu (ms): " << static_cast<long>(1000.0 * std::clock() / CLOCKS_PER_SEC) << "\n";

    close(ong[1]);                                                  // (5) đóng đầu ghi: mọi read trả 0
    for (std::thread& t : luong) t.join();
    close(ong[0]);
    std::cout << "xong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | Tạo ống; `ong[0]` đọc, `ong[1]` ghi | chưa ai ghi |
| (2) | Mỗi luồng trong 1000 luồng gọi `read` trên ống rỗng và **ngủ** | 1000 luồng ngủ trong nhân |
| (3)-(4) | Luồng chính chờ 300 ms cho đủ luồng ngủ, rồi in số liệu | xem kết quả |
| (5) | Đóng đầu ghi: mọi `read` trả 0, 1000 luồng thoát, `join` xong | |

**Kết quả khi chạy** (g++ -std=c++17 -Wall -pthread, không tối ưu; ba lần liền ra cùng các số này, riêng CPU dao động quanh 50 ms):

```text
so luong trong tien trinh: 1001
VmSize tang (MB): 8004
VmRSS tang (MB): 8
CPU da tieu (ms): 50
xong
```

Đọc kết quả: 1001 luồng (1000 luồng phụ cộng luồng chính).

Mỗi luồng được cấp sẵn một stack ảo cỡ **8 MB** (mặc định của Linux, xem bằng `ulimit -s`; máy mình ra 8192 kB), nên `VmSize` tăng cỡ 1000 x 8 MB. Đó là bộ nhớ **đã giữ chỗ**, chưa dùng thật: `VmRSS` chỉ tăng 8 MB (cỡ 8 KB mỗi luồng). CPU chỉ ~50 ms trong 300 ms chờ, phần lớn là chi phí **tạo** luồng. Số của máy bạn sẽ khác; cái mẫu "luồng ngủ gần như miễn phí CPU nhưng mỗi luồng giữ một stack" mới đáng nhớ.

**Thử thay đổi: đổi 1000 thành 10000** (ở vòng `for`). Mình đã chạy hai lần: 10001 luồng, `VmSize` tăng 80042 MB (cỡ 80 GB ảo), `VmRSS` tăng 81 MB, CPU cỡ 400 đến 440 ms; máy mình vẫn chịu được. Đổi thành 40000 thì chết: `terminate called after throwing an instance of 'std::system_error'`, `what(): Resource temporarily unavailable` (mã thoát 134). Ngưỡng đổi theo máy và cấu hình (số luồng tối đa, giới hạn người dùng, số vùng nhớ ánh xạ); chỉ nhớ rằng **có trần**.

Vậy thread-per-connection tốn: **bộ nhớ** mỗi luồng (stack, cộng vài cấu trúc trong nhân), **context switch** (hệ điều hành luân phiên hàng nghìn luồng), và **trần số luồng**; luồng ngủ không tốn CPU nhưng 10 000 luồng ngủ vẫn là 10 000 stack. Đổi lại, code **tuần tự và dễ đọc**: với vài trăm kết nối, nó thường là lựa chọn hợp lý nhất.

### 3. Việc nặng CPU và việc chờ I/O: chọn số luồng

Việc **CPU-bound** (nặng CPU) là việc thời gian chủ yếu đi vào tính toán: lõi luôn bận. Việc **I/O-bound** (nặng I/O) là việc phần lớn thời gian đi vào **chờ** mạng/đĩa/dịch vụ khác. Phân loại này quyết định số luồng ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) đã nói nửa CPU-bound).

- **CPU-bound:** số luồng xấp xỉ số lõi (`std::thread::hardware_concurrency()` làm mốc). Nhiều hơn chỉ làm hệ điều hành luân phiên luồng trên cùng lõi, không thêm sức tính.
- **I/O-bound:** luồng chờ thì lõi rảnh, nên số luồng có thể **lớn hơn nhiều** số lõi. Ước lượng hay dùng: số luồng ≈ số lõi x (1 + thời gian chờ / thời gian tính), rồi **đo lại**. Hoặc dùng event loop để khỏi cần một luồng cho mỗi lần chờ.

[Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) đã đo đúng điều này: mỗi việc chỉ `sleep_for` 10 ms (giả vờ chờ mạng), 100 việc, pool 4 worker mất khoảng 252 ms còn pool 32 worker khoảng 43 ms trên máy bốn lõi của tác giả. Chờ không cần lõi, nên nhiều luồng hơn số lõi vẫn nhanh hơn; con số đổi theo máy. Mình cũng thử đo nửa CPU-bound (cùng việc tính, 8 so với 64 luồng) nhưng máy đang bận việc khác nên số nhiễu, vì vậy không đưa số; nguyên lý "chỉ có từng ấy lõi tính cùng lúc" không đổi.

### 4. Hỏi hệ điều hành "fd nào sẵn sàng": `select`, `poll`, `epoll`

Để một luồng phục vụ nhiều kết nối, ta cần cách hỏi: **"trong 1000 fd này, cái nào đọc được ngay (không phải ngủ)?"**. Ba lời gọi hệ thống trả lời câu đó, tăng dần về khả năng:

| | `select` | `poll` | `epoll` (Linux) |
|---|---|---|---|
| Cách đưa danh sách fd | Mỗi lần gọi đưa lại cả tập | Mỗi lần gọi đưa lại cả mảng | **Đăng ký một lần** (`epoll_ctl`), nhân nhớ |
| Giới hạn | Số fd tối đa thường 1024 (`FD_SETSIZE`, máy mình 1024) | Không bị trần 1024 | Không bị trần 1024 |
| Chi phí mỗi lần hỏi | Quét cả tập: tỉ lệ với **tổng số fd** | Quét cả mảng: tỉ lệ với tổng số fd | Trả **chỉ các fd sẵn sàng**: tỉ lệ với số fd sẵn sàng |
| Chạy ở đâu | Gần như mọi nơi | POSIX | Chỉ Linux (BSD/macOS: `kqueue`; Windows: IOCP) |

`epoll` có ba hàm: `epoll_create1` (tạo "bảng đèn"), `epoll_ctl` (thêm/bớt một fd trên bảng, kèm loại sự kiện muốn nghe như `EPOLLIN` = "có dữ liệu để đọc"), và `epoll_wait` (ngủ tới khi có fd sáng đèn rồi trả danh sách, có thể kèm thời gian chờ tối đa). Bảng chỉ dùng cho socket/ống/terminal: mình thử `epoll_ctl` trên một **tệp thường** (`/etc/hostname`) và nhận `-1`, lỗi `Operation not permitted`.

Muốn vòng lặp không bao giờ kẹt, mọi fd trên bảng nên là **non-blocking** (không chặn): `read` chưa có dữ liệu thì **không ngủ** mà trả ngay `-1` với `errno == EAGAIN` ("chưa có, lát hỏi lại"). Bật bằng `fcntl(fd, F_SETFL, ... | O_NONBLOCK)` (`fcntl` chỉnh thuộc tính của một fd: `F_GETFL` lấy các cờ hiện có, ta bật thêm `O_NONBLOCK` bằng phép `|` rồi `F_SETFL` đặt lại). Epoll có hai chế độ báo, bài này chỉ nêu tên:

- **Level-triggered** (mặc định): chừng nào fd **còn dữ liệu chưa đọc**, mỗi lần `epoll_wait` đều báo nó.
- **Edge-triggered** (`EPOLLET`): chỉ báo **lúc có dữ liệu mới đến**. Phải đọc tới `EAGAIN`, nếu không phần còn lại nằm đó mà không bao giờ được báo nữa (mục "Thử thay đổi" của Ví dụ 2 chạy thật cái treo này).

### 5. Event loop: vòng lặp sự kiện

**Event loop** là một vòng `while` làm ba việc: **chờ** (`epoll_wait`), **xử lý** từng fd sẵn sàng (đọc, tính, ghi) cực nhanh, rồi **quay lại chờ**. Một luồng phục vụ hàng nghìn kết nối, vì kết nối im lặng không tốn gì ngoài một mục trên bảng. Hai luật sống còn: **handler (đoạn xử lý) không được chặn**, vì luồng duy nhất kẹt ở đâu thì mọi kết nối kẹt theo; và **việc nặng CPU không chạy trong vòng lặp** (mục 6). Ví dụ 2 (phần 💻) là một event loop đầy đủ.

Hai tên mô hình hay gặp, chỉ cần nhận ra: **reactor** là "hệ điều hành báo **sẵn sàng**, bạn tự `read`/`write`" (epoll). **Proactor** là "bạn nhờ hệ điều hành **làm hẳn** việc đọc/ghi rồi nó báo **xong**" (IOCP trên Windows; `io_uring` trên Linux thường được xếp vào kiểu này).

!!! info "Bạn biết Go?"
    Trong Go bạn viết `conn.Read(buf)` trông như **chặn**, và thường mở một goroutine cho mỗi kết nối: code kiểu thread-per-connection. Khác ở chỗ **runtime** tự dùng epoll bên dưới (**netpoller**): fd mạng được đặt non-blocking, `Read` chưa có dữ liệu thì goroutine bị **đỗ lại** và luồng hệ điều hành đi chạy goroutine khác; có dữ liệu thì netpoller đánh thức nó.

    Mình đã chạy (Go 1.27.2): 2000 kết nối loopback, mỗi kết nối một goroutine đang chờ `Read`. Chương trình báo `goroutine: 2001`, còn `/proc/self/status` chỉ có **10 đến 11 luồng hệ điều hành**. Dưới `strace -f -c` thấy 1 lần `epoll_create1`, 4005 lần `epoll_ctl`, 7262 lần `epoll_pwait`. Go cho code tuần tự mà chi phí kiểu event loop; C++ thì bạn tự dựng vòng lặp (hoặc dùng thư viện như Boost.Asio, libuv).

### 6. Event loop + thread pool: một người nhận, nhiều người làm

Event loop mạnh ở **chờ**, yếu ở **tính**: một handler tính 300 ms thì cả vòng lặp đứng 300 ms. Mô hình thường dùng: luồng vòng lặp chỉ **nhận sự kiện, đọc yêu cầu, giao việc** cho thread pool ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)); worker tính rồi ghi kết quả về fd; vòng lặp luôn rảnh. Ví dụ 3 (phần 💻) đo đúng điều đó: một câu "ping" gần như rỗng đến sau ba việc nặng.

Bẫy của mô hình này là **tuổi thọ của fd**: nếu vòng lặp `close(fd)` khi worker còn đang tính cho fd đó, worker ghi vào fd đã đóng, tệ hơn là số fd đó đã được tái sử dụng cho kết nối khác. Ví dụ 3 tránh bằng cách khách chỉ đóng **sau khi nhận đủ trả lời**; server thật phải đếm việc đang chạy của từng kết nối (hoặc dùng `EPOLLONESHOT`, chỉ nêu tên).

### 7. Bảng chọn mô hình

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Vài chục đến vài trăm kết nối, cần code dễ đọc | Một luồng một kết nối (hoặc pool luồng blocking) | Code tuần tự, chi phí luồng chấp nhận được |
| Hàng nghìn đến hàng chục nghìn kết nối, phần lớn nhàn rỗi | Event loop (epoll) | Kết nối nhàn rỗi gần như miễn phí |
| Như trên, nhưng yêu cầu có phần tính nặng | Event loop **+ thread pool** | Vòng lặp luôn rảnh, pool tận dụng các lõi |
| Chỉ tính toán thuần, không có I/O | Thread pool cỡ ≈ số lõi | Không có gì để "chờ" |

**Khi nào KHÔNG dùng event loop:** ít kết nối (thêm độ phức tạp mà không được gì); handler hay phải gọi thứ **chặn** mà không có bản non-blocking (thư viện cơ sở dữ liệu đồng bộ, đọc tệp đĩa, `sleep`), vì mỗi lần gọi đóng băng cả vòng lặp; hoặc nhóm chưa quen lập trình bất đồng bộ, vì code kiểu "xử lý nửa chừng rồi chờ sự kiện sau" khó đọc hơn nhiều.

## 💻 Ví dụ code

### Ví dụ 2: event loop thật với `epoll` và `socketpair`

`socketpair(AF_UNIX, SOCK_STREAM, 0, sv)` tạo **một kết nối nội bộ hai đầu** `sv[0]` và `sv[1]`: ghi vào đầu này thì đọc ra ở đầu kia, cư xử như socket TCP (dòng byte) nhưng không cần mạng hay cổng. Server giữ 5 đầu `sv[0]`; một luồng giả lập khách giữ 5 đầu `sv[1]`. Server đổi chữ thường thành chữ hoa rồi gửi lại (mã ASCII của `'a'`..`'z'` lớn hơn mã chữ hoa tương ứng đúng 32, nên `buf[j] -= 32` đổi một chữ thường thành chữ hoa). `epoll_event ev{};` tạo một `struct` ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)) với mọi trường bằng 0 để ta điền; `ev.data.fd` là **nhãn** gửi kèm, `epoll_wait` trả lại đúng nhãn đó. `epoll_create1(0)`: số `0` là "không cờ đặc biệt". `epoll_wait(ep, ra, 16, -1)` điền tối đa 16 sự kiện vào mảng `ra`, trả số sự kiện đã điền; số cuối là thời gian chờ tối đa tính bằng mili giây, `-1` là chờ bao lâu cũng được. `sizeof buf` là kích thước mảng `buf` tính bằng byte.

```cpp
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

int main() {
    const int K = 5;                                   // số kết nối
    const std::string cau = "xin chao tu khach 0";     // mỗi khách gửi câu này (đổi số cuối), dài 19 byte
    std::vector<int> dau_khach(K);
    int ep = epoll_create1(0);                         // (1) tạo "bảng đèn" epoll
    for (int i = 0; i < K; ++i) {
        int sv[2];
        if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) return 1;   // (2) một "kết nối" nội bộ, hai đầu
        dau_khach[i] = sv[1];
        fcntl(sv[0], F_SETFL, fcntl(sv[0], F_GETFL) | O_NONBLOCK);   // (3) đầu server: non-blocking
        epoll_event ev{};
        ev.events = EPOLLIN;
        ev.data.fd = sv[0];
        epoll_ctl(ep, EPOLL_CTL_ADD, sv[0], &ev);      // (4) "fd này có dữ liệu thì báo tôi"
    }

    std::vector<std::string> tra_loi(K);
    std::thread khach([&] {                            // luồng giả lập K khách (chỉ để có người gửi)
        for (int i = 0; i < K; ++i) {
            std::string s = cau;
            s.back() = static_cast<char>('0' + i);
            if (write(dau_khach[i], s.data(), s.size()) < 0) return;
        }
        for (int i = 0; i < K; ++i) {                  // khách được phép chặn: nó chỉ có việc chờ
            char buf[64];
            while (tra_loi[i].size() < cau.size()) {
                ssize_t n = read(dau_khach[i], buf, sizeof buf);
                if (n <= 0) break;
                tra_loi[i].append(buf, n);
            }
        }
        for (int fd : dau_khach) close(fd);            // đóng: server sẽ thấy "hết dữ liệu"
    });

    int dang_mo = K;
    long tong_byte = 0;
    while (dang_mo > 0) {                              // (5) VÒNG LẶP SỰ KIỆN
        epoll_event ra[16];
        int n = epoll_wait(ep, ra, 16, -1);            // (6) ngủ tới khi có fd sẵn sàng
        for (int k = 0; k < n; ++k) {
            int fd = ra[k].data.fd;
            while (true) {                             // (7) đọc tới khi hết (EAGAIN) hoặc đóng (0)
                char buf[64];
                ssize_t r = read(fd, buf, sizeof buf);
                if (r > 0) {
                    for (ssize_t j = 0; j < r; ++j) if (buf[j] >= 'a' && buf[j] <= 'z') buf[j] -= 32;
                    if (write(fd, buf, r) < 0) break;  // (8) xử lý xong, gửi lại
                    tong_byte += r;
                } else if (r == 0) {                   // (9) bên kia đóng
                    close(fd);                         // đóng fd cũng tự gỡ nó khỏi epoll
                    --dang_mo;
                    break;
                } else {
                    break;                             // -1 và EAGAIN: hết dữ liệu, về epoll_wait
                }
            }
        }
    }
    khach.join();
    close(ep);
    for (int i = 0; i < K; ++i) std::cout << "khach " << i << " nhan: " << tra_loi[i] << "\n";
    std::cout << "server xu ly " << tong_byte << " byte tu " << K << " ket noi, tren mot luong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng đèn lúc này |
|---|---|---|
| (1)-(4) | Tạo epoll; mỗi kết nối: tạo cặp socket, đặt đầu server non-blocking, **đăng ký** nó | 5 fd trên bảng |
| luồng `khach` | Gửi 5 câu, rồi chờ đọc lại 5 câu in hoa | |
| (5)-(6) | Vòng lặp: `epoll_wait` ngủ tới khi có fd sáng | trả `n` fd sẵn sàng |
| (7)-(8) | Mỗi fd sáng: đọc, đổi chữ hoa, `write` về; lặp tới khi `read` trả -1 (EAGAIN) hoặc 0 | |
| (9) | Khách đóng: `read` trả 0, server `close` fd và giảm bộ đếm | còn 4, 3, ... rồi 0 fd |

**Kết quả khi chạy** (ba lần liền như nhau, TSan sạch):

```text
khach 0 nhan: XIN CHAO TU KHACH 0
khach 1 nhan: XIN CHAO TU KHACH 1
khach 2 nhan: XIN CHAO TU KHACH 2
khach 3 nhan: XIN CHAO TU KHACH 3
khach 4 nhan: XIN CHAO TU KHACH 4
server xu ly 95 byte tu 5 ket noi, tren mot luong
```

95 byte = 5 câu x 19 byte, do đúng **một luồng** (luồng chính) phục vụ: không có luồng nào cho từng kết nối. Thứ tự các fd được báo trong mỗi lần `epoll_wait` không được hứa, nên ta chỉ in kết quả theo chỉ số khách.

**Thử thay đổi 1: xóa dòng (3) (không đặt `O_NONBLOCK`).** Mình đã chạy với `timeout 3`: **treo**, mã thoát 124. Vòng (7) đọc xong câu của kết nối đầu rồi gọi `read` lần nữa; ở chế độ blocking lần đó **ngủ** mãi vì khách chưa gửi thêm, nên luồng duy nhất kẹt ở kết nối số 0 và bốn kết nối kia không bao giờ được phục vụ.

**Thử thay đổi 2: đọc một lần với bộ đệm 4 byte.** Mình sửa vòng (7): `char buf[4]`, mỗi sự kiện chỉ `read` đúng **một** lần (bỏ vòng `while`, vẫn đổi chữ hoa và ghi lại phần đọc được). Với `EPOLLIN` thường chương trình **vẫn đúng** (mã thoát 0, cùng kết quả): dữ liệu chưa đọc làm `epoll_wait` báo lại lần sau. Giữ nguyên đoạn đó và đổi dòng `ev.events = EPOLLIN;` thành `ev.events = EPOLLIN | EPOLLET;` (edge-triggered) thì **treo** (mã 124): 15 byte còn lại nằm trong socket mà không có "cạnh" mới nào để báo. Muốn dùng edge phải đọc tới `EAGAIN`, như vòng `while` ban đầu.

### Ví dụ 3: event loop giao việc nặng cho thread pool

Bốn kết nối: ba kết nối gửi một việc **nặng CPU** (đếm số nguyên tố nhỏ hơn 600 000, 500 000, 400 000); kết nối thứ tư gửi "ping" (đếm nhỏ hơn 10) **30 ms sau**, khi ba việc nặng đã đến. Ta so thời điểm khách nhận được trả lời. `std::to_string(n)` đổi số thành chuỗi, `std::stoi(buf)` đổi chuỗi chữ số thành `int`, và lambda `[&, i]` bắt mọi thứ theo tham chiếu, riêng `i` theo giá trị. Hằng `DUNG_POOL` chọn giao cho pool (`true`) hay tính ngay trong vòng lặp (`false`). `Pool` là bản rút gọn của [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md): hàng đợi việc, `mutex`, `condition_variable`, hàm hủy làm hết việc còn lại rồi `join`.

```cpp
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

const bool DUNG_POOL = true;                           // false: tính ngay trong vòng lặp

// Nhóm luồng rút gọn (xem Bài 30): hàng đợi việc + mutex + condition_variable.
class Pool {
public:
    Pool(int n) { for (int i = 0; i < n; ++i) ths.emplace_back([this] { chay(); }); }
    ~Pool() {
        { std::lock_guard<std::mutex> g(m); dung = true; }
        cv.notify_all();
        for (std::thread& t : ths) t.join();           // làm hết việc còn lại rồi mới thoát
    }
    void nop(std::function<void()> viec) {
        { std::lock_guard<std::mutex> g(m); hang.push(std::move(viec)); }
        cv.notify_one();
    }
private:
    void chay() {
        while (true) {
            std::unique_lock<std::mutex> lk(m);
            cv.wait(lk, [this] { return dung || !hang.empty(); });
            if (hang.empty()) return;
            std::function<void()> viec = std::move(hang.front());
            hang.pop();
            lk.unlock();                               // chạy việc NGOÀI khóa
            viec();
        }
    }
    std::mutex m;
    std::condition_variable cv;
    std::queue<std::function<void()>> hang;
    std::vector<std::thread> ths;
    bool dung = false;
};

void tra_loi(int fd, int n) {                          // việc nặng CPU: đếm số nguyên tố < n, ghi lại
    int dem = 0;
    for (int x = 2; x < n; ++x) {
        bool la = true;
        for (int d = 2; d * d <= x && la; ++d) la = (x % d != 0);
        if (la) ++dem;
    }
    std::string s = "n=" + std::to_string(n) + " nguyen_to=" + std::to_string(dem) + "\n";
    if (write(fd, s.data(), s.size()) < 0) std::cerr << "write loi\n";
}

int main() {
    const int yeu_cau[4] = {600000, 500000, 400000, 10};   // ba việc nặng + một "ping" gần như rỗng
    int ep = epoll_create1(0);
    int dau_khach[4];
    for (int i = 0; i < 4; ++i) {
        int sv[2];
        if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) return 1;
        dau_khach[i] = sv[1];
        fcntl(sv[0], F_SETFL, fcntl(sv[0], F_GETFL) | O_NONBLOCK);
        epoll_event ev{};
        ev.events = EPOLLIN;
        ev.data.fd = sv[0];
        epoll_ctl(ep, EPOLL_CTL_ADD, sv[0], &ev);
    }

    std::string loi_dap[4];
    std::chrono::steady_clock::time_point luc_nhan[4];
    std::vector<std::thread> khach;
    for (int i = 0; i < 4; ++i) {
        khach.emplace_back([&, i] {                    // luồng giả lập khách thứ i
            if (i == 3) std::this_thread::sleep_for(std::chrono::milliseconds(30));  // ping đến sau
            std::string req = std::to_string(yeu_cau[i]) + "\n";
            if (write(dau_khach[i], req.data(), req.size()) < 0) return;
            char c;
            while (read(dau_khach[i], &c, 1) == 1) {   // đọc từng byte tới hết dòng
                loi_dap[i] += c;
                if (c == '\n') break;
            }
            luc_nhan[i] = std::chrono::steady_clock::now();
            close(dau_khach[i]);                       // chỉ đóng SAU khi nhận đủ trả lời
        });
    }

    {
        Pool pool(4);                                  // (1) 4 worker
        int dang_mo = 4;
        while (dang_mo > 0) {                          // (2) luồng chính = vòng lặp sự kiện
            epoll_event ra[8];
            int n = epoll_wait(ep, ra, 8, -1);
            for (int k = 0; k < n; ++k) {
                int fd = ra[k].data.fd;
                char buf[32];
                ssize_t r = read(fd, buf, sizeof buf - 1);
                if (r > 0) {
                    buf[r] = '\0';
                    int so = std::stoi(buf);
                    if (DUNG_POOL) pool.nop([fd, so] { tra_loi(fd, so); });   // (3) giao cho worker
                    else tra_loi(fd, so);              // (3') tự tính ngay trong vòng lặp
                } else if (r == 0) {
                    close(fd);
                    --dang_mo;
                }
            }
        }
    }                                                  // (4) ~Pool đợi worker xong hết
    for (std::thread& t : khach) t.join();
    close(ep);

    for (int i = 0; i < 4; ++i) std::cout << "ket noi " << i << ": " << loi_dap[i];
    bool ping_truoc = luc_nhan[3] < luc_nhan[0] && luc_nhan[3] < luc_nhan[1] && luc_nhan[3] < luc_nhan[2];
    std::cout << "ping tra loi truoc ca ba viec nang? " << ping_truoc << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai đang làm gì |
|---|---|---|
| (1) | Dựng pool 4 worker | 4 worker ngủ chờ việc |
| (2) | Luồng chính chạy event loop như Ví dụ 2 | luồng chính ngủ ở `epoll_wait` |
| (3) | Đọc được số `so`: **đóng gói thành việc và nộp** cho pool, rồi quay lại `epoll_wait` ngay | worker tính; vòng lặp rảnh |
| ping | 30 ms sau, ping đến: vòng lặp thức dậy, nộp việc, worker còn rảnh làm trong tích tắc | ba worker còn bận tính |
| (4) | Hết vòng: `~Pool` đợi worker xong rồi mới đi tiếp | |

**Kết quả khi chạy** (g++ -std=c++17 -Wall -pthread; ba lần liền như nhau, TSan sạch):

```text
ket noi 0: n=600000 nguyen_to=49098
ket noi 1: n=500000 nguyen_to=41538
ket noi 2: n=400000 nguyen_to=33860
ket noi 3: n=10 nguyen_to=4
ping tra loi truoc ca ba viec nang? 1
```

**Thử thay đổi: đặt `DUNG_POOL = false`** (vòng lặp tự tính, như một handler "nặng"). Mình đã chạy ba lần: kết quả tính vẫn đúng nhưng dòng cuối thành `ping tra loi truoc ca ba viec nang? 0`. Luồng chính bận tính việc nặng thứ nhất, rồi thứ hai, thứ ba, nên ping (đến sau) phải chờ cả ba. Thời gian cả chương trình mình đo (ba lần mỗi bên, đổi theo máy): khoảng 0,18 đến 0,21 giây với pool, 0,41 đến 0,48 giây khi tính trong vòng lặp, vì pool còn chia ba việc cho nhiều lõi.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Server cần phục vụ 10 000 kết nối đồng thời, bạn thiết kế sao?"
    Mình hỏi lại: kết nối chủ yếu nhàn rỗi hay liên tục bận, mỗi yêu cầu tốn CPU hay chờ dịch vụ khác. Nếu phần lớn nhàn rỗi và yêu cầu nhẹ, mình dùng **event loop trên epoll** với socket non-blocking: kết nối nhàn rỗi gần như không tốn gì, một hoặc vài luồng vòng lặp là đủ. Nếu yêu cầu có phần tính nặng, thêm **thread pool cỡ khoảng số lõi**; luồng vòng lặp chỉ nhận và giao việc. Một luồng một kết nối thì 10 000 luồng là 10 000 stack (mình đo: cỡ 80 GB bộ nhớ ảo trên máy mình) cộng nhiều context switch: làm được nhưng gần trần.

??? question "Nối tiếp: thế nếu một handler gọi cơ sở dữ liệu đồng bộ mất 50 ms thì sao?"
    Nó chặn cả vòng lặp, 10 000 kết nối cùng chờ. Hoặc dùng thư viện non-blocking để việc chờ đó cũng đăng ký vào epoll, hoặc đẩy lời gọi sang một **thread pool riêng cho việc chờ** (cỡ lớn hơn số lõi vì chỉ chờ) rồi gửi kết quả về vòng lặp. Không để lời gọi chặn chạy thẳng trong handler.

??? question "`select`, `poll` và `epoll` khác nhau thế nào?"
    Cả ba trả lời "fd nào sẵn sàng". `select` và `poll` nhận lại **cả danh sách** fd mỗi lần gọi và nhân quét hết, nên chi phí tăng theo tổng số fd; `select` còn có trần thường 1024 fd. `epoll` (chỉ Linux) **đăng ký một lần** bằng `epoll_ctl` và `epoll_wait` chỉ trả fd sẵn sàng, nên hợp với nhiều fd mà ít fd bận cùng lúc. Với ít fd, khác biệt không đáng kể.

??? question "Level-triggered và edge-triggered khác nhau thế nào, bẫy ở đâu?"
    Level báo **chừng nào còn dữ liệu chưa đọc**; edge chỉ báo **lúc có dữ liệu mới**. Bẫy của edge: đọc dở rồi quay lại `epoll_wait` thì phần còn lại không được báo nữa, kết nối treo (mình đã chạy ra treo). Nên edge luôn đi với socket non-blocking và vòng đọc tới `EAGAIN`.

??? question "Chọn số luồng thế nào cho việc nặng CPU và việc chờ I/O? Reactor khác proactor thế nào?"
    Nặng CPU: cỡ số lõi, nhiều hơn chỉ thêm context switch. Chờ I/O: nhiều hơn số lõi rất nhiều vì luồng chờ không dùng CPU; ước lượng số lõi x (1 + chờ/tính) rồi đo ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) đo 100 việc chờ 10 ms: pool 4 worker cỡ 252 ms, pool 32 worker cỡ 43 ms). Reactor: hệ điều hành báo fd **sẵn sàng**, chương trình tự đọc/ghi (epoll). Proactor: chương trình nhờ hệ điều hành **làm hẳn** rồi nhận thông báo **xong** (IOCP, `io_uring`). Go ẩn epoll sau `conn.Read` (netpoller), nên code nhìn như chặn mà không tốn một luồng hệ điều hành cho mỗi kết nối.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Làm việc nặng hoặc gọi hàm chặn trong event loop"
    Một handler chạy lâu làm **mọi** kết nối khác đứng chờ (mình đã chạy: ping phải chờ ba việc nặng, Ví dụ 3 với `DUNG_POOL = false`). Việc nặng giao cho thread pool; việc chờ dùng non-blocking.

!!! warning "Lỗi 2: Quên non-blocking, hoặc dùng edge-triggered mà không đọc tới EAGAIN"
    Quên `O_NONBLOCK` thì lần `read` thừa **ngủ** cả vòng lặp; edge mà đọc dở thì phần còn lại không bao giờ được báo (cả hai mình đã chạy ra treo, Ví dụ 2). Quy tắc: fd trên epoll là non-blocking, và đọc tới `EAGAIN` (hoặc `0`).

!!! warning "Lỗi 3: Giả định `write` luôn ghi hết, và đóng fd khi việc còn chạy"
    Ví dụ ngắn chỉ ghi vài chục byte nên `write` ghi trọn; server thật có lúc `write` ghi dở hay trả `EAGAIN` (bộ đệm đầy), phải giữ phần còn lại trong hàng đợi và nghe `EPOLLOUT` (chỉ nêu tên). Và đừng `close(fd)` khi worker còn đang dùng nó (mục 6).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="50" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Một luồng gọi `read` (chế độ mặc định, blocking) trên một ống đang rỗng, chưa ai ghi. Trong lúc chờ, luồng đó ở trạng thái nào?

- Quay vòng hỏi liên tục "có dữ liệu chưa", nên chiếm trọn một lõi CPU
- Bị hệ điều hành hủy sau một thời gian chờ mặc định rồi `read` trả lỗi
- Ngủ trong nhân, gần như không tốn CPU, và vẫn giữ nguyên stack của nó
- Đã được hệ điều hành chuyển sang non-blocking và tự trả `EAGAIN`

<p class="giai-thich" markdown>Blocking `read` đặt luồng vào trạng thái ngủ và chỉ đánh thức khi có dữ liệu hoặc đầu ghi đóng hết; ngủ thì không dùng CPU, nhưng stack của luồng vẫn còn đó (mình đo 1000 luồng ngủ giữ cỡ 8 GB bộ nhớ ảo). Quay vòng hỏi liên tục là cách viết thủ công khác, không phải việc `read` blocking làm. Không có thời gian chờ mặc định nào hủy luồng, và hệ điều hành không tự đổi chế độ: chỉ khi bạn đặt `O_NONBLOCK` thì `read` mới trả `-1` với `EAGAIN` thay vì ngủ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Dịch vụ thông báo đẩy giữ 20 000 kết nối, hầu hết im lặng hàng phút; mỗi tin gửi đi chỉ là sao chép vài chục byte. Máy 8 lõi. Thiết kế nào hợp nhất?

- Event loop trên epoll với socket non-blocking, một hoặc vài luồng vòng lặp
- Một luồng một kết nối, mỗi luồng `read` blocking rồi gửi
- Thread pool 8 luồng, mỗi luồng giữ cố định 2500 kết nối và `read` blocking lần lượt
- Một thread pool cỡ 20 000 luồng, vì số luồng phải bằng số kết nối

<p class="giai-thich" markdown>Rất nhiều kết nối nhàn rỗi và việc xử lý cực nhẹ là đúng chỗ của event loop: kết nối im lặng chỉ là một mục trên bảng epoll. Một luồng một kết nối ở quy mô này tốn 20 000 stack và nhiều context switch. Tám luồng mỗi luồng `read` blocking lần lượt trên 2500 kết nối thì kẹt ngay ở kết nối im lặng đầu tiên, các kết nối còn lại không được phục vụ. Còn "số luồng phải bằng số kết nối" chỉ là cách nói khác của mô hình một luồng một kết nối.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. Fd đăng ký với `EPOLLIN | EPOLLET`, socket non-blocking. Có 100 byte đến, `epoll_wait` báo fd sẵn sàng, ta `read` đúng 10 byte rồi gọi lại `epoll_wait` (không thêm dữ liệu nào đến). Điều gì xảy ra?

```text
epoll_ctl(ep, ADD, fd, EPOLLIN | EPOLLET);
// 100 byte đến
epoll_wait(ep, ra, 8, -1);     // báo fd sẵn sàng
read(fd, buf, 10);             // chỉ đọc 10 byte
epoll_wait(ep, ra, 8, -1);     // lần này?
```

- Trả về ngay, vì còn 90 byte chưa đọc nằm trong socket
- Trả về ngay với lỗi `EAGAIN`, vì lần đọc trước chưa hết
- Trả về ngay với `0`, vì 10 byte đầu đã được lấy rồi
- Chờ mãi, vì edge-triggered chỉ báo lúc có dữ liệu mới đến

<p class="giai-thich" markdown>Edge-triggered chỉ báo khi trạng thái chuyển sang "có dữ liệu mới"; 90 byte còn lại không tạo cạnh mới nên lần `epoll_wait` thứ hai ngủ mãi cho tới khi có dữ liệu mới. Trả ngay vì "còn dữ liệu" là hành vi của level-triggered, chế độ mặc định, và là chỗ nhầm hay gặp. `EAGAIN` là kết quả của `read` trên socket non-blocking khi hết dữ liệu, không phải của `epoll_wait`; và `epoll_wait` trả số fd sẵn sàng chứ không trả lỗi kiểu đó. Cách sửa là đọc cho tới khi `read` trả `EAGAIN`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Event loop một luồng; 10 khách cùng gửi một yêu cầu gần như cùng lúc. Khách cuối cùng nhận trả lời sau khoảng bao lâu (bỏ qua chi phí nhỏ khác)?

```text
vòng lặp: epoll_wait -> với mỗi fd sáng gọi handler(fd)
handler(fd): read(fd); sleep(100 ms);   // giả lập gọi dịch vụ ngoài
             write(fd)
```

- Cỡ 100 ms, vì `epoll` xử lý các fd song song
- Cỡ 10 ms, vì mỗi khách chỉ chiếm một phần mười thời gian
- Cỡ 1 giây, vì các handler chạy nối đuôi trên một luồng
- Không bao giờ nhận được, vì `sleep` làm `epoll_wait` hỏng

<p class="giai-thich" markdown>Chỉ có một luồng nên 10 handler chạy lần lượt, mỗi cái chiếm luồng 100 ms; khách thứ mười chờ cỡ 10 x 100 ms = 1 giây. `epoll` chỉ cho biết fd nào sáng đèn, nó không chạy handler song song. Không có phép chia nào làm mỗi khách chỉ tốn một phần mười. `sleep` không làm hỏng `epoll_wait`, nó chỉ làm luồng duy nhất kẹt lâu; đây chính là lý do không đặt việc chậm trong handler mà giao cho pool hoặc dùng cách non-blocking.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Mỗi yêu cầu của một dịch vụ tốn khoảng 5 ms tính toán rồi chờ cơ sở dữ liệu 95 ms; máy 8 lõi, dùng thread pool với luồng blocking. Cỡ pool nào hợp lý để **bắt đầu thử**?

- 8 luồng, vì số luồng nên bằng số lõi của máy
- Cỡ 160 luồng (8 x (1 + 95/5)), rồi đo lại để chỉnh
- 1 luồng, vì chờ cơ sở dữ liệu không cần song song
- Cỡ 100 000 luồng, vì mỗi yêu cầu cần một luồng riêng

<p class="giai-thich" markdown>Phần lớn thời gian của một yêu cầu là chờ, và luồng chờ không dùng CPU, nên cần nhiều luồng hơn số lõi để lõi không rảnh: số lõi x (1 + chờ/tính) cho cỡ 160, rồi đo vì đây chỉ là ước lượng. "Bằng số lõi" là quy tắc của việc nặng CPU, áp vào việc chờ thì để lõi nhàn rỗi. Một luồng thì mỗi yêu cầu phải nối đuôi chờ nhau. Mỗi yêu cầu một luồng không giới hạn thì tốn bộ nhớ và dễ chạm trần số luồng như phép thử 40 000 luồng ở bài này.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Cổng web chạy event loop ổn định. Bạn thêm tính năng đổi kích thước ảnh, mỗi ảnh tính khoảng 300 ms CPU, và thấy các yêu cầu nhỏ khác bắt đầu chậm. Nên làm gì?

- Đổi tất cả fd sang edge-triggered để mỗi lần xử lý nhanh hơn
- Tăng thời gian chờ tối đa của `epoll_wait` lên để bớt gọi
- Thêm một bảng epoll thứ hai chạy cùng luồng để chia tải
- Giao việc ảnh cho thread pool, vòng lặp chỉ nhận và giao việc

<p class="giai-thich" markdown>Việc tính 300 ms chiếm luồng duy nhất của vòng lặp, nên mọi yêu cầu khác phải chờ; giao việc nặng cho thread pool giữ cho vòng lặp luôn rảnh, đúng như ví dụ ping ở bài này. Edge-triggered chỉ đổi cách báo sự kiện, không rút ngắn việc tính. Thời gian chờ tối đa của `epoll_wait` là thời gian ngủ khi không có gì, không liên quan tới việc handler chạy lâu. Hai bảng epoll trên cùng một luồng vẫn chia nhau một luồng, tổng thời gian tính không giảm.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Blocking I/O** làm luồng **ngủ** trong nhân: không tốn CPU nhưng giữ một stack. Một luồng một kết nối đơn giản nhưng tốn bộ nhớ, context switch và có trần (mình đo: 1000 luồng ngủ giữ cỡ 8 GB ảo và 8 MB thật; 10 000 luồng chạy được ở cỡ 80 GB ảo; 40 000 luồng làm `std::thread` ném `system_error`).
2. `select`/`poll` nhận lại cả danh sách fd mỗi lần và quét hết (`select` trần thường 1024); `epoll` (Linux) đăng ký một lần (`epoll_ctl`) và `epoll_wait` chỉ trả fd sẵn sàng. Fd trên epoll nên **non-blocking** (`read` trả `-1`/`EAGAIN` thay vì ngủ); level-triggered báo khi còn dữ liệu, edge-triggered chỉ báo khi có dữ liệu mới nên phải đọc tới `EAGAIN` (mình chạy ra treo nếu không).
3. **Event loop** = `epoll_wait` → xử lý rất nhanh → chờ tiếp, một luồng phục vụ rất nhiều kết nối. Handler không được chặn: mình chạy ra treo khi bỏ `O_NONBLOCK`, và ping phải chờ ba việc nặng khi tính ngay trong vòng lặp.
4. Việc **nặng CPU** thì số luồng ≈ số lõi; việc **chờ I/O** thì nhiều hơn (ước lượng lõi x (1 + chờ/tính), rồi đo; [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) đo 100 việc chờ 10 ms: pool 4 worker ~252 ms, pool 32 worker ~43 ms). Mô hình phổ biến: event loop nhận sự kiện **+ thread pool** tính; coi chừng tuổi thọ của fd khi worker còn dùng.
5. Reactor (hệ điều hành báo sẵn sàng, bạn tự đọc: epoll) và proactor (bạn nhờ làm hẳn, nó báo xong: IOCP, `io_uring`) chỉ cần nhận tên; Go dùng epoll bên dưới (netpoller): mình đo 2000 goroutine chờ `Read` chỉ dùng 10 đến 11 luồng hệ điều hành. Không dùng event loop khi ít kết nối hoặc handler hay gọi hàm chặn không có bản non-blocking.
