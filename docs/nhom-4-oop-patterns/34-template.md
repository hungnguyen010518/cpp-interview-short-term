# Bài 34 — Template: viết một lần, trình biên dịch làm bản cho từng kiểu

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được template hàm và template lớp (`template <typename T>`), hiểu trình biên dịch **sinh một bản riêng cho mỗi kiểu được dùng** (chạy thật, thấy hai ba bản bằng `__PRETTY_FUNCTION__` và `nm`), và biết `max(3, 4.5)` lỗi vì sao, sửa bằng `max<double>(3, 4.5)`.
    - Đọc được `std::vector<int>` và `std::array<int, 4>` như hai template lớp (tham số kiểu, tham số không phải kiểu, giá trị mặc định), và biết chuyên biệt hóa là gì (chỉ nhắc, một ví dụ nhỏ).
    - So được template (đa hình lúc biên dịch) với hàm ảo của [Bài 33](33-da-hinh-virtual.md) bằng cùng một việc làm hai cách, biết cái giá: thông báo lỗi dài (một lỗi thật rút gọn), code bloat (số đo thật), và vì sao thân template phải nằm trong header (lỗi `undefined reference` chạy thật).
    - Biết nhắc tên `static_assert`/`type_traits`, concepts C++20, SFINAE, lambda `auto` thực chất là template, và so với generics của Go (đã chạy Go 1.27.1).

**Bạn cần biết trước:** [Bài 33](33-da-hinh-virtual.md) (hàm ảo, đa hình lúc chạy), [Bài 31](31-lop-dong-goi.md) (lớp, thành viên `static`, bước liên kết), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`std::vector<int>`, khuôn mẫu được nhắc lần đầu), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`std::array<int, 4>`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (lambda tham số `auto`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`static_assert`).

## 🧠 Câu chuyện mở đầu

Xưởng đồ chơi cần các **hộp đựng**: hộp đựng xe, hộp đựng gấu, hộp đựng robot. Cách làm vụng: vẽ ba bản vẽ gần giống hệt, chỉ khác chữ "xe", "gấu", "robot". Cách gọn: làm **một khuôn có chỗ trống** "hộp đựng ___", rồi mỗi lần cần loại nào thì điền vào chỗ trống và có ngay một bản vẽ thật.

Đó là **template (khuôn mẫu)**: một khuôn có chỗ trống để điền **kiểu**. Bạn đã dùng nó từ lâu: `std::vector<int>` là khuôn "dãy đựng ___" với chỗ trống điền `int` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)). Template hàm cũng vậy: một hàm có chỗ trống ở kiểu, điền xong thành một hàm thật.

!!! info "Chỗ nào ví von xưởng đồ chơi không còn đúng?"
    Ở xưởng, bản vẽ dùng được ngay còn "món" làm ra sau. Template thì **chưa phải bản vẽ**, nó là khuôn để làm ra bản vẽ: điền kiểu xong mới ra một bản vẽ thật (một lớp), rồi từ đó mới làm ra món (với template hàm, điền xong ra thẳng một hàm). Việc điền chỗ trống do **trình biên dịch tự làm lúc biên dịch**, khi nó thấy bạn dùng, và lúc đó chưa có món nào cả. Các ví dụ phía dưới (ngăn xếp, nhãn, hình) rời xưởng đồ chơi: chỉ cần nhớ "khuôn có chỗ trống".

## 📖 Giải thích

### 1. Template hàm: một thân hàm, nhiều kiểu

Viết `template <typename T>` ngay trước một hàm: `T` là **tên chỗ trống** cho một kiểu, dùng được trong cả hàm như kiểu thường. Mỗi lần bạn gọi hàm với một kiểu mới, trình biên dịch **sinh ra một hàm thật** cho kiểu đó (gọi là **instantiation**, "sinh bản"). Ví dụ 1 chạy thật và đếm các bản sinh ra.

`template <class T>` và `template <typename T>` **giống hệt nhau** ở chỗ này (mình đã đổi và chạy: kết quả y hệt). Nhiều người viết `typename` vì chữ `class` dễ làm tưởng `T` phải là lớp, trong khi `int` cũng được.

### 2. Suy luận đối số: khi nào phải ghi `<kiểu>`

Gọi `lonHon(3, 4)` mà không ghi `<int>`: trình biên dịch nhìn kiểu của từng đối số để **tự suy ra** `T` (**suy luận đối số**, template argument deduction). Hai đối số `3` (`int`) và `4.5` (`double`) cho hai kết quả khác nhau cho cùng một `T`, nên nó bỏ cuộc và báo lỗi; hàm thường thì tự đổi `int` sang `double`. Cách chữa: ghi kiểu ra, `lonHon<double>(3, 4.5)`, lúc này không cần suy luận nên `3` được đổi sang `double` như hàm thường. `std::max` của thư viện chuẩn gặp đúng chuyện này (Ví dụ 1, Thử thay đổi).

### 3. Template lớp, tham số không phải kiểu, giá trị mặc định

Template lớp cũng có chỗ trống: `template <typename T> class Ngan { ... };` rồi dùng `Ngan<int>`. Mỗi `Ngan<int>`, `Ngan<std::string>` là **một lớp riêng**, và trình biên dịch chỉ sinh phần hàm thành viên bạn **thật sự gọi** (Ví dụ 2 xem bằng `nm`). Khi khai báo biến, bạn thường phải ghi `<kiểu>` ra như `std::vector<int>` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)); C++17 có suy luận cho một số trường hợp, mình không dạy.

Chỗ trống không chỉ là kiểu. **Tham số không phải kiểu** (non-type) là một **số** biết lúc biên dịch: `template <typename T, int N>` rồi `Ngan<int, 4>`. Đó chính là `std::array<int, 4>` của [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md): cỡ `4` nằm **trong kiểu**, nên cỡ khác là kiểu khác. Chỗ trống có thể có **giá trị mặc định**: `int N = 4` cho phép viết `Ngan<int>` (chỉ nhắc, Ví dụ 2 dùng).

### 4. Chuyên biệt hóa (specialization): chỉ nhắc

Đôi khi một kiểu cần cách làm riêng. **Chuyên biệt hóa** là viết thêm một bản **dành riêng** cho kiểu đó, bằng `template <>` rồi tên lớp có kiểu cụ thể (`Nhan<bool>`); khi dùng đúng kiểu đó, trình biên dịch chọn bản riêng thay vì bản chung. Ví dụ 3 làm với `bool`. Chuẩn còn có **chuyên biệt hóa từng phần** (cho một nhóm kiểu, như mọi con trỏ), mình chỉ nêu tên.

Ví dụ nổi tiếng trong thư viện chuẩn: `std::vector<bool>` là bản chuyên biệt hóa mà g++ cài bằng cách lưu mỗi phần tử một bit (chuẩn chỉ cho phép dạng gọn). Vì vậy `&v[0]` không cho `bool*` (mình đã thử: g++ báo `cannot convert ‘std::vector<bool>::reference*’ to ‘bool*’`); đây là lý do nhiều người tránh `vector<bool>`.

### 5. Template hay hàm ảo? Hai kiểu đa hình

[Bài 33](33-da-hinh-virtual.md) dạy đa hình **lúc chạy**: một mã, nhiều lớp con, hàm được chọn theo món thật. Template là đa hình **lúc biên dịch**: trình biên dịch sinh sẵn một bản cho mỗi kiểu và gọi thẳng, không cần lớp cha chung. Ví dụ 4 làm một việc (cộng diện tích) bằng cả hai.

| Tiêu chí | Hàm ảo (lúc chạy) | Template (lúc biên dịch) |
|---|---|---|
| Chọn hàm khi nào | Lúc chạy, theo món thật | Lúc biên dịch, theo kiểu |
| Cần lớp cha chung | Có | Không, chỉ cần kiểu có đúng hàm cần gọi |
| Trộn nhiều kiểu trong một dãy | Được (`vector<unique_ptr<Hinh>>`) | Không: `vector<H>` chỉ một kiểu `H` |
| Chi phí gọi | Qua bảng hàm ảo, khó inline (Bài 33) | Gọi thẳng, thường inline được |
| Mã nhị phân | Một bản hàm duyệt (như `tongAo`) cho mọi lớp con; mỗi lớp con vẫn có hàm ghi đè riêng | Một bản hàm duyệt cho **mỗi kiểu** dùng, sinh lúc biên dịch |
| Lỗi báo | Thường ngắn, đúng chỗ gọi | Có thể dài (mục 6) |

Không bên nào "tốt hơn" tuyệt đối: cần chứa lẫn nhiều loại và quyết định lúc chạy thì chọn hàm ảo; cùng một thuật toán cho nhiều kiểu, kiểu biết từ lúc viết thì chọn template. Mình không đo thời gian ở bài này.

### 6. Hai cái giá: lỗi dài và code bloat

**Thông báo lỗi dài.** Lỗi trong template hay hiện ở sâu trong thư viện, kèm cả chuỗi "được sinh bản từ đâu". Mình `std::sort` một `vector<Mon>` (với `struct Mon { int gia; };`, file thử `l1.cpp`) mà `Mon` không có `operator<` ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md): `std::sort` sắp xếp bằng `<`); g++ 11.4 in **114 dòng**. Rút gọn (cắt giữa dòng, `...` là phần lược):

```text
predefined_ops.h: In instantiation of ‘constexpr bool __ops::_Iter_less_iter::operator()(...)’ [with ... = Mon*...]:
stl_algo.h:82:17:   required from ‘void std::__move_median_to_first(...)’
stl_algo.h:1904:34: required from ‘... std::__unguarded_partition_pivot(...)’
stl_algo.h:4842:18: required from ‘void std::sort(_RAIter, _RAIter) [with _RAIter = ...<Mon*, std::vector<Mon> >]’
l1.cpp:6:14:   required from here
predefined_ops.h:45:23: error: no match for ‘operator<’ (operand types are ‘Mon’ and ‘Mon’)
```

Cách đọc: tìm dòng có chữ `error:` (nói thiếu `operator<` cho `Mon`), rồi dòng `required from here` có tên **file của bạn** (`l1.cpp:6:14`, chỗ bạn gọi `sort`). Phần giữa là đường đi bên trong thư viện, thường không cần đọc; lỗi này lặp vài lần, đọc lần đầu là đủ.

**Code bloat** là chương trình phình to vì nhiều bản sinh ra. Mình thử một hàm template (sắp xếp một `vector` rồi cộng) với 1, 2, 4, 8 kiểu số, đo phần mã (`.text`) của file đối tượng (`.o`: kết quả dịch một file `.cpp`, chưa ghép) bằng lệnh `size`, lệnh in cỡ phần mã và phần dữ liệu của một file `.o`. Chương trình đo (bản 2 kiểu; bản 4 và 8 kiểu thêm các dòng `tong<float>`, `tong<short>`...):

```text
#include <algorithm>
#include <iostream>
#include <vector>
template <typename T> T tong(std::vector<T> v) { std::sort(v.begin(), v.end()); T t{}; for (const T& x : v) t += x; return t; }
int main() {
  std::cout << tong<int>({3, 1, 2}) << "\n";
  std::cout << tong<long>({3, 1, 2}) << "\n";
}
// g++ -std=c++17 -O0 -c b.cpp -o b.o && size b.o      (cột text)
```

Với `-O0`: 11818, 22929, 45505, 89528 byte, tức mỗi kiểu thêm gần cả chục nghìn byte. Với `-O2`: 1716, 3766, 7353, 14300 byte. Số đổi theo hàm, kiểu, cờ và trình biên dịch; chỉ nhớ **mẫu**: càng nhiều kiểu thì càng nhiều bản.

### 7. Vì sao thân template nằm trong header

Chương trình lớn chia thành nhiều file `.cpp`, mỗi file được biên dịch **riêng**, rồi bước liên kết ([Bài 31](31-lop-dong-goi.md)) ghép lại. File **header** (`.h`) là đoạn chữ mà `#include "lon.h"` dán vào mọi file dùng nó (ngoặc kép `" "` là file của mình, ngoặc nhọn `< >` là thư viện chuẩn). Hàm thường: khai báo ở `.h`, thân ở `.cpp`.

Template không làm vậy được. Khi biên dịch `main.cpp` thấy `lonHon<int>`, trình biên dịch phải **có thân template trước mắt** để sinh bản `int`; nếu chỉ thấy khai báo thì nó đành để lại một lời gọi chưa có thân và hy vọng nơi khác có. File `lon.cpp` thì có thân nhưng **không ai yêu cầu bản `int`** ở đó nên không sinh gì. Kết quả: liên kết báo `undefined reference` (Ví dụ 5).

Cách chữa thông dụng: **để cả thân template ngay trong header**. (Có cách khác là "sinh bản tường minh" cho từng kiểu trong `.cpp`; mình chỉ nhắc tên, vì khi đó chỉ những kiểu đã liệt kê mới dùng được.)

### 8. Chỉ nhắc: `static_assert`, `type_traits`, concepts, SFINAE, lambda `auto`

- **`static_assert` và `<type_traits>`**: `static_assert(điều kiện, "lời nhắn")` ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)) kiểm tra lúc biên dịch, nên rất hợp trong template để chặn kiểu sai bằng lời nhắn rõ ràng. `<type_traits>` cho các phép kiểm kiểu như `std::is_same_v<A, B>` ("A và B cùng kiểu?") và `std::is_integral_v<T>` ("T là kiểu số nguyên?"); `static_assert(N > 0, ...)` ở Ví dụ 2 dùng đúng cách này, và mình đã chạy một template với `static_assert(std::is_integral_v<T>, ...)` cho lời nhắn đúng khi truyền `double`.
- **Concepts (C++20)**: viết ràng buộc ngay trong khai báo, như `template <std::integral T> T gap(T x)`. Mình đã thử g++ 11.4 với `-std=c++20` (không cần cờ phụ, cần `#include <concepts>`): `gap(4)` chạy, `gap(2.5)` báo `no matching function` kèm `constraints not satisfied`. Khóa này biên dịch bằng C++17 nên chỉ nhắc.
- **SFINAE**: tên cũ của kỹ thuật "thay kiểu vào template mà hỏng thì chỉ loại bản đó khỏi các ứng viên, không báo lỗi" (Substitution Failure Is Not An Error). Concepts C++20 làm việc này dễ đọc hơn; ở đây chỉ để bạn nhận ra cái tên.
- **Lambda tham số `auto`** ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)): `[](auto x) {...}` thực chất là một lambda có hàm gọi là **template**, nên mỗi kiểu đối số lại sinh một bản (Ví dụ 1 thấy hai bản).

## 💻 Ví dụ code

### Ví dụ 1: một hàm, ba bản, và lambda `auto`

`lonHon` có một chỗ trống `T`. `__PRETTY_FUNCTION__` là chữ do **g++/clang** có (không phải chuẩn C++) chứa tên đầy đủ của hàm đang chạy kèm `T` đã điền; dùng nó để thấy bản nào đang chạy.

```cpp
#include <iostream>
#include <string>

template <typename T>
T lonHon(T a, T b) {
    std::cout << "  " << __PRETTY_FUNCTION__ << "\n";   // (1)
    if (a < b) return b;
    return a;
}

int main() {
    std::cout << lonHon(3, 4) << "\n";                  // (2)
    std::cout << lonHon(2.5, 1.5) << "\n";              // (3)
    std::cout << lonHon<double>(3, 4.5) << "\n";        // (4)
    std::cout << lonHon(std::string("an"), std::string("binh")) << "\n";  // (5)
    auto gap = [](auto x) {                             // (6)
        std::cout << "  " << __PRETTY_FUNCTION__ << "\n";
        return x + x;
    };
    std::cout << gap(21) << "\n";
    std::cout << gap(std::string("ha")) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | Hai đối số `int`: suy ra `T = int`, sinh bản `lonHon<int>`; (1) in tên bản đó | file có bản `int` |
| (3) | Hai `double`: suy ra `T = double`, sinh bản thứ hai | thêm bản `double` |
| (4) | Ghi `<double>`: không suy luận, `3` đổi sang `double`; bản `double` **đã có**, dùng lại, không sinh thêm | vẫn hai bản (`int`, `double`) |
| (5) | Hai `std::string`: bản thứ ba | ba bản: `int`, `double`, `string` |
| (6) | Lambda có `auto`: gọi với `int` rồi `std::string` sinh hai bản của hàm gọi | thêm hai bản của hàm gọi lambda |

**Kết quả khi chạy** (g++ 11.4, tên đầy đủ của `string` rất dài nên bản in này giữ nguyên chữ g++ in):

```text
  T lonHon(T, T) [with T = int]
4
  T lonHon(T, T) [with T = double]
2.5
  T lonHon(T, T) [with T = double]
4.5
  T lonHon(T, T) [with T = std::__cxx11::basic_string<char>]
binh
  main()::<lambda(auto:1)> [with auto:1 = int]
42
  main()::<lambda(auto:1)> [with auto:1 = std::__cxx11::basic_string<char>]
haha
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Có **ba** bản `lonHon` (`int`, `double`, `string`), không phải bốn: lời gọi (4) dùng lại bản `double`. Chữ in `__PRETTY_FUNCTION__` đổi theo trình biên dịch. Cách xem bản sinh ra trong file thật: lệnh `nm` liệt kê tên các hàm có trong file đã biên dịch, và `-C` giải mã tên cho dễ đọc (biên dịch `-O0`, các dòng `string` dài đã lược):

```text
W double lonHon<double>(double, double)
W int lonHon<int>(int, int)
W ... lonHon<std::__cxx11::basic_string<...> >(...)
t auto main::{lambda(auto:1)#1}::operator()<int>(int) const
t auto main::{lambda(auto:1)#1}::operator()<std::__cxx11::basic_string<...> >(...) const
```

Ba bản `lonHon` và hai bản của hàm gọi trong lambda, đúng số kiểu đã dùng. (Chữ `W` ở đầu là ký hiệu "yếu": nhiều file cùng sinh một bản vẫn ghép được; ta chỉ đọc phần tên.) Các **Thử thay đổi** (đã chạy):

- **Viết `lonHon(3, 4.5)`**: `error: no match for call to ‘lonHon(int, double)’`, ghi chú `deduced conflicting types for parameter ‘T’ (‘int’ and ‘double’)`. `std::max(3, 4.5)` cho lỗi cùng kiểu (`no matching function for call to ‘max(int, double)’`).
- **Đổi `typename` thành `class`** ở dòng template: kết quả y hệt, từng chữ.

### Ví dụ 2: `Ngan<T, N>`, template lớp với tham số kiểu và không phải kiểu

Một ngăn xếp nhỏ (stack dữ liệu, khác stack bộ nhớ của Bài 02: thêm và lấy cùng một đầu, cái vào sau ra trước) giữ tối đa `N` phần tử kiểu `T`, nằm trên một `std::array<T, N>` ([Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md)). `N` có mặc định 4.

```cpp
#include <array>
#include <iostream>
#include <string>

template <typename T, int N = 4>                       // (1)
class Ngan {
    static_assert(N > 0, "N phai duong");              // (2)
public:
    bool them(const T& v) {                            // (3)
        if (dem_ == N) return false;
        a_[dem_] = v;
        ++dem_;
        return true;
    }
    bool lay(T& ra) {                                  // (4)
        if (dem_ == 0) return false;
        --dem_;
        ra = a_[dem_];
        return true;
    }
    int size() const { return dem_; }

private:
    std::array<T, N> a_;                               // (5)
    int dem_ = 0;
};

int main() {
    Ngan<int> a;                                       // (6)
    for (int i = 1; i <= 5; ++i) {
        std::cout << "them " << i << ": " << a.them(i * 10) << "\n";
    }
    int x = 0;
    a.lay(x);
    std::cout << "lay ra " << x << ", con " << a.size() << "\n";

    Ngan<std::string, 2> b;                            // (7)
    b.them("an");
    b.them("binh");
    std::cout << "b day? " << !b.them("chi") << "\n";
    std::cout << sizeof(Ngan<int, 4>) << " " << sizeof(Ngan<int, 8>) << "\n";  // (8)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Hai chỗ trống: kiểu `T` và số `N`; `N` mặc định 4 | |
| (6) | `Ngan<int>` = `Ngan<int, 4>`: một lớp thật, `a_` là `array<int, 4>` | `a`: `[? ? ? ?]`, `dem_` = 0 |
| `them` 1..5 | Bốn lần đầu nhận (10, 20, 30, 40); lần năm `dem_ == N` nên trả `false` | `[10 20 30 40]`, `dem_` = 4 |
| `lay(x)` | `dem_` còn 3, `x` = `a_[3]` = 40 | `[10 20 30 (40)]`, `dem_` = 3 |
| (7) | `Ngan<std::string, 2>`: lớp thứ hai, hoàn toàn khác `Ngan<int, 4>` | `[an binh]`, đầy |
| (8) | Cỡ nằm trong kiểu nên `sizeof` khác nhau | in `20 36` |

**Kết quả khi chạy:**

```text
them 1: 1
them 2: 1
them 3: 1
them 4: 1
them 5: 0
lay ra 40, con 3
b day? 1
20 36
```

Mình chạy với ASan + UBSan: sạch. `20` và `36` là của máy mình (`int` 4 byte: 4 × 4 + `dem_` 4 = 20; 8 × 4 + 4 = 36), máy khác có thể ra số khác. Xem bản sinh ra bằng `nm -C` (rút gọn `string`): trong các hàm bạn gọi có `Ngan<int, 4>::them`, `lay`, `size` và `Ngan<string, 2>::them` (cộng hàm tạo/hủy tự sinh); **không có** `Ngan<string, 2>::lay` hay `size` vì chương trình không gọi. Các **Thử thay đổi** (đã chạy, đều lỗi biên dịch):

- **Thêm `Ngan<int, 0> z;`**: `error: static assertion failed: N phai duong`.
- **Thêm `Ngan<int, 2> p; Ngan<int, 4> q; p = q;`**: `no match for ‘operator=’ (operand types are ‘Ngan<int, 2>’ and ‘Ngan<int, 4>’)`: hai cỡ là hai kiểu khác nhau.
- **Thêm `Ngan<int> a2; a2.them("x");`**: `invalid conversion from ‘const char*’ to ‘int’`. **Thêm `a2.foo();`**: `‘class Ngan<int, 4>’ has no member named ‘foo’`.

### Ví dụ 3: chuyên biệt hóa `Nhan<bool>`

`Nhan<T>::in` in giá trị trong ngoặc vuông. Với `bool`, in `1`/`0` thì khó đọc, nên viết bản riêng in `dung`/`sai`.

```cpp
#include <iostream>
#include <string>

template <typename T>
struct Nhan {
    static void in(const T& v) { std::cout << "[" << v << "]\n"; }   // (1)
};

template <>
struct Nhan<bool> {                                                   // (2)
    static void in(bool v) { std::cout << "[" << (v ? "dung" : "sai") << "]\n"; }
};

int main() {
    Nhan<int>::in(42);                                                // (3)
    Nhan<std::string>::in("xin chao");
    Nhan<bool>::in(true);                                             // (4)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Bản chung cho mọi `T`; `static` nên gọi `Nhan<int>::in(...)` không cần tạo món ([Bài 31](31-lop-dong-goi.md)) | |
| (2) | `template <>` rồi `Nhan<bool>`: bản **dành riêng** cho `bool` | |
| (3) | `T = int`: dùng bản chung, in `[42]` | |
| (4) | `T = bool`: trình biên dịch chọn bản riêng (2) | in `[dung]` |

**Kết quả khi chạy:**

```text
[42]
[xin chao]
[dung]
```

Mình chạy với ASan + UBSan: sạch. **Thử thay đổi: xóa khối `template <> struct Nhan<bool> {...};`** (đã chạy): dòng cuối thành `[1]`, vì bản chung in `bool` ra `1`.

### Ví dụ 4: cùng việc "cộng diện tích", làm bằng hàm ảo và bằng template

`Tron`, `Vuong` kế thừa `Hinh` giống ý của Bài 33 (tên lớp ngắn lại); `Luoi` **không** kế thừa gì, chỉ có hàm `dienTich` cùng tên. `tongAo` dùng hàm ảo, `tongMau` dùng template.

```cpp
#include <iostream>
#include <memory>
#include <vector>

class Hinh {
public:
    virtual ~Hinh() = default;
    virtual double dienTich() const = 0;
};

class Tron : public Hinh {
public:
    explicit Tron(double r) : r_(r) {}
    double dienTich() const override { return 3 * r_ * r_; }
private:
    double r_;
};

class Vuong : public Hinh {
public:
    explicit Vuong(double c) : c_(c) {}
    double dienTich() const override { return c_ * c_; }
private:
    double c_;
};

struct Luoi {                                                 // (1)
    double dienTich() const { return 7; }
};

double tongAo(const std::vector<std::unique_ptr<Hinh>>& ds) {     // (2)
    double t = 0;
    for (const auto& h : ds) t += h->dienTich();
    return t;
}

template <typename H>
double tongMau(const std::vector<H>& ds) {                   // (3)
    double t = 0;
    for (const auto& h : ds) t += h.dienTich();
    return t;
}

int main() {
    std::vector<std::unique_ptr<Hinh>> lan;                  // (4)
    lan.push_back(std::make_unique<Tron>(1));
    lan.push_back(std::make_unique<Vuong>(2));
    std::cout << "ao:  " << tongAo(lan) << "\n";

    std::vector<Tron> toanTron = {Tron(1), Tron(2)};         // (5)
    std::vector<Luoi> toanLuoi = {Luoi(), Luoi()};
    std::cout << "mau: " << tongMau(toanTron) << " " << tongMau(toanLuoi) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (4) | Dãy con trỏ tới `Hinh`: trộn một tròn và một vuông | `[ptr][ptr]` tới hai món ở kho |
| `tongAo(lan)` (2) | `h->dienTich()` là hàm ảo: chạy bản của món thật, 3 + 4 | in `ao:  7` |
| (5) | Mỗi dãy chỉ **một kiểu**: `vector<Tron>` và `vector<Luoi>` | hai dãy, món nằm ngay trong dãy |
| `tongMau(toanTron)` (3) | `H = Tron`: sinh bản `tongMau<Tron>`, gọi thẳng `Tron::dienTich`: 3 + 12 | 15 |
| `tongMau(toanLuoi)` | `H = Luoi`: bản thứ hai; `Luoi` (1) không có lớp cha vẫn dùng được, chỉ cần có `dienTich()` | 7 + 7 = 14 |

**Kết quả khi chạy:**

```text
ao:  7
mau: 15 14
```

Mình chạy với ASan + UBSan: sạch. `nm -C` thấy đúng hai bản `tongMau<Luoi>` và `tongMau<Tron>`. Cái mà hàm ảo làm được và template không: `tongAo` nhận **lẫn** tròn và vuông trong một dãy. **Thử thay đổi (đã chạy):** thêm `tongMau(lan);` vào `main` thì g++ báo `required from here` ở dòng đó và `error: ‘const class std::unique_ptr<Hinh>’ has no member named ‘dienTich’`: `H` bị suy ra là `unique_ptr<Hinh>`, và lỗi chỉ lộ khi sinh bản, không lộ lúc viết template.

### Ví dụ 5: tách template ra `.cpp`, gặp `undefined reference`

Ba file trong một thư mục tạm (ở đây không dùng ` ```cpp ` vì cần ghép nhiều file). `-c` bảo g++ chỉ dịch ra file `.o`, chưa liên kết; lệnh cuối `g++ main.o lon.o -o app` mới ghép các `.o` thành chương trình.

```text
lon.h:
template <typename T>
T lonHon(T a, T b);
```

```text
lon.cpp:
#include "lon.h"
template <typename T>
T lonHon(T a, T b) { if (a < b) return b; return a; }
```

```text
main.cpp:
#include <iostream>
#include "lon.h"
int main() { std::cout << lonHon(3, 4) << "\n"; return 0; }
```

| Bước | Chuyện gì xảy ra | Trong file đối tượng |
|---|---|---|
| `g++ -c lon.cpp -o lon.o` | Có thân template nhưng chưa ai dùng, **không sinh bản nào** | `nm lon.o` không in gì |
| `g++ -c main.cpp -o main.o` | Chỉ thấy khai báo trong `lon.h`; để lại lời gọi `lonHon<int>` chưa có thân | `U int lonHon<int>(int, int)` (`U`: chưa định nghĩa) |
| `g++ main.o lon.o -o app` | Bước liên kết tìm `lonHon<int>` ở đâu cũng không có | lỗi |

Kết quả thật khi liên kết:

```text
/usr/bin/ld: main.o: in function `main':
main.cpp:(.text+0x13): undefined reference to `int lonHon<int>(int, int)'
collect2: error: ld returned 1 exit status
```

Hai lần biên dịch đều sạch lỗi, chỉ bước liên kết hỏng. **Chữa (đã chạy, in `4`):** bỏ `lon.cpp`, chuyển cả thân vào `lon.h`: `main.cpp` thấy thân nên tự sinh `lonHon<int>`. Cách chữa thứ hai (đã chạy, cũng in `4`): giữ `lon.cpp` và thêm dòng `template int lonHon<int>(int, int);` ở cuối nó, ép sinh bản `int` tại đó; cách này chỉ phục vụ các kiểu đã liệt kê.

## Go: generics có ràng buộc, không có chuyên biệt hóa

!!! info "Bạn biết Go?"
    Mình đã chạy chương trình Go 1.27.1 nhỏ để kiểm các ý dưới đây.
    - **Cùng ý, khác cú pháp**: `func Max[T cmp.Ordered](a, b T) T` và `type Hop[T any] struct{...}` tương ứng `template <typename T>`. `Max(3, 4)`, `Max("an", "binh")`, `Max[float64](3, 4.5)` đều chạy.
    - **Suy luận khác nhau**: Go mình dùng cho `Max(3, 4.5)` ra `4.5`, vì cả hai là hằng chưa định kiểu; C++ lỗi (mục 2). Nhưng `Max(i, f)` với `i` là `int` còn `f` là `float64` thì Go cũng lỗi: `type float64 of f does not match inferred type int for T`.
    - **Ràng buộc**: Go kiểm bằng một **constraint** (một interface). `Max(P{1}, P{2})` với `P` là struct báo `P does not satisfy cmp.Ordered`.
    - **Lúc nào kiểm**: thân hàm cũng được kiểm theo constraint ngay lúc định nghĩa: `func Dung[T any](a, b T) bool { return a < b }` lỗi `type parameter T cannot use operator <` dù chưa ai gọi. C++ (không dùng concepts) kiểm lúc **sinh bản**, như duck typing lúc biên dịch: mình đã biên dịch một template chưa ai gọi mà thân gọi `x.size()` thì g++ im lặng, đến khi gọi với `int` mới báo lỗi.
    - **Không có chuyên biệt hóa**: Go không có cách viết bản riêng cho `bool` như `Nhan<bool>`; muốn khác thì rẽ nhánh trong thân hoặc dùng interface.
    - **Cài đặt, chỉ để lấy ý**: với trình biên dịch gc mình dùng, `Max` cho `int`, `float64`, `string` ra ba ký hiệu `main.Max[go.shape.int]`, `[go.shape.float64]`, `[go.shape.string]`; còn `Max(A(1), A(2))`, `Max(B(3), B(4))` với `type A int`, `type B int` **dùng chung** bản `go.shape.int` (`go tool nm` thấy một ký hiệu; biên dịch với `-gcflags=-l` để `Max` không bị inline, không thì khó thấy). Cách này gọi là "GC shape stenciling"; đó là chi tiết cài đặt của gc, spec Go không quy định và có thể đổi. C++ thì mỗi kiểu một bản (Ví dụ 1).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Template là gì? Khác macro thế nào?"
    Template là mã viết một lần với tham số kiểu (hoặc số); trình biên dịch sinh một bản riêng cho mỗi tổ hợp tham số được dùng (instantiation) và kiểm kiểu như code thường. Macro (`#define`) là bộ tiền xử lý thay chữ trước khi biên dịch, không biết kiểu và không biết phạm vi. Mình chạy `#define BINH(x) x * x` rồi `BINH(1 + 2)`: ra `5` chứ không phải `9`, vì chữ bị thay thành `1 + 2 * 1 + 2`.

??? question "Template và đa hình lúc chạy khác nhau thế nào? Chọn cái nào?"
    Đa hình lúc biên dịch (template) chọn theo kiểu lúc biên dịch, không cần lớp cha chung, không có vtable, thường inline được, nhưng mỗi kiểu một bản mã sinh lúc biên dịch và một dãy chỉ chứa một kiểu. Đa hình lúc chạy (hàm ảo) chọn theo món thật lúc chạy, trộn nhiều loại trong một dãy, hàm duyệt chỉ một bản (mỗi lớp con vẫn có hàm ghi đè riêng, chọn lúc chạy qua vtable), đổi lại gọi gián tiếp. Cần trộn loại hoặc quyết định lúc chạy thì hàm ảo; cùng thuật toán cho nhiều kiểu biết trước thì template.

??? question "Tại sao định nghĩa template thường nằm trong header?"
    Mỗi file `.cpp` được biên dịch riêng. Để sinh bản cho `lonHon<int>`, trình biên dịch phải thấy thân template ngay tại file đang dịch; nếu thân nằm ở `.cpp` khác thì file dùng chỉ để lại lời gọi, còn file có thân không được yêu cầu sinh bản `int`, nên bước liên kết báo `undefined reference` (mình đã chạy). Chữa bằng cách để thân trong header, hoặc sinh bản tường minh cho vài kiểu cố định.

??? question "Chuyên biệt hóa (specialization) là gì?"
    Là viết một bản template riêng cho một kiểu (toàn phần, `template <> struct Nhan<bool>`) hoặc một nhóm kiểu (từng phần, như mọi con trỏ); khi dùng đúng kiểu đó, trình biên dịch chọn bản riêng. Ví dụ trong thư viện chuẩn là `std::vector<bool>` (g++) lưu mỗi phần tử một bit, nên `&v[0]` không cho `bool*`. Go không có chuyên biệt hóa.

??? question "Code bloat là gì?"
    Mỗi kiểu dùng sinh một bản mã riêng, nên dùng một template với nhiều kiểu thì chương trình lớn hơn. Mình đo một hàm template với 1 rồi 8 kiểu số: phần mã của file đối tượng tăng từ 11818 lên 89528 byte ở `-O0`, và từ 1716 lên 14300 byte ở `-O2`; số đo đổi theo hàm, kiểu, cờ, trình biên dịch. Giảm bằng cách bớt kiểu thừa, để phần không phụ thuộc `T` ở hàm thường, hoặc dùng hàm ảo khi một hàm duyệt chung là đủ.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Trộn hai kiểu cho một `T`"
    `lonHon(3, 4.5)` lỗi vì suy ra hai `T` khác nhau (Ví dụ 1). Ghi kiểu rõ: `lonHon<double>(3, 4.5)`; Go có thể cho qua nếu cả hai là hằng, C++ thì không.

!!! warning "Lỗi 2: Khai báo template ở `.h`, định nghĩa ở `.cpp`"
    Hai file đều biên dịch được, đến bước liên kết mới báo `undefined reference` (Ví dụ 5). Để thân template trong header.

!!! warning "Lỗi 3: Tin rằng template đã được kiểm kỹ khi viết"
    Thân gọi `x.size()` mà chưa ai dùng thì g++ không phàn nàn; lỗi chỉ hiện khi có người gọi với kiểu sai, và hiện trong thư viện (mục 6). Thử gọi template với vài kiểu thật, hoặc dùng `static_assert`/concepts để báo lỗi sớm và rõ.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="34" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Cho template `lon` dưới đây. Dòng nào lỗi biên dịch?

```text
template <typename T>
T lon(T a, T b) { if (a < b) return b; return a; }
// dòng A:  lon(2, 7)
// dòng B:  lon(2, 7.5)
// dòng C:  lon<double>(2, 7)
```

- Dòng B và dòng C, vì ghi `<double>` mà đối số `2` và `7` lại là `int`
- Chỉ dòng C, vì đã ghi kiểu rõ thì không được kèm đối số có kiểu khác
- Chỉ dòng B, vì hai đối số cho hai kiểu khác nhau mà chỉ có một `T`
- Không dòng nào, vì `int` được tự đổi sang `double` giống mọi hàm thường

<p class="giai-thich" markdown>Ở dòng B, `2` là `int` còn `7.5` là `double`, nên trình biên dịch suy ra hai kiểu cho cùng một `T` và báo lỗi. Dòng C ghi `<double>` nên không cần suy luận và `2`, `7` được đổi sang `double` như hàm thường; dòng A cả hai đều `int`. Hàm thường đổi được `int` sang `double`, nhưng chính phần suy luận của template mới là chỗ vấp. Vậy "ghi kiểu rõ thì không được kèm đối số khác kiểu" là hiểu sai: chính cách đó sửa lỗi dòng B.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Một chương trình gọi `lon(1, 2)`, `lon(3, 4)`, `lon(1.5, 2.5)` và `lon<long>(1, 2)`, với `lon` là template hàm như câu trước. Trình biên dịch sinh bao nhiêu bản của `lon`?

- Bốn bản, vì mỗi lời gọi sinh một bản riêng cho mình
- Ba bản, vì có ba kiểu khác: `int`, `double`, `long`
- Hai bản, vì chỉ có hai nhóm kiểu: số nguyên, số thực
- Một bản dùng chung, vì thân hàm viết đúng một lần

<p class="giai-thich" markdown>Mỗi **kiểu** khác nhau được điền vào `T` sinh một bản: `int` (cho hai lời gọi đầu), `double` và `long`, tổng ba; hai lời gọi `lon(1, 2)` và `lon(3, 4)` dùng chung bản `int`. Số lời gọi không quyết định số bản, nên bốn là sai. Template không gom kiểu theo nhóm "nguyên/thực": `int` và `long` là hai bản riêng. Và thân viết một lần không có nghĩa là chỉ có một bản mã; mình đã thấy ba bản trong `nm` ở Ví dụ 1 với ba kiểu.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Vì sao thân của template hàm thường phải để trong header, không để ở file `.cpp` riêng?

- Vì chuẩn C++ cấm viết thân template trong file `.cpp`, nên chỉ còn chỗ ở header
- Vì mã trong header được nạp nhanh hơn nên chương trình chạy nhanh hơn
- Vì template được sinh bản ngay lúc chạy nên thân phải sẵn trong bộ nhớ
- Vì nơi dùng phải thấy thân để sinh bản, không thì có `undefined reference`

<p class="giai-thich" markdown>Mỗi file `.cpp` được biên dịch riêng; file `main.cpp` cần thân template để sinh bản `int`, còn file `lon.cpp` có thân thì không ai nhờ nó sinh bản đó. Không có bản nào thì bước liên kết báo `undefined reference` (mình đã chạy). Chuẩn không cấm đặt thân ở `.cpp`, vì sinh bản tường minh cho vài kiểu cố định vẫn dùng được. Sinh bản xảy ra lúc biên dịch chứ không phải lúc chạy, và vị trí header không làm chương trình chạy nhanh hơn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Việc cộng diện tích một dãy hình tròn lẫn hình vuông. Phát biểu nào về hai cách làm đúng?

- Hàm ảo trộn được hai loại trong một dãy con trỏ `Hinh`; một `vector<H>` chỉ chứa một kiểu `H`
- Template trộn được hai loại trong một `vector<H>`, vì `H` chọn lại cho từng phần tử lúc chạy
- Hàm ảo không cần lớp cha chung, còn template bắt buộc các kiểu phải có chung một lớp cha
- Cùng có hàm `dienTich` là đủ để một `vector<H>` chứa cả hình tròn lẫn hình vuông

<p class="giai-thich" markdown>`vector<H>` có đúng một kiểu phần tử `H` đã định từ lúc biên dịch, nên muốn lẫn hai loại phải dùng con trỏ lớp cha và hàm ảo. `H` không được chọn lại lúc chạy: template là đa hình lúc biên dịch. Tên hàm giống nhau cũng không gộp được hai kiểu vào một `vector<H>`. Và hai vế bị đảo: hàm ảo cần lớp cha chung, còn template thì không (`Luoi` ở Ví dụ 4).</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn sau và cho biết kết quả khi biên dịch bằng g++ (`-std=c++17 -Wall -Wextra`).

```text
template <typename T>
int f(T x) { return x.size(); }
int main() { }
```

- Lỗi biên dịch, vì `T` chưa biết là kiểu nào nên không thể kiểm `x.size()` được
- Biên dịch được, vì chưa ai gọi `f` nên chưa có bản nào để kiểm `x.size()`
- Biên dịch được, nhưng bước liên kết báo lỗi vì không tìm thấy hàm `size`
- Lỗi biên dịch, vì template phải được gọi ít nhất một lần trong chương trình này

<p class="giai-thich" markdown>Mình đã biên dịch đoạn này: g++ không báo lỗi hay cảnh báo. Thân hàm phụ thuộc vào `T`, nên chuyện `x.size()` có hợp lệ hay không chỉ được kiểm khi sinh bản cho một kiểu cụ thể, mà không ai gọi `f`. Gọi `f(3)` thì mới báo `request for member ‘size’ in ‘x’, which is of non-class type ‘int’` (đã chạy). Và `main` rỗng không chạy gì nên cũng chẳng có lỗi lúc chạy; template cũng không bắt buộc phải được gọi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** `Ngan<int, 3>` và `Ngan<int, 5>` là hai bản của template `template <typename T, int N> class Ngan`. Quan hệ giữa hai kiểu này là gì?

- Cùng một kiểu, vì `T` giống nhau; số 3 và 5 chỉ là cỡ ban đầu, đổi được lúc chạy
- Hai kiểu khác nhau nhưng gán được cho nhau, vì cùng `T` là `int`
- Hai kiểu khác nhau, như `array<int, 3>` và `array<int, 5>`; gán nhau là lỗi
- Cùng một kiểu, vì `N` chỉ là số thường, không nằm trong tên kiểu

<p class="giai-thich" markdown>`N` là tham số không phải kiểu: giá trị của nó nằm **trong** kiểu, nên `Ngan<int, 3>` và `Ngan<int, 5>` là hai lớp riêng, và gán cho nhau báo `no match for ‘operator=’` (mình đã chạy ở Ví dụ 2). Số trong `< >` phải biết lúc biên dịch nên không đổi được lúc chạy. Cùng `T` không làm hai lớp gán được cho nhau. Và `N` không phải số thường: nó nằm trong tên kiểu, nên hai giá trị khác nhau cho hai kiểu khác nhau.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Điều nào đúng khi so generics của Go (`func Max[T cmp.Ordered](a, b T) T`) với template C++?

- Go kiểm thân hàm theo constraint ngay khi định nghĩa; C++ không concepts kiểm khi sinh bản
- Go sinh một bản riêng cho từng kiểu như C++, và cũng cho chuyên biệt hóa từng kiểu
- Go kiểm ràng buộc lúc chạy, nên sai kiểu chỉ lộ ở lần chạy đầu tiên
- C++ kiểm ràng buộc bằng interface lúc biên dịch, còn Go chỉ kiểm khi gọi hàm

<p class="giai-thich" markdown>Mình đã chạy Go 1.27.1: `a < b` trong hàm với `T any` bị chặn ngay ở thân hàm, và `Max` của hai struct bị chặn lúc biên dịch với `does not satisfy cmp.Ordered`; C++ không concepts thì chỉ kiểm khi sinh bản (Ví dụ 4, Câu 5). Go không có chuyên biệt hóa, và trình biên dịch gc còn cho nhiều kiểu cùng hình dạng (như `int` và `type A int`) dùng chung một bản. Go kiểm lúc biên dịch, không đợi lúc chạy. Còn câu nói C++ kiểm bằng interface thì đảo ngược: constraint (interface) là của Go, và hàm `Dung` chưa ai gọi vẫn bị Go chặn, nên không phải "chỉ khi gọi".</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Template** là bản vẽ có chỗ trống cho kiểu (hoặc số): `template <typename T>` (`class` cũng được, giống hệt); mỗi kiểu được dùng sinh **một bản riêng** lúc biên dịch (mình chạy: 3 kiểu, 3 bản `lonHon`, thấy bằng `nm` và `__PRETTY_FUNCTION__`). `max(3, 4.5)` lỗi vì suy ra hai `T`; ghi `max<double>(3, 4.5)`.
2. **Template lớp** (`vector<int>`, `Ngan<T, N>`): mỗi bộ tham số là một lớp riêng; tham số không phải kiểu như `N` nằm trong kiểu (`array<int, 3>` khác `array<int, 5>`), có giá trị mặc định; chỉ hàm thành viên được gọi mới sinh; **chuyên biệt hóa** là bản riêng cho một kiểu (`Nhan<bool>`).
3. **Template vs hàm ảo**: lúc biên dịch (không cần lớp cha chung, gọi thẳng, một bản mỗi kiểu, một dãy một kiểu) so với lúc chạy (trộn loại, một hàm duyệt chung, mỗi lớp con vẫn có hàm ghi đè riêng, gọi gián tiếp). Không bên nào luôn tốt hơn; mình không đo thời gian.
4. **Giá cả**: lỗi dài (114 dòng cho một `sort` thiếu `operator<`, đọc từ dòng `error:` và `required from here`), code bloat (mình đo: `.text` tăng 11818 lên 89528 byte khi 1 lên 8 kiểu ở `-O0`, đổi theo máy và cờ), và thân template phải ở header (tách `.cpp` thì `undefined reference`).
5. Chỉ nhắc: `static_assert`/`type_traits`, concepts C++20 (g++ 11.4 `-std=c++20` chạy được), SFINAE, lambda `auto` là template. Go: generics kiểm constraint ngay ở thân hàm, không có chuyên biệt hóa, gc cho các kiểu cùng "hình dạng" dùng chung một bản (chi tiết cài đặt).
