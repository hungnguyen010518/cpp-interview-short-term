# Bài 81 — Live-coding: tự cài hash map

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng `HashMap<K, V>` **nối chuỗi**: băm, `put`/`get`/`erase`, hệ số tải, rehash bằng cách **nối lại nút** (không chép), và đối chiếu với `std::unordered_map` bằng một test cố định (đầu ra tất định); kết quả sạch với ASan và UBSan.
    - Viết thêm bản **mở địa chỉ** (linear probing) và xóa bằng **bia mộ** (tombstone), thấy bằng số đếm thật chuyện gì xảy ra khi xóa không bia mộ, khi không rehash, khi hàm băm tồi (và khi rehash làm mất nút).
    - Nói đúng điều kiện của "O(1) trung bình, O(n) xấu nhất", và trả lời **lũy thừa của 2 hay số nguyên tố** bằng thí nghiệm đã chạy, kể cả chỗ mỗi bên thua.
    - Nói được mình **lược gì** so với `std::unordered_map` (iterator, allocator, node handle...) và vì sao thư viện chuẩn gần như buộc phải dùng nút nối chuỗi.

**Bạn cần biết trước:** [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, LeakSanitizer), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`= delete`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`enum class`, `constexpr`), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector`), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`unordered_map`, hàm băm), [Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md) (Big-O, amortized, nút nối), [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) (bảng băm nối chuỗi đã phác), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (bất biến, hàm `const`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template`) và [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md) (ASan, UBSan).

!!! note "Phạm vi bài này"
    [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) đã dạy ý tưởng (hộp, đụng độ, hệ số tải, rehash) và [Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md) đã so `map` với `unordered_map`; bài này **không nhắc lại lý thuyết** mà biến nó thành lớp template đầy đủ rồi đào sang mở địa chỉ. Đây là bản để hiểu và để phỏng vấn, **không phải bản thay `std::unordered_map`**: các thứ bị lược nằm ở cuối mục 📖.

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đưa bút: "Không dùng `unordered_map`. Viết cho anh một hash map: `put`, `get`, `erase`." Bạn viết xong phần nối chuỗi, anh gật đầu rồi hỏi liền ba câu: "Khi nào em nới bảng? Số hộp em chọn là bao nhiêu, vì sao? Nếu bỏ hết con trỏ, dùng một mảng phẳng thì xóa một khóa thế nào?"

Trong **xưởng tự lắp đồ** của nhóm này, `unordered_map` là một cái **tủ nhiều ngăn kéo**: ta tháo ra xem từng bánh răng. Bánh răng một là **hàm băm** (tên đồ vật thành con số). Bánh răng hai là phép chia **chọn ngăn**. Bánh răng ba là cách xử lý **hai món vào cùng ngăn**: hoặc xâu chúng thành dây (nối chuỗi), hoặc xếp sang ngăn kế bên (mở địa chỉ, và ngăn trống bị lấy đồ đi phải cắm một tấm "bia mộ"). Bánh răng bốn là **nới tủ** (rehash).

!!! info "Chỗ nào ví von xưởng tự lắp đồ không còn đúng?"
    Lắp lệch một bánh răng của máy thật thì máy kẹt ngay. Bảng băm lắp lệch thường **vẫn chạy đúng**, chỉ chậm đi hàng trăm lần (ta đếm ở mục 💻), nên lỗi này lọt qua test đúng/sai. Riêng "bia mộ" là lỗi thật sự: thiếu nó thì kết quả **sai**.

## 📖 Giải thích

Ta làm hai đề. Đề 1 dùng lại đúng bộ khung của [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) nhưng viết cho ra hồn; đề 2 bỏ con trỏ.

### Đề 1: `HashMap<K, V>` nối chuỗi

**Đề.** Viết lớp mẫu `HashMap<K, V, Hash>`, trong đó chỉ được dùng `std::vector` cho mảng hộp và tự quản lý các nút.

- `bool put(k, v)`: thêm, hoặc ghi đè nếu khóa đã có; trả `true` nếu là khóa mới.
- `const V* get(k) const`: trả con trỏ tới giá trị, hoặc `nullptr` nếu không có.
- `bool erase(k)`: xóa; trả `true` nếu có xóa.
- Tự nới bảng (rehash) để `put`/`get` vẫn **O(1) trung bình** khi số khóa tăng: theo dõi **hệ số tải** (gọi tắt **tải**: số khóa chia số hộp, [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md)). Không rò rỉ.

**Đầu vào/ra và kiểm tra:** chạy cùng một chuỗi lệnh `put`/`get`/`erase` (sinh từ hạt giống cố định) trên bảng của bạn và trên `std::unordered_map`; kết quả mọi lệnh phải giống nhau.

??? tip "Gợi ý 1"
    Đừng nghĩ tới "hash map" nữa, hãy nghĩ tới **một mảng các danh sách liên kết**. Khóa chọn mảng ở vị trí nào? Rồi làm gì ở vị trí đó?

??? tip "Gợi ý 2"
    Vị trí = `hàm băm(k) % số hộp`. Hai khóa khác nhau có thể ra cùng vị trí, nên mỗi vị trí là đầu một danh sách nút nối đơn (`Nut` có `tiep`), và so khóa bằng `==` khi đi dọc danh sách. `put` phải **tìm trước** để không tạo khóa trùng.

??? tip "Gợi ý 3"
    Theo dõi `soPhanTu / soHop`. Vượt ngưỡng thì xin mảng hộp gấp đôi và đưa **từng nút cũ** sang hộp mới (vì `% số hộp` đã đổi). Có cần `new` nút mới không? Không: chỉ cần sửa con trỏ `tiep`. Lúc nối lại nhớ lấy `tiep` cũ ra **trước** khi ghi đè nó.

**Phân tích hướng giải.** Trên bảng trắng, hỏi lại đề trước: khóa kiểu gì, có cần xóa không, có cần duyệt theo thứ tự không (bảng băm **không** có thứ tự)? Sau đó nêu **bất biến**, vì gần như mọi lỗi là làm vỡ một trong ba điều này:

| Bất biến | Nghĩa | Hàm nào dễ làm vỡ |
|---|---|---|
| I1 | Mỗi nút nằm ở hộp `bam(khoa) % số hộp` hiện tại | `rehash` quên tính lại hộp cho một nút |
| I2 | Không có hai nút cùng khóa | `put` chèn mà không tìm trước |
| I3 | `soPhanTu_` bằng tổng độ dài các chuỗi | `erase`/`put` quên cập nhật, nên rehash sai lúc |

### Đề 2: mở địa chỉ, linear probing, bia mộ

**Đề.** Cùng giao diện `put`/`get`/`erase`, nhưng **không có nút riêng**: dữ liệu nằm trong **một mảng phẳng** các ô. Khóa rơi vào ô đã có người thì thử ô kế tiếp, rồi kế tiếp nữa (**linear probing**: dò tuyến tính, cuối mảng thì quay về đầu). Làm `erase` đúng.

**Đầu vào/ra và kiểm tra:** như đề 1, nhưng chuỗi lệnh có **nhiều lệnh xóa hơn** (cứ năm lệnh có hai lệnh `erase`) để bắt lỗi xóa.

??? tip "Gợi ý 1"
    Một ô chỉ có hai trạng thái "có/không" thì đủ không? Khi `get` đi dò, nó dừng ở đâu để kết luận "khóa này không có"?

??? tip "Gợi ý 2"
    `get` dừng ở ô **trống** đầu tiên, vì nếu khóa có mặt thì nó đã được đặt trước ô trống đó. Giả sử khóa A, B, C cùng rơi ô 5 nên nằm ở ô 5, 6, 7; xóa B bằng cách trả ô 6 về trống. Bây giờ tìm C: đi từ ô 5, ô 6 trống nên dừng. Chuyện gì xảy ra?

??? tip "Gợi ý 3"
    Cần **ba** trạng thái: trống, đang có, và **bia mộ** ("ở đây từng có người, đừng dừng"). `get` đi xuyên qua bia mộ; `put` được dùng lại bia mộ đầu tiên (sau khi chắc chắn khóa chưa có). Bia mộ cũng làm chuỗi dò dài ra nên phải tính vào hệ số tải, và rehash là dịp dọn chúng.

**Phân tích hướng giải.** Trạng thái một ô và vai trò của nó:

| Trạng thái | `get`/`put` khi dò gặp | `erase` đặt thành |
|---|---|---|
| Trống | **dừng** (không có khóa) | không bao giờ |
| Đang có | so khóa; khác thì đi tiếp | bia mộ |
| Bia mộ | **đi tiếp**; `put` có thể dùng lại | giữ nguyên |

Bất biến then chốt: với mỗi khóa đang có ở ô `j`, **mọi ô từ ô đầu của nó tới `j` đều không trống**. Xóa bằng "trống" phá đúng bất biến này. Bất biến thứ hai: luôn còn ít nhất một ô trống (tải kể cả bia mộ ≤ 3/4), nếu không vòng dò tìm khóa vắng không bao giờ dừng. Hệ quả: `size()` chỉ đếm ô **đang có** (bia mộ không phải phần tử), còn tải thì đếm cả bia mộ vì chúng chiếm ô và kéo dài chuỗi dò.

### Chi phí, hệ số tải, lũy thừa của 2 và số nguyên tố

| | Nối chuỗi | Mở địa chỉ (linear probing) |
|---|---|---|
| `put`/`get`/`erase` trung bình | O(1) khi hàm băm tản đều, tải ≤ ngưỡng | O(1) khi hàm băm tản đều, tải ≤ ngưỡng |
| Xấu nhất | O(n): mọi khóa cùng một hộp | O(n): dò gần hết mảng |
| Rehash | O(n) mỗi lần, hiếm: **amortized** O(1) cho mỗi `put` | như bên trái |
| Bộ nhớ | mảng hộp + một nút (cấp phát riêng) cho mỗi phần tử | một mảng liền, nhưng phải để trống cỡ 1/4 trở lên |
| Con trỏ tới phần tử sau rehash | **còn đúng** (chỉ nối lại nút) | **hỏng** (mảng mới thay mảng cũ) |
| Khi tải tăng | chậm dần đều | chậm rất nhanh khi gần đầy |
| Xóa | nối bỏ qua nút | bia mộ (hoặc dời lùi, ở 🎤) |

**"Trung bình" mang điều kiện.** Hàm băm phải tản khóa gần như đều qua các hộp, và rehash giữ tải bị chặn. Khi đó nối chuỗi tốn cỡ `1 + tải/2` lần so khóa cho một lần tìm thấy (mình đếm bên dưới: tải 0,61 ra 1,30). Với linear probing, theo công thức của Knuth (dưới giả thiết băm đều, chỉ chèn, chưa xóa) số ô phải xem, tính cả ô cuối (ô chứa khóa, hoặc ô trống), là cỡ `(1 + 1/(1−tải))/2` khi tìm thấy và `(1 + 1/(1−tải)²)/2` khi không có. Mình mô phỏng bằng một chương trình riêng (bảng 2^18 ô, vị trí đầu ngẫu nhiên, chạy ba lần mỗi mức tải) và nó khớp:

| Tải | Tìm thấy: công thức / đo | Không có: công thức / đo |
|---|---|---|
| 0,50 | 1,5 / 1,50 | 2,5 / 2,51 |
| 0,75 | 2,5 / 2,49 | 8,5 / 8,6 |
| 0,90 | 5,5 / 5,47 | 50,5 / 49 đến 52 |

Ở tải 0,90 số đo "không có" dao động giữa các lần chạy (49 đến 52) vì chuỗi dò rất dài, còn hai mức tải thấp thì khớp tới hàng phần mười. Vì vậy nối chuỗi chịu tải 1 (ngưỡng mặc định của `unordered_map`), còn linear probing nên giữ ≤ 0,5 đến 0,75: gần đầy thì "khóa không có" phải dò hàng chục ô.

**Lũy thừa của 2 hay số nguyên tố?** Hai bên đánh đổi, không bên nào thắng hoàn toàn:

- Số hộp **lũy thừa của 2**: chọn hộp bằng `h & (n - 1)` thay cho `h % n` (`&` là "và từng bit": nó giữ các bit thấp của `h`, đúng bằng phần dư khi `n` là lũy thừa của 2; ví dụ số ở 💻), thường rẻ hơn một phép chia; gấp đôi để nới là tự nhiên. Cái giá: chỉ dùng các **bit thấp** của hàm băm, nên hàm băm yếu ở bit thấp thì hỏng. Ví dụ `std::hash<int>` ở g++ trả chính số đó, nên các khóa cách nhau 1024 đều rơi một hộp (có số đếm ở 💻). Chữa: một bước **trộn bit** (biến đổi số băm để mỗi bit vào ảnh hưởng mọi bit ra; có code ở 💻) trước khi chọn hộp.
- Số hộp **nguyên tố**: `h % p` dùng **mọi bit** của hàm băm nên chịu được hàm băm yếu, nhưng phải có bảng số nguyên tố để nới (g++ 11 ở đây đi qua 13, 29, 59, 127, 257, 541... mình đã in `bucket_count()` của `unordered_map`) và mỗi lần chọn hộp là một phép chia. Nó cũng không miễn nhiễm: khóa là bội của chính số nguyên tố đó thì dồn vào một hộp (cũng có số đếm).
- Chuẩn **không quy định** số hộp hay cách chọn hộp; thư viện khác nhau chọn khác nhau, đừng dựa vào `bucket_count()` cụ thể.

**Cái gì lược bớt so với `std::unordered_map`.** Iterator (`begin`/`end`, `find` trả iterator), `operator[]`/`at`, `insert`/`emplace`/`try_emplace`, sao chép và di chuyển cả bảng (ta xóa chúng), allocator tùy biến, node handle (`extract`/`merge`), `reserve`/`rehash`/`max_load_factor` do người dùng chỉnh, `equal_range`, tham số `KeyEqual` (ta cố định `==`), và các bảo đảm về ngoại lệ. Bản mở địa chỉ còn đòi `K`, `V` dựng mặc định được. Chuẩn lại đòi tham chiếu/con trỏ tới phần tử **không hỏng khi rehash** và có giao diện hộp (`bucket_size`...), nên `std::unordered_map` gần như buộc phải dùng nút nối chuỗi chứ không dùng mảng phẳng ([Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md) đã chạy thật chuyện giữ `&bang[13]` qua rehash).

!!! info "Bạn biết Go?"
    `map` của Go cũng là bảng băm, và `m[w]++` ở Go là cả cặp "get rồi put" của ta. Khác biệt đáng nhớ: Go **cấm** lấy địa chỉ phần tử (mình chạy Go 1.27.2: `p := &m[1]` báo `cannot take address of m[1]`), thường được giải thích là vì bảng có thể dời phần tử khi nới. C++ cho giữ `&bang[k]` với `unordered_map` đúng vì các nút không dời. Go cũng không cho bạn chỉnh hệ số tải hay hàm băm của một `map` thường.

## 💻 Ví dụ code

Mọi chương trình ở mục này mình biên dịch bằng `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined` (g++ 11.4) rồi chạy: **không một cảnh báo, ASan và UBSan không báo gì, thoát mã 0**. Các bản sai đánh dấu `// bo-qua-kiem-tra` mình cũng đã chạy thật.

### Lời giải đề 1: xây dần từng bước

Cú pháp mới hoặc dễ lạ trong listing:

- `template <class K, class V, class Hash = std::hash<K>>`: chỗ trống thứ ba có **giá trị mặc định** (như `int N = 4` ở [Bài 34](../nhom-4-oop-patterns/34-template.md), nhưng điền bằng một kiểu). `std::hash<K>` (`<functional>`) là hàm băm có sẵn: `std::hash<int>{}(5)` dựng một đối tượng băm rồi gọi nó với `5`. Gọi được vì nó có `operator()`: struct như vậy là **functor** (đối tượng gọi như hàm); `BamInt` cuối listing là một functor tự viết, đúng thứ người dùng điền vào chỗ trống `Hash`.
- `hop_` (có `_` cuối) là quy ước "thành viên riêng". `if (Nut* n = timNut(k))` khai báo `n` ngay trong điều kiện (đúng khi `n` khác `nullptr`). `for (...; ...; truoc = n, n = n->tiep)`: dấu phẩy ở bước cuối là làm **hai việc liền nhau**. `n ? &n->giaTri : nullptr` là: nếu `n` khác `nullptr` thì địa chỉ của `n->giaTri`, không thì `nullptr`.
- `static constexpr double maxTai_` là hằng chung của lớp, biết lúc biên dịch ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)); `explicit` cấm tự đổi một số thành `HashMap` ngầm.
- Test dùng bộ sinh số `x * 1664525u + 1013904223u`: cùng hạt giống thì cùng dãy, nên đầu ra tất định. Số **không dấu** tràn thì quay vòng (hợp lệ); tràn số **có dấu** mới là UB. `b.count(k)` là số lần khóa có trong `unordered_map` (0 hoặc 1); `b.erase(k)` trả số phần tử đã xóa.

Năm bước trên bảng trắng: **(1) khung**: `Nut` có `tiep`, `std::vector<Nut*> hop_` (`nullptr` là hộp trống), hộp = `bam_(k) % hop_.size()` (dòng (3)). **(2) tìm** (dòng (4)): đi dọc đúng một hộp, so bằng `==` (không đủ nếu chỉ so số băm). **(3) `put`**: tìm trước (giữ I2), kiểm tải **trước** khi chèn (dòng (6)), chèn **đầu** chuỗi vì O(1) (dòng (7)). **(4) `rehash`** (dòng (5)): mảng mới gấp đôi; mỗi nút cũ: lấy `tiep` ra trước, tính hộp mới, nối vào đầu chuỗi mới. **(5) `erase`** (dòng (8)): đi dọc và nhớ `truoc`; nối `truoc` bỏ qua nút (hoặc sửa đầu hộp), rồi `delete`.

```cpp
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

template <class K, class V, class Hash = std::hash<K>>
class HashMap {
    struct Nut {                                 // (1) một nút của chuỗi
        K khoa;
        V giaTri;
        Nut* tiep;                               // nút kế trong cùng hộp, hoặc nullptr
    };
    std::vector<Nut*> hop_;                      // (2) hộp i = đầu một chuỗi (nullptr = trống)
    std::size_t soPhanTu_ = 0;
    static constexpr double maxTai_ = 1.0;       // hệ số tải tối đa
    Hash bam_;

    std::size_t chonHop(const K& k) const { return bam_(k) % hop_.size(); }   // (3)

    Nut* timNut(const K& k) const {              // (4) chỉ lục trong MỘT hộp
        for (Nut* n = hop_[chonHop(k)]; n != nullptr; n = n->tiep)
            if (n->khoa == k) return n;
        return nullptr;
    }

    void rehash(std::size_t soHopMoi) {          // (5) nối lại nút, không tạo nút mới
        std::vector<Nut*> moi(soHopMoi, nullptr);
        for (Nut* n : hop_) {
            while (n != nullptr) {
                Nut* tiep = n->tiep;             // nhớ trước khi sửa n->tiep
                std::size_t h = bam_(n->khoa) % soHopMoi;
                n->tiep = moi[h];
                moi[h] = n;
                n = tiep;
            }
        }
        hop_ = std::move(moi);
    }

public:
    explicit HashMap(std::size_t soHop = 8) : hop_(soHop == 0 ? 1 : soHop, nullptr) {}
    HashMap(const HashMap&) = delete;            // xóa sao chép (Bài 11); move cũng không có
    HashMap& operator=(const HashMap&) = delete;
    ~HashMap() {
        for (Nut* n : hop_)
            while (n != nullptr) { Nut* tiep = n->tiep; delete n; n = tiep; }
    }

    bool put(const K& k, V v) {                  // true nếu là khóa mới
        if (Nut* n = timNut(k)) { n->giaTri = std::move(v); return false; }
        if (static_cast<double>(soPhanTu_ + 1) > maxTai_ * static_cast<double>(hop_.size()))
            rehash(hop_.size() * 2);             // (6) nới TRƯỚC khi chèn
        std::size_t h = chonHop(k);
        hop_[h] = new Nut{k, std::move(v), hop_[h]};   // (7) chèn đầu chuỗi: O(1)
        ++soPhanTu_;
        return true;
    }

    const V* get(const K& k) const {             // nullptr nếu không có
        const Nut* n = timNut(k);
        return n ? &n->giaTri : nullptr;
    }

    bool erase(const K& k) {
        std::size_t h = chonHop(k);
        Nut* truoc = nullptr;
        for (Nut* n = hop_[h]; n != nullptr; truoc = n, n = n->tiep) {
            if (n->khoa == k) {
                if (truoc != nullptr) truoc->tiep = n->tiep;   // (8) nối bỏ qua n
                else hop_[h] = n->tiep;                        //     n là đầu chuỗi
                delete n;
                --soPhanTu_;
                return true;
            }
        }
        return false;
    }

    std::size_t size() const { return soPhanTu_; }
    std::size_t bucket_count() const { return hop_.size(); }
    std::size_t bucket_size(std::size_t i) const {
        std::size_t d = 0;
        for (const Nut* n = hop_[i]; n != nullptr; n = n->tiep) ++d;
        return d;
    }
    std::size_t chuoiDaiNhat() const {
        std::size_t dn = 0;
        for (std::size_t i = 0; i < hop_.size(); ++i) dn = std::max(dn, bucket_size(i));
        return dn;
    }
    void in() const {                            // in từng hộp để nhìn bằng mắt
        std::cout << "  " << soPhanTu_ << " khoa, " << hop_.size() << " hop:";
        for (const Nut* dau : hop_) {
            std::cout << " [";
            for (const Nut* n = dau; n != nullptr; n = n->tiep) std::cout << " " << n->khoa;
            std::cout << " ]";
        }
        std::cout << "\n";
    }
};

struct BamInt {                                  // hàm băm tự viết: chính số đó
    std::size_t operator()(int k) const { return static_cast<std::size_t>(k); }
};

int main() {
    HashMap<int, int, BamInt> nho(2);            // (A) demo nhỏ: bắt đầu 2 hộp
    for (int k : {10, 20, 30, 40, 50}) { nho.put(k, k * 10); nho.in(); }
    nho.erase(10);
    nho.in();

    HashMap<int, int> a;                         // (B) đối chiếu với unordered_map
    std::unordered_map<int, int> b;
    std::uint32_t x = 12345;
    auto rnd = [&x]() { x = x * 1664525u + 1013904223u; return x >> 8; };
    int khac = 0, lanXoa = 0;
    for (int i = 0; i < 20000; ++i) {
        int k = static_cast<int>(rnd() % 1000);
        unsigned loai = rnd() % 4;               // 0,1: put   2: get   3: erase
        if (loai <= 1) {
            bool moiB = b.count(k) == 0;         // khóa chưa có thì put phải báo "mới"
            b[k] = i;
            if (a.put(k, i) != moiB) ++khac;
        } else if (loai == 2) {
            const int* pa = a.get(k);
            auto it = b.find(k);
            if ((pa == nullptr) != (it == b.end()) || (pa != nullptr && *pa != it->second)) ++khac;
        } else {
            bool xoaA = a.erase(k);
            if (xoaA != (b.erase(k) == 1)) ++khac;
            lanXoa += xoaA;
        }
    }
    for (int k = 0; k < 1000; ++k) {             // quét lại toàn bộ khoảng khóa
        const int* pa = a.get(k);
        auto it = b.find(k);
        if ((pa == nullptr) != (it == b.end()) || (pa != nullptr && *pa != it->second)) ++khac;
    }
    std::cout << "doi chieu: khac=" << khac << ", size a=" << a.size() << " b=" << b.size()
              << ", lan xoa=" << lanXoa << "\n";
    std::cout << "a: " << a.bucket_count() << " hop, chuoi dai nhat " << a.chuoiDaiNhat() << "\n";

    HashMap<std::string, int> dem;               // (C) khóa là chuỗi: đếm từ
    for (const char* t : {"to", "be", "or", "not", "to", "be"}) {
        const int* c = dem.get(t);
        dem.put(t, c == nullptr ? 1 : *c + 1);
    }
    std::cout << "to=" << *dem.get("to") << " be=" << *dem.get("be") << " not=" << *dem.get("not")
              << " size=" << dem.size() << " co 'xyz': " << (dem.get("xyz") != nullptr) << "\n";
    return 0;
}
```

**Chạy từng dòng** (phần (A): bảng bắt đầu 2 hộp, `BamInt`, `% số hộp`)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3), (7) `put 10`, `put 20` | `10 % 2 = 0`, `20 % 2 = 0`: cùng hộp 0; chèn đầu nên `20` đứng trước `10`. `2 > 2` sai: chưa rehash | hộp 0: 20 → 10 |
| (6), (5) `put 30` | `3 > 2`: nới trước. `rehash(4)`: `20 % 4 = 0`, `10 % 4 = 2`; rồi `30 % 4 = 2` chèn đầu hộp 2 | hộp 0: 20; hộp 2: 30 → 10 |
| (7) `put 40` | `40 % 4 = 0`, chèn đầu hộp 0; `4 > 4` sai | hộp 0: 40 → 20 |
| (6), (5) `put 50` | `5 > 4`: nới lên 8 hộp: `40`→0, `20`→4, `30`→6, `10`→2; rồi `50 % 8 = 2` chèn đầu hộp 2 | hộp 2: 50 → 10 |
| (8) `erase 10` | Hộp 2: `n` = 50 khác khóa (`truoc` = 50), `n` = 10 khớp: `truoc->tiep = n->tiep`, `delete`. Nếu xóa nút đầu thì nhánh `else` sửa đầu hộp | hộp 2: 50 |
| (B) vòng 20 000 lệnh | Mỗi lệnh chọn khóa 0..999 và loại (`0,1`: put, `2`: get, `3`: erase) từ bộ sinh số; chạy trên `a` (bảng của ta) và `b` (`unordered_map`), mỗi chỗ kết quả lệch thì `++khac`; xong quét lại mọi khóa 0..999 | `khac` phải là 0 |
| (C) đếm từ | `get` trả `nullptr` thì ghi 1, không thì ghi `*c + 1`; khóa là `std::string` | `to` → 2, `be` → 2 |

**Kết quả khi chạy:**

```text
  1 khoa, 2 hop: [ 10 ] [ ]
  2 khoa, 2 hop: [ 20 10 ] [ ]
  3 khoa, 4 hop: [ 20 ] [ ] [ 30 10 ] [ ]
  4 khoa, 4 hop: [ 40 20 ] [ ] [ 30 10 ] [ ]
  5 khoa, 8 hop: [ 40 ] [ ] [ 50 10 ] [ ] [ 20 ] [ ] [ 30 ] [ ]
  4 khoa, 8 hop: [ 40 ] [ ] [ 50 ] [ ] [ 20 ] [ ] [ 30 ] [ ]
doi chieu: khac=0, size a=690 b=690, lan xoa=3095
a: 1024 hop, chuoi dai nhat 1
to=2 be=2 not=1 size=4 co 'xyz': 0
```

Mỗi `[ ... ]` là một hộp, đếm từ hộp 0. Dòng `khac=0` là điều quan trọng nhất: 20 000 lệnh ngẫu nhiên (3095 lệnh xóa thành công) cho kết quả y hệt `std::unordered_map`, và sau cùng khớp từng khóa trong 0..999 (các con số đổi nếu đổi hạt giống). `chuoi dai nhat 1` đúng vì `std::hash<int>` của g++ trả chính số đó nên các số liên tiếp không đụng nhau; chuẩn không bảo đảm điều này. Phần (C) cho thấy khóa là `std::string` dùng được ngay nhờ `std::hash<std::string>` có sẵn: đếm từ `to be or not to be` ra `to=2`, `be=2`.

Rehash **không cấp phát nút mới**, nên con trỏ do `get` trả vẫn đúng sau rehash: mình giữ `const int* p = h.get(1)`, `put` thêm 2000 khóa rồi in `*p`, ra `100` và ASan sạch.

### Hàm băm, lũy thừa của 2 và số nguyên tố (thí nghiệm)

Chương trình dưới **không dùng `HashMap`**: đếm 1000 khóa rơi vào hộp nào với ba cách chọn hộp, trên ba bộ khóa (hàm băm là chính khóa). `tron` là bước trộn bit (xor-dịch rồi nhân hằng lớn, để mỗi bit vào ảnh hưởng mọi bit ra). `*std::max_element(đầu, cuối)` là phần tử lớn nhất của dãy (hàm trả iterator nên có dấu `*`).

```cpp
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>

std::uint64_t tron(std::uint64_t h) {            // trộn bit: mỗi bit vào ảnh hưởng mọi bit ra
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    return h;
}

template <class F>
void thu(const char* ten, std::size_t soHop, const std::vector<std::uint64_t>& khoa, F chon) {
    std::vector<int> dem(soHop, 0);
    for (std::uint64_t k : khoa) ++dem[chon(k)];
    int dung = 0;
    for (int d : dem) dung += d > 0;
    std::cout << "  " << ten << ": dung " << dung << "/" << soHop << " hop, hop dong nhat "
              << *std::max_element(dem.begin(), dem.end()) << " khoa\n";
}

void chayBo(const char* ten, std::uint64_t buoc) {
    std::vector<std::uint64_t> khoa;
    for (std::uint64_t i = 0; i < 1000; ++i) khoa.push_back(i * buoc);   // băm = chính khóa
    std::cout << ten << " (1000 khoa, cach nhau " << buoc << ")\n";
    thu("% 1024 (luy thua cua 2)", 1024, khoa, [](std::uint64_t h) { return h % 1024; });
    thu("% 1021 (so nguyen to)  ", 1021, khoa, [](std::uint64_t h) { return h % 1021; });
    thu("tron bit roi & 1023    ", 1024, khoa, [](std::uint64_t h) { return tron(h) & 1023; });
}

int main() {
    chayBo("A", 1);
    chayBo("B", 1024);
    chayBo("C", 1021);
    return 0;
}
```

**Chạy từng dòng** (chỉ phần `thu`, `chayBo`)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `chayBo("A", 1)` | Dựng 1000 khóa `i * buoc` (`buoc` = 1: khóa 0, 1, 2, ...); hàm băm là chính khóa | `khoa` có 1000 số |
| `thu(..., h % 1024)` | Mỗi khóa: lambda `chon` cho số hộp, rồi `++dem[hộp]`; sau đó đếm hộp khác 0 (`dung`) và lấy hộp đông nhất bằng `max_element` | `dem` có 1024 ô đếm |
| `tron(h) & 1023` | Trộn bit trước, rồi lấy 10 bit thấp (`& 1023` cùng ý `& (n - 1)` với `n` = 1024) | như trên |
| `chayBo("B", 1024)`, `("C", 1021)` | Chỉ đổi bước nhảy giữa các khóa: bội của 1024 phá cách `% 1024`, bội của 1021 phá cách `% 1021` | |

**Kết quả khi chạy:**

```text
A (1000 khoa, cach nhau 1)
  % 1024 (luy thua cua 2): dung 1000/1024 hop, hop dong nhat 1 khoa
  % 1021 (so nguyen to)  : dung 1000/1021 hop, hop dong nhat 1 khoa
  tron bit roi & 1023    : dung 630/1024 hop, hop dong nhat 6 khoa
B (1000 khoa, cach nhau 1024)
  % 1024 (luy thua cua 2): dung 1/1024 hop, hop dong nhat 1000 khoa
  % 1021 (so nguyen to)  : dung 1000/1021 hop, hop dong nhat 1 khoa
  tron bit roi & 1023    : dung 654/1024 hop, hop dong nhat 5 khoa
C (1000 khoa, cach nhau 1021)
  % 1024 (luy thua cua 2): dung 1000/1024 hop, hop dong nhat 1 khoa
  % 1021 (so nguyen to)  : dung 1/1021 hop, hop dong nhat 1000 khoa
  tron bit roi & 1023    : dung 635/1024 hop, hop dong nhat 6 khoa
```

Bộ A (khóa liên tiếp): cả hai cách `%` **hoàn hảo**; trộn bit cho cỡ ném ngẫu nhiên (hộp đông nhất 5 đến 6 khóa là bình thường khi tải gần 1). Bộ B (cách nhau 1024: mã số nhân 1024, hay địa chỉ căn lề): lũy thừa của 2 **sụp** (cả 1000 khóa vào một hộp), nguyên tố ổn. Bộ C (cách nhau 1021): ngược lại. Trộn bit không sụp ở bộ nào. Kết luận: lũy thừa của 2 **cần** hàm băm tốt hoặc bước trộn; nguyên tố chịu được hàm băm yếu nhưng đắt hơn mỗi lần chọn hộp và không miễn nhiễm.

`h & (n - 1)` thay `h % n`: `&` giữa hai số là "và từng bit". Với `n = 8` (nhị phân `1000`), `n - 1 = 7` (`0111`), nên `h & 7` giữ ba bit thấp của `h`, đúng bằng phần dư khi chia 8: `13 = 1101`, `1101 & 0111 = 0101 = 5 = 13 % 8`. Chỉ đúng khi `n` là lũy thừa của 2.

### Ba bản sai của đề 1

Để đếm, mình thêm vào bản đúng một kiểu khóa **đếm số lần `==` được gọi** (`static inline` là biến chung của cả struct, [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) và hai hàm băm. Mỗi lần chạy: 5000 khóa ngẫu nhiên, `put` hết, rồi `get` đủ 5000 khóa và đọc bộ đếm.

```cpp
// bo-qua-kiem-tra
struct Khoa {
    int v;
    static inline long soSoSanh = 0;
    bool operator==(const Khoa& o) const { ++soSoSanh; return v == o.v; }
};
struct BamTot { std::size_t operator()(const Khoa& k) const { return static_cast<std::size_t>(k.v); } };
struct BamTe  { std::size_t operator()(const Khoa& k) const { return static_cast<std::size_t>(k.v & 63); } };
```

**Sai 1: quên rehash** (xóa cả khối `if (...) rehash(...)` trong `put`; nếu chỉ xóa dòng `rehash` thì `if` nuốt luôn dòng kế và không biên dịch được, mình đã dính). **Sai 2: hàm băm tồi** `BamTe`: chỉ giữ 6 bit thấp nên chỉ có 64 giá trị băm khác nhau, dù rehash bình thường.

```text
co rehash, bam tot   : size=5000, 8192 hop, chuoi dai nhat 5, so lan so sanh khoa khi get 5000 lan = 6519 (1.3038 moi lan)
co rehash, bam te    : size=5000, 8192 hop, chuoi dai nhat 89, so lan so sanh khoa khi get 5000 lan = 199076 (39.8152 moi lan)
khong rehash, bam tot: size=5000, 8 hop, chuoi dai nhat 633, so lan so sanh khoa khi get 5000 lan = 1565073 (313.015 moi lan)
```

Bản đúng so khóa 1,30 lần mỗi `get`. Hàm băm tồi vẫn có 8192 hộp nhưng chỉ dùng được 64 giá trị nên chuỗi dài nhất 89 và **gấp cỡ 30 lần** số lần so khóa. Không rehash thì 5000 khóa chen trong 8 hộp: chuỗi dài nhất 633, **gấp cỡ 240 lần**. Cả hai bản vẫn trả **đúng**, chỉ suy thoái về "tìm tuyến tính trong ít danh sách": cái O(n) của mục 📖 (mình đếm so khóa, không đo giây; số đổi theo hạt giống, tỉ lệ thì không).

**Sai 3: rehash làm mất nút.** Đổi `Nut* tiep = n->tiep;` thành `Nut* tiep = nullptr;` và cuối vòng `n = tiep;` thành `n = n->tiep;`. Lúc đó `n->tiep` đã bị ghi trỏ vào chuỗi **mới** nên vòng lặp lạc sang đó, bỏ sót phần còn lại của chuỗi cũ. Ngay lần rehash đầu, `3 khoa` mà chỉ thấy `20` và `30` (nút `10` lạc mất); `doi chieu: khac=227, size a=869 b=690`; LeakSanitizer báo `2896 byte(s) leaked in 181 allocation(s)` vì nút lạc không ai `delete`.

### Lời giải đề 2: xây dần từng bước

Hai điều mới: `h & (n - 1)` ở trên (nên số ô luôn là lũy thừa của 2); `O{Trang::Dang, k, std::move(v)}` dựng một `O` theo thứ tự thành viên, còn `std::vector<O>(moi)` dựng `moi` ô `O` mặc định (trạng thái `Trong`, khóa và giá trị `{}` tức là rỗng/0).

Năm bước: **(1) ô và trạng thái** (dòng (1), (2)): `enum class Trang { Trong, Dang, BiaMo }`. **(2) tìm** (dòng (5)): từ ô đầu đi vòng tròn (dòng (4)); `Trong` thì dừng "không có"; `Dang` thì so khóa; `BiaMo` thì **đi tiếp**; giới hạn số bước bằng số ô để không lặp vô hạn. **(3) `put`** (dòng (7), (8)): tìm trước; kiểm tải **gồm cả bia mộ**; dò tới ô `Trong` **hoặc bia mộ** đầu tiên và đặt vào (dùng lại bia mộ an toàn vì đã biết khóa chưa có). **(4) `erase`** (dòng (9)): tìm rồi đặt `BiaMo`, xóa luôn khóa và giá trị (`K{}`, `V{}`) để nhả tài nguyên nếu là `string`. **(5) `rehash`** (dòng (6)): `đang có + 1` quá nửa số ô thì gấp đôi, không thì **giữ cỡ** và chỉ dọn bia mộ; chèn lại từng ô `Dang`, không cần kiểm trùng.

```cpp
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iostream>
#include <unordered_map>
#include <utility>
#include <vector>

template <class K, class V, class Hash = std::hash<K>>
class OpenMap {
    enum class Trang { Trong, Dang, BiaMo };     // (1) ba trạng thái của một ô
    struct O {
        Trang tt = Trang::Trong;
        K khoa{};                                // K, V phải dựng mặc định được (lược bớt)
        V giaTri{};
    };
    std::vector<O> o_;                           // (2) số ô luôn là lũy thừa của 2
    std::size_t soDang_ = 0;                     // ô đang chứa dữ liệu
    std::size_t soBiaMo_ = 0;                    // ô bia mộ
    Hash bam_;

    std::size_t dau(const K& k) const { return bam_(k) & (o_.size() - 1); }    // (3)
    std::size_t ke(std::size_t i) const { return (i + 1) & (o_.size() - 1); }  // (4) vòng tròn

    std::size_t tim(const K& k) const {          // chỉ số ô chứa k, hoặc o_.size() nếu không có
        std::size_t i = dau(k);
        for (std::size_t buoc = 0; buoc < o_.size(); ++buoc, i = ke(i)) {
            if (o_[i].tt == Trang::Trong) break;                       // (5) ô trống: hết đường
            if (o_[i].tt == Trang::Dang && o_[i].khoa == k) return i;  // bia mộ: đi tiếp
        }
        return o_.size();
    }

    void rehash() {                              // (6) dọn bia mộ; nới gấp đôi nếu đông thật
        std::size_t moi = ((soDang_ + 1) * 2 > o_.size()) ? o_.size() * 2 : o_.size();
        std::vector<O> cu = std::move(o_);
        o_ = std::vector<O>(moi);
        for (O& c : cu) {
            if (c.tt != Trang::Dang) continue;
            std::size_t i = dau(c.khoa);
            while (o_[i].tt != Trang::Trong) i = ke(i);
            o_[i] = std::move(c);
        }
        soBiaMo_ = 0;
    }

public:
    explicit OpenMap(std::size_t soO = 8) {
        std::size_t n = 8;
        while (n < soO) n *= 2;                  // làm tròn lên lũy thừa của 2
        o_ = std::vector<O>(n);
    }

    bool put(const K& k, V v) {                  // true nếu là khóa mới
        std::size_t i = tim(k);
        if (i != o_.size()) { o_[i].giaTri = std::move(v); return false; }
        if ((soDang_ + soBiaMo_ + 1) * 4 > o_.size() * 3) rehash();   // (7) tải ≤ 3/4, tính cả bia mộ
        i = dau(k);
        while (o_[i].tt == Trang::Dang) i = ke(i);    // (8) dừng ở ô Trong HOẶC bia mộ đầu tiên
        if (o_[i].tt == Trang::BiaMo) --soBiaMo_;     //     dùng lại bia mộ
        o_[i] = O{Trang::Dang, k, std::move(v)};
        ++soDang_;
        return true;
    }

    const V* get(const K& k) const {
        std::size_t i = tim(k);
        return i == o_.size() ? nullptr : &o_[i].giaTri;
    }

    bool erase(const K& k) {
        std::size_t i = tim(k);
        if (i == o_.size()) return false;
        o_[i] = O{Trang::BiaMo, K{}, V{}};       // (9) bia mộ, KHÔNG phải ô trống
        --soDang_;
        ++soBiaMo_;
        return true;
    }

    std::size_t size() const { return soDang_; }
    std::size_t capacity() const { return o_.size(); }
    void in() const {                            // [.] trống   [x] bia mộ   [khóa] dữ liệu
        for (const O& o : o_) {
            if (o.tt == Trang::Trong) std::cout << " [.]";
            else if (o.tt == Trang::BiaMo) std::cout << " [x]";
            else std::cout << " [" << o.khoa << "]";
        }
        std::cout << "\n";
    }
};

struct BamInt {
    std::size_t operator()(int k) const { return static_cast<std::size_t>(k); }
};

int main() {
    OpenMap<int, int, BamInt> m;                 // (A) demo: 8 ô; 5, 13, 21 cùng rơi ô 5
    for (int k : {5, 13, 21}) m.put(k, k * 10);
    std::cout << "sau put 5,13,21:";
    m.in();
    m.erase(13);
    std::cout << "sau erase 13:   ";
    m.in();
    std::cout << "get 21 -> " << (m.get(21) ? *m.get(21) : -1) << "\n";
    m.put(29, 290);                              // 29 cũng rơi ô 5
    std::cout << "sau put 29:     ";
    m.in();

    OpenMap<int, int> a;                         // (B) đối chiếu, xóa nhiều hơn
    std::unordered_map<int, int> b;
    std::uint32_t x = 777;
    auto rnd = [&x]() { x = x * 1664525u + 1013904223u; return x >> 8; };
    int khac = 0;
    for (int i = 0; i < 30000; ++i) {
        int k = static_cast<int>(rnd() % 600);
        unsigned loai = rnd() % 5;               // 0,1: put   2: get   3,4: erase
        if (loai <= 1) {
            bool moiB = b.count(k) == 0;
            b[k] = i;
            if (a.put(k, i) != moiB) ++khac;
        } else if (loai == 2) {
            const int* pa = a.get(k);
            auto it = b.find(k);
            if ((pa == nullptr) != (it == b.end()) || (pa != nullptr && *pa != it->second)) ++khac;
        } else if (a.erase(k) != (b.erase(k) == 1)) {
            ++khac;
        }
    }
    for (int k = 0; k < 600; ++k) {              // quét lại toàn bộ khoảng khóa
        const int* pa = a.get(k);
        auto it = b.find(k);
        if ((pa == nullptr) != (it == b.end()) || (pa != nullptr && *pa != it->second)) ++khac;
    }
    std::cout << "doi chieu: khac=" << khac << ", size a=" << a.size() << " b=" << b.size()
              << ", capacity a=" << a.capacity() << "\n";
    return 0;
}
```

**Chạy từng dòng** (phần (A): 8 ô, `BamInt`; `5`, `13`, `21` đều có `h & 7 = 5`)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3), (8) `put 5, 13, 21` | `5` vào ô 5; `13` gặp ô 5 có người nên sang ô 6; `21` đi qua ô 5, 6 rồi vào ô 7 | ô 5: 5, ô 6: 13, ô 7: 21 |
| (5), (9) `erase 13` | `tim` đi từ ô 5 (khác), tới ô 6 khớp; ô 6 thành bia mộ, `soDang_` giảm, `soBiaMo_` tăng | ô 6: bia mộ |
| (5) `get 21` | Ô 5 khác; ô 6 là bia mộ nên **đi tiếp**; ô 7 khớp, trả `210` | không đổi |
| (5), (8) `put 29` | `tim(29)`: ô 5, ô 6 (bia mộ), ô 7 (khóa 21), ô 0 (trống) thì dừng: chưa có. Chèn: từ ô 5 đang có, ô 6 là bia mộ: **dùng lại**, `soBiaMo_` giảm | ô 6: 29 |
| (B) vòng 30 000 lệnh | Như đề 1 nhưng `rnd() % 5`: hai phần năm lệnh (`3`, `4`) là `erase`, và khóa chỉ 0..599, nên bia mộ sinh ra liên tục; so từng lệnh với `unordered_map`, cuối cùng quét lại 0..599 | `khac` phải là 0 |

**Kết quả khi chạy:**

```text
sau put 5,13,21: [.] [.] [.] [.] [.] [5] [13] [21]
sau erase 13:    [.] [.] [.] [.] [.] [5] [x] [21]
get 21 -> 210
sau put 29:      [.] [.] [.] [.] [.] [5] [29] [21]
doi chieu: khac=0, size a=276 b=276, capacity a=1024
```

`khac=0`: 30 000 lệnh (hai phần năm là xóa) cho kết quả y hệt `unordered_map`, kể cả khi bảng nới từ 8 lên 1024 ô (`capacity` và các số khác chỉ đúng cho hạt giống này).

**Thử thay đổi: giữ `get` qua nhiều `put`.** Với `OpenMap`, `const int* p = n.get(1)`, `put` các khóa 2 đến 20 để ép rehash, rồi `*p`: ASan báo `heap-use-after-free`, vì rehash thay cả mảng ô và `p` trỏ vào mảng cũ đã giải phóng. Còn `HashMap` nối chuỗi thì `*p` vẫn ra `100`. Đó là một lý do chuẩn buộc `unordered_map` dùng nút.

### Bản sai của đề 2: xóa không bia mộ

Sửa đúng một dòng trong `erase`: trả ô về `Trong` thay vì `BiaMo` (và bỏ `++soBiaMo_`).

```cpp
// bo-qua-kiem-tra
bool erase(const K& k) {
    std::size_t i = tim(k);
    if (i == o_.size()) return false;
    o_[i] = O{Trang::Trong, K{}, V{}};           // SAI: ô trống ngay giữa chuỗi dò
    --soDang_;
    return true;
}
```

```text
sau put 5,13,21: [.] [.] [.] [.] [.] [5] [13] [21]
sau erase 13:    [.] [.] [.] [.] [.] [5] [.] [21]
get 21 -> -1
sau put 29:      [.] [.] [.] [.] [.] [5] [29] [21]
doi chieu: khac=2404, size a=584 b=276, capacity a=1024
```

Khóa `21` **vẫn nằm** ở ô 7 nhưng `get 21` ra `-1`: dò từ ô 5 gặp ô 6 trống là dừng. Tệ hơn, `put` một khóa đang có mà bị che như vậy thì không tìm ra nó và **thêm bản thứ hai**: sau 30 000 lệnh bảng sai có `size` 584 trong khi `unordered_map` có 276, và 2404 lệnh cho kết quả khác. Đây là lỗi **sai kết quả**, không chỉ chậm.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết cho anh một hash map. Em xử lý va chạm thế nào, và khi nào nới bảng?"
    Hai họ. **Nối chuỗi**: mỗi hộp là danh sách nút, xóa đơn giản, chịu được tải cỡ 1. **Mở địa chỉ**: một mảng phẳng, va chạm thì dò ô kế; đọc liền nhau nên CPU xử lý nhanh (như `vector`, [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)) nhưng cần tải thấp (≤ 0,5 đến 0,75) và phải có bia mộ. Mình viết nối chuỗi: hộp = `bam(k) % số hộp`; `put` tìm trước để không trùng; nếu `size + 1 > tải tối đa * số hộp` thì gấp đôi số hộp và **nối lại** nút. Nói luôn điều kiện: O(1) trung bình cần hàm băm tản đều và tải bị chặn; xấu nhất O(n). Rồi đối chiếu bằng test với `unordered_map`.
    Nối tiếp: **"Rehash tốn O(n), sao em nói `put` vẫn O(1)?"** Mỗi lần số hộp gấp đôi nên tổng số nút bị nối lại qua mọi lần rehash nhỏ hơn 2n; chia cho n lần `put` ra hằng số: **amortized** O(1), như `push_back` ([Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md)). Nhưng riêng lần rehash thì đắt, nên hệ thống cần độ trễ ổn định mà biết trước cỡ thì cấp trước (`reserve`, bài này chưa cài).

??? question "Vì sao số hộp là lũy thừa của 2? Hàm băm của `int` là chính số đó thì có sao không?"
    Lũy thừa của 2 cho phép `h & (n - 1)` thay `h % n` (thường rẻ hơn) và gấp đôi là tự nhiên, nhưng chỉ dùng **bit thấp**: mình chạy 1000 khóa cách nhau 1024 thì cả 1000 khóa vào **một** hộp. Hàm băm là chính số thì dễ gặp đúng chuyện đó. Chữa bằng một bước **trộn bit**, hoặc chọn số hộp nguyên tố (g++ làm vậy: 13, 29, 59...) dùng mọi bit nhưng đắt hơn và vẫn sụp với khóa là bội của chính số nguyên tố đó (mình cũng đếm). Chuẩn không quy định cách nào.
    Nối tiếp: **"Khóa là con trỏ thì sao?"** Địa chỉ cấp phát thường căn lề 8 hoặc 16 byte nên 3 đến 4 bit thấp luôn bằng 0; băm bằng chính địa chỉ rồi lấy bit thấp thì chỉ cỡ 1/8 đến 1/16 số hộp được dùng. Lại là chuyện trộn bit.

??? question "Mở địa chỉ thì xóa thế nào? Có cách nào không cần bia mộ?"
    Đặt ô thành **bia mộ**: lúc tìm thì đi xuyên qua, lúc `put` thì dùng lại bia mộ đầu tiên (sau khi chắc khóa chưa có). Trả ô về "trống" là sai vì tìm kiếm dừng ở ô trống đầu tiên, nên mọi khóa nằm sau ô đó bị che (mình chạy: `get` trả "không có" cho khóa vẫn còn, và `put` thêm bản thứ hai).
    Nối tiếp: **"Bia mộ chất đống thì sao?"** Tìm khóa **không có** phải dò tới ô trống nên bia mộ kéo dài chuỗi dò: ta tính bia mộ vào tải và rehash dọn chúng (giữ nguyên cỡ nếu khóa thật còn thưa). Cách không dùng bia mộ là **xóa dời lùi**: sau khi xóa một ô, duyệt các ô kế tiếp tới ô trống và dời về lấp lỗ những khóa mà việc dời không đưa nó qua ô đầu của chính nó; `erase` phức tạp hơn, đổi lại không còn bia mộ. Mình chỉ nêu bằng lời, chưa viết ở bài này.

??? question "Bản của em thiếu gì so với `std::unordered_map`? Vì sao thư viện chuẩn dùng nút nối chuỗi? Nếu khóa do người lạ gửi lên thì sao?"
    Thiếu iterator, `operator[]`, `insert`/`emplace`, sao chép/di chuyển, allocator, node handle, `reserve`/`max_load_factor`, `KeyEqual` (danh sách đầy đủ ở mục 📖). Chuẩn đòi tham chiếu/con trỏ tới phần tử không hỏng khi rehash và có giao diện hộp, mà mảng phẳng thì rehash là thay cả mảng (mình chạy: ASan báo `heap-use-after-free`). Còn khóa từ người lạ: họ có thể chọn khóa cùng hộp để mỗi thao tác thành O(n) (mình đếm: chuỗi dài 633 thì ~313 lần so khóa mỗi `get`). Cách chống: hàm băm có hạt giống ngẫu nhiên mỗi lần chạy, hoặc dùng `std::map` có chặn trên O(log n) ([Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md)).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Nói \"O(1)\" mà không nói điều kiện"
    Câu đúng: "O(1) **trung bình**, nếu hàm băm tản đều và rehash giữ tải bị chặn; xấu nhất O(n); rehash là amortized." Người phỏng vấn thường hỏi tiếp đúng chỗ bạn bỏ qua. Chọn số hộp lũy thừa của 2 mà không nhắc tới hàm băm cũng là một dạng bỏ qua điều kiện (thí nghiệm cho thấy sụp một hộp).

!!! warning "Lỗi 2: Trả ô về trống khi xóa trong mở địa chỉ"
    Kết quả là `get` sai và `put` sinh khóa trùng (đã chạy: `size` 584 so với 276). Khi viết bảng trắng, hãy vẽ ba khóa va chạm nằm liền nhau rồi xóa khóa giữa, trước khi gõ dòng `erase`.

!!! warning "Lỗi 3: Làm hỏng chuỗi lúc rehash"
    Đọc `n->tiep` **sau khi** đã ghi đè nó làm lạc nút (mất khóa, rò rỉ; đã chạy). Bản đúng: lấy `tiep` ra trước, rồi mới nối. Biến thể khác: nối nút sang mảng mới nhưng quên tính lại hộp bằng số hộp **mới**, nên khóa nằm sai hộp và `get` không thấy.

!!! warning "Lỗi 4: Quên các trường hợp biên"
    Bảng 0 hộp (`% 0` là chia cho 0, UB), `put` khóa đã có (phải ghi đè, không thêm nút), vòng dò mở địa chỉ khi không còn ô trống (không bao giờ dừng nếu không giới hạn số bước), và so khóa chỉ bằng số băm mà không dùng `==`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="81" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Bảng mở địa chỉ 8 ô như trong bài, hàm băm là chính khóa, ô chọn bằng `h & 7`. `get` đi xuyên bia mộ, còn `put` (sau khi chắc khóa chưa có) dừng ở ô trống **hoặc bia mộ** đầu tiên trên đường dò. Chạy dãy dưới. Khóa `26` nằm ở ô nào?

```text
put 2, put 10, put 18
erase 10
put 26
```

- Ô 2, vì đó là ô đầu của `26` nên nó ghi đè khóa `2` đang ở đó
- Ô 5, vì đó là ô trống đầu tiên nằm sau đoạn đã dò xong
- Ô 3, vì bia mộ đầu tiên trên đường dò được dùng lại
- Ô 4, vì chỉ ô nằm sau bia mộ mới chắc chắn còn trống

<p class="giai-thich" markdown>Ba khóa đầu `2`, `10`, `18` đều có `h & 7 = 2`, nên chúng xếp liền nhau ở ô 2, 3, 4. Xóa `10` biến ô 3 thành bia mộ. `26 & 7 = 2`, nên dò từ ô 2 (đang có khóa khác), ô 3 là bia mộ nên dừng và dùng lại; `put` chỉ được làm vậy vì lần tìm trước đó đã đi hết chuỗi mà không thấy `26`. Ô 2 không bị ghi đè vì khóa khác không được chiếm chỗ của nhau. Ô 5 là ô trống đầu tiên **sau** chuỗi, nhưng bia mộ ở ô 3 đến trước nên được dùng trước. Còn ô 4 vẫn đang giữ khóa `18`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Bảng nối chuỗi như trong bài, khởi đầu 4 hộp, tải tối đa 1,0. `put` kiểm `size + 1 > tải tối đa * số hộp` **trước** khi chèn và nếu đúng thì gấp đôi số hộp. Sau 9 lệnh `put` 9 khóa khác nhau, `bucket_count()` bằng bao nhiêu?

- `4`, vì rehash chỉ chạy khi số khóa vượt quá 16
- `8`, vì chỉ riêng lần thứ năm làm số hộp gấp đôi
- `12`, vì mỗi lần nới chỉ thêm đúng 4 hộp mới
- `16`: lần thứ năm lên 8 hộp, lần thứ chín lên 16

<p class="giai-thich" markdown>Khóa thứ năm: `5 > 4` nên nới lên 8. Khóa thứ chín: `9 > 8` nên nới lên 16 (mình chạy đúng ra 16). Đáp án `8` quên lần nới thứ hai; `12` nhầm phép cộng với phép nhân vì bảng luôn **gấp đôi**; còn `4` nhầm ngưỡng với 16 (ngưỡng là tải 1,0 nhân số hộp hiện tại, không phải một số cố định).</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Bảng nối chuỗi 16 hộp, hộp chọn bằng `h % 16`, hàm băm của số nguyên là chính số đó. Chèn 10 khóa `0, 16, 32, ..., 144` (tải 10/16 nên chưa rehash). Chuỗi dài nhất có bao nhiêu nút?

- `1`, vì 10 khóa khác nhau rải đều qua 16 hộp
- `10`, vì mọi khóa đều có phần dư 0 khi chia cho 16
- `2`, vì tối đa hai khóa chung một hộp khi tải dưới 1
- `4`, vì mỗi hộp chứa tối đa 4 khóa trước khi nới

<p class="giai-thich" markdown>Mọi khóa là bội của 16 nên `h % 16` đều bằng 0: cả 10 khóa vào hộp 0 và chuỗi dài 10 (mình chạy đúng ra 10). Tải 10/16 chỉ là **trung bình**, nó nói nhiều về số hộp chứ không về việc khóa phân bố ra sao, nên không bảo đảm chuỗi ngắn. Không có luật "tối đa hai" hay "tối đa bốn" nào trong bảng này; đây chính là chuyện lũy thừa của 2 với khóa cách đều.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Vì sao `erase` của bảng linear probing phải đánh bia mộ thay vì trả ô về "trống"?

- Vì tìm dừng ở ô trống đầu tiên, nên ô trống giữa chuỗi che các khóa sau nó
- Vì ghi đè một ô đang có người buộc chương trình cấp phát lại bộ nhớ cho ô đó
- Vì rehash cần biết ô nào từng chứa khóa để tính lại số hộp của khóa đó
- Vì chuẩn C++ cấm một bảng băm để trống ô mà trước đó từng chứa dữ liệu

<p class="giai-thich" markdown>Chuỗi dò dựa vào quy tắc "gặp ô trống là khóa không có", nên xóa bằng ô trống làm đứt đường tới mọi khóa nằm sau nó (mình chạy: `get` của khóa còn sống trả "không có"). Việc ghi đè một ô trong mảng không cấp phát gì cả. Rehash chỉ duyệt các ô đang có và không quan tâm ô từng chứa gì. Chuẩn không có luật nào về chuyện này, vì bảng mở địa chỉ là tự chọn của người cài đặt.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Điều kiện nào làm `get` của bảng nối chuỗi là O(1) **trung bình**?

- Số hộp là số nguyên tố, bất kể hàm băm thế nào
- Mỗi hộp là danh sách liên kết chứ không phải mảng
- Không có hai khóa nào được băm ra cùng một số
- Hàm băm tản khóa gần đều, rehash giữ tải bị chặn

<p class="giai-thich" markdown>Chi phí là tính hộp (hằng số) cộng với độ dài chuỗi, và độ dài trung bình bằng tải khi khóa rải đều; rehash giữ tải khỏi tăng. Số nguyên tố giúp với hàm băm yếu nhưng không cứu nổi hàm băm cho mọi khóa một giá trị (mình đếm: chỉ 64 giá trị băm thì chuỗi dài 89). Kiểu hộp không quyết định độ dài chuỗi. Còn đòi mọi khóa có số băm khác nhau là băm hoàn hảo, không ai yêu cầu và cũng không cần: đụng độ là chuyện bình thường, chuỗi lo việc đó.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Một bản bảng mở địa chỉ chỉ tính ô **đang có** vào hệ số tải (không tính bia mộ), chạy lâu với `put`/`erase` xen kẽ. Lúc nào cũng chỉ có khoảng 100 khóa trên 1024 ô, vậy mà `get` của khóa **không có** ngày càng chậm. Nguyên nhân và cách chữa hợp lý nhất?

- Rehash chạy quá dày; hãy nâng ngưỡng tải lên cao hơn nữa
- Bia mộ chiếm ô, kéo dài chuỗi dò; tính bia mộ vào tải để dọn
- Hàm băm bị suy giảm theo thời gian; hãy đổi sang hàm băm khác
- Bảng đã đầy khóa thật; hãy nới gấp đôi mỗi khi nó chậm đi

<p class="giai-thich" markdown>Mỗi `erase` để lại một bia mộ, và `put` vào ô khác có thể không dùng lại nó; bia mộ không bao giờ trở thành ô trống, nên chuỗi dò nối dài dần. Tìm khóa vắng phải dò tới ô **trống**, nên bị ảnh hưởng nhiều nhất. Bản trong bài tính bia mộ vào tải và rehash dọn chúng. Hàm băm không "suy giảm" theo thời gian. Rehash không chạy nhiều ở đây vì tải đang-có thấp, và nới gấp đôi không đúng bệnh: khóa thật mới 100 trên 1024 ô.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Đọc đoạn sau, với `OpenMap` đúng như trong bài. Dòng `for` chắc chắn làm bảng rehash. Chuyện gì xảy ra ở dòng cuối?

```text
OpenMap<int, int> m;                         // 8 ô
m.put(1, 100);
const int* p = m.get(1);
for (int k = 2; k <= 20; ++k) m.put(k, k);   // chắc chắn rehash
std::cout << *p;
```

- Hành vi không xác định: rehash thay mảng ô nên `p` treo
- In `100`, vì rehash chép giá trị sang mảng mới nên `p` vẫn còn hợp lệ
- In `100`, vì `p` là con trỏ `const` nên rehash không được làm hỏng nó
- In `1`, vì `p` trỏ vào khóa của phần tử chứ không trỏ vào giá trị

<p class="giai-thich" markdown>Rehash dựng mảng ô mới rồi hủy mảng cũ, nên `p` (trỏ vào mảng cũ) treo; dùng nó là hành vi không xác định (mình chạy: ASan báo `heap-use-after-free`). Chép giá trị sang mảng mới không cập nhật được các con trỏ bên ngoài. `const` chỉ cấm **sửa** qua `p`, không giữ vùng nhớ sống. `get` trả địa chỉ của **giá trị**, không phải của khóa. Với bảng nối chuỗi thì ngược lại: nút không dời, `*p` vẫn là 100.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Khóa là con trỏ cấp phát bằng `new`; giả sử mọi địa chỉ căn lề 16 byte, nên 4 bit thấp luôn bằng 0. Hàm băm là chính địa chỉ, số hộp là 1024 và chọn hộp bằng `h & 1023`. Chuyện gì xảy ra?

- Dùng đều cả 1024 hộp, vì hai địa chỉ khác nhau luôn cho hai hộp khác nhau
- Mọi khóa rơi vào hộp 0, vì 4 bit thấp bằng 0 nghĩa là cả địa chỉ bằng 0
- Chỉ dùng tối đa 64 hộp (1024 / 16): chuỗi dài gấp cỡ 16 lần
- Bảng không chạy được, vì địa chỉ quá lớn để dùng làm đầu vào của hàm băm

<p class="giai-thich" markdown>`h & 1023` giữ 10 bit thấp; 4 bit thấp nhất luôn 0 nên chỉ còn 6 bit biến thiên, tức tối đa 64 giá trị. Vì vậy không dùng đều cả 1024 hộp: hai địa chỉ khác nhau ở bit cao vẫn trùng bit thấp, nên vẫn chung hộp. Nhưng cũng không phải mọi khóa vào hộp 0, vì 6 bit kia vẫn khác nhau. Địa chỉ lớn không phải vấn đề, hàm băm cứ nhận số bất kỳ. Chữa bằng bước trộn bit trước khi lấy bit thấp, hoặc số hộp nguyên tố.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Hash map tự cài = **hàm băm** + **chọn hộp** + **xử lý va chạm** + **nới bảng**. Nối chuỗi: mỗi hộp là danh sách nút, `put` tìm trước rồi chèn đầu chuỗi, kiểm tải trước khi chèn, rehash **nối lại nút** (không chép, nên con trỏ tới phần tử vẫn đúng) và phải lấy `tiep` ra trước khi ghi đè (làm sai thì mất nút: `khac=227`, LeakSanitizer báo rò rỉ).
2. Mở địa chỉ (linear probing): mảng phẳng, ba trạng thái ô (trống, đang có, **bia mộ**); tìm dừng ở ô trống, đi xuyên bia mộ; `put` dùng lại bia mộ đầu tiên sau khi chắc khóa chưa có; xóa bằng ô trống thì sai kết quả (mình chạy: `get 21 -> -1`, `size` 584 so với 276); bia mộ tính vào tải và rehash dọn. Rehash thay cả mảng nên con trỏ tới phần tử hỏng (ASan: `heap-use-after-free`).
3. "O(1) trung bình" cần hàm băm tản đều và tải bị chặn; xấu nhất O(n). Mình đếm số lần so khóa mỗi `get`: 1,30 (đúng), 39,8 (hàm băm chỉ 64 giá trị), 313 (không rehash). Linear probing nên giữ tải ≤ 0,5 đến 0,75: số ô phải xem khi khóa vắng cỡ `(1 + 1/(1−tải)²)/2`, mô phỏng khớp (2,5 / 8,5 / 50,5 ở tải 0,5 / 0,75 / 0,9).
4. Lũy thừa của 2: `h & (n - 1)` rẻ và gấp đôi tự nhiên nhưng chỉ dùng bit thấp (khóa cách nhau 1024 sụp vào một hộp; địa chỉ căn lề cũng vậy), chữa bằng trộn bit; số nguyên tố: `h % p` dùng mọi bit nhưng đắt hơn, cần bảng số nguyên tố, và sụp với khóa là bội của `p` (g++ dùng 13, 29, 59...; chuẩn không quy định).
5. So với `std::unordered_map` bản tự cài lược iterator, `operator[]`, `insert`/`emplace`, sao chép/di chuyển, allocator, node handle, `reserve`/`max_load_factor`, `KeyEqual`, bảo đảm ngoại lệ; chuẩn đòi tham chiếu ổn định qua rehash nên gần như buộc dùng nút nối chuỗi. Kết quả `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined` sạch; nhưng dùng thật thì luôn dùng bản của thư viện chuẩn.
