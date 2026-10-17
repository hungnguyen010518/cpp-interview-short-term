# C++ phỏng vấn — ôn nhanh

Chào bạn! Đây là khóa ôn C++ trong **chưa đầy hai tuần** để đi phỏng vấn.

Mỗi bài được viết như kể chuyện: bắt đầu bằng một ví dụ đời thường (cái bàn học,
cái kho đồ, thư viện...) rồi mới tới tên gọi của các khái niệm. Học sinh lớp 5 đọc cũng hiểu.

## Một bài học gồm gì?

1. 🎯 Mục tiêu bài
2. 🧠 Câu chuyện mở đầu
3. 📖 Giải thích
4. 💻 Ví dụ code (chạy được thật)
5. 🎤 Câu hỏi phỏng vấn hay gặp, có gợi ý trả lời
6. ⚠️ Lỗi thường gặp
7. ✍️ Trắc nghiệm: chọn xong thấy đúng sai ngay, kèm giải thích
8. 🔑 Tóm tắt năm dòng

## Học theo thứ tự nào?

Hãy học **Nhóm 1 — Nền tảng và bộ nhớ** từ [Bài 1](nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) đến [Bài 15](nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md), đúng thứ tự. Nhóm này có 15 bài, đi từ "bộ nhớ là gì" đến smart pointer, move semantics, C++11, C++14/17 và công cụ bắt lỗi. Cả 15 bài đều được viết theo kiểu "dạy từ gốc": đi từng bước, có ví dụ chạy thật và trắc nghiệm.

Sau đó học **Nhóm 2 — STL và thuật toán** từ [Bài 16](nhom-2-stl-thuat-toan/16-vector.md) đến [Bài 23](nhom-2-stl-thuat-toan/23-thuat-toan-hay-hoi.md): vector, string, map/set, iterator, thuật toán và lambda, Big-O, cấu trúc dữ liệu và các thuật toán hay hỏi.

Tiếp theo là **Nhóm 3 — Đa luồng** từ [Bài 24](nhom-3-da-luong/24-thread-co-ban.md) đến [Bài 30](nhom-3-da-luong/30-thread-pool-hieu-nang.md): thread, mutex, deadlock, condition_variable, atomic, async/future và thread pool.

Rồi đến **Nhóm 4 — OOP, template và Design Patterns** từ [Bài 31](nhom-4-oop-patterns/31-lop-dong-goi.md) đến [Bài 37](nhom-4-oop-patterns/37-solid-thiet-ke.md): lớp và đóng gói, kế thừa, đa hình/virtual, template, Singleton/Factory, Observer/Strategy, SOLID.

Cuối cùng là **Nhóm 5 — Hệ thống, công cụ gỡ lỗi và quy trình** từ [Bài 38](nhom-5-he-thong-quy-trinh/38-bien-dich-lien-ket-build.md) đến [Bài 46](nhom-5-he-thong-quy-trinh/46-tong-on-debug-phong-van.md): biên dịch và liên kết, gdb, core dump, sanitizer, strace/perf, Git, mạng, database/quy trình/game, và bài tổng ôn về cách gỡ lỗi khi phỏng vấn.

Khi đã quen kiến thức nền, học phần **chuyên sâu cho phỏng vấn tình huống**, nơi người phỏng vấn hỏi "gặp tình huống này thì chọn gì, vì sao":

- **Nhóm 6 — Hệ điều hành và tiến trình** (Bài 47–50): [tiến trình và luồng](nhom-6-he-dieu-hanh-tien-trinh/47-tien-trinh-vs-luong.md), `fork`/`exec`/`wait`, giao tiếp giữa các tiến trình (IPC), I/O chặn và `epoll`.
- **Nhóm 7 — Chọn đúng công cụ** (Bài 51–58): [chọn smart pointer](nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md), smart pointer và container trong đa luồng, chọn container, thiết kế hàm và sở hữu, xử lý lỗi, chọn cơ chế đồng bộ, bộ nhớ nâng cao.

- **Nhóm 8 — Đa luồng chiều sâu** (Bài 59–64): [memory model](nhom-8-da-luong-chieu-sau/59-memory-model.md), semaphore/latch/barrier, mẫu thiết kế an toàn luồng, lock-free cơ bản, `jthread` và coroutine, gỡ lỗi đa luồng.

- **Nhóm 9 — Thực chiến phỏng vấn đa luồng** (Bài 65–76): các đề viết trên bảng trắng có gợi ý, lời giải chạy được và câu hỏi nối tiếp: [in chẵn lẻ và ABC](nhom-9-thuc-chien-da-luong/65-in-chan-le-abc.md), hàng đợi chặn, thread pool tự viết, khởi tạo một lần, semaphore và barrier tự cài, khóa đọc-ghi, LRU cache, concurrent hash map, event bus, bộ hẹn giờ, chia việc song song, và bài tìm lỗi [12 đoạn code đa luồng](nhom-9-thuc-chien-da-luong/76-bug-hunt.md).

- **Nhóm 10 — Live-coding C++ tổng hợp** (Bài 77–84): tự cài [unique_ptr](nhom-10-live-coding/77-tu-cai-unique-ptr.md), shared_ptr/weak_ptr, vector, string, hash map, `std::function`; [code review tìm lỗi trong 15 đoạn C++](nhom-10-live-coding/83-code-review-bug.md); và bài [tổng ôn 100 câu hỏi nhanh](nhom-10-live-coding/84-tong-on-100-cau.md) cùng ba mini thiết kế hệ thống.

Điểm trắc nghiệm của bạn được lưu **ngay trong trình duyệt này** (không gửi đi đâu cả).
Xem bạn đang yếu bài nào ở trang [Tiến độ](tien-do.md).
