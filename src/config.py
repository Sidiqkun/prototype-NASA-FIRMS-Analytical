"""Konfigurasi proyek. Ubah di sini jika perlu."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
BOUNDARY_DIR = ROOT / "data" / "boundary"
DEMO_DIR = ROOT / "data" / "demo"
OUT_DIR = ROOT / "outputs"
BOUNDARY_FILE = BOUNDARY_DIR / "bengkulu.geojson"

# Periode analisis
START_YEAR, END_YEAR = 2020, 2025

# Bounding box Bengkulu: (barat, selatan, timur, utara)
BBOX = (101.0, -5.6, 103.8, -2.2)

# Sumber FIRMS (dicoba berurutan; SP = standard/arsip, NRT = near real time)
FIRMS_SOURCES = ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"]
DAY_RANGE = 5  # hari per request API

# Kunci API / proyek (dari environment variable)
MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")
EE_PROJECT = os.getenv("EE_PROJECT")  # ID Google Cloud project untuk GEE

# Filter kepercayaan: VIIRS nominal/high; MODIS >= 30
MODIS_MIN_CONF = 30

# Kelas Dynamic World (GEE) -> nama Indonesia
DW_CLASSES = {
    0: "Badan air",
    1: "Pohon/Hutan",
    2: "Rumput",
    3: "Vegetasi tergenang",
    4: "Lahan pertanian",
    5: "Semak belukar",
    6: "Lahan terbangun",
    7: "Lahan terbuka",
    8: "Salju/Es",
}
NODATA_LABEL = "Tidak ada data"
