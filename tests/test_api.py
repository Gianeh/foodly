import sqlite3
from importlib import reload

import pytest
from fastapi.testclient import TestClient

from foodly.core import db as core_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / 'test.db'
    monkeypatch.setattr(core_db, 'DB_PATH', db_path)
    from foodly.app import main as app_module
    reload(app_module)
    with TestClient(app_module.app) as client:
        yield client, db_path


def test_api_flow(client):
    client, db_path = client
    resp = client.post(
        '/api/foods',
        data={
            'name': 'Test Food',
            'kcal_100g': 100,
            'prot_100g': 10,
            'carb_100g': 20,
            'fat_100g': 5,
            'fiber_100g': 2,
            'sugar_100g': 1,
            'satfat_100g': 1,
            'sodium_mg_100g': 0,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT id FROM foods WHERE name=?', ('Test Food',)).fetchone()
    assert row is not None
    food_id = row['id']

    resp = client.post('/api/pantry', data={'food_id': food_id, 'qty_g': 200}, follow_redirects=False)
    assert resp.status_code == 303
    qty = conn.execute('SELECT qty_g FROM pantry WHERE food_id=?', (food_id,)).fetchone()[0]
    assert qty == 200

    resp = client.post('/api/consume', data={'food_id': food_id, 'grams': 50}, follow_redirects=False)
    assert resp.status_code == 303
    qty_after = conn.execute('SELECT qty_g FROM pantry WHERE food_id=?', (food_id,)).fetchone()[0]
    assert qty_after == 150
    grams = conn.execute('SELECT grams FROM consumption_logs WHERE food_id=?', (food_id,)).fetchone()[0]
    assert grams == 50

    resp = client.get('/api/summary')
    assert resp.status_code == 200
    data = resp.json()
    assert data['totals']['kcal'] > 0
    conn.close()
