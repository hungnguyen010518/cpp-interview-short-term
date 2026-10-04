# Bài 32 — Kế thừa: dùng lại lớp cha, và khi nào không nên

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết `class Con : public Cha`, gọi hàm tạo của lớp cha trong danh sách khởi tạo của lớp con, và nói đúng thứ tự: **cha dựng trước, con hủy trước** (in ra thật); biết `protected` khác `private` ở đâu.
    - Hiểu **che hàm** (name hiding): hàm cùng tên ở lớp con che **mọi** hàm cùng tên của cha, kể cả bản quá tải (chạy thật, lỗi biên dịch thật); gọi hàm của cha bằng `Cha::ham()`.
    - Chọn giữa "là một" (is-a, kế thừa) và "có một" (has-a, thành viên) với ví dụ hình vuông/hình chữ nhật; biết **upcast** (Con sang Cha) hợp lệ, **slicing** (chỉ nhắc), kế thừa `private`, `final`, kế thừa đa và bài toán kim cương.
    - So với Go: struct embedding giống ở chỗ gọi được hàm của "cha", nhưng **không** có upcast, không có `protected`; đa hình của Go là interface (đã chạy Go 1.27.1).

**Bạn cần biết trước:** [Bài 31](31-lop-dong-goi.md) (lớp, `public:`/`private:`, hàm tạo, danh sách khởi tạo, thứ tự dựng thành viên, hàm `const`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (hàm hủy chạy ở cuối khối), [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (`sizeof`).

## 🧠 Câu chuyện mở đầu

Trong **xưởng đồ chơi** ([Bài 31](31-lop-dong-goi.md)), bản vẽ `XeChay` không cần vẽ lại từ đầu. Nó ghi: "dựa trên bản vẽ `DoChoi`, rồi thêm pin và bánh". Món `XeChay` làm ra gồm **một phần `DoChoi` lắp trước**, rồi phần riêng của xe lắp sau.

Đó là **kế thừa (inheritance)**: bản vẽ gốc gọi là **lớp cha (base class)**, bản vẽ thêm bớt gọi là **lớp con (derived class)**. Lớp con dùng lại được mọi thứ lớp cha cho phép, và thêm của riêng mình. Điều quan trọng không phải là "đỡ gõ lại" mà là một lời hứa: **mọi `XeChay` đều là một `DoChoi` thật sự**. Bài này dạy cú pháp, rồi dạy cách kiểm lời hứa đó.

!!! info "Chỗ nào ví von xưởng đồ chơi không còn đúng?"
    Bản vẽ con không "sao chép" bản vẽ cha: món `XeChay` thật sự **chứa** phần `DoChoi` bên trong bộ nhớ (mục 5 đo bằng `sizeof`). Nắp `private` của `DoChoi` vẫn đóng với `XeChay`: phần của cha nằm trong món, nhưng thợ làm xe không mở được.

## 📖 Giải thích

### 1. Cú pháp: `class Con : public Cha`

Viết `class XeChay : public DoChoi { ... };`: dấu `:` sau tên lớp rồi `public DoChoi` nghĩa là "`XeChay` kế thừa `DoChoi`". Từ khóa `public` ở đây là **kiểu kế thừa** (mục 7 nói các kiểu khác); gần như luôn dùng `public`. Đối tượng `XeChay` gọi được mọi hàm `public` của `DoChoi` như của chính nó.

Lưu ý: `class XeChay : DoChoi` mà **không** ghi `public` thì kế thừa là `private` (mục 7); riêng `struct XeChay : DoChoi` mặc định `public`. Đó là quy tắc "mức truy cập mặc định" mà [Bài 31](31-lop-dong-goi.md) hẹn nói ở bài này. Hãy luôn ghi rõ `public`.

### 2. Thứ tự tạo, thứ tự hủy, hàm tạo của cha

Khi tạo một `XeChay`, phần cha phải xong trước: thứ tự là **cha, rồi các thành viên của con (theo khai báo), rồi thân hàm tạo con**. Hủy thì ngược lại hoàn toàn: thân hàm hủy con, rồi thành viên của con, rồi cha. Cha dựng đầu tiên nên hủy cuối cùng, vì thành viên và thân hàm con có thể đang dùng phần cha.

Muốn dựng phần cha bằng hàm tạo nào, bạn **gọi nó trong danh sách khởi tạo** của con: `XeChay(...) : DoChoi(ten), toc_(toc) {}`. Nếu bạn không gọi, trình biên dịch tự gọi hàm tạo **không tham số** của cha; cha không có hàm đó thì lỗi biên dịch (Ví dụ 1 chạy thật). Dù bạn viết `DoChoi(ten)` ở đâu trong danh sách, cha vẫn dựng trước (g++ cảnh báo `-Wreorder`, giống thành viên ở [Bài 31](31-lop-dong-goi.md)).

### 3. `protected` và gọi hàm của cha bằng `Cha::ham()`

Phần `private` của cha **con cũng không đụng được**. Nhưng đôi khi cha muốn chừa một cửa riêng cho con mà vẫn đóng với bên ngoài: đó là **`protected`**. Thành viên `protected` thì code của chính lớp và code của lớp con đụng được, còn code bên ngoài thì không, như `private`.

Hàm của cha viết thành `Cha::ham()` gọi được từ con (nếu hàm đó `public` hoặc `protected`) kể cả khi con có hàm cùng tên; từ bên ngoài thì cần nó `public`. Cách dùng hay gặp: hàm của con **làm việc của cha trước rồi thêm việc riêng** (Ví dụ 2).

!!! warning "Hay nhầm"
    Dữ liệu `protected` vẫn là phá đóng gói: bất kỳ lớp con nào, hiện tại hay viết sau này, cũng ghi được vào nó và làm vỡ bất biến ([Bài 31](31-lop-dong-goi.md)). Hay hơn: để dữ liệu `private`, và chỉ cho con hàm `protected` đã tự kiểm tra.

### 4. Che hàm (name hiding)

Lớp con khai báo một hàm **cùng tên** với hàm của cha thì hàm đó **che** (hide) hàm của cha. Quy tắc che là theo **tên**, không theo danh sách kiểu tham số: tìm tên `in` trong lớp con trước, thấy là dừng, **không** nhìn lên cha nữa.

Đây chưa phải "ghi đè" (override) của **đa hình** (polymorphism: một lời gọi tự chạy đúng hàm theo đối tượng thật), thứ cần `virtual` ở Bài 33.

Hệ quả bất ngờ: giả sử cha có hai hàm cùng tên `in(int)` và `in(const std::string&)`. Hai hàm như vậy gọi là hai bản **quá tải** (overload): cùng tên, khác kiểu tham số, trình biên dịch chọn bản theo đối số. Nếu con chỉ thêm `in(double)` thì cả hai bản của cha bị che, và `con.in("abc")` là lỗi biên dịch dù cha có bản nhận chuỗi (Ví dụ 3 chạy thật).

Có hai cách gỡ. Gọi rõ `con.Cha::in(...)`, hoặc viết `using Cha::in;` như một dòng bên trong thân lớp con (thuộc phần `public:`), nghĩa là "đưa các hàm `in` của `Cha` vào để cùng xét với `in` của con". Ví dụ 3 có thử cả hai.

### 5. Upcast, slicing và kích thước

Vì `XeChay` là một `DoChoi`, bạn gán **con trỏ hoặc tham chiếu** `XeChay` cho `DoChoi*`, `DoChoi&` được, không cần ép kiểu: đó là **upcast** (nâng lên lớp cha). Hàm nhận `const DoChoi&` nhận được mọi loại đồ chơi con. Chiều ngược lại (`DoChoi` sang `XeChay`) không tự chuyển được, vì một `DoChoi` thường chưa chắc là xe. Ép kiểu tường minh vẫn biên dịch được nhưng dễ sai (gọi là downcast, nói ở bài sau).

Qua `DoChoi&` bạn chỉ **thấy** phần `DoChoi`. Hàm nào được gọi lúc này do **kiểu khai báo** (`DoChoi&`) quyết định, nên hàm `gioiThieu` của cha chạy dù đối tượng thật là xe (Ví dụ 4). Đó **chưa phải đa hình**: Bài 33 sẽ thêm `virtual` để đổi đúng chuyện này.

Gán **cả đối tượng** `XeChay` vào một biến kiểu `DoChoi` (không phải tham chiếu) thì chỉ phần cha được chép, phần xe bị cắt mất: gọi là **slicing** (cắt lát). Bài 33 dạy kỹ; ở đây chỉ cần nhớ bẫy là có thật, và Ví dụ 4 có một dòng làm vậy.

Cuối cùng, `sizeof(Con)` không nhỏ hơn `sizeof(Cha)` vì món con chứa cả phần cha; thường là lớn hơn. Con số cụ thể tùy máy và trình biên dịch (có **căn lề**: máy chèn byte đệm để mỗi thành viên nằm ở địa chỉ thuận tiện), nên chỉ nên tin con số mình đo trên máy mình.

### 6. "Là một" hay "có một"

Hai cách dùng lại code: **kế thừa** nói "Con **là một** Cha" (is-a), còn **thành viên** nói "Con **có một** Cha" (has-a, hay **composition**, tạm dịch "ghép"). Xe hơi **có một** động cơ, không **là một** động cơ, nên động cơ là thành viên.

Quy tắc: **chỉ kế thừa công khai khi đúng là is-a**, nghĩa là mọi nơi dùng `Cha` thì thay bằng `Con` vẫn đúng. "Muốn dùng lại hàm của cha" không phải lý do: dùng thành viên được mà không dính chặt hai lớp.

Mình đã chạy hai bản của xe. Bản đúng: `XeHoi` giữ `DongCo dongCo_;` là thành viên `private` và chỉ đưa ra hàm `chay()`. Bản sai: `class XeXau : public DongCo {};` chỉ để dùng lại `khoiDong()`; khi đó hàm `lapVaoMayBom(const DongCo&)` nhận được cả xe (upcast hợp lệ), và ai cũng gọi được hàm của động cơ trên xe.

Ví dụ kinh điển là hình vuông: toán học nói vuông là chữ nhật, nhưng trong code thì sao? Ví dụ 5 cho thấy nó vỡ ở đâu. Ý tổng quát (**nguyên lý thay thế Liskov**) sẽ dạy đủ ở Bài 37; bài này chỉ cần biết câu hỏi để tự hỏi.

### 7. Chỉ nhắc: kế thừa `private`/`protected`, `final`, kế thừa đa

**Kế thừa `private`** (`class Con : private Cha`, cũng là mặc định của `class`) nghĩa là "con dùng cha để làm việc bên trong", không còn là is-a với bên ngoài: hàm của cha thành `private` trong con và upcast từ ngoài bị cấm (mình đã chạy: `class Con1 : Cha {}` rồi `Con1 a; a.ham();` ra `‘void Cha::ham() const’ is inaccessible within this context`, còn `Cha& r = a;` ra `‘Cha’ is an inaccessible base of ‘Con1’`). Kế thừa `protected` tương tự, nhưng lớp con của con vẫn thấy. Muốn "dùng lại để làm bên trong" thì thành viên thường gọn hơn.

**`final`** đặt sau tên lớp (`class Kin final {}`) cấm mọi lớp kế thừa nó ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) đã nhắc tên). Mình đã chạy: `class Con : public Kin {}` ra `error: cannot derive from ‘final’ base ‘Kin’ in derived type ‘Con’`.

**Kế thừa đa (multiple inheritance)**: `class C : public A, public B` kế thừa từ hai cha cùng lúc. Cha dựng theo thứ tự **liệt kê** `A` rồi `B`, hủy ngược lại. C++ cho phép, Go thì không có kế thừa nào. Rắc rối khi hai cha cùng có chung **một ông**, gọi là **bài toán kim cương**:

```text
        DoChoi          <- ông
        /    \
    CoPin   CoBanh      <- hai cha
        \    /
     XeDieuKhien        <- con
```

Mặc định `XeDieuKhien` chứa **hai bản** `DoChoi`, một qua `CoPin`, một qua `CoBanh`; gọi `x.ma` không biết bản nào nên lỗi biên dịch.

Mình đã chạy với `struct DoChoi { int ma = 1; };`, `struct CoPin : DoChoi {};`, `struct CoBanh : DoChoi {};`, `struct XeDieuKhien : CoPin, CoBanh {};`. `x.ma` ra `error: request for member ‘ma’ is ambiguous`; `x.CoPin::ma = 10;` rồi in `x.CoPin::ma` và `x.CoBanh::ma` ra `10 1` (hai bản riêng); `sizeof(XeDieuKhien)` là 8, gấp đôi `sizeof(DoChoi)` là 4 (máy mình). Muốn chỉ một bản thì hai cha kế thừa kiểu **`virtual`** (`: virtual DoChoi`, kế thừa ảo): mình chạy thử thì `x.ma` hợp lệ, nhưng `sizeof` lên 24 vì có thêm dữ liệu nội bộ. Chi tiết thuộc phần nâng cao, không dạy ở đây.

## 💻 Ví dụ code

### Ví dụ 1: cha dựng trước, con hủy trước

`Pin` là thành viên của `XeChay` để thấy luôn thứ tự giữa cha, thành viên và thân hàm tạo. Mỗi hàm tạo và hàm hủy đều in một dòng.

```cpp
#include <iostream>
#include <string>

class Pin {
public:
    Pin() { std::cout << "  tao Pin\n"; }
    ~Pin() { std::cout << "  huy Pin\n"; }
};

class DoChoi {
public:
    DoChoi(std::string ten) : ten_(ten) {                         // (1)
        std::cout << "  tao DoChoi " << ten_ << "\n";
    }
    ~DoChoi() {
        std::cout << "  huy DoChoi " << ten_ << "\n";
    }

private:
    std::string ten_;
};

class XeChay : public DoChoi {                                    // (2)
public:
    XeChay(std::string ten, int toc) : DoChoi(ten), toc_(toc) {   // (3)
        std::cout << "  than ham tao XeChay\n";                   // (4)
    }
    ~XeChay() {
        std::cout << "  than ham huy XeChay\n";                   // (5)
    }

private:
    Pin pin_;                                                     // (6)
    int toc_;
};

int main() {
    XeChay x("xe dua", 30);
    std::cout << "het main\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `XeChay x("xe dua", 30)` | Vào (3). Danh sách gọi `DoChoi(ten)` (1) trước: in `tao DoChoi` | `x` bắt đầu bằng phần `DoChoi` (`ten_`) |
| (6) | Thành viên của con dựng theo khai báo: `pin_` in `tao Pin`; `toc_` là `int` | phần `DoChoi`, rồi `pin_`, rồi `toc_` |
| (4) | Thân hàm tạo con chạy cuối cùng | `x` đủ cả ba phần |
| `return 0` rồi hết `main` | `x` chết: thân hàm hủy con (5), rồi `pin_`, rồi phần cha (ngược lại hoàn toàn) | `x` biến mất |

**Kết quả khi chạy:**

```text
  tao DoChoi xe dua
  tao Pin
  than ham tao XeChay
het main
  than ham huy XeChay
  huy Pin
  huy DoChoi xe dua
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Hai **Thử thay đổi** (đã chạy):

- **Bỏ `DoChoi(ten)` khỏi danh sách (3)**, chỉ để `: toc_(toc)`: lỗi biên dịch `error: no matching function for call to ‘DoChoi::DoChoi()’`. g++ ghi chú rằng hàm tạo của cha cần một đối số mà lời gọi ngầm không có.
- **Viết ngược `: toc_(toc), DoChoi(ten)`**: chạy ra **cùng** kết quả như trên, g++ chỉ cảnh báo `-Wreorder`.

### Ví dụ 2: `protected` và `DoChoi::gioiThieu()`

`ten_` giờ là `protected` để `XeChay` đọc được; `maKho_` vẫn `private`. Hàm `gioiThieu` của con gọi hàm cùng tên của cha (5), rồi in thêm.

```cpp
#include <iostream>
#include <string>

class DoChoi {
public:
    DoChoi(std::string ten) : ten_(ten) {}
    void gioiThieu() const {                                     // (1)
        std::cout << "do choi: " << ten_ << "\n";
    }

protected:
    std::string ten_;                                            // (2)

private:
    int maKho_ = 7;                                              // (3)
};

class XeChay : public DoChoi {
public:
    XeChay(std::string ten, int toc) : DoChoi(ten), toc_(toc) {}
    void gioiThieu() const {                                     // (4)
        DoChoi::gioiThieu();                                     // (5)
        std::cout << "  xe chay toc do " << toc_ << ", ten_ = " << ten_ << "\n";   // (6)
    }

private:
    int toc_;
};

int main() {
    XeChay x("xe dua", 30);
    x.gioiThieu();                                               // (7)
    x.DoChoi::gioiThieu();                                       // (8)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (7) `x.gioiThieu()` | Tìm tên trong `XeChay` trước: thấy (4), chạy bản của con | `x`: `ten_` "xe dua", `toc_` 30 |
| (5) | `DoChoi::gioiThieu()` gọi hàm (1) của cha: in `do choi: xe dua` | không đổi |
| (6) | Con đọc `ten_` được vì `protected` (2): in `xe chay toc do 30, ten_ = xe dua` | không đổi |
| (8) | Từ ngoài, `x.DoChoi::gioiThieu()` gọi thẳng bản của cha: in `do choi: xe dua` | không đổi |

**Kết quả khi chạy:**

```text
do choi: xe dua
  xe chay toc do 30, ten_ = xe dua
do choi: xe dua
```

Mình chạy với ASan + UBSan: sạch. Ba **Thử thay đổi về truy cập** (đã chạy, đều lỗi biên dịch):

- **Thêm `std::cout << x.ten_;` vào `main`**: `error: ‘std::string DoChoi::ten_’ is protected within this context`.
- **Thêm `std::cout << x.maKho_;` vào `main`**: `‘int DoChoi::maKho_’ is private within this context`.
- **Viết `std::cout << maKho_;` trong hàm của `XeChay`**: vẫn lỗi `private` như trên, vì con cũng không đụng được phần `private` của cha.

### Ví dụ 3: che hàm (name hiding)

`Ghi` có hai bản quá tải `in`; `GhiMau` chỉ thêm `in(double)`.

```cpp
#include <iostream>
#include <string>

class Ghi {
public:
    void in(int n) const { std::cout << "Ghi::in(int) " << n << "\n"; }                    // (1)
    void in(const std::string& s) const { std::cout << "Ghi::in(string) " << s << "\n"; }  // (2)
};

class GhiMau : public Ghi {
public:
    void in(double d) const { std::cout << "GhiMau::in(double) " << d << "\n"; }           // (3)
};

int main() {
    GhiMau g;
    g.in(5);                                                // (4)
    g.Ghi::in(5);                                           // (5)
    g.Ghi::in(std::string("abc"));                          // (6)
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (4) `g.in(5)` | Tìm `in` trong `GhiMau`: thấy (3), dừng. Cha (1) (2) không được xét; `5` đổi sang `double`, in `GhiMau::in(double) 5` | `g` không đổi (hàm không sửa gì) |
| (5) | `Ghi::in` chỉ rõ cha, nên (1) khớp `int`: in `Ghi::in(int) 5` | không đổi |
| (6) | Cùng cách, bản (2) của cha: in `Ghi::in(string) abc` | không đổi |

**Kết quả khi chạy:**

```text
GhiMau::in(double) 5
Ghi::in(int) 5
Ghi::in(string) abc
```

Mình chạy với ASan + UBSan: sạch. Hai **Thử thay đổi** (đã chạy):

- **Thêm `g.in(std::string("abc"));` vào `main`**: lỗi biên dịch `error: cannot convert ‘std::string’ {aka ‘std::__cxx11::basic_string<char>’} to ‘double’`; bản `in(const std::string&)` của cha có đó nhưng không được xét.
- **Thêm dòng `using Ghi::in;` trong lớp `GhiMau`, ngay trước (3), rồi thêm `g.in(std::string("abc"));` và `g.in(2.5);` vào `main`**: `g.in(5)` giờ in `Ghi::in(int) 5` (bản `int` khớp chính xác hơn), `g.in(std::string("abc"))` chạy được (bản của cha), và `g.in(2.5)` vẫn vào `GhiMau::in(double)`.

### Ví dụ 4: upcast, gọi theo kiểu khai báo, slicing, `sizeof`

`XeChay` có `gioiThieu` riêng (che hàm của cha). Chương trình gọi nó qua `x`, qua `DoChoi&`, qua `DoChoi*`, rồi gán cả đối tượng vào một biến `DoChoi`.

```cpp
#include <iostream>
#include <string>

class DoChoi {
public:
    DoChoi(std::string ten) : ten_(ten) {}
    void gioiThieu() const { std::cout << "DoChoi " << ten_ << "\n"; }
    const std::string& ten() const { return ten_; }

private:
    std::string ten_;
};

class XeChay : public DoChoi {
public:
    XeChay(std::string ten, int toc) : DoChoi(ten), toc_(toc) {}
    void gioiThieu() const { std::cout << "XeChay " << ten() << " toc " << toc_ << "\n"; }

private:
    int toc_;
};

int main() {
    XeChay x("xe dua", 30);
    DoChoi& r = x;                                           // (1)
    DoChoi* p = &x;                                          // (2)
    x.gioiThieu();
    r.gioiThieu();                                           // (3)
    p->gioiThieu();
    DoChoi cat = x;                                          // (4)
    cat.gioiThieu();
    std::cout << "sizeof DoChoi = " << sizeof(DoChoi)
              << ", sizeof XeChay = " << sizeof(XeChay) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) (2) | Upcast: `r` và `p` trỏ vào chính `x`, nhưng kiểu khai báo là `DoChoi` | cùng một món `x`; qua `r` chỉ thấy phần `DoChoi` |
| `x.gioiThieu()` | Kiểu của `x` là `XeChay`: bản của con | in `XeChay xe dua toc 30` |
| (3), `p->` | Kiểu khai báo là `DoChoi`: bản của cha chạy dù đối tượng thật là xe (**chưa phải đa hình**) | in `DoChoi xe dua` hai lần |
| (4) | `cat` là một `DoChoi` riêng: chỉ chép phần cha của `x` (slicing), phần `toc_` bị bỏ | `cat` chỉ có `ten_` |

**Kết quả khi chạy** (hai số cuối đo trên máy mình, g++ 11.4, x86-64; **máy khác có thể ra số khác**, chỉ cần nhớ con ≥ cha):

```text
XeChay xe dua toc 30
DoChoi xe dua
DoChoi xe dua
DoChoi xe dua
sizeof DoChoi = 32, sizeof XeChay = 40
```

Mình chạy với ASan + UBSan: sạch. `XeChay` hơn `DoChoi` 8 byte dù chỉ thêm một `int` 4 byte: phần còn lại là byte đệm để căn lề. Với `struct A { int x; };`, `struct B : A { int y; };`, `struct C : A { char c; };` mình đo `sizeof` là 4, 8, 8: `C` thêm có 1 byte `char` mà vẫn thành 8 vì byte đệm.

**Thử thay đổi (đã chạy, đều lỗi biên dịch):** chiều ngược lại không tự chuyển được. `XeChay y = r;` cho `error: conversion from ‘DoChoi’ to non-scalar type ‘XeChay’ requested`; `XeChay* q = &cat;` cho `error: invalid conversion from ‘DoChoi*’ to ‘XeChay*’`.

### Ví dụ 5: hình vuông có phải hình chữ nhật không?

Hình vuông kế thừa hình chữ nhật. Hàm `keoDaiNgang` nhận `HinhChuNhat&` và nhân đôi chiều rộng: với chữ nhật thì hoàn toàn bình thường (5).

```cpp
#include <iostream>

class HinhChuNhat {
public:
    HinhChuNhat(int rong, int cao) : rong_(rong), cao_(cao) {}
    void datRong(int r) { rong_ = r; }                       // (1)
    int rong() const { return rong_; }
    int cao() const { return cao_; }

private:
    int rong_;
    int cao_;
};

class HinhVuong : public HinhChuNhat {                       // (2)
public:
    HinhVuong(int canh) : HinhChuNhat(canh, canh) {}         // (3)
};

void keoDaiNgang(HinhChuNhat& h) {                           // (4)
    h.datRong(h.rong() * 2);
}

int main() {
    HinhChuNhat cn(3, 3);
    keoDaiNgang(cn);                                         // (5)
    std::cout << "chu nhat: " << cn.rong() << " x " << cn.cao() << "\n";
    HinhVuong v(3);
    keoDaiNgang(v);                                          // (6)
    std::cout << "hinh vuong: " << v.rong() << " x " << v.cao() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (5) | Chữ nhật 3 x 3 thành 6 x 3: đúng ý | `cn`: rong_ 6, cao_ 3 |
| (3) | `HinhVuong(3)` dựng cha là 3 x 3 | `v`: rong_ 3, cao_ 3 |
| (6) | `v` là một `HinhChuNhat` (upcast) nên `keoDaiNgang` nhận; (1) chỉ đổi `rong_` | `v`: rong_ 6, cao_ 3 |

**Kết quả khi chạy:**

```text
chu nhat: 6 x 3
hinh vuong: 6 x 3
```

Mình chạy với ASan + UBSan: sạch. Chương trình biên dịch và chạy suôn sẻ, nhưng **"hình vuông" 6 x 3 không còn vuông**: bất biến "hai cạnh bằng nhau" ([Bài 31](31-lop-dong-goi.md)) bị vỡ qua hàm của cha. Cha có một **hợp đồng** ngầm: "đổi chiều rộng thì chiều cao giữ nguyên", và `HinhVuong` không giữ được hợp đồng đó. Vì vậy `HinhVuong` **không thay được** `HinhChuNhat`, và "vuông là chữ nhật" trong toán không thành is-a trong code. Đây là lỗi thiết kế chứ không phải thiếu tính năng của C++; cách sửa (như thiết kế lại hai lớp không kế thừa nhau) sẽ bàn ở Bài 37.

## Go: embedding giống ở một chỗ, khác ở ba chỗ

!!! info "Bạn biết Go?"
    Go không có kế thừa. Thứ gần nhất là **embedding** (nhúng): `type XeChay struct { dochoi.DoChoi; Toc int }`. Mình đã chạy một gói Go 1.27.1 nhỏ để kiểm:
    - **Giống**: gọi `x.GioiThieu()` được như hàm của XeChay (hàm "được nâng lên"); viết `x.DoChoi.GioiThieu()` thì gọi rõ phần nhúng, như `Cha::ham()`. Hàm cùng tên đặt ở struct ngoài che hàm nhúng (mình chạy: `x.Ten2()` ra bản của `XeChay`, `x.DoChoi.Ten2()` ra bản của `DoChoi`).
    - **Khác 1, không có upcast**: `var d dochoi.DoChoi = x` lỗi `cannot use x (variable of struct type XeChay) as dochoi.DoChoi value in variable declaration`; phải viết `x.DoChoi` lấy phần nhúng ra (một bản sao).
    - **Khác 2, receiver vẫn là phần cha**: bên trong hàm của `DoChoi`, `d` có kiểu `dochoi.DoChoi` (mình in `%T`); khi nó gọi `d.Ten2()` thì chạy bản của `DoChoi`, không phải bản che của `XeChay`. Với struct nhúng, Go không có thứ như `this` trỏ về "con".
    - **Khác 3, không có `protected`**: Go có hai mức: viết hoa (thấy từ package khác) và viết thường (chỉ trong package). Mình chạy: `x.ma` ở package khác lỗi `cannot refer to unexported field ma`.
    - **Đa hình** của Go là **interface**: `XeChay` thỏa interface `GioiThieuer` nhờ hàm được nâng lên, mà không cần khai báo gì (mình chạy). Bài 33 sẽ so với `virtual` của C++.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Thứ tự gọi constructor/destructor trong kế thừa là gì?"
    Hàm tạo: cha trước, rồi thành viên của con theo thứ tự khai báo, rồi thân hàm tạo con. Hàm hủy ngược lại hoàn toàn: thân hàm hủy con, thành viên con, rồi cha. Muốn dùng hàm tạo nào của cha thì gọi nó trong danh sách khởi tạo của con; không gọi thì dùng hàm tạo không tham số của cha, và cha không có thì lỗi biên dịch. Kế thừa đa: cha dựng theo thứ tự liệt kê.

??? question "`protected` khác `private` thế nào?"
    Cả hai cấm code bên ngoài. `private` chỉ cho code của chính lớp; `protected` cho thêm cả lớp con. Dữ liệu `protected` làm lớp con ghi được vào trạng thái của cha, nên bất biến của cha khó giữ; thường chọn dữ liệu `private` và hàm `protected`.

??? question "Kế thừa hay composition (has-a): chọn cái nào?"
    Kế thừa công khai chỉ khi đúng is-a: mọi nơi dùng `Cha` thay bằng `Con` vẫn đúng (Liskov). Nếu chỉ muốn dùng lại cài đặt thì dùng thành viên: ghép lỏng hơn, che được phần không muốn lộ, đổi được sau này. Mặc định nên nghiêng về composition; hình vuông/chữ nhật là ví dụ kế thừa nghe hợp lý mà vỡ.

??? question "Bài toán kim cương (diamond problem) là gì?"
    Lớp `D` kế thừa đa từ `B` và `C`, cả hai cùng kế thừa `A`. Mặc định `D` chứa hai bản `A`, nên gọi thành viên của `A` qua `D` là mơ hồ (lỗi biên dịch). Cách chữa là kế thừa `virtual` (`: virtual A`) để chỉ có một bản `A`, đổi lại thêm chi phí và độ phức tạp (cách cài đặt tùy trình biên dịch); cách tránh gọn hơn là thiết kế sao cho không có kim cương.

??? question "Name hiding (che hàm) là gì?"
    Hàm ở lớp con cùng **tên** với hàm của cha thì che toàn bộ hàm cùng tên của cha, kể cả các bản quá tải khác kiểu tham số, vì tìm tên dừng ở lớp con. Gọi bản bị che phải viết `Cha::ham()` hoặc kéo tên về bằng `using Cha::ham;`. Đây chưa phải ghi đè đa hình (cần `virtual`, Bài 33).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Kế thừa chỉ để dùng lại code"
    Kế thừa công khai là lời hứa "là một" với mọi nơi nhận `Cha&`; dùng nó chỉ để khỏi gõ lại hàm thì `XeXau` ở mục 6 lắp được vào máy bơm nước. Muốn dùng lại cài đặt thì đặt thành viên.

!!! warning "Lỗi 2: Thêm `in(double)` ở con rồi hỏi vì sao `in` của cha biến mất"
    Hàm cùng tên ở con che mọi hàm cùng tên của cha, không chỉ hàm cùng kiểu tham số. Thêm `using Cha::in;` hoặc gọi `Cha::in(...)`.

!!! warning "Lỗi 3: Quên gọi hàm tạo cần tham số của cha, hoặc gán `Cha c = con;`"
    Cha chỉ có hàm tạo cần tham số mà con không gọi trong danh sách khởi tạo thì lỗi `no matching function for call to ‘DoChoi::DoChoi()’`. Gán cả đối tượng con vào biến cha thì chép mất phần con (slicing): dùng tham chiếu hay con trỏ.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="32" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau rồi chạy `Con o;` (mỗi lần in một chữ cái). Chương trình in ra gì?

```text
struct Pin { Pin() { std::cout << "p"; } ~Pin() { std::cout << "P"; } };
struct Cha { Cha() { std::cout << "c"; } ~Cha() { std::cout << "C"; } };
struct Con : Cha {
    Pin pin_;
    Con() { std::cout << "n"; }
    ~Con() { std::cout << "N"; }
};
int main() { Con o; }
```

- `pcnNCP`, vì thành viên của con dựng trước cả phần cha
- `cpnCPN`, vì hủy theo đúng thứ tự đã dựng ra
- `cpnNPC`, vì cha dựng trước, hủy sau cùng
- `ncpPCN`, vì thân hàm con chạy trước phần cha

<p class="giai-thich" markdown>Cha dựng trước (`c`), rồi thành viên của con (`p`), rồi thân hàm tạo con (`n`); hủy thì ngược lại: thân hàm hủy con (`N`), thành viên (`P`), cuối cùng cha (`C`). Thành viên của con không vượt lên trước cha. Hủy không theo thứ tự đã dựng mà theo thứ tự ngược. Thân hàm tạo con chạy sau khi cha và thành viên đã xong.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Thành viên `protected` của `Cha` được truy cập từ đâu?

- Từ code của chính `Cha` và của các lớp con, nhưng không từ code bên ngoài
- Chỉ từ code của chính `Cha`, còn lớp con thì phải dùng hàm công khai
- Từ lớp con và từ bên ngoài, nhưng bên ngoài phải đi qua hàm công khai
- Từ mọi lớp cùng thư mục, vì `protected` mở theo tệp chứ không theo lớp

<p class="giai-thich" markdown>`protected` mở thêm một cửa cho lớp con so với `private`, còn bên ngoài vẫn bị chặn (g++ báo `is protected within this context`). Mức "chỉ chính lớp" là của `private`, không phải `protected`. Bên ngoài không có đường vòng nào qua hàm công khai: truy cập thẳng vào thành viên `protected` là lỗi. Và quyền truy cập C++ tính theo lớp, không theo tệp.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đoạn sau (mọi hàm đều có thân). Điều nào đúng?

```text
struct Cha { void in(int); void in(const char*); };
struct Con : Cha { void in(double); };
Con c;
c.in(5);       // dòng 1
c.in("abc");   // dòng 2
```

- Dòng 1 gọi `Cha::in(int)` vì khớp chính xác hơn, và dòng 2 gọi `Cha::in(const char*)`
- Dòng 1 gọi `Con::in(double)`, và dòng 2 lỗi biên dịch vì chuỗi không đổi được sang `double`
- Dòng 1 gọi `Con::in(double)`, và dòng 2 gọi `Cha::in(const char*)` vì con không có bản chuỗi
- Cả hai dòng lỗi biên dịch vì `in` của con và của cha trùng tên nên mơ hồ

<p class="giai-thich" markdown>Việc tìm tên `in` dừng ngay ở `Con` vì nó có hàm tên đó, nên `Cha::in` không được xét: dòng 1 chọn `Con::in(double)` (đổi `5` sang `double`), dòng 2 không có bản nào nhận được chuỗi. Khớp chính xác hơn chỉ so giữa các hàm đã tìm thấy, mà các hàm của cha chưa được xét. Cũng không có bước "không thấy ở con thì xuống cha" sau khi con đã có tên đó. Và không có mơ hồ nào ở đây: kết quả là dòng 1 chạy và dòng 2 lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Chương trình in ra gì?

```text
struct Cha { void noi() const { std::cout << "cha"; } };
struct Con : Cha { void noi() const { std::cout << "con"; } };
int main() {
    Con c;
    Cha& r = c;
    r.noi();
    c.noi();
}
```

- `concon`, vì `r` thực ra trỏ vào một `Con` nên chạy hàm của con
- Không biên dịch được, vì không gán `Con` cho `Cha&` được
- `chacon`, vì hàm nào chạy tùy kiểu của biến dùng để gọi
- `chacha`, vì mọi lời gọi qua đối tượng `Con` đều dùng hàm của cha

<p class="giai-thich" markdown>`r` có kiểu khai báo `Cha&` nên `r.noi()` gọi `Cha::noi` (in `cha`), còn `c` có kiểu `Con` nên in `con`; không có `virtual` thì kiểu biến quyết định (Bài 33 đổi điều này). Đối tượng thật là `Con` không làm hàm của con chạy khi gọi qua `Cha&`. Gán `Con` cho `Cha&` hợp lệ (upcast), nên chương trình biên dịch được. Và `c.noi()` có kiểu `Con` nên dùng hàm của con, không phải của cha.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn sau. Dòng nào lỗi biên dịch?

```text
struct A { int x; };
struct B : A {};
struct C : A {};
struct D : B, C {};
D d;
d.x = 1;       // dòng 1
d.B::x = 1;    // dòng 2
```

- Cả hai dòng, vì `D` có hai cha nên mọi thành viên của cha đều bị mơ hồ
- Chỉ dòng 2, vì cú pháp `B::x` chỉ dùng được bên trong hàm của lớp
- Không dòng nào, vì trong `A` chỉ khai báo một `x` nên chỉ có một bản trong `D`
- Chỉ dòng 1, vì `D` chứa hai bản `A` nên `x` không rõ là của bản nào

<p class="giai-thich" markdown>Mỗi đường (qua `B`, qua `C`) mang một bản `A` riêng, nên `d.x` mơ hồ (`request for member ‘x’ is ambiguous`), còn `d.B::x` chỉ rõ bản nào nên hợp lệ. Mơ hồ chỉ xảy ra với thành viên của ông `A` được kế thừa hai đường, và `d.B::x` viết ở ngoài lớp được. Chuyện `A` chỉ khai báo một `x` không đủ: mỗi bản `A` trong `D` có `x` riêng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** `HinhVuong` kế thừa `public` từ `HinhChuNhat` (có `datRong` và `datCao` đổi riêng từng cạnh). Vấn đề thiết kế nào là thật?

- Hàm của cha đổi một cạnh làm hình vuông hết vuông, nên con không thay được cha
- `HinhVuong` không biên dịch được, vì con phải tự viết lại mọi hàm đổi cạnh của cha
- Mỗi `HinhVuong` tốn gấp đôi bộ nhớ, vì trong đối tượng có hai bản của `HinhChuNhat`
- `datRong` của cha tự đổi luôn cạnh còn lại ở con nên hình vuông vẫn vuông, chỉ tốn thêm lệnh

<p class="giai-thich" markdown>Hàm của cha chỉ đổi một cạnh nên hình vuông có thể thành 6 x 3 (mình đã chạy); đó là chỗ con không giữ nổi lời hứa của cha. Con kế thừa `datRong` nên không thiếu hàm nào, chương trình vẫn biên dịch. `HinhVuong` chỉ chứa một phần cha, không phải hai. Và hàm `datRong` của cha không biết gì về con nên không tự đổi cạnh kia.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `class Con : public Cha` làm món con chứa một phần cha; thứ tự **cha dựng trước, con hủy trước** (cha, thành viên con theo khai báo, thân hàm tạo con; hủy ngược lại), muốn dùng hàm tạo nào của cha thì gọi nó trong danh sách khởi tạo (mình in ra thứ tự thật).
2. `protected` cho code của lớp và lớp con, không cho bên ngoài; hàm của cha gọi bằng `Cha::ham()`; hàm cùng **tên** ở con **che** mọi hàm cùng tên của cha kể cả các bản quá tải (name hiding, mình chạy ra lỗi thật), gỡ bằng `using Cha::ham;`.
3. Upcast con trỏ/tham chiếu Con sang Cha hợp lệ, nhưng qua kiểu Cha chỉ thấy hàm của Cha (chưa phải đa hình, Bài 33); gán cả đối tượng Con vào biến Cha làm cắt mất phần con (slicing); `sizeof(Con)` thường lớn hơn `sizeof(Cha)` (không nhỏ hơn trong mọi lần mình đo), số cụ thể tùy máy và căn lề.
4. Chỉ kế thừa công khai khi đúng "là một": mọi nơi dùng Cha thay bằng Con vẫn đúng; muốn dùng lại cài đặt thì dùng thành viên ("có một"); hình vuông kế thừa hình chữ nhật vỡ bất biến (Liskov, Bài 37).
5. `class Con : Cha` mặc định kế thừa `private`; `final` cấm kế thừa lớp; kế thừa đa dựng cha theo thứ tự liệt kê, bài toán kim cương cho hai bản của ông (gỡ bằng kế thừa `virtual`). Go: embedding gọi được hàm của "cha", nhưng không có upcast, receiver vẫn là phần nhúng, không có `protected`; đa hình bằng interface.
