import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, Canvas, Frame
import tkinter.font as tkFont
import subprocess
import os
import shutil
import glob
import threading
import time
import ctypes
import webbrowser
import json
from datetime import datetime, timedelta
import sys
import sqlite3
import winreg
import platform

try:
    import psutil
except ImportError:
    psutil = None  # Fallback handling jika psutil belum diinstall

class ScruboApp:
    """
    Kelas utama aplikasi Scrubo.
    Mengatur GUI, logika pembersihan, dan manajemen state aplikasi.
    """
    
    def __init__(self, master):
        """Inisialisasi aplikasi dan konfigurasi awal."""
        self.master = master
        self.setup_window()
        self.setup_styles()
        self.setup_variables()
        self.load_settings()
        self.browsers_detected = self.detect_browsers()
        self.get_system_info()
        self.setup_ui() 
        self.is_admin = self.check_admin_privileges()
        self.load_previous_stats()
        self.setup_scheduler()

    def setup_window(self):
        """Mengatur properti jendela utama (Judul, Ukuran, Posisi)."""
        self.master.title("Scrubo - Pembersih Sistem / System Cleaner v2.5")
        self.master.geometry("1000x850")
        self.master.resizable(True, True)
        self.master.minsize(950, 800)
        self.master.configure(bg="#f5f7fa")
        
        # Mengatur DPI awareness agar tampilan tajam di layar resolusi tinggi
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        
        # Center window di layar
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.master.geometry(f"{width}x{height}+{x}+{y}")
        
        # Setup icon jika ada
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'scrubo.ico')
                if os.path.exists(icon_path):
                    self.master.iconbitmap(icon_path)
        except Exception:
            pass

    def get_available_font(self, font_list):
        """Mencari font terbaik yang tersedia di sistem pengguna."""
        for font in font_list:
            try:
                test_font = tkFont.Font(family=font)
                return font
            except tk.TclError:
                continue
        return "TkDefaultFont"

    def setup_styles(self):
        """Mengatur tema warna dan gaya widget (CSS-like styling)."""
        self.main_font = self.get_available_font(["Segoe UI", "Fira Code", "Consolas", "Courier New"])
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Palet Warna Modern
        self.bg_color = "#f5f7fa"
        self.card_bg = "#ffffff"
        self.accent_color = "#4285f4"
        self.accent_hover = "#3367d6"
        self.text_color = "#202124"
        self.text_secondary = "#5f6368"
        self.success_color = "#34a853"
        self.warning_color = "#fbbc04"
        self.error_color = "#ea4335"
        
        # Custom styles untuk ttk widgets
        self.style.configure("TProgressbar", 
                            thickness=12, 
                            troughcolor="#e8eaed", 
                            background=self.accent_color, 
                            bordercolor="#dadce0", 
                            lightcolor=self.accent_color, 
                            darkcolor=self.accent_color)
        
        self.style.configure("TCombobox", 
                            fieldbackground="#ffffff",
                            background="#ffffff",
                            foreground=self.text_color,
                            arrowcolor=self.accent_color)
                            
        self.style.configure("TNotebook", 
                            background=self.bg_color,
                            borderwidth=0)
                            
        self.style.configure("TNotebook.Tab", 
                            padding=[12, 8],
                            background=self.card_bg,
                            foreground=self.text_color)

    def setup_variables(self):
        """Mendefinisikan variabel state dan daftar item yang dilindungi."""
        self.cleaning_active = False
        self.stop_cleaning_event = threading.Event()
        self.admin_warning_shown = False
        self.last_cleaned = "Belum Pernah / Never"
        self.space_saved = "0 KB"
        self.total_space_saved = 0
        self.cleaning_stats = {
            'files_deleted': 0,
            'folders_cleaned': 0,
            'errors': 0
        }
        self.settings = {
            'auto_close_browsers': True,
            'deep_clean_mode': False,
            'show_confirmations': True,
            'log_level': 'normal',
            'preserve_login_data': True,
            'clean_browser_history': False,
            'clean_form_data': False,
            'clean_downloads': False,
            'schedule_enabled': False,
            'schedule_time': '00:00',
            'schedule_frequency': 'weekly'
        }
        
        # File penting yang tidak boleh dihapus agar login user tidak logout
        self.common_protected = [
            "cookies", "login data", "web data", "local storage", 
            "session storage", "extension state", "bookmarks", 
            "history", "preferences", "logins.json", "key4.db",
            "cert9.db", "cookies.sqlite", "places.sqlite", "formhistory.sqlite"
        ]
        
        self.chrome_protected = ["Cookies", "Login Data", "Web Data", "Local Storage", "Session Storage", 
                                "Preferences", "Bookmarks", "History", "Extension State"]
        self.firefox_protected = ["cookies.sqlite", "places.sqlite", "formhistory.sqlite", 
                                 "logins.json", "key4.db", "cert9.db", "permissions.sqlite"]
        
        # System information variables
        self.system_info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'cpu': platform.processor(),
            'ram': 'N/A',
            'disk_usage': 'N/A',
            'uptime': 'N/A'
        }
        
        # Scheduler variables
        self.scheduler_thread = None
        self.scheduler_running = False

    def get_system_info(self):
        """Collect detailed system information"""
        try:
            # Get RAM information
            if psutil:
                mem = psutil.virtual_memory()
                self.system_info['ram'] = f"{mem.total / (1024**3):.2f} GB"
                
                # Get disk usage
                disk = psutil.disk_usage('C:\\')
                self.system_info['disk_usage'] = f"{disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB ({disk.percent}%)"
                
                # Get system uptime
                boot_time = psutil.boot_time()
                uptime = time.time() - boot_time
                days = int(uptime // (24 * 3600))
                hours = int((uptime % (24 * 3600)) // 3600)
                self.system_info['uptime'] = f"{days} hari, {hours} jam"
        except Exception as e:
            print(f"Error getting system info: {e}")

    def load_settings(self):
        """Memuat konfigurasi dari file JSON user."""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".scrubo_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
                    if 'last_cleaned' in saved_settings:
                        self.last_cleaned = saved_settings['last_cleaned']
                    if 'total_space_saved' in saved_settings:
                        self.total_space_saved = saved_settings['total_space_saved']
                        self.space_saved = self._format_size(self.total_space_saved)
        except Exception as e:
            print(f"Gagal memuat pengaturan: {e}")

    def save_settings(self):
        """Menyimpan konfigurasi ke file JSON."""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".scrubo_config.json")
            config_data = self.settings.copy()
            config_data['last_cleaned'] = self.last_cleaned
            config_data['total_space_saved'] = self.total_space_saved
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Gagal menyimpan pengaturan: {e}")

    def load_previous_stats(self):
        self.space_saved = self._format_size(self.total_space_saved)

    def detect_browsers(self):
        """Mendeteksi browser apa saja yang terinstall di sistem."""
        detected = {
            'Chrome': False, 'Firefox': False, 'Edge': False,
            'Opera': False, 'Brave': False, 'Vivaldi': False,
            'Internet Explorer': False, 'Safari': False
        }
        
        # Daftar path umum instalasi browser
        paths = {
            'Chrome': [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
            ],
            'Firefox': [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Mozilla Firefox', 'firefox.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Mozilla Firefox', 'firefox.exe')
            ],
            'Edge': [
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe')
            ],
            'Opera': [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'launcher.exe')
            ],
            'Brave': [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
            ],
            'Vivaldi': [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Vivaldi', 'Application', 'vivaldi.exe')
            ],
            'Internet Explorer': [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Internet Explorer', 'iexplore.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Internet Explorer', 'iexplore.exe')
            ],
            'Safari': [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Safari', 'Safari.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Safari', 'Safari.exe')
            ]
        }

        for browser, browser_paths in paths.items():
            for path in browser_paths:
                if os.path.exists(path):
                    detected[browser] = True
                    break
                    
        return detected

    def setup_ui(self):
        """Membangun layout antarmuka pengguna (Grid System)."""
        self.main_frame = tk.Frame(self.master, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create main tab
        self.main_tab = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.main_tab, text="Pembersihan / Cleaning")
        
        # Create system info tab
        self.info_tab = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.info_tab, text="Info Sistem / System Info")
        
        # Create scheduler tab
        self.scheduler_tab = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(self.scheduler_tab, text="Penjadwalan / Scheduler")
        
        # Setup UI for each tab
        self.setup_main_tab_ui()
        self.setup_info_tab_ui()
        self.setup_scheduler_tab_ui()

    def setup_main_tab_ui(self):
        """Setup UI for the main cleaning tab"""
        for i in range(7):
            self.main_tab.grid_rowconfigure(i, weight=0 if i != 4 else 1)
        self.main_tab.grid_columnconfigure(0, weight=1)
        
        self.create_header(self.main_tab)
        self.create_browser_selection(self.main_tab)
        self.create_stats_section(self.main_tab)
        self.create_status_bar(self.main_tab)
        self.create_log_section(self.main_tab)
        self.create_control_buttons(self.main_tab)
        self.create_footer(self.main_tab)

    def setup_info_tab_ui(self):
        """Setup UI for the system information tab"""
        # Title
        title_frame = tk.Frame(self.info_tab, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        title_frame.pack(fill=tk.X, padx=0, pady=(0, 15))
        
        gradient_frame = tk.Frame(title_frame, bg=self.accent_color, height=50)
        gradient_frame.pack(fill=tk.X)
        gradient_frame.pack_propagate(False)
        
        tk.Label(gradient_frame, text="💻 Informasi Sistem / System Information", 
                font=(self.main_font, 16, "bold"), fg="#ffffff", bg=self.accent_color).pack(pady=15)
        
        # System info frame
        info_frame = tk.Frame(self.info_tab, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 15))
        
        # Create a canvas with scrollbar for system info
        canvas = Canvas(info_frame, bg=self.card_bg)
        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.card_bg)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # System info content
        info_data = [
            ("Sistem Operasi / OS", f"{self.system_info['os']} {self.system_info['os_version']}"),
            ("Prosesor / CPU", self.system_info['cpu']),
            ("Memori / RAM", self.system_info['ram']),
            ("Penggunaan Disk C: / C: Usage", self.system_info['disk_usage']),
            ("Waktu Aktif / Uptime", self.system_info['uptime']),
            ("Username", os.environ.get('USERNAME', 'Unknown')),
            ("Komputer / PC Name", os.environ.get('COMPUTERNAME', 'Unknown'))
        ]
        
        for i, (label, value) in enumerate(info_data):
            tk.Label(scrollable_frame, text=f"{label}:", 
                    font=(self.main_font, 10, "bold"), 
                    fg=self.text_color, bg=self.card_bg).grid(row=i, column=0, sticky="w", padx=20, pady=5)
            
            tk.Label(scrollable_frame, text=value, 
                    font=(self.main_font, 10), 
                    fg=self.accent_color, bg=self.card_bg).grid(row=i, column=1, sticky="w", padx=10, pady=5)
        
        # Storage analysis
        storage_frame = tk.Frame(scrollable_frame, bg=self.card_bg)
        storage_frame.grid(row=len(info_data), column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        
        tk.Label(storage_frame, text="Analisis Penyimpanan / Storage Analysis", 
                font=(self.main_font, 12, "bold"), 
                fg=self.text_color, bg=self.card_bg).pack(pady=(0, 10))
        
        # Get disk drives
        drives = []
        if psutil:
            for part in psutil.disk_partitions():
                if 'fixed' in part.opts and part.device:
                    drives.append(part.device)
        
        for drive in drives:
            drive_frame = tk.Frame(storage_frame, bg=self.card_bg)
            drive_frame.pack(fill=tk.X, pady=5)
            
            try:
                usage = psutil.disk_usage(drive)
                used_gb = usage.used / (1024**3)
                total_gb = usage.total / (1024**3)
                percent = usage.percent
                
                tk.Label(drive_frame, text=f"{drive}", 
                        font=(self.main_font, 10, "bold"), 
                        fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 10))
                
                # Create progress bar for disk usage
                disk_progress = ttk.Progressbar(drive_frame, length=200, mode='determinate', value=percent)
                disk_progress.pack(side=tk.LEFT, padx=(0, 10))
                
                tk.Label(drive_frame, text=f"{used_gb:.1f} GB / {total_gb:.1f} GB ({percent}%)", 
                        font=(self.main_font, 10), 
                        fg=self.text_secondary, bg=self.card_bg).pack(side=tk.LEFT)
            except Exception:
                tk.Label(drive_frame, text=f"{drive} - Tidak dapat mengakses", 
                        font=(self.main_font, 10), 
                        fg=self.error_color, bg=self.card_bg).pack(side=tk.LEFT)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_scheduler_tab_ui(self):
        """Setup UI for the scheduler tab"""
        # Title
        title_frame = tk.Frame(self.scheduler_tab, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        title_frame.pack(fill=tk.X, padx=0, pady=(0, 15))
        
        gradient_frame = tk.Frame(title_frame, bg=self.accent_color, height=50)
        gradient_frame.pack(fill=tk.X)
        gradient_frame.pack_propagate(False)
        
        tk.Label(gradient_frame, text="⏰ Penjadwalan Pembersihan / Cleaning Scheduler", 
                font=(self.main_font, 16, "bold"), fg="#ffffff", bg=self.accent_color).pack(pady=15)
        
        # Scheduler options frame
        options_frame = tk.Frame(self.scheduler_tab, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        options_frame.pack(fill=tk.X, padx=0, pady=(0, 15))
        
        # Enable scheduler checkbox
        self.schedule_enabled_var = tk.BooleanVar(value=self.settings.get('schedule_enabled', False))
        schedule_cb = tk.Checkbutton(options_frame, text="Aktifkan Penjadwalan / Enable Scheduler", 
                                    variable=self.schedule_enabled_var, font=(self.main_font, 10),
                                    fg=self.text_color, bg=self.card_bg, selectcolor="#f0f3f8",
                                    command=self.toggle_scheduler)
        schedule_cb.pack(anchor="w", padx=20, pady=15)
        
        # Schedule frequency
        freq_frame = tk.Frame(options_frame, bg=self.card_bg)
        freq_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        tk.Label(freq_frame, text="Frekuensi / Frequency:", 
                font=(self.main_font, 10), fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 10))
        
        self.schedule_freq_var = tk.StringVar(value=self.settings.get('schedule_frequency', 'weekly'))
        freq_combo = ttk.Combobox(freq_frame, textvariable=self.schedule_freq_var,
                                 values=['daily', 'weekly', 'monthly'], 
                                 width=10, state="readonly")
        freq_combo.pack(side=tk.LEFT)
        
        # Schedule time
        time_frame = tk.Frame(options_frame, bg=self.card_bg)
        time_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        tk.Label(time_frame, text="Waktu / Time:", 
                font=(self.main_font, 10), fg=self.text_color, bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 10))
        
        self.schedule_time_var = tk.StringVar(value=self.settings.get('schedule_time', '00:00'))
        time_entry = tk.Entry(time_frame, textvariable=self.schedule_time_var, width=10, 
                             font=(self.main_font, 10))
        time_entry.pack(side=tk.LEFT)
        
        tk.Label(time_frame, text="(Format: HH:MM)", 
                font=(self.main_font, 9), fg=self.text_secondary, bg=self.card_bg).pack(side=tk.LEFT, padx=(5, 0))
        
        # Save button
        save_btn = tk.Button(options_frame, text="Simpan Pengaturan / Save Settings", 
                           command=self.save_scheduler_settings,
                           font=(self.main_font, 10), bg=self.accent_color, fg="#ffffff",
                           activebackground=self.accent_hover, bd=0, relief="flat", 
                           padx=20, pady=8, cursor="hand2")
        save_btn.pack(pady=15)
        
        # Status frame
        status_frame = tk.Frame(self.scheduler_tab, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=0)
        
        tk.Label(status_frame, text="Status Penjadwalan / Scheduler Status", 
                font=(self.main_font, 12, "bold"), 
                fg=self.text_color, bg=self.card_bg).pack(pady=(15, 10))
        
        self.scheduler_status_label = tk.Label(status_frame, text="Non-aktif / Inactive", 
                                             font=(self.main_font, 10), 
                                             fg=self.text_secondary, bg=self.card_bg)
        self.scheduler_status_label.pack(pady=(0, 10))
        
        self.next_run_label = tk.Label(status_frame, text="-", 
                                     font=(self.main_font, 10), 
                                     fg=self.text_secondary, bg=self.card_bg)
        self.next_run_label.pack(pady=(0, 15))
        
        # Update scheduler status
        self.update_scheduler_status()

    def toggle_scheduler(self):
        """Toggle the scheduler on/off"""
        if self.schedule_enabled_var.get():
            self.start_scheduler()
        else:
            self.stop_scheduler()

    def start_scheduler(self):
        """Start the scheduler thread"""
        if self.scheduler_running:
            return
            
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self.scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        self.update_scheduler_status()

    def stop_scheduler(self):
        """Stop the scheduler thread"""
        self.scheduler_running = False
        self.update_scheduler_status()

    def scheduler_worker(self):
        """Worker function for the scheduler thread"""
        while self.scheduler_running:
            try:
                # Parse schedule time
                hour, minute = map(int, self.schedule_time_var.get().split(':'))
                now = datetime.now()
                
                # Calculate next run time based on frequency
                if self.schedule_freq_var.get() == 'daily':
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                elif self.schedule_freq_var.get() == 'weekly':
                    days_ahead = 6 - now.weekday()  # Sunday = 6
                    if days_ahead < 0 or (days_ahead == 0 and now.time() > now.replace(hour=hour, minute=minute).time()):
                        days_ahead += 7
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
                else:  # monthly
                    # Schedule for the 1st of next month
                    if now.month == 12:
                        next_run = now.replace(year=now.year+1, month=1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
                    else:
                        next_run = now.replace(month=now.month+1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
                
                # Update next run label
                def update_label():
                    self.next_run_label.config(text=f"Berikutnya / Next run: {next_run.strftime('%Y-%m-%d %H:%M')}")
                self.master.after(0, update_label)
                
                # Sleep until next run time
                sleep_seconds = (next_run - now).total_seconds()
                if sleep_seconds > 0:
                    # Sleep in chunks to check if scheduler is still running
                    for _ in range(int(sleep_seconds)):
                        if not self.scheduler_running:
                            return
                        time.sleep(1)
                
                # Run scheduled cleanup
                if self.scheduler_running:
                    def run_scheduled_cleanup():
                        # Show a notification
                        self.master.after(0, lambda: messagebox.showinfo(
                            "Pembersihan Terjadwal / Scheduled Cleanup", 
                            "Memulai pembersihan terjadwal...\nStarting scheduled cleanup..."
                        ))
                        
                        # Run cleanup
                        self.run_cleaning_in_thread()
                    
                    self.master.after(0, run_scheduled_cleanup)
                    
            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def update_scheduler_status(self):
        """Update the scheduler status display"""
        if self.scheduler_running:
            self.scheduler_status_label.config(text="Aktif / Active", fg=self.success_color)
        else:
            self.scheduler_status_label.config(text="Non-aktif / Inactive", fg=self.text_secondary)
            self.next_run_label.config(text="-")

    def save_scheduler_settings(self):
        """Save scheduler settings"""
        self.settings['schedule_enabled'] = self.schedule_enabled_var.get()
        self.settings['schedule_frequency'] = self.schedule_freq_var.get()
        self.settings['schedule_time'] = self.schedule_time_var.get()
        self.save_settings()
        
        # Restart scheduler if enabled
        if self.schedule_enabled_var.get():
            self.stop_scheduler()
            self.start_scheduler()
        else:
            self.stop_scheduler()
            
        messagebox.showinfo("Pengaturan / Settings", "Pengaturan penjadwalan berhasil disimpan!")

    def setup_scheduler(self):
        """Initialize scheduler based on saved settings"""
        if self.settings.get('schedule_enabled', False):
            self.schedule_enabled_var.set(True)
            self.schedule_freq_var.set(self.settings.get('schedule_frequency', 'weekly'))
            self.schedule_time_var.set(self.settings.get('schedule_time', '00:00'))
            self.start_scheduler()

    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        gradient_frame = tk.Frame(header_frame, bg=self.accent_color, height=70)
        gradient_frame.pack(fill=tk.X)
        gradient_frame.pack_propagate(False)
        
        tk.Label(gradient_frame, text="🧹 Scrubo - Bersih & Segar", 
                font=(self.main_font, 18, "bold"), fg="#ffffff", bg=self.accent_color).pack(pady=20)
        
        info_frame = tk.Frame(header_frame, bg=self.card_bg)
        info_frame.pack(fill=tk.X, padx=20, pady=15)
        
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get('USERNAME', 'Unknown')
            
        info_data = [
            ("Pengguna / User:", username),
            ("Sistem / System:", os.environ.get('COMPUTERNAME', 'Unknown')),
            ("Status:", "Aman (Login Terlindungi) / Safe Mode"),
            ("Terakhir Dibersihkan / Last Cleaned:", self.last_cleaned),
            ("Total Hemat / Total Saved:", self.space_saved)
        ]
        
        info_grid_frame = tk.Frame(info_frame, bg=self.card_bg)
        info_grid_frame.pack(fill="x")
        info_grid_frame.grid_columnconfigure(0, weight=0)
        info_grid_frame.grid_columnconfigure(1, weight=1)
        
        self.info_labels = {}
        for i, (label_text, value_text) in enumerate(info_data):
            tk.Label(info_grid_frame, text=label_text, 
                    font=(self.main_font, 9, "bold"), 
                    fg=self.text_color, bg=self.card_bg).grid(row=i, column=0, sticky="w", pady=1)
            
            # Key dictionary menggunakan bahasa inggris saja untuk consistency code
            key_map = label_text.split(" / ")[-1].strip(":")
            
            self.info_labels[key_map] = tk.Label(
                info_grid_frame, text=value_text, 
                font=(self.main_font, 9), 
                fg=self.accent_color, bg=self.card_bg)
            self.info_labels[key_map].grid(row=i, column=1, sticky="w", padx=10, pady=1)

    def create_browser_selection(self, parent):
        browser_frame = tk.Frame(parent, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        browser_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        tk.Label(browser_frame, text="🌐 Pilih Browser untuk Dibersihkan / Select Browsers", 
                font=(self.main_font, 12, "bold"), 
                fg=self.text_color, bg=self.card_bg).pack(pady=(15, 10))
        
        checkbox_frame = tk.Frame(browser_frame, bg=self.card_bg)
        checkbox_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.browser_vars = {}
        detected_items = [(k, v) for k, v in self.browsers_detected.items() if v]
        
        if not detected_items:
             tk.Label(checkbox_frame, text="Tidak ada browser yang didukung terdeteksi / No browsers detected.", 
                    font=(self.main_font, 10), fg=self.error_color, bg=self.card_bg).pack()
        else:
            for i, (browser, _) in enumerate(detected_items):
                var = tk.BooleanVar(value=True)
                self.browser_vars[browser] = var
                cb = tk.Checkbutton(
                    checkbox_frame, text=browser, variable=var,
                    font=(self.main_font, 10), fg=self.text_color, bg=self.card_bg,
                    selectcolor="#f0f3f8", activebackground=self.card_bg,
                    activeforeground=self.accent_color
                )
                cb.grid(row=i//3, column=i%3, sticky="w", padx=10, pady=5)

    def create_stats_section(self, parent):
        stats_frame = tk.Frame(parent, bg=self.card_bg, bd=1, relief="solid", highlightbackground="#dadce0")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        # Format: (Label Atas/Bawah, Value, Warna)
        stats = [
            ("File Terhapus\nFiles Deleted", "0", self.accent_color),
            ("Folder Bersih\nFolders Cleaned", "0", self.success_color),
            ("Error / Gagal\nErrors", "0", self.error_color),
            ("Sesi Hemat\nSession Space", "0 KB", "#9c27b0")
        ]
        
        self.stats_labels = {}
        for i, (label_text, initial_value, color) in enumerate(stats):
            stat_col_frame = tk.Frame(stats_frame, bg=self.card_bg)
            stat_col_frame.grid(row=0, column=i, padx=15, pady=15, sticky="nsew")
            
            tk.Label(stat_col_frame, text=f"📊 {label_text}", justify="center",
                    font=(self.main_font, 9), fg=self.text_secondary, bg=self.card_bg).pack()
            
            # Key mapping simplified
            key = label_text.split("\n")[-1].replace(" ", "_").lower()
            
            self.stats_labels[key] = tk.Label(
                stat_col_frame, text=initial_value, 
                font=(self.main_font, 12, "bold"), 
                fg=color, bg=self.card_bg)
            self.stats_labels[key].pack()

    def create_status_bar(self, parent):
        status_bar_frame = tk.Frame(parent, bg=self.card_bg, height=50, bd=1, relief="solid", highlightbackground="#dadce0")
        status_bar_frame.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 15))
        status_bar_frame.grid_propagate(False)
        status_bar_frame.grid_columnconfigure(0, weight=1)
        status_bar_frame.grid_columnconfigure(1, weight=0)
        
        self.status_label = tk.Label(status_bar_frame, text="● Siap / Ready", 
                                    font=(self.main_font, 10, "bold"), 
                                    fg=self.success_color, bg=self.card_bg)
        self.status_label.grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        self.progress_frame = tk.Frame(status_bar_frame, bg=self.card_bg)
        self.progress_frame.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, 
            length=200, mode='determinate', style="TProgressbar")
        self.progress_bar.pack(side="right")
        self.update_progress(0)

    def create_log_section(self, parent):
        log_frame = tk.Frame(parent, bg=self.bg_color)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=0, pady=(0, 15))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_header = tk.Frame(log_frame, bg=self.card_bg, height=40, bd=1, relief="solid", highlightbackground="#dadce0")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        log_header.grid_propagate(False)
        log_header.grid_columnconfigure(0, weight=1)
        
        tk.Label(log_header, text="📋 LOG SISTEM / SYSTEM LOGS", 
                font=(self.main_font, 10, "bold"), 
                fg=self.text_color, bg=self.card_bg).grid(row=0, column=0, padx=15, pady=8, sticky="w")
        
        log_level_frame = tk.Frame(log_header, bg=self.card_bg)
        log_level_frame.grid(row=0, column=1, padx=5, pady=6, sticky="e")
        
        tk.Label(log_level_frame, text="Level:", font=(self.main_font, 8), 
                fg=self.text_secondary, bg=self.card_bg).pack(side="left", padx=(0, 5))
        
        self.log_level_var = tk.StringVar(value=self.settings['log_level'])
        log_level_combo = ttk.Combobox(log_level_frame, textvariable=self.log_level_var,
                                        values=['minimal', 'normal', 'verbose'], 
                                        width=8, state="readonly")
        log_level_combo.pack(side="left", padx=(0, 5))
        log_level_combo.bind('<<ComboboxSelected>>', self.on_log_level_change)
        
        clear_btn = tk.Button(
            log_header, text="Hapus Log / Clear", command=self.clear_logs,
            font=(self.main_font, 9), bg="#f1f3f4", fg=self.text_color,
            activebackground="#e8eaed", bd=0, relief="flat", 
            padx=15, cursor="hand2")
        clear_btn.grid(row=0, column=2, padx=15, pady=6, sticky="e")
        
        log_container = tk.Frame(log_frame, bg="#ffffff", bd=1, relief="solid", highlightbackground="#dadce0")
        log_container.grid(row=1, column=0, sticky="nsew")
        
        self.log_area = scrolledtext.ScrolledText(
            log_container, wrap=tk.WORD, font=(self.main_font, 9),
            bg="#ffffff", fg=self.text_color, insertbackground=self.accent_color,
            bd=0, relief="flat", selectbackground="#e8f0fe", 
            selectforeground=self.accent_color)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state='disabled')

    def create_control_buttons(self, parent):
        button_frame = tk.Frame(parent, bg=self.bg_color)
        button_frame.grid(row=5, column=0, sticky="ew", padx=0, pady=(0, 0))
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Tombol Mulai dengan Teks Bilingual
        self.clean_button = tk.Button(
            button_frame, text="🚀 MULAI PEMBERSIHAN\nSTART CLEANUP", width=25,
            command=self.run_cleaning_in_thread,
            font=(self.main_font, 11, "bold"),
            bg=self.accent_color, fg="#ffffff",
            activebackground=self.accent_hover, activeforeground="#ffffff",
            bd=0, relief="flat", padx=20, pady=8,
            cursor="hand2"
        )
        self.clean_button.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # Tombol Stop
        self.stop_button = tk.Button(
            button_frame, text="⏹️ STOP", width=10,
            command=self.stop_cleaning,
            font=(self.main_font, 10, "bold"),
            bg=self.error_color, fg="#ffffff",
            activebackground="#d33b2c", activeforeground="#ffffff",
            bd=0, relief="flat", padx=10, pady=15, # Padding disesuaikan agar tinggi sama
            cursor="hand2", state='disabled'
        )
        self.stop_button.grid(row=0, column=1, sticky="w", padx=(0, 10))
        
        util_frame = tk.Frame(button_frame, bg=self.bg_color)
        util_frame.grid(row=0, column=2, sticky="e")
        
        settings_btn = tk.Button(
            util_frame, text="⚙️ Pengaturan\nSettings", width=12,
            command=self.show_settings,
            font=(self.main_font, 9),
            bg="#f1f3f4", fg=self.text_color,
            activebackground="#e8eaed", activeforeground=self.text_color,
            bd=0, relief="flat", padx=10, pady=8,
            cursor="hand2"
        )
        settings_btn.grid(row=0, column=0, padx=5)
        
        help_btn = tk.Button(
            util_frame, text="❓ Bantuan\nHelp", width=10,
            command=self.show_help,
            font=(self.main_font, 9),
            bg="#f1f3f4", fg=self.text_color,
            activebackground="#e8eaed", activeforeground=self.text_color,
            bd=0, relief="flat", padx=10, pady=8,
            cursor="hand2"
        )
        help_btn.grid(row=0, column=1, padx=5)

    def create_footer(self, parent):
        footer_frame = tk.Frame(parent, bg=self.card_bg, height=30, bd=1, relief="solid", highlightbackground="#dadce0")
        footer_frame.grid(row=6, column=0, sticky="ew", padx=0, pady=(15, 0))
        footer_frame.grid_propagate(False)
        
        tk.Label(footer_frame, text=f"© {datetime.now().year} Scrubo | v2.5", 
                font=(self.main_font, 8), fg=self.text_secondary, bg=self.card_bg).pack(side=tk.LEFT, padx=15)
        
        github_btn = tk.Label(footer_frame, text="GitHub", 
                            font=(self.main_font, 8, "underline"), 
                            fg=self.accent_color, bg=self.card_bg, cursor="hand2")
        github_btn.pack(side=tk.RIGHT, padx=15)
        github_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/KandarLubis31"))

    def on_log_level_change(self, event=None):
        self.settings['log_level'] = self.log_level_var.get()
        self.save_settings()
        self.log_message(f"Level Log diubah ke: {self.settings['log_level']}", "info")

    def run_cleaning_in_thread(self):
        """Memulai proses pembersihan di thread terpisah agar GUI tidak macet."""
        if self.cleaning_active:
            self.log_message("Pembersihan sedang berjalan / Cleanup running.", "warning")
            return
            
        if self.settings['show_confirmations']:
            if not messagebox.askyesno("Konfirmasi / Confirm", 
                                    "Apakah Anda yakin ingin memulai pembersihan?\n"
                                    "Are you sure you want to start cleaning?\n\n"
                                    "Safe mode ON: Sesi login Anda aman.\n"
                                    "Login sessions preserved."):
                return
        
        if not self.is_admin:
            self.log_message("[DENIED] Bukan Admin. Beberapa pembersihan dilewati.", "error")
        
        self.cleaning_active = True
        self.stop_cleaning_event.clear()
        self.clean_button.config(state='disabled', bg="#8ab4f8")
        self.stop_button.config(state='normal', bg=self.error_color)
        self.clear_logs()
        self.log_message("Protokol pembersihan dimulai / Cleanup initiated.", "success")
        self.update_status("Menginisialisasi... / Initializing...", self.warning_color)
        self.update_progress(5)
        
        cleaning_thread = threading.Thread(target=self._start_cleaning_task, daemon=True)
        cleaning_thread.start()

    def stop_cleaning(self):
        """Mengirim sinyal berhenti ke proses pembersihan."""
        if not self.cleaning_active:
            return
        self.stop_cleaning_event.set()
        self.cleaning_active = False
        self.update_status("Menghentikan... / Stopping...", self.warning_color)
        self.stop_button.config(state='disabled')
        self.log_message("Sinyal berhenti dikirim. Menunggu operasi saat ini selesai.", "warning")

    def _start_cleaning_task(self):
        """Logika inti pembersihan (dijalankan di thread background)."""
        self.cleaning_stats = {'files_deleted': 0, 'folders_cleaned': 0, 'errors': 0}
        self.session_space_saved = 0
        self.update_stats_display()
        
        phases = [
            ("Windows Temp Files", self._clean_temp_files),
            ("Windows Update Cache", self._clean_update_cache),
            ("Prefetch Files", self._clean_prefetch),
            ("Recycle Bin", self._empty_recycle_bin),
            ("DNS Cache", self._flush_dns),
            ("Browser Caches", self._clean_browsers),
            ("Event Logs", self._clean_event_logs),
            ("Thumbnail Cache", self._clean_thumbnails),
            ("System Font Cache", self._clean_font_cache),
            ("Disk Cleanup Tool", self._run_disk_cleanup)
        ]
        
        total_phases = len(phases)
        
        try:
            start_time = time.time()
            
            for i, (phase_name, phase_func) in enumerate(phases, 1):
                if self.stop_cleaning_event.is_set():
                    self.log_message(f"Berhenti di fase: {phase_name}", "warning")
                    break
                    
                self.log_message(f"\n--- FASE {i}/{total_phases}: {phase_name} ---", "process")
                self.update_status(f"Fase {i}/{total_phases}: {phase_name}", self.accent_color)
                self.update_progress((i / total_phases) * 90)
                
                admin_required_phases = ["Event Logs", "Disk Cleanup Tool", "DNS Cache", "System Font Cache"]
                if phase_name in admin_required_phases and not self.is_admin:
                    self.log_message(f"Melewati '{phase_name}' (Perlu Admin).", "warning")
                else:
                    try:
                        phase_func()
                    except Exception as e:
                        self.log_message(f"Error pada {phase_name}: {str(e)}", "error")
                        self.cleaning_stats['errors'] += 1
                        self.update_stats_display()
                
                time.sleep(0.1)
            
            if self.cleaning_active and not self.stop_cleaning_event.is_set():
                elapsed_time = time.time() - start_time
                self.log_message(f"\n🎉 Selesai! Waktu: {elapsed_time:.1f} detik", "success")
                self.update_status("Pembersihan Sukses / Cleanup Complete", self.success_color)
                self.update_progress(100)
                
                self.last_cleaned = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.total_space_saved += self.session_space_saved
                self.space_saved = self._format_size(self.total_space_saved)
                self.update_info_labels()
                self.save_settings()
                
                self.show_completion_summary()
                time.sleep(2)
                
            elif self.stop_cleaning_event.is_set():
                self.log_message("\nPembersihan dihentikan pengguna.", "info")
                self.update_status("Dihentikan / Stopped", self.warning_color)
                self.update_progress(0)
                
        except Exception as e:
            self.log_message(f"Critical Error: {e}", "critical")
            self.update_status("Gagal / Failed!", self.error_color)
            self.update_progress(0)
            
        finally:
            self.cleaning_active = False
            self.clean_button.config(state='normal', bg=self.accent_color)
            self.stop_button.config(state='disabled', bg=self.error_color)
            if not self.stop_cleaning_event.is_set():
                self.update_status("Siap / Ready", self.success_color)
                self.update_progress(0)

    def show_completion_summary(self):
        if self.settings['show_confirmations']:
            summary = (f"Ringkasan / Summary:\n\n"
                       f"File Dihapus: {self.cleaning_stats['files_deleted']}\n"
                       f"Folder Dibersihkan: {self.cleaning_stats['folders_cleaned']}\n"
                       f"Error: {self.cleaning_stats['errors']}\n"
                       f"Ruang Kosong (Sesi ini): {self._format_size(self.session_space_saved)}\n"
                       f"Total Hemat Selamanya: {self.space_saved}")
            messagebox.showinfo("Selesai / Complete", summary)

    def clear_logs(self):
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')
        self.log_message("Log dibersihkan.", "info")

    def show_settings(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Pengaturan / Settings")
        settings_window.geometry("500x550") # Diperbesar untuk tab baru
        settings_window.configure(bg=self.bg_color)
        settings_window.resizable(False, False)
        settings_window.transient(self.master)
        settings_window.grab_set()
        
        settings_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - 250
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - 275
        settings_window.geometry(f"500x550+{x}+{y}")
        
        main_frame = tk.Frame(settings_window, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="Pengaturan / Settings", font=(self.main_font, 14, "bold"),
                fg=self.text_color, bg=self.bg_color).pack(pady=(0, 20))
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # General settings tab
        general_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(general_frame, text="Umum / General")
        
        self.auto_close_var = tk.BooleanVar(value=self.settings['auto_close_browsers'])
        self.deep_clean_var = tk.BooleanVar(value=self.settings['deep_clean_mode'])
        self.show_confirm_var = tk.BooleanVar(value=self.settings['show_confirmations'])
        
        tk.Checkbutton(general_frame, text="Tutup browser otomatis sebelum mulai\nAuto-close browsers before cleaning",
                        variable=self.auto_close_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        tk.Checkbutton(general_frame, text="Mode Deep Clean (Lebih lambat)\nDeep clean mode (Slower)",
                        variable=self.deep_clean_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        tk.Checkbutton(general_frame, text="Tampilkan konfirmasi dialog\nShow confirmation dialogs",
                        variable=self.show_confirm_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        # Browser settings tab
        browser_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(browser_frame, text="Browser")
        
        self.preserve_login_var = tk.BooleanVar(value=self.settings['preserve_login_data'])
        self.clean_history_var = tk.BooleanVar(value=self.settings['clean_browser_history'])
        self.clean_form_var = tk.BooleanVar(value=self.settings['clean_form_data'])
        self.clean_downloads_var = tk.BooleanVar(value=self.settings['clean_downloads'])
        
        tk.Checkbutton(browser_frame, text="Jaga data login (Direkomendasikan)\nPreserve login data",
                        variable=self.preserve_login_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        tk.Checkbutton(browser_frame, text="Bersihkan History / Riwayat\nClean browser history",
                        variable=self.clean_history_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        tk.Checkbutton(browser_frame, text="Bersihkan Form Data & Autofill\nClean form data",
                        variable=self.clean_form_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        tk.Checkbutton(browser_frame, text="Bersihkan folder Download\nClean downloads folder",
                        variable=self.clean_downloads_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        # Advanced settings tab
        advanced_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(advanced_frame, text="Lanjutan / Advanced")
        
        # Create backup before cleaning option
        self.create_backup_var = tk.BooleanVar(value=self.settings.get('create_backup', False))
        tk.Checkbutton(advanced_frame, text="Buat backup sebelum membersihkan\nCreate backup before cleaning",
                        variable=self.create_backup_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        # Clean system restore points option
        self.clean_restore_var = tk.BooleanVar(value=self.settings.get('clean_restore_points', False))
        tk.Checkbutton(advanced_frame, text="Hapus titik pemulihan lama (HATI-HATI)\nDelete old restore points (CAUTION)",
                        variable=self.clean_restore_var, font=(self.main_font, 9), justify="left",
                        fg=self.error_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        # Clean Windows search index option
        self.clean_search_var = tk.BooleanVar(value=self.settings.get('clean_search_index', False))
        tk.Checkbutton(advanced_frame, text="Bangun ulang indeks pencarian Windows\nRebuild Windows search index",
                        variable=self.clean_search_var, font=(self.main_font, 9), justify="left",
                        fg=self.text_color, bg=self.bg_color).pack(anchor="w", pady=5, padx=10)
        
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill="x", pady=(20, 0))
        
        save_btn = tk.Button(button_frame, text="Simpan / Save", command=lambda: self.save_settings_dialog(settings_window),
                            font=(self.main_font, 10), bg=self.accent_color, fg="#ffffff",
                            activebackground=self.accent_hover, bd=0, relief="flat", 
                            padx=20, pady=8, cursor="hand2")
        save_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = tk.Button(button_frame, text="Batal / Cancel", command=settings_window.destroy,
                                font=(self.main_font, 10), bg="#f1f3f4", fg=self.text_color,
                                activebackground="#e8eaed", bd=0, relief="flat", 
                                padx=20, pady=8, cursor="hand2")
        cancel_btn.pack(side="right")

    def save_settings_dialog(self, window):
        self.settings['auto_close_browsers'] = self.auto_close_var.get()
        self.settings['deep_clean_mode'] = self.deep_clean_var.get()
        self.settings['show_confirmations'] = self.show_confirm_var.get()
        self.settings['preserve_login_data'] = self.preserve_login_var.get()
        self.settings['clean_browser_history'] = self.clean_history_var.get()
        self.settings['clean_form_data'] = self.clean_form_var.get()
        self.settings['clean_downloads'] = self.clean_downloads_var.get()
        self.settings['create_backup'] = self.create_backup_var.get()
        self.settings['clean_restore_points'] = self.clean_restore_var.get()
        self.settings['clean_search_index'] = self.clean_search_var.get()
        self.save_settings()
        window.destroy()
        messagebox.showinfo("Pengaturan", "Pengaturan berhasil disimpan!")

    def show_help(self):
        help_window = tk.Toplevel(self.master)
        help_window.title("Bantuan / Help")
        help_window.geometry("600x500")
        help_window.configure(bg=self.bg_color)
        help_window.resizable(False, False)
        help_window.transient(self.master)
        help_window.grab_set()
        
        help_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - 300
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - 250
        help_window.geometry(f"600x500+{x}+{y}")
        
        # Create notebook for help sections
        main_frame = tk.Frame(help_window, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="Bantuan Scrubo / Scrubo Help", font=(self.main_font, 14, "bold"),
                fg=self.text_color, bg=self.bg_color).pack(pady=(0, 15))
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # About tab
        about_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(about_frame, text="Tentang / About")
        
        about_text = """Scrubo v2.5 - Pembersih Sistem & Browser

Pembersih sistem yang komprehensif dengan fokus pada keamanan data login pengguna.

Fitur Utama / Key Features:
• Membersihkan file temp Windows
• Membersihkan cache browser (Chrome, Firefox, Edge, dll)
• Melindungi data login dan sesi
• Antarmuka yang modern dan intuitif
• Penjadwalan pembersihan otomatis
• Analisis sistem terperinci

Keamanan / Safety:
• Mode aman default yang melindungi data login
• Opsi backup sebelum pembersihan
• Konfirmasi sebelum tindakan permanen

Pengembang / Developer: KandarLubis
GitHub: github.com/KandarLubis31"""
        
        about_text_widget = tk.Text(about_frame, wrap=tk.WORD, font=(self.main_font, 10),
                                   bg=self.card_bg, fg=self.text_color, bd=0, relief="flat",
                                   padx=15, pady=15)
        about_text_widget.pack(fill=tk.BOTH, expand=True)
        about_text_widget.insert("1.0", about_text)
        about_text_widget.config(state='disabled')
        
        # How to use tab
        usage_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(usage_frame, text="Cara Penggunaan / How to Use")
        
        usage_text = """Cara Menggunakan Scrubo / How to Use Scrubo:

1. Pilih Browser / Select Browsers
   Centang browser yang ingin dibersihkan cache-nya.

2. Mulai Pembersihan / Start Cleaning
   Klik tombol "MULAI PEMBERSIHAN" untuk memulai proses.

3. Monitor Proses / Monitor Process
   Lihat log sistem untuk memantau proses pembersihan.

4. Selesai / Complete
   Aplikasi akan menampilkan ringkasan setelah selesai.

Tips:
• Jalankan sebagai administrator untuk pembersihan penuh.
• Tutup browser secara manual sebelum memulai untuk hasil terbaik.
• Gunakan tab "Info Sistem" untuk melihat detail komputer.
• Atur penjadwalan untuk pembersihan otomatis."""
        
        usage_text_widget = tk.Text(usage_frame, wrap=tk.WORD, font=(self.main_font, 10),
                                   bg=self.card_bg, fg=self.text_color, bd=0, relief="flat",
                                   padx=15, pady=15)
        usage_text_widget.pack(fill=tk.BOTH, expand=True)
        usage_text_widget.insert("1.0", usage_text)
        usage_text_widget.config(state='disabled')
        
        # Troubleshooting tab
        troubleshoot_frame = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(troubleshoot_frame, text="Pemecahan Masalah / Troubleshooting")
        
        troubleshoot_text = """Pemecahan Masalah / Troubleshooting:

Masalah: Pembersihan tidak lengkap
Solusi: Jalankan sebagai administrator dan tutup semua browser.

Masalah: Login terhapus setelah pembersihan
Solusi: Pastikan opsi "Jaga data login" aktif di pengaturan.

Masalah: Aplikasi macet saat membersihkan
Solusi: Gunakan tombol STOP dan mulai ulang aplikasi.

Masalah: Error "Access Denied"
Solusi: Jalankan sebagai administrator atau nonaktifkan antivirus sementara.

Masalah: Browser tidak terdeteksi
Solusi: Pastikan browser terinstall dengan benar di lokasi default."""
        
        troubleshoot_text_widget = tk.Text(troubleshoot_frame, wrap=tk.WORD, font=(self.main_font, 10),
                                          bg=self.card_bg, fg=self.text_color, bd=0, relief="flat",
                                          padx=15, pady=15)
        troubleshoot_text_widget.pack(fill=tk.BOTH, expand=True)
        troubleshoot_text_widget.insert("1.0", troubleshoot_text)
        troubleshoot_text_widget.config(state='disabled')
        
        # Close button
        close_btn = tk.Button(main_frame, text="Tutup / Close", command=help_window.destroy,
                            font=(self.main_font, 10), bg=self.accent_color, fg="#ffffff",
                            activebackground=self.accent_hover, bd=0, relief="flat", 
                            padx=20, pady=8, cursor="hand2")
        close_btn.pack(pady=(15, 0))

    def update_status(self, message, color="#34a853"):
        def update():
            self.status_label.config(text=f"● {message}", fg=color)
        self.master.after(0, update)

    def update_progress(self, value):
        def update():
            self.progress_var.set(value)
        self.master.after(0, update)

    def log_message(self, message, msg_type="info"):
        """Menambahkan pesan ke jendela log GUI."""
        if self.settings['log_level'] == 'minimal' and msg_type in ['scan', 'process']:
            return
        elif self.settings['log_level'] == 'normal' and msg_type == 'scan':
            return
            
        colors = {
            "info": self.text_color, "success": self.success_color, 
            "warning": self.warning_color, "error": self.error_color,
            "process": self.accent_color, "scan": self.text_secondary,
            "critical": "#b00020"
        }
        
        color = colors.get(msg_type, self.text_color)
        timestamp = time.strftime("%H:%M:%S")
        
        def update_log():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
            
            line_start = self.log_area.index("end-2c linestart")
            line_end = self.log_area.index("end-2c lineend")
            self.log_area.tag_add(msg_type, line_start, line_end)
            self.log_area.tag_config(msg_type, foreground=color)
            
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        
        self.master.after(0, update_log)

    def update_info_labels(self):
        def update():
            if "Last Cleaned" in self.info_labels:
                self.info_labels["Last Cleaned"].config(text=self.last_cleaned)
            if "Total Saved" in self.info_labels:
                self.info_labels["Total Saved"].config(text=self.space_saved)
        self.master.after(0, update)

    def update_stats_display(self):
        def update():
            if "files_deleted" in self.stats_labels:
                self.stats_labels["files_deleted"].config(text=f"{self.cleaning_stats['files_deleted']}")
            if "folders_cleaned" in self.stats_labels:
                self.stats_labels["folders_cleaned"].config(text=f"{self.cleaning_stats['folders_cleaned']}")
            if "errors" in self.stats_labels:
                self.stats_labels["errors"].config(text=f"{self.cleaning_stats['errors']}")
            if "session_space" in self.stats_labels:
                self.stats_labels["session_space"].config(text=self._format_size(getattr(self, 'session_space_saved', 0)))
        self.master.after(0, update)

    def run_command(self, command, shell=False, check=False, timeout=30):
        """Menjalankan perintah terminal/CMD eksternal."""
        if isinstance(command, str):
            shell = True
        try:
            result = subprocess.run(
                command, shell=shell, check=check, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, encoding='utf-8', errors='ignore',
                timeout=timeout)
            return result
        except Exception as e:
            self.log_message(f"Command error: {str(e)[:50]}", "error")
            return None

    def clean_directory_contents(self, path, exclude_patterns=None):
        """Menghapus isi folder dengan pengecualian item tertentu."""
        if self.stop_cleaning_event.is_set(): 
            return
            
        if not os.path.exists(path):
            return
            
        items_deleted = 0
        folders_cleaned = 0
        space_freed = 0
        
        if exclude_patterns is None:
            exclude_patterns = self.common_protected
            
        try:
            # Menggunakan scandir untuk performa lebih cepat di Windows
            with os.scandir(path) as entries:
                for entry in entries:
                    if self.stop_cleaning_event.is_set(): return
                    
                    item_name = entry.name
                    # Cek perlindungan (exclude list)
                    if any(p.lower() in item_name.lower() for p in exclude_patterns):
                        continue
                        
                    item_path = entry.path
                    try:
                        if entry.is_file() or entry.is_symlink():
                            size = entry.stat().st_size
                            os.unlink(item_path)
                            items_deleted += 1
                            space_freed += size
                        elif entry.is_dir():
                            dir_size = self._get_dir_size(item_path)
                            shutil.rmtree(item_path, ignore_errors=True)
                            folders_cleaned += 1
                            space_freed += dir_size
                    except (PermissionError, OSError):
                        pass
                    except Exception:
                        self.cleaning_stats['errors'] += 1
                        
            self.cleaning_stats['files_deleted'] += items_deleted
            self.cleaning_stats['folders_cleaned'] += folders_cleaned
            self.session_space_saved = getattr(self, 'session_space_saved', 0) + space_freed
            self.update_stats_display()
            
            if items_deleted > 0 or folders_cleaned > 0:
                self.log_message(f"✓ Dibersihkan \"{os.path.basename(path)}\": {self._format_size(space_freed)}", "success")
                    
        except Exception as e:
            self.log_message(f"Akses error \"{path}\": {str(e)[:50]}", "error")

    def _get_dir_size(self, path):
        total = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir():
                        total += self._get_dir_size(entry.path)
        except Exception:
            pass
        return total

    def _format_size(self, size_bytes):
        if size_bytes == 0: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _clean_temp_files(self):
        """Membersihkan temporary files Windows."""
        temp_dirs = [
            os.environ.get('TEMP'),
            os.environ.get('TMP'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp')
        ]
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                self.clean_directory_contents(temp_dir)

    def _clean_update_cache(self):
        """Membersihkan cache Windows Update."""
        paths = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution', 'Download'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution', 'DataStore')
        ]
        for path in paths:
            if os.path.exists(path):
                self.clean_directory_contents(path)

    def _clean_prefetch(self):
        path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
        if os.path.exists(path):
            self.clean_directory_contents(path)

    def _empty_recycle_bin(self):
        """Mengosongkan Recycle Bin."""
        self.log_message("Mengosongkan Recycle Bin...", "process")
        # Coba pakai powershell dulu
        result = self.run_command(["powershell.exe", "-command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
        # Fallback manual method
        if not result or result.returncode != 0:
            for drive in ['C:', 'D:', 'E:']:
                path = f"{drive}\\$Recycle.Bin"
                if os.path.exists(path):
                    self.run_command(f'rd /s /q "{path}" 2>nul', shell=True)
        self.log_message("Recycle bin selesai.", "success")

    def _flush_dns(self):
        self.run_command(["ipconfig", "/flushdns"])
        self.log_message("DNS cache di-flush.", "success")

    def _close_browsers(self):
        """Menutup paksa browser dengan aman sebelum pembersihan."""
        if psutil is None:
            self.log_message("Modul psutil tidak ditemukan. Skip menutup browser otomatis.", "warning")
            return

        self.log_message("Menutup browser yang berjalan...", "process")
        browsers = ["chrome.exe", "firefox.exe", "msedge.exe", "opera.exe", "brave.exe", "vivaldi.exe"]
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in browsers:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)

    def _clean_browsers(self):
        """Fungsi utama untuk membersihkan berbagai browser."""
        if self.settings['auto_close_browsers']:
            self._close_browsers()

        # Browser definitions: (Name, Config Var Name, Path Lists, Cache Folders, Protected Files)
        browsers = [
            ('Chrome', 'Chrome', 
             [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')], 
             ['Cache', 'Code Cache', 'GPUCache', 'Media Cache'], self.chrome_protected),
            
            ('Edge', 'Edge', 
             [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data')],
             ['Cache', 'Code Cache', 'GPUCache', 'Media Cache'], self.chrome_protected),
             
            ('Brave', 'Brave', 
             [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'User Data')],
             ['Cache', 'Code Cache', 'GPUCache', 'Media Cache'], self.chrome_protected),
             
            ('Vivaldi', 'Vivaldi', 
             [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Vivaldi', 'User Data')],
             ['Cache', 'Code Cache', 'GPUCache', 'Media Cache'], self.chrome_protected),
             
            ('Opera', 'Opera', 
             [os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera Stable'),
              os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera GX Stable')],
             ['Cache', 'GPUCache', 'Media Cache'], self.chrome_protected),
             
            ('Internet Explorer', 'Internet Explorer',
             [os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'INetCache')],
             ['Content.IE5'], self.chrome_protected)
        ]

        # Process Chromium-based browsers
        for name, key, base_paths, caches, protected in browsers:
            if self.browser_vars.get(key, False):
                self._clean_chromium_based(name, base_paths, caches, protected)

        # Process Firefox separately (different structure)
        if self.browser_vars.get('Firefox', False):
            self._clean_firefox()

        if self.settings['clean_downloads']:
            self._clean_downloads_folder()

    def _clean_chromium_based(self, name, base_paths, caches, protected):
        self.log_message(f"Membersihkan {name}...", "process")
        
        target_caches = caches.copy()
        if self.settings['clean_browser_history']: target_caches.append('History')
        if self.settings['clean_form_data']: target_caches.append('Web Data')

        for base in base_paths:
            if not os.path.exists(base): continue
            
            profiles = ['Default', 'System Profile', 'Guest Profile']
            try:
                profiles.extend([d for d in os.listdir(base) if d.startswith('Profile ')])
            except OSError: pass

            for profile in profiles:
                profile_path = os.path.join(base, profile)
                if not os.path.exists(profile_path): continue

                for cache in target_caches:
                    self.clean_directory_contents(os.path.join(profile_path, cache))

                # Clean loose files
                try:
                    with os.scandir(profile_path) as it:
                        for entry in it:
                            if entry.is_file():
                                if self.settings['preserve_login_data'] and any(p in entry.name for p in protected):
                                    continue
                                if entry.name.endswith(('.log', '.tmp', '.old')):
                                    try:
                                        os.unlink(entry.path)
                                        self.cleaning_stats['files_deleted'] += 1
                                    except: pass
                except: pass

    def _clean_firefox(self):
        self.log_message("Membersihkan Firefox...", "process")
        base = os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
        if not os.path.exists(base): return

        try:
            for profile in os.listdir(base):
                p_path = os.path.join(base, profile)
                if os.path.isdir(p_path):
                    for cache in ['cache2', 'startupCache']:
                        self.clean_directory_contents(os.path.join(p_path, cache))
                    
                    try:
                        with os.scandir(p_path) as it:
                            for entry in it:
                                if entry.is_file() and entry.name.endswith(('.log', '.tmp', '.old')):
                                    if not (self.settings['preserve_login_data'] and any(p in entry.name for p in self.firefox_protected)):
                                        try:
                                            os.unlink(entry.path)
                                            self.cleaning_stats['files_deleted'] += 1
                                        except: pass
                    except: pass
        except: pass

    def _clean_downloads_folder(self):
        path = os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads')
        if os.path.exists(path):
            self.log_message("Membersihkan Downloads (file > 7 hari)...", "process")
            cutoff = time.time() - (7 * 86400)
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if entry.stat().st_mtime < cutoff:
                            if entry.is_file():
                                try:
                                    os.unlink(entry.path)
                                    self.cleaning_stats['files_deleted'] += 1
                                except: pass
                            elif entry.is_dir():
                                try:
                                    shutil.rmtree(entry.path)
                                    self.cleaning_stats['folders_cleaned'] += 1
                                except: pass
            except: pass

    def _clean_event_logs(self):
        if not self.is_admin: return
        self.log_message("Membersihkan Event Logs...", "process")
        logs = ["Application", "Security", "System"]
        for log in logs:
            self.run_command(["wevtutil", "cl", log])

    def _clean_thumbnails(self):
        path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer')
        if os.path.exists(path):
            self.log_message("Membersihkan Thumbnail Cache...", "process")
            for f in glob.glob(os.path.join(path, 'thumbcache_*.db')):
                try:
                    os.unlink(f)
                    self.cleaning_stats['files_deleted'] += 1
                except: pass

    def _clean_font_cache(self):
        if not self.is_admin: return
        self.log_message("Membersihkan Font Cache...", "process")
        self.run_command(["net", "stop", "FontCache"])
        time.sleep(1)
        
        paths = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'FontCache'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'FNTCACHE.DAT')
        ]
        
        for p in paths:
            if os.path.isfile(p):
                try: os.unlink(p) 
                except: pass
            elif os.path.isdir(p):
                self.clean_directory_contents(p)
                
        self.run_command(["net", "start", "FontCache"])

    def _clean_restore_points(self):
        """Clean old system restore points if enabled in settings"""
        if not self.settings.get('clean_restore_points', False) or not self.is_admin:
            return
            
        self.log_message("Membersihkan titik pemulihan lama...", "process")
        # Keep only the most recent restore point
        self.run_command(["vssadmin", "delete", "shadows", "/For=C:", "/Oldest"])

    def _rebuild_search_index(self):
        """Rebuild Windows search index if enabled in settings"""
        if not self.settings.get('clean_search_index', False):
            return
            
        self.log_message("Membangun ulang indeks pencarian...", "process")
        self.run_command(["sc", "stop", "WSearch"])
        time.sleep(2)
        
        # Delete the search index
        search_db = os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Search', 'Data', 'Applications', 'Windows')
        if os.path.exists(search_db):
            self.clean_directory_contents(search_db)
            
        self.run_command(["sc", "start", "WSearch"])

    def _run_disk_cleanup(self):
        if not self.is_admin: return
        self.log_message("Menjalankan Disk Cleanup...", "process")
        self.run_command("cleanmgr.exe /sagerun:1", shell=True)
        
        # Additional cleaning if advanced options are enabled
        if self.settings.get('clean_restore_points', False):
            self._clean_restore_points()
            
        if self.settings.get('clean_search_index', False):
            self._rebuild_search_index()

    def check_admin_privileges(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def on_closing(self):
        # Stop scheduler before closing
        self.stop_scheduler()
        
        if self.cleaning_active:
            if messagebox.askokcancel("Keluar / Quit", "Pembersihan sedang berjalan. Berhenti dan keluar?"):
                self.stop_cleaning_event.set()
                self.cleaning_active = False
                self.save_settings()
                self.master.destroy()
        else:
            self.save_settings()
            self.master.destroy()

def main():
    root = tk.Tk()
    app = ScruboApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()