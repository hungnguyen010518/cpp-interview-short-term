# Bài 57 — Chọn cơ chế đồng bộ: mutex, atomic, condition_variable, future, semaphore

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Mở đầu mọi câu hỏi "dùng cơ chế nào?" bằng một câu: **luồng này cần gì từ luồng kia?** (đừng đụng cùng lúc, chờ một sự kiện, nhận một kết quả, hay giới hạn số người vào), rồi đi theo bảng và cây quyết định để chọn `mutex`, `atomic`, `condition_variable`, `promise`/`future`, `semaphore` hay `shared_mutex`.
    - Nói được chi phí theo nguyên lý (atomic rẻ hơn mutex không tranh chấp, mutex không tranh chấp rẻ hơn mutex phải ngủ chờ) và **đo thật** bộ đếm bằng mutex, atomic và bộ đếm chia ngăn, in tỉ lệ chứ không in mili giây.
    - Trả lời 10 tình huống hay gặp (cờ dừng, bộ đếm thống kê, hàng đợi việc, chờ khởi tạo xong, cache, giới hạn 3 kết nối, ghi log, bất biến hai biến, nhận kết quả, chờ N luồng) kèm lý do, và nói khi nào **không** nên dùng từng công cụ.
    - Tránh các bẫy: atomic nhiều biến không thành bất biến chung, `volatile` không phải đồng bộ, lock-free không có nghĩa nhanh hơn, spinlock hiếm khi đáng; giữ nguyên tắc "dùng mutex trước, đo, rồi mới tối ưu".

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `emplace_back` với đối số), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`, `lock_guard`, `unique_lock`, `shared_mutex` chỉ tên), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, `wait` có vị từ, dừng sạch), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, `compare_exchange`, `atomic_flag`, `volatile`), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`async`, `future`, `promise`), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (false sharing, `alignas(64)`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, TSan), [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (`static_cast`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp nhiều đầu bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Mỗi đầu bếp là một luồng. Bếp đã có sẵn cả một tủ đồ nghề: **thẻ vào thớt** (`mutex`), **bộ đếm bấm tay** (`atomic`), **chuông gọi món** (`condition_variable`), **phiếu hẹn** (`future`).

Người phỏng vấn không hỏi "thẻ vào thớt là gì". Họ đưa một tình huống: "bếp có một cái bảng ghi số đĩa đã ra; năm đầu bếp cùng cộng vào, bạn dùng gì?". Đầu bếp giỏi không nhớ thuộc lòng từng đồ nghề, mà hỏi ngược lại một câu: **người này cần gì từ người kia?** Cần "đừng đụng cùng lúc", cần "báo khi món xong", cần "nhận món một lần", hay cần "chỉ ba người được vào quầy rửa"?

Bài này dạy đúng câu hỏi đó, và thêm hai công cụ mà bếp ít dùng: **quầy rửa chỉ có ba vòi** (ba thẻ vòi, ai trả thẻ cũng được: `semaphore`) và **đầu bếp đứng canh ngay cửa thớt** thay vì đi ngủ (spinlock).

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Trong bếp thật, chờ thẻ thì đầu bếp đứng không và mọi thứ đều tốn gần như nhau. Với máy tính, mỗi công cụ có **giá khác nhau**: có cái chỉ là một lệnh CPU, có cái nhờ hệ điều hành đưa luồng đi ngủ rồi gọi dậy. Phần lớn bài này chính là đo cái giá đó.

## 📖 Giải thích

### 1. Câu hỏi gốc: luồng cần gì từ luồng kia?

Các công cụ của [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) đến [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) trả lời những **nhu cầu** khác nhau. Chọn sai thường là do không gọi tên nhu cầu trước.

| Luồng cần gì | Công cụ | Ghi chú ngắn |
|---|---|---|
| Loại trừ lẫn nhau: một lúc chỉ một luồng đụng dữ liệu (nhiều biến, một cấu trúc, một bất biến) | `std::mutex` + `lock_guard` | công cụ mặc định |
| Một biến đơn giản: bộ đếm, cờ, con trỏ | `std::atomic` | không bảo vệ được nhiều biến cùng lúc |
| Chờ một sự kiện hay điều kiện do luồng khác tạo | `std::condition_variable` (+ mutex + vị từ) | ngủ thay vì hỏi liên tục |
| Nhận **một** kết quả (hay ngoại lệ) đúng một lần | `std::promise` / `std::future` / `std::async` | không dùng được cho dòng kết quả liên tục |
| Giới hạn **số luồng** vào một khu (ví dụ 3) | `semaphore` (C++20, dạy kỹ ở Bài 60) | mutex là trường hợp "giới hạn 1" nhưng có chủ sở hữu |
| Đọc rất nhiều, ghi hiếm, vùng đọc đủ dài | `std::shared_mutex` | phải đo xem có đáng |
| Vùng găng cực ngắn, chắc chắn luồng giữ khóa không bị hệ điều hành tạm dừng (preempt) | spinlock | hiếm khi đáng (mục 4) |

Đọc cột đầu như câu hỏi: nếu bạn nói được nhu cầu bằng một câu, công cụ gần như tự hiện ra.

### 2. Chi phí theo nguyên lý, và cây quyết định

Chi phí đổi theo **có tranh chấp hay không**. Không tranh chấp nghĩa là lúc xin khóa không có luồng nào khác đang giữ. Tranh chấp là nhiều luồng cùng đòi một thứ cùng lúc.

| Công cụ | Chi phí (nguyên lý) | Luồng chờ làm gì |
|---|---|---|
| `atomic` | một lệnh CPU đặc biệt; chậm đi khi nhiều lõi cùng đòi một ô nhớ | không chờ lâu, không ngủ |
| `mutex` không tranh chấp | hai lệnh nguyên tử (khóa, nhả) cộng chi phí gọi hàm; trên Linux chưa cần nhờ hệ điều hành | không phải chờ |
| `mutex` có tranh chấp | luồng thua có thể được hệ điều hành cho đi ngủ rồi đánh thức: tốn vài lần chuyển ngữ cảnh (hệ điều hành đổi lõi từ luồng này sang luồng khác) | ngủ (không tốn CPU lúc ngủ, nhưng dậy chậm) |
| `condition_variable`, `future` | ngủ và được đánh thức; `future` còn cấp phát chỗ chứa kết quả | ngủ |
| spinlock | không ngủ, nên không có chi phí đánh thức | **quay vòng**, đốt CPU |

Thứ tự "atomic < mutex không tranh chấp < mutex phải ngủ chờ" là nguyên lý. Con số cụ thể ở mục 3 là do mình đo. Cây quyết định:

```text
Luồng cần gì từ luồng kia?
|
+-- Đừng đụng cùng lúc (loại trừ)
|     +-- đúng MỘT biến đơn (số, cờ, con trỏ), thao tác đơn giản ----> atomic
|     +-- nhiều biến, một cấu trúc, một bất biến chung ------------> mutex
|           +-- đọc rất nhiều, ghi hiếm, vùng đọc dài, ĐÃ ĐO ------> shared_mutex
|           +-- vùng găng cực ngắn, không bị preempt, ĐÃ ĐO -------> spinlock (hiếm)
|
+-- Chờ một điều kiện / sự kiện ----------------------------------> condition_variable
+-- Nhận MỘT kết quả (hay ngoại lệ) một lần ----------------------> promise / future
+-- Giới hạn số luồng vào một khu --------------------------------> semaphore
```

Nhánh nào cũng có chữ "đã đo" hoặc có điều kiện, trừ nhánh mặc định: **mutex**. Nguyên tắc làm việc: **dùng mutex trước, chạy đúng, đo, rồi mới tối ưu.** Mutex đúng và chậm sửa được; atomic hay lock-free sai thì rất khó tìm lỗi.

### 3. Đo thật: bộ đếm bằng mutex, atomic và chia ngăn

[Bài 28](../nhom-3-da-luong/28-atomic.md) đã đo atomic rẻ hơn mutex. Ở đây thêm cách thứ ba: **chia ngăn**. Mỗi luồng cộng vào **ngăn riêng** của mình (không ai đụng ai nên không cần đồng bộ), và chỉ **sau `join`** luồng chính cộng các ngăn lại. Mỗi ngăn đặt `alignas(64)` để không dính false sharing ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)).

Mình đo ba cách với bốn luồng, và thêm một lần với **một** luồng để xem mutex không tranh chấp đắt cỡ nào. Chương trình chỉ in **tỉ lệ**, vì mili giây thật đổi theo máy.

```cpp
#include <atomic>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

const int MOI_LUONG = 200000;              // mỗi luồng tăng 200000 lần

std::mutex khoa;
long long demKhoa = 0;                     // (1) bảo vệ bằng mutex
std::atomic<long long> demNguyenTu{0};     // (2) bảo vệ bằng atomic

struct Ngan {                              // (3) một "ngăn đếm" riêng cho mỗi luồng
    alignas(64) long long v = 0;           //     alignas(64): mỗi ngăn một dòng cache
};
Ngan cacNgan[4];                           //     mảng 4 ngăn: ngăn thứ k là cacNgan[k]

void bangMutex(int) {                      // tham số (số thứ tự luồng) không dùng nên không đặt tên
    for (int i = 0; i < MOI_LUONG; ++i) { std::lock_guard<std::mutex> giu(khoa); ++demKhoa; }
}
void bangAtomic(int) {
    for (int i = 0; i < MOI_LUONG; ++i) ++demNguyenTu;
}
void bangNgan(int k) {                     // (4) mỗi luồng chỉ ghi ngăn của mình: không tranh chấp
    for (int i = 0; i < MOI_LUONG; ++i) ++cacNgan[k].v;
}

long long chay(void (*ham)(int), int soLuong) {     // chạy soLuong luồng, trả số micro giây
    auto bat = std::chrono::steady_clock::now();
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < soLuong; ++k) cacLuong.emplace_back(ham, k);
    for (std::thread& t : cacLuong) t.join();
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::microseconds>(troi).count() + 1;  // +1: khỏi chia cho 0
}

int main() {
    long long uMutex1 = chay(bangMutex, 1);
    long long uAtomic1 = chay(bangAtomic, 1);
    demKhoa = 0;                                            // (5) đặt lại về 0 (chỉ còn luồng chính)
    demNguyenTu = 0;
    long long uMutex = chay(bangMutex, 4);
    long long uAtomic = chay(bangAtomic, 4);
    long long uNgan = chay(bangNgan, 4);
    long long tongNgan = 0;
    for (const Ngan& n : cacNgan) tongNgan += n.v;          // (6) gộp SAU join: an toàn
    std::cout << std::fixed << std::setprecision(1);        // (7) in số thực với 1 chữ số sau dấu phẩy
    std::cout << "tong: " << demKhoa << " " << demNguyenTu << " " << tongNgan << "\n";
    std::cout << "1 luong : mutex / atomic = " << uMutex1 / static_cast<double>(uAtomic1) << "\n";
    std::cout << "4 luong : mutex / atomic = " << uMutex / static_cast<double>(uAtomic) << "\n";
    std::cout << "4 luong : atomic / ngan  = " << uAtomic / static_cast<double>(uNgan) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ai đụng ai |
|---|---|---|
| (1)(2) | Hai bộ đếm dùng chung cho mọi luồng: một bảo vệ bằng khóa, một là atomic | mọi luồng cùng một ô nhớ |
| (3)(4) | Mỗi luồng `k` tăng `cacNgan[k].v`; `alignas(64)` đẩy mỗi ngăn sang dòng cache riêng | không ai đụng ai |
| `chay` | Dựng `soLuong` luồng chạy `ham`, `join` hết, trả thời gian đã trôi | |
| (5) | Hai lần chạy một luồng đã cộng vào `demKhoa`/`demNguyenTu`, nên đặt về 0 trước khi đo bốn luồng | chỉ luồng chính |
| (6) | Sau `join` mọi luồng đã xong, luồng chính cộng bốn ngăn: đồng bộ nhờ `join` | |
| (7) | `std::fixed` và `std::setprecision(1)` (cần `<iomanip>`) bắt `cout` in số thực dạng `3.2` | |

**Kết quả khi chạy** (g++ -std=c++17 -Wall -pthread, không tối ưu, máy 8 luồng phần cứng, ba lần liền; dòng đầu luôn như nhau, tỉ lệ đổi mỗi lần):

```text
tong: 800000 800000 800000
1 luong : mutex / atomic = 3.2
4 luong : mutex / atomic = 5.5
4 luong : atomic / ngan  = 16.2

tong: 800000 800000 800000
1 luong : mutex / atomic = 2.3
4 luong : mutex / atomic = 3.7
4 luong : atomic / ngan  = 10.6

tong: 800000 800000 800000
1 luong : mutex / atomic = 2.3
4 luong : mutex / atomic = 5.7
4 luong : atomic / ngan  = 14.5
```

Chạy với `-fsanitize=thread`: sạch. Mười lăm lần chạy không tối ưu của mình cho: một luồng, mutex chậm hơn atomic **1,2 đến 3,9 lần**; bốn luồng, **2,2 đến 5,8 lần**; atomic chậm hơn chia ngăn **12 đến 33 lần**. Máy bạn ra số khác; ba điều rút ra mới đáng nhớ:

- Ngay cả mutex **không tranh chấp** (một luồng) vẫn đắt hơn atomic (1,2 đến 3,9 lần trong các lần chạy của mình).
- Tranh chấp làm mutex đắt thêm, và ngay cả atomic cũng tranh nhau một ô nhớ.
- Cách nhanh nhất là **không chia sẻ**: mỗi luồng một ngăn, gộp một lần ở cuối.

Với `-O2`, cột cuối nhảy từ 2,4 đến 85 lần trong mười lần chạy, vì g++ biến cả vòng lặp của ngăn thành một lệnh cộng `200000` duy nhất (mình xem mã hợp ngữ). Đừng lấy con số đó làm bằng chứng; ở chương trình thật, mỗi lần tăng đi kèm việc thật.

**Thử thay đổi: bỏ `alignas(64)` ở (3).** Mình đã chạy tám lần: tỉ lệ atomic / ngan tụt từ cỡ 10 đến 23 xuống **1,5 đến 2,6**. Các ngăn nằm cạnh nhau trong cùng dòng cache nên bốn lõi chuyền dòng đó qua lại: false sharing, y như [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md).

Chia ngăn đúng cần cả hai điều: không chia sẻ **và** không dính cùng dòng cache.

!!! info "Bạn biết Go?"
    Go không có spinlock hay `memory_order` để chọn, nhưng tủ đồ nghề cùng ý: `sync.Mutex`, `sync/atomic`, `sync.Cond`, channel (thay cho nhiều thứ ở trên), `sync.RWMutex` (như `shared_mutex`), `sync.WaitGroup`. Bộ đếm chia ngăn trong Go cũng là mẹo hợp lệ: mỗi goroutine cộng biến cục bộ rồi gộp một lần. Chỗ khác lớn nhất: Go khuyên "đừng giao tiếp bằng cách chia sẻ bộ nhớ; hãy chia sẻ bộ nhớ bằng cách giao tiếp" (dùng channel), còn C++ chuẩn không có channel nên mutex và hàng đợi tự xây là chuyện thường.

### 4. Spinlock: đứng canh cửa thay vì đi ngủ

**Spinlock** (khóa quay) là khóa mà luồng chờ **không ngủ**: nó lặp đi lặp lại việc hỏi "khóa trống chưa?" cho tới khi được. Tự viết bằng `std::atomic_flag` ([Bài 28](../nhom-3-da-luong/28-atomic.md): `test_and_set()` đặt cờ lên và trả giá trị cũ, `clear()` hạ cờ). Macro `ATOMIC_FLAG_INIT` khởi tạo cờ ở trạng thái hạ (từ C++20 không cần nữa).

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

class KhoaQuay {                           // spinlock: "quay vòng" chờ khóa thay vì ngủ
public:
    void lock() {
        while (co.test_and_set()) {        // (1) đặt cờ lên; trả true nghĩa là cờ ĐÃ lên (người khác giữ): hỏi lại
        }
    }
    void unlock() { co.clear(); }          // (2) hạ cờ: người khác vào được
private:
    std::atomic_flag co = ATOMIC_FLAG_INIT;
};

KhoaQuay khoa;
int dem = 0;                               // int thường, được khóa quay bảo vệ

void tang() {
    for (int i = 0; i < 100000; ++i) {
        khoa.lock();
        ++dem;                             // (3) vùng găng cực ngắn: một phép cộng
        khoa.unlock();
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);
    for (std::thread& t : cacLuong) t.join();
    std::cout << "dem = " << dem << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Cờ `co` |
|---|---|---|
| (1) | Luồng đầu: `test_and_set` thấy cờ hạ, đặt lên, trả `false`: vòng `while` không chạy, đã giữ khóa | lên |
| (1) | Luồng thứ hai: `test_and_set` trả `true`, vòng `while` quay lại hỏi, hàng triệu lần mỗi giây | lên |
| (3)(2) | Luồng đầu cộng rồi `clear()`; lần hỏi kế tiếp của luồng thứ hai thấy cờ hạ và vào | hạ rồi lên |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
dem = 400000
```

Đúng, nhưng đúng không có nghĩa là đáng dùng. Mình đo riêng một chương trình khác (`-O2`, mỗi luồng 200000 lần khóa-tăng-nhả, máy 8 luồng phần cứng), mili giây, đổi theo máy:

| Số luồng | spinlock | `std::mutex` |
|---|---|---|
| 2 | 17 đến 25 | 19 |
| 4 | 94 đến 103 | 40 đến 41 |
| 16 | 1135 | 158 |
| 32 | 4954 | 297 |

Trong các cấu hình mình thử, spinlock **không thắng** mutex đáng kể ở chỗ nào, và thua nặng khi số luồng vượt số lõi.

Lý do: luồng đang **giữ** khóa có thể bị hệ điều hành tạm dừng (hết lượt chạy, thường gọi là bị preempt) trong lúc cả đám luồng khác quay vòng đốt CPU để chờ nó, mà nó không có lõi để chạy tiếp. Spinlock chỉ hợp khi vùng găng cực ngắn, số luồng không vượt số lõi và bạn **đã đo** thấy lợi. Spinlock cũng **không phải lock-free**: nó vẫn là một cái khóa, luồng giữ khóa bị hoãn thì cả đám kẹt.

**Thử thay đổi: bỏ lời gọi `khoa.unlock()` ở (3).** Mình đã chạy với `timeout 3`: chương trình không bao giờ in gì và bị `timeout` giết; đồng hồ cho `3,0` giây thật nhưng gần `11,7` giây CPU, tức là cả bốn luồng quay hết công suất. Mutex quên nhả ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)) cũng treo, nhưng luồng chờ **ngủ**, không đốt CPU; spinlock treo thì kèm quạt máy hú.

### 5. `shared_mutex`: đọc nhiều ghi ít, nhưng phải đo

`std::shared_mutex` ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) mới nhắc tên) cho **nhiều luồng đọc cùng lúc** (`std::shared_lock`) nhưng **một luồng ghi giữ riêng** (`std::unique_lock`). Nghe như luôn thắng `mutex` khi đọc nhiều, nhưng nó phức tạp hơn một mutex thường nên mỗi lần khóa đắt hơn.

Mình đo riêng một chương trình tra `unordered_map` 1000 khóa, 200000 lượt mỗi luồng, một luồng ghi 1 lượt trên 1000 lượt của nó (`-O2`). Kết quả, mili giây, đổi theo máy:

| Tình huống | `mutex` | `shared_mutex` |
|---|---|---|
| 4 luồng, vùng đọc cực ngắn (chỉ tra) | 36 | 28 |
| 8 luồng, vùng đọc cực ngắn | 78 | 94 |
| 4 luồng, vùng đọc có thêm 100 vòng đếm rỗng trong khóa | 413 | 89 |
| 8 luồng, vùng đọc có thêm 100 vòng đếm rỗng | 796 | 221 |

Rút ra: vùng đọc **ngắn** thì `shared_mutex` không hơn (ở 8 luồng còn chậm hơn); vùng đọc **dài** và ghi hiếm thì hơn nhiều lần, vì các luồng đọc không xếp hàng nữa. Nên: mặc định `mutex`, đo, rồi đổi nếu số đo đáng. Hai điều nên biết thêm: nếu luôn có người đọc thì luồng ghi có thể bị **đói** (chờ mãi, Bài 70 nói kỹ). Và cách khóa đổi theo vai trò: đọc dùng `shared_lock`, ghi dùng `unique_lock` (hay `lock_guard`).

### 6. Semaphore: chỉ nhắc, Bài 60 dạy kỹ

**Semaphore** (đèn hiệu đếm) giữ một con số `n` "thẻ": `acquire()` lấy một thẻ (hết thẻ thì **chờ**), `release()` trả một thẻ. Khác mutex ở hai điểm: số thẻ **tùy ý** (không chỉ 1), và **không có chủ sở hữu** (luồng này lấy, luồng khác trả cũng được). C++20 có `std::counting_semaphore` trong `<semaphore>`; mình kiểm tra thật: biên dịch với `g++ -std=c++20 -pthread`, còn `-std=c++17` báo `'counting_semaphore' in namespace 'std' does not name a template type`.

Mình chạy thử 10 luồng cùng xin dùng một khu chỉ cho 3 người (mỗi luồng ngủ 5 ms trong khu, một biến atomic ghi số người đồng thời lớn nhất): ra `3` ở hai lần chạy. Ở C++17 chưa có semaphore chuẩn, ta mô phỏng bằng `mutex` + `condition_variable` + một biến đếm số thẻ còn lại (Bài 60 viết lớp đó, Bài 69 tự cài kỹ hơn).

!!! info "Bạn biết Go?"
    Go không có semaphore trong thư viện chuẩn, nhưng một **channel có đệm** làm đúng việc đó: `sem := make(chan struct{}, 3)`, lấy thẻ là `sem <- struct{}{}` (đầy thì chờ), trả thẻ là `<-sem`. Mình chạy 10 goroutine với kênh đệm 3: số goroutine đồng thời lớn nhất đo được là `3`, `go run -race` sạch. Ý tưởng "đếm thẻ" cùng một.

### 7. Ba bẫy kinh điển

**Bẫy 1: atomic nhiều biến không thành bất biến chung.** Mỗi `std::atomic` chỉ bảo vệ **một** biến. Bất biến như "`a + b` luôn bằng 1000" liên quan hai biến, nên giữa hai lệnh luồng khác thấy trạng thái dở. [Bài 28](../nhom-3-da-luong/28-atomic.md) đã chạy: luồng đọc thấy tổng sai lần nào cũng có, mà TSan **vẫn sạch** (đây là race condition, không phải data race). Nhiều biến thì dùng một mutex bọc cả hai.

**Bẫy 2: `volatile` không phải đồng bộ.** `volatile` của C++ chỉ dặn trình biên dịch giữ nguyên các lần đọc ghi (dành cho thanh ghi phần cứng); nó không làm `++` nguyên tử, không tạo thứ tự giữa các luồng, và data race trên nó vẫn là hành vi không xác định ([Bài 28](../nhom-3-da-luong/28-atomic.md): `volatile int` đếm ra thiếu, TSan báo). Thứ dùng chung giữa luồng là `atomic` hoặc mutex.

**Bẫy 3: lock-free không có nghĩa nhanh hơn.** "Lock-free" nói về **bảo đảm tiến lên** (một luồng bị hoãn không làm kẹt cả đám), không nói về tốc độ. `atomic<long long>` trên máy mình là lock-free (`is_lock_free()`, [Bài 28](../nhom-3-da-luong/28-atomic.md)) mà ở mục 3 vẫn chậm hơn chia ngăn **12 đến 33 lần**, vì mọi lõi vẫn tranh nhau một dòng cache. Còn tự viết cấu trúc lock-free thì khó đúng (ABA, thứ tự bộ nhớ, Bài 62) và hiếm khi đáng.

## 💻 Ví dụ code

### Một chương trình, bốn công cụ, mỗi công cụ ở đúng chỗ

Chương trình sau có ba worker lấy việc từ hàng đợi, cộng bình phương các số 1 đến 100. Mỗi nhu cầu một công cụ: hàng đợi **chờ việc** (`mutex` + `condition_variable`), bộ đếm **thống kê** (`atomic`), **nhận một kết quả** của mỗi worker (`future`). Điểm tinh tế: cờ `xong` là `bool` thường **dưới khóa**, không phải atomic; lý do ở "Thử thay đổi".

```cpp
#include <atomic>
#include <condition_variable>
#include <future>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

std::mutex khoa;                           // (1) mutex + chuông + hai biến dưới khóa: hàng đợi việc
std::condition_variable chuong;
std::queue<int> hang;
bool xong = false;                         //     cờ "hết việc": đổi DƯỚI khóa vì có luồng đang ngủ trong wait

std::atomic<int> daXuLy{0};                // (2) bộ đếm thống kê: một con số, chỉ cộng

long long tho() {                          // (3) trả tổng của riêng luồng này qua future
    long long tongRieng = 0;
    while (true) {
        std::unique_lock<std::mutex> lk(khoa);
        chuong.wait(lk, [] { return !hang.empty() || xong; });
        if (hang.empty()) return tongRieng;          // hết việc và đã đóng: trả kết quả
        int x = hang.front();
        hang.pop();
        lk.unlock();                                 // làm việc NGOÀI khóa
        tongRieng += static_cast<long long>(x) * x;
        ++daXuLy;
    }
}

int main() {
    std::vector<std::future<long long>> ketQua;
    for (int k = 0; k < 3; ++k) ketQua.push_back(std::async(std::launch::async, tho));   // (4)

    for (int i = 1; i <= 100; ++i) {
        {
            std::lock_guard<std::mutex> giu(khoa);
            hang.push(i);
        }
        chuong.notify_one();               // (5) rung chuông: có việc mới
    }
    {
        std::lock_guard<std::mutex> giu(khoa);
        xong = true;                       // (6) đổi cờ dưới khóa rồi báo TẤT CẢ
    }
    chuong.notify_all();

    long long tong = 0;
    for (std::future<long long>& f : ketQua) tong += f.get();    // (7) nhận kết quả đúng một lần
    std::cout << "tong binh phuong 1..100 = " << tong << "\n";
    std::cout << "so viec da xu ly = " << daXuLy << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Công cụ nào lo |
|---|---|---|
| (4) | Ba worker chạy `tho` trên luồng riêng; mỗi cái trả về một `future<long long>` | `future`: nhận một kết quả |
| (1)(5) | `main` đẩy 100 số vào hàng đợi dưới khóa, mỗi lần rung chuông | `mutex` + `condition_variable` |
| (3) | Worker ngủ trong `wait` tới khi có việc hoặc `xong`; lấy một số, nhả khóa rồi mới bình phương | `condition_variable`, vùng găng ngắn |
| (2) | Mỗi việc xong, cộng một vào `daXuLy` | `atomic`: một con số |
| (6) | `main` đặt `xong = true` dưới khóa rồi `notify_all` để mọi worker đang ngủ dậy | cờ nằm dưới khóa |
| (7) | `get()` chờ từng worker trả `tongRieng` rồi `main` cộng ba số | `future` |

**Kết quả khi chạy** (năm lần liền đều như nhau; TSan sạch):

```text
tong binh phuong 1..100 = 338350
so viec da xu ly = 100
```

Ai lấy số nào đổi theo lần chạy, nhưng tổng 1 + 4 + 9 + ... + 10000 = 338350 và số việc 100 luôn đúng. Ba thứ cùng làm việc mà không thứ nào lấn sang nhiệm vụ của thứ khác.

**Thử thay đổi: biến `xong` thành `std::atomic<bool>` và đặt nó ở (6) mà không xin khóa.** Mình đã chạy:

- Ở dạng chương trình trên (không thêm gì), 200 lần chạy: **không lần nào treo**. Cửa sổ lỗi hẹp tới mức không thấy.
- Để mở cửa sổ ra, mình chèn `sleep_for` 20 ms vào vị từ của `wait` (sau khi nó thấy "chưa xong") và 1 ms giữa các lần đẩy việc: 10 lần chạy thì **cả 10 lần treo**, mã 124 của `timeout`. Cùng chèn `sleep_for` nhưng giữ `xong` dưới khóa: 10 lần đều xong.
- Vì sao: worker kiểm vị từ, thấy `false`, và **trước khi kịp ngủ**, `main` đặt cờ và `notify_all` (không ai đang chờ nên thông báo mất); worker sau đó ngủ mãi. Đây là lost wakeup của [Bài 27](../nhom-3-da-luong/27-condition-variable.md). Cờ mà luồng đang ngủ trong `wait` phụ thuộc vào thì phải đổi **dưới cùng mutex** với `wait`; atomic không sửa được chuyện đó.
- Bài học: cờ dừng là `atomic<bool>` khi luồng chỉ kiểm cờ ở mỗi vòng ([Bài 28](../nhom-3-da-luong/28-atomic.md)); là biến dưới khóa khi luồng ngủ chờ nó trong `condition_variable`.

### Mười tình huống: chọn gì, vì sao, và khi nào không

Mỗi tình huống là một câu người phỏng vấn có thể hỏi. Mình viết đáp án như cách nên trả lời.

1. **Luồng nền chạy vòng lặp, luồng chính muốn báo dừng.** `std::atomic<bool>`, luồng nền kiểm ở mỗi vòng. Không dùng `bool` thường hay `volatile` (data race, [Bài 28](../nhom-3-da-luong/28-atomic.md): `-O2` làm luồng nền treo mãi). Nếu luồng nền đang **ngủ** trong `condition_variable`, cờ phải đổi dưới khóa rồi `notify_all` (ví dụ trên).
2. **Đếm số request đã xử lý, chỉ đọc kết quả lúc tổng kết.** `std::atomic` (mục 3: rẻ hơn mutex), kể cả `fetch_add(1, std::memory_order_relaxed)` vì chỉ cần nguyên tử. Nếu nhiều luồng cộng dồn dập, **bộ đếm chia ngăn** nhanh hơn nữa. Muốn "tăng nếu chưa chạm trần" thì `compare_exchange` ([Bài 28](../nhom-3-da-luong/28-atomic.md)); không dùng `dem = dem + 1`.
3. **Hàng đợi việc: luồng chính bỏ việc vào, worker lấy ra.** `mutex` + `condition_variable` + vị từ (ví dụ trên, hay `BoundedQueue` ở Bài 66). Atomic không làm được vì hàng đợi là cấu trúc nhiều biến; vòng `while (hang.empty()) {}` thì đốt CPU ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)).
4. **Các luồng phải chờ một luồng nạp xong tài nguyên (cấu hình, từ điển) rồi mới chạy.** Một nơi chờ: `promise<void>` + `future` (luồng nạp gọi `set_value()`, luồng chờ gọi `get()`). Nhiều nơi cùng chờ một sự kiện: `condition_variable` + cờ `sanSang` + `notify_all` (hay `shared_future`). "Ai tới trước thì khởi tạo, người sau dùng luôn": `std::call_once` hoặc biến `static` cục bộ (Bài 68). Không dùng `sleep_for` rồi hy vọng đã xong.
5. **Cache tra cứu: đọc rất nhiều, thỉnh thoảng ghi.** Bắt đầu bằng **một mutex** quanh cả map. Chỉ đổi sang `shared_mutex` khi **đo** thấy vùng đọc đủ dài và ghi hiếm (mục 5: vùng đọc ngắn thì không lợi). Atomic không giúp: `map` là nhiều biến. Chi tiết: [Bài 54](54-container-da-luong.md) và Bài 71.
6. **Chỉ cho tối đa 3 luồng dùng kết nối cơ sở dữ liệu cùng lúc; luồng thứ 4 chờ.** `semaphore` (mục 6): `counting_semaphore<3>` ở C++20, hay mô phỏng bằng mutex + cv + biến đếm ở C++17 (Bài 60). Mutex không đủ vì chỉ cho một người vào. `shared_mutex` cũng sai: nó cho **không giới hạn** người đọc.
7. **Nhiều luồng ghi log ra màn hình.** **Một mutex quanh cả dòng** (hay: mọi luồng đẩy dòng vào hàng đợi, một luồng duy nhất ghi: Bài 61, 84). Từng lần `std::cout << ...` không gây data race (mình chạy với TSan: sạch), nhưng một dòng gồm nhiều `<<` thì các luồng **chen vào giữa**: xem ngay dưới.
8. **Chuyển tiền: trừ ở tài khoản A, cộng ở tài khoản B, và người khác không được thấy trạng thái dở.** **Mutex** bọc cả hai bước. Hai atomic riêng vẫn có khoảng hở ở giữa (mục 7, bẫy 1). Nhiều tài khoản thì nhớ thứ tự khóa hay `std::scoped_lock` ([Bài 26](../nhom-3-da-luong/26-deadlock.md)).
9. **Luồng chính cần kết quả của một phép tính nặng chạy trên luồng khác, đúng một lần, kể cả khi nó ném ngoại lệ.** `std::async` + `std::future` (hay `promise`). Ngoại lệ đi qua `get()`, còn `std::thread` thuần thì ngoại lệ làm `std::terminate` ([Bài 29](../nhom-3-da-luong/29-async-future.md)). Không dùng "biến chung + cờ + sleep".
10. **Luồng chính phải chờ N luồng chạy xong rồi mới đi tiếp.** `join` (hay `get()` trên N future). Nếu cần "đếm ngược N rồi mở cửa" mà luồng không kết thúc, hoặc nhiều luồng hẹn nhau ở một vạch qua nhiều vòng: `std::latch`, `std::barrier` (C++20, Bài 60). Không dùng atomic quay vòng chờ.

Về tình huống 7, đoạn mình chạy là: bốn luồng, mỗi luồng in ba dòng, mỗi dòng gồm nhiều `<<`, không khóa.

```text
for (int i = 0; i < 3; ++i)
    std::cout << "[luong " << k << "] dong " << i << "\n";     // k là số thứ tự luồng
```

Mình đẩy đầu ra qua ống (`| cat`). Trong 40 lần chạy, **21 lần** có ít nhất một dòng bị trộn (một lần đo lại lúc máy bận ra 31 trên 40: con số đổi theo máy và lúc chạy). Một lần chạy thật, mình chỉ chép năm dòng đầu:

```text
[luong 0[luong ] dong 01] dong 0
[luong 
[luong 01] dong 1
[luong ] dong 10] dong 
2
```

Thêm `std::lock_guard<std::mutex> giu(khoaLog);` ngay trước dòng `std::cout` trong vòng lặp thì **500 lần** chạy liền đều ra đủ 12 dòng nguyên vẹn. Hình dạng bị trộn đổi mỗi lần chạy, và mình chỉ thấy rõ khi đầu ra đi qua ống (ghi thẳng ra tệp thì 50 lần mình không thấy lần nào); đừng chép nó như một bảo đảm.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Mutex, atomic, condition_variable, future, semaphore: khi nào dùng cái nào?"
    Mình bắt đầu bằng câu hỏi luồng này cần gì từ luồng kia. Loại trừ lẫn nhau trên nhiều biến hay một cấu trúc thì mutex. Một biến đơn (bộ đếm, cờ) thì atomic. Chờ một sự kiện thì condition_variable với vị từ. Nhận một kết quả một lần thì promise/future. Giới hạn số luồng vào một khu thì semaphore. Nếu chưa chắc thì **mutex trước**: đúng đã, rồi đo, rồi mới tối ưu.
    **Nối tiếp:** "Vì sao không dùng atomic cho mọi thứ cho nhanh?" Vì atomic chỉ bảo vệ từng thao tác trên một biến; bất biến liên quan hai biến thì vẫn hở (mình chạy: thấy tổng sai lần nào cũng có, TSan vẫn sạch). Và khó đúng hơn nhiều, trong khi mutex đúng và chậm thì sửa được.

??? question "Spinlock là gì, khi nào dùng?"
    Khóa mà luồng chờ không ngủ mà quay vòng hỏi liên tục; viết được bằng `atomic_flag`. Nó tránh được chi phí đánh thức của mutex, nhưng đốt CPU lúc chờ và rất tệ nếu luồng đang giữ khóa bị hệ điều hành tạm dừng. Chỉ nên dùng khi vùng găng cực ngắn, số luồng không vượt số lõi, biết chắc không bị preempt, và đã đo thấy lợi. Mình đo trên máy 8 luồng phần cứng: spinlock ngang mutex ở hai luồng và chậm hơn 2 đến 17 lần ở bốn đến ba mươi hai luồng.
    **Nối tiếp:** "Spinlock có phải lock-free không?" Không: vẫn là khóa, luồng giữ khóa bị hoãn thì cả đám kẹt. Lock-free là bảo đảm có luồng tiến lên bất kể luồng khác bị hoãn.

??? question "`shared_mutex` có luôn nhanh hơn `mutex` khi đọc nhiều không?"
    Không. Nó cho nhiều luồng đọc cùng lúc nên có lợi khi vùng đọc đủ dài và ghi hiếm; mình đo: vùng đọc ngắn thì ngang hoặc chậm hơn (8 luồng: 78 so với 94 ms), vùng đọc dài thì nhanh hơn 3 đến 5 lần. Đổi lại mỗi lần khóa đắt hơn và luồng ghi có thể bị đói. Nên mặc định mutex, đo rồi mới đổi.
    **Nối tiếp:** "Thế làm cache đọc nhiều ghi ít?" Mutex quanh map; nếu đo thấy cần thì shared_mutex hoặc chia nhiều map nhỏ mỗi map một khóa (chia shard, [Bài 54](54-container-da-luong.md)).

??? question "Lock-free có nhanh hơn dùng mutex không?"
    Không nhất thiết. Lock-free là bảo đảm tiến lên, không phải bảo đảm tốc độ. `atomic<long long>` (lock-free trên máy mình) mà mình đo vẫn chậm hơn bộ đếm chia ngăn 12 đến 33 lần, vì các lõi tranh nhau một dòng cache. Khó viết đúng (ABA, thứ tự bộ nhớ), nên mặc định dùng mutex hay thư viện có sẵn.

??? question "Cách nhanh nhất để nhiều luồng cùng đếm một thứ?"
    Đừng chia sẻ: mỗi luồng một bộ đếm riêng (đặt `alignas(64)` để tránh false sharing), gộp sau `join`. Nếu bắt buộc chia sẻ thì atomic; mutex là chậm nhất trong ba cách mình đo.
    **Nối tiếp:** "Bỏ `alignas(64)` thì sao?" Mình đo: chỉ còn nhanh hơn atomic khoảng 1,5 đến 2,6 lần thay vì 10 đến 23 lần, vì các ngăn dính cùng dòng cache.

??? question "Mutex khác semaphore thế nào?"
    Mutex là trường hợp "một người vào" và có **chủ sở hữu**: luồng nào khóa thì luồng đó mở. Semaphore đếm số thẻ tùy ý và không có chủ: luồng này lấy, luồng khác trả được. Vì vậy mutex bảo vệ dữ liệu, còn semaphore hợp để giới hạn số luồng vào một khu hay báo hiệu giữa các luồng.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Chọn công cụ theo tên quen tay, không theo nhu cầu"
    Dùng atomic cho một bất biến hai biến, dùng mutex để "giới hạn 3 người", dùng vòng `while` quay vòng để chờ sự kiện. Luôn hỏi trước: luồng cần gì từ luồng kia?

!!! warning "Lỗi 2: Tối ưu trước khi đo"
    Đổi mutex sang spinlock, `shared_mutex` hay lock-free "cho nhanh" mà không đo: mình thấy spinlock chậm hơn mutex 2 đến 17 lần ở bốn luồng trở lên, và `shared_mutex` ngang hay chậm hơn khi vùng đọc ngắn. Dùng mutex, chạy đúng, đo (không bật TSan khi đo), rồi mới đổi.

!!! warning "Lỗi 3: Cờ dừng là atomic nhưng luồng ngủ trong `condition_variable`"
    Đặt `atomic<bool>` mà không xin khóa rồi `notify_all` có thể bị lost wakeup: mình mở cửa sổ lỗi bằng `sleep_for` thì treo 10 lần trên 10. Cờ mà vị từ của `wait` đọc thì đổi dưới cùng mutex.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="57" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Luồng nền chạy vòng lặp "làm một phần việc rồi kiểm cờ". Luồng chính muốn báo dừng. Không luồng nào ngủ chờ `condition_variable`. Cách đúng và đơn giản cho một cái cờ là gì?

- Dùng `volatile bool`, vì `volatile` bảo đảm luồng nền luôn đọc được giá trị mới nhất
- Dùng `std::atomic<bool>`: luồng chính `store(true)`, luồng nền `load()` mỗi vòng
- Dùng `bool` thường, vì chỉ một luồng ghi nên không thể có data race
- Dùng `std::future<void>` rồi gọi `get()` ở đầu mỗi vòng của luồng nền

<p class="giai-thich" markdown>`atomic<bool>` làm lần ghi và lần đọc không còn là data race, và hợp với đúng một cờ. `volatile` chỉ giữ nguyên các lần đọc ghi cho trình biên dịch, không tạo đồng bộ giữa luồng, nên vẫn là data race. `bool` thường cũng là data race vì một bên ghi, một bên đọc, không đồng bộ; "chỉ một luồng ghi" không đủ (Bài 28 chạy ra `-O2` treo mãi). Còn `get()` chặn tới khi có kết quả nên làm luồng nền đứng chờ thay vì chạy vòng lặp.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Một khu mã chỉ cho tối đa 3 luồng chạy cùng lúc, luồng thứ tư phải chờ tới khi có người ra. Chọn gì?

- Một `std::mutex`, vì mutex giữ được bao nhiêu người tùy cách khởi tạo
- Một `std::shared_mutex`, vì nó cho nhiều luồng vào cùng lúc, nên ba người cũng được
- Một `std::promise`, mỗi luồng đặt giá trị một lần để báo mình đã vào khu
- Một semaphore đếm với ba thẻ, hoặc mutex + condition_variable + biến đếm ở C++17

<p class="giai-thich" markdown>Đây đúng là nhu cầu "giới hạn số luồng vào một khu", việc của semaphore đếm: lấy thẻ, hết thẻ thì chờ, trả thẻ khi ra. Mutex chỉ cho đúng một luồng vào, không có chuyện khởi tạo thành ba. `shared_mutex` cho **không giới hạn** luồng đọc cùng lúc, không phải đúng ba. `promise` đặt giá trị một lần cho một người nhận, không hề giới hạn ai được vào.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn sau. Hai biến `a`, `b` đều là `std::atomic<int>` bắt đầu từ 0. Luồng 1 chạy một lần, luồng 2 chạy lặp lại. Điều nào đúng?

```text
// luồng 1:  ++a;  ++b;
// luồng 2:  if (a.load() != b.load()) ++phatHien;
```

- Luồng 2 có thể thấy `a` khác `b`, vì giữa hai lệnh của luồng 1 có khoảng hở
- Luồng 2 không bao giờ thấy `a` khác `b`, vì mọi thao tác atomic đều xếp theo một thứ tự chung
- Chương trình có data race, nên ThreadSanitizer sẽ báo lỗi ở dòng của luồng 2
- Luồng 2 chỉ thấy `a` khác `b` nếu ta đổi thành `memory_order_relaxed`

<p class="giai-thich" markdown>Mỗi lệnh atomic đúng riêng lẻ, nhưng `++a` và `++b` là hai thao tác rời; luồng 2 có thể đọc đúng lúc `a` đã tăng mà `b` chưa. Thứ tự chung của atomic không biến hai thao tác thành một khối. Không có data race vì mọi truy cập đều là atomic, nên TSan không báo (đây là race condition, như Bài 28 đã chạy). Và khe hở có sẵn với thứ tự mặc định mạnh nhất; `relaxed` không phải điều kiện để thấy nó. Bất biến hai biến phải đặt dưới một mutex.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Thỉnh thoảng luồng chờ ngủ mãi dù luồng báo đã chạy xong. Nguyên nhân là gì?

```text
std::mutex m;  std::condition_variable cv;  std::atomic<bool> xong{false};
// luồng chờ:  std::unique_lock<std::mutex> lk(m);
//             cv.wait(lk, [] { return xong.load(); });
// luồng báo:  xong = true;  cv.notify_one();     // không xin m
```

- `atomic<bool>` không đọc được bên trong lambda của `wait`, nên vị từ luôn trả `false` mãi mãi
- `notify_one` chỉ có tác dụng khi gọi trong lúc đang giữ khóa `m`, còn không thì bị bỏ qua
- Luồng báo đổi cờ và báo đúng lúc luồng chờ thấy `false` mà chưa ngủ, nên thông báo mất
- Đây là spurious wakeup: `wait` trả về dù không ai báo, nên nó lỡ mất lần thông báo thật

<p class="giai-thich" markdown>Luồng chờ kiểm vị từ, thấy `false`, và còn một khoảng trước khi thật sự ngủ; nếu cờ đổi và thông báo gửi đi đúng lúc đó thì không ai nghe và nó ngủ mãi (lost wakeup). Cờ mà vị từ đọc phải đổi dưới cùng mutex với `wait`. Atomic đọc được trong lambda bình thường, nên đó không phải nguyên nhân. `notify_one` không cần giữ khóa để có tác dụng. Spurious wakeup là chuyện ngược lại: `wait` dậy **thừa**, và vị từ chính là thứ chặn nó, không làm lỡ thông báo.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Bốn luồng ghi log, mỗi dòng gồm vài lần `std::cout << ... << "\n"`. Đầu ra thỉnh thoảng bị trộn giữa các dòng. Sửa thế nào?

- Khóa một mutex quanh cả dòng `std::cout`, hoặc dồn log cho một luồng ghi duy nhất
- Không cần sửa gì, vì `std::cout` đã an toàn luồng nên các dòng không thể bị trộn lẫn
- Thay `"\n"` bằng `std::endl`, vì `endl` làm mỗi dòng thành một thao tác nguyên tử
- Biến mỗi dòng thành `std::atomic<std::string>` để không luồng nào chen vào giữa dòng

<p class="giai-thich" markdown>Từng lần `<<` riêng lẻ không gây data race, nhưng cả dòng gồm nhiều lần `<<` nên các luồng chen vào giữa; phải gói **cả dòng** vào một vùng găng, hoặc để một luồng duy nhất ghi. Nói "cout đã an toàn nên không trộn" nhầm giữa không có data race với dòng nguyên vẹn (mình chạy: 21 trên 40 lần có dòng bị trộn mà TSan sạch). `endl` chỉ xả bộ đệm, không gộp các lần `<<`. Còn `std::atomic<std::string>` không hợp lệ vì `string` không sao chép được bằng phép sao chép đơn giản.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Cache tra cứu của bạn đọc rất nhiều, thỉnh thoảng ghi. Đồng nghiệp muốn đổi ngay mutex quanh `unordered_map` sang `shared_mutex`. Cách làm nào hợp lý nhất?

- Đổi ngay, vì đọc nhiều thì `shared_mutex` luôn nhanh hơn `mutex` bất kể vùng đọc dài hay ngắn
- Đổi sang spinlock, vì tra một khóa trong map rất ngắn nên không đáng để luồng đi ngủ
- Giữ mutex trước, đo trên tải thật, và chỉ đổi nếu số đo cho thấy vùng đọc đủ dài để đáng
- Bỏ khóa hẳn cho đường đọc, vì chỉ đọc thì không có data race dù có luồng ghi

<p class="giai-thich" markdown>Mutex đúng ngay và sửa dễ; `shared_mutex` chỉ lợi khi vùng đọc đủ dài và ghi hiếm, nên phải đo (mình đo: vùng đọc ngắn thì ngang hoặc chậm hơn, vùng đọc dài thì nhanh hơn 3 đến 5 lần). "Luôn nhanh hơn" sai vì mỗi lần khóa của nó đắt hơn. Spinlock cho vùng ngắn hấp dẫn nhưng mình đo chậm hơn mutex từ bốn luồng trở lên. Bỏ khóa đường đọc là data race ngay khi có luồng ghi, vì "chỉ đọc" chỉ đúng khi không ai ghi.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau. Chỉ một luồng, gọi `lock()` hai lần liền mà chưa `unlock()`. Chuyện gì xảy ra?

```text
class KhoaQuay {
    std::atomic_flag co = ATOMIC_FLAG_INIT;
public:
    void lock()   { while (co.test_and_set()) { } }
    void unlock() { co.clear(); }
};
```

- Lần thứ hai trả ngay, vì cùng một luồng thì khóa cho vào lại như khóa đệ quy
- Lần thứ hai ném ngoại lệ, vì thư viện phát hiện luồng này đã giữ khóa
- Lần thứ hai trả ngay, vì `test_and_set` trả `false` khi cờ đã được đặt
- Luồng quay vòng mãi ở lần thứ hai, đốt trọn một lõi CPU mà không ngủ

<p class="giai-thich" markdown>Lần đầu `test_and_set` thấy cờ hạ, đặt lên và trả `false`. Lần hai cờ đang lên nên nó trả `true`, vòng `while` quay lại mãi vì không ai hạ cờ: luồng này tự khóa mình và đốt một lõi (mình đo: bốn luồng quay thì 3 giây thật tốn gần 11,7 giây CPU). Khóa này không có khái niệm chủ sở hữu hay đếm lần giữ, nên không cho vào lại như khóa đệ quy, và cũng không kiểm tra gì để ném ngoại lệ. `test_and_set` trả giá trị **cũ** của cờ, tức `true` khi cờ đã lên, không phải `false`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Tám luồng cùng cộng dồn dập vào một bộ đếm thống kê, chỉ đọc kết quả sau khi tất cả `join`. Cách nào nhanh nhất mà vẫn đúng?

- Một `std::mutex` quanh `++`, vì mutex là công cụ mặc định nên luôn đủ nhanh
- Mỗi luồng cộng vào ngăn riêng (mỗi ngăn một dòng cache), luồng chính gộp sau `join`
- Một `std::atomic<long long>` chung, vì lock-free nên không thể bị chậm vì tranh chấp
- Một `volatile long long` chung, vì `volatile` luôn ghi thẳng ra bộ nhớ nên nhanh

<p class="giai-thich" markdown>Chia ngăn loại bỏ chia sẻ: không luồng nào đụng ngăn của luồng khác, nên không cần đồng bộ trong lúc cộng, và `join` lo phần gộp (mình đo: nhanh hơn atomic chung 12 đến 33 lần). Mutex đúng nhưng là cách chậm nhất trong ba cách mình đo. Atomic chung đúng và lock-free, song các lõi vẫn tranh nhau một dòng cache nên chậm đi nhiều; lock-free là bảo đảm tiến lên, không phải tốc độ. `volatile` thì không đúng: nó không làm `++` nguyên tử, vẫn là data race và đếm thiếu.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Câu hỏi gốc: **luồng này cần gì từ luồng kia?** Loại trừ trên nhiều biến thì `mutex`; một biến đơn thì `atomic`; chờ sự kiện thì `condition_variable` (cờ nằm dưới khóa); nhận một kết quả một lần thì `promise`/`future`; giới hạn số luồng vào khu thì semaphore (Bài 60); đọc nhiều ghi ít thì `shared_mutex` nếu đã đo.
2. Chi phí theo nguyên lý: atomic < mutex không tranh chấp < mutex phải ngủ chờ. Mình đo bốn luồng: mutex chậm hơn atomic 2,2 đến 5,8 lần, và atomic chậm hơn bộ đếm **chia ngăn** (mỗi luồng một ngăn `alignas(64)`, gộp sau `join`) 12 đến 33 lần; bỏ `alignas(64)` thì lợi thế còn 1,5 đến 2,6 lần.
3. Spinlock (viết bằng `atomic_flag`) đúng nhưng đốt CPU lúc chờ; mình đo nó ngang mutex ở hai luồng và chậm hơn 2 đến 17 lần ở bốn luồng trở lên. `shared_mutex` ngang hoặc chậm hơn khi vùng đọc ngắn, nhanh hơn 3 đến 5 lần khi vùng đọc dài và ghi hiếm.
4. Ba bẫy: hai `atomic` không giữ được bất biến chung (cần một mutex); `volatile` không phải đồng bộ; lock-free không có nghĩa nhanh hơn. Cờ mà vị từ của `wait` đọc phải đổi dưới cùng mutex, nếu không có thể lost wakeup (mình mở cửa sổ lỗi: treo 10 lần trên 10).
5. Nguyên tắc: **dùng mutex trước, chạy đúng, đo (không bật TSan khi đo), rồi mới tối ưu**; mọi cách khác (atomic, lock-free, spinlock, `shared_mutex`) phải có số đo chứng minh. Go dùng `sync.Mutex`, `sync/atomic`, channel (kênh có đệm làm semaphore) cho cùng các nhu cầu.
