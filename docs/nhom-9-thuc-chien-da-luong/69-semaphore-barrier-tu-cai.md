# Bài 69 — Thực chiến: tự cài semaphore và barrier từ mutex + condition_variable

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Tự viết trên bảng trắng lớp `Semaphore` (C++17, chỉ `mutex` + `condition_variable`) có `acquire(n)`, `try_acquire(n)`, `release(n)`, dùng nó giới hạn **tổng trọng số** đang chạy; nói được vì sao `release(n)` khi người chờ cần số thẻ khác nhau phải `notify_all` (còn `notify_one` đủ khi nào) và vì sao `acquire(n)` không được thay bằng "gọi `acquire()` n lần".
    - Tự viết lớp `Barrier` **dùng lại được nhiều vòng** bằng **bộ đếm thế hệ**, và giải thích được vì sao chỉ đếm người tới thì hỏng: luồng chạy nhanh lọt sang vòng sau (mình chạy hai bản sai: một bản chạy mà sai kết quả, một bản treo).
    - Kiểm chứng bằng chương trình có đầu ra tất định và TSan sạch: đỉnh đồng thời, kết quả quét tổng tiền tố chia pha, "không ai ra vạch khi chưa đủ người" qua 4 luồng x 1000 vòng.
    - Phân biệt chuẩn bảo đảm gì với máy này (g++ 11.4, 8 lõi) cho kết quả gì, và trả lời được câu nối tiếp: chi phí mỗi vòng, đói của `acquire(n)`, luồng rút giữa chừng.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `lock_guard`, `unique_lock`, TSan), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`condition_variable`, predicate, `notify_one`/`notify_all`, notify bị mất), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, `compare_exchange_weak`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (`std::function`), và [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) (các khái niệm semaphore, barrier, và lớp `Semaphore` đầu tiên; bài này đào sâu hơn).

## 🧠 Câu chuyện mở đầu

Vòng phỏng vấn thứ hai. Người phỏng vấn đẩy cây bút qua bàn: "Tưởng tượng thư viện chuẩn **chưa có** semaphore và barrier. Bạn chỉ có `std::mutex` và `std::condition_variable`. Viết cho tôi hai thứ. Thứ nhất, `Semaphore` có thể xin nhiều thẻ một lần. Thứ hai, `Barrier` mà ba đầu bếp dùng đi dùng lại qua nhiều công đoạn. Vừa viết vừa nói bạn đang bảo vệ điều gì."

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Khu bếp lò có 4 bếp, treo 4 **thẻ bếp**; món to cần 2 hay 3 bếp thì lấy 2 hay 3 thẻ **cùng lúc**, thiếu thì đứng chờ (đề 1). Ba đầu bếp làm nhiều công đoạn, tới **vạch hẹn** cuối công đoạn thì đợi đủ cả ba, rồi cùng sang công đoạn sau, và vạch ấy dùng lại cho công đoạn tiếp theo (đề 2).

!!! info "Chỗ nào ví von hết đúng?"
    Thẻ bếp thật là vật thể, còn `dem_` của semaphore chỉ là một **con số** dưới khóa; không ai kiểm tra bạn trả đúng thẻ mình đã lấy. Vạch hẹn thật thì đứng yên, còn barrier phải **nhớ mình đang ở lượt hẹn thứ mấy** (thế hệ): đó chính là chỗ bài này khai thác.

## 📖 Giải thích

Cả hai đề dùng chung một mẫu mà [Bài 27](../nhom-3-da-luong/27-condition-variable.md) đã dạy: trạng thái nằm dưới mutex, chờ bằng `wait(lk, predicate)`, đổi trạng thái dưới khóa rồi `notify`. Cái khó nằm ở **chọn đúng predicate** và **đúng kiểu notify**. Cách trả lời đề thực chiến: nói trước **bất biến cần giữ**, rồi mới viết code, rồi nói cách kiểm.

### Đề 1: Semaphore có `acquire(n)`, `try_acquire(n)`, `release(n)`

**Đề bài.** Viết lớp `Semaphore` chỉ dùng `std::mutex` và `std::condition_variable` (C++17).

- `Semaphore(int chua)`: bắt đầu với `chua` thẻ.
- `acquire(int n = 1)`: chờ tới khi đủ `n` thẻ rồi lấy **cả n một lần**. (`= 1` là **tham số mặc định**: gọi `acquire()` không ghi số thì `n` bằng 1.)
- `try_acquire(int n = 1)`: **không chờ**; lấy được thì trả `true`, thiếu thẻ thì trả `false` và không đổi gì.
- `release(int n = 1)`: trả `n` thẻ; luồng nào gọi cũng được.
- Ràng buộc: nhiều luồng gọi đồng thời; không chờ bận; không mất tín hiệu; TSan sạch; coi như `n` không vượt số thẻ tối đa.

**Kiểm.** Khu bếp 4 bếp, 8 món cần `{1, 2, 3, 1, 2, 1, 3, 1}` bếp (tổng 14), mỗi món "nấu" 20 ms. Đầu ra phải có đúng ba dòng: kết quả `try_acquire`, "đỉnh tổng bếp đang dùng không quá 4", "8 món xong, còn chiếm 0 bếp".

??? tip "Gợi ý 1"
    Viết ra **bất biến** trước: `0 <= dem_`, và mọi lần đổi `dem_` đều dưới khóa. Luồng chờ cần chờ **điều gì**? (Đủ `n` thẻ, không chỉ "lớn hơn 0".)

??? tip "Gợi ý 2"
    `acquire(n)` là `wait` với predicate `dem_ >= n`, rồi `dem_ -= n` **trong cùng một lần giữ khóa**. `try_acquire` khóa, kiểm, trừ, nhả: không có `wait`. `release(n)` là `dem_ += n` dưới khóa rồi `notify`.

??? tip "Gợi ý 3"
    Hai người đang chờ có thể cần **số thẻ khác nhau**, và một lần `release(n)` có thể làm đủ cho nhiều người cùng lúc. `notify_one` đánh thức đúng **một** người nên có thể bỏ sót người đáng được đi. Nghĩ xem nên dùng `notify_all` hay không, và kiểm bằng cách thử `release(2)` khi hai luồng đang ngủ. Để khỏi quên trả thẻ, bọc `acquire`/`release` bằng RAII ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)).

**Phân tích hướng giải.** Mutex bảo vệ con số `dem_`; `condition_variable` chỉ là chuông đánh thức, **không** giữ trạng thái (nên không dùng chuông làm bộ đếm). Vì sao "gọi `acquire()` n lần" không thay được `acquire(n)`: hai luồng cùng cần 4 thẻ trên semaphore 4 thẻ, mỗi luồng lấy 2 rồi chờ 2 nữa, **không ai nhả**, thế là deadlock ([Bài 26](../nhom-3-da-luong/26-deadlock.md): giữ-và-chờ). `acquire(n)` lấy tất cả hoặc không lấy gì nên phá được giữ-và-chờ.

### Đề 2: Barrier dùng lại được, và vì sao cần "thế hệ"

**Đề bài.** Viết lớp `Barrier(int soLuong, std::function<void()> hoanTat)` với một hàm `arrive_and_wait()`.

- Luồng gọi `arrive_and_wait()` đợi tới khi **đủ `soLuong` luồng** cùng gọi, rồi tất cả đi tiếp.
- Dùng lại được nhiều vòng trên **cùng** một đối tượng. Luồng chạy nhanh quay lại gọi `arrive_and_wait()` ngay lập tức thì **không được** làm hỏng vòng sau, và không được lọt qua vòng mà người khác chưa tới.
- Hàm hoàn tất (nếu có) chạy đúng **một lần mỗi vòng**, trước khi ai được đi tiếp.
- Ràng buộc: không chờ bận, TSan sạch.

**Kiểm.** (a) Quét **tổng tiền tố** (phần tử thứ k bằng tổng các phần tử từ đầu tới k) cho `{1,...,8}` bằng 8 luồng chia pha: kết quả `1 3 6 10 15 21 28 36`, hàm hoàn tất chạy 6 lần. (b) 4 luồng x 1000 vòng, mỗi lần qua vạch kiểm "số lượt tới vạch của mọi luồng cộng lại đã đủ": số lần phát hiện lọt vạch phải là 0.

??? tip "Gợi ý 1"
    Viết bản đơn giản trước: một bộ đếm `conLai_` giảm mỗi lần có người tới; về 0 thì thả mọi người. Rồi hỏi: **vòng thứ hai** thì sao? Ai đặt lại `conLai_`, và vào lúc nào?

??? tip "Gợi ý 2"
    Người tới cuối cùng đặt lại `conLai_ = soLuong_`. Nhưng người đang ngủ ở vòng trước **chưa dậy** thì họ chờ điều kiện nào, khi con số `conLai_` đã bị dùng cho vòng sau? Điều kiện chờ phải là thứ **không bị vòng sau làm đổi lại**.

??? tip "Gợi ý 3"
    Thêm một biến `theHe_` (số thứ tự của vòng, chỉ tăng). Mỗi luồng tới thì **nhớ** `theHe_` hiện tại vào biến cục bộ `dot`, rồi chờ với predicate `theHe_ != dot`. Người cuối cùng: chạy hàm hoàn tất, `conLai_ = soLuong_`, `++theHe_`, `notify_all`.

**Phân tích hướng giải.** Barrier chỉ có **một** con số đếm, nhưng có **hai** chuyện phải nhớ: "vòng này còn thiếu mấy người" và "vòng của tôi đã xong chưa". Nếu dùng chung con số cho cả hai thì khi luồng nhanh vào vòng sau và trừ `conLai_`, luồng chậm còn ngủ ở vòng trước không còn nhận ra vòng của mình đã xong. Thế hệ **tách** hai chuyện ra: `conLai_` đếm cho vòng đang chạy, `theHe_` chỉ tăng nên "vòng của tôi xong" là điều đã xảy ra rồi và không đảo lại được.

!!! info "Bạn biết Go?"
    Go không có barrier trong thư viện chuẩn. `sync.Cond` có `Wait`, `Signal` (như `notify_one`), `Broadcast` (như `notify_all`) và cùng bẫy: phải kiểm điều kiện trong vòng lặp `for`. Tự cài barrier tái sử dụng bằng `sync.Cond` cũng cần đúng ý tưởng thế hệ này.

## 💻 Ví dụ code

### Lời giải đề 1

```cpp
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class Semaphore {
public:
    explicit Semaphore(int chua) : dem_(chua) {}      // (1) bắt đầu với "chua" thẻ

    void acquire(int n = 1) {                         // (2) xin n thẻ một lần; chưa đủ thì ngủ
        std::unique_lock<std::mutex> lk(khoa_);
        cv_.wait(lk, [&] { return dem_ >= n; });      // (3) predicate: đủ n mới đi tiếp
        dem_ -= n;
    }

    bool try_acquire(int n = 1) {                     // (4) không chờ: được thì true, không thì false
        std::lock_guard<std::mutex> g(khoa_);
        if (dem_ < n) return false;
        dem_ -= n;
        return true;
    }

    void release(int n = 1) {                         // (5) trả n thẻ, ai trả cũng được
        {
            std::lock_guard<std::mutex> g(khoa_);
            dem_ += n;
        }
        cv_.notify_all();                             // (6) người chờ cần số thẻ khác nhau: đánh thức hết
    }

private:
    std::mutex khoa_;
    std::condition_variable cv_;
    int dem_;                                         // số thẻ còn lại, chỉ đổi dưới khóa
};

class GiayPhep {                                      // (7) RAII: hàm tạo xin, hàm hủy trả
public:
    GiayPhep(Semaphore& s, int n) : s_(s), n_(n) { s_.acquire(n_); }
    ~GiayPhep() { s_.release(n_); }
    GiayPhep(const GiayPhep&) = delete;
    GiayPhep& operator=(const GiayPhep&) = delete;
private:
    Semaphore& s_;
    int n_;
};

int main() {
    Semaphore thu(4);                                 // thử try_acquire trên một luồng cho dễ đọc
    bool a = thu.try_acquire(3);                      // còn 4 -> lấy 3 -> còn 1
    bool b = thu.try_acquire(2);                      // còn 1 < 2 -> false, không ngủ
    bool c = thu.try_acquire(1);                      // còn 1 -> lấy -> còn 0
    bool d = thu.try_acquire();                       // còn 0 -> false
    std::cout << "try_acquire: " << a << b << c << d << "\n";

    Semaphore bep(4);                                 // khu bếp lò có 4 bếp
    std::atomic<int> dangDung{0};                     // tổng số bếp đang bị chiếm
    std::atomic<int> toiDa{0};                        // đỉnh từng thấy
    std::atomic<int> xong{0};
    const int nang[8] = {1, 2, 3, 1, 2, 1, 3, 1};     // món i cần nang[i] bếp

    std::vector<std::thread> ds;
    for (int i = 0; i < 8; ++i) {
        ds.emplace_back([&, i] {
            GiayPhep gp(bep, nang[i]);                // (8) xin đủ bếp rồi mới nấu
            int now = (dangDung += nang[i]);          // (9) += trả giá trị mới
            int cu = toiDa.load();
            while (cu < now && !toiDa.compare_exchange_weak(cu, now)) {}
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            dangDung -= nang[i];
            ++xong;
        });                                           // (10) ra khỏi lambda: ~GiayPhep trả bếp
    }
    for (std::thread& t : ds) t.join();

    std::cout << "dinh <= 4: " << (toiDa <= 4 ? "dung" : "sai") << "\n";
    std::cout << "xong " << xong << " mon, con chiem " << dangDung << " bep\n";
    return 0;
}
```

**Chạy từng dòng** (8 luồng chạy xen kẽ; cột cuối là `dem_` của `bep` ở một thời điểm minh họa)

| Dòng | Chuyện gì xảy ra | `dem_` của `bep` |
|---|---|---|
| (1) | `Semaphore bep(4)`: 4 thẻ treo ở cửa | `4` |
| (2)-(3) | Món cần 3 bếp: khóa, `wait` tới khi `dem_ >= 3`, rồi `dem_ -= 3` trong cùng lần giữ khóa | `4 -> 1` |
| (3) | Món tiếp theo cần 2 mà `dem_ = 1`: predicate sai, nhả khóa và ngủ (không tốn CPU) | `1` |
| (4) | `try_acquire`: khóa, thấy thiếu thì trả `false` ngay, không ngủ, không trừ gì | không đổi |
| (5)-(6) | `release(3)`: `dem_ += 3` dưới khóa, nhả khóa rồi `notify_all`: mọi người đang ngủ dậy, tự kiểm predicate của mình | `1 -> 4` |
| (7)-(8) | `GiayPhep` là RAII: dựng thì `acquire(n)`, hết phạm vi thì tự `release(n)` kể cả khi thoát sớm; `= delete` cấm sao chép để thẻ không bị trả hai lần ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)) | tùy lúc |
| (9)-(10) | `dangDung`, `toiDa` là `atomic` chỉ để **đo**; ra khỏi lambda thì `~GiayPhep` trả bếp | tùy lúc |

**Kết quả khi chạy:**

```text
try_acquire: 1010
dinh <= 4: dung
xong 8 mon, con chiem 0 bep
```

Biên dịch sạch cảnh báo, TSan sạch. Dòng đầu đúng theo lý luận (3 lấy được, 2 thiếu vì còn 1, 1 lấy được, rồi hết). Mình không in "đỉnh đúng bằng 4" vì chuẩn không hứa luồng nào trùng thời điểm với luồng nào. Mình đo riêng (thêm một dòng in `toiDa`): 100 lần chạy cho đủ 100 lần đỉnh 4, nhưng đó là chuyện của máy này.

**Thử thay đổi 1: xóa dòng `GiayPhep gp(bep, nang[i]);`.** Mình chạy 5 lần: cả 5 lần `toiDa = 14` (tổng trọng số của cả 8 món, tức là tất cả cùng nấu một lúc) và dòng kiểm ra `sai`. Không còn ai chặn.

**Thử thay đổi 2: gọi `bep.acquire(5)` khi semaphore chỉ có tối đa 4 thẻ.** Chương trình **treo mãi** (`timeout 3` thoát mã 124): không đủ 5 thẻ ở bất kỳ thời điểm nào. Đây là lý do đề bài ghi "coi như `n` không vượt số thẻ tối đa"; muốn chắc ăn thì lớp phải nhớ số thẻ tối đa và ném `std::invalid_argument` khi `n` vượt.

**Thử thay đổi 3: đổi `notify_all` ở dòng (6) thành `notify_one`.** Với đúng đề này mình chạy 200 lần, **0 lần treo**. Đừng kết luận là an toàn: bản sai dưới đây treo ngay lần đầu.

#### Bản SAI 1: `release(n)` chỉ `notify_one`

```cpp
// bo-qua-kiem-tra
// (phần còn lại của lớp giống bản đúng)
void release(int n = 1) {
    {
        std::lock_guard<std::mutex> g(khoa_);
        dem_ += n;
    }
    cv_.notify_one();                                 // SAI: trả 2 thẻ mà chỉ gọi dậy 1 người
}

int main() {
    Semaphore s(0);
    std::vector<std::thread> ds;
    for (int i = 0; i < 2; ++i)
        ds.emplace_back([&] { s.acquire(); });        // hai người cùng xin 1 thẻ, đều ngủ vì đang 0
    std::this_thread::sleep_for(std::chrono::milliseconds(100));   // chờ cả hai ngủ hẳn
    s.release(2);                                     // trả 2 thẻ một lần
    for (std::thread& t : ds) t.join();
    std::cout << "xong\n";
}
```

Mình chạy 10 lần: **cả 10 lần treo** (`timeout 3` mã 124), không in gì. Một luồng dậy lấy một thẻ; luồng kia vẫn ngủ dù `dem_` còn 1, vì không ai gọi nó. Đổi dòng đó thành `notify_all` thì cả 5 lần thử đều in `xong`. Mình thử thêm: luồng A xin 3 ngủ trước, luồng B xin 1 ngủ sau, rồi `release(1)` với `notify_one`: chương trình cũng treo, vì chuông gọi nhầm A (A dậy thấy `dem_ = 1 < 3` rồi ngủ lại, còn B đủ thẻ mà không ai gọi). Gọi nhầm ai là chuyện chuẩn không hứa; máy này gọi A. `notify_one` chỉ đủ khi mọi người chờ **cùng nhu cầu** và mỗi `release` thêm đúng cho **một** người.

#### Bản SAI 2: đổi bộ đếm ngoài khóa

```cpp
// bo-qua-kiem-tra
// (acquire giống bản đúng)
void release(int n = 1) {
    dem_ += n;                                        // SAI: không giữ khoa_ khi đổi dem_
    cv_.notify_all();
}
// main: một luồng gọi s.acquire(), luồng chính gọi s.release(); Semaphore s(0)
```

Biên dịch với `-fsanitize=thread`, TSan báo `WARNING: ThreadSanitizer: data race` ở cả 3 lần chạy (thoát mã 66): đọc `dem_` trong predicate (giữ khóa) với ghi `dem_ += n` ở `release` (không giữ). Ngoài data race còn có lỗi thật: nếu `release` đổi `dem_` và báo chuông đúng lúc người chờ vừa kiểm predicate (thấy sai) mà chưa kịp ngủ, tiếng chuông đến trước khi nó ngủ nên **mất** ([Bài 27](../nhom-3-da-luong/27-condition-variable.md) mục 3).

**Chi phí.** `acquire`/`release` không tranh chấp: một lần khóa/nhả mutex và kiểm một số nguyên. Mình đo 2 triệu cặp `acquire`+`release` trên một luồng (`-O2`, 3 lần chạy): khoảng 25-29 ns mỗi cặp, còn cặp `lock`+`unlock` trần khoảng 9-10 ns; đổi theo máy và `-O`.

Phần đắt là lúc **phải ngủ và dậy** (lời gọi vào nhân hệ điều hành), và `notify_all` với nhiều luồng đang chờ **đánh thức thừa** ([Bài 65](65-in-chan-le-abc.md) gọi là "đánh thức cả đàn"): mọi người dậy tranh khóa, chỉ một hai người đi tiếp. Mình đo kịch bản mọi luồng chỉ `acquire(1)`, `release(1)` (mỗi luồng 2000 thẻ): `notify_all` chậm hơn `notify_one` 4,4 đến 6,9 lần với 8 luồng chờ, và từ 2,9 đến 62 lần với 32 luồng chờ (ba lần chạy, nhiễu lớn).

Nên: nếu mọi người cùng xin 1 và `release(1)`, `notify_one` đủ và rẻ hơn; trộn nhiều nhu cầu hay `release(n)` thì `notify_all` mới an toàn.

**Công bằng.** Bản này **không công bằng**: luồng cần 3 thẻ có thể bị luồng cần 1 thẻ liên tục "chen" trước, vì mỗi lần có thẻ ai vào khóa trước thì được. Nếu số việc hữu hạn thì cuối cùng vẫn xong; còn dòng việc xin 1 thẻ không bao giờ ngớt thì luồng xin nhiều có thể chờ rất lâu. Mình không thấy chuẩn hứa thứ tự phục vụ cho `std::counting_semaphore`, nên đừng giả định FIFO. Mình không thử đo hiện tượng đói ở bản này; đây là lý luận từ cách cài.

### Lời giải đề 2

```cpp
#include <atomic>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

class Barrier {
public:
    explicit Barrier(int soLuong, std::function<void()> hoanTat = nullptr)
        : soLuong_(soLuong), conLai_(soLuong), hoanTat_(std::move(hoanTat)) {}

    void arrive_and_wait() {
        std::unique_lock<std::mutex> lk(khoa_);
        const unsigned long long dot = theHe_;        // (1) nhớ mình đang chờ ở đợt nào
        if (--conLai_ == 0) {                         // (2) người đến cuối cùng của đợt này
            if (hoanTat_) hoanTat_();                 // (3) việc chung, chạy trước khi thả mọi người
            conLai_ = soLuong_;                       // (4) đặt lại số người cho đợt sau
            ++theHe_;                                 // (5) đợt mới: đây là tín hiệu "được đi"
            cv_.notify_all();
        } else {
            cv_.wait(lk, [&] { return theHe_ != dot; });   // (6) chờ tới khi đợt của mình kết thúc
        }
    }

private:
    std::mutex khoa_;
    std::condition_variable cv_;
    const int soLuong_;                               // số luồng tham gia, không đổi
    int conLai_;                                      // đợt này còn thiếu mấy người
    unsigned long long theHe_ = 0;                    // số thứ tự của đợt hiện tại
    std::function<void()> hoanTat_;
};

int main() {
    // (a) quét tổng tiền tố (Hillis-Steele) cho 8 phần tử, mỗi luồng một phần tử.
    const int N = 8;
    int x[N] = {1, 2, 3, 4, 5, 6, 7, 8};
    int tam[N];
    int soVong = 0;                                   // chỉ hàm hoàn tất đụng tới khi luồng còn chạy
    Barrier hen(N, [&] { ++soVong; });

    std::vector<std::thread> ds;
    for (int k = 0; k < N; ++k) {
        ds.emplace_back([&, k] {
            for (int d = 1; d < N; d *= 2) {
                tam[k] = (k >= d) ? x[k] + x[k - d] : x[k];   // (7) pha đọc: chỉ đọc x, ghi tam của mình
                hen.arrive_and_wait();                        // (8) mọi người đọc xong
                x[k] = tam[k];                                // (9) pha ghi: ghi ô x của mình
                hen.arrive_and_wait();                        // (10) mọi người ghi xong
            }
        });
    }
    for (std::thread& t : ds) t.join();
    std::cout << "tong tien to:";
    for (int v : x) std::cout << " " << v;
    std::cout << "\nso dot hen: " << soVong << "\n";

    // (b) 4 luồng x 1000 vòng, kiểm "không ai ra khỏi vạch khi chưa đủ người".
    const int T = 4, R = 1000;
    std::atomic<int> daToi{0};                        // tổng số lần "đã tới vạch" của mọi luồng
    std::atomic<int> sai{0};
    int soDot = 0;
    Barrier vach(T, [&] { ++soDot; });
    std::vector<std::thread> ts;
    for (int k = 0; k < T; ++k) {
        ts.emplace_back([&] {
            for (int r = 1; r <= R; ++r) {
                ++daToi;                              // (11) báo mình đã tới vạch của vòng r
                vach.arrive_and_wait();
                if (daToi < r * T) ++sai;             // (12) ra được vạch mà chưa đủ r*T lượt tới: lọt vòng
            }
        });
    }
    for (std::thread& t : ts) t.join();
    std::cout << "vong: " << soDot << ", lot vach: " << sai << "\n";
    return 0;
}
```

**Chạy từng dòng** (barrier 3 luồng A, B, C trong một vòng; mô tả `conLai_` và `theHe_` lúc đó)

| Dòng | Chuyện gì xảy ra | `conLai_`, `theHe_` |
|---|---|---|
| (1) | A tới: khóa, ghi nhớ `dot = 0` (đợt của mình) | `3, 0` |
| (2) | `--conLai_` ra 2, chưa phải người cuối nên chạy nhánh `else` | `2, 0` |
| (6) | A `wait` với predicate `theHe_ != dot`: `0 != 0` sai nên ngủ, nhả khóa | `2, 0` |
| (1)-(6) | B tới, cũng `dot = 0`, `conLai_` về 1, ngủ | `1, 0` |
| (2)-(3) | C tới: `--conLai_` ra 0, là người cuối; chạy hàm hoàn tất (đếm vòng) | `0, 0` |
| (4)-(5) | C đặt `conLai_` lại 3 **và** `++theHe_`, rồi `notify_all` | `3, 1` |
| (6) | A, B dậy, thấy `theHe_ = 1 != 0`: vòng của mình đã xong, đi tiếp. Nếu C đã tới vạch **vòng sau** (`conLai_` về 2) trước khi A dậy, A vẫn thấy `1 != 0` | `2, 1` |
| (7)-(10) | Mỗi bước `d` (1, 2, 4) có hai pha: pha đọc tính `tam[k] = x[k] + x[k-d]` (`a ? b : c` nghĩa là "nếu a thì b, không thì c"), vạch; pha ghi `x[k] = tam[k]`, vạch | |
| (11)-(12) | Phần (b): mỗi luồng cộng 1 vào `daToi` trước vạch vòng `r`; qua vạch thì `daToi` phải `>= r * T` (đủ T luồng đã tới vòng này). Nhỏ hơn nghĩa là có người ra khi chưa đủ người | |

Về thuật toán: bước `d` cộng phần tử cách `d` ô vào mỗi ô, nên sau các bước `d = 1, 2, 4` mỗi ô đã gom đủ các phần tử từ đầu tới nó (ví dụ ô cuối 8 gom 1 rồi 2 rồi 4 ô lùi lại). Cách thế hệ cứu dòng (6): A dậy trễ bao lâu cũng được vì `theHe_` **chỉ tăng**, nên "vòng của tôi đã xong" không bao giờ đảo thành "chưa xong". `unsigned long long` là số nguyên không âm rất lớn; ở một triệu vòng mỗi giây nó cũng không tràn trong hàng trăm nghìn năm.

**Kết quả khi chạy:**

```text
tong tien to: 1 3 6 10 15 21 28 36
so dot hen: 6
vong: 1000, lot vach: 0
```

Biên dịch sạch, TSan sạch. Mình chạy 200 lần bản không TSan: cả 200 lần đầu ra y hệt. Tổng tiền tố đúng (1, 1+2, 1+2+3, ...); 3 bước (`d = 1, 2, 4`) x 2 vạch = 6 lần hàm hoàn tất. Hàm hoàn tất chạy **dưới khóa của barrier** bởi luồng cuối; vì thế đừng gọi lại barrier trong đó, và nó không được ném ngoại lệ (`std::barrier` đòi `noexcept`).

**Thử thay đổi 1: xóa dòng (8) (vạch giữa pha đọc và pha ghi).** Mình chạy 300 lần (`-O2`): **không lần nào** ra `1 3 6 10 15 21 28 36`; có tới 186 kết quả khác nhau, như `1 3 7 13 16 28 35 59`. TSan báo `data race`: đọc `x[k - d]` song song với ghi `x[k]` của luồng khác (thoát mã 66). Vạch ở (8) bảo đảm **mọi người đọc xong** rồi mới ai được ghi.

**Thử thay đổi 2: xóa dòng (10) (vạch giữa pha ghi và bước kế).** Mình chạy 300 lần: cũng không lần nào ra đáp án đúng (84 kết quả khác nhau); luồng nhanh đọc `x[k - d]` khi người kia chưa kịp ghi xong.

**Thử thay đổi 3: một luồng rút giữa chừng.** Mình thêm `arrive_and_drop()` (bỏ `const` ở `soLuong_` rồi giảm cả `soLuong_` và `conLai_`, nếu `conLai_` về 0 thì kết thúc vòng như người cuối) rồi cho 2 trong 4 luồng đi 3 vòng và rút, 2 luồng kia đi 10 vòng: 100 lần chạy cho 100 lần đủ 26 lượt tới, không treo, TSan sạch.

#### Bản SAI 1: không đặt lại bộ đếm (barrier thành latch)

```cpp
// bo-qua-kiem-tra
// Hàm tạo/thành viên giống bản đúng, bỏ theHe_ và hoanTat_
void arrive_and_wait() {
    std::unique_lock<std::mutex> lk(khoa_);
    --conLai_;
    if (conLai_ <= 0) cv_.notify_all();
    else cv_.wait(lk, [&] { return conLai_ <= 0; });  // SAI: conLai_ chỉ giảm, không bao giờ đặt lại
}
```

Với `main` giống phần (b) (4 luồng x 1000 vòng, đếm lọt vạch): 10 lần chạy, **đều thoát mã 0** mà số lọt vạch từ 1985 tới 2435 trên 4000 lần kiểm (TSan sạch vì mọi truy cập dữ liệu đều atomic hoặc dưới khóa, nhưng **logic** vẫn sai). Sau vòng đầu, `conLai_ <= 0` mãi mãi đúng, vạch thành cửa mở: không ai chờ ai. Đây là cái bẫy "chạy xong, không treo, không báo gì, kết quả sai".

#### Bản SAI 2: có đặt lại nhưng không có thế hệ

```cpp
// bo-qua-kiem-tra
// Hàm tạo/thành viên giống bản đúng, bỏ theHe_ và hoanTat_
void arrive_and_wait() {
    std::unique_lock<std::mutex> lk(khoa_);
    if (--conLai_ == 0) {
        conLai_ = soLuong_;                           // có đặt lại cho vòng sau
        cv_.notify_all();
    } else {
        cv_.wait(lk, [&] { return conLai_ == soLuong_; });   // SAI: chờ đúng con số đang bị dùng lại
    }
}
```

Mình chạy 20 lần với cùng `main` đó: **cả 20 lần treo** (`timeout 3` mã 124). Luồng cuối đặt `conLai_ = 4`, báo, rồi tới vạch vòng sau và trừ lại ra 3 **trước khi** ba luồng kia kịp dậy. Chúng thấy `conLai_` là 3, khác 4, nên ngủ tiếp; cả bốn luồng ngủ vĩnh viễn. Với barrier thật, cửa sổ lỗi này rất hẹp nếu giữa hai vòng có việc nặng, nhưng ở đây hai vòng sát nhau nên nó nổ ngay.

**Chi phí và độ phức tạp.** Mỗi `arrive_and_wait` giữ khóa O(1). Luồng cuối `notify_all` đánh thức `soLuong - 1` luồng; chúng phải xin lại **cùng một mutex** nên nhả nhau tuần tự, mỗi vòng tốn thời gian tăng theo số luồng, cộng chi phí ngủ-dậy của nhân hệ điều hành.

Mình đo 20000 vòng không có việc gì (`-O2`, 3 lần chạy, nhiễu lớn): 1 luồng dưới 0,4 micro-giây mỗi vòng; 2 luồng khoảng 11 đến 22; 4 luồng khoảng 34 đến 140; 8 luồng khoảng 70 đến 174; 16 luồng khoảng 134 đến 265.

Hệ quả thực tế: mỗi pha tính toán phải **dài hơn nhiều** so với cỡ trăm micro-giây này, không thì barrier ăn hết lợi ích của việc chia luồng. Có bản nhanh hơn (luồng chờ quay vòng thay vì ngủ, hoặc ghép nhiều barrier nhỏ thành cây) nhưng nằm ngoài phạm vi bài này.

### Chuẩn bảo đảm gì, máy này cho gì

| Chủ đề | Chuẩn C++ bảo đảm | Máy này (g++ 11.4, 8 lõi) cho |
|---|---|---|
| `wait(lk, predicate)` | Kiểm predicate dưới khóa, chịu được spurious wakeup | Bản có predicate chạy đúng trong mọi thử; bản không có thì mất tín hiệu (Bài 27) |
| `notify_one` | Đánh thức **nhiều nhất một** luồng đang chờ; không nói luồng nào | Bản SAI 1 treo 10/10; cùng đề với `notify_one` chạy 0/200 lần treo: **không** chứng minh an toàn |
| Công bằng của semaphore | Mình không thấy chuẩn nêu bảo đảm thứ tự | Mình không đo; đừng giả định thứ tự FIFO |
| Barrier | `std::barrier` (C++20) cho phép dùng lại; hàm hoàn tất `noexcept`, chạy một lần mỗi vòng | Bản tự cài đúng: 200 lần đầu ra giống nhau, TSan sạch |
| Số đỉnh, thời gian | Không bảo đảm | Đỉnh bếp 4 trong 100/100 lần; ns và micro-giây ở trên đổi theo máy |

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Câu nối tiếp 1: Vì sao `Barrier` không dùng `conLai_ == soLuong_` làm điều kiện chờ, mà phải thêm thế hệ?"
    Vì `conLai_` có **hai việc**: đếm vòng đang chạy và báo vòng nào xong. Khi luồng cuối đặt lại `conLai_` rồi tới vạch vòng sau, nó trừ `conLai_` lại **trước** khi luồng chờ kịp dậy; luồng chờ thấy con số khác và ngủ tiếp, cả nhóm treo (mình chạy: 20/20 lần treo). Thế hệ `theHe_` chỉ tăng nên "vòng của tôi đã xong" không bao giờ bị đảo ngược; mỗi luồng chờ `theHe_ != dot` với `dot` là số nó ghi nhớ lúc tới. Ý tưởng "pha" này cũng là cách chuẩn mô tả `std::barrier` (mỗi vòng là một pha).

??? question "Câu nối tiếp 2: Một luồng ném ngoại lệ và chết giữa vòng thì các luồng còn lại sao? Sửa thế nào?"
    Các luồng khác chờ mãi, vì vòng đó không bao giờ đủ người: barrier treo. Cách chữa: (1) luồng sắp chết gọi `arrive_and_drop()` (giảm `soLuong_` và `conLai_`, nếu thành 0 thì kết thúc vòng), đặt trong `catch` hay trong hàm hủy RAII để chắc chắn gọi; mình thử bản có `arrive_and_drop`, không treo. (2) Dùng `wait_for` với hạn chót ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)) để luồng chờ bỏ cuộc và báo lỗi thay vì ngủ vô hạn.

??? question "Câu nối tiếp 3: `acquire(n)` có thể bị đói không? Làm sao để công bằng?"
    Có thể. Luồng cần 3 thẻ chờ `dem_ >= 3`, trong khi luồng cần 1 thẻ luôn chen vào ngay khi `dem_ = 1`, nên `dem_` không bao giờ lên tới 3 nếu dòng xin 1 thẻ liên tục. Chữa: hàng đợi phục vụ **theo thứ tự đến** (mỗi người lấy một số thứ tự, chỉ người ở đầu hàng được kiểm `dem_ >= n`, người sau chờ dù đủ thẻ cho mình), đánh đổi: làm được ít việc mỗi giây hơn vì thẻ có thể nằm không trong lúc người đầu hàng cần nhiều hơn số đang có. Trong thực tế, chọn công bằng chỉ khi đói thật sự xảy ra.

??? question "Viết semaphore trên bảng trắng thì nói theo thứ tự nào?"
    Nêu bất biến ("`dem_ >= 0`, đổi dưới khóa"), chọn predicate ("đủ n"), chỉ ra `notify` ("`notify_all` vì nhu cầu khác nhau"), nói cách kiểm ("`atomic` ghi đỉnh đồng thời, khẳng định không vượt số thẻ, chạy TSan") và nói giới hạn (không công bằng, `n` vượt tối đa thì treo). Người phỏng vấn thường chấm cách bạn nói về **những lỗi bạn đã tránh**.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `release(n)` mà chỉ `notify_one`, hoặc đổi `dem_` ngoài khóa"
    `notify_one` chỉ đánh thức một người dù đã trả nhiều thẻ: mình chạy hai luồng chờ, `release(2)`, treo 10/10 lần (mã 124). Đổi `dem_` ngoài khóa thì TSan báo `data race` (mã 66) và còn mất tín hiệu.

!!! warning "Lỗi 2: Barrier đếm mà không có thế hệ"
    Không đặt lại bộ đếm thì barrier thành cửa mở sau vòng đầu (mình chạy: 1985 đến 2435 lọt vạch trên 4000 lần, thoát mã 0, **không lỗi nào hiện ra**); đặt lại mà không có thế hệ thì treo (20/20). Cả hai đều chạy đúng với số vòng ít, nên chỉ test nhiều vòng mới lộ.

!!! warning "Lỗi 3: Thiếu một vạch trong tính toán chia pha, hoặc đặt sai số luồng"
    Xóa một trong hai vạch của quét tiền tố thì 300 lần chạy không lần nào đúng, và TSan báo `data race`. Khởi tạo `Barrier(9)` mà chỉ 8 luồng tới thì cả 8 chờ mãi, đúng như một luồng chết không báo.

!!! warning "Lỗi 4: Khi nói trên bảng trắng"
    Nói "`notify_one` là đủ" mà không nêu điều kiện (mọi người cùng nhu cầu, mỗi `release` một thẻ); nói "không treo trong lần thử nên đúng" (cửa sổ lỗi hẹp: bản `notify_one` ở đề 1 chạy 0/200 treo mà vẫn sai); gọi "`acquire()` n lần" thay `acquire(n)` (deadlock giữ-và-chờ); quên nêu rằng semaphore tự cài **không công bằng**.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="69" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau. `Semaphore s(0)`; hai luồng A và B đang ngủ trong `s.acquire()` (mỗi luồng xin 1 thẻ). Luồng C gọi `s.release(2)`, và `release` của lớp này kết thúc bằng `cv_.notify_one()`.

```text
// A, B:  s.acquire();   (ngủ vì dem_ == 0)
// C:     s.release(2);  (dem_ += 2 dưới khóa, rồi notify_one)
```

Điều gì xảy ra nhiều khả năng nhất?

- Cả A và B đều dậy và đi tiếp, vì `dem_` đã đủ cho cả hai
- Một luồng đi tiếp, luồng kia ngủ dù `dem_` còn 1, vì không ai gọi nó
- Cả A và B đều ngủ tiếp, vì `notify_one` bị mất khi gọi sau `release`
- `release(2)` ném ngoại lệ, vì không thể trả hai thẻ cho một lần `notify`

<p class="giai-thich" markdown>`notify_one` đánh thức nhiều nhất một luồng đang chờ; luồng đó lấy một thẻ rồi đi, còn luồng kia vẫn ở trong `wait` và chỉ dậy khi có `notify` khác, dù `dem_` đã đủ cho nó. Hai luồng đi tiếp là điều ta muốn chứ không phải điều xảy ra, vì predicate chỉ được kiểm khi luồng dậy. Chuyện "notify bị mất" nói về gọi `notify` lúc chưa ai chờ, còn ở đây cả hai đã chờ. Và không có ngoại lệ nào, vì trả nhiều thẻ một lần là hợp lệ. Cách sửa là `notify_all`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc hàm sau của một `Barrier(4)` được 4 luồng gọi liên tục qua nhiều vòng. Điều gì nhiều khả năng xảy ra?

```text
void arrive_and_wait() {
    std::unique_lock<std::mutex> lk(khoa_);
    if (--conLai_ == 0) { conLai_ = soLuong_; cv_.notify_all(); }
    else cv_.wait(lk, [&] { return conLai_ == soLuong_; });
}
```

- Chạy đúng, vì luồng cuối đã đặt `conLai_` lại cho vòng sau
- Chạy xong nhưng nhiều luồng lọt qua vạch khi chưa đủ người
- Ném ngoại lệ ở vòng thứ hai, vì `conLai_` bị đặt lại khi còn người chờ
- Có thể treo: luồng cuối trừ lại `conLai_` trước khi người chờ kịp dậy

<p class="giai-thich" markdown>Luồng cuối đặt `conLai_ = 4` rồi tới vạch vòng sau và trừ ra 3 trước khi ba luồng kia dậy; chúng thấy 3, khác 4, ngủ tiếp, và cả nhóm treo vì không còn ai tới. Câu "đặt lại là đủ" nghe hợp lý nhưng đặt lại không cho người chờ biết vòng của họ đã xong, thứ chỉ thế hệ làm được. Lọt vạch là hậu quả của bản **không** đặt lại (thành cửa mở), một lỗi khác. Còn ngoại lệ thì không có gì ném.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Máy có 8 đơn vị bộ nhớ đồ họa dùng chung. Mỗi tác vụ cần 1, 2 hay 4 đơn vị **cùng lúc**, 16 luồng xin lúc nào cũng được, hết thì chờ. Cách làm đúng nào?

- Một `Semaphore(8)` có `acquire(n)`: xin đủ n đơn vị một lần rồi `release(n)`
- Một `Semaphore(8)`, mỗi tác vụ gọi `acquire()` n lần liên tiếp rồi mới chạy
- Một `std::mutex` giữ suốt lúc tác vụ chạy, để tránh tranh nhau đơn vị
- Một `Barrier(16)` để 16 luồng cùng xin, cùng nhả

<p class="giai-thich" markdown>Cần "lấy đủ n hoặc không lấy gì", nên `acquire(n)` là lời giải: nó chờ tới khi `dem_ >= n` rồi trừ một lần dưới khóa. Gọi `acquire()` n lần có vẻ giống, nhưng hai tác vụ cùng cần 4 đơn vị có thể mỗi bên giữ 4 rồi chờ 4 nữa: deadlock giữ-và-chờ. Mutex chỉ cho một tác vụ chạy, bỏ phí 7 đơn vị còn lại. Barrier bắt cả 16 đi cùng nhau, trái với đề.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. `Barrier hen(3, hoanTat)` với `hoanTat` làm `++soVong`. Ba luồng, mỗi luồng gọi `hen.arrive_and_wait()` đúng 5 lần. Sau khi cả ba `join`, `soVong` bằng bao nhiêu?

```text
Barrier hen(3, [&] { ++soVong; });   // soVong ban đầu 0
// ba luồng, mỗi luồng:  for (int i = 0; i < 5; ++i) hen.arrive_and_wait();
```

- 15, vì mỗi lần gọi `arrive_and_wait` chạy hàm hoàn tất một lần
- 3, vì có ba luồng nên hàm hoàn tất chạy mỗi luồng một lần
- 5, vì hàm hoàn tất chạy một lần mỗi vòng, do luồng tới cuối
- 1, vì hàm hoàn tất chỉ chạy lúc barrier được tạo

<p class="giai-thich" markdown>Mỗi vòng kết thúc đúng một lần, khi luồng cuối tới, và hàm hoàn tất chạy ở khoảnh khắc đó; năm vòng cho năm lần. Mười lăm là số lần **gọi** `arrive_and_wait`, không phải số vòng; con số ba là số luồng, không liên quan tới số lần chạy hàm hoàn tất. Hàm này cũng không chạy lúc tạo, mà chạy lúc đủ người của mỗi vòng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Một nhóm 4 luồng dùng `Barrier(4)` qua nhiều vòng. Ở vòng 2, luồng số 3 ném ngoại lệ và kết thúc mà không gọi `arrive_and_wait`. Ba luồng còn lại sẽ làm gì?

- Đi tiếp bình thường, vì barrier tự đếm lại số luồng còn sống
- Đi tiếp sau một khoảng, vì `wait` tự hết hạn khi có luồng chết
- Mất tín hiệu và chạy lệch pha, nhưng vẫn kết thúc
- Chờ mãi, vì vòng đó không bao giờ đủ 4 lượt tới

<p class="giai-thich" markdown>Barrier chỉ biết con số `soLuong_` đã khai báo; nó không phát hiện luồng nào chết. Vòng 2 cần đủ 4 lượt tới nên ba luồng ngủ mãi. Chữa bằng `arrive_and_drop()` đặt trong RAII hay `catch`, hoặc dùng `wait_for` để có hạn chót. Câu "tự đếm lại" mô tả điều ta muốn, không phải điều barrier làm. Còn `wait` có predicate không tự hết hạn; chỉ `wait_for` mới có hạn.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Một dịch vụ dùng `Semaphore` để giới hạn 10 kết nối: mọi luồng chỉ `acquire()` (xin 1) và `release()` (trả 1), không có `release(n)`. Có thể dùng `notify_one` ở `release` được không?

- Không, vì `notify_one` luôn làm mất tín hiệu khi nhiều luồng cùng chờ
- Được, vì mỗi `release` thêm đúng một thẻ và mọi người chờ cùng nhu cầu
- Không, vì chuẩn bắt `condition_variable` luôn dùng `notify_all`
- Được, nhưng chỉ khi mọi `release` nằm bên trong vùng giữ khóa

<p class="giai-thich" markdown>Mỗi `release(1)` thêm một thẻ và mọi người chờ đều cần một thẻ, nên đánh thức một người là vừa đủ; nếu có người khác chen vào lấy thẻ trước, người dậy kiểm lại predicate và ngủ tiếp mà không mất gì, vì thẻ đã có người dùng. Mình đo `notify_one` rẻ hơn `notify_all` nhiều lần khi có 8 đến 32 luồng chờ. `notify_one` không "luôn mất tín hiệu"; chỉ gọi khi chưa ai chờ mới mất (và semaphore còn nhớ trong `dem_`). Chuẩn không bắt `notify_all`. Còn notify trong hay sau khi nhả khóa đều đúng ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)).</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Một mô phỏng chia 8 luồng, mỗi pha tính toán chỉ khoảng 2 micro-giây rồi tới barrier tự cài. Mỗi vòng barrier tốn cỡ vài chục tới vài trăm micro-giây. Nên làm gì?

- Thay `notify_all` bằng `notify_one` cho nhanh, vì khi đó barrier vẫn đúng
- Thêm luồng thứ chín, vì nhiều luồng hơn thì mỗi vòng barrier nhanh hơn
- Gộp nhiều bước thành pha dài hơn, để việc tính lớn hơn chi phí chờ nhau
- Bỏ khóa trong barrier để vòng nhanh hơn, vì chỉ dùng cờ nguyên

<p class="giai-thich" markdown>Chi phí chính của barrier là ngủ-dậy và nhả khóa nhau tuần tự, nên phần việc chia ra phải dài hơn nhiều lần chi phí đó, mà gộp pha là cách duy nhất làm tỉ lệ ấy tốt hơn. Đổi sang `notify_one` làm sai barrier: chỉ một luồng được đánh thức, những luồng khác ngủ mãi. Thêm luồng làm mỗi vòng tốn **nhiều hơn** vì có thêm người phải thức dậy tranh khóa (mình đo: nhìn chung tăng theo số luồng). Còn bỏ khóa thì thành data race và mất đúng đắn.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Tự cài semaphore: `dem_` dưới mutex, `acquire(n)` chờ `dem_ >= n` rồi trừ **trong cùng lần giữ khóa**, `try_acquire(n)` kiểm-trừ không chờ, `release(n)` cộng dưới khóa rồi `notify_all`; mình chạy 8 món nặng 1-3 bếp trên 4 bếp: đỉnh `<= 4` (100/100 lần ra đúng 4), bỏ semaphore thì đỉnh 14, TSan sạch.
2. `notify_one` ở `release(n)` chỉ đúng khi mọi người chờ cùng nhu cầu và mỗi lần trả đúng một thẻ; mình chạy hai luồng chờ rồi `release(2)` với `notify_one`: treo 10/10 (mã 124), và `notify_one` ở đúng đề 1 chạy 0/200 lần treo nên **không** chứng minh được gì; đổi `dem_` ngoài khóa thì TSan báo `data race` (mã 66).
3. `acquire(n)` lấy đủ hoặc không lấy gì nên tránh deadlock giữ-và-chờ của "gọi `acquire()` n lần"; bản tự cài không công bằng (luồng xin nhiều có thể bị chen), và `n` vượt số thẻ tối đa thì treo mãi.
4. Barrier dùng lại được cần **thế hệ**: mỗi luồng nhớ `dot = theHe_` lúc tới và chờ `theHe_ != dot`; luồng cuối chạy hàm hoàn tất, đặt `conLai_` lại, `++theHe_`, `notify_all`. Bản không đặt lại: 10 lần chạy đều xong nhưng lọt vạch 1985-2435/4000; bản đặt lại mà không có thế hệ: treo 20/20.
5. Quét tiền tố chia pha cần **hai** vạch mỗi bước (đọc xong rồi mới ghi, ghi xong rồi mới đọc bước sau): bỏ một vạch thì 300 lần chạy không lần nào đúng và TSan báo `data race`; mỗi vòng barrier tự cài tốn cỡ vài chục đến vài trăm micro-giây (đổi theo máy), nên pha tính phải dài hơn nhiều; luồng chết giữa chừng làm barrier treo trừ khi có `arrive_and_drop` hoặc hạn chót.
