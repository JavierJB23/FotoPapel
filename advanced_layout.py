"""Revelo v1.7: layouts de hoja, pies de foto y numeración sin fuentes externas."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence
from PIL import Image, ImageDraw, ImageFont

TEMPLATES = (
    "Cuadrícula",
    "Grande arriba + 2 abajo",
    "Grande izquierda + 2 derecha",
    "2 arriba + grande abajo",
)
TEMPLATE_PHOTOS = 3
NUMBER_POSITIONS = ("Exterior", "Centro", "Izquierda", "Derecha")
CAPTION_PLACEMENTS = ("Debajo", "Sobre foto")


def validate_caption(spec: dict | None) -> dict:
    """Valida metadatos que pueden proceder de PDF o .revelo no confiables."""
    if spec is None:
        return {"title": "", "detail": "", "placement": "Debajo"}
    if not isinstance(spec, dict):
        raise ValueError("El pie de foto debe ser un objeto")
    title, detail, placement = spec.get("title", ""), spec.get("detail", ""), spec.get("placement", "Debajo")
    if not isinstance(title, str) or len(title) > 120 or any(ord(c) < 32 and c not in "\t\n" for c in title):
        raise ValueError("Título del pie de foto incorrecto")
    if not isinstance(detail, str) or len(detail) > 240 or any(ord(c) < 32 and c not in "\t\n" for c in detail):
        raise ValueError("Descripción del pie de foto incorrecta")
    if placement not in CAPTION_PLACEMENTS:
        raise ValueError("Ubicación del pie de foto desconocida")
    return {"title": title.strip(), "detail": detail.strip(), "placement": placement}


def has_caption(spec: dict | None) -> bool:
    return bool(spec and (spec.get("title") or spec.get("detail")))


def template_rects(box: tuple[int, int, int, int], gap_x: int, gap_y: int,
                   *, template: str, count: int, landscape: bool) -> list[tuple[int, int, int, int]]:
    """Rectángulos físicos con huecos; usa proporciones para mosaicos de tres fotos."""
    if template not in TEMPLATES:
        raise ValueError("Plantilla de composición desconocida")
    if template != "Cuadrícula" and count != 3:
        raise ValueError("Las composiciones asimétricas necesitan tres fotografías")
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    if template == "Grande arriba + 2 abajo":
        midx = x0 + (width - gap_x) // 2
        midy = y0 + round((height - gap_y) * 0.60)
        return [(x0,y0,x1,midy), (x0,midy+gap_y,midx,y1), (midx+gap_x,midy+gap_y,x1,y1)]
    if template == "Grande izquierda + 2 derecha":
        midx = x0 + round((width - gap_x) * 0.60)
        midy = y0 + (height - gap_y) // 2
        return [(x0,y0,midx,y1), (midx+gap_x,y0,x1,midy), (midx+gap_x,midy+gap_y,x1,y1)]
    if template == "2 arriba + grande abajo":
        midx = x0 + (width - gap_x)//2
        midy = y0 + round((height - gap_y)*0.40)
        return [(x0,y0,midx,midy), (midx+gap_x,y0,x1,midy), (x0,midy+gap_y,x1,y1)]
    # Conserva las formas existentes para 1,2,4,6,9. Tres fotos: fila o columna.
    if count == 2:
        cols, rows = ((2, 1) if landscape else (1, 2))
    elif count == 3:
        cols, rows = ((3, 1) if landscape else (1, 3))
    elif count == 6:
        cols, rows = ((3, 2) if landscape else (2, 3))
    else:
        side = {1:1, 4:2, 9:3}.get(count)
        if side is None:
            raise ValueError("Cantidad por hoja no permitida")
        cols = rows = side
    usable_w, usable_h = width - (cols-1)*gap_x, height - (rows-1)*gap_y
    if usable_w < cols*6 or usable_h < rows*6:
        raise ValueError("El papel es demasiado pequeño para esta composición")
    return [(x0 + (col * usable_w // cols) + col*gap_x,
             y0 + (row*usable_h//rows)+row*gap_y,
             x0 + ((col+1)*usable_w//cols)+col*gap_x,
             y0 + ((row+1)*usable_h//rows)+row*gap_y)
            for row in range(rows) for col in range(cols)]


def numbers_for_groups(groups: Sequence[Sequence[Path]], specials: dict[Path, dict], *,
                       enabled: bool, start: int = 1, skip_special: bool = True) -> list[int | None]:
    if not enabled:
        return [None]*len(groups)
    current = start
    results = []
    for group in groups:
        if skip_special and any(path in specials for path in group):
            results.append(None)
        else:
            results.append(current)
            current += 1
    return results


def book_spreads(count: int) -> list[tuple[int | None, int | None]]:
    """Primera hoja a la derecha; siguientes hojas izquierda/derecha."""
    if count < 0:
        raise ValueError("Número de hojas incorrecto")
    if not count:
        return []
    results: list[tuple[int | None, int | None]] = [(None, 0)]
    for i in range(1, count, 2):
        results.append((i, i+1 if i+1 < count else None))
    return results


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, max(9, size))
    except OSError:
        return ImageFont.load_default()


def footer_height_px(cell_height: int, px_per_mm: float, spec: dict | None) -> int:
    if not has_caption(spec) or spec.get("placement") == "Sobre foto":
        return 0
    # Hasta dos líneas con tamaño legible sin tragarse la composición.
    return max(12, min(round(px_per_mm*13), round(cell_height*0.23)))


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    s = " ".join(text.split())
    if draw.textlength(s, font=font) <= max_width:
        return s
    while s and draw.textlength(s+"…", font=font) > max_width:
        s = s[:-1]
    return s + "…" if s else ""


def draw_caption(sheet: Image.Image, rect: tuple[int,int,int,int], spec: dict | None,
                 *, mode: str, px_per_mm: float) -> None:
    if not has_caption(spec):
        return
    x0,y0,x1,y1 = rect
    w, h = x1-x0, y1-y0
    if min(w,h) < 18:
        return
    title = spec.get("title", "")
    detail = spec.get("detail", "")
    text_size = max(10, min(42, round(px_per_mm*2.65), round(w*.055)))
    title_font = _font(text_size, bold=True)
    detail_font = _font(max(9, round(text_size*.78)))
    caption_h = footer_height_px(h, px_per_mm, spec)
    if mode == "Sobre foto":
        # Bloque legible y discreto encima de una fotografía.
        caption_h = max(24, min(h//3, max(round(px_per_mm*13), text_size*3)))
    start_y = y1-caption_h
    drawing = ImageDraw.Draw(sheet, "RGBA")
    if mode == "Sobre foto":
        drawing.rectangle((x0,start_y,x1,y1), fill=(9,23,34,210))
        foreground = (255,255,255,255)
        foreground2 = (215,230,235,255)
    else:
        drawing.rectangle((x0,start_y,x1,y1), fill=(247,240,227,255))
        foreground = (30,48,61,255)
        foreground2 = (70,85,93,255)
    pad = max(5, round(px_per_mm*1.3))
    line_height = max(12, round(text_size*1.18))
    if title:
        drawing.text((x0+pad, start_y+pad), _ellipsize(drawing,title,title_font,w-2*pad),
                     fill=foreground,font=title_font)
    if detail:
        dy = start_y + pad + (line_height if title else 0)
        if dy + detail_font.size + 1 <= y1:
            drawing.text((x0+pad,dy),_ellipsize(drawing,detail,detail_font,w-2*pad),
                         fill=foreground2,font=detail_font)


def draw_page_number(sheet: Image.Image, number: int | None, *,
                     placement: str, physical_mm: tuple[float,float], page_index: int) -> None:
    if number is None:
        return
    if placement not in NUMBER_POSITIONS:
        raise ValueError("Posición de numeración no reconocida")
    w_mm,h_mm = physical_mm
    w,h = sheet.size
    scale = w/w_mm
    font=_font(max(11, round(scale*3.0)), bold=True)
    drawing=ImageDraw.Draw(sheet)
    label=str(number)
    tw=round(drawing.textlength(label,font=font))
    px_margin=max(5,round(scale*6))
    if placement == "Centro":
        center_x=w//2
    elif placement == "Exterior":
        center_x=(w-px_margin-tw//2) if page_index%2==0 else (px_margin+tw//2)
    elif placement == "Derecha":
        center_x=w-px_margin-tw//2
    else:
        center_x=px_margin+tw//2
    middle_y=h-max(round(scale*5.2),13)
    textbox=drawing.textbbox((0,0), label, font=font)
    box_w=max(25,tw+round(scale*4))
    box_h=max(22,textbox[3]-textbox[1]+round(scale*2.5))
    x0=max(1,min(w-box_w-1,center_x-box_w//2))
    y0=max(1,min(h-box_h-1,middle_y-box_h//2))
    drawing.rounded_rectangle((x0,y0,x0+box_w,y0+box_h),radius=max(3,round(scale)),
                              fill=(246,239,223),outline=(175,183,179),width=max(1,round(scale*.2)))
    drawing.text((x0+(box_w-tw)//2, y0+(box_h-(textbox[3]-textbox[1]))//2-textbox[1]),
                 label, fill=(23,49,64),font=font)
