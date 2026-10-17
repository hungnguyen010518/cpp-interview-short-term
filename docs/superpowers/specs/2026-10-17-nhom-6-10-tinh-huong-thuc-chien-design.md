# Thiết kế: Nhóm 6–10 — tình huống, đa luồng chiều sâu và thực chiến phỏng vấn

Ngày: 2026-10-17 · Trạng thái: người dùng duyệt phương án làm đủ 38 bài (84 bài toàn khóa), push theo từng nhóm.

## Vì sao thêm
Phản hồi sau khi đi phỏng vấn: khóa cơ bản dạy tốt "cái này là gì" nhưng phỏng vấn hỏi **tình huống** ("tiến trình khác luồng ở chỗ nào, khi nào chọn cái nào", "khi nào `weak_ptr`, khi nào `shared_ptr`/`unique_ptr`", "vector khác map chỗ nào, chọn cái nào"), hỏi sâu tới bản chất, và hay ra **bài tập đa luồng** viết trên bảng trắng. Khảo sát repo cho thấy chưa có: tiến trình/`fork`/IPC, `enable_shared_from_this`, `shared_ptr` trong đa luồng, semaphore/latch/barrier, memory model sâu, LRU cache, concurrent map, bài tập đa luồng kiểu phỏng vấn.

## Phạm vi: 5 nhóm, 38 bài (Bài 47–84)
| Nhóm | Bài | Chủ đề |
|---|---|---|
| 6 — Hệ điều hành và tiến trình | 47–50 | tiến trình vs luồng, fork/exec/wait, IPC, I/O và event loop |
| 7 — Chọn đúng công cụ | 51–58 | smart pointer, container, đồng bộ, API, lỗi, bộ nhớ nâng cao: bài **tình huống** |
| 8 — Đa luồng chiều sâu | 59–64 | memory model, semaphore/latch/barrier, mẫu an toàn luồng, lock-free, jthread/coroutine, gỡ lỗi |
| 9 — Thực chiến đa luồng | 65–76 | khoảng 24 đề viết bảng trắng, có gợi ý, lời giải chạy TSan sạch, câu hỏi nối tiếp; bài 76 là bug-hunt |
| 10 — Live-coding C++ | 77–84 | tự cài unique_ptr/shared_ptr/vector/string/hash map/function, code review, tổng ôn |

## Quyết định thiết kế
- **Giữ khung 8 khối** cho mọi bài (kể cả bài thực chiến) để bộ kiểm tra hiện có chạy nguyên. Bài thực chiến diễn giải khung: 🧠 = cảnh người phỏng vấn đưa đề; 📖 = đề, gợi ý 3 bậc (khối `??? tip`), phân tích hướng giải; 💻 = lời giải đầy đủ chạy được; 🎤 = câu hỏi nối tiếp của người phỏng vấn; ⚠️ = lỗi hay mắc khi viết/nói.
- **Thứ tự viết theo số bài** (6 → 7 → 8 → 9 → 10), vì bài sau liên kết ngược bài trước và build `--strict` cấm liên kết tới bài chưa có. Đổi so với đề xuất ban đầu (Nhóm 9 trước) chỉ vì ràng buộc này.
- **Luật dạy v2 giữ nguyên** (không nhảy bước, chạy thật, quiz công bằng). Quiz ở bài tình huống hỏi "chọn cái nào, vì sao", không hỏi định nghĩa suông.
- **Kiểm tra mới:** `KIEM_TSAN=1 python3 scripts/kiem_code.py` biên dịch khối có `<thread>`/`<future>` kèm `-fsanitize=thread` (chạy dưới `setarch -R` vì kernel hiện tại làm TSan lỗi ánh xạ bộ nhớ); CI bật biến này. `scripts/kiem_mot_bai.py` kiểm nhanh từng bài khi viết.
- **Tích hợp tập trung:** nhiều agent viết song song nên mỗi agent chỉ tạo file bài và file thuật ngữ rời; người điều phối gộp `mkdocs.yml`, `tien-do.md`, `glossary.md`, `index.md` và push mỗi khi xong một nhóm.
