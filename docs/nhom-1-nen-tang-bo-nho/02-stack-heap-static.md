# Bài 02 — Ba vùng nhớ: stack, heap và vùng tĩnh

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được một biến nằm ở stack, heap hay vùng tĩnh, và nó sống đến khi nào.
    - Đọc được thứ tự "ra đời, chết" của đối tượng cục bộ, global, `static` và đối tượng xin bằng `new`.
    - Trả lời được câu hỏi phỏng vấn: "đối tượng của một class khai báo global nằm ở heap hay stack?".

## 🧠 Câu chuyện mở đầu

Ở [Bài 01](01-bo-nho-byte-dia-chi.md) ta có một dãy tủ khóa dài, mỗi ngăn đựng một byte. Nhưng dãy tủ đó không dùng chung một kiểu cho mọi thứ. Chương trình C++ chia nó thành ba khu (còn một khu chứa chính code chương trình, tạm bỏ qua), và mỗi khu có luật riêng. Hãy hình dung một lớp học:

- **Cái bàn học của bạn (stack).** Nhỏ, ngay trước mặt, lấy đồ ra rất nhanh. Khi hết giờ học, bàn tự được dọn sạch mà bạn không cần làm gì. Chỗ này là nơi sống của **biến cục bộ** (biến khai báo trong một hàm).
- **Kho đồ của trường (heap).** Rộng hơn bàn học rất nhiều, nhưng bạn phải **tự xin** thủ kho một chỗ, và phải **tự trả** khi xong. Quên trả thì chỗ đó bị giữ mãi.
- **Bảng treo trên tường lớp (vùng tĩnh).** Được treo từ lúc lớp mở cửa và chỉ gỡ khi lớp đóng cửa. Nó ở đó suốt thời gian lớp học. Chỗ này là nơi của **biến global** (biến khai báo ngoài mọi hàm) và các biến `static`.

Cả bài này chỉ trả lời hai câu hỏi cho từng biến: **nó nằm ở khu nào**, và **nó sống đến bao giờ**.

!!! info "Chỗ nào ví dụ lớp học không còn đúng?"
    Trong máy thật, "bàn học", "kho" và "bảng tường" không phải ba căn phòng riêng. Chúng là ba vùng của cùng một dãy địa chỉ, mà hệ điều hành chia cho chương trình của bạn. Và "thủ kho" không phải một người, mà là một đoạn code có sẵn đi kèm chương trình, lo việc tìm chỗ trống.

## 📖 Giải thích

### 1. Hàm gọi hàm, và "khung" của mỗi lần gọi

**Hàm** là một đoạn code có tên, bạn có thể gọi nhiều lần. Bạn đã gặp một hàm là `main`. Đây là một hàm do ta tự viết, giống `func nhanDoi(so int) int` trong Go:

```text
int nhanDoi(int so) {
    int ketQua = so * 2;
    return ketQua;
}
```

Đọc dòng đầu: `int` đứng trước tên là **kiểu trả về** (hàm trả ra một số nguyên), `nhanDoi` là tên hàm, `int so` trong ngoặc là **tham số** (thứ ta đưa cho hàm khi gọi: kiểu `int`, tên `so`). `return ketQua;` trả giá trị về cho nơi gọi. Gọi hàm: `nhanDoi(10)`.

Điều quan trọng cho bài này: **mỗi lần một hàm được gọi, chương trình dựng cho nó một "khung" riêng** (tiếng Anh: **stack frame**, khung gọi hàm). Khung đó là một mảnh bàn học dành cho lần gọi này. Tham số `so` và biến cục bộ `ketQua` nằm trong khung. Khi hàm `return`, khung bị gỡ bỏ ngay, nên `so` và `ketQua` **mất theo**.

Khi `main` gọi `nhanDoi`, khung của `nhanDoi` được đặt chồng lên trên khung của `main`. Hàm gọi hàm khác thì lại chồng thêm một khung nữa. Một chồng khung như vậy gọi là **stack** (ngăn xếp: cái gì đặt vào sau thì lấy ra trước, như chồng đĩa). Hàm nào kết thúc trước thì khung của nó được gỡ trước.

```text
Khi đang chạy bên trong nhanDoi (địa chỉ minh họa):

   | khung của nhanDoi:  so = 10, ketQua = 20 |   <- vừa đặt lên, gỡ trước
   | khung của main:     a = 10 (sắp thấy ở Ví dụ 1) |
   +------------------------------------------+
                    chồng stack
```

**Phạm vi (scope)** là đoạn code mà trong đó một tên còn dùng được. Với biến cục bộ, phạm vi là từ chỗ khai báo đến dấu `}` đóng khối `{ }` chứa nó. Khối `{ }` có thể là thân hàm, hoặc chỉ là một cặp ngoặc nhọn đứng riêng bạn tự đặt.

**Vòng đời (lifetime)** là khoảng thời gian từ lúc biến ra đời đến lúc nó chết. Với biến cục bộ, vòng đời thường trùng với phạm vi: ra khỏi khối là biến bị hủy.

**Stack thường rất nhanh và gọn, nhưng nhỏ.** Dựng hay gỡ một khung thường chỉ cần nhích một "mốc" trên chồng khung (một con số ghi chỗ đỉnh chồng), nên thường rất nhanh. Đổi lại, stack có dung lượng giới hạn: mỗi chương trình thường chỉ được cấp khoảng một đến vài MB (con số cụ thể tùy hệ điều hành và cách cấu hình, trên nhiều máy Linux mặc định thường là 8 MB). Vì vậy đừng đặt một mảng cục bộ cỡ trăm MB lên stack.

Nếu stack đầy thì sao? Lỗi đó gọi là **tràn stack (stack overflow)**. Cách dễ gặp nhất là một hàm tự gọi lại chính nó mãi không dừng (**đệ quy** vô hạn):

```cpp
// bo-qua-kiem-tra
// CHỈ ĐỂ ĐỌC, mình không chạy chương trình này.
int dem(int n) {
    return dem(n + 1);   // gọi chính nó, mỗi lần chồng thêm một khung
}

int main() {
    return dem(0);
}
```

Mỗi lần gọi `dem` chồng thêm một khung lên stack, mà không có lần nào kết thúc để gỡ khung. Stack đầy, chương trình thường bị dừng đột ngột (trên Linux hay thấy lỗi `Segmentation fault`). Ghi chú: một số trình biên dịch có thể tối ưu hàm kiểu này thành vòng lặp, nên kết quả thực tế còn tùy. Tương tự, khai báo một mảng cục bộ khổng lồ như `int mang[100000000];` (khoảng 400 MB nếu `int` là 4 byte) cũng có thể làm tràn stack ngay khi vào hàm. Mảng lớn nên để ở heap, phần dưới nói tới.

### 2. Heap: kho đồ phải tự xin, tự trả

Biến cục bộ chết khi hàm kết thúc. Nhưng đôi khi bạn cần một thứ **sống lâu hơn hàm đã tạo ra nó**, hoặc một thứ quá lớn cho stack. Với những thứ đó, bạn xin chỗ ở **heap** (tiếng Anh *heap* nghĩa là "đống"; ta cứ gọi là heap). Từ khóa để xin là **`new`**:

```text
int* p = new int(5);
```

Đọc từng phần, từ phải sang trái:

- `new int(5)` nghĩa là "xin heap một chỗ vừa đủ cho một `int`, và ghi giá trị `5` vào đó". `new` **trả về địa chỉ** của chỗ vừa xin.
- `int*` là kiểu "địa chỉ của một `int`". Dấu `*` đứng sau tên kiểu nghĩa là "địa chỉ của một …" (Bài 01 đã nhắc qua, Bài 03 sẽ dạy kỹ). Một biến kiểu `int*` gọi là **con trỏ (pointer)**: nó đựng một địa chỉ.
- `p` là tên biến con trỏ. Bản thân `p` là biến cục bộ nằm trên stack, nhưng nó **chỉ tới** một chỗ ở heap. Giống tờ giấy ghi số phòng trong kho: tờ giấy nằm trên bàn học, còn đồ nằm trong kho.

Muốn đi theo địa chỉ để lấy giá trị, viết `*p` (dấu `*` đặt **trước** tên con trỏ, đọc là "thứ nằm ở địa chỉ `p`"). Viết `*p = 8;` là ghi `8` vào chỗ đó.

Chỗ xin bằng `new` **không tự mất**. Nó tồn tại đến khi bạn tự trả bằng **`delete p;`**. Hàm kết thúc mà bạn chưa `delete` thì tờ giấy `p` mất (vì nó là biến cục bộ), nhưng chỗ trong kho **vẫn bị giữ**, và giờ không còn ai biết số phòng để trả. Lỗi đó tên là **rò rỉ bộ nhớ (memory leak)**. Ta sẽ học kỹ `new`, `delete` và cách tránh rò rỉ ở Bài 07; hôm nay chỉ cần nhớ hình dạng.

Heap rộng hơn stack nhiều, nhưng **thường chậm hơn**: mỗi lần xin, đoạn code thủ kho phải đi tìm một chỗ trống đủ lớn, rồi ghi sổ.

### 3. Vùng tĩnh: bảng treo suốt lớp học

Có những biến không thuộc về một lần gọi hàm nào, mà thuộc về **cả chương trình**. Chúng nằm ở **vùng tĩnh (static storage)**. Ba loại:

- **Biến global** (toàn cục): khai báo **ngoài mọi hàm**, ở tầng ngoài cùng của file. Giống biến cấp package trong Go.
- **Biến `static` cục bộ**: khai báo **trong** một hàm nhưng có thêm từ khóa `static` đằng trước, ví dụ `static int dem = 0;`. Biến vẫn chỉ dùng được trong hàm đó, nhưng khác biến cục bộ thường ở chỗ **nó không chết khi hàm kết thúc**, và các lần gọi sau thấy lại đúng biến cũ.
- **Thành viên `static` của struct/class**: một thành viên khai báo với `static` bên trong struct (hoặc class, xem mục 4), cả kiểu đó dùng chung một bản. Ở bài này ta chỉ cần biết nó cũng nằm ở vùng tĩnh.

Vùng tĩnh có từ lúc chương trình bắt đầu (hoặc, với `static` cục bộ, từ lúc chạy qua dòng khai báo lần đầu) và **kéo dài đến khi chương trình kết thúc**.

### 4. Học nhanh `struct`, hàm tạo và hàm hủy (để làm thí nghiệm)

Để xem tận mắt vòng đời, ta cần một thứ biết "báo tin" khi ra đời và khi chết. Ta dùng một **`struct`**. Nếu bạn quen Go, `struct` của C++ là một kiểu gộp nhiều trường lại, giống `type Dau struct { ... }`. Điểm khác: `struct` của C++ có thể chứa luôn **hàm**.

*Đối tượng (object)* là một biến có kiểu là một struct, ví dụ biến `a` kiểu `Dau` ở dưới. Struct có hai hàm đặc biệt:

- **Hàm tạo (constructor):** tên **trùng tên struct**, không có kiểu trả về. Nó chạy **một lần, đúng lúc đối tượng ra đời**.
- **Hàm hủy (destructor):** tên là `~` rồi tên struct. Nó chạy **một lần, đúng lúc đối tượng chết**.

Ta cũng dùng `std::string`, kiểu chuỗi chữ của thư viện chuẩn, giống `string` của Go; muốn dùng phải thêm `#include <string>`.

```text
struct Dau {
    std::string ten;                  // một trường đựng tên
    Dau(std::string t) { ... }        // hàm tạo: nhận tên t
    ~Dau() { ... }                    // hàm hủy
};

Dau a("abc");   // tạo biến a kiểu Dau, đưa "abc" cho hàm tạo
```

Dấu `;` sau `}` đóng struct là bắt buộc: nó kết thúc câu lệnh khai báo kiểu `Dau` (quên là lỗi biên dịch). `Dau a("abc");` đọc là "tạo biến `a` kiểu `Dau`, và đưa `"abc"` cho hàm tạo", nên hàm tạo chạy ngay lúc đó. Khi `a` chết, hàm hủy chạy. Đối tượng xin ở heap cũng vậy: `new Dau("abc")` chạy hàm tạo, và `delete` chạy hàm hủy. Ta sẽ cho hai hàm này **in một dòng** để thấy khi nào chuyện xảy ra.

C++ còn có từ khóa `class`. Với bài này `class` và `struct` dùng như nhau, nên khi đọc chữ "class" cứ hiểu là struct (khác nhau nhỏ sẽ nói ở bài sau). Vì vậy câu hỏi "đối tượng của một class khai báo global nằm ở đâu?" cũng chính là câu hỏi về struct.
### 5. Bốn kiểu thời gian sống

C++ gọi "thứ này sống bao lâu và nằm ở khu nào" là **storage duration** (thời gian sống của vùng lưu trữ). Có bốn kiểu. (Trong bảng có chữ **luồng (thread)**: một dòng chạy code độc lập, một chương trình có thể có nhiều luồng chạy cùng lúc, gần giống goroutine của Go.)

| Kiểu | Nằm ở | Ra đời | Chết | Ví dụ |
|---|---|---|---|---|
| **automatic** (tự động) | stack | khi chạy qua dòng khai báo | khi ra khỏi khối `{ }` chứa nó | biến cục bộ, tham số |
| **static** (tĩnh) | vùng tĩnh | global: lúc khởi động, thực tế trước `main`; `static` cục bộ: lần chạy qua đầu tiên | khi chương trình kết thúc | global, `static` cục bộ |
| **dynamic** (động) | heap | khi chạy `new` | khi bạn chạy `delete` | `new int(5)` |
| **thread** (theo luồng) | vùng riêng của từng luồng | khi luồng bắt đầu | khi luồng kết thúc | biến khai báo bằng `thread_local` |

Kiểu thứ tư (`thread_local`, mỗi luồng có một bản riêng) mình chỉ nhắc tên, không dùng trong bài này.

## 💻 Ví dụ code

### Ví dụ 1: Hàm gọi hàm, khung xuất hiện rồi biến mất

```cpp
#include <iostream>

int nhanDoi(int so) {                                   // (1)
    int ketQua = so * 2;                                // (2)
    std::cout << "trong nhanDoi: ketQua = " << ketQua << "\n";
    return ketQua;                                      // (3)
}

int main() {
    int a = 10;                                         // (4)
    int b = nhanDoi(a);                                 // (5)
    std::cout << "trong main: b = " << b << "\n";
    {                                                   // (6)
        int tam = 99;
        std::cout << "trong khoi: tam = " << tam << "\n";
    }                                                   // (7)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (4) `int a = 10;` | `main` có khung riêng; `a` sinh ra trong khung đó | `[main: a=10]` |
| (5) gọi `nhanDoi(a)` | Dựng khung mới cho `nhanDoi`. Tham số `so` nhận một **bản sao** của `a` | `[nhanDoi: so=10]` đè lên `[main: a=10]` |
| (2) `int ketQua = so * 2;` | `ketQua` sinh ra trong khung của `nhanDoi` | `[nhanDoi: so=10, ketQua=20]` |
| (3) `return ketQua;` | Trả `20` về cho nơi gọi, **khung của `nhanDoi` bị gỡ**: `so` và `ketQua` mất | còn `[main: a=10]` |
| (5) tiếp | `b` sinh ra trong khung `main` và nhận `20` | `[main: a=10, b=20]` |
| (6) `{` | Mở khối riêng. `tam` sinh ra | `[main: a=10, b=20, tam=99]` |
| (7) `}` | Hết khối. `tam` chết | `[main: a=10, b=20]` |

(Bảng vẽ gọn, không phải địa chỉ thật; chương trình thật có thể cất thêm những thứ phụ khác trong khung.)

**Kết quả khi chạy** (`g++ -std=c++17 -Wall`, `g++ 11.4`):

```text
trong nhanDoi: ketQua = 20
trong main: b = 20
trong khoi: tam = 99
```

**Thử thay đổi: dùng `tam` sau dấu `}` ở dòng (7).** Mình thêm dòng `std::cout << tam << "\n";` ngay sau `}` đó. Chương trình **không biên dịch được**, `g++` báo:

```text
v1.cpp:17:18: error: ‘tam’ was not declared in this scope; did you mean ‘tm’?
```

`was not declared in this scope` nghĩa là "chưa được khai báo trong phạm vi này". Ra khỏi khối thì tên `tam` không còn dùng được: đó chính là biến cục bộ hết phạm vi.

### Ví dụ 2: Xin và trả một chỗ ở heap

```cpp
#include <iostream>

int main() {
    int* p = new int(5);                  // (1)
    std::cout << "gia tri: " << *p << "\n";   // (2)
    *p = 8;                               // (3)
    std::cout << "gia tri moi: " << *p << "\n";
    delete p;                             // (4)
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) `int* p = new int(5);` | Xin heap 4 byte, ghi `5`. Địa chỉ của chỗ đó đặt vào biến `p` | stack: `p = 0x9000`; heap: `0x9000 = 5` (địa chỉ minh họa) |
| (2) `*p` | Đi theo địa chỉ trong `p`, đọc ra `5` | không đổi |
| (3) `*p = 8;` | Đi theo địa chỉ trong `p`, ghi `8` vào chỗ đó | heap: `0x9000 = 8` |
| (4) `delete p;` | Trả chỗ `0x9000` về kho | heap: chỗ đó không còn của ta |

```text
STACK (bàn học)             HEAP (kho)
+-------------+            +----------+
| p = 0x9000  | ---------> | 8        |  (địa chỉ 0x9000, minh họa)
+-------------+            +----------+
```

**Kết quả khi chạy**

```text
gia tri: 5
gia tri moi: 8
```

**Thử thay đổi: bỏ dòng (4) `delete p;`.** Mình đã thử. Chương trình biên dịch sạch và in **y hệt** hai dòng trên, nên bạn không thấy gì sai. Nhưng chỗ ở heap chưa được trả: đó là rò rỉ. Để bắt được, mình biên dịch lại với công cụ kiểm tra bộ nhớ (`g++ -std=c++17 -fsanitize=address -g`), và khi chạy nó báo:

```text
ERROR: LeakSanitizer: detected memory leaks

Direct leak of 4 byte(s) in 1 object(s) allocated from:
```

(Công cụ này Bài 13 dạy kỹ.) Bài học: quên `delete` là lỗi **im lặng**, chương trình vẫn chạy bình thường.

### Ví dụ 3: Ba kiểu thời gian sống cùng một lúc, xem thứ tự in

Đây là chương trình quan trọng nhất của bài. Mỗi đối tượng `Dau` in một dòng khi ra đời và một dòng khi chết. Ta đặt bốn đối tượng ở bốn chỗ khác nhau.

```cpp
#include <iostream>
#include <string>

struct Dau {
    std::string ten;
    Dau(std::string t) {
        ten = t;
        std::cout << "  [ra doi] " << ten << "\n";
    }
    ~Dau() {
        std::cout << "  [chet]   " << ten << "\n";
    }
};

Dau toanCuc("toan cuc");                       // (1)

void goiHam() {
    std::cout << "vao goiHam\n";
    static Dau tinh("static trong ham");       // (2)
    std::cout << "ra khoi goiHam\n";
}

int main() {
    std::cout << "bat dau main\n";
    Dau cucBo("cuc bo");                       // (3)
    Dau* p = new Dau("new");                   // (4)
    goiHam();                                  // (5)
    goiHam();                                  // (6)
    {
        Dau trongKhoi("trong khoi");           // (7)
    }                                          // (8)
    delete p;                                  // (9)
    std::cout << "ket thuc main\n";
    return 0;
}
```

**Chạy từng dòng** (theo đúng thứ tự thật chương trình chạy, kể cả phần xảy ra **trước** `main`):

| Lúc nào | Chuyện gì xảy ra | Nằm ở đâu |
|---|---|---|
| Trước khi `main` bắt đầu (thực tế, xem caveat ở mục Hỏi nhanh) | (1) `toanCuc` ra đời, hàm tạo in `[ra doi] toan cuc` | vùng tĩnh |
| `main` bắt đầu | In `bat dau main` | |
| (3) | `cucBo` ra đời | stack |
| (4) | `new Dau("new")` xin heap, hàm tạo in `[ra doi] new`; `p` (trên stack) giữ địa chỉ | đối tượng ở heap, `p` ở stack |
| (5) lần gọi đầu | In `vao goiHam`. Chạy tới dòng (2): lần đầu nên `tinh` ra đời, in `[ra doi] static trong ham`. In `ra khoi goiHam` | vùng tĩnh |
| (6) lần gọi thứ hai | In `vao goiHam`. Dòng (2) **bị bỏ qua**, vì `tinh` đã có rồi. In `ra khoi goiHam` | |
| (7) và (8) | `trongKhoi` ra đời ở (7); đến `}` ở (8) nó chết, hàm hủy in `[chet] trong khoi` | stack |
| (9) `delete p;` | Hàm hủy in `[chet] new`, rồi chỗ ở heap được trả | heap |
| Cuối `main` | In `ket thuc main`. Tới `}` của `main`, biến cục bộ `cucBo` chết | stack |
| Sau khi `main` kết thúc | Các đối tượng vùng tĩnh chết: `tinh` rồi `toanCuc` | vùng tĩnh |

**Kết quả khi chạy** (một lần chạy thật; thứ tự này là hành vi của các trình biên dịch phổ biến và không phụ thuộc vào địa chỉ):

```text
  [ra doi] toan cuc
bat dau main
  [ra doi] cuc bo
  [ra doi] new
vao goiHam
  [ra doi] static trong ham
ra khoi goiHam
vao goiHam
ra khoi goiHam
  [ra doi] trong khoi
  [chet]   trong khoi
  [chet]   new
ket thuc main
  [chet]   cuc bo
  [chet]   static trong ham
  [chet]   toan cuc
```

Bốn điều đọc ra từ kết quả:

- **Global ra đời trước `main`** (trên các trình biên dịch phổ biến): dòng `[ra doi] toan cuc` hiện lên trước `bat dau main`. Và nó **chết SAU `main`**: nó ở cuối cùng.
- **`static` cục bộ ra đời ở lần gọi hàm đầu tiên**, không phải lúc chương trình bắt đầu. Lần gọi thứ hai không tạo lại nó. Nó chết sau `main`, cùng nhóm với global.
- **Biến cục bộ chết ở cuối khối chứa nó**: `trongKhoi` chết ngay ở `}` của khối nhỏ; `cucBo` chết ở `}` của `main` (nên dòng `[chet] cuc bo` hiện sau `ket thuc main`).
- **Đối tượng ở heap chết đúng lúc bạn `delete`**, không sớm hơn, không muộn hơn.

Ba dòng cuối cho thấy thêm một quy tắc: các đối tượng chết theo thứ tự **ngược** với thứ tự chúng ra đời (`cucBo` ra đời sau `toanCuc` nên chết trước nó; `tinh` ra đời sau `toanCuc` nên chết trước `toanCuc`).

**Thử thay đổi 1: bỏ dòng (9) `delete p;`.** Mình đã chạy. Dòng `[chet]   new` **biến mất** khỏi kết quả: hàm hủy của đối tượng ở heap không bao giờ chạy, và chỗ ở heap bị bỏ lại (rò rỉ). Tất cả dòng khác giữ nguyên.

**Thử thay đổi 2: xóa hai dòng gọi `goiHam();` ở (5) và (6).** Mình đã chạy. Dòng `[ra doi] static trong ham` và dòng `[chet]   static trong ham` **đều không xuất hiện**. Không ai chạy qua dòng (2) nên `tinh` chưa bao giờ ra đời, và cũng không có gì để hủy. Điều này chứng minh `static` cục bộ ra đời lúc chạy qua dòng khai báo chứ không phải lúc chương trình bắt đầu.

!!! info "Bạn biết Go?"
    Trong Go không có "hàm hủy" chạy đúng lúc một biến hết phạm vi, vì bộ thu gom rác (garbage collector) dọn bộ nhớ vào lúc nó chọn. Cái gần nhất với "việc dọn dẹp chạy đúng lúc rời hàm" là `defer`. C++ chạy hàm hủy đúng lúc ra khỏi khối, một cách xác định, và đó là nền của kỹ thuật **RAII** (gắn việc trả tài nguyên vào hàm hủy, để nó tự chạy đúng lúc) mà ta học ở Bài 08.

    Về stack và heap: Go thường **không bắt bạn chọn**. Trình biên dịch Go có **phân tích thoát (escape analysis)**: nó xem biến có "thoát" khỏi hàm không, và nếu có thì tự đặt biến lên heap. Vì vậy `func taoSo() *int { x := 5; return &x }` hoàn toàn hợp lệ trong Go, và `go build -gcflags=-m` in dòng `moved to heap: x`.

    Biến cấp package của Go thường nằm ở vùng tĩnh như global của C++, nhưng Go quy định rõ thứ tự khởi tạo chúng (theo sự phụ thuộc giữa các biến). C++ thì **không làm hộ** bạn việc chọn stack hay heap. Vì vậy C++ có RAII và **smart pointer** (con trỏ thông minh, một vật bọc tự trả chỗ ở heap; Bài 09).

### Ví dụ 4: In địa chỉ của bốn loại

```cpp
#include <iostream>

int toanCuc = 1;                                            // (1)

void ham() {
    static int tinh = 2;                                    // (2)
    int cucBo = 3;                                          // (3)
    int* heap = new int(4);                                 // (4)
    std::cout << "global:  " << &toanCuc << "\n";
    std::cout << "static:  " << &tinh << "\n";
    std::cout << "cuc bo:  " << &cucBo << "\n";
    std::cout << "heap:    " << heap << "\n";               // (5)
    std::cout << "bien con tro heap (cuc bo): " << &heap << "\n";
    delete heap;
}

int main() {
    ham();
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `toanCuc` có từ trước `main`, ở vùng tĩnh. (Giá trị `1` là hằng số viết sẵn, nên nó nằm sẵn đó từ lúc chương trình nạp, không có "khoảnh khắc ra đời" như `Dau`) | vùng tĩnh |
| (2) | `tinh` cũng ở vùng tĩnh và chỉ có một bản dù `ham` gọi bao nhiêu lần. (Vì `2` cũng là hằng số viết sẵn, ở đây không thấy được lúc nó "ra đời"; chuyện "lần đầu" chỉ thấy rõ với `Dau` ở Ví dụ 3) | vùng tĩnh |
| (3) | `cucBo` ra đời trên stack | stack |
| (4) | Xin heap một `int` chứa `4`; biến con trỏ `heap` (trên stack) giữ địa chỉ | `heap` ở stack, số `4` ở heap |
| in 3 dòng đầu | `&toanCuc`, `&tinh`, `&cucBo` là địa chỉ của chính các biến đó | |
| (5) in `heap` | `heap` (không có `&`) là địa chỉ **chỗ ở heap** mà biến con trỏ trỏ tới | địa chỉ của chỗ ở heap |
| in `&heap` | `&heap` là địa chỉ của **chính biến con trỏ**, nằm trên stack | địa chỉ ở stack |

**Kết quả khi chạy** (một lần chạy thật trên máy mình):

```text
global:  0x570794ebb010
static:  0x570794ebb014
cuc bo:  0x7ffeeb931b1c
heap:    0x5707aa85ceb0
bien con tro heap (cuc bo): 0x7ffeeb931b20
```

Số trên máy bạn sẽ khác (và chạy lại cũng đổi, như Bài 01 đã nói). Chỉ có kiểu mẫu đáng nhìn: **thường** thì các địa chỉ ở stack trông khác hẳn (ở đây bắt đầu bằng `0x7ffe…`) so với địa chỉ ở vùng tĩnh và ở heap, và `cucBo` nằm sát `heap` (biến con trỏ), vì cả hai là biến cục bộ cùng một khung. `global` và `static` cũng nằm sát nhau. Trong lần chạy này `heap` có vẻ gần cả hai, nhưng đó chỉ là tình cờ của lần chạy: kiểu mẫu này không được đảm bảo. Mình **không** khẳng định vùng nào có địa chỉ lớn hơn vùng nào: điều đó tùy hệ điều hành và trình biên dịch.

### Ví dụ 5: Câu hỏi của bạn, bằng thực nghiệm

Câu hỏi: đối tượng của class (hay struct) khai báo global thì nằm ở đâu? Ta thử với một struct có chứa `std::vector` (kiểu mảng co giãn, giống slice của Go; muốn dùng thêm `#include <vector>`).

```cpp
#include <iostream>
#include <vector>

struct Kho {
    std::vector<int> so;
    Kho() {
        so.push_back(1);
        so.push_back(2);
        so.push_back(3);
        std::cout << "ham tao Kho chay\n";
    }
};

Kho khoToanCuc;                                          // (1)

int main() {
    std::cout << "bat dau main\n";
    std::cout << "object khoToanCuc: " << &khoToanCuc << "\n";
    std::cout << "du lieu trong vector: " << khoToanCuc.so.data() << "\n";  // (2)
    std::cout << "so phan tu: " << khoToanCuc.so.size() << "\n";
    return 0;
}
```

(`push_back(x)` thêm một phần tử vào cuối vector. `.so.data()` cho địa chỉ vùng chứa các phần tử. Dấu `.` truy cập một thành viên của đối tượng, như Go.)

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) trước `main` | `khoToanCuc` ra đời, hàm tạo chạy: vector xin heap rồi nhận 1, 2, 3, in `ham tao Kho chay` | object ở vùng tĩnh; mảng `1,2,3` ở heap |
| `main` bắt đầu | In `bat dau main` | |
| in | In địa chỉ của object, rồi (2) địa chỉ của dữ liệu bên trong vector | |

```text
VÙNG TĨNH                         HEAP
+-------------------------+      +---+---+---+
| khoToanCuc              |      | 1 | 2 | 3 |   <- dữ liệu của vector
|   so: [con trỏ tới heap] ---->  +---+---+---+
+-------------------------+
```

**Kết quả khi chạy**

```text
ham tao Kho chay
bat dau main
object khoToanCuc: 0x62f0e0abc160
du lieu trong vector: 0x62f0e70a3eb0
so phan tu: 3
```

Dòng `ham tao Kho chay` hiện **trước** `bat dau main`. Hai địa chỉ khác nhau rõ rệt: một cái ở vùng tĩnh, một cái ở heap. Số cụ thể trên máy bạn sẽ khác.

!!! question "Hỏi nhanh: đối tượng của class khai báo global nằm ở heap hay stack?"
    **Cả hai đều không: nó nằm ở vùng tĩnh (static storage).** Cụ thể:

    - **Hàm tạo** chạy khi chương trình khởi động, **trước `main`** (đó là cách các trình biên dịch làm trong thực tế). Chuẩn C++ thực ra cho phép hoãn việc khởi tạo này tới sau đầu `main` trong vài trường hợp; các trình biên dịch phổ biến luôn làm trước `main`, và bài này (cũng như buổi phỏng vấn) dựa vào hành vi đó. **Hàm hủy** chạy khi chương trình kết thúc, **sau `main`**. Ví dụ 3 đã cho thấy đúng thứ tự này.
    - Nếu struct/class có chứa `std::vector` (hay `std::map`…), thì **bản thân object** nằm ở vùng tĩnh, còn **dữ liệu bên trong** vector (các phần tử) nằm ở **heap**, do vector tự xin. Ví dụ 5 đã in hai địa chỉ khác nhau để chứng minh.
    - Chính vector cũng làm đúng như vậy khi bạn khai báo nó là biến cục bộ: lúc đó object `std::vector` nằm trên stack, còn các phần tử vẫn ở heap. (Riêng `std::string`: chuỗi dài thường nằm ở heap, còn chuỗi ngắn có thể nằm ngay trong object.)

### Ví dụ 6: Static initialization order fiasco, và cách tránh

Bạn có thể có nhiều file `.cpp` trong một dự án, mỗi file có global riêng. **Thứ tự khởi tạo global giữa các file `.cpp` khác nhau là không xác định**: chuẩn C++ không nói file nào chạy trước. (Trong **một** file, thứ tự theo đúng thứ tự viết.) Hậu quả: nếu hàm tạo của global `A` ở file này dùng global `B` ở file kia, thì lúc `A` chạy `B` có thể **chưa ra đời**, và `A` đọc phải một thứ chưa sẵn sàng. Lỗi này tên là **static initialization order fiasco** (nghĩa là "thảm họa về thứ tự khởi tạo của biến tĩnh"), và nó khó chịu vì có thể chạy đúng ở máy này, sai ở máy khác, hoặc đổi theo thứ tự nối file lúc build. Vấn đề này chỉ xảy ra với global có hàm tạo hoặc giá trị tính lúc chạy; global chỉ có hằng số viết sẵn (như `int x = 1;`) thì không bị.

Cách tránh thường gặp: **không dựng global sẵn, mà dựng nó trong một hàm, bằng `static` cục bộ**. Nhờ vậy nó được khởi tạo **ở lần gọi hàm đầu tiên** (như Ví dụ 3 đã thấy), tức là ngay lúc có người cần. Từ C++11, chuẩn đảm bảo việc khởi tạo `static` cục bộ này an toàn dù có nhiều luồng cùng gọi lần đầu. Mình chỉ cho code trong một file, vì cách làm là như nhau:

```cpp
#include <iostream>
#include <string>

struct Logger {
    std::string ten;
    Logger(std::string t) {
        ten = t;
        std::cout << "tao Logger " << ten << "\n";
    }
};

Logger* layLogger() {                       // (1)
    static Logger duyNhat("chung");         // (2)
    return &duyNhat;                        // (3)
}

int main() {
    std::cout << "bat dau main\n";
    Logger* a = layLogger();                // (4)
    Logger* b = layLogger();                // (5)
    std::cout << "a = " << a << "\n";
    std::cout << "b = " << b << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| `main` bắt đầu | In `bat dau main`. Chưa có `Logger` nào, vì nó không phải global | chưa có |
| (4) gọi `layLogger()` lần 1 | Chạy qua (2) lần đầu: `duyNhat` ra đời, hàm tạo in `tao Logger chung`. (3) trả địa chỉ của nó | `duyNhat` ở vùng tĩnh |
| (5) gọi lần 2 | Dòng (2) bị bỏ qua, nó đã có rồi. (3) trả **cùng địa chỉ** | không đổi |

**Kết quả khi chạy**

```text
bat dau main
tao Logger chung
a = 0x5583a17df180
b = 0x5583a17df180
```

`a` và `b` có địa chỉ giống nhau (số cụ thể máy bạn sẽ khác, nhưng hai số sẽ trùng nhau). Dòng `tao Logger chung` hiện **sau** `bat dau main`: nó ra đời đúng lúc có người cần. Hàm này trả địa chỉ của một biến nằm bên trong nó mà vẫn **an toàn**, vì `duyNhat` là `static`, sống đến hết chương trình, không như một biến cục bộ thường.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Stack, heap và vùng tĩnh khác nhau thế nào?"
    Stack chứa biến cục bộ và tham số, mỗi lần gọi hàm có một khung, tự dọn khi ra khỏi hàm hoặc khối. Nó nhanh nhưng nhỏ (thường vài MB). Heap là vùng xin bằng `new` (hoặc `malloc`), lớn hơn nhưng thường chậm hơn, và sống đến khi tự `delete`; quên trả là rò rỉ. Vùng tĩnh chứa biến global, `static` cục bộ và thành viên `static`, sống suốt chương trình.

??? question "Một biến global của class nằm ở đâu, hàm tạo và hàm hủy chạy khi nào?"
    Nó nằm ở vùng tĩnh, không phải stack và không phải heap. Hàm tạo chạy khi chương trình khởi động, thực tế là trước `main` (chuẩn cho phép hoãn trong vài trường hợp, nhưng các trình biên dịch phổ biến luôn làm trước); hàm hủy chạy sau khi `main` kết thúc. Nếu class chứa `std::vector`, object ở vùng tĩnh còn các phần tử của vector ở heap.

??? question "Static initialization order fiasco là gì và tránh thế nào?"
    Thứ tự khởi tạo các biến global nằm ở các file `.cpp` khác nhau là không xác định, nên global ở file này có thể dùng một global của file khác khi nó chưa được khởi tạo. Cách tránh phổ biến: thay global bằng một hàm chứa biến `static` cục bộ và trả nó ra, vì `static` cục bộ được khởi tạo ở lần gọi đầu, và từ C++11 việc đó an toàn với nhiều luồng.

??? question "Vì sao không nên đặt một mảng 100 MB làm biến cục bộ?"
    Biến cục bộ nằm trên stack, mà stack nhỏ (thường vài MB, tùy hệ điều hành và cấu hình). Mảng quá lớn làm tràn stack (stack overflow) và chương trình bị dừng đột ngột. Dữ liệu lớn nên xin ở heap, thường qua `std::vector` hoặc smart pointer.

??? question "Storage duration là gì?"
    Là khoảng thời gian vùng lưu trữ của một đối tượng tồn tại. C++ có bốn kiểu: automatic (stack, đến hết khối chứa nó), static (suốt chương trình), dynamic (heap, từ `new` đến `delete`) và thread (suốt đời một luồng, qua `thread_local`).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Trả về địa chỉ của biến cục bộ"
    Trong Go, `return &x` với `x` cục bộ là hợp lệ. Trong C++, `x` nằm trên stack và chết khi hàm kết thúc, nên địa chỉ trả ra **trỏ vào chỗ đã dọn**. Mình thử một hàm `int* hamXau() { int x = 5; return &x; }` và `g++ -Wall` cảnh báo: `warning: address of local variable ‘x’ returned`. Đọc cái địa chỉ đó sau này là hành vi không xác định (Bài 13). Muốn giá trị sống lâu hơn hàm, hãy đặt nó ở heap, hoặc dùng `static` nếu đúng ý.

!!! warning "Lỗi 2: Tưởng global thì không có hàm tạo/hàm hủy chạy"
    Global của kiểu có hàm tạo thì hàm tạo **vẫn chạy**, thường ngay trước `main` mà bạn không thấy dòng nào gọi nó. Hàm hủy cũng vậy, sau `main`. Vì thế một global có hàm tạo in chữ thường sẽ in trước chữ đầu tiên của `main`.

!!! warning "Lỗi 3: Nghĩ biến nào có `new` thì cả biến nằm ở heap"
    `int* p = new int(5);` tạo **hai** thứ: biến con trỏ `p` (cục bộ, trên stack) và chỗ `int` ở heap mà `p` chỉ tới. Tương tự, `std::vector` cục bộ là một object nhỏ trên stack còn các phần tử ở heap. Khi hỏi "cái này nằm đâu", hãy tách rõ **bản thân biến** và **thứ nó trỏ tới**.

!!! warning "Lỗi 4: Mảng khổng lồ làm biến cục bộ, hoặc đệ quy không điểm dừng"
    Cả hai đều ngốn stack mà stack chỉ vài MB, và có thể gây tràn stack. Dữ liệu lớn nên để ở heap; đệ quy phải có điều kiện dừng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="02" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Trong thân một hàm có `int dem = 0;`. Biến `dem` nằm ở đâu và sống đến khi nào?

- Ở vùng tĩnh, và sống đến khi chương trình kết thúc
- Ở heap, và sống đến khi ta gọi `delete` cho nó
- Ở stack, và chết khi chạy tới `}` của khối chứa nó
- Ở stack, và chết khi toàn bộ chương trình kết thúc

<p class="giai-thich" markdown>Biến cục bộ thường thuộc stack, trong khung của lần gọi hàm, và chết khi chạy tới `}` đóng khối chứa nó. Vùng tĩnh là chỗ của global và `static`, chứ không phải của biến khai báo trần trong hàm. Heap chỉ dùng khi bạn gọi `new`, và `delete` chỉ trả những thứ đã xin bằng `new`. Nói biến cục bộ sống đến hết chương trình là nhầm nó với biến `static`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Một biến `int tong = 0;` được khai báo ngoài mọi hàm, ở tầng ngoài cùng của file. Nó nằm ở đâu?

- Ở vùng tĩnh, có sẵn từ lúc chương trình bắt đầu
- Ở stack, vì nó chỉ là một số `int` nhỏ, vừa bàn học
- Ở heap, vì nó không thuộc về hàm nào, nên phải xin
- Ở stack của `main`, và chết khi `main` kết thúc

<p class="giai-thich" markdown>Biến global thuộc vùng tĩnh, có sẵn từ lúc chương trình bắt đầu và sống tới khi chương trình kết thúc. Kích thước nhỏ không quyết định khu nào: khu được chọn theo cách khai báo, không theo cỡ. Heap chỉ có khi bạn gọi `new`, và "không thuộc hàm nào" không có nghĩa là đã gọi `new`. Nó cũng không nằm trong khung của `main`, vì khung `main` chỉ chứa biến cục bộ của `main`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Với `int* p = new int(5);` trong một hàm, câu nào đúng?

- Cả `p` lẫn số `5` đều nằm ở heap, vì có `new`
- Cả `p` lẫn số `5` đều nằm trên stack, vì là biến cục bộ
- `p` nằm ở heap, còn số `5` nằm trên stack
- `p` nằm trên stack, còn số `5` mà nó trỏ tới nằm ở heap

<p class="giai-thich" markdown>`new int(5)` xin một chỗ ở heap để đựng `5`, còn `p` là biến con trỏ cục bộ, nằm trên stack và đựng địa chỉ của chỗ đó. Cả hai cùng ở heap, hoặc cùng ở stack, đều sai vì chúng là hai thứ khác nhau. Đảo ngược cũng sai: `new` không bao giờ đặt đối tượng lên stack. Và khi hàm kết thúc `p` chết, còn số `5` ở heap vẫn nằm đó cho đến khi `delete`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn code sau. Hàm tạo của `Dau` in `+ten`, hàm hủy in `-ten`. Chương trình in ra theo thứ tự nào (trên trình biên dịch phổ biến)?

```text
Dau g("G");
int main() {
    Dau a("A");
    { Dau b("B"); }
    std::cout << "X\n";
    return 0;
}
```

- `+A +B -B X -A +G -G`
- `+G +A +B -B X -A -G`
- `+G +A +B X -B -A -G`
- `+A +B -B X -A`

<p class="giai-thich" markdown>`g` là global nên ra đời trước `main` (`+G` đầu tiên) và chết sau `main` (`-G` cuối cùng). Trong `main`, `a` ra đời, rồi `b` ra đời và chết ngay ở `}` của khối nhỏ (`+B -B`), rồi in `X`, và `a` chết ở `}` của `main`. Dãy có `+G` giữa chừng nhầm rằng global ra đời khi vào `main`. Dãy có `-B` sau `X` quên rằng biến cục bộ chết ở cuối khối chứa nó. Dãy không có `G` quên rằng global có hàm tạo và hàm hủy thì vẫn chạy chúng, chỉ là ngoài `main`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Trên các trình biên dịch phổ biến, điều nào đúng về hàm tạo của một đối tượng khai báo global?

- Nó chạy ở dòng đầu tiên bên trong `main`
- Nó chạy ở lần đầu tiên có code dùng tới đối tượng
- Nó chạy trước khi `main` bắt đầu, không ai gọi
- Nó không chạy, vì global không phải đối tượng thật

<p class="giai-thich" markdown>Đối tượng global ra đời lúc chương trình khởi động, nên hàm tạo của nó chạy trước `main` mà không ai phải gọi, đó là lý do dòng in từ hàm tạo hiện lên trước dòng đầu của `main`. "Dòng đầu tiên của `main`" thì quá muộn, `main` chưa bắt đầu. "Lần đầu có người dùng" là cách chạy của `static` cục bộ, không phải của global. Global là đối tượng thật như mọi đối tượng, nên hàm tạo vẫn chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Đọc đoạn code sau. `Dau` ở đây có hàm tạo in `tao ten`. Chương trình in ra gì (các dòng nối bằng dấu cách)?

```text
void f() { static Dau d("S"); std::cout << "f\n"; }
int main() { std::cout << "A\n"; f(); f(); }
```

- `tao S A f f`, vì `static` được tạo từ đầu chương trình
- `A tao S f tao S f`, vì mỗi lần gọi `f` lại tạo `d`
- `A f f tao S`, vì `static` chỉ được tạo khi chương trình kết thúc
- `A tao S f f`, vì `d` chỉ ra đời ở lần gọi `f` đầu tiên

<p class="giai-thich" markdown>`static` cục bộ ra đời lúc chạy qua dòng khai báo **lần đầu**, tức trong lần gọi `f()` thứ nhất, sau chữ `A`, và lần gọi thứ hai bỏ qua nó vì nó đã có. Vì vậy `tao S` chỉ xuất hiện một lần, giữa `A` và `f` đầu tiên. Nghĩ nó có từ đầu chương trình là nhầm với global. Nghĩ nó tạo lại mỗi lần gọi là nhầm với biến cục bộ thường. Và nó cũng không đợi đến cuối chương trình, vì lúc đó nó chỉ bị hủy.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Vì sao trong Go ta ít khi nghĩ tới chuyện "biến nằm ở stack hay heap" như trong C++?

- Vì Go không dùng stack, nên mọi biến của chương trình đều ở heap
- Vì trình biên dịch Go tự chọn chỗ đặt biến nhờ escape analysis
- Vì Go cấm hàm trả về địa chỉ của biến cục bộ của chính nó
- Vì Go gộp stack và heap thành một vùng nhớ duy nhất cho mọi biến

<p class="giai-thich" markdown>Trình biên dịch Go phân tích xem biến có "thoát" khỏi hàm không (ví dụ khi hàm trả `&x`), và nếu có thì tự đặt biến lên heap, nên lập trình viên không phải chọn. Go vẫn có stack, mỗi goroutine có stack riêng, nên "mọi biến ở heap" và "một vùng duy nhất" đều sai. Và trả `&x` trong Go là hợp lệ, không bị cấm, chính nhờ escape analysis. C++ không làm hộ việc này, nên bạn phải tự nghĩ.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Stack (bàn học) chứa biến cục bộ, mỗi lần gọi hàm có một khung, nhỏ và nhanh, tự dọn khi ra khỏi khối; mảng khổng lồ hoặc đệ quy vô hạn làm tràn stack.
2. Heap (kho) xin bằng `new`, sống đến khi tự `delete`; quên trả là rò rỉ, và `int* p = new int(5);` gồm biến con trỏ `p` ở stack cộng chỗ `int` ở heap.
3. Vùng tĩnh (bảng tường) chứa biến global, `static` cục bộ và thành viên `static`, sống suốt chương trình; hàm tạo của global thực tế chạy trước `main`, hàm hủy sau `main`, `static` cục bộ ra đời ở lần chạy qua đầu tiên.
4. Đối tượng class khai báo global nằm ở vùng tĩnh (không phải heap hay stack), và dữ liệu bên trong `std::vector` của nó nằm ở heap.
5. Bốn storage duration: automatic, static, dynamic, thread; thứ tự khởi tạo global giữa các file `.cpp` là không xác định (static initialization order fiasco), tránh bằng `static` cục bộ trong hàm.
