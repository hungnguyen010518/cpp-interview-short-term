# Bài 1 — Stack, heap, con trỏ, tham chiếu, const

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích được stack và heap khác nhau thế nào bằng hình ảnh cái bàn học và kho đồ.
    - Phân biệt được con trỏ và tham chiếu.
    - Đọc đúng `const int*` và `int* const`.

## 🧠 Câu chuyện mở đầu

Bạn đang học ở lớp.

*Cái bàn học* của bạn khá nhỏ. Bạn để đồ lên đó và lấy ra rất nhanh. Hết giờ, cô giáo tự dọn sạch bàn cho bạn. Cái bàn đó là **stack (ngăn xếp)**.

*Kho đồ của trường* thì rộng. Đồ to cỡ nào cũng để vừa. Nhưng bạn phải xin chìa khóa, ghi vào sổ, và **tự nhớ trả**. Quên trả thì kho đầy dần. Cái kho đó là **heap (vùng nhớ cấp phát động)**.

Tờ giấy ghi "đồ của em ở phòng 12" là **con trỏ (pointer)**. Tờ giấy không phải là đồ. Nó chỉ cho bạn biết đồ ở đâu.

Biệt danh "Tí" của bạn Nguyễn Văn An là **tham chiếu (reference)**. Gọi "Tí" hay gọi "An" thì vẫn cùng một người.

Nhãn dán "Chỉ được xem, không được sửa" là **const (hằng)**.

## 📖 Giải thích

**Stack** chứa các biến cục bộ, tức là biến khai báo trong hàm.

- Ra khỏi phạm vi (khối `{}` chứa nó) là biến tự được giải phóng.
- Rất nhanh.
- Dung lượng nhỏ, thường vài MB.

**Heap** là nơi bạn tự xin và tự trả bộ nhớ.

- Xin bằng `new`, trả bằng `delete`.
- Vùng nhớ tồn tại cho đến khi bạn trả.
- Chậm hơn stack, nhưng rộng hơn nhiều.

**Con trỏ** là biến lưu một địa chỉ.

- Có thể bằng `nullptr`, nghĩa là "chưa trỏ vào đâu".
- Có thể đổi sang trỏ chỗ khác.
- Muốn lấy giá trị ở địa chỉ đó thì viết `*p`.

**Tham chiếu** là biệt danh của một đối tượng có sẵn.

- Phải gán ngay khi khai báo.
- Không bao giờ null.
- Không đổi sang đối tượng khác được.
- Dùng như chính đối tượng, không cần `*`.

**const** đi với con trỏ dễ làm bạn rối. Có một mẹo: đọc **từ phải sang trái**.

- `const int* p` đọc là "p là con trỏ tới int hằng". Bạn không sửa được giá trị qua `p`, nhưng `p` đổi chỗ trỏ được.
- `int* const p` đọc là "p là con trỏ hằng tới int". Bạn sửa được giá trị, nhưng `p` không đổi chỗ trỏ được.

Khi truyền một đối tượng lớn vào hàm, hãy dùng `const T&`. Hàm không phải sao chép đối tượng, mà vẫn không sửa được nó.

## 💻 Ví dụ code

Ví dụ 1: một biến trên stack và một biến trên heap.

```cpp
#include <iostream>

int main() {
    int ban = 5;                 // nằm trên stack (cái bàn học)
    int* kho = new int(7);       // nằm trên heap (kho đồ)
    std::cout << ban << " " << *kho << "\n";
    delete kho;                  // trả đồ về kho
    return 0;
}
```

Kết quả in ra: `5 7`.

Ví dụ 2: con trỏ, tham chiếu và `const&`.

```cpp
#include <iostream>

void tang(int& x) { x += 1; }                       // tham chiếu: sửa thẳng bản gốc
void chiXem(const int& x) { std::cout << x << "\n"; }

int main() {
    int a = 10;
    int* p = &a;      // p giữ địa chỉ của a
    *p = 20;          // đi theo địa chỉ, sửa a
    int& b = a;       // b là biệt danh của a
    b = 30;
    tang(a);
    chiXem(a);        // in 31
    return 0;
}
```

Kết quả in ra: `31`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Stack khác heap thế nào?"
    Khác về vòng đời: biến trên stack tự giải phóng khi hết phạm vi, vùng nhớ trên heap tồn tại đến khi được giải phóng.

    Khác về tốc độ: stack nhanh hơn. Khác về kích thước: stack nhỏ, heap lớn.

    Khác về người quản lý: stack do trình biên dịch lo, heap do lập trình viên lo.

??? question "Con trỏ khác tham chiếu thế nào?"
    Con trỏ có thể null và có thể đổi chỗ trỏ. Muốn dùng giá trị phải giải tham chiếu bằng `*p`.

    Tham chiếu phải gắn với đối tượng ngay khi khai báo, không null, không đổi đối tượng, và dùng như chính đối tượng đó.

??? question "Phân biệt `const int* p`, `int* const p` và `const int* const p`."
    Đọc từ phải sang trái.

    `const int* p`: con trỏ tới int hằng. `int* const p`: con trỏ hằng tới int. `const int* const p`: con trỏ hằng tới int hằng.

??? question "Vì sao truyền đối tượng lớn bằng `const T&`?"
    Tránh chi phí sao chép đối tượng, đồng thời cam kết hàm không sửa đối tượng.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Trả về con trỏ hoặc tham chiếu tới biến cục bộ"
    Biến cục bộ bị dọn khi hàm kết thúc. Địa chỉ vẫn còn, nhưng chỗ đó không còn thuộc về bạn. Con trỏ như vậy gọi là **con trỏ treo (dangling pointer)**.

    ```cpp
    // bo-qua-kiem-tra
    int* hamLoi() {
        int x = 5;
        return &x;   // x bị dọn khi hàm kết thúc → địa chỉ trỏ vào chỗ trống
    }
    ```

!!! warning "Lỗi 2: `new` mà quên `delete`"
    Heap không tự dọn. Quên trả thì vùng nhớ bị chiếm cho đến khi chương trình kết thúc (lúc đó hệ điều hành mới thu lại). Đó là **rò rỉ bộ nhớ (memory leak)**. Bài 5 sẽ nói kỹ hơn.

!!! warning "Lỗi 3: Dùng con trỏ chưa gán giá trị hoặc đang là `nullptr`"
    Luôn khởi tạo con trỏ khi khai báo. Trước khi dùng `*p`, hãy kiểm tra `p` có khác `nullptr` không.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="01" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Biến `int x = 5;` khai báo trong một hàm thường nằm ở đâu?

- Heap, vì `int` nào cũng phải xin bộ nhớ bằng `new`
- Stack, và tự được dọn khi ra khỏi phạm vi chứa nó
- Vùng dùng chung cho mọi hàm, chỉ dọn khi chương trình tắt

<p class="giai-thich" markdown>Biến cục bộ nằm trên stack và tự được dọn khi ra khỏi phạm vi (khối `{}` chứa nó). Heap chỉ dùng khi bạn tự xin bằng `new`.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Chuyện gì xảy ra nếu `new` một vùng nhớ rồi không bao giờ `delete`?

- Vùng nhớ tự được trả khi hàm chứa nó kết thúc
- Chương trình không biên dịch được vì thiếu `delete`
- Vùng nhớ vẫn bị giữ cho đến khi chương trình kết thúc: rò rỉ bộ nhớ
- Con trỏ tự thành `nullptr` và vùng nhớ được thu hồi

<p class="giai-thich" markdown>Heap không tự dọn. Quên trả thì vùng nhớ bị giữ cho đến khi chương trình kết thúc (lúc đó hệ điều hành mới thu lại). Đó là rò rỉ bộ nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Điểm khác chính giữa tham chiếu và con trỏ là gì?

- Tham chiếu có thể null và đổi sang đối tượng khác, con trỏ thì không
- Con trỏ phải gán ngay khi khai báo, còn tham chiếu thì để trống được
- Tham chiếu lưu địa chỉ trên heap, còn con trỏ lưu địa chỉ trên stack
- Tham chiếu gắn một lần với đối tượng và không null; con trỏ có thể null và đổi chỗ trỏ

<p class="giai-thich" markdown>Con trỏ mới có thể null và đổi chỗ trỏ. Tham chiếu là biệt danh gắn một lần, phải gán ngay khi khai báo.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** `const int* p` có nghĩa là gì?

- Không sửa được giá trị int mà `p` trỏ tới (qua `p`), nhưng `p` đổi chỗ trỏ được
- Không đổi được `p` sang trỏ chỗ khác, nhưng sửa được giá trị int đó
- `p` luôn bằng `nullptr` nên không dùng để đọc được gì
- Cả `p` lẫn giá trị int đều không thay đổi được

<p class="giai-thich" markdown>Chữ `const` đứng trước `int` nên cái `int` là hằng. Muốn con trỏ không đổi chỗ thì viết `int* const`, muốn cả hai đều hằng thì viết `const int* const`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Hàm trả về địa chỉ của một biến cục bộ gây ra vấn đề gì?

- Biến tự được chuyển lên heap nên vẫn dùng an toàn
- Con trỏ trỏ vào vùng đã bị dọn (dangling); dùng nó là UB, có thể chạy đúng hoặc sập
- Trình biên dịch luôn báo lỗi nên chương trình không chạy được
- Chỉ có vấn đề khi hàm đó bị gọi nhiều hơn một lần

<p class="giai-thich" markdown>Biến cục bộ mất khi hàm kết thúc; địa chỉ còn đó nhưng chỗ đó không còn thuộc về bạn. Dùng con trỏ treo là hành vi không xác định (UB): chuẩn C++ không bảo đảm kết quả, nó có thể trông như chạy đúng hoặc có thể sập.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 6.** Vì sao nên truyền `std::string` lớn bằng `const std::string&`?

- Để chuỗi được đặt trên heap thay vì stack
- Để hàm sửa được chuỗi gốc mà không phải sao chép
- Để tránh sao chép cả chuỗi mà hàm vẫn không sửa được nó
- Để chương trình biên dịch nhanh hơn nhờ code ngắn hơn

<p class="giai-thich" markdown>Truyền tham chiếu không copy cả chuỗi; `const` cam kết không sửa.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Stack là bàn học: nhanh, nhỏ, tự dọn.
2. Heap là kho đồ: rộng, phải tự xin (`new`) và tự trả (`delete`).
3. Con trỏ là tờ giấy ghi địa chỉ, có thể null và đổi chỗ trỏ.
4. Tham chiếu là biệt danh: gắn một lần, không null, không đổi.
5. Truyền đối tượng lớn bằng `const T&` để không copy mà vẫn an toàn.
