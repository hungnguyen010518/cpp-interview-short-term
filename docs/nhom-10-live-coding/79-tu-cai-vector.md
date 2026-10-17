# Bài 79 — Live-coding: tự cài vector

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng `Vector<T>` đúng ngay lần đầu: ba biến (`d_`, `n_`, `cap_`), xin **bytes thô** rồi dựng từng phần tử bằng **placement new** (không `new T[]`), `push_back` gấp đôi, `reserve`, hàm hủy gọi `~T()` từng phần tử, **Rule of 5**; và chứng minh bằng bộ đếm rằng move `noexcept` thì lúc đổi nhà vector **move** (sao chép 0), thiếu thì **copy** (sao chép 1023 trong 1000 lần `push_back`).
    - Viết `emplace_back`, `insert`/`erase` giữa, iterator là `T*`; nói đúng iterator nào hỏng khi nào, và vì sao `push_back(v[0])` lúc đổi nhà phải dựng phần tử mới **trước** khi trả khối cũ (bản sai: ASan báo `heap-use-after-free`).
    - Phân tích amortized O(1), và nói rõ bản tự cài lược bớt gì so với `std::vector` thật (allocator, `shrink_to_fit`...).

**Bạn cần biết trước:** [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (size, capacity, đổi nhà), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator như con trỏ, vô hiệu hóa, `it = v.erase(it)`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new` làm hai việc, `malloc` xin bytes thô), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (sao chép sâu), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (move, `noexcept`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (hàm hủy, `try`/`catch`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template, tham số không phải kiểu), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda `[&]`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UB, ASan).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đưa bạn cây bút: "Đừng dùng `std::vector`. Viết cho tôi một `Vector<T>` của riêng bạn: `push_back`, `[]`, tự lớn khi đầy, sao chép và di chuyển đúng. Ba mươi phút, vừa viết vừa nói." Anh không chấm cú pháp. Anh nghe bạn có trả lời được: vì sao không `new T[]`, vì sao gấp đôi, vì sao `noexcept`, và chuyện gì xảy ra với `push_back(v[0])`.

Bài này nằm trong **xưởng tự lắp đồ**: thay vì dùng kệ mua sẵn, ta **tự tháo máy ra xem từng bánh răng**. Hình ảnh chính vẫn là kệ sách của [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md): tấm ván xin ở kho là **bytes thô** (ô trống, chưa có cuốn nào), đặt một cuốn lên ô là **dựng một đối tượng**, nhấc cuốn ra vứt là **hủy một đối tượng**. `new T[n]` giống mua kệ đã nhồi sẵn n cuốn sách mẫu: không phải thứ ta muốn.

!!! info "Chỗ nào ví von này không còn đúng?"
    Kệ thật cho bạn thấy ô nào đang có sách. Ô nhớ thì chỉ là bytes: nó có đối tượng sống hay không **không ghi ở đâu cả**, chỉ có `n_` trong đầu bạn biết. Quên một bước là lỗi mà trình biên dịch không thấy; chỉ sanitizer hoặc bộ đếm bắt được.

## 📖 Giải thích

### Ba mảnh ghép cú pháp cần biết trước khi viết

**1. Xin bytes thô, rồi dựng đối tượng vào đó.** `::operator new(soByte)` xin `soByte` bytes ở heap và **không chạy hàm tạo nào** (cùng loại với `malloc`, [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md)); `::operator delete(p)` trả khối đó mà **không chạy hàm hủy**. (`::` đứng đầu nghĩa là "hàm toàn cục", tránh lẫn với `operator new` riêng của một lớp.) Muốn dựng đối tượng vào ô có sẵn, dùng **placement new** (dựng tại chỗ): `::new (p) T(đối số...)` chỉ chạy hàm tạo của `T` tại địa chỉ `p`, không xin thêm gì.

**2. Hủy bằng tay.** Placement new không có `delete` đi kèm: muốn hủy đối tượng mà **giữ ô nhớ**, gọi thẳng hàm hủy `p->~T();`. Nhờ vậy ta tách được bốn việc mà `new`/`delete` dính liền nhau: xin ô, dựng, hủy, trả ô. Vector cần đúng sự tách đó, vì các ô dư (từ `n_` đến `cap_`) chưa có đối tượng nào.

```text
::operator new(4 * sizeof(T))     // xin ô: 4 ô thô, chưa có T nào
::new (d + 0) T(10)               // dựng: ô 0 có T sống
d[0].~T()                         // hủy: ô 0 lại là bytes thô (ô vẫn của ta)
::operator delete(d)              // trả cả khối
```

**3. `std::move_if_noexcept(x)`** (`<utility>`) là bản thận trọng của `std::move`: trả `T&&` (nên hàm tạo **di chuyển** được chọn) nếu move của `T` hứa `noexcept` (hoặc `T` không sao chép được); ngược lại trả `const T&` (nên hàm tạo **sao chép** được chọn). [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) đã gọi tên nó; hôm nay ta tự viết dòng gọi. Placement new còn được dạy kỹ hơn (kèm memory pool) ở [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md).

### Đề 1: `Vector<T>` với `push_back` tăng gấp đôi, placement new và Rule of 5

!!! example "Đề bài 1"
    **Ràng buộc.** `Vector<T>` (template) có `size()`, `capacity()`, `operator[]`, `reserve(k)`, `push_back` (hai bản: `const T&` và `T&&`), `pop_back()`. Hết chỗ thì **tăng gấp đôi** (0 lên 1). `T` **không bắt buộc có hàm tạo mặc định**. Mỗi phần tử dựng và hủy đúng một lần. Sao chép sâu; move lấy mảng của nguồn và không ném. Nếu `T` ném khi sao chép giữa lúc đổi nhà thì vector phải **như chưa gọi** (strong guarantee). Chỉ thư viện chuẩn C++17.

    **Đầu vào/đầu ra (bài test).** Kiểu đếm `Vat` (đếm tạo, sao chép, di chuyển, hủy). 1000 lần `push_back(Vat(i))` vào vector rỗng rồi hủy vector: mong đợi `capacity=1024` và **số đối tượng còn sống = 0**. Hai bản `Vat` chỉ khác `noexcept` ở hàm di chuyển phải cho số sao chép khác nhau (có: 0; không: 1023).

??? tip "Gợi ý 1"
    Hỏi trước: vector cần nhớ **ba thứ gì**, và ô nhớ có **hai trạng thái nào**? (Một con trỏ, hai con số; ô `[0, n_)` có đối tượng sống, ô `[n_, cap_)` chỉ là bytes thô.)

??? tip "Gợi ý 2"
    Đừng dùng `new T[cap]`: nó dựng cả `cap` đối tượng ngay, đòi `T()` mặc định. Xin bytes bằng `::operator new`, dựng từng phần tử bằng placement new, hủy từng phần tử bằng `~T()`. Lúc đầy: xin khối mới, dựng phần tử mới, chuyển các phần tử cũ sang, hủy và trả khối cũ.

??? tip "Gợi ý 3"
    Khung `push_back` khi đầy: `capMoi = cap_ ? 2 * cap_ : 1`; xin `moi`; dựng phần tử mới ở `moi + n_` **trước tiên**; chuyển `n_` phần tử cũ bằng `std::move_if_noexcept`; hủy cũ, trả cũ, đổi `d_`. Vì sao "phần tử mới trước"? Bản sai 2 bên dưới trả lời.

Ba biến và bất biến (điều luôn phải đúng) của chúng:

| Biến | Ý nghĩa | Bất biến |
|---|---|---|
| `d_` | địa chỉ khối bytes thô | `nullptr`, hoặc trỏ khối có đúng `cap_` ô |
| `n_` | số phần tử đang sống | `n_ <= cap_`; ô `[0, n_)` có đối tượng sống |
| `cap_` | số ô của khối | ô `[n_, cap_)` là bytes thô: **không được** gọi `~T()` lên chúng |

### Đề 2: `insert`/`erase` giữa, iterator invalidation và `emplace_back`

!!! example "Đề bài 2"
    **Ràng buộc.** Thêm `begin()`/`end()` (iterator **là con trỏ** `T*`), `emplace_back(đối số...)` (dựng ngay trong ô cuối, trả tham chiếu tới nó), `insert(pos, x)` (chèn trước `pos`, trả iterator tới phần tử vừa chèn), `erase(pos)` (trả iterator tới phần tử kế tiếp). `v.insert(v.begin(), v[2])` (đưa chính phần tử của vector vào) phải đúng, kể cả khi vector đầy. Nêu và **chạy** iterator nào hỏng sau mỗi thao tác.

    **Đầu vào/đầu ra (bài test).** `1 2 3 4 5` rồi `insert` giữa/đầu, `erase`, xóa mọi số chẵn bằng `it = v.erase(it)`: in đúng dãy. `emplace_back(2)` không tốn move nào, `push_back(Vat(1))` tốn một. `insert` vào đầu 1000 phần tử tốn cỡ 1000 phép gán.

??? tip "Gợi ý 1"
    Sau khi chèn, `pos` người gọi đưa vào còn dùng được không? Nếu `insert` phải đổi nhà giữa chừng thì `pos` trỏ vào đâu? Vậy ngay đầu hàm phải đổi `pos` thành thứ **không phụ thuộc khối nhớ**.

??? tip "Gợi ý 2"
    Chèn giữa = chuyển phần tử cuối sang ô mới ở cuối (ô đó chưa có đối tượng: phải **dựng**, không gán), dồn các phần tử còn lại sang phải bằng **phép gán move** (ô đó đang có đối tượng sống), rồi gán giá trị mới vào chỗ trống. Xóa là ảnh gương: dồn sang trái bằng gán, rồi hủy ô cuối.

??? tip "Gợi ý 3"
    Hai bẫy: đối số của `insert` có thể chính là một phần tử của vector mà vòng dồn sẽ đè lên, nên dựng bản sao tạm **trước** khi dồn; và `emplace_back` nên là hàm gốc để `push_back` chỉ gọi nó (cần khuôn mẫu nhận **số lượng đối số tùy ý**, giải thích ở lời giải).

Ý của hướng giải: `insert`/`erase` giữa luôn **O(n)** vì phải dồn các phần tử sau; `push_back` amortized O(1) (mục phân tích). Iterator `T*` của ta là **địa chỉ một ô**, không phải "phần tử": chèn/xóa làm phần tử khác chuyển vào ô đó, đổi nhà làm mọi địa chỉ cũ chết.

## 💻 Ví dụ code

### Lời giải đề 1: xây dần từng bước

Bảy bước, mỗi bước là một câu bạn nói được trên bảng trắng:

| Bước | Viết gì | Nói gì với người phỏng vấn |
|---|---|---|
| 1 | `T* d_ = nullptr; size_t n_ = 0, cap_ = 0;` | "Ba biến: `d_` trỏ khối bytes thô; `n_` ô đầu là đối tượng sống." |
| 2 | `xin(k)`: `static_cast<T*>(::operator new(k * sizeof(T)))` | "Xin bytes, **chưa** dựng gì. Không `new T[]`: nó đòi `T()` và dựng thừa." |
| 3 | còn chỗ: `::new (d_ + n_) T(x); ++n_;` | "Placement new dựng đúng ô thứ `n_`." |
| 4 | đầy: xin `2 * cap_`, dựng phần tử mới, chuyển phần tử cũ, hủy và trả khối cũ | "Dựng cái mới **trước**: `x` có thể đang nằm trong khối cũ." |
| 5 | `~Vector`: `~T()` cho `[0, n_)` rồi `::operator delete(d_)` | "Hủy từng phần tử, không đụng ô dư; rồi trả khối." |
| 6 | sao chép sâu; move lấy con trỏ; gán kiểu copy-and-swap ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)): chép vào bản tạm `tam` rồi `swap(tam)`, trong đó `std::swap(x, y)` (`<utility>`) hoán đổi hai biến | "Rule of 5: tự viết hàm hủy thì quyết định cả năm hàm. Bản tạm mang ruột cũ của tôi đi hủy." |
| 7 | chuyển phần tử cũ bằng `std::move_if_noexcept`; move của vector `noexcept` | "Chỉ move khi move không ném, còn lại copy, để lỡ ném thì khối cũ còn nguyên." |

Bản đầy đủ gom bảy bước, thêm bộ đếm `Vat` để kiểm. Bốn chỗ cú pháp mới:

- `template <bool NX> struct Vat`: tham số khuôn mẫu là giá trị `true`/`false` ([Bài 34](../nhom-4-oop-patterns/34-template.md) mục 3); `noexcept(NX)` nghĩa là "hứa `noexcept` khi `NX` là `true`". Vậy `Vat<true>` và `Vat<false>` y hệt nhau, chỉ khác lời hứa ở hàm di chuyển.
- `static inline int tao = 0, ...`: biến `static` là **một bản dùng chung** cho mọi đối tượng của kiểu; `inline` (C++17) cho phép đặt giá trị ngay trong thân lớp. Mỗi `Vat<NX>` có bộ đếm riêng.
- `throw;` đứng một mình trong `catch (...)` nghĩa là "ném lại đúng ngoại lệ đang bắt": dọn dẹp xong thì cho người gọi biết.
- `them(F dung)` (template hàm, `F` được suy ra là kiểu của lambda): hai `push_back` chỉ khác nhau cách dựng phần tử mới, nên phần đổi nhà viết **một lần** trong `them`, nhận lambda `dung(cho)` dựng phần tử vào ô `cho`.

```cpp
#include <cstddef>
#include <iostream>
#include <new>
#include <stdexcept>
#include <utility>

template <typename T>
class Vector {
public:
    Vector() = default;                                                  // (1)
    ~Vector() { huy(d_, n_); ::operator delete(d_); }                    // (2)
    Vector(const Vector& o) {                                            // (3)
        d_ = xin(o.n_);
        std::size_t xong = 0;
        try { for (; xong < o.n_; ++xong) ::new (d_ + xong) T(o.d_[xong]); }
        catch (...) { huy(d_, xong); ::operator delete(d_); throw; }
        n_ = cap_ = o.n_;
    }
    Vector(Vector&& o) noexcept : d_(o.d_), n_(o.n_), cap_(o.cap_) {     // (4)
        o.d_ = nullptr; o.n_ = o.cap_ = 0;
    }
    Vector& operator=(const Vector& o) {                                 // (5)
        if (this != &o) { Vector tam(o); swap(tam); }
        return *this;
    }
    Vector& operator=(Vector&& o) noexcept {                             // (6)
        if (this != &o) { Vector tam(std::move(o)); swap(tam); }
        return *this;
    }
    void swap(Vector& o) noexcept {
        std::swap(d_, o.d_); std::swap(n_, o.n_); std::swap(cap_, o.cap_);
    }

    std::size_t size() const { return n_; }
    std::size_t capacity() const { return cap_; }
    T& operator[](std::size_t i) { return d_[i]; }
    const T& operator[](std::size_t i) const { return d_[i]; }

    void reserve(std::size_t k) {                                        // (7)
        if (k <= cap_) return;
        T* moi = xin(k);
        try { chuyen(moi); } catch (...) { ::operator delete(moi); throw; }
        huy(d_, n_); ::operator delete(d_);
        d_ = moi; cap_ = k;
    }
    void push_back(const T& x) { them([&](T* cho) { ::new (cho) T(x); }); }
    void push_back(T&& x) { them([&](T* cho) { ::new (cho) T(std::move(x)); }); }
    void pop_back() { d_[--n_].~T(); }                                   // (8)

private:
    T* d_ = nullptr;            // mảng thô: cap_ ô, n_ ô đầu đang có đối tượng sống
    std::size_t n_ = 0;
    std::size_t cap_ = 0;

    static T* xin(std::size_t k) {                                       // (9)
        return k ? static_cast<T*>(::operator new(k * sizeof(T))) : nullptr;
    }
    static void huy(T* p, std::size_t k) { for (std::size_t i = 0; i < k; ++i) p[i].~T(); }
    void chuyen(T* moi) {                                                // (10)
        std::size_t xong = 0;
        try { for (; xong < n_; ++xong) ::new (moi + xong) T(std::move_if_noexcept(d_[xong])); }
        catch (...) { huy(moi, xong); throw; }
    }
    template <typename F>
    void them(F dung) {                                                  // (11)
        if (n_ < cap_) { dung(d_ + n_); ++n_; return; }
        std::size_t capMoi = cap_ == 0 ? 1 : 2 * cap_;
        T* moi = xin(capMoi);
        bool daDung = false;
        try { dung(moi + n_); daDung = true; chuyen(moi); }
        catch (...) { if (daDung) moi[n_].~T(); ::operator delete(moi); throw; }
        huy(d_, n_); ::operator delete(d_);
        d_ = moi; cap_ = capMoi; ++n_;
    }
};

// ---- bộ đếm: mỗi Vat<NX> có bộ đếm riêng; NX = move có noexcept hay không ----
template <bool NX>
struct Vat {
    static inline int tao = 0, sao = 0, chuyenN = 0, huyN = 0;
    int id;
    Vat(int i) : id(i) { ++tao; }
    Vat(const Vat& o) : id(o.id) { ++sao; }
    Vat(Vat&& o) noexcept(NX) : id(o.id) { ++chuyenN; }
    Vat& operator=(const Vat&) = default;
    ~Vat() { ++huyN; }
    static void dat0() { tao = sao = chuyenN = huyN = 0; }
    static int song() { return tao + sao + chuyenN - huyN; }
};

// kiểu "hay hỏng": lần sao chép thứ conLai (kể từ lúc đặt) ném ngoại lệ; move KHÔNG noexcept
struct Nem {
    static inline int conLai = 0, song = 0;
    int id;
    Nem(int i) : id(i) { ++song; }
    Nem(const Nem& o) : id(o.id) { if (conLai > 0 && --conLai == 0) throw std::runtime_error("hong"); ++song; }
    Nem(Nem&& o) : id(o.id) { ++song; }
    ~Nem() { --song; }
};

template <bool NX>
void thu(const char* ten, bool reserveTruoc) {
    using V = Vat<NX>;
    V::dat0();
    {
        Vector<V> v;
        if (reserveTruoc) v.reserve(1000);
        for (int i = 0; i < 1000; ++i) v.push_back(V(i));
        std::cout << ten << ": cap=" << v.capacity() << " tao=" << V::tao << " sao=" << V::sao
                  << " chuyen=" << V::chuyenN;
    }
    std::cout << " | con song sau khi huy = " << V::song() << "\n";
}

int main() {
    thu<true>("noexcept          ", false);
    thu<false>("khong noexcept   ", false);
    thu<false>("khong noexcept+reserve", true);

    Vector<Vat<true>> a;
    for (int i = 1; i <= 3; ++i) a.push_back(Vat<true>(i * 10));
    Vector<Vat<true>> b = a;
    b[0].id = 99;
    Vector<Vat<true>> c = std::move(a);
    a = b;
    a = a;
    std::cout << "c[0]=" << c[0].id << " b[0]=" << b[0].id << " a[0]=" << a[0].id << " a.size=" << a.size() << "\n";

    Vector<Nem> n;
    for (int i = 1; i <= 4; ++i) n.push_back(Nem(i));                   // size 4, capacity 4: dang day
    Nem x(5);
    Nem::conLai = 3;                                                     // lan sao chep thu 3 se nem
    try { n.push_back(x); }
    catch (const std::exception& e) {
        std::cout << "bat duoc '" << e.what() << "': size=" << n.size() << " cap=" << n.capacity()
                  << " noi dung=" << n[0].id << n[1].id << n[2].id << n[3].id << " Nem con song=" << Nem::song << "\n";
    }
    return 0;
}
```

**Chạy từng dòng** (đoạn đầu của `main` với `Vector<Vat<true>>`; địa chỉ minh họa — máy bạn sẽ in số khác)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `Vector<Vat<true>> a;` → (1) | Không xin gì: `d_` rỗng, `n_ = cap_ = 0` | `d_ → ∅` |
| `a.push_back(Vat(10))` → (11) | `n_ == cap_` (0 = 0): `capMoi = 1`, `xin(1)` (9) cho một ô thô; dựng phần tử mới (move từ tạm); `chuyen` (10) không có phần tử cũ; `delete(nullptr)` vô hại | `0x1000: [10]` |
| `a.push_back(Vat(20))` | Đầy: khối 2 ô ở `0x2000`; **dựng 20 ở ô 1 trước**; `chuyen` **move** `10` sang ô 0 (vì `Vat<true>` có `noexcept`); hủy `10` cũ; trả `0x1000` | `0x2000: [10 20]` |
| `a.push_back(Vat(30))` | Đầy: khối 4 ô; dựng 30; chuyển hai phần tử; hủy hai cũ; trả khối | `[10 20 30 _]`, ô cuối thô |
| `Vector b = a;` → (3) | Xin đúng 3 ô, **sao chép** từng phần tử bằng placement new; lỡ ném thì `catch` hủy phần đã dựng, trả khối, `throw;` | hai khối riêng |
| `Vector c = std::move(a);` → (4) | Lấy `d_`, `n_`, `cap_` của `a`, đặt `a` về rỗng: không tạo/sao chép/di chuyển phần tử nào | `a: ∅`, `c` giữ khối cũ |
| `a = b; a = a;` → (5) | Sao chép vào `tam` rồi `swap`: `tam` mang khối cũ của `a` đi hủy; `a = a` bị `this != &o` bỏ qua | `a` có bản của `b` |
| hết `main` → (2) | `~Vector`: hủy từng phần tử `[0, n_)`, rồi trả khối | `con song = 0` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`; **sạch**: không cảnh báo khi biên dịch, ASan/UBSan im lặng, thoát mã 0):

```text
noexcept          : cap=1024 tao=1000 sao=0 chuyen=2023 | con song sau khi huy = 0
khong noexcept   : cap=1024 tao=1000 sao=1023 chuyen=1000 | con song sau khi huy = 0
khong noexcept+reserve: cap=1000 tao=1000 sao=0 chuyen=1000 | con song sau khi huy = 0
c[0]=10 b[0]=99 a[0]=99 a.size=3
bat duoc 'hong': size=4 cap=4 noi dung=1234 Nem con song=5
```

Các số là phép đếm của chính code này nên **tất định**, không phụ thuộc máy hay `-O` (riêng `cap=1024` đúng vì ta tự chọn gấp đôi từ 1; thư viện khác có thể ra số khác). Đọc kết quả:

- **`chuyen=2023`, `sao=0`.** Có `noexcept`: 1000 lần chuyển để dựng phần tử mới, cộng 1023 lần lúc đổi nhà (`1 + 2 + ... + 512`), không sao chép lần nào.
- **`sao=1023`.** Cùng code và cùng kiểu, bỏ đúng chữ `noexcept`: 1023 lần đổi nhà đó thành **sao chép**. Đó là `std::move_if_noexcept` làm việc.
- **Dòng có `reserve(1000)`.** Không đổi nhà lần nào, nên không `sao` dù thiếu `noexcept`.
- **`con song = 0`** ở cả ba: tạo + sao chép + di chuyển = số lần hủy. Đây là **bài kiểm rò rỉ rẻ nhất**: mỗi đối tượng dựng ra bị hủy đúng một lần.
- **`bat duoc 'hong': size=4 cap=4 noi dung=1234 Nem con song=5`.** `Nem` không `noexcept` nên đổi nhà **sao chép**, và lần sao chép thứ 3 ném. Vector còn nguyên (size, capacity, nội dung); 5 đối tượng sống là 4 trong vector và `x`: phần đã dựng ở khối mới bị hủy, khối mới được trả. Đó là **strong guarantee** của đề.

Vì sao không move luôn cho nhanh? Move lấy ruột phần tử cũ; nếu nó ném ở phần tử thứ 3 thì hai phần tử đầu **đã bị lấy ruột** và không trả về được: vector hỏng. Copy thì phần tử cũ còn nguyên, bỏ khối mới là xong. Nên: move chỉ khi move **không thể ném**. Phần `noexcept` và xử lý lỗi nói kỹ ở [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md).

**Thử thay đổi.** Mình đã chạy hai biến thể (biên dịch sạch, chạy với ASan/UBSan).

1. **Bỏ `huy(d_, n_);` khỏi hàm hủy (2).** Bộ đếm in `con song sau khi huy = 1000` ở cả ba dòng. Với `Vector<std::string>` ba chuỗi 40 ký tự, LeakSanitizer báo `Direct leak of 123 byte(s) in 3 object(s)`. Với `Vat` (không giữ heap) LeakSanitizer **im lặng**: chỉ bộ đếm bắt được.
2. **Bỏ `if (this != &o)` khỏi cả hai phép gán.** Kết quả y hệt (mình chạy thêm `a = std::move(a)`): nhờ copy-and-swap tự gán vẫn đúng; dòng `if` chỉ tránh một lần sao chép vô ích.

### Ba bản SAI của đề 1, đã chạy thật

**Sai 1: `new T[cap]`** (người mới hay viết). Nó dựng ngay `cap` đối tượng bằng hàm tạo mặc định, rồi `push_back` chỉ **gán đè** lên đối tượng đã có.

```cpp
// bo-qua-kiem-tra
#include <iostream>

struct Vat {
    int id;
    Vat() : id(0) { std::cout << "tao mac dinh\n"; }
    Vat(int i) : id(i) { std::cout << "tao " << id << "\n"; }
    Vat& operator=(const Vat&) = default;
    ~Vat() { std::cout << "huy " << id << "\n"; }
};

template <typename T>
class VectorSai {
    T* d_ = new T[4];                              // (1) dựng sẵn 4 đối tượng
    int n_ = 0;
public:
    void push_back(const T& x) { d_[n_++] = x; }   // (2) "gán" đè lên đối tượng đã có
    ~VectorSai() { delete[] d_; }
};

int main() {
    VectorSai<Vat> v;
    v.push_back(Vat(7));
    std::cout << "xong\n";
    return 0;
}
```

Kết quả thật: bốn dòng `tao mac dinh` (dòng (1)), rồi `tao 7`, `huy 7` (đối tượng tạm), `xong`, và cuối cùng **bốn** dòng `huy` (ba `huy 0`, một `huy 7`): ba đối tượng "ma" chưa ai đưa vào mà vẫn bị dựng và hủy. Sai về chi phí và về ngữ nghĩa. Xóa dòng `Vat() : id(0) ...` (mình đã chạy) thì g++ báo lỗi biên dịch ở dòng (1): `error: no matching function for call to 'Vat::Vat()'`: kiểu không có hàm tạo mặc định không đặt được vào vector kiểu này.

**Sai 2: trả khối cũ rồi mới dựng phần tử mới, và `push_back(v[0])`.** Đây là "bẫy tự tham chiếu". Dùng `int` cho ngắn; lỗi y hệt với mọi kiểu.

```cpp
// bo-qua-kiem-tra
#include <cstddef>
#include <iostream>
#include <new>

struct VecInt {
    int* d = nullptr;
    std::size_t n = 0, cap = 0;
    void push_back(const int& x) {
        if (n == cap) {
            std::size_t capMoi = cap == 0 ? 1 : 2 * cap;
            int* moi = static_cast<int*>(::operator new(capMoi * sizeof(int)));
            for (std::size_t i = 0; i < n; ++i) moi[i] = d[i];
            ::operator delete(d);               // (1) trả mảng cũ TRƯỚC...
            d = moi; cap = capMoi;
        }
        d[n++] = x;                             // (2) ...rồi mới đọc x, mà x có thể nằm trong mảng cũ
    }
    ~VecInt() { ::operator delete(d); }
};

int main() {
    VecInt v;
    v.push_back(1);
    v.push_back(2);                             // đầy: size = capacity = 2
    v.push_back(v.d[0]);                        // (3) đưa chính phần tử của vector vào
    std::cout << v.d[2] << "\n";
    return 0;
}
```

`x` là **tham chiếu**, ở dòng (3) nó chính là `v.d[0]` trong khối cũ; dòng (1) trả khối đó, dòng (2) đọc `x` từ chỗ đã trả. Mình đã chạy: build thường in một **số rác** (`-313875240` lần này, máy bạn sẽ khác) và thoát được; với `-fsanitize=address` thì báo `heap-use-after-free`, `READ of size 4`, đúng dòng (2), kèm `freed by thread T0 here` ở dòng (1). Bản đúng (lời giải đầy đủ): dựng phần tử mới ở khối mới **trước**, khi khối cũ còn sống; sau đó mới chuyển phần tử cũ và trả khối cũ.

**Sai 3: quên hủy phần tử trong hàm hủy** chính là "Thử thay đổi 1" ở trên: `::operator delete` chỉ trả bytes, **không** gọi `~T()`; hủy từng phần tử là việc của bạn.

### Lời giải đề 2: `emplace_back`, `insert`, `erase`

Ta cần hàm nhận **số lượng đối số tùy ý** rồi đưa nguyên cho hàm tạo của `T`. Cú pháp mới (ba mảnh):

- `template <typename... A>`: `A` là một **danh sách kiểu** (0, 1, 2... kiểu), gọi là *parameter pack*. `A&&... a` là danh sách tham số tương ứng; đây là **tham chiếu chuyển tiếp** (*forwarding reference*), nhận được cả đối tượng có tên (lvalue) lẫn tạm (rvalue).
- `using iterator = T*;` đặt cho `T*` một tên khác là `iterator`, để người dùng viết `Vector<int>::iterator`.
- `std::forward<A>(a)...` (`<utility>`) đưa từng đối số đi tiếp **giữ nguyên** là lvalue hay rvalue (lvalue thì sao chép, rvalue thì di chuyển); `...` sau cùng "bung" ra cho từng đối số.

Vậy `emplace_back(2)` gọi `T(2)` ngay trong ô cuối, còn `push_back(x)` chỉ là `emplace_back(x)` hay `emplace_back(std::move(x))`: cả hai đường dùng chung một chỗ đổi nhà (gọn hơn bản dùng lambda của đề 1). Dòng (8) giữ bản sao tạm, dòng (9) dựng ô mới ở cuối, dòng (10) dồn bằng phép gán.

```cpp
#include <cstddef>
#include <iostream>
#include <new>
#include <utility>

template <typename T>
class Vector {
public:
    using iterator = T*;                                                 // (1)
    using const_iterator = const T*;

    Vector() = default;
    ~Vector() { huy(d_, n_); ::operator delete(d_); }
    Vector(const Vector& o) {
        d_ = xin(o.n_);
        std::size_t xong = 0;
        try { for (; xong < o.n_; ++xong) ::new (d_ + xong) T(o.d_[xong]); }
        catch (...) { huy(d_, xong); ::operator delete(d_); throw; }
        n_ = cap_ = o.n_;
    }
    Vector(Vector&& o) noexcept : d_(o.d_), n_(o.n_), cap_(o.cap_) { o.d_ = nullptr; o.n_ = o.cap_ = 0; }
    Vector& operator=(const Vector& o) { if (this != &o) { Vector tam(o); swap(tam); } return *this; }
    Vector& operator=(Vector&& o) noexcept { if (this != &o) { Vector tam(std::move(o)); swap(tam); } return *this; }
    void swap(Vector& o) noexcept { std::swap(d_, o.d_); std::swap(n_, o.n_); std::swap(cap_, o.cap_); }

    std::size_t size() const { return n_; }
    std::size_t capacity() const { return cap_; }
    T& operator[](std::size_t i) { return d_[i]; }
    const T& operator[](std::size_t i) const { return d_[i]; }
    iterator begin() { return d_; }                                      // (2)
    iterator end() { return d_ + n_; }
    const_iterator begin() const { return d_; }
    const_iterator end() const { return d_ + n_; }

    void reserve(std::size_t k) {
        if (k <= cap_) return;
        T* moi = xin(k);
        try { chuyen(moi); } catch (...) { ::operator delete(moi); throw; }
        huy(d_, n_); ::operator delete(d_);
        d_ = moi; cap_ = k;
    }

    template <typename... A>                                             // (3)
    T& emplace_back(A&&... a) {
        if (n_ < cap_) {
            ::new (d_ + n_) T(std::forward<A>(a)...);                    // (4)
        } else {
            std::size_t capMoi = cap_ == 0 ? 1 : 2 * cap_;
            T* moi = xin(capMoi);
            bool daDung = false;
            try { ::new (moi + n_) T(std::forward<A>(a)...); daDung = true; chuyen(moi); }
            catch (...) { if (daDung) moi[n_].~T(); ::operator delete(moi); throw; }
            huy(d_, n_); ::operator delete(d_);
            d_ = moi; cap_ = capMoi;
        }
        ++n_;
        return d_[n_ - 1];
    }
    void push_back(const T& x) { emplace_back(x); }                      // (5)
    void push_back(T&& x) { emplace_back(std::move(x)); }
    void pop_back() { d_[--n_].~T(); }

    template <typename... A>
    iterator emplace(const_iterator pos, A&&... a) {                     // (6)
        std::size_t i = pos - d_;                                        // (7)
        if (i == n_) { emplace_back(std::forward<A>(a)...); return d_ + i; }
        T tam(std::forward<A>(a)...);                                    // (8)
        emplace_back(std::move(d_[n_ - 1]));                             // (9)
        for (std::size_t k = n_ - 2; k > i; --k) d_[k] = std::move(d_[k - 1]);   // (10)
        d_[i] = std::move(tam);                                          // (11)
        return d_ + i;
    }
    iterator insert(const_iterator pos, const T& x) { return emplace(pos, x); }
    iterator insert(const_iterator pos, T&& x) { return emplace(pos, std::move(x)); }
    iterator erase(const_iterator pos) {                                 // (12)
        std::size_t i = pos - d_;
        for (std::size_t k = i; k + 1 < n_; ++k) d_[k] = std::move(d_[k + 1]);
        pop_back();                                                      // (13)
        return d_ + i;                                                   // (14)
    }

private:
    T* d_ = nullptr;
    std::size_t n_ = 0;
    std::size_t cap_ = 0;

    static T* xin(std::size_t k) { return k ? static_cast<T*>(::operator new(k * sizeof(T))) : nullptr; }
    static void huy(T* p, std::size_t k) { for (std::size_t i = 0; i < k; ++i) p[i].~T(); }
    void chuyen(T* moi) {
        std::size_t xong = 0;
        try { for (; xong < n_; ++xong) ::new (moi + xong) T(std::move_if_noexcept(d_[xong])); }
        catch (...) { huy(moi, xong); throw; }
    }
};

struct Vat {                                    // đếm từng loại thao tác
    static inline int tao = 0, sao = 0, chuyenCtor = 0, gan = 0, huyN = 0;
    int id;
    Vat(int i) : id(i) { ++tao; }
    Vat(const Vat& o) : id(o.id) { ++sao; }
    Vat(Vat&& o) noexcept : id(o.id) { ++chuyenCtor; }
    Vat& operator=(const Vat& o) { id = o.id; ++gan; return *this; }
    Vat& operator=(Vat&& o) noexcept { id = o.id; ++gan; return *this; }
    ~Vat() { ++huyN; }
    static void dat0() { tao = sao = chuyenCtor = gan = huyN = 0; }
};

void in(const char* ten, const Vector<int>& v) {
    std::cout << ten << ":";
    for (int x : v) std::cout << " " << x;                               // range-for chạy nhờ begin()/end()
    std::cout << "  (size " << v.size() << ", cap " << v.capacity() << ")\n";
}

int main() {
    Vector<int> v;
    for (int i = 1; i <= 5; ++i) v.push_back(i);
    in("ban dau       ", v);
    v.insert(v.begin() + 2, 99);       in("insert giua 99 ", v);
    v.insert(v.begin(), 0);            in("insert dau 0   ", v);
    v.erase(v.begin() + 1);            in("erase [1]      ", v);
    v.insert(v.begin(), v[3]);         in("insert v[3]    ", v);

    Vector<int> day;                    // đầy sẵn: size = capacity = 4
    for (int i = 1; i <= 4; ++i) day.push_back(i);
    day.insert(day.begin(), day[2]);   in("day+insert v[2]", day);

    for (auto it = v.begin(); it != v.end();) {                          // xóa mọi số chẵn
        if (*it % 2 == 0) it = v.erase(it); else ++it;
    }
    in("xoa so chan   ", v);

    Vector<int> w;
    w.reserve(4);
    for (int i = 0; i < 4; ++i) w.push_back(i * 10);
    int* p0 = &w[0];
    int* p2 = &w[2];
    w.erase(w.begin() + 1);                                              // không đổi nhà: chỉ dồn
    std::cout << "erase [1]: *p2 = " << *p2 << " (truoc do p2 tro vao 20), p0 van = &w[0]? " << (p0 == &w[0]) << "\n";
    w.push_back(1); w.push_back(2);                                      // phần tử thứ 5 vượt capacity 4: đổi nhà
    std::cout << "sau khi doi nha: p0 == &w[0]? " << (p0 == &w[0]) << "\n";

    Vector<Vat> t;
    t.reserve(10);
    Vat::dat0();
    t.push_back(Vat(1));
    std::cout << "push_back(Vat(1)): tao=" << Vat::tao << " chuyen=" << Vat::chuyenCtor << "\n";
    Vat::dat0();
    t.emplace_back(2);
    std::cout << "emplace_back(2):   tao=" << Vat::tao << " chuyen=" << Vat::chuyenCtor << "\n";

    Vector<Vat> lon;
    lon.reserve(1001);
    for (int i = 0; i < 1000; ++i) lon.emplace_back(i);
    Vat::dat0();
    lon.insert(lon.begin(), Vat(-1));
    std::cout << "insert vao dau 1000 phan tu: gan=" << Vat::gan << "\n";
    Vat::dat0();
    lon.erase(lon.begin());
    std::cout << "erase phan tu dau (1001 phan tu): gan=" << Vat::gan << "\n";
    return 0;
}
```

**Chạy từng dòng** (chèn 99 vào vị trí 1 của `10 20 30 40` đang đầy, cap 4, rồi xóa nó; minh họa)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (7) | `i = pos - d_ = 1`: **đổi iterator thành chỉ số** ngay đầu hàm. Nếu sau đó đổi nhà thì `pos` chết, `i` vẫn đúng | `[10 20 30 40]` |
| (8) | `tam` = 99 dựng ngoài vector (nếu 99 là `v[2]` thì vòng dồn sau sẽ đè nó, nên phải giữ bản riêng) | `tam = 99` |
| (9) | `emplace_back(std::move(d_[3]))`: vector đầy nên đổi nhà sang cap 8, rồi dựng bản chuyển của `40` ở ô 4; ô 3 còn sống nhưng đã bị lấy ruột | `[10 20 30 (40) 40]` |
| (10) | Dồn bằng **phép gán** (các ô đó có đối tượng sống): `d_[3] = d_[2]`, rồi `d_[2] = d_[1]` | `[10 20 20 30 40]` |
| (11) | `d_[1] = 99` | `[10 99 20 30 40]` |
| (12)-(14) | `erase(begin() + 1)`: dồn trái `d_[1] = d_[2]`, `d_[2] = d_[3]`, `d_[3] = d_[4]`; (13) `pop_back` **hủy ô cuối** (đã bị lấy ruột); (14) trả `d_ + 1`, giờ chứa `20` | `[10 20 30 40 _]` |

**Kết quả khi chạy** (cùng cờ; sạch, thoát mã 0):

```text
ban dau       : 1 2 3 4 5  (size 5, cap 8)
insert giua 99 : 1 2 99 3 4 5  (size 6, cap 8)
insert dau 0   : 0 1 2 99 3 4 5  (size 7, cap 8)
erase [1]      : 0 2 99 3 4 5  (size 6, cap 8)
insert v[3]    : 3 0 2 99 3 4 5  (size 7, cap 8)
day+insert v[2]: 3 1 2 3 4  (size 5, cap 8)
xoa so chan   : 3 99 3 5  (size 4, cap 8)
erase [1]: *p2 = 30 (truoc do p2 tro vao 20), p0 van = &w[0]? 1
sau khi doi nha: p0 == &w[0]? 0
push_back(Vat(1)): tao=1 chuyen=1
emplace_back(2):   tao=1 chuyen=0
insert vao dau 1000 phan tu: gan=1000
erase phan tu dau (1001 phan tu): gan=1000
```

`day+insert v[2]` chèn **chính phần tử của vector** vào vector đầy (đổi nhà giữa chừng) mà vẫn đúng (`3 1 2 3 4`): nhờ `tam` và nhờ dựng-mới-trước. `xoa so chan` dùng khuôn `it = v.erase(it)` của [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md). `emplace_back(2)` chỉ có `tao=1`, `push_back(Vat(1))` thêm `chuyen=1`. `insert` đầu 1000 phần tử và `erase` đầu 1001 phần tử đều tốn 1000 phép gán: đúng **O(n)**.

**Thử thay đổi: bỏ `tam` (dòng (8)) và gán thẳng `d_[i] = T(std::forward<A>(a)...)` ở cuối.** Mình đã chạy: `insert v[3]` in `99 0 2 99 3 4 5` thay vì `3 0 2 99 3 4 5` (lúc gán, `v[3]` đã bị dồn và chứa `99`, không còn là giá trị lúc gọi), còn `day+insert v[2]` in một số rác đầu dãy (`1582036050` lần này) và ASan báo `heap-use-after-free`, vì đối số tham chiếu vào khối đã bị `emplace_back` trả. Cả hai là cùng một họ lỗi với Sai 2.

**Iterator của bản tự cài hỏng khi nào** (iterator là `T*`, địa chỉ một ô). Đây là hành vi của **bản tự cài**; với `std::vector` thật, chuẩn chỉ bảo đảm phần "còn sống", phần "hỏng" là không hứa gì ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)):

| Thao tác | Còn dùng được | Bằng chứng ở chương trình |
|---|---|---|
| thêm **có đổi nhà** (`push_back`, `emplace_back`, `insert`, `reserve`) | không cái nào (khối cũ bị trả) | `p0 == &w[0]` in `0`: khối mới được xin khi khối cũ còn sống nên địa chỉ chắc chắn khác |
| thêm **không** đổi nhà | `push_back`: mọi iterator cũ còn đúng ô (trừ `end()`); `insert`: chỉ các ô trước `pos`, từ `pos` trở đi mỗi ô chứa phần tử khác | suy ra từ code: `push_back` không đụng ô nào có sẵn |
| `erase(pos)` | các ô trước `pos`; từ `pos` trở đi chứa phần tử dịch lên, ô cuối đã bị hủy | `*p2` in `30`: `p2` vẫn là địa chỉ ô 2, nhưng phần tử ở đó đổi từ `20` thành `30` |

Vì thế `insert` và `erase` trả iterator mới: ai cầm `it` cũ sau khi đổi nhà là cầm một địa chỉ chết. Thói quen: **sau mọi thao tác thay đổi, lấy lại iterator**, hoặc giữ chỉ số.

**Sai 4: `insert` dùng `pos` sau khi đổi nhà.** Mình đã chạy một `VecInt` nhỏ như Sai 2 có hàm `chen(int* pos, int x)`: nếu đầy thì đổi nhà, rồi dồn các phần tử sang phải và gán `*pos = x` bằng chính `pos` người gọi đưa vào (vector đầy `1 2 3 4`, gọi `chen(v.d + 1, 99)`). Build thường: **abort** `double free or corruption (out)`, mã thoát 134. Với `-fsanitize=address`: `heap-buffer-overflow`, `READ of size 4`, `4 bytes to the left of 32-byte region`, ngay trong vòng dồn (nó so sánh `p > pos` giữa hai khối khác nhau nên chạy ra ngoài khối mới). Báo lỗi cụ thể tùy bộ cấp phát và là **UB**; điều chắc chắn chỉ là dùng `pos` cũ sau đổi nhà là sai. Bản đúng là dòng (7): đổi `pos` thành chỉ số **trước** mọi thứ.

### Phân tích: vì sao `push_back` amortized O(1), còn `insert`/`erase` O(n)

Một lần đổi nhà tốn O(n). Nhưng nếu capacity **nhân một hệ số** mỗi lần, đổi nhà thưa dần. Gấp đôi: các lần đổi nhà chuyển 1, 2, 4, ..., 2^k phần tử, tổng dưới hai lần số phần tử: mỗi `push_back` trả **dưới 2 lần chuyển cộng một lần dựng**, tức hằng số. Nếu mỗi lần chỉ **cộng một hằng** (thêm 10 ô) thì số lần đổi nhà tăng tỉ lệ với n và tổng chi phí là **bậc hai**. Chương trình dưới mô phỏng và đếm số "phần tử bị chuyển" cho ba chính sách:

```cpp
#include <iostream>

// Đếm số lần "một phần tử bị chuyển sang mảng mới" khi push_back N phần tử;
// tang(cap) là chính sách tăng capacity lúc đầy.
template <typename F>
long long demChuyen(long long N, F tang) {
    long long chuyen = 0, n = 0, cap = 0;
    for (long long i = 0; i < N; ++i) {
        if (n == cap) { chuyen += n; cap = tang(cap); }   // đầy: chuyển n phần tử cũ
        ++n;
    }
    return chuyen;
}

int main() {
    for (long long N : {1000LL, 100000LL}) {
        long long a = demChuyen(N, [](long long c) { return c == 0 ? 1 : 2 * c; });
        long long b = demChuyen(N, [](long long c) { return c < 2 ? c + 1 : c + c / 2; });
        long long k = demChuyen(N, [](long long c) { return c + 10; });
        std::cout << "N=" << N << ": x2 -> " << a << ", x1.5 -> " << b << ", +10 -> " << k
                  << " (chuyen moi phan tu: " << double(a) / N << " | " << double(b) / N
                  << " | " << double(k) / N << ")\n";
    }
    return 0;
}
```

**Kết quả khi chạy** (phép đếm thuần túy, tất định):

```text
N=1000: x2 -> 1023, x1.5 -> 2137, +10 -> 49500 (chuyen moi phan tu: 1.023 | 2.137 | 49.5)
N=100000: x2 -> 131071, x1.5 -> 276521, +10 -> 499950000 (chuyen moi phan tu: 1.31071 | 2.76521 | 4999.5)
```

Gấp đôi: luôn dưới 2 lần chuyển mỗi phần tử (1,02 và 1,31 ở hai N này; con số dao động theo N so với lũy thừa của 2). Nhân 1,5: dưới 3 lần (2,14 và 2,77), chuyển nhiều hơn nhưng thừa **ít bộ nhớ** hơn. Cộng 10: `4999,5` lần mỗi phần tử ở N=100000 và còn tăng theo N, nên không còn amortized O(1). Vậy không có luật "phải gấp đôi", chỉ có luật "phải nhân một hệ số" (g++ 11 chọn 2; có cài đặt khác chọn 1,5).

| Thao tác | Chi phí | Vì sao |
|---|---|---|
| `[]`, `size`, `pop_back` | O(1) | cộng địa chỉ, hủy một ô cuối |
| `push_back`/`emplace_back` | amortized O(1); riêng một lần có thể O(n) | đổi nhà thưa dần |
| `reserve(n)` đủ trước | thêm n phần tử không đổi nhà lần nào | biết trước thì đừng để vector đoán |
| `insert`/`erase` giữa | O(n) | dồn các phần tử sau |

**Khi nào KHÔNG tự cài vector:** gần như luôn luôn, ngoài phỏng vấn và học tập. `std::vector` đã được kiểm tra kỹ; hãy dùng nó và `reserve` khi biết cỡ.

**Bản này lược bớt gì so với `std::vector` thật** (nói rõ khi bị hỏi): allocator (ta cứng `::operator new`), `shrink_to_fit`, `resize`, `at`, `front`/`back`, `clear`, `assign`, hàm tạo từ `initializer_list` hay `n` phần tử, `insert`/`erase` theo **khoảng**, các phép so sánh, `max_size` (ném `length_error`), phần tử cần căn lề lớn hơn mặc định (C++17 có `operator new` riêng cho căn lề), tối ưu `memcpy`/`memmove` khi `T` đủ đơn giản (thư viện thật có thể làm), iterator là một lớp riêng (an toàn kiểu hơn `T*`), và `vector<bool>` đặc biệt ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)). Về ngoại lệ: `push_back`/`emplace_back`/`reserve` ở đây đạt **strong guarantee** (đã chạy với `Nem`); `insert`/`erase` giữa chỉ đạt mức **cơ bản** (phép gán ném giữa vòng dồn thì dữ liệu hợp lệ nhưng đã đổi dở), và chuẩn cũng chỉ bảo đảm mức đó cho `insert` giữa.

!!! info "Bạn biết Go?"
    `append` của Go là `push_back` của Vector: `len == cap` thì xin mảng lớn hơn và chép sang. Mình chạy 2000 lần `append` vào `[]int` rỗng (go 1.27.2): `cap` đi `4 8 16 32 64 128 256 512 848 1280 1792 2560`, tức gấp đôi tới 256 rồi tăng chậm dần. Khác lớn: Go có GC nên không có hàm hủy từng phần tử và không có "ô thô"; slice cũ vẫn đọc được sau `append` (mình chạy: `p := &a[0]; a = append(a, 4); *p = 100` rồi `a[0]` vẫn là `1`: hai mảng khác nhau, không crash). Chèn giữa trong Go là `append(t[:2], append([]int{99}, t[2:]...)...)` (ra `[1 2 99 3 4 5]`), xóa là `append(t[:1], t[2:]...)`: cùng O(n).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết `Vector<T>` trên bảng trắng và nói vì sao không dùng `new T[]`."
    Ba biến: con trỏ tới khối bytes thô, `n_`, `cap_`. Xin khối bằng `::operator new(cap * sizeof(T))`, dựng từng phần tử bằng placement new khi `push_back`, hủy từng phần tử bằng `~T()` rồi trả khối bằng `::operator delete`. `new T[cap]` dựng ngay `cap` đối tượng bằng hàm tạo mặc định: kiểu không có `T()` thì không dùng được, kiểu có thì tốn công dựng và hủy "đối tượng ma" chưa ai đưa vào (mình đếm: bốn lần tạo cho một phần tử).
    **Nối tiếp:** "Quên gọi hàm hủy của phần tử thì sao?" Rò rỉ tài nguyên mà phần tử giữ (mình chạy với `std::string`: LeakSanitizer báo ba khối rò); kiểu không giữ tài nguyên thì sanitizer im lặng, nên đếm tạo/hủy mới là cách kiểm: tạo + sao chép + di chuyển phải bằng hủy.

??? question "Vì sao capacity gấp đôi mà không cộng một hằng số? `push_back` có thật sự O(1) không?"
    Cộng hằng k thì cứ k lần `push_back` lại có một lần đổi nhà O(n): tổng cho N lần là bậc hai (mình mô phỏng: cộng 10 ra gần 5000 lần chuyển mỗi phần tử ở N=100000). Nhân một hệ số thì đổi nhà thưa theo cấp số nhân và tổng các lần chuyển chỉ cỡ vài lần N: **amortized O(1)** (chia đều cả chuỗi), dù một lần đơn lẻ vẫn O(n).
    **Nối tiếp:** "Sao có thư viện dùng 1,5?" Hệ số nhỏ hơn thì chuyển nhiều hơn (mình đếm 2,14 so với 1,02 ở N=1000) nhưng thừa ít bộ nhớ hơn. Chuẩn không quy định hệ số, chỉ đòi amortized O(1).

??? question "Vì sao hàm di chuyển phải `noexcept`? Chứng minh bằng vector tự cài."
    Lúc đổi nhà ta chuyển từng phần tử sang khối mới; nếu move ném giữa chừng thì khối cũ đã bị lấy ruột một phần, không phục hồi được; copy thì khối cũ còn nguyên. Nên dùng `std::move_if_noexcept`: move chỉ khi `noexcept`, không thì copy. Mình đếm: 1000 `push_back` vào `Vector<Vat>` có `noexcept` thì `sao=0`, bỏ đúng chữ `noexcept` thì `sao=1023`.
    **Nối tiếp:** "Nếu kiểu chỉ có move, không có copy, mà move lại ném?" Khi đó `move_if_noexcept` vẫn chọn move (không sao chép được), và nếu nó ném giữa chừng thì phần tử cũ đã bị lấy ruột, không còn strong guarantee (chuẩn nói hiệu ứng khi đó không xác định). Strong guarantee chỉ giữ được khi phép copy hoặc move dùng lúc đổi nhà không ném.

??? question "Chuyện gì xảy ra với `v.push_back(v[0])` khi vector đầy? Còn `v.insert(v.begin(), v[2])`?"
    `push_back` nhận tham chiếu tới `v[0]` nằm trong khối cũ. Trả khối cũ trước rồi mới đọc tham chiếu là đọc vùng đã trả: UB, ASan báo `heap-use-after-free`. Cách đúng: dựng phần tử mới ở khối mới **trước**, khi khối cũ còn sống. `insert` có thêm bẫy: vòng dồn đè lên chính phần tử đang đưa vào, nên phải dựng bản sao tạm trước khi dồn (bỏ `tam`, mình chạy ra `99` thay vì `3`).
    **Nối tiếp:** "`std::vector` thật có xử lý trường hợp đó không?" Có: `v.push_back(v[0])` chạy đúng trên các thư viện phổ biến; bản g++ dựng phần tử mới ở khối mới trước khi chuyển các phần tử cũ, cùng ý với bản của ta.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gọi `~T()` cho cả ô dư, hoặc quên gọi cho ô sống"
    Chỉ ô `[0, n_)` có đối tượng sống. Hủy ô `[n_, cap_)` là hủy thứ chưa từng được dựng (UB); quên hủy `[0, n_)` là rò rỉ. Trên bảng, hãy nói to bất biến "`n_` ô đầu sống, phần còn lại là bytes thô" mỗi khi viết một vòng lặp.

!!! warning "Lỗi 2: Đổi nhà rồi mới đọc tham số, hoặc dùng iterator đã có"
    Tham số `const T&` có thể trỏ vào chính vector; iterator `pos` của `insert` chết sau đổi nhà. Nói to: "dựng cái mới trước, giữ chỉ số thay vì địa chỉ". Cùng gốc với lỗi iterator ở [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md).

!!! warning "Lỗi 3: Quên `noexcept` ở hàm di chuyển, hoặc gán kiểu 'xóa của mình trước rồi mới chép'"
    Thiếu `noexcept` ở `Vector(Vector&&)` thì `Vector<Vector<int>>` copy sâu từng vector con khi đổi nhà (cùng quy tắc `move_if_noexcept`). Phép gán nên là copy-and-swap để `a = a` và lỗi giữa chừng đều an toàn; xóa dữ liệu của mình trước rồi mới chép thì tự gán là mất dữ liệu.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="79" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Vì sao `Vector<T>` tự cài **không** dùng `d_ = new T[cap]` để xin khối?

- Vì `new T[cap]` phải cấp phát hai lần nên luôn chậm hơn `::operator new`
- Vì nó dựng sẵn `cap` đối tượng bằng `T()`, điều vector không nên làm
- Vì `new T[cap]` không trả về địa chỉ mà chỉ trả về một con số
- Vì `delete[]` không thể trả được khối mà `new T[cap]` đã xin

<p class="giai-thich" markdown>`new T[cap]` chạy hàm tạo mặc định cho cả `cap` ô: kiểu không có `T()` thì không dùng được, còn kiểu có thì tạo (và hủy) các "đối tượng ma" chưa ai đưa vào (bản sai 1 đếm bốn lần tạo cho một phần tử). Việc nó cấp phát mấy lần không phải lý do chính. Nó trả địa chỉ bình thường. Còn `delete[]` đúng là cặp của `new[]`, vấn đề không nằm ở việc trả.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau (`Vat` có hàm tạo sao chép và hàm di chuyển **không** `noexcept`; `Vector` là bản trong bài; bộ đếm `sao` và `chuyen` đã đặt về 0 trước đoạn này). Sau đoạn này, `sao` và `chuyen` bằng bao nhiêu?

```text
Vector<Vat> v;
for (int i = 0; i < 4; ++i) v.push_back(Vat(i));
```

- `sao = 0`, `chuyen = 7`, vì mỗi lần đổi nhà đều move
- `sao = 7`, `chuyen = 0`, vì không `noexcept` thì chỉ copy
- `sao = 4`, `chuyen = 3`, vì mỗi lần push là một copy
- `sao = 3`, `chuyen = 4`, vì copy ở đổi nhà, move ở push

<p class="giai-thich" markdown>Capacity đi 0, 1, 2, 4. Đổi nhà xảy ra ở lần push thứ 1 (chưa có phần tử cũ), thứ 2 (chuyển 1) và thứ 3 (chuyển 2); lần thứ 4 vừa chỗ. Vậy 0 + 1 + 2 = 3 phần tử cũ được copy vì move không `noexcept`. Bốn phần tử mới đi từ đối tượng tạm nên move: 4. Mình đã chạy ra `3 4`. Đáp án "toàn move" quên điều kiện `noexcept`; "toàn copy" quên rằng phần tử mới đi từ tạm bằng move; và "mỗi lần push là một copy" nhầm chỗ copy: nó xảy ra ở phần tử **cũ** lúc đổi nhà.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** `v` đang đầy (size = capacity). Một bản `push_back(const T& x)` xin khối mới, chuyển các phần tử cũ sang, trả khối cũ, **rồi mới** dựng `x` ở khối mới. Gọi `v.push_back(v[0])` thì sao?

- UB: `x` có thể bị đọc từ khối cũ đã trả
- Luôn đúng, vì `x` là bản sao nên không phụ thuộc vào `v`
- Lỗi biên dịch, vì không được đưa phần tử của chính vector vào
- Luôn đúng, vì lúc đó `x` đã được chuyển sang khối mới

<p class="giai-thich" markdown>`x` là **tham chiếu** tới `v[0]` ở khối cũ, không phải bản sao: sau khi khối cũ bị trả, đọc nó là UB (mình chạy với ASan ra `heap-use-after-free`). Việc phần tử đã được chuyển sang khối mới không giúp: tham chiếu `x` vẫn gắn với ô cũ. Trình biên dịch không biết `x` nằm trong `v` nên không có lỗi biên dịch. Sửa bằng cách dựng phần tử mới ở khối mới trước, khi khối cũ còn sống.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau (`Vector<int>` bản trong bài). Nó in ra gì?

```text
Vector<int> v;
v.push_back(10); v.push_back(20); v.push_back(30); v.push_back(40);
auto it = v.erase(v.begin() + 1);
std::cout << *it << " " << v.size();
```

- `20 3`, vì `it` vẫn trỏ phần tử vừa bị xóa
- `30 4`, vì `erase` chỉ đánh dấu phần tử là đã xóa
- `30 3`, vì `erase` trả iterator tới phần tử kế tiếp
- `40 3`, vì `erase` trả iterator tới phần tử cuối

<p class="giai-thich" markdown>Xóa ô 1 (giá trị 20) thì `30` và `40` dồn lên, size còn 3, và `erase` trả `d_ + 1`: ô đó giờ chứa `30`. `20` không còn trong vector, và `erase` không trả iterator tới thứ đã xóa. Nó cũng không "đánh dấu" mà thật sự dồn và hủy ô cuối nên size giảm. Iterator trả về trỏ phần tử ngay sau chỗ xóa, không phải phần tử cuối.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đoạn sau xóa mọi số chẵn khỏi `v = {2, 4, 5}`. Lỗi nằm ở đâu?

```text
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it % 2 == 0) v.erase(it);
}
```

- Không có lỗi: `erase` tự nhích `it` sang phần tử kế
- `v.end()` lấy ở đầu vòng nên `it` luôn bằng nó ở cuối
- `erase` làm vector đổi nhà nên mọi `it` còn lại đều chết
- Vẫn `++it` sau `erase(it)`: bỏ sót phần tử, dùng `it` hỏng

<p class="giai-thich" markdown>Xóa `2` thì `4` dồn vào ô cũ; `++it` nhảy qua nó nên `4` sống sót (còn `{4, 5}`), và theo chuẩn dùng `it` sau `erase(it)` đã là UB. Phải viết `it = v.erase(it)` và chỉ `++it` khi không xóa. `erase` không tự nhích `it`. `v.end()` được gọi lại mỗi vòng, không lấy một lần. Và `erase` **không** đổi nhà (chỉ dồn và hủy ô cuối), nên không phải mọi iterator chết vì đổi nhà.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Một cài đặt `push_back` tăng capacity bằng cách **cộng thêm 10 ô** mỗi lần đầy (thay vì nhân). Với N lần `push_back` vào vector rỗng, nhận xét nào đúng?

- Số lần chuyển tăng bậc hai theo N, không còn amortized O(1)
- Vẫn amortized O(1), vì mỗi lần đổi nhà chỉ chuyển một ít phần tử
- Vẫn amortized O(1), chỉ là hằng số lớn hơn so với gấp đôi
- Không đổi nhà lần nào, vì mỗi lần xin thêm đủ chỗ cho mọi lần sau

<p class="giai-thich" markdown>Cứ 10 lần push lại đổi nhà một lần và lần thứ k chuyển cỡ 10k phần tử; cộng lại cỡ N bình phương chia 20 (mình mô phỏng: gần 5000 lần chuyển mỗi phần tử ở N=100000, so với dưới 2 khi gấp đôi). Mỗi lần "ít" nhưng số lần tăng theo N nên tổng không còn tuyến tính. Chỉ hệ số nhân mới giữ O(1) phân bổ; vấn đề là bậc tăng trưởng, không phải hằng số. Và 10 ô không đủ cho mọi lần sau: sẽ đầy lại.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `Vector<T>` gồm `d_` (khối bytes thô), `n_` (số phần tử sống) và `cap_`; xin ô bằng `::operator new`, dựng từng phần tử bằng placement new `::new (p) T(...)`, hủy bằng `p->~T()` rồi trả ô bằng `::operator delete`; không dùng `new T[]` vì nó đòi `T()` mặc định và dựng thừa đối tượng.
2. `push_back` khi đầy: xin khối `2 * cap_`, dựng phần tử mới **trước**, rồi chuyển phần tử cũ bằng `std::move_if_noexcept`, hủy và trả khối cũ; thứ tự đó chặn lỗi `push_back(v[0])` (đọc từ khối đã trả, ASan: `heap-use-after-free`) và giữ strong guarantee khi `T` ném lúc sao chép.
3. Move có `noexcept` thì đổi nhà **move**, thiếu thì **copy** (mình đếm: 1000 lần `push_back` sao chép 0 so với 1023); Rule of 5 gồm hàm hủy, sao chép sâu, move lấy con trỏ rồi đặt nguồn về rỗng (`noexcept`), gán bằng copy-and-swap.
4. `emplace_back` dùng gói tham số `A&&... a` và `std::forward<A>(a)...` để dựng ngay trong ô cuối; `insert`/`erase` giữa là O(n), đổi `pos` thành chỉ số trước khi có thể đổi nhà và dựng bản sao tạm trước khi dồn; iterator `T*` là địa chỉ một ô nên hỏng khi đổi nhà, và đổi nội dung khi chèn/xóa.
5. Nhân hệ số (gấp đôi: dưới 2 lần chuyển mỗi phần tử) cho amortized O(1), cộng hằng cho bậc hai; bản tự cài lược bớt allocator, `shrink_to_fit`, `resize`, insert/erase theo khoảng, tối ưu `memcpy`, iterator là lớp riêng; ngoài phỏng vấn thì dùng `std::vector` và `reserve`.
