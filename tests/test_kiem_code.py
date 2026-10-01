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
