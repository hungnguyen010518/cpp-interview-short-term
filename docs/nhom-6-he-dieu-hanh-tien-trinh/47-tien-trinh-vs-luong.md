# Bài 47 — Tiến trình và luồng: khác nhau ở đâu, khi nào chọn cái nào

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng cái gì **riêng** và cái gì **chung**: mỗi tiến trình có một bản đồ bộ nhớ ảo riêng; các luồng của một tiến trình chung code, biến toàn cục và heap, nhưng riêng stack, thanh ghi và biến `thread_local`. Thấy tận mắt cùng một địa chỉ mà hai tiến trình giữ hai giá trị khác nhau.
    - Hiểu **bản chất** của hai chi phí: vì sao tạo tiến trình đắt hơn tạo luồng (và đắt thêm khi bộ nhớ lớn), vì sao đổi luồng chạy trong cùng tiến trình rẻ hơn đổi giữa hai tiến trình; có số đo thật.
    - Nói được hệ quả về **cách ly lỗi** (luồng crash kéo cả tiến trình, tiến trình con crash thì cha vẫn sống) và về **giao tiếp** (bộ nhớ chung cần khóa so với IPC).
    - Dùng **bảng quyết định** để chọn tiến trình hay luồng, biết khi nào KHÔNG nên chọn cái nào, xem luồng bằng `ps -L` và `/proc`, đặt goroutine của Go đúng chỗ, và trả lời câu "process vs thread" theo bốn góc.

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, heap, biến toàn cục), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `thread_local`, TSan), [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md) (`SIGSEGV`, mã thoát 139), [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) (`/proc/PID`, `strace`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda `[&]`). [Bài 48](48-fork-exec-wait.md) (`fork` chi tiết) và [Bài 49](49-ipc.md) (IPC) đến sau; ở đây `fork` được giới thiệu vừa đủ để so sánh.

## 🧠 Câu chuyện mở đầu

Ở Nhóm 3 bạn đã có một **nhà bếp** với nhiều đầu bếp. Giờ ta lùi ra xa nhìn cả **tòa chung cư**: mỗi **căn hộ** là một **tiến trình**, có tường riêng và khóa riêng. Số phòng chỉ có nghĩa **trong căn hộ**: "phòng 5" của căn A và "phòng 5" của căn B là hai phòng khác nhau, và người căn này không bước được vào căn kia.

Những người sống trong cùng một căn hộ là các **luồng**. Họ dùng chung bếp và tủ lạnh (heap và biến toàn cục), nên ai bỏ gì vào tủ thì người khác thấy ngay. Mỗi người có một ngăn bàn riêng (stack) và một hộp đồ cá nhân (`thread_local`). Muốn nhắn tin sang căn hộ khác phải nhờ **ban quản lý** (hệ điều hành): đó là IPC, [Bài 49](49-ipc.md).

!!! info "Chỗ nào ví von chung cư không còn đúng?"
    Căn hộ thật không nhân bản trong chớp mắt, còn tiến trình thì được (`fork`, mục 💻 A). Hai căn hộ thật cũng không dùng chung một phòng, trong khi tiến trình có thể xin hệ điều hành một vùng nhớ chung ([Bài 49](49-ipc.md)). Và ngăn bàn riêng chỉ là **quy ước**: người trong căn hộ vẫn với tay mở được ngăn của nhau nếu biết chỗ (ví dụ ngay dưới đây).

## 📖 Giải thích

### 1. Hai vai trò: hộp tài nguyên và đơn vị được chạy

**Tiến trình (process)** là cái hộp chứa tài nguyên: không gian địa chỉ (toàn bộ bộ nhớ nó thấy), bảng các tệp đang mở, mã số tiến trình **pid**, cách xử lý tín hiệu. **Luồng (thread)** là đơn vị mà hệ điều hành **lập lịch**, tức chọn luồng nào chiếm lõi CPU nào, lúc nào. Mỗi tiến trình có ít nhất một luồng (luồng chính chạy `main`), mỗi luồng có thanh ghi riêng (gồm chỗ "đang chạy tới lệnh nào") và stack riêng.

| Thứ gì | Giữa hai tiến trình | Giữa các luồng của một tiến trình |
|---|---|---|
| Code, biến toàn cục, heap | Mỗi tiến trình một bản riêng | **Chung** |
| Stack | Riêng | Mỗi luồng một stack |
| Thanh ghi | Riêng | Mỗi luồng một bộ |
| `thread_local` | Không có khái niệm này | Mỗi luồng một bản |
| Tệp đang mở, cách xử lý tín hiệu | Riêng: con được **chép** bảng tệp của cha lúc `fork` (hai bảng riêng, nhưng cùng trỏ tới những tệp đang mở, [Bài 48](48-fork-exec-wait.md)) | **Chung** |
| Mã số | `pid` riêng | Chung `pid`, mỗi luồng một `tid` (thread id) |

### 2. Chạy thật: luồng chung gì, riêng gì

Một luồng phụ ghi vào biến toàn cục, heap, `thread_local` và một biến cục bộ của luồng chính. Sau `join`, luồng chính xem còn lại gì.

```cpp
#include <iostream>
#include <thread>

int dem = 0;                              // (1) biến toàn cục: vùng tĩnh, chung
thread_local int rieng = 1;               // (2) mỗi luồng một bản riêng

int main() {
    int* kho = new int(0);                // (3) ô nhớ trên heap, chung
    int canhBan = 0;                      // (4) biến cục bộ: nằm trên stack của luồng chính
    int* diaChiRiengChinh = &rieng;       // (5) địa chỉ bản `rieng` của luồng chính

    std::thread t([&] {
        dem = 100;                        // (6) ghi vào biến toàn cục
        *kho = 100;                       // (7) ghi vào heap
        rieng = 100;                      // (8) ghi vào bản `rieng` của luồng PHỤ
        canhBan = 100;                    // (9) với được cả stack của luồng chính: lambda giữ tham chiếu
        std::cout << "luong phu: rieng = " << rieng
                  << ", &rieng giong cua luong chinh? " << (&rieng == diaChiRiengChinh) << "\n";
    });
    t.join();

    std::cout << "luong chinh: dem = " << dem << "\n";
    std::cout << "luong chinh: *kho = " << *kho << "\n";
    std::cout << "luong chinh: canhBan = " << canhBan << "\n";
    std::cout << "luong chinh: rieng = " << rieng << "\n";    // (10)
    delete kho;
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1)–(5) | Luồng chính tạo biến chung, heap, biến stack, và ghi nhớ địa chỉ `rieng` của mình | `dem=0`, `*kho=0`, `canhBan=0`, `rieng=1` |
| (6)–(7) | Luồng phụ ghi vào hai thứ **chung** | `dem=100`, `*kho=100` |
| (8) | Luồng phụ ghi `rieng`: nó có bản của nó, địa chỉ khác bản của luồng chính | bản của luồng chính vẫn `1` |
| (9) | Luồng phụ ghi vào biến trên stack luồng chính qua tham chiếu | `canhBan=100` |
| (10) | Sau `join`, luồng chính đọc lại cả bốn | thấy 100, 100, 100 và **1** |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
luong phu: rieng = 100, &rieng giong cua luong chinh? 0
luong chinh: dem = 100
luong chinh: *kho = 100
luong chinh: canhBan = 100
luong chinh: rieng = 1
```

Ba thứ **chung** (toàn cục, heap, và cả stack nếu có con trỏ hay tham chiếu tới nó) đều bị luồng phụ sửa. Chỉ `rieng` là mỗi luồng một bản. Vì mọi luồng nằm trong **một** không gian địa chỉ, "stack riêng" nghĩa là mỗi luồng có vùng stack của mình, không có nghĩa là luồng khác bị cấm đụng vào.

**Thử thay đổi: bỏ chữ `thread_local` ở (2).** Mình đã chạy: `&rieng` giống nhau (in `1`) và dòng cuối thành `luong chinh: rieng = 100`. Biến thường thì mọi luồng chung một bản.

### 3. Vì sao tiến trình không thấy bộ nhớ của nhau: bộ nhớ ảo

Địa chỉ mà chương trình của bạn in ra không phải số thứ tự ô nhớ thật trên thanh RAM. Đó là địa chỉ **ảo**: mỗi tiến trình có một **bảng trang** (bảng tra do hệ điều hành giữ) đổi địa chỉ ảo thành vị trí thật trong RAM. CPU đổi mỗi lần truy cập; để không chậm, nó nhớ các kết quả tra gần đây trong một bộ đệm nhỏ tên **TLB**.

Vì mỗi tiến trình có bảng tra riêng, cùng một địa chỉ ảo ở hai tiến trình có thể trỏ tới hai chỗ RAM khác nhau, hoặc không trỏ tới đâu cả. Đó là "tường" của căn hộ: tiến trình không **có cách** nhắm tới bộ nhớ của tiến trình khác bằng con trỏ thường, kể cả khi muốn (muốn chung thì phải xin hệ điều hành một vùng nhớ chung, [Bài 49](49-ipc.md)). Các luồng của một tiến trình dùng **chung một bảng trang**, nên chung mọi thứ như ở mục 2. Ví dụ 💻 A ngay dưới cho thấy điều này bằng một chương trình.

### 4. Chi phí: tạo, và "đổi luồng chạy" (context switch)

**Tạo.** Tạo luồng chỉ cần dựng một stack, một bộ thanh ghi và một mục quản lý trong **nhân** (kernel, phần lõi của hệ điều hành). Tạo tiến trình (bằng `fork`) còn phải dựng **bảng trang** cho tiến trình mới, và bảng này lớn theo lượng bộ nhớ tiến trình cha đang dùng: nhân không chép dữ liệu ngay (mỗi bên chỉ chép trang khi **sửa**, gọi là copy-on-write, [Bài 48](48-fork-exec-wait.md)) nhưng vẫn phải chép bảng tra. Ví dụ 💻 B đo chuyện này.

**Context switch** là lúc hệ điều hành cất trạng thái luồng đang chạy (thanh ghi) rồi nạp trạng thái luồng khác lên cùng lõi. Hai trường hợp khác hẳn nhau:

| | Đổi giữa hai luồng cùng tiến trình | Đổi giữa hai tiến trình |
|---|---|---|
| Phải đổi | Chỉ thanh ghi và stack | Thanh ghi **và cả bảng trang** |
| TLB | Vẫn dùng được: cùng bản đồ | Các mục tra của tiến trình cũ vô dụng với tiến trình mới (CPU đời mới có thể gắn nhãn để khỏi xóa hết, tùy loại CPU) |
| Bộ đệm CPU | Dữ liệu chung vẫn "ấm" | Phải ấm lại từ đầu |

Vì thế đổi luồng trong cùng tiến trình rẻ hơn. Bài này không đo context switch; con số tuyệt đối phụ thuộc CPU và hệ điều hành, nên mình chỉ nêu cơ chế.

### 5. Cách ly lỗi

- **Luồng crash thì cả tiến trình chết.** Truy cập bộ nhớ sai (`SIGSEGV`), `abort()`, hay ngoại lệ không bắt trong hàm của luồng (`std::terminate`, [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) đều là chuyện của **tiến trình**, không của riêng luồng. `try`/`catch` không bắt được `SIGSEGV`.
- **Tiến trình con crash thì cha vẫn sống**, vì con chết riêng trong căn hộ của nó; cha nhận được trạng thái "con chết vì tín hiệu số mấy". Ví dụ 💻 C chạy thật cả hai.
- Mặt trái của việc chung bộ nhớ: một luồng ghi bậy vào bộ nhớ có thể làm hỏng dữ liệu của luồng khác **mà không crash**, vì chung heap. Tiến trình khác không có kiểu hỏng này (trừ vùng nhớ chung hay tệp chung đã chủ động chia sẻ).

### 6. Giao tiếp

**Luồng:** đọc ghi thẳng vào biến chung, nhanh vì không qua nhân, nhưng phải đồng bộ bằng mutex, atomic... ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)); quên một chỗ là data race. **Tiến trình:** không có biến chung mặc định, phải nhờ nhân: pipe, socket, vùng nhớ chia sẻ, tín hiệu ([Bài 49](49-ipc.md)).

Hệ quả hay bị quên: **con trỏ chỉ có nghĩa trong một không gian địa chỉ**, nên gửi `std::vector<Node*>` sang tiến trình khác là vô nghĩa; phải "dẹt" dữ liệu thành byte rồi dựng lại ở bên kia.

### 7. Bảng quyết định

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Chia một mảng lớn trong RAM cho nhiều lõi cộng, dữ liệu đã có sẵn | **Luồng** | Chung bộ nhớ, không phải chép; mỗi luồng một đoạn riêng nên không cần khóa |
| Chạy mã không tin được hoặc hay crash (giải mã tệp lạ, plugin bên thứ ba) | **Tiến trình** | Crash chỉ giết con; có thể hạ quyền và giới hạn tài nguyên cho riêng con |
| Phần nào đó phải sống tiếp dù phần khác chết, hoặc cần khởi động lại riêng từng phần | **Tiến trình** | Cha làm "người giám sát": thấy con chết thì dựng lại |
| Chạy một chương trình khác có sẵn (công cụ dòng lệnh, ngôn ngữ khác) | **Tiến trình** | Là việc của `fork` + `exec` ([Bài 48](48-fork-exec-wait.md)) |
| Rất nhiều việc nhỏ, ngắn | Nhóm luồng (thread pool, [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)) | Chi phí tạo luồng đã lớn hơn việc; dùng lại luồng |
| Hàng nghìn kết nối chủ yếu chờ I/O | Không phải chọn giữa hai: vòng lặp sự kiện | [Bài 50](50-io-epoll-event-loop.md) |

**Khi nào KHÔNG nên chọn luồng:** mã chưa an toàn luồng và khó sửa; phần lớn thời gian thật ra là **giữ khóa** (các luồng xếp hàng, hết lợi); cần chắn lỗi cho phần mã dễ chết. **Khi nào KHÔNG nên chọn tiến trình:** hai bên phải chia sẻ cấu trúc dữ liệu phức tạp chứa con trỏ; cần rất nhiều đơn vị chạy (mỗi tiến trình nặng); việc ngắn hơn cả thời gian `fork`.

### 8. Goroutine nằm ở đâu trong bức tranh này

!!! info "Bạn biết Go?"
    **Goroutine ≠ thread ≠ process.** Cả chương trình Go là **một tiến trình**; runtime của nó ghép rất nhiều goroutine lên ít luồng hệ điều hành. Mình dựng chương trình Go (1.27.2, máy 8 lõi) tạo 10000 goroutine cùng chờ, rồi đọc `/proc/self/status`: `runtime.NumGoroutine()` ra 10001 (thêm goroutine của `main`) còn `Threads:` chỉ **9–10** (ba lần chạy ra 10, 9, 9). Làm vậy trong C++ là 10000 luồng thật, mỗi luồng một stack.

    Về cách ly, goroutine giống **luồng**, không giống tiến trình: mình chạy một `panic` trong goroutine không được `recover`, cả chương trình dừng, mã thoát 2, dù `main` đang ngủ. Muốn một tiến trình con riêng thì chạy chương trình khác bằng `os/exec`. Go cũng không có `thread_local`: goroutine có thể đổi luồng hệ điều hành giữa chừng, nên không có "biến riêng của luồng" để dựa vào.

## 💻 Ví dụ code

### A. Cùng một biến toàn cục: sau `fork` và sau `std::thread`

`fork()` (trong `<unistd.h>`) **nhân bản** tiến trình đang chạy: từ dòng sau đó có hai tiến trình, mỗi bên chạy tiếp từ cùng chỗ. Nó **trả về hai lần**: `0` ở tiến trình con, số `pid` của con ở tiến trình cha, `-1` nếu lỗi (`pid_t` là kiểu số nguyên chứa pid); nên `if (pid == 0)` tách việc của con.

`waitpid(pid, nullptr, 0)` (trong `<sys/wait.h>`) bắt cha chờ con chạy xong. `_exit(0)` kết thúc con ngay, không chạy phần dọn dẹp của C++ (để con không in lại thứ cha còn đệm); ta dùng `std::endl` để in ra ngay. [Bài 48](48-fork-exec-wait.md) giải thích kỹ hơn.

Chương trình dưới làm cùng một việc hai lần, với hai biến toàn cục: lần đầu qua `fork`, lần sau qua `std::thread`.

```cpp
#include <iostream>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>

int bienFork = 0;                                    // (1) hai biến toàn cục, cùng bắt đầu bằng 0
int bienLuong = 0;

int main() {
    pid_t pid = fork();                              // (2) nhân bản: từ đây có HAI tiến trình
    if (pid == -1) return 1;                         // (3) fork thất bại
    if (pid == 0) {                                  // (4) nhánh của tiến trình CON
        bienFork = 100;                              // (5) con sửa bản của con
        std::cout << "con:  bienFork = " << bienFork << ", &bienFork = " << &bienFork << std::endl;
        _exit(0);                                    // (6) con thoát ngay
    }
    waitpid(pid, nullptr, 0);                        // (7) cha chờ con xong
    std::cout << "cha:  bienFork = " << bienFork << ", &bienFork = " << &bienFork << std::endl;   // (8)

    std::thread t([] { bienLuong = 100; });          // (9) luồng phụ, CÙNG tiến trình, sửa bienLuong
    t.join();                                        // (10) chờ luồng phụ xong
    std::cout << "luong chinh: bienLuong = " << bienLuong << std::endl;                         // (11)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (2) | Hệ điều hành nhân bản; cha nhận `pid` của con, con nhận `0` | hai tiến trình, mỗi bên một `bienFork=0` |
| (4)–(5) | Chỉ con vào nhánh này, sửa `bienFork` **trong căn hộ của con** | con `100`, cha `0` |
| (6) | Con kết thúc | còn lại cha |
| (7)–(8) | Cha chờ con xong, in `bienFork` của **cha** | `0` |
| (9)–(11) | Luồng phụ sửa `bienLuong`; sau `join`, luồng chính in nó | chỉ **một** `bienLuong`, nay là `100` |

**Kết quả khi chạy** (một lần chạy thật, TSan và ASan đều sạch; địa chỉ đổi mỗi lần vì hệ điều hành xáo địa chỉ, nên số trên máy bạn khác, chỉ cái **mẫu** đáng nhớ):

```text
con:  bienFork = 100, &bienFork = 0x62887222f154
cha:  bienFork = 0, &bienFork = 0x62887222f154
luong chinh: bienLuong = 100
```

Cùng địa chỉ `0x…f154` mà con thấy `100`, cha thấy `0`: đó là bộ nhớ ảo của mục 3. Con thừa hưởng bản đồ giống hệt, nhưng khi con ghi, bảng trang của con trỏ sang một trang RAM riêng. Với luồng thì ngược lại: chỉ **một** biến, nên luồng chính thấy `100`. Hai cách tạo "nhánh chạy mới", hai đáp án trái nhau; đó là toàn bộ khác biệt về bộ nhớ.

### B. Đo chi phí tạo: tiến trình và luồng, bộ nhớ nhỏ và lớn

Hàm `tienTrinh` sinh một con rỗng rồi chờ nó, lặp lại; hàm `luong` làm tương tự với `std::thread`. Ta đo hai lần: khi tiến trình còn nhỏ, rồi sau khi cấp **128 MiB** bộ nhớ thật (ghi 1 vào từng byte, để RAM được cấp thật). `std::chrono::duration<double, std::micro>(troi).count()` đổi khoảng thời gian `troi` thành số thực tính bằng micro giây.

```cpp
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>

// Trung bình micro giây cho một lần sinh + chờ, lặp `lan` lần.
double tienTrinh(int lan) {
    auto bat = std::chrono::steady_clock::now();
    for (int i = 0; i < lan; ++i) {
        pid_t pid = fork();                           // (1) sinh một tiến trình con
        if (pid == 0) _exit(0);                       // (2) con không làm gì, thoát ngay
        waitpid(pid, nullptr, 0);                     // (3) cha chờ con xong rồi mới vòng sau
    }
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration<double, std::micro>(troi).count() / lan;
}

double luong(int lan) {
    auto bat = std::chrono::steady_clock::now();
    for (int i = 0; i < lan; ++i) {
        std::thread t([] {});                         // (4) sinh một luồng không làm gì
        t.join();                                     // (5) chờ nó xong
    }
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration<double, std::micro>(troi).count() / lan;
}

int main() {
    double tpNho = tienTrinh(200);
    double luongNho = luong(200);

    std::vector<char> lon(128 * 1024 * 1024, 1);      // (6) 128 MiB, RAM được cấp thật
    double tpLon = tienTrinh(20);
    double luongLon = luong(200);

    std::cout << "bo nho nho:   tien trinh " << tpNho << " us, luong " << luongNho << " us\n";
    std::cout << "bo nho 128 M: tien trinh " << tpLon << " us, luong " << luongLon << " us\n";
    std::cout << "tien trinh cham hon luong (bo nho nho)? " << (tpNho > luongNho) << "\n";
    std::cout << "fork cham hon it nhat 5 lan khi bo nho lon? " << (tpLon > tpNho * 5) << "\n";
    std::cout << "luong khong tang qua 5 lan? " << (luongLon < luongNho * 5) << "\n";
    return lon[0] == 1 ? 0 : 1;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ý nghĩa |
|---|---|---|
| (1)–(3) | Mỗi vòng: `fork`, con thoát, cha `waitpid` | đo trọn một vòng đời tiến trình con |
| (4)–(5) | Mỗi vòng: tạo luồng rỗng, `join` | đo trọn một vòng đời luồng |
| (6) | Cấp và ghi 128 MiB | bảng trang của cha giờ lớn |
| `main` | Đo lại cả hai, in số và ba câu trả lời `0`/`1` | chỉ ba câu `0`/`1` là cái đáng tin |

**Kết quả khi chạy** (một lần trong năm lần chạy thật, g++ không tối ưu; số micro giây **đổi theo máy** và theo lần, còn ba dòng `1` thì cả năm lần đều ra như vậy; một lần biên dịch `-O2` và một lần chạy dưới TSan cũng thế):

```text
bo nho nho:   tien trinh 220.849 us, luong 34.7375 us
bo nho 128 M: tien trinh 9699.48 us, luong 29.0291 us
tien trinh cham hon luong (bo nho nho)? 1
fork cham hon it nhat 5 lan khi bo nho lon? 1
luong khong tang qua 5 lan? 1
```

Trên máy mình: tiến trình con tốn chừng **6 lần** thời gian một luồng khi còn nhỏ, rồi hơn 100 lần khi cha giữ 128 MiB, trong khi luồng gần như không đổi. Lý do đúng như mục 4: `fork` phải chép bảng trang, bảng này lớn theo bộ nhớ.

**Thử thay đổi: đổi 128 thành 512 MiB.** Mình đã chạy: `fork` lên cỡ **30–40 ms** mỗi lần (so với cỡ 5–12 ms ở 128 MiB; số đổi theo lần chạy), luồng vẫn cỡ vài chục micro giây.

Số đo này chỉ có `fork` rồi thoát ngay, không có `exec` hay việc thật của con (ngoài đời `fork` hay đi kèm `exec`; có cách tạo con nhẹ hơn như `posix_spawn`, [Bài 48](48-fork-exec-wait.md)). Cái đáng nhớ là **hướng**: tiến trình đắt hơn và đắt thêm theo bộ nhớ; luồng thì không.

### C. Cách ly lỗi: con chết thì cha sống, luồng chết thì tất cả chết

`waitpid(pid, &trangThai, 0)` ghi vào `trangThai` một "giấy báo tử" của con. `WIFSIGNALED(trangThai)` cho biết con chết vì bị **tín hiệu** giết (như `SIGSEGV` ở [Bài 40](../nhom-5-he-thong-quy-trinh/40-gdb-nang-cao-core-dump.md)), `WTERMSIG(trangThai)` cho số của tín hiệu đó. `strsignal(số)` (trong `<cstring>`) đổi số tín hiệu thành tên chữ. `std::abort()` tự hủy bất thường, như khi một `assert` thất bại; nó gửi `SIGABRT` (số 6).

```cpp
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sys/wait.h>
#include <unistd.h>

int main() {
    pid_t pid = fork();
    if (pid == 0) {                                   // (1) nhánh con
        std::abort();                                 // (2) con tự hủy bất thường
        _exit(0);                                     // (3) không bao giờ tới đây
    }

    int trangThai = 0;
    waitpid(pid, &trangThai, 0);                      // (4) cha chờ con, lấy giấy báo tử
    if (WIFSIGNALED(trangThai)) {                     // (5) con chết vì bị tín hiệu giết?
        std::cout << "con chet vi tin hieu " << WTERMSIG(trangThai)      // (6) số tín hiệu
                  << " (" << strsignal(WTERMSIG(trangThai)) << ")\n";
    }
    std::cout << "cha van song va chay tiep\n";       // (7)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1)–(2) | Chỉ con vào nhánh này và tự `abort`; `(3)` không bao giờ chạy | con chết vì `SIGABRT` |
| (4)–(6) | Cha chờ, nhận giấy báo tử; con bị tín hiệu số 6 giết nên in ra | cha còn nguyên |
| (7) | Cha chạy tiếp bình thường | cha thoát mã 0 |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan và ASan sạch, mã thoát 0):

```text
con chet vi tin hieu 6 (Aborted)
cha van song va chay tiep
```

Con chết ở (2), cha không bị gì và còn biết con chết vì sao. Giờ cùng việc đó nhưng ở **luồng**: tiến trình chỉ có một, nên không ai ở lại để báo tin.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>

int main() {
    std::thread t([] {
        std::abort();                                 // (1) luồng phụ tự hủy bất thường
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(200));   // (2) luồng chính ngủ, chưa hề lỗi
    std::cout << "luong chinh van song?\n";           // (3) KHÔNG BAO GIỜ in ra
    t.join();
    return 0;
}
```

Khối này đặt `// bo-qua-kiem-tra` vì nó cố tình chết. Mình chạy: không in gì, tiến trình thoát với mã **134** (128 + 6, `SIGABRT`). Thay (1) bằng ghi vào `nullptr` (hành vi không xác định, kết quả trên máy mình): mã **139** (128 + 11, `SIGSEGV`). Thay bằng `throw 1;` không ai bắt: in `terminate called after throwing an instance of 'int'`, mã 134. Cả ba lần, luồng chính vô tội vẫn chết theo.

### D. Xem luồng bằng công cụ: `/proc`, `ps -L`, `strace`

Chương trình tạo ba luồng cùng ngủ 3 giây rồi tự đọc `/proc/self/status` (`self` là chính tiến trình đang chạy) để đếm luồng. Ba giây ngủ chỉ để bạn kịp gõ `ps` từ cửa sổ khác.

```cpp
#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

// Đọc dòng "Threads:" trong /proc/self/status: số luồng của tiến trình này.
std::string soLuong() {
    std::ifstream f("/proc/self/status");
    std::string dong;
    while (std::getline(f, dong)) {
        if (dong.rfind("Threads:", 0) == 0) {                       // (1) dòng bắt đầu bằng "Threads:"
            return dong.substr(dong.find_first_of("0123456789"));   // (2) giữ phần chữ số
        }
    }
    return "?";
}

int main() {
    std::cout << "luc dau:         " << soLuong() << " luong" << std::endl;

    std::vector<std::thread> cacLuong;
    for (int i = 0; i < 3; ++i) {
        cacLuong.emplace_back([] {
            std::this_thread::sleep_for(std::chrono::seconds(3));   // (3) mỗi luồng phụ ngủ 3 giây
        });
    }
    std::cout << "khi co 3 luong: " << soLuong() << " luong" << std::endl;   // (4) tạo xong, chúng còn ngủ

    for (std::thread& t : cacLuong) t.join();         // (5) chờ cả ba
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số luồng của tiến trình |
|---|---|---|
| đầu `main` | Mới chỉ có luồng chính | 1 |
| (3) | Ba luồng phụ được tạo, mỗi luồng ngủ 3 giây | 1 + 3 |
| (4) | Đọc lại `/proc/self/status` khi ba luồng còn sống | 4 |
| (5) | `join` đợi ba luồng ngủ xong (cả chương trình mất cỡ 3 giây) | về 1 |

**Kết quả khi chạy** (ba lần liền đều như nhau; dưới TSan dòng thứ hai ra `5`, vì TSan thêm một luồng nền của chính nó):

```text
luc dau:         1 luong
khi co 3 luong: 4 luong
```

Mình biên dịch thành `xem_luong`, chạy nền (`./xem_luong &` rồi `PID=$!` để giữ số hiệu tiến trình), và trong lúc nó ngủ gõ `ps` và đọc `/proc`:

```text
$ ps -L -p $PID -o pid,lwp,nlwp,comm
    PID     LWP NLWP COMMAND
 336915  336915    4 xem_luong
 336915  336917    4 xem_luong
 336915  336918    4 xem_luong
 336915  336919    4 xem_luong
$ grep -E "^(Name|Pid|Threads)" /proc/$PID/status
Name:	xem_luong
Pid:	336915
Threads:	4
```

`-L` liệt kê **từng luồng**: cột `PID` giống nhau, cột `LWP` (số hiệu luồng, chính là `tid`) khác nhau, và dòng đầu có `LWP` bằng `PID` là luồng chính. `NLWP` là tổng số luồng. Số trên máy bạn khác.

Cuối cùng, chứng cứ cho thấy hai khái niệm thực ra là một. Mình chạy chương trình ở A dưới `strace -f -e trace=clone,clone3` ([Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)); đây là hai dòng của nó, lược bớt đoạn cuối:

```text
fork:         clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, ...) = 337207
std::thread:  clone3({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|CLONE_SETTLS|..., ...})
```

Trên Linux, cả hai là lời gọi hệ thống tạo một "task" mới (`clone`, đời mới hơn là `clone3`); khác nhau chỉ ở **cờ chia sẻ**. Luồng bật `CLONE_VM` (chung bộ nhớ), `CLONE_FILES` (chung bảng tệp), `CLONE_SIGHAND` (chung cách xử lý tín hiệu), `CLONE_THREAD` (cùng nhóm luồng, nên chung `pid`); `fork` không bật cờ nào trong số đó nên con có bản riêng của từng thứ. Đây chính là bảng ở mục 1, viết thành cờ.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Process và thread khác nhau thế nào?"
    Mình trả lời theo bốn góc. **Bộ nhớ:** mỗi tiến trình có không gian địa chỉ ảo riêng; các luồng trong một tiến trình chung code, biến toàn cục, heap, và riêng stack, thanh ghi, `thread_local`. **Chi phí:** tạo tiến trình đắt hơn (phải dựng bảng trang, đắt theo bộ nhớ của cha), và đổi giữa hai tiến trình phải đổi bảng trang nên TLB và bộ đệm nguội; đổi giữa luồng cùng tiến trình chỉ đổi thanh ghi. **Cách ly:** luồng crash kéo cả tiến trình, tiến trình con crash thì cha vẫn sống. **Giao tiếp:** luồng đọc ghi thẳng bộ nhớ chung và phải khóa; tiến trình phải qua IPC (pipe, socket, shared memory, signal). "Vì sao đổi luồng rẻ hơn đổi tiến trình?" Đổi luồng cùng tiến trình chỉ cất và nạp thanh ghi; đổi tiến trình phải đổi sang bảng trang khác, mà TLB (bộ đệm các kết quả tra địa chỉ ảo sang thật) của tiến trình cũ vô dụng với tiến trình mới (CPU đời mới gắn nhãn tiến trình vào mục TLB để khỏi xóa sạch, nhưng bộ đệm vẫn nguội). Nối tiếp khác: "Thế luồng có chung stack không?" Không, mỗi luồng một stack; nhưng cùng một không gian địa chỉ nên luồng này vẫn truy cập được stack luồng kia qua con trỏ, nên "riêng" là về bố trí, không phải về bảo vệ.

??? question "Một thread bị segfault thì sao? Còn process con bị segfault?"
    `SIGSEGV` là tín hiệu gửi cho **tiến trình**, và mặc định giết cả tiến trình, nên mọi luồng chết theo; `try`/`catch` không bắt được nó. Ngoại lệ không bắt được trong hàm luồng cũng gọi `std::terminate` rồi `abort`, cùng hậu quả. Tiến trình con bị segfault thì chỉ con chết; cha chờ bằng `waitpid` và đọc `WIFSIGNALED`/`WTERMSIG` để biết con chết vì tín hiệu nào, rồi quyết định dựng lại hay ghi log. "Vậy muốn chạy mã không tin được thì sao?" Đặt nó vào tiến trình con (và hạ quyền con), vì đó là ranh giới mà một luồng không có.

??? question "Sau fork, con sửa biến toàn cục thì cha có thấy không? Sao địa chỉ in ra lại giống nhau?"
    Không thấy: sau `fork` mỗi bên có bản riêng, nên con sửa thì chỉ con thấy. Địa chỉ giống nhau vì đó là địa chỉ **ảo**: con thừa hưởng bản đồ ảo của cha, rồi bảng trang của mỗi bên trỏ tới trang RAM riêng khi có ghi (copy-on-write). Với `std::thread` thì ngược lại: chung một biến, sửa là cả hai thấy, nên phải đồng bộ.

??? question "Chrome dùng tiến trình hay luồng? Vì sao?"
    Cả hai, ở hai tầng khác nhau. Trình duyệt kiểu đó tách các trang web (và phần hiển thị so với phần điều phối) vào **tiến trình riêng**, để một trang treo hay crash không kéo cả trình duyệt, và để mã của một trang khó đọc bộ nhớ của trang khác (ranh giới do hệ điều hành bảo vệ). Cái giá là tốn RAM hơn và phải nhắn tin giữa các tiến trình. **Bên trong** mỗi tiến trình vẫn dùng nhiều luồng cho việc cần chung dữ liệu và chạy song song (mạng, giải mã, giữ giao diện không đứng). Nguyên lý: tiến trình để cách ly và an toàn, luồng để chia sẻ dữ liệu và tiết kiệm.

??? question "Goroutine của Go là thread hay process? Vậy sao C++ không tạo hàng chục nghìn thread như tạo goroutine?"
    Goroutine không phải thread, càng không phải process: runtime Go ghép chúng lên ít luồng hệ điều hành và tự lập lịch, stack khởi đầu nhỏ và tự lớn lên. Mình đã chạy 10000 goroutine chờ mà tiến trình chỉ có cỡ 10 luồng. `std::thread` là luồng hệ điều hành thật: mỗi cái có stack riêng và do nhân lập lịch, nên tạo hàng chục nghìn là tốn bộ nhớ và chi phí đổi luồng. Muốn nhiều đơn vị việc nhẹ thì dùng nhóm luồng hoặc vòng lặp sự kiện ([Bài 50](50-io-epoll-event-loop.md)).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng thêm luồng luôn làm chương trình nhanh hơn"
    Tạo một luồng đã tốn cỡ vài chục micro giây (mình đo ra cỡ 30–50 µs), nên với việc chỉ cỡ vài micro giây thì luồng làm chậm đi; việc tính toán thuần cũng không nhanh hơn số lõi. Dùng nhóm luồng cho việc nhỏ, và đo.

!!! warning "Lỗi 2: Nhầm hành vi biến toàn cục giữa `fork` và `std::thread`"
    Sau `fork`, con sửa biến thì cha **không** thấy; sau `std::thread`, sửa là **chung**. Mình đã chạy cả hai ở mục A: `0` và `100`. Tưởng chung mà thực ra riêng thì cập nhật của con mất hút; tưởng riêng mà thực ra chung thì gây data race.

!!! warning "Lỗi 3: Tin `try`/`catch` bảo vệ được khỏi crash của luồng"
    Lỗi truy cập bộ nhớ và `abort()` là **tín hiệu**, không phải ngoại lệ C++; ngoại lệ lọt ra khỏi hàm luồng thì gọi `std::terminate`. Mình đã chạy ba kiểu: luồng phụ chết, luồng chính chết theo (mã 134, 139, 134). Cần chắn lỗi thật thì dùng tiến trình con.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="47" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Dịch vụ của bạn nhận ảnh người dùng gửi lên và giải mã bằng một thư viện bên thứ ba, thỉnh thoảng thư viện crash với tệp lạ. Dịch vụ phải sống tiếp khi một tệp làm hỏng thư viện. Nên làm gì?

- Giải mã trong một luồng riêng, vì luồng rẻ hơn tiến trình nhiều
- Giải mã ở luồng chính và đặt `try`/`catch` bao quanh lời gọi thư viện
- Giải mã trong tiến trình con, cha chờ và đọc trạng thái thoát của con
- Giải mã trong luồng phụ rồi `detach` để lỗi không lan sang luồng chính

<p class="giai-thich" markdown>Crash do truy cập bộ nhớ sai hay `abort` là tín hiệu giết cả tiến trình, nên `catch` không chặn được và luồng nào cũng chết chung với dịch vụ, dù rẻ hơn. `detach` chỉ đổi cách chờ luồng chứ không đổi nơi nó chạy, nên luồng phụ crash vẫn kéo cả tiến trình. Tiến trình con có bản đồ bộ nhớ riêng, nên chỉ con chết; cha nhận trạng thái "chết vì tín hiệu", ghi log rồi xử lý tệp kế.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau (`x` là biến toàn cục `int`). Tiến trình cha in ra gì?

```text
int x = 1;
pid_t p = fork();
if (p == 0) { x = 2; _exit(0); }
waitpid(p, nullptr, 0);
std::cout << x;
```

- `1`, vì con chỉ sửa bản `x` của chính nó
- `2`, vì con đã thoát nên cha thấy giá trị cuối cùng
- `2`, vì biến toàn cục thì mọi tiến trình dùng chung
- Không xác định, vì cha và con cùng ghi vào `x`

<p class="giai-thich" markdown>Sau `fork` mỗi tiến trình có bản đồ bộ nhớ riêng nên con ghi `x` chỉ đổi bản của con, và cha in `1`. "Toàn cục thì chung" đúng cho các luồng, nhưng sai giữa hai tiến trình: toàn cục chỉ chung **trong một** tiến trình. Việc con thoát hay chưa không quyết định gì, và cha không ghi `x` nên chẳng có tranh chấp nào để gọi là không xác định.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. Luồng chính tạo một luồng phụ chạy `[] { g = 1; t = 1; }`, `join` nó, rồi in `g` và `t`. Kết quả?

```text
int g = 0;
thread_local int t = 0;
```

- `1 1`, vì mọi biến toàn cục đều chung giữa các luồng
- `0 0`, vì luồng phụ chỉ sửa một bản sao của cả hai biến
- `0 1`, vì `thread_local` chung cho mọi luồng còn `g` thì riêng
- `1 0`, vì `g` chung còn `t` mỗi luồng một bản

<p class="giai-thich" markdown>`g` là biến toàn cục thường nên cả hai luồng cùng một biến và luồng chính thấy `1`. `t` có từ khóa `thread_local` nên luồng phụ ghi vào bản của nó, bản của luồng chính vẫn `0`. Nghĩ rằng mọi toàn cục đều chung bỏ qua `thread_local`, và nghĩ luồng phụ chỉ sửa bản sao là nhầm luồng với tiến trình sau `fork`. Đáp án `0 1` đảo ngược hẳn vai trò của hai biến.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Một mảng 100 triệu số đã nằm sẵn trong RAM; cần tính tổng bình phương thật nhanh trên máy 8 lõi. Cách nào hợp lý nhất?

- Sinh 8 tiến trình con và gửi từng đoạn mảng qua pipe, vì tiến trình an toàn hơn
- Tạo 8 luồng, mỗi luồng cộng một đoạn riêng, cuối cùng cộng 8 kết quả sau `join`
- Tạo 8 luồng cùng cộng vào một biến chung, mỗi lần cộng đều khóa mutex
- Chạy một luồng duy nhất, vì chia việc cho nhiều lõi luôn tốn hơn lợi

<p class="giai-thich" markdown>Dữ liệu đã nằm trong bộ nhớ của tiến trình nên các luồng đọc chung được ngay, không chép gì; mỗi luồng ghi tổng riêng nên không cần khóa, rồi gộp một lần sau `join`. Dùng tiến trình buộc phải chép dữ liệu qua pipe, tốn hơn cả phép tính. Khóa mutex ở mỗi lần cộng làm cả tám luồng xếp hàng và mất lợi từ nhiều lõi. Còn một luồng thì bỏ phí bảy lõi, trong khi việc này chia rất đều.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Vì sao đổi (context switch) giữa hai luồng của cùng một tiến trình thường rẻ hơn đổi giữa hai tiến trình?

- Luồng không có thanh ghi riêng nên hệ điều hành chẳng phải cất trạng thái nào
- Hệ điều hành bỏ qua việc lập lịch luồng, các luồng tự chia lõi với nhau
- Không phải đổi bản đồ bộ nhớ, nên bản dịch địa chỉ trong TLB vẫn dùng được
- Các luồng dùng chung một stack nên không phải nạp lại stack khi đổi

<p class="giai-thich" markdown>Hai luồng cùng tiến trình chung bảng trang, nên nhân không phải đổi bản đồ và TLB (bộ nhớ đệm của phép đổi địa chỉ ảo sang thật) vẫn hợp lệ. Mỗi luồng vẫn có thanh ghi và stack riêng, nên các lý do "không có thanh ghi riêng" hay "chung một stack" là sai về sự thật. Và chính nhân lập lịch luồng chứ luồng không tự chia lõi nhau.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Có 100000 việc nhỏ, mỗi việc tính chừng 10 micro giây, trên máy 8 lõi. Cách nào đúng hướng nhất?

- Một nhóm vài luồng có sẵn, lấy việc dần từ hàng đợi
- Một tiến trình con mới cho mỗi việc, vì tiến trình cách ly lỗi tốt
- Một luồng mới cho mỗi việc, vì luồng rẻ nên chi phí không đáng kể
- Một luồng mới cho mỗi việc rồi `detach`, vì `detach` làm luồng nhẹ hơn

<p class="giai-thich" markdown>Tạo một luồng đã tốn cỡ vài chục micro giây, lớn hơn chính việc, nên tạo mới cho mỗi việc làm chương trình chậm đi; nhóm luồng có sẵn trả chi phí đó một lần. Tiến trình còn đắt hơn nhiều, và cách ly lỗi là lợi ích không ai cần cho việc tính thuần. Coi luồng là "rẻ nên không đáng kể" chỉ đúng khi việc đủ lớn. `detach` chỉ đổi cách kết thúc luồng, không giảm chi phí tạo nó.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc dòng `strace` sau, được in khi một chương trình bắt đầu một việc. Nó cho biết điều gì?

```text
clone3({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|..., ...})
```

- Tạo một tiến trình con có bản đồ bộ nhớ riêng, vì có tên `clone3`
- Tạo tiến trình con, vì `CLONE_FILES` nghĩa là chép riêng bảng tệp đang mở
- Tạo luồng mới nhưng bộ nhớ riêng, vì `CLONE_VM` nghĩa là sao chép bộ nhớ
- Tạo luồng mới trong cùng tiến trình, vì các cờ báo chia sẻ bộ nhớ

<p class="giai-thich" markdown>Các cờ `CLONE_` là danh sách những thứ **được chia sẻ** với tác vụ mới: `CLONE_VM` chung bộ nhớ, `CLONE_FILES` chung bảng tệp, `CLONE_THREAD` cùng nhóm luồng, nên đây là một luồng. Có tên `clone3` chưa đủ kết luận, vì `fork` cũng đi qua nhóm lời gọi `clone`, chỉ là không bật các cờ chia sẻ này. Các phương án nói `CLONE_FILES` là chép riêng hay `CLONE_VM` là sao chép bộ nhớ đều đọc ngược nghĩa cờ: cờ bật nghĩa là chung, không phải chép riêng.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Bộ nhớ:** mỗi tiến trình có không gian địa chỉ ảo riêng (cùng địa chỉ, hai giá trị: mình chạy `fork` ra `0` ở cha, `100` ở con); các luồng chung code, toàn cục, heap, tệp mở và cách xử lý tín hiệu, riêng stack, thanh ghi, `thread_local` (mình chạy `std::thread` ra `100` ở cả hai).
2. **Chi phí:** tạo tiến trình phải dựng bảng trang nên đắt hơn và đắt theo bộ nhớ (mình đo `fork` cỡ 0,2 ms khi tiến trình nhỏ, cỡ 10 ms với 128 MiB; luồng cỡ 30 µs, không đổi); đổi luồng cùng tiến trình chỉ đổi thanh ghi, đổi tiến trình phải đổi bảng trang nên TLB và bộ đệm nguội.
3. **Cách ly và giao tiếp:** luồng crash kéo cả tiến trình (mình chạy: mã 134, 139) vì `SIGSEGV`/`abort` là chuyện của tiến trình, `try`/`catch` không bắt; tiến trình con crash thì cha còn sống và đọc được `WTERMSIG`. Luồng giao tiếp qua bộ nhớ chung và phải khóa; tiến trình phải qua IPC ([Bài 49](49-ipc.md)), và con trỏ chỉ có nghĩa trong một không gian địa chỉ.
4. **Chọn:** luồng khi chia sẻ nhiều dữ liệu và tin cậy nhau; tiến trình khi cần cách ly lỗi/quyền, chạy chương trình khác, hay mã không tin được; nhóm luồng cho việc nhỏ, vòng lặp sự kiện cho hàng nghìn kết nối ([Bài 50](50-io-epoll-event-loop.md)). Không dùng luồng khi mọi thứ phải giữ khóa, không dùng tiến trình khi phải chia sẻ cấu trúc chứa con trỏ.
5. Trên Linux cả hai đều là `clone`, khác nhau ở cờ chia sẻ (`CLONE_VM`, `CLONE_THREAD`...); xem bằng `ps -L` (cột `LWP`, `NLWP`) hoặc `Threads:` trong `/proc/PID/status`. Goroutine không phải luồng: mình chạy 10000 goroutine trên cỡ 10 luồng hệ điều hành, nhưng `panic` không `recover` vẫn giết cả chương trình như luồng crash.
