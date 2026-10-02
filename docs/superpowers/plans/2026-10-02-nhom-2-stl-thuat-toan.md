# Nhóm 2 — STL và thuật toán (Bài 16–22) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết Nhóm 2 gồm 7 bài (Bài 16–22) về STL và thuật toán, cùng phong cách "dạy từ gốc" như Nhóm 1.

**Architecture:** Thư mục mới `docs/nhom-2-stl-thuat-toan/`; dùng nguyên khung 8 khối, bộ kiểm tra (`nhom-*/*.md` đã được quét tự động) và luật dạy v2. Mỗi bài tự thêm mục nav, dòng `tien-do.md`, hàng glossary.

**Tech Stack:** MkDocs Material 9.5.39, g++ 11 (`-std=c++17 -Wall -pthread`), hai script kiểm tra trong `scripts/`.

## Global Constraints

- **Luật dạy v2**: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/teaching-rules-v2.md` (không hổng, bảng "chạy từng dòng", kết quả chạy thật, cầu nối Go, luật trắc nghiệm công bằng, tự kiểm tra trước khi báo). Quy ước khóa học: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/course-conventions.md` và `global-constraints.md` (số bài trong file cũ đã lỗi thời; dùng số bài trong bảng dưới).
- Học viên: 3 năm Go, đã học Bài 01–15 (bộ nhớ, con trỏ, tham chiếu/const, new/delete, RAII, smart pointer, sao chép, move, C++11/14/17, UB). Trước khi dùng bất kỳ khái niệm nào, kiểm tra trong Bài 01–15 (grep) xem đã dạy chưa; chưa thì giải thích tại chỗ (đặc biệt: `#include <vector>`, cú pháp `<int>` của template, range-for, `auto`, lambda — kiểm tra Bài 13/14).
- Quiz 6–8 câu/bài, ≥2 câu đọc code; công bằng độ dài đáp án (đúng KHÔNG hệ thống là dài nhất/ngắn nhất; ≤2 câu đúng-ngắn-nhất và ≤2 câu đúng-dài-nhất mỗi bài); giải thích không gọi đáp án theo vị trí; đáp án đúng KHÔNG đặt theo thứ tự cố định (JS xáo trộn).
- Mọi khối ```` ```cpp ```` biên dịch sạch cảnh báo, chạy mã thoát 0 trong 5 giây; minh họa lỗi/UB đặt trong khối bắt đầu bằng `// bo-qua-kiem-tra` và chỉ nêu kết quả đã thực sự chạy. Số đo hiệu năng/địa chỉ: nói rõ là khác nhau theo máy.
- Mỗi bài ≤ ~550 dòng; một ý chính; đoạn ≤4 câu. Bộ analogy: tiếp tục dùng bộ của Nhóm 1 khi hợp (kho đồ = heap, ...), thêm analogy mới nhất quán trong nhóm.
- Repo công khai: không tên công ty/khách hàng/dự án/người, không đường dẫn cá nhân, không nhắc "nhà tuyển dụng/JD".
- `data-bai` = số bài hai chữ số = tiền tố file; dòng trong `docs/tien-do.md`; mục `nav` (mới: "Nhóm 2 — STL và thuật toán"); hàng `docs/glossary.md` cho mọi thuật ngữ mới.
- Git: danh tính đã cấu hình cục bộ; commit tiếng Việt kết thúc bằng `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; chưa push; không đụng `docs/superpowers/` hay `.superpowers/`.
- Chạy trước khi commit: `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`.

## Lộ trình

| Bài | File | Nội dung |
|---|---|---|
| 16 | `16-vector.md` | `std::vector`: mảng co giãn, size vs capacity, push_back, tái cấp phát, reserve, `[]` vs `at`, truyền vector vvào hàm, vector<bool> chỉ nhắc |
| 17 | `17-string-array-deque-list.md` | `std::string` (SSO chỉ mô tả sơ), `string_view`, `std::array`, `deque`, `list`; chọn container nào |
| 18 | `18-map-set-unordered.md` | `map`/`set` (cây cân bằng, có thứ tự, O(log n)) vs `unordered_map`/`unordered_set` (băm, O(1) trung bình); `operator[]` tự chèn; `pair`, structured binding (C++17) |
| 19 | `19-iterator-vo-hieu.md` | Iterator là gì, begin/end, range-for chạy thế nào, iterator invalidation của từng container, xóa khi duyệt, `erase` trả iterator |
| 20 | `20-algorithm-lambda.md` | `<algorithm>`: sort, find, find_if, count_if, transform, accumulate, for_each, remove-erase idiom; lambda và capture `[=]`/`[&]`, comparator |
| 21 | `21-big-o-cau-truc-du-lieu.md` | Big-O, so sánh cấu trúc dữ liệu tự cài (mảng, danh sách liên kết, stack, queue, hash table, cây nhị phân tìm kiếm, heap) và `priority_queue`/`stack`/`queue` |
| 22 | `22-thuat-toan-hay-hoi.md` | Thuật toán hay hỏi: tìm kiếm nhị phân, hai con trỏ, sắp xếp (so sánh quick/merge/std::sort), đệ quy, quy hoạch động nhập môn; mẹo giải đề tại bảng trắng |

Mỗi task bên dưới = một bài. Task N nhận brief là dòng tương ứng trong bảng + các ràng buộc ở trên.

### Task 1–7: viết Bài 16, 17, 18, 19, 20, 21, 22 (mỗi bài một task, tuần tự)

- [ ] Mỗi task: viết file bài theo luật dạy v2, thêm nav/tien-do/glossary, chạy bộ kiểm tra, commit.
- [ ] Mỗi bài qua một vòng review "người học" (lens: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/lesson-review-lens-v2.md`), sửa tối đa 3 vòng.
- [ ] Sau Bài 22: cập nhật `docs/index.md` (liệt kê Nhóm 2), rà soát toàn nhóm (độ dài đáp án, thuật ngữ, link chéo) rồi báo người dùng.
