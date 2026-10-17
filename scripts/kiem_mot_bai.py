#!/usr/bin/env python3
"""Kiểm tra nhanh MỘT hoặc vài file bài (dùng khi đang viết, trước khi tích hợp nav/tiến độ).

Chạy: kiem_bai (cấu trúc, quiz, tóm tắt) + biên dịch và chạy mọi khối ```cpp
(có thêm ThreadSanitizer cho khối dùng luồng).

Dùng:  python3 scripts/kiem_mot_bai.py docs/nhom-X/NN-ten.md [...]
Thoát mã 1 nếu có lỗi.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kiem_cau_truc  # noqa: E402
import kiem_code  # noqa: E402


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    os.environ["KIEM_TSAN"] = "1"
    loi = []
    for ten in argv[1:]:
        f = pathlib.Path(ten)
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^(\d{2})-", f.name)
        loi += kiem_cau_truc.kiem_bai(str(f), text, m.group(1) if m else None)
        loi += kiem_code.kiem_file(f)
        dong = len(text.splitlines())
        print(f"{f}: {dong} dòng, {len(kiem_code.lay_khoi(text))} khối code")
    for d in loi:
        print(d)
    print(f"{len(loi)} lỗi")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
