# Bài 68 — Thực chiến: khởi tạo một lần an toàn luồng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải đề "singleton an toàn luồng" trên bảng trắng bằng `static` cục bộ và bằng `std::call_once` + `std::once_flag`, kiểm bằng 8 luồng cùng gọi và đếm **số lần khởi tạo = 1**; biết singleton có tham số thì luồng nào thắng.
    - Giải đề "khởi tạo lười tài nguyên đắt dùng chung": chỉ dựng khi có người cần, đúng một lần, mọi luồng thấy bản dựng xong; hàm dựng ném ngoại lệ thì lần sau **thử lại** (C++), khác `sync.Once` của Go.
    - Chỉ ra bằng chạy thật vì sao ba bản sai là sai (cờ cục bộ: 8 lần tạo; quên kiểm lại trong khóa: 8 lần tạo; kiểm ngoài khóa với cờ/con trỏ thường: TSan báo race), và nói thật bản nào x86 không phá được.
    - Nói được thứ tự hủy `static`, singleton dùng singleton, deadlock giữa hai `static`, singleton "rò rỉ có chủ ý"; so chi phí ba cách bằng số đo thật.

**Bạn cần biết trước:** [Bài 35](../nhom-4-oop-patterns/35-pattern-singleton-factory.md) (Singleton `static` cục bộ, "magic statics", thứ tự hủy: bài này **nâng cấp góc đa luồng**, không dạy lại), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`, TSan qua `setarch -R`, `timeout`), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `reset`). [Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md) đã dạy `std::call_once` + `std::once_flag` và bản double-checked locking đúng bằng `atomic` (`acquire`/`release`); bài này dùng kết quả đó.

## 🧠 Câu chuyện mở đầu

Phòng phỏng vấn. Người phỏng vấn vẽ một cái bếp: "Bếp có **một** cuốn sổ công thức treo tường, tám đầu bếp cùng chạy vào lấy nó lần đầu. Sổ phải được in **đúng một lần**; ai tới sau thì chờ rồi dùng chung. Viết cho tôi." Bạn viết ba dòng với `static` cục bộ, ông gật rồi nói tiếp: "Giờ là **lò nướng** cỡ lớn, làm nóng mất cả phút. Chưa món nào cần thì đừng bật, nhiều người cần cùng lúc thì chỉ bật một lần, bật hỏng thì lần sau bật lại. Lò còn phải ghi nhật ký vào cuốn sổ lúc tắt."

Đó là hai đề của bài. Mỗi đề có **đề bài**, **ba bậc gợi ý** (đóng sẵn: hãy tự nghĩ trước khi mở), lời giải chạy thật, và các bản **sai** hay gặp trên bảng trắng.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Lò thật tắt rồi bật lại được, còn `static` cục bộ và `call_once` chỉ cho **một** lần khởi tạo thành công trong đời chương trình. "Dựng lại khi cấu hình đổi" là bài toán khác (mục 3). Đầu bếp tới sau thì đứng chờ thật, giống luồng bị chặn ở chỗ khởi tạo.

## 📖 Giải thích

### 1. Đề (a): cuốn sổ công thức chung

**Đề bài.** Viết lớp `SoCongThuc` sao cho: (1) bên ngoài không tạo thêm bản nào (hàm tạo `private`, cấm sao chép); (2) mọi luồng lấy được **cùng một** đối tượng và hàm tạo chạy **đúng một lần** dù 8 luồng cùng gọi lần đầu; (3) làm hai bản: hàm tạo không tham số (`lay()`), và hàm tạo cần **tham số lúc chạy** (`lay(ten)`).

Đầu vào: 8 luồng gọi cùng lúc (bản hai: mỗi luồng một tên khác nhau). Đầu ra phải in và kiểm: số lần tạo (phải 1), 8 địa chỉ có trùng nhau không, 8 luồng có thấy cùng một tên không.

??? tip "Gợi ý 1"
    Hỏi lại đề: có tham số không, dựng ở lần gọi đầu hay lúc khác? Việc "một luồng dựng, người tới sau chờ" đã có sẵn trong ngôn ngữ ở dạng nào (xem lại Bài 35)?

??? tip "Gợi ý 2"
    Không tham số: một biến `static` trong hàm. Có tham số: cần một **cờ** nhớ "đã làm chưa" kèm hàm chạy đúng một lần: `std::once_flag` và `std::call_once`. Cờ phải sống **lâu hơn** mỗi lần gọi.

??? tip "Gợi ý 3"
    Cờ và con trỏ giữ đối tượng là thành viên `static` của lớp (`unique_ptr` để tự hủy lúc thoát). Đếm số lần hàm tạo chạy bằng `std::atomic<int>`, cho hàm tạo ngủ 50 ms để các luồng kịp "dồn" vào đúng lúc đang dựng.

**Hướng giải.** Chuẩn bảo đảm hai thứ, ứng với hai cách:

| Cách | Chuẩn bảo đảm | Dùng khi |
|---|---|---|
| `static T x;` trong hàm | Nhiều luồng vào cùng lúc thì **một** luồng chạy hàm tạo, các luồng khác **chờ** tới khi xong (từ C++11). Hàm tạo ném thì biến coi như chưa khởi tạo, lần sau thử lại | Hàm tạo không cần tham số lúc chạy; mặc định |
| `std::call_once(co, f)` | `f` chạy đúng một lần thành công; mọi lần gọi chỉ trả về **sau khi** `f` xong, và những gì `f` ghi được thấy ở mọi luồng trả về. `f` ném thì lần gọi khác chạy lại `f` | Cần tham số lúc chạy, hoặc tự chọn lúc dựng |

Cái bẫy của bản có tham số là về thiết kế, không phải luồng: **luồng tới trước thắng**. Hàm tạo chạy với tham số của luồng đó, tham số của luồng tới sau bị bỏ qua mà không báo (Ví dụ 1, Thử thay đổi). Nếu thứ tự quan trọng, hãy khởi tạo **tường minh** một lần ở `main` trước khi tạo luồng.

### 2. Đề (b): khởi tạo lười tài nguyên đắt, và thứ tự hủy

**Đề bài.** Có `BangNguyenTo` (sàng đến 2 triệu, dựng đắt) dùng chung. Viết `layBang()` sao cho: (1) **lười**: chưa luồng nào gọi thì chưa dựng; (2) dựng **đúng một lần** dù 8 luồng cùng cần; (3) sau đó mọi luồng đọc **không khóa** và luôn thấy bảng dựng xong; (4) lần dựng đầu ném ngoại lệ thì lần gọi sau thử lại; (5) hai singleton `KetNoi` và `Bao` (`KetNoi` ghi nhật ký vào `Bao` cả lúc tạo lẫn lúc hủy) hủy đúng thứ tự.

Đầu vào: 8 luồng, mỗi luồng đếm số nguyên tố ≤ 200000 từ bảng. Đầu ra: số lần dựng (1), tổng 8 kết quả (8 × 17984 = 143872), thứ tự các dòng "tao/huy".

??? tip "Gợi ý 1"
    "Lười" là dựng lúc có người gọi `layBang()` lần đầu. Hai cách của đề (a) đều làm được. Ý "đọc không khóa": sau khi dựng xong, bảng có bị sửa nữa không?

??? tip "Gợi ý 2"
    Bảng xong rồi chỉ **đọc**, nên nhiều luồng đọc không cần khóa; thứ cần là cầu nối ở khoảnh khắc "dựng xong" (thấy trọn vẹn). `call_once` cho cầu đó. Ngoại lệ: thử ném ở lần dựng đầu rồi xem lần sau có chạy lại không.

??? tip "Gợi ý 3"
    `static` cục bộ bị hủy **ngược thứ tự hoàn thành dựng**. Muốn `Bao` chết sau `KetNoi`, `Bao` phải dựng xong **trước**: gọi `Bao::lay()` ngay trong hàm tạo `KetNoi`. Hai singleton gọi nhau vòng tròn thì không có thứ tự nào đúng.

**Hướng giải.** *Lười, một lần, đọc không khóa*: `call_once` với `unique_ptr<const BangNguyenTo>` rỗng cho tới khi cần; không cần mutex thứ hai vì `call_once` là cầu và không ai ghi nữa. *Ngoại lệ*: C++ cho thử lại (Go khác, xem hộp "Bạn biết Go?" ở Ví dụ 4). *Thứ tự hủy*: dựng xong trước thì hủy sau. Cách thứ ba là **không bao giờ hủy** ("rò rỉ có chủ ý": `static T* p = new T;`): hết rắc rối thứ tự, nhưng hàm hủy không chạy (không xả đệm, không đóng file).

### 3. Chọn cách nào, và khi nào KHÔNG dùng

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Hàm tạo không tham số, sống tới hết chương trình | `static` cục bộ | Ngắn nhất; đường nhanh chỉ đọc một byte cờ (Ví dụ 7) |
| Cần tham số lúc chạy, hoặc muốn tự chọn lúc dựng | `call_once` + `once_flag` | Chậm hơn `static` chút ít |
| Đường cực nóng và bạn hiểu `acquire`/`release` | Double-checked locking bằng `atomic` ([Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md)) | Đường nhanh chỉ một lần đọc `acquire` (bài này không đo); dễ viết sai |
| Phải **dựng lại** khi cấu hình đổi | **Không** dùng `static`/`call_once` (chỉ một lần) | Mutex + `shared_ptr` đổi con trỏ ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md), 61) |
| Test cần mỗi bài một bản, hoặc singleton chỉ là biến toàn cục | **Không** dùng singleton | Truyền phụ thuộc vào (Bài 35) |

**Chuẩn nói gì, máy này cho gì.** Đừng chép cột phải như thể chuẩn hứa:

| Điều | Chuẩn bảo đảm | g++ 11.4, x86-64, máy 8 lõi này |
|---|---|---|
| `static`/`call_once` dựng một lần | Có | 1 lần với 8 luồng, TSan sạch |
| Kiểm cờ/con trỏ thường ngoài khóa | Data race: hành vi không xác định | 30000 vòng không thấy sai, nhưng TSan báo race |
| Bật cờ "xong" trước khi dựng xong | Là lỗi thứ tự, không hứa gì | Sai thật: 7 trong 8 luồng thấy dữ liệu dở |
| Thứ tự hủy `static` | Ngược thứ tự hoàn thành dựng | Đúng như chuẩn |
| Hàm dựng ném ngoại lệ | Lần gọi sau thử lại | Thử lại; riêng `call_once` + TSan thì treo |
| Hai singleton gọi nhau | Đệ quy vào cùng biến: không xác định | Hai luồng: treo (124); một luồng: `terminate` |
| Thời gian mỗi cách | Không nói gì | Có đo, đổi theo máy và `-O` |

Giới hạn đã học ở Bài 35 vẫn đúng: chỉ **việc khởi tạo** được bảo vệ; dùng đối tượng sau đó vẫn cần khóa của bạn.

## 💻 Ví dụ code

### Ví dụ 1 (lời giải đề a): `static` cục bộ và `call_once`, tám luồng kiểm

`SoGhi` dùng Meyers singleton, `SoCongThuc` dùng `call_once` vì hàm tạo cần tên. Mỗi lớp đếm số lần hàm tạo chạy; tám luồng gọi cả hai, rồi `main` kiểm.

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

std::atomic<int> soLanTao1{0}, soLanTao2{0};
void ngu50ms() { std::this_thread::sleep_for(std::chrono::milliseconds(50)); }

class SoGhi {                                                   // cach 1: Meyers singleton
public:
    static SoGhi& lay() { static SoGhi so; return so; }         // (1)
    SoGhi(const SoGhi&) = delete;
    SoGhi& operator=(const SoGhi&) = delete;
private:
    SoGhi() { ++soLanTao1; ngu50ms(); }
};

class SoCongThuc {                                              // cach 2: call_once, ham tao can ten
public:
    static SoCongThuc& lay(const std::string& ten) {            // (2)
        std::call_once(co_, [&ten] { the_.reset(new SoCongThuc(ten)); });   // (3)
        return *the_;                                           // (4)
    }
    const std::string& ten() const { return ten_; }
    SoCongThuc(const SoCongThuc&) = delete;
    SoCongThuc& operator=(const SoCongThuc&) = delete;
private:
    explicit SoCongThuc(const std::string& ten) : ten_(ten) { ++soLanTao2; ngu50ms(); }
    static std::once_flag co_;                                  // (5)
    static std::unique_ptr<SoCongThuc> the_;
    std::string ten_;
};
std::once_flag SoCongThuc::co_;
std::unique_ptr<SoCongThuc> SoCongThuc::the_;

int main() {
    const void* dc1[8];
    const void* dc2[8];
    std::string ten2[8];
    std::vector<std::thread> cacLuong;
    for (int i = 0; i < 8; ++i) {
        cacLuong.emplace_back([i, &dc1, &dc2, &ten2] {          // (6)
            dc1[i] = &SoGhi::lay();
            SoCongThuc& s = SoCongThuc::lay("so-" + std::to_string(i));
            dc2[i] = &s;
            ten2[i] = s.ten();
        });
    }
    for (auto& t : cacLuong) t.join();                          // (7)
    bool g1 = true, g2 = true, gTen = true;
    for (int i = 1; i < 8; ++i) {
        g1 = g1 && dc1[i] == dc1[0];
        g2 = g2 && dc2[i] == dc2[0];
        gTen = gTen && ten2[i] == ten2[0];
    }
    std::cout << "Meyers:    so lan tao = " << soLanTao1 << ", cung mot doi tuong = " << g1 << "\n";
    std::cout << "call_once: so lan tao = " << soLanTao2 << ", cung mot doi tuong = " << g2
              << ", tham so cac luong thay giong nhau = " << gTen << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (6) | Tám luồng chạy, mỗi luồng gọi `SoGhi::lay()` (1) rồi `SoCongThuc::lay("so-i")` (2), ghi địa chỉ và tên vào ô riêng của mình | các mảng kết quả, mỗi luồng một ô |
| (1) | Luồng tới đầu chạy hàm tạo `SoGhi`; luồng tới sau **chờ**, không chạy hàm tạo lần hai | một `so` trong vùng static |
| (3) | Luồng tới đầu chạy lambda: tạo `SoCongThuc` bằng **tên của nó**; luồng khác chờ trong `call_once` | `the_` trỏ tới một đối tượng |
| (4), (5) | Mọi luồng trả về từ `call_once` rồi đọc `*the_`: chuẩn bảo đảm họ thấy đối tượng dựng xong. Cờ `co_` và `the_` là thành viên `static` nên sống cả chương trình | `the_` chỉ đọc từ giờ |
| (7) | Sau `join`, `main` mới so địa chỉ các luồng ghi: hợp lệ vì `join` là cầu | |

**Kết quả khi chạy** (bốn lần liền như nhau; TSan sạch ở `-O0` và `-O2`; ASan + UBSan sạch):

```text
Meyers:    so lan tao = 1, cung mot doi tuong = 1
call_once: so lan tao = 1, cung mot doi tuong = 1, tham so cac luong thay giong nhau = 1
```

**Thử thay đổi (đã chạy):** thêm vào cuối `main` dòng in `SoCongThuc::lay("khac").ten()`. Ba lần chạy in `so-0`, `so-2`, `so-2`: tên **do luồng tới trước quyết định**, đổi theo lần chạy, còn `"khac"` bị bỏ qua mà không báo.

### Ví dụ 2 (bản sai đề a): ba cách viết hay gặp trên bảng

Ba hàm cùng định "lấy sổ, tạo đúng một lần", mỗi hàm sai một kiểu; `main` nhận đối số 1, 2 hoặc 3 (qua `argv`, các chữ gõ sau tên chương trình, [Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md)) để chọn bản. Khối này `// bo-qua-kiem-tra` vì có data race.

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

std::atomic<int> dem[3];                        // dem[k]: so lan ham tao cua ban sai k+1 chay
struct SoGhi {
    explicit SoGhi(int k) { ++dem[k]; std::this_thread::sleep_for(std::chrono::milliseconds(50)); }
};
std::mutex khoa;

SoGhi& laySai1() {                              // Sai 1: once_flag la bien cuc bo
    std::once_flag co;                          // (1) moi lan goi mot co moi
    static SoGhi* p = nullptr;
    std::call_once(co, [] { p = new SoGhi(0); });
    return *p;
}
SoGhi& laySai2() {                              // Sai 2: xin khoa roi tao, khong kiem lai
    static SoGhi* p = nullptr;
    if (p == nullptr) {                         // (2) kiem ngoai khoa
        std::lock_guard<std::mutex> giu(khoa);
        p = new SoGhi(1);                       // (3) khong kiem lai trong khoa
    }
    return *p;
}
SoGhi& laySai3() {                              // Sai 3: double-checked locking, con tro thuong
    static SoGhi* p = nullptr;
    if (p == nullptr) {                         // (4) doc ngoai khoa
        std::lock_guard<std::mutex> giu(khoa);
        if (p == nullptr) p = new SoGhi(2);     // (5) ghi trong khoa
    }
    return *p;
}

int main(int argc, char** argv) {
    int ban = argc > 1 ? std::atoi(argv[1]) : 1;    // chon ban sai 1, 2 hoac 3
    std::vector<std::thread> cacLuong;
    for (int i = 0; i < 8; ++i)
        cacLuong.emplace_back([ban] { if (ban == 1) laySai1(); else if (ban == 2) laySai2(); else laySai3(); });
    for (auto& t : cacLuong) t.join();
    std::cout << "ban sai " << ban << ": so lan tao = " << dem[ban - 1] << "\n";
    return 0;
}
```

Mình biên dịch (sạch cảnh báo) và chạy từng bản, ba lần liền như nhau:

```text
ban sai 1: so lan tao = 8
ban sai 2: so lan tao = 8
ban sai 3: so lan tao = 1
```

- **Sai 1**: `once_flag` cục bộ (1): mỗi lần gọi một cờ mới nên `call_once` chưa từng "nhớ" gì: 8 lần tạo, 7 đối tượng rò, `p` bị 8 luồng ghi đồng thời. TSan (`-O0` và `-O2`): `data race`, mã thoát 66 (mã TSan dùng khi báo lỗi), hai `Write of size 8` trên `laySai1()::p`.
- **Sai 2**: có khóa nhưng **quên kiểm lại** (3): 8 lần tạo. TSan báo `data race` giữa `Read` ở (2) (ngoài khóa) và `Write` ở (3) (`mutexes: write M11`), mã 66.
- **Sai 3**: double-checked locking kinh điển, con trỏ thường. Trên máy này nó **in đúng `1`** cả ba lần: mình **không phá được** nó bằng chạy thường. Nhưng TSan báo `data race` ở `-O0` lẫn `-O2` (mã 66): `Read` ở (4) với `Write` ở (5). Theo chuẩn đó là hành vi không xác định dù máy này chưa phạt. Bản đúng là con trỏ `atomic` với `release`/`acquire` ([Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md)), hoặc `static`/`call_once`.

### Ví dụ 3 (lời giải đề b): bảng đắt dựng lười bằng `call_once`

`layBang()` dựng bảng ở lần gọi đầu, sau đó chỉ đọc. `main` in trạng thái **trước** khi gọi (kiểm "lười"), tám luồng cùng cần bảng, rồi in số lần dựng và tổng.

```cpp
#include <atomic>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

std::atomic<int> soLanDung{0};

class BangNguyenTo {                            // tai nguyen dat: sang Eratosthenes den 2 trieu
public:
    explicit BangNguyenTo(int gioiHan) : la_(gioiHan + 1, true) {
        ++soLanDung;
        la_[0] = la_[1] = false;
        for (long long i = 2; i * i <= gioiHan; ++i)
            if (la_[i])
                for (long long j = i * i; j <= gioiHan; j += i) la_[j] = false;
    }
    int dem(int den) const {                    // so nguyen to <= den
        int d = 0;
        for (int i = 0; i <= den; ++i) d += la_[i] ? 1 : 0;
        return d;
    }
private:
    std::vector<bool> la_;
};

std::once_flag co;
std::unique_ptr<const BangNguyenTo> bang;       // (1) chua ai can thi con rong

const BangNguyenTo& layBang() {
    std::call_once(co, [] { bang.reset(new BangNguyenTo(2000000)); });   // (2)
    return *bang;                               // (3)
}

int main() {
    std::cout << "truoc khi goi: da dung bang = " << (bang != nullptr) << "\n";   // (4)
    std::atomic<long long> tong{0};
    std::vector<std::thread> cacLuong;
    for (int i = 0; i < 8; ++i)
        cacLuong.emplace_back([&tong] { tong += layBang().dem(200000); });      // (5)
    for (auto& t : cacLuong) t.join();
    std::cout << "so lan dung = " << soLanDung << ", tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (4) | `bang` rỗng và `main` in `da dung bang = 0`: chưa ai cần thì chưa tốn gì | `bang` = null |
| (5), (2) | Tám luồng cùng gọi `layBang()`; một luồng chạy lambda dựng sàng, các luồng khác chờ trong `call_once` | `bang` → bảng 2 triệu ô đang điền |
| (3) | Luồng nào trả về từ `call_once` cũng thấy bảng đủ; từ giờ mọi luồng chỉ **đọc** `la_`: không khóa, không race | `bang` → bảng xong, bất biến |

**Kết quả khi chạy** (ba lần liền như nhau; TSan sạch ở `-O2`; ASan + UBSan sạch):

```text
truoc khi goi: da dung bang = 0
so lan dung = 1, tong = 143872
```

`143872 = 8 × 17984` (17984 là số các số nguyên tố không vượt 200000). Chuẩn bảo đảm "dựng một lần" và "thấy bảng đầy đủ" trên mọi máy; luồng nào dựng và dựng mất bao lâu thì không ai hứa.

**Thử thay đổi (đã chạy):** thay dòng (2) bằng `if (!bang) bang.reset(new BangNguyenTo(2000000));` (kiểm rồi dựng, không đồng bộ). Mình chạy 20 lần ở `-O2`: 13 lần chết `Segmentation fault` (mã 139), 7 lần chạy xong nhưng `so lan dung` là 5 hay 6 thay vì 1; ở `-O0`, 10 trên 10 lần chết. Lý do: `bang` chỉ được gán **sau khi** dựng xong, nên trong lúc một luồng đang dựng (mất cỡ chục mili-giây), các luồng khác cũng thấy `bang` rỗng và tự dựng thêm bảng của mình. Mỗi lần `reset` lại xóa bảng của lần trước, trong khi luồng khác còn đang đọc nó: ASan báo `heap-use-after-free`. TSan báo nhiều `data race` trên `bang` và trên `vector<bool>` bên trong.

### Ví dụ 4: hàm dựng ném ngoại lệ thì thử lại

Hàm tạo ném ở lần chạy đầu tiên (đếm bằng `soLanThu`). Mỗi luồng gọi `lay()` và nếu gặp ngoại lệ thì thử lại (3). Cần đúng: hàm tạo chạy **2 lần**, đúng **một** luồng thấy ngoại lệ.

```cpp
#include <atomic>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

std::atomic<int> soLanThu{0};                   // so lan ham tao bat dau chay

struct NangLuong {
    NangLuong() { if (++soLanThu == 1) throw std::runtime_error("doc that bai"); }   // (1)
    int v = 5;
};
NangLuong& lay() { static NangLuong n; return n; }   // (2)

int main() {
    std::atomic<int> soLoi{0}, tong{0};
    std::vector<std::thread> cacLuong;
    for (int i = 0; i < 8; ++i) {
        cacLuong.emplace_back([&soLoi, &tong] {
            for (;;) {                          // (3) gap loi thi thu lai
                try { tong += lay().v; return; }
                catch (const std::exception&) { ++soLoi; }
            }
        });
    }
    for (auto& t : cacLuong) t.join();
    std::cout << "so lan thu = " << soLanThu << ", so luong gap loi = " << soLoi << ", tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2), (1) | Một luồng vào khởi tạo, các luồng khác chờ; lần chạy hàm tạo thứ nhất ném: ngoại lệ bay ra khỏi `lay()` ở **luồng đang dựng**, biến vẫn "chưa khởi tạo" | `n` chưa hợp lệ |
| (3) | Luồng đó bắt, đếm `soLoi`, thử lại; một luồng chạy hàm tạo lần hai, lần này xong. Các luồng khác lấy `n` ra, cộng 5 | `n` hợp lệ, `tong` = 8 × 5 |

**Kết quả khi chạy** (năm lần liền như nhau; TSan sạch ở `-O2`; cũng biên dịch được với `-std=c++20`):

```text
so lan thu = 2, so luong gap loi = 1, tong = 40
```

**Thử thay đổi (đã chạy):** thay `static NangLuong n;` bằng `std::call_once`. Chạy thường cho **cùng** kết quả. Nhưng dưới ThreadSanitizer của g++ 11.4 trên máy này chương trình **treo** (`timeout` giết, mã 124), kể cả chương trình một luồng chỉ gọi `call_once` hai lần nối tiếp với lần đầu ném (mình thử riêng). Mình **chưa xác minh nguyên nhân**; `libtsan` có bản bọc `pthread_once` riêng (xem bằng `nm -D`, lệnh liệt kê tên hàm mà một thư viện chia sẻ cung cấp) nên ngoại lệ đi qua nó là nghi can chính. Đó là hạn chế công cụ ở máy này, không phải của chuẩn; vì vậy bài chứng minh "thử lại" bằng `static`.

!!! info "Bạn biết Go?"
    Go có `sync.Once` và (từ Go 1.21) `sync.OnceValue`. Khác biệt ở ngoại lệ: nếu hàm truyền vào `once.Do` **panic**, Go coi như `Do` đã chạy xong nên lần sau **không chạy lại**. Mình chạy (Go 1.27.2): lần gọi đầu panic, lần sau in "xong", hàm chỉ chạy **1** lần. C++ ngược lại: ném thì thử lại. `sync.OnceValue` với 8 goroutine: tính 1 lần, cả 8 nhận 42, `-race` sạch.

### Ví dụ 5: singleton dùng singleton, thứ tự hủy, singleton "rò rỉ có chủ ý"

`KetNoi` ghi vào `Bao` cả trong hàm tạo (2) và hàm hủy (1). Vì hàm tạo `KetNoi` gọi `Bao::lay()` **trước khi** xong, `Bao` hoàn thành sớm hơn nên chết muộn hơn. `MayIn` dùng `new` nên không bao giờ bị hủy (3).

```cpp
#include <iostream>
#include <string>

class Bao {                                     // so nhat ky
public:
    static Bao& lay() { static Bao b; return b; }
    void ghi(const std::string& dong) { std::cout << "  Bao ghi: " << dong << "\n"; }
    ~Bao() { std::cout << "huy Bao\n"; }
private:
    Bao() { std::cout << "tao Bao\n"; }
};

class KetNoi {                                  // dung Bao trong ham tao VA ham huy
public:
    static KetNoi& lay() { static KetNoi k; return k; }
    ~KetNoi() { std::cout << "huy KetNoi\n"; Bao::lay().ghi("dong ket noi"); }   // (1)
private:
    KetNoi() { std::cout << "tao KetNoi\n"; Bao::lay().ghi("dang tao ket noi"); }   // (2)
};

class MayIn {                                   // "ro ri co y": khong bao gio bi huy
public:
    static MayIn& lay() { static MayIn* m = new MayIn; return *m; }   // (3)
    ~MayIn() { std::cout << "huy MayIn\n"; }
private:
    MayIn() { std::cout << "tao MayIn\n"; }
};

int main() {
    KetNoi::lay();
    MayIn::lay();
    std::cout << "het main\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | `KetNoi::lay()` bắt đầu dựng (in `tao KetNoi`), gọi `Bao::lay()`: `Bao` dựng và **xong** trước | thứ tự hoàn thành: `Bao`, rồi `KetNoi` |
| (3) | `MayIn` dựng bằng `new`, giữ qua con trỏ `static` | `MayIn` nằm ngoài các đối tượng static |
| hết `main` | Hủy ngược thứ tự hoàn thành: `KetNoi` trước; (1) ghi vào `Bao` lúc này còn sống; rồi `huy Bao`. `MayIn` không bị hủy | |

**Kết quả khi chạy** (ASan + UBSan sạch, không báo rò rỉ vì con trỏ `static` vẫn trỏ tới `MayIn` lúc thoát):

```text
tao KetNoi
tao Bao
  Bao ghi: dang tao ket noi
tao MayIn
het main
huy KetNoi
  Bao ghi: dong ket noi
huy Bao
```

`huy KetNoi` đứng trước `huy Bao` là **bảo đảm của chuẩn**, không phải may. `huy MayIn` không bao giờ hiện: hợp với thứ hủy không có ý nghĩa (bộ nhớ thuần), không hợp với thứ cần xả đệm hay đóng file.

**Thử thay đổi (đã chạy):** xóa dòng (2) (bỏ lời gọi `Bao::lay()` trong hàm tạo `KetNoi`) và thêm `Bao::lay().ghi("xin chao");` vào `main` sau `KetNoi::lay();`. Giờ `Bao` xong **sau** `KetNoi` nên hủy **trước**: in `huy Bao`, `huy KetNoi`, rồi `Bao ghi: dong ket noi`. Hàm hủy `KetNoi` dùng một `Bao` đã bị hủy: hành vi không xác định, nhưng `Bao` ở đây không có dữ liệu nên chạy êm và ASan im lặng. Bài 35 đã chạy cùng lỗi với `Bao` có `vector` (ASan báo `double-free`).

### Ví dụ 6 (bản sai đề b): cờ thường, bật cờ sớm, và hai singleton gọi nhau

**Bản A và B.** Tài nguyên là `bang[1000]` (`bang[i] = i*i`), cờ `daXong` là `bool` thường. Bản A bật cờ **sau** khi dựng (double-checked locking với cờ thường); bản B bật cờ **trước** khi dựng. `main` nhận bản (`A` hoặc `B`, đọc từ chữ đầu `argv[1][0]` của đối số thứ nhất) và số vòng qua `argv`, mỗi vòng chạy 8 luồng và đếm số lần luồng thấy `bang[999]` sai.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int bang[1000];                                 // tai nguyen: bang[i] = i * i
bool daXong = false;                            // co THUONG, khong atomic
std::mutex khoa;

void dung(bool batSom) {
    if (batSom) {
        daXong = true;                          // (1) ban B: bat co TRUOC khi dung
        std::this_thread::sleep_for(std::chrono::milliseconds(2));   // gia vo viec dung ton cong
    }
    for (int i = 0; i < 1000; ++i) bang[i] = i * i;
    if (!batSom) daXong = true;                 // (2) ban A: bat co SAU khi dung, nhung la bool thuong
}

const int* lay(bool batSom) {
    if (!daXong) {                              // (3) doc co ngoai khoa
        std::lock_guard<std::mutex> giu(khoa);
        if (!daXong) dung(batSom);
    }
    return bang;
}

int main(int argc, char** argv) {
    bool batSom = argc > 1 && argv[1][0] == 'B';
    int soVong = argc > 2 ? std::atoi(argv[2]) : 1, soSai = 0;
    for (int v = 0; v < soVong; ++v) {
        daXong = false;
        for (int& x : bang) x = 0;
        int sai[8] = {};
        std::vector<std::thread> cacLuong;
        for (int t = 0; t < 8; ++t)
            cacLuong.emplace_back([&sai, t, batSom] { if (lay(batSom)[999] != 999 * 999) sai[t] = 1; });   // (4)
        for (auto& th : cacLuong) th.join();
        for (int s : sai) soSai += s;
    }
    std::cout << "ban " << (batSom ? 'B' : 'A') << ": so lan doc phai bang chua xong = " << soSai << "\n";
    return 0;
}
```

```text
./w2 B 1     ->  ban B: so lan doc phai bang chua xong = 7   (5 lan chay: 7, 7, 7, 7, 7)
./w2 A 30000 ->  ban A: so lan doc phai bang chua xong = 0   (-O0 va -O2)
```

- **Bản B** sai **thật, trên máy này**: 7 trong 8 luồng đọc bảng dở (tối đa 7, vì luồng đang dựng luôn thấy đúng; ở bản thử trước đó mình từng thấy 5 và 6, nên con số đổi theo lần chạy). Luồng tới sau thấy `daXong` là `true`, bỏ qua khóa, đọc `bang[999]` còn 0. Đây là lỗi thứ tự logic, không phụ thuộc CPU.
- **Bản A**: mình chạy **30000 vòng × 8 luồng** ở `-O0` và `-O2`: **0 lần sai**. x86 giữ thứ tự ghi nên bản này khó phá bằng thực nghiệm; mình **không tái hiện được**. Nhưng chuẩn vẫn gọi đây là data race, và TSan báo **hai** `data race` (mã 66, `-O0` lẫn `-O2`): một trên chính `daXong` (đọc ngoài khóa ở (3), ghi trong khóa ở (2)), một trên **dữ liệu** `bang` (đọc ở (4) không có quan hệ nào với việc ghi). Báo cáo thứ hai nói thẳng "không có cầu từ lúc dựng tới lúc đọc"; trên ARM hay trình biên dịch khác chuẩn không hứa gì.

**Bản C: hai singleton gọi nhau.** Hàm tạo `A` cần `B`, hàm tạo `B` cần `A`; hai luồng chạm hai singleton khác nhau cùng lúc.

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <thread>

struct A { static A& lay(); A(); int x = 1; };
struct B { static B& lay(); B(); int y = 1; };
A& A::lay() { static A a; return a; }
B& B::lay() { static B b; return b; }
void ngu() { std::this_thread::sleep_for(std::chrono::milliseconds(50)); }
A::A() { ngu(); x = B::lay().y; }               // (1) A can B
B::B() { ngu(); y = A::lay().x; }               // (2) B can A

int main() {
    std::thread t1([] { A::lay(); });
    std::thread t2([] { B::lay(); });
    t1.join(); t2.join();
    std::cout << "xong\n";
}
```

Chạy với `timeout 5`: **không in gì**, mã thoát **124**. Đó là deadlock hai khóa ngược thứ tự (Bài 26), chỉ khác là hai "khóa" do trình biên dịch sinh ra nên không thấy trong code. Biến thể một luồng (`A::lay()` gọi `B::lay()` gọi lại `A::lay()`): chuẩn nói không xác định; g++ 11.4 chạy thường thì `terminate called after throwing an instance of '__gnu_cxx::recursive_init_error'` (mã 134), còn dưới TSan thì **treo** (124). Sửa bằng thiết kế: bỏ phụ thuộc vòng, hoặc tách phần chung thành singleton thứ ba mà cả hai cùng dùng.

### Ví dụ 7: chi phí của ba cách trên đường nóng

Ba hàm `lay()` trả cùng một `Nang`. Hàm tạo phải có tác dụng phụ: nếu nó tầm thường thì g++ khởi tạo biến lúc biên dịch và `static` không tốn gì (thí nghiệm đầu của mình đã sai vì thế). Tám luồng, mỗi luồng gọi `lay().v` rất nhiều lần.

```cpp
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

std::atomic<int> soLanTao{0};
struct Nang {
    int v = 3;
    Nang() { ++soLanTao; }                      // ham tao khong hang so: bat buoc khoi tao luc chay
};
std::mutex khoa;
std::once_flag co;
std::unique_ptr<Nang> p2, p3;

Nang& meyers() { static Nang n; return n; }
Nang& goiOnce() { std::call_once(co, [] { p2.reset(new Nang); }); return *p2; }
Nang& khoaMoiLan() {
    std::lock_guard<std::mutex> giu(khoa);
    if (!p3) p3.reset(new Nang);
    return *p3;
}

template <class H>
void chayThu(const char* ten, int lan, H lay) { // 8 luong, moi luong goi lay() "lan" lan
    std::atomic<long long> tong{0};
    auto t0 = std::chrono::steady_clock::now();
    std::vector<std::thread> v;
    for (int i = 0; i < 8; ++i)
        v.emplace_back([&] { long long s = 0; for (int k = 0; k < lan; ++k) s += lay().v; tong += s; });
    for (auto& t : v) t.join();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
    std::cout << ten << ": tong = " << tong << ", " << ms << " ms\n";
}

int main(int argc, char** argv) {
    int lan = argc > 1 ? std::atoi(argv[1]) : 100000;
    chayThu("static cuc bo    ", lan, meyers);
    chayThu("call_once        ", lan, goiOnce);
    chayThu("khoa moi lan goi ", lan, khoaMoiLan);
    std::cout << "so lan tao: " << soLanTao << "\n";
    return 0;
}
```

Chương trình in thời gian thật nên **không tất định** về thời gian (không đối số: 100 nghìn lần mỗi luồng, chỉ để chắc nó chạy và TSan sạch). Một lần chạy với đối số `2000000` (16 triệu lượt gọi mỗi cách), g++ 11.4 `-O2`, máy 8 lõi này; **số đổi theo máy và `-O`**:

```text
static cuc bo    : tong = 48000000, 14 ms
call_once        : tong = 48000000, 48 ms
khoa moi lan goi : tong = 48000000, 650 ms
so lan tao: 3
```

Ba lần chạy `-O2`: `static` 14 đến 25 ms, `call_once` 48 đến 59 ms, khóa mỗi lần 650 đến 673 ms. Ba lần chạy `-O0`: `static` 19 đến 28 ms, `call_once` 175 đến 266 ms, khóa mỗi lần 2555 đến 2582 ms. Đọc kết quả:

- **`static`**: đọc mã máy (`g++ -S -O2`): đường nhanh là một lệnh đọc **byte cờ** rồi nhảy; chỉ khi chưa xong mới gọi hàm thư viện `__cxa_guard_acquire` để xin dựng.
- **`call_once`**: chậm hơn `static` khoảng 2 đến 4 lần: mã máy cho thấy **mỗi lần gọi** nó ghi hai ô thread-local (biến mỗi luồng một bản) và gọi `pthread_once` (hàm của hệ điều hành chạy một việc đúng một lần).
- **Khóa mỗi lần**: chậm hơn `static` chừng 25 đến 45 lần: tám luồng tranh một mutex dù không còn gì để dựng.
- **Độ phức tạp**: cả ba O(1) mỗi lần gọi, khác ở hằng số và tranh chấp; cả ba dựng đúng một lần (`so lan tao: 3`: mỗi cách một bản).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết singleton an toàn luồng. `static` cục bộ hay `call_once`? Còn nếu hàm tạo cần tham số?"
    Mặc định `static` cục bộ: từ C++11 nhiều luồng cùng vào lần đầu thì một luồng chạy hàm tạo, luồng khác chờ; đường nhanh chỉ là đọc một byte cờ (mình đọc mã máy g++ 11). Dùng `call_once` + `once_flag` khi hàm tạo cần tham số lúc chạy hoặc muốn tự chọn lúc dựng; đổi lại chậm hơn (mình đo 2 đến 4 lần). Mình kiểm bằng 8 luồng và bộ đếm: số lần tạo phải 1. Với tham số, luồng tới trước thắng và tham số khác bị bỏ qua âm thầm (tên thắng đổi theo lần chạy), nên nếu tham số quan trọng thì khởi tạo tường minh ở `main`. Câu nối tiếp: "Dùng đối tượng đó có an toàn luồng không?" Không tự động: chỉ khởi tạo được bảo vệ.

??? question "Double-checked locking kiểu cũ sai ở đâu? Trên x86 chạy cả triệu lần không sai thì sao?"
    Kiểm cờ hay con trỏ thường ngoài khóa trong lúc luồng khác ghi nó là data race (hành vi không xác định); ngoài ra ghi cờ có thể hiện ra trước khi dựng xong. Mình đo: bật cờ trước khi dựng thì sai thật (7 trong 8 luồng thấy bảng dở); bật cờ sau khi dựng, cờ thường, thì 30000 vòng trên x86 **không** sai nhưng TSan báo hai data race, một trên cờ một trên dữ liệu. "Chưa thấy sai" chỉ là may của một CPU và một trình biên dịch. Cách đúng: `static`, `call_once`, hoặc con trỏ `atomic` với `release`/`acquire` ([Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md)).

??? question "Hàm tạo của singleton ném ngoại lệ thì sao?"
    Cả `static` cục bộ và `call_once` cho **thử lại**: biến coi như chưa khởi tạo, lần gọi sau chạy lại hàm tạo (mình chạy: 2 lần thử, đúng một luồng thấy ngoại lệ, cả 8 luồng có kết quả cuối). Go khác: `sync.Once.Do` coi hàm đã chạy xong dù panic nên không thử lại. Riêng máy này: `call_once` mà hàm ném ngoại lệ thì treo dưới TSan của g++ 11.4 (mã 124) dù chạy thường đúng; đó là hạn chế công cụ.

??? question "Hai singleton dùng nhau thì hủy theo thứ tự nào? Phụ thuộc vòng thì sao?"
    `static` cục bộ bị hủy ngược thứ tự **hoàn thành** dựng (chuẩn bảo đảm). `KetNoi` gọi `Bao::lay()` trong hàm tạo thì `Bao` hoàn thành trước, hủy sau, nên hàm hủy `KetNoi` ghi vào `Bao` an toàn (Ví dụ 5). Nếu chỉ dùng `Bao` trong hàm hủy mà `Bao` dựng sau thì nó hủy trước: hành vi không xác định, có khi im lặng. Phụ thuộc vòng không có thứ tự đúng: hai luồng thì deadlock (mình chạy: mã 124), một luồng thì không xác định (g++ ném `recursive_init_error`). Lối thoát khác là singleton rò rỉ có chủ ý (`new` không `delete`), đổi lại hàm hủy không chạy.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Đặt `once_flag` hoặc mutex làm biến cục bộ"
    Mỗi lần gọi có một cờ mới nên "chỉ một lần" hết nghĩa (mình chạy: 8 lần tạo). Cờ và mutex bảo vệ trạng thái chung phải sống lâu bằng trạng thái đó: thành viên `static` hoặc biến toàn cục.

!!! warning "Lỗi 2: Xin khóa rồi dựng mà quên kiểm lại, hoặc bật cờ 'đã xong' quá sớm"
    Hai lần kiểm đều cần (quên: 8 lần tạo). Cờ bật trước khi dựng xong làm luồng khác đọc dữ liệu dở (7 trong 8 luồng). Và kiểu "kiểm ngoài khóa với cờ/con trỏ thường" vẫn sai theo chuẩn: bỏ nó, dùng `static`/`call_once`.

!!! warning "Lỗi 3: Lấy 'chạy đúng trên máy tôi' làm bằng chứng, hoặc nói 'static là an toàn luồng' rồi dừng"
    x86 không phạt bản cờ thường (30000 vòng, 0 lỗi) nhưng TSan vẫn báo race: hãy tách rõ "chuẩn bảo đảm" khỏi "máy tôi cho kết quả". Và `static` chỉ bảo vệ **khởi tạo**: dùng đối tượng vẫn cần khóa, phụ thuộc vòng vẫn deadlock, thứ tự hủy vẫn có thể hại. Người phỏng vấn hay hỏi tiếp đúng các chỗ này.

!!! warning "Lỗi 4: Lao vào code mà không hỏi lại đề"
    Hỏi trước: hàm tạo có tham số không, có thể ném không, sau này có cần dựng lại không, sống tới hết chương trình hay có lúc phải hủy? Câu trả lời quyết định chọn `static`, `call_once` hay một thiết kế không dùng singleton. Nói to suy nghĩ này cũng là điểm cộng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="68" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Singleton cần một đường dẫn file làm tham số hàm tạo, `lay(duongDan)` dùng `call_once`. Hai luồng cùng gọi lần đầu, một luồng truyền `"a.cfg"`, luồng kia `"b.cfg"`. Điều gì xảy ra?

- Hàm tạo chạy hai lần, mỗi luồng giữ một bản riêng theo đường dẫn của chính mình
- Luồng tới sau bị ném ngoại lệ, vì truyền tham số khác với lần dựng đầu tiên
- Chạy một lần với đường dẫn của luồng tới trước; luồng kia bị bỏ qua âm thầm
- Cả hai đường dẫn được gộp vào một bản, vì hàm tạo nhận cả hai tham số cùng lúc

<p class="giai-thich" markdown>`call_once` chạy hàm một lần, với lambda của luồng thắng, nên đường dẫn của luồng thua bị bỏ qua không báo gì (mình chạy: tên thắng đổi giữa các lần chạy). Ý mỗi luồng giữ một bản riêng là hành vi của biến `thread_local` (mỗi luồng một bản), không phải của `call_once`. Thư viện không so tham số giữa các lần gọi nên không ném. Hàm tạo chỉ chạy với một bộ tham số, không có chuyện gộp. Muốn kiểm soát thì khởi tạo tường minh ở `main`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Tám luồng cùng gọi `lay()`. Kết quả nào đúng?

```text
SoGhi& lay() {
    std::once_flag co;
    static SoGhi* p = nullptr;
    std::call_once(co, [] { p = new SoGhi; });
    return *p;
}
```

- Có thể tạo tới 8 `SoGhi`: mỗi lần gọi có một `once_flag` mới, và `p` bị ghi đồng thời
- Đúng một `SoGhi`, vì `call_once` luôn bảo đảm chạy hàm đúng một lần cho mọi luồng
- Đúng một `SoGhi`, nhưng chỉ khi biên dịch với `-O2` nên không luồng nào chen vào được
- Không biên dịch được, vì `once_flag` không được phép khai báo làm biến cục bộ trong hàm

<p class="giai-thich" markdown>Cờ `co` sinh ra mới trong mỗi lần gọi và chết cuối lần gọi, nên không có gì "nhớ" chuyện đã dựng: mình chạy ra 8 lần tạo, TSan báo data race khi ghi `p`. Bảo đảm của `call_once` chỉ áp dụng cho **cùng một** cờ. Cờ `-O2` không đổi luật của chuẩn. Khai báo `once_flag` cục bộ vẫn biên dịch được, chỉ là vô nghĩa.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. Dựng mất khoảng 2 ms; nhiều luồng gọi `lay()` lần đầu cùng lúc. Lỗi nằm ở đâu?

```text
std::atomic<bool> xong{false};   int bang[1000];
void dung() { xong = true;  /* điền bang, mất 2 ms */ }
int* lay() { if (!xong) { lock(m); if (!xong) dung(); } return bang; }
```

- Thiếu lần kiểm thứ hai trong khóa, nên `dung()` có thể chạy nhiều lần cùng lúc
- Cờ `atomic` được đọc ngoài khóa, nên vẫn là data race ngay trên chính cờ đó
- Phải bỏ lần kiểm ngoài khóa, vì kiểm hai lần luôn là sai về mặt nguyên tắc
- Cờ bật trước khi điền xong, nên luồng tới sau thấy `xong` mà `bang` còn dở

<p class="giai-thich" markdown>Đoạn code đã có hai lần kiểm, và cờ là `atomic` nên đọc nó ngoài khóa không phải data race. Lỗi là thứ tự: bật `xong` rồi mới điền bảng, nên luồng khác đọc cờ `true`, bỏ qua khóa và thấy bảng chưa điền (mình chạy với cờ `atomic`: có lần 7 trong 8 luồng thấy sai). Thiếu lần kiểm hai không đúng với đoạn này vì nó đã có. Nói kiểm hai lần luôn sai cũng không đúng: với cờ `atomic` và bật cờ **sau** khi điền xong thì nó đúng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Dịch vụ cần "đối tượng cấu hình dùng chung", nhưng khi quản trị viên đổi file cấu hình thì phải **dựng lại**, và các luồng đang chạy dùng bản mới từ lần đọc sau. Nên chọn gì?

- `static` cục bộ, vì nó an toàn luồng nên đổi cấu hình cũng an toàn
- Mutex bảo vệ một `shared_ptr`; thay con trỏ mỗi khi cấu hình đổi
- `call_once` với một cờ, rồi `reset` lại cờ mỗi khi cấu hình đổi để dựng lại
- Biến toàn cục thường, vì chỉ quản trị viên ghi nên không có race

<p class="giai-thich" markdown>`static` và `call_once` chỉ cho **một** lần khởi tạo thành công, không có thao tác dựng lại. Thứ cần là con trỏ đổi được dưới khóa; luồng đọc sao chép `shared_ptr` ra bản chụp rồi dùng ngoài khóa. `once_flag` không có `reset` trong chuẩn. Biến toàn cục thường vẫn là data race giữa lần ghi của quản trị viên và lần đọc của luồng khác, dù chỉ một người ghi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Singleton `static NangLuong n;` có hàm tạo ném ngoại lệ ở lần chạy đầu và chạy bình thường từ lần hai. Lần gọi `lay()` thứ hai của chương trình sẽ thế nào?

- Hàm tạo không chạy lại; `lay()` trả về đối tượng dựng dở của lần đầu
- Chương trình gọi `std::terminate` vì biến `static` đã thử khởi tạo một lần
- Hàm tạo chạy lại từ đầu vì biến vẫn được coi là chưa khởi tạo
- Lần gọi thứ hai cũng ném cùng ngoại lệ, vì chuẩn lưu kết quả lần đầu

<p class="giai-thich" markdown>Chuẩn nói nếu khởi tạo biến `static` cục bộ kết thúc bằng ngoại lệ thì biến chưa được khởi tạo, và lần chạy qua khai báo sau sẽ thử lại (mình chạy: 2 lần thử, 1 luồng thấy ngoại lệ). Hành vi "không chạy lại" là của `sync.Once` trong Go khi panic, đừng mang sang C++. `terminate` chỉ xảy ra khi ngoại lệ ra khỏi chỗ không bắt được, không phải vì đã thử khởi tạo. Chuẩn không lưu ngoại lệ để ném lại.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn sau. Hàm tạo `KetNoi` gọi `Bao::lay()` ở dòng đầu; hàm hủy `KetNoi` ghi vào `Bao`. `main` chỉ gọi `KetNoi::lay()` rồi thoát. Thứ tự hủy?

```text
KetNoi() { Bao::lay().ghi("tao"); }
~KetNoi() { Bao::lay().ghi("huy"); }
```

- `KetNoi` hủy trước, rồi `Bao`, và lệnh ghi trong hàm hủy `KetNoi` an toàn
- `Bao` hủy trước vì nó bắt đầu dựng sau, nên hàm hủy `KetNoi` dùng `Bao` đã chết
- `KetNoi` hủy trước, nhưng chuẩn không nói gì về `Bao` nên không biết còn sống không
- Thứ tự hủy do trình biên dịch tự chọn và có thể khác nhau giữa các lần chạy

<p class="giai-thich" markdown>Biến `static` cục bộ hủy ngược thứ tự **hoàn thành** dựng. `Bao` hoàn thành bên trong hàm tạo `KetNoi`, tức trước `KetNoi`, nên hủy sau và lệnh ghi hợp lệ (mình chạy). Nhầm "bắt đầu dựng" với "hoàn thành dựng" dẫn tới đáp án `Bao` chết trước: `KetNoi` bắt đầu trước nhưng xong sau. Chuẩn có quy định thứ tự này nên không phải "không biết", và nó không đổi giữa các lần chạy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Đề "singleton an toàn luồng": mặc định `static T x;` trong hàm (một luồng dựng, luồng khác chờ; ném ngoại lệ thì lần sau thử lại); `std::call_once` + `std::once_flag` (cờ và con trỏ **sống lâu**, thành viên `static`) khi hàm tạo cần tham số lúc chạy, trong đó luồng tới trước thắng, âm thầm. Kiểm bằng 8 luồng và bộ đếm: số lần tạo = 1 (mình chạy cả hai, TSan sạch).
2. Ba bản sai đã chạy: `once_flag` cục bộ và khóa không kiểm lại đều ra 8 lần tạo (kèm TSan báo race); kiểm ngoài khóa với con trỏ/cờ thường thì x86 không tái hiện được kết quả sai (30000 vòng, 0 lỗi) nhưng TSan báo race trên cả cờ lẫn dữ liệu; bật cờ **trước** khi dựng xong thì sai thật (7 trong 8 luồng thấy bảng dở).
3. Khởi tạo lười tài nguyên đắt: `call_once` với `unique_ptr<const T>` rỗng tới khi cần, đọc sau đó không cần khóa vì `call_once` là cầu và bảng bất biến. Bỏ `call_once` (`if (!p) p.reset(...)`) thì chết nhiều lần (mã 139) hoặc dựng 5 đến 6 lần thay vì 1. Ném ngoại lệ thì thử lại (C++), khác `sync.Once` của Go; `call_once` + ngoại lệ dưới TSan của g++ 11.4 thì treo (124), hạn chế công cụ.
4. Thứ tự hủy ngược thứ tự **hoàn thành** dựng: singleton gọi singleton khác trong hàm tạo thì kia hủy sau (an toàn). Phụ thuộc vòng: hai luồng deadlock (124), một luồng không xác định (`recursive_init_error`). Singleton "rò rỉ có chủ ý" tránh được thứ tự hủy nhưng hàm hủy không bao giờ chạy.
5. Chi phí (16 triệu lượt gọi, 8 luồng, `-O2`, máy này, đổi theo máy): `static` cỡ chục ms vì đường nhanh chỉ đọc một byte cờ, `call_once` chậm hơn 2 đến 4 lần (ghi hai ô thread-local và gọi `pthread_once` mỗi lần), khóa mỗi lần chậm hơn chừng 25 đến 45 lần (cỡ 650 ms). Không dùng `static`/`call_once` khi cần **dựng lại**: dùng mutex + `shared_ptr`.
