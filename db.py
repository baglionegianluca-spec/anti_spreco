import psycopg2
import psycopg2.extras
import os

# Recupera la variabile ambiente impostata su Render
DATABASE_URL = os.getenv("DATABASE_URL")


# --- Connessione al DB ---
def get_db():
    return psycopg2.connect(DATABASE_URL)


# --- Aggiunta nuovo prodotto ---
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


# --- Ottenere tutti i prodotti (ritorna DIZIONARI!) ---
def get_all_products():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, name, barcode, brand, category, image_url, quantity, expiry_date
        FROM products
        ORDER BY expiry_date ASC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# --- Aggiornare un prodotto esistente ---
def update_product(product_id, name, barcode, brand, category, image_url, quantity, expiry_date):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products SET
            name=%s, barcode=%s, brand=%s, category=%s, image_url=%s,
            quantity=%s, expiry_date=%s
        WHERE id=%s
    """, (name, barcode, brand, category, image_url, quantity, expiry_date, product_id))

    conn.commit()
    cur.close()
    conn.close()


# --- Ottenere un singolo prodotto ---
def get_product(product_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cur.fetchone()

    cur.close()
    conn.close()

    return product
