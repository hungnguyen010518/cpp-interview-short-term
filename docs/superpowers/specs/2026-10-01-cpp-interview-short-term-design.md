# Thiết kế: cpp-interview-short-term

Ngày: 2026-10-01 · Trạng thái: đã được người dùng duyệt (giáo trình và hướng làm)

## Mục tiêu
Khóa ôn C++ ngắn hạn (dưới 2 tuần) để ôn kiến thức C++. Người học là kỹ sư có kinh nghiệm Go và C++ ở mức hẹp, cần ôn lại toàn bộ kiến thức nền, đặc biệt C++ hiện đại, đa luồng và quản lý bộ nhớ.

Sản phẩm: một web tĩnh công khai tại `https://hungnguyen010518.github.io/cpp-interview-short-term/`, nội dung tiếng Việt, mỗi bài có trắc nghiệm tương tác. Push theo từng nhóm bài.

## Phạm vi
- Có: 19 bài chia 5 nhóm, 1 đề tổng ôn, trang Tiến độ, trang Thuật ngữ.
- Không có: code hay tên riêng của nơi làm việc (repo công khai); khóa C++ đầy đủ từ con số 0; bài tập chấm code tự động.

## Phong cách viết
- Giải thích sao cho học sinh lớp 5 cũng hiểu, giống khóa `database-tu-a-z`: mở bài bằng một câu chuyện hoặc phép ẩn dụ đời thường (cái bàn học, kho đồ, thư viện...) rồi mới tới thuật ngữ.
- Mỗi thuật ngữ tiếng Anh xuất hiện lần đầu phải kèm nghĩa tiếng Việt dễ hiểu và đưa vào trang Thuật ngữ.
- Câu ngắn, ví dụ nhỏ, một ý một đoạn. Phần "Câu hỏi phỏng vấn" mới dùng ngôn ngữ chính xác như khi trả lời trực tiếp.

## Hướng kỹ thuật
- MkDocs Material (cùng bộ với repo `database-tu-a-z`), deploy bằng GitHub Actions (`mkdocs gh-deploy`) khi push vào `main`.
- Trắc nghiệm tương tác: một file `docs/javascripts/quiz.js` đọc câu hỏi được viết trong Markdown, chấm ngay khi chọn, hiện giải thích, tính điểm cuối bài.
- Điểm từng bài lưu `localStorage`; mọi truy cập storage bọc `try/catch`, trang vẫn hiển thị đúng khi storage không dùng được.
- Trang "Tiến độ" đọc điểm từ `localStorage`, liệt kê bài chưa làm hoặc dưới 70%.

## Cấu trúc một bài
1. 🎯 Mục tiêu (3 gạch đầu dòng)
2. 🧠 Câu chuyện mở đầu (phép ẩn dụ cho học sinh lớp 5)
3. 📖 Giải thích
4. 💻 Ví dụ code
5. 🎤 Câu hỏi phỏng vấn hay gặp, có gợi ý trả lời
6. ⚠️ Lỗi và bẫy thường gặp
7. ✍️ Trắc nghiệm 6–8 câu, mỗi câu 3–4 lựa chọn, đúng 1 đáp án và có giải thích
8. 🔑 Tóm tắt đúng 5 dòng

Cú pháp trắc nghiệm trong Markdown: mỗi câu là một khối `<div class="cau-hoi" data-dap-an="N" markdown>` (N là số thứ tự đáp án đúng, tính từ 1), các lựa chọn là danh sách gạch đầu dòng, lời giải thích nằm trong `<p class="giai-thich" markdown>` và chỉ hiện sau khi chọn.

## Giáo trình
OOP và Design Patterns được xếp sau (theo yêu cầu "OOP sau một tý"): người học đã quen bộ nhớ, STL và đa luồng rồi mới học.

| Nhóm | Bài |
|---|---|
| 1. Nền tảng và bộ nhớ | 1 Stack/heap, con trỏ, tham chiếu, const · 2 RAII và smart pointer · 3 Move semantics, rule of 0/3/5 · 4 Tính năng C++11/14/17 · 5 Memory leak, dangling, UB, ASan/Valgrind |
| 2. STL và thuật toán | 6 Container và độ phức tạp, iterator invalidation · 7 Algorithm và lambda · 8 Cấu trúc dữ liệu và thuật toán hay hỏi |
| 3. Đa luồng | 9 thread, mutex, lock · 10 condition_variable, producer-consumer · 11 atomic, async/future · 12 Deadlock và race condition · 13 Thread pool và hiệu năng |
| 4. OOP và Design Patterns | 14 OOP, virtual, vtable, object slicing · 15 Template cơ bản · 16 Design patterns hay hỏi (Singleton, Factory, Observer, Strategy) |
| 5. Hệ thống và quy trình | 17 Linux (gdb, CMake, perf), Git · 18 Socket, REST, gRPC, TCP/UDP · 19 Database, SDLC, nguyên lý game dev |
| Tổng ôn | Đề trắc nghiệm trộn từ mọi bài, cộng câu hỏi về dự án thực tế (cách kể STAR, không tên riêng) |

Bài 19 gộp ba chủ đề bổ sung (database, SDLC, game).

## Kiểm tra chất lượng
- CI biên dịch và chạy mọi khối ```` ```cpp ```` trong `docs/` bằng `g++ -std=c++17 -pthread`; khối nào lỗi thì chặn deploy. Khối chủ ý minh họa hành vi không xác định (UB) bắt đầu bằng dòng `// bo-qua-kiem-tra` và được bỏ qua.
- Script kiểm tra cấu trúc: mỗi bài đủ 8 khối theo đúng thứ tự; mỗi câu trắc nghiệm có đúng 1 đáp án đúng và có giải thích.
- Nội dung lý thuyết do Claude soạn, chỉ kiểm chứng được phần code biên dịch và chạy; người học báo bài nghi ngờ để sửa.

## Quy trình giao việc
Mỗi nhóm bài: viết, chạy kiểm tra cục bộ (`mkdocs build --strict`, biên dịch code, kiểm tra cấu trúc), commit, push. Repo GitHub `hungnguyen010518/cpp-interview-short-term` (công khai) được tạo khi push nhóm 1.

## Điều chỉnh lần 2 (2026-10-01): dạy lại phần con trỏ, RAII, smart pointer từ gốc
Sau khi xuất bản Nhóm 1, người học phản hồi: các bài về con trỏ, RAII và smart pointer "dạy hổng nhiều, không hiểu gì". Nguyên nhân: nhảy bước và dùng thuật ngữ trước khi giải thích. Quyết định:
- Thay hai bài cũ bằng 9 bài dạy từ gốc (bộ nhớ và địa chỉ → stack/heap/static → con trỏ ×2 → tham chiếu/const → new/delete → RAII → unique_ptr → shared_ptr/weak_ptr); ba bài cũ còn lại đổi thành Bài 10–12.
- Mọi bài theo "luật dạy v2": không dùng thuật ngữ/cú pháp trước khi giải thích; mỗi đoạn code có bảng "chạy từng dòng", hình vẽ bộ nhớ và kết quả chạy thật; cầu nối từ Go (người học đã quen Go: `defer`, `*T`, escape analysis); câu hỏi trắc nghiệm công bằng (đáp án đúng không dài hơn hẳn, rải đều vị trí, có câu đọc code).
- Đánh số bài là số toàn khóa liên tục (01, 02, …), không bắt đầu lại ở mỗi nhóm; `data-bai` bằng tiền tố `NN-` của tên file.
- Các bài cũ (Bài 10–12) sẽ được rà lại theo luật dạy v2 ở một đợt sau; các nhóm 2–5 viết theo luật này.
