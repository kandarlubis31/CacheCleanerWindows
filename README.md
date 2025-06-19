
-----

# WinClearCache Tool - DarkMatter

Selamat datang di **WinClearCache Tool - DarkMatter**\! Sebuah aplikasi pembersih sistem Windows yang dirancang dengan antarmuka futuristik, minimalis, dan sangat *user-friendly*. Ucapkan selamat tinggal pada *file-file* sampah yang membebani sistem Anda, dan sambut performa yang lebih responsif dengan sentuhan teknologi gelap yang menawan.

-----

## ✨ Fitur Unggulan

  * **Pembersihan Menyeluruh:** Target pembersihan mencakup:
      * File dan Direktori Sementara Windows (`%TEMP%`, `C:\Windows\Temp`, dll.)
      * *Cache* Pembaruan Windows (`SoftwareDistribution\Download`)
      * File *Prefetch* Windows
      * Keranjang Sampah (*Recycle Bin*)
      * *DNS Cache*
      * *Cache Browser* Populer (Chrome, Firefox, Edge, Opera)
      * *Windows Event Logs*
      * *Windows Thumbnail Cache*
      * Integrasi dengan Disk Cleanup bawaan Windows untuk opsi pembersihan mendalam.
  * **Antarmuka Futuristik (DarkMatter Theme):** Desain UI yang ramping dengan skema warna hitam, abu-abu metalik, dan aksen biru dingin yang memanjakan mata, memberikan pengalaman yang lebih modern.
  * **Statistik Real-time:** Pantau jumlah *file* yang dihapus, *folder* yang dibersihkan, dan *error* yang terjadi langsung di UI.
  * **Stop Pembersihan yang Aman:** Tombol `'STOP'` yang responsif memungkinkan Anda menghentikan proses pembersihan kapan saja.
  * **Mode Administrator Pintar:** Aplikasi akan mendeteksi jika dijalankan tanpa hak *administrator* dan secara cerdas melewati fungsi-fungsi yang memerlukannya, tanpa mengganggu proses lainnya. Peringatan akan ditampilkan di log.
  * **Portable (.exe):** Dapat dikompilasi menjadi satu *file* `.exe` mandiri menggunakan PyInstaller, sehingga mudah dijalankan di komputer manapun tanpa perlu instalasi Python.

-----

## 📸 Tampilan Aplikasi

*(Ganti URL ini dengan tautan ke screenshot aplikasi Anda di repository GitHub setelah Anda mengunggahnya)*

-----

## 🚀 Cara Menggunakan

### Persiapan Awal

  * **Unduh Aplikasi:**
      * Buka bagian [**Releases**](https://www.google.com/search?q=https://github.com/KandarLubis31/WinClearCache-Tool/releases) di repositori ini dan unduh *file* `.exe` versi terbaru.
  * **Atau, jika Anda ingin menjalankan dari *source code* Python:**
      * Pastikan Anda memiliki [Python 3.x](https://www.python.org/downloads/) terinstal di sistem Anda.
      * Instal *library* yang diperlukan: `pip install tkinter tk font subprocess os shutil glob threading time ctypes webbrowser datetime` (beberapa sudah bawaan Python, tapi ini untuk memastikan semuanya ada).

### Menjalankan Aplikasi

Aplikasi ini sangat direkomendasikan untuk dijalankan dengan hak akses *Administrator* agar dapat membersihkan *file-file* sistem yang dilindungi (seperti *Event Logs* dan *Disk Cleanup*).

  * **Jika Menggunakan File `.exe`:**

    1.  Temukan *file* `WinClearCache Tool - DarkMatter.exe` (atau nama lain yang Anda tentukan).
    2.  **Klik kanan** pada *file* tersebut.
    3.  Pilih **"Run as administrator"**.
    4.  Aplikasi akan terbuka. Klik tombol "🚀 INITIATE CLEANUP" untuk memulai.

  * **Jika Menjalankan dari *Source Code* Python:**

    1.  Buka **Command Prompt (CMD)** atau **PowerShell**.
    2.  **Penting:** Buka CMD/PowerShell **sebagai Administrator** (Klik kanan icon CMD/PowerShell di Start Menu, pilih "Run as administrator").
    3.  Arahkan ke folder tempat Anda menyimpan *file* `cleaner_app.py` menggunakan perintah `cd`:
        ```bash
        cd C:\Users\NamaAnda\ProyekAnda\WinClearCache-Tool
        ```
        *(Ganti `C:\Users\NamaAnda\ProyekAnda\WinClearCache-Tool` dengan *path* sebenarnya)*
    4.  Jalankan skrip Python:
        ```bash
        python cleaner_app.py
        ```
    5.  Aplikasi akan terbuka. Klik tombol "🚀 INITIATE CLEANUP" untuk memulai.

-----

## 🛠️ Pengembangan (Untuk Developer)

Jika Anda ingin memodifikasi atau berkontribusi pada proyek ini:

1.  **Clone Repositori:**
    ```bash
    git clone https://github.com/KandarLubis31/WinClearCache-Tool.git
    cd WinClearCache-Tool
    ```
2.  **Instal Dependensi:**
    ```bash
    pip install pyinstaller # Untuk mengkompilasi ke .exe
    ```
3.  **Kompilasi ke `.exe` (Setelah Modifikasi):**
    ```bash
    pyinstaller --onefile --windowed --icon=mulyno.ico cleaner_app.py
    ```
    *(Pastikan `mulyno.ico` ada di folder proyek Anda. Ganti `mulyno.ico` jika nama *icon* Anda berbeda).*
    File `.exe` yang sudah jadi akan ditemukan di folder `dist/`.

-----

## 📜 Lisensi

Proyek ini dilisensikan di bawah [MIT License](https://www.google.com/search?q=LICENSE). Anda bebas untuk menggunakan, memodifikasi, dan mendistribusikan kode ini.

-----

## 📞 Dukungan & Kontak

Jika Anda memiliki pertanyaan, saran, atau menemukan *bug*, jangan ragu untuk membuka *Issue* di repositori GitHub ini.

  * **GitHub:** [KandarLubis31](https://github.com/KandarLubis31)

-----

*Created with 💖 by KandarLubis*
