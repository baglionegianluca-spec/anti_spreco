import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


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
        VALUES (%s, %s, %s, %s)
    """, (recipe_id, name, quantity, unit))
    conn.commit()
    conn.close()


def get_ingredients(recipe_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipe_ingredients WHERE recipe_id = %s", (recipe_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================
#   PLANNER: LETTURA GIORNO
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
    
    result = cur.fetchone()
    conn.close()
    return result


# ============================
#   PLANNER: SCRITTURA GIORNO
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
            dinner_second_recipe_id
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (day_date) DO UPDATE SET
            lunch_first_recipe_id = EXCLUDED.lunch_first_recipe_id,
            lunch_second_recipe_id = EXCLUDED.lunch_second_recipe_id,
            dinner_first_recipe_id = EXCLUDED.dinner_first_recipe_id,
            dinner_second_recipe_id = EXCLUDED.dinner_second_recipe_id;
    """, (day_text, lunch_first, lunch_second, dinner_first, dinner_second))

    conn.commit()
    conn.close()


# ============================
#   LISTA SPESA
# ============================

def add_shopping_item(week_start, name, quantity, unit):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shopping_items (week_start, ingredient_name, quantity, unit)
        VALUES (%s, %s, %s, %s)
    """, (week_start, name, quantity, unit))
    conn.commit()
    conn.close()


def get_shopping_list(week_start):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shopping_items WHERE week_start = %s ORDER BY status, ingredient_name", (week_start,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_shopping_status(item_id, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE shopping_items SET status = %s WHERE id = %s", (status, item_id))
    conn.commit()
    conn.close()


def get_recipe_by_id(recipe_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    row = cur.fetchone()
    conn.close()
    return row


def delete_recipe(recipe_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    conn.commit()
    conn.close()
