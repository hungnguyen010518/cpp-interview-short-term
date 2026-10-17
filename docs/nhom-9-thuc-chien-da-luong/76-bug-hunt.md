# Bài 76 — Bug-hunt: 12 đoạn code đa luồng có lỗi, tìm lỗi ở đâu

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Đọc một đoạn code đa luồng lạ theo bốn câu hỏi (dữ liệu nào chung, ai bảo vệ, đang chờ gì, ai sống lâu hơn ai) và nói lỗi theo ba phần người phỏng vấn muốn nghe: lỗi gì, vì sao nguy hiểm, sửa thế nào.
    - Nhận ra 12 lỗi kinh điển: bộ đếm chung, quên khóa ở một đường, khóa ngược thứ tự, lost wakeup, `if` thay `while`, `detach` giữ tham chiếu, `shared_ptr` bị sửa đồng thời, trả tham chiếu ra khỏi khóa, `vector<bool>`, callback khi giữ khóa, hai `atomic` tưởng là một bất biến, quên `join`.
    - Biết lỗi nào TSan bắt, lỗi nào cần ASan, `gdb` hay `timeout`, và hai lỗi mà **cả TSan cũng im** (mục 5 và 11).
    - Tra bảng "triệu chứng, nguyên nhân hay gặp" để đoán nhanh lỗi từ cách chương trình hỏng.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`join`, `detach`, tham số của luồng), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`, TSan qua `setarch -R`, `timeout`), [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock, `scoped_lock`), [Bài 27](../nhom-3-da-luong/27-condition-variable.md) (`wait` có predicate), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, bất biến nhiều biến), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) và [Bài 41](../nhom-5-he-thong-quy-trinh/41-sanitizer-valgrind.md) (ASan, TSan), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (`std::terminate`). [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) (`shared_ptr` nhiều luồng), [Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md) (container) và [Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md) (quy trình gỡ lỗi) được nhắc lại ở chỗ cần, nên bài này đọc riêng được.

## 🧠 Câu chuyện mở đầu

Vòng cuối phỏng vấn. Người phỏng vấn đẩy qua một tờ giấy có 12 đoạn code ngắn: "Mỗi đoạn có đúng một lỗi. Anh/chị đọc to, nói lỗi là gì, vì sao nguy hiểm và sửa thế nào. Hai phút một đoạn." Không có máy tính để chạy thử.

Mỗi đoạn là một cảnh trong **nhà bếp nhiều đầu bếp** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)): hai đầu bếp chặt chung một thớt không thẻ, một người quên xin thẻ ở một cửa, hai người cầm thẻ ngược thứ tự chờ nhau, chuông gọi món bấm trước khi ai đứng nghe, một đầu bếp bê nguyên liệu của bàn đã dọn... Bài này cho bạn xem từng cảnh **diễn ra thật** (mình đã chạy từng đoạn) để lần sau đọc code là thấy cảnh đó.

!!! info "Chỗ nào ví von bếp không còn đúng?"
    Trong bếp thật, hai người tranh một thớt thì ai cũng thấy. Trong bộ nhớ, dữ liệu bị chạm đồng thời **không kêu lên**: chương trình thường vẫn chạy và in kết quả trông đúng. Vì thế nhiều lỗi dưới đây phải có công cụ mới thấy.

## 📖 Giải thích

### 1. Luật chơi

Mỗi mục là một chương trình **đầy đủ**: chép vào máy là chạy. Bạn đọc code, tự trả lời câu "Tìm lỗi", rồi mới mở `??? tip "Xem đáp án"`. Thay cho bảng "Chạy từng dòng", mỗi đáp án kể **ai làm gì theo thứ tự thời gian**, đó mới là thứ bạn phải nói trên bảng trắng. Khối nào cũng có dòng đầu `// bo-qua-kiem-tra` vì cố ý sai; chép đi chạy thì bỏ dòng đó.

| Việc | Lệnh mình đã dùng (tệp rút gọn thành `NN.cpp`) |
|---|---|
| Chạy thường | `g++ -std=c++17 -Wall -pthread -o ct NN.cpp && ./ct` (thử thêm `-O2`) |
| TSan | thêm `-g -fsanitize=thread`, chạy `setarch x86_64 -R ./ct` (có báo cáo thì thoát mã 66) |
| ASan | thêm `-g -fsanitize=address`; lỗi trên stack cần `ASAN_OPTIONS=detect_stack_use_after_return=1` |
| Chương trình treo | `timeout 3 ./ct; echo $?` ra `124` nghĩa là `timeout` phải giết vì treo |

Số dòng trong báo cáo (như `01.cpp:6`) tính khi **bỏ** dòng `// bo-qua-kiem-tra`; đường dẫn và khung thư viện đã lược. Số lần sai ("9/20") đổi theo máy và tải máy. Bản sửa của mỗi mục viết dưới dạng thay đổi (`diff`) cho ngắn: dòng bắt đầu bằng `-` là dòng bỏ đi, dòng bắt đầu bằng `+` là dòng thêm vào, dòng không dấu giữ nguyên; mình đã biên dịch và chạy **cả 12 bản sửa**, TSan sạch ở cả 12.

### 2. Cách đọc: ba bậc gợi ý và ba nhóm lỗi

??? tip "Gợi ý 1: gạch chân dữ liệu chung"
    Tìm mọi biến, đối tượng, con trỏ mà **từ hai luồng trở lên** chạm tới (biến toàn cục, thứ lambda bắt bằng `&`, đối tượng truyền bằng tham chiếu). Dữ liệu chỉ một luồng chạm thì không cần bàn.

??? tip "Gợi ý 2: với mỗi dữ liệu chung, hỏi bốn câu"
    Ai bảo vệ nó (mutex, atomic, hay không ai)? **Mọi** đường truy cập, kể cả hàm đọc và hàm phụ, có qua cái bảo vệ đó không? Có ai chờ điều kiện không, và điều kiện nằm ở biến nào? Dữ liệu và luồng, bên nào **sống lâu hơn**?

??? tip "Gợi ý 3: tự chen vào"
    Chọn một dòng và hỏi "nếu luồng kia chạy trọn một đoạn đúng vào đây thì sao?". Nếu câu trả lời là "kết quả sai", "treo" hay "đọc ô nhớ đã chết", đó là lỗi. Việc `sleep_for` chèn thử làm hộ chính là việc này.

Ba nhóm lỗi để định hướng: **không đồng bộ** (mục 1, 2, 7, 8, 9: dữ liệu chung bị chạm mà không có khóa chung), **đồng bộ sai** (mục 3, 4, 5, 10, 11: có khóa hay biến chờ nhưng dùng sai cách) và **vòng đời** (mục 6, 12: luồng sống lâu hơn dữ liệu, hoặc luồng bị hủy khi chưa được chờ).

## 💻 Ví dụ code

### Mục 1: bộ đếm chung

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>

int dem = 0;                                   // (1) biến chung, không ai bảo vệ
void tang() {
    for (int i = 0; i < 100000; ++i) ++dem;    // (2) đọc, cộng, ghi: ba bước
}
int main() {
    std::thread a(tang), b(tang);
    a.join(); b.join();
    std::cout << "dem = " << dem << "\n";      // (3) mong đợi 200000
}
```

**Tìm lỗi:** chương trình mong đợi in `dem = 200000`. Nó có luôn in như vậy không?

??? tip "Xem đáp án"
    **Lỗi:** data race trên `dem`. `++dem` là ba bước (đọc, cộng, ghi): hai luồng cùng đọc `5` thì cùng ghi `6`, mất một lần cộng; theo chuẩn đây còn là hành vi không xác định.

    **Mình đã chạy:** không `-O`, 9/20 lần in thiếu (`dem = 125043`, `120728`, `132654`); với `-O2`, 20/20 lần in đúng `200000`: **lỗi vẫn còn nhưng ẩn**, nên "chạy thử thấy đúng" không chứng minh gì. TSan báo ngay:

    ```text
    Read of size 4 at 0x… by thread T2:            #0 tang() 01.cpp:6
    Previous write of size 4 at 0x… by thread T1:  #0 tang() 01.cpp:6
    Location is global 'dem' of size 4
    ```

    **Sửa** (đã chạy: 50/50 lần in `200000`, TSan sạch): thêm `#include <atomic>` và đổi `int dem = 0;` thành `std::atomic<int> dem{0};` (`std::mutex` cũng được).

### Mục 2: quên khóa ở một đường

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <thread>

struct TaiKhoan {
    std::mutex khoa;
    int soDu = 0;
    void rut() {
        std::lock_guard<std::mutex> giu(khoa);
        --soDu;
    }
    void nap() { ++soDu; }                     // (1) đường này quên khóa
};
int main() {
    TaiKhoan tk;
    std::thread a([&] { for (int i = 0; i < 100000; ++i) tk.nap(); });
    std::thread b([&] { for (int i = 0; i < 100000; ++i) tk.rut(); });
    a.join(); b.join();
    std::cout << "so du = " << tk.soDu << " (phai bang 0)\n";
}
```

**Tìm lỗi:** lớp có `khoa`, vậy vì sao số dư vẫn có thể sai?

??? tip "Xem đáp án"
    **Lỗi:** khóa chỉ bảo vệ khi **mọi** đường cùng xin nó. `rut()` xin khóa, `nap()` thì không, nên hai hàm vẫn đụng `soDu` cùng lúc.

    **Mình đã chạy:** không `-O`, 20/20 lần sai (`so du = 3927`, `12141`, `15254`); `-O2` 5/20 lần sai (lần đo trước trên cùng máy ra 7/20 và 0/20: đổi theo tải máy). TSan chỉ đúng bên quên: bên `rut` có dòng `mutexes`, bên `nap` không có.

    ```text
    Read of size 4 at 0x… by thread T2 (mutexes: write M11):  #0 TaiKhoan::rut() 02.cpp:10
    Previous write of size 4 at 0x… by thread T1:             #0 TaiKhoan::nap() 02.cpp:12
    ```

    **Sửa** (đã chạy: 50/50 lần in `0`, TSan sạch): thêm `std::lock_guard<std::mutex> giu(khoa);` vào đầu `nap()`. Khi review, với mỗi biến được khóa hãy **tìm mọi chỗ nhắc tới nó** (getter, hàm phụ, hàm hủy).

### Mục 3: hai khóa ngược thứ tự

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex bepGas, tuLanh;
void nauMon1() {
    std::lock_guard<std::mutex> a(bepGas);                              // (1)
    std::this_thread::sleep_for(std::chrono::milliseconds(50));         // (2) trễ để lỗi hiện chắc
    std::lock_guard<std::mutex> b(tuLanh);                              // (3)
    std::cout << "mon 1 xong\n";
}
void nauMon2() {
    std::lock_guard<std::mutex> a(tuLanh);                              // (4) thứ tự ngược
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    std::lock_guard<std::mutex> b(bepGas);                              // (5)
    std::cout << "mon 2 xong\n";
}
int main() {
    std::thread t1(nauMon1), t2(nauMon2);
    t1.join();
    t2.join();
}
```

**Tìm lỗi:** chương trình có thoát không? Dòng `sleep_for` có phải là lỗi?

??? tip "Xem đáp án"
    **Lỗi:** deadlock do thứ tự khóa ngược: `nauMon1` giữ `bepGas` rồi xin `tuLanh`, `nauMon2` giữ `tuLanh` rồi xin `bepGas`; mỗi bên giữ thứ bên kia cần. `sleep_for` **không phải lỗi**, nó chỉ mở rộng cửa sổ cho lỗi hiện chắc.

    **Mình đã chạy:** có `sleep_for`, `timeout 3 ./ct` giết ở mã `124` cả 10/10 lần; bỏ hai dòng `sleep_for` chỉ treo **1/300** lần (code qua test vẫn treo ở production). TSan chạy trên bản **treo thật** không in gì trước khi bị giết. Cho hai hàm chạy **lần lượt** (`t1.join()` trước khi tạo `t2`, không treo) thì TSan thấy đảo thứ tự (`TSAN_OPTIONS=second_deadlock_stack=1`):

    ```text
    WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock)
      Cycle in lock order graph: M11 (0x…) => M12 (0x…) => M11
    ```

    **Sửa** (đã chạy: 100/100 lần không treo, TSan sạch): xin cả hai khóa một lần, thứ tự trong do `scoped_lock` lo ([Bài 26](../nhom-3-da-luong/26-deadlock.md)):

    ```diff
    -    std::lock_guard<std::mutex> a(bepGas);
    -    std::lock_guard<std::mutex> b(tuLanh);
    +    std::scoped_lock lk(bepGas, tuLanh);     // nauMon2: scoped_lock lk(tuLanh, bepGas)
    ```

### Mục 4: lost wakeup

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable chuong;
void tho() {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));   // (1) thợ tới muộn
    std::unique_lock<std::mutex> lk(khoa);
    chuong.wait(lk);                                              // (2) chờ, không kiểm điều kiện
    std::cout << "tho nhan duoc tin\n";
}
int main() {
    std::thread t(tho);
    std::this_thread::sleep_for(std::chrono::milliseconds(1));    // (3) main "chuẩn bị" 1 ms
    chuong.notify_one();                                          // (4) báo, có thể trước khi thợ chờ
    t.join();
    std::cout << "xong\n";
}
```

**Tìm lỗi:** chuyện gì xảy ra nếu `notify_one` chạy trước khi thợ vào `wait`?

??? tip "Xem đáp án"
    **Lỗi:** lost wakeup. `notify_one` chỉ đánh thức luồng **đang chờ lúc đó**; thợ tới sau thì tin đã bay mất, và `wait` trần không có gì để kiểm lại nên ngủ mãi. Tin phải **nằm lại trong một biến**, không phải là sự kiện bay qua.

    **Mình đã chạy:** lỗi này **hiếm tự nhiên**: bỏ dòng (1) chỉ treo **2/300** lần (thợ thường kịp vào `wait` trong 1 ms của `main`). Có dòng (1) (chèn trễ có kiểm soát) thì treo **10/10** lần, mã `124`; cách làm lỗi hiện chắc này là cách của [Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md).

    **Sửa** (đã chạy: 100/100 lần không treo, kể cả có dòng (1); TSan sạch): điều kiện thật nằm trong biến, đổi **trong khóa**, `wait` có predicate:

    ```diff
    +bool coTin = false;
    -    chuong.wait(lk);
    +    chuong.wait(lk, [] { return coTin; });
    -    chuong.notify_one();
    +    { std::lock_guard<std::mutex> giu(khoa); coTin = true; }
    +    chuong.notify_one();
    ```

### Mục 5: `if` thay vì `while`

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

std::mutex khoa;
std::condition_variable chuong;
int phan = 0;                                  // số phần ăn đang sẵn
void khach() {
    std::unique_lock<std::mutex> lk(khoa);
    if (phan == 0) chuong.wait(lk);            // (1) chỉ kiểm một lần
    --phan;                                    // (2) lấy một phần
    std::cout << "khach lay, con " << phan << "\n";
}
int main() {
    std::thread a(khach), b(khach);
    for (int k = 0; k < 2; ++k) {              // đưa MỘT phần, hai lần, mỗi lần đánh thức cả hai
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        { std::lock_guard<std::mutex> giu(khoa); ++phan; }
        chuong.notify_all();                   // (3)
    }
    a.join(); b.join();
}
```

**Tìm lỗi:** hai khách chờ, bếp đưa **một** phần rồi `notify_all`. Mỗi khách in `con` bao nhiêu?

??? tip "Xem đáp án"
    **Lỗi:** `wait` dưới `if` chỉ kiểm điều kiện **một lần, trước khi ngủ**. `notify_all` đánh thức cả hai: khách thứ nhất lấy phần duy nhất, khách thứ hai (đã dậy, đang xin lại khóa) không nhìn lại mà trừ tiếp thành âm. Dậy vì `notify`, vì bị cướp mất phần, hay vì **spurious wakeup** (chuẩn cho phép `wait` trả về mà không ai báo), điều kiện đều có thể sai.

    **Mình đã chạy:** 5/5 lần in `khach lay, con 0` rồi `khach lay, con -1`. **TSan sạch, thoát mã 0**: mọi truy cập đều trong khóa nên không có data race; đây là lỗi logic. Mình **không ép được** spurious wakeup xuất hiện theo ý muốn trên máy này; "dậy khi điều kiện đã bị lấy mất" là cùng một lỗi và tái hiện chắc.

    **Sửa** (đã chạy: 20/20 lần in `con 0` hai lần, TSan sạch): đổi `if (phan == 0)` thành `while (phan == 0)`, hoặc dùng `wait` có predicate `chuong.wait(lk, [] { return phan > 0; });` (tương đương).

### Mục 6: `detach` giữ tham chiếu tới biến cục bộ

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

void giaoViec() {
    std::string mon = "pho bo tai nam gau sach, du dai de nam tren heap";
    std::thread([&mon] {                                           // (1) bắt tham chiếu
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        std::cout << "lam mon: " << mon << "\n";                   // (2) đọc sau khi hàm đã thoát
    }).detach();                                                   // (3) thả cho chạy nền
}                                                                  // (4) mon bị hủy ở đây
int main() {
    giaoViec();
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
}
```

**Tìm lỗi:** `giaoViec` thoát ngay, luồng nền thức dậy sau 50 ms. Nó đọc cái gì?

??? tip "Xem đáp án"
    **Lỗi:** luồng `detach` sống lâu hơn biến mà nó giữ tham chiếu. Ở (4) `mon` bị hủy (bộ đệm chuỗi trên heap bị giải phóng); 50 ms sau, luồng nền đọc một tham chiếu **treo**. `detach` không chờ được nên không gì đảm bảo `mon` còn sống.

    **Mình đã chạy:** chạy thường in `lam mon:` rồi **rác**; ASan mặc định chết `SEGV` trong `fwrite` mà không chỉ nguyên nhân. Bật `ASAN_OPTIONS=detect_stack_use_after_return=1` thì rõ:

    ```text
    ERROR: AddressSanitizer: heap-use-after-free
    READ of size 48 ... thread T1:   #2 operator() 06.cpp:10
    freed by thread T0 here:         #1 giaoViec() 06.cpp:12
    ```

    **Sửa** (đã chạy: in đúng `lam mon: pho bo ...`, ASan có tùy chọn trên và TSan sạch): bắt **bản sao** `[mon]`, luồng nền tự sở hữu dữ liệu; cần kết quả thì `join` hay `future` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)). Đổi `[&mon]` thành `[mon]`. `sleep_for(200 ms)` ở `main` chỉ để demo.

### Mục 7: `shared_ptr` bị gán lại đồng thời

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <memory>
#include <thread>

struct CauHinh { int soMon; };
std::shared_ptr<CauHinh> chung = std::make_shared<CauHinh>(CauHinh{0});   // (1) một biến chung
int main() {
    std::thread ghi([] {
        for (int i = 1; i <= 100000; ++i)
            chung = std::make_shared<CauHinh>(CauHinh{i});         // (2) gán lại biến chung
    });
    std::thread doc([] {
        long long tong = 0;
        for (int i = 0; i < 100000; ++i) {
            std::shared_ptr<CauHinh> ban = chung;                  // (3) sao chép biến chung
            tong += ban->soMon;
        }
        std::cout << "doc xong, tong > 0: " << (tong > 0) << "\n";
    });
    ghi.join();
    doc.join();
}
```

**Tìm lỗi:** `shared_ptr` nổi tiếng là "an toàn luồng". Vậy lỗi ở đâu?

??? tip "Xem đáp án"
    **Lỗi:** `shared_ptr` an toàn ở tầng **bộ đếm** (mỗi luồng giữ bản sao riêng), nhưng **một biến `shared_ptr` bị đọc và gán đồng thời** thì không: luồng đọc có thể chép con trỏ cũ rồi tăng bộ đếm của khối **đã bị luồng ghi giải phóng** ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)).

    **Mình đã chạy:** `-O2` chết 21/30 lần (mã `139`; đổi theo máy); lúc chạy ra thì chỉ in `tong > 0`, dễ qua test. ASan trong 20 lần: 4 lần `heap-use-after-free`, 1 `SEGV`, 12 `abort`, 3 sạch. TSan báo nhiều `data race` trên `chung`. Báo cáo ASan rõ nhất: `heap-use-after-free`, `WRITE of size 4 ... thread T2: #6 operator() 07.cpp:15`, `freed by thread T1 here: #10 operator() 07.cpp:10`.

    **Sửa** (đã chạy: 50/50 lần sạch, TSan và ASan sạch): **một mutex quanh biến**, phần trong khóa ngắn (tạo đối tượng mới ngoài khóa):

    ```diff
    +std::mutex khoa;
    -            chung = std::make_shared<CauHinh>(CauHinh{i});
    +            auto moi = std::make_shared<CauHinh>(CauHinh{i});
    +            std::lock_guard<std::mutex> giu(khoa);
    +            chung = moi;
    -            std::shared_ptr<CauHinh> ban = chung;
    +            std::shared_ptr<CauHinh> ban;
    +            { std::lock_guard<std::mutex> giu(khoa); ban = chung; }
    ```

### Mục 8: trả tham chiếu ra khỏi vùng khóa

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

struct Bang {
    std::mutex khoa;
    std::string chu = "thuc don hom nay, du dai de nam tren heap";
    const std::string& lay() {
        std::lock_guard<std::mutex> giu(khoa);
        return chu;                            // (1) trả tham chiếu: khóa nhả ngay sau đây
    }
    void dat(const std::string& s) { std::lock_guard<std::mutex> giu(khoa); chu = s; }
};
int main() {
    Bang bang;
    std::thread ghi([&] {
        for (int i = 0; i < 100000; ++i)
            bang.dat("thuc don so " + std::to_string(i) + ", dai de nam tren heap");
    });
    long tong = 0;
    for (int i = 0; i < 100000; ++i)
        for (char c : bang.lay()) tong += c;                       // (2) đọc ngoài khóa
    ghi.join();
    std::cout << "xong " << (tong > 0) << "\n";
}
```

**Tìm lỗi:** mọi hàm đều có `lock_guard`. Khóa hết mà vẫn sai ở đâu?

??? tip "Xem đáp án"
    **Lỗi:** `lay()` khóa nhưng trả **tham chiếu** tới `chu` rồi nhả khóa khi hàm kết thúc; người gọi đọc `chu` ở (2) khi **không còn khóa**, đúng lúc `dat` ghi. Khóa chỉ bảo vệ bên trong hàm, không bảo vệ thứ đã "thoát" ra ngoài ([Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md)).

    **Mình đã chạy:** chạy thường luôn in `xong 1` (5/5 lần): lỗi ẩn hoàn toàn. TSan báo cả 3 lần thử: `Write of size 8 ... by thread T1 (mutexes: write M11): operator() 08.cpp:19` và `Previous read of size 1 ... by main thread: main 08.cpp:23`. Để ý bên đọc **không** có dòng `mutexes`.

    Biến thể mình thử (`dat` ghi các chuỗi dài dần nên bộ đệm **cấp phát lại**): tham chiếu treo thật, ASan báo `heap-use-after-free` 5/5 lần.

    **Sửa** (đã chạy: TSan và ASan sạch): đổi kiểu trả về `const std::string&` thành `std::string`, tức trả **bản sao**, sao chép khi còn giữ khóa. Muốn khỏi sao chép thì đưa việc cần làm vào trong hàm của lớp, chạy dưới khóa.

### Mục 9: `vector<bool>` mỗi luồng một ô

```cpp
// bo-qua-kiem-tra
#include <functional>
#include <iostream>
#include <thread>
#include <vector>

void lat(std::vector<bool>& v, int dau) {      // lật các ô dau, dau+2, ... một số CHẴN lần
    for (int lan = 0; lan < 100000; ++lan)
        for (int i = dau; i < 64; i += 2) v[i] = !v[i];
}
int main() {
    std::vector<bool> o(64, false);            // (1) 64 ô, mỗi ô một bit
    std::thread a(lat, std::ref(o), 0);        // (2) luồng a: ô chẵn
    std::thread b(lat, std::ref(o), 1);        // (3) luồng b: ô lẻ, không chung ô nào với a
    a.join(); b.join();
    int bat = 0;
    for (bool x : o) bat += x;
    std::cout << "o dang bat = " << bat << " (phai la 0)\n";
}
```

**Tìm lỗi:** hai luồng không bao giờ chạm cùng một ô, và với `vector<int>` thì an toàn. Vì sao ở đây lại sai?

??? tip "Xem đáp án"
    **Lỗi:** `vector<bool>` nén mỗi phần tử thành **một bit**; 64 ô nằm gọn trong một từ 8 byte. Ghi một bit là đọc cả từ, đổi bit, ghi cả từ, nên hai luồng sửa hai ô **khác nhau** vẫn đụng cùng một từ nhớ. Luật "mỗi luồng một phần tử riêng thì an toàn" có ngoại lệ đúng ở kiểu này ([Bài 54](../nhom-7-chon-dung-cong-cu/54-container-da-luong.md)).

    **Mình đã chạy:** không `-O`, 20/20 lần sai (còn bật 21 đến 38 ô); `-O2` sai 18/20 lần. Đáng ra phải `0` vì mỗi ô được lật chẵn lần. TSan báo đúng chỗ: `Read of size 8 ... by thread T2: 09.cpp:8`, `Previous write of size 8 ... by thread T1: 09.cpp:8`, `Location is heap block of size 8` (cả 64 ô nằm trong 8 byte).

    **Sửa** (đã chạy: 50/50 lần in `0`, TSan sạch): kiểu mỗi phần tử một byte như `vector<char>` (hoặc `deque<bool>`, hoặc mảng riêng cho từng luồng):

    ```diff
    -void lat(std::vector<bool>& v, int dau) {     // và: std::vector<bool> o(64, false);
    +void lat(std::vector<char>& v, int dau) {     // và: std::vector<char> o(64, 0);
    -    for (bool x : o) bat += x;
    +    for (char x : o) bat += x;
    ```

### Mục 10: gọi callback khi đang giữ khóa

```cpp
// bo-qua-kiem-tra
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

struct SuKien {
    std::mutex khoa;
    std::vector<std::function<void()>> ds;
    void dangKy(std::function<void()> f) { std::lock_guard<std::mutex> giu(khoa); ds.push_back(f); }
    void phat() {
        std::lock_guard<std::mutex> giu(khoa);
        for (auto& f : ds) f();                // (1) gọi callback khi đang giữ khóa
    }
};
int main() {
    SuKien sk;
    sk.dangKy([&] { std::cout << "chuong keu\n"; });
    sk.dangKy([&] { sk.dangKy([] {}); });      // (2) callback lại gọi dangKy: xin khóa lần hai
    std::thread t([&] { sk.phat(); });
    t.join();
    std::cout << "xong\n";
}
```

**Tìm lỗi:** chương trình có in `xong` không? Điều gì xảy ra ở callback thứ hai?

??? tip "Xem đáp án"
    **Lỗi:** `phat()` gọi mã **của người khác** (callback) khi còn giữ `khoa`. Callback thứ hai gọi `dangKy`, hàm này xin đúng `khoa` đó; `std::mutex` không cho cùng luồng xin hai lần (hành vi không xác định, trên máy mình là treo). Mã lạ trong khóa còn có thể ngủ lâu, ném ngoại lệ, hay xin khóa khác (thành deadlock như mục 3).

    **Mình đã chạy:** `timeout 3` giết ở mã `124`, chỉ in được `chuong keu` (chạy với `stdbuf -oL` để dòng này không kẹt trong bộ đệm). TSan trên bản treo không in gì. Dừng bằng `gdb` (như [Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md)) thì luồng phụ đứng trong khóa: `Thread 2: #3 ___pthread_mutex_lock ... #7 SuKien::dangKy(std::function<void ()>) 10.cpp:10`, còn `Thread 1: #4 std::thread::join() ... #5 main () 10.cpp:21`.

    **Sửa** (đã chạy: 50/50 lần in `chuong keu`, `xong`; TSan sạch): trong `phat()`, chép danh sách ra biến cục bộ `ban` khi giữ khóa (`{ std::lock_guard<std::mutex> giu(khoa); ban = ds; }`), rồi `for (auto& f : ban) f();` **ngoài** khóa.

### Mục 11: hai `atomic`, một bất biến

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <iostream>
#include <thread>

std::atomic<int> trai{100}, phai{0};           // (1) bất biến: trai + phai luôn bằng 100
std::atomic<bool> dung{false};
int main() {
    std::thread chuyen([] {
        for (int i = 0; i < 1000000; ++i) {
            trai -= 10; phai += 10;            // (2) chuyển 10 sang phải: hai bước riêng
            trai += 10; phai -= 10;            //     rồi chuyển lại
        }
        dung = true;
    });
    long long sai = 0;
    while (!dung) {
        int tong = trai + phai;                // (3) người quan sát đọc hai biến
        if (tong != 100) ++sai;
    }
    chuyen.join();
    std::cout << "thay tong != 100: " << (sai > 0 ? "co" : "khong") << "\n";
}
```

**Tìm lỗi:** mọi biến đều `atomic`, không có data race. Vậy `tong` có luôn bằng 100 không?

??? tip "Xem đáp án"
    **Lỗi:** mỗi phép trên một `atomic` là nguyên tử, nhưng **hai phép** liên tiếp thì không: giữa `trai -= 10` và `phai += 10` người quan sát đọc được `trai` đã giảm mà `phai` chưa tăng (tổng 90), và hai lần đọc `trai`, `phai` của nó cũng có thể bị luồng chuyển chen vào giữa. Bất biến liên quan **nhiều biến** cần một khóa bao cả nhóm ([Bài 28](../nhom-3-da-luong/28-atomic.md)); lỗi xảy ra dù chỉ có một luồng ghi.

    **Mình đã chạy:** 10/10 lần in `thay tong != 100: co`; số lần thấy tổng sai (bản in số đếm, `-O2`, ba lần) là `15166947`, `9066313`, `22437659`. **TSan sạch, thoát mã 0**: không có data race vì `atomic` hợp lệ, nên đây là lỗi mà công cụ không thấy; chỉ người đọc bất biến mới thấy.

    **Sửa** (đã chạy: `co` thành `khong`, TSan sạch): hai số thường và một `mutex`; **cả hai bước đổi** và **việc đọc** đều nằm trong khóa:

    ```diff
    -std::atomic<int> trai{100}, phai{0};
    +std::mutex khoa;
    +int trai = 100, phai = 0;
    +            std::lock_guard<std::mutex> giu(khoa);   // trong luồng chuyển, trước hai cặp phép tính
    +        std::lock_guard<std::mutex> giu(khoa);       // trong vòng đọc, trước phép cộng
    ```

### Mục 12: quên `join`

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>

int main() {
    std::thread t([] { std::cout << "lam viec\n"; });   // (1) tạo luồng
    std::cout << "main xong\n";
    return 0;                                  // (2) t bị hủy khi còn joinable
}
```

**Tìm lỗi:** chương trình kết thúc êm không? Luồng `t` đã chạy xong hay chưa có quan trọng không?

??? tip "Xem đáp án"
    **Lỗi:** hủy một `std::thread` **còn joinable** (chưa `join`, chưa `detach`) gọi `std::terminate`, bất kể luồng đã in xong hay chưa: quy tắc nằm ở trạng thái của đối tượng `thread`.

    **Mình đã chạy:** trong terminal in `main xong` (có khi kèm `lam viec`), rồi `terminate called without an active exception`, thoát mã `134`; qua đường ống thì các dòng in **mất** vì `abort` không xả bộ đệm. Biến thể nguy hiểm hơn: `throw` giữa lúc tạo luồng và `join`, bao ngoài bằng `try/catch` (mình đã chạy): `catch` **không** chạy, vì hủy `t` lúc dọn stack đã gọi `terminate`, cùng thông báo và mã `134`.

    **Sửa** (đã chạy: mã 0, in đủ hai dòng, TSan sạch): `join` trước khi `t` bị hủy; có `return` sớm hay `throw` thì bọc luồng bằng lớp RAII `join` ở hàm hủy ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)). C++20 có `std::jthread` tự `join` (mình đã biên dịch và chạy với `-std=c++20`; `-std=c++17` báo `'jthread' is not a member of 'std'`):

    ```diff
    +    t.join();
         return 0;
    ```

### Bảng phân loại: triệu chứng, nguyên nhân hay gặp

| Triệu chứng | Nghi trước | Công cụ đầu tiên | Mục |
|---|---|---|---|
| Kết quả sai, đổi theo lần chạy, có khi đúng khi bật `-O2` | Data race: biến chung không khóa, quên một đường, `vector<bool>` | TSan; xem dòng `(mutexes: ...)` | 1, 2, 9 |
| Treo, không dùng CPU | Khóa ngược thứ tự, callback xin lại khóa, lost wakeup | `timeout`, rồi `gdb`: luồng đứng ở `mutex_lock` hay `cond_wait` | 3, 4, 10 |
| Chết ngẫu nhiên (mã 139, `abort`), in rác | Tham chiếu hay con trỏ tới thứ đã chết: `detach`, `shared_ptr`, tham chiếu thoát khỏi khóa | ASan (kèm `detect_stack_use_after_return=1`) | 6, 7, 8 |
| Giá trị "không thể có" (số âm, tổng lệch), **TSan sạch** | Lỗi logic: `if` thay `while`, hai `atomic` cho một bất biến | Đọc code theo điều kiện và bất biến | 5, 11 |
| `terminate called without an active exception`, mã 134 | `thread` bị hủy khi còn joinable | Kiểm mọi đường thoát (`return`, `throw`) | 12 |

!!! info "Bạn biết Go?"
    Vài khác biệt (kiến thức ngôn ngữ, mình không chạy Go ở bài này): `go run -race` là bộ phát hiện data race cùng họ ThreadSanitizer, ứng với TSan ở mục 1, 2, 7. `sync.Mutex` của Go cũng không cho khóa hai lần nên callback gọi lại khóa (mục 10) cũng tự treo; runtime chỉ báo `all goroutines are asleep` khi **mọi** goroutine đều kẹt. Khi `main` của Go trả về, mọi goroutine bị dừng, không có `terminate` như mục 12. Phần tử của `[]bool` mỗi cái một byte nên mục 9 không xảy ra. Trả địa chỉ biến cục bộ ở Go hợp lệ nhờ escape analysis, nên mục 6 không có tương đương.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Cho một đoạn code đa luồng lạ, bạn đọc theo thứ tự nào để tìm lỗi?"
    Mình làm bốn việc. Một: gạch chân dữ liệu mà từ hai luồng trở lên chạm tới. Hai: với mỗi dữ liệu, hỏi cái gì bảo vệ nó và **mọi** đường truy cập có qua cái đó không. Ba: nhìn mọi chỗ chờ, hỏi điều kiện nằm ở biến nào và `wait` có kiểm lại sau khi dậy không. Bốn: hỏi vòng đời, luồng hay dữ liệu chết trước, và `thread` nào còn joinable lúc bị hủy. Khi nói lại, mình trình bày lỗi, hậu quả theo thứ tự thời gian, rồi bản sửa.

??? question "Thế nếu TSan chạy sạch thì code có đúng không?"
    Không chắc. TSan chỉ bắt **data race** trong những lần chạy nó quan sát. Nó im với lỗi logic mà mọi truy cập đều hợp lệ: `if` thay `while` ở `wait` (ra số âm), hai `atomic` cho một bất biến (tổng lệch), và nó cũng không in gì trên các bản treo thật mà mình chạy (mục 3, 10). Vì thế mình còn đọc theo điều kiện và bất biến, chạy lặp có `timeout`, và dùng ASan cho lỗi vòng đời.

??? question "Lost wakeup và spurious wakeup khác nhau thế nào, vì sao sửa giống nhau?"
    Lost wakeup là `notify` đến **trước** khi luồng chờ vào `wait`, tin biến mất và luồng ngủ mãi. Spurious wakeup là `wait` trả về dù không ai báo, kéo theo "dậy nhưng điều kiện chưa đúng" (cũng gặp khi luồng khác cướp mất việc). Cả hai sửa bằng cách đặt điều kiện thật trong một biến, đổi nó trong khóa, và `wait` có predicate hoặc vòng `while`: kiểm biến **trước khi ngủ** chặn lost wakeup, kiểm lại **sau khi dậy** chặn dậy sai.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Chỉ nêu tên lỗi mà không nói cơ chế"
    "Đoạn này có data race" chưa đủ. Người phỏng vấn muốn nghe **thứ tự thời gian**: luồng A đọc 5, luồng B đọc 5, cả hai ghi 6. Nói được trình tự này thì bản sửa đúng tự theo sau.

!!! warning "Lỗi 2: Sửa bằng `sleep`, `volatile`, hoặc thêm khóa ở một chỗ"
    `sleep_for` chỉ đổi xác suất (mục 3 và 4 dùng nó để **làm lỗi hiện**, không phải để sửa). `volatile` không tạo đồng bộ giữa các luồng. Thêm khóa vào đúng một hàm mà bỏ sót đường khác thì quay lại mục 2.

!!! warning "Lỗi 3: Tin rằng \"chạy thấy đúng\" hay \"TSan sạch\" là xong"
    Mục 1 in đúng 20/20 lần dưới `-O2` dù sai; mục 5 và 11 sạch dưới TSan dù sai. Chứng minh sửa đúng là chạy lại đúng cách làm lỗi hiện chắc (chèn trễ, chạy lặp), kèm TSan hoặc ASan sạch, kèm lập luận về bất biến.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="76" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Hai luồng cùng gọi hai hàm sau. Lỗi ở đâu?

```text
std::mutex m;  std::vector<int> v;
void them(int x) { std::lock_guard<std::mutex> g(m); v.push_back(x); }
int  dau()       { return v.front(); }
```

- `lock_guard` không dùng được với `vector`, phải dùng `unique_lock`
- `front()` trả bản sao nên không đụng tới vùng nhớ của `vector`
- `dau()` không xin `m`, nên có thể đọc đúng lúc `them` đang ghi
- `push_back` phải gọi sau `reserve`, nếu không khóa vô tác dụng

<p class="giai-thich" markdown>Khóa chỉ bảo vệ khi mọi đường truy cập cùng xin nó; `dau()` đọc `v` không khóa trong lúc `push_back` có thể đổi vùng nhớ, nên đó là data race. `lock_guard` dùng với mutex nào cũng được, `unique_lock` không cần thiết. `front()` trả tham chiếu, và dù trả bản sao thì việc đọc phần tử để sao chép vẫn là truy cập không đồng bộ. `reserve` chỉ giảm số lần cấp phát lại, không thay được khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Hai luồng thợ cùng chạy đoạn sau; người sản xuất đẩy **một** việc rồi `notify_all`. Lỗi ở đâu?

```text
std::unique_lock<std::mutex> lk(m);
if (hang.empty()) cv.wait(lk);
auto viec = hang.front();  hang.pop();
```

- `if` chỉ kiểm hàng một lần, nên thợ thứ hai dậy rồi lấy từ hàng rỗng
- `notify_all` không được dùng với hàng đợi, chỉ `notify_one` mới đúng
- `unique_lock` không truyền được vào `wait`, phải đổi sang `lock_guard`
- `front()` phải gọi trước `wait` để lấy việc sớm hơn khi hàng chưa rỗng

<p class="giai-thich" markdown>Cả hai thợ cùng dậy nhưng chỉ có một việc; thợ thứ nhất lấy xong, thợ thứ hai không kiểm lại vì đã qua câu `if`, rồi đọc `front()` của hàng rỗng. Sửa bằng `while (hang.empty()) cv.wait(lk);` hoặc `wait` có predicate. `notify_all` dùng được, miễn điều kiện được kiểm lại sau khi dậy. `wait` **cần** `unique_lock` vì phải nhả và xin lại khóa; `lock_guard` mới là thứ không truyền được. `front()` trước `wait` đọc hàng khi chưa có gì.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Luồng khác có thể gọi `them` bất cứ lúc nào. Lỗi ở đâu?

```text
const std::vector<int>& Kho::tatCa() {
    std::lock_guard<std::mutex> g(m);
    return ds;
}
...  for (int x : kho.tatCa()) tong += x;
```

- `lock_guard` bị hủy quá sớm nên mutex chưa bao giờ được khóa
- `tatCa()` phải khai báo `static`, nếu không các luồng dùng chung khóa
- Vòng `for` luôn sao chép `ds` trước khi duyệt nên mọi thứ an toàn
- Tham chiếu thoát khỏi khóa: vòng `for` duyệt `ds` khi không còn khóa

<p class="giai-thich" markdown>`lock_guard` chỉ sống trong hàm; hàm trả về tham chiếu rồi nhả khóa, sau đó vòng `for` duyệt `ds` mà không ai bảo vệ, và nếu luồng khác `push_back` thì iterator bị vô hiệu. Mutex vẫn được khóa trong hàm, nó không bị hủy sớm hơn lệnh `return`. `static` không liên quan tới việc khóa. Range-for trên tham chiếu duyệt chính `ds`, không sao chép.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Hàm `chay()` thoát ngay, trong khi luồng vẫn đang chạy. Lỗi ở đâu?

```text
void chay() {
    int ketQua = 0;
    std::thread t([&] { ketQua = tinh(); });
    t.detach();
}
```

- `detach` luôn gây `terminate`, nên mọi chương trình phải dùng `join`
- `ketQua` hết sống khi `chay()` thoát, luồng nền ghi vào ô đã chết
- `ketQua` phải khai báo `volatile` để luồng nền thấy giá trị mới
- Lambda không được bắt biến bằng `[&]` khi dùng với `thread`

<p class="giai-thich" markdown>Luồng `detach` sống lâu hơn biến cục bộ mà nó giữ tham chiếu, nên nó ghi vào vùng stack đã được trả lại, đúng lỗi vòng đời ở mục 6. `detach` không gây `terminate`; cái gây ra là hủy `thread` còn joinable. `volatile` không giải quyết vòng đời lẫn đồng bộ. `[&]` hợp lệ với `thread`, chỉ nguy hiểm khi luồng sống lâu hơn biến.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Chương trình thỉnh thoảng thấy `trai + phai` bằng 90 dù cả hai là `std::atomic<int>`, và TSan chạy sạch. Giải thích hợp lý nhất?

- TSan bị lỗi nên không báo race, cần chạy lại bằng ASan để chắc chắn
- Tốc độ của `atomic<int>` không theo kịp luồng ghi, cần tăng số vòng lặp
- Hai biến chung một bất biến, người đọc xen giữa hai bước đổi
- Biên dịch bằng `-O0` làm `atomic` mất tác dụng, phải dùng `-O2`

<p class="giai-thich" markdown>Từng phép trên `atomic` là nguyên tử, nhưng người đọc có thể thấy `trai` đã đổi còn `phai` chưa, nên tổng lệch; TSan im vì không có data race, và cách sửa là một mutex bao cả hai biến. TSan không sai ở đây. Tốc độ không quyết định tính đúng. Mức tối ưu không tắt tính nguyên tử của `atomic`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Chương trình in `terminate called without an active exception` rồi thoát mã 134, dù luồng phụ đã chạy xong. Nguyên nhân hay gặp nhất?

- Đối tượng `std::thread` bị hủy khi chưa `join` và chưa `detach`
- Luồng phụ ném ngoại lệ mà không có `try/catch` trong hàm của nó
- Luồng phụ còn giữ khóa lúc `main` thoát nên hệ điều hành hủy khóa
- Luồng phụ chạy xong trước `main` nên bị hệ điều hành đóng đột ngột

<p class="giai-thich" markdown>Hủy `std::thread` còn joinable gọi `terminate`, bất kể luồng đã xong hay chưa, vì quy tắc nằm ở trạng thái đối tượng. Ngoại lệ thoát khỏi hàm của luồng cũng gọi `terminate` nhưng thông báo nêu kiểu ngoại lệ (`after throwing an instance of`). Mutex đang giữ không làm chương trình `terminate`. Luồng chạy xong sớm là chuyện bình thường; cần `join` để thu dọn chứ không gây lỗi.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Đọc code đa luồng bằng bốn câu hỏi: dữ liệu nào chung, cái gì bảo vệ và **mọi** đường có xin không, đang chờ điều kiện nào nằm ở biến nào, ai sống lâu hơn ai; khi nói, trình bày lỗi, thứ tự thời gian gây hại, bản sửa.
2. Không đồng bộ (mục 1, 2, 7, 8, 9): TSan bắt, chạy thường hay **ẩn** (mục 1 đúng 20/20 lần dưới `-O2`); `shared_ptr` chỉ an toàn ở bộ đếm, không phải ở một biến bị gán đồng thời; trả tham chiếu ra khỏi khóa hay dùng `vector<bool>` chia ô đều phá bảo vệ.
3. Đồng bộ sai (mục 3, 4, 5, 10, 11): khóa ngược thứ tự thì dùng `scoped_lock`, `wait` luôn có predicate hoặc `while`, đừng gọi callback khi giữ khóa, bất biến nhiều biến cần một mutex; mục 5 và 11 **TSan sạch** nhưng vẫn sai, và ở hai ca treo mình chạy (mục 3, 10) TSan không in gì trước khi `timeout` giết.
4. Vòng đời (mục 6, 12): luồng `detach` chỉ dùng bản sao dữ liệu; `std::thread` joinable bị hủy gọi `terminate` (mã 134), kể cả khi ngoại lệ thoát giữa chừng, nên cần `join` hoặc RAII.
5. Công cụ theo triệu chứng: sai thất thường dùng TSan, treo dùng `timeout` rồi `gdb`, chết ngẫu nhiên hay in rác dùng ASan (lỗi stack cần `detect_stack_use_after_return=1`), TSan sạch mà vẫn sai thì đọc bất biến; chứng minh sửa bằng cách làm lỗi hiện chắc rồi chạy lại, không bằng một lần chạy đẹp.
