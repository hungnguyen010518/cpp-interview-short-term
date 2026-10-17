# Bài 48 — fork, exec, wait: sinh tiến trình con và dọn dẹp

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích `fork` **trả về hai lần** (0 ở con, pid của con ở cha, -1 khi lỗi), vì sao con có một **bản sao** bộ nhớ chứ không phải bộ nhớ chung, và **copy-on-write** (chỉ sao chép trang nhớ khi có bên ghi) với số đo thật.
    - Dùng `execvp` để thay "hình hài" tiến trình, `waitpid` + `WIFEXITED`/`WEXITSTATUS` để đọc mã thoát; hiểu vì sao hệ điều hành tách việc sinh con khỏi việc nạp chương trình mới.
    - Nhìn tận mắt **zombie** (`Z` trong `ps`) và **orphan** (con mồ côi được nhận nuôi), và biết cách phòng zombie.
    - Biết `fork` trong chương trình **đa luồng** là bẫy, file descriptor bị kế thừa và cờ `FD_CLOEXEC`, khi nào chọn `posix_spawn`/`system`; đếm được "`fork` 3 lần in mấy dòng".

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (tiến trình khác luồng), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến toàn cục, heap), [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) (mảng, chuỗi kiểu C), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`std::mutex`), [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) (`/proc/PID`), [Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md) (file descriptor, `errno`, `perror`), [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md) (tín hiệu). [Bài 47](47-tien-trinh-vs-luong.md) nói kỹ về không gian địa chỉ; ở đây chỉ nhắc phần cần dùng.

## 🧠 Câu chuyện mở đầu

Ta ở **tòa chung cư**: mỗi tiến trình là một căn hộ có tường riêng và khóa riêng. Muốn có người giúp việc, căn hộ gọi **`fork`**: ban quản lý **photocopy cả căn hộ** (đồ đạc, việc đang làm dở, cả trang sách đang đọc dở) sang một căn hộ mới. Từ đó hai căn hộ sống riêng: ai sửa đồ của mình, người kia không thấy.

Thường ta muốn căn hộ mới làm việc khác hẳn, nên chủ nó gọi **`exec`**: dọn sạch đồ cũ, bê đồ của chương trình khác vào, nhưng **vẫn là căn hộ số đó**. Còn **`wait`** là chủ nhà đợi con báo "tôi xong, kết quả là…" rồi ký giấy để ban quản lý xóa hồ sơ căn hộ con.

!!! info "Chỗ nào ví von photocopy không còn đúng?"
    Hệ điều hành **không** chép thật cả căn hộ ngay: hai bản dùng chung đồ cho tới khi ai đó sửa (mục 2). Và chỉ **một người ở** (luồng gọi `fork`) có bản sao, những thành viên khác của căn hộ gốc thì không (mục 6).

## 📖 Giải thích

### 1. `fork`: một lời gọi, hai lần trả về

`fork()` (thư viện `<unistd.h>` của hệ POSIX như Linux) tạo tiến trình **con** gần như giống hệt tiến trình **cha**: cùng mã, bản sao dữ liệu, cùng chỗ đang chạy dở. Cả hai chạy tiếp **từ dòng ngay sau `fork`**; con **không** chạy lại từ `main`. Điểm khác nhau là giá trị `fork` trả về:

| `fork()` trả về | Ai nhận | Nghĩa |
|---|---|---|
| `0` | tiến trình **con** | "tôi là con" |
| số dương | tiến trình **cha** | pid (số hiệu tiến trình) của con mới, để sau `wait` đúng nó |
| `-1` | cha (không có con) | lỗi, `errno` cho biết lý do |

Vài thứ mới trong đoạn dưới:

- `pid_t` là kiểu số nguyên chứa pid; `getpid()` là pid của mình, `getppid()` là pid của cha.
- `waitpid(kq, nullptr, 0)` bắt cha chờ con `kq` kết thúc (mục 3).
- `_exit(0)` kết thúc tiến trình ngay (khác `exit`, xem 💻 ví dụ 2).
- `std::perror` in lý do lỗi từ `errno` ([Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md)).
- `std::endl` xuống dòng **và** đẩy chữ ra ngay.
- `static_cast<const void*>(&x)` đổi địa chỉ của `x` sang kiểu "con trỏ không kiểu" để `std::cout` in nó thành số địa chỉ ([Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)).

```cpp
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>

int x = 10;                                          // biến toàn cục, trước fork

int main() {
    pid_t kq = fork();                               // (1) từ đây có HAI tiến trình, cùng chạy tiếp từ dòng (2)
    if (kq < 0) {                                    // (2) fork thất bại: không có con nào
        std::perror("fork");
        return 1;
    }
    if (kq == 0) {                                   // (3) nhánh của CON
        x = 99;                                      // (4) con sửa x của riêng nó
        std::cout << "[con] fork tra " << kq << ", pid = " << getpid()
                  << ", pid cua cha = " << getppid() << "\n"
                  << "      x = " << x << ", &x = " << static_cast<const void*>(&x) << std::endl;
        _exit(0);                                    // (5) con kết thúc tại đây
    }
    waitpid(kq, nullptr, 0);                         // (6) cha chờ con xong rồi mới tiếp
    std::cout << "[cha] fork tra " << kq << ", pid = " << getpid() << "\n"
              << "      x = " << x << ", &x = " << static_cast<const void*>(&x) << std::endl;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Hai tiến trình lúc này |
|---|---|---|
| (1) | Một tiến trình đi vào `fork`, hai tiến trình đi ra | cha: `kq = 270420`; con: `kq = 0` (số minh họa) |
| (2) | Cả hai kiểm `kq < 0`: không ai thấy lỗi | cả hai bỏ qua |
| (3)–(5) | Chỉ con vào nhánh này: sửa `x` bản của nó, in, `_exit` | con `x = 99`, cha `x = 10` |
| (6) | Cha chờ con thoát rồi in `x` của chính cha | cha vẫn `x = 10` |

**Kết quả khi chạy** (một lần chạy thật; pid và địa chỉ đổi theo lần chạy và theo máy):

```text
[con] fork tra 0, pid = 270420, pid cua cha = 270419
      x = 99, &x = 0x5f42a5c52010
[cha] fork tra 270420, pid = 270419
      x = 10, &x = 0x5f42a5c52010
```

`pid cua cha` của con đúng bằng `pid` của cha. Và **địa chỉ `&x` giống hệt nhau** ở hai bên mà `x` khác nhau (99 và 10). Địa chỉ in ra là **địa chỉ ảo**: số trong "bản đồ" riêng của từng tiến trình, mỗi tiến trình có bảng dịch riêng ra ô RAM thật. Cùng một số nhưng hai bản đồ trỏ tới hai chỗ khác nhau.

!!! warning "Hay nhầm: `fork` không tạo luồng và không chạy hàm nào"
    `fork` nhân đôi **cả tiến trình**, không "chạy một hàm ở nền" như `std::thread`. Cha và con chạy **song song**, thứ tự giữa hai bên không bảo đảm; muốn thứ tự (như ở dòng (6)) phải tự chờ bằng `waitpid`.

**`fork` trả `-1`** khi hệ điều hành không cho sinh thêm (hết bộ nhớ hay hết số tiến trình cho phép). Mình ép lỗi bằng `setrlimit(RLIMIT_NPROC, ...)` hạ giới hạn xuống 1 (người dùng thường): `fork` trả `-1`, `errno` là `EAGAIN` ("Resource temporarily unavailable"). Luôn kiểm `fork() < 0`: bỏ qua thì `kq == -1` rơi vào nhánh "cha" và cha tưởng đã có con để `waitpid`.

### 2. Copy-on-write: bản sao "ảo" cho tới khi có ai ghi

Nếu `fork` chép thật từng byte thì tiến trình 10 GB sinh con rất chậm, trong khi con thường `exec` ngay rồi vứt hết. Nên hai tiến trình **dùng chung các trang nhớ vật lý** (trang = khối nhớ thường 4096 byte), đánh dấu "chỉ đọc". Khi **một bên ghi** vào một trang, CPU báo **lỗi trang** (page fault), hệ điều hành mới **sao chép đúng trang ấy** cho bên ghi rồi cho ghi tiếp. Đó là **copy-on-write** (COW).

Hệ quả: `fork` rẻ hơn nhiều so với kích thước bộ nhớ (chỉ sao chép bảng ánh xạ trang, không sao chép dữ liệu) nhưng không miễn phí, chi phí vẫn tăng theo lượng bộ nhớ đang ánh xạ; và bên nào ghi càng nhiều trang thì RAM dùng thêm càng nhiều.

Mình đo bằng `getrusage` (trường `ru_minflt`: số lỗi trang nhẹ của tiến trình). Cha cấp 64 MiB (16384 trang) và chạm mọi trang; rồi `fork`; con ghi một byte vào **mỗi trang** và đếm lỗi trang phát sinh. Mốc so sánh: cha ghi lại chính vùng đó **trước** `fork`. Lõi chương trình:

```text
for (size_t i = 0; i < v.size(); i += 4096) v[i] = 1;   // ghi 1 byte vào mỗi trang
long loi = loiTrangSau - loiTrangTruoc;                  // getrusage(RUSAGE_SELF).ru_minflt, trước và sau vòng lặp
```

Kết quả thật (ba lần liền như nhau, cả khi thêm `-O2`): **con: 16384 lỗi trang, cha (trước fork): 0**. Mỗi trang con ghi lần đầu là một lần sao chép; cha ghi lên trang đã có sẵn thì không lỗi. Số cụ thể đổi theo máy (ví dụ khi hệ thống dùng trang nhớ lớn, "huge page"); cái mẫu "con nhiều lỗi, cha gần như không" mới đáng nhớ.

### 3. `waitpid` và mã thoát

Con kết thúc theo hai cách: **tự thoát** (`return` từ `main`, `exit`, `_exit`) kèm **mã thoát** (số 0–255, quy ước `0` là thành công), hoặc **bị tín hiệu giết** (như `SIGKILL`, `SIGSEGV` của [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)). Cha lấy kết quả bằng `waitpid(pid, &tt, 0)`: chờ con `pid` (hoặc `-1` = bất kỳ con nào), ghi vào `tt` một số nguyên **đóng gói** lý do kết thúc, trả pid con vừa xong (hoặc `-1` khi lỗi). Đừng đọc `tt` bằng mắt, hãy hỏi qua các macro ([Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) có nói macro):

| Macro | Hỏi gì | Ghi chú |
|---|---|---|
| `WIFEXITED(tt)` | con tự thoát? | kiểm trước tiên |
| `WEXITSTATUS(tt)` | mã thoát là mấy | **chỉ có nghĩa** khi `WIFEXITED` đúng |
| `WIFSIGNALED(tt)` | con bị tín hiệu giết? | khi không phải tự thoát |
| `WTERMSIG(tt)` | số tín hiệu | **chỉ có nghĩa** khi `WIFSIGNALED` đúng |

Tham số thứ ba `0` là chờ (chặn); `WNOHANG` thì không chờ, trả `0` nếu chưa có con nào xong. Khi hết con, `waitpid` trả `-1` với `errno == ECHILD` (ví dụ 1 ở 💻 chạy đủ cả ba trường hợp này).

!!! info "Bạn biết Go?"
    Go không cho `fork` trần: runtime Go luôn chạy nhiều luồng nên con sau `fork` không an toàn để chạy tiếp mã Go (mục 6). Go chỉ đưa ra **fork + exec gộp** (`os/exec`, bên dưới là `syscall.ForkExec`): `exec.Command("sh", "-c", "exit 3").Run()` ứng với fork + exec + wait. Mình đã chạy: lỗi trả về là `*exec.ExitError`, `ExitCode()` = `3`; lệnh không có thì `Run` trả `exec: "lenh_khong_ton_tai_123": executable file not found in $PATH`.

### 4. `execvp`: thay hình hài, giữ nguyên số căn hộ

`execvp(ten, argv)` **nạp một chương trình khác vào chính tiến trình đang gọi**: mã, heap, stack cũ bị bỏ, chương trình mới chạy từ đầu `main`. Thành công thì `execvp` **không bao giờ trả về** (không còn mã cũ để trả về); chỉ **thất bại** mới trả `-1` kèm `errno`. Có cả họ `execl`, `execv`, `execve`…; chữ `p` là tìm `ten` trong `PATH`, chữ `v` là đưa đối số qua một **mảng** (vector).

`argv` là mảng con trỏ tới chuỗi kiểu C ([Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)), **kết thúc bằng `nullptr`**, phần tử đầu theo quy ước là tên chương trình. Mỗi chuỗi dưới đây khai báo bằng mảng `char a0[] = "sh";` chứ không dùng thẳng chữ `"sh"`, vì `execvp` đòi `char*` ghi được còn chữ trần là `const char*`. `std::strerror(errno)` đổi mã lỗi `errno` thành câu chữ. Qua `exec` giữ nguyên: pid, cha, thư mục hiện hành, các **file descriptor còn mở** (mục 7). Mất: toàn bộ bộ nhớ và mọi luồng khác. Ta chứng minh "cùng pid": con in pid trước `exec`, rồi `exec` một `sh` in pid của chính nó (`$$`).

```cpp
#include <cerrno>
#include <cstring>
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>

// fork + execvp + waitpid; trả về mã thoát của chương trình mới
int chay(char* argv[]) {
    pid_t con = fork();
    if (con == 0) {
        std::cout << "[con] truoc exec, pid = " << getpid() << std::endl;
        execvp(argv[0], argv);                       // (1) thay hình hài; thành công thì không trở lại
        std::cerr << "[con] execvp loi: " << std::strerror(errno) << std::endl;   // (2) chỉ tới đây khi THẤT BẠI
        _exit(127);                                  // (3) quy ước: 127 = không chạy được lệnh
    }
    int tt = 0;
    waitpid(con, &tt, 0);
    return WEXITSTATUS(tt);
}

int main() {
    char a0[] = "sh";
    char a1[] = "-c";
    char a2[] = "echo \"[sh] sau exec, pid = $$\"";  // $$ là pid của chính sh
    char* argvSh[] = {a0, a1, a2, nullptr};          // (4) argv: mảng con trỏ, kết thúc bằng nullptr
    int ma1 = chay(argvSh);
    std::cout << "sh thoat voi ma " << ma1 << std::endl;

    char b0[] = "lenh_khong_ton_tai_123";
    char* argvSai[] = {b0, nullptr};
    int ma2 = chay(argvSai);                         // (5)
    std::cout << "lenh sai thoat voi ma " << ma2 << std::endl;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Tiến trình con |
|---|---|---|
| (1) lần 1 | `execvp("sh", ...)` thành công: thân xác `sh` thay vào, `echo` in pid của `sh` | pid không đổi, mã cũ biến mất |
| (2),(3) lần 1 | không bao giờ chạy tới | |
| (1) lần 2 | không có lệnh đó trong `PATH`: `execvp` trả `-1` | vẫn là thân xác cũ |
| (2),(3) lần 2 | in lý do, `_exit(127)`; cha đọc 127 ở (5) | thoát mã 127 |

**Kết quả khi chạy** (pid khác ở máy bạn; chỉ cần hai số trước và sau `exec` **bằng nhau**):

```text
[con] truoc exec, pid = 272331
[sh] sau exec, pid = 272331
sh thoat voi ma 0
[con] truoc exec, pid = 272332
[con] execvp loi: No such file or directory
lenh sai thoat voi ma 127
```

**Vì sao tách `fork` và `exec`?** Giữa hai bước, con còn là bản sao chạy mã của cha, nên nó tự sửa môi trường quanh mình rồi mới đổi hình hài: đóng hoặc chuyển hướng file descriptor (nền tảng của `>` và `|` trong shell), đổi thư mục, hạ quyền. Cái giá là khoảng giữa đó nguy hiểm khi có đa luồng (mục 6), nên có `posix_spawn` (mục 8).

### 5. Zombie và orphan

Khi con chết, hệ điều hành **chưa xóa hẳn** nó: phải giữ mẩu hồ sơ (pid, mã thoát) cho tới khi cha `wait` để đọc. Con đã chết mà chưa được thu dọn gọi là **zombie** (xác sống). Nó không tốn CPU hay bộ nhớ đáng kể, nhưng **chiếm một ô pid**; đủ nhiều thì có thể hết pid hoặc chạm giới hạn số tiến trình, và `fork` lỗi `EAGAIN`.

Trong `ps`, zombie có trạng thái `Z` và lệnh ghi `<defunct>`. Chương trình dưới để con chết, cha **chưa** `wait`, hỏi `ps`, rồi `wait` và hỏi lại (`usleep(n)` ngủ `n` micro giây; `std::system` chạy một lệnh shell, mục 8; `std::flush` đẩy chữ ra để không bị `ps` in chen):

```cpp
#include <cstdlib>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    pid_t con = fork();
    if (con == 0) _exit(0);                          // (1) con chết ngay
    usleep(200 * 1000);                              // (2) cha ngủ 0,2 giây, CHƯA gọi wait

    std::string lenh = "ps -o stat= -p " + std::to_string(con);   // (3) hỏi ps trạng thái của con
    std::cout << "truoc wait, ps cho biet trang thai: " << std::flush;
    std::system(lenh.c_str());                       // (4) ps in "Z"

    waitpid(con, nullptr, 0);                        // (5) cha thu dọn: hồ sơ của con bị xóa
    std::cout << "sau wait, ps cho biet: " << std::flush;
    std::system((lenh + " || echo '(khong tim thay tien trinh)'").c_str());   // (6)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Con |
|---|---|---|
| (1)–(2) | Con thoát ngay; cha ngủ, chưa `wait` | đã chết, hồ sơ còn: zombie |
| (3)–(4) | `ps -o stat= -p <pid con>` in trạng thái | `Z` |
| (5)–(6) | `waitpid` đọc kết quả, hồ sơ bị xóa; `ps` không thấy nữa | biến mất |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
truoc wait, ps cho biet trang thai: Z
sau wait, ps cho biet: (khong tim thay tien trinh)
```

Để thấy zombie sống lâu, mình chạy chương trình `if (fork() == 0) _exit(0); sleep(30);` ở nền (cha ngủ, không `wait`) rồi gõ `ps` ở shell khác. Thật trên máy mình:

```text
$ ps -o pid,ppid,stat,cmd --ppid <pid cha>
 194799  194797 ZN   [z] <defunct>
$ kill -9 194799          # bắn thẳng vào zombie: vẫn còn nguyên
$ kill 194797             # tắt CHA: zombie biến mất
```

Chữ `Z` là zombie (`N` chỉ là mức ưu tiên thấp của môi trường mình chạy, máy bạn có thể chỉ thấy `Z`). Hai bài học: **`kill -9` không xóa được zombie** (nó chết rồi, chỉ còn hồ sơ chờ cha đọc), và zombie chỉ hết khi cha `wait` hoặc khi **cha cũng chết**.

**Phòng zombie** là mỗi con phải có một đường `waitpid`. Chương trình đơn giản thì chờ ngay như trên. Server không thể đứng chờ chặn, nên nhân gửi cho cha tín hiệu **`SIGCHLD`** mỗi khi một con dừng hoặc chết (cách bắt tín hiệu ở [Bài 49](49-ipc.md)); cha nhận được thì gọi `waitpid(-1, nullptr, WNOHANG)` **trong vòng lặp** tới khi nó trả `0` hoặc `-1`, vì nhiều `SIGCHLD` đến gần nhau có thể gộp thành một.

**Orphan** (mồ côi) là ngược lại: **cha chết trước, con còn sống**. Con không bị giết; hệ điều hành gán nó cho một tiến trình khác nhận nuôi: thường là `init` (tiến trình đầu tiên của hệ thống, pid 1), hoặc một **subreaper**, tiến trình tự đăng ký làm người nhận nuôi trong cây của nó bằng `prctl(PR_SET_CHILD_SUBREAPER, 1)` (Linux). Người nhận nuôi `wait` con mồ côi khi nó chết, nên orphan **không** để lại zombie.

Ta dựng cây `main → A → B`, cho A chết ngay, `main` làm subreaper:

```cpp
#include <iostream>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    prctl(PR_SET_CHILD_SUBREAPER, 1);                // (1) main nhận nuôi mọi "cháu mồ côi" trong cây của nó
    pid_t pidMain = getpid();

    pid_t A = fork();
    if (A == 0) {                                    // (2) A: con của main
        pid_t pidA = getpid();                       // B sẽ nhớ pid của A qua bản sao bộ nhớ
        pid_t B = fork();
        if (B == 0) {                                // (3) B: cháu của main, con của A
            while (getppid() == pidA) usleep(10 * 1000);    // (4) đợi tới khi cha không còn là A (A đã chết)
            std::cout << "[B] cha moi la main (subreaper): " << (getppid() == pidMain)
                      << ", khac cha cu: " << (getppid() != pidA) << std::endl;
            _exit(0);
        }
        _exit(0);                                    // (5) A chết ngay, B thành mồ côi
    }
    waitpid(A, nullptr, 0);                          // (6) main thu dọn A
    pid_t xong = waitpid(-1, nullptr, 0);            // (7) rồi thu dọn luôn B (nhờ là subreaper)
    std::cout << "[main] thu don them mot tien trinh: " << (xong > 0 && xong != A) << std::endl;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Cây tiến trình |
|---|---|---|
| (1) | `main` đăng ký làm subreaper | `main` |
| (2)–(5) | `main` sinh A, A sinh B rồi A thoát ngay; B chờ tới khi cha đổi | `main → B` (B mồ côi, đã được nhận nuôi) |
| (6)–(7) | `main` `wait` A, rồi `wait` tiếp B | không còn con nào |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
[B] cha moi la main (subreaper): 1, khac cha cu: 1
[main] thu don them mot tien trinh: 1
```

**Thử thay đổi: bỏ dòng (1).** Mình đã chạy: B vẫn sống và đổi cha, nhưng cha mới **không** phải `main` (`cha moi la main: 0`) và `main` không thu dọn được B. Trên máy mình B được nhận nuôi bởi một tiến trình `systemd` của phiên người dùng (cũng là một subreaper), không phải pid 1; ở hệ khác có thể là pid 1.

!!! info "Bạn biết Go?"
    Go cũng có zombie: `c := exec.Command("true"); c.Start()` mà **không** `c.Wait()` thì con thành zombie. Mình đã chạy: sau 0,3 giây `/proc/<pid>/status` của con ghi `State: Z (zombie)`, sau `c.Wait()` thì tệp biến mất. `Run()` và `Output()` đã tự `Wait`; `Start()` thì bạn phải tự `Wait`.

### 6. Bẫy: `fork` trong chương trình đa luồng

POSIX nói rõ: sau `fork`, **chỉ luồng đã gọi `fork` tồn tại trong con**. Các luồng khác không được nhân bản, nhưng **bộ nhớ thì được sao chép nguyên si**, kể cả một mutex đang ở trạng thái "bị giữ". Nếu lúc `fork` có luồng khác đang giữ khóa, bản sao trong con ghi mãi "đang bị giữ" mà **người giữ không còn tồn tại để nhả**: con gọi `lock()` trên khóa đó sẽ chờ mãi, **deadlock** ([Bài 26](../nhom-3-da-luong/26-deadlock.md)). Khóa trong thư viện (của bộ cấp phát, của `std::cout`…) cũng có thể gặp đúng chuyện này.

Vì thế POSIX chỉ cho con trong chương trình đa luồng gọi hàm **async-signal-safe** giữa `fork` và `exec` (hàm không đụng khóa, không cấp phát bộ nhớ: `_exit`, `dup2`, `execve` thuộc loại này; `new`, `std::cout`, `lock()` thì không). Ví dụ an toàn, **không treo**: luồng phụ giữ khóa lúc `fork`, con dùng `try_lock` (thử xin, không chờ) để thấy khóa vẫn "bị giữ". Con vẫn dùng `std::cout` để in vì không luồng nào khác đang in lúc `fork`; đó là may mắn của ví dụ nhỏ, không phải điều bảo đảm, và chương trình thật đừng làm vậy.

```cpp
#include <atomic>
#include <iostream>
#include <mutex>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>

std::mutex khoa;
std::atomic<bool> daGiu{false};                      // luồng phụ báo: "tôi đang giữ khóa"
std::atomic<bool> choNha{false};                     // main báo: "bạn nhả khóa được rồi"

void luongPhu() {
    khoa.lock();                                     // (1) luồng phụ giữ khóa
    daGiu = true;
    while (!choNha) std::this_thread::yield();
    khoa.unlock();                                   // (2) chỉ luồng phụ của CHA mới nhả được
}

int main() {
    std::thread t(luongPhu);
    while (!daGiu) std::this_thread::yield();        // đợi tới khi chắc chắn khóa đang bị giữ

    pid_t con = fork();                              // (3) fork đúng lúc luồng phụ đang giữ khóa
    if (con == 0) {
        bool lay = khoa.try_lock();                  // (4) trong con chỉ còn MỘT luồng; thử xin khóa, không chờ
        std::cout << "[con] xin duoc khoa: " << lay << " (luong giu khoa khong ton tai trong con)" << std::endl;
        _exit(0);
    }
    waitpid(con, nullptr, 0);
    choNha = true;                                   // (5) cha cho luồng phụ nhả khóa
    t.join();
    bool chaLay = khoa.try_lock();                   // (6) trong cha khóa đã được nhả đàng hoàng
    if (chaLay) khoa.unlock();
    std::cout << "[cha] luong phu da nha khoa; cha xin duoc khoa: " << chaLay << std::endl;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Khóa `khoa` |
|---|---|---|
| (1)–(3) | Luồng phụ khóa rồi báo; `main` đợi báo xong mới `fork` | "bị giữ" (ghi trong bộ nhớ, bị sao chép) |
| (4) | Con (một luồng) `try_lock`: thất bại, không treo | con thấy "bị giữ", không ai nhả |
| (5)–(6) | Cha cho phép nhả, `join`, rồi `try_lock` thành công | trong cha: đã nhả |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
[con] xin duoc khoa: 0 (luong giu khoa khong ton tai trong con)
[cha] luong phu da nha khoa; cha xin duoc khoa: 1
```

Đổi `try_lock()` ở (4) thành `lock()` là **treo mãi** (con chờ một luồng không tồn tại). Mình đã chạy với `timeout 3`: không in gì, `timeout` thoát mã **124**; nên khối này ở dạng bỏ qua kiểm tra, chỉ phần con khác đi:

```cpp
// bo-qua-kiem-tra
    if (con == 0) {
        khoa.lock();                                 // chờ một luồng không còn tồn tại: treo mãi
        std::cout << "[con] xin duoc khoa" << std::endl;   // không bao giờ tới đây
        _exit(0);
    }
```

Cách tránh, theo thứ tự ưu tiên: (1) dùng `posix_spawn` thay `fork` + `exec` (mục 8); (2) nếu phải `fork`, `exec` **ngay**, giữa chừng chỉ gọi hàm async-signal-safe; (3) `fork` **trước** khi tạo luồng. `pthread_atfork` (đăng ký hàm chạy quanh `fork`) chỉ nhắc tên vì khó dùng đúng.

### 7. File descriptor bị kế thừa, và `FD_CLOEXEC`

Bảng file descriptor ([Bài 44](../nhom-5-he-thong-quy-trinh/44-mang-socket.md): số nguyên đại diện cho tệp, ống, socket đang mở) được **sao chép qua `fork`** rồi **giữ nguyên qua `exec`**. Hai bên cùng trỏ vào **cùng một đối tượng** (một socket; với tệp thì chung cả vị trí đọc/ghi). Cha `close` fd của mình chỉ bỏ phần của cha; đối tượng thật chỉ đóng khi **mọi** fd trỏ tới nó đều đóng.

Cờ **`FD_CLOEXEC`** ("close on exec") bảo hệ điều hành tự đóng fd khi tiến trình `exec`. Cách tốt nhất là mở sẵn kèm cờ (`O_CLOEXEC` ở `open`, `SOCK_CLOEXEC` ở `socket`): nếu mở rồi mới bật cờ bằng `fcntl` thì với đa luồng còn hở một khoảng cho luồng khác `fork` + `exec` lọt vào giữa.

Ví dụ: mở hai fd, rồi con `exec` một `sh` chạy `test -e /proc/self/fd/N` (thoát mã 0 nếu fd N còn mở trong chương trình mới). Trong `sh -c "lệnh" sh X`, chữ `sh` thứ hai là `$0` và `X` là `$1`; ví dụ dùng `$1` để truyền đường dẫn vào lệnh.

```cpp
#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

bool fdConMoSauExec(int fd) {                        // true nếu fd còn mở sau khi con exec chương trình khác
    pid_t con = fork();
    if (con == 0) {
        std::string duongDan = "/proc/self/fd/" + std::to_string(fd);
        char s0[] = "sh", s1[] = "-c", s2[] = "test -e \"$1\"", s3[] = "sh";
        char* argv[] = {s0, s1, s2, s3, duongDan.data(), nullptr};
        execvp("sh", argv);
        _exit(127);
    }
    int tt = 0;
    waitpid(con, &tt, 0);
    return WIFEXITED(tt) && WEXITSTATUS(tt) == 0;
}

int main() {
    int fdThuong = open("/dev/null", O_RDONLY);               // (1) mở bình thường
    int fdCloexec = open("/dev/null", O_RDONLY | O_CLOEXEC);  // (2) mở kèm cờ FD_CLOEXEC
    bool a = fdConMoSauExec(fdThuong);
    bool b = fdConMoSauExec(fdCloexec);
    std::cout << "fd mo binh thuong, con thay sau exec: " << a << std::endl;
    std::cout << "fd mo voi O_CLOEXEC, con thay sau exec: " << b << std::endl;
    close(fdThuong);
    close(fdCloexec);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng fd |
|---|---|---|
| (1)–(2) | Mở `/dev/null` hai lần, một lần kèm `O_CLOEXEC` | hai fd (số tùy máy) |
| `fdConMoSauExec` | `fork`, con `exec` `sh`, `sh` kiểm `/proc/self/fd/N` còn không | fd thường: còn; fd có cờ: đã bị đóng lúc `exec` |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
fd mo binh thuong, con thay sau exec: 1
fd mo voi O_CLOEXEC, con thay sau exec: 0
```

Rò fd gây lỗi khó thấy. Mình đã thử: cha mở socket lắng nghe rồi `fork` + `exec` chương trình `sleep`; sau đó cha `close` socket của mình. Vì `sleep` còn giữ một bản fd, `connect` tới cổng đó vẫn **thành công** (trả `0`); mở bằng `SOCK_CLOEXEC` thì `connect` bị từ chối (trả `-1`). Tương tự, một đầu ghi của ống bị con giữ khiến bên đọc không bao giờ thấy "hết dữ liệu" ([Bài 49](49-ipc.md)).

### 8. `posix_spawn`, `system`, và khi nào chọn gì

`posix_spawn` (và `posix_spawnp` tìm theo `PATH`) là **fork + exec gói trong một lời gọi**: không có khoảng "đang ở giữa" nguy hiểm, và dặn sẵn việc chuyển hướng fd qua tham số. `std::system("lệnh")` chạy `/bin/sh -c "lệnh"` rồi tự chờ xong, trả trạng thái cùng kiểu `waitpid` (đọc bằng `WEXITSTATUS`). Với `posix_spawn`, con vẫn phải được `wait`.

```cpp
#include <cstdlib>
#include <iostream>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>

extern char** environ;                               // biến môi trường của tiến trình hiện tại

int main() {
    char a0[] = "echo", a1[] = "tu posix_spawnp";
    char* argv[] = {a0, a1, nullptr};
    pid_t pid = 0;
    int loi = posix_spawnp(&pid, "echo", nullptr, nullptr, argv, environ);   // (1) fork + exec trong một lời gọi
    if (loi != 0) {                                  // trả thẳng mã lỗi, không dùng errno
        std::cerr << "posix_spawnp loi, ma " << loi << std::endl;
        return 1;
    }
    int tt = 0;
    waitpid(pid, &tt, 0);                            // (2) vẫn phải wait để dọn con
    std::cout << "posix_spawnp: con thoat ma " << WEXITSTATUS(tt) << std::endl;

    int ts = std::system("exit 7");                  // (3) shell chạy "exit 7", system tự chờ
    std::cout << "system: lenh thoat ma " << WEXITSTATUS(ts) << std::endl;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (1) | `posix_spawnp` sinh con và nạp `echo`, trả mã lỗi (0 = ổn), pid vào `pid`; hai `nullptr` là "không dặn việc chuyển hướng fd (`file_actions`) hay thuộc tính (`attr`) nào" | không có khoảng giữa |
| (2) | `waitpid` đọc mã thoát của `echo` | vẫn phải dọn con |
| (3) | `system` chạy `sh -c "exit 7"`, chờ, trả trạng thái | `WEXITSTATUS` = 7 |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
tu posix_spawnp
posix_spawnp: con thoat ma 0
system: lenh thoat ma 7
```

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Chạy chương trình ngoài, không chỉnh gì đặc biệt, chương trình **có thể đa luồng** | `posix_spawn` | một lời gọi, không có khoảng giữa nguy hiểm |
| Chạy chương trình ngoài và phải chỉnh môi trường con (`dup2`, đổi thư mục, hạ quyền); chương trình một luồng | `fork` + `exec` | khoảng giữa là chỗ duy nhất con tự sửa mình |
| Lệnh shell cố định **bạn** viết (có `\|`, `>`, `*`), làm nhanh | `system` | tiện; **không** ghép chuỗi lấy từ người dùng vào (shell chạy cả phần "thừa": tiêm lệnh) |
| Muốn con chạy tiếp **chính mã này** trên bản chụp dữ liệu (cách ly lỗi, chụp trạng thái) | `fork` không `exec`, trước khi tạo luồng | COW cho bản chụp rẻ |
| Muốn song song và **dùng chung dữ liệu** | `std::thread` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) | sau `fork` không chia sẻ gì, phải thêm IPC ([Bài 49](49-ipc.md)) |

**Khi nào KHÔNG `fork`:** chương trình nhiều luồng (mục 6); chỉ cần chạy chương trình khác (`posix_spawn`, vì `fork` còn phải sao chép bảng ánh xạ bộ nhớ chỉ để bỏ đi ngay); cần trao đổi dữ liệu liên tục (luồng đơn giản hơn).

## 💻 Ví dụ code

### Ví dụ 1: chạy nhiều lệnh song song, thu dọn theo thứ tự xong

Sinh bốn con chạy bốn lệnh `sh -c` cùng lúc, rồi `waitpid(-1, ...)` thu dọn **theo thứ tự con xong** (không phải thứ tự sinh). Một `std::map` từ pid ra số thứ tự lệnh ghép kết quả về đúng lệnh; ta in theo thứ tự lệnh để đầu ra ổn định. Bốn lệnh kết thúc bốn kiểu: thành công, mã 5, bị `SIGKILL`, và lệnh không tồn tại.

```cpp
#include <cerrno>
#include <iostream>
#include <map>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

pid_t chayLenh(const std::string& lenh) {            // chạy "sh -c <lenh>" trong con, trả pid của con
    pid_t con = fork();
    if (con < 0) return -1;
    if (con == 0) {
        char s0[] = "sh", s1[] = "-c";
        std::string ban = lenh;                       // bản sao ghi được để lấy char*
        char* argv[] = {s0, s1, ban.data(), nullptr};
        execvp("sh", argv);                           // (1) thành công thì không bao giờ trở lại
        _exit(127);                                   // (2) execvp lỗi: thoát NGAY bằng _exit, không chạy tiếp mã của cha
    }
    return con;
}

int main() {
    std::vector<std::string> cacLenh = {
        "exit 0", "exit 5", "kill -9 $$", "lenh_khong_ton_tai_123 2>/dev/null"};

    std::map<pid_t, std::size_t> chiSo;               // (3) pid -> lệnh số mấy
    for (std::size_t i = 0; i < cacLenh.size(); ++i) {
        pid_t p = chayLenh(cacLenh[i]);
        if (p < 0) { std::perror("fork"); return 1; }
        chiSo[p] = i;
    }

    std::vector<std::string> ketQua(cacLenh.size());
    for (std::size_t conLai = cacLenh.size(); conLai > 0; --conLai) {   // (4) thu dọn theo thứ tự con xong
        int tt = 0;
        pid_t xong = waitpid(-1, &tt, 0);             // (5) -1 = bất kỳ con nào
        if (xong < 0) break;
        ketQua[chiSo[xong]] = WIFEXITED(tt) ? "thoat ma " + std::to_string(WEXITSTATUS(tt))
                                            : "bi tin hieu " + std::to_string(WTERMSIG(tt));
    }
    for (std::size_t i = 0; i < cacLenh.size(); ++i)  // (6) in theo thứ tự lệnh
        std::cout << "lenh " << i << " (" << cacLenh[i] << "): " << ketQua[i] << "\n";

    int tt = 0;
    std::cout << "het con: waitpid tra " << waitpid(-1, &tt, 0) << ", errno la ECHILD: " << (errno == ECHILD) << "\n";   // (7)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (3) | Sau bốn lần `chayLenh`, `chiSo` ghi bốn cặp pid → số thứ tự | bốn con chạy song song |
| (4)–(5) | Mỗi vòng `waitpid(-1, ...)` trả con nào xong trước; đọc `tt` bằng macro | `conLai` giảm dần |
| (1)/(2) | Trong con: `execvp` thành công thì (2) không chạy; lỗi mới tới (2) | `_exit` tránh chạy tiếp mã cha |
| (6)–(7) | In theo số thứ tự lệnh; rồi hỏi tiếp: hết con, `waitpid` trả `-1` | đầu ra ổn định |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
lenh 0 (exit 0): thoat ma 0
lenh 1 (exit 5): thoat ma 5
lenh 2 (kill -9 $$): bi tin hieu 9
lenh 3 (lenh_khong_ton_tai_123 2>/dev/null): thoat ma 127
het con: waitpid tra -1, errno la ECHILD: 1
```

Lệnh số 3 thoát mã 127 vì chính **`sh`** không tìm thấy lệnh (cùng quy ước 127 với `_exit(127)` của ta). Bỏ vòng `waitpid` ở (4) thì cả bốn con thành zombie cho tới khi chương trình kết thúc, đúng cái hại ở mục 5.

### Ví dụ 2: `fork` 3 lần in bao nhiêu dòng, và bẫy bộ đệm

Mỗi `fork` **nhân đôi số tiến trình đang có**: ba lần liên tiếp cho 1 → 2 → 4 → 8, tức **2^n** với n lần `fork`. Cả tám tiến trình chạy tiếp mã sau `fork` cuối và mỗi cái in đúng một dòng.

```cpp
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    fork();                                          // (1) 1 tiến trình thành 2
    fork();                                          // (2) mỗi tiến trình trong 2 thành 2: tổng 4
    fork();                                          // (3) mỗi tiến trình trong 4 thành 2: tổng 8
    std::cout << "toi la mot trong cac tien trinh\n" << std::flush;   // (4) mỗi tiến trình in đúng một dòng
    while (wait(nullptr) > 0) {}                     // (5) thu dọn mọi con của MÌNH (con nào cũng có thể có con)
    return 0;
}
```

**Chạy từng dòng:** sau (1) có 2 tiến trình, sau (2) có 4, sau (3) có 8; ở (4) cả 8 cùng in (mỗi cái một dòng), ở (5) mỗi tiến trình thu dọn các con của chính nó rồi thoát.

Mình chạy `./chuongtrinh | wc -l` (đếm dòng): ra **8**. Thứ tự các dòng không xác định, nhưng số dòng chắc chắn. Biến thể hay hỏi: `fork() && fork();` cho **3** tiến trình (con của `fork` đầu nhận `0` nên `&&` bỏ qua `fork` thứ hai; chỉ cha gọi tiếp); mình đã chạy ra 3 dòng.

Bẫy thứ hai: **bộ đệm chữ**. `std::cout` mặc định đi qua bộ đệm stdout của C: ra màn hình thì xả theo dòng, ra ống hoặc tệp thì **giữ trong bộ nhớ** tới khi đầy hoặc thoát. `fork` sao chép cả bộ nhớ đó, nên chữ chưa xả bị **in hai lần** (mỗi tiến trình xả bản của mình lúc thoát).

```cpp
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    std::cout << "dong A (khong flush)\n";           // (1) nằm trong bộ đệm, chưa ra ngoài (khi ra ống)
    pid_t con = fork();                              // (2) con nhận BẢN SAO bộ đệm này
    if (con == 0) {
        std::cout << "dong B (tu con)\n";
        return 0;                                    // (3) con thoát bình thường: bộ đệm của con được xả
    }
    waitpid(con, nullptr, 0);
    std::cout << "dong C (tu cha)\n";
    return 0;                                        // (4) cha thoát: bộ đệm của cha được xả
}
```

**Chạy từng dòng:** (1) cha ghi "dong A" vào bộ đệm (ra ống thì chưa xả); (2) `fork` sao chép bộ đệm đó cho con; (3) con ghi "dong B", thoát và xả bộ đệm của nó: ra "dong A", "dong B"; (4) cha ghi "dong C", thoát và xả bộ đệm của cha, vẫn còn "dong A" ở đầu: ra "dong A", "dong C".

Kết quả thật, hai cách chạy khác nhau của **cùng một chương trình**:

```text
$ ./chuongtrinh                  $ ./chuongtrinh | cat
dong A (khong flush)             dong A (khong flush)
dong B (tu con)                  dong B (tu con)
dong C (tu cha)                  dong A (khong flush)
                                 dong C (tu cha)
```

Ra ống, "dong A" hiện **hai lần**. Cách chữa: `<< std::flush` (hoặc `std::endl`) **trước** `fork`; và nhánh con chưa `exec` thì thoát bằng `_exit` (không xả bộ đệm bản sao, không chạy hàm dọn dẹp của cha) thay vì `exit`/`return`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`fork` làm gì và trả về gì? Con có chạy lại từ đầu `main` không?"
    `fork` tạo tiến trình con là bản sao của cha (bộ nhớ, file descriptor, chỗ đang chạy); trả `0` ở con, pid của con ở cha, `-1` nếu lỗi. Con **không** chạy lại từ `main`, cả hai tiếp tục từ dòng ngay sau `fork`. Hai bên sống riêng, con sửa biến thì cha không thấy. Thứ tự chạy của hai bên không bảo đảm, muốn đồng bộ phải `waitpid`.

??? question "Copy-on-write là gì? `fork` tiến trình 10 GB có sao chép 10 GB không?"
    Không chép dữ liệu ngay: hai tiến trình dùng chung các trang vật lý, đánh dấu chỉ-đọc; bên nào ghi vào một trang thì hệ điều hành mới chép đúng trang đó cho bên ấy. Chi phí `fork` theo số trang ánh xạ (phải sao chép bảng ánh xạ), không theo lượng dữ liệu phải chép. Mình đo: con ghi vào 16384 trang thì ra 16384 lỗi trang (xấp xỉ số trang, vài chục lỗi thừa là chuyện thường); cha ghi vùng đã có sẵn thì 0. Con ghi hết các trang thì RAM dùng thêm cũng cỡ đó.

??? question "Zombie là gì, phát hiện và xử lý thế nào? Còn orphan? `kill -9` zombie được không?"
    Zombie là con đã chết nhưng cha chưa `wait`, nên hệ điều hành còn giữ hồ sơ (pid, mã thoát); `ps` ghi `Z` hoặc `<defunct>`. Nó chiếm pid, đủ nhiều thì `fork` có thể lỗi `EAGAIN`. `kill -9` vô ích vì nó đã chết; chữa bằng cách cha `waitpid` (thường khi nhận `SIGCHLD`, hoặc vòng `waitpid(-1, ..., WNOHANG)`), hoặc tắt cha để `init`/subreaper thu dọn. Orphan là con còn sống mà cha đã chết: được `init` hay subreaper nhận nuôi và `wait` giùm, nên không thành zombie.

??? question "Vì sao có `fork` rồi mới `exec`, mà không có một hàm tạo tiến trình mới luôn?"
    Vì giữa hai bước con còn chạy mã của cha và tự chỉnh môi trường quanh mình (chuyển hướng `stdin`/`stdout` bằng `dup2`, đóng fd, đổi thư mục) rồi mới thay hình hài; shell dựng `>` và `|` đúng ở chỗ này. Cái giá: khoảng giữa nguy hiểm khi có đa luồng, và `fork` phải sao chép bảng ánh xạ, nên có `posix_spawn` gộp cả hai cho trường hợp đơn giản.

??? question "Chương trình đa luồng gọi `fork` thì sao? Thế nếu con chỉ in một dòng?"
    Chỉ luồng gọi `fork` tồn tại trong con, nhưng bộ nhớ (kể cả mutex đang bị giữ) được sao chép nguyên. Luồng khác đang giữ khóa lúc `fork` thì con xin khóa đó sẽ treo mãi vì người giữ không còn. Khóa trong thư viện cũng vậy nên "chỉ in một dòng" (`std::cout`, `printf`, `new`) vẫn có thể treo; POSIX chỉ cho gọi hàm async-signal-safe giữa `fork` và `exec`. Tránh bằng `posix_spawn`, hoặc `exec` ngay, hoặc `fork` trước khi tạo luồng.

??? question "`fork()` gọi 3 lần liên tiếp in bao nhiêu dòng? Còn nếu `printf` không có `\n` rồi chuyển hướng ra tệp?"
    n lần `fork` cho 2^n tiến trình: ba lần là 8, mỗi tiến trình in một dòng nên 8 dòng. Nếu chữ còn nằm trong bộ đệm stdout (không có `\n` khi ra màn hình, hoặc luôn như thế khi ra tệp/ống vì chỉ xả khi đệm đầy hay lúc thoát) thì `fork` sao chép cả bộ đệm, và mỗi tiến trình xả bản của mình lúc thoát, nên chữ đó có thể hiện nhiều lần (tối đa 8). Phòng bằng `fflush`/`std::flush` trước `fork`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên `wait` cho con"
    Mỗi con chết mà cha không `wait` là một zombie (mình đã chạy: `ps` ghi `Z`). Server sống lâu mà sinh con không thu dọn sẽ cạn pid. Luôn có một đường `waitpid` cho **mỗi** con.

!!! warning "Lỗi 2: Con không thoát, chạy tiếp mã của cha"
    `execvp` lỗi mà con không `_exit` thì con rơi xuống mã của cha và làm thêm việc của cha (trong vòng lặp sinh con, số tiến trình nhân lên ngoài ý muốn). Sau `execvp` luôn có `_exit(127)`; nhánh con nào không `exec` cũng phải kết thúc rõ ràng.

!!! warning "Lỗi 3: `fork` khi chữ chưa xả hoặc khi đang đa luồng"
    Chữ chưa xả bị in hai lần (mình đã chạy: "dong A" hai lần khi ra ống); khóa bị giữ ở luồng khác làm con treo mãi. Xả bộ đệm trước `fork`; chương trình đa luồng dùng `posix_spawn`.

!!! warning "Lỗi 4: Đọc `WEXITSTATUS` mà không kiểm `WIFEXITED`, và để rò fd qua `exec`"
    Con bị `SIGKILL` giết thì `WEXITSTATUS(tt)` vô nghĩa (phải dùng `WTERMSIG`): kiểm `WIFEXITED` trước. Quên `O_CLOEXEC` thì con giữ socket hay đầu ống mà cha tưởng đã đóng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="48" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau. Mỗi tiến trình khi chạy tới dòng in sẽ in đúng một dòng rồi `wait` các con của mình. Tổng cộng in bao nhiêu dòng?

```text
fork() && fork();
std::cout << "x\n" << std::flush;
```

- 2 dòng, vì có hai lời gọi `fork` nên thêm hai dòng
- 4 dòng, vì hai lần `fork` liên tiếp cho 2^2 tiến trình
- 3 dòng, vì con của `fork` đầu bỏ qua `fork` thứ hai
- 1 dòng, vì chỉ tiến trình cha chạy tới được dòng in

<p class="giai-thich" markdown>`fork()` đầu trả `0` ở con và số dương ở cha; `&&` chỉ tính vế phải khi vế trái khác 0, nên chỉ **cha** gọi `fork` thứ hai, còn con đầu bỏ qua. Cây cuối có cha, con thứ nhất và con thứ hai của cha: 3 tiến trình, 3 dòng. Con số 4 chỉ đúng khi hai `fork` là hai câu lệnh riêng như `fork(); fork();`. Mọi tiến trình đều chạy tới dòng in, nên không phải chỉ cha in.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau. Ở cha, `n` được in ra là gì?

```text
int n = 5;
if (fork() == 0) { n = 50; _exit(0); }
wait(nullptr);
std::cout << n;
```

- `50`, vì con sửa `n` trước khi cha đọc nên cha thấy giá trị mới
- `5` hoặc `50`, tùy cha hay con chạy trước vì cùng một ô nhớ
- Không in được gì, vì con thoát trước nên cha mất `n`
- `5`, vì con chỉ sửa bản `n` của chính nó

<p class="giai-thich" markdown>Sau `fork` mỗi tiến trình có bản `n` riêng (qua copy-on-write, trang bị ghi được sao chép riêng cho con), nên con đặt `n = 50` không ảnh hưởng cha, và cha in 5; `wait` chỉ làm cha đợi con xong rồi mới đọc. Nghĩ "cha thấy 50" là gộp tiến trình với luồng, vốn mới dùng chung biến. Thứ tự chạy không đổi kết quả vì không có ô nhớ chung nào để tranh. Con thoát cũng không làm cha mất biến của cha.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Một server đa luồng cần chạy một công cụ dòng lệnh bên ngoài thật nhiều lần, từ nhiều luồng. Cách nào hợp lý nhất?

- `fork`, để con tiếp tục dùng các mutex và `new` của server rồi mới `exec`
- `posix_spawn`, hoặc `fork` rồi `exec` ngay, không làm gì ở giữa
- `std::system` với chuỗi lệnh ghép từ tên tệp do người dùng gửi lên
- Tạo thêm `std::thread`, vì luồng cũng chạy được chương trình ngoài

<p class="giai-thich" markdown>`posix_spawn` gộp sinh con và nạp chương trình thành một lời gọi, không có khoảng giữa để một khóa bị giữ ở luồng khác làm con treo. Để con dùng mutex và `new` của server trước `exec` là đúng điều bẫy cảnh báo: khóa đang bị luồng khác giữ sẽ không bao giờ được nhả trong con. Ghép tên tệp người dùng vào chuỗi cho `system` mở đường cho tiêm lệnh shell. Còn luồng chạy mã của chính chương trình mình, không nạp được chương trình khác.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Một server sinh con để xử lý mỗi yêu cầu. Sau vài ngày, `ps` thấy hàng nghìn tiến trình `Z <defunct>`, cha vẫn chạy bình thường. Nên làm gì?

- `kill -9` hàng loạt các tiến trình `Z` để dọn chúng khỏi bảng tiến trình
- Tăng giới hạn bộ nhớ của server để hàng nghìn zombie có chỗ chứa
- Cha phải `waitpid` thu dọn con (khi nhận `SIGCHLD` hay vòng `WNOHANG`)
- Đổi `_exit` trong con thành `return` từ `main` để con thoát gọn hơn

<p class="giai-thich" markdown>Zombie là con đã chết mà cha chưa đọc kết quả bằng `wait`, nên chữa tận gốc là cha phải `waitpid` cho mỗi con. `kill -9` vô ích vì tiến trình đã chết, chỉ còn mẩu hồ sơ chờ cha đọc. Zombie hầu như không dùng bộ nhớ, thứ chúng chiếm là ô pid, nên nới bộ nhớ không giải quyết gì. Đổi cách thoát của con cũng không giúp, vì cách thoát nào cũng cần cha thu dọn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Đọc đoạn sau. Con đã bị giết bằng `SIGKILL`. Điều nào đúng về `tt` mà cha nhận từ `waitpid`?

```text
int tt;
waitpid(con, &tt, 0);
```

- `WIFSIGNALED(tt)` đúng và `WTERMSIG(tt)` là 9; `WEXITSTATUS` không có nghĩa
- `WIFEXITED(tt)` đúng và `WEXITSTATUS(tt)` là 9, vì mã thoát bằng số tín hiệu
- `WIFEXITED(tt)` đúng và `WEXITSTATUS(tt)` là 0, vì con không tự báo lỗi
- `waitpid` trả `-1`, vì con bị giết nên không còn gì để chờ

<p class="giai-thich" markdown>Con chết vì tín hiệu thì `WIFSIGNALED` đúng và số tín hiệu lấy bằng `WTERMSIG` (9 cho `SIGKILL`); khi đó không có mã thoát nên `WEXITSTATUS` vô nghĩa. Thoát thường và bị tín hiệu giết là hai trường hợp riêng, nên mã thoát không bao giờ lấy từ số tín hiệu, và `WIFEXITED` sai chứ không đúng với mã 0. `waitpid` vẫn trả pid của con vừa kết thúc; chỉ khi lỗi (như không còn con nào) mới trả `-1`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Một chương trình mở socket lắng nghe cổng, rồi `fork` + `exec` các công cụ ngoài chạy lâu. Sau đó chương trình `close` socket của mình, nhưng cổng vẫn mở và kết nối tới đó vẫn được nhận. Vì sao, và chữa thế nào?

- Hệ điều hành giữ cổng thêm một lúc sau `close`, chỉ cần chờ vài giây là hết
- Socket bị sao chép bộ nhớ sang con, nên con phải gọi `free` cho nó trước
- Cổng bị chiếm bởi các zombie của con, nên cha cần `waitpid` cho từng con
- Con kế thừa fd qua `fork` và `exec`; hãy mở socket bằng `SOCK_CLOEXEC`

<p class="giai-thich" markdown>File descriptor được kế thừa qua `fork` và giữ qua `exec`; đối tượng socket chỉ đóng khi mọi fd trỏ tới nó đều đóng, nên con còn giữ thì cổng vẫn mở. Mở với `SOCK_CLOEXEC` (hay `O_CLOEXEC`) thì fd tự đóng lúc `exec`. Chờ không giúp vì không có đồng hồ nào tự đóng nó. Socket không phải vùng nhớ cấp phát nên `free` không liên quan. Zombie giữ pid chứ không giữ fd, vì fd bị đóng khi tiến trình chết.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Đọc đoạn sau. Chạy `./chuongtrinh | cat` (kết quả vào ống). Chữ "A" xuất hiện mấy lần?

```text
std::cout << "A\n";
fork();
```

- Một lần, vì sau `\n` bộ đệm luôn được xả
- Hai lần, vì bộ đệm chưa xả được sao chép sang con
- Hai lần chỉ khi chạy ra màn hình, ra ống thì một lần
- Không lần nào, vì `fork` xóa bộ đệm của cả hai bên

<p class="giai-thich" markdown>Khi ra ống, chữ nằm trong bộ đệm cho tới khi đầy hoặc thoát, kể cả có `\n`, và `fork` sao chép bộ nhớ đó; cha và con đều xả bản của mình lúc thoát, nên "A" hiện hai lần. Xả sau mỗi `\n` chỉ xảy ra khi đầu ra là màn hình (chế độ theo dòng), và ở đó "A" chỉ hiện một lần; nói "hai lần chỉ khi ra màn hình" là đảo ngược sự thật. `fork` không xóa gì, nên chữ không biến mất.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `fork` nhân đôi tiến trình và **trả hai lần**: `0` ở con, pid con ở cha, `-1` khi lỗi (luôn kiểm); con là bản sao nên sửa biến không ảnh hưởng cha. Nhờ **copy-on-write** `fork` không chép dữ liệu ngay: mình đo con ghi 16384 trang thì có 16384 lỗi trang, cha 0. `fork` n lần liên tiếp cho 2^n tiến trình.
2. `execvp` thay hình hài tiến trình nhưng giữ **pid** (mình chạy: hai pid bằng nhau) và các fd chưa đặt `FD_CLOEXEC`; thành công thì không trở lại, thất bại thì `_exit(127)`. Tách `fork`/`exec` để con tự chỉnh môi trường (chuyển hướng, đóng fd) ở khoảng giữa.
3. Cha dọn con bằng `waitpid`, đọc `WIFEXITED`/`WEXITSTATUS` hoặc `WIFSIGNALED`/`WTERMSIG`. Con chết chưa được `wait` là **zombie** (`Z`, `kill -9` không xóa được; cha `wait` hoặc cha chết thì hết); cha chết trước thì con là **orphan**, được `init`/subreaper nhận nuôi và thu dọn.
4. `fork` trong chương trình **đa luồng** là bẫy: chỉ luồng gọi `fork` có trong con nhưng khóa đang bị giữ được sao chép nguyên, nên con xin khóa đó sẽ treo (mình chạy: `timeout` mã 124). Dùng `posix_spawn`, hoặc `exec` ngay, hoặc `fork` trước khi tạo luồng; `system` chỉ với chuỗi lệnh do chính bạn viết.
5. Fd bị kế thừa nên cần `O_CLOEXEC`/`FD_CLOEXEC` (mình chạy: fd thường còn mở sau `exec`, có cờ thì không); bộ đệm `std::cout` bị sao chép qua `fork` nên chữ chưa xả bị in hai lần khi ra ống; Go không có `fork` trần, chỉ `os/exec` (fork + exec + wait) và vẫn phải `Wait` để khỏi có zombie.
