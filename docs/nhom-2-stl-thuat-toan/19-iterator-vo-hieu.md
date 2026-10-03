# Bài 19 — Iterator và iterator invalidation: duyệt container, và khi nào iterator hỏng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Hiểu **iterator** là "con trỏ tổng quát" cho mọi container: `begin()`, `end()` (điểm **sau** phần tử cuối), `*it`, `++it`, `it->`, `const_iterator`/`cbegin`, và range-for thực chất chạy thế nào.
    - Nói được **iterator invalidation** (iterator bị vô hiệu) là gì, container nào thêm/xóa thì hỏng cái gì (theo **chuẩn**), và g++ thực tế làm gì.
    - Xóa phần tử khi đang duyệt đúng cách (`it = c.erase(it)`) và biết vì sao `push_back` trong lúc duyệt vector là lỗi kinh điển.

**Bạn cần biết trước:** [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) (phép tính con trỏ, vị trí ngay sau phần tử cuối), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`auto`, range-for), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UB, ASan), [Bài 16](16-vector.md) (tái cấp phát), [Bài 17](17-string-array-deque-list.md) (`deque`, `list`) và [Bài 18](18-map-set-unordered.md) (`map`, `find`).

## 🧠 Câu chuyện mở đầu

Quay lại **kệ sách** của Bài 16. Bạn cầm một **ngón tay** chỉ vào một cuốn sách: ngón tay ấy là **iterator**. Bạn đọc cuốn đang chỉ (`*it`), nhích sang cuốn kế (`++it`), và biết đã hết khi ngón tay chạm **chỗ ngay sau cuốn cuối** (đó là `end()`: chỗ ấy không có sách để đọc).

Điểm hay: dù là kệ liền khối (`vector`), các tấm thẻ rời nối bằng dây (`list`) hay danh bạ (`map`), bạn vẫn dùng **cùng một cách** cầm ngón tay. Còn chuyện **ngón tay hỏng** là: bạn chỉ vào một cuốn rồi ai đó dọn kệ sang chỗ khác, hoặc rút cuốn đó ra. Ngón tay vẫn đứng nguyên nhưng chỉ vào chỗ không còn là cuốn sách ấy.

!!! info "Chỗ nào ví dụ ngón tay không còn đúng?"
    Iterator là một **đối tượng thật** của thư viện, không phải ngón tay; với `vector` nó thường chứa một con trỏ, với `list`/`map` nó chứa cách đi tới nút kế. Vì vậy `it + 2` chạy được với `vector` nhưng không chạy với `list` (mục 3). Ví dụ cũng không nói "ngón tay hỏng" thì máy báo gì: thường là **không báo gì cả** (mục 4).

## 📖 Giải thích

### 1. Iterator giống con trỏ của Bài 05

Ở Bài 05, để duyệt mảng ta dùng con trỏ: bắt đầu từ `a`, lặp đến `a + 3` (ngay sau phần tử cuối), mỗi vòng `++p` và đọc `*p`. Mọi container của STL có cùng bộ ba: `c.begin()` chỉ vào phần tử đầu, `c.end()` chỉ vào **vị trí ngay sau phần tử cuối**, và iterator có `*it`, `++it`, `==`, `!=`. Chương trình dưới viết cùng một vòng lặp hai lần để bạn thấy chúng khớp nhau.

```cpp
#include <iostream>
#include <vector>

int main() {
    int a[3] = {10, 20, 30};
    for (int* p = a; p != a + 3; ++p) {                  // (1)
        std::cout << *p << " ";
    }
    std::cout << "\n";

    std::vector<int> v = {10, 20, 30};
    for (std::vector<int>::iterator it = v.begin(); it != v.end(); ++it) {   // (2)
        std::cout << *it << " ";
    }
    std::cout << "\n";

    auto it = v.begin();                                 // (3)
    ++it;                                                // (4)
    *it = 25;                                            // (5)
    std::cout << *it << " o vi tri " << it - v.begin() << "\n";   // (6)

    std::vector<int> rong;
    std::cout << (rong.begin() == rong.end()) << " " << (v.end() - v.begin()) << "\n";   // (7)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Vòng con trỏ của Bài 05: `p` từ `a` đến `a + 3`, in `*p` | `p` đi qua 10, 20, 30 |
| (2) | Cùng vòng đó với vector: `it` bắt đầu ở `begin()`, dừng khi bằng `end()` | `it` đi qua 10, 20, 30 |
| (3) | `auto` để máy tự đoán kiểu dài của iterator | `it` chỉ vào phần tử 0 |
| (4) | `++it` nhích sang phần tử kế | `it` chỉ vào phần tử 1 (giá trị 20) |
| (5) | `*it = 25` sửa chính phần tử trong vector | `v` = `{10, 25, 30}` |
| (6) | `it - v.begin()` là số phần tử giữa hai iterator, giống `q - p` ở Bài 05 | in `25 o vi tri 1` |
| (7) | Vector rỗng có `begin() == end()`; vector đầy có `end() - begin()` đúng bằng `size` | in `1 3` |

**Kết quả khi chạy:**

```text
10 20 30 
10 20 30 
25 o vi tri 1
1 3
```

Hai điều cần nhớ. `vector<int>::iterator` đọc là "kiểu tên `iterator` nằm trong `vector<int>`" (`::` nghĩa là "nằm trong"); gõ dài nên ta thường viết `auto`. Và `end()` **không bao giờ được `*`**: nó là chỗ sau cuối, chỉ để so sánh, y như `a + 3` ở Bài 05.

!!! question "Hỏi nhanh: vì sao `end()` nằm SAU phần tử cuối, không phải ở phần tử cuối?"
    Vì khi đó dãy rỗng biểu diễn được tự nhiên (`begin() == end()`, không có phần tử nào), vòng lặp chỉ cần điều kiện `it != end()`, và `end() - begin()` đúng bằng số phần tử. Nếu `end()` là phần tử cuối thì không có cách nào nói "rỗng".

**Thử thay đổi: viết `int* it = v.begin();`.** Mình đã chạy: lỗi biên dịch `cannot convert 'std::vector<int>::iterator' to 'int*'`. Iterator **dùng giống** con trỏ nhưng là một kiểu riêng, không phải con trỏ.

!!! info "Bạn biết Go?"
    Go không có iterator: bạn viết `for i, x := range s` và ngôn ngữ lo phần duyệt. C++ cũng có range-for (mục 2), nhưng bên dưới nó dùng iterator, và iterator còn là thứ bạn **truyền cho hàm** của thư viện (Bài 20) và giữ lại để xóa/chèn giữa dãy (mục 5).

### 2. Range-for thực chất chạy thế nào

Vòng `for (auto x : v)` ở Bài 13 là cách viết gọn. Máy dịch nó gần như thành đoạn trong dấu `{ }` ở chương trình dưới. Chú ý chỗ `end()` được lấy **một lần**, trước khi vòng lặp bắt đầu.

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};

    for (auto x : v) {                                   // (1)
        std::cout << x << " ";
    }
    std::cout << "\n";

    {                                                    // (2)
        auto&& dai = v;
        auto dau = dai.begin();
        auto cuoi = dai.end();                           // (3)
        for (; dau != cuoi; ++dau) {
            auto x = *dau;                               // (4)
            std::cout << x << " ";
        }
    }
    std::cout << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Range-for gọn: mỗi vòng `x` là bản chép của một phần tử |
| (2) | Bản "viết tay" tương đương; `auto&&` chỉ là cách nhận `v` mà không chép nó (hiểu như `auto&` ở đây) |
| (3) | `begin()` và `end()` được lấy **một lần**; `cuoi` không tự cập nhật nếu vector đổi |
| (4) | `auto x = *dau` chính là phần `auto x` bạn viết trong range-for (đổi thành `auto&` hay `const auto&` thì dòng này đổi theo) |

**Kết quả khi chạy:**

```text
1 2 3 
1 2 3 
```

Với mảng C, range-for dùng chính con trỏ `a` và `a + N` như mục 1. Hệ quả quan trọng của việc lấy `end()` một lần: nếu thân vòng lặp **thêm hoặc xóa** phần tử của chính vector đang duyệt, `dau` và `cuoi` có thể đã hỏng mà vòng lặp không hề biết (mục 4).

### 3. `it->`, `const_iterator` và các "hình dạng" iterator

Iterator của `map` trỏ vào một `std::pair` (Bài 18), nên dùng `it->first` và `it->second`; `it->` là viết gọn của `(*it).`, giống con trỏ ở Bài 03. Iterator **chỉ-đọc** (`const_iterator`) cho đọc mà không cho sửa phần tử: lấy bằng `cbegin()`/`cend()`, hoặc bằng `begin()` trên container `const`.

```cpp
#include <deque>
#include <iostream>
#include <iterator>
#include <list>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> diem = {{"An", 9}, {"Binh", 7}};
    for (auto it = diem.begin(); it != diem.end(); ++it) {     // (1)
        std::cout << it->first << "=" << it->second << " ";    // (2)
    }
    std::cout << "\n";

    std::list<int> l = {5, 6, 7};
    auto it = std::next(l.begin(), 2);                         // (3)
    std::cout << *it << "\n";

    std::deque<int> d = {1, 2, 3, 4};
    std::cout << *(d.begin() + 3) << "\n";                     // (4)

    for (auto c = l.cbegin(); c != l.cend(); ++c) {            // (5)
        std::cout << *c << " ";
    }
    std::cout << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Duyệt `map` bằng iterator; thứ tự là thứ tự khóa |
| (2) | `it->first` là khóa, `it->second` là giá trị |
| (3) | `std::next(it, n)` (`#include <iterator>`) trả iterator nhích `n` bước; dùng được cho mọi container |
| (4) | `deque` (như `vector`) cho `+ 3`: nhảy thẳng tới phần tử thứ 3 |
| (5) | `cbegin()`/`cend()`: chỉ đọc, `*c = 1` sẽ không biên dịch |

**Kết quả khi chạy:**

```text
An=9 Binh=7 
7
4
5 6 7 
```

**Thử thay đổi (đã chạy, ba lỗi biên dịch):** `l.begin() + 1` với `list` báo `no match for 'operator+' (operand types are 'std::list<int>::iterator' and 'int')`; `*c = 1` với `c` từ `cbegin()` báo `assignment of read-only location`; hàm nhận `const std::vector<int>&` rồi `*v.begin() = 1` cũng báo `assignment of read-only location`, vì `begin()` của container `const` trả `const_iterator`.

Từ đó rút ra: `vector`, `deque`, `std::array` (iterator **nhảy tự do**) có `it + n`, `it - n`, `it[n]`; `list`, `map`, `set` chỉ nhích từng bước `++`/`--`; `unordered_map`/`unordered_set` chỉ `++`. Cần nhảy `n` bước ở loại nào cũng được thì dùng `std::next`. Quy tắc dùng thường ngày: chỉ xem thì `cbegin`/`const auto&`, sửa tại chỗ thì `begin`/`auto&`.

### 4. Iterator invalidation: iterator bị vô hiệu

**Iterator invalidation** nghĩa là một thao tác trên container làm iterator (và có thể cả tham chiếu, con trỏ) lấy từ **trước đó** không còn dùng được. Dùng iterator đã bị vô hiệu là **hành vi không xác định** (Bài 15), giống tham chiếu treo ở Bài 06. Bảng dưới là điều **chuẩn C++17 nói**, theo từng container.

| Container | Thêm phần tử (`push_back`, `insert`...) | Xóa phần tử (`erase`) |
|---|---|---|
| `vector` | Phải tái cấp phát: **mọi** iterator, tham chiếu, con trỏ hỏng. Không phải tái cấp phát: từ điểm chèn trở đi (và `end()`) hỏng, phần trước còn sống | Từ chỗ xóa trở đi (cả `end()`) hỏng; phần trước còn sống |
| `deque` | Chèn giữa: tất cả hỏng. `push_back`/`push_front`: **iterator** hỏng, nhưng **tham chiếu và con trỏ** tới phần tử còn sống | Xóa giữa: tất cả hỏng. Xóa ở hai đầu: chỉ cái bị xóa (và `end()` nếu xóa cuối) hỏng |
| `list` | Không cái nào hỏng | Chỉ cái bị xóa hỏng |
| `map`, `set` | Không cái nào hỏng | Chỉ cái bị xóa hỏng |
| `unordered_*` | Không rehash: không cái nào hỏng. Có rehash (Bài 18): **iterator** hỏng, tham chiếu và con trỏ vẫn sống | Chỉ cái bị xóa hỏng |

Đọc bảng cho đúng: "còn sống" là điều chuẩn **bảo đảm**; "hỏng" nghĩa là chuẩn **không hứa gì**, có thể trông vẫn chạy. Một ví dụ: `reserve` đủ lớn trước khi thêm là cách để vector không tái cấp phát (Bài 16). Chương trình ở 💻 chạy thử mấy ô "còn sống".

Ví dụ kinh điển nhất là vector đầy rồi `push_back` (đúng chuyện của Bài 16):

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};                 // size 3, capacity 3
    auto it = v.begin();                            // (1)
    v.push_back(4);                                 // (2)
    std::cout << *it << "\n";                       // (3)
    return 0;
}
```

Dòng (1) lấy iterator vào mảng cũ; dòng (2) hết chỗ nên vector xin mảng mới và **trả mảng cũ**; dòng (3) đọc qua iterator vào mảng đã trả. Mình đã chạy ba cách:

- **Build thường:** thoát bình thường và in một số rác (lần chạy của mình: `-1892327856`; máy bạn sẽ khác).
- **`-fsanitize=address`** (Bài 15): báo `heap-use-after-free`, `READ of size 4`, đúng dòng (3).
- **`-D_GLIBCXX_DEBUG`** (chế độ kiểm tra của thư viện g++): in `Error: attempt to dereference a singular iterator.` rồi dừng chương trình. Chế độ này làm chương trình chậm và chỉ dùng để chạy thử.

Đây là chỗ cần tách "chuẩn nói" với "g++ làm gì". **Chuẩn:** UB, mọi kết quả đều được phép. **g++ bản thường (libstdc++ 11):** không kiểm tra, iterator của vector bên trong chứa một con trỏ, nên nó cứ trỏ vào mảng cũ và đọc rác như trên; kết quả là do bộ cấp phát, không phải luật. Không báo lỗi **không có nghĩa** là đúng.

Dạng ẩn của lỗi này là thêm phần tử trong range-for (mục 2: `cuoi` lấy một lần, đã cũ):

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};
    for (auto x : v) {
        std::cout << x << " ";
        if (x == 2) v.push_back(9);                 // (1)
    }
    std::cout << "\n" << v.size() << "\n";
    return 0;
}
```

Build thường của mình in `1 2 -1310071373` rồi `4`: phần tử thứ ba bị đọc từ mảng đã trả. ASan báo `heap-use-after-free` ở dòng `for`. Lần thứ ba, `-D_GLIBCXX_DEBUG` báo `attempt to increment a singular iterator`.

**Thử thay đổi:** gọi `v.reserve(100)` ngay sau khi tạo `v`. Mình đã chạy: in `1 2 3` rồi `4` và ASan im lặng, vì không còn tái cấp phát. Nhưng chuẩn nói thêm `push_back` làm `end()` hỏng, nên về lý thuyết vẫn là UB: đừng dựa vào đó. Cách sửa thật: duyệt bằng chỉ số `for (std::size_t i = 0; i < v.size(); ++i)` (mình đã chạy: in `1 2 3 9`, `size` 4), hoặc gom việc cần thêm vào một vector khác rồi thêm sau vòng lặp.

!!! info "Bạn biết Go?"
    Go không có lớp lỗi này, nhưng có chuyện gần giống. `for _, x := range s { s = append(s, 9) }` thì **an toàn**: `range` tính `s` đúng một lần, vòng chạy đúng 3 lần (mình đã chạy; `len(s)` thành 4) và slice cũ vẫn đọc được nhờ GC (Bài 16). Điều Go và C++ giống nhau là bẫy logic ở mục 5; khác là Go không bao giờ cho đọc rác.

### 5. Xóa khi đang duyệt: `erase` trả iterator kế tiếp

`c.erase(it)` xóa phần tử `it` chỉ tới, và **trả về iterator của phần tử kế tiếp** (hoặc `end()` nếu đó là phần tử cuối). Vì chính `it` đã hỏng sau lệnh này, lời gọi `++it` ngay sau `erase(it)` là UB. Đây là sai lầm hay gặp nhất:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 2, 3};
    for (auto it = v.begin(); it != v.end(); ++it) {
        if (*it == 2) v.erase(it);                  // (1)
    }
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";
    return 0;
}
```

Build thường của mình in `1 2 3`: `erase` dồn các phần tử lên, `it` vẫn chỉ ô đó (giờ chứa số `2` thứ hai), rồi `++it` **bỏ qua** nó, nên một số 2 sống sót. Chương trình trông chạy bình thường nhưng sai kết quả, và theo chuẩn vẫn là UB. Với `-D_GLIBCXX_DEBUG`, nó báo `attempt to increment a singular iterator`. Với `map` (`m.erase(it)` rồi `++it`), build thường của mình in kết quả trông đúng và ASan **không báo gì**, còn chế độ debug thì dừng chương trình: một lý do nữa để không tin vào "chạy ra đúng".

Cách đúng: **lấy iterator mà `erase` trả về, và chỉ `++` khi không xóa**. Cùng một khuôn dùng được cho `vector`, `list` và `map`:

```cpp
#include <iostream>
#include <list>
#include <map>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 2, 3, 4};
    for (auto it = v.begin(); it != v.end();) {     // (1)
        if (*it % 2 == 0) {
            it = v.erase(it);                       // (2)
        } else {
            ++it;                                   // (3)
        }
    }
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";

    std::list<int> l = {1, 2, 2, 3, 4};
    for (auto it = l.begin(); it != l.end();) {
        if (*it % 2 == 0) it = l.erase(it);         // (4)
        else ++it;
    }
    for (int x : l) std::cout << x << " ";
    std::cout << "\n";

    std::map<int, int> m = {{1, 10}, {2, 20}, {3, 30}, {4, 40}};
    for (auto it = m.begin(); it != m.end();) {
        if (it->first % 2 == 0) it = m.erase(it);   // (5)
        else ++it;
    }
    for (const auto& [k, g] : m) std::cout << k << "=" << g << " ";
    std::cout << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Vòng `for` **không có** `++it` ở đầu; việc nhích do thân vòng lặp quyết định. `v.end()` được gọi lại mỗi vòng |
| (2) | Xóa phần tử chẵn; `it` nhận iterator của phần tử kế (đã dồn lên) |
| (3) | Chỉ khi **không** xóa mới nhích |
| (4) | `list::erase` cũng trả iterator kế tiếp |
| (5) | `map::erase(it)` trả iterator kế tiếp từ C++11, cùng khuôn |

**Kết quả khi chạy:**

```text
1 3 
1 3 
1=10 3=30 
```

Vài điều cần nhớ. Điều kiện phải gọi `v.end()` **mỗi vòng**, không lưu `end()` vào biến trước vòng lặp, vì `erase` làm `end()` cũ hỏng. Không bao giờ `erase(c.end())`: đó là UB. Xóa từng phần tử giữa vector tốn O(n) mỗi lần (dồn các phần tử sau), nên xóa nhiều phần tử theo điều kiện thì dùng idiom **remove-erase** ở Bài 20 (C++20 còn có `std::erase_if`).

!!! info "Bạn biết Go?"
    Xóa khi `range` map trong Go là **hợp lệ**: `for k := range m { if k%2 == 0 { delete(m, k) } }` chạy đúng (mình đã chạy: còn `map[1:10 3:30]`), và đặc tả Go nói mục chưa duyệt tới mà bị xóa thì sẽ không được trả ra. C++ khác hẳn: chỉ an toàn nếu bạn dùng iterator mà `erase` trả về. Với slice Go, `t = append(t[:i], t[i+1:]...)` trong `range` không gây UB nhưng cũng **bỏ sót** phần tử y như ví dụ `1 2 3` ở trên (mình đã chạy: `[1 2 3]`).

!!! warning "Hay nhầm"
    "`list`/`map` không bao giờ bị hỏng iterator". Chuẩn nói: thêm thì không cái nào hỏng, xóa thì **chỉ iterator của phần tử bị xóa** hỏng, và đó chính là `it` bạn đang cầm.

## 💻 Ví dụ code

Chương trình chạy thử những ô "còn sống" của bảng mục 4: vector đã `reserve`, `list` thêm/xóa, và tham chiếu tới phần tử `unordered_map` qua một lần rehash.

```cpp
#include <iostream>
#include <iterator>
#include <list>
#include <unordered_map>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};
    v.reserve(100);                                  // (1)
    auto it = v.begin();
    v.push_back(4);                                  // (2)
    std::cout << *it << " " << (v.capacity() >= 100) << "\n";

    std::list<int> l = {1, 2, 3};
    auto a = l.begin();
    auto b = std::next(a);
    l.push_back(4);                                  // (3)
    l.erase(b);                                      // (4)
    std::cout << *a << " " << l.size() << "\n";

    std::unordered_map<int, int> m;
    m[1] = 10;
    int& r = m[1];                                   // (5)
    auto cu = m.bucket_count();
    for (int i = 2; i <= 100; ++i) m[i] = i;         // (6)
    std::cout << r << " " << (m.bucket_count() != cu) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Còn dùng được không |
|---|---|---|
| (1) | Xin chỗ trước: capacity ít nhất 100 | `it` lấy ở dòng sau |
| (2) | `push_back` không cần tái cấp phát | `it` (phía trước điểm thêm) còn sống theo chuẩn |
| (3) | `list` thêm cuối | `a`, `b` đều còn sống |
| (4) | Xóa `b` | chỉ `b` hỏng; `a` còn sống |
| (5) | Giữ tham chiếu tới giá trị khóa 1; `bucket_count()` cho biết số hộp hiện có của bảng (Bài 18) | `r` là biệt danh của giá trị 10 |
| (6) | Thêm 99 khóa nữa: bảng rehash (`bucket_count` đổi) | iterator cũ sẽ hỏng, nhưng tham chiếu `r` còn sống theo chuẩn |

**Kết quả khi chạy:**

```text
1 1
1 3
10 1
```

Dòng cuối cho thấy `r` vẫn đọc ra `10` và số hộp đã đổi (`1`); số hộp cụ thể khác nhau giữa các thư viện. Mình cũng chạy lại chương trình với `-fsanitize=address,undefined`: không báo gì.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Iterator invalidation là gì? Cho ví dụ."
    Là khi một thao tác trên container làm iterator (và có thể tham chiếu, con trỏ) lấy từ trước không còn hợp lệ; dùng nó là hành vi không xác định. Ví dụ: giữ `auto it = v.begin();` rồi `v.push_back(x)` làm vector tái cấp phát, `it` trỏ vào mảng đã trả. Ví dụ thứ hai: `erase(it)` làm hỏng `it` và mọi iterator từ đó trở đi của vector. Với `list` và `map`, thêm không làm hỏng iterator nào và xóa chỉ làm hỏng iterator của phần tử bị xóa.

??? question "Xóa các phần tử thỏa điều kiện khi đang duyệt thì viết thế nào?"
    Dùng iterator mà `erase` trả về: `for (auto it = c.begin(); it != c.end();) { if (cd(*it)) it = c.erase(it); else ++it; }`, gọi lại `c.end()` mỗi vòng. Sai là `c.erase(it); ++it;` (dùng `it` đã hỏng). Với `vector`, nếu xóa nhiều phần tử thì dùng remove-erase (Bài 20) vì mỗi lần `erase` giữa vector là O(n).

??? question "Vì sao `end()` trỏ sau phần tử cuối? Và range-for chạy thế nào?"
    Để dãy rỗng biểu diễn được (`begin() == end()`), vòng lặp chỉ cần `!=`, và `end() - begin()` là số phần tử. Range-for lấy `begin()` và `end()` **một lần**, rồi lặp `++` đến khi bằng `end()`; vì thế thêm/xóa phần tử của chính container đang duyệt có thể làm `end()` đã lấy bị hỏng.

??? question "Iterator khác con trỏ thế nào? `iterator` khác `const_iterator`?"
    Iterator là khái niệm tổng quát hóa con trỏ: cùng `*`, `++`, `->`, `==`, nhưng là kiểu riêng của từng container, và không phải loại nào cũng cho `+ n` (chỉ `vector`, `deque`, `array`). `const_iterator` (từ `cbegin()` hoặc container `const`) cho đọc mà không cho sửa phần tử, tương tự `const T*`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `erase(it)` rồi `++it`, hoặc lưu `end()` trước vòng lặp"
    Cả hai dùng iterator đã hỏng (mục 5). Viết `it = c.erase(it)` và gọi lại `c.end()` mỗi vòng.

!!! warning "Lỗi 2: Thêm hoặc xóa phần tử của chính container trong range-for"
    `for (auto x : v) { v.push_back(...); }` lấy `end()` một lần rồi dùng nó sau khi vector đã đổi (mục 4). Duyệt bằng chỉ số, hoặc gom thay đổi lại rồi áp dụng sau vòng lặp.

!!! warning "Lỗi 3: Giữ iterator qua `push_back`/`insert` vào vector rồi dùng lại"
    Kể cả khi hôm nay "chạy đúng", chuẩn không bảo đảm: chỉ cần vector đầy là iterator hỏng. Lấy lại `begin()`/`find()` sau khi thay đổi, hoặc dùng chỉ số.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="19" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** `v.end()` của một vector chỉ vào đâu?

- Chính phần tử cuối cùng của vector đó
- Ngay sau phần tử cuối, chỉ dùng để so sánh
- Phần tử đầu tiên, giống hệt `v.begin()`
- Một con trỏ rỗng dùng chung cho mọi vector khác

<p class="giai-thich" markdown>`end()` là vị trí ngay sau phần tử cuối: nó có thể so sánh nhưng không được `*`, giống `a + 3` của mảng ba phần tử ở Bài 05. Nếu nó chỉ vào phần tử cuối thì không biểu diễn được dãy rỗng. Chỉ vào phần tử đầu là việc của `begin()`; hai iterator này bằng nhau chỉ khi vector rỗng. Còn "con trỏ rỗng dùng chung" sai vì mỗi `end()` thuộc về đúng container của nó.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
std::vector<int> v = {5, 6, 7};
auto it = v.begin();
++it;
*it = 60;
std::cout << v[1] << " " << (it - v.begin());
```

- `6 1`, vì `*it = 60` chỉ sửa một bản chép tạm
- `60 2`, vì chỉ số của iterator đếm từ 1, không từ 0
- `60 1`, vì `*it` sửa thẳng phần tử thứ hai
- `5 60`, vì `it` vẫn trỏ vào phần tử đầu tiên

<p class="giai-thich" markdown>`++it` nhích từ phần tử 0 sang phần tử 1, `*it = 60` sửa chính phần tử đó trong vector nên `v[1]` là 60, và `it - v.begin()` là 1. Iterator không phải bản chép: qua nó sửa được phần tử thật. Chỉ số vẫn đếm từ 0 nên không thể là 2. Việc `it` còn ở phần tử đầu chỉ đúng trước khi gọi `++it`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Vector còn dư capacity. Bạn giữ iterator vào phần tử giữa rồi `push_back` một số. Chuẩn nói gì về iterator đó?

- Còn dùng được, vì vector không đổi mảng khác
- Luôn hỏng, vì `push_back` luôn đổi sang mảng mới
- Còn dùng được, kể cả `end()` lấy từ trước
- Chỉ còn dùng được nếu nó chính là `begin()`

<p class="giai-thich" markdown>Khi không phải tái cấp phát, các iterator trước điểm thêm còn sống (chỉ `end()` cũ hỏng), nên iterator vào phần tử giữa dùng tiếp được. Việc "luôn hỏng" chỉ xảy ra khi vector phải xin mảng mới. `end()` cũ thì hỏng vì nó từng chỉ vào chỗ nay đã có phần tử. Và không có luật riêng nào dành cho `begin()`: mọi iterator phía trước đều như nhau.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn code sau. Lỗi nằm ở đâu?

```text
std::list<int> l = {1, 2, 3};
for (auto it = l.begin(); it != l.end(); ++it) {
    if (*it == 2) l.erase(it);
}
```

- Không có lỗi nào, vì iterator của `list` không bao giờ hỏng
- `erase` không dùng được với `list`, chỉ dùng với vector
- `list` không có thứ tự nên so sánh `*it == 2` không xác định
- `++it` dùng `it` đã bị xóa; phải viết `it = l.erase(it)`

<p class="giai-thich" markdown>Sau `l.erase(it)`, iterator `it` của phần tử vừa xóa đã hỏng, mà `++it` ở đầu vòng sau vẫn dùng nó: đó là UB. Đúng là `list` chỉ làm hỏng iterator của phần tử **bị xóa**, nhưng đó chính là `it` này, nên lập luận "không bao giờ hỏng" sai. `list` có `erase`, và có thứ tự theo vị trí nên so sánh giá trị vẫn rõ nghĩa.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Chèn thêm nhiều phần tử vào `unordered_map` làm bảng rehash. Điều nào đúng theo chuẩn?

- Cả iterator lẫn tham chiếu tới phần tử cũ đều còn dùng được
- Iterator cũ hỏng, tham chiếu tới phần tử cũ vẫn dùng được
- Cả iterator lẫn tham chiếu tới phần tử cũ đều bị hỏng hết
- Tham chiếu cũ hỏng, nhưng iterator cũ vẫn dùng tiếp được

<p class="giai-thich" markdown>Rehash xây lại bảng nên iterator bị vô hiệu, nhưng các phần tử không bị chép sang chỗ khác, nên tham chiếu và con trỏ tới chúng vẫn sống. Vì vậy hai phát biểu "cả hai còn" và "cả hai hỏng" đều sai, và phát biểu ngược lại (iterator sống, tham chiếu hỏng) cũng sai. Đây là điểm khác với vector tái cấp phát, nơi cả hai đều hỏng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** So sánh Go và C++ khi xóa phần tử của map lúc đang duyệt. Điều nào đúng?

- Cả hai đều là UB, nên không bao giờ được làm khi đang duyệt map
- Go là UB còn C++ thì luôn an toàn dù xóa kiểu nào
- Cả hai an toàn kể cả với `m.erase(it); ++it` kiểu C++
- Go cho phép; C++ chỉ khi dùng iterator mà `erase` trả về

<p class="giai-thich" markdown>Đặc tả Go cho phép `delete` trong lúc `range` map. C++ chỉ an toàn với khuôn `it = m.erase(it)`; còn `m.erase(it); ++it` dùng iterator đã hỏng và là UB. Nên không thể nói cả hai đều UB, và cũng không thể nói C++ luôn an toàn hay Go mới là bên UB.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Đọc đoạn code sau (vector có capacity 3). Điều nào đúng?

```text
std::vector<int> v = {1, 2, 3};
for (auto x : v) {
    if (x == 1) v.push_back(4);
}
```

- Hành vi không xác định vì `end()` đã được lấy từ trước
- In ra bốn phần tử vì range-for tự cập nhật lại `end()` mỗi vòng
- Lỗi biên dịch vì range-for không cho phép đổi vector
- An toàn, vì `push_back` chỉ thêm vào cuối vector này

<p class="giai-thich" markdown>Range-for lấy `begin()` và `end()` một lần; `push_back` khi đầy làm vector tái cấp phát nên cả hai đã hỏng, và việc dùng tiếp là UB. Range-for không tự cập nhật `end()`, và trình biên dịch cũng không từ chối đoạn code này. Việc "chỉ thêm vào cuối" không cứu được: chính cái thêm ở cuối làm vector chuyển sang mảng mới.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Đọc đoạn code sau. Chuyện gì xảy ra?

```text
const std::vector<int> v = {1, 2};
auto it = v.begin();
*it = 5;
```

- Chạy được và phần tử `v[0]` sẽ đổi thành 5
- Chạy được nhưng `v` vẫn giữ 1 vì `it` chỉ là bản chép
- Lỗi biên dịch vì vector `const` có iterator chỉ-đọc
- Biên dịch được nhưng sẽ gây UB lúc chạy chương trình

<p class="giai-thich" markdown>Vì `v` là `const`, `begin()` trả `const_iterator`, và gán qua nó bị trình biên dịch chặn (mục 3 có thử với thông điệp `assignment of read-only location`). Iterator không phải bản chép nên nếu được phép gán thì `v[0]` đã đổi. Còn UB lúc chạy sai vì lỗi này bị bắt từ lúc biên dịch.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Iterator là "con trỏ tổng quát" của container: `begin()` chỉ phần tử đầu, `end()` chỉ vị trí **sau** phần tử cuối (không được `*`), có `*it`, `++it`, `it->`; `vector`/`deque`/`array` cho `it + n`, còn `list`/`map` chỉ nhích từng bước (dùng `std::next`).
2. Range-for lấy `begin()`/`end()` một lần rồi lặp `++`; `cbegin()`/`const_iterator` cho đọc mà không sửa, và `auto` giúp khỏi gõ kiểu dài.
3. Iterator invalidation: thao tác làm iterator cũ hết hợp lệ, dùng tiếp là UB; theo chuẩn, `vector` tái cấp phát hỏng tất cả, `deque` giữa hỏng tất cả, `list`/`map` chỉ hỏng cái bị xóa, `unordered_*` rehash hỏng iterator (tham chiếu vẫn sống).
4. g++ bản thường không kiểm tra (đọc rác, hoặc "chạy ra đúng" một cách tình cờ); ASan hoặc `-D_GLIBCXX_DEBUG` giúp bắt lỗi khi chạy thử.
5. Xóa khi duyệt: `it = c.erase(it)` và chỉ `++it` khi không xóa, gọi lại `c.end()` mỗi vòng; Go cho phép xóa khi `range` map, C++ thì không; xóa nhiều phần tử của vector dùng remove-erase (Bài 20).
