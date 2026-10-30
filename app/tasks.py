"""Uppgifter i SQLite. Används av både REST-API:t, MCP-servern och schemat."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import get_settings

PRIORITIES = {1: "Brådskande", 2: "Hög", 3: "Normal", 4: "Låg"}
EDITABLE = ("title", "notes", "project", "priority", "due")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    notes       TEXT    NOT NULL DEFAULT '',
    project     TEXT    NOT NULL DEFAULT '',
    priority    INTEGER NOT NULL DEFAULT 3,
    due         TEXT,
    status      TEXT    NOT NULL DEFAULT 'open',
    source      TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    done_at     TEXT,
    printed_at  TEXT
);

CREATE TABLE IF NOT EXISTS journal (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    day         TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    reply       TEXT    NOT NULL DEFAULT '',
    completed   TEXT    NOT NULL DEFAULT '[]',
    created     TEXT    NOT NULL DEFAULT '[]',
    source      TEXT    NOT NULL DEFAULT 'web',
    undone_at   TEXT
);
"""


def now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def today() -> date:
    return now().date()


@contextmanager
def connect():
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _validate(fields: dict) -> dict:
    if "title" in fields:
        fields["title"] = (fields["title"] or "").strip()
        if not fields["title"]:
            raise ValueError("Titeln får inte vara tom")
    if fields.get("priority") is not None and fields["priority"] not in PRIORITIES:
        raise ValueError("Prioritet måste vara 1 (brådskande) till 4 (låg)")
    if fields.get("due"):
        try:
            fields["due"] = date.fromisoformat(str(fields["due"])).isoformat()
        except ValueError:
            raise ValueError(f"Ogiltigt datum '{fields['due']}', använd ÅÅÅÅ-MM-DD") from None
    elif "due" in fields:
        fields["due"] = None
    for key in ("notes", "project"):
        if key in fields:
            fields[key] = (fields[key] or "").strip()
    return fields


def list_tasks(status: str = "open", project: str | None = None) -> list[dict]:
    sql = "SELECT * FROM tasks WHERE 1=1"
    args: list = []
    if status != "all":
        sql += " AND status = ?"
        args.append(status)
    if project:
        sql += " AND project = ? COLLATE NOCASE"
        args.append(project)
    if status == "done":
        sql += " ORDER BY done_at DESC LIMIT 200"
    else:
        sql += " ORDER BY priority, COALESCE(due, '9999-12-31'), id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args)]


def get_task(task_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def create_task(title: str, notes: str = "", project: str = "", priority: int = 3,
                due: str | None = None, source: str = "") -> dict:
    fields = _validate({"title": title, "notes": notes, "project": project,
                        "priority": priority, "due": due})
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, notes, project, priority, due, source, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fields["title"], fields["notes"], fields["project"], fields["priority"],
             fields["due"], source, now().isoformat(timespec="seconds")),
        )
        task_id = cur.lastrowid
    return get_task(task_id)


def update_task(task_id: int, **changes) -> dict | None:
    fields = _validate({k: v for k, v in changes.items() if k in EDITABLE})
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        with connect() as conn:
            conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", (*fields.values(), task_id))
    return get_task(task_id)


def set_done(task_id: int, done: bool = True, keep_printed: bool = False) -> dict | None:
    with connect() as conn:
        if done:
            conn.execute("UPDATE tasks SET status = 'done', done_at = ? WHERE id = ?",
                         (now().isoformat(timespec="seconds"), task_id))
        elif keep_printed:
            # Ångrad avbockning: lappen sitter troligen kvar i skenan
            conn.execute("UPDATE tasks SET status = 'open', done_at = NULL WHERE id = ?", (task_id,))
        else:
            # Återöppnad uppgift har ingen lapp i skenan längre, så den får skrivas ut igen.
            conn.execute("UPDATE tasks SET status = 'open', done_at = NULL, printed_at = NULL"
                         " WHERE id = ?", (task_id,))
    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    with connect() as conn:
        return conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0


def mark_printed(task_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE tasks SET printed_at = ? WHERE id = ?",
                     (now().isoformat(timespec="seconds"), task_id))


def morning_selection(limit: int | None = None) -> list[dict]:
    """Uppgifterna som ska bli bongar: öppna, inte redan i skenan, inte framtida.

    Försenade och dagens först, sedan efter prioritet.
    """
    limit = limit if limit is not None else get_settings().max_tickets
    day = today().isoformat()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status = 'open' AND printed_at IS NULL AND (due IS NULL OR due <= :day)
            ORDER BY CASE WHEN due IS NOT NULL THEN 0 ELSE 1 END,
                     priority, COALESCE(due, '9999-12-31'), id
            LIMIT :limit
            """,
            {"day": day, "limit": limit},
        )
        return [dict(r) for r in rows]
