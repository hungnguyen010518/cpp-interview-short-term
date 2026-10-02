# Bài 16 — std::vector: mảng co giãn

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Biết STL là gì, đọc được `std::vector<int>` (phần trong `< >` là gì), và dùng `push_back`, `size`, `[]`, `pop_back`, duyệt bằng `for`.
    - Phân biệt **size** (số phần tử đang có) với **capacity** (số chỗ đã xin), và hiểu vì sao `push_back` khi đầy làm vector tái cấp phát (xin mảng mới rồi dọn sang), khiến tham chiếu và con trỏ cũ có thể hỏng.
    - Chọn đúng `reserve`, `[]` hay `at`, `const&` hay truyền theo giá trị, `push_back` hay `emplace_back`.

**Bạn cần biết trước:** [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (`#include`, `std::`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, heap), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`&`, `const&`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, `try`/`catch`) và [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (sao chép sâu), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (move, `noexcept`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`for` duyệt dãy) và [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UB, ASan).

## 🧠 Câu chuyện mở đầu

Bạn có một **kệ sách** đặt ở kho đồ của trường (heap). Tổng số ô trên kệ, có sách hay chưa, là **capacity**; số sách đang xếp trên đó là **size**. Mua thêm sách thì xếp vào ô chưa có sách ở cuối kệ, rất nhanh.

Trên bàn học của bạn (stack) chỉ có một **tờ giấy nhỏ** ghi: kệ đang ở đâu, đang có bao nhiêu sách, kệ có bao nhiêu ô. Kệ đầy mà vẫn mua sách thì bạn thuê một kệ **to gấp đôi** ở kho, dọn sách sang, trả kệ cũ, rồi **sửa tờ giấy** cho trỏ kệ mới. Ai còn giữ một tờ giấy khác ghi "sách nằm ở ô số 5 của kệ cũ" thì sẽ đi tới chỗ đã bị dỡ.

**`std::vector`** chính là cái kệ đó: một dãy phần tử nằm **liền nhau**, tự xin kệ mới khi đầy và tự trả kệ khi bạn xong (RAII, [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)).

!!! info "Chỗ nào ví dụ kệ sách không còn đúng?"
    Tờ giấy ghi kệ chính là đối tượng `std::vector` (nhỏ, ở stack), còn kệ là mảng ở heap (mục 3). Vector không dọn "sách" bằng tay: nó chép (hoặc move, [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)) từng phần tử sang kệ mới, và chuyện đó tốn thời gian tỉ lệ với số phần tử. Con số "gấp đôi" cũng chỉ là cách làm của một bản thư viện, không phải luật (mục 4).

## 📖 Giải thích

### 1. STL là gì, và `std::vector<int>` đọc thế nào

**STL** (Standard Template Library, "thư viện khuôn mẫu chuẩn") là bộ công cụ có sẵn đi kèm C++: các **kiểu chứa dữ liệu** (container: vector, map, set...), các hàm làm việc với chúng (sắp xếp, tìm kiếm...). Giống phần `slices`, `maps`, `sort` trong thư viện chuẩn của Go, nhưng viết bằng khuôn mẫu (template, giải thích ngay dưới) nên dùng được với nhiều kiểu. Nhóm bài này dạy dần từng món; bài này là món đầu tiên và dùng nhiều nhất.

Muốn dùng vector, viết `#include <vector>` ở đầu file (nhắc lại [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md): `#include` bảo trình biên dịch nạp phần khai báo của thư viện). Mọi thứ của thư viện chuẩn nằm trong "họ" `std`, nên tên đầy đủ là `std::vector`.

**Khuôn mẫu (template)** là generics của C++: một đoạn code viết một lần với "kiểu để trống", giống `[]T` hay `func F[T any]` của Go. Khi bạn điền kiểu cụ thể, trình biên dịch sinh ra một kiểu riêng cho kiểu đó. Cái nằm trong `< >` gọi là **tham số khuôn mẫu (template argument)**: nó cho biết vector chứa **loại phần tử nào**. Bạn đã gặp cú pháp này ở `std::unique_ptr<Cay>` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)).

```text
std::vector<int>          // dãy các int            (Go: []int)
std::vector<double>       // dãy các double         (Go: []float64)
std::vector<std::string>  // dãy các chuỗi          (Go: []string)
```

Một vector chỉ chứa **một loại** phần tử, và loại đó phải ghi ra lúc khai báo. Vector này khác vector kia hoàn toàn: `std::vector<int>` và `std::vector<double>` là hai kiểu khác nhau.

### 2. Tạo vector và dùng các thao tác cơ bản

Có vài cách tạo. Chương trình dưới thử từng cách, rồi thêm, bớt, duyệt.

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> a;                     // (1)
    std::vector<int> b = {3, 1, 2};         // (2)
    std::vector<int> c(4, 7);               // (3)
    std::vector<int> d(5);                  // (4)
    std::vector<int> e{5};                  // (5)
    std::cout << "a: " << a.size() << " phan tu, rong? " << a.empty() << "\n";
    std::cout << "b: " << b.size() << " phan tu, b[0] = " << b[0] << "\n";
    std::cout << "c: " << c.size() << " phan tu, c[3] = " << c[3] << "\n";
    std::cout << "d: " << d.size() << " phan tu, d[4] = " << d[4] << "\n";
    std::cout << "e: " << e.size() << " phan tu, e[0] = " << e[0] << "\n";

    a.push_back(10);                        // (6)
    a.push_back(20);
    a.push_back(30);
    std::cout << "a sau push_back: ";
    for (int x : a) {                       // (7)
        std::cout << x << " ";
    }
    std::cout << "(size " << a.size() << ", cuoi " << a.back() << ")\n";
    a.pop_back();                           // (8)
    std::cout << "sau pop_back: size " << a.size() << ", cuoi " << a.back() << "\n";
    return 0;
}
```

Giải nghĩa các thao tác mới: `v.size()` là số phần tử đang có; `v.empty()` trả `true`/`false` (`std::cout` in thành 1/0); `v[i]` là phần tử thứ `i` (đếm từ 0, như mảng và slice); `v.push_back(x)` thêm `x` vào **cuối**; `v.pop_back()` bỏ phần tử cuối; `v.back()` là phần tử cuối. Dòng (7) là `for` duyệt dãy ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)): `int x` là bản chép của từng phần tử.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1)–(2) | `a` rỗng; `b` có ba phần tử 3, 1, 2 | `a`: size 0; `b`: `[3 1 2]` |
| (3) | **Ngoặc tròn** `(4, 7)`: bốn phần tử, mỗi cái bằng 7 | `c`: `[7 7 7 7]` |
| (4) | `(5)`: năm phần tử, tự đặt về 0 | `d`: `[0 0 0 0 0]` |
| (5) | **Ngoặc nhọn** `{5}`: danh sách một phần tử bằng 5. Không phải "5 phần tử"! | `e`: `[5]` |
| in 5 dòng | Kích thước và phần tử mẫu của năm vector | xem kết quả |
| (6) | Ba lần `push_back`: `a` thành 10, 20, 30 | `a`: `[10 20 30]` |
| (7) | Duyệt, in từng số; rồi in size 3 và phần tử cuối 30 | không đổi |
| (8) | `pop_back` bỏ 30; size còn 2, `back()` giờ là 20 | `a`: `[10 20]` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -pthread`):

```text
a: 0 phan tu, rong? 1
b: 3 phan tu, b[0] = 3
c: 4 phan tu, c[3] = 7
d: 5 phan tu, d[4] = 0
e: 1 phan tu, e[0] = 5
a sau push_back: 10 20 30 (size 3, cuoi 30)
sau pop_back: size 2, cuoi 20
```

Ngoặc tròn `(5)` nghĩa là "cỡ", ngoặc nhọn `{5}` nghĩa là "danh sách giá trị": lỗi hay gặp khi mới học (nhắc lại ở phần ⚠️).

### 3. Vector bên trong: size, capacity và mảng ở heap

Một đối tượng `std::vector` về ý niệm chỉ giữ **ba thứ** (thư viện thật thường lưu bằng ba con trỏ; chuẩn không quy định cách bố trí): con trỏ tới mảng các phần tử, **size**, và **capacity**. Bản thân đối tượng nhỏ và (nếu là biến cục bộ) nằm trên stack; còn mảng các phần tử nằm ở heap ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)).

```text
  Stack                      Heap (địa chỉ minh họa — máy bạn sẽ in số khác)
  +----------------+         0x5000
  | v              |         +----+----+----+----+----+
  |  con trỏ  -----+-------> | 10 | 20 | 30 |    |    |
  |  size     = 3  |         +----+----+----+----+----+
  |  capacity = 5  |          <- size=3 ->
  +----------------+          <------ capacity=5 ------>
```

- **size**: số phần tử đang dùng (ba ô có số). `v.size()`.
- **capacity**: số phần tử mảng đang chứa được mà chưa phải xin chỗ mới (năm ô). `v.capacity()`. Luôn có capacity ≥ size.

Hai ô cuối là chỗ **đã xin nhưng chưa có phần tử**. Chạm vào chúng bằng `v[3]` là truy cập ngoài size, tức hành vi không xác định (mục 6), dù chúng nằm trong capacity.

!!! info "Bạn biết Go?"
    Vector gần giống slice về công dụng (`append` ≈ `push_back`, `len` ≈ `size`, `cap` ≈ `capacity`), nhưng khác ba điều. Một: slice là **cửa sổ** `(con trỏ, len, cap)` nhìn vào một mảng, và nhiều slice có thể cùng nhìn một mảng; vector **sở hữu** mảng của mình và không ai khác chung nó. Hai: gán `b = a` trong Go chép cửa sổ (hai slice chung mảng); `b = a` với vector chép **cả mảng** (mục 7). Ba: `append` trả slice mới và bạn phải gán lại; `push_back` sửa chính vector, không trả gì.

### 4. Khi đầy: xin kệ mới, và tham chiếu cũ có thể hỏng

`push_back` khi size < capacity thì chỉ ghi vào ô trống ở cuối: nhanh. Khi size == capacity (đầy), vector phải **tái cấp phát (reallocation)**: xin một mảng lớn hơn ở heap, chuyển các phần tử cũ sang (copy hoặc move, [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)), trả mảng cũ. Nhờ vậy `push_back` vẫn nhanh **trung bình**: capacity tăng theo tỉ lệ nên việc chuyển nhà hiếm dần.

Chương trình dưới đẩy 10 phần tử vào vector rỗng và báo mỗi lần capacity đổi.

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v;
    std::cout << "luc dau: size=" << v.size() << " capacity=" << v.capacity() << "\n";   // (1)
    std::size_t capCu = v.capacity();
    for (int i = 1; i <= 10; i++) {
        v.push_back(i * 10);                                                              // (2)
        if (v.capacity() != capCu) {                                                      // (3)
            std::cout << "them phan tu thu " << i << ": capacity " << capCu
                      << " -> " << v.capacity() << ", dia chi mang " << v.data() << "\n";
            capCu = v.capacity();
        }
    }
    std::cout << "cuoi: size=" << v.size() << " capacity=" << v.capacity() << "\n";      // (4)
    return 0;
}
```

`v.data()` cho địa chỉ ô đầu của mảng ở heap (đã gặp ở [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)). `std::size_t` là kiểu số không âm của size và capacity ([Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)).

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Vector rỗng: chưa xin heap, size 0, capacity 0 | con trỏ rỗng |
| (2) i=1 | Đầy ngay (0 = 0): xin mảng 1 ô, ghi 10 | capacity 1, mảng ở địa chỉ A |
| (3) | capacity đổi 0 → 1: in dòng, kèm địa chỉ mảng | in 1 dòng |
| (2) i=2, i=3 | Đầy: xin mảng 2 ô rồi 4 ô, chuyển phần tử cũ sang, ghi phần tử mới, trả mảng cũ | capacity 2 rồi 4, địa chỉ đổi |
| i=4 | Còn chỗ: ghi vào ô chưa có phần tử, không chuyển nhà | capacity vẫn 4, không in |
| i=5, i=9 | Đầy: capacity 4 → 8, rồi 8 → 16 | địa chỉ đổi mỗi lần |
| (4) | Sau 10 lần: size 10, capacity 16 | 6 ô trống |

**Kết quả khi chạy:**

```text
luc dau: size=0 capacity=0
them phan tu thu 1: capacity 0 -> 1, dia chi mang 0x636ebbf3bec0
them phan tu thu 2: capacity 1 -> 2, dia chi mang 0x636ebbf3bee0
them phan tu thu 3: capacity 2 -> 4, dia chi mang 0x636ebbf3bec0
them phan tu thu 5: capacity 4 -> 8, dia chi mang 0x636ebbf3bf00
them phan tu thu 9: capacity 8 -> 16, dia chi mang 0x636ebbf3bf30
cuoi: size=10 capacity=16
```

Quy luật "gấp đôi" (1, 2, 4, 8, 16) là của `g++ 11` trên máy mình; **chuẩn C++ không quy định** capacity tăng thế nào.

Chuẩn bảo đảm capacity ≥ size và `push_back` rẻ **trung bình** (amortized). Muốn vậy mọi cài đặt thực tế đều tăng capacity theo tỉ lệ, nhưng hệ số (2, 1,5...) tùy thư viện.

Địa chỉ in ra khác ở máy bạn; chỉ cần thấy nó **đổi** mỗi lần tái cấp phát. Dòng i=3 tình cờ trùng địa chỉ lần đầu vì khối cũ vừa được trả, không phải luật.

!!! info "Bạn biết Go?"
    Đây đúng là chuyện của `append` khi `len == cap`: Go cũng xin mảng lớn hơn và chép sang. Khác ở chỗ Go còn giữ mảng cũ sống nếu slice cũ vẫn nhìn vào nó (GC), nên slice cũ vẫn đọc được. C++ **trả luôn** mảng cũ: ai còn giữ địa chỉ vào nó thì cầm một địa chỉ đã chết.

**Hệ quả quan trọng.** Sau một lần tái cấp phát, mọi thứ trỏ vào mảng cũ đều **hỏng**: tham chiếu `int& r = v[0];`, con trỏ `&v[0]`, và cả iterator (đối tượng "chỉ vào một phần tử" mà Bài 19 sẽ dạy). Dùng chúng là hành vi không xác định, giống tham chiếu treo ở [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md). Chi tiết từng container ở Bài 19; bài này chỉ cần nhớ: **sau `push_back`, đừng dùng lại tham chiếu/con trỏ lấy từ trước**.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};
    int& dau = v[0];
    v.push_back(4);
    std::cout << dau << "\n";
    return 0;
}
```

Đây là UB nên mình chỉ nêu những gì đã thật sự chạy. Biên dịch thường, chương trình thoát bình thường nhưng in một **số rác** (một lần chạy mình thấy `-24203429`; máy bạn có thể thấy số khác hoặc `1`).

Biên dịch với `-fsanitize=address` ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)) thì báo ngay `heap-use-after-free`, `READ of size 4`, trỏ đúng dòng `std::cout << dau`.

Ở g++ này vector `{1, 2, 3}` có capacity 3 nên `push_back(4)` buộc phải chuyển nhà; thư viện khác có thể khác, nhưng quy tắc "có thể hỏng" thì như nhau.

### 5. `reserve`: xin chỗ trước

Nếu bạn biết trước sẽ thêm khoảng 100 phần tử, hãy gọi `v.reserve(100)`: vector xin sẵn chỗ cho 100 phần tử, **không tạo phần tử nào** (size vẫn 0). Sau đó 100 lần `push_back` đều có chỗ, không còn lần chuyển nhà nào, và địa chỉ phần tử không đổi giữa chừng.

```cpp
#include <iostream>
#include <vector>

int demLanDoi(std::vector<int>& v, int soPhanTu) {       // (1)
    int lan = 0;
    std::size_t capCu = v.capacity();
    for (int i = 0; i < soPhanTu; i++) {
        v.push_back(i);
        if (v.capacity() != capCu) {
            lan++;
            capCu = v.capacity();
        }
    }
    return lan;
}

int main() {
    std::vector<int> a;                                   // (2)
    std::cout << "khong reserve: " << demLanDoi(a, 100) << " lan doi capacity\n";

    std::vector<int> b;
    b.reserve(100);                                       // (3)
    std::cout << "sau reserve(100): size=" << b.size() << " capacity=" << b.capacity() << "\n";
    std::cout << "co reserve: " << demLanDoi(b, 100) << " lan doi capacity\n";   // (4)
    std::cout << "cuoi: size=" << b.size() << " capacity=" << b.capacity() << "\n";
    return 0;
}
```

(1) nhận vector bằng tham chiếu `&` ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)) để hàm đếm trên chính vector của `main`.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) + gọi | `a` rỗng, đẩy 100 phần tử, đếm số lần capacity đổi: in `8` | capacity 0 → 1 → 2 → 4 → ... → 128 |
| (3) | `b.reserve(100)`: xin sẵn mảng 100 ô; chưa có phần tử; in `size=0 capacity=100` | `b`: size 0, capacity 100 |
| (4) | Đẩy 100 phần tử: luôn còn chỗ, capacity không đổi; in `0` rồi `size=100 capacity=100` | `b`: size 100, capacity 100 |

**Kết quả khi chạy:**

```text
khong reserve: 8 lan doi capacity
sau reserve(100): size=0 capacity=100
co reserve: 0 lan doi capacity
cuoi: size=100 capacity=100
```

Số `8` là của `g++ 11` (nhân đôi từ 1 đến 128), và capacity đúng 100 cũng là của g++ (chuẩn chỉ bảo `capacity() >= 100`); thư viện khác có thể ra số khác. Điều đáng nhớ: có `reserve` thì **không còn lần chuyển nhà nào** trong lúc thêm.

!!! warning "Hay nhầm: `reserve` không đổi size"
    `v.reserve(100)` chỉ tăng **capacity**. Sau đó `v[50] = 1;` vẫn là truy cập ngoài size (UB), vì chưa có phần tử nào. Muốn có 100 phần tử thật thì viết `std::vector<int> v(100);` (mục 2), hoặc gọi `v.resize(100)`, hoặc cứ `reserve` rồi `push_back`. `resize(n)` đổi **size** thành n: thiếu thì thêm phần tử 0 (với `int`), thừa thì cắt bớt. Vậy `reserve` đổi capacity, `resize` đổi size.

### 6. `[]` và `at`: không kiểm tra và có kiểm tra

Cả hai đều lấy phần tử thứ `i`, nhưng khác khi `i` ngoài khoảng `0 … size-1`:

- `v[i]`: **không kiểm tra**, nhanh. Ngoài biên là hành vi không xác định.
- `v.at(i)`: **có kiểm tra**, ngoài biên thì **ném ngoại lệ** `std::out_of_range` (cần `#include <stdexcept>` để dùng tên này; ngoại lệ và `try`/`catch` ở [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)). Chậm hơn chút vì phải so sánh.

Chương trình dưới cũng cho thấy một cái bẫy hay gặp với `size()`:

```cpp
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    std::vector<int> v = {10, 20, 30};
    std::cout << v[1] << " " << v.at(1) << "\n";                  // (1)
    try {
        std::cout << v.at(5) << "\n";                             // (2)
    } catch (const std::out_of_range& e) {                        // (3)
        std::cout << "at(5) nem out_of_range: " << e.what() << "\n";
    }
    std::vector<int> rong;
    std::cout << "rong.size() - 1 = " << rong.size() - 1 << "\n"; // (4)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Hợp lệ, cả hai lấy phần tử số 1 | in `20 20` |
| (2) | `at(5)`: 5 ≥ size (3), ném ngoại lệ, chưa in được gì | ném `out_of_range` |
| (3) | `catch` bắt được; `e.what()` là câu mô tả lỗi | in dòng báo lỗi |
| (4) | `rong.size()` là 0 kiểu **không dấu**; trừ 1 không ra -1 mà **quấn vòng** thành số rất lớn | in `18446744073709551615` |

**Kết quả khi chạy:**

```text
20 20
at(5) nem out_of_range: vector::_M_range_check: __n (which is 5) >= this->size() (which is 3)
rong.size() - 1 = 18446744073709551615
```

Câu chữ sau `nem out_of_range:` do thư viện của g++ quyết định, máy bạn có thể khác; chỉ kiểu ngoại lệ là chuẩn quy định. Số ở dòng cuối là hai mũ 64 trừ 1, trên máy 64 bit; số không dấu quấn vòng là hợp lệ (khác số có dấu, [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Hệ quả: vòng `for (std::size_t i = 0; i <= v.size() - 1; i++)` trên vector rỗng truy cập ngoài biên ngay từ vòng đầu (và nếu không sập thì chạy rất lâu).

**Thử thay đổi: đổi `v.at(5)` thành `v[5]`** (UB, nên không chạy trong bộ kiểm tra). Mình đã chạy bản đó: chạy thường in `0` rồi thoát mã 0, không báo gì (số in ra là rác, máy bạn có thể khác); với `-fsanitize=address` thì báo `heap-buffer-overflow`, `READ of size 4`, đúng dòng có `v[5]`. Tức `[]` im lặng cho qua, còn `at` dừng lại đúng chỗ.

### 7. Truyền vector vào hàm, và sao chép vector

Vector là một đối tượng như mọi đối tượng ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)): truyền **theo giá trị** thì hàm nhận một **bản sao**. Với vector, bản sao là **sao chép sâu**: xin mảng mới và chép toàn bộ phần tử ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)). Vector triệu phần tử thì mỗi lần truyền theo giá trị là chép triệu phần tử.

Quy tắc dùng hằng ngày:

- Chỉ **đọc**: nhận `const std::vector<int>&` (không chép, không sửa được).
- Cần **sửa** vector của nơi gọi: nhận `std::vector<int>&`.
- Cần **một bản riêng** để tự do sửa: nhận theo giá trị (chép có chủ ý).

```cpp
#include <iostream>
#include <vector>

int tong(const std::vector<int>& v) {                            // (1)
    int s = 0;
    for (int x : v) s += x;
    return s;
}

void tangMoiPhanTu(std::vector<int>& v) {                        // (2)
    for (int& x : v) x += 1;
}

void suaBanSao(std::vector<int> v, const int* goc) {             // (3)
    v[0] = 999;
    std::cout << "trong ham: v[0] = " << v[0] << ", chung mang voi goc? " << (v.data() == goc) << "\n";
}

void xemBangThamChieu(const std::vector<int>& v, const int* goc) {   // (4)
    std::cout << "trong ham: v[0] = " << v[0] << ", chung mang voi goc? " << (v.data() == goc) << "\n";
}

int main() {
    std::vector<int> a = {1, 2, 3};
    std::cout << "tong = " << tong(a) << "\n";
    tangMoiPhanTu(a);
    std::cout << "sau tangMoiPhanTu: " << a[0] << " " << a[1] << " " << a[2] << "\n";
    suaBanSao(a, a.data());                                      // (5)
    std::cout << "sau suaBanSao: a[0] = " << a[0] << "\n";
    xemBangThamChieu(a, a.data());                               // (6)

    std::vector<int> b = a;                                      // (7)
    b[0] = 50;
    std::cout << "a[0] = " << a[0] << ", b[0] = " << b[0] << ", chung mang? " << (a.data() == b.data()) << "\n";
    return 0;
}
```

Ở (3) và (4), tham số `goc` là địa chỉ mảng của vector gốc; hàm so nó với `v.data()` để cho ta biết `v` có **chung mảng** với gốc hay không (in `1` là chung, `0` là riêng). Dòng (5), (6) truyền `a.data()` ngay từ nơi gọi.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `tong(a)` (1) | `v` là biệt danh của `a`, cộng 1+2+3 | không chép; in `tong = 6` |
| (2) | Duyệt bằng `int& x` (biệt danh từng phần tử), cộng 1 vào mỗi phần tử của `a` | `a`: `[2 3 4]`; in `2 3 4` |
| (5) vào (3) | Theo giá trị: `v` là **bản sao** có mảng riêng | `a` ở mảng A, `v` ở mảng B khác |
| (3) | `v[0] = 999` chỉ đổi bản sao (so `data()` ra 0); hết hàm, bản sao bị hủy (RAII) | `a` vẫn `[2 3 4]`, in `a[0] = 2` |
| (6) vào (4) | `const&`: `v` là biệt danh của `a`, chung mảng, so ra 1 | in `v[0] = 2 ... 1` |
| (7) | `b = a` sao chép sâu (mảng riêng); `b[0] = 50` chỉ đổi `b` | `a`: `[2 3 4]`, `b`: `[50 3 4]`; in `chung mang? 0` |

**Kết quả khi chạy:**

```text
tong = 6
sau tangMoiPhanTu: 2 3 4
trong ham: v[0] = 999, chung mang voi goc? 0
sau suaBanSao: a[0] = 2
trong ham: v[0] = 2, chung mang voi goc? 1
a[0] = 2, b[0] = 50, chung mang? 0
```

!!! info "Bạn biết Go?"
    Trong Go, `b := a` với slice chỉ chép cửa sổ `(ptr, len, cap)`, nên sửa `b[0]` thì `a[0]` cũng đổi (nếu chưa tái cấp phát). Truyền slice vào hàm cũng vậy: hàm sửa được phần tử của bạn. C++ **ngược lại theo mặc định**: `b = a` và truyền theo giá trị đều chép toàn bộ, nên hàm không sửa được vector gốc (dòng "sau suaBanSao" ở trên). Muốn hàm C++ chung dữ liệu như slice thì phải truyền `&` rõ ràng.

Một điều nhẹ nhõm: **trả vector theo giá trị** từ hàm (`std::vector<int> tao() { ... return v; }`) không bị chép tốn kém, nhờ move và tối ưu hóa ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)).

### 8. `emplace_back`, `vector<bool>` và những thao tác chưa dạy

`push_back(x)` nhận một đối tượng **đã được tạo** rồi đưa vào vector. `emplace_back(...)` nhận **các đối số của hàm tạo** và dựng đối tượng ngay trong ô cuối, không qua đối tượng tạm. Với `int` hai cách như nhau. Với kiểu có hàm tạo, mình đã chạy thử một struct `Cay` có hàm tạo `Cay(int)`, hàm tạo sao chép và hàm tạo di chuyển `noexcept` (sau `reserve`): `push_back(Cay(1))` in `tao Cay 1` rồi `move Cay 1`, còn `emplace_back(2)` chỉ in `tao Cay 2`. Chênh lệch chỉ là một lần move, nên có sẵn đối tượng thì cứ `push_back`, muốn tạo mới từ vài đối số thì `emplace_back`. (Nếu không `reserve` và hàm tạo di chuyển không có `noexcept`, lúc chuyển nhà vector sẽ **chép** thay vì move: [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md), mục 8.)

`std::vector<bool>` là **trường hợp đặc biệt**: bên trong nén mỗi phần tử thành 1 bit, nên `v[i]` không trả về tham chiếu thật tới một `bool`. Cần vector `bool` bình thường thì dùng `std::vector<char>`.

Bài này chưa dạy chèn hoặc xóa ở giữa vector (`insert`, `erase`, `clear`): chúng phải dời các phần tử phía sau nên tốn thời gian tỉ lệ với số phần tử, và Bài 19 sẽ dạy `erase`. Gọi `pop_back` hay `back()` trên vector rỗng là UB.

## 💻 Ví dụ code

Các chương trình ở phần 📖 (mục 2, 4, 5, 6, 7) là ví dụ để chạy. Dưới đây là một bài ngắn dùng chung những gì đã học: lấy các số chẵn từ một dãy.

```cpp
#include <iostream>
#include <vector>

std::vector<int> layChan(const std::vector<int>& nguon) {        // (1)
    std::vector<int> kq;
    kq.reserve(nguon.size());                                    // (2)
    for (int x : nguon) {
        if (x % 2 == 0) {
            kq.push_back(x);                                     // (3)
        }
    }
    return kq;                                                   // (4)
}

int main() {
    std::vector<int> so = {5, 8, 3, 6, 2, 7};
    std::vector<int> chan = layChan(so);
    std::cout << "so chan:";
    for (int x : chan) std::cout << " " << x;
    std::cout << "\n";
    std::cout << "size = " << chan.size() << ", capacity >= size? " << (chan.capacity() >= chan.size()) << "\n";
    return 0;
}
```

`x % 2` là phần dư khi chia 2 (bằng 0 nghĩa là số chẵn).

**Chạy từng dòng:** (1) `nguon` là biệt danh của `so`, không chép. (2) `kq` xin sẵn chỗ cho 6 phần tử, size vẫn 0. (3) gặp 8, 6, 2 thì thêm vào `kq`, không chuyển nhà nhờ `reserve`. (4) trả `kq` theo giá trị: mảng được chuyển (move) hoặc bỏ hẳn bước chép, nên `chan` nhận mảng của `kq` mà không chép từng phần tử.

**Kết quả khi chạy:**

```text
so chan: 8 6 2
size = 3, capacity >= size? 1
```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "size và capacity của vector khác nhau thế nào?"
    **size** là số phần tử đang chứa; **capacity** là số phần tử mảng bên trong chứa được mà chưa phải xin chỗ mới. Luôn có `capacity >= size`. Khi `push_back` mà size đã bằng capacity, vector xin mảng lớn hơn, chuyển phần tử sang và trả mảng cũ. Cách tăng capacity là tùy cài đặt (thường nhân lên một hệ số), chuẩn chỉ yêu cầu `push_back` rẻ trung bình.

??? question "Vì sao `push_back` có thể làm hỏng tham chiếu, con trỏ, iterator lấy từ trước?"
    Vì khi đầy, vector tái cấp phát: các phần tử được đưa sang một mảng mới ở địa chỉ khác và mảng cũ bị trả. Mọi tham chiếu, con trỏ, iterator đang trỏ vào mảng cũ trở thành "treo", dùng chúng là hành vi không xác định. Phòng tránh: đừng giữ chúng qua một lần thêm phần tử, hoặc `reserve` đủ chỗ trước, hoặc lưu **chỉ số** thay vì địa chỉ.

??? question "`[]` và `at` khác nhau thế nào? Khi nào dùng cái nào?"
    `[]` không kiểm tra biên: chỉ số sai là hành vi không xác định, có thể im lặng cho ra rác. `at` kiểm tra và ném `std::out_of_range`, nên lỗi dễ thấy hơn nhưng chậm hơn chút. Trong vòng lặp đã bảo đảm biên (`i < v.size()`) thì dùng `[]`; khi chỉ số đến từ dữ liệu ngoài hoặc bạn muốn bắt lỗi sớm thì dùng `at`.

??? question "Truyền vector vào hàm thế nào cho đúng? Khác gì slice của Go?"
    Chỉ đọc thì `const std::vector<T>&`; cần sửa vector của nơi gọi thì `std::vector<T>&`; cần bản riêng thì truyền theo giá trị (chép sâu toàn bộ phần tử). Slice của Go chỉ chép `(ptr, len, cap)` nên mặc định chung mảng với nơi gọi; vector chép cả mảng, nên mặc định cô lập.

??? question "`emplace_back` khác `push_back` thế nào?"
    `push_back` nhận một đối tượng đã có; `emplace_back` nhận các đối số của hàm tạo và dựng đối tượng ngay trong vector, nên bỏ được một lần chép hoặc move của đối tượng tạm. Với kiểu cơ bản thì không khác. Có đối tượng sẵn thì `push_back`, muốn tạo mới thì `emplace_back`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Giữ tham chiếu/con trỏ vào vector rồi `push_back`"
    `int& r = v[0]; v.push_back(1); r = 5;` có thể ghi vào mảng đã trả (mục 4). Nếu cần địa chỉ ổn định thì `reserve` đủ chỗ trước, hoặc dùng chỉ số `v[0]` mỗi lần cần.

!!! warning "Lỗi 2: Truy cập `v[i]` khi `i >= size()`, kể cả khi `i < capacity()`"
    Ô nằm trong capacity nhưng ngoài size chưa có phần tử. `v.reserve(100); v[0] = 1;` là UB. Dùng `at` để bắt lỗi, hoặc `resize`/`push_back` trước.

!!! warning "Lỗi 3: `size() - 1` trên vector rỗng, và `(n)` với `{n}`"
    `v.size() - 1` quấn thành số khổng lồ khi `v` rỗng (mục 6): kiểm `!v.empty()` trước hoặc viết `i + 1 < v.size()`. Và `std::vector<int> v(5)` là năm số 0, còn `std::vector<int> v{5}` là một phần tử bằng 5 (mục 2).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="16" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Trong `std::vector<double>`, phần `<double>` có nghĩa gì?

- Vector này luôn có đúng hai phần tử
- Vector này chỉ gồm các số nguyên không dấu
- Mọi phần tử của vector đều là `double`
- Vector này nhận được mọi kiểu dữ liệu

<p class="giai-thich" markdown>Phần trong `< >` là tham số khuôn mẫu: nó chọn loại phần tử mà vector chứa, và mọi phần tử đều cùng loại đó. Số lượng phần tử không nằm ở đây mà do `size` quyết định và thay đổi được. `double` là số thực, không phải số nguyên không dấu. Vector không lẫn lộn nhiều kiểu: muốn chứa kiểu khác phải khai báo một vector kiểu khác.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
std::vector<int> v(3, 7);
v.push_back(1);
std::cout << v.size() << " " << v[0];
```

- `4 7`, vì ba số 7 rồi thêm một số mới
- `3 7`, vì push_back không đổi số phần tử
- `4 3`, vì 3 là giá trị của phần tử đầu
- `2 3`, vì ngoặc tròn là danh sách giá trị

<p class="giai-thich" markdown>Ngoặc tròn `(3, 7)` nghĩa là ba phần tử, mỗi cái bằng 7; `push_back(1)` thêm một phần tử nên size là 4, còn `v[0]` vẫn là 7. Kết quả `3 7` quên mất rằng `push_back` tăng size. `4 3` nhầm số lượng với giá trị. Còn `2 3` đúng với dạng ngoặc nhọn `{3, 7}` (hai phần tử 3 và 7), không phải với ngoặc tròn.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Với `std::vector<int> v;` rồi gọi `v.reserve(50);`, ngay sau đó điều nào đúng?

- size bằng 50 và mọi phần tử đều bằng 0
- size bằng 0 và capacity vẫn còn bằng 0
- size bằng 50 và capacity bằng 100
- size bằng 0 còn capacity tối thiểu 50

<p class="giai-thich" markdown>`reserve` chỉ xin sẵn chỗ: capacity lên tối thiểu 50, còn size giữ nguyên 0 vì chưa có phần tử nào được tạo. Muốn size bằng 50 phải dùng `resize(50)` hoặc khai báo `v(50)`. Việc capacity vẫn là 0 sẽ làm `reserve` vô nghĩa. Capacity 100 là một con số không có căn cứ nào.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn code sau (`v` đang đầy: size = capacity = 3). Điều nào đúng?

```text
std::vector<int> v = {1, 2, 3};
int& r = v[0];
v.push_back(4);
r = 9;
```

- Hợp lệ, vì `r` là biệt danh của `v[0]` nên luôn theo vector
- Có thể là UB, vì `push_back` đã chuyển mảng sang chỗ mới
- Lỗi biên dịch, vì `r` phải khai báo là `const int&`
- Hợp lệ, vì `push_back` chỉ thêm ở cuối nên không đụng `v[0]`

<p class="giai-thich" markdown>Vector đầy nên `push_back(4)` tái cấp phát: các phần tử sang mảng mới, mảng cũ bị trả, còn `r` vẫn gắn vào ô của mảng cũ. Ghi qua `r` là ghi vào chỗ đã trả, tức UB (ASan báo `heap-use-after-free` khi mình chạy bản tương tự). Việc `r` là biệt danh chỉ đúng chừng nào mảng chưa đổi chỗ. Và dù chỉ thêm ở cuối, việc chuyển nhà vẫn làm đổi chỗ cả `v[0]`. Không có luật nào bắt `r` phải là `const`, nên đây không phải lỗi biên dịch.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn code sau. Nó in ra gì?

```text
void them(std::vector<int> v) { v.push_back(5); }
std::vector<int> a = {1};
them(a);
std::cout << a.size();
```

- `2`, vì `push_back` thêm vào vector gốc
- `0`, vì hàm đã lấy mất toàn bộ phần tử
- Lỗi biên dịch, vì không truyền vector theo giá trị được
- `1`, vì hàm chỉ sửa một bản sao riêng của nó

<p class="giai-thich" markdown>Tham số `std::vector<int> v` nhận theo giá trị nên là bản sao sâu với mảng riêng; `push_back(5)` chỉ thêm vào bản sao, và bản sao bị hủy khi hàm xong, nên `a` vẫn có một phần tử. Muốn hàm thêm vào vector gốc thì tham số phải là `std::vector<int>&`. Truyền theo giá trị hoàn toàn hợp lệ, chỉ là tốn một lần chép. Và hàm không hề lấy mất phần tử của `a`: `a` còn nguyên.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Với `std::vector<int> v = {1, 2, 3};`, hai lời gọi `v.at(10)` và `v[10]` khác nhau thế nào?

- `at(10)` ném `out_of_range`, còn `v[10]` là UB
- Cả hai đều ném `out_of_range`, chỉ khác tên gọi
- `v[10]` ném ngoại lệ, còn `at(10)` trả về 0
- Cả hai đều là UB vì chỉ số quá lớn

<p class="giai-thich" markdown>`at` có kiểm tra biên nên báo lỗi bằng ngoại lệ `std::out_of_range` (mình đã chạy ở mục 6), còn `[]` bỏ qua kiểm tra để nhanh, nên chỉ số sai là UB: có thể in rác, có thể sập, có thể trông như chạy đúng. `[]` không kiểm tra biên nên không có gì để ném. `at` không trả 0 thay cho phần tử thiếu. Và `at` được chuẩn định nghĩa rõ ràng, nên không phải UB.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Với `std::vector<Cay> v;` (`Cay` có hàm tạo nhận `int`), khác biệt chính giữa `v.push_back(Cay(2))` và `v.emplace_back(2)` là gì?

- `emplace_back` luôn nhanh hơn rất nhiều lần
- `push_back` không dùng được với đối tượng tạm
- `emplace_back` dựng đối tượng ngay trong vector
- `emplace_back` chỉ dùng được khi đã gọi `reserve`

<p class="giai-thich" markdown>`emplace_back(2)` chuyển đối số cho hàm tạo và sinh `Cay` ngay trong ô cuối, nên không có đối tượng tạm để move (mình đã chạy: chỉ có dòng `tao`, không có dòng `move`). `push_back(Cay(2))` tạo tạm rồi move vào. Nhưng chênh lệch thường chỉ là một lần move, không phải "rất nhiều lần". `push_back` nhận đối tượng tạm bình thường (mình đã chạy được). Và `reserve` chỉ giúp tránh chuyển nhà, không phải điều kiện để dùng `emplace_back`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. STL là bộ kiểu chứa và hàm có sẵn của C++; `std::vector<T>` (`#include <vector>`) là mảng co giãn mà mọi phần tử cùng kiểu `T`, giống slice của Go nhưng **sở hữu** mảng ở heap; `v(n)` là n phần tử, `v{n}` là danh sách một phần tử.
2. size là số phần tử đang có, capacity là số chỗ đã xin (luôn ≥ size); `push_back` khi đầy làm vector tái cấp phát sang mảng lớn hơn, cách tăng là tùy cài đặt, nên tham chiếu, con trỏ, iterator lấy từ trước có thể hỏng (Bài 19 nói kỹ).
3. `reserve(n)` xin sẵn chỗ để khỏi chuyển nhà nhưng không tạo phần tử; `[]` không kiểm tra biên (ngoài biên là UB), `at` kiểm tra và ném `std::out_of_range`; `size() - 1` trên vector rỗng quấn thành số rất lớn.
4. Truyền theo giá trị và `b = a` đều sao chép sâu cả mảng; chỉ đọc thì nhận `const std::vector<T>&`, cần sửa bản gốc thì `std::vector<T>&`; khác slice của Go vốn chung mảng.
5. `push_back(x)` nhận đối tượng đã tạo, `emplace_back(đối số...)` dựng ngay trong vector để bớt một lần move; `std::vector<bool>` là trường hợp đặc biệt (nén thành bit), nên tránh khi cần `bool` thường; `reserve` đổi capacity còn `resize` đổi size.
