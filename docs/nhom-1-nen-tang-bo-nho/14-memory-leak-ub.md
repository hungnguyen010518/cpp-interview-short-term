# Bài 14 — Memory leak, dangling, UB và công cụ phát hiện

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt được rò rỉ bộ nhớ, con trỏ treo, giải phóng hai lần và hành vi không xác định.
    - Biết dùng AddressSanitizer và Valgrind để tìm lỗi bộ nhớ.
    - Biết cách phòng tránh các lỗi này trong C++ hiện đại.

## 🧠 Câu chuyện mở đầu

Quay lại **kho đồ của trường** ở [Bài 2](02-stack-heap-static.md).

**Rò rỉ (leak)**: bạn mượn đồ mà quên trả. Kho đầy dần, đến lúc không còn chỗ cho ai.

**Con trỏ treo (dangling pointer)**: bạn cầm tờ giấy ghi "đồ ở phòng 12". Nhưng phòng 12 đã bị dỡ. Đến đó, bạn thấy gì cũng có thể xảy ra.

**Giải phóng hai lần (double free)**: bạn trả cùng một món đồ hai lần. Sổ sách rối tung.

**Hành vi không xác định (UB)**: luật chơi đã bị phá. Nên mọi chuyện đều có thể xảy ra. Lúc thì "chạy đúng". Lúc thì sập. Lúc thì sai âm thầm. Đổi máy là đổi kết quả.

## 📖 Giải thích

Có bốn loại lỗi bộ nhớ hay gặp. Rò rỉ là lỗi quản lý bộ nhớ, nhưng chương trình vẫn chạy hợp lệ, chỉ tốn bộ nhớ. Ba loại còn lại là hành vi không xác định (UB).

- **Memory leak (rò rỉ bộ nhớ)**: xin vùng nhớ rồi không trả. Không phải UB, chỉ là phí bộ nhớ.
- **Dangling pointer / use-after-free (con trỏ treo / dùng sau khi trả)**: con trỏ vẫn giữ địa chỉ của vùng nhớ đã được trả hoặc đã bị dọn (như biến cục bộ đã ra khỏi phạm vi), mà bạn vẫn dùng nó.
- **Double free (giải phóng hai lần)**: trả một vùng nhớ hai lần. Bộ cấp phát bộ nhớ bị rối.
- **Buffer overflow (ghi vượt biên mảng)**: đọc hoặc ghi ra ngoài vùng nhớ của mảng.

**UB (undefined behavior, hành vi không xác định)** nghĩa là chuẩn C++ không quy định chương trình sẽ làm gì. Nó có thể chạy "đúng", có thể sai âm thầm, có thể sập. Kết quả đổi theo trình biên dịch và theo máy.

Một số ví dụ UB khác: tràn số nguyên có dấu, data race (hai luồng cùng truy cập một biến, ít nhất một luồng ghi, không có đồng bộ), giải tham chiếu `nullptr`.

Quy tắc ghép đôi:

- `new` đi với `delete`.
- `new[]` đi với `delete[]`.
- Trộn lẫn là UB.

**Công cụ tìm lỗi**:

- **AddressSanitizer (ASan)**: bạn biên dịch với cờ `-fsanitize=address`. Chương trình tự báo khi truy cập bộ nhớ sai. Trên Linux, nó còn báo rò rỉ lúc chương trình kết thúc. ASan nhanh hơn Valgrind nhiều: thường chỉ chậm khoảng 2 lần so với 20–50 lần.
- **Valgrind (memcheck)**: bạn không cần biên dịch lại. Nó chạy chương trình trong một "máy ảo" để kiểm tra từng lần truy cập bộ nhớ. Vì vậy nó chậm hơn nhiều.

**Cách phòng tránh**:

- Dùng RAII và smart pointer (xem [Bài 8](08-raii.md) đến [Bài 10](10-shared-ptr-weak-ptr.md)).
- Dùng container chuẩn như `vector`, `string`.
- Tránh `new`/`delete` trần.
- Bật cảnh báo `-Wall -Wextra`.

## 💻 Ví dụ code

Ví dụ 1: chương trình rò rỉ ba lần.

```cpp
#include <iostream>

int main() {
    for (int i = 0; i < 3; ++i) {
        int* p = new int(i);          // quên delete → rò rỉ 3 lần
        std::cout << *p << "\n";
    }
    return 0;                         // vẫn thoát bình thường, rò rỉ âm thầm
}
```

Kết quả in ra: `0`, `1`, `2`, mỗi số một dòng. Rò rỉ không làm chương trình báo lỗi, nên phải dùng công cụ mới thấy.

Ví dụ 2: sửa bằng `unique_ptr`.

```cpp
#include <iostream>
#include <memory>

int main() {
    for (int i = 0; i < 3; ++i) {
        auto p = std::make_unique<int>(i);   // tự trả khi hết vòng lặp
        std::cout << *p << "\n";
    }
    return 0;
}
```

Kết quả in ra: `0`, `1`, `2`. Lần này không còn rò rỉ.

Ví dụ 3: lệnh shell để tìm lỗi (khối `bash`, không được biên dịch). Giả sử ví dụ 1 lưu trong file `rolo.cpp`.

```bash
# Biên dịch kèm AddressSanitizer rồi chạy: tự báo lỗi bộ nhớ và rò rỉ
g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer rolo.cpp -o rolo
./rolo

# Hoặc dùng Valgrind trên chương trình đã biên dịch thường
g++ -std=c++17 -g rolo.cpp -o rolo
valgrind --leak-check=full ./rolo
```

!!! note "Kết quả mẫu"
    Đây là kết quả chạy thật của lệnh ASan ở trên với ví dụ 1, đã rút gọn (bỏ địa chỉ và đường dẫn riêng của máy). Sau ba dòng `0`, `1`, `2`, ASan in ra:

    ```text
    ==PID==ERROR: LeakSanitizer: detected memory leaks

    Direct leak of 12 byte(s) in 3 object(s) allocated from:
        #0 0x... in operator new(unsigned long)
        #1 0x... in main rolo.cpp:5

    SUMMARY: AddressSanitizer: 12 byte(s) leaked in 3 allocation(s).
    ```

    Đọc kết quả: 3 lần `new int` mỗi lần 4 byte, tổng 12 byte, đều được xin ở `rolo.cpp` dòng 5 và không được trả. Khi có rò rỉ, ASan còn làm chương trình thoát với mã khác 0.

    Với Valgrind, bài này chỉ giới thiệu lệnh. Lệnh `--leak-check=full` bảo nó liệt kê chi tiết từng chỗ rò rỉ.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Làm sao tìm memory leak?"
    Dùng AddressSanitizer (có LeakSanitizer kèm theo trên Linux), Valgrind memcheck, hoặc công cụ phân tích heap.

    Về lâu dài, phòng bằng RAII và smart pointer để không phải tự nhớ `delete`.

??? question "Memory leak khác dangling pointer thế nào?"
    Leak: vùng nhớ vẫn còn nhưng không còn ai trỏ tới để trả.

    Dangling: con trỏ vẫn còn nhưng vùng nhớ đã được trả hoặc đã bị dọn.

??? question "Double free là gì, hậu quả?"
    Là giải phóng cùng một vùng nhớ hai lần. Nó làm hỏng bộ cấp phát bộ nhớ, có thể gây crash hoặc bị khai thác thành lỗ hổng bảo mật.

??? question "Vì sao `new[]` phải đi với `delete[]`?"
    `delete[]` gọi hàm hủy cho mọi phần tử của mảng và trả đúng khối nhớ.

    Dùng `delete` thường cho mảng là hành vi không xác định.

??? question "Cho vài ví dụ về UB."
    Đọc hoặc ghi ngoài mảng, dùng vùng nhớ sau khi `delete`, tràn số nguyên có dấu, data race, giải tham chiếu `nullptr`.

??? question "Buffer overflow là gì? Phát hiện thế nào?"
    Là ghi vượt biên của mảng hoặc vùng nhớ. ASan phát hiện lúc chạy.

    Phòng bằng `std::vector::at`, `std::string` và kiểm tra biên.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Dùng sau khi giải phóng"
    Sau `delete p`, con trỏ `p` vẫn giữ địa chỉ cũ. Nhưng vùng nhớ đó không còn thuộc về bạn. Dùng `*p` lúc này là UB.

    ```cpp
    // bo-qua-kiem-tra
    #include <iostream>
    int main() {
        int* p = new int(5);
        delete p;
        std::cout << *p << "\n";   // dùng sau khi trả: hành vi không xác định
    }
    ```

!!! warning "Lỗi 2: Trộn `new[]` với `delete` (hoặc `new` với `delete[]`)"
    `new int[10]` phải đi với `delete[]`. `new int(5)` phải đi với `delete`. Ghép sai là UB. ASan có thể báo lỗi `alloc-dealloc-mismatch`. Tốt nhất là dùng `std::vector` hoặc smart pointer để khỏi phải chọn.

!!! warning "Lỗi 3: Tin rằng chạy thử không sao nghĩa là không có UB"
    UB có thể chạy đúng ở máy này mà sập ở máy khác, hoặc sập sau khi đổi trình biên dịch. "Chạy thử không sao" không chứng minh được gì. Hãy dùng ASan và bật `-Wall -Wextra`.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="14" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Rò rỉ bộ nhớ (memory leak) là gì?

- Dùng vùng nhớ đã trả, nên con trỏ trỏ vào chỗ trống
- Ghi vượt biên mảng nên làm hỏng vùng nhớ bên cạnh
- Xin vùng nhớ nhưng không bao giờ trả lại, nên bộ nhớ bị chiếm dần
- Trả cùng một vùng nhớ hai lần nên bộ cấp phát bị rối

<p class="giai-thich" markdown>Mượn đồ mà quên trả. Các phương án còn lại là lỗi khác: dùng sau khi trả, ghi vượt mảng và giải phóng hai lần.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Con trỏ treo (dangling pointer) là gì?

- Con trỏ vẫn giữ địa chỉ của vùng nhớ đã được trả hoặc đã bị dọn
- Con trỏ đang bằng `nullptr` nên không trỏ vào đâu cả
- Con trỏ đang trỏ vào một biến nằm trên stack
- Con trỏ được khai báo `const` nên không đổi được chỗ trỏ

<p class="giai-thich" markdown>Tờ giấy ghi số phòng đã bị dỡ: dùng nó là UB. Vùng nhớ có thể đã được trả (heap) hoặc đã bị dọn (biến cục bộ ra khỏi phạm vi).</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Cờ biên dịch `-fsanitize=address` bật công cụ nào?

- Valgrind (memcheck)
- AddressSanitizer
- gdb
- UndefinedBehaviorSanitizer

<p class="giai-thich" markdown>ASan chèn các kiểm tra vào chương trình lúc biên dịch và báo lỗi lúc chạy. Valgrind không cần cờ này, gdb là trình gỡ lỗi, còn UBSan dùng cờ `-fsanitize=undefined`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Vì sao mảng cấp phát bằng `new int[10]` phải giải phóng bằng `delete[]`?

- Chỉ là quy ước đặt tên; dùng `delete` thường cho mảng vẫn đúng
- `delete[]` chạy nhanh hơn `delete` nên được khuyên dùng
- `delete` thường chỉ trả phần tử đầu, các phần tử khác chắc chắn rò rỉ
- `delete[]` hủy mọi phần tử và trả đúng khối nhớ; dùng `delete` thường là UB

<p class="giai-thich" markdown>Với `new[]`, thường (nhất là khi phần tử có hàm hủy) chương trình ghi thêm thông tin phụ để `delete[]` biết cần hủy bao nhiêu phần tử và trả đúng khối nhớ. Dùng `delete` thường thì không có gì đảm bảo, đó là hành vi không xác định, không phải một kiểu rò rỉ cố định.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Hành vi không xác định (UB) nghĩa là gì?

- Chương trình chắc chắn crash ngay tại dòng gây lỗi
- Trình biên dịch luôn báo lỗi và không cho biên dịch
- Chuẩn C++ không quy định kết quả: có thể chạy "đúng", sai âm thầm hoặc crash, tùy trình biên dịch và máy
- Chỉ xảy ra với con trỏ, còn phép tính số nguyên thì không bao giờ

<p class="giai-thich" markdown>Nguy hiểm vì nó có thể "chạy đúng" lúc thử rồi sập khi chạy thật. UB cũng có ở số nguyên, ví dụ tràn số nguyên có dấu.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Cách phòng tránh rò rỉ tốt nhất trong C++ hiện đại là gì?

- Dùng RAII, smart pointer và container chuẩn thay vì `new`/`delete` trần
- Nhớ `delete` cẩn thận ở mọi nhánh, kể cả khi có `return` sớm
- Dùng `malloc`/`free` thay cho `new`/`delete` vì chúng an toàn hơn
- Chuyển mọi biến sang biến toàn cục để khỏi phải giải phóng

<p class="giai-thich" markdown>Để hàm hủy lo việc trả đồ thay vì trông chờ vào trí nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 7.** Valgrind (memcheck) khác ASan ở điểm nào?

- Valgrind phải biên dịch lại bằng cờ riêng, còn ASan chạy trên chương trình có sẵn
- Valgrind kiểm tra chương trình đã biên dịch thường, không cần biên dịch lại, nhưng chậm hơn; ASan chèn kiểm tra lúc biên dịch
- Hai công cụ chỉ khác tên; cách làm và tốc độ giống hệt nhau
- ASan không bao giờ báo được rò rỉ, chỉ Valgrind mới báo được

<p class="giai-thich" markdown>ASan thường chỉ làm chương trình chậm khoảng 2 lần, còn Valgrind memcheck hay chậm 20–50 lần, nhưng Valgrind không cần biên dịch lại. ASan trên Linux có kèm LeakSanitizer nên cũng báo rò rỉ.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Bốn lỗi bộ nhớ hay gặp: rò rỉ, con trỏ treo, giải phóng hai lần, ghi vượt mảng.
2. `new` đi với `delete`, `new[]` đi với `delete[]`; trộn lẫn là UB.
3. UB không phải lúc nào cũng sập: nó có thể "chạy đúng" rồi hỏng ở máy khác.
4. Tìm lỗi bằng AddressSanitizer (`-fsanitize=address`) hoặc Valgrind.
5. Tránh bằng RAII, smart pointer, container chuẩn, và bật `-Wall -Wextra`.
