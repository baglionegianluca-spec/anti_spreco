import sqlite3
from datetime import datetime
from telegram_utils import (
    send_telegram_message,
    send_telegram_photo,
    send_telegram_buttons
)

DB_PATH = "data.db"   # nome del tuo database

def check_expiries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today = datetime.now().date()

    # Recupero tutti i prodotti con una data presente
    cur.execute("""
        SELECT id, name, expiry_date, quantity, image_url
        FROM products
        WHERE expiry_date IS NOT NULL AND expiry_date != ''
    """)

    rows = cur.fetchall()

    for row in rows:
        pid = row["id"]
        name = row["name"]
        qty = row["quantity"]
        expiry_raw = row["expiry_date"]
        image_url = row["image_url"]

        # Normalizzazione formati data
        expiry = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                expiry = datetime.strptime(expiry_raw, fmt).date()
                break
            except:
                continue

        if not expiry:
            continue

        delta = (expiry - today).days

        # Testo della notifica
        def build_caption(prefix):
            return (
                f"{prefix}\n"
                f"📦 *{name}*\n"
                f"📅 Scadenza: *{expiry_raw}*\n"
                f"🔢 Quantità: *{qty}*"
            )

        # Creazione bottoni interattivi
        buttons = [
            [
                {"text": "✓ Consumato", "callback_data": f"consumato_{pid}"},
                {"text": "🗑️ Elimina", "callback_data": f"elimina_{pid}"}
            ]
        ]

        # Logica scadenze
        if delta == 7:
            caption = build_caption("🟡 *Avviso Scadenza (7 giorni)*")
        elif delta == 3:
            caption = build_caption("🟠 *In scadenza tra 3 giorni!*")
        elif delta < 0:
            caption = build_caption("🔴 *PRODOTTO SCADUTO!*")
        else:
            continue  # Nessuna notifica

        # Invio notifica SENZA bottoni
        if image_url and image_url.strip() != "":
            send_telegram_photo(image_url, caption)
        else:
            send_telegram_message(caption)


    conn.close()


# Se lanci direttamente lo script, esegue check_expiries()
if __name__ == "__main__":
    check_expiries()
