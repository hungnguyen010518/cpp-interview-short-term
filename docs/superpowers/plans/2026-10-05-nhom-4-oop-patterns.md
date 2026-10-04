# Nhóm 4 — OOP, template và Design Patterns (Bài 31–37) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết Nhóm 4 gồm 7 bài (Bài 31–37) về lập trình hướng đối tượng, template và design patterns trong C++, cùng phong cách "dạy từ gốc" như Nhóm 1–3.

**Architecture:** Thư mục mới `docs/nhom-4-oop-patterns/`; dùng nguyên khung 8 khối, bộ kiểm tra (`nhom-*/*.md` đã được quét tự động) và luật dạy v2. Mỗi bài tự thêm mục nav (nhóm "Nhóm 4 — OOP, template và Design Patterns"), dòng `tien-do.md`, hàng glossary.

**Tech Stack:** MkDocs Material 9.5.39, g++ 11 (`-std=c++17 -Wall -pthread`), AddressSanitizer/UBSan có sẵn, hai script kiểm tra trong `scripts/`.

## Global Constraints

- **Luật dạy v2**: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/teaching-rules-v2.md`; quy ước: `course-conventions.md`, `global-constraints.md` cùng thư mục (số bài trong đó lỗi thời; dùng số trong bảng dưới). Đọc thêm findings các nhóm trước để tránh loại lỗi đã gặp: `.superpowers/sdd/2026-10-02-nhom-2-stl-thuat-toan/final-review.md`, `.superpowers/sdd/2026-10-04-nhom-3-da-luong/final-review.md` (nếu đã có) và `task-*-findings-r1.md` trong hai thư mục đó.
- Học viên: 3 năm Go (struct, method, interface ngầm định, embedding, không có kế thừa/ngoại lệ/template theo kiểu C++; generics từ Go 1.18), đã học Bài 01–30. Cầu nối Go phải ĐÚNG sự thật (máy có Go 1.27: `/snap/go/current/bin/go`; zsh: `go` có thể in rỗng). Trước khi dùng bất kỳ khái niệm nào, grep Bài 01–30 xem đã dạy chưa (class/struct/constructor/destructor/copy/move/Rule of 3-5: Bài 08, 11, 12; `= default`/`= delete`: Bài 11, 21; template cơ bản và `std::vector<int>`: Bài 16; lambda: Bài 13/20; smart pointer: Bài 09/10); chưa dạy thì giải thích tại chỗ.
- Phân biệt nghiêm: "chuẩn C++ nói/bảo đảm" với "g++ 11 / máy mình cho kết quả này" (ví dụ: vtable là chi tiết cài đặt, chuẩn không bắt buộc; kích thước đối tượng `sizeof` có thể khác theo máy). Mọi câu "mình đã chạy" phải do người viết tự chạy. Số đo/ kích thước: chỉ nêu khi chạy thật và nói đổi theo máy/-O.
- Quiz 6–8 câu/bài, ≥2 câu đọc code; độ dài HIỂN THỊ của đáp án (bỏ dấu `, markup): mỗi bài có ≥1 câu đúng-ngắn-nhất và ≥1 câu đúng-dài-nhất nhưng ≤2 mỗi loại, còn lại hạng giữa; đáp án sai là lầm tưởng có thật, giọng văn đồng đều; chỉ MỘT đáp án bảo vệ được (đề phải đủ chi tiết); giải thích không gọi đáp án theo vị trí; không dùng cú pháp chưa dạy trong code quiz.
- Mọi khối ```` ```cpp ```` biên dịch sạch cảnh báo, chạy mã thoát 0 trong 5 giây (kiem_code.py); chương trình cấp phát phải sạch ASan+UBSan; khối lỗi biên dịch/UB đặt `// bo-qua-kiem-tra` và chỉ nêu cái đã chạy thật (trích thông báo lỗi g++ thật, rút gọn). Mỗi listing có bảng "Chạy từng dòng". Mỗi bài ≤ ~560 dòng; một ý chính; đoạn ≤4 câu; ví von nhất quán (đề xuất: xưởng làm đồ chơi/ bản vẽ → sản phẩm cho class/object; mỗi bài tự kiểm không để ví von tự mâu thuẫn).
- Repo công khai: không tên công ty/khách hàng/dự án/người, không đường dẫn cá nhân.
- `data-bai` = số bài hai chữ số = tiền tố file; dòng trong `docs/tien-do.md`; mục `nav`; hàng `docs/glossary.md` cho mọi thuật ngữ mới (đúng thứ tự bài, không trùng).
- Git: danh tính đã cấu hình cục bộ; commit tiếng Việt kết thúc `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; `git add` từng file cụ thể (không `-A`); không push; không đụng `docs/superpowers/` hay `.superpowers/` (ngoài báo cáo).
- Chạy trước khi commit: `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`.

## Lộ trình

| Bài | File | Nội dung |
|---|---|---|
| 31 | `31-lop-dong-goi.md` | Lớp và đóng gói: class vs struct (khác biệt duy nhất: mặc định truy cập), `public/private`, constructor (danh sách khởi tạo thành viên), destructor, thứ tự gọi (thành viên theo thứ tự khai báo; hủy ngược lại), `this`, hàm thành viên `const`, thành viên `static`, getter/setter và vì sao đóng gói, `friend` chỉ nhắc |
| 32 | `32-ke-thua.md` | Kế thừa: `class Con : public Cha`, thứ tự tạo/hủy, `protected`, ghi đè/che hàm, gọi hàm cha, kế thừa `private`/`protected` chỉ nhắc, "là một" (is-a) vs "có một" (has-a), kế thừa đa vào chỉ nhắc + bài toán kim cương, `final` |
| 33 | `33-da-hinh-virtual.md` | Đa hình: `virtual`, `override`, gọi qua con trỏ/tham chiếu lớp cha, vtable/vptr ở mức khái niệm (chi tiết cài đặt, chứng minh bằng `sizeof` khi chạy thật), hàm hủy `virtual` (UB khi xóa qua con trỏ cha không virtual — ASan), hàm thuần ảo và lớp trừu tượng (interface), object slicing, `dynamic_cast`/`typeid` chỉ nhắc, chi phí gọi virtual |
| 34 | `34-template.md` | Template hàm và template lớp: ý tưởng sinh mã theo kiểu, suy luận đối số, chuyên biệt hóa (chỉ nhắc), tham số không phải kiểu (`std::array<int,N>`), template vs đa hình lúc chạy (đa hình lúc biên dịch vs lúc chạy), thông báo lỗi dài, vì sao định nghĩa template nằm trong header, `static_assert`/concepts C++20 chỉ nhắc, SFINAE chỉ tên |
| 35 | `35-pattern-singleton-factory.md` | Design pattern là gì; Singleton (Meyers singleton: biến `static` cục bộ an toàn luồng từ C++11 — nối Bài 25; vì sao bị chê: trạng thái toàn cục, khó test), Factory Method/Simple Factory trả `unique_ptr<Base>`, Builder chỉ nhắc |
| 36 | `36-pattern-observer-strategy.md` | Observer (danh sách `weak_ptr`/`std::function` callback, hủy đăng ký — nối Bài 10 weak_ptr), Strategy (đối tượng đa hình vs `std::function`/lambda vs template — nối Bài 20/33/34), Decorator/RAII chỉ nhắc |
| 37 | `37-solid-thiet-ke.md` | SOLID (từng chữ cái với ví dụ C++ nhỏ), ưu tiên composition hơn inheritance, Rule of 0 thiết kế lớp (nối Bài 12), interface bằng lớp trừu tượng vs template, tổng hợp câu hỏi phỏng vấn OOP (nối Bài 31–36) |

Mỗi task = một bài, tuần tự. Mỗi bài qua một vòng review "người học" (lens: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/lesson-review-lens-v2.md`), sửa tối đa 3 vòng. Sau Bài 37: cập nhật `docs/index.md`, rà soát cả nhóm bằng reviewer mạnh nhất, sửa, đẩy lên và báo người dùng.
