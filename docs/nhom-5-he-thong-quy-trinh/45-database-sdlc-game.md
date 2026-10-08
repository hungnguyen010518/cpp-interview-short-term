# Bài 45 — Database, quy trình phần mềm và nguyên lý game dev: ba chủ đề bổ sung

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - **Database:** nói được bảng, khóa chính, khóa ngoại, `SELECT`/`JOIN`/`GROUP BY`; hiểu vì sao truy vấn chậm và **index** (chỉ mục) cứu thế nào; biết **transaction** và **ACID**, lỗi **N+1**, và vì sao phải **tham số hóa** để chặn **SQL injection** (đã chạy thật bằng SQLite, xem mục "chưa chạy" ở Ví dụ 3).
    - **Quy trình:** so sánh waterfall với agile/scrum, nói được code review, CI/CD và kiểm thử đơn vị/tích hợp để làm gì, và kể một dự án theo khung **STAR** (không cần tên thật).
    - **Game dev:** viết được vòng lặp game (input → update → render) với **bước thời gian cố định**, một **object pool** không cấp phát trong vòng lặp nóng, và đo **AoS vs SoA** để thấy chuyện cache; có cầu nối Go ở từng phần.

**Bạn cần biết trước:** [Bài 01](../nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md) (bộ nhớ, địa chỉ), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, cấp phát heap), [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`std::vector`), [Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md) (lớp). Bài này là ba chủ đề độc lập, đọc phần nào trước cũng được.

## 🧠 Câu chuyện mở đầu

Một **thư viện trường**. Cuốn sổ mượn sách là một **bảng**: mỗi dòng một lượt mượn. Muốn tìm "các cuốn bạn An đang mượn", cô thủ thư có hai cách: lật từng trang từ đầu, hoặc mở **mục lục theo tên**. Với 100 dòng thì cách nào cũng nhanh; với 1 triệu dòng, lật từng trang là cả buổi sáng. Đó là **database** (cơ sở dữ liệu) và **index** trong một hình ảnh.

Còn để thư viện chạy mượt cả năm, cô hiệu trưởng cần **quy trình**: ai nhận việc, ai kiểm lại sổ trước khi chốt, khi nào thử sách mới nhập. Đó là phần SDLC. Cuối cùng, **rạp chiếu phim hoạt hình**: mỗi giây chiếu 60 tấm hình, tấm nào chậm là khán giả thấy giật. Đó là game, nơi mỗi phần nghìn giây đều quý.

!!! info "Chỗ nào ví von không còn đúng?"
    Thư viện chỉ để hiểu bảng và index ở đoạn này. Từ mục sau, ví dụ dùng bảng khách hàng/đơn hàng; transaction và injection không có "bản giấy" tương ứng. Các phần sau tự nêu ví von riêng.

## 📖 Giải thích

### Phần A. Database cho lập trình viên C++

### 1. Bảng, khóa chính, khóa ngoại

**Cơ sở dữ liệu quan hệ** lưu dữ liệu trong các **bảng**: cột là thuộc tính (tên, tiền), dòng là một bản ghi. **Khóa chính** (primary key) là cột mà mỗi dòng có giá trị riêng, để gọi đúng một dòng ("khách số 2"). **Khóa ngoại** (foreign key) là cột trỏ sang khóa chính của bảng khác: `don.khach_id` trỏ tới `khach.id`, nên không thể có đơn của một khách không tồn tại.

Tách bảng thế này để một thông tin chỉ nằm ở **một chỗ**: tên khách đổi thì sửa một dòng, không phải sửa trong từng đơn hàng.

### 2. SQL cơ bản: SELECT, JOIN, GROUP BY

**SQL** là ngôn ngữ hỏi database. `SELECT cột FROM bảng WHERE điều_kiện` lấy các dòng thỏa điều kiện. `JOIN` ghép hai bảng theo khóa ngoại (`ON don.khach_id = khach.id`). `GROUP BY` gom các dòng cùng giá trị thành nhóm để đếm (`COUNT`) hay cộng (`SUM`).

`LEFT JOIN` giữ cả khách chưa có đơn nào (cột bên đơn là `NULL`); `JOIN` thường (`INNER`) bỏ họ đi. Ví dụ 2 chạy cả hai điều này.

### 3. Index và vì sao truy vấn chậm

Không có index, `WHERE nguoi = 42` buộc database **quét cả bảng** (full scan): nhìn từng dòng, giống lật từng trang sổ. **Index** là cấu trúc phụ giữ các giá trị của một cột theo thứ tự, thường là **cây B** (B-tree), nên tìm một giá trị chỉ cần vài bước thay vì hàng triệu.

Cái giá: index tốn chỗ, và mỗi lần `INSERT`/`UPDATE` phải cập nhật cả index. Đặt index ở cột hay nằm trong `WHERE`/`JOIN`, đừng đặt khắp nơi. Cách xem database định làm gì: lệnh giải thích kế hoạch (`EXPLAIN` hay `EXPLAIN QUERY PLAN` của SQLite); từ `SCAN` là quét cả bảng, `SEARCH ... USING INDEX` là dùng index. Ví dụ 1 mô phỏng bằng C++ (đếm số dòng đã nhìn), Ví dụ 2 xem kế hoạch thật.

### 4. Transaction và ACID

**Transaction** (giao dịch) gom nhiều câu lệnh thành **một khối làm trọn hoặc không làm gì**. Chuyển 150 đồng từ A sang B gồm hai bước (cộng B, trừ A); nếu chết giữa chừng thì tiền không được phép mất hay tự sinh ra.

**ACID** là bốn lời hứa: **A**tomicity (nguyên tử: trọn gói hoặc không), **C**onsistency (nhất quán: luôn thỏa các ràng buộc như `so >= 0`), **I**solation (cô lập: giao dịch chạy cùng lúc không thấy dở dang của nhau), **D**urability (bền: đã `COMMIT` thì mất điện vẫn còn). Ví dụ 2 cho thấy `ROLLBACK` hoàn tác cả hai bước khi bước thứ hai vi phạm ràng buộc.

### 5. N+1 query

Lấy 100 đơn hàng (1 truy vấn), rồi với **mỗi đơn** hỏi thêm tên khách (100 truy vấn nữa) là **N+1 truy vấn**. Mỗi lần hỏi tốn một chuyến đi về tới database (qua mạng hoặc qua thư viện), nên 101 chuyến chậm hơn nhiều so với 1. Cách sửa: một `JOIN`, hoặc lấy trước tất cả khách cần bằng `WHERE id IN (...)`. Ví dụ 1 đếm chuyến đi.

### 6. SQL injection và tham số hóa

**SQL injection** xảy ra khi bạn **nối chuỗi** dữ liệu người dùng vào câu SQL: người dùng gõ `x' OR '1'='1` thì dấu `'` đóng chuỗi sớm, phần sau thành **lệnh SQL**. **Tham số hóa** (prepared statement, câu lệnh chuẩn bị) gửi câu SQL với chỗ trống `?`, rồi **gắn** giá trị vào sau; giá trị chỉ là dữ liệu, không bao giờ được hiểu thành lệnh. Cách chống là tham số hóa, không phải tự "lọc dấu nháy".

### Phần B. Quy trình phần mềm (SDLC)

### 7. Waterfall và agile/scrum

**SDLC** (Software Development Life Cycle, vòng đời phát triển phần mềm) là chuỗi bước từ ý tưởng tới chạy thật rồi bảo trì. Hai cách tổ chức hay gặp:

| | Waterfall (thác nước) | Agile / Scrum |
|---|---|---|
| Cách làm | Làm tuần tự: yêu cầu → thiết kế → code → kiểm thử → giao | Chia nhỏ thành các **sprint** (vòng 1–4 tuần), mỗi vòng ra một bản dùng được |
| Khi yêu cầu đổi | Đắt: nhận ra muộn | Rẻ hơn: lấy phản hồi sau mỗi vòng |
| Hợp khi | Yêu cầu rõ và ít đổi (phần cứng, hợp đồng cố định) | Yêu cầu chưa rõ hoặc hay đổi |
| Hạn chế | Thấy sản phẩm thật rất muộn | Dễ thành "làm hoài không xong" nếu thiếu mục tiêu |

**Scrum** là một khung agile: danh sách việc (backlog), sprint, họp ngắn hằng ngày, họp nhìn lại cuối sprint. Không bên nào "đúng tuyệt đối"; thực tế thường pha trộn.

### 8. Code review, CI/CD, kiểm thử

**Code review**: người khác đọc thay đổi của bạn trước khi gộp vào nhánh chính, để bắt lỗi, chia sẻ hiểu biết và giữ phong cách chung. **CI** (Continuous Integration, tích hợp liên tục): mỗi lần đẩy code, máy chủ tự biên dịch và chạy kiểm thử; hỏng thì chặn. **CD** (Continuous Delivery/Deployment, giao/triển khai liên tục): sau khi qua CI, bản build được đóng gói và đưa lên môi trường thử hoặc chạy thật bằng quy trình tự động.

**Kiểm thử đơn vị** (unit test) thử **một hàm/lớp riêng**, nhanh, chạy cả ngàn lần mỗi ngày. **Kiểm thử tích hợp** (integration test) thử nhiều phần **ghép lại** (code với database thật, hai service gọi nhau); chậm hơn nhưng bắt lỗi chỗ nối. Cả hai cần: unit test nhiều và nhanh làm đáy, integration test ít hơn ở trên. Một chương trình kiểm thử kết thúc bằng mã thoát 0 (đạt) hoặc khác 0 (hỏng); CI chỉ cần đọc mã thoát đó để biết "xanh hay đỏ". Thực tế dùng khung kiểm thử như GoogleTest hay Catch2 (mình chưa cài nên chưa chạy bài nào ở đây). Ca biên (0, rỗng, đầy) là chỗ lỗi hay nấp.

### 9. Kể dự án theo STAR

Phỏng vấn hay hỏi "kể về một dự án/lúc bạn gặp khó". **STAR** giữ câu trả lời gọn: **S**ituation (bối cảnh), **T**ask (nhiệm vụ của **bạn**), **A**ction (bạn đã làm gì, chọn gì, vì sao), **R**esult (kết quả, nên có con số). Ví dụ (đã ẩn mọi tên): "Hệ thống xử lý hàng đợi chạy chậm vào giờ cao điểm (S). Tôi nhận việc tìm nguyên nhân (T). Tôi đo thấy truy vấn quét cả bảng, thêm index và gom truy vấn N+1 thành một `JOIN`, rồi nhờ đồng nghiệp review (A). Thời gian xử lý giảm từ ~8 giây xuống dưới 1 giây (R)." (số tự nghĩ ra để minh họa.) Kể "tôi" cho phần việc của mình, nói thẳng điều đã học từ sai sót.

### Phần C. Nguyên lý game dev bằng C++

### 10. Vòng lặp game và bước thời gian cố định

Rạp chiếu hoạt hình: lặp mãi ba việc. **Input** (đọc phím/chuột), **update** (cập nhật thế giới: vị trí, va chạm), **render** (vẽ ra màn hình). Mỗi vòng là một **frame**. Máy nhanh chậm khác nhau nên mỗi frame dài ngắn khác nhau; **delta time** (dt) là thời gian giữa hai frame.

Nếu update dùng `x += vx * dt` thì frame giật (dt lớn) làm vật nhảy xa, và phép tính khác nhau tùy máy. Cách ổn định: **bước thời gian cố định**. Mỗi frame cộng dt vào một "bình tích lũy"; chừng nào bình đủ một bước (ví dụ 1/60 giây) thì chạy update đúng một bước đó và trừ bình. Frame chậm thì chạy bù nhiều update; frame nhanh thì có khi không update. Kết quả vật lý **giống nhau trên mọi máy**. Ví dụ 4 mô phỏng, không đọc đồng hồ thật.

### 11. Entity-component (ECS) ở mức ý tưởng

Thay vì lớp `Quai` kế thừa `Nhan_vat` kế thừa `Vat_the` (cây kế thừa sâu, [Bài 32](../nhom-4-oop-patterns/32-ke-thua.md)), **ECS** (Entity-Component-System) tách ba thứ: **entity** chỉ là một số định danh ("vật số 7"), **component** là mảnh dữ liệu thuần (vị trí, máu, hình), **system** là hàm xử lý mọi entity có đủ một tổ hợp component ("cho mọi vật có vị trí và vận tốc, cập nhật vị trí"). Thêm khả năng mới là gắn thêm component, không sửa cây lớp. Bài này chỉ nêu ý tưởng, không dựng một ECS đầy đủ.

### 12. Object pool và kỷ luật bộ nhớ

Trong vòng lặp nóng (chạy mỗi frame), `new`/`delete` ([Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md)) có hai tật: thời gian cấp phát **không dự đoán được** (có lúc chậm đột ngột, gây giật) và bộ nhớ **vụn dần**. Kỷ luật game: **không `new`/`delete` trong frame**; xin trước tất cả lúc khởi động.

**Object pool** (hồ chứa đối tượng) là cách làm đó: tạo sẵn N đối tượng; cần thì **mượn** một cái đang rảnh, xong thì **trả** lại để dùng tiếp. Giống kho khay đã rửa sẵn: không đúc khay mới mỗi bữa. Ví dụ 5 viết một pool cỡ cố định; hết chỗ thì trả về `nullptr` (quyết định xử lý thế nào là của người gọi).

### 13. Cache-friendly: AoS và SoA

**Cache** là bộ nhớ nhỏ, rất nhanh nằm gần CPU; CPU đọc RAM theo từng **dòng** (thường 64 byte), không đọc từng byte lẻ. Đọc một chỗ thì cả dòng vào cache; nếu phần còn lại của dòng là thứ bạn cũng cần thì ngon, còn không thì phí.

**AoS** (Array of Structures, mảng các cấu trúc): `vector<Hat>` mà mỗi `Hat` có 8 trường. Cập nhật chỉ `x` thì mỗi dòng cache chứa nhiều trường **không dùng**. **SoA** (Structure of Arrays, cấu trúc các mảng): mỗi trường một mảng riêng, nên dòng cache toàn `x` liền nhau. Ví dụ 6 đo hai kiểu. SoA không phải lúc nào cũng thắng: nếu mỗi vòng dùng **mọi** trường của một phần tử, AoS giữ chúng gần nhau và tốt.

### 14. Cầu nối Go

- **database/sql:** thư viện chuẩn có `database/sql` nhưng cần **driver** riêng (SQLite, Postgres...). `db.Query("... WHERE id = ?", id)` là tham số hóa (ký hiệu chỗ trống phụ thuộc driver: `?` hay `$1`). `db.Begin()` trả `*sql.Tx` có `Commit`/`Rollback`; nhớ `rows.Close()`. N+1 và injection giống hệt C++, ngôn ngữ nào cũng dính.
- **Game loop:** Go không có thư viện game chuẩn; các thư viện ngoài (như Ebitengine) thường gọi sẵn hàm `Update` theo nhịp cố định và hàm `Draw` riêng, đúng tinh thần bước cố định. Go có GC (dọn rác), nên pool vẫn có ích (`sync.Pool`) để giảm áp lực dọn rác; C++ không có GC nên kỷ luật "không `new` trong frame" nặng hơn.
- Mình chưa chạy mã Go nào cho bài này, nên không dán kết quả Go.

## 💻 Ví dụ code

### Ví dụ 1: quét toàn bảng, chỉ mục và N+1 (mô phỏng bằng C++)

**Chủ đề: cửa hàng.** Không phải database thật: `vector` là "bảng", `unordered_map` là "index", và hai biến đếm cho thấy **bao nhiêu dòng đã nhìn**. 50 đơn hàng, mỗi đơn thuộc một trong 1000 khách.

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

struct KhachHang { int id; std::string ten; };
struct DonHang { int id; int khachId; int tien; };

// "Bang" la mot day dong; "truy van" chi la ham dem so dong da phai nhin
int soDongDaNhin = 0;
int soLanHoi = 0;

const KhachHang* timQuet(const std::vector<KhachHang>& bang, int id) {   // (1)
    ++soLanHoi;
    for (const KhachHang& k : bang) {
        ++soDongDaNhin;
        if (k.id == id) return &k;
    }
    return nullptr;
}

int main() {
    std::vector<KhachHang> khach;
    for (int i = 1; i <= 1000; ++i) khach.push_back({i, "khach" + std::to_string(i)});
    std::vector<DonHang> don;
    for (int i = 1; i <= 50; ++i) don.push_back({i, 1 + (i * 37) % 1000, i * 10});

    // Chi muc (index): id -> vi tri dong
    std::unordered_map<int, std::size_t> chiMuc;                          // (2)
    for (std::size_t i = 0; i < khach.size(); ++i) chiMuc[khach[i].id] = i;

    // Tim 1 khach o cuoi bang: quet vs chi muc
    soDongDaNhin = 0;
    timQuet(khach, 1000);
    std::cout << "quet toan bang: nhin " << soDongDaNhin << " dong\n";
    std::cout << "dung chi muc  : nhin 1 dong (khach " << khach[chiMuc.at(1000)].ten << ")\n";

    // N+1: moi don hoi them 1 lan de lay ten khach
    soDongDaNhin = 0; soLanHoi = 1;                                       // (3) 1 lan lay danh sach don
    long tong = 0;
    for (const DonHang& d : don) tong += timQuet(khach, d.khachId)->ten.size();
    std::cout << "N+1 : " << soLanHoi << " lan hoi, " << soDongDaNhin << " dong\n";

    // JOIN: mot luot, gan san qua chi muc
    soDongDaNhin = 0; soLanHoi = 1;                                       // (4)
    long tong2 = 0;
    for (const DonHang& d : don) tong2 += khach[chiMuc.at(d.khachId)].ten.size();
    std::cout << "JOIN: " << soLanHoi << " lan hoi, " << don.size() << " dong don + tra chi muc\n";
    std::cout << (tong == tong2 ? "cung ket qua" : "KHAC ket qua") << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `timQuet` lật từng dòng đến khi gặp `id` (mỗi lần hỏi là một "chuyến đi") | `soDongDaNhin` tăng mỗi dòng |
| (2) | Dựng index: `id` → vị trí dòng, một lần | `chiMuc` có 1000 mục |
| `timQuet(khach, 1000)` | Khách cuối bảng nên nhìn hết 1000 dòng | |
| (3) | Vòng N+1: 1 lần lấy danh sách đơn + 50 lần hỏi tên khách bằng quét | |
| (4) | Vòng JOIN: đi qua đơn một lượt, tra tên qua index | cùng tổng độ dài tên |

**Kết quả khi chạy:**

```text
quet toan bang: nhin 1000 dong
dung chi muc  : nhin 1 dong (khach khach1000)
N+1 : 51 lan hoi, 24225 dong
JOIN: 1 lan hoi, 50 dong don + tra chi muc
cung ket qua
```

Mình chạy cả với ASan + UBSan: sạch, mã thoát 0. Hai cách ra **cùng kết quả**, khác nhau ở công sức: 24225 dòng nhìn so với 50 lần tra.

### Ví dụ 2: SQL thật, chạy bằng module `sqlite3` của Python

Máy mình **không có** `sqlite3.h` và không có chương trình dòng lệnh `sqlite3`, nên đoạn này **không phải C++**: mình chạy cùng SQLite (bản 3.45.1) qua module `sqlite3` có sẵn của Python 3, để xem câu SQL và kế hoạch thật. Đoạn SQL (rút gọn):

```sql
CREATE TABLE khach (id INTEGER PRIMARY KEY, ten TEXT NOT NULL);
CREATE TABLE don (id INTEGER PRIMARY KEY,
                  khach_id INTEGER NOT NULL REFERENCES khach(id), tien INTEGER);
-- khach: (1,An) (2,Binh) (3,Chi); don: (1,1,100) (2,1,50) (3,2,70)
SELECT k.ten, COUNT(d.id), SUM(d.tien)
FROM khach k LEFT JOIN don d ON d.khach_id = k.id GROUP BY k.id;

EXPLAIN QUERY PLAN SELECT COUNT(*) FROM nhatky WHERE nguoi = 42;
CREATE INDEX idx_nguoi ON nhatky(nguoi);
-- tk(ten, so CHECK (so >= 0)): A=100, B=0. Chuyen 150 tu A sang B trong 1 transaction.
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| `LEFT JOIN ... GROUP BY` | Mỗi khách một dòng kết quả: số đơn và tổng tiền; Chi chưa có đơn nên tổng là `NULL` |
| `EXPLAIN QUERY PLAN` (trước/sau `CREATE INDEX`) | Bảng `nhatky` có 200 000 dòng; kế hoạch đổi từ quét sang tìm bằng index |
| Chuyển tiền | Bước 1 (cộng B) thành công, bước 2 (trừ A còn -50) vi phạm `CHECK`, cả transaction bị hủy |
| Nối chuỗi vs `?` | Cùng đầu vào `x' OR '1'='1` cho kết quả khác nhau |

**Kết quả khi chạy** (mình chạy bằng Python, không phải C++):

```text
JOIN + GROUP BY:
('An', 2, 150)
('Binh', 1, 70)
('Chi', 0, None)

truoc index: SCAN nhatky
sau index  : SEARCH nhatky USING COVERING INDEX idx_nguoi (nguoi=?)

loi: CHECK constraint failed: so >= 0
sau rollback: [('A', 100), ('B', 0)]

noi chuoi : SELECT COUNT(*) FROM u WHERE ten='an' AND mk='x' OR '1'='1' -> 1
tham so ? : 0
```

Đọc kết quả: sau rollback `B` vẫn là 0, dù bước cộng B đã chạy trước khi lỗi (đó là Atomicity). Câu nối chuỗi trả `1` (đăng nhập "thành công" dù sai mật khẩu) vì `OR '1'='1'` luôn đúng; câu tham số hóa trả `0`.

### Ví dụ 3: gọi SQLite từ C++ (chưa chạy)

**Mình KHÔNG chạy được đoạn này**: máy mình không có `/usr/include/sqlite3.h` và không có quyền cài. Đây là mã mẫu theo C API của SQLite (đánh dấu `// bo-qua-kiem-tra`, kiểm tra cấu trúc sẽ bỏ qua), viết theo tài liệu; trên máy có `libsqlite3-dev` thì biên dịch với `-lsqlite3`.

```cpp
// bo-qua-kiem-tra
#include <sqlite3.h>
#include <iostream>

int main() {
    sqlite3* db = nullptr;
    if (sqlite3_open(":memory:", &db) != SQLITE_OK) return 1;           // (1)
    sqlite3_exec(db, "CREATE TABLE u (ten TEXT, mk TEXT);"
                     "INSERT INTO u VALUES ('an','bimat');",
                 nullptr, nullptr, nullptr);                            // (2)
    sqlite3_stmt* st = nullptr;
    sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM u WHERE ten = ? AND mk = ?",
                       -1, &st, nullptr);                               // (3)
    sqlite3_bind_text(st, 1, "an", -1, SQLITE_TRANSIENT);               // (4)
    sqlite3_bind_text(st, 2, "x' OR '1'='1", -1, SQLITE_TRANSIENT);
    if (sqlite3_step(st) == SQLITE_ROW)                                 // (5)
        std::cout << sqlite3_column_int(st, 0) << "\n";                 // (6)
    sqlite3_finalize(st);                                               // (7)
    sqlite3_close(db);
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Mở database trong bộ nhớ; `db` là con trỏ thô trả về từ thư viện C |
| (2) | Chạy nhanh các lệnh không có tham số |
| (3) | **Chuẩn bị** câu lệnh có hai chỗ trống `?` |
| (4) | **Gắn** giá trị (số thứ tự chỗ trống tính từ 1); chuỗi độc không bao giờ thành SQL |
| (5), (6) | Chạy một bước, đọc cột 0 (tính từ 0); dự kiến in `0` như bản Python, **chưa kiểm** |
| (7) | Phải `finalize` và `close` thủ công; viết gói RAII ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)) sẽ không quên |

Không có kết quả chạy nào để dán, nên mình không dán.

### Ví dụ 4: vòng lặp game với bước cố định (không đồ họa)

**Chủ đề: viên đạn.** Viên đạn bay với vận tốc 60 đơn vị/giây. `dtFrame` là thời gian từng frame cho sẵn (giả lập máy giật ở frame 2 và 5), nên kết quả **giống nhau mỗi lần chạy**.

```cpp
#include <iostream>

struct Vien { double x = 0, vx = 60; };            // vien dan: vi tri, van toc (don vi/giay)

int main() {
    const double buoc = 1.0 / 60.0;                // (1) moi buoc update dai dung 1/60 giay
    double tichLuy = 0;                            // thoi gian "chua tieu" cua cac frame
    Vien dan;
    int soUpdate = 0;

    // Gia lap 10 frame cua mot may "giat": thoi gian moi frame cho san, khong doc dong ho that
    const double dtFrame[10] = {0.016, 0.016, 0.050, 0.016, 0.016, 0.100, 0.016, 0.016, 0.016, 0.016};  // (2)

    for (int frame = 0; frame < 10; ++frame) {     // (3) vong lap game
        // 1) input: o day khong co ban phim, bo qua
        tichLuy += dtFrame[frame];                 // (4)
        while (tichLuy >= buoc) {                  // (5) update theo buoc co dinh
            dan.x += dan.vx * buoc;
            tichLuy -= buoc;
            ++soUpdate;
        }
        // 3) render: in ra thay cho ve hinh
        std::cout << "frame " << frame << ": x=" << dan.x << " (update tong: " << soUpdate << ")\n";
    }
    double tongGiay = 0;
    for (double d : dtFrame) tongGiay += d;
    std::cout << "tong thoi gian gia lap: " << tongGiay << " s, x ly thuyet = " << 60 * tongGiay << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Mỗi bước update dài đúng 1/60 giây | `buoc` hằng |
| (2) | Mười thời gian frame cho sẵn, thay cho đồng hồ thật | |
| (3), (4) | Mỗi frame cộng dt vào bình `tichLuy` | |
| (5) | Chừng nào bình đủ một bước: update một bước, trừ bình | `x` tăng 1 mỗi update |
| frame 2 (dt = 0.05) | Chạy bù 3 update trong một frame | `x`: 1 → 4 |
| frame 5 (dt = 0.1) | Chạy bù 6 update | `x`: 6 → 12 |

**Kết quả khi chạy:**

```text
frame 0: x=0 (update tong: 0)
frame 1: x=1 (update tong: 1)
frame 2: x=4 (update tong: 4)
frame 3: x=5 (update tong: 5)
frame 4: x=6 (update tong: 6)
frame 5: x=12 (update tong: 12)
frame 6: x=13 (update tong: 13)
frame 7: x=14 (update tong: 14)
frame 8: x=15 (update tong: 15)
frame 9: x=16 (update tong: 16)
tong thoi gian gia lap: 0.278 s, x ly thuyet = 16.68
```

Mình chạy cả với ASan + UBSan: sạch, mã thoát 0. `x` dừng ở 16 chứ không phải 16.68: phần dư (khoảng 0,0113 giây) vẫn nằm trong bình, chờ frame sau, nên không mất. Frame 0 chưa update vì 0,016 < 1/60 (0,01667 giây). Lưu ý: ở game thật cần **chặn trần** số update bù mỗi frame, kẻo máy quá chậm thì càng bù càng chậm.

### Ví dụ 5: object pool cỡ cố định

**Chủ đề: đạn.** `HoBoi<N>` giữ sẵn `N` viên trong một `std::array` và một danh sách "ô rảnh". Mượn/trả chỉ đổi chỉ số, không có `new`/`delete` nào. (`template <std::size_t N>` là template có tham số số nguyên, [Bài 34](../nhom-4-oop-patterns/34-template.md): kích thước biết lúc biên dịch.)

```cpp
#include <array>
#include <iostream>

struct Vien {
    double x = 0, y = 0;
    bool songDo = false;
};

template <std::size_t N>
class HoBoi {                                       // (1) kho N vien dan, xin truoc mot lan
public:
    HoBoi() {
        for (std::size_t i = 0; i < N; ++i) ranh_[i] = i;   // (2) moi o trong deu nam trong danh sach "ranh"
        soRanh_ = N;
    }
    Vien* muon() {                                  // (3) lay 1 vien: khong new
        if (soRanh_ == 0) return nullptr;
        Vien* v = &kho_[ranh_[--soRanh_]];
        v->songDo = true;
        return v;
    }
    void tra(Vien* v) {                             // (4) tra lai: khong delete
        v->songDo = false;
        ranh_[soRanh_++] = static_cast<std::size_t>(v - kho_.data());
    }
    std::size_t soDangDung() const { return N - soRanh_; }
private:
    std::array<Vien, N> kho_{};
    std::array<std::size_t, N> ranh_{};
    std::size_t soRanh_ = 0;
};

int main() {
    HoBoi<3> boi;
    Vien* a = boi.muon();
    Vien* b = boi.muon();
    Vien* c = boi.muon();
    std::cout << "dang dung: " << boi.soDangDung() << "\n";
    std::cout << "muon them: " << (boi.muon() == nullptr ? "het cho" : "con cho") << "\n";   // (5)
    boi.tra(b);
    Vien* d = boi.muon();                           // (6) tai su dung o vua tra
    std::cout << "d dung lai o cua b: " << (d == b ? "dung" : "sai") << "\n";
    std::cout << "dang dung: " << boi.soDangDung() << "\n";
    (void)a; (void)c;
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | Cả kho `kho_` (N viên) nằm sẵn trong đối tượng, không cấp phát heap | `kho_`: 3 viên |
| (2) | Ban đầu mọi ô đều rảnh: `ranh_` = {0, 1, 2} | `soRanh_` = 3 |
| (3) | `muon` lấy một chỉ số từ cuối danh sách rảnh, đánh dấu sống | |
| (5) | Mượn lần thứ 4 khi đã hết: trả `nullptr` | `soRanh_` = 0 |
| (4), (6) | `tra(b)` đưa chỉ số của `b` về danh sách rảnh; lần `muon` sau lấy đúng ô đó | `d == b` |

**Kết quả khi chạy:**

```text
dang dung: 3
muon them: het cho
d dung lai o cua b: dung
dang dung: 3
```

Mình chạy cả với ASan + UBSan: sạch, mã thoát 0. Bẫy: sau `tra(b)` con trỏ `b` vẫn còn đó nhưng ô đã thuộc về người khác; dùng `b` nữa là lỗi logic (và pool không báo).

### Ví dụ 6: AoS và SoA, đo thật

**Chủ đề: hạt.** 1 triệu hạt, mỗi hạt 8 `float` (32 byte); mỗi vòng chỉ cập nhật `x += vx`, lặp 20 lượt. Thời gian in ra `cerr` (dòng lỗi) vì **đổi theo mỗi lần chạy**; còn tổng `x` thì cố định.

```cpp
#include <chrono>
#include <iostream>
#include <vector>

const int N = 1000000;

struct HatAoS { float x, y, z, vx, vy, vz, mau, kichThuoc; };   // (1) 8 float = 32 byte moi hat

struct HatSoA {                                                 // (2) moi truong mot day rieng
    std::vector<float> x, y, z, vx, vy, vz, mau, kichThuoc;
    explicit HatSoA(int n) : x(n), y(n), z(n), vx(n), vy(n), vz(n), mau(n), kichThuoc(n) {}
};

int main() {
    std::vector<HatAoS> aos(N);
    HatSoA soa(N);
    for (int i = 0; i < N; ++i) { aos[i].x = soa.x[i] = float(i % 100); aos[i].vx = soa.vx[i] = 0.5f; }

    using dongHo = std::chrono::steady_clock;
    const int luot = 20;

    auto t0 = dongHo::now();
    for (int l = 0; l < luot; ++l)
        for (int i = 0; i < N; ++i) aos[i].x += aos[i].vx;       // (3) chi can x va vx
    auto t1 = dongHo::now();
    for (int l = 0; l < luot; ++l)
        for (int i = 0; i < N; ++i) soa.x[i] += soa.vx[i];       // (4)
    auto t2 = dongHo::now();

    double tongA = 0, tongS = 0;
    for (int i = 0; i < N; ++i) { tongA += aos[i].x; tongS += soa.x[i]; }
    std::cout << "AoS tong x = " << tongA << "\nSoA tong x = " << tongS << "\n";   // (5)
    std::cout << "sizeof(HatAoS) = " << sizeof(HatAoS) << " byte\n";
    auto ms = [](auto a, auto b) { return std::chrono::duration<double, std::milli>(b - a).count(); };
    std::cerr << "thoi gian AoS: " << ms(t0, t1) << " ms, SoA: " << ms(t1, t2) << " ms\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | AoS: một mảng 1 triệu `HatAoS`, mỗi phần tử chứa đủ 8 trường | khoảng 32 MB, liền nhau |
| (2) | SoA: tám mảng riêng, mỗi mảng 1 triệu `float` | 8 × 4 MB |
| (3) | Duyệt AoS chỉ chạm `x`, `vx` nhưng mỗi dòng cache kéo theo 6 trường không dùng | |
| (4) | Duyệt SoA chạm hai mảng `x`, `vx` liền nhau | chỉ 8 MB đọc mỗi lượt |
| (5) | Hai tổng phải bằng nhau: SoA đổi cách bố trí, không đổi kết quả | |

**Kết quả khi chạy:**

```text
AoS tong x = 5.95e+07
SoA tong x = 5.95e+07
sizeof(HatAoS) = 32 byte
thoi gian AoS: 68.7435 ms, SoA: 41.7355 ms
```

Dòng thời gian là một lần chạy trên máy mình với `-O0` (không tối ưu, mặc định của `g++` khi không ghi `-O`); chạy lại thì khác. Mình chạy `-O0` ba lần: AoS khoảng 69–112 ms, SoA khoảng 40–42 ms. Với `-O2` (bốn lần): AoS khoảng 70–129 ms, SoA khoảng 17–25 ms. **Số đo đổi theo máy, theo `-O`, theo lúc chạy**; chỉ nên tin xu hướng "SoA nhanh hơn khi chỉ chạm vài trường", không tin con số cụ thể. Mình chưa đo bằng `perf` (không có sẵn) nên chưa nhìn trực tiếp số cache miss.

## 🎤 Câu hỏi phỏng vấn hay gặp

- **`INNER JOIN` vs `LEFT JOIN`?** `INNER` chỉ giữ dòng khớp hai bên; `LEFT` giữ mọi dòng bảng trái, cột phải là `NULL` nếu không khớp (Ví dụ 2).
- **Index hoạt động ra sao, và giá phải trả?** Cấu trúc có thứ tự (thường cây B) giúp tìm nhanh thay vì quét cả bảng; tốn chỗ và làm ghi chậm hơn.
- **ACID là gì? Cho ví dụ.** Nguyên tử, nhất quán, cô lập, bền; chuyển tiền: trừ và cộng cùng thành công hoặc cùng hủy (Ví dụ 2).
- **N+1 là gì, sửa sao?** 1 truy vấn lấy danh sách rồi N truy vấn lẻ cho từng phần tử; sửa bằng `JOIN` hoặc `WHERE ... IN`.
- **SQL injection và cách chống?** Nối chuỗi làm dữ liệu thành lệnh; chống bằng tham số hóa, không bằng tự lọc ký tự.
- **CI/CD là gì? Unit test vs integration test?** CI: tự build + test mỗi lần đẩy; CD: tự động giao bản đã qua CI. Unit thử một đơn vị, nhanh; integration thử ghép nhiều phần, chậm hơn.
- **Kể một dự án khó?** Dùng STAR, nói phần việc của mình, có con số ở Result, không nêu tên riêng.
- **Vòng lặp game và bước cố định?** Input → update → render; bước cố định + bình tích lũy để vật lý không phụ thuộc tốc độ máy (Ví dụ 4).
- **Vì sao không `new` trong frame, và pool giải quyết gì?** Cấp phát có thời gian không dự đoán và gây vụn bộ nhớ; pool cấp trước, mượn/trả chỉ đổi chỉ số (Ví dụ 5).
- **AoS vs SoA?** SoA tốt khi mỗi vòng chỉ chạm vài trường của nhiều phần tử (đọc liền, ít phí cache); AoS tốt khi dùng mọi trường cùng lúc (Ví dụ 6).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Nối chuỗi vào câu SQL"
    `"... WHERE ten='" + ten + "'"` mở cửa cho injection (Ví dụ 2). Luôn dùng tham số `?` hoặc `$1`; tên bảng/cột không tham số hóa được, nên chỉ cho chọn từ danh sách cố định của bạn.

!!! warning "Lỗi 2: Tin rằng thêm index luôn tốt, hoặc không đo"
    Index sai cột chỉ tốn chỗ và làm ghi chậm. Với bảng nhỏ, quét còn nhanh hơn. Đoán là điều chắc chắn dẫn đến sai: xem kế hoạch truy vấn và đo.

!!! warning "Lỗi 3: Vòng lặp game dùng dt thô, hoặc không chặn trần bước bù"
    `x += vx * dt` với dt thất thường làm vật lý lệch giữa các máy. Dùng bước cố định; và giới hạn số update bù mỗi frame để tránh "vòng xoắn chết" khi máy quá chậm.

!!! warning "Lỗi 4: Cấp phát trong vòng lặp nóng, hoặc dùng con trỏ đã trả về pool"
    `new` mỗi frame gây giật. Với pool: sau `tra`, con trỏ đã thuộc về người khác (Ví dụ 5). Và đừng tối ưu mù: đo trước (Ví dụ 6 cho thấy số đổi theo máy).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="45" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau (mật khẩu thật của `an` là `bimat`). Người dùng gõ vào ô mật khẩu chuỗi `x' OR '1'='1`. Chuyện gì xảy ra?

```text
sql = "SELECT COUNT(*) FROM u WHERE ten='" + ten + "' AND mk='" + mk + "'"
-- ten = an, mk = x' OR '1'='1
```

- Câu SQL báo lỗi cú pháp vì có hai dấu nháy đơn liền nhau
- Kết quả là 0 vì `x' OR '1'='1` không phải mật khẩu `bimat`
- Điều kiện thành `... AND mk='x' OR '1'='1'`, luôn đúng, nên đăng nhập sai vẫn qua; cách chữa là tham số hóa bằng `?`
- Database tự nhận ra dữ liệu người dùng và chỉ coi nó là chuỗi thường

<p class="giai-thich" markdown>Dấu `'` trong dữ liệu đóng chuỗi sớm, phần `OR '1'='1'` đã thành lệnh SQL và luôn đúng, nên truy vấn trả 1 (mình chạy ở Ví dụ 2 và thấy đúng như vậy). Khi nối chuỗi thì database nhận một câu SQL hoàn chỉnh, không có cách nào biết đâu là dữ liệu. Câu có hai nháy liền nhau vẫn hợp lệ về cú pháp, nên không có lỗi nào dừng nó. Tham số hóa gửi dữ liệu riêng với câu lệnh, nên chuỗi độc chỉ còn là một mật khẩu sai.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Bảng `nhatky` có 1 triệu dòng, truy vấn `WHERE nguoi = 42` chạy chậm, kế hoạch hiện `SCAN nhatky`. Nên làm gì trước?

- Tạo index trên `nguoi`, rồi xem kế hoạch và đo lại
- Chép bảng sang file khác để đọc song song bằng nhiều luồng
- Đổi câu `SELECT` sang `SELECT *` để database lấy một lượt
- Xóa khóa chính của bảng vì khóa chính làm truy vấn chậm đi

<p class="giai-thich" markdown>`SCAN` nghĩa là database nhìn từng dòng; index trên cột trong `WHERE` đổi thành tìm bằng cây có thứ tự (Ví dụ 2: `SCAN` thành `SEARCH ... USING COVERING INDEX`). Sau đó đo lại để chắc chắn có lợi, vì index cũng tốn chỗ và làm ghi chậm hơn. Chép bảng đi nơi khác không giảm số dòng phải nhìn. Chọn thêm cột bằng `SELECT *` chỉ lấy thêm dữ liệu chứ không giúp tìm nhanh. Khóa chính thường chính là một index, nên xóa nó không làm nhanh lên.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. `buoc = 0.25`. Ba frame có `dt` lần lượt là 0.5, 0.75 và 0.25 giây (cộng vào `tichLuy` ở đầu mỗi frame). Tổng số lần `update` sau ba frame là bao nhiêu?

```text
tichLuy += dt;
while (tichLuy >= buoc) {
    update();
    tichLuy -= buoc;
}
```

- 3 lần, vì mỗi frame chạy đúng một `update`
- 4 lần, vì chỉ frame lớn nhất mới chạy `update` bù
- 1 lần, vì `tichLuy` được đặt lại về 0 sau mỗi frame
- 6 lần, vì 2 + 3 + 1 lần và không thừa thời gian

<p class="giai-thich" markdown>Với `buoc = 0.25`: frame đầu có 0.5 nên 2 lần; frame hai có 0.75 nên 3 lần; frame ba có 0.25 nên 1 lần; tổng 6, và bình về 0 vì các số này chia hết chính xác cho 0.25 trong nhị phân. Vòng `while` chạy nhiều lần trong một frame để bù, không phải một lần cố định. Bình không bị đặt về 0 mà chỉ trừ đi phần đã tiêu, nên phần dư (nếu có) sang frame sau. Và frame nào cũng được bù theo dt của nó, không riêng frame lớn nhất.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Một trang hiển thị 100 đơn hàng kèm tên khách. Mã lấy danh sách đơn bằng 1 truy vấn, rồi với mỗi đơn gọi thêm 1 truy vấn lấy tên khách. Có bao nhiêu truy vấn, và cách sửa nào đúng?

- 100 truy vấn; sửa bằng cách thêm index vào cột tên khách
- 101 truy vấn; sửa bằng `JOIN` (hoặc `WHERE id IN (...)`) để lấy tên cùng lúc
- 101 truy vấn; sửa bằng cách chạy 101 truy vấn đó song song bằng nhiều luồng
- 200 truy vấn; sửa bằng cách bọc cả 200 truy vấn trong một transaction

<p class="giai-thich" markdown>1 truy vấn lấy danh sách cộng 100 truy vấn lẻ là 101: đúng mẫu N+1. Gốc vấn đề là số chuyến đi, nên giải pháp là gom lại bằng `JOIN` hoặc `IN` (Ví dụ 1: 51 lần hỏi so với 1). Index làm mỗi truy vấn lẻ nhanh hơn nhưng không giảm số chuyến đi. Chạy song song vẫn là 101 chuyến, chỉ giấu bớt thời gian chờ và còn đè thêm tải lên database. Transaction đảm bảo tính trọn gói, không làm giảm số truy vấn.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Chuyển 150 từ tài khoản A sang B gồm hai lệnh `UPDATE` trong một transaction. Lệnh thứ nhất (cộng B) chạy xong, lệnh thứ hai (trừ A) vi phạm ràng buộc `so >= 0`. Điều gì được ACID bảo đảm?

- B giữ số dư mới, vì lệnh cộng đã chạy xong và thành công
- B giữ số dư mới cho đến khi người dùng tự gọi `ROLLBACK` sau đó
- Cả transaction bị hủy, B về lại số dư cũ
- Chỉ lệnh trừ bị bỏ qua, lệnh cộng giữ lại và lỗi được ghi vào nhật ký

<p class="giai-thich" markdown>Đó là Atomicity (nguyên tử): các lệnh trong transaction cùng thành công hoặc cùng bị hủy, nên số dư B về lại 0 (mình chạy ở Ví dụ 2, `sau rollback: [('A', 100), ('B', 0)]`). Việc lệnh đầu đã chạy xong không làm nó thành vĩnh viễn, vì chưa `COMMIT`. Khi một lệnh trong transaction lỗi, quyết định hủy được áp cho cả khối, không chờ người dùng gọi tay. Và "bỏ qua một lệnh" sẽ để lại tiền sinh ra từ hư không, đúng điều transaction sinh ra để ngăn.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn sau (pool có 3 ô, cả 3 đang được mượn). Điều gì đúng?

```text
pool.tra(b);
Vien* d = pool.muon();
b->x = 5;        // b là con trỏ đã trả
```

- `d` trỏ đúng ô của `b`, nên `b->x = 5` ghi nhầm vào viên đạn của `d`
- Dòng cuối là lỗi biên dịch, vì `tra` đã hủy đối tượng mà `b` trỏ tới
- `pool.muon()` trả `nullptr`, vì pool chưa dọn xong ô vừa được trả về
- `b` tự động trỏ sang ô rảnh khác, nên dòng cuối ghi vô hại

<p class="giai-thich" markdown>`tra` chỉ đưa ô về danh sách rảnh, không hủy gì, nên con trỏ `b` vẫn hợp lệ về mặt ngôn ngữ nhưng ô đã được `muon` giao cho `d` (Ví dụ 5 in `d dung lai o cua b: dung`). Ghi vào `b` thành ghi vào dữ liệu của người khác, một lỗi logic mà không công cụ nào báo. Vì `tra` vừa trả một ô rảnh, `muon` có ô để giao nên không trả `nullptr`. Trình biên dịch không biết gì về chuyện mượn/trả. Con trỏ cũng không tự di chuyển.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Một hệ thống có 1 triệu hạt, mỗi hạt có 8 trường. Mỗi frame, hàm đang xét dùng **cả 8 trường** của từng hạt để tính một giá trị rồi sang hạt kế. Kiểu bố trí nào thường hợp nhất?

- SoA, vì SoA luôn nhanh hơn AoS trong mọi trường hợp
- SoA, vì mảng riêng giúp CPU tự đoán trước phần tử tiếp theo
- Hai kiểu như nhau, vì số byte phải đọc là như nhau
- AoS, vì 8 trường của một hạt nằm sát nhau trong cache

<p class="giai-thich" markdown>Khi mỗi vòng dùng mọi trường của một phần tử, AoS giữ chúng liền nhau và một hai dòng cache đủ cho cả hạt. SoA phải đọc từ tám mảng khác nhau cho mỗi hạt. Ưu thế của SoA (Ví dụ 6) chỉ có khi vòng lặp chạm **vài** trường. Dù tổng byte có thể bằng nhau, số dòng cache chạm vào và cách chúng được dùng khác nhau. Và "luôn nhanh hơn" là câu tuyệt đối mà phép đo không ủng hộ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Trong cách kể STAR, câu nào là phần **Result** tốt nhất?

- "Mình thấy truy vấn quét cả bảng nên thêm index và nhờ đồng nghiệp review"
- "Thời gian xử lý giảm từ khoảng 8 giây xuống dưới 1 giây, và lỗi quá hạn biến mất"
- "Cả nhóm đã rất cố gắng và dự án rất quan trọng với công ty"
- "Tôi nhận nhiệm vụ tìm nguyên nhân hệ thống chậm vào giờ cao điểm"

<p class="giai-thich" markdown>Result nói điều **thay đổi nhờ việc bạn làm**, nên có số đo trước/sau. Câu về thêm index và nhờ review là Action (bạn làm gì). Câu về nhiệm vụ tìm nguyên nhân là Task. Còn lời khen chung chung không cho người nghe biết kết quả gì, và không nói phần của bạn.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Database:** bảng, khóa chính, khóa ngoại; `SELECT`/`JOIN`/`GROUP BY`; **index** biến quét cả bảng thành tìm nhanh (kế hoạch đổi từ `SCAN` sang `SEARCH`, mình chạy) nhưng tốn chỗ và làm ghi chậm hơn.
2. **Transaction và ACID:** trọn gói hoặc không (rollback giữ `B` bằng 0 trong ví dụ mình chạy); **N+1** sửa bằng `JOIN`; **SQL injection** chặn bằng tham số hóa, không bằng lọc dấu nháy. Mã SQLite C++ ở Ví dụ 3 mình **chưa chạy** (máy thiếu `sqlite3.h`).
3. **Quy trình:** waterfall tuần tự vs agile/scrum lặp ngắn; code review, CI/CD tự build và test, unit test nhanh nhiều + integration test ít hơn; kể dự án theo STAR, có số ở Result, không tên riêng.
4. **Game loop:** input → update → render, update theo bước cố định với bình tích lũy (kết quả không phụ thuộc máy, mình chạy), chặn trần bước bù; **ECS** tách entity/component/system.
5. **Bộ nhớ game:** không `new`/`delete` trong frame, dùng **object pool** (mượn/trả chỉ đổi chỉ số); **SoA** thường nhanh hơn AoS khi chỉ chạm vài trường (mình đo, số đổi theo máy và `-O`); Go: `database/sql` tham số hóa, game loop theo nhịp cố định.
