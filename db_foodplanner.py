import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


# ============================
#   CONNESSIONE AL DATABASE
# ============================

def get_db():
    """Restituisce una connessione PostgreSQL usando RealDictCursor."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ============================
#   CREAZIONE TABELLE
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

    # 3) Planner giornaliero
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_entries (
            id SERIAL PRIMARY KEY,
            day_date DATE NOT NULL,
            meal_type TEXT NOT NULL,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            custom_note TEXT,
            is_done BOOLEAN DEFAULT FALSE,
            UNIQUE(day_date, meal_type)
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
    cur.close()
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
        VALUES (%s, %s, %s);
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
        VALUES (%s, %s, %s, %s);
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
        SELECT mp.id, mp.day_date, mp.meal_type, mp.custom_note, mp.is_done,
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
    cur.execute("""
        INSERT INTO meal_plan_entries (day_date, meal_type, recipe_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (day_date, meal_type) DO UPDATE
        SET recipe_id = EXCLUDED.recipe_id,
            is_done = FALSE,
            custom_note = NULL;
    """, (day_date, meal_type, recipe_id))
    conn.commit()
    conn.close()


def remove_planned_recipe(entry_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE meal_plan_entries
        SET recipe_id = NULL, is_done = FALSE
        WHERE id = %s;
    """, (entry_id,))
    conn.commit()
    conn.close()


def mark_meal_done(entry_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE meal_plan_entries
        SET is_done = TRUE
        WHERE id = %s;
    """, (entry_id,))
    conn.commit()
    conn.close()


# ============================
#   PIANO SETTIMANALE COMPLETO
# ============================

def get_week_plan():
    """Ritorna tutte le entries del planner ordinate per giorno e pasto."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT mp.id,
               mp.day_date,
               mp.meal_type,
               mp.custom_note,
               mp.is_done,
               r.id AS recipe_id,
               r.name AS recipe_name
        FROM meal_plan_entries mp
        LEFT JOIN recipes r ON mp.recipe_id = r.id
        ORDER BY mp.day_date, mp.meal_type;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================
#   LISTA DELLA SPESA
# ============================

def add_shopping_item(week_start, name, quantity, unit):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shopping_items (week_start, ingredient_name, quantity, unit)
        VALUES (%s, %s, %s, %s);
    """, (week_start, name, quantity, unit))
    conn.commit()
    conn.close()


def get_shopping_list(week_start):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM shopping_items
        WHERE week_start = %s
        ORDER BY status, ingredient_name;
    """, (week_start,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_shopping_status(item_id, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE shopping_items
        SET status = %s
        WHERE id = %s;
    """, (status, item_id))
    conn.commit()
    conn.close()
