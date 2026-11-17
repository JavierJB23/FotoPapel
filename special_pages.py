"""Portadas, separadores y páginas en blanco para Revelo.

El estilo es información estructurada: se guarda en los proyectos y se vuelve a
renderizar al tamaño de papel elegido. El PNG temporal solo sirve de miniatura.
"""
from __future__ import annotations

from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont

KINDS = ("Portada", "Separador", "Página en blanco")
THEMES = {
    "Azul noche": {"background": "#0B1928", "text": "#F5F0E6", "accent": "#4CD9B5", "muted": "#B7C9D1"},
    "Crema": {"background": "#F6EBDC", "text": "#443427", "accent": "#AD7548", "muted": "#76665C"},
    "Blanco": {"background": "#FFFFFF", "text": "#20364D", "accent": "#1F9C89", "muted": "#687987"},
    "Aguamarina": {"background": "#DDF8EF", "text": "#153C40", "accent": "#198B78", "muted": "#39716A"},
}


def validate_special_spec(spec: dict) -> dict:
    """Crea una especificación limpia y validada, nunca ejecuta datos del proyecto."""
    if not isinstance(spec, dict):
        raise ValueError("La página especial no tiene un formato válido")
    kind = spec.get("kind", "Separador")
    theme = spec.get("theme", "Crema")
    title = spec.get("title", "")
    subtitle = spec.get("subtitle", "")
    if kind not in KINDS or theme not in THEMES:
        raise ValueError("Tipo o color de página especial no admitido")
    if not isinstance(title, str) or not isinstance(subtitle, str):
        raise ValueError("El título y subtítulo deben ser texto")
    title = title.strip()
    subtitle = subtitle.strip()
    if len(title) > 120 or len(subtitle) > 180 or re.search(r"[\x00-\x08\x0b-\x1f]", title+subtitle):
        raise ValueError("El título o subtítulo contiene caracteres no admitidos")
    if kind == "Página en blanco":
        title, subtitle = "", ""
    elif not title:
        raise ValueError("Escribe un título para esta portada o separador")
    return {"kind": kind, "theme": theme, "title": title, "subtitle": subtitle}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Fuentes de Windows, con alternativas gratuitas de Linux."""
    roots = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    filenames = (["georgiab.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else
                 ["georgia.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for root in roots:
        for filename in filenames:
            target = root / filename
            if target.is_file():
                try:
                    return ImageFont.truetype(str(target), max(9, int(size)))
                except OSError:
                    pass
    for filename in filenames:
        try:
            return ImageFont.truetype(filename, max(9, int(size)))
        except OSError:
            pass
    return ImageFont.load_default(size=max(9, int(size)))


def _text_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines = []
    for section in text.split("\n"):
        current = ""
        for word in section.split():
            proposal = f"{current} {word}" if current else word
            if current and draw.textbbox((0, 0), proposal, font=font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = proposal
        if current:
            lines.append(current)
    return lines


def _centered_lines(draw, lines, *, center_x, start_y, font, color, space):
    y = start_y
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        draw.text((center_x - (right-left)/2, y-top), line, font=font, fill=color)
        y += (bottom-top) + space
    return y


def render_special_page(spec: dict, size: tuple[int, int], safe_box: tuple[int,int,int,int] | None = None) -> Image.Image:
    """Dibuja una página completa del tamaño pedido, respetando encuadernación."""
    spec = validate_special_spec(spec)
    w, h = map(int, size)
    if w < 50 or h < 50 or w > 20000 or h > 20000:
        raise ValueError("Tamaño de portada no admitido")
    palette = THEMES[spec["theme"]]
    canvas = Image.new("RGB", (w, h), palette["background"])
    if spec["kind"] == "Página en blanco":
        return canvas
    draw = ImageDraw.Draw(canvas)
    if safe_box is None:
        safe_box = (int(w*.075), int(h*.075), int(w*.925), int(h*.925))
    x0,y0,x1,y1 = safe_box
    padding = max(8, round(min(w,h)*.052))
    x0 += padding
    x1 -= padding
    y0 += padding
    y1 -= padding
    if x1-x0 < 50 or y1-y0 < 80:
        return canvas
    cw, ch = x1-x0, y1-y0
    cx = (x0+x1)/2
    base = min(cw, ch)
    cover = spec["kind"] == "Portada"
    title_pt = int(base * (.135 if cover else .110))
    title_pt = min(title_pt, int(ch*.24))
    title = spec["title"]
    font = None
    title_lines = []
    for _ in range(24):
        font = _font(title_pt, bold=True)
        title_lines = _text_lines(draw, title, font, int(cw*.92))
        if len(title_lines) <= 4 and sum(draw.textbbox((0,0),line,font=font)[3] - draw.textbbox((0,0),line,font=font)[1]
                                          for line in title_lines) < ch*.48:
            break
        title_pt = max(13, int(title_pt*.88))
    sub_text = spec["subtitle"]
    sub_pt = max(12, int(base*.045))
    subfont = _font(sub_pt)
    sub_lines = _text_lines(draw, sub_text, subfont, int(cw*.88)) if sub_text else []
    # Ajustamos verticalmente el bloque: decoración, título, línea y subtítulo.
    title_space = max(7, int(title_pt*.30))
    title_height = sum(draw.textbbox((0,0),t,font=font)[3]-draw.textbbox((0,0),t,font=font)[1]+title_space for t in title_lines)
    sub_space = max(5, int(sub_pt*.40))
    sub_height = sum(draw.textbbox((0,0),t,font=subfont)[3]-draw.textbbox((0,0),t,font=subfont)[1]+sub_space for t in sub_lines)
    gap = max(12, int(base*.06))
    block = title_height + gap*2 + sub_height + max(7, base*.012)
    begin = max(y0, (y0+y1-block)/2)
    bar = max(4, int(base*.008))
    rule_w = int(cw*(.26 if cover else .18))
    draw.rounded_rectangle((cx-rule_w/2, begin, cx+rule_w/2, begin+bar), radius=max(1,bar//2),fill=palette["accent"])
    cursor = begin + gap
    cursor = _centered_lines(draw, title_lines, center_x=cx, start_y=cursor,
                             font=font, color=palette["text"], space=title_space)
    if sub_lines:
        cursor += gap*.35
        _centered_lines(draw, sub_lines, center_x=cx, start_y=cursor,
                        font=subfont, color=palette["muted"], space=sub_space)
    if cover:
        stroke = max(2, int(base*.003))
        edge = max(0, int(base*.045))
        draw.line((x0, y1-edge, x1, y1-edge), fill=palette["accent"], width=stroke)
    return canvas


def save_special_thumbnail(path: Path, spec: dict, *, landscape: bool = False) -> None:
    """Imagen de referencia para miniaturas; la salida real se dibuja de nuevo."""
    size = (840, 600) if landscape else (600, 840)
    img = render_special_page(spec, size)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        img.save(path, "PNG", optimize=True)
    finally:
        img.close()
