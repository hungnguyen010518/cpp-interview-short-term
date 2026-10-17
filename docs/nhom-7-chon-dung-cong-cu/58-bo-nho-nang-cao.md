# Bài 58 — Bộ nhớ nâng cao: căn lề, padding, cache line, placement new, memory pool

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dự đoán đúng `sizeof` của một `struct` (căn lề, padding), sắp lại thành viên để nhỏ hơn, và nói được khi nào việc đó không đáng làm; hiểu `alignas`, dòng cache 64 byte và vì sao nó nối với false sharing ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)).
    - Dùng **placement new** (dựng đối tượng vào chỗ nhớ có sẵn) và gọi hàm hủy bằng tay; thay `operator new` toàn chương trình để **đếm** số lần cấp phát.
    - Tự viết được **arena** (cấp tuyến tính, thả cả vùng một lần) và **object pool** (danh sách ô rảnh), biết `std::pmr::monotonic_buffer_resource` là bản chuẩn của arena.
    - Giải thích vì sao `new`/`malloc` chậm với hàng triệu đối tượng nhỏ, chọn giữa arena, pool, `reserve` hay "đừng làm gì", và trả lời câu "tự viết memory pool".

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, heap, hàm tạo/hủy), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, `malloc`), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`= delete`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`noexcept`, `std::forward` chỉ nêu tên), [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md) (SSO), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (dòng cache, false sharing, `alignas`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (template), [Bài 45](../nhom-5-he-thong-quy-trinh/45-database-sdlc-game.md) (object pool cỡ cố định, AoS/SoA).

## 🧠 Câu chuyện mở đầu

Người phỏng vấn viết lên bảng `struct { char a; int b; char c; }` và hỏi: "`sizeof` bao nhiêu?". Bạn nói 6. Ông ấy mỉm cười: "Là 12. Giờ đổi thứ tự khai báo thì sao?". Rồi tới câu thứ hai: "Hệ thống của chúng tôi tạo mười triệu đối tượng nhỏ mỗi giây và `new` đang là điểm nghẽn. Bạn tự viết một memory pool đi."

Quay lại **nhà bếp**. **Kho** là heap ([Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md)), và `new` là anh **thủ kho**: mỗi lần đầu bếp xin một gói hành, anh phải tìm ngăn trống vừa cỡ, ghi sổ, dán nhãn rồi mới đưa. Xin một triệu gói lẻ thì anh làm một triệu lần như thế. Cách của bếp giỏi: xin **một cái bàn dài** (arena) rồi tự đặt dần, hoặc dựng **bộ đĩa chuẩn** (pool) rửa xong là dùng lại. Còn bài toán `sizeof` là chuyện **khay có ô cỡ cố định**: món nhỏ vẫn chiếm trọn ô, ô trống chèn giữa là **padding**.

!!! info "Chỗ nào ví von nhà bếp không còn đúng?"
    CPU không lấy từng gói mà bê **nguyên một khay 64 ô** (dòng cache) mỗi lần; và ô trống (padding) vẫn nằm trong `sizeof`, còn trong bếp thật chẳng ai tính tiền ô trống.

## 📖 Giải thích

### 1. Căn lề và padding: vì sao `sizeof` không bằng tổng

**Căn lề (alignment)**: toán tử `alignof(T)` cho một con số, và đối tượng kiểu `T` phải nằm ở địa chỉ chia hết cho số đó (thường bằng cỡ kiểu: `int` là 4, `double` là 8, `char` là 1). CPU đọc nhanh khi số không vắt ngang ranh giới; đặt lệch thì chuẩn C++ coi là hành vi không xác định (mục 3 sẽ thấy UBSan bắt).

Thêm `offsetof(Kieu, thanhVien)` (trong `<cstddef>`): khoảng cách từ đầu đối tượng tới thành viên, tính bằng byte. Ba quy tắc mà các trình biên dịch thông dụng đều làm, ta kiểm bằng chương trình:

- Mỗi thành viên đặt ở vị trí chia hết cho `alignof` của nó; chỗ trống chèn thêm là **padding** (byte đệm).
- `alignof` của cả `struct` bằng `alignof` lớn nhất trong các thành viên.
- `sizeof` của `struct` được làm tròn lên bội của `alignof` của nó (để mảng các `struct` đặt liền nhau vẫn đúng căn lề).

Chuẩn chỉ bảo đảm thành viên nằm theo thứ tự khai báo và mọi thứ đều đúng căn lề; **lượng padding cụ thể là chuyện của từng trình biên dịch và máy**.

```cpp
#include <cstddef>
#include <iostream>

struct Rong {          // thứ tự "tự nhiên": theo ý nghĩa
    char loai;         // (1)
    double gia;        // (2)
    char coHang;       // (3)
    int soLuong;       // (4)
};

struct Gon {           // cùng bốn thành viên, xếp từ lớn xuống nhỏ
    double gia;
    int soLuong;
    char loai;
    char coHang;
};

struct alignas(64) Khay {      // (5) đòi địa chỉ chia hết cho 64
    int dem;
};

int main() {
    std::cout << "alignof: char " << alignof(char) << ", int " << alignof(int)
              << ", double " << alignof(double) << "\n";
    std::cout << "Rong: sizeof " << sizeof(Rong) << ", alignof " << alignof(Rong)
              << ", offset loai/gia/coHang/soLuong = " << offsetof(Rong, loai) << "/"
              << offsetof(Rong, gia) << "/" << offsetof(Rong, coHang) << "/"
              << offsetof(Rong, soLuong) << "\n";
    std::cout << "Gon:  sizeof " << sizeof(Gon) << ", alignof " << alignof(Gon)
              << ", offset gia/soLuong/loai/coHang = " << offsetof(Gon, gia) << "/"
              << offsetof(Gon, soLuong) << "/" << offsetof(Gon, loai) << "/"
              << offsetof(Gon, coHang) << "\n";
    std::cout << "Khay: sizeof " << sizeof(Khay) << ", alignof " << alignof(Khay) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `loai` (1 byte) đặt ở vị trí 0 | `[loai]` |
| (2) | `double` cần vị trí chia hết cho 8: máy chèn 7 byte đệm, `gia` ở vị trí 8 | `[loai][đệm 7][gia 8 byte]` |
| (3), (4) | `coHang` ở 16; `int` cần chia hết cho 4 nên chèn 3 byte đệm, `soLuong` ở 20; cuối cùng 24 đã chia hết cho 8 | `...[coHang][đệm 3][soLuong 4]` = 24 |
| `Gon` | Xếp lớn trước: `gia` 0, `soLuong` 8, `loai` 12, `coHang` 13, còn 2 byte đệm cuối để tròn tới 16 | `[gia 8][soLuong 4][loai][coHang][đệm 2]` = 16 |
| (5) | `alignas(64)` kéo `alignof` lên 64 nên `sizeof` cũng tròn lên 64: một `int` 4 byte chiếm trọn một dòng cache | 4 byte dùng, 60 byte đệm |

**Kết quả khi chạy** (g++ 11, máy 64 bit; chuẩn không bảo đảm các số này, máy khác có thể ra khác):

```text
alignof: char 1, int 4, double 8
Rong: sizeof 24, alignof 8, offset loai/gia/coHang/soLuong = 0/8/16/20
Gon:  sizeof 16, alignof 8, offset gia/soLuong/loai/coHang = 0/8/12/13
Khay: sizeof 64, alignof 64
```

Cùng bốn thành viên, chỉ đổi thứ tự khai báo, nhỏ đi **một phần ba** (24 xuống 16). Mảng một triệu `Rong` tốn 24 MB, mảng `Gon` tốn 16 MB.

**Thử thay đổi: đổi `double gia` thành `float gia` ở cả hai `struct`.** Mình đã chạy: `Rong` còn 16 (`alignof` 4, offset 0/4/8/12) và `Gon` còn 12 (offset 0/4/8/9). Căn lề đổi theo thành viên lớn nhất, nên đổi một kiểu là đổi cả bố cục.

!!! warning "Hay nhầm"
    `sizeof` của `struct` **không** phải tổng cỡ các thành viên (`1 + 8 + 1 + 4 = 14`, nhưng thật là 24). Vì padding tùy máy, **đừng** ghi thẳng `struct` thô xuống tệp hay gửi qua mạng rồi đọc lại ở máy khác; hãy ghi từng trường.

!!! info "Bạn biết Go?"
    Go có cùng luật: mình dựng bản Go với `bool`, `float64`, `bool`, `int32` thì `unsafe.Sizeof` ra 24 theo thứ tự đó và 16 khi xếp `float64`, `int32`, `bool`, `bool` (go 1.27.2). Công cụ phân tích `fieldalignment` của Go khuyên sắp lại trường vì cùng lý do. Khác: Go không có placement new hay `operator new` để bạn thay, vì bộ nhớ do runtime và bộ gom rác lo.

**Khi nào KHÔNG cần sắp lại thành viên:** chỉ có vài trăm đối tượng (tiết kiệm vài KB, không đo được), thứ tự theo ý nghĩa giúp người đọc hơn, hoặc `struct` là một phần giao diện nhị phân với thư viện khác. Chỉ đáng làm khi có **rất nhiều** đối tượng cùng loại.

### 2. Dòng cache, `alignas` và AoS/SoA

[Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) đã nói: CPU bê **dòng cache** 64 byte (phổ biến, không bắt buộc) từ RAM vào bộ nhớ đệm. Hệ quả cho bài này có hai chiều. Một: `struct` càng nhỏ thì càng nhiều đối tượng nằm chung một dòng, nên quét mảng càng ít phải bê dòng mới (`Gon` 16 byte: 4 cái một dòng; `Rong` 24 byte: khoảng 2,7 cái một dòng, và có cái vắt ngang hai dòng). Hai: muốn **tách** hai biến sang hai dòng khác nhau thì đặt `alignas(64)`, như `Khay` ở trên. Đó là thuốc chữa false sharing, và cũng là cái giá: 4 byte dữ liệu mà tốn 64.

**AoS và SoA** ([Bài 45](../nhom-5-he-thong-quy-trinh/45-database-sdlc-game.md) đã đo thật) là cùng một ý ở quy mô mảng. Hạt có 8 số `float` (32 byte). Mảng các hạt (AoS) mà chỉ đọc `x`: một triệu hạt kéo 1.000.000 × 32 / 64 = **500.000 dòng**. Mảng riêng cho `x` (SoA): 1.000.000 × 4 / 64 = **62.500 dòng**, ít hơn 8 lần. Nhưng nếu mỗi vòng đều dùng **cả 8 trường** của từng hạt thì AoS giữ chúng sát nhau và tốt hơn.

### 3. Placement new: dựng đối tượng vào chỗ có sẵn

[Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) nói `new` làm **hai việc**: xin chỗ ở heap, rồi chạy hàm tạo. **Placement new** tách hai việc: bạn đưa sẵn một địa chỉ, nó **chỉ chạy hàm tạo** tại đó, không xin gì thêm. Cú pháp `new (diaChi) T(đối số...)`, cần `#include <new>`. Vì không có `delete` tương ứng, bạn phải gọi **hàm hủy bằng tay**: `p->~T();`. Chỗ nhớ thì không bị trả đi đâu; nó vẫn là của bạn và dùng lại được.

Chỗ nhớ phải đủ lớn (`sizeof(T)`) và đúng căn lề (`alignas(T)`). Ta dùng mảng `unsigned char` (một ô một byte, cách thông dụng để nói "bytes thô") làm vùng.

```cpp
#include <iostream>
#include <new>
#include <string>
#include <utility>

struct Mon {
    std::string ten;
    int gia;
    Mon(std::string t, int g) : ten(std::move(t)), gia(g) {
        std::cout << "tao " << ten << "\n";
    }
    ~Mon() { std::cout << "huy " << ten << "\n"; }
};

int main() {
    alignas(Mon) unsigned char vung[sizeof(Mon)];          // (1) chỗ nhớ thô, chưa có Mon nào
    std::cout << "da co vung, chua co Mon nao\n";
    Mon* p = new (vung) Mon("pho", 50000);                 // (2) chạy hàm tạo ngay tại vung
    std::cout << "p == vung ? " << (static_cast<void*>(p) == static_cast<void*>(vung)) << "\n";
    std::cout << p->ten << " " << p->gia << "\n";
    p->~Mon();                                             // (3) hủy bằng tay; vung vẫn còn
    std::cout << "da huy, vung van con\n";
    p = new (vung) Mon("bun", 45000);                      // (4) dùng lại đúng chỗ đó
    std::cout << p->ten << " " << p->gia << "\n";
    p->~Mon();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Mảng byte trên stack, đúng cỡ và căn lề của `Mon`; **không** chạy hàm tạo nào | `vung: [byte rác ...]` |
| (2) | Hàm tạo chạy tại `vung`; in `tao pho`; `p` bằng chính địa chỉ `vung` | `vung: [Mon "pho"]` |
| (3) | `~Mon()` chạy, in `huy pho`; byte vẫn nằm đó nhưng không còn là `Mon` sống | `vung: [byte rác]` |
| (4) | Dựng `Mon` mới đè lên chỗ cũ | `vung: [Mon "bun"]` |

**Kết quả khi chạy:**

```text
da co vung, chua co Mon nao
tao pho
p == vung ? 1
pho 50000
huy pho
da huy, vung van con
tao bun
bun 45000
huy bun
```

**Thử thay đổi 1: quên hàm hủy.** Mình đã chạy hai bản. Bỏ cả hai lệnh `p->~Mon()` với tên ngắn thì chỉ thấy các dòng `huy ...` biến mất. Bỏ cả hai và đổi `"pho"` thành chuỗi 34 ký tự (vượt ngưỡng SSO của g++ 11), biên dịch với `-fsanitize=address`: LeakSanitizer báo `Direct leak of 35 byte(s)`. Lý do: `Mon` thứ hai dựng đè lên `Mon` thứ nhất chưa hủy, nên khối heap của chuỗi đầu không còn con trỏ nào trỏ tới. (Nó chỉ báo khi khối thật sự mất dấu; quên hàm hủy mà con trỏ còn nằm đâu đó thì LeakSanitizer vẫn im, nên đừng coi nó im là yên tâm.)

**Thử thay đổi 2: để `vung` lệch** (`unsigned char vung[sizeof(Mon) + 1]`, dựng tại `vung + 1`). Mình chạy với `-fsanitize=undefined`: `runtime error: constructor call on misaligned address ... which requires 8 byte alignment`. Chỗ nhớ phải đúng căn lề, không chỉ đủ lớn.

Bạn không thấy placement new hằng ngày nhưng nó nằm dưới mọi container: `std::vector` xin một khối byte cho `capacity` phần tử rồi **dựng từng phần tử** đúng lúc `push_back`; phần dư của khối chưa có đối tượng nào sống. Pool và arena ở dưới là cùng một ý.

### 4. `operator new` tự định nghĩa: đếm số lần cấp phát

Biểu thức `new T(...)` gọi một hàm tên **`operator new`**, nhận số byte cần xin, để làm việc "xin chỗ" (`delete` gọi `operator delete` tương ứng), rồi chạy hàm tạo. Bạn được phép **thay** hàm đó cho cả chương trình bằng cách tự định nghĩa nó. Ta chỉ làm một việc vô hại: **đếm** số lần xin, rồi giao việc thật cho `std::malloc`/`std::free` ([Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md)). Mọi thứ cấp phát bằng `new` trong chương trình, kể cả bên trong `std::string` và `std::vector`, đi qua hàm này (trừ kiểu đòi căn lề đặc biệt, đi qua một dạng khác của `operator new`).

```cpp
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <vector>

std::size_t soLanXin = 0;                       // (1) bộ đếm toàn cục

void* operator new(std::size_t n) {             // (2) thay "thủ kho" mặc định
    ++soLanXin;
    void* p = std::malloc(n);
    if (p == nullptr) throw std::bad_alloc();
    return p;
}

void operator delete(void* p) noexcept {        // (3) cặp đôi: phải thay cùng
    std::free(p);
}

void operator delete(void* p, std::size_t) noexcept {   // (4) bản có kích thước (C++14)
    std::free(p);
}

int main() {
    std::size_t truoc = soLanXin;
    std::string ngan = "abc";                               // (5)
    std::cout << "string 3 ky tu:  " << soLanXin - truoc << " lan xin\n";

    truoc = soLanXin;
    std::string dai(40, 'x');                               // (6)
    std::cout << "string 40 ky tu: " << soLanXin - truoc << " lan xin\n";

    truoc = soLanXin;
    std::vector<int> a;
    for (int i = 0; i < 100; ++i) a.push_back(i);           // (7)
    std::cout << "vector 100 push_back: " << soLanXin - truoc << " lan xin\n";

    truoc = soLanXin;
    std::vector<int> b;
    b.reserve(100);
    for (int i = 0; i < 100; ++i) b.push_back(i);           // (8)
    std::cout << "vector reserve(100): " << soLanXin - truoc << " lan xin\n";

    std::cout << "sizeof(string)=" << sizeof(std::string)
              << " sizeof(vector<int>)=" << sizeof(std::vector<int>) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ đếm |
|---|---|---|
| (5) | Chuỗi 3 ký tự nằm ngay trong đối tượng `std::string` (SSO, [Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md)), không gọi `operator new` | tăng 0 |
| (6) | 40 ký tự không vừa chỗ trong đối tượng, chữ phải ở heap: một lần xin | tăng 1 |
| (7) | `vector` đầy thì xin khối lớn gấp đôi rồi chuyển phần tử qua: 1, 2, 4, ..., 128 phần tử | tăng 8 |
| (8) | `reserve(100)` xin đủ chỗ một lần, `push_back` không xin thêm | tăng 1 |

**Kết quả khi chạy:**

```text
string 3 ky tu:  0 lan xin
string 40 ky tu: 1 lan xin
vector 100 push_back: 8 lan xin
vector reserve(100): 1 lan xin
sizeof(string)=32 sizeof(vector<int>)=24
```

Số lần xin là kết quả của g++ 11 (cách `vector` tăng dung lượng và ngưỡng SSO đều là chuyện cài đặt); quy luật mới đáng nhớ: **SSO tránh được lần xin cho chuỗi ngắn, `reserve` biến tám lần xin thành một.** `sizeof(std::string)` là 32, trong đó có sẵn vùng cho chuỗi ngắn: ý tưởng chung gọi là **small-buffer optimization** (chừa một vùng nhỏ trong chính đối tượng để khỏi xin heap).

**Thử thay đổi: đổi `"abc"` thành chuỗi 15 ký tự, rồi 16 ký tự.** Mình đã chạy: 15 ký tự vẫn **0** lần xin, 16 ký tự thì **1** lần. Ngưỡng SSO của g++ 11 là 15 ký tự; thư viện khác có thể cho số khác.

Khi thay `operator new` thật: thay **cả cặp** `delete`; bộ đếm dùng từ nhiều luồng phải là `std::atomic` (bản này chỉ đúng cho một luồng); và thường chỉ thay theo **từng lớp** (khai báo `operator new` thành hàm thành viên của lớp) thay vì cả chương trình.

### 5. Vì sao `new`/`malloc` chậm với hàng triệu đối tượng nhỏ

Mỗi lần `new` (qua `malloc`), thủ kho điển hình làm mấy việc mà đối tượng nhỏ không đáng chịu (chi tiết tùy bộ cấp phát):

- **Tìm chỗ:** duyệt danh sách ô trống để chọn ô vừa cỡ, rồi ghi sổ. `delete` lại cập nhật sổ.
- **Phụ phí mỗi khối:** mỗi khối mang theo thông tin quản lý. Mình đo ở Ví dụ 3: `Nut` 16 byte, hai `Nut` xin liên tiếp bằng `new` cách nhau **32 byte** (trên glibc, máy mình); trong arena chỉ cách nhau 16.
- **Rải rác:** các khối xin ở các thời điểm khác nhau có thể nằm xa nhau, nên duyệt chúng làm CPU phải bê nhiều dòng cache.
- **Phân mảnh (fragmentation):** xin và trả nhiều khối cỡ khác nhau để lại **lỗ trống** nằm xen giữa các khối đang sống.

```text
heap sau khi trả một nửa khối:  [A][ ][C][ ][E][ ][G][ ]      (ô trống = 1 khối)
tổng chỗ trống = 4 khối, nhưng xin 1 khối gấp đôi: KHÔNG có chỗ liền nhau
(phân mảnh ngoài; còn phân mảnh trong là khối được làm tròn lên to hơn cỡ xin)
```

Mình không dựng chương trình đo phân mảnh (nó đổi theo thuật toán và lịch sử cấp phát); sơ đồ chỉ để hiểu cơ chế. Arena và pool tránh gần cả bốn thứ: cấp phát là cộng con trỏ hoặc lấy đầu danh sách, không phụ phí mỗi khối, đối tượng nằm sát nhau.

### 6. Arena và pool: hai cách khác nhau, hai lúc dùng khác nhau

| | **Arena** (cấp tuyến tính) | **Object pool** (danh sách ô rảnh) |
|---|---|---|
| Cách làm | Một khối lớn, một "con trỏ cắt" chạy tới; xin = cộng con trỏ | Mảng ô cùng cỡ; ô rảnh nối thành danh sách; xin = lấy đầu, trả = đưa về đầu |
| Trả lẻ từng đối tượng | **Không**, chỉ thả cả vùng một lần | Có, O(1) |
| Cỡ đối tượng | Tùy ý | Cố định (một loại `T`) |
| Hợp với | Cả cụm đối tượng **cùng sinh, cùng chết** (một yêu cầu, một khung hình, một lần phân tích cú pháp) | Đối tượng cùng loại tạo và hủy **lẻ tẻ liên tục**, vòng đời khác nhau (kết nối, hạt, gói tin) |
| Hàm hủy | Không gọi (chỉ cho kiểu không có gì phải dọn khi hủy) | Gọi tay khi trả |

Cả hai có chung giới hạn: **đa luồng** thì phải đồng bộ (mutex, hoặc mỗi luồng một cái riêng; hướng này Bài 61 nói tới), và **ASan không bắt được** lỗi dùng ô sau khi trả vì với ASan cả vùng vẫn là một khối đang sống (Ví dụ 2 cho thấy).

### 7. `std::pmr`: arena có sẵn trong thư viện chuẩn (C++17)

Bạn không phải tự viết arena. `<memory_resource>` có `std::pmr::monotonic_buffer_resource`: đưa nó một vùng byte, nó cắt dần cho ai xin; **trả lẻ không làm gì**, hủy nó thì cả vùng được thả; hết vùng thì xin thêm từ "nguồn cấp trên" (mặc định là `new`/`delete` thường). Container dùng nó qua `std::pmr::vector`, `std::pmr::string`: giống bản thường nhưng nhận một **allocator** (thứ container hỏi mỗi khi cần bộ nhớ). Mình kiểm `g++ 11` + `-std=c++17` biên dịch được (Ví dụ 4).

### 8. Bảng chọn, và khi nào KHÔNG làm gì cả

| Triệu chứng đo được | Làm gì |
|---|---|
| `vector` tăng dần, nhiều lần xin | `reserve` ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)) |
| Hàng triệu đối tượng nhỏ, cùng sinh cùng chết | Arena (tự viết hoặc `pmr::monotonic_buffer_resource`) |
| Đối tượng cùng loại tạo/hủy liên tục, chết không cùng lúc | Object pool |
| Quét mảng lớn, chỉ đụng vài trường | Cân nhắc SoA (mục 2) |
| Hai luồng ghi hai biến cạnh nhau, chậm | `alignas(64)` tách dòng ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)) |
| Mọi thứ khác | **Không làm gì**: dùng `vector`, `make_unique`, `new` thường |

Thứ tự tự bảo vệ: **đo trước** (profiler, [Bài 42](../nhom-5-he-thong-quy-trinh/42-strace-perf-do-hieu-nang.md)), thử `reserve` và sắp lại `struct` (rẻ, ít rủi ro), rồi mới tới arena/pool. Nếu `new` chiếm vài phần trăm thời gian, một cái pool tự viết chỉ thêm bug (mất ASan, mất an toàn luồng) mà không đổi được gì.

## 💻 Ví dụ code

### Ví dụ 1: arena (cấp tuyến tính)

Hàm `xin(soByte, canLe)` cộng con trỏ cắt `dung_` lên, nhưng trước đó nhảy qua vài byte để địa chỉ chia hết cho `canLe` (ví dụ địa chỉ 1001, `canLe` 8: 1001 % 8 = 1, nhảy 8 - 1 = 7 byte). `tao<T>(đối số...)` xin chỗ rồi dựng `T` bằng placement new. Bốn thứ mới:

- `reinterpret_cast<...>(con trỏ)`: đổi kiểu của địa chỉ mà không đổi byte nào.
- `std::uintptr_t` (`<cstdint>`): số nguyên đủ lớn chứa một địa chỉ, nên làm phép `%` được.
- `static_assert(điều kiện, "lời nhắn")` ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)) bắt trình biên dịch dừng kèm lời nhắn nếu điều kiện sai; `std::is_trivially_destructible<T>::value` (`<type_traits>`) là `true` khi hủy `T` không có việc gì phải làm (như `int`, `double`, struct chỉ chứa số), `false` với `std::string`.
- `template <typename T, typename... Args>` với `Args&&... args` và `std::forward`: cách thư viện (như `emplace_back`) nhận **bao nhiêu đối số cũng được** và chuyển nguyên vẹn cho hàm tạo. Bạn chỉ cần đọc: `tao<Nut>(i, p)` là "dựng `Nut(i, p)` trong arena".

```cpp
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <new>
#include <type_traits>
#include <utility>

class Arena {
public:
    explicit Arena(std::size_t dungLuong)
        : dau_(new unsigned char[dungLuong]), dungLuong_(dungLuong) {}   // (1) xin MỘT khối
    ~Arena() { delete[] dau_; }
    Arena(const Arena&) = delete;                    // (2) không cho sao chép
    Arena& operator=(const Arena&) = delete;

    void* xin(std::size_t soByte, std::size_t canLe) {
        std::uintptr_t diaChi = reinterpret_cast<std::uintptr_t>(dau_) + dung_;   // (3)
        std::size_t lech = (canLe - diaChi % canLe) % canLe;                      // (4)
        if (dung_ + lech + soByte > dungLuong_) return nullptr;                   // (5)
        void* cho = dau_ + dung_ + lech;
        dung_ += lech + soByte;                                                   // (6)
        return cho;
    }

    template <typename T, typename... Args>
    T* tao(Args&&... args) {                                                      // (7)
        static_assert(std::is_trivially_destructible<T>::value, "arena khong goi ham huy");
        void* cho = xin(sizeof(T), alignof(T));
        if (cho == nullptr) return nullptr;
        return new (cho) T(std::forward<Args>(args)...);                          // (8)
    }

    void thaCaVung() { dung_ = 0; }                  // (9)
    std::size_t daDung() const { return dung_; }

private:
    unsigned char* dau_;
    std::size_t dungLuong_;
    std::size_t dung_ = 0;
};

struct Nut {
    int giaTri;
    Nut* tiep;
    Nut(int g, Nut* t) : giaTri(g), tiep(t) {}
};

int main() {
    Arena arena(1024);
    arena.tao<char>('x');                            // 1 byte
    std::cout << "sau char:   da dung " << arena.daDung() << "\n";
    double* d = arena.tao<double>(2.5);              // phải nhảy tới địa chỉ chia hết cho 8
    std::cout << "sau double: da dung " << arena.daDung() << ", dia chi % 8 = "
              << reinterpret_cast<std::uintptr_t>(d) % 8 << "\n";

    Nut* dauDS = nullptr;
    for (int i = 0; i < 10; ++i) dauDS = arena.tao<Nut>(i, dauDS);   // 10 nút, không new nào nữa
    long tong = 0;
    for (Nut* n = dauDS; n != nullptr; n = n->tiep) tong += n->giaTri;
    std::cout << "tong 0..9 = " << tong << ", da dung " << arena.daDung() << "\n";

    arena.thaCaVung();                               // thả tất cả một lần
    std::cout << "sau tha: da dung " << arena.daDung() << "\n";

    int soNut = 0;
    while (arena.tao<Nut>(0, nullptr) != nullptr) ++soNut;
    std::cout << "nhet duoc " << soNut << " nut roi het cho\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Arena lúc này (1024 byte) |
|---|---|---|
| (1) | Một lần `new unsigned char[1024]`; từ đây không xin heap nữa | `[..........] dung_=0` |
| (3), (4) | Tính địa chỉ cắt hiện tại, rồi số byte `lech` cần nhảy để chia hết `canLe` | |
| (5), (6) | Hết chỗ thì trả `nullptr`; còn thì cộng `lech + soByte` vào `dung_` | |
| `char` rồi `double` | `char` ở 0, `dung_`=1; `double` cần chia hết 8 nên nhảy 7 byte, nằm ở 8, `dung_`=16 | `[x][đệm 7][2.5]` |
| 10 `Nut` | Mỗi `Nut` 16 byte: 16 + 10 × 16 = 176 | `dung_`=176 |
| (9) | Đặt `dung_` về 0: cả vùng coi như trống, **không** chạy hàm hủy nào | `dung_=0` |
| vòng `while` | 1024 / 16 = 64 nút rồi `tao` trả `nullptr` | |

**Kết quả khi chạy** (cũng sạch với ASan và UBSan):

```text
sau char:   da dung 1
sau double: da dung 16, dia chi % 8 = 0
tong 0..9 = 45, da dung 176
sau tha: da dung 0
nhet duoc 64 nut roi het cho
```

**Thử thay đổi: đổi `arena.tao<char>('x')` thành `arena.tao<std::string>("x")`** (thêm `#include <string>`). Mình đã chạy: lỗi biên dịch `static assertion failed: arena khong goi ham huy`. `static_assert` chặn kiểu có việc phải làm khi hủy, vì `thaCaVung` sẽ không chạy hàm hủy của `std::string` và làm rò rỉ phần heap bên trong.

### Ví dụ 2: object pool bằng danh sách ô rảnh

Mỗi **ô** (`union O`) chứa **một trong hai thứ**: lúc rảnh, một con trỏ tới ô rảnh kế tiếp; lúc có người dùng, các byte của một `T`. **`union`** là kiểu mà mọi thành viên **chung một chỗ nhớ** (chỉ một cái dùng được tại một thời điểm), nên ô rảnh tốn thêm đúng 0 byte cho danh sách. Danh sách rảnh nằm **bên trong** các ô rảnh.

```cpp
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <new>
#include <string>
#include <utility>

template <typename T, std::size_t N>
class HoCho {                                         // (1) pool: N ô, mỗi ô vừa một T
public:
    HoCho() {
        for (std::size_t i = 0; i + 1 < N; ++i) o_[i].tiep = &o_[i + 1];   // (2) xâu mọi ô thành danh sách rảnh
        o_[N - 1].tiep = nullptr;
        ranh_ = &o_[0];
    }
    template <typename... Args>
    T* tao(Args&&... args) {
        if (ranh_ == nullptr) return nullptr;         // (3) hết ô
        O* o = ranh_;
        ranh_ = o->tiep;                              // (4) lấy ô đầu danh sách rảnh: O(1)
        ++dangDung_;
        return new (o->bo) T(std::forward<Args>(args)...);   // (5) dựng T vào ô
    }
    void huy(T* p) {
        p->~T();                                      // (6) hủy đối tượng, KHÔNG trả bộ nhớ cho hệ thống
        std::size_t i = (reinterpret_cast<std::uintptr_t>(p)
                         - reinterpret_cast<std::uintptr_t>(o_)) / sizeof(O);   // (7) p nằm ở đầu ô thứ i
        O* o = &o_[i];                                // (8) ô i lấy từ chính mảng; ô này lại rảnh: nối vào đầu danh sách
        o->tiep = ranh_;
        ranh_ = o;
        --dangDung_;
    }
    std::size_t dangDung() const { return dangDung_; }

private:
    union O {                                         // (9) một ô: rảnh thì giữ "ô rảnh kế tiếp",
        O* tiep;                                      //     đang dùng thì giữ T
        alignas(T) unsigned char bo[sizeof(T)];
    };
    O o_[N];
    O* ranh_ = nullptr;
    std::size_t dangDung_ = 0;
};

struct Mon {
    std::string ten;
    int gia;
    Mon(std::string t, int g) : ten(std::move(t)), gia(g) { std::cout << "tao " << ten << "\n"; }
    ~Mon() { std::cout << "huy " << ten << "\n"; }
};

int main() {
    HoCho<Mon, 2> ho;
    Mon* a = ho.tao("pho", 50000);
    Mon* b = ho.tao("bun", 45000);
    std::cout << "dang dung " << ho.dangDung() << ", tao them: "
              << (ho.tao("com", 40000) == nullptr ? "het cho" : "con cho") << "\n";
    void* diaChiA = a;
    ho.huy(a);
    Mon* c = ho.tao("com", 40000);
    std::cout << "com o dung cho cua pho? " << (static_cast<void*>(c) == diaChiA) << "\n";
    std::cout << "dang dung " << ho.dangDung() << "\n";
    ho.huy(b);
    ho.huy(c);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Danh sách rảnh |
|---|---|---|
| (2) | Nối ô 0 -> ô 1 -> `nullptr`; `ranh_` trỏ ô 0 | `ranh_ -> [0] -> [1] -> null` |
| `tao("pho")`, `tao("bun")` | Lấy ô 0 rồi ô 1 (đầu danh sách), dựng `Mon` vào đó (5) | `ranh_ -> null` |
| `tao("com")` thứ nhất | `ranh_` là `nullptr` nên trả `nullptr` ("hết chỗ", ở đây ta chọn không ném lỗi) | không đổi |
| `huy(a)` | Hủy `pho` (6), tính ra `pho` ở ô 0 (7)(8), ô 0 nối vào đầu danh sách | `ranh_ -> [0] -> null` |
| `tao("com")` thứ hai | Lấy ngay ô 0: cùng địa chỉ với `pho` đã hủy | `ranh_ -> null` |

Vì sao (7)(8) không viết gọn `reinterpret_cast<O*>(p)`? Mã pool ngoài đời hay viết vậy, và g++ cho chạy sạch, nhưng chuẩn C++ không bảo đảm: `p` trỏ tới một `T` nằm *trong* ô, chưa chắc được ép thẳng thành con trỏ tới chính `union O` (chuẩn có `std::launder` cho các tình huống gần giống, và điều kiện dùng nó khá chặt). Tính số thứ tự ô từ hiệu địa chỉ rồi lấy `&o_[i]` cho ta một con trỏ ô thật, khỏi phải tranh luận. `std::uintptr_t` đã gặp ở Ví dụ 1.

**Kết quả khi chạy** (ASan, UBSan sạch):

```text
tao pho
tao bun
dang dung 2, tao them: het cho
huy pho
tao com
com o dung cho cua pho? 1
dang dung 2
huy bun
huy com
```

**Thử thay đổi 1: bỏ dòng `p->~T();`.** Mình đã chạy: các dòng `huy ...` biến mất hoàn toàn, chương trình vẫn thoát mã 0. Pool không tự hủy đối tượng; hàm hủy là việc của `huy`.

**Thử thay đổi 2: dùng ô sau khi trả.** Mình dựng `HoCho<Hop, 4>` với `struct Hop { int x; }`, gọi `tao(Hop{7})`, `huy(a)` rồi in `a->x`, biên dịch với `-fsanitize=address`: **ASan im lặng**, chương trình in một số rác (4 byte đầu của ô vừa bị con trỏ `tiep` ghi đè). Với `new`/`delete` thường thì ASan báo `heap-use-after-free`. Đây là cái giá của pool: bạn mất một lớp kiểm tra tự động.

Pool này chỉ an toàn cho **một luồng**: hai luồng cùng gọi `tao` có thể cùng lấy một ô. Muốn đa luồng thì thêm mutex quanh `tao`/`huy` hoặc cho mỗi luồng một pool.

### Ví dụ 3: đo thật arena và `new`/`delete`

500.000 nút, ba vòng. Bên `new`: mỗi vòng xin 500.000 lần rồi trả 500.000 lần. Bên arena: xin **một** khối cho cả ba vòng; mỗi vòng đặt nút bằng placement new vào `kho + dung` và "thả cả vùng" bằng cách đặt `dung` về 0.

```cpp
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <new>
#include <vector>

struct Nut {
    int giaTri;
    Nut* tiep;
    Nut(int g, Nut* t) : giaTri(g), tiep(t) {}
};

using Dong = std::chrono::steady_clock;
double mili(Dong::time_point a, Dong::time_point b) {
    return std::chrono::duration<double, std::milli>(b - a).count();
}

int main() {
    const int N = 500000;
    const int VONG = 3;
    std::vector<Nut*> v(N);                                       // (1) chỗ ghi con trỏ, dùng chung hai bên
    long long tongA = 0, tongB = 0;
    std::intptr_t buocA = 0, buocB = 0;

    auto t0 = Dong::now();
    for (int vong = 0; vong < VONG; ++vong) {
        for (int i = 0; i < N; ++i) v[i] = new Nut(i, nullptr);   // (2) N lần xin heap
        buocA = reinterpret_cast<std::intptr_t>(v[1]) - reinterpret_cast<std::intptr_t>(v[0]);
        for (Nut* n : v) tongA += n->giaTri;
        for (Nut* n : v) delete n;                                // (3) N lần trả
    }
    auto t1 = Dong::now();

    unsigned char* kho = new unsigned char[N * sizeof(Nut)];      // (4) MỘT lần xin
    for (int vong = 0; vong < VONG; ++vong) {
        std::size_t dung = 0;                                     // (5) "con trỏ cắt" của arena
        for (int i = 0; i < N; ++i) {
            v[i] = new (kho + dung) Nut(i, nullptr);
            dung += sizeof(Nut);
        }
        buocB = reinterpret_cast<std::intptr_t>(v[1]) - reinterpret_cast<std::intptr_t>(v[0]);
        for (Nut* n : v) tongB += n->giaTri;
    }                                                             // (6) mỗi vòng "thả cả vùng" = đặt dung về 0
    delete[] kho;
    auto t2 = Dong::now();

    std::cout << "tong: " << tongA << " va " << tongB << "\n";
    std::cout << "sizeof(Nut) = " << sizeof(Nut) << ", hai Nut lien tiep cach nhau: new "
              << buocA << " byte, arena " << buocB << " byte\n";
    std::cout << std::fixed << std::setprecision(1)
              << "arena nhanh hon new/delete khoang " << mili(t0, t1) / mili(t1, t2) << " lan\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số lần gọi thủ kho |
|---|---|---|
| (2), (3) | Mỗi vòng 500.000 `new` rồi 500.000 `delete` | 3 × 1.000.000 |
| (4) | Một lần xin cho cả ba vòng | 1 |
| (5), (6) | `dung` tăng 16 mỗi nút; hết vòng đặt lại 0 | 0 |
| `buocA`, `buocB` | Hiệu địa chỉ hai nút liền nhau: đo phụ phí mỗi khối | |

**Kết quả khi chạy** (một lần, g++ -std=c++17 không tối ưu):

```text
tong: 374999250000 va 374999250000
sizeof(Nut) = 16, hai Nut lien tiep cach nhau: new 32 byte, arena 16 byte
arena nhanh hon new/delete khoang 2.6 lan
```

Hai tổng bằng nhau (cùng việc, chỉ khác chỗ cấp phát). Tỉ lệ thời gian đổi theo máy và cờ biên dịch: mình chạy nhiều lần mỗi cách: không tối ưu ra từ 1,8 tới 5,0 lần; với `-O2` ra từ 3,9 tới 7,8 lần (lúc máy bận thì dao động rộng hơn). Con số 32 byte cách nhau là kết quả của `new` trên glibc; bộ cấp phát khác có thể ra khác.

### Ví dụ 4: `std::pmr::monotonic_buffer_resource`

Ta so địa chỉ dữ liệu của `vector` với đầu và cuối mảng `kho` để biết nó nằm trong `kho` hay đã ra heap. `reinterpret_cast` và `std::uintptr_t` như ở Ví dụ 1.

```cpp
#include <cstdint>
#include <iostream>
#include <memory_resource>
#include <vector>

int main() {
    unsigned char kho[4096];                                         // (1) vùng nhớ có sẵn trên stack
    std::pmr::monotonic_buffer_resource vung(kho, sizeof(kho));      // (2) cắt dần vùng này
    auto k0 = reinterpret_cast<std::uintptr_t>(kho);                 // (3) đầu và cuối vùng, để so địa chỉ
    auto k1 = k0 + sizeof(kho);

    std::pmr::vector<int> v(&vung);                                  // (4) vector lấy bộ nhớ từ vung
    for (int i = 0; i < 100; ++i) v.push_back(i);
    auto d = reinterpret_cast<std::uintptr_t>(v.data());
    std::cout << "100 phan tu: du lieu nam trong kho? " << (d >= k0 && d < k1) << "\n";

    for (int i = 0; i < 2000; ++i) v.push_back(i);                   // (5) vượt quá 4096 byte
    d = reinterpret_cast<std::uintptr_t>(v.data());
    std::cout << "2100 phan tu: du lieu nam trong kho? " << (d >= k0 && d < k1) << "\n";

    long tong = 0;
    for (int x : v) tong += x;
    std::cout << "size = " << v.size() << ", tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Dữ liệu `v` nằm ở |
|---|---|---|
| (1), (2) | `vung` cắt bộ nhớ từ mảng `kho` 4096 byte | |
| (4) | `vector` lớn dần, mỗi khối mới đều cắt từ `kho`; khối cũ **không** được tái dùng | trong `kho` |
| (5) | Khối mới không còn vừa `kho`, `vung` xin thêm từ nguồn cấp trên (heap) | ngoài `kho` |

**Kết quả khi chạy** (ASan, UBSan sạch):

```text
100 phan tu: du lieu nam trong kho? 1
2100 phan tu: du lieu nam trong kho? 0
size = 2100, tong = 2003950
```

**Thử thay đổi: thêm đối số thứ ba `std::pmr::null_memory_resource()` khi dựng `vung`** (nguồn cấp trên không bao giờ cho chỗ). Mình đã chạy: chương trình dừng với `terminate called after throwing an instance of 'std::bad_alloc'`, mã 134. Cách này buộc đường chạy nóng "không được chạm heap".

Hai cái giá của `monotonic`: khối cũ bị bỏ lại mỗi lần `vector` tăng, và `clear`/`erase` không trả chỗ; vòng lặp thêm-xóa vô tận sẽ phình mãi tới khi `vung` bị hủy. Nó hợp với "dựng một lần, dùng, bỏ".

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`struct { char a; int b; char c; }` có `sizeof` bao nhiêu? Làm sao nhỏ hơn?"
    Thường là 12 trên máy 64 bit: `a` ở 0, 3 byte đệm, `b` ở 4, `c` ở 8, rồi 3 byte đệm cuối để `sizeof` tròn lên bội của `alignof` (4). Xếp lại `int b; char a; char c;` thì còn 8. Nói rõ số cụ thể tùy trình biên dịch và máy; quy tắc là xếp từ lớn xuống nhỏ. Và nói khi nào không cần: ít đối tượng, hoặc cần giữ thứ tự cho người đọc hay cho giao diện nhị phân.

??? question "Placement new là gì, khi nào dùng, và vì sao phải gọi hàm hủy bằng tay?"
    `new (diaChi) T(...)` chỉ chạy hàm tạo tại một địa chỉ có sẵn, không xin bộ nhớ. Dùng khi bạn **tự quản lý chỗ nhớ**: pool, arena, container tự viết (như `std::vector` dựng phần tử trong khối đã `reserve`). Vì chỗ nhớ không do `new` cấp nên `delete` không dùng được; gọi `p->~T()` để chạy hàm hủy, còn chỗ nhớ giữ lại. Quên hàm hủy là rò rỉ thứ `T` giữ. Chỗ nhớ phải đủ lớn **và đúng căn lề**.

??? question "Tự viết một memory pool. Bạn làm thế nào?"
    Mô tả hướng trước: (1) chốt phạm vi: pool cho một loại `T` cỡ cố định; (2) xin một khối lớn một lần, `N` ô vừa `T` và đúng `alignof`; (3) nối các ô rảnh thành danh sách nằm **trong** chính ô rảnh; (4) cấp = lấy đầu danh sách rồi placement new, O(1); (5) trả = `~T()` rồi đưa ô về đầu danh sách, O(1); (6) hết ô thì trả `nullptr`, ném lỗi hoặc xin thêm khối. Rồi nêu giới hạn: không an toàn luồng, ASan không bắt lỗi dùng sau khi trả, phải rõ ai gọi hàm hủy. Bản chạy được là Ví dụ 2.

??? question "Vì sao `new` chậm khi tạo hàng triệu đối tượng nhỏ? Arena giải quyết gì?"
    Mỗi lần phải tìm khối trống vừa cỡ và ghi sổ, mỗi khối mang phụ phí quản lý (mình đo: nút 16 byte cách nhau 32), các khối rải rác nên cache kém, xin trả lẫn lộn gây phân mảnh. Arena đổi tất cả lấy một lần cộng con trỏ, đối tượng nằm sát nhau, thả cả vùng một lần; mình đo nhanh cỡ 2 đến 5 lần (không tối ưu) và 4 đến 8 lần (`-O2`) trên máy mình, đổi theo lần chạy. Đổi lại không trả lẻ được và không chạy hàm hủy. `std::pmr::monotonic_buffer_resource` là bản có sẵn trong thư viện chuẩn.

??? question "Thế nếu pool dùng trong chương trình đa luồng thì sao?"
    Danh sách rảnh là dữ liệu chung nên hai luồng cùng `tao` có thể lấy trúng một ô: data race ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)). Hai hướng: một mutex quanh `tao`/`huy` (đơn giản, nhưng thành điểm tranh chấp nếu gọi dồn dập), hoặc mỗi luồng một pool riêng (không tranh chấp, nhưng phải trả đối tượng về đúng pool của nó). Chọn theo số đo.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên hàm hủy sau placement new, hoặc đặt chỗ nhớ lệch căn lề"
    Hàm hủy không tự chạy (mình đã chạy: đè `Mon` thứ hai lên `Mon` thứ nhất chưa hủy, LeakSanitizer báo rò 35 byte với `std::string` dài). Chỗ nhớ thô thì khai báo `alignas(T) unsigned char vung[sizeof(T)]`; thiếu `alignas` hay dựng ở địa chỉ lệch là hành vi không xác định (UBSan báo misaligned).

!!! warning "Lỗi 2: Dùng pool hay arena khi chưa đo"
    Pool tự viết mất ASan (mình đã chạy: dùng ô sau khi trả mà ASan im lặng), mất an toàn luồng, thêm mã phải bảo trì. Nếu `new` chỉ chiếm vài phần trăm thời gian, bạn thêm bug mà không đổi được gì. Thứ tự: đo, `reserve`, sắp lại `struct`, rồi mới pool/arena.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="58" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc đoạn sau, trên máy 64 bit thông dụng (`alignof(int)` là 4). `sizeof` của `S` thường bằng bao nhiêu?

```text
struct S { char a; int b; char c; };
```

- 6, vì chỉ cộng cỡ ba thành viên: 1 + 4 + 1
- 12, vì có đệm trước `b` và đệm cuối cho tròn bội 4
- 8, vì trình biên dịch tự xếp lại thành viên cho gọn
- 9, vì chỉ có đệm trước `b`, cuối `struct` thì không

<p class="giai-thich" markdown>`a` ở vị trí 0, `b` phải ở vị trí chia hết cho 4 nên có 3 byte đệm rồi `b` ở 4, `c` ở 8, và `sizeof` tròn lên bội của `alignof` (4) nên thành 12. Tổng cỡ thành viên (6) bỏ qua padding. Trình biên dịch không tự xếp lại thành viên, vì chuẩn bắt giữ thứ tự khai báo; chính bạn xếp thành `int b; char a; char c;` mới được 8. Còn 9 quên rằng cả `struct` cũng phải tròn tới bội của căn lề, để mảng đặt liền nhau vẫn đúng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Bộ phân tích cú pháp tạo một triệu nút cây nhỏ cho mỗi yêu cầu. Mọi nút chỉ dùng trong yêu cầu đó rồi bỏ hết cùng lúc, không nút nào bị xóa lẻ. Chọn gì cho bộ nhớ của các nút?

- Object pool, để trả lẻ từng nút ngay khi dùng xong
- `new`/`delete` thường, vì bộ cấp phát hệ thống đã tối ưu rồi
- `std::shared_ptr` cho từng nút, để nút tự trả khi hết người dùng
- Arena: cấp bằng cách cộng con trỏ, rồi thả cả vùng một lần

<p class="giai-thich" markdown>Các nút cùng sinh, cùng chết nên arena vừa khít: mỗi lần cấp chỉ là cộng con trỏ, các nút nằm sát nhau, và thả cả vùng bằng một lệnh. Pool phục vụ bài toán trả lẻ từng đối tượng, mà ở đây không ai trả lẻ nên chỉ tốn công quản lý danh sách rảnh. `new`/`delete` làm đúng nhưng chịu phụ phí mỗi nút, một triệu lần. `shared_ptr` còn nặng hơn (khối điều khiển và đếm tham chiếu cho từng nút) mà không đổi được cách cấp phát.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Đọc đoạn sau trên g++ 11 (SSO tối đa 15 ký tự), trong chương trình đã thay `operator new` để đếm. Đoạn này làm bộ đếm tăng bao nhiêu?

```text
std::string a = "abc";
std::string b(40, 'x');
std::vector<int> v;
v.reserve(10);
```

- 0
- 1
- 2
- 3

<p class="giai-thich" markdown>Chuỗi `a` ngắn nên chữ nằm ngay trong đối tượng, không xin heap. Chuỗi `b` có 40 ký tự, vượt ngưỡng SSO, nên xin heap một lần. `reserve(10)` của `v` xin một khối một lần. Cộng lại là hai. Đếm ra một là bỏ sót `reserve`; đếm ra ba là coi cả chuỗi ngắn cũng xin heap, trái với SSO.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Server liên tục tạo và hủy các đối tượng `KetNoi` cùng cỡ, chết vào những lúc khác nhau. Bạn đã đo thấy `new`/`delete` là điểm nghẽn. Chọn gì?

- Object pool cho `KetNoi`: trả lẻ O(1), lần tạo sau dùng lại ô cũ
- Arena một khối: chỉ việc thả cả vùng khi hết ca làm việc
- `alignas(64)` cho `KetNoi`, để các luồng khỏi giành dòng cache
- `monotonic_buffer_resource`, vì nó thu lại chỗ khi đối tượng bị hủy

<p class="giai-thich" markdown>Cùng loại, cùng cỡ, vòng đời lệch nhau là chỗ của object pool: trả một ô là đưa về đầu danh sách, lần tạo sau dùng lại ngay. Arena không trả lẻ nên bộ nhớ chỉ phình lên cho tới lúc thả cả vùng, mà ở đây không có lúc nào cả vùng cùng chết. `alignas(64)` chữa false sharing giữa các luồng, không chữa chi phí cấp phát. `monotonic_buffer_resource` đúng là loại không thu chỗ: hủy đối tượng hay trả khối đều không làm gì.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Profiler cho thấy `operator new` chỉ chiếm 2% thời gian chương trình; 60% là một vòng lặp tính toán. Đồng nghiệp đề nghị viết memory pool riêng. Bạn nên làm gì?

- Viết pool ngay, vì tránh cấp phát luôn là việc nên làm trước
- Chưa viết: dù pool đưa cấp phát về 0 thì cũng chỉ nhanh hơn 2%
- Thay `std::vector` bằng `std::list` để mỗi phần tử cấp phát riêng
- Viết pool và tắt ASan cho khỏi báo lỗi trong vùng nhớ của pool

<p class="giai-thich" markdown>Cấp phát chỉ 2% nên dù pool kéo nó về 0 thì chương trình cũng chỉ nhanh hơn vài phần trăm, trong khi pool tự viết kéo theo rủi ro: mất ASan, mất an toàn luồng, thêm mã phải bảo trì. Chỗ cần xem là thứ chiếm 60%. `std::list` cấp phát cho từng nút nên tăng số lần xin chứ không giảm. Tắt ASan chỉ là bỏ công cụ bắt lỗi chứ không giải quyết được nghẽn cổ chai nào.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Nhóm bạn viết object pool như Ví dụ 2 (danh sách ô rảnh, không có khóa) rồi cho bốn luồng cùng gọi `tao()` và `huy()`. Điều gì đúng?

- An toàn, vì mỗi ô chỉ chứa một đối tượng nên các luồng không đụng nhau
- An toàn khi `tao` trả `nullptr` lúc hết ô, vì như vậy không ai phải chờ ai
- Chỉ lỗi khi hai luồng cùng `huy` một ô; còn `tao` thì luôn ổn
- Có data race trên danh sách rảnh; cần mutex hoặc mỗi luồng một pool

<p class="giai-thich" markdown>Con trỏ `ranh_` và các con trỏ `tiep` trong ô rảnh là dữ liệu chung: hai luồng cùng `tao` có thể cùng đọc `ranh_` và lấy trúng một ô, và `huy` đồng thời cũng sửa cùng con trỏ. Mỗi ô một đối tượng chỉ đúng khi ô đã được giao, còn danh sách rảnh thì luồng nào cũng sờ vào. Trả `nullptr` khi hết ô không liên quan tới đồng bộ. Và `tao` cũng ghi vào `ranh_` nên lỗi không chỉ nằm ở `huy`.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Căn lề**: mỗi kiểu có `alignof`, thành viên đặt ở vị trí chia hết cho nó, chỗ trống là padding, `sizeof` tròn lên bội của `alignof` của `struct`; `Rong` 24 byte xếp lại thành `Gon` 16 byte (mình chạy). Con số tùy máy; chỉ đáng sắp lại khi có rất nhiều đối tượng, và đừng ghi `struct` thô xuống tệp hay mạng.
2. **Dòng cache** 64 byte: `struct` nhỏ thì nhiều đối tượng chung dòng; `alignas(64)` tách dòng (chữa false sharing của [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)) nhưng tốn 64 byte cho 4 byte dữ liệu; SoA giảm 8 lần số dòng khi chỉ quét một trường (tính: 500.000 so với 62.500), AoS tốt khi dùng mọi trường.
3. **Placement new** `new (diaChi) T(...)` chỉ chạy hàm tạo; hàm hủy phải gọi tay `p->~T()`; chỗ nhớ phải đủ lớn và đúng căn lề (quên hàm hủy: rò phần `T` giữ, LeakSanitizer có thể báo; lệch căn lề: UBSan báo). Thay `operator new` cho phép đếm: chuỗi ngắn (SSO) 0 lần xin, `reserve` đổi 8 lần thành 1.
4. **Vì sao `new` chậm với triệu đối tượng nhỏ**: tìm chỗ và ghi sổ, phụ phí mỗi khối (mình đo 32 byte cho nút 16), rải rác làm cache kém, phân mảnh. **Arena** (cộng con trỏ, thả cả vùng, không trả lẻ, không chạy hàm hủy) hợp đối tượng cùng sinh cùng chết; **object pool** (danh sách ô rảnh, trả lẻ O(1)) hợp đối tượng cùng loại sinh tử lẻ tẻ; mình đo arena nhanh cỡ 2 đến 8 lần (đổi theo máy, `-O` và lúc chạy).
5. `std::pmr::monotonic_buffer_resource` (C++17) là arena chuẩn; tự viết pool thì mất ASan và an toàn luồng. **Đo trước**, rồi `reserve`, sắp lại `struct`, rồi mới arena/pool; "tự viết memory pool" trả lời bằng hướng sáu bước và giới hạn của nó.
