# Bài 03 — Con trỏ cơ bản

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Khai báo được con trỏ, lấy địa chỉ bằng `&`, giải tham chiếu bằng `*`, và sửa giá trị của một biến qua con trỏ.
    - Dùng được `nullptr`, biết vì sao con trỏ chưa khởi tạo và việc giải tham chiếu `nullptr` là nguy hiểm.
    - Dùng được `->` với struct, và đọc được hình vẽ "con trỏ trỏ tới biến" cùng bẫy `int* a, b;`.

## 🧠 Câu chuyện mở đầu

Quay lại dãy tủ khóa của [Bài 01](01-bo-nho-byte-dia-chi.md): mỗi ngăn có một số thứ tự (địa chỉ). Giả sử bạn gửi đồ ở ngăn số 12. Bạn không thể mang cả ngăn tủ theo người, nên bạn lấy một **tờ giấy** và viết lên đó: "đồ của em ở ngăn 12".

Tờ giấy đó **không phải là đồ**. Nó chỉ là một mảnh giấy ghi đường tới đồ. Ai cầm tờ giấy thì đi tới ngăn 12 và thấy đồ, hoặc thay đồ khác vào. Nếu tờ giấy bị vứt đi, đồ trong ngăn vẫn còn nguyên.

Con trỏ (**pointer**) chính là tờ giấy đó. Điều quan trọng nhất của bài: **tờ giấy cũng là một vật**. Bạn phải cất nó ở đâu đó, nên nó cũng nằm trong một ngăn nhớ riêng, có địa chỉ riêng. Chỉ khác ở chỗ thứ nó "đựng" là một địa chỉ của ngăn khác.

!!! info "Chỗ nào ví dụ tờ giấy không còn đúng?"
    Tờ giấy thật có thể ghi sai hoặc để trống. Con trỏ cũng thế: nó có thể chưa ghi gì, hoặc ghi một địa chỉ không còn đồ của bạn. Hai tình huống đó (mục 4) là chỗ sinh ra phần lớn lỗi C++ nguy hiểm.

    Còn một giới hạn nữa: một `int` chiếm nhiều ngăn liền nhau (thường 4), còn tờ giấy chỉ ghi số của ngăn **đầu tiên**. Vậy nên đọc được hết món đồ là nhờ **kiểu** của con trỏ: `int*` cho chương trình biết phải đọc 4 ngăn từ chỗ đó, `char*` thì chỉ đọc 1.

## 📖 Giải thích

### 1. Địa chỉ nằm trong một biến: con trỏ

Ở Bài 01 ta có `&x` là "địa chỉ của `x`" (số của ngăn đầu tiên `x` chiếm). Ta đã *in* địa chỉ đó ra màn hình. Bây giờ ta **cất** nó vào một biến để dùng về sau. Biến loại này gọi là **con trỏ (pointer)**:

```text
int x = 10;
int* p = &x;
```

Đọc dòng thứ hai từ trái sang phải:

- `int*` là **kiểu** của `p`, đọc là "con trỏ tới `int`". Nó có nghĩa: biến này đựng địa chỉ của một ô nhớ mà trong đó có một số `int`. Ví dụ `char*` là "con trỏ tới `char`", `double*` là "con trỏ tới `double`".
- `p` là tên biến.
- `= &x` đặt giá trị ban đầu cho `p` là địa chỉ của `x`.

Vậy sau hai dòng này, `x` đựng số `10`, còn `p` đựng **địa chỉ của `x`**. Ta nói "`p` trỏ tới `x`".

Hình vẽ hai ô nhớ (địa chỉ minh họa, máy bạn sẽ in số khác):

```text
        x                          p
  địa chỉ 0x1000             địa chỉ 0x1008
 +----------------+         +------------------+
 |       10       | <------ |      0x1000      |
 +----------------+  trỏ    +------------------+
   giá trị của x           giá trị của p = địa chỉ của x
```

Mũi tên chỉ là cách vẽ. Trong máy chỉ có con số `0x1000` nằm trong ô của `p`.

Chú ý: kiểu `int*` là kiểu **riêng**, không phải `int`. Bạn không thể viết `int* p = 20;` vì `20` là số, không phải địa chỉ. Kiểu của con trỏ cho trình biên dịch biết khi đi theo địa chỉ thì phải coi chỗ đó là loại gì (và đọc bao nhiêu byte).

### 2. Giải tham chiếu: đi theo tờ giấy

Có địa chỉ rồi, làm sao lấy đồ ra? Bạn đặt dấu `*` **trước tên con trỏ** trong một câu lệnh: `*p`. Việc này gọi là **giải tham chiếu (dereference)**, nghĩa là "đi theo địa chỉ trong `p` tới ô nhớ đó, và làm việc với thứ nằm ở đó".

- `std::cout << *p` in giá trị nằm ở ô mà `p` trỏ tới (với hình trên là `10`).
- `*p = 20;` ghi `20` vào ô đó. Vì ô đó chính là của `x`, nên **`x` đổi thành `20`**.

`*p` không phải là một bản sao của `x`. `*p` **chính là** `x` (cùng một ô nhớ), chỉ là gọi bằng đường vòng qua con trỏ.

!!! warning "Hay nhầm: dấu `*` có hai nghĩa"
    Dấu `*` xuất hiện ở hai chỗ và nghĩa khác nhau:

    - **Trong khai báo** (đứng sau tên kiểu): `int* p` nghĩa là "`p` là con trỏ tới `int`". Lúc này `*` là một phần của kiểu.
    - **Trong câu lệnh dùng** (đứng trước tên con trỏ): `*p` nghĩa là "đi theo `p` để lấy thứ nằm ở đó".

    Cách nhớ: nếu có tên kiểu (`int`, `char`...) đứng ngay trước `*`, đó là khai báo. Nếu không, đó là giải tham chiếu. Tương tự, `&x` (đặt trước tên biến, trong câu lệnh) là "địa chỉ của `x`", **ngược** với `*p`: một cái đi từ biến ra địa chỉ, một cái đi từ địa chỉ về giá trị.

    Hai dấu này còn nghĩa khác ở những chỗ khác: `a * b` là phép nhân, `a & b` là phép "và" theo từng bit, và `&` trong khai báo còn dùng để tạo tham chiếu (Bài 06). Ở bài này chỉ cần các nghĩa vừa nêu.

Hai con trỏ có thể cùng trỏ vào một biến, như hai tờ giấy cùng ghi ngăn 12. Viết `int* q = p;` là chép địa chỉ trong `p` sang `q`: bây giờ `q` cũng trỏ tới `x`, và sửa qua `*q` hay `*p` đều đổi `x`.

### 3. So sánh hai con trỏ

Hai con trỏ có thể so sánh bằng `==` ("có bằng nhau không", cho ra `true` hoặc `false`). `p == q` hỏi: "hai con trỏ có ghi **cùng một địa chỉ** không?". `p == &x` hỏi: "`p` có đang trỏ tới `x` không?".

Đừng nhầm với `*p == *r` (giả sử `r` là một con trỏ khác, trỏ tới biến `y` cũng bằng 10): cái này so **giá trị** nằm ở hai ô đó. Hai ô nhớ khác nhau hoàn toàn có thể đựng cùng số `10`, nhưng địa chỉ của chúng vẫn khác nhau.

### 4. `nullptr`: tờ giấy để trống

Có lúc bạn cần con trỏ mà **chưa biết** nó nên trỏ tới đâu. Khi đó ta gán cho nó giá trị đặc biệt **`nullptr`** (từ C++11), nghĩa là "chưa trỏ vào đâu cả". `nullptr` giống một tờ giấy để trống có chủ ý, và gần giống `nil` của Go.

```text
int* p = nullptr;
```

Muốn biết con trỏ có đang trống không, ta kiểm tra trước khi dùng. Câu lệnh `if (điều kiện) { ... } else { ... }` chạy khối đầu nếu điều kiện đúng, ngược lại chạy khối `else` (giống Go, nhưng **điều kiện phải nằm trong ngoặc tròn**). Con trỏ đặt vào điều kiện thì `nullptr` tính là "sai", con trỏ có địa chỉ tính là "đúng". Hai cách viết dưới đây là một:

```text
if (p)              // p khác nullptr
if (p != nullptr)   // viết rõ hơn, cùng ý
```

**Không bao giờ giải tham chiếu `nullptr`.** `*p` khi `p` là `nullptr` là đi theo một tờ giấy trống, và chuẩn C++ gọi đó là **hành vi không xác định (undefined behavior, viết tắt UB)**: chuẩn không hứa chuyện gì sẽ xảy ra. Có thể chương trình dừng đột ngột (trên Linux hay thấy `Segmentation fault`), có thể nó chạy tiếp ra kết quả sai, và kết quả có thể đổi giữa các máy hay các lần biên dịch. Đừng dựa vào bất cứ kết quả nào, và đừng nghĩ "luôn luôn crash":

```cpp
// bo-qua-kiem-tra
// CHỈ ĐỂ ĐỌC, mình không chạy chương trình này.
#include <iostream>

int main() {
    int* p = nullptr;
    std::cout << *p << "\n";   // hành vi không xác định
    return 0;
}
```

**Còn nguy hiểm hơn: con trỏ chưa khởi tạo.** Viết `int* p;` mà không gán gì thì `p` không phải `nullptr`, cũng không phải địa chỉ hợp lệ. Nó đựng **rác**: những bit còn sót lại của chỗ nhớ nó vừa chiếm. Giải tham chiếu nó là đi theo một tờ giấy ghi số bừa, và cũng là hành vi không xác định (mình không chạy ví dụ này, vì không có kết quả nào để khẳng định). Điểm đáng sợ: nó **không thể phân biệt** với con trỏ đúng, bạn không có cách kiểm tra `if (p)` để nhận ra. Thói quen tốt: **luôn gán giá trị ngay lúc khai báo**, hoặc `&một_biến`, hoặc `nullptr`.

Hai tên gọi cũ bạn có thể gặp trong code cũ: `NULL` (một macro, tức một chữ được thay bằng thứ khác lúc biên dịch, thường là `0`) và chính số `0`. Chúng cũng được dùng làm "con trỏ trống", nhưng đều là số, còn `nullptr` có kiểu riêng của nó (`std::nullptr_t`), nên không bị nhầm với số `0` khi chọn hàm. Từ nay hãy luôn dùng `nullptr`.

### 5. Con trỏ cũng là một biến

Con trỏ là biến, nên nó có đủ bốn thứ ở Bài 01: tên, kiểu, giá trị, địa chỉ. Hai điều khác nhau cần phân biệt:

| Viết | Là gì |
|---|---|
| `p` | **giá trị** của con trỏ: địa chỉ của thứ nó trỏ tới (bằng `&x`) |
| `*p` | thứ nằm ở địa chỉ đó (chính là `x`) |
| `&p` | địa chỉ của **chính biến `p`**: tờ giấy được cất ở ngăn nào |

Con trỏ cũng chiếm một số byte, và `sizeof(p)` cho biết số đó. Trên máy tính 64 bit thông thường nó là **8 byte**, nhưng đó là thói quen của máy, không phải điều chuẩn C++ đảm bảo. Con trỏ tới kiểu nào cũng đựng một địa chỉ, nên thường cùng cỡ: `int*`, `char*`, `double*` đều 8 byte, dù thứ mà chúng trỏ tới to nhỏ khác nhau.

### 6. Con trỏ tới `struct` và toán tử `->`

`struct` (đã gặp ở Bài 02) là một kiểu gộp nhiều trường lại. Ở đây ta dùng struct chỉ có dữ liệu, không có hàm:

```text
struct Nguoi {
    int tuoi;
    int chieuCao;
};

Nguoi a;       // biến a có hai trường: tuoi và chieuCao
a.tuoi = 30;   // dấu chấm: truy cập một trường của biến
```

Dấu `.` đặt sau tên **biến** để lấy một trường, giống Go (`a.tuoi`). Bây giờ nếu ta có **con trỏ tới** `Nguoi`:

```text
Nguoi* ai = &a;
```

thì `ai` là địa chỉ, không phải struct, nên **`ai.tuoi` là lỗi**. Phải đi theo địa chỉ trước (`*ai` là chính struct `a`), rồi mới lấy trường: `(*ai).tuoi`. Dấu ngoặc là bắt buộc, vì dấu `.` "dính" vào tên chặt hơn dấu `*`, nên `*ai.tuoi` bị hiểu thành `*(ai.tuoi)`, sai.

Viết `(*ai).tuoi` rất vụng, nên C++ có dấu tắt: **toán tử `->` (mũi tên)**:

```text
ai->tuoi    // đúng bằng (*ai).tuoi: "đi theo ai, rồi lấy trường tuoi"
```

### 7. Bẫy khai báo `int* a, b;`

Trong C++ bạn có thể khai báo nhiều biến một dòng: `int m, n;` tạo hai biến `int`. Vậy `int* a, b;` có tạo hai con trỏ không? **Không.** Dấu `*` bám vào **tên đứng sau nó**, chứ không bám vào kiểu. Dòng này thực ra là:

```text
int* a, b;     // a là int* (con trỏ);  b chỉ là int
int *a, b;     // cùng nghĩa, chỉ khác khoảng trắng
```

Muốn hai con trỏ, mỗi tên phải có `*` riêng: `int *a, *b;`. Cách an toàn nhất: mỗi biến một dòng. Ví dụ 6 bên dưới chạy thật cái bẫy này.

### 8. Một câu về `void*`

Ở Bài 01 ta đã ép địa chỉ `char` sang `void*` để in. `void*` là "con trỏ không nói rõ trỏ tới loại gì": nó đựng địa chỉ, nhưng vì không biết loại nên **không thể giải tham chiếu** thẳng. Ở bài này ta chỉ cần nhớ tên của nó.

## 💻 Ví dụ code

### Ví dụ 1: `x`, `p`, `*p`, và sửa qua con trỏ

```cpp
#include <iostream>

int main() {
    int x = 10;
    int* p = &x;                              // (1)
    std::cout << "x = " << x << "\n";
    std::cout << "*p = " << *p << "\n";       // (2)
    *p = 20;                                  // (3)
    std::cout << "x = " << x << "\n";
    int* q = p;                               // (4)
    *q = 30;                                  // (5)
    std::cout << "x = " << x << ", *p = " << *p << ", *q = " << *q << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int x = 10;` | Xin 4 ngăn cho `x`, ghi `10` | `x` ở 0x1000 = 10 (địa chỉ minh họa, máy bạn sẽ in số khác) |
| (1) `int* p = &x;` | Xin một ô cho `p`, ghi vào đó địa chỉ của `x` | `p` ở 0x1008 = 0x1000; vẽ: `p ---> x` |
| in `x` | In giá trị trong ô `x` | in `10` |
| (2) `*p` | Đi theo địa chỉ trong `p` (0x1000), đọc ô ở đó | in `10` |
| (3) `*p = 20;` | Đi theo `p`, ghi `20` vào ô ở đó, tức ô của `x` | `x` = 20; `p` vẫn = 0x1000 |
| in `x` | `x` đổi dù ta không viết `x = ...` | in `20` |
| (4) `int* q = p;` | Chép địa chỉ trong `p` sang ô của `q` | `q` ở 0x1010 = 0x1000: `p` và `q` cùng trỏ vào `x` |
| (5) `*q = 30;` | Đi theo `q`, ghi `30` vào ô của `x` | `x` = 30 |
| in cuối | `x`, `*p`, `*q` đều là cùng một ô | in `30` ba lần |

```text
     p  [ 0x1000 ] ---------+
                            |
                            v
     x  [    30    ] <------+
                            ^
                            |
     q  [ 0x1000 ] ---------+
```

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`):

```text
x = 10
*p = 10
x = 20
x = 30, *p = 30, *q = 30
```

**Thử thay đổi: ở dòng (3) viết `p = 20;` (quên dấu `*`).** Mình đã thử, chương trình không biên dịch được:

```text
error: invalid conversion from ‘int’ to ‘int*’ [-fpermissive]
```

Không có `*`, câu lệnh bảo "đặt giá trị của chính `p` là `20`", mà `p` là con trỏ (kiểu `int*`) nên chỉ nhận địa chỉ, không nhận số `int`. Trình biên dịch bắt lỗi này giúp bạn.

### Ví dụ 2: `p == &x`

```cpp
#include <iostream>

int main() {
    int x = 10;
    int y = 10;
    int* p = &x;
    int* q = &x;
    int* r = &y;
    std::cout << std::boolalpha;                         // (1)
    std::cout << "p == &x : " << (p == &x) << "\n";      // (2)
    std::cout << "p == q  : " << (p == q) << "\n";
    std::cout << "p == r  : " << (p == r) << "\n";       // (3)
    std::cout << "*p == *r: " << (*p == *r) << "\n";     // (4)
    return 0;
}
```

Dòng (1): `std::boolalpha` đẩy vào `std::cout` để từ đó nó in `true`/`false` thay vì `1`/`0`. Các phép so sánh phải đặt trong ngoặc `( )` khi nối với `<<`, nếu không trình biên dịch hiểu nhầm thứ tự.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| khai báo `x`, `y` | Hai biến `int` khác nhau, cùng đựng `10` | `x` ở 0x1000 = 10; `y` ở 0x1004 = 10 (địa chỉ minh họa) |
| khai báo `p`, `q`, `r` | `p` và `q` ghi địa chỉ của `x`; `r` ghi địa chỉ của `y` | `p` = 0x1000; `q` = 0x1000; `r` = 0x1004 |
| (2) `p == &x` | So địa chỉ trong `p` với địa chỉ của `x`: bằng nhau | in `true` |
| `p == q` | Hai tờ giấy cùng ghi 0x1000 | in `true` |
| (3) `p == r` | 0x1000 so với 0x1004: khác nhau | in `false` |
| (4) `*p == *r` | Đi theo `p` được `10`, đi theo `r` được `10`: so **giá trị**, bằng nhau | in `true` |

**Kết quả khi chạy**

```text
p == &x : true
p == q  : true
p == r  : false
*p == *r: true
```

Dòng (3) và (4) cho thấy điều cần nhớ: `x` và `y` có cùng giá trị nhưng khác địa chỉ, nên `p == r` sai mà `*p == *r` đúng. Con trỏ so địa chỉ, giải tham chiếu rồi so mới là so giá trị.

### Ví dụ 3: `nullptr` và `if (p)`

```cpp
#include <iostream>

int main() {
    int* p = nullptr;                                    // (1)
    if (p) {                                             // (2)
        std::cout << "p tro vao dau do\n";
    } else {
        std::cout << "p la nullptr\n";
    }
    std::cout << "p = " << p << "\n";                    // (3)

    int x = 7;
    p = &x;                                              // (4)
    if (p != nullptr) {                                  // (5)
        std::cout << "p tro toi x, *p = " << *p << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `int* p = nullptr;` | `p` ra đời và được ghi giá trị "trống" | `p` ở 0x1008 = (trống), không trỏ đi đâu |
| (2) `if (p)` | `p` là `nullptr` nên điều kiện sai, chạy nhánh `else` | in `p la nullptr` |
| (3) in `p` | In **giá trị** của `p` (không giải tham chiếu, nên hợp lệ) | in `0` (g++ 11.4) |
| `int x = 7;` | Tạo `x` | `x` ở 0x1000 = 7 |
| (4) `p = &x;` | Gán lại: `p` giờ ghi địa chỉ của `x` | `p` = 0x1000 ---> `x` |
| (5) `p != nullptr` | `p` không còn trống, điều kiện đúng; chỉ lúc này mới dám viết `*p` | in `p tro toi x, *p = 7` |

**Kết quả khi chạy**

```text
p la nullptr
p = 0
p tro toi x, *p = 7
```

Dòng (3) in `0` với `g++ 11.4`. In một con trỏ null là việc hợp lệ (không giải tham chiếu gì cả), nhưng chữ cụ thể được in ra do trình cài đặt quyết định, nên đừng dựa vào nó. Ta chỉ in giá trị của con trỏ, còn việc cấm là **giải tham chiếu** (`*p`) khi `p` trống. Cũng thấy rõ thứ tự an toàn: **kiểm tra trước, dùng `*p` sau**.

**Thử thay đổi: viết `int* p = 0;` thay cho `nullptr`.** Mình đã chạy: nó vẫn biên dịch sạch và in đúng như trên. Số `0` viết trực tiếp cũng được chấp nhận làm "con trỏ trống". Nhưng như đã nói ở mục 4, `nullptr` rõ nghĩa hơn và có kiểu riêng, nên hãy dùng nó.

### Ví dụ 4: Con trỏ cũng có kích thước và địa chỉ riêng

```cpp
#include <iostream>

int main() {
    int x = 10;
    int* p = &x;
    std::cout << "sizeof(x) = " << sizeof(x) << "\n";    // (1)
    std::cout << "sizeof(p) = " << sizeof(p) << "\n";    // (2)
    std::cout << "&x = " << &x << "\n";                  // (3)
    std::cout << "p  = " << p << "\n";                   // (4)
    std::cout << "&p = " << &p << "\n";                  // (5)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int x`, `int* p` | `x` chiếm 4 ngăn, `p` chiếm ô riêng (thường 8 ngăn) | `x` ở 0x1000 = 10; `p` ở 0x1008 = 0x1000 (minh họa) |
| (1) `sizeof(x)` | Số byte của `x` | in `4` (thường) |
| (2) `sizeof(p)` | Số byte của **con trỏ**, không phải của thứ nó trỏ tới | in `8` (thường, trên máy 64 bit) |
| (3) `&x` | Địa chỉ của `x` | in 0x1000 (minh họa) |
| (4) `p` | **Giá trị** của `p`: đúng là địa chỉ của `x` | in 0x1000, **trùng** với dòng (3) |
| (5) `&p` | Địa chỉ của **chính `p`**: tờ giấy nằm ở ngăn nào | in 0x1008, **khác** (3) và (4) |

**Kết quả khi chạy** (một lần chạy thật trên máy mình):

```text
sizeof(x) = 4
sizeof(p) = 8
&x = 0x7ffe7c1c510c
p  = 0x7ffe7c1c510c
&p = 0x7ffe7c1c5110
```

Số địa chỉ trên máy bạn sẽ khác và đổi cả giữa các lần chạy, chỉ **kiểu mẫu** đáng nhớ: dòng `&x` và dòng `p` in **cùng một số** (vì `p` đựng địa chỉ của `x`), còn `&p` là một số khác (vì `p` là biến thứ hai, nằm ở ô khác). Trong lần chạy này `&p` hơn `&x` đúng 4, nhưng chuẩn không đảm bảo thứ tự xếp các biến.

**Thử thay đổi: đổi `int* p` thành `double* p` và `char* q`.** Mình đã chạy một chương trình in `sizeof(double*)`, `sizeof(char*)` và `sizeof(int*)`: cả ba cùng là `8` trên máy mình. Con trỏ chỉ đựng một địa chỉ, nên cỡ của nó không phụ thuộc kiểu thứ nó trỏ tới (thường thôi, chuẩn không ép mọi con trỏ cùng cỡ).

### Ví dụ 5: Con trỏ tới struct và `->`

```cpp
#include <iostream>

struct Nguoi {
    int tuoi;
    int chieuCao;
};

int main() {
    Nguoi a;                                  // (1)
    a.tuoi = 30;                              // (2)
    a.chieuCao = 170;
    Nguoi* ai = &a;                           // (3)
    std::cout << "ai->tuoi = " << ai->tuoi << "\n";           // (4)
    std::cout << "(*ai).tuoi = " << (*ai).tuoi << "\n";       // (5)
    ai->tuoi = 31;                            // (6)
    std::cout << "a.tuoi = " << a.tuoi << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `Nguoi a;` | Tạo biến `a` gồm hai trường `int` liền nhau (chưa có giá trị) | `a` ở 0x1000: `[tuoi ?][chieuCao ?]` (minh họa) |
| (2) `a.tuoi = 30;` và dòng sau | Dấu `.` lấy từng trường của **biến** `a` để ghi | `[tuoi 30][chieuCao 170]` |
| (3) `Nguoi* ai = &a;` | `ai` đựng địa chỉ của cả `a` (ngăn đầu tiên của nó) | `ai` ở 0x1010 = 0x1000 ---> `a` |
| (4) `ai->tuoi` | Đi theo `ai` tới `a`, rồi lấy trường `tuoi` | in `30` |
| (5) `(*ai).tuoi` | Cách viết dài của cùng việc đó | in `30` |
| (6) `ai->tuoi = 31;` | Đi theo `ai`, ghi `31` vào trường `tuoi` của `a` | `[tuoi 31][chieuCao 170]` |
| in `a.tuoi` | Đọc trực tiếp bằng tên biến | in `31` |

**Kết quả khi chạy**

```text
ai->tuoi = 30
(*ai).tuoi = 30
a.tuoi = 31
```

**Thử thay đổi 1: viết `ai.tuoi` (dùng dấu chấm với con trỏ).** Mình đã thử, `g++` không cho biên dịch và còn gợi ý đúng:

```text
error: request for member ‘tuoi’ in ‘ai’, which is of pointer type ‘Nguoi*’ (maybe you meant to use ‘->’ ?)
```

**Thử thay đổi 2: viết `*ai.tuoi` (bỏ dấu ngoặc).** Mình đã thử, ra lỗi cùng loại (`request for member ‘tuoi’ in ‘ai’, which is of pointer type`): trình biên dịch gom `ai.tuoi` trước, mà `ai` là con trỏ nên không có trường nào để lấy. Đó là lý do cần `(*ai).tuoi` hoặc `ai->tuoi`.

!!! info "Bạn biết Go?"
    Phần lớn khái niệm bạn đã biết: Go cũng có `*int` (kiểu "con trỏ tới int"), `&x` (địa chỉ của `x`), `*p` (giải tham chiếu) và `nil` ứng với `nullptr` của C++. Hình vẽ hai ô `x` và `p` ở trên đúng y như vậy trong Go.

    Ba điểm khác:

    - Với con trỏ tới struct, Go cho viết `p.field` và **tự giải tham chiếu giùm bạn**. C++ không làm vậy: `ai.tuoi` là lỗi, phải viết `ai->tuoi`.
    - Go **không có phép tính trên con trỏ** (không "cộng 1 vào con trỏ để sang ô kế"). C++ có, ta sẽ học ở Bài 05.
    - Go có bộ thu gom rác (garbage collector): chỗ nhớ nào không ai trỏ tới nữa thì Go tự dọn. C++ không có, nên con trỏ trỏ tới thứ đã chết hoặc chưa tồn tại là rủi ro thật. Go khi gặp `nil` mà bạn giải tham chiếu thì báo lỗi ngay (panic) theo cách xác định; C++ giải tham chiếu `nullptr` là hành vi không xác định.

### Ví dụ 6: Chạy thật bẫy `int* a, b;`

```cpp
#include <iostream>

int main() {
    int x = 5;
    int* a, b;                                           // (1)
    a = &x;                                              // (2)
    b = 7;                                               // (3)
    std::cout << "sizeof(a) = " << sizeof(a) << "\n";
    std::cout << "sizeof(b) = " << sizeof(b) << "\n";
    std::cout << "*a = " << *a << ", b = " << b << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int x = 5;` | Tạo `x` | `x` ở 0x1000 = 5 (minh họa) |
| (1) `int* a, b;` | Tạo **hai** biến khác loại: `a` là `int*`, `b` chỉ là `int` | `a` ở 0x1008 (8 ngăn, chưa có giá trị); `b` ở 0x1010 (4 ngăn, chưa có giá trị) |
| (2) `a = &x;` | Gán địa chỉ của `x` cho `a`: hợp lệ | `a` = 0x1000 ---> `x` |
| (3) `b = 7;` | `b` là `int` nên nhận số `7` bình thường | `b` = 7 |
| in | `sizeof(a)` là cỡ con trỏ, `sizeof(b)` là cỡ `int` | in `8` và `4` (thường) |

**Kết quả khi chạy**

```text
sizeof(a) = 8
sizeof(b) = 4
*a = 5, b = 7
```

Bằng chứng nằm ở hai dòng `sizeof`: `a` là 8 byte (con trỏ), `b` là 4 byte (`int`). Nếu `b` cũng là con trỏ thì phải in `8`.

**Thử thay đổi 1: gán địa chỉ cho `b`, tức viết `b = &x;`** (với `int* a, b;` giữ nguyên). Mình đã thử, `g++` báo lỗi biên dịch:

```text
error: invalid conversion from ‘int*’ to ‘int’ [-fpermissive]
```

Lỗi này cho thấy rõ `b` không phải con trỏ: nó là `int`, không nhận địa chỉ.

**Thử thay đổi 2: sửa thành `int *a, *b;`** rồi gán `a = &x; b = &x;` và in `*a`, `*b`. Mình đã chạy, nó biên dịch sạch và in `5 5`: lúc này cả hai đều là con trỏ.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Con trỏ là gì?"
    Con trỏ là một biến mà giá trị của nó là một địa chỉ bộ nhớ, thường là địa chỉ của một biến khác. Kiểu của con trỏ (ví dụ `int*`) cho biết thứ nằm ở địa chỉ đó thuộc loại gì. Bản thân con trỏ cũng là một biến, có địa chỉ và kích thước riêng.

??? question "`*p` và `&x` khác nhau thế nào?"
    `&x` là toán tử lấy địa chỉ: cho ra địa chỉ của biến `x`. `*p` là toán tử giải tham chiếu: đi theo địa chỉ đang nằm trong `p` và cho ra chính đối tượng ở đó, nên có thể đọc hoặc ghi. Hai toán tử ngược chiều nhau: nếu `p = &x` thì `*p` chính là `x`. (Dấu `*` trong khai báo `int* p` thì là một phần của kiểu, không phải toán tử.)

??? question "`nullptr`, `NULL` và `0` khác nhau thế nào?"
    Cả ba đều có thể dùng làm "con trỏ trống", nhưng `nullptr` (C++11) có kiểu riêng là `std::nullptr_t`, còn `NULL` là một macro mà giá trị do cài đặt quyết định (thường là một số nguyên `0`) và `0` là số `int`. Vì vậy với hai hàm nạp chồng `f(int)` và `f(char*)`, `f(nullptr)` luôn chọn `f(char*)`. Mình thử `f(NULL)` với `g++ 11.4` thì báo "ambiguous" (mơ hồ giữa hai hàm). Nên dùng `nullptr`.

??? question "Con trỏ chưa khởi tạo khác con trỏ null thế nào?"
    Con trỏ null (`nullptr`) có giá trị xác định và nhận biết được: ta có thể kiểm tra `if (p)` trước khi dùng. Con trỏ chưa khởi tạo mang giá trị rác tùy ý, trông như một địa chỉ bình thường nên không có cách kiểm tra đáng tin; giải tham chiếu nó là hành vi không xác định. Vì vậy luôn khởi tạo con trỏ ngay khi khai báo, bằng địa chỉ hợp lệ hoặc `nullptr`.

??? question "Toán tử `->` là gì?"
    Với `p` là con trỏ tới struct (hoặc class), `p->member` là cách viết gọn của `(*p).member`: giải tham chiếu `p` rồi truy cập thành viên. Dấu ngoặc trong cách viết dài là bắt buộc vì `.` có độ ưu tiên cao hơn `*`. Không có `->` thì phải viết dài như vậy; còn viết `p.member` với `p` là con trỏ là lỗi biên dịch.

??? question "Kích thước của một con trỏ là bao nhiêu?"
    Không có số cố định do chuẩn quy định, nó phụ thuộc nền tảng. Trên máy 64 bit thông thường `sizeof(p)` là 8 byte, trên hệ 32 bit là 4 byte. Thường mọi con trỏ dữ liệu cùng cỡ, bất kể kiểu nó trỏ tới (`sizeof(char*)` bằng `sizeof(int*)`), vì chúng chỉ đựng một địa chỉ.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Giải tham chiếu `nullptr` hoặc con trỏ chưa khởi tạo"
    `*p` khi `p` là `nullptr`, hoặc khi `p` chưa được gán gì, là hành vi không xác định. Đừng tin rằng nó "luôn crash": có lúc chương trình chạy tiếp ra kết quả sai và khó tìm. Cách phòng: gán giá trị ngay lúc khai báo, và kiểm tra `if (p)` trước khi dùng `*p` nếu con trỏ có thể trống. Phần UB nói kỹ hơn ở Bài 13.

!!! warning "Lỗi 2: `int* a, b;` tưởng là hai con trỏ"
    Dấu `*` bám vào tên đứng sau nó, nên chỉ `a` là con trỏ còn `b` là `int` (mình đã chạy ở ví dụ 6). Viết `int *a, *b;` hoặc, an toàn hơn, mỗi biến một dòng.

!!! warning "Lỗi 3: Dùng `.` thay vì `->` với con trỏ tới struct"
    Trong Go `p.field` luôn dùng được. Trong C++ nếu `p` là con trỏ thì `p.field` là lỗi biên dịch, `g++` còn gợi ý "maybe you meant to use ‘->’". Viết `p->field`.

!!! warning "Lỗi 4: Nhầm `p` với `*p`"
    `p = 20;` là lỗi biên dịch (đổi chính con trỏ thành số), `*p = 20;` mới là ghi `20` vào chỗ nó trỏ tới. Và `p == q` so địa chỉ, còn `*p == *q` so giá trị. Khi đọc code, luôn tự hỏi: "ở đây là địa chỉ hay giá trị?".

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="03" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Một biến kiểu `int*` đựng thứ gì?

- Một bản sao giá trị `int` của biến mà nó trỏ tới
- Tên của biến `int` mà nó trỏ tới, ghi dưới dạng chữ
- Địa chỉ của một ô nhớ chứa một số `int`
- Số byte của ô nhớ `int` mà nó trỏ tới

<p class="giai-thich" markdown>Con trỏ đựng một địa chỉ, như tờ giấy ghi số ngăn tủ chứ không phải món đồ trong ngăn. Nó không giữ bản sao của giá trị `int`: nếu giữ bản sao thì sửa qua con trỏ sẽ không đổi được biến gốc. Tên biến chỉ là cách ta gọi trong code, máy không lưu nó trong con trỏ. Số byte thì phải hỏi bằng `sizeof`, và đó là thông tin khác hẳn địa chỉ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Với `p` là một con trỏ có địa chỉ hợp lệ, biểu thức `*p` làm gì?

- Đi theo địa chỉ trong `p` để đọc hoặc ghi ô đó
- Lấy địa chỉ của chính biến `p`, giống như `&p` vậy
- Tạo ra một con trỏ mới trỏ tới chính con trỏ `p`
- Xóa luôn ô nhớ mà `p` đang trỏ tới, giải phóng nó

<p class="giai-thich" markdown>`*p` là giải tham chiếu: đi theo địa chỉ để làm việc với chính ô nhớ đó, nên có thể đọc giá trị hoặc ghi giá trị vào. Địa chỉ của chính `p` là `&p`, một toán tử ngược chiều. `*p` không tạo con trỏ nào cả, và cũng không xóa gì: việc xóa ô nhớ ở heap phải dùng `delete`, còn `*p` chỉ chạm tới ô nhớ rồi để nguyên nó ở đó.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn code sau. Nó in ra gì?

```text
int x = 1;
int* p = &x;
*p = 5;
std::cout << x << "\n";
```

- `1`, vì `x` chỉ được đặt giá trị ở dòng đầu tiên
- Một địa chỉ dạng `0x…`, vì `p` đựng địa chỉ của `x`
- Lỗi biên dịch, vì không được gán giá trị cho `*p`
- `5`, vì `*p` chính là ô nhớ của `x`

<p class="giai-thich" markdown>`p` trỏ tới `x`, nên `*p = 5;` ghi `5` đúng vào ô nhớ của `x`, và in `x` ra `5`. Số `1` sẽ đúng nếu `*p` là một bản sao của `x`, nhưng nó là chính `x`. Chương trình in `x` chứ không in `p`, nên không có địa chỉ nào hiện ra. Gán cho `*p` là hợp lệ và là cách chính để sửa một biến qua con trỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Sau khai báo `int* a, b;`, kiểu của `b` là gì?

- `int*`, vì dấu `*` đứng sau chữ `int` áp dụng cho cả hai tên
- `int`, vì dấu `*` chỉ bám vào tên `a` đứng ngay sau nó
- `int**`, vì `b` đứng sau dấu phẩy nên cộng thêm một cấp
- Không có kiểu nào, vì dòng này là lỗi biên dịch

<p class="giai-thich" markdown>Trong khai báo, dấu `*` bám vào tên đứng sau nó, nên `a` là `int*` còn `b` chỉ là `int` (mình đã chạy: `sizeof(a)` là 8 còn `sizeof(b)` là 4). Cách nghĩ "`*` thuộc về kiểu `int` rồi áp dụng cho cả dòng" nghe hợp lý nhưng sai. Dấu phẩy không thêm cấp con trỏ nào. Dòng này biên dịch được, lỗi chỉ xuất hiện về sau nếu bạn gán địa chỉ cho `b`. Muốn hai con trỏ phải viết `int *a, *b;`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** `int* p = nullptr;` có nghĩa là gì?

- `p` trỏ tới ô nhớ số 0, và ta được phép ghi vào đó
- `p` trỏ tới một số `int` có giá trị bằng 0
- `p` đã trỏ tới một ô nhớ vừa bị `delete`
- `p` hiện chưa trỏ tới ô nhớ hợp lệ nào cả

<p class="giai-thich" markdown>`nullptr` là giá trị "chưa trỏ vào đâu", tờ giấy được cố ý để trống, và ta kiểm tra được bằng `if (p)`. Nó không phải địa chỉ của một số `int` bằng 0, vì không có ô nhớ nào được trỏ tới. Cũng không được ghi vào "ô số 0": giải tham chiếu `nullptr` là hành vi không xác định. Con trỏ trỏ vào chỗ đã `delete` là chuyện khác (gọi là con trỏ treo: con trỏ vẫn giữ địa chỉ của một chỗ đã bị trả mất rồi), nó vẫn đựng một địa chỉ cũ chứ không trống.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Cho `struct Nguoi { int tuoi; };` và `Nguoi* ai = &a;`. Cách viết nào tương đương với `ai->tuoi`?

- `(&ai).tuoi`
- `*(ai.tuoi)`
- `(*ai).tuoi`
- `&(*ai.tuoi)`

<p class="giai-thich" markdown>`ai->tuoi` là cách viết gọn của `(*ai).tuoi`: giải tham chiếu `ai` để ra struct, rồi lấy trường `tuoi`. Ba cách còn lại mình đều đã thử biên dịch và đều lỗi. `(&ai).tuoi` nghe giống nhưng `&ai` là địa chỉ của chính con trỏ (kiểu `Nguoi**`), không phải struct. `*(ai.tuoi)` và `&(*ai.tuoi)` đều bắt đầu bằng `ai.tuoi`, mà dấu `.` được tính trước dấu `*`, nên chúng đòi lấy trường từ con trỏ `ai`, điều không làm được.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Với `int* p = nullptr;`, câu lệnh `*p = 1;` gây ra điều gì?

- Chuẩn quy định chương trình phải dừng với `Segmentation fault`
- Chuẩn không hứa kết quả nào, chuyện gì cũng có thể xảy ra
- Chuẩn không hứa gì thêm, nhưng `p` sẽ tự có ô nhớ mới
- Chuẩn quy định đó là lỗi ném ra, bắt được bằng `try`/`catch`

<p class="giai-thich" markdown>Giải tham chiếu `nullptr` là hành vi không xác định: chuẩn không hứa kết quả, nên có thể crash, có thể chạy tiếp sai, và còn tùy máy hay cách biên dịch. Việc "thường thấy crash trên Linux" không phải điều chuẩn quy định, nên không thể khẳng định chương trình phải dừng. C++ không tự cấp ô nhớ cho con trỏ trống. Nó cũng không biến việc này thành lỗi ngoại lệ để bắt bằng `try`/`catch`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 8.** Đọc đoạn code sau. Nó in ra gì?

```text
int a = 1;
int b = 2;
int* p = &a;
p = &b;
*p = 9;
std::cout << a << " " << b << "\n";
```

- `1 9`, vì `p` đã được đổi sang trỏ vào `b`
- `9 2`, vì `p` được khai báo trỏ vào `a` ngay từ đầu
- `9 9`, vì cả hai biến cùng được ghi qua con trỏ `p`
- `1 2`, vì ghi qua `*p` thì không đổi biến nào cả

<p class="giai-thich" markdown>Dòng `p = &b;` đổi địa chỉ trong `p` từ `a` sang `b`, nên `*p = 9;` ghi vào `b`, còn `a` vẫn là `1`, kết quả `1 9`. Chọn `9 2` là nhớ giá trị ban đầu của `p` mà quên rằng nó đã bị gán lại. `a` và `b` là hai ô riêng, một lần ghi chỉ đổi một ô. Và ghi qua `*p` thật sự đổi biến mà `p` đang trỏ tới, không phải một bản sao.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Con trỏ là một biến đựng địa chỉ: `int* p = &x;` nghĩa là `p` trỏ tới `x`; bản thân `p` cũng nằm ở một ô nhớ riêng, thường 8 byte trên máy 64 bit.
2. `&x` là địa chỉ của `x`; `*p` đi theo địa chỉ để đọc hoặc ghi giá trị, nên `*p = 20;` đổi `x`; dấu `*` trong khai báo (`int* p`) khác dấu `*` trong câu lệnh (`*p`).
3. `nullptr` nghĩa là "chưa trỏ vào đâu"; kiểm tra bằng `if (p)`, và giải tham chiếu `nullptr` hay con trỏ chưa khởi tạo là hành vi không xác định, không phải "luôn crash".
4. Với con trỏ tới struct, `p->tuoi` bằng `(*p).tuoi`; viết `p.tuoi` với con trỏ là lỗi biên dịch (khác Go).
5. `int* a, b;` chỉ làm `a` là con trỏ còn `b` là `int`; muốn hai con trỏ viết `int *a, *b;`; `void*` là con trỏ không rõ loại, ta mới biết tên.
