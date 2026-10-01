# Bài 5 — Memory leak, dangling, UB và công cụ phát hiện

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Phân biệt được rò rỉ bộ nhớ, con trỏ treo, giải phóng hai lần và hành vi không xác định.
    - Biết dùng AddressSanitizer và Valgrind để tìm lỗi bộ nhớ.
    - Biết cách phòng tránh các lỗi này trong C++ hiện đại.

## 🧠 Câu chuyện mở đầu

Quay lại **kho đồ của trường** ở [Bài 1](01-stack-heap-con-tro.md).

**Rò rỉ (leak)**: bạn mượn đồ mà quên trả. Kho đầy dần, đến lúc không còn chỗ cho ai.

**Con trỏ treo (dangling pointer)**: bạn cầm tờ giấy ghi "đồ ở phòng 12". Nhưng phòng 12 đã bị dỡ. Đến đó, bạn thấy gì cũng có thể xảy ra.

**Giải phóng hai lần (double free)**: bạn trả cùng một món đồ hai lần. Sổ sách rối tung.

**Hành vi không xác định (UB)**: luật chơi đã bị phá. Nên mọi chuyện đều có thể xảy ra. Lúc thì "chạy đúng". Lúc thì sập. Lúc thì sai âm thầm. Đổi máy là đổi kết quả.

## 📖 Giải thích

Có bốn loại lỗi bộ nhớ hay gặp. Rò rỉ là lỗi quản lý bộ nhớ, nhưng chương trình vẫn chạy hợp lệ, chỉ tốn bộ nhớ. Ba loại còn lại là hành vi không xác định (UB).

- **Memory leak (rò rỉ bộ nhớ)**: xin vùng nhớ rồi không trả. Không phải UB, chỉ là phí bộ nhớ.
- **Dangling pointer / use-after-free (con trỏ treo / dùng sau khi trả)**: con trỏ vẫn giữ địa chỉ của vùng nhớ đã được trả, mà bạn vẫn dùng nó.
- **Double free (giải phóng hai lần)**: trả một vùng nhớ hai lần. Bộ cấp phát bộ nhớ bị rối.
- **Buffer overflow (ghi vượt biên mảng)**: đọc hoặc ghi ra ngoài vùng nhớ của mảng.

**UB (undefined behavior, hành vi không xác định)** nghĩa là chuẩn C++ không quy định chương trình sẽ làm gì. Nó có thể chạy "đúng", có thể sai âm thầm, có thể sập. Kết quả đổi theo trình biên dịch và theo máy.

Một số ví dụ UB khác: tràn số nguyên có dấu, data race (hai luồng cùng truy cập một biến, ít nhất một luồng ghi, không có đồng bộ), giải tham chiếu `nullptr`.

Quy tắc ghép đôi:

- `new` đi với `delete`.
- `new[]` đi với `delete[]`.
- Trộn lẫn là UB.

**Công cụ tìm lỗi**:

- **AddressSanitizer (ASan)**: bạn biên dịch với cờ `-fsanitize=address`. Chương trình tự báo khi truy cập bộ nhớ sai. Trên Linux, nó còn báo rò rỉ lúc chương trình kết thúc. ASan chạy nhanh hơn Valgrind khoảng vài lần.
- **Valgrind (memcheck)**: bạn không cần biên dịch lại. Nó chạy chương trình trong một "máy ảo" để kiểm tra từng lần truy cập bộ nhớ. Vì vậy nó chậm hơn nhiều.

**Cách phòng tránh**:

- Dùng RAII và smart pointer (xem [Bài 2](02-raii-smart-pointer.md)).
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

    Dangling: con trỏ vẫn còn nhưng vùng nhớ đã được trả.

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

<div class="quiz" data-bai="05" markdown>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 1.** Rò rỉ bộ nhớ (memory leak) là gì?

- Xin vùng nhớ nhưng không bao giờ trả lại, nên bộ nhớ bị chiếm dần
- Dùng vùng nhớ đã trả
- Ghi vượt mảng
- Trả vùng nhớ hai lần

<p class="giai-thich" markdown>Mượn đồ mà quên trả. Các phương án còn lại là lỗi khác.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 2.** Con trỏ treo (dangling pointer) là gì?

- Con trỏ bằng nullptr
- Con trỏ vẫn giữ địa chỉ của vùng nhớ đã được trả
- Con trỏ trỏ lên stack
- Con trỏ `const`

<p class="giai-thich" markdown>Tờ giấy ghi số phòng đã bị dỡ: dùng nó là UB.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 3.** Công cụ nào phát hiện lỗi bộ nhớ khi biên dịch kèm cờ `-fsanitize=address`?

- gdb
- AddressSanitizer
- CMake
- git

<p class="giai-thich" markdown>ASan chèn các kiểm tra vào chương trình lúc biên dịch và báo lỗi lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 4.** Vì sao mảng cấp phát bằng `new int[10]` phải giải phóng bằng `delete[]`?

- `delete[]` gọi hàm hủy cho mọi phần tử và trả đúng khối nhớ; dùng `delete` thường là hành vi không xác định
- Chỉ là quy ước, dùng cái nào cũng được
- `delete[]` nhanh hơn
- Để tránh lỗi biên dịch

<p class="giai-thich" markdown>Với `new[]`, thường (nhất là khi phần tử có hàm hủy) chương trình ghi thêm thông tin phụ để `delete[]` biết cần hủy bao nhiêu phần tử và trả đúng khối nhớ. Dùng `delete` thường thì không có gì đảm bảo, đó là hành vi không xác định.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Hành vi không xác định (UB) nghĩa là gì?

- Chương trình luôn crash
- Chuẩn C++ không quy định kết quả: có thể chạy "đúng", sai âm thầm hoặc crash, và đổi theo trình biên dịch/máy
- Luôn có thông báo lỗi
- Chỉ xảy ra trên Windows

<p class="giai-thich" markdown>Nguy hiểm vì nó có thể "chạy đúng" lúc thử rồi sập khi chạy thật.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Cách phòng tránh rò rỉ tốt nhất trong C++ hiện đại là gì?

- Nhớ `delete` cẩn thận
- Dùng RAII, smart pointer và container chuẩn thay vì `new`/`delete` trần
- Tắt cảnh báo của trình biên dịch
- Chỉ dùng biến toàn cục

<p class="giai-thich" markdown>Để hàm hủy lo việc trả đồ thay vì trông chờ vào trí nhớ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Valgrind (memcheck) khác ASan ở điểm nào?

- Valgrind chạy chương trình biên dịch bình thường dưới máy ảo kiểm tra, không cần biên dịch lại nhưng chậm hơn nhiều; ASan chèn kiểm tra lúc biên dịch nên nhanh hơn
- Giống hệt nhau
- Valgrind chỉ dùng cho Java
- ASan không bao giờ tìm được rò rỉ

<p class="giai-thich" markdown>ASan trên Linux có kèm LeakSanitizer nên cũng báo rò rỉ; Valgrind đổi lại cho khả năng kiểm tra không cần sửa cách biên dịch.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Bốn lỗi bộ nhớ hay gặp: rò rỉ, con trỏ treo, giải phóng hai lần, ghi vượt mảng.
2. `new` đi với `delete`, `new[]` đi với `delete[]`; trộn lẫn là UB.
3. UB không phải lúc nào cũng sập: nó có thể "chạy đúng" rồi hỏng ở máy khác.
4. Tìm lỗi bằng AddressSanitizer (`-fsanitize=address`) hoặc Valgrind.
5. Tránh bằng RAII, smart pointer, container chuẩn, và bật `-Wall -Wextra`.
