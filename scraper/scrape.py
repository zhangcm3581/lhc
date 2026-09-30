#!/usr/bin/env python3
"""从 55128.cn 抓取新澳门六合彩开奖记录，合并写入 draws.json。只用标准库，服务器上无需安装依赖。

用法:
  python3 scrape.py                  # 抓最近 30 期，补上缺的（断了超过 30 期会自动按年补）
  python3 scrape.py --wait 22:40     # 定时任务用：每分钟查一次，抓到今天这一期或到 22:40 为止
  python3 scrape.py --all            # 按年抓 2020 年至今全部数据（已有的期不会被覆盖）
  python3 scrape.py --push-test      # 用现有数据发一条测试推送，检查微信能否收到

数据来源：先用电脑版 www.55128.cn；电脑版拒绝访问时（部分云服务器 IP 会被它的 CDN 屏蔽，返回 403）
自动改用手机版 m.55128.cn。手机版没有开奖日期，按期号推算（期号就是当年第几天，2022 年以来全部符合）。

环境变量：
  LHC_BASE_URL   电脑版地址（默认 https://www.55128.cn）
  LHC_MOBILE_URL 手机版地址（默认 https://m.55128.cn）
  LHC_PUSH_KEY   Server酱 SendKey，配置后 --wait 模式抓到新一期或抓取失败时推送到微信
  LHC_ALERT_TM   特码连续未出达到多少期时在推送里提醒（默认 30）
  LHC_ALERT_PM   平码连续未出达到多少期时在推送里提醒（默认 6）

生肖：按"本命生肖"推算（01、13、25、37、49 是本命，春节当天切换），已与全部历史数据逐期核对一致。
网站标注的生肖只用来核对新抓到的期，不一致时保留推算结果并在推送里提醒——网站标注会出错：
电脑版详情页 2023 第022期 7 个号全标成"鼠"；手机版对往年号码一律按今年的对应关系标注，往年全部标错。
"""
import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import date as Date, datetime, timedelta, timezone
from pathlib import Path

BASE_URL = os.environ.get("LHC_BASE_URL", "https://www.55128.cn")
MOBILE_URL = os.environ.get("LHC_MOBILE_URL", "https://m.55128.cn")
LIST_PATH = "/kjh/history_newam6hc.aspx"  # 不带参数是最近几十期，?year=2025 是整年（电脑版、手机版相同）
DETAIL_PATH = "/kjh/newam6hc-kjjg-{qi}.htm"  # 单期详情，标有生肖
FIRST_YEAR = 2020
ZODIACS = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
BEIJING = timezone(timedelta(hours=8))
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "draws.json"
POLL_SECONDS = 60  # 21:34 开奖后每分钟查一次
PUSH_KEY = os.environ.get("LHC_PUSH_KEY", "")
ALERT_TM = int(os.environ.get("LHC_ALERT_TM", "30"))
ALERT_PM = int(os.environ.get("LHC_ALERT_PM", "6"))

# 春节 = 本命生肖切换日。2021–2026 已用开奖数据核对过；之后每期还会和网站标注交叉核对。
SPRING_FESTIVAL = {
    2020: "2020-01-25", 2021: "2021-02-12", 2022: "2022-02-01", 2023: "2023-01-22",
    2024: "2024-02-10", 2025: "2025-01-29", 2026: "2026-02-17", 2027: "2027-02-06",
    2028: "2028-01-26", 2029: "2029-02-13", 2030: "2030-02-03", 2031: "2031-01-23",
    2032: "2032-02-11", 2033: "2033-01-31", 2034: "2034-02-19", 2035: "2035-02-08",
}

ROW_RE = re.compile(
    r'<tr>\s*<td class="td-number">(\d{4}-\d{2}-\d{2})</td>\s*'
    r'<td class="td-number">(\d{7})</td>\s*<td class="td-number">(.*?)</td>', re.S
)
LIST_BALL_RE = re.compile(r'<span class="ball-list[^"]*">(\d+)</span>')
DETAIL_RE = re.compile(
    r'<div class="kaij-cartoon">\s*<div class="kaij-cartoon">\s*<div class="kaij-cartoon">(.*?)</div>\s*'
    r'<div class="kaij-cartoon-new">(.*?)</div>', re.S
)
DETAIL_BALL_RE = re.compile(r'<span class="ball-list[^"]*"[^>]*>(\d+)</span>')
DETAIL_ZODIAC_RE = re.compile(r'<span class="ball-list-new">(\S)</span>')
MOBILE_ITEM_RE = re.compile(r'<strong>(\d{7})</strong>\s*期(.*?)(?=<div class="item">|</section>)', re.S)
MOBILE_BALL_RE = re.compile(r'<span class="kj-\w+">\s*(\d+)\s*</span>')
MOBILE_ZODIAC_RE = re.compile(r'<p>(\S)/\S</p>')

warnings = []  # 需要人工留意的情况，会附在推送里
desktop_blocked = False  # 电脑版返回过 403 后，本次运行不再请求它


def log(msg):
    print(f"[{datetime.now(BEIJING):%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def warn(msg):
    log(msg)
    warnings.append(msg)


def fetch(url, retries=3):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Encoding": "gzip",
    })
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
                return body.decode("utf-8")
        except Exception as e:
            # 4xx 是网站拒绝或页面不存在，重试也没用
            if attempt == retries or (isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500):
                raise
            log(f"请求失败（第 {attempt} 次）：{e}，10 秒后重试")
            time.sleep(10)


def key(draw):
    """一期开奖的唯一标识是 年份+期号。不能用日期：有同一天补开两期的情况。"""
    return int(draw["date"][:4]), draw["issue"]


def qi(draw):
    return f"{draw['date'][:4]}{draw['issue']:03d}"


def benming_of(num, zodiac):
    """由任一号码及其生肖反推本命生肖。"""
    return ZODIACS[(ZODIACS.index(zodiac) + num - 1) % 12]


def benming_by_date(date):
    y = int(date[:4])
    if y not in SPRING_FESTIVAL:
        raise ValueError(f"缺少 {y} 年的春节日期，请在 scrape.py 的 SPRING_FESTIVAL 里补上")
    lunar_year = y if date >= SPRING_FESTIVAL[y] else y - 1
    return ZODIACS[(lunar_year - 2020) % 12]  # 2020 年是鼠年


def zodiac_of(num, benming):
    return ZODIACS[(ZODIACS.index(benming) - (num - 1)) % 12]


def date_of_issue(year, issue):
    """期号就是当年第几天（2022 年以来全部符合）。手机版没有开奖日期，用它推算。"""
    return (Date(year, 1, 1) + timedelta(days=issue - 1)).isoformat()


def check_nums(q, nums):
    # 逐期校验，页面结构一变就立刻报错，而不是悄悄写入坏数据
    if len(nums) != 7 or len(set(nums)) != 7 or not all(1 <= n <= 49 for n in nums):
        raise ValueError(f"第{q}期号码异常：{nums}")


def parse_list(html):
    draws = {}
    for date, q, box in ROW_RE.findall(html):
        nums = [int(n) for n in LIST_BALL_RE.findall(box)]
        if q[:4] != date[:4]:
            raise ValueError(f"第{q}期的日期 {date} 年份不符")
        check_nums(q, nums)
        draw = {"date": date, "issue": int(q[4:]), "nums": nums}
        seen = draws.get(key(draw))
        if seen and seen["nums"] != nums:
            raise ValueError(f"第{q}期出现两条号码不同的记录：{seen['nums']} / {nums}")
        draws.setdefault(key(draw), draw)
    if not draws:
        raise ValueError("列表页没有解析到任何开奖记录，页面结构可能变了")
    return list(draws.values())


def parse_mobile(html):
    """手机版列表：有期号、号码和标注的生肖，没有日期。"""
    draws = {}
    for q, box in MOBILE_ITEM_RE.findall(html):
        nums = [int(n) for n in MOBILE_BALL_RE.findall(box)]
        check_nums(q, nums)
        draw = {"date": date_of_issue(int(q[:4]), int(q[4:])), "issue": int(q[4:]), "nums": nums}
        labels = "".join(MOBILE_ZODIAC_RE.findall(box))
        if len(labels) == 7:
            draw["labels"] = labels  # 网站标注的生肖，只用来核对，不写入数据
        draws.setdefault(key(draw), draw)
    if not draws:
        raise ValueError("手机版列表页没有解析到任何开奖记录，页面结构可能变了")
    return list(draws.values())


def get_list(year=None):
    """开奖列表：先用电脑版；电脑版拒绝访问（服务器 IP 被网站的 CDN 屏蔽）时改用手机版。"""
    global desktop_blocked
    query = f"?year={year}" if year else ""
    if not desktop_blocked:
        try:
            return parse_list(fetch(BASE_URL + LIST_PATH + query))
        except urllib.error.HTTPError as e:
            if e.code != 403:
                raise
            desktop_blocked = True
            log("电脑版拒绝访问（403），改用手机版")
    return parse_mobile(fetch(MOBILE_URL + LIST_PATH + query))


def scrape_year(year):
    rows = get_list(year)
    log(f"{year} 年：{len(rows)} 期")
    return rows


def labels_benming(draw, zs, source):
    """网站标注的生肖所对应的本命；生肖前后矛盾时返回 None。"""
    found = {benming_of(n, z) for n, z in zip(draw["nums"], zs)}
    if len(zs) != 7 or len(found) != 1:
        log(f"第{qi(draw)}期{source}标注的生肖前后矛盾（{''.join(zs)}），以推算为准")
        return None
    return found.pop()


def site_benming(draw):
    """新抓到的期，从网站标注的生肖反推本命，用来核对。拿不到时返回 None。"""
    if "labels" in draw:
        return labels_benming(draw, draw["labels"], "手机版")
    if desktop_blocked:
        return None
    try:
        m = DETAIL_RE.search(fetch(BASE_URL + DETAIL_PATH.format(qi=qi(draw)), retries=1))
    except Exception as e:
        log(f"第{qi(draw)}期详情页打不开：{e}")
        return None
    if not m:
        log(f"第{qi(draw)}期详情页没有解析到号码，页面结构可能变了")
        return None
    nums = [int(n) for n in DETAIL_BALL_RE.findall(m.group(1))]
    if nums != draw["nums"]:
        log(f"第{qi(draw)}期详情页的号码 {nums} 与列表页不符")
        return None
    return labels_benming(draw, DETAIL_ZODIAC_RE.findall(m.group(2)), "详情页")


def with_zodiacs(draw, check_site):
    bm = benming_by_date(draw["date"])
    if check_site:
        bm_site = site_benming(draw)
        if bm_site and bm_site != bm:
            warn(f"第{qi(draw)}期网站标注的本命是「{bm_site}」，按春节推算是「{bm}」，已按推算记录，请人工核对")
    clean = {k: v for k, v in draw.items() if k != "labels"}  # 网站标注只用来核对，不写入数据
    return {**clean, "zodiacs": "".join(zodiac_of(n, bm) for n in draw["nums"])}


def load(path):
    return json.loads(path.read_text("utf-8")) if path.exists() else []


def save(path, draws):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(draws, ensure_ascii=False, separators=(",", ":")), "utf-8")
    os.replace(tmp, path)  # 原子替换，网页不会读到写了一半的文件


def fetch_rows(existing, full):
    this_year = datetime.now(BEIJING).year
    if full or not existing:
        return [r for y in range(FIRST_YEAR, this_year + 1) for r in scrape_year(y)]
    rows = get_list()
    latest = key(existing[-1])
    if min(key(r) for r in rows) > latest:
        log("最近几十期接不上已有数据，按年补抓")
        rows += [r for y in range(latest[0], this_year + 1) for r in scrape_year(y)]
    return rows


def run_once(out, full=False):
    draws = load(out)
    by_key = {key(d): d for d in draws}
    rows = {key(r): r for r in fetch_rows(draws, full)}  # 最近 30 期和整年数据会有重叠
    fresh = []
    for r in sorted(rows.values(), key=key):
        have = by_key.get(key(r))
        if have is None:
            fresh.append(r)
        elif have["nums"] != r["nums"]:
            log(f"第{qi(r)}期：已有号码 {have['nums']}，网站现在是 {r['nums']}，保留已有数据")
    # 只有零星几期新数据时才和网站标注核对（电脑版要逐期打开详情页，避免大量请求）
    added = [with_zodiacs(r, check_site=len(fresh) <= 5) for r in fresh]
    if added:
        draws = sorted(draws + added, key=key)
        save(out, draws)
        log(f"新增 {len(added)} 期，最新：{draws[-1]['date']} 第{draws[-1]['issue']}期，共 {len(draws)} 期")
    else:
        log(f"没有新数据，最新仍是 {draws[-1]['date']} 第{draws[-1]['issue']}期")
    return draws, added


def misses(draws, special_only):
    """每个生肖当前已连续几期未出。特码只看第 7 个号，平码 7 个号都算。"""
    out = {}
    for z in ZODIACS:
        n = 0
        for d in reversed(draws):
            if z in (d["zodiacs"][6] if special_only else d["zodiacs"]):
                break
            n += 1
        out[z] = n
    return out


def summary(draws):
    """最新一期的推送内容：(标题, Markdown 正文)。"""
    d = draws[-1]
    bm = benming_of(d["nums"][0], d["zodiacs"][0])
    tm, pm = misses(draws, True), misses(draws, False)
    by_tm = sorted(ZODIACS, key=lambda z: -tm[z])
    alert_tm = [z for z in by_tm if tm[z] >= ALERT_TM]
    alert_pm = [z for z in sorted(ZODIACS, key=lambda z: -pm[z]) if pm[z] >= ALERT_PM]

    lines = [
        f"**{d['date']} 第{d['issue']}期**", "",
        "号码：" + " ".join(f"{n:02d}" for n in d["nums"][:6]) + f" + {d['nums'][6]:02d}", "",
        "生肖：" + " ".join(d["zodiacs"][:6]) + f" + {d['zodiacs'][6]}", "",
        "**特码最久未出**", "",
    ]
    for z in by_tm[:5]:
        lines.append(f"- {z}：已连续 {tm[z]} 期未出" + ("（本命）" if z == bm else "")
                     + (f" ⚠️ 达到提醒线（{ALERT_TM} 期）" if z in alert_tm else ""))
    lines += ["", f"**本命「{bm}」**：特码已连续 {tm[bm]} 期未出，平码已连续 {pm[bm]} 期未出"]
    if alert_pm:
        lines += ["", f"**平码连续未出 ≥ {ALERT_PM} 期**：" + "、".join(f"{z} {pm[z]} 期" for z in alert_pm)]
    if warnings:
        lines += ["", "**需要留意**", ""] + [f"- {w}" for w in warnings]

    alerts = [f"{z}特码{tm[z]}期" for z in alert_tm] + [f"{z}平码{pm[z]}期" for z in alert_pm]
    title = f"第{d['issue']}期 特码{d['zodiacs'][6]}" + (f" · {'、'.join(alerts)}未出" if alerts else "")
    return title, "\n".join(lines)


def push(title, desp):
    """通过 Server酱 推送到微信。推送失败只记日志，不影响抓取。"""
    if not PUSH_KEY:
        log("未配置 LHC_PUSH_KEY，不推送")
        return False
    data = urllib.parse.urlencode({"title": title[:32], "desp": desp}).encode()
    try:
        with urllib.request.urlopen(f"https://sctapi.ftqq.com/{PUSH_KEY}.send", data=data, timeout=15) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        log(f"推送失败：{e}")
        return False
    if result.get("code") != 0:
        log(f"推送失败：{result}")
        return False
    log(f"已推送到微信：{title}")
    return True


def main():
    ap = argparse.ArgumentParser(description="抓取开奖记录")
    ap.add_argument("--all", action="store_true", help=f"按年抓取 {FIRST_YEAR} 年至今全部数据")
    ap.add_argument("--wait", metavar="HH:MM", help="轮询直到抓到今天这一期，或到北京时间 HH:MM 为止")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="输出文件（默认 data/draws.json）")
    ap.add_argument("--push-test", action="store_true", help="用现有数据发一条测试推送")
    args = ap.parse_args()

    if args.push_test:
        title, desp = summary(load(args.out))
        print(f"标题：{title}\n\n{desp}\n")
        sys.exit(0 if push("[测试] " + title, desp) else 1)

    if not args.wait:
        run_once(args.out, full=args.all)
        return

    now = datetime.now(BEIJING)
    hh, mm = map(int, args.wait.split(":"))
    deadline = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    today = now.strftime("%Y-%m-%d")
    last_error = None
    while True:
        try:
            draws, added = run_once(args.out)
            if draws and draws[-1]["date"] >= today:
                if added:
                    push(*summary(draws))
                return
        except Exception as e:
            last_error = e
            log(f"抓取出错：{e}")
        if datetime.now(BEIJING) + timedelta(seconds=POLL_SECONDS) > deadline:
            log(f"到 {args.wait} 仍未抓到 {today} 的开奖，放弃")
            push(f"{today} 开奖数据抓取失败", "\n\n".join([
                f"到北京时间 {args.wait} 仍未抓到 {today} 的开奖。",
                f"最后一次错误：{last_error}" if last_error else "目标站一直没有更新这一期。",
                f"如果连续几天都失败，可能是目标站换了域名（当前：{BASE_URL}），请更新 LHC_BASE_URL。",
            ]))
            sys.exit(1)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
