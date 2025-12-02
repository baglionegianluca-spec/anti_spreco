import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json


DATABASE_URL = os.getenv("DATABASE_URL")


# ============================
#   CONNESSIONE AL DATABASE
# ============================

def get_db():
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

    # 2) Ingredienti
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_name TEXT NOT NULL,
            quantity NUMERIC,
            unit TEXT
        );
    """)

    # 3) Planner giornaliero — 🔥 day_date ora è TEXT
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_entries (
            id SERIAL PRIMARY KEY,
            day_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            custom_note TEXT,
            is_done BOOLEAN DEFAULT FALSE,
            UNIQUE(day_date, meal_type)
        );
    """)

    # 4) Lista della spesa (lasciamo DATE per week_start)
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


def add_recipe(name, ingredients):
    conn = get_db()
    cur = conn.cursor()
    json_ingredients = json.dumps({"text": ingredients})
    cur.execute("""
        INSERT INTO recipes (name, notes)
        VALUES (%s, %s)
    """, (name, json_ingredients))
    conn.commit()
    cur.close()


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
#   PLANNER GIORNALIERO (TEXT)
# ============================

def get_day_plan(day_text):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            lunch_first_recipe_id,
            lunch_second_recipe_id,
            dinner_first_recipe_id,
            dinner_second_recipe_id
        FROM meal_plan_entries
        WHERE day_date = %s;
    """, (day_text,))

    row = cur.fetchone()
    conn.close()
    return row or {}





def assign_recipe(day_text, lunch_first, lunch_second, dinner_first, dinner_second):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO meal_plan_entries (
            day_date,
            lunch_first_recipe_id,
            lunch_second_recipe_id,
            dinner_first_recipe_id,
            dinner_second_recipe_id,
            is_done,
            custom_note
        )
        VALUES (%s, %s, %s, %s, %s, FALSE, NULL)
        ON CONFLICT (day_date) DO UPDATE SET
            lunch_first_recipe_id = EXCLUDED.lunch_first_recipe_id,
            lunch_second_recipe_id = EXCLUDED.lunch_second_recipe_id,
            dinner_first_recipe_id = EXCLUDED.dinner_first_recipe_id,
            dinner_second_recipe_id = EXCLUDED.dinner_second_recipe_id,
            is_done = FALSE,
            custom_note = NULL;
    """, (day_text, lunch_first, lunch_second, dinner_first, dinner_second))

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
    """Ritorna la settimana intera (ordinata per giorno come TESTO)."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            mp.id,
            mp.day_date,
            mp.meal_type,
            mp.recipe_id,
            mp.custom_note,
            mp.is_done,
            r.name AS recipe_name
        FROM meal_plan_entries mp
        LEFT JOIN recipes r ON mp.recipe_id = r.id
        ORDER BY mp.day_date, mp.meal_type;
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


# ============================
#   LISTA SPESA
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


def get_recipe_by_id(recipe_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    row = cur.fetchone()
    cur.close()
    return row


def delete_recipe(recipe_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    cur.execute("DELETE FROM meal_plan_entries WHERE recipe_id = %s", (recipe_id,))
    conn.commit()
    cur.close()
