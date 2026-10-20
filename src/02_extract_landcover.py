"""Langkah 2: bersihkan titik panas, potong ke batas Bengkulu, lalu beri atribut
tipe tutupan lahan.

Mode default  : Google Earth Engine (Dynamic World, modus tahunan, 10 m).
Mode lokal    : shapefile/GeoJSON/GPKG tutupan lahan sendiri (mis. KLHK/MBMS).

    earthengine authenticate           # sekali saja
    export EE_PROJECT="id-project-gcp"
    python src/02_extract_landcover.py

    # atau pakai tutupan lahan lokal:
    python src/02_extract_landcover.py --local-landcover data/klhk.gpkg --class-col PL2020_ID
"""
import argparse
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from config import (BOUNDARY_FILE, DW_CLASSES, EE_PROJECT, END_YEAR, MODIS_MIN_CONF,
                    NODATA_LABEL, PROC_DIR, RAW_DIR, START_YEAR, BBOX)

CHUNK = 2000  # titik per request GEE


# ---------- pembacaan & pembersihan titik panas ----------
def load_hotspots():
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        sys.exit("Tidak ada CSV di data/raw/. Jalankan langkah 1 atau taruh CSV FIRMS manual.")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True).drop_duplicates()
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    df = df[(df.acq_date.dt.year >= START_YEAR) & (df.acq_date.dt.year <= END_YEAR)]

    # filter kepercayaan
    if "confidence" in df.columns:
        if pd.api.types.is_numeric_dtype(df["confidence"]):  # MODIS: 0-100
            df = df[df["confidence"] >= MODIS_MIN_CONF]
        else:                                                # VIIRS: l / n / h
            c = df["confidence"].astype(str).str.lower().str[0]
            df = df[c.isin(["n", "h"])]
    return df.reset_index(drop=True)


def get_boundary():
    if BOUNDARY_FILE.exists():
        return gpd.read_file(BOUNDARY_FILE).to_crs(4326)
    import ee
    init_ee()
    fc = (ee.FeatureCollection("FAO/GAUL/2015/level1")
          .filter(ee.Filter.eq("ADM0_NAME", "Indonesia"))
          .filter(ee.Filter.eq("ADM1_NAME", "Bengkulu")))
    gj = fc.getInfo()
    if not gj["features"]:
        sys.exit("Batas Bengkulu tidak ditemukan di GAUL. Taruh GeoJSON sendiri di data/boundary/bengkulu.geojson")
    gdf = gpd.GeoDataFrame.from_features(gj["features"], crs=4326)[["geometry"]]
    BOUNDARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(BOUNDARY_FILE, driver="GeoJSON")
    print(f"[ok] batas disimpan: {BOUNDARY_FILE}")
    return gdf


def clip_to_boundary(df, boundary):
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=4326)
    union = boundary.geometry.union_all() if hasattr(boundary.geometry, "union_all") else boundary.unary_union
    pts = pts[pts.within(union)].copy()
    return pts.reset_index(drop=True)


# ---------- Google Earth Engine ----------
def init_ee():
    import ee
    try:
        ee.Initialize(project=EE_PROJECT) if EE_PROJECT else ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=EE_PROJECT) if EE_PROJECT else ee.Initialize()


def dw_image(year, region):
    import ee
    return (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
            .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
            .filterBounds(region).select("label").mode().rename("lc"))


def sample_gee(pts, boundary):
    import ee
    init_ee()
    region = ee.Geometry.Rectangle(list(BBOX))
    pts = pts.copy()
    pts["lc_code"] = np.nan
    area_rows = []
    bgeom = ee.Geometry(boundary.geometry.union_all().__geo_interface__) \
        if hasattr(boundary.geometry, "union_all") else ee.Geometry(boundary.unary_union.__geo_interface__)

    for year in range(START_YEAR, END_YEAR + 1):
        img = dw_image(year, region)
        sub = pts[pts.acq_date.dt.year == year]
        print(f"[gee] {year}: {len(sub):,} titik")
        for i in range(0, len(sub), CHUNK):
            part = sub.iloc[i:i + CHUNK]
            feats = [ee.Feature(ee.Geometry.Point([float(x), float(y)]), {"i": int(idx)})
                     for idx, x, y in zip(part.index, part.longitude, part.latitude)]
            out = img.reduceRegions(ee.FeatureCollection(feats),
                                    ee.Reducer.first().setOutputs(["lc"]),
                                    scale=10, tileScale=4).getInfo()
            for f in out["features"]:
                p = f["properties"]
                if p.get("lc") is not None:
                    pts.at[p["i"], "lc_code"] = p["lc"]
        # luas per kelas (km2)
        res = (ee.Image.pixelArea().divide(1e6).addBands(img)
               .reduceRegion(ee.Reducer.sum().group(groupField=1, groupName="lc"),
                             bgeom, scale=100, maxPixels=1e10, tileScale=4).getInfo())
        for g in res["groups"]:
            area_rows.append({"year": year, "landcover": DW_CLASSES.get(int(g["lc"]), str(g["lc"])),
                              "area_km2": g["sum"]})
    pts["landcover"] = pts["lc_code"].map(DW_CLASSES).fillna(NODATA_LABEL)
    return pts, pd.DataFrame(area_rows)


# ---------- tutupan lahan lokal ----------
def sample_local(pts, path, class_col):
    lc = gpd.read_file(path).to_crs(4326)
    if class_col not in lc.columns:
        sys.exit(f"Kolom '{class_col}' tidak ada. Kolom tersedia: {list(lc.columns)}")
    joined = gpd.sjoin(pts, lc[[class_col, "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    pts = pts.copy()
    pts["landcover"] = joined[class_col].astype(object).where(joined[class_col].notna(), NODATA_LABEL).astype(str)
    pts["lc_code"] = np.nan
    area = lc.to_crs(6933)
    area["area_km2"] = area.geometry.area / 1e6
    tbl = area.groupby(class_col)["area_km2"].sum().reset_index().rename(columns={class_col: "landcover"})
    tbl["landcover"] = tbl["landcover"].astype(str)
    rows = [tbl.assign(year=y) for y in range(START_YEAR, END_YEAR + 1)]
    return pts, pd.concat(rows, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-landcover", help="path file tutupan lahan lokal")
    ap.add_argument("--class-col", help="nama kolom kelas pada file lokal")
    args = ap.parse_args()

    df = load_hotspots()
    print(f"[info] titik panas terbaca (setelah filter kepercayaan): {len(df):,}")
    boundary = get_boundary()
    pts = clip_to_boundary(df, boundary)
    print(f"[info] di dalam batas Bengkulu: {len(pts):,}")
    if pts.empty:
        sys.exit("Tidak ada titik di dalam batas.")

    if args.local_landcover:
        if not args.class_col:
            sys.exit("Isi --class-col untuk mode lokal.")
        pts, area = sample_local(pts, args.local_landcover, args.class_col)
    else:
        pts, area = sample_gee(pts, boundary)

    cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "confidence", "frp",
                        "daynight", "satellite", "lc_code", "landcover"] if c in pts.columns]
    out = pd.DataFrame(pts[cols])
    out["year"] = out["acq_date"].dt.year
    out["month"] = out["acq_date"].dt.month
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(PROC_DIR / "hotspots_landcover.csv", index=False)
    area.to_csv(PROC_DIR / "landcover_area.csv", index=False)
    print(f"[ok] {len(out):,} titik -> data/processed/hotspots_landcover.csv")
    print("[ok] luas kelas -> data/processed/landcover_area.csv")


if __name__ == "__main__":
    main()
