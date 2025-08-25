import sqlite3
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).parent.parent.parent
DB_PATH = APP_DIR / "foodly.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Core tables
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            barcode TEXT,
            kcal_100g REAL NOT NULL,
            prot_100g REAL NOT NULL,
            carb_100g REAL NOT NULL,
            fat_100g REAL NOT NULL,
            fiber_100g REAL DEFAULT 0,
            sugar_100g REAL DEFAULT 0,
            satfat_100g REAL DEFAULT 0,
            sodium_mg_100g REAL DEFAULT 0,
            source TEXT,
            last_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            qty_g REAL NOT NULL,
            package_g REAL,
            location TEXT,
            best_before TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(food_id) REFERENCES foods(id)
        );

        CREATE TABLE IF NOT EXISTS consumption_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            food_id INTEGER NOT NULL,
            grams REAL NOT NULL,
            meal TEXT,
            note TEXT,
            FOREIGN KEY(food_id) REFERENCES foods(id)
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            weight_kg REAL DEFAULT 75,
            height_cm REAL DEFAULT 175,
            age INTEGER DEFAULT 30,
            sex TEXT DEFAULT 'M',               -- 'M' or 'F'
            activity_level REAL DEFAULT 1.5,    -- 1.2..1.9
            kcal_target REAL,                   -- if NULL, use TDEE
            protein_g_per_kg REAL DEFAULT 1.8,
            fat_g_per_kg REAL DEFAULT 0.8
        );
        """
    )

    # Seed settings
    cur.execute("INSERT OR IGNORE INTO user_settings(id) VALUES (1)")

    # Seed a few foods if empty
    cur.execute("SELECT COUNT(*) AS n FROM foods")
    n = cur.fetchone()[0]
    if n == 0:
        foods_seed = [
            # name, brand, barcode, kcal, prot, carb, fat, fiber, sugar, satfat, sodium_mg
            ("Tonno al naturale (scatoletta)", None, None, 116, 25, 0, 1, 0, 0, 0.2, 300),
            ("Gallette di mais", None, None, 381, 8, 77, 3.6, 3.0, 0.6, 0.5, 5),
            ("Prosciutto crudo", None, None, 269, 26, 0, 18, 0, 0, 6, 2000),
        ]
        for row in foods_seed:
            cur.execute(
                """
                INSERT INTO foods
                (name, brand, barcode, kcal_100g, prot_100g, carb_100g, fat_100g, fiber_100g, sugar_100g, satfat_100g, sodium_mg_100g, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed', ?)
                """,
                (*row, datetime.utcnow().isoformat()),
            )

    # Seed pantry if empty
    cur.execute("SELECT COUNT(*) AS n FROM pantry")
    if cur.fetchone()[0] == 0:
        # 2 scatolette da 56 g (112 g totali), 200 g gallette, 100 g prosciutto
        cur.execute("SELECT id FROM foods WHERE name LIKE 'Tonno al naturale%' LIMIT 1")
        tuna_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM foods WHERE name LIKE 'Gallette di mais%' LIMIT 1")
        gallette_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM foods WHERE name LIKE 'Prosciutto crudo%' LIMIT 1")
        prosciutto_id = cur.fetchone()[0]

        cur.executemany(
            "INSERT INTO pantry(food_id, qty_g, package_g, location, best_before) VALUES (?, ?, ?, ?, ?)",
            [
                (tuna_id, 112.0, 56.0, 'dispensa', None),
                (gallette_id, 200.0, None, 'dispensa', None),
                (prosciutto_id, 100.0, None, 'frigo', None),
            ],
        )

    conn.commit()
    conn.close()
