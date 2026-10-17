# Bài 78 — Live-coding: tự cài shared_ptr và weak_ptr

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một `SharedPtr<T>` có **khối điều khiển** (đếm mạnh): hàm tạo, sao chép, gán, chuyển, hủy, `use_count`, và test bằng đối tượng đếm hàm hủy (sạch ASan/UBSan).
    - Thêm `WeakPtr<T>` với **đếm yếu** và `lock()` bằng vòng `compare_exchange`, nói đúng thứ tự: đối tượng bị hủy khi đếm mạnh = 0, khối điều khiển bị hủy khi **cả hai** đếm = 0; phá được vòng tham chiếu bằng `WeakPtr`.
    - Giải thích và chạy thật vì sao đếm phải **nguyên tử** (bản `long` thường chạy nhiều luồng thì TSan báo race, có lúc sập), và vì sao lần giảm đếm dùng `acq_rel` còn lần tăng dùng `relaxed`.
    - Nói rõ bản mình viết lược bớt gì so với `std::shared_ptr` thật: bộ xóa, aliasing, `make_shared` gộp một cấp phát, `enable_shared_from_this`.

**Bạn cần biết trước:** [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, khối điều khiển, `weak_ptr`, `lock()`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`operator*`, `operator->`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (sao chép, gán, chuyển, `noexcept`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template <typename T>`), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (`explicit`, `friend`), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic`, `fetch_add`, `compare_exchange`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, TSan), [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md) (ASan). [Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md) đã dạy `acquire`/`release`/`acq_rel`; bài này nhắc lại đủ dùng tại chỗ.

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đẩy cây bút cho bạn: "Giả sử thư viện chuẩn không có `shared_ptr`. Em lên bảng viết cho anh một cái, có `weak_ptr` luôn. Anh sẽ test bằng một đối tượng đếm xem hàm hủy chạy đúng một lần không."

Đây là **xưởng tự lắp đồ** của Nhóm 10: Bài 10 cho bạn dùng một chiếc máy, hôm nay bạn **tháo máy ra** xem từng bánh răng. Bánh răng chính là tấm **bảng đếm treo ở cửa tủ** của Bài 10: nó là **khối điều khiển**, một vùng heap nhỏ mà mọi thẻ mở tủ cùng nhìn. Người nhìn qua cửa kính (`weak_ptr`) cũng cần đọc tấm bảng đó, nên bảng phải sống lâu hơn cái tủ.

Phép ví von hết đúng ở chỗ: bảng đếm thật không tự dọn; chính **người trả thẻ cuối cùng** phải tự tay dọn tủ, rồi (khi cả người nhìn cũng đi hết) dọn luôn cái bảng. Phần khó của bài là đúng chỗ đó: ai dọn, dọn cái nào trước, và nếu hai người trả thẻ cùng lúc ở hai luồng thì sao.

!!! info "Bạn biết Go?"
    Go có GC nên bạn không bao giờ tự đếm tham chiếu. Nếu có viết tay (ví dụ đếm số người dùng một tài nguyên), bạn dùng `atomic.Int32.Add(-1)` và kiểm `== 0`. Ở C++ `fetch_sub(1)` trả giá trị **cũ**, nên điều kiện "mình là người cuối" là `== 1`, không phải `== 0`.

## 📖 Giải thích

### Đề 1: `SharedPtr<T>` với khối điều khiển (đếm mạnh)

**Người phỏng vấn nói:** "Viết `SharedPtr<T>`. Sao chép thì nhiều chủ cùng giữ một đối tượng, chủ cuối cùng đi thì đối tượng bị `delete` đúng một lần. Cần: hàm tạo từ con trỏ thô, sao chép, gán, chuyển, hàm hủy, `use_count()`, `get()`, `*`, `->`, `if (p)`, `reset()`. Chưa cần đa luồng. Test bằng một lớp mà hàm hủy tăng một biến đếm."

??? tip "Gợi ý 1"
    Mỗi bản sao phải biết "có bao nhiêu người đang giữ" và các bản sao phải thấy **cùng một con số**. Con số đó không thể là thành viên của `SharedPtr` (mỗi bản một số riêng), cũng không nên là biến toàn cục (mọi đối tượng chung một số). Vậy nó nằm ở đâu?

??? tip "Gợi ý 2"
    Con số nằm trong một vùng `new` riêng (khối điều khiển). Mỗi `SharedPtr` giữ **hai** con trỏ: tới đối tượng và tới khối. Sao chép thì đếm +1; hủy thì đếm −1, về 0 thì `delete` cả đối tượng lẫn khối. Chuyển thì đếm **không đổi**, chỉ đổi chủ của hai con trỏ.

??? tip "Gợi ý 3"
    Phép gán: dựng một **bản sao tạm trước** (đếm +1), hoán đổi ruột bản tạm với `*this`, rồi để bản tạm chết mang thẻ cũ đi. Làm vậy không cần kiểm tra tự gán. Hàm tạo từ con trỏ thô nên là `explicit`.

**Phân tích hướng giải.** Trên bảng bạn vẽ trước, viết sau:

```text
a = { ptr_ --> Cay{cao = 5},  kd_ --> KhoiDem{manh = 2} }     (hai chỗ ở heap, tách biệt)
b = { ptr_ --> Cay{cao = 5},  kd_ --> KhoiDem{manh = 2} }     (trỏ đúng hai chỗ như a)
```

Bốn điều bạn nên nói to trước khi viết: (1) đối tượng và khối điều khiển là **hai** vùng heap riêng; (2) đếm ở trong khối, không ở trong `SharedPtr`; (3) thứ tự khi về 0: hủy đối tượng rồi mới trả khối; (4) mọi thao tác "trả thẻ" đi qua **một** hàm `buong()` để không viết sai ở nhiều nơi.

**Cú pháp mới dùng trong bài, giải thích tại chỗ:**

- `explicit operator bool() const` là hàm cho phép `if (p)` và `!p`. `explicit` (như ở Bài 31) chặn chuyển ngầm: `int x = p;` bị lỗi biên dịch (mục "Thử thay đổi" bên dưới đã chạy).
- `std::swap(x, y)` (trong `<utility>`) hoán đổi giá trị của hai biến cùng kiểu; ở đây hoán đổi hai con trỏ.
- `friend class WeakPtr<T>;` (Bài 31) cho `WeakPtr` đụng vào phần `private` của `SharedPtr`; nhờ vậy hàm tạo hai tham số `private` chỉ `lock()` gọi được.
- `throw;` (không kèm giá trị, ở đề 2) ném lại đúng ngoại lệ đang bắt trong `catch`.
- `template <typename T> class WeakPtr;` đứng riêng là **khai báo trước**: báo cho trình biên dịch "có lớp này, định nghĩa sau", để lớp khác nhắc tới tên nó.

**Bốn bước xây dần** (mỗi bước giữ được một bất biến):

| Bước | Thêm gì | Bất biến giữ |
|---|---|---|
| 1 | Hai thành viên `ptr_`, `kd_`; hàm tạo `explicit SharedPtr(T*)` lập khối đếm = 1; hàm hủy gọi `buong()` | Mỗi đối tượng thô có đúng một khối |
| 2 | Hàm tạo sao chép: chép hai con trỏ, `++manh` | Đếm = số `SharedPtr` đang trỏ |
| 3 | Hàm tạo chuyển: lấy hai con trỏ, đặt nguồn về `nullptr` | Chuyển không đổi đếm |
| 4 | `operator=(SharedPtr o)` nhận **theo giá trị** rồi `swap` | Tự gán, gán chuyển, gán sao chép cùng một đường, an toàn |

Bước 4 là chỗ hay hỏng. Tham số `o` được dựng bằng hàm tạo sao chép (gán từ biến) hoặc hàm tạo chuyển (gán từ `std::move(x)`), nên **một** hàm phục vụ cả hai kiểu gán. Hết hàm, `o` (đang giữ thẻ cũ của `*this`) chết và tự trả thẻ đó.

```cpp
// bo-qua-kiem-tra (mảnh của bản đầy đủ, chưa đủ để biên dịch riêng)
SharedPtr& operator=(SharedPtr o) noexcept {   // o: bản sao đã +1 đếm TRƯỚC khi vào hàm
    swap(o);                                   // *this nhận thẻ mới, o cầm thẻ cũ
    return *this;
}                                              // o chết: trả thẻ cũ, có thể là lần trả cuối
```

## 💻 Ví dụ code

### Đề 1: bản đầy đủ

```cpp
#include <iostream>
#include <utility>

struct KhoiDem {                  // (1) khối điều khiển: mới có một bộ đếm
    long manh = 1;
};

template <typename T>
class SharedPtr {
public:
    SharedPtr() = default;                                       // (2) rỗng
    explicit SharedPtr(T* p) : ptr_(p), kd_(new KhoiDem) {}      // (3) nhận hàng, lập khối đếm = 1
    SharedPtr(const SharedPtr& o) : ptr_(o.ptr_), kd_(o.kd_) {   // (4) sao chép: thêm một người giữ
        if (kd_) ++kd_->manh;
    }
    SharedPtr(SharedPtr&& o) noexcept : ptr_(o.ptr_), kd_(o.kd_) {  // (5) chuyển: đếm không đổi
        o.ptr_ = nullptr; o.kd_ = nullptr;
    }
    SharedPtr& operator=(SharedPtr o) noexcept { swap(o); return *this; }  // (6) copy-and-swap
    ~SharedPtr() { buong(); }                                    // (7)

    void swap(SharedPtr& o) noexcept { std::swap(ptr_, o.ptr_); std::swap(kd_, o.kd_); }
    void reset() { SharedPtr().swap(*this); }
    long use_count() const { return kd_ ? kd_->manh : 0; }
    T* get() const { return ptr_; }
    T& operator*() const { return *ptr_; }
    T* operator->() const { return ptr_; }
    explicit operator bool() const { return ptr_ != nullptr; }

private:
    void buong() {                                               // (8) trả một thẻ
        if (kd_ && --kd_->manh == 0) {
            delete ptr_;                                         // (9) hủy đối tượng trước
            delete kd_;                                          // (10) rồi mới hủy khối đếm
        }
    }
    T* ptr_ = nullptr;
    KhoiDem* kd_ = nullptr;
};

int soHuy = 0;

struct Cay {
    int cao;
    explicit Cay(int c) : cao(c) {}
    ~Cay() {
        ++soHuy;
        std::cout << "huy cay " << cao << "\n";
    }
};

int main() {
    SharedPtr<Cay> a(new Cay(5));                                // (11)
    std::cout << "a: dem = " << a.use_count() << ", cao = " << a->cao << "\n";
    {
        SharedPtr<Cay> b = a;                                    // (12)
        SharedPtr<Cay> c(new Cay(7));
        std::cout << "sau b = a, c moi: dem(a) = " << a.use_count()
                  << ", dem(c) = " << c.use_count() << "\n";
        c = a;                                                   // (13)
        std::cout << "sau c = a: dem(a) = " << a.use_count() << "\n";
    }                                                            // (14)
    std::cout << "ra khoi khoi: dem(a) = " << a.use_count() << "\n";
    SharedPtr<Cay> d = std::move(a);                             // (15)
    std::cout << "sau move: a " << (a ? "con" : "rong") << ", dem(d) = " << d.use_count() << "\n";
    SharedPtr<Cay>& r = d;
    d = r;                                                       // (16) tự gán
    std::cout << "sau tu gan: dem(d) = " << d.use_count() << ", cao = " << (*d).cao << "\n";
    d.reset();                                                   // (17)
    std::cout << "sau reset: d " << (d ? "con" : "rong") << ", soHuy = " << soHuy << "\n";
    return 0;
}
```

Biên dịch và chạy mình dùng: `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined -g -o d1 d1.cpp && ./d1`. Kết quả sạch (không báo gì, mã thoát 0), ở cả `-O0` lẫn `-O2`.

**Chạy từng dòng** (cột bộ nhớ ghi đếm của khối; "Cay5" là đối tượng cao 5)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (11) | `new Cay(5)` xin heap, hàm tạo `SharedPtr(T*)` (3) lập `KhoiDem` đếm 1. In `a: dem = 1, cao = 5` | `a` giữ Cay5, khối `manh = 1` |
| (12) | `b = a` gọi hàm tạo sao chép (4): `b` trỏ cùng hai nơi, `++manh`. `c` là cây 7 với khối riêng. In `dem(a) = 2, dem(c) = 1` | Cay5: `manh = 2`; Cay7: `manh = 1` |
| (13) | `c = a`: tham số `o` là bản sao của `a` (Cay5 thành 3), `swap` đổi ruột nên `c` giữ Cay5 còn `o` giữ Cay7. `o` chết ở cuối hàm: Cay7 về 0, `delete ptr_` in `huy cay 7`, rồi `delete kd_`. Sau đó in `dem(a) = 3` | Cay5: `manh = 3`; Cay7 và khối của nó đã trả |
| (14) | Hết khối: `c` chết (3 xuống 2), rồi `b` chết (2 xuống 1; biến khai báo sau chết trước). In `dem(a) = 1` | Cay5: `manh = 1` |
| (15) | `std::move(a)` gọi hàm tạo chuyển (5): `d` lấy hai con trỏ, `a` về rỗng, đếm vẫn 1. In `a rong, dem(d) = 1` | `d` giữ Cay5; `a` là `nullptr` |
| (16) | `d = r` với `r` là tên khác của `d`: tạo bản sao tạm (đếm 2), `swap` (không đổi gì thật), tạm chết (đếm 1). Không hỏng, in `dem(d) = 1, cao = 5` | Cay5: `manh = 1` |
| (17) | `reset()` hoán đổi `d` với một `SharedPtr` rỗng tạm; tạm giữ Cay5 rồi chết: về 0, `delete` in `huy cay 5` và trả khối. In `d rong, soHuy = 2` | cả hai cây và hai khối đã trả |

**Kết quả khi chạy:**

```text
a: dem = 1, cao = 5
sau b = a, c moi: dem(a) = 2, dem(c) = 1
huy cay 7
sau c = a: dem(a) = 3
ra khoi khoi: dem(a) = 1
sau move: a rong, dem(d) = 1
sau tu gan: dem(d) = 1, cao = 5
huy cay 5
sau reset: d rong, soHuy = 2
```

Mỗi cây có đúng một dòng `huy`, đúng lúc người giữ cuối trả thẻ (cây 7 ở (13), cây 5 ở (17)), và `soHuy = 2` khớp hai lần `new Cay`. Đó là test mà người phỏng vấn muốn thấy.

**Thử thay đổi: bỏ `explicit` ở `operator bool`.** Mình thêm dòng `int x = a;` vào `main`. Có `explicit` thì lỗi biên dịch: `error: cannot convert ‘SharedPtr<Cay>’ to ‘int’ in initialization`. Bỏ `explicit` thì biên dịch êm và `x` thành `1` (con trỏ "bị hiểu" thành số): đó là lý do `std::shared_ptr` cũng viết `explicit operator bool`.

### Bản SAI 1: gán "trả thẻ cũ trước"

Người mới hay viết phép gán theo thứ tự "bỏ cái cũ, rồi nhận cái mới":

```cpp
// bo-qua-kiem-tra (bản sai: thay cho operator= trong bản đầy đủ; mình đã chạy)
SharedPtr& operator=(const SharedPtr& o) {
    buong();                    // trả thẻ cũ trước
    ptr_ = o.ptr_;
    kd_ = o.kd_;
    if (kd_) ++kd_->manh;       // đọc o.kd_ ... nhưng o có thể chính là *this
    return *this;
}
```

Mình thay đúng hàm này vào bản đầy đủ rồi chạy với ASan. Mọi thứ vẫn êm cho tới dòng (16) `d = r`: lúc đó `d` là người giữ **duy nhất**, `buong()` đưa đếm về 0 và `delete` cả đối tượng lẫn khối, rồi `++kd_->manh` đụng khối đã trả. ASan báo `heap-use-after-free ... READ of size 8 ... in SharedPtr<Cay>::operator=`, kèm `freed by thread T0 here: ... SharedPtr<Cay>::buong()` gọi từ chính `operator=`. Sửa: dựng bản sao **trước** (tham số theo giá trị).

### Bản SAI 2: đếm không nguyên tử, chạy nhiều luồng

Bản đề 1 dùng `long manh` thường. Đề bài chưa nói gì về luồng, nhưng người phỏng vấn sẽ hỏi: "chạy ở bốn luồng thì sao?" Mình đã thử đúng điều đó:

```cpp
// bo-qua-kiem-tra (bản sai: dùng SharedPtr của đề 1 với long thường; mình đã chạy)
SharedPtr<Cay> sp(new Cay);
std::vector<std::thread> luong;
for (int i = 0; i < 4; ++i) {
    luong.emplace_back([&sp] {
        for (int k = 0; k < 100000; ++k) { SharedPtr<Cay> ban = sp; }   // sao chép rồi hủy
    });
}
for (std::thread& t : luong) t.join();
std::cout << "use_count = " << sp.use_count() << " (mong 1)\n";
```

Kết quả đổi theo lần chạy và theo máy. Với `-O0`, 10 lần chạy không lần nào ra 1: có lần sập với thông báo của glibc như `free(): unaligned chunk detected in tcache 2` hay `double free or corruption`, có lần in `use_count = 8819` rồi `soHuy = 0` (đối tượng không bao giờ bị hủy). Với `-O2`, ba lần chạy đầu **đều ra đúng 1**: lỗi vẫn còn, chỉ là chưa thấy. TSan thì không bỏ sót:

```text
WARNING: ThreadSanitizer: data race
  Read of size 8 at 0x7b0400000010 by thread T2:
    #0 SharedPtr<Cay>::SharedPtr(SharedPtr<Cay> const&) ...
  Previous write of size 8 at 0x7b0400000010 by thread T1:
    #0 SharedPtr<Cay>::SharedPtr(SharedPtr<Cay> const&) ...
```

Dưới TSan mình còn thấy `use_count = -10974` và `soHuy = 76436`: đếm trượt qua 0 nhiều lần nên đối tượng bị hủy hàng chục nghìn lần. Nguyên nhân: `++manh` là ba bước (đọc, cộng, ghi) như `++dem` của Bài 25, nên hai luồng cùng đọc một giá trị cũ và mất một lần cộng. Đề 2 sửa bằng `std::atomic`.

### Đề 2: `WeakPtr<T>`, đếm yếu và đếm nguyên tử

**Người phỏng vấn nói:** "Bây giờ thêm `WeakPtr<T>`: dựng từ `SharedPtr`, `expired()`, `use_count()`, và `lock()` trả `SharedPtr` (rỗng nếu đối tượng đã hủy). Hai đếm phải an toàn khi nhiều luồng sao chép, hủy và gọi `lock()` đồng thời. Anh muốn thấy: đối tượng bị hủy khi đếm mạnh về 0, khối điều khiển bị hủy khi cả hai đếm về 0, vòng tham chiếu phá được bằng `WeakPtr`, và test nhiều luồng sạch TSan."

??? tip "Gợi ý 1"
    Có hai việc hủy với hai điều kiện khác nhau: hủy **đối tượng** khi không còn `SharedPtr`; hủy **khối điều khiển** khi không còn `SharedPtr` lẫn `WeakPtr`. `WeakPtr` còn phải đọc khối sau khi đối tượng đã chết (để biết "đã chết"), nên khối không thể bị trả cùng lúc với đối tượng.

??? tip "Gợi ý 2"
    Đếm yếu bắt đầu ở **1**, không phải 0: một "phần yếu" đại diện cho **cả nhóm** `SharedPtr`. Nhóm này trả phần đó **sau khi** hủy đối tượng. Mỗi `WeakPtr` thêm +1; khối bị hủy khi đếm yếu về 0. Đổi hai đếm thành `std::atomic<long>`.

??? tip "Gợi ý 3"
    `lock()` không được viết "đếm > 0 thì cộng 1" thành hai bước, vì giữa hai bước luồng khác có thể đưa đếm về 0 và hủy đối tượng. Dùng `compare_exchange_weak` trong vòng lặp: chỉ tăng nếu đếm vẫn khác 0. Lần giảm đếm mạnh: `fetch_sub(1, acq_rel)` rồi so giá trị **cũ** với 1.

**Phân tích hướng giải.** Câu hỏi khó nhất là "vì sao đếm yếu bắt đầu ở 1". Thử cách ngây thơ: đếm yếu bắt đầu ở 0, `SharedPtr` cuối cùng trừ đếm mạnh về 0 rồi kiểm "đếm yếu có bằng 0 không", còn `WeakPtr` cuối cùng trừ đếm yếu về 0 rồi kiểm "đếm mạnh có bằng 0 không".

Nếu hai lần trừ xảy ra gần như cùng lúc ở hai luồng, mỗi bên đều thấy đếm của bên kia là 0 và **cả hai cùng `delete` khối**: double free. Với "đại diện +1", mỗi bên chỉ có **một** phép trừ nguyên tử trên đếm của mình, và ai trừ về 0 thì người đó trả khối, không cần kiểm gì thêm.

Lưu ý: [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) nói "đếm yếu là số `weak_ptr`" cho dễ hiểu; con số **lưu** trong khối là số đó cộng 1 khi còn `SharedPtr` giữ đối tượng, nên `soWeak()` ở dưới trừ 1.

Thứ tự trong `buong()`: hủy đối tượng **trước**, buông phần yếu **sau**. Đó là thứ tự của bản thật, vì ở đó cách xóa nằm trong chính khối nên khối phải còn sống trong lúc hủy. Ở bản lược bớt này `delete ptr_` không đọc khối; mình thử đổi hai dòng (11) và (10) cho nhau thì ASan, UBSan và TSan vẫn sạch, nên đừng nói "đổi thứ tự là hỏng"; hãy nói "giữ thứ tự để khớp bản thật và để thêm bộ xóa sau này khỏi sửa". Lỗi thật là **trả khối cùng lúc với đối tượng** (Bản SAI 3).

Về `memory_order`, ba quyết định trong code, mỗi cái kèm lý do:

| Chỗ | Mức | Vì sao |
|---|---|---|
| Tăng đếm (sao chép `SharedPtr`, `WeakPtr`) | `relaxed` | Người sao chép **đã có** một thẻ nên đối tượng chắc chắn còn; chỉ cần phép cộng không bị chia cắt, không cần công bố dữ liệu nào |
| Giảm đếm mạnh | `acq_rel` | Phần **release**: mọi lần đọc/ghi đối tượng của luồng này xảy ra-trước lần trừ. Phần **acquire**: luồng trừ về 0 thấy mọi thứ các luồng trước đã làm với đối tượng, rồi mới chạy hàm hủy |
| `lock()` (CAS) | mặc định `seq_cst` | Mạnh hơn cần thiết nhưng đúng và dễ chứng minh; có thể hạ khi bạn chắc |

**Cái này là đúng chuẩn, cái này là lựa chọn của mình.** Chuẩn C++ không ghi tên `memory_order` nào cho bộ đếm của `shared_ptr`; chuẩn chỉ yêu cầu kết quả quan sát được: copy và hủy các bản khác nhau từ nhiều luồng không gây race, đối tượng bị hủy khi `use_count()` về 0 (dù còn `weak_ptr`), `lock()` trên đối tượng đã hủy trả rỗng. Cặp `relaxed` khi tăng và `acq_rel` khi giảm là cách các thư viện thực tế làm để đạt kết quả đó (theo mình biết, không khẳng định từng dòng của libstdc++). Đếm yếu có "+1 đại diện" cũng là cách cài đặt phổ biến, không phải điều chuẩn bắt buộc.

### Đề 2: bản đầy đủ

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <utility>
#include <vector>

struct KhoiDieuKhien {
    std::atomic<long> manh{1};    // (1) số SharedPtr đang giữ đối tượng
    std::atomic<long> yeu{1};     // (2) số WeakPtr, cộng 1 đại diện cho cả nhóm SharedPtr
};

void buongYeu(KhoiDieuKhien* kd) {                                    // (3)
    if (kd->yeu.fetch_sub(1, std::memory_order_acq_rel) == 1) {
        delete kd;                                                    // (4) cả hai đếm đã về 0
    }
}

template <typename T>
class WeakPtr;                                                        // (5) khai báo trước

template <typename T>
class SharedPtr {
public:
    SharedPtr() = default;
    explicit SharedPtr(T* p) : ptr_(p) {
        try {
            kd_ = new KhoiDieuKhien;
        } catch (...) {
            delete p;                                                 // (6) xin khối đếm hỏng thì không để rò p
            throw;
        }
    }
    SharedPtr(const SharedPtr& o) : ptr_(o.ptr_), kd_(o.kd_) {
        if (kd_) kd_->manh.fetch_add(1, std::memory_order_relaxed);   // (7) tăng: relaxed là đủ
    }
    SharedPtr(SharedPtr&& o) noexcept : ptr_(o.ptr_), kd_(o.kd_) {
        o.ptr_ = nullptr; o.kd_ = nullptr;
    }
    SharedPtr& operator=(SharedPtr o) noexcept { swap(o); return *this; }
    ~SharedPtr() { buong(); }

    void swap(SharedPtr& o) noexcept { std::swap(ptr_, o.ptr_); std::swap(kd_, o.kd_); }
    void reset() { SharedPtr().swap(*this); }
    long use_count() const { return kd_ ? kd_->manh.load() : 0; }
    long soWeak() const { return kd_ ? kd_->yeu.load() - 1 : 0; }     // không có trong chuẩn, để dạy
    T* get() const { return ptr_; }
    T& operator*() const { return *ptr_; }
    T* operator->() const { return ptr_; }
    explicit operator bool() const { return ptr_ != nullptr; }

private:
    friend class WeakPtr<T>;
    SharedPtr(T* p, KhoiDieuKhien* kd) : ptr_(p), kd_(kd) {}          // (8) dùng cho lock(); đếm đã tăng sẵn

    void buong() {
        if (kd_ && kd_->manh.fetch_sub(1, std::memory_order_acq_rel) == 1) {  // (9) giảm: acq_rel
            delete ptr_;                                              // (10) hủy đối tượng trước
            buongYeu(kd_);                                            // (11) rồi trả phần yếu của nhóm
        }
    }
    T* ptr_ = nullptr;
    KhoiDieuKhien* kd_ = nullptr;
};

template <typename T>
class WeakPtr {
public:
    WeakPtr() = default;
    WeakPtr(const SharedPtr<T>& s) : ptr_(s.ptr_), kd_(s.kd_) {       // (12) cố ý không explicit, như bản chuẩn
        if (kd_) kd_->yeu.fetch_add(1, std::memory_order_relaxed);
    }
    WeakPtr(const WeakPtr& o) : ptr_(o.ptr_), kd_(o.kd_) {
        if (kd_) kd_->yeu.fetch_add(1, std::memory_order_relaxed);
    }
    WeakPtr& operator=(WeakPtr o) noexcept {
        std::swap(ptr_, o.ptr_); std::swap(kd_, o.kd_); return *this;
    }
    ~WeakPtr() { if (kd_) buongYeu(kd_); }

    long use_count() const { return kd_ ? kd_->manh.load() : 0; }
    bool expired() const { return use_count() == 0; }
    SharedPtr<T> lock() const {                                       // (13)
        if (!kd_) return SharedPtr<T>();
        long m = kd_->manh.load();
        while (m != 0) {
            if (kd_->manh.compare_exchange_weak(m, m + 1)) {          // (14) chỉ tăng nếu còn khác 0
                return SharedPtr<T>(ptr_, kd_);
            }
        }
        return SharedPtr<T>();                                        // (15) đã về 0: rỗng
    }

private:
    T* ptr_ = nullptr;
    KhoiDieuKhien* kd_ = nullptr;
};

int soHuy = 0;

struct Cay {
    int cao = 42;
    ~Cay() {
        cao = -1;                  // ghi bình thường: thử xem acq_rel có bảo vệ không
        ++soHuy;
    }
};

struct Nut {
    int id;
    SharedPtr<Nut> tiep;           // giữ mạnh
    WeakPtr<Nut> truoc;            // chỉ nhìn
    explicit Nut(int i) : id(i) {}
    ~Nut() { std::cout << "huy nut " << id << "\n"; }
};

int main() {
    // 1) đếm mạnh, đếm yếu, lock, expired
    SharedPtr<Cay> a(new Cay);
    WeakPtr<Cay> w = a;
    std::cout << "dem = " << a.use_count() << ", weak = " << a.soWeak()
              << ", expired = " << w.expired() << "\n";
    {
        SharedPtr<Cay> t = w.lock();
        std::cout << "lock: " << (t ? "duoc" : "rong") << ", dem = " << a.use_count() << "\n";
    }
    a.reset();
    std::cout << "sau reset: soHuy = " << soHuy << ", expired = " << w.expired()
              << ", lock " << (w.lock() ? "duoc" : "rong") << "\n";

    // 2) vòng tham chiếu đã phá: truoc là WeakPtr
    {
        SharedPtr<Nut> n1(new Nut(1));
        SharedPtr<Nut> n2(new Nut(2));
        n1->tiep = n2;
        n2->truoc = n1;
        std::cout << "dem(n1) = " << n1.use_count() << ", dem(n2) = " << n2.use_count() << "\n";
    }
    std::cout << "het khoi nut\n";

    // 3) nhiều luồng sao chép và hủy, lock() chạy đua với lần hủy cuối
    soHuy = 0;
    SharedPtr<Cay> sp(new Cay);
    WeakPtr<Cay> yeu = sp;
    std::vector<std::thread> luong;
    std::vector<int> loi(4, 0);
    for (int i = 0; i < 4; ++i) {
        luong.emplace_back([sp, yeu, &loi, i] {
            for (int k = 0; k < 20000; ++k) {
                SharedPtr<Cay> ban = sp;
                if (ban->cao != 42) ++loi[i];
                SharedPtr<Cay> khoa = yeu.lock();
                if (khoa && khoa->cao != 42) ++loi[i];
            }
        });
    }
    sp.reset();
    for (std::thread& t : luong) t.join();
    int tongLoi = 0;
    for (int x : loi) tongLoi += x;
    std::cout << "luong xong: soHuy = " << soHuy << ", loi = " << tongLoi
              << ", expired = " << yeu.expired() << "\n";
    return 0;
}
```

Mình biên dịch và chạy ba cách, đều sạch: (a) `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined -g -pthread` ở `-O0` và `-O2`; (b) `g++ -std=c++17 -Wall -Wextra -g -fsanitize=thread -pthread` rồi chạy dưới `setarch x86_64 -R` (như Bài 25), 10/10 lần không có cảnh báo ở `-O0` và 10/10 ở `-O2`; (c) biên dịch thường, chạy ra đúng đầu ra bên dưới.

**Chạy từng dòng** (theo ba mục trong `main`; "mạnh" và "yếu" là hai đếm trong khối)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| mục 1: `a`, `w = a` | Khối mới: mạnh 1, yếu 1 (phần đại diện). `WeakPtr(const SharedPtr&)` (12) cộng yếu: 2. `soWeak()` in yếu − 1 nên `weak = 1`. In `dem = 1, weak = 1, expired = 0` | mạnh 1, yếu 2 |
| mục 1: `w.lock()` | (13) đọc mạnh = 1 khác 0, CAS (14) đổi 1 thành 2 (nếu luồng khác đổi đếm trước, `m` được nạp lại giá trị mới và vòng lặp thử tiếp), rồi trả `SharedPtr` bằng hàm tạo riêng (8). In `lock: duoc, dem = 2`. `t` chết: mạnh về 1 | mạnh 1, yếu 2 |
| mục 1: `a.reset()` | `buong()` (9): `fetch_sub` trả 1, tức mình là người cuối. `delete ptr_` (10) chạy `~Cay` (`soHuy = 1`), rồi `buongYeu` (11) đưa yếu 2 về 1: **khối chưa bị trả**, vì `w` còn nhìn | mạnh 0, yếu 1 |
| mục 1: `expired`, `lock` | `use_count()` đọc mạnh = 0 nên `expired()` đúng; `lock()` thấy `m == 0`, bỏ qua vòng lặp, trả rỗng (15). Đối tượng **không bao giờ hồi sinh** | mạnh 0, yếu 1 |
| mục 2: `n1`, `n2` | `n1->tiep = n2` làm mạnh của `n2` thành 2; `n2->truoc = n1` chỉ cộng **yếu** của `n1`. In `dem(n1) = 1, dem(n2) = 2` | `n1`: mạnh 1; `n2`: mạnh 2 |
| mục 2: hết khối | `n2` chết trước (khai báo sau): mạnh 2 về 1, chưa hủy. `n1` chết: mạnh về 0, `~Nut` in `huy nut 1`, rồi thành viên `tiep` chết, mạnh của `n2` về 0, in `huy nut 2` | cả hai khối trả khi yếu về 0 |
| mục 3: bốn luồng | Mỗi lambda mang bản sao `sp` và `yeu`. Mỗi vòng: sao chép (tăng `relaxed`), đọc `cao`, `lock()`, rồi hủy hai bản (giảm `acq_rel`). Luồng chính `sp.reset()` trong lúc đó | mạnh lên xuống, không đoán trước |
| mục 3: `join` | Luồng nào trừ về 0 là luồng hủy `Cay` (**không xác định luồng nào**), nó ghi `cao = -1` và `++soHuy`. Mọi lần đọc `cao` trước đó đã xảy ra-trước nhờ `acq_rel`. In `soHuy = 1, loi = 0, expired = 1` | mạnh 0 |

**Kết quả khi chạy:**

```text
dem = 1, weak = 1, expired = 0
lock: duoc, dem = 2
sau reset: soHuy = 1, expired = 1, lock rong
dem(n1) = 1, dem(n2) = 2
huy nut 1
huy nut 2
het khoi nut
luong xong: soHuy = 1, loi = 0, expired = 1
```

Chỉ có những thứ tất định mới được in: `soHuy` sau `join`, tổng `loi`, `expired`. Ai là luồng hủy cuối, hay `use_count()` giữa lúc các luồng đang chạy, thì chuẩn không hứa gì và mình không in.

**Thử thay đổi: đặt đếm yếu bắt đầu ở 0** (`std::atomic<long> yeu{0};`). Mình đã chạy: ASan báo `heap-use-after-free` ở `std::__atomic_base<long>::load` gọi từ `WeakPtr<Cay>::expired()` trong `main`. Lý do: `a.reset()` làm `buongYeu` trừ từ 1 (chỉ còn `w`) về 0 và trả khối, trong khi `w` vẫn sắp đọc nó. "+1 đại diện" chính là thứ giữ khối sống đến khi cả nhóm mạnh lẫn nhóm yếu đã đi.

### Bản SAI 3: hủy khối điều khiển cùng lúc với đối tượng

Cách "tự nhiên" từ đề 1 là `delete ptr_; delete kd_;`. Mình đổi dòng (11) thành `delete kd_;`, chạy ASan:

```cpp
// bo-qua-kiem-tra (bản sai: thay dòng buongYeu(kd_) trong buong(); mình đã chạy)
if (kd_ && kd_->manh.fetch_sub(1, std::memory_order_acq_rel) == 1) {
    delete ptr_;
    delete kd_;                 // sai: còn WeakPtr cần đọc khối này
}
```

Kết quả: `ERROR: AddressSanitizer: heap-use-after-free ... READ of size 8`, ngăn xếp `WeakPtr<Cay>::use_count() <- expired() <- main`, và "freed by" chỉ vào `SharedPtr<Cay>::buong()` gọi từ `reset()`. Đây đúng là chỗ khác nhau giữa "đối tượng chết" và "khối chết".

### Bản SAI 4: vòng tham chiếu, hai chiều đều mạnh

Đổi `WeakPtr<Nut> truoc;` thành `SharedPtr<Nut> truoc;` (mình đã chạy):

```text
dem(n1) = 2, dem(n2) = 2
het khoi nut
```

Không có dòng `huy nut` nào: ra khỏi khối, mỗi `Nut` vẫn còn một thẻ do nút kia giữ. ASan (LeakSanitizer) báo `ERROR: LeakSanitizer: detected memory leaks` và `SUMMARY: AddressSanitizer: 112 byte(s) leaked in 4 allocation(s)` (hai `Nut` và hai khối), chương trình thoát mã 1. Bản đúng chỉ khác một chữ, và in `huy nut 1`, `huy nut 2`.

### Bản SAI 5: giảm đếm bằng `relaxed`

Đổi `acq_rel` ở dòng (9) thành `relaxed`. Điều đáng học: test bốn luồng của đề 2 **không** bắt được lỗi này, TSan vẫn im. Lý do mình tìm ra: lambda ở đó mang cả `WeakPtr`, và lần trừ `acq_rel` của đếm yếu chạy **trước** lần trả `SharedPtr` trong cùng closure, nên vô tình nối cầu (bỏ `yeu` khỏi danh sách bắt và giữ `relaxed` thì TSan báo race 5/5 lần). TSan im không chứng minh đúng; cần một test **xác định**: luồng phụ chỉ đọc rồi trả thẻ, luồng chính trả thẻ sau cùng.

```cpp
// bo-qua-kiem-tra (bản sai: dòng (9) dùng relaxed; mình đã chạy với TSan)
SharedPtr<Cay> sp(new Cay);
std::thread t([sp] { if (sp->cao != 42) std::cout << "sai\n"; });   // luồng phụ đọc cao
std::this_thread::sleep_for(std::chrono::milliseconds(200));        // đảm bảo nó đã trả thẻ
sp.reset();                                   // luồng chính trả thẻ cuối, ~Cay ghi cao = -1
t.join();
```

TSan báo `WARNING: ThreadSanitizer: data race`, `Write of size 4 ... Cay::~Cay() ... by main thread` và `Previous read of size 4 ... by thread T1`, cả hai trỏ vào cùng đối tượng `Cay`. Đổi lại `acq_rel`, cùng chương trình in `soHuy = 1` và TSan sạch. Ý nghĩa: không có phần release ở lần trừ của luồng phụ thì lần đọc `cao` của nó **không xảy ra-trước** hàm hủy ở luồng chính, tức là data race trên chính đối tượng.

### Bản này lược bớt gì so với `std::shared_ptr` thật

| Thứ | Bản của mình | `std::shared_ptr` thật |
|---|---|---|
| Bộ xóa (deleter) | `delete ptr_` cố định | Nhớ cách xóa lúc dựng (xóa kiểu), nhận hàm tùy ý |
| Kiểu lúc dựng | `SharedPtr<Base>(new Derived)` mà `Base` không có hàm hủy ảo thì `delete` qua `Base*`: không xác định | Nhớ `Derived` lúc dựng nên xóa đúng |
| Aliasing | không có | Hàm tạo aliasing: trỏ vào thành viên nhưng giữ khối của chủ |
| `make_shared` | `SharedPtr<Cay> a(new Cay)` cần 2 lần `new` (đối tượng, khối), mình đếm thật bằng `operator new` thay thế | Thường gộp đối tượng và khối trong **một** lần cấp phát (mình đếm thật: 1 lần) |
| `enable_shared_from_this` | không có | Có, qua một `weak_ptr` ngầm trong đối tượng |
| Còn lại | không có chuyển giữa kiểu liên quan, mảng, so sánh, `weak_ptr` chuyển | Có đầy đủ |

Trên máy mình, `sizeof(SharedPtr<Cay>)` và `sizeof(std::shared_ptr<Cay>)` đều 16 byte (hai con trỏ). Nhánh `catch (...)` ở dòng (6) mình đã thử bằng `operator new` thay thế ném `std::bad_alloc` đúng một lần: `delete p` chạy và ngoại lệ đi tiếp; thiếu nhánh này đối tượng thô bị rò.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Vì sao bộ đếm phải nguyên tử? Vậy `shared_ptr` là thread-safe à?"
    `++manh` trên `long` là đọc, cộng, ghi nên hai luồng cùng sao chép sẽ mất cập nhật: đếm sai, đối tượng bị hủy sớm hoặc không bao giờ (mình chạy: sập, hoặc `use_count` lệch, TSan báo race). Nguyên tử sửa **chỉ phần bộ đếm**. Đối tượng được trỏ tới và việc nhiều luồng cùng sửa **một** biến `shared_ptr` vẫn không an toàn ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)).

    **Nối tiếp: "Em dùng `memory_order` nào cho tăng và giảm, vì sao?"** Tăng dùng `relaxed`: người sao chép đã có thẻ nên không cần công bố gì. Giảm dùng `acq_rel`: release để việc dùng đối tượng của luồng này không bị dời ra sau lần trừ, acquire để luồng trừ về 0 thấy hết rồi mới chạy hàm hủy. `seq_cst` mặc định cũng đúng, chỉ chặt hơn cần thiết.

??? question "Đếm yếu để làm gì, và khi nào hủy đối tượng, khi nào hủy khối điều khiển?"
    Đếm mạnh quyết định đời của **đối tượng**: về 0 thì chạy hàm hủy, dù còn `WeakPtr`. Đếm yếu (cộng 1 đại diện cho nhóm `SharedPtr`) quyết định đời của **khối điều khiển**: về 0 thì trả khối, vì `WeakPtr` còn phải đọc khối để biết đối tượng đã chết chưa. Trong `buong()`, hàm hủy đối tượng chạy trước, rồi nhóm mạnh buông phần yếu của mình.

    **Nối tiếp: "`lock()` viết thế nào cho an toàn đa luồng?"** Vòng `compare_exchange_weak` chỉ tăng đếm mạnh khi nó đang khác 0. Viết "if (đếm > 0) ++đếm" là hai bước: giữa chúng luồng khác có thể đưa đếm về 0 và hủy đối tượng, rồi ta "hồi sinh" một đối tượng đã chết.

??? question "Bản em viết khác `std::shared_ptr` thật ở những điểm nào?"
    Nói bốn điểm: bộ xóa tùy chỉnh (thật nhớ kiểu và cách xóa lúc dựng, nên `shared_ptr<Base>(new Derived)` xóa đúng ngay cả khi `Base` không có hàm hủy ảo, còn bản em thì không), hàm tạo aliasing, `make_shared` gộp đối tượng và khối thành một lần cấp phát (bản em cần hai lần `new`), và `enable_shared_from_this`. Thêm: thật còn hỗ trợ mảng, chuyển giữa kiểu liên quan, so sánh. Đây là điều nên **tự nói ra** trước khi bị hỏi.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: phép gán trả thẻ cũ trước khi nhận thẻ mới"
    Với `a = a` khi `a` là người giữ duy nhất, bạn xóa chính thứ sắp chép (Bản SAI 1: ASan báo heap-use-after-free). Dựng bản sao trước, `swap`, để bản tạm chết.

!!! warning "Lỗi 2: nói \"đếm nguyên tử là xong, thread-safe\""
    Nguyên tử chỉ bảo vệ **bộ đếm**. Khi nói trên bảng, tách ba tầng: bộ đếm, đối tượng, biến `SharedPtr`. Và đừng quên `lock()`: nó cần CAS, không phải "load rồi cộng".

!!! warning "Lỗi 3: hủy khối điều khiển cùng lúc với đối tượng"
    Khi còn `WeakPtr`, khối phải sống tiếp. Hủy đối tượng khi đếm mạnh về 0, hủy khối khi **cả hai** về 0 (Bản SAI 3).

!!! warning "Lỗi 4: dựng hai `SharedPtr` từ cùng một con trỏ thô"
    `SharedPtr<Cay> x(raw); SharedPtr<Cay> y(raw);` tạo hai khối riêng nên `raw` bị `delete` hai lần (giống `std::shared_ptr`). Muốn thêm người giữ thì **sao chép** một `SharedPtr` có sẵn.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="78" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau (dùng `SharedPtr` và `WeakPtr` của bài). Cuối đoạn, `c.use_count()` và `c.soWeak()` (số `WeakPtr` đang nhìn) là bao nhiêu?

```text
SharedPtr<int> a(new int(1));
SharedPtr<int> b = a;
WeakPtr<int> w = b;
SharedPtr<int> c = std::move(b);
a.reset();
```

- `2` và `1`: `std::move(b)` chỉ sao chép thẻ nên `b` vẫn còn giữ
- `1` và `0`: `w` bị hủy khi `b` chuyển sang `c`
- `1` và `1`: thẻ của `b` sang `c`, `a` đã trả, `w` vẫn nhìn
- `3` và `1`: `a`, `b` và `c` mỗi bên giữ một thẻ riêng

<p class="giai-thich" markdown>Đếm từng bước: `a` là 1; `b = a` làm 2; `w` chỉ tăng đếm yếu; `std::move(b)` chuyển thẻ từ `b` sang `c` nên vẫn 2 và `b` thành rỗng; `a.reset()` về 1. Còn đúng một `WeakPtr` nên `soWeak()` là 1. Kết quả `2` và `1` sai vì hàm tạo chuyển lấy cả hai con trỏ rồi đặt nguồn về `nullptr`, không cộng đếm. Kết quả `1` và `0` sai vì `b` chuyển đi không hủy `w`. Kết quả `3` và `1` quên rằng `b` đã rỗng sau khi chuyển.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc phép gán sau. `buong()` giảm đếm mạnh, về 0 thì `delete` đối tượng và khối. Chuyện gì xảy ra với `a = a;` khi `a` đang là người giữ duy nhất?

```text
SharedPtr& operator=(const SharedPtr& o) {
    buong();
    ptr_ = o.ptr_;
    kd_ = o.kd_;
    if (kd_) ++kd_->manh;
    return *this;
}
```

- Use-after-free: `buong()` trả khối, rồi `++kd_->manh` ghi vào khối đã trả
- Không sao: `++kd_->manh` đưa đếm từ 0 lên 1 nên đối tượng vẫn sống như cũ
- Rò rỉ: đếm lên 2 rồi chỉ giảm một lần nên không bao giờ về 0
- Lỗi biên dịch: `o` là `const` mà hàm ghi vào `kd_` của nó

<p class="giai-thich" markdown>Vì `o` chính là `*this`, lệnh `buong()` đưa đếm 1 về 0 và `delete` cả đối tượng lẫn khối; các dòng sau đọc và ghi vào khối đã trả. Mình đã chạy: ASan báo `heap-use-after-free`. Đáp án "đưa đếm lên 1 nên vẫn sống" sai vì vùng nhớ đã bị trả, cộng thêm vào đó không hồi sinh được gì. Đáp án rò rỉ mô tả sai thứ tự: lần giảm đã xảy ra trước. Đáp án lỗi biên dịch sai vì ghi vào `kd_` là ghi vào thành viên của `*this`, còn `o` chỉ bị đọc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau (`Cay` in `huy cay` ở hàm hủy). Hàm hủy `Cay` chạy khi nào và khối điều khiển được trả khi nào?

```text
SharedPtr<Cay> a(new Cay);
{
    WeakPtr<Cay> w = a;
    a.reset();                // (1)
    std::cout << "x\n";
}                             // (2)
```

- `x` in trước, rồi `huy cay` ở (2) khi `w` chết, vì `WeakPtr` giữ đối tượng sống tới lúc đó
- `huy cay` ở (1), và khối điều khiển cũng được trả ngay ở (1) cùng với đối tượng
- `huy cay` ở (2), vì đối tượng chỉ được hủy khi cả đếm mạnh lẫn đếm yếu về 0
- `huy cay` rồi `x`, rồi khối điều khiển được trả ở (2) khi `w` chết

<p class="giai-thich" markdown>Ở (1) đếm mạnh về 0 nên hàm hủy chạy ngay, trước dòng in `x`, dù `w` còn đó. Khối điều khiển còn một `WeakPtr` đọc nó nên chỉ được trả ở (2), khi đếm yếu về 0. Lựa chọn "`x` in trước, rồi `huy cay` ở (2)" coi `WeakPtr` như `SharedPtr` giữ sống. Lựa chọn trả khối ở (1) là lỗi của bản SAI 3 (use-after-free khi `w` đọc khối). Lựa chọn "cả hai đếm" gộp sai hai điều kiện: đối tượng chỉ cần đếm mạnh về 0, còn khối mới cần cả hai.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Vì sao lần `fetch_sub` giảm đếm mạnh dùng `memory_order_acq_rel` chứ không phải `relaxed`?

- Để phép trừ không bị chia cắt, vì `relaxed` không bảo đảm tính nguyên tử
- Để việc dùng đối tượng ở luồng khác xảy ra-trước hàm hủy ở luồng trừ về 0
- Để các luồng luôn hủy đối tượng theo cùng một thứ tự giữa các lần chạy
- Để `use_count()` luôn đọc được đúng số người giữ ở mọi lúc

<p class="giai-thich" markdown>Release ở lần trừ của luồng khác và acquire ở lần trừ về 0 nối hai bên bằng quan hệ xảy ra-trước, nên hàm hủy không đua với lần dùng đối tượng trước đó; mình đã chạy: đổi sang `relaxed` thì TSan báo data race giữa `~Cay` và lần đọc của luồng phụ. Tính nguyên tử có ở cả `relaxed`, nên lý do "không bị chia cắt" sai. `acq_rel` không ép thứ tự hủy giữa các lần chạy: luồng nào về 0 vẫn tùy lịch của hệ điều hành. `use_count()` đa luồng chỉ là ước lượng, không mức `memory_order` nào đổi điều đó.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Vì sao `lock()` dùng vòng `compare_exchange_weak` thay vì `if (manh.load() > 0) manh.fetch_add(1);`?

- Vì `fetch_add` không dùng được trên `std::atomic<long>`
- Vì một lần `compare_exchange` luôn nhanh hơn một lần `fetch_add`
- Vì `lock()` cần chờ đến khi có `SharedPtr` mới được tạo ra
- Vì giữa kiểm và tăng, luồng khác có thể đưa đếm về 0 và hủy đối tượng

<p class="giai-thich" markdown>Kiểm rồi tăng là hai bước nguyên tử riêng lẻ chứ không phải một nguyên tử: luồng khác chen vào đưa đếm về 0 và hủy đối tượng, rồi ta tăng đếm của một đối tượng đã chết và trả `SharedPtr` trỏ vào vùng đã trả. `compare_exchange_weak(m, m + 1)` chỉ tăng nếu đếm vẫn bằng giá trị `m` vừa đọc, còn không thì nạp lại `m` và thử tiếp. `fetch_add` dùng được bình thường trên `std::atomic<long>`, nên lý do "không dùng được" sai. Không có chuyện CAS luôn nhanh hơn (nó có thể phải lặp), và `lock()` không chờ ai: đếm bằng 0 thì trả rỗng ngay.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Người phỏng vấn hỏi: "`SharedPtr<Base> p(new Derived);` mà `Base` không có hàm hủy ảo. Bản em viết và `std::shared_ptr` thật khác nhau thế nào?"

- Bản tự cài xóa qua `Base*` nên không xác định; bản thật nhớ `Derived` nên đúng
- Cả hai đều không xác định, vì không bao giờ được xóa `Derived` qua `Base`
- Cả hai đều đúng, vì khối điều khiển luôn biết kiểu thật của đối tượng
- Bản tự cài đúng; bản thật mới không xác định vì nó dùng bộ xóa

<p class="giai-thich" markdown>Bản của bài lưu `T* ptr_` với `T = Base` và `delete ptr_` nên xóa qua `Base*` khi `Base` không có hàm hủy ảo: hành vi không xác định. `std::shared_ptr` xóa kiểu: hàm tạo nhớ kiểu thật `Derived` (và bộ xóa) lúc dựng nên xóa đúng. Đáp án nói cả hai đều không xác định bỏ qua cơ chế đó. Khối điều khiển của bản tự cài không biết kiểu nào cả, nên đáp án "luôn biết" sai. Và bản thật dùng bộ xóa chính là lý do nó đúng, không phải lý do nó sai.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Đọc mô tả test sau, chạy bản đề 1 (đếm là `long` thường). Sau `join`, `use_count()` in ra gì?

```text
SharedPtr<Cay> sp(new Cay);
bốn luồng, mỗi luồng 100000 lần: SharedPtr<Cay> ban = sp;
join cả bốn; in sp.use_count()
```

- Luôn `1`: mỗi lần cộng đều có một lần trừ đi kèm nên tổng cân bằng
- Không xác định: có thể khác `1`, có thể sập, và TSan báo data race
- Luôn `1`, vì hàm tạo sao chép chỉ đọc `kd_` mà đọc thì không gây race
- Luôn khác `1` nhưng chương trình không sập, vì mất cập nhật chỉ làm đếm sai

<p class="giai-thich" markdown>Hai luồng cùng đọc, cộng, ghi `manh` thì mất một lần cập nhật nên cộng trừ không còn cân bằng; có khi đếm trượt qua 0 và đối tượng bị hủy sớm rồi lại bị hủy tiếp (double free). Mình chạy 10 lần ở `-O0`, không lần nào ra `1` (sập hoặc in `use_count` cỡ nghìn), và TSan báo `data race`. Đáp án "luôn 1" nhầm kỳ vọng với bảo đảm. Hàm tạo sao chép không chỉ đọc mà còn **ghi** `manh`. Đáp án "không sập" sai vì đếm sai kéo theo hủy sai, và mình đã thấy sập.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `SharedPtr<T>` giữ hai con trỏ (đối tượng và khối điều khiển) và mọi thao tác "trả thẻ" đi qua một hàm `buong()`; sao chép cộng đếm, chuyển không đổi đếm, gán viết bằng tham số theo giá trị cộng `swap` (copy-and-swap) nên tự gán an toàn, còn phép gán "trả trước, nhận sau" bị ASan báo use-after-free.
2. Thứ tự đúng: đối tượng bị hủy ngay khi đếm mạnh về 0 (dù còn `WeakPtr`), khối điều khiển bị hủy khi **cả hai** đếm về 0; đếm yếu bắt đầu ở 1 (một phần đại diện cho nhóm `SharedPtr`, buông sau khi hủy đối tượng), và hủy khối cùng lúc với đối tượng thì `WeakPtr` đọc vùng đã trả.
3. `WeakPtr::lock()` phải là vòng `compare_exchange_weak` chỉ tăng khi đếm khác 0; `expired()` là `use_count() == 0`; đối tượng đã hủy thì `lock()` trả rỗng, không bao giờ hồi sinh; vòng tham chiếu phá bằng cách đổi một chiều sang `WeakPtr`.
4. Đếm phải nguyên tử vì `++` là ba bước: bản `long` thường chạy bốn luồng cho kết quả sai, sập hoặc đúng may mắn ở `-O2`, và TSan báo race; tăng đếm dùng `relaxed`, giảm đếm dùng `acq_rel` (bỏ release thì TSan báo race giữa lần đọc và hàm hủy); chuẩn không ghi tên mức, đó là cách cài đặt đạt kết quả chuẩn đòi.
5. Bản tự cài lược bớt bộ xóa (xóa kiểu), aliasing, `make_shared` gộp một lần cấp phát (bản này cần hai lần `new`), `enable_shared_from_this`, nên nên **tự nói ra** các chỗ lược bớt này; test bằng đối tượng đếm hàm hủy cho đầu ra tất định (hủy đúng một lần), và chạy ASan/UBSan cùng TSan trước khi tuyên bố "sạch".
