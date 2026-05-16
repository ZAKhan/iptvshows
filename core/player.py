import shutil
import subprocess
from typing import List


def get_mpv() -> str:
    path = shutil.which('mpv')
    if not path:
        raise FileNotFoundError(
            "mpv not found. Install it with: sudo pacman -S mpv"
        )
    return path


def play(url: str, title: str = "", extra_args: List[str] = None):
    """Launch mpv with IPTV-friendly defaults. Fire-and-forget."""
    cmd = [get_mpv()]

    if title:
        cmd.append(f'--force-media-title={title}')

    # IPTV-tuned defaults — conservative set that works on mpv 0.33+
    cmd += [
        '--cache=yes',
        '--cache-secs=30',
        '--demuxer-max-bytes=200MiB',
        '--demuxer-readahead-secs=60',
        # FFmpeg-side reconnect — widely supported
        '--stream-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=30',
        '--user-agent=VLC/3.0.20 LibVLC/3.0.20',
    ]

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(url)

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
