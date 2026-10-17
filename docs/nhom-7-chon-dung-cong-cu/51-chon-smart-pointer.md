# Bài 51 — Chọn smart pointer: unique_ptr, shared_ptr, weak_ptr hay con trỏ thô

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Trả lời mọi tình huống chọn con trỏ bằng **một câu hỏi gốc**: "AI SỞ HỮU?", rồi đi theo **cây quyết định** để ra `unique_ptr`, `shared_ptr`, `weak_ptr`, tham chiếu/con trỏ thô, hay không cần con trỏ.
    - Giải được **10 tình huống** hay bị hỏi (một chủ, truyền để dùng tạm, nhiều chủ, cache, cha-con, vòng tham chiếu, factory, `make_shared`, mảng và bộ xóa tùy chỉnh, quan sát `use_count`/`expired`), mỗi cái có đáp án và lý do.
    - Nói được **chi phí thật** của từng loại (kích thước, số lần cấp phát, bộ đếm nguyên tử) bằng số đã đo, và biết **khi nào KHÔNG nên dùng** từng loại.
    - Tránh bẫy kinh điển: nhiều `shared_ptr` dựng từ cùng một con trỏ thô (double free), `unique_ptr<T>` giữ mảng, và `shared_ptr` "cho chắc".

**Bạn cần biết trước:** [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (`*p`, `->`, `nullptr`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (`const T&`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, double free, AddressSanitizer), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `std::move`, `get`/`release`/`reset`), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, `weak_ptr`, bộ đếm, vòng tham chiếu), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`std::map`), [Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md) (đa hình qua con trỏ lớp cha) và [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (thay `operator new` để đếm cấp phát). Bài này **không dạy lại** các loại con trỏ đó; nó dạy cách **chọn**.

## 🧠 Câu chuyện mở đầu

Phỏng vấn. Người phỏng vấn đẩy tờ giấy qua bàn: lớp `Bep` có một thành viên `Thot*`, ba chỗ khác trong chương trình cũng cầm `Thot*` đó, và hàm hủy của `Bep` có `delete`. "Em sửa lại bằng smart pointer nào?" Nhiều người đọc thuộc lòng bảng tên và đoán bừa `shared_ptr` cho chắc.

Người phỏng vấn muốn nghe một câu hỏi ngược lại: **"Ai sở hữu cái thớt này?"** Quay lại **nhà bếp** quen thuộc: dụng cụ cất trong **tủ** (heap). `unique_ptr` là **một chiếc chìa duy nhất** ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)). `shared_ptr` là **nhiều thẻ mở tủ cùng một bảng đếm** ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)); `weak_ptr` là người **nhìn qua cửa kính**. Con trỏ thô và tham chiếu là **tờ giấy ghi số tủ**: giúp tìm đồ, nhưng người cầm tờ giấy không chịu trách nhiệm cất.

!!! info "Chỗ nào ví von này không còn đúng?"
    Tờ giấy ghi số tủ không tự báo khi tủ đã bị dọn: con trỏ thô tới đối tượng đã chết vẫn trông bình thường (con trỏ treo, [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md)). Và đầu bếp thật thì nhìn thấy ai đang cầm thẻ; trong code, `shared_ptr` rải khắp nơi làm bạn **không còn thấy** ai là người cuối.

!!! info "Bạn biết Go?"
    Trong Go, mọi con trỏ ngầm là "đồng sở hữu": GC dọn khi không ai trỏ tới nữa, nên với bộ nhớ bạn không cần hỏi "ai sở hữu". Thói quen "cứ chia sẻ thoải mái" đó, mang sang C++ thành `shared_ptr` cho mọi thứ, là sai: bạn trả thêm chi phí và mất khả năng nhìn ra vòng đời. Với tài nguyên khác như file, Go vẫn có chủ rõ ràng (`f, _ := os.Open(...)` rồi `defer f.Close()`), và đó chính là suy nghĩ cần mang sang.

## 📖 Giải thích

### 1. Câu hỏi gốc và cây quyết định

Với mỗi đối tượng, trả lời lần lượt các câu sau. Chỉ khi đi hết các nhánh mới chọn kiểu.

```text
0. Có CẦN nằm ở heap không?
   (kích thước chỉ biết lúc chạy; đa hình qua con trỏ lớp cha; phải sống lâu hơn
    hàm tạo ra nó; được trao đi nơi khác)
   Không  -> biến thường / thành viên trực tiếp. KHÔNG cần con trỏ.
   Có     -> sang câu 1.

1. AI SỞ HỮU (ai chịu trách nhiệm xóa)?
   Đúng một chỗ, rõ ràng                      -> std::unique_ptr   (mặc định)
   Nhiều chỗ, không biết ai xong cuối         -> std::shared_ptr   (hiếm hơn bạn nghĩ)

2. Còn các chỗ khác chỉ CẦN DÙNG, không sở hữu:
   Dùng trong lúc hàm chạy, chủ chắc chắn sống lâu hơn   -> T& / const T&  (hoặc T* nếu "có thể không có")
   Giữ lâu dài, mà chủ có thể chết trước                 -> std::weak_ptr   (chủ là shared_ptr)
```

Chữ "sở hữu" ở đây nghĩa đúng như [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md): ai gọi `delete` cuối cùng. Một con trỏ thô hay tham chiếu **không** sở hữu: ta gọi là **con trỏ không sở hữu (non-owning pointer)**. Chúng vẫn hoàn toàn đúng trong C++ hiện đại, miễn là chủ thật nằm ở chỗ khác và sống lâu hơn.

### 2. Chi phí: `shared_ptr` không miễn phí

| | `T*` / `T&` | `unique_ptr<T>` | `shared_ptr<T>` | `weak_ptr<T>` |
|---|---|---|---|---|
| Kích thước (đo, 64-bit) | 8 byte | 8 byte | 16 byte | 16 byte |
| Cấp phát thêm | không | không | khối điều khiển ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)) | dùng chung khối của `shared_ptr` |
| Mỗi lần copy/hủy | không | không (không copy được) | tăng/giảm bộ đếm **nguyên tử** | tăng/giảm bộ đếm yếu |
| Cho thấy ai sở hữu | không | có (một chủ) | mờ (nhiều chủ) | có (không chủ) |

(**Nguyên tử** nghĩa là một phép tăng hay giảm mà luồng khác không chen vào giữa được, như [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) mục 6 đã nói.) Số kích thước và số lần cấp phát bên trên mình đo ở Ví dụ 4. Bài này không đo thời gian, nhưng nguyên lý rõ: `unique_ptr` gần như con trỏ thô, còn `shared_ptr` luôn trả thêm khối điều khiển và phép nguyên tử. Chi phí đó chấp nhận được khi nhiều chủ là **thật**, và lãng phí khi bạn chỉ muốn "an toàn".

### 3. Mười tình huống

Mỗi dòng là một câu hỏi phỏng vấn kèm đáp án. Ví dụ ở phần 💻 chạy thật cho các dòng có số "VD".

| # | Tình huống | Chọn | Vì sao, và bẫy |
|---|---|---|---|
| 1 | Một đầu bếp có một thớt riêng, không ai khác giữ | `std::unique_ptr<Thot>` (hoặc thành viên thường `Thot` nếu không cần heap) | Một chủ rõ nên hàm hủy chạy đúng một lần, không tốn thêm. VD 1 |
| 2 | Hàm `thai` chỉ dùng thớt trong lúc chạy | `const Thot&` (hoặc `Thot*` nếu có thể không có thớt) | Nhận được thớt từ mọi loại chủ. **Không** nhận `shared_ptr` theo giá trị chỉ để xem: mỗi lần gọi là một lần tăng rồi giảm bộ đếm nguyên tử. VD 1 |
| 3 | Hai đầu bếp cùng giữ một thớt, không ai biết ai xong cuối | `std::shared_ptr<Thot>` | Sở hữu chia sẻ **thật sự**: thớt chết khi người cuối buông. VD 1 |
| 4 | Kho ảnh cất tạm ảnh đã nạp để dùng lại, nhưng không được giữ ảnh sống mãi | `std::map<std::string, std::weak_ptr<Anh>>`, trả `shared_ptr<Anh>` | Cache chỉ nhìn; ai dùng xong hết thì ảnh được giải phóng. Bẫy: mục hết hạn vẫn nằm trong map nên phải dọn. VD 3 |
| 5 | Nút cha sở hữu các nút con, con cần biết cha | Cha giữ con bằng `unique_ptr`, con giữ cha bằng `Nut*` (hoặc `weak_ptr` nếu cha do `shared_ptr` quản lý) | Chỉ cha giữ con thì con không sống lâu hơn cha, con trỏ ngược không treo. Bẫy: chuyển con sang cha khác mà quên cập nhật con trỏ ngược. VD 2 |
| 6 | Hai đối tượng trỏ vào nhau bằng `shared_ptr` | Đổi **chiều ngược** thành `weak_ptr` | Vòng làm bộ đếm không về 0: rò rỉ lặng lẽ, chương trình vẫn thoát mã 0. VD 2 |
| 7 | Hàm factory tạo đối tượng rồi trao cho nơi gọi | Trả `std::unique_ptr<T>` | Nơi gọi muốn một chủ thì giữ nguyên, muốn nhiều chủ thì gán sang `shared_ptr` (làm được); chiều ngược lại thì không. Trả `shared_ptr` là ép chi phí lên mọi nơi gọi. VD 1 |
| 8 | Tạo một `shared_ptr` mới | `std::make_shared<T>(...)` thay vì `std::shared_ptr<T>(new T(...))` | Một lần cấp phát thay vì hai, không có `new` trần. Nhược điểm: bộ nhớ của đối tượng ở lại đến khi `weak_ptr` cuối cùng chết. VD 4 |
| 9 | Mảng động, hoặc thứ cần đóng chứ không `delete` (tệp mở) | `unique_ptr<T[]>` (nhưng thường dùng `std::vector`); `unique_ptr<FILE, BoXoa>` | `unique_ptr<T[]>` gọi `delete[]` đúng; bộ xóa tùy chỉnh thay việc `delete`. Bẫy: `unique_ptr<int>` giữ mảng thì gọi nhầm `delete`. VD 5 và mục "Bản sai" |
| 10 | Muốn biết đối tượng còn sống không, ai đang giữ | `expired()`, `lock()`, `use_count()` | `lock()` vừa kiểm vừa giữ sống nên dùng cho logic. `use_count()` chỉ để quan sát và gỡ lỗi: đọc xong giá trị có thể đã đổi ([Bài 52](52-smart-pointer-da-luong.md)). VD 1 và VD 3 |

Hai dòng cần nói thêm vì hay bị hỏi tiếp.

Dòng 2: chữ ký `void thai(const Thot& t)` còn có lợi là **không áp đặt** cách quản lý. Hàm chạy được với thớt nằm trên stack, trong `unique_ptr`, hay trong `shared_ptr` (truyền `*p`). Chữ ký `void thai(std::shared_ptr<Thot>)` thì bắt mọi nơi gọi phải dùng `shared_ptr`, dù hàm không hề sở hữu gì.

Dòng 8: trước C++17, lời gọi `f(std::shared_ptr<T>(new T), g())` có thể rò rỉ nếu `g()` ném ngoại lệ vào giữa `new T` và việc bọc vào `shared_ptr`, vì chuẩn cho phép chen thứ tự đánh giá hai đối số. Từ C++17 chuẩn cấm kiểu chen đó. Mình thử cả `-std=c++14` lẫn `-std=c++17` trên g++ 11: đều **không** rò rỉ, nên mình không có lỗi chạy thật để cho bạn xem. Lý do thực tế để chuộng `make_shared` vẫn còn: ít cấp phát hơn, và không còn chữ `new` trần.

### 4. Khi nào KHÔNG nên dùng

| Loại | Đừng dùng khi | Dùng gì thay |
|---|---|---|
| `unique_ptr` | Đối tượng sống được trên stack hay làm thành viên trực tiếp (không cần heap); hoặc thật sự có nhiều chủ | Biến thường / thành viên; `shared_ptr` |
| `shared_ptr` | Chỉ có một chủ rõ; chỉ cần truyền để dùng tạm; cấu trúc có vòng mà không phân được chiều; "cho chắc" | `unique_ptr`; `const T&`; tách chiều sở hữu và chiều nhìn |
| `weak_ptr` | Chủ chắc chắn sống lâu hơn người nhìn (tham chiếu rẻ hơn và đủ); hoặc bạn cần **giữ** đối tượng sống | `T&` / `T*`; `shared_ptr` |
| `T*` / `T&` | Người nhận có thể **sống lâu hơn** chủ (lưu lại trong đối tượng sống lâu, gọi lại sau); hoặc bạn định `delete` nó | `weak_ptr`; `unique_ptr` nếu muốn nhận quyền |

!!! warning "Hay nhầm: dựng nhiều `shared_ptr` từ cùng một con trỏ thô"
    Mỗi `shared_ptr<Thot>(tho)` tự lập **khối điều khiển riêng** ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)) nên không biết nhau, và thớt bị xóa hai lần. Muốn thêm người giữ thì **copy một `shared_ptr` có sẵn**. Mình chạy bản sai ở cuối phần 💻.

## 💻 Ví dụ code

### Ví dụ 1: một chủ, truyền để dùng tạm, rồi nhiều chủ (tình huống 1, 2, 3, 7, 10)

`muaThot` là factory (hàm chuyên tạo đối tượng, [Bài 35](../nhom-4-oop-patterns/35-pattern-singleton-factory.md)): trả `unique_ptr` (1). `thai` chỉ nhìn (2). `thaiSai` nhận `shared_ptr` theo giá trị chỉ để xem, để thấy chi phí (3). Rồi thớt được nâng lên `shared_ptr` và hai `DauBep` cùng giữ (4): hàm tạo của `DauBep` nhận một `shared_ptr` và copy vào thành viên `thot`.

```cpp
#include <iostream>
#include <memory>
#include <string>
#include <utility>

struct Thot {
    std::string ten;
    Thot(const std::string& t) { ten = t; std::cout << "tao " << ten << "\n"; }
    ~Thot() { std::cout << "huy " << ten << "\n"; }
};

std::unique_ptr<Thot> muaThot(const std::string& ten) {      // (1)
    return std::make_unique<Thot>(ten);
}
void thai(const Thot& t) {                                   // (2)
    std::cout << "thai tren " << t.ten << "\n";
}
void thaiSai(std::shared_ptr<Thot> t) {                      // (3)
    std::cout << "thaiSai: use_count = " << t.use_count() << "\n";
}
struct DauBep {                                              // (4)
    std::shared_ptr<Thot> thot;
    DauBep(const std::shared_ptr<Thot>& th) { thot = th; }
};

int main() {
    auto t = muaThot("thot-go");                             // (5)
    thai(*t);                                                // (6)
    std::shared_ptr<Thot> chung = std::move(t);              // (7)
    std::cout << "t con giu: " << (t != nullptr) << ", use_count = " << chung.use_count() << "\n";
    thaiSai(chung);                                          // (8)
    thai(*chung);                                            // (9)
    DauBep an(chung);                                        // (10)
    DauBep binh(chung);
    std::cout << "chung + an + binh: use_count = " << chung.use_count() << "\n";
    chung.reset();                                           // (11)
    an.thot.reset();                                         // (12)
    std::cout << "con binh giu: use_count = " << binh.thot.use_count() << "\n";
    binh.thot.reset();                                       // (13)
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng** (cột cuối là số `shared_ptr` đang giữ thớt)

| Dòng | Chuyện gì xảy ra | Số người giữ |
|---|---|---|
| (5) | `muaThot` tạo thớt, `return` trao quyền cho `t`. In `tao thot-go` | 1 (`t`, kiểu `unique_ptr`) |
| (6) | `*t` là chính thớt; `thai` nhận `const Thot&`, chỉ đọc. In `thai tren thot-go` | không đổi |
| (7) | `std::move(t)` trao thớt cho `chung` (một `shared_ptr`); `t` thành `nullptr`. In `t con giu: 0, use_count = 1` | 1 |
| (8) | `thaiSai(chung)` copy `shared_ptr` vào tham số: trong hàm đếm là 2, ra khỏi hàm về lại 1 | 2 rồi 1 |
| (9) | `thai(*chung)` không đụng tới bộ đếm | 1 |
| (10) | Hai `DauBep` mỗi người copy một thẻ. In `... use_count = 3` (`chung`, `an.thot`, `binh.thot`) | 3 |
| (11), (12) | `chung`, rồi `an.thot` buông thẻ. In `con binh giu: use_count = 1` | 2 rồi 1 |
| (13) | `binh.thot` buông thẻ cuối: đếm về 0, hàm hủy chạy, in `huy thot-go`. Rồi `het main` | 0 |

**Kết quả khi chạy:**

```text
tao thot-go
thai tren thot-go
t con giu: 0, use_count = 1
thaiSai: use_count = 2
thai tren thot-go
chung + an + binh: use_count = 3
con binh giu: use_count = 1
huy thot-go
het main
```

Dòng `thaiSai: use_count = 2` là cái giá của việc truyền `shared_ptr` để xem: một lần tăng và một lần giảm bộ đếm nguyên tử, chỉ để đọc `ten`. `thai(*chung)` ở (9) làm đúng việc đó mà không đụng bộ đếm. Mình chạy thêm với AddressSanitizer và UBSan: sạch, thoát mã 0. Tương tự, `thai` không nên nhận `const std::unique_ptr<Thot>&`: nó sẽ bắt thớt phải nằm trong `unique_ptr`, trong khi `const Thot&` nhận được cả thớt trên stack lẫn trong `shared_ptr`.

### Ví dụ 2: ba cách nối cha-con (tình huống 5, 6)

Mỗi kiểu nút có `con` và `cha`, kèm một **biến đếm số nút còn sống** (cộng ở hàm tạo, trừ ở hàm hủy): cách đơn giản nhất để biết có rò rỉ hay không. `NutA` dùng `shared_ptr` cả hai chiều, `NutB` cha giữ con bằng `unique_ptr` và con nhìn cha bằng con trỏ thô, `NutC` cha giữ con bằng `shared_ptr` và con nhìn cha bằng `weak_ptr`.

```cpp
#include <iostream>
#include <memory>

int songA = 0, songB = 0, songC = 0;                        // (1)

struct NutA {                                               // (2) cả hai chiều là shared_ptr
    std::shared_ptr<NutA> con, cha;
    NutA() { ++songA; }
    ~NutA() { --songA; }
};
struct NutB {                                               // (3) cha giữ con, con nhìn cha
    std::unique_ptr<NutB> con;
    NutB* cha = nullptr;
    NutB() { ++songB; }
    ~NutB() { --songB; }
};
struct NutC {                                               // (4) shared_ptr xuôi, weak_ptr ngược
    std::shared_ptr<NutC> con;
    std::weak_ptr<NutC> cha;
    NutC() { ++songC; }
    ~NutC() { --songC; }
};

int main() {
    {
        auto a = std::make_shared<NutA>();
        a->con = std::make_shared<NutA>();
        a->con->cha = a;                                    // (5)
    }
    std::cout << "A: con song " << songA << "\n";
    {
        auto b = std::make_unique<NutB>();
        b->con = std::make_unique<NutB>();
        b->con->cha = b.get();                              // (6)
        std::cout << "B: con tro nguoc dung cha? " << (b->con->cha == b.get()) << "\n";
    }
    std::cout << "B: con song " << songB << "\n";
    {
        auto c = std::make_shared<NutC>();
        c->con = std::make_shared<NutC>();
        c->con->cha = c;                                    // (7)
        std::cout << "C: lock() ve dung cha? " << (c->con->cha.lock() == c) << "\n";
    }
    std::cout << "C: con song " << songC << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai giữ ai |
|---|---|---|
| (5) | `a` giữ nút cha, nút cha giữ nút con, và `a->con->cha = a` bắt con **giữ lại cha** bằng `shared_ptr` | vòng: cha ⇄ con |
| hết khối A | `a` chết, trả một thẻ của cha; cha vẫn còn thẻ do con giữ. Không bộ đếm nào về 0 | 2 nút còn sống |
| (6) | `b->con->cha = b.get()`: con giữ **địa chỉ thô** của cha, không sở hữu. In `1` vì địa chỉ đúng | `unique_ptr` chỉ một chiều |
| hết khối B | `b` chết, xóa cha; hàm hủy của cha hủy thành viên `con` (một `unique_ptr`), xóa con | 0 nút còn sống |
| (7) | `c->con->cha = c`: con giữ `weak_ptr`, không cộng bộ đếm mạnh. `lock()` trả lại đúng cha, in `1` | `shared_ptr` xuôi, `weak_ptr` ngược |
| hết khối C | `c` chết, đếm của cha về 0 nên cha và con lần lượt bị hủy | 0 nút còn sống |

**Kết quả khi chạy:**

```text
A: con song 2
B: con tro nguoc dung cha? 1
B: con song 0
C: lock() ve dung cha? 1
C: con song 0
```

Kiểu A còn **2 nút sống** sau khi không ai tới được chúng: rò rỉ. Mình chạy thêm với `-fsanitize=address`: LeakSanitizer báo `SUMMARY: AddressSanitizer: 96 byte(s) leaked in 2 allocation(s)`, đúng hai nút của A (B và C không bị báo). Chương trình vẫn thoát mã 0, nên đây là lỗi **im lặng**: cách bắt là đếm nút sống như trên, hoặc dùng LeakSanitizer.

Chọn B hay C? Nếu nút con **chỉ** được nút cha giữ, kiểu B đơn giản và rẻ nhất. Nếu nút con có thể bị giữ riêng ở nơi khác và sống lâu hơn nút cha, hãy dùng C: `lock()` cho biết cha còn hay không, còn con trỏ thô trong B sẽ treo.

### Ví dụ 3: cache bằng `weak_ptr` theo khóa (tình huống 4, 10)

Khác `Kho` một ảnh ở [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md), bản này tra theo **tên tệp** bằng `std::map` ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)). `lay` trả `shared_ptr<Anh>`: ai dùng ảnh thì giữ nó sống, còn cache chỉ giữ `weak_ptr` (5). Mình chạy với AddressSanitizer và UBSan: sạch. `cache_[ten]` chèn một `weak_ptr` rỗng nếu khóa chưa có (đúng như `operator[]` ở Bài 18), rồi (3) gán đè khi ta tạo ảnh mới.

```cpp
#include <iostream>
#include <map>
#include <memory>
#include <string>

struct Anh {
    std::string ten;
    Anh(const std::string& t) { ten = t; std::cout << "nap " << ten << " tu dia\n"; }
    ~Anh() { std::cout << "go " << ten << " khoi bo nho\n"; }
};

class KhoAnh {
public:
    std::shared_ptr<Anh> lay(const std::string& ten) {
        std::shared_ptr<Anh> a = cache_[ten].lock();         // (1)
        if (a) {
            std::cout << "cache trung: " << ten << "\n";
        } else {
            a = std::make_shared<Anh>(ten);                  // (2)
            cache_[ten] = a;                                 // (3)
        }
        return a;
    }
    std::size_t soMuc() const { return cache_.size(); }
    std::size_t soMucSong() const {                          // (4)
        std::size_t dem = 0;
        for (const auto& kv : cache_) {
            if (!kv.second.expired()) ++dem;
        }
        return dem;
    }

private:
    std::map<std::string, std::weak_ptr<Anh>> cache_;        // (5)
};

int main() {
    KhoAnh kho;
    auto a1 = kho.lay("meo.png");
    auto a2 = kho.lay("meo.png");
    std::cout << "use_count = " << a1.use_count() << "\n";
    auto c = kho.lay("cho.png");
    std::cout << "so muc = " << kho.soMuc() << ", con song = " << kho.soMucSong() << "\n";
    c.reset();                                               // (6)
    std::cout << "so muc = " << kho.soMuc() << ", con song = " << kho.soMucSong() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai giữ ảnh |
|---|---|---|
| `a1 = lay("meo.png")` | (1) chưa có khóa: `lock()` trả rỗng, vào nhánh `else`: (2) nạp ảnh, in `nap meo.png tu dia`; (3) cache ghi nhớ bằng `weak_ptr` | `a1` |
| `a2 = lay("meo.png")` | `lock()` trả `shared_ptr` thật nên in `cache trung`; `use_count` thành 2 | `a1`, `a2` |
| `c = lay("cho.png")` | Khóa mới: nạp `cho.png`. `soMuc() = 2`, `soMucSong() = 2` (4) | `c` |
| (6) `c.reset()` | `c` là chủ duy nhất nên ảnh bị xóa **ngay**, in `go cho.png ...`: cache không cản vì chỉ nhìn | không ai |
| dòng in sau (6) | Mục `cho.png` **vẫn nằm trong map** (là một `weak_ptr` hết hạn): `soMuc() = 2` nhưng `soMucSong() = 1` | |
| hết `main` | `a2` rồi `a1` chết, in `go meo.png ...` | |

**Kết quả khi chạy:**

```text
nap meo.png tu dia
cache trung: meo.png
use_count = 2
nap cho.png tu dia
so muc = 2, con song = 2
go cho.png khoi bo nho
so muc = 2, con song = 1
go meo.png khoi bo nho
```

**Thử thay đổi: cho cache giữ `shared_ptr`** (đổi (5) thành `std::map<std::string, std::shared_ptr<Anh>>`, bỏ `.lock()` ở (1), bỏ hàm `soMucSong`). Mình đã chạy: `use_count` thành **3** (cache cũng là một người giữ), và sau `c.reset()` **không** có dòng `go cho.png`; cả hai dòng `go` chỉ xuất hiện cuối `main`, khi `kho` bị hủy. Cache là một chủ vĩnh viễn nên ảnh không bao giờ được thả trong lúc chương trình chạy: cache phình mãi. Đổi lại, cache bằng `weak_ptr` có hai việc phải tự lo: mục hết hạn cần dọn (duyệt map, `erase` các mục `expired()`), và nhiều luồng cùng dùng cache cần khóa ([Bài 54](54-container-da-luong.md)).

!!! info "Bạn biết Go?"
    Go chạy cache kiểu này bằng `map[string]*Anh`: map giữ con trỏ nên ảnh sống mãi (như cache giữ `shared_ptr`). Từ Go 1.24 có gói `weak` với `weak.Make(p)` và `w.Value()` (trả `nil` khi đối tượng đã bị GC dọn): đúng vai trò `weak_ptr`/`lock()`. Mình chạy thử một chương trình nhỏ ở máy này, năm lần liền: trước khi bỏ biến thì `Value()` khác `nil`, sau `runtime.GC()` thì là `nil`. GC không hứa lúc nào dọn, nên đừng dựa vào thời điểm.

### Ví dụ 4: chi phí thật, và cái giá của `make_shared` (tình huống 8)

Ta đo bằng cách thay `operator new` toàn cục như ở [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (`malloc`/`free` là cách xin và trả heap kiểu C, chỉ để minh họa), nhưng thêm một biến cộng số **byte** đang sống: `operator new` cộng `n`, và bản `operator delete` có tham số kích thước (`std::size_t n`) trừ `n` (g++ 11 ở chế độ C++17 có gọi bản này, bằng chứng là số byte về 0 ở cuối). `Nong` có một mảng 4096 byte (4) để thấy rõ khối nào còn nằm lại.

```cpp
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>

int soLanNew = 0;                                             // (1)
std::size_t byteDangSong = 0;                                 // (2)

void* operator new(std::size_t n) {                           // (3)
    ++soLanNew;
    byteDangSong += n;
    return std::malloc(n);
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t n) noexcept {
    byteDangSong -= n;
    std::free(p);
}

struct Nong {
    char dem[4096];                                           // (4)
    ~Nong() { std::cout << "  ham huy Nong chay\n"; }
};

int main() {
    std::cout << "sizeof: Nong* = " << sizeof(Nong*)
              << ", unique_ptr = " << sizeof(std::unique_ptr<Nong>)
              << ", shared_ptr = " << sizeof(std::shared_ptr<Nong>)
              << ", weak_ptr = " << sizeof(std::weak_ptr<Nong>) << "\n";
    int truoc = soLanNew;
    { auto u = std::make_unique<Nong>(); }                    // (5)
    std::cout << "make_unique:           " << soLanNew - truoc << " lan new\n";
    truoc = soLanNew;
    { auto s = std::make_shared<Nong>(); }                    // (6)
    std::cout << "make_shared:           " << soLanNew - truoc << " lan new\n";
    truoc = soLanNew;
    { std::shared_ptr<Nong> s(new Nong); }                    // (7)
    std::cout << "shared_ptr<Nong>(new): " << soLanNew - truoc << " lan new\n";

    std::cout << "make_shared, con weak_ptr cuoi:\n";
    {
        std::size_t goc = byteDangSong;
        auto s = std::make_shared<Nong>();
        std::weak_ptr<Nong> w = s;
        s.reset();                                            // (8)
        std::cout << "  het chu: con giu " << byteDangSong - goc << " byte\n";
        w.reset();                                            // (9)
        std::cout << "  het nguoi nhin: con giu " << byteDangSong - goc << " byte\n";
    }
    std::cout << "shared_ptr<Nong>(new), con weak_ptr cuoi:\n";
    {
        std::size_t goc = byteDangSong;
        std::shared_ptr<Nong> s(new Nong);
        std::weak_ptr<Nong> w = s;
        s.reset();
        std::cout << "  het chu: con giu " << byteDangSong - goc << " byte\n";
        w.reset();
        std::cout << "  het nguoi nhin: con giu " << byteDangSong - goc << " byte\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số đo |
|---|---|---|
| dòng `sizeof` | In kích thước bốn kiểu con trỏ | 8, 8, 16, 16 |
| (5), (6), (7) | Mỗi khối `{ }` tạo một đối tượng và để nó chết ngay; `soLanNew` cho biết lần xin heap | 1, 1, 2 |
| (8) | Với `make_shared`: `s.reset()` làm bộ đếm mạnh về 0 nên hàm hủy `Nong` chạy, nhưng `w` còn nhìn nên **cả khối** (đối tượng và khối điều khiển dính liền) chưa được trả | 4112 byte còn giữ |
| (9) | `w.reset()` buông người nhìn cuối, khối được trả | 0 byte |
| 2 dòng sau | Với `shared_ptr<Nong>(new Nong)`: đối tượng và khối điều khiển là hai khối riêng, nên sau `s.reset()` đối tượng đã được trả, chỉ còn khối điều khiển nhỏ | 24 byte rồi 0 |

**Kết quả khi chạy:**

```text
sizeof: Nong* = 8, unique_ptr = 8, shared_ptr = 16, weak_ptr = 16
  ham huy Nong chay
make_unique:           1 lan new
  ham huy Nong chay
make_shared:           1 lan new
  ham huy Nong chay
shared_ptr<Nong>(new): 2 lan new
make_shared, con weak_ptr cuoi:
  ham huy Nong chay
  het chu: con giu 4112 byte
  het nguoi nhin: con giu 0 byte
shared_ptr<Nong>(new), con weak_ptr cuoi:
  ham huy Nong chay
  het chu: con giu 24 byte
  het nguoi nhin: con giu 0 byte
```

Đây là kết quả của g++ 11.4 với libstdc++ trên máy 64-bit này; chuẩn không hứa các con số (nhất là 16, 4112, 24), nên chỉ cái **mẫu** đáng nhớ: `unique_ptr` bằng con trỏ thô, `shared_ptr` gấp đôi, `make_shared` thường xin heap một lần thay vì hai. Mình chạy cùng chương trình ở `-O2` và với ASan + UBSan: kết quả y hệt, thoát mã 0.

Hệ quả cho tình huống 8: nếu đối tượng **lớn** và có `weak_ptr` sống lâu (như cache), `make_shared` giữ cả khối lớn đến khi `weak_ptr` cuối chết, dù hàm hủy đã chạy. Khi đó `shared_ptr<T>(new T)` thả đối tượng sớm hơn. Còn lại, mặc định vẫn là `make_shared`.

### Ví dụ 5: bộ xóa tùy chỉnh và mảng (tình huống 9)

**Tệp (file)** trong C là kiểu `FILE*`: `std::fopen` mở tệp theo tên, `std::fclose` đóng tệp (giống `f.Close()` của Go). Để chạy không đụng đĩa, ta dùng `std::tmpfile()`: tạo tệp tạm tự xóa khi đóng và trả `FILE*`; `std::fputs` ghi một chuỗi, `std::ftell` cho biết đã ghi bao nhiêu byte. Đóng tệp không phải `delete`, nên ta cần **bộ xóa tùy chỉnh (custom deleter)**: kiểu thứ hai của `unique_ptr<T, BoXoa>`, nói "khi chết thì gọi cái này". Bộ xóa ở đây là một `struct` có `operator()` (1), (2): hàm đặc biệt để viết `doiTuong(x)` như gọi hàm, giống `operator*` ở [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md). Loại `struct` như vậy gọi là **functor (hàm đối tượng)**.

```cpp
#include <cstdio>
#include <iostream>
#include <memory>

struct DongTep {                                              // (1)
    void operator()(std::FILE* f) const {                     // (2)
        std::cout << "dong tep\n";
        std::fclose(f);
    }
};

int main() {
    std::unique_ptr<std::FILE, DongTep> tep(std::tmpfile());  // (3)
    if (!tep) return 1;
    std::fputs("xin chao", tep.get());                        // (4)
    std::cout << "da ghi " << std::ftell(tep.get()) << " byte\n";
    std::unique_ptr<int[]> mang = std::make_unique<int[]>(3); // (5)
    mang[2] = 7;
    std::cout << "mang[2] = " << mang[2] << "\n";
    std::cout << "functor: " << sizeof(std::unique_ptr<std::FILE, DongTep>)
              << ", con tro ham: "
              << sizeof(std::unique_ptr<std::FILE, int (*)(std::FILE*)>) << "\n";   // (6)
    std::cout << "het main\n";
    return 0;
}                                                             // (7)
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Tài nguyên |
|---|---|---|
| (3) | `tep` giữ `FILE*` do `tmpfile()` trả; kiểu của nó mang theo `DongTep`. Nếu không tạo được tệp, `tmpfile()` trả `nullptr`, `!tep` đúng và `main` thoát mã 1 | tệp mở |
| (4) | `tep.get()` đưa `FILE*` thô cho `fputs` (chỉ nhìn, như `get()` ở Bài 09); `ftell` báo 8 byte (`xin chao` có 8 ký tự) | đã ghi 8 byte |
| (5) | `unique_ptr<int[]>` giữ 3 số `int`, hàm hủy sẽ gọi `delete[]` | mảng ở heap |
| (6) | In hai kích thước: bộ xóa là functor rỗng thì `unique_ptr` vẫn 8 byte; bộ xóa là con trỏ hàm (`int (*)(std::FILE*)`, [Bài 04](../nhom-1-nen-tang-bo-nho/04-con-tro-ham.md)) thì phải chứa thêm con trỏ nên 16 byte | |
| (7) `}` | `mang` bị `delete[]`; `tep` chết: gọi `DongTep`, in `dong tep`, rồi `fclose` | cả hai đã trả |

**Kết quả khi chạy:**

```text
da ghi 8 byte
mang[2] = 7
functor: 8, con tro ham: 16
het main
dong tep
```

`dong tep` in **sau** `het main`: bộ xóa chạy ở `}` của `main`, đúng như hàm hủy của `Cay`. Nếu cần đóng tệp nhưng quên bộ xóa, `unique_ptr<std::FILE>` mặc định sẽ gọi `delete` lên một `FILE*`, là cách đóng sai. Số 8 và 16 là của g++ này, chuẩn không hứa; ý cần nhớ là **bộ xóa không trạng thái thì miễn phí**.

### Bản sai: dựng hai `shared_ptr` từ cùng một con trỏ thô (không chạy trong bộ kiểm tra)

Lỗi này biên dịch sạch cảnh báo. Mình chạy với AddressSanitizer và báo lại đúng những gì nó in.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <memory>

struct Thot { ~Thot() { std::cout << "huy Thot\n"; } };

int main() {
    Thot* tho = new Thot;
    std::shared_ptr<Thot> a(tho);     // (1) a lập khối điều khiển riêng
    std::shared_ptr<Thot> b(tho);     // (2) b lập một khối nữa: hai khối không biết nhau
    std::cout << a.use_count() << " " << b.use_count() << "\n";   // (3)
    return 0;
}                                      // (4) mỗi khối xóa một lần
```

(3) in `1 1`: mỗi `shared_ptr` tin mình là chủ duy nhất. Đến (4) cả hai cùng xóa. ASan báo `ERROR: AddressSanitizer: attempting double-free`, có dòng `std::_Sp_counted_ptr<Thot*, ...>::_M_dispose()`. Chạy trần trên máy mình thì abort với `free(): double free detected in tcache 2`, mã thoát 134; đó là hành vi không xác định nên chuẩn không hứa gì.

Lỗi thứ hai của tình huống 9: `std::unique_ptr<int> p(new int[4]);` (kiểu thiếu `[]`). Mình chạy trần: in bình thường, thoát mã 0, **không báo gì**. Với ASan: `ERROR: AddressSanitizer: alloc-dealloc-mismatch (operator new [] vs operator delete)`. Chuẩn nói đây là hành vi không xác định, nên "chạy êm" không chứng minh gì. Cách đúng: `unique_ptr<int[]>` hoặc `std::vector<int>`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Khi nào em dùng `unique_ptr`, khi nào `shared_ptr`? Sao không dùng `shared_ptr` hết cho an toàn, như bên Go?"
    Mình bắt đầu từ câu hỏi "ai sở hữu". Một chủ rõ ràng thì `unique_ptr`: không tốn thêm so với con trỏ thô và nói rõ ai xóa. `shared_ptr` chỉ khi quyền sở hữu **thật sự** chia sẻ. Go có GC dọn cả vòng, còn `shared_ptr` đếm tham chiếu nên vòng thì rò rỉ; mỗi lần copy hay hủy là phép nguyên tử, mỗi đối tượng thêm khối điều khiển, và không còn thấy ai sở hữu. "An toàn" ở đây thật ra là dời lỗi từ "xóa sớm" sang "không bao giờ xóa".

??? question "Hàm chỉ đọc đối tượng thì nhận tham số kiểu gì? Nhận `shared_ptr` theo giá trị có sao không?"
    Chỉ đọc thì `const T&`, hoặc `T*` nếu cho phép "không có". Nhận `shared_ptr` theo giá trị làm mỗi lần gọi tăng rồi giảm bộ đếm nguyên tử chỉ để xem, và bắt mọi nơi gọi phải dùng `shared_ptr`. Chỉ nhận `shared_ptr` khi hàm thật sự **trở thành một chủ** (lưu lại dùng về sau).

??? question "Lớp có con trỏ ngược về cha thì dùng gì? Thế nếu con có thể sống lâu hơn cha? Phát hiện vòng tham chiếu thế nào?"
    Cha giữ con bằng `unique_ptr`, con giữ cha bằng con trỏ thô: con không sống lâu hơn cha vì chỉ cha giữ nó. Nếu con còn được giữ riêng ở nơi khác (cha do `shared_ptr` quản lý), con giữ `weak_ptr` tới cha và `lock()` trước khi dùng, vì con trỏ thô lúc đó sẽ treo. Phát hiện vòng: đếm số đối tượng sống (cộng ở hàm tạo, trừ ở hàm hủy) và kiểm về 0 trong test, hoặc chạy LeakSanitizer.

??? question "`make_shared` khác `shared_ptr<T>(new T)` thế nào, và nhược điểm của `make_shared`?"
    `make_shared` thường chỉ xin heap một lần cho cả đối tượng lẫn khối điều khiển; cách còn lại là hai lần (mình đo được 1 và 2), và `make_shared` không để lộ `new` trần. Nhược điểm: đối tượng và khối điều khiển dính liền nên bộ nhớ của đối tượng chỉ được trả khi `weak_ptr` cuối cùng chết, dù hàm hủy đã chạy. Với đối tượng lớn trong cache sống lâu, điều này đáng cân nhắc. (Đây là chi tiết cài đặt, chuẩn không bắt buộc.)

??? question "Em dựng hai `shared_ptr` từ cùng một con trỏ thô thì chuyện gì xảy ra?"
    Mỗi `shared_ptr` lập khối điều khiển riêng và tin mình là chủ duy nhất (`use_count` đều là 1), nên khi chết cả hai cùng `delete`: double free, hành vi không xác định (ASan báo `attempting double-free`). Muốn thêm người giữ thì copy một `shared_ptr` có sẵn. Cũng đừng dựng `shared_ptr` từ `this` ([Bài 52](52-smart-pointer-da-luong.md) có cách đúng).

??? question "Factory nên trả kiểu gì, và `unique_ptr` có tốn hơn con trỏ thô không?"
    Trả `unique_ptr<T>`: nơi gọi giữ một chủ hoặc gán sang `shared_ptr` được, còn trả `shared_ptr` thì ép mọi nơi gọi trả chi phí. Với bộ xóa mặc định hay bộ xóa không trạng thái, `unique_ptr` cùng cỡ con trỏ thô (mình đo 8 byte); bộ xóa là con trỏ hàm thì to gấp đôi (16 byte).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `shared_ptr` cho mọi thứ \"cho chắc\", hoặc truyền nó theo giá trị chỉ để xem"
    Bạn trả khối điều khiển và phép nguyên tử (Ví dụ 1, dòng `thaiSai`), áp đặt `shared_ptr` lên mọi nơi gọi, và mất khả năng thấy ai sở hữu. Bắt đầu bằng `unique_ptr`; hàm chỉ xem nhận `const T&`.

!!! warning "Lỗi 2: Nối hai chiều của một quan hệ bằng `shared_ptr`"
    Kiểu A ở Ví dụ 2: chương trình thoát mã 0 mà nút còn sống mãi. Tách chiều sở hữu (`unique_ptr`/`shared_ptr`) khỏi chiều nhìn (con trỏ thô/`weak_ptr`).

!!! warning "Lỗi 3: Giữ con trỏ thô tới thứ có thể chết trước"
    Con trỏ thô chỉ an toàn khi chủ sống lâu hơn nó. Nếu bạn lưu nó trong một đối tượng sống lâu (danh sách người nghe, cache), hãy đổi sang `weak_ptr`.

!!! warning "Lỗi 4: `unique_ptr<T>` cho mảng, hoặc `shared_ptr` dựng từ con trỏ thô đã có chủ"
    Cả hai biên dịch sạch nhưng sai (mục "Bản sai"): dùng `unique_ptr<T[]>` hoặc `vector` cho mảng; copy `shared_ptr` có sẵn thay vì quay lại con trỏ thô.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="51" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Lớp `DichVu` cần gọi `Logger` do nơi khác tạo, quản lý và chắc chắn sống lâu hơn `DichVu`. `DichVu` chỉ gọi hàm ghi log. Thành viên nên có kiểu nào?

- `std::unique_ptr<Logger>`, vì mọi thành viên con trỏ đều nên là smart pointer
- `std::shared_ptr<Logger>`, vì dùng chung thì phải dùng loại chia sẻ
- `Logger&`, vì chỉ cần dùng và `Logger` sống lâu hơn nên không cần sở hữu
- `std::weak_ptr<Logger>`, vì mọi chỗ chỉ nhìn đối tượng đều nên dùng loại này

<p class="giai-thich" markdown>Câu hỏi gốc là "ai sở hữu": `Logger` đã có chủ ở nơi khác và sống lâu hơn, nên `DichVu` chỉ cần nhìn, và tham chiếu là đủ, rẻ nhất. `unique_ptr` sẽ nói rằng `DichVu` là chủ và xóa `Logger` khi chết, sai với đề. `shared_ptr` ép thêm khối điều khiển và đếm nguyên tử cho một quan hệ chỉ để dùng. `weak_ptr` hợp khi người nhìn có thể sống lâu hơn chủ, mà đề đã nói ngược lại.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Kho ảnh cất tạm ảnh đã nạp theo tên tệp để lần sau dùng lại, nhưng ảnh nào không ai dùng nữa thì phải được giải phóng. Giá trị trong cache nên là gì?

- `std::weak_ptr<Anh>`, còn `lay` trả `shared_ptr<Anh>`
- `std::shared_ptr<Anh>`, để ảnh luôn có sẵn cho lần dùng sau
- `std::unique_ptr<Anh>`, vì mỗi tên tệp chỉ có một ảnh duy nhất
- `Anh*`, và cache tự `delete` khi thấy ảnh hết hạn dùng

<p class="giai-thich" markdown>Cache chỉ cần nhìn, còn ai đang dùng ảnh mới là chủ, nên `weak_ptr` để ảnh được giải phóng khi người cuối buông. Cache giữ `shared_ptr` thì cache là một chủ vĩnh viễn: ảnh không bao giờ được giải phóng và cache phình mãi. `unique_ptr` làm cache là chủ duy nhất nên không trả ảnh chung cho người dùng được. Con trỏ thô bắt cache tự biết khi nào xóa, trong khi nó không biết còn ai đang dùng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau (`std::cout` in `song` ở cuối). In ra gì?

```text
int song = 0;
struct N {
    std::shared_ptr<N> con;
    std::shared_ptr<N> cha;
    N()  { ++song; }
    ~N() { --song; }
};
{
    auto a = std::make_shared<N>();
    a->con = std::make_shared<N>();
    a->con->cha = a;
}
std::cout << song;
```

- `0`, vì `a` chết ở `}` nên cả hai nút bị hủy
- `1`, vì chỉ nút con còn thẻ do cha giữ nên còn lại một nút
- Không biên dịch được, vì hai nút trỏ vào nhau
- `2`, vì mỗi nút còn một thẻ do nút kia giữ

<p class="giai-thich" markdown>Cha giữ con bằng `con`, con giữ lại cha bằng `cha`: một vòng `shared_ptr`. Khi `a` chết ở `}` nó chỉ trả một thẻ, nút cha vẫn còn thẻ do con giữ, và nút con vẫn còn thẻ do cha giữ; hai bộ đếm đứng ở 1, không hủy nút nào, nên `song` là 2. Kết quả `0` tin rằng biến chết là đủ để đối tượng chết. Kết quả `1` tưởng cha chết được còn con ở lại, nhưng cha cũng không chết. Hai `shared_ptr` trỏ vào nhau vẫn biên dịch bình thường, lỗi chỉ lộ lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau (`T` là một kiểu bất kỳ, `use_count()` đọc bộ đếm mạnh). Chương trình in ra gì?

```text
void f(std::shared_ptr<T> p) { std::cout << p.use_count(); }
void g(const T& t)           { std::cout << "g"; }
auto a = std::make_shared<T>();
f(a);
g(*a);
f(a);
std::cout << a.use_count();
```

- `1g11`
- `2g21`
- `2g22`
- `1g21`

<p class="giai-thich" markdown>`f` nhận theo giá trị nên mỗi lần gọi copy `a` và bộ đếm là 2 trong hàm, rồi về 1 khi hàm xong. `g` nhận `const T&` nên không đụng bộ đếm. Vì thế in `2`, `g`, `2`, rồi `1` ở dòng cuối, tức `2g21`. Dãy bắt đầu bằng `1` quên rằng tham số là một bản copy. Dãy kết thúc bằng `2` tưởng bản copy vẫn sống sau khi hàm trả về, nhưng tham số chết ở `}` của hàm.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Hàm `taoHinh(loai)` tạo một đối tượng đa hình và trao cho nơi gọi; chưa biết nơi gọi sẽ giữ một mình hay chia sẻ. Kiểu trả về nên là gì?

- `std::shared_ptr<Hinh>`, vì nơi gọi nào cũng dùng được
- `Hinh*`, vì nhẹ nhất và nơi gọi tự quyết định
- `Hinh&`, vì đối tượng sống trong hàm rồi trả ra ngoài
- `std::unique_ptr<Hinh>`, vì còn gán sang `shared_ptr` được

<p class="giai-thich" markdown>`unique_ptr` nói rõ quyền sở hữu được trao cho nơi gọi, rẻ như con trỏ thô, và gán được sang `shared_ptr` nếu nơi gọi cần chia sẻ; chiều ngược lại thì không. Trả `shared_ptr` ép mọi nơi gọi trả chi phí dù chỉ cần một chủ. Trả `Hinh*` không nói ai phải `delete`, nên dễ rò rỉ hay xóa hai lần. Trả `Hinh&` tới đối tượng tạo trong hàm là tham chiếu treo, vì đối tượng chết cùng hàm.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đối tượng tạo bằng `std::make_shared<T>()`. `shared_ptr` cuối cùng vừa bị `reset()`, nhưng vẫn còn một `weak_ptr` đang nhìn nó. Điều nào đúng trên các cài đặt phổ biến?

- Hàm hủy đã chạy, còn vùng nhớ chứa đối tượng thì chưa trả
- Hàm hủy chưa chạy, vì còn một `weak_ptr` đang nhìn đối tượng
- Hàm hủy đã chạy và vùng nhớ cũng đã được trả hết ngay
- Hàm hủy chạy khi `weak_ptr` cuối bị hủy, cùng lúc với vùng nhớ

<p class="giai-thich" markdown>Hàm hủy chạy khi bộ đếm mạnh về 0, bất kể có `weak_ptr` hay không. Nhưng `make_shared` thường để đối tượng và khối điều khiển dính liền một khối, mà khối điều khiển còn cần cho `weak_ptr`, nên vùng nhớ chỉ được trả khi `weak_ptr` cuối biến mất (mình đo: 4112 byte còn giữ). `weak_ptr` không giữ đối tượng sống, nên hàm hủy không bị hoãn. Vùng nhớ cũng chưa trả hết, nên dãy "trả hết ngay" sai với `make_shared`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Đọc đoạn sau. Lỗi nằm ở đâu?

```text
Thot* tho = new Thot;
std::shared_ptr<Thot> a(tho);
std::shared_ptr<Thot> b(tho);
```

- `b` không biên dịch được, vì `tho` đã được `a` nhận
- Rò rỉ: không `shared_ptr` nào chịu trách nhiệm xóa `tho`
- Hai khối điều khiển riêng, nên `Thot` bị xóa hai lần
- Không có lỗi: bộ đếm của `a` và `b` tự cộng lại thành 2

<p class="giai-thich" markdown>`shared_ptr` dựng từ một con trỏ thô lập khối điều khiển mới và không biết có `shared_ptr` khác đã giữ cùng chỗ đó. Cả `a` và `b` đều tin mình là chủ duy nhất (`use_count` đều 1), nên khi chết cùng xóa `tho`: double free. Nó vẫn biên dịch được vì ngôn ngữ không kiểm tra điều đó. Hai bộ đếm nằm ở hai khối khác nhau nên không cộng được. Rò rỉ là chuyện ngược lại: ở đây `tho` bị xóa quá nhiều lần, không phải quá ít.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Câu hỏi gốc là **"ai sở hữu?"**: không cần heap thì không cần con trỏ; một chủ rõ → `unique_ptr` (mặc định); nhiều chủ thật → `shared_ptr`; chỉ dùng tạm → `const T&`/`T*` không sở hữu; nhìn lâu mà chủ có thể chết trước → `weak_ptr`.
2. Chi phí đo được: `unique_ptr` 8 byte như con trỏ thô, `shared_ptr` và `weak_ptr` 16 byte kèm khối điều khiển và phép nguyên tử; `make_shared` xin heap 1 lần, `shared_ptr<T>(new T)` 2 lần, nhưng `make_shared` giữ cả khối (đo 4112 byte) tới khi `weak_ptr` cuối chết.
3. Quan hệ hai chiều: tách chiều sở hữu (`unique_ptr`/`shared_ptr`) khỏi chiều nhìn (con trỏ thô/`weak_ptr`); hai `shared_ptr` trỏ nhau rò rỉ im lặng (đếm nút sống còn 2, LeakSanitizer báo), cache nên giữ `weak_ptr` và phải dọn mục hết hạn.
4. Factory trả `unique_ptr` (gán sang `shared_ptr` được, ngược lại thì không); hàm chỉ xem nhận `const T&`, không nhận `shared_ptr` theo giá trị (mỗi lần gọi tăng-giảm bộ đếm nguyên tử); tài nguyên không phải bộ nhớ dùng `unique_ptr<T, BoXoa>`, mảng dùng `unique_ptr<T[]>` hoặc `vector`.
5. Hai bẫy im lặng: dựng nhiều `shared_ptr` từ cùng một con trỏ thô (hai khối điều khiển, ASan báo `attempting double-free`) và `unique_ptr<int>` giữ `new int[4]` (ASan báo `alloc-dealloc-mismatch`); `shared_ptr` rải khắp nơi, "cho chắc", làm mờ vòng đời.
