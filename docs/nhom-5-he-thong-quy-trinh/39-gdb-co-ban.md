# Bài 39 — gdb cơ bản: dừng chương trình và nhìn vào bên trong

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Dừng chương trình đúng chỗ bằng `break` (theo hàm, theo `tệp:dòng`, có điều kiện, `tbreak`) rồi đi từng bước bằng `next`, `step`, `finish`, `until`, `continue`.
    - Nhìn vào bên trong: `bt`, `frame`, `up`, `down`, `info locals`, `print`, `ptype`, `display`, `x`, và dùng `watch` để chứng minh một biến **không bao giờ đổi**.
    - Sửa thử giá trị ngay trong gdb (`set var`, `print x = ...`) để kiểm chứng giả thuyết, và viết được kịch bản `gdb -batch -x`.

**Bạn cần biết trước:** [Bài 38](38-bien-dich-lien-ket-build.md) (vì sao phải biên dịch `-g -O0`), [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack, khung gọi hàm) và [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`std::vector`).

## 🧠 Câu chuyện mở đầu

Bạn xem một **cuộn phim** về một ngày ở nhà bếp. Phim chạy một mạch, nhanh quá, và đúng ở cảnh quan trọng thì bạn chớp mắt. Bạn cần một **điều khiển từ xa**.

Nút **Tạm dừng** (đặt trước ở cảnh bạn nghi ngờ) là `break`. Nút **tua từng khung** là `next` và `step`. Ống kính **phóng to** vào một chiếc bát là `print`. Còn chuông **báo khi có ai chạm vào chiếc bát** là `watch`.

Điều khiển từ xa này chính là **gdb** (GNU Debugger, trình gỡ lỗi): nó chạy chương trình của bạn **bên trong nó**, cho dừng bất cứ lúc nào, rồi cho bạn nhìn mọi biến.

!!! info "Chỗ nào ví dụ cuộn phim không còn đúng?"
    Phim thật bạn chỉ xem được, không sửa được cảnh. gdb thì cho bạn **sửa giá trị biến ngay lúc đang dừng** (mục 6) rồi cho chạy tiếp. Và gdb thường **không tua ngược** được: lỡ bấm quá tay thì phải chạy lại từ đầu.

## 📖 Giải thích

### 1. Chuẩn bị: chương trình có lỗi logic

Cả bài dùng một chương trình nhỏ mà **không sập, không cảnh báo, nhưng in sai**. Nó tìm điểm cao nhất trong danh sách ba sinh viên, mà điểm đều âm (-5, -2, -9), nên đáp án đúng là `-2`.

```cpp
#include <iostream>
#include <string>
#include <vector>

struct SinhVien {
    std::string ten;
    int diem;
};

int diemCaoNhat(const std::vector<SinhVien>& ds) {
    int lon = 0;
    for (const SinhVien& sv : ds) {
        if (sv.diem > lon) {
            lon = sv.diem;
        }
    }
    return lon;
}

int main() {
    std::vector<SinhVien> ds = {{"An", -5}, {"Binh", -2}, {"Chi", -9}};
    int kq = diemCaoNhat(ds);
    std::cout << "cao nhat = " << kq << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 10 | Khai báo hàm `diemCaoNhat`, nhận danh sách bằng tham chiếu `const` ([Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md)) |
| 11 | `lon` bắt đầu bằng `0`: giả định "điểm cao nhất không thấp hơn 0" |
| 12–16 | Duyệt từng `sv`; chỉ khi `sv.diem > lon` mới cập nhật `lon` |
| 17 | Trả `lon` |
| 21–23 | Tạo ba sinh viên, gọi hàm, in kết quả |

Mình biên dịch bằng `g++ -std=c++17 -Wall -Wextra -g -O0 lon.cpp -o lon` (`-g -O0` theo [Bài 38](38-bien-dich-lien-ket-build.md)). Chạy ra `cao nhat = 0`: **sai**, vì không sinh viên nào có 0 điểm. Không có gì để g++ cảnh báo, nên đây đúng là chỗ cần gdb.

Máy mình: g++ 13.3 và gdb 15 trên Ubuntu. gdb có thể hỏi bật `debuginfod` (tải thông tin gỡ lỗi của thư viện từ mạng); mình tắt bằng `set debuginfod enabled off` để đầu ra gọn.

### 2. Dừng ở đâu: `break`, `run`

Mở gdb bằng `gdb ./lon`, rồi gõ lệnh ở dấu nhắc `(gdb)`. Bốn cách đặt điểm dừng (breakpoint) hay dùng:

| Lệnh | Dừng khi |
|---|---|
| `break diemCaoNhat` | Chương trình vào hàm đó |
| `break lon.cpp:13` | Chạy tới dòng 13 của tệp đó (có thể viết `break 13` nếu chỉ có một tệp) |
| `break lon.cpp:13 if sv.diem == -2` | Tới dòng 13 **và** điều kiện đúng |
| `tbreak diemCaoNhat` | Như `break` nhưng chỉ dừng **một lần** rồi tự xóa (temporary) |

`run` bắt đầu chạy chương trình. Dưới đây là phiên gdb thật. Mình thêm `(gdb)` trước mỗi lệnh cho dễ đọc, bỏ vài dòng thông báo thư viện luồng, còn lại là nguyên văn.

```text
(gdb) break diemCaoNhat
Breakpoint 1 at 0x2459: file lon.cpp, line 10.
(gdb) run

Breakpoint 1, diemCaoNhat (ds=std::vector of length 3, capacity 3 = {...}) at lon.cpp:10
10	int diemCaoNhat(const std::vector<SinhVien>& ds) {
(gdb) bt
#0  diemCaoNhat (ds=std::vector of length 3, capacity 3 = {...}) at lon.cpp:10
#1  0x00005555555566c8 in main () at lon.cpp:22
```

Hai điều đáng để ý.

Một: gdb dừng ở **dòng 10** (dòng khai báo), chứ không phải dòng 11. g++ thường gắn mã chuẩn bị đầu hàm (dựng khung stack, bước bảo vệ stack mà g++ trên Ubuntu bật sẵn) vào dòng khai báo, nên điểm dừng nằm ở đó; `next` một lần là sang dòng 11. Hai: gdb tự in `std::vector of length 3, capacity 3` thay vì dãy con trỏ khó đọc, nhờ **pretty-printer** (bộ in đẹp) đi kèm thư viện chuẩn của g++.

### 3. Đi từng bước: `next`, `step`, `finish`, `until`, `continue`

Đây là năm nút "tua" của điều khiển từ xa. Khác biệt `next` và `step` là chỗ người mới hay lẫn nhất.

| Lệnh (viết tắt) | Làm gì |
|---|---|
| `next` (`n`) | Chạy hết **một dòng**; gặp lời gọi hàm thì chạy cả hàm đó rồi mới dừng |
| `step` (`s`) | Chạy một dòng; gặp lời gọi hàm có thông tin gỡ lỗi thì **chui vào** hàm |
| `finish` | Chạy cho tới khi hàm hiện tại **trả về**, rồi in giá trị trả về |
| `until 17` | Chạy tới dòng 17 (hữu ích để thoát khỏi vòng lặp) |
| `continue` (`c`) | Chạy tiếp cho tới điểm dừng kế hoặc hết chương trình |

Mình đứng ở dòng 10, bấm `next` ba lần, rồi hỏi gdb trạng thái:

```text
(gdb) next
11	    int lon = 0;
(gdb) next
12	    for (const SinhVien& sv : ds) {
(gdb) next
13	        if (sv.diem > lon) {
(gdb) finish
0x00005555555566c8 in main () at lon.cpp:22
22	    int kq = diemCaoNhat(ds);
Value returned is $6 = 0
```

`finish` cho biết ngay hàm trả `0`: không cần đọc code, đã thấy kết quả sai. (`$6` là số thứ tự giá trị mà gdb tự đánh để bạn dùng lại; mục 4.)

Còn `step` ở dòng 12 thì sao? Dòng đó có lời gọi `ds.begin()` của `std::vector`. Mình thử, và `step` chui thẳng vào mã thư viện:

```text
(gdb) step
std::vector<SinhVien, std::allocator<SinhVien> >::begin (this=0x7fffffffd960) at /usr/include/c++/13/bits/stl_vector.h:883
883	      begin() const _GLIBCXX_NOEXCEPT
```

Đó không phải thứ bạn muốn xem. Quy tắc dễ nhớ: **mặc định dùng `next`**; chỉ dùng `step` khi bạn biết hàm sắp gọi là code của mình. Lỡ chui vào thì `finish` để ra.

### 4. Nhìn vào bên trong: `bt`, `frame`, `info`, `print`, `ptype`

Đang dừng ở dòng 13 (vòng lặp đầu, `sv` là An), mình hỏi liên tiếp:

```text
(gdb) info locals
sv = @0x55555556d2b0: {ten = "An", diem = -5}
__for_range = std::vector of length 3, capacity 3 = {{ten = "An", diem = -5}, {ten = "Binh", diem = -2}, {ten = "Chi", diem = -9}}
__for_begin = {ten = "An", diem = -5}
__for_end = {ten = "", diem = 0}
lon = 0
(gdb) print sv.diem
$2 = -5
(gdb) print ds[1]
$4 = {ten = "Binh", diem = -2}
(gdb) print ds.size()
$5 = 3
(gdb) ptype sv
type = const struct SinhVien {
    std::string ten;
    int diem;
} &
```

Cách đọc:

- `info locals` liệt kê biến cục bộ của khung hiện tại. Ba biến `__for_*` là biến ẩn mà g++ sinh ra cho vòng `for (... : ds)`; bạn có thể bỏ qua.
- `print` (viết tắt `p`) tính một **biểu thức** C++ và in kết quả: tên biến, `sv.diem`, `ds[1]`, thậm chí `ds.size()`. Mỗi kết quả được đánh số `$1`, `$2`, ... để dùng lại như `print $2 + 1`.
- `ptype` (print type) in **kiểu** đầy đủ; ở đây cho thấy `sv` là tham chiếu `const` tới `SinhVien`. Đừng `ptype` cả một `std::vector`: nó dội ra hàng trăm dòng.
- `info args` in tham số của hàm; `bt` (backtrace) in chuỗi hàm đang gọi nhau, `#0` là hàm trong cùng.

Muốn xem biến của hàm đã gọi mình, dùng `up` (lên một khung), `down` (xuống), hay `frame N`. Ví dụ `frame 1` nhảy sang `main` để xem `ds` ở đó. Chỉ khung đang chọn mới "thấy" biến của nó: đứng ở `main` mà `print lon` thì báo `No symbol "lon" in current context`.

Hai mẹo in: `print *ds._M_impl._M_start@2` in **hai phần tử đầu** của mảng nằm sau `vector` (cú pháp `@N` nghĩa là "N phần tử liền nhau"); `print/x sv.diem` in dạng hệ 16. Mình thử `print *ds.data()@2` thì gdb báo `Cannot evaluate function -- may be inlined`: hàm thành viên chưa được biên dịch ra thì gdb không gọi được. Khi đó đi vào dữ liệu thô như trên.

### 5. Theo dõi: `display`, điều kiện, `watch`

**`display`** là `print` tự lặp lại sau mỗi lần dừng. Mình đặt điểm dừng có điều kiện chỉ nổ ở sinh viên Bình (`diem == -2`), rồi `display` hai biểu thức và bước tiếp:

```text
(gdb) tbreak diemCaoNhat
Temporary breakpoint 1 at 0x2459: file lon.cpp, line 10.
(gdb) break lon.cpp:13 if sv.diem == -2
Breakpoint 2 at 0x24a9: file lon.cpp, line 13.
(gdb) run
Temporary breakpoint 1, diemCaoNhat (...) at lon.cpp:10
(gdb) continue

Breakpoint 2, diemCaoNhat (ds=std::vector of length 3, capacity 3 = {...}) at lon.cpp:13
13	        if (sv.diem > lon) {
(gdb) print sv
$2 = (const SinhVien &) @0x55555556d2d8: {ten = "Binh", diem = -2}
(gdb) display lon
(gdb) display sv.diem
(gdb) next
12	    for (const SinhVien& sv : ds) {
1: lon = 0
2: sv.diem = -2
(gdb) next
13	        if (sv.diem > lon) {
1: lon = 0
2: sv.diem = -9
```

(Dòng `Temporary breakpoint 1, ...` mình rút gọn ở chỗ `(...)`.) Điều kiện chỉ nổ ở Bình nên `continue` bỏ qua An. Hai dòng `1:`, `2:` là kết quả `display` tự in sau mỗi bước: bạn **thấy `lon` vẫn là 0 trong khi `sv.diem` toàn âm**. `undisplay 1` tắt cái đầu. Xem cả danh sách điểm dừng bằng `info breakpoints`, xóa bằng `delete 1`.

**`watch`** là chuông báo "có ai chạm vào biến này không". Mình đặt nó ngay sau khi `lon` được khởi tạo (đứng ở dòng 12) rồi cho chạy tiếp:

```text
(gdb) break lon.cpp:12
Breakpoint 1 at 0x246f: file lon.cpp, line 12.
(gdb) run

Breakpoint 1, diemCaoNhat (ds=std::vector of length 3, capacity 3 = {...}) at lon.cpp:12
12	    for (const SinhVien& sv : ds) {
(gdb) watch lon
Hardware watchpoint 2: lon
(gdb) continue

Watchpoint 2 deleted because the program has left the block in
which its expression is valid.
0x00005555555566c8 in main () at lon.cpp:22
22	    int kq = diemCaoNhat(ds);
```

Chuông **không kêu lần nào**: gdb chỉ báo rằng `lon` đã hết phạm vi khi hàm kết thúc. Đây là **bằng chứng** (không phải phỏng đoán) rằng sau dòng 11, không dòng nào ghi vào `lon`. Nên điều kiện `sv.diem > lon` không bao giờ đúng, và lỗi nằm ở giá trị khởi đầu.

Nếu đặt `watch lon` sớm hơn, trước khi dòng 11 chạy, chuông kêu **một lần**: gdb báo `Old value = 32767`, `New value = 0` (giá trị rác cũ biến thành 0 lúc khởi tạo). Mình đã thấy đúng như vậy khi thử.

### 6. Sửa thử ngay trong gdb: `print x = ...`, `set var`

Giả thuyết bây giờ: "nếu `lon` khởi đầu thấp hơn mọi điểm thì kết quả đúng". Kiểm chứng không cần sửa code: dừng ở dòng 17 (`return lon;`), gán `lon`, rồi `finish`.

```text
(gdb) break lon.cpp:17
Breakpoint 1 at 0x24e2: file lon.cpp, line 17.
(gdb) run

Breakpoint 1, diemCaoNhat (ds=std::vector of length 3, capacity 3 = {...}) at lon.cpp:17
17	    return lon;
(gdb) print lon
$1 = 0
(gdb) print lon = -1000
$2 = -1000
(gdb) finish
0x00005555555566c8 in main () at lon.cpp:22
22	    int kq = diemCaoNhat(ds);
Value returned is $3 = -1000
(gdb) continue
cao nhat = -1000
```

`print lon = -1000` là phép gán C++ chạy trong chương trình; `set var lon = -1000` làm đúng việc đó mà không in. Ở đây nó chưa chữa lỗi (mình gán ở cuối nên trả `-1000`), nhưng nó cho thấy bạn **thay được trạng thái đang chạy**. Muốn kiểm chứng đúng giả thuyết thì gán `lon` ngay sau dòng 11, trước vòng lặp. Mọi thay đổi chỉ sống trong lần chạy này: tệp `lon.cpp` không đổi, bạn vẫn phải sửa code thật (phần ví dụ).

### 7. Xem bộ nhớ thô: `x`

Đôi khi cần xem **byte** chứ không phải biến. Lệnh `x/<số lượng><định dạng><cỡ> <địa chỉ>` (examine, soi) làm việc đó: định dạng `d` là số thập phân, `x` hệ 16, `s` chuỗi chữ, `i` lệnh máy; cỡ `b` byte, `w` 4 byte. Đứng ở vòng cuối (`sv` là Chi):

```text
(gdb) x/dw &sv.diem
0x55555556d320:	-9
(gdb) x/s sv.ten._M_dataplus._M_p
0x55555556d310:	"Chi"
(gdb) x/8xb &sv.diem
0x55555556d320:	0xf7	0xff	0xff	0xff	0x00	0x00	0x00	0x00
```

`-9` nằm trong bộ nhớ là bốn byte `f7 ff ff ff` (số âm kiểu bù hai; byte thấp đứng trước, vì máy này viết số theo kiểu little-endian). Đây là nền để đọc lỗi bộ nhớ ở [Bài 40](40-gdb-nang-cao-core-dump.md).

### 8. Chạy kịch bản và TUI

Gõ cùng một chuỗi lệnh nhiều lần thì chán. Ghi chúng vào tệp (mỗi dòng một lệnh) rồi chạy `gdb -batch -x kichban.gdb ./lon`: `-batch` nghĩa là chạy hết lệnh rồi **thoát**, không dừng chờ bạn. Tệp mình dùng:

```text
set debuginfod enabled off
break lon.cpp:17
commands
  silent
  printf "lon = %d\n", lon
  continue
end
run
```

Khối `commands ... end` gắn việc cần làm vào điểm dừng: `silent` (không in thông báo dừng), in một dòng rồi `continue`. Chạy thật ra:

```text
lon = 0
cao nhat = 0
[Inferior 1 (process 476577) exited normally]
```

Kịch bản này nhìn `lon` mà không cần ngồi canh. **Cẩn thận**: nếu một lệnh trong tệp `-x` bị lỗi, gdb báo `Error in sourced command file` và **bỏ các lệnh còn lại**. Mình gặp đúng chuyện đó khi một dòng `print *p` với `p` rỗng nằm giữa kịch bản ([Bài 40](40-gdb-nang-cao-core-dump.md)). Thêm lệnh nhỏ lẻ thì dùng `-ex "lệnh"`, mỗi cờ một lệnh.

**TUI** (text user interface) chia màn hình terminal làm hai: nửa trên là mã nguồn có đánh dấu dòng đang dừng. Bật bằng `gdb -tui ./lon` hoặc bấm `Ctrl+X` rồi `A` khi đang ở gdb. Mình chỉ nhắc tên; bài này không dùng.

### 9. Bảng tra nhanh

| Việc | Lệnh | Viết tắt |
|---|---|---|
| Chạy chương trình (từ đầu) | `run` | `r` |
| Đặt điểm dừng | `break hàm` / `break tệp:dòng` | `b` |
| Điểm dừng có điều kiện | `break ... if biểu_thức` | |
| Điểm dừng một lần | `tbreak ...` | |
| Liệt kê / xóa điểm dừng | `info breakpoints` / `delete N` | `i b` |
| Chạy một dòng, không chui vào hàm | `next` | `n` |
| Chạy một dòng, chui vào hàm | `step` | `s` |
| Chạy tới khi hàm trả về | `finish` | |
| Chạy tới dòng N | `until N` | `u N` |
| Chạy tiếp | `continue` | `c` |
| Chuỗi hàm đang gọi | `backtrace` | `bt`, `where` |
| Chọn khung | `frame N`, `up`, `down` | `f N` |
| Biến cục bộ / tham số | `info locals` / `info args` | |
| In biểu thức | `print biểu_thức` | `p` |
| In kiểu | `ptype tên` | |
| Tự in sau mỗi lần dừng | `display biểu_thức` / `undisplay N` | |
| Báo khi biến bị ghi | `watch biến` | |
| Gán giá trị | `set var x = 5` hoặc `print x = 5` | |
| Xem bộ nhớ | `x/4dw &biến` | |
| In mã nguồn quanh dòng hiện tại | `list` | `l` |
| Thoát | `quit` | `q` |

Bấm Enter trong gdb sẽ **lặp lệnh trước đó**, tiện khi cần `next` liên tục.

!!! info "Bạn biết Go?"
    Trình gỡ lỗi chuẩn của Go là **Delve** (`dlv`), không phải gdb, vì gdb không hiểu tốt goroutine của Go. Ý tưởng giống hệt: `dlv debug` biên dịch rồi chạy, rồi bạn gõ `break main.go:10`, `continue`, `next`, `step`, `print x`, `bt` (và lệnh riêng `goroutines` để liệt kê goroutine). Để gỡ lỗi dễ, Go cũng cần tắt tối ưu: `go build -gcflags="all=-N -l"` (`-N` tắt tối ưu, `-l` tắt inline) tương ứng với `-O0` của bạn. Máy mình không cài `dlv` nên mình chưa chạy nó; phần `-gcflags` mình đã biên dịch thử được.

## 💻 Ví dụ code

### Ví dụ: sửa lỗi `lon` và kiểm chứng bằng gdb

Từ bằng chứng ở mục 5, lỗi nằm ở giá trị khởi đầu. Sửa: bắt đầu bằng điểm của sinh viên đầu tiên, và xử lý danh sách rỗng riêng.

```cpp
#include <iostream>
#include <string>
#include <vector>

struct SinhVien {
    std::string ten;
    int diem;
};

int diemCaoNhat(const std::vector<SinhVien>& ds) {
    if (ds.empty()) {
        return 0;
    }
    int lon = ds.front().diem;
    for (const SinhVien& sv : ds) {
        if (sv.diem > lon) {
            lon = sv.diem;
        }
    }
    return lon;
}

int main() {
    std::vector<SinhVien> ds = {{"An", -5}, {"Binh", -2}, {"Chi", -9}};
    std::cout << "cao nhat = " << diemCaoNhat(ds) << "\n";
    std::vector<SinhVien> rong;
    std::cout << "rong = " << diemCaoNhat(rong) << "\n";
    return 0;
}
```

| Dòng | Việc |
|---|---|
| 11–13 | Danh sách rỗng thì không có "cao nhất", trả `0` (quy ước của hàm này) |
| 14 | `lon` bắt đầu bằng điểm đầu tiên: giờ nó **là một giá trị có thật** trong danh sách |
| 15–19 | Vòng lặp như cũ: chỉ cập nhật khi gặp điểm cao hơn |
| 24 | Với `-5`, `-2`, `-9`: `lon` đi `-5` rồi `-2`, các điểm sau không vượt nên giữ `-2` |
| 26–27 | Danh sách rỗng đi vào nhánh dòng 11 |

Kết quả: `cao nhat = -2` rồi `rong = 0`. Muốn gdb xác nhận, mình đặt `watch lon` ở đầu vòng lặp: lần này chuông kêu khi `lon` đổi từ `-5` sang `-2`, đúng điều bản cũ không làm được.

Bài học về **cách làm việc**, không chỉ về lỗi này: giả thuyết ("`lon` không bao giờ đổi") → chứng minh bằng `watch` → thử sửa trong gdb → sửa code thật → chạy lại. Đừng sửa code trước rồi mới tin.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Khác nhau giữa `next` và `step`?"
    Cả hai chạy một dòng. Gặp lời gọi hàm thì `next` chạy trọn hàm đó rồi dừng ở dòng kế, còn `step` chui vào bên trong (nếu hàm có thông tin gỡ lỗi). `finish` ra khỏi hàm hiện tại. Mặc định dùng `next`; `step` hay dẫn vào mã thư viện như `std::vector::begin`.

??? question "Breakpoint, watchpoint và catchpoint khác nhau thế nào?"
    Breakpoint dừng khi chương trình tới một **vị trí code** (hàm hay dòng). Watchpoint dừng khi một **vùng nhớ** bị ghi (`watch biến`), không quan tâm code nào ghi. Catchpoint dừng khi xảy ra một **sự kiện** như ném ngoại lệ (`catch throw`, [Bài 40](40-gdb-nang-cao-core-dump.md)). Điểm dừng có điều kiện (`break ... if`) dùng được cho breakpoint.

??? question "Vì sao phải biên dịch `-g` mới gỡ lỗi tử tế?"
    `-g` ghi tên biến, kiểu, và ánh xạ dòng nguồn với mã máy vào tệp ([Bài 38](38-bien-dich-lien-ket-build.md)). Không có nó gdb chỉ thấy địa chỉ và tên hàm: mình thử, `print lon` báo `No symbol "lon" in current context` và `bt` không có số dòng. `-g` không làm chương trình chạy chậm.

??? question "Làm sao biết một biến bị đổi ở đâu trong chương trình?"
    Dừng ở nơi biến còn đúng, rồi `watch biến`. Mỗi lần có lệnh ghi vào biến, gdb dừng, in giá trị cũ và mới, và `bt` cho biết hàm nào ghi. Nếu chuông không kêu lần nào, biến chưa từng bị ghi sau điểm đó (chính là bằng chứng ở mục 5).

??? question "Gỡ lỗi bằng gdb có sửa được code đang chạy không?"
    Sửa được **giá trị biến** (`set var x = 5`, `print x = 5`) và gọi hàm (`print ham(3)`) trong lần chạy hiện tại, để kiểm chứng giả thuyết nhanh. Nhưng không sửa được mã nguồn: muốn đổi chương trình phải sửa tệp `.cpp`, biên dịch lại.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Gỡ lỗi bản không có `-g` hoặc bản `-O2`"
    Không `-g`: không có tên biến, số dòng. Có `-O2`: biến `<optimized out>`, dòng nhảy lung tung, thậm chí điểm dừng không bao giờ nổ ([Bài 40](40-gdb-nang-cao-core-dump.md) cho ví dụ thật). Biên dịch lại `-g -O0` trước, rồi mới nghi gdb.

!!! warning "Lỗi 2: Dùng `step` ở mọi nơi"
    Một lần `step` ở dòng có `ds.begin()` đưa bạn vào tệp `stl_vector.h`, nơi không có lỗi của bạn. Dùng `next`, và `step` chỉ ở hàm của chính mình.

!!! warning "Lỗi 3: Tin rằng sửa trong gdb là đã sửa lỗi"
    `print lon = -1000` chỉ đổi bộ nhớ trong lần chạy này. Thoát gdb là mất. Dùng nó để **chứng minh** giả thuyết, rồi sửa code thật.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="39" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Bạn đặt `watch lon` khi đang đứng sau dòng `int lon = 0;` rồi `continue`. gdb không báo `Old value`/`New value` lần nào mà in `Watchpoint 2 deleted because the program has left the block in which its expression is valid`. Kết luận nào bảo vệ được?

- `watch` bị hỏng vì biến `lon` nằm trên stack, nơi CPU không theo dõi được
- Không lệnh nào ghi vào `lon` sau điểm đặt
- `lon` đã bị tối ưu hóa mất nên gdb không có chỗ nào để theo dõi
- Chương trình đã sập trước khi tới bất kỳ dòng nào ghi vào `lon`

<p class="giai-thich" markdown>Watchpoint dừng mỗi lần vùng nhớ của biểu thức bị ghi. Không dừng lần nào cho tới lúc hàm kết thúc (khi biến hết phạm vi, gdb tự xóa watchpoint) nghĩa là không có lệnh ghi nào xảy ra: bằng chứng rằng `lon` không đổi. Biến trên stack theo dõi được bình thường, bằng thanh ghi gỡ lỗi của CPU. Ở bản `-O0` biến còn nguyên, và chương trình vẫn chạy hết hàm (thấy ở dòng cuối: gdb dừng ở `main`).</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Đứng ở dòng `for (const SinhVien& sv : ds) {` (có gọi `ds.begin()` của `std::vector`). Bạn gõ `step` thay vì `next`. Chuyện gì xảy ra?

- Chương trình chạy hết vòng lặp rồi mới dừng
- gdb bỏ qua lời gọi `begin()` và dừng ở dòng kế tiếp trong hàm của bạn
- gdb báo lỗi vì `begin()` không phải hàm do bạn tự viết
- gdb chui vào mã `begin()` trong tệp thư viện chuẩn

<p class="giai-thich" markdown>`step` chui vào hàm được gọi nếu có thông tin gỡ lỗi, và `std::vector::begin` có (g++ cài kèm nguồn thư viện), nên gdb dừng ở `stl_vector.h`. Việc bỏ qua lời gọi là việc của `next`. `step` không tính "hàm của bạn hay của thư viện", chỉ cần có thông tin dòng. Không có chuyện chạy hết vòng lặp: `until` hay `continue` mới làm vậy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Bạn muốn biết hàm `diemCaoNhat` trả về gì mà không đọc từng dòng. Lệnh nào cho kết quả trực tiếp?

- `finish`, chạy tới khi hàm trả về rồi in giá trị trả về
- `until 17`, chạy tới dòng 17
- `frame 1`, chọn khung của `main`
- `display lon`, in `lon` mỗi lần dừng

<p class="giai-thich" markdown>`finish` chạy cho tới khi hàm hiện tại trả về rồi in `Value returned is $N = ...`, đúng thứ cần. `until` chạy tới một dòng nhưng không cho biết giá trị trả. `frame 1` chỉ chọn khung của hàm gọi, chưa chạy gì. `display lon` in `lon` sau mỗi lần dừng, mà `lon` chưa chắc bằng giá trị trả.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Bạn đặt `break lon.cpp:13 if sv.diem == -2` rồi `run`, `continue`. Gõ `print sv` khi gdb dừng. Dữ liệu là `{"An", -5}, {"Binh", -2}, {"Chi", -9}`. gdb in gì?

- `{ten = "An", diem = -5}`, vì An là phần tử đầu tiên của danh sách
- `{ten = "Chi", diem = -9}`, vì đó là phần tử cuối được duyệt
- `{ten = "Binh", diem = -2}`, phần tử thỏa điều kiện
- Báo lỗi vì `sv` chưa khởi tạo

<p class="giai-thich" markdown>Điều kiện `sv.diem == -2` chỉ đúng khi `sv` đang là Bình, nên điểm dừng bỏ qua An và chỉ nổ ở lượt thứ hai; lúc đó `print sv` in Bình. Đã chạy qua lượt đầu nên An không còn là `sv`. Chi chưa được duyệt tới. `sv` được khởi tạo ở mỗi lượt vòng lặp, không phải lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Bạn biên dịch `g++ lon.cpp -o lon` (không `-g`), `break diemCaoNhat`, `run`, rồi `print lon`. gdb in `No symbol "lon" in current context`. Nguyên nhân gần nhất?

- gdb chưa hiểu kiểu `std::vector` nên từ chối in mọi biến
- Tệp không có thông tin gỡ lỗi
- `lon` là biến toàn cục nên gdb không in được theo tên
- `lon` chưa khởi tạo nên gdb từ chối in giá trị rác

<p class="giai-thich" markdown>Không có `-g` thì tệp không mang tên biến hay số dòng, nên gdb chỉ còn tên hàm (lấy từ bảng tên) và địa chỉ. Pretty-printer không liên quan đến việc có tên biến hay không. `lon` là biến cục bộ, không phải toàn cục. gdb in biến chưa khởi tạo bình thường (giá trị rác), không từ chối.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Kịch bản `-x` có dòng 1 `run` (chương trình dừng với `p=0x0`), dòng 2 `print p`, dòng 3 `print *p`, dòng 4 `bt`. Dòng 3 báo `Cannot access memory at address 0x0`. Điều gì xảy ra với dòng 4?

- `bt` vẫn chạy, vì gdb luôn chạy hết kịch bản dù có lệnh lỗi
- `bt` chạy nhưng in rỗng vì con trỏ rỗng đang được chọn
- `bt` chạy, thêm chữ `Error` vào cuối
- `bt` không chạy: lệnh lỗi làm gdb bỏ phần còn lại

<p class="giai-thich" markdown>Khi nạp bằng `-x`, một lệnh lỗi làm gdb in `Error in sourced command file` và bỏ các dòng sau. Muốn lệnh có thể lỗi mà vẫn chạy tiếp thì dùng mỗi lệnh một `-ex`. Con trỏ rỗng chỉ làm lỗi `print *p`, không ảnh hưởng `bt`. Nên `bt` đứng sau lệnh lỗi trong kịch bản thì không bao giờ được chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Bạn gõ `print lon = -1000` ở dòng `return lon;` rồi `continue`, chương trình in `cao nhat = -1000`. Sau đó bạn thoát gdb và chạy lại `./lon` bình thường. Kết quả?

- In `cao nhat = 0`, vì lệnh chỉ đổi bộ nhớ lúc đó
- In `cao nhat = -1000`, vì gdb ghi vào tệp
- In `cao nhat = -2`, vì gdb đã sửa lỗi logic giúp bạn luôn
- Không chạy được, vì tệp đã bị gdb khóa sau khi sửa

<p class="giai-thich" markdown>`print x = giá_trị` là phép gán trong bộ nhớ của tiến trình đang chạy dưới gdb; tệp chạy trên đĩa và mã nguồn không đổi. Lần chạy mới bắt đầu lại từ `int lon = 0` và in `0`. gdb không biết "đáp án đúng" để tự sửa. Tệp chạy không bị khóa sau khi gdb thoát.</p>
</div>

</div>

## 🔑 Tóm tắt

1. gdb là điều khiển từ xa cho chương trình: biên dịch `-g -O0`, `run`, đặt điểm dừng bằng `break hàm`, `break tệp:dòng`, `break ... if điều_kiện` hay `tbreak`; điểm dừng ở hàm nằm ở dòng khai báo, `next` một lần mới vào thân.
2. Đi từng bước: `next` (không chui vào hàm), `step` (chui vào, hay dẫn vào mã thư viện), `finish` (ra khỏi hàm và in giá trị trả), `until N`, `continue`; Enter lặp lệnh trước.
3. Nhìn vào trong: `bt`, `frame N`/`up`/`down`, `info locals`/`info args`, `print` (biểu thức, `ds[1]`, mảng bằng `@N`, `vector` và `string` đều đọc được nhờ pretty-printer), `ptype`, `display`, `x/4dw` cho byte thô.
4. `watch biến` dừng khi biến bị ghi; nếu nó kết thúc bằng thông báo "left the block" mà không nổ lần nào thì đó là bằng chứng biến không bao giờ đổi; `print x = 5`/`set var` sửa giá trị trong lần chạy hiện tại để thử giả thuyết, không sửa mã nguồn.
5. Kịch bản: `gdb -batch -x tệp ./prog` chạy rồi thoát (một lệnh lỗi trong tệp `-x` làm bỏ các lệnh sau; dùng `-ex` rời nếu cần), `commands ... end` gắn việc vào điểm dừng, TUI chỉ cần biết tên; Go có Delve (`dlv`) với ý tưởng giống hệt.
