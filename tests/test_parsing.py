import sqlite3
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from foodly.agent.main import naive_parse
from foodly.core.models import AddToPantry, Consume

@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE foods (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    foods = [
        ("Latte parzialmente scremato",),
        ("Yogurt bianco",),
        ("Tonno al naturale",),
    ]
    conn.executemany("INSERT INTO foods(name) VALUES (?)", foods)
    yield conn
    conn.close()

def test_parse_ml(conn):
    text = "aggiungi 200 ml di latte"
    actions = naive_parse(conn, text)
    assert len(actions) == 1
    a = actions[0]
    assert a.name == "add_to_pantry"
    assert a.arguments["qty_g"] == 200.0

def test_parse_multipack(conn):
    text = "aggiungi 2 vasetti di yogurt da 125 g"
    actions = naive_parse(conn, text)
    assert len(actions) == 1
    a = actions[0]
    assert a.name == "add_to_pantry"
    assert a.arguments["qty_g"] == 250.0

def test_parse_consume(conn):
    text = "ho mangiato 150 g di tonno"
    actions = naive_parse(conn, text)
    assert len(actions) == 1
    a = actions[0]
    assert a.name == "consume"
    assert a.arguments["grams"] == 150.0
