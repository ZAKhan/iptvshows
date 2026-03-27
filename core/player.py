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
    """Launch mpv with the given stream URL. Fire-and-forget."""
    cmd = [get_mpv()]

    if title:
        cmd.append(f'--force-media-title={title}')

    # Sane defaults for IPTV
    cmd += [
        '--cache=yes',
        '--cache-secs=10',
        '--demuxer-max-bytes=50MiB',
        '--no-input-default-bindings',
        '--input-default-bindings',
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
