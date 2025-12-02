import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


# ============================
#   CONNESSIONE DATABASE
# ============================

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ============================
#   CREAZIONE TABELLE (SCHEMA A)
# ============================

def init_foodplanner_tables():
    conn = get_db()
    cur = conn.cursor()

    # 1) Tabella ricette
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT,
            default_servings INTEGER
        );
    """)

    # 2) Ingredienti delle ricette
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_name TEXT NOT NULL,
            quantity NUMERIC,
            unit TEXT
        );
    """)

    # 3) Pianificazione giornaliera pasti
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_entries (
            id SERIAL PRIMARY KEY,
            day_date DATE NOT NULL,
            meal_type TEXT NOT NULL,       -- 'lunch' o 'dinner'
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            custom_note TEXT,
            is_done BOOLEAN DEFAULT FALSE
        );
    """)

    # 4) Lista della spesa
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shopping_items (
            id SERIAL PRIMARY KEY,
            week_start DATE NOT NULL,
            ingredient_name TEXT NOT NULL,
            quantity NUMERIC,
            unit TEXT,
            status TEXT NOT NULL DEFAULT 'needed'
        );
    """)

    conn.commit()
    conn.close()


# ============================
#   RICETTE
# ============================

def get_all_recipes():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM recipes ORDER BY name;")
    rows = cur.fetchall()

    conn.close()
    return rows


def add_recipe(name, notes=None, default_servings=None):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO recipes (name, notes, default_servings)
        VALUES (%s, %s, %s)
    """, (name, notes, default_servings))

    conn.commit()
    conn.close()


# ============================
#   INGREDIENTI RICETTA
# ============================

def add_ingredient(recipe_id, name, quantity, unit):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO recipe_ingredients (recipe_id, ingredient_name, quantity, unit)
        VALUES (%s, %s, %s, %s)
    """, (recipe_id, name, quantity, unit))

    conn.commit()
    conn.close()


def get_ingredients(recipe_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM recipe_ingredients
        WHERE recipe_id = %s;
    """, (recipe_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


# ============================
#   PLANNER GIORNALIERO
# ============================

def get_day_plan(day_date):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT mp.id, mp.day_date, mp.meal_type, mp.custom_note,
               mp.is_done,
               r.id AS recipe_id, r.name AS recipe_name
        FROM meal_plan_entries mp
        LEFT JOIN recipes r ON mp.recipe_id = r.id
        WHERE mp.day_date = %s
        ORDER BY mp.meal_type;
    """, (day_date,))

    rows = cur.fetchall()
    conn.close()
    return rows


def assign_recipe(day_date, meal_type, recipe_id):
    conn = get_db()
    cur = conn.cursor()

    # Se non esiste la riga, la creiamo.
    cur.execute("""
        INSERT INTO meal_plan_entries (day_date, meal_type, recipe_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (day_date, meal_type) DO UPDATE
        SET recipe_id = EXCLUDED.recipe_id, is_done = FALSE_
