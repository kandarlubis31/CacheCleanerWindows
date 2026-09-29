"""
Dev Artifacts Cleaner Core
==========================
Logic pembersihan build artifacts (node_modules, .next, dist, build, dll)
yang aman: age-based, dry-run first, respek flag .no-clean.

Dipake sama: Scrubo (tab Dev Cleaner), maintenance.ps1 (versi PowerShell)

Author: KandarLubis
License: MIT
"""

import os
import shutil
from datetime import datetime
from dataclasses import dataclass, field

# ============================================
#  KONFIGURASI DEFAULT
# ============================================

# Folder artifact yang aman dihapus (regenerate otomatis)
ARTIFACT_PATTERNS = [
    'node_modules',
    '.next',
    'dist',
    'build',
    '__pycache__',
    '.turbo',
    '.parcel-cache',
]

# File/folder yang GA BOLEH disentuh di dalam artifact (double guard)
PROTECTED_NAMES = {'.git', '.env', '.env.local', 'package-lock.json',
                   'pnpm-lock.yaml', 'yarn.lock', 'requirements.txt'}

# ============================================
#  CONFIG (portable — buat semua PC)
# ============================================

# Nama folder project umum yang discan otomatis di lokasi standar
COMMON_PROJECT_DIRS = ['Projects', 'Project', 'projects', 'dev', 'code',
                       'src', 'workspace', 'repos']
COMMON_BASE_DIRS = ['Desktop', 'Documents']

CONFIG_FILENAME = 'dev_cleaner.json'


def _config_paths():
    """Lokasi config yang dicari (urutan prioritas)."""
    import sys
    paths = []
    # 1. Sebelah file module ini (portable mode) — SKIP kalau frozen .exe,
    #    karena lokasi itu = temp folder PyInstaller yang ke-wipe saat exit
    if not getattr(sys, 'frozen', False):
        try:
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      CONFIG_FILENAME))
        except NameError:
            pass
    # 2. %APPDATA%\Scrubo\dev_cleaner.json (installed exe & fallback)
    appdata = os.environ.get('APPDATA')
    if appdata:
        paths.append(os.path.join(appdata, 'Scrubo', CONFIG_FILENAME))
    return paths


def load_config() -> dict:
    """Load config dari lokasi pertama yang ketemu. Return {} kalau ga ada."""
    for p in _config_paths():
        try:
            if os.path.isfile(p):
                import json
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (OSError, ValueError):
            continue
    return {}


def save_config(cfg: dict) -> str:
    """Simpan config ke lokasi pertama yang bisa ditulis. Return path."""
    import json
    for p in _config_paths():
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            return p
        except OSError:
            continue
    return ''


def _auto_discover_roots() -> list:
    """
    Auto-discover lokasi project yang masuk akal di PC apapun:
      - folder umum di home (Desktop/Documents/Projects/dll) yang ada isinya
      - subfolder COMMON_PROJECT_DIRS kalau ada
    """
    home = os.path.expanduser('~')
    roots = []

    # 1. Folder common langsung di home
    candidates = COMMON_BASE_DIRS + COMMON_PROJECT_DIRS
    for c in candidates:
        p = os.path.join(home, c)
        if os.path.isdir(p):
            roots.append(p)

    # 2. Subfolder tipe-project di dalam Desktop/Documents
    for base in COMMON_BASE_DIRS:
        basep = os.path.join(home, base)
        if not os.path.isdir(basep):
            continue
        for c in COMMON_PROJECT_DIRS:
            p = os.path.join(basep, c)
            if os.path.isdir(p):
                roots.append(p)

    # dedup, urut
    return sorted(set(roots))


def get_roots() -> list:
    """
    Urutan prioritas roots:
      1. Config file (roots di dev_cleaner.json)
      2. Environment variable DEV_CLEANER_ROOTS (dipisah ';')
      3. Auto-discovery
    Roots yang ga exist di-skip. Return [] kalau benar2 kosong.
    """
    cfg = load_config()
    roots = cfg.get('roots') or []

    if not roots:
        env = os.environ.get('DEV_CLEANER_ROOTS')
        if env:
            roots = [r.strip() for r in env.split(';') if r.strip()]

    if not roots:
        roots = _auto_discover_roots()

    return [r for r in roots if os.path.isdir(r)]


def add_root(path: str) -> list:
    """Tambah root ke config (persist). Return daftar roots terbaru."""
    path = os.path.abspath(path)
    cfg = load_config()
    roots = cfg.get('roots') or []
    if path not in roots:
        roots.append(path)
    cfg['roots'] = roots
    cfg.setdefault('age_days', 30)
    save_config(cfg)
    return roots


def remove_root(path: str) -> list:
    """Hapus root dari config. Return daftar roots terbaru."""
    cfg = load_config()
    roots = [r for r in (cfg.get('roots') or [])
             if os.path.abspath(r) != os.path.abspath(path)]
    cfg['roots'] = roots
    save_config(cfg)
    return roots


# ============================================
#  DATA CLASSES
# ============================================

@dataclass
class Artifact:
    """Satu folder artifact yang kedetect."""
    path: str
    size_bytes: int
    age_days: int
    reason_skip: str = ''     # kosong = boleh dihapus

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def is_cleanable(self) -> bool:
        return self.reason_skip == ''

    @property
    def project_name(self) -> str:
        """Nama project induk (folder pertama di bawah root)."""
        return os.path.basename(self.path)


@dataclass
class ScanResult:
    """Hasil scan."""
    artifacts: list = field(default_factory=list)
    scanned_roots: list = field(default_factory=list)
    total_cleanable: int = 0
    total_size_cleanable: int = 0

    def summary(self) -> str:
        lines = []
        lines.append(f"Root discan       : {len(self.scanned_roots)}")
        lines.append(f"Artifact ketemu   : {len(self.artifacts)}")
        lines.append(f"Boleh dibersihkan : {self.total_cleanable} "
                     f"({self.total_size_cleanable / (1024*1024):.0f} MB)")
        return '\n'.join(lines)


# ============================================
#  SAFETY CHECKS
# ============================================

def has_no_clean_flag(directory: str, root: str) -> bool:
    """
    Cek apakah ada file flag .no-clean di project induk.
    Naik dari lokasi artifact sampai root, cek tiap level.
    """
    current = directory
    root_parent = os.path.dirname(root.rstrip('\\/'))
    while current and current != root_parent:
        if os.path.isfile(os.path.join(current, '.no-clean')):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return False


def is_safe_to_delete(path: str) -> tuple:
    """
    Double guard: pastikan path beneran artifact.
    Return (is_safe, alasan).
    """
    name = os.path.basename(path).lower()
    if name not in [p.lower() for p in ARTIFACT_PATTERNS]:
        return False, f"bukan artifact pattern: {name}"

    parent = os.path.basename(os.path.dirname(path)).lower()
    if parent == 'node_modules':
        # nested node_modules - biarkan parent yang handle
        return False, "nested (di dalam node_modules lain)"

    # Jangan hapus kalau artifact mengandung file protected di level atas
    try:
        for entry in os.listdir(path):
            if entry.lower() in {p.lower() for p in PROTECTED_NAMES}:
                # package.json boleh ada di dist build output? Tidak biasa.
                # Kalau ada .git/.env di dalam "artifact" itu red flag.
                if entry.lower() in {'.git', '.env', '.env.local'}:
                    return False, f"berisi {entry} (red flag)"
    except OSError:
        return False, "ga bisa dibaca"

    return True, ''


# ============================================
#  SCANNER
# ============================================

def _dir_size(path: str) -> int:
    total = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path, onerror=lambda e: None):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _dir_age_days(path: str, now: datetime) -> int:
    """Umur berdasarkan LastWriteTime folder (mtime)."""
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return (now - mtime).days
    except OSError:
        return 0


def find_artifacts(roots=None, age_days: int = 30,
                   max_depth: int = 4) -> ScanResult:
    """
    Scan roots buat cari artifacts yang:
      - umurnya >= age_days (ga diakses/berubah)
      - lolos safety check
      - project induknya ga ada flag .no-clean
    """
    if roots is None:
        roots = get_roots()

    now = datetime.now()
    result = ScanResult(scanned_roots=[r for r in roots if os.path.isdir(r)])

    for root in result.scanned_roots:
        root_depth = root.rstrip('\\/').count(os.sep)
        for dirpath, dirnames, _filenames in os.walk(root, onerror=lambda e: None):
            depth = dirpath.rstrip('\\/').count(os.sep) - root_depth
            if depth >= max_depth:
                dirnames[:] = []          # ga turun lebih dalam
                continue

            # Ga perlu masuk .git
            dirnames[:] = [d for d in dirnames if d != '.git']

            for d in list(dirnames):
                if d.lower() in [p.lower() for p in ARTIFACT_PATTERNS]:
                    full = os.path.join(dirpath, d)
                    # skip nested node_modules di dalam node_modules
                    if 'node_modules' in dirpath.lower() and d.lower() == 'node_modules':
                        dirnames.remove(d)
                        continue

                    age = _dir_age_days(full, now)
                    size = _dir_size(full)
                    art = Artifact(path=full, size_bytes=size, age_days=age)

                    # ---- safety chain ----
                    safe, reason = is_safe_to_delete(full)
                    if not safe:
                        art.reason_skip = reason
                    elif age < age_days:
                        art.reason_skip = f"masih aktif ({age} hari < {age_days})"
                    elif has_no_clean_flag(full, root):
                        art.reason_skip = ".no-clean flag"

                    result.artifacts.append(art)

                    if art.is_cleanable:
                        result.total_cleanable += 1
                        result.total_size_cleanable += size

                    # ga perlu turun ke dalam artifact yang udah kedetect
                    if d in dirnames:
                        dirnames.remove(d)

    return result


# ============================================
#  CLEANER
# ============================================

def clean_artifact(path: str, progress_cb=None) -> tuple:
    """
    Hapus satu artifact. Return (success, bytes_freed).
    SELALU jalankan safety check terakhir sebelum hapus.
    """
    safe, reason = is_safe_to_delete(path)
    if not safe:
        if progress_cb:
            progress_cb(f"[SKIP] {path}: {reason}")
        return False, 0

    size = _dir_size(path)
    try:
        shutil.rmtree(path, onerror=lambda fn, p, e: None)
    except OSError:
        pass

    if os.path.exists(path):
        # coba sekali lagi (file locked biasanya berkurang)
        try:
            shutil.rmtree(path, onerror=lambda fn, p, e: None)
        except OSError:
            pass

    freed = size - _dir_size(path) if os.path.exists(path) else size
    success = not os.path.exists(path)

    if progress_cb:
        status = "OK" if success else "PARTIAL"
        progress_cb(f"[{status}] {path}: {freed/(1024*1024):.0f} MB")

    return success, freed


def execute_clean(scan_result: ScanResult, progress_cb=None) -> dict:
    """
    Eksekusi pembersihan dari hasil scan.
    Return stats: {'cleaned': n, 'failed': n, 'bytes_freed': n}
    """
    stats = {'cleaned': 0, 'failed': 0, 'bytes_freed': 0}
    for art in scan_result.artifacts:
        if not art.is_cleanable:
            continue
        ok, freed = clean_artifact(art.path, progress_cb)
        if ok:
            stats['cleaned'] += 1
            stats['bytes_freed'] += freed
        else:
            stats['failed'] += 1
    return stats


# ============================================
#  CLI (buat test manual)
# ============================================

if __name__ == '__main__':
    import sys

    # --add-root PATH : tambah folder ke config (persist)
    if '--add-root' in sys.argv:
        idx = sys.argv.index('--add-root')
        if idx + 1 < len(sys.argv):
            roots = add_root(sys.argv[idx + 1])
            print("Roots sekarang:")
            for r in roots:
                print(f"  {r}")
        sys.exit(0)

    # --remove-root PATH : hapus folder dari config
    if '--remove-root' in sys.argv:
        idx = sys.argv.index('--remove-root')
        if idx + 1 < len(sys.argv):
            roots = remove_root(sys.argv[idx + 1])
            print("Roots sekarang:")
            for r in roots:
                print(f"  {r}")
        sys.exit(0)

    # --roots "P1;P2" : override sekali jalan (ga disimpen)
    roots_override = None
    if '--roots' in sys.argv:
        idx = sys.argv.index('--roots')
        if idx + 1 < len(sys.argv):
            roots_override = [r.strip() for r in sys.argv[idx + 1].split(';') if r.strip()]

    age = 30
    if '--age' in sys.argv:
        idx = sys.argv.index('--age')
        if idx + 1 < len(sys.argv):
            age = int(sys.argv[idx + 1])

    print("=== Dev Artifacts Cleaner ===")
    active_roots = roots_override or get_roots()
    print("Roots yang discan:")
    for r in active_roots:
        print(f"  {r}")
    if not active_roots:
        print("  (kosong! tambah via: --add-root PATH, atau file dev_cleaner.json)")
        sys.exit(0)
    print()

    res = find_artifacts(roots=active_roots, age_days=age)
    print(res.summary())
    print()
    for a in res.artifacts:
        flag = 'DELETE' if a.is_cleanable else f'SKIP ({a.reason_skip})'
        print(f"  [{flag}] {a.path}  ({a.size_mb:.0f} MB, {a.age_days} hari)")

    if '--go' in sys.argv:
        print("\n=== EKSEKUSI ===")
        stats = execute_clean(res, progress_cb=print)
        print(f"\nCleaned: {stats['cleaned']} | Failed: {stats['failed']} | "
              f"Freed: {stats['bytes_freed']/(1024*1024):.0f} MB")
    else:
        print("\n(dry-run aja. Tambah --go buat eksekusi)")
