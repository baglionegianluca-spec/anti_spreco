import psycopg2
import os

# Recupera la variabile ambiente impostata su Render
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)


def add_product(name, barcode, brand, category, image_url, quantity, expiry_date):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products (name, barcode, brand, category, image_url, quantity, expiry_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (name, barcode, brand, category, image_url, quantity, expiry_date))

    conn.commit()
    cur.close()
    conn.close()


def get_all_products():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, barcode, brand, category, image_url, quantity, expiry_date
        FROM products
        ORDER BY expiry_date ASC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows
