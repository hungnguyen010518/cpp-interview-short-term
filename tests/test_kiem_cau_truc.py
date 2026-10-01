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
