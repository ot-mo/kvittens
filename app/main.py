"""Kvittens: todo-server med REST-API, MCP för Claude och morgonbongar på kvittoskrivare."""

import asyncio
import hmac
import io
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from . import journal, printer, scheduler, tasks
from .config import get_settings
from .mcp_server import mcp
from .ticket import render_ticket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("kvittens")
STATIC = Path(__file__).parent / "static"


def _key_ok(request: Request) -> bool:
    key = get_settings().api_key
    if not key:
        return True
    given = request.headers.get("x-api-key", "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        given = auth[7:]
    return hmac.compare_digest(given.strip(), key)


def require_key(request: Request) -> None:
    if not _key_ok(request):
        raise HTTPException(401, "Fel eller saknad API-nyckel")


class McpAuth:
    """Samma API-nyckel gäller för MCP-endpointen som för REST-API:t."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not _key_ok(Request(scope)):
            await Response("Fel eller saknad API-nyckel", 401)(scope, receive, send)
            return
        await self.app(scope, receive, send)


mcp_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    # Skyddet mot DNS rebinding tillåter bara localhost; vi skyddar med API-nyckel i stället.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    tasks.init_db()
    if not s.api_key:
        log.warning("API_KEY är inte satt – vem som helst på nätverket kan ändra listan")
    log.info("Skrivare: %s, data: %s", s.printer_type, s.data_dir)
    job = asyncio.create_task(scheduler.run_forever())
    async with mcp.session_manager.run():
        yield
    job.cancel()


app = FastAPI(title="Kvittens", lifespan=lifespan)
api = Depends(require_key)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = ""
    project: str = ""
    priority: int = Field(3, ge=1, le=4)
    due: str | None = None
    source: str = "api"


class TaskPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    notes: str | None = None
    project: str | None = None
    priority: int | None = Field(None, ge=1, le=4)
    due: str | None = None


def _found(task: dict | None) -> dict:
    if task is None:
        raise HTTPException(404, "Uppgiften finns inte")
    return task


def _run(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(422, str(e))


# ---------- REST-API ----------

@app.get("/api/tasks", dependencies=[api])
def list_tasks(status: Literal["open", "done", "all"] = "open", project: str | None = None):
    return tasks.list_tasks(status, project)


@app.post("/api/tasks", dependencies=[api], status_code=201)
def create_task(body: TaskIn):
    return _run(lambda: tasks.create_task(**body.model_dump()))


@app.get("/api/tasks/{task_id}", dependencies=[api])
def get_task(task_id: int):
    return _found(tasks.get_task(task_id))


@app.patch("/api/tasks/{task_id}", dependencies=[api])
def update_task(task_id: int, body: TaskPatch):
    return _found(_run(lambda: tasks.update_task(task_id, **body.model_dump(exclude_unset=True))))


@app.post("/api/tasks/{task_id}/done", dependencies=[api])
def complete_task(task_id: int):
    return _found(tasks.set_done(task_id, True))


@app.post("/api/tasks/{task_id}/reopen", dependencies=[api])
def reopen_task(task_id: int):
    return _found(tasks.set_done(task_id, False))


@app.delete("/api/tasks/{task_id}", dependencies=[api], status_code=204)
def delete_task(task_id: int):
    if not tasks.delete_task(task_id):
        raise HTTPException(404, "Uppgiften finns inte")


@app.get("/api/tasks/{task_id}/ticket.png", dependencies=[api])
def ticket_png(task_id: int):
    buf = io.BytesIO()
    render_ticket(_found(tasks.get_task(task_id))).save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.post("/api/tasks/{task_id}/print", dependencies=[api])
async def print_one(task_id: int):
    task = _found(tasks.get_task(task_id))
    return {"printed": await _print([task])}


@app.get("/api/morning", dependencies=[api])
def morning_preview():
    s = get_settings()
    return {
        "next_run": scheduler.next_run(tasks.now()).isoformat(timespec="minutes"),
        "printer": s.printer_type,
        "max_tickets": s.max_tickets,
        "tasks": tasks.morning_selection(),
    }


@app.post("/api/morning/print", dependencies=[api])
async def morning_print_now():
    return {"printed": await _print(tasks.morning_selection())}


async def _print(selected: list[dict]) -> list[int]:
    try:
        return await asyncio.to_thread(printer.print_tasks, selected)
    except Exception as e:
        log.exception("Utskrift misslyckades")
        raise HTTPException(502, f"Kunde inte skriva ut: {e}")


# ---------- Kvällsdagbok ----------

class JournalIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.get("/api/journal", dependencies=[api])
def list_journal(limit: int = 30):
    s = get_settings()
    return {
        "evening_time": s.evening_time,
        "today": tasks.today().isoformat(),
        "has_entry_today": journal.has_entry_today(),
        "claude": s.claude_enabled,
        "entries": journal.list_entries(limit),
    }


@app.post("/api/journal", dependencies=[api], status_code=201)
async def add_journal(body: JournalIn):
    try:
        return await asyncio.to_thread(journal.add_entry, body.text)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/journal/{entry_id}/undo", dependencies=[api])
def undo_journal(entry_id: int):
    entry = journal.undo_entry(entry_id)
    if entry is None:
        raise HTTPException(404, "Inlägget finns inte")
    return entry


@app.get("/health")
def health():
    return {"ok": True}


# ---------- Webbgränssnitt ----------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


# MCP på /mcp. Monteras sist så att routerna ovan går först.
app.mount("/", McpAuth(mcp_app))
