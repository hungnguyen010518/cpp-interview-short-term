# Bài 52 — Smart pointer trong đa luồng: thứ gì an toàn, thứ gì không

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Trả lời đúng cả hai nửa câu "`shared_ptr` có thread-safe không?": bộ đếm thì an toàn, còn **đối tượng được trỏ tới** và **chính biến `shared_ptr` bị gán đồng thời** thì không (chạy thật: data race, TSan báo, chương trình có thể sập).
    - Công bố một cấu hình mới cho nhiều luồng đọc bằng `shared_ptr<const T>` cộng mutex (hoặc `std::atomic_load`/`atomic_store`), và biết `std::atomic<std::shared_ptr>` là của C++20.
    - Dùng `weak_ptr::lock()` đúng cách (lấy thẻ rồi mới dùng), `enable_shared_from_this`/`shared_from_this()` (và vì sao không viết `shared_ptr<T>(this)`).
    - Viết callback bất đồng bộ không bị use-after-free: chọn giữa bắt `weak_ptr` ("chủ chết thì bỏ qua") và bắt `shared_ptr` ("giữ chủ sống tới khi xong"); trao `unique_ptr` sang luồng khác bằng `std::move`.

**Bạn cần biết trước:** [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, khối điều khiển, `weak_ptr`, `lock()`; mục 6 đã nói ngắn về luồng), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `std::move`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`/`detach`, đối số được sao chép vào luồng), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`, `lock_guard`, lớp `BoDem`, TSan), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic`), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`promise`/`future`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda và danh sách bắt), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`this`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) và [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (use-after-free, ASan), [Bài 32](../nhom-4-oop-patterns/32-ke-thua.md) (kế thừa `: Cha`), [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (observer giữ `weak_ptr`). [Bài 51](51-chon-smart-pointer.md) (chọn smart pointer) là bài "ai sở hữu?"; bài này hỏi tiếp: "nhiều luồng cùng dùng thì sao?".

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Hôm nay bếp có một **tủ nguyên liệu** ở kho. Mỗi đầu bếp cần dùng tủ thì được phát một **tấm thẻ tủ** (`shared_ptr`), và cửa tủ treo một **bảng đếm** "đang có mấy thẻ" (chính là **khối điều khiển** của [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)). Bảng đếm này đặc biệt: ai nhận hay trả thẻ thì ghi **tức thì và không bao giờ ghi lệch**, dù mười người cùng ghi một lúc. Người trả thẻ cuối cùng làm bảng về 0, tủ bị dọn.

Nhưng tấm thẻ chỉ nói "tủ còn mở". Nó **không** bảo vệ **nguyên liệu bên trong**: hai đầu bếp cùng thò tay vào tủ sửa một món vẫn đụng nhau, và muốn tránh thì cần thêm **thẻ vào thớt** (mutex, [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)), một thứ khác hẳn tấm thẻ tủ. Và còn một chỗ nữa: các thẻ được cất trong một **ngăn kéo** (biến `shared_ptr`). Hai người cùng giật ngăn kéo để đổi thẻ bên trong thì thẻ cũ và thẻ mới lẫn lộn.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Đầu bếp thật nhìn thấy ai đang giật ngăn kéo và nhường nhau; chương trình thì không "nhìn" gì cả, nó chỉ chạy lệnh. Ngoài ra thẻ thật là đồ vật, còn `shared_ptr` là một biến chứa **hai con trỏ** (một tới đối tượng, một tới bảng đếm); mục 2 dùng đúng chi tiết đó.

## 📖 Giải thích

### 1. Ba tầng: bộ đếm, đối tượng, biến `shared_ptr`

[Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) mục 6 nói "`shared_ptr` chỉ an toàn ở phần bộ đếm". Bài này đào sâu câu đó. Muốn trả lời đúng một câu hỏi phỏng vấn, hãy tách **ba thứ khác nhau** mà người ta hay gộp thành một:

| Tầng | Là gì | Nhiều luồng cùng đụng thì sao | Ai phải lo |
|---|---|---|---|
| 1. Bộ đếm | Hai con số trong khối điều khiển ở heap | **An toàn**: cập nhật bằng thao tác nguyên tử | Thư viện chuẩn |
| 2. Đối tượng được trỏ tới | `BoDem`, `Cay`, `CauHinh`... | **Không tự an toàn**: hai luồng sửa là data race | Bạn: mutex/atomic trong đối tượng, hoặc làm nó bất biến (`const`) |
| 3. Biến `shared_ptr` | Chính ô nhớ chứa hai con trỏ | Nhiều luồng cùng **đọc** (sao chép) thì ổn; **có luồng ghi** (gán, `reset`, `swap`) thì không | Bạn: mutex, hoặc `atomic_load`/`atomic_store` |

Chuẩn nói chính xác thế này: hai luồng dùng **hai biến `shared_ptr` khác nhau**, dù cùng trỏ một đối tượng, thì không cần đồng bộ cho tầng 1 và tầng 3. Mẹo thực dụng: **mỗi luồng giữ một bản `shared_ptr` riêng** (chép vào lambda, truyền theo giá trị), khi đó chỉ còn tầng 2 cần bạn lo.

Chương trình dưới đây cho thấy tầng 1 an toàn và tầng 2 do đối tượng tự lo. Bốn luồng cùng **đọc** biến `goc` (sao chép và hủy bản sao 100000 lần mỗi luồng) và gọi `tang()` của `BoDem` ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md): dữ liệu và mutex nằm chung trong lớp). Hàm hủy của `BoDem` đếm số lần nó chạy, để ta thấy đối tượng chỉ bị hủy đúng một lần.

```cpp
#include <atomic>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

std::atomic<int> soLanHuy{0};                      // đếm số lần hàm hủy của BoDem chạy

class BoDem {                                      // khóa nằm TRONG đối tượng (như Bài 25)
public:
    ~BoDem() { ++soLanHuy; }
    void tang() {
        std::lock_guard<std::mutex> giu(khoa);     // (1) tầng 2: dữ liệu của đối tượng do mutex lo
        ++dem;
    }
    int doc() {
        std::lock_guard<std::mutex> giu(khoa);
        return dem;
    }
private:
    std::mutex khoa;
    int dem = 0;
};

int main() {
    std::shared_ptr<BoDem> goc = std::make_shared<BoDem>();   // (2) use_count = 1
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&goc] {                        // (3) bốn luồng chỉ ĐỌC biến goc
            for (int i = 0; i < 100000; ++i) {
                std::shared_ptr<BoDem> rieng = goc;           // (4) tầng 1: sao chép, đếm +1 nguyên tử
                rieng->tang();                                // (5) dùng đối tượng
            }                                                 // (6) rieng bị hủy: đếm -1 nguyên tử
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << goc->doc() << "\n";
    std::cout << "use_count = " << goc.use_count() << "\n";
    std::cout << "ham huy da chay: " << soLanHuy << " lan\n";
    goc.reset();                                              // (7) thẻ cuối trả đi: đối tượng bị hủy
    std::cout << "sau reset, ham huy da chay: " << soLanHuy << " lan\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng đếm lúc này |
|---|---|---|
| (2) | `make_shared` tạo `BoDem` và bảng đếm; `goc` cầm một thẻ | 1 |
| (4) | Mỗi vòng, một luồng sao chép `goc` thành `rieng`: bảng đếm +1 nguyên tử | 1 + (số bản sao đang sống) |
| (5) | `tang()` xin khóa của **chính `BoDem`**, tăng `dem`, nhả | không đổi |
| (6) | `rieng` hết vòng, bị hủy: bảng đếm -1 nguyên tử | trở về 1 khi cả bốn luồng xong |
| (7) | `reset()` trả thẻ cuối, bảng về 0, `~BoDem` chạy một lần | 0 |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, ASan sạch):

```text
dem = 400000
use_count = 1
ham huy da chay: 0 lan
sau reset, ham huy da chay: 1 lan
```

Bốn luồng, bốn trăm nghìn lần sao chép và hủy thẻ, mà bảng đếm vẫn về đúng 1 và `~BoDem` chạy đúng một lần.

**Thử thay đổi: xóa dòng `std::lock_guard` trong `tang()`.** Mình đã chạy: `dem` ra `262857`, `234911`, `268054` (máy bạn ra số khác, nhưng nhỏ hơn 400000); `use_count` **vẫn là 1** và `~BoDem` vẫn chạy một lần. TSan báo `data race` tại `++dem` và nêu `Location is heap block of size 64 ... allocated by main thread`. Đây là chỗ mà người ta hay nhầm: tầng 1 vẫn đúng hoàn toàn, nhưng tầng 2 hỏng, vì `shared_ptr` chưa bao giờ hứa bảo vệ đối tượng.

### 2. Tầng 3: gán lại cùng một biến `shared_ptr` từ nhiều luồng

Bài toán thường gặp: một **cấu hình** dùng chung. Nhiều luồng đọc nó liên tục, còn một luồng thỉnh thoảng thay **cả cấu hình** bằng bản mới. Ta để biến toàn cục `hienTai` kiểu `shared_ptr<const CauHinh>`; `const` nghĩa là đối tượng không đổi sau khi tạo, nên tầng 2 hết chuyện. Cấu hình có hai số `a` và `b` luôn phải bằng nhau; luồng đọc đếm số lần thấy `a != b`.

Bản dưới đây **sai**: không có khóa nào quanh biến `hienTai`.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <memory>
#include <thread>

struct CauHinh {
    int a, b;                                   // luôn phải có a == b
    CauHinh(int v) : a(v), b(v) {}
};

std::shared_ptr<const CauHinh> hienTai = std::make_shared<const CauHinh>(0);   // (1) biến CHUNG

int main() {
    long long khongNhatQuan = 0;
    std::thread ghi([] {
        for (int v = 1; v <= 100000; ++v)
            hienTai = std::make_shared<const CauHinh>(v);   // (2) GHI vào biến shared_ptr chung
    });
    std::thread doc([&khongNhatQuan] {
        for (int i = 0; i < 100000; ++i) {
            std::shared_ptr<const CauHinh> s = hienTai;      // (3) ĐỌC (sao chép) cùng biến, cùng lúc
            if (s->a != s->b) ++khongNhatQuan;
        }
    });
    ghi.join();
    doc.join();
    std::cout << "khong nhat quan: " << khongNhatQuan << "\n";
    return 0;
}
```

Vì sao hỏng: biến `hienTai` là **hai con trỏ** (tới đối tượng, tới bảng đếm). Dòng (2) đổi cả hai, dòng (3) đọc cả hai, và không có gì bắt hai việc đó xếp hàng. Một kiểu hỏng có thể xảy ra: luồng đọc lấy con trỏ đối tượng **cũ** mà bảng đếm **mới** (hoặc ngược lại), rồi cộng hay trừ đếm vào một bảng đã bị dọn. TSan thật sự báo hai vụ xung đột riêng, ở hai nửa của biến (mỗi nửa 8 byte).

Mình biên dịch sạch và chạy hai đợt, mỗi đợt mười lần, không sanitizer: **hầu hết chết với mã 134** (in `pure virtual method called` rồi `terminate called without an active exception`; bảy và tám lần trong hai đợt), **hai lần mỗi đợt mã 139** (lỗi phân đoạn), và ở một đợt có **một lần** chạy xong, in `khong nhat quan: 0` với mã 0. TSan báo `data race` nhiều lần, trong đó có `Location is global 'hienTai' of size 16` và có cả `heap-use-after-free`; ASan cũng báo `heap-use-after-free`. Chuẩn không hứa kết quả nào: đó là hành vi không xác định, và lần chạy "ra 0, sạch" ở trên **không chứng minh gì**.

Có ba cách sửa. Cách thông dụng nhất là **một mutex bọc đúng việc sao chép và việc gán con trỏ**; luồng đọc lấy một **bản chụp** (một `shared_ptr` riêng) rồi dùng nó ở ngoài khóa. Code đầy đủ nằm ở mục 💻 bên dưới (lớp `HopCauHinh`). Hai cách còn lại:

- **`std::atomic_load` và `std::atomic_store`** (C++11, `#include <memory>` là đủ cho `shared_ptr`): hàm tự do nhận **địa chỉ** biến, làm việc đọc và việc gán thành nguyên tử. **Thử thay đổi:** ở bản sai trên, đổi dòng (2) thành `std::atomic_store(&hienTai, std::make_shared<const CauHinh>(v));` và dòng (3) thành `std::shared_ptr<const CauHinh> s = std::atomic_load(&hienTai);`. Mình đã chạy: ra `khong nhat quan: 0` bốn lần, TSan sạch, không cảnh báo khi biên dịch kèm `-Wall`, kể cả `-std=c++20`.
- **`std::atomic<std::shared_ptr<T>>`** (C++20): kiểu atomic hẳn hoi cho `shared_ptr`, và chuẩn C++20 đánh dấu các hàm `atomic_load`/`atomic_store` cho `shared_ptr` ở trên là **lỗi thời** vì đã có kiểu này.

Mình thử biên dịch dòng `std::atomic<std::shared_ptr<int>> p;` với `g++ -std=c++20` (g++ 11.4): lỗi `static assertion failed: std::atomic requires a trivially copyable type`, vì thư viện chuẩn của g++ 11 chưa cài kiểu này (bản mới hơn thì có). Nên bài không đưa nó vào code chạy. Bạn chỉ cần nhận ra tên và biết nó là bản "chính thức" của cách sửa trên.

!!! info "Bạn biết Go?"
    Go có bộ gom rác nên không có "thẻ", nhưng tầng 3 thì y hệt: mình chạy `go run -race` cho một con trỏ chung bị gán và đọc đồng thời, `-race` in `WARNING: DATA RACE` (chương trình vẫn in được kết quả, và chuẩn bộ nhớ của Go cũng coi đó là race). Cách sửa là `atomic.Pointer[T]` (Go 1.19) với `Load`/`Store`, ứng với `atomic_load`/`atomic_store`; mình chạy bản này của đúng bài toán trên (hai goroutine, 100000 vòng): `bad2 0`, `-race` không báo gì.

### 3. `weak_ptr::lock()`: lấy thẻ rồi mới dùng

[Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) mục 5 dạy `lock()`: trả `shared_ptr` nếu đối tượng còn sống, rỗng nếu đã chết. Trong đa luồng, `lock()` có thêm một điểm cốt lõi: nó thực hiện **trong một bước nguyên tử**, nên giữa lúc "kiểm còn sống" và lúc "lấy thẻ" không ai xen vào được. Có thẻ trong tay thì đối tượng **chắc chắn sống** tới khi bạn trả thẻ.

Vì thế mẫu đúng là `if (auto sp = yeu.lock()) { dùng sp }`. Mẫu **sai** là `if (!yeu.expired()) yeu.lock()->dung();`: sau `expired()` trả `false`, luồng khác có thể trả thẻ cuối, và `lock()` ra rỗng, `->` gọi trên con trỏ rỗng.

Ta chạy hai tình huống với một luồng nền. Luồng nền chờ tín hiệu rồi mới `lock()`; `promise<void>` là kênh chỉ để báo "được rồi" mà không mang giá trị, và `f.wait()` chờ tín hiệu đó ([Bài 29](../nhom-3-da-luong/29-async-future.md)). `std::this_thread::get_id()` trả mã định danh luồng đang chạy; ta dùng nó để xem hàm hủy chạy ở luồng nào.

```cpp
#include <future>
#include <iostream>
#include <memory>
#include <thread>

std::thread::id luongTao;                          // luồng chính, ghi lại ở đầu main

struct Phien {
    ~Phien() {
        std::cout << "  Phien bi huy, o luong chinh? "
                  << (std::this_thread::get_id() == luongTao) << "\n";
    }
    void chao() const { std::cout << "  xin chao tu Phien\n"; }
};

void thu(std::weak_ptr<Phien> yeu, std::future<void> cho) {
    cho.wait();                                    // (1) chờ main xếp xong tình huống
    std::shared_ptr<Phien> sp = yeu.lock();        // (2) một bước nguyên tử: ra thẻ, hoặc ra rỗng
    if (sp) sp->chao();                            // (3) có thẻ: Phien chắc chắn còn sống
    else std::cout << "  Phien da chet, bo qua\n";
}

void tinhHuong(bool chuBiHuyTruoc) {
    auto chu = std::make_shared<Phien>();
    std::promise<void> tin;
    std::thread t(thu, std::weak_ptr<Phien>(chu), tin.get_future());   // (4) luồng nền chỉ cầm weak_ptr
    if (chuBiHuyTruoc) chu.reset();                // (5) main trả thẻ cuối: Phien bị hủy ngay ở main
    tin.set_value();                               // (6) cho luồng nền chạy tiếp
    t.join();
}

int main() {
    luongTao = std::this_thread::get_id();
    std::cout << "Tinh huong A: chu con song luc luong nen goi lock()\n";
    tinhHuong(false);
    std::cout << "Tinh huong B: chu da bi huy truoc khi luong nen goi lock()\n";
    tinhHuong(true);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Tình huống |
|---|---|---|
| (1) | Luồng nền dừng chờ, chưa đụng `Phien` | A và B |
| (6) | A: `chu` còn giữ thẻ khi `main` báo tin; luồng nền `lock()` nhận một thẻ, in lời chào | A: `lock()` ra thẻ |
| (5) | B: `chu.reset()` là thẻ cuối, bảng về 0, `~Phien` chạy ngay trong `main` | B |
| (2) | B: luồng nền `lock()` sau đó, đối tượng đã chết, ra rỗng, in "da chet" | B: `lock()` ra rỗng |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
Tinh huong A: chu con song luc luong nen goi lock()
  xin chao tu Phien
  Phien bi huy, o luong chinh? 1
Tinh huong B: chu da bi huy truoc khi luong nen goi lock()
  Phien bi huy, o luong chinh? 1
  Phien da chet, bo qua
```

**Thử thay đổi: ở tình huống B, ở dòng tạo luồng đổi `std::weak_ptr<Phien>(chu)` thành `chu`.** Mình đã chạy (ở bản tách riêng hai tình huống): luồng nền in `xin chao tu Phien` rồi `Phien bi huy, o luong chinh? 0`. Lý do: đối số của `std::thread` được **sao chép nguyên kiểu** ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)), nên luồng đã cất một `shared_ptr` thật (thẻ thứ hai) rồi mới chuyển thành `weak_ptr` lúc gọi hàm. `chu.reset()` không còn là thẻ cuối, và `Phien` bị hủy ở **luồng nền**, lúc thẻ cuối rời đi. Ý chung: **hàm hủy chạy ở luồng nào nhả thẻ cuối**, không nhất thiết luồng đã tạo ra đối tượng.

### 4. `enable_shared_from_this`: đưa ra thẻ từ bên trong đối tượng

Có lúc một hàm thành viên cần đưa chính đối tượng của mình cho nơi khác giữ, ví dụ đăng ký làm người nghe. Ta có `this`, nhưng đó là con trỏ thô. Viết `std::shared_ptr<Nut>(this)` trông hợp lý và là **lỗi nặng**: nó dựng một bảng đếm **mới**, độc lập với bảng đếm của các thẻ đã có. Mình đã chạy: đối tượng tạo bằng `make_shared`, hàm thành viên trả `std::shared_ptr<Nut>(this)`, kết thúc `main` thì chương trình chết với mã 134 (`double free or corruption (out)`); ASan báo `attempting free on address which was not malloc()-ed`. Hai bảng đếm, mỗi bảng tưởng mình là chủ duy nhất, nên đối tượng bị trả hai lần.

Cách đúng: cho lớp kế thừa (như [Bài 32](../nhom-4-oop-patterns/32-ke-thua.md)) **`std::enable_shared_from_this<Lop>`**, viết chính tên lớp trong cặp `<>`. Lớp đó nhớ sẵn một `weak_ptr` tới bảng đếm; hàm **`shared_from_this()`** đưa ra một thẻ **cùng bảng đếm** với các thẻ có sẵn.

```cpp
#include <iostream>
#include <memory>

struct Nut : std::enable_shared_from_this<Nut> {       // (1) kế thừa: mở khóa shared_from_this()
    int id = 7;
    std::shared_ptr<Nut> layChinhMinh() {
        return shared_from_this();                      // (2) xin thẻ CÙNG bảng đếm với các thẻ sẵn có
    }
};

int main() {
    auto n = std::make_shared<Nut>();                   // (3) Nut nằm trong shared_ptr
    std::cout << "use_count ban dau = " << n.use_count() << "\n";
    std::shared_ptr<Nut> khac = n->layChinhMinh();      // (4) thẻ thứ hai, chung bảng đếm
    std::cout << "use_count sau shared_from_this = " << n.use_count() << "\n";
    std::cout << "cung doi tuong? " << (khac == n) << "\n";

    Nut tren_stack;                                     // (5) Nut KHÔNG nằm trong shared_ptr nào
    try {
        tren_stack.layChinhMinh();
    } catch (const std::bad_weak_ptr& e) {              // (6) C++17: ném bad_weak_ptr
        std::cout << "bat duoc bad_weak_ptr: " << e.what() << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng đếm lúc này |
|---|---|---|
| (3) | `make_shared` tạo `Nut` và bảng đếm; lớp cha ghi nhớ bảng đó | 1 |
| (4) | `shared_from_this()` sinh thẻ mới từ bảng đã nhớ; `khac == n` | 2 |
| (5)(6) | `tren_stack` không có bảng đếm nào để nhớ: C++17 quy định ném `std::bad_weak_ptr` | không có |

**Kết quả khi chạy:**

```text
use_count ban dau = 1
use_count sau shared_from_this = 2
cung doi tuong? 1
bat duoc bad_weak_ptr: bad_weak_ptr
```

Hai điều kiện để dùng `shared_from_this()`: đối tượng **đã nằm trong một `shared_ptr`**, và **không gọi trong hàm tạo** (lúc đó thẻ đầu tiên chưa tạo xong). Mình đã chạy lỗi sau: gọi `shared_from_this()` trong hàm tạo của lớp được tạo bằng `make_shared` thì chương trình dừng với `terminate called after throwing an instance of 'std::bad_weak_ptr'`, mã 134.

### 5. Callback bất đồng bộ: bắt `this` là bẫy

**Callback bất đồng bộ** là một việc ta đưa cho luồng khác (hoặc hàng đợi) để chạy **về sau**. Nếu lambda bắt `this`, nó cầm một con trỏ thô tới đối tượng; đối tượng có thể bị hủy trước khi lambda chạy. Dưới đây `hen` bắt `this`, `main` hủy đối tượng trước khi cho callback chạy. Hàm `hen` trả về chính `std::thread` (luồng chuyển đi được, không sao chép được) để `main` còn `join`; lambda nhận tham số `f` (kênh chờ) và `std::thread` đưa đối số `std::move(cho)` vào đó, vì `future` không sao chép được để bắt thẳng.

```cpp
// bo-qua-kiem-tra
#include <future>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

struct ManHinh {
    std::string ten = "man hinh chinh";
    std::thread hen(std::future<void> cho) {            // (1) đăng ký việc chạy ở luồng khác
        return std::thread([this](std::future<void> f) {   // (2) lambda giữ this: con trỏ THÔ
            f.wait();
            std::cout << "callback dung ten: " << ten << "\n";   // (3) đọc this->ten
        }, std::move(cho));
    }
};

int main() {
    auto m = std::make_shared<ManHinh>();
    std::promise<void> tin;
    std::thread t = m->hen(tin.get_future());
    m.reset();                                           // (4) chủ bị hủy TRƯỚC khi callback chạy
    tin.set_value();
    t.join();
    return 0;
}
```

Mình biên dịch sạch và chạy ba lần không sanitizer: **cả ba lần in đúng** `callback dung ten: man hinh chinh`, mã 0. Chuỗi 14 ký tự nằm ngay trong đối tượng, và vùng nhớ vừa trả chưa bị ai ghi đè. Với `-fsanitize=address` thì khác: `heap-use-after-free ... READ of size 14 ... freed by thread T0` (chỉ về dòng `m.reset()`), kèm vị trí đã cấp phát. **Chạy ra đúng không chứng minh chương trình đúng**; chuẩn gọi đây là hành vi không xác định.

Hai cách sửa, và chúng **khác nhau về ý nghĩa**, không chỉ về cú pháp:

| | Bắt `weak_ptr` (`weak_from_this()`) | Bắt `shared_ptr` (`shared_from_this()`) |
|---|---|---|
| Callback cầm gì | Thẻ "nhìn qua kính", không giữ chủ sống | Một thẻ thật, giữ chủ sống |
| Chủ chết trước khi callback chạy | `lock()` ra rỗng: **bỏ qua** | Không chết được: chủ **sống tới khi callback xong** |
| Dùng khi | Việc chỉ có nghĩa nếu chủ còn (cập nhật giao diện, observer) | Việc **phải** hoàn thành dù chủ đã rời đi (ghi nốt dữ liệu) |
| Cái giá | Phải kiểm rỗng | Chủ có thể sống lâu hơn bạn tưởng; hàm hủy chạy ở luồng nền |

`weak_from_this()` là C++17 (`std::weak_ptr` lấy thẳng từ `enable_shared_from_this`); với C++14 trở xuống viết `std::weak_ptr<ManHinh> yeu = shared_from_this();`. Cả hai cách đều cần đối tượng **đã nằm trong `shared_ptr`**. Bản sửa đầy đủ nằm ở mục 💻.

**Luồng `detach` và tham chiếu cũng vậy.** Luồng đã `detach` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) có thể sống lâu hơn hàm đã tạo ra nó, nên **không bao giờ** bắt `[&]` thứ nằm trong hàm đó, kể cả khi thứ đó là một `shared_ptr`: bắt **biến** `shared_ptr` bằng tham chiếu không giữ đối tượng sống, nó chỉ cầm địa chỉ của biến cục bộ sắp chết.

```text
void khoiDong(std::future<void> cho) {
    auto so = std::make_shared<int>(42);                // (1) shared_ptr là biến cục bộ của khoiDong
    std::thread([&so](std::future<void> f) {            // (2) bắt so THEO THAM CHIẾU
        f.wait();
        std::cout << "luong detach doc: " << *so << "\n";   // (3) lúc này khoiDong đã return
    }, std::move(cho)).detach();                        // (4) thả luồng, không ai chờ
}                                                       // (5) hết hàm: biến so bị dọn
```

Mình ghép đoạn này vào một `main` (tạo `promise`, gọi `khoiDong`, `set_value`, rồi `sleep_for` 200 ms để luồng nền kịp chạy) và chạy: cả ba lần chết với mã **139** (lỗi phân đoạn). Với `ASAN_OPTIONS=detect_stack_use_after_return=1` và `-fsanitize=address`, ASan báo `stack-use-after-return ... READ of size 8` ở `shared_ptr::get()`. **Thử thay đổi: ở dòng (2) đổi `[&so]` thành `[so]`** (lambda giữ một thẻ riêng): mình đã chạy ba lần ra `luong detach doc: 42`, TSan sạch, ASan sạch (kể cả `detect_stack_use_after_return=1`). Thứ luồng `detach` dùng nên là thứ nó **sở hữu**, không phải thứ nó **mượn**.

!!! info "Bạn biết Go?"
    `go func() { ... so ... }()` luôn an toàn về tuổi thọ: GC giữ `so` sống chừng nào closure còn dùng, nên Go không có hai lỗi trên. Đổi lại, closure giữ đối tượng sống ngay cả khi bạn muốn nó chết (giống nhánh `shared_ptr` ở bảng trên). Muốn "nhìn mà không giữ" như `weak_ptr` thì từ Go 1.24 có gói `weak` (`weak.Make(p)`, `w.Value()` trả `nil` khi đã bị gom): mình chạy thử, `Value()` ra khác `nil` lúc còn tham chiếu và `nil` sau khi bỏ tham chiếu rồi gọi `runtime.GC()`.

### 6. `unique_ptr` qua luồng: chuyển sở hữu, không chia sẻ

`unique_ptr` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)) không có bảng đếm, nên không có "tầng 1". Qua luồng nó an toàn theo cách khác: **tại mỗi thời điểm chỉ một luồng là chủ**. Trao chủ bằng `std::move`, và việc trao phải có **mốc đồng bộ** (`join`, mutex, hàng đợi có khóa) để luồng nhận chắc chắn thấy trạng thái mới. Hai luồng cùng `move` ra khỏi **cùng một biến** `unique_ptr` là data race (biến bị ghi), giống tầng 3 của `shared_ptr`.

Để đưa `unique_ptr` vào lambda ta cần cú pháp **init-capture** (C++14; Bài 13 chưa dạy): trong dấu `[ ]` viết `[p = std::move(p)]`, nghĩa là tạo **một biến mới tên `p` bên trong lambda**, khởi tạo từ biểu thức bên phải dấu `=`. Viết `[p]` không được vì nó sao chép, mà `unique_ptr` không sao chép được. Phần 2 của ví dụ dùng hàng đợi `std::queue` dưới mutex ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)) làm chỗ chuyển giao.

```cpp
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>
#include <utility>
#include <vector>

int main() {
    // Phần 1: trao một unique_ptr cho một luồng bằng init-capture.
    std::unique_ptr<int> p = std::make_unique<int>(7);
    std::thread t([p = std::move(p)] {                 // (1) biến p MỚI trong lambda, chuyển từ p ngoài
        std::cout << "luong nhan so " << *p << "\n";
    });                                                // (2) từ đây p ngoài rỗng, lambda là chủ
    t.join();
    std::cout << "p ngoai con giu gi khong? " << (p != nullptr) << "\n";

    // Phần 2: trao sở hữu qua hàng đợi dưới mutex.
    std::mutex khoa;
    std::queue<std::unique_ptr<int>> hang;
    std::vector<std::thread> sanXuat;
    for (int k = 0; k < 3; ++k) {
        sanXuat.emplace_back([&khoa, &hang, k] {
            for (int i = 1; i <= 100; ++i) {
                std::unique_ptr<int> v = std::make_unique<int>(k * 1000 + i);   // (3) luồng này là chủ của v
                std::lock_guard<std::mutex> giu(khoa);
                hang.push(std::move(v));                                        // (4) trao chủ vào hàng, dưới khóa
            }
        });
    }
    for (std::thread& th : sanXuat) th.join();
    long long tong = 0;
    int dem = 0;
    while (!hang.empty()) {
        std::unique_ptr<int> v = std::move(hang.front());                       // (5) luồng chính nhận chủ
        hang.pop();
        tong += *v;
        ++dem;
    }                                                                           // (6) v chết cuối mỗi vòng: số được xóa đúng một lần
    std::cout << "nhan " << dem << " viec, tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai là chủ |
|---|---|---|
| (1)(2) | Lambda tạo `p` riêng từ `p` ngoài; `p` ngoài thành `nullptr` | lambda (rồi luồng `t`) |
| (3) | Mỗi luồng sản xuất tạo số `k*1000+i` bằng `make_unique` | luồng sản xuất |
| (4) | `std::move(v)` đẩy vào hàng, trong khóa; `v` rỗng | hàng đợi |
| (5) | Sau `join`, luồng chính `move` phần tử ra khỏi `hang.front()` | luồng chính |
| (6) | `v` hết vòng: số được xóa đúng một lần | không ai |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, ASan sạch):

```text
luong nhan so 7
p ngoai con giu gi khong? 0
nhan 300 viec, tong = 315150
```

Tổng 315150 là 100 số của mỗi luồng (`k*1000+1` đến `k*1000+100`) cộng lại cho k = 0, 1, 2; mình tính lại bằng một chương trình khác, ra cùng số. **Thử thay đổi: viết `[p]` thay `[p = std::move(p)]`.** Mình đã chạy: lỗi biên dịch `use of deleted function 'std::unique_ptr<...>::unique_ptr(const std::unique_ptr<...>&)'`, đúng như [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) nói về chuyện không sao chép được. Với `g++ -std=c++11`, init-capture bị g++ cảnh báo `lambda capture initializers only available with '-std=c++14'`.

### 7. Chi phí, và khi nào KHÔNG nên dùng `shared_ptr` giữa các luồng

Mỗi lần sao chép hay hủy `shared_ptr` là một thao tác **nguyên tử** trên bảng đếm, đắt hơn hẳn một phép gán con trỏ thô, và các luồng cùng sao chép từ một đối tượng thì cùng ghi vào **một** bảng đếm. Mình đo riêng (chương trình không đưa vào bài cho gọn): bốn luồng, mỗi luồng gọi 300000 lần một hàm nhận `shared_ptr` **theo giá trị** (mỗi lần +1 rồi -1), so với một hàm nhận `const Cay&`. Biên dịch không tối ưu, năm lần liền ra khoảng `40000` so với `3600` micro giây, tức gấp cỡ 11 lần; máy bạn sẽ ra số khác. Với `-O2` mình thử thì vòng `const&` co lại gần như bằng không, nên tỉ lệ khi đó vô nghĩa: đừng chép con số này đi nói, chỉ nhớ **nguyên lý** (thêm hai thao tác nguyên tử mỗi lần truyền theo giá trị).

**Bảng chốt: tình huống nào chọn gì**

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Luồng chỉ dùng đối tượng trong lúc hàm gọi, chủ chắc chắn sống lâu hơn (có `join`) | Tham chiếu hoặc con trỏ thô, **không** `shared_ptr` | Chủ rõ ràng; khỏi tốn hai thao tác nguyên tử mỗi lần |
| Việc bất đồng bộ chỉ có nghĩa nếu chủ còn sống | Bắt `weak_ptr`, `lock()` rồi mới dùng | Chủ chết thì bỏ qua; callback không giữ chủ sống |
| Việc bất đồng bộ **phải** xong dù chủ đã đi | Bắt `shared_from_this()` theo giá trị | Giữ chủ sống tới khi xong |
| Luồng `detach` | Giữ bản sao `shared_ptr` hoặc dữ liệu, không `[&]` | Luồng sống lâu hơn hàm tạo ra nó |
| Một chủ rõ ràng, chuyển sang luồng khác | `unique_ptr` + `[p = std::move(p)]` hoặc hàng đợi | Một chủ mỗi lúc, không tốn bảng đếm |
| Nhiều luồng đọc, một luồng thay cả cấu hình | `shared_ptr<const T>` + mutex quanh con trỏ (hoặc `atomic_load`/`atomic_store`) | Đọc lấy bản chụp; đối tượng bất biến nên khỏi khóa |
| Nhiều luồng cùng sửa nội dung đối tượng | Mutex/atomic **bên trong** đối tượng | `shared_ptr` không lo tầng 2 |

**Khi nào KHÔNG nên dùng `shared_ptr` giữa các luồng:** khi chỉ có một chủ rõ ràng (dùng `unique_ptr`); khi truyền vào hàm chỉ để dùng tạm (truyền `const T&`); khi dùng nó như "cái khóa giá rẻ" vì tưởng đã thread-safe; và khi định dựa vào `use_count()` để ra quyết định (mục 🎤 giải thích vì sao sai).

## 💻 Ví dụ code

### Công bố cấu hình: `shared_ptr<const T>` cộng một mutex quanh con trỏ

Đây là bản sửa của mục 2. Lớp `HopCauHinh` đóng gói biến `shared_ptr` cùng mutex của nó, giống `BoDem` ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)): dữ liệu và khóa đi cùng nhau. `lay()` trả một **bản chụp** (một `shared_ptr` riêng); `dat()` thay con trỏ. Luồng đọc xong việc lấy bản chụp là nhả khóa ngay, rồi đọc `a`, `b` ở ngoài khóa vì đối tượng `const` không ai sửa.

```cpp
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>

struct CauHinh {
    int a, b;                                   // bất biến: luôn a == b
    CauHinh(int v) : a(v), b(v) {}
};

class HopCauHinh {                              // khóa đi theo biến shared_ptr
public:
    HopCauHinh() : p(std::make_shared<const CauHinh>(0)) {}
    std::shared_ptr<const CauHinh> lay() {
        std::lock_guard<std::mutex> giu(khoa);  // (1) khóa chỉ bọc việc sao chép con trỏ
        return p;
    }
    void dat(std::shared_ptr<const CauHinh> moi) {
        std::lock_guard<std::mutex> giu(khoa);  // (2) khóa bọc việc gán
        p = std::move(moi);
    }
private:
    std::mutex khoa;
    std::shared_ptr<const CauHinh> p;
};

int main() {
    HopCauHinh hop;
    long long khongNhatQuan = 0;
    std::thread ghi([&hop] {
        for (int v = 1; v <= 100000; ++v)
            hop.dat(std::make_shared<const CauHinh>(v));   // (3) cấp phát NGOÀI khóa
    });
    std::thread doc([&hop, &khongNhatQuan] {
        for (int i = 0; i < 100000; ++i) {
            std::shared_ptr<const CauHinh> s = hop.lay();  // (4) lấy một bản chụp
            if (s->a != s->b) ++khongNhatQuan;             // (5) dùng bản chụp, không cần khóa
        }
    });
    ghi.join();
    doc.join();
    std::cout << "khong nhat quan: " << khongNhatQuan << "\n";
    std::cout << "phien ban cuoi: " << hop.lay()->a << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai đang giữ thẻ nào |
|---|---|---|
| (3) | Luồng ghi tạo cấu hình mới **trước** khi xin khóa, rồi `dat()` đổi con trỏ trong khóa | `p` trỏ bản mới; bản cũ còn sống nếu có bản chụp |
| (1)(4) | Luồng đọc xin khóa, sao chép `p` ra `s`, nhả khóa | `s` giữ bản cấu hình **đúng tại lúc chụp** |
| (5) | Đọc `s->a`, `s->b` ở ngoài khóa; luồng ghi có đổi `p` cũng không đụng bản `s` đang cầm | bản của `s` không ai sửa, nên `a == b` |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
khong nhat quan: 0
phien ban cuoi: 100000
```

Luồng đọc luôn thấy một cấu hình **trọn vẹn** (một phiên bản, không nửa cũ nửa mới), và bản cũ tự bị hủy khi bản chụp cuối cùng của nó chết. Đó là **copy-on-write** (sao chép khi ghi): không sửa bản cũ, tạo bản mới rồi đổi con trỏ. Bài 61 sẽ xếp mẫu này vào nhóm "bất biến".

### Callback an toàn: bắt `weak_ptr` hay giữ chủ sống

Bản sửa của mục 5. `henNhin` dùng `weak_from_this()`; `henGiu` dùng `shared_from_this()`. `main` chạy cả hai tình huống "chủ bị hủy trước khi callback chạy", và hàm hủy in `~ManHinh` để ta thấy **khi nào** nó chạy.

```cpp
#include <future>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

struct ManHinh : std::enable_shared_from_this<ManHinh> {
    std::string ten = "man hinh chinh";
    ~ManHinh() { std::cout << "  ~ManHinh\n"; }

    // Cách 1: callback chỉ "nhìn" chủ (weak_ptr); chủ chết thì bỏ qua.
    std::thread henNhin(std::future<void> cho) {
        std::weak_ptr<ManHinh> yeu = weak_from_this();            // (1) C++17
        return std::thread([yeu](std::future<void> f) {
            f.wait();
            if (std::shared_ptr<ManHinh> sp = yeu.lock())         // (2) còn sống thì lấy thẻ
                std::cout << "  [nhin] dung ten: " << sp->ten << "\n";
            else
                std::cout << "  [nhin] chu da chet, bo qua\n";
        }, std::move(cho));
    }

    // Cách 2: callback GIỮ chủ sống (shared_ptr) cho tới khi chạy xong.
    std::thread henGiu(std::future<void> cho) {
        std::shared_ptr<ManHinh> tuMinh = shared_from_this();     // (3) lambda sở hữu một thẻ
        return std::thread([tuMinh](std::future<void> f) {
            f.wait();
            std::cout << "  [giu] dung ten: " << tuMinh->ten << "\n";
        }, std::move(cho));
    }
};

int main() {
    std::cout << "Cach 1: henNhin, chu bi huy truoc callback\n";
    {
        auto m = std::make_shared<ManHinh>();
        std::promise<void> tin;
        std::thread t = m->henNhin(tin.get_future());
        m.reset();                                               // (4) thẻ cuối của main: ~ManHinh chạy NGAY
        tin.set_value();
        t.join();
    }
    std::cout << "Cach 2: henGiu, chu bi huy truoc callback\n";
    {
        auto m = std::make_shared<ManHinh>();
        std::promise<void> tin;
        std::thread t = m->henGiu(tin.get_future());
        m.reset();                                               // (5) main nhả thẻ, nhưng lambda còn một thẻ
        std::cout << "  main da reset, chua huy\n";
        tin.set_value();
        t.join();
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng đếm lúc này |
|---|---|---|
| (1)(2) | Lambda cầm `weak_ptr`; sau này `lock()` quyết định còn hay chết | không tăng |
| (4) | `m` là thẻ duy nhất: `reset()` đưa bảng về 0, `~ManHinh` in ngay; callback sau đó thấy rỗng | 0 |
| (3) | Lambda của `henGiu` cầm một thẻ thật | 2 (main và lambda) |
| (5) | `m.reset()` chỉ trả thẻ của main; `~ManHinh` **chưa** chạy | 1 (lambda) |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, ASan sạch):

```text
Cach 1: henNhin, chu bi huy truoc callback
  ~ManHinh
  [nhin] chu da chet, bo qua
Cach 2: henGiu, chu bi huy truoc callback
  main da reset, chua huy
  [giu] dung ten: man hinh chinh
  ~ManHinh
```

Ở cách 2 `~ManHinh` in **sau** dòng của callback: lambda là thẻ cuối, nó bị hủy khi luồng nền chạy xong, nên hàm hủy chạy ở luồng nền chứ không ở `main`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`shared_ptr` có thread-safe không?"
    Trả lời cả hai nửa. Bộ đếm trong khối điều khiển được cập nhật nguyên tử, nên nhiều luồng sao chép và hủy các `shared_ptr` cùng trỏ một đối tượng thì bộ đếm vẫn đúng, đối tượng hủy đúng một lần. Nhưng đối tượng được trỏ tới thì không tự an toàn: hai luồng cùng sửa nội dung nó là data race, cần mutex hoặc atomic trong đối tượng. Và chính biến `shared_ptr` cũng không an toàn nếu có luồng ghi (gán, `reset`, `swap`) trong lúc luồng khác đọc hay ghi cùng biến đó. Câu trả lời một chữ "có" hoặc "không" đều là câu trả lời thiếu.
    **Nối tiếp: "Thế hai luồng cùng gán lại một `shared_ptr` toàn cục thì sao, sửa thế nào?"** Là data race trên biến (hai con trỏ bị đổi không nguyên tử), mình đã chạy ra `pure virtual method called` và lỗi phân đoạn. Sửa bằng mutex bọc việc sao chép và gán, hoặc `std::atomic_load`/`atomic_store`, hoặc `std::atomic<std::shared_ptr<T>>` (C++20); mỗi luồng giữ bản chụp riêng.

??? question "Làm sao cho nhiều luồng đọc một cấu hình, mà vẫn thay được cấu hình mới khi đang chạy?"
    Làm cấu hình bất biến: `shared_ptr<const CauHinh>`. Luồng ghi tạo bản mới rồi đổi con trỏ dưới một mutex nhỏ (hoặc bằng `atomic_store`); luồng đọc xin khóa chỉ để sao chép con trỏ ra một bản chụp, nhả khóa, rồi đọc thoải mái ngoài khóa. Bản cũ tự hủy khi bản chụp cuối của nó chết. Đọc không phải chờ ai trong lúc dùng, và không bao giờ thấy cấu hình nửa cũ nửa mới.
    **Nối tiếp: "Sao không bọc mutex quanh cả cấu hình?"** Giữ khóa suốt lúc đọc thì ghi chờ đọc và đọc chờ nhau; bản chụp bất biến giữ vùng găng chỉ còn một lệnh sao chép con trỏ.

??? question "`enable_shared_from_this` để làm gì? Sao không viết `shared_ptr<T>(this)`?"
    Khi một hàm thành viên cần đưa ra một `shared_ptr` tới chính đối tượng. `shared_ptr<T>(this)` dựng bảng đếm mới độc lập với các thẻ có sẵn, nên đối tượng bị hai bảng cùng đòi dọn: double free (mình chạy ra mã 134). `enable_shared_from_this` nhớ sẵn bảng đếm gốc, và `shared_from_this()` đưa ra thẻ cùng bảng đó.
    **Nối tiếp: "Gọi `shared_from_this()` trong hàm tạo được không? Với đối tượng trên stack?"** Không cả hai: đối tượng chưa/không nằm trong `shared_ptr` nào nên C++17 ném `std::bad_weak_ptr` (mình chạy: bắt được, hoặc không bắt thì `terminate`).

??? question "Callback bất đồng bộ bắt `this` có vấn đề gì? Sửa bằng `weak_ptr` hay `shared_ptr`?"
    Lambda cầm con trỏ thô; đối tượng có thể bị hủy trước khi callback chạy, thành use-after-free (ASan báo; không sanitizer thì có thể vẫn chạy ra đúng, và đó là hành vi không xác định). Chọn theo ý nghĩa: nếu việc chỉ có ý nghĩa khi chủ còn sống thì bắt `weak_ptr`, `lock()` rồi mới dùng, chủ chết thì bỏ qua. Nếu việc **phải** hoàn thành thì bắt `shared_from_this()`, đổi lại chủ sống tới khi callback xong và hàm hủy có thể chạy ở luồng khác.
    **Nối tiếp: "Mẫu `if (!w.expired()) w.lock()->dung()` sai ở đâu?"** Giữa `expired()` và `lock()` luồng khác có thể trả thẻ cuối, `lock()` ra rỗng và `->` gọi trên con trỏ rỗng; phải `if (auto sp = w.lock()) { ... }`.

??? question "Có dùng `use_count() == 1` để quyết định mình là người cuối cùng không?"
    Không. Trong đa luồng `use_count()` chỉ là ước lượng tại một thời điểm: giữa lúc đọc ra `1` và lúc hành động, luồng khác có thể sao chép hoặc trả thẻ, nên đây là lỗi kiểm-rồi-làm (race condition, [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Muốn biết đối tượng còn sống thì dùng `weak_ptr::lock()`, một bước nguyên tử.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tin rằng `shared_ptr` đã bảo vệ cả đối tượng"
    Bộ đếm đúng không có nghĩa nội dung đối tượng an toàn (mình chạy: `use_count` vẫn là 1 mà `dem` ra thiếu, TSan báo). Đối tượng bị nhiều luồng sửa phải có mutex/atomic của riêng nó, hoặc phải là `const`.

!!! warning "Lỗi 2: Gán lại một `shared_ptr` chung mà không khóa"
    Hai con trỏ trong biến bị đổi không nguyên tử, luồng đọc có thể thấy nửa cũ nửa mới (mình chạy: `pure virtual method called`, lỗi phân đoạn). Dùng mutex, hoặc `atomic_load`/`atomic_store`.

!!! warning "Lỗi 3: Bắt `this` hoặc `[&]` trong callback chạy về sau"
    Đối tượng hay biến cục bộ có thể đã chết khi callback chạy. Chạy ra đúng chỉ là may; ASan mới chỉ ra lỗi. Bắt `weak_ptr` hoặc `shared_ptr` **theo giá trị**; nhớ `shared_from_this()` đòi đối tượng đã nằm trong `shared_ptr`, và đừng bao giờ viết `shared_ptr<T>(this)`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="52" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Câu nào mô tả đúng nhất độ an toàn đa luồng của `std::shared_ptr`?

- Mọi thứ đều an toàn: bộ đếm, đối tượng được trỏ tới và biến `shared_ptr`
- Chỉ bộ đếm an toàn, các luồng không nên sao chép `shared_ptr` cho nhau
- Bộ đếm an toàn; đối tượng và biến bị ghi đồng thời thì phải tự bảo vệ
- Không có gì an toàn, vì bộ đếm cũng là một vùng nhớ chung giữa các luồng

<p class="giai-thich" markdown>Bộ đếm được cập nhật bằng thao tác nguyên tử, nên sao chép và hủy `shared_ptr` giữa các luồng vẫn giữ đếm đúng. Còn nội dung đối tượng thì `shared_ptr` không hề bảo vệ, và chính biến `shared_ptr` bị gán đồng thời với một lần đọc là data race. Nói "mọi thứ an toàn" bỏ qua hai tầng đó. Nói "không nên sao chép" thì ngược, vì sao chép giữa các luồng chính là việc bộ đếm nguyên tử cho phép. Nói "không có gì an toàn" sai ở chỗ bộ đếm là nguyên tử, không phải vùng nhớ cần khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. `hienTai` là biến toàn cục `shared_ptr<const CauHinh>`, không có mutex hay atomic nào. Điều gì đúng?

```text
// Luồng A, lặp nhiều lần:
hienTai = std::make_shared<const CauHinh>(v);
// Luồng B, lặp nhiều lần:
std::shared_ptr<const CauHinh> s = hienTai;
```

- Data race trên biến `hienTai`, dù bộ đếm nguyên tử; chương trình có thể sập
- Không có lỗi, vì bộ đếm của `shared_ptr` là nguyên tử nên đoạn này an toàn
- Không có lỗi, vì `CauHinh` là `const` nên luồng nào đọc cũng thấy bản đúng
- Chỉ có lỗi logic (đọc bản cũ), không có data race, vì mỗi lệnh là một dòng

<p class="giai-thich" markdown>Luồng A **ghi** biến `hienTai` (đổi cả con trỏ đối tượng lẫn con trỏ bảng đếm) trong lúc luồng B **đọc** cùng biến, không có đồng bộ: đó là data race, hành vi không xác định (mình chạy ra `pure virtual method called`, lỗi phân đoạn). Bộ đếm nguyên tử chỉ lo tầng bộ đếm, không lo chính biến. `const` của đối tượng chỉ cấm sửa nội dung, không giúp việc đọc một biến đang bị đổi. Còn "một dòng" không có nghĩa nguyên tử: sao chép `shared_ptr` là nhiều bước.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Một luồng nền cập nhật nhãn của một màn hình. Màn hình có thể bị đóng bất cứ lúc nào, và nếu đã đóng thì việc cập nhật vô nghĩa, bỏ qua được. Màn hình đã nằm trong `shared_ptr`. Lambda của luồng nền nên làm gì?

- Bắt `this` theo giá trị, vì màn hình chắc chắn còn khi luồng nền chạy
- Bắt `shared_from_this()`, để màn hình luôn sống cho tới khi cập nhật xong
- Bắt `[&]` biến màn hình, vì `shared_ptr` đã bảo vệ nó khỏi bị hủy sớm
- Bắt `weak_ptr`, rồi `lock()` khi chạy: có thẻ thì cập nhật, rỗng thì bỏ qua

<p class="giai-thich" markdown>Đề nói việc chỉ có nghĩa khi màn hình còn sống và bỏ qua được, đúng chỗ của `weak_ptr` cộng `lock()`: callback không kéo dài đời màn hình, và kiểm tra rỗng chính là chữ "bỏ qua". Bắt `shared_from_this()` giữ màn hình "đóng rồi mà vẫn sống" chỉ để cập nhật một cái nhãn không ai thấy. Bắt `this` chỉ cầm con trỏ thô, không có gì bảo đảm màn hình còn khi lambda chạy. `[&]` thì cầm tham chiếu tới biến cục bộ, và biến `shared_ptr` bị bắt theo tham chiếu không giữ đối tượng sống.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. `Nut` không kế thừa `enable_shared_from_this`. Chuyện gì xảy ra khi `main` kết thúc?

```text
struct Nut {
    std::shared_ptr<Nut> layChinhMinh() { return std::shared_ptr<Nut>(this); }
};
auto n = std::make_shared<Nut>();
auto khac = n->layChinhMinh();
```

- `use_count` của `n` thành 2, vì `khac` và `n` cùng trỏ một `Nut`
- Có hai bảng đếm cùng cho mình là chủ duy nhất, nên `Nut` bị trả hai lần
- Chương trình chạy bình thường, vì `shared_ptr` biết hai thẻ cùng một địa chỉ
- Không biên dịch được, vì không thể dựng `shared_ptr` từ `this`

<p class="giai-thich" markdown>`shared_ptr<Nut>(this)` dựng một bảng đếm **mới** bắt đầu từ 1, không liên quan bảng của `n`. Hai bảng, mỗi bảng tưởng mình giữ đối tượng một mình, nên cả hai đều cố hủy `Nut` ở cuối `main`: double free (mình chạy: mã 134). `use_count` thành 2 chỉ đúng khi dùng `shared_from_this()`. `shared_ptr` không so địa chỉ giữa các bảng đếm với nhau. Còn dựng được thì vẫn biên dịch bình thường, lỗi nằm ở lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Bạn viết một đối tượng `BaoCao`. Khi đối tượng nhận được dữ liệu, nó giao cho luồng nền việc **ghi nốt kết quả ra tệp**; việc này phải xong dù người dùng đã đóng và hủy `BaoCao` ngay sau đó. `BaoCao` nằm trong `shared_ptr`. Nên bắt gì vào lambda của luồng nền?

- `shared_from_this()` theo giá trị, để `BaoCao` sống tới khi ghi xong
- Một `weak_ptr` lấy từ `weak_from_this()`, rồi bỏ qua nếu `lock()` ra rỗng
- `this` theo giá trị, vì lambda chạy sau cũng vẫn dùng được `this`
- Một tham chiếu `[&]` tới biến `shared_ptr` đang giữ `BaoCao`

<p class="giai-thich" markdown>Việc phải xong dù chủ đã đi nghĩa là callback cần **giữ chủ sống**: bắt một `shared_ptr` thật bằng `shared_from_this()`, và hàm hủy sẽ chạy khi lambda xong. Nhánh `weak_ptr` sẽ thấy chủ chết và **bỏ qua**, tức là mất dữ liệu cần ghi. `this` là con trỏ thô nên không giữ gì. Tham chiếu `[&]` tới biến cục bộ cũng không giữ đối tượng sống và còn có thể trỏ vào biến đã chết.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. `w` là `std::weak_ptr<Ban>`. Vì sao đoạn này sai trong chương trình đa luồng?

```text
if (!w.expired()) {
    w.lock()->dung();
}
```

- `expired()` luôn trả `true` khi có hơn một luồng, nên nhánh không bao giờ chạy
- `lock()` không gọi được trên `weak_ptr`, chỉ gọi được trên `shared_ptr`
- Thiếu `std::move`, nên `lock()` sao chép con trỏ và làm tăng đếm sai
- Luồng khác có thể trả thẻ cuối giữa hai lệnh, nên `lock()` ra con trỏ rỗng

<p class="giai-thich" markdown>Hai lệnh là hai bước rời nhau; luồng khác chen vào giữa và hủy đối tượng thì `lock()` trả `shared_ptr` rỗng, và `->` trên con trỏ rỗng là hành vi không xác định. Mẫu đúng là một bước duy nhất: `if (auto sp = w.lock()) { sp->dung(); }`, vì `lock()` kiểm và lấy thẻ nguyên tử, còn thẻ trong tay giữ đối tượng sống. `expired()` không luôn trả `true`, `lock()` là hàm của `weak_ptr`, và việc tăng đếm khi `lock()` là đúng ý, không cần `std::move`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Bạn có `std::unique_ptr<Viec> p` và muốn một luồng mới là chủ của nó từ giờ trở đi. Cách nào đúng?

- Lambda `[p] { ... }`, vì danh sách bắt chép `p` sang cho luồng
- Lambda `[p = std::move(p)] { ... }`, rồi truyền cho `std::thread`
- Lambda `[&p] { ... }`, vì tham chiếu giúp luồng giữ quyền sở hữu
- Chuyển `p` thành `shared_ptr` rồi bắt `[&]`, vì `unique_ptr` không qua luồng được

<p class="giai-thich" markdown>Init-capture `[p = std::move(p)]` tạo biến `p` mới trong lambda bằng cách chuyển quyền từ `p` ngoài, nên luồng là chủ và `p` ngoài thành rỗng. `[p]` cần sao chép, mà `unique_ptr` không sao chép được (lỗi biên dịch). `[&p]` chỉ mượn biến, không chuyển sở hữu, và biến có thể chết trước luồng. Còn `unique_ptr` qua luồng được bằng `std::move`, nên không cần đổi sang `shared_ptr` cho việc này.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `shared_ptr` có **ba tầng**: bộ đếm (nguyên tử, an toàn), đối tượng được trỏ tới (không tự an toàn, cần mutex/atomic của chính nó hoặc `const`), và biến `shared_ptr` (đọc đồng thời ổn, có luồng ghi thì data race). Mình chạy: `use_count` đúng vẫn không cứu được `dem` thiếu; gán đồng thời một biến chung cho ra `pure virtual method called` và lỗi phân đoạn.
2. Công bố cấu hình mới: `shared_ptr<const T>` cộng mutex quanh con trỏ (lớp `HopCauHinh`), luồng đọc lấy bản chụp rồi dùng ngoài khóa; hoặc `std::atomic_load`/`atomic_store`; `std::atomic<std::shared_ptr>` là C++20 (g++ 11.4 ở máy mình không biên dịch được).
3. `weak_ptr::lock()` là một bước nguyên tử: `if (auto sp = w.lock())`, không bao giờ `expired()` rồi `lock()`. Hàm hủy chạy ở luồng nhả **thẻ cuối**; đối số `std::thread` được sao chép nguyên kiểu nên truyền `shared_ptr` là đã giữ chủ sống.
4. `enable_shared_from_this` + `shared_from_this()` (đối tượng phải đã nằm trong `shared_ptr`, không gọi trong hàm tạo, nếu không `bad_weak_ptr`); không bao giờ `shared_ptr<T>(this)` (hai bảng đếm, double free). Callback bất đồng bộ không bắt `this` hay `[&]`: bắt `weak_ptr` ("chủ chết thì bỏ qua") hoặc `shared_ptr` ("giữ chủ sống tới khi xong"); luồng `detach` phải sở hữu thứ nó dùng.
5. `unique_ptr` qua luồng bằng `std::move` (đối số, init-capture `[p = std::move(p)]` của C++14, hoặc hàng đợi có khóa): mỗi lúc một chủ. `shared_ptr` đắt hơn mượn (mình đo: truyền theo giá trị chậm cỡ 11 lần so với `const&` ở `-O0`, số đổi theo máy), nên chỉ dùng khi thật sự nhiều chủ; Go có GC nên không có use-after-free kiểu này, nhưng `atomic.Pointer` ứng với `atomic_load`/`atomic_store`.
