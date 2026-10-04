# Bài 23 — Thuật toán hay hỏi ở phỏng vấn

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được **tìm kiếm nhị phân** không lệch biên (kể cả dãy rỗng), biết vì sao tính giữa bằng `lo + (hi - lo) / 2` chứ không phải `(lo + hi) / 2`, và nối nó với `std::binary_search`/`std::lower_bound` (Go: `sort.Search`, `slices.BinarySearch`).
    - Dùng **hai con trỏ** (tìm cặp có tổng `k` trên dãy đã sắp) và `unordered_map` (bài "two sum" trên dãy chưa sắp), nói được mỗi cách tốn thời gian và bộ nhớ thế nào.
    - Phân biệt **sắp xếp chèn** O(n²) với **sắp xếp trộn** O(n log n) bằng số lần so sánh đã đo, hiểu quick sort và `std::sort` ở mức khái niệm.
    - Thấy vì sao Fibonacci đệ quy ngây thơ bùng nổ, rồi sửa bằng **ghi nhớ (memoization)** và **quy hoạch động** (bảng), lập và tính tay được bảng cho bài đổi tiền rút gọn.
    - Có quy trình giải đề ở bảng trắng: làm rõ đề, ví dụ nhỏ, nói to cách nghĩ, nêu độ phức tạp, kiểm tra biên.

**Bạn cần biết trước:** [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (`long long`, `static_cast`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến toàn cục, khung hàm), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (tham chiếu `int&` để trả kết quả ra), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (tràn số có dấu là UB, ASan/UBSan), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`%`), [Bài 16](16-vector.md) (`vector`, `size() - 1` khi rỗng), [Bài 18](18-map-set-unordered.md) (`unordered_map`, `find`), [Bài 19](19-iterator-vo-hieu.md) (iterator), [Bài 20](20-algorithm-lambda.md) (`sort`), [Bài 21](21-big-o-cau-truc-du-lieu.md) (Big-O, `&&` là "và" logic), [Bài 22](22-bst-bang-bam-heap.md) (đệ quy tại chỗ).

!!! note "Phạm vi bài này"
    Mức nhập môn: mỗi thuật toán có một bản nhỏ chạy được, để bạn hiểu ý tưởng và nói trôi chảy. Quick sort chỉ ở mức khái niệm; đồ thị, quy hoạch động nhiều chiều và chứng minh đúng nằm ngoài bài.

## 🧠 Câu chuyện mở đầu

Quay lại thư viện của [Bài 21](21-big-o-cau-truc-du-lieu.md). **Tìm nhị phân** là mở giữa kệ đã xếp rồi bỏ một nửa. **Hai con trỏ** là hai người đứng hai đầu kệ rồi cùng đi vào giữa. **Sắp xếp** là xếp sách lên kệ: nhét từng cuốn vào đúng chỗ thì chậm, còn chia kệ làm đôi, xếp từng nửa rồi trộn lại thì nhanh. Đệ quy và quy hoạch động có hình ảnh riêng ở mục 4 và 5.

!!! info "Chỗ nào hình ảnh này không còn đúng?"
    Người mở giữa kệ phải đi tới tận chỗ đó, còn máy lấy `v[mid]` trong một bước vì `vector` nằm liền nhau. Đó là lý do tìm nhị phân cần lấy `v[i]` trong một bước (truy cập ngẫu nhiên); trên danh sách liên kết ([Bài 21](21-big-o-cau-truc-du-lieu.md)) muốn tới "giữa" vẫn phải đi từng nút.

!!! warning "Hay nhầm: 'con trỏ' trong 'hai con trỏ'"
    Ở đây "con trỏ" chỉ là hai **chỉ số** (hoặc iterator) cùng chạy trên dãy, không phải con trỏ `int*` của [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md). Tên gọi chỉ là thói quen của dân thuật toán.

## 📖 Giải thích

### 1. Tìm kiếm nhị phân

Điều kiện: dãy đã **sắp tăng dần** và truy cập `v[i]` nhanh. Ta giữ một đoạn `[lo, hi]` "còn có thể chứa `x`", so `x` với phần tử giữa, rồi bỏ nửa không thể chứa. Mỗi vòng đoạn nhỏ đi một nửa, nên sau cỡ log n vòng là hết: **O(log n)** thời gian, O(1) bộ nhớ.

Một cú pháp cần nhắc lại: `static_cast<int>(v.size()) - 1` đổi `size()` (kiểu không dấu) sang `int` **trước** khi trừ, để dãy rỗng cho `-1` thay vì số khổng lồ ([Bài 16](16-vector.md)).

Rồi hai hàm thư viện mới trong `<algorithm>`, đều đòi dãy đã sắp:

- `std::binary_search(đầu, cuối, x)` trả `true`/`false`.
- `std::lower_bound(đầu, cuối, x)` trả iterator tới phần tử **đầu tiên không nhỏ hơn** `x` (hoặc `end()` nếu không có); `it - v.begin()` đổi iterator ra chỉ số.

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

// Tìm x trong dãy đã sắp tăng dần; trả chỉ số, hoặc -1 nếu không có.
int timNhiPhan(const std::vector<int>& v, int x) {
    int lo = 0;                                  // (1) đầu đoạn còn nghi ngờ
    int hi = static_cast<int>(v.size()) - 1;     // (2) cuối đoạn; dãy rỗng thì hi = -1
    while (lo <= hi) {                           // (3) còn ít nhất một phần tử
        int mid = lo + (hi - lo) / 2;            // (4) điểm giữa, không bị tràn số
        if (v[mid] == x) return mid;             // (5) trúng
        if (v[mid] < x) lo = mid + 1;            // (6) x nằm bên phải: bỏ nửa trái
        else hi = mid - 1;                       // (7) x nằm bên trái: bỏ nửa phải
    }
    return -1;                                   // (8) đoạn rỗng: không có
}

int main() {
    std::vector<int> v = {1, 3, 5, 7, 9, 11};
    std::vector<int> rong;                       // vector rỗng
    std::cout << "tim 7: " << timNhiPhan(v, 7) << "\n";
    std::cout << "tim 4: " << timNhiPhan(v, 4) << "\n";
    std::cout << "tim 1: " << timNhiPhan(v, 1) << "\n";
    std::cout << "day rong, tim 1: " << timNhiPhan(rong, 1) << "\n";

    std::cout << "binary_search 9: " << std::binary_search(v.begin(), v.end(), 9) << "\n";
    auto it = std::lower_bound(v.begin(), v.end(), 6);       // (9) biết trước có 7 nên `*it` an toàn
    std::cout << "lower_bound 6 -> chi so " << (it - v.begin()) << ", gia tri " << *it << "\n";
    auto het = std::lower_bound(v.begin(), v.end(), 100);    // (10)
    std::cout << "lower_bound 100 la end()? " << (het == v.end()) << "\n";
    return 0;
}
```

**Chạy từng dòng** (tìm `7` trong `{1, 3, 5, 7, 9, 11}`)

| Dòng | Chuyện gì xảy ra | Đoạn còn nghi ngờ |
|---|---|---|
| (1)-(2) | `lo = 0`, `hi = 5` | `[1 3 5 7 9 11]` |
| (4) vòng 1 | `mid = 0 + (5 - 0) / 2 = 2`, `v[2] = 5` | `[1 3 5 7 9 11]` |
| (6) | `5 < 7` nên `lo = 3`, bỏ nửa trái | `[7 9 11]` |
| (4) vòng 2 | `mid = 3 + (5 - 3) / 2 = 4`, `v[4] = 9` | `[7 9 11]` |
| (7) | `9 > 7` nên `hi = 3`, bỏ nửa phải | `[7]` |
| (4)-(5) vòng 3 | `mid = 3`, `v[3] = 7` trúng, trả `3` | |
| (8) | Tìm `4` thì `lo` vượt `hi`, đoạn rỗng, trả `-1` | `[]` |
| (9)-(10) | `6` không có, `lower_bound` trả phần tử đầu tiên `>= 6` là `7`; `100` thì trả `end()` | |

**Kết quả khi chạy:**

```text
tim 7: 3
tim 4: -1
tim 1: 0
day rong, tim 1: -1
binary_search 9: 1
lower_bound 6 -> chi so 3, gia tri 7
lower_bound 100 la end()? 1
```

Dãy rỗng cho `hi = -1` nên `lo <= hi` sai ngay và trả `-1`, không cần `if` riêng. Dùng `<=` vì đoạn `[lo, hi]` gồm cả hai đầu: khi `lo == hi` vẫn còn một phần tử chưa xem. Với `lower_bound` luôn kiểm `it != v.end()` trước khi `*it`.

**Bẫy tràn số.** Cách viết quen thuộc `(lo + hi) / 2` sai khi `lo + hi` vượt giá trị lớn nhất của `int` (khoảng 2,1 tỉ): số có dấu tràn là hành vi không xác định ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). `hi - lo` thì luôn nằm trong khoảng an toàn (vì `0 <= lo <= hi`), nên `lo + (hi - lo) / 2` đúng với mọi dãy.

Mình đã chạy một khối nhỏ với `lo = 2000000000`, `hi = 2100000000` (kiểu `int`): `(lo + hi) / 2` in `-97483648` (số âm vô lý), còn `lo + (hi - lo) / 2` in `2050000000`. Với `-fsanitize=undefined` UBSan báo `signed integer overflow: 2000000000 + 2100000000 cannot be represented in type 'int'`. Số âm cụ thể là kết quả của một lần UB trên máy này; đừng dựa vào nó.

**Thử thay đổi: ở dòng (6) đổi `lo = mid + 1` thành `lo = mid`.** Mình đã chạy với `timeout 3`: chương trình không bao giờ dừng (bị dừng, mã 124). Với `{1, 3, 5, 7, 9, 11}` tìm `4`, đoạn rơi về `lo = 0`, `hi = 1`, `mid = 0`, `v[0] < 4` nên `lo = mid = 0` mãi: đoạn không còn nhỏ đi. Mỗi vòng **phải loại ít nhất phần tử `mid`**, vì vậy `+ 1` và `- 1` là bắt buộc.

!!! info "Bạn biết Go?"
    Go có `sort.Search(n, f)`: trả chỉ số **nhỏ nhất** `i` trong `[0, n)` mà `f(i)` đúng (trả `n` nếu không có), đúng tinh thần `lower_bound`, và `sort.SearchInts`. Từ Go 1.21, `slices.BinarySearch(s, x)` trả hai giá trị: vị trí và `found` (`true` nếu có). Mình đã chạy trên `{1,3,5,7,9,11}`: tìm `7` ra `3 true`, tìm `4` ra `2 false` (vị trí `4` sẽ được chèn vào), `sort.Search` với `>= 6` ra chỉ số `3`. Mã nguồn `sort.Search` của Go cố ý viết `int(uint(i+j) >> 1)` với comment "avoid overflow", cùng bẫy trên.

### 2. Hai con trỏ và bài "two sum"

**Bài toán:** cho dãy số và số `k`, tìm hai phần tử (hai chỉ số khác nhau) có tổng bằng `k`. Có ba cách:

| Cách | Điều kiện | Thời gian | Bộ nhớ |
|---|---|---|---|
| Vét cạn (brute force, thử mọi cặp) | không | O(n²) | O(1) |
| Hai con trỏ | dãy đã sắp (chưa sắp thì sắp trước, tổng O(n log n)) | O(n) | O(1) |
| `unordered_map` | không | O(n) trung bình | O(n) |

Ý của hai con trỏ: `i` ở đầu (số nhỏ nhất), `j` ở cuối (số lớn nhất). Tổng nhỏ quá thì chỉ có cách tăng `i` (đổi sang số lớn hơn); tổng lớn quá thì chỉ có cách giảm `j`. Mỗi bước loại hẳn một phần tử khỏi vùng cần xét nên chỉ tối đa `n` bước. Cùng khuôn đó có đảo chuỗi tại chỗ: đổi chỗ `s[i]` với `s[j]` rồi `++i`, `--j` tới khi `i >= j`.

Hai cú pháp ngắn trong listing: `return {a, b}` dựng ngay một vector hai phần tử để trả về, `return {}` dựng vector rỗng; và `{5}` truyền thẳng vào hàm là vector một phần tử.

Với `unordered_map` ([Bài 18](18-map-set-unordered.md)): duyệt từng `v[i]`, hỏi "số bù `k - v[i]` đã gặp ở các vị trí trước chưa?". Có thì xong, chưa thì ghi `v[i]` vào map. Mỗi `find` và mỗi lần ghi là O(1) trung bình nên cả bài O(n).

```cpp
#include <iostream>
#include <unordered_map>
#include <vector>

// Dãy ĐÃ SẮP tăng dần: tìm hai chỉ số khác nhau có tổng bằng k.
bool timCap(const std::vector<int>& v, int k, int& i, int& j) {
    i = 0;                                       // (1) con trỏ trái: đầu dãy
    j = static_cast<int>(v.size()) - 1;          // (2) con trỏ phải: cuối dãy
    while (i < j) {                              // (3) còn ít nhất hai phần tử
        int tong = v[i] + v[j];
        if (tong == k) return true;              // (4) thấy rồi
        if (tong < k) ++i;                       // (5) tổng nhỏ quá: cần số lớn hơn, nhích trái sang phải
        else --j;                                // (6) tổng lớn quá: nhích phải sang trái
    }
    return false;                                // (7) hai con trỏ gặp nhau: không có cặp
}

// Dãy BẤT KỲ (chưa sắp): trả hai chỉ số có tổng k, hoặc vector rỗng nếu không có.
std::vector<int> twoSum(const std::vector<int>& v, int k) {
    std::unordered_map<int, int> daThay;               // (8) giá trị -> chỉ số đã duyệt
    for (int i = 0; i < static_cast<int>(v.size()); ++i) {
        auto it = daThay.find(k - v[i]);               // (9) số bù đã gặp trước đó chưa?
        if (it != daThay.end()) return {it->second, i};   // (10) có: xong
        daThay[v[i]] = i;                              // (11) chưa: ghi lại số này
    }
    return {};
}

int main() {
    std::vector<int> da = {1, 3, 4, 6, 8, 11};   // đã sắp
    int i = 0, j = 0;
    if (timCap(da, 10, i, j)) std::cout << "hai con tro, k=10: v[" << i << "]+v[" << j << "]\n";
    std::cout << "hai con tro, k=100 co cap? " << timCap(da, 100, i, j) << "\n";
    std::cout << "mot phan tu {5}, k=5 co cap? " << timCap({5}, 5, i, j) << "\n";

    std::vector<int> v = {8, 3, 11, 1, 6, 4};    // chưa sắp
    std::vector<int> kq = twoSum(v, 10);
    std::cout << "two sum, k=10: chi so " << kq[0] << " va " << kq[1] << "\n";
    std::cout << "two sum, k=100 co ket qua? " << !twoSum(v, 100).empty() << "\n";
    return 0;
}
```

**Chạy từng dòng** (`da = {1, 3, 4, 6, 8, 11}`, `k = 10`)

| Dòng | Chuyện gì xảy ra | Hai con trỏ |
|---|---|---|
| (1)-(2) | `i = 0`, `j = 5` | `1 ... 11` |
| (3)-(6) | `1 + 11 = 12 > 10`: giảm `j` | `i=0, j=4` |
| (5) | `1 + 8 = 9 < 10`: tăng `i` | `i=1, j=4` |
| (6) | `3 + 8 = 11 > 10`: giảm `j` | `i=1, j=3` |
| (5) | `3 + 6 = 9 < 10`: tăng `i` | `i=2, j=3` |
| (4) | `4 + 6 = 10`: trả `true` | `v[2]+v[3]` |
| (7) | Với `k = 100`, `i` cứ tăng tới khi gặp `j`; với `{5}`, `i = j = 0` nên vòng không chạy; cả hai trả `false` | |
| (9)-(11) | `twoSum`, `k = 10`: `8`, `3`, `11`, `1`, `6` đều chưa có số bù trong map nên được ghi; tới `4`, số bù `6` có ở chỉ số `4`: trả `{4, 5}` | map `{8,3,11,1,6}` |

**Kết quả khi chạy:**

```text
hai con tro, k=10: v[2]+v[3]
hai con tro, k=100 co cap? 0
mot phan tu {5}, k=5 co cap? 0
two sum, k=10: chi so 4 va 5
two sum, k=100 co ket qua? 0
```

(`std::cout` in `bool` thành `1`/`0`.) Hai bản đều qua các biên: dãy một phần tử (`i < j` sai ngay, không có "cặp với chính nó") và không có đáp án. Lưu ý map ghi `v[i]` **sau** khi tìm, nên một phần tử không ghép với chính nó.

!!! info "Bạn biết Go?"
    Hai con trỏ viết y hệt trong Go với hai biến `i`, `j` và slice. Two sum bằng `map[int]int` cũng cùng khuôn: `if j, ok := seen[k-v]; ok { ... }; seen[v] = i`. Độ phức tạp giống hệt vì `map` của Go là bảng băm ([Bài 22](22-bst-bang-bam-heap.md)).

### 3. Sắp xếp: ý tưởng, không phải thuộc lòng

Ba thuật toán bạn cần nói được, từ chậm đến nhanh. **Sắp xếp chèn** lấy từng phần tử rồi lùi nó về đúng chỗ trong phần đã sắp: mỗi phần tử có thể lùi tới `n` bước nên **O(n²)**; **bubble sort** (đổi chỗ các cặp kề nhau nhiều lượt) cũng O(n²). Chúng đơn giản và đủ tốt cho dãy rất ngắn hoặc gần như đã sắp.

**Sắp xếp trộn (merge sort)** chia dãy làm đôi, sắp từng nửa bằng chính nó (đệ quy), rồi **trộn** hai nửa đã sắp: so hai phần tử đầu, lấy cái nhỏ hơn, lặp lại. Trộn là O(n); có khoảng log n tầng chia nên tổng **O(n log n)** trong **mọi** trường hợp, đổi lại cần O(n) bộ nhớ phụ.

**Quick sort** chọn một phần tử mốc (**pivot**), đẩy các số nhỏ hơn mốc sang trái và lớn hơn sang phải, rồi sắp hai phía bằng đệ quy. Trung bình O(n log n) và sắp ngay trong dãy (không cần bộ nhớ phụ lớn), nhưng chọn mốc xấu liên tục (ví dụ luôn lấy phần tử đầu của dãy đã sắp) thì xấu nhất O(n²).

**`std::sort`** ([Bài 20](20-algorithm-lambda.md); Go `sort.Slice`/`slices.Sort` cũng O(n log n)): chuẩn C++ chỉ đòi **O(n log n)** (từ C++11 là cả khi xấu nhất), không quy định thuật toán. Thư viện thực tế dùng bản **lai**: kết hợp nhiều thuật toán để lấy ưu điểm của từng loại và tránh trường hợp xấu (thường gọi là introsort); chi tiết tùy thư viện nên khi phỏng vấn chỉ cần nói "lai, bảo đảm O(n log n)". Phần 💻 bên dưới đo số lần so sánh của chèn và trộn để thấy khoảng cách.

### 4. Đệ quy nâng cao: giai thừa, Fibonacci và vì sao chậm

[Bài 22](22-bst-bang-bam-heap.md) đã dạy đệ quy với điểm dừng và bước đệ quy (hình ảnh mới: giao việc nhỏ hơn cho một người y hệt mình). **Giai thừa**: `n! = n * (n-1)!`, điểm dừng `0! = 1`. Mỗi lần gọi chỉ sinh **một** lần gọi con nên số bước là n, ổn.

**Fibonacci**: `F(0) = 0`, `F(1) = 1`, `F(n) = F(n-1) + F(n-2)`. Viết thẳng thành đệ quy thì mỗi lần gọi sinh **hai** lần gọi con, và các lần gọi con **tính lại** cùng một giá trị rất nhiều lần: `F(5)` gọi `F(4)` và `F(3)`, mà `F(4)` lại gọi `F(3)` lần nữa. Số lần gọi gần như nhân lên mỗi khi `n` tăng một bước, nên người ta nói gọn **O(2^n)** (chính xác hơn: cỡ 1,6^n; cả hai đều là "mũ").

**Ghi nhớ (memoization)** sửa chỗ đó: dùng một mảng `nho`, tính `F(n)` lần đầu thì ghi vào `nho[n]`, những lần sau đọc luôn. Mỗi `n` chỉ tính một lần nên O(n) thời gian và O(n) bộ nhớ (cộng độ sâu đệ quy).

```cpp
#include <iostream>
#include <vector>

long long soLanGoi = 0;                          // đếm số lần hàm bị gọi

long long giaiThua(int n) {
    if (n <= 1) return 1;                        // (1) điểm dừng
    return n * giaiThua(n - 1);                  // (2) n! = n * (n-1)!
}

long long fibNgayTho(int n) {
    ++soLanGoi;
    if (n < 2) return n;                         // (3) F(0)=0, F(1)=1
    return fibNgayTho(n - 1) + fibNgayTho(n - 2);    // (4) hai nhánh, lặp lại việc cũ
}

long long fibNho(int n, std::vector<long long>& nho) {
    ++soLanGoi;
    if (n < 2) return n;
    if (nho[n] != -1) return nho[n];             // (5) đã tính rồi: lấy luôn
    nho[n] = fibNho(n - 1, nho) + fibNho(n - 2, nho);    // (6) tính lần đầu thì ghi lại
    return nho[n];
}

long long fibBang(int n) {                       // quy hoạch động từ dưới lên (mục 5)
    if (n < 2) return n;
    std::vector<long long> f(n + 1);
    f[0] = 0;
    f[1] = 1;
    for (int i = 2; i <= n; ++i) f[i] = f[i - 1] + f[i - 2];   // (7)
    return f[n];
}

int main() {
    std::cout << "5! = " << giaiThua(5) << ", 0! = " << giaiThua(0) << "\n";
    std::vector<int> cacN = {10, 20, 30};
    for (int n : cacN) {
        soLanGoi = 0;
        long long kq = fibNgayTho(n);
        std::cout << "ngay tho  F(" << n << ") = " << kq << ", " << soLanGoi << " lan goi\n";
    }
    soLanGoi = 0;
    std::vector<long long> nho(51, -1);
    std::cout << "ghi nho   F(50) = " << fibNho(50, nho) << ", " << soLanGoi << " lan goi\n";
    std::cout << "bang      F(50) = " << fibBang(50) << "\n";
    std::cout << "bang      F(90) = " << fibBang(90) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (1)-(2) | `giaiThua(5)` chồng 5 khung (`5*4*3*2*1`) rồi gỡ ra `120`; `giaiThua(0)` chạm điểm dừng ngay | một nhánh |
| (3)-(4) | `fibNgayTho(n)` gọi hai nhánh, mỗi nhánh lại gọi hai nhánh; `soLanGoi` đếm tất cả | `F(30)` gọi hơn 2,6 triệu lần |
| (5) | `fibNho`: nếu `nho[n]` khác `-1` (đã tính) thì trả luôn, không gọi tiếp | cắt nhánh |
| (6) | Lần đầu gặp `n` thì tính và ghi vào `nho[n]` | mỗi `n` đúng một lần |
| (7) | `fibBang`: chỉ một vòng `for`, mỗi ô bằng tổng hai ô liền trước | O(n), không đệ quy |

**Kết quả khi chạy:**

```text
5! = 120, 0! = 1
ngay tho  F(10) = 55, 177 lan goi
ngay tho  F(20) = 6765, 21891 lan goi
ngay tho  F(30) = 832040, 2692537 lan goi
ghi nho   F(50) = 12586269025, 99 lan goi
bang      F(50) = 12586269025
bang      F(90) = 2880067194370816120
```

Mỗi lần `n` tăng 10, số lần gọi nhân lên hơn 100 lần (177, rồi 21891, rồi 2692537); còn bản ghi nhớ tính `F(50)` chỉ với 99 lần gọi (khoảng `2n`). `F(50)` đã vượt giới hạn `int` nên dùng `long long`; `F(93)` còn vượt cả `long long`, và giai thừa tràn sớm hơn (`21!` đã vượt `long long`): đây là biên đáng nói khi phỏng vấn.

**Thử thay đổi: gọi `fibNgayTho(40)`.** Mình đã chạy riêng: nó gọi 331160281 lần và mất khoảng 1,3 giây trên máy mình khi biên dịch không bật tối ưu (`-O0`, như lệnh của khóa; số giây khác nhau theo máy và bật tối ưu thì ngắn hơn nhiều), trong khi `fibBang(40)` gần như tức thì. Mỗi khi `n` tăng 1, số lần gọi chỉ tăng khoảng 60%, nhưng cộng dồn thành hàng trăm triệu sau vài chục bước.

!!! info "Bạn biết Go?"
    Fibonacci đệ quy ngây thơ trong Go chậm y như vậy, vì thuật toán và số lần gọi giống hệt (`F(30)` cũng 2692537 lần). Go và C++ không tự biến đệ quy ngây thơ thành ghi nhớ (chuẩn không bảo đảm điều đó; trình biên dịch tối ưu có thể làm nhanh hơn một chút, nhưng số lần gọi vẫn theo hàm mũ). Cách sửa cũng giống: `map` hoặc slice làm bảng nhớ, hay vòng `for` từ dưới lên.

### 5. Quy hoạch động nhập môn

**Quy hoạch động (dynamic programming, DP)** giống cuốn sổ ghi chép: bài nào giải rồi thì ghi đáp án, lần sau chỉ việc đọc. Nó áp dụng khi bài toán có hai tính chất: bài lớn được ghép từ **bài con nhỏ hơn**, và các bài con **lặp lại**. Cách làm: giải mỗi bài con **đúng một lần**, ghi đáp án vào bảng, rồi dùng bảng để giải bài lớn. Có hai cách viết: **từ trên xuống** (đệ quy kèm ghi nhớ, như `fibNho`) và **từ dưới lên** (điền bảng bằng vòng lặp từ bài nhỏ nhất, như `fibBang`).

Bốn bước nghĩ: định nghĩa "ô `dp[s]` nghĩa là gì", điểm bắt đầu (`dp[0]`), công thức nối ô này với các ô trước, và đọc đáp án ở ô nào. Với Fibonacci: `dp[i]` là `F(i)`, `dp[0] = 0`, `dp[1] = 1`, `dp[i] = dp[i-1] + dp[i-2]`, đáp án là `dp[n]`. **Leo cầu thang** (mỗi lần bước 1 hoặc 2 bậc, đếm số cách lên bậc `n`) có đúng công thức này với điểm bắt đầu khác một chút: `dp[1] = 1`, `dp[2] = 2`.

Bài **đổi tiền** (ghép đúng số tiền `t` bằng **ít xu nhất**) cũng cùng khuôn: `dp[s]` là số xu ít nhất để ghép `s`, `dp[0] = 0`, và `dp[s]` là **số nhỏ nhất** (`min`) trong các giá trị `dp[s - x] + 1` qua mọi loại xu `x` thỏa `x <= s` (dùng một xu `x`, phần còn lại `s - x` đã có đáp án). Đáp án ở `dp[t]`, thời gian O(t · m) với `m` loại xu.

Tính tay với xu `{1, 3, 4}`, biết `dp[0..3] = 0 1 2 1`:

| Ô | Thử từng xu | Lấy nhỏ nhất |
|---|---|---|
| `dp[4]` | xu 1: `dp[3] + 1 = 2`; xu 3: `dp[1] + 1 = 2`; xu 4: `dp[0] + 1 = 1` | 1 |
| `dp[5]` | xu 1: `dp[4] + 1 = 2`; xu 3: `dp[2] + 1 = 3`; xu 4: `dp[1] + 1 = 2` | 2 |
| `dp[6]` | xu 1: `dp[5] + 1 = 3`; xu 3: `dp[3] + 1 = 2`; xu 4: `dp[2] + 1 = 3` | 2 (tức `3 + 3`) |

Cách "luôn lấy xu to nhất còn vừa" (**tham lam**, greedy) nhanh hơn nhưng có thể sai: với tiền `6` nó lấy `4 + 1 + 1` (3 xu), trong khi bảng cho 2 xu.

### 6. Mẹo giải đề ở bảng trắng

Phỏng vấn thuật toán chấm cách nghĩ nhiều hơn đáp án. Một quy trình gọn, dùng được cho mọi đề, minh họa bằng two sum:

| Bước | Làm gì | Ví dụ với two sum |
|---|---|---|
| 1. Làm rõ đề | Hỏi dãy đã sắp chưa, có trùng không, rỗng được không, có số âm không, có nhiều đáp án thì trả cái nào | "Dãy đã sắp chưa? Có đảm bảo có đáp án không?" |
| 2. Ví dụ nhỏ | Tự làm tay một ví dụ, ghi lại các bước | `{8, 3, 11, 1, 6, 4}`, `k = 10` |
| 3. Nói cách vét cạn trước | Cách chậm nhưng đúng, kèm độ phức tạp | Thử mọi cặp: O(n²) |
| 4. Cải tiến, nói to vì sao | Tìm chỗ lặp lại hoặc tính chất chưa dùng | "Lưu số đã gặp vào map: O(n) thời gian, O(n) bộ nhớ" |
| 5. Viết code | Tên biến rõ, từng khối nhỏ | `twoSum` ở mục 2 |
| 6. Kiểm tra biên | Chạy tay với dãy rỗng, một phần tử, trùng nhau, không có đáp án, số rất lớn | `{}`, `{5}`, `{5, 5}` với `k = 10` |
| 7. Nêu phức tạp | Thời gian và bộ nhớ, nhắc đánh đổi | "O(n) và O(n); hai con trỏ cần dãy sắp nhưng chỉ O(1) bộ nhớ" |

Nói to trong lúc nghĩ là chủ ý: người phỏng vấn có thể gợi ý khi bạn kẹt, và họ chỉ chấm được thứ họ nghe thấy. Nếu chưa ra cách tối ưu, đưa cách vét cạn đúng trước rồi cải tiến vẫn tốt hơn ngồi im.

## 💻 Ví dụ code

### Sắp xếp chèn và sắp xếp trộn: đếm số lần so sánh

Hai hàm, mỗi hàm cộng vào biến toàn cục `soSoSanh` ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)) mỗi lần so sánh hai phần tử. Mấy cú pháp mới: `break` thoát khỏi vòng lặp ngay (như Go); `std::vector<int>(đầu, cuối)` dựng một vector mới chép các phần tử của đoạn `[đầu, cuối)`; còn `&&` là "và" logic đã gặp ở [Bài 21](21-big-o-cau-truc-du-lieu.md).

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

long long soSoSanh = 0;                          // đếm số lần so sánh hai phần tử

// Sắp xếp chèn: lấy từng phần tử, lùi nó về đúng chỗ trong phần đã sắp.
void sapChen(std::vector<int>& a) {
    for (int i = 1; i < static_cast<int>(a.size()); ++i) {
        int x = a[i];                            // (1) phần tử cần chèn
        int j = i - 1;
        while (j >= 0) {
            ++soSoSanh;
            if (a[j] <= x) break;                // (2) đã đúng chỗ
            a[j + 1] = a[j];                     // (3) dời phần tử lớn hơn sang phải
            --j;
        }
        a[j + 1] = x;                            // (4) đặt x vào chỗ trống
    }
}

// Sắp xếp trộn: chia đôi, sắp từng nửa, rồi trộn hai nửa đã sắp.
std::vector<int> sapTron(const std::vector<int>& a) {
    if (a.size() <= 1) return a;                 // (5) điểm dừng: rỗng hay một phần tử thì đã sắp
    std::size_t giua = a.size() / 2;
    std::vector<int> trai = sapTron(std::vector<int>(a.begin(), a.begin() + giua));   // (6)
    std::vector<int> phai = sapTron(std::vector<int>(a.begin() + giua, a.end()));
    std::vector<int> kq;
    std::size_t i = 0, j = 0;
    while (i < trai.size() && j < phai.size()) { // (7) lấy phần tử nhỏ hơn từ đầu hai nửa
        ++soSoSanh;
        if (trai[i] <= phai[j]) {
            kq.push_back(trai[i]);
            ++i;
        } else {
            kq.push_back(phai[j]);
            ++j;
        }
    }
    while (i < trai.size()) { kq.push_back(trai[i]); ++i; }   // (8) nửa còn dư đã sắp sẵn: chép nốt
    while (j < phai.size()) { kq.push_back(phai[j]); ++j; }
    return kq;
}

int main() {
    std::vector<int> nho = {5, 2, 9, 1, 5, 6};
    std::vector<int> a = nho;
    sapChen(a);
    std::cout << "sap chen: ";
    for (int x : a) std::cout << x << " ";
    std::cout << "\n";
    std::cout << "sap tron: ";
    for (int x : sapTron(nho)) std::cout << x << " ";
    std::cout << "\n";

    std::vector<int> cacCo = {1000, 2000, 4000};
    for (int n : cacCo) {
        std::vector<int> d;
        for (int i = 0; i < n; ++i) d.push_back((i * 7919 + 13) % 10007);   // dãy "lộn xộn" cố định
        std::vector<int> b = d;
        soSoSanh = 0;
        sapChen(b);
        long long chen = soSoSanh;
        soSoSanh = 0;
        std::vector<int> c = sapTron(d);
        long long tron = soSoSanh;
        std::sort(d.begin(), d.end());
        std::cout << "n=" << n << ": chen " << chen << " lan so sanh, tron " << tron
                  << ", ba cach ra cung ket qua? " << (b == d && c == d) << "\n";
    }
    return 0;
}
```

**Chạy từng dòng** (`sapChen` trên `{5, 2, 9}`; `sapTron` trên `{5, 2, 9, 1}`)

| Dòng | Chuyện gì xảy ra | Dãy lúc này |
|---|---|---|
| (1)-(4), `i = 1` | `x = 2`; `5 > 2` nên `5` dời sang phải (3); `j = -1` thoát; đặt `2` ở ô đầu (4) | `2 5 9` |
| (1)-(2), `i = 2` | `x = 9`; `a[1] = 5 <= 9` nên `break` ngay, `9` ở yên | `2 5 9` |
| (5)-(6) | `sapTron` cắt `{5, 2, 9, 1}` thành `{5, 2}` và `{9, 1}`, mỗi nửa lại cắt tới khi còn một phần tử (điểm dừng) | `{5} {2} {9} {1}` |
| (7) | Trộn `{5}` và `{2}`: so `5` với `2`, lấy `2`; `{5}` còn dư nên (8) chép nốt `5`; tương tự `{1, 9}` | `{2, 5}` `{1, 9}` |
| (7)-(8) | Trộn `{2, 5}` và `{1, 9}`: lấy `1`, rồi `2`, rồi `5`; `9` còn dư, chép nốt | `1 2 5 9` |

**Kết quả khi chạy:**

```text
sap chen: 1 2 5 5 6 9 
sap tron: 1 2 5 5 6 9 
n=1000: chen 251044 lan so sanh, tron 8792, ba cach ra cung ket qua? 1
n=2000: chen 1002544 lan so sanh, tron 19586, ba cach ra cung ket qua? 1
n=4000: chen 4009212 lan so sanh, tron 43145, ba cach ra cung ket qua? 1
```

Nhìn từ `n = 1000` lên `2000`: số lần so sánh của sắp xếp chèn gần **gấp bốn** (251 nghìn lên 1,0 triệu), đúng với O(n²); của sắp xếp trộn chỉ hơn gấp đôi một chút (8792 lên 19586), đúng với O(n log n). Số liệu này không phụ thuộc máy vì dãy cố định; thời gian giây thì có, nên mình không đo. Cả ba cách (kể cả `std::sort`) cho cùng kết quả.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết tìm kiếm nhị phân. Những chỗ nào hay sai?"
    Giữ đoạn `[lo, hi]` còn có thể chứa `x`; `mid = lo + (hi - lo) / 2`; trúng thì trả, `v[mid] < x` thì `lo = mid + 1`, ngược lại `hi = mid - 1`; lặp khi `lo <= hi`. O(log n) thời gian, O(1) bộ nhớ, dãy phải đã sắp. Ba lỗi hay gặp: tính giữa bằng `(lo + hi) / 2` (tràn số), quên `+ 1`/`- 1` (vòng lặp mãi), và `size() - 1` trên `size_t` khi dãy rỗng. Trong thực tế dùng `std::binary_search` hoặc `std::lower_bound`.

??? question "Hai số trong mảng có tổng `k`: nêu các cách và đánh đổi."
    Vét cạn thử mọi cặp: O(n²) thời gian, O(1) bộ nhớ. `unordered_map` lưu số đã gặp và tìm số bù: O(n) thời gian trung bình, O(n) bộ nhớ, không cần dãy sắp. Dãy đã sắp thì hai con trỏ từ hai đầu: O(n) thời gian, O(1) bộ nhớ; nếu chưa sắp mà sắp trước thì O(n log n) tổng. Chọn theo ràng buộc: bộ nhớ chặt thì hai con trỏ, dãy chưa sắp mà cần nhanh thì map.

??? question "So sánh merge sort, quick sort và `std::sort`."
    Merge sort luôn O(n log n) nhưng cần O(n) bộ nhớ phụ. Quick sort trung bình O(n log n), sắp ngay trong dãy, nhưng chọn mốc xấu thì O(n²). `std::sort` do chuẩn chỉ đòi O(n log n) (từ C++11 cả khi xấu nhất); thư viện thực tế cài bản lai nhiều thuật toán. Bubble và insertion sort là O(n²), chỉ hợp dãy rất ngắn hoặc gần đã sắp.

??? question "Vì sao Fibonacci đệ quy chậm? Sửa thế nào?"
    Mỗi lần gọi sinh hai lần gọi con và tính lại cùng giá trị nhiều lần, nên số lần gọi bùng nổ cỡ O(2^n) (chặt hơn: cỡ 1,6^n). Sửa bằng ghi nhớ (đệ quy kèm bảng) hoặc quy hoạch động từ dưới lên (vòng `for`, mỗi ô bằng tổng hai ô trước): O(n) thời gian, và bản từ dưới lên có thể giữ chỉ hai giá trị cuối nên O(1) bộ nhớ. Nhắc thêm kiểu `long long` vì `F(50)` đã vượt `int`.

??? question "Khi nào dùng quy hoạch động? Khác gì tham lam?"
    Khi bài lớn ghép từ các bài con lặp lại: định nghĩa ô `dp`, điểm bắt đầu, công thức nối các ô, ô chứa đáp án. Tham lam chọn tốt nhất tại mỗi bước và không quay lại, nên nhanh nhưng chỉ đúng với một số bài (đổi tiền với xu `{1, 3, 4}` cho `6` ra 3 xu thay vì 2 xu). Quy hoạch động thử mọi lựa chọn nhưng nhớ đáp án nên vẫn đúng và đủ nhanh.

??? question "Bạn giải một bài thuật toán ở bảng trắng thế nào?"
    Hỏi lại đề (dãy đã sắp chưa, rỗng được không, trùng không), làm tay một ví dụ nhỏ, nêu cách vét cạn đúng kèm độ phức tạp, rồi nói to chỗ nào cải tiến được và vì sao. Viết code gọn, chạy tay các biên (rỗng, một phần tử, không có đáp án), cuối cùng nêu độ phức tạp thời gian và bộ nhớ.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Lệch biên trong tìm nhị phân"
    Dùng `lo < hi` làm sót phần tử cuối, quên `+ 1` hay `- 1` làm vòng lặp không dừng, tính giữa bằng `(lo + hi) / 2` làm tràn số. Còn gán `hi = v.size() - 1` với `hi` kiểu `size_t` thì dãy rỗng cho số khổng lồ (mình đã chạy một khối nhỏ: trên máy 64 bit, `v.size() - 1` của vector rỗng in `18446744073709551615`). Sửa: `int` cùng `static_cast<int>`, `lo <= hi`, `mid ± 1`.

!!! warning "Lỗi 2: Dùng nhị phân hay hai con trỏ trên dãy chưa sắp"
    Cả hai dựa vào thứ tự để loại bỏ một phía: dãy chưa sắp thì kết quả sai mà không báo lỗi gì (`std::binary_search` đòi dãy đã sắp; vi phạm thì kết quả không đáng tin). Hãy sắp trước (O(n log n)) hoặc chọn cách không cần thứ tự (`unordered_map`).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="23" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. `timNhiPhan` là hàm ở mục 1. Nó trả về gì khi tìm `12`, và sau mấy vòng lặp?

```text
v = {2, 4, 6, 8, 10, 12, 14}
timNhiPhan(v, 12)
```

- `5`, sau ba vòng: ghé `v[3]`, rồi `v[4]`, rồi `v[5]`
- `5`, sau hai vòng: ghé `v[3] = 8`, rồi `v[5] = 12`
- `-1`, vì `12` nằm ở nửa phải nên hàm bỏ qua nó
- `6`, vì `12` là phần tử thứ 6 khi đếm từ 1

<p class="giai-thich" markdown>Vòng một: `lo = 0`, `hi = 6`, `mid = 3`, `v[3] = 8 < 12` nên `lo = 4`. Vòng hai: `mid = 4 + (6 - 4) / 2 = 5`, `v[5] = 12` trúng nên trả `5`, không còn vòng ba (nên "ba vòng" sai dù cũng ra `5`). Không có chuyện bỏ qua nửa phải: nửa phải mới là nơi chứa `12`. Hàm trả chỉ số (đếm từ 0) chứ không phải thứ tự đếm từ 1, nên `6` sai; chỉ số `6` còn chứa `14`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Vì sao viết `lo + (hi - lo) / 2` thay cho `(lo + hi) / 2`?

- Vì phép chia chạy trước phép cộng sẽ nhanh hơn rõ rệt
- Vì `(lo + hi) / 2` luôn làm tròn lên nên bỏ sót phần tử đầu
- Vì `lo + hi` luôn là số âm khi dãy rỗng
- Vì `lo + hi` có thể tràn `int`, còn hiệu `hi - lo` thì không tràn

<p class="giai-thich" markdown>Khi `lo` và `hi` đều lớn, tổng của chúng có thể tràn `int`, và số có dấu tràn là hành vi không xác định; hiệu `hi - lo` luôn nằm trong khoảng an toàn. Tốc độ không phải lý do vì hai cách tốn số phép tính như nhau. Cả hai cách đều làm tròn xuống (phép chia nguyên cắt phần lẻ), và với dãy rỗng không có vòng lặp nào để tính giữa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn sau. `timCap` là hàm hai con trỏ ở mục 2. Nó dừng ở cặp chỉ số nào?

```text
v = {1, 2, 4, 7, 11}, k = 9
timCap(v, 9, i, j)
```

- `i = 1`, `j = 3`, vì `2 + 7 = 9` sau khi giảm `j` rồi tăng `i`
- `i = 2`, `j = 3`, vì `4 + 7 = 11` là tổng gần `9` nhất
- `i = 0`, `j = 4`, vì `1 + 11 = 12` là cặp đầu tiên được thử
- Không có cặp nào, vì không có hai số liền kề cộng ra `9`

<p class="giai-thich" markdown>Bắt đầu `i = 0`, `j = 4`: `1 + 11 = 12 > 9` nên giảm `j` còn 3; `1 + 7 = 8 < 9` nên tăng `i` còn 1; `2 + 7 = 9` thì dừng. Cặp `i = 0`, `j = 4` chỉ là cặp thử đầu tiên và cho tổng `12`, không phải đáp án. Cặp chỉ số 2 và 3 không bao giờ được thử vì `i` chưa kịp tới đó (và tổng `11` cũng không phải `9`); còn hai số không cần liền kề: hai con trỏ tìm mọi cặp có thể.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Vì sao `fibNgayTho(n)` (đệ quy gọi `n-1` và `n-2`, không ghi nhớ) chậm theo hàm mũ?

- Vì mỗi lần gọi đều dùng thêm một khung stack nên stack luôn đầy trước khi tính xong
- Vì đệ quy luôn chậm hơn vòng lặp cả theo hàm mũ khi `n` tăng
- Vì mỗi lần gọi sinh hai lần gọi con và các lần gọi con lặp lại việc đã tính
- Vì kiểu `long long` làm mỗi phép cộng chậm đi theo `n`

<p class="giai-thich" markdown>Hai nhánh gọi lại cùng một đối số (ví dụ `F(3)` được tính cả từ `F(5)` lẫn từ `F(4)`), nên số lần gọi gần như nhân lên mỗi khi `n` tăng; ghi nhớ cắt đúng chỗ lặp đó. Độ sâu đệ quy chỉ cỡ `n` nên stack không đầy chỉ vì lý do này. Đệ quy chậm hơn vòng lặp chỉ một hằng số khi cùng số bước, không phải theo hàm mũ, và `long long` cộng một lần là hằng số.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Chuẩn C++ nói gì về độ phức tạp của `std::sort`?

- Đòi O(n log n) (từ C++11), thuật toán tùy thư viện
- Bắt buộc dùng quick sort thuần nên xấu nhất có thể O(n²)
- Bắt buộc dùng merge sort, vì vậy luôn cần thêm bộ nhớ phụ cỡ n
- Chỉ đòi O(n²) vì sắp xếp tổng quát không làm tốt hơn được

<p class="giai-thich" markdown>Chuẩn chỉ nêu giới hạn độ phức tạp, không chọn thuật toán, và thư viện thực tế dùng bản lai. Quick sort thuần có xấu nhất O(n²) nên không thỏa giới hạn của chuẩn. Merge sort không hề được chuẩn bắt buộc. Giới hạn O(n²) sai vì sắp xếp so sánh làm được O(n log n), như merge sort ở phần 💻.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. Đếm số cách leo `n` bậc cầu thang (mỗi lần bước 1 hoặc 2 bậc) bằng bảng `dp`. Số cách leo 5 bậc là bao nhiêu?

```text
dp[1] = 1, dp[2] = 2
dp[i] = dp[i-1] + dp[i-2]
```

- `10`, vì mỗi bậc thêm đều nhân đôi số cách của bậc trước
- `5`, vì có đúng một cách cho mỗi bậc từ 1 đến 5
- `7`, vì `dp[5] = dp[4] + dp[2]` với `dp[4] = 5`
- `8`, vì `dp[3] = 3`, `dp[4] = 5`, rồi `dp[5] = 5 + 3`

<p class="giai-thich" markdown>Điền bảng từ dưới lên: `dp[3] = 2 + 1 = 3`, `dp[4] = 3 + 2 = 5`, `dp[5] = 5 + 3 = 8`. Con số `10` không ra từ công thức nào: công thức cộng hai ô liền trước chứ không nhân đôi. Mỗi bậc cũng không chỉ có một cách. Công thức `dp[4] + dp[2]` bỏ nhầm ô: ô cần cộng là hai ô liền trước `dp[4]` và `dp[3]`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Được giao một bài thuật toán ở bảng trắng, việc nào nên làm trước khi viết code?

- Nói luôn cách tối ưu mà bạn nhớ, rồi mới hỏi lại đề
- Vừa viết code vừa nghĩ, gặp lỗi mới hỏi lại đề
- Hỏi lại đề, làm tay một ví dụ nhỏ, nói cách vét cạn
- Nghĩ kỹ một mình tới khi có lời giải hoàn chỉnh rồi trình bày

<p class="giai-thich" markdown>Làm rõ đề và thử ví dụ nhỏ giúp tránh giải nhầm bài, còn nói to cách vét cạn cho người nghe thấy bạn đang nghĩ gì và có điểm khởi đầu để cải tiến. Nói ngay cách tối ưu khi chưa hiểu đề dễ giải sai bài, và viết code trước rồi mới hỏi thì sửa lại tốn hơn. Nghĩ một mình tới cuối làm người phỏng vấn không chấm được cách nghĩ của bạn, cũng không gợi ý được khi bạn kẹt.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Tìm nhị phân** cần dãy đã sắp và truy cập ngẫu nhiên: giữ đoạn `[lo, hi]`, `mid = lo + (hi - lo) / 2` (tránh tràn `int` của `(lo + hi) / 2`), `lo = mid + 1` hoặc `hi = mid - 1`, lặp khi `lo <= hi`; O(log n), dãy rỗng cho `-1`; thư viện có `std::binary_search` (`bool`) và `std::lower_bound` (iterator tới phần tử đầu tiên `>= x`), Go có `sort.Search` và `slices.BinarySearch`.
2. **Hai con trỏ** trên dãy đã sắp (tổng nhỏ quá thì tăng `i`, lớn quá thì giảm `j`) giải two sum O(n) thời gian và O(1) bộ nhớ; dãy chưa sắp dùng `unordered_map` lưu số đã gặp để tìm số bù, O(n) thời gian trung bình và O(n) bộ nhớ.
3. **Sắp xếp**: chèn và bubble O(n²) (đo `n = 1000` lên `2000` thì số lần so sánh của chèn gần gấp bốn), merge sort O(n log n) mọi trường hợp nhưng cần bộ nhớ phụ, quick sort trung bình O(n log n) xấu nhất O(n²); chuẩn chỉ đòi `std::sort` đạt O(n log n) (từ C++11 cả khi xấu nhất), thư viện cài bản lai.
4. **Fibonacci đệ quy ngây thơ** gọi lặp lại cùng bài con nên bùng nổ O(2^n) (`F(30)` hơn 2,6 triệu lần gọi, Go cũng vậy); **ghi nhớ** (bảng đi kèm đệ quy) hay vòng lặp từ dưới lên đưa về O(n), nhớ dùng `long long`.
5. **Quy hoạch động** giải mỗi bài con một lần và ghi vào bảng (định nghĩa ô, điểm bắt đầu, công thức, ô đáp án), ví dụ Fibonacci, leo cầu thang, đổi tiền O(t · m) đúng cả khi tham lam sai (`{1, 3, 4}`, tiền 6); ở bảng trắng hãy làm rõ đề, ví dụ nhỏ, nói to, nêu độ phức tạp và kiểm tra biên (rỗng, một phần tử).
