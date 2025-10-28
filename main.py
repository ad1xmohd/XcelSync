#!/usr/bin/env python3
"""
main.py — Enterprise-grade backend for XcelSync
"""

import os
import sys
import time
import base64
import pandas as pd
import mysql.connector
from datetime import datetime
from logger import vlog
from importer import (
    normalize_df, ensure_table_and_columns, find_id_column,
    create_unique_index_if_needed, upsert_rows_batch, sanitize_identifier
)

def get_password_from_env():
    """Decode DB password from environment variable."""
    b64 = os.environ.get("XCELSYNC_PASS_B64", "")
    if not b64:
        return ""
    try:
        return base64.b64decode(b64.encode()).decode()
    except Exception:
        return ""


def ssl_conf_from_flag(use_ssl, ssl_ca=None):
    """Build SSL config for mysql.connector."""
    v = (use_ssl or "").strip().lower()
    if v == "off":
        return {"ssl_disabled": True}
    elif v == "on":
        conf = {"ssl_disabled": False}
        if ssl_ca:
            conf["ssl_ca"] = ssl_ca
        return conf
    return {}

def try_connect(host, user, pwd, dbname=None, ssl_conf=None, timeout=10, retries=3):
    """
    Connects safely to MySQL/MariaDB.
    1. Probes version first (no charset).
    2. Chooses utf8mb4 or utf8 automatically.
    3. Retries on transient failures.
    """
    base_params = {
        "host": host,
        "user": user,
        "password": pwd,
        "connection_timeout": timeout,
    }
    if ssl_conf:
        base_params.update(ssl_conf)
    if dbname:
        base_params["database"] = dbname

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            conn_probe = mysql.connector.connect(**base_params)
            cur = conn_probe.cursor()
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
            cur.close()
            conn_probe.close()

            vlog(f"Detected MySQL/MariaDB version: {version}", "INFO")

            use_utf8 = False
            try:
                major, minor, *_ = [
                    int(x) for x in version.split()[0].split("-")[0].split(".")[:2]
                ]
                if major < 5 or (major == 5 and minor < 5):
                    use_utf8 = True
            except Exception:
                if "5.0" in version or "5.1" in version:
                    use_utf8 = True

            charset_choice = "utf8" if use_utf8 else "utf8mb4"
            vlog(f"Using charset: {charset_choice}", "INFO")

            conn_final = mysql.connector.connect(charset=charset_choice, **base_params)
            return conn_final

        except mysql.connector.Error as e:
            msg = str(e)
            if "Unknown character set" in msg or "utf8mb4" in msg:
                vlog("Server doesn't support utf8mb4 — retrying with utf8...", "WARN")
                try:
                    conn_final = mysql.connector.connect(charset="utf8", **base_params)
                    return conn_final
                except mysql.connector.Error as e2:
                    last_err = e2
            else:
                vlog(f"Connection attempt {attempt} failed: {e}", "WARN")
                last_err = e
                time.sleep(2 * attempt)
    return last_err

def show_connection_info(conn, host, user, ssl_conf):
    """Display connection info similar to the MariaDB monitor."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT CONNECTION_ID(), VERSION()")
        cid, version = cur.fetchone()
        vlog("Connected to MySQL Server successfully!", "SUCCESS")
        print("──────────────────────────────────────────────")
        print(f"Connection ID : {cid}")
        print(f"Server Version: {version}")
        print(f"User           : {user}")
        print(f"Host           : {host}")
        ssl_status = "Disabled" if (ssl_conf.get("ssl_disabled") if ssl_conf else True) else "Enabled"
        print(f"SSL            : {ssl_status}")
        print("──────────────────────────────────────────────")
        cur.close()
    except Exception as e:
        vlog(f"Could not fetch connection info: {e}", "WARN")

def ensure_database(host, user, pwd, dbname, ssl_conf):
    """
    Create the target database if missing, using correct charset.
    """
    vlog(f"Connecting to MySQL server {host} as {user}...", "INFO")
    conn = try_connect(host, user, pwd, None, ssl_conf)
    if isinstance(conn, Exception):
        vlog(f"Initial connection failed: {conn}", "ERROR")
        raise conn

    show_connection_info(conn, host, user, ssl_conf)
    vlog(f"Ensuring database '{dbname}' exists...", "INFO")

    cur = conn.cursor()
    try:
        try:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{sanitize_identifier(dbname)}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            conn.commit()
            vlog(f"Database '{dbname}' ready (utf8mb4).", "SUCCESS")
        except mysql.connector.Error as e:
            if "Unknown character set" in str(e) or "utf8mb4" in str(e):
                vlog("Server doesn't support utf8mb4 — retrying with utf8...", "WARN")
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{sanitize_identifier(dbname)}` "
                    "CHARACTER SET utf8 COLLATE utf8_general_ci;"
                )
                conn.commit()
                vlog(f"Database '{dbname}' ready (utf8 fallback).", "SUCCESS")
            else:
                raise
    except Exception as e:
        vlog(f"Database creation error: {e}", "ERROR")
        raise
    finally:
        cur.close()
        conn.close()

def import_flow(host, user, pwd, dbname, use_ssl, excel_path, tmp_dir):
    ssl_conf = ssl_conf_from_flag(use_ssl, os.environ.get("XCELSYNC_SSL_CA"))
    ensure_database(host, user, pwd, dbname, ssl_conf)
    conn = try_connect(host, user, pwd, dbname, ssl_conf)
    if isinstance(conn, Exception):
        vlog(f"Could not connect to DB '{dbname}': {conn}", "ERROR")
        return
    cur = conn.cursor()

    try:
        vlog(f"Reading Excel file: {excel_path}", "INFO")
        xl = pd.ExcelFile(excel_path)
        sheets = xl.sheet_names
        vlog(f"Found sheets: {sheets}", "INFO")
    except Exception as e:
        vlog(f"Failed to read Excel: {e}", "ERROR")
        return

    os.makedirs(tmp_dir, exist_ok=True)
    summaries = []
    for sheet in sheets:
        vlog(f"Processing sheet: {sheet}", "INFO")
        try:
            raw = xl.parse(sheet_name=sheet, dtype=object)
        except Exception as e:
            vlog(f"Could not parse sheet {sheet}: {e}", "WARN")
            continue

        df = normalize_df(raw)
        if df is None or df.empty:
            vlog(f"Sheet {sheet} empty after normalization. Skipping.", "WARN")
            continue

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_name = sanitize_identifier(sheet) or f"sheet_{int(time.time())}"
        backup_dir = os.path.join(tmp_dir, "backups", timestamp)
        os.makedirs(backup_dir, exist_ok=True)
        csv_path = os.path.join(backup_dir, f"{safe_name}.csv")
        try:
            df.to_csv(csv_path, index=False)
            vlog(f"Saved CSV backup: {csv_path}", "INFO")
        except Exception as e:
            vlog(f"Backup failed for {sheet}: {e}", "WARN")

        table_name = safe_name
        try:
            ensure_table_and_columns(cur, conn, table_name, df)
        except Exception as e:
            vlog(f"Failed ensure table: {e}", "ERROR")
            continue

        id_col = find_id_column(df)
        unique_created = False
        if id_col:
            unique_created = create_unique_index_if_needed(cur, conn, table_name, id_col)

        start = time.time()
        if id_col and unique_created:
            inserted, skipped = upsert_rows_batch(cur, conn, table_name, df, id_col)
        else:
            inserted, skipped = upsert_rows_batch(cur, conn, table_name, df, None)
        elapsed = time.time() - start
        summaries.append((sheet, len(df), inserted, skipped, elapsed))
        vlog(f"Sheet {sheet}: rows={len(df)}, inserted={inserted}, skipped={skipped}, secs={elapsed:.2f}", "SUCCESS")

    cur.close()
    conn.close()

    total_rows = total_ins = total_sk = total_secs = 0
    vlog("Import summary:", "INFO")
    for s, rows, ins, sk, secs in summaries:
        print(f" - {s}: rows={rows}, inserted={ins}, skipped={sk}, secs={secs:.2f}")
        total_rows += rows
        total_ins += ins
        total_sk += sk
        total_secs += secs
    print(f"Total rows: {total_rows}, Inserted: {total_ins}, Skipped: {total_sk}, Time: {total_secs:.2f}s")
    vlog("All sheets processed", "SUCCESS")

def test_connection_all(host, user, pwd, dbname, use_ssl):
    ssl_conf = ssl_conf_from_flag(use_ssl, os.environ.get("XCELSYNC_SSL_CA"))
    try:
        ensure_database(host, user, pwd, dbname, ssl_conf)
    except Exception as e:
        vlog(f"Could not ensure database: {e}", "ERROR")
        return False
    for cs in (None, "utf8mb4", "utf8"):
        c = try_connect(host, user, pwd, dbname, ssl_conf)
        if not isinstance(c, Exception):
            vlog(f"Connected using charset {cs or 'default'}", "SUCCESS")
            c.close()
            return True
        else:
            vlog(f"Attempt failed charset={cs or 'default'}: {c}", "WARN")
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: main.py <test|import> ...")
        sys.exit(1)
    mode = sys.argv[1]
    if mode not in ("test", "import"):
        print("Mode must be 'test' or 'import'")
        sys.exit(1)
    if len(sys.argv) < 7:
        print("Missing args")
        sys.exit(1)

    host, user, dbname, use_ssl, excel_path = sys.argv[2:7]
    tmp_dir = sys.argv[7] if len(sys.argv) >= 8 else "./tmp"
    pwd = get_password_from_env()
    if not pwd:
        vlog("No DB password provided via XCELSYNC_PASS_B64 env var", "ERROR")
        sys.exit(1)

    if mode == "test":
        ok = test_connection_all(host, user, pwd, dbname, use_ssl)
        sys.exit(0 if ok else 2)
    else:
        import_flow(host, user, pwd, dbname, use_ssl, excel_path, tmp_dir)


if __name__ == "__main__":
    main()
