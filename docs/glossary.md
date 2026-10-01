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
| hàm tạo sao chép (copy constructor) | Hàm tạo đặc biệt chạy mỗi khi tạo bản sao của đối tượng cùng kiểu, nhận tham số `const T&` | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| giá trị tạm (temporary) | Giá trị không có tên, chỉ sống trong một câu lệnh, như `5` hay `a + 1` | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| truyền theo tham chiếu (pass by reference) | Hàm nhận tham chiếu: không sao chép, và sửa được bản gốc nếu không có `const` | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| const& | Tham chiếu hằng `const T&`: chỉ xem, không sao chép, nhận được cả giá trị tạm | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) |
| dangling reference (tham chiếu treo) | Tham chiếu trỏ vào chỗ đã bị dọn | [Bài 06](nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md), [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) (lambda) |
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
| std::move | Lời nói "tôi đồng ý trao đi" cho phép chuyển ruột của một đối tượng sang đối tượng khác; với `unique_ptr` nguồn thành `nullptr`; chi tiết ở [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) | [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md) |
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
| data race | Hai luồng cùng truy cập một biến, ít nhất một luồng ghi, mà không có đồng bộ; là UB | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (nhắc, gọi là tranh chấp dữ liệu), [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| luồng (thread) | Một dòng chạy riêng trong cùng chương trình, gần giống goroutine của Go | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| nguyên tử (atomic) | Thao tác mà luồng khác không thể chen vào giữa chừng; bộ đếm của `shared_ptr` được cập nhật như vậy | [Bài 10](nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) |
| lvalue (giá trị có tên) | Có tên, ở lâu | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| rvalue (giá trị tạm) | Tạm thời, sắp biến mất | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| move semantics (ngữ nghĩa di chuyển) | Lấy ruột thay vì sao chép | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| copy elision / RVO | Trình biên dịch bỏ qua bước copy khi trả về | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| rule of 0/3/5 | Quy tắc về các hàm đặc biệt của class | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| perfect forwarding (chuyển tiếp hoàn hảo) | Giữ nguyên lvalue/rvalue khi chuyển tiếp | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| rvalue reference (tham chiếu rvalue) | Tham chiếu tới giá trị tạm, viết `T&&` | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| move constructor (hàm tạo di chuyển) | Hàm tạo đối tượng mới bằng cách lấy ruột của một rvalue (đối tượng tạm hoặc đối tượng đã `std::move`) | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| move assignment (toán tử gán di chuyển) | Phép gán lấy ruột của đối tượng khác thay vì sao chép | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| noexcept | Lời hứa rằng hàm này không ném ngoại lệ | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| valid but unspecified (hợp lệ nhưng không xác định) | Đối tượng đã bị move vẫn dùng được để hủy hoặc gán lại, nhưng đừng đoán bên trong có gì | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| forwarding reference (tham chiếu chuyển tiếp) | `T&&` trong template khi `T` được suy ra từ tham số, nhận được cả lvalue lẫn rvalue | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| std::forward | Chuyển tiếp một tham số mà giữ nguyên nó là lvalue hay rvalue | [Bài 11](nhom-1-nen-tang-bo-nho/11-move-semantics.md) |
| auto | Để trình biên dịch tự đoán kiểu (lần đầu dùng ở [Bài 09](nhom-1-nen-tang-bo-nho/09-unique-ptr.md), giải thích ngay tại đó) | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| lambda | Hàm vô danh viết ngay tại chỗ | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| constexpr | Cho phép tính lúc biên dịch khi đầu vào cố định | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| enum class | Liệt kê có phạm vi riêng | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| optional | Hộp có thể rỗng | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| variant | Hộp chứa một trong nhiều kiểu | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| string_view | Cửa sổ nhìn vào chuỗi, không copy | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| structured binding | Tách một cặp/bộ thành nhiều biến | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| range-based for | Vòng `for` duyệt cả dãy mà không cần chỉ số, ví dụ `for (auto x : v)` | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| override / final | `override` kiểm tra ghi đè hàm ảo cho đúng; `final` cấm ghi đè hoặc kế thừa tiếp | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| generic lambda | Lambda có tham số `auto`, dùng được cho nhiều kiểu (từ C++14) | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| buffer overflow | Ghi vượt biên mảng | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| Valgrind | Công cụ kiểm tra bộ nhớ không cần biên dịch lại | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| crash | Chương trình sập đột ngột | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| allocator (bộ cấp phát bộ nhớ) | Phần chương trình lo việc cấp và thu hồi vùng nhớ trên heap | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
