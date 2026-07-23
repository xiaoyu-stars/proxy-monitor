import sqlite3
import threading
from datetime import datetime

DB_PATH = "monitor_data.db"
_lock = threading.Lock()

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ping_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            avg_ms REAL,
            min_ms REAL,
            max_ms REAL,
            std_dev REAL,
            loss_pct REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tcp_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            port INTEGER,
            connected INTEGER,
            connect_time_ms REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS http_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            url TEXT,
            status_code INTEGER,
            response_time_ms REAL,
            success INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS speed_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            download_mbps REAL,
            upload_mbps REAL
        )
    """)
    conn.commit()
    conn.close()

def insert_ping(avg_ms, min_ms, max_ms, std_dev, loss_pct):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO ping_results (avg_ms, min_ms, max_ms, std_dev, loss_pct) VALUES (?,?,?,?,?)",
            (avg_ms or 0, min_ms or 0, max_ms or 0, std_dev or 0, loss_pct or 0)
        )
        conn.commit()
        conn.close()

def insert_tcp(port, connected, connect_time_ms):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO tcp_results (port, connected, connect_time_ms) VALUES (?,?,?)",
            (port, connected, connect_time_ms or 0)
        )
        conn.commit()
        conn.close()

def insert_http(url, status_code, response_time_ms, success):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO http_results (url, status_code, response_time_ms, success) VALUES (?,?,?,?)",
            (url, status_code or 0, response_time_ms or 0, 1 if success else 0)
        )
        conn.commit()
        conn.close()

def insert_speed(download_mbps, upload_mbps):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO speed_results (download_mbps, upload_mbps) VALUES (?,?)",
            (download_mbps or 0, upload_mbps or 0)
        )
        conn.commit()
        conn.close()

def query_speed(hours=24):
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, download_mbps, upload_mbps FROM speed_results WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC",
        (f'-{hours} hours',)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def query_latest_speed():
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, download_mbps, upload_mbps FROM speed_results ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row

def query_ping(hours=24):
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, avg_ms, min_ms, max_ms, std_dev, loss_pct FROM ping_results WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC",
        (f'-{hours} hours',)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def query_tcp(hours=24):
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, port, connected, connect_time_ms FROM tcp_results WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC",
        (f'-{hours} hours',)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def query_http(hours=24):
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, url, status_code, response_time_ms, success FROM http_results WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC",
        (f'-{hours} hours',)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def query_latest_ping():
    conn = get_conn()
    cur = conn.execute(
        "SELECT timestamp, avg_ms, min_ms, max_ms, std_dev, loss_pct FROM ping_results ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row

def query_latest_tcp():
    conn = get_conn()
    cur = conn.execute(
        "SELECT port, connected, connect_time_ms FROM tcp_results WHERE id IN (SELECT MAX(id) FROM tcp_results GROUP BY port)"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def query_latest_http():
    conn = get_conn()
    cur = conn.execute(
        "SELECT url, status_code, response_time_ms, success FROM http_results WHERE id IN (SELECT MAX(id) FROM http_results GROUP BY url)"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def cleanup(days=30):
    with _lock:
        conn = get_conn()
        for table in ['ping_results', 'tcp_results', 'http_results', 'speed_results']:
            conn.execute(f"DELETE FROM {table} WHERE timestamp < datetime('now', ?)", (f'-{days} days',))
        conn.commit()
        conn.close()
