# Bài 40 — gdb nâng cao: sập chương trình, core dump, đa luồng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Đọc được một vụ sập `SIGSEGV` trong gdb (`p=0x0`, `bt`, `frame 1`), tạo và mở lại **core dump** (ảnh chụp lúc sập) bằng `gcore` và `gdb prog core`, và biết `catch throw` bắt ngoại lệ ở đâu.
    - Phân biệt **nạn nhân** với **thủ phạm** trong lỗi "chết chỗ này, lỗi chỗ kia": tràn mảng làm hỏng bộ nhớ kề bên, rồi dùng `watch -l` bắt đúng lệnh ghi đè.
    - Đọc deadlock hai mutex bằng `info threads`, `thread apply all bt`, `frame N`, `print mutex` (trường `__owner`), biết `gdb -p` có thể bị chặn bởi `ptrace_scope`, và sửa bằng `std::scoped_lock`.

**Bạn cần biết trước:** [Bài 39](39-gdb-co-ban.md) (`break`, `next`, `bt`, `print`, `watch`), [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (`nullptr`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UB, sanitizer), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) và [Bài 26](../nhom-3-da-luong/26-deadlock.md) (mutex, deadlock).

## 🧠 Câu chuyện mở đầu

Một chiếc xe đâm vào cột điện. Điều tra viên đến **hiện trường** để tìm nguyên nhân. Có ba việc họ làm: nhìn **chiếc xe nằm đâu** (chỗ chương trình sập), chụp **ảnh hiện trường** để mang về phân tích (core dump), và hỏi "**ai làm xe mất lái** từ trước đó?" (thủ phạm).

Điểm tinh tế: chiếc xe đâm vào cột chưa chắc là lỗi của cái cột hay của đoạn đường đó. Có thể nó bị cắt dây phanh từ cách đây mười cây số. **Chỗ sập** (nạn nhân) và **chỗ gây lỗi** (thủ phạm) thường là hai chỗ khác nhau. Nửa sau của bài này là học cách lần ngược từ nạn nhân về thủ phạm.

gdb là bộ đồ nghề của điều tra viên: đứng tại hiện trường, đọc ảnh chụp, lần theo các dấu vết.

!!! info "Chỗ nào ví dụ hiện trường không còn đúng?"
    Hiện trường thật chỉ có một. Với chương trình, bạn **dựng lại hiện trường bao nhiêu lần tùy ý** bằng cách chạy lại trong gdb, đặt chuông (`watch`) trước rồi cho "tai nạn" xảy ra lần nữa. Nhưng core dump là ảnh tĩnh: chụp xong chỉ **xem** được, không chạy tiếp được.

## 📖 Giải thích

### 1. Chương trình sập: `SIGSEGV` trong gdb

**Tín hiệu (signal)** là tin nhắn ngắn mà hệ điều hành gửi một tiến trình. `SIGSEGV` (segmentation fault, lỗi phân đoạn) được gửi khi chương trình đụng vào vùng nhớ không được phép, ví dụ địa chỉ 0. Mặc định nó giết chương trình, và shell báo mã thoát `139` (128 + 11, như [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)).

Chương trình sập của bài: danh sách liên kết ba nút, hàm `tongDanh` cộng dồn nhưng **quên kiểm tra `nullptr`** ở cuối danh sách.

```cpp
// bo-qua-kiem-tra
#include <iostream>

struct Nut {
    int giaTri;
    Nut* tiep;
};

Nut* taoDanh(int n) {
    Nut* dau = nullptr;
    for (int i = n; i >= 1; --i) {
        dau = new Nut{i * 10, dau};
    }
    return dau;
}

int tongDanh(const Nut* p) {
    int tong = 0;
    while (true) {
        tong += p->giaTri;
        p = p->tiep;
    }
    return tong;
}

int main() {
    Nut* ds = taoDanh(3);
    std::cout << "tong = " << tongDanh(ds) << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 9–15 | `taoDanh(3)` dựng danh sách `10 -> 20 -> 30 -> nullptr` (chèn từ cuối về đầu) |
| 18–21 | `tongDanh` bắt đầu từ nút đầu: `tong` cộng `p->giaTri` (dòng 20), rồi `p` nhảy sang nút kế (dòng 21) |
| 19 | Vòng `while (true)` **không có chỗ nào kiểm `p == nullptr`**: sau nút `30`, `p` thành `nullptr` |
| 20 | Lượt thứ tư đọc `p->giaTri` với `p` rỗng: giải tham chiếu `nullptr`, UB ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)); ở đây hệ điều hành gửi `SIGSEGV` |
| 28 | Không bao giờ in, vì `tongDanh` không trả về |

Số dòng trong bảng (và trong gdb) tính **cả dòng chú thích `// bo-qua-kiem-tra`** ở đầu. Mình biên dịch `g++ -std=c++17 -g -O0 sap.cpp -o sap` rồi chạy trong gdb. Phiên thật (bỏ dòng thông báo thư viện, thêm `(gdb)` trước lệnh):

```text
(gdb) run

Program received signal SIGSEGV, Segmentation fault.
0x00005555555551f6 in tongDanh (p=0x0) at sap.cpp:20
19	        tong += p->giaTri;
(gdb) bt
#0  0x00005555555551f6 in tongDanh (p=0x0) at sap.cpp:20
#1  0x000055555555524d in main () at sap.cpp:28
(gdb) print p
$1 = (const Nut *) 0x0
(gdb) print *p
Cannot access memory at address 0x0
(gdb) frame 1
#1  0x000055555555524d in main () at sap.cpp:28
27	    std::cout << "tong = " << tongDanh(ds) << "\n";
(gdb) print ds
$2 = (Nut *) 0x55555556b2f0
(gdb) print *ds
$3 = {giaTri = 10, tiep = 0x55555556b2d0}
(gdb) print *ds->tiep->tiep
$4 = {giaTri = 30, tiep = 0x0}
(gdb) frame 0
(gdb) info locals
tong = 60
(gdb) x/i $pc
=> 0x5555555551f6 <_Z8tongDanhPK3Nut+23>:	mov    (%rax),%eax
(gdb) info registers rax
rax            0x0                 0
```

Cách đọc, từng manh mối một:

- Dòng đầu nói **tín hiệu** (`SIGSEGV`) và **chỗ chết**: hàm `tongDanh`, `p=0x0`, dòng 19. `p=0x0` là bản án: con trỏ rỗng.
- `print *p` báo không đọc được địa chỉ 0: gdb xác nhận, không nghi ngờ gì nữa.
- `frame 1` nhảy sang `main`. Chỉ ở đó mới thấy `ds`, con trỏ nút đầu; gõ `print p` ở khung 1 sẽ báo `No symbol "p"`. Ta đi theo `tiep` hai lần, tới nút `30` có `tiep = 0x0`: danh sách **kết thúc đúng lúc** hàm đọc quá.
- `tong = 60`: cả ba nút đã được cộng (10 + 20 + 30), sập xảy ra ở lượt **kế sau** nút cuối.
- `x/i $pc` in lệnh máy đang chạy: `mov (%rax),%eax` (đọc bộ nhớ ở địa chỉ trong `rax`), mà `rax` bằng 0. `$pc` là địa chỉ lệnh hiện tại.

Chữa: kiểm `while (p != nullptr)` thay `while (true)`. Chương trình này hơi đặc biệt: nạn nhân (dòng 20) và thủ phạm (thiếu kiểm tra ở dòng 19) nằm cạnh nhau, dễ đọc. Mục 4 là ca khó hơn.

### 2. Core dump: ảnh chụp hiện trường

**Core dump** là tệp chứa toàn bộ bộ nhớ và thanh ghi của tiến trình tại lúc nó chết. Có nó, bạn mở lại **sau** vụ sập, trên máy khác, mà không cần chạy lại chương trình. Điều này quý khi lỗi chỉ xảy ra ở máy khách hàng, không tái hiện được.

Hệ điều hành chỉ tạo core nếu hai điều kiện đúng:

| Điều kiện | Xem bằng | Máy mình (đọc thôi, không sửa) |
|---|---|---|
| Giới hạn kích thước core khác 0 | `ulimit -c` | `0` (tắt) |
| `core_pattern`: nơi và cách ghi core | `cat /proc/sys/kernel/core_pattern` | `\|/usr/share/apport/apport ...` (đẩy cho **apport**) |

Giá trị `0` nghĩa là không ghi core. Còn `core_pattern` bắt đầu bằng `|` nghĩa là hệ điều hành chuyển core cho một chương trình khác (ở đây apport của Ubuntu, nó cất core vào kho riêng chứ không để tệp `core` trong thư mục của bạn). Trên máy dùng `systemd`, chương trình đó thường là `coredumpctl`; máy mình không có, nên chỉ nhắc tên.

Bật core thật cần `ulimit -c unlimited` trong shell và có thể phải chỉnh `core_pattern`, đều là **cài đặt hệ thống** mà mình không đụng. Có cách khác an toàn hơn: lúc đang dừng trong gdb, lệnh **`gcore`** ghi một core ra tệp bạn chọn.

```text
(gdb) gcore sap.core
warning: Memory read failed for corefile section, 4096 bytes at 0xffffffffff600000.
Saved corefile sap.core
```

Cảnh báo là vùng nhớ đặc biệt của kernel (`vsyscall`) mà gdb không đọc được; vô hại. Tệp `sap.core` nặng khoảng 1,6 MB ở máy mình. Giờ **thoát gdb**, và mở lại sau đó (**post-mortem**, khám nghiệm sau khi chết) chỉ bằng chương trình và core:

```text
$ gdb ./sap sap.core
Core was generated by `…/sap'.
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x00005555555551f6 in tongDanh (p=0x0) at sap.cpp:20
19	        tong += p->giaTri;
(gdb) bt
#0  0x00005555555551f6 in tongDanh (p=0x0) at sap.cpp:20
#1  0x000055555555524d in main () at sap.cpp:28
(gdb) print p
$1 = (const Nut *) 0x0
(gdb) frame 1
(gdb) print *ds
$2 = {giaTri = 10, tiep = 0x55555556b2d0}
```

Mọi thứ nhìn được y hệt lúc sập. Nhưng `next`, `continue`, `run` đều báo `The program is not being run.`: ảnh chụp không chạy tiếp. Hai lưu ý: dùng **đúng tệp chương trình đã sinh ra core** (nếu biên dịch lại, địa chỉ lệch và bạn đọc ra rác), và biên dịch có `-g` thì mới thấy tên biến và số dòng.

### 3. Ngoại lệ không bắt: `catch throw`

Ném ngoại lệ mà **không ai bắt** thì chương trình gọi `std::terminate` rồi `abort`, gửi `SIGABRT` (mã thoát 134). Chương trình nhỏ để xem:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <stdexcept>
#include <string>

int docTuoi(const std::string& s) {
    if (s.empty()) {
        throw std::runtime_error("chuoi rong");
    }
    return std::stoi(s);
}

int main() {
    std::cout << docTuoi("17") << "\n";
    std::cout << docTuoi("") << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 7–9 | Chuỗi rỗng thì ném `std::runtime_error` |
| 14 | `docTuoi("17")` bình thường, trả `17` |
| 15 | `docTuoi("")` ném ngoại lệ; `main` không có `try`/`catch` nên không ai bắt |

Chạy thường, mình thấy hai dòng và mã thoát 134:

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  chuoi rong
```

Dòng `17` **không hiện**: `cout` ghi vào bộ đệm, và `abort` giết chương trình trước khi đổ bộ đệm ra (mình chạy qua ống nên đệm đầy hẳn; ở terminal có thể khác). Vì vậy khi gỡ lỗi nên dùng `cerr` hoặc `std::endl`.

`bt` trong gdb sau vụ `abort` có một chuỗi khung thư viện (`raise`, `abort`, `std::terminate`...), rồi tới `docTuoi (s="") at ngoai_le.cpp:8` và `main () at ngoai_le.cpp:15`: ngoại lệ chưa bị tháo ngăn xếp nên khung của bạn vẫn còn.

```text
(gdb) catch throw
Catchpoint 1 (throw)
(gdb) run

Catchpoint 1 (exception thrown), 0x00007ffff7cbb35a in __cxa_throw () from /lib/x86_64-linux-gnu/libstdc++.so.6
(gdb) bt 5
#0  0x00007ffff7cbb35a in __cxa_throw () from /lib/x86_64-linux-gnu/libstdc++.so.6
#1  0x00005555555564a7 in docTuoi (s="") at ngoai_le.cpp:8
#2  0x000055555555659d in main () at ngoai_le.cpp:15
```

Quy tắc: ngoại lệ bị **bắt** ở đâu đó vẫn nổ `catch throw` (nó dừng lúc ném, kể cả khi sau đó có `catch`), nên rất hợp để tìm "ngoại lệ này bị ném từ đâu". `catch catch` dừng lúc bắt; `catch throw` có thể kèm bộ lọc theo tên kiểu.

### 4. "Chết chỗ này, lỗi chỗ kia": tràn mảng làm hỏng bộ nhớ kề bên

Đây là loại lỗi tốn thời gian nhất của C++. Một vòng lặp ghi **tràn** ra ngoài mảng, đè lên bộ nhớ của thứ khác nằm sát bên. Chương trình **không sập ngay**. Nó đi tiếp, rồi chết muộn ở một chỗ chẳng liên quan, như `delete` một đối tượng khác.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

void datTatCa(int* mang, int n, int giaTri) {
    for (int i = 0; i < n; ++i) {
        mang[i] = giaTri;
    }
}

int main() {
    int* diem = new int[4];
    std::vector<int>* phu = new std::vector<int>(3, 7);
    std::cout << "bat dau" << std::endl;
    datTatCa(diem, 9, -1);
    std::cout << "da ghi xong" << std::endl;
    std::cout << "phu co " << phu->size() << " phan tu" << std::endl;
    delete phu;
    std::cout << "da xoa phu" << std::endl;
    delete[] diem;
    std::cout << "xong" << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 12 | `diem` là mảng **4** `int` trên heap (16 byte) |
| 13 | `phu` là một `std::vector<int>` (3 phần tử bằng 7) cũng trên heap, **cấp phát ngay sau** `diem` |
| 15 | Gọi `datTatCa(diem, 9, -1)`: ghi `-1` vào 9 ô, trong khi mảng chỉ có 4 |
| 6–8 | Vòng lặp ghi `mang[0]` đến `mang[8]`; từ `mang[4]` trở đi là ghi **ra ngoài** |
| 17 | In `phu->size()`: nếu `phu` còn nguyên thì phải là 3 |
| 18 | `delete phu`: giải phóng bộ nhớ của `phu` |

Bước 1, **chạy thường** (g++ không cảnh báo gì, `-Wall -Wextra`). Mình thấy:

```text
bat dau
da ghi xong
phu co 18446744073439103167 phan tu
Segmentation fault (core dumped)
```

Con số `phu co ...` là rác (số này đổi theo lần chạy), rồi chết ở `delete phu` (dòng 18). Đọc ngây thơ: "lỗi ở `phu` hay `delete`". Sai: hai chỗ đó chỉ là nạn nhân.

Bước 2, **thêm log**, cách ai cũng làm đầu tiên. Các dòng `std::cout << ... << std::endl` ở trên *chính là log*, và chúng nói dối giùm: `bat dau`, `da ghi xong` đều in bình thường, không dòng nào tố cáo `datTatCa`.

Log còn làm lỗi **dời chỗ**. Mình chỉ thêm `std::string nhatKy(40, '#');` (một chuỗi dài, nằm trên heap) giữa dòng 12 và 13, và lần chạy kế:

```text
bat dau
da ghi xong
phu co 3 phan tu
da xoa phu
xong
munmap_chunk(): invalid pointer
Aborted (core dumped)
```

Lần này `phu` còn nguyên (`3 phan tu`), mọi dòng log đều bình thường, chương trình in `xong`, rồi **chết sau cả `return 0`** bằng một lỗi khác hẳn. Nguyên nhân: chuỗi `nhatKy` giờ nằm xen vào giữa `diem` và `phu` nên đoạn tràn đè lên chuỗi, và nó chết khi `nhatKy` bị hủy. Log không chỉ thiếu chỉ dẫn mà còn **đổi bố cục bộ nhớ**, làm lỗi trông như đã biến mất hoặc nhảy chỗ.

Bước 3, **gdb `bt` ở chỗ chết**. Chạy lại bản gốc trong gdb:

```text
(gdb) run
Program received signal SIGSEGV, Segmentation fault.
0x00007ffff78ade55 in __GI___libc_free (mem=...) at ./malloc/malloc.c:3375
(gdb) bt
#0  0x00007ffff78ade55 in __GI___libc_free (mem=...) at ./malloc/malloc.c:3375
#1  0x… in std::__new_allocator<int>::deallocate (this=..., __p=..., __n=...)
#2  0x… in std::allocator_traits<std::allocator<int> >::deallocate (...)
#3  std::_Vector_base<int, std::allocator<int> >::_M_deallocate (...)
#4  0x… in std::_Vector_base<int, std::allocator<int> >::~_Vector_base (...)
#5  0x… in std::vector<int, std::allocator<int> >::~vector (...)
#6  0x… in main () at tran.cpp:18
(gdb) frame 6
(gdb) x/10dw diem
0x55555556b2b0:	-1	-1	-1	-1
0x55555556b2c0:	-1	-1	-1	-1
0x55555556b2d0:	-1	21845
```

`bt` chỉ cho thấy **nạn nhân**: `free` bị gọi từ `~vector` ở dòng 18 trên một con trỏ lạ (`mem=0x5555ffffffff` khi mình in đối số của `free`). Nhưng `x/10dw diem` ở khung 6 lộ manh mối: `diem` chỉ có 4 ô mà **10 ô liền nhau đều là `-1`**, và địa chỉ `0x…2d0` chính là địa chỉ của `*phu`. Tức là `-1` đã tràn vào đối tượng `phu`, đè con trỏ dữ liệu bên trong nó (`21845` là nửa cao `0x5555` của con trỏ, nửa thấp thành `0xffffffff`).

Bước 4, **`watch -l` bắt thủ phạm**. Dừng trước khi tràn xảy ra, rồi theo dõi **chỗ nhớ** (location) của con trỏ dữ liệu của `phu`:

```text
(gdb) break 15
(gdb) run
Breakpoint 1, main () at tran.cpp:15
15	    datTatCa(diem, 9, -1);
(gdb) watch -l phu->_M_impl._M_start
Hardware watchpoint 2: -location phu->_M_impl._M_start
(gdb) continue

Hardware watchpoint 2: -location phu->_M_impl._M_start

Old value = (int *) 0x55555556b2f0
New value = (int *) 0x5555ffffffff
datTatCa (mang=0x55555556b2b0, n=9, giaTri=-1) at tran.cpp:6
6	    for (int i = 0; i < n; ++i) {
(gdb) print i
$1 = 8
(gdb) bt
#0  datTatCa (mang=0x55555556b2b0, n=9, giaTri=-1) at tran.cpp:6
#1  0x00005555555553ac in main () at tran.cpp:15
```

`watch -l` (hay `watch -location`) theo dõi **địa chỉ** thay vì tên biểu thức, nên không bị hết hiệu lực khi đổi khung. gdb dừng đúng lúc `datTatCa` ghi lên `phu`: con trỏ của `phu` đổi từ giá trị hợp lệ sang `0x5555ffffffff`, ngay ở lượt `i = 8`, và `bt` chỉ thẳng hàm thủ phạm cùng đối số `n=9`. Mảng có 4 ô, mà `n=9`: đây là lỗi.

Bước 5: để máy chỉ ra **cả dòng ghi tràn lẫn dòng cấp phát** mà không cần đoán địa chỉ, dùng AddressSanitizer, [Bài 41](41-sanitizer-valgrind.md). Cùng chương trình này ở đó cho kết quả trong một lần chạy.

### 5. Đa luồng: deadlock hai mutex

Ở [Bài 26](../nhom-3-da-luong/26-deadlock.md) bạn đã thấy deadlock lần đầu. Ở đây ta nhìn nó như điều tra viên: bốn manh mối từ bốn công cụ trên cùng một chương trình.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex bepA;
std::mutex bepB;

void anLam() {
    std::cerr << "An: xin bepA\n";
    std::lock_guard<std::mutex> g1(bepA);
    std::cerr << "An: da khoa bepA\n";
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    std::cerr << "An: xin bepB\n";
    std::lock_guard<std::mutex> g2(bepB);
    std::cerr << "An: da khoa bepB, lam xong\n";
}

void binhLam() {
    std::cerr << "Binh: xin bepB\n";
    std::lock_guard<std::mutex> g1(bepB);
    std::cerr << "Binh: da khoa bepB\n";
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    std::cerr << "Binh: xin bepA\n";
    std::lock_guard<std::mutex> g2(bepA);
    std::cerr << "Binh: da khoa bepA, lam xong\n";
}

int main() {
    std::thread an(anLam);
    std::thread binh(binhLam);
    an.join();
    binh.join();
    std::cout << "ca hai xong\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 11–13 | An khóa `bepA` trước |
| 14 | `sleep_for` 100 ms: cho Bình kịp khóa `bepB`, để deadlock xảy ra **chắc chắn** (bỏ dòng này thì lúc treo lúc không) |
| 16 | An xin `bepB`: lúc này Bình đang giữ nó |
| 22, 26 | Bình làm đối xứng: khóa `bepB` trước (dòng 22), rồi xin `bepA` mà An đang giữ (dòng 26) |
| 33–34 | `main` đợi cả hai (`join`) và không bao giờ qua được |

**Manh mối 1: chạy thường.** Chương trình treo và không in gì thêm. Mình chạy `timeout 3 ./treo2` (`timeout` giết sau 3 giây, mã thoát 124) và nhận:

```text
An: xin bepA
An: da khoa bepA
Binh: xin bepB
Binh: da khoa bepB
An: xin bepB
Binh: xin bepA
```

Đây là log **tốt**: dòng cuối của mỗi luồng là "xin" chứ không phải "đã khóa", và hai luồng xin hai khóa chéo nhau. Nhưng chỉ khi bạn ghi bằng `cerr` (không đệm). Mình đổi cả sáu `cerr` thành `cout` rồi chạy `timeout 3 ./treo3 | cat`: **không in gì cả**, chỉ có chữ `Terminated`, vì log nằm trong bộ đệm và mất khi tiến trình bị giết.

**Manh mối 2: gdb.** Cách thông thường là gắn gdb vào tiến trình đang treo bằng `gdb -p <PID>`. Máy mình bị chặn:

```text
$ gdb -p <PID> -batch -ex "info threads"
Could not attach to process.  If your uid matches the uid of the target
process, check the setting of /proc/sys/kernel/yama/ptrace_scope, or try
again as the root user.  For more details, see /etc/sysctl.d/10-ptrace.conf
ptrace: Inappropriate ioctl for device.
```

`ptrace_scope` là cài đặt của hệ thống (Yama): bằng `1` thì một tiến trình chỉ được theo dõi **con cháu** của nó, mà `treo2` chạy riêng nên bị từ chối. Hạ xuống `0` cần quyền quản trị, là việc đụng cài đặt hệ thống, nên mình **không làm**. Cách đi vòng: chạy chương trình **ngay trong gdb**, để nó treo, rồi gửi `SIGINT` (như bấm `Ctrl+C`). Trong chế độ batch, một tiến trình khác gửi `SIGINT` sau 2 giây (`pkill -INT -x treo2`). Kịch bản (`info threads` cũng liệt kê ba luồng, mình bỏ khỏi bản dán):

```text
set print frame-arguments none
run
info threads
thread apply all bt 8
thread 2
frame 7
print bepB._M_mutex.__data.__owner
thread 3
frame 7
print bepA._M_mutex.__data.__owner
```

Đầu ra thật (mình bỏ các khung `#0` đến `#5` nằm trong thư viện, và rút gọn dòng; `LWP` là số hiệu luồng do hệ điều hành cấp, đổi mỗi lần chạy):

```text
Thread 1 "treo2" received signal SIGINT, Interrupt.
(gdb) thread apply all bt 8

Thread 3 (Thread 0x7ffff6ffe6c0 (LWP 580047) "treo2"):
#6  … in std::lock_guard<std::mutex>::lock_guard (this=..., __m=...)
#7  … in binhLam () at treo2.cpp:26

Thread 2 (Thread 0x7ffff77ff6c0 (LWP 580046) "treo2"):
#6  … in std::lock_guard<std::mutex>::lock_guard (this=..., __m=...)
#7  … in anLam () at treo2.cpp:16
(gdb) thread 2
[Switching to thread 2 (Thread 0x7ffff77ff6c0 (LWP 580046))]
(gdb) frame 7
#7  … in anLam () at treo2.cpp:16
16	    std::lock_guard<std::mutex> g2(bepB);
(gdb) print bepB._M_mutex.__data.__owner
$1 = 580047
(gdb) thread 3
(gdb) frame 7
#7  … in binhLam () at treo2.cpp:26
26	    std::lock_guard<std::mutex> g2(bepA);
(gdb) print bepA._M_mutex.__data.__owner
$2 = 580046
```

Đọc thành lời: luồng 2 (`anLam`, `LWP 580046`) đứng ở dòng 16, xin `bepB`, mà `bepB` do `580047` (luồng 3) giữ. Luồng 3 (`binhLam`) đứng ở dòng 26, xin `bepA`, mà `bepA` do `580046` (luồng 2) giữ. **Một vòng tròn khép kín**: đúng deadlock. Luồng 1 là `main`, đang ở `join`. `__owner` là tên trường nội bộ của glibc, đổi theo phiên bản.

**Manh mối 3: `strace`.** Chạy dưới `strace -f` (theo dõi cả luồng con, chi tiết ở [Bài 42](42-strace-perf-do-hieu-nang.md)), mình lọc lời gọi `futex` (cơ chế ngủ-chờ của hệ điều hành). Ba luồng đứng yên suốt, rồi mới bị `timeout` giết:

```text
542907 futex(0x…, FUTEX_WAIT_BITSET|FUTEX_CLOCK_REALTIME, 542908, NULL, FUTEX_BITSET_MATCH_ANY <unfinished ...>
542908 futex(0x…, FUTEX_WAIT_PRIVATE, 2, NULL <unfinished ...>
542909 futex(0x…, FUTEX_WAIT_PRIVATE, 2, NULL <unfinished ...>
542909 --- SIGCONT ... ---
542909 +++ killed by SIGTERM +++
```

Hai luồng ngủ ở `FUTEX_WAIT_PRIVATE` (cách mutex ngủ chờ) và **không bao giờ "resumed" trước khi bị giết**; luồng chính ngủ ở `FUTEX_WAIT_BITSET`, chờ `join`. Giống `gdb -p`, `strace -p` vào tiến trình khởi chạy riêng cũng bị chặn (`ptrace(PTRACE_SEIZE, ...): Operation not permitted`), nên mình chạy từ đầu dưới `strace`.

**Manh mối 4: ThreadSanitizer.** Chạy `treo2` trực tiếp dưới TSan thì TSan **không** báo gì và chương trình vẫn treo (mình thử: `timeout` giết, mã 124), vì hai luồng chưa bao giờ xin xong khóa thứ hai. Đổi `main` để chạy tuần tự (`an.join()` trước khi tạo `binh`) thì không treo, và TSan báo `lock-order-inversion (potential deadlock)`. Báo cáo đó ở [Bài 41](41-sanitizer-valgrind.md).

**Chữa.** Khóa **cả hai mutex một lần** bằng `std::scoped_lock` ([Bài 26](../nhom-3-da-luong/26-deadlock.md)); chương trình đầy đủ nằm ở phần ví dụ ngay dưới.

### 6. Các công cụ còn lại

**Bản `-O2` đánh lừa gdb.** Mình có một hàm nhỏ `tinh(int n)` tính `nhan = n * 3; ket = nhan + 1; return ket;` (đánh dấu `__attribute__((noinline))`, lời nhờ riêng của g++ để hàm **không** bị nhét vào `main`, mục 4 của [Bài 38](38-bien-dich-lien-ket-build.md)). Biên dịch `-g -O0` và `-g -O2`, đặt `break tinh`, rồi `info locals` ở dòng đầu hàm (rút gọn):

```text
-O0:  nhan = 73728     ket = 0            <- chưa gán nên là rác, nhưng đọc được
-O2:  nhan = <optimized out>    ket = <optimized out>
```

Ở `-O2`, tham số hiện là `n=n@entry=7` (giá trị lúc vào hàm, còn biết), nhưng `nhan` và `ket` đã bị gộp vào lệnh tính chung nên **không còn tồn tại như biến**, gdb báo `<optimized out>`. `next` cũng nhảy từ dòng 3 sang dòng 6. Không phải gdb hỏng ([Bài 38](38-bien-dich-lien-ket-build.md)).

Tệ hơn, tối ưu có thể **đổi hẳn hành vi** của chương trình UB. Hàm `tongDanh` ở mục 1 khi biên dịch `-O2` thì trình biên dịch thấy "mọi đường đi đều đọc `p->giaTri`, nên `p` không thể là `nullptr`, vòng lặp không bao giờ thoát", và sinh ra:

```text
00000000000011f0 <tongDanh(Nut const*)>:
    11f0:  endbr64
    11f4:  nopl   0x0(%rax)
    11f8:  jmp    11f8 <tongDanh(Nut const*)+0x8>
```

Lệnh cuối nhảy về **chính nó**: vòng lặp vô hạn rỗng. Mình chạy bản `-O2`: nó **treo mãi** thay vì `SIGSEGV` (phải dừng bằng tay). Cùng một UB, `-O0` sập còn `-O2` treo; chuẩn C++ cho phép ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)).

**`watch` phần cứng và phần mềm.** Khi gdb báo `Hardware watchpoint`, CPU tự canh vùng nhớ nên gần như không chậm. Nếu không dùng được (hay đặt `set can-use-hw-watchpoints 0`), gdb rơi về `Watchpoint` **phần mềm**: chạy từng lệnh máy và so sánh sau mỗi lệnh. Mình đo vòng lặp cộng 1 đến 100000 vào `tong` với `watch tong if tong < 0` (điều kiện không bao giờ đúng): phần cứng **10,7 giây**, phần mềm **51,6 giây** (một lần đo, đổi theo máy).

**`handle`: gdb và tín hiệu.** Mặc định gdb **dừng** mỗi khi chương trình nhận một tín hiệu. Mình thử một chương trình tự gửi cho mình `SIGUSR1` hai lần (đã có handler tăng biến `dem`, không có gì sai): gdb vẫn in `Program received signal SIGUSR1` và dừng hai lần, mỗi lần phải `continue`, rồi chương trình in `dem = 2`. Thêm `handle SIGUSR1 nostop noprint pass` (không dừng, không in, vẫn chuyển tín hiệu cho chương trình) thì chạy thẳng tới `dem = 2`. `info signals SIGSEGV` cho thấy `SIGSEGV` mặc định là dừng, in, chuyển tiếp; đừng `nostop` nó khi đang điều tra sập.

**Còn lại, chỉ nhắc.** *`.gdbinit`*: tệp `~/.gdbinit` chứa lệnh gdb chạy mỗi lần khởi động (như `set debuginfod enabled off`, mà chính gdb gợi ý khi hỏi). *`rr`* ghi lại cả lần chạy để **tua ngược** (`reverse-continue`, `reverse-step`): rất mạnh với lỗi hiếm, mình không cài nên chưa chạy.

!!! info "Bạn biết Go?"
    Go phần lớn không có "chết chỗ này, lỗi chỗ kia": ra ngoài biên thì runtime `panic` ngay tại dòng ghi. Mình chạy đoạn Go ghi vào `a[4]` của slice 4 phần tử (Go 1.22 trên máy mình): `panic: runtime error: index out of range [4] with length 4`, kèm stack có số dòng, mã thoát 2.

    Đối chiếu công cụ: `GOTRACEBACK=all` in stack của mọi goroutine khi panic; `GOTRACEBACK=crash` đổi cái chết thành `SIGABRT` để tạo core (mình thử: mã thoát 134); gửi `SIGQUIT` (`kill -QUIT <pid>`) cho chương trình Go đang treo thì runtime in stack mọi goroutine, thay cho `thread apply all bt`. Với trình gỡ lỗi, dùng Delve: `dlv attach <pid>`, `dlv core prog core`, lệnh `goroutines` thay `info threads`. Máy mình không cài `dlv` nên mình chưa chạy nó. Data race của Go thì dùng `go run -race` thay cho TSan.

## 💻 Ví dụ code

### Ví dụ: sửa deadlock bằng `std::scoped_lock`

Thứ tự bạn liệt kê các mutex cho `scoped_lock` không còn quan trọng: nó khóa cả hai bằng thuật toán tránh deadlock.

```cpp
#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

std::mutex bepA;
std::mutex bepB;
std::mutex inKhoa;

void ghi(const std::string& dong) {
    std::lock_guard<std::mutex> g(inKhoa);
    std::cout << dong << std::endl;
}

void anLam() {
    ghi("An: xin ca hai khoa");
    std::scoped_lock ca(bepA, bepB);
    ghi("An: da co ca hai, lam xong");
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
}

void binhLam() {
    ghi("Binh: xin ca hai khoa");
    std::scoped_lock ca(bepB, bepA);
    ghi("Binh: da co ca hai, lam xong");
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
}

int main() {
    std::thread an(anLam);
    std::thread binh(binhLam);
    an.join();
    binh.join();
    ghi("ca hai xong");
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 9, 11–14 | `ghi` in một dòng, có `inKhoa` riêng để hai luồng không in xen vào nhau |
| 18 | `std::scoped_lock(bepA, bepB)` khóa cả hai bằng thuật toán tránh deadlock; không có chuyện "giữ một, chờ một" |
| 26 | Bình liệt kê ngược (`bepB, bepA`) nhưng vẫn an toàn |
| 19, 27 | Chỉ in khi đã có **cả hai** khóa; sau đó ngủ 100 ms, nên luồng kia phải chờ chứ không treo |

Mình chạy ba lần liền, lần nào cũng thoát mã 0 với dòng cuối `ca hai xong` (thứ tự An/Bình đổi giữa các lần). Chạy dưới TSan: không có báo cáo nào, mã 0.

Với lỗi tràn mảng ở mục 4, cách chữa gốc là **không dùng mảng thô**: dùng `std::vector` (số phần tử luôn có sẵn qua `size()`) và `at()` để ngoài biên **ném** `std::out_of_range` ngay tại chỗ gây lỗi thay vì lặng lẽ đè bộ nhớ ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Phần 2 của [Bài 41](41-sanitizer-valgrind.md) cho thấy `-D_GLIBCXX_ASSERTIONS` bắt đúng chỗ đó.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Core dump là gì, và làm sao dùng nó?"
    Là tệp chứa bộ nhớ và thanh ghi của tiến trình lúc nó chết, do hệ điều hành ghi (cần `ulimit -c` khác 0 và `core_pattern` cho phép). Mở bằng `gdb ./chuongtrinh core` (post-mortem): xem `bt`, `frame`, `print` y như lúc sập, nhưng không chạy tiếp được. Phải dùng đúng tệp chương trình đã sinh ra core, biên dịch có `-g`. `gcore` trong gdb tạo core của một tiến trình đang sống.

??? question "Segfault ở một chỗ hợp lý mà code đúng, bạn tìm nguyên nhân thế nào?"
    Nghi **bộ nhớ bị hỏng từ trước**: chỗ sập là nạn nhân. Chạy dưới AddressSanitizer ([Bài 41](41-sanitizer-valgrind.md)) để nó chỉ thẳng dòng ghi tràn. Không có ASan thì `watch -l` trên vùng bị hỏng để gdb dừng đúng lệnh ghi đè và xem `bt`. Thêm log thường không giúp vì log đổi bố cục bộ nhớ.

??? question "Cách tìm deadlock trong chương trình đang treo?"
    Dừng chương trình (gdb `-p` nếu được phép, hoặc chạy dưới gdb rồi `Ctrl+C`), gõ `info threads` và `thread apply all bt`. Hai luồng đứng ở `mutex::lock` là dấu hiệu. Chọn từng luồng (`thread N`), nhảy tới khung của hàm mình (`frame N`) rồi `print` trường `__owner` của mutex mà nó chờ để biết ai giữ. Nếu chủ của khóa này lại đang chờ khóa kia: deadlock.

??? question "`gdb -p` không gắn được vào tiến trình đang chạy, vì sao?"
    Hệ Linux dùng Yama (`/proc/sys/kernel/yama/ptrace_scope`): bằng `1` thì chỉ theo dõi được **tiến trình con** của mình, bằng `0` thì theo dõi được tiến trình cùng người dùng, `2` và `3` còn chặt hơn. Gắn vào tiến trình khởi chạy riêng sẽ bị `Operation not permitted`. Cách đi: chạy chương trình dưới gdb từ đầu, hoặc dùng quyền quản trị, hoặc đổi cài đặt (việc của quản trị viên).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Sửa chỗ sập thay vì chỗ gây lỗi"
    Thấy `delete phu` sập thì thêm `if (phu)` hay bỏ `delete`: lỗi dời sang chỗ khác sau vài ngày. Sập bên trong `free`/`malloc`/`delete` gần như luôn là dấu hiệu **bộ nhớ đã hỏng từ trước**. Tìm thủ phạm bằng ASan hoặc `watch -l`.

!!! warning "Lỗi 2: Tin vào log in bằng `cout` khi chương trình treo hay sập"
    `cout` có bộ đệm; tiến trình bị giết hay `abort` thì dòng đang chờ mất. Dùng `cerr`, hoặc `std::endl`, khi gỡ lỗi.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="40" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** gdb in `Program received signal SIGSEGV` rồi `tongDanh (p=0x0) at sap.cpp:20`, dòng 20 là `tong += p->giaTri;`. Kết luận trực tiếp nhất?

- Mảng `p` bị đọc ngoài biên ở lượt cuối
- Hàm `tongDanh` bị gọi với đối số sai kiểu
- Hàm đọc thành viên qua con trỏ rỗng
- Bộ nhớ heap đã hết nên `new` thất bại ở nút cuối

<p class="giai-thich" markdown>`p=0x0` nghĩa là con trỏ đang bằng `nullptr`, và dòng 19 giải tham chiếu nó bằng `->`: đọc ở địa chỉ 0 gây `SIGSEGV`. `p` là con trỏ tới một nút, không phải mảng. Sai kiểu đối số bị trình biên dịch chặn từ lúc biên dịch. Heap hết chỗ không gây ra `SIGSEGV` ở dòng này (và `new` sẽ ném `std::bad_alloc` chứ không trả con trỏ rỗng).</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Chương trình sập ở `delete phu` với `bt` toàn khung của `free` và `~vector`. `x/10dw diem` (mảng 4 `int`) cho thấy 10 ô liền nhau đều là `-1`, mà ô thứ 9 trùng địa chỉ với `phu`. Chẩn đoán đúng nhất?

- `phu` bị `delete` hai lần, nên `free` thấy khối đã trả
- Hàm `free` của thư viện chuẩn có lỗi với `vector<int>` lớn
- `phu` chưa được khởi tạo
- Một vòng lặp ghi tràn ngoài `diem` đã đè lên `phu`

<p class="giai-thich" markdown>`diem` chỉ có 4 ô mà 10 ô liền nhau mang cùng giá trị ghi tràn, và ô thứ 9 trùng với địa chỉ của `*phu`: tràn mảng đã ghi đè dữ liệu bên trong `phu`. `delete` lần sau đó chết trên con trỏ hỏng, đây chỉ là nạn nhân. Lỗi `delete` hai lần có báo cáo kiểu khác (`double free`). `phu` đã được khởi tạo (`(3, 7)`) ở dòng cấp phát. Thư viện `free` được dùng ở khắp nơi, rất hiếm khi sai.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đầu ra gdb trên chương trình treo: luồng 2 ở `anLam ... :16` đang xin `bepB`, `print bepB._M_mutex.__data.__owner` ra `580047`; luồng 3 (`LWP 580047`) ở `binhLam ... :26` đang xin `bepA`, `print bepA...__owner` ra `580046`; luồng 2 có `LWP 580046`. Kết luận?

- Luồng 3 chờ luồng 1, vì `main` đang `join`
- Hai luồng chờ khóa của nhau: một vòng tròn, đúng deadlock
- Luồng 2 đang giữ cả hai mutex nên chưa nhả
- Không ai giữ khóa nào, chương trình chỉ đang ngủ

<p class="giai-thich" markdown>Người giữ `bepB` là `580047` (luồng 3), người giữ `bepA` là `580046` (luồng 2). Luồng 2 chờ khóa của luồng 3 và luồng 3 chờ khóa của luồng 2: vòng tròn, không bên nào tự nhả được. `join` của `main` chỉ chờ chúng kết thúc, nó không giữ khóa nào. `__owner` khác 0 nên có người giữ, không phải "không ai giữ".</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Chương trình ném ngoại lệ ở một hàm sâu, bị `catch` ở hàm bên ngoài nên không sập, nhưng bạn muốn biết **dòng nào** ném nó. Cách trực tiếp nhất?

- `catch throw` rồi `run`, gdb dừng ngay lúc `throw` được thực thi
- `watch` trên biến của khối `catch`
- Chờ chương trình `abort` rồi đọc `bt` ở khung cuối cùng của thư viện
- Biên dịch lại với `-DNDEBUG`

<p class="giai-thich" markdown>`catch throw` đặt catchpoint dừng đúng tại `__cxa_throw`, nên `bt` sau đó cho khung của hàm ném và dòng ném, kể cả khi ngoại lệ sẽ bị bắt ở nơi khác. Nếu ngoại lệ bị bắt thì chương trình không `abort`, nên "chờ abort" không bao giờ tới. `watch` theo dõi vùng nhớ, không phải sự kiện ném. `-DNDEBUG` chỉ tắt `assert`, không liên quan đến ngoại lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Bạn gõ `gdb -p 543122` vào một chương trình đang treo của chính bạn, nhận `Could not attach to process ... ptrace_scope ... Operation not permitted`. `ptrace_scope` trên máy là `1`. Cách xử lý nằm trong quyền của bạn?

- Gõ lại `gdb -p` với `sudo`, vì mọi tiến trình đều cần quyền root để gắn
- Biên dịch lại với `-O2` để gdb gắn được
- Chạy chương trình trong gdb từ đầu rồi Ctrl+C khi nó treo
- Đổi tên tệp chương trình rồi gắn lại

<p class="giai-thich" markdown>Với `ptrace_scope=1`, chỉ được theo dõi tiến trình **con** của mình; chương trình chạy dưới gdb từ đầu thì là con của gdb, nên dừng bằng `Ctrl+C` (hay `SIGINT`) là được. Dùng `sudo` hay hạ `ptrace_scope` là đụng quyền quản trị và cài đặt hệ thống, không phải việc của người gỡ lỗi. Tối ưu hóa không liên quan đến quyền gắn. Đổi tên tệp không đổi quan hệ cha con.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Cùng chương trình có UB (đọc `p->giaTri` trong `while (true)`), biên dịch `-O0` thì `SIGSEGV`, nhưng `-O2` thì treo mãi, không sập. Cách hiểu nào đúng?

- `-O2` đã sửa lỗi nên chương trình đúng
- `-O2` làm máy không còn phát ra `SIGSEGV`
- gdb tắt `SIGSEGV` khi gặp `-O2`
- UB cho phép trình biên dịch giả định `p` không rỗng, nên sinh vòng lặp rỗng

<p class="giai-thich" markdown>Vì giải tham chiếu `nullptr` là UB, trình biên dịch được giả định nó không xảy ra, nên coi `p` không bao giờ rỗng và vòng lặp không thoát: nó sinh một `jmp` về chính nó (mình xem bằng `objdump`). Lỗi vẫn còn, chỉ đổi triệu chứng. `SIGSEGV` do CPU và hệ điều hành phát khi đọc địa chỉ 0, tối ưu không tắt được, chỉ khiến lệnh đọc đó không còn được sinh ra. gdb không tự tắt tín hiệu nào.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `SIGSEGV` trong gdb: dòng đầu cho tín hiệu và chỗ chết (`tongDanh (p=0x0) at sap.cpp:20`), `bt` và `frame N` cho chuỗi gọi (biến của hàm khác chỉ thấy sau `frame` đúng), `print *p` báo không đọc được địa chỉ 0, `x/i $pc` cho lệnh máy; chỗ sập chỉ là **nạn nhân**, thủ phạm có thể ở nơi khác.
2. Core dump là ảnh chụp bộ nhớ lúc chết: cần `ulimit -c` khác 0 và `core_pattern` cho phép (máy dùng apport thì core vào kho riêng); `gcore tệp` trong gdb tạo core mà không đụng cài đặt hệ thống, `gdb ./prog core` mở lại để xem nhưng không chạy tiếp; ngoại lệ không bắt cho `SIGABRT`, `catch throw` dừng đúng lúc ném.
3. Tràn mảng gây "chết chỗ này, lỗi chỗ kia": chạy thường chết ở `delete`/`free`, log `cout` không tố cáo gì và còn đổi bố cục bộ nhớ nên lỗi dời chỗ, `bt` chỉ thấy nạn nhân, còn `x/10dw` thấy vùng bị đè và `watch -l` trên vùng bị hỏng dừng đúng hàm thủ phạm với đối số sai; ASan (Bài 41) chỉ thẳng dòng ghi và dòng cấp phát.
4. Đa luồng: `info threads`, `thread apply all bt`, `thread N`, `frame N`, `print mutex._M_mutex.__data.__owner` đọc ra ai giữ khóa nào; deadlock là vòng tròn A chờ B, B chờ A (log `cerr` chỉ dòng "xin" cuối, `strace -f` chỉ `FUTEX_WAIT` không dừng); `gdb -p` có thể bị `ptrace_scope=1` chặn nên chạy dưới gdb từ đầu rồi `Ctrl+C`; sửa bằng `std::scoped_lock`.
5. Gỡ lỗi nâng cao: `-O2` sinh `<optimized out>` và có thể đổi sập thành treo (UB), `watch` phần cứng nhanh hơn phần mềm nhiều lần (máy mình 10,7 s so với 51,6 s), `handle SIGUSR1 nostop noprint pass` điều khiển tín hiệu, `.gdbinit` và `rr` chỉ nhắc; Go dùng `GOTRACEBACK`, `dlv` và `go run -race`.
