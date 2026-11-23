import base64
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import materials

HTML = (Path(__file__).parent / 'fixtures/materials.html').read_text('utf-8')
TODAY = date(2026, 11, 23)


class MaterialsTest(unittest.TestCase):
    def test_real_history_and_nested_highlights(self):
        rows = materials.parse_materials(HTML, TODAY)
        self.assertEqual([r['issue'] for r in rows], [314, 326, 327])
        self.assertEqual(rows[0]['date'], '2026-11-10')
        self.assertEqual(rows[1]['rows'][0]['zodiacs'], list('狗猴牛羊鸡鼠'))
        self.assertEqual(rows[1]['rows'][6]['numbers'], [21, 23, 30])
        self.assertEqual(rows[1]['rows'][6]['result'], {'zodiac': '猴', 'number': 23})
        self.assertIsNone(rows[-1]['rows'][0]['result'])
        self.assertEqual(rows[-1]['rows'][5]['numbers'], [25])

    def test_year_boundary(self):
        self.assertEqual(materials.issue_date(365, date(2027, 1, 1)), date(2026, 12, 31))
        self.assertEqual(materials.issue_date(1, date(2026, 12, 31)), date(2027, 1, 1))
        self.assertEqual(materials.issue_date(366, date(2025, 1, 1)), date(2024, 12, 31))

    def test_rejects_incomplete_or_bad_data(self):
        for html in ('<html>error</html>', HTML.replace('327期五肖', '328期五肖'),
                     HTML.replace('25 12 27', '99 12 27'), HTML.replace('马 羊 龙 蛇 鸡 猴', '马 马 龙 蛇 鸡 猴')):
            with self.subTest(html=html[:30]), self.assertRaises(ValueError):
                materials.parse_materials(html, TODAY)

    def test_split_base64_script_and_rotating_source(self):
        chunks = [HTML[:100], HTML[100:]]
        script = '\n'.join('document.writeln(utf8to16(strdecode("' + base64.b64encode(s.encode()).decode() + '")));' for s in chunks)
        with patch.object(materials, 'fetch', side_effect=[
            '<script src="/upload/script/11/new.js"></script>', script,
        ]) as fetch:
            self.assertEqual(len(materials.get_materials('https://example.test/', TODAY)), 3)
            self.assertEqual(fetch.call_args.args[0], 'https://example.test/upload/script/11/new.js')

    def test_prediction_kept_when_source_changes_after_draw(self):
        incoming = materials.parse_materials(HTML, TODAY)
        saved, changed = materials.merge([], deepcopy(incoming), 'first', 'source')
        self.assertEqual(changed, 3)
        saved, changed = materials.merge(saved, incoming, 'again', 'source')
        self.assertEqual(changed, 0)
        update = deepcopy(incoming[-1])
        for row in update['rows']:
            row['result'] = {'zodiac': '马', 'number': 25}
            row['result_text'] = '开：马25'
            row['content'] = 'changed after draw'
            row['zodiacs'] = ['狗']
        saved, changed = materials.merge(saved, [update], 'later', 'source')
        self.assertEqual(len(saved), 3)
        self.assertEqual(changed, 1)
        self.assertEqual(saved[-1]['rows'][0]['zodiacs'], list('马羊龙蛇鸡猴'))
        self.assertEqual(saved[-1]['rows'][0]['result']['number'], 25)
        self.assertEqual(saved[-1]['captured_at'], 'first')
        self.assertEqual(saved[-1]['result_captured_at'], 'later')
        self.assertTrue(saved[-1]['before_result'])
        self.assertNotIn('versions', saved[-1])
        # 已开奖不回退为未开奖，也不重复修改。
        saved, changed = materials.merge(saved, incoming, 'stale', 'source')
        self.assertEqual(changed, 0)
        self.assertEqual(saved[-1]['rows'][0]['result']['number'], 25)

    def test_daytime_skips_network_but_evening_fills_result(self):
        incoming = materials.parse_materials(HTML, TODAY)
        with tempfile.TemporaryDirectory() as tmp, patch.object(materials, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 11, 23, 10, tzinfo=materials.BEIJING)
            out = Path(tmp) / 'materials.json'
            with patch.object(materials, 'get_materials', return_value=deepcopy(incoming)) as fetch:
                self.assertTrue(materials.run_once(out, 'source'))
                self.assertTrue(materials.run_once(out, 'source'))  # 12 点
                self.assertTrue(materials.run_once(out, 'source'))  # 13 点
                self.assertEqual(fetch.call_count, 1)
                clock.now.return_value = datetime(2026, 11, 23, 21, 34, tzinfo=materials.BEIJING)
                self.assertFalse(materials.run_once(out, 'source', results=True))
                self.assertEqual(fetch.call_count, 2)  # 已有预测，仍需补结果
                opened = deepcopy(incoming)
                for row in opened[-1]['rows']:
                    row['result'] = {'zodiac': '马', 'number': 25}
                    row['result_text'] = '开：马25'
                fetch.return_value = opened
                self.assertTrue(materials.run_once(out, 'source', results=True))
                self.assertTrue(materials.run_once(out, 'source', results=True))
                self.assertEqual(fetch.call_count, 3)  # 结果齐了不再请求

    def test_older_issue_does_not_skip_today_and_next_day_is_independent(self):
        records, _ = materials.merge([], materials.parse_materials(HTML, TODAY), 'first', 'source')
        self.assertFalse(materials.complete(records[:-1], TODAY))
        self.assertTrue(materials.complete(records, TODAY))
        self.assertFalse(materials.complete(records, date(2026, 11, 24)))

    def test_results_keep_tracking_previous_day_after_midnight(self):
        records, _ = materials.merge([], materials.parse_materials(HTML, TODAY), 'first', 'source')
        before = datetime(2026, 11, 23, 21, 33, tzinfo=materials.BEIJING)
        after = datetime(2026, 11, 23, 21, 34, tzinfo=materials.BEIJING)
        midnight = datetime(2026, 11, 24, 0, 4, tzinfo=materials.BEIJING)
        self.assertTrue(materials.results_complete(records, before))
        self.assertFalse(materials.results_complete(records, after))
        self.assertFalse(materials.results_complete(records, midnight))
        for row in records[-1]['rows']:
            row['result'] = {'zodiac': '马', 'number': 25}
        self.assertTrue(materials.results_complete(records, midnight))
        # 昨日已齐，但更早的存档还有未同步结果，不能停止。
        records[0]['rows'][0]['result'] = None
        self.assertFalse(materials.results_complete(records, midnight))

    def test_result_sync_skips_network_after_midnight_when_done(self):
        records, _ = materials.merge([], materials.parse_materials(HTML, TODAY), 'first', 'source')
        with tempfile.TemporaryDirectory() as tmp, patch.object(materials, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 11, 24, 0, 4, tzinfo=materials.BEIJING)
            out = Path(tmp) / 'materials.json'
            materials.save(out, records)
            opened = deepcopy(materials.parse_materials(HTML, TODAY))
            for row in opened[-1]['rows']:
                row['result'] = {'zodiac': '马', 'number': 25}
                row['result_text'] = '开：马25'
            with patch.object(materials, 'get_materials', return_value=opened) as fetch:
                self.assertTrue(materials.run_once(out, 'source', results=True))
                self.assertTrue(materials.run_once(out, 'source', results=True))
                self.assertEqual(fetch.call_count, 1)
            self.assertEqual(materials.load(out)[-1]['rows'][0]['zodiacs'], list('马羊龙蛇鸡猴'))

    def test_poll_stops_on_success_without_sleep(self):
        with patch.object(sys, 'argv', ['materials.py', '--wait', '22:40']), \
             patch.object(materials, 'run_once', return_value=True) as run, \
             patch.object(materials.time, 'sleep') as sleep:
            materials.main()
            self.assertEqual(run.call_count, 1)
            self.assertTrue(run.call_args.kwargs['results'])
            sleep.assert_not_called()

    def test_failed_fetch_does_not_replace_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'materials.json'
            out.write_text('[]')
            with patch.object(materials, 'get_materials', side_effect=ValueError('bad data')):
                with self.assertRaises(ValueError):
                    materials.run_once(out, 'source')
            self.assertEqual(out.read_text(), '[]')


if __name__ == '__main__':
    unittest.main()
