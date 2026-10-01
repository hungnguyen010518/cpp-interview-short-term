# Bài 2 — RAII và smart pointer

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích được RAII bằng ví dụ đi mượn sách ở thư viện.
    - Chọn đúng `unique_ptr`, `shared_ptr` hay `weak_ptr` cho từng tình huống.
    - Nhận ra và phá được vòng tròn `shared_ptr` giữ lẫn nhau.

## 🧠 Câu chuyện mở đầu

Bạn vào thư viện để mượn sách.

Thư viện có một luật rất tiện: *mượn khi bước vào, tự động trả khi bước ra khỏi cửa*. Bạn không cần nhớ phải trả. Cửa tự lo giúp bạn. Luật này chính là **RAII**: xin tài nguyên khi đối tượng được tạo, tự trả khi đối tượng bị hủy.

Ở [Bài 1](01-stack-heap-con-tro.md), bạn đã thấy kho đồ (heap) bắt bạn tự nhớ trả. Quên trả thì bị rò rỉ. RAII giúp bạn khỏi phải nhớ.

Từ luật đó, ta có ba "thẻ" để giữ đồ trong kho:

- Chiếc **chìa khóa duy nhất** là **`unique_ptr`**. Chỉ một người cầm. Muốn đưa người khác thì phải trao tay.
- **Nhiều bạn cùng giữ thẻ** là **`shared_ptr`**. Người cuối cùng buông thẻ thì kho mới đóng. Có một bộ đếm số người đang giữ thẻ.
- **Người đứng nhìn qua cửa kính** là **`weak_ptr`**. Nhìn được, nhưng không giữ thẻ. Nên người đó không ngăn được kho đóng.

## 📖 Giải thích

**RAII** (Resource Acquisition Is Initialization) nghĩa là gắn tài nguyên với vòng đời của đối tượng.

- Tài nguyên có thể là bộ nhớ, file hay khóa (lock).
- Hàm khởi tạo xin tài nguyên.
- **Hàm hủy (destructor)** tự chạy khi đối tượng ra khỏi phạm vi, kể cả khi có ngoại lệ (exception).
- Thư viện chuẩn có sẵn nhiều ví dụ: `std::lock_guard` (tự mở khóa), `std::ifstream` (tự đóng file), `std::vector` (tự giải phóng mảng).

**Smart pointer (con trỏ thông minh)** là con trỏ biết tự dọn. Nó dùng RAII để `delete` đúng lúc. Các smart pointer nằm trong `<memory>`.

**`unique_ptr`** có một chủ duy nhất.

- Không copy được.
- Muốn chuyển quyền sở hữu thì dùng `std::move`.
- Gần như không tốn thêm chi phí so với con trỏ thô.
- Đây là lựa chọn mặc định.

**`shared_ptr`** cho nhiều chủ cùng giữ.

- Có **bộ đếm tham chiếu (reference count)** đếm số chủ.
- Thêm một chủ thì đếm tăng, bớt một chủ thì đếm giảm.
- Đếm về 0 thì đối tượng bị hủy.

**`weak_ptr`** trỏ tới đối tượng của `shared_ptr` mà không tăng bộ đếm.

- Dùng để phá vòng tròn giữ nhau, làm cache (chỗ cất tạm đồ hay dùng cho nhanh), làm observer (người theo dõi một đối tượng khác).
- `expired()` cho biết đối tượng đã bị hủy chưa.
- `lock()` trả về một `shared_ptr` nếu đối tượng còn sống, hoặc `nullptr` nếu đã chết.

Hãy tạo bằng `std::make_unique` và `std::make_shared` (C++14 trở lên cho `make_unique`). Tránh `new` trần.

## 💻 Ví dụ code

Ví dụ 1: RAII trong thư viện. Hàm hủy tự chạy khi ra khỏi `main`.

```cpp
#include <iostream>

class TheMuon {
public:
    TheMuon()  { std::cout << "Muon sach\n"; }
    ~TheMuon() { std::cout << "Tra sach\n"; }
};

int main() {
    TheMuon the;
    std::cout << "Dang doc\n";
    return 0;   // ra khỏi main -> hàm hủy tự chạy
}
```

Kết quả in ra, mỗi dòng một câu: `Muon sach`, `Dang doc`, `Tra sach`.

Ví dụ 2: `unique_ptr` và chuyển quyền sở hữu.

```cpp
#include <iostream>
#include <memory>
#include <utility>

struct Hop { int so = 42; };

int main() {
    auto a = std::make_unique<Hop>();
    std::cout << a->so << "\n";
    auto b = std::move(a);                  // chuyển quyền sở hữu
    std::cout << (a == nullptr) << "\n";    // 1: a đã trao tay
    return 0;
}
```

Kết quả in ra: `42` rồi `1`.

Ví dụ 3: `shared_ptr`, bộ đếm và `weak_ptr`.

```cpp
#include <iostream>
#include <memory>

int main() {
    auto s1 = std::make_shared<int>(5);
    std::weak_ptr<int> w = s1;
    {
        auto s2 = s1;
        std::cout << s1.use_count() << "\n";   // 2
    }
    std::cout << s1.use_count() << "\n";       // 1
    s1.reset();
    std::cout << w.expired() << "\n";          // 1
    return 0;
}
```

Kết quả in ra: `2`, `1`, `1`. Mỗi số một dòng.

Ví dụ 4: vòng tròn `shared_ptr`. Chương trình này **rò rỉ âm thầm**.

```cpp
#include <memory>

struct B;
struct A { std::shared_ptr<B> b; };
struct B { std::shared_ptr<A> a; };   // sửa: đổi thành std::weak_ptr<A>

int main() {
    auto a = std::make_shared<A>();
    auto b = std::make_shared<B>();
    a->b = b;
    b->a = a;   // hai bên giữ nhau -> đếm không bao giờ về 0 -> rò rỉ
    return 0;
}
```

Chương trình không in gì và vẫn thoát với mã 0, nên bạn không thấy lỗi. Nhưng nó rò rỉ.

Vì sao? `A` giữ thẻ của `B`, và `B` giữ thẻ của `A`. Khi `main` kết thúc, hai biến `a` và `b` buông thẻ của mình. Nhưng mỗi đối tượng vẫn còn một thẻ do đối tượng kia giữ. Bộ đếm của cả hai chỉ giảm từ 2 xuống 1, không bao giờ về 0. Không ai buông trước, nên không ai bị hủy.

Cách sửa: đổi một phía thành `std::weak_ptr`, ví dụ `std::weak_ptr<A> a;` trong `B`. Người đứng nhìn qua cửa kính không giữ thẻ, nên bộ đếm của `A` chỉ còn 1. Khi `a` buông thẻ, đếm về 0 và `A` được hủy. Sau đó `B` cũng mất chủ cuối và được hủy theo.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "RAII là gì? Cho ví dụ trong thư viện chuẩn."
    Gắn vòng đời của tài nguyên với vòng đời của đối tượng: tài nguyên được xin trong hàm khởi tạo và được trả trong hàm hủy, kể cả khi có ngoại lệ.

    Ví dụ: `std::lock_guard`, `std::unique_ptr`, `std::ifstream`.

??? question "`unique_ptr` và `shared_ptr` khác nhau thế nào? Khi nào dùng cái nào?"
    `unique_ptr` là sở hữu độc quyền, không copy được, chỉ chuyển quyền bằng `std::move`. `shared_ptr` là sở hữu chia sẻ, có bộ đếm tham chiếu.

    Mặc định dùng `unique_ptr`. Chỉ dùng `shared_ptr` khi thật sự cần nhiều chủ.

??? question "`shared_ptr` có thread-safe không?"
    Bộ đếm tham chiếu được cập nhật an toàn giữa các luồng (dùng thao tác atomic).

    Nhưng đối tượng bên trong thì không tự an toàn. Việc sửa chính một biến `shared_ptr` từ nhiều luồng cùng lúc cũng không tự an toàn.

??? question "Khi nào cần `weak_ptr`?"
    Khi cần phá vòng tham chiếu, làm cache, hoặc làm observer mà không muốn kéo dài vòng đời của đối tượng.

??? question "Chi phí của `shared_ptr` là gì?"
    Phải có thêm khối điều khiển (control block) chứa bộ đếm, và các thao tác atomic khi cập nhật bộ đếm.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tạo hai `shared_ptr` từ cùng một con trỏ thô"
    Mỗi `shared_ptr` tạo từ con trỏ thô sẽ có bộ đếm riêng. Hai bộ đếm không biết nhau, nên đối tượng bị giải phóng hai lần. Đây là hành vi không xác định.

    ```cpp
    // bo-qua-kiem-tra
    #include <memory>
    int main() {
        int* raw = new int(1);
        std::shared_ptr<int> a(raw);
        std::shared_ptr<int> b(raw);   // hai bộ đếm riêng -> delete hai lần
    }
    ```

    Hãy dùng `std::make_shared`, hoặc copy từ một `shared_ptr` có sẵn.

!!! warning "Lỗi 2: Dùng `shared_ptr` ở mọi nơi 'cho chắc'"
    Làm vậy tốn thêm chi phí và làm rối quyền sở hữu: không ai biết ai là chủ thật sự. Hãy bắt đầu bằng `unique_ptr`.

!!! warning "Lỗi 3: Lấy `.get()` ra rồi tự `delete`"
    `.get()` chỉ cho bạn mượn con trỏ thô để xem. Nếu bạn tự `delete`, smart pointer vẫn sẽ hủy thêm lần nữa khi ra khỏi phạm vi. Đối tượng bị hủy hai lần.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="02" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Ý tưởng cốt lõi của RAII là gì?

- Xin tài nguyên khi tạo đối tượng và tự trả trong hàm hủy khi đối tượng hết vòng đời
- Luôn dùng `new` và `delete`
- Bỏ kiểm tra để chạy nhanh hơn
- Đặt mọi biến lên heap

<p class="giai-thich" markdown>Như thư viện: mượn khi vào, tự trả khi ra. Nhờ vậy không quên trả, kể cả khi có ngoại lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** `unique_ptr` khác `shared_ptr` ở điểm nào?

- `unique_ptr` chỉ có một chủ duy nhất, `shared_ptr` cho nhiều chủ cùng giữ
- `unique_ptr` chạy chậm hơn
- `shared_ptr` không giải phóng bộ nhớ
- Hai loại giống hệt

<p class="giai-thich" markdown>Một chìa khóa duy nhất so với nhiều bạn cùng giữ thẻ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Với `unique_ptr a`, sau `auto b = std::move(a);` thì `a` là gì?

- Vẫn trỏ vào đối tượng cũ
- Bằng `nullptr` vì quyền sở hữu đã chuyển sang `b`
- Lỗi biên dịch
- Bị xóa khỏi bộ nhớ cùng đối tượng

<p class="giai-thich" markdown>Chìa khóa đã trao tay, nên `a` không còn giữ gì.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Hai đối tượng giữ `shared_ptr` lẫn nhau theo vòng tròn gây ra điều gì?

- Bộ đếm không bao giờ về 0 nên bộ nhớ không được giải phóng (rò rỉ)
- Lỗi biên dịch
- Tự động thành `weak_ptr`
- Chương trình chạy nhanh hơn

<p class="giai-thich" markdown>Mỗi bên đều giữ thẻ của bên kia nên không ai buông trước.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** `weak_ptr` dùng để làm gì?

- Trỏ tới đối tượng mà không tăng bộ đếm, nên phá được vòng tròn giữ nhau
- Giữ đối tượng sống mãi mãi
- Thay thế `unique_ptr`
- Chỉ dùng cho mảng

<p class="giai-thich" markdown>Người nhìn qua cửa kính: thấy được, nhưng không giữ kho mở.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Nên ưu tiên cách nào để tạo `shared_ptr`?

- `std::shared_ptr<T>(new T)`
- `std::make_shared<T>()`
- `new T` rồi gán
- `malloc`

<p class="giai-thich" markdown>`make_shared` cấp phát một lần cho cả đối tượng lẫn bộ đếm nên gọn hơn. Trước C++17, nó còn tránh được rò rỉ khi dùng chung với lời gọi khác.</p>
</div>

</div>

## 🔑 Tóm tắt

1. RAII: mượn trong hàm khởi tạo, tự trả trong hàm hủy.
2. `unique_ptr`: một chìa khóa duy nhất, trao tay bằng `std::move`.
3. `shared_ptr`: nhiều người cùng giữ, người cuối buông thì mới dọn.
4. `weak_ptr`: chỉ nhìn, không giữ, dùng để phá vòng tròn.
5. Mặc định dùng `unique_ptr` và `make_unique`/`make_shared`; tránh `new`/`delete` trần.
