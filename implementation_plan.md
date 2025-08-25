# Implementation Plan

[Overview]
Refactor the monolithic Foodly prototype into a structured multi-package application with two distinct services: a web frontend (`app`) and a conversational agent (`agent`). This refactoring will introduce a shared `core` library to handle database interactions, data models, and nutritional calculations, eliminating code duplication and improving maintainability. The goal is to create a more organized, scalable, and robust architecture.

[Types]
No new types will be introduced, but existing Pydantic models from `agent_service.py` will be moved to the shared `core` library.

The following Pydantic models will be moved to `foodly/core/models.py`:
- `AddToPantry(BaseModel)`
- `Consume(BaseModel)`
- `FindFood(BaseModel)`
- `Summary(BaseModel)`
- `ToolCall(BaseModel)`
- `ChatRequest(BaseModel)`
- `ChatResponse(BaseModel)`

[Files]
The file structure will be reorganized from a flat structure to a packaged one.

**New Directory Structure:**
```
/
|-- foodly/
|   |-- __init__.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- db.py             # Database connection, initialization, and schema
|   |   |-- models.py         # Pydantic models for API and tools
|   |   `-- calculations.py   # Nutritional calculation functions (BMR, TDEE, etc.)
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py           # FastAPI application for the web UI
|   |   |-- templates/
|   |   |   |-- index.html
|   |   |   `-- settings.html
|   |   `-- static/
|   `-- agent/
|       |-- __init__.py
|       |-- main.py           # FastAPI application for the agent service
|       `-- tools.py          # Tool implementations and suggestion logic
|-- .gitignore
|-- requirements.txt
`-- run.sh                  # Script to run both services
```

**File Modifications:**

- **`foodly/core/db.py`**: New file containing `get_db`, `init_db`, and the database schema from `app.py`. The database file will be renamed to `foodly.db`.
- **`foodly/core/models.py`**: New file containing the Pydantic models from `agent_service.py`.
- **`foodly/core/calculations.py`**: New file containing `bmr_mifflin` and `compute_targets` from `app.py` and `agent_service.py`.
- **`foodly/app/main.py`**: This will be the refactored version of `app.py`. It will import from `foodly.core` and will only contain the FastAPI routes and UI logic.
- **`foodly/agent/main.py`**: This will be the refactored version of `agent_service.py`. It will import from `foodly.core` and will only contain the agent's FastAPI routes.
- **`foodly/agent/tools.py`**: New file containing the tool implementations (`tool_add_to_pantry`, `tool_consume`, etc.) and the `suggest_from_pantry` function from `agent_service.py`.
- **`requirements.txt`**: No changes needed.
- **`run.sh`**: New executable script to launch both services.

**Files to be Deleted:**
- `app.py`
- `agent_service.py`
- `static/` (will be moved)
- `templates/` (will be moved)
- `nutricoach.db` (will be replaced by `foodly.db`)

[Functions]
Functions will be reorganized into the new file structure.

**New Functions:**
- All functions will be moved from `app.py` and `agent_service.py` into the new structure. No new functions will be created from scratch.

**Modified Functions:**
- All functions will be updated to use the new import paths (e.g., `from foodly.core.db import get_db`).
- `init_db` in `foodly/core/db.py` will be modified to handle the new path to the database file (`foodly.db`).
- The FastAPI app initializations in `foodly/app/main.py` and `foodly/agent/main.py` will be updated to mount the `static` and `templates` directories from the correct new paths.

**Removed Functions:**
- The duplicated functions `get_db`, `bmr_mifflin`, and `compute_targets` will be removed from `app.py` and `agent_service.py` and replaced by imports from the `core` module.

[Classes]
Classes will be moved to the `core` module.

**Modified Classes:**
- The Pydantic models in `agent_service.py` will be moved to `foodly/core/models.py`.

[Dependencies]
No changes to dependencies are required.

[Testing]
No tests are included in this refactoring plan, but the new structure makes it easier to add unit tests for the `core` library functions in the future.

[Implementation Order]
The implementation will proceed in the following order to minimize disruption.

1.  Create the new directory structure (`foodly`, `foodly/core`, `foodly/app`, `foodly/agent`).
2.  Create `foodly/core/db.py` by moving the database logic from `app.py` and updating references to `foodly.db`.
3.  Create `foodly/core/models.py` by moving the Pydantic models from `agent_service.py`.
4.  Create `foodly/core/calculations.py` by moving the calculation logic from `app.py`.
5.  Create `foodly/agent/tools.py` by moving the tool logic from `agent_service.py`.
6.  Create `foodly/app/main.py` by refactoring `app.py` to use the `core` module.
7.  Create `foodly/agent/main.py` by refactoring `agent_service.py` to use the `core` and `tools` modules.
8.  Move the `templates` and `static` directories into `foodly/app/`.
9.  Create the `run.sh` script.
10. Delete the old monolithic files (`app.py`, `agent_service.py`) and the old database (`nutricoach.db`).
11. Verify that both services run correctly using `run.sh`.
