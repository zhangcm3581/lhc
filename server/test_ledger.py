import concurrent.futures
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from ledger import LedgerServer, init_storage


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        init_storage(self.directory, '123456')
        self.server = LedgerServer(('127.0.0.1', 0), self.directory)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def request(self, method, path='records', body=None, cookie=None, origin=None):
        conn = http.client.HTTPConnection(*self.server.server_address)
        headers = {'Cookie': self.cookie if cookie is None else cookie}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = origin
        conn.request(method, '/api/ledger/' + path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        result = response.status, data, response.getheader('Set-Cookie')
        conn.close()
        return result

    def login(self):
        status, _, cookie = self.request('POST', 'login', {'pin': '123456'})
        self.assertEqual(status, 200)
        self.cookie = cookie.split(';')[0]
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)

    def record(self, **changes):
        return {'date': '2026-11-25', 'issue': 329, 'amount_cents': 15000, **changes}

    def test_auth_and_logout_protect_records(self):
        self.assertEqual(self.request('GET')[0], 401)
        self.assertEqual(self.request('POST', body=self.record())[0], 401)
        self.assertEqual(self.request('POST', 'login', {'pin': '000000'})[0], 401)
        self.login()
        self.assertEqual(self.request('GET')[0], 200)
        self.assertEqual(self.request('POST', 'logout', {})[0], 200)
        self.assertEqual(self.request('GET')[0], 401)
        self.assertNotIn('123456', (self.directory / 'pin.json').read_text())

    def test_duplicate_and_year_boundary_and_persistence(self):
        self.login()
        self.assertEqual(self.request('POST', body=self.record())[0], 200)
        status, data, _ = self.request('POST', body=self.record(date='2026-11-26'))
        self.assertEqual(status, 409)
        self.assertIn('2026 年第 329 期已有记录', data['error'])
        self.assertEqual(self.request('POST', body=self.record(date='2027-11-25'))[0], 200)
        other = LedgerServer(('127.0.0.1', 0), self.directory)
        with other.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM records').fetchone()[0], 2)
        other.server_close()

    def test_two_devices_cannot_insert_same_issue(self):
        self.login()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: self.request('POST', body=self.record())[0], range(2)))
        self.assertEqual(sorted(statuses), [200, 409])

    def test_edit_conflict_and_duplicate(self):
        self.login()
        _, data, _ = self.request('POST', body=self.record())
        record = data['record']
        self.assertEqual(self.request('POST', body=self.record(issue=328))[0], 200)
        payload = self.record(amount_cents=-10000, revision=record['revision'])
        self.assertEqual(self.request('PUT', f"records/{record['id']}", payload)[0], 200)
        self.assertEqual(self.request('PUT', f"records/{record['id']}", payload)[0], 409)
        payload.update(issue=328, revision=2)
        self.assertEqual(self.request('PUT', f"records/{record['id']}", payload)[0], 409)

    def test_validation_and_csrf(self):
        self.login()
        for changes in ({'amount_cents': 0}, {'amount_cents': 1.2}, {'amount_cents': True}, {'issue': 366}, {'date': '2026-02-30'}, {'date': '2026-2-03'}, {'amount_cents': 100000001}):
            with self.subTest(changes=changes):
                self.assertEqual(self.request('POST', body=self.record(**changes))[0], 400)
        self.assertEqual(self.request('POST', body=self.record(), origin='https://other.example')[0], 403)
        self.assertEqual(self.request('POST', body=self.record(date='2024-12-31', issue=366))[0], 200)

    def test_separate_sessions_share_data_and_expire(self):
        self.login()
        first_cookie = self.cookie
        self.assertEqual(self.request('POST', body=self.record())[0], 200)
        self.cookie = ''
        self.login()
        status, data, _ = self.request('GET')
        self.assertEqual(status, 200)
        self.assertEqual(data['records'][0]['amount_cents'], 15000)
        self.assertNotEqual(first_cookie, self.cookie)
        token = self.cookie.split('=', 1)[1]
        self.server.sessions[token] = 0
        self.assertEqual(self.request('GET')[0], 401)
        self.assertEqual(self.request('GET', cookie=first_cookie)[0], 200)

    def test_setup_keeps_existing_pin_and_records(self):
        self.login()
        self.request('POST', body=self.record())
        original = (self.directory / 'pin.json').read_text()
        init_storage(self.directory, '654321')
        self.assertEqual((self.directory / 'pin.json').read_text(), original)
        self.assertEqual(len(self.request('GET')[1]['records']), 1)

    def test_pin_attempts_limited(self):
        for _ in range(5):
            self.assertEqual(self.request('POST', 'login', {'pin': '000000'})[0], 401)
        self.assertEqual(self.request('POST', 'login', {'pin': '123456'})[0], 429)


if __name__ == '__main__':
    unittest.main()
