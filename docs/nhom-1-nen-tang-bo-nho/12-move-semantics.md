# Bài 12 — Move semantics, rule of 5/0

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt **lvalue** và **rvalue** bằng lời thường, và nói đúng `std::move` chỉ là một phép ép kiểu ("tôi đồng ý cho lấy ruột"), chưa di chuyển gì.
    - Tự viết hàm tạo di chuyển và phép gán di chuyển cho lớp giữ con trỏ, biết đối tượng sau khi bị move chỉ nên được hủy hoặc gán lại, và biết Rule of 5 / Rule of 0.
    - Hiểu vì sao `noexcept` quan trọng với `std::vector`, và vì sao trả biến cục bộ theo giá trị thì viết `return v;` chứ không viết `return std::move(v);`.

**Bạn cần biết trước:** [Bài 06](06-tham-chieu-const.md) (tham chiếu `&`, `const&`), [Bài 09](09-unique-ptr.md) (`std::move` với `unique_ptr`) và [Bài 11](11-sao-chep-rule-of-3.md) (sao chép sâu, hàm tạo sao chép, phép gán sao chép, Rule of 3).

## 🧠 Câu chuyện mở đầu

Quay lại quyển vở dày ở [Bài 11](11-sao-chep-rule-of-3.md). Bạn của bạn cần nó.

Cách 1: **photo cả quyển**, đó là sao chép sâu: tốn giấy, tốn thời gian. Cách 2: **đưa luôn quyển vở** cho bạn, đó là **di chuyển (move)**: gần như tức thì, nhưng người đưa chỉ còn lại cái bìa rỗng.

Cách 2 chỉ hợp lý khi bạn **không cần quyển vở nữa**, ví dụ nó là tờ nháp sắp bỏ. Bài này dạy C++ phân biệt "vật còn cần" với "vật sắp bỏ", và cách viết cho lớp của bạn biết đưa luôn ruột thay vì photo.

!!! info "Chỗ nào ví dụ quyển vở không còn đúng?"
    Cái bìa rỗng của người đưa vẫn là một đối tượng thật, và **hàm hủy của nó vẫn chạy** khi hết phạm vi. Vì thế bìa rỗng phải ở trạng thái mà hàm hủy xử lý được (mục 4 và 6).

## 📖 Giải thích

### 1. Vấn đề: sao chép sâu quá tốn khi nguồn sắp biến mất

Ở [Bài 11](11-sao-chep-rule-of-3.md), sao chép sâu nghĩa là xin vùng nhớ mới và chép toàn bộ nội dung. Giả sử một hàm dựng một mảng một triệu `int` rồi trả về. Nếu nơi gọi nhận bằng cách sao chép, ta tốn một lần xin và chép khoảng bốn triệu byte, rồi **mảng gốc lập tức bị hủy** vì nó chỉ là tạm.

Chép xong rồi vứt bản gốc thì thật lãng phí: thay vì chép, ta chỉ cần **lấy con trỏ** của bản gốc. Muốn làm vậy, C++ phải có cách nhận ra "bản gốc này sắp bỏ, lấy ruột được". Cách đó là phân loại giá trị thành lvalue và rvalue.

### 2. lvalue và rvalue bằng lời thường

- **lvalue**: có **tên** và có chỗ trong bộ nhớ để quay lại dùng ở dòng sau. Ví dụ biến `x` (và vài thứ khác như `*p`).
- **rvalue**: giá trị **tạm thời**, hết câu lệnh là biến mất. Ví dụ kết quả của `x + 1`, số viết thẳng `3`, đối tượng tạm `Cay(3)`, hay giá trị một hàm trả về theo giá trị.

Mẹo hay dùng: nếu lấy được địa chỉ bằng `&` thì thường là lvalue. Mình đã thử `&(x + 1)`: g++ báo `lvalue required as unary '&' operand`, vì kết quả tạm không có chỗ ổn định để trỏ tới. Đây là cách hiểu đủ dùng cho bài này; chuẩn C++ chia mịn hơn, ta không cần.

Điều quan trọng: lấy ruột của **rvalue** thì không ai tiếc (nó sắp biến mất), còn lấy ruột của **lvalue** thì người dùng biến đó sẽ bất ngờ. Vì vậy C++ cần một loại tham chiếu chỉ nhận rvalue.

Ngoại lệ có chủ ý: `std::move(x)` bắt C++ **coi** `x` như một giá trị tạm, dù `x` vẫn sống (mục 5 nói rõ).

### 3. Tham chiếu rvalue `T&&`

Viết `int&&` (đọc "tham chiếu rvalue tới `int`") là một tham chiếu **chỉ gắn được với giá trị tạm**. Tham chiếu `int&` quen thuộc ([Bài 06](06-tham-chieu-const.md)) thì ngược lại, chỉ gắn với lvalue. C++ cho phép hai hàm **cùng tên** nếu tham số khác kiểu, và chọn hàm khớp nhất với đối số. Nhờ đó ta nhìn thấy rõ cách C++ phân loại:

```cpp
#include <iostream>
#include <utility>

void ham(int& x) {                                // (1)
    std::cout << "lvalue, x = " << x << "\n";
}

void ham(int&& x) {                               // (2)
    std::cout << "rvalue, x = " << x << "\n";
}

void chuyen(int&& r) {                            // (3)
    ham(r);                                       // (4)
}

int main() {
    int x = 1;
    ham(x);                                       // (5)
    ham(x + 1);                                   // (6)
    ham(3);                                       // (7)
    ham(std::move(x));                            // (8)
    std::cout << "sau move, x = " << x << "\n";
    chuyen(5);                                    // (9)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra |
|---|---|---|
| 1 | `int x = 1;` | Biến `x` bằng 1 |
| 2 | (5) `ham(x)` | `x` là lvalue nên chọn hàm (1), in `lvalue, x = 1` |
| 3 | (6) `ham(x + 1)` | Kết quả tạm `2` là rvalue nên chọn hàm (2), in `rvalue, x = 2` |
| 4 | (7) `ham(3)` | `3` là rvalue, chọn hàm (2), in `rvalue, x = 3` |
| 5 | (8) `ham(std::move(x))` | `std::move(x)` biến `x` thành rvalue, nên chọn hàm (2), in `rvalue, x = 1` |
| 6 | in | `x` vẫn là 1: `std::move` không đổi gì trong `x` |
| 7 | (9) `chuyen(5)` | `5` là rvalue nên gắn được vào tham số `r` của (3) |
| 8 | (4) `ham(r)` | Trong thân hàm, `r` **có tên** nên là lvalue: chọn hàm (1), in `lvalue, x = 5` |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`):

```text
lvalue, x = 1
rvalue, x = 2
rvalue, x = 3
rvalue, x = 1
sau move, x = 1
lvalue, x = 5
```

Có hai điều cần nhớ từ output. Một: hai dòng `rvalue, x = 1` và `sau move, x = 1` cho thấy `std::move(x)` làm `x` được đối xử như rvalue, nhưng giá trị của `x` không hề đổi. Hai: dòng cuối cho thấy một tham số kiểu `int&&` khi đã có tên thì bên trong hàm là lvalue (cái bẫy này gặp lại ở mục 4).

**Thử thay đổi: xóa hàm (2).** Mình đã chạy (bỏ cả `chuyen` và dòng (8)): g++ báo lỗi biên dịch `cannot bind non-const lvalue reference of type 'int&' to an rvalue of type 'int'` ở các dòng `ham(x + 1)` và `ham(3)`. Không có hàm nhận rvalue thì giá trị tạm không có chỗ gắn vào.

### 4. Hàm tạo di chuyển và phép gán di chuyển

Giờ viết cho `Mang` (giống `Day` ở [Bài 11](11-sao-chep-rule-of-3.md), đổi tên), thêm hai hàm có `&&` và cho các hàm sao chép/di chuyển in một dòng để đếm. Phần mới chỉ là các dòng (1)–(6). Phép gán sao chép bị bỏ cho gọn: vì ta khai báo hàm di chuyển, phép gán sao chép tự sinh bị **xóa** (mục 7), nên `d = lvalue` sẽ là lỗi biên dịch; ví dụ này không cần tới nó.

```cpp
#include <iostream>
#include <utility>

struct Mang {
    int n;
    int* d;
    Mang(int so, int v) {
        n = so;
        d = new int[n];
        for (int i = 0; i < n; i++) d[i] = v;
    }
    Mang(const Mang& o) {                         // sao chép (Bài 11)
        n = o.n;
        d = new int[n];
        for (int i = 0; i < n; i++) d[i] = o.d[i];
        std::cout << "copy!\n";
    }
    Mang(Mang&& o) noexcept {                     // (1)
        n = o.n;
        d = o.d;                                  // (2)
        o.n = 0;
        o.d = nullptr;                            // (3)
        std::cout << "move!\n";
    }
    Mang& operator=(Mang&& o) noexcept {          // (4)
        if (this != &o) {                         // (5)
            delete[] d;                           // (6)
            n = o.n;
            d = o.d;
            o.n = 0;
            o.d = nullptr;
        }
        std::cout << "move gan!\n";
        return *this;
    }
    ~Mang() { delete[] d; }
};

void nhan(Mang m) {
    std::cout << "nhan " << m.n << " phan tu\n";
}

int main() {
    Mang a(3, 1);
    Mang b = a;                                   // (7)
    Mang c = std::move(a);                        // (8)
    std::cout << "a.n = " << a.n << ", c.n = " << c.n << "\n";
    nhan(b);                                      // (9)
    nhan(std::move(b));                           // (10)
    Mang d(2, 0);
    d = Mang(4, 9);                               // (11)
    std::cout << "d.n = " << d.n << "\n";
    return 0;
}
```

Đọc hàm tạo di chuyển (1): nó nhận `Mang&& o`, một `Mang` tạm hoặc đã được cho phép lấy ruột. 

Việc làm là **lấy con trỏ** của nguồn (2), rồi **đặt con trỏ nguồn về `nullptr`** (3) để nguồn không còn giữ vùng nhớ nữa. Tham số không có `const` vì ta phải sửa nguồn ở (3).

Chữ `noexcept` là lời hứa "hàm này không ném ngoại lệ": hàm chỉ chép vài con số nên giữ được lời hứa; vì sao lời hứa quan trọng, mục 8 giải thích.

Phép gán di chuyển (4) làm giống hàm tạo, nhưng `this` đã giữ một vùng cũ nên phải xử lý thêm như phép gán sao chép ở Bài 11: kiểm tra tự gán (5), trả vùng cũ (6), rồi lấy con trỏ và đặt nguồn về `nullptr`. Nếu thiếu kiểm tra (5), `a = std::move(a)` sẽ trả vùng của chính `a` rồi "lấy" lại con trỏ vừa trả. Ở lần thử của mình, kết quả là `a` mất sạch dữ liệu (`n` = 0, `d` = `nullptr`), không báo lỗi gì.

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `Mang a(3, 1)` | Xin mảng 3 `int` | `a.d` = 0x9000 |
| 2 | (7) `Mang b = a;` | `a` là lvalue: hàm tạo sao chép, mảng mới, in `copy!` | `b.d` = 0xA000 |
| 3 | (8) `Mang c = std::move(a);` | `std::move(a)` là rvalue nên chọn hàm tạo di chuyển (1): (2) `c.d` = 0x9000, (3) `a.d` = `nullptr`, `a.n` = 0; in `move!` | `c.d` = 0x9000; `a.d` = `nullptr` |
| 4 | in | `a.n = 0, c.n = 3` | không đổi |
| 5 | (9) `nhan(b)` | `m` tạo từ lvalue `b`: sao chép, in `copy!`; in `nhan 3 phan tu`; `m` chết, trả mảng chép | `m.d` = 0xB000 rồi đã trả |
| 6 | (10) `nhan(std::move(b))` | `m` tạo từ rvalue: di chuyển, in `move!`; in `nhan 3 phan tu`; `m` chết, trả 0xA000 | `m.d` = 0xA000 rồi đã trả; `b.d` = `nullptr` |
| 7 | `Mang d(2, 0)` | Xin mảng 2 `int` | `d.d` = 0xC000 |
| 8 | (11) `d = Mang(4, 9);` | Vế phải là tạm (rvalue) nên chọn (4): (5) khác nhau, (6) trả 0xC000, lấy con trỏ của tạm, tạm về `nullptr`; in `move gan!`. Tạm chết cuối câu lệnh, `delete[]` trên `nullptr` không làm gì | `d.d` = mảng của tạm (4 `int`) |
| 9 | in | `d.n = 4` | không đổi |
| 10 | cuối `main` | `d`, `c`, `b`, `a` chết theo thứ tự ngược; `b` và `a` đã `nullptr` nên `delete[]` của chúng không làm gì (chỉ `d` và `c` trả mảng) | heap trống |

**Kết quả khi chạy:**

```text
copy!
move!
a.n = 0, c.n = 3
copy!
nhan 3 phan tu
move!
nhan 3 phan tu
move gan!
d.n = 4
```

Mình đã chạy bản này với AddressSanitizer: không báo gì, thoát mã 0. Dòng `a.n = 0` là do **lớp này tự đặt** `o.n = 0` ở (3); đó là lựa chọn của người viết lớp, không phải quy tắc chung của C++.

Có một chi tiết đáng nhắc ở bước 8: vế phải là giá trị tạm nên **không cần** viết `std::move`, C++ tự chọn phép gán di chuyển. Đó là lý do ở [Bài 09](09-unique-ptr.md), dòng `p = std::make_unique<Cay>(7);` gán được: kết quả của `make_unique` là rvalue, nên `unique_ptr` dùng phép gán di chuyển của nó.

!!! warning "Hay nhầm"
    Trong thân hàm tạo di chuyển, tham số `o` có tên nên **là lvalue** (như `r` ở mục 3), dù kiểu của nó là `Mang&&`. Vì vậy `d = o.d;` chỉ chép con trỏ, và để lấy ruột của một thành viên khác ta lại phải viết `std::move` cho nó. Với con trỏ thô thì chép con trỏ là đủ.

### 5. `std::move` không di chuyển gì cả

Bây giờ nhìn lại dòng (8) ở mục 4: `Mang c = std::move(a);`. Việc lấy con trỏ không do `std::move` làm. `std::move(a)` chỉ **ép `a` thành rvalue**, nghĩa là nói với trình biên dịch "tôi đồng ý cho lấy ruột của `a`". 

Sau đó trình biên dịch chọn hàm tạo di chuyển vì đối số bây giờ là rvalue, và **chính hàm tạo đó** mới lấy con trỏ. 

Bạn đã thấy điều này ở [Bài 09](09-unique-ptr.md): `unique_ptr` trao tay vì hàm tạo di chuyển của nó làm vậy, không phải vì `std::move`.

Hệ quả: nếu lớp không có hàm tạo di chuyển thì `std::move` không làm được gì đặc biệt. Thử với `Cu` chỉ có hàm tạo sao chép:

```cpp
#include <iostream>
#include <utility>

struct Cu {
    int v;
    Cu(int x) { v = x; }
    Cu(const Cu& o) {                             // (1)
        v = o.v;
        std::cout << "copy!\n";
    }
};

int main() {
    Cu a(5);
    Cu b = std::move(a);                          // (2)
    std::cout << "b.v = " << b.v << "\n";
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra |
|---|---|---|
| 1 | `Cu a(5)` | `a.v` = 5 |
| 2 | (2) `Cu b = std::move(a);` | `std::move(a)` là rvalue, nhưng `Cu` không có hàm tạo di chuyển; hàm (1) nhận `const Cu&` mà tham chiếu hằng gắn được cả giá trị tạm, nên (1) được chọn: in `copy!` |
| 3 | in | `b.v = 5` |

**Kết quả khi chạy:**

```text
copy!
b.v = 5
```

**Thử thay đổi: thêm `Cu(Cu&& o) { v = o.v; std::cout << "move!\n"; }` ngay trước (1).** Mình đã chạy: lần này in `move!` rồi `b.v = 5`. Cùng một dòng `std::move`, kết quả đổi theo việc lớp có hàm tạo di chuyển hay không.

### 6. Đối tượng sau khi bị move

Đối tượng bị move **vẫn còn sống**, hàm hủy của nó vẫn chạy khi hết phạm vi. Với các kiểu của thư viện chuẩn (`std::string`, `std::vector`...), chuẩn chỉ hứa đối tượng ở trạng thái **hợp lệ nhưng không xác định (valid but unspecified)**. "Hợp lệ" nghĩa là hủy nó hay gán giá trị mới cho nó đều an toàn. "Không xác định" nghĩa là bạn **không được đoán** nội dung: nhiều máy thấy chuỗi rỗng, nhưng chuẩn không hứa.

Quy tắc dùng an toàn: sau khi move, chỉ **hủy** nó hoặc **gán lại** nó. 

Ngoại lệ có bảo đảm riêng: chuẩn nói `unique_ptr` và `shared_ptr` sau khi bị move thì **rỗng** (`nullptr`), nên viết `a == nullptr` hợp lệ, đúng như [Bài 09](09-unique-ptr.md). Với lớp tự viết như `Mang`, "trạng thái sau move" do chính bạn quy định: ở trên ta chọn `n = 0` và `d = nullptr`, đó cũng là trạng thái mà hàm hủy `delete[] d` xử lý được.

!!! info "Bạn biết Go?"
    Go không có hàm hủy và không có khái niệm move. Gán một struct luôn chép từng byte (con trỏ, slice, map bên trong chỉ chép "đầu mối", nên bản sao dùng chung dữ liệu, như Bài 11 đã nói), và bộ gom rác lo việc dọn khi không còn ai trỏ tới. Vì không có "người phải trả vùng nhớ đúng một lần", Go không cần cách trao quyền: không có thứ nào tương đương `std::move`. Gán biến về `nil` ở Go chỉ là gán, không kích hoạt gì.

### 7. Rule of 5 và Rule of 0

[Bài 11](11-sao-chep-rule-of-3.md) có Rule of 3: hàm hủy, hàm tạo sao chép, phép gán sao chép. Thêm hai hàm di chuyển ta được năm hàm đặc biệt.

**Rule of 5**: nếu lớp quản lý tài nguyên bằng tay (như `Mang` giữ `int*`) thì **thường** phải tự quyết định cả năm hàm: viết, hoặc cấm bằng `= delete`, hoặc giữ mặc định bằng `= default` (nêu tên ở Bài 11).

Trình biên dịch tự sinh hàm nào còn tùy bạn đã khai báo gì: nếu bạn **tự khai báo** một hàm di chuyển, hai hàm sao chép tự sinh bị **xóa**; nếu bạn tự khai báo hàm hủy hay một hàm sao chép, các hàm di chuyển **không** được tự sinh. Mình đã thử cả hai chiều (rút gọn: bỏ hàm tạo thường, và `Cay` là kiểu có hàm tạo sao chép in `copy!` và hàm tạo di chuyển in `move!`):

```text
struct Hop { Hop(){}  Hop(Hop&&) noexcept {} };
    Hop a; Hop b = a;       // lỗi biên dịch: use of deleted function 'Hop::Hop(const Hop&)'
struct M1 { Cay c;  ~M1() {} };    // M1 b = std::move(a);  in: copy!
struct M2 { Cay c; };              // M2 y = std::move(x);  in: move!
```

Chỉ vì thêm một hàm hủy rỗng mà `M1` mất hàm di chuyển tự sinh, và `std::move` âm thầm thành sao chép.

Vì vậy có **Rule of 0**: nếu mọi thành viên của lớp **tự quản lý mình** (`std::vector`, `std::string`, `std::unique_ptr`), bạn **không viết hàm đặc biệt nào** và để trình biên dịch tự sinh; chúng chép và di chuyển từng thành viên đúng cách. Bạn nên ưu tiên cách này mỗi khi có thể.

Chương trình ở mục 💻 chạy thật để chứng minh, với lớp `Lop` chỉ gồm một `std::vector<int>` và một `std::string`, không viết hàm đặc biệt nào.

### 8. `noexcept` và `std::vector`

`std::vector` là mảng co giãn: các phần tử nằm liền nhau trong một khối heap. Khi `push_back` mà khối đã đầy, vector xin một khối **lớn hơn**, chuyển các phần tử cũ sang, rồi trả khối cũ. Chuyển bằng move thì rẻ, nhưng có một rủi ro: nếu move ném ngoại lệ khi mới chuyển được nửa số phần tử, khối cũ đã bị lấy ruột một phần và vector không thể khôi phục. (Cũng vì vậy, nếu một hàm đã hứa `noexcept` mà ngoại lệ vẫn thoát ra khỏi nó, chương trình gọi `std::terminate` và dừng hẳn; ngoại lệ là chuyện của [Bài 08](08-raii.md).)

Để an toàn, vector dùng `std::move_if_noexcept`: **chỉ move khi hàm tạo di chuyển hứa `noexcept`** (hoặc kiểu không sao chép được); nếu không thì **sao chép**, vì sao chép không phá khối cũ. Nghĩa là quên `noexcept` làm vector âm thầm chậm đi. Đếm thử với hai kiểu giống hệt nhau, chỉ khác `noexcept`:

```cpp
#include <iostream>
#include <utility>
#include <vector>

struct CayA {                                     // move có noexcept
    int cao;
    CayA(int c) { cao = c; }
    CayA(const CayA& o) { cao = o.cao; std::cout << "  copy " << cao << "\n"; }
    CayA(CayA&& o) noexcept { cao = o.cao; std::cout << "  move " << cao << "\n"; }
};

struct CayB {                                     // move KHÔNG noexcept
    int cao;
    CayB(int c) { cao = c; }
    CayB(const CayB& o) { cao = o.cao; std::cout << "  copy " << cao << "\n"; }
    CayB(CayB&& o) { cao = o.cao; std::cout << "  move " << cao << "\n"; }
};

int main() {
    std::vector<CayA> va;
    std::cout << "CayA (noexcept):\n";
    for (int i = 1; i <= 4; i++) {
        std::cout << " push_back " << i << "\n";
        va.push_back(CayA(i));
    }
    std::vector<CayB> vb;
    std::cout << "CayB (khong noexcept):\n";
    for (int i = 1; i <= 4; i++) {
        std::cout << " push_back " << i << "\n";
        vb.push_back(CayB(i));
    }
    return 0;
}
```

`push_back` thêm một phần tử vào cuối. Mỗi lần ta đưa vào một `CayX(i)` tạm (rvalue), nên phần tử mới được dựng bằng hàm tạo di chuyển; các dòng còn lại là chuyển phần tử cũ khi vector tăng khối.

| Bước | Dòng | Chuyện gì xảy ra (thứ tự là thứ tự **mình quan sát** trên g++) |
|---|---|---|
| 1 | `push_back` 1 | Vector rỗng, xin khối đầu tiên; phần tử mới dựng từ tạm: `move 1` |
| 2 | `push_back` 2 | Khối đầy, xin khối lớn hơn; phần tử mới: `move 2`; rồi chuyển phần tử cũ: `CayA` in `move 1`, `CayB` in `copy 1` |
| 3 | `push_back` 3 | Khối đầy lần nữa; `move 3`; chuyển phần tử cũ: `CayA` in `move 1`, `move 2`, `CayB` in `copy 1`, `copy 2` |
| 4 | `push_back` 4 | Khối còn chỗ, không phải chuyển ai: chỉ `move 4` |

**Kết quả khi chạy:**

```text
CayA (noexcept):
 push_back 1
  move 1
 push_back 2
  move 2
  move 1
 push_back 3
  move 3
  move 1
  move 2
 push_back 4
  move 4
CayB (khong noexcept):
 push_back 1
  move 1
 push_back 2
  move 2
  copy 1
 push_back 3
  move 3
  copy 1
  copy 2
 push_back 4
  move 4
```

Chỉ khác một chữ `noexcept`, các phần tử cũ của `CayB` bị **sao chép** mỗi khi vector tăng khối.

Con số cụ thể ở trên là của g++ trên máy mình: dung lượng tăng 1, 2, 4 và thứ tự dòng in có thể **khác** giữa các cài đặt thư viện chuẩn, nhưng quy tắc "không `noexcept` thì sao chép khi tăng khối" là ý chính. **Thử thay đổi: thêm `vb.reserve(4);` ngay sau `std::vector<CayB> vb;`** (`reserve(4)` xin sẵn chỗ cho 4 phần tử). Mình đã chạy: `CayB` chỉ còn bốn dòng `move`, không có `copy`, vì vector không còn phải tăng khối.

### 9. Trả về theo giá trị: viết `return v;`

Khi hàm trả một đối tượng theo giá trị, đừng viết `std::move`. Trình biên dịch có thể bỏ hẳn bước sao chép hoặc di chuyển: gọi là **copy elision** (bỏ qua sao chép), thường gọi là RVO (Return Value Optimization, tối ưu giá trị trả về). Từ C++17 điều này **bắt buộc** khi trả về một giá trị tạm (`return Cay(3);`): không có sao chép hay di chuyển nào, kể cả khi hai hàm đó bị xóa.

Với biến cục bộ có tên (`return c;`) thì gọi là **NRVO**, được phép nhưng **không bắt buộc**. Nếu không bỏ qua được, trả về biến cục bộ được thử như rvalue trước, tức là dùng **move** chứ không phải copy. Mình đã thử một hàm có hai biến cục bộ và trả một trong hai tùy nhánh: g++ in đúng một `move!`.

```cpp
#include <iostream>
#include <utility>

struct Cay {
    int cao;
    Cay(int c) { cao = c; std::cout << "tao " << cao << "\n"; }
    Cay(const Cay& o) { cao = o.cao; std::cout << "copy!\n"; }
    Cay(Cay&& o) noexcept { cao = o.cao; std::cout << "move!\n"; }
};

Cay taoTam() {
    return Cay(3);                                // (1)
}

Cay taoCoTen() {
    Cay c(4);
    return c;                                     // (2)
}

int main() {
    std::cout << "--- taoTam\n";
    Cay a = taoTam();                             // (3)
    std::cout << "--- taoCoTen\n";
    Cay b = taoCoTen();                           // (4)
    std::cout << "--- xong " << a.cao << " " << b.cao << "\n";
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra |
|---|---|---|
| 1 | in | `--- taoTam` |
| 2 | (3) → (1) | `Cay(3)` là giá trị tạm trả về: từ C++17 nó được dựng thẳng vào `a`. Chỉ in `tao 3`, không `copy!` hay `move!` |
| 3 | in | `--- taoCoTen` |
| 4 | (4) → (2) | `c` có tên. Trên g++ của mình, `c` được dựng thẳng vào `b` (NRVO): chỉ in `tao 4` |
| 5 | in | `--- xong 3 4` |

**Kết quả khi chạy:**

```text
--- taoTam
tao 3
--- taoCoTen
tao 4
--- xong 3 4
```

Chỉ dòng `tao 3` ở (1) là được **bảo đảm** bởi chuẩn C++17. Việc `taoCoTen` không in gì thêm là điều mình **quan sát** trên g++ này; chuẩn không bắt buộc.

Vậy nếu viết `return std::move(c);` thì sao? Mình đã chạy một bản của `taoCoTen` viết như vậy:

```cpp
// bo-qua-kiem-tra
Cay taoMove() {
    Cay c(5);
    return std::move(c);
}
```

g++ với `-Wall` cảnh báo (rút gọn, bỏ vị trí): `warning: moving a local object in a return statement prevents copy elision [-Wpessimizing-move]`, và chương trình in `tao 5` rồi `move!`.

Tức là `std::move` làm mất cơ hội dựng thẳng, bạn phải trả thêm một lần di chuyển mà không được gì. Quy tắc: **trả biến cục bộ theo giá trị thì cứ `return v;`**. (Ở [Bài 09](09-unique-ptr.md) bảng cũng ghi trả `unique_ptr` thì không cần `std::move`.)

!!! info "Để biết: perfect forwarding (chỉ nêu tên)"
    Trong một **template** (hàm viết chung cho nhiều kiểu), `T&&` với `T` được suy ra từ chính đối số là một **forwarding reference** (tham chiếu chuyển tiếp): nó nhận cả lvalue lẫn rvalue. `std::forward<T>(x)` là hàm giữ nguyên "x là lvalue hay rvalue" khi đưa tiếp `x` cho hàm khác; cách dùng cả hai gọi là **perfect forwarding**. Bài này không dạy; bạn sẽ gặp khi đọc code thư viện (như `emplace_back`). Trong bài này, `T&&` luôn chỉ là tham chiếu rvalue của mục 3.

## 💻 Ví dụ code

### Ví dụ: Rule of 0 chạy thật

Lớp `Lop` dưới đây (đã nêu ở mục 7) **không viết hàm đặc biệt nào**. Ta kiểm tra: sao chép có sâu không, di chuyển có thật là lấy ruột không.

```cpp
#include <iostream>
#include <string>
#include <utility>
#include <vector>

struct Lop {                                      // không viết hàm đặc biệt nào
    std::vector<int> d;
    std::string ten;
};

int main() {
    Lop a;
    a.d = {1, 2, 3};
    a.ten = "abc";
    const int* truoc = a.d.data();                // (1)

    Lop b = a;                                    // (2)
    b.d[0] = 9;
    std::cout << "sao chep: a.d[0] = " << a.d[0] << ", b.d[0] = " << b.d[0] << "\n";

    Lop c = std::move(a);                         // (3)
    std::cout << "di chuyen: c co " << c.d.size() << " so, ten " << c.ten << "\n";
    std::cout << "cung vung nho voi truoc? " << (c.d.data() == truoc) << "\n";
    return 0;
}
```

`a.d.data()` là địa chỉ khối heap chứa các phần tử của vector; ta lưu lại ở (1) để so sánh sau. Ta không in `a` sau khi move, vì nội dung của nó không được bảo đảm.

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `a.d = {1, 2, 3}`, `a.ten = "abc"` | `a` giữ ba số (một dấu `{}` gán ba số vào vector) và chuỗi `abc` | `a.d.data()` = 0x9000 |
| 2 | (1) | Lưu địa chỉ khối của `a.d` vào `truoc` | `truoc` = 0x9000 |
| 3 | (2) `Lop b = a;` | Hàm sao chép tự sinh chép từng thành viên: vector chép sâu sang khối mới, chuỗi cũng vậy | `b.d.data()` = 0xA000 |
| 4 | `b.d[0] = 9` + in | Chỉ đổi khối của `b`: in `sao chep: a.d[0] = 1, b.d[0] = 9` | không đổi |
| 5 | (3) `Lop c = std::move(a);` | Hàm di chuyển tự sinh di chuyển từng thành viên: vector của `c` lấy khối của `a`, chuỗi cũng được di chuyển | `c.d.data()` = 0x9000 |
| 6 | in | `c` có 3 số, tên `abc` | không đổi |
| 7 | in | `c.d.data() == truoc` đúng, in `1` | không đổi |

**Kết quả khi chạy:**

```text
sao chep: a.d[0] = 1, b.d[0] = 9
di chuyen: c co 3 so, ten abc
cung vung nho voi truoc? 1
```

Dòng cuối là bằng chứng: sau khi move, `c` giữ **đúng khối nhớ cũ** của `a`, không có khối mới nào được xin. Con số `1` là kết quả mình thấy trên máy này; chuẩn bảo đảm di chuyển một vector là thao tác hằng thời gian, nên thực tế nó chỉ chuyển con trỏ. Mình đã chạy với AddressSanitizer: không báo gì, thoát mã 0.

Còn một thành viên khác loại thì sao? Nếu `Lop` có thành viên `std::unique_ptr<int> p`, thì hàm sao chép tự sinh bị xóa theo (vì `unique_ptr` không copy được), nhưng di chuyển vẫn hoạt động. Mình đã biên dịch `Lop b = a;` cho bản đó, g++ báo (rút gọn):

```text
error: use of deleted function 'Lop::Lop(const Lop&)'
note: 'Lop::Lop(const Lop&)' is implicitly deleted because the default definition would be ill-formed
```

Lớp tự động **không sao chép được** nhưng **di chuyển được**, đúng ý nghĩa sở hữu duy nhất, mà bạn không viết dòng nào.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "lvalue và rvalue khác nhau thế nào?"
    lvalue có tên và có chỗ ổn định trong bộ nhớ, dùng lại được ở các dòng sau (như một biến). rvalue là giá trị tạm sắp biến mất sau câu lệnh (như `x + 1`, `Cay(3)`, giá trị hàm trả về theo giá trị). Phân biệt này cho phép C++ "lấy ruột" an toàn: chỉ lấy ruột của rvalue, vì không ai còn dùng nó. Tham chiếu rvalue `T&&` là loại tham chiếu chỉ gắn với rvalue.

??? question "`std::move` làm gì?"
    Nó **không di chuyển gì cả**: chỉ ép đối số thành rvalue (kiểu `T&&`), tức là nói "tôi cho phép lấy ruột". Việc di chuyển thật do hàm tạo di chuyển hoặc phép gán di chuyển được chọn sau đó làm. Nếu kiểu không có hàm di chuyển, `std::move` kết thúc bằng sao chép.

??? question "Viết hàm tạo di chuyển cho lớp giữ con trỏ thô."
    Lấy con trỏ của nguồn, đặt con trỏ (và kích thước) của nguồn về rỗng (`nullptr`), và đánh dấu `noexcept`: `Mang(Mang&& o) noexcept { n = o.n; d = o.d; o.n = 0; o.d = nullptr; }`. Đặt nguồn về `nullptr` để hai đối tượng không cùng `delete` một vùng. Phép gán di chuyển thêm hai việc: kiểm tra tự gán và trả vùng cũ trước khi lấy.

??? question "Vì sao hàm tạo di chuyển nên `noexcept`?"
    Khi `std::vector` hết chỗ và phải chuyển phần tử sang khối lớn hơn, nó dùng `std::move_if_noexcept`: chỉ move nếu hàm tạo di chuyển hứa không ném ngoại lệ, nếu không (và kiểu sao chép được) thì sao chép để khối cũ còn nguyên nếu lỡ có ngoại lệ. Thiếu `noexcept` nghĩa là vector chậm đi âm thầm; mình đã đếm bằng bộ đếm in `copy`/`move`. Cách xử lý cụ thể có thể khác giữa các cài đặt, nhưng ý chính là vậy.

??? question "Rule of 3, Rule of 5, Rule of 0?"
    Rule of 3: cần tự viết một trong {hàm hủy, hàm tạo sao chép, phép gán sao chép} thì thường cần cả ba. Rule of 5 thêm hàm tạo di chuyển và phép gán di chuyển: lớp quản lý tài nguyên bằng tay thì thường phải quyết định cả năm (viết, `= delete` hoặc `= default`). Rule of 0: dùng thành viên tự quản lý (`std::vector`, `std::unique_ptr`, `std::string`) và không viết hàm nào trong năm hàm đó; đây là cách nên ưu tiên.

??? question "`return std::move(x);` có sai không?"
    Với biến cục bộ trả theo giá trị thì có, nó là thói quen xấu: nó **ngăn** copy elision/NRVO (g++ có cảnh báo `-Wpessimizing-move`) và buộc thêm một lần di chuyển. Cứ viết `return x;`: trình biên dịch có thể bỏ qua bước sao chép hoặc di chuyển, và nếu không thì cũng dùng move. C++17 còn bảo đảm bỏ qua hoàn toàn khi trả về giá trị tạm như `return Cay(3);`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Dùng đối tượng sau khi move rồi đoán nội dung của nó"
    Đối tượng bị move chỉ ở trạng thái "hợp lệ nhưng không xác định": chỉ hủy nó hoặc gán lại. Đừng viết code dựa trên việc "chắc nó rỗng". Ngoại lệ chuẩn bảo đảm là `unique_ptr`/`shared_ptr`, rỗng sau khi move.

!!! warning "Lỗi 2: Viết `return std::move(bienCucBo);`"
    Nó cản copy elision (mục 9). Hãy viết `return bienCucBo;`.

!!! warning "Lỗi 3: Hàm tạo di chuyển quên đặt nguồn về `nullptr`"
    Khi đó nguồn và đích cùng giữ một con trỏ, và cả hai hàm hủy cùng `delete[]` một vùng: giải phóng hai lần, hành vi không xác định ([Bài 07](07-new-delete.md)). Mình không chạy đoạn dưới và không ghi kết quả.

    ```cpp
    // bo-qua-kiem-tra
    Mang(Mang&& o) noexcept {
        n = o.n;
        d = o.d;
        // thiếu: o.d = nullptr;  -> hai hàm hủy cùng delete[] một vùng
    }
    ```

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="12" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn code sau. `Mang` có hàm tạo sao chép in `copy!` và hàm tạo di chuyển in `move!`. Ba dòng in ra theo thứ tự nào?

```text
Mang a(3);
Mang b = a;
Mang c = std::move(a);
Mang d = std::move(b);
```

- `copy!`, `copy!`, `copy!`: `std::move` chỉ đổi tên
- `copy!`, `move!`, `move!`: `a` là lvalue, hai dòng sau là rvalue
- `move!`, `move!`, `move!`: mọi khởi tạo từ biến cùng loại đều di chuyển
- `copy!`, `move!`, `copy!`: `b` đã được sao chép từ `a` nên dòng cuối chép tiếp

<p class="giai-thich" markdown>Dòng `Mang b = a;` có `a` là lvalue (có tên, không có `std::move`) nên chọn hàm tạo sao chép. Hai dòng sau có `std::move`, ép thành rvalue, nên chọn hàm tạo di chuyển (mình đã chạy ra `copy! move! move!`). `std::move` không "chỉ đổi tên": nó quyết định hàm nào được chọn. Việc `b` từng là bản sao không ngăn nó bị lấy ruột tiếp, và dòng đầu không thể là `move!` vì `a` không được ép thành rvalue.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn code sau (đã `#include <memory>` và `<utility>`). Dòng cuối in ra gì?

```text
std::unique_ptr<int> a = std::make_unique<int>(7);
std::unique_ptr<int> b = std::move(a);
std::cout << (a == nullptr) << " " << *b;
```

- `0 7`: `a` vẫn giữ số 7 vì `std::move` không xóa gì
- `1 0`: `b` được tạo mới nên bắt đầu từ 0
- `0 0`: cả hai đều bị `std::move` làm rỗng đi
- `1 7`: `a` rỗng sau khi trao, `b` giữ số 7

<p class="giai-thich" markdown>Chuẩn bảo đảm `unique_ptr` bị move thì thành rỗng, nên `a == nullptr` đúng và in `1`; `b` nhận số 7 (mình đã chạy ra `1 7`). Lập luận "`std::move` không xóa gì" đúng về bản thân `std::move`, nhưng hàm tạo di chuyển của `unique_ptr` mới là chỗ đặt nguồn về `nullptr`. `b` nhận giá trị của `a` chứ không bắt đầu từ 0, và `b` không thể rỗng vì nó là bên nhận.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Đọc khai báo sau của kiểu `T`, rồi nghĩ về `std::vector<T>` khi `push_back` làm nó hết chỗ. Chuyện gì **thường** xảy ra với các phần tử cũ?

```text
struct T {
    T(const T&);
    T(T&&);
};
```

- Chúng được di chuyển, vì chỉ cần có hàm di chuyển là đủ
- Chương trình không biên dịch được, vì thiếu `noexcept`
- Chúng được sao chép, vì hàm di chuyển không `noexcept`
- Chúng bị bỏ lại ở khối cũ và vector giữ cả hai khối

<p class="giai-thich" markdown>Vector dùng `std::move_if_noexcept`: hàm di chuyển không hứa `noexcept` và kiểu còn sao chép được thì nó sao chép các phần tử cũ, để khối cũ còn nguyên nếu có ngoại lệ (mình đã đếm bằng `CayB` ra các dòng `copy`; chi tiết có thể khác giữa các cài đặt). Có hàm di chuyển là chưa đủ để vector chọn nó. `noexcept` không bắt buộc về cú pháp nên vẫn biên dịch được. Vector luôn giữ đúng một khối, khối cũ được trả sau khi chuyển.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Đọc đoạn code sau. `Cay` in `tao 3` khi tạo, `copy!` khi sao chép và `move!` khi di chuyển. Biên dịch bằng C++17, chương trình in ra gì?

```text
Cay taoTam() { return Cay(3); }
Cay a = taoTam();
```

- Chỉ `tao 3`: giá trị tạm được dựng thẳng vào chính `a`
- `tao 3` rồi `move!`: giá trị tạm được chuyển vào `a`
- `tao 3` rồi `copy!`: giá trị tạm được sao chép vào `a`
- `tao 3` rồi hai `move!`: một ở lệnh `return`, một ở lệnh gán

<p class="giai-thich" markdown>Từ C++17, trả về một giá trị tạm (`return Cay(3);`) được bảo đảm dựng thẳng vào nơi nhận, nên chỉ có `tao 3` (mình đã chạy). Không có bước chuyển nào, nên cả `move!` lẫn `copy!` đều không in. Kiểu nghĩ "một lần ở `return`, một lần ở lệnh gán" là cách mô tả thời trước C++17, khi tối ưu này còn tùy trình biên dịch. Còn `=` ở dòng khai báo `Cay a = ...` là khởi tạo chứ không phải phép gán.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn code sau. `Cu` chỉ có một hàm tạo sao chép (in `copy!`), không có hàm tạo di chuyển. Dòng cuối làm gì?

```text
Cu a(5);
Cu b = std::move(a);
```

- In `move!`, vì `std::move` luôn gọi hàm move
- Lỗi biên dịch, vì `Cu` không có hàm tạo di chuyển
- Không in gì, vì `std::move` chỉ là phép ép kiểu mà thôi
- In `copy!`, vì không có hàm di chuyển nào để chọn cả

<p class="giai-thich" markdown>`std::move(a)` chỉ ép `a` thành rvalue. `Cu` không có hàm tạo di chuyển nên hàm duy nhất khớp là hàm tạo sao chép, vì `const Cu&` gắn được cả rvalue; kết quả là `copy!` (mình đã chạy). Nói `std::move` "luôn gọi hàm di chuyển" là hiểu sai: nó chỉ cho phép, hàm có tồn tại hay không là chuyện khác. Cũng không có lỗi biên dịch, và "không in gì" sai vì vẫn phải tạo `b`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Đọc đoạn code sau. Có hai hàm `f`: `f(int&)` in `L`, `f(int&&)` in `R`. Nó in ra gì?

```text
int x = 1;
f(x);  f(x + 1);  f(std::move(x));  f(3);
```

- `L L R R`: `x + 1` gọi lại được như một biến
- `R R R R`: mọi đối số truyền vào hàm đều là rvalue
- `L R R R`: chỉ `x` là lvalue, ba cái kia là rvalue
- `L R L R`: ngay sau `std::move`, `x` trở lại là lvalue

<p class="giai-thich" markdown>`x` có tên nên là lvalue (in `L`). `x + 1` là kết quả tạm, `std::move(x)` đã ép thành rvalue, và `3` là số viết thẳng, nên cả ba in `R` (mình đã chạy một bản tương tự ra `lvalue rvalue rvalue rvalue`). `x + 1` không gọi lại được như biến vì hết câu lệnh là mất. Đối số không mặc nhiên là rvalue: `x` truyền thẳng vẫn là lvalue. Còn `std::move` không có tác dụng kéo dài sang lần gọi sau.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Hàm trả một biến cục bộ `v` theo giá trị. Cách viết lệnh `return` nào là tốt nhất?

- `return v;` để trình biên dịch tự chọn bỏ qua hay move
- `return std::move(v);` để chắc chắn chọn hàm di chuyển
- `return v;` nhưng phải tự viết hàm tạo sao chép trước
- `return std::move(v);` vì nó luôn bỏ qua được bước sao chép

<p class="giai-thich" markdown>`return v;` cho trình biên dịch cơ hội bỏ qua hẳn bước sao chép hoặc di chuyển (NRVO, được phép chứ không bắt buộc), và nếu không bỏ qua được thì cũng dùng di chuyển. `return std::move(v);` ngược lại ngăn tối ưu đó (g++ cảnh báo `-Wpessimizing-move`) và buộc thêm một lần di chuyển, nên "chắc chắn chọn di chuyển" là lợi ích giả. Không cần viết hàm sao chép riêng để `return v;` chạy. Còn nói `std::move` "luôn bỏ qua được sao chép" sai vì nó không bỏ qua gì: nó chỉ ép kiểu.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **lvalue** có tên và dùng lại được ở dòng sau (`x`); **rvalue** là giá trị tạm sắp biến mất (`x + 1`, `Cay(3)`, kết quả hàm); tham chiếu `T&&` chỉ gắn với rvalue, nhưng bên trong hàm thì tham số `&&` có tên nên là lvalue.
2. **Di chuyển** = lấy con trỏ của nguồn rồi đặt con trỏ nguồn về `nullptr` (kèm `noexcept`); phép gán di chuyển còn phải chống tự gán và trả vùng cũ. `std::move(x)` **không di chuyển gì**: nó chỉ ép `x` thành rvalue, hàm tạo/gán di chuyển được chọn mới làm việc; không có hàm đó thì kết thúc bằng sao chép.
3. Sau khi move, chỉ **hủy** hoặc **gán lại** đối tượng (trạng thái "hợp lệ nhưng không xác định" với kiểu chuẩn; riêng `unique_ptr`/`shared_ptr` được bảo đảm rỗng).
4. **Rule of 5**: lớp quản lý tài nguyên bằng tay thì quyết định cả năm hàm đặc biệt; **Rule of 0**: dùng thành viên tự quản lý (`vector`, `unique_ptr`, `string`) và không viết hàm nào. Thiếu `noexcept` trên hàm tạo di chuyển thì `std::vector` sao chép khi tăng khối.
5. Trả theo giá trị thì viết `return v;`, không viết `return std::move(v);` (có thể cản copy elision); C++17 bảo đảm bỏ qua với giá trị tạm, còn NRVO không bắt buộc. Perfect forwarding chỉ cần biết tên.
