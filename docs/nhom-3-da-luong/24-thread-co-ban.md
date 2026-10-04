# Bài 24 — std::thread: tạo luồng, join, detach và truyền tham số

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt **tiến trình** với **luồng**: luồng cùng tiến trình dùng chung heap và biến toàn cục, nhưng mỗi luồng có stack riêng; biết `goroutine` của Go không phải là luồng của hệ điều hành.
    - Tạo luồng bằng hàm và bằng lambda, chờ nó bằng `join`, biết `detach` làm gì và vì sao hiếm khi nên dùng.
    - Nói được vì sao tham số truyền cho luồng **mặc định bị sao chép**, và dùng `std::ref` hoặc `std::move` khi cần truyền tham chiếu hay `unique_ptr`.
    - Tránh ba lỗi hay gặp (hủy `std::thread` còn joinable, luồng `detach` cầm tham chiếu tới biến đã chết, ngoại lệ thoát khỏi hàm của luồng) và tự viết một lớp bọc nhỏ để luồng luôn được `join`.

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, heap, biến toàn cục), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, hàm hủy, `throw`/`catch`, `std::terminate`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (tham chiếu), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`unique_ptr`, `= delete`, `std::move`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, ASan), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) và [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda, `[&x]`, `[=]`), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector`, `emplace_back`).

!!! note "Phạm vi bài này"
    Bài này chỉ dạy cách **bắt đầu và kết thúc** một luồng. Mọi chương trình ở đây được thiết kế để các luồng không cùng sửa một biến; chuyện nhiều luồng cùng sửa một biến (data race, `std::mutex`) là Bài 25.

## 🧠 Câu chuyện mở đầu

Hãy tưởng tượng một **nhà bếp**. Mỗi chương trình đang chạy là một nhà bếp riêng, có **kho** ở sân sau (heap của [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)) và **bảng treo tường** (biến toàn cục). Mỗi **đầu bếp** là một luồng. Từ Bài 01 tới giờ, nhà bếp của bạn chỉ có đúng một đầu bếp: luồng chính, chạy hàm `main`.

Khi thêm đầu bếp, ba chuyện xảy ra. Mỗi người có **bàn học riêng** để đặt đồ đang cầm trên tay (stack riêng). Cả bếp **dùng chung kho và bảng treo tường**, nên người này thấy ngay món người kia để vào kho. Và đầu bếp chính có thể **đứng chờ** một đầu bếp phụ làm xong món (`join`), hoặc **để họ tự làm** mà không hỏi nữa (`detach`).

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Đầu bếp thật đứng song song. Luồng chỉ chạy song song thật khi máy có đủ lõi CPU; nếu có nhiều luồng hơn lõi, hệ điều hành cho các luồng thay phiên nhau rất nhanh. Ngoài ra "kho chung" là cả một chuyện lớn (hai người cùng sửa một món); bài này tránh nó, Bài 25 mới tới.

## 📖 Giải thích

### 1. Tiến trình và luồng

**Tiến trình (process)** là một chương trình đang chạy, được hệ điều hành cấp một vùng bộ nhớ riêng (stack, heap, vùng tĩnh như [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)). **Luồng (thread)** là một dòng chạy lệnh bên trong tiến trình. Mỗi luồng có stack riêng, nhưng mọi luồng của một tiến trình thấy cùng heap và cùng biến toàn cục. Ta sẽ thấy cả hai trong ví dụ 💻: mỗi luồng có biến cục bộ riêng (trên stack riêng) và cả bốn cùng đọc một `vector` ở heap.

| | Tiến trình | Luồng (cùng tiến trình) |
|---|---|---|
| Bộ nhớ | Riêng: tiến trình này không đọc được bộ nhớ của tiến trình kia | Chung heap và biến toàn cục; stack riêng |
| Nói chuyện với nhau | Phải nhờ hệ điều hành (ống là kênh một chiều giữa hai tiến trình, socket, bộ nhớ chia sẻ) | Đọc ghi thẳng vào biến chung (nên phải cẩn thận, Bài 25) |
| Một luồng gặp lỗi nặng (truy cập bộ nhớ sai) | Thường chỉ tiến trình đó sập | Thường cả tiến trình sập, mọi luồng chết theo |

!!! info "Bạn biết Go?"
    Goroutine **không phải** luồng của hệ điều hành. Runtime của Go lập lịch (quyết định cái nào chạy khi nào) rất nhiều goroutine lên một số ít luồng hệ điều hành; stack của goroutine bắt đầu nhỏ và tự lớn lên, nên tạo hàng chục nghìn goroutine vẫn bình thường. `std::thread` thì mỗi đối tượng là **một luồng thật** do hệ điều hành lập lịch, mỗi luồng có stack riêng (mình đọc giá trị mặc định của thư viện luồng trên máy này: 8388608 byte, tức 8 MiB; đó là vùng địa chỉ dành sẵn, chưa chắc dùng hết, và khác nhau theo hệ thống). Tạo hàng nghìn luồng vẫn là chi phí thật, nên bạn không tạo luồng C++ bừa bãi như `go f()`.

### 2. Luồng đầu tiên: tạo bằng hàm, chờ bằng `join`

Muốn dùng luồng cần `#include <thread>` (thư viện luồng của C++11). Dòng `std::thread t(congDon, 100);` tạo một **luồng mới** và bảo nó chạy `congDon(100)`: trong ngoặc, thứ nhất là hàm cần chạy, các thứ sau là đối số truyền cho hàm. Từ lúc dựng xong, luồng mới được phép chạy bất cứ lúc nào; chuẩn không hứa nó bắt đầu sớm hay muộn.

Luồng chính phải đợi trước khi dùng kết quả. `t.join()` làm đúng việc đó: nó **chặn luồng đang gọi** (ở đây là luồng chính) tới khi luồng `t` chạy xong. Chuẩn C++ bảo đảm mọi thứ luồng `t` đã ghi nhìn thấy được sau khi `join` trả về.

Khi biên dịch chương trình có luồng, thêm cờ `-pthread` (báo cho g++ biết ta dùng luồng; một số hệ thống bắt buộc):

```cpp
#include <iostream>
#include <thread>

long long tong = 0;                    // biến toàn cục: mọi luồng cùng thấy

void congDon(int n) {
    for (int i = 1; i <= n; ++i) {
        tong += i;                     // (1) chạy trong luồng mới
    }
}

int main() {
    std::thread t(congDon, 100);       // (2) tạo luồng, nó được phép chạy từ đây
    t.join();                          // (3) luồng chính đứng chờ t chạy xong
    std::cout << "tong = " << tong << "\n";   // (4)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số luồng đang sống |
|---|---|---|
| (2) | `main` dựng `t`: một luồng mới bắt đầu chạy `congDon(100)` | 2 (luồng chính và `t`) |
| (3), (1) | Luồng chính dừng ở `join`; `t` cộng 1 + 2 + ... + 100 vào `tong`, rồi kết thúc | 2, rồi 1 |
| (4) | `join` đã trả về; `tong` đủ 5050 và an toàn để đọc | 1 |

**Kết quả khi chạy:**

```text
tong = 5050
```

Mình cũng chạy chương trình này với `-fsanitize=thread` (công cụ bắt lỗi luồng, Bài 25 sẽ dạy): không có cảnh báo nào.

!!! info "Bạn biết Go?"
    `go f(x)` ↔ `std::thread t(f, x)`, nhưng C++ bắt bạn nói rõ chuyện chờ: `wg.Wait()` của `sync.WaitGroup` ứng với `t.join()` (mỗi `thread` tự `join`, không có bộ đếm chung). Go còn khác ở chỗ quên chờ không sao cả: khi `main` kết thúc, Go thoát và bỏ goroutine còn lại một cách êm ái (mình đã chạy kiểm). C++ quên `join`/`detach` thì chương trình bị `std::terminate` (mục 5). Thư viện chuẩn C++ cũng **không có channel**; Bài 27 dùng hàng đợi và `condition_variable` thay thế.

### 3. Truyền tham số: mặc định là sao chép

Các đối số đưa vào `std::thread t(f, a, b)` được **chép vào bộ nhớ riêng của luồng mới**, rồi hàm `f` nhận bản chép đó. Lý do nằm ở thời điểm: luồng mới có thể chạy rất muộn, lúc hàm đã gọi `std::thread` kết thúc và biến `a` trên stack của nó đã chết. Nếu luồng giữ tham chiếu tới `a` thì nó trỏ vào chỗ đã dọn ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)). Vì vậy chuẩn chọn mặc định an toàn: luồng giữ **bản sao riêng**.

Hệ quả: hàm nhận `int&` (tham chiếu sửa được) không nhận được đối số thường. Muốn thật sự truyền tham chiếu, bọc đối số bằng `std::ref(n)` (cần `#include <functional>`): `std::ref(n)` tạo một vật nhỏ ghi "dùng chính biến `n`". Luồng chép vật nhỏ đó, nên vẫn làm việc trên `n` gốc. Bạn phải tự bảo đảm `n` sống tới khi luồng xong.

Muốn truyền `unique_ptr` (không sao chép được, [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)) thì trao quyền bằng `std::move` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)). Còn lambda ([Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md)) cũng làm hàm của luồng được: `[&n] { ... }` giữ tham chiếu tới `n` (như `std::ref`), `[n] { ... }` giữ bản sao.

```cpp
#include <functional>
#include <iostream>
#include <memory>
#include <thread>

void tangBanSao(int x) { x += 100; }                 // nhận bản sao
void tangThat(int& x) { x += 100; }                  // nhận tham chiếu
void nhan(std::unique_ptr<int> p) {                  // nhận quyền sở hữu
    std::cout << "luong giu so " << *p << "\n";
}

int main() {
    int n = 1;

    std::thread a(tangBanSao, n);                    // (1) luồng nhận bản sao của n
    a.join();
    std::cout << "sau tangBanSao: n = " << n << "\n";

    std::thread b(tangThat, std::ref(n));            // (2) std::ref: truyền chính n
    b.join();
    std::cout << "sau tangThat + std::ref: n = " << n << "\n";

    std::thread c([&n] { n += 1000; });              // (3) lambda bắt tham chiếu
    c.join();
    std::cout << "sau lambda [&n]: n = " << n << "\n";

    auto p = std::make_unique<int>(7);
    std::thread d(nhan, std::move(p));               // (4) trao p cho luồng
    d.join();
    std::cout << "p con giu gi khong? " << (p != nullptr) << "\n";   // (5)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `a` nhận bản sao của `n`; hàm cộng 100 vào bản sao rồi bản sao mất | `n = 1` (không đổi) |
| (2) | `std::ref(n)` làm luồng `b` cộng thẳng vào `n` | `n = 101` |
| (3) | Lambda `[&n]` cộng 1000 vào `n` gốc | `n = 1101` |
| (4) | `std::move(p)` trao quyền sở hữu cho luồng; `p` ở `main` thành `nullptr` | `p` rỗng, luồng giữ số 7 |
| (5) | `p != nullptr` là `false`, in `0` | |

**Kết quả khi chạy:**

```text
sau tangBanSao: n = 1
sau tangThat + std::ref: n = 101
sau lambda [&n]: n = 1101
luong giu so 7
p con giu gi khong? 0
```

Mỗi luồng được `join` ngay trước khi luồng sau bắt đầu, nên không luồng nào chạy cùng lúc với luồng khác.

**Thử thay đổi: ở dòng (2) viết `std::thread b(tangThat, n);` (bỏ `std::ref`).** Mình đã chạy: lỗi biên dịch, dòng đầu là `error: static assertion failed: std::thread arguments must be invocable after conversion to rvalues`. Nghĩa là luồng đưa **bản sao tạm** của `n` cho hàm, mà `int&` không bám được vào một giá trị tạm. Hàm nhận `const int&` thì chạy được (mình đã thử), vì nó chỉ đọc bản sao.

!!! info "Bạn biết Go?"
    `go f(x)` cũng tính `x` ngay lúc gặp lệnh `go` rồi đưa bản sao cho goroutine (mình đã chạy: sửa `n` sau lệnh `go` không ảnh hưởng đối số đã đưa). Khác ở chỗ closure `go func() { ... n ... }()` của Go bắt `n` theo tham chiếu, giống `[&n]` chứ không giống `[n]`.

### 4. `join` hay `detach`

Mỗi đối tượng `std::thread` đang cầm một luồng thì gọi là **joinable** (còn nối được). `t.joinable()` cho biết điều đó. Sau khi `join` hoặc `detach`, `t` hết joinable. Quy tắc: **trước khi một `std::thread` joinable bị hủy, bạn phải gọi `join` hoặc `detach`** (mục 5 cho thấy làm sai thì sao).

| | `t.join()` | `t.detach()` |
|---|---|---|
| Ý nghĩa | Chờ luồng xong | Thả luồng chạy nền, không chờ nữa |
| Sau lệnh | `t.joinable()` là `false` | `t.joinable()` là `false`, và không còn cách chờ luồng đó |
| Dùng khi | Hầu hết mọi trường hợp | Việc nền độc lập, chỉ dùng bản sao của dữ liệu |

Ta thử `detach` bằng một luồng chỉ dùng bản sao tham số. Để thứ tự in ổn định, luồng nền ngủ 0,1 giây trước khi in, còn luồng chính ngủ 0,4 giây. Hai thứ mới ở đây: `std::this_thread::sleep_for(...)` làm **luồng đang gọi** ngủ một khoảng (các luồng khác vẫn chạy), và `std::chrono::milliseconds(100)` là một giá trị "khoảng thời gian 100 mili giây" (`std::chrono` là thư viện thời gian của C++11; mục 7 nói thêm).

```cpp
#include <chrono>
#include <iostream>
#include <thread>

void inLoi(int so) {                                 // chỉ dùng bản sao, không đụng biến nào của main
    std::this_thread::sleep_for(std::chrono::milliseconds(100));        // (1) làm việc "mất 0,1 giây"
    std::cout << "luong nen: nhan so " << so << "\n";
}

int main() {
    std::thread t(inLoi, 42);
    std::cout << "truoc detach, joinable = " << t.joinable() << "\n";   // (2)
    t.detach();                                      // (3) thả luồng chạy nền, không chờ nữa
    std::cout << "sau detach, joinable = " << t.joinable() << "\n";     // (4)

    // Không có cách chắc chắn biết luồng nền đã xong chưa: ta chỉ ngủ lâu hơn nó và hy vọng.
    std::this_thread::sleep_for(std::chrono::milliseconds(400));        // (5)
    std::cout << "main ket thuc\n";
    return 0;
}
```

**Kết quả khi chạy** (ba lần liền đều như nhau trên máy mình):

```text
truoc detach, joinable = 1
sau detach, joinable = 0
luong nen: nhan so 42
main ket thuc
```

Thứ tự dòng thứ ba và thứ tư chỉ **dựa vào giấc ngủ**, không phải bảo đảm của chuẩn: nếu máy bận, luồng nền có thể chậm hơn 0,3 giây. Đó là lý do `detach` khó dùng: bạn không có cách chắc chắn biết việc nền xong (Bài 27 và Bài 29 có cách).

**Thử thay đổi: ở dòng (5) đổi 400 thành 10.** Mình đã chạy ba lần: dòng `luong nen: ...` không bao giờ hiện, chỉ có `main ket thuc`. `main` kết thúc thì cả chương trình dừng, kể cả luồng nền đang dở; không ai chờ nó.

### 5. Ba lỗi hay gặp

**Lỗi 1: hủy `std::thread` còn joinable.** Bỏ `join` và `detach` rồi để `t` chết (ra khỏi phạm vi, hay `main` kết thúc): hàm hủy của `std::thread` gọi `std::terminate` ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)). Lý do thường được nêu: tự `join` ngầm sẽ chờ lâu bất ngờ, tự `detach` ngầm sẽ để lại luồng dùng biến đã chết; chuẩn chọn cách làm lỗi nổ to thay vì lặng lẽ.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>

void viec() { std::cout << "luong chay\n"; }

int main() {
    std::thread t(viec);       // t còn joinable...
    std::cout << "main sap ket thuc\n";
    return 0;                  // ...nhưng không join, không detach: ~thread gọi std::terminate
}
```

Mình đã chạy: chương trình in `terminate called without an active exception` và thoát với mã 134 (bị hủy bằng `abort`, tức 128 + 6, 6 là số tín hiệu abort). Khi chạy qua ống (pipe), mình không thấy dòng nào do chương trình tự in, vì đầu ra bị đệm và `abort` không xả bộ đệm; đừng dựa vào việc có thấy hay không.

**Lỗi 2: luồng `detach` cầm tham chiếu tới biến cục bộ đã chết.** Lambda `[&so]` chỉ cầm tham chiếu ([Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md)). Nếu hàm `khoiDong` (hàm đã tạo luồng) kết thúc trước khi luồng dùng `so`, thì `so` đã chết và đây là hành vi không xác định ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)):

```cpp
// bo-qua-kiem-tra
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

void khoiDong() {
    std::vector<int> so = {1, 2, 3};
    std::thread t([&so] {                                             // (1) giữ tham chiếu tới `so`
        std::this_thread::sleep_for(std::chrono::milliseconds(100));  // (2) chạy muộn
        std::cout << "luong doc so[0] = " << so[0] << "\n";           // (3) so đã chết từ lâu
    });
    t.detach();                                                       // (4) rồi khoiDong kết thúc
}

int main() {
    khoiDong();
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
    return 0;
}
```

Mình đã chạy: lần thường in một số rác khác nhau mỗi lần (ba lần ra `941067184`, `2115781296`, `-827094560`). Với `-fsanitize=address`, ASan báo `stack-buffer-overflow` ("READ of size 8", trong luồng phụ, dòng (3)); vùng stack của `khoiDong` đã được một lệnh gọi khác dùng lại. Với `-fsanitize=thread`, chương trình sập ngay vì đọc địa chỉ rác.

Cách sửa: bản sao (`[so]`), hoặc `join` trước khi hàm kết thúc.

**Lỗi 3: ngoại lệ thoát khỏi hàm của luồng.** Ngoại lệ không được `catch` bên trong hàm của luồng không bay về luồng tạo ra nó; nó gọi `std::terminate` và dừng cả chương trình. Mình đã chạy một luồng mà hàm của nó chỉ có `throw 1;`: g++ in `terminate called after throwing an instance of 'int'` và thoát với mã 134, y như ngoại lệ không bắt ở `main` ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)). Muốn xử lý, `try`/`catch` ngay trong hàm của luồng; Bài 29 có cách chuyển ngoại lệ sang luồng khác. (Go: goroutine `panic` mà không `recover` cũng làm cả chương trình chết, mình đã chạy: mã thoát 2.)

### 6. RAII bọc `thread`: luôn được `join`

[Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) dạy: hàm hủy chạy cả khi hàm thoát vì ngoại lệ. Ta dùng đúng ý đó: một lớp nhỏ giữ `std::thread` và `join` nó trong hàm hủy. Hai chi tiết cú pháp trong code dưới (ta dùng `struct` như các bài trước):

- `std::thread` **không sao chép được** (một luồng chỉ có một "tay cầm"), chỉ chuyển bằng `std::move` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)); nên hàm tạo của ta nhận `std::thread` và chuyển vào thành viên, còn việc sao chép ta cấm bằng `= delete` ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)).
- `: luong(std::move(t))` sau hàm tạo là **danh sách khởi tạo**: dựng thành viên `luong` ngay từ `t`, trước khi thân hàm `{}` chạy.

```cpp
#include <iostream>
#include <thread>
#include <utility>

long long tong = 0;

void congDon(int n) {
    for (int i = 1; i <= n; ++i) tong += i;
}

struct LuongTuJoin {
    LuongTuJoin(std::thread t) : luong(std::move(t)) {}   // (1) nhận thread, giữ làm thành viên
    ~LuongTuJoin() {                                      // (2) hàm hủy: chờ luồng xong
        if (luong.joinable()) luong.join();
    }
    LuongTuJoin(const LuongTuJoin&) = delete;             // (3) cấm sao chép
    LuongTuJoin& operator=(const LuongTuJoin&) = delete;
    std::thread luong;                                    // thành viên: cái luồng được giữ
};

void viecDoDang() {
    std::thread t(congDon, 100);
    LuongTuJoin g(std::move(t));                          // (4) từ đây g lo việc join
    throw 7;                                              // (5) thoát hàm sớm bằng ngoại lệ
}

int main() {
    try {
        viecDoDang();
    } catch (int ma) {
        std::cout << "bat duoc ma " << ma << "\n";       // (6)
    }
    std::cout << "tong = " << tong << "\n";               // (7) luồng đã được join trong ~LuongTuJoin
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái luồng |
|---|---|---|
| (4) | `t` trao luồng cho `g`; `t` rỗng, `g.luong` giữ luồng | `g.luong` joinable |
| (5) | `throw`: `viecDoDang` thoát sớm, bắt đầu tháo ngăn xếp | luồng vẫn có thể đang chạy |
| (2) | Hàm hủy của `g` chạy (như mọi biến cục bộ): `joinable` đúng nên `join`, chờ luồng xong | luồng đã xong |
| (6)-(7) | `catch` nhận `ma = 7` và in ra; `tong` đã là 5050 vì luồng được join | |

**Kết quả khi chạy:**

```text
bat duoc ma 7
tong = 5050
```

**Thử thay đổi: bỏ `LuongTuJoin g(std::move(t));` và để `t` trần, gọi `t.join()` sau `throw`.** Mình đã chạy: `throw` thoát hàm trước khi tới `t.join()`, nên `t` bị hủy khi còn joinable; chương trình in `terminate called without an active exception` (mã 134) và không bao giờ tới `catch` để in `bat duoc ma`. Lớp bọc cứu đúng chỗ này.

### 7. Vài tiện ích: số lõi và `sleep_for`

- `std::thread::hardware_concurrency()` trả một `unsigned` là **gợi ý** về số luồng phần cứng chạy cùng lúc (chuẩn cho phép trả `0` nếu không biết).
- `std::this_thread::sleep_for(d)` làm luồng này ngủ **ít nhất** khoảng `d`.
- `std::chrono::steady_clock::now()` là thời điểm hiện tại của đồng hồ chạy đều (không nhảy khi ai đó chỉnh giờ).

Hai thời điểm trừ nhau cho ra một khoảng thời gian, và `std::chrono::duration_cast<std::chrono::milliseconds>(khoang).count()` đổi khoảng đó thành số nguyên mili giây.

```cpp
#include <chrono>
#include <iostream>
#include <thread>

int main() {
    unsigned lop = std::thread::hardware_concurrency();      // (1) gợi ý số luồng chạy song song được
    std::cout << "hardware_concurrency = " << lop << "\n";

    auto bat = std::chrono::steady_clock::now();             // (2) đồng hồ chạy đều, không nhảy
    std::this_thread::sleep_for(std::chrono::milliseconds(50));   // (3) luồng này ngủ ít nhất 50 ms
    auto troi = std::chrono::steady_clock::now() - bat;      // (4) khoảng thời gian đã trôi
    long long ms = std::chrono::duration_cast<std::chrono::milliseconds>(troi).count();   // (5)
    std::cout << "ngu it nhat 50 ms? " << (ms >= 50) << "\n";
    return 0;
}
```

**Kết quả khi chạy:**

```text
hardware_concurrency = 8
ngu it nhat 50 ms? 1
```

Dòng đầu là của máy mình (8 luồng phần cứng); máy bạn in số khác.

## 💻 Ví dụ code

### Chia việc cho bốn luồng bằng lambda

Bài toán: cộng 1000 số `1..1000` nằm trong một `vector` (ở heap). Ta chia làm bốn đoạn 250 phần tử, mỗi luồng cộng một đoạn và ghi tổng phần vào **ô riêng** của nó trong `tongPhan`, rồi luồng chính cộng bốn tổng phần. Hai luồng không bao giờ ghi cùng một ô, và `so` chỉ được đọc, nên không có tranh chấp.

Ba thứ mới trong code:

- `std::vector<std::thread>` giữ nhiều luồng; `emplace_back(lambda)` dựng một `std::thread` từ lambda ngay trong ô cuối ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)). Viết `push_back(t)` sẽ cần sao chép `thread`, mà nó không sao chép được.
- Lambda `[&so, &tongPhan, k]` bắt `so` và `tongPhan` theo tham chiếu, còn `k` theo bản sao (mỗi luồng cần `k` của riêng mình).
- Vòng `for (std::thread& t : cacLuong)` dùng `&` để **không sao chép** `thread`.

```cpp
#include <iostream>
#include <thread>
#include <vector>

int main() {
    std::vector<int> so(1000);
    for (int i = 0; i < 1000; ++i) so[i] = i + 1;           // 1, 2, ..., 1000 (nằm ở heap)

    const int soLuong = 4;
    std::vector<long long> tongPhan(soLuong, 0);            // mỗi luồng ghi vào ô riêng của nó
    std::vector<std::thread> cacLuong;

    for (int k = 0; k < soLuong; ++k) {
        cacLuong.emplace_back([&so, &tongPhan, k] {         // (1) lambda là hàm của luồng
            int dau = k * 250;                              // (2) biến cục bộ: stack riêng của luồng
            int cuoi = dau + 250;
            long long tongDoan = 0;
            for (int i = dau; i < cuoi; ++i) tongDoan += so[i];    // (3) chỉ ĐỌC vector chung
            tongPhan[k] = tongDoan;                         // (4) chỉ GHI ô số k
        });
    }
    for (std::thread& t : cacLuong) t.join();               // (5) chờ cả bốn luồng

    long long tong = 0;
    for (int k = 0; k < soLuong; ++k) {
        std::cout << "phan " << k << ": " << tongPhan[k] << "\n";
    }
    for (long long x : tongPhan) tong += x;
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Mỗi vòng `k` dựng một luồng chạy lambda với bản sao riêng của `k` | 4 luồng phụ, mỗi luồng có `k` riêng |
| (2) | Luồng `k` tính đoạn `[k*250, k*250+250)` trong biến cục bộ của nó | `dau`, `cuoi`, `tongDoan` nằm ở stack của từng luồng |
| (3) | Đọc `so[i]` của vector chung | `so` ở heap, chỉ đọc |
| (4) | Ghi tổng vào `tongPhan[k]` | mỗi luồng một ô khác nhau |
| (5) | Luồng chính `join` từng luồng; sau đó `tongPhan` đầy đủ | |

**Kết quả khi chạy:**

```text
phan 0: 31375
phan 1: 93875
phan 2: 156375
phan 3: 218875
tong = 500500
```

Cả bốn dòng `phan` và `tong` in từ luồng chính **sau** `join`, nên thứ tự và giá trị ổn định. Nếu để từng luồng tự in, thứ tự dòng do hệ điều hành quyết định và đổi theo lần chạy (có thể cả chen vào giữa một dòng). Mình cũng chạy với `-fsanitize=thread`: không có cảnh báo.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Process và thread khác nhau thế nào?"
    Tiến trình là chương trình đang chạy với không gian bộ nhớ riêng, được hệ điều hành cô lập. Luồng là một dòng thực thi bên trong tiến trình: mỗi luồng có stack và trạng thái chạy riêng, nhưng cùng chia sẻ heap và biến toàn cục. Vì chung bộ nhớ nên luồng giao tiếp rẻ và tạo rẻ hơn, nhưng một lỗi bộ nhớ làm chết cả tiến trình và việc cùng sửa dữ liệu chung cần đồng bộ. Giữa các tiến trình phải dùng cơ chế do hệ điều hành cung cấp.

??? question "`join` khác `detach` thế nào? Khi nào dùng cái nào?"
    `join` chặn luồng gọi cho tới khi luồng kia kết thúc; sau đó kết quả của luồng kia đọc được an toàn. `detach` thả luồng chạy nền độc lập và không còn cách chờ hay biết khi nào nó xong; nếu `main` kết thúc, luồng nền bị bỏ giữa chừng. Mọi `std::thread` joinable phải được `join` hoặc `detach` trước khi bị hủy, nếu không `std::terminate`. Mặc định hãy `join` (kèm lớp RAII); chỉ `detach` việc nền thật sự độc lập và chỉ dùng bản sao dữ liệu.

??? question "Vì sao tham số truyền cho `std::thread` bị sao chép? Truyền tham chiếu thế nào?"
    Luồng mới có thể chạy sau khi hàm gọi đã kết thúc, khi biến gốc đã chết; nếu luồng giữ tham chiếu thì sẽ trỏ vào vùng đã dọn. Vì vậy `std::thread` chép đối số vào bộ nhớ riêng của luồng rồi đưa bản chép cho hàm, nên hàm nhận `T&` với đối số thường là lỗi biên dịch. Muốn tham chiếu thật thì dùng `std::ref(x)` hoặc lambda `[&x]`, và tự bảo đảm `x` sống lâu hơn luồng. Kiểu chỉ chuyển được như `unique_ptr` thì dùng `std::move`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên `join`/`detach`, hay để ngoại lệ bỏ qua `join`"
    Hủy `std::thread` còn joinable gọi `std::terminate` (mình đã chạy: mã 134). Hai nguồn hay gặp là quên hẳn, và gọi `join` ở cuối hàm trong khi giữa chừng có `return` sớm hay `throw`. Sửa: bọc luồng bằng lớp RAII như mục 6.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="24" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Hai luồng của cùng một tiến trình chia sẻ và tách biệt thứ gì?

- Chung heap và biến toàn cục; mỗi luồng có stack riêng
- Dùng chung stack và heap; mỗi luồng có biến toàn cục riêng
- Mỗi luồng có heap riêng; chỉ dùng chung các biến cục bộ
- Không chung gì cả, giống hai chương trình khác nhau

<p class="giai-thich" markdown>Mọi luồng của một tiến trình cùng thấy một heap và các biến toàn cục, nhưng mỗi luồng cần stack riêng để chứa biến cục bộ và các lời gọi hàm đang dở của nó. Chung stack sẽ làm biến cục bộ của luồng này đè lên của luồng kia. Còn chương trình khác nhau mới là tiến trình khác nhau, không phải luồng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Đọc đoạn sau. Nó in ra gì?

```text
void tang(int x) { x += 100; }
int n = 1;
std::thread t(tang, n);
t.join();
std::cout << n;
```

- `101`, vì `n` được truyền cho luồng như cho hàm thường
- `1`, vì luồng chỉ nhận bản sao của `n`
- Không biên dịch được, vì thiếu `std::ref`
- Kết quả không xác định, vì hai luồng cùng sửa `n`

<p class="giai-thich" markdown>Đối số được chép vào bộ nhớ riêng của luồng, nên `tang` cộng 100 vào bản sao và `n` của `main` vẫn là `1`. Thiếu `std::ref` chỉ là lỗi khi hàm nhận `int&`; ở đây hàm nhận `int` theo giá trị nên biên dịch bình thường. Cũng không có tranh chấp: luồng chỉ chạm bản sao của chính nó, còn `n` thì chỉ luồng chính đọc sau `join`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau trong `main`. Khi `main` chạy tới `return 0`, chuyện gì xảy ra?

```text
std::thread t(viec);
std::cout << "xong\n";
return 0;
```

- Luồng được tự động `join` nên chương trình kết thúc êm
- Luồng được tự động `detach` và tiếp tục chạy nền
- Lỗi biên dịch, vì thiếu lời gọi `join`
- `t` bị hủy khi còn joinable nên gọi `std::terminate`

<p class="giai-thich" markdown>Hàm hủy của `std::thread` gọi `std::terminate` nếu luồng vẫn joinable, và chuẩn cố ý không tự `join` hay tự `detach` hộ bạn. Trình biên dịch không kiểm tra chuyện này nên đây không phải lỗi biên dịch; chương trình biên dịch được và chỉ sập lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Điều nào đúng ngay sau khi gọi `t.detach()`?

- Luồng bị hủy ngay, hàm của nó không chạy tiếp
- Luồng chạy tiếp, nhưng `main` vẫn phải `join` nó trước khi thoát
- `t.joinable()` là `false` và không còn cách chờ luồng đó
- Gọi `t.join()` về sau vẫn chờ được luồng nền

<p class="giai-thich" markdown>`detach` cắt liên hệ giữa đối tượng `t` và luồng: `t` hết joinable, còn luồng tự chạy tới khi xong rồi tự dọn. Vì vậy không còn gì để `join`, và gọi `join` trên `t` lúc này là lỗi. Luồng cũng không bị dừng: nó chỉ chết sớm khi cả chương trình kết thúc.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Vì sao `std::thread` mặc định sao chép đối số vào bộ nhớ riêng của luồng mới?

- Vì hàm của luồng không được phép nhận tham chiếu trong mọi trường hợp
- Vì luồng có thể chạy khi hàm gọi đã xong, lúc biến gốc đã chết
- Vì sao chép luôn nhanh hơn tham chiếu khi có nhiều luồng
- Vì hệ điều hành cấm hai luồng cùng nhìn một vùng nhớ

<p class="giai-thich" markdown>Luồng mới có thể bắt đầu chạy rất muộn; nếu nó giữ tham chiếu tới biến cục bộ của hàm đã kết thúc thì đọc vào vùng đã dọn. Tham chiếu vẫn truyền được khi bạn chủ động viết `std::ref`. Tốc độ không phải lý do, và luồng cùng tiến trình vốn chung heap và biến toàn cục.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn sau, với `nhan` là hàm nhận một `std::unique_ptr<int>` theo giá trị. Dòng cuối in gì?

```text
auto p = std::make_unique<int>(7);
std::thread t(nhan, std::move(p));
t.join();
std::cout << (p == nullptr);
```

- Không biên dịch được, vì `unique_ptr` không truyền cho luồng được
- `0`, vì `p` vẫn giữ số `7` sau khi luồng chạy xong
- Không xác định, vì `p` bị cả hai luồng dùng
- `1`, vì `std::move` đã trao quyền sở hữu cho luồng

<p class="giai-thich" markdown>`std::move(p)` cho phép luồng lấy quyền sở hữu, và `unique_ptr` đã bị lấy đi thì rỗng, nên `p == nullptr` đúng và in `1`. Truyền vẫn được vì `unique_ptr` chuyển được dù không sao chép được. Không có tranh chấp: sau khi trao tay thì `main` không còn dùng `p` vào việc gì khác.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Đọc đoạn sau, với `LuongTuJoin` là lớp bọc ở mục 6 (`join` trong hàm hủy). Ngoại lệ của `f` được `catch` ở hàm gọi `f`. Khi `f` thoát vì ngoại lệ, luồng ra sao?

```text
void f() {
    std::thread t(viec);
    LuongTuJoin g(std::move(t));
    throw 1;
}
```

- Hàm hủy của `g` chạy lúc tháo ngăn xếp và `join` luồng, nên không có `terminate`
- Chương trình gọi `std::terminate`, vì ngoại lệ được ném khi còn luồng chạy
- Luồng bị bỏ lại chạy nền, vì hàm thoát sớm nên không ai `join` nó
- Luồng bị dừng ngay mà không chờ, vì ngoại lệ hủy mọi luồng của hàm

<p class="giai-thich" markdown>Biến cục bộ `g` vẫn được hủy khi hàm thoát bằng ngoại lệ, và hàm hủy của nó chờ luồng xong; đây đúng là lợi ích của RAII ở Bài 08. Không có điều nào khác tự xảy ra: ngoại lệ không tự dừng luồng, cũng không tự `detach` nó. `terminate` chỉ gọi nếu `std::thread` bị hủy lúc còn joinable, mà ở đây `g` đã `join` trước đó. Ngoại lệ được `catch` ở nơi gọi nên không rơi vào trường hợp không ai bắt.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 8.** Một hàm chạy trong luồng phụ ném ngoại lệ và không có `catch` nào bên trong hàm đó. Chuyện gì xảy ra?

- Ngoại lệ bay về `try`/`catch` ở luồng chính nơi đã tạo luồng
- Luồng phụ kết thúc, ngoại lệ bị bỏ, chương trình chạy tiếp
- Chương trình gọi `std::terminate` và dừng cả chương trình
- Ngoại lệ được cất lại và `join` sẽ ném lại ở luồng chính

<p class="giai-thich" markdown>Ngoại lệ không được bắt ngay trong hàm của luồng thì thoát khỏi hàm đó và `std::terminate` được gọi, dừng mọi luồng. Ngăn xếp của mỗi luồng riêng, nên `catch` ở luồng chính không thể bắt thứ ném ở luồng khác. Cũng không có nơi nào âm thầm nuốt hay cất ngoại lệ; việc chuyển ngoại lệ sang luồng khác cần cơ chế riêng mà Bài 29 mới dạy.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Luồng** là dòng chạy lệnh trong tiến trình: dùng chung heap và biến toàn cục, mỗi luồng có stack riêng; tiến trình có bộ nhớ riêng; goroutine của Go là thứ nhẹ do runtime Go lập lịch, không phải luồng hệ điều hành, và C++ chuẩn không có channel.
2. `std::thread t(f, đối số...)` (`#include <thread>`, biên dịch kèm `-pthread`) tạo luồng chạy `f`; lambda cũng dùng được; `t.join()` chờ luồng xong và làm kết quả của nó đọc an toàn (như `wg.Wait()` của Go); `detach` thả luồng nền, hiếm khi nên dùng.
3. Đối số mặc định **bị sao chép** vào luồng (vì luồng có thể chạy khi biến gốc đã chết); muốn tham chiếu dùng `std::ref(x)` hoặc `[&x]` và tự bảo đảm `x` sống đủ lâu; `unique_ptr` truyền bằng `std::move`.
4. Ba lỗi: hủy `std::thread` còn joinable gọi `std::terminate` (mã 134); luồng `detach` cầm tham chiếu tới biến cục bộ đã chết là hành vi không xác định; ngoại lệ thoát khỏi hàm của luồng cũng `std::terminate`.
5. Bọc luồng trong lớp RAII `join` ở hàm hủy (nối [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md); C++20 có `std::jthread`); `hardware_concurrency()` chỉ là gợi ý, `sleep_for` ngủ ít nhất khoảng cho trước, và thứ tự in giữa các luồng không ổn định nên hãy `join` rồi in từ luồng chính.
