"""Verify Croatian region slugs against nepremicnine.net.

Usage:
    python -m backend.scripts.verify_hr_slugs

Issues a HEAD request for each Croatian region slug as it would appear in a
search URL, and prints a summary of any slugs the site doesn't serve.
"""
from __future__ import annotations

import sys

import httpx

from app.scraper.constants import REGIONS

BASE = "https://www.nepremicnine.net/oglasi-prodaja"
PROPERTY = "stanovanje"


def check_slug(client: httpx.Client, slug: str) -> int:
    url = f"{BASE}/{slug}/{PROPERTY}/"
    response = client.head(url, follow_redirects=True, timeout=15.0)
    return response.status_code


def main() -> int:
    failures: list[tuple[str, int | str]] = []
    with httpx.Client(headers={"User-Agent": "FlatsterSlugCheck/1.0"}) as client:
        for slug, label in REGIONS["hr"].items():
            try:
                status_code = check_slug(client, slug)
            except httpx.HTTPError as exc:
                failures.append((slug, f"error: {exc}"))
                print(f"FAIL  {slug:30s} {label!r:35s} {exc}")
                continue
            marker = "OK  " if status_code == 200 else "FAIL"
            print(f"{marker}  {slug:30s} {label!r:35s} {status_code}")
            if status_code != 200:
                failures.append((slug, status_code))
    if failures:
        print(f"\n{len(failures)} slug(s) failed:")
        for slug, info in failures:
            print(f"  - {slug}: {info}")
        return 1
    print(f"\nAll {len(REGIONS['hr'])} Croatian slugs OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
