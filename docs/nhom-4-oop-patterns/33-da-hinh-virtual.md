# Bài 33 — Đa hình và `virtual`: một lời gọi, đúng hàm của món thật

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Thấy tận mắt vì sao gọi hàm qua `Cha&`/`Cha*` mà không có `virtual` thì luôn chạy bản của cha, và dùng `virtual` + `override` để chạy đúng bản của món thật (g++ bắt lỗi chữ ký lệch khi có `override`, chạy thật).
    - Nói đúng vtable/vptr ở mức khái niệm: **cách cài đặt thông dụng**, chuẩn không bắt buộc, chứng minh gián tiếp bằng `sizeof` tăng 8 byte trên máy mình; biết chi phí gọi hàm ảo nhưng không thổi phồng.
    - Biết vì sao hàm hủy của lớp cha phải `virtual` (xóa qua `Cha*` mà không có thì là hành vi không xác định, chạy thật với ASan), dùng hàm thuần ảo `= 0` làm lớp trừu tượng/interface và `vector<unique_ptr<Hinh>>` chứa nhiều loại hình.
    - Nắm hai bẫy phỏng vấn: gọi hàm ảo trong hàm tạo/hàm hủy không đa hình, và **object slicing** (cắt lát) làm mất cả phần con lẫn đa hình; so với interface ngầm định của Go (đã chạy Go 1.27.1).

**Bạn cần biết trước:** [Bài 31](31-lop-dong-goi.md) (lớp, hàm tạo/hàm hủy), [Bài 32](32-ke-thua.md) (kế thừa, upcast, che hàm, thứ tự tạo/hủy), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `make_unique`, `get()`), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector`, `push_back`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, ASan), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`override`/`final` đã nhắc tên).

## 🧠 Câu chuyện mở đầu

Ở cuối [Bài 32](32-ke-thua.md), một hàm nhận `const DoChoi&` nhận được mọi món con, nhưng gọi `gioiThieu()` thì luôn ra bản của `DoChoi`. Giờ đặt cửa hàng đồ chơi: một **hộp** chứa lẫn xe chạy, gấu bông, robot, và nhân viên chỉ cần bấm nút "chơi" trên từng món. Ta muốn mỗi món **tự chơi theo cách của nó**, không phải theo cách của bản vẽ gốc.

Đó là **đa hình (polymorphism)**: cùng một lời gọi `d.choi()`, hàm chạy là hàm của **món thật** đang nằm trong hộp. Bài này dạy cách xin điều đó (`virtual`), cách nó thường được cài đặt, và những cái bẫy đi kèm. Đa hình ở đây là **lúc chạy**: món thật được xác định khi chương trình chạy. Còn `overload` ([Bài 32](32-ke-thua.md)) và `template` ([Bài 34](34-template.md)) là **lúc biên dịch**: trình biên dịch chọn xong trước khi chạy.

!!! info "Chỗ nào ví von xưởng đồ chơi không còn đúng?"
    Mục 2 nói "mỗi món dính một nhãn chỉ vào bảng cách chơi của bản vẽ": đó là cách **hay được cài đặt**, không phải điều chuẩn C++ quy định. Ví von cũng không có chỗ cho chi phí: một món có hàm ảo tốn thêm chỗ cho cái nhãn (mục 2 đo thật).

## 📖 Giải thích

### 1. `virtual` và `override`: chạy theo món thật

Không có `virtual`, hàm chạy do **kiểu khai báo** của tham chiếu/con trỏ quyết định (đã thấy ở [Bài 32](32-ke-thua.md)). Thêm `virtual` trước hàm của cha: khi gọi hàm đó qua `Cha&` hay `Cha*`, chương trình nhìn **món thật** lúc chạy và gọi bản của lớp con nếu lớp con có viết lại. Viết lại như vậy gọi là **ghi đè (override)**, khác với **che hàm** của [Bài 32](32-ke-thua.md) (che chỉ xảy ra theo tên, lúc biên dịch).

Ở lớp con, hàm ghi đè phải **cùng tên, cùng tham số, cùng `const`, cùng kiểu trả về** với hàm ảo của cha (kiểu trả về có ngoại lệ hiếm, bỏ qua). Hàm ghi đè tự thành ảo dù không viết lại `virtual`; `override` chỉ để g++ kiểm. Hãy luôn viết `override` sau hàm: nếu chữ ký lệch dù chỉ thiếu một chữ `const`, g++ báo lỗi ngay. Không có `override`, hàm lệch kia lặng lẽ thành một hàm mới (Ví dụ 1, Thử thay đổi).

### 2. Cài đặt thông dụng: vtable và vptr (chi tiết cài đặt, không phải luật)

Chuẩn C++ chỉ nói kết quả của hàm ảo, **không** nói cách làm. Mọi trình biên dịch phổ biến đều làm gần giống nhau, và đây là hình ảnh để nhớ: mỗi **bản vẽ** có hàm ảo có một **bảng cách chơi** (vtable, virtual table: danh sách hàm ảo của lớp, mỗi ô trỏ tới bản dùng cho lớp đó). Mỗi **món** làm ra dính một **nhãn nhỏ** (vptr, virtual pointer) trỏ vào bảng của bản vẽ của nó.

```text
bảng của DoChoi: [ choi -> DoChoi::choi ]     bảng của XeChay: [ choi -> XeChay::choi ]
món x (XeChay):  [ nhãn ---> bảng của XeChay ][ dữ liệu của x ... ]
p->choi():  đọc nhãn trong món p trỏ tới -> tra ô "choi" -> nhảy tới hàm ghi trong ô
```

Có hai chứng cứ gián tiếp: thêm hàm ảo đầu tiên làm `sizeof` đối tượng **tăng đúng một con trỏ** (8 byte trên máy 64-bit này), và thêm hàm ảo thứ hai thì không tăng thêm, vì nhãn chỉ có một cái. Ví dụ 2 đo thật. Vì là chi tiết cài đặt, số byte đổi theo máy/trình biên dịch; đừng viết code dựa vào nó.

**Chi phí.** Gọi hàm ảo phải đọc nhãn, tra bảng rồi nhảy gián tiếp, nên trình biên dịch thường khó **inline** (chèn thân hàm vào chỗ gọi) lời gọi đó vì lúc biên dịch chưa chắc biết hàm đích. Mỗi món cũng tốn thêm chỗ cho nhãn. Mình không đo thời gian trong bài này: thường phần này không đáng kể so với việc hàm làm; chỉ khi một vòng lặp cực nóng gọi hàm ảo rất nhiều thì mới đáng đo bằng công cụ đo hiệu năng.

### 3. Hàm hủy phải `virtual` khi dùng qua con trỏ cha

Nếu bạn xóa món `XeChay` qua con trỏ `DoChoi*` mà hàm hủy của `DoChoi` **không** `virtual`, chuẩn nói đây là **hành vi không xác định** ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Chuẩn không hứa gì; trên máy mình, hàm hủy của `XeChay` đơn giản **không chạy** (Ví dụ 3 chạy thật). Phần `XeChay` cấp phát (như `new int`) không được trả lại.

Cách chữa: đặt `virtual ~DoChoi() {...}` hoặc `virtual ~DoChoi() = default;` ([Bài 31](31-lop-dong-goi.md) mục 7 đã dạy `= default`) ở lớp cha. Quy tắc nhớ: **lớp nào định làm lớp cha đa hình thì có hàm hủy `virtual`**. `unique_ptr<DoChoi>` giữ món `XeChay` cũng xóa qua `DoChoi*`, nên cũng cần quy tắc này.

### 4. Hàm thuần ảo `= 0`, lớp trừu tượng và interface

Từ đây ví dụ đổi sang hình học cho gọn: `Hinh` là bản vẽ gốc chung, `HinhTron`, `HinhChuNhat` là bản vẽ con, và mỗi loại tính diện tích theo cách riêng nên hàm `dienTich()` tự nhiên là hàm ảo (ví von bản vẽ/món vẫn đúng). Viết `virtual double dienTich() const = 0;` là khai báo **hàm thuần ảo** (pure virtual): "lớp này không có bản dùng sẵn, mọi lớp con phải tự viết". Lớp có ít nhất một hàm thuần ảo là **lớp trừu tượng (abstract class)**: không tạo được đối tượng của nó (như `Hinh h;`, Ví dụ 4 chạy thật ra lỗi), nhưng `Hinh*` và `Hinh&` vẫn dùng để trỏ tới các lớp con. Lớp con chưa viết hết hàm thuần ảo thì cũng vẫn trừu tượng.

Lớp trừu tượng có thể có dữ liệu và hàm thường. Khi nó **chỉ** gồm hàm thuần ảo (cộng hàm hủy ảo) và không có dữ liệu thì thường gọi là **interface**: C++ không có từ khóa `interface`, đó chỉ là cách thiết kế. Tập hợp nhiều loại hình vào một dãy cần con trỏ (hoặc tham chiếu), vì hình khác loại có kích thước khác nhau: `std::vector<std::unique_ptr<Hinh>>` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)) là cách chuẩn.

### 5. Hàm tạo và hàm hủy: không có đa hình ở đó

Khi hàm tạo của `DoChoi` đang chạy, phần `XeChay` **chưa được dựng** ([Bài 32](32-ke-thua.md): cha dựng trước). Nếu cho phép gọi bản của `XeChay` thì nó sẽ đụng vào thành viên chưa tồn tại. Nên chuẩn quy định: trong hàm tạo (và hàm hủy) của lớp `L`, lời gọi hàm ảo chạy bản của **chính `L`** (hoặc của lớp cha nếu `L` không viết lại), không chạy bản của lớp con (Ví dụ 5). 

Hàm hủy cũng vậy: lúc `~DoChoi` chạy, phần `XeChay` đã bị hủy, nên hàm ảo cũng chỉ thấy bản của `DoChoi`.

Gọi hàm thuần ảo trực tiếp hay gián tiếp từ hàm tạo là hành vi không xác định theo chuẩn; trên g++ 11 mình đã chạy cả hai: gọi thẳng thì g++ cảnh báo rồi báo lỗi liên kết `undefined reference`, gọi gián tiếp thì chương trình dừng lúc chạy với `pure virtual method called` (Ví dụ 5, Thử thay đổi). Hãy tránh gọi hàm ảo trong hàm tạo/hàm hủy, hoặc nếu gọi thì chắc chắn muốn bản của chính lớp đó.

### 6. Object slicing đầy đủ

Gán hay truyền **cả đối tượng** `XeChay` vào một biến/tham số kiểu `DoChoi` (theo giá trị) thì C++ tạo một `DoChoi` **mới** và chép vào đó **chỉ phần cha** của xe: phần `XeChay` bị cắt đi, nên gọi tên này là **object slicing**. Món mới thật sự **là** một `DoChoi`, không còn là xe, nên hàm ảo cũng chạy bản của `DoChoi`: mất cả dữ liệu lẫn đa hình ([Bài 32](32-ke-thua.md) mới chỉ nhắc).

Slicing xảy ra ở hàm nhận tham số theo giá trị (`void f(DoChoi d)`), biến `DoChoi d = xe;`, và `std::vector<DoChoi>` nhét món con vào. Cách tránh: **tham chiếu hoặc con trỏ** (`const DoChoi&`, `DoChoi*`, `unique_ptr<DoChoi>`) vì chúng không tạo món mới. Lớp trừu tượng không tạo được đối tượng nên không thể bị slicing kiểu này (Ví dụ 4 chạy ra lỗi biên dịch).

### 7. Chỉ nhắc: `dynamic_cast`, `typeid`, `final`

**`dynamic_cast<Con*>(conTroCha)`** hỏi lúc chạy "món thật có phải `Con` không?": đúng thì cho con trỏ `Con*`, sai thì cho `nullptr` (Ví dụ 4). Nó chỉ dùng được với lớp có ít nhất một hàm ảo. Đây là phép ép con trỏ cha xuống con trỏ con, tức **downcast** đã hẹn ở [Bài 32](32-ke-thua.md). 

`typeid(*p)` (trong `<typeinfo>`) với lớp có hàm ảo cho thông tin kiểu thật, và tên in ra do trình biên dịch tự chọn. Cả hai thuộc nhóm "biết kiểu thật lúc chạy"; cần đến chúng nhiều thì thường là dấu hiệu nên thêm một hàm ảo thay vì hỏi kiểu.

**`final`** đặt sau hàm ảo (`void choi() const final`) cấm lớp con ghi đè tiếp (cùng từ khóa bạn đã gặp cho lớp ở [Bài 32](32-ke-thua.md)); Ví dụ 1 chạy lỗi thật.

## 💻 Ví dụ code

### Ví dụ 1: `ten()` không ảo, `choi()` ảo

`DoChoi` mới, gọn hơn [Bài 32](32-ke-thua.md). Cả hai hàm đều có bản riêng ở `XeChay`; chỉ `choi` là `virtual`. Hàm `thu` nhận `const DoChoi&` rồi gọi cả hai.

```cpp
#include <iostream>

class DoChoi {
public:
    void ten() const { std::cout << "do choi\n"; }                            // (1)
    virtual void choi() const { std::cout << "DoChoi: choi chung chung\n"; }  // (2)
};

class XeChay : public DoChoi {
public:
    void ten() const { std::cout << "xe chay\n"; }                            // (3)
    void choi() const override { std::cout << "XeChay: lao di vun vut\n"; }   // (4)
};

void thu(const DoChoi& d) {                                                   // (5)
    d.ten();
    d.choi();
}

int main() {
    XeChay x;
    thu(x);                                                                   // (6)
    const DoChoi* p = &x;                                                     // (7)
    p->choi();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (6) `thu(x)` | `d` là tham chiếu `DoChoi&` tới chính `x` (upcast) | `x` có nhãn trỏ vào bảng của `XeChay` (chi tiết cài đặt) |
| `d.ten()` | `ten` không ảo: kiểu khai báo là `DoChoi`, nên chạy (1) | in `do choi` |
| `d.choi()` | `choi` ảo: nhìn món thật là `XeChay`, chạy (4) | in `XeChay: lao di vun vut` |
| (7) `p->choi()` | Con trỏ cũng vậy: món thật là `XeChay` | in dòng của `XeChay` lần nữa |

**Kết quả khi chạy:**

```text
do choi
XeChay: lao di vun vut
XeChay: lao di vun vut
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Bỏ `virtual` ở (2)** (và bỏ `override` ở (4)): cả ba dòng ra bản của `DoChoi`: `do choi`, `DoChoi: choi chung chung`, `DoChoi: choi chung chung`. Không có `virtual`, kiểu khai báo quyết định.
- **Giữ `virtual`, viết (4) thành `void choi() override`** (thiếu `const`): `error: ‘void XeChay::choi()’ marked ‘override’, but does not override`.
- **Giữ `virtual`, bỏ cả `override` lẫn `const` ở (4)**: biên dịch được, g++ 11 với `-Wall -Wextra` **không cảnh báo gì**, và kết quả ra bản của `DoChoi` như khi không có `virtual`. Đây là lý do nên luôn viết `override`.
- **Thêm `final` sau (2)** (`virtual void choi() const final`): `error: virtual function ‘virtual void XeChay::choi() const’ overriding final function`.

### Ví dụ 2: `sizeof` khi có hàm ảo

Ba struct cùng có một `long long x` (8 byte). Chỉ khác ở chỗ có hàm ảo hay không, và có một hay hai hàm ảo. (`struct` như `class` nhưng mặc định `public`, [Bài 31](31-lop-dong-goi.md).)

```cpp
#include <iostream>

struct Thuong { long long x; void f() {} };
struct CoAo { long long x; virtual void f() {} };
struct HaiAo { long long x; virtual void f() {} virtual void g() {} };
struct Rong {};
struct RongAo { virtual void f() {} };

int main() {
    std::cout << "Thuong " << sizeof(Thuong) << "\n";
    std::cout << "CoAo   " << sizeof(CoAo) << "\n";
    std::cout << "HaiAo  " << sizeof(HaiAo) << "\n";
    std::cout << "Rong   " << sizeof(Rong) << ", RongAo " << sizeof(RongAo) << "\n";
    std::cout << "con tro " << sizeof(void*) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `Thuong` | Chỉ có `x`; hàm thường không nằm trong đối tượng | `[x: 8]` |
| `CoAo` | Thêm hàm ảo: có thêm nhãn trỏ vào bảng | `[nhãn: 8][x: 8]` |
| `HaiAo` | Hàm ảo thứ hai thêm ô vào **bảng**, không thêm vào món | vẫn `[nhãn][x]` |
| `Rong` / `RongAo` | Lớp rỗng tối thiểu 1 byte; có hàm ảo thì chỉ còn cái nhãn | `[1]` so với `[nhãn: 8]` |

**Kết quả khi chạy** (g++ 11.4, x86-64; **máy khác có thể ra số khác**, chỉ cần nhớ mẫu "hàm ảo đầu tiên thêm cỡ một con trỏ"):

```text
Thuong 8
CoAo   16
HaiAo  16
Rong   1, RongAo 8
con tro 8
```

Mình chạy với ASan + UBSan: sạch. Hàm ảo đầu tiên làm đối tượng tăng 8 byte, bằng `sizeof(void*)` trên máy này. Hàm ảo thứ hai không tăng thêm, và `RongAo` lớn hơn `Rong`: khớp với hình ảnh "nhãn trong món", nhưng chỉ là chứng cứ gián tiếp cho một cách cài đặt.

### Ví dụ 3: hàm hủy `virtual`

`XeChay` giữ một `int` cấp phát bằng `new` (cái "pin") và trả lại ở hàm hủy. Món được tạo bằng `new XeChay()` nhưng xóa qua `DoChoi*`.

```cpp
#include <iostream>

class DoChoi {
public:
    DoChoi() { std::cout << "  tao DoChoi\n"; }
    virtual ~DoChoi() { std::cout << "  huy DoChoi\n"; }            // (1)
};

class XeChay : public DoChoi {
public:
    XeChay() : pin_(new int(100)) { std::cout << "  tao XeChay, lay pin\n"; }
    ~XeChay() { delete pin_; std::cout << "  huy XeChay, tra pin\n"; }   // (2)

private:
    int* pin_;
};

int main() {
    DoChoi* p = new XeChay();                                       // (3)
    delete p;                                                       // (4)
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) | Dựng cha rồi con ([Bài 32](32-ke-thua.md)); `p` kiểu `DoChoi*` trỏ vào món `XeChay` | kho: món `XeChay` + `pin_` trỏ tới một `int` 100 |
| (4) | Có `virtual` ở (1): `delete` nhìn món thật, gọi `~XeChay` (2) trước, rồi `~DoChoi` | hai khối ở kho đều được trả |

**Kết quả khi chạy:**

```text
  tao DoChoi
  tao XeChay, lay pin
  huy XeChay, tra pin
  huy DoChoi
xong
```

Mình chạy với ASan + UBSan: sạch. **Thử thay đổi: bỏ chữ `virtual` ở (1)** (đã chạy ba cách):

- **Không dùng sanitizer**: in `tao DoChoi`, `tao XeChay, lay pin`, `huy DoChoi`, `xong`, thoát 0. Dòng `huy XeChay` biến mất, tức `delete pin_` không chạy.
- **Có ASan**: chương trình bị chặn với `AddressSanitizer: new-delete-type-mismatch ... size of the allocated type: 8 bytes; size of the deallocated type: 1 bytes`.
- **Tắt riêng cảnh báo đó** (`ASAN_OPTIONS=new_delete_type_mismatch=0`): LeakSanitizer báo `Direct leak of 4 byte(s)` tại `new int(100)`.

Chuẩn gọi cả tình huống này là hành vi không xác định, nên ba kết quả trên chỉ là cái mình thấy trên g++ 11.4.

### Ví dụ 4: lớp trừu tượng và `vector<unique_ptr<Hinh>>`

Ví dụ này tạm rời xưởng đồ chơi sang hình học (mục 4). `Hinh` là interface (chỉ hàm thuần ảo và hàm hủy ảo). Hai lớp hình khác loại nằm chung một dãy. Hàm `dienTich` được gọi qua con trỏ cha nên đa hình.

```cpp
#include <iostream>
#include <memory>
#include <vector>

class Hinh {
public:
    virtual ~Hinh() = default;
    virtual double dienTich() const = 0;                            // (1)
};

class HinhChuNhat : public Hinh {
public:
    HinhChuNhat(double rong, double cao) : rong_(rong), cao_(cao) {}
    double dienTich() const override { return rong_ * cao_; }
private:
    double rong_;
    double cao_;
};

class HinhTron : public Hinh {
public:
    explicit HinhTron(double r) : r_(r) {}
    double dienTich() const override { return 3.14 * r_ * r_; }
    double banKinh() const { return r_; }
private:
    double r_;
};

int main() {
    std::vector<std::unique_ptr<Hinh>> cacHinh;                     // (2)
    cacHinh.push_back(std::make_unique<HinhChuNhat>(3, 4));         // (3)
    cacHinh.push_back(std::make_unique<HinhTron>(2));
    double tong = 0;
    for (const auto& h : cacHinh) {
        std::cout << "dien tich " << h->dienTich() << "\n";         // (4)
        tong += h->dienTich();
        if (const HinhTron* t = dynamic_cast<const HinhTron*>(h.get())) {   // (5)
            std::cout << "  la hinh tron, ban kinh " << t->banKinh() << "\n";
        }
    }
    std::cout << "tong " << tong << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | Dãy giữ `unique_ptr<Hinh>`: mỗi phần tử là một con trỏ, cùng cỡ dù hình nào | `[ptr][ptr]` trỏ tới hai món ở kho |
| (3) | `unique_ptr<HinhChuNhat>` là giá trị tạm, đổi được sang `unique_ptr<Hinh>` (như upcast con trỏ) | món 0: hình chữ nhật 3 x 4 |
| (4) | `const auto&` vì `unique_ptr` không chép được ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)); `h->dienTich()` qua `Hinh*`: ảo, nên chạy bản của hình thật | in 12, rồi 12.56 |
| (5) | Khai báo `t` ngay trong điều kiện `if`; `dynamic_cast` cho `nullptr` với chữ nhật nên `if` bỏ qua, với hình tròn cho con trỏ thật | chỉ hình tròn in thêm dòng |
| hết `main` | `cacHinh` chết: mỗi `unique_ptr` xóa qua `Hinh*`, hàm hủy ảo (1) chạy hàm hủy đúng lớp | kho sạch |

**Kết quả khi chạy:**

```text
dien tich 12
dien tich 12.56
  la hinh tron, ban kinh 2
tong 24.56
```

Mình chạy với ASan + UBSan: sạch. Các **Thử thay đổi** (đã chạy, đều lỗi biên dịch):

- **Thêm `Hinh h;` vào `main`**: `error: cannot declare variable ‘h’ to be of abstract type ‘Hinh’`, kèm ghi chú `because the following virtual functions are pure within ‘Hinh’`.
- **Viết `double dienTich() { ... }` ở `HinhTron` (thiếu `const`, bỏ `override`)**: hàm này không ghi đè, `HinhTron` vẫn trừu tượng, nên `make_unique<HinhTron>` báo `invalid new-expression of abstract class type ‘HinhTron’`.
- **Đổi (2) thành `std::vector<Hinh> cacHinh;`**: `no matching function for call to ‘std::vector<Hinh>::push_back(...)’`, vì dãy giữ `Hinh` theo giá trị mà `Hinh` là lớp trừu tượng.
- **Viết `double f(Hinh h)`** (tham số `Hinh` theo giá trị): `error: cannot declare parameter ‘h’ to be of abstract type ‘Hinh’`, nên lớp trừu tượng không bị slicing kiểu này (mục 6).

### Ví dụ 5: gọi hàm ảo trong hàm tạo và hàm hủy

`DoChoi` gọi `gioiThieu()` (ảo) ở cả hàm tạo lẫn hàm hủy; `XeChay` ghi đè nó.

```cpp
#include <iostream>

class DoChoi {
public:
    DoChoi() { gioiThieu(); }                                       // (1)
    virtual ~DoChoi() { gioiThieu(); }                              // (2)
    virtual void gioiThieu() const { std::cout << "  la DoChoi\n"; }
};

class XeChay : public DoChoi {
public:
    void gioiThieu() const override { std::cout << "  la XeChay\n"; }
};

int main() {
    {
        XeChay x;                                                   // (3)
        std::cout << "goi tu ngoai:\n";
        x.gioiThieu();                                              // (4)
    }
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) | Hàm tạo `DoChoi` (1) chạy trước; lúc này phần `XeChay` chưa dựng, hàm ảo chỉ thấy bản của `DoChoi` | đang dựng phần cha |
| (4) | Món đã xong: `x.gioiThieu()` ra bản của `XeChay` | `x` đủ phần |
| hết khối | `~XeChay` chạy trước (rỗng), phần con đã hủy; rồi `~DoChoi` (2) gọi hàm ảo: chỉ thấy bản `DoChoi` | còn phần cha |

**Kết quả khi chạy:**

```text
  la DoChoi
goi tu ngoai:
  la XeChay
  la DoChoi
```

Mình chạy với ASan + UBSan: sạch. Dòng đầu và dòng cuối đều là `la DoChoi` dù món là xe: đúng quy tắc mục 5.

**Thử thay đổi (đã chạy):** đổi `gioiThieu` của `DoChoi` thành thuần ảo (`= 0`).

- **Giữ nguyên (1) và (2)** (gọi thẳng trong hàm tạo/hàm hủy): g++ cảnh báo `pure virtual ‘virtual void DoChoi::gioiThieu() const’ called from constructor` (và `from destructor`), rồi **lỗi liên kết** `undefined reference to ‘DoChoi::gioiThieu() const’`.
- **Bỏ lời gọi ở (2), và ở (1) gọi qua hàm thường `chuanBi() { gioiThieu(); }`** (gọi gián tiếp): biên dịch được, chạy in `pure virtual method called` rồi `terminate called without an active exception`.

### Ví dụ 6: slicing và cách tránh

`DoChoi` và `XeChay` như trước, `choi` là ảo, `XeChay` có thêm `toc_`. Bốn lần gọi `choi()`: tạo `DoChoi cat = x;`, hai hàm nhận theo giá trị/theo tham chiếu, và `vector<DoChoi>`.

```cpp
#include <iostream>
#include <string>
#include <vector>

class DoChoi {
public:
    DoChoi(std::string ten) : ten_(ten) {}
    virtual ~DoChoi() = default;
    virtual void choi() const { std::cout << "DoChoi " << ten_ << "\n"; }
private:
    std::string ten_;
};

class XeChay : public DoChoi {
public:
    XeChay(std::string ten, int toc) : DoChoi(ten), toc_(toc) {}
    void choi() const override { std::cout << "XeChay chay toc " << toc_ << "\n"; }
private:
    int toc_;
};

void choiTheoGiaTri(DoChoi d) { d.choi(); }                         // (1)
void choiTheoThamChieu(const DoChoi& d) { d.choi(); }               // (2)

int main() {
    XeChay x("xe dua", 30);
    DoChoi cat = x;                                                 // (3)
    cat.choi();
    choiTheoGiaTri(x);                                              // (4)
    choiTheoThamChieu(x);                                           // (5)
    std::vector<DoChoi> kho;                                        // (6)
    kho.push_back(x);
    kho[0].choi();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) | `cat` là một `DoChoi` mới, chép phần cha của `x`; `toc_` bị bỏ | `x`: [cha][toc_ 30]; `cat`: [cha] |
| `cat.choi()` | `cat` thật sự là `DoChoi`, nên ra bản của `DoChoi` | in `DoChoi xe dua` |
| (4) | Tham số `d` (1) là bản sao cắt lát, vẫn là `DoChoi` | in `DoChoi xe dua` |
| (5) | Tham chiếu (2) trỏ vào chính `x`, không có bản sao | in `XeChay chay toc 30` |
| (6) | Dãy giữ `DoChoi` theo giá trị, `push_back(x)` cắt lát | in `DoChoi xe dua` |

**Kết quả khi chạy:**

```text
DoChoi xe dua
DoChoi xe dua
XeChay chay toc 30
DoChoi xe dua
```

Mình chạy với ASan + UBSan: sạch. Chỉ chỗ (5), dùng tham chiếu, giữ được đa hình. Chương trình **không báo lỗi hay cảnh báo nào** ở ba chỗ cắt lát: g++ 11 `-Wall -Wextra` im lặng, và đó là điều làm slicing nguy hiểm.

## Go: interface ngầm định, không hàm hủy, không slicing

!!! info "Bạn biết Go?"
    Mình đã chạy một chương trình Go 1.27.1 nhỏ để kiểm các ý dưới đây.
    - **Interface không cần khai báo**: `type Hinh interface { DienTich() float64 }`, `ChuNhat` và `Tron` chỉ cần có method `DienTich` là tự thỏa, rồi `[]Hinh{ChuNhat{3,4}, Tron{2}}` chạy ra `12` và `12.56`. C++ phải ghi `class HinhTron : public Hinh` rõ ràng (kiểu này hay gọi là duck typing, "đi như vịt thì là vịt", nhưng Go kiểm lúc biên dịch).
    - **Cài đặt, chỉ để lấy ý**: một giá trị interface của Go (với trình biên dịch gc) gồm hai con trỏ: con trỏ tới bảng method (gọi là itab) và con trỏ tới dữ liệu. Mình đo `unsafe.Sizeof` được 16 cho biến `Hinh`, còn `Tron{}` vẫn 8: bảng "nằm trong giá trị interface", khác C++ nơi vptr nằm **trong đối tượng**. Đây là chi tiết cài đặt, spec Go không quy định.
    - **Method value**: `f := h.DienTich` rồi `f()` chạy bản của kiểu thật (`12.56`), tương tự gọi `h->dienTich()` qua con trỏ cha.
    - **Chặt hơn**: `Vuong` có method receiver con trỏ thì `var h Hinh = Vuong{2}` lỗi `Vuong does not implement Hinh (method DienTich has pointer receiver)`.
    - Go **không có hàm hủy**, nên không có chuyện "hàm hủy không chạy" (dọn dẹp là `defer`/`Close`), và **không có slicing**: gán `Tron` vào biến `Hinh` giữ nguyên kiểu thật. Struct nhúng cũng không có upcast ([Bài 32](32-ke-thua.md)).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Đa hình là gì? Compile-time khác runtime thế nào?"
    Đa hình là một lời gọi chạy hàm khác nhau tùy kiểu. Compile-time: trình biên dịch chọn hàm trước khi chạy, qua overload và template. Runtime: chọn theo kiểu thật của đối tượng lúc chạy, qua hàm `virtual` gọi bằng con trỏ/tham chiếu lớp cha. Runtime linh hoạt hơn (chứa nhiều loại trong một dãy), compile-time thì không tốn gián tiếp lúc chạy; [Bài 34](34-template.md) nói tiếp.

??? question "vtable hoạt động thế nào?"
    Cách cài đặt thông dụng (chuẩn không bắt buộc): mỗi lớp có hàm ảo có một bảng chứa con trỏ tới các hàm ảo của nó (vtable), mỗi đối tượng có thêm một con trỏ ẩn (vptr) trỏ tới bảng của lớp thật. Gọi hàm ảo là đọc vptr, tra ô tương ứng, nhảy gián tiếp. Chứng cứ gián tiếp: `sizeof` tăng một con trỏ khi thêm hàm ảo đầu tiên. Vì gián tiếp nên khó inline.

??? question "Tại sao hàm hủy của lớp cha phải virtual?"
    Xóa đối tượng lớp con qua con trỏ lớp cha mà hàm hủy cha không ảo là hành vi không xác định theo chuẩn; thực tế hàm hủy lớp con thường không chạy, nên tài nguyên của phần con bị rò. Hàm hủy ảo làm `delete` nhìn kiểu thật và chạy con trước, cha sau. Quy tắc: lớp định làm cha đa hình thì có hàm hủy ảo (`unique_ptr<Cha>` cũng cần).

??? question "Abstract class và interface khác nhau thế nào?"
    Abstract class là lớp có ít nhất một hàm thuần ảo (`= 0`), không tạo được đối tượng, có thể có dữ liệu và hàm thường. Interface (C++ không có từ khóa riêng) là abstract class chỉ có hàm thuần ảo, thường kèm hàm hủy ảo và không có dữ liệu. Lớp con phải viết hết hàm thuần ảo mới tạo được đối tượng.

??? question "Object slicing là gì, tránh thế nào?"
    Gán/truyền đối tượng lớp con vào biến/tham số lớp cha theo giá trị thì chỉ phần cha được chép, mất dữ liệu của con và hàm ảo chạy bản của cha. Hay gặp ở tham số theo giá trị và `vector<Cha>`. Tránh bằng tham chiếu, con trỏ, hoặc `vector<unique_ptr<Cha>>`; lớp trừu tượng chặn được kiểu theo giá trị (không tạo được `Cha` để nhận), nhưng gán qua `Cha&` vẫn biên dịch và chỉ chép phần cha.

??? question "Gọi hàm virtual trong constructor thì sao?"
    Không đa hình: trong hàm tạo của `L` (và hàm hủy), lời gọi hàm ảo chạy bản của chính `L` (hoặc lớp cha), vì phần lớp con chưa dựng (hoặc đã hủy). Gọi hàm thuần ảo từ hàm tạo là hành vi không xác định. Tránh gọi hàm ảo ở đó, hoặc dùng hàm khởi tạo riêng sau khi dựng xong.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Cha đa hình mà hàm hủy không `virtual`"
    Chạy được, không báo gì, nhưng `delete`/`unique_ptr` qua `Cha*` là hành vi không xác định và hàm hủy lớp con thường không chạy (Ví dụ 3). Cứ viết `virtual ~Cha() = default;`.

!!! warning "Lỗi 2: Ghi đè mà lệch chữ ký, không viết `override`"
    Thiếu một chữ `const` là hàm con thành hàm mới, và lời gọi qua `Cha&` vẫn chạy bản của cha (Ví dụ 1, Thử thay đổi). Hãy viết `override` ở mọi hàm ghi đè để g++ báo lỗi ngay.

!!! warning "Lỗi 3: `vector<Cha>` hoặc tham số `Cha` theo giá trị"
    Món con bị cắt lát và hàm ảo chạy bản của cha, không có thông báo nào (Ví dụ 6). Dùng `vector<unique_ptr<Cha>>`, tham chiếu hoặc con trỏ.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="33" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau (mỗi hàm in một từ). Chương trình in ra gì?

```text
struct Cha { virtual void ve() const { std::cout << "cha "; }
             void to() const { std::cout << "TO "; } };
struct Con : Cha { void ve() const override { std::cout << "con "; }
                   void to() const { std::cout << "to "; } };
int main() { Con c; const Cha& r = c; r.ve(); r.to(); c.ve(); c.to(); }
```

- `con to con to`, vì `r` trỏ vào món `Con` nên mọi hàm đều lấy bản của con
- Không biên dịch được, vì `to` ở `Con` trùng tên với `to` của `Cha`
- `con TO con to`, vì chỉ hàm ảo mới nhìn món thật
- `cha TO con to`, vì qua `r` hàm nào cũng lấy bản của `Cha`

<p class="giai-thich" markdown>`ve` là hàm ảo nên `r.ve()` chạy theo món thật (`con`), còn `to` không ảo nên `r.to()` chạy theo kiểu khai báo `Cha` (`TO`); hai lời gọi qua `c` có kiểu `Con` nên ra `con` và `to`. `virtual` chỉ có tác dụng với chính hàm được đánh dấu, không lan sang hàm khác cùng tên. Trình biên dịch không phàn nàn về `to`: nó chỉ che hàm của cha. Và `ve` đã được đánh dấu ảo nên không còn chạy theo kiểu khai báo.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau, dòng nào lỗi biên dịch?

```text
struct Hinh { virtual double dienTich() const = 0; virtual ~Hinh() = default; };
struct Vuong : Hinh { double c = 2; double dienTich() { return c * c; } };   // dòng A
int main() { Vuong v; }                                                      // dòng B
```

- Dòng B, vì `Vuong` vẫn là lớp trừu tượng: hàm thiếu `const` không ghi đè hàm của cha
- Dòng A, vì hàm ghi đè hàm thuần ảo bắt buộc phải ghi `override`
- Không dòng nào, vì `Vuong` có hàm tên `dienTich` nên đã viết hết hàm thuần ảo của cha
- Dòng A, vì `double c = 2;` không được khởi tạo ngay trong lớp

<p class="giai-thich" markdown>`dienTich()` của `Vuong` thiếu `const` nên khác chữ ký với hàm của cha, không phải ghi đè; hàm thuần ảo của cha vẫn chưa có bản nên `Vuong` còn trừu tượng và `Vuong v;` bị g++ chặn (`cannot declare variable ‘v’ to be of abstract type ‘Vuong’`, mình đã chạy). `override` là lời nhắc để g++ bắt lỗi giúp, không phải điều kiện bắt buộc của cú pháp. Trùng tên không đủ: phải cùng tham số và cùng `const`. Còn gán giá trị ngay chỗ khai báo thành viên là cú pháp hợp lệ ([Bài 31](31-lop-dong-goi.md)).</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** `Con` kế thừa `Cha`, hàm hủy của `Cha` không `virtual`, và code là `Cha* p = new Con(); delete p;`. Điều nào đúng theo chuẩn C++?

- Hàm hủy `Con` chạy rồi đến hàm hủy `Cha`, giống khi hàm hủy là `virtual`
- Chỉ hàm hủy `Cha` chạy, vì `p` có kiểu `Cha*`
- Lỗi biên dịch, vì trình biên dịch phát hiện xóa qua con trỏ cha
- Hành vi không xác định, hàm hủy của `Con` có thể không chạy

<p class="giai-thich" markdown>Chuẩn không hứa kết quả nào cho `delete` như thế, nên nó là hành vi không xác định; thực tế trên g++ 11 mình thấy hàm hủy `Con` bị bỏ qua và ASan báo lỗi, nhưng đó chỉ là một hành vi có thể gặp. Việc chạy cả hai hàm hủy là thứ `virtual` mới đem lại. "Chỉ hàm hủy `Cha` chạy" là điều thường thấy chứ không phải điều chuẩn bảo đảm. Và trình biên dịch dịch được đoạn này bình thường, không có lỗi biên dịch.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau (mỗi hàm in một từ). Chương trình in ra gì?

```text
struct Cha { Cha() { chao(); } virtual void chao() const { std::cout << "cha"; } };
struct Con : Cha { void chao() const override { std::cout << "con"; } };
int main() { Con c; c.chao(); }
```

- `concon`, vì `chao` là hàm ảo nên lấy bản của món thật
- `chacon`, vì khi hàm tạo của `Cha` chạy thì phần `Con` chưa có
- `chacha`, vì hàm ảo chỉ có tác dụng khi gọi qua con trỏ
- Hành vi không xác định, vì gọi hàm ảo trong hàm tạo khi phần `Con` chưa có

<p class="giai-thich" markdown>Trong hàm tạo của `Cha`, lời gọi `chao()` chỉ thấy bản của `Cha` (in `cha`); sau khi `c` dựng xong, `c.chao()` mới ra bản của `Con` (in `con`). Hàm ảo chỉ đa hình khi món thật đã dựng đủ, nên "lấy bản của món thật" không đúng ở hàm tạo. Gọi trực tiếp trên `c` cũng cho bản của `Con`, không liên quan đến con trỏ. Gọi hàm ảo trong hàm tạo cũng không phải hành vi không xác định: chuẩn quy định rõ nó chạy bản của lớp đang dựng, nên vẫn hợp lệ, chỉ là không đa hình. Chỉ gọi hàm *thuần ảo* (chưa có thân) từ hàm tạo mới là hành vi không xác định.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Muốn một hàm gọi `d.choi()` (`choi` là hàm ảo) cho ra bản của lớp con khi truyền một `XeChay`, cách nào đúng?

- Khai báo hàm tạo sao chép của `DoChoi` là `virtual` để bản sao nhớ kiểu thật
- Viết `static_cast<DoChoi>(x)` khi truyền, vì ép kiểu giữ lại phần con
- Nhận tham số là `const DoChoi&` thay vì `DoChoi` theo giá trị
- Thêm `override` vào hàm `choi` của `XeChay` thì bản sao sẽ nhớ kiểu thật

<p class="giai-thich" markdown>Tham chiếu không tạo món mới nên vẫn là chính chiếc `XeChay`, và hàm ảo chạy theo món thật. Hàm tạo không thể là `virtual`, và dù sao một bản sao `DoChoi` thì chỉ chứa phần cha. `static_cast<DoChoi>(x)` tạo luôn một `DoChoi` cắt lát. `override` chỉ giúp g++ kiểm chữ ký, không đổi chuyện tham số theo giá trị là một `DoChoi` mới.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Câu nào về vtable/vptr đúng?

- Mỗi đối tượng giữ một bản sao riêng của vtable, nên tốn bộ nhớ theo số hàm ảo của lớp
- Chuẩn quy định mỗi đối tượng có một vptr trỏ vào vtable của lớp thật của nó
- Mỗi hàm ảo thêm một con trỏ vào từng đối tượng, nên ba hàm ảo làm `sizeof` tăng thêm 24 byte
- Cách cài đặt thông dụng, chuẩn không bắt buộc; hàm ảo đầu tiên thường thêm một con trỏ vào `sizeof`

<p class="giai-thich" markdown>Chuẩn chỉ nói hàm ảo chọn theo kiểu thật; vtable/vptr là cách làm của các trình biên dịch phổ biến, và ví dụ `sizeof` trong bài cho thấy hàm ảo đầu tiên thêm 8 byte còn hàm thứ hai không thêm. Nó không phải điều chuẩn quy định. Nhãn trong đối tượng chỉ có một cái, thêm hàm ảo chỉ thêm ô vào bảng. Và bảng thuộc về lớp, dùng chung cho mọi đối tượng, không sao chép theo từng đối tượng.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Không có `virtual`, hàm chạy theo **kiểu khai báo** của `Cha&`/`Cha*`; có `virtual` thì chạy theo **món thật** (đa hình lúc chạy). Luôn viết `override` ở hàm ghi đè: lệch chữ ký (như thiếu `const`) thì g++ báo lỗi, không có `override` thì lặng lẽ thành hàm mới (mình chạy cả hai).
2. vtable/vptr là **cách cài đặt thông dụng**, không phải luật: mỗi lớp một bảng hàm ảo, mỗi đối tượng một con trỏ tới bảng; `sizeof` tăng 8 byte với hàm ảo đầu tiên trên máy mình (đổi theo máy). Gọi hàm ảo là gián tiếp và khó inline; mình không đo thời gian.
3. Cha đa hình cần **hàm hủy `virtual`**: xóa qua `Cha*` mà không có thì là hành vi không xác định (trên g++ 11, hàm hủy con bị bỏ qua, ASan báo lỗi). Hàm thuần ảo `= 0` tạo lớp trừu tượng (không tạo được đối tượng); lớp chỉ gồm hàm thuần ảo là interface; chứa nhiều hình khác loại bằng `vector<unique_ptr<Hinh>>`.
4. Trong hàm tạo/hàm hủy, hàm ảo **không đa hình** (chạy bản của chính lớp đó, vì phần con chưa dựng hoặc đã hủy); gọi hàm thuần ảo ở đó là hành vi không xác định. **Slicing**: truyền/gán/`vector` theo giá trị cắt phần con và mất đa hình; tránh bằng tham chiếu, con trỏ, `unique_ptr`. `dynamic_cast`/`typeid` hỏi kiểu thật lúc chạy, `final` cấm ghi đè tiếp.
5. Go: interface thỏa ngầm định, không cần khai báo (duck typing lúc biên dịch); giá trị interface giữ con trỏ tới bảng method (itab, chi tiết cài đặt, mình đo 16 byte) cạnh con trỏ dữ liệu; không có hàm hủy, không có slicing.
