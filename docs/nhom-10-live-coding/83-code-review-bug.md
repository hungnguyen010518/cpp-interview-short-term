# Bài 83 — Code review: tìm lỗi trong 15 đoạn C++

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Đọc một đoạn C++ lạ theo bốn câu hỏi (ai sở hữu và ai trả, ai sống lâu hơn ai, kiểu số có đủ không, lời hứa của chữ ký có được giữ không) rồi nói lỗi theo ba phần người phỏng vấn muốn nghe: lỗi gì, vì sao nguy hiểm, sửa thế nào.
    - Nhận ra 15 lỗi kinh điển: rò rỉ, `double free`, `delete` sai cặp, thiếu hàm hủy `virtual`, con trỏ và tham chiếu treo, `string_view` treo, iterator bị vô hiệu, slicing, sao chép thay vì chuyển, so sánh có dấu với không dấu, tràn số, `const` bị phá, `noexcept` mà ném, tên tham số che tên thành viên.
    - Biết với từng lỗi thì công cụ nào lên tiếng (cảnh báo `-Wall`, ASan, UBSan) và lỗi nào **mọi công cụ đều im** (mục 9, 10).
    - Tra bảng "triệu chứng, công cụ, nguyên nhân" để đoán nhanh lỗi từ cách chương trình hỏng.

**Bạn cần biết trước:** [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new[]`/`delete[]`, rò rỉ), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (trả tham chiếu cục bộ), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (quy tắc 3), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`string_view`), [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (UB, ASan, UBSan: **đọc trước**), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator), [Bài 32](../nhom-4-oop-patterns/32-ke-thua.md) và [Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md) (kế thừa, `virtual`, slicing). Bài này cho bạn **15 đoạn code lạ** để luyện đọc, không dạy lại các lỗi từ đầu.

## 🧠 Câu chuyện mở đầu

Vòng live-coding. Người phỏng vấn đẩy qua một tờ giấy: "Đây là code đồng nghiệp gửi để review, mỗi đoạn có một lỗi. Anh/chị cho biết lỗi gì, vì sao nguy hiểm, sửa ra sao. Không có máy để chạy thử."

Ở [Bài 77](77-tu-cai-unique-ptr.md) đến 82 của **xưởng tự lắp đồ**, bạn tự tháo máy ra lắp lại. Bài này là phần kiểm máy **người khác** đưa tới: bạn xem từng bánh răng (từng dòng) và hỏi bánh nào kẹt, bánh nào lắp ngược, bánh nào quay được mà sai việc. Mình đã chạy từng đoạn để bạn thấy bánh răng hỏng **kêu thế nào**.

!!! info "Chỗ nào ví von xưởng không còn đúng?"
    Cỗ máy hỏng thì thường dừng hoặc kêu. Chương trình C++ có UB thì có thể chạy tiếp và in kết quả trông đúng. Vì thế một nửa bài này là học cách **không tin** vào "chạy ra đúng".

## 📖 Giải thích

### 1. Luật chơi

Mỗi mục là một chương trình **đầy đủ**: chép vào máy là chạy. Bạn đọc code, tự trả lời câu "Tìm lỗi", rồi mới mở `??? tip "Xem đáp án"`. Mỗi đáp án có ba phần: lỗi và vì sao nguy hiểm, **cái mình đã chạy thật** (trích đúng thứ công cụ báo), và bản sửa. Khối nào cũng có dòng đầu `// bo-qua-kiem-tra` vì cố ý sai; chép đi chạy thì bỏ dòng đó.

| Việc | Lệnh mình đã dùng (tệp rút gọn thành `NN.cpp`) |
|---|---|
| Chạy thường | `g++ -std=c++17 -Wall -Wextra -o ct NN.cpp && ./ct` (thử thêm `-O2`; mục 15 thử thêm `-Wshadow`) |
| ASan + UBSan | `g++ -std=c++17 -g -fsanitize=address,undefined -fno-omit-frame-pointer -o ct NN.cpp && ./ct` |
| Đọc mã thoát | `134` là `abort` (chương trình tự dừng), `139` là `Segmentation fault`; ASan thoát mã `1` |

Số dòng trong báo cáo (như `05.cpp:8`, tệp của mục 5) tính khi **bỏ** dòng `// bo-qua-kiem-tra`; đường dẫn và khung thư viện đã lược. Kết quả của UB chỉ là cái **đã chạy trên g++ 11.4 ở máy mình**, không phải lời hứa. Chương trình bị `abort` hay `SEGV` có thể **mất phần chưa xả** của `std::cout` khi in qua đường ống; vài mục dùng `std::endl` để thấy dòng đầu. Mình đã biên dịch cả 15 bản sửa với `-Wall -Wextra -Wshadow` (không cảnh báo) và chạy dưới ASan + UBSan: **sạch cả 15**.

### 2. Cách đọc: ba bậc gợi ý và bốn nhóm lỗi

??? tip "Gợi ý 1: ai sở hữu, ai trả?"
    Với mỗi `new`, mỗi con trỏ thô, mỗi tài nguyên: **một** chủ, trả **một** lần, trên **mọi** đường thoát (`return` sớm, `throw`). Hai đối tượng cùng giữ một con trỏ thô để trả là báo động.

??? tip "Gợi ý 2: ai sống lâu hơn ai?"
    Mỗi con trỏ, tham chiếu, iterator, `string_view` nhìn vào thứ gì, và thứ đó có **chết trước** nó không (hết vòng `for`, hết hàm, hết câu lệnh, container cấp phát lại)?

??? tip "Gợi ý 3: chữ ký có giữ lời hứa không?"
    Đọc từng chữ ký như một hợp đồng: `const` hứa không sửa, `noexcept` hứa không ném, `virtual ~` hứa xóa qua lớp cha được, kiểu `int` hứa đủ rộng cho đầu vào. Tìm chỗ thân hàm hay người gọi **phá** lời hứa đó.

Bốn nhóm lỗi để định hướng: **sở hữu và trả bộ nhớ** (mục 1 đến 4), **sống lâu hơn nguồn** (mục 5 đến 8), **sai âm thầm, không UB** (mục 9 đến 11: kết quả hoặc chi phí sai mà công cụ vẫn im) và **luật của ngôn ngữ** (mục 12 đến 15: tràn số, `const`, `noexcept`, che tên).

## 💻 Ví dụ code

### Mục 1: rò rỉ do thoát sớm

```cpp
// bo-qua-kiem-tra
#include <cctype>
#include <iostream>
#include <string>
std::string vietHoa(const std::string& s) {
    char* tam = new char[s.size() + 1];                  // (1) xin bộ đệm
    if (s.empty()) return "";                            // (2) thoát sớm: không ai trả tam
    for (std::size_t i = 0; i < s.size(); ++i)
        tam[i] = static_cast<char>(std::toupper(s[i]));
    tam[s.size()] = '\0';
    std::string kq(tam);
    delete[] tam;                                        // (3) chỉ đường đi dài mới tới đây
    return kq;
}
int main() {
    std::cout << vietHoa("abc") << "|" << vietHoa("") << "|\n";
}
```

**Tìm lỗi:** kết quả in ra là `ABC||`, đúng ý. Vậy đoạn này sai ở đâu, và vì sao chạy thường không thấy?

??? tip "Xem đáp án"
    **Lỗi:** (1) xin bộ đệm bằng `new[]` (`std::toupper` đổi một ký tự sang chữ hoa), nhưng đường `return ""` ở (2) thoát **trước** `delete[]` ở (3): mỗi lần gọi với chuỗi rỗng là rò một khối. Rò rỉ **không phải UB** ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)): chương trình vẫn đúng luật và in đúng, hại là bộ nhớ phình dần khi gọi hàng triệu lần. Mỗi `return` hay `throw` thêm về sau lại thêm một lỗ.

    **Mình đã chạy:** thường và `-O2` đều in `ABC||`, thoát mã 0, không báo gì. ASan (LeakSanitizer) báo khi chương trình kết thúc, thoát mã 1:

    ```text
    ERROR: LeakSanitizer: detected memory leaks
    Direct leak of 1 byte(s) in 1 object(s) allocated from:
        #1 … in vietHoa(std::string const&) 01.cpp:5
    ```

    **Sửa** (đã chạy: in `ABC||`, ASan sạch): để `unique_ptr` trả hộ trên mọi đường ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md); `make_unique<char[]>(n)` là bản mảng); dùng thẳng `std::string` còn gọn hơn. Đổi `new char[...]` thành `auto tam = std::make_unique<char[]>(s.size() + 1);` (thêm `<memory>`), bỏ `delete[]` và dựng kết quả bằng `std::string kq(tam.get(), s.size());`.

### Mục 2: `double free` do sao chép mặc định

```cpp
// bo-qua-kiem-tra
#include <cstring>
#include <iostream>
class Buf {
    char* d_;
public:
    explicit Buf(const char* s) : d_(new char[std::strlen(s) + 1]) { std::strcpy(d_, s); }
    ~Buf() { delete[] d_; }                              // (1) hàm hủy trả vùng nhớ
    const char* c() const { return d_; }
};
void in(Buf b) { std::cout << b.c() << "\n"; }           // (2) tham số theo giá trị: sao chép Buf
int main() {
    Buf a("xin chao");
    in(a);                                               // (3) bản sao dùng chung d_ với a
}                                                        // (4) a bị hủy
```

**Tìm lỗi:** hàm hủy trả bộ nhớ đàng hoàng, `in` chỉ in. Vì sao chương trình sập?

??? tip "Xem đáp án"
    **Lỗi:** `Buf` (`strlen` đếm ký tự, `strcpy` chép chuỗi kiểu C) giữ con trỏ **sở hữu** `d_` mà không tự viết hàm tạo sao chép, nên trình biên dịch sinh bản chép **từng thành viên**: con trỏ được chép, vùng nhớ thì không. `in(a)` ở (3) nhận theo giá trị nên có `b` cùng trỏ một vùng với `a`. Hết `in`, `b` bị hủy và trả vùng (lần 1); hết `main`, `a` bị hủy và trả lại lần nữa (lần 2). Đây là quy tắc 3 ([Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md)): đã tự viết hàm hủy thì phải quyết định cả sao chép.

    **Mình đã chạy:** thường và `-O2`: `free(): double free detected in tcache 2`, mã 134, và dòng `xin chao` mất khi in qua đường ống vì `abort` không xả bộ đệm. ASan báo rõ ba chỗ (UB: tin nhắn cụ thể là của glibc và ASan, không phải của chuẩn):

    ```text
    ERROR: AddressSanitizer: attempting double-free on 0x… in thread T0:
        #2 … in main 02.cpp:14
    freed by thread T0 here:   … #2 … in main 02.cpp:13
    ```

    **Sửa** (đã chạy: in `xin chao`, ASan sạch): cấm sao chép (nếu cần sao chép thì viết đúng hoặc dùng `std::string`), và nhận tham số bằng tham chiếu. Thêm `Buf(const Buf&) = delete;` và `Buf& operator=(const Buf&) = delete;`, đổi `in(Buf b)` thành `in(const Buf& b)`.

### Mục 3: `new[]` mà `delete` thường

```cpp
// bo-qua-kiem-tra
#include <iostream>
struct Hat {
    ~Hat() { std::cout << "huy\n"; }
};
int main() {
    Hat* ds = new Hat[3];                                // (1) xin mảng 3 phần tử
    delete ds;                                           // (2) trả bằng delete thường
    std::cout << "xong\n";
}
```

**Tìm lỗi:** `Hat` có hàm hủy in `huy`. Chương trình có in `huy` ba lần rồi `xong` không?

??? tip "Xem đáp án"
    **Lỗi:** `new Hat[3]` phải đi cặp với `delete[]`. Với kiểu có hàm hủy, trình biên dịch thường xin thêm một ô ghi số phần tử ở **đầu** khối; `delete` thường chỉ gọi hàm hủy của phần tử đầu rồi đưa `free` địa chỉ phần tử đầu, lệch so với địa chỉ khối thật. Chuẩn chỉ nói UB; [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) không ghi kết quả, đây là cái mình đã chạy.

    **Mình đã chạy:** g++ báo ngay lúc **biên dịch** (`-Wall`): `warning: 'void operator delete(void*, std::size_t)' called on pointer '<unknown>' with nonzero offset 8 [-Wfree-nonheap-object]`. Chạy: `munmap_chunk(): invalid pointer`, mã 134 (`-O2`: `free(): invalid pointer`); `huy` in đúng **một** lần (thấy khi chạy với `stdbuf -oL`, lệnh ép xả bộ đệm theo từng dòng) và `xong` không bao giờ in. ASan:

    ```text
    ERROR: AddressSanitizer: attempting free on address which was not malloc()-ed: 0x… in thread T0
    0x… is located 8 bytes inside of 11-byte region
    SUMMARY: AddressSanitizer: bad-free … in operator delete(void*, unsigned long)
    ```

    **Sửa** (đã chạy: `xong` rồi `huy` ba lần, ASan sạch): đừng viết `new[]` bằng tay. (Giữ `new[]` thì `delete[] ds;` cũng đúng, mình đã chạy: `huy` ba lần rồi `xong`.) Thay hai dòng `new`/`delete` bằng `std::vector<Hat> ds(3);` (thêm `<vector>`).

### Mục 4: thiếu hàm hủy `virtual`, không thấy chữ `delete` nào

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <memory>
#include <string>
struct Hinh {
    virtual double dienTich() const = 0;                 // (1) lớp cha đa hình, hàm hủy không virtual
};
struct Tron : Hinh {
    std::string ten = "hinh tron co ten dai hon muoi sau ky tu";
    ~Tron() { std::cout << "huy Tron\n"; }
    double dienTich() const override { return 3.14; }
};
std::unique_ptr<Hinh> tao() { return std::make_unique<Tron>(); }
int main() {
    auto h = tao();
    std::cout << h->dienTich() << "\n";
}                                                        // (2) h xóa qua Hinh*
```

**Tìm lỗi:** không có chữ `delete` nào trong code. Vậy hàm hủy của `Tron` có chạy khi `h` ra khỏi `main` không?

??? tip "Xem đáp án"
    **Lỗi:** `unique_ptr<Hinh>` giữ một `Tron` thật nhưng khi hủy nó xóa qua `Hinh*`, mà `~Hinh` không `virtual`: theo chuẩn là UB ([Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md)). Bài 33 chạy bản `new`/`delete` viết thẳng; ở đây `delete` nằm ẩn trong `unique_ptr`, nên dễ lọt khi review. Quy tắc: lớp có hàm ảo và được dùng làm lớp cha thì hàm hủy phải `virtual`.

    **Mình đã chạy:** thường và `-O2` in `3.14`, thoát mã 0, **không** in `huy Tron`: chuỗi `ten` của `Tron` không được trả, rò im lặng; `-Wall -Wextra` cũng im. Tắt riêng cảnh báo mismatch bằng `ASAN_OPTIONS=new_delete_type_mismatch=0` thì LeakSanitizer báo `Direct leak of 40 byte(s)` từ `Tron::Tron() 04.cpp:7`. ASan mặc định chặn ngay:

    ```text
    ERROR: AddressSanitizer: new-delete-type-mismatch on 0x… in thread T0:
      size of the allocated type:   40 bytes;
      size of the deallocated type: 8 bytes.
        #1 … in std::default_delete<Hinh>::operator()(Hinh*) const
    ```

    **Sửa** (đã chạy: in `3.14` rồi `huy Tron`, ASan sạch): thêm `virtual ~Hinh() = default;` vào `Hinh`.

### Mục 5: con trỏ tới biến của vòng `for`

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>
int main() {
    std::vector<int> v = {3, 9, 4};
    const int* lon = nullptr;
    for (int x : v)                                      // (1) x là bản sao, mỗi vòng một lần sống
        if (!lon || x > *lon) lon = &x;                  // (2) nhớ địa chỉ của x
    std::cout << "lon nhat = " << *lon << "\n";          // (3) x đã hết vòng đời
}
```

**Tìm lỗi:** tìm số lớn nhất của `{3, 9, 4}`. Kết quả có phải `9` không? Sau vòng `for`, `lon` đang trỏ vào đâu?

??? tip "Xem đáp án"
    **Lỗi:** `for (int x : v)` tạo `x` là **bản sao**, sống trong đúng một vòng. `lon = &x` nhớ địa chỉ của biến sắp hết vòng đời; trên build thường `x` nằm cùng một ô qua các vòng nên phép so `x > *lon` so ô đó với chính nó và không bao giờ "lớn hơn"; sau vòng `for`, `*lon` ở (3) đọc biến đã chết (con trỏ treo, UB).

    **Mình đã chạy:** thường in `lon nhat = 4` (sai: giá trị **cuối**, không phải `9`); `-O2` cũng in `4`, kèm cảnh báo `'*lon' may be used uninitialized [-Wmaybe-uninitialized]`. ASan chỉ đúng biến:

    ```text
    ERROR: AddressSanitizer: stack-use-after-scope on address 0x… thread T0
        #0 … in main 05.cpp:8
        [48, 52) 'x' (line 6) <== Memory access at offset 48 is inside this variable
    ```

    **Sửa** (đã chạy: `lon nhat = 9`, ASan sạch): `x` là **tham chiếu** tới phần tử của `v`, nên `&x` là địa chỉ phần tử thật, sống tới khi `v` chết. Muốn chắc hơn thì giữ chỉ số hoặc iterator, hay dùng `std::max_element`. Đổi thành `for (const int& x : v)`.

### Mục 6: trả tham chiếu tới biến cục bộ

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
const std::string& ghep(const std::string& a, const std::string& b) {
    std::string kq = a + " " + b;                        // (1) biến cục bộ
    return kq;                                           // (2) trả tham chiếu tới nó
}
int main() {
    const std::string& s = ghep("xin", "chao");
    std::cout << s << "\n";                              // (3) kq đã chết
}
```

**Tìm lỗi:** `ghep` trả `const std::string&` "cho đỡ chép". Chuyện gì xảy ra ở dòng `cout`?

??? tip "Xem đáp án"
    **Lỗi:** `kq` là biến cục bộ, chết khi `ghep` kết thúc ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)); tham chiếu trả về trỏ vào chỗ đã dọn. Không bao giờ trả tham chiếu tới thứ chết cùng hàm. Trả **giá trị**: trình biên dịch thường bỏ hẳn bước chép (NRVO, [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)).

    **Mình đã chạy:** g++ báo ngay lúc biên dịch với `-Wall`: `warning: reference to local variable 'kq' returned [-Wreturn-local-addr]`. Chạy: thường và `-O2` đều `Segmentation fault` (mã 139), không in gì. Dưới ASan + UBSan (UB: chỉ là cái g++ 11 làm ở đây) mình thấy `06.cpp:5:12: runtime error: reference binding to null pointer of type 'const struct string'`, rồi `ERROR: AddressSanitizer: SEGV on unknown address 0x000000000008`. Dòng đầu cho thấy g++ dường như đã **thay địa chỉ trả về bằng null** ngay tại `return` (suy luận từ báo cáo; mình xem thêm `g++ -S -O0` thì giá trị trả về được đặt thành `0`, khớp với suy luận), nên đây không phải `stack-use-after-return` (loại ASan cần `ASAN_OPTIONS=detect_stack_use_after_return=1`; mình thử, báo cáo vẫn như trên). Nơi khác có thể in rác hay chữ cũ.

    **Sửa** (đã chạy: in `xin chao`, ASan sạch): đổi kiểu trả về thành `std::string`, và `main` nhận `std::string s = ghep(...)`.

### Mục 7: `string_view` nhìn vào chuỗi tạm

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <string>
#include <string_view>
std::string_view tuDau(const std::string& dong) {
    return std::string_view(dong).substr(0, dong.find(' '));   // (1) nhìn vào dong
}
std::string docDong() { return "xin chao cac ban hom nay"; }
int main() {
    std::string_view w = tuDau(docDong());               // (2) docDong() trả chuỗi tạm
    std::cout << w << "\n";                              // (3) chuỗi tạm chết từ cuối dòng (2)
}
```

**Tìm lỗi:** `tuDau` trả `string_view` nhìn vào tham số `dong`. Hàm này có đúng không? Còn dòng (2) trong `main`?

??? tip "Xem đáp án"
    **Lỗi:** bản thân `tuDau` chỉ đúng **nếu** chuỗi truyền vào sống lâu hơn kết quả. Ở (2), `docDong()` trả chuỗi **tạm**; tham số `const std::string&` gắn vào tạm; tạm chết ở cuối câu lệnh (2), còn `w` giữ cửa sổ vào bộ nhớ đã trả. Chuỗi đủ dài (trên 15 ký tự với g++) nên nằm ở heap, để ASan thấy rõ. [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) nêu hai ca treo của `string_view`; đây là ca thứ ba, đi qua tham số `const&`: lỗi nằm ở **hợp đồng**, kiểu trả về `string_view` hứa điều mà chữ ký không bảo đảm.

    **Mình đã chạy:** thường in rác (một ký tự lạ rồi byte lạ), `-O2` in rác **khác**: hai build, hai kết quả, đúng kiểu UB. ASan:

    ```text
    ERROR: AddressSanitizer: heap-use-after-free on address 0x…
        #3 … in main 07.cpp:10
    freed by thread T0 here:  … #1 … in main 07.cpp:9
    ```

    **Sửa** (đã chạy: in `xin`, ASan sạch): trả `std::string` (chép vài byte). Giữ `string_view` thì người gọi phải tự giữ chuỗi bằng biến có tên (`std::string dong = docDong(); auto w = tuDau(dong);`), và chữ ký không ép được điều đó. Đổi kiểu trả về thành `std::string` với thân `return dong.substr(0, dong.find(' '));`.

### Mục 8: xóa khi đang duyệt

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>
int main() {
    std::vector<int> v = {1, 2, 3, 4, 5, 6};
    for (auto it = v.begin(); it != v.end(); ++it)
        if (*it % 2 == 0) v.erase(it);                   // (1) xóa số chẵn khi đang duyệt
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";
}
```

**Tìm lỗi:** muốn xóa số chẵn của `{1..6}`, kết quả mong đợi `1 3 5`. Dòng (1) có vấn đề gì?

??? tip "Xem đáp án"
    **Lỗi:** `erase(it)` làm `it` hỏng và **trả về** iterator kế tiếp ([Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md)); code bỏ giá trị trả về rồi `++it`. Dữ liệu `{1, 2, 2, 3}` của Bài 19 chỉ "sót" một số 2 trong im lặng. Dữ liệu ở đây tệ hơn: sau khi xóa `6` (phần tử cuối), `it` bằng `end()`, `++it` đi **quá** `end()` nên `it != v.end()` luôn đúng và vòng lặp chạy tiếp ra ngoài vùng nhớ.

    **Mình đã chạy:** thường và `-O2`: `Segmentation fault` (mã 139), không in gì. ASan:

    ```text
    ERROR: AddressSanitizer: negative-size-param: (size=-8)
        #6 … in std::vector<int>::_M_erase(…)
        #8 … in main 08.cpp:6
    ```

    (`erase` bị gọi với iterator quá `end()` nên dồn dãy với cỡ âm: chi tiết của libstdc++; chuẩn chỉ nói UB.)

    **Sửa** (đã chạy: in `1 3 5`, ASan sạch): nhận iterator mà `erase` trả về, và chỉ `++` khi không xóa. Viết `for (auto it = v.begin(); it != v.end();)` với `if (*it % 2 == 0) it = v.erase(it); else ++it;`.

### Mục 9: slicing trong `vector`

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>
struct Hinh {
    virtual ~Hinh() = default;
    virtual double dienTich() const { return 0; }
};
struct Vuong : Hinh {
    double canh;
    explicit Vuong(double c) : canh(c) {}
    double dienTich() const override { return canh * canh; }
};
int main() {
    std::vector<Hinh> ds;                                // (1) vector chứa Hinh, không phải Vuong
    ds.push_back(Vuong(3));                              // (2)
    std::cout << ds[0].dienTich() << "\n";
}
```

**Tìm lỗi:** `Vuong` cạnh 3 nên diện tích phải là `9`. Chương trình in gì? Có công cụ nào báo lỗi không?

??? tip "Xem đáp án"
    **Lỗi:** `std::vector<Hinh>` chứa **đối tượng `Hinh`**, không chứa `Vuong`. `push_back(Vuong(3))` ở (2) chép riêng phần `Hinh` của `Vuong` vào ô; phần `canh` bị cắt bỏ (slicing, [Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md)). Ô đó là một `Hinh` thật, nên hàm ảo `dienTich()` chạy bản của `Hinh`. Đa hình chỉ có qua con trỏ hoặc tham chiếu.

    **Mình đã chạy:** thường, `-O2` và ASan + UBSan đều in `0` (không phải `9`), thoát mã 0; `-Wall -Wextra` im. **Đây không phải UB**: chương trình đúng luật, chỉ sai ý, nên không công cụ nào có gì để báo. Nếu `Hinh` có hàm thuần ảo `= 0` thì g++ báo lỗi biên dịch (không tạo được `Hinh`); lỗi chỉ lọt khi lớp cha là lớp cụ thể.

    **Sửa** (đã chạy: in `9`, ASan sạch): chứa con trỏ thông minh tới lớp cha ([Bài 33](../nhom-4-oop-patterns/33-da-hinh-virtual.md)). Đổi thành `std::vector<std::unique_ptr<Hinh>> ds;`, `ds.push_back(std::make_unique<Vuong>(3));` và `ds[0]->dienTich()` (thêm `<memory>`).

### Mục 10: sao chép khi nên chuyển

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <utility>
#include <vector>
struct Goi {
    static inline int sao = 0, chuyen = 0;
    Goi() = default;
    Goi(const Goi&) { ++sao; }
    Goi(Goi&&) noexcept { ++chuyen; }
};
std::vector<Goi> kho;
void nhap(Goi g) { kho.push_back(g); }                   // (1) g dùng lần cuối ở đây
int main() {
    kho.reserve(8);
    for (int i = 0; i < 3; ++i) nhap(Goi{});
    std::cout << "chep=" << Goi::sao << " chuyen=" << Goi::chuyen << "\n";
}
```

**Tìm lỗi:** mỗi lần `nhap(Goi{})` có cần sao chép `Goi` không? Chạy xong thì `chep` bằng mấy?

??? tip "Xem đáp án"
    **Lỗi:** `g` là bản của riêng hàm (C++17 dựng thẳng từ tạm `Goi{}`, không chép) và dùng lần cuối ở (1); nhưng `g` là biến có tên, tức **lvalue**, nên `push_back(g)` chọn **sao chép**. Nếu `Goi` giữ chuỗi hay vector lớn, mỗi lần gọi trả thêm một bản chép đầy đủ cho việc mà chuyển (`std::move`, lấy ruột) làm gần như miễn phí ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)). Đây là tham số "bồn" ([Bài 55](../nhom-7-chon-dung-cong-cu/55-api-so-huu-tham-so.md)): nhận theo giá trị thì phải `move` vào chỗ cất.

    **Mình đã chạy:** cả ba cách chạy in `chep=3 chuyen=0` (`sao` và `chuyen` là bộ đếm `static inline`, một bản dùng chung cho cả kiểu, tăng trong hàm tạo sao chép và hàm tạo chuyển; `reserve(8)` để việc tăng khối của `vector` không chen vào số đếm). Đây không phải lỗi đúng sai: chỉ là **chi phí**, nên mọi công cụ đều im, bạn phải đếm hoặc đo.

    **Sửa** (đã chạy: `chep=0 chuyen=3`, ASan sạch): viết `kho.push_back(std::move(g));` và sau đó đừng dùng `g` nữa (nó đã bị lấy ruột).

### Mục 11: so sánh có dấu với không dấu

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <vector>
int main() {
    int ton = -3;                                        // (1) tồn kho âm: đang nợ hàng
    std::vector<int> don = {1, 2};                       // (2) 2 đơn cần giao
    if (ton < don.size()) std::cout << "khong du hang\n";
    else std::cout << "du hang\n";
}
```

**Tìm lỗi:** `ton` là `-3`, `don.size()` là `2`. Chương trình in gì, và g++ nói gì khi biên dịch?

??? tip "Xem đáp án"
    **Lỗi:** `ton` là `int`, `don.size()` là `std::size_t` (không dấu). Khi so sánh, `int` bị đổi thành không dấu: `-3` thành 2 mũ 64 trừ 3, một số rất lớn, lớn hơn `2`, nên `ton < don.size()` ra **sai** dù toán học `-3 < 2`. Phép so sánh đúng luật (không UB), chỉ sai ý.

    **Mình đã chạy:** g++ báo ngay với `-Wall` (cảnh báo `-Wsign-compare`, **phải đọc**): `warning: comparison of integer expressions of different signedness: 'int' and 'std::vector<int>::size_type' {aka 'long unsigned int'} [-Wsign-compare]`

    Cả ba cách chạy in `du hang` (sai; mong đợi `khong du hang`); ASan và UBSan im vì không có UB.

    **Sửa** (đã chạy: `khong du hang`, sạch cảnh báo): ép **về kiểu có dấu** khi chắc `size()` nhỏ hơn `INT_MAX`. C++20 có `std::cmp_less(ton, don.size())` so đúng mọi cặp kiểu nguyên (mình đã chạy với `-std=c++20`: `khong du hang`). Viết `ton < static_cast<int>(don.size())`.

### Mục 12: tràn số `int`

```cpp
// bo-qua-kiem-tra
#include <iostream>
int msTuGio(int gio) { return gio * 3600 * 1000; }       // (1) 3 600 000 mili giây mỗi giờ
int main() {
    std::cout << msTuGio(1) << "\n";
    std::cout << msTuGio(1000) << "\n";                  // (2) 1000 giờ
}
```

**Tìm lỗi:** `msTuGio(1)` ra `3600000`. Còn `msTuGio(1000)` thì sao?

??? tip "Xem đáp án"
    **Lỗi:** `gio * 3600 * 1000` tính bằng `int`; 1000 giờ là 3 600 000 000 mili giây, vượt `INT_MAX` (2 147 483 647). Tràn `int` **có dấu** là UB ([Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)); số không dấu thì quấn vòng có định nghĩa. Hàm đúng với đầu vào nhỏ nên qua test, hỏng khi đầu vào lớn.

    **Mình đã chạy:** thường và `-O2` in `-694967296` (trông như quấn vòng; UB: không phải bảo đảm); `-Wall` im vì giá trị chỉ có lúc chạy. UBSan: `12.cpp:2:44: runtime error: signed integer overflow: 1000 * 3600000 cannot be represented in type 'int'`

    **Sửa** (đã chạy: `3600000` rồi `3600000000`, UBSan sạch): tính bằng kiểu rộng, **trước** khi nhân (`3600LL` là hằng kiểu `long long`). Chỉ đổi kiểu trả về mà vẫn viết `gio * 3600 * 1000` thì vẫn tràn, vì phép nhân xong bằng `int` rồi mới đổi kiểu (mình đã chạy: UBSan vẫn báo). Viết `long long msTuGio(int gio) { return gio * 3600LL * 1000; }`.

### Mục 13: bỏ `const` để ghi

```cpp
// bo-qua-kiem-tra
#include <cctype>
#include <iostream>
void vietHoaDau(const char* s) {
    char* p = const_cast<char*>(s);                      // (1) bỏ const để sửa
    p[0] = static_cast<char>(std::toupper(p[0]));        // (2) ghi vào chỗ s trỏ tới
}
int main() {
    char co[] = "an";
    vietHoaDau(co);
    std::cout << co << std::endl;
    vietHoaDau("binh");                                  // (3) chuỗi chữ
    std::cout << "xong\n";
}
```

**Tìm lỗi:** hàm hứa `const char*` (không sửa) nhưng lại sửa. Lời gọi nào chạy được, lời gọi nào không?

??? tip "Xem đáp án"
    **Lỗi:** `const_cast<char*>(s)` bảo trình biên dịch coi `s` là không `const` để ghi. Với `co` (mảng thường), ghi là hợp lệ. Nhưng `"binh"` là chuỗi chữ, nằm ở vùng chỉ đọc; ghi vào đối tượng vốn là `const` là UB. Chữ ký `const char*` là lời hứa với người gọi, phá lời hứa thì người gọi đưa chuỗi chữ chịu hậu quả. Cần sửa thì nhận bản sao hoặc tham số không `const`.

    **Mình đã chạy:** thường và `-O2` in `An` rồi `Segmentation fault` (mã 139), `xong` không in; `-Wall -Wextra` im, vì `const_cast` nói "tôi biết tôi đang làm gì". ASan:

    ```text
    ERROR: AddressSanitizer: SEGV on unknown address 0x…
    The signal is caused by a WRITE memory access.
        #0 … in vietHoaDau(char const*) 13.cpp:5
    ```

    (Sập vì vùng chỉ đọc là điều thường thấy trên Linux, chuẩn không hứa.) **Sửa** (đã chạy: `An`, `Binh`, `xong`, ASan sạch): nhận `std::string` theo giá trị, sửa bản của mình rồi trả về. Viết `std::string vietHoaDau(std::string s)` rồi `s[0] = ...` và `return s;`.

### Mục 14: `noexcept` mà vẫn ném

```cpp
// bo-qua-kiem-tra
#include <exception>
#include <iostream>
#include <string>
int doc(const std::string& s) noexcept { return std::stoi(s); }   // (1) lời hứa không ném
int main() {
    try {
        std::cout << doc("12") << std::endl;
        std::cout << doc("abc") << std::endl;            // (2) stoi ném invalid_argument
    } catch (const std::exception& e) {
        std::cout << "bat duoc: " << e.what() << "\n";   // (3)
    }
}
```

**Tìm lỗi:** `main` có `try`/`catch`. Lời gọi `doc("abc")` có bị bắt không?

??? tip "Xem đáp án"
    **Lỗi:** `noexcept` hứa hàm không ném ra ngoài. `std::stoi` đổi chuỗi thành số, và `std::stoi("abc")` ném `std::invalid_argument`; ngoại lệ chạm biên `noexcept` thì gọi thẳng `std::terminate`, `catch` không kịp chạy. [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md) dạy ca `throw` viết thẳng (g++ có cảnh báo `-Wterminate`); ở đây ngoại lệ đến **gián tiếp** qua hàm khác nên không cảnh báo nào: chỉ thêm `noexcept` khi chắc cả những thứ hàm gọi cũng không ném.

    **Mình đã chạy:** thường và ASan in `12`, rồi `terminate called after throwing an instance of 'std::invalid_argument'` và `  what():  stoi`, mã 134; `-O2` in `terminate called without an active exception` (cùng mã 134: thông báo đổi theo build). Dòng `bat duoc` không bao giờ in; `-Wall -Wextra` im.

    **Sửa** (đã chạy: `12` rồi `bat duoc: stoi`, ASan sạch): bỏ `noexcept` để ngoại lệ đi lên chỗ có `catch`. Muốn hàm không ném thật sự thì bắt ngay trong hàm rồi trả `std::optional`.

### Mục 15: tên tham số che tên thành viên

```cpp
// bo-qua-kiem-tra
#include <iostream>
struct Kho {
    int sucChua;
    explicit Kho(int sucChua) { sucChua = sucChua; }     // (1) tham số gán cho chính nó
    bool conCho(int dem) const { return dem < sucChua; } // (2) đọc thành viên
};
int main() {
    Kho k(10);
    std::cout << (k.conCho(5) ? "con cho" : "het cho") << "\n";
}
```

**Tìm lỗi:** `Kho k(10)` rồi `conCho(5)` phải in `con cho`. Dòng (1) thật sự làm gì?

??? tip "Xem đáp án"
    **Lỗi:** tham số `sucChua` trùng tên thành viên `sucChua`. Trong thân hàm tạo, tên đó chỉ **tham số** (nó che thành viên), nên `sucChua = sucChua` tự gán cho chính tham số; thành viên không bao giờ được gán. Đọc nó ở (2) là đọc giá trị chưa khởi tạo (UB, [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)).

    **Mình đã chạy:** `-Wall -Wextra` ở build thường **im**. Chạy thường 10/10 lần in `con cho` (đúng do may: rác lớn hơn 5); `-O2` 10/10 lần in `het cho` (sai, dù `5 < 10`), và lúc này g++ báo `warning: 'k.Kho::sucChua' is used uninitialized [-Wuninitialized]`. ASan + UBSan im: chúng **không** bắt đọc biến chưa khởi tạo (công cụ chuyên là MemorySanitizer của clang hay Valgrind; máy mình không có hai thứ này nên không chạy). Cảnh báo `-Wshadow` (không nằm trong `-Wall -Wextra`) nói thẳng: `warning: declaration of 'sucChua' shadows a member of 'Kho' [-Wshadow]`

    **Sửa** (đã chạy: `con cho`, sạch `-Wshadow`, ASan sạch): khởi tạo thành viên trong danh sách khởi tạo và đặt tên tham số khác tên thành viên. Viết `explicit Kho(int suc) : sucChua(suc) {}`.

### Bảng phân loại: triệu chứng, công cụ, nguyên nhân hay gặp

| Triệu chứng hoặc thứ công cụ báo | Nghi trước | Mục |
|---|---|---|
| ASan `LeakSanitizer: detected memory leaks`; chạy thường vẫn đúng | Một đường thoát (`return`, `throw`) không trả tài nguyên | 1 |
| `free(): double free detected`, ASan `double-free`, `bad-free`, `new-delete-type-mismatch`, mã 134 | Hai chủ cho một vùng (sao chép con trỏ thô), `delete` sai cặp, xóa qua lớp cha không `virtual` | 2, 3, 4 |
| ASan `stack-use-after-scope`, `heap-use-after-free`; in rác đổi theo `-O` | Con trỏ, tham chiếu, `string_view` sống lâu hơn nguồn | 5, 6, 7 |
| `Segmentation fault` (139) ở chỗ tưởng vô hại; ASan `negative-size-param` | Iterator vô hiệu; ghi vào vùng chỉ đọc (`const_cast`) | 8, 13 |
| Kết quả sai, **mọi công cụ im** | Slicing, sao chép thay vì chuyển (đếm), so sánh có dấu với không dấu (`-Wsign-compare` có nói) | 9, 10, 11 |
| UBSan `signed integer overflow`; số âm ở chỗ không thể âm | Phép tính `int` vượt miền | 12 |
| `terminate called after throwing`, mã 134, `catch` không chạy | `noexcept` hứa sai, hàm hủy ném | 14 |
| Đúng ở `-O0`, sai ở `-O2`; `-Wuninitialized` hiện khi bật `-O2` | Đọc giá trị chưa khởi tạo; bật thêm `-Wshadow` | 15 |

!!! info "Bạn biết Go?"
    Vài khác biệt (kiến thức ngôn ngữ, mình không chạy Go ở bài này). Go có GC nên không có rò rỉ do quên trả, `double free`, hay con trỏ treo kiểu mục 1 đến 7; trả địa chỉ biến cục bộ hợp lệ nhờ escape analysis, `string` bất biến nên cắt chuỗi con dùng chung bộ nhớ an toàn. Sau `append`, slice cũ có thể còn trỏ mảng cũ, giống iterator cũ ở mục 8, nhưng GC giữ mảng cũ sống nên không đọc phải rác. Go không có kế thừa kiểu C++ hay hàm hủy nên không có slicing hay mục 4, không có `noexcept` (lỗi trả về bằng `error`, `panic` là chuyện khác), và `const` chỉ là hằng lúc biên dịch. Số nguyên có dấu tràn thì quấn vòng có định nghĩa; so `int` với `uint` không ép kiểu là **lỗi biên dịch** (mục 11 và 12 không có tương đương).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Cho một đoạn C++ lạ để review, bạn đọc theo thứ tự nào?"
    Mình hỏi bốn câu. Một: ai **sở hữu** mỗi tài nguyên, và có trả đúng một lần trên mọi đường thoát (`return` sớm, `throw`) không. Hai: con trỏ, tham chiếu, iterator, `string_view` nào có thể sống **lâu hơn** thứ nó nhìn vào. Ba: kiểu số có đủ rộng và có lẫn có dấu với không dấu không. Bốn: chữ ký có giữ lời hứa (`const`, `noexcept`, `virtual ~`) không. Khi nói lại, mình nêu lỗi, hậu quả theo thứ tự thời gian, rồi bản sửa.

??? question "Thế nếu ASan và UBSan chạy sạch thì code có đúng không?"
    Không chắc. Sanitizer chỉ thấy lỗi **xảy ra trong lần chạy đó**, và chỉ những loại chúng được dạy. Mình đã chạy ba mục mà chúng im: slicing in `0` thay vì `9`, sao chép thừa (`chep=3`), so sánh có dấu với không dấu. Chúng cũng im với biến chưa khởi tạo (mục 15). Nên mình còn bật `-Wall -Wextra -Wshadow`, đọc code theo bốn câu trên, và viết test có kết quả cụ thể.

??? question "Làm sao để các lỗi này không lọt vào code ngay từ đầu?"
    Giảm chỗ có thể sai. Để RAII và smart pointer lo việc trả, dùng `std::vector` và `std::string` thay `new[]` (hết mục 1 đến 3), hàm hủy `virtual` ở mọi lớp cha đa hình, nhận tham số bằng `const&` hay giá trị rồi `move`, trả giá trị thay vì tham chiếu. Bật `-Wall -Wextra -Wshadow` và coi cảnh báo là lỗi trong CI (`-Werror`), chạy test dưới ASan + UBSan, và đọc kỹ mọi `const_cast`, `noexcept`, `string_view` được trả về.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Sửa chỗ nổ thay vì chỗ gốc"
    Ở mục 2, thêm `d_ = nullptr` sau `delete[]` không cứu được: hai đối tượng có **hai** `d_` riêng. Ở mục 8, chặn bằng `if (it == v.end()) break;` vẫn bỏ sót phần tử. Hãy hỏi "ai sở hữu" và "ai sống lâu hơn" trước, rồi mới sửa dòng.

!!! warning "Lỗi 2: Tin \"chạy ra đúng\" hay \"công cụ im\" là xong"
    Mục 15 in đúng 10/10 lần ở `-O0` mà sai 10/10 lần ở `-O2`; mục 5 in `4` ở build thường; mục 9 và 10 sạch dưới mọi công cụ dù sai. Chứng minh sửa đúng bằng lập luận về sở hữu, vòng đời, bất biến, kèm test và sanitizer sạch.

!!! warning "Lỗi 3: Dập cảnh báo hay sanitizer bằng ép kiểu"
    `static_cast<int>(don.size())` (mục 11) là cách sửa hợp lý khi bạn **biết** kích thước nhỏ; thêm ép kiểu chỉ để g++ im thì đang giấu lỗi. Tương tự, `const_cast` (mục 13) hay `noexcept` thêm cho "nhanh" làm lỗi chuyển từ lúc biên dịch sang lúc chạy.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="83" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đoạn sau sai ở đâu?

`std::vector<int> v = {1, 2, 3}; int& a = v[0]; v.push_back(4); a = 9;`

- `int&` không gắn được vào phần tử của `vector`, phải dùng con trỏ thô
- `push_back` luôn dồn phần tử cũ sang trái nên `v[0]` không còn nữa
- `push_back` có thể cấp khối mới, trả khối cũ, nên `a` bị treo
- Phép gán `a = 9` đổi luôn cả ba phần tử vì chúng dùng chung ô nhớ

<p class="giai-thich" markdown>Vector khởi tạo từ ba số có chỗ vừa ba số trên g++, nên `push_back` thứ tư cấp khối mới, chép sang và trả khối cũ; tham chiếu `a` vẫn trỏ vào khối đã trả và ghi vào đó là dùng sau khi trả (ASan báo `heap-use-after-free`). `int&` gắn vào phần tử vector được. `push_back` không dồn phần tử sang trái. Mỗi phần tử có ô riêng, gán một phần tử không đổi các phần tử khác.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Với `ho` và `ten` là `std::string`, đoạn sau sai ở đâu?

`const char* p = (ho + ten).c_str(); std::cout << p;`

- Chuỗi tạm `ho + ten` chết cuối câu lệnh, `p` thành con trỏ treo
- `c_str()` chỉ hợp lệ với chuỗi chữ, không gọi được trên `std::string`
- `p` phải khai báo `char*` không `const` thì mới đọc được nội dung chuỗi
- `operator+` của hai `std::string` luôn trả tham chiếu tới chuỗi bên trái

<p class="giai-thich" markdown>`operator+` trả một chuỗi mới (tạm) và nó bị hủy ở cuối câu lệnh khai báo `p`; `p` giữ địa chỉ của bộ nhớ chuỗi tạm đã hết đời, nên dòng `cout` đọc chỗ đã chết. `c_str()` là hàm của chính `std::string`. `const char*` là kiểu đúng để đọc, bỏ `const` không giúp gì. `operator+` trả giá trị mới, không phải tham chiếu tới toán hạng.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đoạn sau sai ở đâu?

`std::vector<int> v = {4, 5, 6}; long tong = 0;` rồi `for (std::size_t i = v.size() - 1; i >= 0; --i) tong += v[i];`

- `size() - 1` luôn âm nên vòng `for` không chạy lần nào, `tong` giữ 0
- `tong` kiểu `long` quá hẹp để cộng ba số `int` nhỏ
- `v[i]` không dùng được khi biến đếm kiểu `std::size_t`, phải ép về `int`
- `i >= 0` luôn đúng với số không dấu nên `i` quấn vòng, đọc ngoài `v`

<p class="giai-thich" markdown>Số không dấu không bao giờ nhỏ hơn 0: sau `i = 0` thì `--i` quấn thành số rất lớn, điều kiện vẫn đúng và `v[i]` đọc ngoài biên (mình đã chạy: ASan báo `heap-buffer-overflow`; g++ `-Wextra` báo `comparison of unsigned expression in '>= 0' is always true`). `size() - 1` là số không dấu nên không "âm", chỉ quấn khi vector rỗng. `long` đủ rộng cho tổng này. `v[i]` nhận `std::size_t` chính là kiểu của chỉ số.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Giả sử `luu()` trả `false`. Đoạn sau chuyện gì xảy ra?

`struct Dong { ~Dong() { if (!luu()) throw std::runtime_error("loi luu"); } };` rồi `try { Dong d; } catch (...) { std::cout << "bat"; }`

- In `bat`, vì `catch (...)` bắt mọi ngoại lệ kể cả ngoại lệ ném từ hàm hủy
- Gọi `std::terminate`: hàm hủy là `noexcept`, ngoại lệ không thoát được
- Ngoại lệ bị nuốt im lặng vì lúc đó không còn nơi nào khác để nhận nó
- Không biên dịch được vì hàm hủy không được phép chứa câu lệnh `throw` nào

<p class="giai-thich" markdown>Từ C++11 hàm hủy mặc định là `noexcept`, nên ngoại lệ ném ra khỏi nó gọi thẳng `std::terminate`, `catch` ngoài không kịp chạy (mình đã chạy: `terminate called after throwing an instance of 'std::runtime_error'`, mã 134, và g++ cảnh báo `-Wterminate`). `catch (...)` không cứu được vì chương trình đã dừng trước đó. Ngoại lệ không bao giờ tự bị nuốt. Câu `throw` trong hàm hủy biên dịch được, chỉ cảnh báo.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Chương trình in đúng ở `-O0`, in sai ở `-O2`; ASan và UBSan im; `g++ -Wall -O2` báo `used uninitialized`. Nên nghi gì trước?

- Lỗi của `-O2` trong trình biên dịch, nên cứ build bằng `-O0` cho yên
- Data race giữa hai luồng, nên phải chạy TSan trước tiên
- Đọc giá trị chưa khởi tạo: UB mà `-O2` làm lộ ra, cần khởi tạo biến
- Rò rỉ bộ nhớ vì `-O2` đổi thứ tự giải phóng của các hàm hủy

<p class="giai-thich" markdown>Cảnh báo `used uninitialized` chỉ thẳng một giá trị chưa gán; ở `-O0` nó mang rác "may mắn" đúng, `-O2` đổi cách dùng rác nên kết quả đổi (mục 15). Đổ lỗi cho trình biên dịch và né `-O2` chỉ giấu lỗi. Chương trình không nhắc gì tới luồng nên chưa có lý do nghĩ tới data race. Rò rỉ thì không làm kết quả sai và `-O2` không đổi chuyện trả bộ nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Dòng cuối của `main` in ra gì?

```text
struct Chim { virtual ~Chim() = default;
              virtual std::string keu() const { return "..."; } };
struct Vet : Chim { std::string keu() const override { return "quac"; } };
void goi(Chim c) { std::cout << c.keu(); }
...  goi(Vet{});
```

- In `...`: `c` là một `Chim` thật, phần `Vet` bị cắt khi truyền theo giá trị
- In `quac`: hàm `keu` là `virtual` nên luôn chạy bản của lớp con dù truyền theo giá trị
- Lỗi biên dịch vì không đổi được `Vet` sang `Chim` khi truyền theo giá trị
- Hành vi không xác định vì `c` giữ con trỏ tới `Vet` đã chết từ lúc gọi

<p class="giai-thich" markdown>Truyền theo giá trị dựng một `Chim` mới từ phần `Chim` của `Vet` (slicing); `c` không còn là `Vet`, nên `keu()` ảo chạy bản của `Chim` và in `...` (mình đã chạy; không UB). `virtual` chỉ cho đa hình qua con trỏ hoặc tham chiếu. `Vet` là `Chim` nên chuyển được, chỉ là mất phần con. `c` là bản sao đầy đủ của phần cha, không giữ con trỏ nào.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Dòng nào trong đoạn sau là hành vi không xác định?

dòng X: `int a = 2000000000; int b = a + a;`, dòng Y: `unsigned c = 4000000000u + 400000000u;`

- Cả hai dòng đều là UB vì kết quả vượt miền của kiểu
- Chỉ dòng X là UB; dòng Y quấn vòng và có kết quả xác định
- Chỉ dòng Y là UB vì `unsigned` không có dấu để chứa số lớn
- Không dòng nào là UB; cả hai chỉ cho kết quả sai nhưng có định nghĩa

<p class="giai-thich" markdown>Tràn `int` có dấu là UB (UBSan báo `signed integer overflow`), còn số không dấu quấn vòng theo modulo 2 mũ 32 nên dòng Y có kết quả xác định (mình đã chạy: `105032704`). Hai dòng khác nhau về kiểu nên không thể cùng là UB. `unsigned` không "không biểu diễn được", nó quấn vòng. Dòng X đã là UB nên không thể nói "không dòng nào".</p>
</div>

</div>

## 🔑 Tóm tắt

1. Đọc code lạ bằng bốn câu hỏi: ai sở hữu và có trả đúng một lần trên mọi đường thoát, ai sống lâu hơn ai, kiểu số có đủ không, chữ ký có giữ lời hứa (`const`, `noexcept`, `virtual ~`) không; khi nói, nêu lỗi, cơ chế theo thứ tự thời gian, rồi bản sửa.
2. Sở hữu (mục 1 đến 4): `return` sớm bỏ sót `delete[]`; sao chép con trỏ thô gây `double free`; `new[]` phải đi với `delete[]`; lớp cha đa hình cần `virtual ~`, kể cả khi `delete` ẩn trong `unique_ptr`. Cách sửa chung: RAII, `vector`, `unique_ptr`.
3. Vòng đời (mục 5 đến 8): `for (int x : v)` cho `x` là bản sao, trả tham chiếu cục bộ, `string_view` gắn vào chuỗi tạm, `erase` rồi `++it` đều dùng thứ đã chết; ASan nói rõ, còn chạy thường chỉ in rác hay sập.
4. Lỗi sai âm thầm (mục 9, 10, 11): slicing, sao chép thừa và so sánh có dấu với không dấu cho kết quả hoặc chi phí sai mà không UB nên sanitizer im; chỉ `-Wsign-compare`, đếm hay đọc code mới thấy. Luật ngôn ngữ (mục 12 đến 15): tràn `int` có dấu là UB (UBSan), `const_cast` ghi chuỗi chữ sập, `noexcept` ném là `terminate`, tên tham số che thành viên (`-Wshadow`) để lại giá trị chưa khởi tạo.
5. Công cụ theo triệu chứng: `-Wall -Wextra -Wshadow` trước, ASan + UBSan khi chạy, mã 134 là `abort` và 139 là `SEGV`; chạy đúng hay sanitizer sạch không chứng minh đúng, vì UB đổi theo `-O` và nhiều lỗi (mục 9, 10, 15) công cụ không thấy.
