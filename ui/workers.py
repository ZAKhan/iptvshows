import os
import hashlib
import requests as req
from PyQt6.QtCore import QThread, QRunnable, QThreadPool, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QPixmapCache, QImage

# Bigger pixmap cache (default ~10MB → 64MB)
QPixmapCache.setCacheLimit(65536)


def _cache_key(url: str, size: tuple | None) -> str:
    if size:
        return f"{url}|{size[0]}x{size[1]}"
    return url


# Shared HTTP session with connection pooling
_HTTP = req.Session()
_HTTP.headers.update({"User-Agent": "iptvshows/1.0"})


# ── API worker ────────────────────────────────────────────────────────────────

_RUNNING_WORKERS: set = set()


class SyncWorker(QThread):
    """Dedicated worker for m3u.sync_all that surfaces stage progress."""
    progress = pyqtSignal(int, int)
    status   = pyqtSignal(str)
    result   = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, url: str, username: str, password: str, parent=None):
        super().__init__(parent)
        self._args = (url, username, password)
        _RUNNING_WORKERS.add(self)
        self.finished.connect(self._on_done)

    def _on_done(self):
        _RUNNING_WORKERS.discard(self)
        self.deleteLater()

    def _cb(self, done, total):
        try: self.progress.emit(done, total)
        except RuntimeError: pass

    def _status_cb(self, text: str):
        try: self.status.emit(text)
        except RuntimeError: pass

    def run(self):
        import logging
        log = logging.getLogger("iptvshows.sync")
        from api import m3u
        try:
            log.info("SyncWorker start url=%s user=%s", self._args[0], self._args[1])
            stats = m3u.sync_all(*self._args, progress_cb=self._cb,
                                 status_cb=self._status_cb)
            log.info("SyncWorker done stats=%s", stats)
            self.result.emit(stats)
        except Exception as exc:
            log.exception("SyncWorker failed")
            self.error.emit(f"{type(exc).__name__}: {exc}")


class ApiWorker(QThread):
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    def __init__(self, fn, *args, parent=None, **kwargs):
        super().__init__(parent)
        self._fn     = fn
        self._args   = args
        self._kwargs = kwargs
        # Pin until finished so overwriting `self._w = ApiWorker(...)` on the
        # caller does not destroy a still-running QThread (which aborts).
        _RUNNING_WORKERS.add(self)
        self.finished.connect(self._on_done)

    def _on_done(self):
        _RUNNING_WORKERS.discard(self)
        self.deleteLater()

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
_tmdb_paused = False


def set_tmdb_paused(paused: bool):
    """Pause/resume TMDBFetcher loops between item fetches."""
    global _tmdb_paused
    _tmdb_paused = bool(paused)


def is_tmdb_paused() -> bool:
    return _tmdb_paused


def shutdown_pools():
    """Set the shutdown flag and drop queued work. Don't block on running tasks —
    the interpreter exits anyway; HTTP requests get killed by socket close."""
    global _shutdown
    _shutdown = True
    try:
        _HTTP.close()       # aborts any in-flight HTTP request
    except Exception:
        pass
    _PREFETCH_POOL.clear()
    _IMAGE_POOL.clear()
    # Brief wait so the most-recent emit can fire without a console error.
    _PREFETCH_POOL.waitForDone(100)
    _IMAGE_POOL.waitForDone(100)
    for w in list(_RUNNING_WORKERS):
        try:
            w.requestInterruption()
            w.quit()
        except Exception:
            pass
    _RUNNING_WORKERS.clear()


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
        # No parent → owned by Python; runnable holds the only reference,
        # so it survives across the QRunnable lifetime regardless of caller GC.
        self.signals = _Signals()
        self.setAutoDelete(True)

    def run(self):
        if not self.url:
            return
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            path = cached_path(self.url)
            if not os.path.exists(path):
                resp = _HTTP.get(self.url, timeout=10)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(resp.content)

            # Decode + scale off the UI thread
            img = QImage(path)
            if img.isNull():
                return
            if self.size:
                img = img.scaled(
                    self.size[0], self.size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            pix = QPixmap.fromImage(img)
            if not pix.isNull():
                try:
                    self.signals.ready.emit(pix, self.tag)
                except RuntimeError:
                    # Signals object was deleted while we were working — drop result.
                    pass
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

class _PrefetchSignals(QObject):
    one_done = pyqtSignal()


class _PrefetchRunnable(QRunnable):
    """Download one image to disk cache silently."""
    def __init__(self, url: str, signals: _PrefetchSignals):
        super().__init__()
        self.url = url
        self.signals = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            if not self.url:
                return
            path = cached_path(self.url)
            if os.path.exists(path):
                return
            os.makedirs(CACHE_DIR, exist_ok=True)
            resp = _HTTP.get(self.url, timeout=10)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
        except Exception:
            pass
        finally:
            try:
                self.signals.one_done.emit()
            except RuntimeError:
                # Owning prefetcher was destroyed mid-run; drop notification.
                pass


class PosterPrefetcher(QThread):
    """
    Submits all poster URLs to the prefetch pool after a sync.
    Emits progress(done, total) and finished() when complete.
    Non-blocking: pool throttles via maxThreadCount; progress driven by signals.
    """
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, urls: list, parent=None):
        super().__init__(parent)
        self._urls  = list({u for u in urls if u and not is_cached(u)})
        self._total = len(self._urls)
        self._done  = 0
        # Parent signals to this QThread so Qt destroys them only when the
        # prefetcher itself is destroyed (after run() and all runnables done).
        self._signals = _PrefetchSignals(self)
        self._signals.one_done.connect(self._on_one)

    def _on_one(self):
        self._done += 1
        if self._done % 20 == 0 or self._done == self._total:
            self.progress.emit(self._done, self._total)
        if self._done >= self._total:
            self.finished.emit()

    def run(self):
        if not self._urls:
            self.finished.emit()
            return
        for url in self._urls:
            if _shutdown:
                break
            _PREFETCH_POOL.start(_PrefetchRunnable(url, self._signals))


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
            if _shutdown or self.isInterruptionRequested():
                break
            # Yield while paused (sync in progress or user pause).
            while _tmdb_paused and not _shutdown and not self.isInterruptionRequested():
                self.msleep(250)
            if _shutdown or self.isInterruptionRequested():
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
