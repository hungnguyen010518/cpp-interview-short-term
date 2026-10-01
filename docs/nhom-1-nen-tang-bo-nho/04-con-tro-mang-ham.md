# Bài 04 — Con trỏ với hàm, mảng và phép tính con trỏ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được hàm sửa biến của nơi gọi bằng con trỏ (`void tang(int* x)`), và phân biệt được với truyền theo giá trị (hàm chỉ sửa bản sao).
    - Hiểu mảng `int a[4]` là bốn ngăn liền nhau, và `a[i]` chính là `*(a + i)`; biết `p + 1` nhích đúng một phần tử, không phải một byte.
    - Biết "mảng thoái hóa thành con trỏ", bẫy `sizeof` trong tham số hàm, và đọc được chuỗi kiểu C (`const char*`) kết thúc bằng `'\0'`.

## 🧠 Câu chuyện mở đầu

Bạn có một bài làm viết tay và nhờ một người bạn sửa lỗi. Có hai cách đưa bài cho bạn.

**Cách 1: gửi bản photo.** Bạn ấy sửa thoải mái trên bản photo, nhưng bài gốc của bạn không đổi một nét. Đây là **truyền theo giá trị (pass by value)**: hàm nhận một **bản sao**.

**Cách 2: đưa số phòng** nơi bài gốc đang nằm (tờ giấy ghi địa chỉ của [Bài 03](03-con-tro-co-ban.md)). Bạn ấy đến đúng phòng đó, sửa trực tiếp lên bài gốc. Đây là **truyền con trỏ**.

Phần còn lại của bài là hệ quả của hai cách đó. Một **mảng** là một dãy ngăn tủ nằm **liền nhau** (như hàng tủ khóa ở [Bài 01](01-bo-nho-byte-dia-chi.md)). Để đi dọc dãy ấy, ta chỉ cần số của ngăn đầu và một con số đếm "đi bao nhiêu ngăn".

!!! info "Chỗ nào ví dụ photo và số phòng không còn đúng?"
    Số phòng có thể sai hoặc phòng đã bị dọn, và khi đó người bạn đến sửa một chỗ không phải bài của bạn (chủ đề của Bài 13). Ngoài ra, hàm luôn nhận **bản sao của tờ giấy** ghi số phòng: bạn ấy có thể vẽ nguệch ngoạc lên tờ giấy của mình mà tờ giấy của bạn không đổi. Mục 7 sẽ cho thấy điều này gây ra chuyện gì.

## 📖 Giải thích

### 1. Hàm có tham số, và truyền theo giá trị

Đến giờ ta chỉ viết một hàm: `main`. Bây giờ ta viết thêm hàm của mình. Hình dạng của nó:

```text
void tang(int x) {
    x = x + 1;
}
```

- `void` đứng đầu nghĩa là "hàm này không trả về gì" (khác `int main`, trả về một số `int`).
- `tang` là tên hàm.
- `(int x)` là **tham số (parameter)**: một biến riêng của hàm, nhận giá trị lúc gọi. Kiểu viết **trước** tên (`int x`), ngược với Go (`x int`).
- Hàm phải được viết **phía trên** chỗ gọi nó, vì trình biên dịch đọc file từ trên xuống.

Để gọi hàm, viết tên và đặt giá trị truyền vào trong ngoặc: `tang(a);`. Giá trị truyền vào gọi là **đối số (argument)**.

Điều quan trọng: tham số `x` là **một biến mới**, nằm trong khung stack của riêng lần gọi này (khung gọi hàm, Bài 02). Lúc gọi, C++ **chép giá trị** của `a` vào `x`. Hàm sửa `x` thì chỉ sửa bản photo, còn `a` ở nơi gọi vẫn như cũ. Đó là truyền theo giá trị, cách mặc định của C++.

!!! info "Bạn biết Go?"
    Go cũng truyền theo giá trị, `func tang(x int)` cho đúng kết quả y hệt. Khác biệt đáng nhớ nằm ở mục 6: khi truyền cả **mảng** vào hàm, Go chép toàn bộ mảng, còn C++ chỉ chép một địa chỉ.

### 2. Truyền con trỏ để sửa bản gốc

Muốn hàm sửa được biến của nơi gọi, ta đưa **số phòng** thay vì bản photo: tham số có kiểu con trỏ, và nơi gọi truyền địa chỉ bằng `&` (cả hai đã học ở Bài 03).

```text
void tang(int* x) {     // x là con trỏ tới int
    *x = *x + 1;        // đi theo x, đọc ô đó, cộng 1, ghi lại vào đúng ô đó
}
...
tang(&a);               // đưa địa chỉ của a
```

Bên trong hàm, `x` vẫn là một biến mới (bản sao của tờ giấy), nhưng tờ giấy chép lại **ghi cùng một số phòng**. Nên `*x` chính là `a`. Hàm không cần biết `a` tên gì ở nơi gọi.

Con trỏ có thể là `nullptr` (Bài 03), mà đi theo `nullptr` là hành vi không xác định. Vì vậy hàm nhận con trỏ nên kiểm tra trước: `if (x == nullptr) { return; }`. Dòng `return;` (không kèm giá trị) thoát khỏi hàm `void` ngay lập tức.

Ví dụ kinh điển là hàm **đổi chỗ (swap)** hai biến: không thể viết được bằng truyền theo giá trị, vì hàm chỉ đổi chỗ hai bản photo. Với con trỏ thì được, và ví dụ 2 bên dưới làm đúng việc này.

### 3. Mảng: dãy ngăn liền nhau

**Mảng (array)** là một dãy các biến **cùng kiểu**, nằm **liền nhau** trong bộ nhớ. Mỗi biến trong dãy gọi là một **phần tử (element)**.

```text
int a[4] = {10, 20, 30, 40};
```

Đọc dòng này: `a` là một mảng gồm 4 phần tử kiểu `int`, được đặt giá trị ban đầu là 10, 20, 30, 40 (các giá trị nằm trong `{ }`, cách nhau bằng dấu phẩy). Con số 4 trong `[ ]` là số phần tử, và nó phải cố định. Giống `var a [4]int` trong Go.

Để lấy một phần tử, viết **chỉ số (index)** trong `[ ]`: `a[0]` là phần tử đầu, `a[3]` là phần tử cuối. Chỉ số **bắt đầu từ 0**, như Go. Mảng 4 phần tử thì chỉ số hợp lệ là 0, 1, 2, 3; ta quay lại chuyện vượt quá ở mục 5.

Mỗi `int` chiếm (thường) 4 byte, nên bốn phần tử chiếm 16 byte liền nhau (địa chỉ minh họa, máy bạn sẽ in số khác):

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

Trong ngoặc có ba phần, cách nhau bằng `;`. Phần 1 `int i = 0` chạy một lần ở đầu. Phần 2 `i < 4` được kiểm tra trước mỗi vòng, đúng thì chạy thân. Phần 3 `i++` chạy sau mỗi vòng, nghĩa là "tăng `i` thêm 1".

### 4. Mảng thoái hóa thành con trỏ

Có một sự thật làm mảng và con trỏ dính vào nhau. Trong một biểu thức, tên mảng `a` tự động biến thành **con trỏ tới phần tử đầu tiên** (`&a[0]`). Chuyện này gọi là **mảng thoái hóa thành con trỏ (array decay)**. Vì thế ta viết được:

```text
int* p = a;       // p đựng địa chỉ của a[0]
```

Từ đây có quy tắc quan trọng: **`p[i]` là cách viết gọn của `*(p + i)`**, và vì `a` cũng thoái hóa thành con trỏ nên `a[i]` đúng bằng `*(a + i)`. Phần `p + i` là "phép tính con trỏ", mục sau sẽ giải thích. Bạn đã quen `p->x` là viết gọn của `(*p).x`; đây là một viết gọn cùng loại.

!!! warning "Hay nhầm: mảng và con trỏ KHÔNG phải một thứ"
    Mảng `a` là cả bốn ngăn (nên `sizeof(a)` là 16). Con trỏ `p` chỉ là một ô đựng một địa chỉ (nên `sizeof(p)` thường là 8). Chúng dễ lẫn vì tên mảng *thoái hóa* thành con trỏ khi dùng trong biểu thức, chứ không vì chúng giống nhau.

    Quy tắc thoái hóa có ngoại lệ: chính `sizeof(a)` không làm `a` thoái hóa, nên nó vẫn đo cả mảng (ví dụ 3). Ngoại lệ này là nguồn của cái bẫy ở mục 6.

### 5. Phép tính con trỏ (pointer arithmetic)

Cộng một số vào con trỏ, ví dụ `p + 1`, là **phép tính con trỏ**. Nó **không** cộng 1 vào con số địa chỉ. Nó nhích sang **phần tử kế tiếp** của kiểu mà `p` trỏ tới, tức là địa chỉ tăng thêm `1 × sizeof(kiểu)` byte.

- Với `int*` (phần tử thường 4 byte): `p + 1` hơn `p` thường 4.
- Với `double*` (phần tử thường 8 byte): `p + 1` hơn `p` thường 8.

Nhờ vậy `p + 2` luôn là "phần tử thứ hai kể từ chỗ `p` đang đứng", không cần ta tự tính byte; và đó chính là lý do `p[i]` bằng `*(p + i)`.

Vài phép khác dùng được:

- `p++` nhích `p` sang phần tử kế tiếp (`p` bị đổi giá trị).
- `q - p` với hai con trỏ **cùng trỏ vào một mảng** cho ra "cách nhau bao nhiêu **phần tử**" (một số nguyên, kiểu `std::ptrdiff_t`). Chuẩn C++ chỉ định nghĩa phép này khi hai con trỏ nằm trong cùng một mảng.
- `p + q` (cộng hai con trỏ) **không có nghĩa**, trình biên dịch từ chối (ví dụ 5 có thử).

Con trỏ có thể trỏ tới mọi phần tử của mảng, và thêm **một vị trí ngay sau phần tử cuối** (như `a + 4` với mảng 4 phần tử). Vị trí đó dùng để so sánh ("đã đi hết chưa?") nhưng **không được giải tham chiếu**.

**Đi ra ngoài mảng là hành vi không xác định (UB, Bài 03).** Ví dụ `a[4]`, `a[-1]` hay `*(p + 10)` với mảng 4 phần tử: chuẩn không hứa chuyện gì sẽ xảy ra. Có thể trông như chạy bình thường, có thể đọc hay ghi nhầm vào biến khác, có thể dừng đột ngột. Mình không chạy các dòng này:

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

### 6. Truyền mảng vào hàm: bẫy `sizeof`

Khi bạn truyền một mảng vào hàm, mảng thoái hóa thành con trỏ, nên hàm chỉ nhận **một địa chỉ**: địa chỉ của phần tử đầu. Nó không nhận số phần tử, cũng không nhận bản sao của mảng. Dù bạn có viết tham số là `int a[4]`, trình biên dịch vẫn coi nó là `int*`.

Hệ quả: bên trong hàm, `sizeof(a)` chỉ là cỡ của **một con trỏ**, không phải 16. Ví dụ 6 chạy thật chuyện này, và `g++ -Wall` còn cảnh báo bạn. Cách đúng: truyền kèm số phần tử, `void in(const int* a, std::size_t n)`. Ở đây `const` đặt trước `int*` nghĩa là "chỉ đọc, không sửa phần tử qua con trỏ này", còn `std::size_t` (Bài 01) là kiểu số không âm hợp để đếm phần tử, cần thêm `#include <cstddef>`.

Cách tốt hơn nữa nằm ở nhóm STL: dùng `std::vector` hoặc `std::array`, những kiểu **mang theo độ dài**. Ở đây ta chỉ nhắc tên.

!!! info "Bạn biết Go?"
    Slice của Go là bộ ba (con trỏ tới phần tử đầu, độ dài, sức chứa), nên độ dài luôn đi kèm. Mảng C++ khi truyền vào hàm thoái hóa thành **chỉ con trỏ** và mất độ dài, vì vậy ta phải tự truyền `n`. Go cũng **không cho** số học con trỏ như `p + 1` (trừ gói `unsafe`), còn C++ cho tự do.

### 7. Con trỏ tới con trỏ: `int**`

Con trỏ cũng là một biến, nên nó có địa chỉ, và ta lưu được địa chỉ đó vào một con trỏ khác. Kiểu của con trỏ đó là `int**`, đọc là "con trỏ tới (con trỏ tới `int`)". Bài này chỉ cần **một** tình huống dùng nó.

Giả sử ta muốn hàm "chọn giúp" một con trỏ: sau khi gọi, con trỏ `p` ở nơi gọi phải trỏ sang chỗ khác. Nếu hàm nhận `int* con`, nó chỉ nhận **bản sao** của `p` (đúng như mục 1). Gán `con = x` chỉ đổi bản sao, `p` ở nơi gọi không đổi. Muốn đổi chính `p`, ta cần đưa **số phòng của tờ giấy `p`**, tức `&p`, có kiểu `int**`; rồi viết `*con = x` để đổi tờ giấy gốc. Ví dụ 8 chạy cả hai cách.

Nguyên tắc chung: muốn hàm sửa một thứ có kiểu `T`, phải đưa `T*`; nếu thứ đó đã là con trỏ thì kiểu thành `T**`. Có một cách khác gọn hơn là tham chiếu (Bài 06); ở đây ta chỉ cần hiểu vì sao `**` xuất hiện.

### 8. Chuỗi kiểu C

Một chữ cái đơn trong C++ là kiểu `char`, viết trong nháy đơn: `'A'`. Máy lưu nó dưới dạng một số (`'A'` là 65). Một **chuỗi** là dãy `char` liền nhau. Chuỗi kiểu C (có từ ngôn ngữ C) là một mảng `char`, và **kết thúc bằng một phần tử đặc biệt `'\0'`** (ký tự có mã số 0), gọi là ký tự kết thúc.

```text
const char* ten = "An";
```

Phần `"An"` (chuỗi trong nháy kép) là **chuỗi hằng**. Nó chiếm **3** ô liền nhau: `'A'`, `'n'` và `'\0'` ở cuối.

```text
  địa chỉ:    0x2000     0x2001     0x2002
             +----------+----------+----------+
             |   'A'    |   'n'    |   '\0'   |
             +----------+----------+----------+
                ^
   ten ---------+     (ten đựng địa chỉ của ký tự đầu, 0x2000)
```

`ten` là con trỏ tới ký tự đầu. Kiểu của chính `"An"` là mảng 3 `const char`, nên nó cũng thoái hóa thành `const char*` khi gán. Chữ `const` ở đây nghĩa là các ký tự **chỉ đọc**.

Hàm không biết chuỗi dài bao nhiêu, nó chỉ đi từng ô cho đến khi gặp `'\0'`. `std::cout << ten` cũng làm đúng thế: in từng ký tự cho đến khi gặp `'\0'`. (Đây chính là "quy ước cũ từ C" ở Bài 01 khiến `char*` bị in thành chữ chứ không phải địa chỉ.)

Về việc sửa: chuỗi hằng là **chỉ đọc**, nên `ten[0] = 'B';` với `const char* ten` bị trình biên dịch từ chối (ví dụ 9 có thử). Muốn một chuỗi sửa được, ta tạo một **mảng** riêng chép nội dung ra: `char ban[] = "An";`. Với đa số việc thực tế, hãy dùng `std::string` (Bài 02) thay vì chuỗi kiểu C: nó tự lo độ dài và việc chép.

## 💻 Ví dụ code

### Ví dụ 1: truyền theo giá trị

```cpp
#include <iostream>

void tang(int x) {                       // (1)
    x = x + 1;                           // (2)
    std::cout << "trong tang: x = " << x << "\n";
}

int main() {
    int a = 5;
    tang(a);                             // (3)
    std::cout << "sau khi goi: a = " << a << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int a = 5;` (trong `main`) | `main` bắt đầu, tạo biến `a` | `a` ở 0x1000 = 5 (địa chỉ minh họa, máy bạn sẽ in số khác) |
| (3) `tang(a);` | Gọi hàm: C++ **chép** giá trị của `a` vào tham số `x` | khung mới của `tang`: `x` ở 0x0f00 = 5; `a` vẫn ở 0x1000 = 5 |
| (2) `x = x + 1;` | Sửa `x` (bản sao) | `x` = 6; `a` vẫn = 5 |
| in trong hàm | In `x` | in `trong tang: x = 6` |
| hết hàm | Khung của `tang` bị gỡ, `x` biến mất | chỉ còn `a` ở 0x1000 = 5 |
| in cuối | In `a` | in `sau khi goi: a = 5` |

(1) là chỗ khai báo hàm: `void`, tên `tang`, tham số `int x`.

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`):

```text
trong tang: x = 6
sau khi goi: a = 5
```

`x` đã thành 6 nhưng `a` vẫn là 5: hàm chỉ sửa bản photo.

**Thử thay đổi: trong `tang` và trong `main`, in địa chỉ `&x` và `&a`.** Mình đã chạy: một lần chạy in `&x = 0x7ffc0135b45c` và `&a = 0x7ffc0135b474`. Hai số khác nhau (số của máy bạn sẽ khác, chỉ cần chúng khác nhau), nên `x` và `a` là hai ô nhớ riêng. Đó là bằng chứng của việc chép.

### Ví dụ 2: truyền con trỏ, kiểm tra null và `swap`

```cpp
#include <iostream>

void tang(int* x) {                      // (1)
    if (x == nullptr) {                  // (2)
        return;
    }
    *x = *x + 1;                         // (3)
}

void doiCho(int* p, int* q) {            // (4)
    int tam = *p;
    *p = *q;
    *q = tam;
}

int main() {
    int a = 5;
    tang(&a);                            // (5)
    std::cout << "a = " << a << "\n";
    tang(nullptr);                       // (6)
    int b = 8;
    doiCho(&a, &b);                      // (7)
    std::cout << "a = " << a << ", b = " << b << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int a = 5;` | `main` tạo `a` | `a` ở 0x1000 = 5 (địa chỉ minh họa) |
| (5) `tang(&a);` | Truyền địa chỉ của `a`; tham số `x` được chép số 0x1000 | `x` ở 0x0f00 = 0x1000 ---> `a` |
| (2) `x == nullptr` | `x` không trống, bỏ qua `return` | không đổi |
| (3) `*x = *x + 1;` | Đi theo `x`: đọc `a` (5), cộng 1, ghi 6 vào **đúng ô của `a`** | `a` = 6 |
| hết hàm | Khung của `tang` bị gỡ, `x` biến mất; `a` vẫn giữ 6 | `a` = 6 |
| in | In `a` | in `a = 6` |
| (6) `tang(nullptr);` | `x` là `nullptr`, nhánh `if` chạy `return` ngay, không đụng gì | không đổi |
| `int b = 8;` | Tạo `b` | `b` ở 0x1004 = 8 |
| (7) `doiCho(&a, &b);` | `p` = 0x1000 (trỏ `a`), `q` = 0x1004 (trỏ `b`) | `p ---> a`, `q ---> b` |
| (4) `tam = *p;` | `tam` giữ tạm giá trị của `a` | `tam` = 6 |
| `*p = *q;` | Chép giá trị `b` vào `a` | `a` = 8 |
| `*q = tam;` | Ghi giá trị cũ của `a` vào `b` | `b` = 6 |
| in cuối | In cả hai | in `a = 8, b = 6` |

(1) là hàm nhận `int*`. Biến `tam` là biến cục bộ của `doiCho`, chỉ để giữ tạm giá trị khi đổi chỗ.

**Kết quả khi chạy**

```text
a = 6
a = 8, b = 6
```

**Thử thay đổi: viết `tang(a);` (quên `&`).** Mình đã thử, không biên dịch được:

```text
error: invalid conversion from ‘int’ to ‘int*’ [-fpermissive]
```

Hàm cần một địa chỉ (`int*`) nhưng bạn đưa một số `int`, và trình biên dịch bắt lỗi này giúp bạn. Nếu bỏ dòng kiểm tra `x == nullptr` (2) thì `tang(nullptr)` ở (6) sẽ giải tham chiếu `nullptr`: hành vi không xác định, mình không chạy.

### Ví dụ 3: mảng, chỉ số, địa chỉ và `sizeof`

```cpp
#include <iostream>

int main() {
    int a[4] = {10, 20, 30, 40};                          // (1)
    std::cout << "a[0] = " << a[0] << ", a[3] = " << a[3] << "\n";   // (2)
    a[1] = 25;                                            // (3)
    for (int i = 0; i < 4; i++) {                         // (4)
        std::cout << "a[" << i << "] = " << a[i] << "  dia chi " << &a[i] << "\n";
    }
    std::cout << "sizeof(a) = " << sizeof(a) << "\n";     // (5)
    std::cout << "sizeof(a[0]) = " << sizeof(a[0]) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `int a[4] = {...};` | Xin 16 ngăn liền nhau, ghi bốn số | `[10][20][30][40]` bắt đầu ở 0x1000 (minh họa) |
| (2) in `a[0]`, `a[3]` | Đọc phần tử đầu và cuối | in `a[0] = 10, a[3] = 40` |
| (3) `a[1] = 25;` | Ghi đè phần tử thứ hai | `[10][25][30][40]` |
| (4) vòng `for` | `i` chạy 0, 1, 2, 3; mỗi vòng in giá trị và **địa chỉ** của `a[i]` | địa chỉ tăng đều |
| (5) `sizeof(a)` | Cỡ của **cả mảng** | in `16` (thường) |
| `sizeof(a[0])` | Cỡ của một phần tử | in `4` (thường) |

**Kết quả khi chạy** (một lần chạy thật):

```text
a[0] = 10, a[3] = 40
a[0] = 10  dia chi 0x7ffef98b98d0
a[1] = 25  dia chi 0x7ffef98b98d4
a[2] = 30  dia chi 0x7ffef98b98d8
a[3] = 40  dia chi 0x7ffef98b98dc
sizeof(a) = 16
sizeof(a[0]) = 4
```

Số địa chỉ trên máy bạn sẽ khác và đổi theo lần chạy; chỉ **kiểu mẫu** quan trọng: các địa chỉ liên tiếp cách nhau 4 (`...d0`, `...d4`, `...d8`, `...dc`, hệ 16) vì mỗi `int` chiếm 4 byte (thường). Chuẩn đảm bảo các phần tử nằm liền nhau; con số 4 là cỡ `int` trên máy thông thường.

**Thử thay đổi 1: khai báo `int a[4] = {10, 20};` (thiếu giá trị).** Mình đã chạy: hai phần tử còn lại được đặt thành `0` (in ra `a[2] = 0` và `a[3] = 0`). Khi có `{ }` mà ít giá trị hơn số ô, các ô thừa được đặt về 0.

**Thử thay đổi 2: `int a[4] = {10, 20, 30, 40, 50};` (thừa giá trị).** Mình đã thử, không biên dịch được:

```text
error: too many initializers for ‘int [4]’
```

### Ví dụ 4: thoái hóa và `p[i]` ≡ `*(p + i)`

```cpp
#include <iostream>

int main() {
    int a[4] = {10, 20, 30, 40};
    int* p = a;                                           // (1)
    std::cout << std::boolalpha;
    std::cout << "p == &a[0] : " << (p == &a[0]) << "\n";   // (2)
    std::cout << "p[2]       = " << p[2] << "\n";          // (3)
    std::cout << "*(p + 2)   = " << *(p + 2) << "\n";      // (4)
    std::cout << "a[2]       = " << a[2] << "\n";
    std::cout << "*(a + 2)   = " << *(a + 2) << "\n";      // (5)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int a[4] = {...};` | Mảng 4 phần tử | `[10][20][30][40]` từ 0x1000 (minh họa) |
| (1) `int* p = a;` | `a` thoái hóa thành địa chỉ của `a[0]`; `p` chép nó | `p` ở 0x1010 = 0x1000 ---> `a[0]` |
| (2) `p == &a[0]` | So địa chỉ hai bên: cùng 0x1000 | in `true` |
| (3) `p[2]` | Viết gọn của `*(p + 2)` | in `30` |
| (4) `*(p + 2)` | Nhích 2 phần tử từ `p` tới 0x1008, đọc ô đó | in `30` |
| in `a[2]` | Đọc trực tiếp qua tên mảng | in `30` |
| (5) `*(a + 2)` | `a` thoái hóa trong biểu thức, nên cộng được như con trỏ | in `30` |

**Kết quả khi chạy**

```text
p == &a[0] : true
p[2]       = 30
*(p + 2)   = 30
a[2]       = 30
*(a + 2)   = 30
```

Cả năm cách viết cùng chạm tới phần tử số 2 (giá trị `30`).

**Thử thay đổi: in `*p + 2` thay cho `*(p + 2)`.** Mình đã chạy: nó in `12`. Dấu `*` dính vào `p` trước (`*p` là `10`) rồi mới cộng 2. Ngoặc quanh `p + 2` là bắt buộc để nhích con trỏ **trước**, giải tham chiếu **sau**.

### Ví dụ 5: `p + 1`, `p++`, hiệu hai con trỏ, đi dọc mảng

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

Dòng (6): `const int* q` là con trỏ chỉ đọc (ta chỉ cộng dồn, không sửa mảng). Vòng lặp bắt đầu từ `a`, lặp đến khi `q` bằng `a + 4`, vị trí ngay sau phần tử cuối (mục 5). Dòng `p + 1` in được số địa chỉ vì với `int*` `std::cout` in địa chỉ (khác `char*`, Bài 01).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a`, `d`, `p`, `pd` | `p` trỏ `a[0]`, `pd` trỏ `d[0]` | `a` từ 0x1000, `d` từ 0x1020, `p` = 0x1000, `pd` = 0x1020 (minh họa) |
| in `p` | Giá trị của `p` | in 0x1000 (minh họa) |
| (1) `p + 1` | Nhích **một phần tử `int`** (4 byte) | in 0x1004 |
| in `pd` | Giá trị của `pd` | in 0x1020 |
| (2) `pd + 1` | Nhích **một phần tử `double`** (8 byte) | in 0x1028 |
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

Số địa chỉ trên máy bạn sẽ khác; chỉ kiểu mẫu đáng nhớ: `p + 1` hơn `p` đúng 4 (`...10` thành `...14`), còn `pd + 1` hơn `pd` đúng 8 (`...20` thành `...28`). **Cùng phép `+ 1`, nhưng nhích theo cỡ phần tử.** Hiệu `cuoi - dau` cho `3` phần tử, không phải 12 byte.

**Thử thay đổi: viết `p + q` với hai con trỏ cùng mảng.** Mình đã thử, không biên dịch được:

```text
error: invalid operands of types ‘int*’ and ‘int*’ to binary ‘operator+’
```

Cộng hai địa chỉ với nhau không có nghĩa gì, nên C++ cấm. Trừ hai con trỏ trong **cùng một mảng** thì có nghĩa (đếm phần tử); trừ hai con trỏ vào hai mảng khác nhau thì chuẩn không định nghĩa, nên mình không chạy.

### Ví dụ 6: bẫy `sizeof` trong tham số mảng

Chương trình này **biên dịch được nhưng `g++ -Wall` cảnh báo**, nên mình đánh dấu để chương trình kiểm tra của khóa không chạy nó (mình đã tự biên dịch và chạy):

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

Cùng tên `a`, cùng viết `sizeof(a)` mà ra 16 và 8. Con số 16 và 8 là cỡ thường gặp (4 byte cho `int`, 8 byte cho con trỏ trên máy 64 bit), chuẩn không ép những số này. Điều chuẩn đảm bảo là: tham số mảng thực chất là con trỏ, nên trong hàm không có cách nào biết mảng dài bao nhiêu.

**Thử thay đổi: sửa `int a[4]` thành `int* a`.** Mình đã chạy: vẫn in `16` rồi `8`, và **không còn cảnh báo**. Hai cách viết tham số là cùng một thứ; cảnh báo chỉ nhắc rằng ta đang viết "dáng mảng" nhưng nhận "thân con trỏ".

### Ví dụ 7: truyền kèm số phần tử

```cpp
#include <iostream>
#include <cstddef>

int tong(const int* a, std::size_t n) {                // (1)
    int s = 0;
    for (std::size_t i = 0; i < n; i++) {              // (2)
        s = s + a[i];
    }
    return s;                                          // (3)
}

int main() {
    int a[4] = {10, 20, 30, 40};
    std::size_t n = sizeof(a) / sizeof(a[0]);          // (4)
    std::cout << "n = " << n << "\n";
    std::cout << "tong = " << tong(a, n) << "\n";      // (5)
    return 0;
}
```

Hàm này trả về một số `int` (thay vì `void`) nên kết thúc bằng `return s;` (3) để đưa số đó cho nơi gọi.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a` | Mảng 4 phần tử ở `main` | `[10][20][30][40]` từ 0x1000 (minh họa) |
| (4) `sizeof(a) / sizeof(a[0])` | Ở `main` (nơi `a` còn là mảng): 16 / 4 = số phần tử | `n` = 4 |
| in `n` | In số phần tử | in `n = 4` |
| (5) `tong(a, n)` | Truyền địa chỉ phần tử đầu và `n` | `a` của hàm = 0x1000, `n` = 4 |
| (2) vòng `for` | `i` chạy 0..3, cộng dồn `a[i]` | `s` lần lượt 10, 30, 60, 100 |
| (3) `return s;` | Trả `100` về cho `main` | in `tong = 100` |

(1) là chữ ký hàm: nhận con trỏ chỉ đọc cùng số phần tử.

**Kết quả khi chạy**

```text
n = 4
tong = 100
```

Phép chia `sizeof(a) / sizeof(a[0])` chỉ đúng ở nơi `a` còn là mảng thật (ví dụ 6 vừa cho thấy). Trong hàm thì không dùng được, nên `n` phải được truyền vào.

### Ví dụ 8: `int**` và hàm "cấp cho bạn một con trỏ mới"

Hai chương trình, cùng việc: hàm làm cho `p` (ban đầu trỏ `a`) chuyển sang trỏ `b`. Cái đầu **không đạt mục tiêu**:

```cpp
#include <iostream>

void chonHong(int* con, int* x) {
    con = x;                                  // (1)
}

int main() {
    int a = 1;
    int b = 2;
    int* p = &a;
    chonHong(p, &b);                          // (2)
    std::cout << "*p = " << *p << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a`, `b`, `p` | `p` trỏ `a` | `a` ở 0x1000 = 1, `b` ở 0x1004 = 2, `p` ở 0x1008 = 0x1000 (minh họa) |
| (2) `chonHong(p, &b)` | `con` được **chép** từ `p`; `x` nhận địa chỉ của `b` | `con` ở 0x0f00 = 0x1000; `x` ở 0x0f08 = 0x1004 |
| (1) `con = x;` | Đổi **bản sao** `con` sang 0x1004 | `con` = 0x1004; `p` vẫn = 0x1000 |
| hết hàm | Khung của `chonHong` bị gỡ, bản sao mất | `p` vẫn trỏ `a` |
| in `*p` | Đi theo `p` (vẫn ghi `a`) | in `*p = 1` |

**Kết quả khi chạy:** `*p = 1`. Con trỏ `p` ở `main` **không** đổi. Cái thứ hai dùng `int**`:

```cpp
#include <iostream>

void chonDung(int** con, int* x) {            // (1)
    *con = x;                                 // (2)
}

int main() {
    int a = 1;
    int b = 2;
    int* p = &a;
    chonDung(&p, &b);                         // (3)
    std::cout << "*p = " << *p << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a`, `b`, `p` | Như trên | `p` ở 0x1008 = 0x1000 ---> `a` |
| (3) `chonDung(&p, &b)` | Đưa **địa chỉ của `p`** (0x1008) và địa chỉ của `b` | `con` ở 0x0f00 = 0x1008 ---> `p`; `x` = 0x1004 |
| (2) `*con = x;` | Đi theo `con` tới ô `p`, ghi 0x1004 vào đó | `p` = 0x1004 ---> `b` |
| hết hàm | Khung bị gỡ | `p` vẫn = 0x1004 |
| in `*p` | Đi theo `p`, giờ ghi `b` | in `*p = 2` |

(1) là chữ ký hàm: `int** con` là "con trỏ tới con trỏ tới `int`".

**Kết quả khi chạy:** `*p = 2`. Lần này `p` ở `main` đã trỏ sang `b`.

**Thử thay đổi: ở (2) của chương trình thứ hai viết `con = x;` (bỏ dấu `*`).** Mình đã thử, không biên dịch được:

```text
error: cannot convert ‘int*’ to ‘int**’ in assignment
```

`con` có kiểu `int**` còn `x` là `int*`, hai kiểu khác nhau. Phải đi theo `con` bằng `*con` để nhận một ô kiểu `int*`.

### Ví dụ 9: chuỗi kiểu C

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

Hai chỗ cần giải thích. `static_cast<int>(ten[i])` (Bài 01) ép một `char` thành số để in ra **mã số** thay vì chữ. `while (điều kiện) { ... }` lặp thân vòng lặp chừng nào điều kiện còn đúng (như `for` của Go khi chỉ có điều kiện), và `dem++` là tăng `dem` thêm 1.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `const char* ten = "An";` | Chuỗi hằng "An" gồm 3 ô: `'A'`, `'n'`, `'\0'`; `ten` giữ địa chỉ của ô đầu | `[A][n][\0]` từ 0x2000; `ten` = 0x2000 (minh họa) |
| (2) in `ten` | `std::cout` đi từ 0x2000, in từng ký tự đến khi gặp `'\0'` | in `ten = An` |
| (3) vòng `for` | In mã số của 3 ô: `'A'` là 65, `'n'` là 110, `'\0'` là 0 | in ba dòng `ten[0] = 65`, `ten[1] = 110`, `ten[2] = 0` |
| `p = ten` | `p` bắt đầu ở ký tự đầu | `p` = 0x2000 |
| (4) vòng `while` | Chừng nào `*p` chưa là `'\0'`: đếm 1, nhích `p`; sau 2 vòng gặp `'\0'` thì dừng | `dem` = 2, `p` = 0x2002 |
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

??? question "Truyền theo giá trị và truyền bằng con trỏ khác nhau thế nào?"
    Truyền theo giá trị: hàm nhận một **bản sao** của đối số, nên sửa tham số không ảnh hưởng biến gốc ở nơi gọi. Truyền bằng con trỏ: hàm nhận (một bản sao của) **địa chỉ** của biến gốc, và đi theo địa chỉ bằng `*p` thì sửa được chính biến gốc. Lưu ý: bản thân con trỏ vẫn được truyền theo giá trị, nên muốn đổi chính con trỏ ở nơi gọi phải truyền `int**` (hoặc tham chiếu, Bài 06).

??? question "`a[i]` và `*(a + i)` quan hệ thế nào?"
    Chúng tương đương: `a[i]` được định nghĩa là `*(a + i)`. Tên mảng `a` thoái hóa thành con trỏ tới phần tử đầu, `a + i` là địa chỉ của phần tử thứ `i` (nhích `i` phần tử, không phải `i` byte), và `*` đi theo địa chỉ đó. Cũng vì vậy `p[i]` dùng được với mọi con trỏ `p`, không chỉ với tên mảng.

??? question "Array decay là gì, và `sizeof` bị ảnh hưởng ra sao?"
    Trong hầu hết biểu thức, tên mảng tự chuyển thành con trỏ tới phần tử đầu; riêng `sizeof` và `&` là ngoại lệ. Khi truyền mảng vào hàm, tham số thực chất là con trỏ (dù viết `int a[4]`), nên `sizeof(a)` trong hàm cho cỡ của con trỏ (thường 8), không phải cỡ mảng (thường 16), và `g++ -Wall` cảnh báo `-Wsizeof-array-argument`. Cách xử lý: truyền kèm số phần tử, hoặc dùng `std::vector`/`std::array` (nhóm STL).

??? question "Con trỏ `p + 1` nhích bao nhiêu byte?"
    Nhích đúng `sizeof(kiểu mà p trỏ tới)` byte, tức một phần tử chứ không phải một byte. Với `int*` thường là 4 byte, với `double*` thường là 8, với `char*` là 1. Phép trừ hai con trỏ cùng mảng cũng tính bằng phần tử, và chuẩn chỉ định nghĩa phép trừ khi hai con trỏ cùng một mảng.

??? question "Chuỗi kiểu C kết thúc thế nào?"
    Là mảng `char` kết thúc bằng ký tự `'\0'` (mã 0). Hàm đọc chuỗi, như `std::cout << s`, không biết độ dài: nó đi từng ký tự cho đến khi gặp `'\0'`. Nên chuỗi `"An"` chiếm 3 byte, và thiếu `'\0'` thì đọc chuỗi là hành vi không xác định. Chuỗi hằng là `const char[N]`, không sửa được; trong C++ hiện đại nên ưu tiên `std::string`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Đi ra ngoài mảng"
    Mảng 4 phần tử có chỉ số 0 đến 3; `a[4]` là hành vi không xác định, và C++ không báo lỗi lúc chạy như Go. Hay gặp khi viết vòng lặp `i <= 4` thay vì `i < 4`. Quy tắc: số phần tử `n` thì chỉ số cuối là `n - 1`, và điều kiện lặp là `i < n`.

!!! warning "Lỗi 2: Dùng `sizeof` để đếm phần tử bên trong hàm"
    `sizeof(a) / sizeof(a[0])` chỉ đếm đúng ở nơi `a` còn là mảng thật. Trong hàm, `a` là con trỏ, kết quả là cỡ con trỏ chia cỡ phần tử, một con số vô nghĩa (và `-Wall` đã cảnh báo). Hãy truyền `n` vào hàm.

!!! warning "Lỗi 3: Tưởng `p + 1` cộng 1 byte"
    `p + 1` nhích một **phần tử**. Với `int*` địa chỉ tăng (thường) 4. Muốn "nhích một byte" thì phải xử lý theo kiểu `char*`, và đó là việc hiếm gặp.

!!! warning "Lỗi 4: Muốn hàm đổi con trỏ nhưng chỉ truyền `int*`"
    Hàm nhận `int*` chỉ giữ **bản sao** của con trỏ; gán lại con trỏ trong hàm không đổi con trỏ ở nơi gọi (ví dụ 8). Cần `int**` (hoặc tham chiếu, Bài 06). Còn `*p = ...` thì sửa được giá trị mà `p` trỏ tới.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="04" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Với `void tang(int x)`, khi gọi `tang(a)` thì tham số `x` là gì?

- Chính biến `a`, chỉ được gọi bằng một cái tên khác
- Một biến mới, được chép giá trị hiện tại của `a`
- Địa chỉ của biến `a`, hàm tự lấy bằng dấu `&`
- Một ô nhớ dùng chung với `a`, đổi một nơi là đổi cả hai

<p class="giai-thich" markdown>Truyền theo giá trị nghĩa là C++ chép giá trị của `a` vào một biến mới `x` trong khung stack của hàm, nên sửa `x` không đụng tới `a`. `x` không phải `a` mang tên khác: hai biến có hai địa chỉ khác nhau. Hàm cũng không tự lấy địa chỉ: muốn nhận địa chỉ thì tham số phải có kiểu `int*` và nơi gọi phải viết `&a`. Ô nhớ dùng chung chỉ có khi truyền con trỏ, đó là tờ giấy cùng ghi một số phòng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

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
**Câu 3.** Giả sử `sizeof(int)` là 4 và `int* p` đang đựng địa chỉ `0x1000`. Sau `int* q = p + 1;`, `q` đựng địa chỉ nào?

- `0x1004`, vì con trỏ nhích một phần tử `int`
- `0x1001`, vì phép cộng 1 làm địa chỉ tăng 1
- `0x1008`, vì con trỏ nhích hai lần cỡ của `int`
- `0x1010`, vì con trỏ nhích 16 byte cả mảng

<p class="giai-thich" markdown>Phép tính con trỏ nhích theo phần tử: địa chỉ tăng `1 × sizeof(int)`, tức 4, nên ra `0x1004`. Chọn `0x1001` là nhầm `p + 1` với cộng 1 vào con số địa chỉ, mà ta đã thấy ở ví dụ 5 là sai. `0x1008` sẽ là kết quả của `p + 2`, còn `0x1010` chỉ có nghĩa nếu mảng có sẵn 16 byte và ta nhích qua cả mảng, điều `p + 1` không làm.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn code sau, trên máy 64 bit thông thường (`int` 4 byte, con trỏ 8 byte). Nó in ra gì?

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

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đoạn code sau. Nó in ra gì?

```text
void doi(int* p, int* q) { int* t = p; p = q; q = t; }
int main() { int a = 1; int b = 2; doi(&a, &b); std::cout << a << " " << b; }
```

- `2 1`, vì `doi` đã đổi chỗ hai số nên `a` thành 2
- `1 1`, vì cả hai biến bị ghi đè bằng giá trị cũ của `a`
- `1 2`, vì `doi` chỉ đổi hai con trỏ bản sao
- `2 2`, vì cả hai biến bị ghi đè bằng giá trị cũ của `b`

<p class="giai-thich" markdown>Hàm đổi chỗ hai **con trỏ** `p` và `q`, mà chúng chỉ là bản sao của hai địa chỉ nằm trong khung của hàm. Không dòng nào dùng `*p` hay `*q` để ghi, nên `a` và `b` không bị chạm tới: kết quả `1 2` (mình đã chạy). Để thật sự đổi chỗ hai số phải đổi giá trị mà chúng trỏ tới: `int tam = *p; *p = *q; *q = tam;`. Hai kết quả `1 1` và `2 2` cần có ai đó ghi vào `a` hoặc `b`, mà đoạn code này không làm vậy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Chuỗi kiểu C như `"An"` kết thúc bằng gì?

- Ký tự `'\0'` (mã số 0) đứng ngay sau chữ cuối
- Ký tự xuống dòng `'\n'` đứng ngay sau chữ cuối
- Một con số ghi độ dài, đặt ở đầu chuỗi
- Dấu nháy kép `"` đứng ngay sau chữ cuối

<p class="giai-thich" markdown>Chuỗi kiểu C là dãy `char` kết thúc bằng ký tự `'\0'`, nên `"An"` chiếm 3 ô và hàm nào đọc chuỗi cũng dừng khi gặp ký tự này. Xuống dòng `'\n'` chỉ là một ký tự bình thường, có thể nằm giữa chuỗi. Con số độ dài ở đầu là cách của một số ngôn ngữ khác (ví dụ chuỗi của Go giữ độ dài riêng), còn chuỗi kiểu C không có. Dấu nháy kép chỉ là cách ta viết chuỗi trong code, không nằm trong bộ nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Cho `int a[4] = {1, 2, 3, 4};`. Theo chuẩn C++, câu lệnh `a[4] = 9;` gây ra chuyện gì?

- Trình biên dịch bắt buộc phải từ chối, nên chương trình không được tạo ra
- Chương trình bắt buộc dừng lúc chạy với lỗi `index out of range`
- Mảng tự nới thêm một ô ở cuối để chứa được số `9` vừa ghi
- Chuẩn không hứa kết quả gì, đó là hành vi không xác định

<p class="giai-thich" markdown>`a[4]` nằm ngoài mảng, ngay sau phần tử cuối, và ghi vào đó là hành vi không xác định (UB): chuẩn không hứa gì, có thể chạy tiếp, ghi nhầm biến khác, hoặc dừng đột ngột. Trình biên dịch không bắt buộc phải từ chối (nhiều lúc chỉ cảnh báo, nhiều lúc không biết). C++ cũng không kiểm tra chỉ số lúc chạy như Go (Go dừng với `index out of range`). Mảng có kích thước cố định, nó không tự nới thêm ô.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Với `a` là một mảng, biểu thức `a[i]` tương đương với biểu thức nào?

- `a + i`, địa chỉ của phần tử thứ `i`
- `*(a + i)`, phần tử nằm ở địa chỉ đó
- `*a + i`, phần tử đầu rồi cộng thêm `i`
- `&a + i`, nhích `i` lần qua cả mảng

<p class="giai-thich" markdown>`a[i]` được định nghĩa là `*(a + i)`: nhích `i` phần tử từ phần tử đầu, rồi đi theo địa chỉ để lấy chính phần tử đó. `a + i` thì chỉ là địa chỉ, chưa lấy giá trị. `*a + i` lấy phần tử đầu `a[0]` rồi mới cộng `i` vào giá trị, nên là một số khác. `&a + i` nhích theo cỡ cả mảng (mỗi bước đi hết một mảng), không phải theo từng phần tử.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Truyền theo giá trị chép đối số vào tham số, nên hàm chỉ sửa bản sao; muốn sửa biến của nơi gọi thì nhận con trỏ (`void tang(int* x)`, gọi `tang(&a)`) và kiểm tra `nullptr` trước khi dùng `*x`.
2. Mảng `int a[4]` là bốn ngăn liền nhau, chỉ số từ 0; tên mảng trong biểu thức thoái hóa thành con trỏ tới phần tử đầu, nên `p[i]` bằng `*(p + i)` và `a[i]` bằng `*(a + i)`.
3. `p + 1` nhích đúng một phần tử (`sizeof(kiểu)` byte, ví dụ thường 4 với `int*` và 8 với `double*`), `q - p` đếm số phần tử trong cùng một mảng, không có `p + q`; đi ra ngoài mảng là hành vi không xác định và C++ không tự kiểm tra.
4. Truyền mảng vào hàm chỉ truyền con trỏ: `sizeof` tham số trong hàm là cỡ con trỏ (thường 8) khác `sizeof` của mảng ở nơi khai báo (thường 16), nên phải truyền kèm số phần tử, hoặc dùng `std::vector`/`std::array`; muốn hàm đổi chính một con trỏ thì truyền `int**`.
5. Chuỗi kiểu C `const char* ten = "An";` là con trỏ tới các ký tự kết thúc bằng `'\0'` (nên chiếm 3 ô), chuỗi hằng không sửa được, và trong thực tế nên dùng `std::string`.
