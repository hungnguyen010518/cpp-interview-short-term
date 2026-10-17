#!/usr/bin/env python3
"""Biên dịch và chạy mọi khối ```cpp trong các bài học.

Mỗi khối là một chương trình đầy đủ: phải biên dịch được với
`g++ -std=c++17 -Wall -pthread`, chạy dưới 5 giây và thoát mã 0.
Khối có dòng đầu tiên `// bo-qua-kiem-tra` (minh họa hành vi không xác định)
được bỏ qua.

Đặt biến môi trường KIEM_TSAN=1 để các khối có dùng luồng (<thread>, <future>)
được biên dịch thêm với -fsanitize=thread và phải chạy sạch cảnh báo.

Dùng:  python3 scripts/kiem_code.py [thu_muc_docs]
Thoát mã 1 nếu có khối lỗi.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

BO_QUA = "// bo-qua-kiem-tra"
KHOI = re.compile(
    r"^(?P<thut>[ \t]*)```cpp(?=[ \t\n])[^\n]*\n(?P<code>.*?)^(?P=thut)```[ \t]*$",
    re.S | re.M)
MO_DAU = re.compile(r"^[ \t]*```cpp(?=[ \t\n]|\Z)", re.M)


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


DUNG_LUONG = re.compile(r"#include\s*<(thread|future)>")


def lay_co_bien_dich(code: str) -> list:
    co = ["-std=c++17", "-Wall", "-pthread"]
    if os.environ.get("KIEM_TSAN") == "1" and DUNG_LUONG.search(code):
        co += ["-g", "-fsanitize=thread"]
    return co


def kiem_khoi(code: str):
    """Trả về None nếu ổn, ngược lại là thông báo lỗi."""
    if code.lstrip().startswith(BO_QUA):
        return None
    with tempfile.TemporaryDirectory() as d:
        nguon = pathlib.Path(d) / "a.cpp"
        chay = pathlib.Path(d) / "a.out"
        nguon.write_text(code, encoding="utf-8")
        co = lay_co_bien_dich(code)
        bd = subprocess.run(
            ["g++", *co, "-o", str(chay), str(nguon)],
            capture_output=True, text=True)
        if bd.returncode != 0:
            return "biên dịch lỗi:\n" + bd.stderr
        try:
            lenh = [str(chay)]
            if "-fsanitize=thread" in co and shutil.which("setarch"):
                # kernel mới đặt ASLR cao hơn mức TSan chịu được; tắt ASLR cho tiến trình con
                lenh = ["setarch", "x86_64", "-R"] + lenh
            kq = subprocess.run(lenh, capture_output=True, text=True, timeout=5,
                stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return "chạy quá 5 giây"
        if kq.returncode != 0:
            return f"chạy trả mã {kq.returncode}\n{kq.stderr}"
    return None


def kiem_file(duong: pathlib.Path) -> list:
    loi = []
    text = duong.read_text(encoding="utf-8")
    khoi = lay_khoi(text)
    da_lay = {so for so, _ in khoi}
    mo = [text.count("\n", 0, m.start()) + 1 for m in MO_DAU.finditer(text)]
    if len(mo) != len(khoi):
        chua = next((so for so in mo if so not in da_lay), None)
        vi_tri = f":{chua}" if chua else ""
        loi.append(f"{duong}{vi_tri}: có {len(mo)} dòng mở ```cpp nhưng chỉ lấy được "
                   f"{len(khoi)} khối (khối không đóng hoặc đóng sai thụt lề)")
    for so_dong, code in khoi:
        ket_qua = kiem_khoi(code)
        if ket_qua:
            loi.append(f"{duong}:{so_dong}: {ket_qua}")
    return loi


def main(argv: list) -> int:
    goc = pathlib.Path(argv[1] if len(argv) > 1 else "docs")
    if not goc.is_dir():
        print(f"Lỗi: không tìm thấy thư mục docs {str(goc)!r}")
        return 1
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
