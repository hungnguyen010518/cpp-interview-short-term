# Bài 38 — Từ mã nguồn đến chương trình: biên dịch, liên kết và build

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Kể được bốn bước g++ biến `.cpp` thành chương trình (tiền xử lý, biên dịch, hợp ngữ, liên kết) và biết lỗi nào thuộc bước nào.
    - Đọc được hai lỗi liên kết kinh điển (`undefined reference`, `multiple definition`) và biết các công cụ soi tệp: `nm`, `c++filt`, `objdump`, `ldd`, `readelf`, `addr2line`.
    - Chọn được cờ biên dịch cho gỡ lỗi (`-g -O0`, `-Wall -Wextra`, `-DNDEBUG`, `-fsanitize=...`), viết được một `Makefile` nhỏ và đọc được một `CMakeLists.txt` nhỏ.

**Bạn cần biết trước:** [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (lệnh `g++` đầu tiên) và [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (`-Wall -Wextra`, `-fsanitize`). Bài này là nền cho cả ba bài gỡ lỗi sau (gdb, sanitizer, strace/perf): công cụ nào cũng cần bạn hiểu chương trình **được tạo ra thế nào**.

## 🧠 Câu chuyện mở đầu

Bạn mở một **xưởng làm sách**. Mỗi chương do một người viết, ghi trên giấy nháp riêng. Muốn thành sách, phải qua bốn trạm.

Trạm 1: **dán** các tờ chèn sẵn vào đúng chỗ (chương nào ghi "xem trang bìa" thì dán trang bìa vào). Trạm 2: **dịch** từng chương sang chữ in (máy chỉ đọc được chữ in). Trạm 3: **đóng** chữ in thành từng tập (mỗi chương một tập). Trạm 4: **ghép** các tập thành cuốn sách, và nối mọi chỗ "xem chương 3" thành số trang thật.

Nếu chương 1 viết "xem chương 3" mà không ai đưa chương 3 vào xưởng, trạm 1 đến 3 vẫn làm xong. **Chỉ trạm 4 mới phát hiện** thiếu chương 3.

Biên dịch C++ y hệt thế. Biết lỗi nằm ở trạm nào là nửa đường tới chỗ sửa.

!!! info "Chỗ nào ví dụ xưởng sách không còn đúng?"
    Xưởng sách làm một lượt rồi xong. Với C++, bạn sửa một chương thì chỉ chương đó phải đi lại trạm 1 đến 3; trạm 4 chạy lại. Công cụ như `make` (mục 5) sinh ra để làm đúng việc này.

## 📖 Giải thích

### 1. Bốn trạm của g++

Lệnh `g++ main.cpp tong.cpp -o prog` làm cả bốn trạm cho mỗi tệp `.cpp`, rồi liên kết chung. Bạn có thể dừng ở từng trạm để xem sản phẩm của nó.

| Trạm | Việc | Cờ dừng sau trạm | Sản phẩm | Lỗi hay gặp ở đây |
|---|---|---|---|---|
| 1. Tiền xử lý (preprocess) | Thay `#include` bằng nguyên văn tệp, thay `#define`, bỏ khối `#if` sai | `-E` | Văn bản C++ rất dài | `fatal error: x.h: No such file or directory` |
| 2. Biên dịch (compile) | Kiểm cú pháp và kiểu, sinh hợp ngữ | `-S` | Tệp `.s` (chữ) | `error:` về cú pháp, kiểu, tên chưa khai báo |
| 3. Hợp ngữ (assemble) | Đổi chữ hợp ngữ thành mã máy | `-c` | Tệp đối tượng `.o` | Hiếm gặp |
| 4. Liên kết (link) | Ghép các `.o` và thư viện, nối tên với địa chỉ | (mặc định) | Chương trình chạy được | `undefined reference`, `multiple definition` |

**Tệp đối tượng (object file, `.o`)** là mã máy của *một* tệp `.cpp`, trong đó những chỗ gọi hàm ở tệp khác còn **để trống tên**. **Đơn vị biên dịch (translation unit)** là một tệp `.cpp` cùng mọi thứ nó `#include` về, sau trạm 1: trình biên dịch chỉ thấy một đơn vị tại một lúc.

Mình thử trên chương trình hai tệp (`main.cpp` gọi `tong` khai báo ở `tong.h`, định nghĩa ở `tong.cpp`). Trạm 1 phình `main.cpp` 3 dòng thành 36520 dòng, vì `#include <iostream>` kéo cả thư viện chuẩn vào (số đổi theo phiên bản g++):

```text
$ g++ -std=c++17 -E main.cpp | wc -l
36520
$ g++ -std=c++17 -S -o main.s main.cpp && wc -l main.s
70 main.s
```

### 2. Hai lỗi liên kết kinh điển

Trạm 4 chỉ nhìn **tên** (symbol): ai *cần* tên nào, ai *có* tên nào. Hai lỗi sinh ra từ hai chuyện ngược nhau.

**`undefined reference`: cần mà không ai có.** Mình biên dịch `main.cpp` thành `main.o` rồi liên kết một mình nó (quên `tong.o`). g++ báo (rút gọn):

```text
$ g++ main.o -o prog
/usr/bin/ld: main.o: in function `main':
main.cpp:(.text+0x13): undefined reference to `tong(int, int)'
collect2: error: ld returned 1 exit status
```

`ld` là chương trình liên kết. Nó nói rõ: trong hàm `main` có chỗ gọi `tong(int, int)` mà không tệp nào cung cấp. Nguyên nhân hay gặp: quên thêm tệp `.cpp` vào lệnh biên dịch, quên `-lthư_viện`, khai báo (`tong.h`) có mà định nghĩa không có, hoặc khai báo và định nghĩa **lệch chữ ký** (khác kiểu tham số thì là hai hàm khác tên).

**`multiple definition`: có tới hai nơi cung cấp.** Mình đặt *thân* hàm `int hai() { return 2; }` thẳng trong `h.h`, rồi `a.cpp` và `b.cpp` cùng `#include "h.h"`. Mỗi tệp `.o` đều mang một bản `hai`, nên:

```text
$ g++ a.cpp b.cpp -o p
/usr/bin/ld: ... in function `hai()':
b.cpp:(.text+0x0): multiple definition of `hai()'; ...a.cpp:(.text+0x0): first defined here
collect2: error: ld returned 1 exit status
```

Cách chữa: header chỉ chứa **khai báo** (`int hai();`) và thân nằm ở đúng một `.cpp`; hoặc thêm `inline` cho hàm nhỏ muốn để thân trong header (template cũng vậy, [Bài 34](../nhom-4-oop-patterns/34-template.md)).

!!! note "Quy tắc một định nghĩa (ODR)"
    Chuẩn C++ gọi là **One Definition Rule**: mỗi hàm, mỗi biến toàn cục chỉ được định nghĩa một lần trong cả chương trình (trừ `inline`, template, lớp: được định nghĩa ở nhiều đơn vị miễn là **giống hệt**). Vi phạm có thể không bị báo (hai bản khác nhau, không ai kiểm) và thành hành vi không xác định, nên `multiple definition` là kết quả còn **dễ chịu**.

### 3. Soi tệp: bộ đồ nghề đọc "tên" và "mã máy"

Khi liên kết lỗi hay chương trình lạ, đừng đoán: nhìn vào tệp. Sáu lệnh sau có sẵn trên Linux với bộ g++ (binutils).

| Lệnh | Việc | Ví dụ trên chương trình `prog` ở trên |
|---|---|---|
| `nm tep.o` | Liệt kê tên trong tệp: `T` = có định nghĩa, `U` = cần từ nơi khác | `nm -C main.o` cho `T main` và `U tong(int, int)` |
| `c++filt` hoặc `nm -C` | Đổi tên đã **mangling** thành tên đọc được | `echo _Z4tongii \| c++filt` ra `tong(int, int)` |
| `objdump -d tep` | Dịch ngược mã máy ra hợp ngữ | So sánh `-O0` và `-O2` (mục 4) |
| `ldd chuongtrinh` | Liệt kê thư viện động mà chương trình cần lúc chạy | `libstdc++.so.6`, `libc.so.6`, `libm.so.6` |
| `readelf -S tep` | Liệt kê các "mục" (section) trong tệp | Đếm mục `.debug_*` (mục 4) |
| `addr2line -e tep -f -C addr` | Từ địa chỉ trong chương trình tra ra hàm và dòng nguồn (cần `-g`) | Dùng khi báo cáo lỗi chỉ cho địa chỉ |

**Mangling (đổi tên)**: C++ cho phép nhiều hàm cùng tên (nạp chồng, [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md)), nên tệp `.o` phải lưu tên *kèm kiểu tham số*. `tong(int, int)` trở thành `_Z4tongii`: `_Z` mở đầu, `4tong` là tên dài 4 chữ, `ii` là hai `int`. Báo lỗi liên kết thường đã đổi lại giúp bạn; nếu gặp chuỗi `_Z...` lạ, chuyền vào `c++filt`. Tên đổi theo trình biên dịch, nên đây là chi tiết cài đặt, không phải chuẩn.

Hai điều đáng nhớ khi đọc `nm`: `U` ở `main.o` rồi `T` ở `tong.o` là cặp mà trạm 4 ghép; và hàm có `T` ở *hai* tệp là `multiple definition`.

### 4. Cờ biên dịch cho gỡ lỗi

Cùng một mã nguồn, cờ khác nhau cho ra chương trình rất khác nhau. Bảng dưới là bộ bạn dùng hằng ngày.

| Cờ | Tác dụng | Dùng khi |
|---|---|---|
| `-std=c++17` | Chọn phiên bản ngôn ngữ | Luôn nêu rõ |
| `-Wall -Wextra` | Bật thêm cảnh báo | Luôn bật; coi cảnh báo là lỗi |
| `-Werror` | Cảnh báo thành lỗi, không biên dịch | CI, để cảnh báo không tích tụ |
| `-g` | Ghi **thông tin gỡ lỗi** (tên biến, số dòng) vào tệp | Mọi lúc định gỡ lỗi |
| `-O0` | Không tối ưu hóa (mặc định khi không ghi `-O`) | Gỡ lỗi bằng gdb: biến và dòng khớp mã |
| `-O2` | Tối ưu cho tốc độ | Bản phát hành, đo hiệu năng |
| `-DNDEBUG` | Định nghĩa `NDEBUG`, tắt `assert` | Bản phát hành |
| `-fsanitize=address,undefined` | Thêm bước kiểm tra lúc chạy ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) | Kiểm thử |
| `-fno-omit-frame-pointer` | Giữ con trỏ khung để danh sách hàm đầy đủ | Cùng sanitizer, `perf` |
| `-save-temps` | Giữ lại tệp trung gian `.ii`, `.s`, `.o` | Muốn xem từng trạm |

**`-g` không làm chương trình chạy chậm.** Mình biên dịch cùng chương trình có và không `-g`: hai tệp có cùng `size` (phần `text` 1821 byte), nhưng tệp có `-g` mang thêm 6 mục `.debug_*` (đếm bằng `readelf -S`), tệp không có thì 0. Thông tin này nằm trong tệp nhưng không được nạp khi chạy. Nên bản phát hành vẫn nên biên dịch `-g` rồi tách riêng, để khi sập có chỗ tra dòng.

**`-O0` và `-O2` cho mã máy khác hẳn.** Hàm `tong` ở `-O0`, mình dịch ngược bằng `objdump -d`:

```text
push   %rbp
mov    %rsp,%rbp
mov    %edi,-0x4(%rbp)      ; cất a vào stack
mov    %esi,-0x8(%rbp)      ; cất b vào stack
mov    -0x4(%rbp),%edx      ; đọc lại a
mov    -0x8(%rbp),%eax      ; đọc lại b
add    %edx,%eax
pop    %rbp
ret
```

Cùng hàm ở `-O2` chỉ còn hai lệnh `lea (%rdi,%rsi,1),%eax` rồi `ret`: không cất gì vào stack. Hệ quả cho gỡ lỗi: ở `-O2`, **biến có thể không còn tồn tại** (nằm thanh ghi rồi bị dùng đè), dòng nguồn bị trộn thứ tự, hàm nhỏ bị nhét thẳng vào nơi gọi (**inline**), và gdb sẽ báo `<optimized out>`. Vì vậy: **gỡ lỗi bằng gdb thì dùng `-g -O0`** (hoặc `-Og`, tối ưu mức vừa phải cho gỡ lỗi, ít mất biến hơn `-O2`); đo tốc độ thì dùng `-O2`. Đừng đo tốc độ trên bản `-O0`.

Cảnh báo cũng phụ thuộc cờ tối ưu, vì có cảnh báo cần phân tích luồng dữ liệu mà `-O0` không làm. Với `int main(){ int x; return x; }`, mình biên dịch `-Wall -Wextra -O2` thì g++ báo `'x' is used uninitialized [-Wuninitialized]`. Vì thế CI nên biên dịch cả hai chế độ.

### 5. `assert` và `NDEBUG`: kiểm tra chỉ có trong bản gỡ lỗi

`assert(điều_kiện)` (trong `<cassert>`) dừng chương trình nếu điều kiện sai, kèm tên tệp và dòng. Khi biên dịch với `-DNDEBUG`, **mọi `assert` biến mất**, kể cả biểu thức bên trong. Mình chạy `assert(1 + 1 == 3)` hai lần:

```text
$ g++ as.cpp -o as && ./as
as: as.cpp:3: int main(): Assertion `1 + 1 == 3' failed.
Aborted (core dumped)         # mã thoát 134 = 128 + SIGABRT (6)
$ g++ -DNDEBUG as.cpp -o as2 && ./as2
xong                          # mã thoát 0
```

Bẫy hay gặp: **đừng đặt việc cần làm vào trong `assert`**. `assert(xoa(f))` thì bản phát hành không bao giờ gọi `xoa`.

### 6. `make`: chỉ làm lại phần đã đổi

Gõ tay lệnh g++ cho 50 tệp thì khổ. **Makefile** là tệp ghi quy tắc "tệp đích cần các tệp nào, tạo bằng lệnh nào"; `make` so thời gian sửa tệp và chỉ làm lại những gì cũ hơn nguồn của nó. Makefile nhỏ cho chương trình hai tệp:

```text
CXX      := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -g -O0
OBJ      := main.o tong.o

prog: $(OBJ)
	$(CXX) $(OBJ) -o $@

%.o: %.cpp tong.h
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) prog
```

Dòng thụt đầu dòng **phải là ký tự Tab**, không phải dấu cách. `$@` là tên đích, `$<` là nguồn đầu tiên, `%.o: %.cpp` là quy tắc mẫu (mọi `x.o` làm từ `x.cpp`). Mình chạy `make` hai lần liên tiếp, giữa hai lần không sửa gì:

```text
$ make
g++ ... -c main.cpp -o main.o
g++ ... -c tong.cpp -o tong.o
g++ main.o tong.o -o prog
$ make
make: 'prog' is up to date.
```

Lần hai không làm gì. Sau `touch tong.h` (giả vờ sửa header) thì **cả hai** `.cpp` được biên dịch lại, vì quy tắc ghi `tong.h` là nguồn của mọi `.o`.

Lỗi kinh điển: header đổi mà Makefile không biết nó là nguồn của `.o`. Chương trình có khi nối `main.o` cũ với `tong.o` mới, và lệch bố cục lớp giữa hai tệp là UB. Cách thủ công: chạy `make clean` rồi `make` mỗi khi nghi ngờ. Cách lâu dài là để công cụ tự dò phụ thuộc (cờ `-MMD` của g++, hoặc CMake).

### 7. CMake: viết một lần, sinh Makefile hay dự án IDE

**CMake** không biên dịch gì: nó **sinh** Makefile (hay tệp của Ninja, Visual Studio) từ một tệp mô tả `CMakeLists.txt`. Ưu điểm: dò phụ thuộc header tự động, chạy trên nhiều hệ điều hành, và tách *kiểu build* khỏi mô tả dự án.

```text
cmake_minimum_required(VERSION 3.16)
project(demo CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(prog main.cpp tong.cpp)
target_compile_options(prog PRIVATE -Wall -Wextra)
```

Dùng (gọi là **build ngoài mã nguồn**, giữ thư mục nguồn sạch):

```text
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug     # sinh vào thư mục build/
cmake --build build                              # biên dịch
```

`CMAKE_BUILD_TYPE` quyết định bộ cờ: `Debug` thường ra `-g` (không tối ưu), `Release` ra `-O3 -DNDEBUG`, `RelWithDebInfo` ra `-O2 -g -DNDEBUG`. Bật sanitizer thì thêm `-DCMAKE_CXX_FLAGS="-fsanitize=address,undefined"`.

!!! warning "Phần CMake trong bài này mình CHƯA chạy"
    Máy mình dùng để viết bài **không cài `cmake`**, nên mọi thứ ở mục 7 đến từ kiến thức về công cụ, không phải từ lần chạy. Mục 1 đến 6 và mục 8 thì mình đã chạy thật. Nếu bạn chạy mà thấy khác, tin kết quả của bạn rồi báo mình.

### 8. Ví dụ: macro ghi nhật ký chỉ có ở bản gỡ lỗi

Nghề gỡ lỗi cũ nhất: in ra màn hình. Làm cho tử tế thì in kèm **tên tệp, dòng, hàm** và tắt được khi phát hành. Đoạn sau dùng `NDEBUG` (mục 5) và ba macro có sẵn `__FILE__`, `__LINE__`, `__func__` (chương trình đầy đủ ở phần ví dụ).

## 💻 Ví dụ code

### Ví dụ: `LOG` tự ghi vị trí và biến mất khi `-DNDEBUG`

```cpp
#include <iostream>

#ifndef NDEBUG
#define LOG(x) (std::cerr << __FILE__ << ":" << __LINE__ << " " << __func__ \
                          << ": " #x " = " << (x) << "\n")
#else
#define LOG(x) ((void)0)
#endif

int chiaNguyen(int a, int b) {
    LOG(a);
    LOG(b);
    return a / b;
}

int main() {
    int kq = chiaNguyen(17, 5);
    std::cout << "kq = " << kq << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 3 | Nếu **chưa** định nghĩa `NDEBUG` (bản gỡ lỗi) thì dùng bản `LOG` có in |
| 4–5 | `LOG(x)` in `tệp:dòng hàm: tên_biểu_thức = giá_trị` ra `cerr`; `#x` biến biểu thức thành chuỗi chữ; `__FILE__`, `__LINE__`, `__func__` do trình biên dịch điền tại chỗ `LOG` được viết (dấu `\` cuối dòng 4 nối tiếp sang dòng 5) |
| 6–7 | Bản phát hành: `LOG` thành câu lệnh rỗng, không tốn gì |
| 11–12 | Hai lần gọi `LOG`: số dòng in ra là **chỗ gọi macro** (11 và 12), không phải chỗ định nghĩa macro |
| 13 | Phép chia (nếu `b` là 0 thì là UB, [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) |
| 17–18 | Gọi `chiaNguyen(17, 5)` và in kết quả `3` ra `cout` |

Kết quả khi biên dịch `g++ -std=c++17 -Wall -Wextra`: `cerr` có hai dòng (tên tệp tùy bạn đặt) và `cout` có `kq = 3`. Biên dịch thêm `-DNDEBUG` thì hai dòng `LOG` biến mất, còn `kq = 3` vẫn in.

Macro làm việc này vì nó là **thay chữ ở trạm 1**, lúc chưa có hàm hay kiểu, nên mới biết `__LINE__` là dòng của chỗ gọi. Hàm thường không làm được điều này. (Từ C++20 có `std::source_location`, nhưng bài này dùng C++17.) Cái giá là macro không biết kiểu và `x` được tính hai lần nếu viết ẩu: đừng `LOG(i++)`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Quá trình từ file .cpp đến chương trình chạy được gồm những bước nào?"
    Bốn bước. Tiền xử lý: thay `#include` và `#define`. Biên dịch: kiểm cú pháp, kiểu và sinh hợp ngữ. Hợp ngữ: đổi thành tệp đối tượng `.o`. Liên kết: ghép các `.o` và thư viện, nối từng tên hàm/biến với địa chỉ. Mỗi `.cpp` được biên dịch **độc lập** thành một đơn vị biên dịch, nên chỉ ở bước liên kết mới phát hiện thiếu hay trùng định nghĩa.

??? question "Phân biệt `undefined reference` và lỗi biên dịch thường."
    Lỗi biên dịch xảy ra khi đang xử lý một `.cpp`: tên chưa khai báo, sai kiểu, thiếu dấu chấm phẩy. `undefined reference` do trình **liên kết** báo, sau khi mọi `.cpp` đã biên dịch xong: khai báo có nhưng không ai cung cấp định nghĩa. Nguyên nhân hay gặp: quên tệp `.cpp` hay thư viện (`-l`), lệch chữ ký giữa khai báo và định nghĩa, thân template nằm ở `.cpp` ([Bài 34](../nhom-4-oop-patterns/34-template.md)). Cách điều tra: `nm -C` các `.o` xem tên đó có `T` ở đâu không.

??? question "`multiple definition` là gì và chữa thế nào?"
    Một hàm hay biến toàn cục không phải `inline` được định nghĩa trong header, nên mọi `.cpp` include nó đều mang một bản, và liên kết gặp nhiều bản. Chữa: header chỉ khai báo, thân đặt ở một `.cpp`; hoặc `inline` (hàm), hoặc `inline` biến (C++17), hoặc `static`/vùng tên ẩn danh nếu muốn mỗi tệp một bản riêng. Nằm trong quy tắc một định nghĩa (ODR).

??? question "Vì sao khi dùng gdb phải biên dịch `-g -O0`?"
    `-g` ghi tên biến và ánh xạ dòng nguồn–mã máy vào tệp; không có nó gdb chỉ thấy địa chỉ. `-O0` giữ nguyên cấu trúc: mỗi biến có chỗ trên stack, mỗi dòng ứng với đoạn mã riêng. Ở `-O2` trình biên dịch có thể xóa biến, đổi thứ tự dòng, nhét hàm vào nơi gọi, nên gdb báo `<optimized out>` và bước từng dòng nhảy lung tung. `-Og` là thỏa hiệp.

??? question "`assert` và `NDEBUG` quan hệ thế nào, có bẫy gì?"
    `assert(c)` dừng chương trình (abort, mã 134) nếu `c` sai, kèm tên tệp, dòng, biểu thức. Biên dịch với `-DNDEBUG` thì `assert` bị xóa hoàn toàn, nên biểu thức bên trong **không được chạy**. Bẫy: đặt việc có hiệu ứng phụ (như gọi hàm xóa, `i++`) trong `assert`; bản phát hành sẽ khác bản gỡ lỗi. `assert` dành cho lỗi lập trình (điều "không thể xảy ra"), không phải cho lỗi môi trường như tệp không mở được.

??? question "Makefile và CMake khác nhau thế nào?"
    Makefile là tập quy tắc trực tiếp mà `make` đọc: đích, nguồn, lệnh; `make` so thời gian tệp để chỉ làm lại phần cũ. CMake không biên dịch: nó đọc `CMakeLists.txt` và **sinh** Makefile (hay tệp Ninja, Visual Studio). CMake tự dò phụ thuộc header, hỗ trợ nhiều nền tảng và kiểu build (`Debug`/`Release`). Makefile tay dễ quên khai báo header là nguồn, dẫn tới chương trình ghép tệp `.o` cũ và mới.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gỡ lỗi trên bản `-O2` rồi tưởng gdb hỏng"
    Biến `<optimized out>`, bước nhảy lung tung là hệ quả của tối ưu hóa, không phải gdb sai. Biên dịch lại `-g -O0`. Nếu lỗi chỉ xuất hiện ở `-O2`, đó thường là dấu hiệu UB ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)), hãy thử sanitizer.

!!! warning "Lỗi 2: Đặt thân hàm thường trong header"
    Chạy được khi chỉ một `.cpp` include nó, rồi vỡ `multiple definition` ngay khi có `.cpp` thứ hai. Header chỉ nên có khai báo, `inline`, `constexpr` và template.

!!! warning "Lỗi 3: Sửa header mà không biên dịch lại hết"
    Makefile thiếu phụ thuộc làm `make` bỏ qua tệp cần làm lại; kết quả là chương trình ghép hai bố cục lớp khác nhau, sập ở chỗ không liên quan. Nghi ngờ thì `make clean && make`, hoặc dùng CMake.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="38" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Bạn gõ `g++ -c main.cpp`, trong đó `main.cpp` gọi hàm `tong` chỉ được khai báo ở `tong.h` và chưa được định nghĩa ở đâu. Chuyện gì xảy ra?

- Báo `undefined reference to tong`, vì g++ dừng ở bước biên dịch
- Báo `multiple definition`, vì `tong` được khai báo nhưng chưa có thân
- Tạo ra `main.o` thành công, và chỗ gọi `tong` còn để trống tên
- Báo lỗi vì không tìm thấy thân hàm trong `tong.h`

<p class="giai-thich" markdown>`-c` dừng sau bước hợp ngữ, không liên kết. Khai báo là đủ cho trình biên dịch kiểm cú pháp và kiểu của lời gọi, nên `main.o` được tạo, trong đó `tong(int, int)` ở dạng `U` (cần từ nơi khác, xem bằng `nm -C`). Lỗi `undefined reference` chỉ đến ở bước liên kết, nếu lệnh liên kết không có tệp nào định nghĩa `tong`. `multiple definition` là bệnh ngược lại: quá nhiều định nghĩa, không phải thiếu. Header chỉ có khai báo là cách viết đúng, không phải lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Hai tệp `a.cpp` và `b.cpp` cùng `#include "h.h"`, và `h.h` chứa `int hai() { return 2; }`. Lệnh `g++ a.cpp b.cpp -o p` báo gì?

- `multiple definition of hai()` ở bước liên kết
- Không lỗi, vì trình biên dịch gộp hai bản giống nhau
- `redefinition of hai()` ở bước biên dịch của `b.cpp`
- `undefined reference to hai()` ở bước liên kết

<p class="giai-thich" markdown>Mỗi `.cpp` được biên dịch riêng và chỉ thấy **một** bản `hai` (qua `#include`), nên trình biên dịch không phàn nàn. Cả hai `.o` đều có hàm `hai` ở dạng `T`, và liên kết thấy hai nơi cùng định nghĩa nên báo `multiple definition`. Thêm `inline` mới cho phép trùng như thế. `undefined reference` ngược lại với tình huống này: ở đây tên có tới hai nơi, không phải không có nơi nào. Lỗi `redefinition` chỉ có khi hai định nghĩa nằm trong **cùng một** đơn vị biên dịch.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Chương trình có `assert(dem(f) > 0);`, trong đó `dem` đếm số dòng và còn mở và đọc tệp. Bản phát hành biên dịch với `-DNDEBUG`. Điều gì đúng?

- `dem` vẫn được gọi, chỉ có thông báo lỗi bị tắt
- Nếu `dem(f)` trả 0 thì chương trình trả mã lỗi khác 0
- Lời gọi `dem` vẫn chạy nhưng kết quả bị bỏ đi
- `dem(f)` không được gọi, nên tệp không được đọc ở bản phát hành

<p class="giai-thich" markdown>Với `-DNDEBUG`, `assert(x)` được thay bằng câu lệnh rỗng, kể cả biểu thức `x`: không đánh giá, nên mọi hiệu ứng phụ của `dem` biến mất và hai bản chạy khác nhau. Đây đúng là bẫy của `assert`. Nó không "tắt thông báo" rồi vẫn gọi; cũng không có cơ chế nào đổi sang mã thoát lỗi. Quy tắc: gọi hàm có hiệu ứng ở dòng riêng, rồi `assert` kết quả của nó.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Bạn dùng gdb và thấy `$1 = <optimized out>` khi in biến `tong`. Cách xử lý hợp lý nhất là gì?

- Cài lại gdb vì nó đọc sai thông tin gỡ lỗi
- Biên dịch lại với `-g -O0` rồi gỡ lỗi trên bản đó
- Thêm `-fsanitize=address`, vì sanitizer giữ lại mọi biến
- Biên dịch lại không có `-g`, vì `-g` làm mất biến

<p class="giai-thich" markdown>`<optimized out>` nghĩa là trình biên dịch đã bỏ hay đổi chỗ biến đó do tối ưu hóa, nên bản `-O2` không còn "biến `tong`" để gdb đọc. `-O0` giữ mỗi biến một chỗ trên stack; `-g` ghi thông tin để gdb tìm ra. gdb không sai. Sanitizer không bảo đảm giữ biến, nó chỉ chèn thêm bước kiểm tra. Bỏ `-g` thì tệ hơn: gdb mất cả tên biến lẫn dòng nguồn, trong khi `-g` không làm mất gì.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đầu ra của `nm -C` (rút gọn) cho hai tệp, rồi cho biết lệnh `g++ main.o -o prog` kết thúc ra sao.

```text
$ nm -C main.o
0000000000000000 T main
                 U tong(int, int)
$ nm -C tong.o
0000000000000000 T tong(int, int)
```

- Thành công, vì `main.o` đã có hàm `main`
- Thành công, vì `tong.o` nằm cùng thư mục
- Lỗi `undefined reference to tong(int, int)`
- Lỗi `multiple definition of main`

<p class="giai-thich" markdown>`U` ở `main.o` nghĩa là `main.o` **cần** `tong(int, int)` từ chỗ khác, và chỉ `tong.o` có nó (`T`). Lệnh chỉ đưa `main.o` cho trình liên kết, nên không ai cung cấp tên đó. Nằm cùng thư mục không có nghĩa gì: trình liên kết chỉ dùng những tệp có trong lệnh. Có `main` ở `main.o` chỉ giải quyết điểm vào chương trình, không giải quyết `tong`. `main` chỉ có một bản (ở `main.o`), nên không thể trùng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Bạn sửa `tong.h` nhưng `Makefile` chỉ ghi `%.o: %.cpp`, không ghi `tong.h`. Sau `make`, chương trình sập ở chỗ lạ. Giải thích khả dĩ nhất?

- `main.o` cũ và `tong.o` mới nhìn cùng một lớp theo hai bố cục khác nhau
- `make` quên bước liên kết, nên chương trình cũ vẫn còn
- Trình liên kết đổi nhầm tên hàm vì mangling
- Header làm `make` chạy `-O2` thay vì `-O0`

<p class="giai-thich" markdown>Không có `tong.h` trong danh sách nguồn thì `make` không biết `.o` cũ đã lỗi thời nên không biên dịch lại; một tệp có bố cục mới, tệp kia bố cục cũ, và khi ghép lại thì đọc ghi lệch vị trí thành viên, thành UB và sập ở chỗ không liên quan. Bước liên kết vẫn chạy. Mangling phụ thuộc tên và kiểu tham số của hàm, header sửa bố cục lớp không làm hỏng chuyện đó. `make` cũng không tự đổi cờ tối ưu.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Đoạn nào cho kết quả **khác nhau** giữa bản biên dịch thường và bản `-DNDEBUG`?

```text
int n = 5;
assert(n > 0);
assert(++n > 0);
std::cout << n << "\n";
```

- In `5` ở cả hai bản
- In `6` ở bản thường và `5` ở bản `-DNDEBUG`
- In `5` ở bản thường và `6` ở bản `-DNDEBUG`
- Bản thường dừng ở dòng 2 vì `n` chưa xác định

<p class="giai-thich" markdown>Bản thường chạy cả hai `assert`; `++n` ở dòng 3 tăng `n` lên 6 trước khi so sánh, nên in `6`. Bản `-DNDEBUG` xóa cả hai dòng, kể cả `++n`, nên `n` vẫn là 5. Đó là lý do không được đặt hiệu ứng phụ trong `assert`. Dòng 2 đúng (5 > 0), `n` đã được gán nên không có gì chưa xác định.</p>
</div>

</div>

## 🔑 Tóm tắt

1. g++ chạy bốn trạm: tiền xử lý (`-E`), biên dịch (`-S`), hợp ngữ (`-c`, ra `.o`), liên kết; mỗi `.cpp` được biên dịch độc lập thành một đơn vị biên dịch, nên chỉ bước liên kết mới thấy thiếu hay trùng định nghĩa.
2. `undefined reference` là tên được cần mà không ai định nghĩa (quên tệp, quên `-l`, lệch chữ ký, thân template ở `.cpp`); `multiple definition` là tên được định nghĩa ở nhiều nơi (thân hàm thường trong header): soi bằng `nm -C` (`U` cần, `T` có), `c++filt`, `ldd`, `objdump -d`, `readelf -S`, `addr2line`.
3. Gỡ lỗi dùng `-g -O0` (hay `-Og`) cùng `-Wall -Wextra`; `-g` chỉ thêm các mục `.debug_*` vào tệp, không làm chạy chậm; `-O2` xóa biến, gộp hàm, đổi thứ tự dòng nên gdb báo `<optimized out>`; đo tốc độ phải dùng bản tối ưu.
4. `assert` dừng chương trình (mã 134) ở bản gỡ lỗi và bị xóa hoàn toàn với `-DNDEBUG`, kể cả hiệu ứng phụ bên trong biểu thức; macro `LOG` với `__FILE__`, `__LINE__`, `__func__` là cách in có vị trí, tắt được khi phát hành.
5. `make` chỉ làm lại tệp cũ hơn nguồn của nó (Makefile thiếu phụ thuộc header sẽ ghép `.o` cũ với mới và gây UB); CMake sinh Makefile từ `CMakeLists.txt` với kiểu build `Debug`/`Release` (phần CMake bài này chưa được chạy thử).
