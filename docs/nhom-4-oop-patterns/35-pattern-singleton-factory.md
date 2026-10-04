# Bài 35 — Singleton và Factory: hai mẫu thiết kế, và vì sao nên dùng ít

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được **design pattern** là gì (tên chung cho một lời giải mẫu, như từ vựng giữa lập trình viên, không phải luật) và vì sao dùng bừa là over-engineering.
    - Viết **Singleton** kiểu `static` cục bộ (hàm tạo `private`, `= delete` sao chép), chạy thật 8 luồng cùng gọi lần đầu mà chỉ tạo **một** lần, và nói đúng chuẩn: từ C++11 việc khởi tạo này an toàn luồng (hay gọi là "magic statics").
    - Chỉ ra bằng chương trình chạy thật vì sao Singleton bị chê (phụ thuộc ngầm, khó test, thứ tự hủy), và dùng **truyền phụ thuộc vào** (dependency injection) thay thế.
    - Viết **Simple Factory** trả `std::unique_ptr<Hinh>`, hiểu đó là chuyển sở hữu cho người gọi, làm "đăng ký kiểu mới không sửa hàm factory" bằng `map` + `std::function`; nhận ra Factory Method, Abstract Factory, Builder; so với Go (`sync.Once`, `NewX`, functional options, đã chạy Go 1.27.1).

**Bạn cần biết trước:** [Bài 33](33-da-hinh-virtual.md) (`Hinh`, hàm ảo, `vector<unique_ptr<Hinh>>`), [Bài 31](31-lop-dong-goi.md) (hàm tạo `private`, thành viên `static`, `this`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`= delete`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `make_unique`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến `static` cục bộ), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) và [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (luồng, data race, `mutex`, `lock_guard`), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`map`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`).

## 🧠 Câu chuyện mở đầu

Hai thợ mộc nói với nhau "chỗ này làm mộng đuôi én", và cả hai hiểu ngay mà không phải vẽ lại cách ghép. **Design pattern (mẫu thiết kế)** cũng vậy: một **cái tên** cho một cách tổ chức code đã được dùng nhiều lần cho một vấn đề thiết kế hay gặp. Điều có giá trị nhất là **từ vựng chung**: nói "chỗ này là factory", đồng nghiệp biết bạn định làm gì.

Bài này kể hai mẫu, và đều gắn với xưởng đồ chơi. **Singleton** là "bản vẽ chỉ cho làm đúng **một** món, treo ở bảng treo tường" ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)): ví dụ một cuốn sổ ghi chép chung của cả xưởng. **Factory** là "quầy nhận đơn": khách nói tên loại, quầy làm ra món và đưa lại. Từ phần Factory, ví dụ dùng lại `Hinh` của [Bài 33](33-da-hinh-virtual.md) (tính diện tích cho gọn); mình sẽ nói rõ lúc chuyển.

!!! info "Chỗ nào ví von không còn đúng?"
    Bảng treo tường thì **ai trong xưởng cũng thấy và sửa được**: chính điều này làm Singleton bị chê (mục 3). Quầy nhận đơn đời thường chỉ đưa món, còn quầy của C++ đưa món **kèm quyền sở hữu** (`unique_ptr`): người nhận phải lo bỏ nó đi, và `unique_ptr` làm việc đó tự động.

## 📖 Giải thích

### 1. Design pattern là gì, và đừng lạm dụng

Một pattern gồm: một vấn đề hay gặp, một cách giải đã được kiểm chứng, và một cái tên. Cuốn sách kinh điển về chủ đề này (1994) liệt kê 23 mẫu; bài chỉ dạy những mẫu hay bị hỏi. Pattern là **từ vựng và gợi ý**, không phải luật. Cảnh báo chính là **over-engineering** (thiết kế quá tay): thêm lớp, interface, factory cho việc mà một hàm thường là đủ. Chỉ dùng khi code đã có vấn đề nó giải; có pattern còn biến mất khi ngôn ngữ có sẵn công cụ, như lambda (Bài 36 sẽ gặp lại).

### 2. Singleton: một thể hiện duy nhất, truy cập toàn cục

Mục tiêu có hai vế: cả chương trình chỉ có **một** đối tượng của lớp đó, và ở đâu cũng lấy được nó. Cách viết gọn nhất trong C++ là một hàm `static` có **biến `static` cục bộ** ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md): sinh ra ở lần chạy qua khai báo đầu tiên, chết lúc chương trình kết thúc): `static SoGhi& lay() { static SoGhi so; return so; }`. Kiểu viết này quen gọi là **Meyers singleton**. Ví dụ 1 chạy thật.

Muốn "chỉ một" thật sự thì cần ba mảnh ghép. Hàm tạo để `private` (bên ngoài không tạo thêm được). Hàm sao chép và phép gán sao chép `= delete` ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)), nếu không `SoGhi a = SoGhi::lay();` vẫn chép ra bản thứ hai (mình đã chạy, Ví dụ 1, Thử thay đổi). Và một hàm `static` như `lay()` để lấy đối tượng, trả **tham chiếu** chứ không trả bản sao.

**Vì sao an toàn luồng.** Câu hỏi hay gặp: nếu nhiều luồng ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) cùng gọi `lay()` lần đầu cùng lúc, hàm tạo có chạy nhiều lần không? Từ **C++11**, chuẩn quy định không: nếu một luồng đang khởi tạo biến `static` cục bộ thì luồng đến sau **chờ** tới khi nó xong. Cơ chế này không chính thức hay gọi là **"magic statics"**; chuẩn trước C++11 chưa có khái niệm luồng nên không hứa gì.

Hai giới hạn cần nhớ. Một: chỉ **việc khởi tạo** được bảo vệ; dùng đối tượng sau đó (như `ghi` ở Ví dụ 1) vẫn cần khóa của riêng bạn ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)), nếu không là data race. Hai: cách tự viết "kiểm con trỏ rồi tạo" là lỗi (Ví dụ 1, Thử thay đổi).

### 3. Vì sao Singleton bị chê

Singleton là biến toàn cục mặc áo đẹp, nên mang tật của biến toàn cục. Ba điều dưới đây mình đã chạy thật:

- **Phụ thuộc ngầm, trạng thái toàn cục ẩn**: hàm `tinhTien1(int gia)` dùng Singleton bên trong, nhưng chữ ký không hề cho thấy nó đọc cấu hình thuế. Ai sửa trạng thái ở đâu cũng ảnh hưởng chỗ khác.
- **Khó test**: các bài kiểm chạy trong cùng một chương trình dùng chung một Singleton, nên bài này để lại trạng thái cho bài sau. Ví dụ 2 cho thấy kết quả sai vì thứ tự chạy.
- **Thứ tự hủy**: các Singleton bị hủy lúc kết thúc chương trình, theo thứ tự **ngược** với thứ tự tạo xong. Nếu hàm hủy của một cái dùng một cái đã bị hủy trước đó, đó là hành vi không xác định (Ví dụ 3, ASan báo lỗi thật).

Vì thế nhiều người coi lạm dụng Singleton là **anti-pattern** (cách làm hay gây hại). Với thứ thật sự duy nhất, gần như chỉ ghi vào (như sổ nhật ký) nó vẫn được dùng; vấn đề là khi nó thành đường tắt dùng khắp nơi.

### 4. Thay thế: truyền phụ thuộc vào (dependency injection)

**Dependency injection** (truyền phụ thuộc vào) nghĩa là: đối tượng hay hàm cần gì thì **nhận cái đó qua tham số** (hàm tạo hoặc hàm), thay vì tự đi lấy từ chỗ toàn cục. Chữ ký giờ nói rõ nó cần gì, và bài kiểm tự tạo một bản riêng. Hai cách hay dùng: nhận **tham chiếu** (`const BangThue&`) khi chỉ mượn dùng, hoặc nhận `std::unique_ptr` khi đối tượng **trở thành chủ** của thứ đó ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md): truyền bằng `std::move`). Ví dụ 2 làm cả hai.

### 5. Factory: quầy nhận đơn, trả về `unique_ptr<Base>`

**Từ đây ví dụ đổi sang `Hinh`** của [Bài 33](33-da-hinh-virtual.md) (ví von quầy nhận đơn vẫn dùng được: khách nói "tron", quầy trao một hình tròn). **Simple Factory** là một hàm nhận một "tên loại" và trả đúng loại đối tượng, ví dụ `taoHinh(const std::string& loai)`. Người gọi chỉ biết `Hinh`, không cần biết `HinhTron` hay `HinhChuNhat`, và việc chọn lớp con nằm gọn trong một hàm.

Kiểu trả về là `std::unique_ptr<Hinh>` vì hai lý do: hình khác loại có cỡ khác nhau nên phải đi qua con trỏ (Bài 33), và `unique_ptr` **chuyển quyền sở hữu** ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)) cho người gọi: món do factory `new` ra, người gọi giữ nó, hết đời thì tự xóa. Loại không biết thì trả `nullptr` (Ví dụ 4 dùng cách này; ném ngoại lệ cũng là một lựa chọn).

Hạn chế của `taoHinh` là chuỗi `if`: thêm một loại hình là phải **sửa hàm**. **Registry factory** (factory có sổ đăng ký) đảo lại chuyện đó: một `std::map<std::string, std::function<std::unique_ptr<Hinh>()>>` ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)) ghi "tên loại -> hàm làm ra nó". Muốn thêm loại mới, chỉ **đăng ký** thêm một dòng, không sửa lớp factory: ý "mở để mở rộng, đóng với sửa đổi" mà Bài 37 gọi là Open/Closed.

**Factory Method** là biến thể dùng kế thừa: lớp cha có hàm ảo trả sản phẩm, **lớp con quyết định tạo gì**, còn code ở lớp cha dùng sản phẩm mà không biết kiểu thật (Ví dụ 4, phần 3).

### 6. Chỉ nhắc: Abstract Factory và Builder

**Abstract Factory** là một interface có **nhiều** hàm tạo, tạo ra cả một **họ** đối tượng đi cùng nhau (ví dụ nhà máy "giao diện tối" tạo nút tối và cửa sổ tối, nhà máy "giao diện sáng" tạo bản sáng). Đổi nhà máy là đổi cả họ. Khác Simple Factory ở chỗ: nó tạo nhiều loại sản phẩm liên quan, không chỉ một.

**Builder** dành cho đối tượng có nhiều tham số, nhiều cái tùy chọn. Thay vì một hàm tạo dài, bạn gọi nối tiếp rồi chốt (mỗi hàm `setX` trả `*this`, [Bài 31](31-lop-dong-goi.md), để gọi nối được):

```text
Server s = ServerBuilder("a").port(8443).tls().build();
```

## 💻 Ví dụ code

### Ví dụ 1: Meyers singleton, tám luồng cùng gọi lần đầu

`SoGhi` là cuốn sổ chung. Hàm tạo ngủ 50 ms để các luồng kịp "dồn" vào lúc đang khởi tạo, và đếm số lần nó chạy bằng `std::atomic` ([Bài 28](../nhom-3-da-luong/28-atomic.md)). Tám luồng cùng lấy sổ và ghi một dòng.

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

std::atomic<int> soLanTao{0};

class SoGhi {
public:
    static SoGhi& lay() {                                           // (1)
        static SoGhi so;                                            // (2)
        return so;
    }
    SoGhi(const SoGhi&) = delete;                                   // (3)
    SoGhi& operator=(const SoGhi&) = delete;

    void ghi(const std::string& dong) {                             // (4)
        std::lock_guard<std::mutex> khoa(m_);
        dong_.push_back(dong);
    }
    int soDong() { std::lock_guard<std::mutex> khoa(m_); return static_cast<int>(dong_.size()); }

private:
    SoGhi() {                                                       // (5)
        ++soLanTao;
        std::this_thread::sleep_for(std::chrono::milliseconds(50)); // (6)
    }
    std::mutex m_;
    std::vector<std::string> dong_;
};

int main() {
    const int N = 8;
    SoGhi* diaChi[N];
    std::vector<std::thread> cacLuong;
    for (int i = 0; i < N; ++i) {
        cacLuong.emplace_back([i, &diaChi] {                        // (7)
            SoGhi& so = SoGhi::lay();
            diaChi[i] = &so;
            so.ghi("mot dong");
        });
    }
    for (auto& t : cacLuong) t.join();
    bool giongNhau = true;
    for (int i = 1; i < N; ++i) giongNhau = giongNhau && diaChi[i] == diaChi[0];
    std::cout << "so lan tao: " << soLanTao << "\n";
    std::cout << "cung mot doi tuong: " << giongNhau << "\n";
    std::cout << "so dong da ghi: " << SoGhi::lay().soDong() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (7) | Tám luồng chạy, mỗi luồng gọi `lay()` (1) và lưu địa chỉ nhận được vào ô `diaChi[i]` riêng của mình | `diaChi`: tám ô |
| (2) | Luồng đến trước vào khai báo `static`, gọi hàm tạo (5); các luồng đến sau **chờ** ở đây, không chạy hàm tạo | `so` đang dựng, trên "bảng treo tường" |
| (5), (6) | `++soLanTao`, rồi ngủ 50 ms cho chắc các luồng khác đã kịp tới | `soLanTao` = 1 |
| sau (2) | Dựng xong, các luồng chờ đi tiếp, cùng nhận tham chiếu tới **một** `so` | một `so`, tám địa chỉ trùng nhau |
| (4) | `ghi` khóa `m_` ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)) rồi thêm một dòng: khóa này là việc của bạn, `static` không lo | `dong_`: 8 dòng |

**Kết quả khi chạy:**

```text
so lan tao: 1
cung mot doi tuong: 1
so dong da ghi: 8
```

Mình chạy ba lần (cùng kết quả), với ASan + UBSan sạch và với ThreadSanitizer (`setarch $(uname -m) -R`) sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Thay (1)-(2) bằng cách tự viết**: `static SoGhi* p = nullptr; if (p == nullptr) p = new SoGhi; return *p;`. Ba lần chạy đều in `so lan tao: 8`, `cung mot doi tuong: 0`, `so dong da ghi: 1` (tám sổ khác nhau, chỉ một cái còn được `p` trỏ tới); ThreadSanitizer báo `data race` ngay ở dòng đó. Chuẩn không hứa số cụ thể nào: `sleep` ở (6) làm lỗi lộ rõ.
- **Viết `SoGhi s;` trong `main`**: g++ báo `‘SoGhi::SoGhi()’ is private within this context`.
- **Cái `= delete` ở (3) làm gì?** `SoGhi` có `std::mutex` (không chép được) nên bỏ (3) vẫn lỗi `use of deleted function`. Với lớp gọn `Cau` không có mutex, thiếu `= delete` thì `Cau a = Cau::lay();` **biên dịch được** và `&a != &Cau::lay()`: hai đối tượng; có `Cau(const Cau&) = delete;` thì lỗi `use of deleted function ‘Cau::Cau(const Cau&)’`.

### Ví dụ 2: Singleton khó test, truyền phụ thuộc vào thì dễ

Hai bản của cùng việc "tính tiền cộng thuế phần trăm". Bản 1 lấy thuế từ Singleton `CauHinh`; bản 2 nhận thuế qua tham số. Hai "bài kiểm" nối tiếp trong một chương trình, bài 2 mong thuế mặc định là 0.

```cpp
#include <iostream>
#include <memory>
#include <utility>

class CauHinh {                                         // Singleton
public:
    static CauHinh& lay() { static CauHinh c; return c; }
    CauHinh(const CauHinh&) = delete;
    CauHinh& operator=(const CauHinh&) = delete;
    void datThue(int phanTram) { thue_ = phanTram; }
    int thue() const { return thue_; }
private:
    CauHinh() {}
    int thue_ = 0;
};

int tinhTien1(int gia) {                                // (1)
    return gia + gia * CauHinh::lay().thue() / 100;
}

struct BangThue { int phanTram; };

int tinhTien2(int gia, const BangThue& bang) {          // (2)
    return gia + gia * bang.phanTram / 100;
}

class QuayThu {                                         // (3)
public:
    explicit QuayThu(std::unique_ptr<BangThue> bang) : bang_(std::move(bang)) {}
    int tinh(int gia) const { return tinhTien2(gia, *bang_); }
private:
    std::unique_ptr<BangThue> bang_;
};

int main() {
    std::cout << "--- Singleton ---\n";
    CauHinh::lay().datThue(10);                         // (4)
    std::cout << "kiem 1 (thue 10): " << tinhTien1(100) << ", mong 110\n";
    std::cout << "kiem 2 (thue mac dinh 0): " << tinhTien1(100) << ", mong 100\n";  // (5)

    std::cout << "--- Truyen phu thuoc vao ---\n";
    BangThue muoi{10};                                  // (6)
    BangThue khong{0};
    std::cout << "kiem 1: " << tinhTien2(100, muoi) << ", mong 110\n";
    std::cout << "kiem 2: " << tinhTien2(100, khong) << ", mong 100\n";
    QuayThu quay(std::make_unique<BangThue>(BangThue{5}));   // (7)
    std::cout << "quay thu thue 5: " << quay.tinh(100) << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `tinhTien1` tự đi lấy thuế từ Singleton: chữ ký `(int gia)` không nói điều này | đọc `thue_` ở bảng treo tường |
| (4) | "Bài kiểm 1" đặt thuế 10 vào Singleton | `thue_` = 10 |
| (5) | "Bài kiểm 2" mong 0 nhưng `thue_` vẫn là 10 từ bài trước: in 110 | `thue_` còn 10 |
| (2), (6) | `tinhTien2` nhận thuế qua tham số, chữ ký cho thấy cái nó cần; mỗi bài kiểm tự tạo `BangThue` riêng | hai biến cục bộ độc lập |
| (3), (7) | `QuayThu` nhận `unique_ptr<BangThue>` rồi `std::move` vào thành viên: nó là chủ của bảng thuế | `quay.bang_` giữ bảng thuế 5 |

**Kết quả khi chạy:**

```text
--- Singleton ---
kiem 1 (thue 10): 110, mong 110
kiem 2 (thue mac dinh 0): 110, mong 100
--- Truyen phu thuoc vao ---
kiem 1: 110, mong 110
kiem 2: 100, mong 100
quay thu thue 5: 105
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Bài kiểm 2 của bản Singleton sai **chỉ vì** bài 1 chạy trước và để lại thuế 10; bản truyền vào không có chuyện đó vì không còn trạng thái chung.

### Ví dụ 3: thứ tự hủy của hai Singleton

`Bao` (sổ ghi) và `KetNoi` đều là Singleton. Hàm hủy của `KetNoi` ghi một dòng vào `Bao`, nhưng `KetNoi` được tạo **trước** `Bao`. Khối này bị `// bo-qua-kiem-tra` vì có hành vi không xác định.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
#include <vector>

class Bao {
public:
    static Bao& lay() { static Bao b; return b; }
    void ghi(const std::string& dong) { dong_.push_back(dong); }
    ~Bao() { std::cout << "huy Bao\n"; }
private:
    Bao() { std::cout << "tao Bao\n"; }
    std::vector<std::string> dong_;
};

class KetNoi {
public:
    static KetNoi& lay() { static KetNoi k; return k; }
    ~KetNoi() {
        std::cout << "huy KetNoi\n";
        Bao::lay().ghi("dong ket noi");                 // (1)
    }
private:
    KetNoi() { std::cout << "tao KetNoi\n"; }           // (2)
};

int main() {
    KetNoi::lay();                                      // (3)
    Bao::lay().ghi("xin chao");                         // (4)
    std::cout << "het main\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3), (4) | `KetNoi` dựng xong **trước** (hàm tạo (2) không đụng `Bao`), rồi mới tới `Bao` | thứ tự xong: `KetNoi`, `Bao` |
| hết `main` | Hủy theo thứ tự ngược: `Bao` trước, `KetNoi` sau | `Bao` đã chết |
| (1) | Hàm hủy `KetNoi` gọi `Bao::lay().ghi(...)` trên `Bao` **đã bị hủy**: hành vi không xác định | `dong_` đã trả bộ nhớ |

**Kết quả khi chạy (không sanitizer):**

```text
tao KetNoi
tao Bao
het main
huy Bao
huy KetNoi
```

Thoát 0, **không báo gì**: lỗi nằm im. Chuẩn không hứa kết quả nào; với ASan trên g++ 11.4 mình thấy `AddressSanitizer: attempting double-free`, vết đi qua `push_back` trong `Bao::ghi`, gọi từ `KetNoi::~KetNoi`.

**Thử thay đổi (đã chạy):** thêm `Bao::lay();` vào đầu hàm tạo `KetNoi`. `Bao` dựng xong trước nên hủy sau: in `tao Bao`, `tao KetNoi`, `het main`, `huy KetNoi`, `huy Bao`, ASan sạch. Nhưng bạn phải **nhớ** thêm dòng đó cho mỗi cặp phụ thuộc.

### Ví dụ 4: Simple Factory, registry factory và Factory Method

Ba phần. Phần 1 là `taoHinh` (chuỗi `if`). Phần 2 là `XuongHinh` có sổ đăng ký: `HinhVuong` được định nghĩa **sau** `XuongHinh` và đăng ký trong `main`, `XuongHinh` không bị sửa. Để gọn, kích thước cố định (tròn bán kính 2, chữ nhật 3 x 4, vuông cạnh 5) và các lớp hình dùng `struct` (kế thừa và thành viên mặc định `public`, [Bài 32](32-ke-thua.md)). Phần 3 là Factory Method: `BanLamHinh::baoCao()` dùng một hình mà nó **không tự tạo**, lớp con quyết định qua hàm ảo `tao()`.

```cpp
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Hinh {
public:
    virtual ~Hinh() = default;
    virtual double dienTich() const = 0;
};

struct HinhTron : Hinh {
    double r;
    explicit HinhTron(double r_) : r(r_) {}
    double dienTich() const override { return 3.14 * r * r; }
};

struct HinhChuNhat : Hinh {
    double rong, cao;
    HinhChuNhat(double r_, double c_) : rong(r_), cao(c_) {}
    double dienTich() const override { return rong * cao; }
};

std::unique_ptr<Hinh> taoHinh(const std::string& loai) {            // (1)
    if (loai == "tron") return std::make_unique<HinhTron>(2);
    if (loai == "chu nhat") return std::make_unique<HinhChuNhat>(3, 4);
    return nullptr;                                                 // (2)
}

class XuongHinh {                                                   // (3)
public:
    void dangKy(const std::string& loai, std::function<std::unique_ptr<Hinh>()> ham) {
        kho_[loai] = std::move(ham);                                // (4)
    }
    std::unique_ptr<Hinh> tao(const std::string& loai) const {
        auto it = kho_.find(loai);
        if (it == kho_.end()) return nullptr;                       // (5)
        return it->second();                                        // (6)
    }
private:
    std::map<std::string, std::function<std::unique_ptr<Hinh>()>> kho_;
};

struct HinhVuong : Hinh {                                           // (7)
    double canh;
    explicit HinhVuong(double c) : canh(c) {}
    double dienTich() const override { return canh * canh; }
};

class BanLamHinh {                                                  // (10)
public:
    virtual ~BanLamHinh() = default;
    void baoCao() const {
        std::unique_ptr<Hinh> h = tao();
        std::cout << "dien tich: " << h->dienTich() << "\n";
    }
protected:
    virtual std::unique_ptr<Hinh> tao() const = 0;                  // (11)
};

class BanLamTron : public BanLamHinh {
protected:
    std::unique_ptr<Hinh> tao() const override { return std::make_unique<HinhTron>(2); }
};

class BanLamVuong : public BanLamHinh {
protected:
    std::unique_ptr<Hinh> tao() const override { return std::make_unique<HinhVuong>(5); }
};

int main() {
    std::cout << "--- Simple Factory ---\n";
    std::unique_ptr<Hinh> a = taoHinh("tron");                      // (8)
    std::cout << "tron: " << a->dienTich() << "\n";
    if (taoHinh("sao hoa") == nullptr) std::cout << "sao hoa: khong biet loai nay\n";

    std::cout << "--- Registry ---\n";
    XuongHinh xuong;
    xuong.dangKy("tron", [] { return std::make_unique<HinhTron>(2); });
    xuong.dangKy("chu nhat", [] { return std::make_unique<HinhChuNhat>(3, 4); });
    xuong.dangKy("vuong", [] { return std::make_unique<HinhVuong>(5); });   // (9)
    std::vector<std::string> don = {"tron", "chu nhat", "vuong", "tam giac"};
    for (const std::string& loai : don) {
        std::unique_ptr<Hinh> h = xuong.tao(loai);
        if (h) std::cout << loai << ": " << h->dienTich() << "\n";
        else std::cout << loai << ": chua dang ky\n";
    }

    std::cout << "--- Factory Method ---\n";
    BanLamTron tron;                                                // (12)
    BanLamVuong vuong;
    const BanLamHinh* ban[] = {&tron, &vuong};
    for (const BanLamHinh* b : ban) b->baoCao();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (8) | `taoHinh` chọn lớp con theo chuỗi; `unique_ptr<HinhTron>` đổi sang `unique_ptr<Hinh>` khi trả về; `a` **nhận** quyền sở hữu, hết `main` tự xóa món qua hàm hủy ảo | `a` -> một món `HinhTron` |
| (2) | Loại lạ trả `nullptr`; người gọi phải kiểm | không có món |
| (10)-(12) | `tao()` thuần ảo (11) là **factory method**, `protected` ([Bài 32](32-ke-thua.md)) để chỉ lớp con ghi đè. `baoCao()` ở lớp cha chạy `tao()` theo món thật (`BanLamTron` hay `BanLamVuong`), nên ra hình tương ứng; hết hàm `h` tự xóa hình | mỗi lần một `Hinh` tạm |
| (7), (9) | `HinhVuong` viết sau `XuongHinh`; (9) đăng ký lambda `[] { ... }` ("hàm làm ra hình vuông"), cất vào `kho_` ở (4) | `kho_`: 3 mục |
| (5) | `find` trả `end()` khi không có tên: phải kiểm trước, vì dùng `it->second` trên `end()` là sai | không đổi |
| (6) | `it->second` là một `std::function`; `()` gọi nó, nhận về `unique_ptr<Hinh>` mới và trả thẳng ra | mỗi lần một món mới |

**Kết quả khi chạy:**

```text
--- Simple Factory ---
tron: 12.56
sao hoa: khong biet loai nay
--- Registry ---
tron: 12.56
chu nhat: 12
vuong: 25
tam giac: chua dang ky
--- Factory Method ---
dien tich: 12.56
dien tich: 25
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Các **Thử thay đổi** (đã chạy):

- **Thêm `std::unique_ptr<Hinh> b = a;` sau (8)**: lỗi biên dịch `use of deleted function ‘std::unique_ptr<...>::unique_ptr(const std::unique_ptr<...>&)’`: chỉ một chủ, chuyển được chứ không chép được.
- **Cho `taoHinh` trả `Hinh*` (`return new HinhTron(2);`), `main` không `delete`**: LeakSanitizer báo `Direct leak of 16 byte(s)`. Trả `unique_ptr` làm quên xóa không xảy ra.
- **Thêm `BanLamHinh bb;` vào `main`**: `cannot declare variable ‘bb’ to be of abstract type ‘BanLamHinh’`, vì `tao()` thuần ảo ([Bài 33](33-da-hinh-virtual.md)).
- **Xóa dòng (5)**: với `"tam giac"` chưa đăng ký, mình gặp ASan báo `stack-use-after-scope` trong `std::function::operator()`. Chuẩn không hứa gì (hành vi không xác định): phải kiểm `end()`.

## Go: `sync.Once`, `NewX` trả interface, functional options

!!! info "Bạn biết Go?"
    Mình đã chạy chương trình Go 1.27.1 nhỏ (cả `go vet` và `-race` sạch) để kiểm các ý dưới đây.
    - **Singleton bằng `sync.Once`**: `once.Do(func() { ... })` chạy hàm **đúng một lần** dù nhiều goroutine cùng gọi, và mọi lời gọi `Do` chỉ trả về **sau khi** hàm đó chạy xong. Mình cho tám goroutine gọi `once.Do` với hàm ngủ 100 ms: hàm chạy 1 lần và không goroutine nào thấy nó chưa xong. Từ Go 1.21 có thêm `sync.OnceValue` (mình gọi hai lần, chữ "tinh mot lan" in một lần).
    - **Biến cấp gói + `init()`**: biến cấp gói được khởi tạo và hàm `init()` chạy **trước** `main` (mình in ra thứ tự: biến, `init()`, `main`). Biến cấp gói mà là trạng thái chung thì phàn nàn ở mục 3 vẫn đúng.
    - **Không có hàm tạo `private`, không có `= delete`**: Go giấu bằng tên chữ thường (không xuất khẩu ra ngoài gói). Cũng **không có hàm hủy** nên không có chuyện thứ tự hủy như Ví dụ 3.
    - **Factory**: `NewX` chỉ là **quy ước đặt tên**, không phải tính năng. `NewHinh(loai string) (Hinh, error)` trả interface `Hinh`; loại lạ trả `(nil, error)` và mình kiểm `h == nil` ra `true`. Không có `unique_ptr`: có GC nên không bàn chuyện ai sở hữu.
    - **Functional options** (Builder kiểu Go): `type Option func(*Server)`, rồi `NewServer(addr string, opts ...Option)`; gọi `NewServer("a", WithPort(8443), WithTLS())` ra `{addr:a port:8443 tls:true}`, còn `NewServer("a")` ra `{addr:a port:80 tls:false}`. Go không có tham số mặc định hay nạp chồng hàm nên hay dùng cách này.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Singleton là gì, cài thế nào cho an toàn luồng?"
    Singleton đảm bảo một lớp chỉ có một thể hiện và có điểm truy cập toàn cục. Trong C++: hàm tạo `private`, xóa hàm sao chép và phép gán, rồi `static T& lay() { static T t; return t; }`. Từ C++11 chuẩn quy định khởi tạo biến `static` cục bộ an toàn luồng (thường gọi là magic statics): luồng đến sau chờ luồng đang khởi tạo. Nhưng chỉ khởi tạo được bảo vệ, dùng đối tượng vẫn cần mutex.

??? question "Tại sao Singleton bị coi là anti-pattern?"
    Nó là trạng thái toàn cục: phụ thuộc bị giấu trong thân hàm (chữ ký không nói), nên khó hiểu và khó test (các bài kiểm dùng chung một đối tượng, bài này để lại trạng thái cho bài kia). Thứ tự hủy giữa các Singleton là ngược thứ tự tạo xong; hàm hủy dùng cái đã hủy là hành vi không xác định. Thay bằng truyền phụ thuộc vào (tham chiếu hoặc `unique_ptr` qua hàm tạo).

??? question "Factory vs Abstract Factory?"
    Factory (Simple Factory hoặc Factory Method) tạo **một loại** sản phẩm, chọn lớp cụ thể theo tham số hoặc theo lớp con. Abstract Factory là một interface có **nhiều** hàm tạo, tạo ra cả họ sản phẩm liên quan đi cùng nhau (ví dụ nút và cửa sổ cùng giao diện tối); đổi nhà máy là đổi cả họ. Factory Method dùng kế thừa (lớp con quyết định), Simple Factory chỉ là một hàm.

??? question "Factory để làm gì?"
    Tách việc **chọn lớp cụ thể** khỏi code dùng nó: người gọi chỉ biết `Hinh`, factory lo `HinhTron` hay `HinhChuNhat`. Trong C++ nó thường trả `unique_ptr<Base>`, tức chuyển sở hữu cho người gọi. Thêm loại mới thì sửa một chỗ, hoặc không sửa chỗ nào nếu dùng registry (`map` tên -> hàm tạo). Đừng thêm factory khi chỉ có một loại và không có kế hoạch thêm: đó là over-engineering.

??? question "Khi nào dùng Builder?"
    Khi đối tượng có nhiều tham số, trong đó nhiều cái tùy chọn, và hàm tạo dài dễ nhầm thứ tự. Builder cho gọi từng bước có tên (`.port(8443).tls().build()`) rồi tạo đối tượng một lần. Ở Go, tương đương là functional options.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tự viết kiểm-rồi-tạo cho Singleton"
    `if (p == nullptr) p = new T;` bị data race khi nhiều luồng gọi (Ví dụ 1, Thử thay đổi: tám bản). Dùng biến `static` cục bộ, và nhớ `= delete` sao chép kẻo `T a = T::lay();` âm thầm tạo bản thứ hai.

!!! warning "Lỗi 2: Factory trả con trỏ thô"
    `Hinh* taoHinh(...)` buộc người gọi nhớ `delete` (LeakSanitizer báo rò ở Ví dụ 4, Thử thay đổi). Trả `std::unique_ptr<Hinh>`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="35" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. Bốn luồng cùng gọi `lay()` lần đầu, đúng lúc nhau. Hàm tạo `Cau()` chạy mấy lần (g++ với `-std=c++17`)?

```text
class Cau {
public:
    static Cau& lay() { static Cau c; return c; }
private:
    Cau() { /* việc chậm */ }
};
```

- Có thể nhiều lần, vì chuẩn không bảo đảm gì cho biến `static` cục bộ khi nhiều luồng
- Đúng một lần, luồng đến sau chờ luồng đầu khởi tạo xong
- Bốn lần, vì mỗi luồng có bản `static` của riêng nó như `thread_local`
- Đúng một lần, nhưng chỉ khi quanh lời gọi `lay()` có `std::mutex` do mình viết

<p class="giai-thich" markdown>Từ C++11 chuẩn quy định việc khởi tạo biến `static` cục bộ an toàn luồng: luồng đến sau đứng chờ đến khi hàm tạo của luồng đầu chạy xong, nên hàm tạo chạy đúng một lần mà không cần khóa của bạn (Ví dụ 1 chạy tám luồng). Lời "chuẩn không bảo đảm" chỉ đúng cho thời trước C++11. Biến `static` thường dùng chung cho mọi luồng, khác với `thread_local` ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Còn mutex tự viết thì chỉ cần khi dùng đối tượng sau đó, không cần cho việc khởi tạo.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau. Chuyện gì xảy ra khi biên dịch và chạy?

```text
class Cau {
public:
    static Cau& lay() { static Cau c; return c; }
private:
    Cau() {}
};
int main() { Cau a = Cau::lay(); }
```

- Lỗi biên dịch, vì hàm tạo `Cau()` ở `private` nên không tạo thêm `Cau` nào được
- Biên dịch được, `a` chỉ là cái tên khác của đối tượng trong `lay()` vì `lay` trả tham chiếu
- Lỗi biên dịch, vì `Cau` chưa khai báo hàm tạo sao chép nên không sao chép được
- Biên dịch được, `a` là bản sao thứ hai vì không có `= delete` chặn hàm sao chép

<p class="giai-thich" markdown>Hàm tạo sao chép do trình biên dịch tự sinh là `public`, và `Cau a = ...` gọi nó (không phải hàm tạo `private`), nên đoạn này biên dịch được và tạo ra đối tượng thứ hai, nằm ở địa chỉ khác (mình đã chạy một bản tương tự). Vì khai báo `Cau a` (không có `&`) là một biến mới, nó không thể là "tên khác" của đối tượng cũ. Chuyện "chưa khai báo hàm tạo sao chép" cũng không gây lỗi: trình biên dịch tự sinh nó. Thêm `Cau(const Cau&) = delete;` mới chặn được.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Hàm `tinhTien(int gia)` bên trong gọi `CauHinh::lay().thue()` (Singleton). Điểm yếu thiết kế chính của cách này là gì?

- Chữ ký hàm giấu mất sự phụ thuộc, và các bài kiểm chạy chung chương trình dùng chung trạng thái
- Singleton không cho dùng bên trong một hàm, nên đoạn này không biên dịch được
- Khởi tạo Singleton không an toàn luồng, vì biến `static` cục bộ có thể bị tạo nhiều lần
- Singleton buộc cấp phát bằng `new`, nên mỗi lần gọi `tinhTien` đều bị rò bộ nhớ

<p class="giai-thich" markdown>Hàm đọc trạng thái toàn cục mà chữ ký không nói, nên khó hiểu, và bài kiểm này để lại giá trị cho bài kiểm sau (Ví dụ 2: kiểm 2 ra 110 thay vì 100). Kiểu Meyers singleton dùng được trong mọi hàm bình thường và biên dịch tốt. Nó cũng không dùng `new`, chính biến `static` cục bộ tự lo vòng đời. Và việc khởi tạo của biến `static` cục bộ là an toàn luồng từ C++11, nên "tạo nhiều lần" không phải điểm yếu của cách viết này.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Hàm factory khai báo `std::unique_ptr<Hinh> taoHinh(const std::string& loai);`. Kiểu trả về này có nghĩa gì với người gọi?

- Factory vẫn giữ món và người gọi chỉ mượn, nên factory tự xóa nó khi chương trình kết thúc
- Người gọi phải tự `delete` con trỏ lấy qua `get()` khi dùng xong, nếu không món sẽ bị rò
- Người gọi nhận quyền sở hữu, và món tự được xóa khi `unique_ptr` hết đời
- Mỗi lần gọi trả về cùng một món đã tạo sẵn, giống cách Singleton làm

<p class="giai-thich" markdown>`unique_ptr` trả về giá trị chuyển quyền sở hữu cho người nhận: khi biến nhận nó ra khỏi phạm vi, món bị xóa qua hàm hủy ảo, không cần `delete` tay ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)). Factory không giữ lại gì để mà "tự xóa sau". Tự `delete` con trỏ của `get()` còn gây xóa hai lần, vì `unique_ptr` cũng sẽ xóa. Và mỗi lần gọi `taoHinh` tạo món mới: trả lại cùng một món là chuyện của Singleton.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn sau (dùng `Hinh`, `HinhTron` như trong bài). Điều gì đúng về dòng `h`?

```text
std::map<std::string, std::function<std::unique_ptr<Hinh>()>> kho;
kho["tron"] = [] { return std::make_unique<HinhTron>(1); };
auto it = kho.find("vuong");
auto h = it->second();
```

- `h` là `nullptr`, vì `find` không thấy tên thì `second()` trả về con trỏ rỗng
- Hành vi không xác định, vì `find` không thấy trả `kho.end()` mà ta lại dùng `it->second`
- Ném `std::out_of_range`, vì tên `"vuong"` chưa có trong `kho`
- Lỗi biên dịch, vì lambda trả `unique_ptr<HinhTron>` mà `kho` cần `unique_ptr<Hinh>`

<p class="giai-thich" markdown>`find` không thấy khóa thì trả `end()`, một vị trí không trỏ tới phần tử nào, nên đọc `it->second` là hành vi không xác định: phải kiểm `it != kho.end()` trước (Ví dụ 4, dòng (5)). `second()` không tự trả `nullptr`. Chuyện ném `out_of_range` là của `at()`, không phải của `find`. Còn lambda trả `unique_ptr<HinhTron>` thì biên dịch được, vì kết quả đổi được sang `unique_ptr<Hinh>` (đúng như ba lambda ở Ví dụ 4).</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Tám goroutine cùng gọi `once.Do(f)` (`once` là `sync.Once`). Điều nào đúng?

- `f` chạy đúng một lần, và mọi lời gọi `Do` chỉ trả về sau khi `f` đã chạy xong
- `f` chạy đúng một lần, nhưng goroutine đến sau trả về ngay mà không chờ `f` xong
- `f` có thể chạy nhiều lần, `sync.Once` chỉ giảm bớt số lần chạy
- Phải tự bọc `once.Do` bằng `sync.Mutex`, nếu không `f` có thể chạy nhiều lần

<p class="giai-thich" markdown>Mình đã chạy tám goroutine với `f` ngủ 100 ms: `f` chạy 1 lần và không goroutine nào thấy `f` chưa xong khi `Do` trả về. Việc chờ đó chính là điều khiến `once.Do` dùng được cho khởi tạo Singleton. `Do` tự an toàn khi nhiều goroutine gọi, nên không cần mutex bọc ngoài. Và nó cũng không chỉ "giảm bớt": số lần chạy đúng bằng một.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Design pattern** là tên chung cho một lời giải mẫu của vấn đề thiết kế hay gặp, tức từ vựng chung, không phải luật; dùng khi code có vấn đề đó, còn không là over-engineering. Bài này có Singleton, Factory (Simple, Method), nhắc Abstract Factory và Builder.
2. **Singleton**: hàm tạo `private`, `= delete` sao chép/gán, `static T& lay() { static T t; return t; }` (Meyers singleton). Từ C++11 khởi tạo biến `static` cục bộ an toàn luồng ("magic statics"): mình chạy 8 luồng, hàm tạo chạy 1 lần; cách tự viết kiểm-rồi-tạo ra 8 lần. Chỉ khởi tạo được bảo vệ, dùng đối tượng vẫn cần mutex.
3. **Vì sao bị chê** (mình đã chạy): phụ thuộc ngầm và khó test (kiểm 2 ra 110 thay vì 100), thứ tự hủy ngược thứ tự tạo xong (hàm hủy dùng Singleton đã hủy: ASan báo `double-free`). Thay bằng truyền phụ thuộc vào qua tham chiếu hoặc `unique_ptr`.
4. **Factory**: `taoHinh` trả `std::unique_ptr<Hinh>`, tức chuyển sở hữu cho người gọi (quên xóa không xảy ra); registry `map<string, function<unique_ptr<Hinh>()>>` thêm loại mới không sửa factory (cần kiểm `find` trả `end()`); Factory Method để lớp con quyết định tạo gì; Abstract Factory tạo cả họ; Builder cho đối tượng nhiều tham số tùy chọn.
5. Go: `sync.Once` (`once.Do` chạy một lần, mọi lời gọi chờ `f` xong), biến cấp gói và `init()` chạy trước `main`, `NewX` trả interface (quy ước, không có `unique_ptr`), functional options thay Builder; Go không có `= delete`, không có hàm hủy.
