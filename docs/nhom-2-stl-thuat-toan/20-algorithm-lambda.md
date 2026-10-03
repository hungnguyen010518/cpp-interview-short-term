# Bài 20 — `<algorithm>` và lambda: sort, find, transform, remove-erase

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Hiểu thuật toán của STL nhận **cặp iterator `[begin, end)`** chứ không nhận container, và dùng được `sort`, `find`, `count`, `min_element`/`max_element`, `reverse`.
    - Truyền **lambda** vào `sort` (comparator), `find_if`, `count_if`, `any_of`/`all_of`, `transform`, `for_each`, `accumulate`, và chọn đúng kiểu capture (`[x]`, `[&x]`, `[=]`, `[&]`).
    - Xóa phần tử theo điều kiện bằng **remove-erase**, và biết vì sao `std::remove` không làm vector ngắn đi.

**Bạn cần biết trước:** [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda, `[=]`/`[&]`, `auto`, range-for), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`{"An", 9}` điền các trường của struct, `điều kiện ? A : B`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const&`), [Bài 16](16-vector.md) (`vector`), [Bài 17](17-string-array-deque-list.md) (`list`) và [Bài 19](19-iterator-vo-hieu.md) (iterator, `erase`).

## 🧠 Câu chuyện mở đầu

Quay lại **kệ sách** và **ngón tay** (iterator) của Bài 19. Bây giờ bạn thuê một **người quản thư**. Bạn chỉ đưa cho người ấy **hai ngón tay**: ngón đầu chỉ cuốn đầu của đoạn cần xử lý, ngón sau chỉ chỗ ngay sau cuốn cuối của đoạn. Người ấy không cần biết kệ làm bằng gỗ hay là các thẻ nối dây; cứ hai ngón tay là làm được nhiều việc: tìm một cuốn, đếm, lật ngược.

Đó là cách **thuật toán** của STL làm việc: `std::sort(đầu, cuối)`, `std::find(đầu, cuối, giá_trị)`... Khi việc cần một tiêu chí ("xếp theo điểm giảm dần", "tìm cuốn nào dày hơn 300 trang") bạn đưa thêm một **mẩu giấy ghi luật**: đó là **lambda**.

!!! info "Chỗ nào ví dụ người quản thư không còn đúng?"
    Người quản thư chỉ có hai ngón tay, nên chỉ **xếp lại** sách trên kệ chứ không **vứt bỏ** hay **thêm** được cuốn nào: việc đó thuộc về chủ kệ (container). Chính điều này giải thích mục 5 (`remove` không làm vector ngắn đi). Ngoài ra, xếp nhanh cần ngón tay **nhảy cóc** được; kệ thẻ nối dây chỉ cho nhích từng bước nên `sort` không dùng được (mục 2).

## 📖 Giải thích

### 1. Cặp iterator `[begin, end)` là giao diện chung

Ngoài `<algorithm>`, ta cần `#include <numeric>` cho `std::accumulate` (mục 3). Mọi thuật toán nhận một đoạn **nửa mở** `[begin, end)`: tính `begin`, **không** tính `end` (đúng như `end()` của Bài 19). Vì vậy `v.begin() + 1, v.begin() + 4` là các phần tử ở chỉ số 1, 2, 3 (đếm từ 0; không gồm chỉ số 4).

Các thuật toán tìm kiếm (`find`...) trả về **iterator**, không trả về giá trị: không tìm thấy thì trả về chính `end` mà bạn đưa vào. Bạn phải so với `end` **trước khi** dùng `*it`.

```cpp
#include <algorithm>
#include <iostream>
#include <list>
#include <vector>

int main() {
    std::vector<int> v = {5, 3, 8, 3, 1};
    auto it = std::find(v.begin(), v.end(), 8);                   // (1)
    if (it != v.end()) {                                          // (2)
        std::cout << "thay " << *it << " o vi tri " << it - v.begin() << "\n";
    }
    auto khong = std::find(v.begin(), v.end(), 99);               // (3)
    std::cout << "99: " << (khong == v.end() ? "khong thay" : "co") << "\n";
    std::cout << "so 3 xuat hien " << std::count(v.begin(), v.end(), 3) << " lan\n";   // (4)
    std::cout << "nho nhat " << *std::min_element(v.begin(), v.end())                 // (5)
              << ", lon nhat " << *std::max_element(v.begin(), v.end()) << "\n";

    std::sort(v.begin() + 1, v.begin() + 4);                      // (6)
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";
    std::reverse(v.begin(), v.end());                             // (7)
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";

    std::list<int> l = {7, 8, 9};
    std::cout << "list: " << *std::find(l.begin(), l.end(), 8) << "\n";   // (8)
    int a[4] = {10, 20, 30, 40};
    std::cout << "mang: " << *std::find(a, a + 4, 30) << "\n";            // (9)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `find` đi từ `begin` tới `end`, dừng ở phần tử đầu tiên bằng 8, trả iterator tới đó | `v = [5 3 8 3 1]`, `it` ở số 8 |
| (2) | Kiểm `it != v.end()` rồi mới `*it`; `it - v.begin()` là vị trí 2 | |
| (3) | Không có 99: duyệt hết, trả về `v.end()` | `khong == v.end()` |
| (4) | `count` đếm các phần tử bằng 3: hai lần | |
| (5) | `min_element`/`max_element` trả **iterator** tới phần tử nhỏ/lớn nhất, ta `*` để lấy giá trị (không gọi trên dãy rỗng: `*` lên `end` là UB) | |
| (6) | Chỉ sắp xếp đoạn `[1, 4)`: các số `3 8 3` thành `3 3 8` | `[5 3 3 8 1]` |
| (7) | `reverse` lật ngược cả dãy | `[1 8 3 3 5]` |
| (8) | Cùng `find` chạy trên `list` | |
| (9) | Con trỏ cũng là iterator (Bài 05): `a` và `a + 4` thay cho `begin`/`end` của mảng | |

**Kết quả khi chạy:**

```text
thay 8 o vi tri 2
99: khong thay
so 3 xuat hien 2 lan
nho nhat 1, lon nhat 8
5 3 3 8 1 
1 8 3 3 5 
list: 8
mang: 30
```

Một hàm `find` dùng được cho vector, list và mảng thường, vì nó chỉ cần `++`, `*` và `!=` của iterator. Có thuật toán đòi nhiều hơn thế, như `sort` ở mục 2.

### 2. `sort` và comparator

`std::sort(đầu, cuối)` sắp xếp tăng dần bằng `<`, với thời gian O(n log n) (tăng chậm hơn nhiều so với bình phương số phần tử; Bài 21 nói kỹ). Muốn tiêu chí khác, đưa thêm một hàm **so sánh** (comparator) làm đối số thứ ba. Hàm đó nhận hai phần tử `a`, `b` và trả `true` nếu **`a` phải đứng trước `b`**.

```cpp
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct HocSinh {
    std::string ten;
    int diem;
};

int main() {
    std::vector<int> v = {5, 3, 8, 1, 9};
    std::sort(v.begin(), v.end());                                          // (1)
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";
    std::sort(v.begin(), v.end(), [](int a, int b) { return a > b; });      // (2)
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";

    std::vector<HocSinh> lop = {{"Lan", 7}, {"An", 9}, {"Binh", 7}, {"Cuong", 9}};
    std::sort(lop.begin(), lop.end(), [](const HocSinh& a, const HocSinh& b) {   // (3)
        if (a.diem != b.diem) return a.diem > b.diem;                       // (4)
        return a.ten < b.ten;                                               // (5)
    });
    for (const HocSinh& h : lop) std::cout << h.ten << ":" << h.diem << " ";
    std::cout << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Không có comparator: dùng `<`, tăng dần |
| (2) | Lambda trả `true` khi `a > b`, tức số lớn đứng trước: giảm dần |
| (3) | Comparator của struct nhận hai `const HocSinh&` (không chép, không sửa; Bài 06) |
| (4) | Khác điểm: điểm cao đứng trước |
| (5) | Cùng điểm: so tên theo thứ tự chữ cái, để kết quả luôn như nhau |

**Kết quả khi chạy:**

```text
1 3 5 8 9 
9 8 5 3 1 
An:9 Cuong:9 Binh:7 Lan:7 
```

**Luật cho comparator.** Hàm phải cho **thứ tự chặt**: `comp(a, a)` luôn `false` (một phần tử không đứng trước chính nó), `comp(a, b)` với `comp(b, a)` không cùng `true`, và bắc cầu (`a` trước `b`, `b` trước `c` thì `a` trước `c`). Cứ dùng `<` hoặc `>`: `<=` hay `>=` vi phạm luật, và theo chuẩn thì sort khi đó là **hành vi không xác định** (mình không chạy thử và không nói nó in gì).

**Thử thay đổi: `std::sort(l.begin(), l.end())` với `l` là `std::list<int>`.** Mình đã chạy: lỗi biên dịch `no match for 'operator-' (operand types are 'std::_List_iterator<int>' and 'std::_List_iterator<int>')`. `sort` cần iterator **truy cập ngẫu nhiên** (nhảy được, trừ nhau được như `vector`, `deque`, `array`, mảng thường), còn `list` chỉ nhích từng bước ([Bài 19](19-iterator-vo-hieu.md)). Đó là lý do `list` có hàm riêng `l.sort()` mà Bài 17 đã dùng.

!!! info "Bạn biết Go?"
    `sort.Slice(s, func(i, j int) bool { return s[i] > s[j] })` cùng ý "cái này có đứng trước cái kia không", nhưng less của Go nhận **chỉ số** `i`, `j`, còn comparator C++ nhận **hai phần tử**. Gói `slices` (từ Go 1.21) có `slices.SortFunc` với hàm trả số âm/0/dương, khác C++ trả `bool`.

!!! warning "Hay nhầm"
    `sort` **không ổn định**: hai phần tử "bằng nhau" theo comparator có thể đổi chỗ cho nhau. Cần giữ thứ tự ban đầu của các phần tử bằng nhau thì dùng `std::stable_sort` (cùng cách gọi); nếu không, hãy so thêm một khóa phụ như dòng (5).

### 3. Lambda truyền vào thuật toán

Lambda đã học ở [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md): `[bắt](tham số) { thân }`, cất vào `auto`. Ở đây ta thêm vai trò mới: làm **đối số** của thuật toán. Hàm trả `bool` dùng để hỏi "phần tử này có thỏa không" gọi là **vị từ** (predicate); `find_if`, `count_if`, `any_of`, `all_of` nhận một vị từ.

```cpp
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main() {
    std::vector<int> v = {4, 9, 2, 7, 6};
    int nguong = 6;
    auto lonHon = [nguong](int x) { return x > nguong; };                      // (1)
    auto it = std::find_if(v.begin(), v.end(), lonHon);                        // (2)
    std::cout << "dau tien > 6: " << *it << "\n";
    std::cout << "dem > 6: " << std::count_if(v.begin(), v.end(), lonHon) << "\n";   // (3)
    std::cout << "co so chan: "
              << std::any_of(v.begin(), v.end(), [](int x) { return x % 2 == 0; })   // (4)
              << ", toan so chan: "
              << std::all_of(v.begin(), v.end(), [](int x) { return x % 2 == 0; })
              << "\n";

    std::vector<int> binhPhuong(v.size());                                     // (5)
    std::transform(v.begin(), v.end(), binhPhuong.begin(), [](int x) { return x * x; });   // (6)
    for (int x : binhPhuong) std::cout << x << " ";
    std::cout << "\n";

    int tong = 0;
    std::for_each(v.begin(), v.end(), [&tong](int x) { tong += x; });          // (7)
    std::cout << "for_each: " << tong << "\n";
    std::cout << "accumulate: " << std::accumulate(v.begin(), v.end(), 0) << "\n";    // (8)

    std::vector<double> d = {0.5, 0.25, 0.25};
    std::cout << "init 0: " << std::accumulate(d.begin(), d.end(), 0)
              << ", init 0.0: " << std::accumulate(d.begin(), d.end(), 0.0) << "\n";  // (9)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Lambda `[nguong]` chép `nguong` (6) vào trong nó, cất vào `lonHon`; dùng lại được nhiều lần |
| (2) | `find_if` trả iterator tới phần tử **đầu tiên** làm vị từ đúng: `9` (ở đây chắc chắn có, nên `*it` an toàn; thường vẫn phải kiểm `!= end`) |
| (3) | `count_if` đếm số phần tử thỏa: `9` và `7` |
| (4) | `x % 2` là số dư khi chia cho 2, bằng 0 là số chẵn. `any_of`: có phần tử nào thỏa không (có: 4); `all_of`: tất cả đều thỏa không (không). In ra `1` và `0` |
| (5) | Tạo sẵn vector 5 số 0 làm chỗ chứa kết quả |
| (6) | `transform` áp lambda lên từng phần tử của `[begin, end)` và ghi kết quả bắt đầu từ `binhPhuong.begin()`; chỗ chứa phải đủ lớn |
| (7) | `[&tong]` giữ tham chiếu để cộng dồn vào biến ngoài |
| (8) | `accumulate` (trong `<numeric>`) giữ một biến tích lũy ("bộ cộng") bắt đầu bằng giá trị đầu `0` và cộng từng phần tử vào: 28. Đối số thứ tư tùy chọn là lambda `(bộ cộng, phần tử)` đổi phép cộng sang phép khác; mục 💻 dùng nó |
| (9) | Giá trị đầu `0` là `int` nên **bộ cộng cũng là `int`**; `0.0` là `double` |

**Kết quả khi chạy:**

```text
dau tien > 6: 9
dem > 6: 2
co so chan: 1, toan so chan: 0
16 81 4 49 36 
for_each: 28
accumulate: 28
init 0: 0, init 0.0: 1
```

Dòng `init 0: 0` là cái bẫy kinh điển: cộng `0.5`, `0.25`, `0.25` vào bộ cộng kiểu `int` cho `0` (mỗi lần phần thập phân bị cắt), còn `0.0` cho đúng `1`. Kiểu của giá trị đầu quyết định kiểu kết quả.

**Thử thay đổi: ở dòng (7) viết `[=]` thay `[&tong]`.** Mình đã chạy: lỗi biên dịch `assignment of read-only variable 'tong'` (lambda `[=]` chỉ có bản chép hằng; Bài 13). Cách chọn capture: thân lambda chỉ **đọc** biến ngoài thì `[x]` hoặc `[=]`; cần **ghi lại** ra biến ngoài thì `[&x]`.

!!! info "Bạn biết Go?"
    Closure của Go bắt biến **theo tham chiếu** mà không cần khai báo: `func(x int) { tong += x }` luôn cộng được vào `tong` bên ngoài. C++ bắt bạn nói rõ: `[&tong]` mới là kiểu Go; `[tong]` hay `[=]` là chép. Các hàm của gói `slices` trong Go (`slices.IndexFunc`, `slices.ContainsFunc`) gần với `find_if` và `any_of`.

### 4. Lambda không bắt, `std::function`, và lambda sống lâu hơn biến

Một lambda **không bắt gì** (`[]`) hoạt động như hàm thường: bạn có thể truyền tên hàm vào thuật toán, truyền lambda, hay đổi lambda thành **con trỏ hàm**. `bool (*conTro)(int)` đọc là "`conTro` là con trỏ tới hàm nhận `int` trả `bool`". Lambda **có bắt** thì không đổi được, vì nó còn phải mang dữ liệu theo.

```cpp
#include <algorithm>
#include <functional>
#include <iostream>
#include <vector>

bool laChan(int x) { return x % 2 == 0; }                          // (1)

int main() {
    std::vector<int> v = {1, 2, 3, 4, 6};
    std::cout << std::count_if(v.begin(), v.end(), laChan) << " ";        // (2)
    auto chanLambda = [](int x) { return x % 2 == 0; };                   // (3)
    std::cout << std::count_if(v.begin(), v.end(), chanLambda) << " ";
    bool (*conTro)(int) = chanLambda;                                     // (4)
    std::cout << conTro(5) << "\n";

    int nguong = 3;
    std::function<bool(int)> f = [nguong](int x) { return x > nguong; };  // (5)
    std::cout << f(4) << f(2) << "\n";
    f = laChan;                                                           // (6)
    std::cout << f(4) << f(5) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Hàm thường `laChan`; tên hàm đưa thẳng cho `count_if` ở (2) |
| (3) | Lambda không bắt, cất vào `auto` |
| (4) | Lambda không bắt đổi được thành con trỏ hàm; `conTro(5)` gọi nó, ra `0` |
| (5) | `std::function<bool(int)>` (trong `<functional>`) là cái hộp chứa **bất kỳ thứ gọi được** nhận `int` trả `bool`, kể cả lambda có bắt. In `10`: `f(4)` đúng (1), `f(2)` sai (0) |
| (6) | Cùng hộp đó gán lại thành hàm `laChan`: `laChan(4)` đúng (1), `laChan(5)` sai (0), cũng in `10` |

**Kết quả khi chạy:**

```text
3 3 0
10
10
```

Thử đổi lambda ở (4) thành `[nguong](int x) {...}` rồi gán vào con trỏ hàm: mình đã chạy, g++ báo lỗi `cannot convert '...<lambda(int)>' to 'bool (*)(int)'`. `std::function` cần khi phải **cất** thứ gọi được với một kiểu cố định (thành viên của struct, danh sách callback).

Gọi qua nó thường chậm hơn gọi lambda trực tiếp, nên chỗ chỉ truyền vào thuật toán thì cứ dùng lambda hoặc `auto`.

**Bẫy: lambda sống lâu hơn biến nó tham chiếu.** `[&]` và `[&x]` chỉ cầm tham chiếu ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)). Truyền thẳng vào `sort`, `for_each`... thì an toàn, vì thuật toán dùng xong lambda ngay trong lời gọi, lúc biến còn sống. Nguy hiểm khi lambda **bị cất hay trả ra** rồi gọi sau khi biến đã chết:

```cpp
// bo-qua-kiem-tra
std::function<int()> taoDem() {
    int n = 5;
    return [&n] { return n; };   // lambda giữ tham chiếu tới n, mà n chết khi hàm kết thúc
}
// auto f = taoDem();  f() đọc n đã chết: hành vi không xác định
```

Đoạn này là hành vi không xác định, mình không chạy và không nói nó in gì. Sửa: bắt bản chép `[n]`.

### 5. Remove-erase: xóa theo điều kiện

Bài 19 để lại một câu hỏi: xóa **nhiều** phần tử của vector bằng `erase` từng cái thì mỗi lần dồn các phần tử sau, tốn O(n) mỗi lần. `std::remove` làm cả việc đó trong **một lượt**. Nhưng nó chỉ có cặp iterator, không có container, nên **không thể** làm vector ngắn lại.

Việc nó làm: dồn các phần tử được **giữ** lên đầu, và trả về iterator tới chỗ ngay sau phần tử giữ cuối cùng. Phần phía sau ở trạng thái "dùng được nhưng không biết giá trị gì". Việc xóa thật sự do `erase` của container làm: `v.erase(std::remove(...), v.end())` cắt đoạn đuôi đó.

Ý tưởng (không phải mã thư viện) trên `{1, 2, 2, 3, 2, 4}` với `remove(..., 2)`: một vị trí ghi `w` bắt đầu ở 0; phần tử nào khác 2 thì chép vào `v[w]` rồi `w` tăng.

| Phần tử đang xét | Làm gì | Phần giữ lại |
|---|---|---|
| 1 | giữ, `w` thành 1 | `1` |
| 2, 2 | bỏ qua cả hai | `1` |
| 3 | giữ, chép vào chỗ `w = 1`, `w` thành 2 | `1 3` |
| 2 | bỏ qua | `1 3` |
| 4 | giữ, `w` thành 3: đó là iterator trả về | `1 3 4` |

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

void in(const char* nhan, const std::vector<int>& v) {
    std::cout << nhan << " (size " << v.size() << "):";
    for (int x : v) std::cout << " " << x;
    std::cout << "\n";
}

int main() {
    std::vector<int> v = {1, 2, 2, 3, 2, 4};
    auto moiCuoi = std::remove(v.begin(), v.end(), 2);            // (1)
    std::cout << "phan giu lai dai " << moiCuoi - v.begin() << ", size van la " << v.size() << "\n";
    std::cout << "giu lai:";
    for (auto it = v.begin(); it != moiCuoi; ++it) std::cout << " " << *it;   // (2)
    std::cout << "\n";
    v.erase(moiCuoi, v.end());                                    // (3)
    in("sau erase", v);

    std::vector<int> w = {5, 12, 7, 20, 3, 15};
    w.erase(std::remove_if(w.begin(), w.end(), [](int x) { return x >= 10; }), w.end());   // (4)
    in("bo >= 10", w);
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `remove` dồn `1 3 4` lên đầu, trả iterator ở vị trí 3; `size()` **vẫn là 6** |
| (2) | Chỉ duyệt tới `moiCuoi`: đoạn sau đó không đọc (giá trị không rõ) |
| (3) | `erase(moiCuoi, v.end())` cắt đoạn đuôi: size về 3 |
| (4) | `remove_if` nhận vị từ thay giá trị: bỏ mọi số `>= 10`, rồi `erase` cùng dòng |

**Kết quả khi chạy:**

```text
phan giu lai dai 3, size van la 6
giu lai: 1 3 4
sau erase (size 3): 1 3 4
bo >= 10 (size 3): 5 7 3
```

Toàn bộ chỉ tốn O(n) (một lượt), thay cho nhiều lần `erase` O(n) của Bài 19. `list` thì có sẵn `l.remove(x)` và `l.remove_if(...)` **tự xóa luôn** (Bài 17); C++20 còn có `std::erase_if(v, vị_từ)` gói cả hai bước. `std::unique` cùng khuôn (`erase(unique(...), end)`) nhưng chỉ gộp các phần tử **liền kề** bằng nhau, nên phải sắp xếp trước.

!!! info "Bạn biết Go?"
    Go xóa theo điều kiện bằng vòng lặp ghi đè `out := s[:0]; for _, x := range s { if giữ(x) { out = append(out, x) } }`: cùng ý "dồn phần giữ lại lên đầu rồi cắt". Từ Go 1.21 có `slices.DeleteFunc` làm trọn gói, ứng với remove_if cộng erase.

## 💻 Ví dụ code

Chương trình dưới ghép các món vừa học trên một danh sách học sinh: bỏ người dưới 5 điểm, xếp theo điểm giảm dần, tính trung bình, đếm người giỏi và tìm hạng của một tên.

```cpp
#include <algorithm>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

struct HocSinh {
    std::string ten;
    int diem;
};

int main() {
    std::vector<HocSinh> lop = {{"Lan", 7}, {"An", 4}, {"Binh", 9}, {"Cuong", 3}, {"Dung", 8}};
    lop.erase(std::remove_if(lop.begin(), lop.end(),
                             [](const HocSinh& h) { return h.diem < 5; }),
              lop.end());                                                 // (1)
    std::sort(lop.begin(), lop.end(),
              [](const HocSinh& a, const HocSinh& b) { return a.diem > b.diem; });   // (2)
    for (const HocSinh& h : lop) std::cout << h.ten << ":" << h.diem << " ";
    std::cout << "\n";

    int tong = std::accumulate(lop.begin(), lop.end(), 0,
                               [](int acc, const HocSinh& h) { return acc + h.diem; });   // (3)
    std::cout << "trung binh " << static_cast<double>(tong) / lop.size() << "\n";

    auto gioi = std::count_if(lop.begin(), lop.end(),
                              [](const HocSinh& h) { return h.diem >= 8; });   // (4)
    auto it = std::find_if(lop.begin(), lop.end(),
                           [](const HocSinh& h) { return h.ten == "Lan"; });   // (5)
    std::cout << "gioi " << gioi << ", Lan hang " << (it - lop.begin()) + 1 << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | remove-erase với vị từ: `An` (4) và `Cuong` (3) bị bỏ, còn `Lan`, `Binh`, `Dung` |
| (2) | Sắp theo điểm giảm dần: `Binh` 9, `Dung` 8, `Lan` 7 |
| (3) | `accumulate` với lambda cộng `h.diem` vào bộ cộng `int` (giá trị đầu `0`): 24 |
| (4) | `count_if` đếm điểm `>= 8`: `Binh`, `Dung` |
| (5) | `find_if` tìm theo tên; `it - lop.begin()` là vị trí 2, cộng 1 thành hạng 3 |

**Kết quả khi chạy:**

```text
Binh:9 Dung:8 Lan:7 
trung binh 8
gioi 2, Lan hang 3
```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Remove-erase idiom là gì và vì sao cần cả hai bước?"
    `std::remove`/`remove_if` chỉ nhận cặp iterator nên không đổi được `size()` của container: nó dồn các phần tử được giữ lên đầu và trả iterator tới chỗ ngay sau phần tử giữ cuối. Bước hai là `container.erase(iterator_đó, container.end())` mới cắt đuôi. Viết gọn: `v.erase(std::remove_if(v.begin(), v.end(), vi_tu), v.end());` chạy O(n), tốt hơn gọi `erase` từng phần tử; C++20 có `std::erase_if`.

??? question "Comparator của `std::sort` phải thỏa điều kiện gì?"
    Phải là thứ tự chặt (strict weak ordering): `comp(a, a)` là `false`, `comp(a, b)` đúng thì `comp(b, a)` sai, và bắc cầu. Cứ dùng `<` hoặc `>`; dùng `<=` là vi phạm và là hành vi không xác định. `sort` cần iterator truy cập ngẫu nhiên và không ổn định (`stable_sort` thì ổn định); `list` dùng `l.sort()`.

??? question "Lambda capture `[=]` và `[&]` khác nhau thế nào? Khi nào nguy hiểm?"
    `[=]` chép các biến dùng tới lúc tạo lambda; `[&]` giữ tham chiếu tới biến gốc. Truyền lambda `[&]` thẳng vào thuật toán thì an toàn vì dùng xong ngay. Nguy hiểm khi lambda được cất hay trả ra và sống lâu hơn biến gốc: tham chiếu treo, hành vi không xác định. Khác Go: closure Go luôn bắt theo tham chiếu và bộ gom rác giữ biến sống; C++ không có gì giữ giùm.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `remove` mà quên `erase`"
    Vector vẫn nguyên `size()` và đuôi chứa giá trị không rõ (mục 5). Luôn viết `v.erase(std::remove(...), v.end())`.

!!! warning "Lỗi 2: Giá trị đầu của `accumulate` sai kiểu"
    `accumulate(d.begin(), d.end(), 0)` trên vector `double` cộng bằng `int` và ra `0` ở ví dụ mục 3. Viết `0.0`.

!!! warning "Lỗi 3: Comparator dùng `<=`"
    `<=` vi phạm thứ tự chặt (hành vi không xác định). Dùng `<` hoặc `>`.

!!! warning "Lỗi 4: `*std::find(...)` mà không kiểm `!= end()`"
    Không tìm thấy thì `find` trả `end()`, và `*` lên `end()` là hành vi không xác định.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="20" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** `std::find(v.begin(), v.end(), x)` không thấy `x` trong vector. Nó trả về gì?

- `v.begin()`, tức là điểm bắt đầu của đoạn
- `v.end()`, nên phải so với nó trước khi `*`
- `nullptr`, vì không có phần tử nào cả
- `-1`, giống hàm tìm chỉ số trong nhiều ngôn ngữ

<p class="giai-thich" markdown>`find` trả iterator, và "không thấy" được biểu diễn bằng chính `end` bạn đưa vào, nên phải kiểm `it != v.end()` trước khi dùng `*it`. Nó không trả `begin()` vì đó là vị trí hợp lệ của phần tử đầu. `nullptr` và `-1` không phải iterator; nhầm lẫn này đến từ các ngôn ngữ trả chỉ số hay con trỏ rỗng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn code sau. Nó in ra gì?

```text
std::vector<int> v = {1, 2, 2, 3, 2, 4};
v.erase(std::remove(v.begin(), v.end(), 2), v.end());
std::cout << v.size();
```

- `6`, vì `remove` đã xóa nhưng `erase` không đổi gì
- `5`, vì chỉ mỗi số `2` đầu tiên bị xóa
- `3`, vì ba số `2` bị cắt
- `4`, vì `remove` bỏ hai số `2` liền nhau

<p class="giai-thich" markdown>`remove` dồn `1 3 4` lên đầu và trả chỗ ngay sau số `4`; `erase` cắt đoạn đuôi đó, nên còn đúng 3 phần tử. Nó xóa **mọi** số 2 chứ không chỉ số đầu tiên hay một cặp liền nhau. Con số `6` chỉ xuất hiện nếu bạn bỏ lời gọi `erase`, vì khi đó `size()` chưa bao giờ đổi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn code sau. Nó in ra gì?

```text
std::vector<int> v = {5, 12, 7, 20};
auto e = std::remove_if(v.begin(), v.end(), [](int x) { return x >= 10; });
std::cout << v.size() << " " << (e - v.begin());
```

- `4 2`, vì `size()` chưa đổi còn `e` ở sau `5 7`
- `2 2`, vì `remove_if` đã cắt vector còn hai phần tử
- `4 4`, vì `e` luôn bằng `v.end()` khi chưa `erase`
- `2 4`, vì `e` là số phần tử đã bị bỏ đi

<p class="giai-thich" markdown>Không gọi `erase` nên `size()` vẫn là 4. Phần giữ lại là `5 7` (hai phần tử), nên `e` ở vị trí 2. `remove_if` chỉ dồn phần tử chứ không cắt, nên `size` không thể thành 2, và `e` bằng `v.end()` chỉ khi không có gì bị bỏ. Hiệu `e - v.begin()` đếm phần tử **giữ lại**, không phải số bị bỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Comparator truyền cho `std::sort` cần thỏa điều kiện nào?

- Trả `true` cả khi hai phần tử bằng nhau, để chúng giữ nguyên chỗ cũ
- Trả `-1`, `0` hoặc `1` như hàm so sánh của nhiều ngôn ngữ
- Trả vị trí mới của phần tử `a` trong dãy sau khi xếp
- Trả `true` nếu `a` đứng trước `b`; bằng nhau thì `false`

<p class="giai-thich" markdown>Comparator là câu hỏi "`a` có phải đứng trước `b` không", nên hai phần tử bằng nhau phải cho `false` (đó là điều mà `<` làm, còn `<=` thì không). Trả `true` khi bằng nhau vi phạm thứ tự chặt và là hành vi không xác định. Kiểu trả `-1/0/1` là của `slices.SortFunc` bên Go, còn ở C++ kiểu trả về là `bool`; và vị trí mới là việc của `sort`, không phải của comparator.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn code sau. Chuyện gì xảy ra khi biên dịch?

```text
int dem = 0;
std::vector<int> v = {1, 2, 3};
std::for_each(v.begin(), v.end(), [dem](int x) { dem += x; });
```

- Chạy được, và `dem` thành 6 khi vòng lặp kết thúc
- Lỗi biên dịch, vì bản chép `dem` trong lambda là hằng
- Chạy được, nhưng `dem` ở ngoài vẫn bằng 0 vì chỉ sửa bản chép
- Biên dịch được, nhưng là hành vi không xác định khi chạy

<p class="giai-thich" markdown>`[dem]` đưa vào lambda một bản chép chỉ đọc, nên `dem += x` bị trình biên dịch chặn bằng lỗi "read-only". Dù sửa được bản chép (cần `mutable`), `dem` bên ngoài vẫn là 0. Muốn cộng vào biến ngoài, viết `[&dem]`. Vì đây là lỗi ngay lúc biên dịch nên không có hành vi không xác định nào ở lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Đọc đoạn code sau. Nó in ra gì?

```text
std::vector<double> d = {0.5, 0.25, 0.25};
std::cout << std::accumulate(d.begin(), d.end(), 0);
```

- `1`, vì ba số cộng lại đúng bằng 1 như phép toán thường
- `1.0`, vì kết quả cộng từ `double` giữ kiểu `double`
- `0`, vì giá trị đầu là `int`
- `0.5`, vì `accumulate` chỉ cộng phần tử đầu tiên

<p class="giai-thich" markdown>Kiểu của giá trị đầu quyết định kiểu bộ cộng: `0` là `int` nên mỗi lần cộng phần thập phân bị cắt và ra `0`. Viết `0.0` mới được `1`. Việc "giữ kiểu `double`" là suy đoán sai: `accumulate` không lấy kiểu từ các phần tử. Phép cộng có chạy qua cả ba phần tử, nên `0.5` cũng sai.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Vì sao `std::sort(l.begin(), l.end())` với `std::list<int> l` không biên dịch được?

- `sort` cần iterator truy cập ngẫu nhiên, mà `list` chỉ nhích từng bước
- `list` không lưu số nguyên liên tiếp nên không có thứ tự
- `sort` chỉ nhận mảng thường và `vector`, không nhận container khác
- Muốn sort `list` phải bật cờ biên dịch riêng cho `list`

<p class="giai-thich" markdown>`sort` cần iterator truy cập ngẫu nhiên: nhảy tới phần tử bất kỳ và trừ hai iterator cho nhau, việc mà iterator của `list` không làm được (g++ báo thiếu `operator-`). Vì vậy `list` có hàm riêng `l.sort()`. Việc `list` không có thứ tự là sai: nó có thứ tự chèn và sắp xếp được. Cũng không phải `sort` chỉ nhận hai loại container, vì `deque`, `array` và mảng thường đều dùng được; không có cờ biên dịch nào liên quan.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 8.** Trường hợp nào dùng lambda `[&]` hoặc `[&x]` là nguy hiểm?

- Truyền thẳng vào `std::for_each` để cộng dồn vào biến cục bộ
- Truyền vào `std::sort` để so sánh theo một biến ở ngoài
- Dùng trong `std::count_if` rồi hủy ngay sau lời gọi
- Trả lambda ra khỏi hàm rồi gọi khi biến cục bộ đã hết đời

<p class="giai-thich" markdown>Lambda `[&]` chỉ cầm tham chiếu, nên nếu nó sống lâu hơn biến gốc (trả ra khỏi hàm, cất vào nơi dùng sau) thì tham chiếu treo và dùng nó là hành vi không xác định. Ba cách còn lại dùng xong lambda ngay trong lời gọi thuật toán, lúc biến còn sống, nên an toàn. Cách sửa cho trường hợp nguy hiểm là bắt bản chép bằng `[x]`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Thuật toán STL nhận cặp iterator `[begin, end)` (nửa mở), không nhận container; `find`/`min_element` trả iterator và "không thấy" là `end`, nên phải so với `end` trước khi `*`.
2. `sort` mặc định dùng `<`, thêm comparator lambda "a đứng trước b?" (thứ tự chặt: dùng `<`/`>`, không dùng `<=`); cần iterator truy cập ngẫu nhiên và không ổn định, còn `list` dùng `l.sort()`.
3. Lambda là đối số của `find_if`, `count_if`, `any_of`/`all_of`, `transform`, `for_each`, `accumulate`; chỉ đọc biến ngoài thì `[x]`, cần ghi ra ngoài thì `[&x]`; giá trị đầu của `accumulate` quyết định kiểu kết quả.
4. Lambda không bắt đổi được thành con trỏ hàm, `std::function` chứa mọi thứ gọi được cùng chữ ký (thường chậm hơn); lambda `[&]` sống lâu hơn biến là tham chiếu treo; closure Go bắt theo tham chiếu mặc định còn C++ phải khai báo.
5. Xóa theo điều kiện bằng `v.erase(std::remove_if(v.begin(), v.end(), vi_tu), v.end())`: `remove` chỉ dồn phần giữ lại lên đầu nên `size()` chưa đổi, `unique` theo cùng khuôn (sau khi sắp xếp), và `list` có `remove` tự xóa.
