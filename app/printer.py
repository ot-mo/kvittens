"""Skickar bongar till kvittoskrivaren (eller bara sparar dem som bilder)."""

import logging
import threading

from . import tasks
from .config import get_settings
from .ticket import render_ticket

log = logging.getLogger("kvittens.printer")
_lock = threading.Lock()  # två utskrifter samtidigt blir sallad på pappret


def _open_printer():
    s = get_settings()
    kwargs = {"profile": s.printer_profile} if s.printer_profile else {}
    if s.printer_type == "network":
        from escpos.printer import Network
        return Network(s.printer_host, port=s.printer_port, timeout=15, **kwargs)
    if s.printer_type == "usb":
        from escpos.printer import Usb
        return Usb(s.usb_vendor, s.usb_product, **kwargs)
    raise ValueError(f"Okänd PRINTER_TYPE: {s.printer_type}")


def print_tasks(task_list: list[dict]) -> list[int]:
    """Skriver ut en bong per uppgift. Returnerar id:n som skrevs ut.

    Varje bong sparas också som PNG i data/tickets, även i preview-läget.
    """
    if not task_list:
        return []
    s = get_settings()
    printed: list[int] = []
    with _lock:
        printer = None if s.printer_type == "preview" else _open_printer()
        try:
            for task in task_list:
                image = render_ticket(task)
                image.save(s.ticket_dir / f"{task['id']}.png")
                if printer:
                    printer.image(image, center=False)
                    printer.cut()
                tasks.mark_printed(task["id"])
                printed.append(task["id"])
        finally:
            if printer:
                printer.close()
    log.info("Skrev ut %d bongar (%s): %s", len(printed), s.printer_type, printed)
    return printed


def print_morning() -> list[int]:
    return print_tasks(tasks.morning_selection())
