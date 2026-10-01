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
