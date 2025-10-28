# importer.py - core Excel -> MySQL synchronization logic
import os
import re
import time
import pandas as pd
import numpy as np
from logger import vlog
import mysql.connector
from mysql.connector import errorcode

def sanitize_identifier(name: str) -> str:
    if name is None:
        return ""
    n = str(name).strip()
    n = re.sub(r"[^0-9A-Za-z_]", "_", n)
    n = n[:64]
    if n == "":
        n = "col"
    return n

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    cols = list(df2.columns)
    new_cols = []
    for i, c in enumerate(cols):
        if pd.isna(c) or str(c).strip() == "":
            if df2.iloc[:, i].isnull().all():
                new_cols.append(None)
            else:
                new_cols.append(f"column_{i+1}")
        else:
            new_cols.append(str(c).strip())
    keep = []
    keep_names = []
    for i, nm in enumerate(new_cols):
        if nm is None:
            if not df2.iloc[:, i].isnull().all():
                keep.append(i); keep_names.append(f"column_{i+1}")
        else:
            keep.append(i); keep_names.append(nm)
    df3 = df2.iloc[:, keep].copy()
    df3.columns = [sanitize_identifier(c) or f"column_{i+1}" for i, c in enumerate(keep_names)]
    df3 = df3.where(pd.notnull(df3), None)
    for col in df3.select_dtypes(include=["object"]).columns:
        df3[col] = df3[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df3

def infer_sql_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "TEXT"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DATETIME"
    if pd.api.types.is_integer_dtype(non_null) or pd.api.types.is_float_dtype(non_null):
        return "DOUBLE"
    try:
        pd.to_datetime(non_null.sample(min(10, len(non_null))))
        return "DATETIME"
    except Exception:
        pass
    return "TEXT"

def ensure_table_and_columns(cur, conn, table_name: str, df: pd.DataFrame):
    safe_table = sanitize_identifier(table_name)
    cur.execute("SHOW TABLES LIKE %s", (safe_table,))
    exists = cur.fetchone()
    if not exists:
        col_defs = []
        for c in df.columns:
            col_type = infer_sql_type(df[c])
            col_defs.append(f"`{c}` {col_type}")
        sql = f"CREATE TABLE `{safe_table}` ({', '.join(col_defs)}) ENGINE=InnoDB"
        cur.execute(sql)
        conn.commit()
        vlog(f"Created table `{safe_table}` with {len(df.columns)} columns", "SUCCESS")
    else:
        cur.execute(f"SHOW COLUMNS FROM `{safe_table}`")
        existing = [row[0] for row in cur.fetchall()]
        for c in df.columns:
            if c not in existing:
                col_type = infer_sql_type(df[c])
                alter = f"ALTER TABLE `{safe_table}` ADD COLUMN `{c}` {col_type}"
                cur.execute(alter)
                conn.commit()
                vlog(f"Added missing column `{c}` to `{safe_table}`", "INFO")

def find_id_column(df):
    for c in df.columns:
        if re.search(r"\bid\b", c, re.IGNORECASE):
            return c
    return None

def create_unique_index_if_needed(cur, conn, table_name, id_col):
    if not id_col:
        return False
    try:
        cur.execute("SHOW INDEX FROM `{}` WHERE Column_name = %s".format(sanitize_identifier(table_name)), (id_col,))
        if cur.fetchone():
            return True
    except Exception:
        pass
    try:
        cur.execute(f"ALTER TABLE `{sanitize_identifier(table_name)}` ADD UNIQUE INDEX `{id_col}_unq` (`{id_col}`)")
        conn.commit()
        vlog(f"Created UNIQUE index on `{table_name}`.`{id_col}`", "INFO")
        return True
    except mysql.connector.Error as e:
        vlog(f"Could not create unique index on `{id_col}`: {e}", "WARN")
        return False

def upsert_rows_batch(cur, conn, table_name: str, df: pd.DataFrame, id_col: str = None, batch_size: int = 500):
    columns = list(df.columns)
    col_sql = ", ".join([f"`{c}`" for c in columns])
    placeholders = ", ".join(["%s"] * len(columns))
    if id_col:
        update_pairs = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in columns if c != id_col])
        upsert_sql = f"INSERT INTO `{sanitize_identifier(table_name)}` ({col_sql}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_pairs}"
    else:
        upsert_sql = f"INSERT INTO `{sanitize_identifier(table_name)}` ({col_sql}) VALUES ({placeholders})"

    rows = [tuple((v.item() if isinstance(v, (np.generic,)) else v) for v in row) for _, row in df.iterrows()]
    inserted = 0; skipped = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        try:
            cur.executemany(upsert_sql, batch)
            conn.commit()
            inserted += len(batch)
        except mysql.connector.Error as e:
            vlog(f"Batch insert error at rows {i}-{i+len(batch)}: {e}", "WARN")
            for r in batch:
                try:
                    cur.execute(upsert_sql, r)
                    inserted += 1
                except mysql.connector.Error as e2:
                    vlog(f"Row insert failed: {e2}", "WARN")
                    skipped += 1
    return inserted, skipped
