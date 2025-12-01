import sqlite3
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler

from telegram_utils import (
    send_telegram_message,
    send_telegram_photo
)

DB_PATH = "data.db"


# ============================================
#  CHECK EXPIRIES (periodico)
# ============================================
def check_expiries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today = date.today()

    cur.execute("""
        SELECT id, name, expiry_date, quantity, image_url
        FROM products
        WHERE expiry_date IS NOT NULL AND expiry_date != ''
    """)
    rows = cur.fetchall()

    for row in rows:
        name = row["name"]
        qty = row["quantity"]
        expiry_raw = row["expiry_date"]
        image_url = row["image_url"]

        # Normalizzazione data
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

        # Costruzione testo
        def build_caption(prefix):
            return (
                f"{prefix}\n"
                f"📦 *{name}*\n"
                f"📅 Scadenza: *{expiry_raw}*\n"
                f"🔢 Quantità: *{qty}*"
            )

        # Regole notifiche periodiche
        if delta == 7:
            caption = build_caption("🟡 *Scadenza tra 7 giorni*")
        elif delta == 3:
            caption = build_caption("🟠 *Scadenza tra 3 giorni!*")
        elif delta == 1:
            caption = build_caption("🔴 *Scade DOMANI!*")
        else:
            continue

        if image_url:
            send_telegram_photo(image_url, caption)
        else:
            send_telegram_message(caption)

    conn.close()



# ============================================
#  NOTIFICA IMMEDIATA (usata da /add)
# ============================================
def notify_single_product(name, expiry_raw, quantity, image_url):
    """Invia una notifica appena un prodotto è aggiunto o modificato."""

    if not expiry_raw:
        return

    # Normalizza date
    expiry = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            expiry = datetime.strptime(expiry_raw, fmt).date()
            break
        except:
            continue

    if not expiry:
        return

    today = date.today()
    delta = (expiry - today).days

    # Notifiche immediate
    def build_caption(prefix):
        return (
            f"{prefix}\n"
            f"📦 *{name}*\n"
            f"📅 Scadenza: *{expiry_raw}*\n"
            f"🔢 Quantità: *{quantity}*"
        )

    if delta < 0:
        caption = build_caption("🔴 *PRODOTTO SCADUTO!*")
    elif delta == 0:
        caption = build_caption("🟠 *Scade OGGI!*")
    else:
        return  # non notificare se >0 giorni

    if image_url:
        send_telegram_photo(image_url, caption)
    else:
        send_telegram_message(caption)



# ============================================
#  SCHEDULER
# ============================================
scheduler = None

def setup_scheduler(app):
    global scheduler

    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(check_expiries, "interval", hours=6)  # controlla ogni 6 ore
        scheduler.start()

    # necessario per evitare che Flask blocchi lo scheduler
    @app.before_first_request
    def init_scheduler():
        pass
