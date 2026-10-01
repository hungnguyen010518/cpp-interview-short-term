# Khung web, trắc nghiệm và Nhóm 1 (Nền tảng và bộ nhớ) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng web ôn C++ phỏng vấn (MkDocs Material) có trắc nghiệm tương tác chấm điểm, bộ kiểm tra tự động, và viết xong 5 bài của Nhóm 1, rồi push lên GitHub Pages.

**Architecture:** Site tĩnh MkDocs Material. Mỗi bài là một file Markdown theo "khuôn bài" cố định. Trắc nghiệm viết bằng HTML thuần bên trong Markdown (`md_in_html`), một file `quiz.js` nhỏ chấm điểm và lưu `localStorage`. Hai script Python kiểm tra cấu trúc bài và biên dịch/chạy mọi khối code C++; CI chạy chúng trước khi deploy.

**Tech Stack:** Python 3.10, mkdocs-material 9.5.39, g++ 11 (`-std=c++17 -pthread`), JavaScript thuần (không thư viện), `unittest` của thư viện chuẩn, GitHub Actions + `mkdocs gh-deploy`.

**Phạm vi kế hoạch này:** Task 1–3 (khung, trắc nghiệm, công cụ), Task 4–8 (Bài 1–5), Task 9 (push). Nhóm 2–5 và đề tổng ôn có kế hoạch riêng, viết sau.

## Global Constraints

Mọi task đều phải tuân thủ các điều sau (lấy nguyên từ bản thiết kế `2026-10-01-cpp-interview-short-term-design.md`):

- Nội dung bài **bằng tiếng Việt có dấu**; tên thuật ngữ tiếng Anh giữ nguyên, lần đầu xuất hiện kèm nghĩa tiếng Việt và có dòng trong `docs/glossary.md`.
- **Văn phong cho học sinh lớp 5 cũng hiểu**, giống `database-tu-a-z`: mở bằng câu chuyện/phép ẩn dụ đời thường rồi mới tới thuật ngữ; câu ngắn, một ý một đoạn. Riêng mục "Câu hỏi phỏng vấn" dùng ngôn ngữ chính xác như khi trả lời nhà tuyển dụng.
- Repo **công khai**: không có code, tên khách hàng, tên dự án hay chi tiết của công ty.
- Khóa học **MkDocs Material 9.5.39** (`requirements.txt` ghim đúng phiên bản này); URL site `https://hungnguyen010518.github.io/cpp-interview-short-term/`.
- Mọi khối ```` ```cpp ```` biên dịch và chạy với `g++ -std=c++17 -pthread`, thoát mã 0, trong 5 giây. Khối cố ý minh họa hành vi không xác định (UB) bắt đầu bằng dòng đầu tiên `// bo-qua-kiem-tra` và bị bỏ qua.
- Mỗi bài có đúng **8 khối** theo thứ tự trong "Khuôn bài" bên dưới; trắc nghiệm 6–8 câu, mỗi câu 3–4 lựa chọn, đúng 1 đáp án, có giải thích; tóm tắt đúng 5 dòng đánh số.
- Truy cập `localStorage` luôn bọc `try/catch`; trang vẫn hiển thị đúng khi storage không dùng được.
- Git: danh tính commit đã được cấu hình cục bộ trong repo (không tự đổi). Mỗi commit kết thúc bằng dòng `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Thông điệp commit bằng tiếng Việt.
- Push chỉ ở Task 9 (sau khi cả nhóm 1 xong và mọi kiểm tra xanh).

### Khuôn bài

Mọi file bài `docs/nhom-N-.../NN-ten-bai.md` có đúng cấu trúc này (checker ở Task 3 sẽ kiểm tra):

````markdown
# Bài N — Tên bài

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Mục tiêu 1
    - Mục tiêu 2
    - Mục tiêu 3

## 🧠 Câu chuyện mở đầu

(phép ẩn dụ đời thường)

## 📖 Giải thích

(các ý chính, thuật ngữ in đậm kèm nghĩa tiếng Việt)

## 💻 Ví dụ code

(các khối ```cpp, mỗi khối là chương trình đầy đủ có main)

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "Câu hỏi 1?"
    Gợi ý trả lời.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: ..."
    Giải thích.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="01" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Nội dung câu hỏi?

- Lựa chọn 1
- Lựa chọn 2
- Lựa chọn 3

<p class="giai-thich" markdown>Vì sao lựa chọn 2 đúng, và vì sao các lựa chọn kia sai.</p>
</div>

(… 6–8 khối cau-hoi …)

</div>

## 🔑 Tóm tắt

1. Dòng 1
2. Dòng 2
3. Dòng 3
4. Dòng 4
5. Dòng 5
````

Ghi chú cú pháp đã kiểm chứng: `data-bai` và `data-dap-an` đi qua `md_in_html` nguyên vẹn; cú pháp `{ .dung }` trên dòng lựa chọn **không** hoạt động nên không dùng. `data-bai` là số bài hai chữ số (`"01"`…`"05"`).

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `requirements.txt`, `.gitignore`, `README.md` | Khởi tạo repo |
| `mkdocs.yml` | Cấu hình site, nav, loại `docs/superpowers/` khỏi site |
| `docs/index.md`, `docs/glossary.md`, `docs/tien-do.md` | Trang chủ, thuật ngữ, tiến độ |
| `docs/stylesheets/quiz.css`, `docs/javascripts/quiz.js` | Giao diện và logic trắc nghiệm |
| `docs/nhom-1-nen-tang-bo-nho/01…05-*.md` | 5 bài nhóm 1 |
| `scripts/kiem_cau_truc.py`, `tests/test_kiem_cau_truc.py` | Kiểm tra khuôn bài và quiz |
| `scripts/kiem_code.py`, `tests/test_kiem_code.py` | Biên dịch và chạy khối code C++ |
| `.github/workflows/ci.yml` | Kiểm tra mọi push/PR; deploy khi push `main` |

---

### Task 1: Khung site MkDocs

**Files:**
- Create: `.gitignore`, `requirements.txt`, `README.md`, `mkdocs.yml`, `docs/index.md`, `docs/glossary.md`

**Interfaces:**
- Produces: site build được bằng `mkdocs build --strict`; `mkdocs.yml` có khóa `nav` (danh sách) mà các task sau thêm mục vào; `docs/glossary.md` là một bảng Markdown mà các task bài thêm dòng vào cuối.

- [ ] **Step 1: Tạo `.gitignore` và `requirements.txt`**

`.gitignore`:
```
site/
.venv/
__pycache__/
*.pyc
```

`requirements.txt`:
```
mkdocs-material==9.5.39
```

- [ ] **Step 2: Tạo `mkdocs.yml`**

```yaml
site_name: C++ phỏng vấn — ôn nhanh
site_description: >-
  Khóa ôn C++ ngắn hạn để đi phỏng vấn — giải thích để học sinh lớp 5 cũng hiểu,
  mỗi bài có trắc nghiệm tương tác.
site_url: https://hungnguyen010518.github.io/cpp-interview-short-term/
repo_url: https://github.com/hungnguyen010518/cpp-interview-short-term
repo_name: cpp-interview-short-term
edit_uri: edit/main/docs/
exclude_docs: |
  superpowers/

theme:
  name: material
  language: vi
  icon:
    logo: material/language-cpp
    repo: fontawesome/brands/github
  features:
    - navigation.sections
    - navigation.top
    - navigation.footer
    - toc.follow
    - content.code.copy
    - search.highlight
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-night
        name: Chuyển sang chế độ tối
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-sunny
        name: Chuyển sang chế độ sáng

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
      toc_depth: 3
  - pymdownx.details
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.superfences

plugins:
  - search:
      lang:
        - vi
        - en

nav:
  - Trang chủ: index.md
  - Bảng thuật ngữ: glossary.md
```

- [ ] **Step 3: Tạo `docs/index.md`**

```markdown
# C++ phỏng vấn — ôn nhanh

Chào bạn! Đây là khóa ôn C++ trong **chưa đầy hai tuần** để đi phỏng vấn.

Mỗi bài được viết như kể chuyện: bắt đầu bằng một ví dụ đời thường (cái bàn học,
cái kho đồ, thư viện...) rồi mới tới tên gọi của các khái niệm. Học sinh lớp 5 đọc cũng hiểu.

## Một bài học gồm gì?

1. 🎯 Mục tiêu bài
2. 🧠 Câu chuyện mở đầu
3. 📖 Giải thích
4. 💻 Ví dụ code (chạy được thật)
5. 🎤 Câu hỏi phỏng vấn hay gặp, có gợi ý trả lời
6. ⚠️ Lỗi thường gặp
7. ✍️ Trắc nghiệm: chọn xong thấy đúng sai ngay, kèm giải thích
8. 🔑 Tóm tắt năm dòng

## Học theo thứ tự nào?

Nhóm 1 — Nền tảng và bộ nhớ đang có sẵn. Các nhóm sau (STL, đa luồng, OOP, hệ thống)
sẽ được thêm dần.

Điểm trắc nghiệm của bạn được lưu **ngay trong trình duyệt này** (không gửi đi đâu cả).
Xem bạn đang yếu bài nào ở trang [Tiến độ](tien-do.md).
```

Trang này liên kết tới `tien-do.md`; file đó được tạo ở Step 4 (bản tạm) nên chỉ build sau Step 4.

- [ ] **Step 4: Tạo `docs/glossary.md` và file tạm `docs/tien-do.md`**

`docs/glossary.md`:
```markdown
# Bảng thuật ngữ

Thuật ngữ được thêm vào đây ở cuối mỗi bài.

| Thuật ngữ | Nghĩa dễ hiểu | Bài |
|---|---|---|
```

`docs/tien-do.md` (bản tạm, Task 2 sẽ viết lại hoàn chỉnh):
```markdown
# Tiến độ

Trang này sẽ được hoàn thiện ở bước sau.
```

Thêm vào `nav` trong `mkdocs.yml`, ngay sau "Trang chủ":
```yaml
  - Tiến độ của bạn: tien-do.md
```

- [ ] **Step 5: Tạo `README.md`**

```markdown
# C++ phỏng vấn — ôn nhanh

Khóa ôn C++ ngắn hạn để đi phỏng vấn, mỗi bài có trắc nghiệm tương tác.

Web: https://hungnguyen010518.github.io/cpp-interview-short-term/

## Chạy ở máy

    pip install -r requirements.txt
    mkdocs serve

## Kiểm tra trước khi push

    python3 -m unittest discover -s tests -v
    python3 scripts/kiem_cau_truc.py
    python3 scripts/kiem_code.py
    mkdocs build --strict
```

- [ ] **Step 6: Build kiểm tra**

Run: `cd /home/user/cpp-interview-short-term && mkdocs build --strict`
Expected: kết thúc không có `WARNING`/`ERROR`, thư mục `site/` được tạo, `site/index.html` tồn tại, và **không có** thư mục `site/superpowers/`.

Run: `ls site/superpowers 2>&1 | head -1`
Expected: `ls: cannot access 'site/superpowers': No such file or directory`

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt README.md mkdocs.yml docs/index.md docs/glossary.md docs/tien-do.md
git commit -m "feat: khung site MkDocs Material, trang chủ và bảng thuật ngữ

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Bộ trắc nghiệm tương tác và trang Tiến độ

**Files:**
- Create: `docs/stylesheets/quiz.css`, `docs/javascripts/quiz.js`, `docs/mau-trac-nghiem.md` (trang mẫu tạm, xóa ở Task 4)
- Modify: `mkdocs.yml` (thêm `extra_css`, `extra_javascript`, nav mẫu), `docs/tien-do.md` (viết lại)

**Interfaces:**
- Consumes: markup quiz đã định nghĩa trong "Khuôn bài" (`.quiz[data-bai]`, `.cau-hoi[data-dap-an]`, `ul > li`, `.giai-thich`).
- Produces: `localStorage` khóa `cpp-interview-short-term:diem:<NN>` giá trị JSON `{"diem": số, "tong": số}`; các phần tử `<span class="diem" data-bai="NN">` ở bất kỳ trang nào được JS điền "X/Y" hoặc "chưa làm". Task 4–8 thêm một dòng bảng vào `docs/tien-do.md` cho mỗi bài theo đúng mẫu `<span class="diem" data-bai="NN"></span>`.

- [ ] **Step 1: Tạo `docs/stylesheets/quiz.css`**

```css
.quiz { margin: 1.5em 0; }

.quiz .cau-hoi {
  border: 1px solid var(--md-default-fg-color--lightest);
  border-radius: 0.4rem;
  padding: 0.8rem 1rem;
  margin-bottom: 1rem;
}

.quiz .cau-hoi ul { list-style: none; margin: 0.5rem 0; padding: 0; }

.quiz .cau-hoi li {
  margin: 0.35rem 0;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--md-default-fg-color--lighter);
  border-radius: 0.3rem;
  cursor: pointer;
}

.quiz .cau-hoi li:hover,
.quiz .cau-hoi li:focus-visible {
  border-color: var(--md-accent-fg-color);
  outline: none;
}

.quiz .cau-hoi.da-tra-loi li { cursor: default; }

.quiz li.chon-dung,
.quiz li.la-dap-an {
  border-color: #2e9e4f;
  background: rgba(46, 158, 79, 0.15);
}
.quiz li.chon-dung::before,
.quiz li.la-dap-an::before { content: "✓ "; font-weight: 700; }

.quiz li.chon-sai {
  border-color: #d64545;
  background: rgba(214, 69, 69, 0.15);
}
.quiz li.chon-sai::before { content: "✗ "; font-weight: 700; }

.quiz .giai-thich {
  display: none;
  margin: 0.5rem 0 0;
  padding: 0.5rem 0.7rem;
  border-left: 4px solid var(--md-accent-fg-color);
  background: var(--md-code-bg-color);
}
.quiz .giai-thich.hien { display: block; }

.quiz .quiz-ket-qua { margin-top: 1rem; }

.diem { font-weight: 600; }
.diem.yeu { color: #d64545; }
```

- [ ] **Step 2: Tạo `docs/javascripts/quiz.js`**

```javascript
(function () {
  "use strict";

  var TIEN_TO = "cpp-interview-short-term:diem:";

  function luuDiem(bai, diem, tong) {
    try {
      localStorage.setItem(TIEN_TO + bai, JSON.stringify({ diem: diem, tong: tong }));
    } catch (e) {
      /* không lưu được thì thôi, trang vẫn dùng được */
    }
  }

  function docDiem(bai) {
    try {
      var v = localStorage.getItem(TIEN_TO + bai);
      return v ? JSON.parse(v) : null;
    } catch (e) {
      return null;
    }
  }

  function moTa(d) {
    return d ? d.diem + "/" + d.tong : "chưa làm";
  }

  function khoiTaoQuiz(quiz) {
    if (quiz.getAttribute("data-khoi-tao") === "1") return;
    quiz.setAttribute("data-khoi-tao", "1");

    var bai = quiz.getAttribute("data-bai");
    var cauHoi = Array.prototype.slice.call(quiz.querySelectorAll(".cau-hoi"));
    var ketQua = document.createElement("div");
    ketQua.className = "quiz-ket-qua";
    quiz.appendChild(ketQua);
    var diem = 0;
    var daTraLoi = 0;

    function capNhatKetQua() {
      ketQua.innerHTML = "";
      var p = document.createElement("p");
      if (daTraLoi === cauHoi.length) {
        p.textContent = "Bạn đúng " + diem + "/" + cauHoi.length + " câu.";
      } else {
        var truoc = docDiem(bai);
        p.textContent = truoc
          ? "Lần làm trước: " + moTa(truoc)
          : "Chọn một đáp án cho mỗi câu.";
      }
      ketQua.appendChild(p);
      if (daTraLoi > 0) {
        var nut = document.createElement("button");
        nut.type = "button";
        nut.className = "md-button";
        nut.textContent = "Làm lại";
        nut.addEventListener("click", lamLai);
        ketQua.appendChild(nut);
      }
    }

    function lamLai() {
      diem = 0;
      daTraLoi = 0;
      cauHoi.forEach(function (ch) {
        ch.classList.remove("da-tra-loi");
        ch.querySelectorAll("li").forEach(function (li) {
          li.classList.remove("chon-dung", "chon-sai", "la-dap-an");
        });
        var gt = ch.querySelector(".giai-thich");
        if (gt) gt.classList.remove("hien");
      });
      capNhatKetQua();
    }

    cauHoi.forEach(function (ch) {
      var dapAn = parseInt(ch.getAttribute("data-dap-an"), 10);
      var luaChon = Array.prototype.slice.call(ch.querySelectorAll("ul > li"));
      var giaiThich = ch.querySelector(".giai-thich");

      luaChon.forEach(function (li, i) {
        function chon() {
          if (ch.classList.contains("da-tra-loi")) return;
          ch.classList.add("da-tra-loi");
          daTraLoi += 1;
          var dung = i + 1 === dapAn;
          if (dung) diem += 1;
          li.classList.add(dung ? "chon-dung" : "chon-sai");
          if (luaChon[dapAn - 1]) luaChon[dapAn - 1].classList.add("la-dap-an");
          if (giaiThich) giaiThich.classList.add("hien");
          if (daTraLoi === cauHoi.length) luuDiem(bai, diem, cauHoi.length);
          capNhatKetQua();
        }
        li.setAttribute("tabindex", "0");
        li.setAttribute("role", "button");
        li.addEventListener("click", chon);
        li.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            chon();
          }
        });
      });
    });

    capNhatKetQua();
  }

  function dienTienDo() {
    document.querySelectorAll(".diem[data-bai]").forEach(function (el) {
      var d = docDiem(el.getAttribute("data-bai"));
      el.textContent = moTa(d);
      el.classList.toggle("yeu", !!d && d.diem / d.tong < 0.7);
    });
  }

  function chay() {
    document.querySelectorAll(".quiz").forEach(khoiTaoQuiz);
    dienTienDo();
  }

  if (window.document$ && window.document$.subscribe) {
    window.document$.subscribe(chay);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", chay);
  } else {
    chay();
  }
})();
```

- [ ] **Step 3: Viết `docs/tien-do.md`**

```markdown
# Tiến độ của bạn

Điểm trắc nghiệm được lưu trong trình duyệt này. Bài nào **dưới 70%** hiện màu đỏ: nên ôn lại.

| Bài | Điểm gần nhất |
|---|---|
```

(Các bài thêm dòng ở Task 4–8, mẫu: `| [Bài 1 — Tên bài](nhom-1-nen-tang-bo-nho/01-ten-file.md) | <span class="diem" data-bai="01"></span> |`.)

- [ ] **Step 4: Tạo trang mẫu tạm `docs/mau-trac-nghiem.md`**

```markdown
# Mẫu trắc nghiệm (tạm)

<div class="quiz" data-bai="99" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Con trỏ giống thứ gì nhất?

- Một cái hộp đựng số
- Một tờ giấy ghi địa chỉ nhà
- Một chiếc xe đạp

<p class="giai-thich" markdown>Con trỏ giữ **địa chỉ**, giống tờ giấy ghi số nhà.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Biến cục bộ nằm ở đâu?

- Stack
- Heap
- Ổ cứng

<p class="giai-thich" markdown>Biến cục bộ nằm trên **stack**, hết hàm là tự dọn.</p>
</div>

</div>

Điểm của bài mẫu: <span class="diem" data-bai="99"></span>
```

- [ ] **Step 5: Nối CSS/JS và trang mẫu vào `mkdocs.yml`**

Thêm (cùng cấp với `plugins:`):
```yaml
extra_css:
  - stylesheets/quiz.css

extra_javascript:
  - javascripts/quiz.js
```
Và thêm vào cuối `nav`:
```yaml
  - Mẫu trắc nghiệm (tạm): mau-trac-nghiem.md
```

- [ ] **Step 6: Build kiểm tra**

Run: `mkdocs build --strict`
Expected: không có `WARNING`/`ERROR`; `site/javascripts/quiz.js` và `site/stylesheets/quiz.css` tồn tại.

- [ ] **Step 7: Kiểm tra bằng tay trong trình duyệt** (không có công cụ tự động cho JS ở máy này)

Run: `mkdocs serve -a 127.0.0.1:8000` rồi mở `http://127.0.0.1:8000/mau-trac-nghiem/`.
Expected, kiểm lần lượt:
1. Hai câu hỏi hiện đủ lựa chọn; chưa thấy phần giải thích; dòng dưới cùng ghi "Chọn một đáp án cho mỗi câu."
2. Bấm đáp án đúng ở câu 1: lựa chọn đó viền xanh có dấu ✓, giải thích hiện ra; bấm lựa chọn khác trong cùng câu không đổi được gì.
3. Câu 2 bấm đáp án sai: lựa chọn đã bấm đỏ có dấu ✗, đáp án đúng cũng được tô xanh ✓.
4. Trả lời hết: dòng kết quả ghi "Bạn đúng 1/2 câu." và có nút "Làm lại".
5. Bấm "Làm lại": mọi màu và giải thích biến mất, làm lại được.
6. Tải lại trang: dòng kết quả ghi "Lần làm trước: 1/2"; dòng "Điểm của bài mẫu" ghi `1/2` (màu đỏ vì dưới 70%).
7. Dùng phím Tab đến một lựa chọn và nhấn Enter: chọn được như khi bấm chuột.
8. Chuyển sang chế độ tối bằng nút ở đầu trang: màu vẫn đọc rõ.
Tắt server bằng Ctrl+C. Nếu mục nào không đạt, sửa `quiz.js`/`quiz.css` rồi kiểm lại.

- [ ] **Step 8: Commit**

```bash
git add docs/stylesheets/quiz.css docs/javascripts/quiz.js docs/mau-trac-nghiem.md docs/tien-do.md mkdocs.yml
git commit -m "feat: trắc nghiệm tương tác chấm điểm, lưu điểm trong trình duyệt, trang Tiến độ

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Công cụ kiểm tra tự động và CI

**Files:**
- Create: `scripts/kiem_cau_truc.py`, `scripts/kiem_code.py`, `tests/test_kiem_cau_truc.py`, `tests/test_kiem_code.py`, `.github/workflows/ci.yml`

**Interfaces:**
- Produces:
  - `kiem_cau_truc.kiem_bai(ten: str, text: str) -> list[str]` (danh sách thông báo lỗi, rỗng nếu hợp lệ); CLI `python3 scripts/kiem_cau_truc.py [thu_muc_docs]` quét `nhom-*/*.md`, in lỗi, thoát mã 1 nếu có lỗi.
  - `kiem_code.lay_khoi(text: str) -> list[tuple[int, str]]` (số dòng, code đã bỏ thụt lề); `kiem_code.kiem_khoi(code: str) -> str | None` (None nếu ổn); `kiem_code.kiem_file(duong: pathlib.Path) -> list[str]`; CLI `python3 scripts/kiem_code.py [thu_muc_docs]`.

- [ ] **Step 1: Viết test cho `kiem_cau_truc` (sẽ thất bại)**

`tests/test_kiem_cau_truc.py`:
```python
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import kiem_cau_truc as k  # noqa: E402

HEADING = ["## 🧠 Câu chuyện", "## 📖 Giải thích", "## 💻 Ví dụ",
           "## 🎤 Phỏng vấn", "## ⚠️ Lỗi", "## ✍️ Trắc nghiệm", "## 🔑 Tóm tắt"]


def cau(dap_an=1, so_lua_chon=3, so_giai_thich=1):
    lua = "\n".join(f"- Lựa chọn {i}" for i in range(1, so_lua_chon + 1))
    gt = '<p class="giai-thich" markdown>Vì sao.</p>\n' * so_giai_thich
    return (f'<div class="cau-hoi" data-dap-an="{dap_an}" markdown>\n'
            f"**Câu.** Hỏi gì đó?\n\n{lua}\n\n{gt}</div>\n")


def bai(so_cau=6, so_dong_tom_tat=5, heading=None, cau_dau=None):
    heading = HEADING if heading is None else heading
    out = '# Bài 1\n\n!!! abstract "🎯 Học xong bài này, bạn sẽ"\n    - Một\n'
    for h in heading:
        out += f"\n{h}\n\n"
        if "Trắc nghiệm" in h:
            cac_cau = [cau_dau or cau()] + [cau() for _ in range(so_cau - 1)]
            out += '<div class="quiz" data-bai="01" markdown>\n\n'
            out += "\n".join(cac_cau) + "\n</div>\n"
        elif "Tóm tắt" in h:
            out += "\n".join(f"{i}. Dòng {i}" for i in range(1, so_dong_tom_tat + 1)) + "\n"
    return out


class TestKiemBai(unittest.TestCase):
    def test_bai_hop_le_khong_loi(self):
        self.assertEqual(k.kiem_bai("b.md", bai()), [])

    def test_thieu_heading(self):
        h = [x for x in HEADING if "🎤" not in x]
        loi = k.kiem_bai("b.md", bai(heading=h))
        self.assertTrue(any("🎤" in l for l in loi), loi)

    def test_sai_thu_tu_heading(self):
        h = HEADING[:]
        h[0], h[1] = h[1], h[0]
        loi = k.kiem_bai("b.md", bai(heading=h))
        self.assertTrue(any("thứ tự" in l for l in loi), loi)

    def test_it_hon_6_cau(self):
        loi = k.kiem_bai("b.md", bai(so_cau=5))
        self.assertTrue(any("6–8" in l for l in loi), loi)

    def test_dap_an_ngoai_khoang(self):
        loi = k.kiem_bai("b.md", bai(cau_dau=cau(dap_an=4, so_lua_chon=3)))
        self.assertTrue(any("ngoài" in l for l in loi), loi)

    def test_thieu_giai_thich(self):
        loi = k.kiem_bai("b.md", bai(cau_dau=cau(so_giai_thich=0)))
        self.assertTrue(any("giai-thich" in l for l in loi), loi)

    def test_qua_it_lua_chon(self):
        loi = k.kiem_bai("b.md", bai(cau_dau=cau(so_lua_chon=2)))
        self.assertTrue(any("lựa chọn" in l for l in loi), loi)

    def test_tom_tat_4_dong(self):
        loi = k.kiem_bai("b.md", bai(so_dong_tom_tat=4))
        self.assertTrue(any("5 dòng" in l for l in loi), loi)

    def test_khoi_cau_hoi_sai_cu_phap(self):
        text = bai().replace('data-dap-an="1" markdown>', 'markdown data-dap-an="1">', 1)
        loi = k.kiem_bai("b.md", text)
        self.assertTrue(any("sai cú pháp" in l for l in loi), loi)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

Run: `python3 -m unittest tests.test_kiem_cau_truc -v`
Expected: lỗi `ModuleNotFoundError: No module named 'kiem_cau_truc'`.

- [ ] **Step 3: Viết `scripts/kiem_cau_truc.py`**

```python
#!/usr/bin/env python3
"""Kiểm tra cấu trúc bài học — những lỗi mà `mkdocs build --strict` KHÔNG bắt được.

1. Có khối mục tiêu và đủ 7 heading emoji theo đúng thứ tự.
2. Đúng một khối <div class="quiz">, 6–8 câu; mỗi câu có 3–4 lựa chọn,
   data-dap-an nằm trong 1..số lựa chọn, đúng một <p class="giai-thich">.
3. Khối 🔑 Tóm tắt có đúng 5 dòng đánh số.

Dùng:  python3 scripts/kiem_cau_truc.py [thu_muc_docs]
Thoát mã 1 nếu có lỗi.
"""
import pathlib
import re
import sys

MUC_TIEU = '!!! abstract "🎯 Học xong bài này, bạn sẽ"'
HEADING = ["## 🧠", "## 📖", "## 💻", "## 🎤", "## ⚠️", "## ✍️", "## 🔑"]
CAU_HOI = re.compile(
    r'<div class="cau-hoi" data-dap-an="(\d+)" markdown>(.*?)</div>', re.S)
LUA_CHON = re.compile(r"^- \S", re.M)
DONG_SO = re.compile(r"^\d+\. \S", re.M)


def kiem_quiz(ten: str, text: str) -> list:
    n_quiz = text.count('<div class="quiz"')
    if n_quiz != 1:
        return [f"{ten}: cần đúng 1 khối quiz, đang có {n_quiz}"]
    loi = []
    cau = CAU_HOI.findall(text)
    if text.count('<div class="cau-hoi"') != len(cau):
        loi.append(f"{ten}: có khối cau-hoi sai cú pháp (đúng: "
                   '<div class="cau-hoi" data-dap-an="N" markdown>)')
    if not 6 <= len(cau) <= 8:
        loi.append(f"{ten}: quiz cần 6–8 câu, đang có {len(cau)}")
    for k, (dap_an, noi_dung) in enumerate(cau, 1):
        so = len(LUA_CHON.findall(noi_dung))
        if not 3 <= so <= 4:
            loi.append(f"{ten}: câu {k} có {so} lựa chọn (cần 3–4)")
        elif not 1 <= int(dap_an) <= so:
            loi.append(f"{ten}: câu {k} có data-dap-an={dap_an} ngoài 1..{so}")
        if noi_dung.count('<p class="giai-thich"') != 1:
            loi.append(f"{ten}: câu {k} cần đúng 1 khối giai-thich")
    return loi


def kiem_tom_tat(ten: str, text: str) -> list:
    i = text.find("\n## 🔑")
    if i < 0:
        return []  # đã báo thiếu heading ở kiem_bai
    phan = text[i + 1:]
    j = phan.find("\n## ", 1)
    if j >= 0:
        phan = phan[:j]
    n = len(DONG_SO.findall(phan))
    return [] if n == 5 else [f"{ten}: tóm tắt cần đúng 5 dòng đánh số, đang có {n}"]


def kiem_bai(ten: str, text: str) -> list:
    loi = []
    if MUC_TIEU not in text:
        loi.append(f"{ten}: thiếu khối mục tiêu {MUC_TIEU!r}")
    vi_tri = []
    for h in HEADING:
        i = text.find("\n" + h)
        if i < 0:
            loi.append(f"{ten}: thiếu heading {h!r}")
        vi_tri.append(i)
    if all(v >= 0 for v in vi_tri) and vi_tri != sorted(vi_tri):
        loi.append(f"{ten}: các heading không đúng thứ tự")
    loi += kiem_quiz(ten, text)
    loi += kiem_tom_tat(ten, text)
    return loi


def main(argv: list) -> int:
    goc = pathlib.Path(argv[1] if len(argv) > 1 else "docs")
    loi = []
    for f in sorted(goc.glob("nhom-*/*.md")):
        loi += kiem_bai(str(f), f.read_text(encoding="utf-8"))
    for dong in loi:
        print(dong)
    print(f"{len(loi)} lỗi cấu trúc")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Chạy test, xác nhận đạt**

Run: `python3 -m unittest tests.test_kiem_cau_truc -v`
Expected: 9 test, tất cả `ok`.

- [ ] **Step 5: Viết test cho `kiem_code` (sẽ thất bại)**

`tests/test_kiem_code.py`:
```python
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import kiem_code as k  # noqa: E402

CHUONG_TRINH_TOT = '#include <iostream>\nint main() { std::cout << "ok\\n"; return 0; }\n'


def md(code: str, thut: str = "") -> str:
    dong = ["```cpp"] + code.rstrip("\n").split("\n") + ["```"]
    return "Văn bản\n\n" + "\n".join(thut + d for d in dong) + "\n"


class TestLayKhoi(unittest.TestCase):
    def test_bo_thut_le_khoi_long_trong_hop(self):
        khoi = k.lay_khoi(md(CHUONG_TRINH_TOT, thut="    "))
        self.assertEqual(len(khoi), 1)
        self.assertTrue(khoi[0][1].startswith("#include <iostream>"))
        self.assertEqual(khoi[0][0], 3)  # dòng chứa ```cpp

    def test_khong_lay_khoi_khac_ngon_ngu(self):
        self.assertEqual(k.lay_khoi("```bash\nls\n```\n"), [])


class TestKiemKhoi(unittest.TestCase):
    def test_chuong_trinh_tot(self):
        self.assertIsNone(k.kiem_khoi(CHUONG_TRINH_TOT))

    def test_loi_bien_dich(self):
        self.assertIn("biên dịch", k.kiem_khoi("int main() { return x; }"))

    def test_chay_tra_ma_khac_0(self):
        self.assertIn("mã 1", k.kiem_khoi("int main() { return 1; }"))

    def test_bo_qua_khoi_danh_dau(self):
        self.assertIsNone(k.kiem_khoi("// bo-qua-kiem-tra\nthis is not c++"))


class TestKiemFile(unittest.TestCase):
    def test_bao_so_dong_cua_khoi_loi(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "b.md"
            p.write_text(md("int main() { return x; }"), encoding="utf-8")
            loi = k.kiem_file(p)
        self.assertEqual(len(loi), 1)
        self.assertIn("b.md:3", loi[0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Chạy test, xác nhận thất bại**

Run: `python3 -m unittest tests.test_kiem_code -v`
Expected: `ModuleNotFoundError: No module named 'kiem_code'`.

- [ ] **Step 7: Viết `scripts/kiem_code.py`**

```python
#!/usr/bin/env python3
"""Biên dịch và chạy mọi khối ```cpp trong các bài học.

Mỗi khối là một chương trình đầy đủ: phải biên dịch được với
`g++ -std=c++17 -Wall -pthread`, chạy dưới 5 giây và thoát mã 0.
Khối có dòng đầu tiên `// bo-qua-kiem-tra` (minh họa hành vi không xác định)
được bỏ qua.

Dùng:  python3 scripts/kiem_code.py [thu_muc_docs]
Thoát mã 1 nếu có khối lỗi.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

BO_QUA = "// bo-qua-kiem-tra"
KHOI = re.compile(
    r"^(?P<thut>[ \t]*)```cpp[ \t]*\n(?P<code>.*?)^(?P=thut)```[ \t]*$",
    re.S | re.M)


def lay_khoi(text: str) -> list:
    """Trả về [(số dòng chứa ```cpp, code đã bỏ thụt lề)]."""
    ket_qua = []
    for m in KHOI.finditer(text):
        thut = m.group("thut")
        dong_code = [d[len(thut):] if d.startswith(thut) else d
                     for d in m.group("code").split("\n")]
        so_dong = text.count("\n", 0, m.start()) + 1
        ket_qua.append((so_dong, "\n".join(dong_code)))
    return ket_qua


def kiem_khoi(code: str):
    """Trả về None nếu ổn, ngược lại là thông báo lỗi."""
    if code.lstrip().startswith(BO_QUA):
        return None
    with tempfile.TemporaryDirectory() as d:
        nguon = pathlib.Path(d) / "a.cpp"
        chay = pathlib.Path(d) / "a.out"
        nguon.write_text(code, encoding="utf-8")
        bd = subprocess.run(
            ["g++", "-std=c++17", "-Wall", "-pthread", "-o", str(chay), str(nguon)],
            capture_output=True, text=True)
        if bd.returncode != 0:
            return "biên dịch lỗi:\n" + bd.stderr
        try:
            kq = subprocess.run([str(chay)], capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            return "chạy quá 5 giây"
        if kq.returncode != 0:
            return f"chạy trả mã {kq.returncode}\n{kq.stderr}"
    return None


def kiem_file(duong: pathlib.Path) -> list:
    loi = []
    for so_dong, code in lay_khoi(duong.read_text(encoding="utf-8")):
        ket_qua = kiem_khoi(code)
        if ket_qua:
            loi.append(f"{duong}:{so_dong}: {ket_qua}")
    return loi


def main(argv: list) -> int:
    goc = pathlib.Path(argv[1] if len(argv) > 1 else "docs")
    loi = []
    n_khoi = 0
    for f in sorted(goc.glob("nhom-*/*.md")):
        n_khoi += len(lay_khoi(f.read_text(encoding="utf-8")))
        loi += kiem_file(f)
    for dong in loi:
        print(dong)
    print(f"{n_khoi} khối code, {len(loi)} lỗi")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 8: Chạy toàn bộ test, xác nhận đạt**

Run: `python3 -m unittest discover -s tests -v`
Expected: 16 test (9 + 7), tất cả `ok`.

Run: `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py`
Expected: `0 lỗi cấu trúc` và `0 khối code, 0 lỗi` (chưa có thư mục `nhom-*`), mã thoát 0.

- [ ] **Step 9: Tạo `.github/workflows/ci.yml`**

```yaml
name: CI và deploy

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  kiem-tra:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: python3 -m unittest discover -s tests -v
      - run: python3 scripts/kiem_cau_truc.py
      - run: python3 scripts/kiem_code.py
      - run: mkdocs build --strict

  deploy:
    needs: kiem-tra
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
      - run: mkdocs gh-deploy --force
```

- [ ] **Step 10: Commit**

```bash
git add scripts tests .github
git commit -m "feat: công cụ kiểm tra khuôn bài, trắc nghiệm, biên dịch code C++ và CI

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Bài 1 — Stack, heap, con trỏ, tham chiếu, const

**Files:**
- Create: `docs/nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md`
- Modify: `mkdocs.yml` (nav, xóa mục mẫu tạm), `docs/glossary.md`, `docs/tien-do.md`
- Delete: `docs/mau-trac-nghiem.md`

**Interfaces:**
- Consumes: Khuôn bài (Global Constraints); `data-bai="01"`.
- Produces: mục nav nhóm 1 mà Task 5–8 thêm tiếp theo cùng cấp; dòng bảng glossary và tiến độ làm mẫu cho các task sau.

Nội dung bài (viết theo Khuôn bài, văn phong lớp 5):

**🎯 Mục tiêu:** (1) Giải thích được stack và heap khác nhau thế nào bằng hình ảnh bàn học và kho đồ. (2) Phân biệt con trỏ và tham chiếu. (3) Đọc đúng `const int*` và `int* const`.

**🧠 Câu chuyện:** Bạn học ở lớp. *Cái bàn học* của bạn nhỏ, để đồ lên lấy rất nhanh, hết giờ thì cô tự dọn sạch: đó là **stack (ngăn xếp)**. *Kho đồ của trường* rộng, để được cả đồ to, nhưng phải xin chìa, ghi sổ và **tự nhớ trả**; quên trả thì kho đầy dần: đó là **heap (vùng nhớ cấp phát động)**. Tờ giấy ghi "đồ của em ở phòng 12" là **con trỏ (pointer)**. Biệt danh "Tí" của bạn Nguyễn Văn An là **tham chiếu (reference)**: vẫn cùng một người. Nhãn dán "Chỉ được xem, không được sửa" là **const**.

**📖 Giải thích (các ý bắt buộc):**
- Stack: biến cục bộ, tự giải phóng khi ra khỏi hàm, rất nhanh, dung lượng nhỏ (thường vài MB).
- Heap: cấp phát bằng `new`, giải phóng bằng `delete`, tồn tại đến khi bạn trả, chậm hơn, rộng hơn.
- Con trỏ: lưu địa chỉ; có thể bằng `nullptr`; có thể trỏ sang nơi khác. Tham chiếu: bí danh; phải gán ngay khi khai báo; không null; không đổi đối tượng.
- `const int* p`: không sửa được giá trị qua `p`. `int* const p`: không đổi được chỗ `p` trỏ. Mẹo đọc: từ phải sang trái.
- Truyền đối tượng lớn bằng `const T&`: không sao chép mà vẫn không bị sửa.

**💻 Ví dụ code (hai khối, chạy được):**

```cpp
#include <iostream>

int main() {
    int ban = 5;                 // nằm trên stack (cái bàn học)
    int* kho = new int(7);       // nằm trên heap (kho đồ)
    std::cout << ban << " " << *kho << "\n";
    delete kho;                  // trả đồ về kho
    return 0;
}
```
Kết quả in ra: `5 7`.

```cpp
#include <iostream>

void tang(int& x) { x += 1; }                       // tham chiếu: sửa thẳng bản gốc
void chiXem(const int& x) { std::cout << x << "\n"; }

int main() {
    int a = 10;
    int* p = &a;      // p giữ địa chỉ của a
    *p = 20;          // đi theo địa chỉ, sửa a
    int& b = a;       // b là biệt danh của a
    b = 30;
    tang(a);
    chiXem(a);        // in 31
    return 0;
}
```
Kết quả in ra: `31`.

**🎤 Câu hỏi phỏng vấn (4 câu + gợi ý):**
1. *Stack khác heap thế nào?* — Khác vòng đời (stack tự giải phóng khi hết phạm vi, heap tồn tại đến khi giải phóng), tốc độ (stack nhanh hơn), kích thước (stack nhỏ, heap lớn), người quản lý (trình biên dịch với lập trình viên).
2. *Con trỏ khác tham chiếu thế nào?* — Con trỏ có thể null và đổi chỗ trỏ, cần giải tham chiếu `*p`; tham chiếu phải gắn ngay khi khai báo, không null, không đổi, dùng như chính đối tượng.
3. *Phân biệt `const int* p`, `int* const p`, `const int* const p`.* — Đọc từ phải sang trái: con trỏ tới int hằng; con trỏ hằng tới int; con trỏ hằng tới int hằng.
4. *Vì sao truyền đối tượng lớn bằng `const T&`?* — Tránh chi phí sao chép, đồng thời cam kết hàm không sửa đối tượng.

**⚠️ Lỗi thường gặp (3 hộp `warning`):**
- Trả về con trỏ/tham chiếu tới biến cục bộ (kèm khối `// bo-qua-kiem-tra`):
```cpp
// bo-qua-kiem-tra
int* hamLoi() {
    int x = 5;
    return &x;   // x bị dọn khi hàm kết thúc → địa chỉ trỏ vào chỗ trống
}
```
- `new` mà quên `delete` (rò rỉ bộ nhớ, bài 5 nói kỹ).
- Dùng con trỏ chưa gán giá trị hoặc đang là `nullptr` (luôn khởi tạo con trỏ; kiểm tra null trước khi dùng).

**✍️ Trắc nghiệm (6 câu, `data-bai="01"`):**

| # | Câu hỏi | Lựa chọn | Đáp án | Giải thích |
|---|---|---|---|---|
| 1 | Biến `int x = 5;` khai báo trong một hàm thường nằm ở đâu? | 1) Stack 2) Heap 3) Ổ cứng 4) Bên trong con trỏ | 1 | Biến cục bộ nằm trên stack và tự được dọn khi hàm kết thúc. |
| 2 | Chuyện gì xảy ra nếu `new` một vùng nhớ rồi không bao giờ `delete`? | 1) Lỗi biên dịch 2) Vùng nhớ tự trả khi hàm kết thúc 3) Rò rỉ bộ nhớ (memory leak) 4) Máy tự khởi động lại | 3 | Heap không tự dọn. Quên trả thì vùng nhớ bị chiếm mãi, gọi là rò rỉ bộ nhớ. |
| 3 | Điểm khác chính giữa tham chiếu và con trỏ là gì? | 1) Tham chiếu có thể null, con trỏ thì không 2) Tham chiếu phải gắn với một đối tượng ngay khi khai báo và không đổi sang đối tượng khác 3) Con trỏ không lưu địa chỉ 4) Hai thứ giống hệt nhau | 2 | Con trỏ mới có thể null và đổi chỗ trỏ. Tham chiếu là biệt danh gắn một lần. |
| 4 | `const int* p` có nghĩa là gì? | 1) Không đổi được p sang trỏ chỗ khác 2) Không sửa được giá trị int mà p trỏ tới (qua p) 3) p luôn bằng null 4) p nằm trên heap | 2 | Chữ `const` đứng trước `int` nên cái `int` là hằng. Muốn con trỏ không đổi chỗ thì viết `int* const`. |
| 5 | Hàm trả về địa chỉ của một biến cục bộ gây ra vấn đề gì? | 1) Không vấn đề gì 2) Con trỏ trỏ tới vùng đã bị dọn (dangling pointer), dùng sẽ sinh lỗi 3) Biến tự chuyển lên heap 4) Trình biên dịch tự sửa | 2 | Biến cục bộ mất khi hàm kết thúc; địa chỉ còn đó nhưng chỗ đó không còn thuộc về bạn. |
| 6 | Vì sao nên truyền `std::string` lớn bằng `const std::string&`? | 1) Để tránh sao chép mà hàm vẫn không sửa được chuỗi 2) Để chuỗi nằm trên heap 3) Để hàm sửa được chuỗi gốc 4) Chỉ để code ngắn hơn | 1 | Truyền tham chiếu không copy cả chuỗi; `const` cam kết không sửa. |

**🔑 Tóm tắt (5 dòng):**
1. Stack là bàn học: nhanh, nhỏ, tự dọn.
2. Heap là kho đồ: rộng, phải tự xin (`new`) và tự trả (`delete`).
3. Con trỏ là tờ giấy ghi địa chỉ, có thể null và đổi chỗ trỏ.
4. Tham chiếu là biệt danh: gắn một lần, không null, không đổi.
5. Truyền đối tượng lớn bằng `const T&` để không copy mà vẫn an toàn.

**Thuật ngữ thêm vào `docs/glossary.md`:** stack (ngăn xếp: nơi chứa biến cục bộ, tự dọn); heap (vùng nhớ cấp phát động: tự xin tự trả); con trỏ / pointer (biến giữ địa chỉ); tham chiếu / reference (biệt danh của một đối tượng); const (hằng: không được sửa); memory leak (rò rỉ bộ nhớ: xin mà không trả); dangling pointer (con trỏ treo: trỏ tới chỗ đã bị dọn). Mỗi dòng cột "Bài" là `[Bài 1](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md)`.

- [ ] **Step 1: Tạo thư mục và viết file bài** `docs/nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md` đúng nội dung trên, theo Khuôn bài (6 khối `cau-hoi`, mỗi khối theo mẫu trong Khuôn bài với `data-dap-an` lấy từ cột "Đáp án").

- [ ] **Step 2: Cập nhật nav, glossary, tiến độ; xóa trang mẫu tạm**

Trong `mkdocs.yml`: xóa dòng `  - Mẫu trắc nghiệm (tạm): mau-trac-nghiem.md`; thêm vào `nav` (trước "Bảng thuật ngữ"):
```yaml
  - "Nhóm 1 — Nền tảng và bộ nhớ":
      - "Bài 1 — Stack, heap, con trỏ, tham chiếu, const": nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md
```
Chạy `git rm docs/mau-trac-nghiem.md`. Thêm 7 dòng thuật ngữ vào cuối bảng `docs/glossary.md` và dòng sau vào cuối bảng `docs/tien-do.md`:
```markdown
| [Bài 1 — Stack, heap, con trỏ](nhom-1-nen-tang-bo-nho/01-stack-heap-con-tro.md) | <span class="diem" data-bai="01"></span> |
```

- [ ] **Step 3: Chạy mọi kiểm tra**

Run: `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`
Expected: `0 lỗi cấu trúc`; `3 khối code, 0 lỗi` (2 khối chạy + 1 khối bỏ qua đều được đếm); build sạch.

- [ ] **Step 4: Xác nhận kết quả in ra đúng như bài ghi**

Biên dịch và chạy riêng hai chương trình ví dụ (`g++ -std=c++17 file.cpp -o t && ./t`); phải in đúng `5 7` và `31`. Sửa chữ "Kết quả in ra" trong bài nếu khác.

- [ ] **Step 5: Kiểm tra bằng tay trong trình duyệt**

`mkdocs serve -a 127.0.0.1:8000`, mở bài 1: làm thử trắc nghiệm (đúng/sai/làm lại), mở trang Tiến độ thấy điểm bài 1.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: Bài 1 — stack, heap, con trỏ, tham chiếu, const; bỏ trang mẫu trắc nghiệm

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Bài 2 — RAII và smart pointer

**Files:**
- Create: `docs/nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md`
- Modify: `mkdocs.yml` (thêm vào nav nhóm 1), `docs/glossary.md`, `docs/tien-do.md`

**Interfaces:**
- Consumes: Khuôn bài; mục nav nhóm 1 từ Task 4; `data-bai="02"`.

**🎯 Mục tiêu:** (1) Giải thích RAII bằng ví dụ thư viện. (2) Chọn đúng `unique_ptr`, `shared_ptr`, `weak_ptr`. (3) Nhận ra và phá vòng tròn `shared_ptr`.

**🧠 Câu chuyện:** Bạn vào thư viện mượn sách. Luật của thư viện: *mượn khi bước vào, tự động trả khi bước ra khỏi cửa*, không cần nhớ. Đó là **RAII** (xin tài nguyên khi đối tượng được tạo, tự trả khi đối tượng bị hủy). Rồi giới thiệu ba "thẻ": chiếc **chìa khóa duy nhất** (`unique_ptr`: chỉ một người cầm, muốn đưa người khác thì phải trao tay), **nhiều bạn cùng giữ thẻ** (`shared_ptr`: người cuối cùng buông thẻ thì kho mới đóng, nhờ có bộ đếm số người đang giữ), và **người đứng nhìn qua cửa kính** (`weak_ptr`: nhìn được nhưng không giữ thẻ, nên không ngăn kho đóng).

**📖 Giải thích (các ý bắt buộc):**
- RAII: tài nguyên (bộ nhớ, file, khóa) gắn với vòng đời đối tượng; hàm hủy (destructor) tự chạy khi đối tượng ra khỏi phạm vi, kể cả khi có ngoại lệ. Ví dụ trong thư viện chuẩn: `std::lock_guard`, `std::ifstream`, `std::vector`.
- `unique_ptr`: một chủ duy nhất, không copy được, chuyển quyền bằng `std::move`, gần như không tốn thêm chi phí. Mặc định nên chọn.
- `shared_ptr`: nhiều chủ, có bộ đếm tham chiếu (reference count); đối tượng được hủy khi đếm về 0.
- `weak_ptr`: trỏ tới đối tượng của `shared_ptr` mà không tăng đếm; dùng để phá vòng tròn, làm cache, observer; kiểm tra bằng `expired()`/`lock()`.
- Tạo bằng `std::make_unique` / `std::make_shared`, tránh `new` trần.

**💻 Ví dụ code (4 khối, chạy được):**

```cpp
#include <iostream>

class TheMuon {
public:
    TheMuon()  { std::cout << "Muon sach\n"; }
    ~TheMuon() { std::cout << "Tra sach\n"; }
};

int main() {
    TheMuon the;
    std::cout << "Dang doc\n";
    return 0;   // ra khỏi main -> hàm hủy tự chạy
}
```
In ra: `Muon sach`, `Dang doc`, `Tra sach` (mỗi dòng một dòng).

```cpp
#include <iostream>
#include <memory>
#include <utility>

struct Hop { int so = 42; };

int main() {
    auto a = std::make_unique<Hop>();
    std::cout << a->so << "\n";
    auto b = std::move(a);                  // chuyển quyền sở hữu
    std::cout << (a == nullptr) << "\n";    // 1: a đã trao tay
    return 0;
}
```
In ra: `42` rồi `1`.

```cpp
#include <iostream>
#include <memory>

int main() {
    auto s1 = std::make_shared<int>(5);
    std::weak_ptr<int> w = s1;
    {
        auto s2 = s1;
        std::cout << s1.use_count() << "\n";   // 2
    }
    std::cout << s1.use_count() << "\n";       // 1
    s1.reset();
    std::cout << w.expired() << "\n";          // 1
    return 0;
}
```
In ra: `2`, `1`, `1`.

```cpp
#include <memory>

struct B;
struct A { std::shared_ptr<B> b; };
struct B { std::shared_ptr<A> a; };   // sửa: đổi thành std::weak_ptr<A>

int main() {
    auto a = std::make_shared<A>();
    auto b = std::make_shared<B>();
    a->b = b;
    b->a = a;   // hai bên giữ nhau -> đếm không bao giờ về 0 -> rò rỉ
    return 0;
}
```
(Khối này vẫn thoát mã 0; bài giải thích rằng nó rò rỉ âm thầm và cách sửa bằng `weak_ptr`.)

**🎤 Câu hỏi phỏng vấn (5 câu + gợi ý):**
1. *RAII là gì? Cho ví dụ trong thư viện chuẩn.* — Gắn vòng đời tài nguyên với vòng đời đối tượng; `lock_guard`, `unique_ptr`, `ifstream`.
2. *`unique_ptr` và `shared_ptr` khác nhau? Khi nào dùng cái nào?* — Sở hữu độc quyền và chia sẻ; mặc định `unique_ptr`, chỉ dùng `shared_ptr` khi thật sự cần nhiều chủ.
3. *`shared_ptr` có thread-safe không?* — Bộ đếm tham chiếu cập nhật an toàn giữa các luồng (atomic), nhưng đối tượng bên trong và việc sửa chính một biến `shared_ptr` từ nhiều luồng thì không tự an toàn.
4. *Khi nào cần `weak_ptr`?* — Phá vòng tham chiếu, cache, observer không muốn kéo dài vòng đời.
5. *Chi phí của `shared_ptr`?* — Thêm khối điều khiển (control block) và thao tác atomic cho bộ đếm.

**⚠️ Lỗi thường gặp (3 hộp `warning`):**
- Tạo hai `shared_ptr` từ cùng một con trỏ thô → hai bộ đếm riêng → giải phóng hai lần:
```cpp
// bo-qua-kiem-tra
#include <memory>
int main() {
    int* raw = new int(1);
    std::shared_ptr<int> a(raw);
    std::shared_ptr<int> b(raw);   // hai bộ đếm riêng -> delete hai lần
}
```
- Dùng `shared_ptr` ở mọi nơi "cho chắc" (tốn chi phí và làm rối quyền sở hữu).
- Lấy `.get()` ra rồi tự `delete` (smart pointer sẽ hủy thêm lần nữa).

**✍️ Trắc nghiệm (6 câu, `data-bai="02"`):**

| # | Câu hỏi | Lựa chọn | Đáp án | Giải thích |
|---|---|---|---|---|
| 1 | Ý tưởng cốt lõi của RAII là gì? | 1) Xin tài nguyên khi tạo đối tượng và tự trả trong hàm hủy khi đối tượng hết vòng đời 2) Luôn dùng `new` và `delete` 3) Bỏ kiểm tra để chạy nhanh hơn 4) Đặt mọi biến lên heap | 1 | Như thư viện: mượn khi vào, tự trả khi ra. Nhờ vậy không quên trả, kể cả khi có ngoại lệ. |
| 2 | `unique_ptr` khác `shared_ptr` ở điểm nào? | 1) `unique_ptr` chỉ có một chủ duy nhất, `shared_ptr` cho nhiều chủ cùng giữ 2) `unique_ptr` chạy chậm hơn 3) `shared_ptr` không giải phóng bộ nhớ 4) Hai loại giống hệt | 1 | Một chìa khóa duy nhất so với nhiều bạn cùng giữ thẻ. |
| 3 | Với `unique_ptr a`, sau `auto b = std::move(a);` thì `a` là gì? | 1) Vẫn trỏ vào đối tượng cũ 2) Bằng `nullptr` vì quyền sở hữu đã chuyển sang `b` 3) Lỗi biên dịch 4) Bị xóa khỏi bộ nhớ cùng đối tượng | 2 | Chìa khóa đã trao tay, nên `a` không còn giữ gì. |
| 4 | Hai đối tượng giữ `shared_ptr` lẫn nhau theo vòng tròn gây ra điều gì? | 1) Bộ đếm không bao giờ về 0 nên bộ nhớ không được giải phóng (rò rỉ) 2) Lỗi biên dịch 3) Tự động thành `weak_ptr` 4) Chương trình chạy nhanh hơn | 1 | Mỗi bên đều giữ thẻ của bên kia nên không ai buông trước. |
| 5 | `weak_ptr` dùng để làm gì? | 1) Trỏ tới đối tượng mà không tăng bộ đếm, nên phá được vòng tròn giữ nhau 2) Giữ đối tượng sống mãi mãi 3) Thay thế `unique_ptr` 4) Chỉ dùng cho mảng | 1 | Người nhìn qua cửa kính: thấy được, nhưng không giữ kho mở. |
| 6 | Nên ưu tiên cách nào để tạo `shared_ptr`? | 1) `std::shared_ptr<T>(new T)` 2) `std::make_shared<T>()` 3) `new T` rồi gán 4) `malloc` | 2 | `make_shared` an toàn trước ngoại lệ và cấp phát một lần cho cả đối tượng lẫn bộ đếm. |

**🔑 Tóm tắt (5 dòng):**
1. RAII: mượn trong hàm khởi tạo, tự trả trong hàm hủy.
2. `unique_ptr`: một chìa khóa duy nhất, trao tay bằng `std::move`.
3. `shared_ptr`: nhiều người cùng giữ, người cuối buông thì mới dọn.
4. `weak_ptr`: chỉ nhìn, không giữ, dùng để phá vòng tròn.
5. Mặc định dùng `unique_ptr` và `make_unique`/`make_shared`; tránh `new`/`delete` trần.

**Thuật ngữ thêm vào glossary:** RAII (xin tài nguyên khi tạo, tự trả khi hủy); smart pointer (con trỏ thông minh: tự dọn); destructor (hàm hủy: chạy khi đối tượng chết); ownership (quyền sở hữu: ai chịu trách nhiệm dọn); reference count (bộ đếm tham chiếu: đếm số người đang giữ); control block (khối điều khiển: chỗ lưu bộ đếm của `shared_ptr`).

- [ ] **Step 1: Viết file bài** `02-raii-smart-pointer.md` đúng nội dung trên theo Khuôn bài.
- [ ] **Step 2: Cập nhật** `mkdocs.yml` (thêm `"Bài 2 — RAII và smart pointer": nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md` dưới nhóm 1), thêm 6 thuật ngữ vào `docs/glossary.md` (cột Bài là `[Bài 2](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md)`), thêm dòng `| [Bài 2 — RAII và smart pointer](nhom-1-nen-tang-bo-nho/02-raii-smart-pointer.md) | <span class="diem" data-bai="02"></span> |` vào `docs/tien-do.md`.
- [ ] **Step 3: Chạy kiểm tra:** `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`. Expected: `0 lỗi cấu trúc`; số khối code tăng thêm 4 chạy được + 1 bỏ qua; build sạch.
- [ ] **Step 4: Xác nhận kết quả in ra** của 3 chương trình đầu đúng như bài ghi (`g++ -std=c++17`).
- [ ] **Step 5: Commit:** `git add -A && git commit -m "feat: Bài 2 — RAII và smart pointer" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`

---

### Task 6: Bài 3 — Move semantics, rule of 0/3/5

**Files:**
- Create: `docs/nhom-1-nen-tang-bo-nho/03-move-semantics.md`
- Modify: `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`

**Interfaces:**
- Consumes: Khuôn bài; mục nav nhóm 1; `data-bai="03"`. Bài này nhắc lại `std::move` đã gặp ở bài 2 (dẫn link sang bài 2).

**🎯 Mục tiêu:** (1) Phân biệt sao chép và di chuyển bằng ví dụ quyển vở. (2) Hiểu `std::move` thực sự làm gì. (3) Biết rule of 0/3/5 và viết được move constructor.

**🧠 Câu chuyện:** Bạn có một quyển vở dày 200 trang và bạn của bạn cần nó. Cách 1: *photo cả quyển* (sao chép, copy): tốn giấy, tốn thời gian. Cách 2: *đưa luôn quyển vở cho bạn* (di chuyển, move): nhanh, nhưng bạn chỉ còn cái bìa rỗng. Ai đưa xong thì đừng mong còn chép được bài từ quyển đó nữa. Vật "có tên, ở lâu" (như quyển vở của bạn) gọi là **lvalue**; vật "tạm thời, sắp biến mất" (như tờ giấy nháp vừa viết) gọi là **rvalue**: lấy ruột của nó đi cũng chẳng ai tiếc.

**📖 Giải thích (các ý bắt buộc):**
- lvalue có tên và địa chỉ, tồn tại sau câu lệnh; rvalue là giá trị tạm. Tham chiếu rvalue viết `T&&`.
- `std::move(x)` **không di chuyển gì cả**: nó chỉ ép `x` thành rvalue để cho phép "lấy ruột"; việc di chuyển do move constructor / move assignment làm.
- Sau khi move, nguồn ở trạng thái hợp lệ nhưng không xác định: chỉ nên hủy hoặc gán lại.
- Move constructor nên `noexcept`: `std::vector` khi tăng dung lượng chỉ dùng move nếu nó không ném ngoại lệ.
- Rule of 3 (C++98): tự viết một trong destructor, copy constructor, copy assignment thì thường phải viết cả ba. Rule of 5 (C++11): thêm move constructor, move assignment. Rule of 0: dùng thành phần tự quản lý tài nguyên (`vector`, `unique_ptr`…) để khỏi phải viết cái nào.
- Trả về đối tượng cục bộ theo giá trị: trình biên dịch dùng copy elision/RVO (tối ưu bỏ qua việc copy) hoặc move; không viết `return std::move(v);` vì có thể cản tối ưu này.
- Perfect forwarding: `std::forward<T>` giữ nguyên "lvalue hay rvalue" khi chuyển tiếp tham số trong template.

**💻 Ví dụ code (4 khối, chạy được):**

```cpp
#include <iostream>
#include <string>
#include <utility>
#include <vector>

int main() {
    std::string a(1000, 'x');
    std::string b = std::move(a);       // lấy luôn bộ nhớ của a
    std::cout << b.size() << "\n";      // 1000
    std::vector<std::string> v;
    v.push_back(std::move(b));
    std::cout << v[0].size() << "\n";   // 1000
    return 0;
}
```
In ra: `1000` rồi `1000`. (Cố ý không in `a.size()` vì sau move giá trị của `a` không được đảm bảo.)

```cpp
#include <cstddef>
#include <iostream>
#include <utility>

class Mang {
public:
    explicit Mang(std::size_t n) : n_(n), d_(new int[n]) {}
    ~Mang() { delete[] d_; }

    Mang(const Mang& o) : n_(o.n_), d_(new int[o.n_]) {
        for (std::size_t i = 0; i < n_; ++i) d_[i] = o.d_[i];
    }
    Mang& operator=(const Mang& o) {
        if (this != &o) {
            Mang tam(o);               // copy-and-swap
            std::swap(n_, tam.n_);
            std::swap(d_, tam.d_);
        }
        return *this;
    }

    Mang(Mang&& o) noexcept : n_(o.n_), d_(o.d_) {
        o.n_ = 0;
        o.d_ = nullptr;                // nguồn về trạng thái an toàn
    }
    Mang& operator=(Mang&& o) noexcept {
        if (this != &o) {
            delete[] d_;
            n_ = o.n_;
            d_ = o.d_;
            o.n_ = 0;
            o.d_ = nullptr;
        }
        return *this;
    }

    std::size_t size() const { return n_; }

private:
    std::size_t n_;
    int* d_;
};

int main() {
    Mang a(100);
    Mang b = std::move(a);
    std::cout << b.size() << " " << a.size() << "\n";   // 100 0
    return 0;
}
```
In ra: `100 0`.

```cpp
#include <cstddef>
#include <iostream>
#include <utility>
#include <vector>

class Mang {
public:
    explicit Mang(std::size_t n) : d_(n) {}
    std::size_t size() const { return d_.size(); }
private:
    std::vector<int> d_;   // vector lo hết, không cần viết hàm đặc biệt nào (Rule of 0)
};

int main() {
    Mang a(100);
    Mang b = std::move(a);
    std::cout << b.size() << "\n";   // 100
    return 0;
}
```
In ra: `100`.

```cpp
#include <iostream>
#include <utility>

void in(int&)  { std::cout << "lvalue\n"; }
void in(int&&) { std::cout << "rvalue\n"; }

template <typename T>
void chuyenTiep(T&& x) { in(std::forward<T>(x)); }

int main() {
    int a = 1;
    chuyenTiep(a);   // lvalue
    chuyenTiep(2);   // rvalue
    return 0;
}
```
In ra: `lvalue` rồi `rvalue`.

**🎤 Câu hỏi phỏng vấn (6 câu + gợi ý):**
1. *lvalue và rvalue khác nhau thế nào?* — lvalue có danh tính (tên, địa chỉ), còn tồn tại sau câu lệnh; rvalue là giá trị tạm sắp hết vòng đời.
2. *`std::move` làm gì?* — Chỉ là phép ép kiểu sang rvalue reference; không tự di chuyển dữ liệu.
3. *Viết move constructor cho class giữ con trỏ thô.* — Lấy con trỏ của nguồn, đặt con trỏ nguồn về `nullptr`, đánh dấu `noexcept`.
4. *Vì sao move constructor nên `noexcept`?* — `std::vector` dùng `move_if_noexcept` khi tăng dung lượng; nếu có thể ném ngoại lệ nó quay về copy để giữ an toàn ngoại lệ.
5. *Rule of 3/5/0?* — Như phần Giải thích; ưu tiên Rule of 0.
6. *Perfect forwarding là gì?* — Chuyển tiếp tham số giữ nguyên lvalue/rvalue bằng `T&&` (forwarding reference) và `std::forward<T>`.

**⚠️ Lỗi thường gặp (3 hộp `warning`):**
- Dùng đối tượng sau khi đã move và đoán nội dung của nó.
- Viết `return std::move(bienCucBo);`, có thể cản RVO.
- Viết move constructor nhưng quên đặt nguồn về `nullptr`, nên cả hai đối tượng cùng `delete` một vùng nhớ (double free).

**✍️ Trắc nghiệm (6 câu, `data-bai="03"`):**

| # | Câu hỏi | Lựa chọn | Đáp án | Giải thích |
|---|---|---|---|---|
| 1 | `std::move(x)` thực sự làm gì? | 1) Di chuyển dữ liệu của x sang chỗ khác ngay 2) Chỉ ép x thành rvalue để cho phép "lấy ruột"; việc di chuyển do move constructor làm 3) Xóa x 4) Sao chép sâu x | 2 | Tên gọi dễ gây hiểu lầm: `std::move` chỉ là cái ép kiểu. |
| 2 | Sau `std::string b = std::move(a);`, điều nào an toàn với `a`? | 1) Đọc `a.size()` và chắc chắn bằng 0 2) Gán giá trị mới cho `a` hoặc hủy `a`; không nên đoán nội dung của `a` 3) Dùng `a` như chưa có gì xảy ra 4) Không được gán lại `a` nữa | 2 | Nguồn ở trạng thái "hợp lệ nhưng không xác định". Gán mới và hủy thì luôn an toàn. |
| 3 | Vì sao move constructor nên đánh dấu `noexcept`? | 1) Để code ngắn hơn 2) Để `std::vector` khi tăng dung lượng dám dùng move thay vì copy 3) Để tắt kiểm tra lỗi 4) Cú pháp bắt buộc | 2 | Nếu move có thể ném ngoại lệ, `vector` quay về copy để không làm hỏng dữ liệu. |
| 4 | Rule of Zero nghĩa là gì? | 1) Không bao giờ viết class 2) Dùng các thành phần tự quản lý tài nguyên (`vector`, `unique_ptr`…) để khỏi tự viết destructor/copy/move 3) Luôn viết cả 5 hàm đặc biệt 4) Xóa mọi destructor | 2 | Để thư viện chuẩn dọn dẹp giùm, bớt code, bớt lỗi. |
| 5 | Rule of Five nói gì? | 1) Nếu tự viết một trong năm hàm (destructor, copy ctor, copy assign, move ctor, move assign) thì thường phải xem xét viết cả năm 2) Mỗi class tối đa 5 hàm 3) Cần 5 thành viên dữ liệu 4) Chỉ áp dụng cho template | 1 | Cần quản lý tài nguyên bằng tay thì phải chăm cả năm hàm. |
| 6 | Hàm trả về biến cục bộ theo giá trị (`return v;`) nên viết thế nào? | 1) `return std::move(v);` 2) `return v;` để trình biên dịch dùng copy elision/RVO hoặc move 3) Bắt buộc `return new T(v);` 4) Luôn trả bằng tham chiếu | 2 | `return std::move(v);` có thể cản tối ưu RVO. |

**🔑 Tóm tắt (5 dòng):**
1. Copy là photo cả quyển vở; move là đưa luôn quyển vở.
2. `std::move` chỉ là phép ép kiểu sang rvalue, chưa di chuyển gì.
3. Sau khi move, chỉ nên hủy hoặc gán lại đối tượng nguồn.
4. Move constructor nên `noexcept` và đặt nguồn về trạng thái an toàn.
5. Ưu tiên Rule of Zero; nếu tự quản lý tài nguyên thì chăm đủ Rule of Five.

**Thuật ngữ thêm vào glossary:** lvalue (giá trị có tên, ở lâu); rvalue (giá trị tạm, sắp biến mất); move semantics (ngữ nghĩa di chuyển: lấy ruột thay vì sao chép); copy elision / RVO (trình biên dịch bỏ qua bước copy khi trả về); rule of 0/3/5 (quy tắc về các hàm đặc biệt của class); perfect forwarding (chuyển tiếp hoàn hảo: giữ nguyên lvalue/rvalue).

- [ ] **Step 1: Viết file bài** `03-move-semantics.md` đúng nội dung trên theo Khuôn bài.
- [ ] **Step 2: Cập nhật** `mkdocs.yml` (nav: `"Bài 3 — Move semantics, rule of 0/3/5": nhom-1-nen-tang-bo-nho/03-move-semantics.md`), `docs/glossary.md` (6 thuật ngữ), `docs/tien-do.md` (dòng `data-bai="03"`).
- [ ] **Step 3: Chạy kiểm tra:** `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`. Expected: không lỗi.
- [ ] **Step 4: Xác nhận kết quả in ra** của cả 4 chương trình đúng như bài ghi.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "feat: Bài 3 — move semantics, rule of 0/3/5" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`

---

### Task 7: Bài 4 — Tính năng C++11/14/17

**Files:**
- Create: `docs/nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md`
- Modify: `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`

**Interfaces:**
- Consumes: Khuôn bài; mục nav nhóm 1; `data-bai="04"`.

**🎯 Mục tiêu:** (1) Kể được các tính năng C++ hiện đại hay bị hỏi. (2) Biết cái bẫy của `auto`, lambda và `string_view`. (3) Phân biệt `const` và `constexpr`.

**🧠 Câu chuyện:** Chiếc hộp đồ nghề của bác thợ mộc. Hồi xưa (C++98) hộp chỉ có búa và cưa. Mỗi vài năm bác lại mua thêm dụng cụ xịn: năm 2011 có máy khoan, năm 2014 chỉnh lại vài món cho vừa tay, năm 2017 có cả thước laser. Bác không bỏ cái cưa cũ, nhưng việc nào có dụng cụ mới thì làm nhanh và ít sai hơn. Ghi chú nhỏ để nhớ: **C++11** (2011), **C++14** (2014), **C++17** (2017).

**📖 Giải thích (các ý bắt buộc):**
- C++11: `auto` (trình biên dịch tự đoán kiểu), range-based for, `nullptr` (thay `NULL`), lambda (hàm vô danh), `enum class`, `override`/`final`, `constexpr`, smart pointer, move semantics.
- C++14: `std::make_unique`, lambda tham số `auto` (generic lambda), `constexpr` linh hoạt hơn.
- C++17: structured binding `auto [a, b] = ...`, `std::optional`, `std::variant`, `std::string_view`, `if` có phần khởi tạo `if (auto x = f(); x)`, `std::filesystem`.
- `auto` bỏ `const` và `&` của kiểu gốc: viết `const auto&` khi không muốn copy.
- Lambda `[=]` bắt bản sao, `[&]` bắt tham chiếu; lambda sống lâu hơn biến mà nó bắt bằng `[&]` thì nguy hiểm.
- `constexpr`: có thể tính ngay lúc biên dịch khi đầu vào cố định. `const` chỉ cấm sửa sau khi gán.
- `string_view`: cửa sổ nhìn vào chuỗi mà không copy; nguy hiểm nếu chuỗi gốc là tạm thời và đã bị hủy.

**💻 Ví dụ code (3 khối, chạy được):**

```cpp
#include <iostream>
#include <vector>

enum class MauSac { Do, Xanh };

int main() {
    std::vector<int> v = {3, 1, 2};
    for (auto x : v) std::cout << x << " ";
    std::cout << "\n";

    int* p = nullptr;
    auto cong = [](int a, int b) { return a + b; };
    std::cout << cong(2, 3) << " " << (p == nullptr) << "\n";

    MauSac m = MauSac::Do;
    std::cout << (m == MauSac::Do) << "\n";
    return 0;
}
```
In ra: `3 1 2 `, `5 1`, `1`.

```cpp
#include <iostream>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <variant>

std::optional<int> tim(const std::map<std::string, int>& m, std::string_view k) {
    auto it = m.find(std::string(k));
    if (it == m.end()) return std::nullopt;
    return it->second;
}

int main() {
    std::map<std::string, int> diem = {{"An", 9}, {"Binh", 7}};
    if (auto d = tim(diem, "An"); d) std::cout << *d << "\n";       // 9
    auto [ten, so] = *diem.begin();                                  // structured binding
    std::cout << ten << " " << so << "\n";                           // An 9
    std::variant<int, std::string> v = std::string("xin chao");
    std::cout << std::get<std::string>(v) << "\n";                   // xin chao
    return 0;
}
```
In ra: `9`, `An 9`, `xin chao`.

```cpp
#include <iostream>

constexpr int giaiThua(int n) { return n <= 1 ? 1 : n * giaiThua(n - 1); }

int main() {
    constexpr int x = giaiThua(5);   // tính ngay lúc biên dịch
    static_assert(x == 120, "sai roi");
    std::cout << x << "\n";
    return 0;
}
```
In ra: `120`.

**🎤 Câu hỏi phỏng vấn (6 câu + gợi ý):**
1. *Những bẫy khi dùng `auto`?* — `auto` bỏ `const` và `&` (copy ngầm); dùng `const auto&`; với `vector<bool>` cho kiểu proxy bất ngờ.
2. *Lambda bắt `[=]` khác `[&]` thế nào? Rủi ro?* — Sao chép so với tham chiếu; `[&]` mà lambda sống lâu hơn biến thì thành tham chiếu treo.
3. *`constexpr` khác `const`?* — `constexpr` đảm bảo đánh giá được lúc biên dịch (khi đầu vào cố định); `const` chỉ không cho sửa.
4. *`enum class` hơn `enum` ở đâu?* — Có phạm vi riêng, không tự đổi sang `int`, không đụng tên.
5. *Dùng `override` và `final` để làm gì?* — `override` nhờ trình biên dịch bắt lỗi khi ghi đè sai chữ ký; `final` cấm ghi đè/kế thừa tiếp.
6. *Kể vài tính năng C++17 bạn hay dùng.* — `optional`, `variant`, `string_view`, structured binding, `if` có khởi tạo; nhớ rủi ro treo của `string_view`.

**⚠️ Lỗi thường gặp (3 hộp `warning`):**
- Lambda bắt `[&]` rồi trả ra khỏi hàm (kèm khối `// bo-qua-kiem-tra`):
```cpp
// bo-qua-kiem-tra
#include <functional>
std::function<int()> hamLoi() {
    int n = 5;
    return [&] { return n; };   // n bị dọn khi hàm kết thúc → tham chiếu treo
}
```
- `auto x = tenBienLon;` làm copy ngầm cả đối tượng lớn.
- `std::string_view` trỏ vào chuỗi tạm thời đã bị hủy.

**✍️ Trắc nghiệm (7 câu, `data-bai="04"`):**

| # | Câu hỏi | Lựa chọn | Đáp án | Giải thích |
|---|---|---|---|---|
| 1 | `auto x = 5;` thì `x` có kiểu gì? | 1) `int` 2) `double` 3) Lỗi vì không biết kiểu 4) `std::string` | 1 | Trình biên dịch tự đoán kiểu từ giá trị bên phải: số nguyên 5 là `int`. |
| 2 | Từ khóa nào thay cho `NULL` và an toàn hơn từ C++11? | 1) `0` 2) `nullptr` 3) `void` 4) `NIL` | 2 | `nullptr` có kiểu riêng, không bị lẫn với số nguyên 0. |
| 3 | Lambda `[&](int x){ return x + n; }` bắt biến `n` kiểu nào? | 1) Bắt bản sao 2) Bắt tham chiếu; nếu lambda sống lâu hơn `n` thì nguy hiểm 3) Không bắt gì 4) Bắt `n` lên heap | 2 | `&` nghĩa là tham chiếu. Biến đã bị dọn mà lambda còn dùng thì thành tham chiếu treo. |
| 4 | `constexpr` khác `const` thế nào? | 1) `constexpr` đảm bảo có thể tính ngay lúc biên dịch (khi đầu vào cố định); `const` chỉ cấm sửa sau khi gán 2) Giống hệt nhau 3) `constexpr` chạy chậm hơn 4) `const` nhanh hơn | 1 | `constexpr` hứa với trình biên dịch là tính xong trước khi chạy. |
| 5 | Khi nào dùng `std::optional<int>`? | 1) Khi một giá trị có thể có hoặc không có (thay cho trả `-1` hay con trỏ null) 2) Khi cần số nguyên rất lớn 3) Khi cần mảng 4) Khi cần đa luồng | 1 | Giống chiếc hộp có thể rỗng; hợp lý hơn dùng số "ma thuật" như -1. |
| 6 | `enum class` hơn `enum` thường ở điểm nào? | 1) Giá trị có phạm vi riêng (`MauSac::Do`) và không tự đổi sang `int`, tránh đụng tên 2) Chạy nhanh hơn 3) Tốn ít bộ nhớ hơn 4) Chỉ dùng được trong template | 1 | Phạm vi riêng và kiểu chặt chẽ hơn giúp ít nhầm lẫn. |
| 7 | Structured binding `auto [ten, so] = p;` có từ phiên bản C++ nào? | 1) C++98 2) C++11 3) C++14 4) C++17 | 4 | Structured binding ra mắt ở C++17, cùng `optional`, `variant`, `string_view`. |

**🔑 Tóm tắt (5 dòng):**
1. C++11 đem lại `auto`, lambda, `nullptr`, `enum class`, smart pointer, move.
2. C++14 thêm `make_unique` và lambda tham số `auto`.
3. C++17 thêm `optional`, `variant`, `string_view`, structured binding, `if` có khởi tạo.
4. `auto` bỏ `const` và `&`; lambda `[&]` và `string_view` dễ gây tham chiếu treo.
5. `constexpr` là tính ngay lúc biên dịch; `const` chỉ là không cho sửa.

**Thuật ngữ thêm vào glossary:** auto (để trình biên dịch tự đoán kiểu); lambda (hàm vô danh viết ngay tại chỗ); constexpr (tính được lúc biên dịch); enum class (liệt kê có phạm vi riêng); optional (hộp có thể rỗng); variant (hộp chứa một trong nhiều kiểu); string_view (cửa sổ nhìn vào chuỗi, không copy); structured binding (tách một cặp/bộ thành nhiều biến).

- [ ] **Step 1: Viết file bài** `04-cpp11-14-17.md` đúng nội dung trên theo Khuôn bài (7 khối `cau-hoi`).
- [ ] **Step 2: Cập nhật** `mkdocs.yml` (nav: `"Bài 4 — Tính năng C++11/14/17": nhom-1-nen-tang-bo-nho/04-cpp11-14-17.md`), `docs/glossary.md` (8 thuật ngữ), `docs/tien-do.md` (dòng `data-bai="04"`).
- [ ] **Step 3: Chạy kiểm tra:** `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`. Expected: không lỗi.
- [ ] **Step 4: Xác nhận kết quả in ra** của cả 3 chương trình đúng như bài ghi (khối 1 in `3 1 2 ` có khoảng trắng cuối dòng).
- [ ] **Step 5: Commit:** `git add -A && git commit -m "feat: Bài 4 — tính năng C++11/14/17" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`

---

### Task 8: Bài 5 — Memory leak, dangling, UB và công cụ phát hiện

**Files:**
- Create: `docs/nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md`
- Modify: `mkdocs.yml`, `docs/glossary.md`, `docs/tien-do.md`

**Interfaces:**
- Consumes: Khuôn bài; mục nav nhóm 1; `data-bai="05"`. Bài này tham chiếu lại bài 1 (stack/heap), bài 2 (smart pointer).

**🎯 Mục tiêu:** (1) Phân biệt rò rỉ, con trỏ treo, giải phóng hai lần, hành vi không xác định. (2) Biết dùng AddressSanitizer và Valgrind. (3) Biết cách phòng tránh trong C++ hiện đại.

**🧠 Câu chuyện:** Quay lại kho đồ của trường. **Rò rỉ (leak)**: mượn đồ mà quên trả, kho đầy dần. **Con trỏ treo (dangling)**: bạn cầm tờ giấy ghi "đồ ở phòng 12", nhưng phòng 12 đã bị dỡ; đến đó thì thấy gì cũng có thể xảy ra. **Giải phóng hai lần (double free)**: trả cùng một món đồ hai lần, sổ sách rối tung. **Hành vi không xác định (UB)**: luật chơi đã bị phá, nên mọi chuyện đều có thể xảy ra: lúc thì "chạy đúng", lúc thì sập, lúc thì sai âm thầm, đổi máy là đổi kết quả.

**📖 Giải thích (các ý bắt buộc):**
- Bốn loại lỗi: memory leak, dangling pointer / use-after-free, double free, buffer overflow (ghi vượt mảng); tất cả đều có thể dẫn tới UB.
- `new[]` phải đi với `delete[]`; `new` đi với `delete`; trộn lẫn là UB.
- AddressSanitizer (ASan): biên dịch với `-fsanitize=address`, chương trình tự báo lỗi truy cập bộ nhớ sai và (trên Linux) cả rò rỉ lúc kết thúc; chạy nhanh hơn Valgrind khoảng vài lần.
- Valgrind (memcheck): không cần biên dịch lại, chạy chương trình trong máy ảo kiểm tra; chậm hơn nhiều.
- Cách phòng tránh: RAII, smart pointer, container chuẩn (`vector`, `string`), tránh `new`/`delete` trần, bật cảnh báo `-Wall -Wextra`.

**💻 Ví dụ code (2 khối chạy được + 1 khối lệnh shell không biên dịch):**

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
In ra: `0`, `1`, `2` (rò rỉ không làm chương trình báo lỗi, nên phải dùng công cụ mới thấy).

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
In ra: `0`, `1`, `2` (không còn rò rỉ).

```bash
# Biên dịch kèm AddressSanitizer rồi chạy: tự báo lỗi bộ nhớ và rò rỉ
g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer rolo.cpp -o rolo
./rolo

# Hoặc dùng Valgrind trên chương trình đã biên dịch thường
g++ -std=c++17 -g rolo.cpp -o rolo
valgrind --leak-check=full ./rolo
```
(Khối này dùng ngôn ngữ `bash` nên không bị kiểm tra biên dịch. Khi viết bài, hãy chạy thật lệnh ASan trên khối rò rỉ ở trên và dán **kết quả thực tế rút gọn** vào bài trong hộp `note` "Kết quả mẫu"; nếu máy thiếu thư viện ASan thì ghi rõ "chưa chạy thử" thay vì tự bịa kết quả.)

**🎤 Câu hỏi phỏng vấn (6 câu + gợi ý):**
1. *Làm sao tìm memory leak?* — ASan/LeakSanitizer, Valgrind memcheck, hoặc công cụ phân tích heap; phòng bằng RAII và smart pointer.
2. *Memory leak khác dangling pointer thế nào?* — Leak: còn vùng nhớ mà không ai trỏ tới để trả; dangling: còn con trỏ nhưng vùng nhớ đã được trả.
3. *Double free là gì, hậu quả?* — Giải phóng một vùng nhớ hai lần; làm hỏng bộ cấp phát, có thể crash hoặc bị khai thác lỗ hổng.
4. *Vì sao `new[]` phải đi với `delete[]`?* — `delete[]` gọi hàm hủy cho mọi phần tử và trả đúng khối nhớ; dùng `delete` thường là UB.
5. *Cho vài ví dụ về UB.* — Đọc/ghi ngoài mảng, dùng sau khi `delete`, tràn số nguyên có dấu, data race, giải tham chiếu `nullptr`.
6. *Buffer overflow là gì? Phát hiện thế nào?* — Ghi vượt biên mảng/vùng nhớ; ASan phát hiện lúc chạy; phòng bằng `std::vector::at`, `std::string`, kiểm tra biên.

**⚠️ Lỗi thường gặp (3 hộp `warning`):**
- Dùng sau khi giải phóng (kèm khối `// bo-qua-kiem-tra`):
```cpp
// bo-qua-kiem-tra
#include <iostream>
int main() {
    int* p = new int(5);
    delete p;
    std::cout << *p << "\n";   // dùng sau khi trả: hành vi không xác định
}
```
- Trộn `new[]` với `delete` (và `new` với `delete[]`).
- Tin rằng "chạy thử không sao" nghĩa là không có UB (UB có thể chạy đúng ở máy này mà sập ở máy khác).

**✍️ Trắc nghiệm (7 câu, `data-bai="05"`):**

| # | Câu hỏi | Lựa chọn | Đáp án | Giải thích |
|---|---|---|---|---|
| 1 | Rò rỉ bộ nhớ (memory leak) là gì? | 1) Xin vùng nhớ nhưng không bao giờ trả lại, nên bộ nhớ bị chiếm dần 2) Dùng vùng nhớ đã trả 3) Ghi vượt mảng 4) Trả vùng nhớ hai lần | 1 | Mượn đồ mà quên trả. Các phương án còn lại là lỗi khác. |
| 2 | Con trỏ treo (dangling pointer) là gì? | 1) Con trỏ bằng nullptr 2) Con trỏ vẫn giữ địa chỉ của vùng nhớ đã được trả 3) Con trỏ trỏ lên stack 4) Con trỏ `const` | 2 | Tờ giấy ghi số phòng đã bị dỡ: dùng nó là UB. |
| 3 | Công cụ nào phát hiện lỗi bộ nhớ khi biên dịch kèm cờ `-fsanitize=address`? | 1) gdb 2) AddressSanitizer 3) CMake 4) git | 2 | ASan chèn các kiểm tra vào chương trình lúc biên dịch và báo lỗi lúc chạy. |
| 4 | Vì sao mảng cấp phát bằng `new int[10]` phải giải phóng bằng `delete[]`? | 1) `delete[]` gọi hàm hủy cho mọi phần tử và trả đúng khối nhớ; dùng `delete` thường là hành vi không xác định 2) Chỉ là quy ước, dùng cái nào cũng được 3) `delete[]` nhanh hơn 4) Để tránh lỗi biên dịch | 1 | Trình quản lý bộ nhớ ghi lại số phần tử của mảng; `delete[]` biết cách đọc thông tin đó. |
| 5 | Hành vi không xác định (UB) nghĩa là gì? | 1) Chương trình luôn crash 2) Chuẩn C++ không quy định kết quả: có thể chạy "đúng", sai âm thầm hoặc crash, và đổi theo trình biên dịch/máy 3) Luôn có thông báo lỗi 4) Chỉ xảy ra trên Windows | 2 | Nguy hiểm vì nó có thể "chạy đúng" lúc thử rồi sập khi chạy thật. |
| 6 | Cách phòng tránh rò rỉ tốt nhất trong C++ hiện đại là gì? | 1) Nhớ `delete` cẩn thận 2) Dùng RAII, smart pointer và container chuẩn thay vì `new`/`delete` trần 3) Tắt cảnh báo của trình biên dịch 4) Chỉ dùng biến toàn cục | 2 | Để hàm hủy lo việc trả đồ thay vì trông chờ vào trí nhớ. |
| 7 | Valgrind (memcheck) khác ASan ở điểm nào? | 1) Valgrind chạy chương trình biên dịch bình thường dưới máy ảo kiểm tra, không cần biên dịch lại nhưng chậm hơn nhiều; ASan chèn kiểm tra lúc biên dịch nên nhanh hơn 2) Giống hệt nhau 3) Valgrind chỉ dùng cho Java 4) ASan không bao giờ tìm được rò rỉ | 1 | ASan trên Linux có kèm LeakSanitizer nên cũng báo rò rỉ; Valgrind đổi lại cho khả năng kiểm tra không cần sửa cách biên dịch. |

**🔑 Tóm tắt (5 dòng):**
1. Bốn lỗi bộ nhớ hay gặp: rò rỉ, con trỏ treo, giải phóng hai lần, ghi vượt mảng.
2. `new` đi với `delete`, `new[]` đi với `delete[]`; trộn lẫn là UB.
3. UB không phải lúc nào cũng sập: nó có thể "chạy đúng" rồi hỏng ở máy khác.
4. Tìm lỗi bằng AddressSanitizer (`-fsanitize=address`) hoặc Valgrind.
5. Tránh bằng RAII, smart pointer, container chuẩn, và bật `-Wall -Wextra`.

**Thuật ngữ thêm vào glossary:** use-after-free (dùng sau khi trả); double free (trả hai lần); buffer overflow (ghi vượt biên mảng); undefined behavior / UB (hành vi không xác định: luật chơi bị phá, mọi chuyện đều có thể xảy ra); AddressSanitizer / ASan (công cụ bắt lỗi bộ nhớ lúc chạy, bật bằng cờ biên dịch); Valgrind (công cụ kiểm tra bộ nhớ không cần biên dịch lại).

- [ ] **Step 1: Chạy thử ASan** trên khối rò rỉ để lấy kết quả thật: lưu khối code đầu tiên vào file tạm ngoài repo, rồi chạy `g++ -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer rolo.cpp -o rolo && ./rolo`. Ghi lại vài dòng đầu của báo cáo `LeakSanitizer` (ví dụ dòng `ERROR: LeakSanitizer: detected memory leaks`). Nếu lệnh lỗi vì thiếu thư viện, ghi lại lỗi và không bịa kết quả.
- [ ] **Step 2: Viết file bài** `05-memory-leak-ub.md` đúng nội dung trên theo Khuôn bài (7 khối `cau-hoi`), kèm hộp `note` "Kết quả mẫu" chứa kết quả thật ở Step 1.
- [ ] **Step 3: Cập nhật** `mkdocs.yml` (nav: `"Bài 5 — Memory leak, dangling, UB": nhom-1-nen-tang-bo-nho/05-memory-leak-ub.md`), `docs/glossary.md` (6 thuật ngữ), `docs/tien-do.md` (dòng `data-bai="05"`).
- [ ] **Step 4: Chạy kiểm tra:** `python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`. Expected: không lỗi.
- [ ] **Step 5: Xác nhận kết quả in ra** của hai chương trình chạy được (`0 1 2`, mỗi số một dòng).
- [ ] **Step 6: Commit:** `git add -A && git commit -m "feat: Bài 5 — memory leak, dangling, UB và công cụ phát hiện" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`

---

### Task 9: Push Nhóm 1 lên GitHub và bật web

**Files:** không sửa file; thao tác trên GitHub.

**Interfaces:**
- Consumes: toàn bộ commit Task 1–8; tài khoản `gh` đã đăng nhập là `hungnguyen010518`.
- Produces: repo công khai `hungnguyen010518/cpp-interview-short-term`, nhánh `main`, nhánh `gh-pages` do workflow tạo, web ở `https://hungnguyen010518.github.io/cpp-interview-short-term/`.

- [ ] **Step 1: Chạy toàn bộ kiểm tra lần cuối**

Run: `python3 -m unittest discover -s tests -v && python3 scripts/kiem_cau_truc.py && python3 scripts/kiem_code.py && mkdocs build --strict`
Expected: 16 test `ok`; `0 lỗi cấu trúc`; `… khối code, 0 lỗi`; build sạch. Nếu có lỗi, dừng và sửa trước khi push.

- [ ] **Step 2: Soát nội dung trước khi công khai**

Người điều phối giữ một danh sách từ khóa cần tránh (tên công ty, khách hàng, dự án) **ở ngoài repo** và chạy `grep -rniE "<danh sách>" . --exclude-dir=.git --exclude-dir=.superpowers --exclude-dir=site`. Kết quả phải rỗng; nếu có, thay bằng cách nói chung ("công ty", "dự án thực tế") trước khi push. Danh sách này không được ghi vào bất kỳ file nào trong repo.

- [ ] **Step 3: Tạo repo công khai và push**

```bash
gh repo create hungnguyen010518/cpp-interview-short-term --public --source=. --remote=origin --description "Ôn C++ phỏng vấn ngắn hạn — giải thích dễ hiểu, trắc nghiệm tương tác" --push
```
Expected: in ra URL repo; `git log origin/main --oneline | head -3` thấy các commit vừa tạo.

- [ ] **Step 4: Đợi CI chạy và deploy**

Run: `gh run watch $(gh run list --limit 1 --json databaseId -q '.[0].databaseId') --exit-status`
Expected: cả hai job `kiem-tra` và `deploy` đều thành công; nhánh `gh-pages` xuất hiện (`gh api repos/hungnguyen010518/cpp-interview-short-term/branches -q '.[].name'` liệt kê `gh-pages`).

- [ ] **Step 5: Bật GitHub Pages từ nhánh `gh-pages`**

```bash
gh api -X POST repos/hungnguyen010518/cpp-interview-short-term/pages -f "source[branch]=gh-pages" -f "source[path]=/"
```
Expected: JSON có `"status"` và `html_url` bằng `https://hungnguyen010518.github.io/cpp-interview-short-term/`. (Nếu trả về lỗi "already enabled" thì bỏ qua.)

- [ ] **Step 6: Kiểm tra web đã lên**

Chờ khoảng 1–2 phút rồi chạy: `curl -s -o /dev/null -w "%{http_code}\n" https://hungnguyen010518.github.io/cpp-interview-short-term/`
Expected: `200`. Mở bài 1 trên web thật, làm thử trắc nghiệm một lần, và mở trang Tiến độ để xác nhận điểm lưu được.

- [ ] **Step 7: Báo kết quả cho người học**

Gửi đường dẫn web, nhắc rằng điểm lưu trong trình duyệt (đổi máy hoặc xóa dữ liệu trình duyệt là mất), và hỏi có muốn bắt đầu kế hoạch nhóm 2 (STL và thuật toán) không.

---

## Self-review (đã chạy khi soạn kế hoạch)

- **Phủ bản thiết kế:** web MkDocs + CI (Task 1, 3, 9); trắc nghiệm tương tác, `localStorage` bọc `try/catch`, trang Tiến độ (Task 2); kiểm tra cấu trúc, biên dịch code, marker `// bo-qua-kiem-tra` (Task 3); khuôn 8 khối, văn phong lớp 5 (Global Constraints + từng bài); thuật ngữ (mỗi bài); 5 bài nhóm 1 (Task 4–8); repo công khai và không có thông tin công ty (Task 9, bước soát). Chưa nằm trong kế hoạch này (có chủ ý): nhóm 2–5 (bài 6–19) và đề tổng ôn.
- **Không còn chỗ trống:** mọi file mã nguồn (JS, CSS, hai script Python, test, workflow) có đầy đủ nội dung; mỗi bài có mục tiêu, câu chuyện, ý giải thích bắt buộc, code đầy đủ kèm kết quả mong đợi, câu hỏi phỏng vấn kèm gợi ý, lỗi thường gặp, trắc nghiệm đầy đủ đáp án và giải thích, tóm tắt, thuật ngữ.
- **Nhất quán tên:** `kiem_bai`, `lay_khoi`, `kiem_khoi`, `kiem_file`; lớp CSS/thuộc tính `quiz`, `cau-hoi`, `data-dap-an`, `giai-thich`, `data-bai`, `diem`; khóa `localStorage` `cpp-interview-short-term:diem:<NN>`; marker `// bo-qua-kiem-tra`.
- **Điều kiểm chứng được và không:** test `unittest` tự động cho hai script. JavaScript trắc nghiệm **không có test tự động** (máy chưa cài Node), nên kiểm bằng danh sách thao tác tay ở Task 2 Step 7.
