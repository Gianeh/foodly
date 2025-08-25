from __future__ import annotations
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from foodly.core.db import get_db, init_db
from foodly.core.calculations import compute_targets
from foodly.core.models import MealType

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Foodly App")

# Ensure folders
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

init_db()

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {k: r[k] for k in r.keys()}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    conn = get_db()
    foods = [row_to_dict(r) for r in conn.execute("SELECT * FROM foods ORDER BY name").fetchall()]
    pantry = conn.execute(
        """
        SELECT p.id AS pid, f.name, f.id AS food_id, p.qty_g, COALESCE(p.package_g, 0) AS package_g, p.location
        FROM pantry p JOIN foods f ON p.food_id=f.id
        ORDER BY f.name
        """
    ).fetchall()
    pantry = [row_to_dict(r) for r in pantry]
    targets = compute_targets(conn)
    today = date.today().isoformat()
    conn.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "foods": foods,
        "pantry": pantry,
        "targets": targets,
        "today": today,
    })

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    conn = get_db()
    s = conn.execute("SELECT * FROM user_settings WHERE id=1").fetchone()
    conn.close()
    return templates.TemplateResponse("settings.html", {"request": request, "s": s})

@app.post("/settings")
def update_settings(
    weight_kg: float = Form(...),
    height_cm: float = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    activity_level: float = Form(...),
    kcal_target: Optional[float] = Form(None),
    protein_g_per_kg: float = Form(1.8),
    fat_g_per_kg: float = Form(0.8),
    llm_api_key: Optional[str] = Form(None),
):
    conn = get_db()
    conn.execute(
        """
        UPDATE user_settings
        SET weight_kg=?, height_cm=?, age=?, sex=?, activity_level=?, kcal_target=?,
            protein_g_per_kg=?, fat_g_per_kg=?, llm_api_key=?
        WHERE id=1
        """,
        (
            weight_kg,
            height_cm,
            age,
            sex,
            activity_level,
            kcal_target,
            protein_g_per_kg,
            fat_g_per_kg,
            llm_api_key,
        ),
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/settings", status_code=303)

@app.post("/api/foods")
def api_add_food(
    name: str = Form(...),
    kcal_100g: float = Form(...),
    prot_100g: float = Form(...),
    carb_100g: float = Form(...),
    fat_100g: float = Form(...),
    fiber_100g: float = Form(0),
    sugar_100g: float = Form(0),
    satfat_100g: float = Form(0),
    sodium_mg_100g: float = Form(0),
    brand: Optional[str] = Form(None),
    barcode: Optional[str] = Form(None),
):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO foods(name, brand, barcode, kcal_100g, prot_100g, carb_100g, fat_100g, fiber_100g, sugar_100g, satfat_100g, sodium_mg_100g, source, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', ?)
        """,
        (name, brand, barcode, kcal_100g, prot_100g, carb_100g, fat_100g, fiber_100g, sugar_100g, satfat_100g, sodium_mg_100g, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.post("/api/pantry")
def api_add_pantry(
    food_id: int = Form(...),
    qty_g: float = Form(...),
    package_g: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    best_before: Optional[str] = Form(None),
):
    conn = get_db()
    conn.execute(
        "INSERT INTO pantry(food_id, qty_g, package_g, location, best_before) VALUES (?,?,?,?,?)",
        (food_id, qty_g, package_g, location, best_before)
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.post("/api/consume")
def api_consume(
    food_id: int = Form(...),
    grams: float = Form(...),
    meal: MealType = Form(MealType.snack),
    note: Optional[str] = Form(None),
):
    grams = max(0.0, grams)
    conn = get_db()
    # Log consumption
    conn.execute(
        "INSERT INTO consumption_logs(ts, food_id, grams, meal, note) VALUES (?,?,?,?,?)",
        (datetime.utcnow().isoformat(), food_id, grams, meal.value, note)
    )
    # Decrement pantry FIFO by created_at
    remaining = grams
    rows = conn.execute(
        "SELECT id, qty_g FROM pantry WHERE food_id=? AND qty_g>0 ORDER BY COALESCE(best_before, '9999-12-31'), created_at",
        (food_id,)
    ).fetchall()
    for r in rows:
        if remaining <= 0: break
        pid, qty = r["id"], float(r["qty_g"])
        take = min(qty, remaining)
        conn.execute("UPDATE pantry SET qty_g = qty_g - ? WHERE id=?", (take, pid))
        remaining -= take
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.get("/api/summary")
def api_summary(date_str: Optional[str] = None):
    if not date_str:
        date_str = date.today().isoformat()
    day_start = date_str + "T00:00:00"
    day_end = date_str + "T23:59:59"
    conn = get_db()
    totals = {"kcal":0.0, "prot_g":0.0, "carb_g":0.0, "fat_g":0.0, "fiber_g":0.0, "sodium_mg":0.0}
    rows = conn.execute(
        """
        SELECT c.ts, c.grams, f.*
        FROM consumption_logs c JOIN foods f ON c.food_id=f.id
        WHERE c.ts BETWEEN ? AND ?
        """,
        (day_start, day_end)
    ).fetchall()
    for r in rows:
        g = float(r["grams"]) / 100.0
        totals["kcal"] += r["kcal_100g"] * g
        totals["prot_g"] += r["prot_100g"] * g
        totals["carb_g"] += r["carb_100g"] * g
        totals["fat_g"]  += r["fat_100g"] * g
        totals["fiber_g"] += r["fiber_100g"] * g
        totals["sodium_mg"] += r["sodium_mg_100g"] * g

    targets = compute_targets(conn)
    conn.close()

    def pct(part, whole):
        return round(100*part/whole, 1) if whole > 0 else 0.0

    response = {
        "date": date_str,
        "totals": {k: round(v, 1) for k, v in totals.items()},
        "targets": targets,
        "progress": {
            "kcal_pct": pct(totals["kcal"], targets["kcal"]),
            "prot_pct": pct(totals["prot_g"], targets["prot_g"]),
            "carb_pct": pct(totals["carb_g"], targets["carb_g"]),
            "fat_pct":  pct(totals["fat_g"], targets["fat_g"]),
            "fiber_pct": pct(totals["fiber_g"], targets["fiber_g"]),
        }
    }
    return JSONResponse(response)
