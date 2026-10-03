# Bài 22 — Cây nhị phân tìm kiếm, bảng băm và heap

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Hiểu **đệ quy** (hàm gọi lại chính nó) và dùng nó để tự cài **cây nhị phân tìm kiếm (BST)**: chèn, tìm, duyệt trung tự ra dãy tăng dần, đo độ cao, hủy cây không rò rỉ; nói được vì sao xấu nhất là O(n) và "cây cân bằng" của `map` giải quyết điều đó thế nào.
    - Phác được **bảng băm kiểu chaining** (mỗi hộp là một danh sách): hàm băm, `% số hộp`, đụng độ, hệ số tải, rehash, và vì sao tìm là O(1) trung bình.
    - Hiểu **heap** lưu trong mảng (con của `i` là `2i+1`, `2i+2`), vì sao `top` O(1) còn `push`/`pop` O(log n), dùng `std::priority_queue` (max-heap, min-heap bằng `greater`) và giải **top-K**.

**Bạn cần biết trước:** [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) (khung hàm, đệ quy vô hạn làm tràn stack), [Bài 03](../nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md) (`->`, `nullptr`), [Bài 06](../nhom-1-nen-tang-bo-nho/06-tham-chieu-const.md) (hàm `const`), [Bài 07](../nhom-1-nen-tang-bo-nho/07-new-delete.md) (`new`/`delete`, ASan báo rò rỉ), [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (hàm hủy), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) (`= delete`), [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (`std::move`), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (`%`), [Bài 16](16-vector.md), [Bài 17](17-string-array-deque-list.md) và [Bài 18](18-map-set-unordered.md) (container), [Bài 20](20-algorithm-lambda.md) (`std::max`) và [Bài 21](21-big-o-cau-truc-du-lieu.md) (Big-O, `Nut`, `std::queue`).

!!! note "Phạm vi bài này"
    Ba cấu trúc này được tách từ Bài 21 cho đỡ dài. BST và bảng băm ở đây **chỉ để hiểu cách `map` và `unordered_map` hoạt động**: đi làm bạn dùng bản có sẵn của thư viện, còn đi phỏng vấn người ta có thể bắt bạn viết BST và nói về bảng băm. Xóa một nút khỏi BST và cây cân bằng đầy đủ nằm ngoài bài.

## 🧠 Câu chuyện mở đầu

Ba hình ảnh cho ba cấu trúc. **BST** là trò đoán số từ 1 đến 100: mỗi câu "lớn hơn hay nhỏ hơn 50?" loại bỏ một nửa. **Bảng băm** là phòng thư nhiều hộp của [Bài 18](18-map-set-unordered.md): người gác tính từ tên ra số hộp rồi chỉ lục trong hộp đó. **Heap** là phòng cấp cứu: ai nặng nhất được khám trước, và lúc nào cũng biết ngay ai đang nặng nhất.

!!! info "Chỗ nào các hình ảnh này không còn đúng?"
    Trò đoán số chỉ nhanh nếu mỗi câu hỏi chia đôi được khoảng còn lại. Nếu bạn hỏi "có phải 1 không? có phải 2 không?..." thì mỗi câu chỉ loại một số và có thể phải hỏi tới 100 lần. BST xấu đi đúng như vậy (mục 2). Phòng cấp cứu thì khác heap ở chỗ: heap chỉ biết rõ **người đứng đầu**, không biết thứ tự những người còn lại; nó không phải một dãy đã xếp.

!!! warning "Hay nhầm: hai nghĩa của chữ heap"
    "Heap" ở [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) là **vùng nhớ** để `new` xin chỗ. "Heap" trong bài này là một **cách sắp phần tử** trong mảng. Hai thứ chỉ trùng tên. Một `std::priority_queue` khai báo trong `main` là biến cục bộ nằm trên stack, dù dữ liệu trong `vector` bên trong nó nằm ở vùng heap.

## 📖 Giải thích

### 1. Đệ quy, vừa đủ để đọc cây

**Đệ quy** là hàm gọi lại **chính nó** với một bài toán nhỏ hơn. [Bài 02](../nhom-1-nen-tang-bo-nho/02-stack-heap-static.md) đã cho thấy mặt xấu của nó (tự gọi mãi thì tràn stack); mặt tốt là cái cây vốn dĩ "cây con của cây con", nên hàm đệ quy trông giống hệt hình cây. Một hàm đệ quy đúng luôn có hai phần: **điểm dừng** (trường hợp nhỏ nhất, trả luôn không gọi tiếp) và **bước đệ quy** (gọi lại chính nó với đầu vào nhỏ hơn, tiến dần tới điểm dừng).

```cpp
#include <iostream>

int tongDen(int n) {
    if (n == 0) return 0;              // (1) điểm dừng: hết đường lùi
    return n + tongDen(n - 1);         // (2) gọi lại chính nó với bài nhỏ hơn
}

int main() {
    std::cout << "tongDen(3) = " << tongDen(3) << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2), `n`=3 | Chưa tính được `3 + ?`, phải biết `tongDen(2)` trước nên gọi nó | stack: khung `main`, khung `tongDen(3)` |
| (2), `n`=2 và `n`=1 | Mỗi lần lại chồng thêm một khung chờ kết quả của khung trên | thêm khung `tongDen(2)`, `tongDen(1)` |
| (1), `n`=0 | Chạm điểm dừng: trả `0`, không gọi tiếp | đỉnh stack: khung `tongDen(0)` |
| (2) lúc quay về | Gỡ khung từ đỉnh xuống: `1 + 0 = 1`, rồi `2 + 1 = 3`, rồi `3 + 3 = 6` | các khung gỡ dần |

**Kết quả khi chạy:**

```text
tongDen(3) = 6
```

Số khung chồng lên nhau là **độ sâu** đệ quy (ở đây 4, kể cả `n`=0); quá sâu thì tràn stack. Với cây, độ sâu cỡ độ cao của cây (cộng thêm một lần gọi tới `nullptr`).

### 2. Cây nhị phân tìm kiếm (BST)

**Cây** là các **nút** nối nhau, mỗi nút có đúng một nút **cha** (trừ **gốc** ở trên cùng). **Cây nhị phân** là cây mà mỗi nút có tối đa hai nút **con**: con trái và con phải; nút không có con gọi là **lá**. **BST** (binary search tree) thêm một luật cho **mọi** nút: cả cây con bên trái chứa toàn giá trị **nhỏ hơn** nút, cả cây con bên phải toàn giá trị **lớn hơn**.

Nút vẫn là `struct Nut` như Bài 21, chỉ khác là có hai mũi tên thay vì một. Luật trên cho ta cách tìm như trò đoán số: so `x` với nút, nhỏ hơn thì rẽ trái, lớn hơn thì rẽ phải, bằng thì xong. Chèn cũng đi đường đó cho tới khi gặp chỗ trống (`nullptr`) và đặt nút mới vào chỗ ấy.

Ba điều cần biết trước khi đọc listing:

- `std::max(a, b)` (`<algorithm>`, [Bài 20](20-algorithm-lambda.md)) trả số lớn hơn trong hai số.
- `std::vector<int>{4, 2, 6}` dựng tạm một vector chỉ để duyệt.
- `chenNut` **trả về con trỏ** tới gốc của cây con sau khi chèn, và ta gán lại `n->trai = chenNut(n->trai, x)`. Cây con rỗng thì lời gọi trả nút mới nên gán nút mới vào; cây con có nút thì lời gọi trả lại chính nút cũ nên gán lại cũng không đổi gì. Bảng "Chạy từng dòng" có một hàng cho bước quay về này.

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

struct Nut {
    int gt;
    Nut* trai;                         // (1) nút con bên trái: toàn giá trị nhỏ hơn gt
    Nut* phai;                         // (2) nút con bên phải: toàn giá trị lớn hơn gt
};

Nut* chenNut(Nut* n, int x) {          // trả về gốc (mới) của cây con n
    if (n == nullptr) return new Nut{x, nullptr, nullptr};   // (3) chỗ trống: đặt nút mới
    if (x < n->gt) n->trai = chenNut(n->trai, x);            // (4)
    else if (x > n->gt) n->phai = chenNut(n->phai, x);       // (5)
    return n;                          // (6) x == gt: đã có, không làm gì
}

void trungTu(const Nut* n) {           // trái, rồi chính nó, rồi phải
    if (n == nullptr) return;
    trungTu(n->trai);                                        // (7)
    std::cout << n->gt << " ";                               // (8)
    trungTu(n->phai);
}

int doCao(const Nut* n) {              // số nút trên đường dài nhất từ n xuống lá
    if (n == nullptr) return 0;
    return 1 + std::max(doCao(n->trai), doCao(n->phai));
}

void giai(Nut* n) {                    // trả cả cây: con trước, rồi mới tới nút
    if (n == nullptr) return;
    giai(n->trai);
    giai(n->phai);
    delete n;                                                // (9)
}

struct Cay {
    Nut* goc = nullptr;                // nullptr = cây rỗng

    Cay() = default;                   // ba dòng này giống DanhSach (Bài 21)
    Cay(const Cay&) = delete;
    Cay& operator=(const Cay&) = delete;
    ~Cay() { giai(goc); }

    void chen(int x) { goc = chenNut(goc, x); }

    int tim(int x) const {             // trả số nút đã ghé; âm nếu không có
        int ghe = 0;
        const Nut* p = goc;
        while (p != nullptr) {
            ++ghe;
            if (x == p->gt) return ghe;
            p = (x < p->gt) ? p->trai : p->phai;             // (10)
        }
        return -ghe;
    }
};

int main() {
    Cay a;                             // chèn theo thứ tự "giữa trước"
    for (int x : std::vector<int>{4, 2, 6, 1, 3, 5, 7}) a.chen(x);
    Cay b;                             // chèn theo thứ tự tăng dần
    for (int x = 1; x <= 7; ++x) b.chen(x);

    std::cout << "a trung tu: "; trungTu(a.goc); std::cout << "\n";
    std::cout << "b trung tu: "; trungTu(b.goc); std::cout << "\n";
    std::cout << "do cao a = " << doCao(a.goc) << ", do cao b = " << doCao(b.goc) << "\n";
    std::cout << "tim 7 trong a: ghe " << a.tim(7) << " nut, trong b: ghe " << b.tim(7) << " nut\n";
    std::cout << "tim 9 trong a: " << a.tim(9) << "\n";
    return 0;
}
```

**Chạy từng dòng** (cây `a`; chèn `4, 2, 6`)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) chèn 4 | Cây rỗng nên tạo nút `4` làm gốc | `goc` → [4] |
| (4) chèn 2 | `2 < 4` nên đi trái; con trái của 4 là `nullptr`: (3) tạo nút `2` ở đó | [4] có trái → [2] |
| (4) lúc quay về | `chenNut(n->trai, 2)` trả con trỏ nút `2`, được gán vào `n->trai` của `4`; rồi `return n` trả lại chính `4` cho `goc` | `goc` vẫn → [4] |
| (5) chèn 6 | `6 > 4` nên đi phải: tạo nút `6` | [4] có trái [2], phải [6] |
| (7)-(8) | Trung tự: đi hết cây con trái, **rồi** in nút, **rồi** đi cây con phải | in `1 2 3 4 5 6 7` |
| (9) | Hủy: đi xuống tận lá, `delete` lá trước, rồi lên `delete` cha; xóa cha trước thì mất đường tới con | |
| (10) | `tim` rẽ theo luật: `7 > 4` rẽ phải, `7 > 6` rẽ phải, gặp `7`: ghé 3 nút | |

**Kết quả khi chạy:**

```text
a trung tu: 1 2 3 4 5 6 7 
b trung tu: 1 2 3 4 5 6 7 
do cao a = 3, do cao b = 7
tim 7 trong a: ghe 3 nut, trong b: ghe 7 nut
tim 9 trong a: -3
```

Cây `a` có hình `4` ở gốc, `2` và `6` ở tầng hai, `1 3 5 7` là lá. Cây `b` chèn `1` rồi `2`, `3`... mỗi số lớn hơn mọi số trước nên **luôn rẽ phải**: nó thành một dây dài 7 nút chỉ có con phải, y như danh sách liên kết. `tim 9` ghé 3 nút rồi hết đường nên in `-3`.

**Duyệt trung tự** (in-order) là "trái, giữa, phải". Vì luật BST, mọi giá trị bên trái nhỏ hơn nút và bên phải lớn hơn, nên in theo thứ tự này **luôn ra dãy tăng dần**, dù cây hình gì (cả hai cây trên cùng in ra `1 2 3 4 5 6 7`). Đó cũng là cách `map` ([Bài 18](18-map-set-unordered.md)) duyệt ra khóa đã xếp.

**Độ cao** là số nút trên đường dài nhất từ gốc xuống lá (cây rỗng cao 0): `1 + max(cao trái, cao phải)`. Chi phí `chen` và `tim` đều **bằng độ cao**, vì mỗi bước đi xuống một tầng.

Cây `a` cao 3 với 7 nút, và nói chung cây đầy đủ `n` nút chỉ cao cỡ log n: số nút gấp đôi thì cao thêm một tầng. Còn cây `b` cao 7 với 7 nút nên `tim` mất O(n).

**Vì sao xấu nhất là O(n)?** Hình cây chỉ phụ thuộc **thứ tự chèn**. Dữ liệu đã sắp xếp (tăng hoặc giảm dần, như mã số tăng dần) làm cây thành dây, và dữ liệu như vậy rất hay gặp trong đời thật. Với dữ liệu ngẫu nhiên cây thường thấp cỡ log n, nhưng BST "trần" (không tự cân bằng) có **xấu nhất O(n)**.

**Cây cân bằng** sửa điều đó bằng cách tự sắp xếp lại. Sau mỗi lần chèn hay xóa, nếu một nhánh quá dài so với nhánh kia thì nó **xoay** vài nút cho cây thấp xuống, mà vẫn giữ luật "trái nhỏ hơn, phải lớn hơn". Nhờ vậy độ cao luôn cỡ log n bất kể thứ tự chèn.

`std::map`/`std::set` ([Bài 18](18-map-set-unordered.md)) thường được cài bằng cây cân bằng (chuẩn chỉ đòi O(log n)); bản g++ dùng loại tên "cây đỏ-đen", bài này không cài.

**Thử thay đổi: đổi hàm hủy thành `~Cay() {}` (bỏ lời gọi `giai`).** Mình đã biên dịch với `-fsanitize=address` và chạy: chương trình vẫn in kết quả như cũ rồi LeakSanitizer báo `336 byte(s) leaked in 14 allocation(s)`. Đúng là hai cây, mỗi cây 7 nút, mỗi nút 24 byte (một `int` cộng đệm và hai con trỏ). Với `giai` thì ASan và UBSan đều sạch.

!!! info "Bạn biết Go?"
    Thư viện chuẩn của Go **không có** BST hay map có thứ tự: `map` của Go là bảng băm (mục 3), và khi duyệt `for range` thứ tự cố ý bị xáo ngẫu nhiên. Muốn có thứ tự thì bạn lấy khóa ra slice rồi `sort`, hoặc dùng thư viện ngoài. Chèn/tìm BST viết bằng Go gần như y nguyên: `type Nut struct { Gt int; Trai, Phai *Nut }`; khác biệt là Go không cần hàm hủy vì bộ gom rác dọn các nút không còn ai trỏ tới.

### 3. Bảng băm kiểu chaining

Mục tiêu: nhận khóa (ví dụ một cái tên) và đi **thẳng** tới chỗ cất nó, không so từng cái một. Cách làm có ba bước. Bước 1: **hàm băm** (hash function) biến khóa thành một con số lớn. Bước 2: phép `% số hộp` (chia lấy dư, [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)) đưa con số đó vào đoạn `0 .. số hộp - 1`, chính là **chỉ số hộp**. Bước 3: cất khóa vào hộp ấy.

Hai khóa khác nhau có thể rơi cùng một hộp: gọi là **đụng độ** (collision), và không tránh hết được (13 người vào 12 hộp thì chắc chắn có hộp chứa hai người). **Chaining** (nối chuỗi) xử lý bằng cách cho mỗi hộp là **một danh sách** các khóa rơi vào nó. Tìm khóa nghĩa là tính hộp, rồi chỉ lục **trong hộp ấy**.

Hộp mà dài thì chậm, nên ta theo dõi **hệ số tải** (load factor) = số khóa / số hộp: trung bình mỗi hộp chứa bao nhiêu khóa. Khi hệ số tải vượt ngưỡng, bảng **rehash**: xin gấp đôi số hộp, rồi tính lại hộp cho **từng** khóa (vì `% số hộp` đã đổi).

Mình dùng `std::vector<std::list<std::string>>`: một vector các hộp, mỗi hộp là một `std::list` ([Bài 17](17-string-array-deque-list.md)) chứa chuỗi. Vì cả vector lẫn list tự dọn khi chết (RAII, [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md)), bảng này không cần hàm hủy.

Ba cú pháp mới trong listing:

- `BangBam() : hop(4) {}` có **danh sách khởi tạo**: sau dấu `:` ta dựng thành viên `hop` bằng `hop(4)` (vector có 4 danh sách rỗng) ngay lúc đối tượng ra đời, trước khi vào thân `{}`.
- `static_cast<unsigned char>(c)` đổi mỗi ký tự thành số từ 0 đến 255, để hàm băm không phụ thuộc `char` có dấu hay không trên máy.
- `hop = std::move(moi)` ([Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md)) chuyển cả vector `moi` vào `hop` mà không chép từng danh sách.

```cpp
#include <iostream>
#include <list>
#include <string>
#include <utility>
#include <vector>

std::size_t bam(const std::string& s) {        // (1) hàm băm: chuỗi -> một con số
    std::size_t h = 0;
    for (char c : s) h = h * 31 + static_cast<unsigned char>(c);
    return h;
}

struct BangBam {
    std::vector<std::list<std::string>> hop;   // (2) mỗi hộp là một danh sách các khóa
    std::size_t soKhoa = 0;

    BangBam() : hop(4) {}                      // bắt đầu với 4 hộp rỗng

    std::size_t chon(const std::string& k) const {
        return bam(k) % hop.size();            // (3) con số -> chỉ số hộp
    }

    bool co(const std::string& k) const {
        for (const std::string& x : hop[chon(k)])      // (4) chỉ lục trong MỘT hộp
            if (x == k) return true;
        return false;
    }

    void them(const std::string& k) {
        if (co(k)) return;
        hop[chon(k)].push_back(k);             // (5) đụng độ thì hộp có thêm một khóa
        ++soKhoa;
        if (soKhoa > hop.size()) rehash();     // (6) hệ số tải > 1 thì nới ra
    }

    void rehash() {                            // (7) xây lại với gấp đôi số hộp
        std::vector<std::list<std::string>> moi(hop.size() * 2);
        for (const auto& h : hop)
            for (const std::string& k : h)
                moi[bam(k) % moi.size()].push_back(k);
        hop = std::move(moi);
    }

    void in() const {
        std::cout << "  " << soKhoa << " khoa, " << hop.size() << " hop (he so tai "
                  << static_cast<double>(soKhoa) / hop.size() << "):";
        for (const auto& h : hop) {
            std::cout << " [";
            for (const std::string& k : h) std::cout << " " << k;
            std::cout << " ]";
        }
        std::cout << "\n";
    }
};

int main() {
    BangBam b;
    for (const std::string& ten : std::vector<std::string>{"An", "Binh", "Cuong", "Dung"}) b.them(ten);
    std::cout << "sau 4 khoa:\n";
    b.in();
    b.them("Em");
    std::cout << "sau khoa thu 5:\n";
    b.in();
    std::cout << "co Binh: " << b.co("Binh") << ", co Hoa: " << b.co("Hoa") << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `bam("An")`: `'A'` là 65, `'n'` là 110, nên `65 * 31 + 110 = 2125` | |
| (3) | `2125 % 4 = 1`: "An" vào hộp 1. "Binh" cũng ra hộp 1, "Cuong" và "Dung" cùng ra hộp 2 | đụng độ: hộp 1 = An, Binh; hộp 2 = Cuong, Dung |
| (6) | Sau 4 khóa: 4 > 4 sai nên chưa rehash. Khóa thứ 5: 5 > 4 nên rehash | hệ số tải từ 1.25 sẽ về 0.625 |
| (7) | Gấp đôi thành 8 hộp, tính lại từng khóa: `2125 % 8 = 5` nên "An" dời sang hộp 5 | các khóa tản ra |
| (4) | `co("Binh")` tính hộp, chỉ duyệt hộp đó | `co("Hoa")` duyệt một hộp rồi trả sai |

**Kết quả khi chạy:**

```text
sau 4 khoa:
  4 khoa, 4 hop (he so tai 1): [ ] [ An Binh ] [ Cuong Dung ] [ ]
sau khoa thu 5:
  5 khoa, 8 hop (he so tai 0.625): [ Em ] [ Binh ] [ Dung ] [ ] [ ] [ An ] [ Cuong ] [ ]
co Binh: 1, co Hoa: 0
```

Mỗi cặp `[ ... ]` là một hộp, đếm từ hộp 0 bên trái. `co` trả `bool`, và `cout` in `true` là `1`, `false` là `0` (không phải chỉ số hộp). Số hộp và hàm băm ở đây là do mình chọn cho dễ đọc; `unordered_map` của thư viện dùng hàm băm khác và hệ số tải tối đa mặc định cũng là 1 (hàm `load_factor()` và `max_load_factor()` cho bạn xem). Chuẩn không quy định cụ thể số hộp hay cách chia, nên đừng dựa vào con số cụ thể.

**Vì sao O(1) trung bình?** Một lần `them`/`co` làm hai việc: tính hộp (số bước cố định, không phụ thuộc số khóa) và lục trong hộp. Nhờ rehash giữ hệ số tải không quá khoảng 1, nếu hàm băm **tản đều** thì mỗi hộp chỉ có vài khóa, nên lục hộp là hằng số. Việc rehash thì tốn O(n) nhưng hiếm (mỗi lần số hộp gấp đôi), nên chia đều vẫn là O(1) amortized, đúng như `push_back` ở Bài 21.

**Xấu nhất O(n)** khi mọi khóa rơi vào cùng một hộp (hàm băm dở, hoặc kẻ xấu cố ý chọn khóa cùng hộp): bảng thành một danh sách dài và `co` lục cả `n` khóa.

**Thử thay đổi: cho hàm băm luôn trả `0`** (đổi `return h;` thành `return 0;`). Mình đã chạy: cả 4 khóa vào hộp 0 (`[ An Binh Cuong Dung ]`), sau rehash 5 khóa vẫn cùng hộp 0 và bảy hộp kia trống. Bảng vẫn **đúng** nhưng mỗi truy vấn phải lục cả danh sách: O(n).

!!! info "Bạn biết Go?"
    `map` của Go cũng là bảng băm (tra O(1) trung bình) và tự nới khi đầy, nhưng bạn không chỉnh được hệ số tải như `max_load_factor` của C++. Khóa của map Go phải so sánh `==` được, tương tự khóa của `unordered_map` cần hàm băm và `==` ([Bài 18](18-map-set-unordered.md)).

### 4. Heap và `std::priority_queue`

**Heap** (đống) ở đây là cây nhị phân **gần đầy**: mọi tầng đầy đủ trừ tầng cuối, và tầng cuối được lấp từ trái sang phải. Với **max-heap**, mỗi nút **lớn hơn hoặc bằng** hai con của nó (**min-heap** thì ngược lại, nhỏ hơn hoặc bằng). Hệ quả: phần tử lớn nhất luôn ở gốc. Luật chỉ so cha với con, anh em không có luật.

Vì cây gần đầy, ta không cần nút và con trỏ: xếp các nút **theo từng tầng** vào một mảng (`vector`). Nút ở chỉ số `i` có con trái ở `2i + 1`, con phải ở `2i + 2`, và cha ở `(i - 1) / 2` (chia nguyên). Ví dụ mảng `[90, 70, 80, 30, 60, 20, 50]` là cây:

```text
            90            chỉ số 0
         /      \
       70        80       chỉ số 1, 2
      /  \      /  \
    30   60   20   50     chỉ số 3, 4, 5, 6
```

Chỉ số 2 (`80`) có con ở `2*2+1 = 5` (`20`) và `2*2+2 = 6` (`50`). Bộ nhớ liền như `vector` nên heap cũng thân thiện với CPU.

Hai thao tác chính đều giữ luật "cha ≥ con" và chỉ đi dọc **một nhánh**, dài nhất bằng độ cao cây, cỡ **log n**:

- **`push(x)`**: đặt `x` ở **ô cuối**, rồi **lọc lên** (sift up): nếu `x` lớn hơn cha thì đổi chỗ với cha, lặp lại cho tới khi hết lớn hơn cha hoặc lên tới gốc.
- **`pop()`** (bỏ phần tử lớn nhất): đưa phần tử ở **ô cuối** lên gốc (ghi đè gốc), bỏ ô cuối, rồi **lọc xuống** (sift down): đổi chỗ với con **lớn hơn** trong hai con chừng nào còn có con lớn hơn nó.

Còn **`top()`** chỉ đọc ô 0 nên O(1). Bảng dưới theo dõi mảng khi `push` lần lượt `50, 30, 20, 70` rồi `pop` một lần. Mình đã viết một bản tự cài tối giản (một `vector<int>` cùng vòng `while` đổi chỗ với cha/con) và chạy: nó in đúng các mảng này.

| Bước | Chuyện gì xảy ra | Mảng lúc này |
|---|---|---|
| `push 50`, `30`, `20` | `50` vào trước nên là gốc; `30` và `20` đặt ở ô cuối, cha của chúng là `50` lớn hơn nên không đổi chỗ | `[50 30 20]` |
| `push 70` | `70` ở chỉ số 3, cha ở chỉ số `(3-1)/2 = 1` (30) nhỏ hơn: đổi chỗ | `[50 70 20 30]` |
| (lọc lên tiếp) | `70` giờ ở chỉ số 1, cha ở chỉ số 0 (50) cũng nhỏ hơn: đổi chỗ, tới gốc thì dừng | `[70 50 20 30]` |
| `pop` | Lấy `30` (ô cuối) ghi đè gốc rồi bỏ ô cuối: `70` biến mất | `[30 50 20]` |
| (lọc xuống) | Hai con của gốc là `50` và `20`; con lớn hơn (`50`) lớn hơn `30`: đổi chỗ, xuống chỉ số 1, hết con | `[50 30 20]` |

`push` và `pop` mỗi lần đi dọc một nhánh tối đa độ cao cây, mà cây gần đầy `n` nút cao cỡ log n nên cả hai là **O(log n)**. Hai điều cần nhớ: `pop`/`top` lúc rỗng là hành vi không xác định, và mảng heap **không** xếp theo thứ tự (`[70 50 20 30]` không phải dãy tăng hay giảm).

**`std::priority_queue`** (`#include <queue>`) là heap có sẵn, thuộc nhóm container adaptor như `stack`/`queue` ([Bài 21](21-big-o-cau-truc-du-lieu.md)): bên trong là một `vector`. Mặc định nó là **max-heap**: `top()` là phần tử **lớn nhất**. Muốn **min-heap** thì khai báo ba tham số: kiểu phần tử, container bên trong, và cách so sánh `std::greater<int>` (`#include <functional>`). `std::greater<int>` là một kiểu so sánh nhận hai số và trả `a > b`; `std::less<int>` trả `a < b` và là **mặc định**. `priority_queue` đưa lên `top` phần tử mà phép so sánh xếp ở cuối cùng: với `less` đó là số lớn nhất, với `greater` là số nhỏ nhất. Các thao tác: `push`, `top` O(1), `pop` (trả `void` như `stack`), `empty`, `size`.

```cpp
#include <functional>
#include <iostream>
#include <queue>
#include <vector>

int main() {
    std::priority_queue<int> mx;                                        // (1)
    std::priority_queue<int, std::vector<int>, std::greater<int>> mn;   // (2)
    for (int x : std::vector<int>{5, 1, 8, 3}) {
        mx.push(x);
        mn.push(x);
    }
    std::cout << "max-heap top = " << mx.top() << ", min-heap top = " << mn.top() << "\n";
    mx.pop();                                                           // (3)
    mn.pop();
    std::cout << "sau pop: max-heap top = " << mx.top() << ", min-heap top = " << mn.top()
              << ", con " << mx.size() << " phan tu\n";
    return 0;
}
```

Dòng (1) là max-heap mặc định. Dòng (2) có ba tham số: kiểu `int`, container nền `vector<int>`, và cách so sánh `greater<int>`: vì nó xếp số nhỏ ở cuối, `top()` là số **nhỏ** nhất. Dòng (3) `pop` bỏ phần tử ở `top` (`8` của max-heap, `1` của min-heap), rồi `top` mới là số kế tiếp.

**Kết quả khi chạy:**

```text
max-heap top = 8, min-heap top = 1
sau pop: max-heap top = 5, min-heap top = 3, con 3 phan tu
```

Lấy hết phần tử ra từng cái thì được dãy xếp, mỗi `pop` O(log n) nên cả dãy O(n log n): đó là **heap sort**. Thứ tự so sánh của `priority_queue` **ngược trực giác** so với `sort`: `sort` mặc định cho dãy tăng dần, còn `priority_queue` mặc định cho `top` lớn nhất, phải thêm `greater` mới ra nhỏ nhất.

!!! info "Bạn biết Go?"
    Go không có `priority_queue` dựng sẵn: gói `container/heap` bắt bạn tự định nghĩa một kiểu (thường là slice) có **năm** hàm của `heap.Interface`: `Len`, `Less`, `Swap`, `Push`, `Pop`, rồi gọi `heap.Init`, `heap.Push(h, x)`, `heap.Pop(h)`. Nó là **min-heap** theo `Less` bạn viết (`h[i] < h[j]` cho phần tử nhỏ nhất ở `h[0]`); muốn max-heap thì đổi dấu. Mình đã chạy bản Go với `{5, 1, 8}` rồi push `3`: lấy ra `1 3 5 8`. Cách làm trong ruột vẫn là sift up/down trên mảng như trên.

## 💻 Ví dụ code

**Top-K phần tử lớn nhất** là câu hỏi phỏng vấn kinh điển: có dòng số dài `n`, lấy ra `K` số lớn nhất. Cách đơn giản là sắp xếp hết rồi lấy `K` số cuối (O(n log n)). Cách dùng heap: giữ một **min-heap** có tối đa `K` phần tử, thêm số mới, nếu vượt `K` thì bỏ **số nhỏ nhất** (chính là `top`); cuối cùng heap giữ đúng `K` số lớn nhất.

Mỗi số tốn O(log K), tổng O(n log K), và chỉ tốn O(K) bộ nhớ nên làm được với dữ liệu không nạp hết vào bộ nhớ.

```cpp
#include <functional>
#include <iostream>
#include <queue>
#include <vector>

std::vector<int> topK(const std::vector<int>& dong, std::size_t k) {
    std::priority_queue<int, std::vector<int>, std::greater<int>> nho;   // (1) min-heap, giữ tối đa k số
    for (int x : dong) {
        nho.push(x);                                                     // (2)
        if (nho.size() > k) nho.pop();                                   // (3) bỏ số nhỏ nhất
    }
    std::vector<int> kq;
    while (!nho.empty()) {
        kq.push_back(nho.top());                                         // (4) nhỏ -> lớn
        nho.pop();
    }
    return kq;
}

int main() {
    std::vector<int> dong = {7, 2, 9, 4, 11, 5, 8, 1};
    std::vector<int> kq = topK(dong, 3);
    std::cout << "3 so lon nhat (nho -> lon):";
    for (int x : kq) std::cout << " " << x;
    std::cout << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | Min-heap: `top()` là số nhỏ nhất trong những số đang giữ, tức "ứng viên yếu nhất" |
| (2)-(3) | Thêm số mới; nếu đang giữ quá `k` số thì bỏ số nhỏ nhất, đảm bảo chỉ còn `k` số lớn nhất từng thấy |
| (4) | Lấy ra từ heap theo thứ tự nhỏ → lớn nên `kq` tăng dần |

**Kết quả khi chạy:**

```text
3 so lon nhat (nho -> lon): 8 9 11
```

**Thử thay đổi: đổi `std::greater<int>` thành `std::less<int>`** (max-heap, `less` là mặc định). Mình đã chạy: in `4 2 1`. Giờ `top` là số **lớn** nhất nên mỗi lần vượt `k` ta bỏ số lớn: heap giữ ba số **nhỏ** nhất và in từ lớn xuống nhỏ. Chọn nhầm chiều heap là một lỗi top-K hay gặp. Mình đã chạy mọi chương trình ở mục 1–4 và mục này với `-fsanitize=address,undefined`: không có báo cáo nào.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "BST so với hash map (`map` và `unordered_map`) khác nhau thế nào? Khi nào chọn cái nào?"
    Cây cân bằng (`std::map`) giữ khóa **có thứ tự**: O(log n) **bảo đảm**, duyệt ra khóa tăng dần, hỏi được khoảng hay "khóa nhỏ nhất lớn hơn x". Bảng băm O(1) **trung bình**, xấu nhất O(n), không thứ tự, khóa phải có hàm băm. Cần thứ tự, khoảng hoặc bảo đảm xấu nhất thì chọn cây; chỉ tra theo khóa thì chọn bảng băm.

??? question "Vì sao bảng băm O(1) trung bình? Khi nào nó thành O(n)?"
    Hàm băm cho ra chỉ số hộp trong số bước không phụ thuộc số khóa, và rehash giữ hệ số tải (số khóa / số hộp) không quá cỡ 1. Hàm băm tản đều thì mỗi hộp có vài khóa nên lục hộp là hằng số; rehash đắt nhưng hiếm nên amortized vẫn O(1). Nhiều khóa cùng hộp (hàm băm dở hoặc bị tấn công) thì hộp thành danh sách dài, tìm là O(n).

??? question "Tự cài hàm chèn của BST."
    Đệ quy trả về gốc cây con: nút rỗng thì tạo nút mới và trả về; `x < n->gt` thì `n->trai = chen(n->trai, x)`; `x > n->gt` thì `n->phai = chen(n->phai, x)`; bằng nhau thì bỏ qua; cuối cùng `return n`. Chi phí O(độ cao): O(log n) nếu cây cân bằng, O(n) nếu dữ liệu đã sắp thành dây. Nhắc luôn việc hủy cây (`delete` đệ quy, con trước nút sau) để không rò rỉ.

??? question "Heap là gì? Vì sao `top` là O(1) còn `push`/`pop` là O(log n)?"
    Heap là cây nhị phân gần đầy mà cha luôn lớn hơn hoặc bằng con (max-heap), lưu trong mảng với con của `i` ở `2i+1`, `2i+2`. Phần tử lớn nhất ở ô 0 nên `top` O(1). `push` đặt ở ô cuối rồi lọc lên, `pop` đưa ô cuối lên gốc rồi lọc xuống; mỗi lần đi tối đa một nhánh, cỡ log n. Heap không phải dãy đã sắp nên không tìm phần tử bất kỳ nhanh được.

??? question "Tìm K phần tử lớn nhất trong dãy `n` số bằng `priority_queue`."
    Min-heap `std::priority_queue<int, std::vector<int>, std::greater<int>>` giữ tối đa `K` số: mỗi số mới `push`, nếu `size() > K` thì `pop` (bỏ số nhỏ nhất). Duyệt hết thì heap giữ đúng `K` số lớn nhất. Thời gian O(n log K), bộ nhớ O(K), tốt hơn sắp xếp hết (O(n log n)) khi `K` nhỏ.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Tưởng BST lúc nào cũng O(log n)"
    BST trần chèn dữ liệu đã sắp xếp thì thành một dây nút, và `tim`, `chen` thành O(n). Các hàm đệ quy (`chenNut`, `giai`) sâu bằng độ cao, nên dây đủ dài có thể làm tràn stack (ngưỡng cụ thể tùy giới hạn stack của máy, thường vài MB). Viết con trỏ con bằng `unique_ptr` cũng đệ quy y như vậy ([Bài 21](21-big-o-cau-truc-du-lieu.md)). Muốn bảo đảm O(log n) dùng `std::map`/`std::set` (cây cân bằng). Khi phỏng vấn, nhớ nói luôn "xấu nhất O(n) nếu cây lệch".

!!! warning "Lỗi 2: Nhầm chiều của `priority_queue`, hoặc `pop()` rỗng"
    Mặc định `priority_queue<int>` cho số **lớn** nhất ở `top`; muốn nhỏ nhất phải khai báo `std::vector<int>, std::greater<int>`. `pop()` trả `void` (lấy `top()` trước), và `top()`/`pop()` lúc rỗng là hành vi không xác định, nên kiểm `empty()` trước.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="22" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Đọc đoạn sau. Chèn lần lượt `5, 3, 8, 1` vào một BST rỗng (trái nhỏ hơn, phải lớn hơn). Nút `1` nằm ở đâu?

```text
chen(5); chen(3); chen(8); chen(1);
```

- Là con phải của nút `3`, vì `1` được chèn sau `3` trong dãy chèn
- Là con trái của nút `5`, vì `1` nhỏ hơn gốc nên chỉ cần rẽ trái một lần
- Là con trái của nút `3`, vì `1 < 5` rẽ trái rồi `1 < 3` rẽ trái nữa
- Là con trái của nút `8`, vì `8` là nút được chèn ngay trước nút `1`

<p class="giai-thich" markdown>Từ gốc `5`, số `1` nhỏ hơn nên đi trái tới nút `3`; tại đó `1` vẫn nhỏ hơn nên đi trái nữa, gặp chỗ trống và đặt ở đó. Vị trí trong BST do so sánh giá trị quyết định, không do thứ tự chèn gần hay xa. Dừng ngay con trái của gốc là bỏ dở một bước vì chỗ đó đã có nút `3`, và nút `8` nằm bên phải gốc nên không liên quan tới `1`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Heap lưu trong mảng `a = [90, 70, 80, 30, 60, 20, 50]`. Con trái của phần tử ở chỉ số `2` là phần tử nào?

- `20`, vì con trái nằm ở chỉ số `2*2 + 1 = 5`
- `60`, vì ở chỉ số `2*2 = 4`, tức nhân đôi chỉ số
- `50`, vì ở chỉ số `2*2 + 2 = 6`
- `30`, vì ở chỉ số `2 + 1 = 3`, ngay kế bên

<p class="giai-thich" markdown>Con trái của chỉ số `i` luôn ở `2i + 1`, nên của chỉ số 2 là chỉ số 5, giá trị `20`. Chỉ số `2i + 2` mới là con **phải** (ở đây là `50`), còn `2i` hay `i + 1` không phải công thức nào của heap. Cách đếm "con trái là chỉ số `2i`" chỉ đúng khi mảng đánh số từ 1, còn mảng của C++ đánh số từ 0.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Đọc đoạn sau. Nó in ra gì?

```text
std::priority_queue<int, std::vector<int>, std::greater<int>> q;
q.push(4); q.push(9); q.push(2);
q.pop();
std::cout << q.top();
```

- `9`, vì `pop` bỏ số nhỏ nhất và còn lại số lớn nhất ở đỉnh
- `4`, vì `pop` bỏ `2` nhỏ nhất, nên số nhỏ nhất kế là `4`
- `2`, vì `greater` làm `pop` bỏ số lớn nhất là `9`
- `2`, vì `pop` bỏ số được cất vào trước nhất là `4`

<p class="giai-thich" markdown>Với `greater`, đỉnh là số nhỏ nhất nên `pop` bỏ `2`, rồi đỉnh mới là `4`. Số `9` chỉ là đỉnh nếu đây là max-heap mặc định. `greater` đặt số nhỏ nhất ở đỉnh nên thứ bị bỏ là `2` chứ không phải `9`, và `priority_queue` bỏ theo độ ưu tiên chứ không theo thứ tự cất vào như `queue`, nên `4` không bị bỏ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Vì sao một BST "trần" (không tự cân bằng) có thể tốn O(n) cho một lần tìm?

- Vì mỗi lần rẽ nó phải so sánh với mọi nút khác trước đó
- Vì hàm tìm đệ quy luôn phải duyệt trung tự cả cây trước
- Vì con trỏ trái và phải làm mỗi bước đi chậm cỡ O(n)
- Vì dữ liệu đã sắp xếp làm cây thành một dây nút cao bằng `n`

<p class="giai-thich" markdown>Chi phí tìm bằng độ cao của cây, và chèn theo thứ tự tăng hoặc giảm dần làm mỗi nút mới luôn rẽ cùng một phía, nên độ cao bằng số nút. Mỗi bước chỉ so với một nút trên đường đi chứ không với mọi nút, và `tim` rẽ theo luật chứ không duyệt trung tự cả cây. Bộ nhớ rời rạc làm mỗi bước chậm hơn một hằng số, nhưng không biến O(log n) thành O(n).</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 5.** Vì sao tìm trong bảng băm là O(1) **trung bình**?

- Hàm băm chọn thẳng một hộp, mà hộp thường chỉ vài khóa
- Các khóa trong hộp thường được giữ theo thứ tự để tra nhị phân
- Hàm băm giữ mỗi hộp đúng một khóa nên khỏi phải lục hộp
- Các khóa thường nằm liền nhau trong một mảng nên CPU đọc nhanh hơn

<p class="giai-thich" markdown>Tính hộp tốn số bước cố định, rồi chỉ lục trong hộp đó; nếu hàm băm tản đều và hệ số tải được giữ nhỏ thì mỗi hộp có vài khóa nên cả lần tìm là hằng số. Đụng độ là chuyện **có thật** (nhiều khóa vào một hộp), nên đáp án nói mỗi hộp đúng một khóa là sai; khi mọi khóa cùng hộp thì xấu nhất là O(n). Hàm băm không xếp thứ tự trong hộp, và các hộp là danh sách rời rạc chứ không phải một mảng liền các khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Đọc đoạn sau. Bảng băm bắt đầu với 4 hộp, và sau đó rehash lên 8 hộp. Khóa `k` có `bam(k) = 13`. Nó nằm ở hộp nào trước và sau khi rehash?

```text
chỉ số hộp = bam(k) % số hộp
```

- Hộp 3 rồi hộp 5, vì `13 / 4` là 3 và `13 % 8` cho 5
- Hộp 1 rồi hộp 5, vì `13 % 4` dư 1 và `13 % 8` còn dư 5
- Hộp 1 rồi vẫn hộp 1, vì hàm băm không hề đổi khi rehash
- Hộp 2 rồi hộp 6, vì rehash dời mỗi khóa lên thêm một hộp

<p class="giai-thich" markdown>`13 % 4` là 1 (13 = 3·4 + 1) và `13 % 8` là 5 (13 = 1·8 + 5). Hàm băm không đổi, nhưng chỉ số hộp thì đổi vì số hộp đổi, và đó là lý do phải tính lại cho từng khóa. Thương `13 / 4` là 3 chỉ là phép chia nguyên, không phải số dư dùng để chọn hộp, và rehash không dời đều mỗi khóa một hộp.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Cần lấy `K` số lớn nhất trong dòng `n` số bằng `std::priority_queue`, và muốn tiết kiệm bộ nhớ nhất. Cách nào đúng?

- Max-heap chứa cả `n` số, rồi `pop` `K` lần
- Max-heap giữ `K` số, quá `K` thì bỏ `top` đi
- Min-heap chứa cả `n` số, rồi bỏ `K` số đầu tiên
- Min-heap giữ `K` số, quá `K` thì bỏ `top` đi

<p class="giai-thich" markdown>Muốn giữ các số lớn nhất, ta phải bỏ số nhỏ nhất mỗi khi vượt `K`, mà `top` của min-heap chính là số nhỏ nhất, nên min-heap giữ `K` số cho O(n log K). Max-heap giữ `K` số sẽ bỏ số lớn nhất, ra `K` số nhỏ nhất. Hai cách chứa cả `n` số đều tốn O(n) bộ nhớ; riêng cách min-heap bỏ `K` số nhỏ nhất thì chỉ còn `n - K` số, sai luôn kết quả.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Đệ quy** là hàm gọi lại chính nó với bài nhỏ hơn, gồm điểm dừng và bước đệ quy; mỗi lần gọi chồng một khung stack, nên độ sâu quá lớn sẽ tràn stack.
2. **BST**: nút trái nhỏ hơn, nút phải lớn hơn; chèn/tìm đi từ gốc xuống nên tốn bằng độ cao; duyệt trung tự (trái, giữa, phải) ra dãy tăng dần; hủy cây bằng `delete` đệ quy (con trước, nút sau, ASan sạch); xấu nhất O(n) khi dữ liệu chèn đã sắp xếp làm cây thành dây, còn `map`/`set` dùng cây cân bằng tự xoay để độ cao luôn cỡ log n.
3. **Bảng băm chaining**: hàm băm cho số, `% số hộp` cho chỉ số hộp, mỗi hộp là một danh sách (`vector<list<...>>`); đụng độ là bình thường, hệ số tải = số khóa / số hộp, vượt ngưỡng thì rehash gấp đôi số hộp và tính lại từng khóa; O(1) trung bình nhờ hộp ngắn, xấu nhất O(n) khi mọi khóa cùng hộp; Go `map` cũng là bảng băm.
4. **Heap** là cây gần đầy lưu trong mảng (con của `i` là `2i+1`, `2i+2`, cha là `(i-1)/2`), max-heap có cha ≥ con; `top` O(1), `push` (lọc lên) và `pop` (lọc xuống) O(log n); heap không phải dãy đã sắp và không trùng nghĩa với "heap" vùng nhớ.
5. `std::priority_queue` là max-heap mặc định, min-heap bằng `std::vector<int>, std::greater<int>`, `pop()` trả `void`; top-K lớn nhất dùng min-heap giữ tối đa K số, O(n log K); Go dùng `container/heap` với năm hàm `Len`, `Less`, `Swap`, `Push`, `Pop` (min-heap theo `Less`).
