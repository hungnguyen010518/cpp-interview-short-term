# Bài 01 — Chương trình C++ đầu tiên, bộ nhớ, byte và địa chỉ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết, biên dịch và chạy được chương trình C++ ngắn nhất, và hiểu từng dòng của nó.
    - Hình dung bộ nhớ như một dãy ngăn có số thứ tự, mỗi ngăn đựng đúng một byte.
    - Biết một biến gồm bốn thứ (tên, kiểu, giá trị, địa chỉ) và in được kích thước lẫn địa chỉ của biến.

## 🧠 Câu chuyện mở đầu

Hãy tưởng tượng một dãy tủ khóa dài vô tận, xếp thành một hàng thẳng. Mỗi ngăn tủ chỉ đựng được **một thứ nhỏ xíu** (ta sẽ gọi nó là một *byte*). Mỗi ngăn có một **số thứ tự** ghi ngoài cửa: ngăn 1000, ngăn 1001, ngăn 1002…

Số thứ tự đó gọi là **địa chỉ (address)**. Muốn lấy đồ ra hay cất đồ vào, bạn không cần biết trong ngăn có gì. Bạn chỉ cần biết số của ngăn.

Chương trình của bạn đứng trước dãy tủ đó. Mỗi lần bạn khai báo một **biến**, thực chất bạn làm hai việc: chọn một hay vài ngăn **liền nhau**, rồi dán lên đó một mảnh giấy ghi **tên** của biến và ghi **loại đồ** nó đựng (số nguyên, chữ cái, số thực…).

Cả bài này chỉ xoay quanh hình ảnh đó. Nhưng trước khi nhìn vào dãy tủ, ta cần một chương trình chạy được để thực hành. Ta bắt đầu từ đó.

!!! info "Chỗ nào ví dụ tủ khóa không còn đúng?"
    Trong máy thật, các "số ngăn" là con số mà *chương trình nhìn thấy*. Hệ điều hành mới là bên quyết định ngăn đó nằm ở đâu trong phần cứng, và bạn không cần quan tâm. Ta cũng chưa nói tới chuyện "tủ nào dùng để làm gì". Phần đó để dành cho các bài sau.

## 📖 Giải thích

### 1. Chương trình C++ ngắn nhất

Một chương trình in ra chữ `Xin chao` rồi kết thúc. Bạn hãy chép nó vào một file tên `bai.cpp` (đuôi `.cpp` báo cho máy biết đây là mã C++).

```cpp
#include <iostream>

int main() {
    std::cout << "Xin chao" << "\n";
    return 0;
}
```

Nếu bạn đã quen Go, đây là phiên bản tương ứng để so sánh:

```go
package main

import "fmt"

func main() {
    fmt.Println("Xin chao")
}
```

Ta đi từng dòng của bản C++.

**`#include <iostream>`**

- Dòng này nói: "hãy chép vào đây bộ công cụ nhập/xuất của thư viện chuẩn (bộ công cụ có sẵn, đi kèm C++)". `iostream` là viết tắt của *input/output stream* (luồng nhập/xuất).
- Nó giống `import "fmt"` trong Go: muốn in chữ ra màn hình thì phải nói trước là bạn cần công cụ in.
- Dòng bắt đầu bằng `#` là chỉ thị gửi cho trình biên dịch (chương trình dịch mã bạn viết thành file máy chạy được, xem mục 2), **không có dấu `;` ở cuối**.

**`int main() {`**

- `main` là tên hàm mà hệ điều hành gọi đầu tiên khi chạy chương trình. Giống `func main()` của Go.
- `int` đứng trước tên hàm có nghĩa là hàm này **trả về một số nguyên**. Số nguyên đó là "mã thoát" (exit code) mà chương trình báo lại cho hệ điều hành. Số `0` nghĩa là "mọi thứ ổn".
- `()` rỗng nghĩa là `main` ở đây không nhận tham số nào.

**`{` và `}`**

- Cặp ngoặc nhọn bao quanh thân hàm: mọi thứ từ `{` đến `}` thuộc về hàm `main`. Giống Go.

**`std::cout << "Xin chao" << "\n";`**

- `cout` là "cổng ra" của chương trình, nối với màn hình (tên là *console output*, đầu ra của console).
- `std::` đọc là "của họ `std`". `std` là viết tắt của *standard* (chuẩn). Thư viện chuẩn của C++ đặt mọi tên của nó vào "họ" `std`, để không đụng tên với code bạn tự viết. `std::cout` nghĩa là "`cout` thuộc họ `std`". Dấu `::` đọc là "thuộc về". Nó cùng vai trò với `fmt.` trong `fmt.Println`: `fmt` là "họ" của `Println`.
- `<<` là một **toán tử** (ký hiệu thực hiện một phép trên dữ liệu, mục 5 nói thêm), đọc là "đẩy vào". Phần trong nháy kép như `"Xin chao"` là một **chuỗi chữ**, được in ra đúng từng ký tự. `std::cout << "Xin chao"` nghĩa là đẩy chữ `Xin chao` vào cổng ra. Bạn có thể nối nhiều `<<` liền nhau, và chúng được đẩy ra theo thứ tự từ trái sang phải.
- `"\n"` là ký tự xuống dòng. Khác với `fmt.Println` của Go (tự thêm xuống dòng), `std::cout` **không** tự thêm. Bạn phải tự đẩy `"\n"` vào.
- `;` kết thúc câu lệnh. Go tự điền `;` giúp bạn khi xuống dòng, còn C++ thì **không**. Quên `;` là lỗi biên dịch.

**`return 0;`**

- Kết thúc `main` và trả về `0`, tức "ổn". Riêng với `main`, C++ cho phép bỏ dòng này (khi đó nó tự hiểu là `return 0;`). Trong khóa này ta vẫn viết ra cho rõ.

### 2. Biên dịch và chạy

Từ mã nguồn đến lúc thấy chữ hiện ra có hai bước: mã nguồn → (bước **biên dịch**, do **trình biên dịch (compiler)** làm) → file chạy được → (bước **chạy** file đó). Go có `go run` gộp hai bước làm một; trong C++ ta tự nối hai bước bằng `&&` trên cùng một dòng lệnh:

```bash
g++ -std=c++17 -Wall -o bai bai.cpp && ./bai
```

| Phần của lệnh | Ý nghĩa |
|---|---|
| `g++` | Trình biên dịch C++ (cần được cài sẵn trên máy bạn) |
| `-std=c++17` | Chọn phiên bản ngôn ngữ C++17 |
| `-Wall` | Bật thêm các cảnh báo (warning), giúp bắt lỗi sớm |
| `-o bai` | Đặt tên file chạy được tạo ra là `bai` |
| `bai.cpp` | File mã nguồn cần dịch |
| `&&` | "Nếu bước trước thành công thì mới làm bước sau" |
| `./bai` | Chạy file `bai` nằm ở thư mục hiện tại |

Nếu code có lỗi, bước `g++` báo lỗi và dừng, nên `./bai` không bao giờ chạy. Các lỗi như vậy gọi là **lỗi biên dịch (compile error)**.

### 3. Bit, byte và địa chỉ

Máy tính lưu mọi thứ bằng các công tắc chỉ có hai trạng thái: tắt hoặc bật, ta ghi là `0` hoặc `1`. Một công tắc như thế gọi là **bit**.

Tám bit gộp lại thành một **byte**. Vì mỗi bit có hai khả năng, một byte có `2 × 2 × … × 2` (2 nhân với chính nó 8 lần, viết là 2⁸), tức **256** tổ hợp khác nhau. Có thể dùng chúng để biểu diễn các số từ `0` đến `255`, hoặc một chữ cái, hoặc một mảnh của số lớn hơn.

**Bộ nhớ** là một dãy byte nằm liền nhau, mỗi byte có một địa chỉ. Đó chính là dãy tủ khóa: **một ngăn = một byte**.

```text
Địa chỉ:   1000   1001   1002   1003   1004   1005  ...
Ngăn:     [ 1 byte ][ 1 byte ][ 1 byte ][ 1 byte ][ 1 byte ][ 1 byte ] ...
```

**Địa chỉ viết bằng hệ 16.** Khi in địa chỉ ra, bạn sẽ thấy dạng `0x7ffc6d7bc6d0`. Đây là một con số bình thường, chỉ khác là viết trong **hệ 16 (hexadecimal)**. Hệ 16 chỉ là một cách viết số gọn hơn:

- Hệ 10 quen thuộc có 10 ký hiệu `0` đến `9`. Hệ 16 có 16 ký hiệu: `0`–`9` rồi `a`, `b`, `c`, `d`, `e`, `f` (nghĩa là 10, 11, 12, 13, 14, 15).
- Tiền tố `0x` chỉ để báo "số sau đây viết trong hệ 16".
- Ví dụ: `0x10` là 16, `0x1f` là 31, `0xff` là 255.
- Một chữ số hệ 16 tương ứng đúng 4 bit, nên hai chữ số hệ 16 vừa đủ một byte (`00` đến `ff`). Vì vậy dân lập trình thích dùng nó để viết địa chỉ và dữ liệu thô.

Bạn không cần tự đổi qua lại. Bạn chỉ cần nhận ra `0x…` là địa chỉ, và biết so hai địa chỉ ở những chữ số cuối, ví dụ `…374` trừ `…370` bằng `4`. Khi phải "mượn", cứ đếm từng bước là được (ví dụ ở ví dụ 3).

### 4. Biến có bốn thứ

Một biến trong C++ có **bốn thứ**:

| Thứ | Ví dụ với `int tuoi = 30;` |
|---|---|
| **Tên** | `tuoi` |
| **Kiểu (type)** | `int` (số nguyên) |
| **Giá trị** | `30` |
| **Địa chỉ** | số của ngăn đầu tiên mà biến chiếm, ví dụ `0x1000` |

Dòng `int tuoi = 30;` đọc là: "tạo một biến kiểu `int`, tên `tuoi`, đặt giá trị ban đầu là `30`". Nó tương ứng với `var tuoi int = 30` trong Go.

**Kiểu quyết định biến chiếm bao nhiêu ngăn (bao nhiêu byte).** Số nhỏ cần ít ngăn, số lớn hoặc số thực cần nhiều ngăn hơn. Các kiểu cơ bản bạn cần biết lúc này:

| Kiểu | Dùng để đựng | Số byte (trên máy tính thông thường) |
|---|---|---|
| `char` | một ký tự, ví dụ `'A'` | 1 (chuẩn C++ đảm bảo đúng 1) |
| `bool` | `true` hoặc `false` | thường là 1 |
| `int` | số nguyên | thường là 4 |
| `long long` | số nguyên lớn hơn | thường là 8 |
| `double` | số thực (có phần thập phân) | thường là 8 |

!!! warning "Hay nhầm: `int` luôn là 4 byte"
    **Chuẩn C++ không ép `int` phải là 4 byte.** Nó chỉ yêu cầu `int` đủ lớn tối thiểu (ít nhất 16 bit). Trên máy tính thông thường mà bạn dùng hằng ngày, `int` thường là 4 byte, nhưng đó là thói quen của phần cứng và trình biên dịch phổ biến, không phải luật. Muốn biết chắc trên máy bạn: hỏi `sizeof` (ngay bên dưới).

`char` đựng một ký tự, và ký tự viết trong **nháy đơn** `'A'`. Chuỗi chữ như `"Xin chao"` viết trong **nháy kép**. Hai thứ này khác nhau, ta sẽ gặp lại ở phần lỗi thường gặp.

### 5. `sizeof` và toán tử `&`

**`sizeof`** là một **toán tử (operator)**. Toán tử là ký hiệu hoặc từ khóa thực hiện một phép tính trên dữ liệu, như `+` hay `<<`. `sizeof(x)` cho bạn biết **số byte** mà `x` chiếm. `x` có thể là tên kiểu, ví dụ `sizeof(int)`, hoặc tên một biến, ví dụ `sizeof(tuoi)`. Kết quả có kiểu `std::size_t`, một kiểu số nguyên không âm, đủ lớn để đếm kích thước.

**`&`** đặt **trước tên biến** là toán tử "lấy địa chỉ". `&tuoi` đọc là "địa chỉ của `tuoi`", tức số của **ngăn đầu tiên** mà `tuoi` chiếm. Giống `&x` trong Go. (Dấu `&` còn có nghĩa khác ở những chỗ khác. Ở bài này nó luôn là "địa chỉ của".)

Khi in `&tuoi` bằng `std::cout`, bạn thấy một số hệ 16. Với biến kiểu `int` thì in thẳng được. Với biến kiểu `char` thì có một cái bẫy, mà ta sẽ gặp ngay trong ví dụ (và giải thích vì sao).

**Địa chỉ có thể đổi giữa các lần chạy.** Mỗi lần chạy, hệ điều hành có thể đặt chương trình của bạn vào vùng nhớ khác (nhiều hệ điều hành cố tình xáo trộn để tăng bảo mật). Vì thế `&tuoi` lần này có thể khác lần sau. Điều đó hoàn toàn bình thường, và bạn **không bao giờ nên dựa vào một con số địa chỉ cụ thể**. Cái cần để ý là **kiểu mẫu**: hai biến `int` khai báo liền nhau thường cách nhau 4, vì mỗi biến chiếm 4 ngăn.

## 💻 Ví dụ code

### Ví dụ 1: Xin chào

Chương trình ở mục 1, lần này có thêm bảng chạy từng dòng.

```cpp
#include <iostream>

int main() {
    std::cout << "Xin chao" << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `#include <iostream>` | Trình biên dịch nạp công cụ nhập/xuất (chuyện xảy ra lúc **biên dịch**, chưa chạy gì) | chưa có gì |
| `int main() {` | Hệ điều hành bắt đầu chạy chương trình từ đây | chưa có biến nào |
| `std::cout << "Xin chao" << "\n";` | Đẩy chữ `Xin chao`, rồi ký tự xuống dòng ra màn hình | không đổi (chữ chỉ đi qua, không đặt vào biến nào) |
| `return 0;` | Hàm `main` kết thúc, báo mã thoát `0` | chương trình kết thúc |

**Kết quả khi chạy** (lệnh `g++ -std=c++17 -Wall -o bai bai.cpp && ./bai`):

```text
Xin chao
```

**Thử thay đổi: bỏ dấu `;` ở dòng `std::cout`.** Nếu bạn xóa `;` cuối dòng đó, `g++` dừng lại, báo lỗi và không tạo file chạy. Mình đã thử, `g++ 11.4` báo:

```text
bai.cpp:4:36: error: expected ‘;’ before ‘return’
    4 |     std::cout << "Xin chao" << "\n"
```

Đọc thông báo: `bai.cpp:4:36` là "file `bai.cpp`, dòng 4, cột 36". `expected ‘;’` nghĩa là "mong thấy `;`". Lưu ý trình biên dịch báo ngay chỗ nó **phát hiện** ra thiếu, tức cuối dòng 4, trước chữ `return`. Khi gặp lỗi lạ, hãy xem cả dòng ngay phía trên chỗ nó trỏ tới.

### Ví dụ 2: Mỗi kiểu chiếm bao nhiêu byte?

```cpp
#include <iostream>

int main() {
    std::cout << "char:      " << sizeof(char) << "\n";        // (1)
    std::cout << "bool:      " << sizeof(bool) << "\n";
    std::cout << "int:       " << sizeof(int) << "\n";
    std::cout << "long long: " << sizeof(long long) << "\n";
    std::cout << "double:    " << sizeof(double) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `sizeof(char)` | Trình biên dịch đã biết `char` chiếm bao nhiêu byte. Chương trình đẩy chữ `char:` rồi con số đó ra màn hình | không có biến nào được tạo, ta chỉ hỏi kích thước kiểu |
| 4 dòng tiếp theo | Tương tự với `bool`, `int`, `long long`, `double` | vẫn không có biến nào |
| `return 0;` | Kết thúc | |

Để hình dung: một `int` (4 byte) chiếm 4 ngăn liền nhau, một `long long` (8 byte) chiếm 8 ngăn liền nhau (địa chỉ minh họa):

```text
int:        [0x1000][0x1001][0x1002][0x1003]
long long:  [0x2000][0x2001][0x2002][0x2003][0x2004][0x2005][0x2006][0x2007]
```

**Kết quả khi chạy** (máy của mình: `g++ 11.4`, Linux 64 bit):

```text
char:      1
bool:      1
int:       4
long long: 8
double:    8
```

Con số này là kết quả trên máy mình. Máy bạn rất có thể in y hệt, nhưng chuẩn C++ chỉ đảm bảo riêng `sizeof(char)` bằng 1. Các số còn lại phụ thuộc máy và trình biên dịch.

!!! info "Bạn biết Go?"
    Go có `unsafe.Sizeof(x)` với ý nghĩa giống `sizeof`. Nó nằm trong gói `unsafe` vì bình thường code Go không cần quan tâm tới kích thước. Một điểm khác cần nhớ: trong Go, `int` có kích thước đúng bằng một từ máy của nền tảng (thường 8 byte trên máy 64 bit), còn `int` trong C++ thường là 4 byte. Nếu muốn kích thước cố định, Go có `int32`, `int64`; C++ cũng có kiểu như vậy, ta sẽ gặp sau.

    Về địa chỉ: `&x` trong Go cũng có nghĩa là "địa chỉ của `x`", giống hệt C++. Go cũng có địa chỉ (con trỏ), nhưng code Go thường ngày ít khi phải để ý tới chúng; trong C++ bạn sẽ để ý nhiều hơn.

**Thử thay đổi: đổi kiểu thì `sizeof` đổi.** Ở ví dụ 4 ngay bên dưới, mình đổi `int diem` thành `long long diem` và chạy lại: số byte in ra đổi từ `4` thành `8`. Kích thước đi theo **kiểu**, không đi theo giá trị.

### Ví dụ 3: Địa chỉ của hai ba biến

Trong code dưới đây có hai thứ lạ ở dòng (2): `void*` và `static_cast<void*>(...)`. Dấu `*` sau tên kiểu nghĩa là "địa chỉ của một …" (`char*` là "địa chỉ của một `char`"); [Bài 03](03-con-tro-co-ban.md) sẽ dạy kỹ. Cứ đọc tiếp, ngay sau phần kết quả mình giải thích vì sao cần chúng.

```cpp
#include <iostream>

int main() {
    int tuoi = 30;
    int nam = 2026;
    char chu = 'A';

    std::cout << "tuoi: " << &tuoi << "\n";                       // (1)
    std::cout << "nam:  " << &nam << "\n";
    std::cout << "chu:  " << static_cast<void*>(&chu) << "\n";    // (2)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int tuoi = 30;` | Xin 4 ngăn cho `tuoi`, ghi `30` vào đó | `tuoi` ở 0x1004..0x1007 = 30 (địa chỉ minh họa) |
| `int nam = 2026;` | Xin 4 ngăn nữa cho `nam`, ghi `2026` | `nam` ở 0x1008..0x100b = 2026 |
| `char chu = 'A';` | Xin 1 ngăn cho `chu`, ghi mã của chữ `A` | `chu` ở 0x1003 = 'A' |
| (1) `&tuoi` | Lấy địa chỉ ngăn đầu của `tuoi` rồi in ra | in `0x1004` (minh họa) |
| `&nam` | Tương tự | in `0x1008` |
| (2) `static_cast<void*>(&chu)` | Đổi "nhãn kiểu" của địa chỉ sang `void*` rồi mới in, xem giải thích bên dưới | in `0x1003` |

Hình minh họa (địa chỉ minh họa, máy bạn sẽ in số khác; cũng chưa chắc trình biên dịch xếp ba biến theo đúng thứ tự này):

```text
0x1003   0x1004 .. 0x1007   0x1008 .. 0x100b
[ 'A' ]  [      30      ]   [     2026     ]
  chu          tuoi              nam
```

**Kết quả khi chạy** (một lần chạy thật trên máy mình):

```text
tuoi: 0x7fffaf5a7370
nam:  0x7fffaf5a7374
chu:  0x7fffaf5a736f
```

Lần chạy khác trên cùng máy, mình thấy các số đổi hoàn toàn:

```text
tuoi: 0x7ffe381a7930
nam:  0x7ffe381a7934
chu:  0x7ffe381a792f
```

Số trên máy bạn sẽ khác, và chạy lần hai cũng có thể khác lần một. Chỉ có **kiểu mẫu** là đáng để ý: `nam` hơn `tuoi` đúng 4 (vì `tuoi` chiếm 4 byte, `nam` nằm ngay sau), còn `chu` kém `tuoi` đúng 1 (ngăn của `chu` nằm ngay trước `tuoi`). Kiểu mẫu này (các biến sát nhau, cách đúng 4 và đúng 1) là điều **thường** thấy chứ trình biên dịch không hứa: nó được quyền xếp các biến theo thứ tự khác. Để thấy `…370` kém `…36f` đúng 1, hãy đếm: …36d, …36e, …36f rồi mới tới …370, vì sau chữ `f` (15) hệ 16 qua hàng tiếp theo.

**Vì sao `chu` phải ép sang `void*`?** Ở dòng (2), `&chu` có kiểu "địa chỉ của một `char`", viết là `char*`.

Với kiểu `char*`, `std::cout` có một quy ước cũ từ ngôn ngữ C: nó coi đó là **chuỗi chữ**, nên nó **không in địa chỉ** mà đi tới địa chỉ đó, đọc và in các ký tự từ đó trở đi. Để buộc nó in con số địa chỉ, ta đổi nhãn kiểu thành `void*` (địa chỉ không nói rõ trỏ tới loại gì) bằng `static_cast<void*>(...)`.

`static_cast<Kiểu>(giá trị)` đọc là "ép giá trị này sang `Kiểu`". Với địa chỉ của `int`, `std::cout` không có quy ước đặc biệt, nên in thẳng được.

**Thử thay đổi: in thẳng `&chu` thì sao?** Mình đã thử một chương trình chỉ có `char chu = 'A'; std::cout << &chu << "\n";`. Nó biên dịch được, và lần chạy của mình in `A`, **không phải một địa chỉ**. Vì `chu` chỉ là một ký tự đơn, không có ký tự `\0` báo "hết chuỗi" ngay sau nó, nên `std::cout` đọc tiếp những byte nằm sau đó. Việc này là **hành vi không xác định (undefined behavior)**, tức chuẩn C++ không nói chuyện gì sẽ xảy ra, có thể in ra rác, và chương trình có thể sai theo cách khó đoán. Kết quả `A` ở máy mình chỉ là may mắn.

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    char chu = 'A';
    std::cout << &chu << "\n";   // KHÔNG in địa chỉ: coi &chu là chuỗi chữ
    return 0;
}
```

### Ví dụ 4: Cùng ngăn, giá trị khác

```cpp
#include <iostream>

int main() {
    int diem = 5;
    std::cout << "gia tri: " << diem << ", so byte: " << sizeof(diem)
              << ", dia chi: " << &diem << "\n";   // (1)
    diem = 9;                                       // (2)
    std::cout << "gia tri: " << diem << ", so byte: " << sizeof(diem)
              << ", dia chi: " << &diem << "\n";   // (3)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `int diem = 5;` | Xin 4 ngăn, đặt tên `diem`, ghi `5` | `diem` ở 0x1000..0x1003 = 5 (địa chỉ minh họa) |
| (1) | In giá trị `5`, số byte `4`, và địa chỉ | `0x1000..0x1003 = 5`, không đổi |
| (2) `diem = 9;` | **Ghi đè** `9` vào đúng 4 ngăn đó. Không xin ngăn mới | `0x1000..0x1003 = 9` |
| (3) | In giá trị `9`, số byte `4`, và địa chỉ | không đổi |

**Kết quả khi chạy**

```text
gia tri: 5, so byte: 4, dia chi: 0x7ffdc531bd54
gia tri: 9, so byte: 4, dia chi: 0x7ffdc531bd54
```

Hai dòng in cùng một địa chỉ. Số địa chỉ trên máy bạn sẽ khác, nhưng hai dòng của bạn vẫn sẽ giống nhau. Đây là điều đáng nhớ: **gán giá trị mới không chuyển biến sang chỗ khác, nó chỉ đổi nội dung của những ngăn mà biến đã có**. Tên, kiểu, địa chỉ của biến không đổi suốt đời biến. Chỉ có giá trị đổi.

**Thử thay đổi: đổi `int diem` thành `long long diem`.** Mình đã chạy lại, và nhận được:

```text
gia tri: 5, so byte: 8, dia chi: 0x7ffd9a9d9400
gia tri: 9, so byte: 8, dia chi: 0x7ffd9a9d9400
```

Số byte đổi từ `4` thành `8`: biến giờ chiếm 8 ngăn liền nhau. Giá trị và chuyện "hai dòng cùng địa chỉ" vẫn y như cũ.

!!! question "Hỏi nhanh: sao biến cần cả địa chỉ, tôi chỉ dùng tên?"
    Trong code thường ngày, bạn dùng tên. Tên là cách *bạn* gọi biến. Địa chỉ là cách *máy* tìm biến. Trình biên dịch thường dịch tên thành địa chỉ. Ở các bài sau, bạn sẽ thấy có lúc ta cần tự cầm cái địa chỉ để đưa cho người khác, và đó là lúc địa chỉ trở nên quan trọng.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Một biến trong C/C++ gồm những gì?"
    Bốn thứ: tên, kiểu, giá trị và địa chỉ. Kiểu quyết định biến chiếm bao nhiêu byte và cách hiểu các byte đó. Địa chỉ là vị trí của byte đầu tiên mà biến chiếm.

??? question "`sizeof` là gì và trả về kiểu gì?"
    `sizeof` là toán tử cho biết số byte mà một kiểu hoặc một biến chiếm. Nó được tính lúc biên dịch. Kết quả có kiểu `std::size_t`, là kiểu số nguyên không âm đủ lớn để biểu diễn kích thước của mọi đối tượng. `sizeof(char)` luôn bằng 1.

??? question "`int` có luôn là 4 byte không?"
    Không. Chuẩn C++ chỉ yêu cầu `int` đủ lớn (ít nhất 16 bit) chứ không ép 4 byte. Trên các máy tính và trình biên dịch phổ biến, nó thường là 4 byte. Muốn chắc chắn thì dùng `sizeof(int)`, hoặc dùng kiểu có kích thước cố định như `std::int32_t` (kiểu số nguyên đúng 32 bit; sẽ gặp lại sau).

??? question "Chạy chương trình hai lần, địa chỉ của biến có giống nhau không?"
    Không đảm bảo. Nhiều hệ điều hành đặt chương trình vào vùng nhớ khác nhau mỗi lần chạy, nên địa chỉ in ra có thể khác. Điều đó không phải lỗi. Không được viết code dựa vào một địa chỉ cụ thể.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên dấu `;`"
    Go tự chèn `;` giúp bạn, C++ thì không. Lỗi báo thường trỏ vào cuối dòng bị thiếu, nhưng nhắc tới chữ ở dòng **kế tiếp** (như `expected ‘;’ before ‘return’` ở ví dụ 1). Hãy nhìn kỹ dòng ngay trên chỗ báo lỗi.

!!! warning "Lỗi 2: Nháy đơn và nháy kép khác nhau"
    `'A'` là một ký tự (kiểu `char`), còn `"A"` là một chuỗi chữ. Viết `char chu = "A";` là lỗi biên dịch. Mình đã thử, `g++ 11.4` báo `invalid conversion from ‘const char*’ to ‘char’`.

!!! warning "Lỗi 3: Tin rằng `int` luôn 4 byte và địa chỉ luôn cố định"
    Cả hai đều chỉ là thói quen của máy thông thường. Hỏi `sizeof` thay vì đoán, và đừng bao giờ ghi cứng một con số địa chỉ vào code.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="01" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Một byte gồm bao nhiêu bit?

- 4 bit, vì một chữ số hệ 16 ứng với một byte
- 16 bit, vì địa chỉ viết bằng hệ 16
- 8 bit, nên có 256 tổ hợp khác nhau
- 10 bit, vì ta đếm bằng hệ 10

<p class="giai-thich" markdown>Một byte là tám bit, và vì mỗi bit có hai khả năng nên có 256 tổ hợp. Con số 4 bit là của **một chữ số** hệ 16, tức chỉ nửa byte (hai chữ số hệ 16 mới đủ một byte). Hệ 16 và hệ 10 chỉ là cách viết số, chúng không làm đổi số bit trong một byte.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Trong hình ảnh dãy tủ khóa, "địa chỉ" của một ngăn nhớ là gì?

- Số thứ tự của ngăn đó trong dãy
- Tên của biến đang được đặt lên ngăn đó
- Giá trị đang được đựng trong ngăn đó
- Kiểu dữ liệu mà ngăn đó đang chứa

<p class="giai-thich" markdown>Địa chỉ là số thứ tự của ngăn, dùng để tìm ra đúng ngăn đó. Tên biến là mảnh giấy do lập trình viên dán lên, và giá trị là thứ đang nằm trong ngăn, cả hai đều có thể đổi mà ngăn vẫn ở nguyên chỗ cũ. Kiểu thuộc về biến chứ không thuộc về từng ngăn riêng lẻ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Một biến trong C++ gồm những thứ nào?

- Chỉ tên và giá trị
- Tên, giá trị và số byte, còn kiểu thì tự suy ra khi chạy
- Kiểu và địa chỉ, vì tên chỉ là chú thích của lập trình viên
- Tên, kiểu, giá trị và địa chỉ

<p class="giai-thich" markdown>Biến có đủ bốn thứ: tên, kiểu, giá trị, địa chỉ. Kiểu thì cố định ngay lúc biên dịch, không phải suy ra lúc chạy, và số byte là hệ quả của kiểu chứ không phải thành phần độc lập. Tên không phải chú thích vô nghĩa: nó là cách bạn gọi biến trong code, và trình biên dịch dùng nó để tìm ra địa chỉ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Trên máy tính thông thường, `sizeof(int)` thường bằng bao nhiêu, và chuẩn C++ có đảm bảo con số đó không?

- Bằng 4, và chuẩn C++ đảm bảo mọi nơi đều là 4
- Thường bằng 4, nhưng chuẩn C++ không ép con số này
- Bằng 8, vì máy hiện nay đều là 64 bit
- Bằng 2, vì `int` là số nguyên ngắn

<p class="giai-thich" markdown>Trên máy phổ biến `int` thường là 4 byte, nhưng chuẩn chỉ yêu cầu nó đủ lớn tối thiểu, không ép đúng 4, nên không được coi 4 là luật. Máy 64 bit không làm `int` thành 8 byte: nhiều hệ thống 64 bit vẫn dùng `int` 4 byte và để `long long` cho số lớn hơn. Con số 2 là mức tối thiểu cũ, không còn là thường lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đoạn code sau. Hai dòng in ra (trên máy tính thông thường) liên quan thế nào?

```text
int diem = 5;
std::cout << &diem << "\n";
diem = 9;
std::cout << &diem << "\n";
```

- Hai địa chỉ khác nhau, vì giá trị mới được ghi vào ngăn mới
- Địa chỉ thứ hai lớn hơn đúng 4, vì `int` chiếm 4 byte
- Hai địa chỉ giống nhau, vì phép gán chỉ ghi đè trong chính các ngăn đó
- Lỗi biên dịch, vì không được lấy địa chỉ một biến hai lần

<p class="giai-thich" markdown>Gán giá trị mới không chuyển biến sang chỗ khác, nó chỉ đổi nội dung của những ngăn biến đã có, nên hai dòng in cùng một địa chỉ (mình đã chạy ví dụ tương tự và thấy đúng vậy). Biến không "dọn nhà" mỗi lần đổi giá trị. Lấy địa chỉ bao nhiêu lần cũng được, và con số 4 là kích thước của biến chứ không phải độ dời địa chỉ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn code sau. Trên máy tính thông thường (`long long` 8 byte, `char` 1 byte), nó in ra gì?

```text
long long a = 1;
char c = 'x';
std::cout << sizeof(a) + sizeof(c) << "\n";
```

- 2, vì mỗi biến tính là một đơn vị
- 8, vì chỉ `long long` được tính
- Lỗi biên dịch, vì không cộng được hai kết quả của `sizeof`
- 9, vì 8 byte cộng 1 byte

<p class="giai-thich" markdown>`sizeof(a)` là 8 và `sizeof(c)` là 1, cả hai đều là số nguyên nên cộng được, ra 9 (mình đã chạy thử và nhận 9). Kết quả 2 là nhầm giữa số biến và số byte. Kết quả 8 là quên rằng `char c` cũng chiếm một byte.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Cho `char chu = 'A';`. Vì sao muốn in địa chỉ của `chu` thì phải viết `static_cast<void*>(&chu)` thay vì `&chu`?

- Vì `&chu` có kiểu `char*`, mà `std::cout` in `char*` như một chuỗi chữ
- Vì `char` không có địa chỉ riêng, nó dùng chung địa chỉ với biến `int` đứng cạnh nó
- Vì `&chu` in ra địa chỉ hệ 10, còn `void*` mới đổi sang hệ 16
- Vì `static_cast` làm `chu` chiếm thêm byte để đủ chỗ chứa địa chỉ

<p class="giai-thich" markdown>Với kiểu `char*`, `std::cout` giữ quy ước từ ngôn ngữ C: đây là địa chỉ đầu của chuỗi chữ, nên nó đọc và in ký tự, có thể đọc quá xa gây hành vi không xác định. Ép sang `void*` để nó in con số địa chỉ. Biến `char` có địa chỉ riêng như mọi biến, và cách viết hệ 16 do `std::cout` quyết định chứ không do kiểu `void*`. `static_cast` chỉ đổi cách *nhìn* địa chỉ, không đổi gì trong bộ nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Với `int x = 7;`, biểu thức `&x` cho ra điều gì?

- Giá trị `7`, chỉ là cách viết khác của chính con số đó
- Địa chỉ của `x`: số của ngăn đầu tiên nó chiếm
- Số byte mà `x` chiếm, giống `sizeof(x)`
- Một bản sao của `x` đặt ở ngăn mới

<p class="giai-thich" markdown>Toán tử `&` đặt trước tên biến là "địa chỉ của". Số byte phải hỏi bằng `sizeof(x)`, còn giá trị `7` thì lấy bằng cách viết thẳng `x`. `&x` không tạo bản sao nào, nó chỉ cho biết `x` đang nằm ở đâu.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Bộ nhớ là dãy ngăn có số thứ tự (địa chỉ); mỗi ngăn là một byte, gồm 8 bit.
2. Chương trình C++ ngắn nhất cần `#include`, `int main()` và `return 0;`; biên dịch bằng `g++ -std=c++17 -Wall -o bai bai.cpp && ./bai`.
3. Một biến gồm bốn thứ: tên, kiểu, giá trị, địa chỉ; kiểu quyết định số byte, và `sizeof` cho biết số đó.
4. `&x` là địa chỉ của `x`; địa chỉ `char` phải ép sang `void*` mới in ra con số.
5. Địa chỉ có thể đổi giữa các lần chạy, và `int` thường (không phải luôn luôn) là 4 byte.
