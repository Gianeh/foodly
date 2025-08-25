import sqlite3

from foodly.agent.tools import suggest_from_pantry


def _setup_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE user_settings (
            id INTEGER PRIMARY KEY,
            weight_kg REAL,
            height_cm REAL,
            age INTEGER,
            sex TEXT,
            activity_level REAL,
            kcal_target REAL,
            protein_g_per_kg REAL,
            fat_g_per_kg REAL
        );
        INSERT INTO user_settings(id, weight_kg, height_cm, age, sex, activity_level, kcal_target, protein_g_per_kg, fat_g_per_kg)
            VALUES (1,70,175,30,'M',1.6,NULL,1.8,0.8);

        CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            kcal_100g REAL,
            prot_100g REAL,
            carb_100g REAL,
            fat_100g REAL,
            fiber_100g REAL
        );
        INSERT INTO foods(name, kcal_100g, prot_100g, carb_100g, fat_100g, fiber_100g) VALUES
            ('High Protein', 150, 30, 0, 5, 0),
            ('High Carb', 120, 5, 80, 2, 2),
            ('High Fat', 200, 5, 5, 15, 0);

        CREATE TABLE pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER,
            qty_g REAL
        );
        INSERT INTO pantry(food_id, qty_g) VALUES (1, 500), (2, 500), (3, 500);

        CREATE TABLE consumption_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            food_id INTEGER,
            grams REAL,
            meal TEXT,
            note TEXT
        );
        '''
    )
    return conn


def test_suggest_from_pantry_prioritizes_carbs():
    conn = _setup_db()
    result = suggest_from_pantry(conn)
    assert result['main_deficit'] == 'carb_g'
    names = [o['name'] for o in result['options']]
    assert 'High Carb' in names
    option = next(o for o in result['options'] if o['name'] == 'High Carb')
    assert option['grams'] > 0
    assert option['grams'] <= 500
