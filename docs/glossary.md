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
| con trỏ (pointer) | Biến đựng một địa chỉ; `int*` là con trỏ tới một `int`, `*p` là giá trị ở địa chỉ đó | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| new / delete | `new` xin chỗ ở heap và trả địa chỉ; `delete` trả chỗ đó về | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| memory leak (rò rỉ bộ nhớ) | Chỗ ở heap đã xin mà không bao giờ được trả | [Bài 02](nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) |
| con trỏ (pointer) | Biến đựng một địa chỉ, thường là địa chỉ của biến khác; `int* p` là con trỏ tới `int` | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| giải tham chiếu (dereference) | Đi theo địa chỉ trong con trỏ để đọc hoặc ghi thứ nằm ở đó, viết `*p` | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| nullptr | Giá trị của con trỏ "chưa trỏ vào đâu" (C++11), có kiểu riêng `std::nullptr_t`; ứng với `nil` của Go | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| null pointer (con trỏ null) | Con trỏ có giá trị `nullptr`; giải tham chiếu nó là hành vi không xác định | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| toán tử `->` | `p->x` là cách viết gọn của `(*p).x`, lấy trường `x` của struct mà con trỏ `p` trỏ tới | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
| void* | Con trỏ không nói rõ trỏ tới loại gì, nên không giải tham chiếu thẳng được | [Bài 03](nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) |
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
| auto | Để trình biên dịch tự đoán kiểu | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
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
| dangling reference (tham chiếu treo) | Tham chiếu trỏ vào chỗ đã bị dọn | [Bài 12](nhom-1-nen-tang-bo-nho/12-cpp11-14-17.md) |
| use-after-free | Dùng sau khi trả | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| double free | Trả hai lần | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| buffer overflow | Ghi vượt biên mảng | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| undefined behavior / UB | Hành vi không xác định: luật chơi bị phá, mọi chuyện đều có thể xảy ra | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| AddressSanitizer / ASan | Công cụ bắt lỗi bộ nhớ lúc chạy, bật bằng cờ biên dịch | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| Valgrind | Công cụ kiểm tra bộ nhớ không cần biên dịch lại | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| data race | Hai luồng cùng truy cập một biến, ít nhất một luồng ghi, mà không có đồng bộ; là UB | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| LeakSanitizer | Phần của ASan báo vùng nhớ bị rò rỉ khi chương trình kết thúc | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| crash | Chương trình sập đột ngột | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
| allocator (bộ cấp phát bộ nhớ) | Phần chương trình lo việc cấp và thu hồi vùng nhớ trên heap | [Bài 13](nhom-1-nen-tang-bo-nho/13-memory-leak-ub.md) |
