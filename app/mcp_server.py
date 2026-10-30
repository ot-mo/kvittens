"""MCP-server så att Claude (och andra AI-klienter) kan läsa och ändra todo-listan."""

import asyncio
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import journal, printer, tasks

mcp = MCPServer(
    name="kvittens",
    instructions=(
        "Kvittens är användarens todo-lista. Varje morgon skrivs de viktigaste öppna "
        "uppgifterna ut som restaurangbongar på en kvittoskrivare. Prioritet: 1 = brådskande, "
        "2 = hög, 3 = normal, 4 = låg. Projekt visas som 'bord' på bongen. Datum i formatet "
        "ÅÅÅÅ-MM-DD. Håll titlar korta – de ska få plats på en kvittolapp."
    ),
)


def _require(task: dict | None, task_id: int) -> dict:
    if task is None:
        raise ToolError(f"Det finns ingen uppgift med id {task_id}")
    return task


def _checked(fn, *args, **kwargs):
    """Skicka valideringsfel (t.ex. fel datumformat) vidare så att Claude ser dem."""
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
def list_tasks(status: Literal["open", "done", "all"] = "open", project: str | None = None) -> list[dict]:
    """Lista uppgifter. Som standard bara öppna. printed_at visar om lappen sitter i bongskenan."""
    return tasks.list_tasks(status, project)


@mcp.tool()
def add_task(title: str, notes: str = "", project: str = "", priority: int = 3,
             due: str | None = None) -> dict:
    """Lägg till en uppgift. due är valfritt datum (ÅÅÅÅ-MM-DD)."""
    return _checked(tasks.create_task, title, notes, project, priority, due, source="claude")


@mcp.tool()
def update_task(task_id: int, title: str | None = None, notes: str | None = None,
                project: str | None = None, priority: int | None = None,
                due: str | None = None) -> dict:
    """Ändra en uppgift. Bara fälten du skickar med ändras. due="" tar bort deadline."""
    changes = {k: v for k, v in dict(title=title, notes=notes, project=project,
                                     priority=priority, due=due).items() if v is not None}
    return _require(_checked(tasks.update_task, task_id, **changes), task_id)


@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Markera en uppgift som klar."""
    return _require(tasks.set_done(task_id, True), task_id)


@mcp.tool()
def reopen_task(task_id: int) -> dict:
    """Öppna en klar uppgift igen. Den skrivs då ut på nytt nästa morgon."""
    return _require(tasks.set_done(task_id, False), task_id)


@mcp.tool()
def delete_task(task_id: int) -> str:
    """Ta bort en uppgift helt."""
    if not tasks.delete_task(task_id):
        raise ToolError(f"Det finns ingen uppgift med id {task_id}")
    return f"Uppgift {task_id} borttagen"


@mcp.tool()
def read_journal(limit: int = 14) -> list[dict]:
    """Läs dagboken, nyast först. source "kväll" är kvällsgenomgångar: text är användarens
    ord om dagen och reply är reflektionen och fokus som skrevs då. source "web" är korta
    anteckningar från webbsidan. completed/created visar vilka uppgifter inlägget ändrade."""
    return journal.list_entries(limit)


@mcp.tool()
def write_journal_entry(text: str, reflection: str = "", complete_task_ids: list[int] | None = None,
                        new_tasks: list[journal.NewTask] | None = None) -> dict:
    """Spara kvällens dagboksinlägg och uppdatera listan i samma steg.

    text: användarens egna ord om dagen. reflection: din korta sammanfattning och vad
    användaren bör fokusera på kommande dagar – nästa kvällsgenomgång läser den.
    complete_task_ids: öppna uppgifter som är klara. new_tasks: nya uppgifter att lägga till.
    Allt i inlägget kan ångras tillsammans från webbsidan.
    """
    return _checked(journal.add_entry, text, reflection, complete_task_ids or [],
                    new_tasks or [], source="kväll")


@mcp.tool()
def preview_morning_tickets() -> list[dict]:
    """Visa vilka uppgifter som skulle skrivas ut som bongar om morgonutskriften kördes nu."""
    return tasks.morning_selection()


@mcp.tool()
async def print_tickets(task_ids: list[int] | None = None) -> str:
    """Skriv ut bongar direkt. Utan task_ids körs morgonurvalet nu; med task_ids skrivs
    just de uppgifterna ut (även om de redan skrivits ut, t.ex. om en lapp tappats bort)."""
    if task_ids:
        selected = [_require(tasks.get_task(i), i) for i in task_ids]
    else:
        selected = tasks.morning_selection()
    printed = await asyncio.to_thread(printer.print_tasks, selected)
    return f"Skrev ut {len(printed)} bongar: {printed}" if printed else "Inget att skriva ut"
