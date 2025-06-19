import sqlite3
import os
from datetime import datetime

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            login_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_user(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        c.execute("INSERT OR IGNORE INTO users (username, login_time) VALUES (?, ?)", (username, now))
        c.execute("UPDATE users SET login_time = ? WHERE username = ?", (now, username))
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, login_time FROM users")
    users = c.fetchall()
    conn.close()
    return users
