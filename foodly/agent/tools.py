import sqlite3
from datetime import datetime
from typing import Dict, Optional

from foodly.core.models import AddToPantry, Consume, FindFood

def tool_add_to_pantry(conn: sqlite3.Connection, p: AddToPantry):
    conn.execute(
        "INSERT INTO pantry(food_id, qty_g, package_g, location, best_before) VALUES (?,?,?,?,?)",
        (p.food_id, p.qty_g, p.package_g, p.location, p.best_before)
    )


def tool_consume(conn: sqlite3.Connection, c: Consume):
    conn.execute(
        "INSERT INTO consumption_logs(ts, food_id, grams, meal, note) VALUES (?,?,?,?,?)",
        (datetime.utcnow().isoformat(), c.food_id, c.grams, c.meal, c.note)
    )
    # Decremento FIFO
    remaining = c.grams
    rows = conn.execute(
        "SELECT id, qty_g FROM pantry WHERE food_id=? AND qty_g>0 ORDER BY COALESCE(best_before,'9999-12-31'), created_at",
        (c.food_id,)
    ).fetchall()
    for r in rows:
        if remaining <= 0: break
        pid, qty = r["id"], float(r["qty_g"])
        take = min(qty, remaining)
        conn.execute("UPDATE pantry SET qty_g = qty_g - ? WHERE id=?", (take, pid))
        remaining -= take


def tool_find_food(conn: sqlite3.Connection, q: FindFood):
    like = f"%{q.query.strip()}%"
    rows = conn.execute(
        "SELECT id, name, brand, kcal_100g, prot_100g, carb_100g, fat_100g FROM foods WHERE name LIKE ? ORDER BY name LIMIT ?",
        (like, q.limit)
    ).fetchall()
    return [dict(r) for r in rows]

def day_summary(conn: sqlite3.Connection, date_str: Optional[str] = None):
    from foodly.core.calculations import day_bounds
    start, end = day_bounds(date_str)
    totals = {"kcal":0.0, "prot_g":0.0, "carb_g":0.0, "fat_g":0.0, "fiber_g":0.0, "sodium_mg":0.0}
    rows = conn.execute(
        """
        SELECT c.ts, c.grams, f.*
        FROM consumption_logs c JOIN foods f ON c.food_id=f.id
        WHERE c.ts BETWEEN ? AND ?
        """, (start, end)
    ).fetchall()
    for r in rows:
        g = float(r["grams"]) / 100.0
        totals["kcal"] += r["kcal_100g"] * g
        totals["prot_g"] += r["prot_100g"] * g
        totals["carb_g"] += r["carb_100g"] * g
        totals["fat_g"]  += r["fat_100g"] * g
        totals["fiber_g"] += r["fiber_100g"] * g
        totals["sodium_mg"] += r["sodium_mg_100g"] * g
    return {k: round(v,1) for k,v in totals.items()}

def suggest_from_pantry(conn: sqlite3.Connection, date_str: Optional[str] = None) -> Dict[str, any]:
    from foodly.core.calculations import compute_targets
    totals = day_summary(conn, date_str)
    targets = compute_targets(conn)
    resid = {
        "kcal": max(0.0, targets["kcal"] - totals["kcal"]),
        "prot_g": max(0.0, targets["prot_g"] - totals["prot_g"]),
        "carb_g": max(0.0, targets["carb_g"] - totals["carb_g"]),
        "fat_g": max(0.0, targets["fat_g"] - totals["fat_g"]),
        "fiber_g": max(0.0, targets["fiber_g"] - totals["fiber_g"]),
    }
    # Candidati: join dispensa + foods (qty>0)
    rows = conn.execute(
        """
        SELECT f.id as food_id, f.name, p.qty_g, f.kcal_100g, f.prot_100g, f.carb_100g, f.fat_100g, f.fiber_100g
        FROM pantry p JOIN foods f ON p.food_id=f.id
        WHERE p.qty_g > 0
        ORDER BY f.name
        """
    ).fetchall()
    candidates = [dict(r) for r in rows]
    if not candidates:
        return {"options": [], "residuals": resid, "note": "Dispensa vuota o esaurita."}

    # Strategy: quale macro è più carente?
    deficits = sorted([(k, v) for k,v in resid.items() if k!="kcal"], key=lambda x: -x[1])
    main_def = deficits[0][0] if deficits else "prot_g"

    def score(food):
        # preferenza in base al deficit principale e penalità grasse se fat è già coperto
        p = food["prot_100g"]; c = food["carb_100g"]; f = food["fat_100g"]; fib = food.get("fiber_100g", 0.0)
        kcal = max(1e-6, food["kcal_100g"])  # prevenire div zero
        s = 0.0
        if main_def == "prot_g": s += (p/kcal)*3 + fib*0.02
        if main_def == "carb_g": s += (c/kcal)*3 + fib*0.03
        if main_def == "fat_g":  s += (f/kcal)*3
        if resid["fiber_g"] > 5: s += fib*0.05
        if resid["fat_g"] <= 0: s -= (f/kcal)  # penalizza grassi se già a target
        return s

    ranked = sorted(candidates, key=score, reverse=True)[:5]

    # Quantità proposta: prova a coprire ~80% del deficit principale con un singolo alimento
    options = []
    for food in ranked:
        if main_def == "prot_g": per100 = food["prot_100g"]
        elif main_def == "carb_g": per100 = food["carb_100g"]
        else: per100 = food["fat_100g"]
        target_cover = 0.8 * resid[main_def]
        grams = 0
        if per100 > 0:
            grams = min(food["qty_g"], max(0.0, target_cover / per100 * 100.0))
            # Arrotonda a step da 5 g
            grams = 5 * round(grams/5)
        if grams <= 0: continue
        # Calcolo impatti
        factor = grams/100.0
        delta = {
            "kcal": round(food["kcal_100g"]*factor, 1),
            "prot_g": round(food["prot_100g"]*factor, 1),
            "carb_g": round(food["carb_100g"]*factor, 1),
            "fat_g": round(food["fat_100g"]*factor, 1),
            "fiber_g": round(food.get("fiber_100g",0)*factor, 1),
        }
        options.append({
            "food_id": food["food_id"],
            "name": food["name"],
            "grams": grams,
            "delta": delta
        })
    return {"options": options[:3], "residuals": resid, "main_deficit": main_def}
