# Bài 42 — Soi tiến trình và đo hiệu năng: strace, perf, gprof, gcov

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `strace` để thấy chương trình xin hệ điều hành làm gì (mở tệp không có thì thấy `ENOENT`, chương trình treo thì thấy nó kẹt ở lời gọi nào), và đọc `/proc/PID` để xem trạng thái, tệp đang mở, bộ nhớ.
    - Đo thời gian đúng cách (`time`, `std::chrono`, `-O2`, chạy nhiều lần, tránh bẫy trình biên dịch xóa mất vòng lặp), rồi tìm chỗ chậm bằng `gprof` và chỗ chưa được kiểm thử bằng `gcov`.
    - Biết `perf` làm gì, vì sao máy mình chặn `perf record`, và áp dụng vòng lặp **đo → giả thuyết → sửa → đo lại**.

**Bạn cần biết trước:** [Bài 38](38-bien-dich-lien-ket-build.md) (`-g`, `-O0` và `-O2`, `-fno-omit-frame-pointer`), [Bài 39](39-gdb-co-ban.md) và [Bài 40](40-gdb-nang-cao-core-dump.md) (gdb), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, để nối với `futex`).

## 🧠 Câu chuyện mở đầu

Một **quán ăn** nhận món chậm, và bạn là chủ quán đi tìm lý do. Bạn có sáu dụng cụ.

**`strace`** là người đứng cửa bếp, ghi lại mọi lần ai đó **nhờ bếp** (hệ điều hành) làm gì: lấy nguyên liệu, rửa bát, báo "đã xong". **`time`** là chiếc đồng hồ bấm giờ cả bữa. **`gprof`** là sổ chấm công: mỗi đầu bếp làm bao nhiêu phút. **`gcov`** là bảng đánh dấu món nào trong thực đơn **đã từng được nấu** và món nào chưa bao giờ. **`perf`** là camera chụp ảnh mỗi mili-giây xem ai đang làm gì.

Nhưng cẩn thận: bấm giờ lúc bếp đang chật khách, đo lúc bếp vừa mở cửa (nồi còn lạnh), hay đo khi một đầu bếp tình cờ nghỉ, đều cho số khác nhau. **Đo được số** chưa phải **đo đúng**.

!!! info "Chỗ nào ví dụ quán ăn không còn đúng?"
    Người ghi sổ ngoài đời không làm chậm bếp. Dụng cụ đo của chương trình thì có: `strace` làm chương trình chậm đi nhiều lần, `-pg` chèn mã đếm vào, `perf` lấy mẫu thì nhẹ hơn. Vì vậy đo xong phải nhớ rằng bạn đang đo **chương trình có dụng cụ**.

## 📖 Giải thích

### 1. `strace`: chương trình nhờ hệ điều hành làm gì

Chương trình của bạn không tự mở tệp, tự ghi ra màn hình hay tự ngủ được: nó **nhờ hệ điều hành** qua các lời gọi hệ thống (**system call**, như `openat`, `read`, `write`, `futex`). `strace` chạy chương trình rồi in từng lời gọi như vậy, kèm kết quả. Chương trình thử nghiệm: mở một tệp không có.

```cpp
// bo-qua-kiem-tra
#include <fstream>
#include <iostream>
#include <string>

int main() {
    std::ifstream tep("cau_hinh.txt");
    if (!tep) {
        std::cout << "khong mo duoc tep" << std::endl;
        return 1;
    }
    std::string dong;
    std::getline(tep, dong);
    std::cout << "dong dau: " << dong << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 7 | Mở `cau_hinh.txt` (tương đối so với thư mục đang chạy) |
| 8–11 | Mở không được thì in thông báo và trả mã 1 |
| 13–15 | Mở được thì đọc dòng đầu và in |

Chương trình chỉ nói "không mở được", không nói **vì sao** (không có tệp? không có quyền?). `strace` trả lời. Lệnh `strace -o st.txt ./doc_tep` ghi vào tệp (mình đếm 68 dòng, phần lớn là nạp thư viện), và ba dòng quan trọng nằm gần cuối. Lọc bằng `-e trace=openat,write` (chỉ hai loại lời gọi) cho đầu ra gọn:

```text
$ strace -e trace=openat,write ./doc_tep
openat(AT_FDCWD, "/lib/x86_64-linux-gnu/libm.so.6", O_RDONLY|O_CLOEXEC) = 3
openat(AT_FDCWD, "cau_hinh.txt", O_RDONLY) = -1 ENOENT (No such file or directory)
write(1, "khong mo duoc tep\n", 18)     = 18
+++ exited with 1 +++
```

Dòng giữa là đáp án: `openat(... "cau_hinh.txt" ...) = -1 ENOENT (No such file or directory)`.

**ENOENT** là mã lỗi "không có tệp hay thư mục đó". Dòng kế, `write(1, ...)` là chương trình in thông báo ra đầu ra chuẩn (số `1`). `exited with 1` là mã thoát. Các cờ hay dùng, mình đều thử:

| Cờ | Việc | Ví dụ |
|---|---|---|
| `-e trace=openat,write` | Chỉ hiện loại lời gọi đó | Lọc nhiễu |
| `-c` | Không in từng dòng, in **bảng đếm** cuối chương trình | Cột `calls`, `errors`, `% time` cho mỗi loại; chương trình trên có 6 `openat`, 1 lỗi |
| `-T` | Thêm thời gian mỗi lời gọi | `... = -1 ENOENT ... <0.000023>` |
| `-o tệp` | Ghi ra tệp thay vì màn hình | Đầu ra dài |
| `-f` | Theo dõi cả luồng/tiến trình con | Chương trình đa luồng |

**Chương trình bị treo.** Chương trình sau hỏi tuổi bằng `cin`, rồi chờ:

```cpp
#include <iostream>

int main() {
    int tuoi = 0;
    std::cout << "nhap tuoi: " << std::flush;
    std::cin >> tuoi;
    std::cout << "tuoi = " << tuoi << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 5 | In lời nhắc và **đổ bộ đệm ngay** (`flush`), để lời nhắc hiện trước khi đọc |
| 6 | `cin >> tuoi` đọc một số từ đầu vào chuẩn: nếu chưa có gì để đọc, nó **chờ** |
| 7 | In tuổi (nếu đầu vào hỏng hay đóng, `tuoi` là 0 và vẫn in `tuoi = 0`) |

Mình cho đầu vào là một ống không bao giờ có dữ liệu (`sleep 6 | ...`) và chạy dưới `strace` có `timeout 2`:

```text
$ sleep 6 | timeout 2 strace -e trace=read,write ./cho_nhap
read(3, "\177ELF\2\1\1\0\0\0\0\0\0\0\0\0\3\0>\0\1\0\0\0\0\0\0\0\0\0\0\0"..., 832) = 832
write(1, "nhap tuoi: ", 11nhap tuoi: )             = 11
read(0, strace: Process … detached
 <detached ...>
```

Dòng cuối là chìa khóa: `read(0, ` **không có dấu `=` và kết quả**: lời gọi `read` đầu vào chuẩn (số `0`) đã bắt đầu mà chưa trả về. Chương trình không "đang tính" mà đang **chờ đầu vào**; `timeout` rồi gỡ `strace`. Cùng cách đó với chương trình deadlock của [Bài 40](40-gdb-nang-cao-core-dump.md): chạy dưới `strace -f` cho thấy ba luồng kẹt ở `futex(..., FUTEX_WAIT_PRIVATE, ...)` suốt, không dòng nào trả về.

Hai lưu ý.

`strace -p <PID>` (gắn vào tiến trình đang chạy) cũng bị `ptrace_scope` chặn như `gdb -p` ([Bài 40](40-gdb-nang-cao-core-dump.md)): `ptrace(PTRACE_SEIZE, ...): Operation not permitted`, nên mình chạy từ đầu dưới `strace`.

Và `strace` làm chương trình chậm đi nhiều, đừng đo thời gian khi đang dùng nó. Công cụ cùng họ, **`ltrace`**, theo dõi lời gọi *hàm thư viện* thay vì lời gọi hệ thống; máy mình không có nên chỉ nhắc tên.

### 2. `/proc/PID`: hỏi chính hệ điều hành

Linux phơi trạng thái mọi tiến trình thành các "tệp" dưới `/proc/<PID>/`. Đọc chúng không cần công cụ nào, và với tiến trình của chính bạn không cần quyền đặc biệt. Mình chạy `cho_nhap` ở trên với đầu vào là `sleep 8 |` rồi đọc:

```text
$ grep -E "^(Name|State|Threads|VmRSS)" /proc/$PID/status
Name:	cho_nhap
State:	S (sleeping)
VmRSS:	    3344 kB
Threads:	1
$ ls -l /proc/$PID/fd           (cột cuối)
0 -> pipe:[53517837]
1 -> /dev/null
2 -> /dev/null
$ cat /proc/$PID/wchan
anon_pipe_read
```

- **`status`**: `State: S (sleeping)` là đang ngủ chờ; `VmRSS` là RAM thật đang dùng; `Threads` là số luồng.
- **`fd`**: các tệp đang mở. Số `0`, `1`, `2` là vào, ra, lỗi chuẩn. Ở đây đầu vào (`0`) là một **ống** (pipe), đầu ra đi vào `/dev/null`.
- **`wchan`**: chương trình đang ngủ ở đâu trong nhân: `anon_pipe_read` nghĩa là đang chờ đọc ống. Khớp với `read(0, ` ở `strace`.
- **`maps`** liệt kê vùng nhớ: dòng `[heap]`, `[stack]`, các thư viện `.so`, và chính tệp chương trình (mình đếm 40 dòng).

`lsof -p <PID>` hiện cùng thông tin về tệp mở theo bảng dễ đọc hơn (cột `FD`, `TYPE`, `NAME`; có mặt trên máy mình), còn `ss -tlnp` liệt kê các cổng mạng đang lắng nghe ([Bài 44](44-mang-socket.md)). Mình chỉ nhắc, không dán đầu ra.

### 3. Đo thời gian: `time`, `std::chrono`, và `-O2`

Hai cách đo. **`time ./prog`** (lệnh của shell) đo cả tiến trình và cho ba con số: `real` (thời gian đồng hồ treo tường), `user` (CPU chạy mã của bạn), `sys` (CPU chạy trong nhân). **`std::chrono::steady_clock`** đo một **đoạn** trong code. Chương trình sau cộng bình phương 50 triệu số:

```cpp
#include <chrono>
#include <iostream>
#include <vector>

long tongBinhPhuong(const std::vector<int>& v) {
    long tong = 0;
    for (int x : v) {
        tong += static_cast<long>(x) * x;
    }
    return tong;
}

int main() {
    std::vector<int> v(50'000'000, 3);
    auto batDau = std::chrono::steady_clock::now();
    long kq = tongBinhPhuong(v);
    auto ketThuc = std::chrono::steady_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(ketThuc - batDau).count();
    std::cout << "kq = " << kq << ", mat " << ms << " ms" << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 5–11 | Hàm cộng `x * x` cho mọi phần tử, ép sang `long` trước khi nhân để khỏi tràn `int` |
| 14 | `vector` 50 triệu số `3`: tạo **trước** khi bấm giờ |
| 15 | Ghi mốc thời gian đầu bằng `steady_clock` (đồng hồ chỉ đi tới, không nhảy khi chỉnh giờ hệ thống) |
| 16 | Chạy hàm cần đo |
| 17–18 | Ghi mốc cuối, đổi hiệu hai mốc sang mili-giây |
| 19 | In kết quả và thời gian |

Mình biên dịch hai lần và chạy mỗi bản **năm lần liền** (kết quả luôn `kq = 450000000`):

```text
-O0 : 179, 175, 178, 175, 178 ms
-O2 :  29,  22,  22,  22,  21 ms
```

Ba bài học.

Một: bản `-O2` nhanh hơn `-O0` khoảng **8 lần** (số đổi theo máy). **Đo hiệu năng phải dùng `-O2`** ([Bài 38](38-bien-dich-lien-ket-build.md)); `-O0` còn cho kết luận sai về chỗ nào chậm.

Hai: **chạy nhiều lần**. Lần `-O2` đầu (29 ms) chậm hơn bốn lần sau (21–22 ms) vì bộ nhớ và bộ nhớ đệm CPU còn **lạnh**, chưa nạp.

Ba: `time ./prog` bản `-O2` cho `real 0.163 s`, `user 0.053 s`, `sys 0.110 s`. Cả chương trình lâu hơn nhiều so với 22 ms đo trong hàm, và phần lớn nằm ở `sys`, tức nhân (cấp phát và chạm vào 200 MB của vector, dòng 14), chứ không ở phép tính. `chrono` đo **đoạn bạn chọn**, `time` đo cả bữa.

### 4. Bẫy đo: trình biên dịch xóa vòng lặp, và nhiễu

**Bẫy 1: vòng lặp biến mất.** Muốn đo "cộng 300 triệu lần mất bao lâu", bạn viết:

```cpp
#include <chrono>
#include <iostream>

int main() {
    auto batDau = std::chrono::steady_clock::now();
    long tong = 0;
    for (int i = 0; i < 300'000'000; ++i) {
        tong += i;
    }
    auto ketThuc = std::chrono::steady_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(ketThuc - batDau).count();
    std::cout << "mat " << ms << " ms" << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 5 | Mốc đầu |
| 6–9 | Vòng lặp cộng dồn vào `tong`, **mà không dòng nào dùng `tong`** về sau |
| 10–12 | Mốc cuối và in thời gian |

Mình thấy `-O0`: **527 ms** và **568 ms**. Với `-O2`: **0 ms** cả hai lần.

Không phải máy nhanh một nghìn lần: mình dịch ngược `main` của bản `-O2` bằng `objdump -d`, và hai lời gọi `steady_clock::now()` đứng **sát nhau**, không có vòng lặp nào giữa. Vì `tong` không được dùng, trình biên dịch coi cả vòng lặp là thừa và xóa nó (được phép: kết quả quan sát được không đổi).

Thử "dùng" `tong` bằng cách in nó ra: **vẫn 0 ms**. g++ thấy vòng lặp cộng `0 + 1 + ... + 299999999` có công thức và tính sẵn lúc biên dịch (mình thấy in ra đúng `tong = 44999999850000000`).

Muốn buộc vòng lặp thật sự chạy, khai báo `volatile long tong` ("đừng giả định, mỗi lần đọc/ghi phải xảy ra thật"); với 100 triệu vòng mình thấy 78, 81, 64 ms. Quy tắc: nếu số đo **bằng 0 hay nhanh đến vô lý**, nghi trình biên dịch đã bỏ đoạn đó.

**Bẫy 2: nhiễu.** Cùng một chương trình, cùng một bản biên dịch, mình chạy tám lần liền trên máy (đang có việc khác chạy) và nhận các số từ 103 đến 189 ms cho một chương trình đáng lẽ ổn định. Máy mình có lõi CPU nhanh và lõi chậm lẫn lộn, và hệ điều hành đẩy chương trình qua lại. Mình ghim chương trình vào từng lõi bằng `taskset -c N ./prog`:

```text
taskset -c 0 : 165 100 106  99  95    ms      <- lõi nhanh (lần đầu lạnh)
taskset -c 4 : 247 175 175 175 183    ms      <- lõi chậm
```

Số liệu nay ổn định **trong từng lõi**, và khác nhau giữa các lõi 1,8 lần. Bài học: báo cáo **nhiều lần chạy** (nhỏ nhất hoặc trung vị), bỏ lần đầu, ghim lõi nếu máy có lõi khác loại, và không so sánh số đo giữa hai máy.

### 5. `gprof`: ai ngốn thời gian nhất

**`gprof`** dựa trên mã đếm mà `g++ -pg` chèn vào: nó đếm số lần gọi mỗi hàm, và cứ 0,01 giây lấy mẫu "đang ở hàm nào". Chương trình thử đếm số nguyên tố dưới 2 triệu và cộng các số chẵn:

```cpp
#include <iostream>

bool laNguyenTo(int n) {
    if (n < 2) {
        return false;
    }
    for (int d = 2; d * d <= n; ++d) {
        if (n % d == 0) {
            return false;
        }
    }
    return true;
}

int demNguyenTo(int gioiHan) {
    int dem = 0;
    for (int n = 0; n < gioiHan; ++n) {
        if (laNguyenTo(n)) {
            ++dem;
        }
    }
    return dem;
}

long tongChan(int gioiHan) {
    long tong = 0;
    for (int n = 0; n < gioiHan; n += 2) {
        tong += n;
    }
    return tong;
}

int main() {
    std::cout << "so nguyen to: " << demNguyenTo(2'000'000) << std::endl;
    std::cout << "tong chan: " << tongChan(2'000'000) << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 3–13 | `laNguyenTo`: thử chia cho mọi `d` từ 2 tới căn bậc hai của `n` |
| 15–23 | `demNguyenTo`: gọi `laNguyenTo` cho mọi `n` dưới `gioiHan` |
| 25–31 | `tongChan`: cộng các số chẵn (rất rẻ) |
| 34–35 | In hai kết quả; chạy ra `148933` và `999999000000` |

Biên dịch kèm `-pg` (mình dùng `-O1 -fno-inline` để mỗi hàm còn là hàm riêng, không bị gộp), chạy chương trình để sinh tệp `gmon.out`, rồi đọc báo cáo:

```text
$ g++ -std=c++17 -O1 -pg -fno-inline nong.cpp -o nong_pg
$ ./nong_pg                       # sinh gmon.out
$ gprof -b -p ./nong_pg gmon.out
Flat profile:
Each sample counts as 0.01 seconds.
  %   cumulative   self              self     total
 time   seconds   seconds    calls  ms/call  ms/call  name
100.00      0.46     0.46  2000000     0.00     0.00  laNguyenTo(int)
  0.00      0.46     0.00        1     0.00   460.00  demNguyenTo(int)
  0.00      0.46     0.00        1     0.00     0.00  tongChan(int)
```

Đọc: `laNguyenTo` chiếm **100%** thời gian (0,46 giây), được gọi 2 triệu lần. `tongChan` chiếm 0%: không đáng tối ưu dù bạn nghĩ nó "cũng là vòng lặp".

Cột `total ms/call` của `demNguyenTo` là 460 ms: nó gánh toàn bộ thời gian của `laNguyenTo`. Bảng ngay sau (`-q` cho đồ thị gọi hàm) xác nhận `demNguyenTo` là nơi duy nhất gọi `laNguyenTo`.

Giới hạn: `gprof` lấy mẫu thô 0,01 s nên hàm chạy ngắn bị bỏ sót; `-pg` đổi hành vi biên dịch (tắt inline mới thấy đủ hàm); không theo dõi tốt đa luồng; thời gian chờ I/O không hiện. Là công cụ đơn giản và có sẵn, đủ để trả lời "hàm nào nóng nhất".

### 6. `gcov`: đoạn nào của code chưa từng chạy

`gcov` không đo tốc độ: nó đếm **mỗi dòng đã chạy bao nhiêu lần**. Dùng để trả lời "bộ kiểm thử của tôi có chạm tới nhánh này chưa". Chương trình phân loại điểm, mà `main` chỉ thử hai điểm:

```cpp
#include <iostream>

const char* phanLoai(int diem) {
    if (diem < 0) {
        return "loi";
    }
    if (diem < 5) {
        return "yeu";
    }
    if (diem < 8) {
        return "kha";
    }
    return "gioi";
}

int main() {
    std::cout << phanLoai(6) << "\n";
    std::cout << phanLoai(9) << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 3–14 | `phanLoai` chia điểm thành bốn loại bằng chuỗi `if` |
| 17–18 | `main` thử điểm `6` (ra `kha`) và `9` (ra `gioi`) |

Biên dịch kèm `--coverage` (viết tắt của `-fprofile-arcs -ftest-coverage`), chạy chương trình (nó sinh tệp `.gcda`), rồi gọi `gcov`:

```text
$ g++ -std=c++17 -O0 --coverage phan_loai.cpp -o pl
$ ./pl
kha
gioi
$ gcov pl-phan_loai.gcda
File 'phan_loai.cpp'
Lines executed:83.33% of 12
Creating 'phan_loai.cpp.gcov'
```

Tệp `phan_loai.cpp.gcov` liệt kê số lần chạy trước mỗi dòng (`-` là dòng không có mã, `#####` là **chưa từng chạy**):

```text
        2:    4:    if (diem < 0) {
    #####:    5:        return "loi";
        2:    7:    if (diem < 5) {
    #####:    8:        return "yeu";
        2:   10:    if (diem < 8) {
        1:   11:        return "kha";
        1:   13:    return "gioi";
```

Hai dòng `return "loi"` và `return "yeu"` mang `#####`: không điểm nào trong phép thử rơi vào hai nhánh đó, đúng với 10 trên 12 dòng chạy (83,33%). Bổ sung thử `-3` và `2` là xong. Dùng `-O0` khi đo độ phủ, vì tối ưu gộp dòng làm số đếm khó hiểu. Lưu ý: độ phủ cao chỉ nói code **đã chạy**, không nói code **đúng**.

### 7. `perf`: lấy mẫu toàn hệ thống, và vì sao máy mình chặn

**`perf`** dùng bộ đếm phần cứng của CPU. `perf stat ./prog` đếm tổng (chu kỳ CPU, lệnh, lỗi bộ nhớ đệm...). `perf record ./prog` rồi `perf report` cứ vài trăm micro-giây lấy mẫu "đang chạy hàm nào" và vẽ bảng chi tiết hơn `gprof` mà không cần `-pg`. Nên biên dịch `-g -O2 -fno-omit-frame-pointer` ([Bài 38](38-bien-dich-lien-ket-build.md)) rồi `perf record -g` để có cả chuỗi gọi hàm.

Nhưng quyền dùng `perf` do nhân quyết, qua `/proc/sys/kernel/perf_event_paranoid`. Máy mình:

```text
$ cat /proc/sys/kernel/perf_event_paranoid
4
$ perf record -o perf.data ./nong
Error:
Failure to open event 'cpu_atom/cycles/Pu' on PMU 'cpu_atom' which will be removed.
Access to performance monitoring and observability operations is limited.
Consider adjusting /proc/sys/kernel/perf_event_paranoid setting ...
perf_event_paranoid setting is 4:
```

Thoát với mã 255, không có dữ liệu. Giá trị `4` chặn người dùng thường dùng bộ đếm phần cứng; hạ xuống (hay cấp `CAP_PERFMON`) cần quyền quản trị, là việc đụng cài đặt hệ thống nên mình **không làm**. `perf stat ./nong` vẫn chạy được nhưng chỉ in `0.3657 seconds time elapsed`, `0.3537 seconds user`, cùng các dòng `<not supported>` cho bộ đếm chu kỳ. Vậy `perf record`/`report` **mình chưa chạy được**, phần trên là cách dùng chứ không phải đầu ra. Trên máy bạn nếu `perf_event_paranoid` thấp hơn thì dùng được.

**Flame graph** (biểu đồ ngọn lửa) chỉ nhắc: một cách vẽ dữ liệu `perf record -g` thành các thanh chồng nhau, thanh càng rộng là hàm (cộng các hàm nó gọi) càng tốn nhiều thời gian. Có công cụ chuyển `perf script` thành ảnh; mình không cài nên chưa chạy.

### 8. Vòng lặp: đo → giả thuyết → sửa → đo lại

Bốn bước, không bỏ bước nào:

1. **Đo** để biết chậm thật, ở đâu (bản `-O2`, chạy nhiều lần, ghim lõi nếu cần).
2. **Giả thuyết**: vì sao đoạn nóng đó chậm.
3. **Sửa một thứ**.
4. **Đo lại** bằng đúng cách đo cũ, và **kiểm kết quả vẫn đúng**.

Ví dụ trên: `gprof` đã cho biết `laNguyenTo` là 100%. Giả thuyết: nó thử chia cho cả `d` chẵn, mà số chẵn lớn hơn 2 đã loại ngay bằng `n % 2`, nên chỉ cần thử `d` lẻ. Phần ví dụ ngay dưới thực hiện và đo lại.

!!! info "Bạn biết Go?"
    Go có sẵn bộ này trong `go` và rất đồng nhất. `go test -bench=. -benchmem` chạy benchmark (số ns/op, bộ nhớ cấp phát mỗi lần); `go test -cpuprofile cpu.out` rồi `go tool pprof -top cpu.out` ứng với `perf`/`gprof` (hiện hàm tốn nhiều CPU nhất); `go test -cover` ứng với `gcov` (in `coverage: 50.0% of statements`; `go tool cover -html` vẽ ra); chương trình chạy lâu thì `net/http/pprof` cho xem lúc đang chạy. `go tool trace` cho dòng thời gian goroutine. Mình đã chạy `-bench`, `-cpuprofile`, `pprof -top` và `-cover` trên Go 1.22 của máy mình (hàm `laNguyenTo` bằng Go ra khoảng 2778 ns/op, 0 allocs, pprof chỉ đúng hàm đó chiếm 97%); `go tool trace` mình chưa chạy. `strace` dùng được với chương trình Go như mọi chương trình khác.

## 💻 Ví dụ code

### Ví dụ: tối ưu `laNguyenTo` và đo lại

Từ chẩn đoán ở mục 5, đây là bản đã sửa, có tự bấm giờ (số nguyên tố dưới 1 triệu):

```cpp
#include <chrono>
#include <iostream>

bool laNguyenTo(int n) {
    if (n < 2) {
        return false;
    }
    if (n % 2 == 0) {
        return n == 2;
    }
    for (int d = 3; d * d <= n; d += 2) {
        if (n % d == 0) {
            return false;
        }
    }
    return true;
}

int demNguyenTo(int gioiHan) {
    int dem = 0;
    for (int n = 0; n < gioiHan; ++n) {
        if (laNguyenTo(n)) {
            ++dem;
        }
    }
    return dem;
}

int main() {
    auto batDau = std::chrono::steady_clock::now();
    int dem = demNguyenTo(1'000'000);
    auto ketThuc = std::chrono::steady_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(ketThuc - batDau).count();
    std::cout << "so nguyen to: " << dem << ", mat " << ms << " ms" << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 8–10 | Số chẵn: chỉ `2` là nguyên tố, còn lại loại ngay, khỏi vào vòng lặp |
| 11 | Vòng lặp thử chia chỉ qua `d` lẻ: `3, 5, 7, ...` (bước `d += 2`) |
| 30–32 | Bấm giờ quanh `demNguyenTo(1'000'000)` (mốc đầu, gọi hàm, mốc cuối) |
| 34 | In số lượng nguyên tố và thời gian |

Mình biên dịch cả bản cũ (vòng lặp `d` từ 2, bước 1) và bản mới bằng `-O2`, ghim lõi nhanh bằng `taskset -c 0`, chạy tám lần mỗi bản:

```text
bản cũ : 168  98  98  95  95  95  96  99   ms     (lần đầu lạnh)
bản mới:  51  50  49  48  49  50  50  48   ms
```

Cả hai in `so nguyen to: 78498`, **cùng đáp án** (bước 4: kiểm kết quả vẫn đúng). Thời gian giảm từ khoảng 95 xuống khoảng 49 ms, gần một nửa: khớp giả thuyết (bỏ một nửa số lần thử chia). Nếu mình không ghim lõi, các số lẫn lộn giữa 85 và 147 ms cho **cùng một** bản và khó thấy khác biệt; đó là lý do đo phải kiểm soát nhiễu.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`strace` dùng để làm gì, ví dụ cụ thể?"
    Theo dõi lời gọi hệ thống của chương trình (`openat`, `read`, `write`, `futex`...) kèm kết quả. Ví dụ: chương trình báo "không mở được tệp", `strace` cho thấy `openat(..., "cau_hinh.txt", ...) = -1 ENOENT`, tức đường dẫn sai; hoặc chương trình treo thì dòng cuối là `read(0, ` chưa trả về, chương trình đang chờ đầu vào. Dùng `-e trace=` để lọc, `-c` để đếm, `-f` cho luồng con, `-o` để ghi tệp.

??? question "`real`, `user`, `sys` của `time` khác nhau thế nào?"
    `real` là thời gian trôi qua trên đồng hồ treo tường. `user` là thời gian CPU chạy mã của bạn, `sys` là thời gian CPU chạy mã nhân thay mặt bạn (I/O, cấp phát bộ nhớ). Chương trình chờ I/O có `real` lớn hơn `user + sys`; chương trình đa luồng có `user + sys` lớn hơn `real`. `sys` lớn gợi ý lời gọi hệ thống nhiều hay chạm bộ nhớ nhiều.

??? question "Vì sao đo hiệu năng phải dùng bản `-O2`, chạy nhiều lần, và nên cẩn thận với vòng lặp rỗng?"
    `-O0` chậm hơn nhiều lần và phân bố thời gian khác bản thật, nên chỉ ra sai chỗ nghẽn. Chạy nhiều lần vì lần đầu bộ nhớ đệm lạnh và máy có nhiễu (việc khác, lõi nhanh/chậm). Trình biên dịch tối ưu xóa mã không ảnh hưởng kết quả quan sát được, nên đoạn đo mà kết quả không được dùng có thể biến mất, cho số `0 ms`. Cách chữa: dùng kết quả, `volatile`, hoặc đo trên bài toán thật.

??? question "`gprof`, `gcov`, `perf` khác nhau thế nào?"
    `gprof` (biên dịch `-pg`) cho biết thời gian và số lần gọi theo hàm, bằng lấy mẫu thô. `gcov` (biên dịch `--coverage`) đếm số lần chạy từng dòng để biết đoạn nào chưa được kiểm thử, không đo tốc độ. `perf` dùng bộ đếm phần cứng, không cần biên dịch lại đặc biệt (nên có `-g -fno-omit-frame-pointer`), lấy mẫu mịn hơn và xem được cả nhân; bị `perf_event_paranoid` giới hạn quyền trên nhiều máy.

??? question "Quy trình tối ưu một chương trình chậm của bạn là gì?"
    Đo trước: tìm đoạn nóng bằng profiler thay vì đoán. Đặt giả thuyết về lý do. Sửa một thứ một lần. Đo lại bằng đúng cách cũ và kiểm kết quả vẫn đúng. Lặp lại tới khi đạt mục tiêu. Không tối ưu những chỗ profiler không chỉ ra, vì thường đó là phần nhỏ so với thời gian tổng.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Đo trên bản `-O0` hay đo đúng một lần"
    Ra kết luận sai về chỗ nghẽn, hay kết luận từ lần chạy đầu (bộ nhớ lạnh). Dùng `-O2`, chạy nhiều lần, báo nhỏ nhất hoặc trung vị.

!!! warning "Lỗi 2: Tin số đo `0 ms` hay nhanh vô lý"
    Thường là trình biên dịch đã xóa đoạn đo vì kết quả không được dùng. Xem hợp ngữ (`objdump -d`), dùng kết quả, hoặc `volatile`.

!!! warning "Lỗi 3: Tối ưu theo cảm giác"
    `tongChan` trông như vòng lặp nặng nhưng `gprof` cho 0%. Luôn đo trước.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="42" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Chương trình in "khong mo duoc tep". `strace -e trace=openat` cho dòng `openat(AT_FDCWD, "cau_hinh.txt", O_RDONLY) = -1 ENOENT (No such file or directory)`. Kết luận nào bảo vệ được?

- Chương trình không có quyền đọc tệp `cau_hinh.txt`
- Tệp tồn tại nhưng bị hỏng nội dung
- Không có tệp `cau_hinh.txt` ở đường dẫn đó
- Thư viện chuẩn lỗi khi mở tệp

<p class="giai-thich" markdown>`ENOENT` nghĩa là "không có tệp hay thư mục này" tại đường dẫn đã cho, và đường dẫn ở đây là tương đối so với thư mục đang chạy, nên có thể chỉ cần chạy sai thư mục. Thiếu quyền sẽ là `EACCES`. Tệp hỏng nội dung thì `openat` vẫn thành công (trả số mô tả tệp như `3`) rồi lỗi mới xuất hiện ở bước đọc. Lời gọi hệ thống trả lỗi cụ thể như vậy không phải do thư viện chuẩn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Chương trình treo; chạy dưới `strace` thấy dòng cuối `read(0, ` mà không có `=` và kết quả. Chuyện gì đang xảy ra?

- Chương trình đang chờ dữ liệu từ đầu vào chuẩn
- Chương trình đang tính toán nặng trên CPU
- Chương trình đã thoát nhưng strace chưa in hết
- Chương trình đang ghi ra màn hình

<p class="giai-thich" markdown>`0` là đầu vào chuẩn và lời gọi `read` chưa trả về: tiến trình đã nhờ nhân đọc và đang ngủ chờ dữ liệu (khớp với `State: S` và `wchan` `anon_pipe_read` ở `/proc`). Nếu tính toán nặng trên CPU thì sẽ không có lời gọi hệ thống nào dở dang. Thoát chương trình luôn có dòng `+++ exited`. Ghi ra màn hình là `write` (số `1`), không phải `read(0`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Bạn đo một đoạn code bằng `chrono` trên bản `-O2` và được `mat 0 ms`; dịch ngược `main` thấy hai lời gọi `steady_clock::now()` đứng sát nhau. Cách hiểu nào đúng?

- Máy đủ nhanh để làm xong trong dưới một mili-giây
- `chrono` hỏng khi dùng với `-O2`
- Hàm `now()` trả về luôn 0 ở bản tối ưu
- Vòng lặp bị xóa vì kết quả của nó không được dùng

<p class="giai-thich" markdown>Hai lời gọi `now()` liền nhau, không có gì ở giữa, nghĩa là không còn mã nào để đo: trình biên dịch coi vòng lặp là thừa (kết quả không ảnh hưởng gì quan sát được) và bỏ nó. Với `-O0` cùng vòng lặp mất hơn nửa giây, nên không phải máy nhanh. `chrono` hoạt động bình thường ở `-O2`, và `now()` trả về thời điểm hiện tại, không phải 0.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc kết quả `time ./prog`: `real 0.163`, `user 0.053`, `sys 0.110`. Điều nào đúng?

- Chương trình đa luồng, vì `real` lớn hơn `user`
- Phần lớn CPU dùng trong nhân, không phải trong mã của bạn
- Chương trình chờ I/O, vì `real` lớn hơn `user`
- Máy quá tải, nên số đo vô nghĩa

<p class="giai-thich" markdown>`sys` (0,110) lớn hơn `user` (0,053): phần lớn thời gian CPU nằm trong nhân thay mặt chương trình, ví dụ cấp phát và chạm vào hàng trăm MB bộ nhớ. `real` ≈ `user + sys` (0,163), nên chương trình không chờ I/O; chờ I/O thì `real` vượt hẳn tổng đó. Đa luồng cho `user + sys` lớn hơn `real`, ngược với số đo này. Số đo hoàn toàn có nghĩa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Đầu ra `gcov` có các dòng `#####:    5:        return "loi";` và `#####:    8:        return "yeu";`, còn mọi dòng khác có số lần chạy khác 0. Điều đó nghĩa là gì?

- Hai dòng đó chưa từng chạy
- Hai dòng đó có lỗi biên dịch
- Hai dòng đó chạy rất nhiều lần
- Hai dòng đó bị trình biên dịch tối ưu hóa mất

<p class="giai-thich" markdown>`#####` là dấu `gcov` dành cho dòng có mã nhưng **chưa từng chạy**; ở đây không điểm thử nào là âm hay nhỏ hơn 5, nên cần bổ sung phép thử. Lỗi biên dịch thì không có tệp chạy để đo. Chạy nhiều lần sẽ là một số dương lớn. Với `-O0` (cách nên dùng khi đo độ phủ) mã không bị tối ưu hóa mất.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Báo cáo phẳng của `gprof`: `laNguyenTo` `100.00` `0.46 s` `2000000 calls`, `demNguyenTo` `0.00`, `tongChan` `0.00`. Bạn nên tối ưu gì trước?

- `tongChan`, vì vòng lặp của nó trông đơn giản nhất
- `demNguyenTo`, vì nó gọi hai triệu lần
- `laNguyenTo`, vì đó là nơi tiêu thụ thời gian
- Cả ba như nhau, vì cùng là vòng lặp

<p class="giai-thich" markdown>`self seconds` cho thấy toàn bộ thời gian nằm ở `laNguyenTo`; tối ưu chỗ khác không làm chương trình nhanh hơn đáng kể (tối đa vài phần trăm). `demNguyenTo` chỉ là nơi gọi: thời gian của nó là thời gian của con (cột `total`), phần `self` bằng 0. Cảm giác "vòng lặp nào trông nặng" chính là điều đo đạc sinh ra để thay thế.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Cùng một chương trình `-O2`, tám lần chạy cho 168, 98, 98, 95, 95, 95, 96, 99 ms khi ghim vào một lõi nhanh. Cách báo cáo nào hợp lý nhất?

- Lấy lần đầu (168 ms) vì đó là lần "thật" duy nhất
- Cộng cả tám lần rồi báo tổng
- Lấy lần nhanh nhất (95) và bỏ qua mọi nhiễu
- Bỏ lần đầu (cache lạnh) và báo khoảng 95 đến 99 ms từ bảy lần còn lại, nói rõ đã ghim lõi

<p class="giai-thich" markdown>Lần đầu chậm hơn vì bộ nhớ và bộ nhớ đệm chưa được nạp (cache lạnh), bảy lần sau ổn định quanh 95–99 ms. Báo khoảng giá trị từ các lần ổn định và điều kiện đo (ghim lõi) là trung thực và lặp lại được. Lần đầu không đại diện cho trạng thái thường gặp; tổng thời gian tám lần không phải thời gian của một lần; chỉ chọn giá trị nhỏ nhất che đi mức dao động thật.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Bạn chạy `perf record ./prog` và nhận lỗi `perf_event_paranoid setting is 4`. Máy không cho bạn quyền quản trị. Cách đi hợp lý?

- Chạy lại nhiều lần liên tiếp cho tới khi `perf` được phép dùng
- Dùng công cụ không cần quyền đó như `gprof`, `time`, `chrono`
- Chạy `perf` kèm `-O0` thì nhân sẽ cho phép ngay
- Đổi tên tệp chương trình rồi chạy lại `perf` để nó nhận ra

<p class="giai-thich" markdown>`perf_event_paranoid=4` là cài đặt của nhân chặn người dùng thường dùng bộ đếm phần cứng, không đổi theo số lần chạy, cờ tối ưu hay tên tệp. Thay vì đụng cài đặt hệ thống, chuyển sang công cụ không đòi quyền đó: `gprof`, `gcov`, `time`, `chrono`, `strace` đều dùng được ở đây. Nếu cần `perf` thật thì nhờ quản trị viên hạ giá trị hoặc cấp `CAP_PERFMON`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `strace ./prog` in mọi lời gọi hệ thống kèm kết quả: mở tệp không có thì `openat(...) = -1 ENOENT`, chương trình treo thì dòng cuối là lời gọi chưa trả về (`read(0, `, hay `futex(... FUTEX_WAIT_PRIVATE ...)` cho mutex); cờ `-e trace=`, `-c`, `-T`, `-o`, `-f`; `strace -p` bị `ptrace_scope` chặn như `gdb -p`; `ltrace` chỉ nhắc.
2. `/proc/PID` cho `status` (`State`, `VmRSS`, `Threads`), `fd` (tệp đang mở: số 0, 1, 2 là vào, ra, lỗi), `maps` (vùng nhớ), `wchan` (đang ngủ chờ gì); `lsof -p` và `ss` nhắc tên.
3. Đo thời gian: `time` cho `real`/`user`/`sys`, `std::chrono::steady_clock` đo một đoạn; luôn dùng `-O2` (mình thấy ~8 lần nhanh hơn `-O0`), chạy nhiều lần bỏ lần đầu (cache lạnh), ghim lõi (`taskset`) khi máy có lõi khác loại.
4. Bẫy đo: vòng lặp có kết quả không được dùng bị xóa ở `-O2` nên đo ra `0 ms` (hai lời gọi `now()` sát nhau trong `objdump -d`), ngay cả khi in kết quả thì vòng lặp có công thức vẫn được tính sẵn; `volatile` buộc vòng lặp chạy thật; nhiễu 103–189 ms giữa các lần chạy cùng một bản.
5. `gprof` (`-pg`) cho thời gian theo hàm (`laNguyenTo` 100%), `gcov` (`--coverage`) cho dòng chưa từng chạy (`#####`), `perf` (`stat`/`record`/`report`, flame graph) bị `perf_event_paranoid=4` chặn trên máy mình nên chưa chạy; làm theo vòng đo → giả thuyết → sửa → đo lại và kiểm kết quả vẫn đúng (95 ms xuống 49 ms, cùng đáp án 78498); Go có `go test -bench`, `pprof`, `-cover`.
