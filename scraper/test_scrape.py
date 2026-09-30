"""抓取脚本的离线测试（不访问网络）。运行：python3 -m unittest scraper/test_scrape.py"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scrape  # noqa: E402

LIST_HTML = """
<tr>
    <td class="td-number">2026-09-30</td>
    <td class="td-number">2026273</td>
    <td class="td-number">
    <span class="ball-list red">30</span>
    <span class="ball-list red">03</span>
    <span class="ball-list red">25</span>
    <span class="ball-list red">28</span>
    <span class="ball-list red">06</span>
    <span class="ball-list red">17</span>
    <span class="ball-list kjhblue">5</span>
    </td>
"""


class ScrapeTest(unittest.TestCase):
    def test_parse_list(self):
        self.assertEqual(scrape.parse_list(LIST_HTML), [{"date": "2026-09-30", "issue": 273, "nums": [30, 3, 25, 28, 6, 17, 5]}])

    def test_parse_list_rejects_bad_draw(self):
        with self.assertRaises(ValueError):
            scrape.parse_list(LIST_HTML.replace(">17<", ">30<"))  # 号码重复

    def test_zodiacs_2026_09_30(self):
        # 与网站详情页一致：牛 龙 马 兔 牛 虎 + 虎
        draw = scrape.with_zodiacs({"date": "2026-09-30", "issue": 273, "nums": [30, 3, 25, 28, 6, 17, 5]}, check_detail=False)
        self.assertEqual(draw["zodiacs"], "牛龙马兔牛虎虎")

    def test_benming_switches_on_spring_festival(self):
        self.assertEqual(scrape.benming_by_date("2026-02-16"), "蛇")
        self.assertEqual(scrape.benming_by_date("2026-02-17"), "马")
        self.assertEqual(scrape.benming_by_date("2027-02-06"), "羊")

    def test_derived_zodiacs_match_history(self):
        # 推算规则与已有数据（原站标注的生肖）逐期一致
        draws = json.loads((Path(__file__).parent.parent / "data" / "draws.json").read_text("utf-8"))
        for d in draws:
            with self.subTest(date=d["date"], issue=d["issue"]):
                bm = scrape.benming_by_date(d["date"])
                self.assertEqual("".join(scrape.zodiac_of(n, bm) for n in d["nums"]), d["zodiacs"])


if __name__ == "__main__":
    unittest.main()
