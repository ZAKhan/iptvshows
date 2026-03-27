import os
import hashlib
import requests as req
from PyQt6.QtCore import QThread, QRunnable, QThreadPool, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap


# ── API worker ────────────────────────────────────────────────────────────────

class ApiWorker(QThread):
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn     = fn
        self._args   = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:
            self.error.emit(str(exc))


# ── Shared image pool ─────────────────────────────────────────────────────────

CACHE_DIR = os.path.expanduser("~/.config/iptvshows/images")

# 6 threads for on-demand card images
_IMAGE_POOL = QThreadPool()
_IMAGE_POOL.setMaxThreadCount(6)
_IMAGE_POOL.setExpiryTimeout(500)

# Separate lower-priority pool for bulk poster prefetch during sync
_PREFETCH_POOL = QThreadPool()
_PREFETCH_POOL.setMaxThreadCount(4)
_PREFETCH_POOL.setExpiryTimeout(500)


_shutdown = False


def shutdown_pools():
    """Call on app exit to drain pools without hanging."""
    global _shutdown
    _shutdown = True
    _PREFETCH_POOL.clear()
    _IMAGE_POOL.clear()
    _PREFETCH_POOL.waitForDone(1000)
    _IMAGE_POOL.waitForDone(1000)


def cached_path(url: str) -> str:
    """Return the local cache path for a URL (may or may not exist yet)."""
    fname = hashlib.md5(url.encode()).hexdigest() + ".jpg"
    return os.path.join(CACHE_DIR, fname)


def is_cached(url: str) -> bool:
    return bool(url) and os.path.exists(cached_path(url))


# ── On-demand image loader ────────────────────────────────────────────────────

class _Signals(QObject):
    ready = pyqtSignal(QPixmap, object)


class _ImageRunnable(QRunnable):
    def __init__(self, url: str, tag, size: tuple | None, pool_hint: str = "demand"):
        super().__init__()
        self.url  = url
        self.tag  = tag
        self.size = size
        self.signals = _Signals()
        self.setAutoDelete(True)

    def run(self):
        if not self.url:
            return
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            path = cached_path(self.url)
            if not os.path.exists(path):
                resp = req.get(self.url, timeout=10)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(resp.content)

            if self.size:
                pix = QPixmap(path)
                if not pix.isNull():
                    pix = pix.scaled(
                        self.size[0], self.size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                self.signals.ready.emit(pix, self.tag)
        except Exception:
            pass


class ImageWorker:
    """
    On-demand image loader.  Cache hit → instant disk load (no network).
    Cache miss → download via shared pool.

    Usage:
        w = ImageWorker(url, tag=self, size=(w, h))
        w.ready.connect(callback)
        w.start()
    """
    def __init__(self, url: str, tag=None, size: tuple = (120, 180)):
        self._runnable = _ImageRunnable(url, tag, size)
        self.ready = self._runnable.signals.ready

    def start(self):
        _IMAGE_POOL.start(self._runnable)


# ── Bulk poster prefetcher (runs during sync) ─────────────────────────────────

class _PrefetchRunnable(QRunnable):
    """Download one image to disk cache silently. No UI signal needed."""
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.setAutoDelete(True)

    def run(self):
        if not self.url:
            return
        try:
            path = cached_path(self.url)
            if os.path.exists(path):
                return   # already cached
            os.makedirs(CACHE_DIR, exist_ok=True)
            resp = req.get(self.url, timeout=10)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
        except Exception:
            pass


class PosterPrefetcher(QThread):
    """
    Submits all poster URLs to the prefetch pool after a sync.
    Emits progress(done, total) and finished() when complete.
    """
    progress = pyqtSignal(int, int)   # (done, total)
    finished = pyqtSignal()

    def __init__(self, urls: list, parent=None):
        super().__init__(parent)
        # deduplicate, skip empty/already-cached
        self._urls = list({u for u in urls if u and not is_cached(u)})
        self._total = len(self._urls)
        self._done  = 0

    def run(self):
        if not self._urls:
            self.finished.emit()
            return

        # Submit in chunks — avoids allocating 10k runnables at once
        CHUNK = 200
        for i in range(0, len(self._urls), CHUNK):
            if _shutdown:
                break
            chunk = self._urls[i:i + CHUNK]
            for url in chunk:
                if _shutdown:
                    break
                r = _PrefetchRunnable(url)
                _PREFETCH_POOL.start(r)
            if _shutdown:
                break
            # Wait for this chunk to drain before submitting the next
            _PREFETCH_POOL.waitForDone(30_000)   # 30 s max per chunk
            self._done += len(chunk)
            self.progress.emit(self._done, self._total)

        self.finished.emit()


# ── TMDB poster fetcher ───────────────────────────────────────────────────────

class TMDBFetcher(QThread):
    """
    Fetches posters from TMDB for series and/or movies missing them.
    mode: 'tv' | 'movies' | 'all'
    """
    progress       = pyqtSignal(int, int)
    finished       = pyqtSignal()
    poster_updated = pyqtSignal(str, str, str)  # (kind, id, cover_url)

    def __init__(self, api_key: str, mode: str = 'all', parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._mode    = mode

    def run(self):
        import core.database as db
        from api.tmdb import search_tv_poster, search_movie_poster

        rows = []
        if self._mode in ('tv', 'all'):
            rows += [('tv', r) for r in db.get_series_without_tmdb_poster()]
        if self._mode in ('movies', 'all'):
            rows += [('movie', r) for r in db.get_vod_without_tmdb_poster()]

        total = len(rows)
        done  = 0

        for kind, row in rows:
            if _shutdown:
                break
            if kind == 'tv':
                poster = search_tv_poster(self._api_key, row['name'])
                if poster:
                    db.update_series_cover(row['series_id'], poster)
                    self.poster_updated.emit('tv', row['series_id'], poster)
            else:
                poster = search_movie_poster(self._api_key, row['name'])
                if poster:
                    db.update_vod_cover(row['stream_id'], poster)
                    self.poster_updated.emit('movie', row['stream_id'], poster)
            done += 1
            if done % 10 == 0:
                self.progress.emit(done, total)

        self.progress.emit(total, total)
        self.finished.emit()
