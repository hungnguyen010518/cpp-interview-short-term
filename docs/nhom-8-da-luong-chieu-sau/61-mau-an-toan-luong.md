# Bài 61 — Mẫu thiết kế an toàn luồng: monitor, thread-local, bất biến, truyền thông điệp

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Hỏi đúng câu gốc trước khi nghĩ tới khóa: "dữ liệu này có thật sự phải chia sẻ và bị sửa từ nhiều luồng không?", rồi chọn một trong bốn mẫu bằng bảng quyết định, kèm **khi nào KHÔNG nên dùng** từng mẫu.
    - Viết lớp **monitor** (dữ liệu và khóa chung một lớp) cho đúng: không lộ tham chiếu, gói chuỗi kiểm-rồi-làm vào một hàm, và **không gọi callback khi đang giữ khóa** (chạy thật: hai khóa của hai lớp chờ nhau, chương trình treo, mã 124).
    - Công bố cấu hình bằng `shared_ptr<const T>` theo kiểu copy-on-write, hoán đổi con trỏ an toàn trong g++ 11 chuẩn C++17 (`std::atomic_load`/`atomic_store` hoặc mutex ngắn), và hiểu vì sao nhiều người ghi vẫn cần khóa ghi (TSan sạch mà vẫn mất cập nhật).
    - Giảm tranh chấp bằng cách **chia dữ liệu theo luồng rồi gộp** và **truyền thông điệp** (một luồng sở hữu trạng thái, "active object"); trả lời câu "thiết kế để giảm tranh chấp khóa" và nối với câu châm ngôn của Go.

**Bạn cần biết trước:** [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`, `lock_guard`, lớp `BoDem`, `thread_local`, TSan), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, thứ tự khóa, callback khi giữ khóa), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, hàng đợi producer-consumer), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic`), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (dòng cache, false sharing, `alignas`), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, `make_shared`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function`), [Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md) (`std::queue`). [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) đã chứng minh vì sao gán `shared_ptr` chung từ nhiều luồng là data race; bài này dùng kết quả đó.

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Đến giờ, mỗi lần có rắc rối ở thớt, bạn đều chữa bằng cách thêm thẻ khóa. Một bếp trưởng giỏi hỏi trước một câu: **"Có nhất thiết để nhiều đầu bếp cùng đụng vào thứ này không?"** Thường là không, và khi đó chẳng cần thẻ nào.

Bài này là bốn cách sắp xếp lại bếp để **ít phải khóa**, hoặc để khóa nằm đúng chỗ. **Monitor**: thớt chung đặt sau một quầy, đầu bếp chỉ được gọi món qua quầy, không tự thò tay. **Bất biến**: thực đơn dán tường, không ai sửa tờ cũ; muốn đổi thì in tờ mới rồi thay lên bảng. **Chia theo luồng**: mỗi đầu bếp một sổ ghi riêng, cuối ca cộng vào sổ tổng. **Truyền thông điệp**: một **băng chuyền**; đặt khay lên là hết quyền với khay, người ở đầu kia mới được đụng.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Thay tờ thực đơn là động tác của người; với máy, việc "thay con trỏ" phải được **làm cho nguyên tử** mới đúng (mục 3). Và băng chuyền thật chạy một hướng, còn hàng đợi trong code có thể có nhiều người gửi, nhiều người nhận.

## 📖 Giải thích

### 1. Bốn mẫu và cách chọn

Một data race cần ba thứ cùng lúc: **chia sẻ** một dữ liệu, **sửa** nó, và **không có đồng bộ**. Cả bốn mẫu đều bỏ đi một trong ba vế: không chia sẻ (mẫu 3), không sửa (mẫu 2), hoặc chỉ cho một nơi sửa tại một thời điểm (mẫu 1 và 4, hai cách xếp hàng khác nhau).

| Mẫu | Ý chính | Hợp khi | KHÔNG nên dùng khi | Chi phí chính |
|---|---|---|---|---|
| 1. Monitor | Dữ liệu + mutex trong một lớp, mọi hàm tự khóa | Trạng thái nhỏ, thao tác ngắn, nhiều hàm chung một bất biến | Thao tác dài (I/O, tính nặng); tranh chấp rất cao; phải chạy mã lạ trong khóa | Chờ khóa; nguy cơ deadlock |
| 2. Bất biến + copy-on-write | Không sửa bản cũ, tạo bản mới rồi đổi con trỏ | Đọc rất nhiều, ghi hiếm (cấu hình, bảng tra) | Dữ liệu lớn bị ghi liên tục | Mỗi lần ghi chép cả bản; đọc vẫn đụng bảng đếm |
| 3. Chia theo luồng, gộp cuối | Mỗi luồng giữ phần riêng, cộng lại khi xong | Đếm, cộng, thống kê chỉ cần kết quả cuối | Cần tổng chính xác ở mọi thời điểm; luồng khác phải thấy ngay | Bộ nhớ nhân số luồng; bước gộp |
| 4. Truyền thông điệp | Hàng đợi; mỗi dữ liệu chỉ một chủ tại một lúc | Trạng thái sống lâu, nhiều bước, cần thứ tự; tài nguyên chỉ một luồng được đụng | Việc cực nhỏ (chi phí hàng đợi lớn hơn việc); cần kết quả ngay | Hàng đợi, đánh thức, độ trễ |

Chọn theo thứ tự câu hỏi:

1. Mỗi luồng có làm được phần riêng rồi gộp sau không? Có: mẫu 3.
2. Dữ liệu có thể coi là không đổi sau khi tạo, và đổi thì thay cả bản? Có, và đọc nhiều hơn ghi: mẫu 2.
3. Việc sửa là vài lệnh ngắn, nhiều luồng gọi từ nhiều nơi? Có: mẫu 1 (monitor).
4. Việc sửa dài, nhiều bước, cần thứ tự, hoặc gắn với tài nguyên chỉ một luồng nên đụng? Có: mẫu 4.

### 2. Mẫu 1, monitor: khóa đi theo dữ liệu, và bốn luật

**Monitor** là cách gọi của lập trình đồng thời cho đúng thứ `BoDem` ở [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md): dữ liệu và mutex nằm trong một lớp, bên ngoài chỉ đi qua các hàm tự khóa. Lớp nhỏ thì dễ đúng. Lớp có nhiều hàm và nhiều bất biến cần thêm bốn luật:

1. Dữ liệu và mutex để `private`; mọi đường vào đều qua hàm tự khóa.
2. **Không lộ tham chiếu, con trỏ, iterator** vào dữ liệu bên trong: trả bản sao, hoặc đưa việc vào trong lớp ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) đã chạy bản hỏng).
3. **Chuỗi kiểm-rồi-làm gói thành một hàm** của lớp (`tangNeuBang0()`), vì hai hàm tự khóa nối nhau vẫn là race condition ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), `if (b.doc() == 0) b.tang();`).
4. **Không chạy mã mình không kiểm soát khi đang giữ khóa**: callback, hàm ảo, hàm của lớp khác.

Luật 4 là luật bị vi phạm nhiều nhất, vì nó không lộ ra khi đọc từng lớp. [Bài 26](../nhom-3-da-luong/26-deadlock.md) đã cho bản một luồng: callback xin lại đúng mutex đang giữ. Bản dưới đây khó thấy hơn: **hai lớp, mỗi lớp khóa đúng**, nhưng hai luồng đi qua hai lớp theo hai chiều ngược nhau. `HopThongBao` giữ `khoaHop` rồi gọi callback; callback xin `khoaNhatKy`. Luồng kia (`baoCao`) giữ `khoaNhatKy` rồi xin `khoaHop`.

```cpp
// bo-qua-kiem-tra
// Chỉ phần khác với Ví dụ 1 (mục 💻); các phần còn lại giống hệt.
// `HopThongBao::phat` là cách viết thân hàm `phat` của lớp `HopThongBao` ở ngoài thân lớp.
void HopThongBao::phat(int x) {
    std::lock_guard<std::mutex> giu(khoaHop);         // (1) giữ khoaHop
    for (auto& f : nguoiNghe) f(x);                   // (2) gọi callback KHI ĐANG GIỮ khoaHop
}
void NhatKy::ghi(int x) {                             // đây là callback
    std::lock_guard<std::mutex> giu(khoaNhatKy);      // (3) callback xin khoaNhatKy
    tong += x;
}
int NhatKy::baoCao(HopThongBao& hop) {
    std::lock_guard<std::mutex> giu(khoaNhatKy);      // (4) giữ khoaNhatKy
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    return hop.dem();                                 // (5) rồi xin khoaHop
}
```

**Chạy từng dòng** (mình dựng chương trình đầy đủ quanh ba hàm trên: luồng `b` gọi `baoCao`, 30 ms sau luồng `a` gọi `phat(1)`)

| Lúc | Luồng `b` | Luồng `a` | `khoaHop` / `khoaNhatKy` |
|---|---|---|---|
| 0 ms | `baoCao`: giữ `khoaNhatKy` (4), ngủ 100 ms | chưa tạo | `b` giữ khoaNhatKy |
| 30 ms | đang ngủ | `phat`: giữ `khoaHop` (1), gọi callback (2), callback xin `khoaNhatKy` (3): **chờ** `b` | `a` giữ khoaHop, `b` giữ khoaNhatKy |
| 100 ms | thức dậy, xin `khoaHop` (5): **chờ** `a` | chờ `b` | hai bên chờ nhau mãi |

Mình biên dịch sạch (`-Wall`) và chạy bản đầy đủ đó với `timeout 3` năm lần: lần nào cũng **không in gì** và `timeout` thoát mã **124**. Cả hai lớp đều "đúng" nếu xét riêng; lỗi nằm ở thứ tự khóa bị chia qua ranh giới hai lớp, đúng nguyên nhân deadlock cổ điển của [Bài 26](../nhom-3-da-luong/26-deadlock.md). Bản sửa (Ví dụ 1 ở mục 💻): **sao chép danh sách người nghe trong khóa, nhả khóa, rồi mới gọi**.

Cái giá của bản sửa có hai phần. Mỗi lần phát phải sao chép cả danh sách. Và callback có thể chạy sau khi người nghe đã hủy đăng ký, nên người nghe phải chịu được "thông báo muộn" (Bài 73 xử lý bằng `weak_ptr`).

**Khóa thô hay khóa mịn?** Khóa thô là một mutex cho cả cấu trúc; khóa mịn là nhiều mutex, mỗi cái một phần.

| | Khóa thô (một mutex) | Khóa mịn (nhiều mutex) |
|---|---|---|
| Song song | Thấp hơn: mọi thao tác xếp hàng | Cao hơn nếu các thao tác đụng phần khác nhau |
| Dễ đúng | Dễ: một khóa, một bất biến | Khó: thêm thứ tự khóa, deadlock ([Bài 26](../nhom-3-da-luong/26-deadlock.md)); bất biến vắt qua nhiều phần |
| Khi chọn | Mặc định, bắt đầu từ đây | Chỉ khi đã **đo** thấy khóa thô là nút thắt |

Đường giữa an toàn nhất là **chia shard** ([Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md), Bài 72): N phần độc lập, mỗi thao tác chỉ đụng đúng một khóa nên không có thứ tự khóa để sai.

### 3. Mẫu 2, bất biến và copy-on-write: công bố cả bản mới

Nếu một đối tượng **không bao giờ đổi sau khi tạo** (**bất biến** theo nghĩa immutable, khác "bất biến của lớp" ở [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) là điều luôn phải đúng), nhiều luồng đọc nó mà không cần khóa gì (chỉ đọc không phải data race). Muốn "đổi" thì tạo **đối tượng mới** rồi cho mọi người dùng bản mới. Đó là **copy-on-write** (sao chép khi ghi). Dùng `shared_ptr<const CauHinh>`: `shared_ptr<const T>` là con trỏ tới `T` chỉ đọc, nên trình biên dịch cấm sửa nhầm; `shared_ptr` giữ bản cũ sống cho tới khi người đọc cuối cùng nhả.

Chỗ khó duy nhất là **đổi con trỏ**: [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) đã chạy, một luồng gán và một luồng sao chép cùng biến `shared_ptr` là data race (chết mã 134, 139). Trong g++ 11 với `-std=c++17` có hai cách đúng: **mutex ngắn** quanh việc sao chép và việc gán ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) có lớp `HopCauHinh`), hoặc `std::atomic_load(&p)` và `std::atomic_store(&p, moi)` (C++11, trong `<memory>`, nhận **địa chỉ** biến). Từ C++20 chuẩn thêm `std::atomic<std::shared_ptr<T>>` và coi hai hàm trên là lỗi thời (deprecated: còn dùng được nhưng khuyên bỏ; g++ 11 chưa cảnh báo, trình biên dịch mới hơn có thể cảnh báo); g++ 11 chưa biên dịch được kiểu mới ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)). Mình chạy `std::atomic_is_lock_free(&p)` trên máy này: **`false`**, nên bên dưới có khóa nội bộ (chuẩn không bắt "nguyên tử" là không khóa).

Phần cần để ý là **người ghi**. `atomic_load` và `atomic_store` mỗi cái nguyên tử, nhưng chuỗi "đọc bản cũ, sao chép, sửa, ghi bản mới" thì **không**. Hai người ghi cùng đọc một bản cũ rồi cùng ghi, một bản mới đè bản kia và **mất một cập nhật**. Vì mỗi lệnh đều nguyên tử, đây là race condition chứ không phải data race, nên **TSan không báo**. Cách đơn giản: một mutex chỉ để các người ghi xếp hàng; người đọc không bao giờ đụng nó.

```cpp
#include <atomic>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

struct CauHinh {                                      // sau khi tạo thì không ai sửa
    std::vector<std::string> mayChu;
    int phienBan = 0;                                 // bất biến: mayChu.size() == phienBan
};

class HopCauHinh {
public:
    HopCauHinh() : hienTai(std::make_shared<const CauHinh>()) {}
    std::shared_ptr<const CauHinh> chup() const {     // người ĐỌC: một bản chụp
        return std::atomic_load(&hienTai);            // (1) đọc con trỏ một cách nguyên tử
    }
    void themMayChu(const std::string& ten) {         // người GHI: copy-on-write
        std::lock_guard<std::mutex> giu(khoaGhi);     // (2) chỉ để các người ghi xếp hàng
        std::shared_ptr<const CauHinh> cu = std::atomic_load(&hienTai);
        CauHinh moi = *cu;                            // (3) sao chép bản cũ
        moi.mayChu.push_back(ten);                    // (4) sửa trên bản nháp
        ++moi.phienBan;
        std::atomic_store(&hienTai, std::make_shared<const CauHinh>(std::move(moi)));   // (5) công bố
    }

private:
    std::mutex khoaGhi;
    std::shared_ptr<const CauHinh> hienTai;           // luôn trỏ tới một CauHinh trọn vẹn
};

int main() {
    HopCauHinh hop;
    std::atomic<long long> viPham{0};                 // đếm số lần đọc thấy bất biến bị vỡ
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 2; ++k) {                     // hai luồng ghi, mỗi luồng thêm 500 máy chủ
        cacLuong.emplace_back([&hop] {
            for (int i = 0; i < 500; ++i) hop.themMayChu("may-chu");
        });
    }
    for (int k = 0; k < 4; ++k) {                     // bốn luồng đọc liên tục
        cacLuong.emplace_back([&hop, &viPham] {
            for (int i = 0; i < 20000; ++i) {
                std::shared_ptr<const CauHinh> s = hop.chup();         // (6) lấy bản chụp
                if (static_cast<int>(s->mayChu.size()) != s->phienBan) // (7) dùng ngoài mọi khóa
                    ++viPham;
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::shared_ptr<const CauHinh> cuoi = hop.chup();
    std::cout << "vi pham bat bien: " << viPham.load() << "\n";
    std::cout << "phien ban cuoi: " << cuoi->phienBan << ", so may chu: " << cuoi->mayChu.size() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Con trỏ `hienTai` lúc này |
|---|---|---|
| (1)(6) | Người đọc gọi `chup()`: `atomic_load` sao chép con trỏ ra `s`, đếm +1 | trỏ bản đang công bố |
| (7) | Đọc `s->mayChu`, `s->phienBan` ngoài mọi khóa; bản này không ai sửa nên khớp nhau | không đổi, hoặc đã trỏ bản mới (không ảnh hưởng `s`) |
| (2)(3)(4) | Người ghi giữ `khoaGhi`, sao chép bản cũ, sửa bản nháp | vẫn trỏ bản cũ |
| (5) | `atomic_store` đổi con trỏ sang bản mới; bản cũ chết khi người đọc cuối nhả | trỏ bản mới |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
vi pham bat bien: 0
phien ban cuoi: 1000, so may chu: 1000
```

Bốn luồng đọc 20000 lần mỗi luồng, hai luồng ghi, và không lần đọc nào thấy bản "nửa cũ nửa mới" (số máy chủ luôn bằng phiên bản).

**Thử thay đổi 1: xóa dòng (2) (`lock_guard` của người ghi).** Mình đã chạy: vẫn `vi pham bat bien: 0`, **TSan vẫn sạch**, nhưng `phien ban cuoi` ra `588`, `507`, `575`, `557`, `666`, `734` thay vì 1000 (máy bạn ra số khác, nhưng nhỏ hơn 1000). Người đọc vẫn luôn thấy bản trọn vẹn; cái hỏng là người ghi mất cập nhật.

**Thử thay đổi 2: thay khóa ghi bằng vòng `std::atomic_compare_exchange_weak(&hienTai, &cu, moi)`** (đổi con trỏ chỉ khi nó vẫn là bản `cu` đã đọc, nếu không thì `cu` được cập nhật và thử lại). Mình đã chạy: `phien ban cuoi: 1000` ba lần, TSan sạch; người ghi thua phải chép lại từ đầu.

**Khi nào KHÔNG nên dùng copy-on-write.** Mỗi lần ghi sao chép cả đối tượng. Mình đo trên máy này (`vector<int>` 100000 phần tử, 1000 lần ghi một phần tử): copy-on-write khoảng **200 µs** mỗi lần, ghi tại chỗ dưới mutex dưới **1 µs**, chênh vài trăm tới hơn nghìn lần tùy `-O`. Vậy nó chỉ hợp khi ghi hiếm. Người đọc cũng không "miễn phí": mỗi lần sao chép `shared_ptr` là cộng và trừ bộ đếm chung, nhiều lõi đọc cùng lúc sẽ tranh dòng cache của bộ đếm đó.

### 4. Mẫu 3, chia theo luồng rồi gộp cuối

Cách giảm tranh chấp triệt để nhất là **không tranh**: mỗi luồng cộng vào phần riêng của nó, và chỉ khi xong mới gộp. Ở [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md), hai biến sát nhau làm hai luồng giành dòng cache (false sharing), nên mỗi ô riêng được đặt trên **một dòng cache riêng** bằng `alignas(64)`. Có hai cách viết:

- **Cách A, mảng ô riêng**: luồng `k` chỉ ghi ô `k`; luồng chính cộng các ô sau `join`.
- **Cách B, `thread_local`** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)): mỗi luồng một bản biến, hợp khi chỗ ghi nằm sâu trong các hàm gọi nhau. Mỗi luồng khóa **một lần** khi sắp kết thúc để cộng bản riêng vào tổng chung.

```cpp
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

struct alignas(64) OBiet {                            // (1) mỗi ô chiếm riêng một dòng cache
    long long v = 0;
};

thread_local long long rieng = 0;                     // (2) mỗi luồng một bản riêng
std::mutex khoa;
long long tongChung = 0;

void ghiNhan() { ++rieng; }                           // (3) hàm gọi ở sâu trong code, không biết khóa là gì

int main() {
    // Cách A: mỗi luồng một ô trong mảng, gộp sau join
    std::vector<OBiet> o(4);
    std::vector<std::thread> a;
    for (int k = 0; k < 4; ++k) {
        a.emplace_back([&o, k] {
            for (int i = 0; i < 100000; ++i) ++o[k].v;     // (4) luồng k chỉ ghi ô k
        });
    }
    for (std::thread& t : a) t.join();
    long long tongA = 0;
    for (const OBiet& x : o) tongA += x.v;                 // (5) gộp ở luồng chính, đã join nên an toàn
    std::cout << "cach A: " << tongA << "\n";
    // Cách B: thread_local, mỗi luồng gộp MỘT lần khi sắp kết thúc
    std::vector<std::thread> b;
    for (int k = 0; k < 4; ++k) {
        b.emplace_back([] {
            for (int i = 0; i < 100000; ++i) ghiNhan();    // (6) không khóa, không tranh chấp
            std::lock_guard<std::mutex> giu(khoa);         // (7) một lần khóa cho cả 100000 lần đếm
            tongChung += rieng;
        });
    }
    for (std::thread& t : b) t.join();
    std::cout << "cach B: " << tongChung << "\n";
    std::cout << "ban rieng cua luong chinh: " << rieng << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu lúc này |
|---|---|---|
| (1) | `alignas(64)`: mỗi `OBiet` chiếm đúng một dòng cache (mình in `sizeof` và `alignof`: đều 64) | `o[0]`, `o[1]`... ở các dòng khác nhau |
| (4) | Luồng `k` tăng `o[k].v`; không luồng nào đụng ô của luồng khác nên không cần khóa | mỗi ô 100000 |
| (5) | Sau `join`, luồng chính cộng bốn ô: `join` bảo đảm thấy giá trị cuối | tổng 400000 |
| (6) | `ghiNhan()` tăng `rieng`: mỗi luồng thấy bản của chính nó | mỗi bản `rieng` 100000 |
| (7) | Mỗi luồng khóa một lần cộng bản riêng vào `tongChung` | 400000; bản `rieng` của luồng chính vẫn 0 |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
cach A: 400000
cach B: 400000
ban rieng cua luong chinh: 0
```

Về tốc độ, mình đo riêng (4 luồng, mỗi luồng 5 triệu lần `fetch_add` trên một `atomic` chung, so với tăng ô riêng, `-O0`): atomic chung chậm hơn khoảng **8 đến 9 lần** trong ba lần chạy, đổi theo máy. Với `-O2` trình biên dịch gộp vòng ô riêng thành một phép cộng nên phép so mất công bằng.

**Khi nào KHÔNG nên dùng.** Khi cần **tổng chính xác ở mọi thời điểm** hoặc luồng khác phải thấy ngay giá trị mới: chỉ có tổng sau khi các luồng xong. Mẫu này hợp với thống kê, không hợp với bộ đếm "còn lại bao nhiêu chỗ".

### 5. Mẫu 4, truyền thông điệp và active object

Ý tưởng: đừng cho nhiều luồng đụng cùng dữ liệu, mà **trao dữ liệu đi**. Hàng đợi giữa các luồng ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)) là băng chuyền: người gửi dựng khay (một `std::vector<int>`), đặt lên hàng đợi bằng `std::move`, và **từ đó không đụng lại**; người nhận lấy ra rồi mới đụng. Mỗi dữ liệu chỉ có **một chủ tại một thời điểm**, nên nội dung khay không cần khóa; mutex chỉ nằm ở hàng đợi, và nó cũng cho thứ tự bảo đảm (người gửi viết xong trước khi nhả khóa, người nhận thấy sau khi lấy khóa).

**Active object** (đối tượng chủ động) là dạng gọn: **một luồng nền sở hữu trạng thái**, mọi luồng khác chỉ **gửi thông điệp** cho nó. Luồng nền xử lý tuần tự từng thông điệp, nên trạng thái của nó **không cần mutex**. Hợp khi trạng thái sống lâu, nhiều bước, hoặc gắn với thứ chỉ nên một luồng đụng (kết nối thiết bị, tệp nhật ký). Không hợp khi việc nhỏ hơn chi phí của hàng đợi, hay người gọi cần kết quả ngay.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <utility>
#include <vector>

class TongTheoLo {                                    // "active object": một luồng nền sở hữu trạng thái
public:
    TongTheoLo() : tho([this] { chay(); }) {}         // (1) luồng nền khởi động cùng đối tượng
    ~TongTheoLo() { dong(); }
    void gui(std::vector<int> lo) {                   // (2) người gửi TRAO CẢ LÔ đi
        {
            std::lock_guard<std::mutex> giu(khoa);
            hang.push(std::move(lo));                 // (3) lô chuyển vào hàng đợi, người gửi hết quyền
        }
        cv.notify_one();
    }
    long long ketThuc() {                             // dừng sạch rồi mới đọc kết quả
        dong();
        return tong;                                  // (4) sau join: luồng nền đã xong, đọc an toàn
    }

private:
    void dong() {
        {
            std::lock_guard<std::mutex> giu(khoa);
            xong = true;
        }
        cv.notify_all();
        if (tho.joinable()) tho.join();
    }
    void chay() {                                     // chạy ở luồng nền, tuần tự từng lô
        while (true) {
            std::vector<int> lo;
            {
                std::unique_lock<std::mutex> lk(khoa);
                cv.wait(lk, [this] { return xong || !hang.empty(); });
                if (hang.empty()) return;             // đã đóng và hết việc
                lo = std::move(hang.front());         // (5) lô chuyển sang luồng nền
                hang.pop();
            }
            for (int x : lo) tong += x;               // (6) tong chỉ luồng nền đụng: KHÔNG khóa
        }
    }
    std::mutex khoa;                                  // chỉ bảo vệ hang và xong
    std::condition_variable cv;
    std::queue<std::vector<int>> hang;
    bool xong = false;
    long long tong = 0;                               // thuộc riêng luồng nền
    std::thread tho;                                  // khai báo CUỐI: mọi thành viên trên đã dựng xong
};

int main() {
    TongTheoLo bo;
    std::vector<std::thread> nguoiGui;
    for (int k = 0; k < 3; ++k) {
        nguoiGui.emplace_back([&bo] {
            for (int j = 0; j < 10; ++j) {
                std::vector<int> lo;
                for (int x = 1; x <= 100; ++x) lo.push_back(x);   // người gửi tự dựng lô
                bo.gui(std::move(lo));                            // rồi trao đi, không đụng lại
            }
        });
    }
    for (std::thread& t : nguoiGui) t.join();
    std::cout << "tong = " << bo.ketThuc() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai đụng gì |
|---|---|---|
| (1) | Hàm tạo khởi động luồng nền chạy `chay()`. Vì thành viên dựng theo thứ tự khai báo, `tho` phải khai báo **cuối** để `khoa`, `hang`... đã tồn tại | luồng nền bắt đầu chờ ở `cv.wait` |
| (2)(3) | Người gửi khóa, đẩy cả lô vào hàng đợi bằng `std::move`, nhả khóa, đánh thức | lô thuộc về hàng đợi |
| (5) | Luồng nền khóa, `std::move` lô ra, `pop`, nhả khóa | lô thuộc về luồng nền |
| (6) | Cộng các phần tử vào `tong` mà không khóa: chỉ luồng nền đụng `tong` | `tong` thuộc luồng nền |
| (4) | `ketThuc()` đặt `xong`, `join` luồng nền, rồi đọc `tong` | sau `join`, luồng chính là chủ |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, ASan và UBSan sạch):

```text
tong = 151500
```

Ba người gửi, mỗi người 10 lô, mỗi lô 1 đến 100 (tổng 5050): 3 x 10 x 5050 = 151500. Thứ tự các lô đến nơi đổi theo lần chạy, nhưng phép cộng thì không phụ thuộc thứ tự.

!!! info "Bạn biết Go?"
    Châm ngôn của Go: "Đừng giao tiếp bằng cách chia sẻ bộ nhớ; hãy chia sẻ bộ nhớ bằng cách giao tiếp". Chính là mẫu 4: `chan []int` ứng với hàng đợi ở trên, goroutine nhận ứng với luồng nền, và `close(ch)` cộng `for lo := range ch` ứng với cờ `xong` cộng "hàng đợi rỗng thì thoát". C++ không có sẵn channel trong thư viện chuẩn; bạn tự ghép `queue` + `mutex` + `condition_variable` như trên.

    Mình viết bản Go của đúng chương trình (3 goroutine gửi mỗi cái 10 lô, một goroutine cộng), biên dịch với `go build -race` và chạy: `tong = 151500`, không báo gì (chạy thêm hai lần bản không `-race`: cùng kết quả). Đây là một lời khuyên chứ không phải luật: Go vẫn có `sync.Mutex`, và người viết Go vẫn dùng nó cho trạng thái đơn giản.

## 💻 Ví dụ code

### Ví dụ 1: gọi callback ngoài khóa

Bản sửa của chương trình treo ở mục 2: `phat` sao chép danh sách trong khóa rồi gọi các callback sau khi đã nhả. Cùng hai luồng, cùng độ trễ, nhưng lần này chạy xong.

```cpp
#include <chrono>
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class HopThongBao {
public:
    void dangKy(std::function<void(int)> f) {
        std::lock_guard<std::mutex> giu(khoaHop);
        nguoiNghe.push_back(std::move(f));
    }
    int dem() {
        std::lock_guard<std::mutex> giu(khoaHop);
        return static_cast<int>(nguoiNghe.size());
    }
    void phat(int x) {
        std::vector<std::function<void(int)>> ban;    // (1) bản sao danh sách
        {
            std::lock_guard<std::mutex> giu(khoaHop);
            ban = nguoiNghe;                          // (2) sao chép TRONG khóa
        }                                             // (3) nhả khóa
        for (auto& f : ban) f(x);                     // (4) gọi callback NGOÀI khóa
    }
private:
    std::mutex khoaHop;
    std::vector<std::function<void(int)>> nguoiNghe;
};

class NhatKy {
public:
    void ghi(int x) {
        std::lock_guard<std::mutex> giu(khoaNhatKy);
        tong += x;
    }
    int doc() {
        std::lock_guard<std::mutex> giu(khoaNhatKy);
        return tong;
    }
    int baoCao(HopThongBao& hop) {
        std::lock_guard<std::mutex> giu(khoaNhatKy);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return hop.dem();
    }
private:
    std::mutex khoaNhatKy;
    int tong = 0;
};

int main() {
    HopThongBao hop;
    NhatKy nk;
    hop.dangKy([&nk](int x) { nk.ghi(x); });
    int soNguoiNghe = 0;
    std::thread b([&] { soNguoiNghe = nk.baoCao(hop); });
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
    std::thread a([&] { hop.phat(1); });
    a.join();
    b.join();
    std::cout << "so nguoi nghe = " << soNguoiNghe << "\n";
    std::cout << "tong = " << nk.doc() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Khóa lúc này |
|---|---|---|
| (2)(3) | `a` giữ `khoaHop` chỉ đủ để chép danh sách sang `ban`, rồi nhả | `khoaHop` rảnh |
| (4) | `a` gọi callback: `ghi` xin `khoaNhatKy` và chờ `b` xong báo cáo | `a` không giữ khóa nào |
| sau 100 ms | `b` xin `khoaHop` (được, vì `a` đã nhả), trả `1`, nhả `khoaNhatKy`; `a` vào được `ghi` | không ai giữ hai khóa cùng lúc |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
so nguoi nghe = 1
tong = 1
```

Không luồng nào **giữ một khóa trong lúc xin khóa của lớp khác**, nên không có thứ tự khóa để sai.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Làm sao thiết kế để giảm tranh chấp khóa?"
    Đi từ rẻ tới đắt, và đo trước khi đổi. (1) Giảm dữ liệu chia sẻ: mỗi luồng giữ phần riêng (`thread_local`, ô riêng) rồi gộp cuối. (2) Rút ngắn vùng găng: việc nặng làm ngoài khóa ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). (3) Dữ liệu đọc nhiều, ghi ít thì làm bất biến và đổi cả bản bằng `shared_ptr<const T>`. (4) Chia shard để các khóa không giẫm nhau. (5) Đơn biến thì `atomic`. (6) Trạng thái dài hạn thì giao cho một luồng chủ và gửi thông điệp. Trước hết phải có số đo (đếm lần chờ khóa, `perf`), vì khóa thô đúng và đơn giản thường đã đủ.

??? question "Cấu hình đọc cực nhiều, thỉnh thoảng đổi: cập nhật mà không chặn người đọc thế nào? Thế nếu hai luồng cùng cập nhật thì sao?"
    Giữ cấu hình bất biến trong `shared_ptr<const CauHinh>`. Người đọc lấy một bản chụp (sao chép con trỏ bằng `atomic_load`, hoặc dưới một mutex ngắn) rồi dùng ngoài khóa. Người ghi sao chép bản cũ, sửa bản nháp, rồi `atomic_store`. Hai người ghi thì phải xếp hàng: một mutex chỉ cho người ghi, hoặc vòng `compare_exchange` thử lại; nếu không, một bản cập nhật mất mà TSan vẫn sạch (mình đã chạy ra 507 đến 734 thay vì 1000). Nếu ghi liên tục lên dữ liệu lớn thì không chọn mẫu này, vì mỗi lần ghi chép cả bản.

??? question "Vì sao không được gọi callback khi đang giữ khóa?"
    Vì bạn không biết callback làm gì. Nó có thể xin lại đúng khóa này (tự deadlock), hoặc xin khóa khác trong khi luồng khác giữ khóa đó và chờ khóa của bạn (deadlock hai khóa, mình đã chạy: treo, mã 124). Nó cũng có thể chạy lâu và chặn mọi người. Cách làm: trong khóa chỉ sao chép danh sách, nhả khóa rồi mới gọi. Cái giá: callback có thể chạy muộn so với lúc hủy đăng ký, nên người nghe phải chịu được điều đó.

??? question "Active object khác monitor chỗ nào, khi nào chọn cái nào?"
    Monitor: nhiều luồng cùng gọi hàm của đối tượng, mỗi hàm khóa rồi chạy ngay trong luồng gọi; kết quả có ngay, nhưng người gọi phải chờ khóa. Active object: luồng gọi chỉ **gửi thông điệp**, một luồng nền xử lý tuần tự, trạng thái của nó không cần khóa; người gọi không bị chặn khi gửi nhưng muốn kết quả phải dùng `future` hoặc gọi lại. Việc ngắn, cần kết quả ngay: monitor. Việc dài, nhiều bước, hoặc tài nguyên chỉ một luồng nên đụng: active object.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gọi callback, hàm ảo hay hàm lạ khi đang giữ khóa"
    Mỗi lớp khóa đúng, nhưng ghép lại thành hai khóa chờ nhau (mình đã chạy: treo, mã 124, lần nào cũng vậy). Trong khóa chỉ lấy dữ liệu ra, nhả khóa rồi mới gọi.

!!! warning "Lỗi 2: Tưởng `atomic_load` cộng `atomic_store` làm cả chuỗi đọc-sửa-ghi nguyên tử, hoặc tin TSan sạch là đúng"
    Mỗi hàm nguyên tử, cả chuỗi thì không: mất cập nhật mà TSan không báo (mình đã chạy: 507 đến 734 thay vì 1000). TSan chỉ bắt data race, không bắt race condition.

!!! warning "Lỗi 3: Gửi qua hàng đợi thứ mà bên gửi vẫn còn cầm, hoặc khai báo `std::thread` không phải thành viên cuối"
    Gửi `shared_ptr<vector<int>>` qua hàng đợi rồi vẫn sửa vector ở luồng gửi: hai chủ cùng đụng một vector, mutex của hàng đợi không bảo vệ nội dung. Mình đã chạy: ra `tong = 200` ba lần liền, nhưng TSan báo `data race` giữa đọc ở luồng nhận và ghi ở luồng chính. Chạy ra đúng không chứng minh gì. Còn với active object, luồng nền khởi động trong hàm tạo nên phải khai báo **cuối**, nếu không nó có thể chạy trước khi `khoa` hay `hang` được dựng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="61" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Một bảng cấu hình khoảng 5 MB được hàng chục luồng đọc hàng nghìn lần mỗi giây và chỉ đổi vài phút một lần, mỗi lần thay cả bảng. Muốn người đọc không bị chặn bởi việc cập nhật, nên chọn gì?

- Một `mutex` bọc cả bảng, người đọc khóa suốt lúc dùng
- Mỗi luồng giữ bản `thread_local` riêng và không bao giờ cập nhật
- `shared_ptr<const Bang>`: người ghi dựng bảng mới rồi đổi con trỏ
- Một `std::atomic<Bang>` để mọi thao tác thành nguyên tử

<p class="giai-thich" markdown>Dữ liệu đọc nhiều ghi hiếm và đổi cả bản đúng là chỗ của bất biến cộng copy-on-write: người đọc chụp con trỏ rồi dùng ngoài khóa, người ghi dựng bản mới. Một mutex bọc cả bảng làm mọi người đọc xếp hàng suốt lúc dùng. Bản `thread_local` riêng thì không bao giờ thấy cập nhật của luồng khác. `std::atomic<Bang>` với kiểu 5 MB không phải kiểu nhỏ mà phần cứng làm nguyên tử được, nên trở thành khóa ẩn và không giải quyết gì thêm.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Luồng X gọi `ds.phat(1)`, luồng Y gọi `nk.baoCao(ds)` cùng lúc. Chuyện gì có thể xảy ra?

```text
void DanhSach::phat(int x) { lock(khoaDS); for (f : nguoiNghe) f(x); }
void NhatKy::ghi(int x)    { lock(khoaNK); tong += x; }      // nguoiNghe chứa hàm gọi ghi
int  NhatKy::baoCao(DanhSach& ds) { lock(khoaNK); return ds.dem(); }   // dem() khóa khoaDS
```

- Deadlock: X giữ `khoaDS` chờ `khoaNK`, Y giữ `khoaNK` chờ `khoaDS`
- Không có vấn đề gì, vì mỗi hàm đều tự khóa mutex của lớp mình
- Data race trên `tong`, vì `ghi` và `baoCao` dùng hai mutex khác nhau
- Chỉ X bị chặn, vì `phat` luôn xin khóa trước nên thắng

<p class="giai-thich" markdown>Hai luồng khóa hai mutex theo hai thứ tự ngược nhau (qua callback ở X, qua `dem()` ở Y), đúng công thức deadlock hai khóa. Mỗi hàm khóa đúng không đủ, vì lỗi nằm ở thứ tự khóa bị chia qua hai lớp. `tong` luôn được bảo vệ bởi `khoaNK` ở mọi chỗ đụng tới nó, nên không có data race trên đó. Còn "xin trước thì thắng" không đúng: cả hai đã giữ một khóa và cùng chờ khóa kia.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Một dịch vụ chạy 16 luồng, mỗi luồng tăng bộ đếm "số yêu cầu đã xử lý" hàng triệu lần mỗi giây, còn người quản trị chỉ đọc tổng mỗi phút một lần. Muốn giảm tranh chấp nhiều nhất thì chọn gì?

- Một `mutex` bọc bộ đếm, vì mutex luôn đúng và dễ kiểm chứng
- Một `atomic` chung, vì atomic không bao giờ phải chờ nhau
- Gửi mỗi lần tăng qua hàng đợi cho một luồng chuyên đếm
- Mỗi luồng một ô riêng (dòng cache riêng), gộp khi cần đọc

<p class="giai-thich" markdown>Ghi cực dày mà đọc hiếm là chỗ hợp nhất cho chia theo luồng rồi gộp: mỗi luồng ghi ô riêng nên không có gì để tranh. Mutex đúng nhưng mọi lần tăng xếp hàng. Atomic chung cũng đúng, nhưng 16 lõi vẫn giành chung một dòng cache (mình đo với 4 luồng: khoảng 8 đến 9 lần chậm hơn ô riêng ở `-O0`), nên "không bao giờ tranh chấp" là sai. Hàng đợi cho mỗi lần tăng thì chi phí đánh thức và cấp phát lớn hơn chính việc cộng một số.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. `p` là `shared_ptr<const Dem>`, hai luồng cùng chạy hàm này 1000 lần, ban đầu `p->n` bằng 0, không có mutex nào khác. Sau khi cả hai xong, điều nào đúng?

```text
void tang() {
    auto cu  = std::atomic_load(&p);
    auto moi = std::make_shared<const Dem>(Dem{cu->n + 1});
    std::atomic_store(&p, moi);
}
```

- `p->n` luôn bằng 2000, vì `atomic_load` và `atomic_store` là nguyên tử
- `p->n` có thể nhỏ hơn 2000 mà TSan không báo gì, vì mất cập nhật
- Chương trình có data race trên `p`, nên TSan sẽ báo lỗi
- `p->n` có thể lớn hơn 2000, vì hai luồng cùng cộng lên bản cũ

<p class="giai-thich" markdown>Mỗi lệnh nguyên tử nhưng cả chuỗi đọc-tính-ghi thì không: hai luồng có thể cùng đọc `n = 5` rồi cùng ghi 6, mất một lần tăng. Không có truy cập thường nào vào `p`, nên không có data race và TSan không báo; đây là race condition. "Luôn 2000" nhầm nguyên tử từng lệnh với nguyên tử cả chuỗi. Còn lớn hơn 2000 thì không thể, vì mỗi bản mới chỉ là bản đã đọc cộng 1, nên mất cập nhật chỉ làm số nhỏ đi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Một thiết bị chỉ nhận lệnh tuần tự qua một kết nối, và 20 luồng khác nhau đều muốn gửi lệnh, mỗi lệnh gồm nhiều bước, có thứ tự, và luồng gọi không nên bị kẹt chờ khi thiết bị trả lời chậm. Thiết kế nào hợp nhất?

- Mỗi luồng tự khóa một `mutex` rồi nói chuyện thẳng với thiết bị
- Mỗi luồng tự mở kết nối riêng tới thiết bị để khỏi tranh chấp
- Một luồng chủ sở hữu kết nối, các luồng khác gửi lệnh qua hàng đợi
- Một `atomic<bool>` báo "thiết bị đang bận" để luồng khác thử lại

<p class="giai-thich" markdown>Tài nguyên chỉ một luồng nên đụng, thao tác nhiều bước có thứ tự: đúng chỗ của active object, luồng chủ xử lý tuần tự nên không cần khóa quanh thiết bị. Khóa mutex ở mỗi luồng vẫn đúng nhưng mỗi luồng chờ lâu suốt lúc nói chuyện chậm với thiết bị (vùng găng bị kéo dài). Mở nhiều kết nối là giả định thiết bị cho phép, trong khi đề nói chỉ có một. Cờ `atomic<bool>` thử lại thì thành vòng chờ bận và vẫn có khe hở giữa kiểm và dùng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. `lo` là `shared_ptr<vector<int>>`, `hang` là hàng đợi có mutex, luồng nhận lấy `lo` ra và cộng các phần tử. Vì sao đây là lỗi?

```text
hang.push(lo);          // luồng gửi, trong khóa
...
(*lo)[0] = 99;          // luồng gửi, sau khi gửi, vẫn sửa
```

- Vì `shared_ptr` không được phép đưa vào hàng đợi giữa các luồng
- Vì hàng đợi chưa dùng `std::move`, nên dữ liệu bị mất khi gửi đi
- Vì mutex của hàng đợi chỉ cho phép một luồng gửi mỗi lúc
- Vì vector có hai chủ, mà mutex của hàng đợi không che nội dung

<p class="giai-thich" markdown>Mẫu truyền thông điệp chỉ đúng khi **mỗi dữ liệu có một chủ tại một lúc**. Gửi `shared_ptr` rồi vẫn sửa nghĩa là cả hai bên còn cầm cùng một vector, và mutex quanh hàng đợi chỉ bảo vệ chính hàng đợi, không bảo vệ nội dung vector: data race. Đưa `shared_ptr` vào hàng đợi là hợp lệ. `std::move` ở đây là cách trao quyền gọn, không phải điều kiện để tránh mất dữ liệu (sao chép con trỏ vẫn giữ dữ liệu). Hàng đợi có mutex thì nhiều luồng gửi đều được.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Câu gốc: dữ liệu này có thật sự phải chia sẻ và sửa từ nhiều luồng? Ba vế của lỗi là chia sẻ, sửa, không đồng bộ; bốn mẫu bỏ một vế hoặc xếp hàng đúng chỗ. Chọn: chia theo luồng nếu gộp được, bất biến nếu đọc nhiều ghi ít, monitor cho việc ngắn, truyền thông điệp cho việc dài hay tài nguyên một chủ.
2. **Monitor**: dữ liệu và mutex chung một lớp, không lộ tham chiếu, gói kiểm-rồi-làm vào một hàm, và **không gọi callback khi giữ khóa** (mình chạy: hai lớp khóa ngược thứ tự, treo mã 124; sửa bằng sao chép danh sách ra ngoài khóa). Khóa thô là mặc định, khóa mịn chỉ khi đo thấy nút thắt, chia shard là đường giữa an toàn.
3. **Bất biến + copy-on-write**: `shared_ptr<const T>`, người ghi dựng bản mới rồi đổi con trỏ bằng `atomic_load`/`atomic_store` hoặc mutex ngắn (g++ 11, C++17; `atomic<shared_ptr>` là C++20); nhiều người ghi vẫn cần khóa ghi (mình chạy: bỏ khóa thì mất cập nhật mà TSan sạch). Chỉ hợp khi ghi hiếm: chép cả bản đắt hơn ghi tại chỗ vài trăm lần ở 100000 phần tử.
4. **Chia theo luồng rồi gộp** (ô riêng `alignas(64)` hoặc `thread_local`): không có gì để tranh, mình đo atomic chung chậm hơn 8 đến 9 lần ở `-O0` (đổi theo máy); đổi lại không có tổng chính xác giữa chừng.
5. **Truyền thông điệp / active object**: hàng đợi cộng `std::move`, mỗi dữ liệu một chủ tại một lúc, trạng thái của luồng nền không cần khóa; gửi đi rồi còn cầm là data race, và `std::thread` thành viên phải khai báo cuối. Go: `chan` là hàng đợi này, "chia sẻ bộ nhớ bằng cách giao tiếp" là chuyển quyền sở hữu.
