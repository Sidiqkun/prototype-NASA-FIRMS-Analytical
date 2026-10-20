"""Langkah 3: analisis sebaran titik panas per tipe tutupan lahan.
Menghasilkan tabel CSV, grafik PNG, peta, dan ringkasan.md di folder outputs/.

    python src/03_analyze.py            # data riil (hasil langkah 2)
    python src/03_analyze.py --demo     # data sintetis untuk uji coba
"""
import argparse
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import BOUNDARY_FILE, DEMO_DIR, OUT_DIR, PROC_DIR

MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    src_dir = DEMO_DIR if args.demo else PROC_DIR
    out = OUT_DIR / ("demo" if args.demo else "")
    tab, fig_dir = out / "tables", out / "figures"
    tab.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    f_pts = src_dir / "hotspots_landcover.csv"
    if not f_pts.exists():
        sys.exit(f"{f_pts} tidak ada. Jalankan langkah 2 (atau --demo).")
    df = pd.read_csv(f_pts)
    area_f = src_dir / "landcover_area.csv"
    area = pd.read_csv(area_f) if area_f.exists() else None
    n_years = df["year"].nunique()
    total = len(df)

    # ---- tabel ----
    per_year = df.groupby("year").size().rename("jumlah").reset_index()
    per_month = (df.groupby(["year", "month"]).size().unstack(fill_value=0)
                 .reindex(columns=range(1, 13), fill_value=0))
    per_month.columns = MONTHS
    per_lc = df.groupby("landcover").size().rename("jumlah").reset_index()
    per_lc["persen"] = (per_lc["jumlah"] / total * 100).round(2)
    lc_year = df.groupby(["landcover", "year"]).size().unstack(fill_value=0)
    lc_month = (df.groupby(["landcover", "month"]).size().unstack(fill_value=0)
                .reindex(columns=range(1, 13), fill_value=0))
    lc_month.columns = MONTHS

    if area is not None:
        mean_area = area.groupby("landcover")["area_km2"].mean().rename("luas_km2").reset_index()
        per_lc = per_lc.merge(mean_area, on="landcover", how="left")
        per_lc["persen_luas"] = (per_lc["luas_km2"] / mean_area["luas_km2"].sum() * 100).round(2)
        per_lc["kerapatan_per_km2_per_tahun"] = (per_lc["jumlah"] / per_lc["luas_km2"] / n_years).round(4)
        per_lc["rasio_preferensi"] = (per_lc["persen"] / per_lc["persen_luas"]).round(2)
    per_lc = per_lc.sort_values("jumlah", ascending=False)

    per_year.to_csv(tab / "titik_per_tahun.csv", index=False)
    per_month.to_csv(tab / "titik_per_bulan.csv")
    per_lc.to_csv(tab / "titik_per_tutupan_lahan.csv", index=False)
    lc_year.to_csv(tab / "tutupan_lahan_x_tahun.csv")
    lc_month.to_csv(tab / "tutupan_lahan_x_bulan.csv")

    # ---- grafik ----
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(per_year["year"].astype(str), per_year["jumlah"], color="#d95f02")
    ax.set(title="Jumlah titik panas per tahun", ylabel="Titik panas")
    save(fig, fig_dir / "01_per_tahun.png")

    fig, ax = plt.subplots(figsize=(7, 3.8))
    for y, row in per_month.iterrows():
        ax.plot(MONTHS, row.values, marker="o", ms=3, label=str(y))
    ax.set(title="Pola musiman titik panas", ylabel="Titik panas")
    ax.legend(ncol=3, fontsize=7, frameon=False)
    save(fig, fig_dir / "02_musiman.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    s = per_lc.sort_values("jumlah")
    ax.barh(s["landcover"], s["jumlah"], color="#1b9e77")
    ax.set(title="Titik panas per tipe tutupan lahan", xlabel="Titik panas")
    save(fig, fig_dir / "03_per_tutupan_lahan.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(lc_year.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(lc_year.shape[1]), lc_year.columns.astype(str))
    ax.set_yticks(range(lc_year.shape[0]), lc_year.index)
    for i in range(lc_year.shape[0]):
        for j in range(lc_year.shape[1]):
            ax.text(j, i, lc_year.values[i, j], ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, label="Titik panas")
    ax.set_title("Tutupan lahan x tahun")
    save(fig, fig_dir / "04_heatmap_tutupan_tahun.png")

    if "kerapatan_per_km2_per_tahun" in per_lc:
        fig, axs = plt.subplots(1, 2, figsize=(10, 4))
        s = per_lc.dropna(subset=["kerapatan_per_km2_per_tahun"]).sort_values("kerapatan_per_km2_per_tahun")
        axs[0].barh(s["landcover"], s["kerapatan_per_km2_per_tahun"], color="#7570b3")
        axs[0].set(title="Kerapatan (titik/km²/tahun)")
        axs[1].barh(s["landcover"], s["rasio_preferensi"], color="#e7298a")
        axs[1].axvline(1, color="k", lw=0.8, ls="--")
        axs[1].set(title="Rasio preferensi (>1 = lebih rawan dari proporsi luasnya)")
        axs[1].set_yticklabels([])
        save(fig, fig_dir / "05_kerapatan_preferensi.png")

    # peta
    fig, ax = plt.subplots(figsize=(5.5, 7))
    if BOUNDARY_FILE.exists() and not args.demo:
        import geopandas as gpd
        gpd.read_file(BOUNDARY_FILE).boundary.plot(ax=ax, color="k", lw=0.8)
    hb = ax.hexbin(df.longitude, df.latitude, gridsize=45, cmap="inferno_r", mincnt=1)
    fig.colorbar(hb, ax=ax, label="Titik panas per sel", shrink=0.7)
    ax.set(title="Kerapatan titik panas (hexbin)", xlabel="Bujur", ylabel="Lintang", aspect="equal")
    save(fig, fig_dir / "06_peta_kerapatan.png")

    fig, ax = plt.subplots(figsize=(6.5, 7))
    if BOUNDARY_FILE.exists() and not args.demo:
        import geopandas as gpd
        gpd.read_file(BOUNDARY_FILE).boundary.plot(ax=ax, color="k", lw=0.8)
    for name, g in df.groupby("landcover"):
        ax.scatter(g.longitude, g.latitude, s=2, alpha=0.5, label=name)
    ax.legend(markerscale=4, fontsize=7, frameon=False)
    ax.set(title="Sebaran titik panas menurut tutupan lahan", aspect="equal")
    save(fig, fig_dir / "07_peta_tutupan.png")

    # ---- ringkasan ----
    top = per_lc.iloc[0]
    peak_month = per_month.sum().idxmax()
    peak_year = per_year.loc[per_year["jumlah"].idxmax()]
    lines = [
        "# Ringkasan Otomatis" + (" (DATA DEMO SINTETIS)" if args.demo else ""),
        "",
        f"- Total titik panas: **{total:,}** ({n_years} tahun)",
        f"- Tahun tertinggi: **{int(peak_year['year'])}** ({int(peak_year['jumlah']):,} titik)",
        f"- Bulan puncak (akumulasi seluruh tahun): **{peak_month}**",
        f"- Tutupan lahan dengan titik terbanyak: **{top['landcover']}** ({top['persen']}%)",
    ]
    if "rasio_preferensi" in per_lc:
        r = per_lc.dropna(subset=["rasio_preferensi"]).sort_values("rasio_preferensi", ascending=False).iloc[0]
        lines.append(f"- Paling rawan terhadap luasnya: **{r['landcover']}** (rasio preferensi {r['rasio_preferensi']})")
    lines += ["", "Tabel: `tables/`  |  Grafik & peta: `figures/`"]
    (out / "ringkasan.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[ok] hasil di: {out}")


if __name__ == "__main__":
    main()
