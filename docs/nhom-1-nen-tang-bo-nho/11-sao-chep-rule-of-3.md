# Bài 11 — Sao chép đúng cách và Rule of 3

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao sao chép mặc định của struct giữ con trỏ thô là sao chép **nông** (hai đối tượng cùng giữ một vùng nhớ), và vì sao với hàm hủy `delete` thì dẫn tới giải phóng hai lần.
    - Tự viết hàm tạo sao chép và phép gán sao chép theo kiểu sao chép **sâu** (mỗi đối tượng có vùng nhớ riêng), kể cả chống tự gán `a = a`.
    - Nêu và áp dụng Rule of 3, biết `= delete` để cấm sao chép (cách `unique_ptr` làm), và hiểu vì sao truyền `const T&` rẻ hơn truyền theo giá trị.

**Bạn cần biết trước:** [Bài 06](06-tham-chieu-const.md) (hàm tạo sao chép, `const&`), [Bài 07](07-new-delete.md) (`new`/`delete`, giải phóng hai lần) và [Bài 08](08-raii.md) (lớp `Hop` giữ con trỏ thô).

## 🧠 Câu chuyện mở đầu

Bạn có một quyển vở dày ở phòng 12, và bạn cần một bản sao. Cách 1: photo **cái bìa**, trên bìa chỉ ghi "vở nằm ở phòng 12". Bạn có hai tờ bìa, nhưng vẫn chỉ có **một quyển vở**: ai ghi vào quyển vở thì cả hai tờ bìa đều "thấy". Cách 2: photo **cả quyển**. Bạn có hai quyển riêng, ghi vào quyển này không ảnh hưởng quyển kia.

Cách 1 là **sao chép nông (shallow copy)**, cách 2 là **sao chép sâu (deep copy)**. Một struct giữ con trỏ thô giống tờ bìa: bên trong chỉ có "số phòng" (địa chỉ). C++ mặc định photo cái bìa. Bài này dạy bạn bảo C++ photo cả quyển.

!!! info "Chỗ nào ví dụ photo vở không còn đúng?"
    Tờ bìa thật không biết ai đang giữ quyển vở. Trong C++ thì có người phải **trả phòng**: hàm hủy gọi `delete`. Hai tờ bìa cùng ghi phòng 12 nghĩa là hai người cùng đi trả một phòng, và đó là lỗi ở mục 1.

## 📖 Giải thích

### 1. Sao chép mặc định chỉ chép cái bìa

Từ [Bài 06](06-tham-chieu-const.md): hàm tạo sao chép chạy mỗi khi một bản sao được tạo. Nếu bạn không tự viết, trình biên dịch tự sinh một hàm **chép từng thành viên** (mỗi trường của struct, như `p`). Với `int` thì chép số; với con trỏ thì chép **giá trị con trỏ**, tức là chép địa chỉ, không chép chỗ được trỏ tới.

Thử với `Hop` (hộp) giữ một con trỏ `p` tới `int` ở heap. Lần này chưa có hàm hủy, nên chương trình chưa gặp lỗi gì nghiêm trọng:

```cpp
#include <iostream>

struct Hop {
    int* p;
    Hop(int v) {
        p = new int(v);
    }
};

void thu() {
    Hop a(5);
    Hop b = a;                                    // (1)
    std::cout << "cung dia chi? " << (a.p == b.p) << "\n";
    *b.p = 9;                                     // (2)
    std::cout << "a: " << *a.p << ", b: " << *b.p << "\n";
}

int main() {
    thu();
    return 0;
}
```

Biểu thức `a.p == b.p` so sánh hai địa chỉ và cho `1` (đúng) hoặc `0` (sai) khi in; ta phải đặt trong ngoặc vì `<<` ưu tiên hơn `==`. Mình so sánh thay vì in địa chỉ thô để kết quả không đổi giữa các lần chạy.

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `Hop a(5)` | Xin heap một `int` bằng 5 | `a.p` = 0x9000; heap 0x9000: 5 |
| 2 | (1) `Hop b = a;` | Hàm tạo sao chép tự sinh: chép từng thành viên, tức chép **địa chỉ** | `b.p` = 0x9000 (cùng số phòng) |
| 3 | in | `a.p == b.p` đúng nên in `1` | không đổi |
| 4 | (2) `*b.p = 9;` | Ghi 9 vào chỗ mà `b.p` trỏ tới, cũng là chỗ của `a.p` | heap 0x9000: 9 |
| 5 | in | `*a.p` và `*b.p` cùng đọc 0x9000 | không đổi |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`):

```text
cung dia chi? 1
a: 9, b: 9
```

Dòng `a: 9` là bằng chứng: bạn chỉ sửa `b`, nhưng `a` cũng đổi, vì hai tờ bìa chỉ chung một quyển vở. Chương trình này cũng **bị rò rỉ** một khối 4 byte, vì `Hop` chưa có hàm hủy nên không ai `delete`. Mình đã chạy với AddressSanitizer: nó báo `Direct leak of 4 byte(s) in 1 object(s)` (rút gọn, bỏ địa chỉ và đường dẫn) và thoát mã 1. Chú ý "1 object": suốt chương trình chỉ **có một** khối heap, dù có hai `Hop`.

Hình dung sau dòng (1) (địa chỉ minh họa):

```text
a.p ---+
       +--> [ 5 ]   (một khối heap duy nhất, 0x9000)
b.p ---+
```

**Thử thay đổi: thay dòng (1) bằng `Hop b(9); b = a;`** (tạo `b` riêng rồi gán `a` vào). Mình đã chạy: vẫn in `1` và `a: 9, b: 9`, nhưng ASan báo `8 byte(s) leaked in 2 allocation(s)`. Phép gán mặc định cũng chỉ chép cái bìa, nên khối 9 ban đầu của `b` bị mất địa chỉ và không ai trả được nữa.

Giờ thêm hàm hủy giống [Bài 08](08-raii.md), để mỗi `Hop` tự trả vùng của mình:

```cpp
// bo-qua-kiem-tra
struct Hop {
    int* p;
    Hop(int v) { p = new int(v); }
    ~Hop() { delete p; }
};

int main() {
    Hop a(5);
    Hop b = a;      // b.p cùng địa chỉ với a.p
    return 0;       // b chết: delete p; a chết: delete p lần nữa
}
```

Cuối `main`, hai hàm hủy cùng `delete` **một** địa chỉ: đó là giải phóng hai lần của [Bài 07](07-new-delete.md), hành vi không xác định. Mình để code trong khối bỏ qua và không ghi kết quả ([Bài 08](08-raii.md) đã hứa bài này sẽ dạy cách sửa). Gốc rễ là có **hai chủ** cho một vùng nhớ chỉ nên có một chủ.

!!! info "Bạn biết Go?"
    Gán struct trong Go cũng chép từng trường. Nếu trường là con trỏ, slice hay map thì bản sao vẫn trỏ **chung** dữ liệu: nó cũng là sao chép nông, và sửa qua bản này thì bản kia thấy. Khác biệt là bộ gom rác (GC): dùng chung không gây giải phóng hai lần, vì GC chỉ dọn khi không còn ai trỏ tới. C++ không có GC, nên "hai chủ" nghĩa là hai lần trả.

### 2. Hai thứ cần biết trước khi viết: `this` và `operator=`

**`this`** là con trỏ tới **chính đối tượng đang chạy hàm**. Khi bạn gọi `b.ham()`, trong thân `ham` thì `this` bằng địa chỉ của `b`, và `*this` là chính `b`. Ta cần nó để hỏi "đối tượng kia có phải chính tôi không?".

**`operator=`** là tên một hàm đặc biệt, hiểu đơn giản là "**cách dấu `=` hoạt động cho kiểu này**". Khi bạn viết `b = a;` (với `b` đã tồn tại), C++ gọi hàm `operator=` của `b`, truyền `a` vào. Nếu bạn không viết, trình biên dịch tự sinh một bản chép từng thành viên, tức là bản nông ở trên. Bài này chỉ dùng `operator=` cho đúng việc đó, không học thêm gì về "nạp chồng toán tử".

### 3. Hàm tạo sao chép sâu

Cách sửa: tự viết hàm tạo sao chép để nó **xin vùng nhớ mới** và **chép giá trị** từ vùng cũ sang. Chữ `const Hop&` nhắc lại [Bài 06](06-tham-chieu-const.md): nhận đối tượng gốc bằng tham chiếu hằng, không sao chép tiếp và không sửa gốc. Nếu viết `Hop(Hop o)` (theo giá trị) thì để tạo tham số `o` lại cần chính hàm tạo sao chép này, nên C++ không cho phép.

```cpp
#include <iostream>

struct Hop {
    int* p;
    Hop(int v) {
        p = new int(v);
    }
    Hop(const Hop& o) {                           // (1)
        p = new int(*o.p);                        // (2)
        std::cout << "sao chep sau\n";
    }
    ~Hop() {
        std::cout << "huy " << *p << "\n";
        delete p;                                 // (3)
    }
};

int main() {
    Hop a(5);
    Hop b = a;                                    // (4)
    std::cout << "cung dia chi? " << (a.p == b.p) << "\n";
    *b.p = 9;                                     // (5)
    std::cout << "a: " << *a.p << ", b: " << *b.p << "\n";
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `Hop a(5)` | Xin heap một `int` bằng 5 | `a.p` = 0x9000; heap 0x9000: 5 |
| 2 | (4) `Hop b = a;` | `b` chưa tồn tại nên C++ gọi hàm tạo sao chép (1) với `o` là `a` | không đổi |
| 3 | (2) | `new int(*o.p)`: đọc giá trị 5 qua `o.p`, xin một chỗ **mới** chứa 5 | `b.p` = 0xA000; heap 0xA000: 5 |
| 4 | trong (1) | In `sao chep sau` | không đổi |
| 5 | in | `a.p == b.p`: 0x9000 và 0xA000 khác nhau, in `0` | không đổi |
| 6 | (5) `*b.p = 9;` | Chỉ ghi vào vùng của `b` | heap 0x9000: 5; 0xA000: 9 |
| 7 | in | `a: 5, b: 9` | không đổi |
| 8 | cuối `main` | `b` chết trước (ra đời sau): in `huy 9`, (3) `delete` 0xA000; rồi `a` chết: in `huy 5`, `delete` 0x9000 | heap trống |

**Kết quả khi chạy:**

```text
sao chep sau
cung dia chi? 0
a: 5, b: 9
huy 9
huy 5
```

Hình dung sau dòng (4) (địa chỉ minh họa):

```text
a.p ---> [ 5 ]   (0x9000)
b.p ---> [ 5 ]   (0xA000, khối riêng)
```

Bây giờ `a` và `b` mỗi cái có quyển vở riêng; có hai chữ `huy` cho hai đối tượng, mỗi khối heap được `delete` đúng một lần. Mình đã chạy bản này với AddressSanitizer: không có báo cáo và thoát mã 0 (nhắc lại: im lặng không chứng minh là sạch, nhưng khớp với việc đếm được hai `huy` cho hai lần xin).

!!! warning "Hay nhầm"
    `Hop b = a;` **không phải phép gán**, dù có dấu `=`. Đó là *tạo* `b` mới từ `a`, nên gọi hàm tạo sao chép; viết `Hop b(a);` cũng y như vậy (mình đã chạy: cùng output). Phép gán chỉ xảy ra khi `b` **đã tồn tại**, như mục sau.

**Thử thay đổi: thêm `Hop c = b;` ngay sau dòng (4).** Mình đã chạy: có hai dòng `sao chep sau` và ba dòng `huy` (`huy 5`, `huy 9`, `huy 5`): ba đối tượng, mỗi cái một vùng, mỗi vùng bị `delete` một lần.

### 4. Phép gán sao chép

Khi viết `b = a;` mà `b` **đã tồn tại**, `b` đang giữ một vùng nhớ cũ. Hàm tạo sao chép chạy trên đối tượng vừa mới tạo, chưa giữ vùng nào; phép gán thì phải xử lý thêm ba việc:

1. **Trả vùng cũ của `b`** (nếu không thì rò rỉ, như thử thay đổi ở mục 1).
2. **Chống tự gán**: `a = a;` là hợp lệ. Nếu cứ máy móc "trả vùng cũ rồi chép từ `a`", thì ở `a = a` ta trả mất chính vùng cần chép, rồi đọc vùng đã trả: hành vi không xác định. Nên kiểm tra `if (this != &o)` ("đối tượng kia không phải chính tôi"; `o` là biệt danh nên `&o` là địa chỉ của đối tượng thật).
3. **Trả về `*this`** (chính `b`), để viết được `x = y = z`. Kiểu trả về là `Hop&` (tham chiếu), nên không tạo thêm bản sao.

Đây là một cách viết, dễ hiểu nhất. Nếu xin vùng mới **trước** rồi mới trả vùng cũ thì không cần kiểm tra tự gán, và nếu `new` ném ngoại lệ thì `b` vẫn còn nguyên (với cách "trả trước" ở đây, `new` hỏng sau `delete p` sẽ để `p` treo). Copy-and-swap (chỉ nêu tên ở mục sau) là cách chuẩn hóa ý đó.

```cpp
#include <iostream>

struct Hop {
    int* p;
    Hop(int v) {
        p = new int(v);
    }
    Hop(const Hop& o) {
        p = new int(*o.p);
    }
    Hop& operator=(const Hop& o) {                // (1)
        if (this != &o) {                         // (2)
            delete p;                             // (3)
            p = new int(*o.p);                    // (4)
        }
        return *this;                             // (5)
    }
    ~Hop() {
        std::cout << "huy " << *p << "\n";
        delete p;
    }
};

int main() {
    Hop a(5);
    Hop b(7);
    b = a;                                        // (6)
    std::cout << "cung dia chi? " << (a.p == b.p) << ", b = " << *b.p << "\n";
    a = a;                                        // (7)
    std::cout << "sau a = a: " << *a.p << "\n";
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `Hop a(5)`, `Hop b(7)` | Hai đối tượng, hai vùng riêng | `a.p` = 0x9000 (5); `b.p` = 0xA000 (7) |
| 2 | (6) `b = a;` | `b` đã tồn tại nên gọi `operator=` (1) của `b`, với `o` là `a` | không đổi |
| 3 | (2) | `this` là địa chỉ `b`, `&o` là địa chỉ `a`: khác nhau, vào `if` | không đổi |
| 4 | (3) | Trả vùng cũ 0xA000 | heap 0xA000 đã trả |
| 5 | (4) | Xin vùng mới chứa bản chép của 5 | `b.p` = 0xB000 (5) |
| 6 | (5) | Trả về `*this` | không đổi |
| 7 | in | 0x9000 khác 0xB000: in `cung dia chi? 0, b = 5` | không đổi |
| 8 | (7) `a = a;` | (2): `this` và `&o` **cùng** là địa chỉ `a`, điều kiện sai, bỏ qua cả `if`; (5) vẫn trả `*this` | `a` không đổi |
| 9 | in | `sau a = a: 5` | không đổi |
| 10 | cuối `main` | `b` chết: `huy 5`; `a` chết: `huy 5` | heap trống |

**Kết quả khi chạy:**

```text
cung dia chi? 0, b = 5
sau a = a: 5
huy 5
huy 5
```

Cả hai `huy` đều là `5` vì sau `b = a;` hai hộp có cùng giá trị (nhưng hai vùng riêng). Mình đã chạy bản này với AddressSanitizer: không báo gì, thoát mã 0.

Có một cách làm khác an toàn hơn, tên là **copy-and-swap** ("chép vào một bản tạm, rồi hoán đổi ruột bản tạm với đối tượng đích"). Bài này chỉ nêu tên để bạn nhận ra khi đọc code người khác, không đi sâu.

### 5. Rule of 3

Nhìn lại ba hàm ta vừa viết cho `Hop`: **hàm hủy** (`delete p`), **hàm tạo sao chép** và **phép gán sao chép**. Chúng đi cùng nhau vì cùng một lý do: `Hop` giữ một tài nguyên (vùng heap) mà trình biên dịch không hiểu quyền sở hữu của nó.

**Rule of 3** (quy tắc ba): nếu lớp của bạn cần tự viết **một** trong ba hàm {hàm hủy, hàm tạo sao chép, phép gán sao chép} thì **thường** cần viết cả ba. Tự viết hàm hủy nghĩa là có tài nguyên phải trả; khi đó hai hàm sao chép mặc định (chép nông) thường sai. Đây là quy tắc kinh nghiệm, không phải luật của ngôn ngữ: trình biên dịch không bắt lỗi nếu bạn chỉ viết một hàm.

Quy tắc này còn hai bản mở rộng, Rule of 5 và Rule of 0, thêm "di chuyển" vào; chúng là nội dung của [Bài 12](12-move-semantics.md).

### 6. Cấm sao chép bằng `= delete`

Đôi khi sao chép **không có nghĩa** (ví dụ một file đang mở, một khóa). Khi đó ta bảo trình biên dịch xóa hàm sao chép bằng `= delete`:

```cpp
// bo-qua-kiem-tra
struct Hop {
    int* p;
    Hop(int v) { p = new int(v); }
    Hop(const Hop&) = delete;
    ~Hop() { delete p; }
};

int main() {
    Hop a(5);
    Hop b = a;
    return 0;
}
```

Mình đã biên dịch khối này bằng `g++ -std=c++17 -Wall`; đây là lỗi **biên dịch** thật (rút gọn: bỏ tên file và số dòng):

```text
error: use of deleted function 'Hop::Hop(const Hop&)'
    Hop b = a;
note: declared here
    Hop(const Hop&) = delete;
```

Ở `Hop(const Hop&) = delete;` tham số không có tên vì hàm bị xóa nên không dùng tới nó. Lỗi nằm ngay lúc biên dịch, trước khi chạy, và chỉ đúng dòng sao chép: rẻ hơn nhiều so với lỗi hai lần `delete` chỉ lộ ra khi chạy. Viết `Hop& operator=(const Hop&) = delete;` thì chặn thêm `b = a;` (mình đã thử, g++ báo `use of deleted function 'Hop& Hop::operator=(const Hop&)'`).

Đây chính là cách `std::unique_ptr` ở [Bài 09](09-unique-ptr.md) không copy được: hàm sao chép của nó bị `= delete`. Còn `= default` là chiều ngược lại: bảo trình biên dịch tự sinh hàm mặc định (bản chép từng thành viên); ở đây chỉ nêu tên.

### 7. Chi phí sao chép

Sao chép sâu **tốn thật**: mỗi lần là một lần xin vùng mới và chép toàn bộ nội dung. Với một `int` thì không đáng kể, nhưng một mảng một triệu phần tử (kiểu `int`) nghĩa là xin và chép khoảng bốn triệu byte mỗi lần sao chép. Vì thế ở [Bài 06](06-tham-chieu-const.md) ta truyền `const T&`: không sao chép gì cả. Kiểm bằng `Hop` có hàm tạo sao chép in `copy!`:

```cpp
#include <iostream>

struct Hop {
    int* p;
    Hop(int v) { p = new int(v); }
    Hop(const Hop& o) {
        p = new int(*o.p);
        std::cout << "copy!\n";
    }
    ~Hop() { delete p; }
};

void theoGiaTri(Hop h) {                          // (1)
    std::cout << "theoGiaTri: " << *h.p << "\n";
}

void theoThamChieu(const Hop& h) {                // (2)
    std::cout << "theoThamChieu: " << *h.p << "\n";
}

int main() {
    Hop a(5);
    theoGiaTri(a);
    theoThamChieu(a);
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (địa chỉ minh họa) |
|---|---|---|---|
| 1 | `Hop a(5)` | Xin heap một `int` bằng 5 | `a.p` = 0x9000 |
| 2 | `theoGiaTri(a)` | Tham số `h` là biến mới, tạo bằng hàm tạo sao chép từ `a`: xin vùng mới, chép 5, in `copy!` | `h.p` = 0xA000 |
| 3 | trong (1) | In `theoGiaTri: 5`; hết hàm thì `h` chết, trả 0xA000 | heap: chỉ còn 0x9000 |
| 4 | `theoThamChieu(a)` | `h` là biệt danh của `a`: không tạo gì, không in `copy!` | không đổi |
| 5 | trong (2) | In `theoThamChieu: 5` | không đổi |

**Kết quả khi chạy:**

```text
copy!
theoGiaTri: 5
theoThamChieu: 5
```

Ở (1), tham số `h` là một biến mới nên C++ tạo nó bằng **hàm tạo sao chép** từ `a`: có `copy!`, và cả một lần xin và chép. Ở (2), `h` chỉ là biệt danh của `a`: không có `copy!`. **Thử thay đổi: bỏ `const` và `&` ở (2)** (thành `Hop h`). Mình đã chạy: có **hai** dòng `copy!`.

## 💻 Ví dụ code

### Ví dụ: Rule of 3 cho một mảng nhỏ

Bản này làm đủ ba hàm cho `Day` (dãy), giữ `n` số `int` ở heap bằng `new int[n]` (nhớ: trả bằng `delete[]`, [Bài 07](07-new-delete.md)). Mỗi hàm in một dòng để bạn thấy khi nào nó chạy.

```cpp
#include <iostream>

struct Day {
    int n;
    int* d;
    Day(int so, int v) {
        n = so;
        d = new int[n];
        for (int i = 0; i < n; i++) d[i] = v;
    }
    Day(const Day& o) {                           // (1)
        n = o.n;
        d = new int[n];
        for (int i = 0; i < n; i++) d[i] = o.d[i];
        std::cout << "sao chep\n";
    }
    Day& operator=(const Day& o) {                // (2)
        if (this != &o) {
            delete[] d;
            n = o.n;
            d = new int[n];
            for (int i = 0; i < n; i++) d[i] = o.d[i];
        }
        std::cout << "gan\n";
        return *this;
    }
    ~Day() {                                      // (3)
        std::cout << "huy day " << n << " phan tu\n";
        delete[] d;
    }
};

void in(const Day& x) {
    for (int i = 0; i < x.n; i++) std::cout << x.d[i] << " ";
    std::cout << "\n";
}

int main() {
    Day a(3, 1);
    Day b = a;                                    // (4)
    b.d[0] = 7;
    Day c(2, 0);
    c = b;                                        // (5)
    in(a);
    in(b);
    in(c);
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|---|
| 1 | `Day a(3, 1)` | Mảng 3 phần tử `1 1 1` | `a`: `1 1 1` |
| 2 | (4) | `b` chưa tồn tại: hàm tạo sao chép (1) xin mảng mới, chép, in `sao chep` | `b`: `1 1 1` (khối riêng) |
| 3 | `b.d[0] = 7` | Chỉ đổi mảng của `b` | `a`: `1 1 1`; `b`: `7 1 1` |
| 4 | `Day c(2, 0)` | `c` ra đời với 2 phần tử | `c`: `0 0` |
| 5 | (5) `c = b;` | `c` đã tồn tại: `operator=` (2): `delete[]` mảng 2 phần tử, xin mảng 3 phần tử, chép, in `gan` | `c`: `7 1 1` |
| 6 | `in(a)`, `in(b)`, `in(c)` | In ba dãy | không đổi |
| 7 | cuối `main` | Chết theo thứ tự ngược lúc tạo (`c`, `b`, `a`), mỗi lần in `huy day 3 phan tu` | heap trống |

**Kết quả khi chạy:**

```text
sao chep
gan
1 1 1 
7 1 1 
7 1 1 
huy day 3 phan tu
huy day 3 phan tu
huy day 3 phan tu
```

Điểm đáng nhìn: `c` đang có 2 phần tử nhưng sau phép gán có 3, nên phép gán **phải trả mảng cũ rồi xin mảng mới đúng cỡ**. Cả ba dòng `huy` đều ghi 3 phần tử vì lúc đó `c` đã đổi cỡ. Mình đã chạy với AddressSanitizer: không báo gì, thoát mã 0. In ra `in(a)` là `1 1 1` chứng tỏ `a` không bị đổi khi sửa `b` hay gán vào `c`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Sao chép nông khác sao chép sâu thế nào?"
    Sao chép nông chép từng thành viên, nên với con trỏ thì chép **địa chỉ**: hai đối tượng cùng trỏ một vùng nhớ. Sao chép sâu xin vùng nhớ **mới** và chép nội dung, nên mỗi đối tượng có vùng riêng. Trình biên dịch mặc định làm bản nông; nếu lớp có hàm hủy `delete` con trỏ thì bản nông dẫn tới hai đối tượng cùng giải phóng một chỗ (hành vi không xác định).

??? question "Rule of 3 là gì?"
    Nếu một lớp cần tự viết một trong ba hàm: hàm hủy, hàm tạo sao chép, phép gán sao chép, thì thường cần viết cả ba. Lý do: cần hàm hủy nghĩa là lớp giữ tài nguyên, nên hai hàm sao chép mặc định (chép nông) sẽ sai. Đây là quy tắc kinh nghiệm chứ không phải luật bắt buộc; từ C++11 nó mở rộng thành Rule of 5 (thêm hai hàm di chuyển) và Rule of 0 ([Bài 12](12-move-semantics.md)).

??? question "Vì sao cần phép gán sao chép riêng, và vì sao phải chống tự gán?"
    Khác với hàm tạo sao chép, phép gán chạy trên đối tượng **đã tồn tại** và đang giữ vùng nhớ cũ, nên phải trả hoặc tái dùng nó, không thì rò rỉ. Với `a = a`, nếu trả vùng cũ trước rồi mới chép từ `o`, ta chép từ vùng vừa bị trả: hành vi không xác định. Vì vậy kiểm `if (this != &o)` và trả về `*this`; cách an toàn hơn là copy-and-swap.

??? question "Khi nào dùng `= delete` cho hàm sao chép?"
    Khi sao chép không có nghĩa hoặc không an toàn cho kiểu đó, ví dụ lớp sở hữu duy nhất một tài nguyên như file, khóa hay `std::unique_ptr`. Cố sao chép sẽ là lỗi **biên dịch** (`use of deleted function`), tốt hơn nhiều so với lỗi lộ ra lúc chạy.

??? question "Vì sao hàm nên nhận tham số kiểu `const T&` thay vì `T`?"
    `T` truyền theo giá trị nên tạo một bản sao (gọi hàm tạo sao chép): với kiểu có sao chép sâu thì tốn xin và chép vùng nhớ. `const T&` chỉ là biệt danh của đối tượng gốc: không sao chép, và `const` bảo đảm hàm không sửa gốc. Với kiểu nhỏ như `int` thì truyền theo giá trị là bình thường.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Viết hàm hủy `delete` mà quên hai hàm sao chép"
    Đây là kịch bản của mục 1: sao chép mặc định chép nông, hai hàm hủy cùng `delete` một chỗ. Có hàm hủy là dấu hiệu để viết (hoặc `= delete`) cả hai hàm sao chép (Rule of 3).

!!! warning "Lỗi 2: Phép gán sao chép không chống tự gán"
    Thân hàm `delete p; p = new int(*o.p);` mà không có `if (this != &o)` sẽ hỏng ở `a = a;`, vì ta đọc `*o.p` sau khi đã trả. Lỗi này hiếm gặp khi chạy thử nhưng có thật (ví dụ `x[i] = x[j]` khi `i == j`).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="11" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn code sau. `Hop` chỉ có con trỏ `p` và hàm tạo (không có hàm hủy hay hàm sao chép riêng). Dòng cuối in ra gì?

```text
Hop a(5);
Hop b = a;
*b.p = 9;
std::cout << *a.p << " " << (a.p == b.p);
```

- `5 0`: bản sao có vùng nhớ riêng
- `5 1`: chung vùng nhưng `a` vẫn giữ 5
- `9 1`: hai con trỏ cùng chỉ vào chính một vùng nhớ
- `9 0`: vùng riêng nhưng giá trị bị chép lại

<p class="giai-thich" markdown>Hàm sao chép mặc định chép từng thành viên, nên `b.p` nhận cùng địa chỉ với `a.p` và so sánh cho `1`. Ghi 9 qua `b.p` cũng là ghi vào vùng của `a`, nên `*a.p` là 9 (mình đã chạy ra đúng `9 1`). Kết quả `5 0` mô tả sao chép sâu, chỉ có khi bạn tự viết hàm tạo sao chép. `9 0` tự mâu thuẫn (vùng riêng thì `a` vẫn là 5), còn `5 1` cũng tự mâu thuẫn theo chiều ngược lại: đã chung một vùng thì ghi qua `b.p` là `a` thấy ngay.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Đọc đoạn code sau. `Hop` có hàm tạo sao chép sâu đúng, và hàm hủy in `huy`. Có bao nhiêu dòng `huy` được in khi khối kết thúc?

```text
{
    Hop a(1);
    Hop b = a;
    Hop& r = b;
}
```

- 1 dòng, vì `b` chỉ là bản sao của `a`
- 2 dòng, vì `a` và `b` là hai đối tượng
- 3 dòng, vì có ba tên `a`, `b` và `r`
- 0 dòng, vì khối nhỏ ở đây không gọi hàm hủy nào

<p class="giai-thich" markdown>Có hai đối tượng `Hop` thật: `a`, và `b` được tạo bằng sao chép sâu, mỗi cái có vùng riêng nên mỗi cái chết một lần (mình đã chạy ra hai dòng `huy`). `r` là tham chiếu, chỉ là tên khác của `b` chứ không phải đối tượng mới, nên không có hàm hủy riêng. Hàm hủy của biến cục bộ chạy ở `}` của khối chứa nó, nên không phải là 0.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn code sau. Phép gán này không có kiểm tra tự gán. Điều gì xảy ra ở `a = a;`?

```text
Hop& operator=(const Hop& o) {
    delete p;
    p = new int(*o.p);
    return *this;
}
// trong main:
Hop a(5);
a = a;
```

- Trả mất vùng của `a` rồi đọc lại vùng đó: hành vi không xác định
- Không có gì xảy ra, vì gán một đối tượng cho chính nó luôn vô hại
- Lỗi biên dịch, vì C++ không cho gán một đối tượng cho chính nó
- Con trỏ `a.p` thành `nullptr`, và chương trình dừng lúc dùng `a`

<p class="giai-thich" markdown>Khi `o` chính là `a`, `delete p` trả đúng vùng mà `o.p` đang trỏ, rồi `*o.p` đọc vùng đã trả: hành vi không xác định, nên không thể khẳng định kết quả nào. Thêm `if (this != &o)` là cách chặn. C++ cho phép `a = a`, nên không có lỗi biên dịch, và nó không vô hại với phép gán viết như trên. `delete` cũng không tự đặt con trỏ về `nullptr`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Rule of 3 nói về ba hàm nào của một lớp?

- Hàm tạo, hàm hủy và hàm tạo sao chép của lớp
- Hàm tạo thường, hàm hủy và `operator=` của lớp
- Hàm tạo, phép gán sao chép và toán tử `new` của lớp
- Hàm hủy, hàm tạo sao chép và phép gán sao chép

<p class="giai-thich" markdown>Ba hàm là hàm hủy, hàm tạo sao chép và phép gán sao chép: cần tự viết một trong ba thì thường cần cả ba. Hàm tạo thường (hàm tạo bạn viết để dựng đối tượng, như `Hop(int v)`) không nằm trong bộ ba, vì nó không liên quan tới việc sao chép hay trả tài nguyên. `new` là toán tử xin bộ nhớ, không phải hàm đặc biệt của lớp. Đây là quy tắc kinh nghiệm, không phải luật bắt buộc.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn code sau. Chuyện gì xảy ra khi biên dịch?

```text
struct Hop {
    int* p;
    Hop(int v) { p = new int(v); }
    Hop(const Hop&) = delete;
};
Hop a(5);
Hop b = a;
```

- Biên dịch được, nhưng `b.p` cùng địa chỉ với `a.p`
- Lỗi biên dịch: gọi hàm sao chép đã bị `= delete`
- Biên dịch được, nhưng chương trình dừng lúc chạy
- Biên dịch được, và `b.p` thành `nullptr`

<p class="giai-thich" markdown>`Hop b = a;` cần hàm tạo sao chép, mà nó đã bị `= delete`, nên trình biên dịch báo lỗi `use of deleted function` ngay lúc biên dịch (mình đã thử). Vì có lỗi biên dịch nên chương trình không được tạo ra: không có chuyện cùng địa chỉ hay `nullptr`, và cũng không có cảnh dừng lúc chạy. Lợi ích của `= delete` là đúng chỗ đó: bắt lỗi sớm.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn code sau. `Hop` có hàm tạo sao chép in `copy!`. Chương trình in `copy!` mấy lần?

```text
void f(Hop h) {}
void g(const Hop& h) {}
Hop a(1);
f(a);
g(a);
f(a);
```

- 0 lần, vì `a` đã tồn tại từ trước
- 1 lần, vì chỉ lần đầu cần chép tham số
- 3 lần, vì mỗi lần gọi hàm đều phải chép
- 2 lần, vì `f` nhận theo giá trị

<p class="giai-thich" markdown>Mỗi lần gọi `f(a)`, tham số `h` là một biến mới được tạo bằng hàm tạo sao chép từ `a`, nên hai lần gọi `f` cho hai lần `copy!` (mình đã chạy). `g` nhận biệt danh của `a` nên không chép. Việc `a` đã tồn tại không ngăn chép, vì `h` là một đối tượng khác. Còn "chỉ lần đầu" sai: lần gọi thứ hai tạo lại một tham số mới.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** "Copy-and-swap" nói về điều gì?

- Chép gốc vào bản tạm, rồi hoán đổi ruột với đích
- Cấm sao chép bằng `= delete`, rồi hoán đổi hai đối tượng bằng tay
- Trao hẳn quyền sở hữu vùng nhớ cho đích và để gốc rỗng
- Chép con trỏ rồi cho hai đối tượng đổi chỗ để cùng giữ một vùng

<p class="giai-thich" markdown>Copy-and-swap là một cách viết phép gán an toàn: chép đối tượng gốc vào một bản tạm trước, rồi hoán đổi ruột của bản tạm với đối tượng đích, để bản tạm mang vùng cũ đi và tự trả. Nó không liên quan tới `= delete`, vốn là cách cấm sao chép. Trao quyền sở hữu và để gốc rỗng là ý tưởng khác, di chuyển, của [Bài 12](12-move-semantics.md). Còn cho hai đối tượng cùng giữ một vùng chính là sao chép nông mà ta đang tránh.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Đọc đoạn code sau. `Hop` có đủ ba hàm. Hai dòng cuối gọi hàm nào?

```text
Hop a(1);
Hop b(2);
Hop c = a;
b = a;
```

- `Hop c = a;` gọi phép gán, còn `b = a;` gọi hàm tạo sao chép
- Cả hai dòng đều gọi phép gán sao chép của `Hop`
- `Hop c = a;` gọi hàm tạo sao chép, còn `b = a;` gọi phép gán sao chép
- Cả hai dòng đều gọi hàm tạo sao chép của `Hop`

<p class="giai-thich" markdown>`Hop c = a;` **tạo** `c` mới nên gọi hàm tạo sao chép, còn `b = a;` gán vào `b` đã có nên gọi phép gán sao chép (mình đã chạy: in `copy!` rồi `gan`). Dấu `=` ở dòng khai báo không làm nó thành phép gán, nên hai lựa chọn "cả hai cùng một loại" đều sai. Lựa chọn đảo ngược hai hàm sai vì phép gán cần một đối tượng đã tồn tại để ghi vào.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Sao chép mặc định chép từng thành viên, nên với con trỏ thô thì chép địa chỉ (sao chép nông): hai đối tượng cùng giữ một vùng nhớ, và nếu hàm hủy `delete` nó thì dẫn tới giải phóng hai lần (hành vi không xác định).
2. Sao chép sâu: hàm tạo sao chép `Hop(const Hop& o)` xin vùng mới và chép nội dung, nên mỗi đối tượng có vùng riêng và hàm hủy `delete` đúng một lần cho mỗi vùng.
3. Phép gán sao chép (`operator=`, cách `=` hoạt động cho kiểu đó) chạy trên đối tượng đã tồn tại, nên phải trả vùng cũ, chống tự gán bằng `if (this != &o)` và trả về `*this`; đây là một cách viết thường gặp, còn copy-and-swap là cách chuẩn hóa việc "xin mới trước, trả cũ sau" (chỉ cần biết tên).
4. Rule of 3: cần tự viết một trong {hàm hủy, hàm tạo sao chép, phép gán sao chép} thì thường cần cả ba (quy tắc kinh nghiệm); Rule of 5 và Rule of 0 ở [Bài 12](12-move-semantics.md).
5. `= delete` cấm sao chép bằng lỗi biên dịch (cách `unique_ptr` làm, [Bài 09](09-unique-ptr.md)); truyền theo giá trị gọi hàm tạo sao chép còn `const T&` thì không, nên với kiểu sao chép sâu tốn kém hãy truyền `const T&`.
