# Bài 80 — Live-coding: tự cài string

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một `String` quản lý bằng RAII đúng ngay lần đầu: ba thành viên (con trỏ, độ dài, sức chứa), `'\0'` luôn ở cuối, Rule of 5 (hủy, sao chép sâu, chuyển), `c_str`, `size`, `operator[]` và `operator+=` tăng gấp đôi; đã chạy sạch với `-fsanitize=address,undefined`.
    - Cài **small string optimization** (đệm trong đối tượng cho chuỗi ngắn), chứng minh bằng bộ đếm `operator new` rằng chuỗi tới 15 ký tự không xin heap, và nói được vì sao con trỏ trỏ vào chính đối tượng bắt buộc phải có hàm sao chép và hàm chuyển tự viết.
    - Giải thích **copy-on-write** (COW), chạy ra hai thứ nó làm hỏng (tham chiếu cũ ghi nhầm sang chuỗi khác, con trỏ cũ không còn thấy chữ mới) và nói được, có hedge, vì sao các luật C++11 cho `std::string` khiến COW không còn hợp lệ.
    - Gặp và đọc được bốn lỗi kinh điển (quên ô `'\0'`, tự gán, sao chép nông, đệm bị chép con trỏ) qua báo cáo AddressSanitizer thật; so `sizeof` của ba cách cài.

**Bạn cần biết trước:** [Bài 05](../nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) (chuỗi kiểu C, `'\0'`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new[]`/`delete[]`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (sao chép sâu, tự gán), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (chuyển, `noexcept`, Rule of 5), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (AddressSanitizer), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (SSO), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (hàm thành viên `const`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template); và [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md) (thay `operator new` để đếm, `union`, `reinterpret_cast`).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đưa bút: "Không được dùng `std::string`. Viết cho tôi một lớp `String`: tạo từ chuỗi chữ, nối thêm, truy cập từng ký tự, đưa được cho hàm C. Rồi nói tôi nghe bạn sẽ làm nó nhanh hơn thế nào cho chuỗi ngắn." Đề này hay gặp vì nó nhỏ mà gom đủ bài học đã qua: bộ nhớ động, RAII, sao chép, chuyển, và cả một chuyện cài đặt thật của thư viện chuẩn.

Trong **xưởng tự lắp đồ** của nhóm này, bạn tự tháo cái máy ra xem từng bánh răng. `String` là một chiếc hộp có **nhãn dán** (địa chỉ kho, đã dùng bao nhiêu ngăn, kho có tất cả bao nhiêu ngăn) và **ngăn kéo ở kho** (heap) chứa chữ. Hàm hủy là việc "trả ngăn kéo khi bỏ hộp". Tối ưu chuỗi ngắn là **túi áo thợ**: món nhỏ nhét túi cho khỏi chạy ra kho. Copy-on-write là **hai thợ dùng chung một bản vẽ**, ai định sửa thì photo ra bản riêng trước.

!!! info "Chỗ nào ví von xưởng không còn đúng?"
    Túi áo không đưa nguyên cho người khác được: khi "chuyển" một chuỗi ngắn sang đối tượng khác, ta phải **chép chữ** từ túi này sang túi kia, chỉ chuỗi dài mới trao tay được địa chỉ kho. Và ngoài đời quên trả ngăn kéo không gây hại gì, còn heap quên `delete[]` thì **rò** thật. Ví von này chỉ giúp nhớ ba thứ trên nhãn và chuyện túi/kho.

## 📖 Giải thích

### Đề 1: `String` với RAII và Rule of 5

!!! example "Đề bài 1"
    **Ràng buộc.** Lớp `String` không dùng `std::string`. Có: hàm tạo mặc định (chuỗi rỗng), hàm tạo từ `const char*`, hàm hủy, **sao chép sâu**, **chuyển** (`noexcept`), `size()`, `c_str()` (luôn kết thúc bằng `'\0'`, kể cả chuỗi rỗng), `operator[]` (đọc và ghi), `operator+=` nhận `String`, `const char*` hoặc `char`. Không rò, không giải phóng hai lần, `s = s` và `s += s` phải đúng. Nối nhiều lần không được tốn một lần xin heap cho mỗi ký tự.

    **Đầu vào/đầu ra (bài test).** `String a("xin"); a += " chao"; a += '!';` in ra `xin chao!`, size 9. Sao chép `b = a` rồi sửa `b[0]` thì `a` giữ nguyên. Sau `c = std::move(a)` thì `a` rỗng, `c` giữ chữ. Cuối chương trình số lần `new` bằng số lần `delete`.

??? tip "Gợi ý 1"
    Hỏi trước: chuỗi ở đâu, ai là chủ, và cần **ba con số nào** để mô tả nó? Chữ ở heap thì cần con trỏ; cần biết đã dùng bao nhiêu (độ dài) và heap đang có bao nhiêu chỗ (sức chứa). Hãy viết ra **bất biến** (điều luôn đúng giữa hai lệnh): ví dụ "`d_[n_]` luôn là `'\0'`".

??? tip "Gợi ý 2"
    `+=` xin vừa đủ thì nối n lần tốn n lần xin; xin **gấp đôi** như `vector` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)) thì còn cỡ log n lần. Và hãy tự hỏi: `s += s` thì nguồn chép nằm ở đâu, và lúc ta chép xong nó còn sống không?

??? tip "Gợi ý 3"
    Sao chép: xin vùng mới, chép **cả `'\0'`**. Gán sao chép: xin vùng mới **trước**, chép, rồi mới trả vùng cũ (thì tự gán không phá gì). Chuyển: lấy ba con số của nguồn rồi đặt nguồn về "rỗng"; phép gán chuyển cần kiểm `this != &o`. Nối: tính độ dài mới, vượt sức chứa thì xin khối mới, chép cũ, chép mới, ghi `'\0'`, **sau cùng** mới trả khối cũ.

Người phỏng vấn nhìn vào sáu chỗ. Bảng này cũng là danh sách để tự rà lại bài trên bảng trắng:

| Chỗ | Bẫy nếu làm ẩu | Cách làm đúng trong bài |
|---|---|---|
| Ô cuối | Cấp `n` byte, quên `'\0'`: `c_str()` đọc lố | Cấp `n + 1`, chép `n + 1` byte |
| Sao chép | Chép nông: hai chủ một vùng, hủy hai lần | Chép sâu: mỗi chuỗi một vùng |
| Gán | Trả trước rồi chép: `s = s` mất chữ | Xin trước, chép, trả sau |
| Chuyển | Quên đặt nguồn về rỗng: hủy hai lần | Nguồn về `nullptr`, 0, 0; kiểm tự chuyển |
| Nối | Xin vừa đủ; hoặc trả khối cũ trước khi chép (`s += s`) | Gấp đôi; chép xong mới trả |
| Nối chuỗi rỗng | `String s; s += "";` khi chưa có khối: ghi `'\0'` vào `nullptr` | Thoát sớm khi không có gì để nối |

### Đề 2: tối ưu chuỗi ngắn (SSO) và copy-on-write

!!! example "Đề bài 2"
    **Ràng buộc.** "Phần lớn chuỗi thực tế rất ngắn, mà mỗi chuỗi lại xin heap một lần. Sửa `String` để chuỗi ngắn nằm **ngay trong đối tượng**." Giữ nguyên giao diện đề 1 (`c_str`, `size`, `[]`, `+=`, Rule of 5). Chuỗi tới 15 ký tự không được xin heap; từ 16 ký tự thì chuyển ra heap. Rồi: "Cách khác để copy rẻ là copy-on-write. Nó là gì, và vì sao `std::string` từ C++11 không dùng nó?"

    **Đầu vào/đầu ra (bài test).** Thay `operator new` để **đếm** số lần xin ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)). Tạo chuỗi 8 và 15 ký tự, sao chép, chuyển: đếm 0. Thêm ký tự thứ 16: đếm 1. So từng bước với `std::string` trên máy này, và in `sizeof` của cả hai.

??? tip "Gợi ý 1"
    Đối tượng đã có ba ô (con trỏ, độ dài, sức chứa) tốn 24 byte. Khi chuỗi ngắn thì chưa có khối heap nào, nên ô sức chứa (8 byte) **nhàn rỗi**: ta dùng luôn chỗ đó, cộng thêm vài byte, thành một **đệm** (buffer: mảng byte nhỏ nằm ngay trong đối tượng) để chứa chữ.

??? tip "Gợi ý 2"
    Giữ nguyên "con trỏ `d_`" để `c_str()` và `[]` không cần nhánh: chuỗi ngắn thì `d_` trỏ vào **đệm của chính đối tượng**. Nhưng hãy nghĩ: sao chép đối tượng bằng cách chép từng thành viên thì `d_` của bản sao trỏ vào đâu?

??? tip "Gợi ý 3"
    Ô sức chứa chỉ cần khi chữ ở heap, đệm chỉ cần khi chữ ở trong: cho chúng **chung một chỗ nhớ** (`union`, giải thích ở lời giải). "Chuỗi đang dài?" nghĩa là `d_ != buf_`. Khi nối vượt 15 ký tự: xin heap, chép chữ ra, **rồi mới** ghi sức chứa (vì ghi sức chứa đè lên đệm).

Bố cục 32 byte của lời giải, đã chọn để khớp với `sizeof(std::string)` của g++ 11 (xem kết quả ở dưới):

```text
chuỗi NGẮN (chữ nằm trong đối tượng):        chuỗi DÀI (chữ ở heap):
 0        8       16               32           0        8       16       24      32
 [ d_ ]--[ n_ ]--[ buf_ 16 byte ]               [ d_ ]--[ n_ ]--[ cap_ ]-[ rác ]
   |_______________^  d_ trỏ vào buf_             |
                                                  +--> khối heap: cap_ + 1 byte
```

## 💻 Ví dụ code

### Lời giải đề 1: dựng `String` từng bước

Bốn thứ cần đọc được trong code dưới:

- `std::memcpy(đích, nguồn, n)` (trong `<cstring>`) chép đúng `n` byte từ nguồn sang đích; hai vùng **không được chồng nhau**.
- `std::max(a, b)` (trong `<algorithm>`, cùng thư viện với `std::sort` ở [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)) trả số lớn hơn trong hai số.
- `char& operator[](std::size_t i)` trả **tham chiếu** tới ký tự ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)) nên `s[0] = 'X'` ghi thẳng vào ô; ta viết thêm bản `const` ([Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) để chuỗi `const` vẫn đọc được. `char* d_ = nullptr;` đặt giá trị khởi tạo ngay tại chỗ khai báo thành viên.
- Cặp `operator new[]`/`delete[]` ở đầu chương trình là phần mở rộng của bộ đếm ở [Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md), vì `new char[n]` đi qua `operator new[]`.

Dựng theo bốn bước, mỗi bước thêm một thứ và một câu hỏi tự kiểm:

| Bước | Thêm gì | Câu tự kiểm |
|---|---|---|
| 1 | Ba thành viên `d_`, `n_`, `cap_`; bất biến "`d_ == nullptr` khi `cap_ == 0`, ngược lại `d_[n_] == '\0'` và `n_ <= cap_`"; `c_str()` trả `d_` hoặc chuỗi hằng `""` khi rỗng | Chuỗi rỗng có `c_str()` hợp lệ chưa? |
| 2 | Hàm tạo từ `const char*` (cấp `n + 1` byte, chép `n + 1` byte) và hàm hủy `delete[] d_` (`delete[]` trên `nullptr` là hợp lệ) | Đã đếm ô cho `'\0'` chưa? |
| 3 | `them(s, k)`: `k == 0` thì thoát ngay; tính độ dài mới; vượt sức chứa thì xin khối `max(mới, 2 × cũ)`, chép chữ cũ, chép `k` ký tự, ghi `'\0'`, và **sau cùng** mới trả khối cũ | `s += s` còn đúng không? |
| 4 | Sao chép sâu, gán (xin trước, trả sau), chuyển và gán chuyển (kiểm `this != &o`) | `s = s`, `s = std::move(s)` còn đúng không? |

Bản đầy đủ, kèm chương trình thử:

```cpp
#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <utility>

std::size_t soLanXin = 0, soLanTra = 0;          // bộ đếm cấp phát (Bài 58)

void* operator new(std::size_t n) {
    ++soLanXin;
    void* p = std::malloc(n);
    if (p == nullptr) throw std::bad_alloc();
    return p;
}
void* operator new[](std::size_t n) { return operator new(n); }      // new char[...] đi qua đây
void operator delete(void* p) noexcept { if (p) ++soLanTra; std::free(p); }
void operator delete[](void* p) noexcept { operator delete(p); }
void operator delete(void* p, std::size_t) noexcept { operator delete(p); }        // bản có kích thước (C++14)
void operator delete[](void* p, std::size_t) noexcept { operator delete(p); }

class String {
public:
    String() = default;                                   // (1) rỗng: chưa xin heap
    String(const char* s) {                               // (2)
        n_ = std::strlen(s);
        if (n_ > 0) {
            cap_ = n_;
            d_ = new char[cap_ + 1];                      // (3) +1 ô cho '\0'
            std::memcpy(d_, s, n_ + 1);
        }
    }
    ~String() { delete[] d_; }                            // (4)

    String(const String& o) : n_(o.n_), cap_(o.n_) {      // (5) sao chép sâu
        if (n_ > 0) {
            d_ = new char[cap_ + 1];
            std::memcpy(d_, o.d_, n_ + 1);
        }
    }
    String& operator=(const String& o) {                  // (6) xin trước, trả sau
        char* moi = nullptr;
        if (o.n_ > 0) {
            moi = new char[o.n_ + 1];
            std::memcpy(moi, o.d_, o.n_ + 1);
        }
        delete[] d_;
        d_ = moi;
        n_ = cap_ = o.n_;
        return *this;
    }
    String(String&& o) noexcept : d_(o.d_), n_(o.n_), cap_(o.cap_) {   // (7)
        o.d_ = nullptr;
        o.n_ = o.cap_ = 0;
    }
    String& operator=(String&& o) noexcept {              // (8)
        if (this != &o) {                                 // (9) tự chuyển: bắt buộc kiểm
            delete[] d_;
            d_ = o.d_;
            n_ = o.n_;
            cap_ = o.cap_;
            o.d_ = nullptr;
            o.n_ = o.cap_ = 0;
        }
        return *this;
    }

    String& operator+=(const String& o) { them(o.d_, o.n_); return *this; }   // (10)
    String& operator+=(const char* s) { them(s, std::strlen(s)); return *this; }
    String& operator+=(char c) { them(&c, 1); return *this; }

    char& operator[](std::size_t i) { return d_[i]; }                 // (11)
    const char& operator[](std::size_t i) const { return d_[i]; }
    std::size_t size() const { return n_; }
    std::size_t capacity() const { return cap_; }
    const char* c_str() const { return d_ ? d_ : ""; }                // (12)

private:
    void them(const char* s, std::size_t k) {             // (13) nối k ký tự từ s
        if (k == 0) return;                               // nối rỗng: không làm gì (d_ có thể là nullptr)
        std::size_t moiN = n_ + k;
        if (moiN > cap_) {
            std::size_t cap = std::max(moiN, cap_ * 2);   // (14) tăng gấp đôi
            char* p = new char[cap + 1];
            if (n_ > 0) std::memcpy(p, d_, n_);
            std::memcpy(p + n_, s, k);                    // (15) s có thể nằm trong d_: chưa trả d_
            p[moiN] = '\0';
            delete[] d_;
            d_ = p;
            cap_ = cap;
        } else {
            std::memcpy(d_ + n_, s, k);
            d_[moiN] = '\0';
        }
        n_ = moiN;
    }

    char* d_ = nullptr;        // chữ ở heap; nullptr khi chưa có gì (cap_ == 0)
    std::size_t n_ = 0;        // số ký tự, không tính '\0'
    std::size_t cap_ = 0;      // sức chứa, không tính '\0'; cấp phát cap_ + 1 byte
};

int main() {
    std::cout << "sizeof(String)=" << sizeof(String) << "\n";
    {
        String a("xin");
        a += " chao";
        a += '!';
        std::cout << "a = " << a.c_str() << " size=" << a.size() << " cap=" << a.capacity() << "\n";

        String b = a;                                      // sao chép sâu
        b[0] = 'X';
        std::cout << "a = " << a.c_str() << ", b = " << b.c_str() << "\n";

        b = a;                                             // gán sao chép
        a = a;                                             // tự gán: vẫn đúng
        a += a;                                            // nối chính mình
        std::cout << "b = " << b.c_str() << ", a += a: " << a.c_str() << " size=" << a.size() << "\n";

        String c = std::move(a);                           // chuyển
        std::cout << "sau move a.size=" << a.size() << " a=\"" << a.c_str() << "\" c.size=" << c.size() << "\n";
        c = std::move(c);                                  // tự chuyển: không hỏng
        const String k("hang");
        String rong;
        rong += "";                                        // nối chuỗi rỗng vào chuỗi chưa có khối: phải không hỏng
        std::cout << "tu chuyen c = " << c.c_str() << ", k[1] = " << k[1] << ", rong.size = " << rong.size()
                  << " c_str = \"" << rong.c_str() << "\"\n";
    }
    std::cout << "xin " << soLanXin << " lan, tra " << soLanTra << " lan\n";

    std::size_t truoc = soLanXin;
    {
        String s;
        for (int i = 0; i < 100; ++i) s += 'x';
        std::cout << "100 lan += 'x': size=" << s.size() << " cap=" << s.capacity()
                  << ", " << soLanXin - truoc << " lan xin\n";
    }
    std::cout << "xin " << soLanXin << " lan, tra " << soLanTra << " lan\n";
    return 0;
}
```

**Chạy từng dòng** (địa chỉ minh họa, máy bạn sẽ in số khác; `[...]` là các ô byte của khối heap)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `String a("xin");` | Hàm tạo (2): `n_ = 3`, `cap_ = 3`, xin 4 byte (3), chép cả `'\0'` | `a.d_`=0x1000 ─> `[x][i][n][\0]` |
| `a += " chao";` | Chọn bản `const char*` (10) → `them` (13): 8 > 3 nên `cap = max(8, 6) = 8` (14); xin 9 byte, chép "xin" rồi " chao", ghi `'\0'`, trả khối cũ | `a.d_`=0x2000 ─> `[x i n _ c h a o \0]` |
| `a += '!';` | 9 > 8 nên `cap = max(9, 16) = 16`: xin 17 byte, chữ chép sang, trả khối 9 byte | `a.d_`=0x3000, `n_`=9, `cap_`=16 |
| `String b = a;` | Hàm tạo sao chép (5): vùng **riêng** cho `b`, `cap_` = 9, chép 10 byte | `b.d_`=0x4000 (khác `a.d_`) |
| `b[0] = 'X';` | `operator[]` (11) trả `char&` tới ô đầu của **b** | `a` vẫn `xin chao!` |
| `b = a; a = a;` | Gán (6): xin vùng mới, chép, rồi trả vùng cũ. Với `a = a`, vùng "nguồn" còn nguyên vì chưa trả, nên chép xong mới trả vẫn đúng | chữ không mất |
| `a += a;` | `them(o.d_, o.n_)` với nguồn **là chính khối của `a`**; 18 > 9 nên xin khối mới; (15) chép nguồn **trước** khi trả khối cũ | `xin chao!xin chao!` |
| `String c = std::move(a);` | Hàm tạo chuyển (7): `c` lấy `d_`, `n_`, `cap_`; `a` về `nullptr`, 0, 0 | `a.d_`=`nullptr`, `c.d_`=0x5000 |
| `c = std::move(c);` | (8) thấy `this == &o` (9) nên không làm gì | không đổi |
| `String rong;` | (1): không xin heap; `c_str()` (12) trả `""` | `rong.d_`=`nullptr` |
| `rong += "";` | Chọn bản `const char*` (10) → `them("", 0)`: `k == 0` nên thoát ngay, không đụng tới `d_` (đang là `nullptr`) | không đổi |
| hết khối `{ }` | Hủy ngược thứ tự tạo; `delete[]` trên `nullptr` bỏ qua | số lần trả = số lần xin |

**Kết quả khi chạy:**

```text
sizeof(String)=24
a = xin chao! size=9 cap=16
a = xin chao!, b = Xin chao!
b = xin chao!, a += a: xin chao!xin chao! size=18
sau move a.size=0 a="" c.size=18
tu chuyen c = xin chao!xin chao!, k[1] = a, rong.size = 0 c_str = ""
xin 8 lan, tra 8 lan
100 lan += 'x': size=100 cap=128, 8 lan xin
xin 16 lan, tra 16 lan
```

Biên dịch sạch cảnh báo với `g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined`, thoát mã 0 (AddressSanitizer kiểm cả rò rỉ nên không rò); `-O2` ra cùng đầu ra. Tám lần xin ở khối đầu: `a` ba lần (xin, `" chao"`, `'!'`), rồi `b = a`, `b = a`, `a = a`, `a += a` mỗi dòng một lần, và `k("hang")`. Nối 100 ký tự từng cái một xin **8** lần (sức chứa 1, 2, 4, …, 128), không phải 100.

**Thử thay đổi 1: đổi `std::max(moiN, cap_ * 2)` thành `moiN` (xin vừa đủ).** Mình đã chạy: nối 100 ký tự xin **100** lần (`cap=100`) thay vì 8. Mỗi lần nối chép lại cả chuỗi nên tổng công việc cỡ n bình phương; gấp đôi thì mỗi ký tự chép O(1) lần *trung bình* (amortized).

**Thử thay đổi 2: bỏ kiểm `this != &o` ở (8).** Mình đã chạy: `c = std::move(c)` làm `c` thành chuỗi **rỗng** (`tu chuyen c = ` in ra trống), không báo lỗi gì, số lần xin/trả vẫn bằng nhau. Lý do: `delete[] d_` trả khối, rồi `o.d_ = nullptr` cũng chính là `d_ = nullptr` vì `o` là `*this`. Mất chữ im lặng.

**Thử thay đổi 3: bỏ dòng `if (k == 0) return;` trong `them`.** Mình đã chạy: `rong += ""` với `rong` chưa có khối rơi vào nhánh `else`, và UBSan báo `null pointer passed as argument 1, which is declared to never be null` (từ `memcpy`) rồi `store to null pointer of type 'char'`; chương trình chết `SEGV` ở `String::them` khi ghi `d_[moiN] = '\0'`. Chuỗi rỗng chưa cấp phát (`d_ == nullptr`) là trạng thái hợp lệ, nên mọi hàm đụng tới `d_` phải tính tới nó. Bản SSO ở đề 2 không dính lỗi này vì `d_` luôn trỏ vào đệm.

**Bản SAI 1: quên ô cho `'\0'`.** Cấp `n_` byte thay vì `n_ + 1` (và chép `n_` byte). Chạy bài thử `String s("xin"); std::cout << s.c_str();` với AddressSanitizer:

```cpp
// bo-qua-kiem-tra
d_ = new char[n_];                 // SAI: thiếu +1
std::memcpy(d_, s, n_);            // chữ có, '\0' không
```

```text
ERROR: AddressSanitizer: heap-buffer-overflow ... READ of size 4
    #0 ... in __interceptor_strlen
    #1 ... in std::operator<< <std::char_traits<char> >(std::basic_ostream<char>&, char const*)
0x... is located 0 bytes to the right of 3-byte region
allocated by thread T0 here: ... in String::String(char const*)
```

`operator<<` nhận `const char*` thì gọi `strlen`, chạy tới khi gặp `'\0'`; không có thì đọc lố khối 3 byte ("0 bytes to the right": ngay sát bên phải khối). Không bật ASan, chương trình có thể in rác hoặc vô tình chạy đúng.

**Bản SAI 2: tự gán `s = s` khi trả trước.** Viết `delete[] d_; d_ = new char[o.n_ + 1]; std::memcpy(d_, o.d_, o.n_ + 1);` rồi chạy `String s("xin chao"); s = s; std::cout << s.c_str();`:

```text
ERROR: AddressSanitizer: heap-buffer-overflow ... READ of size 10
    #0 ... in __interceptor_strlen
0x... is located 0 bytes to the right of 9-byte region
allocated by thread T0 here: ... in String::operator=(String const&)
```

Không phải dùng-sau-khi-trả như nhiều người đoán: `o` chính là `*this`, nên sau `new` thì `o.d_` đã là **khối mới chưa có chữ**; `memcpy` chép khối mới lên chính nó, chữ cũ mất, và khối mới không có `'\0'` đúng chỗ. Bản đúng ở (6) xin trước, trả sau nên không cần kiểm `this != &o`.

**Bản SAI 3: sao chép nông (có hàm hủy mà quên hai hàm sao chép).** Lớp chỉ có hàm hủy `delete[] d_`; `String a("xin chao"); String b = a;`:

```text
ERROR: AddressSanitizer: attempting double-free on 0x... in thread T0:
    #0 ... in operator delete[](void*)
    #1 ... in String::~String()
freed by thread T0 here: ... in String::~String()
previously allocated by thread T0 here: ... in String::String(char const*)
```

Hàm sao chép tự sinh chép từng thành viên, nên `b.d_ == a.d_`: một khối, hai chủ; hàm hủy thứ hai trả lần nữa (loại lỗi ở [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Đó là lý do của Rule of 3/5.

### Lời giải đề 2: SSO với `union` và con trỏ vào chính mình

Bốn cú pháp mới trong code dưới:

- **`union`**: các thành viên chung một chỗ nhớ, một lúc chỉ **một** thành viên đang dùng; kích thước bằng thành viên lớn nhất ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md) đã dùng `union` cho pool). Khai báo **không tên** (như dưới đây) thì dùng thẳng `cap_` và `buf_` như thành viên của lớp.
- **Hàm tạo ủy nhiệm**: `SString(const char* s) : SString() { ... }` gọi hàm tạo khác của cùng lớp để dựng trạng thái "rỗng" trước, rồi mới nối.
- **`static constexpr`**: hằng chung cho cả lớp, tính lúc biên dịch, dùng được làm cỡ mảng.
- `reinterpret_cast<std::uintptr_t>(p)` đổi một địa chỉ thành số để so sánh ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)).

```cpp
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
#include <utility>

std::size_t soLanXin = 0;                        // bộ đếm cấp phát (Bài 58)

void* operator new(std::size_t n) {
    ++soLanXin;
    void* p = std::malloc(n);
    if (p == nullptr) throw std::bad_alloc();
    return p;
}
void* operator new[](std::size_t n) { return operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { operator delete(p); }
void operator delete(void* p, std::size_t) noexcept { operator delete(p); }        // bản có kích thước (C++14)
void operator delete[](void* p, std::size_t) noexcept { operator delete(p); }

class SString {
public:
    static constexpr std::size_t NGAN = 15;              // (1) tối đa 15 ký tự trong đệm, ô thứ 16 giữ '\0'

    SString() : d_(buf_), n_(0) { buf_[0] = '\0'; }      // (2) ngắn và rỗng: không xin heap
    SString(const char* s) : SString() { them(s, std::strlen(s)); }
    ~SString() { if (dai()) delete[] d_; }               // (3) chỉ trả khi chữ ở heap

    SString(const SString& o) : SString() { them(o.d_, o.n_); }      // (4) sao chép: d_ của MÌNH
    SString& operator=(const SString& o) {                           // (5)
        if (this != &o) {
            n_ = 0;
            d_[0] = '\0';
            them(o.d_, o.n_);                            // dùng lại sức chứa đang có
        }
        return *this;
    }
    SString(SString&& o) noexcept : d_(buf_), n_(0) {    // (6)
        buf_[0] = '\0';
        cuop(o);
    }
    SString& operator=(SString&& o) noexcept {           // (7)
        if (this != &o) {
            if (dai()) delete[] d_;
            d_ = buf_;                                   // về trạng thái ngắn rồi mới cướp
            cuop(o);
        }
        return *this;
    }

    SString& operator+=(const SString& o) { them(o.d_, o.n_); return *this; }
    SString& operator+=(const char* s) { them(s, std::strlen(s)); return *this; }
    SString& operator+=(char c) { them(&c, 1); return *this; }

    char& operator[](std::size_t i) { return d_[i]; }
    const char& operator[](std::size_t i) const { return d_[i]; }
    std::size_t size() const { return n_; }
    std::size_t capacity() const { return dai() ? cap_ : NGAN; }
    const char* c_str() const { return d_; }             // (8) lúc nào cũng d_: không cần nhánh
    bool dai() const { return d_ != buf_; }              // (9) chữ đang ở heap?

private:
    void them(const char* s, std::size_t k) {            // nối k ký tự từ s
        std::size_t moiN = n_ + k;
        if (moiN > capacity()) {
            std::size_t cap = std::max(moiN, capacity() * 2);
            char* p = new char[cap + 1];
            std::memcpy(p, d_, n_);
            std::memcpy(p + n_, s, k);                   // (10) s có thể nằm trong buf_: chép xong mới ghi cap_
            p[moiN] = '\0';
            if (dai()) delete[] d_;
            d_ = p;
            cap_ = cap;                                  // (11) ghi cap_ sẽ đè lên buf_
        } else {
            std::memcpy(d_ + n_, s, k);
            d_[moiN] = '\0';
        }
        n_ = moiN;
    }
    void cuop(SString& o) noexcept {                     // (12) *this đang ngắn, không giữ heap
        if (o.dai()) {
            d_ = o.d_;
            cap_ = o.cap_;
        } else {
            std::memcpy(buf_, o.buf_, o.n_ + 1);         // chữ ngắn: chép sang đệm của mình
        }
        n_ = o.n_;
        o.d_ = o.buf_;                                   // nguồn về "ngắn, rỗng"
        o.n_ = 0;
        o.buf_[0] = '\0';
    }

    char* d_;                                            // trỏ vào buf_ (ngắn) hoặc heap (dài)
    std::size_t n_;
    union {                                              // (13) hai thứ không bao giờ dùng cùng lúc
        std::size_t cap_;                                // dài: sức chứa của khối heap
        char buf_[NGAN + 1];                             // ngắn: đệm chứa chữ
    };
};

template <typename S>
bool chuNamTrongDoiTuong(const S& s) {                   // c_str() có nằm trong chính đối tượng không?
    std::uintptr_t chu = reinterpret_cast<std::uintptr_t>(s.c_str());
    std::uintptr_t dau = reinterpret_cast<std::uintptr_t>(&s);
    return chu >= dau && chu < dau + sizeof(S);
}

template <typename S>
void thu(const char* ten, std::size_t soKyTu) {          // dựng chuỗi soKyTu ký tự bằng += từng ký tự
    std::size_t truoc = soLanXin;
    S s;
    for (std::size_t i = 0; i < soKyTu; ++i) s += 'x';
    std::cout << "  " << ten << " " << soKyTu << " ky tu: " << soLanXin - truoc << " lan xin, trong doi tuong: "
              << (chuNamTrongDoiTuong(s) ? "co" : "khong") << "\n";
}

int main() {
    std::cout << "sizeof(SString)=" << sizeof(SString) << " sizeof(std::string)=" << sizeof(std::string) << "\n";

    std::size_t truoc = soLanXin;
    SString ngan("xin chao");                            // 8 ký tự
    SString muoiLam("123456789012345");                  // đúng 15
    SString b = ngan;                                    // sao chép chuỗi ngắn
    SString c;
    c = muoiLam;
    std::cout << "tao + chep chuoi ngan: " << soLanXin - truoc << " lan xin, dia chi chu cua b khac cua ngan: "
              << (b.c_str() != ngan.c_str() ? "dung" : "sai") << "\n";

    truoc = soLanXin;
    SString d(muoiLam);
    d += '!';                                            // ký tự thứ 16
    std::cout << "d = " << d.c_str() << " size=" << d.size() << " cap=" << d.capacity()
              << " dai=" << d.dai() << ", " << soLanXin - truoc << " lan xin\n";

    truoc = soLanXin;
    SString e = std::move(d);                            // chuỗi dài: cướp con trỏ
    std::cout << "move chuoi dai: " << soLanXin - truoc << " lan xin; d.size=" << d.size()
              << " d=\"" << d.c_str() << "\" e.size=" << e.size() << "\n";
    SString f = std::move(ngan);                         // chuỗi ngắn: chép đệm
    std::cout << "move chuoi ngan: f = " << f.c_str() << ", ngan.size=" << ngan.size() << "\n";

    SString g("0123456789");                             // tự nối: ngắn -> dài, nguồn nằm trong đệm
    g += g;
    g = g;
    e = std::move(e);
    e[0] = 'X';
    std::cout << "g += g; g = g: " << g.c_str() << " dai=" << g.dai() << ", e = " << e.c_str() << "\n";

    std::cout << "so lan xin khi += tung ky tu (SString | std::string):\n";
    const std::size_t cac[] = {8, 15, 16, 100};
    for (std::size_t k : cac) {
        thu<SString>("SString    ", k);
        thu<std::string>("std::string", k);
    }
    return 0;
}
```

**Chạy từng dòng** (các số `0x...` là địa chỉ minh họa; hộp là đối tượng 32 byte)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | Chuỗi rỗng: `d_` trỏ vào `buf_` của **chính mình**, `buf_[0] = '\0'`; không xin heap | `[d_=&buf_][n_=0][buf_="\0"…]` |
| `SString ngan("xin chao")` | `them`: 8 ≤ `capacity()` = 15 nên chép thẳng vào `buf_`; **0 lần xin** | `d_=0x7ff0` trong đối tượng, `buf_="xin chao\0"` |
| (4) `SString b = ngan` | Dựng `b` rỗng trước rồi `them(o.d_, o.n_)`: `b.d_` trỏ vào `buf_` của **b**, không phải của `ngan` | hai đệm riêng |
| `d += '!'` (16 ký tự) | 16 > 15: `cap = max(16, 30) = 30`, xin 31 byte (10), chép chữ **trước** khi ghi `cap_` (11) vì `cap_` đè lên `buf_` | `d_` ─> heap; `cap_`=30 |
| (6) `SString e = std::move(d)` | `cuop` (12): `d` đang dài nên `e` lấy `d_` và `cap_`; `d` về ngắn rỗng; **0 lần xin** | `e.d_` ─> heap cũ; `d.d_`=&`d.buf_` |
| `SString f = std::move(ngan)` | `ngan` ngắn: không có gì để "trao tay", chép 9 byte sang `buf_` của `f` | hai đệm, `ngan` rỗng |
| `g += g` | `g` ngắn 10 ký tự, nối 10 nữa > 15: xin heap; (10) chép từ `s` (nằm trong `buf_` của `g`) **trước** khi (11) ghi `cap_` | `g` dài 20 ký tự |
| (5), (7) | `g = g`, `e = std::move(e)`: cả hai kiểm `this != &o` nên không đụng gì | không đổi |

**Kết quả khi chạy:**

```text
sizeof(SString)=32 sizeof(std::string)=32
tao + chep chuoi ngan: 0 lan xin, dia chi chu cua b khac cua ngan: dung
d = 123456789012345! size=16 cap=30 dai=1, 1 lan xin
move chuoi dai: 0 lan xin; d.size=0 d="" e.size=16
move chuoi ngan: f = xin chao, ngan.size=0
g += g; g = g: 01234567890123456789 dai=1, e = X23456789012345!
so lan xin khi += tung ky tu (SString | std::string):
  SString     8 ky tu: 0 lan xin, trong doi tuong: co
  std::string 8 ky tu: 0 lan xin, trong doi tuong: co
  SString     15 ky tu: 0 lan xin, trong doi tuong: co
  std::string 15 ky tu: 0 lan xin, trong doi tuong: co
  SString     16 ky tu: 1 lan xin, trong doi tuong: khong
  std::string 16 ky tu: 1 lan xin, trong doi tuong: khong
  SString     100 ky tu: 3 lan xin, trong doi tuong: khong
  std::string 100 ky tu: 3 lan xin, trong doi tuong: khong
```

Biên dịch sạch với `-Wall -Wextra -fsanitize=address,undefined`, thoát mã 0, `-O2` cùng đầu ra. `sizeof(SString)` = `sizeof(std::string)` = 32 (8 con trỏ + 8 độ dài + 16 dùng chung cho sức chứa/đệm; không có `union` thì 40). Chuỗi 8 và 15 ký tự: **0** lần xin, chữ nằm trong đối tượng; 16 ký tự: **1** lần. Đếm của `SString` và `std::string` **giống hệt nhau** ở mọi hàng, kể cả 3 lần xin cho 100 ký tự (sức chứa 30, 60, 120). Số 15 là của libstdc++ trong g++ 11; **chuẩn không quy định** SSO hay ngưỡng nên máy khác có thể ra số khác (Bài 17).

**Thử thay đổi: bỏ kiểm `this != &o` ở (7).** Mình đã chạy: với `e = std::move(e)`, `delete[] d_` rồi `d_ = buf_`; `o` (tức `*this`) giờ trông như chuỗi ngắn nhưng `n_` vẫn 16, nên `memcpy` đọc 17 byte từ đệm 16 byte: AddressSanitizer báo `stack-buffer-overflow ... READ of size 17` trong `memcpy`, từ `SString::cuop`. Gán chuyển phải kiểm tự chuyển.

**Bản SAI 4: đệm bị chép con trỏ.** Lỗi chỉ có ở SSO kiểu "con trỏ vào chính mình": không viết hàm sao chép, để trình biên dịch chép từng thành viên.

```cpp
// bo-qua-kiem-tra
class SString {                      // rút gọn: chỉ giữ ba thành viên, KHÔNG có hàm sao chép
public:
    SString(const char* s) : d_(buf_), n_(std::strlen(s)) { std::memcpy(buf_, s, n_ + 1); }
    const char* c_str() const { return d_; }
private:
    char* d_; std::size_t n_; char buf_[16];
};
// main: SString b(""); { SString a("xin chao"); b = a; }  std::cout << b.c_str();
```

```text
ERROR: AddressSanitizer: stack-use-after-scope on address 0x... 
READ of size 9 at 0x... thread T0
    #0 ... in __interceptor_strlen
    #2 ... in main
This frame has 2 object(s):
    [32, 64) 'b'
    [96, 128) 'a' <== Memory access at offset 112 is inside this variable
```

Phép gán mặc định chép `d_` nguyên xi, nên `b.d_` trỏ vào `buf_` của **`a`**; `a` hết phạm vi thì đệm của nó chết theo mà `b` vẫn trỏ vào. Với chuỗi **dài** cùng thiếu sót đó cho double free như SAI 3. Bản đúng ở (4)–(7) luôn để `d_` của mỗi đối tượng trỏ vào đệm của chính nó.

Hệ quả người phỏng vấn thích hỏi: với SSO, **chuyển chuỗi ngắn không giữ nguyên con trỏ**. Mình chạy `std::string` g++ 11: `p = s.c_str()` (3 ký tự) rồi `t = std::move(s)` cho `p == t.c_str()` là **sai** (`p` vẫn trỏ vào `s`); với chuỗi 40 ký tự thì **đúng** (trao tay con trỏ). Chuẩn không hứa con trỏ còn dùng được sau khi chuyển.

### Copy-on-write và vì sao C++11 bỏ nó

**Copy-on-write (COW)**: sao chép chuỗi chỉ chép con trỏ và tăng một bộ đếm dùng chung; chữ chỉ được chép thật khi một bên **sửa**. Ý tưởng giống `fork` ở [Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md) và giống cách Go dùng chuỗi bất biến. Chương trình dưới dựng COW bằng `shared_ptr` ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md), `use_count`) để thấy cả mặt được lẫn mặt hỏng:

```cpp
#include <cstddef>
#include <iostream>
#include <memory>
#include <string>

class CowString {
public:
    CowString(const char* s) : p_(std::make_shared<std::string>(s)) {}
    // sao chép: mặc định chỉ chép con trỏ chung (tăng đếm), O(1), không cấp phát chữ
    char& operator[](std::size_t i) {
        if (p_.use_count() > 1)                         // đang chung với ai đó: tách bản riêng trước
            p_ = std::make_shared<std::string>(*p_);
        return (*p_)[i];
    }
    const char* c_str() const { return p_->c_str(); }
    long dem() const { return p_.use_count(); }
private:
    std::shared_ptr<std::string> p_;
};

int main() {
    CowString s("abc");
    CowString t = s;                                    // (1) chung một khối, chưa chép chữ
    std::cout << "sau t = s: dem = " << s.dem() << ", cung dia chi chu: " << (s.c_str() == t.c_str()) << "\n";
    s[0] = 'X';                                         // (2) ghi: tách riêng
    std::cout << "sau s[0] = 'X': s = " << s.c_str() << ", t = " << t.c_str() << ", dem = " << s.dem() << "\n";

    CowString u("abc");
    char& r = u[0];                                     // (3) xin tham chiếu khi chưa ai chung
    CowString v = u;                                    // sao chép: chung khối
    r = 'X';                                            // (4) ghi qua tham chiếu cũ: không qua operator[] nữa
    std::cout << "COW: u = " << u.c_str() << ", v = " << v.c_str() << "\n";

    CowString w("abc");
    CowString z = w;                                    // chung khối
    const char* con = w.c_str();                        // (5) con trỏ tới khối chung
    w[0] = 'X';                                         // (6) w tách bản riêng: khối cũ giờ chỉ còn z giữ
    std::cout << "COW: w = " << w.c_str() << ", con[0] = " << con[0] << "\n";

    std::string a = "abc";
    char& q = a[0];
    std::string b = a;
    q = 'X';
    std::cout << "std::string: a = " << a << ", b = " << b << "\n";

    std::string a2 = "abc";
    const char* cp = a2.c_str();
    a2[0] = 'X';
    std::cout << "std::string: a2 = " << a2 << ", cp[0] = " << cp[0] << "\n";
    return 0;
}
```

**Chạy từng dòng** (`dem` = `use_count`; địa chỉ bỏ qua, chỉ vẽ ai trỏ vào khối nào)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `CowString t = s;` | Hàm sao chép tự sinh chép con trỏ `shared_ptr`: `use_count` thành 2, không chép chữ | `s.p_` và `t.p_` ─> cùng một `string` |
| (2) `s[0] = 'X';` | `use_count() > 1` nên `s` dựng bản riêng rồi mới trả tham chiếu; `t` giữ bản cũ, đếm về 1 | `s.p_` ─> `"Xbc"`, `t.p_` ─> `"abc"` |
| (3), (4) `r`, `v = u`, `r = 'X'` | `r` lấy khi `u` chưa chung ai; `v = u` làm hai bên chung khối; `r = 'X'` ghi thẳng vào khối chung, không qua `operator[]` nên không ai tách | `u` và `v` cùng thấy `"Xbc"` |
| (5), (6) `con`, `w[0] = 'X'` | `con` trỏ vào khối chung của `w` và `z`; `w[0]` tách bản riêng cho `w`, còn `con` vẫn trỏ vào khối cũ (nay chỉ `z` giữ) nên `con[0]` là `'a'` | `w.p_` ─> `"Xbc"`; `z.p_`, `con` ─> `"abc"` |
| hai đoạn `std::string` | `b = a` chép chữ sang chỗ riêng nên `q = 'X'` chỉ đổi `a`; `a2[0] = 'X'` sửa tại chỗ nên `cp` vẫn trỏ vào chữ của `a2` | `a`, `b` hai chỗ; `cp` ─> chữ của `a2` |

**Kết quả khi chạy:**

```text
sau t = s: dem = 2, cung dia chi chu: 1
sau s[0] = 'X': s = Xbc, t = abc, dem = 1
COW: u = Xbc, v = Xbc
COW: w = Xbc, con[0] = a
std::string: a = Xbc, b = abc
std::string: a2 = Xbc, cp[0] = X
```

Hai dòng đầu là lợi ích: `t = s` chỉ tăng đếm (`dem = 2`, cùng địa chỉ chữ), tới khi `s[0] = 'X'` mới tách ra. Hai dòng `COW:` tiếp theo là cái hỏng của COW **ngây thơ** như bản trên; hai dòng `std::string` là hành vi mà chuẩn đòi.

- **Lỗi 1** (`u = Xbc, v = Xbc`): lấy tham chiếu `r` khi chưa ai chung, rồi sao chép `v = u` (một thao tác chỉ-đọc), rồi ghi qua `r`. `r = 'X'` không gọi `operator[]` nên không ai tách, và `v` bị sửa lây. `std::string` thật in `b = abc`.
- **Lỗi 2** (`con[0] = a`): con trỏ `con` lấy trước khi gọi `w[0]` không còn thấy chữ mới của `w`. `std::string` thật in `cp[0] = X`: `operator[]` sửa tại chỗ.

COW nghiêm túc chữa được lỗi 1 bằng cách đánh dấu "đừng chia sẻ nữa" mỗi khi đã đưa tham chiếu ra ngoài (theo mô tả quen thuộc về libstdc++ cũ; mình không đọc lại mã nguồn của nó). Lỗi 2 thì khó tránh: `operator[]` không-const trên chuỗi đang chung buộc phải chép chữ sang chỗ mới.

Chuẩn C++11 không có câu "cấm COW"; nó siết những điều COW khó giữ. Phần dưới là **theo trí nhớ của mình**, chưa đối chiếu lại văn bản chuẩn lúc viết bài, nên hãy tự kiểm khi cần trích dẫn:

- Con trỏ, tham chiếu, iterator tới ký tự chỉ bị mất hiệu lực bởi một danh sách thao tác nêu rõ, và `operator[]`, `at`, `begin`, `end`... **không** nằm trong danh sách (C++03 còn cho lần gọi không-const đầu tiên làm mất hiệu lực, khe hở mà COW dựa vào). Lỗi 2 ở trên là đúng điều này.
- Các hàm truy cập ấy còn phải tốn thời gian hằng, trong khi COW khi tách phải chép cả chuỗi: O(n).
- Chi phí đi kèm, không phải vi phạm: bộ đếm chung phải tăng/giảm nguyên tử, vì hai chuỗi chung khối có thể nằm ở hai luồng khác nhau.

Từ GCC 5, libstdc++ chuyển sang `std::string` mới (có SSO); bản cũ chọn lại được bằng `-D_GLIBCXX_USE_CXX11_ABI=0`. Mình chạy cùng một chương trình đo (g++ 11, bộ đếm `operator new`):

```text
-D_GLIBCXX_USE_CXX11_ABI=1 (mặc định)       -D_GLIBCXX_USE_CXX11_ABI=0 (bản COW cũ)
sizeof(std::string) = 32                    sizeof(std::string) = 8
chép chuỗi 100 ký tự: 1 lần xin, chữ khác   chép chuỗi 100 ký tự: 0 lần xin, cùng địa chỉ chữ
tạo chuỗi 3 ký tự rồi chép: 0 lần xin       tạo chuỗi 3 ký tự rồi chép: 1 lần xin (không SSO)
```

SSO đổi thế mạnh: chuỗi ngắn (đa số) sao chép miễn phí, chuỗi dài tốn một lần xin nhưng không có bộ đếm dùng chung và không có chuyện `operator[]` phải tách bản riêng.

### Phân tích chi phí và khi nào không tự cài

Số liệu đều đo trên g++ 11 với bộ đếm `operator new` (nối ký tự từng cái một); đổi theo thư viện.

| | `String` (đề 1) | `SString` (đề 2) | `std::string` (g++ 11) |
|---|---|---|---|
| `sizeof` | 24 | 32 | 32 |
| Nối 8 ký tự: số lần xin | 4 | 0 | 0 |
| Nối 15 ký tự | 5 | 0 | 0 |
| Nối 16 ký tự | 5 | 1 | 1 |
| Nối 100 ký tự | 8 | 3 | 3 |
| `c_str()`, `[]` | một nhánh (`nullptr` → `""`) | không nhánh | không nhánh |

Trả giá của SSO: đối tượng to hơn (32 so với 24), chuỗi dài vẫn xin heap, `c_str()` và tham chiếu tới ký tự **không ổn định** khi chuyển/hoán đổi. Đề 1 dùng `std::max(moiN, cap_ * 2)` nên mỗi ký tự chép O(1) trung bình; `operator[]` O(1); sao chép O(n).

**Khi nào KHÔNG tự cài string:** gần như mọi lúc trong sản phẩm. `std::string` đã đúng, đã được kiểm thử kỹ, đã có SSO, đã có `reserve`, `append`, `find`. Tự cài đáng làm để **học** và để trả lời phỏng vấn; chỉ tự viết kiểu chuỗi khi có ràng buộc đặc biệt đo được (bộ nhớ nhúng, đệm cỡ cố định). Chuỗi dài mà sao chép nhiều thì tối ưu bằng truyền `const std::string&` hoặc `std::string_view` ([Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md)) và `std::move`, không phải bằng COW tự viết.

!!! info "Bạn biết Go?"
    Chuỗi Go là bất biến, nên chia sẻ vốn an toàn: mình chạy `unsafe.Sizeof("xin chao")` ra **16** (con trỏ và độ dài) và `t := s` cho cùng địa chỉ dữ liệu (`unsafe.StringData(s) == unsafe.StringData(t)` là `true`, go 1.27.2). Đó chính là điều COW muốn đạt, nhưng `std::string` sửa được (`s[0] = 'X'`) nên không chia sẻ ngầm được. Go cũng không có SSO; chuỗi ngắn vẫn nằm ở nơi `string` trỏ tới. Muốn sửa thì chuyển sang `[]byte` (như `String` đề 1 sửa trên vùng riêng).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Tự viết một lớp `String`. Những hàm nào bắt buộc và vì sao?"
    Lớp giữ tài nguyên (khối heap) nên theo Rule of 5 phải tự viết: hàm hủy (`delete[]`), hàm tạo sao chép và gán sao chép (sao chép **sâu**, mỗi chuỗi một khối), hàm tạo chuyển và gán chuyển (`noexcept`, cướp con trỏ, đặt nguồn về rỗng). Thêm `c_str()` luôn kết thúc `'\0'`, `size()`, hai bản `operator[]` (const và không const), `operator+=`. Bất biến: `d_[n_] == '\0'` và `n_ <= cap_`.
    **Nối tiếp:** "Vì sao `noexcept` cho hàm chuyển?" Vì `vector<String>` chỉ chuyển phần tử khi tăng khối nếu hàm chuyển hứa không ném ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)); không có `noexcept` thì nó chép từng chuỗi.

??? question "`operator=` phải xử lý `s = s` thế nào? Gán chuyển có khác không?"
    Gán sao chép: xin khối mới **trước**, chép, rồi trả khối cũ; thứ tự đó làm tự gán an toàn mà không cần `if`, và còn giữ nguyên chuỗi cũ nếu `new` ném ngoại lệ. Gán chuyển thì **phải** kiểm `this != &o`: không kiểm thì `c = std::move(c)` trả khối rồi cướp từ chính mình, chuỗi thành rỗng (mình chạy ra đúng vậy).
    **Nối tiếp:** "`s += s` thì sao?" Nguồn nằm trong khối sắp trả, nên phải chép chữ sang khối mới **xong rồi mới** `delete[]`; trả trước là đọc vùng đã trả.

??? question "Small string optimization là gì? Ngưỡng là bao nhiêu và chuẩn quy định không?"
    Chừa trong đối tượng một đệm nhỏ để chứa chuỗi ngắn, khỏi xin heap. Trên g++ 11 `sizeof(std::string)` là 32 và ngưỡng là 15 ký tự (mình đo: 15 ký tự 0 lần xin, 16 ký tự 1 lần), nhưng **chuẩn không quy định** có SSO hay ngưỡng, nên đó là chuyện của từng thư viện. Cách cài kiểu này dùng con trỏ vào đệm của chính đối tượng và `union` cho ô sức chứa với đệm.
    **Nối tiếp:** "Có hệ quả gì với move?" Chuyển chuỗi ngắn phải chép đệm chứ không trao tay, nên con trỏ `c_str()` lấy trước khi chuyển không trỏ vào đối tượng mới; chỉ chuỗi dài mới trao tay con trỏ.

??? question "Copy-on-write là gì, vì sao `std::string` C++11 không dùng nữa?"
    Sao chép chỉ tăng bộ đếm chung, chữ chỉ được chép khi ai đó sửa. C++11 không "cấm COW" bằng một câu, nhưng (theo trí nhớ, nên nói kèm "tôi nhớ là") chuẩn đòi con trỏ, tham chiếu, iterator tới ký tự không bị mất hiệu lực khi gọi `operator[]`, `at`, `begin`..., và đòi các hàm đó tốn thời gian hằng. COW thì `operator[]` không-const trên chuỗi đang chung phải tách bản riêng, tức chép cả chuỗi và bỏ lại con trỏ cũ trỏ vào khối cũ (mình chạy ra `con[0] = a` trong khi `std::string` ra `X`). Thêm nữa bộ đếm chung phải nguyên tử. SSO làm sao chép chuỗi ngắn đã rẻ sẵn.
    **Nối tiếp:** "Vậy copy chuỗi dài lớn nhiều lần thì sao?" Tránh sao chép: truyền `const std::string&` hay `string_view`, hoặc `std::move` khi đã xong với nguồn.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên ô `'\0'` hoặc chỉ chép `n` byte"
    Cấp `n` thay vì `n + 1`, hoặc `memcpy` thiếu một byte, thì `c_str()` đọc lố. Trình biên dịch không bắt lỗi này; mình chạy với AddressSanitizer ra `heap-buffer-overflow` ngay trong `strlen`. Viết quen: **luôn cấp `cap + 1` và ghi `'\0'` sau mỗi lần đổi nội dung**.

!!! warning "Lỗi 2: Gán và nối chính mình"
    Trả khối cũ trước khi chép (gán) hoặc trước khi chép nguồn (nối) làm `s = s` mất chữ, `s += s` đọc vùng đã trả. Trên bảng trắng, nói to: "xin trước, chép, **trả sau cùng**", và thử `s = s`, `s += s`, `s = std::move(s)` trong đầu trước khi nộp.

!!! warning "Lỗi 3: Quên rằng SSO cần hàm sao chép/chuyển tự viết"
    Có hàm hủy và nghĩ xong. Với con trỏ vào chính đệm, chép nông cho bản sao một con trỏ trỏ vào đối tượng khác (mình chạy: `stack-use-after-scope`). Nói luôn khi giải thích: "SSO làm Rule of 5 **bắt buộc hơn**, không bớt".

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="80" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Lớp `String` giữ `char* d_` xin bằng `new char[...]`, chỉ có hàm tạo từ `const char*` và hàm hủy `delete[] d_`. Chuyện gì xảy ra với đoạn dưới?

```text
{
    String a("abc");
    String b = a;
}
```

- Không biên dịch được, vì lớp có hàm hủy tự viết thì bắt buộc có hàm sao chép
- Hai đối tượng giữ cùng một khối, khối bị trả hai lần (double-free)
- `b` có khối riêng vì trình biên dịch tự sinh phép sao chép sâu cho con trỏ
- `b` rỗng vì sao chép mặc định không đụng tới con trỏ và độ dài

<p class="giai-thich" markdown>Hàm sao chép tự sinh chép từng thành viên, kể cả con trỏ, nên `b.d_` bằng `a.d_`: một khối, hai chủ; hai hàm hủy cùng `delete[]` một địa chỉ. Không báo lỗi biên dịch vì sao chép nông hoàn toàn hợp lệ về cú pháp, đó là lý do Rule of 3 phải do người viết nhớ. Trình biên dịch không biết quyền sở hữu nên không tự sao chép sâu. Và `b` không rỗng: nó nhận y nguyên con trỏ và độ dài.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Dùng `String` của đề 1 (sức chứa tăng gấp đôi: `max(độ dài mới, sức chứa × 2)`, chuỗi rỗng ban đầu sức chứa 0) với bộ đếm `operator new`. Đoạn dưới xin heap mấy lần?

```text
String s;
s += 'a'; s += 'b'; s += 'c'; s += 'd'; s += 'e';
```

- Một lần, vì lần đầu đã xin sẵn đủ chỗ cho cả năm ký tự
- Năm lần, vì mỗi lần `+=` một ký tự đều xin một khối mới
- Ba lần, vì chỉ cần các sức chứa 1, 2 và 4 là xong
- Bốn lần, với các sức chứa lần lượt là 1, 2, 4 rồi 8

<p class="giai-thich" markdown>Ký tự thứ nhất cần 1 > 0 nên xin sức chứa 1; thứ hai cần 2 > 1 nên xin 2; thứ ba cần 3 > 2 nên xin 4; thứ tư nằm vừa trong 4, không xin; thứ năm cần 5 > 4 nên xin 8. Cộng lại 4 lần. Không có chuyện xin sẵn một lần vì ban đầu sức chứa là 0. Năm lần là cách xin vừa đủ (mình đã chạy bản đó: 100 ký tự xin 100 lần). Ba lần quên rằng ký tự thứ năm vượt khối 4.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Phép gán chuyển dưới đây không kiểm `this != &o`. Sau `c = std::move(c);` điều nào đúng?

```text
String& operator=(String&& o) noexcept {
    delete[] d_;
    d_ = o.d_;  n_ = o.n_;  cap_ = o.cap_;
    o.d_ = nullptr;  o.n_ = o.cap_ = 0;
    return *this;
}
```

- `c` thành chuỗi rỗng, chữ cũ mất, và không có lỗi bộ nhớ nào bị báo
- `c` giữ nguyên chữ vì cướp từ chính mình thì không đổi gì
- Chương trình trả khối hai lần và AddressSanitizer báo double-free
- Chương trình đọc khối đã trả và AddressSanitizer báo heap-use-after-free

<p class="giai-thich" markdown>`o` là chính `*this`: `delete[]` trả khối, `d_ = o.d_` chép con trỏ vừa trả sang chính nó, rồi `o.d_ = nullptr` cũng làm `d_` thành `nullptr`, và `n_`, `cap_` về 0. Kết quả là chuỗi rỗng, mình chạy ra đúng vậy. Giữ nguyên chữ là sai vì khối đã bị trả. Không double-free, vì khối chỉ bị trả một lần; không use-after-free, vì sau `delete[]` ta chỉ đọc các thành viên của đối tượng, không đọc khối. Đây là lỗi mất dữ liệu im lặng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Trên g++ 11, đoạn dưới in gì cho `p == t.c_str()`?

```text
std::string s = "abc";
const char* p = s.c_str();
std::string t = std::move(s);
std::cout << (p == t.c_str());
```

- `1`, vì chuyển luôn trao tay con trỏ nên `t` dùng đúng khối của `s`
- `0`, vì chữ ngắn nằm trong `s`, còn `t` có đệm riêng nên `p` lệch khỏi `t`
- Không biên dịch được, vì `std::move(s)` làm `s` mất luôn cả hàm `c_str()`
- `0` hoặc `1` tùy lần chạy, vì địa chỉ của chuỗi thay đổi ngẫu nhiên

<p class="giai-thich" markdown>Với chuỗi ngắn, chữ nằm ngay trong đối tượng `s`, nên chuyển phải chép sang đệm của `t`; `p` vẫn trỏ vào `s`, không bằng `t.c_str()`. Mình chạy ra `0` (còn chuỗi 40 ký tự thì ra `1`, vì con trỏ heap được trao tay). Trao tay con trỏ chỉ xảy ra với chuỗi dài. `std::move` không đổi biến `p`, và kết quả không phụ thuộc lần chạy vì so hai địa chỉ phụ thuộc vào cách bố trí đối tượng, không vào ngẫu nhiên. Dòng đó vẫn biên dịch và chạy bình thường: `s` chỉ rơi vào trạng thái hợp lệ nhưng chưa xác định, và `c_str()` của `t` dùng được.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Một người đề nghị cài `std::string` kiểu copy-on-write để sao chép rẻ. Lý do đúng nhất khiến cách này không còn hợp lệ từ C++11 là gì?

- COW làm `size()` thành O(n) vì phải đếm lại chữ chung mỗi lần gọi
- COW không thể giữ ký tự `'\0'` ở cuối nên `c_str()` không cài được
- Chuẩn cấm hai đối tượng cùng trỏ vào một khối bộ nhớ, dù khối chỉ để đọc
- `operator[]` phải tách bản riêng, làm con trỏ đã lấy trước đó lệch chỗ

<p class="giai-thich" markdown>Chuẩn C++11 (theo trí nhớ, như đã hedge trong bài) đòi `operator[]` không làm mất hiệu lực con trỏ, tham chiếu, iterator đã lấy. COW khi chuỗi đang chung buộc `operator[]` không-const chép chữ sang khối riêng, nên con trỏ cũ vẫn trỏ vào khối cũ; mình chạy ra `con[0] = a` trong khi `std::string` ra `X`. `size()` thì vẫn là một ô độ dài, O(1), nên không liên quan. `'\0'` và `c_str()` COW cài được bình thường. Và chuẩn không cấm chia sẻ bộ nhớ (`shared_ptr` ở khắp nơi); nó chỉ đặt các yêu cầu mà COW khó thỏa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** `SString` của đề 2 (ngưỡng 15 ký tự, đệm 16 byte), với bộ đếm `operator new`. Đoạn dưới xin heap mấy lần?

```text
SString s("123456789012345");   // đúng 15 ký tự
SString t = s;
t += 'x';
SString u = std::move(t);
```

- Một lần, ở `t += 'x'` khi chuỗi vượt 15 ký tự
- Không lần nào, vì `SString` không bao giờ xin heap
- Hai lần, ở hàm tạo sao chép của `t` và ở `+=`
- Ba lần, mỗi dòng có một khởi tạo hoặc nối đều xin một lần

<p class="giai-thich" markdown>`s` có 15 ký tự nên nằm vừa đệm: 0 lần. Sao chép `t = s` chép 15 ký tự vào đệm của `t`: 0 lần. `t += 'x'` thành 16 ký tự, vượt ngưỡng, xin heap: 1 lần. Chuyển `u` lấy con trỏ heap của `t`: 0 lần. Tổng 1. Không bao giờ xin heap là sai vì chuỗi dài vẫn ra heap. Sao chép chuỗi ngắn không xin vì chữ chép vào đệm có sẵn. Chuyển chuỗi dài chỉ trao con trỏ, không xin.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Một hàm nhận chuỗi khoảng 200 byte, bị gọi hàng triệu lần và hiện sao chép chuỗi mỗi lần gọi. Profiler cho thấy `operator new` và `memcpy` chiếm phần lớn thời gian. Bạn nên làm gì?

- Tự cài `SString` với đệm 256 byte để chuỗi 200 byte cũng nằm ngay trong đối tượng
- Tự cài `std::string` kiểu copy-on-write bằng `shared_ptr` để sao chép chỉ tăng bộ đếm
- Truyền `const std::string&` hoặc `string_view`, và `std::move` khi nguồn hết dùng
- Thay `std::string` bằng mảng `char[256]` ở mọi nơi để khỏi phải cấp phát heap

<p class="giai-thich" markdown>Gốc vấn đề là sao chép thừa; bỏ sao chép (tham chiếu hoặc view) rẻ hơn mọi cách làm sao chép rẻ hơn, và `std::move` bỏ sao chép khi chuyển quyền. Đệm 256 byte làm mọi đối tượng chuỗi phình to và SSO không sinh ra để vậy. COW tự viết mang các lỗi đã thấy (tham chiếu lây, bộ đếm nguyên tử). Mảng `char[256]` cứng làm mất độ dài linh hoạt và dễ tràn khi chuỗi dài hơn.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `String` đề 1: ba thành viên (con trỏ, độ dài, sức chứa), bất biến `d_[n_] == '\0'`, cấp `cap + 1` byte; Rule of 5: hủy `delete[]`, sao chép **sâu**, chuyển `noexcept` (cướp rồi đặt nguồn về rỗng); gán sao chép "xin trước, trả sau" nên tự gán an toàn, gán chuyển phải kiểm `this != &o` (bỏ kiểm: `c = std::move(c)` thành chuỗi rỗng, im lặng). Sạch với `-fsanitize=address,undefined`.
2. `+=` xin `max(độ dài mới, 2 × sức chứa)` và trả khối cũ **sau cùng** (để `s += s` đúng); nối chuỗi rỗng thì thoát sớm, vì chuỗi chưa cấp phát có `d_ == nullptr` (bỏ kiểm: `SEGV`): nối 100 ký tự xin 8 lần thay vì 100 (đếm bằng `operator new` thay thế); xin vừa đủ thì n lần, chép lại cả chuỗi mỗi lần.
3. Bốn lỗi đã chạy thật: thiếu ô `'\0'` (`heap-buffer-overflow` ở `strlen`), tự gán khi trả trước (mất chữ, `heap-buffer-overflow`), sao chép nông (`attempting double-free`), chép con trỏ vào đệm của đối tượng khác (`stack-use-after-scope`).
4. SSO đề 2: `d_` trỏ vào `buf_` của chính mình hoặc vào heap; `union { cap_; buf_[16]; }` cho `sizeof` 32 bằng `std::string` của g++ 11; chuỗi tới 15 ký tự 0 lần xin, 16 ký tự 1 lần, đếm giống `std::string` ở mọi hàng đã đo. Chuẩn **không** quy định SSO hay ngưỡng; chuyển chuỗi ngắn phải chép đệm nên con trỏ cũ không còn trỏ vào đối tượng mới.
5. COW: sao chép chỉ tăng bộ đếm, sửa mới chép. COW ngây thơ hỏng hai chỗ (đã chạy: tham chiếu cũ ghi lây `Xbc`/`Xbc`, con trỏ cũ `con[0] = a`). Theo trí nhớ, C++11 đòi `operator[]`, `at`, `begin`... không làm mất hiệu lực con trỏ/tham chiếu/iterator và tốn thời gian hằng, mà COW phải tách bản (chép cả chuỗi) ở các hàm đó; bộ đếm chung còn phải nguyên tử. `-D_GLIBCXX_USE_CXX11_ABI=0` cho bản cũ: `sizeof` 8, chép chuỗi dài 0 lần xin. Trong sản phẩm đừng tự cài; tránh sao chép bằng `const&`, `string_view`, `std::move`.
