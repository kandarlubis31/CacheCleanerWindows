# Scrubo - Pembersih Sistem & Browser

Aplikasi pembersih Windows untuk end-user **dan developer**.

## Fitur

- **Pembersihan / Cleaning** — cache browser & sistem dengan proteksi data login
- ℹ **Info Sistem / System Info** — monitoring storage & hardware
- **Penjadwalan / Scheduler** — pembersihan otomatis terjadwal
- **Dev Artifacts** — pembersih build cache developer (`node_modules`, `.next`, `dist`, `build`, `__pycache__`) dengan pengaman berlapis:
 - **Age-based**: cuma hapus artifact yang tidak aktif N hari (default 30, bisa diatur 7–180)
 - **Dry-run scan**: lihat dulu daftar + ukuran sebelum hapus, konfirmasi dulu
 - **Project aktif aman**: project yang masih dikerjakan otomatis ke-skip
 - **Flag `.no-clean`**: bikin file kosong `.no-clean` di root project untuk protect permanen
 - **Tidak pernah menyentuh**: `.git`, `.env`, source code, `package-lock.json`, database

## Tech Stack

Python (Tkinter) — tanpa dependency wajib eksternal

## Struktur Utama

```
Scrubo.py              # App utama (4 tab)
dev_cleaner_core.py    # Core logic Dev Artifacts Cleaner (reusable, bisa dipake project lain)
Scrubo.spec            # PyInstaller build config
Scrubo.ico
```

## Menjalankan

```bash
python Scrubo.py
```

## Build .exe

```bash
pip install pyinstaller
pyinstaller Scrubo.spec
# hasil: dist/Scrubo.exe
```

## Dev Artifacts Cleaner sebagai CLI (tanpa GUI)

```bash
python dev_cleaner_core.py          # dry-run
python dev_cleaner_core.py --go     # eksekusi
```

## Integrasi ke Project Lain

```python
import dev_cleaner_core as dvc

result = dvc.find_artifacts(roots=[r'C:\Projects'], age_days=30)
print(result.summary())
# ... tampilkan ke user, konfirmasi ...
stats = dvc.execute_clean(result, progress_cb=print)
```

---

## English

**Scrubo** is a Windows cleaner for end users and developers. It clears browser and system cache while protecting saved logins, reports storage and hardware information, and can run on a schedule.

Its developer mode removes build artifacts (`node_modules`, `.next`, `dist`, `build`, `__pycache__`) with layered safeguards: age-based selection, dry-run previews, and automatic skipping of projects that are still active.

---

## Lisensi

Lihat `LICENSE` di repository ini.
