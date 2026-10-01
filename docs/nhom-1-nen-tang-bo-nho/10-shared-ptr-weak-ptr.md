# Bài 10 — `std::shared_ptr`, `std::weak_ptr` và cách chọn smart pointer

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dùng `std::make_shared`, đọc `use_count()` và theo dõi bộ đếm tham chiếu từng bước: copy thì +1, buông thì −1, về 0 thì hàm hủy chạy.
    - Nhận ra **vòng tham chiếu** (hai đối tượng giữ `shared_ptr` của nhau nên không bao giờ bị hủy) và phá nó bằng `std::weak_ptr`; dùng `lock()` và `expired()`.
    - Chọn đúng loại con trỏ cho từng tình huống bằng một bảng ngắn, và biết `shared_ptr` có cái giá của nó.

**Bạn cần biết trước:** [Bài 08](08-raii.md) (RAII, hàm hủy) và [Bài 09](09-unique-ptr.md) (`unique_ptr`, `make_unique`, `std::move`, `if (p)`).

## 🧠 Câu chuyện mở đầu

[Bài 09](09-unique-ptr.md) có **một chiếc chìa** cho một tủ trong kho: một chủ, chủ đi thì tủ đóng. Nhưng đôi khi nhiều bạn cùng cần một tủ và **không ai biết ai dùng xong sau cùng**. Ví dụ một bức ảnh mà ba cửa sổ cùng đang hiển thị: cửa sổ nào đóng cuối cùng thì ảnh mới được dọn.

Lúc này ta cho **mỗi bạn một tấm thẻ mở tủ**, và treo ở cửa một **bảng đếm** "đang có mấy người giữ thẻ". Ai nhận thẻ thì đếm +1, ai trả thẻ thì −1. Người cuối cùng trả thẻ làm bảng về 0: tủ đóng và được dọn. Đó là `std::shared_ptr` ("con trỏ chia sẻ").

Còn **người đứng nhìn qua cửa kính** là `std::weak_ptr`: nhìn được xem tủ còn mở không, nhưng không có thẻ nên không giữ tủ mở. ("Tủ" ở đây là một đối tượng nằm trong kho đồ của trường, tức ở heap.) Phép so sánh này không còn đúng ở một chỗ: thẻ thật là đồ vật còn `shared_ptr` là một biến chứa địa chỉ; "bảng đếm" thật ra là các con số nằm ở một vùng heap (mục 2).

!!! info "Bạn biết Go?"
    Go dọn bộ nhớ bằng GC kiểu **đánh dấu và quét** (tracing): GC đi từ các biến đang sống để tìm mọi thứ còn tới được, phần còn lại bị dọn. Vì vậy hai đối tượng trỏ vòng vào nhau mà không ai ngoài trỏ tới thì Go vẫn dọn bình thường. `shared_ptr` của C++ thì **đếm** tham chiếu, không đi tìm, nên một vòng tham chiếu làm bộ đếm không bao giờ về 0 và bị rò rỉ (mục 3).

## 📖 Giải thích

### 1. Vì sao cần chia sẻ, và bộ đếm chạy thế nào

`unique_ptr` chỉ hợp khi có **một** chủ rõ ràng. Khi nhiều nơi cùng dùng một đối tượng và thứ tự "ai xong cuối" không đoán trước được, ta cần `std::shared_ptr<Cay>` (trong `<memory>`, như `unique_ptr`). Tạo bằng `std::make_shared<Cay>(5)`: giống `make_unique`, phần trong `( )` đi vào hàm tạo của `Cay`.

Khác `unique_ptr`, **copy `shared_ptr` là được**: mỗi bản copy là thêm một người giữ thẻ. Hàm `use_count()` cho biết hiện có mấy `shared_ptr` cùng giữ đối tượng. (Nó dùng để học và gỡ lỗi, đừng dựa vào nó để quyết định logic chương trình.) Ta in nó sau từng bước:

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

void dung(std::shared_ptr<Cay> c) {                              // (1)
    std::cout << "trong dung: dem = " << c.use_count() << "\n";  // (2)
}                                                                // (3)

int main() {
    std::shared_ptr<Cay> a = std::make_shared<Cay>(5);           // (4)
    std::cout << "sau tao a: dem = " << a.use_count() << "\n";
    {
        std::shared_ptr<Cay> b = a;                              // (5)
        std::cout << "sau b = a: dem = " << a.use_count() << "\n";
        dung(a);                                                 // (6)
        std::cout << "sau dung: dem = " << a.use_count() << "\n";
    }                                                            // (7)
    std::cout << "ra khoi khoi: dem = " << a.use_count() << "\n";
    a.reset();                                                   // (8)
    std::cout << "sau reset: dem = " << a.use_count() << "\n";
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng** (cột "Đếm" là `use_count()` của cây sau dòng đó)

| Bước | Dòng | Chuyện gì xảy ra | Đếm |
|---|---|---|---|
| 1 | (4) | Tạo cây cao 5, `a` giữ; in `tao 5`, rồi `sau tao a: dem = 1` | 1 |
| 2 | (5) | `b = a` là **copy**: `b` cũng giữ cây này. In `sau b = a: dem = 2` | 2 |
| 3 | (6), (1) | `dung(a)` nhận tham số theo giá trị, tức là copy: `c` là người giữ thứ ba | 3 |
| 4 | (2) | In `trong dung: dem = 3` | 3 |
| 5 | (3) `}` | `c` chết, trả thẻ | 2 |
| 6 | sau (6) | In `sau dung: dem = 2` | 2 |
| 7 | (7) `}` | Hết khối `{ }`: `b` chết, trả thẻ | 1 |
| 8 | sau (7) | In `ra khoi khoi: dem = 1` | 1 |
| 9 | (8) | `reset()` làm `a` buông cây: đếm về **0**, nên hàm hủy chạy, in `huy 5` | 0 |
| 10 | sau (8) | `a` giờ rỗng; `use_count()` của một `shared_ptr` rỗng là 0. In `sau reset: dem = 0`, rồi `het main` | 0 |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`):

```text
tao 5
sau tao a: dem = 1
sau b = a: dem = 2
trong dung: dem = 3
sau dung: dem = 2
ra khoi khoi: dem = 1
huy 5
sau reset: dem = 0
het main
```

Chỉ có **một** `tao 5` và **một** `huy 5`, dù có ba người từng giữ cây. `huy 5` nằm đúng ở lúc bộ đếm về 0, không phải lúc `b` hay `c` chết.

**Thử thay đổi: bỏ dòng (8) `a.reset();` (và dòng in `sau reset`).** Mình đã chạy: các dòng đếm vẫn y hệt, nhưng `huy 5` chuyển xuống **sau** `het main`, vì lúc đó `a` mới chết ở `}` của `main` và trả thẻ cuối cùng.

### 2. Bên trong: khối điều khiển

Bộ đếm phải nằm ở đâu đó mà **mọi** `shared_ptr` cùng thấy. Nếu mỗi `shared_ptr` giữ một số riêng thì chúng không biết số của nhau. Vì vậy có một vùng heap nhỏ gọi là **khối điều khiển (control block)**, chứa các bộ đếm, và mọi `shared_ptr` cùng giữ một cây đều trỏ tới khối này. Khối điều khiển có **hai** bộ đếm: số `shared_ptr` đang giữ cây (đếm "mạnh", cái `use_count()` đọc ra) và số `weak_ptr` đang nhìn (đếm "yếu", mục 4).

`std::make_shared<Cay>(5)` xin heap **một lần** cho cả cây lẫn khối điều khiển (thường là vậy; chuẩn không bắt buộc, đây là cách các cài đặt phổ biến làm). Hình sau là ví dụ khi `a` và `b` cùng giữ cây (địa chỉ minh họa, bạn sẽ thấy khác):

```text
heap, một khối cấp phát bởi make_shared (hình đơn giản hóa, bắt đầu ở 0x9000):
+----------------------------+-----------+
| khối điều khiển            | Cay       |
|   mạnh = 2 (a và b)        |  cao = 5  |
|   yếu  = 0 (đơn giản hóa)   |           |
+----------------------------+-----------+

stack:   a = { 0x9000 (khối điều khiển), 0x9010 (Cay) }
         b = { 0x9000 (khối điều khiển), 0x9010 (Cay) }
```

Mỗi `shared_ptr` thường ghi **hai** địa chỉ: một tới khối điều khiển, một tới cây. Trên máy mình `sizeof(std::shared_ptr<Cay>)` là 16 byte, gấp đôi `unique_ptr` (8 byte); chuẩn không hứa con số này. Khi bộ đếm mạnh về 0, hàm hủy của cây chạy.

Có hai cách tạo, và nên ưu tiên cách đầu: `std::make_shared<Cay>(5)` thường xin heap một lần; còn `std::shared_ptr<Cay>(new Cay(5))` phải `new` cây trước rồi `shared_ptr` mới xin thêm khối điều khiển, nên thường là hai lần xin. Một nhược điểm nhỏ của `make_shared` là vì cây và khối chung một khối, vùng nhớ của cây thường chỉ được trả sau khi `weak_ptr` cuối cùng cũng đã mất (dù hàm hủy của cây vẫn chạy ngay khi bộ đếm mạnh về 0).

!!! warning "Hay nhầm: hai `shared_ptr` tạo từ cùng một con trỏ thô"
    Nếu bạn đưa **cùng một con trỏ thô** cho hai `shared_ptr` riêng (hai lần `shared_ptr<Cay>(raw)`), mỗi cái tự lập **khối điều khiển riêng** và không biết cái kia; cây sẽ bị `delete` hai lần. Mình không chạy ví dụ này vì nó là lỗi nặng (hành vi không xác định). Muốn thêm người giữ thì **copy một `shared_ptr` có sẵn**, đừng quay lại con trỏ thô.

### 3. Vòng tham chiếu: vì sao đối tượng không bao giờ bị hủy

Giả sử cây 1 giữ một `shared_ptr` tới cây 2, và cây 2 giữ một `shared_ptr` tới cây 1 (hai người bạn mỗi người cầm thẻ của người kia). Đó là **vòng tham chiếu (reference cycle)**. Ta thêm một thành viên `ban` vào `Cay` (dòng (1)) và nối vòng:

```cpp
#include <iostream>
#include <memory>

struct Cay {
    int cao;
    std::shared_ptr<Cay> ban;                // (1)
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

int main() {
    {
        auto a = std::make_shared<Cay>(1);
        auto b = std::make_shared<Cay>(2);
        a->ban = b;                          // (2)
        b->ban = a;                          // (3)
        std::cout << "dem a = " << a.use_count() << ", dem b = " << b.use_count() << "\n";
    }                                        // (4)
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng**

| Bước | Dòng | Chuyện gì xảy ra | Đếm cây 1 | Đếm cây 2 |
|---|---|---|---|---|
| 1 | đầu khối | Tạo hai cây; `a` giữ cây 1, `b` giữ cây 2. In `tao 1`, `tao 2` | 1 | 1 |
| 2 | (2) | `a->ban = b`: cây 1 cũng giữ cây 2 | 1 | 2 |
| 3 | (3) | `b->ban = a`: cây 2 cũng giữ cây 1 | 2 | 2 |
| 4 | sau (3) | In `dem a = 2, dem b = 2` | 2 | 2 |
| 5 | (4) `}` | `b` chết trước (biến tạo sau thì chết trước), trả một thẻ của cây 2 | 2 | 1 |
| 6 | (4) `}` | `a` chết, trả một thẻ của cây 1 | 1 | 1 |
| 7 | sau (4) | Không ai còn là `a` hay `b`, nhưng cây 1 vẫn bị `ban` của cây 2 giữ, và cây 2 vẫn bị `ban` của cây 1 giữ. Không bộ đếm nào về 0, nên **không có `huy` nào** | 1 | 1 |

**Kết quả khi chạy:**

```text
tao 1
tao 2
dem a = 2, dem b = 2
het main
```

Không có dòng `huy` nào, và chương trình vẫn thoát với mã 0: đây là **rò rỉ bộ nhớ**, không phải lỗi làm chương trình dừng. Hai cây vẫn nằm ở heap nhưng không còn biến nào của `main` tới được chúng, nên không ai trả thẻ được nữa. Ta nhờ AddressSanitizer xác nhận (biên dịch thêm `-g -fsanitize=address`, [Bài 07](07-new-delete.md)). Đây là báo cáo thật, mình đã **rút gọn** (bỏ các dòng gọi hàm nội bộ của thư viện, đường dẫn, và một khối báo thứ hai gần như giống hệt khối đầu):

```text
==...==ERROR: LeakSanitizer: detected memory leaks

Indirect leak of 40 byte(s) in 1 object(s) allocated from:
    #0 ... in operator new(unsigned long)
    ...
    #8 ... in std::shared_ptr<Cay> std::make_shared<Cay, int>(int&&)
    #9 ... in main bai.cpp:19

SUMMARY: AddressSanitizer: 80 byte(s) leaked in 2 allocation(s).
```

("Indirect" nghĩa là khối đó chỉ còn được trỏ tới từ một khối rò rỉ khác: đúng với hai cây trỏ vào nhau.) Mỗi khối rò rỉ là **một** lần cấp phát (cây và khối điều khiển đi chung, như mục 2). Lưu ý LeakSanitizer là công cụ bắt rò rỉ rất tốt nhưng không phải lúc nào cũng bắt được; ở đây ta thấy rò rỉ nhờ cả dòng `huy` vắng mặt.

### 4. Phá vòng bằng `std::weak_ptr`

Cách phá: cho **một chiều** của vòng không còn giữ thẻ, chỉ **nhìn**. `std::weak_ptr<Cay>` đứng ở cửa kính: nó biết cây ở đâu nhưng **không cộng vào bộ đếm mạnh**, nên không giữ cây sống. Ta làm lại bài trên theo kiểu cha và con: cha giữ con bằng `shared_ptr` (dòng (1)), còn con chỉ nhìn cha bằng `weak_ptr` (dòng (2)).

```cpp
#include <iostream>
#include <memory>

struct Cay {
    int cao;
    std::shared_ptr<Cay> con;                // (1)
    std::weak_ptr<Cay> cha;                  // (2)
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

int main() {
    {
        auto a = std::make_shared<Cay>(1);
        auto b = std::make_shared<Cay>(2);
        a->con = b;                          // (3)
        b->cha = a;                          // (4)
        std::cout << "dem a = " << a.use_count() << ", dem b = " << b.use_count() << "\n";
    }                                        // (5)
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng**

| Bước | Dòng | Chuyện gì xảy ra | Đếm cây 1 | Đếm cây 2 |
|---|---|---|---|---|
| 1 | đầu khối | `tao 1`, `tao 2`; `a` giữ cây 1, `b` giữ cây 2 | 1 | 1 |
| 2 | (3) | `a->con = b`: cha giữ con bằng `shared_ptr`, thẻ +1 | 1 | 2 |
| 3 | (4) | `b->cha = a`: là `weak_ptr` nên **không** cộng | 1 | 2 |
| 4 | sau (4) | In `dem a = 1, dem b = 2` | 1 | 2 |
| 5 | (5) `}` | `b` chết: trả một thẻ của cây 2 (cây 1 vẫn giữ nó) | 1 | 1 |
| 6 | (5) `}` | `a` chết: đếm cây 1 về **0**, hàm hủy cây 1 chạy, in `huy 1`. Khi đó thành viên `con` của nó bị hủy, trả thẻ cuối của cây 2 | 0 | 1 |
| 7 | (5) | `con` bị hủy xong: đếm cây 2 về 0, in `huy 2` | 0 | 0 |

**Kết quả khi chạy:**

```text
tao 1
tao 2
dem a = 1, dem b = 2
huy 1
huy 2
het main
```

Đủ hai `huy`, và thứ tự là `huy 1` rồi `huy 2`: cây 1 bị hủy trước, kéo theo cây 2. Biến `b` thì chết trước (ở `}`), nhưng nó chỉ trả một thẻ; cây 2 vẫn được `con` của cây 1 giữ, nên chỉ bị hủy như hệ quả của việc cây 1 bị hủy. Quy tắc dùng: trong một quan hệ hai chiều, hướng "sở hữu" (cha giữ con) dùng `shared_ptr`, hướng ngược lại (con nhìn cha) dùng `weak_ptr`.

### 5. `weak_ptr` dùng thế nào: `expired()` và `lock()`

Vì `weak_ptr` không giữ cây sống nên cây có thể đã bị hủy lúc bạn nhìn. Vậy bạn **không** dùng `*w` hay `w->cao` trực tiếp. Có hai cách hỏi:

- `w.expired()` trả `true` nếu cây đã bị hủy.
- `w.lock()` trả về một `shared_ptr`: nếu cây còn sống thì đó là một thẻ thật (đếm +1 trong lúc bạn cầm), nếu cây đã hết thì đó là `shared_ptr` rỗng. Dùng `lock()` là cách đúng, vì cây không thể biến mất giữa lúc bạn kiểm tra và lúc dùng (bạn đang cầm thẻ).

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

void xem(const std::weak_ptr<Cay>& w) {
    std::shared_ptr<Cay> s = w.lock();                          // (3)
    if (s) {
        std::cout << "con cay cao " << s->cao << ", dem = " << s.use_count() << "\n";
    } else {
        std::cout << "cay da het\n";
    }
}

int main() {
    std::weak_ptr<Cay> w;
    {
        auto a = std::make_shared<Cay>(5);
        w = a;                                                   // (1)
        std::cout << "dem = " << a.use_count() << ", expired = " << w.expired() << "\n";  // (2)
        xem(w);
    }                                                            // (4)
    std::cout << "expired = " << w.expired() << "\n";
    xem(w);
    return 0;
}
```

(`expired()` là `bool`, nên `cout` in `1` cho đúng và `0` cho sai, như [Bài 09](09-unique-ptr.md).)

**Chạy từng dòng**

| Bước | Dòng | Chuyện gì xảy ra | Đếm |
|---|---|---|---|
| 1 | đầu `main` | `w` là `weak_ptr` rỗng, chưa nhìn gì | 0 |
| 2 | `auto a` | Tạo cây 5, in `tao 5` | 1 |
| 3 | (1) | `w = a`: `w` nhìn cây 5, **không cộng** vào đếm | 1 |
| 4 | (2) | In `dem = 1, expired = 0` | 1 |
| 5 | `xem(w)`, (3) | `lock()` trả một `shared_ptr` `s` giữ cây: thẻ +1 | 2 |
| 6 | trong `xem` | `s` đúng nên in `con cay cao 5, dem = 2` | 2 |
| 7 | hết `xem` | `s` chết, trả thẻ | 1 |
| 8 | (4) `}` | `a` chết: đếm về 0, in `huy 5` | 0 |
| 9 | sau (4) | `expired()` giờ là `true`: in `expired = 1` | 0 |
| 10 | `xem(w)` | `lock()` trả `shared_ptr` rỗng, nên in `cay da het` | 0 |

**Kết quả khi chạy:**

```text
tao 5
dem = 1, expired = 0
con cay cao 5, dem = 2
huy 5
expired = 1
cay da het
```

**Thử thay đổi: ở `xem`, thay `s->cao` bằng `w->cao` (dùng thẳng `weak_ptr`).** Mình đã biên dịch: không ra chương trình. g++ báo (rút gọn):

```text
error: base operand of '->' has non-pointer type 'const std::weak_ptr<Cay>'
```

`weak_ptr` cố tình **không** có `->` và `*`: muốn dùng cây thì bạn bắt buộc phải qua `lock()` để lấy `shared_ptr`, và kiểm tra xem cây còn không.

Hai chỗ `weak_ptr` hay được dùng, ngoài việc phá vòng. **Cache (bộ nhớ đệm)** là chỗ cất tạm kết quả vừa dùng để lần sau lấy cho nhanh, không phải làm lại. **Observer (người theo dõi)** là một đối tượng muốn biết chuyện của đối tượng khác mà không sở hữu nó. Cả hai chỉ cần "nhìn", không nên ép chủ thể sống. Ví dụ cache nằm ở phần 💻.

### 6. An toàn giữa các luồng

**Luồng (thread)** là một dòng chạy riêng trong cùng chương trình, gần giống goroutine của Go (khác ở cách chương trình lập lịch). Khi hai luồng cùng đụng một chỗ nhớ, trong đó có luồng ghi, mà không có biện pháp phối hợp, thì đó là **tranh chấp dữ liệu (data race)** và hành vi chương trình là không xác định. Với `shared_ptr`, chỉ các câu sau là đúng:

- Bộ đếm trong khối điều khiển được cập nhật bằng **thao tác nguyên tử** (một thao tác mà luồng khác không thể chen vào giữa). Vậy nên các luồng **copy và hủy những `shared_ptr` khác nhau** cùng trỏ một cây thì bộ đếm vẫn đúng.
- Nhưng **cây bên trong thì không tự an toàn**: hai luồng cùng sửa `cay->cao` vẫn là tranh chấp dữ liệu.
- Và hai luồng cùng sửa **một biến `shared_ptr`** (ví dụ cùng gán lại `a = ...`) mà không có phối hợp cũng là tranh chấp dữ liệu.

Vì vậy "`shared_ptr` an toàn đa luồng" chỉ đúng cho phần bộ đếm. Trong chương trình đa luồng giá trị `use_count()` cũng chỉ mang tính ước lượng.

### 7. Cái giá của `shared_ptr`, và bảng chọn nhanh

Mỗi `shared_ptr` đi kèm một khối điều khiển ở heap, mỗi lần copy hoặc hủy phải cập nhật bộ đếm bằng thao tác nguyên tử (mục 6), và nó to hơn con trỏ thô (16 byte so với 8 trên máy mình). Chi phí đó không lớn với đa số chương trình, nhưng cũng không đáng chịu nếu bạn chỉ có một chủ rõ ràng. Quan trọng hơn, `shared_ptr` làm **khó thấy** khi nào đối tượng chết, và mở đường cho vòng tham chiếu. Vì vậy **đừng dùng `shared_ptr` "cho chắc"**.

Nếu sau này bạn cần đổi `unique_ptr` thành `shared_ptr` thì được: `std::shared_ptr<Cay> s = std::move(u);` ([Bài 09](09-unique-ptr.md)). Mình đã biên dịch và chạy: `u` thành `nullptr` và `s.use_count()` là 1. Chiều ngược lại thì không có.

**Bảng chọn nhanh** (nên chép lại và học thuộc):

| Tình huống | Dùng |
|---|---|
| Đối tượng ở heap có **một** chủ rõ ràng (mặc định) | `std::unique_ptr` |
| Đối tượng **thật sự chia sẻ**, không biết ai xong cuối | `std::shared_ptr` |
| Chỉ **nhìn**, không giữ sống (cache, observer, chiều ngược của vòng) | `std::weak_ptr` |
| Hàm chỉ **dùng** đối tượng, có chủ ở nơi khác | tham chiếu `const T&` hoặc con trỏ thô `T*` |
| Cần diễn tả "có thể không có gì" | `nullptr` (con trỏ), hoặc `std::optional` ([Bài 14](14-cpp14-17.md)) |

## 💻 Ví dụ code

### Ví dụ: cache bằng `weak_ptr`

Một `Kho` cất tạm cây vừa tạo. Ai xin cây mà cây còn sống thì dùng lại, còn không thì tạo mới. `Kho` chỉ **nhìn** (`weak_ptr`) chứ không giữ, nên không ép cây sống mãi.

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

struct Kho {
    std::weak_ptr<Cay> nho;                              // (1)

    std::shared_ptr<Cay> lay() {
        std::shared_ptr<Cay> s = nho.lock();             // (2)
        if (s) {
            std::cout << "dung lai cay cu\n";
        } else {
            std::cout << "chua co, tao moi\n";
            s = std::make_shared<Cay>(7);                // (3)
            nho = s;                                     // (4)
        }
        return s;
    }
};

int main() {
    Kho kho;
    auto x = kho.lay();
    auto y = kho.lay();
    std::cout << "dem = " << x.use_count() << "\n";
    x.reset();
    y.reset();
    std::cout << "da buong het\n";
    auto z = kho.lay();
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng**

| Bước | Dòng | Chuyện gì xảy ra | Đếm |
|---|---|---|---|
| 1 | `x = kho.lay()`, (2) | `nho` (khai báo ở (1)) rỗng nên `lock()` trả rỗng; vào nhánh `else`: in `chua co, tao moi` | 0 |
| 2 | (3), (4) | Tạo cây 7 (in `tao 7`) vào `s`; `nho` nhìn nó (không cộng). `return s` trao cây cho `x` | 1 |
| 3 | `y = kho.lay()`, (2) | `lock()` thấy cây còn sống, trả thẻ: in `dung lai cay cu`. `y` là người giữ thứ hai; in `dem = 2` | 2 |
| 4 | `x.reset()`, `y.reset()` | `x` buông (đếm 1), rồi `y` buông: đếm về 0, in `huy 7`. Rồi in `da buong het` | 0 |
| 5 | `z = kho.lay()` | `lock()` trả rỗng: in `chua co, tao moi`, `tao 7`; `z` giữ cây mới | 1 |
| 6 | cuối `main` | In `het main`; `z` chết nên in `huy 7` (`kho` chết cùng lúc, không giữ gì) | 0 |

**Kết quả khi chạy:**

```text
chua co, tao moi
tao 7
dung lai cay cu
dem = 2
huy 7
da buong het
chua co, tao moi
tao 7
het main
huy 7
```

Chỉ có hai `tao 7` cho ba lần xin: lần thứ hai dùng lại. Và `Kho` không cản `huy 7` ở giữa, vì nó chỉ là người nhìn.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::shared_ptr` hoạt động thế nào?"
    `shared_ptr` cho nhiều chủ cùng giữ một đối tượng. Chúng cùng trỏ tới một **khối điều khiển** chứa bộ đếm tham chiếu mạnh (số `shared_ptr`) và bộ đếm yếu (số `weak_ptr`). Copy một `shared_ptr` thì đếm +1; hủy, `reset` hay gán lại thì −1; khi bộ đếm mạnh về 0 thì đối tượng bị hủy. `use_count()` đọc bộ đếm mạnh nhưng chỉ nên dùng để học và gỡ lỗi.

??? question "`shared_ptr` có thread-safe không?"
    Chỉ một phần. Bộ đếm trong khối điều khiển được cập nhật nguyên tử, nên copy và hủy các `shared_ptr` khác nhau cùng trỏ một đối tượng từ nhiều luồng là an toàn. Nhưng đối tượng được trỏ tới thì **không** được làm cho an toàn, và hai luồng cùng sửa **một** biến `shared_ptr` (ví dụ cùng gán lại) mà không đồng bộ là tranh chấp dữ liệu.

??? question "Vòng tham chiếu là gì và phá nó thế nào?"
    Khi A giữ `shared_ptr` tới B và B giữ `shared_ptr` tới A, bộ đếm của cả hai không bao giờ về 0 kể cả khi không còn ai ngoài vòng dùng chúng, nên chúng không bao giờ bị hủy: rò rỉ bộ nhớ (chương trình vẫn chạy bình thường). Cách phá là đổi một chiều thành `std::weak_ptr`, chiều không mang quyền sở hữu, ví dụ con nhìn cha.

??? question "`weak_ptr` dùng khi nào?"
    Khi bạn muốn **nhìn** một đối tượng mà không giữ nó sống: phá vòng tham chiếu, cache (cất tạm kết quả để lần sau lấy nhanh), observer (người theo dõi một đối tượng mà không sở hữu nó). Muốn dùng đối tượng thì gọi `lock()`, kết quả là `shared_ptr` rỗng nếu đối tượng đã bị hủy; `expired()` cho biết nó đã hết chưa. `weak_ptr` không tăng bộ đếm mạnh.

??? question "`make_shared` khác `shared_ptr<T>(new T)` thế nào?"
    `make_shared<T>(...)` thường cấp phát đối tượng và khối điều khiển trong **một** lần, nên ít tốn kém hơn và gọn hơn; `shared_ptr<T>(new T)` thường tốn hai lần cấp phát. Đây là chi tiết cài đặt chứ chuẩn không bắt buộc. Với `make_shared`, vùng nhớ của đối tượng thường chỉ được trả sau khi `weak_ptr` cuối cùng mất, dù hàm hủy vẫn chạy đúng lúc. Ngoài ra không có `new` trần trong code dùng.

??? question "Khi nào chọn loại con trỏ nào?"
    Mặc định `unique_ptr` khi có một chủ rõ ràng. `shared_ptr` chỉ khi quyền sở hữu thật sự chia sẻ và không biết ai xong cuối, vì nó tốn khối điều khiển và thao tác nguyên tử, và làm khó thấy vòng đời. `weak_ptr` để nhìn mà không giữ sống. Hàm chỉ dùng đối tượng thì nhận tham chiếu hoặc con trỏ thô; "có thể không có gì" thì `nullptr` hoặc `std::optional`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Vòng `shared_ptr` giữa hai đối tượng"
    Hai bên giữ nhau nên không bao giờ về 0 và không bao giờ bị hủy. Chương trình vẫn chạy, chỉ rò rỉ lặng lẽ. Đổi một chiều (thường là con nhìn cha) thành `weak_ptr`.

!!! warning "Lỗi 2: Dùng `shared_ptr` cho mọi thứ \"cho chắc\""
    Bạn trả giá khối điều khiển và bộ đếm nguyên tử, và mất khả năng nhìn ra "ai sở hữu cái này". Nếu chỉ có một chủ thì dùng `unique_ptr`.

!!! warning "Lỗi 3: Dùng `use_count()` để quyết định logic"
    Ví dụ `if (p.use_count() == 1) ...` để suy ra "mình là người cuối". Trong chương trình đa luồng giá trị đó có thể đã đổi ngay sau khi bạn đọc. Hãy dùng nó để học và gỡ lỗi thôi.

!!! warning "Lỗi 4: Tạo hai `shared_ptr` từ cùng một con trỏ thô"
    Mỗi cái có khối điều khiển riêng nên đối tượng bị xóa hai lần. Muốn thêm người giữ thì copy một `shared_ptr` có sẵn.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="10" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn code sau. `cout` in `1` cho đúng và `0` cho sai. Dòng cuối in ra gì?

```text
auto a = std::make_shared<int>(1);
auto b = a;
auto c = a;
b.reset();
std::weak_ptr<int> w = a;
auto d = std::move(c);
std::cout << a.use_count() << " " << (c == nullptr) << "\n";
```

- `3 0`: `reset` của `b` không làm đếm giảm, `c` vẫn giữ cây
- `2 1`: chỉ `a` và `d` giữ, `w` không tính
- `1 1`: chỉ `a` giữ, vì `d` chỉ là bản nhìn chứ không giữ
- `4 0`: cả bốn đều giữ, vì `weak_ptr` cũng đếm thẻ

<p class="giai-thich" markdown>Đếm đi từng bước: `a` là 1, `b` và `c` thành 3, `b.reset()` về 2, `w` là `weak_ptr` nên không đổi, rồi `std::move(c)` chỉ đổi chủ từ `c` sang `d` nên vẫn 2, và `c` thành `nullptr` nên in `2 1`; mình đã chạy ra đúng vậy. `reset` có giảm đếm, nên `3 0` sai. `d` là `shared_ptr` giữ thẻ thật, không phải "bản nhìn". `weak_ptr` không cộng vào bộ đếm mạnh, nên không thể ra 4.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). Chương trình in ra gì?

```text
auto a = std::make_shared<Cay>(1);
std::weak_ptr<Cay> w = a;
a.reset();
std::cout << w.expired() << (w.lock() == nullptr) << "\n";
```

- `tao 1, 00, huy 1`: `weak_ptr` giữ cây sống nên chưa hủy
- `tao 1, 01, huy 1`: `expired` báo sai, còn `lock` lại trả rỗng
- `tao 1, huy 1, 00`: cây hủy mà `weak_ptr` vẫn báo còn cây
- `tao 1, huy 1, 11`: cây hủy lúc `reset`, cả hai đều báo hết

<p class="giai-thich" markdown>`a` là `shared_ptr` duy nhất, nên `a.reset()` đưa đếm về 0 và in `huy 1` ngay, trước dòng cuối; `w` không giữ cây sống nên không cản được. Sau đó cả `expired()` và `lock() == nullptr` đều đúng nên in `11`; mình đã chạy ra `tao 1, huy 1, 11`. Dãy `tao 1, 00, huy 1` tin rằng `weak_ptr` giữ cây sống, mà nó không giữ. Dãy `tao 1, huy 1, 00` đúng về thứ tự `huy 1`, nhưng sai ở số cuối: cây đã hủy thì `expired()` phải là đúng (`1`), nên không thể in `0`. Kết quả `01` cũng mâu thuẫn: cây đã hủy thì hai phép kiểm tra phải cùng đúng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`, và có thành viên `std::shared_ptr<Cay> ban;`). Chương trình in ra gì?

```text
{
    auto a = std::make_shared<Cay>(1);
    auto b = std::make_shared<Cay>(2);
    a->ban = b;
    b->ban = a;
}
std::cout << "xong\n";
```

- `tao 1, tao 2, xong`: cả hai cây đều không bị hủy
- `tao 1, tao 2, huy 2, huy 1, xong`: cả hai hủy ngay
- `tao 1, tao 2, huy 2, xong`: chỉ `b` hủy
- `tao 1, tao 2, xong, huy 2, huy 1`: hủy sau

<p class="giai-thich" markdown>Hai cây giữ nhau nên khi `a` và `b` chết ở `}`, mỗi cây vẫn còn một thẻ do cây kia giữ: bộ đếm dừng ở 1, không về 0, nên không có `huy` nào; mình đã chạy ra đúng dãy này. Hai dãy có `huy` ngay sau khối (`huy 2, huy 1`, hay chỉ `huy 2`) tin rằng biến chết là đủ để cây bị hủy, mà ở đây còn thẻ trong vòng. Dãy có `huy` sau `xong` tin rằng chương trình dọn lúc thoát, nhưng `shared_ptr` không có bộ dọn cuối chương trình.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Hàm hủy của một đối tượng được nhiều `shared_ptr` cùng giữ chạy khi nào?

- Khi `shared_ptr` đầu tiên (nơi tạo ra nó) chết, các bản copy chỉ mượn
- Khi bất kỳ `shared_ptr` nào chết, mỗi cái hủy một phần của đối tượng
- Khi bộ đếm mạnh về 0, tức là `shared_ptr` giữ cuối cùng vừa buông
- Khi chương trình kết thúc, vì `shared_ptr` gom rác vào lúc cuối

<p class="giai-thich" markdown>Đối tượng chết khi không còn ai giữ thẻ, tức là bộ đếm mạnh về 0, dù người buông cuối là bản gốc hay bản copy. Không có "người tạo ra nó" đặc biệt: các bản copy đều là chủ ngang nhau, nên nếu cái đầu tiên chết trước thì đối tượng vẫn sống. Mỗi `shared_ptr` chết chỉ trừ 1, không hủy "một phần". Và C++ không có bộ gom rác lúc cuối, chỉ có hàm hủy chạy đúng lúc đếm về 0.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Một `weak_ptr` trỏ vào cây có làm bộ đếm mạnh (`use_count()`) tăng không?

- Có, mỗi `weak_ptr` cộng 1 vào `use_count()`
- Không: `weak_ptr` không giữ cây sống nên không vào bộ đếm mạnh
- Không, và `weak_ptr` cũng không có cách nào để dùng được cây
- Chỉ cộng vào bộ đếm yếu, và cây vẫn chưa bị hủy cho đến khi bộ đếm yếu về 0

<p class="giai-thich" markdown>`weak_ptr` chỉ nhìn: nó cộng vào bộ đếm yếu chứ không cộng vào bộ đếm mạnh, nên cây vẫn bị hủy khi `shared_ptr` cuối cùng buông. Dùng được cây vẫn có cách, là `lock()` trả về `shared_ptr`, nên không phải "không có cách nào". Bộ đếm yếu tồn tại thật, nhưng cây sống hay chết do bộ đếm mạnh quyết định, không phải bộ đếm yếu.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** `w.lock()` (với `w` là `weak_ptr<Cay>`) trả về gì?

- Con trỏ thô tới cây, hoặc `nullptr` nếu cây đã hủy
- Một `weak_ptr` mới trỏ cùng cây
- Một `bool`: cây còn sống hay không
- Một `shared_ptr`, rỗng nếu cây đã bị hủy rồi

<p class="giai-thich" markdown>`lock()` trả một `shared_ptr`: nếu cây còn sống thì nó là một thẻ thật (đếm +1 trong lúc bạn cầm), nếu cây đã hết thì rỗng, và bạn kiểm tra bằng `if (s)`. Nó không trả con trỏ thô, vì con trỏ thô không giữ cây sống và có thể treo ngay sau đó. Nó cũng không trả `weak_ptr` (không dùng được để truy cập). Việc trả `bool` là của `expired()`, không phải của `lock()`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Ba cửa sổ cùng hiển thị một bức ảnh, cửa sổ nào đóng cuối cùng thì ảnh phải được dọn. Cách mô tả nào hợp nhất?

- Mỗi cửa sổ giữ một `unique_ptr` tới ảnh đó
- Mỗi cửa sổ giữ con trỏ thô, và tự `delete` khi đóng
- Mỗi cửa sổ giữ một `shared_ptr` tới ảnh
- Mỗi cửa sổ giữ một `weak_ptr` tới ảnh đó

<p class="giai-thich" markdown>Đây là chia sẻ quyền sở hữu thật sự, nên `shared_ptr`: ảnh được dọn khi cửa sổ cuối buông. `unique_ptr` không copy được nên ba cửa sổ không cùng giữ được. Con trỏ thô với `delete` ở mỗi cửa sổ sẽ xóa ảnh nhiều lần. `weak_ptr` thì không giữ ảnh sống, nên nếu cả ba chỉ nhìn thì ảnh không có chủ nào.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 8.** Câu nào về an toàn đa luồng của `shared_ptr` là đúng?

- Bộ đếm cập nhật an toàn giữa các luồng, còn đối tượng bên trong thì không
- Cả bộ đếm lẫn đối tượng bên trong đều tự an toàn khi dùng `shared_ptr`
- Chỉ an toàn nếu mọi luồng đều chỉ đọc, còn copy `shared_ptr` ở nhiều luồng là tranh chấp
- Hoàn toàn không an toàn, nên mỗi lần copy `shared_ptr` đều phải tự khóa lại

<p class="giai-thich" markdown>Chuẩn bảo đảm bộ đếm trong khối điều khiển được cập nhật an toàn giữa các luồng (nguyên tử), nên copy và hủy các `shared_ptr` khác nhau cùng trỏ một đối tượng từ nhiều luồng là an toàn. Đối tượng bên trong không được bảo vệ gì, nên tin rằng cả hai đều tự an toàn là sai. Copy ở nhiều luồng không phải tranh chấp (tranh chấp xảy ra khi có luồng sửa chính biến `shared_ptr` đó trong lúc luồng khác đọc hoặc sửa nó). Và bạn cũng không phải tự khóa mỗi lần copy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `std::shared_ptr<T>` (trong `<memory>`, tạo bằng `std::make_shared<T>(...)`) cho nhiều chủ cùng giữ một đối tượng: copy thì bộ đếm tham chiếu +1, hủy/`reset`/gán lại thì −1, và đối tượng bị hủy khi bộ đếm mạnh về 0 (`use_count()` đọc nó, chỉ để học và gỡ lỗi).
2. Các bộ đếm nằm ở **khối điều khiển** dùng chung (một bộ đếm mạnh cho `shared_ptr`, một bộ đếm yếu cho `weak_ptr`); mỗi `shared_ptr` thường ghi hai địa chỉ, và `make_shared` thường xin heap một lần cho cả đối tượng lẫn khối điều khiển.
3. Hai đối tượng giữ `shared_ptr` của nhau tạo **vòng tham chiếu**: bộ đếm không bao giờ về 0, hàm hủy không bao giờ chạy (rò rỉ, chương trình vẫn thoát bình thường, LeakSanitizer báo); phá bằng cách đổi một chiều thành `std::weak_ptr`.
4. `weak_ptr` chỉ nhìn, không cộng bộ đếm mạnh nên không giữ đối tượng sống; dùng `expired()` để hỏi còn sống không và `lock()` để lấy `shared_ptr` (rỗng nếu đã hủy); hợp với phá vòng, cache và observer; so với Go, GC tracing dọn được vòng còn đếm tham chiếu thì không.
5. Bộ đếm cập nhật nguyên tử nên copy/hủy các `shared_ptr` khác nhau từ nhiều luồng là an toàn, nhưng đối tượng bên trong và việc nhiều luồng cùng sửa MỘT biến `shared_ptr` thì không; vì có cái giá (khối điều khiển, thao tác nguyên tử) nên không dùng "cho chắc": một chủ → `unique_ptr`, thật sự chia sẻ → `shared_ptr`, chỉ nhìn → `weak_ptr`/con trỏ thô/tham chiếu, "có thể không có" → `nullptr`/`std::optional`.
