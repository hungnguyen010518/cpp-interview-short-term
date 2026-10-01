# Bài 15 — Hành vi không xác định và công cụ bắt lỗi

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được hành vi không xác định (UB) là gì, khác lỗi biên dịch và lỗi chạy bình thường ở đâu, và vì sao "chạy đúng ở máy tôi" không chứng minh gì.
    - Bật được cảnh báo `-Wall -Wextra`, AddressSanitizer và UndefinedBehaviorSanitizer, rồi đọc được báo cáo của chúng.
    - Biết Valgrind và ThreadSanitizer là gì, và biết cách viết code để ít dính UB ngay từ đầu.

**Bạn cần biết trước:** [Bài 03](03-con-tro-co-ban.md) (`nullptr`, UB lần đầu), [Bài 05](05-mang-phep-tinh-con-tro.md) (mảng, đi ra ngoài mảng), [Bài 07](07-new-delete.md) (`new`/`delete`, ba lỗi kinh điển, AddressSanitizer bắt rò rỉ), [Bài 08](08-raii.md) (`try`/`catch`) và [Bài 09](09-unique-ptr.md) (`make_unique`). Bài này **không** dạy lại ba lỗi của Bài 07 từ đầu: nó cho bạn **công cụ** để thấy chúng, và nói rõ chữ "không xác định" nghĩa là gì.

## 🧠 Câu chuyện mở đầu

Bạn thuê **12 ngăn liền nhau** trong dãy tủ khóa ([Bài 01](01-bo-nho-byte-dia-chi.md)) để cất ba món `int`. Hợp đồng thuê (chuẩn C++) chỉ có một điều khoản: bạn được dùng đúng 12 ngăn đó.

Nếu bạn thò tay mở ngăn thứ 13, hợp đồng **không nói gì**: không cấm, không phạt, cũng không hứa ngăn đó có gì. Nó có thể đang trống, có thể là đồ của người khác, có thể là thứ khiến cả dãy tủ hỏng.

Chuyện đáng sợ là **không ai báo bạn**: cô quản lý tủ không đứng canh. **Sanitizer** là thuê thêm một người **bảo vệ** đứng cạnh. Mỗi lần bạn mở ngăn, bảo vệ nhìn sổ; thấy ngăn không thuộc phần bạn thuê thì thổi còi và ghi biên bản (dòng code nào, ngăn nào, ai thuê, ai trả).

Bảo vệ làm mọi thứ chậm đi, và chỉ canh những lần mở ngăn **thật sự xảy ra** trong lần chạy thử đó.

!!! info "Chỗ nào ví dụ bảo vệ không còn đúng?"
    Bảo vệ thật đứng ngoài, không đổi cái tủ. Sanitizer thì không: bạn **biên dịch lại** chương trình và g++ chèn thêm các bước kiểm tra vào chính chương trình (mục 5).

## 📖 Giải thích

### 1. Ba kiểu "sai": lỗi biên dịch, lỗi chạy bình thường, UB

Chương trình sai theo ba kiểu khác hẳn nhau, và phân biệt chúng là bước đầu của bài này.

| | Lỗi biên dịch | Lỗi chạy bình thường | Hành vi không xác định (UB) |
|---|---|---|---|
| Lộ ra khi nào | Lúc biên dịch: không có chương trình nào để chạy | Lúc chạy | Có thể lúc chạy, có thể **không bao giờ lộ** |
| Chuẩn C++ nói gì | Chương trình sai luật, trình biên dịch phải báo | Chương trình đúng luật, kết quả được **định nghĩa rõ** | Chuẩn **không đặt yêu cầu nào** lên kết quả |
| Ví dụ | `int x = "abc";` | Mở tệp không có; `new` hết chỗ ném `std::bad_alloc` ([Bài 07](07-new-delete.md)) | `a[3]` với mảng 3 món; `*p` khi `p` là `nullptr` |
| Bạn xử lý | Sửa code | Kiểm tra, hoặc `try`/`catch` ([Bài 08](08-raii.md)) | Không "bắt" được lúc chạy: phải tránh, và dùng công cụ |

Lỗi biên dịch thì g++ nói ngay. Mình đã biên dịch dòng `int x = "abc";` và g++ báo (rút gọn):

```text
bai.cpp:4:13: error: invalid conversion from 'const char*' to 'int' [-fpermissive]
```

Lỗi chạy bình thường thì chương trình **đúng luật**: C++ nói rõ chuyện gì xảy ra (ví dụ ném ngoại lệ), và bạn có cách bắt. UB thì ngược lại: chương trình **viết ra được** (biên dịch sạch), nhưng khi chạy qua dòng đó, chuẩn nói "kể từ đây, mọi chuyện đều có thể xảy ra" ([Bài 03](03-con-tro-co-ban.md) đã nói một lần).

### 2. "Chạy đúng ở máy tôi" không chứng minh gì

Với UB, kết quả có thể là: chạy ra đúng; chạy ra sai **âm thầm** (không báo gì); sập; hoặc đổi từng lần. Chuẩn không chọn một khả năng nào, nên chương trình có UB mà "chạy đúng" chỉ là một khả năng trong nhiều.

Kết quả còn có thể đổi theo trình biên dịch, theo phiên bản của nó, theo cờ tối ưu hóa và theo máy. Cờ `-O2` bảo trình biên dịch **tối ưu hóa**, nghĩa là viết lại chương trình cho chạy nhanh hơn; lệnh ở [Bài 01](01-bo-nho-byte-dia-chi.md) không có cờ này. Khi tối ưu, trình biên dịch được phép **giả sử UB không bao giờ xảy ra**, nên một chương trình có UB có thể hành xử khác hẳn giữa bản thường và bản `-O2`.

Hệ quả thực tế: chương trình qua mọi lần thử, chạy ổn nhiều tháng, rồi hỏng sau khi đổi máy chủ hoặc nâng cấp trình biên dịch. Lỗi không mới xuất hiện: nó nằm đó từ đầu, chỉ là chưa ai thấy.

### 3. Danh mục UB hay gặp

Đây là các món bạn sẽ gặp nhiều nhất. Bài này chỉ **nêu tên** từng món; ba món đầu bạn đã gặp ở các bài trước.

| UB | Một dòng | Đã gặp |
|---|---|---|
| Đọc hoặc ghi ngoài mảng | Chỉ số ra ngoài biên: mảng 3 món mà dùng `a[3]` | [Bài 05](05-mang-phep-tinh-con-tro.md) |
| Dùng sau khi trả (use-after-free) | Đọc hay ghi qua con trỏ tới chỗ đã `delete` | [Bài 07](07-new-delete.md) |
| Giải phóng hai lần (double free) | `delete` cùng một chỗ hai lần | [Bài 07](07-new-delete.md) |
| Tràn số nguyên **có dấu** | `INT_MAX + 1` với `int` (số nguyên không dấu thì khác: được định nghĩa là quấn vòng) | mục 6 |
| Giải tham chiếu `nullptr` | `*p` khi `p` là `nullptr` | [Bài 03](03-con-tro-co-ban.md) |
| Đọc biến chưa khởi tạo | Biến cục bộ `int x;` chưa gán gì mà đã đọc | [Bài 03](03-con-tro-co-ban.md) (con trỏ rác) |
| Data race (tranh chấp dữ liệu) | Hai luồng cùng truy cập một biến, ít nhất một luồng ghi, không đồng bộ | [Bài 10](10-shared-ptr-weak-ptr.md) (nhắc), nhóm đa luồng |

Còn một điều hay bị xếp nhầm vào đây. **Rò rỉ bộ nhớ không phải UB**: chương trình rò rỉ vẫn đúng luật, kết quả vẫn được định nghĩa, chỉ là phí bộ nhớ ([Bài 07](07-new-delete.md)).

!!! info "Bạn biết Go?"
    Go **không có khái niệm UB** cho các lỗi trên: chúng có kết quả xác định (riêng data race trong Go vẫn là lỗi nguy hiểm, nên có `-race`). Ngoài biên mảng hay slice thì Go kiểm tra lúc chạy và `panic`; giải tham chiếu `nil` cũng `panic`; số nguyên có dấu tràn thì **quấn vòng** (spec Go định nghĩa như vậy). Với race, Go có công cụ `go run -race` ứng với ThreadSanitizer của C++ (mục 7), và `go vet` hơi giống cảnh báo của trình biên dịch (mục 4). "UB" nghĩa như trong bài này là khái niệm của C/C++.

### 4. Bắt sớm nhất: cảnh báo trình biên dịch

Công cụ rẻ nhất là chính g++. Cờ `-Wall` (`W` = warning, cảnh báo) bật các cảnh báo thông dụng, `-Wextra` thêm một lớp nữa.

Cảnh báo không chặn việc biên dịch: chương trình vẫn ra file chạy được, nên **phải đọc**. Một chương trình nhỏ có hai UB:

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int x;                          // (1)
    std::cout << x << "\n";         // (2)
    int a[3] = {1, 2, 3};           // (3)
    std::cout << a[3] << "\n";      // (4)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra |
|---|---|---|
| 1 | (1) | `x` là biến cục bộ **chưa gán giá trị**: nó chứa rác |
| 2 | (2) | Đọc `x` để in: UB (đọc biến chưa khởi tạo) |
| 3 | (3) | `a` có ba món, chỉ số hợp lệ là 0, 1, 2 |
| 4 | (4) | `a[3]` là món thứ tư không tồn tại: UB (đọc ngoài mảng) |

Mình đã biên dịch bằng `g++ -std=c++17 -Wall -Wextra`. Kết quả (rút gọn, bỏ tên hàm và dòng chỉ chỗ):

```text
bai.cpp:6:23: warning: 'x' is used uninitialized [-Wuninitialized]
```

Chỉ có **một** cảnh báo, cho dòng (2). Dòng (4) không bị báo.

Khi mình thêm `-O2`, g++ báo thêm `bai.cpp:8:26: warning: array subscript 3 is above array bounds of 'int [3]' [-Warray-bounds]`. Nghĩa là cảnh báo dựa vào việc g++ **suy luận** từ code, nên nó có thể hiện hay không tùy cờ.

Quy tắc: cảnh báo là lưới thô, nó bắt được những ca rõ ràng như trên, nhưng **im lặng không có nghĩa là sạch**. Hãy luôn bật `-Wall -Wextra` và sửa mọi cảnh báo, rồi dùng sanitizer cho những thứ lưới này không thấy.

### 5. AddressSanitizer: bảo vệ canh từng lần mở ngăn

**AddressSanitizer (ASan)** đã xuất hiện ở [Bài 07](07-new-delete.md) để bắt rò rỉ. Nó còn bắt cả lỗi **ngay lúc chúng xảy ra**: đọc hoặc ghi ngoài vùng được phép, dùng sau khi trả, giải phóng hai lần.

Lệnh bật nó (các cờ giống [Bài 07](07-new-delete.md): `-g` để báo cáo có số dòng, `-fno-omit-frame-pointer` để danh sách hàm đầy đủ):

```text
g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer -o chuongtrinh chuongtrinh.cpp
```

Ý tưởng bên trong (đơn giản hóa, đủ để hình dung và để trả lời phỏng vấn). Lúc biên dịch, g++ chèn một bước kiểm tra trước mỗi lần chương trình đọc hay ghi bộ nhớ. ASan giữ một **bảng ghi chú** (shadow memory) cho biết mỗi nhóm byte có được phép dùng không.

Quanh mỗi mảng cục bộ và mỗi khối `new`, nó chừa **vùng đệm đỏ (red zone)**: vài byte đánh dấu "cấm". Chỗ vừa `delete` cũng bị đánh dấu "cấm" và được giữ lại một lúc thay vì cho dùng lại ngay. Chạm vào byte bị đánh dấu thì ASan báo lỗi.

Hai hệ quả bạn sẽ thấy. Chương trình **chậm hơn** (thường chậm cỡ vài lần) và ngốn thêm bộ nhớ. ASan **mặc định dừng chương trình ở lỗi đầu tiên** (mình thấy mã thoát 1), nên sửa từng lỗi rồi chạy lại.

#### Cách đọc một báo cáo

Mọi báo cáo ASan có cùng các phần. Bảng sau là bản đồ chung; ở mỗi ca dưới, mình chỉ nói phần mới (ca double-free không có dòng `READ`/`WRITE`, vì lỗi nằm ở lần `delete`, không phải một lần đọc hay ghi).

| Phần trong báo cáo | Cho bạn biết |
|---|---|
| `ERROR: AddressSanitizer: <loại>` | **Loại lỗi** (tên lỗi nằm ngay đây) |
| `READ` hay `WRITE of size N` | Đọc hay ghi, bao nhiêu byte |
| `#0 ... in main bai.cpp:7` | Khung `#0`: **nơi lỗi xảy ra**, thường là dòng code của bạn |
| `freed by ...` / `allocated by ...` | Chỗ nhớ đó **được trả** hay **được xin** ở dòng nào |
| `SUMMARY: ...` | Một dòng tóm tắt: loại lỗi và dòng |

"Khung" (frame) là một hàm đang chạy trong chuỗi các hàm gọi nhau (như các tờ nằm chồng trên bàn học, [Bài 02](02-stack-heap-static.md)): `#0` là hàm trong cùng, `#1` là hàm đã gọi nó.

Trong các báo cáo dưới đây mình **rút gọn**: bỏ địa chỉ (viết `0x...`), bỏ đường dẫn tệp (còn `bai.cpp`), bỏ các khung `#1`, `#2`... của thư viện hệ thống ở cuối chuỗi, bỏ dòng `HINT`, và bỏ bảng "Shadow bytes" dài ở cuối.

`thread T0` là luồng chính (luồng = một dòng chạy riêng, [Bài 10](10-shared-ptr-weak-ptr.md); chương trình của ta chỉ có một). Mấy số `pc`, `bp`, `sp` là địa chỉ nội bộ, bạn bỏ qua được.

#### Ca (a): ghi ngoài mảng ở stack (stack-buffer-overflow)

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int a[3] = {1, 2, 3};     // (1)
    int i = 3;                // (2)
    a[i] = 99;                // (3)
    std::cout << "xong\n";    // (4)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới ASan) |
|---|---|---|
| 1 | (1) | Mảng `a` nằm trên stack: 3 món, 12 byte |
| 2 | (2) | `i` = 3 |
| 3 | (3) | Ghi vào `a[3]`, món thứ tư không thuộc mảng: ASan thấy byte đó bị đánh dấu "cấm", báo lỗi và dừng **trước khi** ghi |
| 4 | (4) | Chưa chạy tới: chương trình đã bị dừng ở bước 3 |

Dưới ASan thì chương trình in báo cáo sau và thoát mã 1 (bản rút gọn của lần chạy thật; mình không khẳng định chương trình này làm gì khi **không** có sanitizer):

```text
==...==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x... at pc 0x... bp 0x... sp 0x...
WRITE of size 4 at 0x... thread T0
    #0 0x... in main bai.cpp:7

Address 0x... is located in stack of thread T0 at offset 44 in frame
    #0 0x... in main bai.cpp:4

  This frame has 1 object(s):
    [32, 44) 'a' (line 5) <== Memory access at offset 44 overflows this variable
SUMMARY: AddressSanitizer: stack-buffer-overflow bai.cpp:7 in main
```

Cách đọc: tên lỗi `stack-buffer-overflow` là "tràn bộ đệm trên stack": ta ghi vượt mảng cục bộ. `WRITE of size 4` là một lần **ghi** 4 byte, và `#0 ... main bai.cpp:7` chỉ đúng dòng `a[i] = 99;`.

Dòng `[32, 44) 'a'` nói biến `a` chiếm byte từ 32 đến 43 của khung hàm (12 byte), mà lần ghi chạm byte 44: byte đầu tiên **ngay sau** mảng.

#### Ca (b): đọc ngoài mảng ở heap (heap-buffer-overflow)

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* p = new int[3]{1, 2, 3};   // (1)
    int i = 3;                      // (2)
    std::cout << p[i] << "\n";      // (3)
    delete[] p;                     // (4)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới ASan) |
|---|---|---|
| 1 | (1) | `new int[3]{1, 2, 3}` xin 12 byte ở heap cho ba `int` và điền 1, 2, 3 |
| 2 | (2) | `i` = 3 |
| 3 | (3) | Đọc `p[3]`, ngay sau khối: ASan báo lỗi và dừng |
| 4 | (4) | Chưa chạy tới (bước 3 đã dừng chương trình) |

Báo cáo thật, rút gọn:

```text
==...==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x... at pc 0x... bp 0x... sp 0x...
READ of size 4 at 0x... thread T0
    #0 0x... in main bai.cpp:7

0x... is located 0 bytes to the right of 12-byte region [0x...,0x...)
allocated by thread T0 here:
    #0 0x... in operator new[](unsigned long) ...
    #1 0x... in main bai.cpp:5

SUMMARY: AddressSanitizer: heap-buffer-overflow bai.cpp:7 in main
```

`heap-buffer-overflow` là tràn ở heap, và lần này là một lần **đọc** (`READ`), nên "tràn" không chỉ nghĩa là ghi.

Dòng `0 bytes to the right of 12-byte region` nói rất chính xác: chỗ bị chạm nằm **ngay sau** khối 12 byte, cách 0 byte. Và khối đó **được xin** ở `#1 ... main bai.cpp:5`, đúng dòng có `new int[3]`.

#### Ca (c): dùng sau khi trả (heap-use-after-free)

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* p = new int(5);          // (1)
    delete p;                     // (2)
    std::cout << *p << "\n";      // (3)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới ASan) |
|---|---|---|
| 1 | (1) | Xin 4 byte ở heap, `p` giữ địa chỉ |
| 2 | (2) | Trả chỗ đó; ASan đánh dấu 4 byte ấy "cấm" |
| 3 | (3) | Đọc `*p`: byte bị đánh dấu "cấm", ASan báo lỗi và dừng |

Báo cáo thật, rút gọn:

```text
==...==ERROR: AddressSanitizer: heap-use-after-free on address 0x... at pc 0x... bp 0x... sp 0x...
READ of size 4 at 0x... thread T0
    #0 0x... in main bai.cpp:7

0x... is located 0 bytes inside of 4-byte region [0x...,0x...)
freed by thread T0 here:
    #0 0x... in operator delete(void*, unsigned long) ...
    #1 0x... in main bai.cpp:6

previously allocated by thread T0 here:
    #0 0x... in operator new(unsigned long) ...
    #1 0x... in main bai.cpp:5

SUMMARY: AddressSanitizer: heap-use-after-free bai.cpp:7 in main
```

Ca này báo cáo **kể đủ cả câu chuyện** bằng ba mốc, đều là dòng của bạn. `#0 ... bai.cpp:7` là nơi dùng sai (dòng (3)), `freed by ... bai.cpp:6` là nơi đã trả (dòng (2)), `previously allocated by ... bai.cpp:5` là nơi đã xin (dòng (1)).

Chữ `0 bytes inside of 4-byte region` nghĩa là chạm đúng đầu khối, **bên trong** nó (khác ca (b): ở đó là bên ngoài). Với lỗi kiểu này, hai dòng `freed by` và `allocated by` thường là chỗ bạn tìm ra nguyên nhân.

#### Ca (d): giải phóng hai lần (double-free)

```cpp
// bo-qua-kiem-tra
int main() {
    int* p = new int(5);     // (1)
    delete p;                // (2)
    delete p;                // (3)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới ASan) |
|---|---|---|
| 1 | (1) | Xin 4 byte ở heap |
| 2 | (2) | Trả lần đầu: hợp lệ |
| 3 | (3) | Trả lần hai cùng một chỗ: ASan nhận ra chỗ này đã trả, báo lỗi và dừng |

Báo cáo thật, rút gọn:

```text
==...==ERROR: AddressSanitizer: attempting double-free on 0x... in thread T0:
    #0 0x... in operator delete(void*, unsigned long) ...
    #1 0x... in main bai.cpp:5

0x... is located 0 bytes inside of 4-byte region [0x...,0x...)
freed by thread T0 here:
    #0 0x... in operator delete(void*, unsigned long) ...
    #1 0x... in main bai.cpp:4

previously allocated by thread T0 here:
    #0 0x... in operator new(unsigned long) ...
    #1 0x... in main bai.cpp:3

SUMMARY: AddressSanitizer: double-free ... in operator delete(void*, unsigned long)
```

Có hai điểm khác ca (c). Lỗi được đặt tên `attempting double-free` ("đang thử giải phóng hai lần").

Và khung `#0` lần này là `operator delete`, nằm trong thư viện, vì chính lần `delete` thứ hai là chỗ lỗi: **dòng code của bạn là `#1`** (`bai.cpp:5`, lần `delete` thứ hai), còn `freed by` chỉ lần `delete` đầu (`bai.cpp:4`). Dòng `SUMMARY` cũng trỏ vào thư viện chứ không vào file của bạn, nên với ca này hãy đọc các khung `#1`.

Vậy khung `#0` không phải lúc nào cũng là dòng code của bạn. Cách chắc ăn: tìm dòng **đầu tiên** có tên tệp `.cpp` của bạn trong chuỗi `#0`, `#1`, `#2`...

Một lưu ý khi tự thử: khi in ra màn hình thường bạn thấy các dòng `std::cout` chạy **trước** lỗi. Nếu chuyển hướng đầu ra sang tệp hay ống (`|`), chữ còn nằm trong bộ đệm của chương trình, chưa kịp ghi thì chương trình đã bị dừng đột ngột. Mình đã gặp đúng chuyện này, nên hãy chạy không chuyển hướng, và đừng kết luận "chưa chạy tới đó" chỉ vì không thấy chữ.

### 6. UndefinedBehaviorSanitizer: bắt UB không liên quan đến bộ nhớ

ASan lo việc **địa chỉ**. UB còn nhiều loại khác, như tràn số hay dịch bit quá cỡ, mà ASan không để ý. **UndefinedBehaviorSanitizer (UBSan)** lo các loại đó: bật bằng `-fsanitize=undefined`.

Hai món mới trong chương trình dưới: `INT_MAX` (trong `<climits>`) là số `int` lớn nhất, 2147483647. Còn `1 << s` là **dịch bit** trái: lấy 1 và dịch `s` vị trí, nghĩa là nhân với 2 mũ `s`; một `int` có 32 bit, và dịch một `int` đi 32 vị trí trở lên là UB, nên dịch 40 vị trí là quá cỡ.

```cpp
// bo-qua-kiem-tra
#include <climits>
#include <iostream>

int main() {
    int n = INT_MAX;          // (1)
    int m = n + 1;            // (2)
    int s = 40;               // (3)
    int k = 1 << s;           // (4)
    std::cout << "xong\n";
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới UBSan) |
|---|---|---|
| 1 | (1) | `n` = 2147483647, giá trị lớn nhất của `int` |
| 2 | (2) | `n + 1` vượt miền của `int` có dấu: UB (tràn số nguyên có dấu); UBSan in một dòng báo cáo |
| 3 | (3) | `s` = 40 |
| 4 | (4) | `1 << 40` với `int` 32 bit: UB (dịch bit quá cỡ); UBSan in dòng báo cáo thứ hai |
| 5 | in | In `xong`: UBSan **không dừng** chương trình |

Dưới `-fsanitize=undefined`, mình thấy (thoát mã 0):

```text
bai.cpp:7:9: runtime error: signed integer overflow: 2147483647 + 1 cannot be represented in type 'int'
bai.cpp:9:15: runtime error: shift exponent 40 is too large for 32-bit type 'int'
xong
```

Báo cáo UBSan **ngắn hơn ASan nhiều**: một dòng cho mỗi lỗi, dạng `tệp:dòng:cột: runtime error: <chuyện gì>`. Số `7:9` là dòng 7, cột 9, đúng chỗ `n + 1`.

Khác ASan, mặc định UBSan **in rồi chạy tiếp** (nên có `xong` ở cuối); đó là hành vi của công cụ, không phải lời hứa gì về chương trình khi không có nó.

Ca còn lại là giải tham chiếu `nullptr` ([Bài 03](03-con-tro-co-ban.md)):

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* p = nullptr;          // (1)
    std::cout << *p << "\n";   // (2)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra (dưới UBSan) |
|---|---|---|
| 1 | (1) | `p` giữ `nullptr` |
| 2 | (2) | `*p`: UBSan báo, rồi chương trình thật sự đọc địa chỉ 0 và bị hệ điều hành dừng |

Dưới `-fsanitize=undefined`, mình thấy dòng sau, rồi chương trình dừng với mã thoát 139 (mã mà [Bài 06](06-tham-chieu-const.md) đã gặp, báo hiệu `Segmentation fault`):

```text
bai.cpp:6:24: runtime error: load of null pointer of type 'int'
```

`load of null pointer` nghĩa là "đọc qua con trỏ null". Dưới sanitizer thì kết quả như trên; còn khi không có nó, chuẩn không hứa gì (đừng suy ra "luôn sập").

### 7. Ghép công cụ, LeakSanitizer, Valgrind, ThreadSanitizer

**Ghép ASan với UBSan:** `-fsanitize=address,undefined`. Khi hai công cụ cùng thấy một lỗi, bạn có thể nhận **hai** báo cáo. Với chương trình ca (a), mình thấy UBSan lên tiếng trước (rút gọn), rồi ASan in báo cáo `stack-buffer-overflow` như ở mục 5:

```text
bai.cpp:7:8: runtime error: index 3 out of bounds for type 'int [3]'
bai.cpp:7:10: runtime error: store to address 0x... with insufficient space for an object of type 'int'
```

Nên dòng `ERROR` đầu tiên bạn thấy chưa chắc là của ASan: hãy đọc từ trên xuống.

**LeakSanitizer** đi kèm ASan trên Linux: khi chương trình kết thúc, nó liệt kê các khối đã xin mà chưa trả ([Bài 07](07-new-delete.md), có báo cáo thật). Nhớ rằng nó **đôi khi bỏ sót** (Bài 07 đã nêu một ca).

Chung hơn: ASan, UBSan, LeakSanitizer chỉ thấy lỗi **xảy ra trong lần chạy đó**. Chạy dưới sanitizer mà không có báo cáo thì chỉ nói được "lần chạy này không thấy lỗi", không nói được "chương trình sạch".

**Valgrind** là công cụ khác cùng loại, lệnh:

```text
valgrind --leak-check=full ./chuongtrinh
```

Nó chạy **nguyên bản** chương trình đã biên dịch (không cần biên dịch lại, khác ASan) trong một môi trường theo dõi từng truy cập bộ nhớ, nên **chậm hơn** (thường chậm hơn ASan nhiều lần). Valgrind **không được cài trên máy mình dùng để viết bài**, nên mình không dán kết quả nào.

**ThreadSanitizer** (`-fsanitize=thread`) chuyên bắt **data race** trong chương trình nhiều luồng; bài này chỉ nêu tên, nhóm đa luồng sẽ dùng nó. Nó **không ghép được** với ASan: mình thử `-fsanitize=address,thread` và g++ báo `'-fsanitize=thread' is incompatible with '-fsanitize=address'`.

### 8. Phòng ngừa: viết code ít dính UB

Công cụ bắt lỗi là lớp cuối. Lớp đầu là viết sao cho nhiều loại UB **không thể xảy ra**:

- Để RAII và smart pointer ([Bài 08](08-raii.md), [Bài 09](09-unique-ptr.md), [Bài 10](10-shared-ptr-weak-ptr.md)) lo việc trả: không có `delete` do bạn viết thì không có "trả hai lần" hay "quên trả".
- Dùng `std::vector` và `std::string` thay cho mảng thô và `new[]`: chúng tự xin và trả bộ nhớ, và biết kích thước của mình.
- Khi chỉ số có thể ra ngoài, dùng `v.at(i)` thay cho `v[i]`: `v[i]` không kiểm tra (ngoài biên là UB), còn `v.at(i)` kiểm tra và **ném ngoại lệ** nếu ngoài biên. Ném ngoại lệ là hành vi được định nghĩa, bạn bắt được bằng `try`/`catch`.
- Luôn khởi tạo biến ngay khi khai báo, và bật `-Wall -Wextra`.
- Chạy kiểm thử (các chương trình nhỏ tự kiểm tra kết quả) bằng bản biên dịch có `-fsanitize=address,undefined`.

## 💻 Ví dụ code

### Ví dụ: sửa các lỗi bằng container và smart pointer

Chương trình dưới tránh được các ca (a) và (c)–(d), nhờ dùng `std::vector`, `at` và `make_unique`.

Ba chỗ cần giải thích. `#include <stdexcept>` mang vào kiểu ngoại lệ `std::out_of_range`, kiểu mà `at` ném khi chỉ số ngoài biên. `catch (const std::out_of_range& e)` bắt ngoại lệ đó bằng tham chiếu `const` ([Bài 06](06-tham-chieu-const.md)) để khỏi chép. `e.what()` trả một chuỗi mô tả lỗi.

```cpp
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

int main() {
    std::vector<int> a = {1, 2, 3};                      // (1)
    int i = 3;                                           // (2)
    try {
        a.at(i) = 99;                                    // (3)
    } catch (const std::out_of_range& e) {               // (4)
        std::cout << "bat duoc: " << e.what() << "\n";   // (5)
    }
    auto p = std::make_unique<int>(5);                   // (6)
    std::cout << *p << "\n";                             // (7)
    return 0;
}
```

| Bước | Dòng | Chuyện gì xảy ra |
|---|---|---|
| 1 | (1) | `a` là vector ba phần tử 1, 2, 3 (bộ nhớ ở heap, do vector quản lý) |
| 2 | (2) | `i` = 3 |
| 3 | (3) | `a.at(3)` kiểm tra chỉ số, thấy ngoài biên và **ném** `std::out_of_range`; lệnh ghi không xảy ra |
| 4 | (4) | `catch` khớp kiểu, nhận ngoại lệ vào `e` |
| 5 | (5) | In `bat duoc:` cùng mô tả lỗi |
| 6 | (6) | `make_unique<int>(5)` xin một `int` ở heap giá trị 5, `p` là chủ duy nhất |
| 7 | (7) | In `5`; hết `main` thì `p` tự trả chỗ đó, không có `delete` nào để quên hay lặp |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall -Wextra`):

```text
bat duoc: vector::_M_range_check: __n (which is 3) >= this->size() (which is 3)
5
```

Chữ chính xác sau `bat duoc:` do thư viện chuẩn của g++ quyết định; máy bạn có thể in chữ khác, chỉ có kiểu `std::out_of_range` là do chuẩn quy định. Mình đã chạy bản này với `-fsanitize=address,undefined`: không báo gì, thoát mã 0 (nhắc lại: im lặng không chứng minh là sạch, nhưng ở đây ta còn thấy cả hai việc đúng ý bằng mắt).

**Thử thay đổi: đổi `a.at(i) = 99;` thành `a[i] = 99;`.** Mình đã biên dịch bản đó với `-fsanitize=address` rồi chạy: ASan báo `heap-buffer-overflow`, `WRITE of size 4`, với `#0` trỏ đúng dòng (3), kèm khối "allocated by" đi qua nhiều khung trong mã của `std::vector` (dài nên mình không dán). Bản `at` là chương trình **đúng luật** và bắt được lỗi; bản `[]` là UB, chỉ sanitizer mới thấy.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Undefined behavior là gì? Cho ví dụ."
    Là khi chương trình phạm một luật mà chuẩn C++ không quy định kết quả: chuẩn không đặt yêu cầu nào lên chuyện xảy ra tiếp theo. Ví dụ: truy cập ngoài biên mảng, dùng sau khi `delete`, giải tham chiếu `nullptr`, tràn số nguyên có dấu, đọc biến chưa khởi tạo, data race. Nó khác lỗi biên dịch (bị chặn từ đầu) và lỗi chạy bình thường như ngoại lệ (có kết quả được định nghĩa).

??? question "Vì sao 'chạy đúng ở máy tôi' không đủ để kết luận chương trình không có UB?"
    Vì UB cho phép mọi kết quả, kể cả kết quả đúng. Chương trình có thể chạy đúng với một trình biên dịch, một cờ tối ưu hóa hay một máy, rồi sai hay sập ở nơi khác, vì trình biên dịch được phép giả sử UB không xảy ra khi tối ưu. Nên phải dựa vào công cụ (sanitizer, cảnh báo) và cách viết code, không dựa vào việc "thử thấy ổn".

??? question "AddressSanitizer hoạt động thế nào?"
    Ở mức ý tưởng: biên dịch với cờ, g++ chèn một bước kiểm tra trước mỗi lần đọc hay ghi bộ nhớ. ASan giữ bảng ghi chú (shadow memory) đánh dấu byte nào được phép dùng, chừa các vùng đệm đỏ (red zone) quanh mảng cục bộ và khối ở heap, và đánh dấu chỗ vừa trả là cấm. Chạm vào byte bị đánh dấu thì báo lỗi kèm dòng code. Giá phải trả là chậm hơn và tốn thêm bộ nhớ, và nó chỉ thấy lỗi xảy ra trong lần chạy đó (truy cập nhảy qua hẳn vùng đệm tới một vùng hợp lệ khác thì có thể bị bỏ sót).

??? question "AddressSanitizer khác Valgrind thế nào?"
    ASan cần biên dịch lại với cờ `-fsanitize=address` và thường nhanh hơn nhiều; Valgrind chạy nguyên bản chương trình đã biên dịch, không cần biên dịch lại, nhưng thường chậm hơn nhiều lần. Cả hai cùng bắt được nhiều lỗi bộ nhớ (ngoài biên ở heap, dùng sau khi trả, rò rỉ), và mỗi công cụ có thể thấy những ca mà công cụ kia bỏ sót, nên nhiều đội dùng cả hai.

??? question "UBSan bắt những gì?"
    Bật bằng `-fsanitize=undefined`, nó bắt các UB **không phải lỗi địa chỉ**: tràn số nguyên có dấu, dịch bit quá cỡ, giải tham chiếu `nullptr`, chỉ số ngoài biên mảng có kích thước biết trước... Mỗi lỗi là một dòng `runtime error: ...` kèm tệp, dòng, cột; mặc định nó in rồi chạy tiếp. Thường ghép với ASan bằng `-fsanitize=address,undefined`.

??? question "Làm sao tìm một rò rỉ bộ nhớ?"
    Biên dịch với `-fsanitize=address -g`: khi chương trình kết thúc, LeakSanitizer liệt kê các khối đã xin mà chưa trả, kèm dòng đã xin chúng. Hoặc chạy `valgrind --leak-check=full ./chuongtrinh` không cần biên dịch lại. Cả hai chỉ thấy những gì chạy trong lần đó, nên cần chạy với dữ liệu đủ rộng; cách tốt nhất là thiết kế để khó rò rỉ (RAII, smart pointer).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Coi sự im lặng của công cụ là bằng chứng sạch"
    Không có cảnh báo, hay sanitizer không báo gì, chỉ nghĩa là công cụ không thấy gì **trong lần chạy này**. Đoạn code chưa chạy tới, hay dữ liệu chưa thử, vẫn có thể có UB. LeakSanitizer đôi khi còn bỏ sót cả rò rỉ có thật.

!!! warning "Lỗi 2: Tin rằng UB nào cũng làm chương trình sập"
    Crash (sập) là khả năng dễ chịu nhất, vì ít nhất bạn biết có chuyện; nó chỉ là một trong nhiều kết quả. UB nguy hiểm nhất khi nó **không** làm gì rõ ràng: in sai, hỏng dữ liệu ở chỗ khác, hoặc chạy đúng hôm nay.

!!! warning "Lỗi 3: Xếp rò rỉ bộ nhớ vào UB"
    Rò rỉ không phải UB: chương trình vẫn đúng luật. Nhưng nó vẫn là lỗi cần sửa, và LeakSanitizer (đi kèm ASan) giúp thấy nó. Ngược lại, dùng sau khi trả và giải phóng hai lần **là** UB.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="15" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc báo cáo ASan rút gọn sau (đã bỏ địa chỉ). Chuyện gì đã xảy ra?

```text
ERROR: AddressSanitizer: heap-use-after-free
READ of size 4
    #0 ... in main bai.cpp:8
freed by thread T0 here:
    #1 ... in main bai.cpp:6
previously allocated by thread T0 here:
    #1 ... in main bai.cpp:4
```

- Dòng 6 ghi tràn ra khỏi khối quá nhỏ mà dòng 4 đã xin
- Dòng 8 đọc chỗ dòng 6 đã trả, chỗ dòng 4 từng xin
- Dòng 6 trả hai lần một chỗ mà dòng 4 đã xin trước đó rồi
- Dòng 8 đọc một chỗ chương trình chưa xin

<p class="giai-thich" markdown>Tên lỗi `heap-use-after-free` cùng ba mốc nói đủ câu chuyện: chỗ nhớ được xin ở dòng 4, trả ở dòng 6, rồi bị đọc ở dòng 8 (nơi `#0`). Báo cáo không nói "ghi tràn", vì lần truy cập là `READ` và loại lỗi không phải `buffer-overflow`. Cũng không phải trả hai lần, vì loại đó có tên `double-free`, và mốc `allocated` chứng tỏ chỗ này có được xin. Và chỗ bị đọc có xin ở dòng 4, nên không phải "chưa từng xin".</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Chương trình có ba dòng sau được biên dịch với `-fsanitize=undefined` rồi chạy. Chuyện gì xảy ra?

```text
int s = 40;
int k = 1 << s;
std::cout << "xong\n";
```

- Không biên dịch được, vì dịch bit quá cỡ là một lỗi cú pháp
- In báo lỗi `shift exponent`, dừng và không in `xong`
- Không báo gì, vì UBSan chỉ bắt lỗi tràn số
- In báo lỗi `shift exponent`, rồi chạy tiếp và in `xong`

<p class="giai-thich" markdown>Mình đã chạy đúng đoạn này: UBSan in `runtime error: shift exponent 40 is too large for 32-bit type 'int'` rồi chương trình chạy tiếp, in `xong` và thoát mã 0, vì mặc định UBSan báo mà không dừng. Chương trình vẫn biên dịch được: dịch quá cỡ là UB lúc chạy, không phải lỗi cú pháp. Dịch bit quá cỡ nằm trong danh mục mà UBSan bắt, nên nó không im lặng. Việc dừng ngay ở lỗi đầu tiên là cách ASan hành xử, chứ không phải UBSan.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Chương trình có `int* p = new int[3];` và đọc `p[3]`. Dòng này của báo cáo ASan nói gì?

```text
0x... is located 0 bytes to the right of 12-byte region
```

- Chỗ của `p[3]`, món thứ tư không thuộc khối, ngay sau khối
- Chỗ bị đọc nằm trong khối 12 byte, tức món `p[0]` ở đầu khối
- Khối 12 byte đã bị trả trước đó, nên đây là con trỏ treo
- Khối 12 byte nằm ở stack, nên `p[3]` rơi ra ngoài bàn học

<p class="giai-thich" markdown>`0 bytes to the right of 12-byte region` là "cách mép phải của khối 12 byte đúng 0 byte", tức byte đầu tiên ngay sau khối: ba món `int` chiếm hết 12 byte, nên đó là chỗ của `p[3]`. Nếu chạm vào đầu khối thì báo cáo sẽ nói `0 bytes inside of`. Con trỏ treo có tên lỗi khác, `heap-use-after-free`, kèm mốc `freed by`. Và vì khối do `new` xin nên nó ở heap (tên lỗi cũng là `heap-buffer-overflow`), không phải stack.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Một chương trình có dòng `a[3]` với `a` là mảng 3 món. Nó chạy đúng trên máy bạn và qua mọi lần thử. Kết luận nào hợp lý?

- Không có UB, vì UB làm chương trình sập ngay khi chạy
- Không có UB, vì `-Wall` không báo cảnh báo nào cả
- Vẫn có UB, vì chuẩn không đòi hỏi kết quả nào cả
- Có UB, nhưng chỉ khi đổi sang hệ điều hành khác

<p class="giai-thich" markdown>Ra khỏi biên mảng là UB, và "chạy đúng" chỉ là một trong những kết quả chuẩn cho phép; vì thế chạy thử ổn không chứng minh gì. UB không luôn làm sập: có khi chạy tiếp ra kết quả sai hay đúng như không có gì. Cảnh báo cũng không phải bằng chứng, vì nó chỉ là lưới thô (ở bài này `a[3]` không bị báo khi chỉ dùng `-Wall -Wextra`). Và UB không chỉ xuất hiện khi đổi hệ điều hành: nó có ngay cả trên máy bạn, đổi máy chỉ là một cách nó lộ ra.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Chương trình có `new int(5)` mà không bao giờ `delete`, rồi kết thúc bình thường. Chuẩn C++ coi đó là gì?

- Rò rỉ bộ nhớ: chương trình vẫn đúng luật, không phải UB
- UB, vì chuẩn cấm kết thúc khi còn khối chưa được trả
- Lỗi biên dịch, vì g++ nhận ra thiếu `delete` nên từ chối hẳn
- Con trỏ treo, vì `p` còn giữ địa chỉ sau khi kết thúc

<p class="giai-thich" markdown>Quên `delete` là rò rỉ bộ nhớ: chương trình đúng luật, kết quả vẫn được định nghĩa, chỉ là phí bộ nhớ (và LeakSanitizer có thể liệt kê nó). Chuẩn không có điều cấm kết thúc khi còn khối chưa trả, nên đó không phải UB. G++ không biên dịch lỗi vì với trình biên dịch đây là code hợp lệ. Và `new` không ném ngoại lệ lúc kết thúc: nó chỉ ném khi hết chỗ lúc xin.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Nói về AddressSanitizer và Valgrind (trường hợp thường gặp), câu nào đúng?

- ASan chạy nguyên bản chương trình, Valgrind cần biên dịch lại
- Cả hai cần biên dịch lại, nhưng ASan chỉ bắt lỗi rò rỉ
- Valgrind nhanh hơn ASan, vì nó chỉ đọc file chạy
- ASan cần biên dịch lại và nhanh hơn Valgrind nhiều

<p class="giai-thich" markdown>ASan chèn các bước kiểm tra lúc biên dịch nên phải biên dịch lại với cờ, và nhờ đó thường chậm ít hơn nhiều so với Valgrind, thứ chạy nguyên bản chương trình trong một môi trường theo dõi. Hai ý đầu đảo ngược hoặc sai: ASan không chạy nguyên bản, và nó bắt cả ngoài biên lẫn dùng sau khi trả, không chỉ rò rỉ. Valgrind không biên dịch lại nhưng cũng không nhanh hơn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 7.** Bạn chạy chương trình dưới `-fsanitize=address,undefined`: không có báo cáo nào, mã thoát 0. Kết luận nào đúng nhất?

- Chương trình đã được chứng minh là không có UB nào
- Sanitizer đã hỏng, vì nó phải báo ít nhất một lỗi
- Lần này không thấy lỗi, nhưng chưa chứng minh là sạch
- Thêm `-Wall` rồi chạy lại là đủ để chứng minh chương trình sạch

<p class="giai-thich" markdown>Sanitizer chỉ thấy lỗi **xảy ra trong lần chạy đó**, trên dữ liệu và đường đi của lần đó, nên im lặng chỉ nói "lần này không thấy gì". Không phải chương trình nào cũng có lỗi, nên không có lý do để nói sanitizer hỏng. Cảnh báo `-Wall` cũng chỉ là một lưới thô khác, thêm nó không biến sự im lặng thành bằng chứng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Với `std::vector<int> v = {1, 2, 3};`, hai lệnh `v.at(3)` và `v[3]` khác nhau thế nào?

- Cả hai ném `std::out_of_range`, chỉ khác tên gọi hàm
- `v.at(3)` ném `std::out_of_range`, còn `v[3]` là UB
- Cả hai là UB, vì vector chỉ có chỉ số 0 đến 2
- `v.at(3)` là UB, còn `v[3]` mới ném `std::out_of_range`

<p class="giai-thich" markdown>`at` có kiểm tra biên và ném `std::out_of_range`: đó là hành vi được định nghĩa, bắt được bằng `try`/`catch`. `v[3]` thì không kiểm tra, nên ngoài biên là UB (dưới ASan nó bị báo `heap-buffer-overflow`). Cho nên hai lệnh không giống nhau: chỉ `at` ném ngoại lệ. Và cũng không phải cả hai đều UB, vì `at` được thiết kế để làm điều ngược lại.</p>
</div>

</div>

## 🔑 Tóm tắt

1. UB là khi chuẩn C++ không quy định kết quả: khác lỗi biên dịch (bị chặn từ đầu) và lỗi chạy bình thường (có kết quả định nghĩa rõ); kết quả có thể đúng, sai âm thầm hoặc sập, và đổi theo trình biên dịch, cờ tối ưu và máy, nên "chạy đúng ở máy tôi" không chứng minh gì.
2. UB hay gặp: ngoài biên mảng, dùng sau khi trả, giải phóng hai lần, tràn số nguyên có dấu, giải tham chiếu `nullptr`, đọc biến chưa khởi tạo, data race; rò rỉ bộ nhớ **không** phải UB.
3. `-Wall -Wextra` là lưới thô nhưng rẻ; AddressSanitizer (`-fsanitize=address -g -fno-omit-frame-pointer`) mặc định dừng ở lỗi đầu tiên, báo loại lỗi, dòng `#0`, nơi xin/trả và dòng `SUMMARY`; UBSan (`-fsanitize=undefined`) báo một dòng cho mỗi lỗi không phải địa chỉ như tràn số, dịch bit quá cỡ, `nullptr`.
4. Ghép bằng `-fsanitize=address,undefined`; LeakSanitizer đi kèm ASan; Valgrind (`valgrind --leak-check=full ./chuongtrinh`) không cần biên dịch lại nhưng thường chậm hơn nhiều lần; ThreadSanitizer (`-fsanitize=thread`) dành cho data race và không ghép được với ASan.
5. Công cụ chỉ thấy lỗi xảy ra trong lần chạy đó nên im lặng không chứng minh là sạch; phòng ngừa tốt nhất là RAII, smart pointer, `std::vector`/`std::string`/`at()`, bật cảnh báo và chạy kiểm thử dưới sanitizer.
