# Analisis Sebaran Titik Panas NASA FIRMS pada Berbagai Tipe Tutupan Lahan di Provinsi Bengkulu (2020–2025)

Prototype pipeline untuk skripsi S1: mengunduh titik panas VIIRS (NASA FIRMS), memotongnya ke batas Bengkulu, memberi atribut tipe tutupan lahan, lalu menghasilkan tabel, grafik, dan peta.

```
FIRMS API ──► 01_download ──► data/raw/*.csv
                                   │
batas + tutupan lahan (GEE/lokal) ─┴► 02_extract ──► data/processed/
                                                         │
                                                  03_analyze ──► outputs/ (tabel, grafik, peta, ringkasan)
```

## Instalasi
```bash
git clone <url-repo-anda> && cd firms-bengkulu
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Coba cepat (tanpa API, data sintetis)
```bash
python src/make_demo_data.py
python src/03_analyze.py --demo      # hasil di outputs/demo/
```
Data demo hanya untuk menguji alur kerja, **bukan data nyata**.

## Pakai data nyata
1. **MAP_KEY FIRMS** (gratis): https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. **Akun Google Earth Engine** + project GCP: `earthengine authenticate`

```bash
export FIRMS_MAP_KEY="kunci_anda"
export EE_PROJECT="id-project-gcp-anda"
./run_all.sh
```
Atau per langkah:
```bash
python src/01_download_firms.py            # unduh per tahun (bisa dilanjutkan, file yang ada dilewati)
python src/02_extract_landcover.py         # batas + tutupan lahan Dynamic World via GEE
python src/03_analyze.py
```

**Tanpa API?** Unduh CSV manual dari FIRMS Archive Download, simpan di `data/raw/`, lalu mulai dari langkah 2.

**Pakai tutupan lahan KLHK/MBMS sendiri** (lebih rinci, mis. sawit/karet/hutan):
```bash
python src/02_extract_landcover.py --local-landcover data/klhk.gpkg --class-col NAMA_KOLOM
```
**Batas wilayah sendiri:** taruh GeoJSON di `data/boundary/bengkulu.geojson` (jika tidak ada, diambil dari FAO GAUL via GEE).

## Keluaran (`outputs/`)
| File | Isi |
|---|---|
| `tables/titik_per_tahun.csv`, `titik_per_bulan.csv` | tren tahunan dan musiman |
| `tables/titik_per_tutupan_lahan.csv` | jumlah, persen, luas, kerapatan/km²/tahun, rasio preferensi |
| `tables/tutupan_lahan_x_tahun.csv`, `_x_bulan.csv` | tabulasi silang |
| `figures/01–07_*.png` | grafik, heatmap, peta hexbin, peta per tutupan lahan |
| `ringkasan.md` | ringkasan otomatis |

**Rasio preferensi** = % titik panas pada suatu kelas ÷ % luas kelas tersebut. Nilai > 1 berarti kelas itu lebih sering terbakar daripada proporsi luasnya.

## Pengaturan
Ubah di `src/config.py`: periode, bbox, sumber FIRMS (VIIRS_SNPP_SP/NRT), ambang kepercayaan, nama kelas.

## Metode singkat
- Data: FIRMS VIIRS S-NPP 375 m; hanya kepercayaan *nominal* dan *high*.
- Pembersihan: hapus duplikat, potong ke batas provinsi.
- Tutupan lahan: Dynamic World (modus tahunan, 10 m) atau data lokal; titik diambil pada koordinat hotspot.
- Analisis: statistik deskriptif, kerapatan per luas kelas, dan rasio preferensi.

## Batasan
- Titik panas ≠ kebakaran pasti; bisa juga pembakaran terkontrol. Tidak ada verifikasi lapangan.
- Hubungan bersifat asosiasi spasial, bukan kausalitas.
- Piksel VIIRS 375 m, sedangkan tutupan lahan diambil pada titik pusatnya.
- Dynamic World hanya 9 kelas umum (tidak memisahkan sawit/karet); untuk itu gunakan data KLHK/MBMS.
- Data tahun terbaru bisa berasal dari NRT dan sedikit berbeda dari data arsip final.
- Kode GEE (langkah 2 mode default) belum diuji di lingkungan pengembangan karena butuh autentikasi; mode lokal dan langkah 3 sudah diuji.

## Lisensi
MIT. Data FIRMS: NASA; Dynamic World: Google/WRI (CC BY 4.0).
