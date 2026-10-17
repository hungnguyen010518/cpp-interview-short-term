# Bài 70 — Thực chiến: khóa đọc-ghi và triết gia ăn tối

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Tự viết được `RWLock` (khóa đọc-ghi) bằng `mutex` + `condition_variable` trên bảng trắng, với hai chính sách **ưu tiên đọc** và **ưu tiên ghi**, và so được với `std::shared_mutex`.
    - **Chứng minh đói ghi bằng một kịch bản tất định** (không dựa may rủi về thời gian), rồi nói rõ chuẩn C++ hứa gì còn máy này (g++ 11, glibc) cho kết quả gì.
    - Giải bài **triết gia ăn tối** (ở đây: đầu bếp và dao): tái hiện bản deadlock, rồi sửa bằng thứ tự khóa, `std::scoped_lock` và giới hạn N−1 người ngồi; nói được vì sao mỗi cách đúng và chạy nhiều vòng để kiểm.
    - Phân biệt "chạy nhiều lần không treo" (bằng chứng) với "không có vòng chờ" (chứng minh), và nhận ra các bẫy hay lọt: kiểm-rồi-đặt bằng `atomic`, xin khóa đọc lồng nhau, nâng khóa đọc lên khóa ghi.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`, `vector<thread>`, `std::ref`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, `unique_lock`, TSan), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (bốn điều kiện deadlock, thứ tự khóa cố định, `scoped_lock`), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable` với predicate, `notify_all`), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic`). [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) đã nói về `shared_mutex` và đói ghi, [Bài 69](69-semaphore-barrier-tu-cai.md) viết semaphore; ở đây ta tự gói lại những gì cần.

## 🧠 Câu chuyện mở đầu

Vòng hai, người phỏng vấn đẩy tờ giấy qua bàn: "Bạn có 45 phút, hai đề, viết trên bảng trắng và nói to suy nghĩ." Đề một lấy từ nhà bếp quen thuộc của Bài 25: **sổ công thức dán trên tường**. Nhiều đầu bếp đứng đọc cùng lúc thì được; nhưng đầu bếp trưởng muốn **sửa** sổ thì phải đợi mọi người đọc xong và đuổi họ ra, rồi sửa một mình. Viết cái "khóa đọc-ghi" đó.

Đề hai: bàn tròn có **5 đầu bếp** và **5 con dao** đặt giữa họ (mỗi con dao nằm giữa hai người cạnh nhau). Muốn nấu một món, đầu bếp cần **cả hai con dao** hai bên. Ai cũng cầm dao bên trái trước rồi mới với dao bên phải thì chuyện gì xảy ra, và sửa thế nào? (Bài toán gốc kể bằng triết gia và đũa; ta dùng đầu bếp và dao.)

!!! info "Chỗ nào ví von không còn đúng?"
    Đầu bếp thật nhìn thấy nhau, biết nhường và xin lỗi; luồng thì chỉ biết đứng chờ, và g++ không tự gỡ deadlock cho bạn. Thêm nữa, dao thật không có "tên" còn mutex thì có địa chỉ và ta đánh số được: chính nhờ vậy cách "thứ tự khóa" mới dùng được.

## 📖 Giải thích

### Đề A: `ReadWriteLock` tự viết, ưu tiên đọc hay ưu tiên ghi

**Đề bài.** Viết lớp `RWLock` với bốn hàm: `lock_shared()` / `unlock_shared()` (đọc) và `lock()` / `unlock()` (ghi). Đặt đúng các tên này để `std::shared_lock<RWLock>` và `std::unique_lock<RWLock>` bọc (RAII) được.

- Ràng buộc: nhiều người đọc cùng lúc; người ghi vào thì **không ai khác** ở trong; chỉ dùng `mutex`, `condition_variable` và số nguyên.
- Đầu vào kiểm tra: 2 luồng ghi (mỗi luồng 2000 lần tăng `a` rồi `b`), 4 luồng đọc (mỗi luồng 5000 lần kiểm `a == b`). Đầu ra: `a = 4000, b = 4000, vi pham = 0`.
- Thêm: viết **cả hai chính sách**; chứng minh ưu tiên đọc gây **đói ghi**; so với `std::shared_mutex`.

??? tip "Gợi ý 1: cần đếm những gì?"
    "Ai đang ở trong sổ" chỉ có hai khả năng: **một số người đọc** hoặc **đúng một người ghi**. Nhớ số người đọc ở trong và cờ "có người ghi ở trong", tất cả dưới một `mutex`.

??? tip "Gợi ý 2: điều kiện chờ và ai đánh thức ai"
    Người đọc chờ khi có người ghi ở trong; người ghi chờ khi có người ghi **hoặc** người đọc ở trong. Dùng một `condition_variable` với predicate ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)); có người được vào thêm khi người ghi ra hoặc người đọc **cuối cùng** ra. Dùng `notify_all` vì người chờ có cả hai loại.

??? tip "Gợi ý 3: thêm một con số để chọn chính sách"
    Đếm thêm **số người ghi đang xếp hàng**. Ưu tiên đọc: người đọc chỉ nhìn "có người ghi **ở trong** không". Ưu tiên ghi: còn nhìn "có người ghi **đang chờ** không" và nhường. Hai chính sách khác nhau đúng một vế của một điều kiện.

**Hướng giải.** Bảng dưới là toàn bộ thuật toán (`dangDoc` = số người đọc ở trong, `dangGhi` = có người ghi ở trong, `ghiCho` = số người ghi đang chờ):

| Hàm | Chờ tới khi | Rồi làm | Đánh thức ai |
|---|---|---|---|
| `lock_shared` | `!dangGhi` (ưu tiên ghi: thêm `ghiCho == 0`) | `++dangDoc` | không |
| `unlock_shared` | không chờ | `--dangDoc` | nếu về 0: `notify_all` |
| `lock` | `!dangGhi && dangDoc == 0` (trong lúc chờ: `ghiCho` tăng 1) | `dangGhi = true` | không |
| `unlock` | không chờ | `dangGhi = false` | `notify_all` |

Đói ghi xảy ra ở ưu tiên đọc: người ghi cần `dangDoc == 0`, mà nếu người đọc mới gối đầu người đọc cũ thì `dangDoc` không bao giờ chạm 0. Để **chứng minh**, đừng chạy hàng trăm luồng rồi hy vọng: ta dựng kịch bản gối đầu trong một luồng, kết quả không phụ thuộc may rủi.

### Đề B: triết gia ăn tối (đầu bếp và dao)

**Đề bài.** `N = 5` đầu bếp ngồi quanh bàn tròn, giữa hai người cạnh nhau có một con dao (5 dao). Đầu bếp `i` cần dao `i` (bên trái) và dao `(i + 1) % 5` (bên phải) để nấu một món; nấu xong thì đặt hai dao xuống.

- Ràng buộc: mỗi con dao chỉ một người cầm tại một lúc (mỗi dao là một `std::mutex`); không ai bỏ ngang giữa chừng.
- Yêu cầu: (1) viết bản **ai cũng cầm trái rồi phải** và cho thấy nó deadlock; (2) sửa bằng ba cách: thứ tự khóa, `std::scoped_lock`, chỉ cho **N−1** người ngồi; (3) chạy nhiều vòng để kiểm.
- Đầu ra kiểm tra (mỗi đầu bếp nấu đủ số bữa và mỗi dao được dùng đúng `2 × số bữa` lần): một dòng "tat ca xong dung so bua" cho mỗi cách.

??? tip "Gợi ý 1: vì sao kẹt?"
    Đối chiếu bốn điều kiện của [Bài 26](../nhom-3-da-luong/26-deadlock.md). Cả năm người cùng cầm dao trái thì mỗi người giữ một dao và chờ dao của người bên cạnh: vòng chờ 0 → 1 → 2 → 3 → 4 → 0. Muốn hết kẹt, phá một điều kiện.

??? tip "Gợi ý 2: phá vòng chờ bằng số thứ tự"
    Đánh số dao 0 đến 4, ai cũng **cầm dao số nhỏ trước**. Đầu bếp 4 có dao trái 4 và dao phải 0 nên cầm 0 rồi 4 (đảo thứ tự). Chuỗi chờ luôn đi từ số nhỏ sang số lớn nên không khép vòng được.

??? tip "Gợi ý 3: hai cách còn lại"
    Cách thứ hai: xin cả hai dao **một lần** (`std::scoped_lock`), tức phá "giữ-và-chờ". Cách thứ ba: chỉ cho tối đa 4 người ngồi vào bàn. Vòng chờ cần **cả năm** người cùng giữ dao trái; chỉ có 4 người thì bàn có một ghế trống, và con dao nằm cạnh ghế trống không ai tranh, nên chuỗi chờ đứt ở đó: người sát ghế trống lấy được dao, nấu xong, nhả dao cho người kế bên. Cần một bộ đếm có chờ (semaphore) cho 4 ghế.

**Hướng giải.** Ba cách phá ba chỗ khác nhau của vòng chờ:

| Cách | Phá điều kiện nào | Giá phải trả | Chọn khi |
|---|---|---|---|
| Thứ tự khóa (dao số nhỏ trước) | Chờ vòng tròn | Không tốn thêm; cần quy ước thứ tự chung | Sửa được chỗ xin khóa và có số thứ tự rõ: rẻ, dễ chứng minh |
| `std::scoped_lock(trái, phải)` | Giữ-và-chờ | Cơ chế bên trong do thư viện, chuẩn không quy định | Cần hai khóa một lúc và khó có thứ tự toàn cục: ngắn nhất |
| Giới hạn N−1 ghế | Không phá trực tiếp: **không đủ người để khép vòng** | Thêm một điểm chung mà mọi đầu bếp phải qua | Không sửa được chỗ xin khóa nhưng kiểm soát được ai được vào |

## 💻 Ví dụ code

### Lời giải A: `RWLock` hai chính sách, kiểm đúng-sai và kịch bản đói ghi

`template <bool UuTienGhi>` là một "công tắc" cố định lúc biên dịch: `RWLock<false>` (ưu tiên đọc) và `RWLock<true>` (ưu tiên ghi) là hai lớp sinh ra từ cùng một khuôn. `std::this_thread::yield()` nhường lõi CPU cho luồng khác; ta dùng nó để kéo dài khoảng giữa `++a` và `++b`, cho lỗi (nếu có) dễ lộ. Hàm `try_lock_shared()` là "thử vào, không chờ": trả `true` nếu vào được, `false` nếu sẽ phải chờ. Hàm `doiXep` có hai bản cùng tên (một bản mẫu cho `RWLock`, một bản thường cho `std::shared_mutex`); trình biên dịch chọn bản khớp với kiểu khóa được truyền vào.

```cpp
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <shared_mutex>
#include <thread>
#include <vector>

// Khóa đọc-ghi tự viết. UuTienGhi = false: ưu tiên đọc; true: ưu tiên ghi.
template <bool UuTienGhi>
class RWLock {
    std::mutex m_;
    std::condition_variable cv_;
    int dangDoc_ = 0;        // số người đọc đang ở trong
    bool dangGhi_ = false;   // có người ghi đang ở trong
    int ghiCho_ = 0;         // số người ghi đang xếp hàng chờ

    bool duocDoc() const { return !dangGhi_ && (!UuTienGhi || ghiCho_ == 0); }   // (1)

public:
    void lock_shared() {                                                         // đọc: vào
        std::unique_lock<std::mutex> lk(m_);
        cv_.wait(lk, [this] { return duocDoc(); });
        ++dangDoc_;
    }
    bool try_lock_shared() {                                                     // đọc: thử, không chờ
        std::lock_guard<std::mutex> lk(m_);
        if (!duocDoc()) return false;
        ++dangDoc_;
        return true;
    }
    void unlock_shared() {                                                       // đọc: ra
        std::lock_guard<std::mutex> lk(m_);
        if (--dangDoc_ == 0) cv_.notify_all();                                   // (2)
    }
    void lock() {                                                                // ghi: vào
        std::unique_lock<std::mutex> lk(m_);
        ++ghiCho_;                                                               // (3)
        cv_.wait(lk, [this] { return !dangGhi_ && dangDoc_ == 0; });
        --ghiCho_;
        dangGhi_ = true;
    }
    void unlock() {                                                              // ghi: ra
        std::lock_guard<std::mutex> lk(m_);
        dangGhi_ = false;
        cv_.notify_all();
    }
    int ghiCho() {                                                               // chỉ để kiểm tra
        std::lock_guard<std::mutex> lk(m_);
        return ghiCho_;
    }
};

// Bài kiểm tra đúng-sai: người ghi tăng a rồi b; người đọc kiểm tra a == b.
template <class L>
void kiemTra(const char* ten) {
    L rw;
    int a = 0, b = 0;                              // chỉ đụng tới khi đang giữ khóa
    int viPham[4] = {0, 0, 0, 0};
    std::vector<std::thread> ds;
    for (int w = 0; w < 2; ++w)
        ds.emplace_back([&] {
            for (int i = 0; i < 2000; ++i) {
                std::unique_lock<L> lk(rw);        // (4) ghi
                ++a;
                std::this_thread::yield();         // nhường lõi: mở rộng cửa sổ lỗi
                ++b;
            }
        });
    for (int r = 0; r < 4; ++r)
        ds.emplace_back([&, r] {
            for (int i = 0; i < 5000; ++i) {
                std::shared_lock<L> lk(rw);        // (5) đọc
                if (a != b) ++viPham[r];
            }
        });
    for (std::thread& t : ds) t.join();
    std::cout << ten << ": a = " << a << ", b = " << b << ", vi pham = "
              << viPham[0] + viPham[1] + viPham[2] + viPham[3] << "\n";
}

// Đợi tới khi chắc chắn người ghi đã xếp hàng. Khóa của ta tự hỏi được; shared_mutex thì chỉ đoán bằng giờ.
template <bool U> void doiXep(RWLock<U>& rw) { while (rw.ghiCho() == 0) std::this_thread::yield(); }
void doiXep(std::shared_mutex&) { std::this_thread::sleep_for(std::chrono::milliseconds(100)); }

// Kịch bản "người đọc gối đầu", chạy trong MỘT luồng đọc nên kết quả tất định.
template <class L>
void kichBan(const char* ten) {
    L rw;
    std::atomic<bool> ghiVao{false};
    rw.lock_shared();                                    // (6) người đọc đầu tiên vào trước
    std::thread ghi([&] {
        rw.lock();                                       // (7) người ghi tới, phải chờ
        ghiVao = true;
        rw.unlock();
    });
    doiXep(rw);                                          // (8) chắc chắn người ghi đã xếp hàng
    int giaoCa = 0;
    while (giaoCa < 1000 && rw.try_lock_shared()) {      // (9) người đọc mới xin vào...
        rw.unlock_shared();                              // (10) ...rồi người đọc cũ ra
        ++giaoCa;
    }
    std::cout << ten << ": " << giaoCa << " lan giao ca, ghi da vao: " << (ghiVao ? "roi" : "chua") << "\n";
    rw.unlock_shared();                                  // (11) người đọc cuối cùng ra
    ghi.join();                                          // người ghi giờ mới vào được và xong
}

int main() {
    kiemTra<RWLock<false>>("uu tien doc ");
    kiemTra<RWLock<true>>("uu tien ghi ");
    kiemTra<std::shared_mutex>("shared_mutex");
    kichBan<RWLock<false>>("uu tien doc ");
    kichBan<RWLock<true>>("uu tien ghi ");
    kichBan<std::shared_mutex>("shared_mutex");
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái (`dangDoc`, `dangGhi`, `ghiCho`) |
|---|---|---|
| (1) | Một người đọc được vào khi không có người ghi ở trong; riêng ưu tiên ghi còn đòi không có người ghi đang chờ | |
| (2) | Chỉ người đọc **cuối cùng** mới đánh thức: người ghi đang chờ `dangDoc == 0` | |
| (3) | Người ghi báo "tôi đang xếp hàng" **trước khi** ngủ chờ; nhờ vậy (1) mới thấy được người ghi chờ | `ghiCho` 0 → 1 |
| (4), (5) | `unique_lock<L>` gọi `lock()`/`unlock()`, `shared_lock<L>` gọi `lock_shared()`/`unlock_shared()`: chỉ cần `L` có đủ các tên đó | |
| (6)–(8) | Kịch bản: người đọc đầu tiên vào; luồng ghi gọi `lock()` và ngủ; luồng chính đợi tới khi `ghiCho() == 1` | (1, không, 1) |
| (9), (10) | Người đọc mới vào (+1) rồi người cũ ra (−1): lúc nào cũng có ít nhất một người đọc ở trong | (1, không, 1) lặp lại |
| (11) | Người đọc cuối ra: `dangDoc` về 0, `notify_all`, người ghi mới vào được | (0, có, 0) |

**Kết quả khi chạy** (`-O1` hay `-O2`, ba lần liền đều y hệt; với `-fsanitize=thread`: sạch cảnh báo, mã thoát 0):

```text
uu tien doc : a = 4000, b = 4000, vi pham = 0
uu tien ghi : a = 4000, b = 4000, vi pham = 0
shared_mutex: a = 4000, b = 4000, vi pham = 0
uu tien doc : 1000 lan giao ca, ghi da vao: chua
uu tien ghi : 0 lan giao ca, ghi da vao: chua
shared_mutex: 1000 lan giao ca, ghi da vao: chua
```

Đọc kết quả. Ưu tiên đọc: người đọc mới vào được 1000 lần liên tiếp trong lúc người ghi chờ, người ghi **không vào được** (đó là đói ghi; vòng lặp chỉ dừng vì ta tự dừng ở 1000, và `join` ở dòng (11) cho thấy người ghi vào ngay khi người đọc cuối ra). Ưu tiên ghi: người đọc mới bị chặn ngay lần đầu (0 lần giao ca). Ba dòng đầu cho thấy cả ba khóa đều đúng về loại trừ lẫn nhau.

**Chuẩn nói gì, máy này cho gì.** Dòng `shared_mutex` ở kịch bản là kết quả của g++ 11 / glibc (mình chạy 30 lần, 30 lần y hệt); riêng ở đây việc đợi người ghi xếp hàng là ngủ 100 ms nên là thử nghiệm xác suất, không tất định như hai khóa của ta.

| Chuyện | Chuẩn C++ | g++ 11 / glibc trên máy này |
|---|---|---|
| Ai vào trước khi có người ghi chờ | Không quy định ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md)) | `shared_mutex` cho người đọc mới vào (như "ưu tiên đọc") |
| Luồng đã giữ khóa đọc xin khóa đọc lần hai | Không được phép (hành vi không xác định) | `shared_mutex`: qua được; `RWLock<true>`: treo (xem bản sai 2) |
| Giữ khóa đọc rồi xin khóa ghi ("nâng cấp") | Không được phép (hành vi không xác định) | `shared_mutex`: treo (`timeout 3` mã 124) |

**Thử thay đổi 1: bỏ `notify_all` ở `unlock_shared` (dòng (2)).** Mình chạy 3 lần: cả ba lần treo (`timeout 10`, mã 124): người ghi đang ngủ chờ `dangDoc == 0` mà không ai đánh thức nó.

**Thử thay đổi 2: đổi `notify_all` thành `notify_one` trong `unlock()`.** Mình chạy 6 lần: 4 lần treo, và luôn treo ở khóa **ưu tiên ghi** (khóa ưu tiên đọc vẫn qua). Lý do: người đọc đang chờ thấy `ghiCho_ > 0` nên ngủ tiếp, mà tiếng chuông duy nhất đã bị nó tiêu, còn người ghi thật không được báo. Vì người chờ thuộc **hai loại**, `notify_all` là lựa chọn an toàn.

#### Bản SAI 1: "dùng `atomic` cho nhanh" (kiểm rồi mới đặt)

Đây là phiên bản người ta hay viết trên bảng trắng: hai biến `atomic`, không `mutex`. Từng thao tác trên `atomic` đều nguyên tử, nhưng **"kiểm rồi mới đặt" là hai thao tác**: người đọc và người ghi có thể cùng thấy "chưa ai" rồi cùng vào.

```cpp
// bo-qua-kiem-tra
class RWLockSai {                                    // SAI: "dùng atomic cho nhanh"
    std::atomic<int> dangDoc_{0};
    std::atomic<bool> dangGhi_{false};
public:
    void lock_shared() {
        while (dangGhi_) std::this_thread::yield();                   // (1) thấy chưa ai ghi...
        ++dangDoc_;                                                   // (2) ...rồi mới báo "tôi đang đọc"
    }
    void unlock_shared() { --dangDoc_; }
    void lock() {
        while (dangDoc_ > 0 || dangGhi_) std::this_thread::yield();   // (3) thấy chưa ai đọc, ghi...
        dangGhi_ = true;                                              // (4) ...rồi mới báo "tôi đang ghi"
    }
    void unlock() { dangGhi_ = false; }
};
```

Mình thay `RWLock<false>` bằng `RWLockSai` trong `kiemTra` (chạy riêng, `-O1`). Tám lần chạy cho `vi pham` là 2965, 19999, 406, 20000, 19998, 0, 11, 19998 (tối đa 20000 lần đọc). Lần ra 0 (kèm `a = b = 4000`) trông như đúng, và năm trong tám lần còn ra `a` hoặc `b` **nhỏ hơn 4000**, tức mất cả lần tăng vì hai người ghi cùng vào. Dưới TSan: `WARNING: ThreadSanitizer: data race` (đọc `a != b` song song với `++a`/`++b`), mã thoát 66. Sửa đúng là gộp "kiểm" và "đặt" vào **cùng một vùng găng** dưới `mutex` như lời giải.

#### Bản SAI 2: khóa đọc lồng nhau với chính sách ưu tiên ghi

Hàm đọc ngoài đang giữ khóa đọc và gọi một hàm đọc trong, hàm này lại xin khóa đọc. Nếu **đúng lúc đó** có người ghi xếp hàng, ưu tiên ghi chặn lần xin thứ hai, mà người ghi lại chờ lần thứ nhất nhả: luồng tự chờ chính mình.

```cpp
// bo-qua-kiem-tra
int main() {
    RWLock<true> rw;                                     // ưu tiên ghi (lớp ở trên)
    rw.lock_shared();                                    // (1) hàm đọc ngoài đang giữ khóa đọc
    std::thread ghi([&] { rw.lock(); rw.unlock(); });    // (2) người ghi tới, xếp hàng
    while (rw.ghiCho() == 0) std::this_thread::yield();
    rw.lock_shared();                                    // (3) hàm đọc trong xin khóa đọc LẦN HAI
    std::cout << "qua duoc\n";                           // (4) không bao giờ tới đây
    return 0;
}
```

Mình chạy (cùng lớp `RWLock`, `-O1`): không in gì, `timeout 3` thoát mã **124**; dưới TSan cũng không có báo cáo nào và vẫn mã 124, vì không có dữ liệu bị tranh chấp, chỉ có vòng chờ. Đổi `RWLock<true>` thành `RWLock<false>` (và thêm hai `unlock_shared()` cùng `ghi.join()` cuối hàm cho đủ) thì in `qua duoc`, nhưng đó là may theo chính sách; chuẩn không cho xin lại. Bài học: đừng xin khóa đọc lồng nhau; hàm trong nên nhận dữ liệu từ hàm ngoài (đã khóa sẵn) thay vì tự khóa lại.

**Chi phí và độ phức tạp.** Mỗi thao tác O(1) cộng việc ngủ/dậy; bộ nhớ O(1). `notify_all` đánh thức **mọi** người chờ rồi họ tranh nhau lại `mutex`: với k người chờ tốn O(k) lần thức dậy mà chỉ vài người vào được. Mỗi lần đọc vẫn qua `m_` một lúc ngắn, nên các lần đọc chỉ song song **trong vùng đọc**; với vùng đọc rất ngắn, khóa đọc-ghi không nhanh hơn `mutex` thường ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) đã đo `shared_mutex`).

### Lời giải B: ba cách chữa, chạy nhiều vòng

`enum class Cach` ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)) liệt kê ba cách. `Semaphore` ở dưới là bộ đếm có chờ viết bằng `mutex` + `condition_variable` (dạng giống ở [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md), [Bài 69](69-semaphore-barrier-tu-cai.md)). Mặc định chương trình chạy hai cách đầu; chạy kèm đối số bất kỳ thì chạy cách "bớt một người" (lý do ở phần TSan bên dưới).

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

constexpr int N = 5;                         // 5 đầu bếp quanh bàn, 5 con dao giữa họ

struct Dao {
    std::mutex khoa;
    int lanDung = 0;                         // chỉ đụng tới khi đang cầm dao
};

class Semaphore {                            // bộ đếm có chờ, tự viết từ mutex + cv
    std::mutex m_;
    std::condition_variable cv_;
    int dem_;
public:
    explicit Semaphore(int dem) : dem_(dem) {}
    void acquire() {
        std::unique_lock<std::mutex> lk(m_);
        cv_.wait(lk, [this] { return dem_ > 0; });
        --dem_;
    }
    void release() {
        std::lock_guard<std::mutex> lk(m_);
        ++dem_;
        cv_.notify_one();
    }
};

struct Ban {
    Dao dao[N];
    Semaphore ghe{N - 1};                    // chỉ N - 1 ghế
    int bua[N] = {};                         // bữa đã nấu của đầu bếp i (chỉ luồng i ghi)
};

enum class Cach { ThuTuKhoa, ScopedLock, BotMotNguoi };

void nau(Ban& ban, int i) {                  // đã cầm đủ hai dao mới được gọi
    ++ban.dao[i].lanDung;
    ++ban.dao[(i + 1) % N].lanDung;
    ++ban.bua[i];
}

void dauBep(Ban& ban, int i, int soBua, Cach cach) {
    int trai = i, phai = (i + 1) % N;
    for (int k = 0; k < soBua; ++k) {
        if (cach == Cach::ThuTuKhoa) {
            int dau = trai < phai ? trai : phai;                 // (1) dao số nhỏ trước
            int sau = trai < phai ? phai : trai;
            std::lock_guard<std::mutex> g1(ban.dao[dau].khoa);
            std::this_thread::yield();                           // kéo dài khe hở để lỗi dễ lộ
            std::lock_guard<std::mutex> g2(ban.dao[sau].khoa);
            nau(ban, i);
        } else if (cach == Cach::ScopedLock) {
            std::scoped_lock g(ban.dao[trai].khoa, ban.dao[phai].khoa);   // (2) hai dao một lần
            nau(ban, i);
        } else {
            ban.ghe.acquire();                                   // (3) xin ghế trước
            {
                std::lock_guard<std::mutex> g1(ban.dao[trai].khoa);   // trái rồi phải, như bản sai
                std::this_thread::yield();
                std::lock_guard<std::mutex> g2(ban.dao[phai].khoa);
                nau(ban, i);
            }
            ban.ghe.release();                                   // (4) nhả dao xong mới nhả ghế
        }
    }
}

void thu(const char* ten, Cach cach, int soBan, int soBua) {
    bool tatCaXong = true;
    for (int vong = 0; vong < soBan; ++vong) {                   // (5) nhiều bàn liên tiếp
        Ban ban;
        std::vector<std::thread> ds;
        for (int i = 0; i < N; ++i) ds.emplace_back(dauBep, std::ref(ban), i, soBua, cach);
        for (std::thread& t : ds) t.join();
        for (int i = 0; i < N; ++i)
            if (ban.bua[i] != soBua || ban.dao[i].lanDung != 2 * soBua) tatCaXong = false;
    }
    std::cout << ten << ": " << soBan << " ban x " << N << " dau bep x " << soBua << " bua, "
              << (tatCaXong ? "tat ca xong dung so bua" : "SAI") << "\n";
}

int main(int argc, char**) {
    if (argc > 1) {                                  // có đối số: chạy cách "bớt một người"
        thu("bot mot nguoi", Cach::BotMotNguoi, 20, 100);
        return 0;
    }
    thu("thu tu khoa", Cach::ThuTuKhoa, 20, 100);
    thu("scoped_lock", Cach::ScopedLock, 20, 100);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dao đang cầm (ví dụ đầu bếp 4) |
|---|---|---|
| (1) | Đầu bếp 4 có `trai = 4`, `phai = 0`; so sánh cho `dau = 0`, `sau = 4`: người này cầm dao 0 trước. Bốn người kia vẫn trái rồi phải | 0, rồi 0 và 4 |
| (2) | `scoped_lock` xin cả hai dao một lần; chuẩn bảo đảm không deadlock bất kể thứ tự đối số | cả hai hoặc không dao nào |
| (3), (4) | Xin một trong 4 ghế trước khi đụng dao; chỉ nhả ghế sau khi đã nhả cả hai dao (nhờ ngoặc `{ }` làm `lock_guard` hủy trước) | ghế, rồi dao |
| `nau` | Mỗi dao ghi `lanDung` không có `atomic`: nếu hai người cầm cùng một dao thì TSan báo data race. Cuối bàn, `dao[k].lanDung` phải đúng `2 × soBua` | cả hai dao |
| (5) | Mỗi bàn dựng lại từ đầu, 20 bàn liên tiếp: nếu có kẹt, nó sẽ lộ ở đâu đó trong 20 × 5 × 100 = 10 000 bữa | |

**Kết quả khi chạy** (cả hai cách đầu; ba lần liền y hệt, TSan sạch, mã thoát 0):

```text
thu tu khoa: 20 ban x 5 dau bep x 100 bua, tat ca xong dung so bua
scoped_lock: 20 ban x 5 dau bep x 100 bua, tat ca xong dung so bua
```

Chạy với đối số (`./bua ghe`) ra `bot mot nguoi: 20 ban x 5 dau bep x 100 bua, tat ca xong dung so bua`. Mình lặp cả chương trình 100 lần (`-O1`) cho mỗi chế độ: 100/100 lần xong, và 20/20 lần dưới TSan cho chế độ mặc định.

#### Bản SAI: ai cũng cầm trái rồi phải (deadlock)

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

constexpr int N = 5;
std::mutex dao[N];                                   // dao[i] nằm giữa đầu bếp i-1 và i

void dauBep(int i) {
    int trai = i, phai = (i + 1) % N;
    std::lock_guard<std::mutex> g1(dao[trai]);       // (1) ai cũng cầm dao bên trái trước
    std::this_thread::sleep_for(std::chrono::milliseconds(50));   // (2) cho cả bàn kịp cầm
    std::lock_guard<std::mutex> g2(dao[phai]);       // (3) rồi xin dao bên phải
    std::cout << "dau bep " << i << " dang nau\n";
}

int main() {
    std::vector<std::thread> ds;
    for (int i = 0; i < N; ++i) ds.emplace_back(dauBep, i);
    for (std::thread& t : ds) t.join();
    std::cout << "ca ban an xong\n";
    return 0;
}
```

Mình chạy `timeout 3` ba lần: **không in dòng nào**, mã thoát **124** cả ba. Dưới TSan cũng mã 124 và **không có báo cáo** (đúng như Bài 26: không ai xin xong khóa thứ hai nên TSan chưa thấy thứ tự ngược). Khi bỏ dòng (2): 40 lần chạy đều ổn, vì mỗi luồng thường xong cả hai dao trước khi luồng sau kịp khởi động; đó là điểm đáng sợ.

Muốn tóm lỗi **không dựa vào `sleep`**, lặp nhiều bữa: cùng bản sai nhưng chỉ `yield()` ở dòng (2), mỗi đầu bếp 1000 bữa, 10 bàn liên tiếp. Bản sai treo **5/5 lần** (`timeout 20`, mã 124); bản có thứ tự khóa xong cả 3/3 lần trong khoảng 0,5 đến 1,5 giây (máy lúc đó đang bận, số giây chỉ để tham khảo).

**Thử thay đổi (hai cách chữa).** Đổi `ghe{N - 1}` thành `ghe{N}` (đủ 5 ghế) rồi chạy chế độ "bớt một người": treo 5/5 lần (mã 124), vì cả năm người lại có thể cầm dao trái cùng lúc. Trong cách thứ nhất, đổi `dau = trai`, `sau = phai` (bỏ quy ước thứ tự): cũng treo 5/5 lần. Hai thay đổi nhỏ phá đúng cái cơ chế mà mỗi cách dựa vào.

!!! info "TSan và cách N−1"
    Cách "bớt một người" chạy đúng, nhưng dưới TSan nó báo `lock-order-inversion (potential deadlock)` với chu trình năm dao `M12 => M13 => M15 => M16 => M17 => M12` (số hiệu `M` đổi theo lần chạy), và thoát mã 66. TSan chỉ nhìn thứ tự **khóa mutex**, không biết cái ghế đã chặn không cho cả năm người cùng cầm dao, nên cảnh báo này là "tiềm tàng" chứ không phải deadlock thật (lập luận ở Gợi ý 3). Đó là lý do cách này nằm sau đối số: khối mã mặc định phải sạch TSan, và đừng im lặng tắt cảnh báo; hãy giải thích nó.

**Chạy nhiều vòng không phải chứng minh.** 100/100 lần xong là bằng chứng, không phải chứng minh. Chứng minh thật là **lập luận**: thứ tự khóa thì chuỗi chờ chỉ đi theo số tăng dần nên không có vòng; `scoped_lock` thì nhờ lời bảo đảm của chuẩn; N−1 ghế thì nhờ đếm dao. Phép thử chỉ có sức nặng khi bản sai **bị chính nó bắt** (như trên).

**Chi phí và độ phức tạp.** Cả ba cách: O(1) thao tác khóa mỗi bữa, O(N) mutex. Song song tối đa là `⌊N/2⌋ = 2` người nấu cùng lúc (5 dao, mỗi người 2), dù cách nào. N−1 ghế thêm **một điểm chung** (`mutex` của semaphore) mà mọi đầu bếp phải qua mỗi bữa. Không cách nào bảo đảm **công bằng**: ở trên mỗi người đủ 100 bữa vì ta cho hạn mức cố định, không vì khóa chia đều lượt.

!!! info "Bạn biết Go?"
    Mình chạy Go 1.27.2. `sync.RWMutex` **chặn `RLock` mới khi có `Lock` đang chờ**, tức là ưu tiên ghi, khác `shared_mutex` của máy này. Hệ quả: "đọc lồng đọc" như bản sai 2 treo y hệt. Chương trình Go (`RLock`, một goroutine `Lock`, rồi `RLock` lần hai) in `fatal error: all goroutines are asleep - deadlock!`, và tài liệu Go cũng cấm khóa đọc đệ quy. Runtime báo được vì **mọi** goroutine đều ngủ (như Bài 26). Triết gia ăn tối ở Go chữa bằng thứ tự khóa hoặc giới hạn N−1; Go không có `scoped_lock`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Ưu tiên đọc và ưu tiên ghi khác nhau thế nào, bạn chọn cái nào?"
    Ưu tiên đọc: người đọc mới được vào miễn không có người ghi **ở trong**, nên nhiều đọc nhất nhưng người ghi có thể **đói** nếu người đọc gối đầu. Ưu tiên ghi: khi có người ghi **đang chờ**, người đọc mới phải đợi, nên ghi không đói nhưng đọc có thể bị chặn lâu và khóa đọc không cho xin lại. Mình chọn theo tải: bản ghi cần có hiệu lực sớm (cấu hình, bảng giá) thì ưu tiên ghi; đọc là việc chính và ghi chịu trễ được thì ưu tiên đọc, nhưng nhận rủi ro đói ghi. Muốn công bằng cả hai phía thì xếp hàng theo thứ tự đến.

??? question "Thế nếu một hàm đọc gọi một hàm đọc khác thì sao? Hay muốn nâng khóa đọc thành khóa ghi?"
    Cả hai đều **không được phép** với `std::shared_mutex`: xin khóa đọc lần hai là hành vi không xác định, và dưới chính sách ưu tiên ghi nó treo khi có người ghi chờ (mình chạy: mã 124). Nâng khóa đọc lên khóa ghi trong cùng luồng cũng treo vì luồng chờ chính mình nhả; mình chạy trên máy này ra mã 124. Cách làm đúng: nhả khóa đọc, xin khóa ghi, rồi **kiểm lại điều kiện** (có thể đã đổi trong khe hở). Hoặc đưa phần cần khóa xuống hàm trong, truyền "đã khóa rồi" vào.

??? question "Chữa triết gia ăn tối bằng cách nào? So sánh ba cách."
    Gốc của kẹt là vòng chờ: ai cũng giữ dao trái và chờ dao phải. Thứ tự khóa: đánh số dao, luôn cầm số nhỏ trước, hết vòng chờ. `scoped_lock`: xin cả hai một lần, hết giữ-và-chờ. N−1 người ngồi: không đủ người để khép vòng, vì chuỗi chờ đứt ở ghế trống nên luôn có người lấy được dao còn thiếu. Thứ tự khóa rẻ nhất; `scoped_lock` gọn nhất; N−1 dùng khi không sửa được chỗ xin khóa.

??? question "Bạn chứng minh code của mình không deadlock bằng cách nào? Chạy 1000 lần không treo đủ chưa?"
    Chưa đủ: thử nghiệm chỉ cho bằng chứng, không chứng minh. Mình chứng minh bằng lập luận (đồ thị chờ không có chu trình, hoặc đếm tài nguyên), rồi dùng thử nghiệm để bắt chỗ lập luận hở: lặp nhiều vòng, chèn `yield` vào khe hở, chạy TSan (nó báo `lock-order-inversion` kể cả khi chưa treo). Một phép thử có giá trị khi bản sai bị nó bắt, mình luôn chạy thử bản sai để xác nhận điều đó.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Kiểm rồi mới đặt trên `atomic`"
    Hai thao tác `atomic` liền nhau không thành một thao tác nguyên tử. Mình chạy bản sai: `vi pham` từ 0 đến 20000 (có lần ra 0 như đúng), có lần mất cả lượt tăng, TSan báo `data race`. Muốn loại trừ nhau, "kiểm" và "đặt" phải ở trong **cùng** một vùng găng.

!!! warning "Lỗi 2: Quên đếm người ghi đang chờ, hoặc đánh thức nhầm"
    Không đếm `ghiCho_` thì không phân biệt được hai chính sách. Bỏ `notify_all` ở `unlock_shared` mình chạy treo 3/3 lần; đổi `notify_all` thành `notify_one` ở `unlock` treo 4/6 lần (ở khóa ưu tiên ghi). Người chờ có hai loại nên đánh thức tất cả rồi để predicate quyết định.

!!! warning "Lỗi 3: Tưởng chạy nhiều lần không treo là xong; tưởng N−1 thì TSan sẽ im"
    Bản deadlock không có `sleep` chạy 40 lần đều ổn, mà cùng bản đó với nhiều bữa treo 5/5 lần. Còn bản N−1 đúng nhưng TSan báo `lock-order-inversion`. Khi nói trên bảng trắng, nêu cả hai: bằng chứng ≠ chứng minh, và cảnh báo công cụ cần được đọc chứ không phải tắt.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="70" markdown>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 1.** Đọc đoạn sau, với `RWLock<false>` là ưu tiên đọc và `RWLock<true>` là ưu tiên ghi của bài. Người ghi đã xếp hàng chờ. Kết quả của `ok` là gì?

```text
rw.lock_shared();                 // người đọc A đang ở trong
// luồng khác đã gọi rw.lock() và đang chờ
bool ok = rw.try_lock_shared();   // người đọc B xin vào
```

- `true` ở cả hai, vì A vẫn đang đọc nên B đọc cùng được
- `false` ở cả hai, vì đang có người ghi chờ nên ai cũng phải đợi
- `false` với ưu tiên đọc, `true` với ưu tiên ghi
- `true` với ưu tiên đọc, `false` với ưu tiên ghi

<p class="giai-thich" markdown>Ưu tiên đọc không quan tâm người ghi chờ nên B vào được (`true`); ưu tiên ghi thấy có người chờ nên chặn B (`false`). Nếu cả hai đều `true` thì hai chính sách không còn khác nhau, mâu thuẫn với kịch bản đói ghi của bài. Nếu cả hai đều `false` thì ưu tiên đọc sẽ không còn đói ghi. Còn kết quả đảo ngược (ưu tiên đọc `false`, ưu tiên ghi `true`) là gán nhầm chính sách nhường người ghi cho khóa kia.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Một cấu hình nhỏ chỉ là một số nguyên, đọc rất thường xuyên, cập nhật hiếm, mỗi lần đọc chỉ copy số đó ra. Nhóm đang cân nhắc `shared_mutex`. Bạn khuyên gì?

- Dùng `mutex` thường rồi đo; vùng đọc ngắn nên `shared_mutex` khó có lợi
- Dùng `shared_mutex`, vì đọc nhiều ghi ít là đúng bài toán của nó
- Tự viết khóa đọc-ghi ưu tiên đọc để chắc chắn nhanh hơn `shared_mutex`
- Bỏ khóa, vì chỉ đọc một số nguyên nhỏ thì luôn an toàn với mọi luồng

<p class="giai-thich" markdown>Khi vùng đọc chỉ vài lệnh thì việc ghi nhận số người đọc cũng là một thao tác chung đang tranh chấp, nên `shared_mutex` không nhanh hơn `mutex`; đo trước rồi hẵng đổi. "Đọc nhiều ghi ít" chỉ là điều kiện cần, vùng đọc phải đủ dài mới đáng. Tự viết cũng không có lý do để nhanh hơn, vì vẫn qua một `mutex` ở cổng vào. Bỏ khóa thì sai ngay khi có luồng ghi: đọc song song với ghi một số nguyên thường là data race.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Đọc đoạn sau, dưới `RWLock<true>` (ưu tiên ghi), khi có một luồng khác vừa gọi `lock()` và đang chờ. Điều nào đúng?

```text
void docNgoai() { std::shared_lock<RWLock<true>> lk(rw); docTrong(); }
void docTrong() { std::shared_lock<RWLock<true>> lk(rw); /* chỉ đọc */ }
```

- Luôn chạy xong, vì cả hai lần xin đều chỉ là khóa đọc nên không chặn nhau
- Báo lỗi biên dịch, vì một luồng không được tạo hai `shared_lock` trên cùng khóa
- Có thể treo: người ghi chờ chặn lần xin thứ hai, và nó chờ lần thứ nhất nhả
- Chỉ treo nếu hai hàm chạy trên hai luồng khác nhau, vì cần vòng chờ giữa hai luồng

<p class="giai-thich" markdown>Người ghi đã xếp hàng nên ưu tiên ghi chặn mọi người đọc mới, kể cả luồng này ở lần xin thứ hai, còn người ghi thì chờ luồng này nhả lần thứ nhất: vòng chờ trong một luồng. Hai lần xin cùng chỉ đọc không đủ để an toàn, vì chính sách xếp hàng mới quyết định. Trình biên dịch không kiểm tra chuyện này, đoạn mã biên dịch bình thường. Và vòng chờ ở đây hình thành ngay trong một luồng, nên không cần hai luồng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Bàn tròn 5 đầu bếp, 5 dao, chỉ 4 ghế, ai cũng cầm dao trái rồi dao phải. Vì sao không deadlock?

- Vì mỗi người ngồi luôn cầm dao theo một thứ tự cố định áp dụng cho cả bàn
- Vì bốn người ăn lần lượt từng người một nên không có hai người nào tranh dao
- Vì có một ghế trống nên chuỗi chờ đứt ở đó, luôn có người lấy được đủ dao
- Vì cái ghế là một mutex nên ThreadSanitizer biết trước thứ tự khóa của cả bàn

<p class="giai-thich" markdown>Vòng chờ cần cả năm người cùng giữ dao trái và chờ dao phải của người kế bên. Có một ghế trống thì con dao cạnh ghế đó không ai tranh, nên người sát ghế trống lấy được đủ hai dao, nấu xong rồi nhả. Cách này vẫn trái-rồi-phải ở mọi người, nên không phải thứ tự cố định. Bốn người cũng không ăn tuần tự: tối đa hai người nấu cùng lúc. Còn TSan không hiểu ghế, nó vẫn thấy chu trình năm dao và báo cảnh báo tiềm tàng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Bản `RWLockSai` dùng hai biến `atomic` (xem bản sai 1). Chạy `kiemTra` ra `vi pham = 19999` và `a = 3997`. Giải thích đúng nhất là gì?

- Kiểm cờ rồi đặt cờ là hai bước rời nhau, nên hai luồng cùng thấy "chưa ai" và cùng vào
- `atomic` mặc định không đủ mạnh, nên phải đổi sang `memory_order_seq_cst` mới hết lỗi
- Thiếu `volatile` trên `a` và `b`, nên trình biên dịch giữ giá trị cũ trong thanh ghi
- `yield()` làm bộ lập lịch xếp sai lượt các luồng, nên các cờ `atomic` bị ghi chồng lên nhau

<p class="giai-thich" markdown>Mỗi thao tác trên `atomic` đều nguyên tử, nhưng "kiểm rồi đặt" gồm hai thao tác, và khe hở giữa chúng cho hai luồng cùng vào vùng găng; `a = 3997` là hai người ghi cùng sửa nên mất lượt tăng. `atomic` mặc định đã là `seq_cst`, nên đổi thứ tự bộ nhớ không đóng được khe hở này. `volatile` không đồng bộ giữa các luồng và không sửa được gì ở đây. `yield` chỉ làm khe hở lộ rõ hơn, không tạo ra lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Thư viện cũ lấy hai dao bên trái rồi bên phải trong một hàm bạn không sửa được, nhưng bạn kiểm soát được việc bao nhiêu đầu bếp được vào bàn. Cách nào đáng chọn?

- `std::scoped_lock` ở mỗi lần xin dao, vì nó an toàn hơn mọi cách khác
- Chỉ cho tối đa N−1 đầu bếp vào bàn bằng bộ đếm có chờ ở cổng
- Cho mỗi đầu bếp ngủ một khoảng khác nhau trước khi xin dao
- Đánh số lại dao, mặc dù hàm lấy dao vẫn cầm trái rồi phải

<p class="giai-thich" markdown>Chặn ở cổng không đụng tới hàm lấy dao và vẫn bảo đảm luôn còn người có đủ hai dao. `scoped_lock` đúng nhưng phải sửa chính chỗ xin dao, điều đề bài không cho. Ngủ khác nhau chỉ đổi xác suất, đúng như bản deadlock bỏ `sleep` vẫn lọt qua 40 lần thử. Đánh số lại dao vô ích nếu hàm vẫn cầm theo vị trí trái-phải, vì thứ tự thực tế vẫn không đổi.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau, rồi cho biết chuyện gì có thể xảy ra khi chạy bàn 5 đầu bếp theo cách "bớt một người".

```text
Semaphore ghe{5};          // sửa từ N - 1 thành N
// mỗi đầu bếp: ghe.acquire(); khóa dao trái; khóa dao phải; nấu; nhả; ghe.release();
```

- Vẫn không bao giờ deadlock, vì ghế vẫn là một bộ đếm có chờ ở cổng
- Chạy nhanh hơn vì có thêm một ghế cho đầu bếp, mà vẫn đúng
- Báo lỗi biên dịch vì số ghế phải luôn nhỏ hơn số dao trên bàn
- Có thể treo: cả năm cùng ngồi, cùng cầm dao trái rồi chờ nhau

<p class="giai-thich" markdown>Với 5 ghế, cả năm có thể ngồi và cầm dao trái cùng lúc, tạo lại vòng chờ; mình chạy 5/5 lần đều treo (mã 124). Bộ đếm có chờ chỉ có tác dụng nhờ con số N−1, không nhờ bản thân nó. Có thêm ghế không làm nhanh hơn vì tối đa hai người nấu cùng lúc, và chương trình còn không chạy xong. Còn trình biên dịch không biết gì về quan hệ giữa số ghế và số dao.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **`RWLock`**: đếm người đọc ở trong, cờ người ghi ở trong, và số người ghi chờ, tất cả dưới một `mutex`; `notify_all` khi người ghi ra hoặc người đọc cuối ra. Ưu tiên đọc chỉ nhìn "có người ghi ở trong không"; ưu tiên ghi còn nhìn "có người ghi chờ không".
2. **Đói ghi chứng minh tất định** bằng kịch bản đọc gối đầu một luồng: ưu tiên đọc cho 1000 lần giao ca mà người ghi chưa vào, ưu tiên ghi chặn ngay (0 lần). `shared_mutex` của g++ 11 / glibc cho 1000 lần, nhưng chuẩn không quy định; đọc lồng nhau và nâng khóa đọc thành ghi đều là hành vi không xác định (mình chạy: treo).
3. **Bản sai Đề A**: `atomic` kiểm rồi đặt cho `vi pham` từ 0 đến 20000 (một lần ra 0 như đúng), TSan báo data race (mã 66); khóa đọc lồng nhau dưới ưu tiên ghi treo mã 124; bỏ `notify_all` hay đổi thành `notify_one` cũng treo.
4. **Triết gia ăn tối**: cầm trái rồi phải thì deadlock (`timeout` mã 124); chữa bằng thứ tự khóa (phá chờ vòng tròn), `std::scoped_lock` (phá giữ-và-chờ), hoặc N−1 ghế (không đủ người khép vòng). Cách N−1 chạy đúng nhưng TSan báo `lock-order-inversion` vì không hiểu cái ghế; song song tối đa `⌊N/2⌋`.
5. **Chạy nhiều vòng là bằng chứng, không phải chứng minh**: bản sai không có `sleep` chạy 40 lần đều ổn nhưng treo 5/5 lần khi nhiều bữa; chứng minh thật là lập luận không có vòng chờ, còn thử nghiệm dùng để bắt chỗ lập luận hở (bản đúng xong 100/100 lần).
