import sqlite3
import os
import json
import time
from typing import List, Dict, Optional

DB_PATH = os.path.expanduser("~/.config/iptvshows/data.db")

SYNC_TTL = 3600   # seconds before a background re-fetch is triggered (1 hour)


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # WAL mode: readers never block writers, much faster for concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-8000")   # 8 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


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
        """)


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

def save_live_streams(streams: List[Dict]):
    with _get_conn() as conn:
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
        _mark_synced(conn, 'live_streams')


def get_live_streams_cached(category_id: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if category_id:
            rows = conn.execute(
                "SELECT data FROM live_streams WHERE category_id=? ORDER BY num, name COLLATE NOCASE",
                (str(category_id),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT data FROM live_streams ORDER BY num, name COLLATE NOCASE"
            ).fetchall()
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

def save_vod_streams(streams: List[Dict]):
    with _get_conn() as conn:
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
        _mark_synced(conn, 'vod_streams')


def get_vod_streams_cached(category_id: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if category_id:
            rows = conn.execute(
                "SELECT data FROM vod_streams WHERE category_id=? ORDER BY name COLLATE NOCASE",
                (str(category_id),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT data FROM vod_streams ORDER BY name COLLATE NOCASE"
            ).fetchall()
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

def save_series_list(series: List[Dict]):
    with _get_conn() as conn:
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
        _mark_synced(conn, 'series_list')


def get_series_cached(category_id: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if category_id:
            rows = conn.execute(
                "SELECT data FROM series_list WHERE category_id=? ORDER BY name COLLATE NOCASE",
                (str(category_id),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT data FROM series_list ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]


def search_live_streams(query: str, limit: int = 300) -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT data FROM live_streams WHERE name LIKE ? COLLATE NOCASE "
            "ORDER BY num, name COLLATE NOCASE LIMIT ?",
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
    with _get_conn() as conn:
        conn.execute("UPDATE servers SET active=0")
        conn.execute("UPDATE servers SET active=1 WHERE id=?", (server_id,))


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
            "INSERT OR REPLACE INTO favorites (stream_id, stream_type, name, stream_icon) VALUES (?,?,?,?)",
            (stream_id, stream_type, name, icon)
        )


def remove_favorite(stream_id: str, stream_type: str):
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE stream_id=? AND stream_type=?",
            (stream_id, stream_type)
        )


def is_favorite(stream_id: str, stream_type: str) -> bool:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM favorites WHERE stream_id=? AND stream_type=?",
            (stream_id, stream_type)
        ).fetchone() is not None


def get_favorites(stream_type: Optional[str] = None) -> List[Dict]:
    with _get_conn() as conn:
        if stream_type:
            rows = conn.execute(
                "SELECT * FROM favorites WHERE stream_type=? ORDER BY added DESC", (stream_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM favorites ORDER BY added DESC").fetchall()
        return [dict(r) for r in rows]


# ── History ───────────────────────────────────────────────────────────────────

def add_history(stream_id: str, stream_type: str, name: str, icon: str = ""):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO history (stream_id, stream_type, name, stream_icon, watched)
               VALUES (?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(stream_id, stream_type) DO UPDATE SET watched=CURRENT_TIMESTAMP""",
            (stream_id, stream_type, name, icon)
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
            "SELECT * FROM history ORDER BY watched DESC LIMIT ?", (limit,)
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
