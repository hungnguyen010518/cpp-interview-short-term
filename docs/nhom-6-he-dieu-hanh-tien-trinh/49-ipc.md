# Bài 49 — Giao tiếp giữa các tiến trình (IPC): pipe, shared memory, message queue, socket, signal

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao hai tiến trình **không thấy bộ nhớ của nhau**, nên mọi cách giao tiếp (IPC, inter-process communication) đều phải đi qua hệ điều hành; chia được các cách thành ba họ: nhân chép dữ liệu hộ (pipe, socket, message queue), hai tiến trình cùng nhìn một vùng nhớ (shared memory), và chỉ "gõ cửa" không mang dữ liệu (signal).
    - Viết và chạy thật `pipe` + `fork` (cha gửi, con đọc), shared memory (`mmap`, `shm_open`) có đồng bộ bằng `sem_t` hoặc `pthread_mutex` kiểu "dùng chung giữa tiến trình"; nói đúng **vì sao không nhét `std::mutex` thường vào shared memory** (mình đã chạy: hỏng).
    - Nhận biết message queue POSIX, FIFO, UNIX domain socket (so với TCP) và viết handler `signal` đúng luật: chỉ đặt cờ `volatile sig_atomic_t`, việc còn lại làm ở vòng lặp chính.
    - Chọn cơ chế bằng bảng tiêu chí (mô hình dữ liệu, chiều, cần quan hệ cha-con, tốc độ, độ khó) và trả lời "cách nhanh nhất để trao đổi dữ liệu lớn", kể cả chỗ shared memory **không** nhanh hơn.

**Bạn cần biết trước:** [Bài 47](47-tien-trinh-vs-luong.md) và [Bài 48](48-fork-exec-wait.md) (tiến trình khác luồng, `fork`, `waitpid`; mục 1 nhắc lại ngắn), [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md) (socket, file descriptor, `SIGPIPE`, TCP), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`volatile` không phải đồng bộ), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (`struct`, biến toàn cục), [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (con trỏ), [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) (`void*`, phép tính trên con trỏ, `static_cast`).

## 🧠 Câu chuyện mở đầu

Quay lại **tòa chung cư**: mỗi tiến trình là một căn hộ, có tường riêng và khóa riêng. Người ở căn 301 không thể thò tay sang tủ lạnh căn 302. Muốn trao đổi, họ phải dùng thứ **do ban quản lý (hệ điều hành) lắp sẵn** cho cả tòa nhà.

Có vài thứ như vậy. **Ống dẫn thư** nối hai căn hộ: một đầu bỏ vào, đầu kia lấy ra, đúng thứ tự (pipe).

**Hộp thư có ngăn**, mỗi lá thư là một phong bì nguyên vẹn (message queue). **Điện thoại nội bộ** nói hai chiều (socket). **Bảng thông báo ở sảnh**: ai cũng đọc và viết thẳng lên đó, không qua ai (shared memory). Và **chuông cửa**: bấm là người trong nhà biết có việc, nhưng chuông không mang nội dung (signal).

!!! info "Chỗ nào ví von này không còn đúng?"
    Ống, hộp thư, điện thoại có ban quản lý đứng giữa **chép hộ** từng lá thư và tự xếp hàng. Bảng thông báo ở sảnh thì khác: sau khi lắp xong, hai bên đọc ghi **thẳng** vào cùng một vùng RAM, ban quản lý không xếp hàng hộ, nên hai người viết cùng lúc là hỏng (mục 3 của phần 📖). Ngoài ra chuông chỉ nói được "có việc" kiểu một trong vài chục loại có sẵn, không nói được "việc gì" (mục E).

## 📖 Giải thích

### 1. Vì sao tiến trình không thấy bộ nhớ nhau

Mỗi tiến trình có **bản đồ địa chỉ ảo** riêng ([Bài 47](47-tien-trinh-vs-luong.md)): con trỏ `0x1000` ở tiến trình A và `0x1000` ở tiến trình B trỏ tới hai ô RAM khác nhau. Gửi một con trỏ sang tiến trình kia là vô nghĩa, vì bên kia không có ô nào ở địa chỉ đó. Chỉ có hệ điều hành thấy cả hai bản đồ, nên mọi IPC đều là nhờ hệ điều hành.

Có ba họ: **nhân chép dữ liệu hộ** (pipe, FIFO, socket, message queue: tốn một lần chép vào nhân, một lần chép ra, một lời gọi hệ thống mỗi lần gửi/nhận), **cùng nhìn một vùng nhớ** (shared memory: gần như không chép, nhưng chính bạn phải đồng bộ), và **gõ cửa** (signal: không mang dữ liệu).

Nhắc lại `fork` ([Bài 48](48-fork-exec-wait.md) dạy kỹ): `fork()` nhân đôi tiến trình đang chạy; cha nhận số hiệu tiến trình con (pid), con nhận `0`, lỗi thì cha nhận `-1`. Con có **bản sao** dữ liệu của cha, và **thừa hưởng các file descriptor (fd) đang mở** ([Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md): fd là số nguyên đại diện một tệp, socket... đang mở). `waitpid(pid, nullptr, 0)` bắt cha chờ con xong để không để lại zombie (con đã chết nhưng chưa được cha "ký giấy").

### 2. `pipe`: ống một chiều giữa cha và con

`pipe(ong)` nhận mảng hai số nguyên và điền hai fd: `ong[0]` là **đầu đọc**, `ong[1]` là **đầu ghi**. Byte ghi vào đầu ghi thì đọc ra được ở đầu đọc, đúng thứ tự (FIFO: vào trước ra trước). Ta tạo ống **trước** `fork`, nên cả cha lẫn con đều thừa hưởng hai fd; đó là cách hai tiến trình "gặp nhau" mà không cần tên gọi nào.

Hàm mới: `write(fd, dữ_liệu, số_byte)` ghi, trả số byte đã ghi (hoặc -1 khi lỗi); `read(fd, bộ_đệm, số_tối_đa)` đọc, trả số byte đọc được, trả **0** khi không còn ai có thể ghi nữa; `close(fd)` đóng một fd. Số byte trả về có kiểu `ssize_t`, một số nguyên **có dấu** để chứa được cả `-1`.

```cpp
#include <cstring>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    int ong[2];                                    // (1) ong[0] = đầu đọc, ong[1] = đầu ghi
    if (pipe(ong) == -1) return 1;                 // (2) hệ điều hành tạo ống, trả hai fd

    pid_t pid = fork();                            // (3) con cũng có ong[0] và ong[1]
    if (pid == -1) return 1;

    if (pid == 0) {                                // (4) nhánh của CON
        close(ong[1]);                             // (5) con chỉ đọc: đóng đầu ghi của MÌNH
        char dem[64];
        ssize_t n;
        while ((n = read(ong[0], dem, sizeof dem)) > 0) {   // (6) đọc tới khi hết dữ liệu
            std::cout << "con nhan " << n << " byte: " << std::string(dem, n) << "\n";
        }
        std::cout << "con: read tra " << n << " (het du lieu)\n";   // (7)
        close(ong[0]);
        return 0;
    }

    close(ong[0]);                                 // (8) cha chỉ ghi: đóng đầu đọc
    const char* loi = "xin chao tu cha";
    if (write(ong[1], loi, std::strlen(loi)) == -1) return 1;   // (9) gửi 15 byte vào ống
    close(ong[1]);                                 // (10) cha đóng đầu ghi cuối cùng -> con sẽ thấy hết dữ liệu
    waitpid(pid, nullptr, 0);                      // (11) chờ con xong, không để lại zombie
    std::cout << "cha: xong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Các fd lúc này |
|---|---|---|
| (2) | Nhân tạo ống, giả sử cho fd 3 (đọc) và 4 (ghi) | cha: 3, 4 |
| (3) | `fork`: con là bản sao, thừa hưởng cả fd 3 và 4 | cha: 3, 4; con: 3, 4 |
| (5), (8) | Mỗi bên đóng đầu mình không dùng | cha: chỉ 4 (ghi); con: chỉ 3 (đọc) |
| (9), (6) | Cha ghi 15 byte vào ống (nhân giữ trong bộ đệm của ống); con `read` lấy 15 byte. Nếu ống rỗng mà vẫn còn bên ghi thì `read` **chặn** chờ | ống rỗng |
| (10) | Cha đóng đầu ghi cuối cùng của ống | không còn ai ghi được |
| (6), (7), (11) | `read` của con trả `0`: "hết dữ liệu", con thoát vòng lặp và `main`; cha `waitpid` xong, in "cha: xong" | |

(Các số fd 3, 4 là minh họa, máy bạn có thể khác; chỉ cái mẫu quan trọng.)

**Kết quả khi chạy** (ba lần liền đều như nhau; cũng sạch khi biên dịch thêm `-O2`):

```text
con nhan 15 byte: xin chao tu cha
con: read tra 0 (het du lieu)
cha: xong
```

Thứ tự ổn định vì cha `waitpid` trước khi in dòng cuối, nên dòng của con luôn đứng trước.

**Thử thay đổi: xóa dòng (5)** (con quên đóng đầu ghi của mình). Mình đã chạy với `timeout 3`: **không in gì** và `timeout` thoát mã **124** (hết giờ). Con vẫn tự giữ một đầu ghi mở, nên nhân tưởng "vẫn còn người ghi" và `read` của con chặn mãi; cha thì đang `waitpid` chờ con. Quy tắc: **mỗi bên đóng mọi đầu ống mình không dùng**, và đừng quên rằng `fork` nhân đôi cả hai đầu.

Ba tính chất cần nhớ của pipe. Một: nó là **dòng byte một chiều**, không có ranh giới thông điệp (hai lần `write` có thể bị gộp thành một lần `read`, như TCP ở [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md)). Hai: bộ đệm của ống có hạn; mình đo trên Linux này bằng `fcntl(F_GETPIPE_SZ)` được **65536 byte**, ghi tới khi đầy thì `write` chặn (hoặc trả lỗi nếu fd ở chế độ không chặn). Ba: ghi vào ống đã **không còn ai đọc** thì tiến trình nhận `SIGPIPE` (mình chạy: tiến trình bị giết, mã thoát 141), giống socket ở Bài 44.

!!! info "Bạn biết Go?"
    Goroutine trong cùng một tiến trình giao tiếp bằng channel hoặc `sync.Mutex`, không cần IPC. Khi cần nói chuyện với tiến trình khác, Go dùng đúng các cơ chế hệ điều hành này: `os.Pipe()`, `net.Listen("unix", ...)`, `syscall.Mmap`. Go không có `fork` trần để nhân đôi tiến trình đang chạy (runtime của Go nhiều luồng); tạo tiến trình con là việc của `os/exec`, nó gắn pipe vào `Stdin`/`Stdout` của con giúp bạn.

**FIFO (named pipe)** là pipe có **tên trong hệ thống tệp**, nên hai tiến trình **không cần quan hệ cha-con** vẫn mở chung được. Tạo bằng `mkfifo ten` (lệnh shell) hoặc hàm `mkfifo()`; `ls -l` hiện ký tự đầu là `p`. Mình thử: `mkfifo ff; (echo "xin chao qua fifo" > ff &); cat ff` in ra đúng `xin chao qua fifo`. Phần còn lại giống pipe thường: dòng byte một chiều; mở đầu ghi sẽ chờ tới khi có bên mở đầu đọc.

### 3. Shared memory: hai căn hộ cùng nhìn một bảng

Với pipe mỗi byte đi hai lần qua nhân. **Shared memory** (bộ nhớ chung) làm khác: nhờ hệ điều hành, **một vùng RAM thật** được ánh xạ vào bản đồ của **cả hai** tiến trình. Sau đó hai bên đọc ghi vùng đó như bộ nhớ thường, không còn lời gọi hệ thống nào mỗi lần trao đổi. Hàm chủ chốt là **`mmap`** (memory map, "ánh xạ bộ nhớ"): xin hệ điều hành một vùng và cho bạn con trỏ tới nó.

Có hai cách lấy vùng chung. **Cách 1, ẩn danh + `fork`:** `mmap(..., MAP_SHARED | MAP_ANONYMOUS, -1, 0)` trả một vùng không có tên; sau `fork`, con **thừa hưởng** ánh xạ đó nên cả hai cùng thấy một vùng (khác bộ nhớ thường, vốn được sao chép riêng sau `fork`). **Cách 2, có tên:** `shm_open("/ten", ...)` + `ftruncate` + `mmap` (mục 💻 A) cho tiến trình **không quan hệ** gặp nhau qua tên.

Đọc dòng `mmap(nullptr, kích_thước, quyền, cờ, fd, vị_trí)` như sau: `nullptr` là "hệ điều hành chọn địa chỉ giúp"; `PROT_READ | PROT_WRITE` là quyền đọc và ghi (dấu `|` ghép hai cờ, mỗi cờ là một bit bật lên); `fd = -1` nghĩa là không dựa vào tệp nào; trả `MAP_FAILED` khi lỗi, ngược lại trả `void*` (con trỏ không kiểu, Bài 05) mà ta đổi sang kiểu mình cần bằng `static_cast`. Dùng xong thì `munmap` trả vùng lại.

Điều bạn phải tự lo là **đồng bộ**. Nhân không xếp hàng hộ: hai tiến trình cùng `++` một số trong vùng chung là data race y như hai luồng ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).

Chương trình dưới cho cha và con mỗi bên tăng `dem` 100000 lần, bảo vệ bằng **`sem_t`**: semaphore POSIX, một bộ đếm do nhân quản lý; `sem_wait` trừ 1 (nếu đang 0 thì chờ), `sem_post` cộng 1. Khởi tạo với giá trị 1 thì nó chạy như một "thẻ vào thớt": ai `sem_wait` được thì cầm thẻ, người sau chờ tới khi `sem_post`.

```cpp
#include <iostream>
#include <semaphore.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

struct Chung {                                     // (1) mọi thứ hai bên cùng thấy nằm trong một struct
    sem_t khoa;                                    //     "thẻ vào thớt" dùng được giữa các tiến trình
    long dem;
};

int main() {
    void* vung = mmap(nullptr, sizeof(Chung), PROT_READ | PROT_WRITE,
                      MAP_SHARED | MAP_ANONYMOUS, -1, 0);       // (2) vùng nhớ chung, con thừa hưởng qua fork
    if (vung == MAP_FAILED) return 1;
    Chung* c = static_cast<Chung*>(vung);
    c->dem = 0;
    if (sem_init(&c->khoa, 1, 1) == -1) return 1;   // (3) tham số giữa = 1: chia sẻ giữa TIẾN TRÌNH; giá trị đầu 1

    pid_t pid = fork();                             // (4)
    if (pid == -1) return 1;
    for (int i = 0; i < 100000; ++i) {              // cả cha lẫn con đều chạy vòng này
        sem_wait(&c->khoa);                         // (5) xin thẻ
        ++c->dem;                                   // (6) vùng găng giữa HAI tiến trình
        sem_post(&c->khoa);                         // (7) trả thẻ
    }
    if (pid == 0) return 0;                         // (8) con xong phần mình

    waitpid(pid, nullptr, 0);
    std::cout << "mong doi 200000, thuc te " << c->dem << "\n";
    sem_destroy(&c->khoa);
    munmap(vung, sizeof(Chung));
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | Nhân cấp một vùng cỡ `sizeof(Chung)`, ánh xạ vào bản đồ của cha | `[khoa \| dem]` ở địa chỉ minh họa `0x7f00` |
| (3) | Khởi tạo semaphore nằm **trong** vùng chung, giá trị 1, đánh dấu "dùng giữa tiến trình" | `khoa = 1`, `dem = 0` |
| (4) | `fork`: con thừa hưởng ánh xạ, **cùng vùng RAM** (không phải bản sao) | cha và con cùng trỏ `0x7f00` |
| (5)-(8) | Mỗi vòng: ai xin được thẻ (`khoa` 1 → 0) thì tăng `dem`, rồi trả (0 → 1). Con thoát, cha `waitpid` rồi đọc `dem` | một bên một lúc ở (6); cuối `dem = 200000` |

**Kết quả khi chạy** (nhiều lần liền đều như nhau; cũng đúng khi biên dịch `-O2`):

```text
mong doi 200000, thuc te 200000
```

Hai **Thử thay đổi** mình đã chạy.

- **Xóa hai dòng (5) và (7)** (không đồng bộ), `-O0`: năm lần ra `109974`, `110712`, `109952`, `110090`, `110072` (mong đợi 200000; máy bạn ra số khác). Mất gần nửa vì hai tiến trình đọc-sửa-ghi chồng lên nhau. Với `-O2` bản không khóa này ra đúng 200000 cả năm lần mình chạy, giống hiện tượng ở Bài 25: **ra đúng không chứng minh chương trình đúng**.
- **Đổi (3) thành `sem_init(&c->khoa, 0, 1)`** (không nói "dùng giữa tiến trình"): biên dịch sạch, nhưng mình chạy 20 lần với `timeout 3` thì **cả 20 lần treo** quá 3 giây; chạy lại 60 lần thì 57 lần treo, 3 lần xong bình thường. Đây là lỗi kiểu "lúc treo lúc không", rất khó gỡ.

Vì sao treo? Semaphore/mutex "riêng một tiến trình" cài đặt cách chờ và đánh thức dựa trên giả định mọi bên **chung một không gian địa chỉ** (như luồng). Khi hai tiến trình dùng nó, cách đánh thức đó có thể không tới được bên đang ngủ; tài liệu của POSIX cũng chỉ bảo đảm khi bạn khai báo "chia sẻ giữa tiến trình". Mình chỉ khẳng định điều đã đo: bỏ khai báo thì hỏng.

### 4. Vì sao không nhét `std::mutex` thường vào shared memory

Cám dỗ: `struct Chung { std::mutex khoa; long dem; };` đặt vào vùng chung. Đừng. Lý do xếp từ chắc nhất:

1. **Chuẩn C++ không có khái niệm nhiều tiến trình.** Nó chỉ nói về luồng trong một chương trình; `std::mutex` giữa hai tiến trình nằm ngoài những gì chuẩn bảo đảm.
2. Trên Linux với libstdc++, `std::mutex` bọc một `pthread_mutex_t` **mặc định**, tức loại "riêng một tiến trình" (mình kiểm: `sizeof(std::mutex)` bằng `sizeof(pthread_mutex_t)` là 40 byte, các byte giống hệt `PTHREAD_MUTEX_INITIALIZER`, và `native_handle()` trỏ ngay vào đối tượng). Mutex dùng giữa tiến trình phải được khởi tạo với thuộc tính **`PTHREAD_PROCESS_SHARED`** (mục 💻 A).
3. Mỗi tiến trình tự chạy hàm tạo/hàm hủy của đối tượng, dễ khởi tạo lại hay hủy một mutex đang được bên kia giữ.

Mình đã thử thật: đặt `std::mutex` trong vùng `MAP_SHARED | MAP_ANONYMOUS`, cha và con mỗi bên khóa-tăng-nhả 100000 lần. Chạy 20 lần: **cả 20 lần** chương trình in `Assertion `mutex->__data.__owner == 0' failed.` từ `pthread_mutex_lock` (glibc tự kiểm tra thấy trạng thái mutex vô lý) rồi dừng. Với số vòng lớn hơn, mình từng thấy cả tổng sai, treo, lẫn core dump. **Hành vi không xác định**, không phải "chậm hơn".

Nếu một tiến trình **chết giữa lúc cầm khóa** trong vùng chung, bên kia chờ mãi; POSIX có mutex "robust" (`PTHREAD_MUTEX_ROBUST`) để phát hiện, bài chỉ nhắc tên.

## 💻 Ví dụ code

### A. `shm_open` + `mutex` dùng giữa tiến trình

Vùng chung **có tên** cho tiến trình không quan hệ cha-con gặp nhau. Ba bước: `shm_open("/ten", cờ, quyền)` tạo/mở một "tệp" nằm trong bộ nhớ (Linux: thư mục `/dev/shm`) và trả fd (cờ `O_CREAT | O_EXCL | O_RDWR` = tạo mới, báo lỗi nếu tên đã tồn tại, mở đọc và ghi; quyền `0600` = chủ sở hữu đọc ghi, người khác không); `ftruncate(fd, kích_thước)` đặt cỡ cho vùng mới tạo; `mmap(..., MAP_SHARED, fd, 0)` ánh xạ nó vào bản đồ. Hết việc thì `shm_unlink` xóa tên. Mutex kiểu C khởi tạo qua một "phiếu thuộc tính": `pthread_mutexattr_init` tạo phiếu, `pthread_mutexattr_setpshared` ghi vào phiếu "dùng giữa tiến trình", `pthread_mutex_init` đọc phiếu để dựng mutex. `access(đường_dẫn, F_OK)` trả `0` nếu tệp tồn tại (ta dùng để xem tên có nằm trong `/dev/shm` không). Dưới đây cha tạo và khởi tạo; **con mở lại bằng tên** như một tiến trình lạ.

Trên máy mình (glibc 2.35) không cần thêm `-lrt` khi biên dịch; trên glibc cũ hơn có thể phải thêm `-lrt` để liên kết `shm_open`.

```cpp
#include <fcntl.h>
#include <iostream>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

struct Chung {                                      // chỉ dữ liệu thô: không con trỏ, không std::string/vector
    pthread_mutex_t khoa;                           // mutex kiểu C của POSIX
    long dem;
};

const char* TEN = "/bai49_demo";                    // (1) tên bắt đầu bằng '/'

Chung* mo_vung(bool tao) {
    int fd = shm_open(TEN, tao ? (O_CREAT | O_EXCL | O_RDWR) : O_RDWR, 0600);   // (2) mở theo TÊN
    if (fd == -1) return nullptr;
    if (tao && ftruncate(fd, sizeof(Chung)) == -1) return nullptr;              // (3) mới tạo: đặt kích thước
    void* p = mmap(nullptr, sizeof(Chung), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);   // (4)
    close(fd);                                       // (5) fd không cần nữa, ánh xạ vẫn còn
    return p == MAP_FAILED ? nullptr : static_cast<Chung*>(p);
}

int main() {
    shm_unlink(TEN);                                 // dọn nếu lần chạy trước bỏ sót
    Chung* c = mo_vung(true);
    if (!c) return 1;
    pthread_mutexattr_t thuoc;
    pthread_mutexattr_init(&thuoc);
    pthread_mutexattr_setpshared(&thuoc, PTHREAD_PROCESS_SHARED);   // (6) mutex dùng được giữa các tiến trình
    pthread_mutex_init(&c->khoa, &thuoc);
    pthread_mutexattr_destroy(&thuoc);
    c->dem = 0;

    pid_t pid = fork();
    if (pid == -1) return 1;
    if (pid == 0) {                                  // (7) con mở lại vùng bằng TÊN, như một tiến trình lạ
        Chung* d = mo_vung(false);
        if (!d) return 1;
        for (int i = 0; i < 100000; ++i) {
            pthread_mutex_lock(&d->khoa);
            ++d->dem;
            pthread_mutex_unlock(&d->khoa);
        }
        return 0;
    }
    for (int i = 0; i < 100000; ++i) {
        pthread_mutex_lock(&c->khoa);
        ++c->dem;
        pthread_mutex_unlock(&c->khoa);
    }
    waitpid(pid, nullptr, 0);
    std::cout << "mong doi 200000, thuc te " << c->dem << "\n";
    std::cout << "ten co trong /dev/shm? " << (access("/dev/shm/bai49_demo", F_OK) == 0) << "\n";   // (8)
    pthread_mutex_destroy(&c->khoa);
    munmap(c, sizeof(Chung));
    shm_unlink(TEN);                                 // (9) xóa tên; quên thì vùng còn mãi tới khi khởi động lại
    std::cout << "sau shm_unlink, con ten? " << (access("/dev/shm/bai49_demo", F_OK) == 0) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (2), (3) | Cha tạo "tệp" `/bai49_demo` trong `/dev/shm`, đặt cỡ `sizeof(Chung)` | vùng toàn số 0 |
| (4)-(6) | Cha ánh xạ vùng, đóng fd, khởi tạo mutex với thuộc tính "dùng giữa tiến trình" | cha có con trỏ `c`; `khoa` mở, `dem = 0` |
| (7) | Con gọi lại `mo_vung(false)`: mở theo tên, ánh xạ vào bản đồ của con (con trỏ `d` có thể khác `c`) | cùng RAM, hai con trỏ |
| vòng `for` | Hai bên khóa, tăng, nhả | một bên một lúc |
| (8), (9) | Tên còn trong `/dev/shm` tới khi `shm_unlink` | dòng 1 in `1`, dòng 2 in `0` |

**Kết quả khi chạy** (ba lần liền đều như nhau; sạch khi `-O2`):

```text
mong doi 200000, thuc te 200000
ten co trong /dev/shm? 1
sau shm_unlink, con ten? 0
```

**Thử thay đổi: xóa dòng (6)** (mutex mặc định, không "dùng giữa tiến trình"). Mình chạy 20 lần với `timeout 3`: cả 20 lần `pthread_mutex_lock` báo `Assertion ... __owner == 0' failed` và dừng (ở một loạt thử trước đó mình cũng thấy tổng ra `100000` thay vì `200000`, và có lần ra đúng). Cách hỏng đổi theo lần chạy: đúng là hành vi không xác định.

### B. Vùng chung không chứa con trỏ

Mỗi tiến trình ánh xạ vùng chung ở **địa chỉ ảo của riêng nó**, nên con trỏ ghi trong vùng chung (tới nút kế, tới chuỗi, tới hàm ảo) chỉ đúng với tiến trình đã ghi nó. Vì vậy vùng chung chỉ nên chứa **dữ liệu thô** (số, mảng, `struct` toàn số), không `std::string`, `std::vector`, hay lớp có `virtual` (chúng giữ con trỏ vào heap riêng của mỗi tiến trình). Thứ thay con trỏ là **độ lệch**: "cách đầu vùng bao nhiêu byte".

Mình đã chạy một chương trình nhỏ ánh xạ **cùng một vùng `shm_open` hai lần** trong một tiến trình (giống hai tiến trình mỗi bên ánh xạ một lần), được hai con trỏ `a` và `b`. Kết quả: `a != b` (hai địa chỉ ảo khác nhau, cùng một RAM). Bên A dựng hai nút `{10, tiep = sizeof(Nut)}` và `{20, tiep = -1}` với `tiep` là **độ lệch tính bằng byte**; bên B đi theo độ lệch từ **đầu vùng của chính B** (`b + x->tiep`) và đọc đúng `10 -> 20`. Nếu `tiep` lưu địa chỉ thật của nút kế, B đi theo sẽ rơi vào địa chỉ của A, vốn không phải nút nào trong bản đồ của B.

### C. Khi nào shared memory thật sự nhanh hơn pipe

"Shared memory nhanh nhất" đúng với **dữ liệu lớn, đồng bộ thưa**. Mình đo bằng chương trình riêng (không đưa vào bài, số đo không ổn định): cha gửi 128 MiB sang con, một lần qua pipe, một lần qua **vòng đệm 8 ô** trong shared memory, chia khúc 4096 hoặc 65536 byte. Vòng đệm dùng hai semaphore dùng giữa tiến trình: `trong` (đếm ô trống, đầu = 8) và `day` (đếm ô đầy, đầu = 0).

```text
cha:  lặp mỗi khúc:  sem_wait(trong); memcpy(vào ô k); sem_post(day);
con:  lặp mỗi khúc:  sem_wait(day);   đọc thẳng ô k;   sem_post(trong);
(k đi vòng 0..7; pipe thì cha write(), con read() cùng cỡ khúc)
```

Kết quả là tỉ lệ thời gian pipe/shm (lớn hơn 1 là shm nhanh hơn), một lần thật, `-O0`: khúc 4096 byte ra `0.91`, khúc 65536 byte ra `3.60`. Năm lần liền, khúc 65536 byte nằm khoảng `3.5` đến `3.8` (shm nhanh hơn pipe cỡ 3 đến 4 lần), còn khúc 4096 byte nằm khoảng `0.6` đến `1.2`: **shm không nhanh hơn**. Số đổi theo máy và `-O`.

Vì sao: pipe tốn hai lần chép qua nhân và một lời gọi hệ thống mỗi khúc; shm bỏ được lần chép ra và lời gọi chuyển dữ liệu, nhưng **vẫn phải đồng bộ mỗi khúc** (`sem_wait`/`sem_post` có thể vào nhân khi phải chờ). Khúc nhỏ thì chi phí đồng bộ nuốt hết phần lợi. Bài học: lợi thế của shm nằm ở **ít lần đồng bộ trên mỗi byte dữ liệu**; gửi vài tin nhỏ thì shm không đáng độ phức tạp.

### D. Message queue POSIX và UNIX domain socket

**Message queue** (hàng đợi thông điệp) là hàng đợi do nhân giữ, mỗi phần tử là **một thông điệp nguyên vẹn** có kèm **độ ưu tiên**, khác pipe (dòng byte không ranh giới). API: `mq_open("/ten", ...)`, `mq_send(q, dữ_liệu, độ_dài, ưu_tiên)`, `mq_receive(q, bộ_đệm, cỡ, &ưu_tiên)`, `mq_unlink`; tên bắt đầu bằng `/` như vùng chung nên tiến trình không quan hệ dùng chung được. Mình đã chạy một chương trình nhỏ gửi ba thông điệp `"thuong"` (ưu tiên 1), `"khan"` (ưu tiên 5), `"thuong 2"` (ưu tiên 1) rồi nhận ba lần, được:

```text
4 byte, uu tien 5: khan
6 byte, uu tien 1: thuong
8 byte, uu tien 1: thuong 2
```

`khan` gửi sau nhưng ra trước vì ưu tiên cao hơn; hai thông điệp cùng ưu tiên ra theo thứ tự gửi; mỗi `mq_receive` trả đúng một thông điệp với đúng độ dài lúc gửi (không bị gộp hay cắt như dòng byte). Bộ đệm nhận phải **không nhỏ hơn** `mq_msgsize` của hàng: mình thử bộ đệm 16 byte thì `mq_receive` trả -1 với `Message too long`. Trên máy này không cần `-lrt` (glibc cũ có thể cần). System V (`msgget`, `shmget`, `semget`) là họ API cũ làm việc tương tự; bài chỉ nhắc tên.

**UNIX domain socket** (`AF_UNIX`) dùng cùng API với socket TCP của [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md) (`read`/`write`, `bind`/`listen`/`accept`) nhưng chỉ cho tiến trình **trên cùng một máy**, địa chỉ là **đường dẫn tệp** thay vì IP:cổng. Hàm tiện nhất để thử là `socketpair(AF_UNIX, SOCK_STREAM, 0, cap)`: tạo sẵn **hai đầu nối của một ống hai chiều**; ghi vào `cap[0]` thì đọc ra ở `cap[1]` và ngược lại. Khác pipe (hai fd, mỗi fd một chiều), mỗi đầu của socketpair vừa đọc vừa ghi được.

Mình đã chạy: sau `fork`, cha `write "ping"` trên `cap[0]`, con `read` ở `cap[1]` rồi `write "pong"` trên **cùng** `cap[1]`, cha `read` trên `cap[0]` và in `cha nhan: pong`. Với `SOCK_STREAM` (dòng byte) chương trình thật phải lặp đọc cho đủ, như Bài 44.

UNIX so với TCP: UNIX **không đi qua ngăn xếp mạng**, không có cổng, kiểm soát truy cập bằng quyền tệp, và gửi được cả **fd** sang tiến trình khác (tên: `SCM_RIGHTS`); đổi lại không ra khỏi máy. Mình đo bằng chương trình riêng (không đưa vào bài) gửi 128 MiB, mỗi lần ghi 64 KiB: TCP trên `127.0.0.1` chậm hơn UNIX socket cỡ **1.4 đến 1.8 lần** (bốn lần đo, đổi theo máy). Dùng TCP khi hai bên có thể **khác máy** (hoặc có thể đổi sang khác máy sau này mà không sửa code); cùng máy thì UNIX socket thường đủ.

### E. Signal: chuông cửa, và luật của handler

**Signal** (tín hiệu) là một con số nhỏ hệ điều hành "đẩy" vào tiến trình, gửi bằng `kill(pid, số)` hay do chính hệ điều hành gửi (như `SIGSEGV` ở [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)). Mỗi tín hiệu có hành vi mặc định (thường là **giết tiến trình**); bạn có thể đăng ký một **handler** (hàm xử lý) để thay. Các tín hiệu hay gặp:

| Tín hiệu | Ai gửi / ý nghĩa | Bắt được? |
|---|---|---|
| `SIGINT` | Bấm Ctrl+C: "dừng đi" | có |
| `SIGTERM` | `kill pid` mặc định: "xin dừng, tự dọn rồi thoát" | có |
| `SIGKILL` | `kill -9`: giết ngay | **không** (mình chạy `sigaction`: trả -1, `Invalid argument`) |
| `SIGCHLD` | tiến trình con vừa dừng/chết | có (mặc định bỏ qua) |
| `SIGUSR1`, `SIGUSR2` | dành cho ứng dụng tự định nghĩa | có |
| `SIGPIPE` | ghi vào ống/socket không còn người đọc | có (mặc định giết) |

**Luật của handler.** Handler có thể ngắt chương trình **ở bất cứ lệnh nào**, kể cả giữa chừng `malloc` hay `printf`. Nếu handler gọi lại đúng thứ đang dở dang (ví dụ `malloc`, hàm cần khóa nội bộ), có thể treo hoặc làm hỏng dữ liệu. Chuẩn gọi các hàm dùng được trong handler là **async-signal-safe** ("an toàn khi bị tín hiệu xen vào"): danh sách ngắn, có `write`, `_exit`, và ghi vào biến kiểu **`volatile sig_atomic_t`**; **không** có `printf`, `malloc`, `new`, `std::cout`, `std::mutex`. Cách làm chuẩn: handler **chỉ đặt cờ**, vòng lặp chính kiểm cờ rồi làm việc thật.

Mình thử vi phạm luật: handler gọi `malloc`/`free` trong khi `main` cũng gọi chúng liên tục, tín hiệu đến mỗi 100 micro giây (không đưa mã vào bài vì nó là hành vi không xác định). Sáu lần chạy `-O0`: năm lần xong, **một lần crash** (`SIGSEGV`, mã 139). Đúng kiểu "lúc chạy được lúc hỏng": chạy trót lọt không chứng minh gì.

Chương trình dưới: con làm việc theo vòng lặp tới khi nhận `SIGTERM`; cha gửi tín hiệu rồi đọc cách con kết thúc. Mới:

- `sigaction` đăng ký handler (an toàn hơn `signal` cũ); `sa_handler` là hàm sẽ chạy; `sigemptyset` để danh sách tín hiệu bị chặn thêm trong lúc chạy handler là rỗng.
- `nanosleep` ngủ theo một `timespec{giây, nano giây}`; `kill(pid, SIGTERM)` gửi tín hiệu.
- `WIFEXITED`/`WEXITSTATUS` đọc "con thoát bình thường với mã nào"; `WIFSIGNALED`/`WTERMSIG` đọc "con bị tín hiệu nào giết".


```cpp
#include <csignal>
#include <iostream>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

volatile sig_atomic_t da_nhan_tin = 0;               // (1) cờ duy nhất handler được phép đụng

void xu_ly(int) {                                    // (2) handler: chạy xen vào bất cứ chỗ nào
    da_nhan_tin = 1;                                 // (3) chỉ đặt cờ rồi thoát
}

void ngu_ngan() {                                    // ngủ 5 ms; thấy tín hiệu thì thức sớm
    timespec t{0, 5 * 1000 * 1000};
    nanosleep(&t, nullptr);
}

int main() {
    struct sigaction sa{};
    sa.sa_handler = xu_ly;                           // (4) đăng ký handler cho SIGTERM TRƯỚC khi fork:
    sigemptyset(&sa.sa_mask);                        //     con thừa hưởng nên không có khe hở "chưa kịp đăng ký"
    if (sigaction(SIGTERM, &sa, nullptr) == -1) return 1;

    pid_t pid = fork();
    if (pid == -1) return 1;

    if (pid == 0) {                                  // CON: làm việc đến khi bị yêu cầu dừng
        while (!da_nhan_tin) {                       // (5) vòng làm việc: kiểm cờ mỗi vòng
            ngu_ngan();
        }
        std::cout << "con: nhan SIGTERM, don dep roi thoat\n";   // (6) in ở đây là an toàn: đang ở main, không ở handler
        return 7;
    }

    kill(pid, SIGTERM);                              // (7) cha gửi tín hiệu tới con
    int trang_thai = 0;
    waitpid(pid, &trang_thai, 0);
    if (WIFEXITED(trang_thai)) std::cout << "cha: con thoat voi ma " << WEXITSTATUS(trang_thai) << "\n";
    if (WIFSIGNALED(trang_thai)) std::cout << "cha: con bi giet boi tin hieu " << WTERMSIG(trang_thai) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Cờ `da_nhan_tin` |
|---|---|---|
| (4), (5) | Đăng ký `xu_ly` cho `SIGTERM`; `fork` sau đó nên con thừa hưởng; con lặp kiểm cờ, ngủ 5 ms | 0 |
| (7) | Cha gửi `SIGTERM`; nhân chạy `xu_ly` trong con (xen vào chỗ nó đang ở) | 0 → 1 (ở con) |
| (5), (6) | Vòng sau con thấy cờ bằng 1, thoát vòng lặp, in và trả mã 7 | 1 |
| cuối | Cha `waitpid`; `WIFEXITED` đúng, `WEXITSTATUS` là 7 | cha vẫn là 0 |

**Kết quả khi chạy** (năm lần liền như nhau; `-O0` lẫn `-O2`):

```text
con: nhan SIGTERM, don dep roi thoat
cha: con thoat voi ma 7
```

**Thử thay đổi: xóa dòng đăng ký `sigaction`** (con để mặc định). Mình đã chạy: con bị giết ngay, không in gì, cha in `cha: con bi giet boi tin hieu 15` (15 = số của `SIGTERM`). Khác biệt giữa "con tự dọn rồi thoát với mã 7" và "con bị giết giữa chừng" chính là handler.

Ba điều nữa về signal.

- Tín hiệu thường **không xếp hàng**: nhiều `SIGCHLD` đến gần nhau có thể gộp thành một lần, nên handler/vòng chính phải lặp `waitpid(-1, nullptr, WNOHANG)` cho tới khi hết con để dọn, không giả định một tín hiệu một con.
- `volatile sig_atomic_t` chỉ đúng cho giao tiếp giữa **handler và luồng bị nó ngắt**; cờ được **luồng khác** đọc ghi thì vẫn cần `std::atomic` ([Bài 28](../nhom-3-da-luong/28-atomic.md): `volatile` không đồng bộ luồng).
- Vòng `while (!co) pause();` có khe hở (tín hiệu đến giữa lúc kiểm cờ và lúc ngủ thì ngủ mãi); chương trình thật dùng `sigsuspend`, `signalfd` hoặc ống "tự gọi mình" (handler `write` một byte vào pipe), bài chỉ nhắc tên.

!!! info "Bạn biết Go?"
    Trong Go bạn không viết handler theo luật async-signal-safe: `signal.Notify(ch, syscall.SIGTERM)` biến tín hiệu thành **một giá trị gửi vào channel**, goroutine bình thường nhận và làm gì cũng được (runtime của Go lo phần chạy trong ngữ cảnh handler). Mình chạy thử: tự gửi `SIGTERM` cho chính mình rồi `<-ch` in `nhan terminated`. Ở C++ bạn có thể tự dựng lại kiểu đó bằng ống "tự gọi mình" (nói ở trên).

### F. Chọn cơ chế nào

Bảng tiêu chí:

| Cơ chế | Mô hình dữ liệu | Chiều | Cần quan hệ cha-con? | Tốc độ (cùng máy) | Độ khó | Ai xếp hàng/đồng bộ |
|---|---|---|---|---|---|---|
| pipe | dòng byte | một chiều | có (thừa hưởng fd) | vừa | thấp | nhân |
| FIFO | dòng byte | một chiều | không (có tên) | vừa | thấp | nhân |
| message queue | thông điệp + ưu tiên | hai chiều qua cùng hàng | không (có tên) | vừa | thấp tới vừa | nhân |
| UNIX socket | dòng byte (hoặc gói) | hai chiều | không (có đường dẫn) | vừa, cao hơn TCP loopback | vừa | nhân |
| TCP socket | dòng byte | hai chiều | không; **khác máy được** | thấp hơn UNIX socket | vừa | nhân |
| shared memory | vùng nhớ thô | hai chiều | không (có tên) hoặc có (ẩn danh) | **nhanh nhất khi khúc lớn, đồng bộ thưa** | **cao** | **chính bạn** |
| signal | một con số, không dữ liệu | một chiều | cần biết pid | nhanh, nhưng chỉ để báo hiệu | thấp, nhiều luật | nhân |

Cây quyết định:

```text
Hai bên có thể khác máy?            -> TCP socket
Chỉ cần báo "dừng / làm lại / có việc" (không kèm dữ liệu)? -> signal (rồi làm việc thật ở vòng chính)
Dữ liệu LỚN, trao đổi liên tục, hiệu năng quyết định?
                                    -> shared memory + semaphore/mutex dùng giữa tiến trình
                                       (và chia khúc đủ lớn để ít đồng bộ)
Cha-con, một chiều, đơn giản?       -> pipe
Hai chiều, nhiều bên, tiến trình không quan hệ? -> UNIX domain socket
Cần thông điệp nguyên vẹn + ưu tiên?-> message queue
Còn lại / chưa chắc                 -> UNIX socket hoặc pipe trước, ĐO, rồi mới cân shared memory
```

Khi **không** nên dùng: shared memory cho vài tin nhỏ hiếm (mình đo khúc 4096 byte: không nhanh hơn pipe, mà phải tự đồng bộ); signal để chở dữ liệu (không chở được, và handler bị hạn chế nặng); pipe/UNIX socket khi hai việc thật ra chạy được như hai **luồng** trong một tiến trình, nơi bộ nhớ chung sẵn có (đổi lại mất cách ly lỗi, [Bài 47](47-tien-trinh-vs-luong.md)); TCP khi cả hai bên chắc chắn ở cùng một máy và hiệu năng quan trọng.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Hai tiến trình trao đổi lượng dữ liệu lớn: cách nhanh nhất là gì?"
    Shared memory kèm đồng bộ (semaphore hoặc mutex đặt thuộc tính dùng giữa tiến trình). Nó bỏ được lần chép qua nhân và lời gọi hệ thống cho mỗi lần chuyển dữ liệu: pipe/socket chép dữ liệu vào nhân rồi chép ra. Mình đo 128 MiB, khúc 64 KiB, shm nhanh hơn pipe cỡ 3 đến 4 lần trên máy mình. Nhưng phải nói thêm hai điều: nó chỉ nhanh khi đồng bộ **thưa** (khúc 4 KiB mình đo ra xấp xỉ pipe), và nó khó hơn (tự đồng bộ, không con trỏ trong vùng chung, dọn tên bằng `shm_unlink`).

??? question "Vì sao không nhét `std::mutex` thường vào shared memory?"
    Chuẩn C++ không nói gì về nhiều tiến trình, và trên Linux `std::mutex` bọc một `pthread_mutex_t` mặc định (loại riêng một tiến trình). Mutex dùng giữa tiến trình phải khởi tạo với `PTHREAD_PROCESS_SHARED`. Mình thử thật: bỏ thuộc tính đó thì `pthread_mutex_lock` báo assertion ở cả 20 lần chạy; ở số vòng khác còn thấy tổng sai và treo. Cũng đừng đặt vào vùng chung thứ có con trỏ nội bộ hay hàm hủy riêng mỗi tiến trình tự chạy.

??? question "Pipe và socket khác nhau thế nào? Khi nào chọn cái nào?"
    Pipe: một chiều, hai fd, hai bên thường phải có quan hệ cha-con (thừa hưởng fd) hoặc dùng FIFO có tên; đơn giản. Socket: hai chiều trên một fd, có tên (đường dẫn hoặc IP:cổng), nhiều client nối vào một server, TCP đi được qua máy khác. Cha-con một chiều, đơn giản thì pipe; cần hai chiều, nhiều client, hay có thể khác máy thì socket (UNIX socket nếu cùng máy). Cả hai đều là dòng byte, không có ranh giới thông điệp: bạn tự định khung (độ dài đi trước, như Bài 44).

??? question "Trong signal handler được làm gì?"
    Rất ít. Handler ngắt chương trình ở bất cứ lệnh nào nên chỉ gọi hàm async-signal-safe (`write`, `_exit`...) và ghi vào biến `volatile sig_atomic_t`. Không `printf`, `malloc`, `new`, `std::cout`, `std::mutex` (nếu chương trình đang giữ khóa đó dở thì handler chờ mãi hoặc làm hỏng dữ liệu). Mô hình chuẩn: handler đặt cờ, vòng lặp chính kiểm cờ rồi dọn dẹp và thoát. Cờ chỉ an toàn giữa handler và luồng bị nó ngắt; chia sẻ giữa nhiều luồng thì dùng `std::atomic`.

??? question "`SIGTERM` khác `SIGKILL` thế nào? Vì sao `kill -9` là phương án cuối?"
    `SIGTERM` là lời xin dừng: chương trình bắt được, tự lưu trạng thái, đóng kết nối, rồi thoát (mình chạy: con thoát mã 7 sau khi dọn). `SIGKILL` không bắt được, không chặn được (mình chạy `sigaction` trên nó: `Invalid argument`), nhân giết ngay nên không có cơ hội dọn dẹp: tệp tạm còn đó, khóa có thể còn bị giữ, shared memory còn nguyên tên. Vì vậy thử `SIGTERM` trước, `SIGKILL` khi chương trình không đáp lại.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên đóng đầu ống không dùng"
    Sau `fork` mỗi bên giữ cả hai đầu ống; quên đóng đầu ghi ở bên đọc là `read` không bao giờ thấy "hết dữ liệu" (mình đã chạy: treo, mã 124). Mỗi bên đóng đầu mình không dùng, và đóng đầu ghi khi gửi xong.

!!! warning "Lỗi 2: Dùng vùng chung mà không đồng bộ, hoặc đồng bộ bằng thứ không dùng được giữa tiến trình"
    Không khóa thì mất cỡ nửa lần tăng (mình đo `~110000` thay vì 200000); `std::mutex` thường hay `sem_init` với `pshared = 0` thì treo hoặc báo lỗi. Dùng `sem_t` với `pshared = 1` hoặc `pthread_mutex_t` với `PTHREAD_PROCESS_SHARED`, và nhớ `shm_unlink`: vùng nhớ có tên sống lâu hơn tiến trình, quên thì còn trong `/dev/shm` tới khi khởi động lại.

!!! warning "Lỗi 3: Đặt `std::string`, `std::vector` hay con trỏ vào vùng chung"
    Chúng giữ con trỏ trỏ vào heap hoặc địa chỉ ảo của riêng một tiến trình; bên kia đi theo con trỏ là rơi vào địa chỉ vô nghĩa (hành vi không xác định). Dùng dữ liệu thô và độ lệch thay con trỏ.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="49" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Đọc đoạn sau. Cha tạo `pipe(ong)`, rồi `fork`. Con chạy `while (read(ong[0], dem, 64) > 0) {...}`. Cha ghi một dòng, `close(ong[1])`, rồi `waitpid`. Con **không** gọi `close(ong[1])`. Chuyện gì xảy ra?

```text
cha:  write(ong[1], ...); close(ong[1]); waitpid(pid, ...);
con:  while (read(ong[0], dem, 64) > 0) { ... }   // không close(ong[1])
```

- Treo: con vẫn giữ một đầu ghi nên `read` chưa thấy hết dữ liệu
- Con đọc xong dòng đó rồi thoát vòng lặp, vì cha đã đóng đầu ghi của cha
- Con đọc đúng một lần rồi `read` trả -1, vì ống chỉ chở một lần ghi
- Con bị `SIGPIPE` giết ngay, vì phía cha đã đóng một đầu của ống

<p class="giai-thich" markdown>`read` chỉ trả 0 khi **mọi** bản của đầu ghi (ở cả cha lẫn con) đã đóng. Con thừa hưởng một bản đầu ghi nhờ `fork` và không đóng nên nhân vẫn coi là còn người có thể ghi, `read` chặn mãi, và cha thì đang `waitpid` chờ con. Việc cha đóng bản của cha là chưa đủ. Ống không giới hạn ở một lần ghi, và `SIGPIPE` là chuyện ghi vào ống không còn người đọc, không phải chuyện đọc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Tình huống: một tiến trình thu hình ảnh phải chuyển liên tục từng khung hình 2 MB sang tiến trình xử lý trên cùng máy, hàng trăm khung mỗi giây, hai tiến trình do hai nhóm viết, không cùng cha. Chọn phương án hợp lý nhất?

- Dùng signal, gửi `SIGUSR1` mỗi khung kèm nội dung khung hình
- Dùng pipe thường, nhanh nhất khi hai tiến trình không chung cha
- Dùng TCP trên `127.0.0.1` vì code đơn giản nhất và nhanh ngang shm
- Shared memory có tên (`shm_open`), vòng đệm, semaphore dùng chung

<p class="giai-thich" markdown>Dữ liệu lớn, liên tục, hiệu năng quyết định: shared memory bỏ được việc chép qua nhân cho mỗi khung hình, và `shm_open` có tên cho hai tiến trình lạ gặp nhau; vòng đệm cùng semaphore lo đồng bộ. Signal không mang dữ liệu nên không dùng chở khung hình. Pipe thường cần quan hệ cha-con để thừa hưởng fd, và cũng chép hai lần qua nhân. TCP loopback đơn giản nhưng vẫn chép qua nhân và đi qua cả ngăn xếp mạng (mình đo chậm hơn UNIX socket), nên không có lý do để nhanh ngang shared memory.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Tình huống: dịch vụ nền cần nhận lệnh "đọc lại cấu hình" từ người quản trị bằng lệnh `kill -HUP pid`, và việc đọc lại cấu hình gồm mở tệp, cấp phát chuỗi, ghi log. Thiết kế nào đúng?

- Viết toàn bộ việc đọc cấu hình ngay trong handler để phản hồi tức thì
- Handler chỉ đặt cờ; vòng lặp chính thấy cờ rồi mới đọc cấu hình
- Handler khóa một `std::mutex` rồi đọc cấu hình, để tránh data race
- Không dùng handler, vì `SIGHUP` không bắt được như `SIGKILL`

<p class="giai-thich" markdown>Mở tệp, cấp phát, ghi log đều không async-signal-safe: handler ngắt chương trình ở lệnh bất kỳ, có thể giữa lúc `malloc` đang giữ khóa nội bộ. Nên handler chỉ đặt cờ và việc thật làm ở vòng chính. Khóa `std::mutex` trong handler còn nguy hiểm hơn: nếu luồng bị ngắt đang cầm chính mutex đó, nó tự chờ mình mãi. Còn `SIGHUP` bắt được bình thường; chỉ `SIGKILL` và `SIGSTOP` là không bắt được.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. `Chung` nằm trong vùng `mmap(MAP_SHARED | MAP_ANONYMOUS)` và cha lẫn con đều gọi `ham()` nhiều lần sau `fork`. Lỗi nằm ở đâu?

```text
struct Chung { std::mutex khoa; long dem; };
void ham(Chung* c) { std::lock_guard<std::mutex> g(c->khoa); ++c->dem; }
```

- `lock_guard` không khóa được mutex nằm trong vùng chung nên `++` luôn lẫn nhau
- `dem` kiểu `long` không đủ rộng cho shared memory, phải dùng kiểu `int`
- Mutex thường không dùng được giữa tiến trình; cần `PTHREAD_PROCESS_SHARED`
- Phải gọi `fork` trước `mmap` thì con mới thấy được mutex trong vùng chung

<p class="giai-thich" markdown>Chuẩn không bảo đảm gì về `std::mutex` giữa các tiến trình, và nó bọc mutex loại "riêng một tiến trình"; mình chạy thì `pthread_mutex_lock` báo assertion, đôi khi tổng sai hoặc treo. Mutex dùng giữa tiến trình cần thuộc tính `PTHREAD_PROCESS_SHARED` (hoặc dùng `sem_t` có `pshared = 1`). `lock_guard` vẫn gọi `lock()` bình thường, vấn đề nằm ở loại mutex. Kiểu `long` không liên quan tới shared memory. Còn `mmap` ẩn danh phải đứng **trước** `fork` thì con mới thừa hưởng, đúng ngược lại với phương án bảo gọi `fork` trước `mmap`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn sau. Sau `fork`, con chạy vòng `while (!xong) { lam_viec(); }`, `xong` khai báo `volatile sig_atomic_t xong = 0;`, handler `SIGTERM` chỉ làm `xong = 1;`. Cha gửi `SIGTERM` cho con. Điều nào đúng?

```text
volatile sig_atomic_t xong = 0;
void h(int) { xong = 1; }
// con: while (!xong) { lam_viec(); }   // sau khi đã sigaction(SIGTERM, h)
```

- Con không bao giờ dừng, vì handler chạy ở luồng khác nên con không thấy `xong`
- Con dừng ngay giữa chừng `lam_viec()`, vì tín hiệu hủy hàm đang chạy
- Cha thấy `xong = 1` ở biến của cha, vì `xong` là biến chung của cả hai
- Con dừng sau khi `lam_viec()` hiện tại xong, vì cờ kiểm ở đầu vòng sau

<p class="giai-thich" markdown>Handler chạy trong chính tiến trình con (xen vào luồng đang chạy), đặt cờ; `volatile sig_atomic_t` bảo đảm lần đọc sau thấy giá trị đó. Vòng lặp chỉ kiểm cờ ở đầu mỗi vòng, nên `lam_viec()` đang dở vẫn chạy xong. Tín hiệu không hủy hàm đang chạy. Sau `fork` con có bản sao riêng của `xong`, nên cha không thấy gì. Và handler không chạy ở "luồng khác": nó ngắt chính luồng của con.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Bạn đo: gửi 128 MiB giữa hai tiến trình, mỗi lần chuyển một khúc **4 KiB** và đồng bộ bằng semaphore **mỗi khúc**. Shared memory so với pipe cho kết quả nào hợp lý?

- Xấp xỉ pipe, vì đồng bộ mỗi khúc nhỏ nuốt phần lợi do bỏ chép
- Nhanh hơn pipe nhiều lần, vì shared memory luôn nhanh hơn mọi cách khác
- Chậm hơn pipe cả chục lần, vì shared memory phải ánh xạ lại mỗi khúc
- Nhanh hơn pipe nhiều lần, vì semaphore dùng chung không bao giờ vào nhân

<p class="giai-thich" markdown>Lợi thế của shm là bỏ lần chép qua nhân và lời gọi chuyển dữ liệu, nhưng khúc 4 KiB nghĩa là phải đồng bộ rất nhiều lần, và mỗi lần chờ có thể vào nhân. Mình đo ra tỉ lệ pipe/shm trong khoảng 0.6 đến 1.2, tức xấp xỉ nhau, còn khúc 64 KiB mới cho 3 đến 4 lần. Nói "luôn nhanh hơn" là bỏ quên chi phí đồng bộ. Ánh xạ chỉ làm một lần chứ không lặp mỗi khúc. Và semaphore vẫn có thể vào nhân khi phải chờ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Tình huống: một tiến trình điều phối cần nhận từng **lệnh** (vài chục byte, mỗi lệnh có độ ưu tiên) từ nhiều tiến trình khác nhau không cùng cha, mỗi lệnh phải đến nguyên vẹn, lệnh khẩn xử lý trước. Cơ chế nào khớp nhất?

- Một pipe duy nhất, mọi tiến trình cùng ghi vào, vì pipe tự xếp theo độ dài lệnh
- Shared memory không đồng bộ, vì chỉ cần ghi nhanh vào vùng chung
- Message queue POSIX có tên, vì ranh giới thông điệp và ưu tiên có sẵn
- Signal `SIGUSR1`, vì tín hiệu mang được cả nội dung lệnh

<p class="giai-thich" markdown>Cần ba thứ: thông điệp nguyên vẹn, ưu tiên, và tiến trình không quan hệ gặp nhau; message queue POSIX có đủ cả ba (tên chung, mỗi lần nhận một thông điệp, độ ưu tiên). Pipe là dòng byte không ranh giới và không có ưu tiên, nên các lệnh dễ bị trộn hoặc gộp. Shared memory mà không đồng bộ thì là data race. Signal chỉ mang số hiệu tín hiệu, không chở nội dung lệnh.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Tiến trình có **bản đồ địa chỉ ảo riêng**, nên không thấy bộ nhớ nhau và không gửi con trỏ được; mọi IPC nhờ hệ điều hành, chia ba họ: nhân chép hộ (pipe, FIFO, socket, message queue), cùng nhìn một vùng nhớ (shared memory), và gõ cửa (signal).
2. `pipe` + `fork`: dòng byte một chiều (mình đo bộ đệm 65536 byte); **mỗi bên phải đóng đầu ống mình không dùng**, nếu không `read` không bao giờ thấy hết dữ liệu (mình chạy: treo, mã 124); FIFO là pipe có tên cho tiến trình không quan hệ.
3. Shared memory (`mmap`, hoặc `shm_open` + `ftruncate` + `mmap`) không có ai xếp hàng hộ: phải đồng bộ bằng `sem_t` (`pshared = 1`) hoặc `pthread_mutex` với `PTHREAD_PROCESS_SHARED`; **không** dùng `std::mutex` thường (mình chạy: assertion/treo), không để con trỏ/`std::string` trong vùng chung (dùng độ lệch), và nhớ `shm_unlink`.
4. Shared memory nhanh nhất khi **khúc lớn, đồng bộ thưa** (mình đo 3 đến 4 lần so với pipe ở khúc 64 KiB) nhưng không hơn pipe ở khúc 4 KiB; message queue POSIX cho thông điệp nguyên vẹn + ưu tiên; UNIX domain socket hai chiều, cùng máy, nhanh hơn TCP loopback (mình đo 1.4 đến 1.8 lần), TCP khi có thể khác máy.
5. Signal chỉ báo hiệu: handler chỉ được đặt cờ `volatile sig_atomic_t` (không `printf`/`malloc`/mutex), việc thật làm ở vòng chính; `SIGKILL` không bắt được, `SIGCHLD` có thể gộp nên `waitpid(..., WNOHANG)` theo vòng lặp; chọn cơ chế theo mô hình dữ liệu, chiều, quan hệ cha-con, tốc độ, độ khó, và đo trước khi chọn shared memory.
