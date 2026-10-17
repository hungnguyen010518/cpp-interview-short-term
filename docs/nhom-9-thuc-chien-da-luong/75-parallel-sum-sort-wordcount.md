# Bài 75 — Thực chiến: chia việc song song — tổng, merge sort, đếm từ

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Trả lời mọi đề "chia việc cho nhiều luồng" bằng bốn bước: **chia** dữ liệu thành khúc, mỗi luồng **làm riêng** trên khúc của mình, **gộp** kết quả, **kiểm** với bản tuần tự. Biết khi nào KHÔNG nên song song.
    - Giải ba đề kinh điển: tổng một mảng lớn (so với `std::accumulate`), merge sort song song có giới hạn độ sâu, đếm từ kiểu map-reduce; mỗi đề có bản SAI chạy thật (data race, hàng chục nghìn luồng, khóa chung làm chậm).
    - Nói được ngưỡng đáng song song bằng số đo thật (tỉ lệ, đổi theo máy), vì sao 8 luồng không nhanh gấp 8 (Amdahl, băng thông bộ nhớ), và phân biệt chuẩn C++ bảo đảm gì với g++ 11 trên máy này cho kết quả gì.

**Bạn cần biết trước:** [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::ref`, `steady_clock`, `hardware_concurrency`), [Bài 25](../nhom-3-da-luong/25-data-race-mutex.md) (data race, TSan, `lock_guard`), [Bài 29](../nhom-3-da-luong/29-async-future.md) (`std::async`, `future`, `get`), [Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md) (Amdahl, số luồng, đo thời gian), [Bài 20](../nhom-2-stl-thuat-toan/20-algorithm-lambda.md) (`accumulate`, `sort`, lambda), [Bài 23](../nhom-2-stl-thuat-toan/23-thuat-toan-hay-hoi.md) (ý tưởng merge sort), [Bài 18](../nhom-2-stl-thuat-toan/18-map-set-unordered.md) (`unordered_map`, duyệt `[khoa, giaTri]`).

## 🧠 Cảnh phỏng vấn

Người phỏng vấn viết lên bảng: "Có một mảng 100 triệu số. Tính tổng bằng nhiều luồng. Tiếp theo: sắp xếp nó. Cuối cùng: đếm từ trong một đống văn bản." Rồi hỏi luôn: "Bạn chắc nó nhanh hơn bản một luồng chứ?"

Quay lại **nhà bếp**. Bếp trưởng có một đống nguyên liệu và N đầu bếp. Cách làm đúng: **chia khay**, mỗi đầu bếp một khay riêng, nấu xong đặt kết quả lên mâm riêng; cuối cùng bếp trưởng **gộp các mâm**. Không ai phải xin thẻ vào thớt chung, vì không ai đụng khay của ai.

!!! info "Chỗ nào ví von khay nguyên liệu không còn đúng?"
    Khay của mỗi người là riêng, nhưng **tủ lạnh thì chung**: mọi đầu bếp lấy nguyên liệu qua cùng một cửa tủ. Việc đơn giản như cộng số bị nghẽn ở cửa tủ (băng thông bộ nhớ), thêm đầu bếp cũng không nhanh thêm bao nhiêu. Và thuê đầu bếp mới mất thời gian: nguyên liệu ít thì bếp trưởng tự làm còn nhanh hơn.

## 📖 Giải thích

### 1. Bốn bước và tiêu chí chọn

| Bước | Việc | Điều kiện đúng |
|---|---|---|
| Chia | Cắt dữ liệu thành khúc liền nhau không chồng lấn | Biên khúc tính bằng `n * k / soKhuc` để không rơi phần dư |
| Làm riêng | Mỗi luồng ghi kết quả vào **chỗ riêng** (giá trị trả về, bảng cục bộ) | Không ghi chung, nên không cần khóa |
| Gộp | Một luồng cộng/trộn các kết quả riêng | Phép gộp đúng dù thứ tự khúc nào |
| Kiểm | So với bản tuần tự trên cùng dữ liệu | Bản tuần tự là "đáp án" |

Bốn bước này đúng cho cả ba đề. Còn có đáng làm không, xem bảng:

| Tình huống | Chọn |
|---|---|
| Việc tuần tự chỉ vài chục micro-giây đến vài trăm micro-giây | **Tuần tự**: khởi động một luồng đã mất cỡ vài chục micro-giây |
| Việc nặng CPU (sắp xếp, tính toán), vài mili-giây trở lên | Song song, số khúc cỡ `hardware_concurrency()` |
| Việc chỉ duyệt bộ nhớ (cộng mảng) | Song song cho n rất lớn, nhưng chỉ kỳ vọng 2 đến 4 lần, không gấp 8 |
| Các khúc cần dữ liệu của nhau | Đừng chia kiểu này: nghĩ lại cách chia, hoặc dùng khóa ([Bài 25](../nhom-3-da-luong/25-data-race-mutex.md)) |
| Bước gộp nặng ngang bước làm | Phần gộp là phần tuần tự của Amdahl: gộp song song hoặc chia khác |

**Amdahl** ([Bài 30](../nhom-3-da-luong/30-thread-pool-hieu-nang.md)): tăng tốc tối đa `1 / ((1 - p) + p / n)`. Ở bài này phần tuần tự gồm khởi động luồng và bước gộp. Ngoài ra còn một giới hạn riêng mà công thức không tính: bộ nhớ chỉ có một cửa (băng thông). Ví dụ `p = 0,8`, 8 lõi: `1 / (0,2 + 0,1)` ra khoảng 3,3 lần, chưa bao giờ 8.

### 2. Chuẩn bảo đảm gì, máy này cho gì

| Điều | Chuẩn C++ nói | g++ 11.4, máy 4 lõi 8 luồng phần cứng |
|---|---|---|
| `async(launch::async, f)` | Chạy như thể trên một luồng mới; nếu không tạo nổi luồng thì ném `std::system_error` | Tạo luồng hệ điều hành thật; cạn tài nguyên thì ném (đo ở Đề 2) |
| Số khúc nên chọn | `hardware_concurrency()` chỉ là gợi ý, có thể trả 0 | Trả 8 (4 lõi, mỗi lõi 2 luồng) |
| `std::accumulate` | Cộng **tuần tự, từ trái sang phải** | Một luồng |
| `std::reduce` (C++17, `<numeric>`) | Được phép cộng **theo thứ tự bất kỳ** (cần phép gộp kết hợp và giao hoán) | Không có `par` thì vẫn một luồng |
| `std::execution::par` (C++17, `<execution>`) | **Cho phép** song song, không bắt buộc | Biên dịch được, không cần `-ltbb`, nhưng mình đếm id luồng thì chỉ thấy **một luồng** |
| Tăng tốc | Không hứa gì | Đo ở từng đề: khoảng 2 đến 4,5 lần, tùy việc |

Vì vậy bài này tự chia khúc bằng `async`: kiểm soát được, và biết chắc nó chạy nhiều luồng.

### 3. Ba đề

**Đề 1: tổng song song.** Cho `std::vector<int>` n phần tử (mỗi số từ 0 đến 99999, n tới hàng chục triệu). Viết `long long tongSongSong(const std::vector<int>& v, int soKhuc)` trả **đúng** bằng `std::accumulate`. Ràng buộc: không mutex hay atomic chung; n không nhất thiết chia hết cho `soKhuc`; n nhỏ thì phải biết **không** song song.

??? tip "Gợi ý 1"
    Mỗi luồng cần ghi kết quả ở đâu để không đụng ai? Đừng ghi vào một biến chung: để mỗi việc **trả về** tổng của khúc mình qua `future`, `main` cộng lại.

??? tip "Gợi ý 2"
    Khúc thứ `k` (đếm từ 0) chạy từ `n * k / soKhuc` đến `n * (k + 1) / soKhuc` (không tính điểm cuối). Công thức này phủ kín mảng kể cả khi n không chia hết.

??? tip "Gợi ý 3"
    Hai bẫy: giá trị đầu của `accumulate` phải là `0LL` (tổng vượt `int`), và dưới một ngưỡng n thì gọi thẳng `accumulate`. Rồi kiểm `==` với bản tuần tự.

**Đề 2: merge sort song song.** Cho `std::vector<int>`, viết `void sapXep(std::vector<int>& v, std::size_t dau, std::size_t cuoi, int sau)` sắp đoạn `[dau, cuoi)` tăng dần, kết quả bằng `std::sort`. Ràng buộc: sinh tối đa khoảng `2^sau` luồng chứ không phải hàng nghìn; đoạn ngắn thì khỏi chia; đoạn rỗng hoặc một phần tử vẫn đúng.

??? tip "Gợi ý 1"
    Hai nửa của dãy độc lập nhau: nửa trái giao cho `async`, **luồng hiện tại tự làm nửa phải** (đỡ một luồng ngồi chờ).

??? tip "Gợi ý 2"
    Chỉ trộn **sau khi** nửa trái xong, tức sau `get()`. Hai nửa đã sắp thì ghép bằng `std::inplace_merge` (giải thích ngay dưới).

??? tip "Gợi ý 3"
    Tham số `sau` đếm số tầng còn được sinh luồng, giảm 1 mỗi lần chia; về 0 hoặc đoạn ngắn hơn một ngưỡng thì sắp tuần tự bằng `std::sort`.

`std::inplace_merge(dauA, giua, cuoiB)` (trong `<algorithm>`): hai đoạn liền nhau `[dauA, giua)` và `[giua, cuoiB)` **đã sắp** được trộn thành một đoạn sắp. Nó **ổn định** (hai phần tử bằng nhau giữ thứ tự cũ). Chuẩn: đúng N − 1 phép so sánh nếu xin được bộ nhớ phụ, không thì O(N log N); trộn nhanh là O(N) với O(N) bộ nhớ phụ, như [Bài 23](../nhom-2-stl-thuat-toan/23-thuat-toan-hay-hoi.md).

**Đề 3: đếm từ kiểu map-reduce.** Cho `std::vector<std::string>` các dòng, mỗi dòng gồm các từ cách nhau một dấu cách. Trả bảng `từ → số lần`, rồi in tổng số từ, số từ khác nhau và 3 từ phổ biến nhất (đồng hạng thì theo thứ tự chữ). Ràng buộc: **không khóa chung**; bảng song song phải bằng bảng tuần tự; đầu ra tất định.

??? tip "Gợi ý 1"
    "Map" = mỗi luồng đếm các dòng của khúc mình vào **một bảng riêng** của luồng đó. "Reduce" = cộng các bảng riêng lại.

??? tip "Gợi ý 2"
    Hàm của mỗi luồng **trả bảng về theo giá trị** qua `future` (bảng được chuyển, không sao chép). Luồng `main` là nơi duy nhất đụng bảng chung.

??? tip "Gợi ý 3"
    Duyệt `unordered_map` cho thứ tự không xác định, nên muốn in tất định thì chép ra `vector` rồi `sort` theo (số lần giảm, chữ tăng).

Một món mới: `std::istringstream` (trong `<sstream>`) biến một `std::string` thành "dòng chảy" đọc được như `std::cin`. `in >> tu` bỏ khoảng trắng, đọc một từ vào `tu`, và trả về `false` khi hết chuỗi, nên `while (in >> tu)` duyệt từng từ.

## 💻 Ví dụ code

Dữ liệu thử đều do một **máy sinh số giả ngẫu nhiên** tự viết: `x = x * a + c` rồi lấy vài bit. Cùng giá trị khởi đầu `x` thì mọi máy ra cùng dãy, và `unsigned` tràn thì quay vòng (hợp lệ), nên đầu ra tất định. Hậu tố `u` trong `12345u` đánh dấu số `unsigned`. `x >> 16` dịch `x` sang phải 16 bit (bỏ 16 bit thấp, ngược với `<<` ở [Bài 15](../nhom-1-nen-tang-bo-nho/15-hanh-vi-khong-xac-dinh-cong-cu.md)), `% 100000` lấy phần dư khi chia cho 100000, nên kết quả nằm trong 0 đến 99999.

Vài món cú pháp nhỏ trong code: `điều_kiện ? a : b` chọn `a` nếu đúng, `b` nếu sai; `std::to_string(7)` đổi số thành chuỗi `"7"`; `for (int k : {1, 2, 4, 8})` duyệt một danh sách viết thẳng trong ngoặc nhọn; `std::is_sorted(đầu, cuối)` trả `1` nếu đoạn đã tăng dần; `std::vector<T> xep(a.begin(), a.end())` dựng vector bằng cách chép mọi phần tử của đoạn `[a.begin(), a.end())`; `==` giữa hai vector hay hai bảng so từng phần tử hay từng cặp.

### Đề 1: tổng song song

```cpp
#include <future>
#include <iostream>
#include <numeric>
#include <vector>

// Tổng v[dau], ..., v[cuoi - 1] bằng bộ cộng long long.
long long tongKhuc(const std::vector<int>& v, std::size_t dau, std::size_t cuoi) {
    return std::accumulate(v.begin() + dau, v.begin() + cuoi, 0LL);      // (1)
}

long long tongSongSong(const std::vector<int>& v, int soKhuc) {
    const std::size_t NGUONG = 500000;                                   // (2) ít hơn thì khỏi song song
    if (soKhuc <= 1 || v.size() < NGUONG) return tongKhuc(v, 0, v.size());

    const std::size_t n = v.size();
    std::vector<std::future<long long>> phieu;
    for (int k = 0; k < soKhuc; ++k) {
        std::size_t dau = n * k / soKhuc;                                // (3) biên khúc
        std::size_t cuoi = n * (k + 1) / soKhuc;
        phieu.push_back(std::async(std::launch::async, tongKhuc, std::cref(v), dau, cuoi));   // (4)
    }
    long long tong = 0;
    for (std::future<long long>& f : phieu) tong += f.get();             // (5) gộp theo thứ tự khúc
    return tong;
}

int main() {
    std::vector<int> so(1000003);                                        // (6) cố ý không chia hết cho 8
    unsigned x = 12345;
    for (int& s : so) {
        x = x * 1103515245u + 12345u;                                    // (7) số giả ngẫu nhiên, ai chạy cũng giống
        s = static_cast<int>((x >> 16) % 100000);
    }
    long long chuan = std::accumulate(so.begin(), so.end(), 0LL);
    std::cout << "tuan tu: " << chuan << "\n";
    for (int k : {1, 2, 4, 8}) {
        long long t = tongSongSong(so, k);
        std::cout << k << " khuc: " << t << (t == chuan ? " dung" : " SAI") << "\n";
    }
    std::vector<int> nho(1000, 7);
    std::cout << "day ngan: " << tongSongSong(nho, 8) << "\n";           // (8) dưới ngưỡng: chạy tuần tự
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `accumulate` cộng một khúc, bộ cộng `0LL` kiểu `long long` |
| (2) | Dãy ngắn hơn ngưỡng thì chạy thẳng tuần tự; mọi bản song song nên có lối thoát này |
| (3) | Biên khúc `n * k / soKhuc`: các khúc nối đuôi nhau, phủ đủ mọi phần tử |
| (4) | Mỗi khúc một `async`; `std::cref(v)` như `std::ref` ([Bài 24](../nhom-3-da-luong/24-thread-co-ban.md)) nhưng cho tham chiếu `const`, để khỏi sao chép vector |
| (5) | `get()` theo thứ tự khúc rồi cộng; chỉ `main` đụng `tong` |
| (6)-(7) | 1 000 003 phần tử (cố ý không chia hết cho 8), dữ liệu giả ngẫu nhiên từ 0 đến 99999 |
| (8) | Dãy 1000 phần tử dưới ngưỡng: ra 7000 mà không sinh luồng |

**Kết quả khi chạy** (g++ 11.4; chạy nhiều lần cùng kết quả; TSan sạch):

```text
tuan tu: 32760968841
1 khuc: 32760968841 dung
2 khuc: 32760968841 dung
4 khuc: 32760968841 dung
8 khuc: 32760968841 dung
day ngan: 7000
```

**Thử thay đổi: bỏ `LL`, viết `accumulate(..., 0)`.** Mình chạy: mọi dòng song song ra `-1598769527 SAI` (tổng thật 32760968841 vượt `int`, tràn rồi quay vòng); `-fsanitize=undefined` báo `signed integer overflow`. Lỗi nằm ở **kiểu bộ cộng**, bản tuần tự cũng sai y vậy; chia luồng không gây ra và không sửa được nó.

**Bản SAI: mọi luồng cộng vào một biến chung** (fragment, không đứng một mình):

```cpp
// bo-qua-kiem-tra
long long tong = 0;                                        // một biến, bốn luồng
phieu.push_back(std::async(std::launch::async, [&so, &tong, dau, cuoi] {
    for (std::size_t i = dau; i < cuoi; ++i) tong += so[i];   // SAI: đọc-cộng-ghi không nguyên tử
}));
```

Mình chạy bản này (4 luồng, cùng dữ liệu): không tối ưu, 5 lần ra 8,6 đến 11,4 tỉ thay vì 32,76 tỉ (mất khoảng 70% lần cộng); `-O2`, 3 lần ra khoảng 8,2 tỉ (gần đúng một khúc: compiler giữ `tong` trong thanh ghi, luồng ghi sau cùng thắng). TSan báo `data race` ngay dòng `tong += so[i]` ("Previous write ... by thread T1", "Read ... by thread T2"). Mutex bọc mỗi lần cộng thì đúng nhưng chậm: cả vòng thành tuần tự cộng thêm chi phí khóa.

**Chi phí và ngưỡng.** Mỗi luồng khởi động mất cỡ vài chục micro-giây (dãy 1000 phần tử: 4 khúc mất khoảng 80 µs, 8 khúc khoảng 240 µs, trong khi cộng tuần tự chưa tới 1 µs). Mình đo `-O2`, lấy lần nhanh nhất của nhiều lần, **tỉ lệ thời gian song song / tuần tự** (dưới 1 là nhanh hơn; hai lần chạy cho khoảng):

| n | 4 khúc | 8 khúc |
|---|---|---|
| 10 nghìn | 7 đến 26 (lỗ nặng) | 21 đến 57 |
| 100 nghìn | 1,9 đến 2,8 | 5 đến 6,5 |
| 500 nghìn | 0,7 đến 1,0 | 1,1 đến 1,7 |
| 1 triệu | 0,6 đến 0,7 | 0,65 đến 1,1 |
| 10 triệu | 0,34 đến 0,84 | 0,38 đến 0,53 |
| 100 triệu | 0,22 đến 0,57 | 0,26 đến 0,40 |

Điểm hòa vốn ở `-O2` quanh vài trăm nghìn phần tử (tuần tự cỡ 0,2 đến 0,5 ms); bài chọn ngưỡng 500000. Không tối ưu (`-O0`) thì mỗi phần tử tốn hơn nên hòa vốn sớm hơn (mình thấy lãi từ khoảng 200 nghìn). Máy bận thì số nhảy: chỉ tin vào mẫu. Tăng tốc cao nhất cỡ **2 đến 4,5 lần dù có 8 luồng phần cứng**: cộng mảng bị nghẽn ở băng thông bộ nhớ (cửa tủ lạnh chung), và 8 khúc không hơn gì 4 khúc vì máy chỉ có 4 lõi thật. Đừng đo khi bật TSan.

**Thử thay đổi: cộng số thực.** Mình chia 1 000 000 số `1.0 / (i + 1)` kiểu `double` thành k khúc như trên: 1 khúc cho `14.392726722864989` đúng bằng `accumulate`; 2, 4, 8 khúc cho `...865813`, `...86587`, `...865611` (mỗi lần chạy lại ra đúng như vậy, nhưng **khác** bản tuần tự ở các chữ số cuối). Phép cộng `double` không kết hợp (`(a + b) + c` có thể khác `a + (b + c)`), mà chia khúc đổi thứ tự cộng. Số nguyên thì không bị: so `==` được; số thực thì so với sai số.

### Đề 2: merge sort song song

```cpp
#include <algorithm>
#include <atomic>
#include <future>
#include <iostream>
#include <vector>

std::atomic<int> soLuongDaSinh{0};                    // đếm số luồng mới đã sinh (chỉ để quan sát)

// Sắp xếp v[dau, cuoi) tăng dần. sau = số tầng chia đôi còn được phép sinh luồng.
void sapXep(std::vector<int>& v, std::size_t dau, std::size_t cuoi, int sau) {
    const std::size_t NGUONG = 1000;                  // (1) đoạn ngắn hơn thì khỏi chia
    if (sau <= 0 || cuoi - dau < NGUONG) {
        std::sort(v.begin() + dau, v.begin() + cuoi); // (2) lá: sắp tuần tự
        return;
    }
    std::size_t giua = dau + (cuoi - dau) / 2;
    ++soLuongDaSinh;
    std::future<void> trai = std::async(std::launch::async, sapXep, std::ref(v), dau, giua, sau - 1);   // (3)
    sapXep(v, giua, cuoi, sau - 1);                   // (4) luồng này làm nửa phải
    trai.get();                                       // (5) chờ nửa trái xong
    std::inplace_merge(v.begin() + dau, v.begin() + giua, v.begin() + cuoi);   // (6) trộn hai nửa đã sắp
}

int main() {
    std::vector<int> goc(64003);
    unsigned x = 777;
    for (int& s : goc) {
        x = x * 1103515245u + 12345u;
        s = static_cast<int>((x >> 16) % 100000);
    }
    std::vector<int> chuan = goc;
    std::sort(chuan.begin(), chuan.end());            // (7) bản tuần tự để so

    for (int sau : {0, 1, 3, 5}) {
        std::vector<int> v = goc;
        soLuongDaSinh = 0;
        sapXep(v, 0, v.size(), sau);
        std::cout << "sau " << sau << ": sinh " << soLuongDaSinh << " luong, "
                  << (v == chuan ? "dung" : "SAI") << ", sap xep xong: "
                  << std::is_sorted(v.begin(), v.end()) << "\n";
    }
    std::vector<int> rong;
    sapXep(rong, 0, rong.size(), 3);
    std::vector<int> mot = {5};
    sapXep(mot, 0, mot.size(), 3);
    std::cout << "rong " << rong.size() << ", mot " << mot[0] << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1)-(2) | Hết tầng (`sau <= 0`) hoặc đoạn ngắn: chạy `std::sort` tuần tự rồi thoát. Đoạn rỗng và một phần tử cũng rơi vào đây (in `rong 0, mot 5`, không sinh luồng) |
| (3) | Nửa trái `[dau, giua)` giao cho một luồng mới, hạ `sau` đi 1 |
| (4) | Luồng hiện tại tự sắp nửa phải `[giua, cuoi)`; hai nửa không giao nhau nên không đụng nhau |
| (5) | `get()` chờ nửa trái xong, và bảo đảm mọi thứ luồng kia đã ghi vào `v` hiện ra cho luồng này |
| (6) | Hai nửa đều đã sắp: `inplace_merge` ghép |
| (7) | `std::sort` toàn bộ để làm đáp án so sánh |

Khi mọi đoạn còn dài hơn ngưỡng, số luồng mới là `2^sau - 1` (cộng luồng gốc là `2^sau` luồng chạy), vì mỗi tầng chia nhân đôi số đoạn. Đoạn nào ngắn hơn ngưỡng thì dừng chia sớm và sinh ít luồng hơn.

**Kết quả khi chạy** (TSan sạch; 64003 phần tử):

```text
sau 0: sinh 0 luong, dung, sap xep xong: 1
sau 1: sinh 1 luong, dung, sap xep xong: 1
sau 3: sinh 7 luong, dung, sap xep xong: 1
sau 5: sinh 31 luong, dung, sap xep xong: 1
rong 0, mot 5
```

**Bản SAI 1: chia tới từng phần tử, không giới hạn độ sâu** (fragment):

```cpp
// bo-qua-kiem-tra
void sapXepSai(std::vector<int>& v, std::size_t dau, std::size_t cuoi) {
    if (cuoi - dau < 2) return;                    // SAI: không có `sau`, không có ngưỡng
    std::size_t giua = dau + (cuoi - dau) / 2;
    std::future<void> trai = std::async(std::launch::async, sapXepSai, std::ref(v), dau, giua);
    sapXepSai(v, giua, cuoi);
    trai.get();
    std::inplace_merge(v.begin() + dau, v.begin() + giua, v.begin() + cuoi);
}
```

Kết quả **đúng** và TSan sạch, nhưng quá tốn: mình chạy `-O2`, n = 2000 sinh 1999 luồng và mất khoảng 240 đến 320 ms (`std::sort` một luồng cho 2000 số chỉ cỡ 55 micro-giây); n = 20000 sinh 19999 luồng, khoảng 2,1 giây; n = 100000 chạy khoảng 9,7 giây rồi **ném `std::system_error`** "Resource temporarily unavailable" sau 88915 luồng (giới hạn luồng của hệ điều hành, đổi theo máy). Hàng chục nghìn luồng sống cùng lúc vì mỗi luồng cha chờ con. Đừng thử n lớn trên máy dùng chung.

**Bản SAI 2: quên `get()` trước khi trộn.** Mình xóa dòng (5): `inplace_merge` chạy khi luồng kia còn sắp nửa trái. Chạy 3 lần đều in `SAI, sap xep xong: 0` cho mọi `sau >= 1`; TSan báo `data race` ngay trong thuật toán trộn (`stl_algo.h`, `stl_algobase.h`): luồng chính trộn đúng vùng mà luồng kia còn đang ghi. Hàm hủy của `future` (chờ luồng) chỉ cứu tới khi hàm trả về, trễ hơn chỗ cần.

**Chi phí và ngưỡng.** Phần song song là sắp các lá; phần **tuần tự theo chuỗi** là các lần trộn: tầng trên cùng trộn n phần tử một mình, tầng dưới n/2 (hai luồng cùng trộn), n/4... Tổng chuỗi trộn cỡ `2n` bước. Nên thời gian xấp xỉ `sắp(n / 2^sau) + 2n`, và thêm luồng chỉ giảm số hạng đầu. Tỉ lệ thời gian song song / tuần tự (`std::sort` một luồng; ba lần chạy cho khoảng; dưới 1 là nhanh hơn):

| n (tuần tự) | sau 1 | sau 2 | sau 3 | sau 4 |
|---|---|---|---|---|
| 10 nghìn (cỡ 0,5 ms) | 0,58 đến 0,63 | 0,49 đến 0,85 | 0,89 đến 1,5 | 1,5 đến 5,2 |
| 100 nghìn (cỡ 7 ms) | 0,55 | 0,34 đến 0,57 | 0,46 đến 0,65 | 0,45 đến 0,54 |
| 1 triệu (cỡ 70 đến 120 ms) | 0,6 đến 1,3 | 0,34 đến 0,67 | 0,41 đến 0,66 | 0,31 đến 0,42 |
| 10 triệu (cỡ 1 s) | 0,63 đến 0,78 | 0,38 đến 0,48 | 0,20 đến 0,38 | 0,22 đến 0,30 |

Mẫu: sắp xếp nặng CPU (O(n log n)) nên **đáng song song sớm hơn nhiều** so với cộng mảng, từ cỡ chục nghìn phần tử; nhưng nhiều tầng quá thì lỗ ở n nhỏ (cột `sau 4`, n = 10 nghìn). Tăng tốc nhiều nhất cỡ 3 đến 5 lần, rồi gần như phẳng khi `sau` vượt `log2(số luồng phần cứng)` (8 luồng phần cứng thì `sau` 3).

### Đề 3: đếm từ map-reduce

```cpp
#include <algorithm>
#include <future>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using Dem = std::unordered_map<std::string, int>;     // từ -> số lần xuất hiện

// MAP: đếm từ trong các dòng [dau, cuoi), vào một bảng của riêng khúc này.
Dem demKhuc(const std::vector<std::string>& dong, std::size_t dau, std::size_t cuoi) {
    Dem cucBo;                                        // (1) không ai khác thấy bảng này
    for (std::size_t i = dau; i < cuoi; ++i) {
        std::istringstream in(dong[i]);               // (2) biến dòng thành "dòng chảy" từ
        std::string tu;
        while (in >> tu) ++cucBo[tu];                 // (3) đọc từng từ, đếm
    }
    return cucBo;                                     // (4) trả bảng về qua future
}

// REDUCE: cộng dồn các bảng cục bộ vào một bảng chung, một luồng làm.
Dem demSongSong(const std::vector<std::string>& dong, int soKhuc) {
    std::vector<std::future<Dem>> phieu;
    for (int k = 0; k < soKhuc; ++k) {
        std::size_t dau = dong.size() * k / soKhuc;
        std::size_t cuoi = dong.size() * (k + 1) / soKhuc;
        phieu.push_back(std::async(std::launch::async, demKhuc, std::cref(dong), dau, cuoi));   // (5)
    }
    Dem chung;
    for (std::future<Dem>& f : phieu) {
        Dem cucBo = f.get();                          // (6) chờ khúc xong, nhận bảng của nó
        for (const auto& [tu, so] : cucBo) chung[tu] += so;   // (7) gộp: chỉ luồng main đụng `chung`
    }
    return chung;
}

int main() {
    std::vector<std::string> dong;
    unsigned x = 2024;
    auto ngauNhien = [&x] { x = x * 1103515245u + 12345u; return (x >> 16) % 200; };
    for (int i = 0; i < 20000; ++i) {                 // (8) 20000 dòng, mỗi dòng 10 từ
        std::string d;
        for (int j = 0; j < 10; ++j) {
            unsigned a = ngauNhien(), b = ngauNhien();
            unsigned id = a * b / 200;                // (9) lệch về từ có số nhỏ: vài từ rất phổ biến
            d += "tu" + std::to_string(id) + (j < 9 ? " " : "");
        }
        dong.push_back(d);
    }

    Dem chuan = demKhuc(dong, 0, dong.size());        // tuần tự: một khúc là cả dãy
    for (int k : {1, 3, 8}) {
        Dem kq = demSongSong(dong, k);
        std::cout << k << " khuc: " << (kq == chuan ? "giong" : "KHAC") << " ban tuan tu\n";
    }

    long long tong = 0;
    for (const auto& [tu, so] : chuan) tong += so;
    std::vector<std::pair<std::string, int>> xep(chuan.begin(), chuan.end());
    std::sort(xep.begin(), xep.end(), [](const auto& a, const auto& b) {
        return a.second != b.second ? a.second > b.second : a.first < b.first;   // (10) nhiều trước, hòa thì theo chữ
    });
    std::cout << "tong " << tong << " tu, " << chuan.size() << " tu khac nhau\n";
    for (int i = 0; i < 3; ++i) std::cout << xep[i].first << " " << xep[i].second << "\n";
    return 0;
}
```

**Chạy từng dòng**

| Dòng | Chuyện gì xảy ra |
|---|---|
| (1) | `cucBo` là biến cục bộ của hàm: mỗi luồng một bảng, không luồng nào thấy bảng của luồng khác |
| (2)-(3) | Biến dòng thành dòng chảy, đọc từng từ và `++cucBo[tu]` |
| (4) | Trả bảng theo giá trị: `future` chuyển nó (không sao chép) cho `main` |
| (5) | Mỗi khúc dòng một `async`, `std::cref(dong)` như Đề 1 |
| (6)-(7) | **Reduce**: `get()` bảng của khúc rồi cộng từng cặp vào `chung`; chỉ `main` đụng `chung` |
| (8)-(9) | 20000 dòng, mỗi dòng 10 từ `tu0`...`tu199`; nhân hai số rồi chia để từ số nhỏ xuất hiện nhiều hơn |
| (10) | So sánh để in tất định: nhiều lần trước; hòa thì theo chữ |

**Kết quả khi chạy** (TSan sạch; ổn định qua các lần chạy):

```text
1 khuc: giong ban tuan tu
3 khuc: giong ban tuan tu
8 khuc: giong ban tuan tu
tong 200000 tu, 199 tu khac nhau
tu0 7482
tu1 4999
tu2 4328
```

Các khúc cộng được theo thứ tự nào cũng ra cùng bảng vì phép gộp là `+` trên số nguyên (kết hợp và giao hoán). Số khúc 3 không chia hết 20000 vẫn đúng nhờ công thức biên.

**Bản SAI 1: một bảng chung, không khóa** (fragment):

```cpp
// bo-qua-kiem-tra
Dem chung;                                                // một bảng cho bốn luồng
phieu.push_back(std::async(std::launch::async, [&dong, &chung, dau, cuoi] {
    for (std::size_t i = dau; i < cuoi; ++i) {
        std::istringstream in(dong[i]);
        std::string tu;
        while (in >> tu) ++chung[tu];                     // SAI: sửa bảng băm từ nhiều luồng
    }
}));
```

Mình chạy 40 lần với 4 luồng: **0 lần đúng**; 35 lần ra sai (tổng từ 199 mấy nghìn thay vì 200000, đôi khi 203 đến 218 từ khác nhau thay vì 199: cùng một từ bị chèn hai lần), 2 lần **treo** (quá 5 giây), 3 lần **sập** (mã 139, segmentation fault). TSan báo `data race` trong `hashtable.h`. Bảng băm tự cấp phát nút và đổi cấu trúc khi chèn hay nới (rehash), nên đụng đồng thời không chỉ mất cộng mà hỏng cả cấu trúc.

**Bản chậm: một mutex chung quanh mỗi `++chung[tu]`.** Đúng kết quả nhưng không có lợi: mình đo 4 luồng, `-O2`, ra **chậm hơn tuần tự** ở mọi cỡ mình thử (từ 2000 dòng trở lên, thời gian gấp khoảng 1,05 đến 1,5 lần), vì mỗi từ phải xếp hàng lấy khóa. Bảng riêng mỗi luồng khỏi hết hàng chờ đó.

**Chi phí và ngưỡng.** Làm (map) là O(số từ) chia đều cho các luồng; gộp (reduce) là O(số từ khác nhau × số khúc) và chạy trên một luồng, đó là phần tuần tự. Ở đây chỉ 199 từ khác nhau nên gộp gần như miễn phí. Tỉ lệ thời gian song song / tuần tự (`-O2`, hai lần chạy):

| Số dòng (10 từ/dòng) | map-reduce 4 khúc | 8 khúc | một mutex chung, 4 luồng |
|---|---|---|---|
| 200 | 1,3 đến 4,3 | 1,8 đến 2,8 | 1,8 đến 2,3 |
| 2000 (tuần tự cỡ 3 ms) | 0,59 đến 0,63 | 0,57 đến 1,0 | 1,3 đến 1,4 |
| 20000 | 0,44 đến 0,55 | 0,31 đến 0,46 | 1,06 đến 1,46 |
| 200000 | 0,52 đến 0,56 | 0,26 đến 0,42 | 1,13 đến 1,20 |
| 1 triệu | 0,40 đến 0,47 | 0,33 đến 0,35 | 1,07 |

Hòa vốn nằm giữa vài trăm và vài nghìn dòng (tuần tự cỡ 1 ms trở lên). Tăng tốc cỡ 2 đến 3 lần. Nếu số từ khác nhau lên tới hàng triệu thì bước gộp một luồng thành cổ chai: xem câu hỏi nối tiếp.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Đề 1: 8 luồng mà sao không nhanh gấp 8?"
    Ba lý do cộng lại. (1) Phần tuần tự theo Amdahl: khởi động từng luồng (vài chục micro-giây mỗi luồng) và cộng các tổng riêng. (2) Cộng mảng là việc **chặn ở bộ nhớ**: các lõi cùng chờ một đường bộ nhớ, nên cỡ 2 đến 4 lần là trần (mình đo vậy). (3) 8 là luồng phần cứng chứ không phải 8 lõi: máy mình 4 lõi, mỗi lõi hai luồng, và hai luồng chung một lõi không nhân đôi sức tính. **Nối tiếp:** nếu mỗi phần tử cần tính nặng thì đóng góp (2) nhỏ hơn và tăng tốc gần số lõi hơn.

??? question "Đề 1: sao không dùng `std::reduce(std::execution::par, ...)`?"
    Về nguyên tắc nên thử trước vì ngắn nhất, nhưng chuẩn chỉ **cho phép** song song. Trên libstdc++ của g++ 11 máy mình, nó biên dịch được không cần `-ltbb` mà chạy trên **một luồng** (mình đếm id luồng); muốn song song thật cần cài và liên kết TBB. Thêm nữa `reduce` đổi thứ tự cộng: với số `double` cho kết quả khác `accumulate` ở chữ số cuối, còn `accumulate` thì đảm bảo trái sang phải. Tự chia khúc bằng `async` thì biết chắc cái mình có.

??? question "Đề 1: số khúc chọn thế nào, và n quá nhỏ thì sao?"
    Việc nặng CPU: cỡ `hardware_concurrency()`, hơn nữa chỉ thêm chi phí. Luôn có ngưỡng: dưới đó gọi thẳng bản tuần tự, vì khởi động luồng mất vài chục micro-giây mỗi luồng; ở máy mình cộng mảng hòa vốn quanh vài trăm nghìn phần tử. Ngưỡng phụ thuộc máy và mức tối ưu nên đo, không thuộc lòng. **Nối tiếp:** một khúc ném ngoại lệ thì `get()` ném lại ở `main`; mình chạy thử và thấy các khúc còn lại vẫn chạy xong (hàm hủy `future` chờ) trước khi `catch` chạy, nên không rò luồng.

??? question "Đề 2: vì sao phải giới hạn độ sâu? Chọn `sau` bằng bao nhiêu?"
    Mỗi tầng chia nhân đôi số luồng; chia tới lá thì n luồng (mình đo: n = 2000 ra 1999 luồng, chậm gấp nhiều lần; n = 100000 thì `system_error`). Luồng chỉ đáng khi việc của nó lớn hơn vài chục micro-giây. Chọn `sau` sao cho `2^sau` cỡ số luồng phần cứng (8 luồng thì `sau` 3), và thêm ngưỡng độ dài đoạn. Quá số đó thì đo không thấy lợi.

??? question "Đề 2: bước trộn có song song được không? Có cần bộ nhớ phụ?"
    Cách bài này làm thì tầng trộn trên cùng chạy một luồng và là phần tuần tự lớn nhất (cỡ n bước). Muốn nhanh hơn thì **trộn song song**: lấy phần tử giữa của đoạn A, tìm vị trí tương ứng trong đoạn B bằng `lower_bound` rồi trộn hai cặp đoạn con độc lập; mình nêu hướng, không cài. Bộ nhớ phụ: `inplace_merge` xin vùng đệm cỡ N để đạt N − 1 phép so sánh, không xin được thì chậm hơn (O(N log N)). **Nối tiếp:** vẫn ổn định vì `inplace_merge` ổn định; dùng `std::sort` ở lá thì cả bản này không còn ổn định (dùng `std::stable_sort` nếu cần).

??? question "Đề 3: nếu có 10 triệu từ khác nhau thì sao?"
    Bước reduce một luồng cộng 10 triệu mục từ mỗi bảng: thành cổ chai theo Amdahl, và bộ nhớ bảng riêng nhân lên theo số khúc. Cách sửa: **chia theo khóa** (phân vùng): sau bước map, chia các từ theo `hash(tu) % k`, mỗi luồng reduce một phần các từ (không phần nào trùng nhau, nên cũng không khóa). Hoặc gộp **theo cây** (từng đôi bảng, song song). Đây là ý của shuffle trong map-reduce thật.

??? question "Đề 3: dùng một concurrent hash map chia shard thay cho bảng riêng được không?"
    Được và gọn ([Bài 72](72-concurrent-hashmap.md)), nhưng mỗi lần `++` vẫn khóa một shard, và những từ phổ biến (`tu0` chiếm gần 4%) dồn vào một shard thành điểm nóng. Bảng riêng không khóa lúc làm, chỉ trả giá lúc gộp; thường nhanh hơn khi gộp rẻ. Chọn shard khi dữ liệu đến liên tục, không có giai đoạn "xong khúc rồi gộp". **Nối tiếp:** nếu file 100 GB không nạp nổi vào bộ nhớ thì đọc từng khối, mỗi khối map rồi gộp dần, không nạp hết.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Nói 'song song nhanh hơn' mà không đo, hoặc đo sai"
    Ở bài này cộng 10 nghìn số bằng 4 luồng chậm hơn tuần tự 7 đến 26 lần, và 8 luồng còn tệ hơn. Đo bằng `steady_clock`, lần nhanh nhất của nhiều lần, `-O2`, không bật TSan, rồi nói "đổi theo máy". Trên bảng trắng, hãy nói con số ngưỡng bạn **đã đo**, không nói "luôn nhanh hơn".

!!! warning "Lỗi 2: Gộp qua biến chung thay vì kết quả riêng"
    `tong += so[i]` từ nhiều luồng, hoặc `++chung[tu]` vào bảng chung không khóa: mình chạy ra tổng thiếu, bảng hỏng, treo và sập. Khóa mỗi lần cập nhật thì đúng nhưng chậm hơn tuần tự. Mẫu đúng: mỗi luồng **trả** kết quả riêng, một luồng gộp.

!!! warning "Lỗi 3: Quên phần dư, kiểu bộ cộng, và chia không giới hạn"
    Biên khúc `n / soKhuc` rơi phần dư (khúc cuối thiếu): dùng `n * k / soKhuc`. Bộ cộng `0` thay `0LL` tràn `int` (mình chạy ra `-1598769527`). Chia đệ quy tới từng phần tử sinh 1999 luồng cho 2000 phần tử và `system_error` cho 100000. Nói rõ cả ba khi giải thích đề.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="75" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Cần tính tổng một `vector<int>` 2000 phần tử, máy có 8 luồng phần cứng. Chọn gì?

- Chia 8 khúc, mỗi khúc một `async`, vì có sẵn 8 luồng phần cứng
- Gọi thẳng `std::accumulate` trên một luồng, vì việc quá nhỏ
- Chia 2 khúc, vì ít luồng thì chi phí khởi động ít hơn
- Mỗi phần tử một `async`, vì càng nhiều luồng càng nhanh

<p class="giai-thich" markdown>Cộng 2000 số chỉ tốn cỡ một hai micro-giây, còn khởi động một luồng tốn cỡ vài chục micro-giây, nên mọi cách chia đều chậm hơn (mình đo: ngay 10 nghìn phần tử, 4 khúc chậm hơn 7 lần trở lên). Chia 2 khúc vẫn trả phí khởi động mà chẳng thu được gì. Có sẵn luồng phần cứng không có nghĩa là dùng chúng miễn phí. Mỗi phần tử một luồng là cách tệ nhất vì chi phí nhân lên 2000 lần.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 2.** Bốn luồng (mỗi luồng một khúc `[dau, cuoi)` khác nhau của `v`) cùng chạy đoạn sau. Sau khi cả bốn xong, điều gì đúng nhất?

```text
long long tong = 0;                      // chung cho bốn luồng
// mỗi luồng chạy:
for (std::size_t i = dau; i < cuoi; ++i) tong += v[i];
```

- `tong` luôn đúng, vì mỗi luồng chỉ cộng các số của khúc mình
- `tong` đúng, vì phép `+=` trên `long long` là một lệnh nên nguyên tử
- `tong` có thể sai nhưng chỉ lệch ít, và chương trình vẫn hợp lệ
- Có data race: kết quả không đáng tin và chương trình không hợp lệ

<p class="giai-thich" markdown>Các khúc `v` không giao nhau nhưng `tong` thì chung: `+=` là đọc, cộng, ghi ba bước, và hai luồng xen vào nhau làm mất lần cộng; đây là data race theo chuẩn (hành vi không xác định). Mỗi luồng chỉ cộng số của mình không cứu được biến đích dùng chung. `+=` không nguyên tử với `long long` thường. Còn "lệch ít" không bảo đảm: mình chạy ra thiếu khoảng 70%, và về nguyên tắc chương trình không còn hợp lệ.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Một bản merge sort song song chia đệ quy tới tận đoạn một phần tử, mỗi nửa trái một `std::async`, trộn bằng `inplace_merge` sau `get()`. Với 100000 phần tử, vấn đề chính là gì?

- Sinh hàng chục nghìn luồng: chậm, có thể ném `system_error`
- Kết quả sai, vì hai nửa của dãy cùng ghi vào một vùng bộ nhớ chung
- Đệ quy sâu cỡ 100000 tầng nên tràn stack của luồng chính ngay từ đầu
- `inplace_merge` không dùng được khi đã gọi `get()` trên một future

<p class="giai-thich" markdown>Chia đôi mỗi lần nên số luồng bằng cỡ số lá, tức hàng chục nghìn luồng sống cùng lúc (mình đo: 9,7 giây rồi `system_error` sau 88915 luồng). Hai nửa là hai vùng khác nhau của dãy nên không tranh nhau, và kết quả vẫn đúng ở cỡ nhỏ. Độ sâu đệ quy chỉ cỡ `log2(n)`, khoảng 17 tầng, không phải 100000. `inplace_merge` sau `get()` chính là cách đúng.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 4.** Đọc đoạn sau. Gọi `sapXep(v, 0, n, 3)` với n đủ lớn thì tổng cộng sinh bao nhiêu luồng **mới** (không tính luồng gọi)?

```text
void sapXep(v, dau, cuoi, sau) {
    if (sau <= 0 || cuoi - dau < NGUONG) { sort; return; }
    trai = async(sapXep, v, dau, giua, sau - 1);   // luồng mới
    sapXep(v, giua, cuoi, sau - 1);                // luồng này tự làm
    trai.get();  inplace_merge(...);
}
```

- 3, vì tham số `sau` bằng 3 nên mỗi tầng sinh đúng một luồng
- 8, vì cây chia có 8 đoạn lá và mỗi lá chạy trên một luồng mới
- 7, vì mỗi tầng nhân đôi số đoạn nên tổng là 1 + 2 + 4
- 15, vì cây ba tầng có 1 + 2 + 4 + 8 nút và nút nào cũng sinh luồng

<p class="giai-thich" markdown>Tầng đầu sinh 1 luồng; hai đoạn con (một ở luồng cũ, một ở luồng mới) mỗi đoạn sinh thêm 1, tổng 2; tầng ba có 4 đoạn, sinh 4; ra 1 + 2 + 4 = 7 luồng mới, cộng luồng gọi là 8 luồng chạy lá. Con số 8 là số luồng cộng luồng gọi, không phải số luồng mới. Con số 3 nhầm `sau` với số luồng. Con số 15 đếm cả tầng lá cũng sinh luồng, mà tầng lá `sau = 0` chỉ gọi `sort`.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 5.** Đếm từ trên 1 triệu dòng bằng 4 luồng. Vì sao mỗi luồng giữ một `unordered_map` riêng rồi gộp, thay vì một `unordered_map` chung bọc mutex quanh mỗi lần `++`?

- Vì `unordered_map` không cho phép khóa nó bằng mutex từ nhiều luồng
- Vì khóa chung bắt các luồng xếp hàng từng từ, có khi chậm hơn
- Vì bước gộp sau cùng gần như không tốn gì trong mọi trường hợp
- Vì `std::async` không cho lambda bắt biến chung bằng tham chiếu

<p class="giai-thich" markdown>Với khóa chung, mỗi từ phải chờ lượt vào bảng, nên phần "đếm" thành tuần tự cộng chi phí khóa (mình đo thời gian gấp khoảng 1,05 đến 1,5 lần tuần tự). Bản thân `unordered_map` dùng được với mutex, chỉ chậm. Bước gộp rẻ hay đắt tùy số từ khác nhau: hàng triệu từ thì thành cổ chai. Và `async` bắt tham chiếu bình thường (bản SAI vẫn biên dịch); lỗi nằm ở chỗ đồng bộ.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 6.** Cộng 1 000 000 số `double` bằng `accumulate` tuần tự, rồi chia 4 khúc cộng riêng và gộp. Hai kết quả so sánh với nhau thế nào?

- Luôn bằng nhau, vì chia khúc vẫn cộng đúng cùng một tập số
- Luôn khác nhau rất nhiều, vì chia khúc làm mất một phần số
- Bằng nhau nếu không có data race, vì không còn lý do nào khác
- Có thể khác ở các chữ số cuối, vì cộng `double` không kết hợp

<p class="giai-thich" markdown>Chia khúc đổi thứ tự các phép cộng, mà `(a + b) + c` có thể khác `a + (b + c)` khi làm tròn: mình đo ra `...864989` (tuần tự) và `...86587` (4 khúc). Cùng một tập số không bảo đảm cùng kết quả khi thứ tự đổi. Không mất số nào và không data race, nên chênh lệch chỉ nhỏ ở cuối, không "rất nhiều". Vì thế với số thực, so với sai số chứ không `==`; số nguyên thì `==` được.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Một chương trình có 20% thời gian bắt buộc tuần tự (`p = 0,8` song song được). Theo Amdahl, với 8 lõi tăng tốc tối đa khoảng bao nhiêu?

- 3,3 lần
- 8 lần
- 6,4 lần
- 5 lần

<p class="giai-thich" markdown>`1 / (0,2 + 0,8 / 8) = 1 / 0,3`, khoảng 3,3 lần. Con số 8 chỉ đúng khi không có phần tuần tự. Con số 6,4 là `0,8 * 8`, một phép nhân không có trong công thức. Con số 5 là trần khi số lõi tiến tới vô hạn (`1 / 0,2`), mà 8 lõi chưa tới đó.</p>
</div>

</div>

## 🔑 Tóm tắt

1. Mọi đề chia việc theo bốn bước: chia khúc (biên `n * k / soKhuc`), mỗi luồng làm riêng và **trả** kết quả riêng, một luồng gộp, rồi kiểm với bản tuần tự. Gộp qua biến hoặc bảng chung thì hoặc sai (tổng thiếu, bảng hỏng, treo, sập: mình chạy) hoặc chậm hơn tuần tự (mutex chung).
2. Tổng: `async` + `accumulate` trên từng khúc, bộ cộng `0LL`; ngưỡng hòa vốn quanh vài trăm nghìn phần tử, tăng tốc chỉ cỡ 2 đến 4,5 lần vì nghẽn băng thông bộ nhớ; số thực chia khúc cho kết quả khác ở chữ số cuối.
3. Merge sort: nửa trái `async`, nửa phải tự làm, `get()` rồi `inplace_merge`; `sau` giới hạn còn `2^sau` luồng (chia tới lá: 1999 luồng cho 2000 phần tử, `system_error` ở 100000); bước trộn trên cùng là phần tuần tự nên tăng tốc phẳng ở cỡ 3 đến 5 lần.
4. Đếm từ: bảng riêng mỗi luồng (map), cộng các bảng ở `main` (reduce); đúng với mọi số khúc vì `+` kết hợp, giao hoán; hòa vốn giữa vài trăm và vài nghìn dòng; số từ khác nhau quá nhiều thì phân vùng khóa theo `hash % k`.
5. Chuẩn: `async(launch::async)` như thể luồng mới và có thể ném `system_error`; `accumulate` tuần tự, `reduce` đổi thứ tự được, `execution::par` chỉ là cho phép (g++ 11 máy mình: một luồng). Số đo luôn đổi theo máy và `-O`: nói tỉ lệ và ngưỡng đã đo, không nói "luôn nhanh hơn".
