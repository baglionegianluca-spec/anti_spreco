import requests
import os

BOT_TOKEN = "8214545100:AAFSL84GxS2wtM47srfeFp-9t3qWbcml1Aw"
CHAT_ID = "606221953"


# ============================================
#  INVIO MESSAGGIO TESTO
# ============================================
def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram non configurato correttamente")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Errore Telegram:", e)



# ============================================
#  INVIO FOTO + DIDASCALIA
# ============================================
def send_telegram_photo(image_url, caption):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram non configurato correttamente")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Errore Telegram:", e)



# ============================================
#  INVIO NOTIFICA IMMEDIATA SINGOLO PRODOTTO
# ============================================
def send_expiry_alert_now(name, expiry_raw, quantity, image_url):
    """Notifica immediata appena un prodotto è aggiunto."""
    from datetime import datetime, date

    if not expiry_raw:
        return

    # Normalizza la data
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

    # Costruzione messaggio
    def build_caption(prefix):
        return (
            f"{prefix}\n"
            f"📦 *{name}*\n"
            f"📅 Scadenza: *{expiry_raw}*\n"
            f"🔢 Quantità: *{quantity}*"
        )

    # Regole notifica
    if delta < 0:
        caption = build_caption("🔴 *PRODOTTO SCADUTO!*")
    elif delta == 0:
        caption = build_caption("🟠 *Scade OGGI!*")
    else:
        return

    # Invio
    if image_url:
        send_telegram_photo(image_url, caption)
    else:
        send_telegram_message(caption)
