# Bài 36 — Observer và Strategy: báo tin cho nhiều nơi, và đổi cách làm lúc chạy

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết **Observer** bằng giao diện `Quansat` (hàm thuần ảo `capNhat`) và `Chude` giữ danh sách; chạy thật hai cái bẫy: observer bị hủy mà chủ đề còn gọi (ASan báo `heap-use-after-free`), và observer tự hủy đăng ký ngay lúc chủ đề đang duyệt danh sách.
    - Dùng `std::weak_ptr` để chủ đề **không giữ observer sống** (`lock()` kiểm còn sống), duyệt trên bản sao danh sách, và viết bản gọn bằng `std::function`; biết khi nào chọn giao diện, khi nào chọn function; nhắc thứ tự gọi và thread-safety.
    - Viết **Strategy** ba cách (giao diện + `unique_ptr`, `std::function`/lambda, template), có bảng so sánh, nói rõ chỗ nào chỉ là xu hướng; thấy `std::sort` với comparator chính là Strategy; nêu đúng chi phí của `std::function` (có chương trình đếm lần cấp phát).
    - So với Go (channel, interface một hàm, hàm là giá trị hạng nhất; đã chạy Go 1.27.1); nhắc Decorator và RAII trong một đoạn.

**Bạn cần biết trước:** [Bài 33](33-da-hinh-virtual.md) (hàm thuần ảo, lớp trừu tượng, hàm hủy ảo), [Bài 34](34-template.md) (template lớp), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, `weak_ptr`, `lock()`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator bị vô hiệu, `erase`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function`, `sort`, remove-erase), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (ASan, UB).

## 🧠 Câu chuyện mở đầu

**Observer (người theo dõi)** giống tờ đăng ký nhận tin. Một cảm biến nhiệt độ có một tờ danh sách; màn hình phòng khách, màn hình bếp và còi báo nóng cùng ghi tên vào. Mỗi lần nhiệt độ đổi, cảm biến đọc danh sách và báo từng nơi. Cảm biến **không cần biết** nơi nhận là cái gì, chỉ biết "ai có tên trong danh sách thì gọi một hàm": nơi nhận mới thêm vào không phải sửa cảm biến.

**Strategy (chiến lược)** giống một tay cầm máy khoan có thể thay mũi: tay cầm lo phần chung, mũi khoan là phần đổi được. Đơn hàng cũng vậy: nó lo phần chung (lưu cân nặng), còn **cách tính phí vận chuyển** là thứ thay được lúc chạy mà không sửa đơn hàng.

!!! info "Chỗ nào ví von không còn đúng?"
    Bài này **rời xưởng đồ chơi** (bản vẽ và món) sang cảm biến, màn hình và đơn hàng, vì hai mẫu này hợp với các ví dụ đó hơn. Tờ đăng ký đời thường ghi tên người; trong C++ tờ đăng ký ghi **địa chỉ** hoặc `weak_ptr`, và địa chỉ có thể trỏ tới một nơi nhận đã bị phá bỏ (mục 2). Tay cầm và mũi khoan là đồ vật, còn Strategy ở C++ có ba cách "gắn mũi" khác chi phí (mục 6).

## 📖 Giải thích

### 1. Observer: giao diện `Quansat` và `Chude` giữ danh sách

Vấn đề: một đối tượng (**chủ đề**, subject) đổi, và nhiều nơi cần biết, mà ta không muốn chủ đề phụ thuộc vào từng nơi đó. Nếu cảm biến gọi thẳng từng màn hình, thêm nơi nhận là phải sửa cảm biến. Cách giải: chủ đề chỉ biết **một giao diện** và một danh sách.

Giao diện là lớp trừu tượng của [Bài 33](33-da-hinh-virtual.md): `Quansat` có hàm thuần ảo `capNhat(double)`. `Chude` giữ danh sách `Quansat*`, có `dangKy` (thêm), `huyDangKy` (bớt), và khi nhiệt độ đổi thì duyệt danh sách gọi `capNhat`. Ví dụ 1 viết đúng như vậy; ở đây danh sách chứa **con trỏ thô** (chưa an toàn, mục 2 nói vì sao).

### 2. Vòng đời: con trỏ thô tới observer rất nguy hiểm

Danh sách của `Chude` chỉ **mượn** địa chỉ; không ai bảo nó biết nơi nhận đã bị hủy. Nếu một `Quansat` bị hủy mà quên `huyDangKy`, `Chude` vẫn giữ địa chỉ cũ, và lần báo tin sau gọi `capNhat` trên đồ đã trả: hành vi không xác định ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)). Mình đã chạy thật ở Ví dụ 1, Thử thay đổi.

Hai cách chữa. Cách thủ công: observer luôn `huyDangKy` trước khi bị hủy (dễ quên, nhất là khi có ngoại lệ). Cách tự động: danh sách giữ `std::weak_ptr` (mục 3).

### 3. `weak_ptr`: chủ đề nhìn mà không giữ sống

Nhớ [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md): `weak_ptr` chỉ **nhìn**, không cộng bộ đếm mạnh, nên không giữ đối tượng sống; `lock()` trả `shared_ptr` thật nếu còn sống, rỗng nếu đã hủy. Danh sách của `Chude` đổi thành `vector<weak_ptr<Quansat>>`. Mỗi lần báo, `lock()` từng cái: rỗng thì bỏ qua và dọn khỏi danh sách, còn thì gọi `capNhat`.

Observer do `shared_ptr` quản lý ở nơi khác; hết đời thì mục của chúng được dọn khỏi danh sách ở lần báo sau, không ai phải nhớ gì (Ví dụ 2). Ví dụ 2 vẫn duyệt thẳng danh sách, nên `weak_ptr` không chữa bẫy thứ hai dưới đây.

**Bẫy thứ hai: observer tự hủy đăng ký ngay lúc `capNhat`.** Ví dụ: một observer "chỉ nhận một tin" gọi `huyDangKy(this)` trong `capNhat`. Lúc đó `Chude` đang duyệt chính danh sách mà `erase` làm iterator hỏng ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)): hành vi không xác định (chạy thật ở Ví dụ 1 và Ví dụ 3, Thử thay đổi).

Cách chữa phổ biến: **duyệt trên bản sao** của danh sách (Ví dụ 3, dòng (4)), nên `erase` trên bản gốc không làm hỏng vòng đang chạy. Cái giá: sao chép tốn thêm, và ai vừa hủy đăng ký vẫn có thể nhận nốt tin của lượt đó.

### 4. Chỉ nhắc: thứ tự gọi và thread-safety

**Thứ tự gọi**: với `vector` ở đây là thứ tự đăng ký, nhưng observer không nên dựa vào đó. **Thread-safety**: luồng A `dangKy` trong lúc luồng B đang báo tin là data race trên danh sách ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Thường khóa `mutex` khi sửa hoặc sao chép danh sách, rồi **nhả khóa trước khi gọi `capNhat`**, kẻo observer gọi lại `dangKy` thì có thể tự treo (khóa lại `mutex` đang giữ là hành vi không xác định). Bài không chạy phần này.

### 5. Bản gọn: `std::function` callback

**Callback (hàm gọi lại)** là một hàm bạn đưa cho nơi khác, để nơi đó gọi khi có việc (đã gặp ở [Bài 26](../nhom-3-da-luong/26-deadlock.md)). Ở [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) `std::function<void(double)>` là cái hộp chứa mọi thứ gọi được nhận `double`. Ví dụ 3 cho `CamBien` giữ danh sách các hộp ấy; nơi nhận chỉ là lambda, không cần viết lớp con. `dangKy` trả một **mã số** để sau `huyDangKy(ma)`, vì hai `std::function` không so sánh bằng nhau được để tìm "cái nào cần xóa".

Khi nào dùng cái nào: **giao diện** khi nơi nhận có "danh tính", nhiều thao tác hoặc trạng thái riêng (nhưng cần `weak_ptr` cho vòng đời, mục 3); **`std::function`** khi nơi nhận chỉ là một hành động nhỏ viết tại chỗ (nhưng lambda `[&x]` giữ tham chiếu nên có cùng bẫy treo; chữa bằng hủy đăng ký bằng mã số, hoặc bắt `weak_ptr`, cách này bài không chạy). Không bên nào tốt hơn tuyệt đối.

### 6. Strategy: đổi thuật toán lúc chạy, không sửa lớp dùng nó

Vấn đề: một lớp cần một "cách làm" thay được (tính phí vận chuyển, giảm giá, thứ tự sắp xếp), và ta không muốn sửa lớp mỗi khi có cách mới, cũng không muốn một chuỗi `if` dài. Strategy tách **cách làm** ra khỏi lớp dùng nó. Ví dụ 4 làm một việc (tính phí theo cân nặng) bằng ba cách:

1. **Giao diện đa hình + `unique_ptr`** ([Bài 33](33-da-hinh-virtual.md), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)): `ChienLuoc` có hàm thuần ảo `tinh`; đơn hàng giữ `unique_ptr<ChienLuoc>`, đổi lúc chạy bằng cách gán cái mới.
2. **`std::function` / lambda** ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)): đơn hàng giữ một `std::function<double(double)>`. Gọn nhất khi chiến lược chỉ là **một hàm**.
3. **Tham số template** ([Bài 34](34-template.md)): `DonHangC<CL>` giữ một `CL` bằng giá trị; kiểu chiến lược **chốt lúc biên dịch**; với chiến lược không có hàm ảo như ở Ví dụ 4 thì không có vtable.

| | Giao diện + `unique_ptr` | `std::function` / lambda | Tham số template |
|---|---|---|---|
| Chọn lúc nào | Lúc chạy | Lúc chạy | Lúc biên dịch |
| Đổi trên **cùng một** đối tượng | Được (`doi`) | Được (`doi`) | Không: `DonHangC<A>` và `DonHangC<B>` là hai kiểu khác nhau (mình thử gán, lỗi) |
| Chi phí gọi | Gián tiếp qua bảng hàm ảo ([Bài 33](33-da-hinh-virtual.md)) | Gián tiếp qua `std::function`; lúc tạo có thể cấp phát (mục 7) | Gọi thẳng, thường inline được |
| Chiến lược có nhiều hàm hoặc trạng thái | Hợp | Gượng (một hộp một hàm) | Hợp |
| Khi nào dùng | Nhiều thao tác, cần cất lẫn nhiều loại | Chiến lược là một hàm, viết tại chỗ | Kiểu biết lúc viết, chỗ gọi rất nóng và **đã đo** thấy cần |

Strategy hay bị nhầm với **State**: cấu trúc giống nhau, nhưng ở Strategy bên ngoài chọn cách làm, còn ở State chính đối tượng tự đổi cách làm khi trạng thái chuyển (bài này không viết State).

Cột "chi phí" chỉ là xu hướng thường được nói; chi phí thật phụ thuộc trình biên dịch và phải đo, còn bài này không đo thời gian. Một ví dụ bạn đã dùng: **`std::sort` với comparator chính là Strategy**. Thuật toán sắp xếp là phần chung; lambda so sánh `x < y` hay `x > y` ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)) là cách thay được, sắp tăng hay giảm mà `sort` không đổi một dòng.

### 7. `std::function` có chi phí gì

`std::function` **xóa kiểu** (một hộp chứa lambda, hàm hay đối tượng gọi được khác nhau, cùng chữ ký), nên lời gọi đi gián tiếp; và nếu thứ chứa bên trong **lớn** thì hộp có thể phải xin heap (ngưỡng do thư viện quyết định, chuẩn không nêu). Ví dụ 5 đếm thật số lần `new` trên g++ 11.4 (libstdc++); thư viện khác có thể khác.

### 8. Chỉ nhắc: Decorator và RAII

**Decorator** bọc một đối tượng trong một đối tượng cùng giao diện để thêm việc (bọc bộ tính phí để cộng phụ phí), xếp chồng được nhiều lớp. **RAII** ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)) là "mẫu" bạn đã dùng từ lâu (hàm tạo xin, hàm hủy trả); một "thẻ đăng ký" có thể tự `huyDangKy` trong hàm hủy. Chỉ cần nhận ra tên, bài không dạy sâu.

## 💻 Ví dụ code

### Ví dụ 1: Observer với con trỏ thô: cảm biến và hai màn hình

`Chude` là cảm biến: `datNhietDo` báo tin cho mọi `Quansat` trong danh sách. Hai `ManHinh` kế thừa `Quansat` và in nhiệt độ nhận được. Giữ ý: danh sách chứa `Quansat*` thô.

```cpp
#include <algorithm>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

class Quansat {                                          // (1)
public:
    virtual ~Quansat() = default;
    virtual void capNhat(double doC) = 0;
};

class Chude {                                            // (2)
public:
    void dangKy(Quansat* q) { ds_.push_back(q); }
    void huyDangKy(Quansat* q) {                         // (3)
        ds_.erase(std::remove(ds_.begin(), ds_.end(), q), ds_.end());
    }
    void datNhietDo(double doC) {                        // (4)
        for (Quansat* q : ds_) q->capNhat(doC);
    }
private:
    std::vector<Quansat*> ds_;
};

class ManHinh : public Quansat {
public:
    explicit ManHinh(std::string ten) : ten_(std::move(ten)) {}
    void capNhat(double doC) override { std::cout << ten_ << ": " << doC << " do C\n"; }
private:
    std::string ten_;
};

int main() {
    Chude camBien;
    ManHinh phong("phong khach");
    ManHinh bep("bep");
    camBien.dangKy(&phong);                              // (5)
    camBien.dangKy(&bep);
    camBien.datNhietDo(25);
    camBien.huyDangKy(&bep);                             // (6)
    camBien.datNhietDo(30);
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (5) | Hai lần `dangKy` thêm địa chỉ của `phong` và `bep` vào danh sách | `ds_`: [&phong, &bep] |
| (4) | `datNhietDo(25)` gọi `capNhat` qua con trỏ cha: hàm ảo chọn bản của món thật; cả hai in | không đổi |
| (3), (6) | `huyDangKy(&bep)` bỏ địa chỉ `bep` bằng remove-erase ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)) | `ds_`: [&phong] |
| (4) | `datNhietDo(30)`: chỉ `phong` còn nhận | không đổi |

**Kết quả khi chạy:**

```text
phong khach: 25 do C
bep: 25 do C
phong khach: 30 do C
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Observer bị hủy mà còn trong danh sách.** Trong `main`, tạo `auto m = std::make_unique<ManHinh>("tam");` (cần `<memory>`), `camBien.dangKy(m.get());`, rồi `m.reset();` (màn hình bị hủy, `camBien` vẫn giữ địa chỉ cũ), rồi `camBien.datNhietDo(25);`. ASan báo `heap-use-after-free ... READ of size 8` ngay trong `Chude::datNhietDo` (nhiều khả năng là đọc con trỏ bảng hàm ảo của món đã bị xóa). Không có sanitizer, bản mình thử **sập, mã thoát 139**. Chuẩn không hứa kết quả nào: đây là hành vi không xác định.
- **Observer tự hủy đăng ký trong `capNhat`.** Thêm lớp con `MotLan` có `capNhat` in `MotLan <id> nhan <nhiệt độ>` rồi gọi `c_.huyDangKy(this)` (`c_` là `Chude&` nó giữ); đăng ký ba cái `id` 1, 2, 3 rồi `datNhietDo(25)`. `erase` chạy ngay trong vòng range-for: ASan không báo gì, thoát 0, mà trên g++ 11 của mình in `MotLan 1 nhan 25`, `MotLan 3 nhan 25`, `MotLan 3 nhan 25`: số 2 bị **bỏ sót**, số 3 được gọi hai lần. Với `-D_GLIBCXX_DEBUG`, g++ dừng và báo `attempt to compare a dereferenceable iterator to a singular iterator`. Đây là hành vi không xác định, kết quả "1, 3, 3" không có gì được đảm bảo.

### Ví dụ 2: danh sách `weak_ptr`, observer hết đời thì tự rời danh sách

`dangKy` nhận `weak_ptr` (1). `datNhietDo` `lock()` từng mục (2), chỉ gọi khi còn sống (3), rồi dọn các mục đã hết hạn (4). `bep.reset()` (5) giả lập màn hình bếp bị hủy mà không ai `huyDangKy`.

```cpp
#include <algorithm>
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Quansat {
public:
    virtual ~Quansat() = default;
    virtual void capNhat(double doC) = 0;
};

class Chude {
public:
    void dangKy(std::weak_ptr<Quansat> q) { ds_.push_back(q); }          // (1)
    void datNhietDo(double doC) {
        for (const std::weak_ptr<Quansat>& w : ds_) {
            std::shared_ptr<Quansat> q = w.lock();                       // (2)
            if (q) q->capNhat(doC);                                      // (3)
        }
        ds_.erase(std::remove_if(ds_.begin(), ds_.end(),
                                 [](const std::weak_ptr<Quansat>& w) { return w.expired(); }),
                  ds_.end());                                            // (4)
    }
    std::size_t soDangKy() const { return ds_.size(); }
private:
    std::vector<std::weak_ptr<Quansat>> ds_;
};

class ManHinh : public Quansat {
public:
    explicit ManHinh(std::string ten) : ten_(std::move(ten)) {}
    ~ManHinh() override { std::cout << "huy " << ten_ << "\n"; }
    void capNhat(double doC) override { std::cout << ten_ << ": " << doC << "\n"; }
private:
    std::string ten_;
};

int main() {
    Chude camBien;
    auto phong = std::make_shared<ManHinh>("phong");
    auto bep = std::make_shared<ManHinh>("bep");
    camBien.dangKy(phong);
    camBien.dangKy(bep);
    std::cout << "dang ky: " << camBien.soDangKy() << ", use_count phong: " << phong.use_count() << "\n";
    camBien.datNhietDo(25);
    bep.reset();                                                         // (5)
    camBien.datNhietDo(26);                                              // (6)
    std::cout << "dang ky: " << camBien.soDangKy() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `shared_ptr<ManHinh>` đổi ngầm thành `weak_ptr<Quansat>`; danh sách không cộng bộ đếm mạnh, nên `use_count` của `phong` vẫn 1 | `ds_`: 2 `weak_ptr` |
| (2), (3) | Lượt 25: `lock()` thấy cả hai còn sống, gọi `capNhat` | `q` là chủ tạm, hết vòng lại trả |
| (5) | `bep.reset()` trả chủ duy nhất của bếp: hàm hủy in `huy bep`; mục trong `ds_` thành `expired` | `ds_` còn 2 mục, một cái đã chết |
| (2), (4) | Lượt 26: `lock()` của bếp rỗng nên (3) bỏ qua; (4) dọn mục đó | `ds_`: 1 mục |

**Kết quả khi chạy:**

```text
dang ky: 2, use_count phong: 1
phong: 25
bep: 25
huy bep
phong: 26
dang ky: 1
huy phong
```

Mình chạy với ASan + UBSan và ở `-O2`: sạch, mã thoát 0, cùng kết quả. Dòng `huy phong` cuối cùng là lúc `main` kết thúc. **Thử thay đổi** (đã chạy): bỏ `bep.reset();`. Cả hai màn hình nhận ở lượt 26 và `dang ky: 2`: `weak_ptr` chỉ làm danh sách **không giữ sống**, còn việc bếp chết hay không là do chủ của nó.

### Ví dụ 3: Observer gọn bằng `std::function`, hủy đăng ký ngay trong callback

`using HamNhan = std::function<void(double)>;` (1) là **bí danh kiểu**: `HamNhan` là tên ngắn của kiểu dài đó. `dangKy` (2) cất hàm kèm mã số và trả mã số; `huyDangKy(ma)` (3) bỏ mục mang mã đó. `datNhietDo` duyệt **bản sao** (4). Lambda đầu tiên (6) tự `huyDangKy` bằng mã của chính nó (7). `maMotLan` phải khai báo **trước** vì lambda cần dùng tên đó, mà mã chỉ có sau khi `dangKy` trả về. `[&]` cầm tham chiếu nên lúc lambda chạy nó thấy mã thật (bằng 1); bắt bản chép thì chỉ thấy 0, giá trị lúc tạo lambda.

```cpp
#include <algorithm>
#include <functional>
#include <iostream>
#include <utility>
#include <vector>

class CamBien {
public:
    using HamNhan = std::function<void(double)>;                  // (1)
    int dangKy(HamNhan f) {                                       // (2)
        ds_.push_back(Muc{++maMoi_, std::move(f)});
        return maMoi_;
    }
    void huyDangKy(int ma) {                                      // (3)
        ds_.erase(std::remove_if(ds_.begin(), ds_.end(),
                                 [ma](const Muc& m) { return m.ma == ma; }),
                  ds_.end());
    }
    void datNhietDo(double doC) {
        std::vector<Muc> banSao = ds_;                            // (4)
        for (const Muc& m : banSao) m.ham(doC);                   // (5)
    }
private:
    struct Muc { int ma; HamNhan ham; };
    std::vector<Muc> ds_;
    int maMoi_ = 0;
};

int main() {
    CamBien camBien;
    int maMotLan = 0;
    maMotLan = camBien.dangKy([&](double t) {                               // (6)
        std::cout << "mot lan: " << t << "\n";
        camBien.huyDangKy(maMotLan);                                        // (7)
    });
    camBien.dangKy([](double t) { std::cout << "in: " << t << "\n"; });     // (8)
    int soLan = 0;
    camBien.dangKy([&soLan](double) { ++soLan; });                          // (9)
    camBien.datNhietDo(25);
    camBien.datNhietDo(26);
    std::cout << "so lan dem: " << soLan << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (6), (8), (9) | Ba lambda đăng ký, nhận mã 1, 2, 3; lambda (9) cầm **tham chiếu** tới `soLan`. (`struct Muc` khai báo dưới hàm dùng nó: trong lớp, thân hàm thấy cả thành viên khai báo sau) | `ds_`: 3 mục |
| (4), (5) | Lượt 25: sao chép danh sách (cả các hộp), gọi từng hộp theo thứ tự đăng ký | `banSao`: 3 mục |
| (7) | Lambda 1 gọi `huyDangKy(1)`: `erase` trên `ds_` **gốc**, vòng đang chạy trên `banSao` nên không hỏng | `ds_`: 2 mục |
| (4), (5) | Lượt 26: lambda 1 không còn; (8) và (9) chạy | `ds_`: 2 mục |

**Kết quả khi chạy:**

```text
mot lan: 25
in: 25
in: 26
so lan dem: 2
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Đổi (5) sang duyệt thẳng `ds_`** (`for (const Muc& m : ds_)`): chương trình dừng bằng `terminate called after throwing an instance of 'std::bad_function_call'` (ASan không báo lỗi bộ nhớ nào); `-D_GLIBCXX_DEBUG` thì báo `attempt to compare a dereferenceable iterator to a singular iterator`. Lambda tự xóa mình khỏi danh sách **đang chạy chính nó**: hành vi không xác định, chuẩn không hứa kết quả nào.
- **Đổi `[&]` ở (6) thành `[=, &camBien]`** (chép `maMotLan`, vẫn tham chiếu `camBien`): lambda 1 thấy `maMotLan` bằng 0, `huyDangKy(0)` không xóa gì, nên nó không tự hủy: ra `mot lan: 25`, `in: 25`, `mot lan: 26`, `in: 26`.

### Ví dụ 4: Strategy ba cách cho phí vận chuyển

Cùng việc "phí vận chuyển của đơn nặng 2,5 kg". Cách 1: `DonHangA` + giao diện `ChienLuoc` (`PhiTheoKg` 12 một kg, `PhiCoDinh` 20). Cách 2: `DonHangB` giữ `std::function`. Cách 3: `DonHangC<CL>` là template; `TheoKgT` và `CoDinhT` là hai struct **không có hàm ảo**, chỉ có hàm `tinh`.

```cpp
#include <functional>
#include <iostream>
#include <memory>
#include <utility>

// Cach 1: giao dien da hinh
class ChienLuoc {
public:
    virtual ~ChienLuoc() = default;
    virtual double tinh(double kg) const = 0;
};
class PhiTheoKg : public ChienLuoc {
public:
    explicit PhiTheoKg(double giaMotKg) : gia_(giaMotKg) {}
    double tinh(double kg) const override { return kg * gia_; }
private:
    double gia_;
};
class PhiCoDinh : public ChienLuoc {
public: double tinh(double) const override { return 20; }
};
class DonHangA {
public:
    DonHangA(double kg, std::unique_ptr<ChienLuoc> cl) : kg_(kg), cl_(std::move(cl)) {}
    void doi(std::unique_ptr<ChienLuoc> cl) { cl_ = std::move(cl); }        // (1)
    double phi() const { return cl_->tinh(kg_); }                           // (2)
private:
    double kg_;
    std::unique_ptr<ChienLuoc> cl_;
};

// Cach 2: std::function
class DonHangB {
public:
    DonHangB(double kg, std::function<double(double)> f) : kg_(kg), f_(std::move(f)) {}
    void doi(std::function<double(double)> f) { f_ = std::move(f); }        // (3)
    double phi() const { return f_(kg_); }
private:
    double kg_;
    std::function<double(double)> f_;
};

// Cach 3: template, kieu chien luoc chot luc bien dich
struct TheoKgT { double gia; double tinh(double kg) const { return kg * gia; } };
struct CoDinhT { double tinh(double) const { return 20; } };
template <typename CL>
class DonHangC {
public:
    DonHangC(double kg, CL cl) : kg_(kg), cl_(cl) {}
    double phi() const { return cl_.tinh(kg_); }                            // (4)
private:
    double kg_;
    CL cl_;                                                                 // (5)
};

int main() {
    DonHangA a(2.5, std::make_unique<PhiTheoKg>(12));
    std::cout << "A theo kg: " << a.phi() << "\n";
    a.doi(std::make_unique<PhiCoDinh>());
    std::cout << "A co dinh: " << a.phi() << "\n";

    DonHangB b(2.5, [](double kg) { return kg * 12; });
    std::cout << "B theo kg: " << b.phi() << "\n";
    double nguong = 2;
    b.doi([nguong](double kg) { return kg > nguong ? 0.0 : 15.0; });        // (6)
    std::cout << "B mien phi tren 2 kg: " << b.phi() << "\n";

    DonHangC<TheoKgT> c(2.5, TheoKgT{12});
    DonHangC<CoDinhT> d(2.5, CoDinhT{});
    std::cout << "C theo kg: " << c.phi() << ", C co dinh: " << d.phi() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | `A` gọi `tinh` qua `unique_ptr<ChienLuoc>`: hàm ảo chọn `PhiTheoKg` (12 x 2,5 = 30) | `a.cl_` -> món `PhiTheoKg` |
| (1) | `doi` gán `unique_ptr` mới: món cũ bị xóa, `a` dùng `PhiCoDinh`: 20 | `a.cl_` -> món `PhiCoDinh` |
| (3), (6) | `B` đổi hộp sang lambda mới (bắt bản chép của `nguong`): 2,5 > 2 nên miễn phí, ra 0 | `b.f_` giữ lambda + `nguong` = 2 |
| (4), (5) | `C` giữ `CL` **bằng giá trị** (không con trỏ, không vtable); `cl_.tinh` được biết kiểu lúc biên dịch nên gọi thẳng | `c.cl_` nằm ngay trong `c` |

**Kết quả khi chạy:**

```text
A theo kg: 30
A co dinh: 20
B theo kg: 30
B mien phi tren 2 kg: 0
C theo kg: 30, C co dinh: 20
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Thêm `c = d;`** sau khi tạo `d`: lỗi biên dịch `no match for ‘operator=’ (operand types are ‘DonHangC<TheoKgT>’ and ‘DonHangC<CoDinhT>’)`. Hai kiểu khác nhau: kiểu chiến lược nằm trong kiểu đơn hàng.

### Ví dụ 5: `std::function` tốn gì? Đếm lần `new`

Để đếm, chương trình thay hàm `operator new` toàn cục (2): C++ gọi hàm này mỗi khi `new` xin bộ nhớ (kể cả thư viện xin giùm) và cho bạn viết bản của mình. Bản này tăng biến đếm (1) rồi xin bằng `malloc` (chỉ để minh họa). Hai hàm `operator delete` trả lại bằng `free`; `noexcept` là lời hứa "không ném ngoại lệ" mà chữ ký của `operator delete` đòi có, và bản có `std::size_t` chỉ để khỏi cảnh báo. Hai `std::function` chứa hai lambda cỡ khác nhau.

```cpp
#include <cstdlib>
#include <functional>
#include <iostream>
#include <new>

int soLanNew = 0;                                              // (1)

void* operator new(std::size_t n) {                            // (2)
    ++soLanNew;
    return std::malloc(n);
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

int main() {
    std::cout << "sizeof(std::function<int(int)>) = " << sizeof(std::function<int(int)>) << "\n";

    int k = 5;
    int truoc = soLanNew;
    std::function<int(int)> f2 = [k](int x) { return x + k; };            // (4)
    std::cout << "lambda bat 1 int: " << soLanNew - truoc << " lan new\n";

    int mang[16] = {1};
    truoc = soLanNew;
    std::function<int(int)> f3 = [mang](int x) { return x + mang[0]; };   // (5)
    std::cout << "lambda bat mang 64 byte: " << soLanNew - truoc << " lan new\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2) | Mỗi lần ai đó dùng `new`, biến đếm tăng 1 | `soLanNew`: biến toàn cục |
| (4) | Lambda bắt một `int` (4 byte): nằm gọn trong chính hộp `std::function` trên máy mình | `f2` tự chứa, đếm 0 |
| (5) | Lambda bắt mảng 64 byte: không vừa chỗ sẵn có trong hộp, nên hộp xin heap | `f3` giữ con trỏ tới một khối heap, đếm 1 |

**Kết quả khi chạy:**

```text
sizeof(std::function<int(int)>) = 32
lambda bat 1 int: 0 lan new
lambda bat mang 64 byte: 1 lan new
```

Mình chạy với ASan + UBSan và ở `-O2`: cùng kết quả, thoát 0. Đây là kết quả của g++ 11.4, libstdc++, máy 64-bit này: chuẩn không nêu ngưỡng "nhỏ", nên thư viện khác có thể cấp phát sớm hơn hoặc muộn hơn. Bài chỉ đếm cấp phát, **không đo thời gian** gọi.

## Go: channel, interface bé, hàm là giá trị

!!! info "Bạn biết Go?"
    Mình đã chạy chương trình Go 1.27.1 nhỏ (`go vet`, thêm `-race` với phần channel) để kiểm các ý dưới đây.
    - **Observer bằng callback hoặc interface bé**: Go thích interface **một hàm** (`type Quansat interface{ CapNhat(float64) }`); một struct có phương thức `CapNhat` là đủ, không khai báo "kế thừa". Một **kiểu hàm** cũng có thể có phương thức (`type HamQuansat func(float64)` rồi `func (h HamQuansat) CapNhat(t float64) { h(t) }`), nên một closure đứng vào chỗ interface được. Mình đăng ký một struct và một closure vào cùng danh sách `[]Quansat`; cả hai nhận `21.5`.
    - **Observer bằng channel**: channel gửi cho **một** người nhận mỗi tin, không phát cho tất cả. Mình chạy hai goroutine cùng đọc một channel, gửi 10 tin: tổng nhận được là 10 (chia nhau). Muốn mọi nơi đều nhận thì mỗi observer có channel riêng, và chủ đề gửi vào từng channel.
    - **Strategy bằng hàm**: `type Phi func(kg float64) float64`; truyền `func(kg float64) float64 { return kg * 10 }` vào thẳng (kết quả 30 với 3 kg). Hoặc dùng interface `ChienLuoc` một hàm khi chiến lược có dữ liệu. `sort.Slice(v, func(i, j int) bool { return v[i] > v[j] })` cũng là Strategy (kết quả `[3 2 1]`).
    - **Vòng đời**: Go có bộ gom rác, nên không có use-after-free kiểu C++; nhưng danh sách **giữ observer sống**. Mình gán `m = nil`, gọi `runtime.GC()`, rồi báo tin: danh sách vẫn gọi được observer (in `bep nhan 30`).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Observer là gì? Cho ví dụ thực tế."
    Observer cho một đối tượng (chủ đề) báo tin cho một danh sách đối tượng khác (observer) khi nó đổi, mà chủ đề chỉ biết một giao diện, không biết lớp cụ thể. Ví dụ: sự kiện trong giao diện đồ họa (nút bấm báo cho các hàm xử lý đã đăng ký), publish/subscribe (người đăng tin, nhiều người đăng ký), cảm biến báo cho màn hình. Trong C++: giao diện `Quansat` với `capNhat`, hoặc danh sách `std::function`.

??? question "Observer bị hủy mà chủ đề còn gọi thì sao?"
    Nếu danh sách giữ con trỏ thô, chủ đề gọi vào đối tượng đã hủy: hành vi không xác định (ASan báo `heap-use-after-free`). Chữa: observer tự `huyDangKy` trước khi hủy, hoặc danh sách giữ `std::weak_ptr` và `lock()` trước mỗi lần gọi: rỗng thì bỏ qua và dọn. Nhớ thêm bẫy hủy đăng ký giữa lúc duyệt (iterator hỏng): duyệt trên bản sao danh sách.

??? question "Strategy vs State?"
    Cấu trúc giống nhau: đối tượng giao việc cho một đối tượng "cách làm". Strategy: bên ngoài chọn cách làm (cách tính phí), thường không tự đổi. State: đối tượng tự đổi cách làm khi trạng thái chuyển (máy bán hàng từ "chờ tiền" sang "đã nhận tiền"), các trạng thái thường biết nhau để chuyển. Chọn theo ý định, không theo hình dạng code.

??? question "Strategy bằng đa hình vs lambda vs template?"
    Đa hình (giao diện + `unique_ptr`): chọn lúc chạy, hợp khi chiến lược có nhiều thao tác hoặc trạng thái, mỗi lời gọi gián tiếp qua bảng hàm ảo. `std::function`/lambda: cũng chọn lúc chạy, gọn nhất khi chiến lược chỉ là một hàm. Template: chọn lúc biên dịch, không hàm ảo thì không vtable nên thường gọi thẳng được, nhưng không đổi được trên cùng một đối tượng và mỗi kiểu một bản mã. Đo trước khi chọn vì chi phí.

??? question "`std::function` có chi phí gì?"
    Nó xóa kiểu nên lời gọi đi gián tiếp, và nếu thứ chứa bên trong lớn thì có thể phải cấp phát heap (ngưỡng do thư viện quyết định; trên g++ 11.4 mình thấy lambda bắt mảng 64 byte tốn một lần `new`, lambda bắt một `int` thì không). Nó cũng khó inline hơn lambda gọi trực tiếp. Chỉ nói "có thể", và đo nếu nó nằm trong đường chạy nóng.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Danh sách observer giữ con trỏ thô"
    Observer bị hủy mà chủ đề còn gọi là hành vi không xác định (Ví dụ 1, Thử thay đổi). Dùng `weak_ptr` + `lock()` (Ví dụ 2), hoặc bảo đảm `huyDangKy` trước khi hủy. Lambda `[&x]` làm callback cũng treo khi `x` chết trước (Ví dụ 3).

!!! warning "Lỗi 2: Hủy đăng ký giữa lúc đang duyệt danh sách"
    `erase` trong lúc range-for làm iterator hỏng: bỏ sót, gọi trùng, hoặc sập (Ví dụ 1). Duyệt trên bản sao (Ví dụ 3), và đừng tin vào lần chạy "ra đúng".

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="36" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau. Chuyện gì xảy ra ở dòng cuối?

```text
Chude camBien;                          // giữ vector<Quansat*>
auto m = std::make_unique<ManHinh>("tam");
camBien.dangKy(m.get());
m.reset();
camBien.datNhietDo(25);                 // gọi capNhat trên từng phần tử
```

- Biên dịch được và `capNhat` bị bỏ qua, vì `m` đã rỗng nên danh sách coi mục đó là trống
- Ném một ngoại lệ bắt được, vì địa chỉ trong danh sách không còn hợp lệ
- Biên dịch được, nhưng `capNhat` chạy trên món đã xóa (vùng nhớ đã trả lại)
- Chạy bình thường và in một dòng, vì `Chude` đã sao chép món vào danh sách

<p class="giai-thich" markdown>`m.get()` chỉ đưa **địa chỉ** vào danh sách; `m.reset()` xóa món, còn địa chỉ trong danh sách vẫn nguyên (con trỏ thô không biết món đã chết). Gọi `capNhat` qua địa chỉ đó là hành vi không xác định (mình chạy: ASan báo `heap-use-after-free`; không sanitizer thì sập). Danh sách không sao chép món, nó chỉ cầm địa chỉ nên "tự giữ bản sao" sai. Con trỏ thô cũng không biến thành rỗng khi món chết, nên không có ngoại lệ hay chuyện "tự bỏ qua".</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Vòng duyệt có an toàn không?

```text
void datNhietDo(double t) {
    for (Quansat* q : ds_) q->capNhat(t);   // ds_ là vector<Quansat*>
}
// một Quansat gọi huyDangKy(this) bên trong capNhat,
// và huyDangKy gọi ds_.erase(...)
```

- Không: `erase` trên `ds_` đang được duyệt làm iterator hỏng, là hành vi không xác định
- Có: `erase` chỉ bỏ phần tử khỏi danh sách nên vòng range-for tự đi tiếp đúng
- Không, vì `erase` làm vector cấp phát lại nên con trỏ `q` bị treo
- Có, vì range-for sao chép `ds_` trước khi duyệt rồi mới chạy thân vòng

<p class="giai-thich" markdown>Range-for duyệt trực tiếp trên `ds_` (không sao chép), và `erase` làm hỏng iterator của vòng đang chạy ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)). Đó là hành vi không xác định; mình chạy một bản tương tự thì bỏ sót một observer và gọi trùng một observer khác, còn `-D_GLIBCXX_DEBUG` thì dừng chương trình. Range-for không tự sao chép (bản sao phải do bạn viết). Chuyện `erase` cấp phát lại vector cũng không đúng: nó dời các phần tử và giữ nguyên vùng nhớ, còn con trỏ `q` chỉ là một bản sao của phần tử. Cái hỏng là iterator mà vòng for đang cầm ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)).</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Danh sách của chủ đề giữ `std::weak_ptr<Quansat>`. Với một phần tử `w`, ý nào đúng?

- `w->capNhat(t)` dùng được trực tiếp, và nếu observer đã chết thì tự bỏ qua
- `w.lock()` trả `shared_ptr` khác rỗng, vì `weak_ptr` đang giữ observer sống
- `w.lock()` làm bộ đếm mạnh tăng và giữ lại, nên observer không còn bị hủy nữa
- `w.lock()` trả `shared_ptr` rỗng nếu observer đã hủy, nên kiểm trước khi gọi

<p class="giai-thich" markdown>`lock()` trả `shared_ptr` thật nếu observer còn sống và rỗng nếu đã hủy, nên kiểm rồi mới gọi `capNhat` ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)). `weak_ptr` không có `->` để dùng trực tiếp. Nó cũng **không** giữ observer sống, nên `lock()` có thể rỗng. Và bộ đếm chỉ tăng trong lúc bạn còn cầm `shared_ptr` nhận được: hết biến đó là giảm lại, observer vẫn bị hủy được.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau (dùng `DonHangC` như trong bài). Chuyện gì xảy ra?

```text
DonHangC<TheoKgT> c(2.5, TheoKgT{12});
DonHangC<CoDinhT> d(2.5, CoDinhT{});
c = d;
```

- Chạy được: `c` nhận chiến lược của `d` lúc chạy, giống `doi` của cách giao diện
- Chạy được nhưng `c` giữ lại chiến lược cũ, vì phép gán chỉ chép cân nặng
- Lỗi biên dịch: hai đối tượng là hai kiểu khác nhau vì tham số template khác nhau
- Lỗi liên kết, vì lớp `DonHangC` bị định nghĩa hai lần với hai tham số khác nhau

<p class="giai-thich" markdown>Mỗi bộ tham số template tạo một kiểu riêng: `DonHangC<TheoKgT>` và `DonHangC<CoDinhT>` không liên quan nhau, nên không có phép gán giữa chúng và g++ báo lỗi biên dịch (mình đã chạy: `no match for ‘operator=’`). Đó chính là điều template Strategy đánh đổi: chọn lúc biên dịch thì không đổi được lúc chạy. Phép gán không "chỉ chép cân nặng", vì nó không tồn tại. Mỗi bộ tham số sinh một lớp riêng chứ không "định nghĩa hai lần", nên không có lỗi liên kết.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Câu nào về chi phí của `std::function` là đúng?

- Lời gọi đi gián tiếp, và thứ chứa bên trong quá lớn thì được đặt trên heap
- Lời gọi đi trực tiếp như hàm thường, nhưng thứ chứa bên trong được đặt trên heap
- Lời gọi đi gián tiếp, nhưng thứ chứa bên trong được giữ trên stack dù lớn đến đâu
- Lời gọi đi trực tiếp, và lambda có bắt biến thì bị đặt trên heap dù nhỏ

<p class="giai-thich" markdown>`std::function` xóa kiểu nên lời gọi đi gián tiếp, và thứ chứa bên trong quá lớn so với chỗ sẵn có trong hộp thì hộp xin heap (Ví dụ 5: lambda bắt một `int` không xin, lambda bắt mảng 64 byte xin một lần, trên g++ 11.4; ngưỡng đổi theo thư viện). Nên "đặt trên heap" cho mọi thứ chứa là sai, và "bắt biến là xin heap dù nhỏ" cũng sai vì lambda bắt `int` ở Ví dụ 5 không xin. "Giữ trên stack dù lớn đến đâu" cũng sai: hộp chỉ có chỗ nhỏ, quá cỡ thì phải xin heap. Còn "lời gọi trực tiếp" sai vì hộp phải gọi qua lớp trung gian.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Trong Go, hai goroutine cùng `for v := range ch` đọc một channel `ch`; chủ đề gửi vào `ch` đúng 10 giá trị rồi đóng channel. Tổng số lần nhận (cộng cả hai goroutine) là bao nhiêu?

- 20, vì channel gửi mỗi giá trị tới cả hai goroutine đang đọc, như Observer
- 10, vì mỗi giá trị gửi vào channel chỉ do một goroutine nhận
- 10 nhưng chỉ khi channel không đệm; channel có đệm thì mỗi nơi nhận đủ 10
- Không xác định, vì không gì quyết định goroutine nào nhận giá trị nào

<p class="giai-thich" markdown>Mỗi giá trị gửi vào channel chỉ được **một** người nhận lấy đi, nên tổng là 10, chia nhau theo lúc nào ai rảnh (mình chạy với `-race`: tổng 10). Channel không phát cho mọi người đọc như Observer; muốn vậy mỗi observer cần channel riêng. Đệm không đổi điều đó, và tổng không đổi theo lần chạy: chỉ **ai** nhận cái nào là khác.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Observer**: chủ đề đổi, nhiều nơi cần biết, mà không muốn phụ thuộc từng nơi: giao diện `Quansat` (hàm thuần ảo `capNhat`) và `Chude` giữ danh sách `dangKy`/`huyDangKy`. Danh sách con trỏ thô nguy hiểm: observer bị hủy mà còn trong danh sách thì gọi vào đồ đã trả (ASan: `heap-use-after-free`, mình chạy).
2. **Vòng đời**: danh sách `std::weak_ptr` không giữ observer sống, `lock()` rỗng nghĩa là đã hủy (bỏ qua, dọn). Observer tự hủy đăng ký giữa lúc duyệt làm iterator hỏng (mình chạy: bỏ sót/gọi trùng): duyệt trên bản sao. Thứ tự gọi và thread-safety (khóa `mutex` khi sửa danh sách, nhả khóa trước khi gọi) chỉ nhắc.
3. **Bản gọn `std::function` callback**: lambda đăng ký tại chỗ, trả mã số để hủy; hợp khi nơi nhận chỉ là một hành động; giao diện hợp khi nơi nhận có nhiều thao tác hoặc trạng thái. Lambda `[&x]` làm callback có cùng bẫy treo.
4. **Strategy** tách "cách làm" thay được khỏi lớp dùng nó, ba cách: giao diện + `unique_ptr` (chọn lúc chạy, gián tiếp), `std::function`/lambda (gọn nhất khi chỉ là một hàm), tham số template (chọn lúc biên dịch, không vtable, không đổi được trên cùng đối tượng: `c = d` lỗi). `sort` với comparator là Strategy. Strategy do bên ngoài chọn, State do đối tượng tự đổi. Decorator và RAII chỉ nhắc tên.
5. `std::function` xóa kiểu: gọi gián tiếp, và có thể cấp phát heap khi thứ chứa lớn (g++ 11.4: `sizeof` 32; lambda bắt `int` 0 lần `new`, lambda bắt mảng 64 byte 1 lần; đổi theo thư viện). Go: interface một hàm hoặc kiểu hàm có phương thức, channel gửi mỗi tin cho một người nhận (không phát chung), hàm là giá trị hạng nhất cho Strategy, bộ gom rác tránh use-after-free nhưng danh sách vẫn giữ observer sống.
