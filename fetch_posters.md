# IPTV Player

**Version 1.0.0**

A desktop IPTV client for Linux built with Python and PyQt6. Supports Xtream Codes API and M3U playlists, with local SQLite caching, TMDB poster integration, and MPV playback.

---

## Screenshots

> Live TV · Movies · Series · Search · Favorites

---

## Features

### Content
- **Live TV** — browse channels by category, view EPG (now/next), channel logos with lazy loading
- **Movies** — poster grid with category sidebar, detail page (plot, rating, year, genre, poster)
- **Series** — browse shows by category, season/episode list, per-episode playback
- **Global Search** — searches Live TV, Movies, and Series simultaneously across all categories
- **Favorites** — save Live TV channels, movies, and series; accessible from a dedicated tab
- **Watch History** — automatically records everything you play with timestamps

### Watch Tracking
- **Auto in-progress** — any item you play is immediately marked as In Progress
- **Mark as Watched** — button in the movie detail page; right-click any card or episode
- **Clear Status** — right-click → Clear Status to remove tracking
- **Visual badges** — green circle (✓ watched) or orange circle (… in-progress) on poster cards
- **Episode indicators** — `✓` / `…` prefix on each episode row in the series viewer
- **Per-episode tracking** — watch status is stored individually per episode, not per series

### Library Management
- **Sync** — downloads the full M3U playlist from your server and saves to local SQLite
- **Poster prefetch** — bulk-caches all artwork to disk after each sync
- **TMDB integration** — fetch high-quality posters from The Movie Database for series and movies
- **Image cache** — all artwork stored in `~/.config/iptvshows/images/` (clearable from Settings)
- **Offline browsing** — all content accessible from local DB after first sync; no network required to browse

### Playback
- **MPV backend** — streams via MPV with configurable extra arguments
- **Fullscreen option** — configurable in Settings
- **Stream types** — Live (`.ts`), VOD (`.mp4`), Series episodes (`.mp4`/`.mkv`)
- **Direct URL construction** — Xtream Codes stream URLs built client-side, no extra API calls at play time

### Interface
- **Dark theme** — deep purple-tinted dark UI (inspired by modern streaming apps)
- **Collapsible sidebar** — click the logo to collapse to icon-only mode
- **Category filter** — search bar above the category list on each page
- **Lazy image loading** — only visible cards fetch images; scroll triggers more loading
- **Keyboard shortcuts** — Esc to go back from detail views

### Servers
- **Multiple servers** — add, edit, delete, and switch between Xtream Codes servers
- **Test connection** — validates credentials before saving; shows expiry date and account status
- **Persistent login** — active server is remembered across app restarts

---

## Requirements

### System
| Dependency | Version | Notes |
|---|---|---|
| Python | 3.10+ | f-strings with `|` union types used throughout |
| mpv | any recent | Must be on `$PATH` — install via package manager |

### Python packages
```
PyQt6>=6.4.0
requests>=2.28.0
```

### Optional
| Dependency | Purpose |
|---|---|
| TMDB API key | Fetch high-quality posters for movies and series. Free at [themoviedb.org](https://www.themoviedb.org/settings/api) |

---

## Installation

### 1. Install system dependencies

**Arch / CachyOS / Manjaro**
```bash
sudo pacman -S python mpv
```

**Ubuntu / Debian**
```bash
sudo apt install python3 python3-pip mpv
```

**Fedora**
```bash
sudo dnf install python3 python3-pip mpv
```

### 2. Clone the repository
```bash
git clone <repo-url> iptvshows
cd iptvshows
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

Or inside a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run
```bash
python main.py
```

---

## First Launch

1. A login dialog appears on first run — enter your Xtream Codes server URL, username, and password.
2. Click **Test Connection** to verify credentials.
3. Click **Save & Connect**.
4. Navigate to **Live TV**, **Movies**, or **Series** and click **Sync** to download the playlist.
5. Browsing and search work offline after the first sync.

> Each section (Live TV, Movies, Series) has its own Sync button. You need to sync each one at least once for that content type to appear in search results.

---

## Project Structure

```
iptvshows/
├── main.py                  # Entry point, QApplication setup
├── version.py               # Single source of truth for version number
├── fetch_posters.py         # CLI tool — background TMDB poster fetcher
├── requirements.txt
│
├── api/
│   ├── xtream.py            # Xtream Codes API client (auth, categories, streams, EPG)
│   ├── m3u.py               # M3U playlist download, parser, and DB sync
│   └── tmdb.py              # TMDB poster search (TV shows and movies)
│
├── core/
│   ├── database.py          # SQLite schema, all read/write functions
│   └── player.py            # MPV launcher (subprocess, fire-and-forget)
│
└── ui/
    ├── main_window.py       # App shell, sidebar, navigation, page stack
    ├── styles.py            # Global Qt stylesheet (dark theme)
    ├── widgets.py           # Reusable delegates and list views (MediaListView, ChannelListView)
    ├── workers.py           # Background threads (ApiWorker, ImageWorker, TMDBFetcher, etc.)
    ├── login_dialog.py      # Server add/edit dialog
    ├── live_tv.py           # Live TV page
    ├── movies.py            # Movies page + detail panel
    ├── series.py            # Series page + season/episode viewer
    ├── search.py            # Global search page
    ├── favorites.py         # Favorites + history page
    └── settings.py          # Settings page (servers, MPV, TMDB, cache)
```

---

## Data Storage

All app data is stored under `~/.config/iptvshows/`:

| Path | Contents |
|---|---|
| `data.db` | SQLite database — servers, streams, categories, favorites, history, watch status |
| `images/` | Cached artwork (MD5-named `.jpg` files) |
| `<domain>.m3u` | Last downloaded M3U playlist per server domain |

### Database Tables

| Table | Description |
|---|---|
| `servers` | IPTV server credentials |
| `live_streams` | Cached live channel list |
| `vod_streams` | Cached movie list |
| `series_list` | Cached series list (with embedded episode data for M3U sources) |
| `live_categories` | Live TV category names and IDs |
| `vod_categories` | Movie category names and IDs |
| `series_categories` | Series category names and IDs |
| `favorites` | User-saved favorites (live, vod, series) |
| `history` | Recently played items with timestamps |
| `watch_status` | Per-item watch state: `watched` or `in_progress` |
| `settings` | Key-value app settings (MPV args, TMDB key, etc.) |
| `sync_log` | Timestamps of last sync per content type |

---

## Configuration

All settings are accessible via the **Settings** page inside the app.

| Setting | Description |
|---|---|
| MPV extra arguments | Appended to the MPV command line (e.g. `--hwdec=auto --vo=gpu`) |
| Start in fullscreen | Passes `--fs` to MPV |
| TMDB API key | Used for poster fetching; stored in `settings` table |

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `Esc` | Go back from movie / series detail view |

---

## TMDB Poster Fetch

### Inside the app

1. Get a free API key from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
2. Go to **Settings** → paste the key → **Save Settings**
3. Click **Fetch Series Posters**, **Fetch Movie Posters**, or **Fetch All Posters**
4. Only items without an existing TMDB poster are updated; already-fetched items are skipped

### Background script (recommended for large libraries)

`fetch_posters.py` runs in a terminal while the app stays open. It reads the TMDB key saved in Settings automatically, so you only need to configure it once.

```bash
cd ~/apps/claudecode/iptvshows
```

**Fetch all missing posters (movies + series)**
```bash
python fetch_posters.py
```

**Movies only**
```bash
python fetch_posters.py --movies
```

**Series only**
```bash
python fetch_posters.py --series
```

**One specific title** — substring match, searches both movies and series
```bash
python fetch_posters.py --name "Inception"
python fetch_posters.py --name "Breaking Bad"
python fetch_posters.py --name "hindi"        # all Hindi titles missing a poster
```

**Re-fetch a title even if it already has a poster**
```bash
python fetch_posters.py --name "Inception" --force
python fetch_posters.py --movies --force      # re-fetch all movies
```

**Use a specific TMDB key** (overrides the one saved in Settings)
```bash
python fetch_posters.py --key YOUR_TMDB_KEY
```

**Slow down requests** (if TMDB rate-limits you)
```bash
python fetch_posters.py --delay 0.5
```

**Stop at any time** — press `Ctrl+C`. The script stops cleanly after the current item and nothing is lost. Re-running picks up where it left off.

**After the script finishes**, switch categories in the app to see the new posters — the database is shared and updates appear immediately on the next category load.

#### Incremental behaviour

The script is safe to run repeatedly:
- First run: fetches every movie/series without a poster
- Second run: only processes items added since the last run (or items that weren't found on TMDB)
- Use `--force` to re-fetch everything regardless

#### Progress output

```
Movies: 47985 item(s) to process
  [████████░░░░░░░░░░░░░░░░░░░░] 1842/47985  3%  +1601  Dune: Part Two
```

`+N` is the count of posters actually found and saved (some titles may not be on TMDB).

---

## Architecture Notes

- **M3U as primary data source** — the app downloads the full `m3u_plus` playlist and parses it client-side. Series episodes in M3U format are grouped by show name and season using regex pattern matching.
- **Local-first** — all browsing and search uses the local SQLite DB. The server is only contacted during Sync or when opening a movie/series detail page for extended info.
- **Lazy image loading** — `MediaListView` and `ChannelListView` only fetch images for visible items, using a scroll debounce timer and a shared `QThreadPool`.
- **WAL mode** — SQLite is opened with `PRAGMA journal_mode=WAL` so background image workers can write to the cache without blocking the UI thread.
- **Fire-and-forget playback** — MPV is launched as a detached subprocess (`start_new_session=True`). Position tracking requires manual status updates.

---

## Troubleshooting

**`mpv not found`**
Install mpv and ensure it is on your `$PATH`:
```bash
which mpv   # should print a path
```

**Search returns no results for a content type**
That content type has not been synced yet. Go to the corresponding tab and click **Sync**.

**Qt dbus warnings on startup**
These are silenced automatically via `QT_LOGGING_RULES=qt.qpa.theme.gnome=false`. If you still see them, set the variable in your shell before launching:
```bash
export QT_LOGGING_RULES="qt.qpa.theme.gnome=false"
python main.py
```

**Posters not loading**
- Check your internet connection.
- Clear the image cache in **Settings → Cache → Clear Image Cache**, then re-sync.
- If using TMDB posters, verify your API key is saved correctly.

---

## License

MIT
