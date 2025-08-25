# Foodly

Foodly è un prototipo di coach nutrizionale composto da due servizi FastAPI e una libreria condivisa.

## Struttura a pacchetti
- **`foodly/core`** – gestione del database SQLite, modelli Pydantic e calcoli nutrizionali.
https://github.com/Gianeh/foodly/pull/7/conflict?name=README.md&base_oid=acad9c5d3e4d61e8c7c292b1fbac3575936ae2b9&head_oid=3b192c748521a245427c47c8d6f9146476aa7482- **`foodly/app`** – interfaccia web per consultare dispensa e impostazioni.
- **`foodly/agent`** – agente conversazionale che interagisce con il database tramite strumenti.

## Requisiti
- Python 3.11+
- Dipendenze installabili con `pip install -r requirements.txt`.

## Avvio dei servizi
Eseguire lo script `run.sh` per avviare contemporaneamente il Web UI (porta 8000) e l'agente (porta 8001):

```bash
bash run.sh
```

## Database
Il progetto utilizza un database SQLite denominato `foodly.db` nella directory radice. Le tabelle e alcuni dati di esempio vengono creati automaticamente al primo avvio.

## Variabili d'ambiente
- `FOODLY_API` – chiave API per il modello linguistico. Se impostata, viene salvata anche in `user_settings.llm_api_key`.

## Stato del modello linguistico
L'integrazione con LLM non è ancora implementata. L'agente funziona tramite parser rule‑based: impostare `use_rule_based=true` nelle richieste finché il supporto LLM non sarà disponibile.
