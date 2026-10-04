# Bài 21 — Big-O, danh sách liên kết, stack và queue

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Đọc và nói được **Big-O**: đếm số bước theo `n`, bỏ hằng số, phân biệt O(1), O(log n), O(n), O(n log n), O(n²), phân biệt tốt nhất/trung bình/xấu nhất và **amortized**, rồi đọc bảng độ phức tạp của `vector`, `deque`, `list`, `map`/`set`, `unordered_*`.
    - Tự cài **danh sách liên kết đơn** (nút, thêm/xóa đầu, tìm, hàm hủy trả mọi nút) và **đảo ngược** nó bằng ba con trỏ, nói đúng độ phức tạp của từng thao tác.
    - Phân biệt **stack** (vào sau ra trước) và **queue** (vào trước ra trước), dùng `std::stack`/`std::queue`, và tự cài queue bằng danh sách liên kết có con trỏ đuôi.

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (stack là vùng nhớ vào sau ra trước), [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (`->`, `nullptr`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (hàm `const`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, ASan báo rò rỉ), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (hàm hủy), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`= delete`), [Bài 16](16-vector.md), [Bài 17](17-string-array-deque-list.md) và [Bài 18](18-map-set-unordered.md) (các container).

!!! note "Phạm vi bài này"
    Cây nhị phân tìm kiếm, bảng băm tự cài và heap/`priority_queue` là một cụm riêng, để dành cho [Bài 22](22-bst-bang-bam-heap.md): nhồi chung sẽ quá dài. Bài này lo phần nền: Big-O, danh sách liên kết, stack, queue.

## 🧠 Câu chuyện mở đầu

Bạn cần tìm một cuốn sách trong thư viện có `n` cuốn, và bạn **đếm số lần phải cầm một cuốn lên xem**. Có ba cách tìm:

- Kệ chưa xếp thứ tự: tệ nhất bạn xem cả `n` cuốn.
- Kệ đã xếp theo tên: bạn mở giữa kệ, bỏ nửa không cần, rồi lặp lại, nên với một triệu cuốn chỉ cỡ hai chục lần cầm.
- Có sổ ghi sẵn "cuốn này ở ngăn nào": một lần.

**Big-O** là cách nói gọn việc đó: số bước **tăng thế nào khi `n` lớn lên**. Nó không đo giây, vì giây còn tùy máy; nó cho biết thuật toán nào "chịu được" dữ liệu lớn.

!!! info "Chỗ nào ví dụ thư viện không còn đúng?"
    Cầm một cuốn sách tốn ngang nhau, còn trong máy mỗi bước tốn khác nhau (đọc bộ nhớ liền kề nhanh hơn nhảy khắp heap). Vì vậy Big-O chỉ so sánh **cách tăng**, không bảo một đoạn code nhanh hơn hẳn đoạn kia với `n` nhỏ.

## 📖 Giải thích

### 1. Đếm bước theo n, rồi bỏ hằng số

Gọi `n` là số phần tử cần xử lý. Ba chữ cần nói trước: `long` là số nguyên cỡ lớn hơn `int` (thường 8 byte trên Linux 64-bit), `k /= 2` là `k = k / 2` (chia số nguyên, bỏ phần dư), và `n * x` là phép nhân. Chương trình dưới có bốn hàm, mỗi hàm **trả về số bước nó làm** (mỗi lần đụng vào một phần tử là một bước), để bạn thấy bốn kiểu tăng khác nhau.

```cpp
#include <iostream>
#include <vector>

long layDau() {
    return 1;                                  // (1) luôn một bước
}

long tong(int n) {
    long buoc = 0;
    for (int i = 0; i < n; ++i) ++buoc;        // (2) n bước
    return buoc;
}

long demCap(int n) {
    long buoc = 0;
    for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j) ++buoc;   // (3) n(n-1)/2 bước
    return buoc;
}

long chiaDoi(int n) {
    long buoc = 0;
    for (int k = n; k > 1; k /= 2) ++buoc;     // (4) mỗi vòng bỏ nửa
    return buoc;
}

int main() {
    std::vector<int> cacN = {10, 100, 1000};
    for (int n : cacN) {
        std::cout << "n=" << n << ": O(1)=" << layDau() << ", O(log n)=" << chiaDoi(n)
                  << ", O(n)=" << tong(n) << ", O(n log n)=" << n * chiaDoi(n)       // (5)
                  << ", O(n^2)=" << demCap(n) << "\n";
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Số bước |
|---|---|---|
| (1) | Việc như "lấy phần tử đầu": không phụ thuộc `n` | 1, dù `n` bằng bao nhiêu |
| (2) | Một vòng đi qua cả `n` phần tử | `n` |
| (3) | Vòng ngoài `n` lần, vòng trong ít dần: `(n-1) + (n-2) + ... + 1` | `n(n-1)/2`: 45 khi `n`=10 |
| (4) | `k` giảm một nửa mỗi vòng, nên số vòng là số lần chia đôi `n` tới 1 | 3 khi `n`=10, 9 khi `n`=1000 |
| (5) | Làm một việc cỡ log n cho **từng** trong `n` phần tử | `n` nhân số lần chia đôi |

**Kết quả khi chạy:**

```text
n=10: O(1)=1, O(log n)=3, O(n)=10, O(n log n)=30, O(n^2)=45
n=100: O(1)=1, O(log n)=6, O(n)=100, O(n log n)=600, O(n^2)=4950
n=1000: O(1)=1, O(log n)=9, O(n)=1000, O(n log n)=9000, O(n^2)=499500
```

Cột O(n²) cho thấy chữ **bỏ hằng số**: `demCap` làm `n(n-1)/2` bước, tức gần nửa `n²`, nhưng ta vẫn viết O(n²) vì khi `n` lớn và gấp đôi thì số bước **gần gấp bốn**. Tương tự, một hàm làm `3n + 5` bước là O(n): khi `n` lớn, `5` không đáng kể và `3` chỉ là hệ số. Ta giữ lại số hạng lớn nhất và bỏ phần còn lại.

| Ký hiệu | Đọc là | Ví dụ quen thuộc |
|---|---|---|
| O(1) | không đổi theo `n` | `v[i]`, thêm ở đầu `list` |
| O(log n) | `n` gấp đôi thì thêm một bước | tìm khóa trong `map` |
| O(n) | `n` gấp đôi thì gấp đôi | duyệt, `std::find` trong `vector` |
| O(n log n) | hơi nhiều hơn O(n) | `std::sort` ([Bài 20](20-algorithm-lambda.md)) |
| O(n²) | `n` gấp đôi thì gấp bốn | hai vòng `for` lồng nhau cùng chạy tới `n` |

!!! warning "Hay nhầm"
    O(1) **không** có nghĩa "nhanh": nó có nghĩa "không đổi theo `n`", và hằng số đó có thể lớn. Nên với `n` nhỏ, một `vector` O(n) thường vẫn thắng một cấu trúc O(1) cồng kềnh. Ngoài ra, vòng lồng không tự động là O(n²): nếu vòng trong chạy một số lần cố định (như 5 lần) thì cả hai vòng vẫn là O(n).

!!! info "Bạn biết Go?"
    Big-O không phụ thuộc ngôn ngữ nên bạn dùng y nguyên: `append` của slice là O(1) amortized, `map` của Go là O(1) trung bình, `sort.Slice` là O(n log n). Điều khác duy nhất là chi tiết cài đặt và hằng số.

### 2. Tốt nhất, trung bình, xấu nhất và amortized

Cùng một thao tác có thể tốn khác nhau tùy dữ liệu. `std::find` trong `vector`: nếu giá trị nằm ngay đầu thì 1 bước (**tốt nhất**), nếu nằm cuối hoặc không có thì `n` bước (**xấu nhất**). Khi phỏng vấn bạn nói **xấu nhất** trừ khi nói rõ là trung bình. Ở [Bài 18](18-map-set-unordered.md), `unordered_map` là O(1) **trung bình** nhưng O(n) xấu nhất, khi mọi khóa dồn vào cùng một hộp.

**Amortized** (chia đều) là loại bảo đảm thứ ba, hay nhầm với "trung bình". Nó không dựa vào dữ liệu may mắn: với **mọi** chuỗi `n` thao tác, tổng chi phí chia ra mỗi thao tác vẫn là hằng số, dù một vài lần riêng lẻ đắt. Ví dụ điển hình là `push_back` của `vector` ([Bài 16](16-vector.md)): hầu hết lần chỉ ghi vào ô trống, hiếm lần phải tái cấp phát và chuyển cả mảng sang chỗ mới. Chương trình dưới đếm thật số phần tử bị chuyển.

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v;
    long chep = 0;                                   // (1) tổng phần tử bị chuyển nhà
    std::size_t capCu = v.capacity();
    int lanDoi = 0;
    for (int i = 1; i <= 1000; ++i) {
        std::size_t sizeTruoc = v.size();
        v.push_back(i);                              // (2)
        if (v.capacity() != capCu) {                 // (3) vừa tái cấp phát
            chep += static_cast<long>(sizeTruoc);
            capCu = v.capacity();
            ++lanDoi;
        }
    }
    std::cout << "1000 lan push_back: " << lanDoi << " lan doi nha, chuyen " << chep
              << " phan tu, trung binh " << static_cast<double>(chep) / 1000
              << " phan tu chuyen moi lan push_back\n";
    return 0;
}
```

**Kết quả khi chạy:**

```text
1000 lan push_back: 11 lan doi nha, chuyen 1023 phan tu, trung binh 1.023 phan tu chuyen moi lan push_back
```

Mười một lần chuyển nhà cho 1000 lần thêm, tổng 1023 phần tử bị chuyển, tức khoảng một phần tử mỗi lần `push_back`: đó là "O(1) amortized". Con số `11` và `1023` là của g++ (capacity gấp đôi mỗi lần: 1, 2, 4, ..., 1024). Chuẩn C++ chỉ đòi `push_back` amortized hằng số, còn hệ số nhân tùy thư viện.

### 3. Bảng độ phức tạp của các container đã học

Dấu `–` là container đó không có thao tác ấy. Bảng là mức mà **chuẩn** C++ đòi (`map`/`set` thường cài bằng cây cân bằng, chuẩn chỉ đòi O(log n)), không phải số đo máy bạn.

| Thao tác | `vector` | `deque` | `list` | `map`/`set` | `unordered_*` |
|---|---|---|---|---|---|
| `[i]` theo chỉ số | O(1) | O(1) | – (đi từng nút: O(n)) | – | – |
| tìm một giá trị/khóa | O(n) | O(n) | O(n) | O(log n) | O(1) trung bình, O(n) xấu nhất |
| thêm ở cuối | O(1) amortized | O(1) | O(1) | – | – |
| thêm ở đầu | O(n) | O(1) | O(1) | – | – |
| chèn/xóa ở giữa (đã có vị trí) | O(n) | O(n) | O(1) | – | – |
| thêm/xóa theo khóa | – | – | – | O(log n) | O(1) trung bình, O(n) xấu nhất |

Đọc bảng bằng hai quy tắc. Một: ai tra theo **vị trí** thì cần bộ nhớ liền (`vector`, `deque`); ai tra theo **khóa** thì dùng `map` hoặc `unordered_*`. Hai: "O(1) chèn giữa của `list`" chỉ đúng **khi đã có iterator tới chỗ đó**, còn đi tới chỗ đó vẫn là O(n).

Mặc định vẫn chọn `vector`: các phần tử nằm liền nhau nên CPU đọc nhanh hơn nhiều so với đi theo mũi tên qua heap ([Bài 17](17-string-array-deque-list.md)), dù Big-O của `list` đẹp hơn ở vài ô.

### 4. Danh sách liên kết đơn tự cài

**Danh sách liên kết đơn** là chuỗi các **nút** (node) nằm rời nhau ở heap: mỗi nút giữ một giá trị và **địa chỉ của nút kế tiếp**, y như tờ giấy ghi số ngăn ([Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md)). Nút cuối giữ `nullptr` để báo "hết". Danh sách chỉ cần nhớ **nút đầu**; từ đó lần theo mũi tên là đi hết.

`std::list` của [Bài 17](17-string-array-deque-list.md) là bản **đôi** (mỗi nút có thêm mũi tên lùi); ở đây ta làm bản đơn (một chiều) vì đó là bản hay hỏi.

Có ba điểm cú pháp cần nói trước khi đọc code:

- Nút chứa con trỏ tới **chính kiểu của nó** (`Nut* tiep`): được phép, vì con trỏ luôn cùng một cỡ nên trình biên dịch biết `Nut` to bao nhiêu.
- Viết `Nut tiep;` (nhét nguyên một nút trong nút) là lỗi vì kích thước thành vô hạn; g++ báo `field 'tiep' has incomplete type 'Nut'`.
- `new Nut{x, dau}` xin một nút ở heap và điền hai trường theo thứ tự như `{"An", 9}` ở Bài 14; còn `Nut* dau = nullptr;` đặt giá trị ban đầu ngay tại khai báo trường.

Dòng `DanhSach() = default;` giữ lại hàm tạo mặc định: hễ đã khai báo hàm sao chép (kể cả `= delete`), trình biên dịch thôi không tự sinh nó nữa. Mình đã thử bỏ dòng này: `DanhSach ds;` báo `no matching function for call to 'DanhSach::DanhSach()'`.

```cpp
#include <iostream>

struct Nut {                       // (1) một nút: giá trị + mũi tên tới nút kế
    int gt;
    Nut* tiep;
};

struct DanhSach {
    Nut* dau = nullptr;            // (2) nút đầu; nullptr = danh sách rỗng

    DanhSach() = default;
    DanhSach(const DanhSach&) = delete;              // (3) cấm sao chép (Bài 11)
    DanhSach& operator=(const DanhSach&) = delete;
    ~DanhSach() {                                    // (4) hàm hủy trả MỌI nút
        while (dau != nullptr) xoaDau();
    }

    void themDau(int x) {          // O(1)
        dau = new Nut{x, dau};                       // (5)
    }

    void xoaDau() {                // O(1)
        Nut* cu = dau;
        dau = dau->tiep;                             // (6)
        delete cu;
    }

    Nut* tim(int x) const {        // O(n)
        for (Nut* p = dau; p != nullptr; p = p->tiep)   // (7)
            if (p->gt == x) return p;
        return nullptr;
    }

    void daoNguoc() {              // O(n) thời gian, O(1) bộ nhớ thêm
        Nut* truoc = nullptr;
        Nut* hien = dau;
        while (hien != nullptr) {
            Nut* ke = hien->tiep;                    // (8) nhớ nút kế trước khi cắt dây
            hien->tiep = truoc;                      // (9) quay mũi tên lại
            truoc = hien;                            // (10)
            hien = ke;                               // (11)
        }
        dau = truoc;                                 // (12)
    }

    void in() const {
        for (Nut* p = dau; p != nullptr; p = p->tiep) std::cout << p->gt << " ";
        std::cout << "\n";
    }
};

int main() {
    DanhSach ds;
    ds.themDau(1);
    ds.themDau(2);
    ds.themDau(3);
    ds.in();
    std::cout << "tim 2: " << (ds.tim(2) != nullptr ? "co" : "khong") << ", tim 9: "
              << (ds.tim(9) != nullptr ? "co" : "khong") << "\n";
    ds.daoNguoc();
    ds.in();
    ds.xoaDau();
    ds.in();
    return 0;
}
```

**Chạy từng dòng** (địa chỉ minh họa, máy bạn sẽ in số khác)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (5) lần 1 | `new Nut{1, dau}`: nút mới trỏ tới `dau` cũ (`nullptr`), rồi `dau` trỏ vào nó | `dau` → `0x1000`: [1 \| null] |
| (5) lần 2, 3 | Mỗi lần nút mới **chen lên đầu**, nó trỏ tới nút đầu cũ | `dau` → `0x1020`: [3 \| →`0x1010`] → [2 \| →`0x1000`] → [1 \| null] |
| (7) | `tim` đi từng nút, đúng giá trị thì trả địa chỉ nút, hết mà không thấy thì `nullptr`: O(n) | |
| (8)–(12) | `daoNguoc`, xem bảng theo vết bên dưới; `in()` chỉ đi dọc danh sách và in | |
| (6) | `dau` nhảy sang nút kế, rồi mới `delete` nút cũ (làm ngược lại là mất đường đi) | `dau` → nút `2` |
| (4) | Hết `main`: hàm hủy gọi `xoaDau` đến khi `dau` rỗng, trả mọi nút còn lại | |

**Kết quả khi chạy:**

```text
3 2 1 
tim 2: co, tim 9: khong
1 2 3 
2 3 
```

**Đảo ngược** là câu hỏi phỏng vấn kinh điển. Ý tưởng: đi dọc danh sách và quay từng mũi tên lại, cần ba con trỏ: `hien` là nút đang xử lý, `truoc` là nút đã xử lý ngay trước nó, `ke` là nút kế **nhớ trước khi cắt dây**. Bảng dưới theo dõi danh sách `3 → 2 → 1` (gọi các nút là A=3, B=2, C=1).

| Sau vòng | `ke` | Mũi tên vừa quay | `truoc` | `hien` | Phần đã đảo |
|---|---|---|---|---|---|
| (trước vòng 1) | – | – | `nullptr` | A | – |
| 1 | B | A → `nullptr` | A | B | A → null |
| 2 | C | B → A | B | C | B → A → null |
| 3 | `nullptr` | C → B | C | `nullptr` | C → B → A → null |

Hết vòng, `hien` là `nullptr` và `truoc` là nút cuối cũ, tức đầu mới: dòng (12) gán `dau = truoc`. Chỉ có ba con trỏ phụ nên bộ nhớ thêm là O(1), mỗi nút đụng một lần nên thời gian O(n).

**Thử thay đổi: bỏ vòng `while` trong hàm hủy (dòng (4)).** Mình đã biên dịch với `-fsanitize=address` và chạy: chương trình in đúng như cũ rồi LeakSanitizer báo `32 byte(s) leaked in 2 allocation(s)`. Đúng là hai nút còn lại (ba nút xin, `xoaDau` trả một), mỗi nút thường 16 byte trên máy 64-bit (một `int`, đệm, một con trỏ). Hàm hủy là chỗ RAII ([Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)) trả hết nút khi danh sách chết.

!!! warning "Hay nhầm: viết nút bằng `unique_ptr` cho gọn"
    Có thể viết `std::unique_ptr<Nut> tiep;` để khỏi gọi `delete` ([Bài 09](../nhom-1-nen-tang-bo-nho/09-unique-ptr.md)), và với danh sách ngắn nó chạy đúng. Nhưng hàm hủy của nút này hủy nút kế, nút kế hủy nút sau nó...: một kiểu **đệ quy** (hàm gọi lại chính nó, Bài 02), mỗi nút một tầng stack.

    Trên máy mình (Linux, stack 8 MB) danh sách 10 nghìn nút còn chạy; 100 nghìn nút sập lúc hủy khi biên dịch `-O0` (mã thoát 139 của shell) nhưng vẫn chạy ở `-O2`; 1 triệu nút sập cả ở `-O2`. Đặt `ulimit -s unlimited` thì 1 triệu nút lại chạy được. Ngưỡng cụ thể tùy giới hạn stack của máy bạn và chuẩn không bảo đảm gì; vòng lặp `delete` ở trên không phụ thuộc vào đó.

!!! info "Bạn biết Go?"
    Bài này viết bằng Go gần như y nguyên: `type Nut struct { Val int; Next *Nut }`, và đảo ngược cũng bằng ba con trỏ (`prev`, `cur`, `next := cur.Next`). Khác biệt là Go **không có** `delete` hay hàm hủy: bộ gom rác dọn các nút không còn ai trỏ tới. Trong C++, quên trả nút là rò rỉ (ASan báo), và `container/list` của Go ứng với `std::list`.

### 5. Stack và queue

**Stack** (ngăn xếp) là chồng đĩa: đĩa đặt sau cùng lấy ra trước, gọi là **LIFO** (last in, first out). **Queue** (hàng đợi) là hàng xếp mua vé: người đến trước được phục vụ trước, gọi là **FIFO** (first in, first out).

Vùng stack của [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) cũng theo luật LIFO (khung hàm gọi sau thì trả trước), nên chúng cùng tên. Nhưng `std::stack` là một kiểu thư viện chứa dữ liệu trong một container (mặc định là `deque`, `std::queue` cũng vậy), không phải vùng stack ấy.

`std::stack` (`#include <stack>`) và `std::queue` (`#include <queue>`) là **container adaptor** (bộ bọc): chúng giấu container bên trong và chỉ lộ vài thao tác. Vì vậy chúng không có iterator và không duyệt được. Bạn đổi container bên trong bằng tham số thứ hai: `std::stack<int, std::vector<int>>` được, còn `queue` cần container có `pop_front` nên dùng `deque` hoặc `list`.

`std::stack` có `push(x)` (đặt lên đỉnh), `top()` (xem đỉnh), `pop()` (bỏ đỉnh). `std::queue` có `push(x)` (đặt cuối hàng), `front()` (xem đầu hàng), `back()` (xem cuối hàng), `pop()` (bỏ đầu hàng). Cả hai có `empty()` và `size()`.

Mọi thao tác đó đều O(1). Trong code dưới, `||` là "hoặc" và `&&` là "và" (như Go). Chương trình dùng stack kiểm tra dấu ngoặc khớp nhau (bài kinh điển: ngoặc mở **gần nhất** phải đóng trước) và queue phục vụ khách theo thứ tự đến.

```cpp
#include <iostream>
#include <queue>
#include <stack>
#include <string>
#include <vector>

bool ngoacDung(const std::string& s) {
    std::stack<char> st;                                   // (1)
    for (char c : s) {
        if (c == '(' || c == '[') {
            st.push(c);                                    // (2) mở: cất lên đỉnh
        } else if (c == ')' || c == ']') {
            if (st.empty()) return false;                  // (3) đóng mà chưa có mở
            char mo = st.top();                            // (4) xem đỉnh
            st.pop();                                      // (5) bỏ đỉnh (pop không trả gì)
            if ((c == ')' && mo != '(') || (c == ']' && mo != '[')) return false;
        }
    }
    return st.empty();                                     // (6) còn mở chưa đóng thì sai
}

int main() {
    std::vector<std::string> mau = {"([])", "([)]", "(("};
    for (const std::string& s : mau)
        std::cout << s << " -> " << (ngoacDung(s) ? "dung" : "sai") << "\n";

    std::queue<std::string> hang;                          // (7)
    hang.push("An");
    hang.push("Binh");
    hang.push("Cuong");
    std::cout << "dau hang: " << hang.front() << ", cuoi hang: " << hang.back() << "\n";   // (8)
    while (!hang.empty()) {
        std::cout << "phuc vu " << hang.front() << "\n";
        hang.pop();                                        // (9)
    }
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1)–(2) | Với `"([)]"`: gặp `(` và `[` thì lần lượt cất lên đỉnh | stack, đỉnh bên phải: `( [` |
| (4)–(5) | Gặp `)` thì xem đỉnh: là `[`, không khớp `(` nên trả `false` ngay | `)` đòi `(` nhưng đỉnh là `[` |
| (6) | Với `"(("`: đọc hết mà stack còn hai ngoặc mở nên `empty()` sai | `( (` |
| (7)–(8) | Queue nhận An, Bình, Cường theo thứ tự; `front` là An, `back` là Cường | `An Binh Cuong` (An ở đầu hàng, Cuong ở cuối) |
| (9) | Mỗi vòng phục vụ người ở `front` rồi `pop` bỏ họ | hàng ngắn dần |

**Kết quả khi chạy:**

```text
([]) -> dung
([)] -> sai
(( -> sai
dau hang: An, cuoi hang: Cuong
phuc vu An
phuc vu Binh
phuc vu Cuong
```

!!! warning "Hay nhầm: `pop()` không trả giá trị"
    `pop()` của cả `stack` lẫn `queue` trả `void`: muốn lấy giá trị thì phải gọi `top()` (hoặc `front()`) **trước**, rồi mới `pop()`, như dòng (4)–(5). Và gọi `top()`, `front()`, `pop()` khi rỗng là hành vi không xác định, nên kiểm `empty()` trước (dòng (3)).

Tự cài cũng dễ: stack tự cài bằng danh sách liên kết: `themDau`/`xoaDau` của mục 4 chính là `push`/`pop`, đều O(1). Queue cần thêm ở một đầu và lấy ở đầu kia, nên danh sách đơn phải có thêm **con trỏ đuôi**, như ở mục 💻.

!!! info "Bạn biết Go?"
    Go **không có** stack/queue chuẩn: người ta dùng slice. Stack: `s = append(s, x)` để push, `x := s[len(s)-1]; s = s[:len(s)-1]` để pop. Queue: `q = append(q, x)` và `q = q[1:]` để lấy đầu, đơn giản nhưng phần đã bỏ vẫn nằm trong mảng nền cho đến lần `append` cấp mảng mới. Channel có đệm cũng là hàng đợi FIFO, nhưng để chuyển dữ liệu giữa các goroutine.

!!! info "Một mảnh của Bài 22: `priority_queue`"
    `std::priority_queue` (`<queue>`) lấy phần tử **lớn nhất trước** thay vì vào trước ra trước, cài bằng heap ([Bài 22](22-bst-bang-bam-heap.md)). Bên Go là `container/heap`: bạn tự viết năm hàm của `heap.Interface` (`Len`, `Less`, `Swap`, `Push`, `Pop`) và nó lấy phần tử mà `Less` xếp đầu (với `Less` là `<` thì là nhỏ nhất).

## 💻 Ví dụ code

Ghép mục 4 và 5: **queue tự cài bằng danh sách liên kết đơn có con trỏ đuôi**. Đây cũng là câu hỏi nối tiếp thường gặp sau "đảo ngược danh sách": thêm cuối O(1) thì cần nhớ đuôi.

```cpp
#include <iostream>

struct Nut {
    int gt;
    Nut* tiep;
};

struct HangDoi {
    Nut* dau = nullptr;              // người đứng đầu hàng (lấy ra từ đây)
    Nut* duoi = nullptr;             // người đứng cuối hàng (thêm vào từ đây)

    HangDoi() = default;
    HangDoi(const HangDoi&) = delete;
    HangDoi& operator=(const HangDoi&) = delete;
    ~HangDoi() {
        while (dau != nullptr) pop();
    }

    bool rong() const { return dau == nullptr; }

    void push(int x) {               // O(1) nhờ con trỏ duoi
        Nut* moi = new Nut{x, nullptr};                // (1)
        if (duoi == nullptr) {
            dau = moi;                                 // (2) hàng đang rỗng: nút này là cả đầu lẫn đuôi
        } else {
            duoi->tiep = moi;                          // (3) nối sau nút cuối cũ
        }
        duoi = moi;                                    // (4)
    }

    int front() const { return dau->gt; }              // chỉ gọi khi !rong()

    void pop() {                     // O(1)
        Nut* cu = dau;
        dau = dau->tiep;                               // (5)
        if (dau == nullptr) duoi = nullptr;            // (6) vừa lấy người cuối cùng
        delete cu;
    }
};

int main() {
    HangDoi h;
    for (int x = 10; x <= 30; x += 10) h.push(x);
    std::cout << "dau hang " << h.front() << "\n";
    h.pop();
    h.push(40);
    while (!h.rong()) {
        std::cout << h.front() << " ";
        h.pop();
    }
    std::cout << "\n";
    h.push(50);                      // dùng lại sau khi đã rỗng
    std::cout << "sau khi rong, push 50: " << h.front() << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Xin nút mới, `tiep` là `nullptr` vì nó sẽ là nút cuối |
| (2) | Hàng rỗng (`duoi` là `nullptr`): nút mới là cả đầu lẫn đuôi |
| (3)–(4) | Hàng có người: nút cuối cũ trỏ tới nút mới, rồi `duoi` dời tới nút mới, không phải đi dọc hàng nên O(1) |
| (5) | Lấy người đầu hàng: `dau` nhảy sang nút kế, rồi `delete` nút cũ |
| (6) | Nếu vừa lấy người cuối cùng thì `dau` thành `nullptr`; phải đặt `duoi` về `nullptr` theo, nếu không nó trỏ vào nút đã `delete` (con trỏ treo, [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md)) |

**Kết quả khi chạy:**

```text
dau hang 10
20 30 40 
sau khi rong, push 50: 50
```

Mình đã chạy ba chương trình ở mục 4, mục 5 và mục này với `-fsanitize=address,undefined`: không có báo cáo nào.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Big-O là gì? Vì sao bỏ hằng số, và amortized nghĩa là gì?"
    Big-O mô tả số bước tăng thế nào theo kích thước dữ liệu `n`, thường nói cho trường hợp xấu nhất. Hằng số và số hạng nhỏ bị bỏ vì với `n` lớn chỉ số hạng tăng nhanh nhất quyết định, nên `3n + 5` và `n²/2` là O(n) và O(n²). Amortized O(1) (như `push_back` của `vector`) nghĩa là một vài lần đắt nhưng hiếm, nên mọi chuỗi `n` thao tác tốn tổng cỡ `n`; khác với "trung bình" của bảng băm là phụ thuộc phân bố khóa.

??? question "Đảo ngược danh sách liên kết đơn. Độ phức tạp?"
    Dùng ba con trỏ `truoc` (ban đầu `nullptr`), `hien` (ban đầu `dau`), và `ke`. Mỗi vòng: nhớ `ke = hien->tiep`, quay mũi tên `hien->tiep = truoc`, rồi dời `truoc = hien`, `hien = ke`; cuối cùng `dau = truoc`. Thời gian O(n), bộ nhớ thêm O(1). Lỗi hay gặp là quên lưu `ke` trước khi quay mũi tên, nên mất phần còn lại của danh sách.

??? question "Khi nào chọn `std::list` thay vì `std::vector`? Và `stack` với `queue` khác gì?"
    Hiếm: khi cần chèn/xóa nhiều ở giữa **và đã có iterator** vị trí, hoặc cần tham chiếu tới phần tử không hỏng khi chèn. Phần lớn trường hợp `vector` nhanh hơn nhờ bộ nhớ liền, dù `list` chèn giữa là O(1). `stack` là LIFO (lấy cái mới nhất, hợp với hoàn tác, khớp ngoặc, đệ quy), `queue` là FIFO (lấy cái cũ nhất, hợp với hàng chờ, xử lý theo thứ tự đến); cả hai là container adaptor, thao tác O(1), `pop()` trả `void`.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Quên lưu nút kế khi đảo ngược hoặc xóa"
    `hien->tiep = truoc; hien = hien->tiep;` làm `hien` thành `truoc`, không phải nút kế, và cả phần còn lại của danh sách bị bỏ rơi (rò rỉ). Tương tự khi xóa: lấy `dau->tiep` **trước** khi `delete` nút. Quy tắc: cắt dây nào thì nhớ đầu bên kia trước.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="21" markdown>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 1.** Đọc đoạn code sau. Big-O theo `n` của nó là gì?

```text
for (int i = 0; i < n; ++i)
    for (int j = 0; j < 5; ++j)
        tong += i * j;
```

- O(n²), vì có hai vòng `for` lồng nhau
- O(5), vì vòng trong chỉ chạy năm lần mà thôi
- O(log n), vì `j` chỉ đi một đoạn rất ngắn
- O(n), vì vòng trong luôn chạy đúng 5 lần

<p class="giai-thich" markdown>Vòng ngoài chạy `n` lần và mỗi lần vòng trong chỉ chạy 5 lần, tổng `5n` bước, và hằng số 5 bị bỏ nên là O(n). Hai vòng lồng chỉ cho O(n²) khi cả hai cùng chạy tới `n`. O(5) bỏ quên vòng ngoài chạy `n` lần, còn log n là kiểu chia đôi dữ liệu và không có gì như thế ở đây.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn code sau, dùng khi đảo ngược danh sách `1 → 2 → 3` mà `hien` đang trỏ nút 1 và `truoc` là `nullptr`. Chuyện gì xảy ra?

```text
hien->tiep = truoc;
hien = hien->tiep;
```

- `hien` thành `nullptr`, nút 2 và 3 bị bỏ rơi
- `hien` sang nút 2 như dự định, nên cả danh sách được đảo đúng
- `hien` thành nút 1, nên vòng lặp chạy mãi không dừng
- `hien` nhảy tới nút 3 vì đi theo hai mũi tên

<p class="giai-thich" markdown>Dòng đầu quay mũi tên của nút 1 thành `nullptr`, rồi dòng hai đọc `hien->tiep` **sau khi nó đã bị ghi đè**, nên `hien` thành `nullptr` và vòng dừng. Nút 2 và nút 3 mất đường duy nhất tới chúng, tức rò rỉ. `hien` đã là `nullptr`, không quay lại nút 1 nên không có vòng lặp vô hạn. Cách sửa là lưu nút kế vào biến `ke` **trước** khi quay mũi tên.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Danh sách liên kết đơn chỉ lưu con trỏ `dau`. Cặp thao tác nào sau đây đều O(1)?

- Thêm ở cuối và tìm theo giá trị
- Lấy phần tử thứ `k` và thêm ở cuối
- Thêm ở đầu và xóa ở đầu danh sách
- Tìm theo giá trị và xóa ở đầu

<p class="giai-thich" markdown>Thêm và xóa ở đầu chỉ đụng nút đầu và `dau`, không đi dọc danh sách. Thêm ở cuối phải đi tới nút cuối vì không có con trỏ đuôi, nên O(n), và tìm theo giá trị hay lấy phần tử thứ `k` cũng phải lần từng nút. Cặp cuối chỉ đúng một nửa, vì xóa ở đầu thì O(1) nhưng tìm thì không.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đọc đoạn code sau. Nó in ra gì?

```text
std::stack<int> s;
s.push(1); s.push(2); s.push(3);
s.pop();
std::cout << s.top();
```

- `1`, vì `pop` bỏ phần tử được cất vào đầu tiên
- `2`, vì `pop` bỏ phần tử được cất vào sau cùng
- `3`, vì `pop` chỉ trả giá trị chứ không bỏ gì
- `0`, vì `pop` làm rỗng rồi `top` trả giá trị mặc định

<p class="giai-thich" markdown>Stack là LIFO: phần tử vào sau cùng (3) nằm ở đỉnh và bị `pop` bỏ đi, nên đỉnh mới là 2. Phần tử đầu tiên cất vào (1) nằm dưới đáy, không bị đụng tới. `pop` thật sự **bỏ** phần tử và không trả gì (`void`), nên `3` sai; còn `top` không có "giá trị mặc định" nào, stack vẫn giữ 1 và 2.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** "`push_back` của `vector` là O(1) amortized" có nghĩa là gì?

- Mỗi lần `push_back` đều đúng một bước, kể cả lần tái cấp phát
- Với dữ liệu ngẫu nhiên thì nhanh, còn dãy xấu thì chậm hẳn
- Chỉ O(1) khi đã gọi `reserve` trước, còn không là O(n)
- Hiếm khi mới đắt, chia đều cả chuỗi thì mỗi lần cỡ hằng số

<p class="giai-thich" markdown>Lần tái cấp phát chuyển cả mảng nên đắt, nhưng nó hiếm dần vì capacity tăng theo tỉ lệ: tổng chi phí cả chuỗi chia ra mỗi lần là hằng số, **bất kể** dữ liệu. Vậy nên đáp án nói mỗi lần đúng một bước là sai, vì lần tái cấp phát tốn nhiều hơn. Bảo đảm này không dựa vào dữ liệu may rủi (đó là "trung bình" của bảng băm), và cũng không cần `reserve` mới đúng; `reserve` chỉ giúp tránh những lần đắt đó.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Đọc đoạn code sau. Nó in ra gì?

```text
std::queue<char> q;
q.push('a'); q.push('b'); q.push('c');
q.pop();
std::cout << q.front() << q.back();
```

- `bc`, vì `pop` bỏ `a` đang nằm ở đầu hàng
- `ac`, vì `pop` bỏ `b` nằm ở giữa hàng
- `ca`, vì queue lấy ngược từ cuối về đầu
- `cb`, vì `pop` bỏ `a` rồi hàng bị đảo ngược

<p class="giai-thich" markdown>Queue là FIFO, nên `pop` bỏ phần tử vào **đầu tiên** (`a`); hàng còn `b`, `c`, với `front` là `b` và `back` là `c`. `pop` không bao giờ bỏ phần tử ở giữa. Việc lấy ngược từ cuối là hành vi của stack chứ không phải queue, và `pop` không đảo thứ tự các phần tử còn lại.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Big-O là cách số bước **tăng theo `n`**: đếm bước, giữ số hạng lớn nhất, bỏ hằng số (`3n + 5` là O(n), `n(n-1)/2` là O(n²)); O(1) là "không đổi" chứ không phải "nhanh", và với `n` nhỏ hằng số vẫn đáng kể.
2. Nói rõ tốt nhất/trung bình/xấu nhất (phỏng vấn mặc định là xấu nhất): `unordered_map` O(1) trung bình, O(n) xấu nhất; **amortized** là bảo đảm trên cả chuỗi thao tác không nhờ dữ liệu (`push_back` của `vector`: đo thật được 1023 phần tử chuyển cho 1000 lần thêm).
3. Bảng container: `vector` `[i]` O(1) và thêm cuối O(1) amortized, `deque` thêm hai đầu O(1), `list` chèn giữa O(1) khi đã có vị trí nhưng tìm O(n), `map`/`set` O(log n), `unordered_*` O(1) trung bình; mặc định chọn `vector` vì bộ nhớ liền.
4. Danh sách liên kết đơn: nút gồm giá trị và `Nut* tiep` (con trỏ tới chính kiểu của nó là được, nhét nguyên nút thì lỗi), thêm/xóa đầu O(1), tìm O(n), hàm hủy phải trả mọi nút (RAII) và cấm sao chép bằng `= delete`; đảo ngược bằng ba con trỏ (`truoc`, `hien`, `ke`, nhớ `ke` trước khi quay mũi tên) là O(n) thời gian, O(1) bộ nhớ thêm.
5. `stack` là LIFO (`push`, `top`, `pop`) và `queue` là FIFO (`push`, `front`, `pop`), cả hai là container adaptor O(1) mà `pop()` trả `void` và rỗng thì cấm `top`/`front`; Go không có hai kiểu này (dùng slice), và bảng băm tự cài, cây nhị phân tìm kiếm, heap/`priority_queue` (Go: `container/heap`) học ở [Bài 22](22-bst-bang-bam-heap.md).
