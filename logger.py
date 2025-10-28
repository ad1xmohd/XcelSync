# logger.py - centralized logging for XcelSync
from datetime import datetime
import os

try:
    from rich.console import Console
    USE_RICH = True
    console = Console()
except Exception:
    USE_RICH = False
    console = None

LOG_FILE = "./xcelsync.log"

def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def vlog(msg: str, level: str = "INFO"):
    line = f"[{now()}] {level}: {msg}"
    if USE_RICH:
        if level == "ERROR":
            console.print(f"[bold red]{line}[/]")
        elif level == "WARN":
            console.print(f"[yellow]{line}[/]")
        elif level == "SUCCESS":
            console.print(f"[green]{line}[/]")
        else:
            console.print(f"[cyan]{line}[/]")
    else:
        print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
