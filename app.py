"""Task Manager REST API — Flask + SQLite.

Run:   python app.py            (serves on http://127.0.0.1:5000)
Test:  python -m pytest
"""

from __future__ import annotations

import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

VALID_PRIORITIES = {"low", "medium", "high"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT    NOT NULL,
    priority  TEXT    NOT NULL DEFAULT 'medium',
    due_date  TEXT,
    done      INTEGER NOT NULL DEFAULT 0
);
"""


def create_app(db_path: str = "tasks.db") -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    def row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["done"] = bool(d["done"])
        return d

    def error(message: str, status: int):
        return jsonify({"error": message}), status

    def validate(data: dict, partial: bool) -> str | None:
        """Return an error message, or None if the payload is valid."""
        if not partial or "title" in data:
            title = data.get("title")
            if not isinstance(title, str) or not title.strip():
                return "title is required and must be a non-empty string"
        if "priority" in data and data["priority"] not in VALID_PRIORITIES:
            return f"priority must be one of {sorted(VALID_PRIORITIES)}"
        if data.get("due_date") is not None:
            try:
                date.fromisoformat(data["due_date"])
            except (TypeError, ValueError):
                return "due_date must be YYYY-MM-DD"
        if "done" in data and not isinstance(data["done"], bool):
            return "done must be true or false"
        return None

    def fetch(task_id: int):
        return get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    @app.get("/tasks")
    def list_tasks():
        query = "SELECT * FROM tasks"
        clauses, params = [], []
        if "done" in request.args:
            clauses.append("done = ?")
            params.append(1 if request.args["done"].lower() == "true" else 0)
        if "priority" in request.args:
            clauses.append("priority = ?")
            params.append(request.args["priority"])
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY due_date IS NULL, due_date, id"
        rows = get_db().execute(query, params).fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.post("/tasks")
    def create_task():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("request body must be a JSON object", 400)
        msg = validate(data, partial=False)
        if msg:
            return error(msg, 400)
        db = get_db()
        cur = db.execute(
            "INSERT INTO tasks (title, priority, due_date, done) VALUES (?, ?, ?, ?)",
            (data["title"].strip(), data.get("priority", "medium"),
             data.get("due_date"), int(data.get("done", False))),
        )
        db.commit()
        return jsonify(row_to_dict(fetch(cur.lastrowid))), 201

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id: int):
        row = fetch(task_id)
        return jsonify(row_to_dict(row)) if row else error("task not found", 404)

    @app.patch("/tasks/<int:task_id>")
    def update_task(task_id: int):
        if fetch(task_id) is None:
            return error("task not found", 404)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("request body must be a JSON object", 400)
        msg = validate(data, partial=True)
        if msg:
            return error(msg, 400)
        fields = {k: data[k] for k in ("title", "priority", "due_date", "done") if k in data}
        if "title" in fields:
            fields["title"] = fields["title"].strip()
        if "done" in fields:
            fields["done"] = int(fields["done"])
        if fields:
            assignments = ", ".join(f"{k} = ?" for k in fields)
            db = get_db()
            db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", (*fields.values(), task_id))
            db.commit()
        return jsonify(row_to_dict(fetch(task_id)))

    @app.delete("/tasks/<int:task_id>")
    def delete_task(task_id: int):
        db = get_db()
        cur = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()
        return ("", 204) if cur.rowcount else error("task not found", 404)

    @app.get("/stats")
    def stats():
        row = get_db().execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done, "
            "COALESCE(SUM(CASE WHEN done = 0 AND due_date < ? THEN 1 ELSE 0 END), 0) AS overdue "
            "FROM tasks", (date.today().isoformat(),)
        ).fetchone()
        return jsonify({"total": row["total"], "done": row["done"],
                        "open": row["total"] - row["done"], "overdue": row["overdue"]})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
