# Bài 06 — Tham chiếu và const

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng được tham chiếu (`int& b = a;`) như một biệt danh của biến, và biết nó khác con trỏ ở chỗ nào.
    - Chọn đúng cách truyền tham số cho hàm: theo giá trị, bằng con trỏ, bằng tham chiếu hay bằng `const&`.
    - Đọc đúng `const int*`, `int* const`, `const int&`, và biết vì sao không được trả về tham chiếu tới biến cục bộ.

**Bạn cần biết trước:** [Bài 03](03-con-tro-co-ban.md) (con trỏ, `*p`, `&`) và [Bài 04](04-con-tro-ham.md) (truyền theo giá trị, truyền con trỏ).

## 🧠 Câu chuyện mở đầu

Bạn Nguyễn Văn An có biệt danh ở lớp là "Tí". Cô giáo gọi "Tí lên bảng" hay gọi "An lên bảng" thì **cùng một người** đứng dậy. Biệt danh không tạo ra một người thứ hai: nó chỉ là một cái tên nữa cho người cũ.

**Tham chiếu (reference)** trong C++ là biệt danh đó: một cái tên thứ hai cho một biến có sẵn. Sửa qua tên nào cũng là sửa đúng biến ấy, không có bản sao nào cả.

Còn **`const`** giống nhãn dán **"chỉ được xem, không được sửa"** lên một món đồ. Ai cầm món đồ có nhãn đó thì được đọc, nhưng nếu cố sửa thì trình biên dịch (chương trình dịch code của bạn) từ chối ngay lúc dịch, chưa cần chạy.

!!! info "Chỗ nào ví dụ biệt danh không còn đúng?"
    Biệt danh ngoài đời có thể đổi sang người khác ("từ nay Tí là bạn Bình"). Tham chiếu C++ **không** đổi được: đã là biệt danh của biến nào thì mãi mãi là của biến đó (mục 1). Ngoài ra, một người vẫn còn khi biệt danh bị quên, còn tham chiếu thì có thể bị gắn vào một biến đã bị dọn mất (mục 6).

## 📖 Giải thích

### 1. Tham chiếu là biệt danh

Cú pháp: thêm `&` **sau tên kiểu** ở chỗ khai báo biến.

```text
int a = 10;
int& b = a;     // b là biệt danh của a
```

Chú ý: ở [Bài 03](03-con-tro-co-ban.md), `&a` (dấu `&` đứng **trước một biến**, trong biểu thức) nghĩa là "địa chỉ của `a`". Ở đây `int&` (dấu `&` đứng **sau tên kiểu**, trong khai báo) nghĩa là "tham chiếu". Cùng một ký tự, hai vai trò khác nhau, nhìn vị trí để phân biệt.

Sau dòng đó, `a` và `b` là **hai tên của cùng một ô nhớ**, không có ô nhớ thứ hai:

```text
        ô nhớ ở 0x1000 (địa chỉ minh họa)
        +----+
 a ---> | 10 | <--- b
        +----+
```

Tham chiếu có ba luật (ví dụ 1 ở phần 💻 bên dưới chạy thật điều này, cứ đọc tiếp):

- **Phải gắn ngay lúc khai báo.** `int& b;` (không gắn vào gì) là lỗi biên dịch.
- **Không có "tham chiếu rỗng".** Không có `nullptr` cho tham chiếu: tham chiếu hợp lệ luôn là biệt danh của một biến có thật.
- **Không gắn lại sang biến khác.** Viết `b = c;` không có nghĩa "từ nay `b` là biệt danh của `c`". Nó có nghĩa **gán giá trị của `c` vào ô nhớ mà `b` đang đại diện**, tức là gán vào `a`.

!!! warning "Hay nhầm"
    `b = c;` trông như "đổi `b` sang trỏ vào `c`", nhưng thực tế nó chép giá trị của `c` vào `a`. Sau dòng này `a`, `b` vẫn là một ô, `c` vẫn là ô riêng, chỉ là `a` và `b` mang giá trị mới.

### 2. Tham chiếu và con trỏ

Cả hai đều cho ta "sửa biến của người khác", nhưng khác nhau về cách dùng:

| | Con trỏ `int*` | Tham chiếu `int&` |
|---|---|---|
| Là gì | Một biến chứa địa chỉ (tờ giấy ghi số ngăn) | Một **tên khác** của biến có sẵn |
| Có thể rỗng (`nullptr`)? | Có | Không |
| Phải gán lúc khai báo? | Không bắt buộc (nhưng nên) | Bắt buộc |
| Đổi sang đối tượng khác? | Được (`p = &c;`) | Không (`b = c;` là gán giá trị) |
| Cách dùng giá trị | Phải viết `*p` | Viết thẳng tên `b` |
| Cách đưa vào hàm | Nơi gọi viết `&a` | Nơi gọi viết thẳng `a` |

Ở hàng cuối, tham chiếu gọn hơn: nơi gọi không cần `&`, bên trong hàm không cần `*`.

!!! info "Bạn biết Go?"
    Go truyền **mọi thứ theo giá trị**: bạn đã quen `func f(x int)` chỉ sửa bản sao, và muốn sửa bản gốc thì truyền `*int`. Cái mà người ta hay gọi là "reference" trong Go thực ra là con trỏ, hoặc slice, map, channel (bên trong chúng có chứa con trỏ nên bản sao vẫn nhìn thấy dữ liệu chung). Go không có thứ gì tương đương tham chiếu C++, và `const` của Go chỉ dành cho hằng số lúc biên dịch: Go không có cách nào đánh dấu "tham số này không được sửa".

### 3. `const`: nhãn "chỉ được xem"

Viết `const` trước một khai báo để cam kết không sửa nó:

```text
const int x = 5;
x = 6;              // lỗi biên dịch
```

`const` đi cùng con trỏ thì có **hai thứ** có thể bị khóa: món đồ mà con trỏ trỏ tới, và chính tờ giấy (con trỏ). Vị trí chữ `const` quyết định khóa cái nào. Mẹo đọc: **đọc từ phải sang trái**.

| Khai báo | Đọc từ phải sang trái | Sửa được gì? |
|---|---|---|
| `const int* p` | p là con trỏ tới int hằng | Đổi `p` sang chỗ khác: được. Sửa `*p`: **không** |
| `int* const q` | q là hằng con trỏ tới int | Sửa `*q`: được. Đổi `q` sang chỗ khác: **không** |
| `const int* const r` | r là hằng con trỏ tới int hằng | Cả hai đều **không** |

Hình dung: `const int*` là "tờ giấy được viết lại số ngăn khác, nhưng món đồ ở chỗ nó trỏ tới dán nhãn *chỉ xem*". `int* const` là "tờ giấy bị dán keo không ghi lại được, nhưng món đồ vẫn sửa được". Ví dụ 2 ở phần 💻 bên dưới chứng minh từng hàng, cứ đọc tiếp.

Tham chiếu cũng có `const`: `const int& t = a;` nghĩa là "t là biệt danh của `a`, nhưng qua cái tên `t` chỉ được xem". Bản thân `a` vẫn sửa được qua tên `a`.

### 4. Bốn cách truyền tham số cho hàm

Muốn đưa một món đồ cho hàm, bạn có bốn cách. Để thấy khác biệt, ta dùng một struct có **hàm tạo sao chép** (copy constructor).

**Hàm tạo sao chép là gì?** Nó là một hàm tạo ([Bài 02](02-stack-heap-static.md)) đặc biệt, **chạy mỗi khi C++ tạo một bản sao** của đối tượng cùng kiểu. Nó nhận đối tượng gốc làm tham số, kiểu `const Cay&`. Bình thường bạn không cần tự viết (trình biên dịch tự sinh ra một hàm chép từng trường), nhưng ở đây ta viết để nó in chữ `copy!`, và nhờ vậy **đếm được số lần sao chép**.

Bốn hàm, bốn cách truyền (đọc các dòng đánh số trong code):

- **Theo giá trị** `Cay c`: hàm nhận một bản sao, nên hàm tạo sao chép chạy.
- **Bằng con trỏ** `const Cay* c`: hàm nhận địa chỉ, không sao chép đối tượng.
- **Bằng tham chiếu** `const Cay& c`: hàm nhận biệt danh, không sao chép, và có `const` nên chỉ xem.
- **Bằng tham chiếu không `const`** `Cay& c`: hàm nhận biệt danh và **sửa được** đối tượng gốc.

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {                                  // (1)
        cao = c;
    }
    Cay(const Cay& khac) {                        // (2)
        cao = khac.cao;
        std::cout << "copy!\n";
    }
};

void docTheoGiaTri(Cay c) {                       // (3)
    std::cout << "theo gia tri: " << c.cao << "\n";
}
void docBangConTro(const Cay* c) {                // (4)
    std::cout << "bang con tro: " << c->cao << "\n";
}
void docBangThamChieu(const Cay& c) {             // (5)
    std::cout << "bang tham chieu: " << c.cao << "\n";
}
void suaBangThamChieu(Cay& c) {                   // (6)
    c.cao = c.cao + 1;
}

int main() {
    Cay cay(7);
    std::cout << "--- 1\n";
    docTheoGiaTri(cay);
    std::cout << "--- 2\n";
    docBangConTro(&cay);
    std::cout << "--- 3\n";
    docBangThamChieu(cay);
    std::cout << "--- 4\n";
    suaBangThamChieu(cay);
    std::cout << "cao sau khi sua: " << cay.cao << "\n";
    return 0;
}
```

(1) là hàm tạo thường: tạo `Cay` từ một số. (2) là hàm tạo sao chép. Tên `khac` là tên mình đặt, nghĩa là "đối tượng kia, cái đang được chép". Các dòng `"--- 1"`... chỉ để chia output cho dễ đọc.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `Cay cay(7);` | Gọi hàm tạo (1): tạo `cay` với `cao` = 7 (không phải sao chép, không in gì) | `cay` ở 0x1000, `cao` = 7 (địa chỉ minh họa, máy bạn sẽ in số khác) |
| in `--- 1` | Đánh dấu bắt đầu phép thử 1 | không đổi |
| `docTheoGiaTri(cay);` | Gọi (3): để tạo tham số `c`, C++ chạy hàm tạo sao chép (2) | `c` ở 0x0f00 là **bản sao** có `cao` = 7; `cay` vẫn ở 0x1000 |
| in `copy!` | Hàm (2) in chữ này | in `copy!` |
| in `theo gia tri: 7` | Thân hàm (3) đọc `c.cao` | in `theo gia tri: 7` |
| hết hàm | Bản sao `c` bị dọn | chỉ còn `cay` ở 0x1000 |
| in `--- 2` | Đánh dấu phép thử 2 | không đổi |
| `docBangConTro(&cay);` | Gọi (4): `c` chỉ là tờ giấy ghi 0x1000, **không** có bản sao | `c` ở 0x0f00 = 0x1000 ---> `cay` |
| in `bang con tro: 7` | Đi theo `c->` tới `cay` rồi đọc | in `bang con tro: 7` |
| in `--- 3` | Đánh dấu phép thử 3 | không đổi |
| `docBangThamChieu(cay);` | Gọi (5): `c` là biệt danh của `cay`, không có bản sao | `cay` ở 0x1000 có thêm tên `c` |
| in `bang tham chieu: 7` | Đọc qua `c` | in `bang tham chieu: 7` |
| in `--- 4` | Đánh dấu phép thử 4 | không đổi |
| `suaBangThamChieu(cay);` | Gọi (6): `c` là biệt danh, `c.cao = c.cao + 1` sửa chính `cay` | `cay.cao` = 8 |
| in cuối | In `cay.cao` | in `cao sau khi sua: 8` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`):

```text
--- 1
copy!
theo gia tri: 7
--- 2
bang con tro: 7
--- 3
bang tham chieu: 7
--- 4
cao sau khi sua: 8
```

Chữ `copy!` xuất hiện **đúng một lần**, ở cách truyền theo giá trị. Ba cách còn lại không tạo bản sao nào, và chỉ cách cuối (tham chiếu không `const`) sửa được `cay`.

**Thử thay đổi 1: ở (5) đổi `const Cay& c` thành `Cay c`.** Mình đã chạy: số chữ `copy!` thành **2** (phép thử 1 và phép thử 3 đều sao chép).

**Thử thay đổi 2: trong (5) thay dòng in bằng `c.cao = 0;`.** Mình đã thử, không biên dịch được:

```text
error: assignment of member ‘Cay::cao’ in read-only object
```

`const Cay&` là lời hứa "chỉ xem", và trình biên dịch giữ lời hứa đó giúp bạn. Làm y như vậy ở (4) với `c->cao = 0;` thì có cùng lỗi.

!!! info "Vì sao sao chép là chuyện đáng bận tâm?"
    `Cay` này chỉ có một số `int`, nên sao chép rẻ. Nhưng một đối tượng chứa mảng lớn thì mỗi lần truyền theo giá trị là một lần chép cả mảng, và hàm tạo sao chép của nó còn có thể làm việc nặng. Vì thế quy tắc thông dụng: **đối tượng to thì truyền `const&`** (chỉ đọc) hoặc `&` (cần sửa); kiểu nhỏ như `int`, `double` thì truyền theo giá trị là đủ.

### 5. `const&` nhận được cả giá trị tạm

**Giá trị tạm (temporary)** là một giá trị không có tên, chỉ tồn tại trong một câu lệnh: số `5` viết thẳng trong code, hay kết quả `a + 1`. Nó không phải một biến, nên không có ô nhớ "của ai" để mà sửa.

Hàm nhận `int&` (không `const`) là hàm cam kết **có thể sửa** tham số. Đưa `5` vào thì hàm sẽ sửa cái gì? Nên C++ cấm.

Còn hàm nhận `const int&` chỉ xem, nên C++ cho phép và giữ giá trị tạm sống suốt lúc hàm chạy. Đó là lý do `const T&` là cách viết "nhận mọi thứ để xem" phổ biến nhất.

```cpp
#include <iostream>

void docTheoThamChieu(const int& x) {
    std::cout << "x = " << x << "\n";
}

int main() {
    int a = 3;
    docTheoThamChieu(a);              // (1)
    docTheoThamChieu(5);              // (2)
    docTheoThamChieu(a + 1);          // (3)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int a = 3;` | Tạo biến `a` | `a` ở 0x1000 = 3 (địa chỉ minh họa) |
| (1) `docTheoThamChieu(a)` | `x` là biệt danh của `a` | `a` có thêm tên `x` |
| in | In `x` | in `x = 3` |
| (2) `docTheoThamChieu(5)` | `5` là giá trị tạm; C++ giữ nó ở một chỗ tạm cho `x` đại diện | chỗ tạm ở 0x0f00 = 5, `x` là tên của nó |
| in | In `x` | in `x = 5` |
| (3) `docTheoThamChieu(a + 1)` | Kết quả `a + 1` (4) là giá trị tạm khác | chỗ tạm = 4 |
| in | In `x` | in `x = 4` |

**Kết quả khi chạy:**

```text
x = 3
x = 5
x = 4
```

**Thử thay đổi: đổi dòng khai báo thành `void docTheoThamChieu(int& x)` (bỏ `const`) rồi giữ nguyên lời gọi (2) `docTheoThamChieu(5)`.** Mình đã thử, không biên dịch được:

```text
error: cannot bind non-const lvalue reference of type ‘int&’ to an rvalue of type ‘int’
```

Giải nghĩa câu báo lỗi: "bind" là "gắn"; "lvalue" là giá trị có tên như biến `a`; "rvalue" là giá trị tạm như `5` ([Bài 12](12-move-semantics.md) nói kỹ). Nghĩa là không gắn được tham chiếu không `const` vào giá trị tạm. Lời gọi (1) `docTheoThamChieu(a)` với biến `a` thì vẫn hợp lệ.

### 6. Đừng trả về tham chiếu tới biến cục bộ

Quay lại [Bài 02](02-stack-heap-static.md): biến cục bộ nằm trên "bàn học" của hàm, và khi hàm xong, bàn bị dọn. Nếu hàm **trả về một tham chiếu** tới biến cục bộ, nơi gọi nhận một biệt danh của món đồ vừa bị dọn khỏi bàn. Nó trỏ vào chỗ không còn là của biến đó.

```cpp
// bo-qua-kiem-tra
#include <iostream>

int& hong() {
    int x = 42;
    return x;                 // sai: x sẽ bị dọn khi hàm kết thúc
}

int main() {
    int& r = hong();
    std::cout << r << "\n";   // đọc chỗ đã bị dọn
    return 0;
}
```

Chương trình này **biên dịch được**, nhưng `g++ -Wall` cảnh báo ngay:

```text
warning: reference to local variable ‘x’ returned [-Wreturn-local-addr]
```

Khi chạy, kết quả không được chuẩn bảo đảm (hành vi không xác định): mình chạy thử một lần thì chương trình sập (mã thoát 139, nghĩa là hệ điều hành đã dừng nó vì truy cập sai bộ nhớ), máy bạn có thể in số rác hoặc `42`, và không ai hứa lần sau giống lần này. Tên gọi "con trỏ treo / tham chiếu treo" cho loại lỗi này sẽ được học kỹ ở [Bài 07](07-new-delete.md). Tin tốt: trả về tham chiếu tới thứ **sống lâu hơn hàm** (đối tượng của nơi gọi, biến static, vùng nhớ ở heap) thì không sao.

!!! info "Bạn biết Go?"
    Trong Go, `return &x` với `x` cục bộ là hợp lệ: bộ phân tích thoát (escape analysis) chuyển `x` lên heap và garbage collector dọn sau. C++ không có bước tự cứu đó, nên cùng ý định ấy là lỗi.

### 7. Hàm thành viên `const` (nhắc ngắn)

Một struct có thể chứa hàm viết bên trong nó, gọi là **hàm thành viên**, và gọi bằng `cay.doc()`. Chữ `const` đặt **sau** danh sách tham số là cam kết "hàm này không sửa đối tượng". Chỉ hàm có cam kết đó mới gọi được qua một đối tượng `const` hoặc `const&`; bài sau sẽ dùng cú pháp này.

```text
struct Cay {
    int cao;
    int doc() const { return cao; }       // chỉ xem: gọi được qua const Cay&
    void tang() { cao = cao + 1; }        // có sửa: không gọi được qua const Cay&
};
```

## 💻 Ví dụ code

### Ví dụ 1: tham chiếu là biệt danh

```cpp
#include <iostream>

int main() {
    int a = 10;
    int& b = a;                                   // (1)
    b = 20;                                       // (2)
    std::cout << "a = " << a << ", b = " << b << "\n";
    std::cout << "&a = " << &a << ", &b = " << &b << "\n";
    std::cout << "sizeof(a) = " << sizeof(a) << ", sizeof(b) = " << sizeof(b) << "\n";

    int c = 99;
    b = c;                                        // (3)
    c = 5;                                        // (4)
    std::cout << "a = " << a << ", b = " << b << ", c = " << c << "\n";
    std::cout << "(&b == &a) = " << (&b == &a) << ", (&b == &c) = " << (&b == &c) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int a = 10;` | Tạo `a` | `a` ở 0x1000 = 10 (địa chỉ minh họa, máy bạn sẽ in số khác) |
| (1) `int& b = a;` | `b` là biệt danh của `a`, **không** tạo ô nhớ mới | ô 0x1000 = 10, có hai tên: `a`, `b` |
| (2) `b = 20;` | Ghi 20 qua tên `b`, chính là ghi vào ô của `a` | ô 0x1000 = 20 |
| in 3 dòng | `a` và `b` cùng 20; `&a` và `&b` là **cùng một địa chỉ**; `sizeof` cùng là 4 | xem kết quả |
| `int c = 99;` | Tạo `c`, ô riêng | `c` ở 0x1004 = 99 |
| (3) `b = c;` | Không gắn lại. Chép giá trị của `c` (99) vào ô mà `b` đại diện, tức ô của `a` | ô 0x1000 = 99 (`a`, `b`); `c` = 99 |
| (4) `c = 5;` | Sửa riêng `c` | ô 0x1000 vẫn 99; `c` = 5 |
| in 2 dòng | `a = 99, b = 99, c = 5`; `&b == &a` đúng, `&b == &c` sai | xem kết quả |

**Kết quả khi chạy:**

```text
a = 20, b = 20
&a = 0x7ffe16cbfe68, &b = 0x7ffe16cbfe68
sizeof(a) = 4, sizeof(b) = 4
a = 99, b = 99, c = 5
(&b == &a) = 1, (&b == &c) = 0
```

Địa chỉ ở máy bạn sẽ khác số trên; chỉ cần `&a` và `&b` **bằng nhau**. Ở dòng cuối, `1` nghĩa là đúng, `0` là sai.

Dòng 2 xác nhận "một ô nhớ hai tên". Dòng 4 cho thấy `b = c;` không gắn lại `b`: sau đó `c = 5` không kéo `a`, `b` theo, vì `b` chưa bao giờ là biệt danh của `c`.

**Thử thay đổi: bỏ phần gắn, viết `int& b;`.** Mình đã thử, không biên dịch được:

```text
error: ‘b’ declared as reference but not initialized
```

Tham chiếu phải được gắn ngay lúc khai báo.

!!! question "Hỏi nhanh: `sizeof(b)` là 4, vậy tham chiếu không tốn chỗ à?"
    `sizeof` của một tham chiếu cho ra kích thước của thứ nó đại diện (ở đây `int`, 4 byte). Về ý nghĩa, tham chiếu **không phải một biến thứ hai**; chuẩn C++ không quy định nó có tốn bộ nhớ hay không.

### Ví dụ 2: đọc `const` với con trỏ

```cpp
#include <iostream>

int main() {
    int a = 1;
    int b = 2;
    const int* p = &a;        // (1)
    p = &b;                   // (2)
    std::cout << *p << "\n";
    int* const q = &a;        // (3)
    *q = 10;                  // (4)
    std::cout << a << "\n";
    const int* const r = &a;  // (5)
    std::cout << *r << "\n";
    const int x = 5;          // (6)
    std::cout << x << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| tạo `a`, `b` | Hai biến thường | `a` ở 0x1000 = 1, `b` ở 0x1004 = 2 (địa chỉ minh họa) |
| (1) | `p` trỏ `a`, hứa không sửa qua `p` | `p` ở 0x1008 = 0x1000 |
| (2) `p = &b;` | Đổi tờ giấy sang số ngăn khác: được phép | `p` = 0x1004 |
| in `*p` | Đọc `b` | in `2` |
| (3) | `q` trỏ `a`, bị khóa không đổi chỗ được | `q` ở 0x100c = 0x1000 |
| (4) `*q = 10;` | Sửa món đồ: được phép | `a` = 10 |
| in `a` | In `a` | in `10` |
| (5) | `r` trỏ `a`, khóa cả hai | `r` ở 0x1010 = 0x1000 |
| in `*r` | Đọc `a` qua `r` | in `10` |
| (6) `const int x = 5;` | Tạo hằng `x` | `x` ở 0x1014 = 5 |
| in `x` | In `x` | in `5` |

**Kết quả khi chạy:**

```text
2
10
10
5
```

**Thử thay đổi:** mỗi lần thêm đúng **một** dòng "cố sửa" (bên dưới) vào `main`, mình đã biên dịch và đây là lỗi thật của `g++`, rút gọn:

```text
const int x = 5;   x = 6;
error: assignment of read-only variable ‘x’

const int* p = &a;   *p = 7;
error: assignment of read-only location ‘* p’

int* const q = &a;   q = &b;
error: assignment of read-only variable ‘q’

const int* const r = &a;   *r = 7;
error: assignment of read-only location ‘*(const int*)r’

const int* const r = &a;   r = &b;
error: assignment of read-only variable ‘r’

const int& t = a;   t = 3;
error: assignment of read-only reference ‘t’
```

Khối trên không phải một chương trình để biên dịch, chỉ là danh sách "thử một dòng, nhận một lỗi". Điều cần thấy: `const int*` cấm **sửa `*p`** nhưng cho đổi `p`; `int* const` cấm **đổi `q`** nhưng cho sửa `*q`; bản `const int* const` cấm cả hai.

Gán `const int*` cho `int*` (bỏ nhãn "chỉ xem") cũng bị chặn: `error: invalid conversion from ‘const int*’ to ‘int*’`. Chiều ngược lại (`int*` gán cho `const int*`) thì được.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Tham chiếu và con trỏ khác nhau thế nào?"
    Tham chiếu là một **tên khác** của một đối tượng có sẵn: phải gắn ngay lúc khai báo, không thể rỗng, không thể gắn lại sang đối tượng khác, và dùng thẳng như tên biến. Con trỏ là một **biến riêng** chứa địa chỉ: có thể là `nullptr`, đổi trỏ sang chỗ khác được, và phải giải tham chiếu bằng `*`. Muốn "có thể không có đối tượng" hoặc muốn đổi đối tượng đang trỏ thì dùng con trỏ; còn lại tham chiếu gọn và an toàn hơn.

??? question "Vì sao hay viết `const T&` cho tham số hàm?"
    Truyền `T&` thay vì `T` tránh sao chép một đối tượng có thể lớn, và `const` hứa hàm không sửa nó, nên nơi gọi yên tâm và trình biên dịch kiểm tra giúp. Thêm nữa, `const T&` nhận được cả giá trị tạm như `5` hay kết quả của một biểu thức, còn `T&` thì không. Với kiểu nhỏ như `int` thì truyền theo giá trị là đủ và thường không chậm hơn.

??? question "`const int*` khác `int* const` thế nào?"
    Đọc từ phải sang trái. `const int*` là con trỏ tới `int` hằng: không sửa được giá trị qua con trỏ, nhưng đổi con trỏ sang chỗ khác được. `int* const` là hằng con trỏ tới `int`: sửa giá trị qua con trỏ được, nhưng không đổi con trỏ sang chỗ khác. `const int* const` khóa cả hai.

??? question "Tham chiếu có thể null không?"
    Không. Tham chiếu hợp lệ luôn gắn với một đối tượng có thật, và không có cú pháp "tham chiếu rỗng". Có thể cố tình tạo ra nó bằng cách viết `int& r = *p;` với `p == nullptr`, nhưng đó là hành vi không xác định, nên chương trình đúng không bao giờ làm vậy. Khi cần biểu diễn "không có", dùng con trỏ.

??? question "Có thể trả về tham chiếu tới biến cục bộ không?"
    Không: biến cục bộ bị dọn khi hàm kết thúc, tham chiếu trả ra sẽ gắn vào chỗ đã hết hiệu lực, và dùng nó là hành vi không xác định (trình biên dịch thường cảnh báo, ví dụ `-Wreturn-local-addr`). Chỉ trả về tham chiếu tới thứ sống lâu hơn hàm, như đối tượng nhận qua tham số tham chiếu, biến static hay vùng nhớ heap. Nếu cần trả về giá trị mới thì trả theo giá trị.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng `b = c;` gắn lại tham chiếu"
    Tham chiếu gắn một lần duy nhất lúc khai báo. Sau đó `b = c;` chép giá trị của `c` vào biến gốc (ví dụ 1). Muốn "đổi sang đối tượng khác" thì phải dùng con trỏ.

!!! warning "Lỗi 2: Sửa tham số `const&` hoặc gọi hàm không `const` qua nó"
    `const Cay&` chỉ cho xem: gán trường hay gọi hàm thành viên không `const` đều là lỗi biên dịch (mục 4 và 7). Muốn hàm sửa được thì bỏ `const`, và chỉ làm vậy khi hàm thật sự cần sửa.

!!! warning "Lỗi 3: Trả về tham chiếu tới biến cục bộ"
    `int& f() { int x = 1; return x; }` biên dịch được (có thể chỉ kèm cảnh báo) nhưng sai: `x` bị dọn khi hàm xong (mục 6). Nếu `g++` cảnh báo `-Wreturn-local-addr` thì sửa ngay, đừng bỏ qua.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="06" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Với `int a = 10; int& b = a;` thì "`b` là biệt danh của `a`" nghĩa là gì?

- `b` là một biến mới, chép giá trị của `a`
- `b` và `a` là hai tên khác nhau của cùng một ô nhớ
- `b` là con trỏ, tự lưu địa chỉ của `a`
- `b` là một bản sao mà sau này tự theo kịp `a`

<p class="giai-thich" markdown>Biệt danh nghĩa là không có ô nhớ thứ hai: đọc hay ghi qua `b` là đọc hay ghi chính ô của `a`, và `&a` bằng `&b` (ví dụ 1). Nếu `b` là biến mới chép giá trị thì sửa `a` sẽ không làm `b` đổi theo. Tham chiếu không phải con trỏ: bạn viết thẳng `b`, không cần `*b`. Và không có bản sao nào "tự theo kịp", vì ngay từ đầu chỉ có một ô.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
int a = 1; int c = 2; int& b = a; b = c; c = 3;
std::cout << a << " " << b << " " << c;
```

- `1 1 3`, vì phép gán `b = c` chỉ đổi tên của `b`
- `3 3 3`, vì `b` gắn sang `c`
- `2 2 3`, vì `b = c` gán giá trị vào `a`
- `1 2 3`, vì `b` giữ giá trị riêng

<p class="giai-thich" markdown>`b = c;` không gắn lại tham chiếu, mà chép giá trị 2 của `c` vào ô mà `b` đại diện, tức ô của `a`. Vậy `a` và `b` đều là 2; `c = 3` sau đó chỉ đổi `c`. Kết quả `3 3 3` chỉ đúng nếu `b` đã đổi sang làm biệt danh của `c`, mà tham chiếu không đổi được. Kết quả `1 1 3` bỏ quên rằng `a` đã nhận giá trị mới. Còn `1 2 3` cần `b` là biến riêng, trong khi `b` và `a` là một ô (mình đã chạy: `2 2 3`).</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Với `const int* p = &a;`, điều nào sau đây ĐÚNG?

- Đổi `p` được, còn sửa `*p` thì không
- Sửa `*p` được, còn đổi `p` thì không
- Cả đổi `p` lẫn sửa `*p` đều không được
- Cả đổi `p` lẫn sửa `*p` đều được

<p class="giai-thich" markdown>Đọc từ phải sang trái: `p` là con trỏ tới `int` hằng. Món đồ bị khóa (`*p = 7;` lỗi `assignment of read-only location`), còn tờ giấy `p` thì ghi lại số ngăn khác được. Phương án "sửa `*p` được mà không đổi `p`" là của `int* const`, tức bị ngược. Phương án khóa cả hai là của `const int* const`, còn phương án không khóa gì là con trỏ thường `int*`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn code sau. Dòng nào gây lỗi biên dịch?

```text
int a = 1; int b = 2;
int* const q = &a;   // dòng A
*q = 10;             // dòng B
q = &b;              // dòng C
```

- Dòng A, vì không được khai báo `const` sau dấu `*`
- Dòng B, vì `q` bị khóa nên `*q` không sửa được
- Cả dòng B và dòng C, vì `q` bị khóa hết
- Chỉ dòng C, vì `q` là hằng nên không thể gán lại được

<p class="giai-thich" markdown>`int* const q` đọc là "q là hằng con trỏ tới int": chính `q` bị khóa, còn món đồ nó trỏ tới thì không. Nên `*q = 10;` hợp lệ, và chỉ `q = &b;` lỗi `assignment of read-only variable ‘q’` (mình đã biên dịch). Dòng A đúng cú pháp: `const` đứng sau `*` là một dạng hợp lệ. Dòng B là phương án bị nhầm với `const int*`, kiểu mà `*p` mới bị khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn code sau (`Cay` có hàm tạo sao chép in `copy!`). Nó in `copy!` mấy lần?

```text
void f(Cay c) {}
void g(const Cay& c) {}
void h(Cay* c) {}
Cay x(1);  f(x);  g(x);  h(&x);  f(x);
```

- 4 lần, vì cả bốn lời gọi hàm đều sao chép
- 2 lần, vì chỉ hai lần gọi `f` sao chép
- 1 lần, vì chỉ lần gọi đầu mới chép
- 0 lần, vì `x` đã tồn tại sẵn rồi

<p class="giai-thich" markdown>Chỉ truyền theo giá trị (`f`) tạo bản sao, và `f` được gọi hai lần nên có hai lần `copy!` (mình đã chạy). `g` nhận biệt danh còn `h` nhận địa chỉ, nên không lần nào sao chép. Không có chuyện "chỉ lần đầu mới sao chép": mỗi lần gọi `f` đều tạo tham số mới. Việc `x` đã tồn tại không ngăn sao chép, vì tham số `c` của `f` là một biến mới.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Với `void xem(const int& v)` và `void sua(int& v)`, cặp lời gọi nào đúng?

- `xem(5)` hợp lệ, `sua(5)` lỗi
- Cả `xem(5)` lẫn `sua(5)` đều hợp lệ
- `sua(5)` hợp lệ, `xem(5)` lỗi
- Cả `xem(5)` lẫn `sua(5)` đều lỗi

<p class="giai-thich" markdown>`const int&` chỉ xem, nên được phép gắn vào giá trị tạm `5` (C++ giữ giá trị tạm sống suốt lúc hàm chạy). `int&` cam kết có thể sửa, mà `5` không phải biến có chỗ để sửa, nên `g++` báo `cannot bind non-const lvalue reference`. Chiều ngược lại không thể đúng: `const` là lời hứa không sửa, nên nó nới lỏng điều kiện chứ không siết thêm. Vì vậy `xem(5)` hợp lệ, nên hai phương án cho rằng `xem(5)` lỗi đều sai.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Vì sao `int& f() { int x = 1; return x; }` là sai?

- Vì tham chiếu không được dùng làm kiểu trả về
- Vì `x` chưa khai báo `const` nên không trả được
- Vì muốn trả địa chỉ thì chỉ được dùng con trỏ
- Vì `x` bị dọn khi `f` xong, tham chiếu hỏng

<p class="giai-thich" markdown>`x` là biến cục bộ, nằm trên "bàn học" của `f` và bị dọn khi `f` kết thúc, nên tham chiếu trả ra gắn vào chỗ không còn là của `x`: dùng nó là hành vi không xác định. Tham chiếu hoàn toàn được làm kiểu trả về, nếu nó gắn vào thứ sống lâu hơn hàm (ví dụ biến của nơi gọi). Thêm `const` cho `x` không cứu được, vì `x` vẫn bị dọn. Trả về con trỏ tới `x` cũng bị y như vậy, nên đổi sang con trỏ không giải quyết gì.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Tham chiếu `int& b = a;` là biệt danh: hai tên của một ô nhớ, phải gắn lúc khai báo, không rỗng, và `b = c;` là gán giá trị chứ không gắn lại.
2. Con trỏ có thể rỗng và đổi chỗ trỏ, dùng qua `*p`; tham chiếu dùng thẳng như tên biến, nơi gọi không cần `&`.
3. Truyền theo giá trị tạo bản sao (hàm tạo sao chép chạy); truyền con trỏ, `const&` hay `&` thì không sao chép, và chỉ `&` hoặc con trỏ không `const` mới sửa được bản gốc.
4. `const` đọc từ phải sang trái: `const int*` khóa giá trị, `int* const` khóa con trỏ, `const int* const` khóa cả hai; `const T&` còn nhận được giá trị tạm, còn `T&` thì không.
5. Không trả về tham chiếu tới biến cục bộ, vì biến đó bị dọn khi hàm kết thúc; hàm thành viên `const` hứa không sửa đối tượng.
