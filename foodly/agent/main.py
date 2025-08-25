from __future__ import annotations
import sqlite3
import re
from typing import Any, Dict, List

from fastapi import FastAPI, Body

from foodly.core.db import get_db
from foodly.core.calculations import compute_targets
from foodly.core.models import (
    AddToPantry,
    Consume,
    FindFood,
    Summary,
    ToolCall,
    ChatRequest,
    ChatResponse,
)
from foodly.agent.tools import (
    tool_add_to_pantry,
    tool_consume,
    tool_find_food,
    day_summary,
    suggest_from_pantry,
)

app = FastAPI(title="Foodly Agent")

SYSTEM_PROMPT = (
    "Agisci come Coach nutrizionale conversazionale. Capisci richieste in italiano; "
    "usa SOLO gli strumenti forniti per leggere/scrivere dati. Regole: "
    "1) Non inventare nutrienti; 2) tutte le quantità in grammi/ml; 3) conferma operazioni ambigue; "
    "4) rispondi con numeri chiari e brevi; 5) se utile, proponi 1–3 opzioni dalla dispensa; "
    "6) MAI superare i limiti: niente decreti negativi, niente kcal/macro impossibili; "
    "7) Output JSON con 'actions' (tool calls) e 'message' sintetico."
)

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "add_to_pantry",
            "description": "Aggiunge quantità in grammi alla dispensa per un food_id.",
            "parameters": AddToPantry.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consume",
            "description": "Registra consumo in grammi e decrementa la dispensa FIFO.",
            "parameters": Consume.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_food",
            "description": "Cerca alimenti per nome (LIKE).",
            "parameters": FindFood.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daily_summary",
            "description": "Restituisce riepilogo per la data.",
            "parameters": Summary.model_json_schema(),
        },
    },
]

ADD_PAT = re.compile(r"aggiung[ei]|metti(?: .+)? in dispensa", re.I)
CONS_PAT = re.compile(r"(ho )?(mangiato|consumato|usa|consuma)", re.I)
GRAMS_PAT = re.compile(r"(\d+)(?:\s)?g\b", re.I)
QTY_PAT = re.compile(r"(\d+)\s*(?:x|scatolette?|confezioni?)", re.I)


def naive_parse(conn: sqlite3.Connection, text: str) -> List[ToolCall]:
    text = text.strip()
    actions: List[ToolCall] = []
    # Trova alimento per nome
    def find_id(name: str) -> int | None:
        r = conn.execute("SELECT id FROM foods WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
        return int(r[0]) if r else None

    if ADD_PAT.search(text):
        grams = 0.0
        m = GRAMS_PAT.search(text)
        if m:
            grams = float(m.group(1))
        # Prova quantità per unità (es. 2 scatolette da 56 g)
        mq = QTY_PAT.search(text)
        if mq and grams == 0.0:
            qty = float(mq.group(1))
            # deduci 56 g se parla di tonno
            grams = qty * (56.0 if "tonno" in text.lower() else 100.0)
        # identifica food
        food = None
        for key in ["tonno", "gallette", "prosciutto", "riso", "pollo", "yogurt"]:
            if key in text.lower():
                food = key; break
        if food is None:
            # fallback: prima parola ‘alimento’ dopo verbo
            tokens = re.split(r"\s+", text)
            if len(tokens) > 1:
                food = tokens[-1]
        fid = find_id(food) if food else None
        if fid and grams>0:
            actions.append(ToolCall(name="add_to_pantry", arguments=AddToPantry(food_id=fid, qty_g=grams).model_dump()))
        return actions

    if CONS_PAT.search(text):
        grams = 0.0
        m = GRAMS_PAT.search(text)
        if m:
            grams = float(m.group(1))
        food = None
        for key in ["tonno", "gallette", "prosciutto", "riso", "pollo", "yogurt"]:
            if key in text.lower():
                food = key; break
        fid = find_id(food) if food else None
        if fid and grams>0:
            actions.append(ToolCall(name="consume", arguments=Consume(food_id=fid, grams=grams).model_dump()))
        return actions

    # default: nessuna azione → solo riepilogo/suggerimento
    return []


def execute_actions(conn: sqlite3.Connection, actions: List[ToolCall], dry: bool=False) -> List[Dict[str, Any]]:
    results = []
    if dry:
        return [{"name": a.name, "status": "dry_run", "arguments": a.arguments} for a in actions]
    for a in actions:
        if a.name == "add_to_pantry":
            p = AddToPantry(**a.arguments); tool_add_to_pantry(conn, p); results.append({"name": a.name, "status": "ok"})
        elif a.name == "consume":
            c = Consume(**a.arguments); tool_consume(conn, c); results.append({"name": a.name, "status": "ok"})
        elif a.name == "find_food":
            q = FindFood(**a.arguments); data = tool_find_food(conn, q); results.append({"name": a.name, "status": "ok", "data": data})
        elif a.name == "daily_summary":
            q = Summary(**a.arguments); data = day_summary(conn, q.date_str); results.append({"name": a.name, "status": "ok", "data": data})
        else:
            results.append({"name": a.name, "status": "unknown_tool"})
    return results


@app.post("/agent/chat", response_model=ChatResponse)
def agent_chat(req: ChatRequest = Body(...)):
    conn = get_db()

    # 1) Determina azioni da eseguire (LLM o fallback rule-based)
    actions: List[ToolCall] = []
    if req.use_rule_based:
        actions = naive_parse(conn, req.user_message)
    else:
        # Hook LLM: costruisci messages + tools e ottieni tool calls (da implementare)
        _ = SYSTEM_PROMPT, TOOLS_SCHEMA  # silenzia l/linter
        raise NotImplementedError("LLM non collegato in questo prototipo. Imposta use_rule_based=true.")

    # 2) Esegui tools
    results = execute_actions(conn, actions, dry=req.dry_run)
    conn.commit(); conn.close()

    # 3) Riepilogo e suggerimento
    conn = get_db()
    totals = day_summary(conn, req.date_str)
    targets = compute_targets(conn)
    sugg = suggest_from_pantry(conn, req.date_str)
    conn.close()

    # 4) Messaggio sintetico
    def pct(part, whole):
        return round(100*part/whole) if whole>0 else 0
    msg = (
        f"Riepilogo: {round(totals['kcal'])}/{round(targets['kcal'])} kcal — "
        f"P {round(totals['prot_g'])}/{round(targets['prot_g'])} g, "
        f"C {round(totals['carb_g'])}/{round(targets['carb_g'])} g, "
        f"F {round(totals['fat_g'])}/{round(targets['fat_g'])} g. "
    )
    if sugg.get("options"):
        o = sugg["options"][0]
        msg += f"Proposta: {o['grams']} g di {o['name']} (≈ +{o['delta']['kcal']} kcal, +{o['delta']['prot_g']}P, +{o['delta']['carb_g']}C, +{o['delta']['fat_g']}F)."
    else:
        msg += sugg.get("note", "")

    return ChatResponse(actions=actions, results={"tool_results": results, "totals": totals, "targets": targets, "suggestion": sugg}, message=msg)


@app.post("/tools/add_to_pantry")
def http_add_to_pantry(p: AddToPantry):
    conn = get_db(); tool_add_to_pantry(conn, p); conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/tools/consume")
def http_consume(c: Consume):
    conn = get_db(); tool_consume(conn, c); conn.commit(); conn.close()
    return {"status": "ok"}

@app.get("/tools/find_food")
def http_find_food(query: str, limit: int = 10):
    conn = get_db(); data = tool_find_food(conn, FindFood(query=query, limit=limit)); conn.close(); return {"data": data}

@app.get("/tools/summary")
def http_summary(date_str: str | None = None):
    conn = get_db(); data = day_summary(conn, date_str); conn.close(); return {"data": data}
