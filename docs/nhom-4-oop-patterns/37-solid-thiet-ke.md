# Bài 37 — SOLID và thiết kế lớp: năm nguyên tắc, và đừng thiết kế thừa

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được từng chữ cái của **SOLID** (S, O, L, I, D) bằng một ví dụ C++ nhỏ chạy thật: tách lớp làm ba việc (S), thêm kiểu mới không sửa mã cũ (O, nối registry ở [Bài 35](35-pattern-singleton-factory.md) và Strategy ở [Bài 36](36-pattern-observer-strategy.md)), hình vuông/hình chữ nhật vỡ **hợp đồng** (L, đã hẹn ở [Bài 32](32-ke-thua.md)), interface nhỏ (I), lớp cấp cao nhận interface và test bằng đối tượng giả `MayChuGia` (D).
    - Phân biệt **Dependency Inversion** (nguyên tắc) với **Dependency Injection** (kỹ thuật); chọn **composition** (has-a) thay vì kế thừa khi chỉ muốn dùng lại; dùng **Rule of 0** khi thiết kế lớp (chạy thật, kể cả khi thêm `unique_ptr`).
    - Chọn giữa lớp trừu tượng, template và `std::function` bằng một bảng; biết lúc nào SOLID thành over-engineering (KISS, YAGNI).
    - Có danh sách 14 câu hỏi phỏng vấn OOP nối Bài 31–36; so với Go (không có kế thừa, interface nhỏ nhận ở nơi dùng; đã chạy Go 1.27.1).

**Bạn cần biết trước:** [Bài 31](31-lop-dong-goi.md) (lớp, bất biến), [Bài 32](32-ke-thua.md) (kế thừa, is-a/has-a, hình vuông/chữ nhật), [Bài 33](33-da-hinh-virtual.md) (hàm thuần ảo, hàm hủy ảo, `unique_ptr<Hinh>`), [Bài 34](34-template.md) (template), [Bài 35](35-pattern-singleton-factory.md) (registry factory, truyền phụ thuộc vào), [Bài 36](36-pattern-observer-strategy.md) (Strategy, `std::function`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (Rule of 3/5/0).

## 🧠 Câu chuyện mở đầu

Trở lại **xưởng đồ chơi** của [Bài 31](31-lop-dong-goi.md). Một xưởng làm ăn lâu dài có vài nếp: mỗi thợ chỉ lo **một việc** (không ai vừa cắt, vừa sơn, vừa đóng hộp); thêm mẫu đồ chơi mới thì thêm bản vẽ, **không đập dây chuyền cũ**; món con làm ra phải **thay được** món cha ở mọi chỗ trên dây chuyền; phiếu việc ghi đúng việc cần, không kèm việc thừa; dây chuyền nhận "khuôn tiêu chuẩn" chứ không nhận một cái máy cụ thể.

Năm nếp đó chính là **SOLID**, ghép từ chữ cái đầu của năm nguyên tắc thiết kế lớp (Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion). Chúng là **nguyên tắc** (kinh nghiệm đúc kết), không phải luật: dùng đúng chỗ thì code dễ đổi, dùng cứng nhắc thì thành thiết kế thừa.

!!! info "Chỗ nào ví von không còn đúng?"
    Xưởng đồ chơi chỉ dùng ở đoạn mở đầu này. Các ví dụ bên dưới **đổi chủ đề** theo từng nguyên tắc (bảng điểm, hình học, máy in, máy chủ báo động, xe); mình báo ở đầu mỗi ví dụ. Và "đập dây chuyền" ngoài đời tốn tiền, còn trong code "sửa mã cũ" tốn ở chỗ có thể làm hỏng chỗ đang chạy tốt.

## 📖 Giải thích

### 1. SOLID trong một bảng, và nó không phải luật

| Chữ | Tên | Một câu |
|---|---|---|
| S | Single Responsibility (một trách nhiệm) | Một lớp chỉ có **một lý do để bị sửa** |
| O | Open/Closed (mở/đóng) | Thêm hành vi mới bằng **thêm mã**, không sửa mã đã chạy |
| L | Liskov Substitution (thay thế) | Lớp con dùng được ở **mọi chỗ** lớp cha dùng, không làm vỡ hợp đồng của cha |
| I | Interface Segregation (tách interface) | Nhiều interface **nhỏ** hơn một interface to |
| D | Dependency Inversion (đảo phụ thuộc) | Lớp cấp cao phụ thuộc **interface**, không phụ thuộc lớp cụ thể |

Mỗi nguyên tắc có một cái giá (thêm lớp, thêm interface). Nó có lời khi **sự thay đổi có thật** xảy ra; mục 9 nói về lúc nó không có lời.

### 2. S: một lớp, một lý do để đổi

Lớp `BaoCao` vừa **tính** trung bình, vừa **in**, vừa **lưu** thì có ba lý do bị sửa: đổi công thức, đổi cách in, đổi nơi lưu. Mỗi lần sửa một việc có nguy cơ làm hỏng hai việc kia, vì chúng nằm chung một lớp, dùng chung dữ liệu. Tách ra: một hàm tính, một hàm in, một lớp lưu. Ví dụ 1 làm cả hai bản và cho cùng kết quả.

### 3. O: thêm kiểu mới mà không sửa mã cũ

Hàm `tong(const Hinh&, const Hinh&)` ở Ví dụ 2 chỉ biết `Hinh` và gọi `dienTich()` ([Bài 33](33-da-hinh-virtual.md)). Thêm `TamGiac` chỉ cần **viết thêm một lớp**: `tong` không đổi một dòng. Nếu thay vì hàm ảo ta dùng chuỗi `if (loai == "tron") ... else if (...)`, mỗi hình mới là một lần sửa hàm đó.

"Đóng với sửa đổi" không có nghĩa không bao giờ sửa: nó có nghĩa loại thay đổi dự đoán được (thêm loại hình) không đòi sửa phần ổn định. Hai bài trước đã là O: registry factory ([Bài 35](35-pattern-singleton-factory.md)) cho "đăng ký loại mới không sửa factory", và Strategy ([Bài 36](36-pattern-observer-strategy.md)) cho "cách tính mới không sửa đơn hàng". Điểm chung: phần **đổi** nằm sau một interface, phần **ổn định** chỉ biết interface.

### 4. L: lớp con phải giữ hợp đồng của lớp cha

Quy tắc Liskov: ở đâu dùng được lớp cha thì thay bằng lớp con vẫn chạy **đúng**. "Đúng" nói về **hợp đồng** của lớp cha: những điều người dùng được phép trông đợi (ví dụ: sau `datRong(5)` thì rộng là 5 **và cao không đổi**), cộng với các bất biến ([Bài 31](31-lop-dong-goi.md)). Lớp con được thêm khả năng, nhưng không được làm hợp đồng và bất biến của cha sai đi.

Hình vuông kế thừa hình chữ nhật có hàm `datRong` là ví dụ kinh điển ([Bài 32](32-ke-thua.md) đã hẹn). Muốn vuông còn vuông thì `datRong` phải đổi cả cao, và kỳ vọng "cao không đổi" của chữ nhật vỡ; không đổi cao thì vuông hết vuông. **Với `datRong` công khai và yêu cầu vuông luôn có hai cạnh bằng nhau, không có cách viết lớp con nào đúng cả hai** (Ví dụ 2 chạy cả hai).

Cách sửa: **bỏ kế thừa**, dùng interface chung `Hinh` với `dienTich()`; `ChuNhat` và `Vuong` là hai lớp anh em, không có hàm "sửa cạnh" nên không có hợp đồng "đổi rộng, cao giữ nguyên" để phá. Bài học: "là một" trong toán không tự thành is-a trong code; câu hỏi đúng là "mọi nơi dùng cha có còn đúng với con không".

### 5. I: interface nhỏ, mỗi chỗ cần gì thì nhận cái đó

Một interface `MayVanPhong` có `in`, `quet`, `fax` buộc mọi lớp cài đặt phải viết cả ba, kể cả máy chỉ biết in. Tách thành `MayIn` và `MayQuet`: máy in đơn chỉ cài `MayIn`; máy đa năng cài cả hai bằng kế thừa nhiều interface.

Kế thừa nhiều interface ở đây không dính bài toán kim cương của [Bài 32](32-ke-thua.md), vì `MayIn` và `MayQuet` **không có cha chung** (mình chạy thử với g++ 11: hai interface cùng kế thừa một interface gốc `G` rồi gộp vào một lớp `C` thì vẫn biên dịch được, nhưng chuyển `C&` sang `G&` (hay `C*` sang `G*`) báo `‘G’ is an ambiguous base of ‘C’`, dù gốc không có dữ liệu). Hàm `inBienLai(MayIn&)` nhận đúng thứ nó cần (Ví dụ 3).

### 6. D: phụ thuộc interface; Dependency Inversion khác Dependency Injection

**Dependency Inversion** (đảo phụ thuộc, **nguyên tắc**): bình thường lớp cấp cao (làm việc nghiệp vụ, như `DichVuBaoDong`) phụ thuộc thẳng lớp cấp thấp (như `MayChuThat`), mũi tên đi từ cao xuống thấp. Thêm interface `MayChu` do bên cấp cao định ra: `DichVuBaoDong` chỉ phụ thuộc `MayChu`, còn `MayChuThat` phải cài `MayChu`. Mũi tên phía cấp thấp **đổi chiều** (từ lớp thấp hướng về interface của lớp cao): đó là chữ "đảo".

**Dependency Injection** (truyền phụ thuộc vào, **kỹ thuật** của [Bài 35](35-pattern-singleton-factory.md)): thứ cần dùng được đưa vào qua tham số hay hàm tạo, không tự tạo bên trong. Injection là cách thường dùng để **thực hiện** inversion.

Lợi ích thấy ngay: kiểm thử. `DichVuBaoDong` nhận `MayChu&`, nên bài kiểm đưa vào `MayChuGia` (đối tượng giả: ghi lại tin nhận, hoặc cố ý báo hỏng) mà không gửi gì thật (Ví dụ 4). Nếu `DichVuBaoDong` tự tạo `MayChuThat` bên trong, không có chỗ nào để thay.

### 7. Composition hơn inheritance, và Rule of 0

[Bài 32](32-ke-thua.md) nói: chỉ kế thừa công khai khi đúng is-a; chỉ muốn dùng lại thì dùng thành viên (has-a). Kế thừa buộc con vào **toàn bộ** giao diện cha (và mọi thay đổi của cha), còn thành viên chỉ lộ ra những hàm bạn chọn và đổi được sau này. `Xe` **có một** `DongCo` thì viết `DongCo dongCo_;` và gọi `dongCo_.no()`, không viết `class Xe : public DongCo`.

Thiết kế bằng thành viên còn cho **Rule of 0** ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)): nếu mọi thành viên tự quản lý mình (`std::string`, `std::vector`, `std::unique_ptr`, hoặc một lớp khác cũng như vậy) thì bạn **không viết** hàm hủy, hàm tạo/gán sao chép hay di chuyển nào, và trình biên dịch sinh đúng cho bạn (Ví dụ 5). Rule of 5 chỉ cần khi một lớp trực tiếp giữ tài nguyên thô; ngoại lệ hay gặp là hàm hủy ảo `= default` của lớp cha đa hình ([Bài 33](33-da-hinh-virtual.md)).

### 8. Interface bằng lớp trừu tượng, template, hay `std::function`?

Ba bài trước đã cho ba cách viết "một chỗ, nhiều cách làm". Bảng này gom lại; không cái nào tốt hơn tuyệt đối.

| | Lớp trừu tượng ([Bài 33](33-da-hinh-virtual.md)) | Template ([Bài 34](34-template.md)) | `std::function` / lambda ([Bài 36](36-pattern-observer-strategy.md)) |
|---|---|---|---|
| Chọn lúc nào | Lúc chạy | Lúc biên dịch | Lúc chạy |
| Chứa lẫn nhiều loại trong một dãy | Được | Không (`vector<H>` chỉ một kiểu) | Được, nếu cùng chữ ký |
| Yêu cầu với kiểu | Phải kế thừa lớp cha, ghi đè đủ hàm thuần ảo | Chỉ cần có đúng các hàm được gọi; lỗi có thể dài | Chỉ cần gọi được với chữ ký đó |
| Chi phí | Gọi gián tiếp (thường qua bảng hàm ảo) | Thường gọi thẳng; mỗi kiểu một bản mã | Gọi gián tiếp; lúc tạo có thể cấp phát heap |
| Hợp khi | Nhiều thao tác, nhiều loại, quyết định lúc chạy | Thuật toán chung, kiểu biết lúc viết | Chỉ **một** hành động nhỏ, viết tại chỗ |

### 9. Đừng thiết kế thừa: KISS và YAGNI

**KISS** ("giữ cho đơn giản") và **YAGNI** ("bạn sẽ không cần nó": đừng làm thứ chưa ai cần). Một hàm 20 dòng chưa có lý do đổi thì không cần ba lớp và hai interface; một lớp chỉ có **một** cài đặt và chưa ai cần thay thì chưa cần interface. Cách làm hợp lý: viết đơn giản, và **tách khi sự thay đổi có thật xuất hiện** (hoặc khi cần test mà không thay được). SOLID trả lời "tách thế nào cho đúng"; KISS/YAGNI trả lời "có cần tách bây giờ không".

## 💻 Ví dụ code

### Ví dụ 1 (S): `BaoCaoXau` làm ba việc, rồi tách

**Chủ đề: bảng điểm.** `BaoCaoXau` có `trungBinh` (1), `in` (2) và `luu` (3) (thêm trung bình vào `kho`, một dãy số thay cho file). Bản sau tách thành hàm `trungBinh` (4), hàm `inBaoCao` (5) và lớp `KhoLuu` (6).

(Từ đây các interface viết bằng `struct` cho gọn: mặc định `public`, [Bài 31](31-lop-dong-goi.md); kế thừa của `struct` cũng mặc định `public`, [Bài 32](32-ke-thua.md).)

```cpp
#include <iostream>
#include <vector>

// Truoc: mot lop lam ba viec (tinh, in, luu)
class BaoCaoXau {
public:
    explicit BaoCaoXau(std::vector<int> diem) : diem_(diem) {}
    double trungBinh() const {                                       // (1)
        double t = 0;
        for (int d : diem_) t += d;
        return t / diem_.size();
    }
    void in() const { std::cout << "Trung binh: " << trungBinh() << "\n"; }   // (2)
    void luu(std::vector<double>& kho) const { kho.push_back(trungBinh()); }   // (3)
private:
    std::vector<int> diem_;
};

// Sau: moi viec mot cho
double trungBinh(const std::vector<int>& diem) {                     // (4)
    double t = 0;
    for (int d : diem) t += d;
    return t / diem.size();
}
void inBaoCao(double tb) { std::cout << "Trung binh: " << tb << "\n"; }    // (5)
class KhoLuu {                                                       // (6)
public:
    void them(double giaTri) { gia_.push_back(giaTri); }
    std::size_t soGiaTri() const { return gia_.size(); }
private:
    std::vector<double> gia_;
};

int main() {
    std::vector<int> diem = {7, 8, 9, 10};
    std::vector<double> kho;
    BaoCaoXau xau(diem);
    xau.in();
    xau.luu(kho);
    std::cout << "kho (truoc): " << kho.size() << " gia tri\n";

    inBaoCao(trungBinh(diem));
    KhoLuu kho2;
    kho2.them(trungBinh(diem));
    std::cout << "kho (sau): " << kho2.soGiaTri() << " gia tri\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2), (3) | Bản xấu: một lớp, ba lý do đổi (công thức, cách in, nơi lưu); `in` và `luu` đều gọi `trungBinh` | `xau.diem_`: 7, 8, 9, 10 |
| `xau.in()`, `xau.luu(kho)` | In `8.5`; `luu` thêm một giá trị vào `kho` | `kho`: 1 giá trị |
| (4), (5), (6) | Bản sau: tính, in, lưu là ba chỗ riêng; đổi cách in chỉ sửa (5) | không đổi |
| `kho2.them(...)` | Cùng kết quả: một giá trị trong kho | `kho2.gia_`: 1 giá trị |

**Kết quả khi chạy:**

```text
Trung binh: 8.5
kho (truoc): 1 gia tri
Trung binh: 8.5
kho (sau): 1 gia tri
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Hai bản **cho cùng kết quả**: S không đổi hành vi, chỉ đổi chỗ phải sửa khi yêu cầu đổi.

### Ví dụ 2 (L, rồi O): hình vuông phá hợp đồng của hình chữ nhật

**Chủ đề: hình học.** Hàm `dungKyVong` (3) viết theo hợp đồng của `ChuNhatSua`: nhớ cao cũ, `datRong(5)`, kỳ vọng diện tích bằng `5 * caoCu` (4). `VuongSua` ghi đè `datRong` để giữ vuông (2). Bản sửa ở dưới: `Hinh`, `ChuNhat`, `Vuong` không kế thừa nhau. Cuối cùng thêm `TamGiac` (6) làm ví dụ cho O: `Hinh` và `tong` không đổi.

```cpp
#include <iostream>

// --- Ban vi pham Liskov: vuong ke thua chu nhat co the sua ---
class ChuNhatSua {
public:
    ChuNhatSua(int r, int c) : r_(r), c_(c) {}
    virtual ~ChuNhatSua() = default;
    virtual void datRong(int r) { r_ = r; }                          // (1)
    virtual void datCao(int c) { c_ = c; }
    int rong() const { return r_; }
    int cao() const { return c_; }
protected:
    int r_, c_;
};
class VuongSua : public ChuNhatSua {
public:
    explicit VuongSua(int canh) : ChuNhatSua(canh, canh) {}
    void datRong(int r) override { r_ = r; c_ = r; }                 // (2)
    void datCao(int c) override { r_ = c; c_ = c; }
};

bool dungKyVong(ChuNhatSua& h) {                                     // (3)
    int caoCu = h.cao();
    h.datRong(5);
    return h.rong() * h.cao() == 5 * caoCu;                          // (4)
}

// --- Ban sua: bo ke thua, dung giao dien chung ---
struct Hinh {
    virtual ~Hinh() = default;
    virtual int dienTich() const = 0;
};
struct ChuNhat : Hinh {
    int r, c;
    ChuNhat(int r_, int c_) : r(r_), c(c_) {}
    int dienTich() const override { return r * c; }
};
struct Vuong : Hinh {
    int canh;
    explicit Vuong(int c) : canh(c) {}
    int dienTich() const override { return canh * canh; }
};
int tong(const Hinh& a, const Hinh& b) { return a.dienTich() + b.dienTich(); }   // (5)

// --- Them kieu moi: chi viet them lop, KHONG sua Hinh va tong ---
struct TamGiac : Hinh {                                              // (6)
    int day, cao;
    TamGiac(int d, int c) : day(d), cao(c) {}
    int dienTich() const override { return day * cao / 2; }
};

int main() {
    ChuNhatSua cn(3, 4);
    VuongSua v(4);
    std::cout << "chu nhat: " << (dungKyVong(cn) ? "dung ky vong" : "vo ky vong") << "\n";
    std::cout << "vuong:    " << (dungKyVong(v) ? "dung ky vong" : "vo ky vong") << "\n";
    std::cout << "vuong sau do: " << v.rong() << " x " << v.cao() << "\n";
    std::cout << "tong (ban sua): " << tong(ChuNhat(3, 4), Vuong(4)) << "\n";
    std::cout << "tong (them tam giac): " << tong(TamGiac(6, 5), Vuong(4)) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (3), (4) với `cn` | Cao cũ 4; `datRong` (1) chỉ đổi rộng: 5 x 4 = 20, bằng `5 * caoCu` = 20: đúng kỳ vọng | `cn`: 5 x 4 |
| (2), (3), (4) với `v` | `v` là một `ChuNhatSua` (upcast, [Bài 32](32-ke-thua.md)); cao cũ 4; `datRong(5)` của vuông đổi cả cao: 5 x 5 = 25, khác 5 x 4 | `v`: 5 x 5 |
| (5) | Bản sửa: `tong` nhận hai `Hinh` (đối tượng tạm, sống tới hết câu lệnh); `Vuong` là 4 x 4 = 16, `ChuNhat` 3 x 4 = 12 | không có hàm sửa cạnh nên không có gì để phá |
| (6) | `TamGiac` là mã mới: 6 x 5 / 2 = 15, cộng `Vuong` 16 = 31; `Hinh` và `tong` không đổi dòng nào | |

**Kết quả khi chạy:**

```text
chu nhat: dung ky vong
vuong:    vo ky vong
vuong sau do: 5 x 5
tong (ban sua): 28
tong (them tam giac): 31
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Chương trình vẫn **biên dịch và chạy êm**: Liskov là lỗi thiết kế, không phải lỗi cú pháp, và trình biên dịch không bắt được. **Thử thay đổi** (đã chạy):

- **Đổi (2) thành `void datRong(int r) override { r_ = r; }`** (không đổi cao). Dòng vuông ra `dung ky vong`, nhưng `vuong sau do` thành `5 x 4`: hợp đồng cha giữ được mà **bất biến "hai cạnh bằng nhau"** của hình vuông thì vỡ. Hai cách viết, đều hỏng một trong hai.

### Ví dụ 3 (I): `MayIn` và `MayQuet` tách riêng

**Chủ đề đổi sang văn phòng: máy in, máy quét.** `MayIn` (1) và `MayQuet` (2) là hai interface một hàm. `MayInDon` (3) chỉ cài `MayIn`; `MayDaNang` (4) cài cả hai. `inBienLai` (5) chỉ cần `MayIn&`.

```cpp
#include <iostream>
#include <string>

struct MayIn {                                                       // (1)
    virtual ~MayIn() = default;
    virtual void in(const std::string& noiDung) = 0;
};
struct MayQuet {                                                     // (2)
    virtual ~MayQuet() = default;
    virtual std::string quet() = 0;
};

struct MayInDon : MayIn {                                            // (3)
    void in(const std::string& nd) override { std::cout << "[may in don] " << nd << "\n"; }
};
struct MayDaNang : MayIn, MayQuet {                                  // (4)
    void in(const std::string& nd) override { std::cout << "[may da nang] in: " << nd << "\n"; }
    std::string quet() override { return "anh-giay-A4"; }
};

void inBienLai(MayIn& may) { may.in("bien lai so 1"); }              // (5)
std::string luuBanQuet(MayQuet& may) { return "luu " + may.quet(); }

int main() {
    MayInDon don;
    MayDaNang nang;
    inBienLai(don);
    inBienLai(nang);
    std::cout << luuBanQuet(nang) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2), (3) | Hai interface một hàm; `MayInDon` chỉ biết in; không bị ép viết `quet` | `don`: một món `MayIn` |
| (4) | `MayDaNang` kế thừa hai interface, cài cả `in` và `quet` | `nang`: chứa hai phần giao diện |
| (5) | `inBienLai` nhận `MayIn&`: cả `don` lẫn `nang` đưa vào được; `luuBanQuet` chỉ nhận máy quét | |

**Kết quả khi chạy:**

```text
[may in don] bien lai so 1
[may da nang] in: bien lai so 1
luu anh-giay-A4
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. **Thử thay đổi** (đã chạy):

- **Gộp** thành một interface `MayVanPhong` có cả `in` và `quet` thuần ảo, cho `MayInDon` kế thừa nó và chỉ viết `in`. Biên dịch lỗi: `cannot declare variable ‘don’ to be of abstract type ‘MayInDon’`, vì `quet` vẫn thuần ảo. Muốn qua, máy in đơn phải viết một hàm `quet` giả: đó là dấu hiệu của interface quá to.

### Ví dụ 4 (D): `MayChuThat` và `MayChuGia`, test không gửi gì thật

**Chủ đề đổi sang báo động.** `MayChu` (1) là interface do bên cấp cao (`DichVuBaoDong`) cần. `MayChuThat` (2) in ra "gửi thật"; `MayChuGia` (3) ghi tin nhận vào `daNhan` và có thể giả vờ hỏng. `DichVuBaoDong` (4) là lớp; hàm tạo `explicit DichVuBaoDong(MayChu& mc)` nhận tham chiếu, và nó giữ `MayChu&` (5). Tin là nhiệt độ (số nguyên).

```cpp
#include <iostream>
#include <vector>

struct MayChu {                                                      // (1)
    virtual ~MayChu() = default;
    virtual bool gui(int doC) = 0;
};
struct MayChuThat : MayChu {                                         // (2)
    bool gui(int doC) override { std::cout << "[that] bao nong: " << doC << "\n"; return true; }
};
struct MayChuGia : MayChu {                                          // (3)
    bool hong;
    std::vector<int> daNhan;
    explicit MayChuGia(bool h) : hong(h) {}
    bool gui(int doC) override { daNhan.push_back(doC); return !hong; }
};

class DichVuBaoDong {                                                // (4)
public:
    explicit DichVuBaoDong(MayChu& mc) : mc_(mc) {}
    void baoNhiet(int doC) {
        if (doC <= 40) return;
        if (!mc_.gui(doC)) ++soLoi_;
    }
    int soLoi() const { return soLoi_; }
private:
    MayChu& mc_;                                                     // (5)
    int soLoi_ = 0;
};

int main() {
    MayChuThat that;
    DichVuBaoDong dvThat(that);
    dvThat.baoNhiet(45);

    MayChuGia tot(false);                                            // (6)
    DichVuBaoDong dv1(tot);
    dv1.baoNhiet(30);
    dv1.baoNhiet(45);
    std::cout << "gia tot: nhan " << tot.daNhan.size() << " tin, loi " << dv1.soLoi() << "\n";

    MayChuGia hong(true);
    DichVuBaoDong dv2(hong);
    dv2.baoNhiet(50);
    std::cout << "gia hong: nhan " << hong.daNhan.size() << " tin, loi " << dv2.soLoi() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2), (3) | Một interface, hai cài đặt: bản thật in ra; bản giả ghi vào `daNhan` | |
| (4), (5) | `DichVuBaoDong` chỉ biết `MayChu`; nó giữ **tham chiếu** tới món do người ngoài tạo | `dvThat.mc_` -> `that` |
| `dvThat.baoNhiet(45)` | 45 > 40: gọi `gui` của món thật, in một dòng | |
| (6), `dv1` | Giả tốt: 30 không gửi (không quá 40); 45 gửi: `daNhan` có 1 tin, không lỗi | `tot.daNhan`: 1 tin |
| `dv2` | Giả hỏng: `gui` trả `false`, `soLoi_` lên 1; tin vẫn được ghi | `hong.daNhan`: 1 tin |

**Kết quả khi chạy:**

```text
[that] bao nong: 45
gia tot: nhan 1 tin, loi 0
gia hong: nhan 1 tin, loi 1
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Hai dòng cuối là một bài kiểm thử nhỏ **không cần mạng**, và còn thử được trường hợp lỗi mà máy chủ thật khó tái hiện. Chú ý `DichVuBaoDong` không sở hữu máy chủ (giữ tham chiếu): người tạo phải để `MayChu` sống lâu hơn dịch vụ, cùng bẫy vòng đời ở [Bài 36](36-pattern-observer-strategy.md).

### Ví dụ 5 (composition và Rule of 0): `Xe` có `DongCo`

**Chủ đề đổi sang xe** (như [Bài 32](32-ke-thua.md)). `Xe` giữ `ten_`, `dongCo_`, `nhatKy_` làm thành viên (4) và **không viết hàm đặc biệt nào** (5), nên không có hàm hủy hay hàm sao chép/di chuyển do ta viết. `dongCo_{congSuat}` (2) khởi tạo `DongCo` bằng ngoặc nhọn. `Xe b = a;` (6) sao chép, `std::move(a)` (7) di chuyển.

```cpp
#include <iostream>
#include <string>
#include <utility>
#include <vector>

struct DongCo {
    int congSuat;
    void no() const { std::cout << "dong co " << congSuat << " ma luc no\n"; }
};

class Xe {                                                           // (1)
public:
    Xe(std::string ten, int congSuat) : ten_(std::move(ten)), dongCo_{congSuat} {}   // (2)
    void chay() {
        std::cout << ten_ << " chay: ";
        dongCo_.no();                                                // (3)
        nhatKy_.push_back("chay");
    }
    std::size_t soLanChay() const { return nhatKy_.size(); }
private:
    std::string ten_;                                                // (4)
    DongCo dongCo_;
    std::vector<std::string> nhatKy_;
};                                                                   // (5) khong co ham dac biet nao

int main() {
    Xe a("xe a", 90);
    a.chay();
    Xe b = a;                                                        // (6)
    b.chay();
    Xe c = std::move(a);                                             // (7)
    std::cout << "b: " << b.soLanChay() << ", c: " << c.soLanChay() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2), (3) | Hàm tạo nhận `string` theo giá trị rồi `std::move` vào `ten_` để khỏi chép thêm; `Xe` **dùng** `DongCo` qua thành viên; bên ngoài chỉ thấy `chay()`, không thấy `no()` | `a`: `ten_`, `dongCo_`, `nhatKy_` ["chay"] sau lần chạy đầu |
| (6) | `b` là bản sao: mỗi thành viên tự sao chép mình (chuỗi, động cơ, vector), nên `b.nhatKy_` cũng có 1 mục | `b` độc lập với `a` |
| `b.chay()` | `b.nhatKy_` thành 2 mục; `a` không đổi | |
| (7) | `c` lấy ruột của `a` bằng hàm di chuyển do trình biên dịch sinh; `c.nhatKy_` có 1 mục (của `a`) | `a`: không dùng nữa ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)) |

**Kết quả khi chạy:**

```text
xe a chay: dong co 90 ma luc no
xe a chay: dong co 90 ma luc no
b: 2, c: 1
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. **Thử thay đổi** (đã chạy):

- **Đổi `dongCo_` thành `std::unique_ptr<DongCo>`** (tạo bằng `std::make_unique<DongCo>(congSuat)`, gọi `dongCo_->no()`, thêm `#include <memory>`). Lớp vẫn **không viết hàm đặc biệt nào**, nhưng `Xe b = a;` thành lỗi `use of deleted function ‘Xe::Xe(const Xe&)’`: `unique_ptr` không sao chép được nên `Xe` cũng không. Bỏ dòng sao chép (chỉ giữ di chuyển) thì chạy tốt, in `c: 1`. Rule of 0 nghĩa là "để thành viên quyết định", không phải "mọi lớp đều chép được".

## Go: không có kế thừa nên composition và interface nhỏ là mặc định

!!! info "Bạn biết Go?"
    Mình đã chạy chương trình Go 1.27.1 nhỏ (`go vet` sạch) để kiểm các ý dưới đây.
    - **Composition là cách duy nhất**: Go không có kế thừa; dùng lại bằng trường hoặc **embedding** ([Bài 32](32-ke-thua.md)). `type Xe struct { DongCo; Ten string }` rồi `x.No()` chạy; gán `y := x` là sao chép cả struct (không viết gì thêm), đổi `y.CongSuat` không đụng `x` (mình in `90 1`). Không có upcast nên không có chuyện Liskov kiểu "Con thay Cha" qua struct; thay thế được chỉ qua **interface**.
    - **Interface ngầm định làm I và D gần như miễn phí**: `type MayChu interface{ Gui(tin string) bool }` định nghĩa **ngay ở gói dùng nó**; `MayChuThat` và `MayChuGia` chỉ cần có method `Gui`, không khai báo gì. Mình truyền cả hai vào `DichVu`: cái thật in `[that] nong 45`, cái giả ghi `[nong 50]`. Kiểu thiếu method thì lỗi biên dịch (`Vuong does not implement Hinh (missing method DienTich)`).
    - **"Accept interfaces, return structs"** (nhận interface, trả struct): hàm nhận interface nhỏ ở tham số (dễ thay bằng đồ giả), nhưng trả về kiểu cụ thể (người dùng lấy đủ chức năng, không bị che). `NewDichVu(mc MayChu) *DichVu` là dạng đó. Đây là **tục lệ** của cộng đồng Go, không phải luật của ngôn ngữ.
    - Interface Go thường **một hoặc hai method** (`io.Reader`), hợp với I. Bên C++ bạn ghi `: public MayIn` rõ ràng; bên Go quan hệ đó nằm ở chỗ dùng, không nằm ở khai báo của kiểu.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "SOLID là gì? (nói từng chữ cái với ví dụ)"
    S: một lớp một lý do để đổi (tách `BaoCao` thành tính, in, lưu). O: thêm hành vi bằng thêm mã, không sửa mã cũ (thêm `TamGiac` mà `tong` không đổi; registry factory, Strategy). L: lớp con dùng được ở mọi chỗ lớp cha dùng mà không phá hợp đồng (hình vuông không thay được hình chữ nhật có `datRong`). I: nhiều interface nhỏ (`MayIn`, `MayQuet` thay cho `MayVanPhong`). D: lớp cấp cao phụ thuộc interface (`DichVuBaoDong` nhận `MayChu&`, test bằng `MayChuGia`). Thêm: đây là nguyên tắc, áp cứng nhắc thì thành thiết kế thừa.

??? question "Liskov là gì? Cho ví dụ vi phạm."
    Ở đâu dùng đối tượng lớp cha thì thay bằng lớp con vẫn đúng: lớp con giữ hợp đồng của cha (điều kiện người dùng được trông đợi) và các bất biến. Ví dụ vi phạm: `VuongSua` kế thừa `ChuNhatSua` có `datRong` ([Bài 32](32-ke-thua.md) gọi là `HinhVuong`, `HinhChuNhat`); hàm viết cho chữ nhật kỳ vọng "đổi rộng thì cao giữ nguyên", vuông phải đổi cả cao nên vỡ (mình chạy). Cách sửa: bỏ kế thừa, dùng interface `Hinh` chung, hoặc cho lớp bất biến không có hàm sửa cạnh.

??? question "Dependency Inversion khác Dependency Injection thế nào?"
    Inversion là **nguyên tắc**: lớp cấp cao và cấp thấp cùng phụ thuộc một interface, interface do bên cấp cao định ra. Injection là **kỹ thuật**: đưa thứ cần dùng vào qua hàm tạo hay tham số, không tự tạo bên trong. Injection là cách phổ biến để thực hiện inversion, và cho phép thay bằng đối tượng giả khi test; nhưng có thể inject một lớp cụ thể (vẫn là Injection mà không có Inversion).

??? question "Composition hay inheritance?"
    Mặc định nghiêng về composition (has-a): chỉ lộ những hàm bạn chọn, ghép lỏng, đổi được sau này, và thường để Rule of 0 sinh đúng các hàm đặc biệt. Kế thừa công khai chỉ khi đúng is-a theo nghĩa Liskov và bạn cần đa hình qua con trỏ/tham chiếu cha (hàm hủy ảo). "Chỉ muốn dùng lại hàm của cha" không phải lý do để kế thừa.

??? question "Danh sách ngắn các câu OOP hay gặp (mỗi câu một dòng, kèm bài đã dạy)"
    - **`class` khác `struct`?** Chỉ khác mức truy cập mặc định (`private` / `public`): [Bài 31](31-lop-dong-goi.md).
    - **Thứ tự constructor/destructor?** Cha, rồi thành viên theo thứ tự khai báo, rồi thân hàm tạo; hủy ngược lại: [Bài 31](31-lop-dong-goi.md), [Bài 32](32-ke-thua.md).
    - **`virtual` và vtable?** Gọi theo món thật lúc chạy; vtable/vptr là cách cài đặt thông dụng, chuẩn không bắt buộc: [Bài 33](33-da-hinh-virtual.md).
    - **Vì sao hàm hủy phải `virtual`?** Xóa qua `Cha*` mà hàm hủy cha không ảo là hành vi không xác định: [Bài 33](33-da-hinh-virtual.md).
    - **Object slicing?** Gán cả đối tượng con vào biến cha chỉ chép phần cha; dùng tham chiếu/con trỏ: [Bài 33](33-da-hinh-virtual.md).
    - **Abstract class và interface?** Lớp có hàm thuần ảo là lớp trừu tượng; C++ không có từ khóa `interface`, lớp chỉ gồm hàm thuần ảo và hàm hủy ảo đóng vai đó: [Bài 33](33-da-hinh-virtual.md).
    - **Đa kế thừa và kim cương?** Hai bản cha chung nên mơ hồ; kế thừa `virtual` hoặc tránh: [Bài 32](32-ke-thua.md).
    - **Template hay đa hình?** Lúc biên dịch với lúc chạy, bảng so sánh: [Bài 34](34-template.md), mục 8 bài này.
    - **Singleton?** Một thể hiện, `static` cục bộ an toàn luồng từ C++11; bị chê vì trạng thái toàn cục, khó test: [Bài 35](35-pattern-singleton-factory.md).
    - **Factory?** Hàm/registry trả `unique_ptr<Hinh>`, che lớp cụ thể: [Bài 35](35-pattern-singleton-factory.md).
    - **Observer?** Chủ đề báo cho danh sách qua interface hoặc callback; coi chừng vòng đời: [Bài 36](36-pattern-observer-strategy.md).
    - **Strategy?** Tách cách làm thay được: giao diện, `std::function` hoặc template: [Bài 36](36-pattern-observer-strategy.md).
    - **Gọi hàm ảo trong hàm tạo/hàm hủy?** Không đa hình ở đó, chạy bản của lớp đang dựng/hủy: [Bài 33](33-da-hinh-virtual.md).
    - **Rule of 3/5/0?** Tự quản lý tài nguyên thì quyết định cả 3/5 hàm; thành viên tự quản lý thì Rule of 0: [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Kế thừa chỉ để dùng lại hàm, hoặc tin 'toán nói vuông là chữ nhật'"
    Kế thừa công khai nói "Con thay được Cha ở mọi chỗ". Hình vuông kế thừa chữ nhật có `datRong` phá hợp đồng mà trình biên dịch không báo gì (Ví dụ 2). Muốn dùng lại: thành viên (Ví dụ 5); muốn thay thế: interface chung.

!!! warning "Lỗi 2: Áp SOLID khi chưa có lý do (thiết kế thừa)"
    Mỗi lớp một interface, mỗi hàm một lớp, trong khi chỉ có một cài đặt và chưa ai cần thay: code dài, khó theo dõi, không lợi gì. Viết đơn giản trước, tách khi sự thay đổi hoặc nhu cầu test xuất hiện (mục 9).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="37" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Đọc đoạn sau (hai lớp như ở Ví dụ 2). Gọi `f` với một `VuongSua`, chuyện gì đúng?

```text
class ChuNhatSua { public: virtual void datRong(int r) { r_ = r; } ... };
class VuongSua : public ChuNhatSua { public: void datRong(int r) override { r_ = r; c_ = r; } };
void f(ChuNhatSua& h) {
    int caoCu = h.cao();
    h.datRong(5);          // f trông đợi: cao() vẫn bằng caoCu
}
```

- Trông đợi của `f` bị vỡ, vì `VuongSua` đổi cả cao khi đặt rộng
- Lỗi biên dịch, vì `VuongSua` ghi đè một hàm mà làm đổi hai thành viên cùng lúc
- `f` vẫn đúng, vì `VuongSua` ghi đè bằng `override` nên khớp hợp đồng của lớp cha
- `f` vẫn đúng, vì tham chiếu `ChuNhatSua&` chỉ cho `datRong` chạm phần của lớp cha

<p class="giai-thich" markdown>`VuongSua` đổi `c_` cùng lúc với `r_`, nên sau `datRong(5)` thì `cao()` không còn bằng `caoCu`: trông đợi của hàm `f` viết cho chữ nhật bị phá, dù chương trình biên dịch và chạy bình thường (mình chạy ở Ví dụ 2). `override` chỉ bảo đảm chữ ký khớp, không bảo đảm hợp đồng được giữ. Không có quy tắc nào của C++ cấm ghi đè đổi nhiều thành viên, nên không có lỗi biên dịch. Và tham chiếu `ChuNhatSua&` vẫn trỏ tới một món `VuongSua`, nên hàm ảo chạy bản của vuông chứ không chỉ "phần của cha".</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** `Xe` chỉ muốn dùng lại hàm `no()` của `DongCo`, và không phải một loại động cơ. Nhận xét nào đúng?

```text
A:  class Xe : public DongCo { ... };    // gọi no() trực tiếp
B:  class Xe { DongCo dongCo_; ... };    // gọi dongCo_.no() bên trong
```

- Nên chọn A: kế thừa cho phép đổi động cơ lúc chạy dễ hơn thành viên
- Nên chọn B: ở A, `Xe` nhận được ở mọi chỗ cần `DongCo` và lộ hết hàm của nó
- Hai cách như nhau, vì cả hai đều chứa một phần `DongCo` trong đối tượng `Xe`
- Nên chọn B, vì thành viên làm `Xe` nhỏ hơn trong bộ nhớ

<p class="giai-thich" markdown>Thiết kế A nói "xe là một động cơ": hàm nhận `const DongCo&` nhận cả `Xe`, và mọi hàm `public` của động cơ lộ ra ngoài `Xe` ([Bài 32](32-ke-thua.md)). Thành viên (B) chỉ lộ những gì `Xe` chọn và đổi được sau này. Kế thừa không giúp đổi động cơ lúc chạy. Thành viên cũng không làm `Xe` nhỏ hơn: cả hai cách cùng chứa đúng một phần động cơ trong bộ nhớ. Hai cách khác nhau ở quan hệ kiểu (is-a và has-a), nên không "như nhau".</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. Chuyện gì xảy ra ở dòng `Xe b = a;`?

```text
class Xe {
    std::string ten_;
    std::vector<std::string> nhatKy_;
};                              // không viết hàm đặc biệt nào
Xe a;  /* nhatKy_ của a có 3 mục */
Xe b = a;
```

- Lỗi biên dịch, vì `Xe` chưa có hàm tạo sao chép tự viết
- Chạy được, nhưng `b.nhatKy_` dùng chung vùng nhớ với `a.nhatKy_`
- Chạy được, nhưng `ten_` của `b` rỗng vì `string` không chép ngầm
- Chạy được, `b` có bản sao riêng của `ten_` và `nhatKy_` (3 mục)

<p class="giai-thich" markdown>Hàm tạo sao chép do trình biên dịch sinh ra chép **từng thành viên** bằng hàm sao chép của chính thành viên đó; `std::string` và `std::vector` tự sao chép sâu, nên `b` có bản riêng (Rule of 0, Ví dụ 5). Không phải viết tay: lớp không giữ tài nguyên thô thì hàm sinh sẵn đủ dùng. Dùng chung vùng nhớ chỉ xảy ra khi thành viên là con trỏ thô bị chép nông ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)), không phải `vector`. Và `std::string` được chép bình thường khi lớp chứa nó được chép, nên `ten_` không rỗng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn sau. Chuyện gì xảy ra khi biên dịch `main`?

```text
class MayVanPhong {
public:
    virtual ~MayVanPhong() = default;
    virtual void in(const std::string&) = 0;
    virtual std::string quet() = 0;
};
class MayInDon : public MayVanPhong {
public:
    void in(const std::string& nd) override { std::cout << nd; }
};
int main() { MayInDon don; }
```

- Biên dịch được, và `don.quet()` sau này trả về chuỗi rỗng
- Lỗi biên dịch: `in` thiếu chữ `virtual` nên `override` không khớp
- Lỗi liên kết: `quet` được khai báo mà chưa có định nghĩa nào
- Lỗi biên dịch: `MayInDon` vẫn trừu tượng vì chưa viết `quet`

<p class="giai-thich" markdown>Lớp con chưa viết hết hàm thuần ảo thì vẫn là lớp trừu tượng và không tạo được đối tượng, nên lỗi hiện ngay lúc biên dịch (mình chạy: `cannot declare variable ‘don’ to be of abstract type`). `override` ở `in` khớp chữ ký của hàm ảo cha, nên không có lỗi ở đó. Chương trình không qua được biên dịch, nên cũng không tới bước liên kết, và không có bản `quet` mặc định nào trả chuỗi rỗng. Đây chính là lý do Interface Segregation: tách `MayIn` và `MayQuet` để máy in đơn không bị ép viết hàm nó không có.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Câu nào về Dependency Inversion và Dependency Injection là đúng?

- Hai tên của cùng một thứ, vì cả hai đều nói đưa lớp cụ thể vào hàm tạo
- Inversion là nguyên tắc về hướng phụ thuộc; Injection là kỹ thuật đưa vào từ ngoài
- Injection là nguyên tắc thiết kế, còn Inversion là cách viết hàm tạo nhận tham số
- Inversion bắt buộc dùng thư viện tiêm phụ thuộc, còn Injection thì viết tay được

<p class="giai-thich" markdown>Inversion nói về **hướng phụ thuộc**: cấp cao và cấp thấp cùng dựa vào một interface. Injection nói về **cách đưa** thứ cần dùng vào đối tượng (tham số, hàm tạo), và thường dùng để đạt được Inversion. Hai thứ khác nhau: có thể inject một lớp cụ thể mà chẳng có interface nào. Không bên nào đòi thư viện: ở Ví dụ 4 chỉ dùng hàm tạo bình thường.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn Go sau. Hai dòng in ra gì?

```text
type DongCo struct{ CongSuat int }
type Xe struct {
    DongCo
    Ten string
}
x := Xe{DongCo{90}, "a"}
y := x
y.CongSuat = 1
fmt.Println(x.CongSuat, y.CongSuat)
```

- `90 1`, vì `y := x` sao chép cả struct kể cả phần nhúng
- `1 1`, vì phần nhúng `DongCo` được dùng chung giữa `x` và `y`
- Lỗi biên dịch, vì `y := x` không sao chép được struct có phần nhúng
- `90 0`, vì `y := x` chỉ chép `Ten`, phần nhúng `DongCo` về giá trị mặc định

<p class="giai-thich" markdown>Struct Go truyền và gán theo giá trị: `y := x` chép toàn bộ, kể cả phần nhúng `DongCo`, nên đổi `y.CongSuat` không đụng `x` (mình chạy: `90 1`). Phần nhúng không phải con trỏ, nên không có chuyện dùng chung. Struct có phần nhúng sao chép bình thường. Và `y.CongSuat` là trường được nâng lên, gán vào nó có hiệu lực trên `y`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **SOLID** là năm nguyên tắc, không phải luật: S một lý do để đổi; O thêm mã chứ không sửa mã cũ; L lớp con giữ hợp đồng của cha (vuông/chữ nhật có `datRong` vỡ, mình chạy; sửa bằng interface `Hinh` chung); I interface nhỏ; D phụ thuộc interface.
2. **Dependency Inversion** là nguyên tắc (cấp cao và cấp thấp cùng dựa vào interface do cấp cao định, nên mũi tên phụ thuộc phía cấp thấp đổi chiều); **Dependency Injection** là kỹ thuật đưa phụ thuộc vào, nhờ đó test bằng `MayChuGia`.
3. **Composition hơn inheritance** (`Xe` có `DongCo`); kế thừa công khai chỉ khi đúng is-a. **Rule of 0**: thành viên tự quản lý thì không viết hàm đặc biệt (thêm `unique_ptr` thì lớp chỉ di chuyển được, mình chạy).
4. Chọn lớp trừu tượng (nhiều loại, nhiều thao tác), template (kiểu biết lúc viết) hay `std::function` (một hành động nhỏ); KISS/YAGNI: tách khi thay đổi có thật, SOLID cứng nhắc là thiết kế thừa.
5. Go không có kế thừa nên mặc định là composition và interface nhỏ định nghĩa ở nơi dùng ("accept interfaces, return structs", tục lệ); phỏng vấn OOP: danh sách một dòng mỗi câu, liên kết Bài 31–36.
