# CacheCleanerWindows (Scrubo) — Project Context

> *Terakhir diupdate: 2026-09-09 — setelah integrasi Dev Artifacts Cleaner*

## Ringkasan

**Scrubo** adalah aplikasi pembersih Windows berbasis Python/Tkinter untuk end-user **dan developer**. Awalnya pembersih cache browser/sistem, sekarang punya 4 tab:

1. **Pembersihan / Cleaning** — cache browser & sistem, proteksi data login
2. **Info Sistem / System Info** — monitoring storage & hardware
3. **Penjadwalan / Scheduler** — pembersihan otomatis terjadwal
4. **Dev Artifacts** *(baru, 2026-09)* — pembersih build cache developer

## Tech Stack

- Python 3.13 (Tkinter, stdlib saja — tanpa dependency wajib)
- psutil (opsional, fallback kalau ga ada)
- PyInstaller 6.x buat build .exe

## Struktur Utama

```
Scrubo.py              # App utama, 4 tab (1.6k+ baris)
dev_cleaner_core.py    # Core logic Dev Artifacts Cleaner — reusable & universal
Scrubo.spec            # PyInstaller build config (WAJIB ikut repo)
Scrubo.ico             # Icon (WAJIB ikut repo)
README.md              # GitHub-ready
CONTEXT.md             # File ini
```

## Modul dev_cleaner_core.py (inti fitur baru)

Logic pembersihan build artifacts yang **aman & universal**:

| Komponen | Fungsi |
|----------|--------|
| `find_artifacts(roots, age_days)` | Scan folder project cari `node_modules`, `.next`, `dist`, `build`, `__pycache__`, `.turbo`, `.parcel-cache` |
| `is_safe_to_delete(path)` | Double-guard: validasi nama artifact + deteksi red flag (`.git`, `.env` di dalamnya) |
| `has_no_clean_flag()` | Respek file flag `.no-clean` di project manapun di atas artifact |
| `execute_clean(scan_result)` | Eksekusi dengan retry untuk file locked, return stats |
| `get_roots()` | Root discovery 3-tier: **config file → env var `DEV_CLEANER_ROOTS` → auto-discovery** |

### Pengaman (jangan pernah dilemahin)

- Age-based: cuma hapus artifact yang ga aktif N hari (default 30)
- Project aktif otomatis ke-skip (mtime check)
- Flag `.no-clean` = protect permanen
- TIDAK PERNAH sentuh: `.git`, `.env*`, source code, `package-lock.json`, database

### Root Discovery (biar universal di PC apapun)

1. Config `dev_cleaner.json` (cari di sebelah module — mode portable/script; ATAU `%APPDATA%\Scrubo\` — mode .exe)
2. Env var `DEV_CLEANER_ROOTS` (dipisah `;`)
3. Auto-discovery: folder umum (`Projects`, `Project`, `dev`, `code`, `workspace`, `repos`...) di `~/Desktop` & `~/Documents`

> ⚠️ Catatan penting: di mode **.exe frozen**, config TIDAK boleh ditulis sebelah module (itu temp folder PyInstaller yang ke-wipe saat exit) — selalu `%APPDATA%\Scrubo\`.

### CLI standalone

```bash
python dev_cleaner_core.py                      # dry-run
python dev_cleaner_core.py --go                 # eksekusi
python dev_cleaner_core.py --add-root "C:\path" # tambah root ke config
python dev_cleaner_core.py --roots "P1;P2"      # override sekali jalan
python dev_cleaner_core.py --age 14             # ubah threshold
```

## Build .exe

```bash
pip install pyinstaller
python -m PyInstaller Scrubo.spec --noconfirm
# hasil: dist/Scrubo.exe (~12.8 MB, onefile, ada icon)
```

`dev_cleaner_core` ke-include otomatis via static analysis import di Scrubo.py (verified di Analysis-00.toc).

## UI: Tab Dev Artifacts

- Spinbox umur threshold (7–180 hari, default 30)
- Tombol: Scan / Bersihkan / + Folder (folder picker → `add_root()`)
- Treeview hasil: path | size | age | status (BOLEH HAPUS / SKIP + alasan)
- Label roots aktif + safety note
- Semua operasi berat di background thread, UI update via `master.after()`

## Status

- ✅ Siap push ke GitHub (`github.com/KandarLubis31`)
- ✅ .gitignore udah bener: `Scrubo.spec` & `Scrubo.ico` di-un-ignore, `dist/` di-ignore
- ⏳ Push dilakukan manual oleh owner (bukan via agent)
