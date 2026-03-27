import os
import re
import hashlib
import requests
from typing import Dict, List, Tuple, Any

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


def download(server_url: str, username: str, password: str,
             timeout: int = 60) -> str:
    from urllib.parse import urlparse
    url = m3u_url(server_url, username, password)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    content = resp.text
    domain = urlparse(server_url).netloc or urlparse(server_url).path
    # strip port if present
    domain = domain.split(':')[0]
    m3u_dir = os.path.expanduser("~/.config/iptvshows")
    os.makedirs(m3u_dir, exist_ok=True)
    with open(os.path.join(m3u_dir, f"{domain}.m3u"), 'w', encoding='utf-8') as f:
        f.write(content)
    return content


def _cat_id(name: str) -> str:
    """Stable category ID derived from name."""
    return hashlib.md5(name.encode()).hexdigest()[:12]


def parse(content: str) -> Tuple[List[Dict], List[Dict], List[Dict],
                                  List[Dict], List[Dict], List[Dict]]:
    """
    Parse M3U+ content.

    Returns:
        live_cats, live_streams,
        vod_cats,  vod_streams,
        ser_cats,  ser_list
    """
    live_streams: List[Dict] = []
    vod_streams:  List[Dict] = []
    ser_list:     List[Dict] = []

    live_cats_map: Dict[str, str] = {}   # name -> id
    vod_cats_map:  Dict[str, str] = {}
    ser_cats_map:  Dict[str, str] = {}

    # For grouping M3U episode entries into shows:
    # key: (show_name, category_id) -> {'cover', 'seasons': {snum: [ep, ...]}}
    _shows: Dict = {}

    lines = content.splitlines()
    total = len(lines)
    i = 0
    num_live = num_vod = num_ser = 0

    while i < total:
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

        # Advance to URL line
        i += 1
        while i < total and not lines[i].strip():
            i += 1
        if i >= total:
            break
        url = lines[i].strip()
        i += 1

        if not url or url.startswith('#'):
            continue

        # Detect type from URL
        lm = _LIVE_RE.search(url)
        mm = _MOVIE_RE.search(url)
        sm = _SERIES_RE.search(url)
        slm = None if (lm or mm or sm) else _SHORT_LIVE_RE.match(url)

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
            vod_streams.append({
                'stream_id':           sid,
                'name':                name,
                'stream_icon':         logo,
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
                ser_list.append({
                    'series_id':   sid,
                    'name':        name,
                    'cover':       logo,
                    'category_id': cid,
                })
                continue

            key = (show_name, cid)
            if key not in _shows:
                _shows[key] = {'cover': logo, 'cover_season': 9999,
                               'cover_ep': 9999, 'seasons': {}}
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

            # Use the logo from the earliest episode (lowest season + ep number)
            s_num = int(season_num) if season_num.isdigit() else 9999
            if logo and (s_num < _shows[key]['cover_season'] or
                         (s_num == _shows[key]['cover_season'] and
                          ep_num < _shows[key]['cover_ep'])):
                _shows[key]['cover'] = logo
                _shows[key]['cover_season'] = s_num
                _shows[key]['cover_ep'] = ep_num

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
            'cover':          show_data['cover'],
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


def sync_all(server_url: str, username: str, password: str) -> Dict[str, Any]:
    """
    Download the M3U file and save all categories + streams to the database.

    Returns a dict with counts:
        {'live': N, 'vod': N, 'series': N,
         'live_icons': [...], 'vod_icons': [...], 'series_icons': [...]}
    """
    import core.database as db

    content = download(server_url, username, password)
    live_cats, live_streams, vod_cats, vod_streams, ser_cats, ser_list = parse(content)

    db.save_live_categories(live_cats)
    db.save_live_streams(live_streams)
    db.save_vod_categories(vod_cats)
    db.save_vod_streams(vod_streams)
    db.save_series_categories(ser_cats)
    db.save_series_list(ser_list)

    return {
        'live':         len(live_streams),
        'vod':          len(vod_streams),
        'series':       len(ser_list),
        'live_icons':   [s.get('stream_icon', '') for s in live_streams],
        'vod_icons':    [s.get('stream_icon', '') for s in vod_streams],
        'series_icons': [s.get('cover', '')        for s in ser_list],
    }
