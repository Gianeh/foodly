import sqlite3
import pytest

from foodly.core.calculations import compute_targets


def _setup_user_settings(conn: sqlite3.Connection):
    conn.execute(
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
        )
        '''
    )
    conn.execute(
        'INSERT INTO user_settings(id, weight_kg, height_cm, age, sex, activity_level, kcal_target, protein_g_per_kg, fat_g_per_kg) VALUES (1,?,?,?,?,?,?,?,?)',
        (70, 175, 30, 'M', 1.6, None, 1.8, 0.8)
    )
    conn.commit()


def test_compute_targets_defaults():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    _setup_user_settings(conn)
    targets = compute_targets(conn)
    assert targets['kcal'] == pytest.approx(2638.0, rel=1e-3)
    assert targets['prot_g'] == pytest.approx(126.0, rel=1e-3)
    assert targets['carb_g'] == pytest.approx(407.5, rel=1e-3)
    assert targets['fat_g'] == pytest.approx(56.0, rel=1e-3)
    assert targets['fiber_g'] == pytest.approx(36.9, rel=1e-3)
