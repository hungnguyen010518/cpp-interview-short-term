#!/usr/bin/env python3
"""Kiểm tra cấu trúc bài học — những lỗi mà `mkdocs build --strict` KHÔNG bắt được.

1. Có khối mục tiêu và đủ 7 heading emoji theo đúng thứ tự.
2. Đúng một khối <div class="quiz">, 6–8 câu; mỗi câu có 3–4 lựa chọn,
   data-dap-an nằm trong 1..số lựa chọn, đúng một <p class="giai-thich">.
3. Khối 🔑 Tóm tắt có đúng 5 dòng đánh số.
4. Dòng trống ngay trước danh sách lựa chọn (nếu không Markdown gộp lựa chọn
   vào đoạn văn và câu hỏi không bấm được).
5. data-bai của quiz khớp tiền tố NN của tên file, không trùng giữa các bài,
   và docs/tien-do.md có đúng một dòng <span class="diem" data-bai="NN"> cho mỗi bài.

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
DATA_BAI = re.compile(r'<div class="quiz" data-bai="([^"]*)"')
TIEN_TO_FILE = re.compile(r"^(\d{2})-")
DIEM_TIEN_DO = re.compile(r'<span class="diem" data-bai="([^"]*)"')


def lay_lua_chon(noi_dung: str) -> tuple:
    """Đếm các lựa chọn: danh sách `- ` liền mạch cuối cùng trước khối giai-thich.

    Trả về (số lựa chọn, có dòng trống ngay trước danh sách không)."""
    truoc = noi_dung.split('<p class="giai-thich"', 1)[0]
    dong = [d for d in truoc.split("\n")]
    while dong and not dong[-1].strip():
        dong.pop()
    n = 0
    while dong and LUA_CHON.match(dong[-1]):
        n += 1
        dong.pop()
    co_dong_trong = n == 0 or not dong or not dong[-1].strip()
    return n, co_dong_trong


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
        so, co_dong_trong = lay_lua_chon(noi_dung)
        if not co_dong_trong:
            loi.append(f"{ten}: câu {k} thiếu dòng trống giữa câu hỏi và các lựa chọn "
                       "(Markdown sẽ gộp lựa chọn vào đoạn văn, không bấm được)")
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


def kiem_data_bai(ten: str, text: str, nn: str) -> list:
    m = DATA_BAI.search(text)
    if not m:
        return []  # đã báo thiếu/sai quiz ở kiem_quiz
    if m.group(1) != nn:
        return [f"{ten}: data-bai={m.group(1)!r} phải bằng {nn!r} (tiền tố tên file)"]
    return []


def kiem_trung_data_bai(theo_file: dict) -> list:
    """theo_file: {tên file: data-bai}. Báo lỗi nếu hai file dùng chung một giá trị."""
    thay = {}
    loi = []
    for ten, v in theo_file.items():
        if v in thay:
            loi.append(f"data-bai={v!r} trùng giữa {thay[v]} và {ten}")
        else:
            thay[v] = ten
    return loi


def kiem_tien_do(duong_dan: pathlib.Path, cac_bai: list) -> list:
    """Mỗi bài phải có đúng một dòng diem trong tien-do.md, và không có dòng thừa."""
    if not duong_dan.is_file():
        return [f"{duong_dan}: không tìm thấy trang tiến độ"]
    co = DIEM_TIEN_DO.findall(duong_dan.read_text(encoding="utf-8"))
    loi = []
    for nn in cac_bai:
        if co.count(nn) != 1:
            loi.append(f'{duong_dan}: cần đúng 1 dòng <span class="diem" '
                       f'data-bai="{nn}">, đang có {co.count(nn)}')
    for nn in sorted(set(co) - set(cac_bai)):
        loi.append(f'{duong_dan}: có dòng data-bai="{nn}" nhưng không có bài tương ứng')
    return loi


def kiem_bai(ten: str, text: str, nn: str = None) -> list:
    loi = []
    if nn is not None:
        loi += kiem_data_bai(ten, text, nn)
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
    if not goc.is_dir():
        print(f"Lỗi: không tìm thấy thư mục docs {str(goc)!r}")
        return 1
    loi = []
    cac_bai = []
    theo_file = {}
    for f in sorted(goc.glob("nhom-*/*.md")):
        text = f.read_text(encoding="utf-8")
        m = TIEN_TO_FILE.match(f.name)
        if not m:
            loi.append(f"{f}: tên file bài phải bắt đầu bằng NN- (hai chữ số)")
        else:
            cac_bai.append(m.group(1))
        loi += kiem_bai(str(f), text, m.group(1) if m else None)
        d = DATA_BAI.search(text)
        if d:
            theo_file[str(f)] = d.group(1)
    loi += kiem_trung_data_bai(theo_file)
    if cac_bai:
        loi += kiem_tien_do(goc / "tien-do.md", cac_bai)
    for dong in loi:
        print(dong)
    print(f"{len(loi)} lỗi cấu trúc")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
