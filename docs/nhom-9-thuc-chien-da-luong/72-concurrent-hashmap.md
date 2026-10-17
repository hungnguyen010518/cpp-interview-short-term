# Bài 72 — Thực chiến: concurrent hash map chia shard

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một `ShardedMap<K,V>` đúng: N shard, mỗi shard một mutex và một `unordered_map`, băm khóa để chọn shard; `put`, `get` (trả **bản sao**), `erase`, và biết vì sao không được trả tham chiếu hay con trỏ ra ngoài.
    - Thêm `compute` (tra, sửa, chèn nếu vắng trong **một** lần khóa) và thấy tận mắt vì sao "mỗi hàm tự khóa" vẫn sai: TSan sạch mà đếm thiếu.
    - Trả lời gọn các câu khó: vì sao `size()` và duyệt khó, ảnh chụp nhất quán giá bao nhiêu, rehash nằm ở đâu, đổi số shard khi đang chạy, `shared_mutex` mỗi shard.
    - Đưa số đo (tỉ lệ, khoảng) và nói được khi nào **không** nên chia shard.

**Bạn cần biết trước:** [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`unordered_map`, hàm băm, `m[k]` tự chèn), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`std::optional`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`, `shared_mutex`, bẫy trả tham chiếu), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, khóa theo thứ tự, gọi callback khi giữ khóa), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template lớp), [Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md) (chia shard lần đầu, ba luật của chuẩn, bốn kiểu khóa; bài này đào sâu, không lặp lại số đo ở đó).

## 🧠 Câu chuyện mở đầu

Phỏng vấn viên đẩy micro bút về phía bạn: "Viết cho tôi một concurrent hash map. Không dùng thư viện ngoài, ba mươi phút." Bạn vừa nghĩ tới `std::unordered_map` thì anh nói thêm: "Tám luồng cùng đọc ghi. Và tôi sẽ hỏi: `size()` của bạn trả gì khi đang có người ghi?"

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Tủ kho một chìa khóa thì đúng, nhưng tám đầu bếp xếp hàng trước **một** chìa. Cách chữa: đóng 16 tủ nhỏ, mỗi tủ một chìa riêng; nguyên liệu vào tủ nào do **mã số** của nó quyết định (hàm băm). Hai đầu bếp lấy hai nguyên liệu ở hai tủ khác nhau thì không chờ nhau.

!!! info "Chỗ nào ví von nhiều tủ không còn đúng?"
    Quản lý muốn **kiểm kê cả bếp** phải xin đủ 16 chìa, và trong lúc đó cả bếp đứng chờ; còn đi từng tủ đếm thì lúc đếm xong tủ cuối, tủ đầu đã khác. Ngoài ra bếp thật chuyển nguyên liệu sang tủ mới khi tăng số tủ, còn ở đây "tăng số tủ lúc đang nấu" nghĩa là xếp lại **mọi** nguyên liệu, nên khó hơn nhiều (mục 4).

## 📖 Giải thích

### 1. Đề 1: `ShardedMap` với `put`, `get`, `erase`

!!! example "Đề bài"
    Viết lớp mẫu `ShardedMap<K, V>`; dùng thư viện chuẩn, C++17. Số shard `N` cho lúc tạo, sau đó cố định. Ba hàm: `bool put(k, v)` (ghi đè nếu khóa có, trả `true` nếu là khóa **mới**), `std::optional<V> get(k) const` (rỗng nếu vắng), `bool erase(k)` (trả `true` nếu có khóa để xóa). Mọi tổ hợp lời gọi từ nhiều luồng phải an toàn. **Cấm** trả tham chiếu hoặc con trỏ vào bên trong bảng.
    **Ví dụ:** `put(7, 70)` trả `true`; `get(7)` ra `70`; `erase(7)` trả `true`; `get(7)` ra rỗng.

??? tip "Gợi ý 1"
    Một mutex quanh một `unordered_map` đã đúng. Vấn đề là chậm: tám luồng xếp hàng trước một khóa. Làm sao để hai khóa **khác nhau** không chờ nhau?

??? tip "Gợi ý 2"
    Dựng `N` bảng nhỏ, mỗi bảng một mutex. Một hàm của khóa chọn bảng nào, và **một khóa luôn vào cùng một bảng**. Mỗi thao tác chỉ khóa đúng bảng đó.

??? tip "Gợi ý 3"
    `get` trả `std::optional<V>` chứa bản sao. Muốn `get` là hàm `const` mà vẫn khóa được thì mutex phải `mutable`. `std::mutex` không chép và không chuyển được, nên giữ các shard trong `std::vector<Shard>(n)` (dựng sẵn `n` phần tử, không bao giờ nở thêm).

**Hướng giải.** Mỗi hàm chỉ động vào **một** shard, nên không bao giờ giữ hai khóa cùng lúc và không thể deadlock. Chi phí: `put`/`get`/`erase` trung bình O(1) cộng một lần băm và một lần khóa. Bộ nhớ thêm là `N` mutex và `N` bảng, không đáng kể. Hai luồng chỉ chờ nhau khi hai khóa **rơi vào cùng shard**; nếu khóa phân bố đều thì xác suất đó cỡ 1/N.

Ba chỗ cú pháp mới. `insert_or_assign(k, v)` (C++17) là "có khóa thì gán đè, chưa có thì chèn", trả một cặp mà `.second` là `true` khi **chèn mới**. `mutable` đặt trước một thành viên nghĩa là hàm `const` vẫn được sửa nó; khóa và nhả mutex là "sửa" mutex, nên cần chữ này. `std::hash<K>{}(k)` dựng bộ băm của `K` rồi gọi nó trên `k`, trả một số lớn ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)).

### 2. Đề 2: `compute`, đếm tần suất, `size`, ảnh chụp

!!! example "Đề bài"
    Mở rộng lớp trên. (1) `compute(k, f)`: gọi `f(V&)` trên giá trị của `k` **nguyên tử theo khóa** (khóa vắng thì dựng `V{}` trước). (2) Dùng nó để đếm tần suất 100000 từ (500 từ khác nhau, mỗi từ 200 lần) bằng 8 luồng; mỗi từ phải đúng 200. (3) `size()` và một ảnh chụp toàn bảng. (4) So một khóa với chia shard bằng tỉ lệ thời gian. (5) Bàn: rehash và đổi số shard có khó không. (6) Đọc nhiều ghi ít thì sao: `shared_mutex` mỗi shard?
    **Ràng buộc:** `compute` không được để hai luồng cùng cộng mất một lượt.

??? tip "Gợi ý 1"
    Thử viết "đếm" bằng `get` rồi `put`. Hai hàm đều đã khóa, vậy sai ở đâu? Cái gì xảy ra **giữa** hai lần khóa?

??? tip "Gợi ý 2"
    Gộp "tra, sửa, chèn nếu vắng" vào **một** lần khóa: hàm nhận một hàm `f` và gọi `f` ngay trong vùng găng, trên tham chiếu tới giá trị. Hàm `f` phải ngắn và **không được gọi ngược vào map**.

??? tip "Gợi ý 3"
    `size()`: khóa lần lượt từng shard cho ra tổng gần đúng, rẻ. Cần con số đúng ở một thời điểm: giữ **mọi** khóa cùng lúc, luôn theo chỉ số tăng dần. Ảnh chụp: làm cùng cách rồi **sao chép** ra, dùng ngoài khóa.

**Hướng giải, từng câu hỏi khó.**

| Hỏi | Trả lời ngắn | Chi phí |
|---|---|---|
| `compute` | Một lần khóa gộp tra + sửa; callback chạy trong vùng găng | O(1) + thời gian của `f` (cả shard chờ) |
| `size()` từng shard | Mỗi shard đúng lúc nó được đếm, tổng ghép lại **có thể chưa từng đúng** | `N` lần khóa, không chặn lâu |
| `sizeChinhXac()`, `chupAnh()` | Giữ mọi khóa theo thứ tự tăng, rồi đếm hoặc chép | cả bảng đứng yên; ảnh chụp thêm O(n) sao chép và bộ nhớ |
| rehash | Xảy ra **bên trong một shard**, dưới khóa của shard đó | O(n/N) mỗi lần, chỉ shard đó chờ |
| đổi số `N` | Khóa nào cũng đổi shard: phải giữ mọi khóa và xếp lại tất cả | O(n), cả bảng dừng |

**Duyệt và iterator.** Không có iterator đi ra ngoài `ShardedMap`: iterator của một shard hỏng khi shard đó rehash hay xóa, và khóa nhả thì không ai bảo vệ nó nữa ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), bẫy trả tham chiếu). Muốn duyệt thì lấy **ảnh chụp** (bản sao) hoặc đưa hàm `f` vào trong như `compute`.

**Rehash.** `unordered_map` rehash khi quá đầy ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)): xây lại mảng hộp, chuyển **mọi** nút, O(n), nên một lần chèn nào đó đột nhiên rất chậm. Chia shard cắt cái giá này thành `N` mảnh nhỏ và độc lập.

Mình đo một lần `rehash` gấp đôi số hộp: bảng 1 triệu phần tử cỡ 19 đến 35 ms, bảng 62500 phần tử (một shard trong 16) cỡ 0,5 ms, tỉ lệ **39 đến 60** (lớn hơn 16, có thể vì bảng nhỏ nằm gọn trong cache; đổi theo máy).

Thêm `reserve(n)` lúc dựng (đặt trước đủ hộp cho `n` phần tử, như `vector::reserve` ở [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)) để gần như khỏi rehash: chèn 1 triệu khóa, `bucket_count()` (số hộp hiện có) đổi **17 lần** khi không `reserve` và **0 lần** khi có (g++ 11 ở đây).

**Đổi số shard khi đang chạy.** Khó vì `chiSo(k)` của mọi khóa đổi theo `N` mới. Hai lối: (a) giữ mọi khóa, dựng bảng mới, xếp lại tất cả, rồi thả: đúng nhưng dừng cả bảng; (b) đặt mảng shard sau một khóa tổng `shared_mutex`, mọi thao tác phải xin khóa tổng ở chế độ chia sẻ, nên tự tạo một điểm tranh chấp chung. Cách phổ biến nhất trong phỏng vấn và trong thực tế: **chọn `N` một lần lúc dựng**, thường vài lần số lõi, và nói rõ giới hạn.

**`shared_mutex` mỗi shard.** Khi đọc áp đảo, `get` dùng `shared_lock`, ghi dùng `unique_lock`. Mình đo ở mục 💻 và kết quả không đẹp như nhiều người tưởng, nên **đo trước** mới đổi.

!!! info "Bạn biết Go?"
    Go không có map đồng thời trong ngôn ngữ; cách thường làm là `map` kèm `sync.RWMutex`, hoặc `sync.Map` cho hai kiểu dùng đặc biệt (tài liệu của nó nêu). Chia shard trong Go viết gần như y hệt: một mảng `[16]struct{ mu sync.Mutex; m map[K]V }`, băm khóa chọn phần tử mảng, `compute` là `mu.Lock(); m[k]++; mu.Unlock()`. Khác một chỗ: đọc `m[k]` khóa vắng trong Go **không** chèn gì cả, còn `m[k]` của C++ thì chèn ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)).

### 3. Chuẩn nói gì, máy này cho gì

| Chủ đề | Chuẩn C++ bảo đảm | g++ 11 trên máy này |
|---|---|---|
| Khóa đúng | Nhả mutex ở luồng trước *happens-before* xin mutex ở luồng sau: mọi lần ghi trong vùng găng hiện ra cho luồng sau | Mọi chương trình đúng dưới đây: TSan sạch |
| `std::hash<int>` | Không hứa phân bố đều | Trả chính số đó, nên khóa 0, 16, 32... với `N = 16` dồn hết vào shard 0 |
| Rehash | Iterator mất hiệu lực; con trỏ và tham chiếu tới **phần tử** vẫn dùng được, chỉ `erase` phần tử đó mới làm chúng hỏng | `bucket_count` từ 1 (bảng rỗng; 13 sau lần chèn đầu) lên 172933 sau 100000 lần chèn; con trỏ lấy từ đầu vẫn đọc đúng (ASan sạch) |
| Khóa lại mutex đang giữ | Hành vi không xác định | Treo (mục 💻, mã thoát 124) |
| `shared_mutex` | Nhiều người đọc cùng lúc; **không** nói ai được ưu tiên giữa đọc và ghi | Tỉ lệ thời gian ở mục 💻 |
| Thứ tự duyệt `unordered_map` | Không xác định | Không in ra, chỉ in tổng và số đếm |

### 4. Khi nào KHÔNG dùng `ShardedMap`

| Tình huống | Chọn | Vì sao |
|---|---|---|
| 1 đến 2 luồng, hoặc ghi thưa | Một `mutex` + `unordered_map` | Đơn giản, đủ nhanh; shard chỉ thêm chỗ sai |
| Nhiều luồng ghi **khóa khác nhau** | `ShardedMap` | Hai khóa khác shard không chờ nhau |
| Một khóa nóng (hầu hết lượt vào một khóa) | Không shard; cân nhắc `atomic` hoặc đếm cục bộ rồi gộp | Mọi lượt vào cùng một shard, như một khóa |
| Hay cần tổng hoặc duyệt toàn bảng | Một khóa, hoặc bảng sao chép khi ghi | Mỗi lần duyệt phải giữ mọi khóa |
| Bảng nhỏ, ghi cực hiếm | Sao chép khi ghi ([Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md)) | Đọc không chờ ai |

## 💻 Ví dụ code

### Lời giải đề 1: `ShardedMap`, kiểm bằng ghi, đọc và xóa đồng thời

Chương trình dựng bản đồ 16 shard, rồi chạy ba pha. Pha 1: bốn luồng ghi bốn khoảng khóa rời nhau, trong lúc hai luồng đọc liên tục và kiểm "đọc ra thì phải đúng giá trị". Pha 2: bốn luồng xóa mọi khóa chia hết cho 3. Cuối: luồng chính đối chiếu với đáp án tính tay.

```cpp
#include <atomic>
#include <cstddef>
#include <functional>
#include <iostream>
#include <mutex>
#include <optional>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

template <typename K, typename V>
class ShardedMap {
public:
    explicit ShardedMap(std::size_t soShard = 16) : cacShard(soShard) {}   // (1) N shard, N mutex, tạo xong là không đổi N

    bool put(const K& k, V v) {                                  // (2) true nếu là khóa mới
        Shard& s = chon(k);
        std::lock_guard<std::mutex> giu(s.khoa);                 // (3) chỉ khóa MỘT shard
        return s.bang.insert_or_assign(k, std::move(v)).second;
    }
    std::optional<V> get(const K& k) const {                     // (4) trả BẢN SAO, không trả tham chiếu
        const Shard& s = chon(k);
        std::lock_guard<std::mutex> giu(s.khoa);
        auto it = s.bang.find(k);
        if (it == s.bang.end()) return std::nullopt;
        return it->second;
    }
    bool erase(const K& k) {                                     // (5) true nếu có khóa để xóa
        Shard& s = chon(k);
        std::lock_guard<std::mutex> giu(s.khoa);
        return s.bang.erase(k) == 1;
    }

private:
    struct Shard {
        mutable std::mutex khoa;                                 // (6) mutable: hàm const vẫn khóa được
        std::unordered_map<K, V> bang;
    };
    const Shard& chon(const K& k) const { return cacShard[std::hash<K>{}(k) % cacShard.size()]; }
    Shard& chon(const K& k) { return cacShard[std::hash<K>{}(k) % cacShard.size()]; }   // (7) băm khóa, chia lấy dư
    std::vector<Shard> cacShard;
};

int main() {
    ShardedMap<int, int> m(16);
    const int SO_LUONG = 4, MOI_LUONG = 1000;
    std::vector<int> moi(SO_LUONG, 0), xoa(SO_LUONG, 0);
    std::atomic<int> docSai{0};
    std::atomic<bool> xong{false};

    std::vector<std::thread> docGia;                             // (8) 2 luồng đọc chạy suốt lúc ghi
    for (int r = 0; r < 2; ++r) {
        docGia.emplace_back([&] {
            while (!xong) {
                for (int k = 0; k < SO_LUONG * MOI_LUONG; k += 7) {
                    std::optional<int> v = m.get(k);
                    if (v && *v != k * 2) ++docSai;              // (9) đọc được thì phải đúng giá trị
                }
            }
        });
    }
    std::vector<std::thread> ghi;
    for (int t = 0; t < SO_LUONG; ++t) {
        ghi.emplace_back([&, t] {
            for (int k = t * MOI_LUONG; k < (t + 1) * MOI_LUONG; ++k)
                if (m.put(k, k * 2)) ++moi[t];                   // (10) mỗi luồng một khoảng khóa riêng
        });
    }
    for (std::thread& t : ghi) t.join();

    ghi.clear();                                                 // (11) pha 2: xóa mọi khóa chia hết cho 3
    for (int t = 0; t < SO_LUONG; ++t) {
        ghi.emplace_back([&, t] {
            for (int k = t * MOI_LUONG; k < (t + 1) * MOI_LUONG; ++k)
                if (k % 3 == 0 && m.erase(k)) ++xoa[t];
        });
    }
    for (std::thread& t : ghi) t.join();
    xong = true;
    for (std::thread& t : docGia) t.join();

    int tongMoi = 0, tongXoa = 0, conLai = 0, lech = 0;
    for (int t = 0; t < SO_LUONG; ++t) { tongMoi += moi[t]; tongXoa += xoa[t]; }
    for (int k = 0; k < SO_LUONG * MOI_LUONG; ++k) {
        std::optional<int> v = m.get(k);
        if (v) ++conLai;
        if (v.has_value() != (k % 3 != 0)) ++lech;               // (12) còn đúng khi k % 3 != 0
    }
    std::cout << "chen moi: " << tongMoi << ", xoa duoc: " << tongXoa << "\n";
    std::cout << "con lai: " << conLai << ", sai lech: " << lech << ", doc sai: " << docSai.load() << "\n";
    std::cout << "get(4) co gia tri? " << m.get(4).has_value() << ", get(3) co gia tri? " << m.get(3).has_value() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Dựng `N = 16` shard; mỗi shard một mutex và một bảng rỗng | 16 cặp (khóa, bảng), `N` không đổi nữa |
| (7) | Băm khóa rồi chia lấy dư `N` chọn shard; cùng khóa luôn cùng shard | `put(5)` và `get(5)` luôn tới cùng một shard |
| (3) | Khóa **một** shard trong lúc ghi; 15 shard kia vẫn rảnh | 1 khóa bị giữ |
| (4) | Trả `optional<V>` chứa **bản sao**; khóa nhả khi hàm trả về, nên bên ngoài không còn dính tới bảng | không con trỏ nào thoát ra |
| (8), (9) | Hai luồng đọc liên tục; nếu đọc ra được giá trị thì phải đúng `2k` | `docSai` phải còn 0 |
| (10) | Luồng `t` chỉ ghi khoảng khóa của riêng nó nhưng các khóa vẫn rải đều ra mọi shard | luồng khác nhau, shard trùng nhau vẫn an toàn nhờ khóa |
| (11), (12) | Pha 2 xóa; cuối cùng đúng các khóa chia hết cho 3 đã mất | còn 2666 khóa |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
chen moi: 4000, xoa duoc: 1334
con lai: 2666, sai lech: 0, doc sai: 0
get(4) co gia tri? 1, get(3) co gia tri? 0
```

Con số tính tay: 4000 khóa, trong 0 đến 3999 có 1334 số chia hết cho 3, còn lại 2666. Thứ tự các luồng không đổi các số này.

**Thử thay đổi: xóa dòng (3)** (bỏ `lock_guard` trong `put`). Mình đã chạy 5 lần: 4 lần chương trình chết (`core dumped`), 1 lần in `doc sai: 1`. TSan báo `data race` trong `_M_rehash_aux` của `hashtable.h`: hai luồng cùng chèn vào một `unordered_map` làm hỏng bảng băm.

**Bản SAI điển hình: `get` trả con trỏ vào bảng.** Trên bảng trắng nhiều người viết `const V* get(k)` vì "đỡ sao chép". Khóa nhả ở cuối hàm, con trỏ thì sống tiếp:

```cpp
// bo-qua-kiem-tra
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <vector>

class MapSai {
public:
    void put(int k, int v) {
        std::lock_guard<std::mutex> giu(khoa);
        bang[k] = v;
    }
    const int* get(int k) {                                      // (1) SAI: trả con trỏ vào phần tử đang nằm trong bảng
        std::lock_guard<std::mutex> giu(khoa);
        auto it = bang.find(k);
        return it == bang.end() ? nullptr : &it->second;
    }                                                            // (2) khóa nhả ở đây, con trỏ thì sống tiếp
    void erase(int k) {
        std::lock_guard<std::mutex> giu(khoa);
        bang.erase(k);
    }
private:
    std::mutex khoa;
    std::unordered_map<int, int> bang;
};

int main() {
    MapSai m;
    m.put(7, 70);
    const int* p = m.get(7);                                     // (3) luồng A lấy con trỏ
    std::thread b([&m] { m.erase(7); });                         // (4) luồng B xóa khóa đó (đúng luật khóa)
    b.join();
    std::cout << "doc qua p: " << *p << "\n";                    // (5) nút đã bị giải phóng
    return 0;
}
```

Chạy trần mình được `doc qua p: 24205` (một số rác, máy bạn ra số khác hoặc sập). Với `-fsanitize=address`: `heap-use-after-free`, `READ of size 4`, `located 12 bytes inside of 16-byte region` (cả nút băm 16 byte, giá trị nằm ở byte thứ 12) và `freed by thread T1 here: ... MapSai::erase`. TSan cũng báo `heap-use-after-free` và ghi bên xóa đang `mutexes: write M...`: **bên xóa giữ khóa đúng luật**, bên đọc lại không giữ gì. Khóa chỉ xếp hàng các lời gọi hàm, không bảo vệ địa chỉ đã lấy ra ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Lời sửa là `get` trả bản sao, hoặc đưa việc cần làm vào trong lớp (như `compute`).

### Lời giải đề 2: `compute`, `size` đúng và gần đúng, ảnh chụp, `shared_mutex`

Bản mở rộng khác bản đầu ở vài chỗ, kèm cú pháp mới:

- Tham số mẫu thứ ba `Mutex` cho chọn `std::mutex` hay `std::shared_mutex`. `std::is_same_v<A, B>` là `true` nếu hai kiểu giống nhau; `std::conditional_t<điều kiện, A, B>` là kiểu `A` nếu điều kiện đúng, kiểu `B` nếu sai. Dòng (1) dùng cả hai để `get` lấy `shared_lock` khi mutex hỗ trợ và `unique_lock` khi không.
- `std::vector<KhoaDoc>` giữ **nhiều** khóa cùng lúc (mỗi `unique_lock`/`shared_lock` chuyển được nhưng không chép được).
- Dòng (9) trộn bit: `0x9E3779B97F4A7C15ull` là một hằng số 64 bit viết hệ 16 (`ull` = `unsigned long long`, hợp với kiểu `std::uint64_t` của `h`). Nhân với nó làm các bit của mã băm lẫn vào nhau, rồi `h >> 32` (dịch phải 32 bit) lấy nửa cao làm số đem chia lấy dư.
- Mục (14) cố ý cho khóa toàn bội của số shard.

```cpp
#include <algorithm>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iostream>
#include <mutex>
#include <optional>
#include <shared_mutex>
#include <string>
#include <thread>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

template <typename K, typename V, typename Mutex = std::mutex>
class ShardedMap {
    using KhoaDoc = std::conditional_t<std::is_same_v<Mutex, std::shared_mutex>,
                                       std::shared_lock<Mutex>, std::unique_lock<Mutex>>;   // (1) đọc: chia sẻ nếu mutex hỗ trợ
public:
    explicit ShardedMap(std::size_t soShard = 16, std::size_t duKien = 0) : cacShard(soShard) {
        for (Shard& s : cacShard) s.bang.reserve(duKien / soShard + 1);   // (2) đặt trước chỗ: ít rehash trong lúc chạy
    }
    bool put(const K& k, V v) {
        Shard& s = chon(k);
        std::lock_guard<Mutex> giu(s.khoa);
        return s.bang.insert_or_assign(k, std::move(v)).second;
    }
    std::optional<V> get(const K& k) const {
        const Shard& s = chon(k);
        KhoaDoc giu(s.khoa);
        auto it = s.bang.find(k);
        if (it == s.bang.end()) return std::nullopt;
        return it->second;
    }
    bool erase(const K& k) {
        Shard& s = chon(k);
        std::lock_guard<Mutex> giu(s.khoa);
        return s.bang.erase(k) == 1;
    }
    template <typename F>
    void compute(const K& k, F f) {                              // (3) tra + sửa + chèn nếu vắng: MỘT lần khóa
        Shard& s = chon(k);
        std::lock_guard<Mutex> giu(s.khoa);
        f(s.bang[k]);                                            // (4) f sửa trực tiếp V&; khóa vắng thì V{} được chèn trước
    }
    std::vector<std::size_t> kichThuoc() const {                 // (5) cỡ từng shard, mỗi shard đọc vào lúc riêng
        std::vector<std::size_t> kq;
        for (const Shard& s : cacShard) { KhoaDoc giu(s.khoa); kq.push_back(s.bang.size()); }
        return kq;
    }
    std::size_t size() const {                                   // (6) tổng GẦN ĐÚNG khi đang có người ghi
        std::size_t n = 0;
        for (std::size_t x : kichThuoc()) n += x;
        return n;
    }
    std::size_t sizeChinhXac() const {                           // (7) giữ MỌI shard cùng lúc rồi mới đếm
        std::vector<KhoaDoc> giuHet = khoaHet();
        std::size_t n = 0;
        for (const Shard& s : cacShard) n += s.bang.size();
        return n;
    }
    std::vector<std::pair<K, V>> chupAnh() const {               // (8) ảnh chụp nhất quán: sao chép ra rồi dùng ngoài khóa
        std::vector<KhoaDoc> giuHet = khoaHet();
        std::vector<std::pair<K, V>> kq;
        for (const Shard& s : cacShard) kq.insert(kq.end(), s.bang.begin(), s.bang.end());
        return kq;
    }

private:
    struct Shard {
        mutable Mutex khoa;
        std::unordered_map<K, V> bang;
    };
    std::size_t chiSo(const K& k) const {
        std::uint64_t h = std::hash<K>{}(k) * 0x9E3779B97F4A7C15ull;   // (9) trộn bit: khóa 0, 16, 32... không dồn vào một shard
        return static_cast<std::size_t>(h >> 32) % cacShard.size();
    }
    const Shard& chon(const K& k) const { return cacShard[chiSo(k)]; }
    Shard& chon(const K& k) { return cacShard[chiSo(k)]; }
    std::vector<KhoaDoc> khoaHet() const {                       // (10) luôn khóa theo chỉ số tăng dần: không deadlock với nhau
        std::vector<KhoaDoc> v;
        for (const Shard& s : cacShard) v.emplace_back(s.khoa);
        return v;
    }
    std::vector<Shard> cacShard;
};

template <typename Map>
bool demTu(Map& m, const std::vector<std::string>& kho, int soLuong) {
    std::vector<std::thread> cacLuong;
    int phan = static_cast<int>(kho.size()) / soLuong;
    for (int t = 0; t < soLuong; ++t) {
        cacLuong.emplace_back([&m, &kho, t, phan] {
            for (int i = t * phan; i < (t + 1) * phan; ++i)
                m.compute(kho[i], [](int& n) { ++n; });          // (11) "cộng 1 cho từ này" nguyên tử theo khóa
        });
    }
    for (std::thread& t : cacLuong) t.join();
    bool dung = m.size() == 500;
    for (int i = 0; i < 500; ++i) {
        std::optional<int> n = m.get("tu" + std::to_string(i));
        if (!n || *n != 200) dung = false;
    }
    return dung;
}

int main() {
    std::vector<std::string> kho;                                // 100000 từ: 500 từ khác nhau, mỗi từ 200 lần
    for (int i = 0; i < 100000; ++i) kho.push_back("tu" + std::to_string(i % 500));
    ShardedMap<std::string, int> a(16, 500);
    ShardedMap<std::string, int, std::shared_mutex> b(16, 500);
    std::cout << "dem tu (mutex):        " << demTu(a, kho, 8) << ", size = " << a.size() << "\n";
    std::cout << "dem tu (shared_mutex): " << demTu(b, kho, 8) << ", size = " << b.size() << "\n";

    ShardedMap<int, int> w(64);                                  // (12) cửa sổ trượt: luôn đúng 10 hoặc 11 khóa
    for (int i = 0; i < 10; ++i) w.put(i, i);
    std::atomic<bool> xong{false};
    std::thread ghi([&] {
        for (int i = 10; i < 20000; ++i) { w.put(i, i); w.erase(i - 10); }
        xong = true;
    });
    bool trongKhoang = true;
    do {                                                         // (13) đọc liên tục trong lúc luồng ghi chạy
        std::size_t n = w.sizeChinhXac();
        if (n < 10 || n > 11) trongKhoang = false;
    } while (!xong);
    ghi.join();
    std::cout << "sizeChinhXac luon trong [10, 11]? " << trongKhoang << "\n";
    auto anh = w.chupAnh();
    std::cout << "cuoi cung: size = " << w.size() << ", anh co " << anh.size() << " khoa\n";

    ShardedMap<int, int> day(16);                                // (14) khóa 0, 16, 32, ...: bội của số shard
    for (int i = 0; i < 16000; i += 16) day.put(i, i);
    std::size_t lonNhat = 0;
    for (std::size_t x : day.kichThuoc()) lonNhat = std::max(lonNhat, x);
    std::cout << "1000 khoa boi cua 16, shard lon nhat <= 2 lan trung binh? " << (lonNhat <= 2 * (1000 / 16)) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | `reserve` đặt trước chỗ cho mỗi shard | ít rehash trong lúc chạy |
| (3), (4) | Khóa **một** lần, `s.bang[k]` chèn `V{}` nếu vắng, rồi `f` sửa trực tiếp | giá trị thay đổi trong vùng găng, không luồng nào chen giữa |
| (11) | 8 luồng gọi `compute(từ, ++n)`, mỗi từ cuối cùng đúng 200 | `size() == 500` sau `join` |
| (10) | `khoaHet` xin khóa theo chỉ số 0, 1, 2... luôn tăng dần | hai luồng gọi `khoaHet` không thể chờ vòng tròn |
| (7) | `sizeChinhXac` giữ mọi khóa rồi mới đếm | ghi chờ; kết quả là số thật ở một thời điểm |
| (12), (13) | Một luồng ghi giữ "cửa sổ trượt": `put(i)` rồi `erase(i-10)`, nên thật sự luôn 10 hoặc 11 khóa | `sizeChinhXac` phải luôn trong [10, 11] |
| (9), (14) | Trộn bit trước khi chia: khóa 0, 16, 32... rải đều, không dồn shard 0 | shard lớn nhất không quá 2 lần trung bình |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
dem tu (mutex):        1, size = 500
dem tu (shared_mutex): 1, size = 500
sizeChinhXac luon trong [10, 11]? 1
cuoi cung: size = 10, anh co 10 khoa
1000 khoa boi cua 16, shard lon nhat <= 2 lan trung binh? 1
```

**Thử thay đổi 1: ở dòng (13) đổi `sizeChinhXac()` thành `size()`** (khóa từng shard). Mình đã chạy 10 lần (5 không tối ưu, 5 với `-O2`): 8 lần có ít nhất một lần đọc ra ngoài [10, 11], từ 1 đến 6 lần trên vài trăm đến vài nghìn lần đọc, và có lần đọc ra **9**, có lần ra **12**. Hai con số chưa từng đúng ở thời điểm nào. TSan vẫn sạch: từng shard đọc đúng luật, chỉ có phép cộng là không nhất quán.

**Thử thay đổi 2: ở (9) bỏ phép nhân** (chỉ còn `std::hash<K>{}(k) % cacShard.size()`). Mình đã chạy: dòng cuối in `0`, tức shard lớn nhất vượt 2 lần trung bình, vì `std::hash<int>` ở g++ trả chính số đó và mọi khóa bội của 16 chia 16 đều dư 0, nên **cả 1000 khóa vào shard 0**. Bảng vẫn đúng, chỉ là mười sáu shard thành một.

**Bản SAI 1: "kiểm rồi làm" bằng `get` rồi `put`.** Mỗi hàm tự khóa nên người viết yên tâm. Nhưng khóa nhả giữa hai dòng:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

class BangSai {                                                  // mỗi hàm TỰ khóa, nhưng "đọc rồi ghi" là hai lần khóa
public:
    std::optional<int> get(const std::string& k) {
        std::lock_guard<std::mutex> giu(khoa);
        auto it = bang.find(k);
        if (it == bang.end()) return std::nullopt;
        return it->second;
    }
    void put(const std::string& k, int v) {
        std::lock_guard<std::mutex> giu(khoa);
        bang[k] = v;
    }
    std::mutex khoa;
    std::unordered_map<std::string, int> bang;
};

int main() {
    std::vector<std::string> kho;
    for (int i = 0; i < 100000; ++i) kho.push_back("tu" + std::to_string(i % 500));
    BangSai m;
    std::vector<std::thread> cacLuong;
    for (int t = 0; t < 8; ++t) {
        cacLuong.emplace_back([&m, &kho, t] {
            for (int i = t * 12500; i < (t + 1) * 12500; ++i) {
                std::optional<int> n = m.get(kho[i]);            // (1) khóa, đọc, NHẢ khóa
                m.put(kho[i], n ? *n + 1 : 1);                   // (2) luồng khác có thể đã cộng ở giữa (1) và (2)
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();
    long tong = 0;
    for (const auto& kv : m.bang) tong += kv.second;
    std::cout << "tong luot dem = " << tong << " (mong doi 100000)\n";
    return 0;
}
```

Mình chạy 5 lần: `99342`, `99737`, `99393`, `99468`, `99513` (mong đợi 100000). TSan chạy 3 lần: **sạch cả ba**, không một cảnh báo. Đây là **race condition** chứ không phải data race ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)): mọi truy cập đều có khóa, nhưng hai luồng cùng đọc `n = 5` rồi cùng ghi `6`, mất một lượt. Công cụ không bắt được; chỉ có suy luận ("giữa hai lần khóa ai chen vào được?") bắt được. Lời sửa chính là `compute`.

**Bản SAI 2: callback gọi ngược vào map.** `f` chạy khi đang giữ khóa của shard. Nếu `f` lại gọi `get` mà khóa rơi vào **cùng shard**, luồng xin lại đúng mutex nó đang giữ. Để thấy rõ nhất, ví dụ dưới rút gọn còn một shard:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <optional>
#include <unordered_map>

class MotShard {                                                 // rút gọn: một shard duy nhất, để thấy lỗi gọn nhất
public:
    template <typename F>
    void compute(int k, F f) {
        std::lock_guard<std::mutex> giu(khoa);
        f(bang[k]);                                              // (1) f chạy KHI ĐANG giữ khóa
    }
    std::optional<int> get(int k) {
        std::lock_guard<std::mutex> giu(khoa);                   // (3) xin lại đúng cái khóa mình đang giữ
        auto it = bang.find(k);
        if (it == bang.end()) return std::nullopt;
        return it->second;
    }
private:
    std::mutex khoa;
    std::unordered_map<int, int> bang;
};

int main() {
    MotShard m;
    m.compute(1, [&m](int& n) {
        n = m.get(2).value_or(0) + 1;                            // (2) callback gọi ngược vào map
    });
    std::cout << "xong\n";
    return 0;
}
```

Chạy trần với `timeout 5`: **treo, mã thoát 124**, không in `xong`. Chạy với TSan cũng treo, mã 124, và mình **không** thấy cảnh báo nào trong 5 giây. Chuẩn nói khóa lại `std::mutex` đang giữ là hành vi không xác định; glibc ở đây chọn treo. Với 16 shard thì lỗi **lúc có lúc không** (chỉ treo khi hai khóa trùng shard), và còn tệ hơn: callback gọi vào shard khác thì hai luồng gọi ngược chiều nhau có thể deadlock chéo ([Bài 26](../nhom-3-da-luong/26-deadlock.md)). Quy tắc: `f` ngắn, thuần túy, không gọi lại map.

### Đo: chia shard và `shared_mutex` có đáng không

Mình viết bản đo ngoài bộ kiểm tự động (cùng lớp ở trên, `steady_clock` bọc quanh phần đếm, 8 luồng, 5 lần mỗi cấu hình, in ra tỉ lệ hai thời gian; máy 8 lõi và có tiến trình khác chạy cùng nên số khá nhiễu). Số đổi theo máy và cờ biên dịch; hãy tự đo.

**Chia shard** (đếm 500 từ, mỗi luồng 400000 lần `compute`), tỉ lệ thời gian của **1 shard** chia thời gian của **N shard** (lớn hơn 1: N shard nhanh hơn):

| `N` | không tối ưu | `-O2` |
|---|---|---|
| 1 (đối chứng) | 0,78 đến 1,08 | 0,89 đến 1,20 |
| 4 | 1,17 đến 1,72 | 1,52 đến 1,85 |
| 16 | 1,09 đến 2,40 | 1,52 đến 2,26 |
| 256 | 1,06 đến 2,01 | 1,53 đến 2,47 |

Hướng thì rõ: nhiều shard nhanh hơn một shard, nhưng tăng `N` từ 16 lên 256 thì mình **không** thấy nhanh thêm rõ rệt. **Khóa nóng** (mọi lượt vào một từ, `N = 16`): **0,96 đến 1,36** không tối ưu, **0,94 đến 1,03** với `-O2`, tức không được gì. Con số đẹp hơn ở [Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md) vì khác tải; đừng chép số, chép **cách đo**.

**`shared_mutex` mỗi shard** (1000 khóa, `N = 16`, mỗi luồng 200000 thao tác), tỉ lệ thời gian của `mutex` chia thời gian của `shared_mutex` (lớn hơn 1: `shared_mutex` nhanh hơn):

| Tỉ lệ ghi | không tối ưu | `-O2` |
|---|---|---|
| 0% (chỉ đọc) | 1,44 đến 2,02 | 1,46 đến 1,73 |
| 5% | 0,61 đến 0,87 | 0,68 đến 0,89 |
| 50% | 0,52 đến 0,82 | 0,49 đến 0,59 |

Chỉ đọc thì `shared_mutex` nhanh hơn, nhưng chỉ cần **5% ghi** là nó **chậm hơn** một mutex thường. Lý do hợp lý: vùng găng ở đây cực ngắn (một lần tra), nên cái giá xin và nhả khóa chia sẻ lớn hơn cái lợi cho phép đọc song song. Vùng găng dài thì kết luận có thể khác; đó là điều chỉ đo mới nói được.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết một concurrent hash map. Bạn làm thế nào?"
    Nói theo bậc thang. Bậc 1: một mutex quanh `unordered_map`, đúng và đơn giản, đo trước. Bậc 2: nếu nghẽn vì nhiều luồng ghi các khóa khác nhau thì **chia shard**: `N` bảng, `N` mutex, băm khóa chọn shard; mỗi hàm chỉ khóa một shard nên không deadlock. Nói rõ ba quyết định: `get` trả **bản sao** (không trả tham chiếu), `compute` gộp tra-sửa-chèn vào một lần khóa, và `N` cố định lúc dựng.
    Nối tiếp: **"`size()` của bạn trả gì khi đang có người ghi?"** Khóa từng shard cộng lại thì chỉ là con số gần đúng, mình chạy thấy ra 9 và 12 trong khi thật sự luôn 10 hoặc 11. Cần số đúng thì giữ mọi khóa theo chỉ số tăng dần, và cái giá là cả bảng đứng yên.

??? question "Hai luồng cùng tăng bộ đếm của một khóa. Tại sao `get` rồi `put` sai, dù cả hai hàm đều có khóa?"
    Vì khóa nhả giữa hai lời gọi: hai luồng cùng đọc 5 rồi cùng ghi 6. Đó là race condition, không phải data race, nên TSan **không** báo (mình chạy 3 lần, sạch, mà đếm thiếu cỡ 0,3 đến 0,7%). Phải gộp thành một thao tác khóa một lần: `compute(k, [](int& n) { ++n; })`. Nối tiếp: **"`compute` gọi ngược vào map được không?"** Không: `f` chạy khi đang giữ khóa, gọi `get` cùng shard là khóa lại mutex đang giữ (treo), gọi shard khác dễ thành deadlock chéo.

??? question "Cần tăng số shard khi map đang chạy. Làm được không?"
    Làm được nhưng đắt. Mọi khóa đổi shard theo `N` mới nên phải giữ mọi khóa, dựng mảng shard mới, chuyển từng khóa, rồi thả: cả bảng đứng O(n). Hoặc đặt mảng shard sau một `shared_mutex` tổng, mọi thao tác xin nó ở chế độ chia sẻ, và vô tình tạo điểm tranh chấp chung. Thực tế chọn `N` một lần (vài lần số lõi), kèm `reserve` để rehash từng shard ít và nhỏ.

??? question "Đọc nhiều ghi ít thì dùng `shared_mutex` mỗi shard?"
    Có thể thử, nhưng **đo**. Mình đo chỉ đọc thì nhanh hơn 1,4 đến 2 lần, còn với 5% ghi thì chậm hơn một mutex thường vì vùng găng quá ngắn. Hợp hơn khi vùng găng dài hoặc đọc gần như tuyệt đối. Và chuẩn không nói bên đọc hay bên ghi được ưu tiên, nên đừng hứa chuyện "không đói ghi".

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Trả `V&`, `V*` hoặc iterator từ `get`"
    Mình chạy: `erase` ở luồng khác, đúng luật khóa, mà `heap-use-after-free` ở bên đọc. Trả **bản sao** `optional<V>`, hoặc đưa việc vào hàm như `compute`.

!!! warning "Lỗi 2: Nói \"mỗi hàm có khóa nên cả lớp an toàn\""
    Phỏng vấn viên sẽ hỏi `if (!contains(k)) put(k, v)` hay `get` rồi `put`. TSan sạch mà kết quả sai. Nói thẳng: thao tác nhiều bước phải gộp thành **một** hàm giữ khóa một lần.

!!! warning "Lỗi 3: Chọn shard bằng `hash % N` rồi tin phân bố đều"
    Với `std::hash<int>` trả chính số, khóa là bội của `N` dồn hết vào một shard (mình chạy: 1000 khóa vào shard 0). Trộn bit trước khi chia, và nói rằng chuẩn không hứa hàm băm rải đều.

!!! warning "Lỗi 4: Viết `size()` xong tuyên bố \"chính xác\""
    Khóa từng shard cho số gần đúng. Muốn đúng phải giữ mọi khóa theo thứ tự cố định (chỉ số tăng), và nêu cái giá: chặn mọi ghi. Cũng đừng quên nêu: bảng này không tặng iterator, chỉ tặng ảnh chụp.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="72" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. Tám luồng, mỗi luồng chạy đoạn này 1000 lần cho cùng khóa `"a"`; `get` và `put` đều tự khóa. Điều nào đúng?

```text
auto n = m.get("a");
m.put("a", n ? *n + 1 : 1);
```

- Luôn ra 8000, vì `get` và `put` đều có khóa nên không lượt nào mất
- Có thể ra ít hơn 8000 mà TSan vẫn không báo gì
- TSan báo data race ở `put`, vì hai luồng cùng ghi khóa `"a"`
- Treo, vì mỗi luồng xin khóa hai lần liên tiếp

<p class="giai-thich" markdown>Khóa nhả giữa `get` và `put`, nên hai luồng có thể cùng đọc 5 rồi cùng ghi 6 và mất một lượt; đó là race condition, không phải data race, vì mọi truy cập đều có khóa nên TSan không thấy gì. Nói "luôn 8000 vì mỗi hàm có khóa" nhầm tính đúng của từng hàm với tính đúng của cả thao tác. Nói "TSan báo race" nhầm hai loại lỗi. Còn hai lần xin khóa ở hai lần gọi riêng, mỗi lần nhả trước khi sang lần sau, nên không treo.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau. Map chỉ có **một** shard, dùng `std::mutex`, và `compute` giữ khóa suốt lúc gọi `f`. Chuyện gì xảy ra?

```text
m.compute(1, [&m](int& n) {
    n = m.get(2).value_or(0) + 1;
});
```

- Chạy bình thường, ghi vào khóa 1 giá trị 1
- Ném ngoại lệ, vì `get` bị gọi lồng trong `compute`
- Treo, vì `get` xin lại mutex mà luồng này đang giữ
- Data race, vì `get` đọc khóa 2 khác khóa 1

<p class="giai-thich" markdown>`f` chạy khi `compute` đang giữ khóa của shard duy nhất, và `get` xin lại đúng mutex đó trên cùng luồng; chuẩn gọi đó là hành vi không xác định, glibc ở đây cho treo (mình chạy: mã 124). Không có ngoại lệ nào được ném. Cũng không có data race, vì mọi truy cập đều qua khóa, chỉ là khóa bị xin hai lần. Khóa khác nhau không giúp được, vì chỉ có một shard nên mọi khóa dùng chung một mutex.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Cache cấu hình: 16 luồng đọc liên tục, 95% lượt tra cùng **một** khóa nóng `"cfg"`, thỉnh thoảng một luồng ghi. Chia 256 shard có giúp không, và nên thử gì?

- Có, 256 shard cho 256 luồng chạy riêng, nên đọc không chờ nhau
- Có, nhưng chỉ khi đổi `unordered_map` trong mỗi shard sang `map`
- Không, và cách duy nhất là gom cả cache về một `std::mutex`
- Không, vì `"cfg"` luôn vào một shard; thử chế độ đọc chia sẻ rồi đo

<p class="giai-thich" markdown>Cùng một khóa luôn băm vào cùng một shard, nên 95% lượt tra vẫn tranh một khóa và 256 shard không đổi gì (mình đo khóa nóng thì tỉ lệ quanh 1). Hướng đáng thử là `shared_lock` để người đọc không chặn nhau, nhưng phải đo vì vùng găng ngắn thì lợi có thể không bù được giá. Đổi loại bảng trong shard không đổi việc cùng một khóa tranh một mutex. Còn gom về một mutex thường thì đọc nào cũng xếp hàng, không tốt hơn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Bảng 64 shard luôn có 10 hoặc 11 khóa thật. Hàm `size()` khóa shard 0, đếm, nhả, rồi sang shard 1, và cứ thế, trong lúc các luồng khác thêm xóa. `size()` có thể trả gì?

- Một số chưa từng đúng, như 12, vì mỗi shard đếm vào lúc khác nhau
- Luôn 10 hoặc 11, vì mỗi shard đều được khóa đúng lúc nó được đếm
- Luôn nhỏ hơn số khóa thật, vì các shard đếm sau luôn bị bỏ sót đi
- Chương trình bị deadlock, vì phải giữ nhiều mutex của shard liên tiếp

<p class="giai-thich" markdown>Giữa hai lần khóa, một luồng kịp thêm khóa mới ở shard chưa đếm và xóa khóa cũ ở shard đã đếm, nên tổng có thể là 12 hoặc 9 (mình chạy thấy cả hai). "Mỗi shard khóa nên tổng đúng" nhầm tính đúng từng mảnh với tính đúng của tổng. Hàm nhả khóa trước khi sang shard kế nên không giữ hai khóa cùng lúc và không deadlock. Số đếm không có chiều lệch cố định.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đoạn sau. `std::hash<int>` trên g++ này trả chính số truyền vào. Các khóa là 0, 16, 32, 48, ... Điều nào đúng?

```text
shard = std::hash<int>{}(k) % 16;
```

- Khóa rải đều 16 shard, vì hàm băm biến mọi số thành ngẫu nhiên
- Khóa dồn vào shard 15, vì khóa lớn dần
- Mọi khóa vào shard 0, vì bội của 16 chia 16 đều dư 0
- Chương trình không biên dịch được vì `hash<int>` không tồn tại

<p class="giai-thich" markdown>Hàm băm trả chính khóa, nên `k % 16` luôn bằng 0 với khóa là bội của 16 và cả bảng thành một shard. Chuẩn không hứa hàm băm rải đều; `hash<int>` nhận một số và trả số đó là hợp lệ. Nói "rải đều" nhầm hàm băm của `int` với một hàm băm ngẫu nhiên. Khóa lớn dần không đổi dư của phép chia. Cách chữa là trộn bit (nhân với một hằng lẻ lớn, lấy bit cao) trước khi chia.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Một đồng nghiệp viết `const V* get(const K& k)` trả con trỏ vào phần tử trong shard, khóa nhả khi hàm trả về. Lỗi nằm ở đâu?

- Con trỏ sống lâu hơn khóa; luồng khác `erase` thì nó treo vào nút đã giải phóng
- Không có lỗi, vì suốt lúc `get` đang chạy luồng này đã giữ khóa của shard đó
- Con trỏ bị hỏng ngay khi `get` trả về, vì con trỏ trả từ hàm luôn vô hiệu
- Lỗi ở chỗ không dùng `shared_mutex` cho `get`, nên các người đọc chặn nhau

<p class="giai-thich" markdown>Khóa chỉ xếp hàng các lời gọi hàm, còn địa chỉ lấy ra trong khóa vẫn dùng được sau khi khóa nhả, và `erase` của luồng khác giải phóng nút đó (mình chạy: `heap-use-after-free`). Nói "đã giữ khóa lúc `get`" đúng về hàm nhưng sai về lúc dùng con trỏ. Con trỏ không tự hỏng khi hàm trả; nó hỏng khi phần tử bị xóa. Còn `shared_mutex` chỉ là chuyện hiệu năng, không chữa được con trỏ treo.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Vì sao tăng số shard khi map đang chạy khó?

- Vì `unordered_map` không cho tăng số hộp sau khi đã dựng xong bảng
- Vì mutex không thể thêm vào mảng sau khi chương trình đã bắt đầu chạy luồng
- Vì mỗi luồng giữ sẵn một iterator của shard mà nó đang dùng dở
- Vì mọi khóa đổi shard theo `N` mới, nên phải giữ mọi khóa và xếp lại hết

<p class="giai-thich" markdown>Shard của khóa là hàm của `N`; đổi `N` thì hầu hết khóa phải sang shard khác, nên phải ngăn mọi thao tác (giữ mọi khóa) rồi chuyển từng khóa, tốn O(n). `unordered_map` thì tăng số hộp được bằng `rehash`. Mutex thì không bao giờ bị "thêm" vào một mảng đang dùng mà chỉ dựng mảng mới. Còn lớp của bài không trao iterator ra ngoài, nên không có luồng nào giữ iterator của shard.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Hàm `sizeChinhXac` khóa các shard theo chỉ số **tăng dần**. Vì sao thứ tự đó quan trọng khi hai luồng cùng gọi `sizeChinhXac` (hoặc `chupAnh`) một lúc?

- Để các shard nhỏ được đếm trước, vì như vậy mỗi lần đếm chạy nhanh hơn một chút
- Để hai luồng khóa nhiều shard không chờ vòng tròn, tức không deadlock
- Để `unordered_map` trong mỗi shard giữ đúng thứ tự các khóa được chèn
- Vì chuẩn C++ bắt mọi khóa phải được xin theo thứ tự địa chỉ trong bộ nhớ

<p class="giai-thich" markdown>Nếu một luồng khóa shard 3 rồi 7 còn luồng kia khóa 7 rồi 3 thì mỗi bên giữ một khóa và chờ khóa kia: deadlock ([Bài 26](../nhom-3-da-luong/26-deadlock.md)). Cùng một thứ tự toàn cục phá điều kiện chờ vòng tròn. Thứ tự không liên quan tới tốc độ đếm hay thứ tự chèn của bảng băm. Chuẩn cũng không bắt thứ tự theo địa chỉ; đó là quy ước của người viết, `std::scoped_lock` là cách khác để tránh.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `ShardedMap` đúng gồm `N` shard (mỗi shard một mutex và một `unordered_map`), băm khóa chọn shard, mỗi hàm chỉ khóa **một** shard nên không deadlock; `get` trả **bản sao** vì con trỏ hay tham chiếu thoát khỏi khóa là `heap-use-after-free` (mình chạy), và `N` cố định lúc dựng.
2. "Mỗi hàm tự khóa" chưa đủ: `get` rồi `put` mất lượt đếm (mình chạy: thiếu 0,3 đến 0,7%) mà TSan sạch, vì đó là race condition; gộp vào `compute` khóa một lần, và `f` không được gọi ngược vào map (mình chạy: treo, mã 124).
3. `size()` khóa từng shard chỉ là số gần đúng (mình thấy 9 và 12 khi thật luôn 10 hoặc 11); số đúng cần giữ mọi khóa theo chỉ số tăng dần, và cái giá là cả bảng đứng; ảnh chụp là bản sao làm cùng cách, không có iterator đi ra ngoài.
4. Rehash chỉ nằm trong một shard (một lần rehash bảng 1 triệu phần tử đắt hơn bảng một shard cỡ 39 đến 60 lần, đổi theo máy) và `reserve` cắt gần hết; đổi số shard khi chạy phải xếp lại mọi khóa nên người ta chọn `N` một lần; `std::hash<int>` trả chính số nên phải trộn bit.
5. Chia shard nhanh hơn một shard cỡ 1,1 đến 2,5 lần khi nhiều luồng ghi khóa khác nhau, nhưng không giúp với khóa nóng (tỉ lệ quanh 1); `shared_mutex` mỗi shard nhanh hơn khi chỉ đọc nhưng chậm hơn từ 5% ghi trong thí nghiệm này: luôn đo trên tải thật, và 1 đến 2 luồng thì một mutex là đủ.
