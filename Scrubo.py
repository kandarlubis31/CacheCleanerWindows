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
import json
from datetime import datetime
import tempfile
import sys

class ScruboApp:
    def __init__(self, master):
        self.master = master
        self.setup_window()
        self.setup_styles()
        self.setup_variables()
        self.load_settings()
        self.setup_ui() 
        self.is_admin = self.check_admin_privileges()
        self.load_previous_stats()

    def setup_window(self):
        self.master.title("Scrubo - DarkMatter v1.3.0")
        self.master.geometry("950x800")
        self.master.resizable(True, True)
        self.master.minsize(900, 700)
        self.master.configure(bg="#0d1117")
        
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.master.geometry(f"{width}x{height}+{x}+{y}")

    def get_available_font(self, font_list):
        for font in font_list:
            try:
                test_font = tkFont.Font(family=font)
                return font
            except tk.TclError:
                continue
        return "TkDefaultFont"

    def setup_styles(self):
        self.main_font = self.get_available_font(["Segoe UI", "Fira Code", "Consolas", "Courier New"])
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TProgressbar", 
                            thickness=12, 
                            troughcolor="#404040", 
                            background="#58a6ff", 
                            bordercolor="#30363d", 
                            lightcolor="#58a6ff", 
                            darkcolor="#58a6ff")
        
        self.style.configure("TCombobox", 
                            fieldbackground="#21262d",
                            background="#21262d",
                            foreground="#f0f6fc",
                            arrowcolor="#58a6ff")

    def setup_variables(self):
        self.cleaning_active = False
        self.stop_cleaning_event = threading.Event()
        self.admin_warning_shown = False
        self.last_cleaned = "Never"
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
            'log_level': 'normal'
        }

    def load_settings(self):
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
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".scrubo_config.json")
            config_data = self.settings.copy()
            config_data['last_cleaned'] = self.last_cleaned
            config_data['total_space_saved'] = self.total_space_saved
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_previous_stats(self):
        self.space_saved = self._format_size(self.total_space_saved)

    def setup_ui(self):
        self.main_frame = tk.Frame(self.master, bg="#0d1117")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        for i in range(6):
            self.main_frame.grid_rowconfigure(i, weight=0 if i != 3 else 1)
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
        
        tk.Label(header_frame, text="┌─────────────────────────────────┐", 
                font=(self.main_font, 10), fg="#58a6ff", bg="#21262d").pack(pady=(10,0))
        tk.Label(header_frame, text="│     Scrubo - DarkMatter     │", 
                font=(self.main_font, 14, "bold"), fg="#58a6ff", bg="#21262d").pack()
        tk.Label(header_frame, text="└─────────────────────────────────┘", 
                font=(self.main_font, 10), fg="#58a6ff", bg="#21262d").pack(pady=(0,10))
        
        try:
            username = os.getlogin()
        except Exception:
            username = os.environ.get('USERNAME', 'Unknown')
            
        info_data = [
            ("User:", username),
            ("Author:", "KandarLubis"),
            ("Github:", "github.com/KandarLubis31"),
            ("Last Cleaned:", self.last_cleaned),
            ("Total Space Saved:", self.space_saved)
        ]
        
        info_grid_frame = tk.Frame(header_frame, bg="#21262d")
        info_grid_frame.pack(fill="x", padx=20, pady=(5, 10))
        info_grid_frame.grid_columnconfigure(0, weight=0)
        info_grid_frame.grid_columnconfigure(1, weight=1)
        
        self.info_labels = {}
        for i, (label_text, value_text) in enumerate(info_data):
            tk.Label(info_grid_frame, text=label_text, 
                    font=(self.main_font, 9, "bold"), 
                    fg="#f0f6fc", bg="#21262d").grid(row=i, column=0, sticky="w", pady=1)
            
            self.info_labels[label_text.strip(":")] = tk.Label(
                info_grid_frame, text=value_text, 
                font=(self.main_font, 9), 
                fg="#7dd3fc", bg="#21262d")
            self.info_labels[label_text.strip(":")].grid(row=i, column=1, sticky="w", padx=5, pady=1)
        
        tk.Frame(header_frame, height=5, bg="#21262d").pack()

    def create_stats_section(self, parent):
        stats_frame = tk.Frame(parent, bg="#21262d", bd=1, relief="solid")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        stats = [
            ("Files Deleted", "0", "#58a6ff"),
            ("Folders Cleaned", "0", "#7ee787"),
            ("Errors", "0", "#f85149"),
            ("Session Space", "0 KB", "#d2a8ff")
        ]
        
        self.stats_labels = {}
        for i, (label_text, initial_value, color) in enumerate(stats):
            stat_col_frame = tk.Frame(stats_frame, bg="#21262d")
            stat_col_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            
            tk.Label(stat_col_frame, text=f"📊 {label_text}", 
                    font=(self.main_font, 9), fg="#c9d1d9", bg="#21262d").pack()
            
            key = label_text.replace(" ", "_").lower()
            self.stats_labels[key] = tk.Label(
                stat_col_frame, text=initial_value, 
                font=(self.main_font, 12, "bold"), 
                fg=color, bg="#21262d")
            self.stats_labels[key].pack()

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
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, 
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
        
        tk.Label(log_header, text="📋 SYSTEM LOGS", 
                font=(self.main_font, 11, "bold"), 
                fg="#58a6ff", bg="#21262d").grid(row=0, column=0, padx=15, pady=8, sticky="w")
        
        log_level_frame = tk.Frame(log_header, bg="#21262d")
        log_level_frame.grid(row=0, column=1, padx=5, pady=6, sticky="e")
        
        tk.Label(log_level_frame, text="Level:", font=(self.main_font, 8), 
                fg="#c9d1d9", bg="#21262d").pack(side="left", padx=(0, 5))
        
        self.log_level_var = tk.StringVar(value=self.settings['log_level'])
        log_level_combo = ttk.Combobox(log_level_frame, textvariable=self.log_level_var,
                                        values=['minimal', 'normal', 'verbose'], 
                                        width=8, state="readonly")
        log_level_combo.pack(side="left", padx=(0, 5))
        log_level_combo.bind('<<ComboboxSelected>>', self.on_log_level_change)
        
        clear_btn = tk.Button(
            log_header, text="Clear Logs", command=self.clear_logs,
            font=(self.main_font, 9), bg="#6e7681", fg="#f0f6fc",
            activebackground="#8b949e", bd=0, relief="flat", 
            padx=15, cursor="hand2")
        clear_btn.grid(row=0, column=2, padx=15, pady=6, sticky="e")
        
        log_container = tk.Frame(log_frame, bg="#0d1117", bd=1, relief="solid")
        log_container.grid(row=1, column=0, sticky="nsew")
        
        self.log_area = scrolledtext.ScrolledText(
            log_container, wrap=tk.WORD, font=(self.main_font, 9),
            bg="#161b22", fg="#e6edf3", insertbackground="#58a6ff",
            bd=0, relief="flat", selectbackground="#264f78", 
            selectforeground="#ffffff")
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
        
        tk.Label(footer_frame, text=f"© {datetime.now().year} Scrubo | v1.3.0", 
                font=(self.main_font, 8), fg="#8b949e", bg="#21262d").pack(side=tk.LEFT, padx=15)
        
        github_btn = tk.Label(footer_frame, text="GitHub", 
                            font=(self.main_font, 8, "underline"), 
                            fg="#58a6ff", bg="#21262d", cursor="hand2")
        github_btn.pack(side=tk.RIGHT, padx=15)
        github_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/KandarLubis31"))

    def on_log_level_change(self, event=None):
        self.settings['log_level'] = self.log_level_var.get()
        self.save_settings()
        self.log_message(f"Log level changed to: {self.settings['log_level']}", "info")

    def run_cleaning_in_thread(self):
        if self.cleaning_active:
            self.log_message("Cleanup is already running.", "warning")
            return
            
        if self.settings['show_confirmations']:
            if not messagebox.askyesno("Confirm Cleanup", 
                                        "Are you sure you want to start the cleanup process?\n\n"
                                        "This will delete temporary files and cache data."):
                return
        
        if not self.is_admin:
            self.log_message("[DENIED] Cleanup initiated without administrator privileges. Some operations will be skipped.", "error")
        
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
        self.log_message("Stop signal sent. Cleanup will halt after current operation.", "warning")

    def _start_cleaning_task(self):
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
                    self.log_message(f"Cleanup interrupted at phase: {phase_name}", "warning")
                    break
                    
                self.log_message(f"\n--- PHASE {i}/{total_phases}: {phase_name} ---", "process")
                self.update_status(f"Phase {i}/{total_phases}: {phase_name}", "#58a6ff")
                self.update_progress((i / total_phases) * 90)
                
                admin_required_phases = ["Event Logs", "Disk Cleanup Tool", "DNS Cache", "System Font Cache"]
                if phase_name in admin_required_phases and not self.is_admin:
                    self.log_message(f"Skipping '{phase_name}' (requires administrator privileges).", "warning")
                else:
                    try:
                        phase_func()
                    except Exception as e:
                        self.log_message(f"Error in {phase_name}: {str(e)}", "error")
                        self.cleaning_stats['errors'] += 1
                        self.update_stats_display()
                
                time.sleep(0.1)
            
            if self.cleaning_active and not self.stop_cleaning_event.is_set():
                elapsed_time = time.time() - start_time
                self.log_message(f"\n🎉 Cleanup Protocol Complete! (Elapsed: {elapsed_time:.1f}s)", "success")
                self.update_status("Cleanup completed successfully", "#3fb950")
                self.update_progress(100)
                
                self.last_cleaned = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.total_space_saved += self.session_space_saved
                self.space_saved = self._format_size(self.total_space_saved)
                self.update_info_labels()
                self.save_settings()
                
                self.show_completion_summary()
                time.sleep(2)
                
            elif self.stop_cleaning_event.is_set():
                self.log_message("\nCleanup protocol stopped by user.", "info")
                self.update_status("Cleanup stopped", "#d29922")
                self.update_progress(0)
                
        except Exception as e:
            self.log_message(f"Critical error during cleanup: {e}", "critical")
            messagebox.showerror("Critical Error", f"An unexpected error occurred during cleanup:\n{e}")
            self.update_status("Cleanup failed!", "#f85149")
            self.update_progress(0)
            
        finally:
            self.cleaning_active = False
            self.clean_button.config(state='normal', bg="#238636")
            self.stop_button.config(state='disabled', bg="#da3633")
            if not self.stop_cleaning_event.is_set():
                self.update_status("Ready", "#3fb950")
                self.update_progress(0)

    def show_completion_summary(self):
        if self.settings['show_confirmations']:
            summary = (f"Cleanup Summary:\n\n"
                       f"Files Deleted: {self.cleaning_stats['files_deleted']}\n"
                       f"Folders Cleaned: {self.cleaning_stats['folders_cleaned']}\n"
                       f"Errors: {self.cleaning_stats['errors']}\n"
                       f"Space Freed: {self._format_size(self.session_space_saved)}\n"
                       f"Total Space Saved: {self.space_saved}")
            messagebox.showinfo("Cleanup Complete", summary)

    def clear_logs(self):
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state='disabled')
        self.log_message("Log cleared.", "info")

    def show_settings(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.configure(bg="#0d1117")
        settings_window.resizable(False, False)
        settings_window.transient(self.master)
        settings_window.grab_set()
        
        settings_window.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - 200
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - 150
        settings_window.geometry(f"400x300+{x}+{y}")
        
        main_frame = tk.Frame(settings_window, bg="#0d1117")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="Settings", font=(self.main_font, 14, "bold"),
                fg="#58a6ff", bg="#0d1117").pack(pady=(0, 20))
        
        self.auto_close_var = tk.BooleanVar(value=self.settings['auto_close_browsers'])
        self.deep_clean_var = tk.BooleanVar(value=self.settings['deep_clean_mode'])
        self.show_confirm_var = tk.BooleanVar(value=self.settings['show_confirmations'])
        
        tk.Checkbutton(main_frame, text="Auto-close browsers before cleaning",
                        variable=self.auto_close_var, font=(self.main_font, 10),
                        fg="#f0f6fc", bg="#0d1117", selectcolor="#21262d",
                        activebackground="#0d1117", activeforeground="#f0f6fc").pack(anchor="w", pady=5)
        
        tk.Checkbutton(main_frame, text="Deep clean mode (slower but more thorough)",
                        variable=self.deep_clean_var, font=(self.main_font, 10),
                        fg="#f0f6fc", bg="#0d1117", selectcolor="#21262d",
                        activebackground="#0d1117", activeforeground="#f0f6fc").pack(anchor="w", pady=5)
        
        tk.Checkbutton(main_frame, text="Show confirmation dialogs",
                        variable=self.show_confirm_var, font=(self.main_font, 10),
                        fg="#f0f6fc", bg="#0d1117", selectcolor="#21262d",
                        activebackground="#0d1117", activeforeground="#f0f6fc").pack(anchor="w", pady=5)
        
        button_frame = tk.Frame(main_frame, bg="#0d1117")
        button_frame.pack(fill="x", pady=(30, 0))
        
        save_btn = tk.Button(button_frame, text="Save", command=lambda: self.save_settings_dialog(settings_window),
                            font=(self.main_font, 10), bg="#238636", fg="#ffffff",
                            activebackground="#2ea043", bd=0, relief="flat", 
                            padx=20, pady=8, cursor="hand2")
        save_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=settings_window.destroy,
                                font=(self.main_font, 10), bg="#6e7681", fg="#f0f6fc",
                                activebackground="#8b949e", bd=0, relief="flat", 
                                padx=20, pady=8, cursor="hand2")
        cancel_btn.pack(side="right")

    def save_settings_dialog(self, window):
        self.settings['auto_close_browsers'] = self.auto_close_var.get()
        self.settings['deep_clean_mode'] = self.deep_clean_var.get()
        self.settings['show_confirmations'] = self.show_confirm_var.get()
        self.save_settings()
        window.destroy()
        messagebox.showinfo("Settings", "Settings saved successfully!")

    def show_help(self):
        help_text = """Scrubo v1.3.0

This tool helps clean various cache and temporary files from your Windows system.

KEY FEATURES:
• Cleans Windows temp files, prefetch, and update cache
• Empties recycle bin and flushes DNS cache
• Cleans browser caches (Chrome, Firefox, Edge, Opera)
• Clears Windows Event Logs and Thumbnail Cache
• Removes system font cache
• Integrates with Windows Disk Cleanup tool

REQUIREMENTS:
• Windows 10/11
• Administrator privileges recommended for full functionality

SAFETY:
• Only removes temporary and cache files
• Does not delete personal documents or important system files
• Operation can be stopped at any time

Author: KandarLubis
GitHub: github.com/KandarLubis31"""
        messagebox.showinfo("Help", help_text, icon="question")

    def update_status(self, message, color="#3fb950"):
        def update():
            self.status_label.config(text=f"● {message}", fg=color)
        self.master.after(0, update)

    def update_progress(self, value):
        def update():
            self.progress_var.set(value)
        self.master.after(0, update)

    def log_message(self, message, msg_type="info"):
        if self.settings['log_level'] == 'minimal' and msg_type in ['scan', 'process']:
            return
        elif self.settings['log_level'] == 'normal' and msg_type == 'scan':
            return
            
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
            if "Total Space Saved" in self.info_labels:
                self.info_labels["Total Space Saved"].config(text=self.space_saved)
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
        if isinstance(command, str):
            shell = True
            
        try:
            result = subprocess.run(
                command, shell=shell, check=check, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, encoding='utf-8', errors='ignore',
                timeout=timeout)
                
            if result.stdout.strip() and self.settings['log_level'] == 'verbose':
                self.log_message(f"  [CMD_OUT] {result.stdout.strip()[:200]}...", "info")
            if result.stderr.strip():
                self.log_message(f"  [CMD_ERR] {result.stderr.strip()[:200]}...", "error")
            return result
            
        except subprocess.TimeoutExpired:
            self.log_message(f"Command timed out: {command[0] if isinstance(command, list) else command}", "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None
            
        except FileNotFoundError:
            self.log_message(f"Command not found: {command[0] if isinstance(command, list) else command}", "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {command[0] if isinstance(command, list) else command}"
            if e.stderr and e.stderr.strip():
                error_msg += f" - {e.stderr.strip()[:100]}"
            if e.returncode == 5:
                error_msg += " (Access denied - requires administrator)"
            elif e.returncode == 1:
                error_msg += " (General error)"
            self.log_message(error_msg, "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None
            
        except Exception as e:
            self.log_message(f"Unexpected error executing command: {str(e)[:100]}", "critical")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()
            return None

    def clean_directory_contents(self, path, description=""):
        if self.stop_cleaning_event.is_set(): 
            return
            
        if not os.path.exists(path):
            if self.settings['log_level'] == 'verbose':
                self.log_message(f"Directory not found: \"{path}\"", "warning")
            return
            
        self.log_message(f"Scanning: \"{path}\"...", "scan")
        
        items_deleted = 0
        folders_deleted = 0
        space_freed = 0
        
        try:
            items_to_delete = []
            for item_name in os.listdir(path):
                if self.stop_cleaning_event.is_set(): 
                    return
                items_to_delete.append(item_name)
            
            for item_name in items_to_delete:
                if self.stop_cleaning_event.is_set(): 
                    return
                    
                item_path = os.path.join(path, item_name)
                
                try:
                    if "_MEI" in item_path or "python" in item_path.lower():
                        continue
                        
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        try:
                            size = os.path.getsize(item_path)
                        except Exception:
                            size = 0
                        os.unlink(item_path)
                        items_deleted += 1
                        space_freed += size
                        
                    elif os.path.isdir(item_path):
                        dir_size = self._get_dir_size(item_path)
                        shutil.rmtree(item_path, ignore_errors=True)
                        folders_deleted += 1
                        space_freed += dir_size
                        
                except PermissionError:
                    if self.settings['log_level'] == 'verbose':
                        self.log_message(f"Permission denied: {item_name}", "warning")
                    self.cleaning_stats['errors'] += 1
                    
                except FileNotFoundError:
                    continue
                    
                except Exception as e:
                    if "Access is denied" in str(e):
                        if self.settings['log_level'] == 'verbose':
                            self.log_message(f"Access denied: {item_name}", "warning")
                        self.cleaning_stats['errors'] += 1
                    else:
                        self.log_message(f"Failed to delete {item_name}: {str(e)[:50]}", "warning")
                        self.cleaning_stats['errors'] += 1
            
            self.cleaning_stats['files_deleted'] += items_deleted
            self.cleaning_stats['folders_cleaned'] += folders_deleted
            self.session_space_saved = getattr(self, 'session_space_saved', 0) + space_freed
            self.update_stats_display()
            
            if items_deleted > 0 or folders_deleted > 0:
                self.log_message(f"✓ Cleaned \"{os.path.basename(path)}\": {items_deleted} files, {folders_deleted} folders ({self._format_size(space_freed)})", "success")
            else:
                if self.settings['log_level'] == 'verbose':
                    self.log_message(f"No items to clean in \"{os.path.basename(path)}\"", "info")
                    
        except Exception as e:
            self.log_message(f"Failed to access directory \"{path}\": {str(e)[:100]}", "error")
            self.cleaning_stats['errors'] += 1
            self.update_stats_display()

    def _get_dir_size(self, path):
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        if os.path.exists(fp):
                            total += os.path.getsize(fp)
                    except (OSError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total

    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _clean_temp_files(self):
        temp_dirs = [
            os.environ.get('TEMP'),
            os.environ.get('TMP'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp')
        ]
        
        for temp_dir in temp_dirs:
            if self.stop_cleaning_event.is_set(): 
                return
            if temp_dir and os.path.exists(temp_dir):
                self.clean_directory_contents(temp_dir)

    def _clean_update_cache(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        update_paths = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution', 'Download'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution', 'DataStore')
        ]
        
        for path in update_paths:
            if self.stop_cleaning_event.is_set(): 
                return
            if os.path.exists(path):
                self.clean_directory_contents(path)

    def _clean_prefetch(self):
        if self.stop_cleaning_event.is_set(): 
            return
        win_prefetch = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
        if os.path.exists(win_prefetch):
            self.clean_directory_contents(win_prefetch)

    def _empty_recycle_bin(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        self.log_message("Emptying Recycle Bin...", "process")
        
        result = self.run_command(["powershell.exe", "-command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
        
        if not result or result.returncode != 0:
            for drive in ['C:', 'D:', 'E:', 'F:']:
                recycle_path = f"{drive}\\$Recycle.Bin"
                if os.path.exists(recycle_path):
                    self.run_command(f'rd /s /q "{recycle_path}" 2>nul', shell=True)
        
        self.log_message("Recycle bin emptied", "success")

    def _flush_dns(self):
        if self.stop_cleaning_event.is_set(): 
            return
        self.log_message("Flushing DNS cache...", "process")
        result = self.run_command(["ipconfig", "/flushdns"])
        if result and result.returncode == 0:
            self.log_message("DNS cache cleared successfully", "success")
        else:
            self.log_message("Failed to clear DNS cache", "error")

    def _clean_browsers(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        browsers = {
            "Chrome": self._clean_chrome,
            "Firefox": self._clean_firefox,
            "Edge": self._clean_edge,
            "Opera": self._clean_opera,
        }
        
        self.log_message("Initiating browser cache cleanup...", "info")
        
        if self.settings['auto_close_browsers']:
            self._close_browsers()
        
        for browser_name, clean_func in browsers.items():
            if self.stop_cleaning_event.is_set(): 
                break
            self.log_message(f"Cleaning {browser_name} cache...", "process")
            try:
                clean_func()
            except Exception as e:
                self.log_message(f"Error cleaning {browser_name}: {str(e)[:50]}", "error")
                self.cleaning_stats['errors'] += 1
                self.update_stats_display()

    def _close_browsers(self):
        browsers_to_close = [
            "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe",
            "iexplore.exe", "brave.exe", "vivaldi.exe"
        ]
        
        self.log_message("Closing browser processes...", "process")
        for browser in browsers_to_close:
            try:
                self.run_command(f"taskkill /f /im {browser} /t", shell=True)
            except Exception:
                pass 
        time.sleep(2)

    def _clean_chrome(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        chrome_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data', 'Default'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data', 'Profile 1'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data', 'Guest Profile')
        ]
        
        chrome_caches = ['Cache', 'Code Cache', 'GPUCache', 'Media Cache', 
                         'Service Worker\\CacheStorage', 'Application Cache']
        
        for chrome_data in chrome_paths:
            if self.stop_cleaning_event.is_set(): 
                return
            if not os.path.exists(chrome_data):
                continue
                
            for cache in chrome_caches:
                if self.stop_cleaning_event.is_set(): 
                    return
                cache_path = os.path.join(chrome_data, cache)
                if os.path.exists(cache_path):
                    self.clean_directory_contents(cache_path)

    def _clean_firefox(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        firefox_profiles_base = os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
        if not os.path.exists(firefox_profiles_base):
            self.log_message("Firefox profile directory not found", "warning")
            return
            
        try:
            for profile_dir in os.listdir(firefox_profiles_base):
                if self.stop_cleaning_event.is_set(): 
                    return
                profile_path = os.path.join(firefox_profiles_base, profile_dir)
                if os.path.isdir(profile_path):
                    cache_dirs = ['cache2', 'startupCache', 'OfflineCache']
                    for cache_dir in cache_dirs:
                        cache_path = os.path.join(profile_path, cache_dir)
                        if os.path.exists(cache_path):
                            self.clean_directory_contents(cache_path)
        except Exception as e:
            self.log_message(f"Error accessing Firefox profiles: {str(e)[:50]}", "error")

    def _clean_edge(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        edge_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data', 'Default'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data', 'Profile 1')
        ]
        
        edge_caches = ['Cache', 'Code Cache', 'GPUCache', 'Media Cache', 
                       'Service Worker\\CacheStorage', 'Application Cache']
        
        for edge_data in edge_paths:
            if self.stop_cleaning_event.is_set(): 
                return
            if not os.path.exists(edge_data):
                continue
                
            for cache in edge_caches:
                if self.stop_cleaning_event.is_set(): 
                    return
                cache_path = os.path.join(edge_data, cache)
                if os.path.exists(cache_path):
                    self.clean_directory_contents(cache_path)

    def _clean_opera(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        opera_paths = [
            os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera Stable'),
            os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera GX Stable')
        ]
        
        opera_caches = ['Cache', 'GPUCache', 'Media Cache', 'Application Cache']
        
        for opera_data in opera_paths:
            if self.stop_cleaning_event.is_set(): 
                return
            if not os.path.exists(opera_data):
                continue
                
            for cache in opera_caches:
                if self.stop_cleaning_event.is_set(): 
                    return
                cache_path = os.path.join(opera_data, cache)
                if os.path.exists(cache_path):
                    self.clean_directory_contents(cache_path)

    def _clean_event_logs(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        if not self.is_admin:
            self.log_message("Event log cleanup skipped (requires administrator)", "warning")
            return
            
        self.log_message("Clearing Windows Event Logs...", "process")
        event_logs = ["Application", "Security", "System", "Setup", "Windows PowerShell"]
        
        for log_name in event_logs:
            if self.stop_cleaning_event.is_set(): 
                return
            self.log_message(f"Clearing {log_name} log...", "process")
            result = self.run_command(["wevtutil", "cl", log_name])
            if result and result.returncode == 0:
                self.log_message(f"✓ {log_name} log cleared", "success")
            else:
                self.log_message(f"✗ Failed to clear {log_name} log", "error")

    def _clean_thumbnails(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        self.log_message("Cleaning Windows Thumbnail Cache...", "process")
        thumb_cache_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer')
        
        if not os.path.exists(thumb_cache_dir):
            self.log_message("Thumbnail cache directory not found", "warning")
            return
            
        thumb_cache_pattern = os.path.join(thumb_cache_dir, 'thumbcache_*.db')
        found_thumbs = glob.glob(thumb_cache_pattern)
        
        if found_thumbs:
            self.log_message(f"Removing {len(found_thumbs)} thumbnail cache files...", "process")
            deleted_count = 0
            space_freed = 0
            
            for thumb_file in found_thumbs:
                if self.stop_cleaning_event.is_set(): 
                    return
                try:
                    size = os.path.getsize(thumb_file)
                    os.unlink(thumb_file)
                    deleted_count += 1
                    space_freed += size
                except Exception as e:
                    if self.settings['log_level'] == 'verbose':
                        self.log_message(f"Failed to delete thumbnail: {str(e)[:50]}", "warning")
                    self.cleaning_stats['errors'] += 1
            
            if deleted_count > 0:
                self.cleaning_stats['files_deleted'] += deleted_count
                self.session_space_saved = getattr(self, 'session_space_saved', 0) + space_freed
                self.update_stats_display()
                self.log_message(f"✓ Thumbnail cache cleared: {deleted_count} files ({self._format_size(space_freed)})", "success")
        else:
            self.log_message("No thumbnail cache files found", "info")

    def _clean_font_cache(self):
        if self.stop_cleaning_event.is_set(): 
            return
            
        if not self.is_admin:
            self.log_message("Font cache cleanup skipped (requires administrator)", "warning")
            return
            
        self.log_message("Cleaning Windows Font Cache...", "process")
        
        self.run_command(["net", "stop", "FontCache"])
        time.sleep(1)
        
        font_cache_paths = [
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'ServiceProfiles', 'LocalService', 'AppData', 'Local', 'FontCache'),
            os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'FNTCACHE.DAT')
        ]
        
        for path in font_cache_paths:
            if self.stop_cleaning_event.is_set(): 
                return
            if os.path.exists(path):
                if os.path.isfile(path):
                    try:
                        os.unlink(path)
                        self.log_message(f"✓ Deleted font cache file: {os.path.basename(path)}", "success")
                    except Exception as e:
                        self.log_message(f"Failed to delete font cache: {str(e)[:50]}", "error")
                else:
                    self.clean_directory_contents(path)
        
        self.run_command(["net", "start", "FontCache"])
        self.log_message("Font cache service restarted", "success")

    def _run_disk_cleanup(self):
        if self.stop_cleaning_event.is_set():
            return
            
        if not self.is_admin:
            self.log_message("Disk Cleanup tool skipped (requires administrator)", "warning")
            return
            
        self.log_message("Running built-in Disk Cleanup (this may take a while)...", "process")
        self.log_message("This uses pre-configured settings. Run 'cleanmgr.exe /sageset:1' manually to change them.", "info")

        result = self.run_command("cleanmgr.exe /sagerun:1", shell=True, timeout=300)
        
        if result and result.returncode == 0:
            self.log_message("✓ Disk Cleanup completed successfully", "success")
        else:
            self.log_message("Disk Cleanup finished. It might have been skipped or timed out.", "warning")

    def check_admin_privileges(self):
        try:
            result = subprocess.run(["net", "session"], check=True, 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                    text=True, timeout=5)
            self.log_message("Administrator privileges detected", "success")
            return True
            
        except subprocess.CalledProcessError:
            self.log_message("Running without administrator privileges", "warning")
            if not self.admin_warning_shown:
                messagebox.showwarning(
                    "Administrator Required", 
                    "This application is not running with administrator privileges.\n\n"
                    "Some advanced cleanup functions may not work:\n"
                    "• Event Logs clearing\n"
                    "• Disk Cleanup tool\n"
                    "• DNS Flush\n"
                    "• Font Cache cleaning\n\n"
                    "Please run as administrator for full functionality.")
                self.admin_warning_shown = True
            self.clean_button.config(bg="#d29922")
            return False
            
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.log_message("Cannot verify admin privileges", "error")
            return False

    def on_closing(self):
        if self.cleaning_active:
            if messagebox.askokcancel("Quit", "Cleanup is running. Do you want to stop and quit?"):
                self.stop_cleaning_event.set()
                self.cleaning_active = False
                time.sleep(1)
                self.save_settings()
                self.master.destroy()
        else:
            self.save_settings()
            self.master.destroy()

def main():
    root = tk.Tk()
    app = ScruboApp(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        app.save_settings()
    except Exception as e:
        print(f"Unexpected error: {e}")
        messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{e}")
        app.save_settings()

if __name__ == "__main__":
    main()