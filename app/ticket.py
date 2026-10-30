"""Ritar en uppgift som en restaurangbong (svartvit bild i skrivarens bredd).

Bongen skrivs ut som bild i stället för text, så att åäö, stora rubriker och
QR-koden ser likadana ut oavsett skrivarmodell.
"""

import hashlib
import hmac
from datetime import date
from functools import lru_cache
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from .config import get_settings
from .tasks import PRIORITIES, now, today

WEEKDAYS = ["mån", "tis", "ons", "tor", "fre", "lör", "sön"]
MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]

FONT_FILES = {
    "bold": ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"],
    "regular": ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf"],
    "mono": ["DejaVuSansMono-Bold.ttf", "consolab.ttf", "Courier New Bold.ttf"],
}
FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/TTF",
    "C:/Windows/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
]


@lru_cache
def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    dirs = [get_settings().font_dir, *FONT_DIRS]
    for d in filter(None, dirs):
        for name in FONT_FILES[kind]:
            path = Path(d) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def done_token(task_id: int) -> str:
    key = get_settings().secret.encode()
    return hmac.new(key, f"done:{task_id}".encode(), hashlib.sha256).hexdigest()[:20]


def done_url(task_id: int) -> str | None:
    base = get_settings().public_url
    return f"{base}/done/{task_id}?t={done_token(task_id)}" if base else None


def format_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def describe_due(due: str | None) -> str | None:
    if not due:
        return None
    d = date.fromisoformat(due)
    diff = (d - today()).days
    if diff == 0:
        return "IDAG"
    if diff == 1:
        return "imorgon"
    if diff < 0:
        return f"FÖRSENAD {-diff} d"
    return format_date(d)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            # Ord som är längre än raden bryts tecken för tecken.
            while draw.textlength(word, font=font) > width:
                cut = len(word)
                while cut > 1 and draw.textlength(word[:cut], font=font) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        lines.append(line)
    return lines


def render_ticket(task: dict) -> Image.Image:
    W = get_settings().paper_width_px
    s = W / 576  # allt är ritat för 80 mm-papper och skalas för 58 mm
    m = round(14 * s)
    inner = W - 2 * m

    img = Image.new("L", (W, 4000), 255)
    draw = ImageDraw.Draw(img)
    y = m

    def text(xy, value, font, fill=0, anchor="la"):
        draw.text(xy, value, font=font, fill=fill, anchor=anchor)

    def dashed(y_pos: int) -> int:
        dash = round(10 * s)
        for x in range(m, W - m, dash * 2):
            draw.line([(x, y_pos), (min(x + dash, W - m), y_pos)], fill=0, width=max(2, round(3 * s)))
        return y_pos + round(18 * s)

    def bar(y_pos: int, label: str, font) -> int:
        h = round(font.size * 1.5)
        draw.rectangle([m, y_pos, W - m, y_pos + h], fill=0)
        text((m + round(12 * s), y_pos + h // 2), label, font, fill=255, anchor="lm")
        return y_pos + h + round(14 * s)

    # Huvud: ordernummer till vänster, tid och datum till höger
    stamp = now()
    num_font = _font("mono", round(64 * s))
    small = _font("regular", round(24 * s))
    small_bold = _font("bold", round(26 * s))
    text((m, y), f"#{task['id']:04d}", num_font)
    text((W - m, y + round(4 * s)), stamp.strftime("%H:%M"), _font("mono", round(34 * s)), anchor="ra")
    text((W - m, y + round(44 * s)), format_date(stamp.date()), small, anchor="ra")
    y += round(84 * s)

    # "Bord" = projekt
    table = (task.get("project") or "").strip()
    y = bar(y, f"BORD: {table.upper()}" if table else "BORD: —", _font("bold", round(30 * s)))

    # Själva beställningen
    title_font = _font("bold", round(50 * s))
    for line in _wrap(draw, task["title"], title_font, inner):
        text((m, y), line, title_font)
        y += round(title_font.size * 1.18)
    y += round(8 * s)

    if notes := (task.get("notes") or "").strip():
        y = dashed(y)
        notes_font = _font("regular", round(28 * s))
        for line in _wrap(draw, notes, notes_font, inner):
            text((m, y), line, notes_font)
            y += round(notes_font.size * 1.3)
        y += round(6 * s)

    y = dashed(y)

    # Prioritet och deadline
    prio = task.get("priority") or 3
    prio_label = {1: "!!! BRÅDSKANDE", 2: "!! HÖG"}.get(prio, PRIORITIES[prio].upper())
    due_label = describe_due(task.get("due"))
    if prio <= 2:
        y = bar(y, prio_label, _font("bold", round(32 * s)))
    else:
        text((m, y), f"PRIO: {prio_label}", small_bold)
        y += round(40 * s)
    if due_label:
        text((m, y), f"DEADLINE: {due_label}", _font("bold", round(34 * s)))
        y += round(48 * s)

    # QR-kod som bockar av uppgiften
    if url := done_url(task["id"]):
        y += round(6 * s)
        qr = qrcode.QRCode(border=0, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        size = round(170 * s)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")
        qr_img = qr_img.resize((size, size), Image.NEAREST)
        img.paste(qr_img, (m, y))
        tx = m + size + round(20 * s)
        text((tx, y + round(30 * s)), "Klar?", _font("bold", round(36 * s)))
        text((tx, y + round(80 * s)), "Skanna koden,", small)
        text((tx, y + round(112 * s)), "släng lappen.", small)
        y += size + round(16 * s)

    source = task.get("source") or ""
    footer = f"kvittens{' · från ' + source if source else ''}"
    text((W // 2, y + round(6 * s)), footer, _font("regular", round(20 * s)), anchor="ma")
    y += round(60 * s)

    img = img.crop((0, 0, W, y))
    # Hård tröskel: skarpare text på termopapper än dithering
    return img.point(lambda v: 0 if v < 140 else 255, mode="1")
