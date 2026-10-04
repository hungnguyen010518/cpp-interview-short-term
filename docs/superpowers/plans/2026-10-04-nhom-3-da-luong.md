# Nhóm 3 — Đa luồng (Bài 24–30) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết Nhóm 3 gồm 7 bài (Bài 24–30) về lập trình đa luồng C++, cùng phong cách "dạy từ gốc" như Nhóm 1 và 2.

**Architecture:** Thư mục mới `docs/nhom-3-da-luong/`; dùng nguyên khung 8 khối, bộ kiểm tra (`nhom-*/*.md` đã được quét tự động) và luật dạy v2. Mỗi bài tự thêm mục nav (nhóm "Nhóm 3 — Đa luồng"), dòng `tien-do.md`, hàng glossary.

**Tech Stack:** MkDocs Material 9.5.39, g++ 11 (`-std=c++17 -Wall -pthread`), ThreadSanitizer (`-fsanitize=thread`, đã kiểm tra chạy được trên máy này) để chứng minh data race/deadlock thật, hai script kiểm tra trong `scripts/`.

## Global Constraints

- **Luật dạy v2**: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/teaching-rules-v2.md`; quy ước: `course-conventions.md`, `global-constraints.md` cùng thư mục (số bài trong đó lỗi thời; dùng số trong bảng dưới). Đọc thêm các findings của Nhóm 2 trong `.superpowers/sdd/2026-10-02-nhom-2-stl-thuat-toan/` (task-*-findings-r1.md, final-review.md) để tránh loại lỗi đã gặp.
- Học viên: 3 năm Go (goroutine, channel, `sync.Mutex`, `sync.WaitGroup`, `-race`, `sync/atomic`, `context`), đã học Bài 01–23. Cầu nối Go phải ĐÚNG sự thật: goroutine ≠ thread (do runtime Go lập lịch), channel không có trong thư viện chuẩn C++; `go test -race` ↔ ThreadSanitizer (máy có Go 1.27 để kiểm). Trước khi dùng bất kỳ khái niệm nào, grep Bài 01–23 xem đã dạy chưa (lambda: Bài 13/20; RAII/lock_guard: Bài 08; move: Bài 12; unique_ptr: Bài 09); chưa dạy thì giải thích tại chỗ (kể cả `#include <thread>`, `std::chrono`, `std::this_thread::sleep_for`).
- Phân biệt nghiêm: "chuẩn C++ nói/bảo đảm" với "g++ 11 / máy mình cho kết quả này". Kết quả đa luồng không xác định → KHÔNG chép thứ tự in cụ thể như thể bảo đảm; chương trình ví dụ phải có đầu ra ổn định (in tổng, đếm, kết quả sau join) hoặc nói rõ thứ tự thay đổi mỗi lần. Chương trình minh họa data race/deadlock đặt trong khối `// bo-qua-kiem-tra` và chỉ nêu cái đã thực sự chạy (TSan báo gì, treo thì timeout mã 124). Số đo thời gian: chỉ nêu nếu chạy thật và nói là khác nhau theo máy/-O.
- Quiz 6–8 câu/bài, ≥2 câu đọc code; độ dài HIỂN THỊ của đáp án (bỏ dấu `, markup): mỗi bài có ≥1 câu đúng-ngắn-nhất và ≥1 câu đúng-dài-nhất nhưng ≤2 mỗi loại, còn lại hạng giữa; đáp án sai là lầm tưởng có thật, giọng văn đồng đều; chỉ MỘT đáp án bảo vệ được; giải thích không gọi đáp án theo vị trí; không dùng cú pháp chưa dạy trong code quiz.
- Mọi khối ```` ```cpp ```` biên dịch sạch cảnh báo, chạy mã thoát 0 trong 5 giây (kiem_code.py); chạy thật với `-fsanitize=thread` khi có luồng và sạch. Mỗi bài ≤ ~560 dòng; một ý chính; đoạn ≤4 câu; ví von nhất quán trong nhóm (đề xuất: bếp ăn nhiều đầu bếp, một cái thớt chung; mỗi bài tự kiểm không để ví von tự mâu thuẫn).
- Repo công khai: không tên công ty/khách hàng/dự án/người, không đường dẫn cá nhân.
- `data-bai` = số bài hai chữ số = tiền tố file; dòng trong `docs/tien-do.md`; mục `nav` ("Nhóm 3 — Đa luồng"); hàng `docs/glossary.md` cho mọi thuật ngữ mới (đúng thứ tự bài, không trùng).
- Git: danh tính đã cấu hình cục bộ; commit tiếng Việt kết thúc `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; `git add` từng file cụ thể; không push (người điều phối push); không đụng `docs/superpowers/` hay `.superpowers/`.
- Chạy trước khi commit: `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`.

## Lộ trình

| Bài | File | Nội dung |
|---|---|---|
| 24 | `24-thread-co-ban.md` | `std::thread`: tạo luồng, `join` vs `detach`, truyền tham số (sao chép mặc định, `std::ref`), lambda làm hàm luồng, lỗi hay gặp (hủy `thread` còn joinable → `std::terminate`, tham chiếu tới biến cục bộ đã chết), `hardware_concurrency`, `this_thread`; RAII bọc thread (nối Bài 08) |
| 25 | `25-data-race-mutex.md` | Data race là gì (ví dụ đếm chung), `std::mutex`, `lock_guard`, `unique_lock`, phạm vi khóa nhỏ nhất, TSan bắt race thật, `thread_local` nhắc |
| 26 | `26-deadlock.md` | Deadlock (bốn điều kiện sơ lược), thứ tự khóa, `std::scoped_lock`/`std::lock`, ví dụ treo thật (timeout), livelock/starvation nhắc ngắn, cách tìm bằng gdb/TSan, thiết kế tránh khóa lồng |
| 27 | `27-condition-variable.md` | `std::condition_variable`, chờ có điều kiện (predicate), spurious wakeup, `notify_one/all`, mẫu producer-consumer với hàng đợi, vì sao không dùng vòng `sleep` |
| 28 | `28-atomic.md` | `std::atomic<int>`, `fetch_add`, `compare_exchange`, atomic vs mutex (khi nào dùng cái nào), cờ dừng `atomic<bool>`, memory order chỉ nhắc (mặc định seq_cst), lock-free sơ lược, ABA chỉ tên |
| 29 | `29-async-future.md` | `std::async`, `std::future::get`, `std::promise`, `packaged_task` (nhắc), ném ngoại lệ qua future, `std::launch`, so với channel/goroutine của Go |
| 30 | `30-thread-pool-hieu-nang.md` | Thread pool tự cài (hàng đợi công việc + condition_variable + dừng sạch), số luồng ≈ số lõi, chi phí tạo luồng, false sharing, Amdahl, đo thật; câu hỏi phỏng vấn tổng hợp đa luồng |

Mỗi task = một bài, tuần tự. Mỗi bài qua một vòng review "người học" (lens: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/lesson-review-lens-v2.md`), sửa tối đa 3 vòng. Sau Bài 30: cập nhật `docs/index.md`, rà soát cả nhóm bằng reviewer mạnh nhất, sửa, đẩy lên và báo người dùng.
