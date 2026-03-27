import re
import time
import requests

TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w500"
_SESSION     = requests.Session()
_LAST_CALL   = 0.0
_MIN_INTERVAL = 0.26   # ~40 req/10s safe ceiling


def _throttle():
    global _LAST_CALL
    wait = _MIN_INTERVAL - (time.time() - _LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL = time.time()


def _clean_name(name: str) -> str:
    """
    Strip IPTV-provider noise from a series/movie name before searching TMDB.
    Removes: bracketed tags, parenthesised years/codes, quality markers,
    leading episode/season prefixes, and trailing/double whitespace.
    """
    # Remove anything in square brackets: [KOR], [4K], [SUB], [2019], …
    name = re.sub(r'\[.*?\]', '', name)
    # Remove parenthesised pure-number years or country/lang codes: (2019), (KOR), (EN)
    name = re.sub(r'\(\s*(?:\d{4}|[A-Z]{2,5})\s*\)', '', name, flags=re.IGNORECASE)
    # Remove common quality/source tags (standalone words)
    noise = r'\b(?:4K|UHD|FHD|HD|SDR|HDR|HEVC|H\.?265|H\.?264|BluRay|WEB[-\s]?DL|WEBRip|AMZN|NF|DSNP|HMAX|S\d{1,2}(?:E\d{1,2})?)\b'
    name = re.sub(noise, '', name, flags=re.IGNORECASE)
    # Collapse extra whitespace and strip
    name = re.sub(r'\s{2,}', ' ', name).strip(' :-|.')
    return name


def _candidate_queries(name: str) -> list[str]:
    """Return progressively simpler search queries for a given name."""
    queries = [name]
    cleaned = _clean_name(name)
    if cleaned and cleaned != name:
        queries.append(cleaned)
    # Also try just the first 4 words of the cleaned name as a last resort
    words = cleaned.split()
    if len(words) > 4:
        queries.append(' '.join(words[:4]))
    return list(dict.fromkeys(queries))  # deduplicate while preserving order


def _best_result(results: list, query: str) -> dict | None:
    """Pick the result whose name most closely matches the query."""
    if not results:
        return None
    q = query.lower()
    # Prefer an exact name match first
    for r in results:
        title = (r.get('name') or r.get('title') or '').lower()
        if title == q:
            return r
    # Otherwise return the first result with a poster
    for r in results:
        if r.get('poster_path'):
            return r
    return results[0]


def _search_tv(api_key: str, query: str) -> list:
    _throttle()
    resp = _SESSION.get(
        f"{TMDB_BASE}/search/tv",
        params={"api_key": api_key, "query": query, "page": 1},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _search_movie(api_key: str, query: str) -> list:
    _throttle()
    resp = _SESSION.get(
        f"{TMDB_BASE}/search/movie",
        params={"api_key": api_key, "query": query, "page": 1},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def search_tv_poster(api_key: str, name: str) -> str | None:
    """
    Search TMDB for a TV show by name.
    Returns the full poster URL (w500) or None if not found.
    """
    try:
        for query in _candidate_queries(name):
            results = _search_tv(api_key, query)
            hit = _best_result(results, query)
            if hit and hit.get("poster_path"):
                return TMDB_IMG + hit["poster_path"]
    except Exception:
        pass
    return None


def search_movie_poster(api_key: str, name: str) -> str | None:
    """Search TMDB for a movie. Returns poster URL or None."""
    try:
        for query in _candidate_queries(name):
            results = _search_movie(api_key, query)
            hit = _best_result(results, query)
            if hit and hit.get("poster_path"):
                return TMDB_IMG + hit["poster_path"]
    except Exception:
        pass
    return None


def get_tv_details(api_key: str, name: str) -> dict:
    """
    Search TMDB for a TV show and return rich metadata.
    Returns a dict with poster_url, overview, genres, vote_average,
    year, number_of_seasons, number_of_episodes, status, networks,
    tagline, created_by — or {} on failure.
    """
    try:
        hit = None
        for query in _candidate_queries(name):
            results = _search_tv(api_key, query)
            hit = _best_result(results, query)
            if hit:
                break
        if not hit:
            return {}

        show_id = hit["id"]
        _throttle()
        resp2 = _SESSION.get(
            f"{TMDB_BASE}/tv/{show_id}",
            params={"api_key": api_key},
            timeout=10,
        )
        resp2.raise_for_status()
        d = resp2.json()

        poster = (TMDB_IMG + d["poster_path"]) if d.get("poster_path") else None
        air_date = d.get("first_air_date", "")
        year = air_date[:4] if air_date else ""

        return {
            "poster_url": poster,
            "overview": d.get("overview", ""),
            "genres": [g["name"] for g in d.get("genres", [])],
            "vote_average": round(d["vote_average"], 1) if d.get("vote_average") else None,
            "year": year,
            "number_of_seasons": d.get("number_of_seasons"),
            "number_of_episodes": d.get("number_of_episodes"),
            "status": d.get("status", ""),
            "networks": [n["name"] for n in d.get("networks", [])],
            "tagline": d.get("tagline", ""),
            "created_by": [c["name"] for c in d.get("created_by", [])],
        }
    except Exception:
        return {}


def is_tmdb_poster(url: str) -> bool:
    """Returns True if the URL already points to TMDB."""
    return bool(url) and "image.tmdb.org" in url
