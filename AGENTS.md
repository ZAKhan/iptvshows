# IPTV Player - Claude Code Context

## Overview
IPTV Player is a PyQt6 desktop application for watching IPTV content from Xtream-compatible servers.

## Architecture

```
iptvshows/
├── main.py              # Entry point
├── ui/                  # UI layer
│   ├── main_window.py   # Main window with sidebar navigation
│   ├── live_tv.py       # Live TV view
│   ├── movies.py        # Movies/VOD view
│   ├── series.py        # Series view
│   ├── search.py        # Search view
│   ├── favorites.py     # Favorites view
│   ├── settings.py      # Settings view
│   ├── login_dialog.py   # Server login/edit dialog
│   ├── widgets.py       # Reusable widgets (MediaListView, ChannelListView)
│   ├── poster_widget.py  # Poster display widget
│   ├── image_loader.py   # Image loading utility
│   └── workers.py        # Background workers (ApiWorker, SyncWorker)
├── core/
│   ├── database.py       # SQLite database operations
│   └── player.py         # MPV player wrapper
├── api/
│   ├── xtream.py         # Xtream API client
│   └── m3u.py           # M3U playlist parser
└── fetch_tmdb_posters.py # Standalone TMDB poster fetcher
```

## Database Schema

### series_list
| Column | Type | Description |
|--------|------|-------------|
| series_id | TEXT | Primary key |
| name | TEXT | Series name |
| category_id | TEXT | Category reference |
| cover | TEXT | Poster URL from IPTV server |
| tmdb_poster | TEXT | Poster URL from TMDB |
| rating | TEXT | Rating |
| data | TEXT | Full JSON blob |

### vod_streams
| Column | Type | Description |
|--------|------|-------------|
| stream_id | TEXT | Primary key |
| name | TEXT | Movie name |
| category_id | TEXT | Category reference |
| stream_icon | TEXT | Poster URL from IPTV server |
| tmdb_poster | TEXT | Poster URL from TMDB |
| rating | TEXT | Rating |
| data | TEXT | Full JSON blob |

### Other Tables
- `servers` - IPTV server configurations
- `favorites` - User favorites
- `history` - Watch history
- `settings` - App settings
- `live_streams` - Live TV channels
- `live/vod/series_categories` - Content categories
- `series_progress` - Episode progress
- `watch_status` - Watch status (watched/in_progress)
- `sync_log` - Sync timestamps

## Key Features

### Views
- **Live TV** - Channel list with EPG info
- **Movies** - VOD catalog with categories
- **Series** - Series catalog with seasons/episodes
- **Search** - Search across all content
- **Favorites** - Saved favorites
- **Settings** - Server management, MPV options

### Data Flow
1. **Sync All** - Fetches content from IPTV server via Xtream API
2. **TMDB Fetch** - Downloads posters from TMDB (standalone script)
3. **Display** - Shows posters from local cache

## Poster System

### Fetch Script
```bash
python3 fetch_tmdb_posters.py        # All missing posters
python3 fetch_tmdb_posters.py --force  # Re-fetch all
python3 fetch_tmdb_posters.py --series  # Series only
python3 fetch_tmdb_posters.py --movies  # Movies only
```

### Display Logic
1. Read `tmdb_poster` from database
2. Calculate MD5 hash of URL → filename
3. Check if file exists in `~/.config/iptvshows/images/`
4. If cached → load from disk (fast)
5. If not cached → download and save

### Image Cache
- Location: `~/.config/iptvshows/images/`
- Naming: MD5 hash of URL + `.jpg` extension
- Downloaded by: `fetch_tmdb_posters.py`

## TMDB Poster Fetcher

The `fetch_tmdb_posters.py` script:
1. Reads series/movies from database
2. Searches TMDB for posters
3. Downloads images to local cache
4. Saves TMDB URL to `tmdb_poster` column

### Usage
```bash
# Requires TMDB API key (save in Settings or pass via --key)
python3 fetch_tmdb_posters.py --key YOUR_TMDB_API_KEY
```

## Performance Optimizations

1. **Lazy page loading** - Pages created on first navigation
2. **Debounced search** - 200ms delay to reduce DB queries
3. **Database indexes** - On category_id, name, cover columns
4. **SQLite WAL mode** - Concurrent read/write

## Known Issues / TODOs

- [ ] Add posters to grid view (movie/series lists)
- [ ] HTTPS enforcement (currently warns but allows HTTP)
- [ ] Plaintext passwords in database
- [ ] No error logging infrastructure

## Development Notes

### Adding a New Page
1. Create widget in `ui/`
2. Add to `_page_factories` in `main_window.py`
3. If no API needed, pass `needs_api=False`

### Image Display in Detail Views
```python
from ui.poster_widget import PosterLabel

self._poster = PosterLabel(width, height)
self._poster.load(tmdb_url or cover_url)
```

### Database Functions
- `get_series_cached(category_id)` - Get series with `tmdb_poster`优先
- `get_vod_streams_cached(category_id)` - Get movies with `tmdb_poster`
- `update_series_tmdb_poster(series_id, url)` - Update TMDB URL
- `update_vod_tmdb_poster(stream_id, url)` - Update TMDB URL
