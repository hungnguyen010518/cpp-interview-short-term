# Bài 82 — Live-coding: tự cài std::function và type erasure

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một `Function<R(Args...)>` nhận hàm thường, lambda có bắt và functor bằng **type erasure** (xóa kiểu: lớp cơ sở ảo + lớp mẫu bọc thứ gọi được), có sao chép sâu, di chuyển, hộp rỗng; chạy sạch `-fsanitize=address,undefined`.
    - Nói được **chi phí thật** của nó (đếm bằng `operator new` thay thế: lambda nhỏ 0 lần, lambda lớn 1 lần) và thêm **small buffer** (chỗ dựng sẵn trong hộp, placement new) để lambda nhỏ khỏi cấp phát; biết cái giá của nó.
    - Dựng `Registry` (Observer) trên `Function`, và thấy ba bản sai chạy thật: quên `virtual` ở hàm hủy, sao chép nông, lambda bắt tham chiếu tới biến cục bộ đã chết.
    - Trả lời nối tiếp: `std::function` khác bản của mình ở đâu, `std::any` là cùng ý tưởng, khi nào chọn template/giao diện/`std::function` và khi nào **không** nên tự viết.

**Bạn cần biết trước:** [Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md) (hàm ảo, hàm hủy ảo, hàm thuần ảo), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template lớp, chuyên biệt hóa), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda, `[=]`/`[&]`, bẫy tham chiếu treo), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) và [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (`std::function`, Observer, đếm `new` bằng `operator new` thay thế), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (sao chép sâu, Rule of 3/5, `noexcept` với `vector`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (ASan, UBSan). Template tham số biến thiên (`Args...`), `std::forward` và `if constexpr` chưa có bài nào dạy đủ nên bài này **giải thích tại chỗ** ở mức đọc hiểu; placement new và `alignas` đã học ở [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md), bài này chỉ nhắc lại.

## 🧠 Câu chuyện mở đầu

Người phỏng vấn mở trình soạn thảo trống. "Anh dùng `std::function` hằng ngày rồi. Giờ coi nó là một cái hộp kín: tháo ra, viết lại cho tôi một cái giống vậy. Nhận được hàm thường, lambda có bắt, cả functor. Sao chép được, chuyển được. Anh nói to khi nghĩ nhé."

Trong **xưởng tự lắp đồ**, `std::function` là một **vỏ hộp chuẩn** có đúng một ổ cắm và một nút "chạy". Thiết bị nào cũng có phích khác nhau (mỗi lambda một kiểu riêng); xưởng làm sau vỏ một **đầu chuyển** riêng cho từng thiết bị, rồi vỏ chỉ cần biết "bấm nút thì đầu chuyển lo". Hôm nay ta tự tháo hộp ra xem từng bánh răng.

!!! info "Chỗ nào ví von không còn đúng?"
    Ngoài xưởng, đầu chuyển được lắp lúc chạy. Trong C++, mỗi loại đầu chuyển là một lớp mẫu do trình biên dịch sinh **lúc biên dịch**; lúc chạy chỉ còn việc chọn đúng hàm qua bảng hàm ảo. Và hộp **chép luôn thiết bị** khi bị sao chép, chứ không cho hai hộp dùng chung một thiết bị.

## 📖 Giải thích

### 1. Đề 1: `Function<R(Args...)>`

!!! example "Đề 1"
    Viết `Function` sao cho `Function<int(int, int)>` chứa được **một** thứ gọi được nhận hai `int` trả `int`: hàm thường, lambda (có hoặc không bắt biến), functor (struct có `operator()`).
    **Ràng buộc:** gọi bằng `f(2, 3)`; sao chép được (hai hộp độc lập), chuyển được (hộp nguồn thành rỗng); hộp rỗng mà gọi thì ném `std::bad_function_call`; không rò rỉ bộ nhớ; C++17, chỉ thư viện chuẩn.
    **Vào/ra:** `f = cong; f(2,3)` ra 5. Lambda `[heso](int x){...}` với `heso = 10` bắt lúc tạo thì dù sau đó `heso` đổi, hộp vẫn nhân với 10. Lambda đếm `mutable` sao chép ra hai hộp thì đếm độc lập.

??? tip "Gợi ý 1"
    Mỗi lambda có một kiểu riêng, nên `Function<int(int)>` không thể là template theo kiểu lambda. Vậy trong hộp phải cất cái gì để mọi lambda dùng chung **một** kiểu?

??? tip "Gợi ý 2"
    Một lớp cơ sở có hàm ảo `goi`, và một lớp con **template** `Giu<F>` giữ đúng thứ gọi được kiểu `F`. Hộp chỉ giữ một `Base*` trỏ tới `Giu<F>` trên heap. Sao chép cũng phải đi qua hàm ảo: vì sao hộp không tự sao chép được?

??? tip "Gợi ý 3"
    Cần ba hàm ảo: `goi`, `nhanBan` (clone: tạo bản sao cùng kiểu thật), và hàm hủy ảo. Hàm tạo của `Function` là template nhận `F` **theo giá trị**. Gán dùng copy-and-swap (Bài 11): tham số nhận theo giá trị, đổi con trỏ, bản cũ tự chết mang đồ cũ đi.

### 2. Hướng giải đề 1: quên kiểu, chỉ nhớ "làm được gì"

Lambda không bắt có kiểu riêng; lambda bắt `heso` lại có kiểu khác ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md): kiểu không có tên). Nhưng `Function<int(int)>` phải là **một** kiểu, để cất được vào `vector` hay làm thành viên của lớp. Muốn vậy hộp phải **quên** kiểu cụ thể và chỉ nhớ ba việc làm được với nó: **gọi**, **nhân bản**, **hủy**. Kỹ thuật này gọi là **type erasure (xóa kiểu)**. Có ba mảnh:

| Mảnh | Làm gì | Biết kiểu `F` không? |
|---|---|---|
| `Base` (lớp cơ sở ảo) | Khai ba việc: `goi`, `nhanBan`, hủy | Không |
| `Giu<F>` (lớp mẫu, con của `Base`) | Cất một `F`, làm ba việc đó cho đúng `F` | **Có** |
| `Function` (vỏ ngoài) | Giữ một `Base*`, chuyển lời gọi qua hàm ảo | Không |

```text
  f1 (trên stack)         heap (địa chỉ minh họa 0x5000)
  ┌─────────┐            ┌──────────────────────────────┐
  │ p_ ─────┼──────────► │ vptr │ f = &cong             │  <- một Giu<int(*)(int,int)>
  └─────────┘            └──────────────────────────────┘
  vptr trỏ tới bảng hàm ảo của đúng lớp Giu<...> này (Bài 33)
```

**Hai cách khác** cho cùng việc: tự dựng "bảng hàm ảo bằng tay" (một `void*` trỏ tới thiết bị, kèm ba con trỏ hàm: gọi, sao chép, hủy; kiểu C, chạy được nhưng dài và dễ sai), hoặc để trình biên dịch dựng giúp bằng hàm ảo như trên. Trên bảng trắng chọn hàm ảo: ngắn, ai cũng đọc được. Điều bạn phải nói to là **hai thứ đi cùng nhau**: template ở `Giu<F>` để *nhớ* kiểu, hàm ảo ở `Base` để *quên* kiểu khi ra ngoài.

### 3. Ba thứ mới cần đọc được

**(a) Kiểu hàm `R(Args...)` và chuyên biệt hóa từng phần.** `int(int, int)` là một **kiểu** (không phải giá trị), đọc là "hàm nhận hai `int`, trả `int`". Ta khai báo hai lần: dòng (1) `template <typename Sig> class Function;` là cái tên chung, **chưa có thân**; dòng (2) `class Function<R(Args...)>` là bản dành riêng cho mọi `Sig` có dạng "trả `R`, nhận `Args...`". Gọi `Function<int(int, int)>` thì trình biên dịch tự tách `R = int`, `Args = int, int`. ([Bài 34](../nhom-4-oop-patterns/34-template.md) chỉ nêu tên chuyên biệt hóa từng phần; đây là một ví dụ.)

**(b) Gói tham số `Args...` và `std::forward`.** `typename... Args` là "một gói gồm không, một hay nhiều kiểu". `Args... args` là "mỗi kiểu trong gói một tham số". Đặt `...` sau một biểu thức là **mở gói**: viết lại biểu thức cho từng phần tử, ngăn bằng dấu phẩy. Với `Args = int, int` thì `f(std::forward<Args>(args)...)` thành `f(std::forward<int>(a1), std::forward<int>(a2))`. `std::forward<T>(x)` giữ nguyên "kiểu đi vào": `T` là kiểu giá trị thì cho `x` đi như một tạm thời (có thể chuyển, [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) chỉ nêu tên), `T` là tham chiếu (`int&`) thì vẫn là tham chiếu. Nhờ vậy `Function<void(int&)>` sửa được biến gốc.

**(c) Nhận `F` theo giá trị.** `template <typename F> Function(F f)` nhận theo giá trị nên `F` tự bỏ `&` và `const`, và tên hàm `cong` biến thành con trỏ hàm `int(*)(int,int)` (giống mảng thoái hóa thành con trỏ ở [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md)). Bản của libstdc++ 11 (mình đọc `<bits/std_function.h>`) nhận `F&&` rồi phải gọt tay bằng `std::decay_t<F>` để được kết quả tương tự (chuẩn C++17 viết theo giá trị, theo trí nhớ); ta nhận theo giá trị cho khỏi viết. Hàm tạo template này còn **không** hút nhầm lời sao chép `Function a = b;`: chuẩn cấm sinh hàm tạo nhận chính lớp đó theo giá trị, nên `Function(const Function&)` được chọn.

### 4. Đề 2: callback registry dùng `Function`

!!! example "Đề 2"
    Viết `Registry` kiểu Observer: `int dangKy(Function<void(int)>)` trả mã số, `bool huyDangKy(int ma)`, `void phat(int sk)` gọi từng callback theo thứ tự đăng ký. Rồi trả lời: **mỗi lần đăng ký tốn mấy lần cấp phát heap, làm sao giảm?** Lambda `[&tong]` bắt tham chiếu có an toàn không?
    **Vào/ra:** callback 1 cộng `sk` vào `tong`, callback 2 ghi `"cam bien" + sk + ";"` vào `log`. `phat(3)`, `phat(4)` cho `tong = 7`; hủy callback 2 rồi `phat(5)` cho `tong = 12`, còn 1 mục.

??? tip "Gợi ý 1"
    `Registry` chỉ cần `std::vector` các cặp (mã, `Function`). Việc chính là đưa `Function` vào vector: chuyển, không sao chép.
    
??? tip "Gợi ý 2"
    Muốn lambda nhỏ khỏi lên heap thì hộp phải có **chỗ sẵn bên trong nó**: một mảng byte `buf_[N]`, dựng `Giu<F>` vào đó bằng placement new khi vừa chỗ, không vừa mới `new`.

??? tip "Gợi ý 3"
    Khi `Giu<F>` nằm trong `buf_`, hộp có con trỏ `p_` trỏ **vào chính nó**. Sao chép thô các byte sẽ cho con trỏ trỏ vào hộp cũ. Nên chuyển phải qua một hàm ảo `diChuyen(cho)` dựng đối tượng mới tại chỗ mới. Nhớ `noexcept`, và nhớ hủy bằng `p_->~Base()` chứ không `delete`.

### 5. Hướng giải đề 2: chi phí, rồi small buffer

Bản đề 1 **luôn** `new` một `Giu<F>` cho mỗi hộp, kể cả lambda chỉ bắt một `int`. Trong `Registry` thì mỗi `dangKy`, mỗi lần **sao chép** hộp cũng thế. **Small buffer optimization (SBO)** là mánh quen thuộc ([Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) có cùng ý cho chuỗi ngắn, gọi là SSO; [Bài 80](80-tu-cai-string.md) tự cài nó): giữ sẵn trong hộp một mảng byte, vừa thì dựng ngay trong đó.

Điều kiện để dựng trong hộp (dòng (8) của code): `Giu<F>` vừa `N` byte; căn lề không quá `alignof(std::max_align_t)` (căn lề lớn nhất "bình thường", thường 16); và `F` chuyển được **không ném** (để hộp chuyển được `noexcept`). Kết quả: cái giá của lambda nhỏ chỉ còn gọi hàm ảo.

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Hàm chỉ **gọi** callback trong lúc chạy, không cất; gọi nhiều (so sánh khi sort) | tham số template `F` | Gọi thẳng, inline được, không xóa kiểu, không cấp phát |
| **Cất** callback lâu dài (thành viên, registry, hàng đợi), nhiều loại khác nhau | `std::function` | Một kiểu cho mọi thứ gọi được |
| Callback có nhiều thao tác, trạng thái, tên gọi riêng | giao diện + hàm ảo ([Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md), [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md)) | Rõ vai trò, mở rộng được |
| Chỉ hàm thường không bắt, giao tiếp với API kiểu C | con trỏ hàm | 8 byte, không cấp phát, không bắt được gì |
| Lambda **chỉ chuyển được** (giữ `unique_ptr`) | `std::move_only_function` (C++23, g++ 11 chưa có) hoặc bọc `shared_ptr` | `std::function` đòi sao chép được |

**Khi nào KHÔNG tự viết `Function`:** trong code thật. Dùng `std::function`: nó đã xử lý đủ trường hợp (con trỏ hàm thành viên, ràng buộc kiểu, các bộ so sánh với `nullptr`). Tự viết chỉ để hiểu bản chất, hoặc vì người phỏng vấn đòi. Và khi hot loop chạy hàng triệu lần: đo trước, nếu chỉ cần gọi tại chỗ thì dùng tham số template.

## 💻 Ví dụ code

### Xây đề 1 từng bước

**Bước 1: hộp rỗng.** Tên chung (1), bản cho dạng `R(Args...)` (2), và một con trỏ `Base* p_ = nullptr;` (`nullptr` = hộp rỗng).

**Bước 2: giao diện và hộp con.** `Base` khai ba việc; `Giu<F>` làm chúng cho đúng `F` (bên trong `Giu<F>`, viết trơn `Giu` là chỉ chính nó):

```text
struct Base {
    virtual ~Base() = default;                          // hủy đúng loại, qua Base*
    virtual R goi(Args... args) = 0;                    // gọi
    virtual Base* nhanBan() const = 0;                  // nhân bản (clone) cùng kiểu thật
};
template <typename F> struct Giu : Base {
    F f;
    R goi(Args... args) override { return f(std::forward<Args>(args)...); }
    Base* nhanBan() const override { return new Giu(f); }
};
```

**Bước 3: vỏ ngoài đủ Rule of 5.** Hàm tạo template `Function(F f) : p_(new Giu<F>(std::move(f)))`; sao chép gọi `p_->nhanBan()`; chuyển lấy con trỏ rồi đặt nguồn về `nullptr`; gán nhận theo giá trị rồi `swap`; hủy `delete p_`; `operator()` ném `bad_function_call` nếu rỗng. Ghép lại thành bản đầy đủ ở mục sau.

### Lời giải đề 1: `Function` bằng hàm ảo

Bốn thứ cần đọc được trong chương trình dưới:

- `try`/`catch` ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)) để bắt `bad_function_call`.
- Lớp `Dem` đếm số bản đang sống, để thấy hộp hủy đúng.
- `mutable` sau `()` của lambda: lambda bình thường coi biến bắt là hằng; `mutable` cho sửa **bản chép nằm trong lambda** (biến gốc không đổi). `(void)d;` chỉ để lambda "dùng" biến bắt; một số trình biên dịch (như clang) cảnh báo biến bắt không dùng, g++ 11 thì không.
- Hàm tạo `Function(F f)` không đánh `explicit` nên viết được `Function<...> f = cong;`; còn `explicit operator bool()` cho phép hỏi `(dem ? "con" : "rong")` mà hộp không tự đổi thành số ở chỗ khác.

```cpp
#include <functional>
#include <iostream>
#include <string>
#include <utility>

template <typename Sig>
class Function;                                              // (1) khai báo chung, chưa có thân

template <typename R, typename... Args>
class Function<R(Args...)> {                                 // (2) bản dành riêng cho dạng "R(Args...)"
    struct Base {                                            // (3) giao diện: chỉ biết gọi và nhân bản
        virtual ~Base() = default;                           // (4) hàm hủy ảo
        virtual R goi(Args... args) = 0;
        virtual Base* nhanBan() const = 0;
    };
    template <typename F>
    struct Giu : Base {                                      // (5) hộp giữ một thứ gọi được kiểu F
        F f;
        explicit Giu(F g) : f(std::move(g)) {}
        R goi(Args... args) override { return f(std::forward<Args>(args)...); }   // (6)
        Base* nhanBan() const override { return new Giu(f); }                     // (7)
    };
    Base* p_ = nullptr;                                      // (8) nullptr = hộp rỗng

public:
    Function() = default;
    template <typename F>
    Function(F f) : p_(new Giu<F>(std::move(f))) {}          // (9) nhận mọi thứ gọi được
    Function(const Function& o) : p_(o.p_ ? o.p_->nhanBan() : nullptr) {}   // (10) sao chép sâu
    Function(Function&& o) noexcept : p_(o.p_) { o.p_ = nullptr; }          // (11) chuyển: lấy con trỏ
    Function& operator=(Function o) noexcept {               // (12) gán: hoán đổi với bản nhận về
        std::swap(p_, o.p_);
        return *this;
    }
    ~Function() { delete p_; }                               // (13)
    explicit operator bool() const { return p_ != nullptr; }
    R operator()(Args... args) const {                       // (14)
        if (!p_) throw std::bad_function_call();
        return p_->goi(std::forward<Args>(args)...);
    }
};

int song = 0, chep = 0;                                      // đếm số bản Dem đang sống, số lần sao chép
struct Dem {
    Dem() { ++song; }
    Dem(const Dem&) { ++song; ++chep; }
    Dem(Dem&&) noexcept { ++song; }
    ~Dem() { --song; }
};

int cong(int a, int b) { return a + b; }
struct NhanDoi {                                             // functor: lớp có operator()
    int operator()(int x) const { return 2 * x; }
};

int main() {
    Function<int(int, int)> f1 = cong;                       // hàm thường
    std::cout << "ham thuong: " << f1(2, 3) << "\n";

    int heso = 10;
    Function<int(int)> f2 = [heso](int x) { return x * heso; };   // lambda có bắt (chép)
    heso = 99;
    std::cout << "lambda bat: " << f2(4) << "\n";
    f2 = NhanDoi();                                          // functor, gán lại
    std::cout << "functor: " << f2(4) << "\n";

    Function<void(int&)> tang = [](int& x) { ++x; };         // tham chiếu đi xuyên qua hộp
    int v = 1;
    tang(v);
    std::cout << "tham chieu: v = " << v << "\n";

    int n = 0;
    Function<int()> dem = [n]() mutable { return ++n; };     // lambda có trạng thái riêng
    dem();
    dem();
    Function<int()> ban = dem;                               // sao chép sâu: ban có n riêng
    std::cout << "dem: " << dem() << " " << ban() << " " << ban() << " " << dem() << "\n";

    Function<int()> chuyen = std::move(dem);                 // chuyển: dem thành rỗng
    std::cout << "sau chuyen: dem " << (dem ? "con" : "rong")
              << ", chuyen() = " << chuyen() << "\n";
    try {
        dem();
    } catch (const std::bad_function_call&) {
        std::cout << "goi hop rong: bad_function_call\n";
    }

    {
        Dem d;
        Function<void()> g = [d]() { (void)d; };             // lambda giữ một bản Dem, nằm trong hộp g
        Function<void()> h = g;                              // sao chép sâu: h có bản Dem riêng
        std::cout << "trong khoi: song=" << song << " chep=" << chep << "\n";
    }
    std::cout << "ra khoi: song=" << song << "\n";
    std::cout << "sizeof(Function) = " << sizeof(Function<int()>) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `f1 = cong` | Hàm tạo (9) với `F = int(*)(int,int)`: `new Giu<...>` trên heap, `p_` trỏ tới nó | `f1.p_ ──► [vptr \| &cong]` (địa chỉ minh họa) |
| `f1(2, 3)` | `operator()` (14) → `p_->goi(2,3)`: hàm ảo, vào `Giu<...>::goi` → `cong(2,3)` = 5 | không đổi |
| `f2 = [heso]...` | `heso` được **chép** vào lambda lúc tạo (qua hàm tạo (9)); sau `heso = 99` hộp vẫn nhân 10; `f2(4)` = 40 | `[vptr \| heso=10]` |
| `f2 = NhanDoi()` | `NhanDoi()` thành hộp tạm (9); gán (12) đổi `p_` với `o`; `o` chết ở cuối hàm, mang hộp lambda cũ đi (13) | `f2.p_ ──► [vptr \| NhanDoi]`, hộp cũ đã `delete` |
| `tang(v)` | `Args = int&`: `forward<int&>` giữ tham chiếu, nên `++x` sửa `v` gốc → 2 | `v` ở stack, đổi trực tiếp |
| `ban = dem` | Hai lần `dem()` đưa `n` tới 2; `ban` (10) gọi `nhanBan` (7): chép cả lambda (n = 2) vào một `Giu` mới | hai hộp, hai `n` riêng |
| in `dem: ...` | `dem()`=3, `ban()`=3, `ban()`=4, `dem()`=4: đếm độc lập | |
| `chuyen = move(dem)` | (11): lấy `p_` của `dem`, đặt `dem.p_ = nullptr`; `dem` thành rỗng; `chuyen()` = 5 | `chuyen.p_ ──► hộp cũ của dem`, `dem.p_ = nullptr` |
| `dem()` rỗng | `p_` là `nullptr` nên (14) ném `bad_function_call`, `catch` bắt | |
| khối `Dem` | `[d]` chép `d` vào lambda; chuyển vào hộp `g`; `h = g` chép thêm một bản. Còn sống: `d`, bản trong `g`, bản trong `h` = 3; đã sao chép 2 lần | |
| ra khối | `h`, `g` hủy: `delete p_` → hàm hủy **ảo** (4) → `~Giu` → `~Dem`. `d` hủy. Còn sống: 0 | |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`):

```text
ham thuong: 5
lambda bat: 40
functor: 8
tham chieu: v = 2
dem: 3 3 4 4
sau chuyen: dem rong, chuyen() = 5
goi hop rong: bad_function_call
trong khoi: song=3 chep=2
ra khoi: song=0
sizeof(Function) = 8
```

Mình chạy chương trình này với `-fsanitize=address,undefined` ở cả `-O0` và `-O2`, và biên dịch `-std=c++17 -Wall -Wextra`: **không cảnh báo, ASan và UBSan sạch, thoát mã 0, đầu ra giống nhau**. `sizeof = 8` là trên máy 64-bit này (một con trỏ).

**Thử thay đổi** (mình đã chạy cả bốn, thay đúng dòng nói tới trong `main`; ví dụ đầu cần thêm `#include <memory>`):

- **Bắt một `unique_ptr`:** `auto p = std::make_unique<int>(5); Function<int()> f = [q = std::move(p)]() { return *q; };` (`[q = std::move(p)]` tạo biến `q` trong lambda từ biểu thức bên phải, cú pháp C++14). Lỗi biên dịch: `use of deleted function ... unique_ptr(const unique_ptr&)`. Vì `Giu::nhanBan` cần **sao chép** `F`, nên lambda chỉ-chuyển không vào được; `std::function` thật cũng đòi sao chép được ([Bài 67](../nhom-9-thuc-chien-da-luong/67-thread-pool-tu-viet.md) gặp đúng chuyện này).
- **Sai số đối số:** `Function<int(int, int)> f = cong; f(1);` → `no match for call to '(Function<int(int, int)>) (int)'`.
- **Lambda sai chữ ký:** `Function<int(int)> f = [](int a, int b) { return a + b; };` → lỗi `no match for call to '(...<lambda(int, int)>) (int)'`, nhưng nằm **trong `Giu::goi`**, không ở dòng gán. `std::function` thật báo ngay ở dòng gán (`conversion from ... to non-scalar type 'std::function<int(int)>' requested`) vì hàm tạo của nó được ràng buộc để loại kiểu không gọi được.
- **`Function<int> f;`** (không phải kiểu hàm): `aggregate 'Function<int> f' has incomplete type`, vì chỉ có tên chung (1), chưa có thân.

### Bản SAI của đề 1

**Sai A: quên `virtual` ở hàm hủy của `Base`.** Đổi dòng (4) thành `~Base() = default;`, rồi thử một `main` có lambda bắt một `std::string` dài (phần còn lại của chương trình giữ nguyên):

```cpp
// bo-qua-kiem-tra
int main() {
    std::string dai(100, 'x');
    {
        Dem d;
        Function<void()> g = [d, dai]() { (void)d; (void)dai; };
        std::cout << "trong khoi: song=" << song << "\n";
    }
    std::cout << "ra khoi: song=" << song << "\n";
}
```

g++ `-Wall` đã cảnh báo lúc biên dịch: `deleting object of abstract class type 'Function<void()>::Base' which has non-virtual destructor will cause undefined behavior [-Wdelete-non-virtual-dtor]`. Chạy dưới ASan: `new-delete-type-mismatch ... size of the allocated type: 48 bytes; size of the deallocated type: 8 bytes` (đối tượng thật là `Giu`, nhưng `delete` qua `Base*` nên chỉ biết `Base` dài 8). Tắt riêng báo cáo đó (`ASAN_OPTIONS=new_delete_type_mismatch=0`) thì thấy hậu quả: in `trong khoi: song=2` rồi `ra khoi: song=1` (bản `Dem` trong hộp **không bao giờ bị hủy**), và LeakSanitizer báo `101 byte(s) leaked` (chuỗi trong lambda). Không sanitizer: chạy ra cùng hai dòng, thoát 0, **rò rỉ im lặng**. Chuẩn gọi đây là hành vi không xác định.

**Sai B: sao chép nông.** Hàm tạo sao chép chỉ chép con trỏ, rồi thử `Function<int()> a = [] { return 7; }; Function<int()> b = a;`:

```cpp
// bo-qua-kiem-tra
Function(const Function& o) : p_(o.p_) {}          // hai hộp cùng trỏ một Giu
```

Hai hộp cùng giữ một `Giu`; hộp chết sau `delete` lại cái đã bị hộp kia `delete`. ASan báo `heap-use-after-free` ở `~Function` (**READ of size 8**, đúng chỗ lấy `vptr` để gọi hàm hủy ảo), kèm "freed by ... `~Giu` ... `~Function`". Không sanitizer: thoát mã **139** (SIGSEGV). Nó là double free "hóa trang": trước khi kịp xóa lần hai thì đã đọc vào bộ nhớ chết.

### Lời giải đề 2: small buffer và `Registry`

Bản này thêm tham số `N` (số byte chỗ dựng sẵn) và hai hàm ảo mới. Ba thứ cần nhắc:

- **Placement new** `new (cho) T(...)` ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)) chỉ chạy hàm tạo tại địa chỉ `cho` có sẵn, không xin heap (cần `<new>`); vì không có `delete` tương ứng nên hủy bằng tay `p->~T()`. `alignas(std::max_align_t)` đặt mảng byte ở địa chỉ chia hết cho căn lề đủ cho mọi kiểu thường gặp.
- **`if constexpr`** (C++17, mới) là `if` mà điều kiện biết **lúc biên dịch**: nhánh không được chọn bị bỏ, không biên dịch. Cần vì `new (buf_) G` sẽ hỏng khi `G` quá lớn, dù nhánh không chạy.
- Hàm `operator new` thay thế để đếm cấp phát là của [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (và [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)).

```cpp
#include <cstddef>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <new>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

int soLanNew = 0;                                            // đếm mỗi lần ai đó xin heap
void* operator new(std::size_t n) {
    ++soLanNew;
    void* p = std::malloc(n);
    if (!p) throw std::bad_alloc();
    return p;
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

template <typename Sig, std::size_t N = 24>                  // (1) N = chỗ dựng sẵn trong hộp (byte)
class Function;

template <typename R, typename... Args, std::size_t N>
class Function<R(Args...), N> {
    struct Base {
        virtual ~Base() = default;
        virtual R goi(Args... args) = 0;
        virtual Base* nhanBan(void* cho) const = 0;          // (2) cho != nullptr: dựng bản sao vào đó
        virtual Base* diChuyen(void* cho) noexcept = 0;      // (3) chỉ dùng khi đang nằm trong hộp
    };
    template <typename F>
    struct Giu : Base {
        F f;
        explicit Giu(F g) : f(std::move(g)) {}
        R goi(Args... args) override { return f(std::forward<Args>(args)...); }
        Base* nhanBan(void* cho) const override { return cho ? new (cho) Giu(f) : new Giu(f); }
        Base* diChuyen(void* cho) noexcept override { return new (cho) Giu(std::move(f)); }
    };

    alignas(std::max_align_t) unsigned char buf_[N == 0 ? 1 : N];   // (4) chỗ dựng sẵn
    Base* p_ = nullptr;
    bool trong_ = false;                                     // (5) true: đối tượng nằm trong buf_

    void huy() noexcept {
        if (!p_) return;
        if (trong_) p_->~Base();                             // (6) chỉ hủy, KHÔNG delete
        else delete p_;
        p_ = nullptr;
        trong_ = false;
    }
    void lay(Function&& o) noexcept {                        // (7) chuyển ruột từ o sang *this (đang rỗng)
        if (!o.p_) return;
        if (o.trong_) {
            p_ = o.p_->diChuyen(buf_);
            trong_ = true;
            o.huy();
        } else {
            p_ = o.p_;
            o.p_ = nullptr;
        }
    }

public:
    Function() = default;
    template <typename F>
    Function(F f) {
        using G = Giu<F>;
        if constexpr (sizeof(G) <= N && alignof(G) <= alignof(std::max_align_t)    // (8)
                      && std::is_nothrow_move_constructible<F>::value) {
            p_ = new (buf_) G(std::move(f));
            trong_ = true;
        } else {
            p_ = new G(std::move(f));
        }
    }
    Function(const Function& o) {
        if (!o.p_) return;
        p_ = o.p_->nhanBan(o.trong_ ? buf_ : nullptr);
        trong_ = o.trong_;
    }
    Function(Function&& o) noexcept { lay(std::move(o)); }   // (9) quên noexcept là mất tiền (Thử thay đổi 2)
    Function& operator=(const Function& o) { return *this = Function(o); }   // (10) bản nháp rồi chuyển vào
    Function& operator=(Function&& o) noexcept {
        if (this != &o) {
            huy();
            lay(std::move(o));
        }
        return *this;
    }
    ~Function() { huy(); }
    explicit operator bool() const { return p_ != nullptr; }
    bool tuChua() const { return trong_; }                   // để test: đang nằm trong hộp không?
    R operator()(Args... args) const {
        if (!p_) throw std::bad_function_call();
        return p_->goi(std::forward<Args>(args)...);
    }
};

class Registry {                                             // Observer: danh sách hàm gọi lại
public:
    using Ham = Function<void(int)>;
    int dangKy(Ham h) {                                      // trả mã số để hủy sau
        ds_.push_back(Muc{++ma_, std::move(h)});
        return ma_;
    }
    bool huyDangKy(int ma) {
        for (auto it = ds_.begin(); it != ds_.end(); ++it)
            if (it->ma == ma) { ds_.erase(it); return true; }
        return false;
    }
    void phat(int sk) const {
        for (const Muc& m : ds_) m.ham(sk);                  // callback không được sửa registry này
    }
    std::size_t size() const { return ds_.size(); }

private:
    struct Muc { int ma; Ham ham; };
    std::vector<Muc> ds_;
    int ma_ = 0;
};

int main() {
    Registry rg;
    int tong = 0;
    std::string log;
    int ma1 = rg.dangKy([&tong](int sk) { tong += sk; });                  // (11) bắt 1 tham chiếu: nhỏ
    std::string ten = "cam bien";
    int ma2 = rg.dangKy([ten, &log](int sk) { log += ten + std::to_string(sk) + ";"; });   // (12) bắt chuỗi: lớn
    rg.phat(3);
    rg.phat(4);
    std::cout << "tong=" << tong << " log=" << log << "\n";
    rg.huyDangKy(ma2);
    rg.phat(5);
    std::cout << "sau huy: tong=" << tong << " size=" << rg.size() << "\n";
    (void)ma1;

    int k = 5;
    int mang[16] = {1};                                      // 64 byte
    int truoc = soLanNew;
    Function<int(int), 24> nho = [k](int x) { return x + k; };
    std::cout << "bat 1 int, N=24: " << soLanNew - truoc << " new, trong hop=" << nho.tuChua() << "\n";
    truoc = soLanNew;
    Function<int(int), 0> khongDem = [k](int x) { return x + k; };
    std::cout << "bat 1 int, N=0 : " << soLanNew - truoc << " new, trong hop=" << khongDem.tuChua() << "\n";
    truoc = soLanNew;
    Function<int(int), 24> lon = [mang](int x) { return x + mang[0]; };
    std::cout << "bat mang 64B, N=24: " << soLanNew - truoc << " new, trong hop=" << lon.tuChua() << "\n";
    truoc = soLanNew;
    std::function<int(int)> sf = [k](int x) { return x + k; };
    std::cout << "std::function bat 1 int: " << soLanNew - truoc << " new\n";
    truoc = soLanNew;
    std::function<int(int)> sf2 = [mang](int x) { return x + mang[0]; };
    std::cout << "std::function bat mang 64B: " << soLanNew - truoc << " new\n";

    truoc = soLanNew;
    Function<int(int), 24> sao = nho;                        // sao chép hàm nhỏ
    Function<int(int), 24> chuyen = std::move(nho);          // chuyển hàm nhỏ
    std::cout << "sao chep + chuyen (nho): " << soLanNew - truoc << " new\n";
    truoc = soLanNew;
    Function<int(int), 24> saoLon = lon;                     // sao chép hàm lớn
    Function<int(int), 24> chuyenLon = std::move(lon);       // chuyển hàm lớn
    std::cout << "sao chep + chuyen (lon): " << soLanNew - truoc << " new\n";
    std::cout << "ket qua: " << sao(1) << " " << chuyen(2) << " " << saoLon(3) << " " << chuyenLon(4)
              << ", nho sau chuyen: " << (nho ? "con" : "rong") << "\n";
    std::cout << "sizeof: N=24: " << sizeof(Function<int(int)>) << ", N=0: " << sizeof(Function<int(int), 0>)
              << ", std::function: " << sizeof(std::function<int(int)>) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `dangKy([&tong]...)` | Lambda bắt một tham chiếu (thường cỡ con trỏ, 8 byte): `Giu` ≈ 16 ≤ 24 nên (8) chọn nhánh trong hộp: placement new vào `buf_`, `trong_ = true`, **0 lần `new`** | `Ham.buf_: [vptr \| &tong]`, `p_ ──► buf_` |
| `dangKy([ten, &log]...)` | Lambda giữ `std::string` + tham chiếu (thường cỡ 40 byte): `Giu` lớn hơn 24 nên `new G` trên heap, `trong_ = false` | `p_ ──► heap [vptr \| ten \| &log]` |
| `push_back(Muc{...})` | Vector có thể tăng dung lượng: chuyển từng `Muc` bằng (9). Hộp **trong buf_** phải dựng lại ở chỗ mới: `lay` (7) gọi `diChuyen` (3), rồi hủy bản cũ; hộp **heap** chỉ đổi chủ con trỏ | con trỏ `p_` của hộp trong luôn trỏ vào `buf_` **của nó** |
| `phat(3)`, `phat(4)` | Gọi từng hộp qua `operator()` → `goi` ảo: `tong` = 7, `log` = `cam bien3;cam bien4;` | |
| `huyDangKy(ma2)`, `phat(5)` | `erase` bỏ mục 2; `~Function` → `huy()` thấy `trong_ = false` nên `delete`; `tong` = 12, còn 1 mục | |
| 5 dòng đo | `soLanNew` trước và sau mỗi lần tạo hộp: hiệu = số lần xin heap | `std::function` đo cùng cách |
| sao chép/chuyển | Hộp nhỏ: `nhanBan(buf_)` dựng vào buffer của hộp mới, 0 lần `new`. Hộp lớn: sao chép `new` 1 lần; chuyển chỉ đổi con trỏ | |

**Kết quả khi chạy** (g++ 11.4, libstdc++, x86-64; mọi đếm là số lần `operator new`):

```text
tong=7 log=cam bien3;cam bien4;
sau huy: tong=12 size=1
bat 1 int, N=24: 0 new, trong hop=1
bat 1 int, N=0 : 1 new, trong hop=0
bat mang 64B, N=24: 1 new, trong hop=0
std::function bat 1 int: 0 new
std::function bat mang 64B: 1 new
sao chep + chuyen (nho): 0 new
sao chep + chuyen (lon): 1 new
ket qua: 6 7 4 5, nho sau chuyen: rong
sizeof: N=24: 48, N=0: 32, std::function: 32
```

Mình chạy với `-fsanitize=address,undefined` (`-Wall -Wextra`) ở `-O0` và `-O2`: **sạch, thoát 0, đầu ra giống nhau**. Mình cũng chạy riêng một chương trình thử gán đủ kiểu (sao chép, chuyển, gán chính mình, gán lambda, gán hộp rỗng, hộp nhỏ lẫn hộp lớn) với cùng lớp: sạch ASan và UBSan.

**Thử thay đổi 1: `N = 0`** (dòng đo thứ hai trong chương trình): cùng lambda bắt một `int` mà `Function<int(int), 0>` tốn **1** lần `new` thay vì 0, vì không còn chỗ dựng sẵn; hộp nhỏ lại, `sizeof` 32 thay vì 48.

**Thử thay đổi 2: bỏ `noexcept` ở (9).** Mình dùng một chương trình riêng: cùng lớp `Registry`, đăng ký **bốn** lambda bắt một chuỗi dài, đếm `new`. Có `noexcept`: 11 lần. Bỏ `noexcept`: **17** lần. Chênh 6 vì `std::vector` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md), mục 8) chỉ *chuyển* phần tử khi tăng dung lượng nếu hàm tạo chuyển không ném; không thì **sao chép** (ba phần tử được chép qua hai lần tăng, mỗi lần một `Giu` mới và một bản chuỗi). Tức quên `noexcept` làm mọi lần vector lớn lên thành một đợt cấp phát.

### Bản SAI của đề 2: lambda bắt tham chiếu sống ngắn

Đoạn thay cho `main` (còn lại giữ nguyên): callback bắt `[&dem]` với `dem` là biến cục bộ của hàm đăng ký.

```cpp
// bo-qua-kiem-tra
void lapDangKy(Registry& rg) {
    int dem = 0;
    rg.dangKy([&dem](int sk) { dem += sk; std::cout << "dem=" << dem << "\n"; });
}                                       // dem chết ở đây, lambda vẫn cầm tham chiếu

int main() {
    Registry rg;
    lapDangKy(rg);
    rg.phat(1);                         // gọi callback: đọc, rồi ghi vào chỗ đã chết
}
```

Cú pháp đúng, biên dịch **không một cảnh báo**. Không sanitizer: in một số rác (mình thấy `dem=32766` ở `-O0` và `dem=24204` ở `-O2`, **đổi theo lần biên dịch**) và thoát mã 0, nên dễ lọt qua tay. ASan: báo `stack-buffer-underflow` (READ of size 4) ở thân lambda; bật thêm `ASAN_OPTIONS=detect_stack_use_after_return=1` thì báo đúng tên `stack-use-after-return`, chỉ ra biến `dem` trong khung của `lapDangKy`. Chuẩn: hành vi không xác định; tên báo cáo của ASan tùy cờ, đừng học thuộc. Sửa: bắt theo giá trị (`[dem]` với `mutable`) nếu cần đếm riêng, hoặc để biến sống lâu hơn registry, hoặc để chủ gọi `huyDangKy(ma)` trước khi biến chết.

### Chi phí gom lại, `std::function` thật và `std::any`

Số đo gom lại (g++ 11.4, libstdc++, x86-64; xem kết quả ở trên): bản đề 1 luôn 1 lần `new` (hộp 8 byte); bản đề 2 với `N = 24` là 0 lần cho lambda bắt một `int` và 1 lần cho mảng 64 byte (hộp 48 byte); `std::function` thật là 0 và 1 lần (hộp 32 byte).

Cái giá của SBO: hộp **to hơn** (48 so với 8 byte: 24 byte đệm + 8 con trỏ + 1 cờ = 33, làm tròn lên bội của 16 vì mảng đệm căn lề 16, như padding ở [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)), mỗi lời sao chép/chuyển phải qua hàm ảo thay vì chép một con trỏ, và hộp có điều kiện ngầm (`noexcept` khi chuyển). Mình **không đo thời gian**: số lần cấp phát đã đủ để lý luận, thời gian đổi theo máy và `-O`.

**Lược bớt so với `std::function` thật:** (1) hàm tạo không bị ràng buộc theo kiểu (thấy ở "Thử thay đổi"); (2) không hỗ trợ con trỏ hàm thành viên (`&Lop::ham`) vì ta gọi bằng `f(...)` chứ không `std::invoke`; (3) không có `target<T>()`, `target_type()`, `swap`, so sánh với `nullptr`; (4) hàm tạo nhận `F` theo giá trị thay vì `F&&` kèm `decay_t`; (5) gán `nullptr` cho `Function` là lỗi biên dịch (mình thử: `expression cannot be used as a function`); (6) không hỗ trợ lambda chỉ-chuyển (thư viện thật cũng không, đến `std::move_only_function` C++23).

**`std::any` cùng ý tưởng.** `std::any` (C++17, `<any>`) cũng xóa kiểu (cách cài bên trong tùy thư viện), nhưng nó **không có `operator()`**: nó chỉ cất một giá trị sao chép được, lấy ra bằng `std::any_cast<T>` với đúng `T`. Mình thử trên g++ 11.4 (ASan, UBSan sạch): `std::any a = 42;` rồi `any_cast<int>(a)` ra 42, `any_cast<double>(a)` ném `bad_any_cast`; `sizeof(std::any)` là 16. Gói gọn: `Function` = xóa kiểu **kèm phép gọi**, `any` = xóa kiểu **chỉ cất và trả lại**.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Type erasure là gì, và `Function<int(int)>` làm thế nào chứa được cả lambda lẫn hàm thường?"
    Là quên kiểu cụ thể, chỉ giữ lại giao diện "gọi được, sao chép được, hủy được". `Base` ảo là giao diện; `Giu<F>` là lớp mẫu **nhớ** `F` và làm ba việc cho đúng `F`; vỏ ngoài chỉ giữ `Base*`. Nhờ vậy mọi `F` cùng chữ ký ra cùng **một** kiểu `Function<int(int)>`.
    **Nối tiếp: "Mỗi lời gọi tốn gì?"** Một lời gọi gián tiếp qua hàm ảo, và trình biên dịch không inline xuyên qua hộp được. Với đa số việc chẳng đáng kể; trong vòng lặp nóng thì nên nhận template `F` thay vì `Function`.

??? question "`std::function` có cấp phát heap không? Làm sao tránh?"
    Tùy thứ nó chứa và tùy thư viện: chuẩn không nêu ngưỡng. Mình đo trên g++ 11.4: lambda bắt một `int` 0 lần `new`, lambda bắt mảng 64 byte 1 lần. Muốn tránh: giữ sẵn `buf_` trong hộp và dựng `Giu<F>` vào đó bằng placement new khi vừa chỗ (đề 2).
    **Nối tiếp: "SBO có cái giá gì?"** Hộp to hơn (bản của mình 48 byte so với 8), sao chép và chuyển phải qua hàm ảo (hộp có con trỏ trỏ vào chính nó nên không chép thô byte được), và `F` không được ném khi chuyển, kẻo hộp mất `noexcept`. Quên `noexcept` ở hàm tạo chuyển còn khiến `vector` sao chép phần tử mỗi lần lớn lên (mình đếm 11 → 17 lần `new`).

??? question "Sao chép `Function` là sao chép nông hay sâu? Sao không để hai hộp dùng chung một thiết bị cho rẻ?"
    Sâu: `nhanBan` chép luôn thứ trong hộp, như `std::function`. Mình chạy cùng lambda đếm `mutable` ở cả hai: sau hai lần gọi, sao chép, rồi gọi xen kẽ cho `3 3 4 4`. Để hai hộp dùng chung (bọc `shared_ptr`) thì lambda có trạng thái sẽ **đếm chung một dãy**, bất ngờ cho người dùng.
    **Nối tiếp: "Sao chép nông thì hỏng gì?"** Hai hộp cùng `delete` một `Giu` (mình chạy: ASan `heap-use-after-free` ở hàm hủy, không sanitizer thì mã 139).

??? question "Observer dùng `Function`: callback bắt `[&]` hoặc `[this]` thì nguy hiểm thế nào?"
    Hộp cất callback **lâu hơn** nơi tạo ra nó, nên mọi tham chiếu/con trỏ nó bắt phải sống ít nhất bằng registry, nếu không là tham chiếu treo (mình chạy: ASan báo `stack-buffer-underflow` hoặc `stack-use-after-return`, không sanitizer thì in số rác). Cách chữa: bắt theo giá trị; hoặc người đăng ký giữ mã số và `huyDangKy(ma)` trong hàm hủy của mình; hoặc bắt `weak_ptr`, như ở [Bài 73](../nhom-9-thuc-chien-da-luong/73-event-bus.md).
    **Nối tiếp: "Callback tự `huyDangKy` giữa lúc `phat` thì sao?"** Bản `Registry` ở đây duyệt thẳng `ds_` nên `erase` làm iterator hỏng ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)); muốn cho phép thì phát trên bản chụp danh sách, như đã làm với [Bài 73](../nhom-9-thuc-chien-da-luong/73-event-bus.md), và nhớ rằng sao chép danh sách `Function` lớn là một đợt cấp phát.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên `virtual` ở hàm hủy của `Base`"
    Dễ quên vì chương trình vẫn chạy (mình chạy: thoát 0, chỉ rò rỉ im lặng). Dấu hiệu nên nhớ: g++ `-Wall` cảnh báo `-Wdelete-non-virtual-dtor`, ASan báo `new-delete-type-mismatch`. Trên bảng trắng, viết `virtual ~Base() = default;` **trước** mọi thứ khác.

!!! warning "Lỗi 2: Hàm sao chép tự sinh hay sao chép nông"
    `Function` giữ con trỏ sở hữu nên cần Rule of 5 ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)): sao chép sâu qua `nhanBan`, chuyển đặt nguồn về `nullptr`, hủy `delete`. Đừng quên `noexcept` ở hàm tạo chuyển.

!!! warning "Lỗi 3: Bắt `[&]` hoặc `[this]` cho callback cất lâu"
    Lambda trông vô hại và biên dịch sạch, nhưng cầm tham chiếu tới thứ có thể chết trước registry. Khi nói: nêu luôn cách chữa (bắt giá trị, hủy đăng ký bằng mã số, `weak_ptr`).

!!! warning "Lỗi 4 (khi nói): hứa sai về chi phí"
    Đừng nói "`std::function` luôn cấp phát heap" (lambda nhỏ thường không) hay "type erasure chậm vì dùng `virtual`" (chỉ thêm một lời gọi gián tiếp và mất inline). Cũng đừng nói "SBO miễn phí": hộp to hơn và chuyển phải qua hàm ảo.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="82" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** `Function` của bài (sao chép sâu). Đoạn sau in gì?

```text
int n = 0;
Function<int()> a = [n]() mutable { return ++n; };
a();
Function<int()> b = a;
std::cout << a() << b();
```

- `23`, vì `b` dùng chung biến `n` với `a` nên đếm tiếp
- `22`, vì hai hộp độc lập và cùng có `n = 1` lúc sao chép
- `21`, vì `b` chép lambda từ lúc tạo nên bắt đầu từ `n = 0`
- `11`, vì lambda `mutable` luôn chạy trên bản chép mới của `n`

<p class="giai-thich" markdown>Lời gọi `a()` đầu đưa `n` của `a` lên 1. `b = a` gọi `nhanBan`, chép cả lambda **kèm `n = 1`** sang hộp mới. Sau đó `a()` ra 2 và `b()` ra 2 độc lập. Kết quả `23` chỉ có nếu hai hộp dùng chung trạng thái (như khi bọc bằng `shared_ptr`), còn sao chép của `Function` là sâu. Nói `b` bắt đầu từ 0 quên rằng lambda được chép **lúc đang có trạng thái**, không phải lúc tạo. `mutable` không tạo bản mới mỗi lần gọi: nó chỉ cho sửa bản đang nằm trong lambda.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đoạn sau chạy thì xảy ra gì?

```text
struct Base { ~Base() = default; virtual int goi() = 0; };
template <class F> struct Giu : Base { F f; int goi() override { return f(); } };
Base* p = new Giu<Lambda>{...};    // Lambda bắt một std::string dài
delete p;
```

- Hàm hủy của `Giu` vẫn chạy, vì `goi` là hàm ảo nên cả bảng hàm ảo được dùng
- Chạy bình thường, vì `= default` làm trình biên dịch tự thêm `virtual` cho nó
- Lỗi biên dịch, vì lớp có hàm ảo bắt buộc phải khai báo hàm hủy ảo
- Hành vi không xác định: `~Giu` không chạy nên chuỗi bị rò rỉ

<p class="giai-thich" markdown>`delete p` qua `Base*` mà hàm hủy không ảo là hành vi không xác định; thực tế `~Giu` không chạy nên chuỗi trong lambda không bị giải phóng (mình chạy: LeakSanitizer báo rò, ASan báo `new-delete-type-mismatch`). Việc `goi` là hàm ảo không kéo hàm hủy theo: mỗi hàm ảo tự có chỗ trong bảng, hàm hủy phải được khai báo `virtual` riêng. `= default` không thêm `virtual`. Còn trình biên dịch không coi đây là lỗi: nó chỉ cảnh báo, nên chương trình vẫn biên dịch.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Trên x86-64 với g++, bản đề 2 có `N = 24`. Đoạn sau cấp phát heap mấy lần cho riêng việc dựng `f` (với `a`, `b`, `c` là `long long`)?

```text
Function<int(int), 24> f = [a, b, c](int x) { return x + a + b + c; };
```

- 1 lần: cộng `vptr` 8 byte thì thành 32, hơn 24
- 0 lần: ba biến bắt đúng 24 byte nên vừa vặn chỗ dựng sẵn
- 3 lần: mỗi biến bắt được cấp phát riêng lẻ một khối trên heap
- 0 lần: lambda bắt theo giá trị nên chẳng bao giờ cần dùng đến heap

<p class="giai-thich" markdown>Thứ phải nằm vừa `buf_` là cả `Giu<F>`, không chỉ `F`: nó có thêm con trỏ bảng hàm ảo (thường 8 byte trên máy 64-bit). 8 + 24 = 32 lớn hơn 24 nên rơi vào nhánh `new`: đúng 1 lần. Nói 0 lần là quên `vptr`. Mỗi biến bắt nằm liền trong một khối `Giu` duy nhất, không ai cấp phát riêng từng biến. Bắt theo giá trị hay tham chiếu không quyết định chỗ ở: chỉ có **kích thước** của hộp con quyết định.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Vì sao `Giu<F>` là lớp mẫu còn vỏ `Function` chỉ giữ một `Base*`?

- Để trình biên dịch sinh một bản `Function` riêng cho từng lambda, gọi nhanh hơn
- Vì lớp mẫu không thể có hàm ảo nên phải tách ra một lớp cơ sở khác
- Để `Function<int(int)>` luôn là một kiểu duy nhất dù chứa lambda hay hàm
- Vì `Base*` cho phép bỏ qua việc sao chép thứ bên trong khi sao chép hộp

<p class="giai-thich" markdown>Template ở `Giu<F>` để **nhớ** `F` và làm ba việc đúng cho nó; `Base*` ở vỏ để **quên** `F` khi ra ngoài, nên mọi `F` cùng chữ ký cho ra một kiểu duy nhất. Sinh bản `Function` riêng cho từng lambda là điều ngược lại, vì khi đó chúng không còn là một kiểu. Lớp mẫu có hàm ảo được (chính `Giu` có `goi` ảo), nên lý do tách không phải ở đó. Và sao chép vẫn phải chép thiết bị: `nhanBan` ảo lo việc ấy, không bị bỏ qua.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** `Widget` đăng ký `[this](int sk) { capNhat(sk); }` vào một `Registry` sống lâu hơn nó. `Widget` bị hủy mà không ai gỡ callback. Cách chữa đúng nhất?

- Không cần chữa gì: `Function` sao chép lambda nên `this` luôn còn sống
- Giữ mã số `dangKy` trả về, gọi `huyDangKy(ma)` trong hàm hủy `Widget`
- Đổi `[this]` thành `[&]` để tham chiếu tự cập nhật theo `Widget`
- Đặt `N = 0` để lambda nằm trên heap nên không phụ thuộc `Widget`

<p class="giai-thich" markdown>Registry giữ một bản của lambda, nhưng bản đó chỉ chứa **con trỏ** `this`, không chứa `Widget`: `Widget` chết thì con trỏ treo. Cách chữa là chấm dứt đăng ký trước khi `Widget` chết, hoặc bắt `weak_ptr`. `[&]` không giúp gì: nó cũng chỉ cầm tham chiếu, và còn dễ tệ hơn nếu bắt cả biến cục bộ. `N` chỉ đổi **chỗ nằm** của lambda (trong hộp hay trên heap), không đổi việc nó trỏ tới `Widget` đã chết.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Hàm `sapXep(v, tieuChi)` chạy `tieuChi` hàng triệu lần trong vòng lặp nóng, chỉ dùng bên trong hàm và không cất lại. Chữ ký nào hợp nhất?

- Tham số `Function<bool(int, int)>`, vì dùng chung một kiểu cho mọi tiêu chí
- Tham số `std::function`, vì template làm phình mã nhị phân quá nhiều
- Con trỏ hàm `bool (*)(int, int)`, vì lambda không truyền vào hàm được
- Tham số template `F`, vì gọi thẳng, inline được, không cấp phát

<p class="giai-thich" markdown>Không cất thì không cần xóa kiểu: tham số template `F` giữ nguyên kiểu thật nên trình biên dịch gọi thẳng và có thể inline, không hàm ảo, không cấp phát. Hộp `Function`/`std::function` đáng giá khi phải cất lâu hoặc để nhiều loại chung một kiểu, ở đây là trả giá vô ích. Phình mã là có thật nhưng nhỏ so với việc mất inline ở vòng lặp nóng. Lambda không bắt đổi được thành con trỏ hàm, còn lambda có bắt thì không, nên con trỏ hàm cũng không tổng quát.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Ở bản đề 2, bạn quên `noexcept` ở hàm tạo chuyển của `Function`. `Registry` giữ `std::vector<Muc>` với `Muc { int ma; Function<void(int)> ham; }`. Khi vector tăng dung lượng thì sao?

```text
Function(Function&& o) { lay(std::move(o)); }    // quên noexcept
```

- Nó sao chép từng `Muc` sang chỗ mới, tốn thêm cấp phát cho mỗi hộp lớn
- Vẫn chuyển như cũ, vì `noexcept` chỉ là chú thích cho người đọc
- Không biên dịch được, vì vector đòi mọi phần tử có hàm chuyển `noexcept`
- Vẫn chuyển, nhưng vector bọc mỗi lần chuyển trong `try` nên chậm hơn

<p class="giai-thich" markdown>`std::vector` chỉ chuyển phần tử khi tăng dung lượng nếu hàm tạo chuyển không ném (để giữ được bảo đảm "hỏng giữa chừng thì dữ liệu cũ còn nguyên"); không thì nó **sao chép** (mình đếm: bốn lambda lớn từ 11 lên 17 lần `new`). `noexcept` không chỉ là chú thích: nó đổi hành vi của thư viện. Chương trình vẫn biên dịch, vì vector chấp nhận cả hai trường hợp. Và không có `try` nào được thêm quanh mỗi lần chuyển.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** `std::any` và `Function` giống và khác nhau thế nào?

- `std::any` cũng có `operator()` nên thay được `Function` mỗi khi chữ ký khớp
- `std::any` không xóa kiểu: nó chỉ lưu `void*` kèm kích thước nên không cần hàm ảo
- Cùng ý xóa kiểu, nhưng `any` chỉ cất rồi trả; lấy ra phải `any_cast<T>` đúng `T`
- `std::any` chỉ chứa được kiểu số và chuỗi vì cần biết kích thước ngay khi biên dịch

<p class="giai-thich" markdown>Cả hai xóa kiểu nên chứa được nhiều loại trong cùng một kiểu. Khác ở chỗ `Function` biết **phép gọi** (một chữ ký cố định), còn `any` chỉ cất giá trị: muốn dùng phải `any_cast<T>` đúng kiểu, sai thì ném `bad_any_cast` (mình chạy `any_cast<double>` trên một `any` chứa `int`). `any` không có `operator()`, nên không thay được `Function`. Và nó không chỉ chứa số hay chuỗi: kiểu nào sao chép được cũng vào được, vì kích thước thật được nhớ trong phần xóa kiểu bên trong, không cần biết lúc biên dịch.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Type erasure = template để nhớ kiểu + hàm ảo để quên kiểu:** `Base` khai ba việc (gọi, nhân bản, hủy), `Giu<F>` làm chúng cho đúng `F`, vỏ `Function` chỉ giữ `Base*`; nên mọi thứ cùng chữ ký là **một** kiểu (`R(Args...)` tách bằng chuyên biệt hóa từng phần, `Args...` mở gói, `std::forward` giữ tham chiếu). Mình chạy sạch `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`, ở `-O0` và `-O2`.
2. **Phải đủ Rule of 5, bằng sao chép sâu qua `nhanBan` ảo:** quên `virtual` ở hàm hủy thì UB (mình chạy: ASan `new-delete-type-mismatch`, bản `Dem` không bị hủy, LeakSanitizer báo rò); sao chép nông thì hai hộp cùng `delete` (ASan `heap-use-after-free`, không sanitizer mã 139). `std::function` cũng sao chép sâu (mình chạy: `3 3 4 4` ở cả hai).
3. **Chi phí là số lần cấp phát, không phải lời gọi ảo:** bản đề 1 luôn 1 lần `new`; `std::function` trên g++ 11.4 là 0 lần với lambda bắt một `int`, 1 lần với mảng 64 byte. Small buffer (placement new vào `buf_`, hủy `p_->~Base()`, hộp tự trỏ vào mình nên chuyển phải qua hàm ảo) đưa lambda nhỏ về 0 lần, trả giá hộp to hơn (48 so với 8 byte) và điều kiện `noexcept`.
4. **Registry/Observer trên `Function`:** callback sống lâu hơn nơi tạo nên `[&]`/`[this]` là bẫy (mình chạy: ASan `stack-buffer-underflow` hoặc `stack-use-after-return`, không sanitizer in số rác, thoát 0); chữa bằng bắt giá trị, `huyDangKy(ma)` trong hàm hủy của chủ, hay `weak_ptr`. Quên `noexcept` ở hàm tạo chuyển làm `vector` sao chép (mình đếm 11 → 17 lần `new`).
5. **Khi nào chọn gì:** chỉ gọi tại chỗ, không cất, đường nóng → tham số template `F`; cất lâu, nhiều loại → `std::function`; nhiều thao tác/trạng thái → giao diện ảo; hàm thuần không bắt → con trỏ hàm; chỉ-chuyển → `move_only_function` (C++23). Trong code thật dùng `std::function`; `std::any` cùng ý xóa kiểu nhưng không có phép gọi, lấy ra phải `any_cast<T>` đúng kiểu.
