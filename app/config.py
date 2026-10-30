"""Inställningar som läses från miljövariabler (se .env.example)."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _hex_or_int(value: str) -> int:
    return int(value, 16) if value.lower().startswith("0x") else int(value or 0)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_key: str
    timezone: str
    print_time: str
    print_days: frozenset[int]
    max_tickets: int
    printer_type: str  # preview | network | usb
    printer_host: str
    printer_port: int
    printer_profile: str
    usb_vendor: int
    usb_product: int
    paper_width_px: int
    font_dir: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "kvittens.db"

    @property
    def ticket_dir(self) -> Path:
        return self.data_dir / "tickets"


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(_env("DATA_DIR", "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "tickets").mkdir(exist_ok=True)

    days = _env("PRINT_DAYS", "mon,tue,wed,thu,fri,sat,sun").lower()
    print_days = frozenset(DAY_NAMES.index(d.strip()[:3]) for d in days.split(",") if d.strip())

    return Settings(
        data_dir=data_dir,
        api_key=_env("API_KEY"),
        timezone=_env("TZ", "Europe/Stockholm"),
        print_time=_env("PRINT_TIME", "07:00"),
        print_days=print_days,
        max_tickets=int(_env("MAX_TICKETS", "5")),
        printer_type=_env("PRINTER_TYPE", "preview").lower(),
        printer_host=_env("PRINTER_HOST"),
        printer_port=int(_env("PRINTER_PORT", "9100")),
        printer_profile=_env("PRINTER_PROFILE"),
        usb_vendor=_hex_or_int(_env("USB_VENDOR", "0")),
        usb_product=_hex_or_int(_env("USB_PRODUCT", "0")),
        paper_width_px=int(_env("PAPER_WIDTH_PX", "576")),
        font_dir=_env("FONT_DIR"),
    )
