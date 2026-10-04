# Bài 17 — string, string_view, array, deque, list

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::string` (nối, so sánh, `find`, `substr`, `c_str`), biết SSO là gì và vì sao nó là chuyện của từng bản thư viện, và nhớ lại `std::string_view` chỉ là cửa sổ nhìn vào chuỗi người khác giữ.
    - Dùng `std::array` (kích thước cố định lúc biên dịch, không cần heap) thay cho mảng C của Bài 05, và biết `std::deque` (thêm nhanh ở hai đầu) và `std::list` (nút rời nhau) khác `std::vector` ở đâu.
    - Chọn container bằng bảng quyết định: **mặc định là `std::vector`**, đổi khi có lý do rõ.

**Bạn cần biết trước:** [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) (mảng, chuỗi kiểu C, `'\0'`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const&`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`string_view`) và [Bài 16](16-vector.md) (`vector`, size/capacity, tái cấp phát).

## 🧠 Câu chuyện mở đầu

Ở [Bài 16](16-vector.md), `vector` là **một kệ sách liền khối**. Bài này là cả cửa hàng đồ nội thất. `std::string` là kệ sách chỉ đựng chữ cái, có nhiều món tiện cho chữ (chuỗi ngắn thì chữ được ghi luôn lên tờ giấy, tức chính đối tượng, khỏi thuê kệ ở kho; mục 2).

`std::array` là kệ **đóng cố định vào tường**: cỡ chốt từ lúc xây, không nở ra. `std::deque` là **dãy nhiều kệ nhỏ** xếp nối nhau, kèm một bảng chỉ dẫn: thêm kệ ở đầu hay cuối đều dễ.

`std::list` là **các tấm thẻ rời** mỗi thẻ ghi một món và "thẻ trước ở đâu, thẻ sau ở đâu": thẻ nằm khắp kho. Còn `std::string_view` vẫn là **ô cửa kính** của Bài 14: nhìn được, không giữ đồ.

!!! info "Chỗ nào ví dụ này không còn đúng?"
    Đây chỉ là hình dung. Thật ra bộ nhớ chỉ có các byte (Bài 01); "kệ nhỏ", "thẻ" là các khối byte mà thư viện xin ở heap hoặc đặt ngay trong đối tượng.

## 📖 Giải thích

### 1. `std::string`: dùng hằng ngày

`std::string` (`#include <string>`) là kiểu chuỗi chữ của thư viện chuẩn, đã gặp ở [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md). Nó giống `std::vector<char>` ở chỗ tự quản lý bộ nhớ (RAII), nhưng có thêm nhiều thao tác cho chữ. Chương trình dưới thử các thao tác hay dùng nhất; các vị trí đếm từ 0.

```cpp
#include <cstring>
#include <iostream>
#include <string>

int main() {
    std::string ho = "Nguyen";                       // (1)
    std::string ten = "An";
    std::string full = ho + " " + ten;               // (2)
    full += "!";                                     // (3)
    std::cout << full << " (" << full.size() << " ky tu)\n";

    full[0] = 'M';                                   // (4)
    std::cout << full << "\n";

    std::cout << (ho == "Nguyen") << " " << (ho < ten) << " " << (ten < ho) << "\n";   // (5)

    std::size_t vt = full.find("An");                // (6)
    std::cout << "find An: " << vt << "\n";
    std::size_t khong = full.find("xyz");            // (7)
    if (khong == std::string::npos) {
        std::cout << "khong thay xyz\n";
    }
    std::string con = full.substr(vt, 2);            // (8)
    std::cout << "substr: " << con << "\n";

    std::string b = full;                            // (9)
    b[1] = 'X';
    std::cout << full << " | " << b << "\n";

    const char* p = full.c_str();                    // (10)
    std::cout << std::strlen(p) << " " << full.size() << "\n";
    std::string vn = "xin chào";                     // (11)
    std::cout << "size = " << vn.size() << "\n";
    return 0;
}
```

`std::string::npos` là một hằng của thư viện, nghĩa là "không có vị trí nào": `find` trả nó khi không tìm thấy. Kiểu của vị trí là `std::size_t` (số không dấu, [Bài 16](16-vector.md)), nên `npos` là số không dấu lớn nhất, **không phải -1**. `std::strlen` (trong `<cstring>`) đếm ký tự cho tới `'\0'`.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `ho` và `ten` được dựng từ chuỗi hằng (chép chữ vào string) | `ho`: `Nguyen`; `ten`: `An` |
| (2) | `+` nối: tạo một string **mới** `Nguyen An` (ít nhất một vế phải là `std::string`) | `full`: `Nguyen An`, size 9 |
| (3) | `+=` nối thêm vào chính `full` | `full`: `Nguyen An!`, size 10 |
| (4) | `[0]` là ký tự đầu, **sửa được** tại chỗ | `full`: `Mguyen An!` |
| (5) | `==` so nội dung; `<` so theo thứ tự từ điển (từng ký tự theo mã): `N` đứng sau `A` | in `1 0 1` |
| (6) | `find("An")` trả vị trí bắt đầu của lần gặp đầu tiên: vị trí 7 (đếm từ 0) | `vt` = 7 |
| (7) | `find("xyz")` không thấy nên trả `npos`; so với `npos` mới đúng | in `khong thay xyz` |
| (8) | `substr(vt, 2)`: lấy 2 ký tự từ vị trí 7, ra string **mới** | `con`: `An` |
| (9) | `b = full` sao chép sâu ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)); sửa `b[1]` không đụng `full` | `b`: `MXuyen An!` |
| (10) | `c_str()` đưa con trỏ `const char*` kiểu C ([Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)) cho hàm C đòi chuỗi kiểu C; `strlen` và `size()` cùng ra 10 | `p` ---> `M g u y e n _ A n ! \0` |
| (11) | `"xin chào"` có 8 chữ nhưng `size()` là 9 (xem dưới) | in `size = 9` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -pthread`):

```text
Nguyen An! (10 ky tu)
Mguyen An!
1 0 1
find An: 7
khong thay xyz
substr: An
Mguyen An! | MXuyen An!
10 10
size = 9
```

`size()` và `length()` là một, và đều đếm **byte**, không đếm "chữ cái". Chữ viết ra thành byte theo **UTF-8**: chữ không dấu như `a` chiếm 1 byte, chữ có dấu như `à` chiếm 2 byte (hoặc hơn), nên "xin chào" là 9 byte. Go dùng cùng UTF-8 và `len("xin chào")` cũng ra 9. Con trỏ của `c_str()` chỉ dùng được khi chuỗi còn sống và chưa bị sửa, giống địa chỉ phần tử của vector ở [Bài 16](16-vector.md).

**Thử thay đổi:** viết `std::string s = "xin" + " chao";` (cộng hai chuỗi hằng). Mình đã biên dịch: g++ báo `invalid operands of types 'const char [4]' and 'const char [6]' to binary 'operator+'`. Chuỗi hằng là mảng `char` ([Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)), không có phép `+`; chỉ cần một vế là `std::string` thì `+` chạy.

!!! info "Bạn biết Go?"
    Chuỗi Go **bất biến**: `s[0] = 'M'` không biên dịch được, và `s += "x"` trong vòng lặp tạo chuỗi mới mỗi lần. `std::string` thì **sửa được** tại chỗ và cũng có size/capacity như vector, nên `+=` nhiều lần rẻ kiểu amortized (phân bổ), giống `push_back` của vector. Phần giống: cả hai đều là dãy **byte**. Cái giống chuỗi Go hơn cả là `std::string_view` (mục 3): một cặp (địa chỉ, độ dài) nhìn vào byte có sẵn.

### 2. SSO: chuỗi ngắn nằm ngay trong đối tượng

**SSO (Small String Optimization, "tối ưu chuỗi nhỏ")**: phần lớn chuỗi thực tế rất ngắn, nên nhiều bản thư viện chừa trong **chính đối tượng** `std::string` một vùng nhỏ để chứa luôn chữ của chuỗi ngắn, khỏi xin heap. Chuỗi dài hơn thì chữ nằm ở heap.

Chuẩn C++ **không đòi hỏi** SSO và không quy định ngưỡng: đó là chuyện cài đặt, nên mọi con số dưới đây chỉ là của `g++ 11` (thư viện libstdc++) trên máy mình.

```cpp
#include <iostream>
#include <string>

int main() {
    std::string ngan = "abc";                         // (1)
    std::string dai(100, 'z');                        // (2)
    std::cout << "sizeof(std::string) = " << sizeof(std::string) << "\n";
    std::cout << "capacity ngan = " << ngan.capacity() << ", dai = " << dai.capacity() << "\n";   // (3)
    return 0;
}
```

Dòng (2): `std::string(n, c)` tạo chuỗi gồm `n` ký tự `c`, giống `vector(n, giá trị)` ở [Bài 16](16-vector.md).

**Kết quả khi chạy:**

```text
sizeof(std::string) = 32
capacity ngan = 15, dai = 100
```

Đối tượng `std::string` to 32 byte, và chuỗi `"abc"` có capacity 15 ngay từ đầu: vùng nhỏ trong đối tượng chứa được 15 ký tự (chuỗi `dai` thì ở heap). Thư viện khác có thể cho số khác. Điều cần nhớ: chuỗi ngắn thường không tốn lần xin heap nào, nhưng **đừng dựa** vào ngưỡng hay địa chỉ cụ thể.

### 3. `std::string_view`: nhắc lại và hai kiểu dangling mới

[Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) đã dạy: `std::string_view` là cửa sổ (địa chỉ đầu + độ dài), **không sở hữu, không chép**, hợp làm tham số hàm; `substr` của nó cũng chỉ cắt cửa sổ chứ không chép chữ (khác `substr` của `std::string`, mục 1, ra chuỗi mới). Nó **không bảo đảm có `'\0'`** ở cuối, nên đừng đưa `sv.data()` cho hàm C đòi chuỗi kiểu C: chép ra `std::string` rồi dùng `c_str()`.

Bài 14 nêu hai kiểu dangling (trả `string_view` của biến cục bộ, gán từ chuỗi tạm). Có thêm hai kiểu nữa. Kiểu thứ nhất: chuỗi gốc **dài ra**, nên xin vùng nhớ mới và trả vùng cũ. Cả hai kiểu là hành vi không xác định (UB), nên mình chỉ nêu những gì đã thật sự chạy.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
#include <string_view>

int main() {
    std::string s(20, 'a');
    std::string_view sv = s;
    s += std::string(200, 'b');
    std::cout << sv.size() << " " << sv[0] << "\n";
    return 0;
}
```

Dòng 7 tạo chuỗi 20 ký tự `a`, dòng 8 cho `sv` nhìn vào nó, dòng 9 nối thêm 200 ký tự (`std::string(200, 'b')`), buộc `s` xin vùng nhớ lớn hơn và trả vùng cũ. Lần chạy thường của mình in `20` rồi một ký tự rác (UB: máy bạn có thể in khác, hoặc sập).

Biên dịch thêm `-fsanitize=address` ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) thì chương trình báo `heap-use-after-free`, `READ of size 1`, đúng dòng `std::cout`. Chuỗi 20 ký tự nằm ở heap là chuyện của `g++ 11`; thư viện khác (ngưỡng SSO cao hơn) có thể chứa nó trong đối tượng, và cơ chế hỏng sẽ khác, nhưng theo chuẩn vẫn là UB.

Kiểu thứ hai: chuỗi chết ở cuối một khối `{ }` ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)) trong khi `sv` (khai báo rỗng ở ngoài khối, rồi gán `sv = s;` bên trong) sống tiếp. Mình đã chạy bản này: chạy thường in `abc` và thoát mã 0, **trông như chạy đúng**; ASan lại báo `stack-use-after-scope`. Lý do: chuỗi `"abc"` nhỏ nên (trên `g++ 11`) nằm trong đối tượng `s` trên stack, khối kết thúc thì `s` hết sống nhưng byte còn đó chưa ai ghi đè. Một lần chạy may mắn không chứng minh gì.

### 4. `std::array`: mảng cỡ cố định, có trọn bộ tiện ích

Mảng C của Bài 05 có hai nỗi đau: tham số hàm thoái hóa thành con trỏ (mất cỡ), và không gán `b = a` được (g++ báo `invalid array assignment`). **`std::array<T, N>`** (`#include <array>`) bọc một mảng cỡ `N` và sửa cả hai. `N` là một **số** ghi trong `< >`, bắt buộc biết **lúc biên dịch**, và là một phần của kiểu: `std::array<int, 3>` và `std::array<int, 4>` là hai kiểu khác nhau.

```cpp
#include <array>
#include <iostream>

int tongC(int a[], int n) {                           // (1)
    int s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s;
}

int tong(const std::array<int, 4>& a) {               // (2)
    int s = 0;
    for (int x : a) s += x;
    return s;
}

int main() {
    int c[4] = {1, 2, 3, 4};                          // (3)
    std::array<int, 4> a = {1, 2, 3, 4};              // (4)
    std::cout << "sizeof(c) = " << sizeof(c) << ", sizeof(a) = " << sizeof(a) << ", a.size() = " << a.size() << "\n";
    std::cout << "tongC = " << tongC(c, 4) << ", tong = " << tong(a) << "\n";

    std::array<int, 4> b = a;                         // (5)
    b[0] = 100;
    std::cout << "a[0] = " << a[0] << ", b[0] = " << b[0] << ", a == b? " << (a == b) << "\n";
    return 0;
}
```

Hàm `tongC` ở (1) viết chỉ để so sánh: tham số `int a[]` là con trỏ, nên phải kèm `n`. Hệ quả của "cỡ là một phần của kiểu": `tong` ở (2) chỉ nhận `std::array<int, 4>`, không nhận dãy 5 phần tử (muốn nhận mọi cỡ cần khuôn mẫu hàm, ngoài phạm vi nhóm này).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3)–(4) | Hai dãy 4 số: mảng C và `std::array`, đều trên stack | mỗi cái 16 byte (4 số, thường 4 byte/`int`) |
| in `sizeof` | Cả hai 16 byte: `std::array` không tốn thêm gì; `a.size()` = 4 | in `16`, `16`, `4` |
| `tongC` (1) / `tong` (2) | Mảng C phải truyền kèm `4`; `std::array` mang cỡ theo kiểu, truyền `const&` không chép | cả hai ra 10 |
| (5) | `b = a` **chép từng phần tử** sang `b` (mảng C không làm được) | `a`: `[1 2 3 4]`, `b`: `[1 2 3 4]` rồi `[100 2 3 4]` |
| in | `b[0]` đổi, `a[0]` không; `==` so từng phần tử nên ra 0 | in `a[0] = 1, b[0] = 100, a == b? 0` |

**Kết quả khi chạy:**

```text
sizeof(c) = 16, sizeof(a) = 16, a.size() = 4
tongC = 10, tong = 10
a[0] = 1, b[0] = 100, a == b? 0
```

**Thử thay đổi: để cỡ là biến thường.** Viết `int n = 3; std::array<int, n> a = {1, 2, 3};`: mình đã biên dịch và g++ báo `the value of 'n' is not usable in a constant expression`. Cỡ phải là hằng biết lúc biên dịch (hằng `const` hay `constexpr` có giá trị viết sẵn, [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md), thì dùng được); cỡ chỉ biết lúc chạy thì dùng `vector`.

Khác `vector`: `array` **không có** `push_back`, không đổi cỡ, không dùng heap (phần tử nằm ngay trong đối tượng, tức trên stack nếu là biến cục bộ; `sizeof` ở trên cho thấy không tốn thêm byte nào so với mảng C). Vì stack có hạn ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)), đừng đặt `array` hàng triệu phần tử làm biến cục bộ.

!!! info "Bạn biết Go?"
    `std::array<int, 4>` chính là `[4]int` của Go: cỡ là một phần của kiểu, và gán hay truyền vào hàm đều **chép cả dãy** (Go cũng vậy). Mảng C mới là kẻ khác thường. Còn `std::vector` tương ứng với `[]int`, kể cả chuyện slice chung mảng đã nói ở [Bài 16](16-vector.md).

### 5. `std::deque`: thêm nhanh ở cả hai đầu

`std::deque` (`#include <deque>`, từ *double-ended queue*, "hàng đợi hai đầu") có phần lớn những thứ `vector` có (`[]`, `at`, `size`, `back`...), **không có** `capacity`/`reserve`, và thêm `push_front`, `pop_front`, `front` ở đầu. Bên trong nó **không** là một mảng liền: các phần tử nằm trong **nhiều khối nhỏ**, và một bảng nhỏ ghi địa chỉ từng khối. `d[i]` tính ra khối rồi vị trí trong khối, nên vẫn nhanh.

```cpp
#include <deque>
#include <iostream>

int main() {
    std::deque<int> d;                                // (1)
    d.push_back(2);                                   // (2)
    d.push_back(3);
    d.push_front(1);                                  // (3)
    d.push_front(0);
    std::cout << "d:";
    for (int x : d) std::cout << " " << x;
    std::cout << " | d[2] = " << d[2] << ", front = " << d.front() << ", back = " << d.back() << "\n";
    d.pop_front();                                    // (4)
    d.pop_back();
    std::cout << "sau pop: size = " << d.size() << ", front = " << d.front() << "\n";

    int& r = d[0];                                    // (5)
    const int* truoc = &r;
    for (int i = 0; i < 1000; i++) d.push_back(i);
    for (int i = 0; i < 1000; i++) d.push_front(i);
    std::cout << "size = " << d.size() << ", r van cung dia chi? " << (truoc == &d[1000]) << ", r = " << r << "\n";

    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1)–(2) | Rỗng; `push_back` thêm 2, rồi 3 vào **cuối** | `[2 3]` |
| (3) | `push_front` thêm 1, rồi 0 vào **đầu** | `[0 1 2 3]` |
| in | Duyệt in, rồi in `d[2]`, `front`, `back` | in dòng đầu của kết quả |
| (4) | `pop_front` bỏ 0, `pop_back` bỏ 3 | `[1 2]`, in `size = 2, front = 1` |
| (5) | `r` là tham chiếu tới phần tử đầu (giá trị 1), `truoc` giữ địa chỉ của nó | `r` ---> phần tử `1` |
| thêm 2000 | Thêm 1000 phần tử ở cuối, 1000 ở đầu; phần tử cũ giờ ở chỉ số 1000; địa chỉ của nó **không đổi**, `r` vẫn đọc ra 1 | in `size = 2002, r van cung dia chi? 1, r = 1` |

**Kết quả khi chạy:**

```text
d: 0 1 2 3 | d[2] = 2, front = 0, back = 3
sau pop: size = 2, front = 1
size = 2002, r van cung dia chi? 1, r = 1
```

Điều đáng học thứ nhất: **tham chiếu tới phần tử vẫn sống** khi bạn thêm ở hai đầu (khác vector, [Bài 16](16-vector.md), mục 4). Chuẩn bảo đảm điều này cho tham chiếu và con trỏ tới phần tử với thao tác ở hai đầu, nhưng **không** cho iterator ([Bài 19](19-iterator-vo-hieu.md)). Chèn hay xóa ở **giữa** thì phải dời phần tử như vector và làm hỏng cả tham chiếu.

Điều thứ hai: `deque` **không liền khối**, nên hai phần tử kề nhau đôi khi nằm ở hai khối khác nhau (khối to cỡ nào là tùy bản thư viện).

Dùng `deque` khi cần thêm/lấy nhanh ở **cả hai đầu** mà vẫn muốn `d[i]`: hàng đợi, cửa sổ trượt. [Bài 21](21-big-o-cau-truc-du-lieu.md) sẽ cho thấy `std::queue` mặc định dựng trên `deque`.

### 6. `std::list`: các nút rời nhau

`std::list` (`#include <list>`) là **danh sách liên kết đôi**. Mỗi phần tử nằm trong một **nút (node)** xin riêng ở heap; nút ghi giá trị cùng hai con trỏ: tới nút trước và nút sau. Nên **không có `[]`**: muốn tới phần tử thứ 1000 phải đi qua từng nút. Điểm mạnh: thêm ở đầu hay cuối đều xong ngay, và xóa một nút chỉ cần nối lại hai con trỏ, **không dời ai**.

```cpp
#include <iostream>
#include <list>

void in(const char* ten, const std::list<int>& l) {
    std::cout << ten << ":";
    for (int x : l) std::cout << " " << x;
    std::cout << "  (size " << l.size() << ")\n";
}

int main() {
    std::list<int> l = {30, 10, 20, 10};              // (1)
    l.push_front(5);                                  // (2)
    l.push_back(40);
    in("ban dau", l);
    const int* p = &l.front();                        // (3)
    l.remove(10);                                     // (4)
    in("remove(10)", l);
    l.sort();                                         // (5)
    in("sort", l);
    for (int i = 0; i < 100; i++) l.push_back(i);     // (6)
    std::cout << "front van o cho cu? " << (p == &l.front()) << ", *p = " << *p << "\n";
    return 0;
}
```

`remove(10)` xóa **mọi** phần tử bằng 10; `sort()` là hàm sắp xếp riêng của `list` ([Bài 20](20-algorithm-lambda.md) sẽ nói vì sao nó cần hàm riêng).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1)–(2) | Dựng `30 10 20 10`; `push_front(5)`, `push_back(40)` | `5 30 10 20 10 40` |
| (3) | `p` giữ địa chỉ của phần tử đầu (giá trị 5) | `p` ---> nút `5` |
| (4) | Xóa hai nút `10`, nối lại các nút kề | `5 30 20 40`, size 4 |
| (5) | `sort()` sắp tăng dần | `5 20 30 40` |
| (6) | Thêm 100 nút ở cuối | size 104 |
| in | Nút `5` không bị di chuyển, `p` vẫn đúng | in `front van o cho cu? 1, *p = 5` |

**Kết quả khi chạy:**

```text
ban dau: 5 30 10 20 10 40  (size 6)
remove(10): 5 30 20 40  (size 4)
sort: 5 20 30 40  (size 4)
front van o cho cu? 1, *p = 5
```

**Thử thay đổi: viết `l[1]`.** Mình đã biên dịch: `no match for 'operator[]' (operand types are 'std::list<int>' and 'int')`. `list` cố ý không có `[]`.

Giá phải trả của các nút rời: mỗi phần tử cần chỗ cho cả hai con trỏ. Chương trình dưới dựng một cái nút giả có hình dạng như vậy rồi đo cỡ bằng `sizeof` ([Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md)).

```cpp
#include <iostream>

struct Nut {
    Nut* truoc;
    Nut* sau;
    int giaTri;
};

int main() {
    std::cout << "sizeof(Nut) = " << sizeof(Nut) << ", sizeof(int) = " << sizeof(int) << "\n";
    return 0;
}
```

**Kết quả khi chạy:**

```text
sizeof(Nut) = 24, sizeof(int) = 4
```

Hai con trỏ (16 byte) cộng `int` (4 byte, thường là thế) cộng 4 byte đệm cho tròn: 24 byte, gấp khoảng 6 lần chỉ riêng số `int`. Nút thật của `g++ 11` cỡ đó; mình còn đo thấy hai nút kề nhau trong một `list` bốn số cách nhau 32 byte, vì bộ cấp phát cộng thêm phần quản lý của nó. Các con số này chỉ là của máy mình.

Mỗi nút còn là một lần xin heap riêng. Sau nhiều lần thêm, xóa, các nút **rải rác** khắp heap và phải đi theo con trỏ từng bước, trong khi `vector` đặt các `int` sát nhau (4 byte một món) và CPU đọc sẵn các byte kề nhau rất nhanh. Nên duyệt `list` thường chậm hơn duyệt `vector` nhiều.

!!! warning "Hay nhầm: 'chèn giữa nhanh nên dùng list'"
    Chèn/xóa một nút chỉ tốn vài bước **khi bạn đã cầm sẵn vị trí** (iterator, [Bài 19](19-iterator-vo-hieu.md)); để **tìm** vị trí đó vẫn phải đi qua từng nút. Cộng chi phí nút rời nói trên, `vector` thường vẫn thắng cả khi chèn giữa. Chỉ chọn `list` khi cần **địa chỉ phần tử ổn định** (như `p` ở trên) cùng việc chèn/xóa giữa dày đặc.

!!! info "Bạn biết Go?"
    Go có `container/list` trong thư viện chuẩn, đúng là danh sách liên kết đôi (chứa kiểu `any`), nhưng rất ít người dùng; Go **không có** deque chuẩn. Người viết Go dùng slice cho hầu hết việc (hàng đợi hay bỏ phần đầu bằng `s = s[1:]`). C++ cũng nên mặc định kiểu "dãy liền khối" (`vector`), nhưng có sẵn `deque` và `list` khi cần.

### 7. Chọn container nào?

Để so sánh các thao tác, ký hiệu **O(1)** nghĩa là "thời gian gần như không phụ thuộc số phần tử n", **O(n)** là "tăng theo n" ([Bài 21](21-big-o-cau-truc-du-lieu.md) nói kỹ). Số liệu dưới là kiến thức chung, không phải số đo máy bạn.

| | `vector` | `deque` | `list` | `array` |
|---|---|---|---|---|
| `[i]` | O(1) | O(1) | không có | O(1) |
| thêm ở cuối | O(1) amortized | O(1) | O(1) | không thêm được |
| thêm ở đầu | O(n) | O(1) | O(1) | không thêm được |
| chèn/xóa ở giữa | O(n) | O(n) | O(1) *khi đã có vị trí* | không |
| bộ nhớ | liền khối ở heap | nhiều khối nhỏ ở heap | mỗi nút một khối ở heap | ngay trong đối tượng |

| Bạn cần | Chọn | Lý do |
|---|---|---|
| Một dãy các phần tử, không có yêu cầu đặc biệt | **`std::vector`** | liền khối, ít tốn nhất, nhanh nhất ở đa số việc |
| Cỡ cố định, biết lúc biên dịch (3 tọa độ, 12 tháng) | `std::array` | không heap, không tốn thêm, vẫn có `size()` và `=` |
| Chuỗi chữ | `std::string` | tự quản lý, có `find`, `substr`... |
| Chỉ **đọc** một chuỗi (tham số hàm) | `std::string_view` | không chép; chỉ khi chuỗi gốc chắc còn sống |
| Thêm/lấy ở cả hai đầu và vẫn cần `d[i]` | `std::deque` | hai đầu O(1), tham chiếu phần tử không hỏng khi thêm ở đầu/cuối |
| Địa chỉ phần tử phải ổn định, chèn/xóa giữa dày đặc | `std::list` | nút không bao giờ bị dời |
| Tìm theo khóa | `map`, `unordered_map` | [Bài 18](18-map-set-unordered.md) |

**Quy tắc:** bắt đầu bằng `vector`. Chỉ đổi khi có lý do cụ thể (cỡ cố định thì `array`, thêm ở đầu thì `deque`, cần địa chỉ ổn định thì `list`), và nếu lo về tốc độ thì **đo** trước rồi mới đổi.

## 💻 Ví dụ code

Chương trình dưới tách một câu thành các từ (bỏ khoảng trắng thừa). Nó dùng `string_view` làm tham số (mục 3), `find`/`substr` (mục 1) và `vector` trả về ([Bài 16](16-vector.md)).

```cpp
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

std::vector<std::string> tachTu(std::string_view cau) {         // (1)
    std::vector<std::string> kq;
    std::size_t dau = 0;
    while (dau < cau.size()) {
        std::size_t cach = cau.find(' ', dau);                  // (2)
        if (cach == std::string_view::npos) {
            cach = cau.size();                                  // (3)
        }
        if (cach > dau) {
            kq.push_back(std::string(cau.substr(dau, cach - dau)));   // (4)
        }
        dau = cach + 1;                                         // (5)
    }
    return kq;
}

int main() {
    std::string cau = "  mot hai   ba ";
    std::vector<std::string> tu = tachTu(cau);
    std::cout << "co " << tu.size() << " tu:";
    for (const std::string& t : tu) std::cout << " [" << t << "]";
    std::cout << "\n";

    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| gọi `tachTu(cau)` | (1): `cau` ở `main` chuyển thành cửa sổ, không chép; hàm trả vector chuỗi mới, nên **không dangling** | `cau` còn sống suốt lúc gọi |
| (2)–(3) | `find(' ', dau)` tìm dấu cách từ vị trí `dau` (`string_view` cũng có `npos`); không còn thì từ cuối chạy tới hết chuỗi | `cach` là vị trí hoặc `size` |
| (4) | Chỉ khi từ không rỗng mới cắt và **chép** thành `std::string` (chuyển từ `string_view` phải viết rõ) đưa vào `kq` | thêm `mot`, `hai`, `ba` |
| (5) | Nhảy qua dấu cách để tìm từ kế | `dau` tăng |

**Kết quả khi chạy:**

```text
co 3 tu: [mot] [hai] [ba]
```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::string` và `std::string_view` khác nhau thế nào?"
    `std::string` **sở hữu** các ký tự (chép và tự giải phóng); `std::string_view` chỉ là cặp (con trỏ, độ dài) nhìn vào ký tự của người khác, nên không chép và không bảo đảm có `'\0'`. Dùng `string_view` làm tham số chỉ-đọc để nhận cả `std::string` lẫn chuỗi hằng mà không chép. Không cất lâu hay trả về từ hàm: nếu chuỗi gốc chết hoặc đổi chỗ (dài ra) thì nó dangling.

??? question "`std::array` khác mảng C và `std::vector` thế nào?"
    So với mảng C: `array` mang cỡ trong kiểu (có `size()`), không thoái hóa thành con trỏ, gán và so sánh được, không tốn thêm bộ nhớ. So với `vector`: cỡ cố định lúc biên dịch, không dùng heap, không có `push_back`. Cỡ biết lúc biên dịch thì `array`, không thì `vector`.

??? question "Khi nào dùng `deque`, khi nào dùng `list`?"
    `deque` khi cần thêm/lấy nhanh ở cả hai đầu mà vẫn muốn `d[i]` (tham chiếu phần tử không hỏng khi thêm ở hai đầu). `list` khi cần địa chỉ phần tử ổn định và chèn/xóa giữa dày đặc với vị trí đã có; nhược điểm là không có `[]`, mỗi nút một lần xin heap cộng hai con trỏ phụ, và duyệt chậm. Còn lại thì `vector`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `string_view` nhìn vào chuỗi sẽ đổi chỗ hoặc chết"
    `sv = s;` rồi `s` dài thêm hoặc ra khỏi khối: `sv` dangling (mục 3), kể cả khi trông như chạy đúng. Giữ `string_view` trong phạm vi ngắn, và dùng ASan để bắt.

!!! warning "Lỗi 2: Cộng hai chuỗi hằng, quên so với `npos`"
    `"xin" + " chao"` không biên dịch được (mục 1). Dùng kết quả `find` làm chỉ số mà không so với `std::string::npos` là lỗi logic thầm lặng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="17" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Với `std::string s = "cat";`, câu lệnh `s[0] = 'b';` cho kết quả nào?

- Lỗi biên dịch, vì chuỗi luôn bất biến như chuỗi của Go
- `s` thành `"bat"`, vì `std::string` sửa được tại chỗ
- `s` thành `"bat"`, nhưng chỉ khi đã gọi `reserve` trước
- Hành vi không xác định, vì chữ nằm ở vùng tĩnh chỉ đọc

<p class="giai-thich" markdown>`s` là một đối tượng `std::string` có bản chép chữ của riêng nó, nên sửa từng ký tự tại chỗ là hợp lệ và `s` thành `"bat"`. Chuỗi Go mới bất biến, không phải `std::string`. `reserve` chỉ liên quan tới việc xin chỗ trước, không quyết định việc sửa được hay không. Chuỗi hằng `"cat"` đúng là chỉ đọc (Bài 05), nhưng `s` đã chép chữ ra chỗ riêng, nên không đụng vào chuỗi hằng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn code sau (máy 64 bit). Nó in ra gì?

```text
std::string s = "banana";
std::cout << s.find("na") << " " << s.find("x") << " " << s.substr(1, 3);
```

- `2 -1 ana`, vì `find` luôn trả -1 khi không tìm thấy
- `3 -1 nan`, vì vị trí trong chuỗi được đếm từ 1
- `2 0 ana`, vì không tìm thấy thì `find` trả về 0
- `2 18446744073709551615 ana`, vì không thấy là `npos`

<p class="giai-thich" markdown>`"na"` xuất hiện đầu tiên ở vị trí 2 (đếm từ 0: b, a, n), `"x"` không có nên `find` trả `std::string::npos`, là số không dấu lớn nhất nên in ra `18446744073709551615`, và `substr(1, 3)` lấy 3 ký tự từ vị trí 1 là `"ana"`. Việc in `-1` là thói quen từ ngôn ngữ khác: kiểu của `find` không dấu nên không thể ra -1. Chuỗi cũng đếm từ 0 chứ không từ 1, nên vị trí 3 sai. Còn trả 0 sẽ lẫn với trường hợp tìm thấy ngay ở đầu chuỗi, vì thế thư viện dùng một giá trị riêng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Điều nào về SSO (tối ưu chuỗi nhỏ) của `std::string` là đúng?

- Chuẩn không bắt buộc; nhiều thư viện làm, ngưỡng tùy bản
- Chuẩn bắt buộc chuỗi dưới 16 ký tự phải nằm trong đối tượng
- Chỉ chuỗi hằng viết trong nháy kép mới được hưởng SSO
- SSO làm `std::string` không bao giờ xin heap, kể cả chuỗi dài

<p class="giai-thich" markdown>SSO là chuyện cài đặt: chuẩn C++ không đòi hỏi và không quy định ngưỡng, trên g++ 11 mình đo ngưỡng là 15 ký tự nhưng bản khác có thể khác. Vì thế không có con số 16 do chuẩn bắt buộc. SSO cũng không giới hạn ở chuỗi hằng: mọi `std::string` ngắn đều có thể được chứa ngay trong đối tượng. Và SSO chỉ giúp chuỗi ngắn: chuỗi dài vẫn xin heap (mình đã chạy: chuỗi 100 ký tự có capacity 100, tức chữ ở heap).</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn code sau. Dòng nào khiến chương trình dùng `sv[0]` ở dòng cuối là hành vi không xác định?

```text
std::string s(20, 'a');
std::string_view sv = s;
s += std::string(200, 'b');
std::cout << sv[0];
```

- Dòng đầu, vì `std::string` không có hàm tạo `(20, 'a')` như thế
- Dòng hai, vì `string_view` không tạo được từ một `std::string`
- Dòng ba, vì `s` dài ra nên có thể bị dời sang chỗ khác
- Không dòng nào, vì `string_view` tự cập nhật theo `s`

<p class="giai-thich" markdown>Dòng `s += ...` thêm 200 ký tự vào chuỗi đang có 20, buộc `s` xin vùng nhớ lớn hơn và trả vùng cũ; `sv` vẫn nhìn vào vùng cũ nên đọc `sv[0]` là dùng chỗ đã mất (ASan báo `heap-use-after-free` khi mình chạy). Hàm tạo `std::string(20, 'a')` có thật, giống `vector(n, giá trị)`. `string_view` tạo được từ `std::string` bình thường, đó là công dụng chính của nó. Còn nó không hề tự cập nhật: `string_view` chỉ giữ địa chỉ và độ dài lúc được tạo.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn code sau. Nó in ra gì?

```text
std::array<int, 3> a = {1, 2, 3};
std::array<int, 3> b = a;
b[0] = 9;
std::cout << a[0];
```

- `9`, vì hai biến chung dữ liệu như hai slice của Go
- `1`, vì phép gán chép cả dãy, nên `b` là bản riêng
- Lỗi biên dịch, vì mảng không gán cho nhau được
- Hành vi không xác định, vì `b` chưa có chỗ riêng

<p class="giai-thich" markdown>Với `std::array`, `b = a` chép từng phần tử sang `b`, nên sửa `b[0]` không đụng tới `a` và in `1`. Hai biến chung dữ liệu là cách của slice Go, không phải của `std::array` (giống `[3]int` của Go: gán là chép). Không gán được là đặc điểm của mảng C (mình đã biên dịch `b = a` với mảng C và g++ báo `invalid array assignment`), đúng cái mà `std::array` sửa. Và `b` có sẵn chỗ riêng nằm ngay trong đối tượng, nên không có UB nào.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Bạn cần một dãy vừa thêm/lấy phần tử rất nhiều ở cả đầu lẫn cuối, vừa truy cập bằng chỉ số `[i]`. Chọn kiểu nào?

- `std::vector`, vì thêm ở đầu cũng rất rẻ như thêm cuối
- `std::list`, vì thêm được ở hai đầu và có cả `[i]`
- `std::array`, vì cỡ cố định nên chắc chắn nhanh nhất
- `std::deque`, vì hai đầu đều rẻ và vẫn có sẵn `[i]`

<p class="giai-thich" markdown>`std::deque` thêm và lấy ở hai đầu đều nhanh, và vẫn truy cập `d[i]` được nhờ bảng chỉ dẫn các khối. `vector` thêm ở đầu phải dời mọi phần tử nên đắt. `list` thêm hai đầu nhanh nhưng không có `[]` (mình đã biên dịch thử và g++ báo lỗi). `array` có cỡ cố định, không thêm phần tử được, nên không hợp bài toán.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Vì sao duyệt qua một `std::list<int>` thường chậm hơn duyệt `std::vector<int>` cùng số phần tử?

- `list` kiểm tra biên ở mỗi phần tử, `vector` thì không
- `list` sao chép cả dãy mỗi khi bắt đầu một vòng duyệt
- Mỗi phần tử ở một nút riêng nên phải đi theo con trỏ
- `list` phải tái cấp phát khi duyệt hết capacity của nó

<p class="giai-thich" markdown>Mỗi phần tử của `list` ở trong một nút xin riêng ở heap, nên để sang phần tử kế phải đi theo con trỏ tới chỗ khác, còn `vector` chỉ bước tiếp 4 byte (mình đo được 32 so với 4 byte giữa hai phần tử kề nhau). Không có kiểm tra biên nào ở mỗi bước duyệt bằng `for`. Duyệt cũng không sao chép gì cả. Và `list` không có capacity: nó không có mảng chung để mà đầy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::string` sửa được tại chỗ (khác chuỗi Go bất biến): `+`/`+=` nối, `==`/`<` so, `find` trả vị trí hoặc `std::string::npos` (số không dấu lớn, không phải -1), `substr(vt, n)` ra chuỗi mới, `c_str()` đưa con trỏ kiểu C; `size()` đếm byte.
2. SSO là việc nhiều bản thư viện chứa chuỗi ngắn ngay trong đối tượng `std::string` để khỏi xin heap; chuẩn không đòi hỏi và không quy định ngưỡng (g++ 11: 15 ký tự), nên đó là chuyện cài đặt.
3. `std::string_view` chỉ là cửa sổ (địa chỉ, độ dài), không sở hữu, không bảo đảm `'\0'`; nó dangling khi chuỗi gốc chết hoặc đổi chỗ (dài ra), và có thể "trông như chạy đúng" với chuỗi ngắn.
4. `std::array<T, N>` có cỡ cố định lúc biên dịch (là một phần của kiểu, giống `[N]T` của Go), nằm ngay trong đối tượng, có `size()`, gán và so sánh được; `deque` thêm nhanh ở hai đầu và vẫn có `[i]`; `list` là các nút rời, không có `[]`, địa chỉ phần tử ổn định.
5. Chọn container: mặc định `std::vector`; cỡ cố định thì `array`, hai đầu thì `deque`, địa chỉ ổn định kèm chèn/xóa giữa dày đặc thì `list`, và lo tốc độ thì đo trước khi đổi.
