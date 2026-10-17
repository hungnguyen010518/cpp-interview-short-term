# Bài 77 — Live-coding: tự cài unique_ptr

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được trên bảng trắng `UniquePtr<T>` đúng ngay lần đầu: hàm tạo, hàm hủy, **xóa** sao chép, hàm tạo và phép gán di chuyển (nguồn về `nullptr`), `release`/`reset`/`get`/`operator*`/`operator->`/`explicit operator bool`, và kiểm bằng một đối tượng đếm hàm tạo/hủy (kết quả sạch với ASan và UBSan; `sizeof` bằng `std::unique_ptr` thật: 8 byte).
    - Thêm bộ xóa tùy chọn `UniquePtr<T, D>` (kế thừa `D` để bộ xóa rỗng không tốn byte: 16 byte xuống 8), `MakeUnique` nhận bao nhiêu đối số cũng được (`std::forward`), và bản `UniquePtr<T[]>` gọi `delete[]`.
    - Nhận ra và nói được hậu quả của các bản sai điển hình, đều đã chạy thật: quên cấm sao chép, quên đặt nguồn về `nullptr` (ASan: `attempting double-free`), phép gán di chuyển quên xóa cũ (LeakSanitizer báo rò rỉ) hoặc tự gán làm mất đối tượng im lặng, ném ngoại lệ giữa hai `new` thô, `delete` thay `delete[]`, gọi bộ xóa với `nullptr`.
    - Trả lời các câu nối tiếp của người phỏng vấn (vì sao `explicit`, vì sao `noexcept`, vì sao cùng cỡ con trỏ thô) và biết khi nào **không** tự cài mà dùng bản của thư viện chuẩn.

**Bạn cần biết trước:** [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`/`delete[]`, ASan, LeakSanitizer), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, ngoại lệ), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `operator*`/`->`, `UniquePtrMini`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (sao chép, move, `noexcept`, tự gán, `static_assert` ở [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (`explicit`, `= delete`), [Bài 32](../nhom-4-oop-patterns/32-ke-thua.md) (kế thừa, danh sách khởi tạo) và [Bài 34](../nhom-4-oop-patterns/34-template.md) (template lớp, chuyên biệt hóa).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đặt lên bàn một chiếc máy đã lắp sẵn: `std::unique_ptr`. "Máy này bạn dùng hằng ngày. Giờ tôi muốn xem bạn **tháo nó ra** và lắp lại bằng tay trên bảng trắng: từng bánh răng một, và nói vì sao bánh răng đó nằm ở đó." Anh ấy không cần bản giống hệt thư viện; anh cần thấy bạn biết **mỗi hàm tồn tại để chặn lỗi nào**.

Trong **xưởng tự lắp đồ** của nhóm này, đối tượng ở heap là món đồ, `UniquePtr` là cái hộp giữ món đồ đó, và mỗi hàm thành viên là một bánh răng. Bánh răng "cấm sao chép" ngăn hai hộp cùng nhận một món. Bánh răng "chuyển" trao món sang hộp khác rồi **để hộp cũ trống**. Bánh răng "hàm hủy" dọn món khi hộp bị vứt.

!!! info "Chỗ nào ví von xưởng tự lắp đồ không còn đúng?"
    Tự tháo ra thì thấy bánh răng, nhưng bản tự lắp của bạn thiếu nhiều bánh răng mà hãng thêm cho các tình huống ít gặp (chuyển `Con*` thành `Cha*`, so sánh hai hộp, băm hộp, bộ xóa là con trỏ hàm, `make_unique<T[]>`). Vì vậy tự cài là để **hiểu và để phỏng vấn**; code thật vẫn dùng `std::unique_ptr`.

## 📖 Giải thích

### Bốn mảnh cú pháp cần có trước khi viết

Hai mảnh đầu là hàm mới của thư viện chuẩn (cần `#include <utility>`); hai mảnh sau là cách hỏi và cách chuyển kiểu của trình biên dịch.

| Mảnh | Nghĩa | Ví dụ |
|---|---|---|
| `std::exchange(a, v)` | Đặt `a = v` và **trả giá trị cũ** của `a`, trong một biểu thức | `int a = 5; int cu = std::exchange(a, 9);` ra `cu == 5`, `a == 9` |
| `std::swap(a, b)` | Hoán đổi giá trị hai biến cùng kiểu (bản đổi chỗ của [Bài 04](../nhom-1-nen-tang-bo-nho/04-con-tro-ham.md), có sẵn) | `std::swap(x, y);` |
| `explicit operator bool() const` | Hàm chuyển đối tượng thành `bool`. `explicit` (như hàm tạo ở [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) nghĩa là **chỉ chạy khi bạn đòi rõ hoặc ở chỗ cần điều kiện**: `if (p)`, `!p`, `while (p)`, `static_cast<bool>(p)` được; `bool ok = p;` và `p + 1` thì không | |
| `std::is_copy_constructible<T>::value` (`<type_traits>`) | Hỏi trình biên dịch lúc biên dịch "`T` sao chép được không?", trả `true`/`false`; hợp với `static_assert` ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)) để **chứng minh** một tính chất. Cùng họ: `std::is_nothrow_move_constructible<T>::value` hỏi "hàm tạo di chuyển của `T` có hứa `noexcept` không?" | `static_assert(!std::is_copy_constructible<X>::value, "...");` |

Ba thứ khác đã học nên chỉ nhắc: `noexcept` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md): lời hứa không ném), `= delete` ([Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)), `template <typename T>` ([Bài 34](../nhom-4-oop-patterns/34-template.md)).

### Đề 1: `UniquePtr<T>` một chủ

!!! example "Đề bài 1"
    **Ràng buộc.** Viết lớp template `UniquePtr<T>` sở hữu **duy nhất** một `T` ở heap. Hàm tạo nhận `T*`; hàm hủy xóa đối tượng đúng một lần. **Không** sao chép được. Chuyển được bằng `std::move` (hàm tạo và phép gán di chuyển), và nguồn sau đó rỗng. Có `get`, `release`, `reset`, `operator*`, `operator->`, `explicit operator bool`, `swap`. Chỉ dùng C++17 chuẩn, không dùng `<memory>`.

    **Đầu vào/đầu ra (bài test).** Dùng `Dem` (struct đếm số lần hàm tạo và hàm hủy chạy). Mong đợi: sau `b = std::move(a)` thì `a` rỗng và hàm hủy `Dem` chạy đúng một lần cho mỗi đối tượng; hết khối thì `tao == huy`; `sizeof(UniquePtr<Dem>)` bằng `sizeof(Dem*)`; `UniquePtr` nằm được trong `std::vector`.

??? tip "Gợi ý 1"
    Bắt đầu từ chuyện sai: hộp nào cũng có hàm hủy `delete p_`. Nếu hai hộp cùng giữ một món thì sao? Vậy phải **cấm** gì, và cho phép gì thay thế?

??? tip "Gợi ý 2"
    Gom "lấy con trỏ ra và để mình rỗng" thành **một** hàm: `release()`. Hàm tạo di chuyển và phép gán di chuyển chỉ là `release()` của nguồn cộng với việc nhận con trỏ đó. Còn "nhận con trỏ mới và xóa con trỏ cũ" là `reset()`.

??? tip "Gợi ý 3"
    Khung: `UniquePtr(UniquePtr&& o) noexcept : p_(o.release()) {}` và `operator=(UniquePtr&& o) noexcept { reset(o.release()); return *this; }`, với `release() { return std::exchange(p_, nullptr); }`. Phần còn lại là bảy hàm một dòng.

Hướng giải gói trong bảng "hàm nào chặn lỗi nào" (cũng là thứ nên **nói to** trên bảng trắng):

| Hàm | Chặn lỗi gì | Chi tiết nên nói |
|---|---|---|
| `~UniquePtr` | Rò rỉ | `delete p_`; `delete nullptr` an toàn nên không cần `if` |
| `= delete` sao chép | Hai chủ, double free | Tự khai báo hai hàm di chuyển thì sao chép đã bị xóa ngầm (mình chạy), nhưng vẫn ghi `= delete` để người đọc thấy ý định |
| Hàm tạo di chuyển | Nguồn còn giữ sau khi trao | Lấy bằng `release()` để nguồn về `nullptr` trong **cùng** bước |
| Phép gán di chuyển | Rò rỉ giá trị cũ, tự gán | `reset(o.release())`: xóa cũ, nhận mới; tự gán thành không làm gì |
| `noexcept` | `vector` không dám dùng move | Cả ba hàm chuyển chỉ chép con trỏ nên hứa được |
| `get`, `operator*`, `operator->` là `const` | Không dùng được qua `const UniquePtr&` | `const UniquePtr` giống `T* const`: **hộp** hằng, `T` bên trong thì không |
| `explicit operator bool` | `int n = p + 1;` biên dịch êm | Bỏ `explicit` thì mình chạy ra `n = 2` mà không báo gì |

### Đề 2: bộ xóa tùy chọn, `MakeUnique` và mảng

!!! example "Đề bài 2"
    **Ràng buộc.** Mở rộng đề 1: (a) `UniquePtr<T, D>` với bộ xóa `D` (mặc định xóa bằng `delete`), dùng được cho tài nguyên không phải `delete` như `FILE*`; bộ xóa không có dữ liệu **không được tốn thêm byte**. (b) `MakeUnique<T>(args...)` dựng `T` từ bao nhiêu đối số cũng được, kể cả đối số chỉ di chuyển được. (c) `UniquePtr<T[]>` giữ mảng, xóa bằng `delete[]`, truy cập bằng `operator[]`. Hàm hủy **không** được gọi bộ xóa với `nullptr`.

    **Đầu vào/đầu ra (bài test).** Mảng 3 `Dem`: `tao=3 huy=0`, hết khối `huy=3`. `UniquePtr<std::FILE, DongTep>`: in `dong tep` đúng một lần. Bộ xóa đếm lần gọi: sau khi move chỉ **1** lần. `MakeUnique<Chu>(MakeUnique<Dem>(5))` chạy được. In `sizeof` của bản mình và của `std::unique_ptr` với cùng bộ xóa.

??? tip "Gợi ý 1"
    Bộ xóa là **một kiểu** (tham số template thứ hai) có `operator()(T*)`: `delete` là một bộ xóa, `fclose` bọc trong một `struct` là bộ xóa khác. Hàm hủy gọi `get_deleter()(p_)` thay vì `delete p_`.

??? tip "Gợi ý 2"
    Lưu `D` làm **thành viên** thì mỗi `UniquePtr` thêm ít nhất 1 byte (rồi đệm lên 8). Có cách nào để một lớp rỗng không chiếm chỗ? Nhớ lại Bài 32: lớp con chứa phần lớp cha.

??? tip "Gợi ý 3"
    `MakeUnique`: `template <typename T, typename... Args> UniquePtr<T> MakeUnique(Args&&... args)` rồi `new T(std::forward<Args>(args)...)`. Mảng: chuyên biệt hóa từng phần `UniquePtr<T[], D>` và `DefaultDelete<T[]>` gọi `delete[]`.

Ba chỗ cần dạy tại chỗ:

- **Gói đối số (variadic template).** `typename... Args` nghĩa là "bao nhiêu kiểu cũng được"; `Args&&... args` là **gói** các đối số tương ứng; `f(args...)` mở gói thành `f(a1, a2, ...)`. `std::forward<Args>(args)...` mở gói **và** giữ nguyên từng đối số là lvalue hay rvalue (tên `args` luôn là lvalue, như `o` ở [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md); `forward` trả nó về đúng loại ban đầu).
- **Kế thừa `private`.** `class UniquePtr : private D` ([Bài 32](../nhom-4-oop-patterns/32-ke-thua.md)): `UniquePtr` chứa một `D` làm phần cha mà người ngoài không thấy. Lớp rỗng làm **thành viên** phải có địa chỉ riêng nên chiếm ít nhất 1 byte; làm **lớp cha** thì được phép chiếm 0 byte (tối ưu lớp cha rỗng, EBO). Mình đo ở mục 💻.
- **Chuyên biệt hóa từng phần** ([Bài 34](../nhom-4-oop-patterns/34-template.md)): `template <typename T, typename D> class UniquePtr<T[], D>` là bản riêng dùng khi `T` có dạng `X[]`.

## 💻 Ví dụ code

### Lời giải đề 1, dựng từng bước

**Bước 1: sở hữu và dọn.** Bản đầu giống `UniquePtrMini` của [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md), nhưng dùng được cho mọi kiểu nhờ `template`.

```cpp
// bo-qua-kiem-tra
template <typename T>
class UniquePtr {
public:
    explicit UniquePtr(T* p) noexcept : p_(p) {}   // explicit: không gán ngầm UniquePtr<T> x = new T;
    ~UniquePtr() { delete p_; }
private:
    T* p_;
};
```

Bản này **chưa an toàn**: trình biên dịch tự sinh hàm tạo sao chép chép con trỏ (hai chủ). Mục "bản SAI 1" chạy nó.

**Bước 2: cấm sao chép.** Hai dòng `= delete` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)): `UniquePtr(const UniquePtr&) = delete;` và `UniquePtr& operator=(const UniquePtr&) = delete;`.

**Bước 3: chuyển.** `release()` là bánh răng trung tâm; hàm tạo di chuyển chỉ gọi nó.

```cpp
// bo-qua-kiem-tra
T* release() noexcept { return std::exchange(p_, nullptr); }  // trả con trỏ cũ, tự rỗng
UniquePtr(UniquePtr&& o) noexcept : p_(o.release()) {}
```

**Bước 4: gán chuyển và `reset`.** `reset` nhận con trỏ mới trước rồi mới xóa con trỏ cũ; phép gán chuyển dựa vào nó.

```cpp
// bo-qua-kiem-tra
void reset(T* p = nullptr) noexcept {   // "= nullptr": gọi reset() không đối số thì p là nullptr
    T* cu = std::exchange(p_, p);
    delete cu;
}
UniquePtr& operator=(UniquePtr&& o) noexcept { reset(o.release()); return *this; }
```

Tự gán `a = std::move(a)` an toàn mà không cần `if (this != &o)`: `o.release()` đặt `p_` về `nullptr` và trả con trỏ, rồi `reset` nhận lại đúng con trỏ đó; `cu` là `nullptr` nên không xóa gì.

**Bước 5: truy cập, `bool`, `swap`.** `get`, `operator*`, `operator->` cho dùng như con trỏ; `explicit operator bool` cho `if (p)`; `swap` gọi `std::swap(p_, o.p_)`. Ghép lại và thêm bài test:

```cpp
#include <iostream>
#include <memory>
#include <type_traits>
#include <utility>
#include <vector>

int soTao = 0, soHuy = 0;            // đếm hàm tạo và hàm hủy của Dem

struct Dem {
    int id;
    explicit Dem(int i = 0) : id(i) { ++soTao; }
    ~Dem() { ++soHuy; }
};

void in(const char* nhan) {
    std::cout << nhan << ": tao=" << soTao << " huy=" << soHuy << "\n";
}

template <typename T>
class UniquePtr {
public:
    UniquePtr() noexcept : p_(nullptr) {}                          // (1)
    explicit UniquePtr(T* p) noexcept : p_(p) {}                   // (2)
    ~UniquePtr() { delete p_; }                                    // (3)

    UniquePtr(const UniquePtr&) = delete;                          // (4)
    UniquePtr& operator=(const UniquePtr&) = delete;               // (5)

    UniquePtr(UniquePtr&& o) noexcept : p_(o.release()) {}         // (6)
    UniquePtr& operator=(UniquePtr&& o) noexcept {                 // (7)
        reset(o.release());
        return *this;
    }

    T* release() noexcept { return std::exchange(p_, nullptr); }   // (8)
    void reset(T* p = nullptr) noexcept {                          // (9)
        T* cu = std::exchange(p_, p);
        delete cu;
    }
    T* get() const noexcept { return p_; }                         // (10)
    T& operator*() const { return *p_; }                           // (11)
    T* operator->() const noexcept { return p_; }                  // (12)
    explicit operator bool() const noexcept { return p_ != nullptr; }   // (13)
    void swap(UniquePtr& o) noexcept { std::swap(p_, o.p_); }      // (14)

private:
    T* p_;
};

static_assert(!std::is_copy_constructible<UniquePtr<Dem>>::value, "UniquePtr khong duoc copy");
static_assert(std::is_nothrow_move_constructible<UniquePtr<Dem>>::value, "move phai noexcept");

int main() {
    {
        UniquePtr<Dem> a(new Dem(1));
        in("tao a");
        UniquePtr<Dem> b = std::move(a);                           // (A)
        std::cout << "a rong: " << (!a) << ", b->id = " << b->id << "\n";
        in("sau move ctor");

        UniquePtr<Dem> c(new Dem(2));
        c = std::move(b);                                          // (B)
        std::cout << "c->id = " << c->id << ", b rong: " << (!b) << "\n";
        in("sau move assign");

        UniquePtr<Dem>& ten = c;
        c = std::move(ten);                                        // (C) tự gán
        std::cout << "tu gan: c con giu id " << (*c).id << "\n";
        in("sau tu gan");

        Dem* tho = c.release();                                    // (D)
        std::cout << "release: c rong " << (!c) << ", tho->id = " << tho->id << "\n";
        in("sau release");
        c.reset(tho);                                              // (E)
        c.reset(new Dem(3));                                       // (F)
        in("sau reset(moi)");
        c.reset();                                                 // (G)
        in("sau reset()");

        UniquePtr<Dem> d(new Dem(4)), e(new Dem(5));
        d.swap(e);
        std::cout << "swap: d->id = " << d->id << ", e->id = " << e->id << "\n";
        if (d) std::cout << "d dang giu\n";
        if (!UniquePtr<Dem>()) std::cout << "mac dinh thi rong\n";
    }                                                              // (H)
    in("het khoi");

    std::vector<UniquePtr<Dem>> v;
    for (int i = 10; i < 13; ++i) v.push_back(UniquePtr<Dem>(new Dem(i)));
    in("vector 3 phan tu");
    v.clear();
    in("sau clear");

    std::cout << "sizeof: Dem* = " << sizeof(Dem*) << ", UniquePtr = " << sizeof(UniquePtr<Dem>)
              << ", std::unique_ptr = " << sizeof(std::unique_ptr<Dem>) << "\n";
    return 0;
}
```

**Chạy từng dòng** (cột cuối là `soTao`/`soHuy` sau dòng đó)

| Dòng | Chuyện gì xảy ra | tao/huy |
|---|---|---|
| (A) | Hàm tạo di chuyển (6): `b` nhận con trỏ của `a`, `a` thành `nullptr`; không `Dem` nào được tạo hay hủy | 1/0 |
| `new Dem(2)` | Tạo `Dem` thứ hai, `c` giữ nó | 2/0 |
| (B) | Phép gán (7): `o.release()` lấy `Dem` 1 từ `b`; `reset` đặt vào `c` và **xóa `Dem` 2 cũ** | 2/1 |
| (C) | Tự gán: không làm gì và `Dem` 1 vẫn còn | 2/1 |
| (D) | `release()` trả địa chỉ thô, `c` rỗng, **không xóa**; từ giờ `tho` là việc của mình | 2/1 |
| (E) | `reset(tho)` giao lại cho `c` (cũ là `nullptr`, không xóa gì) | 2/1 |
| (F) | `new Dem(3)` tạo ra rồi `reset` thay vào: `Dem` 1 bị xóa | 3/2 |
| (G) | `reset()` không đối số: `p` mặc định `nullptr`; `Dem` 3 bị xóa | 3/3 |
| `swap`, `if (d)` | Đổi hai con trỏ; `d` giờ giữ `Dem` 5. `if (d)` dùng `explicit operator bool` | 5/3 |
| (H) `}` | `e`, `d` chết (xóa `Dem` 4 và 5); `c`, `b`, `a` rỗng nên không xóa gì | 5/5 |
| `vector` | `push_back` có thể cấp phát lại và **chuyển** phần tử cũ sang vùng mới: không `Dem` nào bị hủy giữa chừng | 8/5 |
| `v.clear()` | Hủy ba `UniquePtr`, mỗi cái xóa một `Dem` | 8/8 |

**Kết quả khi chạy:**

```text
tao a: tao=1 huy=0
a rong: 1, b->id = 1
sau move ctor: tao=1 huy=0
c->id = 1, b rong: 1
sau move assign: tao=2 huy=1
tu gan: c con giu id 1
sau tu gan: tao=2 huy=1
release: c rong 1, tho->id = 1
sau release: tao=2 huy=1
sau reset(moi): tao=3 huy=2
sau reset(): tao=3 huy=3
swap: d->id = 5, e->id = 4
d dang giu
mac dinh thi rong
het khoi: tao=5 huy=5
vector 3 phan tu: tao=8 huy=5
sau clear: tao=8 huy=8
sizeof: Dem* = 8, UniquePtr = 8, std::unique_ptr = 8
```

Mình biên dịch bằng `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`: **không cảnh báo**, chạy thoát mã 0, ASan và UBSan không báo gì; chạy lại ở `-O2` (không sanitizer) cho đúng đầu ra này. `tao == huy` ở cuối mỗi phần là bằng chứng không rò rỉ và không xóa đôi. `sizeof` bằng nhau là con số của g++ 11 trên máy này; chuẩn không hứa, nhưng hộp chỉ chứa một con trỏ nên đó là điều mong đợi.

**Thử thay đổi 1: bỏ `explicit` ở `operator bool`** và thêm `UniquePtr<Dem> q(new Dem(1)); int n = q + 1;`. Mình chạy: biên dịch **êm**, in `n = 2` (`q` đổi ngầm thành `true` rồi thành số 1). Giữ `explicit` thì `bool ok = q;` và `q + 1` đều là lỗi (`cannot convert ‘UniquePtr<Dem>’ to ‘bool’ in initialization`, `no match for ‘operator+’`); `std::unique_ptr` cũng vậy.

**Thử thay đổi 2: bỏ `noexcept` ở hàm tạo di chuyển (6).** `static_assert` thứ hai dừng biên dịch với `static assertion failed: move phai noexcept`. Đó là cách bắt quên `noexcept` mà không cần chạy.

**Thử thay đổi 3: xóa hai dòng `= delete` (4), (5)** (hàm di chuyển vẫn còn) rồi viết `UniquePtr<Dem> r = q;`. Mình chạy: vẫn **lỗi** `use of deleted function ... UniquePtr(const UniquePtr&)`, vì lớp tự khai báo hàm di chuyển thì sao chép bị xóa ngầm. Ở Bước 1 (chưa có hàm di chuyển) thì không: lúc đó sao chép là chép con trỏ.

**Thử thay đổi 4: dùng nguồn sau khi chuyển** (`UniquePtr<Dem> r = std::move(q); std::cout << q->id;`). UBSan báo `member access within null pointer of type 'struct Dem'`, rồi ASan `SEGV on unknown address 0x000000000000`. Rỗng sau move là bảo đảm của **chúng ta** (và của `std::unique_ptr`), nhưng dùng nó vẫn là lỗi.

### Các bản SAI của đề 1 (không chạy trong bộ kiểm tra)

Mỗi bản dưới đây là lớp tối thiểu (`explicit UniquePtr(T*)`, `~UniquePtr() { delete p_; }`, `get()` và `private: T* p_;`) cộng hàm sai, dùng `Dem` ở trên và `-fsanitize=address,undefined`.

**SAI 1: quên cấm sao chép.** Lớp ở Bước 1, rồi `UniquePtr<Dem> a(new Dem(1)); UniquePtr<Dem> b = a;`. Biên dịch **sạch** không cảnh báo, in `a va b cung giu 1`.

Rồi ASan báo `ERROR: AddressSanitizer: attempting double-free on 0x502000000010`, ngăn xếp `UniquePtr<Dem>::~UniquePtr() ... in main`, cùng khối "freed by thread T0 here" cũng ở hàm hủy.

Chạy trần (không sanitizer): `free(): double free detected in tcache 2`, mã 134. Chữa: hai dòng `= delete`.

**SAI 2: hàm tạo di chuyển quên đặt nguồn về `nullptr`.**

```cpp
// bo-qua-kiem-tra
UniquePtr(UniquePtr&& o) noexcept : p_(o.p_) {}   // SAI: o vẫn giữ con trỏ
```

Với `UniquePtr<Dem> b = std::move(a);`: chương trình in `sau move: tao=1 huy=0` rồi **cả hai** hàm hủy `delete` cùng một địa chỉ (mình cho hàm hủy in địa chỉ: hai dòng giống hệt), ASan báo `attempting double-free`.

Đây là bẫy "quên đặt null sau move": `std::move` không tự đặt gì, nên việc đặt `nullptr` là của **hàm tạo di chuyển**. Dùng `o.release()` thì không thể quên.

**SAI 3: phép gán di chuyển viết tay.** Hai biến thể:

```cpp
// bo-qua-kiem-tra
p_ = o.p_; o.p_ = nullptr;                      // 3a: quên xóa đối tượng cũ của *this
delete p_; p_ = o.p_; o.p_ = nullptr;           // 3b: không chống tự gán
```

3a với `b = std::move(a);` (`b` đang giữ `Dem` 2): in `tao=2 huy=0` và LeakSanitizer báo `Direct leak of 4 byte(s) in 1 object(s)`, `SUMMARY: AddressSanitizer: 4 byte(s) leaked in 1 allocation(s)`; không crash.

3b với tự gán `a = std::move(ten)`: `delete p_` xóa `Dem`, rồi `p_ = o.p_` (cùng biến) chép con trỏ vừa xóa, rồi `o.p_ = nullptr` đặt **chính nó** về rỗng. Mình chạy: `a.get() = nullptr`, `tao=1 huy=1`, **không có báo cáo nào của ASan hay UBSan**; đối tượng biến mất im lặng.

Đó là lý do [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) bắt phải nghĩ tới tự gán; `reset(o.release())` làm cả hai bản sai đúng mà khỏi kiểm tra.

**SAI 4: ném ngoại lệ giữa hai `new` thô.** Lớp chứa `Dem*` và `Hong*` (`Hong` có hàm tạo luôn ném `std::runtime_error`) dựng cả hai trong danh sách khởi tạo, thân hàm hủy `delete` cả hai:

```cpp
// bo-qua-kiem-tra
struct ThoHolder {
    Dem* a_; Hong* b_;
    ThoHolder() : a_(new Dem(1)), b_(new Hong) {}     // Hong ném: ThoHolder chưa dựng xong
    ~ThoHolder() { delete a_; delete b_; }            // nên hàm hủy KHÔNG bao giờ chạy
};
struct TotHolder {
    UniquePtr<Dem> a_; UniquePtr<Hong> b_;
    TotHolder() : a_(new Dem(1)), b_(new Hong) {}     // a_ đã dựng xong nên được hủy khi ném
};
```

Cả hai bản bị `catch` in `bat: hong`. Bản thô: `tao=1 huy=0` và LeakSanitizer `Direct leak of 4 byte(s)` (ngăn xếp có `ThoHolder::ThoHolder()`). Bản `UniquePtr`: `tao=1 huy=1`, sạch.

Hàm hủy của lớp **chưa dựng xong** không chạy, nhưng hàm hủy của từng thành viên **đã dựng xong** thì có chạy: đó là lý do thành viên nên là `UniquePtr`. (`new Hong` tự trả phần nhớ của nó khi hàm tạo `Hong` ném; ASan không báo gì ở `Hong`.)

### Lời giải đề 2, dựng từng bước

**Bước 1: bộ xóa là một kiểu.**

```cpp
// bo-qua-kiem-tra
template <typename T> struct DefaultDelete { void operator()(T* p) const { delete p; } };
template <typename T> struct DefaultDelete<T[]> { void operator()(T* p) const { delete[] p; } };
```

`operator()` cho phép viết `bo(p)` như gọi hàm (functor, giống `DongTep` ở [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md): bài đó viết `unique_ptr<FILE, DongTep>`, ở đây ta tự cài phần nhận `D`). Bản thứ hai là chuyên biệt hóa cho `T[]`.

**Bước 2: `D` làm lớp cha, hàm hủy gọi bộ xóa, bỏ qua `nullptr`.** Thay `delete cu;` ở `reset` bằng `if (cu) get_deleter()(cu);`, và hàm hủy chỉ gọi `reset()`. Chữ `if (cu)` quan trọng: sau khi chuyển, hộp cũ có `p_ == nullptr` mà hàm hủy của nó vẫn chạy, còn `fclose(nullptr)` thì sập (mục SAI 5).

**Bước 3: `MakeUnique` và mảng.**

```cpp
// bo-qua-kiem-tra
template <typename T, typename... Args>
UniquePtr<T> MakeUnique(Args&&... args) {
    return UniquePtr<T>(new T(std::forward<Args>(args)...));
}
```

Bản mảng là chuyên biệt hóa `UniquePtr<T[], D>` thay `operator*`/`->` bằng `operator[]`. Ghép lại:

```cpp
#include <cstddef>
#include <cstdio>
#include <iostream>
#include <memory>
#include <utility>

int soTao = 0, soHuy = 0;            // đếm hàm tạo và hàm hủy của Dem

struct Dem {
    int id;
    explicit Dem(int i = 0) : id(i) { ++soTao; }
    ~Dem() { ++soHuy; }
};

void in(const char* nhan) {
    std::cout << nhan << ": tao=" << soTao << " huy=" << soHuy << "\n";
}

template <typename T>
struct DefaultDelete {                                       // (1) bộ xóa mặc định
    void operator()(T* p) const { delete p; }
};
template <typename T>
struct DefaultDelete<T[]> {                                  // (2) bản riêng cho mảng
    void operator()(T* p) const { delete[] p; }
};

template <typename T, typename D = DefaultDelete<T>>
class UniquePtr : private D {                                // (3) kế thừa bộ xóa
public:
    UniquePtr() noexcept : p_(nullptr) {}
    explicit UniquePtr(T* p) noexcept : p_(p) {}
    UniquePtr(T* p, D d) noexcept : D(std::move(d)), p_(p) {}
    ~UniquePtr() { reset(); }

    UniquePtr(const UniquePtr&) = delete;
    UniquePtr& operator=(const UniquePtr&) = delete;
    UniquePtr(UniquePtr&& o) noexcept : D(std::move(o.get_deleter())), p_(o.release()) {}
    UniquePtr& operator=(UniquePtr&& o) noexcept {
        reset(o.release());
        get_deleter() = std::move(o.get_deleter());
        return *this;
    }

    T* release() noexcept { return std::exchange(p_, nullptr); }
    void reset(T* p = nullptr) noexcept {
        T* cu = std::exchange(p_, p);
        if (cu) get_deleter()(cu);                           // (4) không bao giờ gọi bộ xóa với nullptr
    }
    T* get() const noexcept { return p_; }
    D& get_deleter() noexcept { return *this; }              // (5)
    T& operator*() const { return *p_; }
    T* operator->() const noexcept { return p_; }
    explicit operator bool() const noexcept { return p_ != nullptr; }

private:
    T* p_;
};

template <typename T, typename D>
class UniquePtr<T[], D> : private D {                        // (6) bản cho mảng, rút gọn
public:
    explicit UniquePtr(T* p) noexcept : p_(p) {}
    ~UniquePtr() { if (p_) D::operator()(p_); }
    UniquePtr(const UniquePtr&) = delete;
    UniquePtr& operator=(const UniquePtr&) = delete;
    T* get() const noexcept { return p_; }
    T& operator[](std::size_t i) const { return p_[i]; }     // (7) thay cho * và ->
private:
    T* p_;
};

template <typename T, typename... Args>
UniquePtr<T> MakeUnique(Args&&... args) {                    // (8)
    return UniquePtr<T>(new T(std::forward<Args>(args)...)); // (9)
}

template <typename T>
UniquePtr<T[]> MakeUniqueMang(std::size_t n) {
    return UniquePtr<T[]>(new T[n]());
}

struct Chu {                                                 // nhận một UniquePtr theo giá trị
    UniquePtr<Dem> d;
    explicit Chu(UniquePtr<Dem> x) : d(std::move(x)) {}
};

struct DongTep {
    void operator()(std::FILE* f) const {
        std::cout << "  dong tep\n";
        std::fclose(f);
    }
};

struct DemXoa {                                              // bộ xóa CÓ trạng thái
    int* dem;
    void operator()(Dem* p) const { ++*dem; delete p; }
};

struct ThanhVien { Dem* p; DefaultDelete<Dem> d; };          // so cỡ: bộ xóa làm thành viên
struct KeThua : DefaultDelete<Dem> { Dem* p; };              // so cỡ: bộ xóa làm lớp cha

int main() {
    {
        UniquePtr<Dem[]> m = MakeUniqueMang<Dem>(3);
        m[1].id = 42;
        std::cout << "m[0].id = " << m[0].id << ", m[1].id = " << m[1].id << "\n";
        in("mang 3 phan tu");
    }
    in("het khoi mang");

    {
        UniquePtr<std::FILE, DongTep> tep(std::tmpfile());
        std::fputs("xin chao", tep.get());
        std::cout << "da ghi " << std::ftell(tep.get()) << " byte\n";
    }

    int lanXoa = 0;
    {
        UniquePtr<Dem, DemXoa> a(new Dem(7), DemXoa{&lanXoa});
        UniquePtr<Dem, DemXoa> b = std::move(a);
        std::cout << "a rong: " << (!a) << ", b->id = " << b->id << "\n";
    }
    std::cout << "bo xoa duoc goi " << lanXoa << " lan\n";
    in("sau bo xoa rieng");

    {
        auto c = MakeUnique<Chu>(MakeUnique<Dem>(5));
        std::cout << "c->d->id = " << c->d->id << "\n";
    }
    in("sau MakeUnique");

    std::cout << "sizeof: thanh vien = " << sizeof(ThanhVien) << ", ke thua = " << sizeof(KeThua)
              << "\n";
    std::cout << "sizeof UniquePtr: mac dinh = " << sizeof(UniquePtr<Dem>)
              << ", DongTep = " << sizeof(UniquePtr<std::FILE, DongTep>)
              << ", DemXoa = " << sizeof(UniquePtr<Dem, DemXoa>) << "\n";
    std::cout << "sizeof std::unique_ptr: mac dinh = " << sizeof(std::unique_ptr<Dem>)
              << ", DongTep = " << sizeof(std::unique_ptr<std::FILE, DongTep>)
              << ", DemXoa = " << sizeof(std::unique_ptr<Dem, DemXoa>) << "\n";
    return 0;
}
```

Bản mảng (6) cố ý rút gọn: không có hàm di chuyển, `release`, `reset` (copy elision bắt buộc của C++17 cho phép `MakeUniqueMang` trả giá trị tạm không cần hàm di chuyển); `std::unique_ptr<T[]>` có đủ. `new T[n]()` có cặp ngoặc để mỗi phần tử được khởi tạo giá trị (số thành 0), như `std::make_unique<T[]>(n)`.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| `MakeUniqueMang<Dem>(3)` | `new Dem[3]()` dựng 3 `Dem` (id 0); `UniquePtr<Dem[]>` giữ; (7) cho `m[1].id = 42` | tao/huy 3/0 |
| hết khối mảng | Hàm hủy (6) gọi bộ xóa mặc định của `Dem[]`, tức (2): `delete[]` hủy cả 3 | 3/3 |
| `UniquePtr<FILE, DongTep>` | `D` = `DongTep`; hàm hủy gọi `DongTep` (in `dong tep`, `fclose`) đúng một lần | `ftell` báo 8 byte |
| `DemXoa{&lanXoa}` rồi `std::move` | Bộ xóa mang con trỏ tới biến đếm nên chuyển cùng hộp; hộp cũ rỗng nên (4) bỏ qua | `lanXoa` = 1 |
| `MakeUnique<Chu>(MakeUnique<Dem>(5))` | (8) nhận một rvalue `UniquePtr<Dem>`; (9) `forward` giữ nó là rvalue nên `Chu` nhận bằng **move** | tao/huy 5/5 sau khối |
| `sizeof` | `ThanhVien` (có thành viên rỗng): 16; `KeThua` (cha rỗng): 8; `DemXoa` có con trỏ nên 16 | |

**Kết quả khi chạy:**

```text
m[0].id = 0, m[1].id = 42
mang 3 phan tu: tao=3 huy=0
het khoi mang: tao=3 huy=3
da ghi 8 byte
  dong tep
a rong: 1, b->id = 7
bo xoa duoc goi 1 lan
sau bo xoa rieng: tao=4 huy=4
c->d->id = 5
sau MakeUnique: tao=5 huy=5
sizeof: thanh vien = 16, ke thua = 8
sizeof UniquePtr: mac dinh = 8, DongTep = 8, DemXoa = 16
sizeof std::unique_ptr: mac dinh = 8, DongTep = 8, DemXoa = 16
```

Mình biên dịch bằng `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`: không cảnh báo, thoát mã 0, ASan/UBSan im lặng; `-O2` cho cùng đầu ra. Bản mình và `std::unique_ptr` **cùng cỡ** ở cả ba bộ xóa; bộ xóa có dữ liệu (`DemXoa`) thì cả hai đều 16, vì dữ liệu phải nằm đâu đó. Số 8/16 là của g++ 11 trên máy 64 bit này.

**Thử thay đổi 1: đổi `UniquePtr<std::FILE, DongTep>` thành bộ xóa là con trỏ hàm** `UniquePtr<std::FILE, int (*)(std::FILE*)> f(std::tmpfile(), &std::fclose);`.

Mình chạy: lỗi biên dịch `base type ‘int (*)(_IO_FILE*)’ fails to be a struct or class type`. Lớp cha phải là lớp, mà con trỏ hàm không phải. Còn `std::unique_ptr<std::FILE, int (*)(std::FILE*)>` thì biên dịch được và (mình đã chạy) có `sizeof` 16: thư viện chuẩn lưu bộ xóa theo cách xử lý được cả kiểu không phải lớp. Đó là một phần lý do bản của thư viện dài hơn bản mình.

**Thử thay đổi 2: bỏ `std::forward`**, viết `new T(args...)`. Lỗi biên dịch: `use of deleted function ‘UniquePtr<T, D>::UniquePtr(const UniquePtr<T, D>&)’`. `args` có tên nên là lvalue, `Chu` đòi `UniquePtr` theo giá trị, mà lvalue thì phải **sao chép**, đã bị xóa. Mỗi đối số chỉ-di-chuyển (`UniquePtr`, `std::thread`, `std::promise`) làm bản không `forward` hỏng.

### Các bản SAI của đề 2 (không chạy trong bộ kiểm tra)

**SAI 5: bỏ `if (cu)`** (`reset` gọi `get_deleter()(cu)` cả khi `cu` là `nullptr`). Với `UniquePtr<std::FILE, DongTep> a(std::tmpfile()); UniquePtr<std::FILE, DongTep> b = std::move(a);` hết khối: `dong tep` **in hai lần** (hộp cũ `a` cũng gọi bộ xóa) rồi ASan `SEGV on unknown address 0x000000000000`, ngăn xếp `_IO_new_fclose` ở `libio/iofclose.c:48`.

Với `delete` thì `nullptr` vô hại, nên bản đề 1 không cần kiểm tra; bộ xóa tùy chỉnh thì cần. `std::unique_ptr` có kiểm tra này.

**SAI 6: dùng bản đơn cho mảng.** `UniquePtr<Dem> m(new Dem[3]);` biên dịch **sạch** nhưng hàm hủy gọi `delete` (không `[]`). ASan báo `attempting free on address which was not malloc()-ed`, `located 8 bytes inside of 20-byte region` (với g++ trên máy này và kiểu có hàm hủy, `new[]` ghi thêm 8 byte đầu để nhớ số phần tử; `delete` đưa địa chỉ phần tử đầu, lệch 8 byte; chuẩn không quy định chi tiết này), `SUMMARY: AddressSanitizer: bad-free`.

Với `int` (không có hàm hủy) thì ASan báo `alloc-dealloc-mismatch` như ở [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md); lỗi giống nhau, thông báo khác nhau. Chữa: kiểu `UniquePtr<Dem[]>`, để `DefaultDelete<Dem[]>` gọi `delete[]`.

### Phân tích chi phí, và khi nào không tự cài

Bộ nhớ: một con trỏ (8 byte) cộng bộ xóa nếu có dữ liệu. Thời gian: mọi hàm là vài lệnh, trình biên dịch nhúng thẳng nên bằng con trỏ thô; không có đếm nguyên tử, không có khối điều khiển (khác `shared_ptr`, [Bài 78](78-tu-cai-shared-ptr.md)). `MakeUnique` chỉ một lần `new`.

**Không** tự cài trong code thật: `std::unique_ptr` còn chuyển `unique_ptr<Con>` thành `unique_ptr<Cha>`, so sánh, băm, bộ xóa là con trỏ hàm, `make_unique<T[]>`, đã được kiểm thử rất nhiều. Tự cài khi: phỏng vấn, học, hoặc cần một biến thể nhỏ (hộp giữ tài nguyên của một API C, như cặp `mở`/`đóng`; khi đó bạn chỉ cần `unique_ptr<T, BoXoa>` có sẵn).

!!! info "Bạn biết Go?"
    Mình đã chạy Go 1.27.2. Go không có `delete`, nên không có "hai chủ cùng xóa" cho bộ nhớ; nhưng với tài nguyên như tệp thì có thể: gán `g := f` cho `*os.File` rồi `f.Close()`, `g.Close()` thì lần hai **trả lỗi** `close ...: file already closed` thay vì hành vi không xác định. `UniquePtr` ghi quyền "ai đóng" vào kiểu dữ liệu; Go ghi nó vào quy ước và vào `defer f.Close()`. Go cũng không có move: gán `g := f` luôn chép con trỏ và cả hai dùng tiếp.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết `unique_ptr` trên bảng trắng và giải thích từng hàm."
    Mình viết theo thứ tự lỗi cần chặn: `T* p_`; hàm tạo `explicit`; hàm hủy `delete p_`; **cấm** sao chép (hai dòng `= delete`) vì sao chép sẽ tạo hai chủ và double free; `release()` bằng `std::exchange(p_, nullptr)`; hàm tạo di chuyển `p_(o.release())`; phép gán di chuyển `reset(o.release())`; `reset`; `get`, `*`, `->`, `explicit operator bool`; `swap`. Hàm chuyển đều `noexcept`.
    **Nối tiếp:** "Phép gán di chuyển có cần `if (this != &o)` không?" Không với bản này: `o.release()` làm `p_` rỗng rồi `reset` nhận lại đúng con trỏ cũ, nên tự gán là không làm gì. Mình chạy bản viết tay `delete p_; p_ = o.p_; o.p_ = nullptr;`: tự gán xóa đối tượng và để `nullptr` mà không sanitizer nào báo. "Còn nếu viết kiểu đó thì sửa sao?" Thêm `if (this != &o)` hoặc đổi sang `reset(o.release())`.

??? question "Vì sao `operator bool` phải `explicit`? `if (p)` vẫn chạy thì `explicit` làm gì?"
    `explicit` cấm chuyển **ngầm**. `if (p)`, `!p`, `&&`, `while (p)` là chỗ đòi điều kiện nên được phép (chuyển theo ngữ cảnh). Nhưng `bool ok = p;`, `p + 1`, `int n = p;` bị cấm. Mình chạy bản bỏ `explicit`: `int n = q + 1;` biên dịch êm và ra `n = 2`.
    **Nối tiếp:** "Sao không so sánh `p == nullptr`?" Cũng được, nhưng cần thêm `operator==`; bản mình dùng `!p` và `static_cast<bool>(p)`. `std::unique_ptr` có `operator==` với `nullptr`, bản tối thiểu thì không.

??? question "Vì sao `unique_ptr` cùng cỡ con trỏ thô dù có bộ xóa? Bộ xóa có dữ liệu thì sao?"
    Bộ xóa mặc định là lớp rỗng; lưu làm thành viên thì ít nhất 1 byte (mình đo `ThanhVien` = 16), nhưng làm lớp cha thì được chiếm 0 byte (`KeThua` = 8). Bộ xóa có dữ liệu (một con trỏ) thì tốn thật: `UniquePtr<Dem, DemXoa>` và `std::unique_ptr<Dem, DemXoa>` đều 16.
    **Nối tiếp:** "Bộ xóa là lambda không bắt gì?" Lambda không bắt là lớp rỗng nên vẫn 8 byte (mình chạy `std::unique_ptr<Dem, decltype(l)>` với `auto l = [](Dem* p) { delete p; };`, trong đó `decltype(l)` nghĩa là "kiểu của biến `l`": 8); con trỏ hàm thì 16 (mình chạy `std::unique_ptr<FILE, int(*)(FILE*)>`: 16). C++20 có `[[no_unique_address]]` cho thành viên rỗng; mình không chạy nên chỉ nêu tên.

??? question "Hàm tạo di chuyển quên `noexcept` thì sao?"
    Mình hứa `noexcept` vì chỉ chép con trỏ. Thiếu lời hứa thì `std::is_nothrow_move_constructible` ra `false` (mình chạy: `static_assert` dừng biên dịch). Với `std::vector` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)): kiểu sao chép được mà move không `noexcept` thì vector **sao chép** khi cấp phát lại; `UniquePtr` không sao chép được nên vẫn bị move nhưng mất bảo đảm an toàn ngoại lệ mạnh của `push_back`.
    **Nối tiếp:** "Làm sao chắc lớp mình đúng?" Ba lớp kiểm: `static_assert` tính chất (không sao chép, move không ném), bộ đếm tạo/hủy tất định (`tao == huy`), và ASan/UBSan.

??? question "Vì sao có `make_unique`? Viết `UniquePtr<T>(new T(...))` có gì sai?"
    `MakeUnique` nhận đối số bao nhiêu cũng được và `forward` (giữ lvalue/rvalue) cho `T`; nơi gọi không còn `new` trần và chỉ viết tên kiểu một lần. Trước C++17, `f(UniquePtr<A>(new A), g())` có thể chạy `new A`, rồi `g()` ném, rồi mới tới hộp: rò rỉ; C++17 cấm xen kẽ kiểu đó (mình không chạy `-std=c++14` để tái hiện nên không có số liệu).
    **Nối tiếp:** "Bỏ `std::forward` thì sao?" Mình chạy: đối số chỉ-di-chuyển thành lỗi biên dịch `use of deleted function ... UniquePtr(const UniquePtr&)`, vì `args` có tên là lvalue.

??? question "Khi nào tự viết, khi nào dùng thư viện? Còn thiếu gì so với bản chuẩn?"
    Code thật dùng `std::unique_ptr`. Bản tự cài thiếu: chuyển `unique_ptr<Con>` sang `unique_ptr<Cha>`, `operator==`/`<`/băm, bộ xóa là con trỏ hàm (mình chạy: kế thừa con trỏ hàm là lỗi biên dịch), `make_unique<T[]>`. Tự cài hợp cho học, phỏng vấn, hoặc khi cần một hộp nhỏ giữ tài nguyên của API C.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Chép con trỏ ở hàm tạo di chuyển mà quên đặt nguồn về `nullptr`"
    `p_(o.p_)` biên dịch sạch, chạy thấy `huy` bình thường rồi sập ở hàm hủy thứ hai (ASan: `attempting double-free`). `std::move` không đặt gì; việc đó là của hàm tạo di chuyển. Dùng `o.release()`.

!!! warning "Lỗi 2: Viết phép gán di chuyển bằng tay mà bỏ sót một trong ba việc"
    Xóa cũ (quên thì LeakSanitizer báo rò rỉ), chống tự gán (quên thì đối tượng biến mất im lặng), đặt nguồn về `nullptr` (quên thì double free). `reset(o.release())` gom đủ cả ba.

!!! warning "Lỗi 3: Quên rằng bộ xóa tùy chỉnh không nhận `nullptr`, và `delete` khác `delete[]`"
    Hàm hủy phải `if (p_)` trước khi gọi bộ xóa (`fclose(nullptr)` sập: ASan `SEGV`). Mảng thì kiểu phải là `UniquePtr<T[]>` để gọi `delete[]`; dùng bản đơn thì ASan báo `bad-free` hoặc `alloc-dealloc-mismatch`.

!!! warning "Lỗi 4: Khi nói, chỉ viết mà không giải thích `explicit` và `noexcept`"
    Người phỏng vấn chấm ở lời giải thích: mỗi bánh răng chặn lỗi nào. Đừng quên `const` ở `get`/`operator*`/`operator->` (hộp hằng không làm `T` bên trong thành hằng) và nói rõ bản này thiếu gì so với `std::unique_ptr`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="77" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Vì sao hàm tạo di chuyển viết `p_(o.release())` thay vì `p_(o.p_)`?

- `release()` tạo một bản sao của đối tượng để hộp nguồn vẫn dùng được như cũ
- `release()` chép con trỏ và đặt nguồn về `nullptr` cùng lúc, nên nguồn không xóa nữa
- `release()` xóa đối tượng của nguồn ngay lập tức, nên hộp mới chỉ giữ một con trỏ trống
- `p_(o.p_)` không biên dịch được vì `p_` là thành viên `private` của một đối tượng khác

<p class="giai-thich" markdown>`release()` trả con trỏ cũ và đặt `p_` của nguồn về `nullptr` cùng lúc, nên chỉ hộp mới còn giữ và đối tượng bị xóa đúng một lần; mình chạy bản `p_(o.p_)` ra `attempting double-free`. `release()` không tạo bản sao nào và cũng không xóa gì, nên hai lựa chọn đó sai. Truy cập `o.p_` thì được phép, vì cùng một lớp thấy thành viên `private` của nhau; vấn đề không phải quyền truy cập mà là nguồn còn giữ con trỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau (`Dem` tăng `soTao` ở hàm tạo, `soHuy` ở hàm hủy; hàm tạo/gán di chuyển viết đúng như bài). Sau dòng cuối, `soTao` và `soHuy` là bao nhiêu?

```text
UniquePtr<Dem> a(new Dem(1));
UniquePtr<Dem> b(new Dem(2));
b = std::move(a);
```

- `soTao = 2`, `soHuy = 0`: `Dem` 2 vẫn nằm đó vì `b` chưa chết và chưa ai xóa nó
- `soTao = 2`, `soHuy = 2`: cả hai `Dem` đều bị xóa ngay trong lúc gán, mỗi cái một lần
- `soTao = 2`, `soHuy = 1`: `reset` xóa `Dem` 2 cũ của `b`
- `soTao = 3`, `soHuy = 1`: phép gán tạo thêm một `Dem` mới để chuyển

<p class="giai-thich" markdown>Phép gán dùng `reset(o.release())`: `release` lấy `Dem` 1 khỏi `a`, `reset` đặt nó vào `b` và xóa `Dem` 2 cũ, nên một lần hàm hủy chạy. Kết quả `soHuy = 0` là của bản viết tay quên xóa cũ, mà mình chạy ra rò rỉ. `soHuy = 2` sai vì `Dem` 1 chỉ đổi chủ chứ không bị xóa. Không có hàm tạo nào chạy trong phép gán, nên `soTao` giữ nguyên 2.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** `UniquePtr` có `explicit operator bool`. Đọc đoạn sau: dòng nào là lỗi biên dịch?

```text
UniquePtr<Dem> p(new Dem(1));
if (p) {}               // dòng 2
bool ok = p;            // dòng 3
bool ok2(p);            // dòng 4
int n = p + 1;          // dòng 5
```

- Dòng 3 và dòng 5, vì cả hai cần chuyển ngầm
- Chỉ dòng 3, vì chỉ có nó khởi tạo bằng dấu `=`
- Dòng 4 và dòng 5, vì cả hai chuyển kiểu rõ ràng
- Dòng 2 và dòng 3, vì cả hai đều dùng kiểu `bool`

<p class="giai-thich" markdown>`explicit` cho phép chuyển ở chỗ đòi điều kiện (`if`) và khi bạn đòi rõ (khởi tạo trực tiếp `bool ok2(p)`), nhưng cấm chuyển ngầm: `bool ok = p;` là khởi tạo bằng dấu `=` và `p + 1` cần chuyển ngầm sang số, nên cả hai lỗi (mình đã chạy ra hai lỗi). Chỉ dòng 3 bỏ sót dòng 5. Dòng 4 viết kiểu trực tiếp nên được; còn dòng 2 là chỗ điều kiện nên cũng được, nên không thể là lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Vì sao `UniquePtr<T, D>` kế thừa `private D` thay vì có thành viên `D d_;` khi `D` là lớp rỗng?

- Để gọi được hàm thành viên của `D` mà không cần viết `get_deleter()` ở bất kỳ chỗ nào
- Vì thành viên có kiểu lớp rỗng không được phép khai báo trong một class template
- Vì kế thừa khiến bộ xóa được gọi tự động trong hàm hủy mà người viết không cần làm gì
- Vì thành viên rỗng vẫn chiếm chỗ và làm hộp to thành 16 byte; làm lớp cha thì được chiếm 0 byte

<p class="giai-thich" markdown>Mỗi thành viên phải có địa chỉ riêng nên lớp rỗng làm thành viên chiếm ít nhất 1 byte rồi bị đệm lên 8: mình đo `ThanhVien` = 16 còn `KeThua` = 8. Kế thừa không làm bộ xóa tự chạy; hàm hủy vẫn phải gọi nó. Thành viên kiểu lớp rỗng khai báo được bình thường (chính `ThanhVien` biên dịch), và chuyện gọi `D::operator()` là chuyện tiện, không phải lý do của thiết kế.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Phép gán di chuyển viết tay như dưới đây, rồi gọi `a = std::move(a);` (qua một tham chiếu). Chuyện gì xảy ra?

```text
UniquePtr& operator=(UniquePtr&& o) noexcept {
    delete p_;
    p_ = o.p_;
    o.p_ = nullptr;
    return *this;
}
```

- ASan báo double free vì `delete p_` chạy hai lần trên cùng một địa chỉ
- `a` thành rỗng và đối tượng bị hủy, không sanitizer nào báo gì
- LeakSanitizer báo rò rỉ vì đối tượng cũ không được xóa trước khi gán
- `a` giữ nguyên đối tượng, vì gán một đối tượng cho chính nó là không làm gì

<p class="giai-thich" markdown>Với `o` chính là `*this`: `delete p_` xóa đối tượng, `p_ = o.p_` chép con trỏ vừa xóa, rồi `o.p_ = nullptr` đặt luôn `p_` của `a` về rỗng; mình chạy ra `tao=1 huy=1` và `a` rỗng, không báo lỗi nào. Không có double free vì hàm hủy gặp `nullptr`. Không có rò rỉ vì đối tượng **đã** bị xóa. Còn "không làm gì" là điều ta mong, nhưng bản này làm mất đối tượng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Vì sao `reset` của bản có bộ xóa phải viết `if (cu) get_deleter()(cu);` chứ không gọi bộ xóa luôn?

- Vì gọi bộ xóa hai lần liên tiếp trên cùng một con trỏ luôn bị trình biên dịch cấm hẳn
- Vì bộ xóa tùy chỉnh chỉ được phép gọi đúng một lần trong suốt cả chương trình
- Vì hộp đã chuyển đi có `nullptr` mà hàm hủy vẫn chạy; `fclose(nullptr)` thì sập
- Vì `delete` trên `nullptr` luôn sập nên mọi bộ xóa đều phải kiểm tra trước

<p class="giai-thich" markdown>Hộp nguồn sau khi chuyển có `p_ == nullptr` nhưng hàm hủy của nó vẫn chạy; nếu gọi bộ xóa thì `fclose(nullptr)` sập (mình chạy ra ASan `SEGV` và `dong tep` in hai lần). Trình biên dịch không hề cấm gọi hai lần, và mỗi hộp có thể gọi bộ xóa của nó khi nào cần. Còn `delete nullptr` vô hại, nên bản đề 1 không cần kiểm tra; chỉ bộ xóa tùy chỉnh mới cần.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** `MakeUnique` viết `new T(args...)` thay vì `new T(std::forward<Args>(args)...)`. Gọi `MakeUnique<Chu>(MakeUnique<Dem>(5))`, trong đó `Chu` có hàm tạo `Chu(UniquePtr<Dem> x)`. Điều gì xảy ra?

```text
template <typename T, typename... Args>
UniquePtr<T> MakeUnique(Args&&... args) {
    return UniquePtr<T>(new T(args...));
}
```

- Biên dịch được và chạy đúng, vì `Args&&` đã giữ nguyên đối số là rvalue rồi
- Biên dịch được, nhưng `Dem` bị hủy hai lần vì `args` chỉ chép con trỏ thô
- Lỗi biên dịch vì `Args&&` không thể nhận được một kiểu chỉ-di-chuyển như `UniquePtr`
- Lỗi biên dịch: `args` có tên nên là lvalue, phải sao chép mà bản sao đã bị xóa

<p class="giai-thich" markdown>Tên `args` luôn là lvalue (như `o` ở hàm tạo di chuyển), nên `Chu(UniquePtr<Dem>)` nhận nó bằng sao chép, mà hàm sao chép đã `= delete`; mình chạy ra `use of deleted function`. `std::forward` mới trả lại loại rvalue ban đầu. `Args&&` nhận được rvalue `UniquePtr` bình thường, nên lỗi không nằm ở tham số hàm. Và vì không biên dịch được nên chuyện hủy hai lần không có cơ hội xảy ra.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 8.** Ở đề 2, `UniquePtr<Dem> m(new Dem[3]);` (dùng bản đơn cho mảng) biên dịch sạch. Chạy với ASan thì sao?

- Báo `bad-free`: hàm hủy `delete` một địa chỉ không phải đầu khối `new[]`
- Chạy bình thường vì `delete` và `delete[]` cùng giải phóng một khối heap
- LeakSanitizer báo rò rỉ vì chỉ phần tử đầu được xóa, hai phần tử còn lại thì không
- Báo `use-after-free` vì mảng bị xóa trước khi hàm hủy chạy

<p class="giai-thich" markdown>Bản đơn gọi `delete` thay vì `delete[]`; với g++ ở đây và kiểu có hàm hủy, `new[]` ghi thêm 8 byte đầu khối, nên `delete` đưa cho bộ cấp phát một địa chỉ lệch 8 byte và ASan báo `attempting free on address which was not malloc()-ed` (`bad-free`). Hai cách xóa không thể thay cho nhau, nên "chạy bình thường" là hiểu nhầm. Khối bị xóa lỗi nên không có chuyện chỉ xóa một phần, và không có truy cập nào sau khi xóa nên cũng không có `use-after-free`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `UniquePtr<T>` là một con trỏ `p_` cộng bốn bánh răng: hàm hủy `delete p_`; **xóa** sao chép (hai dòng `= delete`) để không có hai chủ; hàm tạo/gán di chuyển viết bằng `release()` và `reset()` (`release` = `std::exchange(p_, nullptr)`) nên nguồn luôn về `nullptr` và tự gán an toàn; và `get`/`*`/`->`/`explicit operator bool`/`swap`, mọi hàm chuyển đều `noexcept`.
2. Kiểm bằng ba lớp: `static_assert` với `std::is_copy_constructible`/`is_nothrow_move_constructible`, đối tượng `Dem` đếm tạo/hủy tất định (`tao == huy`, trong cả `std::vector`), và `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined` (cả hai lời giải sạch; `sizeof` bằng `std::unique_ptr`: 8 byte).
3. Bẫy đã chạy: quên cấm sao chép hoặc quên đặt nguồn về `nullptr` thì ASan `attempting double-free`; phép gán viết tay quên xóa cũ thì LeakSanitizer báo rò rỉ, tự gán không chống thì đối tượng mất im lặng (không sanitizer nào báo); hai `new` thô gặp ngoại lệ thì rò rỉ, thành viên `UniquePtr` thì sạch; dùng nguồn sau move là null deref.
4. Bộ xóa tùy chọn: `D` là một kiểu có `operator()`; kế thừa `private D` để bộ xóa rỗng chiếm 0 byte (đo: thành viên 16, kế thừa 8); hàm hủy không gọi bộ xóa với `nullptr` (`fclose(nullptr)` sập); bộ xóa có dữ liệu thì tốn thật (16, bằng `std::unique_ptr`); kế thừa không dùng được với con trỏ hàm.
5. `MakeUnique<T>(args...)` dùng gói đối số và `std::forward` (bỏ `forward` thì đối số chỉ-di-chuyển thành lỗi biên dịch); `UniquePtr<T[]>` là chuyên biệt hóa gọi `delete[]` và có `operator[]`, dùng bản đơn cho mảng thì ASan `bad-free`; code thật vẫn dùng `std::unique_ptr` vì nó đủ hơn (chuyển Con thành Cha, so sánh, băm, con trỏ hàm).
