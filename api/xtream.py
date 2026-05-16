import requests
from typing import Optional, List, Dict, Any


class XtreamAPI:
    def __init__(self, server_url: str, username: str, password: str):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.base_url = f"{self.server_url}/player_api.php"
        self.session = requests.Session()
        self.session.timeout = 20
        self.session.headers.update({
            'User-Agent': 'VLC/3.0.20 LibVLC/3.0.20',
            'Accept': '*/*',
        })
        self.user_info: Dict = {}
        self.server_info: Dict = {}

    def authenticate(self) -> Dict:
        resp = self.session.get(
            self.base_url,
            params={'username': self.username, 'password': self.password}
        )
        if resp.status_code == 461:
            raise ValueError(
                "Server blocked the request (HTTP 461). "
                "The panel rejected this client's User-Agent or IP. "
                "Try a VPN or contact your provider."
            )
        resp.raise_for_status()
        data = resp.json()
        self.user_info = data.get('user_info', {})
        self.server_info = data.get('server_info', {})
        if self.user_info.get('auth') == 0:
            raise ValueError("Authentication failed: invalid credentials")
        return data

    # ── Live TV ─────────────────────────────────────────────────────────────

    def get_live_categories(self) -> List[Dict]:
        return self._call('get_live_categories')

    def get_live_streams(self, category_id: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {'action': 'get_live_streams'}
        if category_id:
            params['category_id'] = category_id
        return self._raw(params)

    def get_short_epg(self, stream_id: str, limit: int = 4) -> Dict:
        return self._call('get_short_epg', stream_id=stream_id, limit=limit)

    def get_epg(self, stream_id: str) -> Dict:
        return self._call('get_simple_data_table', stream_id=stream_id)

    # ── VOD ─────────────────────────────────────────────────────────────────

    def get_vod_categories(self) -> List[Dict]:
        return self._call('get_vod_categories')

    def get_vod_streams(self, category_id: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {'action': 'get_vod_streams'}
        if category_id:
            params['category_id'] = category_id
        return self._raw(params)

    def get_vod_info(self, vod_id: str) -> Dict:
        return self._call('get_vod_info', vod_id=vod_id)

    # ── Series ───────────────────────────────────────────────────────────────

    def get_series_categories(self) -> List[Dict]:
        return self._call('get_series_categories')

    def get_series(self, category_id: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {'action': 'get_series'}
        if category_id:
            params['category_id'] = category_id
        return self._raw(params)

    def get_series_info(self, series_id: str) -> Dict:
        return self._call('get_series_info', series_id=series_id)

    # ── Stream URLs ──────────────────────────────────────────────────────────

    def live_url(self, stream_id: str, ext: str = 'ts') -> str:
        return f"{self.server_url}/live/{self.username}/{self.password}/{stream_id}.{ext}"

    def vod_url(self, vod_id: str, ext: str = 'mp4') -> str:
        return f"{self.server_url}/movie/{self.username}/{self.password}/{vod_id}.{ext}"

    def series_url(self, episode_id: str, ext: str = 'mp4') -> str:
        return f"{self.server_url}/series/{self.username}/{self.password}/{episode_id}.{ext}"

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _call(self, action: str, **kwargs) -> Any:
        params = {
            'action': action,
            'username': self.username,
            'password': self.password,
            **kwargs,
        }
        resp = self.session.get(self.base_url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _raw(self, params: Dict) -> Any:
        params = {**params, 'username': self.username, 'password': self.password}
        resp = self.session.get(self.base_url, params=params)
        resp.raise_for_status()
        return resp.json()
