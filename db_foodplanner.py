import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ============================
#   TABELLE NECESSARIE
# ============================

def init_foodplanner_tables():
    conn = get_db()
    cur = conn.cursor()

    # 1) Tabella ricette
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ingredients TEXT NOT NULL
        );
    """)

    # 2) Tabella planner settimanale
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_plan (
            id SERIAL PRIMARY KEY,
            day_of_week TEXT NOT NULL,
            meal_type TEXT NOT NULL,   -- pranzo o cena
            recipe_id INTEGER REFERENCES recipes(id),
            done BOOLEAN DEFAULT FALSE
        );
    """)

    # Inserimento automatico giorni (solo se vuoto)
    cur.execute("SELECT COUNT(*) FROM weekly_plan;")
    count = cur.fetchone()["count"]

    if count == 0:
        days = ["lunedì", "martedì", "mercoledì", "giovedì",
                "venerdì", "sabato", "domenica"]

        for d in days:
            cur.execute("""
                INSERT INTO weekly_plan (day_of_week, meal_type)
                VALUES (%s, %s), (%s, %s)
            """, (d, "pranzo", d, "cena"))

    conn.commit()
    cur.close()
    conn.close()


# ============================
#   RICETTE
# ============================

def get_all_recipes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_recipe(name, ingredients):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO recipes (name, ingredients)
        VALUES (%s, %s)
    """, (name, ingredients))
    conn.commit()
    conn.close()


# ============================
#   PLANNER SETTIMANALE
# ============================

def get_week_plan():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT w.id, w.day_of_week, w.meal_type,
               r.id AS recipe_id, r.name AS recipe_name,
               w.done
        FROM weekly_plan w
        LEFT JOIN recipes r ON w.recipe_id = r.id
        ORDER BY w.id;
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def assign_recipe_to_day(day, meal, recipe_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE weekly_plan
        SET recipe_id = %s, done = FALSE
        WHERE day_of_week = %s AND meal_type = %s
    """, (recipe_id, day, meal))

    conn.commit()
    conn.close()


def remove_planned_recipe(plan_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE weekly_plan
        SET recipe_id = NULL, done = FALSE
        WHERE id = %s
    """, (plan_id,))

    conn.commit()
    conn.close()


def mark_meal_done(plan_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE weekly_plan
        SET done = TRUE
        WHERE id = %s
    """, (plan_id,))

    conn.commit()
    conn.close()
