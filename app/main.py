"""Kvittens: todo-server med REST-API, MCP för Claude och morgonbongar på kvittoskrivare."""

import asyncio
import hmac
import io
import logging
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from . import printer, scheduler, tasks
from .config import get_settings
from .mcp_server import mcp
from .ticket import done_token, render_ticket

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


@app.get("/health")
def health():
    return {"ok": True}


# ---------- QR-koden på bongen ----------

def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>body{{font:18px/1.5 system-ui,sans-serif;max-width:28rem;margin:3rem auto;padding:0 16px;
background:#f6f3ec;color:#1d1b18}}h1{{font-size:1.5rem}}button{{font:inherit;font-weight:600;
padding:.8rem 1.4rem;border:0;border-radius:8px;background:#1d1b18;color:#fff;width:100%}}
.ticket{{background:#fff;padding:1rem;border:1px dashed #999;margin:1rem 0}}
@media(prefers-color-scheme:dark){{body{{background:#1b1a18;color:#eee}}.ticket{{background:#262421}}
button{{background:#eee;color:#111}}}}</style></head><body>{body}</body></html>""")


def _task_for_link(task_id: int, t: str) -> dict:
    if not hmac.compare_digest(t, done_token(task_id)):
        raise HTTPException(403, "Ogiltig länk")
    return _found(tasks.get_task(task_id))


@app.get("/done/{task_id}", response_class=HTMLResponse)
def done_page(task_id: int, t: str = ""):
    task = _task_for_link(task_id, t)
    ticket = f'<div class="ticket"><b>#{task_id:04d}</b><br>{escape(task["title"])}</div>'
    if task["status"] == "done":
        return _page("Redan klar", f"<h1>Redan klar ✓</h1>{ticket}<p>Släng lappen.</p>")
    form = f'<form method="post" action="/done/{task_id}?t={escape(t)}"><button>Markera som klar</button></form>'
    return _page("Klar?", f"<h1>Klar med bongen?</h1>{ticket}{form}")


@app.post("/done/{task_id}", response_class=HTMLResponse)
def done_submit(task_id: int, t: str = ""):
    task = _task_for_link(task_id, t)
    tasks.set_done(task_id, True)
    return _page("Klart!", f'<h1>Klart! ✓</h1><div class="ticket"><s>{escape(task["title"])}</s></div>'
                           "<p>Riv ner lappen och släng den.</p>")


# ---------- Webbgränssnitt ----------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


# MCP på /mcp. Monteras sist så att routerna ovan går först.
app.mount("/", McpAuth(mcp_app))
