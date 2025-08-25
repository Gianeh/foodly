import sqlite3
from datetime import date
from typing import Dict, Tuple, Optional

def bmr_mifflin(kg: float, cm: float, years: int, sex: str) -> float:
    base = 10*kg + 6.25*cm - 5*years
    return base + (5 if sex.upper() == 'M' else -161)


def compute_targets(conn: sqlite3.Connection) -> Dict[str, float]:
    s = conn.execute("SELECT * FROM user_settings WHERE id=1").fetchone()
    kg = s["weight_kg"]; cm = s["height_cm"]; years = s["age"]; sex = s["sex"]; act = s["activity_level"]
    kcal_t = s["kcal_target"]
    if kcal_t is None:
        kcal_t = bmr_mifflin(kg, cm, years, sex) * act
    prot_g = max(0.0, (s["protein_g_per_kg"] or 1.8) * kg)
    fat_g = max(0.0, (s["fat_g_per_kg"] or 0.8) * kg)
    used_kcal = prot_g*4 + fat_g*9
    carb_g = max(0.0, (kcal_t - used_kcal)/4)
    fiber_g = (kcal_t / 1000.0) * 14.0
    return {
        "kcal": round(kcal_t, 1),
        "prot_g": round(prot_g, 1),
        "carb_g": round(carb_g, 1),
        "fat_g": round(fat_g, 1),
        "fiber_g": round(fiber_g, 1),
    }


def day_bounds(date_str: Optional[str] = None) -> Tuple[str, str]:
    """Return ISO 8601 start and end timestamps for the given day.

    If ``date_str`` is ``None`` it defaults to today's date. The function
    returns a tuple ``(start, end)`` where ``start`` corresponds to midnight
    and ``end`` to the last second of the day. These bounds are used by several
    reporting utilities to select records within a specific day.
    """
    if not date_str:
        date_str = date.today().isoformat()
    start = f"{date_str}T00:00:00"
    end = f"{date_str}T23:59:59"
    return start, end
