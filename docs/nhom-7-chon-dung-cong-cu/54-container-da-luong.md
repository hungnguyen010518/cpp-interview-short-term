# Bài 54 — Container và đa luồng: khóa ở đâu, an toàn tới đâu

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói đúng ba luật của chuẩn về container và đa luồng: nhiều luồng **chỉ đọc** thì ổn; có một luồng **ghi** thì mọi truy cập khác phải đồng bộ; hai **phần tử khác nhau** ghi từ hai luồng thì ổn, trừ `vector<bool>`. Thấy tận mắt `push_back` đồng thời làm sập chương trình, và `m[k]` "chỉ đọc" thực ra là ghi.
    - Hiểu vì sao khóa đúng vẫn chưa đủ: tham chiếu, con trỏ, iterator lấy ra **trong** khóa mà dùng **sau** khi nhả khóa là bom nổ chậm.
    - Chọn kiểu khóa theo mẫu truy cập, có đo: một mutex cho cả bảng, `shared_mutex`, **chia shard** (N bảng, N mutex) và **sao chép khi ghi**; biết mỗi kiểu **không** hợp khi nào.
    - Trả lời câu hỏi "làm cache đa luồng, đọc nhiều ghi ít" từ phương án đơn giản tới phương án tối ưu, kèm số đo và các câu hỏi nối tiếp.

**Bạn cần biết trước:** [Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) (`vector`, `push_back`, tăng dung lượng, `vector<bool>`), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`map`, `unordered_map`, `m[k]` tự chèn, `std::hash`), [Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) (iterator bị vô hiệu), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, `lock_guard`, `shared_mutex` nhận tên, trả tham chiếu ra khỏi khóa), [Bài 28](../nhom-3-da-luong/28-atomic.md) (`std::atomic<bool>`), [Bài 10](../nhom-1-nen-tang-bo-nho/10-shared-ptr-weak-ptr.md) (`shared_ptr`, `make_shared`), [Bài 52](52-smart-pointer-da-luong.md) (`atomic_load`/`atomic_store` trên `shared_ptr`, mục 2), [Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md) (lambda tham số `auto`), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (false sharing), [Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md) (`using` đặt tên kiểu).

## 🧠 Câu chuyện mở đầu

Quay lại **nhà bếp** của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md). Bài đó nói về một thớt chung; giờ bếp có thêm **tủ kho nhiều ngăn**: container. Cả bếp cùng ra vào tủ để lấy nguyên liệu, và quản lý bếp treo một nội quy ngoài cửa.

Nội quy gồm ba dòng. Một: nhiều người **cùng nhìn** vào tủ thì không sao. Hai: hễ có một người đang **sắp xếp lại tủ** (thêm ngăn, dời hộp) thì không ai khác được đụng vào, kể cả để nhìn. Ba: hai người lấy đồ ở **hai ngăn khác nhau** thì không vướng nhau, trừ một loại tủ có ngăn nén chung nhiều hộp nhỏ vào một ô.

!!! info "Chỗ nào ví von tủ kho không còn đúng?"
    Người thật nhìn thấy tủ đang bị dời và tự dừng; chương trình thì không. Nó cứ đọc, và đọc vào chỗ đang bị dời cho ra kết quả rác hoặc sập. Ngoài ra "nhìn" mà tủ tự chèn thêm ngăn (như `m[k]` ở mục 5) thì thật ra là **sắp xếp lại**, dù nhìn bề ngoài chỉ là một lần tra.

## 📖 Giải thích

### 1. Ba luật của chuẩn

Chuẩn C++ không có một câu "container thread-safe"; nó có quy tắc chung về data race của thư viện và một mục riêng về data race của container. Ghép lại, với **mọi** container thư viện chuẩn, ta có ba luật sau (đây là cách tóm tắt của mình, không chép nguyên văn).

| Luật | Nội dung | Ví dụ |
|---|---|---|
| 1 | Nhiều luồng cùng gọi các hàm **chỉ đọc** thì không có data race | `size()`, `begin()`, `find`, `at`, `v[i]` đọc |
| 2 | Hễ **một** luồng gọi hàm có thể **ghi**, mọi truy cập khác từ luồng khác phải được đồng bộ (mutex...) | `push_back`, `erase`, `insert`, `clear`, `rehash` |
| 3 | Các phần tử **khác nhau** của cùng container được ghi từ các luồng khác nhau thì ổn, **trừ `vector<bool>`** | `v[0] = 1` ở luồng A, `v[1] = 2` ở luồng B |

Chữ "ghi" ở luật 2 nghĩa là **hàm không phải `const`** làm thay đổi cấu trúc container: số phần tử, mảng bên trong, các nút của cây. Chuẩn nêu rõ một số hàm luôn được coi là đọc (`begin`, `end`, `find`, `at`, `lower_bound`...), và `operator[]` của `vector` cũng vậy. Riêng `operator[]` của `map` và `unordered_map` thì **không** (mục 5).

Luật 3 cho phép chia một mảng lớn cho nhiều luồng, mỗi luồng một khoảng. Nó **không** cho phép đổi **số** phần tử: thay đổi kích thước là ghi vào cấu trúc chung, thuộc luật 2.

### 2. Luật 1 và luật 3 chạy thật: đọc chung, ghi ô riêng

Chương trình sau dùng cả hai luật. Bốn luồng cùng đọc một `map` (luật 1), và mỗi luồng ghi một khoảng riêng của một `vector` đã có đủ 400 phần tử (luật 3). Tổng cuối được so với con số tính tay.

```cpp
#include <iostream>
#include <map>
#include <thread>
#include <vector>

int main() {
    const std::map<int, int> heSo = {{0, 1}, {1, 2}, {2, 3}, {3, 4}};   // (1) dựng xong trước khi có luồng, rồi chỉ ĐỌC
    std::vector<int> v(400, 1);                          // (2) 400 phần tử, tạo SẴN trước khi chạy luồng
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&heSo, &v, k] {
            int h = heSo.at(k);                          // (3) bốn luồng cùng ĐỌC một map: ổn
            for (int i = k * 100; i < (k + 1) * 100; ++i) {
                v[i] = i * h;                            // (4) GHI, nhưng luồng k chỉ ghi ô [100k, 100k+100)
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();            // (5) join: luồng chính thấy mọi lần ghi
    long long tong = 0;
    for (int x : v) tong += x;
    std::cout << "tong = " << tong << " (mong doi 249500)\n";    // (6) 249500 tính tay: 1*sum(0..99)+2*sum(100..199)+...
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2) | Luồng chính dựng `heSo` và `v` xong **trước** khi tạo luồng nào | `v`: 400 ô, mảng nằm yên một chỗ |
| (3) | Cả bốn luồng gọi `heSo.at(k)`, hàm `const`, chỉ đi theo các nút cây | không ai sửa cây |
| (4) | Luồng `k` ghi các ô `100k`...`100k+99`; không ô nào có hai luồng | bốn khoảng rời nhau |
| (5) | `join` bảo đảm mọi lần ghi xong và luồng chính thấy chúng | `v` đầy đủ |

**Kết quả khi chạy** (ba lần liền đều như nhau; chạy với `-fsanitize=thread`: sạch, mã thoát 0):

```text
tong = 249500 (mong doi 249500)
```

Điều kiện then chốt nằm ở (2): `v` đã có **đủ** phần tử trước khi các luồng bắt đầu, nên luồng nào cũng chỉ **ghi giá trị vào ô có sẵn**, không đổi cấu trúc. Chỗ này còn một chuyện hiệu năng: các khoảng rời nhau mà sát biên có thể chung dòng cache và chậm đi (false sharing, [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)); đúng vẫn là đúng.

### 3. Vi phạm luật 2: `push_back` đồng thời

`push_back` nghe nhẹ, nhưng nó ghi vào **ba thứ**: ô mới, bộ đếm số phần tử, và (khi đầy) cả con trỏ tới mảng bên trong ([Bài 16](../nhom-2-stl-thuat-toan/16-vector.md): xin kệ mới, chép sang, trả kệ cũ). Hai luồng cùng làm việc đó là data race theo luật 2.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>
#include <vector>

int main() {
    std::vector<int> v;                                  // (1) một vector chung, chưa reserve
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&v] {
            for (int i = 0; i < 100000; ++i) v.push_back(i);   // (2) bốn luồng cùng push_back
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "mong doi 400000, size() = " << v.size() << "\n";
    return 0;
}
```

**Chạy từng dòng** (một cách xen kẽ có thể xảy ra)

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (2) | Luồng A thấy kệ đầy, xin kệ lớn hơn, chép sang, **trả kệ cũ** | `v` trỏ kệ mới |
| (2) | Luồng B cùng lúc vẫn ghi vào kệ cũ, hoặc cùng trả kệ cũ lần nữa | ghi vào vùng đã trả, `double free` |

**Kết quả khi chạy** (g++ -std=c++17 -Wall -pthread, không tối ưu): mình chạy **10 lần liền, cả 10 lần chương trình chết** và không in dòng nào. Năm lần thoát mã 134 (bị hủy, thông báo `malloc(): corrupted top size` hoặc `double free or corruption (!prev)`), năm lần thoát mã 139 (lỗi truy cập bộ nhớ, segmentation fault). Máy bạn sẽ chết theo kiểu khác, nhưng đừng mong nó in ra một số đúng.

TSan báo ngay lần đầu (rút gọn): `Read of size 8 ... by thread T2: std::vector<int>::push_back` và `Previous write of size 8 ... by thread T1: std::vector<int>::_M_realloc_insert`, tức là một luồng đọc con trỏ bên trong trong lúc luồng kia đang ghi nó khi xin kệ mới. Sau đó heap hỏng nặng nên chính TSan cũng không chạy tiếp được trên máy mình (hết 20 giây hoặc `FATAL`). Khối mã đặt `// bo-qua-kiem-tra`.

### 4. Ngoại lệ của luật 3: `vector<bool>`

[Bài 16](../nhom-2-stl-thuat-toan/16-vector.md) nói `vector<bool>` nén mỗi phần tử thành **một bit**. Vậy hai bit khác nhau có thể nằm trong **cùng một từ nhớ** (một số 64 bit trên g++ này). Ghi một bit là: đọc cả từ, đổi một bit, ghi cả từ lại. Hai luồng ghi hai bit khác nhau của cùng từ thì lần ghi sau có thể **xóa** bit mà lần ghi trước vừa đặt. Đó là lý do chuẩn loại riêng `vector<bool>` khỏi luật 3.

Ta cho bốn luồng ghi **các bit khác nhau** (luồng `k` ghi các bit có chỉ số chia 4 dư `k`), cố tình để mọi từ nhớ đều bị chia chung:

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <thread>
#include <vector>

int main() {
    const int N = 1000000;
    std::vector<bool> v(N, false);                       // (1) mỗi phần tử là 1 bit
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&v, N, k] {
            for (int i = k; i < N; i += 4) v[i] = true;  // (2) luồng k ghi các bit i % 4 == k: KHÁC bit, CÙNG từ nhớ
        });
    }
    for (std::thread& t : cacLuong) t.join();
    int dem = 0;
    for (int i = 0; i < N; ++i) dem += v[i];
    std::cout << "mong doi " << N << " bit bat, thuc te " << dem << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | 1000000 bit nằm trong khoảng 15625 từ 64 bit | một mảng từ nhớ |
| (2) | Luồng A: đọc từ, bật bit 0, ghi từ. Luồng B cùng lúc: đọc từ cũ, bật bit 1, ghi từ; bit 0 của A bị ghi đè về 0, không ai bật lại | `dem` thiếu vài bit |

**Kết quả khi chạy** (năm lần liền, không tối ưu): `999988`, `999995`, `999994`, `999824`, `1000000`. Bốn lần thiếu bit và một lần ra đủ; **ra đủ không chứng minh chương trình đúng**. TSan báo `data race ... in std::_Bit_reference::operator=(bool)` với `Read of size 8` và `Previous write of size 8`: tám byte là cả cái từ nhớ, không phải một bit.

**Thử thay đổi: đổi `vector<bool>` thành `vector<char>`** (và `false`/`true` thành `0`/`1`). Mình đã chạy: ra `1000000` cả ba lần, TSan sạch, mã thoát 0. Mỗi `char` là một ô nhớ riêng nên luật 3 áp dụng. Cái giá là tốn 8 lần bộ nhớ.

### 5. `operator[]` của map: nhìn mà ghi

[Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) đã nói `m[k]` với khóa chưa có sẽ **chèn** khóa đó. Giờ thêm hệ quả đa luồng: chuẩn không xếp `operator[]` của `map`/`unordered_map` vào nhóm hàm đọc. Nên "tra giá" bằng `m[k]` từ nhiều luồng là ghi, dù người viết chỉ muốn đọc.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <map>
#include <string>
#include <thread>
#include <vector>

int main() {
    std::map<std::string, int> gia = {{"ca", 30}, {"com", 10}, {"tra", 5}};   // (1) dựng xong TRƯỚC khi tạo luồng
    std::vector<std::thread> cacLuong;
    for (int k = 0; k < 4; ++k) {
        cacLuong.emplace_back([&gia, k] {
            for (int i = 0; i < 20000; ++i) {
                int g = gia["mon" + std::to_string(k * 20000 + i)];   // (2) "chỉ đọc" khóa chưa có: operator[] CHÈN
                (void)g;                                              // báo trình biên dịch: cố ý không dùng g
            }
        });
    }
    for (std::thread& t : cacLuong) t.join();
    std::cout << "size() = " << gia.size() << " (mong doi " << 3 + 4 * 20000 << ")\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1) | `gia` có 3 nút, chưa luồng nào chạy | cây 3 nút |
| (2) | Mỗi luồng tra các khóa `mon...` chưa có, mỗi lần **chèn một nút** và cân bằng lại cây; các luồng cùng sửa liên kết giữa các nút | chèn bị mất hoặc cây hỏng: `size()` thiếu so với 80003 |

**Kết quả khi chạy** (tám lần liền): `size()` ra `76382`, `76376`, `76142`, `75693`, một lần chết (mã 139), rồi `76957`, `75437`, `74460`; mong đợi 80003. TSan báo `data race` trong `_Rb_tree` (nút cây vừa được luồng khác cấp phát).

**Thử thay đổi: chỉ tra khóa đã có** (cả bốn luồng chạy `gia["com"]` 20000 lần). Mình đã chạy với TSan: sạch, tổng đúng `800000`, `size()` vẫn 3. Với khóa đã có, bản g++ này không ghi gì. Nhưng chuẩn không hứa điều đó, và mã dùng `m[k]` thì một khóa vắng mặt là hỏng. Muốn đọc an toàn: `find` (hoặc `at`, `count`) trên map **không** bị ai ghi.

!!! info "Bạn biết Go?"
    `map` của Go cũng không an toàn cho truy cập đồng thời. Mình chạy một goroutine ghi `m[i%100] = i` và một goroutine đọc `m[i%100]` (Go 1.27.2): cả 5 lần đều chết với `fatal error: concurrent map read and map write`, vì runtime Go cố **phát hiện** việc này và dừng chương trình; C++ thì không báo gì, cứ chạy và hỏng. Tương ứng với `std::mutex`/`shared_mutex` là `sync.Mutex`/`sync.RWMutex`; `sync.Map` là map an toàn luồng có sẵn, nhưng tài liệu của nó nói nó chỉ tối ưu cho hai kiểu dùng (khóa ghi một lần đọc nhiều lần, hoặc các luồng đụng các khóa rời nhau), còn lại nên dùng map thường kèm khóa.

### 6. Khóa đúng vẫn chưa đủ: tham chiếu và iterator thoát khỏi khóa

[Bài 19](../nhom-2-stl-thuat-toan/19-iterator-vo-hieu.md) nói `push_back` có thể làm tham chiếu và iterator cũ hỏng. Chuyện đó **không** biến mất khi bạn có mutex. Mutex chỉ xếp hàng các **lời gọi hàm**; một tham chiếu hay iterator lấy ra trong khóa vẫn tồn tại sau khi khóa nhả, và nó vẫn bị vô hiệu bởi lần `push_back` của luồng khác.

```cpp
// bo-qua-kiem-tra
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

std::mutex khoa;
std::vector<int> v = {10, 20, 30};

int main() {
    int* p;
    {
        std::lock_guard<std::mutex> giu(khoa);
        p = &v[0];                                        // (1) lấy địa chỉ phần tử trong khóa
    }                                                     // (2) khóa nhả, nhưng p vẫn trỏ vào mảng cũ
    std::thread t([] {
        std::lock_guard<std::mutex> giu(khoa);            // (3) luồng khác xin khóa đúng luật
        for (int i = 0; i < 1000; ++i) v.push_back(i);    // (4) vector xin kệ mới, giải phóng kệ cũ
    });
    t.join();
    std::lock_guard<std::mutex> giu(khoa);
    std::cout << "doc qua p: " << *p << "\n";             // (5) dùng p: kệ cũ đã bị trả
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (1), (2) | `p` giữ địa chỉ ô đầu của mảng 3 phần tử | `p` -> kệ cũ (0x1000, địa chỉ minh họa) |
| (4) | `push_back` vượt dung lượng nên xin kệ mới, chép sang, **trả kệ cũ** | `v` -> kệ mới (0x2000); kệ cũ đã trả |
| (5) | `*p` đọc vào kệ cũ | đọc vùng đã trả: không xác định |

**Kết quả khi chạy**: chạy trần, mình được `doc qua p: -471749360` (một số rác; máy bạn ra số khác, hoặc sập). Với `-fsanitize=address`: `ERROR: AddressSanitizer: heap-use-after-free` với `READ of size 4`, `located 0 bytes inside of 12-byte region` (12 byte là mảng ba `int` ban đầu) và `freed by thread T1 here: ... push_back`. TSan cũng báo `heap-use-after-free`, và lưu ý nó ghi cả hai bên đều `mutexes: write M12`: **cả hai chỗ đều đang giữ khóa**, mà vẫn hỏng.

Quy tắc rút ra giống bẫy của [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md): đừng để tham chiếu, con trỏ, iterator tới phần tử thoát khỏi vùng khóa. Hoặc **sao chép giá trị** ra, hoặc giữ khóa suốt lúc dùng, hoặc đưa việc cần làm vào **trong** lớp bọc container như một hàm tự khóa.

### 7. Bốn kiểu khóa, và cách chọn

Sau khi biết **cái gì** gây hỏng, ta bàn **khóa thế nào**. Không có container "an toàn luồng" trong thư viện chuẩn: không có `concurrent_map`. Các thư viện ngoài có sẵn (Intel TBB có `concurrent_hash_map`, Folly có `ConcurrentHashMap`; chỉ nhắc tên). Bài này chỉ dùng thư viện chuẩn, tự bọc khóa lấy. Hàng đợi an toàn luồng là một chủ đề riêng, bài thực chiến [Bài 66](../nhom-9-thuc-chien-da-luong/66-bounded-queue.md) sẽ xây.

| Kiểu khóa | Cách làm | Hợp khi | **Không** hợp khi |
|---|---|---|---|
| **Một mutex** cho cả bảng | mọi hàm đọc/ghi đều `lock_guard` | mặc định; vùng găng ngắn; ít luồng | nhiều luồng, mỗi lần tranh khóa lâu |
| **`shared_mutex`** | đọc `shared_lock`, ghi `unique_lock` | **đọc áp đảo**, nhiều luồng đọc cùng lúc | ghi nhiều (đo của mình: không hơn mutex) |
| **Chia shard** | N bảng + N mutex, băm khóa chọn shard | nhiều luồng ghi **khóa khác nhau** | một khóa nóng; hay cần tổng/duyệt toàn bảng |
| **Sao chép khi ghi** | đọc "ảnh" bất biến, ghi tạo bản mới rồi tráo | bảng **nhỏ**, ghi rất hiếm | bảng lớn (mỗi ghi chép cả bảng), nhiều người ghi |

Thứ tự thử: **một mutex trước**, đo, rồi mới sang kiểu khác. Ba kiểu còn lại đều phức tạp hơn, và phức tạp có giá: nhiều chỗ để sai. Phần 💻 chạy thật hai nhóm: chia shard (ví dụ 1), `shared_mutex` và sao chép khi ghi (ví dụ 2), kèm số đo.

Còn một thứ **không** khóa nào giải quyết: **thao tác gồm nhiều bước**. `if (!bang.co(k)) bang.them(k, v);` với `co` và `them` mỗi hàm tự khóa vẫn là race condition ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md), câu kiểm-rồi-làm): giữa hai lần khóa, luồng khác chen vào. Phải gộp thành **một hàm** khóa một lần, như `them` ở ví dụ 1 gộp "tra rồi cộng 1" vào một lần khóa.

## 💻 Ví dụ code

### Ví dụ 1: đếm tần suất từ, một khóa và chia shard

Bài toán: bốn luồng cùng đếm số lần xuất hiện của từng từ, vào **một** bảng chung. Cách một: một mutex. Cách hai: **chia shard** (shard = mảnh): tám bảng, mỗi bảng một mutex; từ nào vào bảng nào do **hàm băm** quyết định ([Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md)). Hai luồng đếm hai từ ở hai shard khác nhau thì không chờ nhau.

Cú pháp mới: `std::hash<std::string>{}` dựng một bộ băm cho chuỗi, còn `(tu)` gọi nó như một hàm và nhận về một số lớn; `% SO_SHARD` (chia lấy dư) đổi số đó thành vị trí 0...7. `struct Shard` khai báo **bên trong** lớp, ở phần `private`, nên chỉ lớp thấy nó. `std::array<Shard, 8>` là mảng cố định 8 shard ([Bài 17](../nhom-2-stl-thuat-toan/17-string-array-deque-list.md)). Lambda `dem` có tham số `auto&` ([Bài 14](../nhom-1-nen-tang-bo-nho/14-cpp14-17.md)) nên dùng được cho cả hai lớp.

```cpp
#include <array>
#include <functional>
#include <iostream>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

class DemMotKhoa {                                       // (1) cách 1: một mutex cho cả bảng
public:
    void them(const std::string& tu) {
        std::lock_guard<std::mutex> giu(khoa);
        ++bang[tu];                                      // (2) operator[] có thể CHÈN: phải khóa, kể cả khi "chỉ cộng 1"
    }
    int lay(const std::string& tu) {
        std::lock_guard<std::mutex> giu(khoa);
        auto it = bang.find(tu);
        return it == bang.end() ? 0 : it->second;        // (3) trả bản sao của số, không trả tham chiếu
    }
private:
    std::mutex khoa;
    std::unordered_map<std::string, int> bang;
};

const std::size_t SO_SHARD = 8;

class DemChiaShard {                                     // (4) cách 2: 8 bảng, mỗi bảng một mutex
public:
    void them(const std::string& tu) {
        Shard& s = chonShard(tu);
        std::lock_guard<std::mutex> giu(s.khoa);         // (5) chỉ khóa MỘT shard, 7 shard kia vẫn chạy
        ++s.bang[tu];
    }
    int lay(const std::string& tu) {
        Shard& s = chonShard(tu);
        std::lock_guard<std::mutex> giu(s.khoa);
        auto it = s.bang.find(tu);
        return it == s.bang.end() ? 0 : it->second;
    }
private:
    struct Shard {
        std::mutex khoa;
        std::unordered_map<std::string, int> bang;
    };
    Shard& chonShard(const std::string& tu) {
        return cacShard[std::hash<std::string>{}(tu) % SO_SHARD];   // (6) cùng một từ luôn vào cùng một shard
    }
    std::array<Shard, SO_SHARD> cacShard;
};

int main() {
    std::vector<std::string> kho;                        // (7) 100000 từ: "tu0".."tu499" lặp lại, mỗi từ 200 lần
    for (int i = 0; i < 100000; ++i) kho.push_back("tu" + std::to_string(i % 500));

    auto dem = [&kho](auto& bo) {                        // (8) lambda nhận "bo" thuộc kiểu nào cũng được
        std::vector<std::thread> cacLuong;
        for (int k = 0; k < 4; ++k) {
            cacLuong.emplace_back([&kho, &bo, k] {
                for (int i = k * 25000; i < (k + 1) * 25000; ++i) bo.them(kho[i]);   // (9) mỗi luồng một phần tư
            });
        }
        for (std::thread& t : cacLuong) t.join();
    };

    DemMotKhoa a;
    DemChiaShard b;
    dem(a);
    dem(b);

    bool giongNhau = true;                               // (10) đối chiếu với đáp án biết trước: mỗi từ đúng 200 lần
    for (int i = 0; i < 500; ++i) {
        std::string tu = "tu" + std::to_string(i);
        if (a.lay(tu) != 200 || b.lay(tu) != 200) giongNhau = false;
    }
    std::cout << "tu7 (mot khoa)    = " << a.lay("tu7") << "\n";
    std::cout << "tu7 (chia shard)  = " << b.lay("tu7") << "\n";
    std::cout << "du 500 tu, moi tu 200 lan? " << giongNhau << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (7) | Dựng `kho` 100000 từ, mỗi từ trong 500 từ lặp đúng 200 lần | `kho` chỉ được ĐỌC từ đây |
| (9) | Bốn luồng, mỗi luồng 25000 từ liền nhau, gọi `them` | 4 luồng cùng một `bo` |
| (2) | `DemMotKhoa`: cả bốn xếp hàng trước **một** `khoa` | 1 khóa, 1 bảng |
| (6), (5) | `DemChiaShard`: băm `tu` ra 0...7, khóa đúng shard đó | 8 khóa, 8 bảng; hai từ khác shard không chờ nhau |
| (10) | Sau `join`, tra từng từ trong cả hai bảng, phải đúng 200 | không còn luồng nào ghi |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
tu7 (mot khoa)    = 200
tu7 (chia shard)  = 200
du 500 tu, moi tu 200 lan? 1
```

**Thử thay đổi: xóa dòng (5)** (bỏ `lock_guard` trong `DemChiaShard::them`). Mình đã chạy: vẫn biên dịch sạch, nhưng **5 lần liền đều chết** với mã 139 (segmentation fault): nhiều luồng chèn cùng lúc vào một `unordered_map` làm bảng băm hỏng. TSan báo hàng loạt `data race` trong `hashtable.h`.

Hai điểm cần nhớ về shard. Một: **hàm `lay` chỉ khóa một shard** nên đúng; nhưng một hàm kiểu `tongSo()` cộng kích thước các shard phải khóa **lần lượt** từng shard, và giữa hai lần khóa luồng khác vẫn thêm/xóa. Tổng đó **không bảo đảm** là tổng ở một thời điểm thật nào (chỉ chắc chắn khi không còn ai ghi, như sau `join` ở trên). Muốn con số đúng ở một thời điểm thì phải giữ khóa **mọi** shard cùng lúc, theo thứ tự cố định để tránh deadlock ([Bài 26](../nhom-3-da-luong/26-deadlock.md)). Hai: số shard cố định 8 ở đây; tăng giảm số shard khi đang chạy khó, vì mọi khóa đã băm theo số cũ.

**Đo: chia shard có đáng không?** Mình thay `main` bằng bản bọc `steady_clock` quanh `dem(a)` và `dem(b)`: 8 luồng, mỗi luồng gọi `them` 400000 lần (cả `kho` bốn lượt), rồi in `msMot / msShard` (lớn hơn 1: shard nhanh hơn). Máy mình có 8 lõi. Năm lần liền: không tối ưu, tỉ lệ từ **2,8 đến 3,7**; với `-O2`, từ **1,7 đến 2,3**. Số đổi theo máy và cờ biên dịch, nhưng hướng thì rõ: shard thắng khi nhiều luồng ghi các khóa khác nhau.

Hai thử nghiệm "không đáng" mình cũng chạy, bốn lần mỗi thử nghiệm. Đổi `i % 500` thành luôn cùng một từ (**khóa nóng**, mọi lượt vào một shard): tỉ lệ còn **0,94 đến 1,01**. Chỉ chạy 1 luồng: **0,80 đến 1,04**. Tức là không được gì cả. Bản đo không nằm trong khối chạy tự động vì số thời gian đổi theo máy và chậm đi nhiều lần dưới TSan; hai lớp đúng thì đã chạy TSan sạch ở trên.

### Ví dụ 2: cache đọc nhiều ghi ít, `shared_mutex` và sao chép khi ghi

Bài toán: một cache nhỏ, nhiều luồng đọc liên tục, thỉnh thoảng một luồng ghi. Hai cách tận dụng "đọc không chặn nhau". Cách `shared_mutex`: nhiều luồng `shared_lock` cùng lúc, `unique_lock` khi ghi. Cách **sao chép khi ghi** (copy-on-write): bảng hiện tại là một `shared_ptr<const Bang>` **không bao giờ bị sửa tại chỗ**. Người đọc chụp "ảnh" bằng cách sao chép `shared_ptr` rồi tra trong ảnh. Người ghi chép cả bảng ra bản nháp, sửa bản nháp, rồi **tráo** con trỏ sang bản mới.

Cú pháp mới: `using Bang = std::map<std::string, int>;` là tên gọn cho kiểu dài ([Bài 36](../nhom-4-oop-patterns/36-pattern-observer-strategy.md)). `std::atomic_load(&hienTai)` và `std::atomic_store(&hienTai, ...)` là hai hàm đọc và ghi **một biến `shared_ptr` một cách nguyên tử**; [Bài 52](52-smart-pointer-da-luong.md) (mục 2) đã giải thích vì sao cần. Phần sau dấu `:` ở hàm tạo là danh sách khởi tạo ([Bài 31](../nhom-4-oop-patterns/31-lop-dong-goi.md)) đặt giá trị đầu cho `hienTai`: một bảng rỗng.

```cpp
#include <atomic>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <thread>
#include <vector>

using Bang = std::map<std::string, int>;                 // (1) "Bang" là tên gọn cho kiểu map này

class CacheSharedMutex {                                 // (2) cách 3: đọc chung, ghi riêng
public:
    int doc(const std::string& k) {
        std::shared_lock<std::shared_mutex> giu(khoa);   // (3) nhiều luồng đọc cùng lúc
        auto it = bang.find(k);
        return it == bang.end() ? -1 : it->second;
    }
    void ghi(const std::string& k, int v) {
        std::unique_lock<std::shared_mutex> giu(khoa);   // (4) ghi: giữ riêng, không ai đọc/ghi cùng lúc
        bang[k] = v;
    }
private:
    std::shared_mutex khoa;
    Bang bang;
};

class CacheSaoChepKhiGhi {                               // (5) cách 4: đọc không khóa của mình
public:
    CacheSaoChepKhiGhi() : hienTai(std::make_shared<const Bang>()) {}
    int doc(const std::string& k) {
        std::shared_ptr<const Bang> anh = std::atomic_load(&hienTai);   // (6) chụp "ảnh" hiện tại, giữ nó sống
        auto it = anh->find(k);
        return it == anh->end() ? -1 : it->second;
    }
    void ghi(const std::string& k, int v) {
        std::lock_guard<std::mutex> giu(khoaGhi);        // (7) chỉ các luồng GHI xếp hàng với nhau
        Bang moi = *std::atomic_load(&hienTai);          // (8) chép cả bảng ra bản nháp
        moi[k] = v;                                      // (9) sửa bản nháp
        std::atomic_store(&hienTai, std::make_shared<const Bang>(std::move(moi)));   // (10) tráo bản mới vào
    }
private:
    std::shared_ptr<const Bang> hienTai;
    std::mutex khoaGhi;
};

int main() {
    CacheSharedMutex c1;
    CacheSaoChepKhiGhi c2;

    auto thu = [](auto& cache) {                         // (11) lambda dùng cho cả hai kiểu cache; trả số lần đọc thấy số LÙI
        std::atomic<bool> xong{false};
        std::atomic<int> lui{0};
        std::vector<std::thread> docGia;
        for (int k = 0; k < 3; ++k) {
            docGia.emplace_back([&] {
                int truoc = -1;
                while (!xong) {
                    int v = cache.doc("a");
                    if (v < truoc) ++lui;                // (12) writer chỉ ghi số tăng dần, nên đọc thấy số giảm là lỗi
                    truoc = v;
                }
            });
        }
        for (int v = 1; v <= 300; ++v) cache.ghi("a", v);   // (13) một luồng ghi 300 lần
        xong = true;
        for (std::thread& t : docGia) t.join();
        return lui.load();
    };

    int l1 = thu(c1);
    int l2 = thu(c2);
    std::cout << "shared_mutex:     a = " << c1.doc("a") << ", lan doc thay lui: " << l1 << "\n";
    std::cout << "sao chep khi ghi: a = " << c2.doc("a") << ", lan doc thay lui: " << l2 << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra | Bộ nhớ lúc này |
|---|---|---|
| (3) | Ba luồng đọc cùng giữ `shared_lock`: không chặn nhau | khóa ở chế độ "chia sẻ" |
| (4) | Luồng ghi chờ mọi người đọc nhả, rồi giữ `unique_lock` riêng | khóa ở chế độ "độc quyền" |
| (6) | Người đọc sao chép `shared_ptr` nguyên tử: đếm tham chiếu của bản hiện tại tăng 1 | `anh` -> bản hiện tại |
| (8)-(10) | Người ghi chép bảng, sửa bản nháp, tráo con trỏ sang bản mới | `hienTai` -> bản mới; bản cũ sống tới khi người đọc cuối thả `anh` |
| (12) | Mỗi người đọc nhớ số vừa thấy; thấy số nhỏ hơn là bản cũ "sống lại": không được | `lui` phải còn 0 |

**Kết quả khi chạy** (ba lần liền đều như nhau; TSan sạch, mã thoát 0):

```text
shared_mutex:     a = 300, lan doc thay lui: 0
sao chep khi ghi: a = 300, lan doc thay lui: 0
```

Số lần mỗi người đọc đọc được **đổi theo lần chạy** và không được in; thứ cố định là giá trị cuối `300` và `0` lần đọc lùi.

**Thử thay đổi: ở (6) thay `std::atomic_load(&hienTai)` bằng `hienTai` thường** (sao chép trực tiếp). Mình đã chạy: chạy trần vẫn in đúng như trên, nhưng TSan báo `data race`: `Previous read of size 8 ... shared_ptr copy constructor` (luồng đọc) và `Write of size 8 ... atomic_store` (luồng ghi). Nghĩa là chính **biến `shared_ptr`** `hienTai` bị đọc và ghi đồng thời không đồng bộ; bộ đếm bên trong là nguyên tử, nhưng biến trỏ thì không ([Bài 52](52-smart-pointer-da-luong.md) mục 2 đã nói kỹ; ở đây chỉ cần nhớ: đọc/ghi `hienTai` phải qua `atomic_load`/`atomic_store`).

**Đo: có đáng không?** Mình viết một bản đo ngoài bộ kiểm tự động (cùng hai lớp trên, thêm lớp `CacheMotKhoa` dùng `std::mutex` cho cả đọc lẫn ghi, bảng nạp sẵn 1000 khóa): 8 luồng đọc, mỗi luồng 200000 lần tra một khóa, một luồng ghi thưa (mỗi 100 micro-giây một lần), rồi in thời gian của `CacheMotKhoa` chia thời gian từng cách. Máy 8 lõi, năm lần mỗi cấu hình, đọc áp đảo:

- Không tối ưu: `shared_mutex` nhanh hơn một mutex **7,8 đến 10,2 lần**, sao chép khi ghi **3,6 đến 4,1 lần**.
- Với `-O2`: `shared_mutex` **3,0 đến 3,8 lần**, sao chép khi ghi **1,3 đến 1,4 lần**.
- Khi **một nửa số thao tác là ghi** (chỉ đo `shared_mutex`, bốn lần): tỉ lệ **0,69 đến 1,07** không tối ưu, **0,95 đến 1,78** với `-O2`, tức là không hơn gì một mutex.

Nên `shared_mutex` thắng khi đọc áp đảo nhưng không khi ghi nhiều. Sao chép khi ghi **không** thắng như nhiều người tưởng: `std::atomic_is_lock_free(&hienTai)` ra `0` trên g++ 11 này, tức `atomic_load` của `shared_ptr` **dùng một khóa nhỏ bên trong thư viện** (TSan cho thấy một mutex tạo bởi `std::_Sp_locker`), và mỗi lần đọc còn tăng giảm một bộ đếm chung. "Đọc không khóa" đúng ở nghĩa **không có khóa của mình**, chưa chắc nhanh nhất. Hãy tự đo trên máy và tải thật của bạn.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`std::vector` / `std::map` có thread-safe không?"
    Trả lời hai nửa. Nhiều luồng **chỉ đọc** (gọi hàm `const`) thì an toàn. Hễ có một luồng **ghi** (`push_back`, `erase`, `insert`, `m[k]` với khóa chưa có...) thì mọi truy cập khác phải được đồng bộ, nếu không là data race, tức hành vi không xác định (mình chạy: 10 lần `push_back` đồng thời, cả 10 lần chết). Ngoại lệ chuẩn nêu: ghi các **phần tử khác nhau** từ các luồng khác nhau thì ổn (có thể chậm vì false sharing, Bài 30), **trừ `vector<bool>`**: nó nén bit, hai bit chung một từ nhớ nên ghi một bit có thể xóa bit của luồng kia (mình chạy: thiếu bit, TSan báo race). Hỏi nối tiếp "`m[k]` để đọc có an toàn không?": không, `operator[]` chèn khóa vắng nên là ghi; dùng `find`/`count`/`at`. Cuối cùng, mutex bảo vệ các **lời gọi**, không bảo vệ tham chiếu hay iterator đã lấy ra rồi.

??? question "Làm một cache đa luồng, đọc nhiều ghi ít. Bạn làm thế nào?"
    Nói theo bậc thang, nêu rõ lý do đi lên từng bậc. Bậc 1: một `std::mutex` cho cả `unordered_map`, đơn giản và đúng, đo trước. Bậc 2: nếu đo thấy khóa là điểm nghẽn và đọc áp đảo, đổi sang `shared_mutex` (đọc `shared_lock`, ghi `unique_lock`); của mình đo được nhanh hơn 3 đến 10 lần khi đọc áp đảo. Bậc 3: nếu bảng nhỏ và ghi hiếm thì sao chép khi ghi (đọc chụp ảnh `shared_ptr<const Bang>`). Nếu nhiều luồng ghi các khóa khác nhau thì chia shard. Nhớ nói thêm: cache còn phải xử lý "khóa vắng thì tính và ghi", gộp thành **một** thao tác để hai luồng không cùng tính lại.
    Nối tiếp: **"thế nếu ghi nhiều thì sao?"** `shared_mutex` không còn lợi (mình đo 50% ghi: tỉ lệ quanh 1), hãy quay về một mutex hoặc chia shard. **"Thế nếu bảng rất lớn?"** Sao chép khi ghi chép cả bảng mỗi lần ghi, chi phí tỉ lệ với kích thước bảng, nên loại; chia shard hợp hơn.

??? question "Vì sao thư viện chuẩn không có `concurrent_map`? Dùng gì thay?"
    Vì không có một thiết kế khóa nào tốt cho mọi mẫu truy cập: một khóa, khóa đọc-ghi, chia shard, lock-free mỗi cái đúng cho một tải khác nhau, và nhiều thao tác như duyệt hay đếm cần ngữ nghĩa riêng. Nên chuẩn để bạn tự chọn và bọc `mutex` quanh container thường. Thư viện ngoài có sẵn (TBB `concurrent_hash_map`, Folly `ConcurrentHashMap`; chỉ nhắc tên). Chia shard tự viết là cách phổ biến nhất khi cần.

??? question "Với map chia shard, hàm `size()` hay duyệt toàn bảng có vấn đề gì?"
    Muốn đếm hay duyệt qua nhiều shard phải khóa từng shard, mà giữa hai lần khóa luồng khác vẫn ghi, nên kết quả **không phải ảnh chụp ở một thời điểm**. Chấp nhận được nếu số liệu chỉ để thống kê gần đúng. Nếu cần chính xác phải giữ khóa mọi shard cùng lúc, theo **thứ tự cố định** (tránh deadlock, Bài 26), và đó là cái giá của việc chia nhỏ khóa.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Coi \"mỗi hàm tự khóa\" là \"cả thao tác an toàn\""
    `if (!bang.co(k)) bang.them(k, v);` với hai hàm đều tự khóa vẫn là race condition: khóa nhả giữa hai lệnh, hai luồng cùng thấy "chưa có" rồi cùng thêm. Gộp "kiểm rồi làm" vào **một** hàm giữ khóa một lần (như `++bang[tu]` trong `them` ở ví dụ 1).

!!! warning "Lỗi 2: Giữ tham chiếu, con trỏ hay iterator sau khi nhả khóa"
    Mình đã chạy ở mục 6: mọi truy cập vector đều trong khóa mà vẫn `heap-use-after-free`, vì `push_back` của luồng khác làm con trỏ lấy trước đó hết hiệu lực. Trả **bản sao**, hoặc giữ khóa suốt lúc dùng.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="54" markdown>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 1.** Đọc đoạn sau. Hai luồng chạy cùng lúc, không khóa. Điều nào đúng?

```text
std::vector<bool> co(64, false);
luồng A:  co[3]  = true;
luồng B:  co[40] = true;
```

- Không có lỗi, vì hai bit nằm ở hai vị trí khác nhau
- Chỉ lỗi nếu cả hai luồng cùng ghi một chỉ số
- Có lỗi, vì `vector<bool>` luôn phải gọi `reserve` trước khi dùng
- Có data race: ghi một bit là đọc-sửa-ghi cả từ nhớ chứa nó

<p class="giai-thich" markdown>`vector<bool>` nén mỗi phần tử thành một bit, nên bit 3 và bit 40 cùng nằm trong một từ nhớ và mỗi lần ghi bit là đọc-sửa-ghi cả từ đó. Hai luồng làm vậy cùng lúc có thể xóa bit của nhau, và chuẩn loại riêng `vector<bool>` khỏi bảo đảm ghi phần tử khác nhau. Nói "hai vị trí khác nhau nên ổn" đúng với `vector<char>` nhưng sai ở đây. `reserve` không liên quan vì ở đây không có `push_back`.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Đọc đoạn sau. Cả hai luồng cùng chạy dòng thứ hai, `m` không bị luồng nào khác đụng. Vì sao có data race dù "chỉ đọc"?

```text
std::map<std::string, int> m = {{"a", 1}};
int x = m["b"];
```

- `operator[]` chèn khóa "b" chưa có, nên cả hai luồng cùng ghi vào cây
- Hai luồng cùng đọc khóa "b", mà chuẩn coi hai lần đọc cùng một khóa là xung đột
- `map` luôn cần khóa, ngay cả khi mọi luồng chỉ gọi các hàm `const` của nó
- Phép gán vào `int x` ghi ngược lại vào `m`, nên hai luồng xung đột nhau

<p class="giai-thich" markdown>`m["b"]` với khóa chưa có tạo ra một nút mới rồi trả giá trị mặc định, nên đó là thao tác ghi vào cấu trúc cây và hai luồng làm đồng thời là race. Hai luồng chỉ đọc thì không bao giờ xung đột, kể cả cùng một khóa. Không đúng rằng `map` luôn cần khóa: nhiều luồng chỉ gọi hàm `const` là hợp lệ. Còn gán vào `x` chỉ ghi vào biến cục bộ của mỗi luồng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 3.** Một bảng tỉ giá nhỏ, 16 luồng tra liên tục, một luồng cập nhật vài giây một lần. Bạn muốn các luồng đọc **không chặn nhau** mà vẫn an toàn khi có ghi. Cách nào đáp ứng đúng?

- Bỏ khóa ở các hàm đọc, vì ghi rất hiếm nên hầu như không bao giờ đụng nhau
- Chia 16 shard, mỗi shard một `std::mutex` thường, mỗi luồng đọc một shard
- Dùng `shared_mutex`: `shared_lock` khi đọc, `unique_lock` khi ghi
- Dùng một `std::mutex` cho cả bảng, khóa cả khi đọc lẫn khi ghi, cho đơn giản

<p class="giai-thich" markdown>`shared_mutex` cho phép nhiều luồng giữ chế độ đọc cùng lúc và chỉ chặn khi có người ghi. Bỏ khóa ở hàm đọc là data race ngay khi luồng ghi đến, dù hiếm. Chia shard bằng `mutex` thường vẫn bắt các luồng đọc cùng shard xếp hàng, và nếu đọc dồn vào vài khóa thì gần như không đổi. Một mutex duy nhất thì đọc nào cũng xếp hàng.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** Đếm tần suất từ bằng 8 luồng vào một bảng chia 8 shard. 95% lượt đếm là cùng một từ "the". Chia shard giúp nhiều không?

- Có, vì 8 shard cho phép 8 luồng chạy song song, mỗi luồng một khóa riêng
- Gần như không, vì "the" luôn băm vào một shard nên vẫn xếp hàng chờ một khóa
- Không, vì chia shard luôn chậm hơn dùng một khóa duy nhất cho cả bảng
- Có, nhưng chỉ khi đổi `unordered_map` trong mỗi shard thành `map` có thứ tự

<p class="giai-thich" markdown>Shard chọn theo hàm băm của khóa, nên cùng một từ luôn vào cùng một shard; 95% lượt đếm đều tranh nhau khóa của shard đó, giống như dùng một khóa. Mình đo khóa nóng thì tỉ lệ so với một khóa quanh 1. Nói "8 shard cho 8 luồng chạy riêng" chỉ đúng khi khóa phân bố đều. Nói "luôn chậm hơn" cũng sai, vì khi khóa phân bố đều shard thắng rõ. Đổi sang `map` không đổi được việc cả đám vẫn đụng một khóa.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 5.** Đọc đoạn sau. Mọi chỗ đụng vào `v` (một `vector<int>`) đều nằm trong khóa `m`. Luồng khác, cũng trong khóa, `push_back` thêm 1000 phần tử rồi kết thúc. Lỗi nằm ở đâu?

```text
int* p;
{ std::lock_guard<std::mutex> g(m); p = &v[0]; }
...                               // luồng khác push_back 1000 lần
{ std::lock_guard<std::mutex> g(m); std::cout << *p; }
```

- Ở `std::cout`, vì không được in ra màn hình khi đang giữ khóa của mutex
- Không có lỗi, vì mọi lần đọc và ghi `v` đều nằm trong vùng giữ khóa `m`
- Ở chỗ hai khối khóa dùng chung một mutex `m` ngay trong cùng một luồng
- `p` trỏ vào mảng cũ mà `push_back` đã trả, nên `*p` đọc vùng đã giải phóng

<p class="giai-thich" markdown>Khóa chỉ xếp hàng các lần truy cập, còn `p` là địa chỉ lấy trong khóa nhưng dùng sau khi nhả. `push_back` của luồng khác có thể xin mảng mới và trả mảng cũ, nên `*p` đọc vùng bộ nhớ đã giải phóng. In ra `cout` trong khóa không sai, chỉ chậm. Hai khối dùng cùng `m` lần lượt trong một luồng cũng hợp lệ vì khối trước đã nhả khóa. Còn "mọi chỗ đều khóa nên an toàn" là đúng cho lời gọi hàm, không cho con trỏ đã lấy ra.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Map chia 8 shard. Hàm `tongSo()` làm: khóa shard 0, đếm, nhả, rồi sang shard 1 và cứ thế. Trong lúc đó các luồng khác vẫn thêm và xóa. Kết quả `tongSo()` nói gì?

- Không bảo đảm là tổng tại một thời điểm thật, vì mỗi shard đếm vào lúc riêng
- Luôn là tổng đúng ở một thời điểm nào đó, vì mỗi shard đều được khóa khi đếm
- Luôn nhỏ hơn số phần tử thật, vì các shard sau không bao giờ được đếm đủ
- Hàm bị deadlock, vì nó phải giữ nhiều mutex của các shard liên tiếp nhau

<p class="giai-thich" markdown>Từng shard đếm đúng tại lúc nó được khóa, nhưng giữa hai lần khóa luồng khác kịp thêm hoặc xóa, nên tổng ghép lại có thể chưa từng đúng ở thời điểm nào. Nói "luôn đúng nhờ mỗi shard có khóa" nhầm tính đúng từng mảnh với tính đúng của tổng. Hàm này nhả khóa trước khi sang shard kế nên không giữ hai khóa cùng lúc và không deadlock. Số đếm có thể lớn hơn hoặc nhỏ hơn, không có chiều cố định.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Bộ đếm lượt truy cập theo địa chỉ web: 16 luồng ghi liên tục, mỗi lần cộng 1 cho một trong hàng nghìn địa chỉ khác nhau (gặp đều nhau), gần như không ai đọc. Bạn đã đo và thấy một `std::mutex` cho cả bảng là điểm nghẽn. Nên đổi sang cách nào?

- `shared_mutex`, vì nó cho nhiều luồng cùng vào một lúc
- Chia shard: nhiều bảng nhỏ, mỗi bảng một mutex riêng
- Sao chép khi ghi: mỗi lần cộng tạo bản bảng mới rồi tráo con trỏ
- Bỏ khóa, vì mỗi lần chỉ cộng 1 nên không ai giẫm lên ai

<p class="giai-thich" markdown>Ghi áp đảo mà khóa gặp đều nhau là đúng chỗ của chia shard: hai luồng đếm hai địa chỉ ở hai shard khác nhau thì không chờ nhau. `shared_mutex` chỉ cho nhiều luồng **đọc** cùng lúc; mọi lần cộng đều là ghi nên vẫn xếp hàng (mình đo khi ghi nhiều thì không hơn một mutex). Sao chép khi ghi phải chép cả bảng hàng nghìn khóa ở mỗi lần cộng, quá đắt. Bỏ khóa là data race: `++bang[diaChi]` có thể chèn khóa mới và sửa cấu trúc bảng, nên "chỉ cộng 1" không làm nó an toàn.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Ba luật của chuẩn: nhiều luồng **chỉ đọc** (hàm `const`) thì ổn; có một luồng **ghi** thì mọi truy cập khác phải đồng bộ; ghi các **phần tử khác nhau** từ các luồng khác nhau thì ổn, trừ `vector<bool>` (bit đóng gói chung từ nhớ: mình chạy ra thiếu bit, TSan báo race).
2. `push_back` đồng thời là data race (mình chạy 10 lần, cả 10 lần chết); `m[k]` trên `map`/`unordered_map` có thể **chèn** nên cũng là ghi, muốn đọc thì dùng `find`/`count`/`at`; Go thì runtime báo `fatal error: concurrent map read and map write`.
3. Khóa đúng vẫn chưa đủ: tham chiếu, con trỏ, iterator lấy ra trong khóa mà dùng sau khi nhả bị vô hiệu bởi `push_back` của luồng khác (mình chạy: `heap-use-after-free` dù mọi chỗ đều khóa); thao tác nhiều bước ("kiểm rồi chèn") phải gộp vào **một** lần khóa.
4. Chọn kiểu khóa theo mẫu truy cập và **đo**: một mutex trước; `shared_mutex` khi đọc áp đảo (mình đo nhanh hơn 3 đến 10 lần, nhưng không hơn khi 50% là ghi); chia shard khi nhiều luồng ghi các khóa khác nhau (nhanh hơn 1,7 đến 3,7 lần, nhưng không hơn khi có khóa nóng, và tổng/duyệt qua shard không là ảnh chụp một thời điểm); sao chép khi ghi cho bảng nhỏ ghi hiếm (`atomic_load` của `shared_ptr` ở g++ 11 không lock-free).
5. Thư viện chuẩn không có `concurrent_map` (TBB/Folly có, chỉ nhắc tên); câu "cache đọc nhiều ghi ít" trả lời theo bậc thang: mutex, `shared_mutex`, sao chép khi ghi hoặc chia shard, kèm câu "thế nếu ghi nhiều / bảng lớn thì sao".
