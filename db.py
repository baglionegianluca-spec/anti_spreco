import sqlite3
from datetime import datetime

DB_PATH = "data.db"

def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT,
            brand TEXT,
            category TEXT,
            image_url TEXT,
            quantity INTEGER DEFAULT 1,
            expiry_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def add_product(conn, name, barcode, brand, category, image_url, quantity, expiry_date):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (name, barcode, brand, category, image_url, quantity, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, barcode, brand, category, image_url, quantity, expiry_date))
    conn.commit()

def get_all_products(conn):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, barcode, brand, category, image_url, quantity, expiry_date
        FROM products
        ORDER BY expiry_date ASC
    """)
    return cursor.fetchall()

