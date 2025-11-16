# 🧩 XcelSync

**XcelSync** is a lightweight automation tool that synchronizes and imports Excel data into databases using a hybrid Python + Shell + Batch pipeline.
Now available for both Windows and Linux — one repository, two releases, Cross-Platform supported.

---
## 🚀 Features

-  🖥️ Cross-platform support (Windows + Linux)
-  📊 Supports MySQL, PostgreSQL, and SQLite
- 🔹 Simple launchers:
-  * `xcelsync.sh` → Linux/macOS **(CLI)**
   * `xcelsync.bat` → Windows **(Web-based GUI)***
   * `web_app.py` → To start web-based GUI
-  🧩 Modular Python backend (`main.py`, `importer.py`, `logger.py`) & `web_app.py` for Python(cross-platoform  eg:- windows,linux/debian,etc..)
- 🔹 Automated logging with status tracking
-  🧠 Web-based UI (Flask) in Windows edition
-  🔐 Handles encoding and logging with precision
- 🔹 Clean and readable CLI logs
-  💾 Imports Excel sheets as tables automatically

---

## Installation

### Windows
### 1️⃣ Download the Cross-Platform Version
**[XcelSync-CrossPlatform]**(https://github.com/ad1xmohd/XcelSync/releases/download/XcelSync/XcelSync-CrossPlatform.zip)
### 2️⃣ Double click xcelsync.bat
It will start to Detect wheather Python installed or not. Sometimes it will automatically install Python if its not installed Automatically You have to Install it from [python.org](https://www.python.org/downloads/windows/). Make sure it is Python3.3+
**THE CROSSPLATFORM VERSION CAN BE USED ALSO IN LINUX/WINDOWS/MacOS(not-tested) it runs on Python3 + HTML,css,js for Web-Based GUI**

### LINUX

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/ad1xmohd/XcelSync.git
cd XcelSync
```
### 2️⃣ Install Python Dependencies
```bash
pip install -r requirements.txt --break-system-packages
```
## 💡 -(Optional TIP): Use a virtual environment for isolated installs.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### 3️⃣ Make the Shell Script Executable
```bash
chmod +x xcelsync.sh
```

### ⚙️ Usage
**RUN THE MAIN SCRIPT**
```bash
./xcelsync.sh
```
**Under the Hood, `xcelsync.sh` orchestrates Python modules such as:
main.py → controls overall execution.
importer.py → processes and imports Excel data.
logger.py → handles structured logging and output.**

## 🧰 Project Structure(Linux Version)
```bash
.
├── LICENSE             # Non-Commercial, Restricted MIT Variant
├── xcelsync.sh         # Main entry point (bash automation)
├── main.py             # Core controller
├── importer.py         # Handles Excel-to-database import
├── logger.py           # Logging utility
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```
## 🧰 Project Structure(Windows/Cross-Platform Version)
```
.
├── LICENSE                # Non-Commercial, Restricted MIT Variant
├── windows.bat            # Windows launcher (auto-installer)
├── main.py                # Core controller
├── importer.py            # Excel import handler
├── logger.py              # Logging utility
├── web_app.py             # Web-Based GUI and FLASK API
├── requirements.txt       # Python dependencies
└── README.md              # Documentation
```
