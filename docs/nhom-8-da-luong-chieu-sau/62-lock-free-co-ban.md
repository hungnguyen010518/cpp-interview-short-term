# Bài 62 — Lock-free cơ bản: compare_exchange, ABA và hàng đợi SPSC

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt ba mức bảo đảm tiến lên (có chặn, lock-free, wait-free) bằng định nghĩa chính xác, và biết `is_lock_free()` của một kiểu atomic là chuyện khác; viết vòng lặp `compare_exchange_weak` và nói được vì sao vòng CAS là lock-free mà chưa phải wait-free.
    - Đọc hiểu ngăn xếp lock-free Treiber, thấy bản "ngây thơ" hỏng thế nào (xóa nút thì use-after-free, không xóa thì rò rỉ), chạy lại **ABA** từng bước và thấy thẻ phiên bản chặn nó; nêu tên hazard pointer và epoch cho bài toán thu hồi bộ nhớ.
    - Tự viết **hàng đợi vòng SPSC** (một luồng ghi, một luồng đọc) bằng hai `atomic<size_t>` với `acquire`/`release`: chạy thật, TSan sạch, đúng thứ tự phần tử và tổng; biết mỗi `acquire`/`release` giữ chỗ nào (đổi đi là TSan báo); `alignas(64)` tách hai chỉ số, đo thật và đọc đúng con số.
    - Nói được khi nào **không** nên viết lock-free, và trả lời "tự viết queue lock-free" ở mức nguyên lý cộng SPSC.

**Bạn cần biết trước:** [Bài 28](../nhom-3-da-luong/28-atomic.md) (`atomic`, `compare_exchange`, `weak`/`strong`, `is_lock_free`, ABA chỉ tên), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `mutex`, TSan), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (false sharing, `alignas(64)`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`, `delete`, use-after-free), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (ASan, hành vi không xác định), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template`), [Bài 13](../nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (`static_assert`, lambda), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (`std::array<T, N>`).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp nhiều đầu bếp**. Muốn đổi món ở đầu băng chuyền thì lấy **thẻ vào thớt** ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Nhưng nếu đầu bếp cầm thẻ rồi bị gọi đi chỗ khác (hệ điều hành lấy lõi của luồng đó), cả bếp đứng chờ người cầm thẻ quay lại.

Bếp thử bỏ thẻ. Mỗi lần muốn đổi, đầu bếp **nhìn** đầu băng chuyền đang là đĩa nào, chuẩn bị đĩa mới ở bàn riêng, rồi đặt vào **chỉ nếu đầu băng vẫn đúng đĩa lúc nãy nhìn** (một lần so và đổi, chính là `compare_exchange` của [Bài 28](../nhom-3-da-luong/28-atomic.md)). Có người đổi trước thì nhìn lại và làm lại. Không ai cầm gì, nên ai bị gọi đi cũng không chặn người khác. Đó là **lock-free**.

Có một ca đặc biệt đẹp: đúng **một** đầu bếp đặt đĩa và đúng **một** đầu bếp lấy đĩa, qua một **cửa sổ chuyển món có N ô xếp vòng tròn**. Mỗi người chỉ đụng vạch của mình nên không cần so-và-đổi; đó là hàng đợi SPSC ở nửa sau bài.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    Đĩa trong bếp không "đổi rồi trả về y như cũ mà vẫn khác". Trong bộ nhớ thì có: địa chỉ bị giải phóng rồi cấp lại cho một nút mới, và so-và-đổi chỉ so **địa chỉ**, không so "đời" của nút (đó là ABA, mục 4). Ngoài ra "không ai chặn ai" không có nghĩa là rẻ: nhiều người cùng nhìn rồi làm lại thì tốn công, và bài đo ở phần 💻 cho thấy cái giá đó.

## 📖 Giải thích

### 1. Ba mức bảo đảm tiến lên

"Có dùng `mutex` hay không" không phải thước đo đúng. Thước đo đúng là câu hỏi: **nếu một luồng bị hoãn bao lâu cũng được, các luồng khác có còn xong việc không?**

| Mức | Bảo đảm | Ví dụ |
|---|---|---|
| Có chặn (blocking) | Luồng giữ khóa bị hoãn thì mọi luồng cần khóa đó đứng chờ | `mutex`, hàng đợi bọc `mutex`, cả spinlock ([Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md)) |
| **Lock-free** | Dù luồng nào bị hoãn, trong hệ thống **luôn có ít nhất một** luồng xong thao tác sau số bước hữu hạn | vòng CAS, ngăn xếp Treiber (mục 3) |
| **Wait-free** | **Mọi** luồng xong thao tác sau số bước hữu hạn, có chặn trên số bước | `push`/`pop` của SPSC ở mục 5 (không có vòng lặp nào) |

Lock-free cho phép **một** luồng thử đi thử lại mãi nếu luồng khác luôn nhanh hơn; chỉ cần hệ thống nói chung vẫn tiến lên. Wait-free thì không ai bị đói. Spinlock tự viết bằng `atomic_flag` không có chữ `mutex` nhưng vẫn là có chặn: luồng giữ khóa bị hoãn thì cả đám quay vòng chờ.

Đừng lẫn với `is_lock_free()` của [Bài 28](../nhom-3-da-luong/28-atomic.md): đó hỏi **kiểu** atomic này chạy bằng lệnh CPU hay thư viện giấu một khóa bên trong. Một thuật toán lock-free còn đòi mọi kiểu atomic nó dùng đều `is_lock_free()` thật; nếu không, nó có khóa ngầm. Mình gọi thật: `atomic<size_t>` và `atomic` của struct 8 byte ở mục 4 đều ra `1` trên g++ 11, x86-64 (chuẩn không hứa điều đó cho mọi máy).

### 2. Vòng lặp CAS: đọc, tính, đổi-nếu-chưa-ai-đổi

[Bài 28](../nhom-3-da-luong/28-atomic.md) đã dạy `compare_exchange`; đây là khuôn dùng lại cho mọi thuật toán lock-free. Ví dụ: `std::atomic` không có sẵn phép "đặt thành max", nên tự viết.

```text
void capNhatLonNhat(std::atomic<int>& lonNhat, int v) {
    int cu = lonNhat.load();                              // (1) đọc
    while (cu < v) {                                      // (2) tính: còn cần đổi không?
        if (lonNhat.compare_exchange_weak(cu, v)) return; // (3) đổi nếu chưa ai đổi
        // (4) thất bại: cu vừa được ghi giá trị mới nhất, vòng lại (2)
    }
}
```

Mình chạy bốn luồng, mỗi luồng gọi hàm này 100000 lần với dãy tăng dần (`i * 4 + k`): `lonNhat` ra đúng `399999` mọi lần, TSan sạch. Số lần CAS thất bại, năm lần chạy mỗi mức: từ 106393 đến 153134 ở `-O2`, từ 136377 đến 197989 không tối ưu (đổi theo lần chạy và máy). Bốn luồng giẫm chân nhau nên mỗi lần thất bại là một vòng làm lại.

Vì sao đây là lock-free: một CAS thất bại **vì giá trị đã khác** nghĩa là có luồng khác vừa đổi thành công, nên hệ thống vẫn tiến lên. Vì sao chưa phải wait-free: không có chặn trên số lần một luồng xui xẻo phải thử. `weak` được phép thất bại giả ([Bài 28](../nhom-3-da-luong/28-atomic.md)), chỉ tốn thêm một vòng, nên đặt nó trong vòng lặp là đúng.

Ba luật của vòng CAS: **(a)** phần "tính" chỉ dựa vào `cu` và không có tác dụng phụ, vì nó chạy lại nhiều lần; **(b)** mọi thứ muốn đổi nguyên tử phải nằm trong **một** ô atomic, vì CAS chỉ so một ô; **(c)** CAS chỉ so **giá trị**, không biết ô đã bị đổi đi rồi đổi lại. Luật (c) là mầm của ABA.

### 3. Ngăn xếp Treiber: đọc hiểu, và vì sao bản ngây thơ hỏng

Ngăn xếp là một chuỗi nút, biến atomic `dau_` trỏ vào nút trên cùng. `push`: nút mới trỏ vào đầu hiện tại, rồi CAS đầu từ cũ sang nút mới. `pop`: CAS đầu từ nút trên cùng sang nút kế tiếp của nó. Chỉ một ô atomic (`dau_`), đúng luật (b). Đây là bản dễ viết nhất; mục này **chỉ để đọc hiểu**, đừng dùng.

```cpp
// bo-qua-kiem-tra
#include <atomic>
#include <iostream>
#include <thread>
#include <utility>
#include <vector>

template <typename T>
class NganXepNgayTho {                     // ngăn xếp Treiber bản "ngây thơ"
    struct Nut { T giaTri; Nut* tiep; };
    std::atomic<Nut*> dau_{nullptr};
public:
    void push(T v) {
        Nut* nut = new Nut{std::move(v), dau_.load()};              // (1) nút mới trỏ vào đầu hiện tại
        while (!dau_.compare_exchange_weak(nut->tiep, nut)) {}      // (2) thất bại: nut->tiep được cập nhật, thử lại
    }
    bool pop(T& ra) {
        Nut* cu = dau_.load();
        while (cu && !dau_.compare_exchange_weak(cu, cu->tiep)) {}  // (3) ĐỌC cu->tiep: nút có thể đã bị luồng khác xóa
        if (!cu) return false;
        ra = std::move(cu->giaTri);
        delete cu;                                                  // (4) xóa ngay: luồng khác có thể còn đang cầm cu
        return true;
    }
};

NganXepNgayTho<int> ns;
std::atomic<long> tong{0};

void tho() {
    for (int i = 0; i < 200000; ++i) {
        ns.push(1);
        int x;
        if (ns.pop(x)) tong += x;
    }
}

int main() {
    std::vector<std::thread> v;
    for (int k = 0; k < 4; ++k) v.emplace_back(tho);
    for (auto& t : v) t.join();
    std::cout << tong << "\n";
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này (minh họa) |
|---|---|---|
| (1) | `push` dựng nút mới `N` có `tiep` = đầu hiện tại | `dau_ → A → B`; `N → A` |
| (2) | CAS đầu từ `nut->tiep` sang `nut`. Có người đẩy trước thì `nut->tiep` được cập nhật thành đầu mới, vòng lại | `dau_ → N → A → B` |
| (3) | `pop` đọc đầu `cu = N` (rỗng thì dừng), rồi **đọc `cu->tiep`** để CAS đầu sang đó | `dau_ → A → B` |
| (4) | Lấy giá trị ra, `delete cu` | nút `N` được trả lại heap |

**Hỏng ở đâu.** Ở (3), giữa lúc luồng này đọc `cu` và đọc `cu->tiep`, luồng khác có thể đã `pop` đúng nút đó và `delete` ở (4): đọc `cu->tiep` là **use-after-free**. Mình chạy bản này (bốn luồng, mỗi luồng 200000 lần đẩy rồi lấy): với ASan, năm lần chạy cả năm lần báo `heap-use-after-free` ngay dòng đọc `cu->tiep`:

```text
ERROR: AddressSanitizer: heap-use-after-free on address 0x... at pc 0x...
READ of size 8 at 0x... thread T3
    #0 0x... in NganXepNgayTho<int>::pop(int&) ...
```

Không bật sanitizer, `-O2`, sáu lần chạy: cả sáu lần chương trình sập (mã thoát 139 hoặc 134, nhiều lần kèm `free(): unaligned chunk detected in tcache 2`: heap đã bị phá). Ngay cả khi đọc phải rác mà CAS vẫn thành công, ta gặp ABA (mục 4).

**Thử thay đổi:** bỏ dòng `delete cu` (4). Chạy lại (mỗi luồng 50000 lần): `tong` ra đúng 200000, TSan sạch, không còn use-after-free. Nhưng LeakSanitizer báo `3200000 byte(s) leaked in 200000 allocation(s)`: mọi nút đã lấy ra đều không bao giờ được trả. Xóa thì hỏng, không xóa thì rò: đó là **bài toán thu hồi bộ nhớ**, phần khó nhất của cấu trúc lock-free (mục 4).

### 4. ABA: đúng giá trị, sai câu chuyện

Kịch bản: ngăn xếp `A → B → C`. Luồng 1 `pop`: đọc đầu là `A`, kế tiếp là `B`, rồi bị hoãn. Luồng 2 chạy một loạt: `pop` (lấy A), `pop` (lấy B), rồi `push` một nút mới, và allocator tình cờ cấp lại **đúng địa chỉ của A**. Giờ ngăn xếp là `A' → C` với `A'` trùng địa chỉ `A`. Luồng 1 tỉnh dậy và CAS "đầu từ `A` sang `B`": đầu vẫn bằng `A`, nên CAS **thành công**, đầu thành `B`, nút đã bị lấy và có thể đã bị `delete`.

Để chạy lại kịch bản này mà không phải đợi may rủi (lỗi thật xảy ra hiếm và khó tái hiện), chương trình dưới tự xếp lịch xen kẽ bằng tay, **không dùng luồng**. Nút nằm trong mảng 3 ô, "dùng lại địa chỉ" nghĩa là `push` vào đúng ô 0 vừa trống.

`std::uint32_t` (từ `<cstdint>`) là số nguyên không dấu đúng 32 bit; đầu ngăn xếp là struct hai số `Dau{the, chiSo}` (viết `Dau{0, 0}` là `the = 0`, `chiSo = 0`) vừa 8 byte nên CAS một nhịp được. Thẻ `the` là **số phiên bản**: mỗi lần đổi đầu, bản có thẻ tăng nó thêm 1.

```cpp
#include <atomic>
#include <cstdint>
#include <iostream>

// Ngăn xếp Treiber dựng trên mảng 3 nút, để việc "dùng lại nút" xảy ra có chủ đích.
struct Nut { int giaTri; std::uint32_t tiep; };           // tiep: chỉ số nút kế tiếp; HET nếu không còn
struct Dau { std::uint32_t the; std::uint32_t chiSo; };   // (1) số phiên bản + chỉ số nút đầu: vừa 8 byte
constexpr std::uint32_t HET = 0xFFFFFFFF;                 // số 32 bit lớn nhất, dùng làm dấu "hết"

Nut nut[3];
std::atomic<Dau> dau;

std::uint32_t theMoi(Dau d, bool coThe) {                 // (2) bật thẻ: mỗi lần đổi đầu, thẻ tăng 1
    if (coThe) return d.the + 1;
    return d.the;
}

void push(std::uint32_t chiSo, int giaTri, bool coThe) {
    nut[chiSo].giaTri = giaTri;
    Dau cu = dau.load();
    nut[chiSo].tiep = cu.chiSo;
    while (!dau.compare_exchange_weak(cu, Dau{theMoi(cu, coThe), chiSo})) {
        nut[chiSo].tiep = cu.chiSo;                       // thất bại: cu đã mới, nối lại cho khớp
    }
}

int pop(bool coThe) {                                     // (ở kịch bản này ngăn xếp không bao giờ rỗng)
    Dau cu = dau.load();
    while (!dau.compare_exchange_weak(cu, Dau{theMoi(cu, coThe), nut[cu.chiSo].tiep})) {}
    return nut[cu.chiSo].giaTri;
}

void inNganXep() {
    std::cout << "ngan xep con lai:";
    for (std::uint32_t i = dau.load().chiSo; i != HET; i = nut[i].tiep) std::cout << " " << nut[i].giaTri;
    std::cout << "\n";
}

void kichBan(bool coThe) {
    nut[0] = {10, 1}; nut[1] = {20, 2}; nut[2] = {30, HET};   // ngăn xếp: 10 -> 20 -> 30 (10 ở đỉnh)
    dau.store(Dau{0, 0});
    // Luồng 1 bắt đầu pop: đọc xong (đầu = nút 0, kế tiếp = nút 1) thì bị hoãn.
    Dau l1 = dau.load();                                  // (3)
    std::uint32_t l1Tiep = nut[l1.chiSo].tiep;
    // Trong lúc đó luồng 2 làm một loạt việc:
    int a = pop(coThe);                                   // (4) lấy 10
    int b = pop(coThe);                                   // (5) lấy 20
    push(0, 40, coThe);                                   // (6) đẩy 40 vào đúng nút 0 vừa trống: "địa chỉ cũ" được dùng lại
    std::cout << "luong 2 lay " << a << " va " << b << ", roi day 40\n";
    // Luồng 1 tiếp tục: CAS(đầu: nút 0 -> nút 1).
    bool ok = dau.compare_exchange_strong(l1, Dau{theMoi(l1, coThe), l1Tiep});   // (7)
    if (ok) {
        std::cout << "CAS cua luong 1 THANH CONG, luong 1 tin la da lay " << nut[l1.chiSo].giaTri << "\n";
    } else {
        std::cout << "CAS cua luong 1 that bai, luong 1 doc lai va lay " << pop(coThe) << "\n";
    }
    inNganXep();
}

int main() {
    std::cout << "--- khong co the phien ban ---\n";
    kichBan(false);
    std::cout << "--- co the phien ban ---\n";
    kichBan(true);
    std::cout << "is_lock_free cua atomic<Dau>: " << dau.is_lock_free() << "\n";
    return 0;
}
```

**Chạy từng dòng** (cùng một kịch bản, chạy hai lần: không thẻ rồi có thẻ)

| Dòng | Chuyện gì xảy ra | Ngăn xếp / đầu lúc này |
|---|---|---|
| (3) | Luồng 1 đọc đầu = nút 0 (thẻ 0) và `l1Tiep` = nút 1, rồi "bị hoãn" | `10 → 20 → 30` |
| (4)(5) | Luồng 2 lấy 10, lấy 20 (nếu có thẻ: thẻ thành 1, rồi 2) | `30` |
| (6) | Luồng 2 đẩy 40 vào nút 0: nút 0 lại là đầu, `tiep` = nút 2 (có thẻ: thẻ thành 3) | `40 → 30` |
| (7) | Luồng 1 CAS đầu từ (nút 0, thẻ 0) sang (nút 1, thẻ +1). Không thẻ: đầu vẫn là "nút 0, thẻ 0" nên thành công. Có thẻ: đầu là "nút 0, thẻ 3" nên thất bại | không thẻ: `20 → 30` |

**Kết quả khi chạy** (ổn định, chương trình không có luồng nào; ASan/UBSan sạch):

```text
--- khong co the phien ban ---
luong 2 lay 10 va 20, roi day 40
CAS cua luong 1 THANH CONG, luong 1 tin la da lay 40
ngan xep con lai: 20 30
--- co the phien ban ---
luong 2 lay 10 va 20, roi day 40
CAS cua luong 1 that bai, luong 1 doc lai va lay 40
ngan xep con lai: 30
is_lock_free cua atomic<Dau>: 1
```

Bản không thẻ: luồng 1 lấy 40 (đúng) nhưng ngăn xếp còn `20 30`, trong khi `20` đã bị luồng 2 lấy rồi: **phần tử 20 sống lại**. Với nút thật đã `delete`, đầu sẽ trỏ vào bộ nhớ đã giải phóng. Bản có thẻ: CAS thất bại vì thẻ đã đổi, luồng 1 đọc lại và lấy đúng, còn `30`.

**Cách phòng ABA và thu hồi bộ nhớ** (chỉ cần biết tên và ý):

| Cách | Ý chính |
|---|---|
| Thẻ phiên bản (như trên) | Gắn số đếm vào con trỏ/chỉ số, CAS so cả cặp; cần CAS đủ rộng, và vẫn chưa giải quyết việc khi nào được `delete` |
| Hazard pointer | Mỗi luồng ghi công khai "tôi đang đọc nút này"; luồng muốn `delete` thì kiểm các ghi chú, nút đang bị ghi thì hoãn xóa |
| Epoch (thu hồi theo kỷ) | Luồng vào "kỷ" hiện tại khi đụng cấu trúc; nút bị gỡ chỉ được xóa khi mọi luồng đã sang kỷ mới hơn |
| Không bao giờ xóa trong lúc chạy | Nút nằm trong vùng cấp sẵn, giải phóng cả vùng sau cùng; đơn giản, đúng, nhưng bộ nhớ chỉ tăng |

!!! info "Bạn biết Go?"
    Go có bộ gom rác nên ngăn xếp Treiber "ngây thơ" viết bằng Go gần như không bị use-after-free: nút chưa bị xóa khi còn con trỏ trỏ vào nó, và địa chỉ không được cấp lại khi luồng 1 còn giữ `A`. Điều kiện: mỗi lần `push` cấp nút mới và không tự tái dùng nút (ví dụ qua `sync.Pool`). C++ không có gom rác nên phải tự giải bài thu hồi này. Go cũng có CAS (`atomic.CompareAndSwapInt64`, `atomic.Pointer[T].CompareAndSwap`), chỉ trả `bool`.

### 5. Hàng đợi vòng SPSC: lock-free dễ nhất và đáng viết nhất

**SPSC** (single-producer single-consumer: một luồng ghi, một luồng đọc) là trường hợp mà không cần CAS. Một mảng `buf_` N ô xếp vòng, hai chỉ số: `dau_` (ô sẽ đọc tiếp) và `duoi_` (ô sẽ ghi tiếp). **Quy tắc sở hữu**: chỉ luồng ghi sửa `duoi_`, chỉ luồng đọc sửa `dau_`, và tại mỗi lúc mỗi ô thuộc đúng một bên. Rỗng khi `dau_ == duoi_`. Đầy khi `duoi_ + 1` (quay vòng) chạm `dau_`, nên chứa tối đa N − 1 phần tử (chừa một ô để phân biệt đầy với rỗng).

```text
N = 4:   ô 0   ô 1   ô 2   ô 3        rỗng:  dau_=0 duoi_=0
         [ 7 ] [ 8 ] [ . ] [ . ]      có 2:  dau_=0 duoi_=2   (ô 0,1 của luồng đọc; ô 2,3 của luồng ghi)
```

Còn thứ tự bộ nhớ, giải thích tại chỗ (chi tiết ở [Bài 59](59-memory-model.md)). Để giao một ô từ bên này sang bên kia, bên giao **đóng dấu** bằng một lần ghi chỉ số kiểu `release`: mọi thứ ghi trước dòng đó (dữ liệu trong ô) hiện ra trước dấu. Bên nhận **nhìn dấu** bằng một lần đọc chỉ số kiểu `acquire`: thấy đúng dấu mới thì mọi thứ trước dấu đã đọc được. Cặp này phải nằm trên **cùng một biến atomic**; thiếu cặp thì CPU hoặc trình biên dịch được phép cho bên nhận thấy chỉ số mới mà dữ liệu vẫn cũ.

Có **hai** lần giao: ghi giao dữ liệu cho đọc (qua `duoi_`) và đọc giao ô trống lại cho ghi (qua `dau_`). Đọc chính chỉ số của mình thì không cần dấu: chỉ mình ta ghi nó, nên `relaxed` đủ.

`%` là phép chia lấy dư: `(duoi + 1) % N` quay về 0 khi chạm N. `template <typename T, std::size_t N>` có tham số thứ hai là một **số** (như `std::array<int, 5>`), nên `HangDoiSpsc<int, 1024>` là hàng đợi 1024 ô.

### 6. Khi nào KHÔNG nên viết lock-free

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Nhiều luồng ghi và/hoặc nhiều luồng đọc, hàng đợi việc thông thường | `mutex` + `condition_variable` (Bài 66) | Đúng, dễ kiểm, và luồng ngủ khi hết việc thay vì đốt CPU |
| Cần **chờ** khi đầy/rỗng | `condition_variable` | SPSC chỉ trả `false`; chờ là việc của người gọi (quay vòng đốt CPU, hoặc ngủ rồi thử lại) |
| Đúng một ghi một đọc, đường nóng, **đã đo** thấy khóa là nút cổ chai | SPSC | Quy tắc sở hữu làm nó đơn giản; mục 💻 đo nhanh hơn bản mutex 10 đến 20 lần |
| Cấu trúc phức tạp (map, danh sách xóa giữa), nhiều luồng ghi | Khóa, hoặc thư viện đã được kiểm chứng (ví dụ `spsc_queue`, `queue` trong Boost.Lockfree) | ABA, thu hồi bộ nhớ, thứ tự bộ nhớ: sai một chỗ là lỗi hiếm khó tái hiện |

Lý do chung: lock-free **khó đúng** (chạy đúng trên x86 không chứng minh gì: mục 💻 có bản sai chạy đúng 60 lần mà TSan vẫn báo), **khó kiểm thử** ([Bài 64](64-go-loi-da-luong.md)), **không bảo đảm nhanh hơn** khi tranh chấp nặng (mỗi CAS thất bại là làm lại) và không hề chờ-ngủ. Nguyên tắc của [Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md) vẫn nguyên: dùng mutex trước, chạy đúng, đo, rồi mới tối ưu.

## 💻 Ví dụ code

### Ví dụ 1: hàng đợi vòng SPSC, kiểm thứ tự và tổng

Luồng chính ghi `1..200000`; một luồng đọc lấy ra, kiểm từng phần tử có đúng thứ tự mong đợi không và cộng dồn. Hàng đợi 1024 ô nên chắc chắn nhiều lần đầy và quay vòng. `[&]` trong lambda bắt mọi biến bên ngoài bằng tham chiếu; `std::this_thread::yield()` nhường lõi cho luồng khác thay vì quay vòng đốt CPU.

```cpp
#include <array>
#include <atomic>
#include <cstddef>
#include <iostream>
#include <thread>

// Hàng đợi vòng một-người-ghi một-người-đọc (SPSC). Chứa tối đa N - 1 phần tử (chừa một ô để phân biệt đầy với rỗng).
template <typename T, std::size_t N>
class HangDoiSpsc {
    static_assert(N >= 2, "can it nhat 2 o");
public:
    // Chỉ luồng GHI (producer) được gọi. Trả false nếu hàng đợi đầy.
    bool push(const T& v) {
        std::size_t duoi = duoi_.load(std::memory_order_relaxed);     // (1) chỉ mình ta ghi duoi_, đọc kiểu relaxed là đủ
        std::size_t ke = (duoi + 1) % N;
        if (ke == dau_.load(std::memory_order_acquire)) return false; // (2) đầy; acquire: thấy mọi việc luồng đọc làm trước khi trả ô
        buf_[duoi] = v;                                               // (3) ghi dữ liệu vào ô
        duoi_.store(ke, std::memory_order_release);                   // (4) công bố: "ô này đã có dữ liệu"
        return true;
    }
    // Chỉ luồng ĐỌC (consumer) được gọi. Trả false nếu hàng đợi rỗng.
    bool pop(T& ra) {
        std::size_t dau = dau_.load(std::memory_order_relaxed);       // (5) chỉ mình ta ghi dau_
        if (dau == duoi_.load(std::memory_order_acquire)) return false; // (6) rỗng; acquire: thấy dữ liệu đã công bố ở (4)
        ra = buf_[dau];                                               // (7) lấy dữ liệu ra
        dau_.store((dau + 1) % N, std::memory_order_release);         // (8) trả ô: "ô này đã đọc xong, ghi đè được"
        return true;
    }
private:
    alignas(64) std::atomic<std::size_t> dau_{0};    // chỉ số ô sẽ đọc tiếp theo (luồng đọc sở hữu)
    alignas(64) std::atomic<std::size_t> duoi_{0};   // chỉ số ô sẽ ghi tiếp theo (luồng ghi sở hữu)
    std::array<T, N> buf_{};
};

constexpr int SO_PHAN_TU = 200000;
HangDoiSpsc<int, 1024> hd;

int main() {
    long long tong = 0;
    int soDung = 0;                         // số phần tử đến đúng thứ tự mong đợi
    int soNhan = 0;

    std::thread nguoiDoc([&] {
        int mongDoi = 1;
        while (soNhan < SO_PHAN_TU) {
            int x;
            if (hd.pop(x)) {                // (9) lấy được: kiểm thứ tự và cộng dồn
                if (x == mongDoi) ++soDung;
                ++mongDoi;
                tong += x;
                ++soNhan;
            } else {
                std::this_thread::yield();  // rỗng: nhường lõi rồi thử lại
            }
        }
    });

    for (int i = 1; i <= SO_PHAN_TU; ++i) { // luồng chính là người ghi
        while (!hd.push(i)) {
            std::this_thread::yield();      // đầy: nhường lõi rồi thử lại
        }
    }
    nguoiDoc.join();

    std::cout << "da nhan " << soNhan << " phan tu, dung thu tu: " << soDung << "\n";
    std::cout << "tong = " << tong << " (ky vong " << (long long)SO_PHAN_TU * (SO_PHAN_TU + 1) / 2 << ")\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ô nhớ lúc này (N nhỏ, minh họa) |
|---|---|---|
| (1) | Luồng ghi đọc `duoi_` của chính mình, `relaxed`: không ai khác ghi nó | `duoi_=0` |
| (2) | Tính `ke`; đọc `dau_` kiểu `acquire`: nếu `ke == dau_` thì đầy, trả `false`. `acquire` để thấy "luồng đọc đã đọc xong ô này" trước khi ghi đè | `dau_=0` |
| (3) | Ghi dữ liệu vào `buf_[duoi]`: ô này đang thuộc luồng ghi | `[7 . . .]` |
| (4) | `duoi_.store(ke, release)`: công bố, ô vừa ghi nay thuộc luồng đọc | `duoi_=1` |
| (5)(6) | Luồng đọc đọc `dau_` của mình (`relaxed`), đọc `duoi_` kiểu `acquire`: bằng nhau thì rỗng, trả `false`. `acquire` để thấy dữ liệu đã ghi trước (4) | `dau_=0 duoi_=1` |
| (7) | Lấy `buf_[dau]` ra | `ra = 7` |
| (8) | `dau_.store(dau+1, release)`: trả ô, nay thuộc luồng ghi | `dau_=1` |
| (9) | Luồng đọc kiểm `x == mongDoi` rồi cộng dồn; `main` in sau `join` | |

**Kết quả khi chạy** (50 lần liền ở `-O2` và 20 lần dưới TSan đều ra y hệt; TSan sạch, mã thoát 0):

```text
da nhan 200000 phan tu, dung thu tu: 200000
tong = 20000100000 (ky vong 20000100000)
```

`soNhan`, `soDung`, `tong` chỉ luồng đọc sửa, và `main` chỉ đọc sau `join` nên không có data race.

**Thử thay đổi** (đều chạy thật dưới TSan; mỗi bản sai cho `data race` và mã thoát 66):

- Đổi `release` ở dòng (4) thành `relaxed`: TSan báo `data race` giữa việc ghi `buf_[duoi]` trong `push` và việc đọc `buf_[dau]` trong `pop`. Nhưng chạy thường ở `-O2` và `-O3`, mỗi mức 30 lần, **vẫn ra đúng cả 30 lần**: x86 giữ thứ tự hai lệnh ghi, nên "chạy đúng" không chứng minh gì, và chuẩn không hứa; CPU yếu thứ tự hơn (nhiều CPU ARM) được phép làm hỏng.
- Đổi `acquire` ở dòng (2) thành `relaxed`: TSan báo data race ở dòng (3) (ghi đè ô mà chưa chắc luồng đọc đã đọc xong). Đổi `acquire` ở dòng (6): data race ở dòng (7).
- Hai luồng cùng `push` (mỗi luồng 100000 phần tử): TSan báo data race ở cả `push` lẫn `pop`. Chạy `-O2` năm lần: bốn lần treo (hết hạn 10 giây, mã 124; nhiều khả năng hai luồng ghi chung một ô làm mất phần tử nên luồng đọc chờ mãi, mình không kiểm riêng điều này), một lần chạy xong. SPSC chỉ đúng khi đúng một luồng ghi và một luồng đọc.
- Đổi 1024 thành 2 (chứa tối đa 1 phần tử): vẫn đúng, ra y hệt, TSan sạch; chỉ chậm vì hai luồng phải nhường nhau từng phần tử.

### Ví dụ 2: `alignas(64)` cho hai chỉ số, và so với `mutex`

`dau_` (luồng đọc ghi) và `duoi_` (luồng ghi ghi) là hai biến khác nhau, nhưng nếu nằm sát nhau thì rất có thể chung một dòng cache 64 byte: mỗi lần một bên ghi, lõi bên kia phải nạp lại dòng ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)). Chương trình đo chuyển 1000000 phần tử qua ba hàng đợi: SPSC với hai chỉ số sát nhau (`Le = 8`), SPSC có `alignas(64)`, và hàng đợi `mutex + std::queue` cùng giao diện. Khối này đánh dấu bỏ qua vì thời gian đổi theo máy và TSan chậm hơn hàng chục lần; mình chạy tay, và chạy TSan bản giảm cỡ (20000 phần tử): sạch.

```cpp
// bo-qua-kiem-tra
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>

// Lớp ở Ví dụ 1, thêm tham số Le: lề căn của hai chỉ số (8 = nằm sát nhau, 64 = mỗi chỉ số một dòng cache).
template <typename T, std::size_t N, std::size_t Le>
class HangDoiSpsc {
public:
    bool push(const T& v) {
        std::size_t duoi = duoi_.load(std::memory_order_relaxed), ke = (duoi + 1) % N;
        if (ke == dau_.load(std::memory_order_acquire)) return false;
        buf_[duoi] = v;
        duoi_.store(ke, std::memory_order_release);
        return true;
    }
    bool pop(T& ra) {
        std::size_t dau = dau_.load(std::memory_order_relaxed);
        if (dau == duoi_.load(std::memory_order_acquire)) return false;
        ra = buf_[dau];
        dau_.store((dau + 1) % N, std::memory_order_release);
        return true;
    }
private:
    alignas(Le) std::atomic<std::size_t> dau_{0};
    alignas(Le) std::atomic<std::size_t> duoi_{0};
    std::array<T, N> buf_{};
};

// Đối chứng: cùng giao diện, một mutex bảo vệ std::queue.
template <typename T, std::size_t N>
class HangDoiMutex {
public:
    bool push(const T& v) {
        std::lock_guard<std::mutex> giu(khoa_);
        if (q_.size() == N - 1) return false;
        q_.push(v);
        return true;
    }
    bool pop(T& ra) {
        std::lock_guard<std::mutex> giu(khoa_);
        if (q_.empty()) return false;
        ra = q_.front();
        q_.pop();
        return true;
    }
private:
    std::mutex khoa_;
    std::queue<T> q_;
};

HangDoiSpsc<int, 1024, 8> sat;
HangDoiSpsc<int, 1024, 64> rieng;
HangDoiMutex<int, 1024> coKhoa;
constexpr int SO_PHAN_TU = 1000000;
constexpr int SO_LAN = 5;

template <typename HD>
long long chay(HD& hd) {                    // số mili-giây để chuyển SO_PHAN_TU phần tử qua hàng đợi
    auto bd = std::chrono::steady_clock::now();
    std::thread nguoiDoc([&] {
        int x;
        for (int nhan = 0; nhan < SO_PHAN_TU;) {
            if (hd.pop(x)) ++nhan;          // rỗng thì quay vòng hỏi lại ngay (cần từ hai lõi)
        }
    });
    for (int i = 0; i < SO_PHAN_TU; ++i) {
        while (!hd.push(i)) {}              // đầy thì quay vòng hỏi lại ngay
    }
    nguoiDoc.join();
    auto kt = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(kt - bd).count();
}

int main() {
    std::cout << "sizeof sat = " << sizeof(sat) << ", sizeof rieng = " << sizeof(rieng) << "\n";
    long long tSat = 1000000000, tRieng = 1000000000, tKhoa = 1000000000;   // lớn hơn mọi thời gian đo được
    for (int lan = 0; lan < SO_LAN; ++lan) {         // (1) xen kẽ ba loại, mỗi loại lấy lượt nhanh nhất
        tSat = std::min(tSat, chay(sat));
        tRieng = std::min(tRieng, chay(rieng));
        tKhoa = std::min(tKhoa, chay(coKhoa));
    }
    std::cout << "SPSC chi so sat nhau (Le 8): " << tSat << " ms\n";
    std::cout << "SPSC alignas(64)           : " << tRieng << " ms\n";
    std::cout << "mutex + queue              : " << tKhoa << " ms\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| `sat`, `rieng` | Cùng lớp, khác `Le`: `sat` có hai chỉ số kề nhau (`sizeof` 4112), `rieng` đẩy `duoi_` sang dòng kế (`sizeof` 4224) |
| `chay` | Luồng đọc quay vòng `pop`, luồng chính quay vòng `push`; trả số mili-giây |
| (1) | Chạy xen kẽ ba loại 5 lượt, mỗi loại lấy lượt nhanh nhất để bớt nhiễu do máy bận |

**Kết quả khi chạy** (một lần, `-O2`; số đổi theo máy và lần chạy, chỉ tỉ lệ có ý nghĩa):

```text
sizeof sat = 4112, sizeof rieng = 4224
SPSC chi so sat nhau (Le 8): 14 ms
SPSC alignas(64)           : 8 ms
mutex + queue              : 143 ms
```

Mình chạy tám lần mỗi mức tối ưu. Về **mutex**: `-O2` từ 121 đến 148 ms, không tối ưu từ 352 đến 388 ms, tức SPSC nhanh hơn khoảng 10 đến 20 lần (SPSC từ 6 đến 15 ms ở `-O2`). Về **`alignas(64)`**: kết quả không đều. Ở `-O2`, bốn trong tám lần bản sát nhau chậm gấp khoảng 2 (14 đến 15 ms so với 5 đến 9 ms), bốn lần còn lại như nhau (6 so với 7 ms). Không tối ưu: không thấy lợi (`alignas(64)` nhanh hơn 2 trong 8 lần, còn lại bằng hoặc chậm hơn). Mình đoán chênh lệch phụ thuộc hai luồng rơi vào những lõi nào (hai luồng chung một lõi vật lý thì chia sẻ cache nên không mất gì), nhưng không kiểm điều đó. Nên `alignas(64)` là thói quen đúng về nguyên lý, và lợi ích phải **đo trên máy thật**, không đoán.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Lock-free, wait-free và blocking khác nhau thế nào? Spinlock có phải lock-free không?"
    Blocking: luồng giữ khóa bị hoãn thì luồng cần khóa đó đứng chờ. Lock-free: dù luồng nào bị hoãn, luôn có ít nhất một luồng khác xong thao tác sau số bước hữu hạn (một luồng cụ thể vẫn có thể bị đói). Wait-free: mọi luồng xong sau số bước hữu hạn. **Nối tiếp:** spinlock **không** lock-free, dù không gọi `mutex`: luồng giữ khóa bị hệ điều hành tạm dừng thì mọi luồng khác quay vòng chờ. Và `is_lock_free()` là câu hỏi khác: kiểu atomic có chạy bằng lệnh CPU hay không.

??? question "Vòng lặp CAS hoạt động thế nào, vì sao `weak` nằm trong vòng lặp?"
    Đọc giá trị hiện tại, tính giá trị mới chỉ từ giá trị đó, rồi `compare_exchange_weak(cu, moi)`: đổi nếu ô vẫn bằng `cu`, không thì ghi giá trị hiện tại vào `cu` và vòng lại. `weak` được phép thất bại giả dù giá trị đúng, nên phải nằm trong vòng lặp; thất bại giả chỉ tốn thêm một vòng. Phần tính phải không có tác dụng phụ vì nó chạy lại. Vòng này lock-free (CAS thất bại vì giá trị đã khác nghĩa là có luồng khác vừa thành công) nhưng chưa wait-free.

??? question "ABA là gì? Cho ví dụ và cách phòng."
    CAS chỉ so giá trị. Ở ngăn xếp: luồng 1 đọc đầu `A` và kế tiếp `B`, bị hoãn; luồng 2 lấy `A`, lấy `B`, rồi đẩy lại một nút tình cờ cùng địa chỉ `A`; CAS của luồng 1 thấy "vẫn là `A`" nên thành công và đặt đầu vào `B`, nút đã bị lấy (phần tử "sống lại", hoặc trỏ vào bộ nhớ đã xóa). Phòng: thẻ phiên bản gắn vào con trỏ (CAS so cả cặp), hoặc kỹ thuật thu hồi bộ nhớ như hazard pointer, epoch để nút chưa an toàn thì chưa bị xóa và địa chỉ chưa bị cấp lại. **Nối tiếp:** "sao không `delete` luôn?" Vì luồng khác có thể còn đang đọc nút đó (use-after-free); không xóa thì rò rỉ.

??? question "Tự viết một queue lock-free trên bảng trắng."
    Hỏi lại ràng buộc trước: mấy luồng ghi, mấy luồng đọc, có cần chờ không. Với **một ghi một đọc**: mảng N ô xếp vòng, `dau_` chỉ luồng đọc sửa, `duoi_` chỉ luồng ghi sửa; `push` ghi dữ liệu rồi `store(duoi_, release)`, `pop` `load(duoi_, acquire)` rồi đọc dữ liệu rồi `store(dau_, release)`; `push` đọc `dau_` bằng `acquire` để chắc ô đã trống; chứa tối đa N − 1; hai chỉ số đặt `alignas(64)`. Với **nhiều ghi hoặc nhiều đọc**: nói thẳng là rất khó (ABA, thu hồi bộ nhớ, thứ tự), mặc định dùng `mutex` + `condition_variable`, hoặc thư viện đã kiểm chứng. **Nối tiếp:** "hai luồng cùng `push` thì sao?" Hỏng: hai luồng ghi cùng một ô và mất phần tử (mình chạy: TSan báo data race, và bốn lần trong năm lần chạy bị treo).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tin 'chạy đúng trên máy mình' là đúng"
    Bản SPSC dùng `relaxed` để công bố chạy đúng 60 lần trên x86 của mình, mà TSan vẫn báo data race. x86 che mất lỗi thứ tự bộ nhớ. Chạy TSan, và dùng đúng cặp `release`/`acquire`.

!!! warning "Lỗi 2: Dùng SPSC với hai luồng ghi (hoặc hai luồng đọc)"
    Tên đã nói: một ghi, một đọc. Hai luồng cùng `push` ghi chung một ô và mất phần tử; mình chạy ra treo bốn lần trên năm. Nhiều ghi hoặc nhiều đọc thì dùng mutex hoặc thư viện MPMC.

!!! warning "Lỗi 3: `delete` ngay trong `pop` của cấu trúc lock-free"
    Luồng khác có thể còn đang đọc nút đó. Mình chạy bản ngây thơ: ASan báo `heap-use-after-free`, bản thường sập. Không có chiến lược thu hồi (hazard pointer, epoch, hoặc không xóa) thì đừng tự viết ngăn xếp/hàng đợi nhiều luồng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="62" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Mệnh đề nào mô tả đúng một thuật toán **lock-free**?

- Nhanh hơn bản dùng mutex, vì không còn chi phí xin và nhả khóa
- Không dùng `std::mutex` nên không luồng nào phải thử lại hay chờ ai
- Dù một luồng bị hoãn bao lâu, luôn có luồng khác xong việc sau số bước hữu hạn
- Mọi luồng đều xong thao tác sau số bước hữu hạn, nên không luồng nào bị đói

<p class="giai-thich" markdown>Lock-free là bảo đảm về **tiến lên của cả hệ thống**: luồng bị hoãn không chặn được những luồng còn lại. Nói "mọi luồng đều xong" là định nghĩa của wait-free, mức mạnh hơn; ở lock-free một luồng xui xẻo vẫn có thể thử đi thử lại mãi. Nói "không phải thử lại" sai ngay với vòng CAS, vì thất bại là chuyện thường. Còn "nhanh hơn" không nằm trong định nghĩa: mình đo thấy tranh chấp nặng làm hàng trăm nghìn CAS phải làm lại.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. `x` bắt đầu bằng 1; mỗi luồng trong bốn luồng chạy đúng một lần đoạn này, rồi cả bốn `join`. `x` bằng bao nhiêu?

```text
std::atomic<int> x{1};
// mỗi luồng chạy một lần:
int cu = x.load();
while (!x.compare_exchange_weak(cu, cu * 2)) { }
```

- Đúng 16, vì mỗi luồng nhân đôi đúng một lần và thất bại thì thử lại
- Có thể 2, 4 hoặc 8, vì hai luồng cùng đọc 1 thì cùng ghi 2
- Đúng 8, vì luồng thua cuộc cuối cùng bỏ cuộc thay vì thử lại
- Không xác định, vì nhiều luồng ghi cùng `x` là data race

<p class="giai-thich" markdown>Mỗi vòng so sánh `x` với `cu` rồi mới đổi, trong một nhịp. Hai luồng cùng đọc 1 thì chỉ một luồng đổi được thành 2; luồng kia thất bại, `cu` được cập nhật thành 2 và nó nhân đôi thành 4. Không lần nhân nào bị mất, nên kết quả đúng 16. Kịch bản "cùng ghi 2" chỉ xảy ra với `x = x * 2` viết bằng `load` rồi `store` rời nhau. Vòng lặp không bỏ cuộc, và `atomic` nên không có data race.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc kịch bản sau trên ngăn xếp Treiber **không** có thẻ phiên bản. Điều nào đúng?

```text
ngăn xếp (đỉnh trước): A -> B -> C
luồng 1: cu = A, tiep = B           (rồi bị hoãn)
luồng 2: pop (lấy A), pop (lấy B), push A (lại đúng nút A)
luồng 1: CAS(dau, cu, tiep)         // đổi đầu từ A sang B
```

- CAS thất bại, vì ngăn xếp đã bị luồng 2 sửa đổi khá nhiều
- CAS thất bại, vì nút A đã từng bị lấy ra khỏi ngăn xếp
- CAS thành công và ngăn xếp còn đúng một phần tử là C
- CAS thành công, và đầu ngăn xếp trỏ vào B đã bị lấy ra

<p class="giai-thich" markdown>CAS chỉ so `dau` với `A`, và `dau` đang đúng là `A` (nút được đẩy lại), nên nó thành công mà không biết gì về chuyện giữa chừng. Đầu thành `B`: phần tử đã bị luồng 2 lấy "sống lại", còn nút A vừa đẩy bị mất khỏi ngăn xếp. Đó là ABA. Nói CAS thất bại vì ngăn xếp "đã bị sửa" nhầm CAS với việc kiểm phiên bản: không có thẻ thì giá trị quay về y như cũ là đủ để qua mặt nó. Còn "chỉ còn C" là kết quả mà thuật toán đúng mong muốn, không phải cái đã xảy ra.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Một luồng nhận gói từ mạng và đẩy sang đúng một luồng xử lý, vài chục nghìn gói mỗi giây. Hàng đợi `mutex` + `condition_variable` đang chạy đúng, và công cụ đo cho thấy nó không phải nút cổ chai. Nên làm gì?

- Thay ngay bằng SPSC lock-free, vì đúng một luồng ghi và một luồng đọc
- Giữ hàng đợi hiện tại; chỉ cân nhắc SPSC nếu đo ra khóa là điểm nghẽn
- Viết hàng đợi lock-free dùng CAS để dùng lại được cho mọi bài toán sau
- Bỏ khóa và dùng `std::queue` thường, vì chỉ có hai luồng đụng vào nó

<p class="giai-thich" markdown>Cái gì đúng và đã đo là không nghẽn thì chưa có lý do đổi: lock-free thêm rủi ro (thứ tự bộ nhớ, SPSC không biết chờ ngủ) mà chưa mua được gì. SPSC hấp dẫn vì đúng ràng buộc một ghi một đọc, nhưng "hợp ràng buộc" chưa phải "cần". Viết CAS tổng quát để dùng lại là đi vào vùng khó nhất (ABA, thu hồi bộ nhớ). Và `std::queue` thường mà hai luồng cùng sửa là data race, hai luồng không làm nó an toàn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc hai nửa của hàng đợi SPSC. Theo chuẩn C++, đoạn này có vấn đề gì?

```text
// luồng ghi
buf_[duoi] = v;
duoi_.store(ke, std::memory_order_relaxed);

// luồng đọc
if (dau == duoi_.load(std::memory_order_acquire)) return false;
ra = buf_[dau];
```

- Không có vấn đề: `acquire` ở luồng đọc đã đủ để thấy dữ liệu trong `buf_`
- `duoi_` không còn nguyên tử, nên hai luồng đụng nhau ngay trên chính `duoi_`
- Việc ghi `buf_` không được bảo đảm hiện ra trước chỉ số mới, nên đọc `buf_` là data race
- Không có vấn đề trên x86, vì x86 không đổi thứ tự hai lệnh ghi nên chuẩn cũng cho phép

<p class="giai-thich" markdown>`acquire` chỉ có tác dụng khi nó đọc đúng giá trị do một `release` ghi; ở đây bên ghi dùng `relaxed`, nên không có cầu nối và việc ghi `buf_` không được xếp trước chỉ số mới. Mình chạy đúng bản này: TSan báo data race, mã thoát 66. `relaxed` vẫn nguyên tử, nên nhận định về `duoi_` sai. "Đúng trên x86" là lỗi nghĩ kinh điển: chuẩn không dựa vào phần cứng, trình biên dịch cũng được sắp xếp lại, và mình thấy bản này chạy đúng 60 lần mà vẫn sai.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Vì sao hàng đợi SPSC đặt `alignas(64)` cho cả `dau_` lẫn `duoi_`?

- Để hai chỉ số ở hai dòng cache khác nhau, hai luồng khỏi làm nhau nạp lại dòng
- Để mỗi lần `store` trở thành nguyên tử, vì atomic cần địa chỉ chia hết cho 64
- Để luồng đọc thấy dữ liệu trong `buf_` ngay khi `duoi_` đổi, thay cho `release`
- Để `atomic<size_t>` trở thành lock-free, vì nếu không thì nó dùng khóa ngầm

<p class="giai-thich" markdown>`dau_` do luồng đọc ghi, `duoi_` do luồng ghi ghi: khác biến nhưng nếu chung dòng cache thì các lõi chuyền dòng qua lại (false sharing). Căn lề 64 tách chúng ra hai dòng. Tính nguyên tử không đến từ căn lề 64 (kiểu 8 byte vốn đã nguyên tử khi căn theo 8), và `alignas` không thay được `release`/`acquire` trong việc bảo đảm thứ tự. Và `atomic<size_t>` vốn đã `is_lock_free()` ở máy mình, không cần căn lề 64 mới được vậy. Mình đo lợi ích này không đều, nên phải đo trên máy thật.</p>
</div>


</div>

## 🔑 Tóm tắt

1. Ba mức bảo đảm tiến lên: **có chặn** (luồng giữ khóa bị hoãn thì cả đám chờ), **lock-free** (luôn có ít nhất một luồng xong sau số bước hữu hạn, dù luồng khác bị hoãn; một luồng vẫn có thể bị đói), **wait-free** (mọi luồng xong sau số bước hữu hạn). Spinlock vẫn là có chặn; `is_lock_free()` chỉ hỏi kiểu atomic có chạy bằng lệnh CPU không.
2. Vòng CAS: đọc, tính từ `cu` (không tác dụng phụ), `compare_exchange_weak` trong vòng lặp; thất bại vì giá trị đã khác nghĩa là có luồng khác thành công nên lock-free nhưng chưa wait-free (mình chạy: mất 106393 đến 197989 lần thử lại trên 400000 lần cập nhật). CAS chỉ so **giá trị** và chỉ một ô.
3. Ngăn xếp Treiber ngây thơ hỏng: `delete` trong `pop` làm luồng khác đọc `cu->tiep` đã xóa (ASan báo `heap-use-after-free`, bản thường sập), không `delete` thì rò (3200000 byte). ABA: địa chỉ bị lấy ra rồi cấp lại, CAS thấy "vẫn là A"; mình chạy lại từng bước, phần tử 20 sống lại, và thẻ phiên bản chặn được. Hazard pointer và epoch là cách thu hồi bộ nhớ đúng.
4. Hàng đợi vòng SPSC: `dau_` chỉ luồng đọc sửa, `duoi_` chỉ luồng ghi sửa; ghi dữ liệu rồi `store(release)` chỉ số, nhận bằng `load(acquire)`, chứa tối đa N − 1. Mình chạy đúng thứ tự và tổng, TSan sạch; đổi bất kỳ `release`/`acquire` nào thành `relaxed` thì TSan báo data race (dù x86 vẫn chạy đúng), hai luồng ghi thì hỏng (treo 4 trong 5 lần).
5. `alignas(64)` cho hai chỉ số đúng về nguyên lý nhưng mình đo không đều (khoảng 2 lần ở bốn trong tám lần chạy `-O2`, không lợi ở không tối ưu); SPSC nhanh hơn hàng đợi mutex 10 đến 20 lần trong bài đo. Vẫn: viết lock-free khó đúng và khó kiểm thử, nên mặc định dùng mutex, chỉ SPSC (hoặc thư viện đã kiểm chứng) khi đã đo thấy khóa là nút cổ chai.
