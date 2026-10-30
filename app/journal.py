"""Kvällsdagbok: du skriver fritt om dagen, Claude bockar av klara uppgifter och
lägger till nya. Varje inlägg sparas så att det också fungerar som dagbok."""

import json
import logging
from datetime import date

import anthropic
from pydantic import BaseModel, Field

from . import tasks
from .config import get_settings
from .ticket import format_date

log = logging.getLogger("kvittens.journal")

# Modeller som stödjer fallbacks="default" när en förfrågan nekas
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}

SYSTEM = """\
Du är assistenten i Kvittens, användarens todo-lista. Varje morgon skrivs de viktigaste \
uppgifterna ut som restaurangbongar som sätts upp i en bongskena. På kvällen skriver \
användaren fritt om hur dagen gått, som en dagbok. Din uppgift är att läsa texten och:

1. completed_task_ids: id för de öppna uppgifter som texten säger är klara. Ta bara med \
sådant som tydligt är gjort. Är du osäker, låt bli – det är bättre att användaren bockar \
av själv än att fel lapp bockas av.
2. new_tasks: nya saker användaren säger att den behöver eller ska göra och som inte \
redan finns bland de öppna uppgifterna. Bara konkreta saker, inte känslor eller \
reflektioner. Korta titlar (helst under 40 tecken) i imperativ, eftersom de ska få plats \
på en kvittolapp. Sätt due (ÅÅÅÅ-MM-DD) bara om en dag eller ett datum nämns, räknat från \
dagens datum. Sätt project bara om ett befintligt projekt passar uppenbart, annars tom \
sträng. priority: 1 brådskande, 2 hög, 3 normal, 4 låg – 3 om inget annat framgår. notes \
får vara tom sträng.
3. reply: ett kort, personligt svar på svenska (1–3 meningar) som kvitterar dagen. \
Räkna inte upp vad du bockat av eller lagt till; det visas separat.
"""


class NewTask(BaseModel):
    title: str
    notes: str
    project: str
    priority: int = Field(ge=1, le=4)
    due: str | None


class DayReview(BaseModel):
    completed_task_ids: list[int]
    new_tasks: list[NewTask]
    reply: str


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


def has_entry_today() -> bool:
    with tasks.connect() as conn:
        return conn.execute("SELECT 1 FROM journal WHERE day = ?",
                            (tasks.today().isoformat(),)).fetchone() is not None


def _describe(task: dict) -> str:
    parts = [f"#{task['id']}"]
    if task["project"]:
        parts.append(f"[{task['project']}]")
    parts.append(task["title"])
    extra = []
    if task["due"]:
        extra.append(f"deadline {task['due']}")
    if task["printed_at"]:
        extra.append("sitter i bongskenan")
    if extra:
        parts.append(f"({', '.join(extra)})")
    line = " ".join(parts)
    if task["notes"]:
        line += f"\n    Anteckning: {task['notes']}"
    return line


def review_day(text: str, open_tasks: list[dict], day: date) -> DayReview:
    s = get_settings()
    task_list = "\n".join(_describe(t) for t in open_tasks) or "(inga öppna uppgifter)"
    prompt = (f"Idag är {format_date(day)} {day.year} ({day.isoformat()}).\n\n"
              f"Öppna uppgifter:\n{task_list}\n\n"
              f"<dagbok>\n{text}\n</dagbok>")
    extra = {}
    if s.claude_model in FALLBACK_MODELS:
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = anthropic.Anthropic().beta.messages.parse(
        model=s.claude_model,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=DayReview,
        **extra,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Claude kunde inte tolka texten ({response.stop_reason})")
    return response.parsed_output


def add_entry(text: str) -> dict:
    """Sparar inlägget, låter Claude tolka det och genomför ändringarna."""
    text = text.strip()
    if not text:
        raise ValueError("Skriv något om dagen först")
    day = tasks.today()
    open_tasks = tasks.list_tasks("open")
    completed: list[dict] = []
    created: list[dict] = []

    if not get_settings().claude_enabled:
        reply = "Sparat i dagboken. (Ingen ANTHROPIC_API_KEY är inställd, så inget bockades av.)"
    else:
        try:
            review = review_day(text, open_tasks, day)
        except (anthropic.APIError, RuntimeError) as e:
            log.exception("Claude-anropet misslyckades")
            review = None
            reply = f"Sparat i dagboken, men Claude kunde inte läsa det just nu: {e}"
        if review:
            reply = review.reply
            open_ids = {t["id"] for t in open_tasks}
            for task_id in dict.fromkeys(review.completed_task_ids):
                if task_id in open_ids:
                    task = tasks.set_done(task_id, True)
                    completed.append({"id": task_id, "title": task["title"]})
            for new in review.new_tasks:
                try:
                    task = tasks.create_task(new.title, new.notes, new.project, new.priority,
                                             new.due, source="dagbok")
                except ValueError:
                    log.warning("Hoppade över ogiltig ny uppgift: %s", new)
                    continue
                created.append({"id": task["id"], "title": task["title"]})

    with tasks.connect() as conn:
        cur = conn.execute(
            "INSERT INTO journal (day, text, created_at, reply, completed, created)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (day.isoformat(), text, tasks.now().isoformat(timespec="seconds"), reply,
             json.dumps(completed, ensure_ascii=False), json.dumps(created, ensure_ascii=False)),
        )
        entry_id = cur.lastrowid
    return get_entry(entry_id)


def undo_entry(entry_id: int) -> dict | None:
    """Ångrar vad Claude gjorde. Själva dagbokstexten finns kvar."""
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
