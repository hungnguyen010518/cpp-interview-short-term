# Bài 73 — Thực chiến: event bus (pub/sub) an toàn luồng với weak_ptr

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết `EventBus` (đăng ký, hủy đăng ký, phát) chạy đúng với nhiều luồng: **chép danh sách người nghe ra ngoài khóa rồi mới gọi callback**, và nói được vì sao hai bản sai (giữ khóa khi gọi, nhả khóa rồi duyệt thẳng) hỏng ra sao (chạy thật: treo mã 124, mã 139, TSan `data race`).
    - Làm bus **không giữ người nghe sống** bằng `weak_ptr` + `lock()` + dọn mục hết hạn ngay trong lượt phát; chỉ ra hàm hủy người nghe chạy ở luồng nào (chạy thật: ở luồng phát), và vì sao bus giữ con trỏ thô (ASan `heap-use-after-free`) hay `shared_ptr` (người nghe không chết) đều sai.
    - Trả lời nối tiếp: `recursive_mutex` có cứu được không, `huyDangKy` trả về rồi mà callback vẫn bị gọi (**thông báo muộn**, chạy thật), callback ném ngoại lệ, phát cho hàng chục nghìn người nghe (chép-khi-ghi, đo ra cỡ 2,5 lần).
    - Phân biệt chuẩn bảo đảm gì với g++ 11 trên máy này cho kết quả gì, và biết khi nào **không** nên dùng event bus.

**Bạn cần biết trước:** [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (Observer: giao diện `Quansat`, danh sách `weak_ptr`, duyệt bản sao), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, `weak_ptr`, `lock()`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, TSan), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, callback khi giữ khóa), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (`erase` làm iterator hỏng), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function`, remove-erase), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`promise`/`future`, dùng làm "chuông" cho test), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (ASan, UB). [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md) (ai sở hữu?), [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) (`weak_ptr::lock()`, callback bất đồng bộ, hàm hủy chạy ở luồng nhả thẻ cuối) và [Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md) (không gọi callback khi giữ khóa) đã dạy các mảnh ghép; bài này **áp dụng** chúng vào một đề phỏng vấn, không dạy lại.

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đẩy bút qua bàn: "Viết cho tôi một `EventBus`. Ai quan tâm một loại tin thì đăng ký một hàm, ai có tin thì phát, bus gọi hàm của từng người đã đăng ký. Chương trình nhiều luồng, và người nghe có thể biến mất bất cứ lúc nào. Anh nói to cách nghĩ nhé."

Trong **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), bus là **bảng thông báo** bên cửa kho. Đầu bếp ghi tên vào tờ "ai muốn nghe tin hết hành" (đăng ký). Ai có tin thì dán lên bảng rồi **đi gọi từng người** trong tờ (phát). Tờ danh sách là một thứ dùng chung nên cần **thẻ vào thớt** (mutex) khi sửa hay chép nó.

!!! info "Chỗ nào ví von không còn đúng?"
    Người dán tin ngoài đời chỉ báo, còn người nghe tự xử lý. Trong C++, bus **chạy luôn hàm của người nghe ngay trong luồng của người phát**, nên hàm đó có thể làm mọi thứ, kể cả gọi ngược lại bảng thông báo. Toàn bộ độ khó của đề nằm ở chỗ này.

## 📖 Giải thích

### 1. Đề 1: `EventBus` an toàn luồng

!!! example "Đề 1"
    Viết `EventBus` cho tin kiểu chuỗi, `Handler` là `std::function<void(const std::string&)>`. Ba hàm: `int dangKy(Handler)` (trả mã số), `void huyDangKy(int ma)`, `void phat(const std::string& tin)`.
    **Ràng buộc:** gọi được từ nhiều luồng cùng lúc; callback được phép gọi `dangKy`/`huyDangKy` trên chính bus (kể cả tự hủy mình) mà không treo, không sập; C++17, chỉ thư viện chuẩn.
    **Vào/ra:** a, b, c đăng ký theo thứ tự, `phat("1")` thì a, b, c nhận theo thứ tự đó (thứ tự đăng ký là lựa chọn của ta, chuẩn không bảo đảm gì). Bốn luồng, mỗi luồng phát 2500 tin cho ba người nghe ổn định: mỗi người nhận **đúng 10000**.

??? tip "Gợi ý 1"
    Danh sách người nghe là dữ liệu chung bị sửa nên cần khóa. Nhưng callback là mã của người khác: nếu nó gọi `huyDangKy` khi bạn đang giữ khóa thì chuyện gì xảy ra?

??? tip "Gợi ý 2"
    Giữ khóa chỉ đủ lâu để **chép danh sách ra một biến cục bộ**; nhả khóa; rồi gọi callback trên bản chép. Mọi `erase`/`push_back` do callback gây ra chỉ đụng danh sách gốc.

??? tip "Gợi ý 3"
    Bản chép nên chứa `shared_ptr<const Handler>` (chép con trỏ thay vì chép cả hộp hàm: rẻ hơn, và không chép trạng thái nằm trong lambda). Rồi tự hỏi và nói to: người đăng ký giữa lượt phát có nhận tin lượt đó không? Người vừa hủy thì sao?

### 2. Hướng giải đề 1: ba cách, chỉ một cách đúng

| Cách | Callback chạy | Callback gọi lại bus | Kết luận |
|---|---|---|---|
| A. Giữ khóa suốt lượt phát | Trong khóa | Khóa lại mutex đang giữ: UB, treo (mục 💻); đổi `recursive_mutex` thì `erase` làm hỏng vòng đang duyệt | Sai |
| B. Nhả khóa rồi duyệt thẳng `ds_` | Ngoài khóa | Callback hoặc luồng khác sửa `ds_` lúc ta đọc: data race | Sai |
| C. Chép trong khóa, gọi trên bản chép | Ngoài khóa | An toàn | **Đúng**, mặc định |

Cách C kéo theo **ngữ nghĩa bản chụp**, và nên nói to với người phỏng vấn:

- Người đăng ký **giữa** lượt phát không nhận tin của lượt đó (nằm ngoài bản chụp), nhận từ lượt sau.
- Người hủy giữa lượt phát **vẫn có thể bị gọi nốt**: đó là **thông báo muộn** (late notification, chạy thật ở mục 💻).
- Callback chạy **trong luồng của người phát**; bốn luồng phát thì cùng một callback chạy **đồng thời**, nên callback phải tự an toàn (bộ đếm dùng `atomic`).

**Chuẩn nói gì, máy này cho gì.** Chuẩn: khóa lại một `std::mutex` mà luồng đang giữ là hành vi không xác định; data race cũng vậy. g++ 11 trên máy này: cái đầu **treo**, cái sau **thường vẫn ra đúng** (3 trong 40 lần chạy chết, mục 💻). "Chạy ra đúng" không chứng minh gì.

### 3. Đề 2: người nghe có đời riêng, chết trước bus

!!! example "Đề 2"
    Người nghe là đối tượng có vòng đời riêng (một màn hình, một phiên làm việc), có thể bị hủy bất cứ lúc nào, không ai nhớ `huyDangKy`. Bus **không được gọi vào đối tượng đã chết**, cũng **không được giữ nó sống mãi**. Luồng khác vẫn đăng ký và phát trong lúc đó.
    **Vào/ra:** phòng, bếp, kho đăng ký; bếp bị hủy; `phat("A")` thì chỉ phòng và kho nhận, và sau lượt phát bus chỉ còn **2 mục**. Bốn luồng phát 2000 lần, luồng thứ năm đăng ký 2000 người nghe rồi buông ngay: ba người nghe ổn định nhận đúng **8001** tin (tính cả một lượt phát cuối), 2000 hàm hủy chạy, còn **3 mục**.

??? tip "Gợi ý 1"
    [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md) hỏi "ai sở hữu?". Người nghe thuộc về ai: bus hay chủ của nó? Vậy bus chỉ nên **nhìn** hay nên **giữ**?

??? tip "Gợi ý 2"
    Lưu `weak_ptr<NguoiNghe>`. Mỗi lượt phát gọi `lock()` từng mục ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md): một bước nguyên tử): ra thẻ thì gọi, rỗng thì bỏ qua **và xóa mục đó**.

??? tip "Gợi ý 3"
    Thẻ `lock()` được phải chết **ngoài khóa của bus**. Hàm hủy người nghe chạy ở luồng nhả thẻ cuối, và đó có thể là luồng phát đang đứng trong khóa. Hãy khai báo vector các thẻ ở ngoài khối khóa.

### 4. Hướng giải đề 2: bus lưu cái gì

| Bus lưu | Người nghe chết trước | Chủ muốn nó chết | Kết luận |
|---|---|---|---|
| Con trỏ thô, hoặc lambda bắt `this` | Bus gọi vào đồ đã trả: use-after-free | Chết được, nhưng bus không biết | Sai |
| `shared_ptr` | Không chết được vì bus giữ sống | Không chết: nhận "tin ma", rò rỉ logic | Sai (trừ khi muốn vậy) |
| `weak_ptr` | `lock()` rỗng: bỏ qua, dọn mục | Chết đúng lúc chủ buông | **Đúng** |

Ba điểm tinh. **(1)** `lock()` xong có **thẻ trong tay**, nên người nghe chắc chắn sống tới khi callback xong (không dùng mẫu `expired()` rồi `lock()`, đã sai ở [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)). **(2)** Vì thẻ trong tay có thể là thẻ cuối, **hàm hủy người nghe chạy ở luồng phát**, ngay sau khi callback xong; mục 💻 cho thấy điều này. **(3)** Dọn mục hết hạn ngay trong lượt phát (ta đang giữ khóa sẵn), không cần luồng dọn riêng.

### 5. Khi nào KHÔNG nên dùng event bus

| Tình huống | Chọn gì | Vì sao |
|---|---|---|
| Chỉ một người nghe, biết trước | Gọi hàm hoặc callback thẳng | Bus chỉ thêm khóa và độ khó gỡ lỗi |
| Cần giá trị trả về hoặc thứ tự chặt | Gọi trực tiếp, hoặc chuỗi xử lý | Bus không có "câu trả lời" và không bảo đảm thứ tự giữa các luồng phát |
| Người nghe chậm không được kéo người phát chậm | Đẩy tin vào hàng đợi ([Bài 66](66-bounded-queue.md)), luồng riêng xử lý | Phát đồng bộ chạy callback ngay trong luồng người phát |
| Dòng dữ liệu liên tục, cần chặn khi đầy | Hàng đợi có giới hạn | Bus không có áp lực ngược (backpressure) |

## 💻 Ví dụ code

### Lời giải đề 1: chép ra ngoài khóa rồi gọi

Ba phần trong `main`: phần 1 (một luồng, đầu ra tất định) cho thấy ngữ nghĩa bản chụp; phần 2 là bốn luồng phát và một luồng đăng ký/hủy liên tục; phần 3 chứng minh thông báo muộn bằng hai `promise`/`future` làm "chuông" ([Bài 29](../nhom-3-da-luong/29-async-future.md)). `mutable` ở `khoa_` cho phép khóa mutex ngay trong hàm `const`.

```cpp
#include <atomic>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

class EventBus {
public:
    using Handler = std::function<void(const std::string&)>;

    int dangKy(Handler h) {
        std::lock_guard<std::mutex> giu(khoa_);                       // (1) sửa danh sách: phải khóa
        ds_.push_back(Muc{++maMoi_, std::make_shared<const Handler>(std::move(h))});
        return maMoi_;
    }
    void huyDangKy(int ma) {
        std::shared_ptr<const Handler> bo;                            // (1b) hàm bị gỡ sẽ chết ở đây, SAU khi nhả khóa
        std::lock_guard<std::mutex> giu(khoa_);
        for (auto it = ds_.begin(); it != ds_.end(); ++it)
            if (it->ma == ma) { bo = it->ham; ds_.erase(it); break; }
    }
    void phat(const std::string& tin) {
        std::vector<Muc> banChup;                                     // (2) bản chụp, sống ngoài khóa
        {
            std::lock_guard<std::mutex> giu(khoa_);
            banChup = ds_;                                            // (3) chép TRONG khóa
        }                                                             // (4) nhả khóa
        for (const Muc& m : banChup) (*m.ham)(tin);                   // (5) gọi callback NGOÀI khóa
    }
    std::size_t soNguoiNghe() const {
        std::lock_guard<std::mutex> giu(khoa_);
        return ds_.size();
    }

private:
    struct Muc { int ma; std::shared_ptr<const Handler> ham; };
    mutable std::mutex khoa_;
    std::vector<Muc> ds_;
    int maMoi_ = 0;
};

int main() {
    // Phần 1: ngữ nghĩa của bản chụp, chạy một luồng nên đầu ra tất định.
    EventBus bus;
    int maB = 0;
    bool daThemD = false;
    bus.dangKy([](const std::string& t) { std::cout << "a nhan " << t << "\n"; });
    maB = bus.dangKy([&](const std::string& t) {
        std::cout << "b nhan " << t << " roi tu huy\n";
        bus.huyDangKy(maB);                                           // (6) tự hủy ngay trong callback
    });
    bus.dangKy([&](const std::string& t) {
        std::cout << "c nhan " << t << "\n";
        if (!daThemD) {
            daThemD = true;
            bus.dangKy([](const std::string& u) { std::cout << "d nhan " << u << "\n"; });   // (7)
        }
    });
    std::cout << "--- phat 1 ---\n";
    bus.phat("1");
    std::cout << "so nguoi nghe: " << bus.soNguoiNghe() << "\n";
    std::cout << "--- phat 2 ---\n";
    bus.phat("2");

    // Phần 2: bốn luồng phát, một luồng đăng ký/hủy liên tục.
    EventBus bus2;
    std::atomic<int> dem[3] = {{0}, {0}, {0}};                        // ba bộ đếm nguyên tử
    for (int k = 0; k < 3; ++k)
        bus2.dangKy([&dem, k](const std::string&) { ++dem[k]; });     // (8) ba người nghe ổn định
    std::vector<std::thread> luong;
    for (int p = 0; p < 4; ++p)
        luong.emplace_back([&bus2] {
            for (int i = 0; i < 2500; ++i) bus2.phat("x");
        });
    luong.emplace_back([&bus2] {                                      // (9) luồng "chạy ra chạy vào"
        for (int i = 0; i < 2000; ++i) {
            int ma = bus2.dangKy([](const std::string&) {});
            bus2.huyDangKy(ma);
        }
    });
    for (std::thread& t : luong) t.join();
    std::cout << "on dinh: " << dem[0] << " " << dem[1] << " " << dem[2] << "\n";
    std::cout << "con lai: " << bus2.soNguoiNghe() << "\n";

    // Phần 3: huyDangKy trả về rồi, người nghe đó vẫn có thể bị gọi nốt (thông báo muộn).
    EventBus bus3;
    std::promise<void> aDangChay, choA;
    std::future<void> choAF = choA.get_future();
    bus3.dangKy([&](const std::string&) {                             // (10) A: đứng giữa chừng
        aDangChay.set_value();
        choAF.wait();
    });
    int maB3 = bus3.dangKy([](const std::string& t) { std::cout << "b3 van nhan " << t << "\n"; });
    std::thread phatThu([&bus3] { bus3.phat("Z"); });
    aDangChay.get_future().wait();                                    // bản chụp đã có cả A và B
    bus3.huyDangKy(maB3);                                             // (11) main hủy B
    std::cout << "main: huyDangKy(B) da tra ve\n";
    choA.set_value();
    phatThu.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Danh sách gốc `ds_` / bản chụp |
|---|---|---|
| (1) | `push_back` sửa vector nên phải khóa | `ds_`: [a, b, c] |
| (1b) | `huyDangKy` giữ thêm một thẻ của hàm bị gỡ trong `bo`, khai báo **trước** `giu` nên chết **sau** khi `giu` nhả khóa (hàm hủy của thứ lambda bắt cũng là mã của người khác) | `bo` giữ hàm vừa gỡ |
| (3)(4) | Chép rồi nhả khóa: chỉ hai lệnh này cần khóa | `banChup` = [a, b, c] |
| (5)(6) | `(*m.ham)(tin)`: `*m.ham` lấy hàm ra khỏi `shared_ptr`, `(tin)` gọi nó. Callback chạy ngoài khóa nên b gọi được `huyDangKy` (xin khóa lại được) | `ds_`: [a, c]; `banChup` vẫn [a, b, c], vòng chạy tiếp |
| (7) | c đăng ký d giữa lượt "1": d không có trong bản chụp, nhận từ lượt "2" | `ds_`: [a, c, d] |
| (8)(9) | Phần 2: bốn luồng phát và một luồng đăng ký/hủy xếp hàng qua cùng một khóa | `ds_` luôn có 3 người ổn định |
| (10)(11) | Phần 3: bản chụp đã chứa B; main hủy B trong lúc A đứng giữa chừng; sau khi A chạy tiếp, luồng phát vẫn gọi B | `ds_`: [A]; `banChup`: [A, B] |

**Kết quả khi chạy** (40 lần liền đều y hệt; TSan sạch, ASan và UBSan sạch):

```text
--- phat 1 ---
a nhan 1
b nhan 1 roi tu huy
c nhan 1
so nguoi nghe: 3
--- phat 2 ---
a nhan 2
c nhan 2
d nhan 2
on dinh: 10000 10000 10000
con lai: 3
main: huyDangKy(B) da tra ve
b3 van nhan Z
```

Hai dòng cuối là bằng chứng thông báo muộn: `huyDangKy` đã trả về mà B vẫn nhận tin. Muốn B an toàn trước chuyện đó thì B phải **tự chịu được** (kiểm một cờ `atomic` riêng, hoặc dùng `weak_ptr` như đề 2); bus không thể hứa.

### Bản SAI của đề 1

**Sai A: gọi callback khi đang giữ khóa.** Chỉ thay thân `phat` (phần còn lại giữ nguyên), rồi chạy cả `main` ở trên:

```cpp
// bo-qua-kiem-tra
void phat(const std::string& tin) {
    std::lock_guard<std::mutex> giu(khoa_);
    for (const Muc& m : ds_) (*m.ham)(tin);        // callback chạy TRONG khóa
}
```

Mình chạy ba lần với `timeout 3` (lệnh giết chương trình sau 3 giây và thoát mã 124): lần nào cũng mã **124**. Thêm `stdbuf -oL` (ép ghi đầu ra từng dòng, kẻo `timeout` giết làm mất phần chưa ghi) thì thấy nó dừng sau `a nhan 1` và `b nhan 1 roi tu huy`: b gọi `huyDangKy` và xin lại đúng `khoa_` mà luồng này đang giữ. Chuẩn gọi đây là hành vi không xác định; g++ 11 ở đây cho treo. TSan (ba lần) cũng treo mã 124 và **không in cảnh báo nào**. Đổi `std::mutex` thành `std::recursive_mutex` thì hết treo, nhưng `erase` chạy giữa vòng range-for: cả ba lần chết mã **139**; ASan báo `SEGV` trong `std::_Function_base::_M_empty`, UBSan báo `member call on null pointer`, `-D_GLIBCXX_DEBUG` báo `attempt to increment a singular iterator`. Đổi sang `recursive_mutex` chỉ chữa triệu chứng treo, không chữa nguyên nhân.

**Sai B: nhả khóa rồi duyệt thẳng danh sách.**

```cpp
// bo-qua-kiem-tra
void phat(const std::string& tin) {
    { std::lock_guard<std::mutex> giu(khoa_); }    // khóa rồi nhả ngay: chẳng bảo vệ gì
    for (const Muc& m : ds_) (*m.ham)(tin);        // đọc ds_ trong lúc luồng khác push_back/erase
}
```

Mình chạy riêng phần 2 (bỏ phần 1, vì phần 1 tự hủy giữa vòng nên sập trước). **TSan:** 40 lần, cả 40 lần mã 66 với `data race` (một báo cáo là `Write of size 8 ... vector::emplace_back` từ `dangKy`, đọc ở `phat`). **Không sanitizer:** 40 lần, 37 lần in đúng `10000 10000 10000`, 3 lần chết mã **134** (`terminate called after throwing an instance of 'std::bad_function_call'`). **ASan:** 40 lần, 10 lần `heap-use-after-free` (vector cấp phát lại bộ nhớ khi đang bị duyệt). Đa số lần "ra đúng", nên dễ qua mặt người tự test vài lần.

### Lời giải đề 2: `weak_ptr`, `lock()`, dọn mục hết hạn

Bus lưu `weak_ptr<NguoiNghe>`; vẫn có mã số để hủy chủ động. Ba phần trong `main`: người nghe chết trước bus; người nghe bị buông **giữa lúc callback đang chạy** (in `std::this_thread::get_id()` để thấy hàm hủy chạy ở luồng nào, như [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)); và nhiều luồng với người nghe vào ra liên tục.

```cpp
#include <algorithm>
#include <atomic>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

struct NguoiNghe {                                    // giao diện như Bài 36
    virtual ~NguoiNghe() = default;
    virtual void nhan(const std::string& tin) = 0;
};

class BusWeak {
public:
    int dangKy(const std::shared_ptr<NguoiNghe>& n) {
        std::lock_guard<std::mutex> giu(khoa_);
        ds_.push_back(Muc{++maMoi_, n});                              // (1) shared_ptr -> weak_ptr: không giữ sống
        return maMoi_;
    }
    void huyDangKy(int ma) {
        std::lock_guard<std::mutex> giu(khoa_);
        ds_.erase(std::remove_if(ds_.begin(), ds_.end(),
                                 [ma](const Muc& m) { return m.ma == ma; }),
                  ds_.end());
    }
    void phat(const std::string& tin) {
        std::vector<std::shared_ptr<NguoiNghe>> song;                 // (2) thẻ lấy được; khai báo NGOÀI khối khóa
        {
            std::lock_guard<std::mutex> giu(khoa_);
            for (const Muc& m : ds_)
                if (std::shared_ptr<NguoiNghe> sp = m.yeu.lock())     // (3) một bước: ra thẻ hoặc rỗng
                    song.push_back(std::move(sp));
            ds_.erase(std::remove_if(ds_.begin(), ds_.end(),          // (4) dọn mục đã chết, ngay lượt này
                                     [](const Muc& m) { return m.yeu.expired(); }),
                      ds_.end());
        }                                                             // (5) nhả khóa
        for (const std::shared_ptr<NguoiNghe>& sp : song) sp->nhan(tin);   // (6) gọi NGOÀI khóa, có thẻ trong tay
    }                                                                 // (7) song chết ở đây: hàm hủy người nghe (nếu là thẻ cuối) chạy Ở ĐÂY
    std::size_t soDangKy() const {
        std::lock_guard<std::mutex> giu(khoa_);
        return ds_.size();
    }

private:
    struct Muc { int ma; std::weak_ptr<NguoiNghe> yeu; };
    mutable std::mutex khoa_;
    std::vector<Muc> ds_;
    int maMoi_ = 0;
};

struct Man : NguoiNghe {                              // người nghe có tên, in ra khi nhận và khi bị hủy
    explicit Man(std::string t) : ten(std::move(t)) {}
    ~Man() override { std::cout << "  huy " << ten << "\n"; }
    void nhan(const std::string& tin) override { std::cout << "  " << ten << " nhan " << tin << "\n"; }
    std::string ten;
};

std::thread::id luongPhat;                            // luồng đang phát (phần 2)

struct Cham : NguoiNghe {                             // callback chạy chậm: dừng giữa chừng cho test
    Cham(std::promise<void>& vao, std::future<void> cho) : daVao(vao), choRa(std::move(cho)) {}
    ~Cham() override {
        std::cout << "  ~Cham, o luong phat? " << (std::this_thread::get_id() == luongPhat) << "\n";
    }
    void nhan(const std::string&) override {
        daVao.set_value();                            // (8) báo "tôi đang chạy callback"
        choRa.wait();                                 // (9) đứng chờ main cho đi tiếp
        std::cout << "  Cham chay xong callback\n";
    }
    std::promise<void>& daVao;                        // do main giữ, sống lâu hơn Cham
    std::future<void> choRa;
};

struct Dem : NguoiNghe {                              // đếm tin; nếu có soHuy thì đếm cả lần bị hủy
    explicit Dem(std::atomic<int>* h = nullptr) : soHuy(h) {}
    ~Dem() override { if (soHuy) ++*soHuy; }
    void nhan(const std::string&) override { ++n; }
    std::atomic<int> n{0};
    std::atomic<int>* soHuy;
};

int main() {
    std::cout << "Phan 1: nguoi nghe chet truoc bus\n";
    {
        BusWeak bus;
        auto phong = std::make_shared<Man>("phong");
        auto bep = std::make_shared<Man>("bep");
        auto kho = std::make_shared<Man>("kho");
        bus.dangKy(phong);
        bus.dangKy(bep);
        int maKho = bus.dangKy(kho);
        std::cout << "dang ky: " << bus.soDangKy() << ", use_count phong: " << phong.use_count() << "\n";
        bep.reset();                                   // bếp bị hủy mà không ai gọi huyDangKy
        std::cout << "phat lan 1:\n";
        bus.phat("A");
        std::cout << "dang ky sau khi don: " << bus.soDangKy() << "\n";
        bus.huyDangKy(maKho);
        std::cout << "phat lan 2 (kho da huy dang ky):\n";
        bus.phat("B");
    }

    std::cout << "Phan 2: nguoi nghe bi buong khi callback dang chay\n";
    {
        BusWeak bus;
        std::promise<void> daVao, choRa;               // hai "chuông" do main giữ
        auto cham = std::make_shared<Cham>(daVao, choRa.get_future());
        bus.dangKy(cham);
        std::thread phatThu([&bus] {
            luongPhat = std::this_thread::get_id();
            bus.phat("X");
        });
        daVao.get_future().wait();                     // (10) callback đã chạy tới giữa chừng
        cham.reset();                                  // (11) main buông thẻ của mình
        std::cout << "main da buong, ~Cham chua chay\n";
        choRa.set_value();                             // (12) cho callback chạy tiếp
        phatThu.join();
    }

    std::cout << "Phan 3: nhieu luong, nguoi nghe vao ra lien tuc\n";
    {
        BusWeak bus;
        std::shared_ptr<Dem> on[3];
        for (auto& p : on) { p = std::make_shared<Dem>(); bus.dangKy(p); }
        std::atomic<int> soHuy{0};
        std::vector<std::thread> luong;
        for (int p = 0; p < 4; ++p)
            luong.emplace_back([&bus] {
                for (int i = 0; i < 2000; ++i) bus.phat("x");
            });
        luong.emplace_back([&bus, &soHuy] {
            for (int i = 0; i < 2000; ++i)
                bus.dangKy(std::make_shared<Dem>(&soHuy));   // (13) đăng ký rồi buông ngay
        });
        for (std::thread& t : luong) t.join();
        bus.phat("cuoi");                              // một lượt phát nữa để dọn nốt
        std::cout << "on dinh: " << on[0]->n << " " << on[1]->n << " " << on[2]->n << "\n";
        std::cout << "da huy: " << soHuy << ", con dang ky: " << bus.soDangKy() << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai giữ thẻ |
|---|---|---|
| (1) | `dangKy` đổi `shared_ptr` thành `weak_ptr`: `use_count` của phòng vẫn 1 | chủ của từng người nghe |
| (3) | `lock()` trong khóa: bếp đã chết nên rỗng, phòng và kho ra thẻ | `song` = [phòng, kho] |
| (4) | Dọn mục của bếp ngay lượt này: `ds_` còn 2 mục | |
| (6)(7) | Gọi ngoài khóa, rồi `song` chết cuối hàm: người nghe không còn chủ nào khác sẽ bị hủy **tại đây** | |
| (8)-(12) | Phần 2: callback đứng giữa chừng, main buông thẻ; hàm hủy **chưa** chạy vì `song` còn một thẻ; callback xong, `song` chết trong luồng phát, `~Cham` chạy ở đó | luồng phát (thẻ cuối) |
| (13) | Phần 3: mỗi người nghe tạm chết ngay ở luồng đăng ký (hoặc ở luồng phát, nếu một lượt `lock()` chen vào trước); `soHuy` đếm đúng 2000 dù nơi chết là đâu | |

**Kết quả khi chạy** (40 lần liền đều y hệt; TSan sạch, ASan và UBSan sạch):

```text
Phan 1: nguoi nghe chet truoc bus
dang ky: 3, use_count phong: 1
  huy bep
phat lan 1:
  phong nhan A
  kho nhan A
dang ky sau khi don: 2
phat lan 2 (kho da huy dang ky):
  phong nhan B
  huy kho
  huy phong
Phan 2: nguoi nghe bi buong khi callback dang chay
main da buong, ~Cham chua chay
  Cham chay xong callback
  ~Cham, o luong phat? 1
Phan 3: nhieu luong, nguoi nghe vao ra lien tuc
on dinh: 8001 8001 8001
da huy: 2000, con dang ky: 3
```

Chú ý dòng `~Cham, o luong phat? 1`: người nghe bị hủy **ở luồng phát, sau callback**. Hệ quả: hàm hủy của người nghe không được làm việc nguy hiểm (xin khóa mà người phát đang giữ, chờ luồng phát). Hai dòng `huy kho`, `huy phong` ở cuối phần 1 là lúc khối `{}` kết thúc.

**Thử thay đổi: bỏ lệnh dọn (4).** Mình đã chạy: `phat` vẫn đúng (bếp vẫn bị bỏ qua), nhưng `dang ky sau khi don` ra **3** thay vì 2, và cuối phần 3 `con dang ky` ra **2003** thay vì 3: 2000 `weak_ptr` chết nằm lại mãi. Không sai kết quả, nhưng danh sách phình ra và mỗi lượt phát phải duyệt qua xác chết.

### Bản SAI của đề 2

**Sai C: lưu con trỏ thô (hoặc lambda bắt `this`).** Bus chép `std::vector<NguoiNghe*>` trong khóa rồi gọi ngoài khóa (đúng cả khóa lẫn bản chụp), `main` đăng ký `phong.get()` và `bep.get()` từ hai `unique_ptr<Man>`, rồi `bep.reset()` và `bus.phat("A")`.

```cpp
// bo-qua-kiem-tra
void dangKy(NguoiNghe* n) {                        // BusTho: lưu con trỏ THÔ
    std::lock_guard<std::mutex> giu(khoa_);
    ds_.push_back(n);
}
// main: bus.dangKy(phong.get()); bus.dangKy(bep.get()); bep.reset(); bus.phat("A");
```

Mình chạy ba lần không sanitizer: in `huy bep`, `phong nhan A` rồi chết mã **139** (bus đọc con trỏ bảng hàm ảo của đối tượng đã xóa). ASan báo `heap-use-after-free ... READ of size 8` trong `BusTho::phat`. Khóa đúng 100% mà vẫn sai: **khóa bảo vệ danh sách, không bảo vệ tuổi thọ của thứ danh sách trỏ tới**.

**Sai D: lưu `shared_ptr`.** Chỉ đổi `weak_ptr` thành `shared_ptr` trong danh sách. `main` vòng 2000 lần: tạo một `Man`, `dangKy`, rồi chủ buông thẻ ngay. Cuối cùng in `da dang ky: 2000, van con song: 2000`: không ai chết, vì bus **là chủ chung** của cả 2000. ASan và UBSan đều sạch: nó không crash, nó chỉ **rò rỉ về logic** (đối tượng "đã bị buông" vẫn nhận tin ma, bộ nhớ tăng mãi theo số lần đăng ký).

### Chi phí và độ phức tạp

Gọi n là số người nghe. Bảng dưới là nguyên lý; con số đo ở đoạn sau.

| Thao tác | Bản đề 1 (`vector<Muc>`) | Bản đề 2 (`weak_ptr`) |
|---|---|---|
| `dangKy` | O(1) trung bình, trong khóa | O(1) trung bình, trong khóa |
| `huyDangKy` | O(n) quét, trong khóa | O(n) quét, trong khóa |
| `phat`, phần trong khóa | O(n): chép n con trỏ (2n thao tác nguyên tử với `shared_ptr`) | O(n): n lần `lock()` (nguyên tử) và dọn |
| `phat`, phần ngoài khóa | n lần gọi callback (thường là chi phí chính) | n lần gọi callback |
| Bộ nhớ thêm mỗi lượt phát | O(n) | O(n) |

**Chép-khi-ghi cho bus đọc nhiều ghi ít** (tận dụng `HopCauHinh` của [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)): danh sách là `shared_ptr<const vector<Muc>>` dưới mutex; `phat` chỉ chép **một** con trỏ trong khóa (O(1)); `dangKy`/`huyDangKy` tạo vector mới O(n) rồi đổi con trỏ. Mình đo riêng (không đưa vào bài): 1000 người nghe, callback rỗng, một luồng phát 20000 lần, `-O2`: bản chép vector chậm hơn bản chép-khi-ghi **cỡ 2,5 lần** ba lần liền. Số này đổi theo máy và `-O`; callback nặng làm tỉ lệ mờ đi.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Vì sao không được gọi callback khi đang giữ khóa? Dùng `recursive_mutex` được không?"
    Vì bạn không biết callback làm gì: nó có thể gọi lại `huyDangKy`/`dangKy` và xin lại đúng khóa đang giữ (mình chạy: `std::mutex` treo, mã 124), hoặc xin khóa khác mà luồng khác đang giữ rồi chờ khóa của bạn ([Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md): deadlock hai khóa). Làm cách C: chép trong khóa, gọi ngoài khóa.
    **Nối tiếp: "`recursive_mutex` thì sao?"** Hết treo, nhưng `erase` chạy giữa vòng duyệt làm iterator hỏng (mình chạy: mã 139). Nó chữa triệu chứng khóa, không chữa việc sửa danh sách đang duyệt.
    **Nối tiếp: "Một callback ném ngoại lệ thì sao?"** Với `phat` đồng bộ, ngoại lệ bay ra khỏi `phat` về người phát và **những người nghe phía sau không nhận tin** (mình thử với một vòng gọi y hệt: a in, b ném, c không in). Muốn bền hơn thì bắt từng callback và ghi lỗi, rồi quyết định có ném lại hay không. Đó là lựa chọn thiết kế, nói ra là được điểm.

??? question "`huyDangKy` trả về rồi thì chắc chắn callback đó không còn bị gọi nữa chứ?"
    Không. Lượt `phat` đã chụp danh sách trước đó vẫn gọi nó nốt (mình chạy: `main: huyDangKy(B) da tra ve` rồi `b3 van nhan Z`). Muốn bảo đảm tuyệt đối thì `huyDangKy` phải **chờ mọi lượt phát đang chạy xong**, và khi đó callback không được gọi `huyDangKy` (tự chờ chính mình, deadlock). Hai ràng buộc đó mâu thuẫn nhau, nên bus thường chọn "thông báo muộn" và bắt người nghe tự chịu được.
    **Nối tiếp: "Làm sao người nghe tự chịu được?"** Giữ trạng thái "đã đóng" bằng cờ `atomic` trong chính nó và kiểm cờ ở đầu callback, hoặc dùng `weak_ptr` để đối tượng chắc chắn còn sống suốt lúc nó nhận nốt tin.

??? question "Người nghe chết trước bus: vì sao `weak_ptr`, không phải con trỏ thô hay `shared_ptr`?"
    Con trỏ thô: bus gọi vào đồ đã trả, mình chạy ra mã 139 và ASan báo `heap-use-after-free`. `shared_ptr`: bus thành chủ chung nên không ai chết (mình chạy: đăng ký 2000, vẫn sống 2000). `weak_ptr`: bus chỉ nhìn; `lock()` rỗng thì bỏ qua và dọn, có thẻ thì người nghe chắc chắn sống tới khi callback xong.
    **Nối tiếp: "`weak_ptr` có làm danh sách an toàn luồng không?"** Không. Nó chỉ lo **tuổi thọ** của người nghe; danh sách vẫn cần mutex (đã có trong bản đề 2).

??? question "Hàm hủy của người nghe chạy ở luồng nào, và nó có hậu quả gì?"
    Ở luồng nhả thẻ cuối. Nếu chủ buông thẻ trước và callback đã `lock()` được thẻ thì thẻ cuối nằm trong `song` của luồng phát, nên hàm hủy chạy ở luồng phát sau callback (mình chạy: `~Cham, o luong phat? 1`). Hậu quả: hàm hủy không được xin khóa mà luồng phát có thể đang giữ, và không nên làm việc nặng. Vì thế `song` phải chết **ngoài** khóa của bus.

??? question "Hàng chục nghìn người nghe, phát hàng nghìn lần mỗi giây, đăng ký thì hiếm: tối ưu thế nào? Phát bất đồng bộ thì sao?"
    Chép-khi-ghi: danh sách bất biến trong `shared_ptr<const vector>`, `phat` chỉ chép một con trỏ trong khóa (mình đo cỡ 2,5 lần ở 1000 người nghe). Cái giá là `dangKy` phải chép cả vector.
    **Nối tiếp: "Phát bất đồng bộ?"** Phát đẩy tin vào hàng đợi ([Bài 66](66-bounded-queue.md)) và một hoặc vài luồng riêng gọi callback. Người phát không bị callback chậm kéo chậm, nhưng mất tính "xong khi `phat` trả về", cần quyết định hàng đợi đầy thì làm sao, và thứ tự tin chỉ còn bảo đảm trong từng hàng đợi.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Giữ khóa trong lúc gọi callback, rồi 'sửa' bằng recursive_mutex"
    Callback tự hủy đăng ký thì `std::mutex` treo (mình chạy: mã 124), `recursive_mutex` thì sập (mã 139). Cả hai cho thấy cùng một sai: mã của người khác chạy trong vùng găng. Khi nói: nêu luôn "chép ra ngoài khóa".

!!! warning "Lỗi 2: Nhả khóa rồi duyệt thẳng danh sách gốc, tin vào lần chạy ra đúng"
    Mình chạy 40 lần: 37 lần ra đúng, 3 lần chết, TSan báo `data race` cả 40 lần. Người phỏng vấn muốn nghe "chép **trong** khóa", không phải "mình test chạy được".

!!! warning "Lỗi 3: Nghĩ bus giữ bất kỳ thứ gì cũng thế, hoặc nghĩ `weak_ptr` đã thread-safe"
    Con trỏ thô: sập. `shared_ptr`: không ai chết, danh sách phình. `weak_ptr` lo **tuổi thọ**, còn danh sách vẫn phải khóa. Nhớ thêm: `song` phải chết ngoài khóa, vì hàm hủy người nghe chạy ở luồng phát.

!!! warning "Lỗi 4 (khi nói): hứa nhiều hơn những gì bus bảo đảm"
    Đừng nói "hủy đăng ký xong là không nhận nữa" (còn thông báo muộn), "thứ tự nhận giống thứ tự phát" (chỉ đúng trong một luồng phát), hay "callback chạy lần lượt" (bốn luồng phát thì cùng một callback chạy đồng thời, nên bộ đếm của người nghe cần `atomic`).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="73" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. `khoa_` là `std::mutex`. Một callback gọi `bus.huyDangKy(ma)` (hàm này khóa `khoa_`). Chuyện gì xảy ra?

```text
void phat(const std::string& tin) {
    std::lock_guard<std::mutex> giu(khoa_);
    for (const Muc& m : ds_) (*m.ham)(tin);
}
```

- Chạy bình thường, vì `huyDangKy` chỉ bỏ một mục nên không xung đột với vòng duyệt đang chạy
- Luồng đó khóa lại mutex mà nó đang giữ: hành vi không xác định, trên g++ 11 ở đây thì treo
- Ném `std::system_error` mà `phat` bắt được, vì chuẩn bắt buộc báo lỗi khi khóa hai lần
- Chỉ treo khi có luồng thứ hai cũng đang gọi `phat`, còn chạy một luồng thì vẫn ổn

<p class="giai-thich" markdown>Cùng một luồng xin lại `std::mutex` mà nó đang giữ là hành vi không xác định; mình chạy thì treo (mã 124). Việc `huyDangKy` "chỉ bỏ một mục" không liên quan: lỗi nằm ở chỗ xin khóa hai lần, kể cả khi chỉ có một luồng. Chuẩn không bắt buộc ném `system_error` cho `std::mutex`, nên "bắt được" là mong muốn chứ không phải bảo đảm. Một luồng là đủ để treo: không cần luồng thứ hai.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau. Bus dùng cách C (chép trong khóa, gọi ngoài khóa). Khi nhận một tin, c đăng ký thêm d một lần duy nhất. Ai nhận tin "1" và ai nhận tin "2"?

```text
bus.dangKy(a);
bus.dangKy(b);
bus.dangKy(c);       // c gọi bus.dangKy(d) khi nhận tin đầu tiên
bus.phat("1");
bus.phat("2");
```

- Tin "1": a, b, c, d; tin "2": a, b, c, d, vì đăng ký xong là nhận mọi tin
- Tin "1": a, b, c; tin "2": a, b, c, vì d đăng ký trong callback nên không bao giờ được gọi
- Tin "1": a, b, c, d; tin "2": a, b, c, vì d chỉ được gọi ngay trong lượt nó đăng ký
- Tin "1": a, b, c; tin "2": a, b, c, d, vì lượt "1" đã chụp danh sách trước khi d xuất hiện

<p class="giai-thich" markdown>Bản chụp của lượt "1" được lấy **trước** khi gọi callback nên chưa có d; lượt "2" chụp lại và thấy d. Nói d nhận cả hai tin bỏ qua việc bản chụp đã cố định. Nói d không bao giờ được gọi bỏ qua việc lượt sau chụp lại danh sách gốc. Nói d chỉ nhận lượt đang chạy là đảo ngược: lượt đó chính là lượt d **không** nhận.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Một màn hình đăng ký nghe bus. Người dùng đóng màn hình bất cứ lúc nào và không ai nhớ gọi `huyDangKy`; màn hình đã nằm trong `shared_ptr`. Bus nên lưu gì?

- `weak_ptr` tới màn hình, mỗi lượt phát `lock()`: rỗng thì bỏ qua và dọn mục đó
- `shared_ptr`, để màn hình chắc chắn còn sống mỗi khi bus gọi nó
- Con trỏ thô, vì khi màn hình bị hủy thì nó tự gỡ mình khỏi mọi bus đã đăng ký
- `unique_ptr`, vì mỗi màn hình có đúng một chủ duy nhất và đó là bus

<p class="giai-thich" markdown>Màn hình thuộc về chủ của nó, bus chỉ cần nhìn, đúng vai `weak_ptr` cộng `lock()`. `shared_ptr` biến bus thành chủ chung nên màn hình đóng rồi vẫn sống và vẫn nhận tin (mình chạy: đăng ký 2000, vẫn sống 2000). Con trỏ thô không tự gỡ gì khi đối tượng chết (mình chạy: mã 139 và ASan báo `heap-use-after-free`). `unique_ptr` nghĩa là bus **sở hữu** màn hình, ngược với đề bài.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Luồng A gọi `bus.huyDangKy(ma)` cho một người nghe X và hàm trả về. Cùng lúc luồng B đã chụp danh sách (có X) và đang gọi các callback trước X. Điều nào đúng?

- X không thể bị gọi nữa, vì `huyDangKy` đã xóa X khỏi danh sách trong khóa
- X không thể bị gọi nữa, vì khóa của bus chặn lượt phát của B tới khi `huyDangKy` xong
- X vẫn có thể bị gọi nốt trong lượt của B (thông báo muộn), nên X phải tự chịu được
- X vẫn bị gọi nốt, nhưng chỉ khi bus lưu `shared_ptr`; với `weak_ptr` thì không

<p class="giai-thich" markdown>Bản chụp của B đã chứa X nên B vẫn gọi X dù danh sách gốc đã đổi (mình chạy: `huyDangKy` trả về rồi mà `b3 van nhan Z`). Xóa khỏi danh sách gốc không chạm bản chụp. Khóa của bus chỉ giữ lúc chép, B gọi callback ngoài khóa nên không bị chặn. `weak_ptr` cũng không chặn thông báo muộn: nó chỉ bảo đảm X còn sống lúc được gọi, không bảo đảm X còn "đăng ký".</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đoạn sau trong hàm `phat` của bus giữ `weak_ptr`. Lỗi nằm ở đâu?

```text
{
    std::lock_guard<std::mutex> giu(khoa_);
    std::vector<std::shared_ptr<NguoiNghe>> song;
    for (const Muc& m : ds_)
        if (auto sp = m.yeu.lock()) song.push_back(sp);
    for (auto& sp : song) sp->nhan(tin);
}
```

- `lock()` phải gọi ngoài khóa của bus, vì nó đã nguyên tử và không cần khóa bảo vệ thêm
- Callback `nhan` chạy trong khóa, và `song` cũng chết trong khóa nên hàm hủy chạy trong khóa
- `push_back(sp)` sao chép thẻ nên bộ đếm tăng hai lần và người nghe không bao giờ bị hủy được
- Không có lỗi: `lock()` giữ người nghe sống nên mọi thứ trong khối đều an toàn kể cả callback

<p class="giai-thich" markdown>Vòng `sp->nhan(tin)` nằm trong khối khóa nên callback chạy trong khóa (treo nếu nó gọi lại bus), và `song` khai báo trong khối nên thẻ cuối, nếu có, bị hủy trong khóa. `lock()` gọi trong khóa hoàn toàn ổn: nó chỉ làm việc nguyên tử, không chạy mã của người khác. Thẻ `sp` được chép nhưng bản chép hủy ở cuối mỗi vòng nên không rò. Thẻ giữ người nghe sống đúng, nhưng không cứu được chuyện giữ khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Bus có 10 000 người nghe, chừng một lần đăng ký mỗi phút, và hàng nghìn lượt phát mỗi giây từ nhiều luồng. Thiết kế nào hợp lý nhất?

- Giữ khóa suốt lượt phát, để khỏi tốn công chép danh sách rồi gọi từng callback
- Chép cả vector trong khóa mỗi lượt phát, vì chép con trỏ luôn rẻ hơn mọi cách khác
- Danh sách bất biến trong `shared_ptr<const vector>`; đăng ký tạo bản mới, đổi con trỏ
- Bỏ mutex và đánh dấu con trỏ tới danh sách là `volatile` để mọi luồng thấy bản mới ngay

<p class="giai-thich" markdown>Đọc nhiều ghi ít là đúng chỗ của chép-khi-ghi: lượt phát chỉ chép một con trỏ trong khóa, còn đăng ký (hiếm) trả giá chép vector (mình đo: cỡ 2,5 lần nhanh hơn chép vector mỗi lần ở 1000 người nghe, đổi theo máy). Giữ khóa suốt lượt phát bị treo hoặc hỏng khi callback gọi lại bus. Chép 10 000 phần tử mỗi lượt hàng nghìn lần mỗi giây thì không "luôn rẻ nhất". `volatile` không phải đồng bộ nên bỏ mutex vẫn là data race.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Bus giữ `weak_ptr`. Luồng phát đang chạy callback của X (đã `lock()` được thẻ vào `song`). Chủ của X buông thẻ của mình ở luồng khác. Hàm hủy của X chạy khi nào, ở đâu?

- Ngay lúc chủ buông, ở luồng của chủ, dù callback vẫn đang chạy dở
- Không bao giờ chạy, vì bus còn `weak_ptr` trỏ tới X
- Ở lượt phát kế tiếp, khi bus dọn mục đã hết hạn
- Sau khi callback xong, ở luồng phát, lúc `song` bị hủy

<p class="giai-thich" markdown>Hàm hủy chạy khi **thẻ mạnh cuối** bị nhả, và thẻ cuối nằm trong `song` của luồng phát, nên nó chạy ở đó sau khi callback xong (mình chạy: `~Cham, o luong phat? 1`). Nó không chạy ngay khi chủ buông vì còn thẻ trong `song`. `weak_ptr` không giữ đối tượng sống nên không chặn được hàm hủy. Việc bus dọn mục ở lượt sau chỉ xóa `weak_ptr` khỏi danh sách, không phải lúc đối tượng bị hủy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Event bus an toàn luồng = mutex quanh danh sách + chép ra bản chụp trong khóa + gọi callback ngoài khóa.** Giữ khóa khi gọi thì callback gọi lại bus sẽ treo (mình chạy: mã 124; đổi `recursive_mutex` thì sập mã 139); nhả khóa rồi duyệt thẳng danh sách gốc là data race (TSan 40/40, chết 3/40 không sanitizer).
2. **Ngữ nghĩa bản chụp cần nói to:** người đăng ký giữa lượt phát nhận từ lượt sau; người hủy giữa lượt phát vẫn có thể bị gọi nốt (thông báo muộn, mình chạy); callback chạy trong luồng người phát và đồng thời giữa nhiều người phát, nên tự phải an toàn. Chuẩn không bảo đảm thứ tự giữa các luồng phát.
3. **Người nghe có đời riêng thì bus lưu `weak_ptr`:** `lock()` có thẻ thì gọi, rỗng thì bỏ qua và dọn ngay trong lượt phát. Con trỏ thô: use-after-free (mã 139, ASan); `shared_ptr`: không ai chết (mình chạy: 2000 đăng ký, 2000 còn sống). Khóa bảo vệ danh sách, không bảo vệ tuổi thọ.
4. **Thẻ `lock()` được phải chết ngoài khóa của bus:** hàm hủy người nghe chạy ở luồng nhả thẻ cuối, tức thường ở luồng phát sau callback (mình chạy: `~Cham, o luong phat? 1`). Hàm hủy không được xin khóa mà luồng phát đang giữ.
5. **Chi phí và lựa chọn:** `phat` chép O(n) trong khóa; đọc nhiều ghi ít thì chép-khi-ghi (`shared_ptr<const vector>`, mình đo cỡ 2,5 lần ở 1000 người nghe, đổi theo máy). Không nên dùng bus khi chỉ một người nghe, khi cần giá trị trả về/thứ tự chặt, hay khi người nghe chậm không được kéo người phát chậm (dùng hàng đợi, [Bài 66](66-bounded-queue.md)).
