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

    # Tabelle ricette
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            notes TEXT,
            default_servings INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_name TEXT NOT NULL,
            quantity NUMERIC,
            unit TEXT
        );
    """)

    # ============================
    #   NUOVA STRUTTURA FOOD PLANNER
    # ============================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_entries (
            id SERIAL PRIMARY KEY,
            day_date TEXT NOT NULL UNIQUE,

            lunch_first_recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            lunch_second_recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,

            dinner_first_recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
            dinner_second_recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,

            custom_note TEXT,
            is_done BOOLEAN DEFAULT FALSE
        );
    """)

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
    conn.close()


def get_recipe_by_id(recipe_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def delete_recipe(recipe_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM meal_plan_entries WHERE lunch_first_recipe_id = %s OR lunch_second_recipe_id = %s OR dinner_first_recipe_id = %s OR dinner_second_recipe_id = %s",
                (recipe_id, recipe_id, recipe_id, recipe_id))

    cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))

    conn.commit()
    cur.close()
    conn.close()


# ============================
#   LETTURA PIANO DEL GIORNO
# ============================

def get_day_plan(day_text):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            mp.*,
            r1.name AS lunch_first_name,
            r2.name AS lunch_second_name,
            r3.name AS dinner_first_name,
            r4.name AS dinner_second_name
        FROM meal_plan_entries mp
        LEFT JOIN recipes r1 ON mp.lunch_first_recipe_id = r1.id
        LEFT JOIN recipes r2 ON mp.lunch_second_recipe_id = r2.id
        LEFT JOIN recipes r3 ON mp.dinner_first_recipe_id = r3.id
        LEFT JOIN recipes r4 ON mp.dinner_second_recipe_id = r4.id
        WHERE mp.day_date = %s
    """, (day_text,))

    row = cur.fetchone()
    conn.close()
    return row


# ============================
#   SALVATAGGIO / MODIFICA PIANO
# ============================

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


# ============================
#   RIMOZIONE PASTO
# ============================

def remove_planned_recipe(entry_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE meal_plan_entries
        SET lunch_first_recipe_id = NULL,
            lunch_second_recipe_id = NULL,
            dinner_first_recipe_id = NULL,
            dinner_second_recipe_id = NULL,
            is_done = FALSE
        WHERE id = %s
    """, (entry_id,))

    conn.commit()
    conn.close()


def mark_meal_done(entry_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE meal_plan_entries SET is_done = TRUE WHERE id = %s", (entry_id,))
    conn.commit()
    conn.close()
