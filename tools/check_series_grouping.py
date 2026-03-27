#!/usr/bin/env python3
"""
Scan the M3U file and report how series entries are grouped.
Shows: matched shows (grouped by episode regex), unmatched flat entries, and stats.
"""
import sys
import os
import re
import hashlib
from collections import defaultdict

M3U_PATH = os.path.expanduser("~/.config/iptvshows/mystb.online.m3u")

_EXTINF_RE  = re.compile(r'#EXTINF:-?\d+((?:[^,"]|"[^"]*")*),(.*)')
_ATTR_RE    = re.compile(r'([\w-]+)="([^"]*)"')
_SERIES_RE  = re.compile(r'/series/[^/]+/[^/]+/(\d+)')
_EP_NUMBERED_RE = re.compile(
    r'^(.*?)\s+[Ss](\d+)(?:\s+[Ee]pisode\s+|\s*[Ee])(\d+)',
    re.IGNORECASE
)
_EP_NAMED_RE = re.compile(r'^(.*?)\s+[Ss](\d+)\s+(.+)$', re.IGNORECASE)
_EP_SEASON_RE = re.compile(r'^(.*?)\s+[Ss](\d+)\s*$', re.IGNORECASE)

def _cat_id(name: str) -> str:
    return hashlib.md5(name.encode()).hexdigest()[:12]

def main():
    print(f"Reading {M3U_PATH} …")
    with open(M3U_PATH, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    total = len(lines)
    i = 0

    grouped   = defaultdict(lambda: defaultdict(list))  # show_name -> season -> [ep_nums]
    flat      = []   # series entries that didn't match episode regex
    no_match  = []   # series entries with no episode pattern

    series_count = 0

    while i < total:
        line = lines[i].strip()
        if not line.startswith('#EXTINF:'):
            i += 1
            continue

        m = _EXTINF_RE.match(line)
        if not m:
            i += 1
            continue

        attrs  = dict(_ATTR_RE.findall(m.group(1)))
        title  = m.group(2).strip()
        name   = attrs.get('tvg-name', '').strip() or title
        group  = attrs.get('group-title', '').strip() or 'Uncategorized'

        i += 1
        while i < total and not lines[i].strip():
            i += 1
        if i >= total:
            break
        url = lines[i].strip()
        i += 1

        if not url or url.startswith('#'):
            continue

        if not _SERIES_RE.search(url):
            continue

        series_count += 1

        if _EP_NUMBERED_RE.match(name):
            m2 = _EP_NUMBERED_RE.match(name)
            show_name  = m2.group(1).strip()
            season_num = int(m2.group(2))
            ep_num     = int(m2.group(3))
            grouped[show_name][season_num].append(ep_num)
        elif _EP_NAMED_RE.match(name):
            m2 = _EP_NAMED_RE.match(name)
            show_name  = m2.group(1).strip()
            season_num = int(m2.group(2))
            grouped[show_name][season_num].append(f"'{m2.group(3).strip()}'")
        elif _EP_SEASON_RE.match(name):
            m2 = _EP_SEASON_RE.match(name)
            show_name  = m2.group(1).strip()
            season_num = int(m2.group(2))
            grouped[show_name][season_num].append('?')
        else:
            flat.append({'name': name, 'group': group})

    # ── Report ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Total series entries in M3U : {series_count:,}")
    print(f"Grouped shows               : {len(grouped):,}")
    print(f"Flat (ungrouped) entries    : {len(flat):,}")
    print(f"{'='*60}\n")

    print("── GROUPED SHOWS (each becomes one card with seasons/episodes) ──")
    for show_name in sorted(grouped):
        seasons = grouped[show_name]
        season_info = ", ".join(
            f"S{s:02d}({len(eps)} eps)"
            for s, eps in sorted(seasons.items())
        )
        print(f"  {show_name}  →  {season_info}")

    print(f"\n── FLAT ENTRIES (no episode pattern matched, stored as-is) ──")
    for entry in sorted(flat, key=lambda x: x['name'])[:100]:
        print(f"  [{entry['group']}]  {entry['name']}")
    if len(flat) > 100:
        print(f"  … and {len(flat)-100} more")

    print(f"\n── SAMPLE UNMATCHED NAMES (check if regex needs expanding) ──")
    samples = [e['name'] for e in flat if not _EP_NAME_RE.match(e['name'])][:30]
    for s in samples:
        print(f"  {s!r}")

if __name__ == '__main__':
    main()
