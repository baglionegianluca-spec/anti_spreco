from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date, timedelta
import os
from scheduler import setup_scheduler
from db import get_db, add_product, get_all_products
from dotenv import load_dotenv
from fpdf import FPDF
from psycopg2.extras import RealDictCursor


# force redeploy 3.0

# --- FOOD PLANNER IMPORT ---
from db_foodplanner import (
    init_foodplanner_tables,
    get_all_recipes,
    add_recipe,
    assign_recipe,
    get_day_plan,
    remove_planned_recipe,
    mark_meal_done,
    get_recipe_by_id,
    delete_recipe
)


# Carico variabili ambiente
load_dotenv()

# ✅ Inizializzo le tabelle del food planner PRIMA di creare l'app
init_foodplanner_tables()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chiave-segreta-cambia-questa")

APP_PASSWORD = os.getenv("APP_PASSWORD", "1234")


# ============================
#   LOGIN REQUIRED DECORATOR
# ============================

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# ============================
#   LOGIN / LOGOUT
# ============================
from flask import make_response

@app.route("/login", methods=["GET", "POST"])
def login():
    # Se l'utente è già loggato → vai in dashboard
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Password errata"

    # Disattiva cache per impedire il tasto 'indietro'
    response = make_response(render_template("login.html", error=error))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



# ============================
#   DASHBOARD
# ============================
@app.route("/")
@login_required
def dashboard():
    return render_template("menu.html")


# ============================
#   ANTI SPRECO
# ============================
@app.route("/anti-spreco")
@login_required
def anti_spreco_dashboard():
    products = get_all_products()

    today = date.today()
    total = len(products)
    expired = 0
    soon = 0
    fresh = 0

    for p in products:
        expiry = p["expiry_date"]
        if not expiry:
            fresh += 1
            continue

        try:
            exp_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            diff = (exp_date - today).days
        except:
            fresh += 1
            continue

        if diff < 0:
            expired += 1
        elif diff <= 3:
            soon += 1
        else:
            fresh += 1

    stats = {
        "total": total,
        "expired": expired,
        "soon": soon,
        "fresh": fresh
    }

    return render_template("dashboard.html", stats=stats)








# ============================
#   LISTA PRODOTTI
# ============================

from datetime import datetime, date

@app.route("/products")
@login_required
def products():
    rows = get_all_products()

    today = date.today()
    filter_type = request.args.get("filter")

    fixed = []
    for p in rows:
        expiry_raw = p["expiry_date"]
        diff = None

        if expiry_raw:
            # SUPPORTO A PIÙ FORMATI (Italia + HTML)
            date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

            expiry = None
            for fmt in date_formats:
                try:
                    expiry = datetime.strptime(expiry_raw, fmt).date()
                    break
                except:
                    continue

            if expiry:
                diff = (expiry - today).days

        fixed.append({
            "id": p["id"],
            "name": p["name"],
            "brand": p["brand"],
            "barcode": p["barcode"],
            "category": p["category"],
            "image_url": p["image_url"],
            "quantity": p["quantity"],
            "expiry_date": expiry_raw,
            "days_left": diff
        })

    # FILTRI
    if filter_type == "soon":
        fixed = [p for p in fixed if p["days_left"] is not None and 0 < p["days_left"] <= 14]

    elif filter_type == "expired":
        fixed = [p for p in fixed if p["days_left"] is not None and p["days_left"] < 0]

    elif filter_type == "fresh":
        fixed = [p for p in fixed if p["days_left"] is not None and p["days_left"] > 14]

    # Ordino sempre (prima i prodotti con data, poi gli altri)
    fixed.sort(key=lambda x: (x["days_left"] is None, x["days_left"]))

    # Titoli pagina
    titles = {
        None: "Tutti i prodotti",
        "soon": "In scadenza",
        "expired": "Scaduti",
        "fresh": "Freschi"
    }

    return render_template(
        "products.html",
        products=fixed,
        title=titles.get(filter_type),
        today=today
    )

# ============================
#   ADD PRODUCT (BASICO)
# ============================

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    conn = get_db()
    cur = conn.cursor()

    product_id = request.args.get("id")

    # ---------------------------------------------------
    # FUNZIONE NORMALIZZAZIONE DATE ITALIANE
    # ---------------------------------------------------
    import re
    from datetime import datetime
    import locale
    try:
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
    except:
        pass

    def normalize_date(d):
        if not d:
            return ""

        # HTML input (YYYY-MM-DD)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            return d

        # DD/MM/YYYY
        if re.match(r"^\d{2}/\d{2}/\d{4}$", d):
            day, month, year = d.split("/")
            return f"{year}-{month}-{day}"

        # DD-MM-YYYY
        if re.match(r"^\d{2}-\d{2}-\d{4}$", d):
            day, month, year = d.split("-")
            return f"{year}-{month}-{day}"

        # 28 nov 2025
        try:
            parsed = datetime.strptime(d, "%d %b %Y")
            return parsed.strftime("%Y-%m-%d")
        except:
            pass

        return ""

    # ---------------------------------------------------
    # POST → salvataggio (update o nuovo)
    # ---------------------------------------------------
    if request.method == "POST":
        name = request.form.get("name", "")
        barcode = request.form.get("barcode", "")
        brand = request.form.get("brand", "")
        category = request.form.get("category", "")
        image_url = request.form.get("image_url", "")
        quantity = int(request.form.get("quantity", "1") or 1)

        expiry_date_raw = request.form.get("expiry_date", "")
        expiry_date = normalize_date(expiry_date_raw)

        if product_id:
            cur.execute("""
                UPDATE products SET
                    name=%s, barcode=%s, brand=%s, category=%s, image_url=%s,
                    quantity=%s, expiry_date=%s
                WHERE id=%s
            """, (name, barcode, brand, category, image_url, quantity, expiry_date, product_id))
        else:
            cur.execute("""
                INSERT INTO products
                (name, barcode, brand, category, image_url, quantity, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, barcode, brand, category, image_url, quantity, expiry_date))

        conn.commit()

        # --- NOTIFICA IMMEDIATA ---
        from notifier import notify_single_product
        notify_single_product(name, expiry_date_raw, quantity, image_url)


        return redirect(url_for("products"))


    # ---------------------------------------------------
    # GET → modifica esistente
    # ---------------------------------------------------
    product = None
    if product_id:
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchone()

    # ---------------------------------------------------
    # GET → precompilazione da scanner (solo nuovi)
    # ---------------------------------------------------
    if product:
        name = product["name"]
        barcode = product["barcode"]
        brand = product["brand"]
        category = product["category"]
        image_url = product["image_url"]
        quantity = product["quantity"]
        expiry_date = product["expiry_date"]
    else:
        name = request.args.get("name", "")
        barcode = request.args.get("barcode", "")
        brand = request.args.get("brand", "")
        category = request.args.get("category", "")
        image_url = request.args.get("image_url", "")
        quantity = request.args.get("quantity", "1")
        expiry_date = request.args.get("expiry_date", "")

    # ---------------------------------------------------
    # RENDER TEMPLATE
    # ---------------------------------------------------
    return render_template(
        "add_product.html",
        name=name,
        barcode=barcode,
        brand=brand,
        category=category,
        image_url=image_url,
        quantity=quantity,
        expiry_date=expiry_date
    )

# =============================
# SCANNER
# =============================
@app.route("/scanner")
@login_required
def scanner():
    return render_template("scanner.html")

import requests

@app.route("/api/barcode_lookup", methods=["POST"])
@login_required
def barcode_lookup():
    data = request.get_json()
    barcode = data.get("barcode")

    if not barcode:
        return {"found": False}

    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    resp = requests.get(url).json()

    if resp.get("status") == 1:
        product = resp.get("product", {})

        expiry = product.get("expiration_date", "")   # spesso mancante su OFF

        image_url = (
            product.get("image_front_small_url")
            or product.get("image_front_url")
            or product.get("image_small_url")
            or ""
        )

        return {
            "found": True,
            "product": {
                "name": product.get("product_name", ""),
                "brand": product.get("brands", ""),
                "category": product.get("categories", ""),
                "image_url": image_url,
                "barcode": barcode,
                "expiry_date": expiry
            }
        }

    return {"found": False}


# ============================
#   ELIMINA
# ============================
@app.route("/delete/<int:product_id>")
@login_required
def delete_product(product_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    return redirect(url_for("products"))


# ============================
#   FOOD PLANNER (visualizzazione settimana)
# ============================
@app.route("/food-planner")
@login_required
def food_planner():
    # Giorni in minuscolo, come vengono salvati nel DB
    days_query = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

    # Giorni per mostrarli nel template
    days_display = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]

    week = {}

    for i, day_db in enumerate(days_query):

        day_plan = get_day_plan(day_db)  # <-- ORA CERCA IL GIORNO CORRETTO

        if day_plan:
            week[days_display[i]] = {
                "lunch_first": day_plan.get("lunch_first_name"),
                "lunch_second": day_plan.get("lunch_second_name"),
                "dinner_first": day_plan.get("dinner_first_name"),
                "dinner_second": day_plan.get("dinner_second_name")
            }
        else:
            week[days_display[i]] = {
                "lunch_first": None,
                "lunch_second": None,
                "dinner_first": None,
                "dinner_second": None
            }

    return render_template("food_planner.html", week=week)




@app.route("/food-planner/pdf")
@login_required
def food_planner_pdf():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    days_order = ["lunedì", "martedì", "mercoledì", "giovedì",
                  "venerdì", "sabato", "domenica"]

    cur.execute("""
        SELECT 
            mp.day_date,
            r1.name AS lunch_first,
            r2.name AS lunch_second,
            r3.name AS dinner_first,
            r4.name AS dinner_second
        FROM meal_plan_entries mp
        LEFT JOIN recipes r1 ON mp.lunch_first_recipe_id = r1.id
        LEFT JOIN recipes r2 ON mp.lunch_second_recipe_id = r2.id
        LEFT JOIN recipes r3 ON mp.dinner_first_recipe_id = r3.id
        LEFT JOIN recipes r4 ON mp.dinner_second_recipe_id = r4.id;
    """)

    rows = cur.fetchall()
    conn.close()

    # Prepara dati
    week = {d: {"lunch_first": "-", "lunch_second": "-", "dinner_first": "-", "dinner_second": "-"}
            for d in days_order}

    for row in rows:
        d = row["day_date"]
        if d in week:
            week[d]["lunch_first"] = row["lunch_first"] or "-"
            week[d]["lunch_second"] = row["lunch_second"] or "-"
            week[d]["dinner_first"] = row["dinner_first"] or "-"
            week[d]["dinner_second"] = row["dinner_second"] or "-"

    # === PDF ===
    pdf = FPDF("P", "mm", "A4")
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # HEADER
    pdf.set_fill_color(242, 242, 247)  # stile Apple
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 14, "Meal Planner Settimanale", ln=True, align="C", fill=True)
    pdf.ln(4)

    # TABella
    col_day = 35
    col_lunch = 75
    col_dinner = 75
    row_height = 12

    # Header colonne
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(col_day, row_height, "Giorno", 1, 0, "C", True)
    pdf.cell(col_lunch, row_height, "Pranzo", 1, 0, "C", True)
    pdf.cell(col_dinner, row_height, "Cena", 1, 1, "C", True)

    pdf.set_font("Arial", size=10)

    toggle = False

    for day in days_order:
        d = week[day]

        # Riga alternata
        if toggle:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        toggle = not toggle

        # Giorno
        pdf.cell(col_day, row_height, day.capitalize(), 1, 0, "C", True)

        # Pranzo (azzurro)
        pdf.set_fill_color(220, 238, 255)
        lunch_text = f"1º: {d['lunch_first']}\n2º: {d['lunch_second']}"
        pdf.multi_cell(col_lunch, row_height/2, lunch_text, border=1, align="L", fill=True, max_line_height=row_height/2)
        
        # ritorna a fianco
        pdf.set_xy(pdf.get_x() + col_day + col_lunch - col_lunch, pdf.get_y())

        # Cena (verde chiaro)
        pdf.set_fill_color(223, 255, 226)
        dinner_text = f"1º: {d['dinner_first']}\n2º: {d['dinner_second']}"
        pdf.multi_cell(col_dinner, row_height/2, dinner_text, border=1, align="L", fill=True, max_line_height=row_height/2)

    # Output finale
    pdf_bytes = pdf.output(dest="S")
    return bytes(pdf_bytes), 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=meal_planner.pdf"
    }

# ============================
#   AGGIUNGI / MODIFICA PASTO
# ============================

@app.route("/food-planner/add", methods=["GET", "POST"])
@login_required
def add_foodplanner():

    if request.method == "POST":
        day = request.form.get("day")

        lunch_first = request.form.get("lunch_first") or None
        lunch_second = request.form.get("lunch_second") or None
        dinner_first = request.form.get("dinner_first") or None
        dinner_second = request.form.get("dinner_second") or None

        assign_recipe(day, lunch_first, lunch_second, dinner_first, dinner_second)

        return redirect(url_for("food_planner"))

    days = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
    recipes = get_all_recipes()

    return render_template("planner.html", days=days, recipes=recipes)



# ============================
#   RIMUOVI PASTO
# ============================

@app.route("/food-planner/delete/<int:plan_id>")
@login_required
def food_planner_delete(plan_id):
    remove_planned_recipe(plan_id)
    return redirect(url_for("food_planner"))


# ============================
#   RICETTE
# ============================

@app.route("/recipes")
@login_required
def recipes():
    rows = get_all_recipes()
    return render_template("recipes.html", recipes=rows)


# ============================
#   AGGIUNGI RICETTA
# ============================

@app.route("/add_recipe", methods=["GET", "POST"])
@login_required
def add_recipe_route():
    if request.method == "POST":
        name = request.form["name"]
        ingredients = request.form["ingredients"]
        add_recipe(name, ingredients)
        return redirect(url_for("recipes"))

    return render_template("add_recipe.html")





@app.route("/recipe/<int:recipe_id>")
@login_required
def recipe_detail(recipe_id):
    recipe = get_recipe_by_id(recipe_id)

    # ingredients è già un dict → lo leggiamo direttamente
    ingredients = recipe["ingredients"]["text"]

    return render_template("recipe_detail.html", recipe=recipe, ingredients=ingredients)


@app.route("/recipe/<int:recipe_id>/delete", methods=["POST"])
@login_required
def delete_recipe_route(recipe_id):
    delete_recipe(recipe_id)
    return redirect(url_for("recipes"))








# ============================
#   START APP
# ============================

# Quando il file viene importato (es. da gunicorn su Render)
# inizializziamo subito il DB e lo scheduler

setup_scheduler(app)

if __name__ == "__main__":
    # Avvio locale sul Mac
    app.run(host="0.0.0.0", port=5050, debug=True)
