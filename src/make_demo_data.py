"""Membuat data SINTETIS (bukan data nyata) untuk menguji langkah 3 tanpa API/GEE."""
import numpy as np
import pandas as pd

from config import DEMO_DIR, DW_CLASSES

rng = np.random.default_rng(42)
classes = ["Pohon/Hutan", "Lahan pertanian", "Semak belukar", "Rumput", "Lahan terbangun", "Badan air"]
weights = [0.30, 0.35, 0.20, 0.08, 0.05, 0.02]
area_share = [0.45, 0.30, 0.15, 0.05, 0.03, 0.02]
rows = []
for year, n in zip(range(2020, 2026), [900, 600, 2500, 1800, 800, 1500]):
    month_w = np.array([1, 1, 1, 1, 2, 4, 6, 8, 9, 5, 2, 1], float)
    months = rng.choice(np.arange(1, 13), n, p=month_w / month_w.sum())
    day = rng.integers(1, 28, n)
    lc = rng.choice(classes, n, p=weights)
    rows.append(pd.DataFrame({
        "latitude": rng.uniform(-5.4, -2.4, n), "longitude": rng.uniform(101.2, 103.5, n),
        "acq_date": pd.to_datetime(dict(year=year, month=months, day=day)),
        "confidence": "n", "frp": rng.gamma(2, 3, n), "landcover": lc,
        "year": year, "month": months}))
pd.concat(rows).to_csv(DEMO_DIR / "hotspots_landcover.csv", index=False)
area = [{"year": y, "landcover": c, "area_km2": 19800 * s}
        for y in range(2020, 2026) for c, s in zip(classes, area_share)]
pd.DataFrame(area).to_csv(DEMO_DIR / "landcover_area.csv", index=False)
print("[ok] data demo dibuat di data/demo/")
