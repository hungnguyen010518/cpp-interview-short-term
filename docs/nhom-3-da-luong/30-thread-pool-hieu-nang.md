# Bài 30 — Thread pool và hiệu năng: false sharing, Amdahl

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao "mỗi việc một luồng" tệ khi việc nhỏ, và tự cài một **thread pool** (nhóm luồng dùng lại) từ `std::queue`, `std::mutex`, `std::condition_variable`: worker lấy việc, chạy **ngoài khóa**, và hàm hủy dừng sạch (đặt cờ dưới khóa, `notify_all`, `join`).
    - Biết dùng `std::packaged_task` để lấy `future` từ việc nộp vào pool, chọn số worker theo `hardware_concurrency()` (số luồng phần cứng) cho việc nặng CPU, và vì sao việc chờ I/O thì khác.
    - Đo thật ba cách (tuần tự, mỗi việc một luồng, pool): việc nhỏ thì pool cũng không thắng được tuần tự; việc đủ lớn mới có lợi.
    - Hiểu **false sharing** (đo thật với `alignas(64)`) và **định luật Amdahl**; có bảng chọn công cụ đa luồng và danh sách câu hỏi phỏng vấn nối về [Bài 24](24-thread-co-ban.md) đến 29; so với worker pool của Go.

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, `hardware_concurrency`, `steady_clock`, ngoại lệ trong luồng gọi `std::terminate`), [Bài 25](25-data-race-mutex.md) (`mutex`, `lock_guard`, class có `private:`), [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (con trỏ), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`this`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda `[&]`), [Bài 27](27-condition-variable.md) (`condition_variable`, `wait` với predicate, dừng sạch, hàng đợi), [Bài 28](28-atomic.md) (`std::atomic`, `fetch_add`), [Bài 29](29-async-future.md) (`future`, `get`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, hàm hủy), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`make_shared`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `std::function<bool(int)>`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](25-data-race-mutex.md). Có hai cách xử lý một đống món nhỏ. Cách một: mỗi món **thuê một đầu bếp mới**, làm xong là cho nghỉ việc. Tuyển người, chỉ chỗ đứng, trả lương, rồi sa thải: món chỉ mất một phút nấu thì phần thủ tục còn lâu hơn.

Cách hai: giữ **một đội đầu bếp cố định**, treo một **bảng phiếu việc** ở cửa. Ai rảnh thì lấy phiếu tiếp theo, làm xong lại quay ra bảng; bảng trống thì ngồi nghỉ và chờ chuông. Đội đó là **thread pool**, bảng phiếu là hàng đợi công việc, chuông là `condition_variable` của [Bài 27](27-condition-variable.md).

!!! info "Chỗ nào ví von đội đầu bếp không còn đúng?"
    Đầu bếp thật nhìn món rồi biết nó khó hay dễ. Worker của pool chỉ thấy một cái hàm, không biết hàm đó nặng hay nhẹ. Bếp thật thêm người thì thêm chỗ đứng; máy chỉ có số lõi nhất định, thêm worker quá số đó không thêm CPU (mục 4). Cuối cùng, mọi người vẫn **dùng chung thớt và bảng phiếu**, nên có phần việc không chia ra được (mục 5).

## 📖 Giải thích

### 1. Vì sao không "mỗi việc một luồng"

Tạo một `std::thread` là nhờ hệ điều hành dựng một luồng thật: cấp một stack riêng, đăng ký để lập lịch, rồi lúc `join` thu dọn. Chi phí đó cố định cho mỗi luồng, không phụ thuộc việc làm to hay nhỏ. Với một việc chạy hàng giây thì không đáng kể. Với hàng nghìn việc cỡ vài micro-giây thì chi phí tạo luồng **lớn hơn chính việc**; và số luồng sống cùng lúc quá nhiều còn ngốn bộ nhớ (mỗi luồng giữ một stack).

Giải pháp là **tái sử dụng**: tạo vài luồng một lần, rồi để chúng lần lượt nhận việc. Phần 💻 đo thật chênh lệch này; con số đổi theo máy, nhưng mẫu thì ổn định.

### 2. Thiết kế pool: ba mảnh quen thuộc

Mọi thứ cần dùng bạn đã học. Pool gồm đúng **ba mảnh** như producer-consumer ở [Bài 27](27-condition-variable.md):

- `std::queue<std::function<void()>>`: hàng đợi các việc. `std::function<void()>` đọc như `std::function<bool(int)>` ở [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md): "hộp chứa bất kỳ thứ gọi được, **không nhận gì và không trả gì**". Lambda nào cũng nhét vừa, kể cả lambda có bắt biến.
- `std::mutex` bảo vệ hàng đợi và cờ `dung_`; `std::condition_variable` để worker ngủ chờ việc.
- N worker, mỗi worker là một `std::thread` chạy vòng lặp: **chờ có việc hoặc đã dừng, lấy một việc ra, nhả khóa, chạy việc**.

Hai điều khiến pool đúng hay sai:

- **Chạy việc ngoài khóa.** Nếu giữ khóa lúc chạy, các worker chờ nhau và pool thành tuần tự (giống Lỗi 3 ở [Bài 27](27-condition-variable.md)).
- **Dừng sạch.** Hàm hủy đặt cờ dưới khóa, `notify_all`, rồi `join`. Bài này chọn **một** hành vi: worker **làm hết việc còn trong hàng rồi mới thoát** (predicate `!hang_.empty() || dung_`: chỉ thoát khi hàng cạn). Chọn khác (bỏ việc còn lại) cũng được, nhưng phải nói rõ với người dùng pool.

Pool là một **đối tượng RAII** ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)): tạo ra thì mở worker, hết phạm vi thì hàm hủy dừng và `join` chúng, kể cả khi có ngoại lệ. Quên `join` một `std::thread` còn chạy là `std::terminate` ([Bài 24](24-thread-co-ban.md)); RAII cất việc `join` vào hàm hủy để không ai quên.

### 3. Mở rộng: `submit` trả `future`

`submit(std::function<void()>)` không trả kết quả. Muốn kết quả, dùng `std::packaged_task<int()>` ([Bài 29](29-async-future.md) mục 7): nó bọc một hàm, **không chạy lúc tạo**, khi được gọi thì kết quả (hoặc ngoại lệ) tự vào `future` của nó. Có hai chi tiết:

- `packaged_task` không sao chép được, còn `std::function` đòi thứ nó chứa phải sao chép được. Cách gỡ phổ biến là bọc nó trong `std::shared_ptr` bằng `std::make_shared` ([Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md)): sao chép `shared_ptr` thì rẻ và chỉ có một `packaged_task` thật.
- Phải `get_future()` **trước** khi nộp việc, vì sau khi nộp, một worker có thể đang gọi gói đó, mà gọi `get_future()` cùng lúc là hai luồng đụng một đối tượng.

Mình làm đúng như vậy ở ví dụ phần 💻, không sửa lớp pool. Viết thành hàm mẫu (template) `submit` trả `future<T>` cho mọi kiểu là việc gọn hơn nhưng cần cú pháp chưa dạy, nên bài chỉ nêu hướng.

### 4. Bao nhiêu worker?

Với việc **nặng CPU** (tính toán thuần), mỗi worker giữ một lõi bận suốt, nên số worker hợp lý xấp xỉ số lõi, mà mốc dễ lấy là `std::thread::hardware_concurrency()` ([Bài 24](24-thread-co-ban.md); chuẩn chỉ gọi nó là gợi ý và cho phép trả `0`, nên cần kiểm). Hàm này đếm **luồng phần cứng**, không đếm lõi: CPU có siêu phân luồng (mỗi lõi chạy hai luồng) thì con số gấp đôi số lõi thật (máy mình: 4 lõi, trả 8), và nó đổi theo máy; vẫn dùng làm mốc được. Nhiều hơn số lõi thì các worker tranh nhau lõi, chỉ buộc hệ điều hành luân phiên nhiều luồng trên cùng một lõi.

Với việc **chờ I/O** (đọc mạng, đọc đĩa, ngủ), worker đang chờ **không dùng CPU**, nên có thể nhiều worker hơn số lõi: lúc một worker chờ, lõi đó chạy worker khác. Mình thử đúng điều đó ở "Thử thay đổi" của ví dụ 1.

### 5. Hai bức tường: false sharing và Amdahl

**Dòng cache.** CPU không đọc từng byte từ RAM mà từng **dòng cache** (cache line) cỡ 64 byte, cất trong **bộ nhớ đệm** (cache) của CPU: vùng nhỏ nằm sát mỗi lõi, nhanh hơn RAM rất nhiều. Tên giống cache ở [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) vì cùng ý "cất tạm cho nhanh", nhưng đây là phần cứng. 64 là cỡ **phổ biến** (máy mình báo đúng 64), không phải chuẩn C++ bắt buộc.

**False sharing** (chia sẻ giả): hai luồng ghi hai biến **khác nhau** nhưng nằm trên **cùng một dòng cache**. Mỗi lần một lõi ghi, nó giành quyền sở hữu cả dòng, buộc lõi kia bỏ bản của mình và nạp lại. Về logic hai luồng không đụng nhau (không có data race), nhưng phần cứng vẫn bắt chúng chuyền dòng cache qua lại, chậm đi.

Cách gỡ: tách hai biến sang hai dòng, ví dụ bằng `alignas(64)` (đòi địa chỉ của biến chia hết cho 64).

C++17 có `std::hardware_destructive_interference_size` (trong `<new>`) để thay số 64; mình thử trên g++ 11.4 của máy này thì báo `is not a member of 'std'`, nên bài dùng 64 trực tiếp.

**Định luật Amdahl.** Gọi `p` là phần thời gian chương trình có thể chia song song được (0 đến 1) và `n` là số lõi. Tốc độ tăng tối đa:

```text
tang_toc = 1 / ((1 - p) + p / n)
```

Phần `(1 - p)` là phần **bắt buộc tuần tự**, không lõi nào giúp được. Tính tay với `p = 0.9` (90% song song được):

| Số lõi `n` | Phép tính | Tăng tốc |
|---|---|---|
| 4 | 1 / (0,1 + 0,9/4) = 1 / 0,325 | khoảng 3,08 lần |
| 8 | 1 / (0,1 + 0,9/8) = 1 / 0,2125 | khoảng 4,7 lần |
| rất nhiều | 1 / (0,1 + gần 0) | tiến tới 10 lần, không vượt |

Thêm lõi tới đâu cũng không vượt `1/(1-p)`. Trong thực tế còn kém hơn công thức, vì công thức bỏ qua chi phí đồng bộ; và đoạn việc bạn đặt trong **vùng găng** của mutex ([Bài 25](25-data-race-mutex.md)) chạy lần lượt, nên tính vào phần tuần tự. Đó là lý do phạm vi khóa phải nhỏ nhất.

## 💻 Ví dụ code

### Ví dụ 1: thread pool tự cài

Chương trình tạo pool 4 worker, nộp 1000 việc "cộng `i` vào `tong`" (một `std::atomic<long long>`), rồi nộp thêm một việc có kết quả bằng `packaged_task`. Việc nào chạy trên worker nào đổi theo lần chạy, nên **không in thứ tự**; chương trình chỉ in sau khi pool đã hủy (dừng sạch).

Về cú pháp mới: `[this]` cho lambda trong hàm thành viên dùng được các thành viên của đối tượng (`this` là con trỏ tới chính đối tượng, như đã học ở [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)); đuôi `_` trong `khoa_`, `hang_` chỉ là thói quen đặt tên cho thành viên.

```cpp
#include <atomic>
#include <condition_variable>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

class NhomLuong {
public:
    NhomLuong(int n) {
        for (int i = 0; i < n; ++i) {
            worker_.emplace_back([this] { chay(); });                    // (1) mở n worker
        }
    }

    void submit(std::function<void()> viec) {
        {
            std::lock_guard<std::mutex> g(khoa_);
            hang_.push(std::move(viec));                                 // (2) bỏ việc vào hàng
        }
        cv_.notify_one();                                                // (3) gọi một worker dậy
    }

    ~NhomLuong() {
        {
            std::lock_guard<std::mutex> g(khoa_);
            dung_ = true;                                                // (4) đặt cờ dưới khóa
        }
        cv_.notify_all();                                                // (5) đánh thức mọi worker
        for (std::thread& t : worker_) t.join();                         // (6) chờ họ làm hết rồi thoát
    }

private:
    void chay() {
        while (true) {
            std::function<void()> viec;
            {
                std::unique_lock<std::mutex> lk(khoa_);
                cv_.wait(lk, [this] { return !hang_.empty() || dung_; });  // (7)
                if (hang_.empty()) return;                               // (8) đã dừng và hết việc
                viec = std::move(hang_.front());
                hang_.pop();
            }                                                            // (9) nhả khóa
            try { viec(); } catch (...) {}                               // (10) chạy ngoài khóa
        }
    }

    std::mutex khoa_;
    std::condition_variable cv_;
    std::queue<std::function<void()>> hang_;
    bool dung_ = false;
    std::vector<std::thread> worker_;
};

int main() {
    std::atomic<long long> tong{0};
    std::future<int> kq;
    {
        NhomLuong nhom(4);
        for (int i = 1; i <= 1000; ++i) {
            nhom.submit([&tong, i] { tong += i; });                      // (11)
        }
        auto goi = std::make_shared<std::packaged_task<int()>>([] { return 6 * 7; });
        kq = goi->get_future();                                          // (12) lấy phiếu trước
        nhom.submit([goi] { (*goi)(); });                                // (13) pool gọi gói
    }                                                                    // (14) hủy nhom: dừng sạch
    std::cout << "tong = " << tong << "\n";
    std::cout << "kq = " << kq.get() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Hàm tạo mở 4 worker, mỗi worker chạy `chay()` |
| (2)-(3) | `submit` đẩy việc vào hàng dưới khóa (`std::move` để khỏi sao chép hộp hàm), nhả khóa, gọi một worker dậy |
| (7) | Worker chờ tới khi hàng có việc **hoặc** đã dừng; hàng rỗng thì nhả khóa và ngủ |
| (8) | Dậy mà hàng rỗng thì chỉ có thể là đã dừng: thoát hàm, luồng kết thúc |
| (9)-(10) | `std::move` chuyển hộp việc ra khỏi hàng, `pop` bỏ chỗ trống; nhả khóa **rồi mới** chạy: các worker chạy song song. `catch (...)` bắt ngoại lệ **mọi loại** từ việc (và bỏ qua nó) |
| (11) | Mỗi việc cộng `i` vào `tong` bằng atomic, nên không cần khóa |
| (12)-(13) | `get_future` trước, rồi nộp lambda gọi gói: `*goi` lấy chính `packaged_task` từ `shared_ptr`, `( )` ngay sau thì gọi nó; `shared_ptr` giữ gói sống tới khi chạy |
| (14) | Hết khối, hàm hủy chạy (4)-(6): đặt cờ, đánh thức, `join`. Việc còn trong hàng được làm hết |

**Kết quả khi chạy:** `tong = 500500` rồi `kq = 42`. Mình biên dịch sạch cảnh báo, chạy 100 lần cùng một kết quả, và TSan (`setarch $(uname -m) -R ./a.out`, [Bài 25](25-data-race-mutex.md)) không báo gì. Hàm hủy chờ hết việc **trước** khi `main` in, nên `tong` luôn đủ 500500.

**Thử thay đổi 1: bỏ dòng (5) `cv_.notify_all();`.** Mình thử hai cách:

- Chương trình trên, chạy 20 lần một đợt, ba đợt mỗi mức `-O`. Không tối ưu: 5, 4, 3 lần ra bình thường, còn lại treo (`timeout 3` mã **124**). `-O2`: 19, 16, 18 lần ra bình thường, chỉ 1 đến 4 lần treo. Treo hay không tùy lúc hủy worker còn bận hay đã ngủ, nên tỉ lệ đổi mạnh theo máy, mức `-O` và lần chạy.
- Chỉ tạo pool 4 worker, ngủ 200 ms rồi hủy (cả bốn chắc chắn đang ngủ trong `wait`): 3 lần đều treo.

Lý do: không ai đánh thức worker đang ngủ, nên `join` chờ mãi (trên máy mình; chuẩn cho phép đánh thức giả nên không hứa). "Ra bình thường" là may; chuẩn chỉ nói `notify_one` đánh thức nhiều nhất một luồng và `wait` cần được đánh thức.

**Thử thay đổi 2: cho một việc ném ngoại lệ**, ví dụ việc `i == 500` thực hiện `throw std::runtime_error("loi")`. Với bản pool **bỏ** `try`/`catch` ở dòng (10) (chỉ còn `viec();`), mình chạy: chương trình dừng với `terminate called after throwing an instance of 'std::runtime_error'` và mã **134**. Việc chạy trên luồng của worker, ngoại lệ không ai bắt thoát khỏi hàm luồng, đúng như [Bài 24](24-thread-co-ban.md). Với bản có `try`/`catch` như listing, mình chạy: in `tong = 500000` (thiếu đúng việc 500) và `kq = 42`, mã 0, TSan sạch. Ngoại lệ bị **nuốt im lặng**; muốn biết lỗi thì ghi lại nó, hoặc dùng `packaged_task` để ngoại lệ đi vào `future` ([Bài 29](29-async-future.md)).

Bài này không xử lý chuyện `submit` sau khi pool đã bị hủy hay đặt cờ dừng (việc nộp muộn có thể không bao giờ chạy), nên đây là bản học, chưa đủ cho sản phẩm.

**Thử thay đổi 3: việc chờ I/O.** Mình đổi mỗi việc thành `std::this_thread::sleep_for(std::chrono::milliseconds(10))` (giả vờ chờ mạng), nộp 100 việc, rồi đo thời gian từ lúc tạo pool tới lúc hủy xong. Máy mình (4 lõi, 8 luồng phần cứng): pool 4 worker mất khoảng 252 ms (ba lần chạy: 252, 252, 253), pool 32 worker khoảng 43 ms (ba lần: 43, 43, 43). Việc chờ không tốn CPU nên nhiều worker hơn số lõi vẫn nhanh hơn; con số đổi theo máy.

### Ví dụ 2: đo pool, mỗi việc một luồng, và tuần tự

Mỗi việc ghi kết quả vào ô riêng `kq[i]` (không đụng ô của việc khác, nên không cần khóa). Ba cách cùng làm một lô việc: chạy lần lượt; mỗi việc một `std::thread` (theo đợt 8 luồng rồi `join`); và pool 4 worker (thời gian gồm cả dựng pool và hủy). Mình chạy hai lô: 20000 việc nhỏ và 400 việc to hơn.

Đoạn dưới là phần thay cho `main` ở ví dụ 1. Mình ghép nó ngay sau lớp `NhomLuong` (thêm `#include <chrono>`) rồi biên dịch và chạy; khối này không đứng một mình (cần lớp ở ví dụ 1) và in số đo đổi theo lần chạy, nên không được tự biên dịch riêng.

```cpp
// bo-qua-kiem-tra
void lam(std::vector<long long>& kq, int i, int lan) {
    long long s = 0;
    for (int k = 0; k < lan; ++k) s += (i + k) % 7;
    kq[i] = s;                                       // (1) ô riêng của việc i
}

long long ms(std::function<void()> f) {              // (2) đo một đoạn việc bằng mili giây
    auto bat = std::chrono::steady_clock::now();
    f();
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();
}

void thu(const char* ten, int soViec, int lan) {
    std::vector<long long> a(soViec), b(soViec), c(soViec);
    long long t1 = ms([&] { for (int i = 0; i < soViec; ++i) lam(a, i, lan); });
    long long t2 = ms([&] {
        for (int i = 0; i < soViec; i += 8) {        // (3) mỗi việc một luồng, 8 luồng một đợt
            std::vector<std::thread> ts;
            for (int j = i; j < i + 8 && j < soViec; ++j) ts.emplace_back(lam, std::ref(b), j, lan);
            for (std::thread& t : ts) t.join();
        }
    });
    long long t3 = ms([&] {
        NhomLuong nhom(4);                           // (4) pool: dựng, nộp, hủy
        for (int i = 0; i < soViec; ++i) nhom.submit([&c, i, lan] { lam(c, i, lan); });
    });
    std::cout << ten << ": tuan tu " << t1 << " ms, moi viec mot luong " << t2
              << " ms, pool 4 worker " << t3 << " ms\n";
}

int main() {
    thu("viec nho (20000 viec x 20 vong)", 20000, 20);
    thu("viec vua (400 viec x 200000 vong)", 400, 200000);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Việc `i` làm `lan` vòng cộng rồi ghi vào ô của chính nó |
| (2) | `ms` chạy hàm `f` và trả số mili giây trôi qua (`steady_clock`, [Bài 24](24-thread-co-ban.md)) |
| (3) | Cách hai (`std::ref` như [Bài 24](24-thread-co-ban.md)): mỗi việc một `std::thread`, nên tạo và hủy 20000 luồng ở lô nhỏ |
| (4) | Cách ba: dựng 4 worker, nộp mọi việc, hủy (chờ hết việc) rồi mới có thời gian |

**Kết quả khi chạy** (g++ 11.4, máy 4 lõi 8 luồng phần cứng; ba lần ở mỗi mức `-O`, đổi theo máy, lần chạy, và mức `-O`):

| Lô | Mức `-O` | Tuần tự | Mỗi việc một luồng | Pool 4 worker |
|---|---|---|---|---|
| nhỏ | không tối ưu | 1 ms | 654 đến 674 ms | 30 đến 33 ms |
| nhỏ | `-O2` | 0 ms | 625 đến 648 ms | 6 đến 8 ms |
| vừa | không tối ưu | 200 đến 201 ms | 80 đến 103 ms | 58 đến 72 ms |
| vừa | `-O2` | 93 đến 100 ms | 66 đến 69 ms | 37 ms |

Mẫu đáng nhớ có ba ý:

- Việc nhỏ thì **tuần tự thắng cả pool** (ở `-O2`: 0 ms so với 6 đến 8 ms): một việc chỉ vài chục phép cộng, nhẹ hơn việc khóa mutex, đẩy hàng và đánh thức một worker. Pool vẫn rẻ hơn tạo luồng cho từng việc rất nhiều.
- Việc vừa thì pool thường nhanh nhất, nhưng **không nhanh gấp 4 lần** tuần tự dù có 4 worker: còn chi phí đồng bộ, phần tuần tự (mục 5), và máy này chỉ có 4 lõi thật.
- Luồng dùng một lần, mỗi việc một luồng, tốn nhất khi việc nhỏ (khoảng 650 ms chia cho 20000 luồng ra cỡ 30 micro-giây mỗi luồng, trên máy này).

### Ví dụ 3: false sharing, đo thật

Hai luồng, mỗi luồng tăng **bộ đếm của riêng mình** 5 triệu lần. Bản đầu để hai bộ đếm kề nhau (16 byte, nên rất có thể chung một dòng 64 byte); bản sau dùng `alignas(64)` để mỗi bộ đếm ở dòng riêng. `std::atomic<long long>` để mỗi lần tăng đúng và không có data race ([Bài 28](28-atomic.md)).

```cpp
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

struct Gan {                              // hai bộ đếm nằm kề nhau
    std::atomic<long long> a{0};
    std::atomic<long long> b{0};
};

struct Xa {                               // mỗi bộ đếm bắt đầu ở địa chỉ chia hết cho 64
    alignas(64) std::atomic<long long> a{0};
    alignas(64) std::atomic<long long> b{0};
};

const int N = 5000000;

long long dem(std::atomic<long long>& a, std::atomic<long long>& b) {
    auto bat = std::chrono::steady_clock::now();
    std::thread t1([&a] { for (int i = 0; i < N; ++i) a.fetch_add(1); });   // (1)
    std::thread t2([&b] { for (int i = 0; i < N; ++i) b.fetch_add(1); });   // (2)
    t1.join();
    t2.join();
    auto troi = std::chrono::steady_clock::now() - bat;
    if (a != N || b != N) std::cout << "sai!\n";                            // (3)
    return std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();
}

int main() {
    Gan g;
    Xa x;
    std::cout << "sizeof(Gan) = " << sizeof(Gan) << ", sizeof(Xa) = " << sizeof(Xa) << "\n";
    std::cout << "ke nhau: " << dem(g.a, g.b) << " ms\n";
    std::cout << "alignas(64): " << dem(x.a, x.b) << " ms\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1)-(2) | Hai luồng, mỗi luồng chỉ đụng bộ đếm của mình: hai biến khác nhau, không có data race |
| (3) | Kiểm hai bộ đếm đủ `N`: tăng atomic nên luôn đúng; không in gì nghĩa là đúng |
| `Xa` | Mỗi `alignas(64)` đẩy bộ đếm tới địa chỉ chia hết cho 64, nên `sizeof(Xa)` là 128 (hai dòng) thay vì 16 |

**Kết quả khi chạy:** `sizeof(Gan) = 16, sizeof(Xa) = 128` (hai số này ổn định). Hai dòng thời gian đổi theo lần chạy; trên máy mình, ba lần ở không tối ưu: `ke nhau` 139, 145, 142 ms so với `alignas(64)` 49, 51, 40 ms; ở `-O2`: 123, 113, 107 ms so với 30, 30, 31 ms. Bản kề nhau chậm hơn khoảng 3 đến 4 lần, dù không có data race: TSan sạch (mình chạy). Chênh lệch này không bảo đảm: nó đổi theo CPU và việc hai luồng có chạy trên hai lõi hay không.

!!! warning "Hay nhầm"
    False sharing **không** phải data race. Hai luồng ghi hai biến khác nhau thì chương trình đúng; chỉ có tốc độ bị ảnh hưởng, và TSan không báo gì. Nó hay xuất hiện với mảng bộ đếm theo luồng (`dem[0]`, `dem[1]`... nằm kề nhau): cách gỡ là đệm mỗi phần tử tới cỡ một dòng cache.

!!! info "Bạn biết Go?"
    Go **không cần tự cài pool** cho hầu hết việc: goroutine do runtime Go lập lịch trên một số luồng hệ điều hành, tạo rất rẻ (stack nhỏ, tự lớn thêm), nên thường mở **mỗi việc một goroutine**. Điều đó không đúng với `std::thread` (một luồng hệ điều hành thật, [Bài 24](24-thread-co-ban.md)). Khi cần **giới hạn số việc chạy cùng lúc** thì Go mới dựng worker pool, bằng channel và `WaitGroup`. Mình chạy Go 1.27.1; chương trình đầy đủ (bọc mảnh dưới trong `package main`, `import`, rồi thêm `fmt.Println("tong =", tong.Load())` sau `wg.Wait()`) in `tong = 500500`, `go run -race` sạch:

    ```go
    jobs := make(chan int)
    var tong atomic.Int64
    var wg sync.WaitGroup
    for w := 0; w < 4; w++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs { // thoát khi jobs đã close và cạn
                tong.Add(int64(job))
            }
        }()
    }
    for i := 1; i <= 1000; i++ { jobs <- i }
    close(jobs)   // thay cho dung_ = true + notify_all
    wg.Wait()     // thay cho join
    ```

    Đối chiếu với pool C++: channel `jobs` thay cả hàng đợi, mutex và `condition_variable`; `close` thay cờ dừng; `for job := range jobs` làm hết việc còn lại rồi mới thoát (cùng hành vi "dừng sạch" mà bài chọn); `wg.Wait()` thay `join`. Go lập lịch goroutine nên số worker `4` ở đây chỉ để giới hạn, không phải để "chia lõi".

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Vì sao dùng thread pool thay vì tạo một luồng cho mỗi việc, và cài thế nào?"
    Tạo và hủy luồng có chi phí cố định (hệ điều hành dựng stack và đăng ký lập lịch), nên với nhiều việc nhỏ chi phí đó lớn hơn việc, và quá nhiều luồng sống cùng lúc tốn bộ nhớ. Pool tạo N luồng một lần và tái sử dụng. Cài: một hàng đợi `std::queue<std::function<void()>>` dưới `std::mutex`, một `std::condition_variable`; worker `wait` tới khi có việc hoặc đã dừng, lấy việc, **nhả khóa rồi chạy**; hàm hủy đặt cờ dừng dưới khóa, `notify_all`, `join` (RAII). Muốn kết quả thì `std::packaged_task` + `std::future`.

??? question "Số luồng trong pool nên là bao nhiêu?"
    Việc nặng CPU: xấp xỉ số lõi, lấy mốc từ `std::thread::hardware_concurrency()` (chỉ là gợi ý, có thể trả 0, và đếm luồng phần cứng nên có thể gấp đôi số lõi), vì nhiều hơn chỉ tranh lõi. Việc chờ I/O: có thể nhiều hơn số lõi, vì luồng đang chờ không dùng CPU. Cần đo, không đoán; số tối ưu còn tùy tranh chấp khóa.

??? question "False sharing là gì và Amdahl nói gì?"
    False sharing: hai luồng ghi hai biến khác nhau nhưng cùng một dòng cache (thường 64 byte), nên các lõi phải chuyền dòng đó qua lại và chương trình chậm đi dù không có data race; gỡ bằng đệm hoặc `alignas(64)`. Amdahl: nếu phần song song được là `p` thì tăng tốc với `n` lõi tối đa `1 / ((1 - p) + p / n)`, không bao giờ vượt `1 / (1 - p)`; phần tuần tự (kể cả vùng găng của mutex) và chi phí đồng bộ giới hạn hiệu quả của việc thêm luồng.

### Tổng hợp đa luồng: chọn công cụ nào?

| Bạn cần | Công cụ | Bài |
|---|---|---|
| Chạy một việc dài trên luồng riêng, tự quản `join` | `std::thread` (bọc RAII) | [24](24-thread-co-ban.md) |
| Giao một việc và **nhận kết quả hay ngoại lệ** | `std::async` + `std::future` (hoặc `promise`) | [29](29-async-future.md) |
| Bảo vệ dữ liệu chung gồm nhiều biến | `std::mutex` + `lock_guard`/`scoped_lock` | [25](25-data-race-mutex.md), [26](26-deadlock.md) |
| Một bộ đếm hay một cờ đơn | `std::atomic` | [28](28-atomic.md) |
| Chờ một điều kiện do luồng khác tạo | `std::condition_variable` + predicate | [27](27-condition-variable.md) |
| Nhiều việc nhỏ, đều đặn, cần giới hạn số luồng | thread pool | bài này |

### Câu hỏi đa luồng hay gặp (và nơi ôn)

- `join` khác `detach`; điều gì xảy ra khi hủy `std::thread` còn joinable; truyền tham chiếu vào luồng cần gì: [Bài 24](24-thread-co-ban.md).
- Data race là gì, khác race condition ra sao; `lock_guard` khác `unique_lock`; vì sao phạm vi khóa nhỏ nhất: [Bài 25](25-data-race-mutex.md).
- Bốn điều kiện của deadlock; tránh bằng thứ tự khóa hoặc `std::scoped_lock`: [Bài 26](26-deadlock.md).
- Spurious wakeup là gì; vì sao `wait` cần predicate và `unique_lock`; `notify_one` hay `notify_all`: [Bài 27](27-condition-variable.md).
- Atomic khác mutex ở đâu; `compare_exchange` làm gì; vì sao `volatile` không thay được atomic: [Bài 28](28-atomic.md).
- `std::async` có mặc định chạy luồng mới không; `future::get` hai lần; ngoại lệ đi qua `future`: [Bài 29](29-async-future.md).
- Cài producer-consumer và thread pool từ đầu: [Bài 27](27-condition-variable.md) và bài này.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Hàm hủy pool quên `notify_all`, hoặc không `join`"
    Quên `notify_all` thì worker đang ngủ không biết cờ dừng đã đổi: mình chạy ra treo, mã 124, nhiều hay ít tùy mức `-O` (mục 💻 ví dụ 1). Không `join` thì hủy `std::thread` còn joinable gọi `std::terminate` ([Bài 24](24-thread-co-ban.md)).

!!! warning "Lỗi 2: Giữ khóa lúc chạy việc, hoặc để ngoại lệ thoát khỏi việc"
    Chạy `viec()` khi còn giữ `lk` thì mọi worker chờ nhau, pool thành tuần tự. Ngoại lệ không bắt trong việc làm cả chương trình `terminate` (mình chạy: mã 134); listing đã bọc `try`/`catch`, hoặc dùng `packaged_task`.

!!! warning "Lỗi 3: Dùng pool (hoặc nhiều luồng) cho việc quá nhỏ, và đo khi bật TSan"
    Mình đo: 20000 việc cỡ vài chục phép cộng, tuần tự 0 đến 1 ms còn pool 6 đến 33 ms. Hãy đo trước khi song song hóa; và đừng đo tốc độ với `-fsanitize=thread` vì nó chậm hơn nhiều lần.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="30" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Trong pool ở bài này, worker lấy việc ra, nhả khóa rồi mới gọi `viec()`. Vì sao không gọi khi còn giữ khóa?

- Vì `std::function` không được gọi trong lúc một mutex đang bị khóa
- Vì giữ khóa thì các worker phải chạy lần lượt, mất lợi ích nhiều luồng
- Vì khóa tự nhả khi việc kết thúc nên phải nhả trước cho đỡ trùng
- Vì hàng đợi cần được nhả khóa thì `pop` mới có hiệu lực với worker khác

<p class="giai-thich" markdown>Mutex cho một luồng vào một lúc; nếu `viec()` chạy khi còn giữ khóa thì worker khác không lấy được việc và việc chạy lần lượt như tuần tự. Gọi một `std::function` khi đang giữ mutex hoàn toàn hợp lệ, chỉ là chậm. Khóa `unique_lock` chỉ tự nhả khi nó bị hủy hay khi gọi `unlock`, không tự nhả khi việc kết thúc. Còn `pop` có hiệu lực ngay khi gọi, không đợi nhả khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đọc đoạn sau: hàm hủy của pool bị bỏ dòng `notify_all`. Pool đã tạo xong 4 worker, chưa nộp việc nào, và cả bốn đang ngủ trong `wait`. Rồi pool bị hủy. Điều gì xảy ra?

```text
~NhomLuong() {
    { std::lock_guard<std::mutex> g(khoa_);  dung_ = true; }
    // đã bỏ dòng cv_.notify_all();
    for (std::thread& t : worker_) t.join();
}
```

- Hủy êm, vì `dung_` đã `true` nên các worker tự nhận ra và thoát
- Chương trình gọi `std::terminate`, vì worker vẫn còn joinable lúc hủy
- Hủy êm, vì `join` tự đánh thức worker đang ngủ rồi chờ chúng thoát
- Treo ở `join`, vì worker đang ngủ mà không ai gọi dậy để thấy `dung_`

<p class="giai-thich" markdown>Worker chỉ kiểm lại predicate khi được đánh thức; đổi `dung_` không đánh thức ai, nên cả bốn ngủ tiếp và `join` chờ mãi (mình chạy: mã 124; chuẩn cho phép đánh thức giả nên không hứa chắc). Chúng không tự nhận ra thay đổi vì `wait` không theo dõi biến. `join` chỉ chờ luồng kết thúc, không gọi ai dậy. Còn `std::terminate` xảy ra khi hủy `std::thread` chưa `join`, mà ở đây `join` được gọi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Máy có `hardware_concurrency() == 8`. Cần chạy 100 việc, mỗi việc chủ yếu **chờ mạng** 10 ms rồi tính một chút. Số worker nào hợp lý nhất?

- Nhiều hơn 8, vì worker đang chờ mạng thì không chiếm CPU
- Ít hơn 8, vì nhiều worker thì tranh khóa hàng đợi rất nặng
- Đúng 1, vì chờ mạng thì một worker làm lần lượt là đủ
- Đúng 8, vì `hardware_concurrency` là số worker được khuyên dùng

<p class="giai-thich" markdown>Việc chờ mạng không dùng CPU, nên khi một worker chờ thì lõi đó chạy worker khác; vì vậy nhiều worker hơn số lõi vẫn làm xong nhiều việc hơn (mình thử với việc ngủ 10 ms: 4 worker mất khoảng 252 ms, 32 worker khoảng 43 ms). Quy tắc "bằng số lõi" chỉ hợp việc nặng CPU, và `hardware_concurrency` chỉ là gợi ý về phần cứng. Tranh khóa hàng đợi có thật nhưng nhỏ so với 10 ms chờ mỗi việc, nên ít worker hơn chỉ làm chậm thêm. Chỉ một worker thì 100 việc nối đuôi nhau mất cỡ 100 lần 10 ms, trong khi chờ mạng không cần chiếm lõi nào.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Luồng 1 chỉ `fetch_add` trên `a`, luồng 2 chỉ `fetch_add` trên `b`, mỗi luồng 5 triệu lần. Với `Gan` chạy chậm hơn nhiều so với `Xa` (mình đo khoảng 3 đến 4 lần). Vì sao?

```text
struct Gan { std::atomic<long long> a;  std::atomic<long long> b; };
struct Xa  { alignas(64) std::atomic<long long> a;
             alignas(64) std::atomic<long long> b; };
```

- Hai luồng cùng tăng một biến nên bị data race và phải chờ nhau
- Hai atomic khác nhau dùng chung một mutex ngầm nên phải lần lượt
- `a` và `b` rất có thể chung dòng cache nên hai lõi giành dòng đó
- `alignas(64)` tắt bộ nhớ đệm của CPU nên các lõi khỏi phải giành

<p class="giai-thich" markdown>`Gan` dài 16 byte, nên `a` và `b` rất có thể nằm trong cùng dòng cache 64 byte; mỗi lần một lõi ghi, nó giành cả dòng, ép lõi kia nạp lại: false sharing. `a` và `b` là hai biến khác nhau nên không có data race, và không có mutex ngầm nào dùng chung. `alignas(64)` không tắt cache: nó chỉ đặt hai biến vào hai dòng khác nhau.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Một chương trình có một nửa thời gian chạy bắt buộc tuần tự (`p = 0,5`). Theo định luật Amdahl, thêm thật nhiều lõi thì tăng tốc tối đa khoảng bao nhiêu?

- Gần bằng số lõi, vì nửa kia chia đều được cho mọi lõi
- Dưới 2 lần, tiến dần tới 2 khi số lõi rất lớn
- Cỡ 4 lần, vì một nửa chương trình được chia cho 8 lõi
- Không có giới hạn, nếu mỗi lõi có dòng cache riêng

<p class="giai-thich" markdown>Với `p = 0,5`, công thức `1 / ((1 - p) + p / n)` ra `1 / (0,5 + 0,5 / n)`, luôn dưới 2 và tiến tới 2 khi `n` lớn: nửa tuần tự không lõi nào chia được. "Gần bằng số lõi" chỉ đúng khi phần tuần tự gần 0. Con số 4 không rút ra từ công thức nào. Còn dòng cache riêng chỉ tránh false sharing, không làm mất phần tuần tự.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn Go sau. Một goroutine nhận bằng vòng `range`. Channel `jobs` **có đệm**. Bên gửi gửi 3 giá trị vào `jobs` rồi gọi `close(jobs)`, lúc đó goroutine nhận mới nhận được 2 giá trị. Vòng `for job := range jobs` làm gì?

```text
for job := range jobs { xuLy(job) }
// ... chỗ gửi:  jobs <- 1;  jobs <- 2;  jobs <- 3;  close(jobs)
```

- Vẫn nhận nốt giá trị còn lại, rồi thoát khi channel đã đóng và cạn
- Thoát ngay khi `close`, bỏ giá trị chưa nhận để dừng cho nhanh
- Thoát ngay khi channel tạm rỗng, rồi phải gọi `range` lại để nhận tiếp
- Không bao giờ thoát, vì phải có `break` hoặc `return` mới ra khỏi `range`

<p class="giai-thich" markdown>`range` trên channel nhận cho tới khi channel đã `close` **và** hết giá trị, nên việc còn lại vẫn được xử lý rồi vòng mới kết thúc; đó là hành vi "làm hết việc rồi dừng" như pool C++ của bài. Nó không bỏ giá trị chưa nhận. Channel rỗng nhưng còn mở thì `range` chờ chứ không thoát. Và sau `close`, vòng thoát tự nhiên mà không cần `break`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau. Pool đang chạy (bản worker chỉ gọi `viec();`, không bọc `try`/`catch`), việc thứ 500 thực hiện `throw std::runtime_error("loi")`. Điều gì xảy ra?

```text
nhom.submit([&tong, i] {
    if (i == 500) throw std::runtime_error("loi");
    tong += i;
});
```

- Ngoại lệ được ném lại ở `main` khi pool bị hủy ở cuối khối
- Worker đó bỏ qua việc này và tiếp tục nhận việc kế tiếp bình thường
- Ngoại lệ đi vào một `future` ngầm của pool và chờ `get()` mới ném ra
- Ngoại lệ thoát khỏi hàm của luồng, chương trình gọi `std::terminate`

<p class="giai-thich" markdown>Việc chạy trên luồng của worker; ngoại lệ không ai bắt thoát khỏi hàm luồng thì chương trình gọi `std::terminate` (mình chạy: mã 134). Không có cơ chế nào chuyển ngoại lệ về `main` khi hủy pool. Worker cũng không tự bỏ qua: không có `catch` nào để bỏ qua. Còn `future` chỉ có khi bạn dùng `packaged_task`; `submit` kiểu `void` không có `future` ngầm.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Mỗi việc một luồng tốn chi phí tạo và hủy luồng, lớn hơn chính việc nhỏ (mình đo: 20000 việc nhỏ mất hơn 600 ms nếu mỗi việc một luồng); thread pool tạo N luồng một lần rồi tái sử dụng.
2. Pool tự cài là ba mảnh của [Bài 27](27-condition-variable.md): `std::queue<std::function<void()>>` dưới mutex, `condition_variable`, N worker; worker lấy việc, nhả khóa, **chạy ngoài khóa**; hàm hủy (RAII) đặt cờ dưới khóa + `notify_all` + `join`, làm hết việc còn lại rồi thoát (quên `notify_all` thì treo hay không tùy mức `-O` và lần chạy, mình chạy). `packaged_task` trong `shared_ptr` cho `submit` trả `future`; ngoại lệ không bắt trong việc là `terminate` (listing bọc `try`/`catch (...)` thì nuốt nó).
3. Số worker ≈ `hardware_concurrency()` cho việc nặng CPU; việc chờ I/O thì nhiều hơn số lõi vẫn có lợi. Việc quá nhỏ thì tuần tự thắng cả pool (số đo đổi theo máy và `-O`, mẫu thì ổn định).
4. False sharing: hai biến khác nhau chung dòng cache (thường 64 byte) làm chậm dù không có data race (mình đo: khoảng 3 đến 4 lần); gỡ bằng `alignas(64)` hoặc đệm. Amdahl: tăng tốc tối đa `1 / ((1 - p) + p / n)`, không vượt `1 / (1 - p)`; vùng găng và đồng bộ tính vào phần tuần tự.
5. Chọn công cụ: `thread` cho việc dài, `async`/`future` khi cần kết quả, `mutex` cho dữ liệu chung, `atomic` cho một bộ đếm hay cờ, `condition_variable` để chờ điều kiện, pool cho nhiều việc nhỏ. Go không cần tự cài pool vì goroutine rẻ; khi cần giới hạn thì `for job := range jobs` + `WaitGroup`.
