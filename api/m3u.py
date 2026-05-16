import os
import re
import hashlib
import logging
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Tuple, Any

_log = logging.getLogger("iptvshows.m3u")

# Matches:  #EXTINF:-1 attr1="val1" attr2="val2",Title
# The attr section uses (?:[^,"]|"[^"]*")* to skip over quoted values
# that may contain commas (e.g. tvg-name="Show, Episode").
_EXTINF_RE  = re.compile(r'#EXTINF:-?\d+((?:[^,"]|"[^"]*")*),(.*)')
_ATTR_RE    = re.compile(r'([\w-]+)="([^"]*)"')
# URL patterns to detect stream type
_LIVE_RE       = re.compile(r'/live/[^/]+/[^/]+/(\d+)')
_MOVIE_RE      = re.compile(r'/movie/[^/]+/[^/]+/(\d+)')
_SERIES_RE     = re.compile(r'/series/[^/]+/[^/]+/(\d+)')
# Short Xtream live URL: http://host/user/pass/12345  (no type prefix, no extension)
_SHORT_LIVE_RE = re.compile(r'^https?://[^/]+/[^/]+/[^/]+/(\d+)$')
# Pattern A: "Show Name S01 Episode 1"  or  "Show Name S01E01"
_EP_NUMBERED_RE = re.compile(
    r'^(.*?)\s+[Ss](\d+)(?:\s+[Ee]pisode\s+|\s*[Ee])(\d+)',
    re.IGNORECASE
)
# Pattern B: "Show Name S02 Named Title"  (named episodes, no number)
_EP_NAMED_RE = re.compile(
    r'^(.*?)\s+[Ss](\d+)\s+(.+)$',
    re.IGNORECASE
)
# Pattern C: "Show Name S01"  (season-only label, no title)
_EP_SEASON_RE = re.compile(
    r'^(.*?)\s+[Ss](\d+)\s*$',
    re.IGNORECASE
)


def m3u_url(server_url: str, username: str, password: str) -> str:
    base = server_url.rstrip('/')
    return f"{base}/get.php?username={username}&password={password}&type=m3u_plus&output=ts"


_UA_HEADERS = {
    'User-Agent': 'VLC/3.0.20 LibVLC/3.0.20',
    'Accept': '*/*',
}


def _http_session() -> requests.Session:
    """Session with retry adapter — 3 retries with exponential backoff."""
    s = requests.Session()
    retry_kw = dict(
        total=3, connect=3, read=2,
        backoff_factor=1.5,
        status_forcelist=(500, 502, 503, 504),
        raise_on_status=False,
    )
    try:
        retry = Retry(allowed_methods=frozenset(['GET']), **retry_kw)
    except TypeError:
        # urllib3 < 1.26 uses 'method_whitelist'
        retry = Retry(method_whitelist=frozenset(['GET']), **retry_kw)
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def download(server_url: str, username: str, password: str,
             timeout: Tuple[int, int] = (30, 600), progress_cb=None,
             start_pct: int = 5, end_pct: int = 25) -> str:
    """Resume-safe streaming download.

    - Saves to a temp file first, atomic-renames on success.
    - Retries on transient network errors (urllib3 Retry).
    - timeout = (connect_timeout, read_timeout). Read 10 min for huge lists.
    """
    from urllib.parse import urlparse
    url = m3u_url(server_url, username, password)

    domain = urlparse(server_url).netloc or urlparse(server_url).path
    domain = domain.split(':')[0]
    m3u_dir = os.path.expanduser("~/.config/iptvshows")
    os.makedirs(m3u_dir, exist_ok=True)
    final_path = os.path.join(m3u_dir, f"{domain}.m3u")

    session = _http_session()
    resp = session.get(url, timeout=timeout, headers=_UA_HEADERS, stream=True)
    resp.raise_for_status()

    total = 0
    try:
        total = int(resp.headers.get('Content-Length') or 0)
    except (TypeError, ValueError):
        total = 0

    fd, tmp_path = tempfile.mkstemp(prefix=".m3u-", suffix=".part", dir=m3u_dir)
    got = 0
    span = max(1, end_pct - start_pct)
    last_pct = -1
    try:
        with os.fdopen(fd, "wb") as out:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                out.write(chunk)
                got += len(chunk)
                if progress_cb:
                    if total > 0:
                        pct = start_pct + int(span * got / total)
                    else:
                        pct = min(end_pct, start_pct + (got // (256 * 1024)))
                    pct = min(end_pct, pct)
                    if pct != last_pct:
                        try: progress_cb(pct, 100)
                        except Exception: pass
                        last_pct = pct
        os.replace(tmp_path, final_path)            # atomic — partial files never overwrite
    except Exception:
        try: os.unlink(tmp_path)
        except OSError: pass
        raise

    # Read once from disk (encoded UTF-8). Avoids holding 2 copies in memory.
    with open(final_path, "rb") as f:
        data = f.read()
    return data.decode("utf-8", errors="replace")


def _cat_id(name: str) -> str:
    """Stable category ID derived from name."""
    return hashlib.md5(name.encode()).hexdigest()[:12]


def parse(content: str, progress_cb=None,
          start_pct: int = 25, end_pct: int = 85) -> Tuple[
              List[Dict], List[Dict], List[Dict],
              List[Dict], List[Dict], List[Dict]]:
    """
    Parse M3U+ content. Emits line-level progress in [start_pct..end_pct].
    """
    live_streams: List[Dict] = []
    vod_streams:  List[Dict] = []
    ser_list:     List[Dict] = []

    live_cats_map: Dict[str, str] = {}
    vod_cats_map:  Dict[str, str] = {}
    ser_cats_map:  Dict[str, str] = {}

    _shows: Dict = {}

    lines = content.splitlines()
    total = max(1, len(lines))
    i = 0
    num_live = num_vod = num_ser = 0
    span = max(1, end_pct - start_pct)
    last_pct = -1

    parse_errors = 0
    while i < total:
        if progress_cb and (i & 1023) == 0:
            pct = start_pct + int(span * i / total)
            if pct != last_pct:
                try: progress_cb(min(pct, end_pct), 100)
                except Exception: pass
                last_pct = pct
        try:
            line = lines[i].strip()
            if not line.startswith('#EXTINF:'):
                i += 1
                continue

            m = _EXTINF_RE.match(line)
            if not m:
                i += 1
                continue

            attrs   = dict(_ATTR_RE.findall(m.group(1)))
            title   = m.group(2).strip()
            name    = attrs.get('tvg-name', '').strip() or title
            logo    = attrs.get('tvg-logo', '').strip()
            group   = attrs.get('group-title', '').strip() or 'Uncategorized'
            tvg_id  = attrs.get('tvg-id', '').strip()
            chno    = attrs.get('tvg-chno', '').strip()

            i += 1
            while i < total and not lines[i].strip():
                i += 1
            if i >= total:
                break
            url = lines[i].strip()
            i += 1

            if not url or url.startswith('#'):
                continue
        except Exception as exc:
            parse_errors += 1
            if parse_errors < 5:
                _log.warning("parse error at line %d: %s", i, exc)
            i += 1
            continue

        # Detect type from URL — wrap in try so a single bad entry can't kill the parse.
        try:
            lm = _LIVE_RE.search(url)
            mm = _MOVIE_RE.search(url)
            sm = _SERIES_RE.search(url)
            slm = None if (lm or mm or sm) else _SHORT_LIVE_RE.match(url)
        except Exception as exc:
            parse_errors += 1
            if parse_errors < 5:
                _log.warning("type-detect error: %s", exc)
            continue

        if lm or slm:
            lm = lm or slm
        if lm:
            sid = lm.group(1)
            cid = live_cats_map.setdefault(group, _cat_id(group))
            ext = url.rsplit('.', 1)[-1] if '.' in url.rsplit('/', 1)[-1] else 'ts'
            num_live += 1
            live_streams.append({
                'stream_id':           sid,
                'name':                name,
                'stream_icon':         logo,
                'category_id':         cid,
                'num':                 int(chno) if chno.isdigit() else num_live,
                'epg_channel_id':      tvg_id,
                'container_extension': ext,
            })

        elif mm:
            sid = mm.group(1)
            cid = vod_cats_map.setdefault(group, _cat_id(group))
            ext = url.rsplit('.', 1)[-1] if '.' in url.rsplit('/', 1)[-1] else 'mp4'
            num_vod += 1
            # Drop m3u tvg-logo for VOD — those are wrong posters from server.
            # TMDB fetcher fills the real poster.
            vod_streams.append({
                'stream_id':           sid,
                'name':                name,
                'stream_icon':         '',
                'category_id':         cid,
                'container_extension': ext,
            })

        elif sm:
            sid = sm.group(1)
            cid = ser_cats_map.setdefault(group, _cat_id(group))
            ext = url.rsplit('.', 1)[-1] if '.' in url.rsplit('/', 1)[-1] else 'mkv'
            num_ser += 1

            nm = _EP_NUMBERED_RE.match(name)
            am = _EP_NAMED_RE.match(name) if not nm else None
            sm2 = _EP_SEASON_RE.match(name) if not nm and not am else None

            if nm:
                show_name  = nm.group(1).strip()
                season_num = str(int(nm.group(2)))
                ep_num     = int(nm.group(3))
                ep_title   = f"Episode {ep_num}"
            elif am:
                show_name  = am.group(1).strip()
                season_num = str(int(am.group(2)))
                ep_title   = am.group(3).strip()
                ep_num     = None   # assigned sequentially below
            elif sm2:
                show_name  = sm2.group(1).strip()
                season_num = str(int(sm2.group(2)))
                ep_title   = None
                ep_num     = None
            else:
                # Drop m3u logo — TMDB fetcher fills real cover.
                ser_list.append({
                    'series_id':   sid,
                    'name':        name,
                    'cover':       '',
                    'category_id': cid,
                })
                continue

            key = (show_name, cid)
            if key not in _shows:
                _shows[key] = {'seasons': {}}
            season_eps = _shows[key]['seasons'].setdefault(season_num, [])

            if ep_num is None:
                ep_num = len(season_eps) + 1
            if ep_title is None:
                ep_title = f"Episode {ep_num}"

            season_eps.append({
                'id':                  sid,
                'episode_num':         ep_num,
                'title':               ep_title,
                'container_extension': ext,
                'stream_url':          url,
            })

    if parse_errors:
        _log.warning("parse completed with %d skipped entries", parse_errors)

    # Convert grouped shows into series_list entries with embedded episode data
    for (show_name, cid), show_data in _shows.items():
        series_id = _cat_id(show_name + ':' + cid)
        seasons_sorted = sorted(show_data['seasons'].keys(),
                                key=lambda x: int(x) if x.isdigit() else 0)
        seasons_list = [{'season_number': int(s) if s.isdigit() else 0}
                        for s in seasons_sorted]
        # Sort episodes within each season
        episodes = {
            s: sorted(eps, key=lambda e: e['episode_num'])
            for s, eps in show_data['seasons'].items()
        }
        ser_list.append({
            'series_id':      series_id,
            'name':           show_name,
            'cover':          '',
            'category_id':    cid,
            '_m3u_episodes':  {'seasons': seasons_list, 'episodes': episodes},
        })

    def _build_cats(cats_map: Dict) -> List[Dict]:
        return [{'category_id': cid, 'category_name': name}
                for name, cid in sorted(cats_map.items())]

    return (
        _build_cats(live_cats_map), live_streams,
        _build_cats(vod_cats_map),  vod_streams,
        _build_cats(ser_cats_map),  ser_list,
    )


def sync_all(server_url: str, username: str, password: str,
             progress_cb=None) -> Dict[str, Any]:
    """
    Download the M3U file and save all categories + streams to the database.
    `progress_cb(done, total)` reports continuous 0..100 progress across the
    download (5..25), parse (25..85) and save stages (85..100).
    """
    import core.database as db

    def p(v):
        if progress_cb:
            try: progress_cb(v, 100)
            except Exception: pass

    p(2)
    content = download(server_url, username, password, progress_cb=progress_cb,
                      start_pct=5, end_pct=25)
    live_cats, live_streams, vod_cats, vod_streams, ser_cats, ser_list = parse(
        content, progress_cb=progress_cb, start_pct=25, end_pct=85
    )

    # Each save is wrapped — a failure in one bucket (e.g. one bad row triggers
    # an integrity error) won't take down the entire sync.
    live_diff: Dict[str, int] = {}
    vod_diff: Dict[str, int] = {}
    ser_diff: Dict[str, int] = {}
    try:
        db.save_live_categories(live_cats)
        live_diff = db.save_live_streams(live_streams) or {}
    except Exception:
        _log.exception("save live failed")
    p(90)
    try:
        db.save_vod_categories(vod_cats)
        vod_diff = db.save_vod_streams(vod_streams) or {}
    except Exception:
        _log.exception("save vod failed")
    p(95)
    try:
        db.save_series_categories(ser_cats)
        ser_diff = db.save_series_list(ser_list) or {}
    except Exception:
        _log.exception("save series failed")
    p(99)

    return {
        'live':         len(live_streams),
        'vod':          len(vod_streams),
        'series':       len(ser_list),
        'live_added':   live_diff.get('added', 0),
        'live_removed': live_diff.get('removed', 0),
        'vod_added':    vod_diff.get('added', 0),
        'vod_removed':  vod_diff.get('removed', 0),
        'series_added': ser_diff.get('added', 0),
        'series_removed': ser_diff.get('removed', 0),
        # Only live channels prefetch logos. VOD/series posters come from TMDB.
        'live_icons':   [s.get('stream_icon', '') for s in live_streams],
        'vod_icons':    [],
        'series_icons': [],
    }
