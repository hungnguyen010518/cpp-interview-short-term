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
| RAII | Xin tài nguyên khi tạo, tự trả khi hủy | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| smart pointer (con trỏ thông minh) | Con trỏ tự dọn | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| destructor (hàm hủy) | Chạy khi đối tượng chết | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| ownership (quyền sở hữu) | Ai chịu trách nhiệm dọn | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| reference count (bộ đếm tham chiếu) | Đếm số người đang giữ | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| control block (khối điều khiển) | Chỗ lưu bộ đếm của `shared_ptr` | [Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) |
| lvalue (giá trị có tên) | Có tên, ở lâu | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| rvalue (giá trị tạm) | Tạm thời, sắp biến mất | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| move semantics (ngữ nghĩa di chuyển) | Lấy ruột thay vì sao chép | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| copy elision / RVO | Trình biên dịch bỏ qua bước copy khi trả về | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| rule of 0/3/5 | Quy tắc về các hàm đặc biệt của class | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
| perfect forwarding (chuyển tiếp hoàn hảo) | Giữ nguyên lvalue/rvalue khi chuyển tiếp | [Bài 3](nhom-1-nen-tang-bo-nho/03-move-semantics.md) |
