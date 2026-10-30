"""Skriver ut morgonens bongar på inställd tid (PRINT_TIME, PRINT_DAYS)."""

import asyncio
import logging
from datetime import datetime, time, timedelta

from . import printer
from .config import get_settings
from .tasks import now

log = logging.getLogger("kvittens.scheduler")


def next_run(after: datetime) -> datetime:
    s = get_settings()
    hour, minute = (int(p) for p in s.print_time.split(":"))
    candidate = datetime.combine(after.date(), time(hour, minute), tzinfo=after.tzinfo)
    if candidate <= after:
        candidate += timedelta(days=1)
    while candidate.weekday() not in s.print_days:
        candidate += timedelta(days=1)
    return candidate


async def run_forever() -> None:
    if not get_settings().print_days:
        log.info("PRINT_DAYS är tom, ingen morgonutskrift")
        return
    while True:
        target = next_run(now())
        log.info("Nästa morgonutskrift: %s", target.isoformat(timespec="minutes"))
        await asyncio.sleep(max(0.0, (target - now()).total_seconds()))
        try:
            await asyncio.to_thread(printer.print_morning)
        except Exception:
            log.exception("Morgonutskriften misslyckades")
