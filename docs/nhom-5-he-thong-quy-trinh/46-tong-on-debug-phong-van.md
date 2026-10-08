# Bài 46 — Tổng ôn: quy trình gỡ lỗi và kể chuyện dự án

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Trả lời được câu hỏi phỏng vấn "có bug mà không biết ở đâu thì làm sao" bằng một **quy trình**, không chỉ liệt kê "đặt log và gdb".
    - Chọn đúng công cụ theo triệu chứng: sập, treo, chết muộn do ghi đè bộ nhớ, chạy chậm, chỉ lỗi ở `-O2`.
    - Kể một lần gỡ lỗi theo khuôn STAR, và tự kiểm tra lại cả khóa bằng đề trắc nghiệm trộn.

**Bạn cần biết trước:** Bài 38 đến 42 (build, gdb, sanitizer, strace/perf), cùng [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md) (hành vi không xác định) và [Bài 26](../nhom-3-da-luong/26-deadlock.md) (deadlock). Bài này **không dạy công cụ mới**: nó xâu các công cụ thành một quy trình.

## 🧠 Câu chuyện mở đầu

Nhà bạn mất điện nửa căn. Người thợ giỏi không lao vào tháo hết dây trong tường. Anh ta **nhìn đèn nào tắt** (triệu chứng), ngó **cầu dao** (chỗ rẻ nhất để kiểm), đoán "chắc ổ cắm phòng bếp chập", rút thử ổ đó (kiểm chứng) rồi mới sửa. Sửa xong anh bật lại để chắc là đã hết.

Người thợ dở thì thay cầu dao, thay bóng đèn, thay luôn dây, và không biết cái nào đã chữa được bệnh.

Gỡ lỗi là nghề của người thợ giỏi: **quan sát, đặt giả thuyết, kiểm chứng, sửa, bật lại**. Công cụ chỉ là dụng cụ trong tay.

## 📖 Giải thích

### 1. Quy trình năm bước

1. **Xác định loại lỗi** qua cách chương trình chết (bảng mục 2).
2. **Tái hiện và thu nhỏ**: tìm đầu vào ngắn nhất vẫn gây lỗi; `git bisect` ([Bài 43](43-git.md)) để tìm commit đầu tiên gây lỗi. Không tái hiện được (lỗi ở nơi khác) thì thu **core dump** ([Bài 40](40-gdb-nang-cao-core-dump.md)).
3. **Đặt giả thuyết bằng một câu** ("`p` null vì danh sách rỗng") rồi kiểm chứng bằng breakpoint có điều kiện, `watch` hoặc sanitizer, không sửa mò.
4. **Sửa nguyên nhân gốc**, không sửa chỗ lộ ra: thêm `if (p)` chỉ giấu triệu chứng.
5. **Viết test tái hiện lỗi** và bật sanitizer trong kiểm thử để lỗi không quay lại.

### 2. Triệu chứng chọn công cụ

| Triệu chứng | Nghi ngờ | Công cụ đầu tiên | Bài |
|---|---|---|---|
| `SIGSEGV` (mã 139) | `nullptr`, dangling, tràn | gdb `bt`, hoặc ASan | 40, 41 |
| `SIGABRT` (mã 134) | `assert`, ngoại lệ không bắt, `free` hỏng | gdb `bt` | 38, 40 |
| Chết **muộn**, chỗ lạ (`corrupted`, `double free`) | Ghi tràn đè bộ nhớ kề | ASan; không build lại được thì `watch -l` | 40, 41 |
| Treo, không in gì | Deadlock, vòng lặp vô hạn | `gdb -p`/`thread apply all bt`, `strace -f`, TSan | 40, 41, 42 |
| Lúc được lúc không | Data race, UB | ThreadSanitizer, UBSan | 41 |
| Chỉ lỗi ở `-O2` | UB | Sanitizer (đừng đọc tay) | 15, 41 |
| Sai kết quả, không sập | Lỗi logic | Breakpoint điều kiện, `watch`, `display` | 39 |
| Chậm | Chỗ nóng | `time`, gprof, perf | 42 |
| Lỗi mở tệp, kết nối | Môi trường | `strace`, `ss`, `curl -v` | 42, 44 |
| Hỏng sau khi đổi header | `.o` cũ trộn mới | `make clean && make` | 38 |

### 3. Ba điều khiến người ta bị chê "tầm thường"

- **Chỉ kể công cụ, không kể trình tự.** Người phỏng vấn muốn nghe bạn chọn công cụ *vì sao*.
- **Tin chỗ chết là chỗ lỗi.** Với ghi tràn hay use-after-free, chỗ chết chỉ là nạn nhân: dùng ASan, hoặc `watch` vùng bị hỏng để thấy thủ phạm.
- **Chỉ có log.** Log đổi thời điểm chạy và có thể làm lỗi dời chỗ hay biến mất (Bài 40); log cũng có thể bị mất khi chết (`cout` qua ống chưa kịp xả).

### 4. Kể chuyện theo khuôn STAR

**S**ituation (bối cảnh) · **T**ask (việc bạn nhận) · **A**ction (bạn làm gì, theo trình tự) · **R**esult (kết quả đo được). Hầu hết người học dồn hết vào A và quên R. Phần A của câu chuyện gỡ lỗi chính là quy trình năm bước ở mục 1.

## 💻 Ví dụ code

### Ví dụ: một đoạn trả lời mẫu cho "app chết, bạn làm gì?"

```text
Bối cảnh:  dịch vụ xử lý ảnh thỉnh thoảng thoát với mã 139, vài ngày một lần.
Nhiệm vụ:  tìm nguyên nhân, không có cách tái hiện sẵn.

Hành động:
 1. Bật core dump trên máy thử, thu được một core; mở bằng `gdb ./app core`,
    `bt` cho thấy chết trong hàm giải phóng bộ đệm, không phải chỗ dùng nó.
 2. Chết ở chỗ trả bộ nhớ gợi ý ghi tràn đã làm hỏng thông tin của heap,
    nên mình build lại bản kiểm thử với -fsanitize=address,undefined -g.
 3. Chạy lại bộ ảnh mẫu: ASan chỉ đúng dòng ghi vượt cỡ bộ đệm và dòng cấp phát nó.
 4. Nguyên nhân gốc: kích thước đệm tính theo số điểm ảnh, ghi theo số byte.
 5. Sửa thành std::vector<uint8_t>, thêm test ảnh biên, bật ASan trong CI.

Kết quả:   hết sập; sanitizer trong CI bắt thêm một lỗi cùng loại ở module khác.
```

Đoạn này không có công cụ nào lạ. Cái làm nó thuyết phục là **thứ tự và lý do**: có core, nghi tràn, sanitizer xác nhận, sửa gốc, ngăn quay lại. Hãy thay chi tiết bằng chuyện thật của bạn (không nêu tên công ty hay khách hàng).

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Có bug mà không biết ở đâu thì bạn debug thế nào?"
    Xác định loại lỗi qua cách chương trình chết, tái hiện và thu nhỏ đầu vào (`git bisect` nếu mới xuất hiện), đặt giả thuyết một câu rồi kiểm chứng bằng công cụ hợp với loại lỗi (gdb cho sập và logic, sanitizer cho bộ nhớ và UB, TSan cho race, `thread apply all bt` cho treo), sửa nguyên nhân gốc rồi viết test chặn quay lại. Log là công cụ bổ sung, không phải bước đầu.

??? question "Chương trình chết ở chỗ này nhưng lỗi ở chỗ khác, bạn làm gì?"
    Nghi hỏng bộ nhớ (ghi tràn, dùng sau khi trả). Biên dịch lại với ASan để nó chặn ngay lúc ghi sai và chỉ ra dòng ghi lẫn dòng cấp phát. Nếu không build lại được, đặt `watch -l` trên vùng bị hỏng để gdb dừng đúng lệnh ghi đè rồi `bt`.

??? question "Chương trình treo, bạn làm gì?"
    Attach `gdb -p PID`, chạy `thread apply all bt` để xem từng luồng kẹt ở đâu; hai luồng kẹt ở `lock` thì kiểm chủ sở hữu mutex để xác nhận deadlock. `strace -f` thấy `futex` chờ. Dùng ThreadSanitizer để bắt đảo thứ tự khóa ngay cả khi lần chạy chưa treo; sửa bằng `std::scoped_lock` hoặc thứ tự khóa cố định.

??? question "Lỗi chỉ xuất hiện ở bản release (`-O2`), bản debug thì không. Bạn nghĩ gì?"
    Rất có thể là hành vi không xác định: trình biên dịch được giả sử UB không xảy ra nên tối ưu khác đi. Chạy bản có `-fsanitize=address,undefined`, bật cảnh báo (`-Wall -Wextra` ở `-O2`), kiểm biến chưa khởi tạo. Cũng có thể là data race lộ ra vì thời điểm đổi: dùng TSan.

??? question "Khi nào log là đủ, khi nào cần gdb hay sanitizer?"
    Log đủ để biết luồng đi của hệ thống chạy lâu trên môi trường không attach được. Cần gdb khi muốn xem trạng thái tại một thời điểm hay bắt thay đổi của một vùng nhớ. Cần sanitizer khi lỗi là hỏng bộ nhớ, UB hay race, vì chúng chỉ ra nguyên nhân thay vì triệu chứng.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Sửa triệu chứng"
    Thêm kiểm tra `nullptr` ngay chỗ chết rồi coi như xong. Lỗi thật (vì sao con trỏ rỗng) vẫn còn và sẽ nổ ở chỗ khác.

!!! warning "Lỗi 2: Đổi nhiều thứ một lúc"
    Đổi ba chỗ rồi lỗi biến mất thì bạn không biết chỗ nào đã chữa. Mỗi lần một giả thuyết, một thay đổi.

!!! warning "Lỗi 3: Không chặn lỗi quay lại"
    Không có test hay sanitizer trong CI, lỗi cùng loại sẽ trở lại. Bước 5 là phần người phỏng vấn nhớ nhất.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="46" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Chương trình thỉnh thoảng báo `double free or corruption` ở một hàm giải phóng bộ nhớ không liên quan tới dữ liệu đang xử lý. Bước hợp lý đầu tiên là gì?

- Thêm `if (p != nullptr)` trước mỗi `delete` để tránh trả hai lần
- Biên dịch lại với AddressSanitizer để bắt đúng lúc bộ nhớ bị ghi sai
- Đặt thêm log thật nhiều quanh hàm giải phóng
- Chuyển sang `-O2` để heap được dùng hiệu quả hơn

<p class="giai-thich" markdown>Báo lỗi ở chỗ trả bộ nhớ cho thấy thông tin của heap đã bị hỏng từ trước, thường do ghi tràn ở nơi khác. AddressSanitizer chặn ngay lúc ghi sai và chỉ ra cả dòng cấp phát. Kiểm `nullptr` không đụng vào nguyên nhân (con trỏ không hề rỗng, bộ nhớ kề nó bị đè). Log có thể làm lỗi dời chỗ mà không chỉ ra thủ phạm. Đổi mức tối ưu không sửa gì và còn che lỗi.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Dịch vụ đứng yên, CPU gần 0, không in gì. Bạn attach `gdb -p` và `thread apply all bt` thấy hai luồng cùng dừng ở `lock` của hai mutex khác nhau. Kết luận hợp lý nhất?

- Chương trình đang chờ đầu vào từ mạng
- Hai luồng đang chạy bình thường, chỉ chậm
- Có data race trên biến đếm
- Deadlock do hai luồng khóa hai mutex theo thứ tự ngược nhau

<p class="giai-thich" markdown>Hai luồng cùng kẹt ở `lock` và CPU rảnh là dấu hiệu chờ nhau: mỗi luồng giữ một mutex và xin cái còn lại. Chờ mạng sẽ dừng ở hàm đọc socket, không ở `lock`. Luồng đang chạy chậm thì tốn CPU. Data race không làm luồng kẹt ở `lock`; nó cho kết quả sai, không cho treo.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Hàm trả về 0 thay vì giá trị lớn nhất của dãy toàn số âm. Bạn đặt `watch` lên biến `lon` và chạy hết hàm, gdb không dừng lần nào. Điều đó cho biết gì?

- `lon` không bao giờ bị gán lại, nên điều kiện cập nhật không bao giờ đúng
- gdb hỏng, vì watchpoint phải dừng ít nhất một lần
- `lon` đã bị trình biên dịch xóa mất
- Chương trình chưa chạy tới hàm đó

<p class="giai-thich" markdown>Watchpoint chỉ dừng khi giá trị đổi. Không lần nào dừng nghĩa là mọi so sánh `sv.diem > lon` đều sai với dữ liệu âm, do khởi tạo `lon = 0`: đó chính là bằng chứng cho giả thuyết. Ở `-O0` biến vẫn tồn tại, và gdb báo khi chương trình rời phạm vi của biến, nên chương trình vẫn chạy qua hàm.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Một lỗi biến mất khi bạn thêm `std::cerr << ...` vào, quay lại khi xóa dòng đó. Giả thuyết đáng tin nhất?

- Trình biên dịch có lỗi với dòng `cerr`
- `cerr` sửa bộ nhớ bị hỏng
- Lỗi phụ thuộc thời điểm hay bố cục bộ nhớ (UB, race), nên log làm đổi chúng
- Dòng log làm chương trình chạy nhanh hơn nên hết lỗi

<p class="giai-thich" markdown>Thêm log đổi thời điểm các luồng và dịch bố cục stack hay heap, nên UB hoặc data race có thể ẩn đi mà không biến mất thật. Đó là lý do chạy sanitizer thay vì tin vào "hết lỗi rồi". Lỗi trình biên dịch là khả năng cuối cùng, không phải giả thuyết đáng tin nhất. `cerr` không sửa bộ nhớ. Chạy nhanh hơn không phải điều log làm.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đọc đầu ra sau của `gdb`. Chuyện gì đã xảy ra?

```text
Program received signal SIGSEGV, Segmentation fault.
0x... in tongDanh (p=0x0) at sap.cpp:19
19	        tong += p->giaTri;
```

- Chương trình hết bộ nhớ khi cấp phát nút mới
- Con trỏ `p` là rỗng và dòng 19 đã giải tham chiếu nó
- Dòng 19 chia cho 0
- `tong` bị tràn số nguyên

<p class="giai-thich" markdown>`SIGSEGV` kèm `p=0x0` và `p->giaTri` ở dòng dừng cho thấy chương trình đọc qua con trỏ rỗng. Hết bộ nhớ sẽ ném `std::bad_alloc` hay bị hệ điều hành kill, không phải `SIGSEGV` ở một phép đọc. Chia cho 0 cho `SIGFPE`. Tràn số nguyên có dấu là UB nhưng không phát ra tín hiệu này.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Bạn muốn biết chương trình đang chờ gì khi nó đứng yên mà không sửa mã. Lệnh nào hợp nhất để xem nó đang gọi hệ thống nào?

- `make clean`
- `objdump -d`
- `ldd ./app`
- `strace -f ./app`

<p class="giai-thich" markdown>`strace -f` in từng lời gọi hệ thống của mọi luồng; dòng cuối kẹt ở `futex(... FUTEX_WAIT ...)` hay `read(...)` cho biết nó đang chờ khóa hay chờ dữ liệu. `make clean` xóa sản phẩm build. `objdump -d` chỉ đọc mã máy tĩnh. `ldd` liệt kê thư viện cần, không nói gì về trạng thái lúc chạy.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Trong khuôn STAR, người phỏng vấn thường thấy bạn thiếu phần nào nhất khi kể một lần gỡ lỗi?

- Result: kết quả cụ thể, và cách chặn lỗi quay lại
- Situation: bối cảnh
- Task: việc bạn nhận
- Action: bạn làm gì

<p class="giai-thich" markdown>Người học thường kể rất kỹ Action rồi dừng, trong khi Result (đo được, kèm biện pháp phòng ngừa như test hay sanitizer trong CI) là phần cho thấy lỗi đã thật sự được giải quyết. Ba phần còn lại thường được kể đủ vì chúng là chuyện xảy ra, còn Result đòi bạn phải có số liệu hay bằng chứng.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Gỡ lỗi là quy trình năm bước: xác định loại lỗi từ cách chết, tái hiện và thu nhỏ (`git bisect`, core dump), đặt giả thuyết một câu rồi kiểm chứng, sửa nguyên nhân gốc, và viết test cùng bật sanitizer để lỗi không quay lại.
2. Chọn công cụ theo triệu chứng: sập thì `bt` trong gdb, chết muộn do ghi đè thì ASan hoặc `watch -l`, treo thì `gdb -p`, `thread apply all bt`, `strace -f` và TSan, chậm thì đo bằng bản `-O2` với gprof hay perf.
3. Chỗ chết không phải lúc nào cũng là chỗ lỗi: ghi tràn và dùng sau khi trả làm hỏng bộ nhớ kề nên chương trình chết muộn ở chỗ khác; thêm `if (p)` hay thêm log chỉ che triệu chứng.
4. Lỗi chỉ ở `-O2`, hoặc biến mất khi thêm log, thường là UB hay data race phụ thuộc bố cục và thời điểm: chạy sanitizer thay vì đọc tay.
5. Khi phỏng vấn, kể theo trình tự và lý do chọn công cụ, dùng khuôn STAR có Result đo được, và không chỉ trả lời "đặt log và gdb".
