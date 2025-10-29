<html>
<head>
  <meta name="google-site-verification" content="1APVEnM8wSQRpS0nZekQOzOfjUq47UExustnF_VTgZU" />
</head>
<body>
  <h1>XcelSync</h1>
  <p>Excel/CSV Database Automation Tool</p>
  <p>XcelSync is a lightweight automation tool that synchronizes and imports Excel data into databases using a hybrid Bash + Python pipeline.  
It’s built for data engineers, analysts, and developers who need a reliable, scriptable import workflow.</p>
</body>
</html>

## 🚀 Features

- 🔹 Simple launcher: `xcelsync.sh`
- 🔹 Modular Python backend (`main.py`, `importer.py`, `logger.py`)
- 🔹 Automated logging with status tracking
- 🔹 Supports MySQL, PostgreSQL, and SQLite
- 🔹 Handles UTF-8 and fallback encodings automatically
- 🔹 Clean and readable CLI logs
- 🔹 Automaic Sheet Detections and Sheets Are Inserted As Table In Database

---

## 📦 Installation

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
main.py → controls overall execution
importer.py → processes and imports Excel data
logger.py → handles structured logging and output**

## 🧰 Project Structure
```bash
.
├── xcelsync.sh         # Main entry point (bash automation)
├── main.py             # Core controller
├── importer.py         # Handles Excel-to-database import
├── logger.py           # Logging utility
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```
