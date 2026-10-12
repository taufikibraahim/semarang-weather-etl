# Semarang Weather ETL

Pipeline ETL yang mengambil **prakiraan cuaca per jam untuk Semarang** dari
[Open-Meteo](https://open-meteo.com/), menyimpan data mentah, membersihkan dan
memvalidasinya, lalu memuatnya ke **SQLite** secara idempoten. Pipeline
dijadwalkan harian dengan Windows Task Scheduler.

Proyek ini dibuat sebagai latihan data engineering ujung ke ujung: extract,
raw layer, transform dengan validasi, load idempoten, logging, tes otomatis,
dan penjadwalan.

## Daftar isi

- [Alur data](#alur-data)
- [Fitur](#fitur)
- [Struktur proyek](#struktur-proyek)
- [Instalasi](#instalasi)
- [Menjalankan](#menjalankan)
- [Penjadwalan harian](#penjadwalan-harian-windows)
- [Skema database](#skema-database)
- [Keputusan desain](#keputusan-desain)
- [Contoh query](#contoh-query)
- [Pengujian](#pengujian)
- [Keterbatasan](#keterbatasan)
- [Rencana pengembangan](#rencana-pengembangan)

## Alur data

```mermaid
flowchart LR
    A[Open-Meteo API] --> B[extract]
    B --> C[raw layer<br/>Parquet]
    B --> D[transform<br/>clean + validasi]
    D --> E[load<br/>upsert]
    E --> F[(SQLite<br/>hourly_weather)]
```

Versi teks:

```
Open-Meteo API
      |
   extract ------> raw layer (Parquet, data/raw/)
      |
  transform  (timezone, nama kolom + satuan, validasi rentang)
      |
    load ------> SQLite (data/weather.db, tabel hourly_weather)
```

Tiap tahap berupa fungsi terpisah yang menerima input dan mengembalikan hasil,
sehingga mudah diuji dan kelak mudah dipindah menjadi task di orkestrator
seperti Airflow.

## Fitur

- **Extract** dengan cache HTTP (1 jam) dan retry otomatis.
- **Raw layer**: DataFrame asli disimpan sebagai Parquet ber-timestamp, sehingga
  transform bisa dijalankan ulang tanpa memanggil API lagi.
- **Transform** dengan validasi: hujan tidak negatif, probabilitas 0-100,
  tidak ada timestamp ganda.
- **Load idempoten**: primary key `date` + upsert, menjalankan pipeline dua kali
  tidak menggandakan data.
- **Logging** ke terminal dan file berputar (`logs/pipeline.log`), error
  tercatat lengkap dengan traceback.
- **Path absolut** berbasis lokasi proyek, aman dijalankan penjadwal dari folder
  mana pun.
- **Tes otomatis** dengan pytest (transform, load, raw layer).

## Struktur proyek

```
semarang_weather_etl/
├── main.py                     # titik masuk: extract -> raw -> transform -> load
├── pytest.ini
├── requirements.txt
├── run_pipeline.example.bat    # contoh pembungkus untuk Task Scheduler
├── src/
│   └── pipeline/
│       ├── config.py           # konstanta dan path
│       ├── extract.py          # panggil Open-Meteo
│       ├── raw.py              # simpan data mentah (Parquet)
│       ├── transform.py        # bersihkan dan validasi
│       ├── load.py             # upsert ke SQLite
│       └── logging_config.py   # logging ke terminal + file
├── tests/
│   ├── conftest.py             # fixture bersama
│   ├── test_transform.py
│   ├── test_load.py
│   └── test_raw.py
├── data/                       # dibuat otomatis, tidak masuk Git
│   ├── raw/                    # file Parquet mentah
│   ├── cache/                  # cache HTTP
│   └── weather.db              # database SQLite
└── logs/                       # dibuat otomatis, tidak masuk Git
```

## Instalasi

Prasyarat: Python 3.10 atau lebih baru dan Git.

```bash
git clone <URL-REPO-KAMU>
cd semarang_weather_etl

python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

## Menjalankan

Jalankan dari **folder induk proyek**:

```bash
python main.py
```

Hasil:

- file Parquet baru di `data/raw/`
- tabel `hourly_weather` di `data/weather.db` terisi atau diperbarui
- log di `logs/pipeline.log`

Contoh log yang berhasil:

```
... - INFO - Extract: fetching weather data from Open-Meteo
... - INFO - Raw: saved 336 rows to .../data/raw/weather_<timestamp>.parquet
... - INFO - Transform: cleaning DataFrame
... - INFO - Load: saving DataFrame to SQLite
... - INFO - Finish: 336 rows written to .../data/weather.db
```

Exit code bernilai `0` saat sukses dan bukan `0` saat gagal.

## Penjadwalan harian (Windows)

1. Salin `run_pipeline.example.bat` menjadi `run_pipeline.bat`, lalu sesuaikan
   path proyek di dalamnya.
2. Uji dari PowerShell: `.\run_pipeline.bat` lalu cek `$LASTEXITCODE` (harus `0`).
3. Di **Task Scheduler** pilih _Create Task_:
   - **Triggers**: Daily, misalnya 06:00
   - **Actions**: Start a program, arahkan ke `run_pipeline.bat`, isi
     **Start in** dengan folder proyek (tanpa tanda kutip)
   - **Settings**: jalankan segera jika jadwal terlewat; batasi waktu jalan 1 jam
4. Klik kanan tugas, **Run**, lalu pastikan _Last Run Result_ `0x0` dan
   `logs/pipeline.log` terisi.

`run_pipeline.bat` berisi path pribadi dan masuk `.gitignore`.

## Skema database

Tabel `hourly_weather`, satu baris per jam:

| Kolom                    | Tipe                  | Satuan | Keterangan                                |
| ------------------------ | --------------------- | ------ | ----------------------------------------- |
| `date`                   | TEXT, **PRIMARY KEY** | WIB    | waktu lokal, format `YYYY-MM-DD HH:MM:SS` |
| `temperature_c`          | REAL                  | °C     | suhu udara 2 m                            |
| `precip_probability_pct` | REAL                  | %      | peluang presipitasi                       |
| `humidity_pct`           | REAL                  | %      | kelembapan relatif 2 m                    |
| `apparent_temperature_c` | REAL                  | °C     | suhu terasa                               |
| `wind_speed_kmh`         | REAL                  | km/h   | kecepatan angin 10 m                      |
| `rain_mm`                | REAL                  | mm     | jumlah hujan per jam                      |

Satuan mengikuti nilai bawaan Open-Meteo (tidak ada parameter satuan khusus yang
dikirim). Jika parameter satuan di `config.py` diubah, nama kolom dan tabel ini
harus disesuaikan.

Pemetaan nama kolom API ke nama tabel ada di `COLUMN_RENAMES` pada
`src/pipeline/config.py`.

## Keputusan desain

| Keputusan                                                       | Alasan                                                                                        |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Waktu lokal WIB tanpa zona**, disimpan sebagai teks ISO       | proyek satu kota; kunci `date` seragam dan aman di SQLite yang tidak punya tipe datetime asli |
| **Upsert "terbaru menang"** pada `date`                         | data prakiraan berubah antar run; tabel selalu berisi tebakan terbaru dan ukurannya stabil    |
| **Satuan di nama kolom** (`rain_mm`, `humidity_pct`)            | mencegah salah olah, misalnya menjumlahkan persentase                                         |
| **Validasi dengan `raise ValueError`**, bukan `assert`          | `assert` bisa dimatikan dengan opsi optimasi Python                                           |
| **Raw layer = DataFrame sebelum `clean_weather`** dalam Parquet | tipe data (termasuk timezone dan float32) terjaga, bisa diproses ulang tanpa API              |
| **Path absolut** berbasis `BASE_DIR`                            | aman dijalankan Task Scheduler yang folder kerjanya bukan folder proyek                       |
| **Setup cache/koneksi di dalam fungsi**, bukan level modul      | mengimpor modul tidak punya efek samping (penting untuk pytest)                               |
| **SQLite**                                                      | sederhana, tanpa server; `load.py` terpisah sehingga mudah diganti ke PostgreSQL              |
| **Task Scheduler** untuk versi awal                             | cukup untuk satu job; migrasi ke Airflow direncanakan                                         |

### Sifat data

Endpoint `forecast` memberi **prakiraan model**, bukan pengukuran. Nilai untuk
jam yang sama bisa berbeda antar run. Opsi `past_days=7` mengambil beberapa hari
ke belakang, tetapi tetap berasal dari model.

## Contoh query

Buka database dengan DB Browser for SQLite, ekstensi SQLite Viewer di VS Code,
atau Python:

```python
import sqlite3

conn = sqlite3.connect("data/weather.db")
print(conn.execute("SELECT COUNT(*) FROM hourly_weather").fetchone())
```

**Rentang data dan jumlah baris**

```sql
SELECT COUNT(*) AS jumlah_baris,
       MIN(date) AS awal,
       MAX(date) AS akhir
FROM hourly_weather;
```

**Rata-rata, minimum, dan maksimum suhu per hari**

```sql
SELECT substr(date, 1, 10) AS tanggal,
       ROUND(AVG(temperature_c), 1) AS suhu_rata2,
       MIN(temperature_c) AS suhu_min,
       MAX(temperature_c) AS suhu_max
FROM hourly_weather
GROUP BY tanggal
ORDER BY tanggal;
```

**Total hujan per hari** (`rain_mm` dijumlahkan, peluang tidak)

```sql
SELECT substr(date, 1, 10) AS tanggal,
       ROUND(SUM(rain_mm), 1) AS total_hujan_mm
FROM hourly_weather
GROUP BY tanggal
ORDER BY total_hujan_mm DESC;
```

Query analitik lain akan ditambahkan di bagian ini.

## Pengujian

```bash
pytest -v
```

| File                | Yang diuji                                                                      |
| ------------------- | ------------------------------------------------------------------------------- |
| `test_transform.py` | tanggal tanpa zona, kolom di-rename, input tidak berubah, data buruk ditolak    |
| `test_load.py`      | database dan tabel dibuat, idempoten, upsert menimpa nilai lama, tipe `REAL`    |
| `test_raw.py`       | file terbentuk, folder dibuat otomatis, roundtrip data utuh, nama tidak bentrok |

Tes memakai DataFrame buatan dan folder sementara (`tmp_path`); tidak memanggil
API dan tidak menyentuh database asli.

Pengecekan gaya kode:

```bash
flake8 src tests main.py
```

## Keterbatasan

- Komputer harus menyala agar jadwal berjalan.
- SQLite hanya cocok untuk satu penulis.
- Data berupa prakiraan, bukan observasi.
- Folder `data/raw/` tumbuh satu file per run dan belum ada retensi otomatis.
- Penjadwalan khusus Windows.

## Rencana pengembangan

- [ ] Query analitik dan visualisasi
- [ ] Retensi file raw (hapus yang lebih lama dari N hari)
- [ ] GitHub Actions untuk menjalankan tes dan flake8
- [ ] Migrasi orkestrasi ke Airflow (Docker)
- [ ] Migrasi database ke PostgreSQL
