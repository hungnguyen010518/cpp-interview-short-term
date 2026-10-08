# Bài 43 — Git: lịch sử, nhánh, gộp và cứu lỗi

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Giải thích được **commit** (một ảnh chụp cả dự án kèm lời ghi chú), **staging** (khu chọn món sẽ chụp), **nhánh** (một cái nhãn trỏ vào commit) và vì sao `git add` rồi `git commit` là hai bước, bằng lệnh chạy thật trong một thư mục tạm.
    - Phân biệt **merge** (giữ nguyên lịch sử, thêm commit gộp) với **rebase** (viết lại commit lên nền mới), biết khi nào được dùng rebase, và giải được **conflict** (hai nhánh sửa cùng chỗ).
    - Cứu lỗi đúng công cụ: `stash` (cất việc dở), `restore` (bỏ thay đổi chưa commit), `reset` (lùi nhánh), `revert` (đảo ngược bằng commit mới), `reflog` (tìm lại commit "mất"), `bisect` (nhị phân tìm commit gây lỗi).
    - Viết được `.gitignore`, một thông điệp commit rõ ràng, và biết Go và Git liên quan nhau ở đâu.

**Bạn cần biết trước:** dùng được dòng lệnh (`cd`, `ls`, `cat`). Bài này **không** cần bài C++ nào; các bài sau (build, gỡ lỗi) giả định bạn đã quen `git status` và `git log`.

## 🧠 Câu chuyện mở đầu

Bạn làm bài tập lớn suốt một tuần trên một cuốn vở. Hôm thứ Tư bài chạy tốt, thứ Năm bạn sửa lung tung, thứ Sáu nó hỏng và bạn **không nhớ** mình đã đổi gì. Giá mà mỗi tối bạn chụp cả cuốn vở lại và dán nhãn "tối thứ Tư: chạy tốt".

**Git** là chương trình làm đúng việc đó cho thư mục mã nguồn: mỗi lần bạn bảo, nó chụp một **ảnh** (gọi là **commit**) kèm lời ghi chú, và nhớ ảnh nào đứng sau ảnh nào. Nhờ vậy bạn xem lại được mọi thời điểm, quay về được, thử ý tưởng riêng ở "nhánh" mà không đụng bản chính, và tìm ra **ảnh nào** làm bài hỏng.

!!! info "Chỗ nào ví von không còn đúng?"
    Ảnh chụp ngoài đời nặng, còn commit của Git rất nhẹ vì nó chỉ lưu phần khác nhau và chia sẻ phần giống. Ngoài đời bạn không "gộp hai cuốn vở", còn Git gộp được hai nhánh sửa riêng. Ví von chỉ dùng ở đoạn mở đầu; các ví dụ bên dưới là lệnh thật.

## 📖 Giải thích

### 1. Ba khu vực: thư mục làm việc, staging, lịch sử

Git có ba chỗ để một thay đổi đi qua. **Thư mục làm việc** là các file bạn đang sửa. **Staging** (khu chuẩn bị, còn gọi là *index*) là danh sách thay đổi bạn đã chọn để đưa vào ảnh sắp chụp. **Lịch sử** là các commit đã chụp.

`git add file` chuyển thay đổi từ thư mục làm việc sang staging; `git commit` chụp đúng thứ đang ở staging. Tách hai bước để bạn chụp **một việc gọn** dù trong thư mục đang sửa dở ba việc. Ví dụ 1 cho thấy `git status --short` đổi từ `??` sang `A` sang sạch.

### 2. Commit, mã băm và nhánh

Mỗi commit có một **mã băm** (hash, chuỗi hex dài 40 ký tự mà Git hay cắt còn 7), một lời ghi chú, tác giả, và **con trỏ tới commit cha**. Chuỗi cha-con đó là lịch sử. Mã băm tính từ nội dung, nên **đổi thời điểm chạy là đổi mã**: đừng chép mã trong bài này làm chuẩn.

**Nhánh** (branch) chỉ là một cái **nhãn** trỏ vào một commit, và nhãn tự đi theo khi bạn commit thêm. Vì vậy tạo nhánh gần như miễn phí. `HEAD` là "bạn đang đứng ở đâu" (thường trỏ vào tên một nhánh). `git switch -c ten` tạo và chuyển sang nhánh mới; `git switch ten` chuyển sang nhánh đã có.

### 3. Merge: gộp hai nhánh bằng một commit gộp

`git merge nhanh-a` (đứng ở `main`) gom thay đổi của `nhanh-a` vào `main`. Nếu hai nhánh sửa **chỗ khác nhau**, Git tự gộp và tạo một **commit gộp** có hai cha. Lịch sử giữ nguyên hình dạng thật: có chỗ tách, có chỗ nhập (Ví dụ 2).

### 4. Conflict: hai nhánh sửa cùng một chỗ

Nếu cả hai nhánh sửa **cùng dòng**, Git không dám đoán và dừng lại: file đó thành `UU` (cả hai bên đã sửa) và Git chèn **dấu xung đột** vào file. Phần giữa `<<<<<<< HEAD` và `=======` là bản của nhánh bạn đang đứng; phần giữa `=======` và `>>>>>>> ten-nhanh` là bản của nhánh đến.

Bạn giải bằng cách **sửa file thành nội dung cuối cùng bạn muốn** (xóa hết ba loại dấu), `git add file`, rồi `git commit`. Đổi ý thì `git merge --abort` trả mọi thứ về trước khi gộp. Conflict là chuyện bình thường của làm việc nhóm, không phải sự cố.

### 5. Rebase: dời nhánh sang nền mới

**Rebase** lấy các commit riêng của nhánh bạn, "nhấc" chúng lên, rồi **phát lại từng cái** lên đỉnh nhánh kia. Kết quả là một đường thẳng, không có commit gộp (Ví dụ 3). Cái giá: các commit được phát lại là **commit mới với mã băm mới**; commit cũ bị bỏ lại.

Quy tắc vàng: **không rebase nhánh mà người khác đã lấy về**. Họ vẫn giữ commit cũ, còn bạn đẩy lên commit mới cùng tên: hai bên lệch nhau và phải dọn rất mệt. Rebase nhánh riêng của mình trước khi chia sẻ thì ổn. Merge an toàn hơn vì không viết lại gì; rebase cho lịch sử gọn hơn.

### 6. Cứu lỗi: chọn đúng công cụ

Câu hỏi đầu tiên luôn là: thay đổi đó **đã commit chưa, đã chia sẻ chưa**?

| Tình huống | Lệnh | Điều nó làm |
|---|---|---|
| Đang sửa dở, cần chuyển việc | `git stash` rồi `git stash pop` | Cất thay đổi chưa commit vào ngăn riêng, lấy lại sau |
| Bỏ thay đổi chưa commit ở một file | `git restore file` | Đưa file về như commit gần nhất (**mất** thay đổi đó) |
| Bỏ một file khỏi staging, giữ nội dung | `git restore --staged file` | Chỉ rút khỏi khu chọn |
| Commit nhầm, **chưa** chia sẻ | `git reset --soft HEAD~1` hoặc `--hard` | Lùi nhãn nhánh; `--soft` giữ thay đổi ở staging, `--hard` **vứt** |
| Commit sai, **đã** chia sẻ | `git revert HEAD` | Thêm một commit mới làm việc ngược lại; lịch sử không bị viết lại |
| Lỡ `reset --hard`, "mất" commit | `git reflog` | Xem lịch sử các nơi `HEAD` từng đứng, quay lại được |
| Có lỗi, không biết commit nào gây ra | `git bisect` | Chia đôi khoảng nghi ngờ, kiểm từng nấc |

`git reflog` là lưới an toàn: Git ghi lại mọi lần `HEAD` di chuyển, và commit "mất" vẫn nằm đó một thời gian (mặc định hàng tuần) trước khi bị dọn. Nhưng chỉ thay đổi **đã commit** mới cứu được; thay đổi chưa commit mà bị `restore` hay `reset --hard` thì đi luôn.

### 7. Bisect: tìm commit gây lỗi bằng chia đôi

Bạn biết commit cũ X **tốt** và commit mới Y **hỏng**, ở giữa có N commit. `git bisect` chọn commit giữa, bạn kiểm (đúng/hỏng), nó loại một nửa, lặp lại. Tìm trong N commit cần khoảng log₂N lần kiểm: 100 commit chỉ cỡ 7 lần, thay vì kiểm 100.

Nếu bạn có một lệnh trả mã thoát 0 khi tốt và khác 0 khi hỏng (ví dụ chạy test), `git bisect run lệnh` làm hết việc tự động (Ví dụ 5). Đó cũng là lý do nên commit **nhỏ và thường xuyên**: commit càng nhỏ, commit thủ phạm càng dễ khoanh.

### 8. `.gitignore` và quy ước commit

File `.gitignore` liệt kê mẫu tên file mà Git **bỏ qua**: sản phẩm build (`*.o`, `build/`), file tạm của trình soạn thảo, thông tin bí mật. Với dự án C++, đừng commit file chạy và file đối tượng: chúng sinh lại được và làm repo phình. `git check-ignore -v file` cho biết dòng nào đang chặn file.

`.gitignore` chỉ ảnh hưởng file **chưa được theo dõi**. File lỡ commit rồi thì thêm vào `.gitignore` cũng vô ích; phải `git rm --cached file` để Git thôi theo dõi (file trên đĩa vẫn còn).

Về thông điệp commit: dòng đầu ngắn (khoảng 50 ký tự), nói **làm gì và vì sao**, không nói "sửa lỗi" chung chung. Nhiều nhóm dùng tiền tố như `feat:` (tính năng), `fix:` (sửa lỗi), `docs:`, `refactor:`. Mỗi commit một việc, để `revert` và `bisect` có chỗ bám.

## 💻 Ví dụ code

Mọi ví dụ dưới đây mình chạy bằng Git 2.43.0 trong một thư mục tạm, với danh tính giả `Ban Hoc <ban@example.com>`. Kết quả đã **rút gọn** (bỏ dòng trống, bớt thông báo gợi ý). **Mã băm và ngày giờ đổi mỗi lần chạy**, nên bạn sẽ thấy mã khác.

### Ví dụ 1: Thư mục làm việc, staging, commit, log

Lần đầu làm quen: `git status --short` cho mỗi file một cột ký hiệu. `??` là file chưa được theo dõi, `A` là đã thêm vào staging, `M` là đã sửa.

```bash
git init -q -b main .
echo "xin chao" > a.txt
git status --short            # (1)
git add a.txt
git status --short            # (2)
git commit -q -m "feat: them a.txt"
echo "dong 2" >> a.txt
git diff                      # (3)
git add a.txt
git commit -q -m "feat: them dong 2"
git log --oneline             # (4)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| `git init` | Tạo kho trống, nhánh `main` | chưa có commit |
| (1) | `a.txt` chưa được theo dõi | thư mục làm việc: `a.txt` |
| (2) | Sau `add`, `a.txt` ở staging | staging: `a.txt` |
| `commit` | Chụp ảnh đầu tiên | lịch sử: 1 commit |
| (3) | `diff` chỉ ra dòng `+dong 2` thêm vào so với commit | chưa vào staging |
| (4) | `log` liệt kê commit mới nhất ở trên | lịch sử: 2 commit |

**Kết quả khi chạy:**

```text
?? a.txt
A  a.txt
diff --git a/a.txt b/a.txt
@@ -1 +1,2 @@
 xin chao
+dong 2
568f9d8 feat: them dong 2
f7b3394 feat: them a.txt
```

Mình chạy thật. Ký hiệu hai cột của `A  ` là (staging, thư mục làm việc); khi bạn sửa file đã commit, ta thấy ` M` (sửa, chưa vào staging) rồi `M ` (đã vào staging).

### Ví dụ 2: Nhánh, merge và conflict

Ta tạo `nhanh-a` thêm `b.txt`, đồng thời `main` thêm `c.txt` (hai nhánh sửa file khác nhau), gộp; rồi cho hai nhánh sửa **cùng dòng** của `a.txt` để thấy conflict.

```bash
git switch -q -c nhanh-a
echo "tu nhanh a" > b.txt; git add b.txt; git commit -q -m "feat: b.txt"    # (1)
git switch -q main
echo "tu main" > c.txt; git add c.txt; git commit -q -m "feat: c.txt"       # (2)
git merge --no-edit nhanh-a                                                  # (3)
git log --oneline --graph                                                    # (4)

git switch -q -c x; echo "ban x" > a.txt; git commit -qam "x sua a"          # (5)
git switch -q main; echo "ban main" > a.txt; git commit -qam "main sua a"    # (6)
git merge x                                                                  # (7)
git status --short
cat a.txt
git merge --abort                                                            # (8)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | Commit trên `nhanh-a` | `nhanh-a` đi trước 1 commit |
| (2) | Commit trên `main`: lịch sử rẽ đôi | hai nhánh cùng cha, mỗi nhánh 1 commit riêng |
| (3), (4) | Hai nhánh sửa file khác nhau nên tự gộp; `log` vẽ hình thoi | `main` có thêm 1 commit gộp, 2 cha |
| (5), (6) | Hai nhánh sửa **cùng dòng** `a.txt` thành hai giá trị | chưa gộp |
| (7) | Git dừng: conflict ở `a.txt` | `a.txt` chứa dấu xung đột |
| (8) | Hủy việc gộp | trở về trước (7) |

**Kết quả khi chạy:**

```text
*   e4938d8 Merge branch 'nhanh-a'
|\  
| * 92eb052 feat: b.txt
* | 7c6c415 feat: c.txt
|/  
* 568f9d8 feat: them dong 2
* f7b3394 feat: them a.txt
Auto-merging a.txt
CONFLICT (content): Merge conflict in a.txt
Automatic merge failed; fix conflicts and then commit the result.
UU a.txt
<<<<<<< HEAD
ban main
=======
ban x
>>>>>>> x
```

Mình chạy thật. Muốn **giải** conflict (thay vì hủy ở (8)): sửa `a.txt` thành `ban main + ban x`, rồi `git add a.txt` và `git commit --no-edit`. Mình chạy cách này ở một kho khác và lịch sử cuối là một commit gộp có hai cha, `a.txt` mang nội dung bạn viết.

### Ví dụ 3: Rebase

Một nhánh `y` tách từ cách đây ba commit; ta rebase lên đỉnh `main` để lịch sử thành một đường thẳng.

```bash
git switch -q -c y HEAD~3          # (1)
echo y > y.txt; git add y.txt; git commit -q -m "y"
git rebase main                    # (2)
git log --oneline --graph          # (3)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | Nhánh `y` bắt đầu từ commit cũ | `y` cách đỉnh `main` vài commit |
| (2) | Phát lại commit `y` lên đỉnh `main` | commit `y` được tạo lại, **mã băm mới** |
| (3) | `log` thành đường thẳng | `y` nằm trên đỉnh `main` |

**Kết quả khi chạy (đoạn đầu):**

```text
Successfully rebased and updated refs/heads/y.
* 71cc486 y
* a8d014a main sua a
*   e4938d8 Merge branch 'nhanh-a'
```

Mình chạy thật. Trước rebase commit `y` mang mã `e9867dc`; sau rebase là `71cc486`: cùng lời ghi chú, **khác mã**, đúng như mục 5 nói. Rebase cũng gặp conflict khi hai bên sửa cùng chỗ: nó dừng, bạn sửa, `git add`, `git rebase --continue`, hoặc bỏ cuộc bằng `git rebase --abort` (mình có chạy `--abort` và nhánh về nguyên trạng).

### Ví dụ 4: stash, restore, reset, revert, reflog

Một kho có file `n.txt`, hai commit với nội dung `1` rồi `2`. Ta thử từng công cụ cứu lỗi.

```bash
echo dang-lam-do > n.txt
git stash -q; cat n.txt          # (1)
git stash pop -q; cat n.txt      # (2)
git restore n.txt; cat n.txt     # (3)

echo 3 > n.txt; git commit -qam "v3-loi"
git reset -q --hard HEAD~1; cat n.txt     # (4)
git reflog | head -2             # (5)
git reset -q --hard HEAD@{1}; cat n.txt   # (6)
git revert --no-edit HEAD >/dev/null; cat n.txt; git log --oneline   # (7)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | `stash` cất thay đổi, file về như commit | `n.txt` = `2`; ngăn stash có 1 mục |
| (2) | `stash pop` lấy lại | `n.txt` = `dang-lam-do` |
| (3) | `restore` bỏ thay đổi chưa commit | `n.txt` = `2` (thay đổi **mất hẳn**) |
| (4) | `reset --hard HEAD~1` lùi nhánh một commit | commit `v3-loi` rời khỏi `log` |
| (5) | `reflog` vẫn thấy nơi `HEAD` từng đứng | `v3-loi` còn trong reflog |
| (6) | `HEAD@{1}` là nơi `HEAD` đứng trước đó | `n.txt` = `3`, `v3-loi` trở lại |
| (7) | `revert` thêm commit đảo ngược `v3-loi` | `n.txt` = `2`, lịch sử có 4 commit |

**Kết quả khi chạy:**

```text
2
dang-lam-do
2
2
6196c42 HEAD@{0}: reset: moving to HEAD~1
1a4cea6 HEAD@{1}: commit: v3-loi
3
2
9d9228f Revert "v3-loi"
1a4cea6 v3-loi
6196c42 v2
1e2f32c v1
```

Mình chạy thật đúng chuỗi lệnh này (kho có sẵn hai commit `v1`, `v2`). Điểm cần nhớ ở (7): `revert` **không xóa** `v3-loi` mà thêm một commit mới nên an toàn với nhánh đã chia sẻ; `reset --hard` viết lại lịch sử nên chỉ dùng với commit chưa ai lấy.

### Ví dụ 5: `.gitignore` và `bisect run`

Phần đầu: ignore. Phần sau: chín commit, trong đó commit "v10 hong" ghi `0` vào `n.txt` làm hỏng; một script `test.sh` trả mã khác 0 khi `n.txt` là `0`; `bisect` tự tìm thủ phạm.

```bash
printf '*.o\nbuild/\n' > .gitignore
touch x.o; mkdir build; touch build/y
git status --short                 # (1)
git check-ignore -v x.o            # (2)

cat > test.sh <<'E'
#!/bin/sh
[ "$(cat n.txt)" != "0" ]
E
git bisect start HEAD HEAD~8       # (3)
git bisect run sh test.sh          # (4)
git bisect reset                   # (5)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | `x.o` và `build/` không hiện; chỉ `.gitignore` mới là lạ | `?? .gitignore` |
| (2) | Chỉ ra dòng 1 của `.gitignore` chặn `x.o` | |
| (3) | Báo `HEAD` hỏng, `HEAD~8` tốt | 8 commit nghi ngờ |
| (4) | Chạy `test.sh` ở các commit giữa, loại dần một nửa | nhảy qua `v9`, rồi `v10 hong` |
| (5) | Quay lại nhánh gốc | `HEAD` về `main` |

**Kết quả khi chạy (rút gọn):**

```text
?? .gitignore
.gitignore:1:*.o	x.o
Bisecting: 1 revision left to test after this (roughly 1 step)
[c215c751dbfd949266716764610835918710f903] v9
Bisecting: 0 revisions left to test after this (roughly 0 steps)
[fb1b54468ba76831fe4d3977d06d78506efca96a] v10 hong
fb1b54468ba76831fe4d3977d06d78506efca96a is the first bad commit
    v10 hong
```

Mình chạy thật. Trong 8 commit nghi ngờ, `bisect` kiểm vài lần rồi chỉ đúng `v10 hong`. Số lần kiểm là khoảng log₂ của số commit, không phải 8.

**Thử thay đổi** (đã chạy):

- Commit file `a.out` trước, rồi thêm `a.out` vào `.gitignore` và sửa `a.out`: `git status` **vẫn** báo ` M a.out`. Chạy `git rm --cached a.out` thì Git báo `D  a.out` (thôi theo dõi) và file `a.out` vẫn còn trên đĩa.

## Go: Git không liên quan Go, nhưng module Go dựa vào nó

!!! info "Bạn biết Go?"
    - **Không liên quan trực tiếp**: Git là công cụ riêng, không phải thư viện của Go hay C++. Mọi lệnh trong bài giống nhau cho dự án Go, C++ hay thứ khác; `.gitignore` của Go thường ghi tên file chạy được, của C++ ghi `*.o` và `build/`.
    - **Điểm chạm duy nhất**: phiên bản module Go như `v1.2.3` tương ứng với **tag** của repo Git chứa module đó; `go get` lấy mã qua Git. Đây là điều mình biết từ cách Go module hoạt động, **mình chưa chạy** `go get` trong bài này.
    - **Thói quen chung**: nhánh ngắn, commit nhỏ, `bisect run` với `go test` hay chương trình C++ đều dùng được vì `bisect run` chỉ cần mã thoát 0 hoặc khác 0.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "`git merge` và `git rebase` khác nhau thế nào? Khi nào dùng cái nào?"
    Merge tạo một commit gộp có hai cha, giữ nguyên lịch sử thật, không viết lại gì nên an toàn với nhánh đã chia sẻ. Rebase phát lại commit của nhánh bạn lên nền mới, cho đường thẳng gọn, nhưng tạo commit **mới với mã băm mới**. Dùng rebase cho nhánh riêng trước khi chia sẻ; không rebase nhánh người khác đã lấy về.

??? question "Staging dùng để làm gì? Sao không commit thẳng?"
    Staging cho phép chọn **đúng những thay đổi** vào commit tiếp theo, dù thư mục đang sửa dở nhiều việc. Nhờ đó mỗi commit là một việc gọn, dễ `revert` và dễ `bisect`. (`git commit -a` bỏ qua bước `add` cho file đã theo dõi, nhưng không thêm file mới.)

??? question "Lỡ `git reset --hard` làm mất commit, cứu thế nào?"
    Dùng `git reflog` để xem các nơi `HEAD` từng đứng, tìm dòng trước lúc lỡ tay, rồi `git reset --hard HEAD@{N}` hoặc `git switch -c nhanh-cuu <mã>`. Chỉ cứu được **commit đã có**; thay đổi chưa commit mà bị `--hard` hay `restore` thì mất.

??? question "`reset` khác `revert` thế nào?"
    `reset` dời nhãn nhánh về commit cũ (viết lại lịch sử), chỉ hợp commit chưa chia sẻ. `revert` thêm một commit mới có tác dụng ngược lại commit cần bỏ; lịch sử giữ nguyên nên an toàn cho nhánh chung.

??? question "Giải conflict thế nào?"
    Mở file `UU`, sửa phần giữa các dấu `<<<<<<<`, `=======`, `>>>>>>>` thành nội dung cuối cùng và xóa hết dấu, `git add file`, rồi `git commit` (hoặc `git rebase --continue` nếu đang rebase). Đổi ý thì `git merge --abort` hoặc `git rebase --abort`.

??? question "Làm sao tìm commit làm hỏng chương trình trong 500 commit?"
    `git bisect start <hỏng> <tốt>`, rồi kiểm từng commit Git đưa ra (`git bisect good` hay `bad`) hoặc dùng `git bisect run <lệnh>` với lệnh trả mã khác 0 khi hỏng. 500 commit cần chừng 9 lần kiểm (log₂500 ≈ 9).

??? question "`git fetch` khác `git pull`? `git stash` dùng khi nào?"
    `fetch` chỉ tải commit mới về mà chưa đụng nhánh của bạn; `pull` là `fetch` rồi gộp (merge hoặc rebase). `stash` cất việc dở khi phải chuyển nhánh gấp. Mình **chưa chạy** `fetch`/`pull` trong bài này vì cần một kho từ xa.

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: `git reset --hard` hay `git restore` khi còn thay đổi chưa commit"
    Hai lệnh này **vứt** thay đổi chưa commit mà không hỏi, reflog cũng không cứu được. Chưa chắc thì `git stash` trước, hoặc commit tạm rồi sửa sau. Kiểm tra `git status` và `git diff` trước khi dùng.

!!! warning "Lỗi 2: Rebase nhánh đã chia sẻ, hoặc commit file build"
    Rebase nhánh người khác đã lấy về làm lịch sử hai bên lệch nhau (mục 5). Và commit `a.out`, `*.o`, `build/` làm kho phình và gây conflict vô nghĩa: viết `.gitignore` ngay từ commit đầu, và nhớ rằng thêm vào `.gitignore` sau khi lỡ commit thì phải `git rm --cached` (Ví dụ 5).

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="43" markdown>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 1.** Đọc chuỗi lệnh sau. Cuối cùng `cat f.txt` in gì?

```text
echo "a" > f.txt
git add f.txt
git commit -q -m "dau"
echo "b" >> f.txt
git restore f.txt
cat f.txt
```

- `a` và `b` trên hai dòng, vì `restore` chỉ bỏ file khỏi staging
- `a`, vì `restore` đưa file về như commit gần nhất
- Lỗi, vì `restore` chỉ chạy được sau `git add`
- Rỗng, vì `restore` xóa nội dung chưa commit

<p class="giai-thich" markdown>`git restore f.txt` đưa file trong thư mục làm việc về đúng nội dung của commit gần nhất, nên dòng `b` thêm sau đó biến mất và còn `a` (và thay đổi đó mất hẳn, không có lưới an toàn). Việc "chỉ bỏ khỏi staging" là của `git restore --staged`, một lệnh khác với cờ khác. `restore` không đòi `add` trước; thực ra nó dùng được ngay cả khi chưa `add` gì. Và nó không làm file rỗng, nó lấy lại nội dung từ commit.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 2.** Đồng đội đã `git pull` nhánh `tinh-nang` của bạn về máy. Sau đó bạn rebase `tinh-nang` lên `main` rồi đẩy lên. Điều gì xảy ra?

- Không có gì xấu, vì rebase vẫn giữ nguyên mã băm của mọi commit
- Git tự động rebase luôn nhánh của đồng đội khi họ pull
- Mã băm commit đổi, nên nhánh đồng đội và nhánh bạn lệch nhau
- Chỉ commit gộp bị đổi mã, còn commit thường giữ nguyên mã

<p class="giai-thich" markdown>Rebase phát lại từng commit thành **commit mới**, nên mã băm đổi (mình thấy `e9867dc` thành `71cc486`). Đồng đội còn giữ các commit cũ, nên hai bên có lịch sử khác nhau và phải dọn tay. Không có cơ chế nào tự rebase hộ đồng đội. Và rebase không đổi mã chỉ commit gộp: mọi commit được phát lại đều đổi, còn nhánh dạng đường thẳng chẳng có commit gộp nào.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 3.** Bạn gõ `git reset --hard HEAD~1` và nhận ra đã xóa nhầm một commit đã làm xong, rất quan trọng. Thay đổi trong commit đó đã được commit đàng hoàng. Cách nào cứu được?

- `git reflog` để tìm mã cũ, rồi `git reset --hard` về đó
- Không cứu được, vì `reset --hard` xóa vĩnh viễn commit
- `git revert HEAD`, vì nó khôi phục commit bị mất
- `git restore .`, vì nó lấy lại commit từ kho

<p class="giai-thich" markdown>`reset --hard` chỉ dời nhãn nhánh; commit cũ vẫn còn trong kho và `git reflog` ghi lại nơi `HEAD` từng đứng, nên reset về mã đó là lấy lại được (Ví dụ 4, bước 6). Nó không xóa vĩnh viễn ngay; commit chỉ bị dọn sau một thời gian nếu không có gì trỏ tới. `revert HEAD` thêm một commit đảo ngược commit hiện tại, không lấy lại commit bị lùi qua. `restore .` đưa file về như commit hiện tại, không đụng đến commit bị mất.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 4.** Sau `git merge x`, `git status --short` hiện `UU a.txt` và file có đoạn sau. Làm gì tiếp để hoàn tất?

```text
<<<<<<< HEAD
ban main
=======
ban x
>>>>>>> x
```

- Chạy `git commit` ngay: Git sẽ tự chọn bản của `main`
- Chạy `git add a.txt` ngay: Git sẽ tự gỡ các dấu xung đột
- Chạy `git restore a.txt` để Git tự giải xung đột
- Sửa file thành nội dung cuối muốn có, bỏ hết dấu, `git add`, rồi `git commit`

<p class="giai-thich" markdown>Conflict phải do người quyết định nội dung cuối: sửa file cho đúng ý (có thể lấy một bên, hoặc ghép cả hai thành dòng mới), bỏ hết dấu, `git add`, rồi commit. `git commit` ngay khi còn `UU` bị từ chối, và Git không tự chọn bên nào. `git add` chỉ đánh dấu file đã xử lý, không sửa gì trong file, nên dấu xung đột sẽ bị commit nguyên xi nếu bạn không tự bỏ. `restore` chỉ đưa file về trạng thái cũ, không giải được xung đột.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Một commit lỗi đã được đẩy lên nhánh chung, cả nhóm đang dùng. Cách nào hợp lý nhất để bỏ tác dụng của nó?

- `git reset --hard` về trước commit lỗi rồi đẩy ép lên nhánh chung
- Xóa nhánh chung rồi tạo lại nó từ một commit cũ hơn
- `git revert` commit lỗi rồi đẩy lên
- `git stash` để cất commit lỗi đi rồi đẩy lên nhánh chung

<p class="giai-thich" markdown>`revert` thêm một commit mới làm việc ngược lại, nên lịch sử chung chỉ dài thêm và máy của đồng đội vẫn khớp. `reset --hard` rồi đẩy ép viết lại lịch sử mà người khác đã lấy, tạo đúng cảnh lệch nhau như khi rebase nhánh chung. Xóa và tạo lại nhánh cũng làm lịch sử của mọi người lệch. `stash` chỉ cất thay đổi **chưa commit**, không cất được commit đã có.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 6.** Bạn có 100 commit giữa một commit tốt và một commit hỏng. Dùng `git bisect`, cỡ bao nhiêu lần kiểm là đủ để chỉ ra commit đầu tiên hỏng?

- Khoảng 50, vì mỗi lần kiểm chỉ loại được một commit
- Khoảng 7, vì mỗi lần kiểm loại bỏ một nửa
- Khoảng 100, vì phải kiểm từng commit mới chắc chắn được
- Khoảng 25, vì mỗi lần loại được một phần tư số commit

<p class="giai-thich" markdown>`bisect` là tìm kiếm nhị phân: kiểm commit giữa rồi bỏ nửa không chứa thủ phạm, nên cần chừng log₂ 100 ≈ 7 lần. Loại từng commit một sẽ cần cỡ 50 hay 100 lần, đó là cách làm tay chứ không phải `bisect`. Nó cũng không cắt một phần tư mỗi lần: mỗi lần chỉ có hai khả năng (đúng hoặc hỏng) nên chia đôi.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 7.** Đọc đoạn sau. Chuyện gì xảy ra ở `git status --short`?

```text
git add a.out && git commit -m "oops"      # a.out đã được commit
echo "a.out" > .gitignore
echo 2 > a.out
git status --short
```

- Vẫn báo ` M a.out`: file đã theo dõi nên `.gitignore` không có tác dụng
- Không báo gì về `a.out`, vì `.gitignore` bỏ qua mọi file có tên đó
- Báo `?? a.out`, vì Git coi nó là file mới
- Báo lỗi, vì không được vừa ignore vừa theo dõi cùng một file

<p class="giai-thich" markdown>`.gitignore` chỉ áp dụng cho file **chưa được theo dõi**; `a.out` đã nằm trong commit nên Git vẫn so sánh và báo ` M` (mình chạy). Muốn Git bỏ qua nó, phải `git rm --cached a.out` rồi commit. Không có lỗi nào vì Git cho phép tình huống này mà không phàn nàn. Còn `??` chỉ dành cho file chưa từng được theo dõi.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **Commit** là ảnh chụp cả dự án; thay đổi đi từ thư mục làm việc qua **staging** (`git add`) vào **lịch sử** (`git commit`). Mã băm tính từ nội dung nên đổi mỗi lần, và **nhánh** chỉ là nhãn trỏ vào một commit.
2. **Merge** gộp bằng commit có hai cha và giữ nguyên lịch sử; **rebase** phát lại commit lên nền mới thành đường thẳng nhưng tạo commit mới (mình thấy `e9867dc` thành `71cc486`), nên không rebase nhánh đã chia sẻ.
3. **Conflict** xảy ra khi hai nhánh sửa cùng dòng: file thành `UU` với dấu `<<<<<<<`; sửa thành nội dung cuối, `git add`, rồi `git commit`, hoặc `git merge --abort`.
4. Cứu lỗi: `stash` cất việc dở, `restore` bỏ thay đổi chưa commit (mất hẳn), `reset` lùi nhánh (chỉ khi chưa chia sẻ), `revert` đảo ngược bằng commit mới, `reflog` tìm lại commit "mất"; chỉ thứ đã commit mới cứu được.
5. `git bisect run` chia đôi để tìm commit gây lỗi (khoảng log₂N lần kiểm); `.gitignore` chỉ có tác dụng với file chưa theo dõi (lỡ commit thì `git rm --cached`); commit nhỏ, một việc, dòng đầu rõ; Go chỉ chạm Git ở chỗ phiên bản module ứng với tag.
