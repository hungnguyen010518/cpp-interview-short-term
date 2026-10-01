# Bảng thuật ngữ

Thuật ngữ được thêm vào đây ở cuối mỗi bài.

| Thuật ngữ | Nghĩa dễ hiểu | Bài |
|---|---|---|
| stack (ngăn xếp) | Nơi chứa biến cục bộ, tự dọn khi hết hàm | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| heap (vùng nhớ cấp phát động) | Nơi tự xin (`new`) và tự trả (`delete`) bộ nhớ | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| con trỏ (pointer) | Biến giữ một địa chỉ | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| tham chiếu (reference) | Biệt danh của một đối tượng có sẵn | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| const (hằng) | Không được sửa | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| memory leak (rò rỉ bộ nhớ) | Xin bộ nhớ mà không trả | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| dangling pointer (con trỏ treo) | Con trỏ trỏ tới chỗ đã bị dọn | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| nullptr | Giá trị con trỏ nghĩa là "chưa trỏ vào đâu" | [Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) |
| RAII | Xin tài nguyên khi tạo, tự trả khi hủy | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| smart pointer (con trỏ thông minh) | Con trỏ tự dọn | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| destructor (hàm hủy) | Chạy khi đối tượng chết | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| ownership (quyền sở hữu) | Ai chịu trách nhiệm dọn | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| reference count (bộ đếm tham chiếu) | Đếm số người đang giữ | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| control block (khối điều khiển) | Chỗ lưu bộ đếm của `shared_ptr` | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| unique_ptr | Con trỏ thông minh chỉ có một chủ; không copy được, chỉ trao tay bằng `std::move` | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| shared_ptr | Con trỏ thông minh cho nhiều chủ cùng giữ; chủ cuối cùng buông thì đối tượng mới bị dọn | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| weak_ptr | Con trỏ chỉ nhìn đối tượng của `shared_ptr`, không giữ nó sống | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| exception (ngoại lệ) | Một sự cố bất ngờ khi chạy, được "ném" ra để chỗ khác bắt và xử lý | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| cache (bộ nhớ đệm) | Chỗ cất tạm những thứ hay dùng để lần sau lấy cho nhanh | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| observer (người theo dõi) | Đối tượng chỉ để ý một đối tượng khác chứ không giữ nó sống | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| lvalue (giá trị có tên) | Có tên, ở lâu | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| rvalue (giá trị tạm) | Tạm thời, sắp biến mất | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| move semantics (ngữ nghĩa di chuyển) | Lấy ruột thay vì sao chép | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| copy elision / RVO | Trình biên dịch bỏ qua bước copy khi trả về | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| rule of 0/3/5 | Quy tắc về các hàm đặc biệt của class | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| perfect forwarding (chuyển tiếp hoàn hảo) | Giữ nguyên lvalue/rvalue khi chuyển tiếp | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| rvalue reference (tham chiếu rvalue) | Tham chiếu tới giá trị tạm, viết `T&&` | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| move constructor (hàm tạo di chuyển) | Hàm tạo đối tượng mới bằng cách lấy ruột của một đối tượng tạm | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| move assignment (toán tử gán di chuyển) | Phép gán lấy ruột của đối tượng khác thay vì sao chép | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| noexcept | Lời hứa rằng hàm này không ném ngoại lệ | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| valid but unspecified (hợp lệ nhưng không xác định) | Đối tượng đã bị move vẫn dùng được để hủy hoặc gán lại, nhưng đừng đoán bên trong có gì | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| forwarding reference (tham chiếu chuyển tiếp) | `T&&` trong template khi `T` được suy ra từ tham số, nhận được cả lvalue lẫn rvalue | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| std::forward | Chuyển tiếp một tham số mà giữ nguyên nó là lvalue hay rvalue | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| auto | Để trình biên dịch tự đoán kiểu | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| lambda | Hàm vô danh viết ngay tại chỗ | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| constexpr | Cho phép tính lúc biên dịch khi đầu vào cố định | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| enum class | Liệt kê có phạm vi riêng | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| optional | Hộp có thể rỗng | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| variant | Hộp chứa một trong nhiều kiểu | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| string_view | Cửa sổ nhìn vào chuỗi, không copy | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| structured binding | Tách một cặp/bộ thành nhiều biến | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| range-based for | Vòng `for` duyệt cả dãy mà không cần chỉ số, ví dụ `for (auto x : v)` | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| override / final | `override` kiểm tra ghi đè hàm ảo cho đúng; `final` cấm ghi đè hoặc kế thừa tiếp | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| generic lambda | Lambda có tham số `auto`, dùng được cho nhiều kiểu (từ C++14) | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| dangling reference (tham chiếu treo) | Tham chiếu trỏ vào chỗ đã bị dọn | [Bài 4](nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md) |
| use-after-free | Dùng sau khi trả | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| double free | Trả hai lần | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| buffer overflow | Ghi vượt biên mảng | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| undefined behavior / UB | Hành vi không xác định: luật chơi bị phá, mọi chuyện đều có thể xảy ra | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| AddressSanitizer / ASan | Công cụ bắt lỗi bộ nhớ lúc chạy, bật bằng cờ biên dịch | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| Valgrind | Công cụ kiểm tra bộ nhớ không cần biên dịch lại | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| data race | Hai luồng cùng truy cập một biến, ít nhất một luồng ghi, mà không có đồng bộ; là UB | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| LeakSanitizer | Phần của ASan báo vùng nhớ bị rò rỉ khi chương trình kết thúc | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| crash | Chương trình sập đột ngột | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
| allocator (bộ cấp phát bộ nhớ) | Phần chương trình lo việc cấp và thu hồi vùng nhớ trên heap | [Bài 5](nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md) |
