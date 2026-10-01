# Bảng thuật ngữ

Thuật ngữ được thêm vào đây ở cuối mỗi bài.

| Thuật ngữ | Nghĩa dễ hiểu | Bài |
|---|---|---|
| byte | 1 ngăn nhớ, gồm 8 bit, có 256 giá trị khác nhau | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| bit | Một công tắc chỉ có hai trạng thái, 0 hoặc 1 | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| địa chỉ (address) | Số thứ tự của một byte trong bộ nhớ, thường viết dạng hệ 16 như `0x7ffc…` | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| biến (variable) | Một hay vài byte liền nhau có tên, kiểu, giá trị và địa chỉ | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| kiểu (type) | Cho biết biến chiếm bao nhiêu byte và các byte đó được hiểu thế nào | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| sizeof | Toán tử cho biết số byte của một kiểu hoặc một biến, kết quả kiểu `std::size_t` | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| toán tử (operator) | Ký hiệu hay từ khóa tính trên dữ liệu, như `+`, `<<`, `&`, `sizeof` | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| biên dịch (compile) | Dịch mã nguồn thành file chạy được, ví dụ bằng `g++` | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| #include | Chỉ thị nạp bộ công cụ của thư viện vào chương trình, giống `import` của Go | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| main | Hàm đầu tiên được chạy khi chương trình bắt đầu | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| std::cout | Cổng ra để in chữ ra màn hình; `std::` là họ thư viện chuẩn | [Bài 01](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) |
| stack (ngăn xếp) | Vùng nhớ nhỏ, nhanh, chứa biến cục bộ; mỗi lần gọi hàm có một khung, tự dọn khi ra khỏi hàm | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| stack frame (khung gọi hàm) | Mảnh stack riêng của một lần gọi hàm, chứa tham số và biến cục bộ, bị gỡ khi hàm kết thúc | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| heap | Vùng nhớ rộng, phải tự xin bằng `new` và tự trả bằng `delete` | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| vùng tĩnh (static storage) | Vùng chứa biến global, `static` cục bộ và thành viên `static`; sống suốt chương trình | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| vòng đời (lifetime) | Khoảng thời gian từ lúc đối tượng ra đời đến lúc nó chết | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| phạm vi (scope) | Đoạn code mà trong đó một tên còn dùng được, ví dụ từ chỗ khai báo đến `}` của khối chứa nó | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| hàm tạo (constructor) | Hàm trùng tên struct/class, chạy một lần khi đối tượng ra đời | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| hàm hủy (destructor) | Hàm tên `~` rồi tên struct/class, chạy một lần khi đối tượng chết | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| stack overflow (tràn stack) | Stack đầy, thường do đệ quy không dừng hoặc mảng cục bộ quá lớn; chương trình bị dừng đột ngột | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| global (biến toàn cục) | Biến khai báo ngoài mọi hàm; nằm ở vùng tĩnh, hàm tạo thực tế chạy trước `main` (trên trình biên dịch phổ biến), hàm hủy sau `main` | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| storage duration | Thời gian sống của vùng lưu trữ: automatic, static, dynamic hoặc thread | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| static initialization order fiasco | Thứ tự khởi tạo global giữa các file `.cpp` là không xác định nên global này có thể dùng global kia khi chưa sẵn sàng; tránh bằng `static` cục bộ trong hàm | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| escape analysis (phân tích thoát) | Trình biên dịch Go kiểm tra biến có thoát khỏi hàm không và tự đưa lên heap nếu có | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| struct | Kiểu gộp nhiều trường lại; trong C++ còn chứa được hàm, gồm hàm tạo và hàm hủy | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| con trỏ (pointer) | Biến đựng một địa chỉ, thường là địa chỉ của biến khác; `int* p` là con trỏ tới `int` | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| giải tham chiếu (dereference) | Đi theo địa chỉ trong con trỏ để đọc hoặc ghi thứ nằm ở đó, viết `*p` | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| nullptr | Giá trị của con trỏ "chưa trỏ vào đâu" (C++11), có kiểu riêng `std::nullptr_t`; ứng với `nil` của Go | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| null pointer (con trỏ null) | Con trỏ có giá trị `nullptr`; giải tham chiếu nó là hành vi không xác định | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| toán tử `->` | `p->x` là cách viết gọn của `(*p).x`, lấy trường `x` của struct mà con trỏ `p` trỏ tới | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| void* | Con trỏ không nói rõ trỏ tới loại gì, nên không giải tham chiếu thẳng được | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| undefined behavior / UB | Hành vi không xác định: luật chơi bị phá, mọi chuyện đều có thể xảy ra | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| tham số (parameter) | Biến riêng của hàm, nhận giá trị lúc gọi; đối số (argument) là giá trị truyền vào | [Bài 04](nhom-1-nen-tang-bo-nho/04-con-tro-ham.md) |
| truyền theo giá trị (pass by value) | Hàm nhận bản sao của đối số, nên sửa tham số không đổi biến gốc | [Bài 04](nhom-1-nen-tang-bo-nho/04-con-tro-ham.md) |
| swap (đổi chỗ) | Hàm hoán đổi giá trị của hai biến; viết được bằng con trỏ, không viết được bằng truyền theo giá trị | [Bài 04](nhom-1-nen-tang-bo-nho/04-con-tro-ham.md) |
| int** (con trỏ tới con trỏ) | Con trỏ đựng địa chỉ của một con trỏ `int*`; dùng khi hàm cần đổi chính con trỏ của nơi gọi | [Bài 04](nhom-1-nen-tang-bo-nho/04-con-tro-ham.md) |
| mảng (array) | Dãy các biến cùng kiểu nằm liền nhau, ví dụ `int a[4]`; chỉ số bắt đầu từ 0 | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| phần tử (element) | Một biến trong mảng, lấy bằng chỉ số `a[i]` | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| chỉ số (index) | Số thứ tự của phần tử trong mảng, bắt đầu từ 0: `a[0]` là phần tử đầu | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| array decay (mảng thoái hóa thành con trỏ) | Trong biểu thức, tên mảng tự chuyển thành con trỏ tới phần tử đầu; tham số mảng của hàm thực chất là con trỏ nên `sizeof` chỉ cho cỡ con trỏ | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| phép tính con trỏ (pointer arithmetic) | `p + 1` nhích một phần tử (`sizeof(kiểu)` byte); `q - p` đếm số phần tử trong cùng mảng; không cộng hai con trỏ | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| chuỗi kiểu C | Mảng `char` kết thúc bằng ký tự `'\0'`; `const char*` trỏ tới ký tự đầu | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| chuỗi hằng | Chuỗi chữ viết sẵn trong nháy kép như `"An"`; ký tự của nó chỉ đọc, kiểu `const char[N]` | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| '\0' | Ký tự có mã số 0, đánh dấu hết chuỗi kiểu C | [Bài 05](nhom-1-nen-tang-bo-nho/05-mang-phep-tinh-con-tro.md) |
| tham chiếu (reference) | Một tên khác (biệt danh) của biến có sẵn, viết `int& b = a;`; phải gắn lúc khai báo, không rỗng, không gắn lại | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| const (hằng) | Nhãn "chỉ được xem, không được sửa"; trình biên dịch từ chối mọi dòng cố sửa | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| hàm tạo sao chép (copy constructor) | Hàm tạo đặc biệt chạy mỗi khi tạo bản sao của đối tượng cùng kiểu, nhận tham số `const T&`; tự viết để sao chép sâu | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (ý niệm), [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (tự viết) |
| giá trị tạm (temporary) | Giá trị không có tên, chỉ sống trong một câu lệnh, như `5` hay `a + 1` | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| truyền theo tham chiếu (pass by reference) | Hàm nhận tham chiếu: không sao chép, và sửa được bản gốc nếu không có `const` | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| const& | Tham chiếu hằng `const T&`: chỉ xem, không sao chép, nhận được cả giá trị tạm | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| dangling reference (tham chiếu treo) | Tham chiếu trỏ vào chỗ đã bị dọn | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md), [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (lambda) |
| new / delete / delete[] | `new T(...)` xin chỗ ở heap, gọi hàm tạo, trả về địa chỉ; `delete p` gọi hàm hủy rồi trả chỗ; `new T[n]` xin mảng và phải trả bằng `delete[] p`; không được trộn các dạng | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| rò rỉ bộ nhớ (memory leak) | Xin chỗ ở heap mà không bao giờ trả; chương trình vẫn đúng luật (không phải UB) nhưng phí bộ nhớ dần | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| malloc / free | Cặp xin/trả bytes thô của ngôn ngữ C, không gọi hàm tạo/hàm hủy; C++ hiện đại gần như không dùng | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| con trỏ treo (dangling pointer) | Con trỏ còn giữ địa chỉ của chỗ đã bị trả hoặc đã hết hiệu lực | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| ngoại lệ (exception) | Cách C++ báo lỗi bằng cách cắt ngang hàm đang chạy và thoát ra ngoài; `new` hết chỗ ném `std::bad_alloc`; cú pháp `throw`/`try`/`catch` ở [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| use-after-free | Dùng sau khi trả: đọc hay ghi qua con trỏ treo; là UB | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| double free | Trả hai lần: `delete` cùng một chỗ hai lần; là UB | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| AddressSanitizer / ASan | Công cụ bắt lỗi bộ nhớ lúc chạy, bật bằng cờ biên dịch | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| LeakSanitizer | Phần của ASan báo vùng nhớ bị rò rỉ khi chương trình kết thúc | [Bài 07](nhom-1-nen-tang-bo-nho/07-new-delete.md) |
| RAII (Resource Acquisition Is Initialization) | Xin tài nguyên trong hàm tạo, trả trong hàm hủy, để tài nguyên tự được trả khi đối tượng chết | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| tài nguyên (resource) | Thứ mượn rồi phải trả: bộ nhớ heap, file, khóa, kết nối, ổ cắm mạng | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| throw / try / catch | `throw` ném một giá trị ra và cắt ngang hàm; `try { }` là vùng thử; `catch (T x) { }` bắt giá trị kiểu `T` được ném | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| tháo ngăn xếp (stack unwinding) | Khi có ngoại lệ, chương trình thoát ngược từng hàm tới `catch` và hủy mọi đối tượng cục bộ đã ra đời trên đường đi | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| std::terminate | Hàm kết thúc chương trình, được gọi khi ngoại lệ không bị bắt ở đâu cả; việc hủy các đối tượng khi đó là do cài đặt quyết định | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| defer (Go) | Câu lệnh Go chạy việc dọn dẹp ở cuối hàm; phải nhớ viết ở từng nơi dùng, khác RAII gắn vào kiểu dữ liệu | [Bài 08](nhom-1-nen-tang-bo-nho/08-raii.md) |
| smart pointer (con trỏ thông minh) | Đối tượng giả vờ là con trỏ nhưng tự lo việc giải phóng bộ nhớ bằng hàm hủy; `unique_ptr` và `shared_ptr` là hai loại chính | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| std::unique_ptr | Con trỏ thông minh sở hữu duy nhất một đối tượng ở heap, tự `delete` khi chết; không copy được, chỉ trao tay bằng move; trong `<memory>` | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| std::make_unique | Hàm tạo đối tượng và bọc ngay vào `unique_ptr`, như `std::make_unique<Cay>(5)`; có từ C++14 | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| quyền sở hữu (ownership) | Việc "ai chịu trách nhiệm xóa đối tượng"; `unique_ptr` ghi rõ điều đó trong kiểu, còn Go không cần vì có GC | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| std::move | Lời nói "tôi đồng ý trao đi": chỉ **ép** đối tượng thành rvalue, chưa di chuyển gì; hàm tạo/gán di chuyển được chọn mới lấy ruột (với `unique_ptr` nguồn thành `nullptr`); chi tiết ở [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| get() / release() / reset() | `get()` trả địa chỉ thô để nhìn, vẫn là chủ; `release()` bỏ quyền sở hữu mà không xóa; `reset()` xóa đối tượng đang giữ | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| operator* / operator-> | Hàm đặc biệt để một lớp "giả vờ là con trỏ": `*m` và `m->x` gọi chúng | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| template (khuôn mẫu) | Kiểu có tham số là kiểu khác, viết như `unique_ptr<Cay>`; giống generics của Go | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| custom deleter (bộ xóa tùy chỉnh) | Cách đổi việc `unique_ptr` làm khi hủy (ví dụ `fclose` thay vì `delete`); chỉ cần biết tên | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
| std::shared_ptr | Con trỏ thông minh cho nhiều chủ cùng giữ một đối tượng; copy được, đối tượng bị hủy khi người giữ cuối cùng buông; trong `<memory>` | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| std::weak_ptr | Con trỏ chỉ nhìn một đối tượng của `shared_ptr` mà không giữ nó sống; dùng `lock()` để lấy `shared_ptr` khi cần dùng | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| bộ đếm tham chiếu (reference count) | Số `shared_ptr` đang giữ một đối tượng; copy thì +1, buông thì −1, về 0 thì đối tượng bị hủy | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| khối điều khiển (control block) | Vùng heap nhỏ chứa bộ đếm mạnh và bộ đếm yếu, dùng chung cho mọi `shared_ptr`/`weak_ptr` của một đối tượng | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| use_count() | Hàm đọc bộ đếm mạnh của `shared_ptr`; chỉ dùng để học và gỡ lỗi, không dùng cho logic chương trình | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| std::make_shared | Hàm tạo đối tượng và bọc ngay vào `shared_ptr`; thường xin heap một lần cho cả đối tượng lẫn khối điều khiển | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| vòng tham chiếu (reference cycle) | Hai (hay nhiều) đối tượng giữ `shared_ptr` của nhau nên bộ đếm không bao giờ về 0 và chúng bị rò rỉ; phá bằng `weak_ptr` | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| lock() / expired() | `lock()` của `weak_ptr` trả về `shared_ptr` (rỗng nếu đối tượng đã hủy); `expired()` cho biết đối tượng đã hủy chưa | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| cache (bộ nhớ đệm) | Chỗ cất tạm kết quả vừa dùng để lần sau lấy cho nhanh, khỏi làm lại | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| observer (người theo dõi) | Đối tượng theo dõi một đối tượng khác mà không sở hữu nó | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| thread-safe (an toàn đa luồng) | Dùng được từ nhiều luồng cùng lúc mà không gây tranh chấp dữ liệu; với `shared_ptr` chỉ bộ đếm là an toàn, đối tượng bên trong thì không | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| data race | Hai luồng cùng truy cập một biến, ít nhất một luồng ghi, mà không có đồng bộ; là UB | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (nhắc, gọi là tranh chấp dữ liệu), [Bài 15](nhom-1-nen-tang-bo-nho/15-memory-leak-ub.md) |
| luồng (thread) | Một dòng chạy riêng trong cùng chương trình, gần giống goroutine của Go | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| nguyên tử (atomic) | Thao tác mà luồng khác không thể chen vào giữa chừng; bộ đếm của `shared_ptr` được cập nhật như vậy | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| sao chép nông (shallow copy) | Chép từng thành viên, nên con trỏ chỉ chép địa chỉ: hai đối tượng cùng giữ một vùng nhớ; là cách sao chép mặc định | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| sao chép sâu (deep copy) | Xin vùng nhớ mới và chép cả nội dung, để mỗi đối tượng có vùng riêng | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| phép gán sao chép (copy assignment) | Hàm `operator=` chạy khi gán vào đối tượng đã tồn tại (`b = a;`); phải trả vùng cũ, chống tự gán và trả `*this` | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| operator= | Tên hàm hiểu là "cách dấu `=` hoạt động cho kiểu này" | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| this | Con trỏ tới chính đối tượng đang chạy hàm; `*this` là chính đối tượng đó | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| Rule of 3 | Cần tự viết một trong {hàm hủy, hàm tạo sao chép, phép gán sao chép} thì thường cần cả ba; quy tắc kinh nghiệm | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| = delete | Xóa một hàm để cấm dùng; sao chép một kiểu đã xóa hàm sao chép là lỗi biên dịch (như `unique_ptr`) | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| = default | Bảo trình biên dịch tự sinh hàm đặc biệt mặc định (chỉ nêu tên ở Bài 11) | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| copy-and-swap | Cách viết phép gán an toàn: chép vào bản tạm rồi hoán đổi ruột (chỉ nêu tên ở Bài 11) | [Bài 11](nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) |
| lvalue (giá trị có tên) | Giá trị có tên và có chỗ để quay lại dùng ở dòng sau, như biến `x` | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| rvalue (giá trị tạm) | Giá trị tạm thời sắp biến mất, như `x + 1`, `3`, `Cay(3)` hay giá trị hàm trả về theo giá trị; lấy ruột của nó thì không ai tiếc | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| rvalue reference (tham chiếu rvalue) | Tham chiếu chỉ gắn được với giá trị tạm, viết `T&&`; bên trong hàm, tham số `&&` có tên nên là lvalue | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| move semantics (ngữ nghĩa di chuyển) | Lấy ruột (con trỏ) của đối tượng sắp bỏ thay vì sao chép sâu; nguồn còn lại cái bìa rỗng | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| move constructor (hàm tạo di chuyển) | Hàm tạo `T(T&&) noexcept` lấy ruột của một rvalue: chép con trỏ của nguồn rồi đặt con trỏ nguồn về `nullptr` | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| move assignment (phép gán di chuyển) | Phép gán lấy ruột: chống tự gán, trả vùng cũ, lấy con trỏ của nguồn rồi đặt nguồn về `nullptr` | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| valid but unspecified (hợp lệ nhưng không xác định) | Trạng thái của đối tượng chuẩn sau khi bị move: hủy hay gán lại đều an toàn, nhưng đừng đoán nội dung (`unique_ptr`/`shared_ptr` được bảo đảm rỗng) | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| rule of 0/5 | Rule of 5: lớp quản lý tài nguyên bằng tay thì quyết định cả năm hàm đặc biệt (hủy, sao chép ×2, di chuyển ×2); Rule of 0: dùng thành viên tự quản lý (`vector`, `unique_ptr`, `string`) và không viết hàm nào | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| noexcept | Lời hứa hàm không ném ngoại lệ; hàm tạo di chuyển không có nó thì `std::vector` sao chép thay vì di chuyển khi tăng khối | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| std::move_if_noexcept | Hàm chuẩn trả rvalue (để di chuyển) chỉ khi hàm tạo di chuyển hứa `noexcept` hoặc kiểu không sao chép được, nếu không thì trả lvalue (để sao chép); `std::vector` dùng nó khi tăng dung lượng | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| copy elision / RVO / NRVO | Trình biên dịch bỏ hẳn bước sao chép/di chuyển khi trả về; C++17 bắt buộc với giá trị tạm (`return Cay(3);`), còn NRVO cho biến có tên (`return c;`) là được phép nhưng không bắt buộc; đừng viết `return std::move(c);` | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| perfect forwarding (chuyển tiếp hoàn hảo) | Giữ nguyên lvalue/rvalue khi chuyển tiếp đối số bằng `T&&` và `std::forward` (chỉ nêu tên ở Bài 12) | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| forwarding reference (tham chiếu chuyển tiếp) | `T&&` trong template khi `T` được suy ra từ đối số, nhận cả lvalue lẫn rvalue (chỉ nêu tên ở Bài 12) | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| std::forward | Chuyển tiếp một đối số mà giữ nguyên nó là lvalue hay rvalue (chỉ nêu tên ở Bài 12) | [Bài 12](nhom-1-nen-tang-bo-nho/12-move-semantics.md) |
| auto | Để trình biên dịch tự đoán kiểu (lần đầu dùng ở [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md), giải thích ngay tại đó); bẫy: bỏ `&` và `const` ngoài cùng, nên muốn giữ phải viết `auto&` hay `const auto&` | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| range-based for | Vòng `for (khai báo : dãy)` duyệt cả dãy mà không cần chỉ số (C++11); `for (auto x : v)` sao chép từng phần tử, `for (const auto& x : v)` thì không | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| std::vector | Mảng co giãn của thư viện chuẩn, giống slice của Go (`#include <vector>`); các kiểu chứa học kỹ ở nhóm STL | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) (dùng cơ bản) |
| lambda | Hàm không tên viết ngay tại chỗ, cú pháp `[bắt](tham số){ thân }`, cất được vào biến `auto` và gọi như hàm (C++11); giống closure của Go | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| capture (bắt) | Danh sách trong `[ ]` của lambda: `[=]` chép biến dùng tới lúc tạo lambda, `[&]` giữ tham chiếu (treo nếu lambda sống lâu hơn biến), `[x]`/`[&x]` chọn từng biến | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| enum class | Kiểu liệt kê có phạm vi riêng (`MauSac::Tim`) và không tự đổi sang `int` (C++11) | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| override / final | `override` đánh dấu hàm ghi đè hàm ảo của lớp cha để trình biên dịch báo lỗi nếu sai chữ ký; `final` cấm ghi đè hoặc kế thừa tiếp (C++11); chỉ nêu tên, ví dụ ở nhóm OOP | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| constexpr | Cho phép tính lúc biên dịch: biến `constexpr` bắt buộc và ngầm `const`; hàm `constexpr` gọi với giá trị lúc chạy vẫn chạy lúc chạy (C++11; thân thoải mái hơn từ C++14) | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| static_assert | Kiểm tra điều kiện lúc biên dịch; sai thì không biên dịch được (C++11) | [Bài 13](nhom-1-nen-tang-bo-nho/13-cpp11-14-17.md) |
| generic lambda | Lambda có tham số `auto`, dùng được cho nhiều kiểu (C++14) | Bài 14 |
| structured binding | `auto [a, b] = giaTri;` tách cặp hoặc struct thành nhiều biến; `auto` chép, `auto&` là biệt danh (C++17) | Bài 14 |
| std::optional | Hộp hoặc chứa một giá trị, hoặc rỗng (`std::nullopt`); kiểm tra bằng `if (r)`, lấy bằng `*r` hay `value_or` (C++17) | Bài 14 |
| std::variant | Giá trị chứa đúng một trong vài kiểu đã liệt kê; dùng `std::holds_alternative`, `std::get` (C++17) | Bài 14 |
| std::string_view | Cửa sổ không sở hữu nhìn vào các ký tự có sẵn, không sao chép; treo nếu chuỗi gốc chết trước (C++17) | Bài 14 |
| `if` có khởi tạo | `if (khởi tạo; điều kiện)`: biến khai báo ở đầu chỉ sống trong `if`/`else`; giống `if v, ok := ...; ok` của Go (C++17) | Bài 14 |
| std::filesystem | Thư viện làm việc với đường dẫn, file, thư mục (C++17); chỉ nêu tên | Bài 14 |
| buffer overflow | Ghi vượt biên mảng | [Bài 15](nhom-1-nen-tang-bo-nho/15-memory-leak-ub.md) |
| Valgrind | Công cụ kiểm tra bộ nhớ không cần biên dịch lại | [Bài 15](nhom-1-nen-tang-bo-nho/15-memory-leak-ub.md) |
| crash | Chương trình sập đột ngột | [Bài 15](nhom-1-nen-tang-bo-nho/15-memory-leak-ub.md) |
| allocator (bộ cấp phát bộ nhớ) | Phần chương trình lo việc cấp và thu hồi vùng nhớ trên heap | [Bài 15](nhom-1-nen-tang-bo-nho/15-memory-leak-ub.md) |
