"""Dagbok. Kvällssessionen i Claude Code skriver ett inlägg per kväll via MCP och bockar
samtidigt av och lägger till uppgifter. Från webbsidan kan du skriva korta anteckningar
som kvällssessionen läser."""

import json
import logging

from pydantic import BaseModel, Field

from . import tasks

log = logging.getLogger("kvittens.journal")


class NewTask(BaseModel):
    title: str = Field(description="Kort titel i imperativ, helst under 40 tecken")
    notes: str = Field("", description="En rad om var man börjar")
    project: str = ""
    priority: int = Field(3, ge=1, le=4, description="1 brådskande, 2 hög, 3 normal, 4 låg")
    due: str | None = Field(None, description="ÅÅÅÅ-MM-DD eller null")


def _row(r) -> dict:
    entry = dict(r)
    entry["completed"] = json.loads(entry["completed"])
    entry["created"] = json.loads(entry["created"])
    return entry


def list_entries(limit: int = 30) -> list[dict]:
    with tasks.connect() as conn:
        rows = conn.execute("SELECT * FROM journal ORDER BY id DESC LIMIT ?", (limit,))
        return [_row(r) for r in rows]


def get_entry(entry_id: int) -> dict | None:
    with tasks.connect() as conn:
        row = conn.execute("SELECT * FROM journal WHERE id = ?", (entry_id,)).fetchone()
    return _row(row) if row else None


def add_entry(text: str, reflection: str = "", complete_task_ids: list[int] = (),
              new_tasks: list[NewTask] = (), source: str = "web") -> dict:
    """Sparar inlägget och genomför ändringarna, så att de kan ångras tillsammans."""
    text = text.strip()
    if not text:
        raise ValueError("Inlägget får inte vara tomt")
    # Kontrollera allt innan något ändras, så att inget blir halvgjort
    for new in new_tasks:
        tasks._validate(new.model_dump())
    open_ids = {t["id"] for t in tasks.list_tasks("open")}
    completed: list[dict] = []
    created: list[dict] = []
    for task_id in dict.fromkeys(complete_task_ids):
        if task_id in open_ids:
            task = tasks.set_done(task_id, True)
            completed.append({"id": task_id, "title": task["title"]})
    for new in new_tasks:
        task = tasks.create_task(new.title, new.notes, new.project, new.priority, new.due,
                                 source=source)
        created.append({"id": task["id"], "title": task["title"]})

    with tasks.connect() as conn:
        cur = conn.execute(
            "INSERT INTO journal (day, text, created_at, reply, completed, created, source)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tasks.today().isoformat(), text, tasks.now().isoformat(timespec="seconds"),
             reflection.strip(), json.dumps(completed, ensure_ascii=False),
             json.dumps(created, ensure_ascii=False), source),
        )
        entry_id = cur.lastrowid
    return get_entry(entry_id)


def undo_entry(entry_id: int) -> dict | None:
    """Ångrar avbockningar och nya uppgifter från inlägget. Själva texten finns kvar."""
    entry = get_entry(entry_id)
    if entry is None or entry["undone_at"]:
        return entry
    for item in entry["completed"]:
        tasks.set_done(item["id"], False, keep_printed=True)
    for item in entry["created"]:
        tasks.delete_task(item["id"])
    with tasks.connect() as conn:
        conn.execute("UPDATE journal SET undone_at = ? WHERE id = ?",
                     (tasks.now().isoformat(timespec="seconds"), entry_id))
    return get_entry(entry_id)
