# Dayline

Personal planner/agenda. Front end is one file (`index.html`), no frameworks, light theme by default with a dark toggle.
Hosted on GitHub Pages; data in Supabase (Postgres + email-code login + row-level security).
`server.py` (Python stdlib + SQLite) is the offline/local alternative.

## Run
- `python3 server.py` → http://localhost:5178. Data is saved to `dayline.db` (git-ignored).
- Env: `DAYLINE_PORT`, `DAYLINE_HOST` (default 127.0.0.1, localhost only), `DAYLINE_DB`.
- Production: https://mattyinc.github.io/dayline/ — setup in `supabase/README.md`, schema in `supabase/schema.sql`.
- Opening `index.html` directly still works, but then data lives only in that browser's localStorage.
- Tests: `python3 -m unittest -v`.

## Structure
- Views: Agenda (1), Week (2), Tasks (3), Assistant (4). Keys: `N` new, `⌘K` palette, `[` collapse sidebar, `←/→` weeks, `T` this week.
- Spaces: work, build, growth, life. Types: meeting, focus, call, email, learn, personal, task.
- Sync priority: Supabase (configured + signed in) → `server.py` on localhost → browser only. Config: `SUPABASE_CONFIG` in `index.html` (anon key is public by design) or the Assistant view (stored in `dayline:sb`).
- Supabase sync is per row: upserts only changed items, deletes removed ones (diff against `lastSynced`), realtime subscription triggers a pull.
- When served by `server.py`, the page syncs with `/api/items`: pulls on load, on tab focus and every 30s; PUTs the full list 600ms after a change. localStorage (`dayline:v1`) is a cache.
- The remote (Supabase or server) is the source of truth: a pull always replaces the local copy, and a stale local copy is never auto-uploaded. Moving data in is explicit: Import JSON.
- New browsers start empty (no sample data). Assistant view has *Clear all items* (confirm dialog + undo toast).
- UI state: `dayline:v1:ui`. Theme: `dayline:theme`.

## Item shape
```json
{ "id": "abc123", "title": "...", "type": "focus", "space": "work",
  "date": "2026-11-24", "time": "10:00", "dur": 60, "done": false, "note": "" }
```
`time` is `null` for all-day/anytime items.

## Assistant hooks
- `window.dayline`: `list(filter)`, `add(string|object)`, `update(id, patch)`, `complete(id)`, `remove(id)`, `brief()`, `parse(text)`.
- HTTP API (see docstring in `server.py`): `GET/PUT/POST /api/items`, `PATCH/DELETE /api/items/<id>`, `GET /api/brief` (Markdown). Filters: `?date=&space=&done=0|1`.
- The page does a full-list PUT; an API write is picked up on the page's next pull. Last write wins.
- The Assistant view's endpoint field overrides `/api/items` (a different server must allow CORS).
- Export/Import JSON uses `{ exported, items }`.

## Design
Glass panels over animated gradient light: mist-grey page (#e9ecf1) with soft ice-blue light. Geist everywhere, light weights (300–500; 600 only on the logo mark). Indigo accent.
Easing: `--ease` cubic-bezier(.2,.8,.2,1), `--spring` cubic-bezier(.34,1.36,.5,1). Respects reduced motion.
Design language studied from a commercial template (Sylva by OVERSHOOT); no code, assets, or copy were taken from it. Keep it that way.
