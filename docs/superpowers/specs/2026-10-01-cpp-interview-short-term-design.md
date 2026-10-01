# Thiết kế: cpp-interview-short-term

Ngày: 2026-10-01 · Trạng thái: đã được người dùng duyệt (giáo trình và hướng làm)

## Mục tiêu
Khóa ôn C++ ngắn hạn (dưới 2 tuần) để phỏng vấn vị trí C++ theo hai JD đã cho. Người học là kỹ sư có kinh nghiệm Go và C++ ở mức hẹp, cần ôn lại toàn bộ kiến thức nền, đặc biệt C++ hiện đại, đa luồng và quản lý bộ nhớ.

Sản phẩm: một web tĩnh công khai tại `https://hungnguyen010518.github.io/cpp-interview-short-term/`, nội dung tiếng Việt, mỗi bài có trắc nghiệm tương tác. Push theo từng nhóm bài.

## Phạm vi
- Có: 19 bài chia 5 nhóm, 1 đề tổng ôn, trang Tiến độ, trang Thuật ngữ.
- Không có: code hoặc tên khách hàng của công ty (repo công khai); khóa C++ đầy đủ từ con số 0; bài tập chấm code tự động.

## Hướng kỹ thuật
- MkDocs Material (cùng bộ với repo `database-tu-a-z`), deploy bằng GitHub Actions (`mkdocs gh-deploy`) khi push vào `main`.
- Trắc nghiệm tương tác: một file `docs/javascripts/quiz.js` đọc câu hỏi được viết trong Markdown, chấm ngay khi chọn, hiện giải thích, tính điểm cuối bài.
- Điểm từng bài lưu `localStorage`; mọi truy cập storage bọc `try/catch`, trang vẫn hiển thị đúng khi storage không dùng được.
- Trang "Tiến độ" đọc điểm từ `localStorage`, liệt kê bài chưa làm hoặc dưới 70%.

## Cấu trúc một bài
1. Mục tiêu (3 gạch đầu dòng)
2. Giải thích kèm ví dụ code
3. Câu hỏi phỏng vấn hay gặp, có đáp án mẫu
4. Lỗi và bẫy thường gặp
5. Trắc nghiệm 6–8 câu, mỗi câu đúng 1 đáp án và có giải thích
6. Tóm tắt

## Giáo trình
| Nhóm | Bài |
|---|---|
| 1. Nền tảng và bộ nhớ | 1 Stack/heap, con trỏ, tham chiếu, const · 2 RAII và smart pointer · 3 Move semantics, rule of 0/3/5 · 4 Tính năng C++11/14/17 · 5 Memory leak, dangling, UB, ASan/Valgrind |
| 2. OOP và Design Patterns | 6 OOP, virtual, vtable, object slicing · 7 Template cơ bản · 8 Design patterns hay hỏi (Singleton, Factory, Observer, Strategy) |
| 3. STL và thuật toán | 9 Container và độ phức tạp, iterator invalidation · 10 Algorithm và lambda · 11 Cấu trúc dữ liệu và thuật toán hay hỏi |
| 4. Đa luồng | 12 thread, mutex, lock · 13 condition_variable, producer-consumer · 14 atomic, async/future · 15 Deadlock và race condition · 16 Thread pool và hiệu năng |
| 5. Hệ thống và quy trình | 17 Linux (gdb, CMake, perf), Git · 18 Socket, REST, gRPC, TCP/UDP · 19 Database, SDLC, nguyên lý game dev |
| Tổng ôn | Đề trắc nghiệm trộn từ mọi bài, cộng câu hỏi về dự án thực tế (cách kể STAR, không tên khách hàng) |

Bài 19 gộp ba chủ đề của JD2 (database, SDLC, game).

## Kiểm tra chất lượng
- CI biên dịch mọi khối code C++ trong `docs/` bằng `g++ -std=c++17 -pthread`; khối nào lỗi thì chặn deploy. Khối chủ ý minh họa lỗi phải đánh dấu rõ và được bỏ qua.
- Script kiểm tra cấu trúc: mỗi bài đủ 6 mục; mỗi câu trắc nghiệm có đúng 1 đáp án đúng và có giải thích.
- Nội dung lý thuyết do Claude soạn, chỉ kiểm chứng được phần code biên dịch và chạy; người học báo bài nghi ngờ để sửa.

## Quy trình giao việc
Mỗi nhóm bài: viết, chạy kiểm tra cục bộ (`mkdocs build --strict`, biên dịch code, kiểm tra cấu trúc), commit, push. Repo GitHub `hungnguyen010518/cpp-interview-short-term` (công khai) được tạo khi push nhóm 1.
