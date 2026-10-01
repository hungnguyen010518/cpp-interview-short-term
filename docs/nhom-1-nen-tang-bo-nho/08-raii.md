# Bài 08 — RAII: tài nguyên tự trả khi đối tượng chết

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích RAII bằng lời và bằng code: xin tài nguyên trong hàm tạo, trả trong hàm hủy, nên không cần nhớ trả.
    - Hiểu hàm hủy của biến cục bộ chạy ở cuối khối `{}`, cả khi `return` sớm lẫn khi có ngoại lệ (`throw`).
    - Tự viết một lớp bọc nhỏ giữ `new int` và `delete` trong hàm hủy, biết vì sao copy lớp đó là nguy hiểm, và so sánh với `defer` của Go.

**Bạn cần biết trước:** [Bài 02](02-stack-heap-static.md) (hàm tạo, hàm hủy, khối `{}`), [Bài 06](06-tham-chieu-const.md) (hàm tạo sao chép) và [Bài 07](07-new-delete.md) (`new`/`delete`, rò rỉ, hàm `xuLy` thoát sớm).

## 🧠 Câu chuyện mở đầu

Ở Bài 07, kho đồ của trường bắt bạn **tự đi trả** phòng: quên một lần là phòng bị giữ mãi. Bây giờ hãy nghĩ tới **thư viện**. Bạn bước vào, mượn sách ở quầy. Đến lúc bước ra khỏi cửa, sách **tự động được trả**: bạn không cần nhớ, và cũng không thể "quên trả" vì cánh cửa lo việc đó.

RAII là ý tưởng đó trong C++. Tài nguyên được mượn lúc đối tượng **ra đời** và được trả lúc đối tượng **chết**. Bạn chỉ cần để đối tượng chết đúng lúc; việc trả đã gắn sẵn vào hàm hủy.

!!! info "Chỗ nào ví dụ thư viện không còn đúng?"
    Cửa thư viện thật là của thư viện. Trong C++, "cánh cửa" là chính dấu `}` kết thúc khối chứa đối tượng, và việc trả là code do **bạn viết một lần** trong hàm hủy. Máy chỉ lo gọi nó đúng lúc.

## 📖 Giải thích

### 1. Ôn: hàm hủy chạy ở cuối khối `{}`

Từ Bài 02, bạn đã biết: hàm tạo chạy khi đối tượng ra đời, hàm hủy chạy khi nó chết, và biến cục bộ chết ở dấu `}` kết thúc khối chứa nó. Ta kiểm lại bằng struct `TheMuon` (thẻ mượn sách) in `muon` khi ra đời và `tra` khi chết:

```cpp
#include <iostream>

struct TheMuon {
    int so;
    TheMuon(int s) {
        so = s;
        std::cout << "muon " << so << "\n";
    }
    ~TheMuon() {
        std::cout << "tra " << so << "\n";
    }
};

int main() {
    TheMuon a(1);                      // (1)
    {
        std::cout << "vao khoi\n";
        TheMuon b(2);                  // (2)
        TheMuon c(3);                  // (3)
        std::cout << "het khoi\n";
    }                                  // (4)
    std::cout << "ra khoi\n";
    return 0;
}                                      // (5)
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `a` ra đời, hàm tạo in `muon 1` | stack: `a` (số 1) |
| in `vao khoi` | Vào khối nhỏ `{` | không đổi |
| (2) | `b` ra đời, in `muon 2` | stack: `a`, `b` |
| (3) | `c` ra đời, in `muon 3` | stack: `a`, `b`, `c` |
| in `het khoi` | Hết việc trong khối | không đổi |
| (4) `}` | Khối kết thúc: `c` chết trước (in `tra 3`), rồi `b` (in `tra 2`) | stack: chỉ còn `a` |
| in `ra khoi` | Đã ra khỏi khối nhỏ | không đổi |
| (5) `}` của `main` | `a` chết, in `tra 1` | stack trống |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`):

```text
muon 1
vao khoi
muon 2
muon 3
het khoi
tra 3
tra 2
ra khoi
tra 1
```

Hai điều cần nhớ. Một: hàm hủy chạy **ngay tại `}`**, không ai gọi tay. Hai: trong cùng một khối, đối tượng ra đời sau thì chết trước (`c` rồi `b`), giống như xếp chồng thẻ và lấy từ trên xuống.

**Thử thay đổi: bỏ cặp `{ }` quanh `b` và `c`** (để chúng nằm thẳng trong `main`). Mình đã chạy: `tra 3`, `tra 2`, `tra 1` đều dồn về cuối, sau `ra khoi`, vì giờ cả ba cùng chết ở `}` của `main`, vẫn theo thứ tự ngược với lúc tạo.

### 2. RAII là gì?

**RAII** viết tắt của *Resource Acquisition Is Initialization*, dịch thoáng là "xin tài nguyên chính là khởi tạo". Cách làm gồm hai bước: **xin tài nguyên trong hàm tạo**, **trả trong hàm hủy**. Từ đó trở đi, chỉ cần để đối tượng sống ở một biến cục bộ: ra khỏi khối là tài nguyên được trả.

**Tài nguyên (resource)** là bất cứ thứ gì "mượn rồi phải trả": bộ nhớ ở heap (Bài 07), một file đang mở, một cái khóa đang giữ (để hai phần của chương trình không cùng sửa một thứ một lúc), một kết nối mạng, một ổ cắm mạng. Thư viện chuẩn của C++ có sẵn nhiều lớp theo kiểu này, bạn chỉ cần biết tên: `std::ifstream` mở file khi tạo và đóng khi hủy; `std::lock_guard` giữ khóa khi tạo và mở khóa khi hủy. Bài này không đi sâu vào chúng, mà tự viết một lớp nhỏ để hiểu bên trong.

!!! info "Bạn biết Go?"
    Go có `defer f.Close()`: đóng file đúng lúc hàm thoát. Hàm hủy làm việc tương tự, nhưng có hai khác biệt thật. Thứ nhất, `defer` là việc **bạn phải nhớ viết** ở từng nơi dùng; còn RAII gắn việc trả vào **chính kiểu dữ liệu**, nên dùng kiểu đó là tự được trả, không cần nhớ viết ở từng nơi dùng. Thứ hai, `defer` chạy ở **cuối hàm**, còn hàm hủy chạy ở cuối **khối `{}`** chứa đối tượng, có thể sớm hơn nhiều.

### 3. Thí nghiệm: thoát sớm, cách thủ công và cách RAII

Ta lấy lại hàm `xuLy` của Bài 07. Bản (a) quản lý bằng `new`/`delete` thủ công; bản (b) để một đối tượng cục bộ lo. Mỗi bản đều gọi `xuLy(5)` rồi `xuLy(-1)` (số âm kích hoạt `return` sớm).

**(a) Thủ công** (không phải UB: chỉ bị rò rỉ, chương trình vẫn đúng luật):

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

void xuLy(int cao) {
    Cay* p = new Cay(cao);                // (1)
    if (cao < 0) {
        std::cout << "cao am, thoat som\n";
        return;                           // (2)
    }
    std::cout << "xu ly cay cao " << p->cao << "\n";
    delete p;                             // (3)
}

int main() {
    xuLy(5);
    xuLy(-1);
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `xuLy(5)`, (1) | Xin heap, hàm tạo in `tao 5` | heap: `Cay` cao 5 |
| in `xu ly cay cao 5` | `cao < 0` sai nên bỏ qua `if`, rồi dùng cây | không đổi |
| (3) `delete p;` | Hàm hủy in `huy 5`, trả chỗ | heap: sạch |
| `xuLy(-1)`, (1) | Xin heap, in `tao -1` | heap: `Cay` cao -1 |
| in `cao am, thoat som` | `cao < 0` đúng, vào `if` | không đổi |
| (2) `return;` | Thoát hàm ngay, **nhảy qua (3)**; biến `p` mất | heap: `Cay` cao -1 bị bỏ rơi |
| in `xong` | Về `main` | in `xong` |

**Kết quả khi chạy:**

```text
tao 5
xu ly cay cao 5
huy 5
tao -1
cao am, thoat som
xong
```

Lần gọi thứ hai có `tao -1` mà **không có `huy -1`**: đây chính là hàm đã gặp ở Bài 07, rò rỉ vì `delete` bị nhảy qua.

**(b) RAII**: không còn `new` và `delete`. `Cay` là biến cục bộ, nên hàm hủy của nó tự chạy:

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

void xuLy(int cao) {
    Cay c(cao);                           // (1)
    if (cao < 0) {
        std::cout << "cao am, thoat som\n";
        return;                           // (2)
    }
    std::cout << "xu ly cay cao " << c.cao << "\n";
}                                         // (3)

int main() {
    xuLy(5);
    xuLy(-1);
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `xuLy(5)`, (1) | `c` ra đời trên stack, in `tao 5` | stack: `c` (cao 5) |
| in `xu ly cay cao 5` | `cao < 0` sai, dùng cây | không đổi |
| (3) `}` | Hết hàm, `c` chết, in `huy 5` | stack của `xuLy` bị dọn |
| `xuLy(-1)`, (1) | `c` ra đời, in `tao -1` | stack: `c` (cao -1) |
| in `cao am, thoat som` | Vào `if` | không đổi |
| (2) `return;` | Thoát hàm: **mọi biến cục bộ đang sống đều chết trước khi hàm trả về**, nên `c` chết, in `huy -1` | stack của `xuLy` bị dọn |
| in `xong` | Về `main` | in `xong` |

**Kết quả khi chạy:**

```text
tao 5
xu ly cay cao 5
huy 5
tao -1
cao am, thoat som
huy -1
xong
```

Dòng `huy -1` **xuất hiện**, đúng giữa `cao am, thoat som` và `xong`. Không có dòng `delete` nào để nhảy qua. Dù hàm có thêm mười chỗ `return`, mỗi chỗ đều ra khỏi khối chứa `c` và làm `c` chết.

**Thử thay đổi: chạy cả hai bản với AddressSanitizer** (lệnh ở Bài 07, mục 5). Mình đã chạy: bản (a) bị LeakSanitizer báo `4 byte(s) leaked in 1 allocation(s)` ở dòng `new Cay(cao)` và thoát mã 1; bản (b) không báo gì và thoát mã 0. Nhớ rằng im lặng của công cụ không chứng minh chương trình sạch, nhưng ở đây ta còn thấy bằng mắt: có `huy -1`.

!!! warning "Hay nhầm"
    "Biến cục bộ ở stack thì không cần hàm hủy" là sai. Hàm hủy chạy với **mọi** đối tượng, kể cả ở stack. Chính vì thế RAII dùng được: ta đặt việc trả vào hàm hủy của một biến cục bộ.

### 4. Ngoại lệ: `throw`, `try`, `catch`

Ngoại lệ (đã nhắc ở Bài 07) là cách báo lỗi bằng cách **cắt ngang hàm đang chạy**. Cú pháp gồm ba mảnh:

```text
throw 5;                       // ném một giá trị ra: hàm hiện tại dừng ngay tại đây
try { ... }                    // vùng "thử": code trong này có thể ném
catch (int ma) { ... }         // nếu có ném một int, nhảy tới đây và gán vào ma
```

Khi `throw` chạy, chương trình **không** chạy tiếp dòng sau nó. Nó thoát khỏi hàm hiện tại, rồi hàm đã gọi hàm đó, cứ thế đi ngược lên cho tới khi gặp một `catch` có kiểu khớp, và chạy khối `catch` đó. **Kiểu** của giá trị được ném quyết định `catch` nào bắt: `catch (int ma)` không bắt được một `std::string`. Ở đây ta ném số `int` cho đơn giản; code thật thường ném đối tượng lỗi như `std::runtime_error`.

!!! info "Bạn biết Go?"
    Go báo lỗi thông thường bằng giá trị `error` trả về, và bạn kiểm tra `if err != nil` ở từng nơi. `throw` thì không trả về gì: nó nhảy thẳng tới `catch` gần nhất ở phía trên, nên gần với `panic` + `recover` của Go hơn. Khác biệt lớn: C++ dùng ngoại lệ như cách báo lỗi bình thường trong nhiều thư viện (ví dụ `new` hết chỗ ném `std::bad_alloc`), còn Go chủ yếu để `panic` cho tình huống nghiêm trọng.

Câu hỏi quan trọng: khi hàm bị cắt ngang, các đối tượng cục bộ của nó có được dọn không? Thử với `Cay` ở dạng RAII:

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

void xuLy(int cao) {
    Cay c(cao);                           // (1)
    std::cout << "truoc khi throw\n";
    if (cao < 0) {
        throw cao;                        // (2)
    }
    std::cout << "sau khi throw\n";       // (3)
}

int main() {
    try {                                 // (4)
        xuLy(-1);
        std::cout << "xuLy xong\n";
    } catch (int ma) {                    // (5)
        std::cout << "bat duoc loi " << ma << "\n";
    }
    std::cout << "xong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (4) `try {` | Bắt đầu vùng thử | không đổi |
| `xuLy(-1)`, (1) | `c` ra đời, in `tao -1` | stack: `c` (cao -1) |
| in `truoc khi throw` | Chạy bình thường | không đổi |
| (2) `throw cao;` | Ném `-1`. `xuLy` bị cắt ngang; dòng (3) và dòng `xuLy xong` **không chạy** | đang "tháo" |
| (trong lúc thoát khỏi `xuLy`) | `c` chết, in `huy -1` | stack của `xuLy` bị dọn |
| (5) `catch (int ma)` | Kiểu `int` khớp: `ma` = -1, in `bat duoc loi -1` | stack: `ma` trong `main` |
| in `xong` | Chạy tiếp sau khối `catch` | in `xong` |

**Kết quả khi chạy:**

```text
tao -1
truoc khi throw
huy -1
bat duoc loi -1
xong
```

Chú ý thứ tự: `huy -1` in **trước** `bat duoc loi -1`. Hàm hủy của `c` chạy trong lúc chương trình còn đang đi ngược ra khỏi `xuLy`, rồi mới tới thân khối `catch`.

Việc đi ngược từ nơi `throw` lên nơi `catch`, hủy mọi đối tượng cục bộ trên đường đi, gọi là **tháo ngăn xếp (stack unwinding)** (ngăn xếp = stack, cái bàn học của Bài 02; không phải "ngăn" của tủ khóa). Nó là lý do RAII an toàn với ngoại lệ: dù hàm bị cắt ngang ở đâu, các đối tượng đã ra đời đều được hủy.

Cùng hàm đó nhưng viết thủ công (`Cay* p = new Cay(cao);` ... `delete p;` ở cuối): mình đã chạy, kết quả là `tao -1`, `truoc khi throw`, `bat duoc loi -1`, `xong`. **Không có `huy -1`**: dòng `delete p;` bị nhảy qua, và ASan báo rò rỉ 4 byte. Con trỏ `p` mất, còn chỗ ở heap thì không ai giữ hay trả.

**Thử thay đổi: đưa `if (cao < 0) { throw cao; }` lên trước dòng `Cay c(cao);`.** Mình đã chạy: output chỉ còn `bat duoc loi -1` rồi `xong`. Không có `tao` lẫn `huy`, vì lúc `throw`, `c` **chưa ra đời**: chỉ đối tượng đã ra đời mới được hủy.

Có hai điều cần nói cho chắc. Nếu ngoại lệ **không bị bắt ở đâu cả** (bỏ `try`/`catch` đi), chương trình gọi `std::terminate` và thường bị dừng đột ngột. Khi đó việc hàm hủy của các đối tượng có chạy hay không là **do cài đặt quyết định**, chuẩn không hứa, nên đừng dựa vào nó:

```cpp
// bo-qua-kiem-tra
void xuLy(int cao) {
    Cay c(cao);
    throw cao;          // không có try/catch nào ở trên: std::terminate
}
```

Mình có thử trên máy mình: g++ in `terminate called after throwing an instance of 'int'` và chương trình bị hủy bỏ (mã thoát 134). Còn việc có thấy `huy` hay không thì mình không ghi ở đây, vì đó là chỗ chuẩn để ngỏ.

Điều thứ hai: hàm hủy **không nên ném ngoại lệ**. Từ C++11, hàm hủy mặc định là `noexcept` (hứa không ném ngoại lệ ra ngoài), và nếu một ngoại lệ thoát ra khỏi hàm hủy thì chương trình gọi `std::terminate`. Vì thế đừng ném từ hàm hủy.

### 5. Tự viết một lớp RAII: `Hop`

Ta tự bọc một tài nguyên in được: một chỗ `int` ở heap. Lớp `Hop` (cái hộp) xin chỗ bằng `new` trong hàm tạo và trả bằng `delete` trong hàm hủy. Mình dùng `struct` cho gọn (ở đây `class` và `struct` dùng như nhau, như Bài 02 đã nói):

```cpp
#include <iostream>

struct Hop {
    int* p;
    Hop(int v) {
        p = new int(v);                        // (1)
        std::cout << "hop: xin heap, gia tri " << *p << "\n";
    }
    ~Hop() {
        std::cout << "hop: tra heap, gia tri " << *p << "\n";
        delete p;                              // (2)
    }
};

void dung(int v) {
    Hop h(v);                                  // (3)
    if (v < 0) {
        std::cout << "am, thoat som\n";
        return;                                // (4)
    }
    std::cout << "dung hop, gia tri " << *h.p << "\n";
}

int main() {
    dung(7);
    dung(-1);
    std::cout << "xong\n";
    return 0;
}
```

Người dùng `Hop` không viết `new` hay `delete` ở đâu cả: (1) và (2) nằm gọn trong lớp.

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `dung(7)`, (3) | `h` ra đời trên stack; hàm tạo (1) xin heap, ghi 7, in `hop: xin heap, gia tri 7` | stack: `h.p` = 0x9000; heap: 0x9000 chứa 7 (địa chỉ minh họa) |
| in `dung hop, gia tri 7` | `v < 0` sai nên dùng hộp: `*h.p` đọc qua con trỏ trong hộp | không đổi |
| (cuối `dung`) | `h` chết, hàm hủy in `hop: tra heap, gia tri 7` rồi (2) `delete p;` | heap: 0x9000 đã trả |
| `dung(-1)`, (3) | `h` ra đời, xin heap, ghi -1, in `hop: xin heap, gia tri -1` | heap: 0x9000 (hoặc chỗ khác) chứa -1 |
| in `am, thoat som` | Vào `if` | không đổi |
| (4) `return;` | Thoát hàm: `h` chết, in `hop: tra heap, gia tri -1` rồi `delete p;` | heap: đã trả |
| in `xong` | Về `main` | in `xong` |

**Kết quả khi chạy:**

```text
hop: xin heap, gia tri 7
dung hop, gia tri 7
hop: tra heap, gia tri 7
hop: xin heap, gia tri -1
am, thoat som
hop: tra heap, gia tri -1
xong
```

Mỗi lần "xin" có đúng một lần "tra", kể cả lần thoát sớm. Mình đã chạy bản này với ASan: không có báo cáo nào và thoát mã 0 (nhắc lại: im lặng không chứng minh là sạch, nhưng khớp với việc ta đếm được đủ cặp xin/tra).

**Thử thay đổi: thêm dòng `Hop k(v + 1);` ngay sau `Hop h(v);`.** Mình đã chạy: với `dung(7)` ta thấy xin 7, xin 8, rồi lúc hết hàm là `tra 8` **trước** `tra 7` (ngược thứ tự tạo, như mục 1). Với `dung(-1)` thì thấy xin -1, xin 0, và khi `return` là `tra 0` rồi `tra -1`.

### 6. Chỗ nguy hiểm: copy một lớp giữ con trỏ thô

Lớp `Hop` có một cái bẫy. Khi bạn **sao chép** một `Hop`, nếu bạn không tự viết hàm tạo sao chép (Bài 06), trình biên dịch tự viết một bản **chép từng trường**. Trường của `Hop` chỉ có một: con trỏ `p`. Vậy bản sao nhận **cùng địa chỉ** ở heap, không phải một chỗ mới:

```cpp
// bo-qua-kiem-tra
struct Hop {
    int* p;
    Hop(int v) { p = new int(v); }
    ~Hop() { delete p; }
};

int main() {
    Hop a(5);
    Hop b = a;      // sao chép: b.p có cùng địa chỉ với a.p
    return 0;       // a chết: delete p; b chết: delete p lần nữa
}
```

```text
stack:   a.p = 0x9000 ------+
                             v
heap:                     [ 0x9000: 5 ]
                             ^
stack:   b.p = 0x9000 ------+     <- hai tờ giấy cùng ghi số phòng 0x9000
```

Cuối `main`, `b` chết (hàm hủy `delete 0x9000`), rồi `a` chết (lại `delete 0x9000`): đó là **giải phóng hai lần** của Bài 07, là hành vi không xác định. Vì thế mình để code trong khối bỏ qua và **không ghi kết quả**. Ý chính: mỗi tài nguyên chỉ nên có **một** chủ lo việc trả, còn ở đây có hai. Cách sửa (các quy tắc "rule of 3/5") nằm ở Bài 11; bài này chỉ cần bạn biết lớp bọc con trỏ thô cần được để ý khi copy.

### 7. Chốt: đừng gọi `delete` tay

Nhìn lại những gì ta thấy: `return` sớm làm sót `delete`, ngoại lệ làm sót `delete`, nhưng đối tượng cục bộ luôn được hủy. Quy tắc rút ra: **đừng viết `delete` tay ở code dùng; để một đối tượng lo.** Lớp `Hop` ở trên là bản tự làm cho một `int`. Thư viện chuẩn có bản **làm sẵn** cho bộ nhớ ở heap, tên `std::unique_ptr`, là nội dung Bài 09: bạn sẽ không phải tự viết `Hop` nữa, và nó còn chặn copy (sẽ thấy ở Bài 09).

!!! question "Hỏi nhanh: vậy `new` và `delete` dùng ở đâu?"
    Gần như chỉ **bên trong** các lớp RAII như `Hop`. Code của người dùng thì giữ đối tượng ở biến cục bộ (hoặc trong lớp RAII làm sẵn) và để hàm hủy lo phần trả.

## 💻 Ví dụ code

### Ví dụ 1: tháo ngăn xếp qua hai hàm

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

void trong() {
    Cay b(2);                         // (1)
    throw 99;                         // (2)
}

void giua() {
    Cay a(1);                         // (3)
    trong();                          // (4)
    std::cout << "khong in dong nay\n";
}

int main() {
    try {
        giua();
    } catch (int ma) {                // (5)
        std::cout << "bat duoc " << ma << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `giua()`, (3) | `a` ra đời, in `tao 1` | stack: `a` |
| (4) gọi `trong()`, (1) | `b` ra đời, in `tao 2` | stack: `a`, `b` |
| (2) `throw 99;` | Ném 99, `trong` bị cắt ngang | đang "tháo" |
| (thoát khỏi `trong`) | `b` chết, in `huy 2` | stack: `a` |
| (thoát khỏi `giua`) | Dòng `khong in dong nay` bị bỏ qua; `a` chết, in `huy 1` | stack trống |
| (5) | `catch` khớp `int`, in `bat duoc 99` | `ma` = 99 |

**Kết quả khi chạy:**

```text
tao 1
tao 2
huy 2
huy 1
bat duoc 99
```

Ngoại lệ đi qua **hai khung hàm**, và cả hai đối tượng đều được hủy, theo thứ tự ngược với lúc tạo, trước khi tới `catch`.

**Thử thay đổi: bỏ `try`/`catch` trong `main`, chỉ để `giua();`.** Đây là trường hợp "không bắt ở đâu cả" (mục 4). Mình không ghi output: việc có in `huy` hay không là do cài đặt quyết định.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "RAII là gì? Cho ví dụ trong thư viện chuẩn."
    RAII (Resource Acquisition Is Initialization) là kỹ thuật gắn vòng đời của tài nguyên vào vòng đời của một đối tượng: tài nguyên được xin trong hàm tạo và trả trong hàm hủy. Vì hàm hủy của biến cục bộ tự chạy khi ra khỏi khối, tài nguyên được trả mà không cần ai nhớ. Ví dụ trong chuẩn: `std::lock_guard` (giữ và nhả khóa), `std::ifstream` (mở và đóng file), `std::unique_ptr` (giữ và `delete` bộ nhớ), `std::vector` và `std::string` (tự quản lý bộ nhớ bên trong).

??? question "Vì sao RAII an toàn với ngoại lệ?"
    Khi một ngoại lệ được ném, chương trình tháo ngăn xếp: nó thoát khỏi từng hàm và gọi hàm hủy của mọi đối tượng cục bộ đã ra đời trên đường tới `catch`. Nên tài nguyên nằm trong đối tượng RAII luôn được trả, còn `delete` viết tay ở cuối hàm thì bị nhảy qua. Hedge cho đúng: nếu ngoại lệ không bị bắt ở đâu cả, chương trình gọi `std::terminate` và việc hủy các đối tượng là do cài đặt quyết định.

??? question "Hàm hủy chạy khi nào?"
    Với biến cục bộ: khi chương trình ra khỏi khối chứa nó, dù bằng chạy hết khối, `return` hay ngoại lệ được bắt ở ngoài; các biến trong cùng khối chết theo thứ tự ngược với lúc tạo. Với đối tượng ở heap: khi `delete`. Với biến global: sau khi `main` kết thúc. Nó không chạy nếu chương trình bị dừng đột ngột (sập hoặc bị kết thúc từ bên ngoài).

??? question "RAII khác `defer` của Go thế nào?"
    Cả hai đều giúp dọn dẹp đúng lúc. Khác biệt: `defer` là việc lập trình viên phải nhớ viết ở từng nơi dùng tài nguyên (quên là sót), còn RAII gắn việc trả vào chính kiểu dữ liệu nên dùng kiểu đó là tự được trả. Ngoài ra `defer` chạy ở cuối hàm, còn hàm hủy chạy ở cuối khối `{}` chứa đối tượng, có thể sớm hơn.

??? question "Vì sao lớp RAII giữ con trỏ thô cần để ý khi copy?"
    Nếu không có hàm tạo sao chép riêng, trình biên dịch chép từng trường, nên hai đối tượng giữ cùng một con trỏ. Cả hai hàm hủy đều `delete` cùng một chỗ, tức giải phóng hai lần (hành vi không xác định). Muốn đúng phải quản lý quyền sở hữu khi copy, đó là rule of 3/5 (Bài 11), hoặc dùng sẵn `std::unique_ptr` (Bài 09).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Viết `new` rồi `delete` tay trong hàm có nhiều đường thoát"
    `return` sớm và ngoại lệ đều nhảy qua `delete` (mục 3 và 4). Đưa tài nguyên vào một đối tượng cục bộ (RAII) thì mọi đường thoát đều đi qua hàm hủy.

!!! warning "Lỗi 2: Tưởng ngoại lệ không bị bắt thì hàm hủy vẫn chắc chắn chạy"
    Hàm hủy chạy khi tháo ngăn xếp, mà tháo ngăn xếp gắn với việc có một `catch` bắt ở đâu đó. Nếu không có, chương trình gọi `std::terminate` và việc hủy là do cài đặt quyết định (mục 4). Đừng dựa vào nó để dọn dẹp.

!!! warning "Lỗi 3: Copy lớp giữ con trỏ thô"
    Chép con trỏ chứ không chép chỗ được trỏ tới, nên hai đối tượng cùng `delete` một chỗ (mục 6). Bài 11 dạy cách sửa; Bài 09 có bản làm sẵn.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="08" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Ý cốt lõi của RAII là gì?

- Dùng `new` và `delete` thật cẩn thận ở mọi nơi trong chương trình
- Xin tài nguyên trong hàm tạo, trả trong hàm hủy để tự động trả
- Bắt mọi ngoại lệ bằng `try`/`catch` để không có gì bị sót
- Chỉ cho một biến global giữ tài nguyên trong suốt chương trình

<p class="giai-thich" markdown>RAII gắn việc xin tài nguyên vào hàm tạo và việc trả vào hàm hủy, nên khi đối tượng chết thì tài nguyên được trả mà không ai phải nhớ. Cẩn thận với `delete` tay chính là cách mong manh mà RAII muốn thay thế. `try`/`catch` xử lý ngoại lệ chứ không trả tài nguyên giúp bạn. Còn giữ trong biến global chỉ làm tài nguyên sống đến hết chương trình, không liên quan đến việc trả đúng lúc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Hàm hủy của một biến cục bộ chạy vào lúc nào?

- Lúc chương trình kết thúc, cùng với mọi biến khác
- Lúc bạn gọi `delete` cho biến đó
- Lúc hàm chứa nó trả về, dù biến nằm ở khối nào
- Lúc ra khỏi khối `{}` chứa nó

<p class="giai-thich" markdown>Biến cục bộ chết khi chương trình ra khỏi khối chứa nó, dù bằng chạy hết khối, `return` hay ngoại lệ, và hàm hủy chạy đúng lúc đó. Không phải lúc chương trình kết thúc: đó là thời điểm của biến global. `delete` chỉ dành cho đối tượng xin bằng `new`, còn biến cục bộ không cần và không được `delete`. Nói "lúc hàm trả về" sai với biến nằm trong khối nhỏ bên trong hàm: nó chết sớm hơn, ngay ở `}` của khối nhỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn code sau (`Cay` in `tao n` ở hàm tạo và `huy n` ở hàm hủy). Chương trình in ra theo thứ tự nào?

```text
void f(int s) { Cay c(s); if (s > 1) return; std::cout << "giua\n"; }
int main() { f(1); f(2); std::cout << "xong\n"; }
```

- `tao 1, giua, huy 1, tao 2, huy 2, xong`
- `tao 1, giua, huy 1, tao 2, xong`
- `tao 1, huy 1, tao 2, huy 2, giua, xong`
- `tao 1, giua, huy 1, tao 2, giua, huy 2, xong`

<p class="giai-thich" markdown>`c` là biến cục bộ nên hàm hủy của nó chạy khi ra khỏi `f`, kể cả khi `f(2)` thoát bằng `return` sớm: nên vẫn có `huy 2`, còn `giua` chỉ in ở lần gọi đầu. Mình đã chạy ra đúng dãy này. Dãy thiếu `huy 2` cho rằng `return` sớm làm mất hàm hủy, điều đó đúng với `delete` viết tay chứ không đúng với đối tượng cục bộ. Dãy có hai chữ `giua` quên rằng `return` bỏ qua dòng in đó ở lần gọi thứ hai. Dãy đặt `giua` sau hai lần `huy` nhầm thứ tự: mỗi `huy` in ngay khi `f` kết thúc, nên `giua` của lần đầu đến trước.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). Chương trình in ra gì?

```text
void g() { Cay a(1); Cay b(2); throw 5; std::cout << "sau\n"; }
int main() { try { g(); } catch (int e) { std::cout << "bat " << e << "\n"; } }
```

- `tao 1, tao 2, sau, huy 2, huy 1, bat 5`
- `tao 1, tao 2, bat 5`
- `tao 1, tao 2, huy 2, huy 1, bat 5`
- `tao 1, tao 2, huy 1, huy 2, bat 5`

<p class="giai-thich" markdown>`throw` cắt ngang `g` ngay tại đó, nên `sau` không bao giờ in. Khi tháo ngăn xếp, `b` rồi `a` chết (ngược thứ tự tạo), nên `huy 2` rồi `huy 1`, và chỉ sau đó mới tới khối `catch` in `bat 5`. Mình đã chạy ra đúng dãy này. Dãy `tao 1, tao 2, bat 5` nhầm rằng ngoại lệ làm mất hàm hủy, trong khi tháo ngăn xếp chính là để chạy chúng. Dãy `huy 1` trước `huy 2` quên rằng trong cùng khối, cái ra đời sau chết trước.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** RAII khác `defer` của Go ở điểm nào?

- `defer` chạy ở cuối khối còn hàm hủy chạy ở cuối hàm
- `defer` chỉ dùng được cho bộ nhớ còn RAII dùng cho cả file
- Hàm hủy phải do người dùng gọi tay còn `defer` thì tự chạy
- RAII gắn việc trả vào kiểu, không cần nhớ viết mỗi nơi

<p class="giai-thich" markdown>Với `defer`, bạn phải nhớ viết nó ở từng nơi dùng tài nguyên; với RAII, việc trả nằm trong hàm hủy của kiểu, nên bạn không cần nhớ viết nó ở từng nơi dùng. Hai lựa chọn đầu bị đảo hoặc sai: `defer` chạy ở cuối hàm còn hàm hủy ở cuối khối, và `defer` dùng được cho cả file, khóa, bất cứ việc dọn nào. Còn hàm hủy tự chạy, không ai gọi tay, nên lựa chọn nói ngược lại là sai.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Vì sao một lớp giữ con trỏ thô (như `Hop`) nguy hiểm khi bị copy?

- Vì copy làm con trỏ trỏ vào `nullptr` ở cả hai đối tượng
- Vì hai đối tượng cùng `delete` một chỗ ở heap
- Vì copy chép cả vùng heap, làm tốn gấp đôi bộ nhớ
- Vì hàm hủy của bản sao không bao giờ được chạy

<p class="giai-thich" markdown>Bản sao mặc định chỉ chép con trỏ, nên hai đối tượng trỏ cùng một chỗ ở heap; khi cả hai chết, cùng một chỗ bị `delete` hai lần, là hành vi không xác định. Copy không đặt con trỏ về `nullptr`, và cũng không chép vùng heap (chính vì thế mới có chuyện dùng chung). Hàm hủy của bản sao vẫn chạy bình thường, và việc nó chạy chính là nguồn của lần `delete` thứ hai.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Ví dụ nào sau đây trong thư viện chuẩn là RAII?

- `std::lock_guard`: giữ khóa khi tạo, nhả khóa khi bị hủy
- `std::terminate`: gọi hàm hủy của mọi đối tượng rồi mới dừng
- `malloc`: xin bộ nhớ và tự trả khi con trỏ hết phạm vi
- `throw`: ném lỗi và tự đóng giúp các file đang mở

<p class="giai-thich" markdown>`std::lock_guard` xin khóa trong hàm tạo và nhả trong hàm hủy: đúng khuôn RAII. `std::terminate` là hàm kết thúc chương trình, được gọi ví dụ khi ngoại lệ không bị bắt; nó không phải một đối tượng giữ tài nguyên, và chuẩn không hứa nó chạy hàm hủy giúp bạn. `malloc` chỉ xin bytes và bạn phải tự gọi `free`, không có hàm hủy nào lo. `throw` chỉ là lệnh ném ngoại lệ; việc các đối tượng RAII trên đường đi được hủy là do hàm hủy của chúng, không phải do `throw` tự đóng file.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`, chạy trong `main`). Dòng nào được in ngay sau `tao 2`?

```text
Cay a(1);
{ Cay b(2); }
Cay c(3);
std::cout << "het\n";
```

- `tao 3`: khối nhỏ chỉ kết thúc khi `main` kết thúc
- `huy 1`: `a` ra đời trước nên phải chết trước
- `huy 2`: `b` chết ngay ở `}` nhỏ
- `het`: mọi dòng `tao` phải in hết rồi mới tới `huy`

<p class="giai-thich" markdown>`b` nằm trong khối nhỏ nên chết ngay ở `}` của khối đó, vì vậy `huy 2` đến trước khi `c` kịp ra đời; cả chương trình in `tao 1, tao 2, huy 2, tao 3, het, huy 3, huy 1` (mình đã chạy). Khối nhỏ không đợi đến hết `main`, nên `tao 3` không đến ngay sau `tao 2`. `a` sống tới `}` của `main`, nên `huy 1` ở cuối cùng, sau `huy 3`. Còn `tao` và `huy` không bị tách thành hai nhóm: hàm hủy chạy đúng lúc đối tượng chết, không đợi các dòng `tao` in xong.</p>
</div>

</div>

## 🔑 Tóm tắt

1. RAII là xin tài nguyên trong hàm tạo và trả trong hàm hủy; tài nguyên không chỉ là bộ nhớ mà còn là file, khóa, kết nối, ổ cắm mạng (ví dụ trong chuẩn: `std::ifstream`, `std::lock_guard`).
2. Hàm hủy của biến cục bộ chạy ở cuối khối `{}` chứa nó, theo thứ tự ngược với lúc tạo, kể cả khi `return` sớm; còn `delete` viết tay thì bị nhảy qua.
3. Khi `throw` được ném và bị `catch` ở ngoài bắt, chương trình tháo ngăn xếp và hủy mọi đối tượng cục bộ đã ra đời trên đường đi, trước khi chạy khối `catch`; nếu không ai bắt thì gọi `std::terminate` và việc hủy là do cài đặt quyết định, còn hàm hủy thì không nên ném ngoại lệ.
4. Lớp RAII giữ con trỏ thô rất nguy hiểm khi copy: hai đối tượng cùng giữ một con trỏ nên cùng `delete` một chỗ (cách sửa ở Bài 11).
5. So với `defer` của Go: `defer` phải nhớ viết ở từng nơi và chạy ở cuối hàm, còn RAII gắn vào kiểu dữ liệu (không cần nhớ viết ở từng nơi) và chạy ở cuối khối; đừng gọi `delete` tay, để một đối tượng lo, và `std::unique_ptr` (Bài 09) là bản làm sẵn cho bộ nhớ.
