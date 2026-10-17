# Bài 84 — Tổng ôn: 100 câu hỏi nhanh và thiết kế hệ thống nhỏ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Trả lời nhanh, đúng và ngắn khoảng 100 câu hỏi hay gặp ở mười chủ đề (bộ nhớ, smart pointer, move/copy, STL, thuật toán, đa luồng, OOP, hệ điều hành, công cụ, thiết kế), và với mỗi câu biết quay về **bài nào** để đọc lại phần gốc.
    - Dùng một khuôn trả lời cố định (đáp thẳng, giải thích cơ chế, nêu giá phải trả, kiểm tra biên) cùng các thói quen phỏng vấn: nói to suy nghĩ, hỏi lại đề, nêu trade-off (đánh đổi: chọn cách này thì được gì, mất gì), và biết nói gì khi không biết.
    - Vẽ và nói được ba hệ thống nhỏ ở bảng trắng: logger đa luồng bất đồng bộ (kèm code chạy được, TSan sạch), object pool (kèm code), task scheduler (ghép các bài đã học); mỗi cái có yêu cầu, thành phần, luồng dữ liệu, điểm đồng bộ, rủi ro.
    - Tự lập kế hoạch ôn: câu nào còn nói vấp thì đọc lại bài gốc, đề live-coding nào còn chậm thì luyện ở bài tương ứng.

**Bạn cần biết trước:** toàn bộ Bài 01–82 (câu hỏi nhanh chủ yếu lấy từ Bài 01–76, bài tự cài lấy từ [Bài 77](77-tu-cai-unique-ptr.md)–82); bài này không dạy khái niệm mới mà **hệ thống hóa** chúng. Ba phần dùng nhiều nhất: [Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md) (hàng đợi chặn), [Bài 67](../nhom-9-thuc-chien-da-luong/67-thread-pool-tu-viet.md) (thread pool tự viết), [Bài 74](../nhom-9-thuc-chien-da-luong/74-timer-rate-limiter.md) (bộ hẹn giờ).

## 🧠 Câu chuyện mở đầu

Sáng thứ Hai, bạn ngồi vào phòng phỏng vấn. Người hỏi mở màn bằng loạt câu nhanh: "`unique_ptr` sao không copy được? `vector` đầy thì sao? `fork` ba lần in mấy dòng?" Mỗi câu chỉ cho bạn mười giây. Rồi anh ấy đẩy tờ giấy trắng qua: "Thiết kế giúp tôi một logger cho chương trình nhiều luồng."

Trong **xưởng tự lắp đồ** của nhóm này, 83 bài trước là tháo từng cái máy ra xem bánh răng. Hôm nay là buổi kiểm tra cuối: người chấm không hỏi bạn thuộc bao nhiêu bánh răng, mà hỏi bạn **ráp được cái máy nào ra hồn** và nói được vì sao chọn bánh răng đó. Câu hỏi nhanh thử độ chắc của từng bánh răng; bài thiết kế thử khả năng ráp.

!!! info "Chỗ nào ví von xưởng không còn đúng?"
    Trong xưởng, máy ráp xong là xong. Ở phòng phỏng vấn, người chấm còn nghe **cách bạn nghĩ**: im lặng ráp đúng vẫn có thể bị chấm thấp hơn người vừa nói vừa ráp sai một chỗ rồi tự sửa. Vì vậy nửa đầu bài này dạy cách nói, nửa sau mới là nội dung.

## 📖 Giải thích

### Khuôn một câu trả lời tốt: bốn nhịp

Với câu hỏi "X là gì / khác Y thế nào", trả lời theo bốn nhịp, mỗi nhịp một hai câu. Dừng ở nhịp nào tùy thời gian người hỏi cho; nhịp 1 luôn phải có.

| Nhịp | Nói gì | Ví dụ cho "vì sao `wait` cần vị từ?" |
|---|---|---|
| 1. Đáp thẳng | Một câu trả lời đúng | "Vì `wait` có thể dậy mà điều kiện chưa đúng." |
| 2. Cơ chế | Vì sao đúng | "Chuẩn cho phép spurious wakeup, và luồng khác có thể lấy mất món trước khi mình xin lại khóa." |
| 3. Giá / khi nào KHÔNG | Điều kiện đúng-sai, chi phí | "Vị từ phải đọc biến đổi dưới cùng mutex, không thì có thể lost wakeup." |
| 4. Biên hoặc ví dụ | Một trường hợp thử | "Hàng rỗng và đã đóng thì sao: vị từ phải có cả hai vế." |

### Năm thói quen khi ngồi bảng trắng

| Thói quen | Làm gì | Câu mẫu |
|---|---|---|
| Nói to suy nghĩ | Nói **trước khi** viết; sai thì sửa thành tiếng | "Em nghĩ có hai điều kiện chờ, nên em sẽ dùng hai `condition_variable`." |
| Hỏi lại đề | Chốt ràng buộc trước khi vẽ (bảng bên dưới) | "Hàng đầy thì chặn người gọi hay bỏ dòng log ạ?" |
| Nêu trade-off | Mỗi lựa chọn đi kèm giá và điều kiện đổi ý | "Em chọn mutex vì dễ đúng; nếu đo thấy là nút cổ chai em mới xét SPSC." |
| Kiểm tra biên | Rỗng, một phần tử, `N = 0`, dừng giữa chừng, nhiều luồng | "Còn trường hợp đóng logger khi hàng còn dòng chưa ghi." |
| Khi không biết | Nói thật, suy từ nguyên lý, nêu cách kiểm chứng | "Em chưa dùng cái này. Em đoán nó hoạt động như X vì Y; em sẽ viết thử và chạy dưới sanitizer để kiểm." |

Đừng bịa. Người phỏng vấn thường hỏi tiếp đúng chỗ bạn bịa, và "em không chắc, nhưng suy ra là..." được điểm hơn một câu trả lời tự tin mà sai. Cũng đừng nói "chạy 100 lần đều đúng" như một bằng chứng: [Bài 70](../nhom-9-thuc-chien-da-luong/70-rwlock-dining.md) và [Bài 74](../nhom-9-thuc-chien-da-luong/74-timer-rate-limiter.md) đều có ca chạy đẹp mà vẫn sai.

**Câu nên hỏi lại, theo loại đề:**

| Loại đề | Hỏi lại |
|---|---|
| Cấu trúc dữ liệu / thuật toán | Kích thước `n`? Dữ liệu đã sắp chưa? Có trùng không? Cần tối ưu thời gian hay bộ nhớ? |
| Đa luồng | Mấy producer, mấy consumer? Có cần giữ thứ tự? Mất dữ liệu được không? Đầy thì chặn hay bỏ? |
| Thiết kế lớp | Ai sở hữu, vòng đời ra sao? Có cần đa hình lúc chạy? Chuẩn C++ nào? |
| "Hệ thống X" | Quy mô (kết nối, dòng/giây)? Một máy hay nhiều? Độ trễ hay thông lượng quan trọng hơn? |

### Cách dùng bài này

Vòng 1: che cột đáp, nói to từng câu rồi mới nhìn đáp; đánh dấu câu nói vấp. Vòng 2: chỉ làm lại câu đã đánh dấu, đọc phần gốc ở bài ghi sau dấu mũi tên. Vòng 3: chọn ngẫu nhiên 10 câu, nói với một người (hay với gương) và bấm giờ: mỗi câu dưới 30 giây.

Đề live-coding và bài luyện tương ứng (tên bài trong ngoặc là tiêu đề trong lộ trình):

| Đề hay gặp | Luyện ở |
|---|---|
| In chẵn lẻ, in ABC xoay vòng | [Bài 65](../nhom-9-thuc-chien-da-luong/65-in-chan-le-abc.md) |
| Hàng đợi chặn, producer-consumer | [Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md) |
| Thread pool trả `future`, dừng êm | [Bài 67](../nhom-9-thuc-chien-da-luong/67-thread-pool-tu-viet.md) |
| Singleton an toàn luồng, khởi tạo một lần | [Bài 68](../nhom-9-thuc-chien-da-luong/68-singleton-call-once.md) |
| Tự cài semaphore, barrier | [Bài 69](../nhom-9-thuc-chien-da-luong/69-semaphore-barrier-tu-cai.md) |
| Khóa đọc-ghi, triết gia ăn tối | [Bài 70](../nhom-9-thuc-chien-da-luong/70-rwlock-dining.md) |
| LRU cache, concurrent hash map | [Bài 71](../nhom-9-thuc-chien-da-luong/71-lru-cache.md), [Bài 72](../nhom-9-thuc-chien-da-luong/72-concurrent-hashmap.md) |
| Event bus, bộ hẹn giờ, giới hạn tốc độ | [Bài 73](../nhom-9-thuc-chien-da-luong/73-event-bus.md), [Bài 74](../nhom-9-thuc-chien-da-luong/74-timer-rate-limiter.md) |
| Tổng, merge sort, đếm từ song song | [Bài 75](../nhom-9-thuc-chien-da-luong/75-parallel-sum-sort-wordcount.md) |
| Tìm lỗi trong code đa luồng / trong code C++ | [Bài 76](../nhom-9-thuc-chien-da-luong/76-bug-hunt.md), [Bài 83](83-code-review-bug.md) (code review: tìm lỗi trong 15 đoạn C++) |
| Tự cài `unique_ptr`, `shared_ptr`, `vector`, `string` | [Bài 77](77-tu-cai-unique-ptr.md) (tự cài unique_ptr), [Bài 78](78-tu-cai-shared-ptr.md) (tự cài shared_ptr và weak_ptr), [Bài 79](79-tu-cai-vector.md) (tự cài vector), [Bài 80](80-tu-cai-string.md) (tự cài string) |
| Tự cài hash map, `std::function` | [Bài 81](81-tu-cai-hashmap.md) (tự cài hash map), [Bài 82](82-tu-cai-function.md) (tự cài std::function và type erasure) |

## 💻 Ví dụ code

### Phần 1: 100 câu hỏi đáp nhanh

Mỗi đáp ngắn đủ để nói ra trong 20 đến 30 giây. Quy ước: "UB" là hành vi không xác định (Bài 15); "→ Bài N" là nơi có phần giải thích đầy đủ. Các con số đo thời gian cố ý không nằm ở đây: chúng đổi theo máy và `-O`, hãy xem ở bài gốc.

#### A. Bộ nhớ và con trỏ

| # | Hỏi | Đáp |
|---|---|---|
| 1 | Stack khác heap thế nào? | Stack chứa biến cục bộ, mỗi lần gọi hàm một khung, nhỏ, tự dọn khi ra khỏi khối; heap xin bằng `new`, sống tới khi tự trả, quên là rò rỉ. → Bài 02 |
| 2 | Global và `static` cục bộ sống bao lâu, dựng khi nào? | Ở vùng tĩnh, sống suốt chương trình; global thường dựng trước `main`, `static` cục bộ dựng ở lần chạy qua đầu tiên (an toàn luồng từ C++11). → Bài 02, 35 |
| 3 | Thứ tự khởi tạo global giữa hai file `.cpp`? | Không xác định (static initialization order fiasco); tránh bằng `static` cục bộ trong hàm. → Bài 02 |
| 4 | Con trỏ khác tham chiếu thế nào? | Tham chiếu là biệt danh: gắn lúc khai báo, không rỗng, không gắn lại (`b = c` là gán giá trị); con trỏ có thể `nullptr` và đổi chỗ trỏ. → Bài 06 |
| 5 | `const int*`, `int* const`, `const int* const`? | Đọc từ phải sang trái: con trỏ tới int hằng (khóa giá trị), con trỏ hằng tới int (khóa con trỏ), khóa cả hai. → Bài 06 |
| 6 | `new`/`delete` khác `malloc`/`free`? | `new` xin chỗ rồi chạy hàm tạo, `delete` chạy hàm hủy rồi trả; `malloc`/`free` không chạy hàm tạo/hủy; phải đúng cặp (`new[]` với `delete[]`), trộn là UB. → Bài 07 |
| 7 | Ba lỗi kinh điển của `new`/`delete`, cái nào là UB? | Rò rỉ (không phải UB, im lặng), dùng sau khi trả, giải phóng hai lần (hai cái sau là UB). → Bài 07 |
| 8 | RAII là gì, vì sao hơn `delete` tay? | Xin tài nguyên ở hàm tạo, trả ở hàm hủy; hàm hủy biến cục bộ chạy cuối khối kể cả khi `return` sớm hay ném ngoại lệ, còn `delete` viết tay bị nhảy qua. → Bài 08 |
| 9 | UB là gì, cho ví dụ? | Chuẩn không quy định kết quả (đúng, sai âm thầm hay sập): ngoài biên mảng, dùng sau khi trả, tràn số nguyên có dấu, giải tham chiếu `nullptr`, đọc biến chưa khởi tạo, data race. → Bài 15 |
| 10 | "Chạy đúng ở máy tôi" chứng minh được gì? | Không gì cả: UB đổi theo trình biên dịch, cờ tối ưu, máy; công cụ chỉ thấy lỗi xảy ra trong lần chạy đó. → Bài 15, 41 |
| 11 | False sharing là gì? | Hai biến khác nhau chung một dòng cache (thường 64 byte) bị hai luồng ghi: chậm dù không có data race; gỡ bằng `alignas(64)`. → Bài 30, 58 |

#### B. Smart pointer

| # | Hỏi | Đáp |
|---|---|---|
| 12 | Vì sao `unique_ptr` không sao chép được? | Sao chép sẽ tạo hai chủ cùng `delete` một chỗ nên hàm tạo sao chép bị xóa; chuyển bằng `std::move`, nguồn thành `nullptr` (chuẩn bảo đảm). → Bài 09 |
| 13 | Hàm nhận và trả `unique_ptr` thế nào? | Chỉ dùng thì nhận `const T&`/`T*`; cần sở hữu thì nhận `unique_ptr` theo giá trị, nơi gọi viết `std::move`; trả từ hàm không cần `std::move`. → Bài 09, 55 |
| 14 | `shared_ptr` đếm tham chiếu ở đâu? | Ở khối điều khiển dùng chung (đếm mạnh và đếm yếu); sao chép +1, hủy −1, đếm mạnh về 0 thì hủy đối tượng; `make_shared` thường xin heap một lần cho cả hai. → Bài 10, 51 |
| 15 | Vòng tham chiếu là gì, chữa sao? | Hai đối tượng giữ `shared_ptr` của nhau: đếm không về 0, hàm hủy không chạy (rò rỉ); đổi một chiều thành `weak_ptr`. → Bài 10 |
| 16 | Dùng `weak_ptr::lock()` thế nào? | `if (auto sp = w.lock())`: rỗng nghĩa là đã hủy; đừng `expired()` rồi mới `lock()` vì giữa hai bước đối tượng có thể chết. → Bài 10, 52 |
| 17 | `shared_ptr` an toàn luồng tới đâu? | Ba tầng: bộ đếm nguyên tử (an toàn), đối tượng được trỏ tới (không tự an toàn), biến `shared_ptr` (nhiều luồng đọc ổn, có luồng ghi là data race). → [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) |
| 18 | Chọn smart pointer thế nào? | Hỏi "ai sở hữu": một chủ thì `unique_ptr` (mặc định), nhiều chủ thật thì `shared_ptr`, chỉ dùng tạm thì `const T&`/`T*`, nhìn lâu mà chủ có thể chết trước thì `weak_ptr`. → [Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md) |
| 19 | Callback gửi sang luồng khác có nên bắt `this` hay `[&]`? | Không, vì chủ có thể chết trước: bắt `weak_ptr` ("chủ chết thì bỏ qua") hoặc `shared_ptr` ("giữ chủ sống tới khi xong"). → [Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md) |

#### C. Move và copy

| # | Hỏi | Đáp |
|---|---|---|
| 20 | Sao chép nông khác sâu thế nào? | Mặc định chép từng thành viên: con trỏ thô thì chép địa chỉ nên hai đối tượng cùng giữ một vùng (hủy hai lần); sâu thì xin vùng mới và chép nội dung. → Bài 11 |
| 21 | Rule of 3? | Tự viết một trong hàm hủy, hàm tạo sao chép, phép gán sao chép thì thường cần viết cả ba. → Bài 11 |
| 22 | lvalue khác rvalue? | lvalue có tên, dùng lại được ở dòng sau; rvalue là giá trị tạm sắp biến mất (kết quả hàm, `x + 1`). → Bài 12 |
| 23 | `std::move` làm gì? | Không di chuyển gì cả, chỉ ép thành rvalue; hàm tạo/gán di chuyển mới làm việc, không có thì rơi về sao chép. → Bài 12 |
| 24 | Sau khi move, đối tượng còn dùng được không? | Chỉ nên hủy hoặc gán lại (kiểu chuẩn: hợp lệ nhưng không xác định); riêng `unique_ptr`/`shared_ptr` được bảo đảm rỗng. → Bài 12 |
| 25 | Rule of 5 và Rule of 0? | Lớp tự quản lý tài nguyên thì quyết định cả năm hàm đặc biệt; Rule of 0: dùng thành viên tự quản lý (`vector`, `unique_ptr`) và không viết hàm nào. → Bài 12 |
| 26 | Vì sao hàm tạo di chuyển nên `noexcept`? | `vector` chỉ chuyển khi tăng khối nếu move `noexcept` (để giữ bảo đảm mạnh), không thì sao chép (với kiểu chép được). → Bài 12, 56 |

#### D. STL và container

| # | Hỏi | Đáp |
|---|---|---|
| 27 | `size` khác `capacity`; `reserve` khác `resize`? | `size` là số phần tử có, `capacity` là số chỗ đã xin; `reserve` đổi capacity (không tạo phần tử), `resize` đổi size. → Bài 16 |
| 28 | `push_back` khi vector đầy thì sao? | Tái cấp phát sang mảng lớn hơn và chuyển phần tử; tham chiếu, con trỏ, iterator cũ hỏng; vẫn amortized O(1). → Bài 16, 19, 21 |
| 29 | Bẫy của `vector<bool>`? | Nén thành bit, trả đối tượng đại diện; hai luồng ghi hai phần tử khác nhau vẫn là data race; cần `bool` thường thì dùng `vector<char>`. → Bài 16, 54 |
| 30 | `string_view` treo khi nào? | Nó chỉ là cửa sổ (địa chỉ, độ dài), không sở hữu; treo khi chuỗi gốc chết hay đổi chỗ; dùng làm tham số, đừng cất hay trả về. → Bài 17 |
| 31 | `map` khác `unordered_map`? | `map` là cây cân bằng: O(log n), có thứ tự, truy vấn khoảng; `unordered_map` là bảng băm: O(1) trung bình, O(n) xấu nhất, không thứ tự. → Bài 18, 53 |
| 32 | Bẫy của `m[k]`? | Khóa chưa có thì **chèn** giá trị mặc định; muốn chỉ hỏi thì dùng `find`/`count`/`at`. → Bài 18 |
| 33 | Iterator của từng container hỏng khi nào? | `vector` tái cấp phát hỏng tất cả; `deque` chèn giữa hỏng tất cả; `list`/`map` chỉ hỏng cái bị xóa; `unordered_*` rehash hỏng iterator (tham chiếu vẫn sống). → Bài 19 |
| 34 | Xóa phần tử khi đang duyệt? | `it = c.erase(it)` và chỉ `++it` khi không xóa; xóa nhiều ở `vector` thì remove-erase. → Bài 19, 20 |
| 35 | Chọn container mặc định nào? | `vector`; hai đầu thì `deque`, địa chỉ ổn định thì `list`, tra theo khóa thì `unordered_map`, cần thứ tự thì `map`; đổi khi có lý do và đã đo. → [Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md), 17 |

#### E. Thuật toán và Big-O

| # | Hỏi | Đáp |
|---|---|---|
| 36 | Big-O là gì? | Số bước tăng theo `n`: giữ số hạng lớn nhất, bỏ hằng số; O(1) là "không đổi" chứ không phải "nhanh". → Bài 21 |
| 37 | Vì sao `unordered_map` O(1) mà vẫn có thể O(n)? | Trung bình mỗi hộp ngắn nhờ hệ số tải và rehash; xấu nhất mọi khóa cùng một hộp (hàm băm tệ). → Bài 22, 53 |
| 38 | Tìm nhị phân cần gì, viết `mid` thế nào? | Dãy đã sắp và truy cập ngẫu nhiên; `mid = lo + (hi - lo) / 2` để khỏi tràn `int`; O(log n). → Bài 23 |
| 39 | Two sum? | Dãy đã sắp: hai con trỏ O(n) thời gian, O(1) bộ nhớ; chưa sắp: `unordered_map` lưu số đã gặp, O(n) trung bình. → Bài 23 |
| 40 | Độ phức tạp các thuật toán sắp xếp? | Chèn, bubble O(n²); merge sort O(n log n) cần bộ nhớ phụ; quick sort trung bình O(n log n), xấu nhất O(n²); `std::sort` chuẩn đòi O(n log n) (từ C++11). → Bài 23 |
| 41 | Fibonacci đệ quy chậm vì sao, sửa sao? | Giải lặp lại cùng bài con nên bùng nổ O(2^n); ghi nhớ hoặc vòng lặp từ dưới lên O(n). → Bài 23 |
| 42 | Top K phần tử lớn nhất? | Min-heap giữ tối đa K số: gặp số lớn hơn đỉnh thì thay; O(n log K). → Bài 22 |

#### F. Đa luồng

| # | Hỏi | Đáp |
|---|---|---|
| 43 | Hủy `std::thread` còn joinable thì sao? | Gọi `std::terminate`; phải `join` (hoặc `detach`, hiếm khi nên), tốt nhất bọc RAII. → Bài 24 |
| 44 | Đối số truyền cho `std::thread` đi đâu? | Được sao chép vào luồng mặc định; muốn tham chiếu dùng `std::ref` (và tự bảo đảm biến sống đủ lâu); `unique_ptr` truyền bằng `std::move`. → Bài 24 |
| 45 | Data race là gì? | Hai luồng cùng truy cập một ô nhớ, ít nhất một bên ghi, không có đồng bộ giữa chúng: UB, không chỉ là "kết quả sai". → Bài 25 |
| 46 | Data race khác race condition? | Race condition là lỗi logic phụ thuộc thứ tự chạy (kiểm rồi làm giữa hai lần khóa), còn xảy ra dù không có data race. → Bài 25 |
| 47 | `lock_guard` khác `unique_lock`? | `lock_guard` khóa đến hết khối; `unique_lock` nhả và xin lại được, và bắt buộc cho `condition_variable::wait`. → Bài 25, 27 |
| 48 | Deadlock cần mấy điều kiện, tránh sao? | Bốn: loại trừ lẫn nhau, giữ-và-chờ, không bị giành lại, chờ vòng tròn; khóa theo thứ tự cố định hoặc `std::scoped_lock`. → Bài 26 |
| 49 | Vì sao `wait` phải có vị từ? | Chuẩn cho phép spurious wakeup, luồng khác có thể lấy mất món, và `notify` đến trước `wait` thì mất; `wait(lk, pred)` tương đương `while (!pred()) wait(lk)`. → Bài 27, 66 |
| 50 | `notify_one` khác `notify_all`? | `notify_one` cho một món một người; `notify_all` khi thay đổi mà mọi người phải biết (như cờ dừng). → Bài 27 |
| 51 | `atomic` bảo vệ được gì, không được gì? | Mỗi thao tác trên **một** biến không chia cắt; bất biến liên quan nhiều biến (hay `x = x + 1` viết rời) vẫn cần mutex. → Bài 28 |
| 52 | Cờ dừng dùng `bool` thường được không? | Không: data race, và ở `-O2` luồng có thể không bao giờ thấy cờ đổi; dùng `atomic<bool>`; `volatile` không thay được. → Bài 28, 59 |
| 53 | `future::get()` gọi hai lần? | Lần hai là lỗi người gọi (`get` chỉ lấy một lần); ngoại lệ ném trong tác vụ được cất và `get()` ném lại; future của `async` bị hủy thì chờ tác vụ xong. → Bài 29 |
| 54 | Vì sao dùng thread pool? | Tạo và hủy luồng đắt hơn chính việc nhỏ; pool tạo N luồng một lần, worker lấy việc, nhả khóa, **chạy ngoài khóa**; dừng êm = cờ dưới khóa, `notify_all`, `join`. → Bài 30, 67 |
| 55 | Happens-before và release/acquire? | Bảo đảm "B thấy mọi kết quả của A": ghi dữ liệu rồi `store(release)` cờ; luồng kia `load(acquire)` thấy cờ rồi đọc dữ liệu; mutex `unlock`→`lock` và `join` cũng tạo quan hệ này. → [Bài 59](../nhom-8-da-luong-chieu-sau/59-memory-model.md) |
| 56 | Chọn cơ chế đồng bộ thế nào? | Nhiều biến: `mutex`; một biến đơn: `atomic`; chờ sự kiện: `condition_variable`; một kết quả một lần: `future`; giới hạn số luồng vào: semaphore. Mutex trước, đo, rồi mới tối ưu. → [Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md), 60 |
| 57 | Lock-free có nghĩa là nhanh hơn? | Không: lock-free chỉ hứa luôn có ít nhất một luồng tiến lên; khó đúng (ABA, thu hồi bộ nhớ), nên mặc định mutex, chỉ SPSC (một producer, một consumer) khi đã đo. → [Bài 62](../nhom-8-da-luong-chieu-sau/62-lock-free-co-ban.md), 57 |
| 58 | Singleton an toàn luồng? | `static T x;` trong hàm (C++11 bảo đảm dựng một lần); cần tham số lúc chạy thì `std::call_once`; kiểm-rồi-tạo bằng con trỏ thường là sai. → Bài 35, 59, 68 |
| 59 | Amdahl nói gì? | Tăng tốc tối đa `1 / ((1 - p) + p / n)`, không vượt `1 / (1 - p)`: phần tuần tự (kể cả vùng găng) chặn trần. → Bài 30 |

#### G. OOP, virtual, template

| # | Hỏi | Đáp |
|---|---|---|
| 60 | Danh sách khởi tạo bắt buộc khi nào, thứ tự dựng? | Với thành viên `const`, tham chiếu, hay kiểu không có hàm tạo mặc định; thành viên dựng theo thứ tự **khai báo**, không theo thứ tự trong danh sách. → Bài 31 |
| 61 | `virtual` làm gì? | Không `virtual`: gọi theo kiểu khai báo của `Cha&`/`Cha*`; có `virtual`: theo món thật lúc chạy; vtable/vptr là cách cài đặt thông dụng, không phải luật. → Bài 33 |
| 62 | Vì sao lớp cha đa hình cần hàm hủy `virtual`? | Xóa qua `Cha*` mà hàm hủy không `virtual` là UB (hàm hủy của lớp con có thể không chạy). → Bài 33 |
| 63 | `override` có ích gì? | Báo lỗi biên dịch khi lệch chữ ký (như thiếu `const`); thiếu nó thì lặng lẽ thành hàm mới. → Bài 33 |
| 64 | Gọi hàm ảo trong hàm tạo/hàm hủy? | Không đa hình: chạy bản của chính lớp đó (phần con chưa dựng hay đã hủy); gọi hàm thuần ảo ở đó là UB. → Bài 33 |
| 65 | Slicing là gì, tránh sao? | Gán/truyền/chứa `vector` theo giá trị làm cắt phần con và mất đa hình; dùng tham chiếu, con trỏ, `unique_ptr`. → Bài 32, 33 |
| 66 | Kế thừa hay chứa thành viên? | Kế thừa công khai chỉ khi đúng "là một" (mọi chỗ dùng cha thay bằng con vẫn đúng, Liskov); dùng lại cài đặt thì "có một". → Bài 32, 37 |
| 67 | Template khác hàm ảo thế nào? | Template: lúc biên dịch, mỗi kiểu một bản, không cần cha chung, gọi thẳng; hàm ảo: lúc chạy, trộn nhiều loại trong một dãy, gọi gián tiếp. → Bài 34 |
| 68 | Observer cần chú ý vòng đời gì? | Danh sách con trỏ thô: observer chết mà còn trong danh sách thì gọi vào đồ đã trả; dùng `weak_ptr` và duyệt trên bản sao. → Bài 36, 73 |

#### H. Hệ điều hành, tiến trình, IPC, mạng

| # | Hỏi | Đáp |
|---|---|---|
| 69 | Tiến trình khác luồng thế nào? | Bộ nhớ (tiến trình có không gian địa chỉ riêng, luồng chung heap và toàn cục, riêng stack), chi phí (luồng rẻ hơn), cách ly (luồng crash kéo cả tiến trình), giao tiếp (luồng: bộ nhớ chung có khóa; tiến trình: IPC). → [Bài 47](../nhom-6-he-dieu-hanh-tien-trinh/47-tien-trinh-vs-luong.md) |
| 70 | Vì sao đổi ngữ cảnh giữa tiến trình đắt hơn giữa luồng? | Cùng tiến trình chỉ đổi thanh ghi; khác tiến trình phải đổi bảng trang nên TLB và bộ đệm nguội. → [Bài 47](../nhom-6-he-dieu-hanh-tien-trinh/47-tien-trinh-vs-luong.md) |
| 71 | `fork` trả gì, copy-on-write là gì? | `0` ở con, pid con ở cha, `-1` khi lỗi; trang nhớ chỉ được chép khi một bên ghi. `fork` n lần liên tiếp cho 2^n tiến trình. → [Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md) |
| 72 | `exec` làm gì với pid và file descriptor? | Thay hình hài chương trình nhưng **giữ pid** và các fd chưa đặt `FD_CLOEXEC`; thành công thì không trở lại. → [Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md) |
| 73 | Zombie khác orphan? | Zombie: con đã chết mà cha chưa `wait` (`kill -9` không xóa được); orphan: cha chết trước, `init`/subreaper nhận nuôi. → [Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md) |
| 74 | `fork` trong chương trình đa luồng nguy hiểm sao? | Chỉ luồng gọi `fork` có trong con nhưng mutex đang bị luồng khác giữ vẫn được sao chép: con xin khóa đó thì treo; nên `exec` ngay hoặc `posix_spawn`. → [Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md) |
| 75 | Hai tiến trình trao đổi lượng dữ liệu lớn nhanh nhất? | Shared memory (`mmap`/`shm_open`) kèm đồng bộ (`sem_t` hay `pthread_mutex` với `PTHREAD_PROCESS_SHARED`); lợi nhất khi khúc lớn và đồng bộ thưa. → [Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md) |
| 76 | Vì sao không đặt `std::mutex` thường vào shared memory? | Nó không được thiết kế cho nhiều tiến trình (chuẩn không bảo đảm; mình chạy ra assertion hoặc treo); dùng mutex POSIX có cờ `PTHREAD_PROCESS_SHARED`. → [Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md) |
| 77 | Với `pipe` + `fork` phải nhớ gì? | Mỗi bên đóng đầu ống mình không dùng, nếu không `read` không bao giờ thấy hết dữ liệu và treo. → [Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md) |
| 78 | Signal handler được làm gì? | Rất ít: đặt cờ `volatile sig_atomic_t` rồi để vòng chính xử lý (không `printf`, `malloc`, mutex); `SIGKILL` không bắt được. → [Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md) |
| 79 | Vì sao `epoll` thay cho một luồng một kết nối? | Mỗi luồng giữ một stack và tốn đổi ngữ cảnh, có trần; `epoll` đăng ký fd một lần, `epoll_wait` chỉ trả fd sẵn sàng (fd để non-blocking), một luồng phục vụ rất nhiều kết nối. → [Bài 50](../nhom-6-he-dieu-hanh-tien-trinh/50-io-epoll-event-loop.md) |
| 80 | Server 10 000 kết nối thiết kế sao? | Event loop `epoll` nhận sự kiện, việc tính nặng đẩy sang thread pool, handler không được chặn; nặng CPU thì số luồng cỡ số lõi. → [Bài 50](../nhom-6-he-dieu-hanh-tien-trinh/50-io-epoll-event-loop.md), 30 |

#### I. Công cụ: biên dịch, gỡ lỗi, đo, Git

| # | Hỏi | Đáp |
|---|---|---|
| 81 | `undefined reference` khác `multiple definition`? | Cái đầu: tên được cần mà không ai định nghĩa (quên tệp, quên `-l`, lệch chữ ký, thân template ở `.cpp`); cái sau: định nghĩa ở nhiều nơi (thân hàm thường trong header). Soi bằng `nm -C`. → Bài 38 |
| 82 | Gỡ lỗi nên biên dịch với cờ nào? | `-g -O0` (hay `-Og`); `-g` chỉ thêm thông tin gỡ lỗi; `-O2` làm gdb báo `<optimized out>`, còn đo tốc độ phải dùng bản tối ưu. → Bài 38, 42 |
| 83 | `assert` trong bản phát hành? | `-DNDEBUG` xóa hẳn `assert`, kể cả hiệu ứng phụ trong biểu thức. → Bài 38 |
| 84 | Chương trình sập `SIGSEGV`, bắt đầu từ đâu? | Chạy dưới gdb: `bt`, `frame N`, `info locals`, `print`; nhớ chỗ sập chỉ là nạn nhân, thủ phạm có thể ở chỗ khác. → Bài 40 |
| 85 | Core dump là gì? | Ảnh chụp bộ nhớ lúc chết; cần `ulimit -c` khác 0, mở lại bằng `gdb ./prog core` để xem (không chạy tiếp). → Bài 40 |
| 86 | Chương trình đa luồng treo, xem gì? | `gdb -p` hay chạy dưới gdb rồi `Ctrl+C`, `thread apply all bt`: `pthread_mutex_lock` là chờ khóa (xem `__owner`), `pthread_cond_wait` là chờ tín hiệu. → Bài 40, 64 |
| 87 | ASan, UBSan, TSan bắt gì, ghép được không? | ASan: ngoài biên, dùng sau khi trả, giải phóng hai lần (kèm LeakSanitizer); UBSan: tràn số có dấu, dịch bit quá cỡ...; TSan: data race và `lock-order-inversion`. ASan ghép với UBSan được, không ghép với TSan. → Bài 15, 41 |
| 88 | Sanitizer im lặng thì chương trình đúng? | Không: chỉ thấy lỗi xảy ra trong lần chạy đó; TSan không báo ca đã treo vì deadlock (dùng gdb). → Bài 41, 64 |
| 89 | `strace` và `/proc/PID` dùng để làm gì? | `strace` in lời gọi hệ thống: treo thì dòng cuối là lời gọi chưa trả (như `futex`); `/proc/PID/status`, `fd`, `maps` cho trạng thái, tệp mở, vùng nhớ. → Bài 42 |
| 90 | Đo hiệu năng cho đúng? | Dùng bản `-O2`, chạy nhiều lần; vòng lặp có kết quả không dùng bị xóa nên đo ra 0; làm theo đo, giả thuyết, sửa, đo lại, và kiểm kết quả vẫn đúng. → Bài 42 |
| 91 | `git merge` khác `git rebase`? | Merge gộp bằng commit có hai cha, giữ nguyên lịch sử; rebase phát lại commit lên nền mới (thành commit mới) nên không rebase nhánh đã chia sẻ. → Bài 43 |
| 92 | `reset`, `revert`, `reflog`? | `reset` lùi nhánh (chỉ khi chưa chia sẻ); `revert` đảo ngược bằng commit mới; `reflog` tìm lại commit "mất"; `bisect` tìm commit gây lỗi. → Bài 43 |

#### J. Thiết kế và xử lý lỗi

| # | Hỏi | Đáp |
|---|---|---|
| 93 | Ngoại lệ, mã lỗi hay `optional`? | Lỗi dự kiến, hay gặp, người gọi xử lý ngay thì `optional`/`variant`/mã lỗi (`[[nodiscard]]`); lỗi hiếm, nghiêm trọng, xử lý cách nhiều tầng thì ngoại lệ; hàm tạo không trả được mã lỗi nên ném. → [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md) |
| 94 | Ba mức an toàn ngoại lệ? | Cơ bản (không rò rỉ), mạnh (xong cả hoặc như chưa gọi, thường bằng "làm bản nháp rồi `swap`"), không ném (`noexcept`). → [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md) |
| 95 | `noexcept` mà vẫn ném thì sao? | `std::terminate`; hàm hủy mặc định `noexcept`. → [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md) |
| 96 | Ngoại lệ ném trong một luồng thì sao? | Thoát khỏi hàm luồng là `std::terminate`; bắt `catch (...)` rồi cất `std::exception_ptr`, hoặc dùng `async`/`promise` để chuyển sang luồng khác. → [Bài 56](../nhom-7-chon-dung-cong-cu/56-xu-ly-loi.md), 29 |
| 97 | Hàm nhận tham số thế nào cho rõ sở hữu? | Chỉ đọc: nhỏ thì giá trị, to thì `const&`; sửa cho người gọi: `T&`; giữ lại: giá trị rồi `std::move`; có thể không có: `T*`/`optional`. → [Bài 55](../nhom-7-chon-dung-cong-cu/55-api-so-huu-tham-so.md) |
| 98 | Monitor là gì, bẫy gì? | Dữ liệu và mutex chung một lớp, không lộ tham chiếu, gói "kiểm rồi làm" vào một hàm; bẫy: gọi callback khi giữ khóa (có thể deadlock). → [Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md) |
| 99 | Bốn mẫu an toàn luồng? | Chia theo luồng rồi gộp, bất biến kèm copy-on-write, monitor, truyền thông điệp; hỏi trước "dữ liệu này có thật sự phải chia sẻ và sửa?". → [Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md) |
| 100 | LRU cache O(1), an toàn luồng? | `list` (đầu là mới dùng nhất) + `unordered_map` khóa → iterator, `splice` đưa nút lên đầu; `get` là **ghi** nên cần khóa độc quyền; trả bản sao. → [Bài 71](../nhom-9-thuc-chien-da-luong/71-lru-cache.md) |
| 101 | Concurrent hash map? | Chia shard, mỗi shard một mutex và một bảng, mỗi hàm chỉ khóa một shard; "`get` rồi `put`" vẫn là race condition nên gộp thành `compute`. → [Bài 72](../nhom-9-thuc-chien-da-luong/72-concurrent-hashmap.md) |

### Phần 2: ba mini thiết kế hệ thống

Mỗi thiết kế dùng cùng năm ô: yêu cầu, thành phần, luồng dữ liệu, điểm đồng bộ, rủi ro. Nói theo thứ tự đó là đã đủ để người phỏng vấn thấy bạn có khung.

#### Thiết kế 1: logger đa luồng bất đồng bộ

| Ô | Nội dung |
|---|---|
| Yêu cầu | Nhiều luồng gọi `log(dòng)` mà không phải chờ I/O chậm; không mất dòng khi dừng; dòng của **cùng một luồng** giữ thứ tự; hàng có giới hạn. |
| Thành phần | Hàng đợi `deque<string>` + một mutex + hai `condition_variable` ([Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md)); **một** luồng ghi; đích ghi (`ostream`) chỉ luồng ghi được chạm vào. |
| Luồng dữ liệu | `log`: khóa, chờ chỗ, đẩy, nhả khóa, báo `khongRong`. Luồng ghi: chờ có việc, lấy, nhả khóa, ghi, lặp. |
| Điểm đồng bộ | Mutex của hàng; cờ `dong_` đổi dưới khóa rồi `notify_all`; `join` trong hàm hủy là cầu trước khi ai đọc đích. |
| Rủi ro, trade-off | Đầy thì chặn (chậm nhưng không mất) hay bỏ (nhanh nhưng mất log); chết đột ngột thì các dòng còn trong hàng mất (log lỗi nghiêm trọng nên ghi đồng bộ hoặc flush); thứ tự **giữa** các luồng chỉ là thứ tự lấy khóa; gọi `log` sau khi hủy logger là UB; `toiDa` phải từ 1 trở lên (bằng 0 thì `log` chờ mãi); không gọi `log` trong signal handler (có mutex). |

Về cú pháp: `std::ostream&` là tham chiếu tới luồng đầu ra bất kỳ (`cout`, `ofstream`, `ostringstream`), nhờ đó test ghi vào chuỗi trong bộ nhớ. `ghi_` là `std::thread` khai báo **cuối** lớp để luồng chỉ chạy khi mọi thành viên khác đã dựng xong ([Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md)).

```cpp
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <utility>
#include <vector>

class AsyncLogger {
public:
    AsyncLogger(std::ostream& dich, std::size_t toiDa)
        : dich_(dich), toiDa_(toiDa), ghi_([this] { chayGhi(); }) {}   // (1) luồng ghi dựng CUỐI

    ~AsyncLogger() {
        {
            std::lock_guard<std::mutex> g(khoa_);
            dong_ = true;                                               // (2) cờ đổi dưới khóa
        }
        khongRong_.notify_all();
        khongDay_.notify_all();
        ghi_.join();                                                    // (3) ghi nốt rồi mới hủy
    }

    bool log(std::string dong) {                                        // (4) nhiều luồng gọi
        std::unique_lock<std::mutex> lk(khoa_);
        khongDay_.wait(lk, [this] { return hang_.size() < toiDa_ || dong_; });
        if (dong_) return false;                                        // đã đóng: từ chối
        hang_.push_back(std::move(dong));
        lk.unlock();
        khongRong_.notify_one();
        return true;
    }

private:
    void chayGhi() {                                                    // (5) CHỈ luồng này chạm dich_
        std::unique_lock<std::mutex> lk(khoa_);
        for (;;) {
            khongRong_.wait(lk, [this] { return !hang_.empty() || dong_; });
            if (hang_.empty()) return;                                  // đóng VÀ cạn
            std::string dong = std::move(hang_.front());
            hang_.pop_front();
            lk.unlock();
            khongDay_.notify_one();
            dich_ << dong << '\n';                                      // (6) I/O chậm nằm NGOÀI khóa
            lk.lock();
        }
    }

    std::ostream& dich_;
    std::size_t toiDa_;
    std::mutex khoa_;
    std::condition_variable khongDay_, khongRong_;
    std::deque<std::string> hang_;
    bool dong_ = false;
    std::thread ghi_;                                                   // khai báo cuối
};

int main() {
    const int SO_LUONG = 4, MOI_LUONG = 250;
    std::ostringstream kho;                       // đích giả: chỉ luồng ghi đụng vào lúc chạy
    {
        AsyncLogger lg(kho, 8);
        std::vector<std::thread> ds;
        for (int k = 0; k < SO_LUONG; ++k)
            ds.emplace_back([&lg, k] {
                for (int i = 0; i < MOI_LUONG; ++i)
                    lg.log(std::to_string(k) + " " + std::to_string(i));
            });
        for (auto& t : ds) t.join();
    }                                             // hủy lg: ghi nốt rồi join
    std::istringstream in(kho.str());
    std::vector<int> cuoi(SO_LUONG, -1);
    int so = 0;
    bool dungThuTu = true;
    for (int k, i; in >> k >> i; ++so) {
        if (i != cuoi[k] + 1) dungThuTu = false;
        cuoi[k] = i;
    }
    std::cout << "so dong = " << so << '\n';
    std::cout << "thu tu trong tung luong: " << (dungThuTu ? "dung" : "sai") << '\n';
}
```

**Chạy từng dòng** (đã chạy 5 lần dưới TSan, mọi lần sạch và cùng kết quả):

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (1) | Hàm tạo dựng `dich_`, `toiDa_`, mutex, cv, hàng, cờ, rồi cuối cùng mới tạo luồng `ghi_` | Luồng chạy `chayGhi` khi mọi thứ nó cần đã sẵn sàng |
| (4) | 4 luồng gọi `log`; hàng đầy 8 dòng thì chờ trên `khongDay_` | Hàng đầy là **áp lực ngược**: producer chạy chậm theo luồng ghi |
| (5)-(6) | Luồng ghi lấy một dòng, **nhả khóa**, báo "có chỗ", rồi mới ghi | Ghi vào `ostringstream` ở đây thay cho ghi tệp chậm; không giữ khóa lúc I/O |
| (2)-(3) | Hàm hủy đổi cờ dưới khóa, đánh thức cả hai phía, `join` | Luồng ghi thoát khi `dong_` **và** hàng cạn nên không mất dòng |
| `main` | Sau khi hủy `lg`, đọc `kho` | `join` là cầu đồng bộ: đọc `kho` lúc này an toàn |

**Kết quả khi chạy:**

```text
so dong = 1000
thu tu trong tung luong: dung
```

Đầu ra tất định vì ta chỉ in **tính chất** (đủ 1000 dòng, mỗi luồng giữ thứ tự), không in thứ tự xen giữa các luồng. Thứ tự xen kẽ giữa bốn luồng là thứ tự lấy khóa, thay đổi mỗi lần chạy.

**Thử thay đổi.** (a) Bỏ hai dòng `notify_all` trong hàm hủy, rồi cho `main` chỉ `log` ba dòng, ngủ 100 ms, sau đó hủy logger: chương trình **treo**, `timeout` báo mã 124 (mình đã chạy). Luồng ghi đang ngủ trên `khongRong_`, cờ đổi mà không ai gọi nó dậy. (b) Đưa `std::thread ghi_` lên đầu danh sách thành viên: mình chạy 6 lần đều ra đúng, nhưng luồng có thể chạm mutex chưa dựng, tức là UB; "chạy đúng" ở đây không chứng minh gì (câu 10), nên luồng luôn khai báo cuối.

!!! info "Bạn biết Go?"
    Bản Go gần như một dòng: `ch := make(chan string, 64)`, một goroutine `for s := range ch { ghi(s) }`, và `close(ch)` rồi chờ goroutine đó xong khi dừng. Channel có đệm đã là hàng đợi chặn có giới hạn. Gửi vào channel **đã đóng** thì `panic`, nên cũng phải chắc không ai `log` sau khi đóng, đúng như hàm `log` của C++ ở trên trả `false`.

#### Thiết kế 2: object pool

| Ô | Nội dung |
|---|---|
| Yêu cầu | Mượn và trả đối tượng cùng loại O(1) mà không `new`/`delete` mỗi lần; số ô cố định; nhiều luồng dùng chung; mượn xong **tự trả** khi hết đời. |
| Thành phần | Kho cố định `O o_[N]` (ô thô đúng cỡ và căn lề của `T`), ngăn xếp con trỏ ô rảnh, một mutex; `muon()` trả `unique_ptr` có deleter riêng (RAII). |
| Luồng dữ liệu | `muon`: khóa, lấy một ô rảnh, nhả khóa, **dựng** `T` bằng placement new. Hết đời tay cầm: hàm hủy `T`, khóa, đẩy ô về ngăn xếp. |
| Điểm đồng bộ | Chỉ ngăn xếp ô rảnh dưới mutex; đối tượng đang mượn thuộc đúng một luồng nên không cần khóa riêng. |
| Rủi ro, trade-off | Hết ô: trả rỗng (người gọi quyết định) hay chờ trên cv (có thể deadlock nếu ai cũng giữ ô và chờ ô); pool chết trước đối tượng đang mượn là UB; **ASan không còn bắt được dùng-sau-khi-trả** (vùng nhớ vẫn thuộc pool); đối tượng tái dùng phải được dựng lại sạch; hàm tạo của `T` mà ném thì ô bị mất (bản dưới đây chưa bắt ngoại lệ đó, nên `T` phải có hàm tạo không ném); lock-free thì dính ABA ([Bài 62](../nhom-8-da-luong-chieu-sau/62-lock-free-co-ban.md)). Chỉ đáng dùng khi đã đo thấy `new` là nút thắt ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)). |

Về cú pháp: `new (cho) T(...)` là placement new ([Bài 58](../nhom-7-chon-dung-cong-cu/58-bo-nho-nang-cao.md)); `alignas(T) unsigned char buf[sizeof(T)]` là ô thô đúng căn lề; `Tra` là một **deleter** (Bài 09: bộ xóa tùy chỉnh của `unique_ptr`) nhớ địa chỉ pool để trả ô về.

```cpp
#include <atomic>
#include <cstddef>
#include <iostream>
#include <memory>
#include <mutex>
#include <new>
#include <thread>
#include <utility>
#include <vector>

template <typename T, std::size_t N>
class ObjectPool {
    struct Tra {                                          // deleter: trả ô về pool
        ObjectPool* pool;
        void operator()(T* t) const { pool->tra(t); }
    };

public:
    using Ma = std::unique_ptr<T, Tra>;                   // "tay cầm" RAII: hết đời thì tự trả

    ObjectPool() {
        for (auto& o : o_) ranh_.push_back(o.buf);        // (1) mọi ô đều rảnh
    }

    template <typename... A>
    Ma muon(A&&... a) {                                   // (2) hết ô: trả Ma rỗng, người gọi quyết định
        void* cho = nullptr;
        {
            std::lock_guard<std::mutex> g(khoa_);
            if (ranh_.empty()) return Ma(nullptr, Tra{this});
            cho = ranh_.back();
            ranh_.pop_back();
        }
        return Ma(new (cho) T(std::forward<A>(a)...), Tra{this});   // (3) dựng NGOÀI khóa
    }

    std::size_t ranh() {
        std::lock_guard<std::mutex> g(khoa_);
        return ranh_.size();
    }

private:
    void tra(T* t) {
        t->~T();                                          // (4) hủy tay: chỉ hàm hủy, không delete
        std::lock_guard<std::mutex> g(khoa_);
        ranh_.push_back(static_cast<void*>(t));
    }

    struct O { alignas(T) unsigned char buf[sizeof(T)]; };
    O o_[N];                                              // kho cố định: không new trong lúc chạy
    std::vector<void*> ranh_;                             // ngăn xếp các ô rảnh
    std::mutex khoa_;
};

struct Hop {
    static std::atomic<int> dangSong;                     // số Hop đang sống
    int gia = 0;
    Hop() { ++dangSong; }
    ~Hop() { --dangSong; }
};
std::atomic<int> Hop::dangSong{0};

int main() {
    ObjectPool<Hop, 4> pool;
    std::atomic<int> sai{0}, xong{0}, dinh{0};
    std::vector<std::thread> ds;
    for (int k = 0; k < 8; ++k)
        ds.emplace_back([&, k] {
            for (int i = 0; i < 1000; ++i) {
                auto h = pool.muon();
                while (!h) { std::this_thread::yield(); h = pool.muon(); }   // hết ô: thử lại
                if (h->gia != 0) ++sai;                   // mỗi lần mượn phải thấy đối tượng MỚI
                int d = Hop::dangSong.load();
                int cu = dinh.load();
                while (d > cu && !dinh.compare_exchange_weak(cu, d)) {}
                h->gia = k + 1;                           // dùng riêng, không ai khác chạm
                ++xong;
            }                                             // h ra khỏi khối: tự trả
        });
    for (auto& t : ds) t.join();
    std::cout << "so lan muon = " << xong << '\n';
    std::cout << "doi tuong cu con sot = " << sai << '\n';
    std::cout << "dang song = " << Hop::dangSong << ", o ranh = " << pool.ranh() << '\n';
    std::cout << "dinh dong thoi <= 4: " << (dinh <= 4 ? "dung" : "sai") << '\n';
}
```

**Chạy từng dòng:**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (1) | Hàm tạo đẩy địa chỉ 4 ô thô vào `ranh_` | Chưa có `Hop` nào được dựng: `dangSong` vẫn 0 |
| (2) | Tám luồng tranh 4 ô; luồng không được ô nhận `Ma` rỗng và `yield` rồi thử lại | Chỉ lúc đó mới chờ; không luồng nào giữ khóa khi chờ |
| (3) | Lấy ô dưới khóa, nhả khóa, rồi `new (cho) Hop()` | Hàm tạo chạy ngoài khóa nên không kéo dài vùng găng |
| (4) | `h` ra khỏi khối: `Tra` gọi `tra`, chạy `~Hop`, đẩy ô về | Mỗi lần mượn lại dựng `Hop` mới, nên `gia` luôn khởi đầu bằng 0 |

**Kết quả khi chạy** (dưới TSan và ASan+UBSan cũng sạch, cùng kết quả):

```text
so lan muon = 8000
doi tuong cu con sot = 0
dang song = 0, o ranh = 4
dinh dong thoi <= 4: dung
```

**Thử thay đổi.** Giữ một con trỏ thô `Hop* tho = h.get();` rồi đọc `tho->gia` **sau khi** `h` đã trả ô: chương trình in `7` và ASan im lặng (đọc ra `7` chỉ là may, vẫn là UB). Cùng lỗi với `new`/`delete` thường thì ASan báo ngay `heap-use-after-free`. Đây là cái giá thật của pool: nó che mất lỗi dùng-sau-khi-trả khỏi công cụ.

!!! info "Bạn biết Go?"
    `sync.Pool` của Go là bể đối tượng tạm: bộ gom rác có thể dọn bớt phần tử bất cứ lúc nào, và nó không giới hạn số lượng. Pool có kích thước cố định, như bài này, thường làm bằng channel có đệm chứa sẵn N đối tượng: nhận từ channel là mượn, gửi lại là trả.

#### Thiết kế 3: task scheduler (hẹn giờ + chạy việc)

| Ô | Nội dung |
|---|---|
| Yêu cầu | `hen(việc, sau bao lâu)` và việc lặp; hủy được; việc dài không làm trễ việc khác; dừng êm; kiểm thử không phụ thuộc mili-giây. |
| Thành phần | Bộ hẹn giờ: min-heap theo `(mốc giờ, id)` + `cv.wait_until` + một luồng điều phối ([Bài 74](../nhom-9-thuc-chien-da-luong/74-timer-rate-limiter.md)); thread pool trả `future` ([Bài 67](../nhom-9-thuc-chien-da-luong/67-thread-pool-tu-viet.md)); tùy chọn hàng đợi chặn trước pool ([Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md)). |
| Luồng dữ liệu | `hen` → khóa, đẩy vào heap, báo cv → luồng điều phối ngủ tới mốc sớm nhất → tới giờ thì **đẩy việc vào pool** → worker chạy ngoài khóa. |
| Điểm đồng bộ | Mutex + cv của heap (đổi heap và cờ dừng dưới khóa); mutex + cv của hàng pool; hủy bằng xóa lười (chỉ đánh dấu đã hủy, bỏ khi đỉnh heap tới lượt) dưới khóa heap; `join` điều phối rồi `shutdown` pool. |
| Rủi ro, trade-off | Chạy việc ngay trong luồng điều phối thì việc dài làm trễ mọi việc sau; gọi `hen` từ trong việc phải không treo (chạy việc ngoài khóa); dậy sớm hay dậy giả đều phải **xem lại đỉnh heap và đồng hồ**; chuẩn không hứa đúng mốc; việc lặp bị trễ thì bù hay bỏ; dùng `steady_clock`; dừng thì việc chưa tới giờ bỏ hay chạy luôn phải nói rõ. |

Phần code khung của ba mảnh đã có đầy đủ ở [Bài 74](../nhom-9-thuc-chien-da-luong/74-timer-rate-limiter.md) (heap + `wait_until`), [Bài 67](../nhom-9-thuc-chien-da-luong/67-thread-pool-tu-viet.md) (pool) và [Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md) (hàng chặn); phần ghép chỉ là một lời gọi. Ở bảng trắng, vẽ giao diện và luồng đi như sau:

```text
class Scheduler {
  hen(viec, doTre)  -> id      // khóa heap, đẩy (mốc, id, viec), notify
  huy(id)                      // đánh dấu đã hủy (xóa lười), notify
  luongDieuPhoi():             // wait_until(mốc sớm nhất) có kiểm cờ dừng
      lấy mọi việc tới giờ ra khỏi heap (dưới khóa)
      nhả khóa; pool.submit(viec) cho từng việc   // KHÔNG chạy việc ở đây
  ~Scheduler(): cờ dừng dưới khóa, notify_all, join điều phối, pool.shutdown()
}
```

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Chương trình thỉnh thoảng sập, chạy `-O0` thì ổn. Bạn làm gì?"
    Nghi UB: kết quả đổi theo `-O` là dấu hiệu quen thuộc. Biên dịch lại với `-g -fsanitize=address,undefined` và chạy bộ test; nếu sập thì lấy core dump hoặc chạy dưới gdb xem `bt` (Bài 15, 40, 41). Nhớ chỗ sập có thể chỉ là nạn nhân (Bài 46).
    **Nối tiếp:** "Sanitizer sạch mà vẫn sập thì sao?" Nghĩ tới data race: chạy riêng với `-fsanitize=thread` (không ghép với ASan), và nhớ lỗi hiếm cần chạy lặp hay mở rộng cửa sổ chạy đua ([Bài 64](../nhom-8-da-luong-chieu-sau/64-go-loi-da-luong.md)). Im lặng vẫn không chứng minh đúng.

??? question "Thiết kế logger cho chương trình nhiều luồng."
    Khung năm ô của Thiết kế 1: hàng đợi có giới hạn, một luồng ghi, hai cv, đóng bằng cờ dưới khóa rồi `notify_all` và `join`; I/O nằm ngoài khóa.
    **Nối tiếp:** "Hàng đầy thì sao?" Chặn (không mất, chậm lại theo luồng ghi) hoặc bỏ (nhanh, mất log); chọn theo mức quan trọng của log, và nói rõ với người dùng ([Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md)). **Nối tiếp nữa:** "Chương trình chết đột ngột thì dòng nào mất?" Mọi dòng còn trong hàng; log lỗi nghiêm trọng nên ghi đồng bộ hay flush ngay, đánh đổi lấy tốc độ.

??? question "Hai tiến trình cần trao đổi nhiều dữ liệu; mỗi tiến trình lại có nhiều luồng. Thiết kế sao?"
    Shared memory (`mmap`/`shm_open`) kèm đồng bộ xuyên tiến trình: `sem_t` với `pshared = 1` hoặc `pthread_mutex` có `PTHREAD_PROCESS_SHARED`, không dùng `std::mutex` thường; trong vùng chung chỉ để dữ liệu thuần, không con trỏ hay `std::string` ([Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md)). Trong mỗi tiến trình, các luồng vẫn dùng mutex/cv như thường.
    **Nối tiếp:** "Tiến trình cha có luồng mà muốn `fork` thì sao?" Chỉ luồng gọi `fork` sống trong con, khóa bị luồng khác giữ vẫn bị sao chép nên con có thể treo; `exec` ngay hoặc `posix_spawn`, hoặc `fork` trước khi tạo luồng ([Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md)).

??? question "Cache dùng chung cho nhiều luồng, đọc nhiều ghi ít. Chọn cấu trúc và cơ chế khóa nào?"
    `unordered_map` dưới một mutex trước ([Bài 53](../nhom-7-chon-dung-cong-cu/53-chon-container.md), 54), giá trị là `shared_ptr<const T>` để luồng đọc lấy bản chụp rồi dùng ngoài khóa; cache giữ `weak_ptr` nếu không muốn giữ sống đối tượng ([Bài 51](../nhom-7-chon-dung-cong-cu/51-chon-smart-pointer.md), 52). `get` trả bản sao hoặc `shared_ptr`, không trả tham chiếu ra khỏi khóa.
    **Nối tiếp:** "Thế nếu ghi nhiều, bảng lớn?" Chia shard ([Bài 72](../nhom-9-thuc-chien-da-luong/72-concurrent-hashmap.md)); nếu cần loại bỏ theo độ cũ thì LRU, trong đó `get` cũng là ghi ([Bài 71](../nhom-9-thuc-chien-da-luong/71-lru-cache.md)). Chỉ đổi sang `shared_mutex` hay copy-on-write sau khi **đo** thấy mutex là nút thắt ([Bài 57](../nhom-7-chon-dung-cong-cu/57-chon-dong-bo.md), 61).

??? question "Vì sao chứa các hình khác loại bằng `vector<unique_ptr<Hinh>>` mà không phải `vector<Hinh>`?"
    `vector<Hinh>` chứa theo giá trị nên gán đối tượng con vào sẽ bị cắt (slicing) và mất đa hình; `unique_ptr<Hinh>` giữ đối tượng thật ở heap, gọi hàm ảo đúng món. Lớp cha cần hàm hủy `virtual` để `unique_ptr` xóa đúng (Bài 33, 32, 09).
    **Nối tiếp:** "Sao `push_back(std::make_unique<...>())` không sao chép?" `unique_ptr` chỉ chuyển được; tham số là rvalue nên chọn hàm chuyển; và khi `vector` tăng khối, nó chuyển các `unique_ptr` (Bài 09, 12, 16).

??? question "Server phải giữ 10 000 kết nối. Bạn thiết kế thế nào?"
    Event loop `epoll` với socket non-blocking, một (hay vài) luồng nhận sự kiện, việc tính nặng chuyển sang thread pool; handler không được chặn ([Bài 50](../nhom-6-he-dieu-hanh-tien-trinh/50-io-epoll-event-loop.md), 30). Một luồng một kết nối tốn stack và đổi ngữ cảnh, có trần.
    **Nối tiếp:** "Callback chạy ở worker mà kết nối đã đóng thì sao?" Tuổi thọ của fd và đối tượng kết nối: bắt `weak_ptr` hay `shared_ptr` chứ không `this` thô ([Bài 52](../nhom-7-chon-dung-cong-cu/52-smart-pointer-da-luong.md)). **Nối tiếp nữa:** "Producer nhanh hơn worker mãi?" Hàng có giới hạn tạo áp lực ngược thay vì phình bộ nhớ ([Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md)).

??? question "Chương trình đa luồng của bạn chạy chậm. Bạn làm gì?"
    Đo trước, với bản `-O2` (Bài 42): chậm ở đâu, tranh chấp khóa hay cấp phát hay false sharing. Chọn công cụ theo triệu chứng, nhớ Amdahl: phần tuần tự và vùng găng chặn trần tăng tốc (Bài 30, 64).
    **Nối tiếp:** "Thêm luồng mà không nhanh hơn?" Có thể đã chạm trần Amdahl, nghẽn băng thông bộ nhớ, hay tranh một mutex; chữa bằng chia theo luồng rồi gộp hoặc shard ([Bài 61](../nhom-8-da-luong-chieu-sau/61-mau-an-toan-luong.md), 72). Việc nhỏ thì tuần tự có thể thắng cả pool ([Bài 75](../nhom-9-thuc-chien-da-luong/75-parallel-sum-sort-wordcount.md)).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Lao vào code khi chưa hỏi lại đề"
    Gặp đề "viết hàng đợi", bạn viết ngay `push`/`pop` rồi mới nhận ra đề cần dừng sạch hoặc nhiều consumer. Dành hai phút hỏi: mấy producer/consumer, đầy thì làm gì, có cần dừng sạch không, và nói thẳng giả định của mình.

!!! warning "Lỗi 2: Im lặng, hoặc trả lời thuộc lòng không biết vì sao"
    Im lặng khiến người chấm không có gì để chấm. Trả lời thuộc lòng ("`wait` phải có `while`") mà không nói được cơ chế (spurious wakeup, món bị lấy mất) sẽ gãy ở câu nối tiếp đầu tiên. Dùng khuôn bốn nhịp, và nhịp 2 là nhịp quyết định.

!!! warning "Lỗi 3: Nói tuyệt đối, hoặc coi một lần chạy đẹp là bằng chứng"
    "Atomic luôn nhanh hơn mutex", "lock-free luôn tốt hơn", "chạy 100 lần đều đúng", "UB thì sẽ sập". Cả bốn đều sai: UB có thể chạy đúng (mình đã thấy hai ca ở trên ra đúng dù có UB: `ghi_` khai báo đầu ở Thiết kế 1, và con trỏ thô dùng sau khi trả ở Thiết kế 2), và tốc độ đổi theo tải. Nói "tùy, vì... và em sẽ đo" kèm tiêu chí.

!!! warning "Lỗi 4: Bịa khi không biết, hoặc nói 'em không biết' rồi dừng"
    Bịa bị hỏi tiếp là lộ. Dừng ngay ở "không biết" bỏ phí cơ hội: hãy nói điều bạn **suy ra được** từ nguyên lý và cách bạn sẽ kiểm. Ví dụ: "Em chưa dùng `io_uring`; em biết nó là kiểu proactor, khác `epoll` ở chỗ bạn nhờ hệ điều hành làm hẳn; em sẽ đọc tài liệu và thử một chương trình nhỏ."

!!! warning "Lỗi 5: Quên kiểm tra chính code mình viết"
    Bản nháp đầu của chính bài này, ở object pool, viết `[&]` thay cho `[&, k]` trong lambda của vòng `for`: mỗi luồng cầm tham chiếu tới biến `k` đã hết đời, ASan báo ngay `stack-use-after-scope`. Trên bảng trắng, hãy đọc lại từng lambda: nó bắt gì, ai sống lâu hơn ai (Bài 24, 76).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="84" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau (vector vừa tạo có 3 phần tử, sức chứa chưa tới 1000). Dòng cuối có vấn đề gì?

```text
std::vector<int> v(3);
int& r = v[0];
v.resize(1000);
r = 9;
```

- Hợp lệ, vì `r` là tham chiếu nên luôn trỏ đúng phần tử đầu của vector
- Không biên dịch được, vì cấm giữ tham chiếu tới phần tử của vector
- UB: `resize` tái cấp phát, `r` còn trỏ vào mảng cũ đã trả
- Chỉ sai khi `resize` làm vector nhỏ đi, còn lớn lên thì vẫn đúng

<p class="giai-thich" markdown>`resize(1000)` vượt sức chứa nên vector xin mảng mới, chuyển phần tử sang đó và trả mảng cũ; `r` vẫn ghi địa chỉ cũ, nên `r = 9` ghi vào bộ nhớ đã trả, là hành vi không xác định (Bài 16, 19). Tham chiếu không "đi theo" phần tử như tên gọi gợi ý: nó chỉ là biệt danh của một ô nhớ cụ thể. Giữ tham chiếu tới phần tử là cú pháp hợp lệ, trình biên dịch không cấm. Và chính việc vector **lớn lên** mới gây tái cấp phát, còn thu nhỏ không làm đổi chỗ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đoạn sau in ra gì?

```text
auto a = std::make_unique<int>(5);
auto b = std::move(a);
std::cout << (a == nullptr) << *b;
```

- `15`: `a` rỗng sau khi chuyển (chuẩn bảo đảm), `b` giữ số 5
- `05`: `std::move` chép giá trị sang `b` nên `a` vẫn trỏ tới số 5
- Không biên dịch được, vì `unique_ptr` không hỗ trợ chuyển quyền sở hữu
- In `1` rồi sập, vì `*b` đọc từ con trỏ đã bị đặt về rỗng

<p class="giai-thich" markdown>Chuẩn bảo đảm `unique_ptr` sau khi bị chuyển đi là rỗng, nên `a == nullptr` đúng (in `1`), còn `b` nhận đối tượng nên `*b` là 5 (Bài 09, 12). `std::move` không chép gì: nó chỉ ép `a` thành rvalue để hàm tạo di chuyển chạy. `unique_ptr` không **sao chép** được nhưng chuyển được, nên đoạn này biên dịch tốt. Người bị đặt về rỗng là `a`, không phải `b`, nên `*b` an toàn.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Một tiến trình chạy đoạn sau (bộ đệm `stdout` đang trống). Tổng cộng bao nhiêu dòng `x` được in ra?

```text
fork();
fork();
printf("x\n");
```

- 2 dòng, vì có hai lời gọi `fork`, mỗi lời gọi thêm một dòng
- 3 dòng, vì tiến trình gốc cộng hai tiến trình con
- 8 dòng, vì mỗi `fork` nhân đôi rồi `printf` lại nhân đôi nữa
- 4 dòng, vì có 2^2 tiến trình và mỗi tiến trình in một lần

<p class="giai-thich" markdown>Mỗi `fork` nhân đôi số tiến trình đang chạy: sau hai lần còn 2^2 = 4 tiến trình, và cả bốn cùng chạy `printf` một lần ([Bài 48](../nhom-6-he-dieu-hanh-tien-trinh/48-fork-exec-wait.md)). Cộng "mỗi fork thêm một" sai vì tiến trình con cũng tiếp tục gọi `fork` thứ hai. Con số 3 quên rằng con của lần `fork` đầu cũng tự `fork` tiếp. Con số 8 đếm `printf` như thể nó cũng nhân đôi, trong khi `printf` không tạo tiến trình mới.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đoạn sau sai ở đâu?

```text
std::string_view ten() {
    std::string s = "hoso_nguoi_dung_so_1";
    return s;
}
```

- Không sai: `return` sao chép nội dung chuỗi vào `string_view` nên an toàn
- `string_view` trỏ vào `s` đã bị hủy khi hàm kết thúc; trả `std::string`
- Không biên dịch được, vì `string` không đổi ngầm sang `string_view`
- Chỉ treo với chuỗi ngắn hơn 16 ký tự; chuỗi dài thì luôn an toàn

<p class="giai-thich" markdown>`string_view` chỉ giữ (địa chỉ, độ dài) và không sở hữu gì, nên khi `s` chết cuối hàm thì nó trỏ vào bộ nhớ đã trả; sửa bằng cách trả `std::string` theo giá trị (Bài 17). Không có phép sao chép nội dung nào ở đây: đó là hiểu `string_view` như một `string`. Phép đổi ngầm từ `string` sang `string_view` có tồn tại nên đoạn này biên dịch được, đó là lý do lỗi dễ lọt. Chuỗi ngắn (SSO) cũng treo, chỉ khác là nó nằm trong chính `s` trên stack, nên "chuỗi dài thì an toàn" là sai.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Bốn luồng, mỗi luồng chạy `n = n + 1;` một nghìn lần trên `std::atomic<int> n{0};`. Điều nào đúng?

- Luôn đúng 4000, vì `n` là `atomic` nên mọi phép gán đều an toàn
- Là UB vì hai luồng cùng ghi `n` không có khóa, nên có thể sập
- Có thể nhỏ hơn 4000, không phải UB: đọc rồi ghi là hai thao tác rời
- Có thể lớn hơn 4000 vì hai luồng cùng đọc một giá trị rồi cùng cộng thêm

<p class="giai-thich" markdown>`n + 1` đọc `n` bằng một thao tác nguyên tử, rồi `n = ...` ghi bằng một thao tác nguyên tử khác; giữa hai thao tác luồng khác có thể chen vào nên mất lần cộng, kết quả có thể nhỏ hơn 4000 mà vẫn không có data race (Bài 28). Từng thao tác trên `atomic` an toàn, nhưng chuỗi hai thao tác thì không thành một khối: phải dùng `++n` hoặc `fetch_add`. Vì mỗi thao tác đều nguyên tử nên đây không phải UB. Hai luồng cùng đọc rồi cùng ghi ra giá trị cũ cộng một làm **mất** lần cộng, không bao giờ làm tổng vượt 4000.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Tình huống: server giữ 10 000 kết nối, phần lớn nằm rảnh, mỗi yêu cầu xử lý rất nhanh. Chọn mô hình nào?

- Event loop `epoll` với socket non-blocking, việc nặng đẩy sang thread pool
- Mỗi kết nối một luồng, vì luồng đang ngủ không tốn CPU nên không có gì phải lo
- Mỗi kết nối một tiến trình `fork`, vì cách ly lỗi tốt hơn cho từng kết nối
- Một luồng gọi `read` chặn lần lượt từng socket theo vòng tròn

<p class="giai-thich" markdown>Phần lớn kết nối rảnh nên một luồng chờ trên `epoll_wait` phục vụ được rất nhiều kết nối mà không tốn một stack cho mỗi kết nối ([Bài 50](../nhom-6-he-dieu-hanh-tien-trinh/50-io-epoll-event-loop.md)). Luồng ngủ đúng là không tốn CPU, nhưng mỗi luồng vẫn giữ stack và gây đổi ngữ cảnh, và có trần số luồng. Một tiến trình mỗi kết nối còn đắt hơn nữa, và cách ly lỗi không phải thứ cần ở đây. Gọi `read` chặn lần lượt thì một kết nối rảnh làm tất cả kết nối sau nó phải chờ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Tình huống: hai tiến trình cùng tăng một bộ đếm nằm trong vùng `mmap` chia sẻ. Bảo vệ bộ đếm bằng gì?

- `std::mutex` thường đặt ngay trong vùng chia sẻ, vì mutex nào cũng dùng được
- `volatile int` là đủ, vì vùng nhớ chung luôn được cập nhật tức thì cho cả hai
- Không cần gì, vì mỗi tiến trình đã có sẵn một bản sao riêng của vùng nhớ đó
- Mutex POSIX `PTHREAD_PROCESS_SHARED` hoặc `sem_t` dùng chung, đặt trong vùng

<p class="giai-thich" markdown>Mutex phải nằm trong vùng chung **và** được khởi tạo cho nhiều tiến trình, tức `pthread_mutex_t` với thuộc tính `PTHREAD_PROCESS_SHARED` hay `sem_t` với `pshared` khác 0 ([Bài 49](../nhom-6-he-dieu-hanh-tien-trinh/49-ipc.md)). `std::mutex` thường không được thiết kế và không được chuẩn bảo đảm cho việc đó. `volatile` không tạo đồng bộ nên hai tiến trình vẫn mất lần cộng. Vùng `MAP_SHARED` chính là chỗ hai tiến trình cùng thấy một bản, nên "mỗi bên một bản sao" là sai và thiếu khóa sẽ gây race.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Tình huống: chương trình đa luồng thỉnh thoảng đứng im, CPU gần 0%, lần chạy TSan trước đó không báo gì. Việc đầu tiên nên làm?

- Chèn `sleep_for` vào chỗ nghi ngờ để các luồng lệch pha nhau cho hết kẹt
- Gắn gdb vào tiến trình rồi `thread apply all bt` xem từng luồng ở đâu
- Biên dịch lại với `-O2` và chạy nhiều lần cho tới khi nó hết treo hẳn
- Chạy lại dưới ASan, vì ASan có phát hiện được deadlock giữa các luồng

<p class="giai-thich" markdown>Treo mà CPU gần 0% nghĩa là các luồng đang ngủ chờ nhau, và `thread apply all bt` cho thấy từng luồng đứng ở `pthread_mutex_lock`, `pthread_cond_wait` hay `join` (Bài 40, 64). Chèn `sleep_for` chỉ che lỗi (đổi cửa sổ chạy đua) chứ không tìm ra nguyên nhân. Đổi `-O2` đổi lịch chạy, không chữa được deadlock. ASan bắt lỗi bộ nhớ, không bắt deadlock; và TSan sạch chỉ nói lần chạy đó chưa thấy lỗi, nhất là với chương trình đã treo.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Mỗi câu hỏi nhanh trả lời theo bốn nhịp: đáp thẳng, cơ chế, giá phải trả hoặc khi nào không dùng, rồi một trường hợp biên; 101 câu của phần 1 chia mười chủ đề và câu nào cũng trỏ về bài gốc, nên chỗ nói vấp thì đọc lại đúng bài đó chứ không đọc lại tất cả.
2. Ở bảng trắng: hỏi lại đề trước khi vẽ, nói to suy nghĩ, nêu trade-off cùng điều kiện đổi ý, kiểm tra biên (rỗng, một phần tử, dừng giữa chừng, nhiều luồng), và khi không biết thì nói điều suy ra được cùng cách kiểm chứng thay vì bịa; "chạy đúng một lần" không phải bằng chứng.
3. Logger bất đồng bộ: hàng đợi có giới hạn dưới một mutex với hai cv, một luồng ghi, I/O ngoài khóa, dừng bằng cờ dưới khóa rồi `notify_all` và `join`; đầy thì chặn hay bỏ là quyết định phải nói rõ, và thứ tự chỉ được bảo đảm trong từng luồng gọi (mình chạy: 1000 dòng, đúng thứ tự, TSan sạch; bỏ `notify_all` thì treo, mã 124).
4. Object pool: kho cố định cộng ngăn xếp ô rảnh dưới mutex, placement new để dựng, `unique_ptr` có deleter tự trả ô; giá phải trả là che lỗi dùng-sau-khi-trả khỏi ASan (đã chạy: ASan im, còn `new`/`delete` thường thì báo `heap-use-after-free`) và pool không được chết trước đối tượng đang mượn.
5. Task scheduler ghép các bài đã học: min-heap `(mốc giờ, id)` cộng `wait_until` ở luồng điều phối, việc đẩy sang thread pool để việc dài không làm trễ hẹn giờ, hủy bằng xóa lười, dừng êm theo thứ tự cờ, `join`, `shutdown`; kiểm thử bằng thứ tự và hạn chót rộng, không bằng mili-giây.
