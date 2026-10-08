# Bài 41 — Công cụ bắt lỗi bộ nhớ và luồng: sanitizer sâu và Valgrind

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Chỉnh được hành vi của sanitizer bằng `ASAN_OPTIONS` (`halt_on_error`, `detect_leaks`, `abort_on_error`), đọc được báo cáo ASan cho lỗi "chết chỗ này, lỗi chỗ kia" ở [Bài 40](40-gdb-nang-cao-core-dump.md), và gắn ASan với gdb.
    - Chạy ThreadSanitizer thật trên data race và deadlock, đọc báo cáo (kể cả dòng `As if synchronized via sleep`), và dùng thêm `-D_GLIBCXX_ASSERTIONS`, `-D_GLIBCXX_DEBUG`, `-fsanitize=undefined` mở rộng, `-fstack-protector`.
    - Biết Valgrind (`memcheck`, `helgrind`, `massif`, `callgrind`) và MemorySanitizer dùng để làm gì, và chọn công cụ theo triệu chứng.

**Bạn cần biết trước:** [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (ASan, UBSan cơ bản: bài này **không dạy lại**), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock), [Bài 38](38-bien-dich-lien-ket-build.md) (cờ biên dịch) và [Bài 40](40-gdb-nang-cao-core-dump.md) (hai ca "chết chỗ này, lỗi chỗ kia" và deadlock mà bài này soi lại).

## 🧠 Câu chuyện mở đầu

Quay lại **dãy tủ khóa** ở [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md), nhưng giờ nó là cả một **tòa nhà** với nhiều ban bảo vệ, mỗi ban canh một việc.

Ban **tủ khóa** (ASan) canh ai mở nhầm ngăn. Ban **luật số học** (UBSan) canh các phép tính sai luật. Ban **sổ ra vào** (TSan) ghi ai vào phòng nào lúc nào, và la lên khi hai người cùng chạm một món đồ mà **không xếp hàng**. Còn **đội kiểm toán thuê ngoài** (Valgrind) không cần sửa tòa nhà, chỉ cần thuê vào kiểm, nhưng làm rất chậm.

Mọi ban bảo vệ đều có chung điều này: họ chỉ báo những gì **xảy ra trong ngày họ làm việc**. Ngày nào lỗi không xảy ra thì họ im lặng.

!!! info "Chỗ nào ví dụ tòa nhà không còn đúng?"
    Bảo vệ thật không đổi tòa nhà, còn sanitizer thì có: g++ **chèn thêm mã kiểm tra** vào chương trình khi biên dịch ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Bài này cũng cho thấy thêm một điều bảo vệ thật không có: bạn có thể bảo ban nào đó "gặp lỗi thì **gọi gdb**" thay vì chỉ báo cáo.

## 📖 Giải thích

### 1. Bản đồ các công cụ

| Công cụ | Cờ biên dịch / lệnh | Bắt | Ghi chú |
|---|---|---|---|
| AddressSanitizer (ASan) | `-fsanitize=address` | Ra ngoài biên, dùng sau khi trả, trả hai lần, rò rỉ (LeakSanitizer đi kèm) | Chậm cỡ vài lần ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) |
| UBSan | `-fsanitize=undefined` | Tràn số có dấu, dịch bit quá cỡ, `vptr`, `nonnull`... | Mục 4 |
| ThreadSanitizer (TSan) | `-fsanitize=thread` | Data race, đảo thứ tự khóa | **Không ghép được** với ASan; mục 5 |
| MemorySanitizer (MSan) | `-fsanitize=memory` | Đọc bộ nhớ **chưa khởi tạo** | **Chỉ có ở clang**; máy mình không có clang nên **mình chưa chạy** |
| Cờ thư viện chuẩn | `-D_GLIBCXX_ASSERTIONS`, `-D_GLIBCXX_DEBUG` | `v[i]` ngoài biên, iterator sai | Mục 3 |
| Bảo vệ stack | `-fstack-protector-strong` | Ghi đè ra ngoài mảng cục bộ, phát hiện lúc hàm trả về | Mục 6 |
| Valgrind | `valgrind ./prog` | Gần như ASan, không cần biên dịch lại; thêm `helgrind`, `massif`, `callgrind` | Mục 7; **mình chưa chạy** |

### 2. ASan sâu hơn: chỉnh bằng `ASAN_OPTIONS`

**`ASAN_OPTIONS`** là biến môi trường, gồm các cặp `tên=giá_trị` cách nhau dấu `:`. Nó đổi hành vi ASan **mà không cần biên dịch lại**. Bốn tùy chọn hay dùng, đều do mình chạy thật:

| Tùy chọn | Tác dụng | Mình thấy |
|---|---|---|
| `halt_on_error=0` | Báo lỗi **rồi chạy tiếp** thay vì dừng ở lỗi đầu | Chỉ có tác dụng nếu đã biên dịch kèm `-fsanitize-recover=address` |
| `detect_leaks=0` | Tắt LeakSanitizer ở cuối chương trình | Chương trình rò rỉ: mặc định mã thoát 1, đặt `0` thì mã 0 và im lặng |
| `abort_on_error=1` | Sau báo cáo, gọi `abort()` (`SIGABRT`) thay vì `exit(1)` | Để gdb hoặc core dump bắt được tại chỗ (xem dưới) |
| `symbolize=0` | Không đổi địa chỉ thành tên hàm và dòng | Báo cáo chỉ còn `#0 0x… (tran_asan+0x…)`, khó đọc; mặc định là bật |

Hai lỗi trong một lượt chạy, để thấy `halt_on_error`:

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* a = new int[3]{1, 2, 3};
    std::cout << "loi 1: " << a[3] << "\n";
    delete[] a;
    std::cout << "loi 2: " << a[0] << "\n";
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 5 | Mảng 3 `int` trên heap |
| 6 | `a[3]` là ô thứ tư, **ngoài biên**: lỗi 1 (đọc) |
| 7 | Trả mảng |
| 8 | `a[0]` sau khi đã trả: lỗi 2 (dùng sau khi trả) |

Biên dịch hai kiểu rồi chạy với `ASAN_OPTIONS=halt_on_error=0`:

```text
$ g++ -std=c++17 -g -fsanitize=address hai_loi.cpp -o hl1
$ ASAN_OPTIONS=halt_on_error=0 ./hl1          # thiếu -fsanitize-recover
(1 báo cáo heap-buffer-overflow rồi dừng, mã thoát 1)

$ g++ -std=c++17 -g -fsanitize=address -fsanitize-recover=address hai_loi.cpp -o hl2
$ ASAN_OPTIONS=halt_on_error=0 ./hl2
loi 1: 0
loi 2: 7
xong                                           # mã thoát 0
```

Bản `hl2` in **hai** báo cáo (mình đếm: `heap-buffer-overflow` ở dòng 6 và `heap-use-after-free` ở dòng 8) và chạy hết. Hai giá trị đọc ra (`0` và `7`) là rác từ bộ nhớ không thuộc mảng.

Lợi ích: một lần chạy thấy mọi lỗi. Nguy cơ: sau lỗi đầu, chương trình đang ở trạng thái hỏng, nên báo cáo về sau có thể là **hệ quả**, không phải lỗi mới.

#### ASan với "chết chỗ này, lỗi chỗ kia"

Quay lại chương trình `tran.cpp` ở mục 4 của [Bài 40](40-gdb-nang-cao-core-dump.md): `datTatCa(diem, 9, -1)` ghi tràn mảng 4 ô, phá đối tượng `phu` nằm sát, và chương trình chết muộn ở `delete phu`. Gdb phải dùng `bt`, `x`, `watch -l` mới tới thủ phạm. Với ASan chỉ cần biên dịch lại rồi chạy:

```text
$ g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer tran.cpp -o tran_asan
$ ./tran_asan
bat dau
==PID==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x… at pc 0x… bp 0x… sp 0x…
WRITE of size 4 at 0x… thread T0
    #0 0x… in datTatCa(int*, int, int) tran.cpp:7
    #1 0x… in main tran.cpp:15
    ...

0x… is located 0 bytes after 16-byte region [0x…,0x…)
allocated by thread T0 here:
    #0 0x… in operator new[](unsigned long) ../../../../src/libsanitizer/asan/asan_new_delete.cpp:98
    #1 0x… in main tran.cpp:12
    ...

SUMMARY: AddressSanitizer: heap-buffer-overflow tran.cpp:7 in datTatCa(int*, int, int)
```

(Mình rút gọn: bỏ địa chỉ, đường dẫn, các khung thư viện, và bảng "Shadow bytes" ở cuối. Mã thoát 1.) Ba dòng đủ giải án:

- `WRITE of size 4 ... tran.cpp:7`: dòng **thủ phạm** là `mang[i] = giaTri;`, gọi từ `main` dòng 15. ASan dừng ở **đúng lần ghi tràn đầu tiên**, trước khi bộ nhớ kề bên bị hỏng, nên không có nạn nhân nào để đuổi theo.
- `0 bytes after 16-byte region`: chỗ ghi nằm ngay sau một khối 16 byte (4 `int`).
- `allocated by ... tran.cpp:12`: khối đó được cấp phát ở dòng 12 (`new int[4]`). Hai dòng 7 và 12 đủ để thấy `n=9` lớn hơn 4.

So với gdb ở Bài 40: ASan không cần biết trước nên theo dõi chỗ nào, và chi phí là biên dịch lại, chạy chậm hơn.

#### ASan kết hợp gdb

Khi cần xem biến lúc ASan bắt lỗi, có hai cách. **Cách 1**: `abort_on_error=1`, để ASan gọi `abort()` rồi gdb dừng ở `SIGABRT` với đủ ngăn xếp. Mình chạy chương trình `hl1` ở trên dưới gdb:

```text
(gdb) set environment ASAN_OPTIONS=abort_on_error=1
(gdb) run
...
Program received signal SIGABRT, Aborted.
(gdb) bt
#4  0x… in __GI_abort () at ./stdlib/abort.c:79
#5  0x… in __sanitizer::Abort () ...
#7  0x… in __asan::ScopedInErrorReport::~ScopedInErrorReport (...)
#8  0x… in __asan::ReportGenericError (...)
#10 0x… in __asan::__asan_report_load4 (...)
#11 0x… in main () at hai_loi.cpp:6
(gdb) frame 11
(gdb) info locals
a = 0x502000000010
(gdb) print a[3]
$1 = 0
```

Tìm khung có tên hàm của bạn (ở đây `#11`, dòng 6) rồi `frame 11` để xem biến.

**Cách 2**: đặt điểm dừng ngay hàm báo lỗi của ASan, **trước** khi nó in báo cáo: `set breakpoint pending on` rồi `break __asan::ReportGenericError`. Mình thử: gdb dừng ở đó, `up 2` đưa về `main () at hai_loi.cpp:6` và `info locals` cho `a`. (Cách 2 dựa vào tên hàm nội bộ của libasan trong g++ 13, có thể đổi giữa các phiên bản; cách 1 ổn định hơn.)

### 3. Cờ thư viện chuẩn: `v[i]` ngoài biên

ASan canh **địa chỉ heap**. Nhưng `std::vector` thường xin dư chỗ (`capacity` lớn hơn `size`), và phần dư vẫn là bộ nhớ hợp lệ, nên `v[size()]` rơi vào đó thì ASan có thể không báo. Thư viện chuẩn của g++ có hai cờ biên dịch kiểm tra **ở mức container**:

| Cờ | Bắt | Chi phí |
|---|---|---|
| `-D_GLIBCXX_ASSERTIONS` | `v[i]` ngoài biên, `front()` của vector rỗng... bằng một `assert` rẻ | Nhỏ, dùng được cả ở bản phát hành |
| `-D_GLIBCXX_DEBUG` | Tất cả ở trên **và** iterator vô hiệu, so sánh iterator khác container... | Lớn: đổi cả bố cục kiểu dữ liệu; mọi tệp và thư viện nối cùng nhau phải dùng cùng cờ |

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

int main() {
    std::vector<int> diem(4, 0);
    std::vector<int> phu(3, 7);
    for (int i = 0; i <= 8; ++i) {
        diem[i] = -1;
    }
    std::cout << "phu[0] = " << phu[0] << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 6–7 | Hai vector: `diem` 4 ô, `phu` 3 ô bằng 7; dữ liệu của chúng ở heap, nằm gần nhau |
| 8–10 | `diem[i]` với `i` chạy `0..8`: từ `i = 4` là ngoài biên |
| 11 | In `phu[0]`: nếu `phu` còn nguyên thì phải là `7` |

Mình biên dịch ba kiểu và chạy:

```text
$ g++ -std=c++17 -g vec.cpp -o vec && ./vec
phu[0] = -1
munmap_chunk(): invalid pointer                    <- mã thoát 134, chết lúc dọn

$ g++ -std=c++17 -g -D_GLIBCXX_ASSERTIONS vec.cpp -o vec && ./vec
.../stl_vector.h:1128: ... operator[](size_type) [with _Tp = int; ...]: Assertion '__n < this->size()' failed.   <- mã 134

$ g++ -std=c++17 -g -D_GLIBCXX_DEBUG vec.cpp -o vec && ./vec
Error: attempt to subscript container with out-of-bounds index 4, but
container only holds 4 elements.                   <- mã 134
```

Bản thường **không** báo gì ở chỗ tràn: `phu[0]` đã thành `-1` (nạn nhân!) rồi sập lúc dọn. Hai cờ kia dừng ngay lần `diem[4]` đầu tiên, và `bt` trong gdb chỉ thẳng `main () at vec.cpp:9`. `_GLIBCXX_DEBUG` còn nói rõ chỉ số `4` và kích thước `4`. Tương tự `v.at(i)` ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) nhưng không cần sửa code.

### 4. UBSan mở rộng

[Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) dạy tràn số và dịch bit. `-fsanitize=undefined` còn gồm nhiều kiểm tra khác (g++ đặt tên từng cái, như `vptr`, `nonnull-attribute`, `bounds`, `null`). Chương trình sau gom ba lỗi:

```cpp
// bo-qua-kiem-tra
#include <iostream>

struct Cha {
    virtual ~Cha() {}
};
struct Con : Cha {
    int x = 1;
};
struct Khac : Cha {};

__attribute__((nonnull)) int chon(const char* ten, int x) {
    return x;
}

int main() {
    Khac k;
    Cha* c = &k;
    Con* sai = static_cast<Con*>(c);
    std::cout << sai->x << "\n";

    const char* rong = nullptr;
    std::cout << chon(rong, 5) << "\n";

    double lon = 1e20;
    int v = static_cast<int>(lon);
    std::cout << v << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 17–19 | `c` trỏ vào một `Khac`, ép xuống `Con*` (dòng 19): sai kiểu, đối tượng thực là `Khac` |
| 20 | Đọc `sai->x` trên đối tượng không phải `Con` |
| 12–14 | `__attribute__((nonnull))` là lời hứa của g++: tham số đầu **không bao giờ** rỗng |
| 23 | Truyền `nullptr` cho tham số đã hứa không rỗng |
| 25–26 | Ép `1e20` (to hơn `int`) sang `int`: ngoài miền |

Biên dịch `-g -fsanitize=undefined`, chạy (rút gọn, thoát mã 0 vì UBSan in rồi chạy tiếp):

```text
ub2.cpp:19:16: runtime error: downcast of address 0x… which does not point to an object of type 'Con'
ub2.cpp:20:23: runtime error: member access within address 0x… which does not point to an object of type 'Con'
ub2.cpp:23:35: runtime error: null pointer passed as argument 1, which is declared to never be null
```

Ba điều rút ra:

- `vptr` bắt ép kiểu xuống sai trong cây kế thừa ([Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md)), và còn in kèm `note: object is of type 'Khac'` (mình lược bỏ).
- Dòng 26 (`1e20` sang `int`) **không** bị báo: `float-cast-overflow` không nằm trong `undefined`. Thêm `-fsanitize=undefined,float-cast-overflow` thì có dòng thứ tư `1e+20 is outside the range of representable values of type 'int'` (mình thử cả hai).
- Muốn dừng ở lỗi đầu: `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`, hoặc biên dịch `-fno-sanitize-recover=undefined`. Mình thử cả hai, chương trình dừng ngay ở báo cáo đầu, mã thoát 1.

### 5. ThreadSanitizer chạy thật

TSan chạy một **sổ ra vào**: mỗi truy cập bộ nhớ và mỗi mutex được ghi lại, nó so xem có hai truy cập từ hai luồng mà **không có quan hệ "xảy ra trước"** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).

Hai lưu ý khi chạy trên máy mình: TSan chạy trần thì dừng với `FATAL: ThreadSanitizer: unexpected memory mapping`, nên mình chạy qua `setarch $(uname -m) -R ./prog` (tắt xáo trộn địa chỉ); và nó chậm: một chương trình 4 luồng ngắn mất 0,34 giây dưới TSan so với 0,03 giây bản thường (một lần đo).

**Ca 1: `sleep` không phải đồng bộ.** Lỗi phổ biến: "chờ đủ lâu thì luồng kia chắc đã xong".

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <thread>

int ketQua = 0;

int main() {
    std::thread t([] { ketQua = 42; });
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    std::cout << "ketQua = " << ketQua << "\n";
    t.join();
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 9 | Luồng `t` ghi `42` vào `ketQua` |
| 10 | `main` ngủ 50 ms, hy vọng `t` đã ghi xong |
| 11 | `main` **đọc** `ketQua` khi chưa `join` và chưa có khóa: đọc và ghi từ hai luồng, không đồng bộ |
| 12 | `join` đến muộn, sau khi đã đọc |

Chạy thường, mình luôn thấy `ketQua = 42`: lỗi **ẩn**. Dưới TSan (`-g -fsanitize=thread`, thoát mã 66), báo cáo thật, rút gọn:

```text
ketQua = 42
==================
WARNING: ThreadSanitizer: data race (pid=…)
  Read of size 4 at 0x… by main thread:
    #0 main ngu.cpp:11

  Previous write of size 4 at 0x… by thread T1:
    #0 operator() ngu.cpp:9
    ...

  As if synchronized via sleep:
    #0 nanosleep ...
    #2 main ngu.cpp:10

  Location is global 'ketQua' of size 4 at 0x…
  Thread T1 (tid=…, finished) created by main thread at:
    #2 main ngu.cpp:9

SUMMARY: ThreadSanitizer: data race ngu.cpp:11 in main
```

Đọc từ trên: `Read ... by main thread: ngu.cpp:11` và `Previous write ... by thread T1: ngu.cpp:9` là hai truy cập xung đột.

Dòng quý nhất là **`As if synchronized via sleep`**: TSan nhận ra bạn *đang dùng `sleep` thay cho đồng bộ* (dòng 10) và nói thẳng điều đó.

Chữa: `t.join()` **trước** khi đọc (hoặc dùng `std::atomic`, `std::future`, [Bài 29](../nhom-3-da-luong/29-async-future.md)): đừng bao giờ tăng thời gian ngủ.

**Ca 2: deadlock hai mutex (nối [Bài 40](40-gdb-nang-cao-core-dump.md)).** Chạy `treo2` (An khóa `bepA` rồi xin `bepB`; Bình ngược lại) dưới TSan thì TSan **không báo gì** và chương trình vẫn treo (mình thử: `timeout 5`, mã 124). Lý do: TSan ghi thứ tự khóa khi một khóa **được lấy xong**, mà hai luồng chưa bao giờ lấy xong khóa thứ hai.

Mình đổi `main` thành chạy **lần lượt** (`an.join()` rồi mới tạo `binh`) để không treo, giữ nguyên hai hàm, đặt tên `treo_tt.cpp`. Lần này TSan thấy hai thứ tự khóa ngược nhau trong cùng chương trình:

```text
ca hai xong
==================
WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=…)
  Cycle in lock order graph: M0 (0x…) => M1 (0x…) => M0

  Mutex M1 acquired here while holding mutex M0 in thread T1:
    #0 pthread_mutex_lock ...
    #4 anLam() treo_tt.cpp:16

  Mutex M0 acquired here while holding mutex M1 in thread T2:
    #0 pthread_mutex_lock ...
    #4 binhLam() treo_tt.cpp:26

SUMMARY: ThreadSanitizer: lock-order-inversion (potential deadlock) ...
```

`M0` là `bepA`, `M1` là `bepB`. T1 (An) lấy `M1` khi đang giữ `M0` (dòng 16), T2 (Bình) lấy `M0` khi đang giữ `M1` (dòng 26): chu trình `M0 => M1 => M0`, chính là deadlock tiềm tàng.

Sửa bằng `std::scoped_lock` ([Bài 40](40-gdb-nang-cao-core-dump.md)) rồi chạy lại: không báo cáo, mã 0. Bài học: TSan bắt **tiềm năng** deadlock miễn là hai thứ tự khóa ngược nhau **từng** xảy ra, dù lần đó không treo.

### 6. `-fstack-protector`: ghi đè stack, phát hiện lúc hàm trả về

ASan canh được mảng cục bộ, nhưng tốn. Cách rẻ hơn: g++ đặt một số bí mật (**canary**, chim hoàng yến trong mỏ) giữa mảng cục bộ và địa chỉ trả về; trước khi hàm trả về, nó kiểm số đó còn nguyên không. Ubuntu bật `-fstack-protector-strong` sẵn (gdb cho thấy cờ này trong `Producer` của tệp mình biên dịch).

```cpp
// bo-qua-kiem-tra
#include <cstring>
#include <iostream>

void chep(const char* nguon) {
    char o[8];
    std::strcpy(o, nguon);
    std::cout << "o = " << o << std::endl;
}

int main(int argc, char** argv) {
    chep(argc > 1 ? argv[1] : "ngan");
    std::cout << "ve main binh an" << std::endl;
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 6 | Mảng `o` chỉ 8 byte, trên stack |
| 7 | `strcpy` chép chuỗi không kiểm độ dài: tràn nếu `nguon` dài hơn 7 ký tự |
| 8 | In `o` |
| 9 | Hàm trả về: ở đây canary được kiểm |
| 12 | Truyền đối số dòng lệnh làm `nguon`, hoặc `"ngan"` nếu không có |

Mình truyền chuỗi 32 chữ `A`, với `-fno-stack-protector` và `-fstack-protector-strong` (cả hai kèm `-D_FORTIFY_SOURCE=0` để không có lớp bảo vệ khác che khuất):

```text
-fno-stack-protector:      o = AAAA...A       <- mã thoát 139 (SIGSEGV, chết lúc trả về với địa chỉ bị đè)
-fstack-protector-strong:  o = AAAA...A
                           *** stack smashing detected ***: terminated     <- mã thoát 134
```

Cả hai đều in `o = AAAA...` (tràn **chưa** bị phát hiện ở dòng 7). Có canary thì dừng sạch ở dòng 9 (cuối hàm) với thông báo rõ; không có thì chương trình nhảy tới địa chỉ rác.

Trong gdb, `bt` của bản có canary lên tới `__stack_chk_fail` rồi `chep (...) at ngan_xep.cpp:9`, và các khung trên nữa là rác `0x4141414141414141` (mã ASCII của `A`): ngăn xếp đã bị đè. Cũng là kiểu "chết muộn": chỗ sập (dòng 9) khác chỗ gây lỗi (dòng 7).

### 7. Valgrind và MSan: chỉ nêu cách dùng

!!! warning "Phần này mình CHƯA chạy"
    Máy mình dùng để viết bài **không cài `valgrind`** (và không có `sudo` để cài), cũng không có `clang` cho MSan. Dưới đây là kiến thức về công cụ, **không có đầu ra dán từ lần chạy**, nên mình không bịa ví dụ báo cáo. Nếu bạn chạy mà thấy khác, tin kết quả của bạn.

**Valgrind** chạy chương trình **đã biên dịch sẵn** trong một "máy ảo" theo dõi từng truy cập bộ nhớ, nên không cần biên dịch lại (nhưng nên có `-g` để có số dòng), và thường chậm hơn ASan nhiều. Bốn công cụ trong bộ:

| Lệnh | Việc | Cách đọc |
|---|---|---|
| `valgrind --leak-check=full ./prog` (`memcheck`, mặc định) | Đọc/ghi ngoài khối, dùng sau khi trả, **dùng giá trị chưa khởi tạo**, rò rỉ | Các mục `Invalid read/write of size N`, `Conditional jump depends on uninitialised value(s)`, cuối là bản tóm tắt rò rỉ `definitely lost` / `indirectly lost` / `still reachable` |
| `valgrind --tool=helgrind ./prog` | Data race và đảo thứ tự khóa (như TSan) | Mục `Possible data race` và `Lock order violated` |
| `valgrind --tool=massif ./prog` rồi `ms_print massif.out.<PID>` | **Dùng heap theo thời gian**: bao nhiêu byte, do dòng nào cấp phát | Đồ thị chữ và danh sách "snapshot" đỉnh dùng bộ nhớ |
| `valgrind --tool=callgrind ./prog` rồi `callgrind_annotate callgrind.out.<PID>` | Đếm lệnh chạy từng hàm, đồ thị gọi hàm | Danh sách hàm xếp theo số lệnh; công cụ GUI `kcachegrind` vẽ lên |

**MSan** (`clang++ -fsanitize=memory -g`) bắt **đọc bộ nhớ chưa khởi tạo**, thứ ASan không bắt. Nó đòi mọi thư viện liên kết cũng được biên dịch kèm MSan, nên khó dùng; ở g++ thì dùng Valgrind `memcheck`, hoặc biên dịch `-Wall -O2` để g++ cảnh báo những ca rõ ràng (mình thấy `-Wuninitialized` ở [Bài 38](38-bien-dich-lien-ket-build.md)).

### 8. Chọn công cụ theo triệu chứng

| Triệu chứng | Công cụ đầu tiên | Vì sao / công cụ phụ |
|---|---|---|
| Rò rỉ bộ nhớ (RAM tăng mãi) | ASan (LeakSanitizer), `massif` | Danh sách khối chưa trả, cùng dòng `new` |
| Ghi/đọc ngoài biên (mảng thô, heap, stack) | ASan | Dòng ghi và dòng cấp phát; `-fstack-protector` cho stack |
| `v[i]` ngoài biên của vector | `-D_GLIBCXX_ASSERTIONS` | Dừng ngay tại `operator[]`; hoặc ASan |
| Use-after-free, double free | ASan | Báo dòng cấp phát, dòng trả, dòng dùng |
| Chết ở `free`/`delete`, bộ nhớ hỏng từ trước | ASan | Chỉ thủ phạm; nếu không có ASan: `watch -l` trong gdb ([Bài 40](40-gdb-nang-cao-core-dump.md)) |
| Data race, kết quả đổi theo lần chạy | TSan | `helgrind` thay thế |
| Treo, nghi deadlock | gdb `thread apply all bt` | TSan bắt thứ tự khóa ngược (ca tuần tự); `scoped_lock` để chữa |
| Dùng biến **chưa khởi tạo** | Valgrind `memcheck`, MSan (clang) | ASan **không** bắt; `-Wall -O2` bắt ca rõ |
| Tràn số có dấu, dịch bit, ép kiểu sai | UBSan | Một dòng mỗi lỗi |
| Chạy chậm | `perf`, `gprof`, `callgrind` | [Bài 42](42-strace-perf-do-hieu-nang.md) |

Chung cho tất cả: chạy sạch **không chứng minh** chương trình đúng. Chạy sanitizer trong kiểm thử, với dữ liệu càng đa dạng càng tốt.

!!! info "Bạn biết Go?"
    Go không có tràn mảng thô, nên phần lớn công cụ ASan/UBSan không cần. Còn data race thì có đúng một công cụ tương ứng TSan: **`go test -race`** (hay `go run -race`, `go build -race`). Theo tài liệu của Go, bộ phát hiện này dựa trên thư viện ThreadSanitizer, và báo `WARNING: DATA RACE` kèm hai ngăn xếp (đọc/ghi). Nó cũng chậm và tốn bộ nhớ hơn bản thường. `go build -asan` và `-msan` có, nhưng chỉ có ý nghĩa khi chương trình dùng cgo (gọi mã C). Go còn có `go vet` để bắt lỗi phổ biến lúc biên dịch. Mình không chạy lại phần Go ở bài này; Go 1.22 trên máy mình cho thấy `panic: index out of range` khi ghi ngoài slice ([Bài 40](40-gdb-nang-cao-core-dump.md)).

## 💻 Ví dụ code

### Ví dụ: sửa data race bằng `std::atomic` rồi kiểm lại bằng TSan

Chương trình đếm với bốn luồng ở [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) có data race. Bản sửa gọn nhất cho **một bộ đếm** là `std::atomic`:

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

std::atomic<int> dem{0};

void tang() {
    for (int i = 0; i < 100000; ++i) {
        ++dem;
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << dem << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 6 | `dem` là `std::atomic<int>`: mỗi `++` là một thao tác nguyên vẹn, không bị xen giữa |
| 8–12 | Mỗi luồng tăng 100000 lần |
| 17 | Bốn luồng chạy cùng lúc |
| 18 | `join` cả bốn **trước** khi đọc `dem` |
| 19 | In `dem`: luôn là `400000` |

Kết quả: `dem = 400000` mọi lần. Mình biên dịch `-g -fsanitize=thread` và chạy qua `setarch $(uname -m) -R`: **không có báo cáo nào**, mã thoát 0. Cùng chương trình khi `dem` là `int` thường thì TSan báo `data race` ngay (đúng báo cáo của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).

Quy trình chung cho mọi lỗi trong bài: tái hiện dưới công cụ phù hợp, đọc **dòng thủ phạm**, sửa gốc (đồng bộ, đúng biên, đúng thứ tự khóa), rồi chạy lại **cùng công cụ** để chứng minh nó im lặng.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "AddressSanitizer, ThreadSanitizer, UBSan: mỗi cái bắt gì, có dùng chung được không?"
    ASan bắt lỗi địa chỉ (ngoài biên, dùng sau khi trả, trả hai lần, rò rỉ), TSan bắt data race và đảo thứ tự khóa, UBSan bắt UB không liên quan địa chỉ (tràn số có dấu, dịch bit, ép kiểu sai, tham số `nonnull`). ASan và UBSan ghép được (`-fsanitize=address,undefined`); TSan **không** ghép với ASan (g++ báo `incompatible`), nên chạy riêng một lượt.

??? question "Chương trình chết ở `delete` hay `free`, code ở đó nhìn đúng. Bạn làm gì?"
    Nghi bộ nhớ đã hỏng từ trước (nạn nhân khác thủ phạm). Biên dịch lại với ASan: nó dừng ở lần ghi tràn đầu tiên và in cả dòng ghi lẫn dòng cấp phát. Nếu không dùng được ASan, đặt `watch -l` trên vùng bị hỏng trong gdb để bắt lệnh ghi đè. Thêm log thường không giúp vì log đổi bố cục bộ nhớ.

??? question "`halt_on_error=0` làm gì, và cần gì kèm theo?"
    Nó bảo ASan báo lỗi xong thì chạy tiếp thay vì dừng, để thấy nhiều lỗi trong một lượt chạy. Phải biên dịch thêm `-fsanitize-recover=address`; thiếu cờ này thì tùy chọn không có tác dụng (mình thử: vẫn dừng ở lỗi đầu, mã 1). Lỗi sau lỗi đầu có thể chỉ là hệ quả của bộ nhớ đã hỏng.

??? question "Valgrind khác sanitizer thế nào, và khi nào chọn nó?"
    Valgrind chạy nguyên bản chương trình đã biên dịch, không biên dịch lại, nên dùng được trên mã không sửa được; bù lại chậm hơn nhiều. Nó bắt thêm **biến chưa khởi tạo** (`memcheck`) mà ASan không bắt, và có `massif` (heap theo thời gian), `callgrind` (đếm lệnh theo hàm). Sanitizer nhanh hơn và chỉ đúng dòng tốt hơn khi bạn biên dịch được.

??? question "Vì sao TSan không báo gì khi chương trình đã treo vì deadlock?"
    TSan ghi thứ tự khóa khi một khóa được lấy xong. Hai luồng treo chưa bao giờ lấy xong khóa thứ hai, nên chưa có "thứ tự ngược" nào được ghi. Chạy lại ca đó theo cách không treo (mỗi luồng chạy lần lượt) thì TSan báo `lock-order-inversion`. Cũng vì thế gdb (`thread apply all bt`) là công cụ cho chương trình đang treo.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng chạy sạch sanitizer là chương trình đúng"
    Sanitizer chỉ thấy đường đi **đã chạy**. Lỗi nằm ở nhánh chưa được kiểm thử vẫn lọt. Chạy với nhiều đầu vào, kể cả đầu vào xấu (rỗng, rất lớn).

!!! warning "Lỗi 2: Đặt `halt_on_error=0` mà quên `-fsanitize-recover=address`"
    Tùy chọn im lặng không có tác dụng: chương trình vẫn dừng ở lỗi đầu. Kiểm tra bằng cách đếm số báo cáo.

!!! warning "Lỗi 3: Chữa data race bằng `sleep`"
    TSan nói thẳng `As if synchronized via sleep`. `sleep` chỉ đổi xác suất, không tạo quan hệ "xảy ra trước". Dùng `join`, mutex, `atomic` hay `future`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="41" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Báo cáo ASan cho chương trình `tran.cpp` có `WRITE of size 4 ... #0 datTatCa(int*, int, int) tran.cpp:7`, `#1 main tran.cpp:15`, và `0 bytes after 16-byte region ... allocated by ... main tran.cpp:12`. Điều nào đúng?

- Lỗi ở `delete phu`, vì đó là chỗ chương trình sập
- Dòng 7 ghi vượt khối cấp phát ở dòng 12
- Dòng 15 cấp phát thiếu bộ nhớ cho mảng `diem`
- Khối 16 byte đã bị trả trước khi dòng 7 ghi vào

<p class="giai-thich" markdown>`WRITE of size 4` tại dòng 7 cùng "0 bytes after 16-byte region" nghĩa là lần ghi nằm ngay sau khối 16 byte (4 `int`) cấp phát ở dòng 12: ghi tràn. Thủ phạm là dòng ghi, không phải `delete phu` (ASan dừng trước khi nạn nhân xuất hiện). Dòng 15 chỉ là nơi gọi hàm với `n=9`. Nếu khối đã bị trả thì báo cáo sẽ là `heap-use-after-free` với dòng `freed by`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Bạn biên dịch `g++ -g -fsanitize=address a.cpp` (không `-fsanitize-recover`) rồi chạy `ASAN_OPTIONS=halt_on_error=0 ./a.out` trên chương trình có hai lỗi bộ nhớ khác nhau. Kết quả?

- Hai báo cáo và chương trình chạy hết, mã thoát 0
- Hai báo cáo rồi dừng, mã thoát 1
- Không báo cáo nào, vì tùy chọn tắt ASan
- Một báo cáo rồi dừng, tùy chọn không có tác dụng

<p class="giai-thich" markdown>`halt_on_error=0` chỉ hoạt động nếu mã đã được biên dịch ở chế độ "có thể phục hồi" (`-fsanitize-recover=address`). Thiếu cờ đó, ASan vẫn dừng ở lỗi đầu tiên và thoát mã 1. Hai báo cáo và mã 0 là kết quả của bản có cờ phục hồi. Tùy chọn này không tắt ASan.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Cùng đoạn `diem[i] = -1;` với `i` tới `8` trên `std::vector<int> diem(4, 0)`. Biên dịch thường chạy ra `phu[0] = -1` rồi chết lúc dọn; thêm `-D_GLIBCXX_ASSERTIONS` thì chạy ra `Assertion '__n < this->size()' failed`. Điều gì đúng?

- Dừng ngay ở lần `diem[4]` đầu, trước khi `phu` bị đè
- Chương trình dừng sau khi `phu` bị đè, vì cờ kiểm tra lúc dọn
- Cờ thêm `try/catch` quanh vòng lặp để bắt lỗi
- Cờ làm `diem` tự lớn thêm để đủ 9 ô

<p class="giai-thich" markdown>`-D_GLIBCXX_ASSERTIONS` làm `operator[]` kiểm `chỉ_số < size()` mỗi lần gọi; `diem[4]` (chỉ số bằng size) vi phạm ngay nên chương trình `abort` ở lần đó, `phu` còn nguyên. Không có kiểm tra lúc dọn. Cờ không thêm ngoại lệ (nó `abort`, không ném). Vector cũng không tự lớn khi dùng `[]`: đó là việc của `push_back`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** TSan in `Read of size 4 ... by main thread: ngu.cpp:11`, `Previous write ... by thread T1: ngu.cpp:9`, và `As if synchronized via sleep: ... main ngu.cpp:10`. Cách sửa đúng?

- Tăng `sleep_for` lên 500 ms để luồng `t` chắc chắn xong
- Bỏ `sleep_for` và đọc `ketQua` ngay
- Gọi `t.join()` trước khi đọc `ketQua`
- Đổi `ketQua` thành `static`

<p class="giai-thich" markdown>`join` tạo quan hệ "xảy ra trước": mọi việc luồng `t` làm (ghi `ketQua`) hoàn tất trước khi `join` trả về, nên đọc sau đó là hợp lệ. Dòng `As if synchronized via sleep` cho biết `sleep` chỉ làm lỗi ít lộ chứ không đồng bộ gì, nên tăng thời gian vẫn là data race. Bỏ sleep càng dễ đọc trước khi ghi. `static` ở phạm vi toàn cục không đổi gì về đồng bộ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Chương trình hai luồng khóa hai mutex ngược thứ tự và **đang treo**. Bạn chạy nó dưới `-fsanitize=thread` và TSan không in gì. Giải thích nào khả dĩ nhất?

- TSan không hỗ trợ `std::mutex`
- Cả hai luồng chưa bao giờ lấy xong khóa thứ hai, nên chưa có thứ tự khóa ngược nào được ghi
- Deadlock không phải lỗi mà TSan nhận biết
- TSan đã sửa deadlock nên chương trình không treo

<p class="giai-thich" markdown>TSan phát hiện đảo thứ tự khóa bằng cách ghi lại "lấy khóa B khi đang giữ khóa A" mỗi khi một khóa được lấy **xong**. Hai luồng treo kẹt ở lần xin thứ hai, nên chưa ghi được thứ tự nào. Chạy tuần tự để chương trình không treo thì TSan báo `lock-order-inversion`. TSan hỗ trợ `std::mutex` bình thường, và nó chỉ báo cáo, không tự sửa gì.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Hàm đọc một biến cục bộ `int x;` chưa gán rồi dùng nó trong `if`. Trên máy chỉ có g++ (không clang) và Valgrind đã cài, công cụ nào đáng thử đầu tiên?

- Valgrind `memcheck`, vì nó theo dõi giá trị chưa gán
- ASan, vì nó bắt mọi lỗi bộ nhớ phát sinh lúc chạy chương trình
- TSan, vì biến chưa gán là một dạng đua
- `-D_GLIBCXX_DEBUG`, vì nó kiểm biến cục bộ

<p class="giai-thich" markdown>`memcheck` theo dõi từng bit đã được khởi tạo chưa và báo `Conditional jump depends on uninitialised value(s)` khi giá trị đó quyết định một nhánh. ASan canh địa chỉ nên **không** thấy biến chưa gán. TSan chỉ lo truy cập giữa các luồng. `_GLIBCXX_DEBUG` lo container của thư viện chuẩn, không lo biến cục bộ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Hàm `chep` có `char o[8]` và `strcpy(o, nguon)` với `nguon` dài 32 ký tự, biên dịch `-fstack-protector-strong`. Chương trình in `o = AAAA...` rồi `*** stack smashing detected ***: terminated`. Dòng nào là chỗ **phát hiện**, dòng nào là chỗ **gây lỗi**?

- Phát hiện ở `strcpy`, gây lỗi ở cuối hàm
- Phát hiện ở `strcpy` ngay lúc ghi, gây lỗi cũng ở `strcpy`
- Phát hiện lúc hàm trả về (dấu `}`), gây lỗi ở `strcpy`
- Phát hiện ở `main`, gây lỗi ở `std::cout`

<p class="giai-thich" markdown>Canary chỉ được kiểm ngay trước khi hàm trả về, nên thông báo đến từ dấu `}` cuối `chep`, sau khi `strcpy` đã ghi đè. Việc `o = AAAA...` vẫn in ra cho thấy tràn không bị chặn ở `strcpy`. `main` không gây lỗi, và `std::cout` chỉ in chuỗi `o`. Nên đây là ca "chết muộn" hơi khác ca heap: nạn nhân và thủ phạm cách nhau vài dòng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 8.** ASan báo lỗi trong chương trình và bạn muốn xem giá trị biến lúc đó trong gdb mà không phải đoán. Cách nào đúng?

- Chạy `gdb` rồi gõ `catch asan`
- Đặt `ASAN_OPTIONS=symbolize=0` để gdb đọc được địa chỉ
- Biên dịch thêm `-fsanitize=thread` để gdb nhận biết
- Đặt `ASAN_OPTIONS=abort_on_error=1`, để ASan `abort()` rồi dừng ở `SIGABRT`, dùng `frame N` tới khung của mình

<p class="giai-thich" markdown>Với `abort_on_error=1`, sau báo cáo ASan gọi `abort()`, gdb dừng ở `SIGABRT` với ngăn xếp đầy đủ, và `frame N` tới khung hàm của bạn cho `info locals`. Không có lệnh `catch asan` trong gdb. `symbolize=0` làm báo cáo khó đọc hơn, không giúp gdb. TSan không ghép được với ASan, và cũng không liên quan đến việc gdb dừng.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `ASAN_OPTIONS` chỉnh ASan không cần biên dịch lại: `halt_on_error=0` (phải kèm `-fsanitize-recover=address`, thiếu thì vẫn dừng ở lỗi đầu), `detect_leaks=0` (tắt LeakSanitizer), `abort_on_error=1` (để gdb dừng ở `SIGABRT` rồi `frame N` xem biến), `symbolize=0` (mất tên hàm và dòng).
2. Với lỗi "chết chỗ này, lỗi chỗ kia" của Bài 40, ASan chỉ ngay `WRITE of size 4 ... datTatCa tran.cpp:7` và `allocated by ... tran.cpp:12`: dừng ở lần ghi tràn đầu tiên, trước khi nạn nhân xuất hiện; `-D_GLIBCXX_ASSERTIONS` (rẻ) và `-D_GLIBCXX_DEBUG` (đắt, cần nhất quán cờ) bắt `v[i]` ngoài biên ngay tại `operator[]`, khi bản thường chỉ chết muộn lúc dọn.
3. `-fsanitize=undefined` còn gồm `vptr` (ép kiểu xuống sai), `nonnull-attribute`..., nhưng không gồm `float-cast-overflow` (phải thêm); `-fstack-protector-strong` (Ubuntu bật sẵn) phát hiện ghi đè stack lúc hàm trả về với `*** stack smashing detected ***`, nghĩa là chết muộn hơn dòng gây lỗi.
4. TSan chạy thật (qua `setarch $(uname -m) -R` trên máy này): bắt data race với hai ngăn xếp đọc/ghi và dòng `As if synchronized via sleep` khi dùng `sleep` thay đồng bộ; bắt `lock-order-inversion` khi hai thứ tự khóa ngược nhau từng xảy ra, nhưng im lặng với chương trình đã treo vì deadlock (dùng gdb cho ca đó); sửa rồi chạy lại cùng công cụ để thấy nó im.
5. Valgrind (`memcheck` cho biến chưa khởi tạo và rò rỉ, `helgrind` cho đua, `massif` cho heap theo thời gian, `callgrind` cho đếm lệnh) và MSan (chỉ clang) bài này **chưa chạy** vì máy không có; chọn công cụ theo triệu chứng (rò rỉ, ngoài biên, use-after-free, data race, biến chưa khởi tạo, UB số học); chạy sạch không chứng minh chương trình đúng; Go có `go test -race` ứng với TSan.
