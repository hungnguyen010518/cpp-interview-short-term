# Bài 27 — condition_variable: chờ điều kiện thay vì hỏi liên tục

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao một luồng cần **chờ một điều kiện** do luồng khác tạo ra, và vì sao vòng `while (!xong) { ngủ; }` hoặc vòng không ngủ đều dở (đã chạy thật: một bản đốt CPU, một bản trả lời trễ).
    - Dùng `std::condition_variable` cùng `std::mutex` và `std::unique_lock` (nối [Bài 25](25-data-race-mutex.md)): vì sao `wait` cần `unique_lock` mà không phải `lock_guard`, và vì sao luôn dùng dạng `wait(lk, predicate)` (predicate: điều kiện để thôi chờ): chuẩn cho phép **spurious wakeup** (đánh thức giả), và `notify` gọi trước `wait` thì bị mất.
    - Phân biệt `notify_one` với `notify_all`, biết notify trong hay sau khi nhả khóa đều đúng, và nhắc được `wait_for` (có hạn chờ).
    - Viết mẫu **producer-consumer** với `std::queue` được bảo vệ, dừng sạch bằng cờ `xong` đặt dưới khóa kèm `notify_all`; so với channel và `sync.Cond` của Go.

**Bạn cần biết trước:** [Bài 24](24-thread-co-ban.md) (`std::thread`, `join`, `sleep_for`, `vector<thread>`), [Bài 25](25-data-race-mutex.md) (`std::mutex`, `lock_guard`, `unique_lock`, vùng găng, TSan), [Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md) (`std::queue`: `push`, `front`, `pop`, `empty`), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, vị từ), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda `[&x]`), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector<long long> v(2, 0)`: hai phần tử, đều bằng 0), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`điều kiện ? A : B`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](25-data-race-mutex.md), với một thớt chung và một thẻ vào thớt. Giờ có hai người phụ thuộc nhau: đầu bếp chính cần hành đã sơ chế, mà hành do đầu bếp phụ chuẩn bị, mất một lúc. Chính chưa thể thái cho tới khi phụ xong.

Có hai cách chờ tồi. Cách một: chính đứng ngay cạnh thớt và nhìn **không ngừng**, mệt và chẳng làm được việc gì khác. Cách hai: cứ vài phút chính ghé nhìn một lần rồi đi ngủ; đỡ mệt, nhưng hành xong từ lâu mà chính vẫn chưa hay.

Cách tốt: chính **để thẻ thớt lại** (để phụ còn có thẻ mà đặt hành lên thớt), ngồi xuống ghế và ngủ. Phụ chuẩn bị xong thì **bấm chuông**. Chuông reo, chính dậy, xin lại thẻ thớt rồi làm. Cái chuông chính là `std::condition_variable`.

!!! info "Chỗ nào ví von cái chuông không còn đúng?"
    Chuông của bếp thật chỉ reo khi có người bấm, còn `condition_variable` thì chuẩn C++ **cho phép** `wait` trả về dù chẳng ai bấm (mục 3). Chuông thật cũng không "quên": bấm lúc chính chưa ngồi vào ghế thì chính nhìn thấy hành đã có. Với `condition_variable`, bấm khi chưa ai ngồi chờ là bấm vào khoảng không, và tiếng chuông mất luôn. Hai chỗ này là lý do cả bài xoay quanh một **biến điều kiện** (hành đã xong chưa) thay vì tin vào tiếng chuông.

## 📖 Giải thích

### 1. Vì sao cần chờ điều kiện: hai cách chờ tồi

Chương trình dưới có luồng phụ "chuẩn bị dữ liệu" mất 1 giây rồi đặt cờ `xong`; luồng chính chờ cờ đó bằng một **vòng chờ bận** (busy waiting: lặp lại việc kiểm tra liên tục, không ngủ). Cờ và dữ liệu luôn được đọc/ghi dưới khóa ([Bài 25](25-data-race-mutex.md)). `std::chrono::seconds(1)` là khoảng 1 giây, cùng họ với `milliseconds` ở [Bài 24](24-thread-co-ban.md). `while (true)` là vòng lặp không có điều kiện dừng (như `for { }` của Go), chỉ thoát bằng `break`.

```cpp
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
bool xong = false;                 // true khi luồng phụ đã chuẩn bị xong
int duLieu = 0;

int main() {
    std::thread phu([] {
        std::this_thread::sleep_for(std::chrono::seconds(1));   // (1) "chuẩn bị" mất 1 giây
        std::lock_guard<std::mutex> g(khoa);
        duLieu = 42;
        xong = true;
    });

    while (true) {                                              // (2) vòng chờ bận
        std::lock_guard<std::mutex> g(khoa);
        if (xong) break;
    }
    std::cout << "nhan duoc " << duLieu << "\n";
    phu.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Luồng phụ ngủ 1 giây (giả vờ chuẩn bị), rồi khóa, đặt `duLieu` và `xong` |
| (2) | Luồng chính khóa, nhìn `xong`, nhả khóa, rồi lặp ngay, không nghỉ |

**Kết quả khi chạy** (đo bằng `time ./chuongtrinh` trong shell, mình biên dịch sạch cảnh báo và TSan cũng sạch):

```text
nhan duoc 42
real	0m1,004s
user	0m1,002s
```

`real` là thời gian trôi qua, `user` là thời gian CPU chương trình thực sự dùng. Hai số gần bằng nhau: luồng chính **đốt gần trọn một lõi CPU trong 1 giây** chỉ để nhìn một cờ. Con số khác nhau theo máy, nhưng mẫu "user gần bằng real" là mẫu của chờ bận.

**Thử thay đổi: thêm `std::this_thread::sleep_for(std::chrono::milliseconds(100));` vào cuối vòng lặp** (sau khối khóa, để ngủ lúc không giữ khóa). Mình đã chạy (cho luồng phụ ngủ 1010 ms và đo thêm bằng `std::chrono::steady_clock`):

- `user` chỉ cỡ 0,001 giây, vì luồng chính ngủ gần hết thời gian.
- Luồng chính biết tin trễ **khoảng 90 ms** sau khi dữ liệu sẵn sàng (ba lần chạy: 91, 90, 90).

Mình chọn 1010 ms để cờ đến ngay sau một lần hỏi, nên trễ gần mức tối đa (một chu kỳ ngủ); trung bình khoảng nửa chu kỳ. Vòng ngủ-rồi-hỏi tốn gần như không CPU nhưng trễ; ngủ ngắn lại thì trễ ít đi mà CPU tốn trở lại.

Ta muốn: **không tốn CPU lúc chờ, và biết tin ngay khi có**. Hệ điều hành làm được chuyện đó nếu luồng chờ xin "đánh thức tôi khi có tin".

### 2. `std::condition_variable`: chờ và đánh thức

`std::condition_variable` (`#include <condition_variable>`) là chiếc chuông. Một cuộc chờ luôn có **ba mảnh** đi cùng nhau:

- một `std::mutex` bảo vệ dữ liệu chung;
- một **biến điều kiện** thường (ở đây là `bool xong`), được đổi **dưới khóa**;
- một `std::condition_variable` để ngủ chờ và để gọi dậy.

Luồng chờ gọi `cv.wait(lk, vịTừ)`; luồng báo tin đổi biến dưới khóa rồi gọi `cv.notify_one()`. (`vịTừ` là một lambda trả `bool` như ở [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md); với `wait` ta gọi nó là **predicate**, điều kiện để thôi chờ.)

```cpp
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable cv;
bool xong = false;
int duLieu = 0;

int main() {
    std::thread phu([] {
        std::this_thread::sleep_for(std::chrono::seconds(1));   // (1) chuẩn bị dữ liệu
        {
            std::lock_guard<std::mutex> g(khoa);                // (2) đổi dữ liệu dưới khóa
            duLieu = 42;
            xong = true;
        }                                                       // (3) nhả khóa
        cv.notify_one();                                        // (4) đánh thức người đang chờ
    });

    std::unique_lock<std::mutex> lk(khoa);                      // (5) xin khóa bằng unique_lock
    cv.wait(lk, [] { return xong; });                           // (6) chờ tới khi xong == true
    std::cout << "nhan duoc " << duLieu << "\n";                // (7) vẫn đang giữ khóa
    lk.unlock();
    phu.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (5) | Luồng chính xin khóa (như `lock_guard`, nhưng bằng `unique_lock`) |
| (6) | `wait` kiểm predicate: `xong` còn `false`, nên nó **nhả khóa và ngủ** (không tốn CPU) |
| (1)-(3) | Luồng phụ xin được khóa (vì chính đã nhả), đặt dữ liệu, trả khóa |
| (4) | `notify_one` đánh thức luồng chính |
| (6) | Luồng chính dậy, **xin lại khóa**, kiểm lại predicate: `true`, nên `wait` trả về |
| (7) | In ra khi luồng chính đang giữ khóa; rồi `unlock()` để không giữ khóa lúc `join` chờ luồng phụ |

**Kết quả khi chạy:** `nhan duoc 42`; `time` ra `real 1,005 s` nhưng `user` chỉ `0,001 s`, trong khi bản chờ bận ở mục 1 ra `user 1,002 s`. Mình cũng đo độ trễ từ lúc đặt cờ đến lúc luồng chính dậy: ba lần, 22 đến 58 **micro**giây (khác nhau theo máy), so với ~90 **mili**giây của vòng ngủ. TSan (`setarch $(uname -m) -R`, [Bài 25](25-data-race-mutex.md)) không báo gì.

!!! question "Hỏi nhanh: vì sao `wait` đòi `unique_lock` mà không nhận `lock_guard`?"
    `wait` phải làm hai việc **mà `lock_guard` không cho làm**: nhả khóa trước khi ngủ (nếu không, luồng phụ không bao giờ xin được khóa để đổi `xong`: deadlock như [Bài 26](26-deadlock.md)), rồi xin lại khóa khi dậy. `lock_guard` chỉ xin lúc tạo và trả lúc hủy, không có `unlock()`/`lock()`; `unique_lock` có ([Bài 25](25-data-race-mutex.md) mục 5). Chuẩn nói `wait` làm trọn "nhả khóa và đi ngủ" như **một bước không bị xen vào**, nên không có khe hở giữa nhả và ngủ để tin báo lọt qua.

### 3. Luôn dùng `wait(lk, predicate)`: spurious wakeup và lost wakeup

Dạng `cv.wait(lk, pred)` tương đương với:

```text
while (!pred()) {
    cv.wait(lk);        // nhả khóa, ngủ; dậy thì xin lại khóa
}
```

Vòng `while` này không phải để cho đẹp. Có **ba lý do** phải kiểm điều kiện: hai lý do cho lúc **sau khi dậy** (hai mục đầu), một lý do cho lúc **trước khi ngủ** (mục cuối):

- **Spurious wakeup** (đánh thức giả): chuẩn C++ **cho phép** `wait` trả về mà không ai gọi `notify`. Mình không tái hiện được trên máy này và không đưa ví dụ nào ra; bạn chỉ cần biết chuẩn cho phép, nên không được giả định "dậy nghĩa là có tin".
- **Món bị lấy mất:** khi có nhiều luồng chờ, `notify_one` đánh thức luồng A, nhưng luồng B tới nhanh hơn và lấy mất món trước khi A xin lại được khóa. A dậy thấy món không còn, phải ngủ lại. Lý do này không cần chuẩn cho phép gì thêm.
- **Lost wakeup** (mất thông báo): `notify` chỉ đánh thức luồng **đang chờ lúc đó**. Gọi `notify` khi chưa ai chờ thì nó biến mất, không ai nhớ giùm.

Lý do thứ ba nguy hiểm nhất, nên xem tận mắt. Luồng phụ gọi `notify_one` ngay; luồng chính tới trễ 300 ms rồi gọi `wait` **không** có predicate:

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable cv;

int main() {
    std::thread phu([] {
        cv.notify_one();                                          // (1) notify ngay, chưa ai chờ
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(300));  // (2) main tới trễ
    std::unique_lock<std::mutex> lk(khoa);
    cv.wait(lk);                                                  // (3) wait không predicate
    std::cout << "xong\n";
    phu.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Luồng phụ gọi `notify_one` khi chưa luồng nào chờ: tiếng chuông mất |
| (2) | Luồng chính ngủ 300 ms, tới sau khi tiếng chuông đã mất |
| (3) | `wait` không có predicate nên ngủ ngay; không ai báo nữa, nên ngủ mãi |

**Kết quả khi chạy:** mình biên dịch sạch cảnh báo; chạy `timeout 3 ./chuongtrinh` thì **không in gì**, `timeout` thoát mã **124**. Tiếng chuông ở (1) đã mất, nên (3) ngủ không ai gọi. Khối đặt `// bo-qua-kiem-tra` vì nó treo. Chuẩn không hứa là nó treo (spurious wakeup có thể làm nó dậy), mình chỉ nói điều mình thấy trên máy này.

**Thử thay đổi: lấy chương trình ở mục 3, thêm `bool xong` đặt thành `true` dưới khóa trước `notify_one`, và đổi `wait` thành `wait(lk, [] { return xong; })`.** Vậy `notify_one` vẫn đến **trước** `wait` (luồng chính còn ngủ 300 ms), nhưng `wait` giờ có predicate. Mình đã chạy: in `xong`, không treo (TSan sạch). Predicate được kiểm **trước khi ngủ** (như vòng `while` ở trên): `xong` đã `true` nên `wait` không ngủ. Trạng thái nằm trong biến, không nằm trong tiếng chuông.

!!! warning "Hay nhầm"
    Biến điều kiện phải được đổi **dưới cùng mutex** mà luồng chờ dùng, kể cả khi nó chỉ là một `bool`. Đổi ngoài khóa thì có thể rơi đúng vào khe giữa lúc luồng chờ kiểm `xong` (thấy `false`) và lúc nó ngủ: tin đến mà không ai nhận, lost wakeup trá hình, và còn là data race ([Bài 25](25-data-race-mutex.md)) vì hai luồng đụng cùng một biến không đồng bộ. Hàng đợi ở mục 💻 cũng thế: mọi `push`/`pop` đều dưới khóa.

### 4. `notify_one` hay `notify_all`, và notify lúc nào

- `notify_one()` đánh thức **nhiều nhất một** luồng đang chờ trên `cv` đó (chuẩn không nói là luồng nào).
- `notify_all()` đánh thức **tất cả** luồng đang chờ; chúng dậy lần lượt vì phải xin lại cùng một khóa.

Quy tắc dễ nhớ: **một món mới, chỉ một người dùng được** thì `notify_one`; **một thay đổi mà mọi người đều phải biết** (như "hết việc, dừng") thì `notify_all`. Lỡ dùng `notify_one` để báo dừng khi có hai consumer cùng đang chờ, thì một luồng thoát, luồng kia ngủ tiếp không ai gọi (trên máy mình là mãi; chuẩn cho phép đánh thức giả; mục 💻 có thử thật).

**Notify trong khi giữ khóa hay sau khi nhả?** Cả hai đều đúng theo chuẩn: `notify` không đòi bạn giữ khóa. Nhả trước rồi mới notify (như dòng (3)-(4) ở mục 2) thường **được khuyên dùng**: luồng vừa được đánh thức khỏi phải ngay lập tức bị chặn lại vì khóa vẫn nằm trong tay người báo tin. Một số cài đặt tự tối ưu chuyện này nên chênh lệch tùy thư viện và máy; mình không đo, nên đừng coi đó là luật. Giữ khóa lúc notify đôi khi lại cần, ví dụ khi luồng chờ sẽ hủy chính `cv` ngay lúc dậy.

## 💻 Ví dụ code

### Producer-consumer: hàng đợi chung và dừng sạch

**Producer-consumer** (người sản xuất, người tiêu thụ) là mẫu thông dụng nhất của `condition_variable`: một nhóm luồng **tạo việc** bỏ vào hàng đợi chung, một nhóm luồng khác **lấy việc ra làm**. Hàng đợi là `std::queue<int>` ([Bài 21](../nhom-2-stl-thuat-toan/21-big-o-cau-truc-du-lieu.md)); nó không an toàn luồng, nên mọi thao tác dưới khóa. Trong bếp: producer đặt đĩa lên quầy, consumer lấy đĩa đi nấu.

Chương trình: producer đưa các số 1..1000, hai consumer chia nhau lấy. Ai lấy số nào đổi theo lần chạy, nên **không in thứ tự**: chỉ in tổng và số việc sau khi mọi luồng `join`. Mỗi consumer cộng vào ô riêng của mình (`tong[k]`), nên không cần khóa cho việc cộng.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

std::mutex khoa;
std::condition_variable cv;
std::queue<int> hang;              // hàng đợi chung, luôn truy cập dưới khóa
bool xong = false;                 // producer đã giao hết việc

int main() {
    std::vector<long long> tong(2, 0);   // mỗi consumer cộng vào ô riêng của mình
    std::vector<int> soViec(2, 0);

    std::vector<std::thread> consumer;
    for (int k = 0; k < 2; ++k) {
        consumer.emplace_back([&tong, &soViec, k] {
            while (true) {
                std::unique_lock<std::mutex> lk(khoa);
                cv.wait(lk, [] { return !hang.empty() || xong; });   // (1)
                if (hang.empty()) break;                             // (2) xong và hết việc
                int v = hang.front();
                hang.pop();
                lk.unlock();                                         // (3) xử lý ngoài khóa
                tong[k] += v;
                ++soViec[k];
            }
        });
    }

    std::thread producer([] {
        for (int i = 1; i <= 1000; ++i) {
            {
                std::lock_guard<std::mutex> g(khoa);
                hang.push(i);                                        // (4)
            }
            cv.notify_one();                                         // (5)
        }
        {
            std::lock_guard<std::mutex> g(khoa);
            xong = true;                                             // (6) đặt cờ dưới khóa
        }
        cv.notify_all();                                             // (7) đánh thức mọi consumer
    });

    producer.join();
    for (std::thread& t : consumer) t.join();
    std::cout << "tong = " << tong[0] + tong[1]
              << ", so viec = " << soViec[0] + soViec[1] << "\n";
    return 0;
}
```

**Chạy từng dòng** (nhiều luồng chạy xen kẽ; bảng nói vai trò, không phải thứ tự cố định)

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Consumer chờ tới khi **có việc hoặc đã xong**: hàng không rỗng hay `xong == true` |
| (2) | Dậy mà hàng vẫn rỗng thì chỉ có thể là `xong`: hết việc, thoát vòng lặp (khóa `lk` tự nhả khi ra khỏi khối) |
| (3) | Lấy xong một số thì **nhả khóa ngay**; cộng vào `tong[k]` không đụng dữ liệu chung nên làm ngoài khóa |
| (4)-(5) | Producer đặt một số vào hàng dưới khóa, nhả khóa, rồi báo cho **một** consumer |
| (6)-(7) | Hết việc: đặt `xong` **dưới khóa**, rồi `notify_all` để **mọi** consumer đang ngủ dậy và thấy `xong` |

**Kết quả khi chạy:** `tong = 500500, so viec = 1000`. Mình biên dịch sạch cảnh báo (cả `-O2`), chạy 100 lần cùng đúng một dòng, và TSan không báo gì. Tổng 1 + 2 + ... + 1000 = 500500 luôn đúng, nhưng consumer nào xử lý bao nhiêu việc thì đổi theo lần chạy (mình không in).

Về cú pháp: `[&tong, &soViec, k]` trộn được hai kiểu bắt: `tong` và `soViec` bắt bằng tham chiếu, còn `k` bắt bằng **bản sao** (mỗi luồng giữ `k` của riêng nó; bắt tham chiếu thì vòng `for` đổi `k` ngay sau đó). Biến toàn cục như `xong`, `hang` không cần bắt, nên lambda `[]` rỗng vẫn đọc được chúng.

Ba điểm đáng nhớ:

- **Predicate có hai vế** (`!hang.empty() || xong`): consumer chỉ được thoát khi hàng đã **cạn**. Sau khi `xong = true`, vẫn còn việc trong hàng thì consumer vẫn lấy tiếp cho hết rồi mới thoát; không bị bỏ sót việc.
- **Dừng sạch** là ba bước: đặt cờ `xong` dưới khóa, `notify_all`, rồi `join`. Quên `notify_all`, consumer đang ngủ không biết cờ đổi (xem Lỗi 1).
- **Xử lý ngoài khóa** (dòng (3)): giữ khóa suốt lúc tính thì các consumer thành tuần tự, như phạm vi khóa nhỏ nhất ở [Bài 25](25-data-race-mutex.md).

**Thử thay đổi: ở dòng (7) đổi `notify_all()` thành `notify_one()`.** Mình đã chạy 100 lần: 99 lần ra đúng `tong = 500500`, **1 lần treo** (`timeout 3` mã 124). Con số đổi theo máy và theo lần chạy: chạy lại 100 lần khác có thể cho 0 lần treo, nên đừng dựa vào con số cụ thể. Chuẩn chỉ hứa `notify_one` đánh thức nhiều nhất một luồng, không hứa gì hơn.

- Treo xảy ra khi cả hai consumer đã ngủ lúc producer báo dừng: `notify_one` chỉ đánh thức một, luồng kia ngủ mãi và `join` chờ nó.
- Những lần "ổn" là cái bẫy: lỗi hiếm và hên xui như deadlock ở [Bài 26](26-deadlock.md).
- Để tái hiện chắc chắn, mình cho producer ngủ 200 ms và không đưa việc nào (cả hai consumer chắc chắn đang ngủ): treo, mã 124.

### `wait_for`: chờ có hạn

`wait_for(lk, khoảng, predicate)` giống `wait` nhưng chỉ chờ tối đa một khoảng thời gian; trả `true` nếu predicate đã đúng, `false` nếu hết giờ mà predicate vẫn sai. (`wait_until` nhận một thời điểm thay vì một khoảng.) Dùng khi luồng không được phép chờ vô hạn, giống `try_lock_for` ở [Bài 26](26-deadlock.md).

```cpp
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>

int main() {
    std::mutex khoa;
    std::condition_variable cv;
    std::unique_lock<std::mutex> lk(khoa);
    bool ok = cv.wait_for(lk, std::chrono::milliseconds(50), [] { return false; });
    std::cout << (ok ? "du dieu kien" : "het gio") << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| `unique_lock` | Luồng chính giữ khóa |
| `wait_for` | Kiểm predicate: `false`; nhả khóa, chờ 50 ms; hết giờ thì xin lại khóa, kiểm lần cuối, trả `false` |

Bản `wait_for` **không** predicate trả `std::cv_status` (`timeout` hay `no_timeout`) và có thể trả `no_timeout` do spurious wakeup, nên bài chỉ dùng dạng có predicate.

**Kết quả khi chạy:** `het gio` (sau khoảng 50 ms; `time` ra `real 0,053 s`). Predicate luôn sai và không ai notify, nên chỉ có hết giờ mới đưa nó ra khỏi `wait_for`.

### Hàng đợi có giới hạn: hai điều kiện, hai `condition_variable`

Ở chương trình trên, producer nhanh hơn consumer thì hàng phình mãi. Hàng đợi **có giới hạn** (bounded queue) chặn chuyện đó: hàng chứa tối đa 4 phần tử, đầy thì **producer** phải chờ. Giờ có **hai** điều kiện khác nhau (consumer chờ "có việc", producer chờ "còn chỗ"), nên dùng hai `condition_variable`, mỗi cái đánh thức đúng phía cần nó. `size_t` là kiểu số nguyên không âm mà `size()` trả về. `[&]` bắt mọi biến cục bộ bằng tham chiếu ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)).

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>

std::mutex khoa;
std::condition_variable conViec;     // "hàng có việc hoặc đã xong": consumer chờ
std::condition_variable conCho;      // "hàng còn chỗ": producer chờ
std::queue<int> hang;
bool xong = false;
const size_t TOI_DA = 4;             // hàng chứa tối đa 4 phần tử

int main() {
    size_t dinh = 0;                 // số phần tử nhiều nhất từng thấy trong hàng (đọc/ghi dưới khóa)
    long long tong = 0;

    std::thread consumer([&] {
        while (true) {
            std::unique_lock<std::mutex> lk(khoa);
            conViec.wait(lk, [] { return !hang.empty() || xong; });
            if (hang.empty()) break;
            int v = hang.front();
            hang.pop();
            lk.unlock();
            conCho.notify_one();                                   // (1) vừa có chỗ trống
            tong += v;
        }
    });

    std::thread producer([&] {
        for (int i = 1; i <= 1000; ++i) {
            std::unique_lock<std::mutex> lk(khoa);
            conCho.wait(lk, [] { return hang.size() < TOI_DA; });  // (2) hàng đầy thì chờ
            hang.push(i);
            if (hang.size() > dinh) dinh = hang.size();
            lk.unlock();
            conViec.notify_one();
        }
        {
            std::lock_guard<std::mutex> g(khoa);
            xong = true;
        }
        conViec.notify_all();
    });

    producer.join();
    consumer.join();
    std::cout << "tong = " << tong << ", dinh <= " << TOI_DA << ": " << (dinh <= TOI_DA ? "dung" : "sai") << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Consumer lấy một việc ra thì hàng có chỗ trống: báo `conCho` cho producer |
| (2) | Producer chờ tới khi `hang.size() < TOI_DA`; sau mỗi `push`, nó báo `conViec` cho consumer |

**Kết quả khi chạy:** `tong = 500500, dinh <= 4: dung`. Mình chạy 100 lần, cả 100 lần giống nhau, và TSan không báo gì. `dinh` là số phần tử nhiều nhất từng thấy trong hàng (ghi dưới khóa); nó không bao giờ vượt 4. Dùng một `cv` chung cho cả hai điều kiện cũng được nếu luôn `notify_all`, nhưng hai `cv` đánh thức đúng người hơn. Đây là nền cho thread pool ở [Bài 30](30-thread-pool-hieu-nang.md).

## Go: channel làm sẵn hàng đợi và chờ

!!! info "Bạn biết Go?"
    Mình đã chạy Go 1.27.1. Go có `sync.Cond` là bản **gần nhất** của `condition_variable`, nhưng ít khi là lựa chọn đầu tiên:

    - Channel làm sẵn việc ta vừa viết thủ công: `ch <- v` bỏ vào hàng đợi, `<-ch` lấy ra và **tự chờ** khi hàng rỗng; `close(ch)` thay cho cờ `xong` + `notify_all`, và `for v := range ch` thoát khi channel đóng và cạn (như dòng (2) ở trên). Chương trình Go dưới đây chạy ra `tong = 500500`, `-race` sạch.
    - `sync.Cond` gần nhất với `std::condition_variable`: `cond := sync.NewCond(&mu)`; luồng chờ khóa `mu` rồi viết `for !xong { cond.Wait() }` (**vòng `for` do bạn tự viết**, không có tham số predicate như `wait(lk, pred)` của C++); `Signal` ứng với `notify_one`, `Broadcast` với `notify_all`. `Wait` nhả `c.L` khi ngủ và khóa lại trước khi trả về, y như `wait`.
    - Tài liệu Go (`go doc sync.Cond.Wait`) dặn vẫn phải `Wait` trong vòng lặp vì khi `Wait` trả về điều kiện có thể đã đổi (goroutine khác lấy mất món). Khác C++ một điểm: tài liệu nói `Wait` **không trả về** trừ khi có `Signal`/`Broadcast`, tức Go không có spurious wakeup.
    - Thói quen Go là **truyền dữ liệu qua channel** thay vì nhiều goroutine cùng khóa biến chung rồi gọi chuông; `sync.Cond` hiếm gặp hơn nhiều trong code Go. C++ chuẩn **không có channel** ([Bài 24](24-thread-co-ban.md)), nên bạn tự ghép mutex + queue + `condition_variable`, hoặc dùng thư viện ngoài chuẩn.
    - Chờ có hạn: Go dùng `select` với `time.After(...)`; C++ dùng `wait_for`.

    ```go
    ch := make(chan int, 16)
    // ... hai goroutine: for v := range ch { tong[k] += v }
    for i := 1; i <= 1000; i++ { ch <- i }
    close(ch)                               // thay cho "xong = true; notify_all()"
    ```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::condition_variable` dùng để làm gì?"
    Để một luồng **ngủ chờ một điều kiện** do luồng khác tạo ra và được đánh thức khi điều kiện có thể đã đúng, thay vì chờ bận (tốn CPU) hay ngủ-rồi-hỏi (trả lời trễ). Luôn đi với một `std::mutex` bảo vệ dữ liệu của điều kiện và `std::unique_lock`: `wait` nhả khóa lúc ngủ và xin lại khi dậy. Luồng chờ gọi `cv.wait(lk, pred)`; luồng báo tin đổi dữ liệu dưới khóa rồi gọi `notify_one` hoặc `notify_all`.

??? question "Spurious wakeup là gì, vì sao cần predicate?"
    Spurious wakeup là việc `wait` trả về mà không ai gọi `notify`; chuẩn C++ cho phép điều đó, nên không được coi "dậy" là bằng chứng của "điều kiện đúng". Ngoài ra còn hai lý do không liên quan chuyện đó: luồng khác có thể lấy mất món giữa lúc `notify` và lúc luồng chờ xin lại được khóa, và `notify` gọi khi chưa ai chờ thì mất (lost wakeup). Vì vậy điều kiện nằm trong **biến** được bảo vệ bởi mutex, và `wait(lk, pred)` (tương đương `while (!pred()) wait(lk);`) kiểm nó **trước khi ngủ** và **sau mỗi lần dậy**.

??? question "Mô tả producer-consumer và cách dừng sạch."
    Producer bỏ việc vào một hàng đợi dùng chung (`std::queue`) dưới mutex rồi `notify_one`; consumer `wait` tới khi hàng không rỗng hoặc đã `xong`, lấy một việc ra, **nhả khóa**, rồi xử lý ngoài khóa. Dừng sạch: producer đặt cờ `xong = true` **dưới khóa** rồi `notify_all` (mọi consumer đang ngủ phải dậy); consumer thoát khi hàng rỗng **và** `xong`, nên việc còn lại trong hàng vẫn được làm hết; cuối cùng `join` các luồng. Dùng `notify_one` để báo dừng thì chỉ một consumer thoát, các consumer còn lại ngủ mãi.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Đổi điều kiện mà quên `notify`"
    Luồng chờ đang ngủ chỉ dậy khi có `notify` (hay một spurious wakeup mà bạn không nên trông chờ). Mình chạy: luồng phụ đặt `xong = true` dưới khóa nhưng không gọi `notify`, luồng chính đang `wait(lk, [] { return xong; })` từ trước: treo, `timeout 3` mã **124** (cả khi chạy TSan, vẫn 124).

!!! warning "Lỗi 2: `wait` không predicate, hoặc coi tiếng chuông là điều kiện"
    `cv.wait(lk);` trần chỉ đúng khi bạn chắc chắn `notify` luôn đến **sau** khi bạn đã ngủ, mà bạn không thể chắc (mục 3: treo, mã 124). Luôn viết `cv.wait(lk, [] { return điềuKiện; });`.

!!! warning "Lỗi 3: Giữ khóa lúc xử lý việc, hoặc báo dừng bằng `notify_one`"
    Giữ khóa suốt lúc xử lý làm các consumer chờ nhau, mất lợi ích của nhiều luồng; lấy việc ra, nhả khóa, rồi mới làm. Báo "dừng" bằng `notify_one` khi có nhiều consumer chờ thì chỉ đánh thức một (mục 💻: hiếm và hên xui, mình có lần thấy treo trong 100 lần chạy).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="27" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Luồng đang giữ `unique_lock lk` gọi `cv.wait(lk, pred)` và `pred()` đang trả `false`. Luồng đó làm gì?

- Nhả khóa và ngủ, rồi khi được đánh thức thì xin lại khóa và kiểm lại `pred`
- Giữ nguyên khóa và ngủ, để không luồng nào đổi được dữ liệu trong lúc chờ
- Nhả khóa và ngủ, rồi khi được đánh thức thì chạy tiếp mà không kiểm lại `pred`
- Giữ khóa và quay vòng liên tục tới khi `pred` đúng, như một vòng chờ bận

<p class="giai-thich" markdown>`wait` nhả khóa trước khi ngủ, nếu không luồng phụ không có cách xin khóa để làm `pred` đúng; khi dậy nó xin lại khóa và kiểm `pred` một lần nữa, vì dậy chưa chắc điều kiện đã đúng. Giữ khóa lúc ngủ sẽ làm chính luồng báo tin bị chặn, nên cả hai cùng kẹt. Chạy tiếp mà không kiểm lại bỏ qua spurious wakeup và việc món bị lấy mất. Còn quay vòng liên tục là chờ bận, đúng thứ `wait` sinh ra để thay thế.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đọc đoạn sau. Luồng A chạy xong hẳn trước, lúc luồng B chưa hề gọi `wait`. Sau đó luồng B chạy. Điều gì xảy ra ở B?

```text
std::mutex m;  std::condition_variable cv;  bool san = false;
// luồng A:  { std::lock_guard<std::mutex> g(m); san = true; }  cv.notify_one();
// luồng B:  std::unique_lock<std::mutex> lk(m);  cv.wait(lk, [] { return san; });
```

- B ngủ mãi, vì lời `notify_one` của A đã mất khi chưa có ai chờ
- B ngủ tới lần `notify` kế tiếp, vì `wait` chỉ thức sau một `notify` mới
- B chạy tiếp ngay, vì `san` đã `true` nên `wait` kiểm xong là không ngủ
- B bị ném ngoại lệ, vì không được gọi `notify_one` khi chưa có luồng chờ

<p class="giai-thich" markdown>`wait(lk, pred)` kiểm `pred` trước khi ngủ, mà `san` đã là `true` nên B đi tiếp ngay, không cần tiếng chuông nào. Tiếng `notify_one` của A đúng là bị mất, nhưng với predicate thì điều đó không còn quan trọng vì trạng thái nằm trong biến `san`; chỉ `wait` trần mới ngủ mãi. B cũng không đợi `notify` mới, vì nó không ngủ ngay từ đầu. Còn `notify_one` khi chưa ai chờ hoàn toàn hợp lệ, không ném ngoại lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Vì sao `condition_variable::wait` nhận `std::unique_lock` mà không nhận `std::lock_guard`?

- Vì `unique_lock` tự gọi `notify_one` khi nó bị hủy ở cuối khối
- Vì `wait` phải nhả khóa lúc ngủ rồi xin lại, mà `lock_guard` không nhả được
- Vì `unique_lock` nhanh hơn `lock_guard` nên chuẩn bắt buộc dùng nó
- Vì `lock_guard` không xin được khóa của mutex đã dùng với `condition_variable`

<p class="giai-thich" markdown>`wait` cần `unlock()` trước khi ngủ và `lock()` khi dậy; `unique_lock` có hai thao tác này, còn `lock_guard` chỉ xin lúc tạo và trả lúc hủy. Hàm hủy của `unique_lock` chỉ trả khóa, nó không gọi `notify` thay ai. Nó không nhanh hơn: ngược lại còn nặng hơn `lock_guard` một chút. Và `lock_guard` xin khóa mutex đó bình thường, vấn đề chỉ ở chỗ nó không nhả được giữa chừng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Đọc đoạn sau. Cuối cùng producer đặt `xong = true` dưới khóa rồi gọi `notify_all()`. Consumer đang ngủ trong `wait` khi đó sẽ làm gì?

```text
// consumer:
cv.wait(lk, [] { return !hang.empty(); });   // không có chỗ nào nhìn xong
int v = hang.front();  hang.pop();
```

- Thoát vòng lặp êm, vì `notify_all` đánh thức nó và cờ `xong` đã là `true`
- Gọi `front()` trên hàng rỗng, vì `notify_all` buộc nó chạy tiếp ngay
- Ném ngoại lệ, vì `wait` nhận ra sẽ không còn producer nào nữa
- Dậy, thấy hàng vẫn rỗng và ngủ lại, vì predicate chỉ nhìn hàng đợi

<p class="giai-thich" markdown>Dậy thì predicate được kiểm lại, và nó chỉ hỏi hàng có rỗng không, không hề đọc `xong`; hàng vẫn rỗng nên `wait` ngủ lại và `join` chờ mãi. Cờ `xong` có đổi cũng vô nghĩa nếu predicate không nhìn nó. Predicate chính là thứ chặn consumer gọi `front()` trên hàng rỗng, nên cách nói đó sai. Và `wait` không có cơ chế phát hiện producer đã kết thúc.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Hai consumer cùng đang ngủ trên một `condition_variable`, producer vừa đặt `xong = true`. Muốn cả hai thoát thì producer nên gọi gì?

- `notify_one`, vì khi một luồng dậy rồi thoát thì luồng kia tự dậy theo
- Không cần gọi gì, vì đặt `xong` dưới khóa là đủ cho mọi luồng biết
- `notify_one`, vì nó luôn đánh thức luồng đã chờ lâu nhất trước tiên
- `notify_all`, vì `notify_one` chỉ đánh thức nhiều nhất một luồng đang chờ

<p class="giai-thich" markdown>`notify_all` đánh thức mọi luồng đang chờ, nên cả hai consumer thấy `xong` và thoát. `notify_one` chỉ gọi dậy tối đa một luồng; luồng kia ngủ tiếp và không ai gọi nó, kể cả khi luồng đầu đã thoát. Đặt `xong` không đánh thức ai: luồng đang ngủ không tự kiểm lại biến. Còn chuẩn không nói `notify_one` chọn luồng nào, nên không có chuyện hứa chờ lâu nhất đi trước.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Vì sao nên luôn dùng `cv.wait(lk, pred)` thay vì `cv.wait(lk)` trần?

- Chuẩn cho phép `wait` trả về dù không ai notify, nên phải kiểm lại
- Có predicate thì `notify` chạy nhanh hơn vì không phải đánh thức luồng nào
- Không có predicate thì `wait` không nhả được khóa trong lúc nó ngủ
- Predicate tự gọi `notify_one` thay cho producer khi điều kiện đã đúng

<p class="giai-thich" markdown>Chuẩn cho phép đánh thức giả, và còn hai lý do nữa (món bị lấy mất, `notify` đến trước `wait`) khiến việc dậy không chứng minh điều kiện đúng; predicate kiểm nó trước khi ngủ và sau mỗi lần dậy. Predicate không làm `notify` nhanh hơn: nó chỉ là một hàm trả `bool` mà `wait` gọi. `wait` trần vẫn nhả khóa lúc ngủ như dạng có predicate. Và predicate không bao giờ tự gọi `notify`, đó là việc của luồng báo tin.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Đọc đoạn sau. Luồng chính đã ngủ trong `wait` từ trước. Sau 300 ms luồng phụ chạy dòng thứ nhất và kết thúc, không gọi thêm gì. Điều nào đúng?

```text
bool xong = false;
// luồng phụ:   { std::lock_guard<std::mutex> g(m); xong = true; }
// luồng chính: std::unique_lock<std::mutex> lk(m);  cv.wait(lk, [] { return xong; });
```

- Luồng chính dậy khi `xong` đổi, vì `wait` theo dõi biến trong predicate
- Luồng chính thường dậy khi luồng phụ nhả khóa, vì `wait` chờ chính khóa đó
- Không có gì đánh thức luồng chính, nên nó ngủ tiếp chứ không dậy
- Luồng chính dậy sau lần kiểm kế tiếp, vì `wait` tự kiểm predicate mỗi giây

<p class="giai-thich" markdown>Không ai gọi `notify`, nên không có gì đánh thức luồng chính; đây là lỗi quên `notify`, và mình đã chạy ra treo mã 124. Chuẩn cho phép đánh thức giả nên không thể hứa chắc là mãi mãi, và bạn không được dựa vào nó; trên máy mình thì treo. `wait` không theo dõi biến nào: predicate chỉ được gọi khi luồng chính dậy vì lý do khác. Nó cũng không chờ khóa (lúc đó luồng chính đã nhả khóa và ngủ trên `cv`), và không có đồng hồ kiểm mỗi giây nào.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** `sync.Cond.Wait` của Go khác `condition_variable::wait(lk, pred)` của C++ ở điểm nào?

- Nó nhận một predicate nhưng không nhả khóa `c.L` trong lúc nó ngủ chờ
- Nó không nhận predicate: bạn tự viết vòng `for !dieuKien { c.Wait() }`
- Nó nhả `c.L` khi ngủ nhưng không bao giờ khóa lại khi trả về cho bạn
- Nó không cần khóa nào, vì goroutine không bao giờ có data race với nhau

<p class="giai-thich" markdown>`Wait` của Go chỉ nhận một lần "chờ đánh thức", nên vòng `for` kiểm điều kiện là việc của bạn, còn C++ gói vòng đó vào `wait(lk, pred)`. Go vẫn nhả `c.L` khi ngủ như C++, nếu không người báo tin không khóa được. Nó cũng khóa lại `c.L` trước khi trả về, nên đoạn sau `Wait` được bảo vệ. Còn goroutine hoàn toàn có data race, `-race` của Go sinh ra để bắt chúng.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Luồng phải đợi điều kiện do luồng khác tạo ra thì đừng chờ bận (mình chạy: `user` ≈ `real`, đốt trọn một lõi) và đừng ngủ-rồi-hỏi (mình đo trễ ~90 ms ở chu kỳ 100 ms); `std::condition_variable` cho ngủ không tốn CPU mà dậy sau vài chục micro-giây (số đo trên máy mình).
2. Ba mảnh đi cùng nhau: `std::mutex`, biến điều kiện (đổi **dưới khóa**) và `std::condition_variable`; `wait` cần `std::unique_lock` vì nó phải nhả khóa lúc ngủ và xin lại khi dậy, việc `lock_guard` không làm được.
3. Luôn dùng `wait(lk, predicate)` (≡ `while (!pred()) wait(lk);`): chuẩn cho phép spurious wakeup, luồng khác có thể lấy mất món, và `notify` gọi trước `wait` thì mất (mình chạy `wait` trần: treo, mã 124); trạng thái nằm trong biến, không nằm trong tiếng chuông.
4. `notify_one` cho một món một người dùng; `notify_all` cho thay đổi mọi người phải biết (như dừng); notify trong hay sau khi nhả khóa đều đúng, nhả trước thường được khuyên (tùy cài đặt, mình không đo); `wait_for` chờ có hạn.
5. Producer-consumer: `std::queue` dưới khóa, consumer `wait` tới khi có việc hoặc `xong`, xử lý ngoài khóa; dừng sạch = đặt `xong` dưới khóa + `notify_all` + `join`. Go: channel và `close` làm sẵn cả hàng đợi lẫn chờ; `sync.Cond` là bản gần nhất (vòng `for` tự viết, `Signal`/`Broadcast`), nhưng hiếm dùng hơn channel.
