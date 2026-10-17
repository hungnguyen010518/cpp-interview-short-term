# Bài 53 — Chọn container: vector, list, deque, map, unordered_map, set

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Chọn container bằng cách hỏi **mẫu truy cập** (duyệt tuần tự? tra theo khóa? duyệt có thứ tự? chèn/xóa giữa?) chứ không bắt đầu từ cái tên; đọc được cả Big-O lẫn **hằng số ẩn** (cấp phát, bộ nhớ đệm, bộ nhớ thêm mỗi phần tử).
    - Thấy bằng số đo thật vì sao `vector` gần như luôn thắng `list` (kể cả khi chèn giữa), và biết đúng ba điều kiện để `list` thắng.
    - Phân biệt `map` và `unordered_map` ở thứ tự, tra theo khoảng, tính ổn định của tham chiếu/iterator, trường hợp xấu nhất; nhớ bẫy `operator[]` tự chèn và bẫy `vector<bool>`.
    - Giải 10 tình huống chọn container có lý do (đếm tần suất, LRU, hàng đợi, đồ thị, top-K, tập đã thấy, nhiều khóa...), và dùng **vector đã sắp + `lower_bound`** thay `map` khi dữ liệu ít sửa.

**Bạn cần biết trước:** [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector`, `reserve`), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`deque`, `list`), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`map`, `unordered_map`, `m[k]` tự chèn), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator bị vô hiệu), [Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md) (Big-O), [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) (`priority_queue`, top-K), [Bài 23](../nhom-2-stl-thuat-toan/23-thuat-toan-hay-hoi.md) (`std::lower_bound`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::chrono`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template`), [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) (đo hiệu năng phải dùng `-O2`).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn viết lên bảng: "Cần chèn phần tử vào giữa một dãy liên tục. Bạn dùng container nào?" Bạn nhớ bảng Big-O và đáp ngay "`std::list`, chèn giữa O(1)". Anh ấy cười: "Thế nếu mình đo thì sao? Em dám nói chắc `list` nhanh hơn không?"

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Kho của bếp có nhiều kiểu cất đồ. `vector` là **một dãy kệ liền khối**: lấy món thứ 500 là đi thẳng tới, nhưng chen món vào giữa phải xô cả hàng. `list` là **các tấm thẻ rời** rải khắp kho: chen món chỉ sửa hai thẻ kề, nhưng tìm tới chỗ chen phải lần từng thẻ.

`map` là **sổ cái xếp theo ABC**: tra nhanh, lật trang kế là có "tên đứng sau". `unordered_map` là **tủ nhiều ngăn kéo có nhãn băm**: tra nhanh hơn nữa nhưng ngăn nào cạnh ngăn nào thì vô nghĩa. `deque` là **hàng người chờ trước cửa bếp**: vào ra ở hai đầu đều dễ.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Người thật đi nhanh hay chậm tùy quãng đường; máy còn tốn thêm một thứ không có ngoài đời: **bộ nhớ đệm** của CPU. Đọc những byte nằm sát nhau rẻ hơn rất nhiều so với nhảy tới các địa chỉ xa nhau (mục 2).

## 📖 Giải thích

### 1. Hỏi mẫu truy cập, đừng hỏi tên

Người giỏi chọn container không nhớ bảng; họ hỏi **chương trình làm gì với dữ liệu nhiều nhất**. Cây quyết định:

```text
Tra theo KHÓA (không phải theo vị trí)?
|- có: cần thứ tự khóa, hỏi khoảng, "khóa kế tiếp"?
|       |- có    -> map / set   (ít sửa: vector đã sắp + lower_bound)
|       `- không -> unordered_map / unordered_set
`- không (dãy theo vị trí):
        thêm/lấy ở HAI ĐẦU?                          -> deque
        đã cầm iterator, chèn/xóa giữa dày đặc,
        cần địa chỉ phần tử ổn định, n LỚN?          -> list
        còn lại                                       -> vector
```

Bảng dưới thêm cột **khi nào KHÔNG nên dùng**, phần người phỏng vấn hay hỏi vặn. Big-O là mức chuẩn đòi ([Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md)).

| Container | Mạnh khi | Đừng dùng khi |
|---|---|---|
| `vector` | duyệt tuần tự, `[i]`, thêm cuối | chèn/xóa đầu hoặc giữa dày đặc với n lớn; giữ tham chiếu qua lúc thêm mà chưa `reserve` |
| `deque` | thêm/lấy ở hai đầu, tham chiếu ổn định ở hai đầu | cần bộ nhớ liền khối (như đưa mảng cho hàm C); chèn giữa |
| `list` | đã cầm iterator + chèn/xóa giữa, địa chỉ ổn định, n lớn | gần như mọi lúc khác: cần `[i]`, hay duyệt, phần tử nhỏ |
| `map`, `set` | duyệt có thứ tự, `lower_bound`, khoảng | chỉ tra/đếm, không cần thứ tự (`unordered_*` thường nhanh hơn) |
| `unordered_map`, `unordered_set` | tra, đếm, "đã thấy chưa" | cần thứ tự hay khoảng; cần chặn trên thời gian xấu nhất |

### 2. Hằng số ẩn: Big-O chưa nói hết

Trước hết là phần Big-O ([Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md)), mức mà chuẩn đòi (dấu `–` là không có thao tác đó):

| Thao tác | `vector` | `deque` | `list` | `map`/`set` | `unordered_*` |
|---|---|---|---|---|---|
| `[i]` theo vị trí | O(1) | O(1) | – | – | – |
| tìm theo giá trị/khóa | O(n) | O(n) | O(n) | O(log n) | O(1) tb, O(n) xấu nhất |
| thêm ở cuối | O(1) amortized | O(1) | O(1) | – | – |
| thêm/xóa ở đầu | O(n) | O(1) | O(1) | – | – |
| chèn/xóa ở giữa (đã có vị trí) | O(n) | O(n) | O(1) | – | – |
| thêm/xóa theo khóa | – | – | – | O(log n) | O(1) tb, O(n) xấu nhất |

Big-O bỏ hằng số, nhưng máy thật trả tiền cho hằng số:

| | `vector` | `deque` | `list` | `map`/`set` | `unordered_*` |
|---|---|---|---|---|---|
| lần cấp phát heap | ít (một mảng) | ít (khối nhỏ) | **mỗi nút một lần** | **mỗi nút một lần** | **mỗi nút một lần** + mảng hộp |
| bộ nhớ thêm mỗi phần tử | ~0 (trừ capacity dự trữ) | nhỏ | hai con trỏ + phần quản lý | nhiều (xem dưới) | con trỏ nút kế + phần quản lý |
| duyệt tuần tự | **nhanh nhất**, byte sát nhau | gần như vector | chậm: nhảy qua nút rải rác | chậm: đi theo cây | chậm: đi theo nút |
| tham chiếu/con trỏ tới phần tử khi thêm | hỏng nếu tái cấp phát | sống ở hai đầu | luôn sống | luôn sống | luôn sống (kể cả rehash) |

Số "nhiều" của `map` mình đo trên g++ 11 (libstdc++): `sizeof(std::_Rb_tree_node_base)` là 32 byte (màu đỏ/đen, con trỏ cha, trái, phải), và hai nút kề nhau của `map<int,int>` cách nhau 48 byte, trong khi một `pair<int,int>` trong vector chỉ chiếm 8 byte. Đó là chi tiết của bản thư viện này, chuẩn không đòi.

**Bộ nhớ đệm (cache).** CPU không đọc từng byte từ RAM: nó kéo cả một **dòng cache** (thường 64 byte, [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)) về chỗ đệm gần lõi. Duyệt `vector<int>` thì mỗi dòng mang theo cỡ 16 số kế tiếp nên các lần đọc sau gần như miễn phí. Duyệt `list` thì mỗi nút ở một chỗ khác, mỗi bước theo con trỏ có thể là một lần chờ RAM. Tính chất "đọc thứ nằm sát nhau thì nhanh" gọi là **tính cục bộ của bộ nhớ đệm** (cache locality).

Ta đo, hai phần. **Phần A:** chèn 20000 số vào vị trí **ngẫu nhiên** của `vector` và `list` (cùng chỗ), rồi duyệt 200 lượt. **Phần B:** đã **cầm sẵn iterator** tới giữa dãy 100000 phần tử, chèn 20000 lần vào đúng chỗ đó.

Ba thứ mới trong code, đọc trước cho khỏi vấp:

- `v.insert(it, x)` chèn `x` vào trước `it` và dời mọi phần tử phía sau sang phải; `l.insert(it, x)` cũng chèn trước `it` nhưng chỉ nối con trỏ; `std::next(it, k)` là "đi k bước" từ `it`.
- Hàm `tiep` là bộ sinh số giả ngẫu nhiên tự làm: cùng hạt giống thì cùng dãy, nên hai bên chèn đúng cùng chỗ. `unsigned` tràn thì quay vòng có định nghĩa, khác `int` ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)); hậu tố `u` của `12345u` nghĩa là số không dấu.
- `a % k` là số dư khi chia `a` cho `k`, dùng để ép vị trí vào khoảng hợp lệ; `x >> 16` bỏ 16 bit thấp (bit thấp của công thức này ít ngẫu nhiên).

```cpp
#include <chrono>
#include <iostream>
#include <iterator>
#include <list>
#include <vector>

unsigned tiep(unsigned& x) {
    x = x * 1103515245u + 12345u;                        // (1) công thức sinh số giả ngẫu nhiên
    return x >> 16;
}

long long tiLe(long long a, long long b) {               // a / b làm tròn, tránh chia cho 0
    return (a + b / 2) / (b > 0 ? b : 1);
}

long long troiUs(std::chrono::steady_clock::time_point bat) {
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::microseconds>(troi).count();
}

int main() {
    // Phần A: chèn vào vị trí NGẪU NHIÊN, rồi duyệt.
    const int n = 20000;
    std::vector<int> v;
    std::list<int> l;
    unsigned hatV = 1, hatL = 1;
    auto bat = std::chrono::steady_clock::now();
    for (int i = 0; i < n; ++i)
        v.insert(v.begin() + tiep(hatV) % (v.size() + 1), i);         // (2) vector: dời phần đuôi sang phải
    long long usV = troiUs(bat);
    bat = std::chrono::steady_clock::now();
    for (int i = 0; i < n; ++i) {
        auto it = std::next(l.begin(), tiep(hatL) % (l.size() + 1));  // (3) list: đi từng nút tới vị trí
        l.insert(it, i);                                              // (4) chèn chỉ nối lại hai con trỏ
    }
    long long usL = troiUs(bat);

    long long tongV = 0, tongL = 0;
    bat = std::chrono::steady_clock::now();
    for (int lan = 0; lan < 200; ++lan) for (int x : v) tongV += x;   // (5) duyệt vector 200 lượt
    long long duyetV = troiUs(bat);
    bat = std::chrono::steady_clock::now();
    for (int lan = 0; lan < 200; ++lan) for (int x : l) tongL += x;   // (6) duyệt list 200 lượt
    long long duyetL = troiUs(bat);

    // Phần B: đã CẦM SẴN iterator tới giữa, chèn nhiều lần vào đúng chỗ đó.
    std::vector<int> lon(100000, 1);
    std::list<int> dsl(100000, 1);
    bat = std::chrono::steady_clock::now();
    for (int i = 0; i < 20000; ++i) lon.insert(lon.begin() + 50000, i);   // (7) mỗi lần dời nửa đuôi
    long long cV = troiUs(bat);
    bat = std::chrono::steady_clock::now();
    auto giua = std::next(dsl.begin(), 50000);                        // (8) đi tới giữa đúng MỘT lần
    for (int i = 0; i < 20000; ++i) dsl.insert(giua, i);              // (9) mỗi lần chỉ nối lại con trỏ
    long long cL = troiUs(bat);

    std::cout << "cung ket qua? " << (v.size() == l.size() && tongV == tongL && lon.size() == dsl.size()) << "\n";
    std::cout << "A chen ngau nhien: list cham hon vector? " << (usL > usV) << ", list/vector = " << tiLe(usL, usV) << " lan\n";
    std::cout << "A duyet: list/vector = " << tiLe(duyetL, duyetV) << " lan\n";
    std::cout << "B da cam iterator: list nhanh hon vector? " << (cL < cV) << ", vector/list = " << tiLe(cV, cL) << " lan\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Chi phí lúc này |
|---|---|---|
| (2) | `vector` dời trung bình nửa đuôi | một lần chép khối byte liền nhau |
| (3)-(4) | `list` lần theo con trỏ trung bình n/2 nút, rồi nối hai con trỏ | n/2 lần nhảy tới địa chỉ xa |
| (5)-(6) | Cùng cộng toàn bộ số, 200 lượt | `vector`: đọc liền; `list`: nhảy nút |
| (7) | Mỗi lần dời 50000+ phần tử | O(n) mỗi lần |
| (8)-(9) | Đi tới giữa một lần, rồi mỗi lần chèn chỉ sửa hai con trỏ (`giua` vẫn hợp lệ) | O(1) mỗi lần |

**Kết quả khi chạy** (g++ -std=c++17 -O2, một trong ba lần liền):

```text
cung ket qua? 1
A chen ngau nhien: list cham hon vector? 1, list/vector = 36 lan
A duyet: list/vector = 16 lan
B da cam iterator: list nhanh hon vector? 1, vector/list = 126 lan
```

Bốn lần `-O2` của mình ra: A chèn từ `24` tới `41` lần; A duyệt `16`-`17` lần; B từ `126` tới `162` lần. Máy bạn sẽ ra số khác, nên chỉ cái **mẫu** đáng nhớ (A: `list` chậm hơn rõ; B: `list` thắng áp đảo). Mình in tỉ lệ chứ không in mili giây vì mili giây đổi theo máy.

**Thử thay đổi: biên dịch không `-O2`.** Mình đã chạy: A chèn vẫn chậm cỡ `29`-`45` lần và B vẫn thắng `50`-`71` lần, nhưng A duyệt chỉ còn chênh `1`-`2` lần. Không tối ưu thì vòng lặp tự nó đã chậm, che mất chuyện chờ RAM; đó là lý do [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md) đòi `-O2` khi đo.

**Vậy `list` thắng khi nào?** Khi **đồng thời**: (1) đã cầm iterator tới chỗ chèn (phần B), (2) n lớn, (3) cần địa chỉ phần tử ổn định hoặc chèn dày đặc. Mất điều (1) là phần A: phải đi tìm vị trí, và mỗi bước là một lần chờ RAM. Mình còn thử phần B với n = 100 và 100 lần chèn: chênh chỉ `1`-`2` lần và có lần `list` không nhanh hơn, không đáng tin. Với n nhỏ, hay phải đi tìm, hoặc chủ yếu là duyệt: **`vector`**.

!!! info "Bạn biết Go?"
    Go không cho bạn chọn: slice là `vector`, và mọi người dùng slice cho gần như mọi việc, kể cả chèn giữa bằng `append(s[:i], append([]T{x}, s[i:]...)...)` (mình đã chạy với `[]int`, ra `[1 2 3 4]`). `container/list` của Go có sẵn nhưng hiếm ai dùng, cũng vì lý do bộ nhớ đệm này.

### 3. `map` và `unordered_map`: thứ tự, ổn định, trường hợp xấu nhất

Cả hai đều tra theo khóa, nhưng khác nhau ở những điều người phỏng vấn hay hỏi:

| | `map`, `set` | `unordered_map`, `unordered_set` |
|---|---|---|
| bên trong | cây đỏ-đen (một kiểu cây cân bằng, [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md)) | bảng băm ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)) |
| tìm/chèn/xóa | O(log n), **luôn luôn** | O(1) trung bình, **O(n) xấu nhất** |
| thứ tự duyệt | tăng dần theo khóa, mọi máy như nhau | không xác định |
| hỏi khoảng (`lower_bound`) | có | không |
| tham chiếu/con trỏ tới phần tử | sống khi thêm/xóa chỗ khác | sống khi thêm, **kể cả khi rehash** |
| iterator khi thêm | sống | **hỏng nếu rehash** ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)) |
| khóa tự định nghĩa cần | `operator<` | hàm băm + `operator==` |

Hai hàm mới của `map`/`set`: `lower_bound(k)` trả iterator tới phần tử đầu tiên có khóa **>= k** (hoặc `end()` nếu không có), `upper_bound(k)` tới phần tử đầu tiên có khóa **> k**. Cặp này trả lời "việc kế tiếp sau 14 giờ" hay "mọi khóa từ 10 tới 16", điều `unordered_map` không làm được. Chương trình dưới thử cả hai, và thử giữ địa chỉ một giá trị qua lúc chèn thêm nhiều khóa.

```cpp
#include <iostream>
#include <map>
#include <string>
#include <unordered_map>

int main() {
    std::map<int, std::string> lich;                     // khóa: giờ trong ngày (24 giờ)
    lich[9] = "hop nhom";
    lich[13] = "an trua";
    lich[16] = "review code";
    lich[20] = "da bong";

    auto it = lich.lower_bound(14);                      // (1) phần tử đầu tiên có khóa >= 14
    std::cout << "viec ke tiep sau 14h: " << it->first << "h " << it->second << "\n";
    auto het = lich.lower_bound(21);                     // (2) không có khóa nào >= 21
    std::cout << "sau 21h co viec? " << (het != lich.end()) << "\n";
    for (auto i = lich.lower_bound(10); i != lich.upper_bound(16); ++i) {   // (3) khoảng 10..16
        std::cout << i->first << " ";
    }
    std::cout << "\n";

    std::string* giu = &lich[13];                        // (4) giữ địa chỉ của một giá trị
    for (int g = 0; g < 8; ++g) lich[g] = "ngu";         // (5) chèn thêm nhiều khóa vào giữa
    std::cout << "dia chi con dung? " << (giu == &lich[13]) << ", gia tri = " << *giu << "\n";

    std::unordered_map<int, std::string> bang;
    bang[13] = "an trua";
    std::string* giu2 = &bang[13];                       // (6)
    std::size_t hopTruoc = bang.bucket_count();
    for (int g = 100; g < 1100; ++g) bang[g] = "x";      // (7) chèn nhiều tới mức phải rehash
    std::cout << "unordered_map: so hop " << (bang.bucket_count() > hopTruoc ? "da tang" : "khong doi")
              << ", dia chi con dung? " << (giu2 == &bang[13]) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu lúc này |
|---|---|---|
| (1) | Khóa 9, 13 nhỏ hơn 14; 16 là đầu tiên `>= 14` | trỏ tới `16` |
| (2) | Không khóa nào `>= 21`, nên trả `end()` | `het == end()` |
| (3) | Từ `lower_bound(10)` (khóa 13) tới trước `upper_bound(16)` (khóa 20) | in `13 16` |
| (4)-(5) | `giu` trỏ vào nút khóa 13; thêm 8 khóa 0..7 | nút 13 **không bị dời** |
| (6)-(7) | Thêm 1000 khóa vào bảng băm: số hộp tăng (rehash) | nút 13 vẫn ở chỗ cũ |

**Kết quả khi chạy:**

```text
viec ke tiep sau 14h: 16h review code
sau 21h co viec? 0
13 16 
dia chi con dung? 1, gia tri = an trua
unordered_map: so hop da tang, dia chi con dung? 1
```

Dòng cuối là chỗ hay bị nhầm: rehash làm **iterator** hỏng (chuẩn nói vậy; mình không chạy thử vì dùng iterator hỏng là hành vi không xác định), nhưng **tham chiếu và con trỏ** tới phần tử vẫn sống vì các nút không bị dời, chỉ bảng hộp được xây lại. **Thử thay đổi: thêm `bang.reserve(2000);` ngay trước dòng (6).** Mình đã chạy: dòng cuối in `so hop khong doi`; biết trước cỡ thì `reserve` tránh rehash, như với `vector` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)).

**Trường hợp xấu nhất O(n) có thật không?** Có, khi nhiều khóa rơi vào cùng một hộp. Chương trình dưới ép chuyện đó bằng hàm băm tệ: mọi khóa cùng ra số 7. `BamXau` là một **functor** (hàm đối tượng, như `DongTep` ở [Bài 51](51-chon-smart-pointer.md)): `struct` có `operator()` nên gọi được như hàm. `unordered_map` nhận loại đối tượng đó làm tham số thứ ba để thay hàm băm mặc định. `bucket_count()` là số hộp, `bucket_size(h)` là số khóa trong hộp `h`. `dongNhat` là `template` ([Bài 34](../nhom-4-oop-patterns/34-template.md)) để dùng cho cả hai kiểu bảng.

```cpp
#include <algorithm>
#include <iostream>
#include <unordered_map>

struct BamXau {                                          // (1) struct có operator(): gọi nó như gọi hàm
    std::size_t operator()(int) const { return 7; }      // (2) mọi khóa cùng một số băm
};

template <class Bang>
std::size_t dongNhat(int n) {                            // số khóa của hộp đông nhất
    Bang b;
    for (int k = 0; k < n; ++k) b[k] = k;
    std::size_t lon = 0;
    for (std::size_t h = 0; h < b.bucket_count(); ++h) lon = std::max(lon, b.bucket_size(h));   // (3)
    return lon;
}

int main() {
    std::cout << "ham bam mac dinh: hop dong nhat co " << dongNhat<std::unordered_map<int, int>>(5000) << " khoa\n";
    std::cout << "ham bam xau: hop dong nhat co " << dongNhat<std::unordered_map<int, int, BamXau>>(5000) << " khoa\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
ham bam mac dinh: hop dong nhat co 1 khoa
ham bam xau: hop dong nhat co 5000 khoa
```

Hàm băm mặc định của `int` rải 5000 khóa mỗi hộp một khóa (trên bản thư viện của mình); hàm băm tệ dồn cả 5000 vào một hộp, nên mỗi lần chèn phải lục cả hộp: O(n). Mình đo thêm thời gian chèn bằng `std::chrono` (ở bản dài hơn, không chép ra đây): bản tệ chậm hơn `177`, `91`, `135` lần trong ba lần `-O2`, và cỡ `160` lần khi n = 10000. Vì vậy khi cần **chặn trên thời gian xấu nhất**, hoặc khóa đến từ người lạ có thể cố ý gây đụng độ, `map` an toàn hơn.

`set` và `unordered_set` chọn giống hệt, chỉ không có giá trị đi kèm: `unordered_set` cho "đã thấy chưa", `set` khi còn cần thứ tự hay "phần tử kế tiếp".

**Bẫy `operator[]`.** Như [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) đã nói, `m[k]` **chèn** khóa `k` với giá trị mặc định nếu chưa có. Ở bài chọn container nó thành lỗi thiết kế: hàm chỉ định "hỏi" mà làm bảng phình ra.

```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> diem = {{"an", 8}};
    diem["binh"];                                        // (1) định "chỉ hỏi", nhưng [] chèn khi thiếu khóa
    diem["chi"];
    std::cout << "sau 2 lan hoi bang []: size = " << diem.size() << "\n";

    std::map<std::string, int> sach = {{"an", 8}};
    sach.find("binh");                                   // (2) find và count không bao giờ chèn
    sach.count("chi");
    std::cout << "sau find va count: size = " << sach.size() << "\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
sau 2 lan hoi bang []: size = 3
sau find va count: size = 1
```

**Thử thay đổi: đưa `m[ten]` vào hàm nhận `const std::map<std::string, int>& m`.** Mình đã biên dịch: lỗi `passing 'const std::map<...>' as 'this' argument discards qualifiers`. Vì `[]` có thể chèn nên **không dùng được trên map `const`**. Tra mà không chèn: `find`, `count`, `contains` (C++20), hoặc `at` (ném ngoại lệ nếu thiếu).

!!! info "Bạn biết Go?"
    `map[K]V` của Go là bảng băm, tức `unordered_map`; Go **không có** map có thứ tự trong thư viện chuẩn, muốn duyệt theo thứ tự phải lấy khóa ra rồi sắp. Go cũng **không** có bẫy này: mình chạy `_ = m["binh"]` hai lần trên map của Go 1.27.2 thì `len(m)` vẫn là 1, đọc khóa thiếu trả giá trị 0 mà không chèn (chỉ `m["binh"]++` mới chèn).

### 4. `deque` và bẫy `vector<bool>`

`deque` ([Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md)) hợp với **hai đầu**: hàng đợi (`std::queue` mặc định dựng trên nó), cửa sổ trượt, và tham chiếu phần tử không hỏng khi thêm ở hai đầu. Không dùng khi cần bộ nhớ liền khối (`data()` cho hàm C) hoặc chèn giữa dày đặc (vẫn O(n)).

`std::vector<bool>` là bẫy vì mỗi phần tử là **1 bit** và `v[i]` trả về một **đối tượng đại diện** (proxy) nhớ "bit nào ở byte nào" chứ không phải `bool&` thật. Hệ quả: `auto x = b[0]` tưởng là bản sao nhưng thực ra là đại diện, nên sửa `x` là sửa luôn `b[0]`.

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<bool> b(3, false);
    auto x = b[0];                                       // (1) tưởng là bản sao của một bool
    x = true;                                            // (2) sửa "bản sao"
    std::cout << "vector<bool>: b[0] = " << b[0] << "\n";

    std::vector<char> c(3, 0);
    auto y = c[0];                                       // (3) bản sao thật
    y = 1;
    std::cout << "vector<char>: c[0] = " << static_cast<int>(c[0])
              << ", y = " << static_cast<int>(y) << "\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
vector<bool>: b[0] = 1
vector<char>: c[0] = 0, y = 1
```

Mình cũng biên dịch `bool& r = b[0];` và `bool* p = &b[0];`: cả hai lỗi biên dịch (`cannot bind non-const lvalue reference of type 'bool&' to an rvalue of type 'bool'`, và `taking address of rvalue`), vì không có `bool` thật nào để trỏ tới.

Mặt đa luồng: mình viết hai luồng, mỗi luồng ghi 100000 lần vào **một phần tử riêng** của `vector<bool>` (`co[0]` và `co[1]`) rồi `join`. Với `-fsanitize=thread`, ba lần chạy đều bị TSan báo `data race` ở `std::_Bit_reference::operator=` (`stl_bvector.h:93`) và thoát mã 66, vì hai bit nằm chung một từ nhớ ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Đổi thành `vector<char>` thì TSan im lặng, thoát mã 0 (ba lần). Cần mảng cờ: dùng `std::vector<char>`.

### 5. Vector đã sắp + `lower_bound` thay cho `map` khi ít sửa

Nếu dữ liệu **nạp một lần (hoặc ít khi sửa)** rồi tra rất nhiều, một `vector` đã sắp theo khóa kèm `std::lower_bound` ([Bài 23](../nhom-2-stl-thuat-toan/23-thuat-toan-hay-hoi.md)) tra O(log n) như `map`, nhưng các phần tử nằm liền nhau nên nhanh hơn và ít tốn bộ nhớ hơn (không có 32 byte đầu nút). Cái giá: chèn/xóa là O(n) vì phải giữ thứ tự. Mẹo: `std::make_pair(a, b)` tạo cặp `{a, b}`, và `std::pair` so theo `first` rồi mới `second`, nên với giá trị không âm, `std::make_pair(khoa, 0)` là mốc "đứng trước mọi cặp có khóa `khoa`".

```cpp
#include <algorithm>
#include <chrono>
#include <iostream>
#include <map>
#include <utility>
#include <vector>

int main() {
    const int n = 200000;
    std::map<int, int> m;
    std::vector<std::pair<int, int>> v;                  // (1) dãy (khóa, giá trị) ĐÃ SẮP theo khóa
    for (int k = 0; k < n; ++k) {
        m[k * 3] = k;                                    // khóa 0, 3, 6, ...
        v.push_back({k * 3, k});                         // (2) thêm theo thứ tự tăng nên vector tự đã sắp
    }

    auto tra = [&v](int khoa) {                          // (3) tra khóa trong vector đã sắp
        auto it = std::lower_bound(v.begin(), v.end(), std::make_pair(khoa, 0));
        return (it != v.end() && it->first == khoa) ? it->second : -1;
    };

    unsigned x = 1;
    long long tongM = 0, tongV = 0;
    auto bat = std::chrono::steady_clock::now();
    for (int i = 0; i < 300000; ++i) {
        x = x * 1103515245u + 12345u;
        int khoa = static_cast<int>((x >> 8) % (3 * n));  // (4) khóa ngẫu nhiên, trúng khoảng 1/3
        auto it = m.find(khoa);
        tongM += (it != m.end()) ? it->second : -1;
    }
    long long usM = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - bat).count();

    x = 1;
    bat = std::chrono::steady_clock::now();
    for (int i = 0; i < 300000; ++i) {
        x = x * 1103515245u + 12345u;
        int khoa = static_cast<int>((x >> 8) % (3 * n));
        tongV += tra(khoa);
    }
    long long usV = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - bat).count();

    std::cout << "cung ket qua? " << (tongM == tongV) << "\n";
    std::cout << "vector da sap nhanh hon map? " << (usV < usM) << "\n";
    std::cout << "map/vector = " << (usM + usV / 2) / (usV > 0 ? usV : 1) << " lan\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu lúc này |
|---|---|---|
| (1)-(2) | `map` và `vector` cùng nhận 200000 cặp, khóa tăng dần | `v` tự đã sắp, không cần `sort` |
| (3) | `lower_bound` tìm cặp đầu tiên không nhỏ hơn `(khoa, 0)`, rồi kiểm khóa có khớp | tìm nhị phân trên mảng liền |
| (4) | 300000 khóa ngẫu nhiên, hai bên dùng cùng hạt giống 1 | hai tổng phải bằng nhau |

**Kết quả khi chạy** (`-O2`, một trong ba lần liền):

```text
cung ket qua? 1
vector da sap nhanh hon map? 1
map/vector = 4 lan
```

Ba lần của mình ra `5`, `4`, `6` lần. Không `-O2` thì chênh chỉ khoảng `1`-`2` lần (mình đã chạy), và số lần đổi theo cỡ dữ liệu và máy. **Không** làm vậy khi dữ liệu bị sửa liên tục (mỗi lần chèn là O(n)) hay cần tham chiếu ổn định (chèn làm dời phần tử). Biết trước cỡ thì gọi `reserve(n)` trước vòng thêm, cho `vector` lẫn `unordered_map`: tránh tái cấp phát/rehash và giữ tham chiếu sống.

### 6. Mười tình huống chọn container

| # | Tình huống | Chọn | Lý do |
|---|---|---|---|
| 1 | Đếm tần suất từ trong tệp lớn, chỉ cần số đếm | `unordered_map<string,int>`, `++dem[tu]` | chỉ tra/đếm, O(1) trung bình; cần in theo ABC thì `map` |
| 2 | Cache LRU: lấy và bỏ mục lâu không dùng, O(1) | `list` + `unordered_map<khóa, iterator vào list>` | `list` chuyển một nút lên đầu không dời ai, iterator không hỏng (💻) |
| 3 | Hàng đợi công việc FIFO, duyệt đồ thị theo chiều rộng | `std::queue` (mặc định trên `deque`) | thêm cuối, lấy đầu đều O(1) |
| 4 | Đồ thị 100000 đỉnh, mỗi đỉnh vài láng giềng | `vector<vector<int>>` | chỉ số đỉnh là vị trí; mỗi dãy láng giềng liền khối |
| 5 | Lấy K số lớn nhất từ luồng lớn, bộ nhớ nhỏ | `priority_queue` min-heap cỡ K | O(log K) mỗi số, giữ K phần tử ([Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md)) |
| 6 | "Đã thấy phần tử này chưa" (loại trùng) | `unordered_set` | chỉ cần có/không; cần giữ thứ tự xuất hiện thì thêm `vector` song song |
| 7 | Tra nhân viên theo `id` **và** theo `email` | một `vector` giữ dữ liệu + mỗi khóa một chỉ mục `unordered_map<khóa, vị trí>` | dữ liệu ở **một** chỗ; chỉ mục lưu **chỉ số**, không lưu con trỏ (💻) |
| 8 | Bảng giá nạp một lần, tra hàng triệu lần | `vector` đã sắp + `lower_bound` (hoặc `unordered_map` nếu chỉ cần khớp đúng) | nhanh nhờ bộ nhớ đệm, ít tốn bộ nhớ (mục 5) |
| 9 | Lịch sự kiện: thêm/xóa liên tục, hỏi "sự kiện kế tiếp sau thời điểm T" | `map<thời điểm, sự kiện>` + `lower_bound` | cần thứ tự **và** sửa liên tục nên vector đã sắp không hợp |
| 10 | Cửa sổ trượt: giữ N sự kiện gần nhất (thêm cuối, bỏ đầu) | `deque` | hai đầu O(1), vẫn `[i]` được |

Hai gợi ý ngoài bảng: vài chục phần tử thì cái nào cũng được, cứ `vector` duyệt thẳng; mảng cờ đúng/sai lớn thì `vector<char>`, không phải `vector<bool>` (mục 4).

## 💻 Ví dụ code

### Tình huống 2: cache LRU bằng `list` + `unordered_map`

LRU (least recently used, "lâu không dùng nhất") là cache chứa tối đa `sucChua` mục; khi đầy mà có mục mới thì bỏ mục **lâu không dùng nhất**. Cần hai thao tác O(1): "đưa mục này lên đầu" và "bỏ mục ở cuối". Ta giữ các mục trong `list` (đầu = mới dùng nhất) và một `unordered_map` từ khóa tới **iterator vào nút của nó**, để nhảy tới nút mà không đi tìm.

Bốn điều cần biết trước khi đọc code:

- `thu_.splice(vi_tri_dich, thu_, it)` **nối nút `it` sang trước `vi_tri_dich`** trong cùng danh sách: chỉ sửa con trỏ, không chép phần tử, không cấp phát, iterator của nút vẫn đúng.
- `std::list<std::pair<int, int>>::iterator` là kiểu iterator của danh sách cặp (viết dài vậy).
- Hậu tố `_` (`sucChua_`) chỉ là cách đặt tên để phân biệt thành viên với tham số; `: sucChua_(sucChua)` là danh sách khởi tạo thành viên ([Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md)).
- Để gọn, `dat` giả định khóa chưa có trong cache.

```cpp
#include <iostream>
#include <list>
#include <unordered_map>

class LRU {
public:
    LRU(std::size_t sucChua) : sucChua_(sucChua) {}

    int lay(int khoa) {                                  // trả -1 nếu không có
        auto it = tra_.find(khoa);
        if (it == tra_.end()) return -1;
        thu_.splice(thu_.begin(), thu_, it->second);     // (1) đưa nút lên đầu: không chép, không cấp phát
        return it->second->second;
    }

    void dat(int khoa, int giaTri) {                     // giả định khóa chưa có
        if (thu_.size() == sucChua_) {                   // (2) đầy: bỏ nút CUỐI (lâu không dùng nhất)
            tra_.erase(thu_.back().first);
            thu_.pop_back();
        }
        thu_.push_front({khoa, giaTri});                 // (3) nút mới vào đầu
        tra_[khoa] = thu_.begin();                       // (4) bảng băm ghi nhớ iterator tới nút
    }

    void in() const {
        for (const auto& [k, v] : thu_) std::cout << k << "=" << v << " ";
        std::cout << "\n";
    }

private:
    std::size_t sucChua_;
    std::list<std::pair<int, int>> thu_;                 // đầu = mới dùng nhất
    std::unordered_map<int, std::list<std::pair<int, int>>::iterator> tra_;
};

int main() {
    LRU c(3);
    c.dat(1, 10); c.dat(2, 20); c.dat(3, 30);
    c.in();
    std::cout << "lay 1 -> " << c.lay(1) << "\n";
    c.in();
    c.dat(4, 40);
    c.in();
    std::cout << "lay 2 -> " << c.lay(2) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `thu_` (đầu -> cuối) |
|---|---|---|
| `dat` 1, 2, 3 | Mỗi mục mới vào đầu (3), ghi iterator vào `tra_` (4) | `3 2 1` |
| `lay(1)` | `it->second` là iterator vào nút của 1, `splice` đưa nó lên đầu (1); `it->second->second` là giá trị trong nút | `1 3 2` |
| `dat(4, 40)` | Đầy (size 3): bỏ nút cuối là `2` (2), thêm `4` vào đầu | `4 1 3` |
| `lay(2)` | `2` đã bị bỏ, `tra_` không còn khóa 2 | trả -1 |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
3=30 2=20 1=10 
lay 1 -> 10
1=10 3=30 2=20 
4=40 1=10 3=30 
lay 2 -> -1
```

**Thử thay đổi: xóa dòng (1)** (không `splice` trong `lay`). Mình đã chạy: sau `lay(1)` thứ tự vẫn `3 2 1`, nên `dat(4, 40)` bỏ nhầm mục `1` vừa dùng và `lay(2)` trả `20` thay vì `-1`: không còn là LRU. Vì sao `list` hợp ở đây: `unordered_map` giữ iterator vào nút, mà iterator của `list` **không hỏng** khi thêm/xóa nút khác (bảng mục 2). Với `vector` hay `deque`, chuyển phần tử giữa là O(n) và iterator hỏng.

### Tình huống 7: tra theo nhiều khóa

Tra theo nhiều khóa không có nghĩa là chép dữ liệu vào nhiều map. Giữ dữ liệu ở **một** `vector`, và mỗi khóa tra có một chỉ mục `unordered_map` ghi **vị trí** trong `vector`. `at(k)` của map tra như `[]` nhưng ném ngoại lệ thay vì chèn khi thiếu khóa, và `std::to_string(i)` đổi số `i` thành chuỗi.

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

struct NhanVien {
    int id;
    std::string email;
    std::string ten;
};

int main() {
    std::vector<NhanVien> ds;                                     // (1) nơi duy nhất giữ dữ liệu
    std::unordered_map<int, std::size_t> theoId;                  // (2) chỉ mục: khóa -> VỊ TRÍ trong ds
    std::unordered_map<std::string, std::size_t> theoEmail;
    auto them = [&](int id, const std::string& email, const std::string& ten) {
        ds.push_back({id, email, ten});
        theoId[id] = ds.size() - 1;                               // (3) lưu chỉ số, không lưu con trỏ
        theoEmail[email] = ds.size() - 1;
    };
    them(7, "an@x.vn", "An");
    them(9, "binh@x.vn", "Binh");
    for (int i = 0; i < 1000; ++i) them(100 + i, "u" + std::to_string(i) + "@x.vn", "U");   // (4) vector tái cấp phát nhiều lần
    std::cout << "theo id 9    -> " << ds[theoId.at(9)].ten << "\n";
    std::cout << "theo email  -> " << ds[theoEmail.at("an@x.vn")].ten << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu lúc này |
|---|---|---|
| (1)-(3) | Mỗi nhân viên vào `ds`; hai chỉ mục ghi vị trí của họ (7 ở 0, 9 ở 1) | `theoId = {7:0, 9:1}` |
| (4) | Thêm 1000 người nữa: `ds` tái cấp phát nhiều lần, nhưng chỉ số vẫn đúng | chỉ mục không hỏng |
| in | `theoId.at(9)` ra vị trí 1, `ds[1].ten` là `Binh`; email `an@x.vn` ra vị trí 0 | in `Binh`, `An` |

**Kết quả khi chạy** (ba lần liền đều như nhau):

```text
theo id 9    -> Binh
theo email  -> An
```

**Thử thay đổi: để chỉ mục lưu con trỏ `&ds.back()` thay cho chỉ số** (`unordered_map<int, NhanVien*>`, và đọc `theoId.at(9)->id`). Mình đã chạy: build thường in `9` cho id (đúng chỉ do chưa bị ghi đè) và số rác `-457089663` cho email; với `-fsanitize=address`, ASan báo `heap-use-after-free` ngay dòng in, vì `ds` đã tái cấp phát và trả mảng cũ ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)). Lưu **chỉ số** thì không có chuyện này.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Cần chèn vào giữa một dãy liên tục, em chọn `list` hay `vector`? Vì sao?"
    Mặc định `vector`. Big-O nói chèn giữa `list` là O(1) nhưng chỉ khi đã cầm iterator; đi tới vị trí vẫn là O(n) và mỗi bước là một lần nhảy qua heap, trong khi `vector` dời một khối byte liền nhau, được bộ nhớ đệm đón sẵn. Mình đã đo: chèn vị trí ngẫu nhiên 20000 phần tử, `list` chậm hơn hàng chục lần.

??? question "Thế nếu mình đã có sẵn iterator tới chỗ chèn thì sao?"
    Khi đó `list` hết phải đi tìm, mỗi lần chèn chỉ sửa hai con trỏ, và với n lớn nó thắng áp đảo (mình đo chèn 20000 lần vào cùng một chỗ giữa 100000 phần tử: `vector` chậm hơn 126 tới 162 lần). Nhưng với n nhỏ hay chủ yếu duyệt thì vẫn `vector`. Muốn chắc thì đo trên dữ liệu thật, với `-O2`.

??? question "`map` và `unordered_map` khác nhau thế nào? Rehash làm hỏng cái gì?"
    `map` là cây đỏ-đen: O(log n) luôn luôn, duyệt theo thứ tự khóa, có `lower_bound`/khoảng, khóa chỉ cần `operator<`. `unordered_map` là bảng băm: O(1) trung bình nhưng O(n) xấu nhất, không thứ tự, cần hàm băm và `operator==`. Chỉ tra/đếm thì `unordered_map`; cần thứ tự, khoảng, hoặc chặn trên thời gian xấu nhất thì `map`. Rehash vô hiệu hóa **iterator**, còn tham chiếu và con trỏ tới phần tử vẫn hợp lệ vì các nút không bị dời (mình đã chạy: giữ `&bang[13]`, chèn thêm 1000 khóa, địa chỉ vẫn đúng); biết trước cỡ thì `reserve`.

??? question "Dữ liệu nạp một lần rồi tra hàng triệu lần, em dùng gì?"
    Cần tra khớp đúng thì `unordered_map` hoặc vector đã sắp. Cần hỏi "phần tử đầu tiên không nhỏ hơn x" thì `vector` đã sắp + `std::lower_bound`: O(log n) như `map` nhưng nằm liền bộ nhớ, mình đo nhanh hơn `map` cỡ 4-6 lần với 200000 phần tử và tốn ít bộ nhớ hơn. Cái giá là chèn O(n), nên chỉ khi dữ liệu ít sửa.

??? question "Thiết kế một LRU cache, mỗi thao tác O(1)."
    Một `list` giữ các mục theo độ mới (đầu = mới nhất) và một `unordered_map` từ khóa tới iterator vào nút. `lay`: tra bảng băm, `splice` nút lên đầu. `dat` khi đầy: bỏ nút cuối và xóa khóa của nó khỏi bảng. Dùng `list` vì chuyển một nút không dời ai và iterator không hỏng; `vector`/`deque` thì chuyển phần tử giữa là O(n).

??? question "Vì sao không nên dùng `vector<bool>`? Và cần tra theo cả `id` lẫn `email` thì tổ chức dữ liệu thế nào?"
    `vector<bool>` nén mỗi phần tử thành một bit nên `v[i]` trả đối tượng đại diện chứ không phải `bool&`: không lấy được tham chiếu hay con trỏ, `auto x = v[i]; x = true;` sửa luôn phần tử, và hai luồng ghi hai phần tử khác nhau vẫn là data race (TSan báo); cần mảng cờ thì `vector<char>`. Tra theo nhiều khóa: giữ dữ liệu ở một `vector<NhanVien>`, mỗi khóa một chỉ mục `unordered_map<khóa, vị trí>`, lưu vị trí chứ không lưu con trỏ vì `vector` tái cấp phát làm con trỏ treo (mình chạy thử bản con trỏ: ASan báo `heap-use-after-free`). Nếu còn xóa nhân viên thì phải cập nhật mọi chỉ mục, hoặc đánh dấu "đã xóa".

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Chọn `list` vì 'chèn giữa O(1)'"
    Quên rằng phải đi tìm vị trí, và mỗi nút là một lần cấp phát nằm rải rác. Mình đã đo: chèn vị trí ngẫu nhiên thì `list` chậm hơn `vector` hàng chục lần ở 20000 phần tử. Chọn `list` chỉ khi đã cầm iterator, n lớn, cần địa chỉ ổn định.

!!! warning "Lỗi 2: Dùng `m[k]` để 'hỏi' có khóa hay không"
    `[]` tự chèn khóa mới, làm bảng phình ra và sai các phép đếm `size` (mình đã chạy: hai lần hỏi thêm hai khóa). Dùng `find`, `count`, `contains` hoặc `at`; trên map `const` thì `[]` còn không biên dịch được.

!!! warning "Lỗi 3: Đo hiệu năng mà không `-O2`, hoặc kết luận từ một lần đo"
    Không tối ưu thì chênh lệch duyệt `list`/`vector` rơi từ cỡ 16 lần xuống 1-2 lần (mình đã chạy). Luôn đo bằng `-O2`, nhiều lần, và kết luận bằng **tỉ lệ**, không bằng mili giây; số liệu bài này đổi theo máy.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="53" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Bạn đếm số lần xuất hiện của từng từ trong tệp 10 triệu từ. Kết quả chỉ cần số đếm, in ra thứ tự nào cũng được. Chọn container nào cho bảng đếm?

- `std::unordered_map<std::string, int>`, mỗi từ `++dem[tu]`
- `std::map<std::string, int>`, vì luôn có thứ tự nên luôn an toàn
- `std::vector<std::pair<std::string, int>>`, tìm tuyến tính từng từ
- `std::list<std::string>`, mỗi lần gặp từ thì thêm một nút

<p class="giai-thich" markdown>Chỉ cần tra và đếm theo khóa, không cần thứ tự, nên bảng băm cho O(1) trung bình là hợp nhất. `map` cũng cho kết quả đúng nhưng trả O(log n) và nút nặng cho thứ tự mà đề không cần. `vector` tìm tuyến tính phải lục cả bảng mỗi lần gặp từ nên thành O(n) mỗi từ. `list` chỉ ghi lại từ chứ không đếm được, và tìm trong đó cũng tuyến tính.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Đọc đoạn sau. `m` bắt đầu rỗng. Chương trình in gì?

```text
std::map<std::string, int> m;
if (m["a"] == 0) { std::cout << "khong co "; }
std::cout << m.size();
```

- `khong co 0`, vì `[]` chỉ đọc nên `m` vẫn rỗng
- `khong co 1`, vì `[]` chèn khóa `"a"` với giá trị `0`
- Ném ngoại lệ, vì khóa `"a"` không tồn tại trong `m`
- Không biên dịch được, vì `[]` không dùng được trên `map`

<p class="giai-thich" markdown>`m["a"]` không tìm thấy khóa nên **chèn** `"a"` với giá trị mặc định `0` rồi trả tham chiếu tới nó, vì vậy điều kiện đúng và `size()` thành 1. Coi `[]` như hàm chỉ đọc (cho `0` rồi `size` vẫn 0) là nhầm với `find`. Ném ngoại lệ là hành vi của `at`, không phải của `[]`. Còn biên dịch được: `[]` dùng bình thường trên `map` không `const`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Bạn nạp một lần 100000 số vào bộ nhớ rồi không sửa nữa. Sau đó có hàng triệu câu hỏi dạng "số nhỏ nhất trong dữ liệu mà không nhỏ hơn x là số nào?". Cách nào vừa đúng vừa hợp lý nhất?

- `std::unordered_set<int>`, vì tra O(1) nên nhanh nhất
- `std::list<int>` đã sắp, vì chèn khi nạp O(1)
- `std::vector<int>` đã sắp, hỏi bằng `std::lower_bound`
- `std::vector<int>` chưa sắp, duyệt tuyến tính mỗi câu hỏi

<p class="giai-thich" markdown>Câu hỏi "không nhỏ hơn x" là hỏi theo thứ tự, và dữ liệu không đổi nên vector đã sắp cùng `lower_bound` trả lời trong O(log n), trên bộ nhớ liền. `unordered_set` không giữ thứ tự nên không biết "số kế tiếp", và O(1) chỉ có ích cho khớp đúng. `list` đã sắp vẫn phải đi từng nút để tìm vị trí, nên mỗi câu hỏi thành O(n). Vector chưa sắp mà duyệt tuyến tính thì cũng O(n) mỗi câu, nhân với hàng triệu câu là quá chậm.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn sau. Chương trình in gì?

```text
std::vector<bool> b(2, false);
auto x = b[1];
x = true;
std::cout << b[1] << b[0];
```

- `00`, vì `x` là bản sao nên `b` không đổi
- `01`, vì `b[1]` in sau `b[0]`
- Không biên dịch được, vì `auto` không đoán được kiểu của `b[1]`
- `10`, vì `x` là đối tượng đại diện nên sửa `x` là sửa `b[1]`

<p class="giai-thich" markdown>`vector<bool>` nén mỗi phần tử thành một bit nên `b[1]` trả một đối tượng đại diện nhớ "bit nào", không phải `bool` thật. `auto x` chép chính đối tượng đại diện đó, và `x = true` ghi vào bit của `b[1]`; in `b[1]` rồi `b[0]` ra `1` và `0`, tức `10`. Phương án "bản sao" đúng với `vector<char>` chứ không đúng ở đây. `auto` đoán được kiểu (đối tượng đại diện) nên vẫn biên dịch. Còn `01` đảo thứ tự: câu lệnh in `b[1]` trước.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Bạn cần cache LRU giữ tối đa N mục: `lay` một khóa và "đưa nó lên đầu", hoặc thêm mục mới và bỏ mục lâu không dùng nhất, đều phải O(1). Cấu trúc nào đúng?

- `std::vector` giữ theo thứ tự dùng, chuyển mục lên đầu bằng `erase` rồi `insert`
- `std::list` giữ theo thứ tự dùng, kèm `unordered_map` từ khóa tới iterator
- `std::map` có khóa là thời điểm dùng, tra khóa gốc bằng cách duyệt
- `std::deque` kèm `unordered_map` giữ iterator, chuyển mục bằng `erase` và `push_front`

<p class="giai-thich" markdown>`list` cho phép chuyển một nút lên đầu bằng `splice` mà không dời nút nào, và iterator của nó không hỏng khi thêm hay xóa nút khác, nên bảng băm giữ iterator vẫn đúng và mọi thao tác O(1). `vector` phải dời phần tử khi `erase` và `insert`, nên mỗi lần là O(n). `map` theo thời điểm dùng thì tra theo khóa gốc phải duyệt, hoặc thêm một bảng phụ mà vẫn O(log n). `deque` xóa giữa là O(n) và `erase` ở giữa làm iterator hỏng, nên bảng iterator không còn đáng tin.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. Dòng `for` chắc chắn làm `unordered_map` rehash. Chương trình in gì?

```text
std::unordered_map<int,int> m = {{1, 10}};
int* p = &m[1];
for (int k = 100; k < 1100; ++k) m[k] = k;
std::cout << *p;
```

- Không xác định, vì rehash làm mọi con trỏ tới phần tử hỏng
- Một số rác, vì phần tử bị dời sang bảng hộp mới
- Không biên dịch được, vì không lấy được địa chỉ của `m[1]`
- `10`, vì rehash làm hỏng iterator chứ không làm hỏng con trỏ

<p class="giai-thich" markdown>Chuẩn bảo đảm rehash chỉ vô hiệu hóa iterator, còn tham chiếu và con trỏ tới phần tử vẫn hợp lệ vì các nút không bị dời, chỉ các hộp được xây lại; nên `*p` vẫn là 10. Nói "mọi con trỏ đều hỏng" là nhầm với `vector` tái cấp phát, nơi con trỏ cũ mới thật sự treo. Địa chỉ của `m[1]` lấy được bình thường vì `m[1]` là một giá trị có địa chỉ, nên biên dịch không có vấn đề.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Bạn nhận một luồng 10 triệu số và chỉ cần 10 số lớn nhất, bộ nhớ phải nhỏ. Cách nào đúng?

- `std::priority_queue` min-heap cỡ 10, quá 10 thì bỏ `top()` là số nhỏ nhất
- `std::priority_queue<int>` mặc định cỡ 10, quá 10 thì `pop()` bỏ `top()`
- `std::vector<int>` chứa mọi số rồi `sort`, lấy 10 số cuối
- `std::set<int>` chứa cả luồng, rồi lấy 10 phần tử cuối

<p class="giai-thich" markdown>Min-heap cỡ K giữ K số lớn nhất đã thấy: số mới vào, rồi nếu quá K thì bỏ số **nhỏ nhất** ở đỉnh, nên mỗi số tốn O(log K) và bộ nhớ chỉ K. `priority_queue` mặc định là max-heap nên bỏ `top()` là bỏ số lớn nhất, ra 10 số **nhỏ** nhất. Hai cách còn lại cho kết quả đúng nhưng giữ cả 10 triệu số, vi phạm yêu cầu bộ nhớ nhỏ.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Chọn container theo **mẫu truy cập** (tra theo khóa? cần thứ tự? hai đầu? chèn giữa?), kèm cột "khi nào KHÔNG dùng"; mặc định `vector`, đổi khi có lý do và **đo** bằng `-O2` rồi kết luận bằng tỉ lệ, không bằng mili giây.
2. Big-O chưa đủ: hằng số ẩn là số lần cấp phát, bộ nhớ thêm mỗi phần tử (nút `map` có 32 byte đầu nút) và tính cục bộ của bộ nhớ đệm. Mình đo: chèn vị trí ngẫu nhiên `list` chậm hơn `vector` hàng chục lần, duyệt chậm cỡ 16 lần; `list` chỉ thắng khi đã cầm iterator, n lớn, cần địa chỉ ổn định (đo được `vector` chậm hơn 100 lần ở ca đó).
3. `map` (cây đỏ-đen): O(log n) luôn luôn, có thứ tự, `lower_bound`/khoảng, tham chiếu và iterator ổn định. `unordered_map`: O(1) trung bình, O(n) xấu nhất (hàm băm tệ dồn vào một hộp: mình đo chậm cỡ trăm lần), không thứ tự; rehash làm hỏng iterator nhưng không làm hỏng tham chiếu/con trỏ; `reserve` tránh rehash. `m[k]` tự chèn nên dùng `find`/`count`/`at` để hỏi.
4. `deque` cho hai đầu; `vector<bool>` là bẫy (đối tượng đại diện, `auto x = v[i]` sửa được phần tử, data race giữa hai phần tử), dùng `vector<char>`. Dữ liệu ít sửa thì **vector đã sắp + `lower_bound`** thay `map` (mình đo nhanh hơn cỡ 4-6 lần); `reserve` khi biết cỡ.
5. Mười tình huống có đáp án: đếm tần suất (`unordered_map`), LRU (`list` + `unordered_map` giữ iterator, `splice`), hàng đợi (`queue`/`deque`), đồ thị (`vector<vector<int>>`), top-K (min-heap), đã thấy (`unordered_set`), nhiều khóa (một `vector` + chỉ mục lưu **chỉ số**), bảng giá nạp một lần (vector đã sắp), lịch sự kiện (`map` + `lower_bound`), cửa sổ trượt (`deque`). Go chỉ có slice và map băm, và đọc khóa thiếu của map Go không chèn.
