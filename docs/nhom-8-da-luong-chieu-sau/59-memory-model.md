# Bài 59 — Memory model: happens-before, acquire/release và vì sao volatile không cứu được

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích vì sao **thứ tự bạn viết code không phải thứ tự luồng khác thấy** (trình biên dịch và CPU đều được phép sắp xếp lại), và nói đúng **happens-before** là gì: một bảo đảm về *ai thấy gì của ai*, không phải chuyện đồng hồ.
    - Viết đúng mẫu công bố dữ liệu "ghi dữ liệu, rồi bật cờ `ready`" bằng `memory_order_release` và `memory_order_acquire` (chạy thật, TSan sạch); biết `seq_cst` là mặc định an toàn, và `relaxed` chỉ dành cho bộ đếm độc lập, vì sao dùng nó để công bố dữ liệu là sai.
    - Thấy **tận mắt trên máy này** một kiểu sắp xếp lại thật (ghi rồi đọc), biết vì sao x86 "gần như không reorder" vẫn không cứu code sai.
    - Nhận ra mutex, `join`, `call_once` đã có acquire/release sẵn; biết `volatile` **không** tạo happens-before; giải thích vì sao double-checked locking kinh điển sai và ba cách làm đúng (`static` cục bộ, `std::call_once`, atomic).

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`, `lock_guard`, TSan), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, `load`/`store`, cờ dừng, `volatile`, `memory_order` mới nhắc tên), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định, sanitizer), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (biến `static` cục bộ), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (lambda), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp**. Anh bếp trưởng thái xong hành, đặt lên thớt rồi **treo biển "hành đã sẵn sàng"** lên bảng treo tường. Chị bếp phó đứng chờ, thấy biển thì đi lấy hành. Ai cũng thấy chuyện này hiển nhiên: có biển thì phải có hành.

Nhưng bảng treo tường không tức thời. Mỗi đầu bếp có **sổ tay riêng** và chỉ chép lên bảng chung khi rảnh, theo thứ tự **họ thấy tiện**, không nhất thiết theo thứ tự ghi trong sổ. Có thể biển "sẵn sàng" lên bảng **trước** khi hành lên thớt, và chị bếp phó bước tới thấy thớt trống. Bài này dạy cách ra lệnh: "chép hành lên bảng **trước** biển, và ai thấy biển thì phải thấy cả hành".

!!! info "Chỗ nào ví von sổ tay và bảng không còn đúng?"
    Máy thật không có một bảng chung duy nhất mà là nhiều tầng đệm (bộ đệm ghi, cache là vùng nhớ nhỏ và nhanh nằm sát từng lõi) và một giao thức giữ cho chúng nhất quán. Bảng và sổ tay chỉ để hình dung: **thứ ta ghi và thứ người khác thấy có thể lệch thứ tự**. Ví von cũng không có trình biên dịch, một "người chép thuê" đổi thứ tự câu lệnh trước khi chương trình chạy.

## 📖 Giải thích

### 1. Vì sao thứ tự bị đảo: trình biên dịch và CPU

Hai chỗ đảo thứ tự, độc lập nhau. **Trình biên dịch** (compiler, chương trình dịch code C++ ra lệnh máy, [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md)) được đổi chỗ, bỏ bớt, gom lại các lệnh miễn là kết quả **trong một luồng** không đổi. [Bài 28](../nhom-3-da-luong/28-atomic.md) đã cho thấy một ca: `-O2` đọc cờ `bool` đúng một lần rồi lặp mãi, vì trong một luồng không ai ghi cờ lúc đang lặp.

**CPU** cũng đảo, bằng phần cứng. Lệnh ghi không đi thẳng ra bộ nhớ: nó nằm trong một **hàng chờ ghi** (store buffer) của lõi rồi mới ra sau. Trong lúc đó lệnh đọc đứng sau có thể chạy xong trước. Với luồng khác, như thể "đọc" xảy ra trước "ghi". Mỗi dòng CPU có luật riêng: x86-64 gần như chỉ đảo kiểu *ghi rồi đọc*; ARM và vài CPU khác đảo nhiều kiểu hơn.

Ai giữ cho code đúng? **Memory model** (mô hình bộ nhớ), phần của chuẩn C++ nói một luồng được **thấy** gì từ việc ghi của luồng khác và khi nào. Bạn chỉ cần tuân luật của chuẩn; trình biên dịch lo dịch ra **rào chắn** (lệnh máy ép thứ tự) phù hợp cho từng CPU.

Vì thế "máy tôi là x86, nó mạnh, không reorder" là lập luận sai hai lần: trình biên dịch vẫn đảo trên mọi máy, và chính x86 vẫn đảo kiểu ghi-rồi-đọc (mục 6 cho thấy). Code chỉ đúng nhờ may của một CPU là code có data race.

### 2. Happens-before: ai thấy gì của ai

Gọi hai thao tác là A và B. **A happens-before B** (A xảy ra-trước B) nghĩa là: B được bảo đảm **thấy mọi kết quả** của A. Đây không phải chuyện A chạy sớm hơn theo đồng hồ. Hai luồng ghi và đọc cách nhau một giờ mà không có quan hệ nào giữa chúng thì chuẩn vẫn không hứa người đọc thấy gì.

Quan hệ này đến từ ba nguồn. Mỗi mối nối hai luồng như vậy, mình gọi là một **cầu**:

| Nguồn | Nội dung | Ví von bảng |
|---|---|---|
| Cùng một luồng | Dòng trên happens-before dòng dưới (theo thứ tự trong chương trình) | Mỗi đầu bếp tự nhớ việc mình đã làm |
| Đồng bộ giữa hai luồng | Ghi **release** vào một atomic mà luồng kia **acquire** và đọc được giá trị do chính lần ghi đó để lại (mục 4); `unlock` rồi `lock` cùng mutex; kết thúc luồng rồi `join` | Biển "sẵn sàng" và người nhìn thấy biển |
| Bắc cầu | A happens-before B và B happens-before C thì A happens-before C | Hành lên thớt, biển lên bảng, chị phó thấy biển: chị phó phải thấy hành |

Nếu hai thao tác **xung đột** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md): cùng ô nhớ, có một bên ghi) mà **không** có quan hệ happens-before nào giữa chúng, đó chính là data race, tức hành vi không xác định. Memory model là cách chuẩn nói data race theo ngôn ngữ chính xác.

### 3. Mẫu công bố: ghi dữ liệu rồi bật cờ

Bài toán: luồng viết ghi `duLieu = 42` rồi bật cờ `sanSang`. Luồng đọc chờ cờ rồi đọc `duLieu`. `duLieu` là `int` thường; chỉ cờ là `atomic`. Bản đầu dùng thứ tự mặc định (`seq_cst`), như [Bài 28](../nhom-3-da-luong/28-atomic.md).

```cpp
#include <atomic>
#include <iostream>
#include <thread>

int duLieu = 0;                            // (1) dữ liệu thường: KHÔNG phải atomic
std::atomic<bool> sanSang{false};          // (2) cờ báo "đã niêm yết xong"

void nguoiViet() {
    duLieu = 42;                           // (3) ghi dữ liệu trước
    sanSang.store(true);                   // (4) rồi mới bật cờ (mặc định seq_cst)
}

void nguoiDoc() {
    while (!sanSang.load()) {              // (5) chờ tới khi thấy cờ
    }
    std::cout << "doc duoc " << duLieu << "\n";   // (6) đọc dữ liệu thường
}

int main() {
    std::thread doc(nguoiDoc);
    std::thread viet(nguoiViet);
    viet.join();
    doc.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Quan hệ |
|---|---|---|
| (3) | Luồng viết ghi `duLieu = 42` | |
| (4) | Luồng viết bật cờ; (3) nằm trên (4) cùng luồng | (3) happens-before (4) |
| (5) | Luồng đọc lặp tới khi `load()` thấy `true`, tức đọc đúng giá trị mà (4) ghi | (4) nối sang (5): một **cầu** |
| (6) | Đọc `duLieu` sau (5): theo bắc cầu (3), (4), (5), (6) nối nhau, nên thấy 42 và **không phải** data race | luôn 42 |

**Kết quả khi chạy** (g++ 11, x86-64; mọi lần như nhau; TSan sạch ở `-O0` và `-O2`):

```text
doc duoc 42
```

Chuẩn bảo đảm dòng này in `42`, không chỉ "thường thường". Cờ là cầu: không có cầu thì `duLieu` hai luồng đụng nhau trần trụi.

### 4. `acquire` và `release`: đúng vừa đủ, và năm mức tất cả

`seq_cst` đúng nhưng đòi nhiều hơn mẫu này cần. Mẫu công bố chỉ cần hai nửa: luồng viết **đóng dấu** (mọi thứ ghi trước dòng này phải lên bảng trước), luồng đọc **nhìn dấu** (thấy dấu thì mọi thứ trước dấu chắc chắn đọc được). Đó là `release` và `acquire`.

```cpp
#include <atomic>
#include <iostream>
#include <thread>

int duLieu = 0;
std::atomic<bool> sanSang{false};

void nguoiViet() {
    duLieu = 42;                                           // (1)
    sanSang.store(true, std::memory_order_release);        // (2) đóng dấu: (1) không được trôi xuống dưới dòng này
}

void nguoiDoc() {
    while (!sanSang.load(std::memory_order_acquire)) {     // (3) nhìn dấu
    }
    std::cout << "doc duoc " << duLieu << "\n";            // (4) không được trôi lên trên (3); thấy 42
}

int main() {
    std::thread doc(nguoiDoc);
    std::thread viet(nguoiViet);
    viet.join();
    doc.join();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bảng lúc này |
|---|---|---|
| (1) | Ghi `duLieu = 42` (có thể còn nằm trong "sổ tay" luồng viết) | chưa chắc lên bảng |
| (2) | `release`: ép (1) phải hiện lên **trước hoặc cùng** lúc cờ bật; không lệnh ghi/đọc trước (2) được dời ra sau nó | hành lên rồi mới tới biển |
| (3) | `acquire`: nếu đọc được `true` do (2) ghi, mọi thứ luồng viết đã ghi trước (2) giờ hiện ra; không lệnh nào sau (3) được dời lên trước nó | thấy biển, thấy hành |
| (4) | Đọc `duLieu` an toàn | 42 |

**Kết quả khi chạy** (như nhau mọi lần; TSan sạch ở `-O0` và `-O2`):

```text
doc duoc 42
```

**Thử thay đổi: bỏ một nửa của cặp.** Mình chạy ba biến thể, `-O2` với TSan:

- Đổi `release` thành `relaxed` (còn `acquire` ở đọc): TSan báo `data race` trên `duLieu`, mã thoát 66.
- Giữ `release` nhưng đổi `acquire` thành `relaxed`: cũng báo `data race`, mã 66. Cầu cần **cả hai đầu**.
- Cả hai `relaxed`: cùng báo `data race` ở `duLieu` (mục 5 nói rõ vì sao).

Cả ba vẫn in `doc duoc 42` trên máy mình. Đừng đọc đó là "đúng": chuẩn không hứa, và TSan đã chỉ ra cầu bị đứt.

**Năm mức `memory_order`.** Tất cả đều làm thao tác **nguyên tử**; chúng khác nhau ở chỗ ràng buộc thứ tự với việc khác:

| Mức | Bảo đảm | Dùng khi |
|---|---|---|
| `relaxed` | Chỉ nguyên tử và thứ tự riêng từng biến; **không** ràng buộc với biến khác | Bộ đếm độc lập, đọc kết quả sau `join` |
| `release` (cho `store`) | Mọi thứ ghi trước nó hiện ra trước nó | Đầu "công bố" của cầu |
| `acquire` (cho `load`) | Thấy giá trị do release ghi thì thấy mọi thứ trước release đó | Đầu "nhận" của cầu |
| `acq_rel` | Cả hai, cho thao tác đọc-sửa-ghi (`fetch_add`, `exchange`) | Lấy và đặt trong một nhịp |
| `seq_cst` | Mọi thứ trên cộng thêm **một thứ tự chung** của mọi thao tác `seq_cst` mà luồng nào cũng thấy giống nhau | Mặc định; khi không chắc |

Cầu chỉ nối khi `load(acquire)` đọc đúng giá trị do `release` để lại, hoặc do các thao tác đọc-sửa-ghi (như `fetch_add`) nối ngay sau nó (gọi là *release sequence*); ở bài này mỗi cờ chỉ được ghi một lần nên khỏi bận tâm.

Còn `memory_order_consume`: chỉ nhắc tên, đừng dùng (g++ hiện đối xử như `acquire`). `std::atomic_thread_fence` cũng chỉ nhắc tên: một "rào chắn" đứng riêng không gắn với biến nào, hiếm khi cần.

!!! info "Bạn biết Go?"
    Go không cho chọn: mọi thao tác trong `sync/atomic` hành xử như `seq_cst` của C++ (tài liệu `go doc sync/atomic` và mô hình bộ nhớ của Go nói vậy, như [Bài 28](../nhom-3-da-luong/28-atomic.md) đã nhắc). Go tạo happens-before bằng công cụ quen thuộc: gửi vào channel xảy ra-trước khi nhận xong, `Unlock` xảy ra-trước `Lock` kế tiếp, `once.Do(f)` xong thì mọi `Do` thấy `f` đã xong.

    - Mình chạy bản Go của mẫu trên, `duLieu` là `int` thường, cờ `atomic.Bool`: in `doc duoc 42`, `-race` sạch. Đổi cờ thành `bool` thường: `-race` báo `WARNING: DATA RACE` (mã thoát 66). Go cũng không có `volatile`.

### 5. `relaxed`: đúng chỗ và sai chỗ

`relaxed` chỉ đòi atomic làm đúng một việc: thao tác không bị chia cắt. Hợp với **bộ đếm thống kê**: bốn luồng cùng cộng, không ai đọc trước khi tất cả `join`.

```cpp
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

std::atomic<long long> dem{0};             // (1) bộ đếm thống kê: các luồng chỉ cộng

void tang() {
    for (int i = 0; i < 100000; ++i) {
        dem.fetch_add(1, std::memory_order_relaxed);   // (2) relaxed: chỉ cần "cộng không mất"
    }
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) cacLuong.emplace_back(tang);
    for (std::thread& t : cacLuong) t.join();          // (3) join cho luồng chính thấy kết quả cuối
    std::cout << "dem = " << dem.load(std::memory_order_relaxed) << "\n";   // (4)
    return 0;
}
```

**Chạy từng dòng:** (2) mỗi lần cộng là một khối nguyên tử, bốn luồng không làm mất lần cộng của nhau dù không có thứ tự gì giữa chúng; (3) `join` là cầu happens-before (mục 2), nên (4) thấy kết quả cuối.

**Kết quả khi chạy** (mọi lần như nhau; TSan sạch):

```text
dem = 400000
```

Vì sao đúng: bộ đếm **không công bố gì cả**; không ai dựa vào việc "thấy bộ đếm = k nghĩa là thấy việc khác của luồng kia". Vì sao `relaxed` sai khi công bố dữ liệu: đọc cờ `relaxed` không kéo theo việc thấy `duLieu` (mục 4: biến thể cả hai `relaxed` bị TSan báo). **Quy tắc: chưa chứng minh được thì dùng `seq_cst`**; khi biết rõ mình đang xây cầu thì `release`/`acquire`; `relaxed` chỉ khi mọi người chỉ cộng và không ai dựa vào nó để thấy việc khác.

### 6. Thấy tận mắt trên máy này: ghi rồi đọc bị đảo

Mình không phá được mẫu ở mục 3 bằng cách chạy thử trên x86, vì x86 giữ thứ tự ghi-ghi và đọc-đọc. Nhưng x86 **đảo ghi rồi đọc**, nên có một thí nghiệm nhìn được. Mỗi vòng: luồng A ghi `x = 1` rồi đọc `y`; luồng B ghi `y = 1` rồi đọc `x`; cả hai bắt đầu gần như cùng lúc. Nếu mọi thứ xảy ra theo một thứ tự chung thì ít nhất một luồng phải thấy `1` của bên kia. Cả hai thấy `0` nghĩa là hai lệnh ghi còn nằm trong hàng chờ trong khi lệnh đọc chạy.

```cpp
#include <atomic>
#include <iostream>
#include <thread>

const int SO_VONG = 20000;
const std::memory_order GHI = std::memory_order_seq_cst;   // (1) thử đổi thành relaxed
const std::memory_order DOC = std::memory_order_seq_cst;

std::atomic<int> x{0}, y{0};
int r1 = 0, r2 = 0;                        // kết quả mỗi vòng; chỉ đọc sau khi luồng báo xong
std::atomic<int> batDau{0};                // main tăng số này để phát lệnh "chạy vòng mới"
std::atomic<int> xongA{0}, xongB{0};

void luongA() {
    for (int v = 1; v <= SO_VONG; ++v) {
        while (batDau.load() < v) std::this_thread::yield();   // (2) chờ lệnh chạy vòng v
        x.store(1, GHI);                   // (3) A: viết x, rồi đọc y
        r1 = y.load(DOC);
        xongA.store(v);
    }
}

void luongB() {
    for (int v = 1; v <= SO_VONG; ++v) {
        while (batDau.load() < v) std::this_thread::yield();
        y.store(1, GHI);                   // (4) B: viết y, rồi đọc x
        r2 = x.load(DOC);
        xongB.store(v);
    }
}

int main() {
    std::thread a(luongA), b(luongB);
    int dongThoi = 0;                      // số vòng mà CẢ HAI cùng đọc được 0
    for (int v = 1; v <= SO_VONG; ++v) {
        x.store(0);                        // (5) dọn bảng cho vòng v
        y.store(0);
        batDau.store(v);                   // phát lệnh
        while (xongA.load() < v || xongB.load() < v) std::this_thread::yield();   // (6) chờ cả hai xong
        if (r1 == 0 && r2 == 0) ++dongThoi;
    }
    a.join();
    b.join();
    std::cout << "so vong thay (r1, r2) = (0, 0): " << dongThoi << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (5)(batDau) | `main` dọn `x`, `y` về 0 rồi phát lệnh cho vòng `v` | hai luồng đang chờ ở (2); `yield()` là nhường lõi cho luồng khác thay vì quay vòng đốt CPU |
| (3)(4) | A và B cùng ghi biến của mình rồi đọc biến của bên kia | `r1`, `r2` là `int` thường, ghi một lần mỗi vòng |
| `xongA`/`xongB` | Mỗi luồng báo xong; `main` chờ ở (6), rồi mới đọc `r1`, `r2` | cặp atomic này là cầu, nên đọc `r1`, `r2` không phải data race |
| (6) | `main` đếm vòng có `r1 == 0 && r2 == 0` | với `seq_cst` luôn bằng 0 |

**Kết quả khi chạy** (`seq_cst`, mười lần mỗi mức `-O0` và `-O2`, đều như nhau; TSan sạch):

```text
so vong thay (r1, r2) = (0, 0): 0
```

`0` ở đây được **chuẩn bảo đảm**: `seq_cst` có một thứ tự chung nên "cả hai thấy 0" là không thể (g++ 11 dịch `store` `seq_cst` thành lệnh `xchgl`, một lệnh có rào chắn ngầm). **Thử thay đổi: đổi dòng (1) thành `relaxed`** (cả `GHI` và `DOC`), mình chạy `-O2` mười lần ra (trên 20000 vòng): `152 0 283 131 223 80 186 244 183 917`. Đổi thành `release` (ghi) và `acquire` (đọc): `30 26 60 23 0 150 18 44 33 82`. Cả hai đều cho phép kết quả `(0, 0)`, vì `release`/`acquire` **không** có thứ tự chung; chỉ `seq_cst` có.

Ba điều cần nói thật. Một, con số đổi theo lần chạy, máy và độ bận; **đừng hứa sẽ thấy nó** trên máy bạn (có lần mình thấy `0` ở `relaxed` dù cùng mã). Hai, ở `-O0` cả ba mức đều ra `0` mười lần mình thử, và khi ép chương trình chạy trên **một lõi** (`taskset -c 0`) `relaxed` ở `-O2` cũng ra `0` ba lần: cần hai lõi thật sự chạy song song mới thấy. Ba, lệnh máy của `relaxed` có `store` đứng trước `load` đúng như viết; việc đảo do phần cứng, không do trình biên dịch.

### 7. Mutex, `join` và `volatile`

**Mutex đã có acquire/release.** `unlock()` là một lần `release`, `lock()` kế tiếp của luồng khác là một lần `acquire`; nên mọi thứ ghi trong vùng găng của luồng trước, luồng sau thấy hết. Đây là lý do dữ liệu thường được mutex bảo vệ không cần atomic ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Tương tự `join`: thân luồng xong rồi `join` trả về là một cầu (mục 2).

Mình chạy bản dùng mutex: `duLieu` là `int` thường, `sanSang` là `bool` thường, luồng viết ghi cả hai trong một `lock_guard`, luồng đọc lặp "xin khóa, kiểm `sanSang`, nhả khóa" tới khi thấy `true` rồi in `duLieu`. Kết quả luôn `doc duoc 42`, TSan sạch ở `-O0` và `-O2`: cả hai biến đều thường, vẫn không data race, vì `unlock` của luồng viết và `lock` của luồng đọc là một cặp release/acquire.

**`volatile` không tạo happens-before.** Lấy chương trình mục 3, bỏ `atomic`, đổi cờ thành `volatile bool sanSang = false;`. `volatile` dặn trình biên dịch **đừng bỏ hoặc gộp** các lần đọc ghi biến đó, nhưng nó không nói gì về thứ tự với biến khác và không đồng bộ luồng. Mình chạy: in `doc duoc 42` trên máy này (cả `-O0` và `-O2`), nhưng TSan báo `data race` ở `-O0` lẫn `-O2` (ở `sanSang`: một bên ghi, một bên đọc, không có cầu; và cả ở `duLieu`). Chuẩn: data race là hành vi không xác định, kể cả với `volatile`. Cờ phải là `atomic`.

Đừng nghĩ "`volatile` đi thẳng vào bộ nhớ nên luồng khác thấy ngay": vế đầu chỉ là chuyện trình biên dịch, vế sau chuẩn không bảo đảm. Java khác: `volatile` ở Java **có** happens-before; đừng mang thói quen đó sang C++.

## 💻 Ví dụ code

### Double-checked locking: bản sai kinh điển và ba cách đúng

Bài toán: một đối tượng cấu hình dùng chung, **dựng lúc có người cần đầu tiên**, nhiều luồng cùng gọi `lay()`. Dựng mỗi lần thì tốn, khóa mỗi lần cũng tốn. Cách "khôn" cổ điển: kiểm con trỏ **ngoài khóa** (đa số lần đã dựng xong, khỏi xin khóa), nếu rỗng thì xin khóa, **kiểm lại** rồi dựng. Chính cách này sai:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

struct CauHinh {
    int a;
    CauHinh() : a(7) {}
};

CauHinh* cauHinh = nullptr;                // (1) con trỏ thường, ban đầu rỗng
std::mutex khoa;

CauHinh* lay() {
    if (cauHinh == nullptr) {              // (2) kiểm lần 1: KHÔNG giữ khóa
        std::lock_guard<std::mutex> giu(khoa);
        if (cauHinh == nullptr) {          // (3) kiểm lần 2: có khóa
            cauHinh = new CauHinh();       // (4) tạo và gán
        }
    }
    return cauHinh;
}

int main() {
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([] { std::cout << lay()->a << "\n"; });
    }
    for (std::thread& t : cacLuong) t.join();
    return 0;
}
```

**Chạy từng dòng** (một cách xen kẽ có thể xảy ra)

| Dòng | Luồng A | Luồng B |
|---|---|---|
| (2) | thấy rỗng, xin khóa | |
| (4) | `new` cấp vùng nhớ, ghi `a = 7`, ghi con trỏ `cauHinh` | |
| (2) | | đọc `cauHinh` **không khóa**, thấy khác rỗng, bỏ qua khóa |
| trả về | | `lay()->a`: nhưng không có cầu nào từ việc ghi `a = 7` của A tới B |

Hai chỗ hỏng. Một, ở (2) luồng B **đọc** `cauHinh` trong lúc A **ghi** nó, không có đồng bộ: đã là data race, hành vi không xác định, **dù** thứ tự có đúng. Hai, ghi con trỏ có thể hiện ra trước việc dựng `CauHinh` (trình biên dịch hoặc CPU được phép), nên B có thể thấy con trỏ khác rỗng mà `a` còn rác. Mình chạy: in `7` bốn lần, trên máy này luôn "đúng", không phá được bằng chạy thử. TSan thì báo ngay `data race` (mã 66, cả `-O0` lẫn `-O2`), đúng chỗ (2) đọc `cauHinh` ở luồng B với (4) ghi ở luồng A:

```text
WARNING: ThreadSanitizer: data race
  Read of size 8 at 0x... by thread T2:
    #0 lay() ...
  Previous write of size 8 at 0x... by thread T1 (mutexes: write M11):
    #0 lay() ...
  Location is global 'cauHinh' of size 8 ...
```

Cách đúng, ba cách trong một chương trình. `std::call_once(cờ, hàm)` (`#include <mutex>`) chạy `hàm` đúng một lần cho cả chương trình, `std::once_flag` là cờ nhớ chuyện đó; `reset(p)` của `unique_ptr` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)) cho nó giữ con trỏ `p` mới. Mỗi cách có bộ đếm riêng số lần dựng; tám luồng cùng gọi cả ba.

```cpp
#include <atomic>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

std::atomic<int> soLanTao[3];              // đếm số lần dựng CauHinh của từng cách (0, 1, 2)

struct CauHinh {
    int a;
    explicit CauHinh(int cach) : a(7) { ++soLanTao[cach]; }
};

// Cách 1: biến static cục bộ (C++11 bảo đảm khởi tạo an toàn luồng)
CauHinh& cach1() {
    static CauHinh cauHinh(0);             // (1)
    return cauHinh;
}

// Cách 2: std::call_once
std::once_flag co;
std::unique_ptr<CauHinh> cauHinh2;
CauHinh& cach2() {
    std::call_once(co, [] { cauHinh2.reset(new CauHinh(1)); });   // (2)
    return *cauHinh2;
}

// Cách 3: double-checked locking đúng, bằng atomic acquire/release
std::atomic<CauHinh*> cauHinh3{nullptr};
std::mutex khoa;
CauHinh& cach3() {
    CauHinh* p = cauHinh3.load(std::memory_order_acquire);       // (3) kiểm lần 1: "nhìn dấu"
    if (p == nullptr) {
        std::lock_guard<std::mutex> giu(khoa);
        p = cauHinh3.load(std::memory_order_relaxed);            // (4) kiểm lần 2: đã có khóa lo
        if (p == nullptr) {
            p = new CauHinh(2);
            cauHinh3.store(p, std::memory_order_release);        // (5) công bố: "đóng dấu"
        }
    }
    return *p;
}

int main() {
    std::vector<std::thread> cacLuong;
    std::atomic<int> tong{0};
    for (int k = 0; k < 8; ++k) {
        cacLuong.emplace_back([&tong] {
            tong += cach1().a + cach2().a + cach3().a;
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "tong = " << tong << ", so lan tao: " << soLanTao[0] << " " << soLanTao[1] << " " << soLanTao[2] << "\n";
    delete cauHinh3.load();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Vì sao đúng |
|---|---|---|
| (1) | Luồng đầu chạy qua dòng này dựng `cauHinh`; luồng tới sau **chờ** tới khi dựng xong | chuẩn C++11 bảo đảm: đồng thời vào thì chỉ một luồng dựng, còn lại chờ |
| (2) | `call_once` chạy lambda đúng một lần; mọi lần gọi `call_once` trả về sau khi lambda đã xong | lần dựng xong happens-before mọi lần trả về |
| (3) | Đọc con trỏ bằng `acquire`: thấy khác rỗng thì thấy cả `CauHinh` đã dựng | cầu với (5) |
| (4) | Trong khóa, đọc lại bằng `relaxed` cũng được: mutex đã làm cầu giữa các luồng qua khóa | khóa lo thứ tự |
| (5) | Dựng xong mới `release` con trỏ | "đóng dấu" sau khi hành lên thớt |

**Kết quả khi chạy** (năm lần liền như nhau; TSan sạch ở `-O0` và `-O2`; cũng biên dịch được với `-std=c++20`):

```text
tong = 168, so lan tao: 1 1 1
```

`168 = 8 luồng x 21` (mỗi luồng cộng `7 + 7 + 7`), và mỗi cách dựng đúng **một** lần. Chọn cách nào: **cách 1 mặc định**, ngắn nhất, trình biên dịch tự lo (đối tượng sống tới hết chương trình). Cách 2 khi việc dựng cần tham số hoặc làm lúc nào đó rõ ràng. Cách 3 chỉ khi bạn cần đọc rất nhanh và thật sự hiểu từng dòng; bản acquire/release này đúng, nhưng dễ viết sai.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Memory model là gì? `acquire`/`release` khác `seq_cst` thế nào?"
    Memory model là phần chuẩn C++ nói một luồng được thấy gì từ việc ghi của luồng khác, vì trình biên dịch và CPU đều được sắp xếp lại lệnh. Công cụ chính là **happens-before**: nếu A happens-before B thì B thấy kết quả của A; hai truy cập xung đột không có quan hệ đó là data race. `release` ghi và `acquire` đọc cùng một atomic tạo quan hệ đó: mọi thứ ghi trước `release` được thấy sau `acquire`. `seq_cst` (mặc định) cộng thêm một thứ tự chung của mọi thao tác `seq_cst`; `release`/`acquire` thì không có (mình chạy thí nghiệm ghi-rồi-đọc: `seq_cst` luôn ra `0` trường hợp "cả hai thấy 0", còn `release`/`acquire` hay `relaxed` thì thấy được). Câu nối tiếp: "Khi nào dùng `relaxed`?" Chỉ khi atomic không công bố gì, ví dụ bộ đếm thống kê đọc sau `join`.

??? question "Happens-before có phải là 'xảy ra trước theo thời gian' không?"
    Không. Nó là **quan hệ về điều được thấy**, không phải đồng hồ. Hai thao tác trong hai luồng có thể cách nhau một giờ mà không happens-before nhau, và khi đó chuẩn không hứa người đọc thấy gì. Quan hệ này sinh ra từ thứ tự trong một luồng, từ cặp `release`/`acquire`, từ `unlock` rồi `lock` cùng mutex, từ kết thúc luồng rồi `join`, và bắc cầu qua chúng.

??? question "`volatile bool` làm cờ có được không? Thế trên x86 thì sao?"
    Không. `volatile` của C++ chỉ buộc trình biên dịch giữ các lần đọc ghi; nó không tạo happens-before và không đồng bộ dữ liệu khác, nên ghi dữ liệu rồi bật cờ `volatile` vẫn là data race (mình chạy: TSan báo). Trên x86 mã thường vẫn chạy "đúng", nhưng đó là may: trình biên dịch và các CPU khác vẫn được phép phá, và chuẩn gọi là hành vi không xác định. Cờ phải là `std::atomic`. Khác Java, nơi `volatile` có nghĩa đồng bộ.

??? question "Double-checked locking sai ở đâu? Làm sao cho đúng?"
    Bản kinh điển đọc con trỏ ngoài khóa trong khi luồng khác có thể đang ghi nó: data race. Thêm nữa, việc ghi con trỏ có thể hiện ra trước việc dựng đối tượng, nên luồng đọc thấy con trỏ khác rỗng mà đối tượng chưa xong. Cách đúng: biến `static` cục bộ (C++11 tự an toàn luồng), `std::call_once` với `std::once_flag`, hoặc đổi con trỏ thành `atomic` và công bố bằng `release`, đọc bằng `acquire` ngoài khóa. Nên chọn `static` cục bộ trước; tự viết bản atomic là bước cuối.

??? question "x86 là mô hình bộ nhớ mạnh, vậy tôi có cần quan tâm `memory_order` không?"
    Có. Một, trình biên dịch đảo lệnh trên mọi máy; chỉ `atomic` với thứ tự đúng mới ngăn nó. Hai, ngay x86 vẫn đảo kiểu ghi-rồi-đọc (mình thấy trên máy mình với `relaxed` và `release`/`acquire`). Ba, code chạy trên ARM (điện thoại, máy chủ mới) sẽ gặp nhiều kiểu đảo hơn. Thứ tự đúng là nghĩa vụ của bạn, không phải của một CPU cụ thể.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Công bố dữ liệu bằng cờ `relaxed` hoặc `bool`/`volatile` thường"
    Cờ phải là cầu: ghi cờ bằng `release` (hoặc mặc định `seq_cst`) và đọc bằng `acquire`. `relaxed` hoặc cờ thường không kéo theo việc thấy dữ liệu; TSan báo data race ở dữ liệu. Chạy "đúng" trên máy mình không chứng minh gì.

!!! warning "Lỗi 2: Tự viết double-checked locking với con trỏ thường, và dùng `relaxed` khi chưa chứng minh được"
    Dựng đối tượng dùng chung thì dùng `static` cục bộ hoặc `std::call_once` trước. Còn `relaxed` chỉ dành cho bộ đếm độc lập: chưa chứng minh được cái gì phụ thuộc vào thứ tự thì để `seq_cst`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="59" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Câu nào mô tả đúng "A happens-before B" theo chuẩn C++?

- A chạy sớm hơn B theo đồng hồ, nên B chắc chắn thấy kết quả của A
- A và B nằm cùng một luồng, nên mới có thể có quan hệ này giữa chúng
- B được bảo đảm thấy mọi kết quả của A nhờ đồng bộ hoặc thứ tự nối chúng
- A là lệnh `atomic`, còn B là lệnh thường, thì A luôn happens-before B

<p class="giai-thich" markdown>Happens-before là bảo đảm về điều B **thấy**, đến từ thứ tự trong luồng, từ cặp release/acquire, từ mutex, từ `join`, và bắc cầu. Đồng hồ không nói lên điều đó: hai việc cách nhau cả giờ mà không có cầu thì vẫn không hứa gì, nên ý "sớm hơn theo đồng hồ" sai. Ý "chỉ trong cùng một luồng" cũng sai vì đồng bộ giữa luồng là chỗ quan hệ này hữu ích nhất. Còn loại lệnh (atomic hay thường) tự nó không tạo quan hệ: phải có thứ tự release/acquire thích hợp.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** `duLieu` là `int` thường, `san` là `std::atomic<bool>`, ban đầu `false`. Luồng 2 chỉ in khi `load` thấy `true`. Luồng 2 in gì?

```text
// luồng 1:  duLieu = 5;  san.store(true, std::memory_order_release);
// luồng 2:  if (san.load(std::memory_order_acquire))  print(duLieu);
```

- Luôn in 5, vì release/acquire cùng cờ làm việc ghi `duLieu` được thấy
- Có thể in 0 hoặc 5, vì `duLieu` không phải atomic nên không được bảo đảm
- Luôn in 5 nhưng chỉ trên x86, trên máy khác thì không bảo đảm
- Có data race, vì `duLieu` bị đọc và ghi bởi hai luồng khác nhau

<p class="giai-thich" markdown>Khi luồng 2 thấy `true` do `release` ghi, việc ghi `duLieu = 5` (nằm trước release) happens-before việc đọc `duLieu` (nằm sau acquire), nên in 5 theo chuẩn trên mọi máy. Ý "0 hoặc 5" quên rằng cầu đã bảo đảm thấy. Ý "chỉ trên x86" nhầm giữa chuẩn và phần cứng. Ý có data race sai vì hai truy cập `duLieu` đã có thứ tự happens-before nối chúng: data race là thiếu quan hệ đó chứ không phải hai luồng cùng đụng một biến.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đoạn dưới giống câu trước nhưng cả hai đầu đều `relaxed`. Điều nào đúng theo chuẩn?

```text
// luồng 1:  duLieu = 5;  san.store(true, std::memory_order_relaxed);
// luồng 2:  if (san.load(std::memory_order_relaxed))  print(duLieu);
```

- Luôn in 5, vì cờ đã là `atomic` nên mọi thứ trước nó cũng được thấy
- Có thể in 0 hoặc 5, nhưng chương trình vẫn có nghĩa, chỉ kết quả không chắc
- Luôn in 5 trên x86 vì x86 không đảo lệnh ghi, nên chuẩn bảo đảm trên máy đó
- Là data race trên `duLieu`, nên chuẩn không hứa gì kể cả khi tình cờ in 5

<p class="giai-thich" markdown>`relaxed` làm thao tác nguyên tử nhưng không tạo cầu: việc ghi `duLieu` và việc đọc nó không có happens-before, thế là data race, hành vi không xác định, TSan sẽ báo. Atomic chỉ bảo vệ chính biến của nó, không kéo theo thứ khác nên "luôn in 5" sai. "In 0 hoặc 5 nhưng vẫn có nghĩa" cũng sai: hành vi không xác định không dừng ở chỗ kết quả khó đoán. Còn x86 chỉ là một CPU; chuẩn nói về chương trình, và trình biên dịch vẫn được đảo lệnh.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Luồng A chuẩn bị một mảng 1000 phần tử rồi bật cờ; luồng B thấy cờ thì đọc mảng. Mảng là biến thường. Cặp thứ tự **tối thiểu mà vẫn đúng** cho cờ là?

- `relaxed` ở cả `store` lẫn `load`, vì cờ chỉ là một con số
- `release` ở `store` của A, `acquire` ở `load` của B
- `acquire` ở `store` của A, `release` ở `load` của B
- `release` ở `store` của A, `relaxed` ở `load` của B

<p class="giai-thich" markdown>Cầu cần đủ hai đầu: bên công bố dùng release, bên nhận dùng acquire. `relaxed` cả hai bị TSan báo data race trên mảng. Giữ release mà để phía nhận `relaxed` cũng đứt cầu (mình chạy, TSan báo data race). Hoán ngược thành acquire cho `store` và release cho `load` thì chuẩn không cho phép: acquire chỉ dành cho đọc, release chỉ dành cho ghi.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Hàm `lay()` trả về cấu hình dùng chung, **dựng lúc được gọi lần đầu**, nhiều luồng cùng gọi. Cách nào vừa đơn giản vừa đúng?

- Kiểm `if (p == nullptr)` ngoài khóa, rồi xin khóa và kiểm lại, với `p` là con trỏ thường
- Giống cách trên nhưng khai báo `p` là `volatile`, để mọi luồng đọc được giá trị mới nhất
- Dựng trong biến `static` cục bộ của hàm và trả tham chiếu tới nó
- Dùng `if (p == nullptr) p = new CauHinh();` rồi bọc cả hàm bằng một `try`/`catch`

<p class="giai-thich" markdown>Biến `static` cục bộ được chuẩn C++11 bảo đảm khởi tạo đúng một lần, an toàn luồng: luồng tới sau chờ luồng đầu dựng xong. Cách kiểm hai lần với con trỏ thường là double-checked locking sai: đọc `p` ngoài khóa trong lúc luồng khác ghi là data race. `volatile` không tạo happens-before nên không sửa được lỗi đó. `try`/`catch` chỉ lo ngoại lệ, không đồng bộ gì giữa các luồng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn sau. Điều nào đúng?

```text
volatile bool san = false;   int duLieu = 0;
// luồng 1:  duLieu = 9;  san = true;
// luồng 2:  while (!san) { }   print(duLieu);
```

- Là data race: `volatile` không tạo happens-before, nên luồng 2 chưa chắc thấy 9
- Đúng: `volatile` ép mọi lần đọc ghi đi thẳng vào bộ nhớ, nên luồng 2 luôn thấy 9
- Đúng nếu biên dịch với `-O0`, vì khi đó không có tối ưu để đảo lệnh
- Chỉ sai khi `san` là `volatile` của một kiểu lớn hơn `bool`, như `long`

<p class="giai-thich" markdown>`volatile` của C++ chỉ nói với trình biên dịch giữ các lần đọc ghi chính biến đó; nó không tạo quan hệ với `duLieu` và không đồng bộ luồng, nên đây là data race và là hành vi không xác định (TSan báo ở cả `-O0` lẫn `-O2` khi mình chạy). "Đi thẳng vào bộ nhớ" là cách hình dung sai: luồng khác vẫn có thể thấy các việc ghi lệch thứ tự. `-O0` chỉ tắt tối ưu của trình biên dịch, không đổi luật của chuẩn, còn CPU vẫn đảo. Kích thước kiểu không liên quan.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đồng nghiệp bảo: "Mình công bố dữ liệu bằng cờ `relaxed`, chạy cả triệu lần trên server x86 chưa lần nào sai, vậy là ổn." Bạn nên trả lời thế nào?

- Ổn, vì x86 không đảo thứ tự ghi nên cả triệu lần đúng là bằng chứng
- Ổn nếu thêm `volatile` cho dữ liệu, để nó đi thẳng vào bộ nhớ chính
- Không ổn chỉ khi chạy trên máy nhiều lõi hơn, nên cứ giữ nếu server ít lõi
- Chưa ổn: chạy đúng không chứng minh gì; cần `release`/`acquire`

<p class="giai-thich" markdown>Chuẩn gọi đây là data race, nên "chưa thấy sai" chỉ là may của một CPU, một trình biên dịch và một mức tối ưu: máy khác (ARM), bản biên dịch mới hay `-O` khác vẫn có thể phá. Sửa bằng cầu: `release` khi ghi cờ, `acquire` khi đọc. Ý "x86 không đảo" sai ở hai chỗ: trình biên dịch vẫn đảo, và x86 vẫn đảo ghi-rồi-đọc. `volatile` không thêm quan hệ nào. Số lõi không quyết định tính đúng của chương trình.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Đọc đoạn sau. `x`, `y` là `atomic<int>` ban đầu 0, hai luồng chạy song song. Có thể xảy ra `r1 == 0 && r2 == 0` không?

```text
// luồng A:  x.store(1, ghi);  r1 = y.load(doc);
// luồng B:  y.store(1, ghi);  r2 = x.load(doc);
```

- Không với mọi cặp thứ tự, vì mỗi luồng ghi trước rồi mới đọc
- Có với `release`/`acquire` hoặc `relaxed`; không với `seq_cst`
- Chỉ có với `relaxed`; không với `release`/`acquire`, vì cặp đó đã có cầu
- Có với mọi cặp thứ tự, kể cả `seq_cst`, vì hai luồng chạy song song

<p class="giai-thich" markdown>Chỉ `seq_cst` có một thứ tự chung của mọi thao tác, trong đó ít nhất một luồng phải thấy ghi của luồng kia. `release`/`acquire` và `relaxed` không có thứ tự chung nên cho phép cả hai đọc 0 (mình chạy thấy cả hai). "Ghi trước rồi đọc" chỉ đúng trong một luồng, còn luồng kia có thể thấy lệch thứ tự. Nói không với `release`/`acquire` nhầm rằng cặp này mạnh bằng `seq_cst`. Nói có với mọi cặp thứ tự bỏ qua đúng điều `seq_cst` bảo đảm.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Trình biên dịch và CPU đều được sắp xếp lại lệnh (CPU qua hàng chờ ghi; x86 gần như chỉ đảo ghi-rồi-đọc, ARM đảo nhiều kiểu hơn), nên thứ tự bạn viết không phải thứ tự luồng khác thấy. **Happens-before** là bảo đảm "B thấy mọi kết quả của A", đến từ thứ tự trong luồng, cặp release/acquire, mutex `unlock`→`lock`, `join`, và bắc cầu; không phải chuyện đồng hồ. Hai truy cập xung đột mà thiếu quan hệ này là data race (hành vi không xác định).
2. Mẫu công bố: ghi dữ liệu thường rồi `store(true, release)` cờ atomic; luồng kia `load(acquire)` cờ rồi đọc dữ liệu: luôn thấy 42, TSan sạch. Bỏ **một** đầu của cặp hay cả hai `relaxed` thì TSan báo data race trên dữ liệu (mình chạy). `seq_cst` là mặc định an toàn; năm mức: `relaxed`, `release`, `acquire`, `acq_rel`, `seq_cst`.
3. `relaxed` chỉ cho bộ đếm độc lập đọc sau `join` (ra đúng 400000); dùng nó để công bố dữ liệu là sai. Thí nghiệm ghi-rồi-đọc: `seq_cst` luôn ra 0 trường hợp "cả hai thấy 0", còn `relaxed` và `release`/`acquire` thấy được trên máy mình ở `-O2` (con số đổi theo lần chạy; `-O0` và một lõi thì không thấy): **đừng hứa thấy** reorder, và code đúng không phụ thuộc may đó. Quy tắc: chưa chứng minh được thì `seq_cst`.
4. Mutex và `join` đã có acquire/release nên dữ liệu thường được mutex bảo vệ không cần atomic; `volatile` **không** tạo happens-before (mình chạy: TSan báo data race ở `-O0` lẫn `-O2`), khác Java; Go chỉ có atomic `seq_cst`, channel/mutex/`Once` tạo happens-before. `atomic_thread_fence` và `consume` chỉ cần biết tên.
5. Double-checked locking với con trỏ thường sai (đọc ngoài khóa là data race; ghi con trỏ có thể hiện trước việc dựng đối tượng; TSan báo). Cách đúng: `static` cục bộ (mặc định), `std::call_once` + `std::once_flag`, hoặc con trỏ `atomic` công bố bằng `release` và đọc bằng `acquire` ngoài khóa; mình chạy cả ba: mỗi cách dựng đúng một lần, TSan sạch.
