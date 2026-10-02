# Bài 18 — map, set, unordered_map: tra cứu theo khóa

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::map`/`std::set` (có thứ tự theo khóa, tìm/chèn/xóa O(log n), giải thích ở mục 1) và `std::unordered_map`/`std::unordered_set` (băm, O(1) trung bình, không có thứ tự).
    - Tránh bẫy `m[k]`: đọc một khóa chưa có bằng `operator[]` sẽ **chèn** khóa đó; biết dùng `find`, `count`, `at`, và phân biệt `insert`, `emplace`, `try_emplace`.
    - Duyệt map bằng `for (const auto& [khoa, giaTri] : m)`, chọn `map` hay `unordered_map`, và biết khóa tự định nghĩa cần gì.

**Bạn cần biết trước:** [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`std::pair`, structured binding, `if` có khởi tạo), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (`try`/`catch`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`operator*`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 16](16-vector.md) (vector, `at`) và [Bài 17](17-string-array-deque-list.md) (`std::string`, ký hiệu O(1)/O(n)).

## 🧠 Câu chuyện mở đầu

Bạn có một **cuốn danh bạ**: mỗi dòng gồm một **khóa** (tên người) và một **giá trị** (số điện thoại). Hỏi "số của An?" thì tra theo tên, không tra theo vị trí. Đó là `std::map` và `std::unordered_map`; còn `std::set` là danh bạ chỉ có tên, không có số.

Có hai cách tổ chức. **`std::map`** xếp các dòng **theo thứ tự tên** (A, B, C...): tra bằng cách so tên với một dòng rồi bỏ đi khoảng một nửa số dòng còn lại, lặp lại. **`std::unordered_map`** là một **phòng thư nhiều hộp thư**: người gác lấy tên, tính ra một con số (**hàm băm**), con số đó chọn hộp, rồi chỉ lục trong hộp ấy. Các hộp không xếp theo thứ tự nào.

!!! info "Chỗ nào ví dụ này không còn đúng?"
    Thật ra không có cuốn sổ phẳng nào. Chuẩn C++ chỉ bảo đảm `map` giữ khóa theo thứ tự và tìm trong O(log n); trong các bản thư viện phổ biến, nó xếp các **nút** rời ở heap thành một **cây cân bằng**.

    Cây đó hoạt động thế này: so khóa với một nút, nhỏ hơn thì rẽ trái, lớn hơn thì rẽ phải. "Cân bằng" là cây không lệch hẳn về một bên, nên mỗi lần rẽ loại bỏ cỡ một nửa số nút còn lại. `unordered_map` thì thường giữ một dãy "hộp" thật, và hàm băm chọn hộp.

## 📖 Giải thích

### 1. `std::map`: danh bạ có thứ tự

`std::map<K, V>` (`#include <map>`) là bảng từ khóa kiểu `K` sang giá trị kiểu `V`, mỗi khóa **chỉ xuất hiện một lần**, và các khóa luôn được giữ theo thứ tự `<`. Chuẩn bảo đảm tìm, chèn, xóa theo khóa tốn **O(log n)**: mỗi lần n gấp đôi chỉ thêm một bước (một triệu phần tử cỡ hai chục bước). Chương trình dưới là danh bạ điểm; `K` là `std::string`, nên thứ tự là thứ tự từ điển của [Bài 17](17-string-array-deque-list.md).

`find(khoa)` trả về một **iterator**: một "ngón tay chỉ" vào phần tử tìm thấy, dùng giống con trỏ (`->`, `*`; chi tiết ở Bài 19). Không thấy thì nó trả `m.end()`, "ngón tay chỉ ra ngoài cuối". Phần tử của map là một `std::pair` ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)): `it->first` là khóa, `it->second` là giá trị.

```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> diem;                       // (1)
    diem["Binh"] = 7;                                      // (2)
    diem["An"] = 9;
    diem["Chi"] = 8;
    diem["An"] = 10;                                       // (3)
    std::cout << "size = " << diem.size() << "\n";
    for (const auto& [ten, d] : diem) {                    // (4)
        std::cout << ten << "=" << d << " ";
    }
    std::cout << "\n";
    if (auto it = diem.find("Binh"); it != diem.end()) {   // (5)
        std::cout << "Binh: " << it->second << "\n";
    }
    if (diem.find("Dung") == diem.end()) {                 // (6)
        std::cout << "khong co Dung\n";
    }
    std::cout << diem.count("An") << " " << diem.count("Dung") << "\n";   // (7)
    diem.erase("Binh");                                    // (8)
    std::cout << "sau erase: " << diem.size() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Một map rỗng, khóa `std::string`, giá trị `int` | `{}` |
| (2) | `diem[k] = v` đặt giá trị cho khóa `k` (chưa có thì thêm; mục 3 nói kỹ) | `{An:9, Binh:7, Chi:8}` (tự xếp theo khóa) |
| (3) | `"An"` đã có nên chỉ **ghi đè**, không thêm dòng | `{An:10, Binh:7, Chi:8}`, size 3 |
| (4) | Duyệt theo thứ tự khóa; `[ten, d]` tách từng cặp (Bài 14) | in `An=10 Binh=7 Chi=8 ` |
| (5) | `find` thấy `"Binh"`; `it->second` là giá trị | in `Binh: 7` |
| (6) | `find` không thấy `"Dung"` nên trả `end()` | in `khong co Dung` |
| (7) | `count(k)` trả số dòng có khóa `k`: với map chỉ là 0 hoặc 1 | in `1 0` |
| (8) | `erase(k)` xóa dòng có khóa `k` | `{An:10, Chi:8}`, size 2 |

Cột cuối chỉ là hình dung; thường là các nút rời ở heap.

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -pthread`):

```text
size = 3
An=10 Binh=7 Chi=8 
Binh: 7
khong co Dung
1 0
sau erase: 2
```

Ở (4), kiểu của mỗi phần tử là `std::pair<const std::string, int>`: **khóa là `const`**, vì sửa khóa sẽ làm sai thứ tự của cả cây. Muốn "đổi khóa" thì `erase` khóa cũ rồi thêm khóa mới.

**Thử thay đổi:** viết `for (auto& [ten, d] : diem) { d++; ten += "x"; }`. Mình đã biên dịch: g++ báo lỗi ở `ten += "x"` (`no match for 'operator+='`, vì `ten` là `const std::string`). Bỏ riêng dòng đó thì `d++` chạy tốt: giá trị sửa được, khóa thì không.

### 2. `std::set`: danh bạ chỉ có tên

`std::set<K>` (`#include <set>`) giống `map` nhưng chỉ có khóa, không có giá trị: một **tập** các phần tử không trùng, luôn theo thứ tự. Thêm một phần tử đã có thì **không làm gì**.

```cpp
#include <iostream>
#include <set>

int main() {
    std::set<int> s = {30, 10, 20, 10};                    // (1)
    s.insert(20);                                          // (2)
    s.insert(5);
    for (int x : s) {
        std::cout << x << " ";
    }
    std::cout << "\n";
    std::cout << "size = " << s.size() << ", count(20) = " << s.count(20) << "\n";
    s.erase(10);                                           // (3)
    std::cout << "co 10 khong? " << s.count(10) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Dựng từ danh sách; `10` lặp lần hai bị bỏ qua | `{10, 20, 30}` |
| (2) | `20` đã có nên không thêm; `5` mới thì thêm vào đúng chỗ | `{5, 10, 20, 30}` |
| in | Duyệt luôn theo thứ tự tăng | in `5 10 20 30 `, `size = 4, count(20) = 1` |
| (3) | `erase(10)` bỏ phần tử bằng 10 | `{5, 20, 30}` |

**Kết quả khi chạy:**

```text
5 10 20 30 
size = 4, count(20) = 1
co 10 khong? 0
```

Dùng `set` khi bạn chỉ cần hỏi "có hay chưa" hoặc "bỏ trùng và sắp xếp luôn". Go **không có** kiểu set riêng: người ta hay dùng `map[K]struct{}` hoặc `map[K]bool`.

### 3. Bẫy kinh điển: `m[k]` tự chèn

`m[k]` trả về tham chiếu tới giá trị của khóa `k`. Nếu `k` **chưa có**, map **thêm** một dòng mới với giá trị mặc định (số thì 0, `std::string` thì rỗng) rồi trả tham chiếu tới nó. Nghĩa là **chỉ đọc** `m[k]` cũng có thể làm map to ra. Chương trình dưới đọc mà không định ghi:

```cpp
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

int main() {
    std::map<std::string, int> kho;
    kho["tao"] = 5;
    std::cout << "doc cam: " << kho["cam"] << "\n";                // (1)
    std::cout << "size = " << kho.size() << "\n";                  // (2)
    std::cout << "count nho = " << kho.count("nho") << ", size = " << kho.size() << "\n";   // (3)
    try {
        std::cout << kho.at("xoai") << "\n";                       // (4)
    } catch (const std::out_of_range&) {
        std::cout << "at: khong co xoai\n";
    }
    std::cout << "size = " << kho.size() << "\n";
    kho["tao"]++;                                                  // (5)
    kho["le"]++;                                                   // (6)
    std::cout << "tao = " << kho["tao"] << ", le = " << kho["le"] << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `"cam"` chưa có: map **chèn** `cam` với giá trị 0 rồi trả 0 | `{cam:0, tao:5}` |
| (2) | Trước đó chỉ có `tao` (1 dòng); `cam` vừa được chèn nên giờ là 2 dòng | in `size = 2` |
| (3) | `count` chỉ **hỏi**, không chèn | size vẫn 2 |
| (4) | `at` ném `std::out_of_range` khi không có khóa (Bài 16), cũng không chèn | in `at: khong co xoai` |
| (5) | `tao` đã có: tăng 5 lên 6 | `tao:6` |
| (6) | `le` chưa có: chèn với 0 rồi `++` thành 1; đây là cách **đếm** quen thuộc | `{cam:0, le:1, tao:6}` |

**Kết quả khi chạy:**

```text
doc cam: 0
size = 2
count nho = 0, size = 2
at: khong co xoai
size = 2
tao = 6, le = 1
```

Ba cách hỏi khóa, ba hành vi: `m[k]` chèn nếu thiếu; `m.at(k)` ném ngoại lệ nếu thiếu; `m.find(k)` / `m.count(k)` chỉ hỏi và không đổi map.

Từ **C++20** có thêm `m.contains(k)` trả `true`/`false`; ở `-std=c++17` thì chưa có (mình đã biên dịch: `'class std::map<int, int>' has no member named 'contains'`; với `-std=c++20` thì chạy). Với C++17, dùng `count(k) != 0` hoặc `find(k) != end()`.

**Thử thay đổi:** gọi `m["x"]` trong hàm nhận `const std::map<...>&`. Mình đã biên dịch: g++ báo `... discards qualifiers`. `[]` có thể chèn nên không dùng được trên map `const`; ở đó dùng `at` hoặc `find`.

!!! info "Bạn biết Go?"
    Trong Go, `v := m[k]` với khóa chưa có trả **zero value** và **không** thêm gì vào map; `v, ok := m[k]` cho biết có hay không. Bên C++, `m[k]` cũng cho `0` với `int`, nhưng **chèn** khóa vào. `v, ok := m[k]` gần nhất với `auto it = m.find(k); it != m.end()` (`ok` ↔ so với `end()`, `v` ↔ `it->second`). Còn `m[k]++` thì cả hai đều chạy được trên khóa mới: Go và C++ đều coi giá trị khởi đầu là 0.

### 4. `insert`, `emplace`, `try_emplace` và `std::pair`

Ba hàm thêm một dòng vào map. Điểm chung: nếu khóa **đã có**, chúng **không ghi đè**; còn `m[k] = v` thì ghi đè. `insert` nhận một cặp `{khoa, giaTri}` và trả về một `std::pair`: iterator chỉ vào dòng đó, và `bool` cho biết có thêm mới không. Ta tách cặp trả về bằng structured binding (Bài 14).

`emplace(đối số...)` dựng dòng mới ngay trong map từ các đối số; `try_emplace(khoa, đối số...)` (C++17) thì **chỉ dựng khi khóa chưa có**, và chuẩn bảo đảm khi khóa đã có thì các đối số không bị đụng tới. Chương trình dưới dùng `std::move` (Bài 12) để thấy khác biệt:

```cpp
#include <iostream>
#include <map>
#include <string>
#include <utility>

int main() {
    std::map<std::string, int> m;
    auto [it1, moi1] = m.insert({"a", 1});                  // (1)
    auto [it2, moi2] = m.insert({"a", 99});                 // (2)
    std::cout << moi1 << " " << moi2 << " a=" << it2->second << "\n";
    m["a"] = 99;                                            // (3)
    std::cout << "a=" << m["a"] << "\n";

    std::map<int, std::string> ten;
    std::string s1 = "mot";
    std::string s2 = "hai";
    ten.try_emplace(1, std::move(s1));                      // (4)
    ten.try_emplace(1, std::move(s2));                      // (5)
    std::cout << "ten[1]=" << ten[1] << ", s1=[" << s1 << "], s2=[" << s2 << "]\n";
    ten.emplace(2, "ba");                                   // (6)
    std::cout << "size = " << ten.size() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `"a"` mới nên thêm; `moi1` là `true` (in thành 1) | `{a:1}` |
| (2) | `"a"` đã có: **không làm gì**; `moi2` là `false`, `it2` chỉ vào dòng cũ | `{a:1}` |
| (3) | `m[k] = v` mới ghi đè | `{a:99}` |
| (4) | `1` chưa có: dựng dòng mới, chuỗi `mot` được move vào | `{1:"mot"}`, `s1` đã bị move |
| (5) | `1` đã có: **không dựng gì**, `s2` còn nguyên | `s2` = `hai` |
| (6) | `emplace(2, "ba")` dựng dòng `{2:"ba"}` ngay trong map | size 2 |

**Kết quả khi chạy:**

```text
1 0 a=1
a=99
ten[1]=mot, s1=[], s2=[hai]
size = 2
```

`s1` rỗng vì đã bị move đi (Bài 12: sau khi move thì chuỗi hợp lệ nhưng chuẩn không nói giá trị gì; g++ ra rỗng).

**Thử thay đổi:** đổi dòng (5) thành `ten.emplace(1, std::move(s2));`. Mình đã chạy trên g++ 11: `s2` thành rỗng dù khóa đã có, vì `emplace` có thể dựng dòng tạm trước rồi mới phát hiện trùng khóa. Chuẩn **không hứa** điều đó; chuẩn chỉ hứa cho `try_emplace` (đối số nguyên vẹn khi trùng). Vì vậy khi truyền vào một thứ vừa move mà khóa có thể đã tồn tại, hãy dùng `try_emplace`.

### 5. `std::unordered_map` và `std::unordered_set`: bảng băm

`std::unordered_map<K, V>` (`#include <unordered_map>`) và `std::unordered_set<K>` có **cùng cách dùng** như `map`/`set`: `[]`, `find`, `count`, `insert`, `erase`, `size`, duyệt range-for, cùng bẫy `[]` tự chèn. Khác ở bên trong (phòng thư nhiều hộp) và ở ba điều chuẩn nói:

- Tìm/chèn/xóa **O(1) trung bình**, nhưng **xấu nhất O(n)**: nếu mọi khóa dồn vào cùng một hộp thì phải lục cả hộp.
- **Không có thứ tự**: thứ tự duyệt không xác định, tùy bản thư viện và có thể đổi khi thêm phần tử. Đừng dựa vào nó.
- Khi hộp quá đầy, bảng tự **rehash** (xây lại với nhiều hộp hơn): thứ tự duyệt có thể đổi và iterator cũ bị vô hiệu (Bài 19 nói kỹ).

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

int main() {
    std::vector<std::string> tu = {"a", "b", "a", "c", "a", "b"};
    std::unordered_map<std::string, int> dem;               // (1)
    for (const std::string& t : tu) {
        dem[t]++;                                           // (2)
    }
    std::cout << "size = " << dem.size() << "\n";
    std::vector<std::string> hoi = {"a", "b", "c", "z"};
    for (const std::string& t : hoi) {
        auto it = dem.find(t);                              // (3)
        std::cout << t << ": " << (it == dem.end() ? 0 : it->second) << "\n";
    }
    int tong = 0;
    for (const auto& [t, n] : dem) {                        // (4)
        tong += n;
    }
    std::cout << "tong = " << tong << "\n";

    std::unordered_set<int> da;
    std::vector<int> so = {3, 1, 3, 2, 1};
    for (int x : so) {
        da.insert(x);                                       // (5)
    }
    std::cout << "set: " << da.size() << " phan tu, co 2? " << da.count(2) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Bảng băm rỗng | các hộp đều trống |
| (2) | Đếm: `a` ba lần, `b` hai, `c` một | `{a:3, b:2, c:1}` (thứ tự bên trong không biết) |
| (3) | Tra từng từ **bằng `find`** để khỏi chèn nhầm `z` | in 3, 2, 1, rồi 0 cho `z` |
| (4) | Duyệt cả bảng: **không in từng dòng** vì thứ tự tùy máy; chỉ cộng các số đếm | `tong` = 6 |
| (5) | Thêm từng số của `so` vào tập: số lặp bị bỏ qua, còn ba số khác nhau | `{1, 2, 3}` |

**Kết quả khi chạy:**

```text
size = 3
a: 3
b: 2
c: 1
z: 0
tong = 6
set: 3 phan tu, co 2? 1
```

Mình cố ý không chép thứ tự duyệt ra: chương trình nào in nó thì kết quả có thể khác trên máy bạn. Mọi thứ trên (số đếm, `size`, tổng) thì không phụ thuộc thứ tự nên luôn giống nhau.

!!! info "Bạn biết Go?"
    `map[K]V` của Go là **bảng băm**, tương đương `std::unordered_map` (không phải `std::map`). Go còn cố ý **xáo ngẫu nhiên** thứ tự `for range` để bạn không phụ thuộc vào nó; C++ không xáo, nhưng cũng không hứa gì, và kết quả giữa g++, clang, MSVC có thể khác. Muốn duyệt theo thứ tự thì Go phải lấy khóa ra, sắp xếp rồi duyệt; C++ chỉ cần dùng `std::map`.

### 6. Chọn `map` hay `unordered_map`, và khóa tự định nghĩa

| Bạn cần | Chọn | Lý do |
|---|---|---|
| Chỉ tra, đếm, kiểm tra "có chưa" theo khóa | `unordered_map` / `unordered_set` | O(1) trung bình, thường nhanh hơn khi nhiều phần tử |
| Duyệt theo thứ tự khóa (in báo cáo, kết quả cố định) | `map` / `set` | thứ tự có sẵn, giống nhau ở mọi máy |
| Hỏi theo khoảng ("khóa nhỏ nhất", "từ 10 đến 20") | `map` / `set` | hàng xóm trong thứ tự là hàng xóm trong cây |
| Khóa tự định nghĩa, chỉ có sẵn phép `<` | `map` / `set` | không cần viết hàm băm |
| Rất ít phần tử (vài chục) | cái nào cũng được, kể cả `vector` duyệt thẳng | chênh lệch nhỏ; **đo** trước khi đổi |

**Khóa tự định nghĩa.** `map`/`set` cần so thứ tự hai khóa, nên kiểu khóa phải có `operator<` (đặt tên hàm là `operator<` thì viết `a < b` gọi hàm đó, như `operator*` ở Bài 09). Chuẩn đòi hỏi vài quy tắc, và đây là ba cái dễ vi phạm nhất:

- `a < a` phải luôn sai (nên dùng `<`, đừng dùng `<=`).
- `a < b` đúng thì `b < a` phải sai.
- Bắc cầu: `a < b` và `b < c` thì `a < c`.

Hai khóa mà không cái nào nhỏ hơn cái kia được coi là **trùng**; `map` không dùng `==`.

```cpp
#include <iostream>
#include <map>
#include <set>
#include <string>

struct Toa {
    int x;
    int y;
    bool operator<(const Toa& kia) const {                 // (1)
        if (x != kia.x) return x < kia.x;
        return y < kia.y;
    }
};

int main() {
    std::set<Toa> s;
    s.insert({2, 1});
    s.insert({1, 5});
    s.insert({1, 2});
    s.insert({1, 5});                                      // (2)
    for (const Toa& t : s) {
        std::cout << "(" << t.x << "," << t.y << ") ";
    }
    std::cout << "\n";

    std::map<Toa, std::string> ten;
    ten[{0, 0}] = "goc";                                   // (3)
    ten[{3, 4}] = "xa";
    std::cout << ten[{3, 4}] << " " << ten.size() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | So `x` trước, bằng nhau mới so `y`; `const` ở cuối cho phép gọi trên khóa `const` (Bài 06) | quy tắc xếp |
| (2) | `{2, 1}`, `{1, 5}`... điền `x`, `y` theo thứ tự (Bài 14); `{1, 5}` lần hai: không cái nào nhỏ hơn cái kia, nên là trùng, bị bỏ qua | `{(1,2), (1,5), (2,1)}` |
| (3) | `{0, 0}` dựng một `Toa` làm khóa; `ten[...]` thêm dòng | `{(0,0):"goc", (3,4):"xa"}` |

**Kết quả khi chạy:**

```text
(1,2) (1,5) (2,1) 
xa 2
```

**Thử thay đổi:** xóa `operator<` rồi `std::set<Toa> s; s.insert({1, 2});`. Mình đã biên dịch: lỗi `no match for 'operator<' (operand types are 'const Toa' and 'const Toa')`.

Với `unordered_map`/`unordered_set`, khóa tự định nghĩa cần **hai** thứ: một **hàm băm** cho ra con số từ khóa, và `operator==` để phân biệt hai khóa cùng hộp; hai khóa bằng nhau phải cho cùng con số.

Kiểu có sẵn (`int`, `std::string`...) đã có hàm băm. Với `Toa` không có hàm băm thì g++ báo (mình đã biên dịch) `use of deleted function ... std::hash<Toa>`. Cách viết hàm băm vượt phạm vi bài này.

## 💻 Ví dụ code

Đếm tần suất từ bằng `std::map`, in theo thứ tự chữ cái, rồi tìm từ xuất hiện nhiều nhất. Đây là bài toán phỏng vấn quen thuộc.

```cpp
#include <iostream>
#include <map>
#include <string>
#include <vector>

int main() {
    std::vector<std::string> tu = {"go", "c++", "go", "rust", "c++", "go"};
    std::map<std::string, int> dem;
    for (const std::string& t : tu) {
        dem[t]++;                                          // (1)
    }
    for (const auto& [t, n] : dem) {                       // (2)
        std::cout << t << ": " << n << "\n";
    }
    int nhieuNhat = 0;
    std::string tuDo;
    for (const auto& [t, n] : dem) {
        if (n > nhieuNhat) {                               // (3)
            nhieuNhat = n;
            tuDo = t;
        }
    }
    std::cout << "nhieu nhat: " << tuDo << " (" << nhieuNhat << " lan)\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Mỗi từ: chưa có thì chèn với 0 rồi `++`; có rồi thì tăng | `{c++:2, go:3, rust:1}` |
| (2) | Duyệt theo thứ tự khóa, chỉ-đọc, không chép | in ba dòng, `c++` trước `go` trước `rust` |
| (3) | Giữ từ có số đếm lớn nhất đến giờ | `tuDo` = `go`, `nhieuNhat` = 3 |

**Kết quả khi chạy:**

```text
c++: 2
go: 3
rust: 1
nhieu nhat: go (3 lan)
```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::map` và `std::unordered_map` khác nhau thế nào? Khi nào chọn cái nào?"
    `map` giữ khóa theo thứ tự (thường cài bằng cây cân bằng), tìm/chèn/xóa O(log n), cần `operator<` cho khóa. `unordered_map` là bảng băm: O(1) trung bình nhưng xấu nhất O(n), không có thứ tự, cần hàm băm và `==`. Chọn `unordered_map` khi chỉ tra theo khóa; chọn `map` khi cần duyệt theo thứ tự, truy vấn khoảng, hoặc kết quả ổn định giữa các máy. Quan trọng nhất là nói được cái giá của mỗi bên.

??? question "`m[k]` khác `m.at(k)` và `m.find(k)` thế nào?"
    `m[k]` nếu `k` chưa có thì **chèn** một dòng với giá trị mặc định rồi trả tham chiếu (nên không dùng được trên map `const`, và đọc cũng có thể làm map to ra). `m.at(k)` ném `std::out_of_range` nếu thiếu. `m.find(k)` trả iterator, `end()` nếu thiếu, không đổi map. Để kiểm tra tồn tại ở C++17 dùng `count` hoặc `find`; `contains` chỉ có từ C++20.

??? question "`emplace` khác `try_emplace` thế nào?"
    Cả hai dựng dòng mới ngay trong map. `try_emplace` (C++17) chỉ dựng khi khóa chưa có, và chuẩn bảo đảm khi trùng khóa thì đối số không bị đụng tới. `emplace` thì không hứa: có thể dựng tạm rồi mới bỏ, nên thứ bạn vừa `std::move` vào có thể đã mất.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Dựa vào thứ tự duyệt của `unordered_map`"
    Bài kiểm tra so sánh chuỗi in ra, hoặc code giả định "phần tử thêm trước thì duyệt trước", có thể chạy đúng trên máy bạn và sai trên máy khác (mục 5). Cần thứ tự thì dùng `map`, hoặc lấy ra `vector` rồi sắp xếp (Bài 20).

!!! warning "Lỗi 2: `operator<` viết sai cho khóa tự định nghĩa"
    Quên so các trường sau khi trường đầu bằng nhau, hoặc dùng `<=`, làm hai khóa khác nhau bị coi là trùng (mất dòng) hoặc vi phạm yêu cầu của chuẩn (hành vi không xác định). Hãy so từng trường theo thứ tự như `Toa` ở mục 6.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="18" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Bạn cần in một bảng khóa-giá trị theo thứ tự khóa tăng dần, kết quả phải giống nhau trên mọi máy. Chọn kiểu nào?

- `std::unordered_map`, vì băm xếp các khóa tăng dần
- `std::map`, vì nó giữ các khóa theo thứ tự `<`
- `std::unordered_set`, vì tập nào cũng sắp xếp
- `std::vector`, vì nó tự giữ thứ tự khóa khi thêm

<p class="giai-thich" markdown>`std::map` giữ khóa theo thứ tự `<` (chuẩn bảo đảm), nên duyệt ra tăng dần ở mọi máy. Bảng băm không có thứ tự và thứ tự còn khác nhau giữa các bản thư viện, nên `unordered_map` và `unordered_set` không dùng được cho việc này. `vector` thì duyệt được, nhưng không có phép tra theo khóa và không tự sắp xếp.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
std::map<std::string, int> m;
m["a"] = 1;
if (m["b"] == 0) std::cout << "khong co b\n";
std::cout << m.size();
```

- `khong co b`, rồi `1`, vì đọc `m["b"]` không đổi map
- Không in gì rồi `1`, vì `"b"` chưa tồn tại
- Ném `std::out_of_range`, vì khóa `"b"` không có
- `khong co b`, rồi `2`, vì `m["b"]` đã chèn khóa mới

<p class="giai-thich" markdown>`m["b"]` với khóa chưa có thì chèn một dòng giá trị 0, nên điều kiện `== 0` đúng và in dòng đầu, và map có hai khóa nên `size` là 2. Việc "đọc không đổi map" chỉ đúng với `find` hoặc `count`. Cái ném `std::out_of_range` là `at`, không phải `[]`. Còn "không in gì" sai vì `[]` không thấy khóa thì trả giá trị mặc định 0 chứ không báo lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Về `m[k]` khi `k` chưa có và giá trị là `int`, điều nào đúng khi so Go với C++?

- Cả hai cho 0, nhưng chỉ `std::map` thêm khóa
- Go ném lỗi khi thiếu khóa, còn `std::map` trả 0
- Cả hai cho 0 và đều giữ nguyên số khóa của bảng
- Go thêm khóa vào bảng, còn `std::map` thì không thêm

<p class="giai-thich" markdown>Go trả zero value (0 với `int`) và **không** thêm khóa; `std::map::operator[]` cũng trả giá trị mặc định 0 nhưng **chèn** khóa đó. Go không ném lỗi khi đọc khóa thiếu (muốn biết có hay không thì dùng `v, ok := m[k]`). Hai ngôn ngữ khác nhau đúng ở chỗ này, nên không thể nói cả hai đều không thay đổi bảng, cũng không phải Go là bên chèn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn code sau. Nó in ra gì?

```text
std::map<std::string, int> m = {{"a", 1}, {"b", 2}};
for (auto& [k, v] : m) { v += 10; }
std::cout << m["a"] << " " << m["b"];
```

- `1 2`, vì range-for luôn làm việc trên bản chép
- Lỗi biên dịch, vì map không cho sửa gì khi đang duyệt
- `11 12`, vì `v` là biệt danh của giá trị trong map
- `11 2`, vì `v` chỉ đổi ở phần tử đầu tiên của map đó

<p class="giai-thich" markdown>Có `&` thì `[k, v]` là biệt danh của khóa và giá trị gốc (luật của Bài 14), nên `v += 10` sửa thẳng vào map và cả hai phần tử đều tăng. Nếu viết `auto [k, v]` không có `&` thì mới sửa bản chép và in `1 2`. Chương trình biên dịch được vì chỉ **khóa** `k` là `const`, còn giá trị sửa được. Vòng lặp chạy cho mọi phần tử chứ không dừng ở phần tử đầu.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Bạn đếm tần suất của hàng triệu từ, chỉ cần số đếm cuối cùng, không cần thứ tự. Chọn kiểu nào hợp nhất?

- `std::map`, vì thứ tự khóa luôn giúp tra nhanh hơn
- `std::unordered_map`, vì chỉ tra theo khóa, khỏi cần thứ tự
- `std::set`, vì set lưu được cả cặp khóa lẫn số đếm đi kèm
- `std::list`, vì chèn ở giữa chỉ tốn vài bước, nên rất rẻ

<p class="giai-thich" markdown>Chỉ tra và đếm theo khóa, không cần thứ tự, nên `std::unordered_map` với chi phí trung bình O(1) là lựa chọn hợp lý (nếu lo thì đo trước). Thứ tự khóa không làm tra nhanh hơn: `map` tốn O(log n), còn băm trung bình O(1). `std::set` chỉ lưu khóa, không có giá trị đi kèm. `std::list` không tra theo khóa được và phải đi từng nút.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Bạn muốn dùng `struct Toa { int x; int y; }` làm khóa của `std::set<Toa>`. Cần cung cấp gì?

- Chỉ `operator==`, vì set phải biết hai phần tử bằng nhau
- Hàm băm cho `Toa`, vì set tra theo giá trị băm
- Không cần gì, vì set tự so từng byte
- `operator<` để so thứ tự hai `Toa`

<p class="giai-thich" markdown>`std::set` giữ phần tử theo thứ tự nên cần `operator<`; hai phần tử mà không cái nào nhỏ hơn cái kia được coi là trùng, nên `set` không dùng `==`. Hàm băm là yêu cầu của `std::unordered_set`, không phải của `std::set`. Còn "tự so từng byte" không có: thiếu `operator<` thì g++ báo lỗi biên dịch (mình đã chạy).</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Đọc đoạn code sau. Nó in ra gì?

```text
std::map<int, int> m;
m.insert({1, 10});
m.insert({1, 20});
m[2] = 5;
m[2] = 6;
std::cout << m[1] << " " << m[2] << " " << m.size();
```

- `20 6 2`, vì `insert` lần thứ hai ghi đè giá trị cũ
- `10 5 3`, vì mỗi lệnh gọi đều thêm một dòng mới vào map của bạn
- `10 6 2`, vì `insert` không ghi đè, còn gán `=` thì ghi đè
- `10 6 3`, vì `m[2]` chèn thêm một dòng ở mỗi lần gán

<p class="giai-thich" markdown>`insert({1, 20})` khi khóa 1 đã có thì không làm gì, nên `m[1]` còn 10. `m[2] = 5` chèn khóa 2, rồi `m[2] = 6` ghi đè nên còn 6. Map chỉ có hai khóa là 1 và 2 nên `size` là 2. Việc mỗi lệnh thêm một dòng mới sai vì khóa trùng không tạo dòng thứ hai; map không bao giờ có hai dòng cùng khóa.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::map<K, V>` (`<map>`) và `std::set<K>` (`<set>`) giữ khóa không trùng theo thứ tự `<` (thường cài bằng cây cân bằng), tìm/chèn/xóa O(log n); phần tử của map là `std::pair<const K, V>` nên khóa là `const`, duyệt bằng `for (const auto& [khoa, giaTri] : m)`.
2. `std::unordered_map`/`unordered_set` là bảng băm: tìm/chèn/xóa O(1) trung bình, xấu nhất O(n), **không có thứ tự duyệt** (khác nhau giữa các thư viện), rehash làm iterator cũ hỏng (Bài 19); `map[K]V` của Go tương đương nó, và Go cố ý xáo thứ tự duyệt.
3. `m[k]` với khóa chưa có **chèn** giá trị mặc định (Go thì không chèn); `m.at(k)` ném `std::out_of_range`; `find(k)` / `count(k)` chỉ hỏi (`v, ok := m[k]` của Go ↔ `find`); `contains` chỉ có từ C++20.
4. `insert` và `try_emplace` không ghi đè khi khóa đã có (`insert` trả `pair<iterator, bool>`), `m[k] = v` thì ghi đè; `try_emplace` được chuẩn bảo đảm không đụng đối số khi trùng khóa, `emplace` thì không hứa.
5. Chọn `unordered_map` khi chỉ tra theo khóa, `map` khi cần thứ tự hoặc truy vấn khoảng; khóa tự định nghĩa cần `operator<` cho `map`/`set`, còn `unordered_*` cần hàm băm và `==`.
