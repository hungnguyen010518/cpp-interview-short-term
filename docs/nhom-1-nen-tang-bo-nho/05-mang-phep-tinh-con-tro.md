# Bài 05 — Mảng và phép tính con trỏ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Hiểu mảng `int a[4]` là bốn phần tử `int` nằm liền nhau, và `a[i]` chính là `*(a + i)`.
    - Biết `p + 1` nhích đúng một phần tử (không phải một byte), và đi ra ngoài mảng là hành vi không xác định.
    - Biết "mảng thoái hóa thành con trỏ", bẫy `sizeof` trong tham số hàm, và đọc được chuỗi kiểu C (`const char*`) kết thúc bằng `'\0'`.

**Bạn cần biết trước:** [Bài 01](01-bo-nho-byte-dia-chi.md) (địa chỉ, `sizeof`, `std::size_t`), [Bài 03](03-con-tro-co-ban.md) (con trỏ, `*p`) và [Bài 04](04-con-tro-ham.md) (hàm có tham số, truyền theo giá trị: hàm nhận **bản sao** của đối số).

## 🧠 Câu chuyện mở đầu

Trong dãy tủ khóa của [Bài 01](01-bo-nho-byte-dia-chi.md), nhớ rằng mỗi ngăn là một byte, và một số `int` chiếm (thường) 4 ngăn liền nhau. Giờ xếp **bốn món đồ cùng loại** (bốn số `int`) nằm liền nhau: đó là một **mảng**, và mỗi món là một **phần tử**. Bạn không cần bốn tờ giấy riêng, chỉ cần **một** tờ ghi số của ngăn đầu tiên, rồi đếm "đi thêm mấy món".

Đi thêm một món nghĩa là gì phụ thuộc vào cỡ món đồ: mỗi món chiếm 4 ngăn thì đi thêm một món là nhích 4 ngăn. Đó là chuyện của **phép tính con trỏ**.

!!! info "Chỗ nào ví dụ hàng tủ không còn đúng?"
    Tờ giấy chỉ ghi ngăn đầu, nó **không ghi dãy có bao nhiêu món**. Đếm sai thì bạn mở cửa ngăn của người khác mà không hay biết (mục 4), và khi đưa tờ giấy đó cho một hàm thì số món bị mất (mục 5).

## 📖 Giải thích

### 1. Mảng: dãy phần tử liền nhau

**Mảng (array)** là một dãy các biến **cùng kiểu**, nằm **liền nhau** trong bộ nhớ. Mỗi biến trong dãy gọi là một **phần tử (element)**.

```text
int a[4] = {10, 20, 30, 40};
```

Đọc dòng này: `a` là một mảng gồm 4 phần tử kiểu `int`, được đặt giá trị ban đầu là 10, 20, 30, 40 (các giá trị nằm trong `{ }`, cách nhau bằng dấu phẩy). Con số 4 trong `[ ]` là số phần tử, và nó phải cố định. Giống `var a [4]int` trong Go.

Để lấy một phần tử, viết **chỉ số (index)** trong `[ ]`: `a[0]` là phần tử đầu, `a[3]` là phần tử cuối. Chỉ số **bắt đầu từ 0**, như Go. Mỗi `int` chiếm (thường) 4 byte, nên bốn phần tử chiếm 16 byte liền nhau (địa chỉ minh họa, máy bạn sẽ in số khác):

```text
 địa chỉ:  0x1000      0x1004      0x1008      0x100c
          +-----------+-----------+-----------+-----------+
          |    10     |    20     |    30     |    40     |
          +-----------+-----------+-----------+-----------+
  chỉ số:     a[0]        a[1]        a[2]        a[3]
```

Để đi qua từng phần tử, ta cần vòng lặp **`for`**. Dạng của nó giống Go nhưng bắt buộc có ngoặc tròn và không dùng `:=`:

```text
for (int i = 0; i < 4; i++) {
    ...                         // thân vòng lặp, chạy với i = 0, 1, 2, 3
}
```

Trong ngoặc có ba phần, cách nhau bằng `;`. Phần 1 `int i = 0` chạy một lần ở đầu. Phần 2 `i < 4` ("`i` nhỏ hơn 4", cho `true` hoặc `false`) được kiểm tra trước mỗi vòng, đúng thì chạy thân. Phần 3 `i++` chạy sau mỗi vòng, nghĩa là "tăng `i` thêm 1".

### 2. Mảng thoái hóa thành con trỏ

Có một sự thật làm mảng và con trỏ dính vào nhau. Trong một biểu thức, tên mảng `a` tự động biến thành **con trỏ tới phần tử đầu tiên** (`&a[0]`). Chuyện này gọi là **mảng thoái hóa thành con trỏ (array decay)**. Vì thế ta viết được:

```text
int* p = a;       // p đựng địa chỉ của a[0]
```

Từ đây có quy tắc quan trọng: **`p[i]` là cách viết gọn của `*(p + i)`**, và vì `a` cũng thoái hóa thành con trỏ nên `a[i]` đúng bằng `*(a + i)`. Phần `p + i` là "phép tính con trỏ": nó nhích `i` **phần tử** từ chỗ `p` đang đứng, mục 3 giải thích kỹ. Bạn đã quen `p->x` là viết gọn của `(*p).x`; đây là một viết gọn cùng loại.

!!! warning "Hay nhầm: mảng và con trỏ KHÔNG phải một thứ"
    Mảng `a` là cả bốn phần tử, 16 ngăn (nên `sizeof(a)` là 16). Con trỏ `p` chỉ là một ô đựng một địa chỉ (nên `sizeof(p)` thường là 8). Chúng dễ lẫn vì tên mảng *thoái hóa* thành con trỏ khi dùng trong biểu thức, chứ không vì chúng giống nhau.

    Quy tắc thoái hóa có ngoại lệ: `sizeof(a)` không làm `a` thoái hóa, nên nó vẫn đo cả mảng. `&a` cũng không làm `a` thoái hóa: đó là địa chỉ của **cả mảng**, không phải của phần tử đầu. Ngoại lệ của `sizeof` là nguồn của cái bẫy ở mục 5.

### 3. Phép tính con trỏ (pointer arithmetic)

Cộng một số vào con trỏ, ví dụ `p + 1`, là **phép tính con trỏ**. Nó **không** cộng 1 vào con số địa chỉ. Nó nhích sang **phần tử kế tiếp** của kiểu mà `p` trỏ tới, tức là địa chỉ tăng thêm `1 × sizeof(kiểu)` byte.

- Với `int*` (phần tử thường 4 byte): `p + 1` hơn `p` thường 4.
- Với `double*` (phần tử thường 8 byte): `p + 1` hơn `p` thường 8.

Nhờ vậy `p + 2` luôn là "phần tử thứ hai kể từ chỗ `p` đang đứng", không cần ta tự tính byte; và đó chính là lý do `p[i]` bằng `*(p + i)`.

Vài phép khác dùng được:

- `p++` nhích `p` sang phần tử kế tiếp (`p` bị đổi giá trị).
- `q - p` với hai con trỏ **cùng trỏ vào một mảng** cho ra "cách nhau bao nhiêu **phần tử**" (một số nguyên có dấu). Chuẩn C++ chỉ định nghĩa phép này khi hai con trỏ nằm trong cùng một mảng.
- `p + q` (cộng hai con trỏ) **không có nghĩa**, trình biên dịch từ chối (ví dụ 2 có thử).

Con trỏ có thể trỏ tới mọi phần tử của mảng, và thêm **một vị trí ngay sau phần tử cuối** (như `a + 4` với mảng 4 phần tử). Vị trí đó dùng để so sánh ("đã đi hết chưa?") nhưng **không được giải tham chiếu**. Đi xa hơn nữa thì ngay việc tạo ra con trỏ (như `a + 10`) đã là hành vi không xác định, dù chưa giải tham chiếu. Phép `!=` ("khác nhau", cho `true`/`false`) dùng để so hai con trỏ như vậy.

### 4. Đi ra ngoài mảng

**Đi ra ngoài mảng là hành vi không xác định (UB, [Bài 03](03-con-tro-co-ban.md)).** Ví dụ `a[4]`, `a[-1]` hay `*(p + 10)` với mảng 4 phần tử: chuẩn không hứa chuyện gì sẽ xảy ra. Có thể trông như chạy bình thường, có thể đọc hay ghi nhầm vào biến khác, có thể dừng đột ngột. Mình không chạy các dòng này:

```cpp
// bo-qua-kiem-tra
// CHỈ ĐỂ ĐỌC, mình không chạy chương trình này.
#include <iostream>

int main() {
    int a[4] = {10, 20, 30, 40};
    int* p = a;
    std::cout << a[4] << "\n";        // đọc ngoài mảng: hành vi không xác định
    a[-1] = 5;                        // ghi ngoài mảng: hành vi không xác định
    std::cout << *(p + 10) << "\n";   // cũng ngoài mảng: hành vi không xác định
    return 0;
}
```

C++ **không kiểm tra** chỉ số khi chạy (khác Go: Go dừng chương trình với `index out of range`). Giữ chỉ số trong khoảng hợp lệ là việc của bạn.

### 5. Truyền mảng vào hàm: bẫy `sizeof`

Khi truyền một mảng vào hàm, mảng thoái hóa thành con trỏ, nên hàm chỉ nhận **một địa chỉ**: địa chỉ của phần tử đầu (như mọi tham số, nó là một bản sao, [Bài 04](04-con-tro-ham.md)). Hàm không nhận số phần tử, cũng không nhận bản sao của mảng. Dù bạn viết tham số là `int a[4]`, trình biên dịch vẫn coi nó là `int*`.

Hệ quả: bên trong hàm, `sizeof(a)` chỉ là cỡ của **một con trỏ**, không phải 16. Ví dụ 3 chạy thật chuyện này, và `g++ -Wall` còn cảnh báo bạn.

Cách đúng: truyền kèm số phần tử, và đo ở nơi `a` còn là mảng thật:

```text
int tong(const int* a, std::size_t n) { ... }     // nhận địa chỉ đầu và số phần tử n
std::size_t n = sizeof(a) / sizeof(a[0]);         // ở main: 16 / 4 = 4
tong(a, n);
```

Ở đây `const` đặt trước `int*` nghĩa là "chỉ đọc, không sửa phần tử qua con trỏ này".

`std::size_t` là kiểu số không âm hợp để đếm phần tử (cần `#include <cstddef>`). Cách tốt hơn nữa nằm ở nhóm STL: `std::vector` hoặc `std::array`, những kiểu **mang theo độ dài**; ở đây ta chỉ nhắc tên.

!!! info "Bạn biết Go?"
    Slice của Go là bộ ba (con trỏ tới phần tử đầu, độ dài, sức chứa), nên độ dài luôn đi kèm. Mảng C++ khi truyền vào hàm thoái hóa thành **chỉ con trỏ** và mất độ dài, nên ta phải tự truyền `n`. Mảng Go `[4]int` thì được **chép cả bốn phần tử** khi truyền vào hàm. Go cũng **không cho** số học con trỏ như `p + 1` (trừ gói `unsafe`), còn C++ cho tự do.

### 6. Chuỗi kiểu C

Một chữ cái đơn trong C++ là kiểu `char`, viết trong nháy đơn: `'A'`. Máy lưu nó dưới dạng một số (`'A'` là 65 trên máy thông thường), và `char` chiếm 1 byte.

Một **chuỗi** là dãy `char` liền nhau, tức một mảng `char`. Chuỗi kiểu C (có từ ngôn ngữ C) **kết thúc bằng một phần tử đặc biệt `'\0'`**, ký tự có mã số 0, gọi là ký tự kết thúc.

```text
const char* ten = "An";
```

Phần `"An"` (chuỗi trong nháy kép) là **chuỗi hằng**. Nó chiếm **3** ngăn liền nhau (mỗi `char` 1 byte): `'A'`, `'n'` và `'\0'` ở cuối.

```text
  địa chỉ:    0x2000     0x2001     0x2002
             +----------+----------+----------+
             |   'A'    |   'n'    |   '\0'   |
             +----------+----------+----------+
                ^
   ten ---------+     (ten đựng địa chỉ của ký tự đầu, 0x2000)
```

`ten` là con trỏ tới ký tự đầu. Kiểu của chính `"An"` là mảng 3 `const char`, nên nó thoái hóa thành `const char*` khi gán. Chữ `const` nghĩa là các ký tự **chỉ đọc**.

Hàm đọc chuỗi không biết độ dài, nó đi từng ô cho đến khi gặp `'\0'`. `std::cout << ten` làm đúng thế. Chính quy ước này là lý do [Bài 01](01-bo-nho-byte-dia-chi.md) phải ép `char*` sang `void*` mới in được địa chỉ.

Về việc sửa: `ten[0] = 'B';` với `const char* ten` bị trình biên dịch từ chối (ví dụ 4 có thử). Nếu cố ép bỏ `const` rồi ghi vào chuỗi hằng thì là hành vi không xác định, mình không chạy.

Muốn chuỗi sửa được, tạo một **mảng** riêng chép nội dung ra: `char ban[] = "An";`. Với đa số việc thực tế, hãy dùng `std::string` ([Bài 02](02-stack-heap-static.md)): nó tự lo độ dài và việc chép.

## 💻 Ví dụ code

### Ví dụ 1: mảng, địa chỉ, `sizeof`, thoái hóa và `p[i]` ≡ `*(p + i)`

```cpp
#include <iostream>

int main() {
    int a[4] = {10, 20, 30, 40};                          // (1)
    a[1] = 25;                                            // (2)
    for (int i = 0; i < 4; i++) {                         // (3)
        std::cout << "a[" << i << "] = " << a[i] << "  dia chi " << &a[i] << "\n";
    }
    std::cout << "sizeof(a) = " << sizeof(a) << "\n";     // (4)
    std::cout << "sizeof(a[0]) = " << sizeof(a[0]) << "\n";

    int* p = a;                                           // (5)
    std::cout << std::boolalpha;
    std::cout << "p == &a[0] : " << (p == &a[0]) << "\n";
    std::cout << "p[2]       = " << p[2] << "\n";         // (6)
    std::cout << "*(p + 2)   = " << *(p + 2) << "\n";     // (7)
    std::cout << "*(a + 2)   = " << *(a + 2) << "\n";     // (8)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `int a[4] = {...};` | Xin 16 ngăn liền nhau (bốn `int`), ghi bốn số | `[10][20][30][40]` bắt đầu ở 0x1000 (địa chỉ minh họa) |
| (2) `a[1] = 25;` | Ghi đè phần tử thứ hai | `[10][25][30][40]` |
| (3) vòng `for` | `i` chạy 0..3; mỗi vòng in giá trị và **địa chỉ** của `a[i]` | địa chỉ tăng đều |
| (4) `sizeof(a)` | Cỡ của **cả mảng**; dòng sau là cỡ một phần tử | in `16` và `4` (thường) |
| (5) `int* p = a;` | `a` thoái hóa thành địa chỉ của `a[0]`; `p` chép nó | `p` ở 0x1010 = 0x1000 ---> `a[0]` |
| in `p == &a[0]` | So địa chỉ hai bên: cùng 0x1000 | in `true` |
| (6) `p[2]` | Viết gọn của `*(p + 2)` | in `30` |
| (7) `*(p + 2)` | Nhích 2 phần tử từ `p` tới 0x1008, đọc ô đó | in `30` |
| (8) `*(a + 2)` | `a` thoái hóa trong biểu thức, nên cộng được như con trỏ | in `30` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`; một lần chạy thật):

```text
a[0] = 10  dia chi 0x7ffde29f2e10
a[1] = 25  dia chi 0x7ffde29f2e14
a[2] = 30  dia chi 0x7ffde29f2e18
a[3] = 40  dia chi 0x7ffde29f2e1c
sizeof(a) = 16
sizeof(a[0]) = 4
p == &a[0] : true
p[2]       = 30
*(p + 2)   = 30
*(a + 2)   = 30
```

Số địa chỉ trên máy bạn sẽ khác và đổi theo lần chạy; chỉ **kiểu mẫu** quan trọng: các địa chỉ liên tiếp cách nhau 4 (`...10`, `...14`, `...18`, `...1c`, hệ 16) vì mỗi `int` chiếm 4 byte (thường). Chuẩn đảm bảo các phần tử nằm liền nhau; con số 4 là cỡ `int` trên máy thông thường.

**Thử thay đổi 1: in `*p + 2` thay cho `*(p + 2)`.** Mình đã chạy: nó in `12`. Dấu `*` dính vào `p` trước (`*p` là `10`) rồi mới cộng 2. Ngoặc quanh `p + 2` là bắt buộc để nhích con trỏ **trước**, giải tham chiếu **sau**.

**Thử thay đổi 2: khai báo `int a[4] = {10, 20};` (thiếu giá trị).** Mình đã chạy: hai phần tử còn lại được đặt thành `0`. Còn `int a[4] = {10, 20, 30, 40, 50};` (thừa giá trị) không biên dịch được: `error: too many initializers for ‘int [4]’`.

### Ví dụ 2: `p + 1`, `p++`, hiệu hai con trỏ, đi dọc mảng

```cpp
#include <iostream>

int main() {
    int a[4] = {10, 20, 30, 40};
    double d[2] = {1.5, 2.5};
    int* p = a;
    double* pd = d;
    std::cout << "p      = " << p << "\n";
    std::cout << "p + 1  = " << p + 1 << "\n";                   // (1)
    std::cout << "pd     = " << pd << "\n";
    std::cout << "pd + 1 = " << pd + 1 << "\n";                  // (2)

    p++;                                                         // (3)
    std::cout << "sau p++: *p = " << *p << "\n";

    int* dau = a;
    int* cuoi = a + 3;                                           // (4)
    std::cout << "cuoi - dau = " << (cuoi - dau) << "\n";        // (5)

    int tong = 0;
    for (const int* q = a; q != a + 4; q++) {                    // (6)
        tong = tong + *q;
    }
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

Dòng (6): `const int* q` là con trỏ chỉ đọc (ta chỉ cộng dồn, không sửa mảng). Vòng lặp bắt đầu từ `a`, lặp đến khi `q` bằng `a + 4`, vị trí ngay sau phần tử cuối (mục 3).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a`, `d`, `p`, `pd` | `p` trỏ `a[0]`, `pd` trỏ `d[0]` | `a` từ 0x1000, `d` từ 0x1020 (minh họa) |
| (1) `p + 1` | Nhích **một phần tử `int`** (4 byte) | in 0x1000 rồi 0x1004 |
| (2) `pd + 1` | Nhích **một phần tử `double`** (8 byte) | in 0x1020 rồi 0x1028 |
| (3) `p++` | `p` nhích sang phần tử kế tiếp, giờ trỏ `a[1]` | `p` = 0x1004; in `*p` ra `20` |
| (4) `cuoi = a + 3;` | `dau` trỏ `a[0]`, `cuoi` trỏ `a[3]` | `dau` = 0x1000, `cuoi` = 0x100c |
| (5) `cuoi - dau` | Đếm số phần tử giữa hai con trỏ (cùng một mảng) | in `3` |
| (6) vòng `for` | `q` chạy từ `a[0]` đến hết, cộng dồn 10, 20, 30, 40 | `tong` = 100 |

**Kết quả khi chạy** (một lần chạy thật):

```text
p      = 0x7ffde0044710
p + 1  = 0x7ffde0044714
pd     = 0x7ffde0044720
pd + 1 = 0x7ffde0044728
sau p++: *p = 20
cuoi - dau = 3
tong = 100
```

Số địa chỉ trên máy bạn sẽ khác; chỉ kiểu mẫu đáng nhớ: `p + 1` hơn `p` đúng 4, còn `pd + 1` hơn `pd` đúng 8. **Cùng phép `+ 1`, nhưng nhích theo cỡ phần tử.** Hiệu `cuoi - dau` cho `3` phần tử, không phải 12 byte.

**Thử thay đổi: viết `p + q` với hai con trỏ cùng mảng.** Mình đã thử, không biên dịch được:

```text
error: invalid operands of types ‘int*’ and ‘int*’ to binary ‘operator+’
```

Cộng hai địa chỉ với nhau không có nghĩa gì, nên C++ cấm. Trừ hai con trỏ vào hai mảng khác nhau thì chuẩn không định nghĩa, nên mình không chạy.

### Ví dụ 3: bẫy `sizeof` trong tham số mảng

Chương trình này **biên dịch được nhưng `g++ -Wall` cảnh báo**, nên mình đánh dấu để bộ kiểm tra không chạy nó (mình đã tự biên dịch và chạy):

```cpp
// bo-qua-kiem-tra
// Biên dịch được, nhưng có cảnh báo -Wall (xem bên dưới).
#include <iostream>

void in(int a[4]) {                                    // (1)
    std::cout << "trong ham: sizeof(a) = " << sizeof(a) << "\n";   // (2)
}

int main() {
    int a[4] = {10, 20, 30, 40};
    std::cout << "o main: sizeof(a) = " << sizeof(a) << "\n";      // (3)
    in(a);                                             // (4)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a` trong `main` | Mảng 16 byte | `[10][20][30][40]` từ 0x1000 (minh họa) |
| (3) `sizeof(a)` ở `main` | Ở đây `a` là cả mảng | in `16` (thường) |
| (4) `in(a);` | `a` thoái hóa thành địa chỉ phần tử đầu, tham số nhận số đó | tham số `a` của `in` ở 0x0f00 = 0x1000 |
| (1) | Dù viết `int a[4]`, tham số thực chất là `int*` | không đổi |
| (2) `sizeof(a)` trong hàm | Đo **con trỏ**, không đo mảng | in `8` (thường, máy 64 bit) |

**Cảnh báo thật của `g++ 11.4 -Wall`:**

```text
warning: ‘sizeof’ on array function parameter ‘a’ will return size of ‘int*’ [-Wsizeof-array-argument]
```

**Kết quả khi chạy**

```text
o main: sizeof(a) = 16
trong ham: sizeof(a) = 8
```

Cùng tên `a`, cùng viết `sizeof(a)` mà ra 16 và 8. Hai con số là cỡ thường gặp (4 byte cho `int`, 8 byte cho con trỏ trên máy 64 bit), chuẩn không ép. Điều chuẩn đảm bảo là: tham số mảng thực chất là con trỏ, nên trong hàm không có cách nào biết mảng dài bao nhiêu.

**Thử thay đổi: sửa `int a[4]` thành `int* a`.** Mình đã chạy: vẫn in `16` rồi `8`, và **không còn cảnh báo**. Hai cách viết tham số là cùng một thứ; cảnh báo chỉ nhắc rằng ta viết "dáng mảng" nhưng nhận "thân con trỏ".

### Ví dụ 4: chuỗi kiểu C

```cpp
#include <iostream>

int main() {
    const char* ten = "An";                               // (1)
    std::cout << "ten = " << ten << "\n";                 // (2)
    for (int i = 0; i < 3; i++) {
        std::cout << "ten[" << i << "] = " << static_cast<int>(ten[i]) << "\n";   // (3)
    }
    int dem = 0;
    const char* p = ten;
    while (*p != '\0') {                                  // (4)
        dem++;
        p++;
    }
    std::cout << "do dai = " << dem << "\n";
    std::cout << "sizeof(\"An\") = " << sizeof("An") << "\n";   // (5)
    char ban[] = "An";                                    // (6)
    ban[0] = 'B';
    std::cout << "ban = " << ban << "\n";
    return 0;
}
```

Hai chỗ cần giải thích. `static_cast<int>(ten[i])` ([Bài 01](01-bo-nho-byte-dia-chi.md)) ép một `char` thành số để in ra **mã số** thay vì chữ. `while (điều kiện) { ... }` lặp thân vòng lặp chừng nào điều kiện còn đúng (như `for` của Go khi chỉ có điều kiện), và `dem++` là tăng `dem` thêm 1.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `const char* ten = "An";` | Chuỗi hằng "An" gồm 3 ô: `'A'`, `'n'`, `'\0'`; `ten` giữ địa chỉ của ô đầu | `[A][n][\0]` từ 0x2000; `ten` = 0x2000 (minh họa) |
| (2) in `ten` | `std::cout` đi từ 0x2000, in từng ký tự đến khi gặp `'\0'` | in `ten = An` |
| (3) vòng `for` | In mã số của 3 ô: `'A'` là 65, `'n'` là 110, `'\0'` là 0 | in ba dòng `ten[0] = 65`, `ten[1] = 110`, `ten[2] = 0` |
| (4) vòng `while` | `p` bắt đầu ở ký tự đầu; chừng nào `*p` chưa là `'\0'`: đếm 1, nhích `p`; sau 2 vòng gặp `'\0'` thì dừng | `dem` = 2, `p` = 0x2002 |
| in `dem` | In độ dài (không tính `'\0'`) | in `do dai = 2` |
| (5) `sizeof("An")` | Cỡ của chuỗi hằng, **tính cả `'\0'`** | in `3` |
| (6) `char ban[] = "An";` | Tạo **mảng** `char` riêng, chép 3 ô vào | `ban` ở 0x1000: `[A][n][\0]` |
| `ban[0] = 'B';` | Sửa ô đầu của bản chép: hợp lệ | `[B][n][\0]` |
| in `ban` | In từ ô đầu đến `'\0'` | in `ban = Bn` |

**Kết quả khi chạy**

```text
ten = An
ten[0] = 65
ten[1] = 110
ten[2] = 0
do dai = 2
sizeof("An") = 3
ban = Bn
```

Chuỗi chữ "An" có 2 ký tự nhưng chiếm 3 ô, vì có `'\0'` đứng cuối. Mã 65 của `'A'` và 110 của `'n'` là bảng mã ASCII thông dụng (bảng gán mỗi ký tự một con số; chuẩn C++ không đảm bảo bảng mã, nhưng trên g++ thường gặp là thế).

**Thử thay đổi: thêm `ten[0] = 'B';` ngay sau dòng (1).** Mình đã thử, không biên dịch được:

```text
error: assignment of read-only location ‘* ten’
```

Vì `ten` là `const char*`, ký tự của chuỗi hằng chỉ đọc. Muốn sửa phải chép ra mảng riêng như dòng (6).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`a[i]` và `*(a + i)` quan hệ thế nào?"
    Chúng tương đương: `a[i]` được định nghĩa là `*(a + i)`. Tên mảng `a` thoái hóa thành con trỏ tới phần tử đầu, `a + i` là địa chỉ của phần tử thứ `i` (nhích `i` phần tử, không phải `i` byte), và `*` đi theo địa chỉ đó. Cũng vì vậy `p[i]` dùng được với mọi con trỏ `p`, không chỉ với tên mảng.

??? question "Array decay là gì, và `sizeof` bị ảnh hưởng ra sao?"
    Trong hầu hết biểu thức, tên mảng tự chuyển thành con trỏ tới phần tử đầu; ngoại lệ chính là `sizeof` và `&`. Khi truyền mảng vào hàm, tham số thực chất là con trỏ (dù viết `int a[4]`), nên `sizeof(a)` trong hàm cho cỡ của con trỏ (thường 8), không phải cỡ mảng (thường 16), và `g++ -Wall` cảnh báo `-Wsizeof-array-argument`. Cách xử lý: truyền kèm số phần tử, hoặc dùng `std::vector`/`std::array` (nhóm STL).

??? question "Con trỏ `p + 1` nhích bao nhiêu byte?"
    Nhích đúng `sizeof(kiểu mà p trỏ tới)` byte, tức một phần tử chứ không phải một byte. Với `int*` thường là 4 byte, với `double*` thường là 8, với `char*` là 1. Phép trừ hai con trỏ cũng tính bằng phần tử, và chuẩn chỉ định nghĩa nó khi hai con trỏ cùng một mảng.

??? question "Chuỗi kiểu C kết thúc thế nào?"
    Là mảng `char` kết thúc bằng ký tự `'\0'` (mã 0). Hàm đọc chuỗi, như `std::cout << s`, không biết độ dài: nó đi từng ký tự cho đến khi gặp `'\0'`. Nên `"An"` chiếm 3 byte, và thiếu `'\0'` thì đọc chuỗi là hành vi không xác định. Chuỗi hằng là `const char[N]`, không sửa được; trong C++ hiện đại nên ưu tiên `std::string`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Đi ra ngoài mảng"
    Mảng 4 phần tử có chỉ số 0 đến 3; `a[4]` là hành vi không xác định, và C++ không báo lỗi lúc chạy như Go. Hay gặp khi viết vòng lặp `i <= 4` thay vì `i < 4`. Quy tắc: số phần tử `n` thì chỉ số cuối là `n - 1`, và điều kiện lặp là `i < n`.

!!! warning "Lỗi 2: Dùng `sizeof` để đếm phần tử bên trong hàm"
    `sizeof(a) / sizeof(a[0])` chỉ đếm đúng ở nơi `a` còn là mảng thật. Trong hàm, `a` là con trỏ, kết quả là cỡ con trỏ chia cỡ phần tử, một con số vô nghĩa (và `-Wall` đã cảnh báo). Hãy truyền `n` vào hàm.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="05" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn code sau. Nó in ra gì?

```text
int a[4] = {10, 20, 30, 40};
int* p = a;
std::cout << *(p + 2) << "\n";
```

- `20`, vì `p + 2` là phần tử thứ hai nếu đếm từ 1
- `12`, vì `*(p + 2)` được tính như `*p + 2`
- `30`, vì `p + 2` nhích hai phần tử từ `a[0]`
- `40`, vì `p + 2` nhích hai phần tử từ `a[1]`

<p class="giai-thich" markdown>`p` trỏ tới `a[0]`, và `p + 2` nhích hai phần tử, tới `a[2]` có giá trị `30`. Chọn `20` là đếm chỉ số từ 1, trong khi chỉ số bắt đầu từ 0. Chọn `12` là bỏ qua ngoặc: ngoặc buộc phép cộng làm trước, còn `*p + 2` mới ra `12`. Chọn `40` là cho rằng `p` bắt đầu ở `a[1]`, nhưng `p` đang ở `a[0]`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Giả sử `sizeof(int)` là 4 và `int* p` đang đựng địa chỉ `0x1000`. Sau `int* q = p + 1;`, `q` đựng địa chỉ nào?

- `0x1004`, vì con trỏ nhích một phần tử `int`
- `0x1001`, vì phép cộng 1 làm địa chỉ tăng 1
- `0x1008`, vì con trỏ nhích hai lần cỡ của `int`
- `0x1010`, vì con trỏ nhích 16 byte cả mảng

<p class="giai-thich" markdown>Phép tính con trỏ nhích theo phần tử: địa chỉ tăng `1 × sizeof(int)`, tức 4, nên ra `0x1004`. Chọn `0x1001` là nhầm `p + 1` với cộng 1 vào con số địa chỉ, mà ta đã thấy ở ví dụ 2 là sai. `0x1008` sẽ là kết quả của `p + 2`, còn `0x1010` chỉ có nghĩa nếu ta nhích qua cả một mảng 16 byte, điều `p + 1` không làm.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn code sau, trên máy 64 bit thông thường (`int` 4 byte, con trỏ 8 byte). Nó in ra gì?

```text
void f(int a[10]) { std::cout << sizeof(a); }
int main() { int b[10]; std::cout << sizeof(b) << " "; f(b); }
```

- `40 40`, vì cả hai nơi đều đo mảng 10 phần tử
- `10 10`, vì `sizeof` đếm số phần tử của mảng
- `8 8`, vì mảng nào truyền qua hàm cũng thành con trỏ
- `40 8`, vì trong hàm `a` chỉ là một con trỏ

<p class="giai-thich" markdown>Ở `main`, `b` là mảng thật nên `sizeof(b)` là 10 × 4 = 40. Truyền vào hàm thì `b` thoái hóa thành con trỏ, và tham số `int a[10]` thực chất là `int*`, nên `sizeof(a)` là cỡ con trỏ, 8 (mình đã chạy: `40 8` và `g++ -Wall` cảnh báo). `40 40` là tưởng tham số còn nhớ độ dài mảng. `10 10` là nhầm `sizeof` với đếm phần tử, nó đếm byte. `8 8` sai ở `main`: ở đó `b` chưa bị thoái hóa.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn code sau. Nó in ra gì?

```text
int a[4] = {10, 20, 30, 40};
int* dau = a;
int* cuoi = a + 3;
std::cout << cuoi - dau << "\n";
```

- `12`, vì hai địa chỉ cách nhau 12 byte
- `3`, vì hiệu hai con trỏ đếm phần tử
- `30`, vì `cuoi` đang trỏ tới giá trị 30
- `2`, vì phần tử ở giữa hai con trỏ là 2

<p class="giai-thich" markdown>Hiệu hai con trỏ cùng một mảng cho ra số **phần tử** giữa chúng: `a[3]` cách `a[0]` ba phần tử, nên in `3` (mình đã chạy). Hai địa chỉ thật sự cách nhau 12 byte (thường), nhưng phép trừ chia cho cỡ phần tử nên không ra 12. `cuoi` trỏ tới `40` chứ không phải `30`, và phép trừ không đọc giá trị nào. Con số 2 là đếm số phần tử nằm giữa, còn phép trừ đếm số bước đi từ `dau` đến `cuoi`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Chuỗi kiểu C như `"An"` kết thúc bằng gì?

- Ký tự `'\0'` (mã số 0) đứng ngay sau chữ cuối
- Ký tự xuống dòng `'\n'` đứng ngay sau chữ cuối
- Một con số ghi độ dài, đặt ở đầu chuỗi
- Dấu nháy kép `"` đứng ngay sau chữ cuối

<p class="giai-thich" markdown>Chuỗi kiểu C là dãy `char` kết thúc bằng ký tự `'\0'`, nên `"An"` chiếm 3 ô và hàm nào đọc chuỗi cũng dừng khi gặp ký tự này. Xuống dòng `'\n'` chỉ là một ký tự bình thường, có thể nằm giữa chuỗi. Con số độ dài ở đầu là cách của một số ngôn ngữ khác (ví dụ chuỗi của Go giữ độ dài riêng), còn chuỗi kiểu C không có. Dấu nháy kép chỉ là cách ta viết chuỗi trong code, không nằm trong bộ nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Cho `int a[4] = {1, 2, 3, 4};`. Theo chuẩn C++, câu lệnh `a[4] = 9;` gây ra chuyện gì?

- Trình biên dịch bắt buộc phải từ chối, nên chương trình không được tạo ra
- Chương trình bắt buộc dừng lúc chạy với lỗi `index out of range`
- Mảng tự nới thêm một ô ở cuối để chứa được số `9` vừa ghi
- Chuẩn không hứa kết quả gì, đó là hành vi không xác định

<p class="giai-thich" markdown>`a[4]` nằm ngoài mảng, ngay sau phần tử cuối, và ghi vào đó là hành vi không xác định (UB): chuẩn không hứa gì, có thể chạy tiếp, ghi nhầm biến khác, hoặc dừng đột ngột. Trình biên dịch không bắt buộc phải từ chối (nhiều lúc chỉ cảnh báo, nhiều lúc không biết). C++ cũng không kiểm tra chỉ số lúc chạy như Go (Go dừng với `index out of range`). Mảng có kích thước cố định, nó không tự nới thêm ô.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Với `a` là một mảng, biểu thức `a[i]` tương đương với biểu thức nào?

- `a + i`, địa chỉ của phần tử thứ `i`
- `*(a + i)`, phần tử nằm ở địa chỉ đó
- `*a + i`, phần tử đầu rồi cộng thêm `i`
- `&a + i`, nhích `i` lần qua cả mảng

<p class="giai-thich" markdown>`a[i]` được định nghĩa là `*(a + i)`: nhích `i` phần tử từ phần tử đầu, rồi đi theo địa chỉ để lấy chính phần tử đó. `a + i` thì chỉ là địa chỉ, chưa lấy giá trị. `*a + i` lấy phần tử đầu `a[0]` rồi mới cộng `i` vào giá trị, nên là một số khác. `&a + i` nhích theo cỡ cả mảng, vì `&a` là địa chỉ của **cả mảng** (mục thoái hóa đã nói), nên mỗi bước đi hết một mảng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Cho `const char* s = "An";`. Câu lệnh `s[0] = 'B';` cho kết quả gì?

- Chuỗi đổi thành `"Bn"`, vì `s[0]` là một ô nhớ như mọi ô khác
- Chương trình biên dịch được, và chuỗi vẫn là `"An"`
- `g++` báo lỗi biên dịch, vì ký tự của chuỗi hằng chỉ đọc
- Chuỗi đổi thành `"B"`, vì ghi `'B'` cắt chuỗi ngay ô đầu

<p class="giai-thich" markdown>`s` là `const char*`, nghĩa là các ký tự mà nó trỏ tới chỉ đọc, nên `g++` từ chối với `assignment of read-only location` (mình đã thử). Nếu cố ép bỏ `const` rồi ghi thì là hành vi không xác định, không phải "sửa được". Chương trình đã không biên dịch được nên không có chuyện chuỗi vẫn là `"An"`. Chuỗi cũng không bị cắt: chỉ ký tự `'\0'` mới đánh dấu hết chuỗi, và ghi `'B'` không tạo ra `'\0'`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Mảng `int a[4]` là bốn phần tử `int` liền nhau, chỉ số từ 0; tên mảng trong biểu thức thoái hóa thành con trỏ tới phần tử đầu, nên `p[i]` bằng `*(p + i)` và `a[i]` bằng `*(a + i)`.
2. `p + 1` nhích đúng một phần tử (`sizeof(kiểu)` byte, thường 4 với `int*` và 8 với `double*`), `q - p` đếm số phần tử trong cùng một mảng, và không có `p + q`.
3. Đi ra ngoài mảng là hành vi không xác định, và C++ không tự kiểm tra chỉ số (khác Go).
4. Truyền mảng vào hàm chỉ truyền con trỏ: `sizeof` tham số trong hàm là cỡ con trỏ (thường 8) khác `sizeof` của mảng ở nơi khai báo (thường 16), nên phải truyền kèm số phần tử, hoặc dùng `std::vector`/`std::array`.
5. Chuỗi kiểu C `const char* ten = "An";` là con trỏ tới các ký tự kết thúc bằng `'\0'` (nên chiếm 3 ô), chuỗi hằng không sửa được, và trong thực tế nên dùng `std::string`.
