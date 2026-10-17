# Bài 74 — Thực chiến: bộ hẹn giờ và giới hạn tốc độ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Viết trên bảng trắng một `BoHenGio` (scheduler) chạy việc đúng giờ: min-heap `priority_queue` theo mốc giờ, `cv.wait_until` trong một luồng nền, hủy việc, dừng sạch; kiểm bằng **thứ tự chạy** và một hạn chót rộng, không kiểm mili giây tuyệt đối.
    - Thấy vì sao `wait_until` có predicate mà chỉ nhìn cờ dừng là bản sai kinh điển (mình chạy: việc hẹn 20 ms bị trễ tới khoảng 400 ms mà thứ tự vẫn đúng), và phân biệt rõ **chuẩn bảo đảm gì** (`steady_clock` không đi lùi, dậy giả) với **máy này cho gì** (độ trễ đo được, TSan của g++ 11 báo sai ở `wait_until` trên `steady_clock`).
    - Viết **token bucket** an toàn luồng: nạp lười theo thời gian đã trôi, toàn số nguyên, chặn tràn số, và truyền nguồn giờ vào (inject) để test tất định bằng đồng hồ giả; thấy bản "kiểm rồi trừ bằng hai atomic" chấp nhận thừa yêu cầu dù TSan im lặng.
    - Trả lời các câu nối tiếp: chạy việc song song, việc lặp định kỳ, chờ thay vì từ chối, giới hạn theo từng người dùng, không dùng khóa; và nói khi nào **không** nên tự viết.

**Bạn cần biết trước:** [Bài 22](../nhom-2-stl-thuat-toan/22-bst-bang-bam-heap.md) (`priority_queue`, `greater`, min-heap), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`wait` với predicate, `notify`, `wait_for`/`wait_until`), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, hai biến phải đổi cùng nhau), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (mutex, TSan), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`chrono`, `sleep_for`, `join`), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (`std::function<void()>`, dừng êm), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`std::map`, `operator<` tự viết), [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (`using` bí danh), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (thứ tự dựng thành viên), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UBSan, tràn số có dấu).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn đẩy tờ giấy qua bàn: "Hai đề, cùng một chủ đề là thời gian. Đề một: viết cho tôi một bộ hẹn giờ. `hen(sau, viec)` chạy `viec` đúng giờ, `huy(id)` hủy được, tắt chương trình thì tắt sạch. Đề hai: viết một bộ giới hạn tốc độ, tối đa 100 yêu cầu mỗi giây nhưng cho dồn cục 20 cái. Và tôi muốn xem bạn **kiểm** chúng thế nào."

Quay lại **nhà bếp nhiều đầu bếp**. Đề một là **đồng hồ hẹn giờ bếp**: nhiều món hẹn nhiều giờ khác nhau, một đầu bếp phụ chỉ canh cái chuông **sắp reo sớm nhất**. Có người ghi thêm món "chín sau 1 phút" trong lúc phụ đang chờ chuông "10 phút": phụ phải **nhìn lại** hàng chuông, nếu không món 1 phút sẽ cháy. Đề hai là **thẻ vào cửa kho**: quầy phát một thẻ mỗi 100 ms, hộp chứa tối đa 5 thẻ, ai vào kho phải nộp một thẻ, hết thẻ thì bị từ chối.

!!! info "Chỗ nào ví von hết đúng?"
    Quầy thẻ thật có người đứng phát từng thẻ. Bộ giới hạn của ta **không có luồng nào phát thẻ**: nó chỉ tính "từ lần trước đã trôi bao lâu, đáng phát mấy thẻ" mỗi khi có người xin (mục 2). Đồng hồ hẹn giờ bếp thật cũng reo **đúng giây**; còn `wait_until` chỉ hứa không dậy-vì-hết-giờ **trước** mốc giờ, chứ không hứa dậy đúng mốc (bảng ở mục 1).

## 📖 Giải thích

### 1. Đề 1: `BoHenGio`, chạy việc đúng giờ

!!! example "Đề bài"
    Viết lớp `BoHenGio`, C++17, không thư viện ngoài. `hen(sau, viec)` trả một `id` và chạy `viec` **một lần** sau khoảng `sau` (mili-giây) kể từ lúc gọi, trên **một luồng nền**. Việc chạy theo thứ tự mốc giờ; bằng mốc thì theo thứ tự hẹn; không bao giờ chạy trước mốc. `huy(id)` trả `true` nếu việc chưa chạy (và từ nay không chạy). Hàm hủy dừng luồng nền, không treo; việc chưa tới giờ bị bỏ. Gọi từ nhiều luồng được, kể cả một việc tự gọi `hen`. Dùng `steady_clock`.
    **Đầu ra cần kiểm:** hẹn C lúc 150 ms, A lúc 50 ms, B lúc 100 ms (gọi theo thứ tự C, A, B) phải chạy ra `A B C`.

??? tip "Gợi ý 1"
    Luồng nền luôn cần biết "việc nào tới giờ **sớm nhất**". Cấu trúc nào lấy phần tử nhỏ nhất ra nhanh, và thêm vào cũng nhanh? Và nếu chưa tới giờ, luồng nền nên làm gì trong lúc chờ: ngủ-rồi-hỏi hay một cách rẻ hơn?

??? tip "Gợi ý 2"
    Heap (`priority_queue` với `greater`, như Bài 22) giữ mốc giờ; luồng nền ngủ bằng `cv.wait_until(lk, mốcGiờĐỉnh)`: ngủ tới mốc **hoặc** tới khi có người gọi. Nếu việc mới đến sớm hơn đỉnh hiện tại thì luồng nền phải được đánh thức và **tính lại**. Gợi ý nhỏ: sau mỗi lần dậy, đừng giả định gì, hãy xem lại mọi thứ từ đầu.

??? tip "Gợi ý 3"
    Heap không xóa được phần tử ở giữa. Cất nội dung việc trong một `std::map<id, việc>`, mốc giờ trong heap; `huy` chỉ xóa khỏi map. Khi luồng nền lấy đỉnh heap ra mà id không còn trong map thì bỏ qua ("xóa lười"). Chạy việc **ngoài khóa**, và dừng bằng cờ + `notify_all` + `join`.

**Hướng giải.** Luồng nền lặp: khóa, nhìn đỉnh, chưa tới giờ thì ngủ tới giờ đó, dậy thì làm lại từ đầu. Dậy có **ba lý do**: tới mốc giờ, có người báo (việc mới, hủy, dừng), hoặc dậy giả (Bài 27). Cách duy nhất đúng cho cả ba là **không phân biệt**: mỗi lần dậy đều đọc lại hàng đợi và đồng hồ. Đó là điểm người phỏng vấn muốn thấy.

Mốc giờ tính bằng đồng hồ nào? Chuẩn cho hai đồng hồ khác tính chất:

| | `steady_clock` | `system_clock` |
|---|---|---|
| Chuẩn bảo đảm | `is_steady == true`: không bao giờ đi lùi | Là giờ treo tường, có thể bị chỉnh tay hay đồng bộ lại; **không** bảo đảm đi đều |
| Hợp với | Đo khoảng, hẹn "sau bao lâu" | Ghi "lúc mấy giờ ngày nào" cho người đọc |
| Máy này (`is_steady` in ra) | `1` | `0` |

Hẹn "sau 50 ms" phải dùng `steady_clock`: nếu ai đó chỉnh giờ hệ thống lùi một tiếng, bộ hẹn dựa `system_clock` có thể chờ nhầm. (Mình **không** chạy thử chỉnh giờ, vì cần quyền quản trị; nên câu này dựa vào định nghĩa của chuẩn, không phải số đo.)

Hứa gì và không hứa gì về `wait_until`, đối chiếu với máy này:

| Chuẩn C++ nói | Chuẩn **không** nói | Máy này (g++ 11.4, x86-64, 8 luồng phần cứng) |
|---|---|---|
| `wait_until` trả `timeout` khi mốc đã tới; có thể trả về dù chưa tới (dậy giả) | Không hứa dậy **đúng** mốc: có thể trễ vì lập lịch | 50 việc cách nhau 10 ms: trễ so với mốc từ **60 µs** đến **4,3 ms** (ba lần chạy; đổi theo máy và độ bận) |
| `priority_queue` lấy đỉnh theo phép so sánh | **Không** hứa thứ tự giữa hai phần tử bằng nhau | Ta tự phá hòa bằng `id` (dòng (7)), không dựa vào chuyện máy này thường thế nào |
| `wait`/`wait_until` nhả khóa lúc ngủ và xin lại khi dậy | Không nói gì về công cụ kiểm như TSan | TSan của g++ 11 **báo sai** với `wait_until` trên `steady_clock` (mục "TSan báo sai") |

Hệ quả cho cách kiểm: **không** đòi "việc chạy đúng lúc 100 ms". Ta kiểm thứ tự (tất định), và một hạn chót rộng (250 ms cho việc hẹn 20 ms) chỉ để bắt lỗi trễ gấp chục lần, không đo độ chính xác.

!!! info "Bạn biết Go?"
    Go có sẵn bộ hẹn giờ trong runtime: `time.AfterFunc(d, f)` chạy `f` sau `d` trên goroutine riêng và trả `*Timer`; `t.Stop()` trả `true` nếu hủy được trước khi chạy, `false` nếu đã chạy hoặc đã hủy. Mình chạy Go 1.27.2 với ba việc 150/50/100 ms và hủy việc 100 ms: `Stop lan 1: true lan 2: false`, thứ tự chạy `A C`, đúng như `huy` ở dưới. Heap các timer và luồng canh nằm **trong runtime Go**, bạn không viết; ở C++ chuẩn không có timer nào, nên đề này mới là bài tập.

### 2. Đề 2: token bucket, giới hạn tốc độ

!!! example "Đề bài"
    Viết `ThungThe` (token bucket): chứa tối đa `dungLuong` thẻ, mỗi giây nhỏ thêm `tocDo` thẻ (số nguyên dương); lúc đầu đầy. `thu(n)` lấy `n` thẻ nếu **đủ** và trả `true`, không đủ thì trả `false` và không lấy gì. An toàn khi gọi từ nhiều luồng. **Không** được gọi `steady_clock::now()` thẳng trong lớp: nguồn giờ phải truyền vào để test tất định.
    **Ví dụ** (`dungLuong = 5`, `tocDo = 10`, đồng hồ giả đứng yên): 7 lần `thu()` liên tiếp ra `1 1 1 1 1 0 0`; tiến đồng hồ 100 ms thì `thu()` ra `1`.

??? tip "Gợi ý 1"
    Đừng viết luồng "mỗi 100 ms cộng một thẻ": thêm một luồng, thêm đồng bộ, và không test được. Hỏi ngược lại: khi có yêu cầu tới, ta cần biết gì để **tính** số thẻ đang có?

??? tip "Gợi ý 2"
    Cất hai thứ: số thẻ lúc tính lần cuối và mốc giờ của lần đó. Mỗi lần xin: thẻ mới = thẻ cũ + (thời gian trôi × tốc độ), chốt ở dung lượng. Hai thứ này phải đổi **cùng nhau**, nên một mutex hợp hơn hai atomic (Bài 28). Nguồn giờ là một hàm truyền vào.

??? tip "Gợi ý 3"
    Số thực làm kết quả test lệch ở chữ số cuối. Đếm thẻ bằng số nguyên: 1 thẻ = 10^9 "hạt", mỗi nano-giây trôi thêm `tocDo` hạt. Hỏi thêm: nếu máy rảnh một ngày thì phép nhân "thời gian × tốc độ" có tràn `long long` không?

**Hướng giải.** Mỗi lần xin làm bốn việc dưới khóa: đọc giờ, nạp lười, so, trừ. Không có luồng nền, không có đồng hồ ngầm, nên độ phức tạp là O(1) và bộ nhớ O(1) cho mỗi thùng. Chú ý hai bẫy: nạp mà quên chốt trần (khách nghỉ lâu rồi xả cả trăm yêu cầu một lúc), và nhân thời gian với tốc độ khi nghỉ rất lâu (tràn số, mục "Thử thay đổi" dưới đây).

Chọn thuật toán giới hạn, vì người phỏng vấn sẽ hỏi "sao không dùng cái khác":

| Thuật toán | Cho dồn cục? | Điểm mạnh | Điểm yếu |
|---|---|---|---|
| **Token bucket** (bài này) | Có, tới dung lượng | O(1), bộ nhớ O(1), tốc độ trung bình bị chặn | Dồn cục có thể làm hệ thống phía sau gặp đỉnh tải |
| Leaky bucket (xô rỉ) | Không: đầu ra đều | Làm phẳng tải | Yêu cầu đến dồn phải xếp hàng hoặc bị bỏ |
| Cửa sổ cố định (đếm trong mỗi giây) | Có, tùy ranh giới | Đơn giản nhất | Ở ranh giới hai cửa sổ có thể lọt gấp đôi giới hạn |
| Cửa sổ trượt (ghi mốc từng yêu cầu) | Có | Chính xác | Bộ nhớ O(giới hạn) mỗi người dùng |

!!! info "Bạn biết Go?"
    Go không có bộ giới hạn trong thư viện chuẩn; gói mở rộng `golang.org/x/time/rate` là một token bucket: `rate.NewLimiter(10, 5)` (10 thẻ/giây, dung lượng 5). Mình chạy: bảy lần `Allow()` liên tiếp ra `true true true true true false false`. Điểm hay: `AllowN(t, n)` nhận **thời điểm** `t` làm tham số, tức Go cũng chọn cách "truyền giờ vào" để test; mình gọi với `now+100ms` ra `true`. Đó đúng là ý của nguồn giờ truyền vào ở bài này.

## 💻 Ví dụ code

### Lời giải đề 1 và bộ kiểm

Chương trình dưới có ba phần: `BoHenGio`; `NhatKy` (nơi các việc ghi "tôi đã chạy", kèm `cho(n, hạn)` để `main` chờ đủ `n` dòng); và `main` chạy năm kịch bản. Lớp `NhatKy` ghi lại **thứ tự**, vì thứ tự là thứ chuẩn và thiết kế của ta bảo đảm; mili-giây thì không.

Cú pháp lạ: `#ifdef __SANITIZE_THREAD__ ... #else ... #endif` là chỉ thị cho **bộ tiền xử lý** (bước đầu của biên dịch, chọn đoạn code nào được dịch). g++ tự định nghĩa tên `__SANITIZE_THREAD__` khi biên dịch với `-fsanitize=thread`; mục "TSan báo sai" giải thích vì sao ta cần chỗ này. `std::greater<Muc>` đòi kiểu `Muc` có `operator>` (như `operator<` ở Bài 18).

```cpp
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <map>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#ifdef __SANITIZE_THREAD__
using DongHo = std::chrono::system_clock;   // (0) CHỈ khi chạy dưới TSan: lý do ở mục "TSan báo sai"
#else
using DongHo = std::chrono::steady_clock;   // (0) bản thật: đồng hồ không bao giờ đi lùi
#endif
using MocGio = DongHo::time_point;
using ms = std::chrono::milliseconds;

class BoHenGio {
public:
    using Id = long long;
    BoHenGio() : nen_([this] { chay(); }) {}                 // (1) luồng nền khởi động ở đây
    ~BoHenGio() { dung(); }

    Id hen(ms sau, std::function<void()> viec) {
        MocGio gio = DongHo::now() + sau;                    // (2) "sau bao lâu" thành "mốc giờ"
        std::lock_guard<std::mutex> g(khoa_);
        Id id = ++idCuoi_;
        viec_[id] = std::move(viec);                         // (3) nội dung việc, cất theo id
        hang_.push({gio, id});                               // (4) mốc giờ, cất vào heap
        cv_.notify_one();                                    // (5) đánh thức luồng nền: xem lại đỉnh
        return id;
    }
    bool huy(Id id) {
        std::function<void()> bo;                            // hàm bị hủy sẽ chết ở đây, SAU khi nhả khóa
        std::lock_guard<std::mutex> g(khoa_);
        auto it = viec_.find(id);
        if (it == viec_.end()) return false;                 // (6) không có trong map: đã chạy hoặc đã hủy
        bo = std::move(it->second);                          //     rút việc khỏi map: từ nay không ai chạy nó
        viec_.erase(it);
        return true;
    }
    void dung() {                                            // việc chưa tới giờ bị bỏ
        { std::lock_guard<std::mutex> g(khoa_); dung_ = true; }
        cv_.notify_all();
        if (nen_.joinable()) nen_.join();
    }

private:
    struct Muc {
        MocGio gio;
        Id id;
        bool operator>(const Muc& o) const {                 // (7) mốc sớm hơn lên đỉnh; bằng nhau: id nhỏ trước
            return gio != o.gio ? gio > o.gio : id > o.id;
        }
    };
    void chay() {
        std::unique_lock<std::mutex> lk(khoa_);
        while (!dung_) {                                     // (8) MỖI vòng xem lại mọi thứ từ đầu
            if (hang_.empty()) { cv_.wait(lk); continue; }   // (9) không có việc: ngủ tới khi có tin
            MocGio gio = hang_.top().gio;
            if (DongHo::now() < gio) {
                cv_.wait_until(lk, gio);                     // (10) ngủ tới mốc giờ HOẶC có tin
                continue;                                    // (11) dậy vì lý do gì cũng quay lại xem đỉnh
            }
            Id id = hang_.top().id;
            hang_.pop();
            auto it = viec_.find(id);
            if (it == viec_.end()) continue;                 // (12) đã bị hủy: bỏ qua
            std::function<void()> viec = std::move(it->second);
            viec_.erase(it);
            lk.unlock();                                     // (13) chạy việc NGOÀI khóa
            try { viec(); } catch (...) {}
            viec = nullptr;                                  // hàm và thứ nó bắt chết NGOÀI khóa
            lk.lock();
        }
    }
    std::mutex khoa_;
    std::condition_variable cv_;
    std::priority_queue<Muc, std::vector<Muc>, std::greater<Muc>> hang_;   // min-heap theo (gio, id)
    std::map<Id, std::function<void()>> viec_;
    Id idCuoi_ = 0;
    bool dung_ = false;
    std::thread nen_;                                        // PHẢI khai báo cuối: mọi thứ trên đã sẵn sàng
};

class NhatKy {                                               // chỗ các việc ghi lại "tôi đã chạy"
public:
    void ghi(const std::string& s) {
        std::lock_guard<std::mutex> g(khoa_);
        v_.push_back(s);
        cv_.notify_all();                                    // báo KHI ĐANG giữ khóa (xem mục "Thử thay đổi")
    }
    bool cho(std::size_t n, ms han) {                        // chờ đủ n dòng, tối đa `han`
        std::unique_lock<std::mutex> lk(khoa_);
        return cv_.wait_until(lk, DongHo::now() + han, [&] { return v_.size() >= n; });
    }
    std::string chuoi() {
        std::lock_guard<std::mutex> g(khoa_);
        std::string kq;
        for (const std::string& s : v_) kq += (kq.empty() ? "" : " ") + s;
        return kq;
    }
private:
    std::mutex khoa_;
    std::condition_variable cv_;
    std::vector<std::string> v_;
};

int main() {
    std::cout << "steady_clock::is_steady = " << std::chrono::steady_clock::is_steady
              << ", system_clock::is_steady = " << std::chrono::system_clock::is_steady << "\n";
    BoHenGio bo;
    {   // Đề 1: hẹn lộn xộn, chạy đúng thứ tự mốc giờ
        NhatKy nk;
        bo.hen(ms(150), [&] { nk.ghi("C"); });
        bo.hen(ms(50), [&] { nk.ghi("A"); });
        bo.hen(ms(100), [&] { nk.ghi("B"); });
        bool du = nk.cho(3, ms(3000));
        std::cout << "1. thu tu chay: " << nk.chuoi() << " (du 3 viec: " << du << ")\n";
    }
    {   // Đề 2: luồng nền đang ngủ chờ việc xa, rồi một việc SỚM HƠN tới
        NhatKy nk;
        bo.hen(ms(400), [&] { nk.ghi("muon"); });
        std::this_thread::sleep_for(ms(50));                 // để luồng nền chắc chắn đang ngủ chờ "muon"
        bo.hen(ms(20), [&] { nk.ghi("som"); });
        bool kip = nk.cho(1, ms(250));                       // hạn chót 250 ms, nhỏ hơn 400 ms của "muon"
        std::cout << "2. som chay truoc han chot 250 ms: " << (kip ? "co" : "khong") << "\n";
        nk.cho(2, ms(3000));
        std::cout << "   thu tu chay: " << nk.chuoi() << "\n";
    }
    {   // Đề 3: hủy việc
        NhatKy nk;
        BoHenGio::Id biHuy = bo.hen(ms(100), [&] { nk.ghi("bi-huy"); });
        BoHenGio::Id giu = bo.hen(ms(200), [&] { nk.ghi("giu"); });
        bool l1 = bo.huy(biHuy), l2 = bo.huy(biHuy);
        nk.cho(1, ms(3000));
        bool l3 = bo.huy(giu);
        std::cout << "3. huy lan 1: " << l1 << ", lan 2: " << l2 << ", huy sau khi da chay: " << l3
                  << ", da chay: " << nk.chuoi() << "\n";
    }
    {   // Đề 4: việc tự hẹn lại chính nó (chạy ngoài khóa nên gọi hen() được)
        NhatKy nk;
        int lan = 0;
        std::function<void()> tick = [&] {
            int n = ++lan;                                   // đọc `lan` TRƯỚC khi ghi: sau lần ghi cuối, main có thể đã dọn nó
            nk.ghi("tick" + std::to_string(n));
            if (n < 3) bo.hen(ms(40), tick);
        };
        bo.hen(ms(40), tick);
        nk.cho(3, ms(3000));
        std::cout << "4. tu hen lai: " << nk.chuoi() << "\n";
    }
    std::atomic<bool> xaDaChay{false};
    {   // Đề 5: hủy bộ hẹn giờ khi còn một việc hẹn 60 giây nữa
        BoHenGio rieng;
        rieng.hen(ms(60000), [&] { xaDaChay = true; });
    }
    std::cout << "5. huy bo hen gio khi con viec xa 60 giay: viec xa da chay = " << xaDaChay << "\n";
    return 0;
}
```

**Chạy từng dòng** (nói về `BoHenGio`; dòng `main` là kịch bản)

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (0) | Chọn đồng hồ: `steady_clock`, trừ khi chạy dưới TSan | `MocGio` là kiểu thời điểm của đồng hồ đó |
| (1) | Hàm tạo mở luồng nền ngay; `nen_` khai báo **cuối** nên khóa, cv, heap đã dựng xong (Bài 31) | luồng nền vào `chay()`, ngủ ở (9) |
| (2)-(5) | `hen`: đổi "sau bao lâu" thành mốc giờ, cất việc vào map, mốc vào heap, **đánh thức luồng nền** | heap có thêm một mục |
| (6) | `huy`: tìm `id` trong map; có thì rút việc ra khỏi map (trả `true`), không có thì trả `false`; mục trong heap để đó. Việc rút ra nằm trong `bo`, chết **sau** khi nhả khóa | `find` không thấy: đã chạy hoặc đã hủy |
| (7) | So sánh cho min-heap: mốc sớm hơn lên đỉnh, bằng mốc thì `id` nhỏ trước | thứ tự tất định |
| (8)-(11) | Vòng chính. Heap rỗng thì ngủ (9). Chưa tới giờ thì ngủ tới giờ (10), dậy vì **bất cứ lý do gì** thì `continue` về (8) xem lại đỉnh | đỉnh có thể đã đổi |
| (12) | Mục heap mà id không còn trong map là việc đã hủy: bỏ qua | không chạy gì |
| (13) | Mở khóa rồi mới chạy việc: việc được phép gọi `hen`/`huy`; `catch (...)` nuốt ngoại lệ để luồng nền không `terminate`; `viec = nullptr` cho hàm chết khi chưa xin lại khóa (mình thử: bỏ dòng này, rồi cho một đối tượng lambda bắt có hàm hủy gọi `huy`: treo, mã 124) | việc chạy không giữ khóa |

Bảng thời gian của kịch bản 2 (việc hẹn xa đang chờ, rồi việc sớm hơn đến):

| Lúc | Chuyện gì | Luồng nền |
|---|---|---|
| 0 ms | `hen(400, muon)` | dậy ở (9), chưa tới giờ, ngủ tới 400 ở (10) |
| 50 ms | `hen(20, som)`: mốc là 70 ms, **sớm hơn** đỉnh cũ; (5) báo | dậy, `continue`, đỉnh bây giờ là `som`, ngủ tới 70 |
| 70 ms | | dậy, tới giờ, lấy `som`, chạy ngoài khóa; rồi ngủ tới 400 |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -pthread`; cả chương trình mất khoảng 0,88 s):

```text
steady_clock::is_steady = 1, system_clock::is_steady = 0
1. thu tu chay: A B C (du 3 viec: 1)
2. som chay truoc han chot 250 ms: co
   thu tu chay: som muon
3. huy lan 1: 1, lan 2: 0, huy sau khi da chay: 0, da chay: giu
4. tu hen lai: tick1 tick2 tick3
5. huy bo hen gio khi con viec xa 60 giay: viec xa da chay = 0
```

Mình chạy 30 lần không TSan ở không tối ưu, 30 lần `-O2`, và 30 lần dưới TSan (`setarch x86_64 -R`): đầu ra giống hệt, TSan không báo gì, mã thoát 0. Các hạn chót rộng (cách mốc cần kiểm từ 50 ms trở lên) là lý do kết quả ổn định; trên máy bận hơn, lệch quá hạn thì dòng 2 có thể ra `khong` mà không có bug.

**Thử thay đổi 1: `wait_until` có predicate "chỉ nhìn cờ dừng".** Thay dòng (10) bằng đoạn dưới (đúng theo lời khuyên "luôn dùng predicate" của Bài 27, nhưng predicate quên điều kiện "đỉnh đổi"):

```cpp
// bo-qua-kiem-tra
cv_.wait_until(lk, gio, [&] { return dung_; });   // SAI: dậy vì notify, predicate sai, ngủ lại tới gio CŨ
```

Mình chạy ba lần: dòng 1 vẫn `A B C`, dòng 3 và 4 vẫn đúng, dòng 2 ra `som chay truoc han chot 250 ms: khong` (đủ cả ba lần), dù `thu tu chay` vẫn `som muon`. Việc `som` chạy lúc khoảng 400 ms thay vì 70 ms: luồng nền bị `notify` đánh thức, thấy predicate sai nên **ngủ tiếp tới mốc cũ** (400 ms), rồi mới lấy đỉnh (lúc này là `som`). TSan sạch vì không có data race: đây là lỗi logic. Bài học: **kiểm thứ tự không đủ**; muốn bắt lỗi này cần thêm một hạn chót.

**Thử thay đổi 2: bỏ dòng (5) `notify_one`.** Việc mới vào heap mà không ai đánh thức luồng nền: luồng nền đang ngủ ở (9) ngủ mãi. Mình chạy hai lần: mỗi `cho(..., 3000)` đợi hết 3 giây rồi bỏ cuộc, cả chương trình mất 9,5 s và 12,3 s (tùy việc đầu có kịp chạy trước khi luồng nền ngủ hay không), các dòng `thu tu chay` trống hoặc thiếu.

**Thử thay đổi 3: bỏ dòng `lk.unlock()` ở (13)** (chạy việc khi đang giữ khóa). Kịch bản 1 đến 3 vẫn đúng; kịch bản 4 treo: việc `tick` gọi `bo.hen`, và `hen` xin lại `khoa_` trong khi chính luồng nền đang giữ nó. `timeout 5` thoát mã **124**, cả bản thường lẫn TSan. Việc chạy trong khóa còn chặn mọi `hen`/`huy` từ luồng khác suốt thời gian nó chạy.

**Thử thay đổi 4: đưa `std::thread nen_` lên đầu danh sách thành viên.** Luồng nền chạy `chay()` khi `khoa_` và `dung_` chưa dựng: hành vi không xác định (Bài 31 đã nói thứ tự dựng là thứ tự **khai báo**). Mình chạy 20 lần thường: 19 lần thoát 0, 1 lần sập (mã 139). TSan 10 lần: cả 10 lần `data race` (mã 66) ở lệnh khóa mutex. UBSan 15 lần: không báo gì, nên đừng coi "công cụ im lặng" là bằng chứng. Chạy thường "được" 19/20 lần chính là lý do lỗi này sống lâu.

**Thử thay đổi 5: `NhatKy::ghi` báo `notify_all` sau khi nhả khóa** (như khuyên ở Bài 27). Mình chạy TSan 5 lần: 5 lần `data race` giữa `pthread_cond_destroy` (hàm hủy `NhatKy` trong `main`) và `pthread_cond_broadcast` (luồng nền, còn đang báo). `main` được đánh thức, thoát khối và **hủy** `NhatKy` trong lúc luồng nền chưa báo xong. Thường (không TSan) 5 lần đều thoát 0, nên không thấy. Báo **khi đang giữ khóa** thì người chờ chưa thể thoát `wait` để hủy `cv` (dòng `ghi` của listing). Bài 27 đã nhắc đúng ca này trong một câu ("giữ khóa lúc notify đôi khi lại cần, ví dụ khi luồng chờ sẽ hủy chính `cv`"), còn ở đây là bản chạy thật: "ngoài khóa đều đúng" chỉ nói về việc đánh thức, không nói về tuổi thọ của chính `cv`.

### TSan báo sai với `wait_until` trên `steady_clock`

Nếu bỏ `#ifdef` và luôn dùng `steady_clock`, chạy dưới TSan 5 lần mình được cả 5 lần mã **66** với `WARNING: ThreadSanitizer: double lock of a mutex` (ở `NhatKy::ghi`, khi `main` đang ở trong `wait_until`), kèm `data race` giả ở dòng sau. Code vẫn đúng: chạy thường 10 lần ra đúng đầu ra ở trên. Nguyên nhân giống [Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md) (đã đọc trong `nm -D`): `wait_until` trên `steady_clock` gọi `pthread_cond_clockwait`, mà `libtsan` của g++ 11 không bọc hàm này (thấy `U pthread_cond_clockwait` trong tệp chạy), nên TSan không biết `wait` nhả khóa lúc ngủ. Với `system_clock`, thư viện gọi `pthread_cond_timedwait` (có trong `nm -D`), TSan hiểu, và 30 lần chạy TSan đều sạch.

Cách xử lý ở đây là **chỉ khi chạy dưới TSan** mới đổi đồng hồ sang `system_clock` (dòng (0)). Điều này có nghĩa: lần chạy TSan **không kiểm** đường `steady_clock` của bản thật; phần khóa, heap, cờ dừng thì được kiểm. Đường `steady_clock` được kiểm bằng chạy thường (60 lần ở hai mức `-O`, đầu ra đúng). Không có cách "đúng hơn" mà vẫn dùng `wait_until` trên `steady_clock`; đây là giới hạn của công cụ, không phải lỗi của code.

### Lời giải đề 2 và đồng hồ giả

Chương trình dưới có `ThungThe` nhận nguồn giờ là `std::function<long long()>` (số nano-giây từ một mốc bất kỳ), `DongHoGia` chỉ chạy khi `tien(...)` gọi, và `main` kiểm tất định: một luồng, tám luồng khi đồng hồ **đứng yên**, tám luồng sau khi tiến đúng 1 giây giả, và một lần với đồng hồ thật. `static constexpr` là hằng số của cả lớp, tính lúc biên dịch (Bài 13). `std::invalid_argument` là kiểu lỗi để `throw` khi tham số sai (Bài 31). Ở đồng hồ thật, `now().time_since_epoch()` là khoảng thời gian từ mốc gốc của đồng hồ tới lúc này, và `duration_cast<nanoseconds>(...).count()` đổi nó thành số nano-giây.

```cpp
#include <atomic>
#include <chrono>
#include <functional>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

// Thùng thẻ (token bucket): chứa tối đa dungLuong thẻ, mỗi giây nhỏ thêm tocDo thẻ.
// Mỗi yêu cầu cần lấy đi n thẻ; không đủ thẻ thì bị từ chối (không chờ).
class ThungThe {
public:
    using NguonGio = std::function<long long()>;    // (0) trả số NANO-giây kể từ một mốc bất kỳ

    ThungThe(long long dungLuong, long long tocDo, NguonGio gio)
        : tran_(dungLuong * DON_VI), toc_(tocDo), gio_(std::move(gio)) {
        if (dungLuong <= 0 || tocDo <= 0) throw std::invalid_argument("dungLuong va tocDo phai > 0");
        con_ = tran_;                               // (1) bắt đầu với thùng đầy
        moc_ = gio_();
    }

    // Giả định: 0 <= n và n * 10^9 vừa `long long` (n tối đa cỡ 9·10^9); dungLuong cũng vậy.
    bool thu(long long n = 1) {
        std::lock_guard<std::mutex> g(khoa_);       // (2) đọc-sửa-ghi con_ và moc_ là MỘT bước
        napLai();
        long long can = n * DON_VI;
        if (con_ < can) return false;
        con_ -= can;
        return true;
    }

    // Còn bao nhiêu nano-giây nữa thì đủ n thẻ: 0 = đủ ngay, -1 = không bao giờ (n > dung lượng).
    long long choDen(long long n = 1) {
        std::lock_guard<std::mutex> g(khoa_);
        napLai();
        long long can = n * DON_VI;
        if (can > tran_) return -1;
        if (con_ >= can) return 0;
        return (can - con_ + toc_ - 1) / toc_;      // (3) làm tròn lên
    }

private:
    static constexpr long long DON_VI = 1000000000LL;   // (4) 1 thẻ = 10^9 "hạt": toàn số nguyên

    void napLai() {                                 // (5) gọi khi đang giữ khóa
        long long bay = gio_();
        long long troi = bay - moc_;
        if (troi <= 0) return;                      // đồng hồ đứng yên: không có gì để nạp
        moc_ = bay;
        long long thieu = tran_ - con_;
        if (troi > thieu / toc_) con_ = tran_;      // (6) nạp quá đầy: chốt ở trần (và không để nhân bị tràn số)
        else con_ += troi * toc_;                   // (7) mỗi nano-giây thêm tocDo hạt
    }

    std::mutex khoa_;
    const long long tran_;
    const long long toc_;
    NguonGio gio_;
    long long con_ = 0;
    long long moc_ = 0;
};

// Đồng hồ giả: chỉ chạy khi ta tiến nó.
struct DongHoGia {
    std::atomic<long long> ns{0};
    void tien(std::chrono::milliseconds d) {
        ns += std::chrono::duration_cast<std::chrono::nanoseconds>(d).count();
    }
    ThungThe::NguonGio nguon() {
        return [this] { return ns.load(); };
    }
};

// 8 luồng, mỗi luồng thử `moiLuong` lần; trả tổng số lần được chấp nhận.
long long thuSongSong(ThungThe& thung, int moiLuong) {
    std::atomic<long long> duoc{0};
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 8; ++k) {
        cacLuong.emplace_back([&] {
            for (int i = 0; i < moiLuong; ++i) {
                if (thung.thu()) ++duoc;
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();
    return duoc;
}

int main() {
    using std::chrono::milliseconds;
    {
        DongHoGia dh;
        ThungThe t(5, 10, dh.nguon());              // chứa 5 thẻ, nhỏ thêm 10 thẻ/giây (= 1 thẻ/100 ms)
        std::cout << "7 lan lien tiep luc dau:";
        for (int i = 0; i < 7; ++i) std::cout << ' ' << t.thu();
        std::cout << "\n";
        std::cout << "can cho them " << t.choDen() / 1000000 << " ms de co 1 the\n";
        dh.tien(milliseconds(99));
        std::cout << "sau 99 ms: " << t.thu() << ", can cho them " << t.choDen() / 1000 << " us\n";
        dh.tien(milliseconds(1));
        std::cout << "sau them 1 ms (tong 100 ms): " << t.thu() << ", roi lai: " << t.thu() << "\n";
        dh.tien(milliseconds(10000));
        int duoc = 0;
        while (t.thu()) ++duoc;
        std::cout << "nghi 10 giay roi xa: duoc " << duoc << " lan (khong qua 5 = dung luong)\n";
        std::cout << "xin 6 the mot lan: choDen = " << t.choDen(6) << " (-1 = khong bao gio)\n";
    }
    {
        DongHoGia dh;
        ThungThe t(1000, 100, dh.nguon());
        std::cout << "dong ho dung yen, 8 luong x 500 lan: duoc " << thuSongSong(t, 500) << " (dung luong 1000)\n";
        dh.tien(milliseconds(1000));                // 1 giây giả = nạp thêm đúng 100 thẻ
        std::cout << "tien 1 giay, 8 luong x 100 lan: duoc " << thuSongSong(t, 100) << " (toc do 100/giay)\n";
    }
    {
        auto that = [] {
            return std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
        };
        ThungThe t(3, 1, that);                     // đồng hồ thật: 3 thẻ, 1 thẻ/giây
        int duoc = 0;
        for (int i = 0; i < 10; ++i) duoc += t.thu();
        std::cout << "dong ho that, 10 lan lien tiep: duoc " << duoc << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (0)-(1) | Nguồn giờ là hàm truyền vào; hàm tạo ghi mốc giờ đầu và cho thùng **đầy** | `con_` = 5 thẻ (5·10^9 hạt) |
| (2) | `thu` khóa mutex: đọc-nạp-so-trừ là **một bước**, hai luồng không chen giữa | một luồng vào một lúc |
| (4)-(7) | `napLai`: `troi` ns trôi thì thêm `troi·tocDo` hạt; nạp quá đầy thì chốt ở trần; so với `thieu / toc_` để phép nhân không tràn | `con_ <= tran_` luôn đúng |
| (3) | `choDen`: thiếu bao nhiêu hạt thì cần bấy nhiêu ns, **làm tròn lên** (phép chia nguyên làm tròn xuống, nên cộng trước `toc_ - 1`: mẹo làm tròn lên) | 100 ms nếu cạn thẻ ở `tocDo = 10` |
| `main` | 7 lần: 5 lần thấy thẻ, 2 lần hết; tiến 99 ms vẫn thiếu 1 ms; tiến thêm 1 ms thì đủ đúng một thẻ | kết quả suy ra bằng tay được |

**Kết quả khi chạy:**

```text
7 lan lien tiep luc dau: 1 1 1 1 1 0 0
can cho them 100 ms de co 1 the
sau 99 ms: 0, can cho them 1000 us
sau them 1 ms (tong 100 ms): 1, roi lai: 0
nghi 10 giay roi xa: duoc 5 lan (khong qua 5 = dung luong)
xin 6 the mot lan: choDen = -1 (-1 = khong bao gio)
dong ho dung yen, 8 luong x 500 lan: duoc 1000 (dung luong 1000)
tien 1 giay, 8 luong x 100 lan: duoc 100 (toc do 100/giay)
dong ho that, 10 lan lien tiep: duoc 3
```

Mọi dòng suy ra được trên giấy, nên so sánh được: tám luồng tranh nhau mà tổng **luôn đúng 1000** rồi **đúng 100**; luồng nào được thẻ thì đổi theo lần chạy, nên bài không in. Mình chạy TSan 20 lần (đầu ra giống hệt bản thường, sạch, mã 0). Dòng cuối chạy cùng lớp với đồng hồ thật (3 thẻ, 1 thẻ/giây); ra `3` vì mười lần xin kéo dài vài micro-giây, chưa tới 1 giây. Dòng này chỉ chứng tỏ lớp chạy được với đồng hồ thật; mọi khẳng định về đúng sai nằm ở các dòng dùng đồng hồ giả.

**Thử thay đổi 6: bỏ phép chặn tràn số.** Thay hai dòng (6) và (7) bằng `con_ += troi * toc_; if (con_ > tran_) con_ = tran_;` (nhìn "đúng": cộng rồi chốt trần), rồi tạo `ThungThe(1000, 1000000, ...)`, xả cạn, tiến đồng hồ giả 24 giờ. Bản có chặn: `duoc 1000 lan`. Bản bỏ chặn: UBSan báo `signed integer overflow: 86400000000000 * 1000000 cannot be represented in type 'long long int'` và kết quả `duoc 0 lan`: sau một ngày nghỉ, thùng **từ chối mọi người**, ngược hẳn mong muốn. Chuẩn: tràn số có dấu là UB, nên con số `0` chỉ là điều máy này làm (cả `-O0` lẫn `-O2` đều ra `0`), không phải điều được hứa.

### Bản sai: hai atomic "kiểm rồi trừ"

Lời giải "không khóa" quen thuộc là `atomic<long long> con` với `if (con.load() >= 1) con.fetch_sub(1)`. Mỗi lệnh đều nguyên tử, nhưng kiểm và trừ là **hai bước**. Để lỗi hiện đều, mình dùng 200 000 thùng, mỗi thùng 1 thẻ, tám luồng xuất phát cùng lúc; đúng thì tổng được chấp nhận là đúng 200 000.

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

// SAI: kiểm và trừ là hai lệnh atomic rời nhau (đồng hồ đứng yên nên không nạp lại).
struct ThungSai {
    std::atomic<long long> con{1};
    bool thu() {
        if (con.load() >= 1) {          // (a) kiểm: thấy còn thẻ
            con.fetch_sub(1);           // (b) trừ: nhưng luồng khác có thể đã lấy mất thẻ đó
            return true;
        }
        return false;
    }
};

int main() {
    const int SO_THUNG = 200000;        // 200000 thùng, mỗi thùng 1 thẻ: đúng thì được chấp nhận đúng 200000 lần
    std::vector<ThungSai> thung(SO_THUNG);
    std::atomic<long long> duoc{0};
    std::atomic<bool> xuatPhat{false};
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 8; ++k) {
        cacLuong.emplace_back([&] {
            while (!xuatPhat) {}        // đợi hiệu lệnh để 8 luồng chạy gần như cùng lúc
            for (int i = 0; i < SO_THUNG; ++i) if (thung[i].thu()) ++duoc;
        });
    }
    xuatPhat = true;
    for (std::thread& th : cacLuong) th.join();
    std::cout << "duoc " << duoc << " (dung phai la " << SO_THUNG << ")\n";
}
```

Mình chạy 20 lần ở mỗi mức: không tối ưu ra từ **207 308** đến **443 507**, `-O2` từ **244 771** đến **476 962**; mọi lần đều thừa, nhiều lần gấp đôi. TSan 5 lần: **không báo gì** (218 459 đến 239 903), vì từng lệnh đều là atomic: đây là **race condition**, không phải data race (như `compare_exchange` ở Bài 28). Bản `ThungThe` ở trên, cùng bài kiểm 200 000 thùng (mỗi thùng một `ThungThe` đồng hồ đứng yên), chạy 20 lần đều ra đúng `200000`, và một lần dưới TSan cũng vậy. Bài học: TSan sạch **không** chứng minh đúng; cần một phép kiểm có đáp án biết trước.

### Chi phí

| | Đề 1: `BoHenGio` | Đề 2: `ThungThe` |
|---|---|---|
| Thời gian một thao tác | `hen`: O(log n) (đẩy heap và chèn map); `huy`: O(log n); lấy một việc ra: O(log n) | `thu`, `choDen`: O(1): một khóa, vài phép số nguyên, một lời gọi `std::function` |
| Bộ nhớ | O(n) việc; việc đã hủy vẫn nằm trong heap tới mốc của nó rồi mới bị bỏ ("xóa lười") | O(1) mỗi thùng |
| Tranh chấp | Một mutex cho cả bộ hẹn; việc chạy ngoài khóa nên không chặn `hen`/`huy` | Một mutex mỗi thùng; vùng găng chỉ vài ns |
| Hạn chế | Một luồng chạy việc: việc chậm làm trễ việc sau | Giới hạn trong **một tiến trình**, không qua nhiều máy |

`hen` nào cũng đánh thức luồng nền, kể cả khi việc mới không sớm hơn đỉnh (luồng nền dậy, thấy đỉnh không đổi, ngủ lại). Có thể chỉ báo khi mốc mới **sớm hơn** đỉnh để bớt một lượt dậy, nhưng đúng sai ở đây rất mong manh; mình không làm vì không đo thấy cần.

**Khi nào không tự viết:** nếu dự án đã có thư viện vòng lặp sự kiện (`asio`, `libuv`) hay `timerfd` của Linux thì dùng chúng. Cần hàng triệu timer chính xác thì bánh xe thời gian (timer wheel) thay heap. Giới hạn qua nhiều máy thì token bucket phải nằm ở **kho chung**, không phải trong bộ nhớ một tiến trình.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Bộ hẹn giờ của bạn chạy việc nặng 2 giây thì sao? Làm sao chạy song song?"
    Với một luồng nền, việc nặng chặn mọi việc sau nó: chúng trễ tới 2 giây. Cách chữa: luồng nền chỉ **canh đồng hồ**; tới giờ thì không chạy việc mà `submit` nó vào thread pool (Bài 30; [Bài 67](67-thread-pool-tu-viet.md) xây kỹ). Cái giá: các việc **bắt đầu** theo thứ tự mốc giờ nhưng **kết thúc** không còn theo thứ tự đó, và thread pool phải sống lâu hơn bộ hẹn.

??? question "Làm việc lặp lại mỗi 100 ms thế nào? Có trôi giờ không?"
    Cho việc tự gọi `hen` lại như `tick` ở kịch bản 4. Nhưng `hen(100 ms)` tính từ **bây giờ**, nên mỗi vòng cộng thêm thời gian chạy việc và độ trễ lập lịch (vài chục µs tới vài ms, bảng ở mục 1): giờ **trôi** dần. Muốn không trôi thì thêm `henLuc(mốcGiờ, viec)` và việc lặp hẹn lại ở `mốcGiờ + chuKy`, tính từ mốc **dự kiến** chứ không từ `now()`. Bản của mình chưa có `henLuc`.

??? question "Sao dùng `steady_clock` mà không phải `system_clock`? Dậy giả thì sao?"
    `steady_clock` không bao giờ đi lùi (`is_steady`), nên "sau 50 ms" luôn là khoảng thật; `system_clock` có thể bị chỉnh nên hợp để ghi giờ treo tường chứ không để hẹn khoảng. Dậy giả và dậy vì việc mới đều xử lý bằng một cách: vòng `while` ở (8) đọc lại đỉnh và đồng hồ mỗi lần dậy, không tin lý do dậy. Đó là lý do bản sai ở "Thử thay đổi 1" sai.

??? question "Hết thẻ thì chờ cho tới khi có thẻ, thay vì từ chối, làm sao?"
    `choDen(n)` cho biết còn bao lâu: `while (!thung.thu(n)) std::this_thread::sleep_for(std::chrono::nanoseconds(thung.choDen(n)));` (xử lý riêng kết quả `-1`: `n` lớn hơn dung lượng thì không bao giờ đủ). Vẫn phải **thử lại** sau khi ngủ vì luồng khác có thể lấy mất thẻ vừa nạp. Cách này không công bằng giữa các luồng chờ (không ai xếp hàng); muốn công bằng thì dùng hàng đợi. Với dịch vụ web, thường trả luôn `chờ tới X ms` cho khách thử lại.

??? question "Mỗi người dùng một giới hạn riêng, hàng triệu người, làm sao?"
    Một `unordered_map<UserId, ThungThe>` chia shard như [Bài 72](72-concurrent-hashmap.md), xin thùng của người đó rồi `thu`. Quan sát hay: thùng **đầy và nhàn rỗi** giống hệt một thùng mới, nên xóa nó khỏi map được mà không đổi kết quả; nhờ vậy bộ nhớ chỉ theo số người **đang dùng**. Nhớ rằng thùng nằm trong map thì thao tác `thu` phải giữ thùng sống (dùng `shared_ptr`, Bài 10) khi nơi khác dọn dẹp.

??? question "Làm token bucket không khóa được không? Hai atomic được không?"
    Hai atomic (số thẻ, mốc giờ) **không đủ**: hai biến phải đổi cùng nhau (mục "Bản sai" cho thấy lỗi tương tự, và Bài 28 cũng thế). Hướng nói được ở mức nguyên lý: gộp trạng thái thành **một** số (ví dụ "thời điểm thùng sẽ đầy lại", gọi là GCRA) rồi `compare_exchange` trong vòng lặp. Mình **không cài** hướng này ở bài, nên chỉ nêu ý. Thực tế mutex đủ: vùng găng chỉ vài ns, và lock-free hiếm khi đáng độ khó ([Bài 62](../nhom-8-da-luong-chieu-sau/62-lock-free-co-ban.md)).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `wait_until` có predicate mà predicate chỉ nhìn cờ dừng"
    Viết trên bảng trắng rất tự nhiên vì "luôn dùng predicate". Kết quả mình chạy: thứ tự đúng, nhưng việc hẹn sớm bị trễ từ 70 ms tới khoảng 400 ms. Predicate phải trả lời "có lý do gì để dừng ngủ **không**" gồm cả "đỉnh đã đổi"; hoặc viết vòng `while` như (8) và `wait_until` không predicate.

!!! warning "Lỗi 2: Chạy việc khi đang giữ khóa, hoặc quên `notify` khi thêm việc"
    Chạy việc trong khóa: việc nào gọi `hen` là treo (mã 124) và mọi `hen`/`huy` khác bị chặn. Quên `notify_one` trong `hen`: luồng nền ngủ mãi, `main` đợi cả chục giây. Cả hai đều chạy ra ngay khi thử, nên hãy **nói to** hai câu này khi viết.

!!! warning "Lỗi 3: Test bằng giờ thật và mong khớp mili-giây, hoặc dùng số thực đếm thẻ"
    `sleep_for(100ms)` rồi mong có đúng một thẻ: `sleep_for` có thể ngủ lâu hơn, nên số thẻ lệch tùy máy; giờ giả cho kết quả đúng từng nano-giây. Số thực (`double`) đếm thẻ làm tổng lệch ở chữ số cuối, và test bằng `==` thất bại ngẫu nhiên. Nguồn giờ truyền vào và số nguyên (hạt) tránh cả hai.

!!! warning "Lỗi 4: Coi 'TSan sạch' là 'đúng', hoặc 'TSan báo' là 'sai'"
    Bản hai atomic: TSan sạch mà thừa tới gấp đôi. Bản `steady_clock` đúng: TSan báo `double lock` sai. Cả hai chiều đều là lỗi. Dùng công cụ để **tìm**, dùng bài kiểm có đáp án biết trước để **chứng minh**, và đối chiếu báo cáo với code trước khi tin.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="74" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. Luồng nền đang ngủ tới `gio` = 400 ms. Lúc 50 ms, một việc hẹn 20 ms sau được thêm và `hen` gọi `notify_one`. Việc mới chạy lúc nào?

```text
cv_.wait_until(lk, gio, [&] { return dung_; });
continue;   // vòng while (!dung_) ở ngoài
```

- Khoảng 70 ms, vì `notify_one` làm `wait_until` trả về và luồng nền lấy ngay việc mới
- Khoảng 400 ms, vì predicate sai nên `wait_until` ngủ tiếp tới mốc `gio` cũ
- Không bao giờ, vì predicate không nhìn heap nên việc mới bị bỏ sót
- Khoảng 20 ms, vì `wait_until` tính lại mốc giờ mỗi lần có `notify`

<p class="giai-thich" markdown>Dạng `wait_until(lk, mốc, pred)` tương đương vòng "dậy, kiểm `pred`, sai thì ngủ tiếp tới **cùng mốc**"; `notify` chỉ làm nó dậy kiểm lại, còn `pred` chỉ hỏi `dung_` nên vẫn sai. Việc mới vì thế chờ tới 400 ms, rồi mới được lấy lên (nó vẫn chạy, chỉ trễ). Nói chạy lúc 70 ms là đúng với bản `wait_until` không predicate, nơi vòng ngoài xem lại đỉnh. Việc không bị bỏ sót: nó nằm trong heap. Và `wait_until` không bao giờ tự tính lại mốc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Bộ hẹn giờ phải chạy việc "sau 30 giây" đúng ý ngay cả khi quản trị viên chỉnh đồng hồ hệ thống lùi 1 giờ giữa chừng. Nên tính mốc giờ bằng đồng hồ nào?

- `system_clock`, vì nó khớp với giờ treo tường mà người dùng nhìn thấy
- `system_clock`, vì được đồng bộ với máy chủ giờ nên chính xác hơn
- Cả hai như nhau, vì `wait_until` tự bù khi giờ hệ thống đổi
- `steady_clock`, vì chuẩn bảo đảm nó không đi lùi khi chỉnh giờ

<p class="giai-thich" markdown>`steady_clock` có `is_steady == true`: chỉ đi tới, nên "30 giây" là khoảng thật. `system_clock` là giờ treo tường và có thể bị chỉnh, đúng thứ ta đang lo; chuyện nó khớp giờ người nhìn hay được đồng bộ chính là lý do nó nhảy. Không có gì trong chuẩn bảo đảm `wait_until` tự bù thay đồng hồ bị chỉnh. Nên với mốc hẹn dạng khoảng, chọn đồng hồ không đi lùi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Đọc đoạn sau. Đồng hồ giả đứng yên, thùng 5 thẻ, nạp 10 thẻ/giây, lúc đầu đầy. Chương trình in ra gì?

```text
ThungThe t(5, 10, gio);
int a = 0;  for (7 lan) a += t.thu();
gio.tien(250 ms);
int b = 0;  while (t.thu()) ++b;
in a, b
```

- `5 2`, vì 250 ms nạp thêm 2,5 thẻ và chỉ phần nguyên được dùng
- `5 3`, vì 2,5 thẻ được làm tròn lên thành 3 thẻ dùng được
- `5 5`, vì thùng được nạp đầy lại sau một khoảng nghỉ đủ dài
- `7 0`, vì cả 7 lần đầu đều được nên không còn thẻ để nạp

<p class="giai-thich" markdown>Bảy lần đầu: 5 thẻ có sẵn nên 5 lần được, 2 lần bị từ chối (`a = 5`), thùng cạn. 250 ms nạp 2,5 thẻ; `thu` cần trọn một thẻ nên được hai lần (còn 0,5 thẻ), lần thứ ba thiếu. Làm tròn lên cho ra ba lần là sai vì thẻ chưa đủ; mình đã chạy ra `5 2`. Nạp đầy lại cần 500 ms (5 thẻ ở 10 thẻ/giây), không phải 250 ms. Và dung lượng chỉ 5 nên không thể được 7 lần.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Bạn cần test "sau 100 ms thì có thêm đúng một thẻ" cho token bucket. Cách nào cho test tất định?

- Dùng `steady_clock` thật, `sleep_for(100ms)` rồi kiểm số thẻ
- Dùng `steady_clock` thật nhưng kiểm bằng "khoảng từ 0 tới 2 thẻ" cho an toàn
- Truyền vào nguồn giờ giả, tiến đúng 100 ms rồi kiểm số thẻ
- Chạy test 1000 lần rồi lấy giá trị hay gặp nhất làm đáp án

<p class="giai-thich" markdown>Nguồn giờ giả chỉ đổi khi test bảo nó đổi, nên "sau đúng 100 ms" là một con số chính xác và kết quả lặp lại được. `sleep_for` có thể ngủ lâu hơn mong muốn nên số thẻ đổi theo máy và độ bận. Nới khoảng kiểm cho "an toàn" thì test không còn bắt được lỗi (lệch một thẻ vẫn qua). Chạy nhiều lần lấy số hay gặp thì che lỗi chứ không chứng minh đúng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** `huy(id)` của `BoHenGio` (dùng heap + map) làm gì với việc đã hẹn?

- Xóa mục khỏi heap, tốn O(log n) và giải phóng chỗ ngay lập tức
- Xóa việc khỏi map; mục trong heap ở lại tới mốc của nó rồi bị bỏ qua
- Chỉ đặt cờ "đã hủy", còn nội dung việc vẫn nằm trong map tới khi chạy
- Gọi `viec` ngay với tham số "hủy" để nó tự dọn dẹp rồi mới xóa

<p class="giai-thich" markdown>`priority_queue` không cho xóa phần tử ở giữa, nên `huy` chỉ xóa việc khỏi map (và nhờ đó hủy cả nội dung); khi mục heap lên đỉnh, luồng nền không tìm thấy `id` trong map và bỏ qua: "xóa lười". Xóa khỏi heap là điều thư viện chuẩn không có sẵn. Đặt cờ rồi giữ nội dung trong map là một thiết kế khác, không phải bản này (và giữ đồ thừa, nặng nếu việc bắt nhiều dữ liệu). Còn `huy` không chạy việc: hủy tức là không chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau. Dòng `lk.unlock()` bị xóa khỏi vòng `chay()`, và việc `tick` có thân `bo.hen(ms(40), tick)`. Điều gì xảy ra khi `tick` chạy?

```text
std::unique_lock<std::mutex> lk(khoa_);
...
viec();            // chạy khi vẫn giữ khoa_
```

- `hen` chờ khóa tới khi `viec` xong, rồi chạy tiếp bình thường
- `hen` ném ngoại lệ vì khóa đã bị giữ bởi một luồng khác
- `hen` mượn khóa của luồng nền nên chạy được, vì cùng một luồng
- Luồng nền treo, vì `hen` xin lại `khoa_` mà chính nó đang giữ

<p class="giai-thich" markdown>`tick` chạy trên luồng nền, đang giữ `khoa_`; lời gọi `hen` xin cùng mutex đó từ chính luồng này, mà `std::mutex` thường không cho khóa hai lần: luồng tự chờ chính mình mãi (mình chạy: `timeout` mã 124). Nó không "chờ rồi chạy tiếp" vì thứ nó chờ là chính nó. Không có ngoại lệ nào được hứa, và mutex không "mượn" theo luồng. Chạy việc ngoài khóa là cách tránh.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Token bucket "không khóa" dùng `if (con.load() >= 1) { con.fetch_sub(1); return true; }`. Chạy TSan thì sao, và đúng hay sai?

- TSan sạch nhưng vẫn chấp nhận thừa, vì kiểm và trừ là hai bước rời
- TSan báo data race ở `fetch_sub`, vì hai luồng cùng ghi một biến
- TSan sạch và kết quả đúng, vì mọi thao tác đều là atomic
- TSan báo lock-order-inversion, vì thiếu thứ tự khóa giữa hai thao tác

<p class="giai-thich" markdown>Mỗi lệnh là atomic nên không có data race, TSan im lặng; nhưng giữa `load` và `fetch_sub` luồng khác có thể lấy mất thẻ, nên thùng bị trừ quá (mình chạy: thừa tới gấp đôi). Data race chỉ báo khi hai truy cập thường vào cùng ô nhớ không đồng bộ; hai truy cập atomic thì không. Không phải thao tác nào atomic cũng ghép lại thành đúng. `lock-order-inversion` là chuyện hai mutex ngược thứ tự, không có mutex nào ở đây.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Hai việc có cùng mốc giờ chính xác nằm trong `priority_queue` chỉ so sánh theo mốc giờ. Việc nào chạy trước?

- Việc hẹn trước, vì `priority_queue` giữ thứ tự thêm vào khi bằng nhau
- Việc hẹn sau, vì phần tử thêm mới luôn nổi lên đỉnh khi bằng nhau
- Chuẩn không hứa; muốn chắc phải tự phá hòa, ví dụ so thêm `id`
- Cả hai chạy cùng lúc, vì `priority_queue` cho phép lấy nhiều đỉnh

<p class="giai-thich" markdown>Chuẩn chỉ đòi đỉnh là phần tử lớn nhất theo phép so sánh; giữa hai phần tử bằng nhau nó không hứa thứ tự, nên dựa vào điều máy này thường làm là sai. Vì vậy `operator>` ở dòng (7) so thêm `id`, và thứ tự giữa các mốc bằng nhau trở thành tất định theo thiết kế. Không có chuyện "giữ thứ tự thêm vào": đó là tính chất của hàng đợi `queue`, không phải `priority_queue`. Phần tử thêm sau cũng không tự nổi lên đỉnh khi bằng nhau. Và mỗi `top` chỉ lấy một phần tử.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Bộ hẹn giờ = min-heap theo `(mốc giờ, id)` + `cv.wait_until` + luồng nền; mỗi lần dậy (tới giờ, có tin, hay dậy giả) đều **xem lại đỉnh và đồng hồ** từ đầu; `wait_until` có predicate chỉ nhìn cờ dừng cho thứ tự đúng nhưng việc sớm trễ cả trăm ms (mình chạy: `khong` ba lần trên ba).
2. Hủy bằng map + "xóa lười", chạy việc **ngoài khóa** (trong khóa thì việc gọi `hen` là treo, mã 124), dừng bằng cờ + `notify_all` + `join`, và `std::thread` khai báo **cuối** lớp; hẹn khoảng thì dùng `steady_clock`.
3. Kiểm bằng thứ tự chạy và hạn chót rộng, không bằng mili-giây: chuẩn không hứa dậy đúng mốc (máy này trễ 60 µs tới 4,3 ms), và TSan g++ 11 báo sai với `wait_until` trên `steady_clock` nên lần chạy TSan dùng `system_clock` và nói rõ điều đó.
4. Token bucket = nạp lười (thẻ += thời gian trôi × tốc độ, chốt trần), toàn số nguyên, chặn tràn số (bản không chặn: UBSan báo, kết quả `0`), một mutex cho cả hai biến, nguồn giờ truyền vào để test tất định bằng đồng hồ giả.
5. Hai atomic "kiểm rồi trừ" vẫn thừa yêu cầu tới gấp đôi dù TSan im lặng, còn mutex luôn ra đúng 200 000: **TSan sạch không chứng minh đúng**; khi cần nói thêm hãy nêu chạy song song bằng pool, việc định kỳ không trôi, chờ thay vì từ chối, và khi nào không tự viết.
