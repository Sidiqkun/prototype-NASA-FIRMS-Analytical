#!/usr/bin/env bash
# Menjalankan seluruh pipeline. Butuh FIRMS_MAP_KEY dan EE_PROJECT.
set -e
python src/01_download_firms.py
python src/02_extract_landcover.py
python src/03_analyze.py
