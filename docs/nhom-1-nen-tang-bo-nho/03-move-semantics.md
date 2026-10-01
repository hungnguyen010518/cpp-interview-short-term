# Bài 3 — Move semantics, rule of 0/3/5

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt được sao chép và di chuyển bằng ví dụ quyển vở.
    - Hiểu `std::move` thực sự làm gì.
    - Biết rule of 0/3/5 và viết được move constructor.

## 🧠 Câu chuyện mở đầu

Bạn có một quyển vở dày 200 trang. Bạn của bạn cần nó.

Cách 1: *photo cả quyển*. Đó là **sao chép (copy)**. Tốn giấy, tốn thời gian.

Cách 2: *đưa luôn quyển vở cho bạn*. Đó là **di chuyển (move)**. Rất nhanh. Nhưng bạn chỉ còn cái bìa rỗng. Ai đưa xong thì đừng mong chép bài từ quyển đó nữa.

Có hai loại "vật" trong C++.

Vật "có tên, ở lâu", như quyển vở của bạn, gọi là **lvalue**.

Vật "tạm thời, sắp biến mất", như tờ giấy nháp vừa viết, gọi là **rvalue**. Lấy ruột của nó đi cũng chẳng ai tiếc.

## 📖 Giải thích

**lvalue và rvalue.**

- lvalue có tên và có địa chỉ. Nó vẫn còn sau khi câu lệnh chạy xong.
- rvalue là giá trị tạm, ví dụ kết quả của `a + b` hay `2`.
- Tham chiếu tới rvalue viết là `T&&` (tham chiếu rvalue, rvalue reference).

**`std::move` không di chuyển gì cả.**

- Nó chỉ ép `x` thành rvalue. Như dán nhãn "cho phép lấy ruột".
- Việc di chuyển thật sự do **move constructor** (hàm tạo di chuyển) hoặc **move assignment** (toán tử gán di chuyển) làm.
- Bạn đã gặp `std::move` với `unique_ptr` ở [Bài 2](02-raii-smart-pointer.md).

**Sau khi move, nguồn ra sao?**

- Nguồn ở trạng thái **hợp lệ nhưng không xác định (valid but unspecified)**.
- Hợp lệ nghĩa là hủy nó hay gán giá trị mới cho nó đều an toàn.
- Không xác định nghĩa là bạn đừng đoán bên trong có gì. Ví dụ `std::string` đã bị move thì độ dài của nó không được đảm bảo.
- Vì vậy sau khi move, chỉ nên hủy hoặc gán lại.

**Move constructor nên có `noexcept`.**

- `noexcept` là lời hứa "hàm này không ném ngoại lệ".
- Khi `std::vector` hết chỗ, nó cấp vùng nhớ mới và chuyển các phần tử sang đó. Nó dùng `std::move_if_noexcept`.
- Nếu move không hứa `noexcept` và có thể ném ngoại lệ, `vector` quay về dùng copy. Copy chậm hơn, nhưng nếu lỡ lỗi giữa chừng thì dữ liệu cũ vẫn còn nguyên.

**Rule of 3, 5, 0.** Đây là các quy tắc về "hàm đặc biệt" của class.

- **Rule of 3** (từ C++98): tự viết một trong ba hàm (destructor, copy constructor, copy assignment) thì thường phải viết cả ba.
- **Rule of 5** (từ C++11): thêm move constructor và move assignment, thành năm hàm.
- **Rule of 0**: dùng các thành phần tự quản lý tài nguyên (`vector`, `unique_ptr`…). Khi đó bạn không phải viết hàm nào trong số năm hàm ấy. Hãy ưu tiên cách này.

**Trả về đối tượng cục bộ theo giá trị.**

- Hãy viết `return v;`.
- Trình biên dịch có thể dùng **copy elision (bỏ qua bước copy)**, thường gọi là RVO. Nếu không bỏ qua được, nó sẽ dùng move.
- Từ C++17, khi trả về một giá trị tạm (như `return T(...);`), việc bỏ qua copy là bắt buộc.
- Đừng viết `return std::move(v);`. Nó có thể cản tối ưu này.

**Perfect forwarding (chuyển tiếp hoàn hảo).**

- Trong template, `T&&` là **tham chiếu chuyển tiếp (forwarding reference)**: nhận được cả lvalue lẫn rvalue.
- `std::forward<T>(x)` giữ nguyên x là lvalue hay rvalue khi đưa tiếp cho hàm khác.

## 💻 Ví dụ code

Ví dụ 1: move một `std::string`, rồi move vào `vector`. Cố ý không in `a.size()`, vì sau khi move giá trị của `a` không được đảm bảo.

```cpp
#include <iostream>
#include <string>
#include <utility>
#include <vector>

int main() {
    std::string a(1000, 'x');
    std::string b = std::move(a);       // lấy luôn bộ nhớ của a
    std::cout << b.size() << "\n";      // 1000
    std::vector<std::string> v;
    v.push_back(std::move(b));
    std::cout << v[0].size() << "\n";   // 1000
    return 0;
}
```

Kết quả in ra: `1000` rồi `1000`.

Ví dụ 2: class `Mang` giữ con trỏ thô, tự viết đủ cả năm hàm đặc biệt (Rule of 5). Nhớ lại `new[]` và `delete[]` từ [Bài 1](01-stack-heap-con-tro.md).

```cpp
#include <cstddef>
#include <iostream>
#include <utility>

class Mang {
public:
    explicit Mang(std::size_t n) : n_(n), d_(new int[n]) {}
    ~Mang() { delete[] d_; }

    Mang(const Mang& o) : n_(o.n_), d_(new int[o.n_]) {
        for (std::size_t i = 0; i < n_; ++i) d_[i] = o.d_[i];
    }
    Mang& operator=(const Mang& o) {
        if (this != &o) {
            Mang tam(o);               // copy-and-swap
            std::swap(n_, tam.n_);
            std::swap(d_, tam.d_);
        }
        return *this;
    }

    Mang(Mang&& o) noexcept : n_(o.n_), d_(o.d_) {
        o.n_ = 0;
        o.d_ = nullptr;                // nguồn về trạng thái an toàn
    }
    Mang& operator=(Mang&& o) noexcept {
        if (this != &o) {
            delete[] d_;
            n_ = o.n_;
            d_ = o.d_;
            o.n_ = 0;
            o.d_ = nullptr;
        }
        return *this;
    }

    std::size_t size() const { return n_; }

private:
    std::size_t n_;
    int* d_;
};

int main() {
    Mang a(100);
    Mang b = std::move(a);
    std::cout << b.size() << " " << a.size() << "\n";   // 100 0
    return 0;
}
```

Kết quả in ra: `100 0`. Ở đây `a.size()` bằng 0 vì chính class này đặt nguồn về 0. Đó là lựa chọn của người viết class, không phải quy tắc chung.

Ví dụ 3: Rule of 0. Cùng class đó nhưng dùng `vector` giữ dữ liệu, nên không phải viết hàm đặc biệt nào.

```cpp
#include <cstddef>
#include <iostream>
#include <utility>
#include <vector>

class Mang {
public:
    explicit Mang(std::size_t n) : d_(n) {}
    std::size_t size() const { return d_.size(); }
private:
    std::vector<int> d_;   // vector lo hết, không cần viết hàm đặc biệt nào (Rule of 0)
};

int main() {
    Mang a(100);
    Mang b = std::move(a);
    std::cout << b.size() << "\n";   // 100
    return 0;
}
```

Kết quả in ra: `100`.

Ví dụ 4: perfect forwarding giữ nguyên lvalue hay rvalue.

```cpp
#include <iostream>
#include <utility>

void in(int&)  { std::cout << "lvalue\n"; }
void in(int&&) { std::cout << "rvalue\n"; }

template <typename T>
void chuyenTiep(T&& x) { in(std::forward<T>(x)); }

int main() {
    int a = 1;
    chuyenTiep(a);   // lvalue
    chuyenTiep(2);   // rvalue
    return 0;
}
```

Kết quả in ra: `lvalue` rồi `rvalue`.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "lvalue và rvalue khác nhau thế nào?"
    lvalue có danh tính (có tên, có địa chỉ) và còn tồn tại sau câu lệnh. rvalue là giá trị tạm, sắp hết vòng đời.

??? question "`std::move` làm gì?"
    Chỉ là phép ép kiểu sang rvalue reference. Nó không tự di chuyển dữ liệu. Việc di chuyển do move constructor hoặc move assignment thực hiện.

??? question "Viết move constructor cho class giữ con trỏ thô."
    Lấy con trỏ của nguồn, đặt con trỏ nguồn về `nullptr`, và đánh dấu `noexcept`. Xem class `Mang` ở ví dụ 2.

??? question "Vì sao move constructor nên `noexcept`?"
    `std::vector` dùng `std::move_if_noexcept` khi tăng dung lượng. Nếu move có thể ném ngoại lệ (và type còn copy được), `vector` quay về copy để giữ an toàn ngoại lệ.

??? question "Rule of 3/5/0?"
    Rule of 3: tự viết một trong destructor, copy constructor, copy assignment thì thường phải viết cả ba. Rule of 5 thêm move constructor và move assignment. Rule of 0: dùng thành phần tự quản lý tài nguyên để không phải viết hàm nào. Ưu tiên Rule of 0.

??? question "Perfect forwarding là gì?"
    Chuyển tiếp tham số mà giữ nguyên là lvalue hay rvalue, bằng `T&&` (forwarding reference) và `std::forward<T>`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Dùng đối tượng sau khi đã move và đoán nội dung của nó"
    Nguồn chỉ ở trạng thái "hợp lệ nhưng không xác định". Chỉ nên hủy nó hoặc gán giá trị mới. Đừng đọc rồi đoán bên trong còn gì.

!!! warning "Lỗi 2: Viết `return std::move(bienCucBo);`"
    Viết vậy có thể cản copy elision/RVO, làm code chậm hơn. Cứ viết `return bienCucBo;`.

!!! warning "Lỗi 3: Viết move constructor nhưng quên đặt nguồn về `nullptr`"
    Khi đó hai đối tượng giữ cùng một con trỏ. Cả hai cùng `delete` một vùng nhớ, gọi là **double free**, và đó là hành vi không xác định. Luôn đặt con trỏ của nguồn về `nullptr`.

    ```cpp
    // bo-qua-kiem-tra
    Mang(Mang&& o) noexcept : n_(o.n_), d_(o.d_) {
        // thiếu: o.d_ = nullptr;  → a và b cùng delete[] một chỗ
    }
    ```

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="03" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** `std::move(x)` thực sự làm gì?

- Di chuyển dữ liệu của x sang chỗ khác ngay
- Chỉ ép x thành rvalue để cho phép "lấy ruột"; việc di chuyển do move constructor làm
- Xóa x
- Sao chép sâu x

<p class="giai-thich" markdown>Tên gọi dễ gây hiểu lầm: `std::move` chỉ là cái ép kiểu.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Sau `std::string b = std::move(a);`, điều nào an toàn với `a`?

- Đọc `a.size()` và chắc chắn bằng 0
- Gán giá trị mới cho `a` hoặc hủy `a`; không nên đoán nội dung của `a`
- Dùng `a` như chưa có gì xảy ra
- Không được gán lại `a` nữa

<p class="giai-thich" markdown>Nguồn ở trạng thái "hợp lệ nhưng không xác định". Gán mới và hủy thì luôn an toàn.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Vì sao move constructor nên đánh dấu `noexcept`?

- Để code ngắn hơn
- Để `std::vector` khi tăng dung lượng dám dùng move thay vì copy
- Để tắt kiểm tra lỗi
- Cú pháp bắt buộc

<p class="giai-thich" markdown>Nếu move có thể ném ngoại lệ, `vector` quay về copy để không làm hỏng dữ liệu.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Rule of Zero nghĩa là gì?

- Không bao giờ viết class
- Dùng các thành phần tự quản lý tài nguyên (`vector`, `unique_ptr`…) để khỏi tự viết destructor/copy/move
- Luôn viết cả 5 hàm đặc biệt
- Xóa mọi destructor

<p class="giai-thich" markdown>Để thư viện chuẩn dọn dẹp giùm, bớt code, bớt lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Rule of Five nói gì?

- Nếu tự viết một trong năm hàm (destructor, copy ctor, copy assign, move ctor, move assign) thì thường phải xem xét viết cả năm
- Mỗi class tối đa 5 hàm
- Cần 5 thành viên dữ liệu
- Chỉ áp dụng cho template

<p class="giai-thich" markdown>Cần quản lý tài nguyên bằng tay thì phải chăm cả năm hàm.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Hàm trả về biến cục bộ theo giá trị (`return v;`) nên viết thế nào?

- `return std::move(v);`
- `return v;` để trình biên dịch dùng copy elision/RVO hoặc move
- Bắt buộc `return new T(v);`
- Luôn trả bằng tham chiếu

<p class="giai-thich" markdown>`return std::move(v);` có thể cản tối ưu RVO.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Copy là photo cả quyển vở; move là đưa luôn quyển vở.
2. `std::move` chỉ là phép ép kiểu sang rvalue, chưa di chuyển gì.
3. Sau khi move, chỉ nên hủy hoặc gán lại đối tượng nguồn.
4. Move constructor nên `noexcept` và đặt nguồn về trạng thái an toàn.
5. Ưu tiên Rule of Zero; nếu tự quản lý tài nguyên thì chăm đủ Rule of Five.
