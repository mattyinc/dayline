"""Tests for the Dayline API. Run: python3 -m unittest -v"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["DAYLINE_QUIET"] = "1"
import server  # noqa: E402


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        server.DB_PATH = os.path.join(cls.tmp.name, "test.db")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.req("PUT", "/api/items", {"items": []})

    def req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r) as res:
                raw = res.read().decode()
                return res.status, (json.loads(raw) if res.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            with e:
                raw = e.read().decode()
            try:
                return e.code, json.loads(raw or "{}")
            except json.JSONDecodeError:
                return e.code, raw

    def test_create_and_list(self):
        code, it = self.req("POST", "/api/items", {"title": "Recon mock run 3", "date": "2026-11-24", "time": "10:00", "space": "work"})
        self.assertEqual(code, 201)
        self.assertEqual(it["type"], "task")  # default
        _, out = self.req("GET", "/api/items")
        self.assertEqual([i["title"] for i in out["items"]], ["Recon mock run 3"])

    def test_filter_by_date_and_done(self):
        self.req("POST", "/api/items", {"title": "A", "date": "2026-11-24"})
        self.req("POST", "/api/items", {"title": "B", "date": "2026-11-25", "done": True})
        _, out = self.req("GET", "/api/items?date=2026-11-24")
        self.assertEqual([i["title"] for i in out["items"]], ["A"])
        _, out = self.req("GET", "/api/items?done=1")
        self.assertEqual([i["title"] for i in out["items"]], ["B"])

    def test_patch_completes_item(self):
        _, it = self.req("POST", "/api/items", {"title": "Pay card", "date": "2026-11-24"})
        code, upd = self.req("PATCH", f"/api/items/{it['id']}", {"done": True})
        self.assertEqual(code, 200)
        self.assertTrue(upd["done"])
        self.assertEqual(upd["title"], "Pay card")  # untouched fields survive

    def test_delete(self):
        _, it = self.req("POST", "/api/items", {"title": "Temp", "date": "2026-11-24"})
        self.assertEqual(self.req("DELETE", f"/api/items/{it['id']}")[0], 200)
        self.assertEqual(self.req("DELETE", f"/api/items/{it['id']}")[0], 404)

    def test_put_replaces_everything(self):
        self.req("POST", "/api/items", {"title": "Old", "date": "2026-11-24"})
        self.req("PUT", "/api/items", {"items": [{"title": "New", "date": "2026-11-24"}]})
        _, out = self.req("GET", "/api/items")
        self.assertEqual([i["title"] for i in out["items"]], ["New"])

    def test_validation(self):
        self.assertEqual(self.req("POST", "/api/items", {"date": "2026-11-24"})[0], 400)
        self.assertEqual(self.req("POST", "/api/items", {"title": "x", "date": "24/11"})[0], 400)
        self.assertEqual(self.req("POST", "/api/items", {"title": "x", "time": "3pm"})[0], 400)

    def test_ordering_untimed_last(self):
        self.req("POST", "/api/items", {"title": "Anytime", "date": "2026-11-24"})
        self.req("POST", "/api/items", {"title": "Morning", "date": "2026-11-24", "time": "08:00"})
        _, out = self.req("GET", "/api/items")
        self.assertEqual([i["title"] for i in out["items"]], ["Morning", "Anytime"])

    def test_db_file_not_served(self):
        self.assertEqual(self.req("GET", "/dayline.db")[0], 404)
        self.assertEqual(self.req("GET", "/server.py")[0], 404)

    def test_brief(self):
        from datetime import date
        self.req("POST", "/api/items", {"title": "Stand-up", "date": date.today().isoformat(), "time": "09:00"})
        code, text = self.req("GET", "/api/brief")
        self.assertEqual(code, 200)
        self.assertIn("Stand-up", text)


if __name__ == "__main__":
    unittest.main()
