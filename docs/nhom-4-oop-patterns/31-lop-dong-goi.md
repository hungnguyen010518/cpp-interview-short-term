# Bài 31 — Lớp và đóng gói: giữ cho đối tượng luôn hợp lệ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng khác biệt duy nhất giữa `class` và `struct` (mức truy cập mặc định), dùng `public:`/`private:` để **đóng gói**, và giữ **bất biến** của lớp (ví dụ `TaiKhoan` giữ số dư không âm qua mọi đường vào) bằng hàm tạo và hàm thành viên thay cho trường công khai.
    - Dùng **danh sách khởi tạo thành viên** và biết vì sao nó bắt buộc với thành viên `const` hay tham chiếu; biết thứ tự dựng thành viên theo thứ tự **khai báo** (không theo thứ tự bạn viết trong danh sách, g++ cảnh báo `-Wreorder`) và thứ tự hủy ngược lại (đã chạy thật).
    - Đọc và viết hàm thành viên `const` (nối [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)), `this`, thành viên `static` (một bản cho cả lớp), `explicit` cho hàm tạo một tham số, `= default`/`= delete` (nối [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)), và nhắc được `friend`.
    - So với Go: struct + method, receiver giá trị/con trỏ, không có hàm tạo/hàm hủy (hàm `NewX`, `defer`), truy cập theo package chứ không theo kiểu.

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (struct, hàm tạo, hàm hủy), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const&`, hàm thành viên `const` nhắc ngắn), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (hàm hủy chạy ở cuối khối, `throw`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`this`, hàm tạo sao chép, `= delete`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`= default` nêu tên), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`try`/`catch`, `e.what()`, `<stdexcept>`), [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) và [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (danh sách khởi tạo đã gặp), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`class`, `public:`, `private:`), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (đuôi `_` trong tên thành viên).

## 🧠 Câu chuyện mở đầu

Một **xưởng đồ chơi** có tập **bản vẽ**. Mỗi bản vẽ mô tả một loại đồ chơi: có những bộ phận nào, lắp theo thứ tự nào, và ai được mở nắp ra sửa. Từ một bản vẽ, xưởng làm ra bao nhiêu **món đồ chơi** cũng được; mỗi món có bộ phận riêng.

**Class** (lớp) là bản vẽ, **object** (đối tượng) là món đồ chơi làm ra từ nó. [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) và [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) bạn đã dùng struct và hàm tạo/hàm hủy như vậy; bài này nâng lên cấp **thiết kế**. Câu hỏi chính: làm sao để món đồ chơi ra khỏi xưởng luôn đạt kiểm định (luôn hợp lệ), kể cả khi khách cầm nó trong tay? Câu trả lời là **đóng gói (encapsulation)**: giấu bộ phận bên trong sau nắp, chỉ cho khách bấm vài nút đã được kiểm định.

!!! info "Chỗ nào ví von xưởng đồ chơi không còn đúng?"
    Nắp `private` chỉ là rào **lúc biên dịch**: code ngoài lớp đụng vào là bị từ chối khi dịch, còn bộ nhớ của món đồ thì không có khóa nào. Ngoài ra bản vẽ ngoài đời không "sống" trong kho, còn thành viên `static` (mục 6) giống tờ ghi chú **dán ngay trên bản vẽ**, chung cho mọi món làm ra.

## 📖 Giải thích

### 1. `class` và `struct`: một khác biệt duy nhất

[Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) nói `class` dùng như `struct` ("khác nhau nhỏ sẽ nói ở bài sau"). Khác nhau nhỏ đó là **mức truy cập mặc định**: thành viên của `struct` mặc định `public` (ai cũng đụng được), của `class` mặc định `private` (chỉ code của chính lớp đụng được). Chuẩn C++ còn dùng đúng quy tắc này cho kế thừa (Bài 32 sẽ nói). Thử 3 ở Ví dụ 1 chạy thật điều này.

Ngoài ra hai từ khóa **hoàn toàn như nhau**: đều có hàm tạo, hàm hủy, hàm thành viên, đều đặt ở stack hay heap được. Thói quen thường gặp là `struct` cho gói dữ liệu đơn giản, `class` khi lớp có quy tắc cần giữ; đó chỉ là quy ước đặt tên, không phải luật.

### 2. Đóng gói và bất biến

**Bất biến của lớp (class invariant)** là điều luôn phải đúng với mọi đối tượng hợp lệ, như "số dư không âm". Nếu trường `soDu` để `public`, bất kỳ dòng code nào cũng viết được `tk.soDu = -5` và lớp không còn gì bảo đảm. Đóng gói là đặt trường dưới `private:` rồi cho bên ngoài đi qua **hàm thành viên** (member function, hàm viết trong lớp, [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)) và hàm tạo, nơi bạn kiểm tra điều kiện.

- **Getter**: hàm chỉ đọc một thành viên, như `soDu()`. **Setter**: hàm đổi một thành viên; chỉ đưa ra khi thật cần, và phải kiểm bất biến bên trong.
- **Thiết kế tốt hơn setter**: đưa ra hành động có nghĩa, như `nop`/`rut`, thay cho `datSoDu`. Bên ngoài không cần (và không nên) ghi thẳng số dư.

Mọi đối tượng ra đời qua một hàm tạo. Nếu hàm tạo ném ngoại lệ ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)) thì theo chuẩn đối tượng coi như chưa tồn tại, nên không ai cầm được `TaiKhoan` sai.

### 3. Danh sách khởi tạo thành viên

[Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) và [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) đã dùng `: hop(4)` sau dấu `)` của hàm tạo. Đó là **danh sách khởi tạo thành viên**: các thành viên được **dựng** (khởi tạo ngay) trước khi thân `{}` của hàm tạo chạy. Viết `chu_ = chu;` trong thân thì thành viên đã được dựng xong rồi mới bị **gán** lại, tức là hai bước.

Có ba chỗ **bắt buộc** dùng danh sách (hoặc giá trị đặt ngay chỗ khai báo như `int ma_ = 0;`):

- Thành viên `const`: sinh ra là phải có giá trị, gán sau là sửa hằng.
- Thành viên là tham chiếu `int&`: phải gắn ngay lúc khai báo ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)).
- Thành viên có kiểu lớp mà lớp đó không có hàm tạo không tham số: gán trong thân nghĩa là đã cố dựng nó bằng hàm tạo không tham số trước.

Với `int` hay `std::string` thường thì cả hai cách đều chạy được; nên mặc định dùng danh sách. Ví dụ 2 cho ra thông báo lỗi thật.

!!! warning "Hay nhầm"
    Thứ tự dựng thành viên là thứ tự **khai báo trong lớp**, không phải thứ tự bạn viết trong danh sách. Viết `: b_(1), a_(b_ + 10)` mà khai báo `a_` trước `b_` thì `a_` được dựng trước và đọc `b_` khi nó còn chưa có giá trị. Ví dụ 3 chạy thật; g++ cảnh báo `-Wreorder` để bắt chuyện này.

### 4. Thứ tự gọi hàm tạo và hàm hủy

Với **một** đối tượng có thành viên là đối tượng khác: các thành viên được dựng theo thứ tự khai báo, rồi thân hàm tạo chạy. Khi chết thì thân hàm hủy chạy trước, rồi các thành viên bị hủy **theo thứ tự ngược**. Giữa nhiều biến cục bộ cùng khối, cái ra đời sau chết trước ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)).

Xưởng đồ chơi: thợ lắp bộ phận theo thứ tự trên bản vẽ rồi mới kiểm tra lần cuối (thân hàm tạo); tháo thì ngược lại. Ví dụ 3 in ra thứ tự thật.

### 5. Hàm thành viên `const` và `this`

[Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) đã cho thấy chữ `const` đặt **sau** danh sách tham số, như `int soDu() const`: cam kết "hàm này không sửa đối tượng". Chỉ hàm có chữ đó mới gọi được qua `const TaiKhoan&`, nên hàm chỉ đọc luôn nên có `const`. Bên trong, `this` ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)) có kiểu `const TaiKhoan*`, nên thân hàm không sửa được thành viên (trừ thành viên khai báo `mutable`, từ khóa ít dùng, chỉ nhắc tên).

`this` còn dùng để trả `*this`, cho phép gọi nối `b.datTen("x").datTen("y")` (Ví dụ 4).

### 6. Thành viên `static`

Thành viên thường mỗi đối tượng một bản. **Thành viên `static`** chỉ có **một bản cho cả lớp** (tờ ghi chú dán trên bản vẽ), hợp để đếm "đang có bao nhiêu món". Khai báo `static int soLuong_;` trong lớp chưa cấp chỗ nhớ: phải **định nghĩa đúng một lần ngoài lớp** (`int DoChoi::soLuong_ = 0;`). Quên thì g++ dịch được nhưng bước **liên kết** (linker: bước cuối ghép các phần đã dịch thành chương trình) báo `undefined reference`. Từ C++17 có cách khác: thêm chữ `inline` (ở đây hiểu là "định nghĩa ngay trong lớp, vẫn chỉ một bản"), như `inline static int soLuong_ = 0;`.

**Hàm `static`** (như `static int dem()`) gọi bằng `DoChoi::dem()`, không có `this`, nên chỉ đụng được thành viên `static`.

### 7. `explicit`, `= default`, `= delete` và `friend`

Hàm tạo một tham số, như `Tien(long long d)`, mặc định còn là **phép chuyển kiểu ngầm** (implicit conversion): chỗ nào cần `Tien` thì đưa số `5` vẫn được, C++ tự tạo `Tien` tạm. Thường đó là bẫy (đưa nhầm số vào chỗ cần tiền mà không báo). Thêm **`explicit`** trước hàm tạo để cấm; muốn có `Tien` phải viết rõ `Tien(5)`.

`= default` và `= delete` ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)): `= default` bảo trình biên dịch tự sinh hàm đó, `= delete` cấm hẳn. Khi bạn tự viết **bất kỳ** hàm tạo nào, trình biên dịch không còn tự sinh hàm tạo không tham số, nên cần `Khoa() = default;` nếu vẫn muốn.

**`friend`** (nhắc cho biết): lớp khai báo `friend` một hàm hay lớp khác thì nơi đó được đụng vào phần `private`, ví dụ `friend void in(const TaiKhoan&);`. Dùng ít, vì nó làm hai nơi dính nhau; hay gặp nhất khi viết `operator<<` để in một đối tượng bằng `std::cout << obj`.

## 💻 Ví dụ code

### Ví dụ 1: `TaiKhoan` giữ bất biến "số dư không âm"

Hàm tạo kiểm số dư đầu, `rut` từ chối rút quá số dư, và không có cách nào ghi thẳng `soDu_`. `LLONG_MAX` (trong `<climits>`) là số `long long` lớn nhất; `nop` từ chối khoản làm số dư vượt nó, vì tràn số nguyên có dấu là hành vi không xác định. `std::invalid_argument` là kiểu ngoại lệ có sẵn trong `<stdexcept>` cho "đối số không hợp lệ" (cùng họ với `out_of_range` ở [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)).

```cpp
#include <climits>
#include <iostream>
#include <stdexcept>
#include <string>

class TaiKhoan {
public:
    TaiKhoan(std::string chu, long long soDuDau)          // (1)
        : chu_(chu), soDu_(soDuDau) {                      // (2)
        if (soDuDau < 0) {
            throw std::invalid_argument("so du dau am");   // (3)
        }
    }
    bool nop(long long tien) {                             // (4)
        if (tien <= 0 || tien > LLONG_MAX - soDu_) return false;
        soDu_ += tien;
        return true;
    }
    bool rut(long long tien) {                             // (5)
        if (tien <= 0 || tien > soDu_) return false;
        soDu_ -= tien;
        return true;
    }
    long long soDu() const { return soDu_; }               // (6)
    const std::string& chu() const { return chu_; }

private:
    std::string chu_;
    long long soDu_;                                       // (7) bất biến: >= 0
};

void in(const TaiKhoan& t) {                               // (8)
    std::cout << t.chu() << ": " << t.soDu() << "\n";
}

int main() {
    TaiKhoan tk("An", 100);
    tk.nop(50);
    std::cout << "rut 30: " << tk.rut(30) << "\n";
    std::cout << "rut 500: " << tk.rut(500) << "\n";
    in(tk);
    try {
        TaiKhoan xau("Binh", -5);                          // (9)
        in(xau);
    } catch (const std::invalid_argument& e) {
        std::cout << "loi: " << e.what() << "\n";
    }
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `TaiKhoan tk("An", 100)` | Hàm tạo (1): danh sách (2) dựng `chu_`, `soDu_`; số dư đầu không âm nên (3) không ném | `tk`: chu_ "An", soDu_ 100 |
| `tk.nop(50)` | (4): 50 > 0 và không vượt `LLONG_MAX` nên cộng | soDu_ 150 |
| `tk.rut(30)` | (5): hợp lệ, trừ, trả `true` (in `1`) | soDu_ 120 |
| `tk.rut(500)` | (5): 500 > 120 nên trả `false` (in `0`), số dư giữ nguyên | soDu_ 120 |
| `in(tk)` | (8) nhận `const&`, chỉ gọi được hàm `const` (6) | in `An: 120` |
| (9) | Số dư đầu -5: (3) ném, `xau` không ra đời, `in(xau)` không chạy | `catch` in lỗi |

**Kết quả khi chạy:**

```text
rut 30: 1
rut 500: 0
An: 120
loi: so du dau am
```

Mình chạy cả bản này với ASan + UBSan: sạch, mã thoát 0. Bốn Thử thay đổi, mình đều đã chạy:

- **Thử 1: thêm `tk.soDu_ = -5;` vào `main`.** Lỗi biên dịch `error: ‘long long int TaiKhoan::soDu_’ is private within this context`. Bất biến an toàn vì chỉ code của lớp ghi được `soDu_`.
- **Thử 2: bỏ chữ `const` khỏi `soDu()`.** Dòng `t.soDu()` trong `in` thành `error: passing ‘const TaiKhoan’ as ‘this’ argument discards qualifiers`.
- **Thử 3: đổi `class TaiKhoan {` thành `struct TaiKhoan {` rồi xóa hai dòng `public:` và `private:`.** Chương trình vẫn chạy, và thêm `tk.soDu_ = -5; in(tk);` vào `main` thì in `An: -5`: mọi thứ thành công khai nên bất biến vỡ. Ngược lại, giữ `class` mà chỉ xóa `public:` thì g++ báo nhiều lỗi `is private within this context`, trong đó có `TaiKhoan::TaiKhoan(std::string, long long int)`.
- **Thử 4: thêm `tk.nop(LLONG_MAX);` sau `tk.nop(50);`.** `nop` trả `false`, số dư vẫn 150 và UBSan sạch. Bỏ vế `tien > LLONG_MAX - soDu_` thì mình chạy ra tràn số và số dư âm, nên bất biến chỉ đúng khi mọi đường vào đều kiểm.

### Ví dụ 2: thành viên `const`, tham chiếu và kiểu không có hàm tạo mặc định

Hàm tạo dưới đây gán trong thân. Mình đã chạy, g++ từ chối với bốn lỗi (rút gọn):

```cpp
// bo-qua-kiem-tra
struct Phu { Phu(int) {} };
class Cap {
public:
    Cap(int i, int& r) {
        id_ = i;           // thành viên const
        ref_ = r;          // thành viên tham chiếu
        p_ = Phu(1);       // thành viên không có hàm tạo không tham số
    }
private:
    const int id_;
    int& ref_;
    Phu p_;
};
```

```text
error: uninitialized const member in ‘const int’
error: uninitialized reference member in ‘int&’
error: no matching function for call to ‘Phu::Phu()’
error: assignment of read-only member ‘Cap::id_’
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `Cap(int i, int& r) {` | Thân `{` chạy sau khi thành viên đã được dựng; `id_` và `ref_` không có giá trị ban đầu nên g++ báo hai lỗi `uninitialized`; `p_` cần dựng bằng `Phu()` mà `Phu` không có nên báo `no matching function` | chưa dựng được |
| `id_ = i;` | Gán vào một hằng: `assignment of read-only member` | `id_` là hằng, không sửa được |
| `ref_ = r;` | Không có lỗi riêng ở dòng này: dù gắn được thì cũng chỉ là gán giá trị chứ không gắn lại tham chiếu | không đổi |
| `p_ = Phu(1);` | Gán sau khi dựng mặc định đã thất bại | không đổi |

Chuyển ba thành viên vào danh sách (`Cap(int i, int& r) : id_(i), ref_(r), p_(1) {}`, thân rỗng) thì biên dịch sạch với `-Wall -Wextra` (mình đã chạy).

### Ví dụ 3: thứ tự gọi hàm tạo và hàm hủy

`Ghi` in `tao`/`huy` kèm tên; `DoChoi` giữ hai `Ghi` (`khung_` rồi `banh_`) và in ở thân hàm tạo/hủy của nó.

```cpp
#include <iostream>

class Ghi {
public:
    Ghi(const char* ten) : ten_(ten) {
        std::cout << "  tao " << ten_ << "\n";
    }
    ~Ghi() {
        std::cout << "  huy " << ten_ << "\n";
    }

private:
    const char* ten_;
};

class DoChoi {
public:
    DoChoi() : khung_("khung"), banh_("banh") {      // (1)
        std::cout << "  than ham tao DoChoi\n";      // (2)
    }
    ~DoChoi() {
        std::cout << "  than ham huy DoChoi\n";      // (3)
    }

private:
    Ghi khung_;                                      // (4)
    Ghi banh_;
};

int main() {
    std::cout << "vao khoi\n";
    {
        DoChoi a;
        std::cout << "het khoi\n";
    }
    std::cout << "ra khoi\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| `DoChoi a;` | Thành viên theo khai báo (4): `khung_`, `banh_`; rồi thân hàm tạo (2) |
| `}` hết khối | `a` chết: thân hàm hủy (3) trước, rồi `banh_`, rồi `khung_` (ngược lại) |

**Kết quả khi chạy:**

```text
vao khoi
  tao khung
  tao banh
  than ham tao DoChoi
het khoi
  than ham huy DoChoi
  huy banh
  huy khung
ra khoi
```

Mình chạy với ASan + UBSan: sạch.

**Thử thay đổi: viết danh sách (1) ngược lại, `: banh_("banh"), khung_("khung")`.** Mình đã chạy: output **y hệt** (vẫn `tao khung` trước `tao banh`), vì thứ tự dựng là thứ tự khai báo (4), không phải thứ tự trong danh sách. g++ 11.4 với `-Wall` cảnh báo (rút gọn): `warning: ‘DoChoi::banh_’ will be initialized after [-Wreorder]`, kèm `when initialized here`.

Nguy hiểm thật khi thành viên này dùng thành viên kia: với `struct Hai { int a; int b; Hai(int x) : b(x), a(b + 1) {} };` mình chạy thì g++ báo thêm `‘*this.Hai::b’ is used uninitialized [-Wuninitialized]`, vì `a` được dựng trước `b`. Sửa: viết danh sách đúng thứ tự khai báo, hoặc tính `a` từ `x`.

### Ví dụ 4: `this`, hàm `const` và thành viên `static`

`DoChoi` đếm số đối tượng đang sống bằng `soLuong_`: hàm tạo tăng, hàm hủy giảm. `datTen` trả `*this` để gọi nối.

```cpp
#include <iostream>
#include <string>

class DoChoi {
public:
    DoChoi(std::string ten) : ten_(ten) {
        ++soLuong_;                                  // (1)
    }
    ~DoChoi() {
        --soLuong_;                                  // (2)
    }
    DoChoi& datTen(std::string ten) {                // (3)
        ten_ = ten;
        return *this;                                // (4)
    }
    const std::string& ten() const { return ten_; }
    static int dem() { return soLuong_; }            // (6)

private:
    std::string ten_;
    static int soLuong_;                             // (7) khai báo: chung cho cả lớp
};

int DoChoi::soLuong_ = 0;                            // (8) định nghĩa ngoài lớp

int main() {
    std::cout << "luc dau: " << DoChoi::dem() << "\n";
    DoChoi a("robot");
    {
        DoChoi b("xe lua");
        std::cout << "trong khoi: " << DoChoi::dem() << "\n";
        b.datTen("tau hoa").datTen("tau thuy");      // (9)
        std::cout << "b ten: " << b.ten() << "\n";
    }
    std::cout << "sau khoi: " << a.dem() << "\n";    // (10)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `DoChoi::dem()` đầu | (6) hàm `static`, gọi bằng tên lớp; chưa có món nào | `soLuong_` (một bản, vùng tĩnh) = 0 |
| `DoChoi a("robot")` | (1) tăng | `soLuong_` = 1 |
| `DoChoi b("xe lua")` | (1) tăng, in `trong khoi: 2` | `soLuong_` = 2; `a`, `b` mỗi cái một `ten_` |
| (9) | `datTen` đổi tên rồi trả `*this` (chính `b`), nên nối `datTen` tiếp được | `b.ten_` = "tau thuy" |
| `}` hết khối | `b` chết, (2) giảm | `soLuong_` = 1 |
| (10) | `a.dem()` cũng được, cùng một bản `soLuong_` | in `sau khoi: 1` |

**Kết quả khi chạy:**

```text
luc dau: 0
trong khoi: 2
b ten: tau thuy
sau khoi: 1
```

Ba **Thử thay đổi** (mình đã chạy cả ba):

- **Xóa dòng (8):** g++ dịch xong nhưng bước liên kết báo `undefined reference to ‘DoChoi::soLuong_’`.
- **C++17:** thay dòng (7) bằng `inline static int soLuong_ = 0;` rồi bỏ (8): cùng kết quả. Với `-std=c++14`, g++ cảnh báo `inline variables are only available with ‘-std=c++17’`.
- **Thêm `void xem(DoChoi d) {}` và gọi `xem(a);` trước dòng in `sau khoi`:** `d` là bản sao tạo bằng hàm tạo sao chép **tự sinh**, nó không chạy (1), nên trong `xem` bộ đếm vẫn là 1; khi `d` chết (2) giảm, và `sau khoi` in **0** dù `a` vẫn sống. Đó là lý do của [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md): lớp có trạng thái ngoài như bộ đếm phải tự viết hàm sao chép hoặc cấm bằng `= delete`.

### Ví dụ 5: `explicit`

```cpp
#include <iostream>

class Tien {
public:
    Tien(long long dong) : dong_(dong) {}            // (1) một tham số
    long long dong() const { return dong_; }

private:
    long long dong_;
};

void tra(Tien t) {                                   // (2)
    std::cout << "tra " << t.dong() << " dong\n";
}

int main() {
    tra(Tien(100));
    tra(5);                                          // (3) số 5 tự biến thành Tien
    Tien b = 7;                                      // (4) cũng chuyển ngầm
    std::cout << "b = " << b.dong() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `tra(Tien(100))` | Gọi hàm tạo (1) tường minh, rồi truyền | in `tra 100 dong` |
| (3) `tra(5)` | `5` là `int` còn `tra` cần `Tien`: C++ thấy (1) nhận số nên tự tạo `Tien(5)` tạm | in `tra 5 dong` |
| (4) | Tương tự, `b` dựng từ số `7` | `b.dong_` = 7 |

**Kết quả khi chạy:** ba dòng `tra 100 dong`, `tra 5 dong`, `b = 7`.

**Thử thay đổi: viết `explicit Tien(long long dong)` ở (1).** Mình đã chạy; dòng (3) và (4) cùng thành lỗi biên dịch: `error: could not convert ‘5’ from ‘int’ to ‘Tien’` và `error: conversion from ‘int’ to non-scalar type ‘Tien’ requested`. `tra(Tien(100))` vẫn hợp lệ vì viết rõ; `Tien b = 7;` bị coi là chuyển ngầm dù có dấu `=`.

### Ví dụ 6: tự khai báo hàm tạo thì mất hàm tạo mặc định

Hai hàm tạo ở (1) và (2) đều do bạn khai báo, nên trình biên dịch không tự sinh `Khoa()`. Mình đã chạy, g++ từ chối:

```cpp
// bo-qua-kiem-tra
class Khoa {
public:
    explicit Khoa(int ma) : ma_(ma) {}              // (1)
    Khoa(const Khoa&) = delete;                     // (2)
    int ma() const { return ma_; }

private:
    int ma_ = 0;
};

int main() {
    Khoa a;                                         // (3)
    Khoa b(42);
    Khoa c = b;                                     // (4)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Kết quả |
|---|---|---|
| (3) | Cần `Khoa()` nhưng có (1) và (2) nên không có bản tự sinh | `error: no matching function for call to ‘Khoa::Khoa()’` |
| `Khoa b(42);` | Dùng (1) | hợp lệ |
| (4) | Sao chép gọi hàm tạo sao chép đã `= delete` ở (2) | `error: use of deleted function ‘Khoa::Khoa(const Khoa&)’` |

Sửa (3): thêm `Khoa() = default;` (xin lại hàm tạo mặc định), bỏ dòng (4): mình chạy ra thoát mã 0, sạch ASan + UBSan. Muốn cấm cả phép gán sao chép thì thêm `Khoa& operator=(const Khoa&) = delete;` ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)). Mọi chương trình chạy được ở bài này đều sạch với `-fsanitize=address,undefined`.

## Go: struct + method, nhưng không có hàm tạo, hàm hủy, `this`

!!! info "Bạn biết Go?"
    Mình đã chạy một gói Go 1.27.1 nhỏ để kiểm các ý dưới đây:

    - **Struct + method**: `func (t *TaiKhoan) Rut(tien int64) bool` có receiver là tham số **có tên** (`t`) đặt trước tên hàm, nên Go không có `this` mà bạn tự đặt tên. Receiver con trỏ sửa được đối tượng; receiver giá trị `func (t TaiKhoan) RutNham(...)` sửa trên **bản sao** (mình chạy: số dư vẫn 70 sau `RutNham(10)`). Receiver giá trị không phải lời hứa "không sửa" như `const` của C++: Go không có hàm thành viên `const`.
    - **Không có hàm tạo**: quy ước là hàm `NewTaiKhoan(chu string, soDuDau int64) (*TaiKhoan, error)` trả lỗi qua giá trị (mình chạy: `NewTaiKhoan("Binh", -5)` trả lỗi `so du dau am`). Nhưng không có gì buộc người ngoài gọi nó: `var z tk.TaiKhoan` vẫn tạo được giá trị 0 (mình chạy: `z.SoDu()` = 0). Với C++, nếu lớp chỉ có hàm tạo có kiểm tra thì `TaiKhoan t;` bị chặn (không có `TaiKhoan()`), nên không đối tượng nào ra đời mà bỏ qua kiểm tra (như `Khoa a;` ở Ví dụ 6).
    - **Không có hàm hủy**: dọn tài nguyên chắc chắn đúng lúc dùng `defer f.Close()` ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)); bộ gom rác chỉ lo bộ nhớ, vào lúc nó chọn.
    - **Truy cập theo package, không theo kiểu**: trường viết thường `soDu` chỉ thấy được **trong cùng package**. Mình chạy: hàm khác của package `tk` đọc `t.soDu` được; từ package `main` thì `t.soDu undefined (type *tk.TaiKhoan has no field or method soDu, but does have method SoDu)`. `private` của C++ thì theo **lớp**: kể cả hàm khác cùng file cũng không được đụng, trừ `friend`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`class` và `struct` khác nhau ở đâu?"
    Chỉ ở mức truy cập mặc định: thành viên (và cơ sở kế thừa) của `struct` mặc định `public`, của `class` mặc định `private`. Ngoài ra không khác: cả hai đều có hàm tạo, hàm hủy, hàm thành viên, kế thừa. Quy ước: `struct` cho gói dữ liệu đơn giản, `class` cho kiểu có bất biến cần bảo vệ.

??? question "Hàm tạo và hàm hủy được gọi khi nào, theo thứ tự nào?"
    Hàm tạo chạy khi đối tượng ra đời: thành viên được dựng trước theo **thứ tự khai báo**, rồi tới thân hàm tạo. Hàm hủy chạy khi đối tượng chết (cuối khối, `delete`, hết `main` với biến tĩnh): thân hàm hủy trước, rồi thành viên theo thứ tự **ngược**. Với nhiều biến cục bộ trong một khối, cái ra đời sau chết trước.

??? question "Vì sao dùng danh sách khởi tạo thay vì gán trong thân hàm tạo?"
    Danh sách **dựng** thành viên trực tiếp một bước, còn gán trong thân là dựng mặc định rồi gán lại. Với thành viên `const`, tham chiếu, hoặc kiểu không có hàm tạo mặc định thì chỉ danh sách mới hợp lệ. Lưu ý thứ tự dựng theo khai báo, không theo thứ tự trong danh sách; g++ cảnh báo `-Wreorder`.

??? question "Hàm thành viên `const` nghĩa là gì?"
    Là cam kết hàm không sửa trạng thái (có thể quan sát) của đối tượng: bên trong `this` có kiểu `const T*`. Chỉ hàm `const` gọi được trên đối tượng `const` hoặc qua `const&`, nên hàm chỉ đọc nên luôn đánh dấu `const`. Gọi hàm không `const` trên đối tượng `const` là lỗi biên dịch.

??? question "Thành viên `static` là gì?"
    Là thành viên thuộc về **lớp**, chỉ có một bản dùng chung cho mọi đối tượng, nên hợp với bộ đếm hay cấu hình chung. Phải định nghĩa một lần ngoài lớp (`int T::x = 0;`); từ C++17 có thể `inline static` ngay trong lớp. Hàm thành viên `static` không có `this`, gọi bằng `T::ham()`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Để trường `public` rồi mong người dùng tự giữ quy tắc"
    Lớp không còn bảo đảm gì: ai cũng ghi được `soDu = -5`. Để trường `private`, kiểm trong hàm tạo và các hàm thay đổi trạng thái, và đưa ra hành động có nghĩa (`rut`, `nop`) thay vì setter thuần.

!!! warning "Lỗi 2: Quên `const` ở hàm chỉ đọc, hoặc quên định nghĩa thành viên `static`"
    Quên `const` thì hàm không dùng được với `const&` (`discards qualifiers`). Thành viên `static` không `inline` mà quên định nghĩa ngoài lớp thì lỗi `undefined reference` ở bước liên kết.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="31" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau rồi chạy `P p;`. Điều nào đúng về `a_`?

```text
class P {
    int a_;
    int b_;
public:
    P() : b_(1), a_(b_ + 10) {}
};
```

- `a_` là 11, vì danh sách khởi tạo chạy từ trái sang phải
- `a_` chưa có giá trị đáng tin, vì nó dựng trước `b_` mà đọc `b_`
- `a_` là 10, vì thành viên `int` mặc định bằng 0 trước khi bị đọc
- Không biên dịch được, vì `b_` bị dùng trước khi đối tượng ra đời

<p class="giai-thich" markdown>Thứ tự dựng là thứ tự khai báo trong lớp: `a_` đứng trước `b_` nên được dựng trước, và lúc đó `b_` chưa có giá trị; g++ báo `-Wreorder` và `-Wuninitialized`. Danh sách không chạy theo thứ tự bạn viết. Thành viên `int` không tự bằng 0, nó chứa rác nếu chưa ai gán. Và chương trình vẫn biên dịch được (chỉ có cảnh báo), nên đây là lỗi âm thầm chứ không phải lỗi biên dịch.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau. Chương trình in ra gì? (Mỗi lần in một chữ cái, không có xuống dòng.)

```text
struct A { A() { std::cout << "a"; } ~A() { std::cout << "A"; } };
struct B { B() { std::cout << "b"; } ~B() { std::cout << "B"; } };
struct C {
    B x_;
    A y_;
    C() { std::cout << "c"; }
    ~C() { std::cout << "C"; }
};
int main() { C o; }
```

- `abcCBA`, vì mỗi thành viên dựng theo thứ tự chữ cái của tên kiểu
- `cbaABC`, vì thân hàm tạo chạy trước khi thành viên dựng
- `bacBAC`, vì thân hàm hủy chạy sau khi thành viên đã bị hủy
- `bacCAB`, vì dựng theo khai báo rồi hủy theo thứ tự ngược lại

<p class="giai-thich" markdown>Thành viên `x_` (kiểu `B`) khai báo trước `y_` (kiểu `A`) nên dựng ra `b`, `a`, rồi thân hàm tạo in `c`. Khi hủy, thân hàm hủy chạy trước (`C`), rồi thành viên theo thứ tự ngược lại: `y_` in `A`, `x_` in `B`. Thứ tự chữ cái không liên quan gì tới thứ tự dựng. Thân hàm tạo chạy sau khi thành viên dựng xong, và thân hàm hủy chạy trước khi thành viên bị hủy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn sau. Dòng nào gây lỗi biên dịch?

```text
class H {
    int n_ = 0;
public:
    int lay() const { return n_; }
    void tang() { ++n_; }
};
void f(const H& h) {
    int v = h.lay();   // dòng 1
    h.tang();          // dòng 2
}
```

- Chỉ dòng 2, vì `tang()` không cam kết là không sửa đối tượng
- Chỉ dòng 1, vì `lay()` đọc `n_` của một đối tượng `const`
- Cả hai dòng, vì không được gọi hàm thành viên nào trên `const&`
- Không dòng nào, vì `const&` chỉ cấm gán lại biến `h` thôi

<p class="giai-thich" markdown>`lay()` có `const` sau danh sách tham số nên được gọi qua `const H&`; `tang()` thì không, nên dòng 2 lỗi `discards qualifiers` (mình đã chạy). Đọc dữ liệu qua hàm `const` hoàn toàn được phép, nên dòng 1 không sao. Hàm `const` gọi được trên đối tượng `const`; không phải mọi hàm đều bị cấm. Và `const&` còn cấm cả việc gọi hàm có thể sửa đối tượng, không chỉ việc gán lại `h`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Thành viên khai báo `const int id_;` (không có giá trị đặt sẵn) phải được khởi tạo trong danh sách khởi tạo. Điều nào là lý do thật?

- Danh sách cho phép chọn thứ tự dựng thành viên khác thứ tự khai báo của lớp
- Thân hàm tạo chạy xong mới tới lượt dựng các thành viên của lớp đó
- Thành viên `const` phải có giá trị lúc ra đời, còn gán trong thân thì quá muộn
- Hàm tạo không được dùng tham số của chính nó để gán cho thành viên khác

<p class="giai-thich" markdown>Thân hàm tạo chạy khi các thành viên đã được dựng xong, nên một `const` chưa có giá trị lúc đó chỉ còn cách bị gán, mà gán vào hằng là lỗi. Danh sách không đổi được thứ tự dựng: thứ tự luôn theo khai báo. Thân hàm tạo chạy **sau** việc dựng thành viên, không phải trước. Còn tham số của hàm tạo dùng tự do trong thân: với thành viên thường, `chu_ = chu;` vẫn viết được.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn sau (C++17, không dùng `inline`), toàn bộ nằm trong một file. g++ làm gì?

```text
class DoChoi {
public:
    static int dem() { return soLuong_; }
private:
    static int soLuong_;
};
int main() { return DoChoi::dem(); }
```

- Lỗi biên dịch, vì `static` không dùng được với biến thành viên của lớp
- Dịch được, nhưng liên kết báo `undefined reference` tới `soLuong_`
- Dịch và chạy được, vì `soLuong_` tự bằng 0 khi chưa có định nghĩa
- Dịch và chạy được, nhưng mỗi lần gọi `dem()` lại tạo một `soLuong_` mới

<p class="giai-thich" markdown>Dòng `static int soLuong_;` trong lớp chỉ **khai báo**; phải có đúng một định nghĩa ngoài lớp như `int DoChoi::soLuong_ = 0;`, không thì phần liên kết không tìm thấy chỗ nhớ (mình đã chạy ra `undefined reference`). Biến thành viên `static` hoàn toàn hợp lệ. Nó không tự có chỗ nhớ nên cũng không "tự bằng 0". Và chỉ có một bản dùng chung cho cả lớp, không có bản mới ở mỗi lần gọi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Đọc đoạn sau. Hàm tạo có `explicit`, còn `tra` nhận một `Tien`. Dòng nào lỗi biên dịch?

```text
explicit Tien(long long d);
void tra(Tien t);
Tien a(5);       // dòng 1
tra(a);          // dòng 2
tra(5);          // dòng 3
Tien b = 7;      // dòng 4
```

- Chỉ dòng 3, vì chỉ lời gọi hàm mới cần chuyển kiểu ngầm
- Chỉ dòng 4, vì dấu `=` là phép gán nên bị `explicit` cấm
- Dòng 3 và dòng 4, vì cả hai cần chuyển ngầm số sang `Tien`
- Dòng 1 và dòng 3, vì số `5` không được đưa thẳng vào hàm tạo

<p class="giai-thich" markdown>`explicit` cấm chuyển ngầm: dòng 3 cần biến `5` thành `Tien` ngầm, dòng 4 (`Tien b = 7;`) cũng là khởi tạo bằng chuyển ngầm dù có dấu `=`, mình đã chạy ra hai lỗi. Dòng 1 viết rõ hàm tạo nên hợp lệ, dòng 2 chỉ truyền một `Tien` có sẵn. Dòng 4 không phải phép gán vào biến đã có, nên lý do "dấu `=` bị cấm" là sai. Và lời gọi hàm không phải nơi duy nhất cần chuyển ngầm, cách khởi tạo bằng `=` cũng cần.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau. Dòng nào gây lỗi biên dịch?

```text
struct S { int x; };
class T { int x; };
int main() {
    S s;
    T t;
    s.x = 1;   // dòng 1
    t.x = 1;   // dòng 2
}
```

- Chỉ dòng 1, vì `struct` không cho đụng thẳng vào thành viên của nó
- Cả hai dòng, vì thành viên chỉ đổi được qua hàm thành viên
- Không dòng nào, vì `class` và `struct` chỉ khác nhau ở tên gọi
- Chỉ dòng 2, vì `class` mặc định `private`, `struct` mặc định `public`

<p class="giai-thich" markdown>Thành viên của `struct` mặc định `public` nên dòng 1 hợp lệ, còn thành viên của `class` mặc định `private` nên dòng 2 bị từ chối (`is private within this context`, mình đã chạy). Hai từ khóa không chỉ khác tên: mức truy cập mặc định là chỗ khác duy nhất. `struct` không cấm đụng vào thành viên, chính nó mặc định cho phép. Và C++ không bắt mọi thành viên phải đi qua hàm: trường `public` ghi thẳng được.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `class` và `struct` chỉ khác mức truy cập mặc định (`private` và `public`); đóng gói là đặt trường `private`, cho bên ngoài đi qua hàm tạo và hàm thành viên để giữ **bất biến** (như `TaiKhoan` giữ số dư không âm: hàm tạo, `nop`, `rut` đều kiểm, kể cả khoản nộp quá lớn), nên đưa hành động có nghĩa (`rut`, `nop`) thay vì setter thuần.
2. Danh sách khởi tạo dựng thành viên trực tiếp và bắt buộc với thành viên `const`, tham chiếu, hay kiểu không có hàm tạo mặc định (mình chạy ra lỗi thật); thứ tự dựng là thứ tự **khai báo** chứ không theo thứ tự trong danh sách (`-Wreorder`, mình đã chạy).
3. Thứ tự: thành viên dựng theo khai báo rồi thân hàm tạo; hủy thì thân hàm hủy trước rồi thành viên theo thứ tự ngược; hai biến cục bộ trong một khối thì cái sau chết trước (mình in ra thứ tự thật).
4. Hàm chỉ đọc nên là `const` (`this` thành `const T*`, mới dùng được qua `const&`); `this` là con trỏ tới đối tượng, trả `*this` để gọi nối; thành viên `static` là **một bản cho cả lớp** (định nghĩa ngoài lớp, hoặc `inline static` từ C++17: định nghĩa ngay trong lớp) và hàm `static` không có `this`.
5. `explicit` cấm chuyển kiểu ngầm của hàm tạo một tham số; `= default` xin lại hàm tự sinh, `= delete` cấm hẳn; `friend` cho một hàm hay lớp đụng vào `private` (dùng ít). Go: struct + method (receiver có tên, giá trị hay con trỏ), hàm `NewX` thay hàm tạo, `defer` thay hàm hủy, truy cập theo package (hoa/thường), không có `this`.
