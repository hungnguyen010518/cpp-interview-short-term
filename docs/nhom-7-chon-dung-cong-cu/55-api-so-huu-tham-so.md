# Bài 55 — Thiết kế hàm: truyền tham số và sở hữu rõ ràng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nhìn một chữ ký hàm là đọc ra **ai sở hữu, ai chỉ nhìn, ai được sửa**; chọn tham số bằng một cây hỏi ba câu thay vì thuộc lòng quy tắc, và biết rõ khi nào mỗi lựa chọn là **sai** (không chỉ "kém tối ưu").
    - Giải thích bằng số liệu thật (đếm `copy`/`move`, đếm lần xin heap) vì sao "nhận theo giá trị rồi `std::move`" (sink parameter) thắng `const&` khi hàm sẽ **giữ** đối số, và vì sao nó thua khi hàm chỉ **gán lại** nhiều lần.
    - Chọn kiểu trả về (giá trị, `unique_ptr`, tham chiếu, struct nhiều giá trị) và nói được vì sao `return std::move(local)` làm chậm, vì sao `return b ? x : y;` lại **sao chép**.
    - Tránh các bẫy sống-ngắn-hơn-nguồn (`string_view`, `const&` nhận tạm, getter trên đối tượng tạm), hiểu `const` ở hàm thành viên cùng `mutable` + mutex, rồi trả lời mười tình huống thiết kế chữ ký như khi phỏng vấn.

**Bạn cần biết trước:** [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (bốn cách truyền, `const&`, trả tham chiếu cục bộ, hàm thành viên `const`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, bảng chọn tham số cho cây), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (hàm tạo sao chép), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`, `T&&`, copy elision, `return v;`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`optional`, structured binding, `string_view`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, lớp `BoDem`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, tham số luồng bị sao chép).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md). Hai đầu bếp trao việc cho nhau bằng một **phiếu giao nhận**, và phiếu chỉ có vài loại. Loại "**xem thôi**": đưa bản công thức cho người kia đọc tại chỗ, không được viết lên đó (`const&`). Loại "**sửa tại thớt**": mời người kia tới thớt của mình và cho phép chỉnh món đang nằm đó (`T&`). Loại "**nhận hẳn**": trao luôn nguyên liệu, từ giờ món đó thuộc về người nhận (`unique_ptr`, hoặc giá trị rồi `std::move`).

Phiếu càng rõ thì bếp càng ít cãi nhau. Nhìn phiếu "xem thôi" là biết người nhận không mang món đi; nhìn phiếu "nhận hẳn" là biết người giao không được đụng vào nữa. Chữ ký hàm trong C++ chính là tờ phiếu đó: nó nói ra **ai sống lâu hơn ai** mà không cần đọc thân hàm.

!!! info "Chỗ nào ví von phiếu giao nhận không còn đúng?"
    Phiếu ngoài đời do người đọc tự giữ lời. Với `const&`, trình biên dịch **bắt** bạn giữ lời (sửa là lỗi biên dịch), nhưng nó **không** kiểm tra chuyện "người kia còn đứng đó không": đưa bản công thức đã bị xé (đối tượng đã chết) thì trình biên dịch vẫn chấp nhận. Phần lớn bài này nói về chỗ hở đó.

## 📖 Giải thích

### 1. Ba câu hỏi trước khi viết chữ ký

[Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) và [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) đã cho bốn cách truyền. Bài này gộp lại thành một cây hỏi, vì câu hỏi phỏng vấn thường là "bạn sẽ khai báo hàm này thế nào?" chứ không phải "`const&` là gì".

```text
Hàm làm gì với đối số này?
├─ Chỉ ĐỌC
│   ├─ kiểu nhỏ, sao chép rẻ (int, double, string_view, con trỏ) ──► theo GIÁ TRỊ
│   └─ kiểu to / sao chép đắt ───────────────────────────────────► const T&
├─ SỬA cho người gọi thấy ───────────────────────────────────────► T&   (đầu ra / vào-ra)
├─ GIỮ LẠI (lưu vào thành viên, đẩy vào hàng đợi, đưa sang luồng khác)
│   ├─ kiểu sao chép được (string, vector...) ────────────────► theo GIÁ TRỊ rồi std::move (gọi là sink, mục 3)
│   └─ đối tượng không sao chép được (unique_ptr, thread) ────► theo GIÁ TRỊ (người gọi std::move)
└─ "Có thể không có" ──► T* (nullptr = không có)  hoặc  std::optional<T> (nếu chép rẻ)
```

Chữ "kiểu nhỏ" có số đo: mình chạy `sizeof` trên g++ 11 (x86-64): `int` 4 byte, `double` 8, `std::string_view` 16, `std::unique_ptr<int>` 8, `std::string` 32, `std::vector<int>` 24. Đây là số **thường gặp**, không phải chuẩn bảo đảm. Quy ước thông dụng: kiểu tới cỡ 16 byte mà việc chép chỉ là chép vài byte (không phải xin heap) thì nhận theo giá trị; to hơn nhiều, hoặc chép phải xin heap, thì `const&`.

### 2. Bảng chọn tham số

| Tham số | Dùng khi | Người gọi viết | **Không** dùng khi |
|---|---|---|---|
| `int n`, `double x`, `std::string_view s` | Chỉ đọc, kiểu nhỏ | `f(n)` | Kiểu to (chép đắt) |
| `const T&` | Chỉ đọc, kiểu to | `f(obj)` | Hàm sẽ **giữ** đối số (bắt buộc chép bên trong) |
| `T&` | Sửa đối số, đầu ra / vào-ra | `f(obj)` (không thấy nó bị sửa!) | Đầu ra thật sự: trả giá trị (mục 7) |
| `T` rồi `std::move` (sink) | Hàm giữ đối số; chép rẻ khi người gọi truyền tạm | `f(obj)` chép, `f(std::move(obj))` chuyển | Chỉ đọc; hoặc **gán lại** nhiều lần (mục 4) |
| `std::unique_ptr<T>` | Nhận sở hữu một đối tượng heap | `f(std::move(p))` | Chỉ **dùng** đối tượng: nhận `const T&` hoặc `T*` |
| `T&&` | Nhận sở hữu, chỉ nhận rvalue | `f(std::move(obj))` | Muốn nhận cả biến thường (sẽ bị từ chối) |
| `const T*` / `T*` | Có thể không có (`nullptr`) | `f(&obj)`, `f(nullptr)` | Luôn có đối số: dùng tham chiếu |
| `std::string_view` | Quan sát chuỗi bất kỳ, không giữ | `f("abc")`, `f(s)` | **Lưu lại**; hoặc cần chuỗi kết thúc `'\0'` (mục 5) |
| `std::optional<T>` | Giá trị tùy chọn, `T` chép rẻ | `f(5)`, `f(std::nullopt)` | `T` to hoặc đã có sẵn ở nơi khác: dùng `T*` |

!!! info "Bạn biết Go?"
    Go không có `const&` hay `std::move`: **mọi thứ truyền theo giá trị**. Mình chạy thử: sửa một `struct` trong hàm nhận giá trị thì người gọi vẫn thấy `1`; qua con trỏ `*Hop` thì thành `99`; một `[]int` đưa vào hàm cho sửa phần tử được (`[99 2 3]`) nhưng `append` trong hàm không làm người gọi dài ra (độ dài vẫn 3), vì slice là một bộ (con trỏ, độ dài, sức chứa) được chép. Go không cần câu hỏi "ai sống lâu hơn ai" vì bộ gom rác giữ mọi thứ còn được trỏ tới; C++ không có người dọn đó, nên chữ ký phải nói thay.

### 3. Sink parameter: hàm sẽ giữ đối số

Một **sink parameter** (tham số "bồn", chảy vào rồi nằm lại) là tham số mà hàm sẽ **giữ**: hàm tạo lưu tên vào thành viên là ví dụ kinh điển. Hai cách viết cũ đều có chỗ dở: `const std::string&` rồi chép vào thành viên thì **luôn chép**, kể cả khi người gọi đưa một chuỗi tạm sắp chết; `std::string&&` thì không nhận được biến có tên. Cách hiện đại là **nhận theo giá trị rồi `std::move` vào thành viên**.

Ta đếm thật. `Goi` in `copy`/`move` mỗi khi hàm tạo sao chép/di chuyển ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)) chạy. Ba lớp lưu một `Goi` theo ba cách; hàm mẫu `thu<K>` chạy cùng một thử nghiệm cho từng lớp `K` (hàm mẫu: [Bài 34](../nhom-4-oop-patterns/34-template.md)). `Goi{}` dựng một `Goi` tạm.

```cpp
#include <iostream>
#include <utility>

struct Goi {
    int x = 0;
    Goi() = default;
    Goi(const Goi& o) : x(o.x) { std::cout << " copy"; }          // (1)
    Goi(Goi&& o) noexcept : x(o.x) { std::cout << " move"; }      // (2)
};

struct KhoConstRef {
    Goi g;
    KhoConstRef(const Goi& v) : g(v) {}                           // (3) nhận const&, chép vào thành viên
};

struct KhoSink {
    Goi g;
    KhoSink(Goi v) : g(std::move(v)) {}                           // (4) nhận theo giá trị rồi move
};

struct KhoHaiHam {
    Goi g;
    KhoHaiHam(const Goi& v) : g(v) {}                             // (5) một hàm tạo cho lvalue
    KhoHaiHam(Goi&& v) : g(std::move(v)) {}                       // (6) một hàm tạo cho rvalue
};

template <class K>
void thu(const char* ten) {
    Goi a;
    std::cout << ten << " | lvalue   :";
    K k1(a);                                                      // (7) truyền biến có tên
    std::cout << "\n" << ten << " | std::move:";
    Goi b;
    K k2(std::move(b));                                           // (8) truyền std::move(b)
    std::cout << "\n" << ten << " | tam      :";
    K k3(Goi{});                                                  // (9) truyền giá trị tạm
    std::cout << "\n";
}

int main() {
    thu<KhoConstRef>("const&  ");
    thu<KhoSink>    ("sink    ");
    thu<KhoHaiHam>  ("2 ham   ");
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số lần chép/move |
|---|---|---|
| (3) | `v` là biệt danh của đối số, `g(v)` chạy hàm tạo sao chép (1) dù đối số là tạm | luôn 1 copy |
| (4)+(7) | Đối số là biến có tên: tham số `v` được **sao chép** ra, rồi `std::move(v)` đưa vào `g` | 1 copy + 1 move |
| (4)+(8) | Đối số là `std::move(b)`: `v` được **di chuyển** ra, rồi lại move vào `g` | 2 move |
| (4)+(9) | Đối số là giá trị tạm `Goi{}`: C++17 dựng thẳng `v`, không chép/di chuyển; chỉ còn move vào `g` | 1 move |
| (5),(6) | Trình biên dịch chọn hàm tạo khớp: lvalue vào (5), rvalue vào (6) | 1 copy hoặc 1 move |

**Kết quả khi chạy** (g++ 11, `-std=c++17 -Wall`):

```text
const&   | lvalue   : copy
const&   | std::move: copy
const&   | tam      : copy
sink     | lvalue   : copy move
sink     | std::move: move move
sink     | tam      : move
2 ham    | lvalue   : copy
2 ham    | std::move: move
2 ham    | tam      : move
```

Đọc bảng: `const&` chép cả ba lần. Hai hàm tạo tối ưu nhất (không thừa phép nào) nhưng phải viết **hai** hàm cho mỗi tham số, và với hai tham số là bốn hàm. Sink chỉ **thừa một lần `move`** so với hai hàm, mà `move` thường rẻ (đổi vài con trỏ, [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)). Vì thế sink là mặc định cho "hàm sẽ giữ". Với kiểu **không sao chép được** (`unique_ptr`, `std::thread`), nhận theo giá trị là cách duy nhất, và người gọi buộc phải viết `std::move` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)).

!!! warning "Hay nhầm"
    Đừng thấy `std::move` mà tưởng "hàm này nhanh hơn". Sink vẫn **chép một lần** khi người gọi đưa biến có tên (dòng `sink | lvalue`). Cái được là: không chép thừa khi người gọi đưa tạm hoặc đã `std::move`.

### 4. Khi nào KHÔNG nên sink: gán lại nhiều lần

Sink hợp với **hàm tạo** (đối tượng chưa có gì). Với hàm **gán lại** một thành viên đã có chuỗi, `const&` có thể thắng, vì phép gán chép vào được **vùng nhớ cũ** của `ten_` nếu còn đủ chỗ, còn sink đã buộc cấp phát một chuỗi mới ngay ở tham số. Ta đếm lần xin heap thật bằng cách thay `operator new` (hàm xin heap mà `new` và `std::string` đều gọi) bằng bản có bộ đếm; [Bài 58](58-bo-nho-nang-cao.md) sẽ nói kỹ hơn, ở đây chỉ dùng như thước đo.

```cpp
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <utility>

int soLanXin = 0;                                     // (1) đếm số lần xin heap

void* operator new(std::size_t n) {                   // (2) thay hàm xin heap mặc định: đếm rồi gọi malloc
    ++soLanXin;
    void* p = std::malloc(n);
    if (!p) throw std::bad_alloc();                   // hết bộ nhớ thì ném ngoại lệ
    return p;
}
void operator delete(void* p) noexcept { std::free(p); }

class HoSo {
public:
    void datTenCRef(const std::string& t) { ten_ = t; }              // (3) nhận const&, gán chép
    void datTenSink(std::string t) { ten_ = std::move(t); }          // (4) nhận giá trị, gán move
private:
    std::string ten_;
};

int main() {
    std::string ten(100, 'a');                        // (5) chuỗi 100 ký tự: không nằm trong bộ đệm nhỏ
    HoSo h;
    h.datTenCRef(ten);                                // lần đầu: ten_ chưa có chỗ
    int truoc = soLanXin;
    for (int i = 0; i < 1000; ++i) h.datTenCRef(ten);                // (6)
    std::cout << "const& : " << soLanXin - truoc << " lan xin heap trong 1000 lan goi\n";
    h.datTenSink(ten);
    truoc = soLanXin;
    for (int i = 0; i < 1000; ++i) h.datTenSink(ten);                // (7)
    std::cout << "sink   : " << soLanXin - truoc << " lan xin heap trong 1000 lan goi\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Heap lúc này |
|---|---|---|
| (5) | `ten` có 100 ký tự, vượt bộ đệm nhỏ nằm sẵn trong `std::string` (viết tắt SSO), nên chuỗi sống ở heap | 1 vùng cho `ten` |
| (6) | Mỗi lần `ten_ = t`: `ten_` đã có vùng đủ rộng, phép gán chép ký tự vào đó | không xin thêm |
| (7) | Mỗi lần `datTenSink(ten)`: tham số `t` là **chuỗi mới**, phải xin một vùng heap đủ chứa 100 ký tự; sau đó move vào `ten_` rồi vùng cũ của `ten_` bị trả | mỗi lần một xin |

**Kết quả khi chạy:**

```text
const& : 0 lan xin heap trong 1000 lan goi
sink   : 1000 lan xin heap trong 1000 lan goi
```

Bài học là **điều kiện đúng/sai**, không phải "sink tệ": sink tốt khi hàm tạo hoặc khi người gọi hay đưa giá trị tạm; `const&` tốt khi gán lại lên một đối tượng đã có sức chứa và người gọi hay đưa biến có tên. Không chắc thì đo, vì với `int` hay chuỗi ngắn (nằm trong bộ đệm nhỏ) sự khác biệt này biến mất.

### 5. Quan sát không sở hữu: `string_view` và `span`

[Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) đã nêu hai chỗ làm `string_view` treo: **trả** nó khi nó nhìn vào một `std::string` cục bộ của hàm (hàm trả về thì chuỗi chết), và gán nó từ một chuỗi tạm. Hai điều dưới đây là phần còn thiếu, và đều hay bị hỏi.

**Bẫy 1: `string_view` không bảo đảm có `'\0'` ở cuối.** Cửa sổ cắt giữa chuỗi thì ký tự ngay sau cửa sổ là ký tự bình thường. Hàm C như `std::printf("%s", ...)` hay `std::fopen` đọc tới khi gặp `'\0'`, nên đọc lố khỏi cửa sổ.

```text
std::string ten = "Nguyen Van An";
std::string_view ho = std::string_view(ten).substr(0, 6);        // cửa sổ "Nguyen"
std::printf("%.*s\n", static_cast<int>(ho.size()), ho.data());   // (1) nói rõ độ dài
std::printf("%s\n", ho.data());                                  // (2) chờ '\0'
```

Mình bọc đoạn này vào `main`, biên dịch và chạy: (1) in `Nguyen` (`%.*s` nhận độ dài từ đối số), (2) in cả `Nguyen Van An`, vì `%s` không biết độ dài cửa sổ và đi tiếp tới `'\0'` cuối `ten`.

Ở đây (2) "tình cờ" an toàn vì `ten` vẫn có `'\0'` cuối. Đổi sang chuỗi nguồn không có `'\0'` thì đọc lố thật sự là hành vi không xác định. Quy tắc: **hàm cần chuỗi kết thúc `'\0'` (gọi API C) thì nhận `const std::string&`** (đảm bảo `c_str()`), không nhận `string_view`.

**Bẫy 2: lưu `string_view` làm thành viên.** Tham số `string_view` ổn vì người gọi giữ chuỗi sống suốt lúc gọi; thành viên `string_view` thì không ai bảo đảm gì. Mình chạy ví dụ dưới (dùng kết quả là hành vi không xác định):

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
#include <string_view>

struct Nhan {
    std::string_view ten;
    Nhan(std::string_view t) : ten(t) {}   // lưu cửa sổ, không lưu chuỗi
};

int main() {
    Nhan n(std::string("mot chuoi du dai de khong nam trong SSO"));   // chuỗi tạm chết cuối dòng
    std::cout << n.ten << "\n";
    return 0;
}
```

Mình biên dịch sạch cảnh báo. Chạy trần một lần: in vài byte rác rồi `de khong nam trong SSO` (đổi theo lần chạy). Với `-fsanitize=address`: `heap-use-after-free`, đọc 39 byte. Nếu lớp cần **giữ** chuỗi thì thành viên phải là `std::string` (sink ở mục 3).

**`std::span`** (C++20, `<span>`) là `string_view` cho mọi dãy liên tiếp: `std::span<const int>` nhận `vector<int>`, `std::array`, mảng C mà không chép, và cũng chỉ là cửa sổ (địa chỉ đầu + số phần tử), nên mọi bẫy của `string_view` đều đúng với nó. Mình biên dịch thử một hàm `tong(std::span<const int>)` với `g++ -std=c++20`: chạy đúng với cả ba kiểu (`10 60 10 5` trên dữ liệu thử); với `-std=c++17` thì lỗi `'span' is not a member of 'std'`. Vì vậy bài này không có khối `span` chạy kiểm tra. Trong C++17, hàm đọc dãy hay viết `const std::vector<int>&`, hoặc cặp `(const int* p, std::size_t n)` nếu cần nhận nhiều loại dãy.

### 6. `const&` nhận giá trị tạm: kéo dài vòng đời tới đâu

Gắn một giá trị tạm trực tiếp vào một **biến** `const&` thì C++ **kéo dài vòng đời** của tạm tới hết phạm vi của biến đó:

```text
std::string layTen() { return "Nguyen Van An"; }
const std::string& r = layTen();      // tạm gắn thẳng vào r: sống tiếp tới hết phạm vi của r
std::cout << r << " " << r.size();    // an toàn
```

Mình bọc vào `main` và chạy: in `Nguyen Van An 13`, sạch cảnh báo.

Điều này **không** áp dụng khi tạm đi qua một hàm trả về tham chiếu. Tạm làm đối số hàm chỉ sống tới hết **câu lệnh**; hàm trả lại tham chiếu tới đối số đó thì `r` giữ một biệt danh của thứ đã chết:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>

const std::string& dai(const std::string& a, const std::string& b) {
    return a.size() >= b.size() ? a : b;             // trả biệt danh của một trong hai đối số
}

int main() {
    const std::string& r = dai(std::string("ngan"), std::string("dai hon nhieu"));   // (1) hai tạm chết cuối dòng
    std::cout << r << "\n";                                                          // (2) đọc chuỗi đã chết
    return 0;
}
```

Mình biên dịch **không cảnh báo** (`-Wall`). Chạy trần: in `dai hon nhieu` và thoát mã 0, tức là **trông như đúng**. Với `-fsanitize=address`: `stack-use-after-scope` ở dòng (2). Đây là dạng lỗi đáng sợ nhất: chạy đúng cho tới ngày thay đổi mức tối ưu hay thêm một dòng code.

Bẫy cùng họ: duyệt kết quả của một getter gọi trên đối tượng tạm. Giả sử có `Tui` là một `struct` giữ `std::vector<std::string> v`, với getter `dsach()` trả `const&` tới `v`, và hàm `taoTui()` trả một `Tui` mới:

```text
for (const std::string& s : taoTui().dsach()) { std::cout << s << "\n"; }
```

Vế phải của dấu `:` được gán vào một biến tham chiếu ẩn, và `Tui` tạm chết ngay khi câu gán đó xong, **trước** thân vòng lặp; `dsach()` trả biệt danh của `v` bên trong `Tui` đã chết. Mình chạy với `-std=c++17`: ASan báo `stack-use-after-scope` ngay ở `begin()`; chạy trần thì kết quả đổi theo lần chạy (có lần in rác không dừng, có lần không in gì). Đề xuất P2718R0 (được nhận vào C++23) kéo dài vòng đời mọi giá trị tạm trong vế phải của `for` kiểu này; mình không kiểm được ở đây (g++ 11 với `-std=c++2b` vẫn báo `stack-use-after-scope` như C++17), nên đừng dựa vào nó: hãy giữ đối tượng ở một biến có tên (`Tui t = taoTui(); for (... : t.dsach())`).

!!! warning "Hay nhầm"
    Hàm trả `const T&` hứa "thứ này sống lâu hơn lời gọi hàm". Tham số `const&` nhận tạm thì **không** có lời hứa đó. Khi viết hàm `const T& chon(const T&, const T&)`, hãy nghĩ tới người gọi truyền tạm; nếu muốn an toàn thì trả **giá trị**.

### 7. Đầu ra: trả giá trị, `T&`, `T*`, `optional`

Hàm cũ kiểu C hay viết `bool phanTich(const std::string& s, int& ra)`: giá trị đầu ra đi qua `T&`. Nơi gọi `phanTich(s, n)` không thấy `n` bị sửa, và `n` phải khai báo trước rồi để khởi tạo dở. Nếu hàm trả được giá trị thì **trả giá trị**: `std::optional<int> phanTich(std::string_view s)` cho biết cả "có hay không" lẫn kết quả ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)).

Tham số `T&` (hoặc `T*`) vẫn có chỗ đứng khi **tái dùng bộ nhớ**: hàm gọi hàng triệu lần với cùng một bộ đệm (`void doc(std::string& bo)` xóa nội dung rồi ghi tiếp, giữ sức chứa như mục 4), hoặc kiểu đầu ra không di chuyển rẻ được.

Với "có thể không có": `std::optional<T>` **chứa một bản** của `T` (chép), và ở C++17 không chứa được tham chiếu (`optional<T&>` không hợp lệ). Vì vậy tra trong container chứa phần tử to thì trả `const T*` trỏ **thẳng vào phần tử** (`nullptr` = không thấy), với điều kiện container sống lâu hơn việc dùng con trỏ; còn phần tử nhỏ (`int`) thì `optional<int>` tự nhiên hơn. Tham số vào cũng tương tự: tùy chọn thì `const Cau_hinh*` với mặc định `nullptr`.

### 8. Kiểu trả về

**Trả theo giá trị** là mặc định, kể cả với vector lớn. Ba tầng bảo vệ (đã gặp ở [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) mục 9): trả giá trị tạm (`return Goi();`) thì từ C++17 **bắt buộc** không chép/di chuyển; trả biến cục bộ có tên thì **được phép** bỏ (NRVO) nhưng không bắt buộc; nếu chưa bỏ được thì thử `move` trước khi chép. Điều Bài 12 chưa đếm là những kiểu `return` **không** hưởng ưu đãi đó. Ta đếm lại trong một chương trình:

```cpp
#include <iostream>
#include <utility>

struct Goi {
    Goi() = default;
    Goi(const Goi&) { std::cout << " copy"; }
    Goi(Goi&&) noexcept { std::cout << " move"; }
};

Goi giaTriTam() { return Goi(); }                    // (1) trả giá trị tạm

Goi coTen() {
    Goi g;
    return g;                                        // (2) trả biến cục bộ (NRVO)
}

Goi tuThamSo(Goi p) { return p; }                    // (3) trả chính tham số

struct Hop {
    Goi g;
    Goi lay() const { return g; }                    // (4) trả thành viên
};

Goi toanTuBaNgoi(bool b) {
    Goi x, y;
    return b ? x : y;                                // (5) ? : giữa hai biến
}

int main() {
    std::cout << "(1) giaTriTam :"; Goi a = giaTriTam();
    std::cout << "\n(2) coTen      :"; Goi b = coTen();
    std::cout << "\n(3) tuThamSo   :"; Goi c = tuThamSo(Goi());
    std::cout << "\n(4) thanh vien :"; Hop h; Goi d = h.lay();
    std::cout << "\n(5) ? :        :"; Goi e = toanTuBaNgoi(true);
    std::cout << "\n";
    (void)a; (void)b; (void)c; (void)d; (void)e;   // (void): để g++ khỏi báo biến không dùng
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Vì sao ra kết quả đó |
|---|---|
| (1) | Giá trị tạm: C++17 bắt buộc dựng thẳng vào `a`, không in gì |
| (2) | NRVO: g++ 11 dựng `g` thẳng trong `b`; chuẩn **cho phép** chứ không bắt, nên đừng viết code phụ thuộc vào nó |
| (3) | Tham số theo giá trị cũng được thử như rvalue khi `return`: một `move` |
| (4) | `g` là thành viên của `h` còn sống sau hàm, không phải biến cục bộ: không move ngầm, không bỏ qua, phải **chép** |
| (5) | Kết quả của `? :` giữa hai lvalue là một lvalue chứ không phải "tên biến", nên không hưởng move ngầm: **chép** |

**Kết quả khi chạy:**

```text
(1) giaTriTam :
(2) coTen      :
(3) tuThamSo   : move
(4) thanh vien : copy
(5) ? :        : copy
```

Hai dòng `copy` là chỗ người ta hay mất điểm. Sửa (5): viết `if (b) return x; return y;` (hai `return`, mỗi cái một biến; mình chạy: một `move`). Sửa (4) khi bạn **muốn lấy hẳn** thành viên ra (đối tượng sau đó bỏ đi): `Goi layVaXoa() { return std::move(g); }`; mình chạy: một `move`. Đây là trường hợp `return std::move(...)` **đúng**: thứ được trả không phải biến cục bộ.

**Đừng `return std::move(bienCucBo);`.** `std::move` biến biểu thức thành rvalue, mà NRVO chỉ áp dụng cho **tên biến cục bộ**, nên bản có `std::move` bị chặn NRVO và phải `move` một lần. Mình biên dịch hàm `{ Goi g; return std::move(g); }` với `-Wall`: g++ 11 cảnh báo thẳng `moving a local object in a return statement prevents copy elision [-Wpessimizing-move]`, chạy ra `move` (so với không in gì ở dòng (2)). Đừng thêm `const` vào kiểu trả về theo giá trị (`const Goi f()`): `Goi y = f();` vẫn không chép, nhưng `x = f();` gọi phép gán **sao chép** thay vì phép gán di chuyển (mình chạy: `copy-gan` so với `move-gan` khi bỏ `const`).

Các kiểu trả khác:

- **`std::unique_ptr<T>`**: tạo đối tượng heap rồi trao quyền sở hữu cho người gọi, hay cần đa hình ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)). Đừng trả `T*` thô khi có chủ sở hữu mới; `unique_ptr` trả về gán được sang `shared_ptr` nếu người gọi cần (xem [Bài 51](51-chon-smart-pointer.md)).
- **`T&` / `const T&`**: chỉ khi thứ được trả **sống lâu hơn lời gọi**: thành viên của đối tượng còn sống, phần tử container, biến `static`, hoặc chính tham số tham chiếu. Biến cục bộ thì không bao giờ ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)). Trả `T&&` gần như luôn là lỗi thiết kế.
- **Nhiều giá trị:** trả `struct` có **tên trường** (`ThuongDu{thuong, du}`) cho đáng đọc; `std::pair`/`std::tuple` (như `pair` nhưng gói được nhiều giá trị) gọn khi chỉ hai ba giá trị và nơi gọi tách bằng structured binding `auto [a, b] = f();` ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)).

!!! info "Bạn biết Go?"
    Go trả nhiều giá trị bằng cú pháp (`q, r := chia(17, 5)`; mình chạy ra `3 2`), nên Go không có tham số ra kiểu C++. `return &h` với `h` cục bộ hợp lệ trong Go (mình chạy: in `5`) vì escape analysis đưa `h` lên heap; C++ trả `unique_ptr` hoặc giá trị để nói rõ ai sở hữu.

### 9. `const` ở hàm thành viên, `mutable` và mutex

[Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) và [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) đã nói: `const` sau danh sách tham số là cam kết "hàm này không sửa đối tượng", và chỉ hàm có chữ đó gọi được qua `const&`. Bài này thêm hai chuyện: ý nghĩa của cam kết, và cái bẫy khi hàm `const` cần khóa mutex.

`const` là lời cam kết về **trạng thái nhìn thấy được**, không nhất thiết là từng bit. Một hàm `doc() const` hoàn toàn có thể sửa một thành viên chỉ để phục vụ nội bộ: khóa mutex, đếm số lần gọi, giữ cache tính trước. Thành viên như vậy khai báo **`mutable`** (sửa được kể cả trong hàm `const`). Vì `lock_guard` phải sửa mutex (khóa/nhả), nên `BoDem` ở [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) muốn có `doc() const` thì mutex phải `mutable`.

```cpp
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class BoDem {
public:
    void tang() {                                       // (1) có sửa: không const
        std::lock_guard<std::mutex> giu(khoa_);
        ++dem_;
    }
    int doc() const {                                   // (2) chỉ đọc về mặt ý nghĩa: const
        std::lock_guard<std::mutex> giu(khoa_);         // (3) khóa mutex: cần mutable
        return dem_;
    }

private:
    mutable std::mutex khoa_;                           // (4) mutable: sửa được cả trong hàm const
    int dem_ = 0;
};

void inKetQua(const BoDem& b) {                         // (5) chỉ cầm const&: vẫn gọi được doc()
    std::cout << "doc() qua const& = " << b.doc() << "\n";
}

int main() {
    BoDem b;
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&b] {
            for (int i = 0; i < 1000; ++i) {
                b.tang();
                (void)b.doc();                          // (6) vừa ghi vừa đọc từ nhiều luồng
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();
    inKetQua(b);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Mutex lúc này |
|---|---|---|
| (6) | Bốn luồng gọi `tang()` rồi `doc()` liên tục trên cùng `b` | một luồng cầm một lúc |
| (3) | `doc()` là `const` nhưng `khoa_` là `mutable` nên `lock_guard` khóa được | luồng gọi `doc()` cầm |
| (5) | Sau `join`, `inKetQua` nhận `const BoDem&` và gọi `doc()`: được, vì `doc()` có `const` | không ai cầm |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
doc() qua const& = 4000
```

**Thử thay đổi 1: bỏ chữ `mutable` ở (4).** Mình đã thử, lỗi biên dịch: `binding reference of type 'std::lock_guard<std::mutex>::mutex_type&' {aka 'std::mutex&'} to 'const std::mutex' discards qualifiers`. Trong hàm `const`, thành viên là `const`, mà khóa cần sửa mutex.

**Thử thay đổi 2: trong `inKetQua` thêm `b.tang();`.** Lỗi biên dịch: `passing 'const BoDem' as 'this' argument discards qualifiers`. Đó là lời cam kết `const&` được giữ giúp bạn.

Quy ước đa luồng cần nhớ: thư viện chuẩn bảo đảm gọi các hàm `const` của **kiểu chuẩn** đồng thời từ nhiều luồng là an toàn, và người dùng cũng kỳ vọng như vậy ở kiểu của bạn. Cho nên hàm `const` mà sửa dữ liệu `mutable` thì **chính bạn** phải bảo vệ (mutex hoặc `atomic`), nếu không hàm trông "chỉ đọc" nhưng gây data race ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).

!!! warning "Hay nhầm"
    Đa luồng thêm một lý do tránh tham số **sống ngắn hơn luồng**: hàm đưa việc cho luồng khác rồi trả về ngay, mà nhận `const std::string&` hay `std::string_view` rồi lưu lại (hoặc cho lambda bắt tham chiếu) thì luồng kia đọc thứ đã chết khi người gọi xong. Dữ liệu đi sang luồng khác nên được **giữ bản của nó** (tham số theo giá trị, `std::move` vào). [Bài 52](52-smart-pointer-da-luong.md) làm kỹ phần này với `shared_ptr`.

## 💻 Ví dụ code

### Mười tình huống thiết kế chữ ký

Mười hàm dưới đây chọn chữ ký theo cây ở mục 1, mỗi hàm một tình huống. Bảng sau chương trình nói **vì sao** và **khi nào không**.

```cpp
#include <cctype>
#include <iostream>
#include <memory>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

struct Viec { int ma; };

// (1) chỉ đọc chuỗi, không cần '\0' cuối: string_view
int demChuHoa(std::string_view s) {
    int n = 0;
    for (char c : s) if (std::isupper(static_cast<unsigned char>(c))) ++n;
    return n;
}
// (2) chỉ đọc vector lớn: const&
long long tong(const std::vector<int>& v) {
    long long t = 0;
    for (int x : v) t += x;
    return t;
}
// (3) sửa tại chỗ cho người gọi thấy: T&
void tangMoiPhanTu(std::vector<int>& v) { for (int& x : v) ++x; }

// (4) hàm tạo lưu chuỗi vào thành viên: sink (giá trị rồi move)
class NguoiDung {
public:
    explicit NguoiDung(std::string ten) : ten_(std::move(ten)) {}
    const std::string& ten() const { return ten_; }     // getter: const& tới thành viên
private:
    std::string ten_;
};
// (5) tìm có thể không thấy, không chép phần tử: con trỏ const (nullptr = không thấy)
const std::string* timTen(const std::vector<std::string>& ds, std::string_view can) {
    for (const std::string& s : ds) if (s == can) return &s;
    return nullptr;
}
// (6) nhận sở hữu một việc: unique_ptr theo giá trị
class HangViec {
public:
    void them(std::unique_ptr<Viec> v) { q_.push_back(std::move(v)); }
    std::size_t size() const { return q_.size(); }
private:
    std::vector<std::unique_ptr<Viec>> q_;
};
// (7) tham số tùy chọn: con trỏ const có thể null
std::string dinhDang(std::string_view nd, const std::string* tien = nullptr) {
    return tien ? *tien + ": " + std::string(nd) : std::string(nd);
}
// (8) trả hai giá trị: struct có tên trường
struct ThuongDu { int thuong; int du; };
ThuongDu chia(int a, int b) { return {a / b, a % b}; }

// (9) factory: unique_ptr (chuyển sở hữu); vector lớn trả theo giá trị
std::unique_ptr<Viec> taoViec(int ma) { return std::make_unique<Viec>(Viec{ma}); }
std::vector<int> taoDay(int n) {
    std::vector<int> v;
    for (int i = 1; i <= n; ++i) v.push_back(i);
    return v;                                           // không chép cả vector
}
// (10) giao chuỗi cho luồng khác: nhận THEO GIÁ TRỊ (luồng có bản riêng), trả std::thread theo giá trị
std::thread khoiDong(std::string ten, long long* oKetQua) {
    return std::thread([ten, oKetQua] { *oKetQua = static_cast<long long>(ten.size()) * 10; });
}

int main() {
    std::cout << "(1) " << demChuHoa("Nguyen Van An") << "\n";
    std::vector<int> v = taoDay(5);
    std::cout << "(2) " << tong(v) << "\n";
    tangMoiPhanTu(v);
    std::cout << "(3) " << tong(v) << "\n";
    NguoiDung nd(std::string("Lan"));
    std::cout << "(4) " << nd.ten() << "\n";
    std::vector<std::string> ds = {"An", "Binh", "Chi"};
    const std::string* p = timTen(ds, "Binh");
    std::cout << "(5) " << (p ? *p : "?") << " / " << (timTen(ds, "Dung") ? "thay" : "khong thay") << "\n";
    HangViec hang;
    hang.them(taoViec(7));
    hang.them(std::make_unique<Viec>(Viec{8}));
    std::cout << "(6) " << hang.size() << "\n";
    std::string tien = "LOG";
    std::cout << "(7) " << dinhDang("xin chao", &tien) << " / " << dinhDang("khong tien to") << "\n";
    auto [thuong, du] = chia(17, 5);
    std::cout << "(8) " << thuong << " " << du << "\n";
    std::cout << "(9) " << taoViec(9)->ma << " " << taoDay(3).size() << "\n";
    std::vector<long long> kq(2, 0);
    std::string ten = "bep";
    std::thread t1 = khoiDong(ten, &kq[0]);
    std::thread t2 = khoiDong(std::move(ten), &kq[1]);
    t1.join();
    t2.join();
    std::cout << "(10) " << kq[0] << " " << kq[1] << "\n";
    return 0;
}
```

**Chạy từng dòng** (theo thứ tự thực thi của `main`; số trong ngoặc là số tình huống)

| Dòng | Chuyện gì xảy ra | Ai sở hữu gì lúc này |
|---|---|---|
| (9) `taoDay(5)` | Dựng vector rồi `return v;`: không chép cả vector | `v` của `main` giữ 1..5 |
| (1),(2),(3) | `"Nguyen Van An"` thành `string_view` không chép (3 chữ hoa: N, V, A); `tong` đọc qua `const&` (15); `tangMoiPhanTu` sửa chính `v` qua `&`, tổng thành 20 | `v` vẫn của `main` |
| (4),(5) | `std::string("Lan")` tạm được **move** vào `ten_`; `timTen` trả địa chỉ phần tử `"Binh"` trong `ds`, không thấy `"Dung"` thì `nullptr` | `nd` sở hữu chuỗi; `ds` sở hữu, `p` chỉ xem |
| (6),(7),(8) | `them` nhận `unique_ptr` rồi `std::move` vào vector; `&tien` đưa con trỏ, bỏ trống thì mặc định `nullptr`; `chia` trả `ThuongDu{3, 2}`, `auto [thuong, du]` tách ra | `hang` sở hữu hai `Viec` |
| (10) | `khoiDong(ten, ...)` chép `ten` vào tham số, lambda giữ bản riêng; `khoiDong(std::move(ten), ...)` move; mỗi luồng ghi một ô `kq[i]`, `join` rồi mới đọc | mỗi luồng giữ chuỗi riêng |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan và ASan sạch):

```text
(1) 3
(2) 15
(3) 20
(4) Lan
(5) Binh / khong thay
(6) 2
(7) LOG: xin chao / khong tien to
(8) 3 2
(9) 9 3
(10) 30 30
```

| # | Tình huống | Chữ ký chọn | Vì sao | Khi KHÔNG hợp |
|---|---|---|---|---|
| 1 | Đếm chữ hoa trong chuỗi, người gọi có `string`, chuỗi chữ hoặc cửa sổ | `std::string_view` | Nhận mọi nguồn, không chép, 16 byte | Cần `'\0'` (gọi API C) hoặc phải lưu lại |
| 2 | Cộng vector lớn | `const std::vector<int>&` | Chép vector là phí; chỉ đọc | Kiểu nhỏ như `int`: theo giá trị |
| 3 | Tăng mọi phần tử tại chỗ | `std::vector<int>&` | Người gọi cần thấy kết quả trên chính nó | Có thể trả vector mới thì trả giá trị, dễ đọc hơn |
| 4 | Hàm tạo lưu tên | `explicit NguoiDung(std::string ten)` + `std::move` | Chỉ thừa một `move` so với hai hàm tạo | Hàm chỉ gán lại nhiều lần (mục 4) |
| 5 | Tìm trong container, phần tử to | `const std::string*` (hoặc `optional<int>` nếu phần tử nhỏ) | Không chép phần tử; `nullptr` = không thấy | Container có thể chết/đổi trước khi dùng con trỏ |
| 6 | Hàng đợi nhận việc | `std::unique_ptr<Viec>` theo giá trị | Chữ ký nói rõ "hàm này nhận quyền"; `std::move` ở nơi gọi | Chỉ cần xem `Viec`: `const Viec&` |
| 7 | Tham số tùy chọn | `const std::string* tien = nullptr` | Nhận được "không có" mà không chép | Luôn có đối số: dùng `const&`; chép rẻ: `optional` |
| 8 | Chia lấy thương và dư | trả `struct ThuongDu` | Có tên trường; không cần tham số ra | Chỉ hai giá trị hiển nhiên: `pair` cũng được |
| 9 | Hàm sinh đối tượng | trả giá trị (`vector`), `unique_ptr` (đối tượng heap) | Copy elision; chuyển sở hữu rõ ràng | `return std::move(local)`; trả `T&` tới cục bộ |
| 10 | Giao chuỗi cho luồng chạy nền | `std::string` theo giá trị, trả `std::thread` theo giá trị | Luồng giữ bản riêng, không treo khi người gọi xong | `const&`/`string_view` mà luồng dùng sau khi hàm trả về |

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Khi nào truyền tham số theo giá trị, khi nào `const&`? Thế nếu hàm sẽ lưu đối số lại thì sao?"
    Chỉ đọc: kiểu nhỏ và chép rẻ (`int`, `double`, `string_view`, con trỏ) thì theo giá trị; kiểu to thì `const&` vì chép là phí. Nếu hàm **giữ** đối số (hàm tạo lưu thành viên, đẩy vào hàng đợi) thì nhận **theo giá trị rồi `std::move`** vào chỗ cất. Khi đó người gọi đưa tạm hoặc `std::move` thì chỉ một `move`, đưa biến có tên thì một `copy` cộng một `move`; mình đã đếm thật. Nối tiếp "sao không viết hai hàm `const&` và `&&`": tối ưu hơn một `move` nhưng phải nhân đôi số hàm; với kiểu `move` rẻ thì sink gọn hơn.

??? question "Sink parameter có luôn tốt hơn `const&` không?"
    Không. Khi hàm **gán lại** vào một đối tượng đã có sức chứa (setter gọi nhiều lần), `const&` cho phép phép gán dùng lại vùng nhớ cũ, còn sink bắt xin vùng mới ngay ở tham số. Mình đo: 1000 lần gán chuỗi 100 ký tự, `const&` xin heap 0 lần, sink 1000 lần. Với kiểu rẻ chép (`int`) hay chuỗi ngắn nằm trong bộ đệm nhỏ thì khác biệt không đáng kể. Sink hợp nhất ở hàm tạo.

??? question "Trả về `std::move(local)` có nhanh hơn `return local;` không?"
    Không, thường chậm hơn. NRVO chỉ áp dụng cho tên biến cục bộ; `std::move(local)` là một biểu thức khác, nên chặn NRVO và buộc một lần `move` (g++ cảnh báo `-Wpessimizing-move`). Còn `return local;` nếu không bỏ được thì trình biên dịch tự thử `move`. Chỗ `std::move` ở `return` là **đúng**: trả thứ **không** phải biến cục bộ mà bạn muốn lấy hẳn, ví dụ thành viên của đối tượng sắp bỏ. Câu hỏi nối tiếp hay gặp: "`return b ? x : y;` thì sao": chép, vì kết quả của `? :` giữa hai lvalue là lvalue; viết `if/else` với hai `return`.

??? question "`string_view` thay `const std::string&` được không? Nguy hiểm gì?"
    Làm tham số **chỉ đọc** thì được và tốt hơn: nhận cả chuỗi chữ lẫn `string` mà không tạo `string` tạm. Ba chỗ nguy hiểm. Một: nó không sở hữu, nên không được lưu làm thành viên hay trả về nếu nguồn có thể chết trước (mình chạy ASan: `heap-use-after-free`). Hai: không bảo đảm `'\0'` cuối, nên không đưa `data()` cho `printf("%s")`/`fopen`. Ba: `string_view` tạo từ chuỗi tạm thì chết cuối câu lệnh. Cần C API thì nhận `const std::string&`.

??? question "Hàm trả về tham chiếu khi nào thì an toàn?"
    Khi thứ được trả sống lâu hơn lời gọi: thành viên của đối tượng còn sống, phần tử container còn đó, biến `static`, hoặc chính tham số tham chiếu. Nối tiếp "nhưng tham số là tạm thì sao": `const std::string& dai(const std::string& a, const std::string& b)` gọi với hai chuỗi tạm trả về biệt danh của hai tạm chết cuối câu lệnh; mình chạy trần thấy in đúng, ASan báo `stack-use-after-scope`. Muốn an toàn trước tạm thì trả giá trị. Biến cục bộ thì không bao giờ.

??? question "`const` ở cuối hàm thành viên nghĩa gì? Hàm `const` có thread-safe không? Mutex trong lớp mà vẫn muốn hàm đọc là `const` thì làm sao?"
    `const` cam kết hàm không sửa trạng thái nhìn thấy của đối tượng, và `this` trở thành `const T*`. Về luồng: chuẩn bảo đảm gọi hàm `const` của **kiểu chuẩn** đồng thời là an toàn, và người dùng kỳ vọng như vậy ở kiểu của bạn, nhưng `const` **không tự đem lại** an toàn: hàm `const` sửa thành viên `mutable` không có bảo vệ vẫn gây data race. Muốn hàm đọc khóa mutex mà vẫn `const` thì khai báo mutex là `mutable` (mình thử bỏ `mutable`: lỗi biên dịch `discards qualifiers`).

??? question "Hàm cần trả về hai ba kết quả thì làm thế nào? Có dùng tham số `&` làm đầu ra không?"
    Ưu tiên trả `struct` có tên trường (hoặc `pair`/`tuple` khi ngắn), nơi gọi dùng structured binding; nó tự mô tả và không buộc khai báo biến trống trước. Tham số `T&` làm đầu ra giấu việc "biến này bị sửa" ở nơi gọi, nên chỉ để cho trường hợp thật cần tái dùng bộ nhớ (bộ đệm dùng đi dùng lại). Cần "có thể không có": `optional` nếu chép rẻ, `const T*` nếu trỏ vào đối tượng sống lâu.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `return std::move(local);` hoặc `return b ? x : y;`"
    Hai kiểu "tưởng nhanh": `std::move(local)` chặn NRVO (mình chạy ra `move` thay vì không gì cả, g++ còn cảnh báo `-Wpessimizing-move`), còn `? :` giữa hai biến là `copy`. Viết `return local;`, và dùng `if/else` với hai `return`.

!!! warning "Lỗi 2: Nhận `const&`/`string_view` rồi lưu lại, hoặc trả tham chiếu tới đối số tạm"
    Các ví dụ này biên dịch sạch cảnh báo, có cái chạy trần còn in đúng, rồi bị ASan bắt (`stack-use-after-scope`, `heap-use-after-free`). Thứ nào hàm **giữ** thì phải thuộc về hàm: nhận theo giá trị rồi `std::move`.

!!! warning "Lỗi 3: Sink ở chỗ không đáng, `const T` ở kiểu trả về, `T&` làm đầu ra"
    Sink cho hàm gán lại nhiều lần (1000 lần xin heap thay vì 0), `const Goi` làm kiểu trả về (gán sao chép thay vì gán di chuyển), tham số `T&` đầu ra mà trả giá trị được: đều làm code chậm hơn hoặc khó đọc hơn mà không được gì.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="55" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Hàm tạo của lớp `HoSo` luôn lưu `ten` vào thành viên `ten_`; người gọi hay viết `HoSo h(std::string("An"));` hoặc `HoSo h(std::move(s));`. Chữ ký nào đủ tốt nhất?

- `explicit HoSo(const std::string& ten) : ten_(ten) {}`, vì `const&` không bao giờ chép
- `explicit HoSo(std::string ten) : ten_(std::move(ten)) {}`, vì chỉ tốn thêm một `move`
- `explicit HoSo(std::string&& ten) : ten_(std::move(ten)) {}`, vì nhận được mọi chuỗi
- `explicit HoSo(std::string_view ten) : ten_(ten) {}`, vì không tạo bản sao nào

<p class="giai-thich" markdown>Hàm tạo giữ đối số, đúng mô hình sink: nhận theo giá trị rồi move vào thành viên thì đưa tạm hay `std::move` đều chỉ tốn thêm một phép move rẻ. `const&` vẫn phải chép vào `ten_`, nên nó luôn chép, kể cả khi người gọi đưa tạm. `std::string&&` không nhận được biến có tên, nên câu "nhận mọi chuỗi" là sai. `string_view` thì khi lưu vào `ten_` vẫn phải chép ký tự, nên "không tạo bản sao nào" là sai, và người gọi có `std::string` tạm cũng không được hưởng move.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** `Goi` có hàm tạo sao chép in `copy` và hàm tạo di chuyển in `move`. Đoạn sau in gì?

```text
Goi f(bool b) { Goi x, y; return b ? x : y; }
Goi g = f(true);
```

- Không in gì, vì NRVO bắt buộc kể từ C++17 trở đi
- `move`, vì `return` luôn coi mọi biến cục bộ là rvalue
- `move` hoặc `copy` tùy `b`, vì `x` và `y` là hai biến khác nhau
- `copy`, vì `? :` cho một lvalue, không phải tên biến

<p class="giai-thich" markdown>Kết quả của `b ? x : y` với hai lvalue cùng kiểu là một lvalue, không còn là "tên một biến cục bộ", nên cả NRVO lẫn move ngầm đều không áp dụng và phép chép chạy; mình chạy g++ 11 thấy đúng `copy`. Từ C++17 chỉ giá trị tạm như `return Goi();` mới bắt buộc bỏ qua; với biến có tên NRVO chỉ là được phép. Move ngầm chỉ áp dụng khi `return` một tên biến cục bộ hoặc tham số. Việc `b` đúng hay sai không đổi kiểu biểu thức, nên kết quả không đổi theo `b`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Đọc đoạn sau. Chuyện gì xảy ra ở dòng in?

```text
const std::string& dai(const std::string& a, const std::string& b) {
    return a.size() >= b.size() ? a : b;
}
const std::string& r = dai(std::string("ngan"), std::string("dai hon"));
std::cout << r;
```

- An toàn, vì `const&` gắn vào tạm nên tạm sống tới hết phạm vi của `r`
- Lỗi biên dịch, vì không gắn `const&` vào giá trị tạm được trong đối số
- `r` treo, vì hai tạm chết cuối câu lệnh mà hàm trả biệt danh của một tạm
- `r` treo, vì `? :` luôn tạo ra một bản sao của chuỗi vừa được chọn

<p class="giai-thich" markdown>Việc kéo dài vòng đời chỉ xảy ra khi tạm gắn **thẳng** vào biến tham chiếu; ở đây tạm là đối số của `dai`, sống tới hết câu lệnh, và `r` chỉ giữ biệt danh mà hàm trả ra, nên bị treo. Gắn `const&` vào tạm là hợp lệ nên không có lỗi biên dịch; mình biên dịch `-Wall` không cảnh báo, chạy trần còn in đúng, nhưng ASan báo `stack-use-after-scope`. Còn `? :` giữa hai lvalue cùng kiểu cho lvalue, không sao chép gì; nếu sao chép thì `r` lại không treo ở đúng chỗ này.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Bảng `std::vector<HoSo>` chứa các `HoSo` rất lớn, sống suốt chương trình. Hàm `tim(ma)` có thể không thấy, người gọi chỉ đọc và không muốn chép cả hồ sơ. Kiểu trả về hợp lý?

- `const HoSo*`, trả `nullptr` khi không thấy
- `std::optional<HoSo>`, vì `optional` luôn chỉ tham chiếu, không chép
- `const HoSo&`, trả tham chiếu tới một `HoSo` cục bộ rỗng khi không thấy
- `HoSo`, vì copy elision làm trả theo giá trị thành miễn phí

<p class="giai-thich" markdown>Con trỏ tới phần tử có sẵn không chép gì và có giá trị đặc biệt `nullptr` cho "không thấy", với điều kiện bảng sống lâu hơn lúc dùng con trỏ. `optional<HoSo>` **chứa một bản** `HoSo` (chép), và ở C++17 còn không chứa được tham chiếu, nên "luôn chỉ tham chiếu" sai. Tham chiếu tới `HoSo` cục bộ rỗng là trả tham chiếu tới biến cục bộ, lỗi cổ điển. Copy elision chỉ bỏ chép khi tạo giá trị **mới**; ở đây phần tử đã nằm trong bảng, nên trả theo giá trị vẫn chép.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn sau. Dòng `printf` in gì?

```text
std::string ten = "Nguyen Van An";
std::string_view ho = std::string_view(ten).substr(0, 6);
std::printf("%s\n", ho.data());
```

- `Nguyen`, vì cửa sổ chỉ có 6 ký tự
- Lỗi biên dịch, vì không đưa `data()` của `string_view` cho `printf` được
- Không xác định, vì `string_view` không bao giờ có ký tự kết thúc
- `Nguyen Van An`, vì `%s` đọc tới `'\0'` cuối chuỗi gốc

<p class="giai-thich" markdown>`ho.data()` là địa chỉ ký tự đầu của cửa sổ, nhưng `printf("%s")` không biết độ dài cửa sổ nên đọc tiếp tới `'\0'`, mà `ten` có `'\0'` cuối; mình chạy và in đúng `Nguyen Van An`. Nghĩ rằng "chỉ in `Nguyen`" là coi `string_view` như một chuỗi riêng, trong khi nó chỉ là địa chỉ cộng độ dài. `data()` trả `const char*` nên `printf` dùng được, không có lỗi biên dịch. Còn "không xác định" là quá tay: chuỗi gốc ở đây có `'\0'` cuối nên kết quả xác định, chỉ là ngoài ý muốn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Lớp `BoDem` có thành viên `std::mutex khoa_` (chưa `mutable`), và hàm `int doc() const` khóa `khoa_` bằng `lock_guard`. Biên dịch báo `discards qualifiers`, mà hàm vẫn phải gọi được qua `const BoDem&`. Cách sửa đúng?

- Bỏ lệnh khóa trong `doc()`, vì hàm `const` không sửa gì nên không thể có data race
- Bỏ chữ `const` ở `doc()`, vì khi đó vẫn gọi được qua `const BoDem&`
- Khai báo `mutable std::mutex khoa_;` để khóa được trong hàm `const`
- Đổi `lock_guard` thành `unique_lock`, vì `unique_lock` khóa được mutex `const`

<p class="giai-thich" markdown>Khóa mutex là sửa mutex, mà trong hàm `const` thành viên là `const`; `mutable` cho phép đúng việc đó mà vẫn giữ cam kết `const` với bên ngoài (mình thử bỏ `mutable`: lỗi `discards qualifiers`). Bỏ `const` thì `doc()` không gọi được qua `const BoDem&`, nên không đáp ứng đề. `unique_lock` cũng cần sửa mutex, nên lỗi y hệt. Bỏ khóa thì vẫn có data race khi luồng khác đang `tang()`, vì "hàm const" không ngăn luồng khác ghi cùng lúc.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Hàm `datTen(...)` của `HoSo` được gọi hàng nghìn lần trên cùng một đối tượng đã có sẵn một tên dài, và người gọi thường truyền một biến chuỗi có sẵn. Chữ ký nào hợp nhất?

- `void datTen(std::string t) { ten_ = std::move(t); }`, vì nhận theo giá trị luôn là mặc định tốt nhất
- `void datTen(const std::string& t) { ten_ = t; }`, vì phép gán dùng lại vùng nhớ sẵn có của `ten_`
- `void datTen(std::string&& t) { ten_ = std::move(t); }`, vì nhận được mọi loại chuỗi
- `void datTen(std::string& t) { ten_ = t; }`, vì không chép và không xin heap

<p class="giai-thich" markdown>Đây là hàm gán lại, không phải hàm tạo: `ten_ = t` chép ký tự vào vùng nhớ cũ nếu còn đủ chỗ, nên `const&` không xin heap lần nào (mình đếm: 0 trên 1000 lần gọi). Sink thì mỗi lần gọi dựng một chuỗi mới ở tham số, tức là 1000 lần xin heap; "luôn tốt nhất" chỉ đúng với hàm tạo. `std::string&&` từ chối biến có tên, mà người gọi ở đây hay truyền biến có tên. `std::string&` không `const` từ chối cả chuỗi tạm lẫn chuỗi `const`, và hứa với người đọc rằng đối số có thể bị sửa.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Chữ ký hàm nói **ai sở hữu, ai chỉ xem, ai được sửa**. Cây hỏi: chỉ đọc (nhỏ thì giá trị, to thì `const&`), sửa cho người gọi thấy (`T&`), giữ lại (sink hoặc `unique_ptr`), có thể không có (`T*` hay `optional`). Kiểu nhỏ trên g++ 11: `int` 4, `string_view` 16, `string` 32 byte.
2. **Sink parameter**: hàm giữ đối số thì nhận theo giá trị rồi `std::move`; mình đếm: tạm chỉ một `move`, biến có tên một `copy` cộng một `move`, trong khi `const&` luôn chép. Nhưng **gán lại** nhiều lần thì `const&` thắng (0 so với 1000 lần xin heap trong ví dụ), nên sink hợp nhất ở hàm tạo.
3. **Quan sát chỉ khi sống đủ lâu**: `string_view`/`span` không giữ nguồn sống và không bảo đảm `'\0'`; `const&` chỉ kéo dài tạm khi gắn thẳng vào biến, không qua hàm trả tham chiếu (ASan: `stack-use-after-scope`). Thứ hàm giữ thì thuộc về hàm.
4. **Kiểu trả về**: trả giá trị mặc định (C++17 bắt buộc bỏ chép với giá trị tạm; NRVO chỉ được phép); `return std::move(local)` chặn NRVO; `return b ? x : y;` và `return thanhVien;` **chép**; đừng thêm `const` vào kiểu trả về; `unique_ptr` để chuyển sở hữu, tham chiếu chỉ tới thứ sống lâu hơn hàm, nhiều giá trị thì `struct` có tên.
5. **`const` ở hàm thành viên** là cam kết về trạng thái nhìn thấy; `mutable` cho mutex/cache bên trong và khi đó **bạn** phải bảo vệ nó để hàm `const` an toàn đa luồng; dữ liệu đưa sang luồng khác thì giữ bản riêng (theo giá trị, `std::move`).
