# Task Manager API

A RESTful API for managing tasks, built with **Flask** and **SQLite**, with input
validation, filtering, and an automated **pytest** test suite.

## Features

- Full CRUD on tasks (`title`, `priority`, `due_date`, `done`)
- Validation with clear `400` error messages (bad priority, bad dates, empty titles, non-JSON bodies)
- Filtering by status and priority; results sorted by due date (undated tasks last)
- `/stats` endpoint with total / done / open / overdue counts
- Parameterized SQL everywhere (no SQL injection)
- App-factory pattern so tests run against an isolated temporary database

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/tasks` | List tasks. Optional `?done=true` / `?priority=high` |
| POST   | `/tasks` | Create a task |
| GET    | `/tasks/<id>` | Get one task |
| PATCH  | `/tasks/<id>` | Update any fields |
| DELETE | `/tasks/<id>` | Delete a task |
| GET    | `/stats` | Summary counts |

### Example

```bash
curl -X POST http://127.0.0.1:5000/tasks -H "Content-Type: application/json" \
     -d "{\"title\": \"Finish lab report\", \"priority\": \"high\", \"due_date\": \"2026-12-01\"}"
```

```json
{"id": 1, "title": "Finish lab report", "priority": "high", "due_date": "2026-12-01", "done": false}
```

## Tests

```bash
python -m pytest -v
```
