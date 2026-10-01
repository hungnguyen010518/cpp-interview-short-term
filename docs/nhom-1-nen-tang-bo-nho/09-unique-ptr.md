# Bài 09 — `std::unique_ptr`: một chủ duy nhất cho mỗi cây

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::make_unique`, `*p`, `p->`, `get()`, `reset()`, `release()` và hiểu "quyền sở hữu duy nhất": chỉ một `unique_ptr` giữ một đối tượng, nên hàm hủy chạy đúng một lần.
    - Biết vì sao `std::unique_ptr<Cay> b = a;` là lỗi biên dịch, và trao quyền bằng `std::move` thì `a` thành `nullptr`.
    - Truyền `unique_ptr` vào và ra khỏi hàm đúng cách, và biết khi nào chỉ cần con trỏ thô hoặc tham chiếu để "nhìn".

**Bạn cần biết trước:** [Bài 03](03-con-tro-co-ban.md) (`*p`, `->`, `nullptr`), [Bài 06](06-tham-chieu-const.md) (`const T&`), [Bài 07](07-new-delete.md) (`new`/`delete`, double free) và [Bài 08](08-raii.md) (RAII, lớp `Hop`, ngoại lệ).

## 🧠 Câu chuyện mở đầu

Trong kho đồ của trường, mỗi món đồ nằm trong một **tủ riêng** có một chiếc **chìa khóa duy nhất**. Chỉ một người cầm chìa, và người đó chịu trách nhiệm đóng tủ, dọn sạch khi xong việc. Muốn người khác dùng tủ thì phải **trao tay** chiếc chìa: từ lúc đó người cũ hết chìa, người mới là chủ. Khi người cầm chìa đi khỏi (ra khỏi khối `{}` của họ), tủ tự đóng và được dọn.

`std::unique_ptr` là chiếc chìa đó. Ở [Bài 08](08-raii.md) bạn thấy lớp `Hop` tự `delete` trong hàm hủy nhưng bị nguy hiểm khi copy, vì copy làm **hai** người cầm chìa. `unique_ptr` giải quyết bằng cách **không cho copy**: chìa chỉ được trao, không được đúc thêm (miễn là bạn không tự đưa cùng một con trỏ thô cho hai `unique_ptr`, hay `delete` kết quả của `get()`).

!!! info "Bạn biết Go?"
    Go không có khái niệm "quyền sở hữu": bộ nhớ được dọn bởi GC khi không còn ai dùng, nên với bộ nhớ bạn không cần biết "ai chịu trách nhiệm dọn"; với tài nguyên khác như file bạn vẫn tự `defer Close()`. C++ không có GC, nên phải có một chỗ ghi rõ **ai** dọn. `unique_ptr` là cách C++ viết điều đó ngay trong kiểu dữ liệu: biến nào là `unique_ptr` thì biến đó là chủ.

!!! info "Chỗ nào ví dụ chiếc chìa không còn đúng?"
    "Chìa" thật là đồ vật; ở đây nó là địa chỉ cây trong `unique_ptr`, và "trao tay" là chép địa chỉ sang chỗ khác rồi đặt chỗ cũ về `nullptr`.

## 📖 Giải thích

### 1. Nối Bài 08: tự viết một bản rất ngắn

[Bài 08](08-raii.md) kết thúc với ý: đừng gọi `delete` tay, để một đối tượng lo. Ta thử viết đối tượng đó cho `Cay` (cây, vẫn in `tao`/`huy` như trước), tên `UniquePtrMini`. Nó **không** tự `new`: nó nhận một con trỏ thô đã trỏ tới cây và từ đó là chủ của cây.

Hai hàm lạ trong code là `operator*` và `operator->`. Trong C++, bạn đặt tên một hàm là `operator*` thì viết `*m` sẽ gọi hàm đó; `operator->` thì `m->cao` gọi hàm đó. Nhờ vậy một lớp tự làm **"giả vờ là con trỏ"**: dùng `*m` và `m->` như với con trỏ thật, dù `m` là một đối tượng. (`Cay&` ở kiểu trả về là tham chiếu, [Bài 06](06-tham-chieu-const.md): trả về chính cây chứ không phải bản sao.)

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

struct UniquePtrMini {
    Cay* p;
    UniquePtrMini(Cay* raw) {
        p = raw;                       // (1)
    }
    ~UniquePtrMini() {
        delete p;                      // (2)
    }
    Cay& operator*() {
        return *p;                     // (3)
    }
    Cay* operator->() {
        return p;                      // (4)
    }
};

int main() {
    UniquePtrMini m(new Cay(5));       // (5)
    std::cout << "cao = " << (*m).cao << "\n";   // (6)
    std::cout << "cao = " << m->cao << "\n";     // (7)
    std::cout << "het main\n";
    return 0;
}                                      // (8)
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (5) | `new Cay(5)` chạy trước: xin heap, in `tao 5`. Rồi hàm tạo (1) của `m` ghi địa chỉ đó vào `m.p` | stack: `m.p` = 0x9000; heap: 0x9000 chứa `Cay` cao 5 (địa chỉ minh họa — máy bạn sẽ in số khác) |
| (6) | `*m` gọi `operator*` (3), trả về cây; `.cao` đọc 5, in `cao = 5` | không đổi |
| (7) | `m->cao` gọi `operator->` (4), trả về `p`, rồi lấy `cao`; in `cao = 5` | không đổi |
| in `het main` | Hết việc | không đổi |
| (8) `}` | `m` chết, hàm hủy (2) chạy `delete p`: in `huy 5` | heap: đã trả |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`):

```text
tao 5
cao = 5
cao = 5
het main
huy 5
```

Không có `delete` nào ở `main`, vậy mà `huy 5` vẫn in: đây chính là RAII của [Bài 08](08-raii.md), áp cho bộ nhớ heap. Bản mini này chỉ để hiểu ý tưởng. Bản **thật** khác ở ba điểm: dùng được cho **mọi kiểu** (không chỉ `Cay`), **xóa** việc copy, và **hỗ trợ trao tay** (mục 4). Nếu để bản mini bị copy thì nó có đúng cái bẫy double free của Bài 08, mục 6.

### 2. Dùng bản thật: `std::unique_ptr` và `std::make_unique`

Bản thật nằm trong thư viện chuẩn, muốn dùng thì `#include <memory>`. Kiểu của nó viết là `std::unique_ptr<Cay>`: cặp `< >` cho biết nó giữ **loại đối tượng nào**. Đây là một **khuôn mẫu (template)**: một kiểu có tham số là kiểu khác, giống `Stack[int]` của generics trong Go. Mình chỉ cần bạn đọc được `unique_ptr<Cay>` là "con trỏ-chủ của một `Cay`".

Để tạo cây và đưa vào `unique_ptr` cùng lúc, ta gọi `std::make_unique<Cay>(5)`. Phần trong `( )` được chuyển cho hàm tạo của `Cay`, nên nó giống `new Cay(5)` nhưng kết quả đã được bọc sẵn. `make_unique` có từ **C++14**; khóa này biên dịch bằng `-std=c++17` nên dùng được.

Ta thử mọi thao tác thường dùng trong một chương trình. Chữ `auto` ở các ví dụ sau nghĩa là "trình biên dịch tự đoán kiểu": `auto p = std::make_unique<Cay>(5);` chính là `std::unique_ptr<Cay> p = ...`.

```cpp
#include <iostream>
#include <memory>

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

int main() {
    std::unique_ptr<Cay> p = std::make_unique<Cay>(5);   // (1)
    std::cout << "cao = " << (*p).cao << "\n";            // (2)
    std::cout << "cao = " << p->cao << "\n";              // (3)

    Cay* nhin = p.get();                                  // (4)
    std::cout << "nhin thay " << nhin->cao << "\n";

    if (p) {                                              // (5)
        std::cout << "p dang giu cay\n";
    }

    p.reset();                                            // (6)
    if (!p) {
        std::cout << "p rong\n";
    }

    p = std::make_unique<Cay>(7);                         // (7)
    Cay* tho = p.release();                               // (8)
    if (!p) {
        std::cout << "p rong sau release\n";
    }
    std::cout << "tho van tro toi cay cao " << tho->cao << "\n";
    delete tho;                                           // (9)
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Tạo cây cao 5 và `p` giữ nó; in `tao 5` | stack: `p` = 0x9000; heap: cây 5 (địa chỉ minh họa) |
| (2), (3) | `*p` và `p->` dùng như con trỏ thật; in `cao = 5` hai lần | không đổi |
| (4) | `get()` trả về địa chỉ thô 0x9000 cho `nhin`; `p` **vẫn là chủ**. In `nhin thay 5` | stack: `p` và `nhin` cùng 0x9000 |
| (5) | `if (p)` đúng khi `p` đang giữ cây; in `p dang giu cay` | không đổi |
| (6) | `reset()` **xóa cây** đang giữ: in `huy 5`; `p` thành `nullptr` | heap: đã trả; `nhin` thành con trỏ treo (không dùng nữa) |
| in `p rong` | `!p` nghĩa là "p đang rỗng": đúng | không đổi |
| (7) | Tạo cây cao 7 (in `tao 7`) và đưa vào `p`. Dòng này gán vào `p` kết quả vừa tạo; [Bài 12](12-move-semantics.md) giải thích vì sao được phép | stack: `p` = 0xA000; heap: cây 7 |
| (8) | `release()` **bỏ quyền sở hữu** và trả địa chỉ thô cho `tho`; **không xóa gì**. `p` thành `nullptr` | `p` rỗng; `tho` = 0xA000 |
| in 2 dòng | `p rong sau release`, rồi `tho` vẫn đọc được cây 7 | không đổi |
| (9) | Giờ ta là chủ: phải tự `delete tho`; in `huy 7` | heap: đã trả |

**Kết quả khi chạy:**

```text
tao 5
cao = 5
cao = 5
nhin thay 5
p dang giu cay
huy 5
p rong
tao 7
p rong sau release
tho van tro toi cay cao 7
huy 7
het main
```

Ba hàm hay bị lẫn, nên đặt cạnh nhau:

| Hàm | `p` sau đó | Cây có bị xóa không | Bạn nhận được |
|---|---|---|---|
| `p.get()` | **vẫn là chủ** | không | địa chỉ thô để **nhìn**; không bao giờ `delete` nó |
| `p.release()` | rỗng (`nullptr`) | **không** | địa chỉ thô; **bạn** thành chủ và phải lo xóa |
| `p.reset()` | rỗng (`nullptr`) | **có**, ngay lúc gọi | không có gì |

**Thử thay đổi 1: bỏ dòng (9) `delete tho;`.** Mình đã chạy với AddressSanitizer (`-fsanitize=address`, [Bài 07](07-new-delete.md)): chương trình in `tao 7` ... `het main` mà **không có `huy 7`**, và LeakSanitizer báo `4 byte(s) leaked in 1 allocation(s)`. Đúng như bảng: sau `release()` cây là việc của bạn.

**Thử thay đổi 2: thay (6) bằng `p.reset(new Cay(2));`** (`reset` có thể nhận con trỏ thô mới và giữ nó). Mình đã chạy với `p` đang giữ cây cao 1 (và thêm một dòng in `p->cao`): output `tao 1`, `tao 2`, `huy 1`, rồi `p giu cay 2` và cuối chương trình `huy 2`. Cây mới ra đời trước, cây cũ bị xóa ngay sau đó.

### 3. Không copy được

Bây giờ thử copy một `unique_ptr`, đúng thứ gây double free ở [Bài 08](08-raii.md):

```cpp
// bo-qua-kiem-tra
// (struct Cay và các #include như các ví dụ trên)
int main() {
    std::unique_ptr<Cay> a = std::make_unique<Cay>(5);
    auto b = a;                                  // (1)
    return 0;
}
```

Mình đã biên dịch: **không ra được chương trình**, g++ báo lỗi (rút gọn):

```text
error: use of deleted function 'std::unique_ptr<_Tp, _Dp>::unique_ptr(const std::unique_ptr<_Tp, _Dp>&) [with _Tp = Cay; ...]'
   17 |     auto b = a;
note: declared here
  468 |       unique_ptr(const unique_ptr&) = delete;
```

Cách đọc: `auto b = a;` cần **hàm tạo sao chép** ([Bài 06](06-tham-chieu-const.md)) của `unique_ptr`. Thư viện chuẩn viết hàm đó kèm `= delete`, nghĩa là "hàm này bị xóa": trình biên dịch từ chối mọi dòng gọi tới nó. Vì sao bị xóa? Nếu `a` và `b` cùng giữ một cây thì hai hàm hủy cùng `delete` một chỗ: đúng cái double free ở [Bài 08](08-raii.md). Thay vì để lỗi đó xảy ra lúc chạy, C++ chặn nó ngay lúc **biên dịch**.

Đây là ý nghĩa của "sở hữu duy nhất": tại mọi thời điểm, nhiều lắm một `unique_ptr` giữ một cây, nên cây bị xóa đúng một lần (miễn là bạn không tự đưa cùng một con trỏ thô cho hai `unique_ptr`, hay `delete` kết quả của `get()`).

!!! question "Hỏi nhanh: cấm copy thì làm sao đưa cây cho người khác?"
    Bằng cách **trao tay**: người cũ buông, người mới nhận. Đó là mục sau.

### 4. Trao tay bằng `std::move`

Muốn chuyển quyền sở hữu từ `a` sang `b`, ta viết `auto b = std::move(a);`. `std::move` (cần `#include <utility>`) không tự di chuyển gì. Nó chỉ là **lời nói**: "tôi đồng ý trao `a` đi". Việc trao thật do `unique_ptr` làm: chép địa chỉ cây sang `b` rồi đặt `a` về `nullptr`. Ý nghĩa sâu hơn của `std::move` nằm ở [Bài 12](12-move-semantics.md); bây giờ bạn chỉ cần dùng được.

```cpp
#include <iostream>
#include <memory>
#include <utility>

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

int main() {
    auto a = std::make_unique<Cay>(5);                // (1)
    std::cout << "truoc move\n";
    auto b = std::move(a);                            // (2)
    if (a == nullptr) {
        std::cout << "a == nullptr\n";                // (3)
    }
    std::cout << "b giu cay cao " << b->cao << "\n";
    std::cout << "het main\n";
    return 0;
}                                                     // (4)
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Tạo cây cao 5, `a` giữ; in `tao 5` | stack: `a` = 0x9000; heap: cây 5 (địa chỉ minh họa) |
| in `truoc move` | | không đổi |
| (2) | Trao tay: `b` nhận địa chỉ 0x9000, `a` thành `nullptr`. **Không có cây nào được tạo hay xóa**, nên không in gì | `a` = `nullptr`; `b` = 0x9000 |
| (3) | `a == nullptr` đúng; in `a == nullptr` | không đổi |
| in 2 dòng | `b->cao` đọc cây 5; rồi `het main` | không đổi |
| (4) `}` | Biến chết theo thứ tự ngược với lúc tạo: `b` chết trước, hàm hủy xóa cây, in `huy 5`. Rồi `a` chết: nó rỗng nên không xóa gì | heap: đã trả |

**Kết quả khi chạy:**

```text
tao 5
truoc move
a == nullptr
b giu cay cao 5
het main
huy 5
```

Có đúng **một** `tao 5` và **một** `huy 5`: cây đổi chủ chứ không được nhân đôi. Với `unique_ptr`, chuẩn **bảo đảm** nguồn sau khi bị move là `nullptr`, nên viết `a == nullptr` là hợp lệ.

### 5. Truyền `unique_ptr` vào và ra khỏi hàm

Câu hỏi cần tự hỏi khi viết hàm: **hàm này chỉ dùng cây, hay phải trở thành chủ của nó?** Hai tình huống có hai cách viết khác nhau, và tình huống thứ ba là hàm tạo ra cây rồi đưa cho nơi gọi.

```cpp
#include <iostream>
#include <memory>
#include <utility>

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

void nhin(const Cay& c) {                             // (1)
    std::cout << "nhin: cao " << c.cao << "\n";
}

void nhinCon(Cay* c) {                                // (2)
    std::cout << "nhinCon: cao " << c->cao << "\n";
}

void nhan(std::unique_ptr<Cay> c) {                   // (3)
    std::cout << "nhan: cao " << c->cao << "\n";
}                                                     // (4)

std::unique_ptr<Cay> trongMoi(int cao) {
    return std::make_unique<Cay>(cao);                // (5)
}

int main() {
    auto p = std::make_unique<Cay>(5);
    nhin(*p);                                         // (6)
    nhinCon(p.get());                                 // (7)
    std::cout << "p con giu cay: " << (p != nullptr) << "\n";
    nhan(std::move(p));                               // (8)
    std::cout << "sau nhan, p con giu cay: " << (p != nullptr) << "\n";
    auto q = trongMoi(9);                             // (9)
    std::cout << "q giu cay cao " << q->cao << "\n";
    std::cout << "het main\n";
    return 0;
}                                                     // (10)
```

(`p != nullptr` cho đúng/sai; khi in ra, `cout` hiện đúng là `1`, sai là `0`.)

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| đầu `main` | `p` giữ cây 5, in `tao 5` | `p` = 0x9000 (địa chỉ minh họa) |
| (6) | `*p` là chính cây; hàm (1) nhận nó qua `const Cay&` (xem, không sao chép, không sửa). In `nhin: cao 5` | `p` vẫn giữ |
| (7) | `p.get()` đưa địa chỉ thô cho hàm (2). In `nhinCon: cao 5`, rồi `p con giu cay: 1` | `p` vẫn giữ |
| (8) | `std::move(p)`: tham số `c` của (3) nhận quyền sở hữu, `p` thành `nullptr`. In `nhan: cao 5` | `c` = 0x9000; `p` = `nullptr` |
| (4) `}` của `nhan` | `c` chết, **hàm hủy chạy ở đây**: in `huy 5`. Về `main`: `sau nhan, p con giu cay: 0` | heap: đã trả |
| (9) | `trongMoi(9)` tạo cây 9 (in `tao 9`); (5) `return` đưa quyền sở hữu thẳng sang `q`, không in `huy` giữa chừng | `q` = 0xA000 |
| in 2 dòng | `q giu cay cao 9`, `het main` | không đổi |
| (10) `}` của `main` | `q` chết: in `huy 9`. `p` rỗng nên không xóa gì | heap: sạch |

**Kết quả khi chạy:**

```text
tao 5
nhin: cao 5
nhinCon: cao 5
p con giu cay: 1
nhan: cao 5
huy 5
sau nhan, p con giu cay: 0
tao 9
q giu cay cao 9
het main
huy 9
```

Quy tắc rút ra:

| Hàm cần gì | Viết tham số | Nơi gọi viết | Ghi chú |
|---|---|---|---|
| Chỉ **dùng** cây (phổ biến nhất) | `const Cay&` (hoặc `Cay&` nếu cần sửa) | `f(*p)` | Hàm không biết cây được quản lý thế nào, và không quan tâm |
| Dùng cây, **có thể không có cây** | `Cay*` | `f(p.get())` | `nullptr` nghĩa là "không có"; hàm không được `delete` |
| **Trở thành chủ** (lưu lại, hoặc dùng xong rồi hủy nó) | `std::unique_ptr<Cay>` theo giá trị | `f(std::move(p))` | Nhìn tham số là biết: hàm này nhận quyền |
| **Trả cây** về nơi gọi | kiểu trả về `std::unique_ptr<Cay>` | `return std::make_unique<Cay>(...);` | Không cần `std::move` ở `return`: trình biên dịch lo |

!!! warning "Hay nhầm"
    Hàm `nhan` nhận theo giá trị, nhưng nếu nơi gọi viết `nhan(p);` (không có `std::move`) thì đó là **copy**, và bị từ chối. Mình đã thử: g++ báo lại đúng `use of deleted function ... unique_ptr(const unique_ptr&)` ở dòng `nhan(p);`. Chữ `std::move` ở nơi gọi là chỗ bạn viết ra "tôi đồng ý trao".

### 6. Mảng và `vector`

`std::unique_ptr<int[]>` (có `[]` sau kiểu) giữ một **mảng** ở heap và biết dùng `delete[]` ([Bài 07](07-new-delete.md)) khi hủy. Nó có `operator[]` nên viết `m[i]` như mảng thường:

```cpp
#include <iostream>
#include <memory>

int main() {
    // (1) xin mảng 4 int ở heap: số 4 là số phần tử, không phải giá trị
    std::unique_ptr<int[]> m = std::make_unique<int[]>(4);
    for (int i = 0; i < 4; i++) {
        m[i] = (i + 1) * 10;     // (2) ghi 10, 20, 30, 40
    }
    std::cout << "m[0] = " << m[0] << ", m[3] = " << m[3] << "\n";
    return 0;
}                                // (3) m chết: mảng được delete[]
```

```text
m[0] = 10, m[3] = 40
```

Dù vậy, thường nên dùng `std::vector` (kiểu mảng co giãn, đã gặp ở [Bài 02](02-stack-heap-static.md)) thay cho mảng động; mình dạy kỹ ở nhóm STL. `std::vector<std::unique_ptr<Cay>>` (danh sách các chủ cây) cũng dùng được vì chỉ cần trao tay, không cần copy.

### 7. Chi phí và bộ xóa tùy chỉnh

`unique_ptr` gần như không tốn thêm so với con trỏ thô. Mình đã đo `sizeof`: trên máy mình cả `int*` lẫn `std::unique_ptr<int>` đều 8 byte; chuẩn không hứa điều này, nhưng trên các cài đặt phổ biến, với bộ xóa mặc định (là `delete`), hai kiểu cùng cỡ. Việc xóa có thể đổi được bằng **bộ xóa tùy chỉnh (custom deleter)**, ví dụ để `unique_ptr` giữ file mở bằng `fopen` và gọi `fclose`; bài này chỉ nêu tên.

### 8. Quy tắc chọn

Mặc định, **dùng `unique_ptr`** cho đối tượng ở heap có một chủ rõ ràng. Con trỏ thô và tham chiếu vẫn dùng, nhưng chỉ để **nhìn** (không sở hữu, không `delete`). Với trường hợp nhiều chủ cùng dùng một đối tượng, có `std::shared_ptr` ([Bài 10](10-shared-ptr-weak-ptr.md)).

## 💻 Ví dụ code

### Ví dụ 1: mọi đường thoát đều xóa cây (nối Bài 08)

Ở [Bài 08](08-raii.md), hàm `xuLy` có `return` sớm hay `throw` thì `delete` tay bị nhảy qua. Dưới đây là hàm đó với `unique_ptr`, ba lần gọi: bình thường, `return` sớm và `throw`.

```cpp
#include <iostream>
#include <memory>

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
    auto p = std::make_unique<Cay>(cao);          // (1)
    if (cao < 0) {
        std::cout << "cao am, thoat som\n";
        return;                                   // (2)
    }
    if (cao == 0) {
        throw cao;                                // (3)
    }
    std::cout << "xu ly cay cao " << p->cao << "\n";
}                                                 // (4)

int main() {
    try {
        xuLy(5);
        xuLy(-1);
        xuLy(0);
        std::cout << "khong in dong nay\n";
    } catch (int ma) {
        std::cout << "bat duoc loi " << ma << "\n";
    }
    std::cout << "xong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `xuLy(5)`, (1) | `p` giữ cây 5; in `tao 5` | heap: cây 5 |
| in `xu ly cay cao 5` | Không vào hai `if`; dùng cây qua `p->cao` | không đổi |
| (4) `}` | `p` chết, cây bị xóa; in `huy 5` | heap: sạch |
| `xuLy(-1)`, (1) | in `tao -1` | heap: cây -1 |
| (2) `return;` | In `cao am, thoat som`; thoát hàm, `p` chết: in `huy -1` | heap: sạch |
| `xuLy(0)`, (1) | in `tao 0` | heap: cây 0 |
| (3) `throw cao;` | Ném 0, `xuLy` bị cắt ngang; tháo ngăn xếp làm `p` chết: in `huy 0`. Dòng `khong in dong nay` không chạy | heap: sạch |
| `catch` | in `bat duoc loi 0`, rồi `xong` | |

**Kết quả khi chạy:**

```text
tao 5
xu ly cay cao 5
huy 5
tao -1
cao am, thoat som
huy -1
tao 0
huy 0
bat duoc loi 0
xong
```

Cả ba lần đều có đúng một `tao` và một `huy`, không có dòng `delete` nào. Mình đã chạy thêm với AddressSanitizer: không báo gì (nhưng im lặng không chứng minh là sạch; ta còn thấy đủ cặp `tao`/`huy`).

**Thử thay đổi: đổi dòng (1) thành `Cay* p = new Cay(cao);` và thêm `delete p;` ở cuối hàm (thay cho dòng (4)).** Đây là hàm thủ công của [Bài 08](08-raii.md). Mình đã chạy: `xuLy(5)` đủ `tao 5`/`huy 5`, nhưng `xuLy(-1)` chỉ có `tao -1` (không có `huy -1`) và `xuLy(0)` chỉ có `tao 0` rồi `bat duoc loi 0`, vì `return` và `throw` đều nhảy qua `delete p;`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::unique_ptr` là gì, khác con trỏ thô thế nào?"
    `unique_ptr` là con trỏ thông minh (smart pointer) áp dụng RAII cho bộ nhớ heap: nó **sở hữu duy nhất** đối tượng mà nó giữ và tự `delete` đối tượng đó trong hàm hủy. Con trỏ thô chỉ là một địa chỉ, không nói ai chịu trách nhiệm xóa, nên người viết phải tự nhớ `delete` đúng một lần trên mọi đường thoát. `unique_ptr` không thể copy, chỉ trao tay (move), và trên các cài đặt phổ biến thì cùng cỡ với con trỏ thô khi dùng bộ xóa mặc định.

??? question "Vì sao `unique_ptr` không copy được?"
    Vì hàm tạo sao chép của nó bị xóa (`= delete`), nên `auto b = a;` là lỗi biên dịch. Nếu copy được thì hai `unique_ptr` cùng giữ một đối tượng và cùng `delete` nó khi chết, tức là giải phóng hai lần (hành vi không xác định). C++ chọn chặn lỗi đó lúc biên dịch thay vì để nó xảy ra lúc chạy. Muốn chuyển đối tượng cho chỗ khác thì trao tay bằng `std::move`.

??? question "`std::move` làm gì với `unique_ptr`?"
    Bản thân `std::move` chỉ là lời nói "tôi đồng ý trao đi" (nó cho phép dùng thao tác di chuyển), còn việc trao do `unique_ptr` làm: chép địa chỉ đối tượng sang `unique_ptr` đích và đặt nguồn về `nullptr`. Chuẩn bảo đảm nguồn là `nullptr` sau đó, nên đừng giải tham chiếu nó. Chi tiết về `std::move` và rvalue nằm ở [Bài 12](12-move-semantics.md).

??? question "`get()`, `release()` và `reset()` khác nhau thế nào?"
    `get()` trả địa chỉ thô để nhìn và `unique_ptr` vẫn là chủ, nên không được `delete` địa chỉ đó. `release()` bỏ quyền sở hữu và trả địa chỉ thô nhưng **không xóa**: từ đó bạn phải tự lo xóa, nếu không là rò rỉ. `reset()` **xóa** đối tượng đang giữ (và có thể nhận một con trỏ mới để giữ tiếp).

??? question "Khi nào truyền `unique_ptr` theo giá trị, khi nào dùng con trỏ thô hoặc tham chiếu?"
    Hàm chỉ dùng đối tượng thì nhận `const T&` (hoặc `T&`, hoặc `T*` nếu cho phép "không có"), nơi gọi truyền `*p` hay `p.get()` và vẫn là chủ. Hàm cần trở thành chủ (lưu lại, hoặc hủy khi xong) thì nhận `std::unique_ptr<T>` theo giá trị và nơi gọi viết `std::move(p)`, nên nhìn chữ ký là biết quyền sở hữu được trao. Trả `unique_ptr` từ hàm thì chỉ cần `return` bình thường, không cần `std::move`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `delete` địa chỉ lấy từ `get()`"
    Cây vẫn thuộc `unique_ptr`, nên khi nó chết lại xóa lần nữa: double free ([Bài 07](07-new-delete.md)). Muốn lấy quyền thì dùng `release()`, và khi đó đừng để `unique_ptr` giữ nữa.

!!! warning "Lỗi 2: Gọi `release()` rồi bỏ đó"
    `release()` không xóa, nên cây bị rò rỉ. Muốn xóa thì dùng `reset()`, hoặc để `unique_ptr` chết.

!!! warning "Lỗi 3: Dùng `unique_ptr` sau khi đã `std::move` nó đi"
    Nguồn là `nullptr` sau khi trao, nên `*a` hay `a->cao` là hành vi không xác định. Kiểm tra bằng `if (a)` nếu chưa chắc.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="09" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** "Quyền sở hữu duy nhất" của `unique_ptr` nghĩa là gì?

- Cây có đúng một địa chỉ ở heap nên con trỏ thô nào trỏ vào cũng là chủ
- Nhiều `unique_ptr` cùng giữ một cây, nhưng chỉ cái đầu tiên được phép xóa
- Mỗi lúc chỉ một `unique_ptr` giữ cây, nên chỉ riêng nó chịu trách nhiệm xóa
- Cây chỉ được tạo một lần trong cả chương trình và sống đến lúc dừng hẳn

<p class="giai-thich" markdown>Mỗi cây có đúng một chủ tại mỗi lúc, và chủ đó xóa cây khi chết, nên hàm hủy chạy đúng một lần. Con trỏ thô nhìn vào cây không thành chủ, vì chỉ `unique_ptr` mới xóa. Cho nhiều `unique_ptr` cùng giữ là điều bị cấm (không copy được), chứ không phải "cái đầu tiên xóa". Còn số lần tạo cây không bị giới hạn: bạn tạo bao nhiêu cây cũng được, mỗi cây có một chủ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Vì sao `auto b = a;` (với `a` là `unique_ptr<Cay>`) là lỗi biên dịch?

- Hàm tạo sao chép bị xóa, vì copy sẽ tạo ra hai chủ cho một cây
- `auto` không đoán được kiểu `unique_ptr` nên phải ghi kiểu rõ ra
- Copy sẽ chép cả cây ở heap, quá tốn nên C++ cấm hẳn từ trước
- `a` còn giữ cây nên chưa được đụng tới trước khi hết `main`

<p class="giai-thich" markdown>Hàm tạo sao chép của `unique_ptr` được viết là `= delete`, vì cho copy thì có hai chủ và cây bị xóa hai lần. `auto` đoán kiểu `unique_ptr` bình thường (`auto p = std::make_unique<Cay>(5);` chạy tốt). Copy mặc định của một con trỏ chỉ chép địa chỉ chứ không chép cây, nên lý do không phải chuyện tốn bộ nhớ. Còn việc `a` đang giữ cây không cản gì: trao tay bằng `std::move` ngay lúc đó vẫn được.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). `cout` in `1` cho đúng và `0` cho sai. Dòng cuối in ra gì?

```text
auto p = std::make_unique<Cay>(1);
auto c = std::move(p);
std::cout << (p == nullptr) << (c == nullptr) << "\n";
```

- `11`: cả hai đều rỗng vì cây đã bị xóa
- `10`: `p` rỗng sau khi trao, `c` đang giữ cây
- `00`: cả hai cùng giữ cây vì `std::move` chỉ đổi tên
- `01`: `p` còn giữ cây, `c` mới chỉ nhận nhưng chưa dùng

<p class="giai-thich" markdown>Sau `std::move`, `c` nhận cây còn `p` thành `nullptr` (chuẩn bảo đảm cho `unique_ptr`): `p == nullptr` đúng nên in `1`, `c == nullptr` sai nên in `0`. Mình đã chạy ra `10`. Cây không bị xóa lúc trao, chỉ đổi chủ (hàm hủy chạy khi `c` chết), nên `11` sai. `std::move` không sao chép gì nên hai biến không thể cùng giữ cây, và nguồn đã bị đặt về `nullptr` ngay lúc trao nên `p` không thể còn giữ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). Chương trình in ra gì?

```text
int main() {
    auto p = std::make_unique<Cay>(1);
    Cay* r = p.release();
    std::cout << "xong\n";
}
```

- `tao 1, xong, huy 1`
- `tao 1, huy 1, xong`
- `tao 1, huy 1`
- `tao 1, xong`

<p class="giai-thich" markdown>`release()` bỏ quyền sở hữu mà không xóa, nên khi `p` chết nó rỗng và không có gì để `delete`. Không ai gọi `delete r`, nên không có `huy 1` và cây bị rò rỉ; mình đã chạy ra `tao 1, xong`. Dãy có `huy 1` ở cuối nhầm `release()` với `reset()` hoặc tưởng `p` vẫn xóa lúc chết. Dãy `huy 1` trước `xong` nhầm `release()` thành lời gọi xóa ngay.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). Chương trình in ra theo thứ tự nào?

```text
void nhan(std::unique_ptr<Cay> c) { std::cout << "trong nhan\n"; }
int main() {
    auto p = std::make_unique<Cay>(1);
    nhan(std::move(p));
    std::cout << "xong\n";
}
```

- `tao 1, trong nhan, xong, huy 1`
- `tao 1, huy 1, trong nhan, xong`
- `tao 1, trong nhan, huy 1, xong`
- `tao 1, trong nhan, huy 1, huy 1, xong`

<p class="giai-thich" markdown>Tham số `c` là chủ mới của cây, và nó chết ở `}` của `nhan`, nên `huy 1` in ngay sau `trong nhan` và trước `xong`; mình đã chạy ra đúng dãy này. Dãy để `huy 1` cuối cùng nhầm rằng cây vẫn thuộc `p` ở `main`, nhưng `p` đã rỗng. Dãy `huy 1` trước `trong nhan` quên rằng hàm chạy trọn thân rồi `c` mới chết. Dãy có hai `huy 1` đếm nhầm hai chủ: `p` đã `nullptr` nên chỉ `c` xóa.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Hàm có tham số `const Cay&` thể hiện điều gì?

- Hàm sẽ xóa cây khi chạy xong, nên nơi gọi phải truyền địa chỉ thô
- Hàm nhận quyền sở hữu cây từ nơi gọi và lo việc xóa nó sau đó
- Hàm được sửa cây, rồi giữ lại một bản sao để dùng ở lần gọi sau
- Hàm chỉ nhìn cây: không sở hữu, không sửa, và không sao chép cây

<p class="giai-thich" markdown>`const Cay&` là tham chiếu hằng ([Bài 06](06-tham-chieu-const.md)): xem được cây, nhưng không sửa, không copy và không xóa, nên chủ của cây vẫn là nơi gọi. Muốn nhận quyền sở hữu thì tham số phải là `std::unique_ptr<Cay>` theo giá trị, không phải tham chiếu hằng. `const` cấm sửa nên cũng không thể "sửa rồi giữ bản sao". Còn xóa cây là việc của chủ, không phải của hàm chỉ nhìn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** `std::make_unique<Cay>(5)` hơn `new Cay(5)` ở điểm nào?

- Tạo cây rồi bọc vào `unique_ptr` ngay trong một bước, không còn `new` trần
- Cây được tạo ở stack thay vì heap, nên nhanh hơn và khỏi phải xóa
- Cho phép copy `unique_ptr` đó thoải mái vì cây đã được bọc sẵn
- Cây được dọn bởi GC giống Go khi không còn biến nào trỏ tới nó

<p class="giai-thich" markdown>`make_unique` xin cây và đưa nó vào `unique_ptr` trong một bước, nên cây có chủ ngay từ lúc ra đời và bạn không viết `new` ở code dùng. Cây vẫn nằm ở heap, không phải stack. Việc bọc không làm `unique_ptr` copy được: nó vẫn chỉ trao tay. C++ không có GC; cây được dọn vì hàm hủy của `unique_ptr` chạy, chứ không vì có bộ dọn ngầm.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Đọc đoạn code sau. Lỗi nằm ở đâu?

```text
auto p = std::make_unique<Cay>(1);
Cay* r = p.get();
delete r;
```

- `get()` đặt `p` về `nullptr`, nên `delete r` xóa nhầm một cây khác
- `delete r` xóa cây, rồi `p` chết lại xóa lần nữa: double free
- Không có lỗi, vì `get()` đã trao quyền sở hữu cho `r`
- Rò rỉ: `delete r` chỉ trả con trỏ `r`, chứ không trả cây ở heap

<p class="giai-thich" markdown>`get()` chỉ cho địa chỉ để nhìn, `p` vẫn là chủ. `delete r` xóa cây, và khi `p` chết hàm hủy của nó xóa chỗ đó lần nữa: giải phóng hai lần, hành vi không xác định (mình không chạy đoạn này). `get()` không đổi `p` thành `nullptr`; đó là việc của `release()` và `reset()`. Hàm trao quyền sở hữu cho con trỏ thô là `release()`, không phải `get()`. Còn `delete r` xóa cây mà `r` trỏ tới, không phải riêng con trỏ `r`, nên không gây rò rỉ.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::unique_ptr<T>` (trong `<memory>`) là RAII cho bộ nhớ heap: nó là chủ duy nhất của đối tượng và `delete` đối tượng đó trong hàm hủy; tạo bằng `std::make_unique<T>(...)` (C++14), dùng `*p`, `p->` như con trỏ thật nhờ `operator*`/`operator->`.
2. `unique_ptr` không copy được (hàm tạo sao chép bị xóa nên `auto b = a;` là lỗi biên dịch), vì copy sẽ tạo hai chủ và double free; chuyển quyền bằng `auto b = std::move(a);` thì `a` thành `nullptr` (chuẩn bảo đảm), còn chi tiết `std::move` ở [Bài 12](12-move-semantics.md).
3. `get()` trả địa chỉ thô để nhìn và `p` vẫn là chủ (không `delete` nó); `release()` bỏ quyền sở hữu và trả địa chỉ thô mà không xóa (phải tự xóa); `reset()` xóa cây đang giữ.
4. Hàm chỉ dùng cây nhận `const T&`/`T&`/`T*`; hàm cần sở hữu nhận `std::unique_ptr<T>` theo giá trị và nơi gọi viết `std::move(p)`; trả `unique_ptr` từ hàm không cần `std::move`; mảng dùng `unique_ptr<T[]>` nhưng `std::vector` thường tốt hơn.
5. Chi phí gần như bằng con trỏ thô (trên cài đặt phổ biến, với bộ xóa mặc định; chuẩn không hứa), bộ xóa tùy chỉnh chỉ cần biết tên; so với Go, `unique_ptr` là cách C++ ghi "ai chịu trách nhiệm dọn", và quy tắc là mặc định dùng `unique_ptr`, còn con trỏ thô và tham chiếu chỉ để nhìn.
