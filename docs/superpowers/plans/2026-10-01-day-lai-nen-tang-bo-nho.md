# Dạy lại nền tảng bộ nhớ, con trỏ, RAII và smart pointer từ gốc — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay hai bài cũ về con trỏ/RAII/smart pointer (người học báo "dạy hổng nhiều, không hiểu gì") bằng 9 bài mới dạy từ gốc, không nhảy bước, rồi đánh số lại các bài cũ về move semantics, C++11/14/17 và UB thành Bài 10–12.

**Architecture:** Dùng nguyên khung MkDocs, trắc nghiệm, bộ kiểm tra đã có. Thay đổi là nội dung và đánh số: 9 bài mới `01…09` theo "luật dạy v2" (câu chuyện, bảng "chạy từng dòng", kết quả chạy thật, cầu nối Go), ba bài cũ đổi thành `10…12`.

**Tech Stack:** MkDocs Material 9.5.39, g++ 11 (`-std=c++17 -Wall -pthread`), Python 3.10 `unittest`, hai script kiểm tra trong `scripts/`.

## Global Constraints

- Nội dung bằng **tiếng Việt có dấu**; người học: 3 năm Go, gần như chưa biết C++; cần bài **không nhảy bước**, thuật ngữ nào cũng giải thích trước khi dùng.
- **Mọi bài viết theo luật dạy v2**: `.superpowers/sdd/2026-10-01-day-lai-nen-tang-bo-nho/teaching-rules-v2.md` (đọc kỹ; nó có luật "không hổng", khuôn từng đoạn code, luật trung thực khi chạy thật, luật trắc nghiệm công bằng, cơ chế commit/báo cáo).
- Khuôn 8 khối của mỗi bài, cú pháp trắc nghiệm và các kiểm tra do `scripts/kiem_cau_truc.py` thực thi (đã có sẵn trong repo; các khối `## 🧠`, `## 📖`, `## 💻`, `## 🎤`, `## ⚠️`, `## ✍️`, `## 🔑` + dòng `!!! abstract "🎯 Học xong bài này, bạn sẽ"`; trắc nghiệm 6–8 câu `<div class="cau-hoi" data-dap-an="N" markdown>`, câu hỏi in đậm, DÒNG TRỐNG, rồi các lựa chọn `- ` liền nhau, dòng trống, đúng một `<p class="giai-thich" markdown>`; tóm tắt đúng 5 dòng đánh số). Bài mẫu hình dạng: `docs/nhom-1-nen-tang-bo-nho/10-move-semantics.md` sau Task 1 (hoặc `03-move-semantics.md` ở commit 8848647).
- `data-bai` = số bài hai chữ số = tiền tố `NN-` của tên file; mỗi bài có đúng một dòng `<span class="diem" data-bai="NN">` trong `docs/tien-do.md`.
- Mọi khối ```` ```cpp ```` biên dịch và chạy sạch (`g++ -std=c++17 -Wall -pthread`, mã thoát 0, dưới 5 giây); khối minh họa lỗi biên dịch / UB / chạy mãi bắt đầu bằng dòng `// bo-qua-kiem-tra`. Không đặt khối ```` ```cpp ```` trong phần đề của câu trắc nghiệm (dùng code nội dòng hoặc khối ```` ```text ````).
- Repo **công khai**: không có tên công ty, khách hàng, dự án, tên người, đường dẫn cá nhân. Thông tin người học chỉ nêu là "bạn đã quen Go".
- Thư mục bài: `docs/nhom-1-nen-tang-bo-nho/`; tên file đúng như từng task chỉ định; thêm vào `nav` của `mkdocs.yml` theo thứ tự; thuật ngữ mới thêm vào `docs/glossary.md`.
- Không đặt liên kết tới bài chưa tồn tại (build `--strict` sẽ lỗi): viết "Bài N" dạng chữ thường cho bài sau; Task 11 sẽ gắn liên kết chéo.
- Git: danh tính commit đã cấu hình cục bộ (không đổi). Mỗi commit tiếng Việt, kết thúc bằng dòng `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. **Không push** trong các task này (người điều phối quyết định khi nào push). Không đụng `docs/superpowers/` và `.superpowers/`.
- Commit tham chiếu chứa nội dung bài CŨ (để tái dùng ý, câu hỏi, định nghĩa thuật ngữ): `8848647`. Xem bằng `git show 8848647:docs/nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md` (và `02-raii-smart-pointer.md`, `docs/glossary.md`).

## Lộ trình mới của Nhóm 1

| Bài | File | Nội dung |
|---|---|---|
| 01 | `01-bo-nho-byte-dia-chi.md` | Chương trình C++ đầu tiên, bộ nhớ là dãy ngăn có số, byte, địa chỉ, biến, `sizeof`, `&` |
| 02 | `02-stack-heap-static.md` | Ba vùng nhớ: stack, heap, vùng tĩnh (global/static); vòng đời |
| 03 | `03-con-tro-co-ban.md` | Con trỏ: khai báo, `&`, `*`, `nullptr`, `->` |
| 04 | `04-con-tro-mang-ham.md` | Con trỏ với hàm, mảng, phép tính con trỏ, con trỏ tới con trỏ, chuỗi kiểu C |
| 05 | `05-tham-chieu-const.md` | Tham chiếu, `const`, truyền tham số: giá trị / con trỏ / tham chiếu / `const&` |
| 06 | `06-new-delete.md` | Cấp phát động `new`/`delete`, `new[]`/`delete[]`, ba lỗi kinh điển |
| 07 | `07-raii.md` | RAII: hàm tạo/hàm hủy, phạm vi, ngoại lệ; so với `defer` của Go |
| 08 | `08-unique-ptr.md` | `std::unique_ptr` |
| 09 | `09-shared-ptr-weak-ptr.md` | `std::shared_ptr`, `std::weak_ptr`, vòng tham chiếu, cách chọn |
| 10 | `10-move-semantics.md` | (bài cũ, đánh số lại) |
| 11 | `11-cpp11-14-17.md` | (bài cũ, đánh số lại) |
| 12 | `12-memory-leak-ub.md` | (bài cũ, đánh số lại) |

---

### Task 1: Dọn bài cũ và đánh số lại thành Bài 10–12

**Files:**
- Delete: `docs/nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md`, `docs/nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md`
- Rename (git mv): `03-move-semantics.md` → `10-move-semantics.md`, `04-cpp11-14-17.md` → `11-cpp11-14-17.md`, `05-memory-leak-ub.md` → `12-memory-leak-ub.md` (cùng thư mục)
- Modify: ba file vừa đổi tên, `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`

**Interfaces:**
- Produces: sau task này, Nhóm 1 chỉ có Bài 10, 11, 12 (nav, tiến độ, thuật ngữ nhất quán, build xanh). Các task Bài 01–09 thêm bài mới vào nav **trước** Bài 10 và thêm dòng tiến độ/thuật ngữ theo thứ tự số bài.

- [ ] **Step 1: Xóa hai bài cũ và đổi tên ba bài**

```bash
git rm docs/nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md docs/nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md
git mv docs/nhom-1-nen-tang-bo-nho/03-move-semantics.md docs/nhom-1-nen-tang-bo-nho/10-move-semantics.md
git mv docs/nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md docs/nhom-1-nen-tang-bo-nho/11-cpp11-14-17.md
git mv docs/nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md docs/nhom-1-nen-tang-bo-nho/12-memory-leak-ub.md
```

- [ ] **Step 2: Sửa ba bài đã đổi tên**

Trong mỗi file: đổi tiêu đề `# Bài N — …` thành số mới (10, 11, 12); đổi `data-bai="03|04|05"` thành `"10|11|12"`. Sửa MỌI chỗ nhắc "Bài 1", "Bài 2", "Bài 3", "Bài 4", "Bài 5" (văn bản và liên kết) cho đúng số mới theo bảng: ý stack/heap → **Bài 2**; con trỏ → **Bài 3–4**; tham chiếu/`const` → **Bài 5**; `new`/`delete`/rò rỉ/con trỏ treo/giải phóng hai lần → **Bài 6**; RAII → **Bài 7**; `unique_ptr` → **Bài 8**; `shared_ptr`/`weak_ptr` → **Bài 9**; bài cũ 3 → **Bài 10**; bài cũ 4 → **Bài 11**; bài cũ 5 → **Bài 12**. Với bài mới CHƯA tồn tại (Bài 1–9) viết chữ thường, không dùng liên kết Markdown; liên kết giữa Bài 10, 11, 12 phải là liên kết thật tới tên file mới. Không đổi nội dung kỹ thuật, câu trắc nghiệm hay code.

- [ ] **Step 3: Cập nhật `mkdocs.yml`, `docs/tien-do.md`, `docs/glossary.md`**

- `mkdocs.yml`: mục `"Nhóm 1 — Nền tảng và bộ nhớ"` chỉ còn ba bài với tiêu đề `"Bài 10 — Move semantics, rule of 0/3/5"`, `"Bài 11 — Tính năng C++11/14/17"`, `"Bài 12 — Memory leak, dangling, UB"` trỏ tới tên file mới.
- `docs/tien-do.md`: bỏ hai dòng của Bài 1, 2; đổi ba dòng còn lại thành Bài 10, 11, 12 (liên kết và `data-bai="10|11|12"`).
- `docs/glossary.md`: bỏ MỌI dòng có cột "Bài" trỏ tới hai file đã xóa (nội dung cũ vẫn còn trong `git show 8848647:docs/glossary.md` để các bài mới dùng lại); các dòng của bài cũ 3, 4, 5 đổi cột "Bài" thành Bài 10, 11, 12 với liên kết tới tên file mới.

- [ ] **Step 4: Chạy kiểm tra**

Run: `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`
Expected: test OK; `0 lỗi cấu trúc`; `… khối code, 0 lỗi`; build sạch (không cảnh báo liên kết hỏng).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: bỏ hai bài cũ, đánh số lại Bài 3–5 thành Bài 10–12 để nhường chỗ cho 9 bài dạy từ gốc

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Bài 01 — Chương trình C++ đầu tiên, bộ nhớ, byte và địa chỉ

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/01-bo-nho-byte-dia-chi.md`; Modify `mkdocs.yml` (nav, đặt TRƯỚC Bài 10), `docs/glossary.md`, `docs/tien-do.md`. `data-bai="01"`.

**Việc người học làm được sau bài:** viết, biên dịch, chạy chương trình C++ ngắn nhất; hiểu bộ nhớ là dãy ngăn có số; biết một biến có bốn thứ (tên, kiểu, giá trị, địa chỉ); in được kích thước và địa chỉ của biến.

**Câu chuyện:** một dãy tủ khóa dài vô tận, mỗi ngăn đựng đúng một byte và có một số thứ tự (địa chỉ). Biến = đặt tên cho một hay vài ngăn liền nhau và cho biết trong đó đựng loại gì.

**Phải dạy theo thứ tự này (không bỏ bước):**
1. Chương trình ngắn nhất, từng dòng: `#include <iostream>`, `int main()`, `{ }`, `std::cout << … << "\n";`, `;`, `return 0;` (+ biên dịch/chạy: `g++ -std=c++17 -Wall -o bai bai.cpp && ./bai`). Nói rõ `std::` là "họ" của `cout`. Cầu nối Go: `package main`/`func main()`/`fmt.Println`.
2. Bit và byte (1 byte = 8 bit, đựng 256 giá trị); bộ nhớ = dãy byte có địa chỉ; địa chỉ viết dạng hệ 16 (`0x…`), giải thích ngắn "hệ 16 chỉ là cách viết số gọn".
3. Biến: tên, kiểu, giá trị, địa chỉ; kiểu quyết định số byte: `char`, `int`, `double`, `long long`, `bool`; `sizeof`. Nhấn mạnh: chuẩn không ép `int` là 4 byte, nhưng thực tế trên máy tính thường là 4 (đừng khẳng định chắc hơn).
4. Toán tử `&x` = "địa chỉ của x" và cách in địa chỉ (`std::cout << &tuoi` in được địa chỉ cho `int`; với `char` phải ép `static_cast<void*>(&chu)` vì nếu không nó coi là chuỗi chữ — giải thích gọn lý do).
5. Điều gì xảy ra với địa chỉ khi chạy lại chương trình (có thể đổi) và vì sao chỉ cần để ý "kiểu mẫu" chứ không phải con số.

**Chương trình bắt buộc:** (a) `Xin chao`; (b) in `sizeof` của `char`, `int`, `double`, `long long`, `bool`; (c) hai/ba biến và in địa chỉ của chúng (+ in hiệu hai địa chỉ ép sang `char*`/`unsigned long` chỉ khi bạn kiểm chứng được và dùng hedge "thường"); (d) một biến thay đổi giá trị rồi in lại để thấy "cùng ngăn, giá trị khác". Có "Thử thay đổi": đổi `int` thành `long long` thì `sizeof` đổi; bỏ `;` thì lỗi biên dịch (trích dòng báo lỗi thật ngắn).

**Hộp Go:** `unsafe.Sizeof`, `&x` giống ý nghĩa; Go cũng có địa chỉ nhưng ít khi phải để ý.

**Câu hỏi phỏng vấn (3–4):** biến trong C/C++ gồm những gì; `sizeof` là gì, trả về kiểu gì (`std::size_t`); `int` có luôn 4 byte không; địa chỉ của hai lần chạy có giống nhau không.

**Trắc nghiệm (7 câu, đáp án đúng rải đều):** 1 byte có bao nhiêu bit (8); địa chỉ của một ngăn nhớ là gì; một biến gồm những thứ nào; `sizeof(int)` trên máy thường là bao nhiêu và chuẩn có đảm bảo không; `&x` cho ra gì; đọc code đoán kết quả (một đoạn 3–4 dòng với `sizeof`); vì sao in `&chu` kiểu `char` phải ép sang `void*` hoặc điều gì sai khi hai lần chạy in địa chỉ khác nhau (không sai).

**Thuật ngữ:** byte, bit, địa chỉ (address), biến (variable), kiểu (type), `sizeof`, toán tử (operator), biên dịch (compile), `#include`, `main`, `std::cout`.

- [ ] **Step 1:** Đọc luật dạy v2 và viết bài theo khuôn; biên dịch/chạy mọi chương trình và mọi "Thử thay đổi", ghi kết quả thật.
- [ ] **Step 2:** Cập nhật `mkdocs.yml` (nav: Bài 01 trước Bài 10), `docs/tien-do.md` (dòng `data-bai="01"` trước dòng Bài 10), `docs/glossary.md` (thuật ngữ trên, đặt trước các dòng Bài 10).
- [ ] **Step 3:** `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict` sạch.
- [ ] **Step 4:** Commit: `git add -A && git commit -m "feat: Bài 01 — chương trình C++ đầu tiên, bộ nhớ, byte và địa chỉ" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`

---

### Task 3: Bài 02 — Ba vùng nhớ: stack, heap và vùng tĩnh

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/02-stack-heap-static.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="02"`.

**Việc người học làm được sau bài:** nói được một biến nằm ở stack, heap hay vùng tĩnh và nó sống đến khi nào; trả lời câu hỏi "đối tượng global thuộc class nằm ở heap hay stack?" (cả hai đều không: vùng tĩnh).

**Câu chuyện (giữ nguyên bộ ẩn dụ cho cả nhóm):** cái **bàn học** (stack: nhỏ, lấy nhanh, hết giờ tự dọn), **kho đồ của trường** (heap: rộng, phải tự xin và tự trả), **bảng treo trên tường lớp** (vùng tĩnh: có từ lúc lớp mở, gỡ khi lớp đóng cửa).

**Phải dạy theo thứ tự:**
1. Hàm gọi hàm và "khung" (stack frame) của mỗi lần gọi: biến cục bộ sinh ra khi vào hàm, mất khi ra khỏi hàm/khối `{}`; stack nhỏ (vài MB, tránh mảng khổng lồ cục bộ — hedge); giải thích "tràn stack" (stack overflow) bằng đệ quy vô hạn (chỉ mô tả, KHÔNG chạy).
2. Heap: xin bằng `new` (chỉ giới thiệu hình dạng `new int(5)`, `delete`; học kỹ ở Bài 06), tồn tại đến khi tự trả, rộng hơn nhưng chậm hơn; ai quên trả → rò rỉ (chỉ nhắc tên).
3. Vùng tĩnh: biến global, biến `static` cục bộ, thành viên `static`; có suốt chương trình. Dạy gọn `struct` có hàm tạo/hàm hủy (2–3 câu: "hàm tạo chạy khi đối tượng ra đời, hàm hủy khi chết") để làm chương trình thí nghiệm.
4. **Chương trình thí nghiệm vòng đời:** một `struct Dau` có hàm tạo/hàm hủy in tên; đặt `Dau toanCuc("toan cuc")` ở ngoài hàm, `static Dau tinh("static trong ham")` trong một hàm, `Dau cucBo("cuc bo")` trong `main`, và một đối tượng `new`/`delete` rõ ràng. Kết quả in thật cho thấy: global ra đời TRƯỚC `main` và chết SAU `main`; static cục bộ ra đời ở lần gọi hàm đầu tiên; cục bộ chết ở cuối khối. Ghi đúng thứ tự in thật.
5. Bảng tổng kết bốn "kiểu thời gian sống" (automatic, static, dynamic, thread): thread_local chỉ nhắc tên một dòng.
6. In địa chỉ của một biến global, một biến static, một biến cục bộ và một vùng `new`: chương trình in thật; nói "thường" ba nhóm số trông khác nhau, không khẳng định chiều tăng/giảm cụ thể.
7. Hộp **"Hỏi nhanh"** trả lời đúng câu của người học: *đối tượng của class khai báo global nằm ở đâu?* → vùng tĩnh, hàm tạo chạy trước `main`; nếu class chứa `std::vector` thì bản thân object ở vùng tĩnh còn dữ liệu bên trong vector ở heap. Và **static initialization order fiasco**: thứ tự khởi tạo global giữa các file `.cpp` khác nhau là không xác định; cách tránh thường gặp (static cục bộ trong hàm, từ C++11 khởi tạo an toàn khi gọi lần đầu) — mô tả bằng lời, chỉ cho code một file (không cần bản hai file).

**Hộp Go:** Go không hỏi stack/heap vì có **escape analysis**: `return &x` của biến cục bộ là hợp lệ, trình biên dịch tự chuyển `x` lên heap (`go build -gcflags=-m` in `moved to heap: x`); biến cấp package nằm vùng tĩnh và Go quy định thứ tự khởi tạo rõ ràng. C++ không làm hộ: vì vậy RAII và smart pointer. Chỉ dùng các câu đúng.

**Câu hỏi phỏng vấn (4–5):** stack vs heap vs static; một biến global của class nằm ở đâu và khi nào hàm tạo/hủy chạy; static initialization order fiasco; vì sao không nên đặt mảng 100MB làm biến cục bộ; storage duration là gì.

**Trắc nghiệm (7 câu):** biến cục bộ nằm ở đâu; biến global; đối tượng `new`; câu "đọc thứ tự in" từ một chương trình nhỏ (code trong khối ```text); điều nào đúng về hàm tạo của global (chạy trước `main`); `static` cục bộ khởi tạo khi nào; vì sao Go không có chuyện stack/heap rõ ràng như C++ (escape analysis).

**Thuật ngữ:** stack, stack frame (khung gọi hàm), heap, vùng tĩnh (static storage), vòng đời (lifetime), phạm vi (scope), hàm tạo (constructor), hàm hủy (destructor), stack overflow, global, escape analysis.

- [ ] **Step 1:** Viết bài theo luật dạy v2 và các ý trên; biên dịch/chạy chương trình vòng đời và ghi thứ tự in THẬT; chạy chương trình in địa chỉ và ghi một lần chạy thật.
- [ ] **Step 2:** Nav (Bài 02 sau Bài 01, trước Bài 10), tiến độ (`data-bai="02"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 02 — ba vùng nhớ: stack, heap và vùng tĩnh`.

---

### Task 4: Bài 03 — Con trỏ cơ bản

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/03-con-tro-co-ban.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="03"`.

**Việc người học làm được sau bài:** khai báo con trỏ, lấy địa chỉ, giải tham chiếu, dùng `nullptr`, dùng `->` với struct; đọc được hình vẽ con trỏ trỏ tới biến.

**Câu chuyện:** tờ giấy ghi "đồ của em ở phòng 12" (bảng treo/phòng = ngăn nhớ); tờ giấy KHÔNG phải là đồ, nó chỉ đường tới đồ. Con trỏ cũng là một biến, cũng nằm ở một ngăn nhớ, và cái nó đựng là một địa chỉ.

**Phải dạy theo thứ tự:**
1. Ôn từ Bài 01: `&x` là địa chỉ của `x`. Con trỏ là biến đựng địa chỉ: `int* p = &x;` đọc từng ký hiệu (`int*` = "con trỏ tới int").
2. Giải tham chiếu `*p` = "đi theo địa chỉ để thấy/sửa giá trị"; hai nghĩa của dấu `*` (khi khai báo và khi dùng) — "Hay nhầm". Hình vẽ ASCII hai ô: `x` (giá trị 10) và `p` (đựng địa chỉ của x).
3. Sửa giá trị qua con trỏ (`*p = 20;` đổi `x`). Hai con trỏ cùng trỏ một biến.
4. `nullptr`: "chưa trỏ vào đâu"; kiểm tra `if (p)`/`p != nullptr`; con trỏ chưa khởi tạo là nguy hiểm (chỉ mô tả, KHÔNG chạy); giải tham chiếu `nullptr` là hành vi không xác định (khối `// bo-qua-kiem-tra`, không chạy).
5. Con trỏ cũng có kích thước và địa chỉ riêng: in `sizeof(p)` (thường 8 trên máy 64-bit — hedge) và `&p`, so với `p` và `&x`.
6. Con trỏ tới `struct`: `struct Nguoi { int tuoi; }`, `Nguoi* ai = &a; ai->tuoi` ≡ `(*ai).tuoi`.
7. Bẫy khai báo `int* a, b;` (b là `int`, không phải con trỏ) — kiểm chứng bằng chương trình/ lỗi biên dịch thật.
8. Con trỏ `void*` chỉ nhắc tên một câu (dùng ở Bài 01).

**Chương trình bắt buộc:** (a) `x`, `p`, `*p`, sửa qua `p`; (b) in `p == &x`; (c) `nullptr` + `if (p)`; (d) `sizeof(p)`, `&p`; (e) struct + `->`. Mỗi chương trình có bảng "Chạy từng dòng" với hình ô nhớ.

**Hộp Go:** `*int`, `&x`, `*p`, `nil` ↔ `nullptr`; Go gọi `p.field` luôn tự giải tham chiếu, C++ phải viết `p->field`; Go không có phép tính con trỏ (Bài 04) và có GC.

**Câu hỏi phỏng vấn (4–5):** con trỏ là gì; `*p` và `&x`; `nullptr` vs `NULL` vs `0` (nullptr có kiểu riêng); con trỏ chưa khởi tạo vs null; `->` là gì; kích thước con trỏ.

**Trắc nghiệm (7 câu):** con trỏ đựng gì; `*p` làm gì; sau `int* p = &x; *p = 5;` giá trị `x` (đọc code); `int* a, b;` thì `b` là gì; `nullptr` nghĩa là gì; `p->tuoi` tương đương; giải tham chiếu con trỏ null gây ra gì (UB, không phải "luôn crash").

**Thuật ngữ:** con trỏ (pointer), giải tham chiếu (dereference), `nullptr`, toán tử `->`, `void*`, struct, null pointer.

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy mọi chương trình thật; chạy thật bẫy `int* a, b;`.
- [ ] **Step 2:** Nav (03), tiến độ (`data-bai="03"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 03 — con trỏ cơ bản`.

---

### Task 5: Bài 04 — Con trỏ với hàm, mảng, phép tính con trỏ

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/04-con-tro-mang-ham.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="04"`.

**Việc người học làm được sau bài:** viết hàm đổi giá trị biến của nơi gọi bằng con trỏ; hiểu mảng và con trỏ liên quan thế nào; dùng `p + 1`; biết "mảng thoái hóa thành con trỏ" (array decay) và bẫy `sizeof`; đọc chuỗi kiểu C (`const char*`) cơ bản.

**Câu chuyện:** gửi **bản photo** của bài cho bạn (truyền theo giá trị: bạn sửa trên bản photo, bài gốc không đổi) so với đưa **số phòng** (truyền con trỏ: bạn đến sửa đúng bài gốc). Mảng = dãy ngăn liền nhau; con trỏ tới ngăn đầu + đếm số ngăn.

**Phải dạy theo thứ tự:**
1. Truyền theo giá trị: hàm nhận bản sao (`void tang(int x)` không đổi biến gốc) — chạy thật.
2. Truyền con trỏ để sửa bản gốc (`void tang(int* x)`, gọi `tang(&a)`), `swap` bằng con trỏ; kiểm tra null trong hàm.
3. Mảng `int a[4] = {10,20,30,40};`: bốn ngăn liền nhau; truy cập `a[i]`; in địa chỉ các phần tử (thường cách nhau `sizeof(int)`).
4. "Thoái hóa mảng": trong biểu thức tên mảng thành con trỏ tới phần tử đầu; `int* p = a;` ; `p[i]` ≡ `*(p + i)`.
5. Phép tính con trỏ: `p + 1` nhích đúng một PHẦN TỬ (không phải một byte); `p++`; hiệu hai con trỏ cùng mảng; không cộng hai con trỏ; đi ra ngoài mảng là UB (khối `// bo-qua-kiem-tra`, không chạy).
6. Bẫy: truyền mảng vào hàm là truyền con trỏ: `sizeof(a)` ở nơi khai báo (16, thường) khác `sizeof` tham số mảng trong hàm (kích thước con trỏ) — kiểm chứng bằng chương trình thật (đọc cảnh báo của `-Wall` nếu có và ghi lại); nên truyền kèm số phần tử hoặc dùng `std::vector`/`std::array` (chỉ nhắc, học ở nhóm STL).
7. Con trỏ tới con trỏ (`int**`): MỘT ví dụ ngắn "hàm cấp cho bạn một con trỏ mới" và vì sao cần `**` hoặc tham chiếu; không đi sâu hơn.
8. Chuỗi kiểu C: `const char* ten = "An";` là con trỏ tới các ký tự kết thúc bằng ký tự `'\0'`; in được bằng `std::cout`; không sửa được chuỗi hằng (chỉ mô tả, hedge); khuyên dùng `std::string`.

**Hộp Go:** slice là (con trỏ, độ dài, sức chứa) nên có độ dài đi kèm; mảng C++ thoái hóa thành con trỏ mất độ dài; Go không cho phép số học con trỏ (trừ `unsafe`).

**Câu hỏi phỏng vấn (5):** truyền theo giá trị vs bằng con trỏ; `a[i]` ≡ `*(a+i)`; array decay và `sizeof`; con trỏ `p+1` nhích bao nhiêu byte; chuỗi kiểu C kết thúc thế nào.

**Trắc nghiệm (7–8 câu), có ít nhất 3 câu đọc code:** truyền theo giá trị có đổi biến gốc không; `p + 1` nhích gì; `*(p+2)` với mảng cho trước; `sizeof` mảng vs `sizeof` con trỏ; `swap` bằng con trỏ làm gì; ký tự kết thúc chuỗi C; ra ngoài mảng gây gì (UB).

**Thuật ngữ:** truyền theo giá trị (pass by value), mảng (array), array decay (mảng thoái hóa thành con trỏ), phép tính con trỏ (pointer arithmetic), chuỗi kiểu C, `'\0'`, `int**` (con trỏ tới con trỏ), phần tử (element).

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật mọi chương trình và các "Thử thay đổi" (bẫy `sizeof`, ghi cảnh báo thật nếu có).
- [ ] **Step 2:** Nav (04), tiến độ (`data-bai="04"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 04 — con trỏ với hàm, mảng và phép tính con trỏ`.

---

### Task 6: Bài 05 — Tham chiếu và const

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/05-tham-chieu-const.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="05"`.

**Việc người học làm được sau bài:** dùng tham chiếu như biệt danh; chọn đúng cách truyền tham số (giá trị / con trỏ / tham chiếu / `const&`); đọc đúng `const int*`, `int* const`, `const int&`.

**Câu chuyện:** bạn Nguyễn Văn An có biệt danh "Tí": gọi Tí hay gọi An đều là CÙNG MỘT người (tham chiếu = biệt danh, không phải người thứ hai). Nhãn dán **"chỉ được xem, không được sửa"** là `const`.

**Phải dạy theo thứ tự:**
1. Tham chiếu `int& b = a;`: là biệt danh; phải gắn ngay khi khai báo; không có "tham chiếu rỗng"; không gắn lại sang đối tượng khác (`b = c;` là GÁN GIÁ TRỊ của c cho a — chạy thật để thấy). Hình vẽ: một ô nhớ hai tên.
2. Tham chiếu vs con trỏ (bảng).
3. Bốn cách truyền tham số cho hàm với một lớp đo "đếm số lần sao chép": `struct Cay` có **hàm tạo sao chép** (copy constructor) in "copy!" (giải thích 2–3 câu: nó chạy mỗi khi tạo bản sao); chương trình gọi `docTheoGiaTri(Cay)`, `docBangConTro(const Cay*)`, `docBangThamChieu(const Cay&)`, `suaBangThamChieu(Cay&)`; in thật số lần "copy!" (chỉ cách theo giá trị tạo bản sao).
4. `const`: `const int x = 5;` không sửa; đọc `const int*` (giá trị là hằng, con trỏ đổi chỗ được) vs `int* const` (con trỏ là hằng) vs `const int* const`; mẹo đọc từ phải sang trái; mỗi trường hợp một dòng thử sửa → lỗi biên dịch THẬT (trích dòng lỗi ngắn, mỗi cái trong khối `// bo-qua-kiem-tra`).
5. `const&` nhận cả giá trị tạm (`docTheoThamChieu(5)` hợp lệ) còn `int&` thì không — kiểm chứng.
6. Trả về tham chiếu tới biến cục bộ là sai (con trỏ/tham chiếu treo): khối `// bo-qua-kiem-tra`, giải thích bằng bàn học (biến cục bộ bị dọn).
7. Hàm thành viên `const` chỉ nhắc 3 câu (cam kết không sửa đối tượng) — dùng ở bài sau.

**Hộp Go:** Go truyền MỌI THỨ theo giá trị; "tham chiếu" của Go thực ra là con trỏ, slice/map/chan chứa con trỏ bên trong; Go không có `const` cho biến tham số.

**Câu hỏi phỏng vấn (5):** tham chiếu vs con trỏ; vì sao `const T&`; `const int*` vs `int* const`; tham chiếu có null được không; có thể trả về tham chiếu tới biến cục bộ không.

**Trắc nghiệm (7 câu):** biệt danh nghĩa là gì; tham chiếu có gắn lại được không (đọc code `b = c`); đọc `const int*`; đọc `int* const`; truyền `Cay` theo giá trị tạo mấy bản sao (đọc code); `const&` bind được với giá trị tạm không; trả về tham chiếu tới biến cục bộ.

**Thuật ngữ:** tham chiếu (reference), `const` (hằng), hàm tạo sao chép (copy constructor), giá trị tạm (temporary), truyền theo tham chiếu (pass by reference), `const&`.

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật chương trình đếm "copy!" và các lỗi biên dịch minh họa; ghi thông báo lỗi thật ngắn.
- [ ] **Step 2:** Nav (05), tiến độ (`data-bai="05"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 05 — tham chiếu và const`.

---

### Task 7: Bài 06 — Cấp phát động `new`/`delete` và ba lỗi kinh điển

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/06-new-delete.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="06"`.

**Việc người học làm được sau bài:** cấp phát và giải phóng bộ nhớ động đúng cách; phân biệt `new`/`delete` với `new[]`/`delete[]`; nhận ra rò rỉ, con trỏ treo, giải phóng hai lần; hiểu vì sao phải có RAII.

**Câu chuyện:** quay lại **kho đồ của trường**: xin chìa (`new`), nhận về tờ giấy ghi số phòng (con trỏ), dùng xong phải **trả** (`delete`). Quên trả → kho đầy dần. Trả rồi mà vẫn cầm tờ giấy cũ → đến phòng đã dọn. Trả hai lần → sổ sách rối.

**Phải dạy theo thứ tự:**
1. `int* p = new int(5);` → `*p` → `delete p;`; `new` trả địa chỉ ở heap (nối Bài 02, Bài 03). Vì sao cần heap: tồn tại sau khi hàm kết thúc, kích thước biết lúc chạy.
2. `new` với `struct` có hàm tạo/hàm hủy: `new` GỌI hàm tạo, `delete` GỌI hàm hủy (chương trình `Cay` in "tao"/"huy"); khác `malloc/free` (chỉ nhắc: không gọi hàm tạo; không dùng trong C++ hiện đại).
3. Mảng động: `new int[n]`, `delete[] p`; `new Cay[2]` in hai lần tạo; `delete[]` in hai lần hủy.
4. Ba lỗi, mỗi lỗi: câu chuyện + khối code `// bo-qua-kiem-tra` (chỉ những khối UB; riêng rò rỉ chạy được và chương trình thoát mã 0): (i) **rò rỉ** (leak): quên `delete` (cho thấy dòng "huy" KHÔNG xuất hiện); (ii) **con trỏ treo**/dùng sau khi trả (use-after-free); (iii) **giải phóng hai lần** (double free); thêm (iv) trộn `new[]` với `delete` là UB. Đặt `p = nullptr` sau `delete` là thói quen tốt nhưng không phải thuốc chữa mọi thứ (hedge).
5. Chạy chương trình rò rỉ với AddressSanitizer thật (`g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer`) và dán báo cáo LeakSanitizer THẬT rút gọn (bỏ số tiến trình, đường dẫn máy; nói đã rút gọn); Valgrind chưa cài trên máy: chỉ ghi lệnh, KHÔNG dán kết quả.
6. Vì sao thủ công là mong manh: hàm có nhiều `return` hoặc ném ngoại lệ ở giữa dễ quên `delete` (kể bằng lời, ví dụ ngắn trong khối `// bo-qua-kiem-tra` nếu cần) → mở đường cho Bài 07 (RAII).

**Hộp Go:** Go có GC nên không có `delete`; rò rỉ trong Go thường là giữ tham chiếu mãi (khác bản chất).

**Câu hỏi phỏng vấn (5):** `new` vs `malloc`; `delete` vs `delete[]`; rò rỉ vs con trỏ treo vs giải phóng hai lần; làm sao tìm rò rỉ (ASan/LeakSanitizer, Valgrind); vì sao nên tránh `new`/`delete` trần.

**Trắc nghiệm (7–8 câu), ≥3 câu đọc code:** `new` gọi gì (hàm tạo) và `delete` gọi gì; thiếu `delete` thì thấy gì khi chạy (đọc kết quả in); `new[]` đi với gì; ba lỗi nhận biết qua mô tả; vì sao `p = nullptr` sau `delete` giúp một phần; rò rỉ có phải UB không (không); ASan phát hiện gì.

**Thuật ngữ:** `new`, `delete`, `new[]`/`delete[]`, rò rỉ bộ nhớ (memory leak), con trỏ treo (dangling pointer), use-after-free, giải phóng hai lần (double free), hành vi không xác định (undefined behavior), AddressSanitizer, LeakSanitizer, `malloc`/`free`.

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật mọi chương trình; chạy ASan thật và dán kết quả rút gọn thật; tuyệt đối không bịa kết quả Valgrind.
- [ ] **Step 2:** Nav (06), tiến độ (`data-bai="06"`), thuật ngữ (có thể tái dùng định nghĩa từ `git show 8848647:docs/glossary.md`).
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 06 — cấp phát động new/delete và ba lỗi kinh điển`.

---

### Task 8: Bài 07 — RAII

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/07-raii.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="07"`.

**Việc người học làm được sau bài:** giải thích RAII bằng lời và bằng code; viết một lớp nhỏ tự mượn khi tạo và tự trả khi hủy; hiểu hàm hủy chạy cả khi `return` sớm và khi có ngoại lệ; so với `defer` của Go.

**Câu chuyện:** **thư viện**: bạn bước vào thì mượn sách, bước ra khỏi cửa thì sách TỰ ĐỘNG được trả, không cần nhớ. Khác với "tự đi trả" ở Bài 06.

**Phải dạy theo thứ tự:**
1. Ôn: hàm tạo/hàm hủy (từ Bài 02, 06). Lớp `TheMuon` in "muon"/"tra"; một đối tượng cục bộ → hàm hủy chạy ở cuối khối `{}` (chạy thật).
2. RAII = *Resource Acquisition Is Initialization*: xin tài nguyên trong hàm tạo, trả trong hàm hủy; "tài nguyên" không chỉ là bộ nhớ: file, khóa, kết nối, ổ cắm mạng (nêu tên `std::ifstream`, `std::lock_guard` như ví dụ thật có sẵn, không đi sâu).
3. Thí nghiệm: (a) hàm dùng `new`/`delete` thủ công có `return` sớm (hàm ví dụ trong khối `// bo-qua-kiem-tra`: dòng "huy" không in) so với (b) cùng hàm với RAII (đối tượng cục bộ) → "huy" LUÔN in. Chạy thật phần (b) và phần (a) bản có thể chạy (không UB) để thấy khác biệt.
4. Ngoại lệ: dạy 4 dòng cú pháp `throw`, `try`/`catch` (cầu nối Go: `panic`/`recover` và `error`); chương trình ném ngoại lệ ở giữa hàm, hàm hủy VẪN chạy khi "tháo ngăn xếp" (stack unwinding) — chạy thật, ghi thứ tự in. Hedge: nếu ngoại lệ không bị bắt ở đâu cả, chương trình gọi `std::terminate` và việc hủy các đối tượng có thể không xảy ra.
5. Tự viết một lớp bọc RAII nhỏ cho một "tài nguyên" in được (ví dụ `class Hop` giữ một con trỏ `new int` và `delete` trong hàm hủy). Giải thích rõ chỗ nguy hiểm khi copy một lớp như vậy (hai đối tượng cùng giữ một con trỏ → hủy hai lần) bằng lời và hình, KHÔNG dạy cách sửa (đó là Rule of 3/5, Bài 10); đặt khối nguy hiểm trong `// bo-qua-kiem-tra`.
6. Chốt: "Đừng gọi `delete` tay; để một đối tượng lo" → Bài 08 là bản làm sẵn cho bộ nhớ.

**Hộp Go:** `defer f.Close()` ≈ hàm hủy; khác ở chỗ `defer` là việc bạn phải NHỚ viết ở từng nơi dùng, còn RAII gắn vào chính kiểu dữ liệu nên không thể quên; `defer` chạy ở cuối hàm còn hàm hủy ở cuối KHỐI `{}`.

**Câu hỏi phỏng vấn (5):** RAII là gì (ví dụ trong chuẩn); vì sao RAII an toàn với ngoại lệ; hàm hủy chạy khi nào; RAII khác `defer` của Go thế nào; vì sao class RAII cần để ý khi copy.

**Trắc nghiệm (7–8 câu), ≥3 câu đọc code:** ý cốt lõi của RAII; hàm hủy của biến cục bộ chạy khi nào; thứ tự in của chương trình có `return` sớm; thứ tự in khi có ngoại lệ; RAII khác `defer` ở điểm nào; vì sao class giữ con trỏ thô nguy hiểm khi copy; ví dụ nào trong chuẩn là RAII.

**Thuật ngữ:** RAII, tài nguyên (resource), hàm hủy (destructor), ngoại lệ (exception), `throw`/`try`/`catch`, tháo ngăn xếp (stack unwinding), `std::terminate`, `defer` (Go).

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật mọi chương trình, ghi thứ tự in thật (kể cả khi ngoại lệ).
- [ ] **Step 2:** Nav (07), tiến độ (`data-bai="07"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 07 — RAII`.

---

### Task 9: Bài 08 — `std::unique_ptr`

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/08-unique-ptr.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="08"`.

**Việc người học làm được sau bài:** dùng `std::make_unique`; hiểu "quyền sở hữu duy nhất"; trao quyền bằng `std::move` (hiểu ở mức dùng được; chi tiết ở Bài 10); truyền `unique_ptr` vào/ra hàm đúng cách; biết khi nào dùng con trỏ thô để chỉ "nhìn".

**Câu chuyện:** **chiếc chìa khóa duy nhất** của kho: chỉ một người cầm; muốn người khác dùng thì phải TRAO TAY (người cũ hết chìa); hết người cầm chìa thì kho tự đóng và dọn.

**Phải dạy theo thứ tự:**
1. Nối Bài 07: `unique_ptr` chính là RAII cho bộ nhớ heap. Cho người học thấy một bản tự viết RẤT ngắn (hàm tạo `new`, hàm hủy `delete`, `operator*`, `operator->`) chỉ để hiểu ý tưởng, rồi nói bản thật còn chặn copy và hỗ trợ move (không viết đủ ở đây); dạy 2–3 câu về `operator*`/`operator->` là "cách kiểu của mình giả vờ làm con trỏ".
2. Dùng bản thật: `#include <memory>`, `std::make_unique<Cay>(...)`, `*p`, `p->`, `p.get()` (con trỏ thô nhìn, không sở hữu), `if (p)`, `p.reset()`, `p.release()` (lấy ra và KHÔNG tự hủy nữa — cảnh báo).
3. Không copy được: dòng `auto b = a;` là LỖI BIÊN DỊCH — chạy thật và trích dòng lỗi ngắn (khối `// bo-qua-kiem-tra`). Vì sao: nếu copy được thì có hai chủ và hủy hai lần.
4. Trao tay bằng `std::move`: `auto b = std::move(a);` → `a` thành `nullptr` (chuẩn bảo đảm cho `unique_ptr`); giải thích `std::move` ở mức: "chỉ là lời nói: tôi đồng ý trao đi", việc trao do `unique_ptr` làm; hứa chi tiết ở Bài 10. Chạy thật, in `a == nullptr`.
5. Truyền vào hàm: (a) hàm chỉ cần NHÌN → nhận `const Cay&` hoặc `Cay*` (gọi `*p`/`p.get()`); (b) hàm cần SỞ HỮU → nhận `std::unique_ptr<Cay>` theo giá trị và gọi bằng `std::move(p)`; (c) trả về từ hàm: `return std::make_unique<Cay>();` (chuyển quyền tự nhiên, trình biên dịch lo). Chạy thật mỗi trường hợp với `Cay` in "tao"/"huy" để thấy hàm hủy chạy đúng một lần ở đúng nơi.
6. `std::unique_ptr<int[]>` và nhắc: thường dùng `std::vector` thay cho mảng động. `unique_ptr` trong `std::vector<std::unique_ptr<T>>` chỉ nêu một câu.
7. Chi phí: gần như không tốn thêm (nói hedge: cùng cỡ con trỏ với bộ xóa mặc định). Bộ xóa tùy chỉnh (custom deleter) chỉ nhắc tên.
8. Quy tắc chọn: mặc định dùng `unique_ptr`; con trỏ thô/tham chiếu chỉ để NHÌN.

**Hộp Go:** Go không có "quyền sở hữu" vì GC dọn khi không ai dùng; `unique_ptr` là cách C++ biểu đạt "ai chịu trách nhiệm dọn".

**Câu hỏi phỏng vấn (5):** `unique_ptr` là gì, khác con trỏ thô; vì sao không copy được; `std::move` với `unique_ptr` làm gì; `get()` vs `release()` vs `reset()`; khi nào truyền `unique_ptr` theo giá trị / dùng con trỏ thô.

**Trắc nghiệm (7–8 câu), ≥3 câu đọc code:** ý nghĩa "sở hữu duy nhất"; vì sao `auto b = a;` lỗi; sau `auto b = std::move(a);` thì `a` là gì; `release()` khác `reset()`; hàm nhận `const Cay&` thể hiện điều gì; thứ tự in hàm hủy trong chương trình có trao tay; `make_unique` hơn `new` ở điểm nào (một câu, đúng).

**Thuật ngữ:** smart pointer (con trỏ thông minh), `unique_ptr`, `make_unique`, quyền sở hữu (ownership), `std::move`, `get()`, `release()`, `reset()`, `operator*`/`operator->`, custom deleter (bộ xóa tùy chỉnh).

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật mọi chương trình (kể cả lỗi biên dịch của copy) và ghi kết quả thật.
- [ ] **Step 2:** Nav (08), tiến độ (`data-bai="08"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 08 — std::unique_ptr`.

---

### Task 10: Bài 09 — `std::shared_ptr`, `std::weak_ptr` và cách chọn smart pointer

**Files:** Create `docs/nhom-1-nen-tang-bo-nho/09-shared-ptr-weak-ptr.md`; Modify `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`. `data-bai="09"`.

**Việc người học làm được sau bài:** dùng `shared_ptr` và đọc `use_count`; hiểu bộ đếm tham chiếu từng bước; nhận ra và phá vòng tham chiếu bằng `weak_ptr`; chọn đúng loại con trỏ cho từng tình huống.

**Câu chuyện:** **nhiều bạn cùng giữ một tấm thẻ vào kho**; có một bảng đếm "đang có mấy người giữ thẻ"; ai tới thì đếm +1, ai buông thì −1; người cuối cùng buông về 0 thì kho đóng và dọn. **Người đứng nhìn qua cửa kính** (`weak_ptr`) nhìn được nhưng không giữ thẻ nên không giữ kho mở.

**Phải dạy theo thứ tự:**
1. Vì sao cần chia sẻ (nhiều nơi cùng dùng một đối tượng, không biết ai dùng xong sau cùng). `std::make_shared<Cay>()`.
2. Bộ đếm từng bước: chương trình in `use_count()` sau khi tạo, copy sang `b`, thêm một bản vào hàm, ra khỏi khối, `reset()` — bảng "Chạy từng dòng" ghi bộ đếm tại mỗi dòng; hàm hủy của `Cay` chạy đúng khi đếm về 0 (in "huy" thật).
3. "Khối điều khiển" (control block) chứa bộ đếm — vẽ hình hai phần: đối tượng + khối điều khiển; `make_shared` cấp phát một lần cho cả hai.
4. Vòng tham chiếu: hai đối tượng giữ `shared_ptr` của nhau → bộ đếm không về 0 → KHÔNG BAO GIỜ in "huy" (chạy thật, thoát mã 0, ghi rõ "không có dòng huy nào"; chạy thật với ASan để thấy báo rò rỉ, rút gọn, nói rõ đã rút gọn); sửa bằng `std::weak_ptr` ở một phía → "huy" in đủ (chạy thật, ghi thứ tự).
5. `weak_ptr`: `expired()`, `lock()` trả về `shared_ptr` (hoặc rỗng); không tăng bộ đếm; dùng cho vòng tham chiếu, cache, observer — định nghĩa "cache" (chỗ cất tạm cho nhanh) và "observer" (người theo dõi) bằng lời đời thường.
6. An toàn luồng (chỉ mệnh đề đúng, không đào sâu): bộ đếm tham chiếu cập nhật an toàn giữa các luồng; nhưng đối tượng bên trong, và việc nhiều luồng cùng sửa MỘT biến `shared_ptr`, thì không tự an toàn.
7. Chi phí của `shared_ptr` (khối điều khiển + thao tác nguyên tử cho bộ đếm) → không dùng "cho chắc".
8. **Bảng chọn nhanh** (người học in ra học thuộc): sở hữu một chủ → `unique_ptr`; thật sự chia sẻ → `shared_ptr`; chỉ nhìn, không giữ sống → `weak_ptr`/con trỏ thô/tham chiếu; cần "không có" → `nullptr`/`std::optional` (nhắc tên).

**Hộp Go:** Go dùng GC kiểu "đánh dấu và quét" (tracing) nên vòng tham chiếu được dọn bình thường; C++ `shared_ptr` đếm tham chiếu nên vòng tham chiếu bị rò rỉ.

**Câu hỏi phỏng vấn (6):** `shared_ptr` hoạt động thế nào; `shared_ptr` có thread-safe không; vòng tham chiếu và cách phá; `weak_ptr` dùng khi nào; `make_shared` vs `shared_ptr<T>(new T)`; khi nào chọn loại nào.

**Trắc nghiệm (7–8 câu), ≥3 câu đọc code:** bộ đếm sau chuỗi thao tác (đọc code); khi nào hàm hủy chạy; vòng tham chiếu gây gì; `weak_ptr` có tăng bộ đếm không; `lock()` trả gì; chọn loại con trỏ cho một tình huống mô tả; câu đúng về thread-safety.

**Thuật ngữ:** `shared_ptr`, `weak_ptr`, bộ đếm tham chiếu (reference count), khối điều khiển (control block), `use_count()`, `make_shared`, vòng tham chiếu (reference cycle), `lock()`, `expired()`, cache (bộ nhớ đệm), observer (người theo dõi), thread-safe (an toàn đa luồng).

- [ ] **Step 1:** Viết bài theo luật dạy v2; chạy thật mọi chương trình, ghi `use_count` và thứ tự "huy" thật; chạy ASan thật cho ví dụ vòng tham chiếu.
- [ ] **Step 2:** Nav (09), tiến độ (`data-bai="09"`), thuật ngữ.
- [ ] **Step 3:** Chạy bộ kiểm tra như Task 2 Step 3.
- [ ] **Step 4:** Commit: `feat: Bài 09 — std::shared_ptr, std::weak_ptr và cách chọn smart pointer`.

---

### Task 11: Gắn liên kết chéo và cập nhật trang chủ

**Files:** Modify các bài `01…12` trong `docs/nhom-1-nen-tang-bo-nho/`, `docs/index.md`.

**Interfaces:**
- Consumes: mọi bài 01–12 đã tồn tại với tên file ở bảng "Lộ trình mới".
- Produces: mọi chỗ nhắc "Bài N" (chữ thường được để dành ở Task 1–10) trở thành liên kết Markdown tới đúng file; trang chủ mô tả đúng Nhóm 1 có 12 bài.

- [ ] **Step 1:** Trong từng bài, tìm các chỗ nhắc "Bài N" dạng chữ thường tới một bài đã tồn tại và đổi thành liên kết `[Bài N](tên-file.md)` (cùng thư mục, đường dẫn tương đối đúng); không đổi nội dung nào khác; không tạo liên kết tới bài không tồn tại.
- [ ] **Step 2:** `docs/index.md`: sửa đoạn "Học theo thứ tự nào?" cho khớp lộ trình mới (Nhóm 1 gồm 12 bài, từ "bộ nhớ là gì" đến "move semantics, C++11/14/17 và UB"; các nhóm sau thêm dần).
- [ ] **Step 3:** Chạy `python3 -m unittest discover -s tests && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`: sạch. Kiểm tra không còn chữ "Bài N" thường nào trỏ tới bài đã tồn tại mà chưa có liên kết (`grep -nE "Bài (0?[1-9]|1[0-2])" docs/nhom-1-nen-tang-bo-nho/*.md` rồi đối chiếu bằng mắt).
- [ ] **Step 4:** Commit: `docs: gắn liên kết chéo giữa các bài Nhóm 1 và cập nhật trang chủ`.
