"""抓取脚本的离线测试（不访问网络）。运行：python3 -m unittest scraper/test_scrape.py"""
import io
import json
import sys
import unittest
import urllib.error
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

# 手机版列表页的一期（生肖标注按今年的对应关系，往年会标错，只用来核对）
MOBILE_HTML = """
<div class="item">
    <p class="title-left">第 <strong>2026273</strong>期</p>
    <div class="kj-detailss">
        <div class="kjh-wxs"><span class="kj-red"> 30 </span><p>牛/水</p></div>
        <div class="kjh-wxs"><span class="kj-blue"> 03 </span><p>龙/火</p></div>
        <div class="kjh-wxs"><span class="kj-blue"> 25 </span><p>马/木</p></div>
        <div class="kjh-wxs"><span class="kj-green"> 28 </span><p>兔/土</p></div>
        <div class="kjh-wxs"><span class="kj-green"> 06 </span><p>牛/土</p></div>
        <div class="kjh-wxs"><span class="kj-green"> 17 </span><p>虎/木</p></div>
        <div class="jiahaos">+</div>
        <div class="kjh-wxs"><span class="kj-green"> 05 </span><p>虎/金</p></div>
    </div>
</div>
</section>
"""


class ScrapeTest(unittest.TestCase):
    def test_parse_list(self):
        self.assertEqual(scrape.parse_list(LIST_HTML), [{"date": "2026-09-30", "issue": 273, "nums": [30, 3, 25, 28, 6, 17, 5]}])

    def test_parse_list_rejects_bad_draw(self):
        with self.assertRaises(ValueError):
            scrape.parse_list(LIST_HTML.replace(">17<", ">30<"))  # 号码重复

    def test_zodiacs_2026_09_30(self):
        # 与网站详情页一致：牛 龙 马 兔 牛 虎 + 虎
        draw = scrape.with_zodiacs({"date": "2026-09-30", "issue": 273, "nums": [30, 3, 25, 28, 6, 17, 5]}, check_site=False)
        self.assertEqual(draw["zodiacs"], "牛龙马兔牛虎虎")

    def test_parse_mobile(self):
        self.assertEqual(scrape.parse_mobile(MOBILE_HTML), [{
            "date": "2026-09-30", "issue": 273, "nums": [30, 3, 25, 28, 6, 17, 5], "labels": "牛龙马兔牛虎虎",
        }])

    def test_date_of_issue(self):
        # 期号就是当年第几天
        self.assertEqual(scrape.date_of_issue(2026, 273), "2026-09-30")
        self.assertEqual(scrape.date_of_issue(2024, 366), "2024-12-31")
        self.assertEqual(scrape.date_of_issue(2027, 1), "2027-01-01")

    def test_falls_back_to_mobile_on_403(self):
        calls = []

        def fake_fetch(url, retries=3):
            calls.append(url)
            if url.startswith(scrape.BASE_URL):
                raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO())
            return MOBILE_HTML

        orig, scrape.fetch = scrape.fetch, fake_fetch
        scrape.desktop_blocked = False
        try:
            rows = scrape.get_list()
            scrape.get_list()  # 第二次不再请求电脑版
        finally:
            scrape.fetch = orig
            scrape.desktop_blocked = False
        self.assertEqual(rows[0]["nums"], [30, 3, 25, 28, 6, 17, 5])
        self.assertEqual([u.startswith(scrape.BASE_URL) for u in calls], [True, False, False])

    def test_site_labels_never_override_derivation(self):
        # 真实例子：2026 第047期（春节前一天，还是蛇年），手机版按马年标成了"兔猴猴牛鸡猴龙"
        scrape.warnings.clear()
        draw = {"date": "2026-02-16", "issue": 47, "nums": [40, 35, 23, 42, 46, 47, 39], "labels": "兔猴猴牛鸡猴龙"}
        out = scrape.with_zodiacs(draw, check_site=True)
        self.assertEqual(out["zodiacs"], "虎羊羊鼠猴羊兔")
        self.assertNotIn("labels", out)
        self.assertEqual(len(scrape.warnings), 1)
        scrape.warnings.clear()

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
