# Bài 56 — Xử lý lỗi: exception, mã lỗi, optional hay expected

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Chọn được cách báo lỗi theo **tần suất** và **ai xử lý**: lỗi dự kiến, xảy ra thường xuyên thì trả `optional`/`variant`/mã lỗi; lỗi bất thường, hiếm, xử lý ở xa thì ném ngoại lệ; nói được khi nào KHÔNG nên dùng từng cách.
    - Giải thích chi phí của ngoại lệ (gần như không tốn khi không ném, đắt khi ném) bằng số đo thật, và biết `std::expected` là C++23 nên bài mô phỏng bằng `variant`.
    - Phân biệt ba mức an toàn ngoại lệ (cơ bản, mạnh, không ném) và đạt mức mạnh bằng "làm trên bản nháp rồi hoán đổi"; hiểu vì sao `vector` chỉ `move` khi hàm tạo di chuyển `noexcept` (đếm copy và move thật), vì sao hàm hủy không được ném.
    - Trả lời "hàm tạo lỗi thì làm sao" và "ngoại lệ trong luồng thì sao": dùng `std::exception_ptr` để chuyển sang luồng khác, RAII giữ khóa khi ném, so với `error`/`panic` của Go.

**Bạn cần biết trước:** [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (`throw`/`try`/`catch`, tháo ngăn xếp, `std::terminate`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (hàm tạo di chuyển, `noexcept`, `vector` tăng khối), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`optional`, `variant`), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (ngoại lệ thoát khỏi luồng), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (`lock_guard`), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`future`, `current_exception`), [Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md) (`unique_ptr`), [Bài 34](../nhom-4-oop-patterns/34-template.md) (`template <typename T>`).

## 🧠 Câu chuyện mở đầu

Về **nhà bếp** quen thuộc. Có hai loại sự cố. Loại thứ nhất là **hết hành**: chuyện hằng ngày, đầu bếp ngay tại thớt biết và xử lý luôn ("hết hành, dùng hành khô"), không ai cần rung chuông. Cách báo hợp lý là nói thẳng với người đứng cạnh: trả về một câu trả lời đặc biệt.

Loại thứ hai là **cháy bếp**: hiếm, nghiêm trọng, và người quyết định xử lý là quản lý đứng ngoài, cách vài tầng. Bấm chuông báo cháy: mọi đầu bếp dừng việc, **trước khi chạy ra mỗi người tắt bếp của mình và trả thẻ vào thớt** (RAII), rồi quản lý ở cửa quyết định. Chuông báo cháy chính là ngoại lệ.

!!! info "Chỗ nào ví von chuông báo cháy không còn đúng?"
    Chuông bếp thật vang cho cả bếp, còn ngoại lệ C++ chỉ đi ngược lên chuỗi hàm gọi của **một luồng**; nó không bay sang luồng khác (Ví dụ 3 ở 💻). Ngoài ra bấm chuông trong bếp thật rẻ, còn **ném** ngoại lệ trong C++ khá đắt (mục 2).

## 📖 Giải thích

### 1. Bốn cách báo lỗi cho cùng một việc

Việc: đọc một số nguyên từ chuỗi; chuỗi rỗng hoặc có ký tự khác chữ số là "lỗi". Ta viết bốn bản. Một chi tiết mới: `std::invalid_argument` là một kiểu ngoại lệ có sẵn (trong `<stdexcept>`) mang một câu thông báo; `e.what()` đọc câu đó ra. Kiểu ngoại lệ này (cùng `std::runtime_error`) kế thừa `std::exception` ([Bài 32](../nhom-4-oop-patterns/32-ke-thua.md)). Thêm một hàm quen: `std::stoi(chuoi)` (trong `<string>`) đổi chuỗi chữ số thành `int`, giống `strconv.Atoi` của Go; chuỗi số vượt cỡ `int` thì nó tự ném `std::out_of_range` (mình đã chạy với `"99999999999"`), nên ví dụ này chỉ dùng số ngắn.

```cpp
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

struct LoiDoc { std::string lyDo; };                 // (1) "tờ biên bản" khi đọc hỏng

bool laSo(const std::string& s) {                    // chuỗi không rỗng, toàn chữ số
    if (s.empty()) return false;
    for (char c : s) if (c < '0' || c > '9') return false;
    return true;
}
int giaTri(const std::string& s) { return std::stoi(s); }   // chỉ gọi khi laSo(s) đúng

int docNem(const std::string& s) {                   // cách 1: ném ngoại lệ
    if (!laSo(s)) throw std::invalid_argument("khong phai so: '" + s + "'");
    return giaTri(s);
}
std::optional<int> docOpt(const std::string& s) {    // cách 2: optional rỗng = lỗi
    if (!laSo(s)) return std::nullopt;
    return giaTri(s);
}
bool docMa(const std::string& s, int& ra) {          // cách 3: mã đúng/sai + tham số ra
    if (!laSo(s)) return false;
    ra = giaTri(s);
    return true;
}
std::variant<int, LoiDoc> docBien(const std::string& s) {   // cách 4: giá trị HOẶC lý do lỗi
    if (!laSo(s)) return LoiDoc{"khong phai so: '" + s + "'"};
    return giaTri(s);
}

int main() {
    std::vector<std::string> dau = {"12", "x7", "7", "", "30"};
    int t1 = 0, t2 = 0, t3 = 0, t4 = 0;
    for (const std::string& s : dau) {
        try { t1 += docNem(s); }                                      // (2)
        catch (const std::invalid_argument& e) { std::cout << "nem: " << e.what() << "\n"; }
        std::optional<int> r = docOpt(s);                             // (3)
        if (r) t2 += *r;
        int v = 0;
        if (docMa(s, v)) t3 += v;                                     // (4)
        std::variant<int, LoiDoc> kq = docBien(s);                    // (5)
        if (std::holds_alternative<int>(kq)) t4 += std::get<int>(kq);
        else std::cout << "variant: " << std::get<LoiDoc>(kq).lyDo << "\n";
    }
    std::cout << t1 << " " << t2 << " " << t3 << " " << t4 << "\n";
    return 0;
}
```

**Chạy từng dòng** (vòng lặp chạy với `"12"`, `"x7"`, `"7"`, `""`, `"30"` lần lượt)

| Dòng | Chuyện gì xảy ra | Ai phải nhớ kiểm tra |
|---|---|---|
| (2) | `"x7"` làm `docNem` ném; `catch` in `nem: ...`; `t1 += ...` bị bỏ qua | không ai: ngoại lệ tự nhảy tới `catch` |
| (3) | `docOpt("x7")` trả hộp rỗng; `if (r)` sai nên không cộng | người gọi, nhưng kiểu `optional` nhắc họ |
| (4) | `docMa` trả `false`, `v` giữ 0, không cộng | người gọi; quên kiểm tra là dùng `v` rác |
| (5) | `docBien` trả `LoiDoc`; nhánh `else` in lý do | người gọi, nhưng có cả lý do lỗi |

**Kết quả khi chạy:**

```text
nem: khong phai so: 'x7'
variant: khong phai so: 'x7'
nem: khong phai so: ''
variant: khong phai so: ''
49 49 49 49
```

Bốn tổng đều là 12 + 7 + 30 = 49. `optional` và mã lỗi chỉ nói "hỏng", không nói vì sao; `variant` và ngoại lệ mang được lý do. Cách 4 chính là hình dạng của `std::expected` của C++23 (mục 4).

**Thử thay đổi: thêm `[[nodiscard]]` trước `bool docMa`, rồi gọi `docMa("x7", t1);` mà bỏ kết quả.** Mình đã chạy: vẫn biên dịch, nhưng g++ cảnh báo `ignoring return value of 'bool docMa(...)', declared with attribute 'nodiscard'`. `[[nodiscard]]` (C++17) là nhãn đặt trước hàm để trình biên dịch nhắc "đừng bỏ giá trị trả về"; nó vá điểm yếu lớn nhất của mã lỗi là quên kiểm tra.

!!! info "Bạn biết Go?"
    Go chọn đúng cách 3-4: hàm trả `(giá trị, error)` và bạn viết `if err != nil` ở mỗi nơi. `fmt.Errorf("...: %w", err)` bọc lỗi thêm ngữ cảnh, `errors.Is(err, ErrAm)` kiểm tra nguyên nhân gốc (mình đã chạy với Go 1.27: in `ok 12`, `loi: doc "x7": ...`, `am: doc "-3": so am`). Cặp `(n, err)` làm đúng việc của `variant<int, LoiDoc>`; khác chỗ: Go **không ép** bạn nhìn `err`, còn `optional`/`variant` ép phải mở hộp mới lấy được giá trị.

### 2. Chi phí: không ném thì gần như miễn phí, ném thì đắt

Trên g++ và clang x86-64 Linux, ngoại lệ chạy theo mô hình "**zero-cost**" ("không tốn gì khi không ném"): trình biên dịch lập sẵn một **bảng** ghi "nếu ném ở địa chỉ lệnh này thì nhảy tới `catch`/dọn dẹp nào", và khối `try` không sinh lệnh nào trên đường chạy bình thường. Cái giá nằm ở nhị phân to hơn (có bảng; mình thử một chương trình nhỏ với `-O2`: thêm `-fno-exceptions` thì phần mã nhỏ đi cỡ 7%, con số đổi theo chương trình) và đôi khi cản vài tối ưu.

Khi **ném**, runtime phải cấp phát đối tượng ngoại lệ, tra bảng từng khung hàm đi ngược lên, và chạy hàm hủy của mọi đối tượng trên đường (tháo ngăn xếp, [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)). Giá tăng theo số khung phải tháo. Ta đo: 20 triệu lần gọi **không lỗi** qua `try`, rồi 100 nghìn lần **mọi lần đều lỗi**, so ném với `optional` rỗng. Hàm `nanoGiay` là một **template** ([Bài 34](../nhom-4-oop-patterns/34-template.md)) nhận một lambda và đo nó chạy bao lâu.

```cpp
#include <chrono>
#include <iostream>
#include <optional>
#include <stdexcept>

bool coLoi = false;                                // (1) cờ đọc từ ngoài: ngăn trình biên dịch tính sẵn

int chiaNem() {
    if (coLoi) throw std::runtime_error("loi");    // (2) báo lỗi bằng ngoại lệ
    return 3;
}
std::optional<int> chiaOpt() {
    if (coLoi) return std::nullopt;                // (3) báo lỗi bằng optional rỗng
    return 3;
}

template <typename F>
long long nanoGiay(F viec) {                       // đo thời gian chạy của một đoạn việc
    auto bat = std::chrono::steady_clock::now();
    viec();
    auto troi = std::chrono::steady_clock::now() - bat;
    return std::chrono::duration_cast<std::chrono::nanoseconds>(troi).count();
}

int main() {
    long long tong = 0;

    const int N1 = 20000000;                       // Phần 1: không lỗi nào, 20 triệu lần qua try
    long long khongLoi = nanoGiay([&] {
        for (int i = 0; i < N1; ++i) {
            try { tong += chiaNem(); } catch (const std::runtime_error&) { tong -= 1; }   // (4)
        }
    });

    coLoi = true;                                  // Phần 2: MỌI lần đều lỗi, 100 nghìn lần
    const int N2 = 100000;
    long long nem = nanoGiay([&] {
        for (int i = 0; i < N2; ++i) {
            try { tong += chiaNem(); } catch (const std::runtime_error&) { tong -= 1; }   // (5)
        }
    });
    long long opt = nanoGiay([&] {
        for (int i = 0; i < N2; ++i) {
            std::optional<int> r = chiaOpt();
            if (r) tong += *r; else tong -= 1;                                           // (6)
        }
    });

    std::cout << "khong loi: moi lan goi qua try duoi 50 ns? " << (khongLoi < 50LL * N1) << "\n";
    std::cout << "moi lan deu loi: nem cham hon optional it nhat 20 lan? " << (nem >= 20 * opt) << "\n";
    std::cout << "tong = " << tong << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Ghi chú |
|---|---|---|
| (1) | `coLoi` là biến toàn cục đổi lúc chạy, để trình biên dịch không xóa cả vòng lặp | cờ `false` ở phần 1, `true` ở phần 2 |
| (4) | `chiaNem` không ném, trả 3, `tong` tăng 3 mỗi vòng | 20 triệu x 3 = 60 000 000 |
| (5) | Mỗi vòng ném, nhảy vào `catch`, `tong` giảm 1 | -100 000 |
| (6) | `optional` rỗng, nhánh `else`, `tong` giảm 1 | -100 000 |

**Kết quả khi chạy** (ba lần liền đều như nhau, cả `-O0` lẫn `-O2`):

```text
khong loi: moi lan goi qua try duoi 50 ns? 1
moi lan deu loi: nem cham hon optional it nhat 20 lan? 1
tong = 59800000
```

Chương trình chỉ in `0`/`1` vì thời gian đo đổi theo máy. Khi mình in thẳng số đo (ba lần mỗi chế độ biên dịch), trên máy mình: gọi qua `try` khi không lỗi tốn khoảng 1,6 đến 6,7 ns một lần; **một lần ném** tốn khoảng 2200 đến 2900 ns (cỡ 2,5 micro giây); một lần `optional` rỗng tốn khoảng 20 đến 30 ns ở `-O0` và dưới 1 ns ở `-O2` (hàm quá nhỏ nên trình biên dịch gần như xóa nó). Máy bạn ra số khác, nhưng chênh lệch giữa "ném" và "trả giá trị" là cái cần nhớ: cỡ **một trăm lần** ở `-O0` (2200 so với 20 đến 30 ns), và hàng nghìn lần ở `-O2`.

Hệ quả: ném ngoại lệ cho chuyện xảy ra 1 lần trong 1000 là ổn (cứ 1000 lần gọi có một lần ném thì trung bình mỗi lần gọi chỉ gánh thêm 2,5 micro giây chia 1000, tức cỡ 2,5 ns); ném cho chuyện xảy ra **thường xuyên** hoặc trong vòng lặp nóng là tự bắn vào chân.

### 3. Chọn cái nào: bảng quyết định

Hai câu hỏi quyết định: lỗi này xảy ra **thường hay hiếm**, và **ai xử lý**: người gọi ngay (gần) hay một tầng ở xa.

| Tình huống | Chọn | Vì sao |
|---|---|---|
| Tìm không thấy, ô có thể trống, "không có" là bình thường | `std::optional<T>` | Rẻ (cỡ ns), kiểu nhắc người gọi nhìn hộp rỗng |
| Có thể sai theo cách dự kiến **và** người gọi cần biết vì sao (kiểm tra input người dùng, phân tích chuỗi) | `variant<T, Loi>` hay struct; `std::expected` khi có C++23 | Mang được lý do lỗi, vẫn rẻ |
| Lỗi **hiếm**, nghiêm trọng, nơi xử lý cách nhiều tầng (hết bộ nhớ, đĩa đầy, mất kết nối, file cấu hình hỏng lúc khởi động) | Ngoại lệ | Tầng giữa không phải viết gì; RAII dọn tự động; đắt nhưng hiếm |
| Hàm tạo, toán tử (không có chỗ trả mã lỗi) | Ngoại lệ (hoặc hàm dựng `static` trả `optional`, Ví dụ 2 ở 💻) | Hàm tạo không có giá trị trả về |
| Vòng lặp nóng, lỗi xảy ra **thường** | Mã lỗi / `optional` | Một lần ném cỡ vài micro giây, đắt hơn cỡ trăm lần trở lên |
| Build tắt ngoại lệ (`-fno-exceptions`, hay quy ước của đội); ranh giới C API, plugin, thread | Mã lỗi ở **biên**; bắt hết ngoại lệ ngay trong biên | Ngoại lệ thoát khỏi biên mà không ai đỡ thì hành xử tùy cài đặt hoặc `terminate` |
| Lỗi do **lập trình viên** (vi phạm điều kiện đầu vào, bug) | `assert`, hay dừng sớm | Không nên "xử lý" bug bằng `catch` rồi chạy tiếp |

**Khi KHÔNG nên dùng ngoại lệ:** để điều khiển luồng bình thường ("tìm thấy thì ném ra khỏi vòng lặp"), trong vòng lặp nóng, hoặc khi lỗi là kết quả **dự kiến** của nghiệp vụ (người dùng gõ sai là chuyện thường). **Khi KHÔNG nên dùng `optional`/mã lỗi:** khi lỗi hiếm mà phải chuyển tiếp qua sáu tầng hàm, mỗi tầng chỉ thêm một dòng `if (!r) return nullopt;`; khi cần lý do thì `optional` không đủ chỗ.

Mã lỗi (số nguyên, `bool`, `errno` của C, `std::error_code` của thư viện chuẩn) có nhược điểm: không gì ép bạn kiểm tra. `[[nodiscard]]` ở trên giảm nhược điểm đó, chưa xóa hẳn.

### 4. `std::expected` là C++23: mô phỏng bằng `variant`

`std::expected<T, E>` (`<expected>`, C++23) là "giá trị `T` **hoặc** lỗi `E`": cách 4 ở mục 1 nhưng có API gọn. Mình thử `#include <expected>` trên g++ 11 với `-std=c++23`: `fatal error: expected: No such file or directory`, nên **không chạy được ở đây** và bài không dùng nó trong khối chạy. Hình dạng dùng, theo chuẩn C++23 (mình chưa chạy):

```cpp
// bo-qua-kiem-tra
std::expected<int, LoiDoc> docBien(const std::string& s) {
    if (!laSo(s)) return std::unexpected(LoiDoc{"khong phai so"});   // trả lỗi
    return giaTri(s);                                                // trả giá trị
}
// auto kq = docBien("x7");  if (kq) dung(*kq); else in(kq.error().lyDo);
```

Với C++17, dùng `variant<T, Loi>` như mục 1, hoặc tự viết một struct nhỏ chứa `optional<T>` và lý do. Khi nâng lên C++23, đổi sang `expected` gần như chỉ đổi tên kiểu và cách mở hộp.

### 5. `noexcept`: lời hứa, và vì sao `vector` đếm nó

`noexcept` sau danh sách tham số là lời hứa "hàm này không ném ngoại lệ ra ngoài". Hứa sai thì ngoại lệ ném ra gọi **thẳng `std::terminate`**, không còn cơ hội `catch`. Mình đã chạy ba trường hợp (g++ cảnh báo `-Wterminate`; cả ba thoát mã 134):

```cpp
// bo-qua-kiem-tra
void hua() noexcept { throw std::runtime_error("het tien"); }
int main() { try { hua(); } catch (const std::exception& e) { std::cout << "bat\n"; } }
```

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  het tien
```

Dòng `bat` không in: `catch` không bao giờ được thấy ngoại lệ.

Với **hàm hủy**: từ C++11 hàm hủy **ngầm định là `noexcept`**, kể cả hàm bạn tự viết mà không ghi gì thêm. Nên `~Hong() { throw 1; }` rồi cho một `Hong` ra khỏi khối là `terminate` ngay (mình đã chạy: `terminate called after throwing an instance of 'int'`). Muốn ném được phải viết `noexcept(false)`, nhưng vẫn nguy hiểm.

Nếu hàm hủy đó chạy **trong lúc đang tháo ngăn xếp vì một ngoại lệ khác** (`try { Hong h; throw 2; } ...`) thì có hai ngoại lệ cùng bay, và chuẩn bắt chương trình `terminate` (mình đã chạy: mã 134, không bao giờ in `bat`). Đó là lý do hàm hủy không được ném: thứ chạy khi dọn lỗi mà lại gây lỗi thì không còn ai dọn.

Nay đến câu hỏi phỏng vấn kinh điển: vì sao `vector` chỉ `move` phần tử khi hàm tạo di chuyển `noexcept` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md))? Vì `vector` muốn `push_back` đạt **bảo đảm mạnh** (mục 💻): nếu ném giữa chừng thì vector còn như cũ. Move lấy ruột phần tử cũ, ném nửa chừng thì không quay lại được; copy thì phần tử cũ còn nguyên. Ta đếm, và thử cho một lần copy ném.

```cpp
#include <iostream>
#include <stdexcept>
#include <vector>

int soCopy = 0, soMove = 0;                          // (1) bộ đếm chung

struct A {                                           // move có noexcept
    int x;
    A(int v) : x(v) {}
    A(const A& o) : x(o.x) { ++soCopy; }
    A(A&& o) noexcept : x(o.x) { ++soMove; }
};
struct B {                                           // y hệt, chỉ thiếu noexcept
    int x;
    B(int v) : x(v) {}
    B(const B& o) : x(o.x) { ++soCopy; }
    B(B&& o) : x(o.x) { ++soMove; }
};

template <typename T>
void dem(const char* ten) {
    soCopy = soMove = 0;
    std::vector<T> v;
    for (int i = 0; i < 100; ++i) v.push_back(T(i)); // (2) 100 lần push_back, không reserve
    std::cout << ten << ": copy = " << soCopy << ", move = " << soMove << "\n";
}

struct Dai {                                         // bản sao thứ 3 sẽ ném ngoại lệ
    int x;
    Dai(int v) : x(v) {}
    Dai(const Dai& o) : x(o.x) {
        if (++soCopy == 3) throw std::runtime_error("copy hong");          // (3)
    }
    Dai(Dai&& o) : x(o.x) {}                         // KHÔNG noexcept → vector sẽ chọn copy
};

int main() {
    dem<A>("A (move noexcept)");
    dem<B>("B (move khong noexcept)");

    std::vector<Dai> v;
    v.reserve(4);
    for (int i = 1; i <= 4; ++i) v.push_back(Dai(i));    // đầy chỗ: size 4, capacity 4
    soCopy = 0;
    try {
        v.push_back(Dai(5));                              // (4) phải xin khối mới, chép 4 phần tử cũ
    } catch (const std::runtime_error& e) {
        std::cout << "bat: " << e.what() << "\n";
    }
    std::cout << "size = " << v.size() << ":";
    for (const Dai& d : v) std::cout << " " << d.x;       // (5) vector cũ còn nguyên
    std::cout << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Kết quả |
|---|---|---|
| (2) với `A` | 100 `push_back`: 100 lần move phần tử mới, cộng 127 lần chuyển phần tử cũ (1+2+4+...+64) bằng move | copy 0, move 227 |
| (2) với `B` | Phần tử mới vẫn move (100); phần tử cũ bị **copy** vì move không `noexcept` | copy 127, move 100 |
| (4) | `v` đầy; `vector` xin khối mới, chép từng phần tử cũ; bản sao thứ 3 ném (3) | ngoại lệ bay lên `catch` |
| (5) | `vector` hủy các bản đã chép dở, trả khối mới; khối cũ chưa bị đụng | `size = 4`, 1 2 3 4 |

**Kết quả khi chạy** (cũng sạch dưới `-fsanitize=address,undefined`):

```text
A (move noexcept): copy = 0, move = 227
B (move khong noexcept): copy = 127, move = 100
bat: copy hong
size = 4: 1 2 3 4
```

Con số 127 là của cách tăng dung lượng gấp đôi trên g++; cài đặt khác có thể ra số khác. Còn quy tắc "thiếu `noexcept` thì copy" đến từ bảo đảm mà chuẩn đòi cho `push_back` (xem "mạnh" ở Ví dụ 1 bên dưới), nên cài đặt nào cũng phải theo. **Thử thay đổi: thêm `noexcept` vào hàm tạo di chuyển của `B`.** Mình đã chạy: `B` ra `copy = 0, move = 227`, giống hệt `A`.

## 💻 Ví dụ code

### Ví dụ 1: ba mức an toàn ngoại lệ, và "làm trên bản nháp rồi hoán đổi"

Khi một hàm ném giữa chừng, nó có thể đã sửa dở dữ liệu. Có ba mức bảo đảm, từ yếu đến mạnh:

- **Cơ bản (basic):** không rò rỉ, mọi bất biến ([Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) còn đúng, nhưng dữ liệu có thể đã đổi một phần.
- **Mạnh (strong):** hoặc thành công trọn vẹn, hoặc như chưa gọi (xong cả hoặc không gì cả).
- **Không ném (nothrow):** hứa không bao giờ ném: `swap` của `vector`, hàm di chuyển tốt, hàm hủy.

Cách đạt mức mạnh: **làm hết việc dễ hỏng trên bản nháp, rồi chốt bằng một bước không ném** (thường là `swap`, hoán đổi ruột hai đối tượng). Copy-and-swap của [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) là cùng ý: `operator=` nhận tham số **theo giá trị** nên việc chép xảy ra trước khi vào thân hàm; chép ném thì `*this` chưa bị đụng.

```cpp
#include <iostream>
#include <stdexcept>
#include <vector>

struct BangDiem {
    std::vector<int> diem;

    void themTaiCho(const std::vector<int>& them) {          // chỉ bảo đảm cơ bản
        for (int d : them) {
            if (d < 0 || d > 10) throw std::invalid_argument("diem ngoai 0..10");   // (1)
            diem.push_back(d);                                // (2) sửa thẳng vào dữ liệu thật
        }
    }
    void themNguyenKhoi(const std::vector<int>& them) {      // bảo đảm mạnh
        std::vector<int> nhap = diem;                         // (3) bản nháp
        for (int d : them) {
            if (d < 0 || d > 10) throw std::invalid_argument("diem ngoai 0..10");   // (4)
            nhap.push_back(d);                                // (5) chỉ sửa bản nháp
        }
        diem.swap(nhap);                                      // (6) chốt: hoán đổi ruột, không ném
    }
};

void in(const char* nhan, const BangDiem& b) {
    std::cout << nhan;
    for (int d : b.diem) std::cout << " " << d;
    std::cout << "\n";
}

int main() {
    std::vector<int> lo = {8, 9, -1, 7};                      // phần tử thứ ba là điểm hỏng
    BangDiem a, b;
    a.diem = {5};
    b.diem = {5};
    try { a.themTaiCho(lo); } catch (const std::invalid_argument&) { std::cout << "a: bi loi\n"; }
    try { b.themNguyenKhoi(lo); } catch (const std::invalid_argument&) { std::cout << "b: bi loi\n"; }
    in("a sau loi:", a);
    in("b sau loi:", b);
    b.themNguyenKhoi({8, 9, 7});                              // lô tốt: chốt thành công
    in("b sau lo tot:", b);
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | `diem` của `a` / `b` lúc này |
|---|---|---|
| (2) | `a` đẩy 8, 9 vào dữ liệu thật; tới `-1` thì (1) ném | `a` = 5 8 9; `b` = 5 |
| (3)(5) | `b` chép `diem` ra bản nháp, đẩy 8, 9 vào **nháp**; tới `-1` thì (4) ném, nháp bị hủy | `b` vẫn = 5 |
| (6) | Lô tốt `{8, 9, 7}`: nháp đẩy đủ, `swap` đổi ruột nháp với `diem` | `b` = 5 8 9 7 |

**Kết quả khi chạy:**

```text
a: bi loi
b: bi loi
a sau loi: 5 8 9
b sau loi: 5
b sau lo tot: 5 8 9 7
```

`a` đạt mức cơ bản: vẫn là một `vector` hợp lệ, không rò rỉ, nhưng đã chứa 8, 9 của một lô hỏng. `b` đạt mức mạnh: như chưa gọi. Giá phải trả: bản nháp là một lần **chép** toàn bộ, nên mức mạnh không miễn phí; dùng khi người gọi cần "xong cả hoặc không gì cả". Lưu ý `{8, 9, 7}` ở lời gọi cuối là một `vector` tạm dựng từ danh sách trong ngoặc nhọn ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md)).

### Ví dụ 2: hàm tạo lỗi thì làm sao?

Hàm tạo không có giá trị trả về, nên không trả được mã lỗi: cách chính là **ném**. Đối tượng mà hàm tạo chưa chạy xong thì **chưa từng ra đời**, nên hàm hủy **của nó** không chạy; nhưng các **thành viên đã dựng xong** vẫn bị hủy. Cách khác: hàm dựng `static` (gọi bằng `Cong::tao(...)`, không cần có đối tượng sẵn) trả `optional`, kèm hàm tạo `private` để ngoài chỉ dựng qua đó.

```cpp
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>

struct Cay {                                         // thành viên: có in khi sinh/tử
    Cay()  { std::cout << "tao Cay\n"; }
    ~Cay() { std::cout << "huy Cay\n"; }
};

struct KetNoi {
    Cay cay;                                         // (1) thành viên dựng TRƯỚC thân hàm tạo
    std::unique_ptr<int> bo;                         // (2) vùng nhớ ở heap, do unique_ptr giữ
    KetNoi(int cong) {
        bo = std::make_unique<int>(7);               // (3) xin vùng nhớ
        if (cong < 0) throw std::invalid_argument("cong am");   // (4) hàm tạo không thể trả mã lỗi
        std::cout << "KetNoi dung xong\n";
    }
    ~KetNoi() { std::cout << "huy KetNoi\n"; }
};

struct Cong {                                        // cách khác: hàm dựng trả optional
    int so;
    static std::optional<Cong> tao(int s) {          // (5) static: gọi bằng Cong::tao
        if (s < 0 || s > 65535) return std::nullopt;
        return Cong(s);
    }
private:
    Cong(int s) { so = s; }                          // (6) hàm tạo private: ngoài chỉ dựng qua tao()
};

int main() {
    try {
        KetNoi k(-1);                                // (7)
        std::cout << "khong toi duoc day\n";
    } catch (const std::invalid_argument& e) {
        std::cout << "bat: " << e.what() << "\n";
    }
    std::optional<Cong> a = Cong::tao(8080), b = Cong::tao(-5);
    std::cout << "a: " << (a ? a->so : -1) << ", b co gia tri? " << b.has_value() << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Đã dựng xong |
|---|---|---|
| (7) | Dựng `KetNoi`: trước hết thành viên `cay` dựng (in `tao Cay`), `bo` rỗng | `cay`, `bo` |
| (3)(4) | `bo` giữ một `int` ở heap; `cong < 0` nên ném; thân hàm tạo dừng, `KetNoi dung xong` không in | `cay`, `bo` |
| tháo ngăn xếp | Hủy các thành viên đã dựng: `bo` trả vùng nhớ, `cay` in `huy Cay`; **không** có `huy KetNoi` | không còn gì |
| `catch` | In `bat: cong am` | |

**Kết quả khi chạy** (cũng sạch dưới AddressSanitizer):

```text
tao Cay
huy Cay
bat: cong am
a: 8080, b co gia tri? 0
```

**Thử thay đổi: thay `unique_ptr<int> bo` bằng `int* bo`, `bo = new int(7);`, và `delete bo;` trong hàm hủy.** Mình đã chạy với `-fsanitize=address`: đầu ra giống hệt, nhưng LeakSanitizer báo `Direct leak of 4 byte(s)` với ngăn xếp chỉ vào `KetNoi::KetNoi`. Hàm hủy của `KetNoi` không chạy (đối tượng chưa ra đời) nên `delete bo` không bao giờ được gọi; `unique_ptr` là thành viên đã dựng xong nên tự trả. Luật: trong hàm tạo, **mỗi tài nguyên giữ bằng một thành viên RAII**, đừng giữ con trỏ thô.

### Ví dụ 3: ngoại lệ trong luồng, và RAII giữ khóa khi ném

Ngoại lệ không bay sang luồng khác. Ném ra khỏi hàm của `std::thread` mà không `catch` ngay trong luồng là `std::terminate` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)). Muốn luồng chính biết: bắt **ngay trong luồng**, gói ngoại lệ vào `std::exception_ptr` (một "gói đựng ngoại lệ", không phụ thuộc kiểu) bằng `std::current_exception()`, cất vào ô riêng, và `std::rethrow_exception` sau `join`. Đó cũng chính là điều `std::async` và `std::promise` làm giùm ([Bài 29](../nhom-3-da-luong/29-async-future.md)). Ta rút tiền từ một tài khoản chung dưới khóa; `-> int` ở lambda cuối chỉ nói rõ kiểu trả về vì thân lambda chỉ có `throw`.

```cpp
#include <exception>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

std::mutex khoa;
int soDu = 100;

void rut(int x) {
    std::lock_guard<std::mutex> giu(khoa);                      // (1) RAII: hàm hủy nhả khóa dù ném
    if (x > soDu) throw std::runtime_error("khong du tien: " + std::to_string(x));   // (2)
    soDu -= x;
}

int main() {
    const int soLuong = 4;
    int soTien[soLuong] = {30, 500, 20, 900};
    std::vector<std::exception_ptr> loi(soLuong);               // (3) mỗi luồng một ô riêng
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < soLuong; ++k) {
        cacLuong.emplace_back([&loi, &soTien, k] {
            try {
                rut(soTien[k]);
            } catch (...) {                                     // (4) bắt MỌI ngoại lệ ngay trong luồng
                loi[k] = std::current_exception();              // (5) gói lại, cất vào ô của mình
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();                   // (6) join xong mới đọc loi

    for (int k = 0; k < soLuong; ++k) {
        if (!loi[k]) continue;                                  // ô rỗng: luồng này không lỗi
        try {
            std::rethrow_exception(loi[k]);                     // (7) ném lại ở luồng chính
        } catch (const std::runtime_error& e) {
            std::cout << "luong " << k << ": " << e.what() << "\n";
        }
    }
    std::cout << "so du = " << soDu << "\n";                    // (8)

    std::future<int> f = std::async(std::launch::async, []() -> int {
        throw std::runtime_error("async cung vay");
    });
    try { f.get(); } catch (const std::runtime_error& e) { std::cout << "get: " << e.what() << "\n"; }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Trạng thái |
|---|---|---|
| (1)(2) | Luồng 1 và 3 xin rút 500, 900 > `soDu`: ném khi **đang cầm khóa**; hàm hủy của `giu` nhả khóa lúc tháo ngăn xếp | các luồng sau vẫn xin được khóa |
| (4)(5) | `catch (...)` ngay trong luồng; `current_exception()` gói ngoại lệ vào `loi[k]` (mỗi luồng ghi ô riêng nên không tranh chấp) | `loi[1]`, `loi[3]` có gói |
| (6) | `join` làm mọi luồng xong và cho luồng chính thấy `loi` | |
| (7) | `rethrow_exception` ném lại đúng ngoại lệ gốc, `catch` bắt được kiểu `runtime_error` | in theo thứ tự `k` |
| (8) | Chỉ luồng 0 (30) và 2 (20) rút được: 100 - 50 | `soDu = 50` |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch):

```text
luong 1: khong du tien: 500
luong 3: khong du tien: 900
so du = 50
get: async cung vay
```

Thứ tự **chạy** của bốn luồng thì không xác định, nhưng kết quả ổn định: 500 và 900 luôn lớn hơn mọi `soDu` có thể có (≤ 100), còn hai lần rút 30 và 20 luôn thành công bất kể thứ tự; ta in theo `k` sau `join`.

**Thử thay đổi: bỏ cả khối `try`/`catch` trong luồng, chỉ để `rut(soTien[k]);`.** Mình đã chạy: `terminate called after throwing an instance of 'std::runtime_error'` kèm `what():  khong du tien: ...`, mã thoát 134. Ngoại lệ không bay về `main`.

Còn khóa: so với `lock()`/`unlock()` tay làm treo mãi ở [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), ở (1) ngoại lệ không làm ai treo, vì hàm hủy của `lock_guard` chạy lúc tháo ngăn xếp.

!!! info "Bạn biết Go?"
    `panic` ứng với `throw`, `recover` ứng với `catch`, nhưng `recover` chỉ có tác dụng trong một hàm `defer` **của cùng goroutine**. Panic trong một goroutine mà không `recover` ngay trong nó thì cả chương trình chết: mình đã chạy `go func() { panic("...") }()` trong khi `main` có `defer` + `recover`: `recover` không bắt được, chương trình in `panic: trong goroutine` và thoát mã 2. Giống C++ ở chỗ cả hai không chuyển lỗi sang luồng khác; Go còn dùng `panic` ít hơn: văn hóa Go dành `error` cho lỗi dự kiến và `panic` cho tình huống không thể tiếp tục, gần với ranh giới "dự kiến hay bất thường" của bài này.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Khi nào dùng exception, khi nào trả mã lỗi hay optional? Thế nếu đây là hot path?"
    Hỏi hai thứ: lỗi này thường hay hiếm, và ai xử lý. Lỗi **dự kiến, thường xảy ra, người gọi xử lý ngay** (tìm không thấy, kiểm tra input): `optional`, `variant`/`expected` khi cần lý do, hay mã lỗi. Lỗi **hiếm, nghiêm trọng, xử lý cách nhiều tầng** (hết bộ nhớ, mất kết nối): ngoại lệ, vì tầng giữa không phải viết gì và RAII dọn giùm. Ở hot path với lỗi thường xảy ra thì không ném: một lần ném cỡ vài micro giây (mình đo: khoảng 2,5 micro giây), đắt hơn trả `optional` cỡ trăm lần trở lên.

??? question "Exception có chậm không? Thế sao nhiều codebase cấm?"
    Khi **không ném**, trên g++/clang x86-64 gần như không tốn thời gian (mô hình zero-cost: tra bảng lúc ném, không chạy lệnh nào khi chạy bình thường); mình đo cỡ vài ns một lần gọi qua `try`. Khi **ném** thì đắt: cấp phát đối tượng ngoại lệ, tra bảng từng khung, chạy hàm hủy. Một số đội cấm ngoại lệ vì nhị phân to hơn, vì code cũ không an toàn ngoại lệ, hoặc vì muốn luồng lỗi hiện rõ trong chữ ký hàm. Đó là quyết định của đội, không phải do ngoại lệ "hỏng".

??? question "An toàn ngoại lệ có mấy mức? Cho ví dụ mức mạnh."
    Cơ bản: không rò rỉ, bất biến còn đúng, dữ liệu có thể đã đổi một phần. Mạnh: xong cả hoặc như chưa gọi. Không ném: hứa không bao giờ ném (`swap`, hàm hủy, move tốt). Đạt mức mạnh: làm trên bản nháp rồi chốt bằng `swap` không ném (ví dụ `themNguyenKhoi`), hoặc copy-and-swap cho `operator=`. Giá là một lần chép nháp.

??? question "Vì sao `std::vector` chỉ `move` khi hàm tạo di chuyển `noexcept`?"
    Khi tăng khối, `vector` chuyển từng phần tử cũ sang khối mới. Nếu move ném giữa chừng thì một phần khối cũ đã bị lấy ruột, không khôi phục được, vi phạm bảo đảm mạnh của `push_back`. Copy thì khối cũ còn nguyên. Nên `vector` dùng `std::move_if_noexcept`: move chỉ khi `noexcept`, không thì copy. Mình đếm: 100 `push_back`, không `noexcept` ra `copy = 127`, có `noexcept` ra `copy = 0`. Vì vậy hàm di chuyển và `swap` của lớp bạn nên có `noexcept`.

??? question "Hàm hủy ném ngoại lệ thì sao?"
    Hàm hủy mặc định là `noexcept`, nên ném ra khỏi nó là `std::terminate`. Dù ghi `noexcept(false)`, nếu nó chạy lúc đang tháo ngăn xếp vì ngoại lệ khác thì có hai ngoại lệ cùng bay và chương trình cũng `terminate` (mình đã chạy: mã 134). Hàm hủy phải tự nuốt lỗi (ghi log), không để thoát ra ngoài.

??? question "Ngoại lệ trong luồng thì sao? Giữ khóa mà ném có sao không?"
    Ngoại lệ không qua được ranh giới luồng; không bắt ngay trong hàm của luồng thì `terminate`. Cách đúng: bắt trong luồng, `std::current_exception()` cất vào `exception_ptr`, luồng chính `rethrow_exception` sau `join`; hoặc dùng `std::async`/`promise` tự làm việc này (`get()` ném lại). Giữ khóa bằng `lock_guard` thì ném an toàn: hàm hủy nhả khóa khi tháo ngăn xếp. Giữ bằng `lock()`/`unlock()` tay thì ném làm khóa không bao giờ được trả.

??? question "Hàm tạo bị lỗi thì làm sao?"
    Ném ngoại lệ, vì hàm tạo không có giá trị trả về. Đối tượng chưa ra đời nên hàm hủy của nó không chạy, nhưng thành viên đã dựng xong vẫn bị hủy; vì thế mỗi tài nguyên phải do một thành viên RAII giữ (`unique_ptr`), không dùng `new` thô trong hàm tạo (mình chạy ra rò rỉ 4 byte). Tránh hai giai đoạn "tạo rồi gọi `init()`" vì để lại đối tượng nửa vời. Nếu build tắt ngoại lệ thì dùng hàm dựng `static` trả `optional`.

??? question "`optional` và `expected` khác nhau thế nào? C++17 chưa có `expected` thì làm gì?"
    `optional<T>` chỉ nói "có hoặc không", không nói vì sao. `expected<T, E>` (C++23) mang lý do lỗi `E`. Ở C++17 dùng `std::variant<T, Loi>` hoặc tự viết struct nhỏ có `optional<T>` và lý do; mình đã viết bản `variant` chạy được ở mục 1.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Ném ngoại lệ cho chuyện thường xuyên xảy ra"
    "Tìm không thấy" ném `runtime_error` mỗi lần, hay dùng ngoại lệ để thoát vòng lặp, là chậm: mình đo một lần ném cỡ 2,5 micro giây. Chuyện thường xảy ra thì trả `optional` hoặc `variant`.

!!! warning "Lỗi 2: `noexcept` hứa bừa, hay hàm hủy ném ra ngoài"
    Gắn `noexcept` lên hàm vẫn có thể ném: ngoại lệ thoát ra là `terminate`, không `catch` nào kịp (mình đã chạy: mã 134). Quên `noexcept` ở hàm di chuyển thì `vector` âm thầm copy.

!!! warning "Lỗi 3: Bắt xong rồi nuốt, hoặc dùng mã lỗi mà không ép kiểm tra"
    `catch (...) {}` rỗng giấu mất bug và để dữ liệu nửa vời. Mã lỗi không ai ép kiểm tra: dùng `[[nodiscard]]` hay trả `optional`/`variant`. Thêm một thói quen: **ném theo giá trị, bắt theo `const&`** (`catch (const std::exception& e)`), để không sao chép và không cắt mất phần của kiểu con.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="56" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Hàm `timNguoiDung(ten)` tìm trong một danh sách; tìm không thấy là chuyện bình thường, và hàm được gọi hàng nghìn lần mỗi giây. Cách báo "không thấy" hợp lý nhất?

- Ném `std::runtime_error`, vì lỗi nào cũng nên báo bằng ngoại lệ
- Gọi `std::terminate`, vì không thấy nghĩa là dữ liệu sai
- Trả `std::optional` rỗng, vì "không thấy" là kết quả dự kiến và hay xảy ra
- Trả con trỏ thô tới một đối tượng rỗng dùng chung, rồi người gọi tự dò

<p class="giai-thich" markdown>Chuyện xảy ra thường xuyên và người gọi xử lý ngay thì nên được diễn đạt trong kiểu trả về; `optional` rỗng rẻ cỡ nano giây và nhắc người gọi kiểm tra. Ném ngoại lệ mỗi lần cỡ vài micro giây, chậm cỡ trăm lần trở lên ở đường nóng. Dừng chương trình vì một kết quả bình thường là phản ứng quá tay. Còn đối tượng rỗng dùng chung chỉ chuyển nỗi đau sang người gọi vì phải nhớ dò, mà không có kiểu nào nhắc.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Hàm tạo của `KetNoiDB` nhận một chuỗi kết nối sai định dạng. Bản build bật ngoại lệ, và đội muốn đối tượng nào đã tạo ra thì luôn hợp lệ. Nên làm gì?

- Ném ngoại lệ, vì hàm tạo không có giá trị trả về để báo lỗi
- Cho hàm tạo `return false;` để người gọi kiểm tra việc tạo đối tượng
- Đặt cờ `hopLe = false` rồi để hàm tạo kết thúc, người dùng tự kiểm cờ
- Gọi `exit(1)` ngay trong hàm tạo, vì chuỗi sai là lỗi không cứu được

<p class="giai-thich" markdown>Hàm tạo không có giá trị trả về nên không thể `return false`; cú pháp đó không hợp lệ. Cờ `hopLe` để lại một đối tượng nửa vời, đúng điều đội muốn tránh, vì ai quên kiểm cờ sẽ dùng đối tượng hỏng. `exit(1)` quá tay khi lỗi có thể xử lý ở nơi gọi. Ném ngoại lệ thì đối tượng không bao giờ ra đời, các thành viên đã dựng xong tự được hủy, và người gọi quyết định cách xử lý.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. `X` có cả hàm tạo sao chép lẫn hàm tạo di chuyển; hàm di chuyển **không** ghi `noexcept`. Vector đang đầy (3 phần tử, dung lượng 3). Khi `push_back` làm nó xin khối mới, 3 phần tử cũ được chuyển sang bằng cách nào?

```text
struct X { X(); X(const X&); X(X&&); };
std::vector<X> v;      // có 3 phần tử, capacity 3
v.push_back(X{});
```

- Bằng move, vì `X` có hàm tạo di chuyển nên `vector` luôn ưu tiên nó
- Không biên dịch được, vì hàm di chuyển phải có `noexcept` mới dùng với `vector`
- Bằng move nếu `X` nhỏ, bằng copy nếu `X` lớn, tùy cài đặt chọn
- Bằng copy, vì hàm di chuyển không hứa `noexcept` và `X` còn sao chép được

<p class="giai-thich" markdown>`vector` dùng `std::move_if_noexcept`: chỉ move khi hàm di chuyển hứa `noexcept` (hoặc kiểu không sao chép được); không thì copy, vì copy để khối cũ nguyên vẹn nếu có ngoại lệ giữa chừng. Nghĩ rằng cứ có hàm di chuyển là dùng là bỏ sót điều kiện `noexcept`. Thiếu `noexcept` không gây lỗi biên dịch, chỉ âm thầm chậm hơn. Kích thước kiểu không liên quan tới quyết định này.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn sau. Chuyện gì xảy ra khi chạy?

```text
struct H { ~H() noexcept(false) { throw 1; } };
try { H h; throw 2; } catch (int e) { std::cout << "bat " << e; }
```

- In `bat 1`, vì ngoại lệ ném sau cùng sẽ thay thế ngoại lệ ném trước
- Gọi `std::terminate`, vì hàm hủy ném khi đang tháo ngăn xếp
- In `bat 2`, vì hàm hủy ném `1` nhưng `catch` chỉ nhận ngoại lệ gốc
- In `bat 2` rồi `bat 1`, vì cả hai ngoại lệ đều bay lên tới `catch`

<p class="giai-thich" markdown>`throw 2` bắt đầu tháo ngăn xếp và hủy `h`; hàm hủy ném `1` khi ngoại lệ `2` còn đang bay. Chuẩn không cho có hai ngoại lệ cùng bay ra khỏi quá trình dọn dẹp nên gọi `std::terminate` (mình đã chạy: mã thoát 134, không in gì). Ngoại lệ sau không thay thế ngoại lệ trước như ở một số ngôn ngữ, và `catch` cũng không nhận được cả hai. Nếu hàm hủy ném khi không có ngoại lệ nào đang bay thì `noexcept(false)` mới cho ném bình thường, nhưng đó không phải đoạn này.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Hàm làm việc trong một `std::thread` đôi khi ném `std::runtime_error`, và luồng chính cần biết để báo cho người dùng. Cách đúng?

- Bọc `std::thread t(f); t.join();` trong `try`/`catch` ở `main`, vì `catch` ở đó sẽ bắt được
- Gọi `detach` luồng, để ngoại lệ tự bay về luồng chính khi luồng con kết thúc
- Bắt trong luồng, cất `std::current_exception()`, rồi ném lại ở luồng chính sau `join`
- Đánh dấu hàm của luồng `noexcept`, để ngoại lệ không còn xảy ra

<p class="giai-thich" markdown>Ngoại lệ chỉ đi ngược lên chuỗi gọi hàm của chính luồng đó; ở luồng chính, `catch` bọc quanh `t.join()` không bao giờ thấy nó, và ngoại lệ không bắt trong luồng là `std::terminate`. `detach` không tạo ra kênh nào đưa lỗi về. `noexcept` không ngăn lỗi xảy ra, chỉ biến việc ném thành `terminate`. Gói ngoại lệ bằng `exception_ptr` và ném lại sau `join` là cách chuyển lỗi qua ranh giới luồng; `std::async` làm việc này tự động qua `future`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Hàm `themNhieu(lo)` thêm nhiều phần tử vào `vector` thành viên, và ném giữa chừng nếu gặp phần tử hỏng. Để đạt bảo đảm **mạnh** (hỏng thì như chưa gọi), nên làm gì?

- Làm trên bản nháp, chỉ khi mọi bước xong mới chốt bằng `swap`
- Bọc cả thân hàm trong `try { ... } catch (...) {}` để ngoại lệ không bay ra ngoài
- Đánh dấu hàm `noexcept`, vì hàm đã hứa không ném thì không làm hỏng dữ liệu
- Dùng `lock_guard` bao cả thân hàm, vì khóa bảo vệ dữ liệu khỏi bị sửa dở

<p class="giai-thich" markdown>Mức mạnh đạt được bằng cách đưa mọi việc dễ hỏng vào bản nháp rồi chốt bằng một bước không ném như `swap`; nếu ném giữa chừng thì chỉ bản nháp bị bỏ. Nuốt ngoại lệ bằng `catch` rỗng thì dữ liệu thật đã bị sửa dở mà không ai biết. `noexcept` không làm việc hỏng biến mất; nó chỉ biến lỗi thành `terminate`. `lock_guard` chống data race giữa các luồng, không phục hồi dữ liệu khi ném.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Đọc đoạn sau. `Cay` có hàm hủy in `huy Cay`. Chạy `main` in ra gì?

```text
struct K {
    Cay c;
    K() { throw 1; }
    ~K() { std::cout << "huy K\n"; }
};
int main() { try { K k; } catch (int) { std::cout << "bat\n"; } }
```

- `huy K` rồi `bat`, vì `k` bị hủy khi ra khỏi khối `try`
- Chỉ `bat`, vì hàm tạo đã ném nên không có gì được hủy cả
- `huy Cay`, `huy K`, rồi `bat`, vì mọi phần của `k` đều bị hủy
- `huy Cay` rồi `bat`, vì `c` đã dựng xong còn `K` thì chưa ra đời

<p class="giai-thich" markdown>Hàm tạo của `K` ném nên `K` chưa dựng xong: hàm hủy `~K` không chạy. Nhưng thành viên `c` đã dựng xong trước thân hàm tạo, nên bị hủy trong lúc tháo ngăn xếp, in `huy Cay`, rồi tới `catch` in `bat`. Phương án "không có gì được hủy" quên các thành viên đã xong. Phương án có `huy K` giả định `K` đã ra đời. Lý do này cũng khiến tài nguyên trong hàm tạo phải do thành viên RAII giữ, không do con trỏ thô.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 8.** Hàm `docCauHinh(dong)` được nhiều luồng cùng gọi; nó có thể sai ở nhiều kiểu (thiếu khóa, sai kiểu giá trị, ngoài khoảng) và người gọi cần biết **kiểu sai nào** để báo người dùng. Chọn kiểu trả về nào ở C++17?

- `std::optional<int>`, vì rỗng đủ để người gọi biết đã có lỗi
- `std::variant<int, LoiCauHinh>`, vì mang được cả giá trị lẫn lý do lỗi
- `int` trả `-1` cho mọi kiểu lỗi, vì quen thuộc, rẻ và dễ kiểm
- `bool` cùng một biến toàn cục `lyDoCuoi` ghi lý do của lần lỗi gần nhất

<p class="giai-thich" markdown>Cần cả giá trị và lý do lỗi thì kiểu trả về phải chứa được hai thứ đó: `variant<int, LoiCauHinh>` làm đúng việc của `std::expected` (C++23). `optional` rỗng chỉ nói "có lỗi", không nói kiểu nào. Mã `-1` cũng chỉ có một dấu hiệu chung cho mọi lỗi và lẫn với giá trị hợp lệ nếu -1 là số được phép. Biến toàn cục `lyDoCuoi` bị nhiều luồng ghi chồng lên nhau là data race, nên không dùng được trong đề này.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Chọn theo **tần suất và người xử lý**: lỗi dự kiến, thường xảy ra, người gọi xử lý ngay thì trả `optional` (chỉ "không có"), `variant<T, Loi>` hay `std::expected` C++23 (có lý do), hay mã lỗi (nhớ `[[nodiscard]]`); lỗi hiếm, nghiêm trọng, xử lý cách nhiều tầng thì ném ngoại lệ. Không ném ngoại lệ cho luồng điều khiển thường hay vòng lặp nóng; hàm tạo không có chỗ trả mã lỗi nên ném (hoặc hàm dựng `static` trả `optional`).
2. Chi phí (mình đo): không ném thì gần như miễn phí (mô hình zero-cost, tra bảng lúc ném, vài ns mỗi lần gọi qua `try`); **mỗi lần ném cỡ 2,5 micro giây**, đắt hơn `optional` rỗng cỡ trăm lần trở lên. `std::expected` là C++23, g++ 11 không có `<expected>`, nên C++17 mô phỏng bằng `variant`.
3. Ba mức an toàn ngoại lệ: cơ bản (không rò rỉ, dữ liệu có thể đổi một phần), mạnh (xong cả hoặc như chưa gọi, đạt bằng "bản nháp rồi `swap` không ném" hay copy-and-swap, tốn một lần chép), không ném. Mọi tài nguyên giữ bằng RAII để ném vẫn dọn sạch (`lock_guard` nhả khóa, `unique_ptr` trong hàm tạo).
4. `noexcept` là lời hứa: hứa sai thì `terminate`; hàm hủy mặc định `noexcept`, ném khi đang tháo ngăn xếp cũng `terminate`. `vector` chỉ `move` khi move `noexcept` để giữ bảo đảm mạnh (mình đếm: 100 `push_back` ra `copy = 127` khi thiếu `noexcept`, `copy = 0` khi có), nên hàm di chuyển và `swap` nên `noexcept`.
5. Ngoại lệ không qua được ranh giới luồng: không bắt trong luồng là `std::terminate`; bắt `catch (...)`, cất `std::current_exception()` vào `exception_ptr`, `rethrow_exception` sau `join`, hay dùng `std::async`/`promise`. Go dùng `(giá trị, error)` như `variant`; `panic`/`recover` giống `throw`/`catch` nhưng panic trong goroutine không `recover` cũng làm chết cả chương trình.
