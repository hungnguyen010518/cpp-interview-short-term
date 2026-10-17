# Bài 66 — Thực chiến: hàng đợi chặn có giới hạn (producer-consumer)

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết được trên bảng trắng `BoundedQueue<T>` đúng ngay lần đầu: `push` chờ khi đầy, `pop` chờ khi rỗng, **hai** `condition_variable` (`khongDay`, `khongRong`), mỗi điều kiện một vị từ đọc dưới cùng một mutex, và nói được vì sao hai cv chứ không phải một (đã chạy thật: một cv với `notify_one` treo, mã 124).
    - Thêm `dong()` để dừng sạch (consumer thoát khi hàng **đóng và cạn**, producer đang chờ vì đầy được đánh thức và nhận "từ chối"), cùng `try_pop` (không chờ) và `pop_for` (chờ có hạn, ba kết quả: có, hết giờ, đã đóng).
    - Phân biệt ba thứ làm hỏng `wait`: spurious wakeup (chuẩn cho phép, mình không tái hiện được), wakeup bị cướp (`if` thay `while`: mình chạy ra SIGSEGV) và lost wakeup (đổi cờ không khóa: treo); nói được notify trong hay ngoài khóa đều đúng và khi nào chọn cái nào.
    - Phân tích chi phí (đo sức chứa 1, 4, 64, 4096), nói khi nào **không** nên dùng hàng đợi chặn, và trả lời các câu nối tiếp của người phỏng vấn; so với channel có đệm của Go.

**Bạn cần biết trước:** [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, `wait` có vị từ, producer-consumer, hàng đợi có giới hạn, `wait_for`, dừng sạch bằng cờ), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `unique_lock`, TSan chạy dưới `setarch -R`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `sleep_for`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template lớp `template <typename T>`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`std::optional`, `if (r)`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`std::deque`: `push_back`, `pop_front`, `front`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`, `make_unique`).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đẩy một tờ giấy trắng qua bàn: "Viết cho tôi một hàng đợi dùng chung giữa nhiều luồng, chứa tối đa N phần tử. Đầy thì người bỏ vào phải chờ, rỗng thì người lấy ra phải chờ. Bạn có hai mươi phút." Rồi anh ấy ngồi im, và bạn biết anh đang đếm: bạn có viết `wait` có vị từ không, có hai chiếc chuông hay một, có giữ khóa lúc xử lý không.

Trong **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), đây là **quầy ra món** chỉ có 4 chỗ đặt đĩa. Đầu bếp (producer) đặt đĩa lên quầy; người chạy bàn (consumer) lấy đĩa đi. Quầy đầy thì đầu bếp đứng chờ, quầy trống thì người chạy bàn đứng chờ. Có **hai chuông**: chuông "quầy có đĩa" gọi người chạy bàn, chuông "quầy có chỗ trống" gọi đầu bếp. Hết giờ thì bếp còn phải **đóng quầy**: đầu bếp dừng đặt đĩa, nhưng người chạy bàn phải bưng nốt đĩa còn lại rồi mới tan ca, và ai đang đứng chờ chỗ trống phải biết quầy đã đóng. Phần khó nhất của đề nằm ở đây, không phải ở `push`/`pop`.

!!! info "Chỗ nào ví von quầy ra món không còn đúng?"
    Chuông thật chỉ reo khi có người bấm và không bao giờ "bấm vào khoảng không rồi mất". Chuông `condition_variable` thì mất nếu bấm lúc chưa ai ngồi chờ, và chuẩn còn cho phép nó reo khi chẳng ai bấm. Quầy thật cũng có người liếc mắt nhìn thấy đĩa; luồng thì chỉ biết được qua **biến** nằm dưới mutex. Vì vậy cả bài xoay quanh biến chứ không xoay quanh tiếng chuông.

## 📖 Giải thích

### Đề 1: `BoundedQueue<T>` với `push` chờ khi đầy, `pop` chờ khi rỗng

!!! example "Đề bài 1"
    **Ràng buộc.** Lớp `BoundedQueue<T>` với hàm tạo nhận sức chứa `toiDa`. `push(T)` chặn tới khi hàng còn chỗ; `pop()` chặn tới khi hàng có việc và trả `T`. An toàn với nhiều producer và nhiều consumer; không chờ bận; hàng không bao giờ quá `toiDa`; phần tử ra theo thứ tự vào. Dùng `T` di chuyển được (không bắt buộc sao chép được). Chỉ dùng thư viện chuẩn C++17, không cần dừng sạch (đề 2 làm).

    **Đầu vào/đầu ra (bài test).** Sức chứa 4, 3 producer mỗi người đẩy các số 1..1000, 3 consumer mỗi người lấy đúng 1000 lần: in tổng các số lấy được và kiểm tra hàng chưa từng quá 4. Mong đợi `tong = 1501500, dinh <= 4: dung`. Với một producer và một consumer: các số ra đúng thứ tự 1, 2, 3...

??? tip "Gợi ý 1"
    Hỏi trước: có **mấy điều kiện chờ khác nhau**, và ai chờ ai? Producer chờ một điều kiện, consumer chờ một điều kiện khác.

??? tip "Gợi ý 2"
    Mỗi điều kiện phải là thứ **đọc được từ dữ liệu dưới mutex**: "còn chỗ" là `hang.size() < toiDa`, "có việc" là `!hang.empty()`. Mỗi điều kiện một `condition_variable`, và luôn dùng `wait(lk, vịTừ)`.

??? tip "Gợi ý 3"
    Khung của `push`: khóa; `wait` tới khi `size() < toiDa`; `push_back`; nhả khóa; báo `khongRong`. `pop` là ảnh gương: khóa; `wait` tới khi không rỗng; lấy ra; nhả khóa; báo `khongDay`. Báo **bên kia**, vì hành động của mình vừa thỏa điều kiện của họ.

Bài này không dạy lại `wait` và producer-consumer; [Bài 27](../nhom-3-da-luong/27-condition-variable.md) đã có hàng đợi 4 chỗ viết bằng biến toàn cục. Ở đây ta đóng gói thành lớp dùng lại được, rồi thêm phần người phỏng vấn thật sự hỏi. Hướng giải gói trong một bảng, mỗi hàng là "ai chờ gì, ai báo":

| Ai chờ | Chờ tới khi | Ai báo, sau khi làm gì | `condition_variable` |
|---|---|---|---|
| producer (`push`) | `hang.size() < toiDa` (còn chỗ) | consumer, sau khi `pop` một phần tử | `khongDay` |
| consumer (`pop`) | `!hang.empty()` (có việc) | producer, sau khi `push` một phần tử | `khongRong` |

Cả hai điều kiện đọc cùng `hang`, nên dùng **một** mutex cho cả hai. Hai cv chỉ để biết **gọi đúng người**; sự thật nằm trong `hang`, không nằm trong chuông.

### Đề 2: `dong()`, `try_pop`, `pop_for`

!!! example "Đề bài 2"
    **Ràng buộc.** Thêm vào lớp trên: `dong()` đóng hàng. Sau khi đóng: `push` mới bị **từ chối** (trả `false`); producer đang chờ vì đầy phải thức dậy và nhận `false`; consumer vẫn lấy **hết** việc còn lại rồi mới nhận tín hiệu "hết" (`pop` trả `std::optional` rỗng); consumer đang ngủ vì hàng rỗng phải thoát. Thêm `try_pop()` (không chờ, rỗng thì trả rỗng) và `pop_for(ra, hạn)` (chờ tối đa `hạn`) với ba kết quả phân biệt được: có việc, hết giờ, đã đóng và cạn. Không mất việc, không chờ bận, không treo.

    **Đầu vào/đầu ra (bài test).** (1) 3 producer 3 consumer, consumer không biết trước số việc, vòng lặp tới khi `pop` trả rỗng; sau khi mọi producer `join` thì `dong()`: mong đợi `tong = 1501500, so viec = 3000`. (2) Bỏ 10, 20, 30 vào, `dong()`, `push(40)` bị từ chối, vẫn lấy được đủ 3 việc (tổng 60). (3) Hàng sức chứa 1 đầy, một luồng `push(2)` đang chờ, `dong()` làm nó nhận `false`. (4) `try_pop` hàng rỗng; `pop_for` 30 ms hàng rỗng ra "hết giờ", sau `push(7)` ra `co 7`, sau `dong()` ra "đã đóng" ngay chứ không chờ hết hạn.

??? tip "Gợi ý 1"
    Có thêm một điều kiện thứ ba: **đã đóng**. Hãy sửa **cả hai** vị từ: producer thôi chờ khi "còn chỗ **hoặc** đã đóng"; consumer thôi chờ khi "có việc **hoặc** đã đóng". Ai cần biết cờ `dong_` đổi? Cả hai cv.

??? tip "Gợi ý 2"
    Consumer thoát khi **đã đóng và cạn**, không phải chỉ khi đã đóng: nếu hàng còn việc thì lấy tiếp. Cờ `dong_` đổi **dưới cùng mutex**, rồi `notify_all` trên **cả hai** cv (mọi luồng đang ngủ đều có thể cần biết).

??? tip "Gợi ý 3"
    `wait_for(lk, hạn, vịTừ)` trả `bool`: `false` nghĩa là hết giờ mà vị từ vẫn sai. Sau khi vị từ đúng, kiểm theo thứ tự: hàng rỗng (vậy là đóng và cạn) hay có phần tử. Gom việc "lấy phần tử đầu, nhả khóa, báo `khongDay`" vào một hàm riêng để `pop`, `try_pop`, `pop_for` dùng chung.

**Vì sao các vị từ này đúng: ba thứ có thể làm hỏng `wait`.** Mỗi thứ có nguyên nhân riêng và cách chữa riêng; đừng gộp chúng thành "cứ có `while` là xong".

| Hiện tượng | Chuẩn nói gì | Trên máy này (g++ 11) | Chữa bằng |
|---|---|---|---|
| Spurious wakeup: `wait` trả về mà không ai notify | Chuẩn **cho phép** | Mình không tái hiện được | Vị từ (`wait(lk, pred)`) |
| Wakeup bị cướp: A được báo, B lấy mất món trước khi A xin lại được khóa | Xảy ra được kể cả khi không có spurious wakeup | Tái hiện được: bản `if` ở mục 💻 SIGSEGV 10/10 lần | Vị từ kiểm lại **sau** khi dậy |
| Lost wakeup: `notify` đến lúc chưa ai chờ, hay đổi cờ không khóa rơi vào khe giữa "kiểm" và "ngủ" | `notify` chỉ đánh thức luồng **đang chờ** | Tái hiện được khi mở rộng khe hở (mục 💻) | Đổi biến điều kiện **dưới mutex** + vị từ kiểm **trước** khi ngủ |

**Notify trong hay ngoài khóa?** Cả hai **đúng** theo chuẩn, vì sự thật nằm trong biến chứ không trong chuông. Code bài này nhả khóa rồi mới notify: luồng vừa được gọi dậy khỏi phải xin khóa khi người báo vẫn đang giữ (một số thư viện tự tối ưu chuyện này). Mình đo hai bản trên máy mình: chênh lệch nằm trong nhiễu, nên đừng coi là luật. Notify **trong** khóa cần khi luồng được đánh thức có thể hủy ngay chính hàng đợi hay cv của nó: notify sau khi nhả khóa khi đó là dùng một cv đã bị hủy. Bài này tránh chuyện đó bằng cách `join` mọi luồng trước khi hủy hàng.

**Khi hàng đầy, làm gì?** `push` chặn là một lựa chọn trong năm, và người phỏng vấn hay hỏi "thế nếu không được chặn?".

| Chính sách khi đầy | Dùng khi | Giá phải trả |
|---|---|---|
| Chặn producer (`push` bài này) | Cần chạy tuần tự đúng, không được mất việc; muốn làm producer chậm lại theo consumer (áp lực ngược, backpressure) | Producer có thể ngủ lâu |
| Chờ có hạn (`push_for`) | Chờ được một lúc rồi báo lỗi cho người gọi | Phải xử lý "hết giờ" |
| Từ chối ngay (`try_push`) | Luồng **không được ngủ** (giao diện, vòng lặp thời gian thực) | Người gọi quyết định bỏ hay thử lại |
| Bỏ phần tử cũ nhất (hàng vòng) | Dữ liệu cảm biến, chỉ giá trị mới nhất có ý nghĩa | Mất dữ liệu có chủ đích |
| Không giới hạn | Việc ít, chắc chắn không phình | Hết bộ nhớ nếu consumer chậm mãi |

**Khi nào không nên dùng hàng đợi chặn?** Khi luồng không được phép ngủ (dùng `try_push` và một chính sách bỏ việc). Khi chỉ cần nhận **một kết quả** từ một việc (dùng `future`, [Bài 29](../nhom-3-da-luong/29-async-future.md)). Khi đúng một producer và một consumer cần tốc độ cao: hàng vòng lock-free ([Bài 62](../nhom-8-da-luong-chieu-sau/62-lock-free-co-ban.md)). Và khi các tầng hàng đợi nối đuôi nhau thành vòng (consumer của hàng A là producer của hàng B và ngược lại), vì các hàng cùng đầy sẽ làm tất cả chờ nhau (deadlock).

## 💻 Ví dụ code

### Lời giải đề 1: `BoundedQueue<T>` hai cv

Về cú pháp mới: `template <typename T>` là template lớp ([Bài 34](../nhom-4-oop-patterns/34-template.md)); `explicit` trước hàm tạo cấm `BoundedQueue<int> q = 4;` kiểu gán ngầm; `[this]` cho lambda dùng được thành viên của đối tượng ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)); đuôi `_` là thói quen đặt tên thành viên. `dinh_` ghi số phần tử nhiều nhất từng thấy, để test kiểm hàng không vượt sức chứa.

```cpp
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(std::size_t toiDa) : toiDa_(toiDa) {}

    void push(T v) {
        std::unique_lock<std::mutex> lk(khoa_);
        khongDay_.wait(lk, [this] { return hang_.size() < toiDa_; });   // (1) đầy thì chờ
        hang_.push_back(std::move(v));                                  // (2)
        if (hang_.size() > dinh_) dinh_ = hang_.size();
        lk.unlock();
        khongRong_.notify_one();                                        // (3) báo "có việc"
    }

    T pop() {
        std::unique_lock<std::mutex> lk(khoa_);
        khongRong_.wait(lk, [this] { return !hang_.empty(); });         // (4) rỗng thì chờ
        T v = std::move(hang_.front());
        hang_.pop_front();
        lk.unlock();
        khongDay_.notify_one();                                         // (5) báo "có chỗ"
        return v;
    }

    std::size_t dinh() {                // số phần tử nhiều nhất từng thấy
        std::lock_guard<std::mutex> g(khoa_);
        return dinh_;
    }

private:
    std::mutex khoa_;
    std::condition_variable khongDay_;   // producer chờ: hàng còn chỗ
    std::condition_variable khongRong_;  // consumer chờ: hàng có việc
    std::deque<T> hang_;
    std::size_t toiDa_;
    std::size_t dinh_ = 0;
};

int main() {
    const int SO_PRODUCER = 3, SO_CONSUMER = 3, MOI_NGUOI = 1000;
    BoundedQueue<int> q(4);
    std::vector<long long> tong(SO_CONSUMER, 0);

    std::vector<std::thread> luong;
    for (int k = 0; k < SO_CONSUMER; ++k) {
        luong.emplace_back([&q, &tong, k] {
            for (int i = 0; i < MOI_NGUOI; ++i) tong[k] += q.pop();   // đúng 1000 lần: chưa cần tín hiệu dừng
        });
    }
    for (int p = 0; p < SO_PRODUCER; ++p) {
        luong.emplace_back([&q] {
            for (int i = 1; i <= MOI_NGUOI; ++i) q.push(i);
        });
    }
    for (std::thread& t : luong) t.join();

    long long cong = 0;
    for (long long x : tong) cong += x;
    std::cout << "tong = " << cong << ", dinh <= 4: " << (q.dinh() <= 4 ? "dung" : "sai") << "\n";

    BoundedQueue<int> mot(2);                    // một producer, một consumer: thứ tự FIFO
    bool dungThuTu = true;
    std::thread nhan([&] { for (int i = 1; i <= 1000; ++i) if (mot.pop() != i) dungThuTu = false; });
    std::thread gui([&] { for (int i = 1; i <= 1000; ++i) mot.push(i); });
    gui.join(); nhan.join();
    std::cout << "thu tu FIFO: " << (dungThuTu ? "dung" : "sai") << "\n";
    BoundedQueue<std::unique_ptr<int>> chiDiChuyen(2);   // T chỉ di chuyển được vẫn dùng được
    chiDiChuyen.push(std::make_unique<int>(99));
    std::cout << "unique_ptr: " << *chiDiChuyen.pop() << "\n";
    return 0;
}
```

**Chạy từng dòng** (nhiều luồng chạy xen kẽ; bảng nói vai trò, không phải thứ tự cố định)

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Producer chờ trên `khongDay_` tới khi `size() < toiDa_`. Đầy thì `wait` nhả khóa và ngủ; dậy thì xin lại khóa và **kiểm lại** vị từ |
| (2) | Vị từ đúng nên hàng còn chỗ; `push_back` dưới khóa, cập nhật `dinh_` |
| (3) | Nhả khóa **rồi** báo `khongRong_`: một consumer đang chờ việc được gọi dậy |
| (4) | Consumer chờ trên `khongRong_` tới khi hàng không rỗng |
| (5) | Lấy xong, nhả khóa, báo `khongDay_`: một producer đang chờ chỗ được gọi dậy |

**Kết quả khi chạy:**

```text
tong = 1501500, dinh <= 4: dung
thu tu FIFO: dung
unique_ptr: 99
```

Mình biên dịch sạch cảnh báo (cả `-O2`), chạy 100 lần mỗi mức `-O` cùng đúng ba dòng đó, và TSan (`setarch x86_64 -R`) chạy 30 lần không báo gì. Dòng cuối cho thấy `T` chỉ di chuyển được (`unique_ptr`) vẫn dùng được, vì `push` và `pop` chỉ **di chuyển**. Mỗi consumer lấy **đúng 1000 lần** nên chưa cần tín hiệu dừng (đề 2 bỏ ràng buộc này). Tổng 3 × 500500 luôn đúng; consumer nào lấy số nào thì đổi theo lần chạy, nên bài chỉ in tổng. Thứ tự FIFO chỉ kiểm được với **một** producer và một consumer: với nhiều producer, chuẩn không nói luồng nào chen vào trước.

**Bản SAI 1: một `condition_variable` chung với `notify_one`.** Nhiều người viết một cv cho gọn. Mình đổi hai cv thành một `cv_` và giữ `notify_one` (còn lại y hệt, vị từ vẫn đúng), rồi giảm sức chứa còn 1:

```cpp
// bo-qua-kiem-tra
// SAI: chỉ khác chỗ khai báo cv và hai lời notify
std::condition_variable cv_;                       // một cv cho cả hai phía
// push:  cv_.wait(lk, [this] { return hang_.size() < toiDa_; });  ...  cv_.notify_one();
// pop:   cv_.wait(lk, [this] { return !hang_.empty(); });         ...  cv_.notify_one();
```

Mình chạy bài test với 3 producer 3 consumer, sức chứa 1: **10 lần trên 10 treo**, `timeout 3` mã **124** (cả `-O2`, cả TSan). TSan im lặng: treo không phải data race. Cơ chế, từng bước:

1. Hàng rỗng, hai consumer C1, C2 đang ngủ. P1 đặt một phần tử và báo; C1 dậy.
2. Trước khi C1 kịp lấy khóa, P2 đến, thấy hàng đầy nên ngủ.
3. C1 lấy phần tử rồi báo. Hai luồng đang chờ là C2 và P2, và chuông chọn **C2** (chuẩn không nói chọn ai), nhưng C2 thấy hàng rỗng và ngủ lại.
4. C1 quay lại, hàng rỗng, ngủ. Cuối cùng C1, C2, P2 đều ngủ trong khi vị từ của P2 đã đúng và không ai gọi nó.

Với sức chứa **4** (như bài test chính), cùng bản sai này mình chạy 10 lần: **10 lần ra bình thường**. Đó mới là cái bẫy: bản sai qua bài test dễ, treo ở tải khác. Chữa bằng một trong hai cách: hai cv như lời giải (báo đúng phe), hoặc một cv với `notify_all` (mình chạy 10 lần ở sức chứa 1: ra đúng, TSan sạch), đổi lại mọi luồng chờ đều dậy rồi phần lớn ngủ lại ("thundering herd", bầy đàn cùng thức dậy).

**Bản SAI 2: `if` thay cho vị từ.** Dạng `if (hang_.empty()) khongRong_.wait(lk);` (và `if (hang_.size() >= toiDa_) khongDay_.wait(lk);` ở `push`) nhìn như vòng `while` ngắn gọn; mọi thứ khác giữ nguyên, kể cả `T v = std::move(hang_.front());` ngay sau.

Mình chạy bài test chính: **10 lần trên 10 SIGSEGV** (mã 139, không in gì). Biên dịch với `-D_GLIBCXX_ASSERTIONS` thì mã 134 và in `front() ... Assertion '!this->empty()' failed`; TSan dừng bằng `SEGV` ở dòng `front()` mà **không** báo data race, vì mọi truy cập đều dưới khóa. Đây là "wakeup bị cướp": consumer C1 được báo, nhưng C3 (chưa ngủ, vừa đến) lấy mất phần tử; C1 dậy, đi tiếp vì `if` không kiểm lại, và gọi `front()` trên hàng rỗng (hành vi không xác định, mình chỉ nói điều thấy trên máy này). Không cần spurious wakeup mới hỏng; thêm spurious wakeup thì chuẩn càng không tha cho `if`.

**Thử thay đổi: đổi sức chứa trong bài test (3 producer, 3 consumer, 100000 việc mỗi người, `-O2`).** Mình đo ba lần mỗi mức bằng một chương trình riêng (không bật TSan, máy đang bận nên nhiễu): sức chứa 1 mất 3,8 s đến 5,7 s; sức chứa 4 mất 2,8 s đến 3,9 s; sức chứa 64 mất 0,31 s đến 0,52 s; sức chứa 4096 mất 0,05 s đến 0,14 s. Sức chứa nhỏ buộc hai phía **đi từng bước một**: mỗi phần tử kèm một lần đánh thức và một lần đổi luồng. Sức chứa lớn cho mỗi bên làm nhiều việc liền trước khi phải chờ bên kia. Con số đổi theo máy, nhưng mẫu ổn định: nhỏ thì chậm theo bậc độ lớn, không chỉ vài phần trăm.

### Lời giải đề 2: `dong()`, `try_pop`, `pop_for`

Về cú pháp mới: `std::optional<T>` rỗng là "không có phần tử" ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)); `enum class Kq` ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)) cho `pop_for` ba kết quả. `pop_for` dùng tham số ra `T& ra` vì C++17 chưa có `std::expected` (C++23); `layRa` nhận `unique_lock&` để tự nhả khóa. `while (std::optional<int> v = q.pop())` khai báo `v` ngay trong điều kiện: vòng lặp chạy khi hộp có giá trị, giống `for v := range ch` của Go.

```cpp
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <iostream>
#include <mutex>
#include <optional>
#include <thread>
#include <utility>
#include <vector>

enum class Kq { co, hetGio, daDong };    // kết quả của pop_for

template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(std::size_t toiDa) : toiDa_(toiDa) {}

    bool push(T v) {                                     // false: hàng đã đóng, việc bị từ chối
        std::unique_lock<std::mutex> lk(khoa_);
        khongDay_.wait(lk, [this] { return hang_.size() < toiDa_ || dong_; });   // (1)
        if (dong_) return false;                         // (2)
        hang_.push_back(std::move(v));
        lk.unlock();
        khongRong_.notify_one();
        return true;
    }

    std::optional<T> pop() {                             // nullopt: đã đóng và hết việc
        std::unique_lock<std::mutex> lk(khoa_);
        khongRong_.wait(lk, [this] { return !hang_.empty() || dong_; });         // (3)
        return layRa(lk);
    }

    std::optional<T> try_pop() {                         // không chờ: rỗng thì nullopt
        std::unique_lock<std::mutex> lk(khoa_);
        return layRa(lk);                                // (4)
    }

    Kq pop_for(T& ra, std::chrono::milliseconds han) {   // chờ tối đa `han`
        std::unique_lock<std::mutex> lk(khoa_);
        bool duDieuKien = khongRong_.wait_for(lk, han, [this] { return !hang_.empty() || dong_; });  // (5)
        if (!duDieuKien) return Kq::hetGio;
        std::optional<T> v = layRa(lk);
        if (!v) return Kq::daDong;
        ra = std::move(*v);
        return Kq::co;
    }

    void dong() {                                        // (6) đóng: mọi luồng đang chờ phải biết
        {
            std::lock_guard<std::mutex> g(khoa_);
            dong_ = true;
        }
        khongDay_.notify_all();
        khongRong_.notify_all();
    }

private:
    // Gọi khi đang giữ khóa `lk`: lấy phần tử đầu nếu có, rồi nhả khóa và báo "có chỗ".
    std::optional<T> layRa(std::unique_lock<std::mutex>& lk) {
        if (hang_.empty()) return std::nullopt;
        std::optional<T> v(std::move(hang_.front()));
        hang_.pop_front();
        lk.unlock();
        khongDay_.notify_one();
        return v;
    }

    std::mutex khoa_;
    std::condition_variable khongDay_;
    std::condition_variable khongRong_;
    std::deque<T> hang_;
    std::size_t toiDa_;
    bool dong_ = false;
};

int main() {
    auto ms = [](int n) { return std::chrono::milliseconds(n); };
    {   // 1) 3 producer, 3 consumer; consumer không biết trước số việc, thoát khi pop() trả nullopt
        BoundedQueue<int> q(4);
        std::atomic<long long> tong{0}, dem{0};
        std::vector<std::thread> consumer, producer;
        for (int k = 0; k < 3; ++k) {
            consumer.emplace_back([&] {
                while (std::optional<int> v = q.pop()) { tong += *v; ++dem; }       // (7)
            });
        }
        for (int p = 0; p < 3; ++p) {
            producer.emplace_back([&q] { for (int i = 1; i <= 1000; ++i) q.push(i); });
        }
        for (std::thread& t : producer) t.join();
        q.dong();                                       // (8) mọi producer xong rồi mới đóng
        for (std::thread& t : consumer) t.join();
        std::cout << "tong = " << tong << ", so viec = " << dem << "\n";
    }
    {   // 2) đã đóng: việc còn lại vẫn lấy hết, push mới bị từ chối
        BoundedQueue<int> q(8);
        q.push(10); q.push(20); q.push(30);
        q.dong();
        std::cout << "push sau dong: " << (q.push(40) ? "nhan" : "tu choi") << "\n";
        int tong = 0, dem = 0;
        while (std::optional<int> v = q.pop()) { tong += *v; ++dem; }
        std::cout << "lay duoc " << dem << " viec, tong " << tong << "\n";
    }
    {   // 3) producer đang chờ vì hàng đầy; dong() đánh thức nó và push trả false
        BoundedQueue<int> q(1);
        q.push(1);
        bool ketQua = true;
        std::thread cho([&] { ketQua = q.push(2); });
        std::this_thread::sleep_for(ms(50));
        q.dong();
        cho.join();
        std::cout << "push(2) bi chan roi dong: " << (ketQua ? "nhan" : "tu choi") << "\n";
    }
    {   // 4) try_pop và pop_for
        BoundedQueue<int> q(4);
        auto ten = [](Kq k) { return k == Kq::co ? "co" : k == Kq::hetGio ? "het gio" : "da dong"; };
        int ra = 0;
        std::cout << "try_pop hang rong: " << (q.try_pop() ? "co" : "rong") << "\n";
        std::cout << "pop_for 30ms hang rong: " << ten(q.pop_for(ra, ms(30))) << "\n";
        q.push(7);
        std::cout << "pop_for sau push(7): " << ten(q.pop_for(ra, ms(30))) << " " << ra << "\n";
        q.dong();
        std::cout << "pop_for sau dong: " << ten(q.pop_for(ra, ms(5000))) << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Vị từ của producer có **hai vế**: còn chỗ **hoặc** đã đóng |
| (2) | Dậy mà đã đóng thì từ chối, trả `false`; việc chưa được bỏ vào hàng nên không có gì để dọn |
| (3) | Vị từ của consumer cũng hai vế: có việc **hoặc** đã đóng |
| `layRa` | Hàng rỗng thì trả rỗng (khi tới đây mà rỗng thì chỉ có thể là đã đóng, hoặc `try_pop` gọi lúc rỗng); còn thì lấy đầu hàng, nhả khóa, báo `khongDay_` |
| (4) | `try_pop` không `wait` gì cả: khóa, thử lấy, trả rỗng nếu rỗng |
| (5) | `wait_for` trả `false` nếu hết giờ mà vị từ vẫn sai; sai ở đây nghĩa là hàng rỗng và chưa đóng |
| (6) | `dong()` đổi `dong_` **dưới khóa**, rồi `notify_all` trên **cả hai** cv (producer đang chờ chỗ, consumer đang chờ việc) |
| (7) | Consumer lấy tới khi `pop` trả rỗng: hàng đóng **và** cạn |
| (8) | `main` chỉ gọi `dong()` sau khi mọi producer `join`: đóng sớm thì `push` của họ bị từ chối |

**Kết quả khi chạy:**

```text
tong = 1501500, so viec = 3000
push sau dong: tu choi
lay duoc 3 viec, tong 60
push(2) bi chan roi dong: tu choi
try_pop hang rong: rong
pop_for 30ms hang rong: het gio
pop_for sau push(7): co 7
pop_for sau dong: da dong
```

Mình biên dịch sạch cảnh báo (`-Wall -Wextra`, cả `-O2`), chạy 100 lần mỗi mức `-O` ra đúng 8 dòng đó, và TSan chạy 30 lần cũng đúng 8 dòng, không báo gì. Ba điều đáng nhìn. Một: thử nghiệm (3) cho `push(2)` ra `false` **dù nó đã kịp chặn hay chưa** (`sleep_for` chỉ để nó nhiều khả năng đã ngủ; kết quả không phụ thuộc vào điều đó). Hai: thử nghiệm (2) cho thấy `dong()` không làm mất việc đã nằm trong hàng. Ba: `pop_for` sau `dong()` ra ngay dù hạn là 5 giây, vì vị từ đã đúng.

`wait_for` có vị từ được chuẩn định nghĩa tương đương `wait_until` tới **một thời điểm cố định** (`steady_clock::now() + hạn`, tính một lần), nên spurious wakeup không kéo dài tổng thời gian chờ. Chuẩn không cho `wait_for` trả về vì hết giờ **sớm hơn** thời điểm đó; trả về trễ bao nhiêu thì tùy lập lịch. Test của mình kiểm kết quả, không kiểm số mili giây.

**Bản SAI 3: đổi cờ đóng mà không xin khóa (lost wakeup).** Nhiều người nghĩ `std::atomic<bool> dong_` thì khỏi cần khóa. Biến thì đúng là không race, nhưng nó vẫn **là biến điều kiện của `wait`**. Chương trình dưới thu nhỏ vấn đề: một consumer chờ trên hàng rỗng, `main` đóng **không khóa**. Mình cho vị từ ngủ 100 ms khi nó sai để **mở rộng khe hở** giữa "kiểm vị từ" và "ngủ trong `wait`" (khe hở thật chỉ cỡ nano giây):

```cpp
// bo-qua-kiem-tra
// (cần <atomic> <chrono> <condition_variable> <iostream> <mutex> <thread>)
std::mutex khoa;
std::condition_variable khongRong;
std::atomic<bool> dong{false};          // SAI: đổi mà không xin khóa (hàng luôn rỗng ở đây)

int main() {
    std::thread consumer([] {
        std::unique_lock<std::mutex> lk(khoa);
        khongRong.wait(lk, [] {
            bool xong = dong;
            if (!xong) std::this_thread::sleep_for(std::chrono::milliseconds(100));   // (1) mở rộng khe hở
            return xong;
        });
        std::cout << "consumer thoat\n";
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    dong = true;                        // (2) không khóa: rơi vào khe hở
    khongRong.notify_all();             // (3) consumer chưa ngủ nên chẳng ai nghe
    consumer.join();
    return 0;
}
```

Mình chạy: **5 lần trên 5 treo**, `timeout 3` mã **124**, không in gì; TSan cũng treo mã 124 và im lặng. Luồng consumer giữ khóa lúc kiểm vị từ (thấy `false`, đang ngủ 100 ms *trong vị từ*); dòng (2) đổi cờ **không cần khóa**, dòng (3) báo khi consumer **chưa ngủ trên cv**, rồi consumer ngủ và không còn ai báo.

Bản sửa chỉ đổi dòng (2) thành `{ std::lock_guard<std::mutex> g(khoa); dong = true; }`: mình chạy 3 lần, đều in `consumer thoat` (cả TSan). Vì mutex buộc `main` đợi tới khi consumer đã vào `wait` (nhả khóa) mới đổi được cờ, `notify` sau đó chắc chắn có người nghe. **Không** mở rộng khe hở: mình chạy 20000 vòng tạo/hủy, ba đợt, **0 lần treo**. Lỗi hiếm tới mức bài test thường không thấy, rồi treo ở môi trường sản xuất.

**Hai bản sai nhanh nữa** (mình chạy cả hai trên bài test của đề 2). SAI 4: `pop` thoát ngay khi `dong_` (dòng `if (dong_) return std::nullopt;` ngay sau `wait`), kể cả khi hàng còn việc. SAI 5: `dong()` chỉ gọi `khongRong_.notify_all()`, quên `khongDay_.notify_all()`.

Với SAI 4, chạy xong mà **không treo, không báo lỗi gì**, chỉ in kết quả sai: `lay duoc 0 viec, tong 0` (đúng phải là 3 việc, tổng 60). Đó là kiểu lỗi nguy hiểm nhất: im lặng làm mất việc. Với SAI 5, thử nghiệm (3) treo (mã 124, cả TSan): producer đang chờ chỗ trống không bao giờ biết hàng đã đóng.

### Phân tích chi phí và độ phức tạp

`push`, `pop`, `try_pop` đều O(1) mỗi lần cộng một lần khóa/nhả mutex (`deque::push_back` và `pop_front` không cấp phát lại cả khối như `vector`); bộ nhớ O(`toiDa`), đó là lý do có "giới hạn"; `pop_for` chờ bằng cách **ngủ** nên không tốn CPU; `dong()` đánh thức mọi luồng đang ngủ, hợp lý vì ai cũng cần biết.

Chi phí thật không nằm ở Big-O mà ở **tranh chấp một mutex và số lần đổi luồng** (bảng đo ở trên: sức chứa nhỏ chậm gấp chục lần). Producer và consumer cùng xếp hàng xin **một** khóa nên thông lượng bị chặn bởi nó; muốn nhanh hơn thì lấy nhiều việc một lần (consumer `pop` cả lô dưới một lần khóa), chia nhiều hàng (mỗi cặp một hàng), hay dùng hàng vòng lock-free cho đúng một producer và một consumer ([Bài 62](../nhom-8-da-luong-chieu-sau/62-lock-free-co-ban.md), bài toán khác, khó viết đúng hơn nhiều). Sức chứa là thông số cần đo: đủ lớn để hấp thụ lúc producer giật cục, nhưng consumer chậm hơn **mãi mãi** thì hàng nào cũng đầy, chỉ khác là đầy chậm hơn (đó chính là áp lực ngược).

## Go: channel có đệm làm sẵn gần hết

!!! info "Bạn biết Go?"
    Mình đã chạy Go 1.27 với `-race`, sạch. `make(chan int, 4)` chính là `BoundedQueue<int>` sức chứa 4: `ch <- v` là `push` (chờ khi đầy), `<-ch` là `pop` (chờ khi rỗng), và runtime lo hết cặp cv, vị từ, khóa. Khác biệt nằm ở **đóng** và **thời hạn**:

    - `close(ch)` thay `dong()`, và `for v := range ch` thoát khi channel **đóng và cạn**: đúng điều ta viết ở dòng (7). `v, ok := <-ch` trên channel đóng còn việc thì **vẫn trả việc còn lại** (`ok == true`), rồi mới `0, false`. Mình chạy: đóng khi còn 10, nhận ra `10 true`, rồi `0 false`.
    - Khác C++: **gửi vào channel đã đóng là panic** (`send on closed channel`, mình đã `recover` thử), trong khi `push` của ta trả `false` êm ái. Producer đang chặn trên channel đầy mà channel bị đóng cũng **panic** (mình chạy riêng, và `-race` còn báo data race vì `close` đồng thời với gửi): ở Go chỉ phía gửi được đóng, và đóng phải sau khi mọi người gửi xong.
    - `try_pop` là `select { case v := <-ch: ... default: ... }` (mình chạy: `try_pop: rong`); `pop_for` là `select` với `case <-time.After(30 * time.Millisecond)` (mình chạy: `pop_for: het gio`).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Viết `BoundedQueue<T>` an toàn luồng. Vì sao hai `condition_variable` mà không phải một?"
    Một mutex bảo vệ `std::deque<T>`. `push` chờ trên `khongDay` tới khi `size() < toiDa`, `push_back`, nhả khóa rồi `notify_one` trên `khongRong`; `pop` ảnh gương: chờ trên `khongRong` tới khi không rỗng, lấy, nhả khóa, `notify_one` trên `khongDay`. Hai cv vì có hai điều kiện và hai phe chờ: báo đúng phe thì không đánh thức nhầm.
    **Nối tiếp:** "Một cv thì sao?" Với `notify_one` thì có thể treo: mình chạy ra 10/10 treo ở sức chứa 1, vì chuông có thể chọn nhầm luồng cùng phe (consumer báo mà đánh thức consumer khác), người cần dậy vẫn ngủ. Một cv với `notify_all` thì đúng, nhưng đánh thức cả bầy rồi đa số ngủ lại.

??? question "Spurious wakeup và lost wakeup khác nhau thế nào? Vì sao `wait` luôn cần vị từ?"
    Spurious wakeup: `wait` trả về dù không ai notify; chuẩn cho phép, mình không tái hiện được trên máy này. Lost wakeup: `notify` chỉ đánh thức luồng **đang chờ**, nên báo lúc chưa ai chờ thì mất. Vị từ chữa cả hai (kiểm trước khi ngủ và sau mỗi lần dậy), cộng chữa chuyện "món bị lấy mất" mà `if` dính: mình chạy `if` ra SIGSEGV 10/10.
    **Nối tiếp:** "Mình đổi cờ `dong` bằng `atomic<bool>` và `notify_all` thì có cần khóa không?" Có: cờ là biến điều kiện của `wait`; đổi không khóa có thể rơi vào khe giữa lúc consumer kiểm vị từ (thấy sai) và lúc nó ngủ, thì tiếng báo mất (mình mở rộng khe hở bằng `sleep_for` trong vị từ: treo 5/5, mã 124).

??? question "Notify trong hay ngoài khóa?"
    Cả hai đều đúng theo chuẩn, vì trạng thái nằm trong biến dưới mutex chứ không nằm trong tiếng chuông. Ngoài khóa (nhả rồi mới báo) tránh việc luồng vừa dậy phải chờ khóa mà người báo còn giữ; mình đo hai bản trên máy mình, chênh lệch nằm trong nhiễu.
    **Nối tiếp:** "Có lúc nào bắt buộc notify trong khóa?" Khi luồng được đánh thức có thể hủy ngay chính cv hay hàng đợi (ví dụ nó là luồng cuối cùng và hủy đối tượng): báo sau khi nhả khóa khi đó chạm vào cv đã hủy. Cách tránh dễ nhất là `join` mọi luồng trước khi hủy hàng, như bài này.

??? question "Dừng sạch thế nào? Producer đang chờ chỗ trống thì sao?"
    `dong()`: đổi cờ `dong_` dưới khóa, rồi `notify_all` trên **cả hai** cv. `push` thấy đã đóng thì trả `false`; `pop` vẫn lấy hết việc còn lại, chỉ trả rỗng khi **đóng và cạn**. Chỉ gọi `dong()` sau khi mọi producer đã `join`, nếu không việc của họ bị từ chối.
    **Nối tiếp:** "Đóng rồi mà còn 1000 việc thì bỏ hay làm hết?" Là một quyết định thiết kế, phải nói rõ với người dùng: bài này làm hết (muốn bỏ thì thêm `dongNgay()`: xóa hàng rồi `dong()`; bài này không cài). Mình đã chạy bản sai "thoát ngay khi đóng": mất việc im lặng, `lay duoc 0 viec` thay vì 3. **Nối tiếp nữa:** "Dùng một giá trị đặc biệt (poison pill) để báo dừng được không?" Được, nhưng cần **một viên cho mỗi consumer**; bỏ một viên cho ba consumer thì chỉ một người thoát.

??? question "`try_pop` và `pop_for` dùng khi nào? `wait_for` có bị spurious wakeup kéo dài không?"
    `try_pop` khi luồng không được ngủ và có việc khác để làm lúc hàng rỗng (vòng lặp sự kiện, luồng giao diện). `pop_for` khi chờ được nhưng phải có giới hạn: để kiểm tra cờ hủy, gửi nhịp tim, hay báo lỗi "quá hạn". Cần ba kết quả (có, hết giờ, đã đóng) nên mình trả một `enum` và truyền kết quả qua tham chiếu.
    **Nối tiếp:** "Spurious wakeup có làm `wait_for` chờ lâu hơn hạn?" Không: `wait_for(lk, hạn, vịTừ)` được chuẩn định nghĩa bằng `wait_until` tới một thời điểm cố định tính một lần; dậy giả thì vị từ được kiểm lại và vẫn chờ tới thời điểm đó.

??? question "Producer nhanh hơn consumer mãi mãi thì sao? Chọn sức chứa bao nhiêu?"
    Hàng sớm hay muộn cũng đầy rồi producer bị chặn: đó là áp lực ngược, làm producer chạy chậm theo consumer, và là lý do hàng có giới hạn tốt hơn hàng không giới hạn (sẽ hết bộ nhớ). Sức chứa là thông số đo được: quá nhỏ thì hai bên đi từng bước (mình đo sức chứa 1 chậm gấp chục lần sức chứa 64); lớn hơn nữa chỉ hấp thụ lúc giật cục chứ không cứu được consumer chậm mãi.
    **Nối tiếp:** "Thread pool ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)) dùng hàng không giới hạn, đổi sang hàng này thì được gì?" `submit` bị chặn khi pool quá tải thay vì phình bộ nhớ; mất: `submit` có thể ngủ, nên không gọi từ luồng không được ngủ. [Bài 67](67-thread-pool-tu-viet.md) viết pool đó.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Viết `if` thay `while`, hoặc `wait` trần, và đổi cờ ngoài khóa"
    Trên bảng trắng người ta hay viết `if (hang.empty()) cv.wait(lk);` cho nhanh. Mình chạy: SIGSEGV 10/10. Cờ đóng cũng vậy: `atomic<bool>` mà không xin mutex khi đổi thì lost wakeup (treo, mã 124). Viết `cv.wait(lk, [&] { ... });` và đổi mọi biến điều kiện dưới cùng mutex.

!!! warning "Lỗi 2: `dong()` đóng nửa vời"
    Quên đánh thức một phía (producer đang chờ chỗ trống treo, mã 124), hoặc `pop` thoát khi `dong_` dù hàng còn việc (mất việc **im lặng**, `lay duoc 0 viec`). Luật: consumer thoát khi **đóng và cạn**; `dong()` báo cả hai cv bằng `notify_all`; và chỉ đóng sau khi mọi producer xong.

!!! warning "Lỗi 3: Khi nói, quên trả lời phần khó"
    Viết xong `push`/`pop` rồi dừng. Người phỏng vấn muốn nghe thêm: dừng sạch ra sao, chính sách khi đầy, hạn của `pop_for`, `pop` trả `T` thì nếu hàm tạo di chuyển ném ngoại lệ phần tử đã rời hàng (bài này giả định kiểu di chuyển không ném; `std::queue` tách `front` và `pop` vì lý do này). Cũng đừng trả `T&` tới phần tử rồi `pop_front()`: tham chiếu treo.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="66" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau: một cv chung, sức chứa 1, hai producer và hai consumer, vị từ đều đúng. Vì sao chương trình vẫn có thể treo?

```text
push: cv.wait(lk, [] { return hang.size() < 1; });  push_back(v);  cv.notify_one();
pop:  cv.wait(lk, [] { return !hang.empty(); });    pop_front();   cv.notify_one();
```

- Vì hai vị từ khác nhau không được dùng chung một mutex trong cùng một chương trình
- Vì `notify_one` gọi khi mình còn giữ khóa làm luồng được báo không bao giờ dậy được
- Vì `notify_one` có thể đánh thức nhầm một luồng cùng phe, người cần dậy vẫn ngủ
- Vì mỗi `condition_variable` chỉ nhận được đúng một lời báo trong suốt đời của nó

<p class="giai-thich" markdown>Với một cv chung, người chờ gồm cả producer lẫn consumer; `notify_one` chọn một trong số họ mà không biết ai cần. Nếu nó chọn nhầm (consumer báo mà đánh thức consumer khác, thấy hàng rỗng, ngủ lại), producer đáng lẽ phải dậy vẫn ngủ và cả nhóm kẹt; mình chạy ra treo mã 124. Dùng chung mutex cho nhiều vị từ hoàn toàn hợp lệ, miễn các vị từ đọc dữ liệu được mutex đó bảo vệ. Notify khi đang giữ khóa chỉ làm luồng dậy phải đợi một chút, không làm nó mất tiếng báo. Còn một cv nhận bao nhiêu lời báo cũng được, không có hạn mức một lần.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Ba consumer cần thoát sạch khi producer xong, và consumer không biết trước có bao nhiêu việc. Chọn cách nào, vì sao?

- Gọi `dong()`: cờ dưới khóa, `notify_all` hai cv; thoát khi hàng đóng và cạn
- Bỏ một phần tử đặc biệt như -1 vào hàng, consumer nào lấy được thì thoát cả nhóm
- Cho mỗi consumer ngủ một lúc rồi hỏi `empty()`; hễ thấy rỗng là thoát luôn
- Gọi `detach` cho cả ba consumer rồi để chương trình kết thúc vào lúc nào cũng được

<p class="giai-thich" markdown>Đóng hàng bằng cờ dưới khóa kèm `notify_all` đánh thức mọi consumer đang ngủ, và điều kiện "đóng và cạn" bảo đảm việc còn lại được làm hết. Một phần tử đặc biệt chỉ thoát **một** consumer, vì chỉ một người lấy được nó; muốn dùng thì phải bỏ một viên cho mỗi consumer. Ngủ rồi hỏi `empty()` có thể thấy rỗng đúng lúc producer chưa kịp bỏ việc tiếp, nên consumer thoát sớm và bỏ sót việc. Còn `detach` rồi để chương trình kết thúc làm luồng chạy tiếp trên dữ liệu đã bị hủy.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. Producer bỏ 5 việc vào hàng rồi gọi `dong()`; sau đó consumer mới bắt đầu chạy vòng `while (auto v = q.pop()) xuLy(*v);`. Consumer xử lý bao nhiêu việc?

```text
pop(): wait(lk, [] { return !hang.empty() || dong; });
       if (dong) return std::nullopt;
       lấy phần tử đầu rồi trả về nó
```

- Đủ 5 việc, vì `dong()` không xóa các việc đã nằm sẵn trong hàng đợi
- Đúng 1 việc, vì vòng lặp chỉ thoát sau khi `pop` lần đầu đã trả về một việc
- Treo, vì vị từ đòi hàng phải rỗng thì `wait` mới chịu thôi chờ và trả về
- Không việc nào: `pop` thấy đã đóng nên trả rỗng, chưa lấy phần tử nào

<p class="giai-thich" markdown>Vị từ đúng ngay (hàng không rỗng) nên `wait` không ngủ, rồi dòng `if (dong)` trả rỗng trước khi đụng tới hàng: 5 việc bị bỏ, im lặng. Đúng là `dong()` không xóa việc, nhưng `pop` này không bao giờ lấy chúng ra; sửa là kiểm `hang.empty()` thay vì `dong`. Ra đúng 1 việc cũng sai vì `pop` chưa lấy gì ở lần đầu. Và treo thì không: vị từ đúng, nên `wait` trả về ngay.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau: hàng rỗng, không ai `push`, không ai đóng. `r` bằng gì, và `wait_for` trả về lúc nào?

```text
bool r = cv.wait_for(lk, std::chrono::milliseconds(50),
                     [] { return !hang.empty() || dong; });
```

- `true` sau khoảng 50 ms, vì hết giờ nghĩa là điều kiện thôi chờ đã thỏa
- `false` ngay lập tức, vì vị từ đang sai và chẳng có luồng nào khác chờ
- `false` sau khoảng 50 ms, vì hết giờ mà vị từ vẫn còn đang sai
- Không trả về, vì không ai gọi `notify` nên luồng chờ mãi mãi

<p class="giai-thich" markdown>`wait_for` có vị từ trả về giá trị của vị từ lúc kết thúc; hết 50 ms mà vị từ vẫn sai thì trả `false`. Nó không trả ngay khi vị từ sai, vì lúc đó nó đi ngủ chờ thời hạn. Hết giờ không làm vị từ đúng, nên `true` là sai. Và việc không ai notify không làm nó chờ mãi: thời hạn chính là thứ đánh thức nó (mình chạy bản tương tự, ra `het gio`).</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Cờ đóng là `std::atomic<bool> dong_`. Vì sao `dong()` vẫn nên đổi nó dưới cùng mutex mà `wait` dùng?

- Consumer có thể vừa thấy vị từ sai mà chưa ngủ; báo ngay lúc đó thì lời báo mất
- `atomic<bool>` đọc ghi từ hai luồng vẫn bị coi là data race, nên TSan sẽ báo lỗi
- `notify_all` chỉ có tác dụng nếu luồng gọi nó đang giữ sẵn mutex của chính cv đó
- Vị từ của `wait` không đọc được biến `atomic`, nên cờ buộc phải là `bool` thường

<p class="giai-thich" markdown>Khe hở nằm giữa "kiểm vị từ, thấy sai" và "ngủ"; mutex buộc người đổi cờ đợi tới khi consumer đã ngủ (đã nhả khóa) rồi mới đổi, nên lời báo sau đó có người nghe. Mình mở rộng khe hở bằng `sleep_for` trong vị từ và thấy treo 5 lần trên 5. Còn atomic không phải data race, nên TSan im lặng. `notify_all` không đòi giữ khóa. Và vị từ đọc `atomic` bình thường, đây chỉ là chuyện đồng bộ chứ không phải kiểu dữ liệu.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Go: channel có đệm sức chứa 4 đang chứa 1 và 2, rồi `close(ch)`. Ba lần `v, ok := <-ch` liên tiếp cho ra gì?

- `0 false` ba lần liên tiếp, vì `close` xóa hết các việc còn nằm trong channel
- `1 true`, `2 true`, rồi `0 false`: việc đã vào vẫn nhận hết, sau đó mới hết
- `1 true`, `2 true`, rồi panic, vì nhận từ channel đã đóng và cạn là một lỗi
- Treo ngay từ lần đầu, vì channel đã đóng thì không cho nhận thêm gì nữa

<p class="giai-thich" markdown>Channel đóng vẫn giao nốt các giá trị đã nằm trong đệm (`ok` là `true`), chỉ sau khi cạn mới trả giá trị zero với `ok == false`: mình chạy ra đúng `1 true`, `2 true`, `0 false`. Đây cũng là hành vi ta cài cho `pop` (đóng và cạn mới trả rỗng); cách hiểu "đóng xóa việc" chính là bản SAI 4. Nhận từ channel đã đóng không panic (panic là khi **gửi** vào channel đã đóng), và cũng không treo.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `BoundedQueue<T>`: một mutex bảo vệ `deque`, **hai** cv (`khongDay` cho producer, `khongRong` cho consumer), mỗi điều kiện một vị từ đọc dưới mutex, `wait(lk, vịTừ)`; sau mỗi `push`/`pop` báo **bên kia**. Hai cv để gọi đúng phe: một cv với `notify_one` mình chạy ra treo 10/10 (sức chứa 1), một cv với `notify_all` thì đúng nhưng đánh thức cả bầy.
2. Ba thứ hỏng `wait`: spurious wakeup (chuẩn cho phép, mình không tái hiện), wakeup bị cướp (`if` thay `while`: SIGSEGV 10/10), lost wakeup (đổi cờ không khóa: treo mã 124, phải mở rộng khe hở mới thấy); chữa bằng vị từ cộng đổi biến dưới mutex. Notify trong hay ngoài khóa đều đúng, ngoài khóa thường được chọn, trong khóa khi luồng dậy có thể hủy cv.
3. Dừng sạch: `dong()` đổi cờ dưới khóa rồi `notify_all` **cả hai** cv; `push` sau khi đóng bị từ chối (và producer đang chờ chỗ nhận `false`); `pop` chỉ trả rỗng khi **đóng và cạn**; chỉ đóng sau khi mọi producer `join`. Quên một phía thì treo, thoát khi `dong_` mà còn việc thì mất việc im lặng.
4. `try_pop` không chờ (cho luồng không được ngủ); `pop_for` chờ có hạn qua `wait_for` có vị từ (≡ `wait_until` một thời điểm cố định, nên spurious wakeup không kéo dài hạn) và phân biệt ba kết quả: có, hết giờ, đã đóng.
5. Chi phí: mọi thao tác O(1), bộ nhớ O(`toiDa`), nhưng thời gian bị chi phối bởi tranh chấp một mutex và số lần đổi luồng (mình đo sức chứa 1 chậm hơn sức chứa 64 cỡ chục lần, đổi theo máy). Đầy thì chọn chính sách (chặn, chờ có hạn, từ chối, bỏ cũ nhất); luồng không được ngủ thì không dùng `push` chặn. Go: channel có đệm cùng `close`, `select` làm sẵn, nhưng gửi vào channel đã đóng là panic.
