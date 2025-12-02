import psycopg2
import os

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
        ORDER BY expiry_date ASC NULLS LAST
    """)

    rows = cur.fetchall()

    # conversione tuple → dict
    col_names = [desc[0] for desc in cur.description]
    results = [dict(zip(col_names, r)) for r in rows]

    cur.close()
    conn.close()

    return results
