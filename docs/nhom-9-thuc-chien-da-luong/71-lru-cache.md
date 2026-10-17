# Bài 71 — Thực chiến: LRU cache an toàn luồng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một LRU cache `get`/`put` O(1) bằng `list` + `unordered_map` giữ iterator, đủ cả các trường hợp biên người phỏng vấn hay thử: khóa đã có, sức chứa 0, hết hạn (TTL).
    - Nói được vì sao `get` cũng phải khóa (nó **sắp xếp lại** danh sách, tức là ghi) và vì sao `shared_mutex` không cứu được; thấy bằng TSan và bằng lần chạy thật chuyện gì xảy ra nếu "chỉ đọc nên không khóa".
    - Chọn giữa **một khóa** và **chia shard**, biết cái giá phải trả (LRU thành xấp xỉ, khóa nóng, `size()` không là ảnh chụp), và biết trả **bản sao** chứ không trả tham chiếu ra khỏi khóa.
    - Kiểm tra đúng bằng test tất định (kể cả TTL bằng đồng hồ giả) và bằng nhiều luồng kèm TSan; trả lời được các câu nối tiếp "thế nếu hàm tải chậm", "thế nếu 64 luồng".

**Bạn cần biết trước:** [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`list`), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`unordered_map`, `find`), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator bị vô hiệu), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`std::optional`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `std::chrono`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (bất biến của lớp, `inline static`), [Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md) (ý tưởng LRU một luồng) và [Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md) (chia shard, khóa).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đưa bút: "Viết cho anh một LRU cache. `get` và `put`, cả hai O(1), sức chứa cố định." Bạn nhớ [Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md) và vẽ `list` cộng `unordered_map`. Anh gật đầu, rồi hỏi tiếp: "Giờ tám luồng cùng dùng nó. `get` chỉ đọc thôi, em có cần khóa không?"

Quay lại **nhà bếp nhiều đầu bếp**. Cache là **kệ gia vị gần bếp**, chỉ đặt vừa ba lọ. Quy tắc: lọ nào vừa dùng thì đặt lên **đầu kệ**; hết chỗ thì bỏ lọ ở **cuối kệ** (lâu không đụng nhất) xuống kho. Chỉ **lấy** lọ muối ra dùng cũng là **dời** nó lên đầu kệ, tức là đụng vào kệ chung. Đó là toàn bộ bài này: khi nhiều đầu bếp cùng tới, "chỉ lấy" không còn là chỉ nhìn.

!!! info "Chỗ nào ví von kệ gia vị không còn đúng?"
    Chương trình có thêm một **sổ tra** (bảng băm) ghi "lọ muối đang ở ô nào"; sổ và kệ phải luôn khớp nhau, và đây là chỗ hay hỏng. Đầu bếp thật thấy hai người cùng với tay vào một ô sẽ nhường nhau, còn chương trình thì không tự nhường.

## 📖 Giải thích

[Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md) đã nhắc ý tưởng LRU một luồng cho `int`, với hàm `lay`/`dat` và giả định khóa chưa có. Ở đây ta đặt tên `get`/`put` như đề phỏng vấn và viết đầy đủ (khóa tùy ý, `optional`, hết hạn, khóa đã có, sức chứa 0) rồi làm nó an toàn luồng. Ta làm hai đề.

### Đề 1: LRU cache một luồng

**Đề.** Viết lớp `LruCache<K, V>` với sức chứa `n` cố định.

- `std::optional<V> get(const K&)`: trả giá trị nếu có (và đánh dấu "vừa dùng"), không thì `nullopt`.
- `void put(const K&, V, ttl)`: ghi khóa; nếu khóa đã có thì ghi đè; nếu cache đầy thì bỏ mục **lâu không dùng nhất**. `ttl` tùy chọn: sau từng ấy mili giây (tính từ lúc `put`, `get` không gia hạn) mục coi như hết hạn.
- `get` và `put` đều **O(1) trung bình**. Sức chứa 0 phải không sập.

**Đầu vào/ra:** một chuỗi lệnh `put`/`get`; ra là giá trị hoặc "không có". Thứ tự các mục (mới nhất tới cũ nhất) phải kiểm tra được.

??? tip "Gợi ý 1"
    Cần hai việc O(1): **tìm theo khóa** và **tìm mục cũ nhất để bỏ, đưa mục vừa dùng lên đầu**. Cấu trúc nào giỏi việc nào? Một cấu trúc làm cả hai thì không có, nên cần hai cấu trúc.

??? tip "Gợi ý 2"
    Giữ các mục theo thứ tự "mới dùng" trong một `list` (đầu = mới nhất, cuối = cũ nhất). Bảng băm cho phép tra theo khóa, nhưng tra ra cái gì để nhảy thẳng tới nút trong `list` mà không phải đi tìm? Hãy lưu **iterator vào nút** làm giá trị trong bảng.

??? tip "Gợi ý 3"
    Đưa một nút lên đầu không cần chép: `list::splice` chỉ sửa con trỏ liên kết, iterator của nút vẫn đúng. Khi đầy, nút cuối là nạn nhân và phải xóa khỏi **cả** `list` **lẫn** bảng. Đừng quên hai trường hợp biên: `put` khóa đã có (không được thêm nút thứ hai) và sức chứa 0.

**Phân tích hướng giải.** Hai cấu trúc phải luôn khớp nhau. Đó là **bất biến** ([Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) của lớp này, và hầu hết lỗi trên bảng trắng là làm vỡ nó.

| Bất biến | Nghĩa | Hàm nào dễ làm vỡ |
|---|---|---|
| I1 | Mỗi nút trong `list` có **đúng một** khóa trong bảng trỏ tới nó, và ngược lại | `put` khóa đã có; bỏ nút cuối mà quên xóa khóa |
| I2 | `size() <= sức chứa` | `put` khi sức chứa 0 |
| I3 | Đầu `list` là mục dùng gần nhất | `get` quên `splice` |

Vì sao `list` mà không phải `vector`/`deque`? Chuyển một phần tử giữa lên đầu của `vector` là O(n) và dời mọi phần tử, nên iterator lưu trong bảng hỏng hết. `list::splice` thì không dời ai: chuẩn bảo đảm iterator và tham chiếu tới nút được chuyển **vẫn hợp lệ** (chúng chỉ nay nằm ở vị trí mới). Còn `erase` rồi `push_front` thì nút cũ bị hủy, iterator trong bảng treo. Ta sẽ thấy điều này chạy thật ở mục 💻.

### Đề 2: bọc mutex, chia shard, TTL

**Đề.** Cho 8 luồng dùng chung một cache. Giữ `get`/`put` đúng và không có data race.

- Phương án 1: **một khóa** bảo vệ cả cache. Giải thích vì sao `get` cũng phải khóa.
- Phương án 2: **chia shard**: `N` cache nhỏ, mỗi cái một khóa riêng, băm khóa để chọn shard. Nêu cái giá phải trả.
- TTL tùy chọn đã nằm trong đề 1; kiểm hết hạn bằng test tất định, không dùng `sleep`.

**Đầu vào/ra:** nhiều luồng gọi `get`/`put` đồng thời; ra là giá trị đúng như một chuỗi lệnh tuần tự nào đó.

**Ràng buộc kiểm tra:** kết quả phải đúng ở mọi lần chạy (số lần trúng khi cache đủ chỗ, giá trị luôn khớp khóa, `size` không vượt sức chứa) và TSan sạch.

??? tip "Gợi ý 1"
    Với mỗi hàm public, hỏi: nó chỉ đọc, hay có đổi `list` hoặc bảng? Hỏi riêng cho `get`: sau khi tìm thấy, nó làm gì với nút?

??? tip "Gợi ý 2"
    `list` và bảng phải đổi **cùng nhau** (bất biến I1), nên chúng phải nằm dưới **cùng một** mutex. Và giá trị trả về phải được **chép ra trong khóa**: nếu trả tham chiếu, luồng khác có thể đẩy mục đó ra ngay sau khi bạn nhả khóa.

??? tip "Gợi ý 3"
    Một mutex duy nhất thành nút cổ chai khi nhiều luồng. Chia thành `N` cache nhỏ theo `hash(khoa) % N`: hai luồng đụng hai khóa ở hai shard thì không chờ nhau. Ai trả giá? Hãy nghĩ tới sức chứa của từng shard.

**Phân tích hướng giải.**

- **`get` là ghi.** Nó gọi `splice` nên sửa con trỏ liên kết của `list`. Hai luồng cùng `get` mà không loại trừ nhau là hai luồng cùng sửa `list`: data race, hành vi không xác định ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).
- **`shared_mutex` không giúp.** Nó cho nhiều luồng **đọc** cùng lúc, nhưng ở đây mọi `get` đều ghi. Dùng `shared_lock` trong `get` là data race (ta chạy thật bên dưới).
- **Chia shard** giảm tranh chấp nhưng đổi hợp đồng: mỗi shard tự chạy LRU trên phần của nó, nên **cache tổng không còn là LRU chính xác**. Bảng so sánh:

| | Một khóa | Chia `N` shard |
|---|---|---|
| Đúng LRU toàn cục | Có | Không (xấp xỉ: mục bị bỏ là cũ nhất **trong shard**) |
| Tranh chấp khóa | Cao khi nhiều luồng | Thấp nếu khóa trải đều |
| Khóa nóng (một khóa nhận hầu hết lượt) | Không khác | Không giúp được: vẫn dồn vào một shard |
| `size()` toàn cache | Chính xác | Cộng từng shard, không là ảnh chụp một thời điểm |
| Bộ nhớ thêm | Một khóa | `N` khóa và `N` bảng |

**Chi phí.** `get`/`put` O(1) trung bình (O(n) xấu nhất nếu bảng băm va chạm nặng, [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)). Mỗi mục tốn một nút `list` (hai con trỏ liên kết cộng dữ liệu) và một nút bảng băm: cache nhỏ-mà-nhiều-mục thì phần phụ này lớn hơn dữ liệu. Mỗi thao tác chạm vài vùng nhớ rải rác nên không nhanh theo kiểu `vector`.

## 💻 Ví dụ code

### Lời giải đề 1: `LruCache` một luồng

Bốn điều cần biết trước khi đọc:

- `typename DanhSach::iterator`: `DanhSach` phụ thuộc vào tham số template nên trình biên dịch chưa biết `::iterator` là kiểu hay giá trị; `typename` báo "đây là kiểu".
- `Clock` là tham số template: kiểu đồng hồ có `now()`, `duration`, `time_point`. Mặc định là `steady_clock` thật; test dùng **đồng hồ giả** `DongHoGia`, có biến `static inline bayGio` (một bản chung cho cả lớp, [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) mà `now()` trả về và test tự cộng số vào, khỏi `sleep`. [Bài 74](74-timer-rate-limiter.md) dùng lại ý này.
- `std::chrono::time_point::max()` là thời điểm xa nhất, ta dùng làm "không bao giờ hết hạn".
- `duyet(f)` gọi `f(khoa, giaTri)` cho từng mục từ mới tới cũ; `f` là lambda nào cũng được (`template <class F>`).

```cpp
#include <chrono>
#include <iostream>
#include <list>
#include <optional>
#include <unordered_map>

template <class K, class V, class Clock = std::chrono::steady_clock>
class LruCache {
    struct Nut {                                          // một mục của cache
        K khoa;
        V giaTri;
        typename Clock::time_point hetHan;                // time_point::max() = không hết hạn
    };
    using DanhSach = std::list<Nut>;

public:
    explicit LruCache(std::size_t sucChua) : sucChua_(sucChua) {}

    std::optional<V> get(const K& khoa) {
        auto it = tra_.find(khoa);
        if (it == tra_.end()) return std::nullopt;                    // trượt (miss)
        if (Clock::now() >= it->second->hetHan) {                     // (1) hết hạn: xóa rồi coi như trượt
            thu_.erase(it->second);
            tra_.erase(it);
            return std::nullopt;
        }
        thu_.splice(thu_.begin(), thu_, it->second);                  // (2) đưa nút lên đầu
        return it->second->giaTri;                                    // (3) trả BẢN SAO
    }

    void put(const K& khoa, V giaTri, std::chrono::milliseconds ttl = std::chrono::milliseconds(0)) {
        if (sucChua_ == 0) return;                                    // (4) cache sức chứa 0: không giữ gì
        auto het = ttl.count() > 0 ? Clock::now() + ttl : Clock::time_point::max();
        auto it = tra_.find(khoa);
        if (it != tra_.end()) {                                       // (5) khóa ĐÃ có: ghi đè rồi đưa lên đầu
            it->second->giaTri = std::move(giaTri);
            it->second->hetHan = het;
            thu_.splice(thu_.begin(), thu_, it->second);
            return;
        }
        if (thu_.size() == sucChua_) {                                // (6) đầy: bỏ nút cuối VÀ khóa của nó trong bảng
            tra_.erase(thu_.back().khoa);
            thu_.pop_back();
        }
        thu_.push_front(Nut{khoa, std::move(giaTri), het});           // (7) nút mới vào đầu
        tra_[khoa] = thu_.begin();                                    // (8) ghi nhớ iterator tới nút
    }

    std::size_t size() const { return thu_.size(); }

    template <class F>
    void duyet(F f) const {                                           // từ mới dùng nhất tới lâu nhất
        for (const Nut& n : thu_) f(n.khoa, n.giaTri);
    }

private:
    std::size_t sucChua_;
    DanhSach thu_;                                                    // đầu = mới dùng nhất
    std::unordered_map<K, typename DanhSach::iterator> tra_;
};

// Đồng hồ giả: thời gian chỉ nhích khi ta bảo, nên test hết hạn không cần ngủ.
struct DongHoGia {
    using duration = std::chrono::milliseconds;
    using time_point = std::chrono::time_point<DongHoGia, duration>;
    static inline time_point bayGio{};
    static time_point now() { return bayGio; }
};

template <class C>
void inThuTu(const char* nhan, const C& c) {
    std::cout << nhan << ": ";
    c.duyet([](int k, int v) { std::cout << k << "=" << v << " "; });
    std::cout << "\n";
}

int main() {
    LruCache<int, int> c(3);
    c.put(1, 10); c.put(2, 20); c.put(3, 30);
    inThuTu("sau put 1,2,3", c);
    std::cout << "get(1) = " << c.get(1).value_or(-1) << "\n";
    inThuTu("sau get(1)   ", c);
    c.put(4, 40);
    inThuTu("sau put(4)   ", c);
    std::cout << "get(2) = " << c.get(2).value_or(-1) << " (bi bo)\n";

    c.put(3, 33);                                            // khóa đã có: ghi đè, không thêm nút
    inThuTu("sau put(3,33)", c);
    std::cout << "size = " << c.size() << "\n";

    LruCache<int, int> khong(0);
    khong.put(1, 1);
    std::cout << "suc chua 0: size = " << khong.size() << ", get(1) co gia tri: " << khong.get(1).has_value() << "\n";

    LruCache<int, int, DongHoGia> t(3);
    t.put(7, 70, std::chrono::milliseconds(100));
    t.put(8, 80);
    DongHoGia::bayGio += std::chrono::milliseconds(99);
    std::cout << "t=99ms:  get(7) = " << t.get(7).value_or(-1) << "\n";
    DongHoGia::bayGio += std::chrono::milliseconds(1);
    std::cout << "t=100ms: get(7) = " << t.get(7).value_or(-1) << ", size = " << t.size() << "\n";
    std::cout << "khong TTL: get(8) = " << t.get(8).value_or(-1) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `thu_` (đầu -> cuối) |
|---|---|---|
| `put` 1, 2, 3 | Khóa chưa có (5) nên đi tiếp; chưa đầy nên bỏ qua (6); mục mới vào đầu (7) và bảng ghi iterator (8) | `3 2 1` |
| `get(1)` | Tìm thấy; `hetHan` là `max()` nên (1) không chạy; (2) `splice` đưa nút lên đầu; (3) trả bản sao `10` | `1 3 2` |
| `put(4)` | Đầy (3 mục): (6) lấy khóa của nút cuối (là 2), xóa khỏi bảng rồi `pop_back`; (7)(8) thêm 4 | `4 1 3` |
| `get(2)` | Bảng không còn khóa 2 nên `nullopt`; `value_or(-1)` cho `-1` | `4 1 3` |
| `put(3, 33)` | (5) khóa đã có: ghi đè giá trị, `splice` lên đầu, **không thêm nút** | `3 4 1` |
| `khong(0)` | (4) sức chứa 0: `return` ngay, không đụng `back()` của `list` rỗng | rỗng |
| Đồng hồ giả | `put(7, 70, 100ms)` đặt `hetHan = 0+100`; `put(8, 80)` không TTL. Tới 99 ms `now() < hetHan` nên trúng; tới 100 ms `now() >= hetHan`: (1) xóa cả nút lẫn bảng, `size` còn 1 | `8` |

**Kết quả khi chạy** (nhiều lần liền đều như nhau):

```text
sau put 1,2,3: 3=30 2=20 1=10 
get(1) = 10
sau get(1)   : 1=10 3=30 2=20 
sau put(4)   : 4=40 1=10 3=30 
get(2) = -1 (bi bo)
sau put(3,33): 3=33 4=40 1=10 
size = 3
suc chua 0: size = 0, get(1) co gia tri: 0
t=99ms:  get(7) = 70
t=100ms: get(7) = -1, size = 1
khong TTL: get(8) = 80
```

**Thử thay đổi 1: bỏ khối (5)** (`put` không kiểm khóa đã có). Mình đã chạy với `LruCache` rút gọn kiểu `int`: sau `put(1,10)`, `put(1,11)` có `size = 2` nhưng bảng chỉ có 1 khóa (hai nút cho một khóa, bất biến I1 vỡ). Sau `put(2,20)`, nút cũ `1:10` bị bỏ và nó **xóa luôn khóa 1** khỏi bảng dù nút `1:11` còn sống: `get(1)` trả `-1` thay vì `11`.

```cpp
// bo-qua-kiem-tra
// Ban SAI: put khong hoi "khoa da co chua?"
void put(int khoa, int giaTri) {
    if (thu_.size() == sucChua_) { tra_.erase(thu_.back().first); thu_.pop_back(); }
    thu_.push_front({khoa, giaTri});
    tra_[khoa] = thu_.begin();           // khoa cu van con mot nut "mo coi" trong thu_
}
```

**Thử thay đổi 2: bỏ `tra_.erase(...)` ở (6)** (bỏ nút khỏi `list` nhưng quên xóa khóa trong bảng). Sau `put` 1, 2, 3 với sức chứa 2, bảng còn giữ iterator tới nút đã bị giải phóng. `get(1)` đi qua iterator treo: chạy thường in `get(1) = 30` (rác, hên xui, **không bảo đảm**); ASan báo `heap-use-after-free ... READ of size 8` ngay ở dòng (1), nơi `get` đọc `hetHan` của nút đã giải phóng (với bản rút gọn không có TTL, lỗi hiện ra ở `list::splice`).

**Thử thay đổi 3: bỏ dòng (4).** `put` thấy `size() == 0 == sucChua_` rồi gọi `thu_.back()` trên `list` rỗng (hành vi không xác định). Mình đã chạy: chết với `free(): invalid pointer`; ASan báo `attempting free on address which was not malloc()-ed`.

### Vì sao `splice` giữ được iterator

Chương trình nhỏ dưới đây cho thấy iterator và địa chỉ của nút **không đổi** sau khi nối nút lên đầu. `std::next(l.begin(), 2)` nhích iterator hai bước ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)).

```cpp
#include <iostream>
#include <iterator>
#include <list>

int main() {
    std::list<int> l = {1, 2, 3};
    auto it = std::next(l.begin(), 2);          // it trỏ nút chứa 3
    const int* p = &*it;                        // địa chỉ của chính nút đó
    l.splice(l.begin(), l, it);                 // nối nút 3 lên đầu: chỉ sửa con trỏ liên kết
    std::cout << "thu tu: ";
    for (int x : l) std::cout << x << " ";
    std::cout << "\n*it = " << *it << ", it == begin: " << (it == l.begin())
              << ", cung dia chi: " << (p == &*it) << "\n";
    return 0;
}
```

**Kết quả khi chạy:**

```text
thu tu: 3 1 2 
*it = 3, it == begin: 1, cung dia chi: 1
```

Dòng cuối nói rõ ba điều: `it` vẫn trỏ nút chứa 3, nay `it == l.begin()`, và địa chỉ nút vẫn là địa chỉ cũ. Nhờ vậy giá trị `iterator` cất trong `tra_` vẫn đúng sau mọi `splice`. Bảng băm rehash cũng không sao: rehash làm hỏng iterator **của chính bảng băm**, còn thứ ta cất bên trong nó là iterator của `list`, và nút `list` không bị rehash động tới.

### Lời giải đề 2: một khóa, chia shard, và kiểm nhiều luồng

Lõi giữ nguyên đề 1 (đã bỏ `duyet`), chỉ thêm một mutex và ba dòng khóa (đánh dấu `// +`). Ba điều cần biết:

- `mutable std::mutex m_`: `mutable` cho phép hàm `const` (như `size() const`) vẫn khóa/nhả `m_`, vì khóa không phải một phần "giá trị" của cache.
- `LruShard` giữ `vector<unique_ptr<LruCache>>` vì `std::mutex` không chép được cũng không di chuyển được, nên `LruCache` cũng vậy; `unique_ptr` giữ chúng ở heap, và khi `vector` cần nở thêm thì nó chỉ **chuyển** các con trỏ sang chỗ mới.
- `Hash{}(khoa)` tạo một hàm băm tạm rồi gọi nó (`std::hash<K>` là một **functor**: lớp có `operator()`, [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md)); `% N` chọn shard.

```cpp
#include <chrono>
#include <functional>
#include <iostream>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <thread>
#include <unordered_map>
#include <vector>

// Lõi của đề 1, thêm một mutex m_ và ba dòng khóa đánh dấu "// +" (bỏ hàm duyet cho gọn).
template <class K, class V, class Clock = std::chrono::steady_clock>
class LruCache {
    struct Nut { K khoa; V giaTri; typename Clock::time_point hetHan; };
    using DanhSach = std::list<Nut>;

public:
    explicit LruCache(std::size_t sucChua) : sucChua_(sucChua) {}

    std::optional<V> get(const K& khoa) {
        std::lock_guard<std::mutex> giu(m_);                          // + get cũng KHÓA: nó đổi thứ tự list
        auto it = tra_.find(khoa);
        if (it == tra_.end()) return std::nullopt;
        if (Clock::now() >= it->second->hetHan) {
            thu_.erase(it->second);
            tra_.erase(it);
            return std::nullopt;
        }
        thu_.splice(thu_.begin(), thu_, it->second);
        return it->second->giaTri;                                    // bản sao, chép TRONG khóa
    }

    void put(const K& khoa, V giaTri, std::chrono::milliseconds ttl = std::chrono::milliseconds(0)) {
        std::lock_guard<std::mutex> giu(m_);                          // +
        if (sucChua_ == 0) return;
        auto het = ttl.count() > 0 ? Clock::now() + ttl : Clock::time_point::max();
        auto it = tra_.find(khoa);
        if (it != tra_.end()) {
            it->second->giaTri = std::move(giaTri);
            it->second->hetHan = het;
            thu_.splice(thu_.begin(), thu_, it->second);
            return;
        }
        if (thu_.size() == sucChua_) {
            tra_.erase(thu_.back().khoa);
            thu_.pop_back();
        }
        thu_.push_front(Nut{khoa, std::move(giaTri), het});
        tra_[khoa] = thu_.begin();
    }

    std::size_t size() const {
        std::lock_guard<std::mutex> giu(m_);                          // +
        return thu_.size();
    }

private:
    std::size_t sucChua_;
    DanhSach thu_;
    std::unordered_map<K, typename DanhSach::iterator> tra_;
    mutable std::mutex m_;                                            // + một khóa bảo vệ CẢ thu_ lẫn tra_
};

// Chia shard: N cache nhỏ, mỗi cái một khóa riêng; hàm băm chọn shard.
template <class K, class V, class Hash = std::hash<K>>
class LruShard {
public:
    LruShard(std::size_t tongSucChua, std::size_t soShard) {
        std::size_t moiShard = (tongSucChua + soShard - 1) / soShard;  // chia lên, mỗi shard giữ moiShard mục
        for (std::size_t i = 0; i < soShard; ++i)
            cacShard_.push_back(std::make_unique<LruCache<K, V>>(moiShard));
    }
    std::optional<V> get(const K& khoa) { return chon(khoa).get(khoa); }
    void put(const K& khoa, V giaTri, std::chrono::milliseconds ttl = std::chrono::milliseconds(0)) {
        chon(khoa).put(khoa, std::move(giaTri), ttl);                  // chuyển tiếp ttl cho shard
    }
    std::size_t size() const {                                         // KHÔNG phải ảnh chụp một thời điểm
        std::size_t tong = 0;
        for (const auto& s : cacShard_) tong += s->size();
        return tong;
    }
private:
    LruCache<K, V>& chon(const K& khoa) { return *cacShard_[Hash{}(khoa) % cacShard_.size()]; }
    std::vector<std::unique_ptr<LruCache<K, V>>> cacShard_;            // unique_ptr vì mutex không chép/di chuyển được
};

// Chạy viec(t) trên soLuong luồng (t = 0..soLuong-1), đợi xong; mỗi luồng tự ghi vào ô riêng kq[t].
template <class F>
long long chayLuong(int soLuong, F viec) {
    std::vector<long long> kq(soLuong, 0);
    std::vector<std::thread> cacLuong;
    for (int t = 0; t < soLuong; ++t) cacLuong.emplace_back([&kq, &viec, t] { kq[t] = viec(t); });
    for (std::thread& th : cacLuong) th.join();
    long long tong = 0;
    for (long long x : kq) tong += x;
    return tong;
}

// Mỗi luồng một khoảng khóa riêng: put 100 khóa rồi get lại. Sức chứa dư nên MỌI get phải trúng.
template <class Cache>
long long thuDungSai(Cache& cache) {
    return chayLuong(8, [&cache](int t) {
        long long trung = 0;
        for (int k = t * 100; k < (t + 1) * 100; ++k) cache.put(k, k * 10);
        for (int k = t * 100; k < (t + 1) * 100; ++k) {
            auto r = cache.get(k);
            if (r && *r == k * 10) ++trung;
        }
        return trung;
    });
}

// Tranh giành thật: cache nhỏ, khóa chồng nhau, mục bị đẩy ra liên tục. Đếm lần "trúng mà giá trị sai".
template <class Cache>
long long thuTranhGianh(Cache& cache) {
    return chayLuong(8, [&cache](int t) {
        long long sai = 0;
        unsigned x = 12345u + 777u * t;                                // bộ sinh số giả riêng, tất định
        for (int i = 0; i < 5000; ++i) {
            x = x * 1103515245u + 12345u;
            int k = static_cast<int>((x >> 16) % 200);
            auto r = cache.get(k);
            if (!r) cache.put(k, k * 10);
            else if (*r != k * 10) ++sai;
        }
        return sai;
    });
}

struct BamChan { std::size_t operator()(int k) const { return static_cast<std::size_t>(k); } };

int main() {
    LruCache<int, int> mot(3200);
    LruShard<int, int> chia(3200, 8);
    std::cout << "doc ghi dung (can 800): mot khoa = " << thuDungSai(mot)
              << ", 8 shard = " << thuDungSai(chia) << "\n";

    LruCache<int, int> motNho(64);
    LruShard<int, int> chiaNho(64, 8);
    long long sai1 = thuTranhGianh(motNho);
    long long sai2 = thuTranhGianh(chiaNho);
    std::cout << "tranh gianh: gia tri sai = " << sai1 << " / " << sai2
              << ", size<=64: " << (motNho.size() <= 64) << " / " << (chiaNho.size() <= 64) << "\n";

    LruCache<int, int> toanCuc(4);
    LruShard<int, int, BamChan> haiShard(4, 2);                        // 2 shard x 2 mục; khóa chẵn cùng shard 0
    for (int k : {0, 2, 4}) { toanCuc.put(k, k); haiShard.put(k, k); }
    std::cout << "toan cuc: get(0) co = " << toanCuc.get(0).has_value()
              << ", 2 shard: get(0) co = " << haiShard.get(0).has_value()
              << " (size " << toanCuc.size() << " vs " << haiShard.size() << ")\n";
    return 0;
}
```

**Chạy từng dòng** (chỉ phần khác đề 1)

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| `lock_guard` ở `get`/`put`/`size` | Xin `m_` tới hết hàm, kể cả `return` sớm; `get` **cũng** khóa vì có `splice` | Một khóa bảo vệ cả `thu_` lẫn `tra_` |
| `return it->second->giaTri` | Trả `optional<V>` **chép trong khóa**: luồng khác đẩy mục ra sau đó cũng không sao | Trả tham chiếu hay con trỏ là bom nổ chậm |
| `LruShard`, `chon(khoa)` | Mỗi shard chứa `ceil(tổng/N)` mục (không chia hết thì tổng sức chứa thật nhỉnh hơn `tổng` một chút); `Hash{}(khoa) % N` chọn shard, mỗi thao tác chỉ khóa **một** shard | Hai khóa khác shard không chờ nhau |
| `chayLuong`, `thuDungSai` | Chạy hàm trên 8 luồng; mỗi luồng ghi kết quả vào ô `kq[t]` của mình, tổng cộng sau `join`. Mỗi luồng `put` rồi `get` lại 100 khóa riêng | Sức chứa dư (3200 cho 800 khóa) nên **mọi** `get` phải trúng: tổng đúng 800 |
| `thuTranhGianh` | 5000 thao tác mỗi luồng trên khóa 0..199, cache chỉ 64 chỗ nên mục bị đẩy liên tục; bộ sinh số giả riêng mỗi luồng (tất định) | Kiểm: trúng thì giá trị luôn `khóa x 10`, và `size <= 64` |
| `BamChan` + `haiShard` | Băm "chính khóa": khóa chẵn vào shard 0, lẻ vào shard 1. Sức chứa 4 chia 2 shard là 2 mục mỗi shard | `put` 0, 2, 4 đều vào shard 0 |

**Kết quả khi chạy** (5 lần liền cho cùng kết quả; biên dịch thêm `-fsanitize=thread` và chạy dưới `setarch x86_64 -R` 3 lần đều sạch, mã thoát 0):

```text
doc ghi dung (can 800): mot khoa = 800, 8 shard = 800
tranh gianh: gia tri sai = 0 / 0, size<=64: 1 / 1
toan cuc: get(0) co = 1, 2 shard: get(0) co = 0 (size 3 vs 2)
```

Dòng cuối là **cái giá của chia shard**: cache toàn cục sức chứa 4 giữ cả 3 khóa (`size 3`), còn 2 shard đã bỏ khóa 0 (`size 2`) dù cache tổng còn trống. Nó đã bỏ mục cũ nhất **của shard 0**, không phải cũ nhất toàn cục.

**Chuẩn nói gì, máy này cho gì.**

| Chuẩn C++ bảo đảm | g++ 11.4, 8 lõi, `-std=c++17` cho kết quả |
|---|---|
| Hai luồng cùng chạy `get` không loại trừ nhau là data race, **hành vi không xác định**: không hứa sập, không hứa sai | Bản `get` không khóa (bên dưới): 10 lần chạy thường, 8 lần `Segmentation fault` (mã 139), 2 lần `free(): invalid pointer` (mã 134); TSan báo ngay lần đầu. Máy khác có thể in kết quả sai hoặc treo |
| `list::splice` không vô hiệu iterator/tham chiếu tới nút được nối | Chương trình `c.cpp` ở trên: iterator và địa chỉ vẫn nguyên |

Chuẩn cũng không bắt `std::hash<int>` phân phối đều, nên bài không dựa vào nó: `thuDungSai` chừa dư sức chứa, còn ví dụ cần shard chính xác dùng `BamChan` tự viết.

### Ba bản sai điển hình của đề 2

**Bản sai A: "`get` chỉ đọc nên không khóa".** Xóa đúng một dòng `std::lock_guard` ở đầu `get` rồi chạy lại chương trình trên. Mình đã chạy 10 lần (bản thường): 8 lần `Segmentation fault`, 2 lần `free(): invalid pointer`, không lần nào ra kết quả. Dưới TSan, cảnh báo đầu tiên (rút gọn) cho thấy đúng thủ phạm:

```text
WARNING: ThreadSanitizer: data race
  Read of size 8 at 0x7fffffffd2e8 by thread T2 (mutexes: write M11):
    #2 std::list<...>::size() const
    #3 LruCache<int, int, ...>::put(...)
  Previous write of size 8 at 0x7fffffffd2e8 by thread T1:
    #1 std::list<...>::splice(...)
    #3 LruCache<int, int, ...>::get(...)
```

Chú ý `(mutexes: write M11)` ở bên `put` và **không có mutex nào** ở bên `get`: `put` thì khóa đúng, nhưng `get` ghi vào `list` mà không giữ gì. Một bên khóa không cứu được: khóa chỉ có tác dụng khi **mọi** bên cùng giữ nó.

```cpp
// bo-qua-kiem-tra
// Ban SAI A: "get chi doc nen khong can khoa"
std::optional<V> get(const K& khoa) {
    auto it = tra_.find(khoa);                 // doc bang trong luc luong khac dang put (rehash)
    if (it == tra_.end()) return std::nullopt;
    thu_.splice(thu_.begin(), thu_, it->second);   // GHI vao list ma khong giu khoa
    return it->second->giaTri;
}
```

**Bản sai B: `shared_mutex` với `shared_lock` ở `get`.** Nghe hợp lý ("đọc nhiều thì dùng khóa đọc"), nhưng `get` ghi. Mình đã đổi `m_` thành `std::shared_mutex`, `get` dùng `std::shared_lock`, `put`/`size` dùng `unique_lock`. Kết quả 6 lần chạy thường: 4 lần mã 134, 1 lần mã 139 và **1 lần mã 0** (UB không hứa sập, nên có lần may mắn không chết). TSan báo hai bên cùng giữ khóa đọc:

```text
  Read of size 8 ... by thread T2 (mutexes: read M11):
    #3 LruCache<...>::get(int const&)
  Previous write of size 8 ... by thread T3 (mutexes: read M11):
    #3 LruCache<...>::get(int const&)
```

**Bản sai C: `get` trả con trỏ (hay tham chiếu) vào nút.** Dù mọi thao tác đều khóa đúng, con trỏ trả ra sống lâu hơn khóa. Mình mô phỏng "luồng A lấy con trỏ, luồng B đẩy mục ra" bằng hai lệnh liên tiếp trong một luồng (không cần thật sự hai luồng để thấy lỗi):

```cpp
// bo-qua-kiem-tra
LruCon c(2);                                         // get tra const std::string* vao nut
c.put(1, std::string(40, 'a')); c.put(2, std::string(40, 'b'));
const std::string* p = c.get(1);                     // "luong A" lay con tro, nha khoa
c.put(3, "x"); c.put(4, "y");                        // "luong B" day muc 1 ra: nut bi giai phong
std::cout << *p << "\n";                             // "luong A" doc con tro cu
```

ASan báo `heap-use-after-free ... READ of size 40`, vùng nhớ "freed by" là destructor của `std::pair<int, std::string>` của nút bị bỏ; chạy thường thì in `y` (đọc rác ở vùng đã trả, **không bảo đảm**). Cách sửa là cách ta đã làm: trả **bản sao** chép ngay trong khóa.

### Chi phí: một khóa hay chia shard

Mình đo bằng một chương trình ngắn dùng lại hai lớp trên: 8 luồng, mỗi luồng 300 000 lần `get` (trượt thì `put`) trên 10 000 khóa ngẫu nhiên, sức chứa 8192. Với `-O2` (15 lần đo) chia 8 shard nhanh hơn một khóa **1,8 đến 2,6 lần**; với `-O0` (5 lần đo) chỉ **1,06 đến 1,52 lần**. Máy lúc đo đang bận nên số dao động, và mọi con số đổi theo máy, cờ tối ưu, số lõi và dạng tải: hãy tự đo. Chia shard giúp thật khi nhiều luồng và khóa trải đều, nhưng không giúp khi có khóa nóng.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết LRU cache với `get`/`put` O(1)."
    Một `list` giữ các mục theo độ mới (đầu = mới nhất) và một `unordered_map` từ khóa tới iterator vào nút. `get`: tra bảng, `splice` nút lên đầu, trả giá trị. `put`: nếu khóa có rồi thì ghi đè và `splice` lên đầu; nếu chưa có và đầy thì bỏ nút cuối **và** xóa khóa của nó khỏi bảng, rồi thêm nút mới vào đầu. Dùng `list` vì `splice` không dời ai và iterator không hỏng; `vector`/`deque` thì chuyển phần tử giữa là O(n). Nói luôn các trường hợp biên: `put` khóa trùng, sức chứa 0, và bất biến "list và bảng luôn khớp".

??? question "Bây giờ cho nhiều luồng dùng chung. `get` có cần khóa không? Dùng `shared_mutex` được không?"
    Cần, và **phải khóa độc quyền**: `get` gọi `splice` nên sửa danh sách; hai `get` đồng thời là data race (mình chạy: sập 10 trên 10 lần, TSan báo ngay). `shared_mutex` với `shared_lock` ở `get` cũng sai vì nó cho nhiều luồng vào cùng lúc, trong khi mọi `get` đều ghi (mình chạy: sập 5 trên 6 lần, TSan báo hai bên cùng giữ khóa đọc). Cách đúng: một `mutex` cho cả `list` và bảng, trả **bản sao** giá trị trong khóa.
    Nối tiếp: **"Một mutex nghẽn khi 64 luồng thì sao?"** Chia shard: `N` cache nhỏ, mỗi cái một khóa, chọn bằng `hash(khoa) % N` (thường chọn `N` cỡ vài lần số lõi, đo để chốt). Cái giá phải nói: LRU thành **xấp xỉ** (mỗi shard tự bỏ mục cũ nhất của nó), khóa nóng vẫn dồn vào một shard, và `size()` cộng từng shard không là ảnh chụp một thời điểm.

??? question "Hàm tải giá trị khi trượt mất một giây. Hai luồng cùng trượt một khóa thì sao?"
    Đừng giữ khóa lúc tải: một lần tải một giây sẽ chặn **mọi** luồng, kể cả những luồng chỉ cần mục khác. Cách thường dùng: nhả khóa, tải, khóa lại rồi `put`. Cái giá: hai luồng cùng trượt có thể cùng tải (tốn gấp đôi, người ta gọi là "cache stampede" khi nhiều luồng cùng ập vào một khóa vừa hết hạn). Muốn chỉ tải một lần thì giữ trong cache (hoặc một bảng riêng) một `shared_future` theo khóa: luồng đến sau thấy có người đang tải thì **chờ future đó** thay vì tải lại. Mình chỉ nêu hướng đi này bằng lời, chưa viết ở bài này.

??? question "TTL làm thế nào? Test hết hạn thế nào cho khỏi chậm và không chập chờn?"
    Lưu `hetHan` trong nút; `get` kiểm lười (lazy): thấy quá hạn thì xóa rồi coi như trượt. Mục hết hạn mà không ai hỏi vẫn chiếm chỗ cho tới khi bị đẩy ra, nên cache lớn có thể thêm một luồng quét nền; mình không làm ở đây. Test: truyền **đồng hồ giả** vào template (như `DongHoGia`), cộng số vào `bayGio` thay vì `sleep`: nhanh, tất định, kiểm được đúng mốc 99 ms còn trúng và 100 ms hết hạn. Dùng `steady_clock` (không `system_clock`, vì giờ hệ thống có thể bị chỉnh lùi).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Làm vỡ bất biến list/bảng khi viết trên bảng trắng"
    Hai chỗ hay quên: `put` khóa đã có (nút mồ côi, `get` sau đó trả `-1`) và bỏ nút cuối mà không `erase` khóa trong bảng (`heap-use-after-free`). Trước khi nói "xong", hỏi từng hàm: "sau hàm này `list` và bảng còn khớp không?".

!!! warning "Lỗi 2: Nói \"get chỉ đọc nên không khóa\" hoặc \"dùng shared_mutex cho nhanh\""
    Cả hai đều sai vì `get` **ghi** (`splice`). Câu đúng: "`get` đổi thứ tự nên cần khóa độc quyền; muốn nhanh hơn thì chia shard, không phải khóa đọc."

!!! warning "Lỗi 3: Trả tham chiếu/con trỏ ra khỏi khóa, hoặc giữ khóa lúc làm việc chậm"
    Con trỏ tới nút sống lâu hơn khóa nên luồng khác đẩy mục ra là `heap-use-after-free`; ngược lại, giữ khóa lúc tải chậm chặn cả cache. Trả bản sao trong khóa; việc chậm làm ngoài khóa.

!!! warning "Lỗi 4: Coi `size()` của cache chia shard là con số chính xác, hoặc kỳ vọng LRU toàn cục"
    `size()` cộng từng shard không là ảnh chụp một thời điểm, và mỗi shard tự bỏ mục cũ nhất của nó. Hãy nói rõ "xấp xỉ LRU" với người phỏng vấn thay vì để họ tự tìm ra.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="71" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Cache sức chứa 2, hàm `put` không kiểm khóa đã có (luôn thêm nút mới; khi đầy thì bỏ nút cuối **và** xóa khóa của nút đó khỏi bảng). Gọi lần lượt như dưới, `get(1)` cuối cùng trả gì?

```text
put(1, 10)
put(1, 11)
put(2, 20)
get(1)
```

- `11`, vì `put` sau cùng ghi đè giá trị cũ của khóa 1
- `10`, vì bảng vẫn nhớ nút `1:10` được thêm vào trước
- Trượt, dù giá trị 11 vẫn nằm trong danh sách
- Sập ngay ở `put(1, 11)` vì khóa 1 đã có trong bảng

<p class="giai-thich" markdown>`put(1, 11)` thêm nút thứ hai cho khóa 1 và bảng chỉ nhớ nút mới. Khi `put(2, 20)` làm đầy, nút cuối là `1:10`, và việc xóa "khóa của nút cuối" xóa luôn mục của khóa 1 trong bảng, dù nút `1:11` vẫn sống. Nên `get(1)` không tìm thấy gì. Nói trả `11` nhầm danh sách với bảng: ta tra qua bảng. Nói trả `10` hay sập đều không có cơ sở: không có lệnh nào truy cập vùng nhớ đã giải phóng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Vì sao `get` của LRU cache phải khóa độc quyền khi nhiều luồng dùng chung?

- Vì `get` gọi `splice` để đưa nút lên đầu, tức là sửa danh sách
- Vì `unordered_map::find` không an toàn khi nhiều luồng cùng gọi
- Vì chuẩn bắt mọi hàm public của một lớp phải tự khóa
- Vì `get` trả giá trị nên phải chặn luồng khác chép nó

<p class="giai-thich" markdown>Mỗi lần trúng, `get` sắp xếp lại danh sách để ghi nhận "vừa dùng", nên nó là một thao tác ghi, và hai thao tác ghi không loại trừ nhau là data race. Nhiều luồng cùng `find` trên bảng mà không ai sửa bảng là hợp lệ, nên lý do không nằm ở `find`. Chuẩn không có luật "hàm public phải tự khóa": đồng bộ do người viết lớp chọn. Còn việc chép giá trị không cần chặn ai nếu không có luồng nào đang ghi vào cùng chỗ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc cấu hình sau. Cache đã có dữ liệu; tám luồng cùng gọi `get` (đều trúng), không luồng nào gọi `put`. Điều gì đúng?

```text
std::shared_mutex m_;
get:  std::shared_lock<std::shared_mutex> giu(m_);  ... splice(...) ...
put:  std::unique_lock<std::shared_mutex> giu(m_);  ...
```

- An toàn, vì không có lệnh `put` nào nên không có ai ghi vào cache
- An toàn, vì mọi hàm đều giữ một loại khóa nào đó trong lúc chạy
- Chỉ lỗi khi hai luồng `get` cùng một khóa với nhau, khác khóa thì ổn
- Có data race: các `get` cùng giữ khóa đọc mà cùng sửa danh sách

<p class="giai-thich" markdown>`shared_lock` cho phép nhiều luồng vào cùng lúc, mà mỗi `get` trúng lại chạy `splice` để sửa danh sách; hai luồng sửa một danh sách cùng lúc là race (TSan báo cả hai bên đều `mutexes: read`). Nói "không ai ghi" quên rằng `get` chính là người ghi. Nói "đều giữ khóa nào đó" nhầm: khóa đọc không loại trừ nhau. Hai `get` ở hai khóa khác nhau vẫn cùng sửa con trỏ đầu danh sách và bộ đếm kích thước, nên không cần trùng khóa mới lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Cache sức chứa 4 chia 2 shard (mỗi shard 2 mục), shard chọn bằng `khoa % 2`. Gọi `put(0, a)`, `put(2, b)`, `put(4, c)` rồi `get(0)`. Một LRU toàn cục sức chứa 4 sẽ trúng. Cache chia shard cho kết quả nào?

- Trúng, vì tổng sức chứa cả cache là 4 nên vẫn còn dư chỗ
- Trượt, vì ba khóa chẵn cùng một shard chỉ chứa 2 mục
- Trượt, vì `get` luôn xóa mục đầu tiên mà nó tìm thấy trong shard
- Sập, vì shard 1 chưa có mục nào mà `get` đã chạy qua nó

<p class="giai-thich" markdown>Khóa chẵn đều vào shard 0, shard này chỉ chứa 2 mục, nên `put(4, c)` bỏ khóa 0 dù shard 1 còn trống. Đây là cái giá của chia shard: LRU thành xấp xỉ. "Tổng sức chứa còn dư" đúng với cache một khóa nhưng không phải với từng shard. `get` không xóa mục, chỉ đưa lên đầu. Shard rỗng là chuyện bình thường, không sinh lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Cache có nhiệm vụ tự gọi một hàm tải chậm cỡ một giây mỗi khi trượt (người gọi chỉ gọi `get`). Cách nào hợp lý nhất?

- Nhả khóa lúc tải, rồi khóa lại để `put`; chấp nhận có thể tải trùng
- Giữ khóa suốt lúc tải, để chắc chắn mỗi khóa chỉ được tải đúng một lần
- Tải không cần khóa, rồi ghi vào cache cũng không cần khóa vì việc tải đã xong
- Không tải trong `get`: trả lỗi và để người gọi tự `put` khi có dữ liệu

<p class="giai-thich" markdown>Giữ khóa lúc tải làm tất cả luồng khác, kể cả luồng cần mục khác, đứng chờ một giây; nên nhả khóa lúc tải rồi khóa lại để `put` (muốn tránh tải trùng thì thêm `shared_future` theo khóa). Giữ khóa suốt lúc tải bảo đảm tải một lần nhưng giết khả năng chạy song song. Ghi vào cache không khóa là data race dù hàm tải đã xong. Trả lỗi cho người gọi tự `put` đẩy gánh nặng sang mọi nơi gọi và vẫn phải khóa khi `put`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Đọc đoạn sau, với `l` là `std::list<int>` gồm `1 2 3`. Sau lệnh thứ hai, `*it` còn dùng được không?

```text
auto it = std::next(l.begin(), 2);
l.splice(l.begin(), l, it);
```

- Không, vì `splice` hủy nút cũ rồi tạo nút mới ở đầu danh sách
- Có, `it` vẫn trỏ nút chứa 3, nút này nay nằm ở đầu danh sách
- Có, nhưng `it` giờ trỏ nút đang ở vị trí thứ ba, tức nút chứa 2
- Không xác định được, vì chuẩn không nói gì về `splice` và iterator

<p class="giai-thich" markdown>`splice` chỉ nối lại con trỏ liên kết, không hủy hay chép nút, và chuẩn bảo đảm iterator tới phần tử được nối vẫn hợp lệ, nên `*it` vẫn là 3 và `it` bằng `l.begin()`. Nói nút bị hủy nhầm `splice` với `erase`. Iterator bám theo **nút**, không bám theo **vị trí**, nên nó không trỏ sang nút chứa 2. Chuẩn có nói rõ về `splice`; đó cũng là lý do cache LRU cất iterator trong bảng băm.</p>
</div>

</div>

## 🔑 Tóm tắt

1. LRU O(1) = `list` (đầu = mới dùng nhất) + `unordered_map` khóa → iterator vào nút; `get` dùng `splice` đưa nút lên đầu mà không chép và không làm hỏng iterator; khi đầy, bỏ nút cuối **và** khóa của nó. Bất biến "mỗi nút ↔ một khóa" là chỗ hay vỡ: `put` khóa trùng và quên `erase` bảng (mình chạy ra `get` trượt và `heap-use-after-free`), cộng thêm sức chứa 0.
2. `get` là **ghi** (nó `splice`), nên cần khóa độc quyền: bản "get không khóa" sập 10/10 lần chạy và TSan báo race; `shared_mutex` + `shared_lock` ở `get` cũng sai (sập 5/6 lần, TSan báo hai bên cùng giữ khóa đọc). Chuẩn chỉ nói "data race là UB", còn "sập" là điều máy này cho thấy chứ không phải lời hứa.
3. Trả **bản sao** giá trị chép trong khóa; trả con trỏ/tham chiếu vào nút là `heap-use-after-free` khi luồng khác đẩy mục ra; hàm tải chậm làm ngoài khóa (muốn gộp lần tải thì `shared_future` theo khóa).
4. Chia shard giảm tranh chấp (mình đo `-O2`: 1,8 đến 2,6 lần với 8 shard, 8 luồng, máy đang bận; `-O0` chỉ 1,06 đến 1,52) nhưng LRU thành xấp xỉ (ví dụ 2 shard bỏ khóa 0 trong khi tổng còn trống), khóa nóng vẫn dồn một shard, và `size()` cộng shard không là ảnh chụp một thời điểm.
5. TTL kiểm lười ở `get` bằng `hetHan` trong nút; test tất định bằng **đồng hồ giả** (cộng số, không `sleep`); chương trình kiểm nhiều luồng phải có đầu ra ổn định (tổng trúng đúng 800, giá trị luôn khớp khóa, `size <= sức chứa`) và sạch dưới TSan.
