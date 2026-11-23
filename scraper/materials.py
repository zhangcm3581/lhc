#!/usr/bin/env python3
"""六肖十码：预测只保存一次，开奖后只补结果，已完成的期不重复请求。"""
import argparse
import base64
import calendar
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import time
from urllib.parse import urljoin

from scrape import BEIJING, ZODIACS, fetch, load, log, save

SOURCE = 'https://fmlolf.03ise-mmr4c-qqobks.work:17455/'
DEFAULT_OUT = Path(__file__).resolve().parent.parent / 'data' / 'materials.json'
LABELS = ['六肖', '五肖', '四肖', '三肖', '二肖', '一肖', '③码中特', '⑤码中特', '⑩码中特']


class MaterialParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'title_list74' in dict(attrs).get('class', '').split():
                self.depth = 1
        if not self.depth:
            return
        if tag == 'table':
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag == 'td' and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag == 'td' and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None
        elif tag == 'div':
            self.depth -= 1


def issue_date(issue, today):
    # 原站此栏目没有年份；只展示最近 14 期，按最近的公历日期归年，兼容跨年。
    candidates = [date(y, 1, 1) + timedelta(days=issue - 1)
                  for y in (today.year - 1, today.year, today.year + 1)
                  if 1 <= issue <= 365 + calendar.isleap(y)]
    if not candidates:
        raise ValueError(f'无效期号：{issue}')
    return min(candidates, key=lambda d: abs((d - today).days))


def parse_materials(html, today):
    parser = MaterialParser()
    parser.feed(html)
    records = {}
    for table in parser.tables:
        if len(table) != 9 or any(len(row) != 3 for row in table):
            raise ValueError('六肖十码表格必须包含九行、每行三列')
        match = re.fullmatch(r'(\d{1,3})期六肖', table[0][0])
        if not match:
            raise ValueError('无法识别六肖十码期号')
        issue = int(match[1])
        day = issue_date(issue, today)
        rows = []
        results = set()
        for i, (label, content, result_text) in enumerate(table):
            expected = f'{issue}期{LABELS[i]}' if i < 6 else LABELS[i]
            if label != expected:
                raise ValueError(f'第{issue}期栏目异常：{label}')
            zs = re.findall(f'[{ZODIACS}]', content)
            nums = [int(n) for n in re.findall(r'\d+', content)]
            count = 6 - i if i < 6 else (3, 5, 10)[i - 6]
            values = zs if i < 6 else nums
            if len(values) != count or len(set(values)) != count:
                raise ValueError(f'第{issue}期{label}数量或内容异常：{content}')
            if any(not 1 <= n <= 49 for n in nums) or (i == 5 and len(nums) != 1):
                raise ValueError(f'第{issue}期号码异常：{content}')
            result = re.fullmatch(rf'开[：:]\s*(?:00|([{ZODIACS}])(\d{{1,2}})(?:错|中|准)?)', result_text)
            if not result or (result[2] and not 1 <= int(result[2]) <= 49):
                raise ValueError(f'第{issue}期结果异常：{result_text}')
            opened = {'zodiac': result[1], 'number': int(result[2])} if result[2] else None
            results.add((result[1], result[2]))
            rows.append({'label': LABELS[i], 'content': content, 'zodiacs': zs,
                         'numbers': nums, 'result': opened, 'result_text': result_text})
        if len(results) != 1:
            raise ValueError(f'第{issue}期各行开奖结果不一致')
        record = {'year': day.year, 'issue': issue, 'date': day.isoformat(), 'rows': rows}
        key = (day.year, issue)
        if key in records and records[key] != record:
            raise ValueError(f'第{issue}期重复且内容不同')
        records[key] = record
    if not records:
        raise ValueError('没有解析到六肖十码资料，原站结构可能已改变')
    return sorted(records.values(), key=lambda r: (r['year'], r['issue']))


def decode_script(script):
    # 只解码 document.write 的 Base64 文本，不执行远端 JavaScript。
    return ''.join(base64.b64decode(s, validate=True).decode('utf-8')
                   for s in re.findall(r'strdecode\([\"\x27]([A-Za-z0-9+/=]+)[\"\x27]\)', script))


def get_materials(source, today):
    html = fetch(source, retries=1)
    if re.search(r'class=[\"\x27]title_list74(?:\s|[\"\x27])', html):
        return parse_materials(html, today)
    # 首页脚本地址会轮换，每次从首页发现，而非固定某个 CDN 文件。
    scripts = re.findall(r'<script\b[^>]*\bsrc=[\"\x27]([^\"\x27]+)[\"\x27]', html)
    errors = []
    for src in dict.fromkeys(scripts):
        if '/upload/script/' not in src:
            continue
        try:
            decoded = decode_script(fetch(urljoin(source, src), retries=1))
        except Exception as exc:
            errors.append(str(exc))
            continue
        if re.search(r'class=[\"\x27]title_list74(?:\s|[\"\x27])', decoded):
            return parse_materials(decoded, today)
    raise ValueError('首页脚本中未找到六肖十码资料' + (f'；请求错误：{errors[0]}' if errors else ''))


def merge(existing, incoming, captured_at, source):
    records = {(r['year'], r['issue']): r for r in existing}
    changed = 0
    for item in incoming:
        key = (item['year'], item['issue'])
        record = records.get(key)
        if record is None:
            records[key] = {**item, 'captured_at': captured_at, 'source': source,
                            'before_result': all(r['result'] is None for r in item['rows']),
                            'result_captured_at': captured_at if item['rows'][0]['result'] else None}
            changed += 1
        elif not all(r['result'] for r in record['rows']) and item['rows'][0]['result']:
            # 原站可能在开奖后改预测，只补结果，不替换首次保存的生肖和号码。
            for row in record['rows']:
                row['result'] = item['rows'][0]['result']
                row['result_text'] = item['rows'][0]['result_text']
            record['result_captured_at'] = captured_at
            changed += 1
    return sorted(records.values(), key=lambda r: (r['year'], r['issue'])), changed


def complete(records, today, results=False):
    record = next((r for r in records if r['date'] == today.isoformat()), None)
    return record is not None and (not results or all(row['result'] for row in record['rows']))


def run_once(out, source, results=False):
    now = datetime.now(BEIJING)
    existing = load(out)
    if complete(existing, now.date(), results):
        log(f'六肖十码：{now.date()} 的{"开奖结果" if results else "预测资料"}已保存，跳过请求')
        return True
    incoming = get_materials(source, now.date())
    records, changed = merge(existing, incoming, now.isoformat(timespec='seconds'), source)
    if changed:
        save(out, records)
    log(f'六肖十码：读取 {len(incoming)} 期，新增/补结果 {changed} 期，累计保存 {len(records)} 期')
    return complete(records, now.date(), results)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--source', default=os.environ.get('LHC_MATERIALS_URL', SOURCE))
    ap.add_argument('--wait', metavar='HH:MM', help='每分钟尝试补齐当天开奖结果，成功即停止，最晚到指定北京时间')
    args = ap.parse_args()
    if not args.wait:
        run_once(args.out, args.source)
        return
    hh, mm = map(int, args.wait.split(':'))
    deadline = datetime.now(BEIJING).replace(hour=hh, minute=mm, second=0, microsecond=0)
    while True:
        try:
            if run_once(args.out, args.source, results=True):
                return
        except Exception as exc:
            log(f'六肖十码采集失败：{exc}')
        if datetime.now(BEIJING) + timedelta(seconds=60) > deadline:
            break
        time.sleep(60)
    log(f'六肖十码：到 {args.wait} 仍未补齐当天开奖结果，保留已有资料')
    raise SystemExit(1)


if __name__ == '__main__':
    main()
