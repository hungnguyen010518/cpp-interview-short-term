# Bài 04 — Con trỏ với hàm

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được hàm sửa biến của nơi gọi bằng con trỏ (`void tang(int* x)`), và phân biệt được với truyền theo giá trị (hàm chỉ sửa bản sao).
    - Viết được hàm `swap` bằng con trỏ, và biết kiểm tra `nullptr` bên trong hàm.
    - Hiểu vì sao muốn hàm đổi chính một con trỏ thì phải truyền `int**`.

**Bạn cần biết trước:** [Bài 01](01-bo-nho-byte-dia-chi.md) (địa chỉ, `&`), [Bài 02](02-stack-heap-static.md) (khung gọi hàm trên stack) và [Bài 03](03-con-tro-co-ban.md) (con trỏ, `*p`, `nullptr`).

## 🧠 Câu chuyện mở đầu

Quay lại dãy tủ khóa của [Bài 01](01-bo-nho-byte-dia-chi.md). Bài làm của bạn đang nằm trong một ngăn tủ, và bạn nhờ một người bạn sửa lỗi giúp. Có hai cách đưa bài.

**Cách 1: gửi bản photo.** Bạn ấy sửa thoải mái trên bản photo, nhưng bài gốc trong tủ không đổi một nét. Đây là **truyền theo giá trị (pass by value)**: hàm nhận một **bản sao**.

**Cách 2: đưa tờ giấy ghi số ngăn tủ** (tờ giấy của [Bài 03](03-con-tro-co-ban.md)). Bạn ấy mở đúng ngăn đó và sửa trực tiếp lên bài gốc. Đây là **truyền con trỏ**.

!!! info "Chỗ nào ví dụ photo và số ngăn không còn đúng?"
    Số ngăn có thể sai, hoặc đồ trong ngăn đã bị dọn mất (chuyện này sẽ gặp ở Bài 07, khi học `new` và `delete`). Ngoài ra, hàm luôn nhận **bản sao của tờ giấy**: bạn ấy có thể vẽ nguệch ngoạc lên tờ giấy của mình mà tờ giấy của bạn không đổi. Mục 3 cho thấy điều này gây ra chuyện gì.

## 📖 Giải thích

### 1. Hàm có tham số, và truyền theo giá trị

Ta đã thấy vài hàm nhỏ ở Bài 02; giờ học kỹ cách viết một hàm. Hình dạng của nó:

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

Tham số `x` là **một biến mới**, nằm trong khung stack của riêng lần gọi này (Bài 02). Lúc gọi, C++ **chép giá trị** của `a` vào `x`. Hàm sửa `x` thì chỉ sửa bản photo, còn `a` ở nơi gọi vẫn như cũ. Đó là truyền theo giá trị, cách mặc định của C++.

!!! info "Bạn biết Go?"
    Go cũng truyền theo giá trị: `func tang(x int)` cho đúng kết quả y hệt. Với con trỏ cũng vậy: Go truyền con trỏ theo giá trị (chép địa chỉ), và C++ làm giống hệt, như mục 3 sẽ cho thấy.

### 2. Truyền con trỏ để sửa bản gốc

Muốn hàm sửa được biến của nơi gọi, ta đưa **số ngăn** thay vì bản photo: tham số có kiểu con trỏ, và nơi gọi truyền địa chỉ bằng `&` (cả hai đã học ở Bài 03).

```text
void tang(int* x) {     // x là con trỏ tới int
    *x = *x + 1;        // đi theo x, đọc ô đó, cộng 1, ghi lại vào đúng ô đó
}
...
tang(&a);               // đưa địa chỉ của a
```

Bên trong hàm, `x` vẫn là một biến mới (bản sao của tờ giấy), nhưng tờ giấy chép lại **ghi cùng một số ngăn**. Nên `*x` chính là `a`.

Con trỏ có thể là `nullptr` (Bài 03), mà đi theo `nullptr` là hành vi không xác định. Vì vậy hàm nhận con trỏ nên kiểm tra trước: `if (x == nullptr) { return; }`. Dòng `return;` (không kèm giá trị) thoát khỏi hàm `void` ngay lập tức.

Ví dụ kinh điển là hàm **đổi chỗ (swap)** hai biến: không thể viết được bằng truyền theo giá trị, vì hàm chỉ đổi chỗ hai bản photo. Với con trỏ thì được, và ví dụ 2 làm đúng việc này.

### 3. Con trỏ tới con trỏ: `int**`

Con trỏ cũng là một biến, nên nó có địa chỉ, và ta lưu được địa chỉ đó vào một con trỏ khác. Kiểu của con trỏ đó là `int**`, đọc là "con trỏ tới (con trỏ tới `int`)". Bài này chỉ cần **một** tình huống dùng nó.

**Ta muốn gì?** Một hàm "chọn giúp" một con trỏ: sau khi gọi, con trỏ `p` ở nơi gọi phải trỏ sang chỗ khác.

**Vì sao `int*` không đủ?** Hàm nhận `int* con` chỉ nhận **bản sao** của `p` (đúng như mục 1). Gán `con = x` chỉ đổi bản sao, còn `p` ở nơi gọi không đổi.

**Vì sao `int**` được?** Ta đưa **số ngăn của chính tờ giấy `p`**, tức `&p`, có kiểu `int**`. Rồi viết `*con = x` để đổi tờ giấy gốc. Ví dụ 3 chạy cả hai cách.

Nguyên tắc chung: muốn hàm sửa một thứ có kiểu `T`, phải đưa `T*`; nếu thứ đó đã là con trỏ thì kiểu thành `T**`. Có một cách gọn hơn là tham chiếu (Bài 06); ở đây ta chỉ cần hiểu vì sao `**` xuất hiện.

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
| hết hàm | Khung của `tang` bị gỡ; `a` vẫn giữ 6 | `a` = 6 |
| in | In `a` | in `a = 6` |
| (6) `tang(nullptr);` | `x` là `nullptr`, nhánh `if` chạy `return` ngay | không đổi |
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

Hàm cần một địa chỉ (`int*`) nhưng bạn đưa một số `int`, và trình biên dịch bắt lỗi này giúp bạn. Nếu bỏ dòng kiểm tra (2) thì `tang(nullptr)` ở (6) sẽ giải tham chiếu `nullptr`: hành vi không xác định, mình không chạy.

### Ví dụ 3: `int**` và hàm "cấp cho bạn một con trỏ mới"

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

**Chạy từng dòng**

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

**Chạy từng dòng**

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

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Truyền theo giá trị và truyền bằng con trỏ khác nhau thế nào?"
    Truyền theo giá trị: hàm nhận một **bản sao** của đối số, nên sửa tham số không ảnh hưởng biến gốc ở nơi gọi. Truyền bằng con trỏ: hàm nhận (một bản sao của) **địa chỉ** của biến gốc, và đi theo địa chỉ bằng `*p` thì sửa được chính biến gốc. Lưu ý: bản thân con trỏ vẫn được truyền theo giá trị.

??? question "Vì sao hàm nhận con trỏ nên kiểm tra `nullptr`?"
    Nơi gọi có thể truyền `nullptr`, và giải tham chiếu `nullptr` là hành vi không xác định. Kiểm tra `if (p == nullptr) return;` ở đầu hàm biến lỗi đó thành một nhánh xử lý rõ ràng thay vì chương trình chạy sai.

??? question "Muốn hàm đổi chính con trỏ của nơi gọi thì làm sao?"
    Con trỏ cũng được truyền theo giá trị, nên hàm nhận `int*` chỉ sửa bản sao. Phải truyền địa chỉ của con trỏ (`&p`, kiểu `int**`) rồi gán `*con = ...`, hoặc dùng tham chiếu (Bài 06).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên `&` khi gọi hàm nhận con trỏ"
    `tang(a)` với `void tang(int* x)` là lỗi biên dịch (ví dụ 2). Phải viết `tang(&a)`.

!!! warning "Lỗi 2: Tưởng gán lại con trỏ trong hàm sẽ đổi con trỏ ở nơi gọi"
    Hàm nhận `int*` chỉ giữ **bản sao** của con trỏ; `con = x` không đổi `p` ở nơi gọi (ví dụ 3). Còn `*con = ...` (với `con` kiểu `int*`) thì sửa được giá trị mà nó trỏ tới.

!!! warning "Lỗi 3: Đổi chỗ hai con trỏ thay vì đổi giá trị"
    Trong `doiCho`, viết `int* t = p; p = q; q = t;` chỉ đổi chỗ hai bản sao của con trỏ, `a` và `b` không đổi. Phải đổi giá trị: `int tam = *p; *p = *q; *q = tam;`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="04" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Với `void tang(int x)`, khi gọi `tang(a)` thì tham số `x` là gì?

- Chính biến `a`, chỉ được gọi bằng một cái tên khác
- Một biến mới, được chép giá trị hiện tại của `a`
- Địa chỉ của biến `a`, hàm tự lấy bằng dấu `&`
- Một ô nhớ dùng chung với `a`, đổi một nơi là đổi cả hai

<p class="giai-thich" markdown>Truyền theo giá trị nghĩa là C++ chép giá trị của `a` vào một biến mới `x` trong khung stack của hàm, nên sửa `x` không đụng tới `a`. `x` không phải `a` mang tên khác: hai biến có hai địa chỉ khác nhau. Hàm cũng không tự lấy địa chỉ: muốn nhận địa chỉ thì tham số phải có kiểu `int*` và nơi gọi phải viết `&a`. Ô nhớ dùng chung chỉ có khi truyền con trỏ, đó là tờ giấy cùng ghi một số ngăn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
void tang(int* x) { *x = *x + 1; }
int main() { int a = 5; tang(&a); std::cout << a; }
```

- `5`, vì hàm chỉ sửa bản sao của `a`
- Một địa chỉ dạng `0x…`, vì ta truyền `&a`
- `6`, vì `*x` chính là ô nhớ của `a`
- Lỗi biên dịch, vì không được gán cho `*x`

<p class="giai-thich" markdown>Hàm nhận địa chỉ của `a`, nên `*x` là chính ô nhớ của `a` và dòng `*x = *x + 1;` đổi `a` từ 5 thành 6 (mình đã chạy). Kết quả `5` đúng nếu `x` là `int` chứ không phải `int*`. Chương trình in `a` chứ không in `x`, nên không có địa chỉ nào hiện ra. Gán cho `*x` là hợp lệ và là cách chính để sửa biến qua con trỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn code sau. Nó in ra gì?

```text
void doi(int* p, int* q) { int* t = p; p = q; q = t; }
int main() { int a = 1; int b = 2; doi(&a, &b); std::cout << a << " " << b; }
```

- `1 2`, vì `doi` chỉ đổi hai con trỏ bản sao
- `2 1`, vì `doi` đã đổi chỗ hai số nên `a` thành 2
- `1 1`, vì cả hai biến bị ghi đè bằng giá trị cũ của `a`
- `2 2`, vì cả hai biến bị ghi đè bằng giá trị cũ của `b`

<p class="giai-thich" markdown>Hàm đổi chỗ hai **con trỏ** `p` và `q`, mà chúng chỉ là bản sao của hai địa chỉ nằm trong khung của hàm. Không dòng nào dùng `*p` hay `*q` để ghi, nên `a` và `b` không bị chạm tới: kết quả `1 2` (mình đã chạy). Để thật sự đổi chỗ hai số phải đổi giá trị mà chúng trỏ tới: `int tam = *p; *p = *q; *q = tam;`. Hai kết quả `1 1` và `2 2` cần có ai đó ghi vào `a` hoặc `b`, mà đoạn code này không làm vậy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Vì sao muốn hàm đổi chính con trỏ `p` của nơi gọi, ta phải truyền `&p` (kiểu `int**`)?

- Vì hàm chỉ nhận bản sao của `p`, nên cần địa chỉ của `p`
- Vì `int*` không chứa được địa chỉ của biến kiểu `int`
- Vì con trỏ có kích thước lớn nên truyền theo giá trị bị lỗi
- Vì `**` bắt hàm phải kiểm tra `nullptr` trước khi dùng

<p class="giai-thich" markdown>Mọi tham số được chép từ đối số, con trỏ cũng vậy: hàm nhận `int*` sửa bản sao của `p`, còn `p` gốc không đổi. Đưa `&p` thì hàm có địa chỉ của chính `p` và đổi được nó bằng `*con = ...`. `int*` chứa địa chỉ của `int` rất bình thường, đó là việc nó làm hằng ngày. Con trỏ chỉ chiếm vài byte nên chép nó không gây lỗi, và `**` không liên quan gì tới việc kiểm tra `nullptr`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Vì sao hàm nhận một con trỏ nên kiểm tra `nullptr` ở đầu hàm?

- Vì `nullptr` luôn làm chương trình dừng lúc chạy
- Vì `nullptr` có thể lọt vào, và `*p` khi đó là UB
- Vì trình biên dịch bắt buộc có dòng kiểm tra này
- Vì con trỏ nhận qua tham số là bản sao nên hay trống

<p class="giai-thich" markdown>Hàm không kiểm soát được nơi gọi truyền gì. Nếu `nullptr` lọt vào mà hàm vẫn viết `*p` thì đó là hành vi không xác định (UB). `nullptr` không "luôn làm chương trình dừng": chuẩn không hứa kết quả nào. Trình biên dịch không ép viết dòng kiểm tra, đó là thói quen phòng thủ của người viết. Và bản sao của một con trỏ có cùng giá trị với bản gốc, nó không tự biến thành trống.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Cho `void tang(int* x)` và `int a = 5;`. Câu lệnh `tang(a);` cho kết quả gì?

- Hàm chạy và `a` thành 6, vì C++ tự lấy địa chỉ của `a`
- Hàm chạy nhưng `a` vẫn 5, vì `a` được truyền theo giá trị
- Lỗi biên dịch, vì đang đưa một `int` vào chỗ cần `int*`
- Chương trình biên dịch được nhưng dừng khi chạy

<p class="giai-thich" markdown>Tham số cần một địa chỉ (`int*`) mà `a` là một số `int`, hai kiểu khác nhau, nên `g++` báo lỗi `invalid conversion from ‘int’ to ‘int*’` (mình đã thử). C++ không tự lấy địa chỉ giùm bạn: phải viết `tang(&a)`. Vì chương trình không biên dịch được nên không có chuyện `a` đổi hay không đổi, và cũng không có chuyện chạy rồi mới dừng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn code sau. Nó in ra gì?

```text
void chon(int* con, int* x) { con = x; }
int main() { int a = 1; int b = 2; int* p = &a; chon(p, &b); std::cout << *p; }
```

- `2`, vì `p` đã được đổi sang trỏ vào `b`
- Một địa chỉ, vì `p` giờ chứa địa chỉ của `b`
- Lỗi biên dịch, vì không được gán `con = x`
- `1`, vì `con` chỉ là bản sao của `p`

<p class="giai-thich" markdown>`con = x;` đổi bản sao `con` sang trỏ vào `b`, nhưng `p` ở `main` vẫn trỏ vào `a`, nên `*p` là `1` (mình đã chạy). Chọn `2` là tưởng gán trong hàm đổi được `p` gốc: muốn vậy phải dùng `int**`. Chương trình in `*p` chứ không in `p`, nên không có địa chỉ. Gán một con trỏ cho con trỏ cùng kiểu là hợp lệ, không có lỗi biên dịch nào.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Truyền theo giá trị chép đối số vào tham số, nên hàm chỉ sửa bản sao và biến gốc của nơi gọi không đổi.
2. Muốn sửa biến của nơi gọi thì nhận con trỏ (`void tang(int* x)`, gọi `tang(&a)`), sửa bằng `*x = ...`.
3. Hàm nhận con trỏ nên kiểm tra `nullptr` trước khi dùng `*x`, vì giải tham chiếu `nullptr` là hành vi không xác định.
4. `swap` bằng con trỏ phải đổi giá trị (`int tam = *p; *p = *q; *q = tam;`); chỉ đổi chỗ hai con trỏ thì `a` và `b` không đổi.
5. Con trỏ cũng truyền theo giá trị, nên muốn hàm đổi chính con trỏ ở nơi gọi thì truyền `int**` (hoặc tham chiếu, Bài 06).
