import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import tkinter.font as tkFont
import subprocess
import os
import shutil
import glob
import threading
import time
import ctypes
import webbrowser
from datetime import datetime

class WinClearCacheApp:
    def __init__(self, master):
        self.master = master
        self.setup_window()
        self.setup_styles()
        self.setup_variables()
        
        self.setup_ui() 
        self.is_admin = self.check_admin_privileges() 


    def setup_window(self):
        self.master.title("WinClearCache Tool - DarkMatter")
        self.master.geometry("900x750")
        self.master.resizable(True, True)
        self.master.minsize(850, 650)
        self.master.configure(bg="#0d1117")
        
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    def get_available_font(self, font_list):
        for font in font_list:
            try:
                tkFont.Font(family=font)
                return font
            except tk.TclError:
                continue
        return "TkDefaultFont"

    def setup_styles(self):
        self.main_font = self.get_available_font(["Fira Code", "Consolas", "Courier New"])
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TProgressbar", 
                             thickness=12, 
                             troughcolor="#404040", 
                             background="#58a6ff",
                             bordercolor="#30363d",
                             lightcolor="#58a6ff",
                             darkcolor="#58a6ff")

    def setup_variables(self):
        self.cleaning_active = False
        self.stop_cleaning_event = threading.Event()
        self.admin_warning_shown = False
        self.last_cleaned = "Never" # Akan diupdate setelah pembersihan pertama
        self.space_saved = "0 KB" # Akan diupdate
        self.cleaning_stats = {
            'files_deleted': 0,
            'folders_cleaned': 0,
            'errors': 0
        }
        # self.info_labels dan self.stats_labels akan diinisialisasi di fungsi create_..._section


    # --- UI Setup Functions ---
    def setup_ui(self):
        self.main_frame = tk.Frame(self.master, bg="#0d1117")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_rowconfigure(3, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=0)
        self.main_frame.grid_rowconfigure(5, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.create_header(self.main_frame)
        self.create_stats_section(self.main_frame)
        self.create_status_bar(self.main_frame)
        self.create_log_section(self.main_frame)
        self.create_control_buttons(self.main_frame)
        self.create_footer(self.main_frame)


    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg="#21262d", bd=1, relief="solid")
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 15))

        tk.Label(header_frame, text="┌─────────────────────────────────────────┐", 
                 font=(self.main_font, 10), fg="#58a6ff", bg="#21262d").pack(pady=(10,0))
        tk.Label(header_frame, text="│     WinClearCache Tool - DarkMatter     │", 
                 font=(self.main_font, 14, "bold"), fg="#58a6ff", bg="#21262d").pack()
        tk.Label(header_frame, text="└─────────────────────────────────────────┘", 
                 font=(self.main_font, 10), fg="#58a6ff", bg="#21262d").pack(pady=(0,10))

        # --- PERBAIKAN DI SINI: Tambahkan Last Cleaned dan Space Saved ke info_data ---
        info_data = [
            ("User:", os.getlogin()),
            ("Author:", "KandarLubis"),
            ("Github:", "github.com/KandarLubis31"),
            ("Last Cleaned:", self.last_cleaned), # Pastikan ini ada
            ("Space Saved:", self.space_saved) # Pastikan ini ada
        ]

        info_grid_frame = tk.Frame(header_frame, bg="#21262d")
        info_grid_frame.pack(fill="x", padx=20, pady=(5, 10))
        info_grid_frame.grid_columnconfigure(0, weight=0)
        info_grid_frame.grid_columnconfigure(1, weight=1)

        self.info_labels = {} # Inisialisasi dictionary di sini
        for i, (label_text, value_text) in enumerate(info_data):
            tk.Label(info_grid_frame, text=label_text, font=(self.main_font, 9, "bold"), 
                     fg="#f0f6fc", bg="#21262d").grid(row=i, column=0, sticky="w", pady=1)
            # Simpan referensi Label untuk diupdate nanti
            self.info_labels[label_text.strip(":")] = tk.Label(info_grid_frame, text=value_text, font=(self.main_font, 9), 
                                                               fg="#7dd3fc", bg="#21262d")
            self.info_labels[label_text.strip(":")].grid(row=i, column=1, sticky="w", padx=5, pady=1)
        
        tk.Frame(header_frame, height=5, bg="#21262d").pack()


    def create_stats_section(self, parent):
        stats_frame = tk.Frame(parent, bg="#21262d", bd=1, relief="solid")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_columnconfigure(2, weight=1)

        stats = [
            ("Files Deleted", "0", "#58a6ff"),
            ("Folders Cleaned", "0", "#7ee787"),
            ("Errors", "0", "#f85149")
        ]

        self.stats_labels = {} # Inisialisasi dictionary di sini
        for i, (label_text, initial_value, color) in enumerate(stats):
            stat_col_frame = tk.Frame(stats_frame, bg="#21262d")
            stat_col_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            
            tk.Label(stat_col_frame, text=f"📊 {label_text}", font=(self.main_font, 9), 
                     fg="#c9d1d9", bg="#21262d").pack()
            
            self.stats_labels[label_text.replace(" ", "_").lower()] = tk.Label(stat_col_frame, text=initial_value, font=(self.main_font, 12, "bold"), 
                                                                              fg=color, bg="#21262d")
            self.stats_labels[label_text.replace(" ", "_").lower()].pack()


    def create_status_bar(self, parent):
        status_bar_frame = tk.Frame(parent, bg="#21262d", height=40, bd=1, relief="solid")
        status_bar_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 15))
        status_bar_frame.grid_propagate(False)
        status_bar_frame.grid_columnconfigure(0, weight=1)
        status_bar_frame.grid_columnconfigure(1, weight=0)

        self.status_label = tk.Label(status_bar_frame, text="● Ready", 
                                     font=(self.main_font, 10, "bold"), 
                                     fg="#3fb950", bg="#21262d")
        self.status_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.progress_frame = tk.Frame(status_bar_frame, bg="#21262d")
        self.progress_frame.grid(row=0, column=1, padx=15, pady=8, sticky="e")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, 
                                             length=200, mode='determinate', style="TProgressbar")
        self.progress_bar.pack(side="right")
        self.update_progress(0)


    def create_log_section(self, parent):
        log_frame = tk.Frame(parent, bg="#0d1117")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 15))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_header = tk.Frame(log_frame, bg="#21262d", height=35)
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        log_header.grid_propagate(False)
        log_header.grid_columnconfigure(0, weight=1)
        
        tk.Label(log_header, text="📋 SYSTEM LOGS", font=(self.main_font, 11, "bold"), 
                 fg="#58a6ff", bg="#21262d").grid(row=0, column=0, padx=15, pady=8, sticky="w")

        clear_btn = tk.Button(log_header, text="Clear Logs", command=self.clear_logs,
                              font=(self.main_font, 9), bg="#6e7681", fg="#f0f6fc",
                              activebackground="#8b949e", bd=0, relief="flat",
                              padx=15, cursor="hand2")
        clear_btn.grid(row=0, column=1, padx=15, pady=6, sticky="e")

        log_container = tk.Frame(log_frame, bg="#0d1117", bd=1, relief="solid")
        log_container.grid(row=1, column=0, sticky="nsew")
        
        self.log_area = scrolledtext.ScrolledText(
            log_container, wrap=tk.WORD, font=(self.main_font, 9),
            bg="#161b22", fg="#e6edf3", insertbackground="#58a6ff",
            bd=0, relief="flat", selectbackground="#264f78",
            selectforeground="#ffffff"
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state='disabled')


    def create_control_buttons(self, parent):
        button_frame = tk.Frame(parent, bg="#0d1117")
        button_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=(0, 0))

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=0)

        self.clean_button = tk.Button(
            button_frame, text="🚀 INITIATE CLEANUP", width=20,
            command=self.run_cleaning_in_thread,
            font=(self.main_font, 12, "bold"),
            bg="#238636", fg="#ffffff",
            activebackground="#2ea043", activeforeground="#ffffff",
            bd=0, relief="flat", padx=30, pady=12,
            cursor="hand2"
        )
        self.clean_button.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.stop_button = tk.Button(
            button_frame, text="⏹️ STOP", width=10,
            command=self.stop_cleaning,
            font=(self.main_font, 10, "bold"),
            bg="#da3633", fg="#ffffff",
            activebackground="#f85149", activeforeground="#ffffff",
            bd=0, relief="flat", padx=20, pady=12,
            cursor="hand2", state='disabled'
        )
        self.stop_button.grid(row=0, column=1, sticky="w", padx=(0, 10))

        util_frame = tk.Frame(button_frame, bg="#0d1117")
        util_frame.grid(row=0, column=2, sticky="e")

        settings_btn = tk.Button(
            util_frame, text="⚙️ Settings", width=10,
            command=self.show_settings,
            font=(self.main_font, 10),
            bg="#6e7681", fg="#f0f6fc",
            activebackground="#8b949e", activeforeground="#ffffff",
            bd=0, relief="flat", padx=15, pady=12,
            cursor="hand2"
        )
        settings_btn.grid(row=0, column=0, padx=5)

        help_btn = tk.Button(
            util_frame, text="❓ Help", width=10,
            command=self.show_help,
            font=(self.main_font, 10),
            bg="#6e7681", fg="#f0f6fc",
            activebackground="#8b949e", activeforeground="#ffffff",
            bd=0, relief="flat", padx=15, pady=12,
            cursor="hand2"
        )
        help_btn.grid(row=0, column=1, padx=5)


    def create_footer(self, parent):
        footer_frame = tk.Frame(parent, bg="#21262d", height=30)
        footer_frame.grid(row=5, column=0, sticky="ew", padx=0, pady=(15, 0))
        footer_frame.grid_propagate(False)
        
        tk.Label(footer_frame, text=f"© {datetime.now().year} WinClearCache Tool | v1.2.0", 
                 font=(self.main_font, 8), fg="#8b949e", bg="#21262d").pack(side=tk.LEFT, padx=15)
        
        github_btn = tk.Label(footer_frame, text="GitHub", font=(self.main_font, 8, "underline"), 
                              fg="#58a6ff", bg="#21262d", cursor="hand2")
        github_btn.pack(side=tk.RIGHT, padx=15)
        github_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/KandarLubis31"))


    # --- Fungsi Utama Pengontrol Proses Pembersihan ---
    def run_cleaning_in_thread(self):
        if self.cleaning_active:
            self.log_message("Cleanup is already running.", "warning")
            return

        if not self.is_admin:
            self.log_message("[DENIED] Cleanup initiated without administrator privileges. Some operations will be skipped.", "error")
            # Tidak perlu pop-up lagi di sini, karena sudah di check_admin_privileges()
            # return # Uncomment ini jika Anda ingin sepenuhnya memblokir proses jika tidak admin

        self.cleaning_active = True
        self.stop_cleaning_event.clear()
        self.clean_button.config(state='disabled', bg="#1f6feb")
        self.stop_button.config(state='normal', bg="#da3633")
        
        self.clear_logs()
        self.log_message("Cleanup protocol initiated.", "success")
        self.update_status("Initializing cleanup...", "#f1c40f")
        self.update_progress(5)
        
        cleaning_thread = threading.Thread(target=self._start_cleaning_task, daemon=True)
        cleaning_thread.start()

    def stop_cleaning(self):
        if not self.cleaning_active:
            self.log_message("Cleanup is not running.", "info")
            return
        self.stop_cleaning_event.set()
        self.cleaning_active = False
        self.update_status("Stopping cleanup...", "#f1c40f")
        self.stop_button.config(state='disabled')

    def _start_cleaning_task(self):
        # Reset stats for new run
        self.cleaning_stats = {
            'files_deleted': 0,
            'folders_cleaned': 0,
            'errors': 0
        }
        self.space_saved = "0 KB" # Reset space saved
        self.update_stats_display() # Update display to 0s

        phases = [
            ("Windows Temp Files", self._clean_temp_files),
            ("Windows Update Cache", self._clean_update_cache),
            ("Prefetch Files", self._clean_prefetch),
            ("Recycle Bin", self._empty_recycle_bin),
            ("DNS Cache", self._flush_dns),
            ("Browser Caches", self._clean_browsers),
            ("Event Logs", self._clean_event_logs),
            ("Thumbnail Cache", self._clean_thumbnails),
            ("Disk Cleanup Tool", self._run_disk_cleanup)
        ]

        total_phases = len(phases)
        try:
            for i, (phase_name, phase_func) in enumerate(phases, 1):
                if self.stop_cleaning_event.is_set():
                    self.log_message(f"Cleanup interrupted at phase: {phase_name}", "warning")
                    break
                    
                self.log_message(f"\n--- PHASE {i}/{total_phases}: {phase_name} ---", "process")
                self.update_status(f"Phase {i}/{total_phases}: {phase_name}", "#58a6ff")
                self.update_progress( (i / total_phases) * 90 )
                
                # Tambahkan pemeriksaan admin di sini juga jika fungsi tersebut memang butuh admin
                if phase_name in ["Event Logs", "Disk Cleanup Tool", "DNS Cache"] and not self.is_admin:
                    self.log_message(f"Skipping '{phase_name}' (requires administrator privileges).", "warning")
                else:
                    phase_func()
                time.sleep(0.1)

            if self.cleaning_active and not self.stop_cleaning_event.is_set():
                self.log_message("\n🎉 Cleanup Protocol Complete!", "success")
                self.update_status("Cleanup completed successfully", "#3fb950")
                self.update_progress(100)
                self.last_cleaned = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.update_info_labels() # Update last cleaned time
                time.sleep(2)
                
            elif self.stop_cleaning_event.is_set():
                self.log_message("\nCleanup protocol stopped by user.", "info")
                self.update_status("Cleanup stopped", "#d29922")
                self.update_progress(0)
                
        except Exception as e:
            self.log_message(f"Critical error during cleanup: {e}", "critical")
            messagebox.showerror("Critical Error", f"An unexpected error occurred during cleanup: {e}")
            self.update_status("Cleanup failed!", "#f85149")
            self.update_progress(0)
        finally:
            self.cleaning_active = False
            self.clean_button.config(state='normal', bg="#238636")
            self.stop_button.config(state='disabled', bg="#da3633")
            self.update_status("Ready", "#3fb950")
            self.update_progress(0)

    # --- Utility Functions ---
    def clear_logs(self):
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')
        self.log_message("Log cleared.", "info")

    def show_settings(self):
        messagebox.showinfo("Settings", "Settings panel coming soon!", icon="info")

    def show_help(self):
        messagebox.showinfo("Help", 
                            "This tool helps clean various cache and temporary files from your Windows system and browsers.\n\n"
                            "Key features:\n"
                            "- Cleans temp files, prefetch, recycle bin, DNS cache.\n"
                            "- Cleans browser caches (Chrome, Firefox, Edge, Opera).\n"
                            "- Cleans Windows Event Logs and Thumbnail Cache.\n"
                            "- Integrates with Windows Disk Cleanup for advanced options.\n\n"
                            "IMPORTANT: For full functionality, please 'Run as administrator'.\n\n"
                            "Author: KandarLubis", icon="question")

    def update_status(self, message, color="#3fb950"):
        self.status_label.config(text=f"● {message}", fg=color)
        self.master.update_idletasks()

    def update_progress(self, value):
        self.progress_var.set(value)
        self.master.update_idletasks()

    def log_message(self, message, msg_type="info"):
        colors = {
            "info": "#e6edf3",
            "success": "#3fb950", 
            "warning": "#d29922",
            "error": "#f85149",
            "process": "#58a6ff",
            "scan": "#a5a5a5",
            "critical": "#ff0000"
        }
        
        color = colors.get(msg_type, "#e6edf3")
        timestamp = time.strftime("%H:%M:%S")
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        
        line_start = self.log_area.index("end-2c linestart")
        line_end = self.log_area.index("end-2c lineend")
        self.log_area.tag_add(msg_type, line_start, line_end)
        self.log_area.tag_config(msg_type, foreground=color)
        
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.master.update_idletasks()

    def update_info_labels(self):
        # This function updates the info labels in the header
        # Ensure 'Last Cleaned' and 'Space Saved' keys exist before updating
        if "Last Cleaned" in self.info_labels:
            self.info_labels["Last Cleaned"].config(text=self.last_cleaned)
        if "Space Saved" in self.info_labels:
            self.info_labels["Space Saved"].config(text=self.space_saved)


    def update_stats_display(self):
        # Update labels in stats section
        if "files_deleted" in self.stats_labels:
            self.stats_labels["files_deleted"].config(text=f"{self.cleaning_stats['files_deleted']}")
        if "folders_cleaned" in self.stats_labels:
            self.stats_labels["folders_cleaned"].config(text=f"{self.cleaning_stats['folders_cleaned']}")
        if "errors" in self.stats_labels:
            self.stats_labels["errors"].config(text=f"{self.cleaning_stats['errors']}")
        
        # update_info_labels is called separately for space saved/last cleaned


    def run_command(self, command, shell=False, check=False):
        if isinstance(command, str):
            shell = True

        try:
            result = subprocess.run(command, shell=shell, check=check,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='utf-8', errors='ignore')
            if result.stdout.strip():
                self.log_message(f"  [CMD_OUT] {result.stdout.strip()}", "info")
            if result.stderr.strip():
                self.log_message(f"  [CMD_ERR] {result.stderr.strip()}", "error")
            return result
        except FileNotFoundError:
            self.log_message(f"Command not found: {command[0] if isinstance(command, list) else command}", "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {command[0] if isinstance(command, list) else command}"
            if e.stderr.strip():
                error_msg += f" - {e.stderr.strip()}"
            if e.returncode == 5:
                error_msg += " (Access denied - may need higher privileges)"
            self.log_message(error_msg, "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None
        except Exception as e:
            self.log_message(f"Error executing command: {e}", "critical")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None

    def clean_directory_contents(self, path):
        if self.stop_cleaning_event.is_set(): return
            
        self.log_message(f"Scanning: \"{path}\"...", "scan")
        if os.path.exists(path):
            self.log_message(f"Cleaning: \"{path}\"...", "process")
            # self.cleaning_stats['folders_cleaned'] += 1 # Moved this into loop if successful deletion of folder
            # self.update_stats_display()

            max_retries = 3
            for i in range(max_retries):
                if self.stop_cleaning_event.is_set(): return
                try:
                    items_to_delete = os.listdir(path) # Get list once to avoid issues during deletion
                    for item_name in items_to_delete:
                        if self.stop_cleaning_event.is_set(): return
                        item_path = os.path.join(path, item_name)
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                # size = os.path.getsize(item_path) # For space calculation
                                os.unlink(item_path)
                                self.cleaning_stats['files_deleted'] += 1
                                # self.space_saved += size (if implementing space calculation)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                self.cleaning_stats['folders_cleaned'] += 1 # Sub-folders also counted
                            self.update_stats_display() # Update during deletion
                        except Exception as e:
                            if "_MEI" in item_path:
                                self.log_message(f"Skipped PyInstaller temp: {item_name}", "warning")
                            elif "Access is denied" in str(e):
                                self.log_message(f"Access denied: {item_name}", "warning")
                                self.cleaning_stats['errors'] += 1
                                self.update_stats_display()
                                time.sleep(0.5)
                                # Do not re-raise, handle retry at directory level if needed
                            else:
                                self.log_message(f"Failed to delete {item_name}: {e}", "warning")
                                self.cleaning_stats['errors'] += 1
                                self.update_stats_display()
                    self.log_message(f"Successfully cleaned: \"{path}\"", "success")
                    return # Exit retry loop if successful
                except Exception as e: # This outer catch is for issues listing dir or shutil.rmtree
                    if i < max_retries - 1:
                        self.log_message(f"Retrying cleaning of \"{path}\" ({i+1}/{max_retries})...", "warning")
                        time.sleep(1)
                    else:
                        self.log_message(f"Failed after {max_retries} attempts for \"{path}\": {e}", "error")
                        self.cleaning_stats['errors'] += 1 # Error for the directory
                        self.update_stats_display()
        else:
            self.log_message(f"Directory not found: \"{path}\"", "warning")

    # --- Individual Cleanup Phase Functions ---
    def _clean_temp_files(self):
        temp_dirs = [
            os.environ.get('TEMP'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            os.path.join(os.environ.get('USERPROFILE'), 'AppData', 'Local', 'Temp')
        ]
        for d in temp_dirs:
            if self.stop_cleaning_event.is_set(): return
            if d:
                self.clean_directory_contents(d)

    def _clean_update_cache(self):
        if self.stop_cleaning_event.is_set(): return
        win_update_cache = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution', 'Download')
        self.clean_directory_contents(win_update_cache)

    def _clean_prefetch(self):
        if self.stop_cleaning_event.is_set(): return
        win_prefetch = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
        self.clean_directory_contents(win_prefetch)

    def _empty_recycle_bin(self):
        if self.stop_cleaning_event.is_set(): return
        self.log_message("Emptying Recycle Bin...", "process")
        self.run_command(["powershell.exe", "-command", "Clear-RecycleBin -Force"])
        self.log_message("Recycle bin emptied", "success")

    def _flush_dns(self):
        if self.stop_cleaning_event.is_set(): return
        self.log_message("Flushing DNS cache...", "process")
        self.run_command(["ipconfig", "/flushdns"])
        self.log_message("DNS cache cleared", "success")

    def _clean_browsers(self):
        if self.stop_cleaning_event.is_set(): return

        browsers = {
            "Chrome": self._clean_chrome,
            "Firefox": self._clean_firefox,
            "Edge": self._clean_edge,
            "Opera": self._clean_opera,
        }
        
        self.log_message("Initiating browser cache cleanup...", "info")
        for browser_name, clean_func in browsers.items():
            if self.stop_cleaning_event.is_set(): break
            self.log_message(f"Cleaning {browser_name} cache...", "process")
            clean_func()

    def _clean_chrome(self):
        if self.stop_cleaning_event.is_set(): return
        chrome_data = os.path.join(os.environ.get('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default')
        chrome_caches = ['Cache', 'Code Cache', 'GPUCache', 'Media Cache', os.path.join('Service Worker', 'CacheStorage')]
        for cache in chrome_caches:
            if self.stop_cleaning_event.is_set(): return
            self.clean_directory_contents(os.path.join(chrome_data, cache))

    def _clean_firefox(self):
        if self.stop_cleaning_event.is_set(): return
        firefox_profiles_base = os.path.join(os.environ.get('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
        if os.path.exists(firefox_profiles_base):
            for profile_dir in os.listdir(firefox_profiles_base):
                if self.stop_cleaning_event.is_set(): return
                profile_path = os.path.join(firefox_profiles_base, profile_dir)
                if os.path.isdir(profile_path):
                    self.clean_directory_contents(os.path.join(profile_path, 'cache2'))
                    self.clean_directory_contents(os.path.join(profile_path, 'startupCache'))
        else:
            self.log_message("Firefox profile directory not found", "warning")

    def _clean_edge(self):
        if self.stop_cleaning_event.is_set(): return
        edge_data = os.path.join(os.environ.get('LOCALAPPDATA'), 'Microsoft', 'Edge', 'User Data', 'Default')
        edge_caches = ['Cache', 'Code Cache', 'GPUCache', 'Media Cache', os.path.join('Service Worker', 'CacheStorage')]
        for cache in edge_caches:
            if self.stop_cleaning_event.is_set(): return
            self.clean_directory_contents(os.path.join(edge_data, cache))

    def _clean_opera(self):
        if self.stop_cleaning_event.is_set(): return
        opera_data = os.path.join(os.environ.get('APPDATA'), 'Opera Software', 'Opera Stable')
        opera_caches = ['Cache', 'GPUCache']
        for cache in opera_caches:
            if self.stop_cleaning_event.is_set(): return
            self.clean_directory_contents(os.path.join(opera_data, cache))

    def _clean_event_logs(self):
        if self.stop_cleaning_event.is_set(): return
        if self.is_admin:
            self.log_message("Clearing Windows Event Logs...", "process")
            event_logs = ["Application", "Security", "System", "Setup"]
            for log_name in event_logs:
                if self.stop_cleaning_event.is_set(): return
                self.log_message(f"Clearing {log_name} log...", "process")
                self.run_command(["wevtutil", "cl", log_name])
            self.log_message("Event logs cleared", "success")
        else:
            self.log_message("Event log cleanup skipped (requires administrator)", "warning")

    def _clean_thumbnails(self):
        if self.stop_cleaning_event.is_set(): return
        self.log_message("Cleaning Windows Thumbnail Cache...", "process")
        thumb_cache_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'Microsoft', 'Windows', 'Explorer')
        thumb_cache_pattern = os.path.join(thumb_cache_dir, 'thumbcache_*.db')
        
        found_thumbs = glob.glob(thumb_cache_pattern)
        if found_thumbs:
            self.log_message(f"Removing {len(found_thumbs)} thumbnail cache files...", "process")
            for f in found_thumbs:
                if self.stop_cleaning_event.is_set(): return
                try:
                    os.unlink(f)
                except Exception as e:
                    self.log_message(f"Failed to delete thumbnail: {e}", "warning")
            self.log_message("Thumbnail cache cleared", "success")
        else:
            self.log_message("No thumbnail cache files found", "info")

    def _run_disk_cleanup(self):
        if self.stop_cleaning_event.is_set(): return
        if self.is_admin:
            self.log_message("Running built-in Disk Cleanup...", "process")
            self.log_message("ATTENTION: Disk Cleanup window may appear. Please confirm settings manually.", "warning")
            self.run_command("cleanmgr.exe /sageset:1", shell=True)
            self.run_command("cleanmgr.exe /sagerun:1", shell=True)
            self.log_message("Disk Cleanup process completed", "success")
        else:
            self.log_message("Disk Cleanup tool skipped (requires administrator)", "warning")

    def check_admin_privileges(self):
        try:
            subprocess.run(["net", "session"], check=True, stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, text=True)
            self.log_message("Administrator privileges detected", "success")
            return True
        except subprocess.CalledProcessError:
            self.log_message("Running without administrator privileges", "warning")
            if not self.admin_warning_shown:
                messagebox.showwarning("Administrator Required", 
                                      "This application is not running with administrator privileges.\n\n"
                                      "Some advanced cleanup functions (e.g., Event Logs, Disk Cleanup, DNS Flush) may not work.\n\n"
                                      "Please run as administrator for full functionality.")
                self.admin_warning_shown = True
            self.clean_button.config(bg="#d29922") 
            return False
        except FileNotFoundError:
            self.log_message("Cannot verify admin privileges (net command not found)", "error")
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = WinClearCacheApp(root)
    root.mainloop()