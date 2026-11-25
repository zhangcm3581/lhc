#!/usr/bin/env python3
"""共享输赢账本：仅监听本机，由 nginx 代理；SQLite 数据保存在静态目录外。"""
import argparse
from collections import defaultdict, deque
from contextlib import closing, contextmanager
from datetime import date
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

SESSION_SECONDS = 12 * 60 * 60
PIN_ROUNDS = 200_000


def pin_hash(pin, salt):
    return hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(salt), PIN_ROUNDS).hex()


def init_storage(directory, pin=None):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    credentials = directory / 'pin.json'
    if not credentials.exists():
        if pin is None or not re.fullmatch(r'\d{6}', pin, flags=re.ASCII):
            raise ValueError('首次启动请配置 6 位数字验证码')
        salt = secrets.token_hex(16)
        with credentials.open('x') as stream:
            json.dump({'salt': salt, 'hash': pin_hash(pin, salt)}, stream)
        os.chmod(credentials, 0o600)
    with closing(sqlite3.connect(directory / 'ledger.sqlite3')) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY, date TEXT NOT NULL, year INTEGER NOT NULL,
            issue INTEGER NOT NULL, amount_cents INTEGER NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            UNIQUE(year, issue))''')
    os.chmod(directory / 'ledger.sqlite3', 0o600)


def validate_record(body):
    raw_date = body.get('date')
    if not isinstance(raw_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
        raise ValueError('请选择有效日期')
    try:
        day = date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError('请选择有效日期') from None
    if not 2020 <= day.year <= 2100:
        raise ValueError('日期年份须在 2020～2100 年之间')
    issue = body.get('issue')
    limit = date(day.year, 12, 31).timetuple().tm_yday
    if type(issue) is not int or not 1 <= issue <= limit:
        raise ValueError(f'期数须为 1～{limit} 的整数')
    amount = body.get('amount_cents')
    if type(amount) is not int or not 0 < abs(amount) <= 100_000_000:
        raise ValueError('金额须大于 0 且不超过 1,000,000 元，最多两位小数')
    return day.isoformat(), day.year, issue, amount


class LedgerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, directory):
        self.directory = directory
        self.credentials = json.loads((directory / 'pin.json').read_text())
        self.sessions = {}
        self.attempts = defaultdict(deque)
        self.lock = threading.Lock()
        super().__init__(address, Handler)

    @contextmanager
    def database(self):
        db = sqlite3.connect(self.directory / 'ledger.sqlite3', timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # 不记录请求体、验证码或会话 cookie。
        super().log_message(fmt, *args)

    def respond(self, status, body, cookie=None):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def cookie(self, token='', age=0):
        secure = '; Secure' if self.headers.get('X-Forwarded-Proto') == 'https' else ''
        return f'lhc_ledger={token}; Path=/api/ledger; HttpOnly; SameSite=Strict; Max-Age={age}{secure}'

    def token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            return cookie['lhc_ledger'].value if 'lhc_ledger' in cookie else ''
        except Exception:
            return ''

    def authenticated(self):
        with self.server.lock:
            now = time.time()
            self.server.sessions = {t: expiry for t, expiry in self.server.sessions.items() if expiry > now}
            return self.token() in self.server.sessions

    def body(self):
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('请求须为 JSON')
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 4096:
            raise ValueError('请求大小不正确')
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError('请求须为 JSON 对象')
        return value

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def do_PUT(self):
        self.dispatch()

    def dispatch(self):
        try:
            self.handle_request()
        except (ValueError, UnicodeError) as exc:
            self.respond(400, {'error': str(exc)})
        except sqlite3.Error:
            self.respond(503, {'error': '账本暂时不可用，请稍后重试'})

    def handle_request(self):
        path = urlsplit(self.path).path
        if self.command != 'GET':
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                self.respond(403, {'error': '不允许跨站请求'})
                return
            body = self.body()
        if path == '/api/ledger/login' and self.command == 'POST':
            self.login(body)
            return
        if not self.authenticated():
            self.respond(401, {'error': '请输入验证码进入账本'})
            return
        if path == '/api/ledger/logout' and self.command == 'POST':
            with self.server.lock:
                self.server.sessions.pop(self.token(), None)
            self.respond(200, {'ok': True}, self.cookie())
        elif path == '/api/ledger/records' and self.command == 'GET':
            with self.server.database() as db:
                rows = db.execute('SELECT * FROM records ORDER BY date DESC, issue DESC').fetchall()
            self.respond(200, {'records': [dict(row) for row in rows]})
        elif path == '/api/ledger/records' and self.command == 'POST':
            self.write_record(body)
        elif re.fullmatch(r'/api/ledger/records/\d+', path) and self.command == 'PUT':
            self.write_record(body, int(path.rsplit('/', 1)[1]))
        else:
            self.respond(404, {'error': '接口不存在'})

    def login(self, body):
        # nginx 覆盖 X-Real-IP，直连服务仅开放在回环地址。
        ip = self.headers.get('X-Real-IP', self.client_address[0])
        now = time.time()
        with self.server.lock:
            for key in list(self.server.attempts):
                queue = self.server.attempts[key]
                while queue and queue[0] <= now - 300:
                    queue.popleft()
                if not queue:
                    del self.server.attempts[key]
            attempts = self.server.attempts[ip]
            if len(attempts) >= 5:
                self.respond(429, {'error': '尝试次数过多，请 5 分钟后再试'})
                return
            attempts.append(now)
        pin = body.get('pin', '')
        credential = self.server.credentials
        if not isinstance(pin, str) or not re.fullmatch(r'[0-9]{6}', pin) or not hmac.compare_digest(pin_hash(pin, credential['salt']), credential['hash']):
            self.respond(401, {'error': '验证码不正确'})
            return
        token = secrets.token_urlsafe(32)
        with self.server.lock:
            self.server.attempts.pop(ip, None)
            self.server.sessions.pop(self.token(), None)
            self.server.sessions[token] = now + SESSION_SECONDS
        self.respond(200, {'ok': True}, self.cookie(token, SESSION_SECONDS))

    def write_record(self, body, record_id=None):
        values = validate_record(body)
        try:
            with self.server.database() as db:
                if record_id is None:
                    cursor = db.execute('INSERT INTO records(date, year, issue, amount_cents) VALUES (?, ?, ?, ?)', values)
                    record_id = cursor.lastrowid
                else:
                    revision = body.get('revision')
                    if type(revision) is not int or revision < 1:
                        raise ValueError('记录版本不正确，请刷新后重试')
                    cursor = db.execute('UPDATE records SET date=?, year=?, issue=?, amount_cents=?, revision=revision+1 WHERE id=? AND revision=?', (*values, record_id, revision))
                    if cursor.rowcount == 0:
                        self.respond(409, {'error': '记录已被其他设备修改，请刷新账本后重新编辑'})
                        return
                record = dict(db.execute('SELECT * FROM records WHERE id=?', (record_id,)).fetchone())
        except sqlite3.IntegrityError:
            self.respond(409, {'error': f'{values[1]} 年第 {values[2]} 期已有记录，请编辑已有记录。'})
            return
        self.respond(200, {'record': record})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', type=Path, default=Path('/opt/lhc-private'))
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--init-pin', action='store_true', help='从标准输入读取首次验证码，已有配置不覆盖')
    args = parser.parse_args()
    os.umask(0o077)
    if args.init_pin:
        import sys
        init_storage(args.storage, sys.stdin.read().strip())
        return
    init_storage(args.storage)
    LedgerServer(('127.0.0.1', args.port), args.storage).serve_forever()


if __name__ == '__main__':
    main()
