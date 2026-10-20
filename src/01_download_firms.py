"""Langkah 1: unduh titik panas NASA FIRMS (VIIRS) untuk bbox Bengkulu 2020-2025.

Butuh MAP_KEY gratis: https://firms.modaps.eosdis.nasa.gov/api/map_key/
    export FIRMS_MAP_KEY="kunci_anda"
    python src/01_download_firms.py

Alternatif tanpa API: unduh manual CSV dari FIRMS Archive Download,
simpan di data/raw/*.csv, lalu lanjut ke langkah 2.
"""
import argparse
import io
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests

from config import (BBOX, DAY_RANGE, END_YEAR, FIRMS_SOURCES, MAP_KEY, RAW_DIR,
                    START_YEAR)

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch_chunk(source, start, days):
    w, s, e, n = BBOX
    url = f"{BASE}/{MAP_KEY}/{source}/{w},{s},{e},{n}/{days}/{start:%Y-%m-%d}"
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200:
                text = r.text.strip()
                if text.startswith("latitude"):
                    return pd.read_csv(io.StringIO(text))
                if "invalid" in text.lower() and "key" in text.lower():
                    sys.exit("MAP_KEY tidak valid. Periksa FIRMS_MAP_KEY.")
                return pd.DataFrame()
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)
    return None


def download_year(year, force=False):
    out = RAW_DIR / f"firms_{year}.csv"
    if out.exists() and not force:
        print(f"[skip] {out.name} sudah ada")
        return
    cur, end = date(year, 1, 1), date(year, 12, 31)
    frames, failed = [], 0
    while cur <= end:
        days = min(DAY_RANGE, (end - cur).days + 1)
        df = None
        for src in FIRMS_SOURCES:
            df = fetch_chunk(src, cur, days)
            if df is not None and len(df):
                break
        if df is None:
            failed += 1
        elif len(df):
            frames.append(df)
        cur += timedelta(days=days)
        time.sleep(0.2)
    if not frames:
        print(f"[warn] {year}: tidak ada data (gagal: {failed} chunk)")
        return
    data = pd.concat(frames, ignore_index=True).drop_duplicates()
    data.to_csv(out, index=False)
    print(f"[ok] {year}: {len(data):,} titik -> {out.name} (chunk gagal: {failed})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="unduh ulang")
    args = ap.parse_args()
    if not MAP_KEY:
        sys.exit("Set dulu: export FIRMS_MAP_KEY='kunci_anda'")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for y in range(START_YEAR, END_YEAR + 1):
        download_year(y, args.force)


if __name__ == "__main__":
    main()
