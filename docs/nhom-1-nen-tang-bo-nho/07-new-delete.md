# Bài 07 — Cấp phát động `new`/`delete` và ba lỗi kinh điển

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Xin và trả bộ nhớ ở heap đúng cách: `new` đi với `delete`, `new[]` đi với `delete[]`, và biết `new` gọi hàm tạo, `delete` gọi hàm hủy.
    - Nhận ra ba lỗi kinh điển: rò rỉ bộ nhớ, con trỏ treo (dùng sau khi trả), giải phóng hai lần; biết lỗi nào là hành vi không xác định.
    - Chạy được công cụ bắt rò rỉ (AddressSanitizer) và hiểu vì sao quản lý bằng tay mong manh, nên cần RAII ([Bài 08](08-raii.md)).

**Bạn cần biết trước:** [Bài 02](02-stack-heap-static.md) (stack, heap, hàm tạo, hàm hủy), [Bài 03](03-con-tro-co-ban.md) (con trỏ, `*p`, `->`, `nullptr`) và [Bài 05](05-mang-phep-tinh-con-tro.md) (mảng, `p[i]`).

## 🧠 Câu chuyện mở đầu

Quay lại **kho đồ của trường** ở [Bài 02](02-stack-heap-static.md). Khi cần một chỗ để đồ sống lâu hơn một tiết học, bạn đến xin thầy giữ kho một căn phòng. Thầy đưa bạn một **tờ giấy ghi số phòng**. Tờ giấy đó chính là con trỏ, và bạn mang nó về bàn học của mình (stack).

Quy tắc của kho rất đơn giản: **xin thì phải trả**. Dùng xong, bạn mang số phòng ra trả (`delete`), thầy dọn phòng và cho người khác mượn. Có ba cách làm sai, và bài này dạy từng cách:

- **Quên trả:** bạn đi mất, tờ giấy mất theo, căn phòng bị giữ mãi mà không ai biết số để trả. Xin nhiều lần thì kho đầy dần. Đây là **rò rỉ bộ nhớ**.
- **Trả rồi vẫn cầm tờ giấy cũ:** bạn đến đúng số phòng đó và thấy người khác đang ở, hoặc phòng đã dọn trống. Dùng tờ giấy này là **dùng sau khi trả**.
- **Trả hai lần:** thầy ghi sổ "phòng 9 vừa được trả" lần thứ hai, sổ sách rối tung. Đây là **giải phóng hai lần**.

!!! info "Chỗ nào ví dụ kho đồ không còn đúng?"
    Kho thật có thầy nhắc bạn "em chưa trả phòng". C++ **không có ai nhắc**: quên trả thì chương trình vẫn chạy bình thường, và trả sai thì không có ai ngăn bạn lại.

## 📖 Giải thích

### 1. `new` và `delete`: xin một chỗ, trả một chỗ

Ở [Bài 02](02-stack-heap-static.md) bạn đã thấy hình dạng của hai lệnh này. Bây giờ ta học kỹ từng bước.

```text
int* p = new int(5);     // xin chỗ ở heap cho một int, ghi 5 vào đó
std::cout << *p;         // đi theo địa chỉ trong p, đọc ra 5
delete p;                // trả chỗ đó về kho
```

- **`new int(5)`** xin heap một chỗ vừa đủ cho một `int` (4 byte), ghi `5` vào, rồi **trả về địa chỉ** của chỗ đó.
- **`int* p`** là biến con trỏ ([Bài 03](03-con-tro-co-ban.md)) giữ địa chỉ ấy: tờ giấy ghi số phòng. Biến `p` nằm ở stack, còn chỗ chứa số `5` nằm ở heap.
- **`delete p;`** trả chỗ mà `p` đang trỏ tới về kho. Nó trả **thứ `p` trỏ tới**, chứ không xóa biến `p`.

Chương trình đầy đủ, có đánh số các dòng quan trọng:

```cpp
#include <iostream>

int main() {
    int* p = new int(5);                                   // (1)
    std::cout << "*p = " << *p << "\n";                    // (2)
    *p = 7;                                                // (3)
    std::cout << "*p = " << *p << "\n";
    std::cout << "p  = " << p << "  (dia chi o heap)\n";
    std::cout << "&p = " << &p << "  (dia chi cua chinh bien p, o stack)\n";
    delete p;                                              // (4)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `new int(5)` rồi gán vào `p` | Xin heap 4 byte, ghi 5, địa chỉ đặt vào biến `p` | stack: `p` ở 0x7ff0 chứa 0x9000; heap: 0x9000 chứa 5 (địa chỉ minh họa, máy bạn sẽ in số khác) |
| (2) in `*p` | Đi theo `p` tới 0x9000, đọc 5 | in `*p = 5` |
| (3) `*p = 7;` | Ghi 7 vào chỗ ở heap (không đụng tới `p`) | heap: 0x9000 chứa 7 |
| in `*p` | Đọc lại | in `*p = 7` |
| in `p` và `&p` | `p` là địa chỉ ở heap; `&p` là địa chỉ của chính biến `p` ở stack | in hai địa chỉ khác nhau |
| (4) `delete p;` | Trả chỗ 0x9000 về kho. Chỗ đó không còn của ta | heap: 0x9000 đã trả; `p` vẫn chứa 0x9000 (xem mục 4.2) |

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`):

```text
*p = 5
*p = 7
p  = 0x5d9a0a9d1eb0  (dia chi o heap)
&p = 0x7ffe401c88f0  (dia chi cua chinh bien p, o stack)
```

Hai địa chỉ ở máy bạn sẽ là số khác, và chỉ cần thấy chúng **khác nhau rõ rệt**: một số thuộc heap, một số thuộc stack. Dòng cuối của bảng là chỗ cần để ý: sau `delete p;`, biến `p` **vẫn còn đó và vẫn chứa số cũ**, chỉ là căn phòng không còn của bạn.

!!! warning "Hay nhầm"
    `delete p;` không xóa biến `p`, cũng không sửa giá trị trong `p`. Nó chỉ báo cho kho "phòng này tôi trả rồi". Tờ giấy vẫn nằm trong tay bạn, ghi số phòng cũ.

#### Vì sao phải xin ở heap?

Có hai lý do, cả hai đã gặp ở [Bài 02](02-stack-heap-static.md). Lý do thứ nhất: biến ở stack chết khi hàm kết thúc, còn chỗ xin bằng `new` **sống đến khi bạn `delete`**. Chương trình sau cho một hàm xin một chỗ rồi giao nó cho nơi gọi:

```cpp
#include <iostream>

int* taoSo() {
    int* p = new int(42);        // (1)
    return p;                    // (2)
}

int main() {
    int* q = taoSo();            // (3)
    std::cout << "*q = " << *q << "\n";   // (4)
    delete q;                    // (5)
    return 0;
}
```

Dòng (3) xuất hiện hai lần trong bảng vì nó vừa gọi hàm, vừa nhận kết quả về; bảng đánh số theo thứ tự chạy.

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| Bước 1: dòng (3) gọi `taoSo()` | Vào hàm; trên bàn học của `taoSo` có biến `p` | stack: `p` ở 0x7fc0 |
| Bước 2: dòng (1) | Xin heap một `int`, ghi 42 | heap: 0x9000 chứa 42; `p` = 0x9000 |
| Bước 3: dòng (2) `return p;` | Trả **địa chỉ** về nơi gọi (sao chép tờ giấy); hết hàm, bàn học của `taoSo` bị dọn, biến `p` mất | stack của `taoSo` biến mất; heap: 0x9000 vẫn chứa 42 |
| Bước 4: về lại dòng (3) | Kết quả được gán vào `q`: `q` trong `main` nhận địa chỉ 0x9000 | stack: `q` ở 0x7ff0 = 0x9000 |
| Bước 5: dòng (4) in `*q` | Đọc ra 42, chỗ ở heap vẫn nguyên vẹn dù hàm đã xong | in `*q = 42` |
| Bước 6: dòng (5) `delete q;` | Nơi gọi trả chỗ về kho | heap: 0x9000 đã trả |

**Kết quả khi chạy:**

```text
*q = 42
```

Hàm `taoSo` đã kết thúc từ lâu mà số 42 vẫn còn, đó là điều biến cục bộ không làm được (so với tham chiếu tới biến cục bộ ở [Bài 06](06-tham-chieu-const.md)). Đổi lại, có một quy ước phải nhớ: **ai xin thì phải có người trả**. Ở đây `main` nhận địa chỉ nên `main` phải `delete`.

Lý do thứ hai là **kích thước chỉ biết lúc chạy**. Mảng ở stack phải có cỡ cố định viết sẵn trong code; heap thì bạn xin bao nhiêu cũng được, tính ngay lúc chạy (mục 3).

!!! info "Bạn biết Go?"
    Go cũng có `new(int)`: xin một `int` và trả về con trỏ `*int`. Nhưng Go **không có `delete`**: bộ thu gom rác (garbage collector) tự thu hồi khi không còn ai giữ con trỏ. Trong C++ không ai thu hồi giúp bạn: xin bằng `new` thì bạn phải tự trả bằng `delete`. Cũng vì vậy, "rò rỉ" trong Go thường là chuyện khác hẳn: bạn **vẫn giữ tham chiếu** (ví dụ một map toàn cục phình mãi) nên bộ thu gom không dám dọn. Rò rỉ trong C++ thì ngược lại: bạn **đã mất** tờ giấy mà phòng vẫn chưa trả.

!!! question "Hỏi nhanh: `new` hết chỗ thì sao, có trả về `nullptr` không?"
    Với `new` thường thì không. Khi kho hết chỗ, `new` **ném ngoại lệ** `std::bad_alloc` (ném = báo lỗi và dừng hàm hiện tại). Ngoại lệ (exception) là cách C++ báo lỗi bằng cách cắt ngang hàm đang chạy và thoát ra ngoài, hơi giống `panic` của Go ở chỗ hàm bị dừng giữa chừng. Nên viết `if (p == nullptr)` ngay sau `new` thường là thừa; bài này chưa cần xử lý ngoại lệ, chỉ cần biết nó tồn tại.

### 2. `new` gọi hàm tạo, `delete` gọi hàm hủy

Với `int`, `new` chỉ xin chỗ rồi ghi số. Với một struct có hàm tạo và hàm hủy ([Bài 02](02-stack-heap-static.md)), `new` làm thêm một việc: **sau khi xin chỗ, nó gọi hàm tạo** để dựng đối tượng. Và `delete` **gọi hàm hủy trước**, rồi mới trả chỗ về kho. Ta dùng lại struct `Cay` in chữ `tao` và `huy` để nhìn thấy điều đó:

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

int main() {
    std::cout << "--- bat dau\n";
    Cay* p = new Cay(7);                  // (1)
    std::cout << "cao = " << p->cao << "\n";   // (2)
    delete p;                             // (3)
    std::cout << "--- xong\n";
    return 0;
}
```

(1) xin chỗ cho một `Cay` rồi đưa `7` cho hàm tạo. (2) dùng `->` ([Bài 03](03-con-tro-co-ban.md)) để đọc trường `cao` qua con trỏ.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| in `--- bat dau` | Đánh dấu bắt đầu | không đổi |
| (1) `new Cay(7)` | Xin heap 4 byte cho một `Cay`, rồi **gọi hàm tạo** với 7: nó ghi `cao` = 7 và in `tao 7`; địa chỉ đặt vào `p` | stack: `p` = 0x9000; heap: 0x9000 chứa `cao` = 7 (địa chỉ minh họa) |
| (2) | Đọc `p->cao` | in `cao = 7` |
| (3) `delete p;` | **Gọi hàm hủy** trước: in `huy 7`; sau đó trả chỗ 0x9000 về kho | heap: 0x9000 đã trả |
| in `--- xong` | Đánh dấu kết thúc | không đổi |

**Kết quả khi chạy:**

```text
--- bat dau
tao 7
cao = 7
huy 7
--- xong
```

`tao 7` xuất hiện ngay lúc `new`, và `huy 7` ngay lúc `delete`: cặp `new`/`delete` chính là cặp "tạo"/"hủy" của đối tượng ở heap. Nếu không có `delete`, dòng `huy 7` sẽ **không bao giờ in** (Ví dụ 2 chạy thật điều này).

!!! info "Còn `malloc` và `free` thì sao?"
    `malloc` và `free` là cặp xin/trả của ngôn ngữ C (C++ vẫn dùng được, nằm trong `<cstdlib>`). Khác biệt then chốt: chúng chỉ xin và trả **bytes thô**, **không gọi hàm tạo hay hàm hủy**, nên với `Cay` bạn sẽ không thấy `tao` hay `huy`. Trong C++ hiện đại, bạn gần như không cần chúng: dùng `new`/`delete` khi buộc phải tự quản lý, và tốt hơn nữa là dùng các công cụ tự trả ở [Bài 08](08-raii.md) đến [Bài 10](10-shared-ptr-weak-ptr.md). Hai cặp này **không được lẫn**: xin bằng `malloc` thì trả bằng `free`; xin bằng `new` thì trả bằng `delete`.

### 3. Mảng động: `new[]` và `delete[]`

Muốn xin **nhiều món liên tiếp** (một mảng) mà số lượng chỉ biết lúc chạy, viết số lượng trong `[ ]`: `new int[n]`. Kết quả là địa chỉ của món đầu tiên (như tên mảng ở [Bài 05](05-mang-phep-tinh-con-tro.md)), nên dùng được `a[i]`. Để trả, phải dùng dạng có `[]`: **`delete[] a;`**.

```cpp
#include <iostream>

int main() {
    int n = 3;                                  // (1)
    int* a = new int[n];                        // (2)
    for (int i = 0; i < n; i = i + 1) {
        a[i] = (i + 1) * 10;                    // (3)
    }
    for (int i = 0; i < n; i = i + 1) {
        std::cout << a[i] << " ";
    }
    std::cout << "\n";
    delete[] a;                                 // (4)
    return 0;
}
```

`n` là biến thường, có thể là số người dùng nhập; ở đây ta cho sẵn 3 cho gọn.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `int n = 3;` | Biến `n` ở stack | `n` = 3 |
| (2) `new int[n]` | Xin heap 3 món `int` liền nhau (cần 12 byte; thực tế thường xin thêm chút chỗ để nhớ kích thước); địa chỉ món đầu đặt vào `a`. Các món **chưa có giá trị xác định** | heap: 0x9000..0x900b là 3 món chưa ghi; `a` = 0x9000 |
| (3) vòng `for` | Ghi 10, 20, 30 vào từng món qua `a[i]` | heap: món 0 = 10, món 1 = 20, món 2 = 30 |
| vòng `for` in | In ba số | in `10 20 30 ` |
| (4) `delete[] a;` | Trả cả mảng 3 món về kho | heap: vùng 0x9000 đã trả |

**Kết quả khi chạy:**

```text
10 20 30 
```

Lưu ý dòng (2): `new int[n]` **không** tự điền 0. Phải ghi trước (như dòng (3)) rồi mới đọc.

Vì sao có hai dạng `delete`? Vì với mảng đối tượng, `new[]` gọi hàm tạo **cho từng phần tử**, nên `delete[]` phải biết đi qua từng phần tử để gọi hàm hủy của từng cái. Ví dụ 1 ở phần 💻 bên dưới chạy đầy đủ điều này; đây là hai dòng chính của nó:

```text
Cay* v = new Cay[2];     // gọi hàm tạo hai lần (một lần cho mỗi phần tử)
delete[] v;              // gọi hàm hủy hai lần, rồi trả cả vùng
```

`delete[]` biết có bao nhiêu phần tử là việc của thư viện, ta không cần biết cách làm. Luật đi cặp:

| Xin bằng | Trả bằng |
|---|---|
| `new T(...)` | `delete p;` |
| `new T[n]` | `delete[] p;` |
| `malloc(...)` | `free(p);` |

Trả sai cặp (ví dụ xin bằng `new[]` mà trả bằng `delete`) là **hành vi không xác định** (tức chuẩn C++ không hứa chuyện gì sẽ xảy ra; mục 4 giải thích kỹ), xem mục 4.4.

### 4. Ba lỗi kinh điển (và một lỗi nữa)

Trước khi vào từng lỗi, cần một khái niệm. **Hành vi không xác định (undefined behavior, viết tắt UB)** là khi chương trình phạm một luật mà chuẩn C++ nói "kể từ đây, mọi chuyện đều có thể xảy ra": chạy ra kết quả đúng, in số rác, sập, hoặc chạy đúng hôm nay và hỏng ngày mai. Với UB, **không ai hứa trước kết quả**, nên ta không thể "thử rồi thấy ổn là yên tâm". Vì thế các khối code UB dưới đây đều đánh dấu `// bo-qua-kiem-tra` và mình **không ghi kết quả** của chúng.

Một điểm cần phân biệt ngay từ đầu: trong ba lỗi, **rò rỉ không phải UB** (chương trình vẫn đúng luật, chỉ phí bộ nhớ); còn dùng sau khi trả và giải phóng hai lần **là UB**.

#### 4.1 Rò rỉ bộ nhớ (memory leak): xin mà không trả

**Rò rỉ bộ nhớ** là khi bạn xin một chỗ ở heap rồi **không bao giờ trả** nó, và đến lúc mất hết tờ giấy trỏ tới chỗ đó thì không còn cách nào trả nữa. Chỗ bị giữ thì không ai dùng được: chạy lâu, xin nhiều, bộ nhớ đầy dần. Cái đáng sợ là lỗi này **im lặng**: chương trình vẫn chạy, vẫn in đúng, thoát với mã 0.

Chương trình `Cay` ở mục 2, nhưng **bỏ `delete`**, trông như sau (đầy đủ ở Ví dụ 2, phần 💻 bên dưới):

```text
Cay* p = new Cay(7);
std::cout << "cao = " << p->cao << "\n";
// quên delete p;
```

Kết quả không có dòng `huy 7`: hàm hủy không bao giờ chạy, và chỗ ở heap bị bỏ lại. Khi chương trình kết thúc, hệ điều hành thường thu hồi mọi thứ của tiến trình đó, nên bạn không thấy hậu quả ngay; nhưng một chương trình chạy mãi (máy chủ, dịch vụ) mà rò rỉ mỗi lần xử lý một yêu cầu thì sớm muộn sẽ hết bộ nhớ.

#### 4.2 Con trỏ treo và dùng sau khi trả (use-after-free)

**Con trỏ treo (dangling pointer)** là con trỏ còn giữ địa chỉ của một chỗ **đã hết hiệu lực** (đã bị `delete`, hoặc là biến cục bộ đã bị dọn). **Dùng sau khi trả (use-after-free)** là hành động đọc hay ghi qua con trỏ treo đó. Trong câu chuyện: bạn vẫn cầm tờ giấy ghi phòng 9 dù đã trả phòng 9, và bước vào.

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* p = new int(5);
    delete p;                       // trả phòng
    std::cout << *p << "\n";        // vẫn dùng tờ giấy cũ: UB
    return 0;
}
```

Chương trình này **biên dịch được** và nhìn rất vô hại. Nhưng sau `delete p;`, chỗ đó không còn của bạn: kho có thể đã cho người khác mượn, hoặc dùng vào việc khác. Đọc nó là hành vi không xác định, nên không có kết quả nào để mà ghi lại ở đây.

Lỗi này nguy hiểm vì có lúc **hôm nay vẫn chạy "đúng"** (chỗ chưa bị ai ghi đè nên còn số cũ), rồi hỏng ở một lần chạy khác hay trên máy khác.

#### 4.3 Giải phóng hai lần (double free)

**Giải phóng hai lần (double free)** là gọi `delete` hai lần cho **cùng một chỗ**. Lần thứ hai bạn trả một căn phòng đã được trả (và có thể đã cho người khác mượn): sổ sách kho bị hỏng.

```cpp
// bo-qua-kiem-tra
int main() {
    int* p = new int(5);
    delete p;
    delete p;                       // trả lần thứ hai: UB
    return 0;
}
```

Đây cũng là hành vi không xác định, nên mình không ghi kết quả. Thực tế nó thường xảy ra khi **hai con trỏ cùng trỏ vào một chỗ** và mỗi bên đều nghĩ "mình phải trả", hoặc khi một hàm trả và nơi gọi cũng trả.

#### 4.4 Lỗi thứ tư: trộn `new[]` với `delete`

Xin bằng `new[]` thì phải trả bằng `delete[]` (mục 3). Trả bằng `delete` thường (hoặc ngược lại) là hành vi không xác định:

```cpp
// bo-qua-kiem-tra
int main() {
    int* a = new int[4];
    delete a;                       // sai cặp: phải là delete[] a;  (UB)
    return 0;
}
```

Biên dịch được, nhưng mình không ghi kết quả vì đó là UB. Với struct có hàm hủy hay không, chuẩn đều không hứa điều gì sẽ xảy ra.

!!! warning "Hay nhầm"
    "Mảng `int` đơn giản thì `delete` thay `delete[]` cũng không sao" là suy nghĩ nguy hiểm. Chuẩn C++ vẫn gọi đó là hành vi không xác định, dù một lần chạy có thể trông bình thường. Nhớ cặp: `new[]` thì `delete[]`.

#### 4.5 Thói quen `p = nullptr` sau `delete`

Một thói quen tốt: ngay sau `delete p;`, gán `p = nullptr;`. Lý do: chuẩn C++ đảm bảo **`delete` một con trỏ rỗng (`nullptr`) là việc không làm gì cả, hoàn toàn an toàn**. Vậy nếu lỡ `delete p;` lần nữa, thì lần sau chỉ là `delete nullptr`, không còn là trả hai lần.

```cpp
#include <iostream>

int main() {
    int* p = new int(5);
    delete p;                    // (1)
    p = nullptr;                 // (2)
    delete p;                    // (3)
    std::cout << "van chay binh thuong\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `new int(5)` | Xin chỗ, `p` giữ địa chỉ | `p` = 0x9000; heap: 0x9000 chứa 5 (địa chỉ minh họa) |
| (1) `delete p;` | Trả chỗ 0x9000 | `p` vẫn = 0x9000 (treo) |
| (2) `p = nullptr;` | Xóa số cũ khỏi tờ giấy | `p` = nullptr |
| (3) `delete p;` | Trả "phòng rỗng": không làm gì | không đổi |

**Kết quả khi chạy:**

```text
van chay binh thuong
```

Nhưng đây **không phải thuốc chữa mọi thứ**, vì nó chỉ sửa đúng con trỏ bạn gán. Nếu có một con trỏ khác cùng giữ địa chỉ cũ, con trỏ đó vẫn treo:

```cpp
// bo-qua-kiem-tra
#include <iostream>

int main() {
    int* p = new int(1);
    int* q = p;                     // q cũng giữ địa chỉ này
    delete p;
    p = nullptr;                    // chỉ p an toàn
    std::cout << *q << "\n";        // q vẫn treo: dùng sau khi trả, UB
    return 0;
}
```

Gán `nullptr` chỉ giúp được một phần: nó chặn việc `delete` lần hai qua `p`, và biến lỗi dùng `p` thành lỗi dễ thấy hơn (dùng `nullptr` thì thường sập ngay, nhưng đó cũng là UB, không phải lời hứa). Nó không thể làm gì cho `q`.

### 5. Làm sao tìm rò rỉ: AddressSanitizer và Valgrind

Đọc code bằng mắt rất khó thấy một dòng `delete` bị thiếu. May là có công cụ bắt giúp. **AddressSanitizer (viết tắt ASan)** là công cụ của `g++` (và `clang++`): bạn bật nó bằng cờ khi biên dịch, nó chèn thêm bước theo dõi mọi lần xin và trả bộ nhớ, và báo lỗi lúc chạy. **LeakSanitizer** là phần của ASan chuyên tìm rò rỉ: khi chương trình kết thúc, nó liệt kê những chỗ đã xin mà chưa trả.

Lệnh biên dịch và chạy (cờ `-g` để báo cáo có số dòng, `-fno-omit-frame-pointer` để danh sách hàm đầy đủ hơn):

```text
g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer -o chuongtrinh chuongtrinh.cpp
./chuongtrinh
```

Mình đã chạy lệnh này với chương trình rò rỉ vừa rồi (Ví dụ 2 ở phần 💻 bên dưới). Trong file đó, các dòng quan trọng được đánh số như sau (số đầu dòng là số dòng của file):

```text
14: int main() {
15:     std::cout << "--- bat dau\n";
16:     Cay* p = new Cay(7);                  // (1)
17:     std::cout << "cao = " << p->cao << "\n";
18:     // (2) quen delete p;
```

Báo cáo thật (đã **rút gọn**: bỏ số tiến trình, địa chỉ và đường dẫn trên máy mình, bỏ bớt dòng):

```text
ERROR: LeakSanitizer: detected memory leaks

Direct leak of 4 byte(s) in 1 object(s) allocated from:
    #0 ... in operator new(unsigned long) ...
    #1 ... in main ...:16
    #2 ... in __libc_start_call_main ...

SUMMARY: AddressSanitizer: 4 byte(s) leaked in 1 allocation(s).
```

Cách đọc: "Direct leak of 4 byte(s) in 1 object(s)" là có 1 chỗ 4 byte bị bỏ rơi; các dòng `#0`, `#1`... là dấu vết "chỗ này được xin ở đâu", và dòng `#1 ... main ...:16` chỉ **đúng dòng 16** có `new Cay(7)` ở khung số dòng ngay trên. Chương trình bị ASan chạy kết thúc với **mã thoát khác 0** (mình thấy là 1), dù bản không có ASan thoát mã 0.

Hai lưu ý trung thực. Thứ nhất, ASan chỉ báo những gì **xảy ra trong lần chạy đó**; đoạn code chưa chạy tới thì nó không thấy. Thứ hai, LeakSanitizer đôi khi bỏ sót (ví dụ vì một giá trị cũ còn sót trong bộ nhớ làm nó tưởng "vẫn còn trỏ tới"), nên im lặng không chứng minh là sạch.

**Valgrind** là công cụ khác làm cùng loại việc: bạn **không cần biên dịch lại** chương trình, chỉ chạy nó qua công cụ:

```text
valgrind --leak-check=full ./chuongtrinh
```

Valgrind chạy chương trình trong một môi trường do nó dựng lên, theo dõi từng lần xin và trả bộ nhớ, và khi chương trình kết thúc thì liệt kê những khối chưa được trả cùng nơi đã xin chúng. Valgrind **chưa được cài trên máy mình dùng để viết bài**, nên mình chỉ ghi lệnh và mô tả bằng lời, không dán kết quả. [Bài 13](13-memory-leak-ub.md) sẽ nói kỹ hơn về các công cụ này.

### 6. Vì sao quản lý bằng tay mong manh

Bốn lỗi trên có chung nguồn gốc: **việc trả bộ nhớ phụ thuộc vào việc bạn nhớ viết `delete` đúng chỗ, đúng một lần, đúng cặp**. Chương trình thật có nhiều đường đi, và mỗi đường phải gặp đúng một `delete`. Chỉ cần một hàm có **thoát sớm** (`return` giữa chừng) là đã có đường bị sót. Đây là phần lõi của hàm trong Ví dụ 3 (phần 💻 bên dưới):

```text
void xuLy(int cao) {
    Cay* p = new Cay(cao);
    if (cao < 0) {
        return;          // thoát sớm: nhảy qua delete
    }
    delete p;
}
```

Cũng như thế với ngoại lệ (mục 1): nếu một dòng ở giữa hàm ném ngoại lệ, hàm bị cắt ngang và **dòng `delete` ở cuối hàm không bao giờ chạy**. Bạn có thể viết `delete` thêm vào mọi đường thoát, nhưng code càng dài, càng dễ sót, và ai sửa code sau này cũng phải nhớ.

!!! info "Bạn biết Go?"
    Trong Go, bạn không bị chuyện này: bộ thu gom rác lo bộ nhớ, còn việc cần dọn (đóng file, mở khóa) thì bạn viết `defer` ngay sau khi mở, và `defer` chạy dù hàm thoát đường nào. C++ có cách tương đương nhưng đi theo hướng khác: gắn việc dọn vào **hàm hủy**, vì hàm hủy chạy đúng lúc đối tượng chết. Kỹ thuật đó tên là **RAII**, và là nội dung [Bài 08](08-raii.md). Bài sau đó ([Bài 09](09-unique-ptr.md), [Bài 10](10-shared-ptr-weak-ptr.md)) là các con trỏ thông minh dùng nó để tự trả bộ nhớ.

## 💻 Ví dụ code

### Ví dụ 1: `new Cay[2]` và `delete[]`

```cpp
#include <iostream>

int dem = 0;                    // (1)

struct Cay {
    int so;
    Cay() {                     // (2)
        dem = dem + 1;
        so = dem;
        std::cout << "tao " << so << "\n";
    }
    ~Cay() {
        std::cout << "huy " << so << "\n";
    }
};

int main() {
    Cay* v = new Cay[2];        // (3)
    std::cout << "--- giua\n";
    delete[] v;                 // (4)
    std::cout << "--- xong\n";
    return 0;
}
```

(1) là biến toàn cục đếm số lần tạo ([Bài 02](02-stack-heap-static.md)) để mỗi `Cay` có số thứ tự riêng. (2) là hàm tạo **không nhận tham số**: `new Cay[2]` tạo hai phần tử mà không đưa giá trị nào, nên struct phải có hàm tạo như vậy.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) `new Cay[2]` | Xin heap cho hai `Cay` liền nhau (cần 8 byte, thực tế thường xin thêm chút chỗ để nhớ số phần tử), rồi gọi hàm tạo cho **từng phần tử**: lần 1 in `tao 1`, lần 2 in `tao 2`; địa chỉ phần tử đầu đặt vào `v` | heap: 0x9000 chứa `so` = 1, 0x9004 chứa `so` = 2; `v` = 0x9000 (địa chỉ minh họa) |
| in `--- giua` | Đánh dấu | không đổi |
| (4) `delete[] v;` | Gọi hàm hủy cho **từng phần tử**: in `huy 2` rồi `huy 1`; sau đó trả cả vùng về kho | heap: vùng 0x9000 đã trả |
| in `--- xong` | Đánh dấu | không đổi |

**Kết quả khi chạy:**

```text
tao 1
tao 2
--- giua
huy 2
huy 1
--- xong
```

Hai lần `tao`, hai lần `huy`: đúng "mỗi phần tử một lần". Chuẩn C++ quy định `delete[]` hủy các phần tử theo thứ tự **ngược** với lúc tạo, nên `huy 2` đến trước `huy 1`.

**Thử thay đổi: ở (4) viết `delete v;` thay vì `delete[] v;`.** Mình **không chạy** biến thể này: đó là hành vi không xác định (mục 4.4), nên có chạy ra gì cũng không đại diện cho điều gì. Điều chắc chắn chỉ là: nó biên dịch được và sai luật.

### Ví dụ 2: quên `delete` (rò rỉ)

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

int main() {
    std::cout << "--- bat dau\n";
    Cay* p = new Cay(7);                  // (1)
    std::cout << "cao = " << p->cao << "\n";
    // (2) quen delete p;
    std::cout << "--- xong\n";
    return 0;
}
```

Đây chính là chương trình ở mục 2, chỉ khác là tại (2) **không có `delete p;`**.

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| in `--- bat dau` | Đánh dấu | không đổi |
| (1) `new Cay(7)` | Xin heap, gọi hàm tạo: in `tao 7`; `p` giữ địa chỉ | stack: `p` = 0x9000; heap: 0x9000 chứa `cao` = 7 (địa chỉ minh họa) |
| in `cao = 7` | Đọc qua `p->cao` | không đổi |
| (2) không có gì | Không `delete`, nên **hàm hủy không chạy** và chỗ không được trả | không đổi |
| in `--- xong`, `return 0;` | `main` kết thúc, biến `p` ở stack bị dọn, nhưng chỗ ở heap vẫn **chưa được trả**: không còn ai giữ số phòng | heap: 0x9000 bị bỏ rơi (rò rỉ) |

**Kết quả khi chạy** (không có ASan, thoát mã 0):

```text
--- bat dau
tao 7
cao = 7
--- xong
```

Nhìn kỹ: dòng `huy 7` **không xuất hiện**. Chương trình không báo lỗi, không sập, mã thoát vẫn là 0: rò rỉ không phải hành vi không xác định, chương trình vẫn đúng luật, chỉ là bỏ rơi một chỗ ở heap. Cũng chính vì im lặng như thế mà ta cần công cụ (mục 5).

Khi biên dịch lại với `-fsanitize=address` thì báo cáo ở mục 5 hiện ra, trỏ vào dòng của (1).

**Thử thay đổi: thêm `delete p;` vào chỗ (2).** Mình đã chạy: dòng `huy 7` xuất hiện giữa `cao = 7` và `--- xong` (giống hệt kết quả ở mục 2), và với ASan thì không còn báo cáo rò rỉ nào, chương trình thoát mã 0.

### Ví dụ 3: thoát sớm làm sót `delete`

```cpp
#include <iostream>

struct Cay {
    int cao;
    Cay(int c) {
        cao = c;
        std::cout << "tao " << cao << "\n";
    }
    ~Cay() {
        std::cout << "huy " << cao << "\n";
    }
};

void xuLy(int cao) {
    Cay* p = new Cay(cao);                // (1)
    if (cao < 0) {
        std::cout << "cao am, thoat som\n";
        return;                           // (2)
    }
    std::cout << "xu ly cay cao " << p->cao << "\n";
    delete p;                             // (3)
}

int main() {
    xuLy(5);
    xuLy(-1);
    std::cout << "xong\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `xuLy(5)`, (1) | Xin heap, hàm tạo in `tao 5` | heap: một `Cay` có `cao` = 5 |
| `cao < 0`? | 5 không nhỏ hơn 0, bỏ qua `if` | không đổi |
| in `xu ly cay cao 5` | Dùng cây | in dòng đó |
| (3) `delete p;` | Hàm hủy in `huy 5`, trả chỗ | heap: sạch |
| `xuLy(-1)`, (1) | Xin heap, hàm tạo in `tao -1` | heap: một `Cay` có `cao` = -1 |
| `cao < 0`? | Đúng: in `cao am, thoat som` | không đổi |
| (2) `return;` | Thoát hàm ngay, **nhảy qua (3)**; biến `p` mất | heap: `Cay` cao -1 bị bỏ rơi (rò rỉ) |
| in `xong` | Quay về `main`, in dòng cuối | in `xong` |

**Kết quả khi chạy:**

```text
tao 5
xu ly cay cao 5
huy 5
tao -1
cao am, thoat som
xong
```

Lần gọi đầu có đủ cặp `tao 5` / `huy 5`. Lần gọi sau có `tao -1` mà **không có `huy -1`**. Cùng một hàm, hai đường đi, chỉ một đường trả bộ nhớ: đó chính là sự mong manh ở mục 6. Chương trình vẫn thoát mã 0, giống ví dụ 2.

**Thử thay đổi: chạy ví dụ này với ASan.** Mình đã chạy thật (cùng lệnh ở mục 5). Chương trình in như trên, rồi LeakSanitizer báo (rút gọn, bỏ số tiến trình, địa chỉ và đường dẫn):

```text
ERROR: LeakSanitizer: detected memory leaks

Direct leak of 4 byte(s) in 1 object(s) allocated from:
    #0 ... in operator new(unsigned long) ...
    #1 ... in xuLy(int) ...:15
    #2 ... in main ...:26
    #3 ... in __libc_start_call_main ...

SUMMARY: AddressSanitizer: 4 byte(s) leaked in 1 allocation(s).
```

Mã thoát là 1. Dòng `#1` chỉ vào `new Cay(cao)` bên trong `xuLy` (dòng 15 của file, tức dòng (1)), và `#2` là lời gọi `xuLy(-1)` ở `main` (dòng 26): đúng chỗ rò rỉ. Chỉ có một khối bị báo, vì lần gọi `xuLy(5)` đã trả đúng. Sửa thật sự là thêm `delete p;` trước `return;` ở (2), hoặc tốt hơn là dùng RAII ([Bài 08](08-raii.md)) để khỏi phải nhớ.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`new` khác `malloc` thế nào?"
    `new` là toán tử của C++: nó xin bộ nhớ **và gọi hàm tạo** để dựng đối tượng, trả về con trỏ đúng kiểu, và khi hết chỗ thì ném ngoại lệ `std::bad_alloc`. `malloc` là hàm của C: chỉ xin bytes thô, **không gọi hàm tạo**, trả về `void*` (phải ép kiểu), và khi hết chỗ thì trả `nullptr`. Tương ứng, `delete` gọi hàm hủy rồi trả bộ nhớ, còn `free` chỉ trả bytes. Hai cặp không được lẫn lộn, và C++ hiện đại gần như không dùng `malloc`/`free`.

??? question "`delete` khác `delete[]` thế nào?"
    `delete p` dùng cho thứ xin bằng `new T`: gọi hàm hủy một lần rồi trả chỗ. `delete[] p` dùng cho thứ xin bằng `new T[n]`: gọi hàm hủy cho **từng phần tử** (theo thứ tự ngược) rồi trả cả vùng. Dùng sai cặp là hành vi không xác định, kể cả khi kiểu là `int` đơn giản.

??? question "Phân biệt rò rỉ bộ nhớ, con trỏ treo và giải phóng hai lần."
    Rò rỉ: xin mà không trả; chương trình vẫn đúng luật, chỉ tốn bộ nhớ dần (không phải UB). Con trỏ treo: con trỏ còn giữ địa chỉ của chỗ đã trả hoặc đã hết hiệu lực; đọc hay ghi qua nó là use-after-free, là UB. Giải phóng hai lần: `delete` cùng một chỗ hai lần, là UB. Rò rỉ là "quên trả", hai lỗi còn lại là "trả sai hoặc dùng sai sau khi trả".

??? question "Làm sao tìm rò rỉ bộ nhớ?"
    Cách thông dụng nhất là biên dịch với `-fsanitize=address -g`: khi chạy xong, LeakSanitizer liệt kê những chỗ chưa trả cùng dòng code đã xin chúng. Cách khác là Valgrind (`valgrind --leak-check=full ./chuongtrinh`), không cần biên dịch lại nhưng chạy chậm hơn. Cả hai chỉ thấy những gì xảy ra trong lần chạy đó, nên cần chạy với dữ liệu và đường đi đủ rộng. Tốt nhất vẫn là thiết kế để khó rò rỉ ngay từ đầu (RAII, con trỏ thông minh).

??? question "Vì sao nên tránh `new`/`delete` trần?"
    Vì việc trả bộ nhớ phụ thuộc vào việc người viết nhớ `delete` đúng một lần trên **mọi** đường thoát của hàm, kể cả `return` sớm và ngoại lệ; chỉ cần sót một đường là rò rỉ, thừa một lần là double free. Thay vào đó, dùng đối tượng tự quản lý (`std::vector`, `std::string`, `std::unique_ptr`, `std::shared_ptr`) để hàm hủy của chúng tự trả bộ nhớ đúng lúc. Đây là ý tưởng RAII ở [Bài 08](08-raii.md).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng chương trình in đúng thì không rò rỉ"
    Rò rỉ không đổi output và không làm sập chương trình (ví dụ 2). Dấu hiệu duy nhất ở output có thể chỉ là một dòng "huy" **bị thiếu**; còn thường thì phải dùng công cụ như ASan. Nhìn kết quả đúng chưa đủ để kết luận là sạch.

!!! warning "Lỗi 2: Dùng con trỏ sau `delete`, hoặc `delete` hai lần"
    Cả hai là hành vi không xác định, nên có thể "chạy được" một lần rồi hỏng lần khác. Sau `delete p;`, coi chỗ đó là của người khác. Gán `p = nullptr;` giúp với chính `p`, nhưng không giúp các con trỏ khác cùng giữ địa chỉ đó (mục 4.5).

!!! warning "Lỗi 3: Sai cặp `new[]` / `delete`"
    `new[]` phải đi với `delete[]`; `new` phải đi với `delete`; `malloc` đi với `free`. Trộn các cặp là hành vi không xác định (mục 3 và 4.4).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="07" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Với struct `Cay` có hàm tạo và hàm hủy, câu `Cay* p = new Cay(7);` rồi `delete p;` làm gì?

- `new` chỉ xin chỗ, còn hàm tạo chạy khi `delete` được gọi
- `new` gọi hàm tạo, còn `delete` chỉ trả chỗ mà không gọi hàm hủy
- `new` xin chỗ rồi gọi hàm tạo, `delete` gọi hàm hủy rồi trả chỗ
- `new` và `delete` chỉ làm việc với bytes, không gọi hàm nào

<p class="giai-thich" markdown>`new` làm hai việc theo thứ tự: xin chỗ ở heap, rồi chạy hàm tạo để dựng đối tượng; `delete` làm ngược lại: chạy hàm hủy trước, rồi mới trả chỗ (ví dụ ở mục 2 in `tao 7` rồi `huy 7`). Việc hàm tạo chỉ chạy lúc `delete` là đảo ngược thứ tự thật. Nói `delete` không gọi hàm hủy là nhầm với việc quên `delete`; chính `delete` mới làm hàm hủy chạy. Còn "chỉ làm việc với bytes" là đặc điểm của `malloc` và `free`, không phải của `new` và `delete`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn code sau (`Cay` in `tao n` ở hàm tạo và `huy n` ở hàm hủy). Chương trình in ra theo thứ tự nào?

```text
int main() {
    Cay a(1);
    Cay* p = new Cay(2);
    delete p;
    return 0;
}
```

- `tao 1, tao 2, huy 2, huy 1`, vì `a` chết ở `}`
- `tao 1, tao 2, huy 2`, vì `a` nằm ở stack nên không có hàm hủy
- `tao 1, tao 2, huy 1, huy 2`, vì hủy theo đúng thứ tự tạo ra
- `tao 2, tao 1, huy 2, huy 1`, vì `new` chạy trước biến `a`

<p class="giai-thich" markdown>Hai biến được tạo theo thứ tự viết nên `tao 1` rồi `tao 2`. `delete p;` hủy cây ở heap ngay lúc đó (`huy 2`), còn `a` là biến cục bộ nên hàm hủy của nó chạy khi chạy tới `}` của `main` (`huy 1`); mình đã chạy ra đúng dãy này. Đối tượng ở stack vẫn có hàm hủy, đó là [Bài 02](02-stack-heap-static.md), nên dãy thiếu `huy 1` sai. Dãy hủy `1` trước `2` bỏ qua việc `delete p;` nằm trước `}`. Còn dãy tạo `2` trước `1` sai vì dòng `Cay a(1);` được chạy trước dòng có `new`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Mảng xin bằng `int* a = new int[10];` thì phải trả bằng lệnh nào?

- `delete a;`, vì `a` là một con trỏ
- `free(a);`, vì đó là mảng
- `delete *a;`, vì phải xóa giá trị mà `a` trỏ tới
- `delete[] a;`, vì xin bằng `new[]`

<p class="giai-thich" markdown>Luật đi cặp: `new[]` đi với `delete[]`, vì `delete[]` biết đây là cả mảng và đi qua từng phần tử để gọi hàm hủy. `delete a;` là dạng dành cho `new` đơn, và dùng với `new[]` là hành vi không xác định. `free` là cặp của `malloc`, không phải của `new`. Còn `delete *a;` là nhầm: `delete` nhận chính con trỏ (địa chỉ của chỗ cần trả), không phải giá trị đọc ra qua `*a`, và `g++` báo lỗi `type ‘int’ argument given to ‘delete’, expected pointer` (mình đã biên dịch).</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn code sau. Lỗi nằm ở đâu?

```text
int* a = new int[4];
a[0] = 1;
delete a;
```

- Không có lỗi, vì mảng `int` đơn giản thì `delete` hay `delete[]` đều được
- Dòng cuối: `new[]` mà trả bằng `delete` là hành vi không xác định
- Dòng thứ hai: không được ghi vào chỗ vừa xin bằng `new[]` khi chưa khởi tạo
- Dòng đầu: `new int[4]` phải được ép kiểu trước khi gán

<p class="giai-thich" markdown>`new[]` phải đi với `delete[]`; trả bằng `delete` thường là hành vi không xác định, kể cả với `int` (ví dụ 4.4). Câu nói "mảng đơn giản thì thế nào cũng được" là sai: chuẩn không phân biệt kiểu đơn giản hay phức tạp, và một lần chạy trông ổn không chứng minh gì. Dòng thứ hai hoàn toàn hợp lệ vì chỗ vừa xin là của bạn để ghi. Dòng đầu cũng đúng cú pháp: `new int[4]` trả về `int*` nên không cần ép kiểu.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Đọc đoạn code sau. Chương trình sai ở đâu?

```text
int* p = new int(1);
int* q = p;
delete p;
p = nullptr;
std::cout << *q;
```

- Rò rỉ, vì không còn ai trả chỗ đó
- Giải phóng hai lần, vì cả `p` lẫn `q` đều bị trả
- Dùng sau khi trả, vì `q` vẫn giữ địa chỉ cũ
- Không sai, vì `p = nullptr` đã làm mọi thứ an toàn

<p class="giai-thich" markdown>`delete p;` trả chỗ mà cả `p` lẫn `q` đang trỏ tới, rồi `*q` đọc đúng chỗ đã trả: đó là dùng sau khi trả, tức hành vi không xác định. `p = nullptr` chỉ sửa tờ giấy `p`, còn `q` vẫn ghi số phòng cũ. Không có rò rỉ, vì chỗ đã được trả. Cũng không có giải phóng hai lần, vì `delete` chỉ gọi một lần (`q` không bị `delete`).</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Điều nào sau đây KHÔNG phải hành vi không xác định?

- Gọi `delete p;` hai lần liên tiếp cho cùng một chỗ ở heap
- Xin bằng `new` rồi quên `delete` đến hết chương trình
- Đọc `*q` sau khi chỗ mà `q` đang trỏ tới đã bị `delete`
- Xin bằng `new[]` rồi lại trả bằng `delete` thường

<p class="giai-thich" markdown>Quên `delete` là rò rỉ: chương trình vẫn đúng luật và thoát bình thường, chỉ lãng phí bộ nhớ (ví dụ 2 in kết quả và thoát mã 0). Ba trường hợp còn lại đều vi phạm luật của chuẩn nên là hành vi không xác định: trả hai lần, dùng sau khi trả, và sai cặp `new[]`/`delete`. Đừng nhầm "ít gây lỗi quan sát được" với "hợp lệ": rò rỉ là không UB vì chuẩn không cấm nó, còn những lỗi kia bị cấm dù một lần chạy có vẻ ổn.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Bạn biên dịch chương trình `Cay` có `new Cay(7)` mà không có `delete` (như ví dụ 2) với `-fsanitize=address -g` rồi chạy. Điều gì xảy ra?

- Nó báo lỗi ngay lúc biên dịch, vì code thiếu lệnh `delete`
- Nó chạy y hệt bản thường và không in thêm gì ra màn hình
- Nó tự thêm `delete` vào chỗ còn thiếu rồi chạy tiếp bình thường
- Nó in LeakSanitizer kèm dòng `new`, mã thoát khác 0

<p class="giai-thich" markdown>ASan theo dõi các lần xin và trả lúc chạy; với chương trình ở ví dụ 2, lúc kết thúc nó báo `LeakSanitizer: detected memory leaks`, chỉ ra chỗ 4 byte được xin ở dòng nào, và chương trình thoát với mã khác 0 (mình thấy 1). Nó không báo lúc biên dịch, vì thiếu `delete` là chuyện của lúc chạy, không phải lỗi cú pháp. Nó cũng không sửa code giúp bạn. Nói "chạy y hệt bản thường" bỏ qua đúng thứ ASan thêm vào: dòng báo cáo và mã thoát.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 8.** Đọc đoạn code sau (`Cay` in `tao n` và `huy n`). Chương trình in ra gì?

```text
void f(int s, bool loi) {
    Cay* p = new Cay(s);
    if (loi) return;
    delete p;
}
int main() { f(1, true); f(2, false); return 0; }
```

- `tao 1, tao 2, huy 2`: lần thoát sớm không có `huy`
- `tao 1, huy 1, tao 2, huy 2`: mỗi lần gọi đủ cặp
- `tao 1, tao 2, huy 1, huy 2`: hủy sau khi cả hai đã được tạo xong
- `tao 1, tao 2`: hàm hủy chưa chạy lần nào

<p class="giai-thich" markdown>`f(1, true)` gặp `return` trước dòng `delete`, nên cây số 1 được tạo mà không bao giờ bị hủy (rò rỉ). `f(2, false)` đi hết hàm, nên có `tao 2` rồi `huy 2`. Mình đã chạy và thấy đúng dãy này. Dãy "đủ cặp mỗi lần" quên mất đường thoát sớm, còn dãy chỉ có hai dòng `tao` quên rằng lần gọi thứ hai có `delete`. Dãy hủy `1` sau `2` cho rằng cây 1 vẫn được hủy ở đâu đó, nhưng không có dòng code nào làm việc đó.</p>
</div>

</div>

## 🔑 Tóm tắt

1. `new T(...)` xin chỗ ở heap rồi gọi hàm tạo và trả về địa chỉ; `delete p` gọi hàm hủy rồi trả chỗ; chỗ xin bằng `new` sống đến khi bạn tự `delete`, và ai xin thì phải có người trả.
2. Mảng động xin bằng `new T[n]` và trả bằng `delete[]`, gọi hàm tạo/hủy cho từng phần tử; cặp phải đúng: `new` với `delete`, `new[]` với `delete[]`, `malloc` với `free` (và `malloc`/`free` không gọi hàm tạo/hủy).
3. Rò rỉ (quên trả) không phải UB, im lặng, và hàm hủy không chạy; con trỏ treo dùng sau khi trả (use-after-free), giải phóng hai lần và trộn `new[]` với `delete` đều là hành vi không xác định, không ai hứa kết quả.
4. `p = nullptr` sau `delete` làm `delete p` lần nữa vô hại, nhưng chỉ sửa đúng con trỏ `p`: các con trỏ khác giữ địa chỉ cũ vẫn treo.
5. Tìm rò rỉ bằng `-fsanitize=address -g` (LeakSanitizer) hoặc Valgrind, nhưng LeakSanitizer đôi khi bỏ sót nên im lặng không chứng minh là sạch; thoát sớm hay ngoại lệ dễ làm sót `delete`, vì vậy cần RAII ([Bài 08](08-raii.md)) thay vì `new`/`delete` trần.
