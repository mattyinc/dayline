#!/usr/bin/env python3
"""Dayline server: serves index.html and a small JSON API backed by SQLite.

Standard library only. Run:  python3 server.py   (then open http://localhost:5178)

API
  GET    /api/items              -> {"items": [...]}         optional ?date=YYYY-MM-DD&space=work&done=0
  PUT    /api/items              <- {"items": [...]}         replace everything (what the UI uses)
  POST   /api/items              <- {...item}                create one, returns the item
  PATCH  /api/items/<id>         <- {...partial}             update one, returns the item
  DELETE /api/items/<id>                                     delete one
  GET    /api/brief                                          today's brief as Markdown
"""
import json
import os
import re
import secrets
import sqlite3
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DAYLINE_DB", os.path.join(ROOT, "dayline.db"))
HOST = os.environ.get("DAYLINE_HOST", "127.0.0.1")
PORT = int(os.environ.get("DAYLINE_PORT", "5178"))

TYPES = {"meeting", "focus", "call", "email", "learn", "personal", "task"}
SPACES = {"work", "build", "growth", "life"}
FIELDS = ("id", "title", "type", "space", "date", "time", "dur", "done", "note")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id    TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type  TEXT NOT NULL DEFAULT 'task',
  space TEXT NOT NULL DEFAULT 'work',
  date  TEXT NOT NULL,
  time  TEXT,
  dur   INTEGER NOT NULL DEFAULT 30,
  done  INTEGER NOT NULL DEFAULT 0,
  note  TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS items_date ON items(date);
"""


def connect(path=None):
    con = sqlite3.connect(path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def normalize(x, existing=None):
    """Validate an incoming item; fill defaults. Raises ValueError on bad input."""
    base = dict(existing or {})
    base.update({k: v for k, v in (x or {}).items() if k in FIELDS})
    title = str(base.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    d = str(base.get("date") or date.today().isoformat())
    if not re.fullmatch(r"\d{4}-\d\d-\d\d", d):
        raise ValueError("date must be YYYY-MM-DD")
    t = base.get("time")
    if t in ("", None):
        t = None
    elif not re.fullmatch(r"\d\d:\d\d", str(t)):
        raise ValueError("time must be HH:MM or null")
    return {
        "id": str(base.get("id") or secrets.token_hex(4)),
        "title": title,
        "type": base.get("type") if base.get("type") in TYPES else "task",
        "space": base.get("space") if base.get("space") in SPACES else "work",
        "date": d,
        "time": t,
        "dur": max(5, int(base.get("dur") or 30)),
        "done": bool(base.get("done")),
        "note": str(base.get("note") or ""),
    }


def row_to_item(r):
    item = {k: r[k] for k in FIELDS}
    item["done"] = bool(item["done"])
    return item


def upsert(con, it):
    con.execute(
        """INSERT INTO items (id,title,type,space,date,time,dur,done,note,updated_at)
           VALUES (:id,:title,:type,:space,:date,:time,:dur,:done,:note,datetime('now'))
           ON CONFLICT(id) DO UPDATE SET title=excluded.title,type=excluded.type,space=excluded.space,
             date=excluded.date,time=excluded.time,dur=excluded.dur,done=excluded.done,note=excluded.note,
             updated_at=excluded.updated_at""",
        {**it, "done": int(it["done"])},
    )


def list_items(con, date_=None, space=None, done=None):
    sql, args = "SELECT * FROM items WHERE 1=1", []
    if date_:
        sql += " AND date = ?"; args.append(date_)
    if space:
        sql += " AND space = ?"; args.append(space)
    if done in ("0", "1"):
        sql += " AND done = ?"; args.append(int(done))
    sql += " ORDER BY date, COALESCE(time, '99:99')"
    return [row_to_item(r) for r in con.execute(sql, args)]


def brief(con, today=None):
    today = today or date.today()
    t, tm = today.isoformat(), (today + timedelta(days=1)).isoformat()
    items = list_items(con)
    line = lambda i: f"- [{'x' if i['done'] else ' '}] {i['time'] or 'any time'} · {i['title']} ({i['type']}, {i['space']}, {i['dur']}m)"
    over = [i for i in items if i["date"] < t and not i["done"]]
    tod = [i for i in items if i["date"] == t]
    tom = [i for i in items if i["date"] == tm]
    out = [f"# Daily brief — {today:%A %d %B %Y}", "",
           f"Open: {sum(not i['done'] for i in items)} · Overdue: {len(over)} · Today: {len(tod)}", ""]
    if over:
        out += ["## Overdue", *[line(i) + f" — was due {i['date']}" for i in over], ""]
    out += ["## Today", *([line(i) for i in tod] or ["- (clear)"]), "", "## Tomorrow", *([line(i) for i in tom] or ["- (clear)"])]
    return "\n".join(out)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    # Only the app itself is public; never serve the database or source files by accident.
    def translate_path(self, path):
        p = urlparse(path).path
        if p in ("/", "/index.html"):
            return os.path.join(ROOT, "index.html")
        return os.path.join(ROOT, "__nope__")

    def log_message(self, fmt, *args):
        if os.environ.get("DAYLINE_QUIET") != "1":
            super().log_message(fmt, *args)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _route(self):
        u = urlparse(self.path)
        m = re.fullmatch(r"/api/items(?:/([\w-]+))?", u.path)
        return u, m

    def do_GET(self):
        u, m = self._route()
        if u.path == "/api/brief":
            with connect() as con:
                body = brief(con).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if m and not m.group(1):
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            with connect() as con:
                return self._json(200, {"items": list_items(con, q.get("date"), q.get("space"), q.get("done"))})
        if u.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        return super().do_GET()

    def do_PUT(self):
        u, m = self._route()
        if not (m and not m.group(1)):
            return self._json(404, {"error": "not found"})
        try:
            items = [normalize(x) for x in self._body().get("items", [])]
        except (ValueError, json.JSONDecodeError, AttributeError) as e:
            return self._json(400, {"error": str(e)})
        with connect() as con:
            con.execute("DELETE FROM items")
            for it in items:
                upsert(con, it)
        self._json(200, {"items": items})

    def do_POST(self):
        u, m = self._route()
        if not (m and not m.group(1)):
            return self._json(404, {"error": "not found"})
        try:
            it = normalize(self._body())
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"error": str(e)})
        with connect() as con:
            upsert(con, it)
        self._json(201, it)

    def do_PATCH(self):
        u, m = self._route()
        if not (m and m.group(1)):
            return self._json(404, {"error": "not found"})
        with connect() as con:
            r = con.execute("SELECT * FROM items WHERE id = ?", (m.group(1),)).fetchone()
            if not r:
                return self._json(404, {"error": "no such item"})
            try:
                it = normalize({**self._body(), "id": m.group(1)}, existing=row_to_item(r))
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": str(e)})
            upsert(con, it)
        self._json(200, it)

    def do_DELETE(self):
        u, m = self._route()
        if not (m and m.group(1)):
            return self._json(404, {"error": "not found"})
        with connect() as con:
            n = con.execute("DELETE FROM items WHERE id = ?", (m.group(1),)).rowcount
        self._json(200 if n else 404, {"deleted": n})


def main():
    connect().close()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Dayline on http://{'localhost' if HOST == '127.0.0.1' else HOST}:{PORT}  ·  db: {DB_PATH}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
