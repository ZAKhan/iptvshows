import sqlite3
import os
import json
import time
import threading
from typing import List, Dict, Optional

DB_PATH = os.path.expanduser("~/.config/iptvshows/data.db")

SYNC_TTL = 3600   # seconds before a background re-fetch is triggered (1 hour)

_tls = threading.local()


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_tls, 'conn', None)
    if conn is not None:
        return conn
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-16000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=134217728")
    _tls.conn = conn
    return conn


_current_server_id: int = 0


def set_current_server(sid):
    """Scope favorites/history queries to the given server id (0 = legacy/global)."""
    global _current_server_id
    try:
        _current_server_id = int(sid or 0)
    except (TypeError, ValueError):
        _current_server_id = 0


def initialize():
    with _get_conn() as conn:
        conn.executescript("""
            -- ── User / server data ──────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS servers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                url      TEXT    NOT NULL,
                username TEXT    NOT NULL,
                password TEXT    NOT NULL,
                active   INTEGER DEFAULT 0,
                created  TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id    TEXT NOT NULL,
                stream_type  TEXT NOT NULL,
                name         TEXT NOT NULL,
                stream_icon  TEXT,
                added        TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stream_id, stream_type)
            );

            CREATE TABLE IF NOT EXISTS history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id    TEXT NOT NULL,
                stream_type  TEXT NOT NULL,
                name         TEXT NOT NULL,
                stream_icon  TEXT,
                watched      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stream_id, stream_type)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            -- ── IPTV content cache ───────────────────────────────────────────
            -- Categories (all three types share same schema)
            CREATE TABLE IF NOT EXISTS live_categories (
                category_id   TEXT PRIMARY KEY,
                category_name TEXT NOT NULL,
                parent_id     TEXT DEFAULT '0'
            );

            CREATE TABLE IF NOT EXISTS vod_categories (
                category_id   TEXT PRIMARY KEY,
                category_name TEXT NOT NULL,
                parent_id     TEXT DEFAULT '0'
            );

            CREATE TABLE IF NOT EXISTS series_categories (
                category_id   TEXT PRIMARY KEY,
                category_name TEXT NOT NULL,
                parent_id     TEXT DEFAULT '0'
            );

            -- Streams: key searchable columns + full JSON blob
            CREATE TABLE IF NOT EXISTS live_streams (
                stream_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                category_id TEXT,
                stream_icon TEXT,
                num         INTEGER,
                data        TEXT NOT NULL   -- full JSON
            );
            CREATE INDEX IF NOT EXISTS idx_live_cat  ON live_streams(category_id);
            CREATE INDEX IF NOT EXISTS idx_live_name ON live_streams(name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS vod_streams (
                stream_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                category_id TEXT,
                stream_icon TEXT,
                rating      TEXT,
                data        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vod_cat  ON vod_streams(category_id);
            CREATE INDEX IF NOT EXISTS idx_vod_name ON vod_streams(name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS series_list (
                series_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                category_id TEXT,
                cover       TEXT,
                rating      TEXT,
                data        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_series_cat  ON series_list(category_id);
            CREATE INDEX IF NOT EXISTS idx_series_name ON series_list(name COLLATE NOCASE);

            -- Last played episode per series (for "continue watching")
            CREATE TABLE IF NOT EXISTS series_progress (
                series_id   TEXT PRIMARY KEY,
                episode_id  TEXT NOT NULL,
                season_num  TEXT NOT NULL,
                ep_num      INTEGER,
                ep_title    TEXT,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Watch progress
            CREATE TABLE IF NOT EXISTS watch_status (
                stream_id    TEXT NOT NULL,
                stream_type  TEXT NOT NULL,
                status       TEXT NOT NULL,   -- 'watched' | 'in_progress'
                updated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (stream_id, stream_type)
            );

            -- Sync timestamps
            CREATE TABLE IF NOT EXISTS sync_log (
                key        TEXT PRIMARY KEY,
                synced_at  REAL NOT NULL   -- Unix epoch
            );

            -- First-seen tracker for "newly added" detection
            CREATE TABLE IF NOT EXISTS stream_first_seen (
                stream_type TEXT NOT NULL,         -- 'live' | 'vod' | 'series'
                stream_id   TEXT NOT NULL,
                first_seen  REAL NOT NULL,
                PRIMARY KEY (stream_type, stream_id)
            );
            CREATE INDEX IF NOT EXISTS idx_fs_type_time
                ON stream_first_seen(stream_type, first_seen DESC);
        """)
        _strip_non_tmdb_covers(conn)
        _backfill_first_seen(conn)
        _migrate_per_server(conn)


def _migrate_per_server(conn: sqlite3.Connection):
    """Rebuild favorites + history with server_id column for per-server scoping."""
    fav_cols = [r[1] for r in conn.execute("PRAGMA table_info(favorites)").fetchall()]
    hist_cols = [r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
    needs_fav = 'server_id' not in fav_cols
    needs_hist = 'server_id' not in hist_cols
    if not (needs_fav or needs_hist):
        return
    row = conn.execute("SELECT id FROM servers WHERE active=1 LIMIT 1").fetchone()
    cur_id = int(row[0]) if row else 0
    if needs_fav:
        conn.executescript(f"""
            CREATE TABLE favorites_new (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id    INTEGER NOT NULL DEFAULT 0,
                stream_id    TEXT NOT NULL,
                stream_type  TEXT NOT NULL,
                name         TEXT NOT NULL,
                stream_icon  TEXT,
                added        TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, stream_id, stream_type)
            );
            INSERT INTO favorites_new (server_id, stream_id, stream_type, name, stream_icon, added)
                SELECT {cur_id}, stream_id, stream_type, name, stream_icon, added FROM favorites;
            DROP TABLE favorites;
            ALTER TABLE favorites_new RENAME TO favorites;
            CREATE INDEX IF NOT EXISTS idx_fav_server ON favorites(server_id);
        """)
    if needs_hist:
        conn.executescript(f"""
            CREATE TABLE history_new (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id    INTEGER NOT NULL DEFAULT 0,
                stream_id    TEXT NOT NULL,
                stream_type  TEXT NOT NULL,
                name         TEXT NOT NULL,
                stream_icon  TEXT,
                watched      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, stream_id, stream_type)
            );
            INSERT INTO history_new (server_id, stream_id, stream_type, name, stream_icon, watched)
                SELECT {cur_id}, stream_id, stream_type, name, stream_icon, watched FROM history;
            DROP TABLE history;
            ALTER TABLE history_new RENAME TO history;
            CREATE INDEX IF NOT EXISTS idx_hist_server ON history(server_id);
        """)


def _backfill_first_seen(conn: sqlite3.Connection):
    """One-time: stamp existing rows with first_seen=0 so they don't count as new."""
    has_any = conn.execute("SELECT 1 FROM stream_first_seen LIMIT 1").fetchone()
    if has_any:
        return
    for st_type, table, id_col in (
        ('live',   'live_streams', 'stream_id'),
        ('vod',    'vod_streams',  'stream_id'),
        ('series', 'series_list',  'series_id'),
    ):
        conn.execute(
            f"INSERT OR IGNORE INTO stream_first_seen (stream_type, stream_id, first_seen) "
            f"SELECT ?, {id_col}, 0 FROM {table}", (st_type,)
        )


def _strip_non_tmdb_covers(conn: sqlite3.Connection):
    """One-time scrub: remove m3u tvg-logo URLs from VOD/series rows.
    Only TMDB poster URLs (image.tmdb.org) survive. JSON blobs updated too."""
    # VOD
    rows = conn.execute(
        "SELECT stream_id, data FROM vod_streams "
        "WHERE stream_icon IS NOT NULL AND stream_icon != '' "
        "AND stream_icon NOT LIKE '%image.tmdb.org%'"
    ).fetchall()
    for r in rows:
        try:
            d = json.loads(r["data"])
            d["stream_icon"] = ''
            conn.execute(
                "UPDATE vod_streams SET stream_icon='', data=? WHERE stream_id=?",
                (json.dumps(d), r["stream_id"])
            )
        except Exception:
            pass
    # Series
    rows = conn.execute(
        "SELECT series_id, data FROM series_list "
        "WHERE cover IS NOT NULL AND cover != '' "
        "AND cover NOT LIKE '%image.tmdb.org%'"
    ).fetchall()
    for r in rows:
        try:
            d = json.loads(r["data"])
            d["cover"] = ''
            conn.execute(
                "UPDATE series_list SET cover='', data=? WHERE series_id=?",
                (json.dumps(d), r["series_id"])
            )
        except Exception:
            pass


# ── Sync helpers ──────────────────────────────────────────────────────────────

def is_stale(key: str, ttl: int = SYNC_TTL) -> bool:
    with _get_conn() as conn:
        row = conn.execute("SELECT synced_at FROM sync_log WHERE key=?", (key,)).fetchone()
        if not row:
            return True
        return (time.time() - row["synced_at"]) > ttl


def _mark_synced(conn: sqlite3.Connection, key: str):
    conn.execute(
        "INSERT OR REPLACE INTO sync_log (key, synced_at) VALUES (?,?)",
        (key, time.time())
    )


# ── Live categories ───────────────────────────────────────────────────────────

def save_live_categories(cats: List[Dict]):
    with _get_conn() as conn:
        conn.execute("DELETE FROM live_categories")
        conn.executemany(
            "INSERT OR REPLACE INTO live_categories (category_id, category_name, parent_id) VALUES (?,?,?)",
            [(c.get('category_id',''), c.get('category_name',''), str(c.get('parent_id', 0))) for c in cats]
        )
        _mark_synced(conn, 'live_categories')


def get_live_categories_cached() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM live_categories ORDER BY category_name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


# ── Live streams ──────────────────────────────────────────────────────────────

def save_live_streams(streams: List[Dict]) -> Dict[str, int]:
    with _get_conn() as conn:
        before = {r[0] for r in conn.execute("SELECT stream_id FROM live_streams")}
        conn.execute("DELETE FROM live_streams")
        conn.executemany(
            "INSERT OR REPLACE INTO live_streams (stream_id, name, category_id, stream_icon, num, data) VALUES (?,?,?,?,?,?)",
            [
                (
                    str(s.get('stream_id', '')),
                    s.get('name', ''),
                    str(s.get('category_id', '')),
                    s.get('stream_icon', ''),
                    s.get('num', 0),
                    json.dumps(s),
                )
                for s in streams
            ]
        )
        after = {str(s.get('stream_id', '')) for s in streams}
        added = after - before
        now = time.time()
        if added:
            conn.executemany(
                "INSERT OR IGNORE INTO stream_first_seen (stream_type, stream_id, first_seen) VALUES ('live', ?, ?)",
                [(sid, now) for sid in added]
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('latest_sync_live', ?)",
                (str(now),)
            )
        _mark_synced(conn, 'live_streams')
        return {'added': len(added), 'removed': len(before - after)}


def get_live_streams_cached(category_id: Optional[str] = None,
                            limit: Optional[int] = None) -> List[Dict]:
    with _get_conn() as conn:
        sql = "SELECT data FROM live_streams"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [json.loads(r["data"]) for r in rows]


# ── VOD categories ────────────────────────────────────────────────────────────

def save_vod_categories(cats: List[Dict]):
    with _get_conn() as conn:
        conn.execute("DELETE FROM vod_categories")
        conn.executemany(
            "INSERT OR REPLACE INTO vod_categories (category_id, category_name, parent_id) VALUES (?,?,?)",
            [(c.get('category_id',''), c.get('category_name',''), str(c.get('parent_id', 0))) for c in cats]
        )
        _mark_synced(conn, 'vod_categories')


def get_vod_categories_cached() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM vod_categories ORDER BY category_name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


# ── VOD streams ───────────────────────────────────────────────────────────────

def save_vod_streams(streams: List[Dict]) -> Dict[str, int]:
    with _get_conn() as conn:
        before = {r[0] for r in conn.execute("SELECT stream_id FROM vod_streams")}
        conn.execute("DELETE FROM vod_streams")
        conn.executemany(
            "INSERT OR REPLACE INTO vod_streams (stream_id, name, category_id, stream_icon, rating, data) VALUES (?,?,?,?,?,?)",
            [
                (
                    str(s.get('stream_id', '')),
                    s.get('name', ''),
                    str(s.get('category_id', '')),
                    s.get('stream_icon', ''),
                    str(s.get('rating', '') or s.get('rating_5based', '')),
                    json.dumps(s),
                )
                for s in streams
            ]
        )
        after = {str(s.get('stream_id', '')) for s in streams}
        added = after - before
        now = time.time()
        if added:
            conn.executemany(
                "INSERT OR IGNORE INTO stream_first_seen (stream_type, stream_id, first_seen) VALUES ('vod', ?, ?)",
                [(sid, now) for sid in added]
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('latest_sync_vod', ?)",
                (str(now),)
            )
        _mark_synced(conn, 'vod_streams')
        return {'added': len(added), 'removed': len(before - after)}


def get_vod_streams_cached(category_id: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict]:
    with _get_conn() as conn:
        sql = "SELECT data FROM vod_streams"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [json.loads(r["data"]) for r in rows]


# ── Series categories ─────────────────────────────────────────────────────────

def save_series_categories(cats: List[Dict]):
    with _get_conn() as conn:
        conn.execute("DELETE FROM series_categories")
        conn.executemany(
            "INSERT OR REPLACE INTO series_categories (category_id, category_name, parent_id) VALUES (?,?,?)",
            [(c.get('category_id',''), c.get('category_name',''), str(c.get('parent_id', 0))) for c in cats]
        )
        _mark_synced(conn, 'series_categories')


def get_series_categories_cached() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM series_categories ORDER BY category_name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


# ── Series list ───────────────────────────────────────────────────────────────

def save_series_list(series: List[Dict]) -> Dict[str, int]:
    with _get_conn() as conn:
        before = {r[0] for r in conn.execute("SELECT series_id FROM series_list")}
        conn.execute("DELETE FROM series_list")
        conn.executemany(
            "INSERT OR REPLACE INTO series_list (series_id, name, category_id, cover, rating, data) VALUES (?,?,?,?,?,?)",
            [
                (
                    str(s.get('series_id', '')),
                    s.get('name', ''),
                    str(s.get('category_id', '')),
                    s.get('cover', ''),
                    str(s.get('rating', '') or s.get('rating_5based', '')),
                    json.dumps(s),
                )
                for s in series
            ]
        )
        after = {str(s.get('series_id', '')) for s in series}
        added = after - before
        now = time.time()
        if added:
            conn.executemany(
                "INSERT OR IGNORE INTO stream_first_seen (stream_type, stream_id, first_seen) VALUES ('series', ?, ?)",
                [(sid, now) for sid in added]
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('latest_sync_series', ?)",
                (str(now),)
            )
        _mark_synced(conn, 'series_list')
        return {'added': len(added), 'removed': len(before - after)}


def get_series_cached(category_id: Optional[str] = None,
                      limit: Optional[int] = None) -> List[Dict]:
    with _get_conn() as conn:
        sql = "SELECT data FROM series_list"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [json.loads(r["data"]) for r in rows]


def list_live_streams(category_id: Optional[str] = None,
                      limit: Optional[int] = None,
                      offset: int = 0) -> List[Dict]:
    """Lightweight live stream list — no JSON blob parse."""
    with _get_conn() as conn:
        sql = "SELECT stream_id, name, category_id, stream_icon, num FROM live_streams"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_vod_streams(category_id: Optional[str] = None,
                     limit: Optional[int] = None,
                     offset: int = 0) -> List[Dict]:
    with _get_conn() as conn:
        sql = "SELECT stream_id, name, category_id, stream_icon, rating FROM vod_streams"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_series(category_id: Optional[str] = None,
                limit: Optional[int] = None,
                offset: int = 0) -> List[Dict]:
    with _get_conn() as conn:
        sql = "SELECT series_id, name, category_id, cover, rating FROM series_list"
        params: list = []
        if category_id:
            sql += " WHERE category_id=?"
            params.append(str(category_id))
        sql += " ORDER BY name COLLATE NOCASE"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r['stream_icon'] = r.get('cover', '')
        return rows


def _latest_sync_threshold(stream_type: str) -> float:
    try:
        return float(get_setting(f'latest_sync_{stream_type}', '0') or 0)
    except (TypeError, ValueError):
        return 0.0


def list_new_vod_streams(query: str = '', limit: Optional[int] = None) -> List[Dict]:
    threshold = _latest_sync_threshold('vod')
    sql = (
        "SELECT v.stream_id, v.name, v.category_id, v.stream_icon, v.rating "
        "FROM vod_streams v "
        "INNER JOIN stream_first_seen f "
        "  ON f.stream_id=v.stream_id AND f.stream_type='vod' "
        "WHERE f.first_seen >= ?"
    )
    params: list = [threshold]
    if query:
        sql += " AND v.name LIKE ? COLLATE NOCASE"
        params.append(f'%{query}%')
    sql += " ORDER BY v.name COLLATE NOCASE"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with _get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_new_series(query: str = '', limit: Optional[int] = None) -> List[Dict]:
    threshold = _latest_sync_threshold('series')
    sql = (
        "SELECT s.series_id, s.name, s.category_id, s.cover, s.rating "
        "FROM series_list s "
        "INNER JOIN stream_first_seen f "
        "  ON f.stream_id=s.series_id AND f.stream_type='series' "
        "WHERE f.first_seen >= ?"
    )
    params: list = [threshold]
    if query:
        sql += " AND s.name LIKE ? COLLATE NOCASE"
        params.append(f'%{query}%')
    sql += " ORDER BY s.name COLLATE NOCASE"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with _get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r['stream_icon'] = r.get('cover', '')
        return rows


def list_new_live_streams(query: str = '', limit: Optional[int] = None) -> List[Dict]:
    threshold = _latest_sync_threshold('live')
    sql = (
        "SELECT v.stream_id, v.name, v.category_id, v.stream_icon, v.num "
        "FROM live_streams v "
        "INNER JOIN stream_first_seen f "
        "  ON f.stream_id=v.stream_id AND f.stream_type='live' "
        "WHERE f.first_seen >= ?"
    )
    params: list = [threshold]
    if query:
        sql += " AND v.name LIKE ? COLLATE NOCASE"
        params.append(f'%{query}%')
    sql += " ORDER BY v.name COLLATE NOCASE"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with _get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def search_live_streams_lite(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT stream_id, name, category_id, stream_icon, num FROM live_streams "
            "WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        return [dict(r) for r in rows]


def search_vod_streams_lite(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT stream_id, name, category_id, stream_icon, rating FROM vod_streams "
            "WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        return [dict(r) for r in rows]


def search_series_lite(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT series_id, name, category_id, cover, rating FROM series_list "
            "WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        out = [dict(r) for r in rows]
        for r in out:
            r['stream_icon'] = r.get('cover', '')
        return out


def search_live_streams(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT data FROM live_streams WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]


def search_vod_streams(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT data FROM vod_streams WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]


def search_series(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT data FROM series_list WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY name COLLATE NOCASE LIMIT ?",
            (f'%{query}%', limit)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]


def update_vod_cover(stream_id: str, cover_url: str):
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT data FROM vod_streams WHERE stream_id=?", (stream_id,)
        ).fetchone()
        if not row:
            return
        data = json.loads(row["data"])
        data["stream_icon"] = cover_url
        conn.execute(
            "UPDATE vod_streams SET stream_icon=?, data=? WHERE stream_id=?",
            (cover_url, json.dumps(data), stream_id)
        )


def get_vod_without_tmdb_poster() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT stream_id, name, stream_icon FROM vod_streams "
            "WHERE stream_icon NOT LIKE '%image.tmdb.org%' "
            "OR stream_icon IS NULL OR stream_icon=''"
        ).fetchall()
        return [dict(r) for r in rows]


def update_series_cover(series_id: str, cover_url: str):
    """Update the cover URL for a series entry (used by TMDB fetcher)."""
    with _get_conn() as conn:
        # Update the cover column and the cover field inside the JSON data blob
        row = conn.execute(
            "SELECT data FROM series_list WHERE series_id=?", (series_id,)
        ).fetchone()
        if not row:
            return
        data = json.loads(row["data"])
        data["cover"] = cover_url
        conn.execute(
            "UPDATE series_list SET cover=?, data=? WHERE series_id=?",
            (cover_url, json.dumps(data), series_id)
        )


def get_series_without_tmdb_poster() -> List[Dict]:
    """Return series whose cover is not already from TMDB."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT series_id, name, cover FROM series_list "
            "WHERE cover NOT LIKE '%image.tmdb.org%' OR cover IS NULL OR cover=''"
        ).fetchall()
        return [dict(r) for r in rows]


def has_live_data() -> bool:
    with _get_conn() as conn:
        return conn.execute("SELECT 1 FROM live_streams LIMIT 1").fetchone() is not None

def has_vod_data() -> bool:
    with _get_conn() as conn:
        return conn.execute("SELECT 1 FROM vod_streams LIMIT 1").fetchone() is not None

def has_series_data() -> bool:
    with _get_conn() as conn:
        return conn.execute("SELECT 1 FROM series_list LIMIT 1").fetchone() is not None


# ── Servers ───────────────────────────────────────────────────────────────────

def add_server(name: str, url: str, username: str, password: str) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO servers (name, url, username, password) VALUES (?,?,?,?)",
            (name, url, username, password)
        )
        return cur.lastrowid


def get_servers() -> List[Dict]:
    with _get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM servers ORDER BY created DESC")]


def get_active_server() -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM servers WHERE active=1 LIMIT 1").fetchone()
        return dict(row) if row else None


def set_active_server(server_id: int):
    """Switch active server. If actually changing, wipe the cached library
    (streams + categories + sync log) so the next sync repopulates cleanly —
    prevents playing old-server stream URLs against the new server."""
    with _get_conn() as conn:
        prev = conn.execute("SELECT id FROM servers WHERE active=1 LIMIT 1").fetchone()
        prev_id = int(prev[0]) if prev else 0
        conn.execute("UPDATE servers SET active=0")
        conn.execute("UPDATE servers SET active=1 WHERE id=?", (server_id,))
        if prev_id and prev_id != int(server_id):
            for tbl in (
                'live_streams', 'vod_streams', 'series_list',
                'live_categories', 'vod_categories', 'series_categories',
                'sync_log', 'stream_first_seen',
            ):
                conn.execute(f"DELETE FROM {tbl}")


def delete_server(server_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM servers WHERE id=?", (server_id,))


def update_server(server_id: int, name: str, url: str, username: str, password: str):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE servers SET name=?, url=?, username=?, password=? WHERE id=?",
            (name, url, username, password, server_id)
        )


# ── Favorites ─────────────────────────────────────────────────────────────────

def add_favorite(stream_id: str, stream_type: str, name: str, icon: str = ""):
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO favorites (server_id, stream_id, stream_type, name, stream_icon) VALUES (?,?,?,?,?)",
            (_current_server_id, stream_id, stream_type, name, icon)
        )


def remove_favorite(stream_id: str, stream_type: str):
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE server_id=? AND stream_id=? AND stream_type=?",
            (_current_server_id, stream_id, stream_type)
        )


def is_favorite(stream_id: str, stream_type: str) -> bool:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM favorites WHERE server_id=? AND stream_id=? AND stream_type=?",
            (_current_server_id, stream_id, stream_type)
        ).fetchone() is not None


def get_favorites(stream_type: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if stream_type:
            rows = conn.execute(
                "SELECT * FROM favorites WHERE server_id=? AND stream_type=? ORDER BY added DESC",
                (_current_server_id, stream_type)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM favorites WHERE server_id=? ORDER BY added DESC",
                (_current_server_id,)
            ).fetchall()
        return [dict(r) for r in rows]


# ── History ───────────────────────────────────────────────────────────────────

def add_history(stream_id: str, stream_type: str, name: str, icon: str = ""):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO history (server_id, stream_id, stream_type, name, stream_icon, watched)
               VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(server_id, stream_id, stream_type) DO UPDATE SET watched=CURRENT_TIMESTAMP""",
            (_current_server_id, stream_id, stream_type, name, icon)
        )


# ── Series progress (last played episode) ────────────────────────────────────

def save_series_progress(series_id: str, episode_id: str, season_num: str,
                         ep_num, ep_title: str):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO series_progress
               (series_id, episode_id, season_num, ep_num, ep_title, updated_at)
               VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(series_id) DO UPDATE
               SET episode_id=excluded.episode_id, season_num=excluded.season_num,
                   ep_num=excluded.ep_num, ep_title=excluded.ep_title,
                   updated_at=CURRENT_TIMESTAMP""",
            (series_id, episode_id, str(season_num), ep_num, ep_title)
        )


def get_series_progress(series_id: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM series_progress WHERE series_id=?", (series_id,)
        ).fetchone()
        return dict(row) if row else None


# ── Watch status ───────────────────────────────────────────────────────────────

def set_watch_status(stream_id: str, stream_type: str, status: Optional[str]):
    """Set 'watched'/'in_progress', or pass None to clear."""
    with _get_conn() as conn:
        if status is None:
            conn.execute(
                "DELETE FROM watch_status WHERE stream_id=? AND stream_type=?",
                (stream_id, stream_type)
            )
        else:
            conn.execute(
                """INSERT INTO watch_status (stream_id, stream_type, status, updated_at)
                   VALUES (?,?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(stream_id, stream_type) DO UPDATE
                   SET status=excluded.status, updated_at=CURRENT_TIMESTAMP""",
                (stream_id, stream_type, status)
            )


def get_watch_status(stream_id: str, stream_type: str) -> Optional[str]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT status FROM watch_status WHERE stream_id=? AND stream_type=?",
            (stream_id, stream_type)
        ).fetchone()
        return row["status"] if row else None


def bulk_get_watch_statuses(stream_ids: List[str], stream_type: str) -> Dict[str, str]:
    """Return {stream_id: status} for all ids that have a status recorded."""
    if not stream_ids:
        return {}
    placeholders = ",".join("?" * len(stream_ids))
    with _get_conn() as conn:
        rows = conn.execute(
            f"SELECT stream_id, status FROM watch_status "
            f"WHERE stream_type=? AND stream_id IN ({placeholders})",
            [stream_type] + stream_ids
        ).fetchall()
        return {r["stream_id"]: r["status"] for r in rows}


def get_live_stream_data(stream_id: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT data FROM live_streams WHERE stream_id=?", (stream_id,)).fetchone()
        return json.loads(row["data"]) if row else None


def get_vod_stream_data(stream_id: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT data FROM vod_streams WHERE stream_id=?", (stream_id,)).fetchone()
        return json.loads(row["data"]) if row else None


def get_series_data(series_id: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT data FROM series_list WHERE series_id=?", (series_id,)).fetchone()
        return json.loads(row["data"]) if row else None


def get_history(limit: int = 50) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history WHERE server_id=? ORDER BY watched DESC LIMIT ?",
            (_current_server_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with _get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value)
        )
