# Bài 65 — Thực chiến: in chẵn lẻ và in ABC xoay vòng bằng nhiều luồng

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải được đề kinh điển **hai luồng in 1..N xen kẽ lẻ/chẵn** bằng `mutex` + `condition_variable`: đặt "tới lượt ai" vào một **biến chung** (không vào tiếng `notify`), chờ bằng `wait(lk, vịTừ)`, và cho **cả hai luồng thoát** dù N lẻ hay chẵn.
    - Giải được đề **ba luồng in `ABCABC…` n lần** bằng mẫu "biến lượt", rồi bằng **chuỗi semaphore** (bản mô phỏng C++17, kèm bản `std::binary_semaphore` C++20), và nói được khi nào chọn cách nào.
    - Chạy thật bốn bản sai điển hình và đọc đúng triệu chứng: chờ trần không biến lượt (treo, mã 124), đọc biến thường không khóa (TSan báo data race, `-O2` treo), `if` thay vị từ (sai thứ tự hay treo), `notify_one` trên một `cv` chung với ba luồng (treo).
    - Phân biệt **chuẩn bảo đảm gì** với **máy này cho gì**, nêu chi phí (mỗi số in là một lần chuyển giao giữa hai luồng; `notify_all` thành "đánh thức cả đàn" khi nhiều luồng) và nói được khi nào KHÔNG nên viết kiểu này.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread` với hàm và đối số, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`mutex`, `unique_lock`, data race, TSan), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`wait` có vị từ, spurious và lost wakeup, `notify_one`/`notify_all`, `timeout` mã 124), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`std::string`, nối chuỗi), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) và [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `[&]`, vị từ), [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) (lớp `Semaphore` tự viết; mục 💻 chép lại cho bài đứng riêng được), [Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md) (chọn cơ chế đồng bộ).

## 🧠 Câu chuyện mở đầu

Phòng phỏng vấn, một tấm bảng trắng. Người phỏng vấn viết: "Hai luồng. Một luồng chỉ in số lẻ, một luồng chỉ in số chẵn. Chương trình phải in `1 2 3 4 …` đúng thứ tự tới N. Bạn có năm phút."

Bạn quen tay viết `lock_guard` quanh `cout`, và người phỏng vấn mỉm cười: "Mutex chỉ bảo đảm không ai in **cùng lúc**. Nó không nói **ai in trước**." Đó chính là đề: không phải bảo vệ dữ liệu, mà là **bắt các luồng đi theo một thứ tự**.

Trong **nhà bếp nhiều đầu bếp** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)): hai đầu bếp Lẻ và Chẵn cùng đánh số lên đĩa, nhưng đĩa phải ra quầy theo đúng thứ tự 1, 2, 3. Trên tường treo một **bảng "đĩa kế tiếp"** (một biến chung), thẻ vào thớt là mutex, và cái chuông là `condition_variable`. Đầu bếp nào cũng làm đúng một việc: nhìn **bảng**, thấy số của mình thì làm, xong thì sửa bảng và bấm chuông. Họ **không** nhìn chuông để biết có tới lượt mình không.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Bảng trên tường bếp thật ai cũng đọc được không cần xin gì. Với máy tính, đọc **và** sửa bảng đều phải dưới thẻ vào thớt, nếu không là data race ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Chuông bếp thật chỉ reo khi có người bấm, còn `wait` được phép trả về dù không ai bấm ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)): lại một lý do để tin **bảng**, không tin chuông.

## 📖 Giải thích

### 1. Đề (a): hai luồng in 1..N xen kẽ lẻ/chẵn

**Đề bài.**

- Đầu vào: số nguyên `N ≥ 0`. Đầu ra: các số `1 2 3 … N` đúng thứ tự, cách nhau một dấu cách.
- Đúng hai luồng: luồng **lẻ** chỉ in số lẻ, luồng **chẵn** chỉ in số chẵn.
- Dùng `std::mutex` và `std::condition_variable`; **không** chờ bận (vòng lặp đốt CPU), **không** dùng `sleep` để xếp thứ tự.
- Cả hai luồng phải **kết thúc** để `join` về, kể cả khi N lẻ (luồng chẵn không có số cuối) hay N = 0.

??? tip "Gợi ý 1"
    Hỏi: lúc nào đó, thông tin "bây giờ tới số mấy" nằm ở **đâu** để cả hai luồng cùng thấy? Nó không thể nằm trong "ai vừa được bấm chuông": chuông không nhớ gì ([Bài 27](../nhom-3-da-luong/27-condition-variable.md)).

??? tip "Gợi ý 2"
    Dùng một biến chung `so` = số **kế tiếp** cần in, chỉ đổi dưới khóa. Luồng lẻ chờ tới khi `so` lẻ, luồng chẵn chờ tới khi `so` chẵn. Đó là vị từ của `cv.wait(lk, vịTừ)`. In xong thì `++so` và báo cho luồng kia.

??? tip "Gợi ý 3"
    Còn một vế nữa của vị từ: khi `so > N` thì **không còn gì để in**, cả hai luồng phải thoát. Một luồng dậy mà thấy `so > N` thì `return`. Quên vế này, một trong hai luồng sẽ chờ một lượt không bao giờ đến.

**Hướng giải.** Mọi đề "bắt luồng đi theo thứ tự" đều có ba mảnh quen thuộc của [Bài 27](../nhom-3-da-luong/27-condition-variable.md): `mutex`, một **biến trạng thái** đổi dưới khóa (ở đây là `so`), và `condition_variable`. Cái mới của đề này là biến trạng thái **chính là thứ tự**. Gọi nó là **biến lượt**: vị từ của mỗi luồng là câu hỏi "lượt có phải của mình không, hoặc đã hết việc chưa?".

### 2. Đề (b): ba luồng in `ABCABC…` n lần

**Đề bài.**

- Đầu vào: số nguyên `n ≥ 0`. Đầu ra: chuỗi `ABC` lặp đúng n lần (`n = 5` ra `ABCABCABCABCABC`, 15 ký tự).
- Ba luồng: luồng 0 chỉ in `A`, luồng 1 chỉ in `B`, luồng 2 chỉ in `C`; mỗi luồng in đúng n ký tự.
- Làm hai cách: (1) `mutex` + `condition_variable` + biến `luot`; (2) **semaphore** (C++17 chưa có, nên dùng bản tự viết ở [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) làm mô phỏng).

??? tip "Gợi ý 1"
    Đề (a) có hai luồng nên "lẻ/chẵn" suy ra lượt được. Với ba luồng, hãy đặt tên thẳng: biến `luot` nhận giá trị 0, 1 hoặc 2, và luồng số `toi` chỉ được đi khi `luot == toi`.

??? tip "Gợi ý 2"
    Mỗi luồng lặp n lần: khóa, `wait` tới khi `luot == toi`, ghi ký tự, đặt `luot = (luot + 1) % 3` (phép `%` cho vòng 0, 1, 2, 0, …), nhả khóa, báo tin. Lần này mỗi luồng **tự biết n** nên không cần vế "hết việc" như đề (a).

??? tip "Gợi ý 3"
    Với ba luồng cùng chờ trên **một** `cv`, hỏi: khi `notify_one`, luồng nào được dậy? Chuẩn không nói. Còn với semaphore: ba bộ đếm, `luotA` bắt đầu bằng 1, hai bộ kia bằng 0; mỗi luồng `acquire` bộ của mình rồi `release` bộ của luồng kế. Tại sao bộ đầu bằng 1 mà không phải 0?

**Hướng giải.** Cách (1) là đề (a) mở rộng. Cách (2) đổi chỗ đặt trạng thái: không còn biến `luot`, mà **số thẻ** của ba semaphore *là* lượt (thẻ ở đâu thì lượt ở đó). Semaphore **nhớ** `release` trong bộ đếm, nên không có lost wakeup ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md)); đổi lại mỗi luồng một semaphore.

### 3. Trước khi viết: chuẩn bảo đảm gì, máy này cho gì

Bài thực chiến dễ sai nhất ở chỗ "chạy ra đúng nên chắc là đúng". Bảng dưới tách hai chuyện; cột phải là điều mình đo ở mục 💻 (g++ 11, glibc, 8 lõi, lúc đó máy khá bận), **đổi theo máy**.

| Chuyện | Chuẩn C++ nói | Máy này cho |
|---|---|---|
| Thứ tự in | Chỉ do **đồng bộ** trong chương trình quyết định (biến lượt + vị từ); lịch chạy luồng không được dùng để suy ra gì | Lịch luồng đổi mỗi lần, nhưng bản dùng biến lượt đúng 100% trong mọi lần thử |
| `notify_one` | Đánh thức nhiều nhất **một** luồng đang chờ, không nói luồng nào | Ba luồng trên một `cv` chung: **80 trên 100** lần treo |
| Spurious wakeup | Được phép | Mình không tái hiện được (như [Bài 27](../nhom-3-da-luong/27-condition-variable.md)); vị từ vẫn bắt buộc |
| Đọc/ghi biến thường từ hai luồng | **Data race = hành vi không xác định**: mọi kết quả đều "hợp lệ" | `-O0` chạy ra đúng 3/3 lần (may); `-O2` treo; TSan báo ngay |
| `std::cout` từ nhiều luồng | Không gây data race trên `cout`, nhưng ký tự của hai lần in **có thể trộn** | Ở đây chỉ một luồng in tại mỗi lúc nên không trộn |

Hàng thứ tư là cái bẫy: "chạy được" trên `-O0` không chứng minh gì; chứng cứ đáng tin là lập luận đúng cộng TSan sạch.

## 💻 Ví dụ code

### Đề (a): lời giải

Chương trình ghi kết quả vào chuỗi `ra` (dưới khóa) thay vì in thẳng, để so được với bản tuần tự. `std::to_string(so)` đổi số thành chuỗi chữ (`<string>`); `ra += ...` nối vào cuối chuỗi. `for (int N : {0, 1, 2, 7, 20, 200})` lặp qua danh sách số viết trong ngoặc nhọn (range-for chạy trên danh sách). Mỗi N chạy 50 lần và so với `tuanTu(N)`. Ở vòng `for` trong, phần cuối `++lan, ++tong` có dấu phẩy: nó chạy hai phép tăng liền nhau, giống `lan, tong = lan+1, tong+1` của Go.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

std::mutex khoa;
std::condition_variable cv;
int so = 1;              // số kế tiếp cần in; chỉ đổi dưới khóa
std::string ra;          // chuỗi kết quả; chỉ ghi dưới khóa

// du == 1: luồng lẻ; du == 0: luồng chẵn
void luong(int N, int du) {
    std::unique_lock<std::mutex> lk(khoa);
    while (true) {
        cv.wait(lk, [&] { return so > N || so % 2 == du; });   // (1) tới lượt mình, hoặc đã hết
        if (so > N) return;                                     // (2) hết số: thoát
        ra += std::to_string(so) + ' ';                         // (3) "in"
        ++so;                                                   // (4) chuyển lượt sang bên kia
        cv.notify_all();                                        // (5) báo tin
    }
}

std::string chanLe(int N) {
    so = 1;
    ra.clear();
    std::thread le(luong, N, 1), chan(luong, N, 0);
    le.join();
    chan.join();
    return ra;
}

std::string tuanTu(int N) {       // bản tuần tự để so sánh
    std::string s;
    for (int i = 1; i <= N; ++i) s += std::to_string(i) + ' ';
    return s;
}

int main() {
    std::cout << chanLe(20) << "\n";
    int sai = 0, tong = 0;
    for (int N : {0, 1, 2, 7, 20, 200})
        for (int lan = 0; lan < 50; ++lan, ++tong)
            if (chanLe(N) != tuanTu(N)) ++sai;
    std::cout << "so lan sai: " << sai << " / " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng** (hai luồng chạy xen kẽ; bảng nói vai trò, không phải thứ tự cố định)

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `wait` kiểm vị từ **trước khi ngủ**: luồng chẵn lúc đầu thấy `so = 1`, lẻ, nên ngủ; luồng lẻ thấy `1 % 2 == 1` nên đi tiếp, không ngủ |
| (2) | Dậy mà `so > N` nghĩa là đã in xong số cuối: `return` (khóa `lk` tự nhả khi ra khỏi hàm) |
| (3) | In dưới khóa. Luồng kia chỉ làm được sau khi `so` đổi, nên giữ khóa lúc in không làm chậm thêm gì |
| (4) | Đổi biến lượt, **dưới khóa**: chính lúc này "lượt" chuyển đi |
| (5) | Đánh thức luồng kia; nó dậy, xin lại khóa, kiểm vị từ: `so` đúng tính chẵn lẻ của nó, đi tiếp |

**Kết quả khi chạy:**

```text
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 
so lan sai: 0 / 300
```

Mình biên dịch sạch cảnh báo (cả `-O2`), TSan cũng sạch. Dòng đầu có một dấu cách thừa ở cuối (do `' '` sau mỗi số). Nó luôn đúng vì **vị từ chứ không phải lịch chạy** quyết định ai đi. Mình cũng chạy bản thử dài hơn (mỗi N chạy 200 lần, 1200 phép thử, N lớn nhất là 1000): 0 lần sai, TSan sạch.

**Thử thay đổi 1: đổi `notify_all()` thành `notify_one()`.** Mình đã chạy 3 lần bản 1200 phép thử nói ở trên: cả 3 lần 0 sai, TSan cũng sạch. Với **đúng hai luồng** thì người đang chờ chỉ có thể là luồng kia, và chuẩn bảo đảm `notify_one` đánh thức một luồng đang chờ nếu có: luồng vừa in không bao giờ chờ chính nó. Nên đây là đúng theo chuẩn, không phải may. Với ba luồng trở lên thì khác hẳn (đề (b), bản sai 2): chuẩn không cho chọn luồng nào dậy.

**Thử thay đổi 2: ở dòng (3) thay bằng `std::cout << so << ' ';` và bỏ `ra`.** Mình đã chạy: in `1 2 … 20`; 200 lần chạy cho đúng một dòng như nhau, TSan sạch. Chỉ một luồng in tại mỗi lúc, nên không có chuyện ký tự trộn nhau.

**Thử thay đổi 3: bỏ vế `so > N ||` khỏi vị từ ở dòng (1).** Mình đã chạy với N = 20 và N = 7: cả hai treo, `timeout 3` thoát mã **124**, và không in gì (vì chuỗi `ra` chỉ được in sau `join`). Luồng cuối cùng in xong thì luồng còn lại chờ một lượt không bao giờ đến. Đây là lỗi hay mắc nhất của đề này.

### Đề (a): hai bản SAI

**Sai 1: không có biến lượt, chỉ "mời nhau" bằng `notify` rồi chờ trần.** Ý tưởng nghe hợp lý: in xong thì báo bên kia, rồi ngủ chờ bên kia báo lại.

```cpp
// bo-qua-kiem-tra
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable cv;

void luong(int N, int dau) {            // dau = số đầu tiên của luồng này (1 hoặc 2)
    std::unique_lock<std::mutex> lk(khoa);
    for (int s = dau; s <= N; s += 2) {
        std::cout << s << ' ';          // (1) in luôn, không kiểm tới lượt chưa
        cv.notify_one();                // (2) "mời" bên kia
        cv.wait(lk);                    // (3) chờ trần: không biến lượt, không vị từ
    }
}

int main() {
    std::thread le(luong, 20, 1), chan(luong, 20, 2);
    le.join();
    chan.join();
    std::cout << "\nxong\n";
    return 0;
}
```

Mình chạy 40 lần (`timeout 1`, tắt đệm stdout bằng `stdbuf -o0` để thấy chữ in ra trước khi bị giết): **40 trên 40 lần treo**, mã **124**, không lần nào in `xong`. 37 lần in đúng `1 2 … 20` rồi treo; **3 lần in sai thứ tự** (`2 1 4 3 6 5 …`, vì luồng chẵn xin được khóa trước). Hai lỗi chồng nhau. Không biến lượt, nên không ai kiểm "có đúng lượt mình không" và thứ tự phó mặc lịch luồng. Và `wait` trần ở (3): luồng in số cuối gọi `notify_one` rồi vẫn `wait`, trong khi bên kia vừa thoát vòng lặp, nên không ai gọi nó dậy nữa; đó là lỗi `wait` không có vị từ của [Bài 27](../nhom-3-da-luong/27-condition-variable.md), cộng thêm việc không có điều kiện thoát.

**Sai 2: bỏ mutex, tự quay vòng đọc một biến thường.** Người ta hay "tối ưu" như thế vì thấy `cv` rườm rà.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
#include <thread>

int so = 1;                              // biến thường: không mutex, không atomic
std::string ra;

void luong(int N, int du) {
    while (so <= N) {                    // (1) đọc so không đồng bộ
        if (so % 2 == du) {              // (2) tới lượt mình thì "in" rồi sang số kế
            ra += std::to_string(so) + ' ';
            ++so;                        // (3) ghi so không đồng bộ
        }
    }
}

int main() {
    std::thread le(luong, 20, 1), chan(luong, 20, 0);
    le.join();
    chan.join();
    std::cout << ra << "\n";
    return 0;
}
```

Mình chạy ba cách. Với `-O0` (không tối ưu), 3 lần liền in đúng `1 2 … 20`: **may**. Với `-O2`, 3 lần liền **treo** (mã 124). Mình xem mã hợp ngữ (`g++ -O2 -S`): `so` được nạp vào thanh ghi **một lần** trước vòng `while`, rồi vòng lặp chỉ so sánh thanh ghi, nên không bao giờ thấy giá trị luồng kia ghi. Trình biên dịch được phép làm vậy vì không có đồng bộ nào, nên theo chuẩn không luồng nào khác đụng tới `so`.

Với TSan, báo ngay: `WARNING: ThreadSanitizer: data race`, một cặp `Read of size 4` (dòng (1)) với `Previous write of size 4` (dòng (3)), dòng `Location is global 'so'`; sau đó còn báo thêm một data race trên chính chuỗi `ra`. Ba kết quả khác nhau cho cùng một code là đặc trưng của hành vi không xác định ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)).

### Đề (b): lời giải mẫu "biến lượt"

Cùng khung với đề (a), khác ở chỗ mỗi luồng tự biết số vòng `n` nên chỉ cần vị từ `luot == toi`. Phép `% 3` quay vòng 0 → 1 → 2 → 0. Hàm `luong` chạy trong ba luồng với `(toi, chu)` khác nhau.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

std::mutex khoa;
std::condition_variable cv;
int luot = 0;            // 0: tới A, 1: tới B, 2: tới C; chỉ đổi dưới khóa
std::string ra;          // chuỗi kết quả; chỉ ghi dưới khóa

// toi: số thứ tự của luồng này (0, 1, 2); chu: chữ nó in; n: số vòng
void luong(int toi, char chu, int n) {
    for (int i = 0; i < n; ++i) {
        std::unique_lock<std::mutex> lk(khoa);
        cv.wait(lk, [&] { return luot == toi; });   // (1) chờ tới lượt mình
        ra += chu;                                  // (2) "in"
        luot = (luot + 1) % 3;                      // (3) trao lượt cho luồng kế
        lk.unlock();                                // (4) nhả khóa rồi mới báo
        cv.notify_all();                            // (5) đánh thức cả hai luồng còn lại
    }
}

std::string abc(int n) {
    luot = 0;
    ra.clear();
    std::thread a(luong, 0, 'A', n), b(luong, 1, 'B', n), c(luong, 2, 'C', n);
    a.join();
    b.join();
    c.join();
    return ra;
}

std::string mau(int n) {          // bản mẫu để so sánh
    std::string s;
    for (int i = 0; i < n; ++i) s += "ABC";
    return s;
}

int main() {
    std::cout << abc(5) << "\n";
    int sai = 0, tong = 0;
    for (int n : {0, 1, 5, 100})
        for (int lan = 0; lan < 50; ++lan, ++tong)
            if (abc(n) != mau(n)) ++sai;
    std::cout << "so lan sai: " << sai << " / " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng** (ba luồng xen kẽ)

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Lúc đầu `luot = 0`: B và C thấy vị từ sai nên ngủ; A đi tiếp |
| (2)-(3) | A ghi `A` rồi đặt `luot = 1`: lượt chuyển cho B, **dưới khóa** |
| (4)-(5) | Nhả khóa rồi `notify_all`: B và C cùng dậy; B thấy `luot == 1` đi tiếp, C thấy sai và **ngủ lại** |
| vòng lặp | Mỗi luồng quay lại đầu vòng `for` để xin lượt lần sau; sau n vòng thì hàm kết thúc |

**Kết quả khi chạy:**

```text
ABCABCABCABCABC
so lan sai: 0 / 200
```

Mình biên dịch sạch cảnh báo, TSan sạch. Dùng `notify_all` ở (5) là **bắt buộc** khi ba luồng dùng chung **một** `cv` (xem bản sai 2 bên dưới): luồng được dậy phải là luồng có `luot == toi`, mà chuẩn không cho ta chọn.

### Đề (b): bản semaphore (mô phỏng C++17)

Lớp `Semaphore` dưới đây là lớp ở [Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md) chép lại: bộ đếm `dem_` dưới khóa; `acquire` chờ tới khi `dem_ > 0` rồi giảm 1; `release` tăng 1 rồi đánh thức một luồng. Ba semaphore **truyền thẻ** theo vòng: A lấy thẻ của mình, in `A`, đưa thẻ cho B, và cứ thế. Chỉ `luotA` có sẵn 1 thẻ.

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

// Mô phỏng semaphore C++20 bằng mutex + condition_variable (Bài 60)
class Semaphore {
public:
    explicit Semaphore(int chua) : dem_(chua) {}
    void acquire() {
        std::unique_lock<std::mutex> lk(khoa_);
        cv_.wait(lk, [this] { return dem_ > 0; });   // (1) hết thẻ thì ngủ
        --dem_;
    }
    void release() {
        {
            std::lock_guard<std::mutex> g(khoa_);
            ++dem_;                                   // (2) trả thẻ: bộ đếm nhớ lại
        }
        cv_.notify_one();
    }

private:
    std::mutex khoa_;
    std::condition_variable cv_;
    int dem_;
};

std::string abc(int n) {
    Semaphore luotA(1), luotB(0), luotC(0);           // (3) chỉ A có thẻ lúc đầu
    std::string ra;                                   // chỉ luồng đang giữ thẻ mới ghi
    std::thread a([&] { for (int i = 0; i < n; ++i) { luotA.acquire(); ra += 'A'; luotB.release(); } });
    std::thread b([&] { for (int i = 0; i < n; ++i) { luotB.acquire(); ra += 'B'; luotC.release(); } });
    std::thread c([&] { for (int i = 0; i < n; ++i) { luotC.acquire(); ra += 'C'; luotA.release(); } });
    a.join();
    b.join();
    c.join();
    return ra;
}

std::string mau(int n) {          // bản mẫu để so sánh
    std::string s;
    for (int i = 0; i < n; ++i) s += "ABC";
    return s;
}

int main() {
    std::cout << abc(5) << "\n";
    int sai = 0, tong = 0;
    for (int n : {0, 1, 5, 100})
        for (int lan = 0; lan < 50; ++lan, ++tong)
            if (abc(n) != mau(n)) ++sai;
    std::cout << "so lan sai: " << sai << " / " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (3) | `luotA = 1`, hai bộ kia `0`: B và C `acquire` là ngủ ngay; A đi |
| (1)-(2) | `acquire` giảm thẻ hoặc ngủ; `release` **cộng thẻ vào bộ đếm**, nên dù B chưa kịp ngủ, thẻ vẫn nằm đó chờ nó |
| lambda của `a` | `acquire` thẻ của A, ghi `A`, `release` thẻ của B: trao lượt |
| ghi `ra` | Không cần mutex riêng: tại mỗi lúc chỉ luồng đang cầm thẻ mới ghi, và `release` → `acquire` truyền kết quả ghi sang luồng kế |

**Kết quả khi chạy:**

```text
ABCABCABCABCABC
so lan sai: 0 / 200
```

Mình biên dịch sạch cảnh báo, TSan sạch.

**Thử thay đổi: đổi `luotA(1)` thành `luotA(0)`.** Mình đã chạy: treo, `timeout 3` mã **124**. Không luồng nào có thẻ ngay từ đầu, nên cả ba cùng ngủ trong `acquire`. Đây là câu hỏi "vì sao bộ đầu bằng 1" ở gợi ý 3: bộ đếm *là* lượt, nên phải có đúng một thẻ để vòng bắt đầu.

Với C++20 (`g++ -std=c++20`), bỏ lớp `Semaphore` và khai báo `std::binary_semaphore luotA{1}, luotB{0}, luotC{0};` sau `#include <semaphore>` (nhị phân: số thẻ chỉ 0 hoặc 1); ba lambda giữ nguyên. Mình không đưa nguyên khối vì bộ kiểm tra của bài chạy `-std=c++17`: thử `-std=c++17` thì lỗi `'binary_semaphore' is not a member of 'std'`, còn `-std=c++20` biên dịch sạch, in `ABCABCABCABCABC`, TSan sạch.

### Đề (b): hai bản SAI

**Sai 1: `if` thay vì vị từ.** Viết `if (luot != toi) cv.wait(lk);` thay cho `cv.wait(lk, vịTừ)`. `notify_all` đánh thức cả ba luồng, và luồng dậy rồi **đi tiếp mà không kiểm lại**.

```cpp
// bo-qua-kiem-tra
void luong(int toi, char chu, int n) {
    for (int i = 0; i < n; ++i) {
        std::unique_lock<std::mutex> lk(khoa);
        if (luot != toi) cv.wait(lk);               // (1) "if": dậy là đi luôn, không kiểm lại
        ra += chu;
        luot = (luot + 1) % 3;
        lk.unlock();
        cv.notify_all();
    }
}
// main như bản đúng: ba luồng, n = 5, in ra
```

Mình chạy 100 lần với n = 5 (`timeout 1`): **6 lần ra đúng**, **59 lần ra sai thứ tự** (ví dụ `ABCACBABCABCABC`, `ABACBCABACBCABC`, `ABCABCBBCABCACA`: có lần dư một `B`, thiếu một `A`), **35 lần treo** (mã 124). Khi mình kiểm lại lúc máy bận hơn thì ra 0 đúng, 15 sai thứ tự, 85 treo: tỉ lệ đổi nhiều theo máy và theo lần chạy, chỉ có "không bao giờ chắc đúng" là ổn định. Cùng một lỗi mà ba triệu chứng. Chuẩn không nói luồng được báo thức "đúng lượt", và `notify_all` đánh thức luôn cả hai luồng chưa tới lượt: với `if`, chúng đi tiếp luôn.

**Sai 2: `notify_one` trên một `cv` chung với ba luồng** (vị từ vẫn đúng). Mình đổi dòng (5) của lời giải mẫu thành `cv.notify_one();` rồi chạy 100 lần với n = 5: **80 lần treo**, 20 lần ra đúng. Ba luồng cùng chờ trên một `cv`; A trao lượt cho B, nhưng `notify_one` có thể đánh thức C (chuẩn không chỉ định). C dậy, thấy `luot != 2`, ngủ lại; B vẫn ngủ và không ai báo nữa. Tỉ lệ treo đổi theo máy và theo độ bận của máy, nhưng chuẩn **không** hứa lần nào cũng may.

### Chi phí, và khi nào KHÔNG nên viết thế này

**Chi phí của đề (a) và (b).** Mọi số dưới đây mình đo bằng một chương trình riêng (`-O2`, `steady_clock`), **đổi theo máy**; lúc đo máy bận (số `load average`, trung bình số luồng đang chờ lõi để chạy, khoảng 20 trên 8 lõi), nên chỉ tin bậc độ lớn.

- **Thời gian:** O(N) lần chuyển giao (mỗi số một lần), mỗi lần O(1) thao tác nhưng cần hệ điều hành đánh thức một luồng khác. Với N = 200000, hai luồng dùng `cv` mất khoảng **1,4 đến 1,6 giây** (cỡ 7 micro-giây mỗi số) trong khi một luồng vòng `for` cộng 200000 số mất khoảng **0,5 mili-giây**: chậm hơn **cỡ ba nghìn lần**. Hai luồng ở đây là tuần tự hóa hoàn toàn (mỗi lúc chỉ một luồng làm), nên thêm luồng không đem lại tốc độ, chỉ thêm chi phí chuyển giao.
- **Bộ nhớ:** O(1) cho phần đồng bộ, cộng O(N) chỉ vì ta gom chuỗi kết quả.
- **Nhiều luồng, `notify_all`:** mỗi lần chuyển giao đánh thức **K − 1 luồng**, trong đó K − 2 luồng thấy vị từ sai và ngủ lại: "đánh thức cả đàn" (thundering herd), O(K) mỗi số. Mình đo vòng K = 64 luồng, 1000 vòng (64000 lần chuyển giao): `notify_all` chung một `cv` mất **13 đến 21 giây**; **mỗi luồng một `cv` riêng** (chỉ `notify_one` luồng kế) mất **0,5 đến 0,6 giây**: nhanh hơn cỡ 20 đến 40 lần. Với K = 3, 60000 lần chuyển giao: `notify_all` 430 đến 610 ms, `cv` riêng 295 đến 400 ms: chênh nhẹ.

| Cách ép thứ tự | Khi nào chọn | Chi phí / điểm yếu |
|---|---|---|
| `mutex` + một `cv` + biến lượt + `notify_all` | **Mặc định** cho 2 đến vài luồng; dễ chứng minh đúng | Đánh thức cả đàn, O(K) mỗi lượt |
| `mutex` + **mỗi luồng một `cv`** | K lớn: chỉ gọi dậy đúng luồng kế | Nhiều `cv` hơn, vẫn một mutex chung |
| Chuỗi semaphore ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md)) | Muốn code ngắn, bộ đếm nhớ giùm, tránh lost wakeup | Mỗi luồng một semaphore; C++17 phải tự viết |
| `atomic` + quay vòng (không ngủ) | Chỉ khi chờ cực ngắn và luồng ít hơn lõi | Đốt CPU lúc chờ; mình đo bản không `yield` nhanh hơn `cv` 3 đến 100 lần (3 lần thử) nhưng đốt cả hai lõi; thêm `yield` thì dao động rất lớn (0,2 đến 4,9 giây) khi máy bận ([Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md)) |
| **Một luồng, vòng `for`** | Khi thứ tự là toàn bộ việc | Nhanh nhất; không cần đồng bộ gì |

**Khi nào KHÔNG nên dùng mẫu này trong code thật.** Nếu việc cần làm là tính toán, hãy cho mỗi luồng làm phần của mình **song song**, ghi kết quả vào ô theo chỉ số, rồi ghép theo thứ tự sau `join`; đừng bắt luồng chờ nhau từng bước. Nếu cần chuyển việc từ luồng này sang luồng kia qua một hàng đợi, đó là producer-consumer ([Bài 66](66-bounded-queue.md)), không phải "lượt". Còn đề chẵn lẻ/ABC thì **chỉ có ý nghĩa như bài kiểm tra phối hợp luồng**.

## Go: chuỗi channel làm sẵn việc "trao lượt"

!!! info "Bạn biết Go?"
    Mình đã chạy bằng `go run -race`. Với **channel không đệm** của Go, `ch <- x` chặn tới khi có goroutine nhận, nên một chuỗi ba channel (`<-luot[k]` chờ lượt mình, rồi `luot[(k+1)%3] <- struct{}{}` trao lượt cho goroutine kế) làm đúng việc của chuỗi semaphore ở trên: in `ABCABCABCABCABC`, `-race` sạch. Bên gửi **chờ** tới khi có bên nhận nên không có chuyện tin bị mất như `notify` trong C++; vì thế Go không cần `mutex` + `cv` + vị từ. Cái bẫy thoát vẫn y hệt: nếu goroutine C ở vòng cuối vẫn gửi lượt cho A (đã thoát), nó chặn mãi và Go báo `fatal error: all goroutines are asleep - deadlock!`; mình phải bỏ lần gửi cuối. C++ chuẩn không có channel nên ta tự ghép.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Cách bạn tiếp cận đề in chẵn lẻ trên bảng: nói thế nào trong một phút?"
    Nói trước ba mảnh: "đề này là **thứ tự**, không phải loại trừ lẫn nhau, nên mutex một mình không đủ". Rồi: "mình đặt thông tin tới lượt ai vào một **biến chung** `so`, đổi dưới khóa; mỗi luồng `wait(lk, ...)` với vị từ 'tới lượt mình hoặc đã hết'; in xong đổi `so` và `notify_all`". Cuối cùng nêu điều kiện thoát (`so > N`) và hai bẫy: chờ trần (lost wakeup) và `if` thay vị từ. Khi được hỏi "vì sao đúng?", nêu **bất biến** ("biến lượt chỉ đổi dưới khóa; luồng chỉ ghi khi vị từ đúng; mỗi lần ghi chỉ chuyển lượt cho luồng kế"), đừng nói "chạy 100 lần đều đúng": bản data race ở `-O0` cũng từng "chạy đúng".

??? question "Nếu N rất lớn thì cách này nhanh hay chậm? Có nhanh hơn một luồng không?"
    Chậm hơn nhiều. Mỗi số cần một lần **chuyển giao**: luồng này đổi biến lượt, luồng kia phải được hệ điều hành đánh thức (cỡ hàng micro-giây mỗi lần; mình đo chừng 7 micro-giây). Hai luồng ở đây tuần tự hóa hoàn toàn, nên không có song song nào để thắng. Mình đo một luồng vòng `for` nhanh hơn cỡ ba nghìn lần. Đề này đo khả năng phối hợp luồng, không phải hiệu năng.

??? question "`notify_one` được không, hay bắt buộc `notify_all`?"
    Với **đúng hai** luồng thì `notify_one` đủ, vì khi một luồng đang in thì luồng kia là người chờ duy nhất (mình chạy `notify_one` ở đề (a): 3 lần 1200 phép thử, 0 sai). Với ba luồng trở lên trên **một** `cv` chung thì phải `notify_all`, vì chuẩn không cho chọn luồng nào dậy: mình chạy bản `notify_one` thì 80 trên 100 lần treo. Muốn gọi đúng người mà không đánh thức cả đàn thì dùng **mỗi luồng một `cv`** hoặc chuỗi semaphore.

??? question "Không dùng `mutex` được không, chỉ `atomic`?"
    Được: biến lượt là `std::atomic<int>` và mỗi luồng quay vòng đọc nó (có thể thêm `yield`). Đúng theo chuẩn nếu mọi truy cập đều qua `atomic`. Nhưng luồng quay vòng đốt CPU lúc chờ ([Bài 27](../nhom-3-da-luong/27-condition-variable.md) mục 1: `user` gần bằng `real`), và kết quả dao động rất lớn khi máy bận (mình đo bản có `yield` từ 0,2 đến 4,9 giây cho 200000 số, trong khi `cv` ổn định cỡ 1,4 đến 1,6 giây). Còn đọc/ghi **biến thường** không khóa thì là data race, không phải lựa chọn (bản sai 2 của đề (a): `-O2` treo, TSan báo).

??? question "Mở rộng ra K luồng, hoặc nhiều chữ không đều (như `AABBC`): bạn đổi gì?"
    Biến lượt chạy 0..K−1 (`% K`); với mẫu không đều, đổi `luot` thành chỉ số vào một mảng "kịch bản" (ví dụ `"AABBC"`), luồng chữ nào chỉ đi khi `kichBan[luot] == chu`, rồi tăng `luot` theo `% kichBan.size()`. K lớn thì đổi sang **mỗi luồng một `cv`** để chỉ đánh thức đúng luồng kế (mình đo K = 64: nhanh hơn 20 đến 40 lần).

??? question "Một luồng ném ngoại lệ hay thoát sớm giữa chừng thì sao?"
    Cả hệ thống treo: các luồng kia chờ một lượt không bao giờ đến. Mình chạy thử: cho luồng B chỉ in 2 chữ trong khi A và C in 5: treo, mã 124. Cách chữa: thêm một cờ `huy` (đổi dưới khóa, `notify_all` khi đổi) và đưa nó vào vị từ (`luot == toi || huy`), rồi mọi luồng kiểm `huy` sau khi dậy và thoát. Đó cũng là cách "dừng sạch" ở [Bài 27](../nhom-3-da-luong/27-condition-variable.md).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Xếp thứ tự bằng `sleep_for`"
    Cho luồng B ngủ lâu hơn A "để A in trước" là cách nhiều người nghĩ ra đầu tiên. Chuẩn không hứa gì về tốc độ hay lịch chạy của luồng, nên không có độ dài ngủ nào **đảm bảo** thứ tự (máy bận hay chạy dưới TSan là đổi hẳn). Đồng bộ phải đến từ biến lượt và vị từ, không đến từ thời gian.

!!! warning "Lỗi 2: Quên điều kiện thoát cho luồng cuối"
    Vị từ chỉ hỏi "tới lượt mình chưa" mà không có "đã hết việc chưa": một luồng chờ một lượt không bao giờ tới (đề (a): bỏ vế `so > N`, treo mã 124 với cả N chẵn lẫn lẻ). Khi viết trên bảng, hãy tự hỏi "luồng nào là luồng **cuối cùng**, và luồng còn lại thoát bằng cách nào?".

!!! warning "Lỗi 3: Dùng `if`, hoặc chờ trần, thay cho vị từ"
    Hai lỗi cùng họ: dựa vào "dậy nghĩa là tới lượt mình" hoặc "tiếng chuông luôn đến sau khi mình ngủ". Mình chạy `if` + `notify_all` với ba luồng: trong 100 lần chỉ vài lần ra đúng, còn lại sai thứ tự hoặc treo. Luôn viết `cv.wait(lk, [&] { return ...; })`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="65" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đề chẵn lẻ: hai luồng phải in `1 2 3 …` đúng thứ tự. Thông tin "bây giờ tới lượt luồng nào" nên được giữ ở đâu?

- Trong tiếng `notify`: luồng nào vừa được báo thì tới lượt luồng đó
- Trong thứ tự tạo luồng: luồng tạo trước luôn được chạy trước
- Trong một biến chung đổi dưới khóa, và vị từ của `wait` đọc nó
- Trong độ dài `sleep_for` của mỗi luồng, để luồng lẻ ngủ ít hơn

<p class="giai-thich" markdown>Biến chung được bảo vệ bởi mutex là thứ duy nhất bền: `wait(lk, vịTừ)` kiểm nó trước khi ngủ và sau mỗi lần dậy, nên tin báo đến sớm hay muộn, thật hay giả đều không làm sai thứ tự. Tiếng `notify` mất nếu chưa ai chờ và không nói gì về lượt. Thứ tự tạo luồng không quyết định luồng nào chạy trước vì chuẩn không hứa gì về lịch chạy. Còn `sleep_for` chỉ là phỏng đoán về tốc độ, máy bận là đổi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Hai luồng lẻ/chẵn chạy với `N = 7`. Chuyện gì xảy ra?

```text
cv.wait(lk, [&] { return so % 2 == du; });
if (so > N) return;
// ... ghi so, ++so, cv.notify_all();
```

- In đủ `1..7` rồi một luồng ngủ mãi, `join` treo
- In đủ `1..7`, rồi hai luồng cùng thoát và `join` về bình thường
- Luồng chẵn in thêm số `8`, rồi cả hai thoát khi `so` lên tới 9
- Chương trình ném ngoại lệ ngay khi `so` vượt quá `N`

<p class="giai-thich" markdown>Luồng lẻ in `7` rồi đặt `so = 8`. Luồng chẵn dậy vì `8` chẵn, thấy `so > N` nên thoát; còn luồng lẻ quay lại `wait` và vị từ `8 % 2 == 1` sai mãi, nên ngủ không ai báo. Vị từ thiếu vế `so > N ||` nên không có lối thoát cho luồng còn lại. Cả hai cùng thoát chỉ khi vị từ có vế đó. Số `8` không bao giờ được in vì `return` chạy trước dòng ghi, và không có ngoại lệ nào ở đây.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Cần 64 luồng xoay vòng in theo thứ tự cố định, in hàng chục nghìn vòng. Cách nào vừa đúng vừa không đánh thức luồng thừa?

- Một `cv` chung, `notify_one`, vì chỉ cần đánh thức một luồng mỗi lượt
- Một `cv` chung, `notify_all`, vì chắc chắn đúng và chi phí không đáng kể
- Cho mỗi luồng ngủ `sleep_for` lệch nhau để mỗi luồng tự biết lượt của mình
- Mỗi luồng một `cv` riêng (hoặc chuỗi semaphore) và chỉ báo đúng luồng kế

<p class="giai-thich" markdown>Một `cv` riêng cho mỗi luồng cho phép gọi dậy đúng người tiếp theo, không đánh thức 62 luồng thừa; mình đo K = 64 nhanh hơn `notify_all` cỡ 20 đến 40 lần. `notify_one` trên `cv` chung có thể đánh thức nhầm luồng chưa tới lượt, rồi treo vì không ai báo lại luồng đúng. `notify_all` thì đúng nhưng đánh thức cả đàn mỗi lượt, và chi phí lớn dần theo K. `sleep_for` lệch nhau là phỏng đoán về lịch chạy, không phải đồng bộ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. Ba luồng A, B, C dùng một `cv` chung, `notify_all` sau mỗi lượt. Điều nào đúng?

```text
if (luot != toi) cv.wait(lk);
ra += chu;
luot = (luot + 1) % 3;
```

- Luôn đúng, vì `notify_all` chỉ đánh thức luồng đang tới lượt
- Có thể in sai thứ tự, vì luồng dậy mà chưa tới lượt vẫn đi tiếp
- Luôn treo ngay lần đầu, vì `wait` không có vị từ thì không nhả khóa
- Không biên dịch được, vì `wait` bắt buộc phải có đối số thứ hai

<p class="giai-thich" markdown>`notify_all` đánh thức mọi luồng đang chờ chứ không lọc theo lượt; với `if`, luồng chưa tới lượt dậy rồi ghi luôn nên chuỗi sai thứ tự (mình chạy 100 lần: chỉ vài lần đúng, còn lại sai thứ tự hoặc treo). Vòng `while` hay vị từ kiểm lại sau khi dậy mới đưa nó ngủ lại. `wait` không vị từ vẫn nhả khóa khi ngủ, nên chương trình không treo ngay lần đầu. Và `wait(lk)` một đối số là dạng hợp lệ, biên dịch bình thường.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Một bản dùng `notify_one` với ba luồng và `cv` chung chạy 100 lần ra đúng 20 lần, treo 80 lần. Bạn kết luận gì?

- Lỗi nhẹ: đúng 20 trên 100 lần là chấp nhận được cho bài thi
- Máy chậm nên treo; trên máy nhanh hơn sẽ đúng hết các lần
- Thêm một `sleep_for` nhỏ trước `notify_one` là đủ để sửa lỗi này
- Bản sai: chuẩn không cho chọn luồng dậy, "lần đúng" chỉ là may

<p class="giai-thich" markdown>`notify_one` đánh thức một luồng không chỉ định; nếu đó là luồng chưa tới lượt, nó ngủ lại và không ai báo luồng đúng, nên treo. Tỉ lệ đổi theo máy, nhưng chuẩn không bảo đảm lần nào cũng may, nên bản này sai dù có lần chạy đúng. Máy nhanh chỉ đổi tỉ lệ, không biến nó thành đúng. Còn `sleep_for` không làm `notify_one` chọn đúng luồng được.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn sau. Bản semaphore của đề ABC, `n = 5`. Chuyện gì xảy ra?

```text
Semaphore luotA(0), luotB(0), luotC(0);
// a: luotA.acquire(); ra += 'A'; luotB.release();   (lặp n lần)
// b: luotB.acquire(); ra += 'B'; luotC.release();
// c: luotC.acquire(); ra += 'C'; luotA.release();
```

- Treo ngay từ đầu, vì cả ba cùng ngủ ở `acquire` và không có thẻ nào
- In `ABCABCABCABCABC`, vì `release` của luồng nào tới trước thì dậy trước
- In sai thứ tự, vì ba luồng giành thẻ nhau và chuẩn không quy định ai thắng
- Biên dịch lỗi vì bộ đếm của semaphore không được bắt đầu từ 0

<p class="giai-thich" markdown>Mọi `acquire` đều thấy bộ đếm 0 nên ngủ; chỉ có `release` mới tăng bộ đếm, mà không luồng nào chạy tới được `release` nào (mình đã chạy: `timeout 3` mã 124). Vì vậy một bộ phải bắt đầu bằng 1 để vòng khởi động. Không có thẻ nào để các luồng "giành" nhau nên không có chuyện sai thứ tự. Bộ đếm bắt đầu từ 0 vẫn hợp lệ, và còn được dùng làm tín hiệu ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md)).</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Người phỏng vấn hỏi: "Hai luồng in 1..200000 xen kẽ bằng `cv` so với một luồng vòng `for` làm cùng việc, cái nào nhanh, vì sao?"

- Hai luồng nhanh hơn gần gấp đôi vì chia đều việc cho hai lõi CPU
- Hai bản xấp xỉ nhau, vì phần lớn thời gian nằm ở việc in chứ không ở luồng
- Một luồng nhanh hơn nhiều bậc, vì mỗi số tốn một lần chuyển giao
- Hai luồng nhanh hơn nếu dùng `notify_all`, vì nó đánh thức nhiều luồng hơn

<p class="giai-thich" markdown>Ở đề này mọi số đều phải chờ lượt của số trước, nên hai luồng không chạy song song gì; mỗi số tốn thêm một lần đánh thức luồng kia (mình đo cỡ vài micro-giây), trong khi vòng `for` cộng một số chỉ tốn vài nano-giây. Con số "ba nghìn lần" đổi theo máy, nhưng chiều hướng thì không. Chia đều cho hai lõi chỉ đúng khi việc độc lập với nhau. `notify_all` không làm nhanh hơn, chỉ có thể đánh thức thừa. Và phần việc thật của mỗi số gần như không tốn gì, nên không có phần song song nào để chia.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Đề "bắt luồng đi theo thứ tự" dùng đúng ba mảnh của [Bài 27](../nhom-3-da-luong/27-condition-variable.md): `mutex`, một **biến lượt** đổi dưới khóa (`so` hoặc `luot`) và `condition_variable`; luồng chờ bằng `wait(lk, vịTừ)` với vị từ "tới lượt mình **hoặc** đã hết việc", nên cả hai luồng thoát được, N lẻ hay chẵn, kể cả N = 0.
2. Bốn bản sai mình chạy thật: chờ trần không biến lượt (40/40 treo mã 124, 3/40 sai thứ tự), đọc biến thường không khóa (TSan báo data race; `-O0` ra đúng 3/3 lần nhờ may, `-O2` treo), `if` thay vị từ (100 lần: chỉ vài lần đúng, còn lại sai thứ tự hoặc treo); riêng `notify_one` với ba luồng trên một `cv` chung thì 80/100 lần treo.
3. Đề ABC bằng chuỗi semaphore: ba bộ đếm truyền thẻ theo vòng, `luotA` bắt đầu bằng 1 (đổi thành 0 thì treo); `release` được đếm lại nên không lost wakeup. C++17 phải tự viết `Semaphore` ([Bài 60](../nhom-8-da-luong-chieu-sau/60-semaphore-latch-barrier.md)), C++20 có `std::binary_semaphore` (`g++ -std=c++20`; `-std=c++17` thì lỗi biên dịch).
4. Chuẩn bảo đảm thứ tự đến từ đồng bộ của bạn chứ không từ lịch luồng; `notify_one` không chọn được luồng; data race là hành vi không xác định (chạy ra đúng chưa chứng minh gì); `cout` không race nhưng có thể trộn ký tự: nói được vì sao đúng bằng **bất biến**, đừng nói "chạy 100 lần đều đúng".
5. Chi phí: O(N) lần chuyển giao, mỗi lần cần hệ điều hành đánh thức luồng kia (mình đo cỡ vài micro-giây; một luồng vòng `for` nhanh hơn cỡ ba nghìn lần); `notify_all` với K luồng là O(K) mỗi lượt (K = 64: 13 đến 21 giây so với 0,5 đến 0,6 giây khi mỗi luồng một `cv`); đề này chỉ là bài kiểm tra phối hợp luồng, code thật chia việc song song rồi ghép kết quả theo thứ tự.
