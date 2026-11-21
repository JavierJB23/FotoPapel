"""Revelo v1.7: layouts de hoja, pies de foto y numeración sin fuentes externas."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence
from PIL import Image, ImageDraw, ImageFont
from special_pages import FONT_CHOICES, _font as font_family

TEMPLATES = (
    "Cuadrícula",
    "Grande arriba + 2 abajo",
    "Grande izquierda + 2 derecha",
    "2 arriba + grande abajo",
    "Diseño libre",
)
TEMPLATE_PHOTOS = 3
NUMBER_POSITIONS = ("Exterior", "Centro", "Izquierda", "Derecha")
NUMBER_FORMATS = ("1", "-1-", "[1]", "(1)", "· 1 ·")
CAPTION_PLACEMENTS = ("Debajo", "Sobre foto", "Personalizado")
CAPTION_ALIGNMENTS = ("Izquierda", "Centro", "Derecha")


def validate_caption(spec: dict | None) -> dict:
    """Valida pies de foto nuevos y antiguos sin romper los PDF reversibles."""
    if spec is None:
        return {"title": "", "detail": "", "placement": "Debajo"}
    if not isinstance(spec, dict):
        raise ValueError("El pie de foto debe ser un objeto")
    title, detail, placement = spec.get("title", ""), spec.get("detail", ""), spec.get("placement", "Debajo")
    for value, label, limit in ((title, "Título", 120), (detail, "Descripción", 240)):
        if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in "\t\n" for c in value):
            raise ValueError(f"{label} del pie de foto incorrecto")
    if placement not in CAPTION_PLACEMENTS:
        raise ValueError("Ubicación del pie de foto desconocida")
    clean = {"title": title.strip(), "detail": detail.strip(), "placement": placement}
    # Mantén el formato anterior si no se suministraron campos adicionales:
    # antiguos proyectos/PDF conservan sus datos sin cambios.
    for key in ("title_font", "detail_font"):
        if key in spec:
            if not isinstance(spec[key], str) or spec[key] not in FONT_CHOICES:
                raise ValueError("Tipo de letra del pie de foto desconocido")
            clean[key] = spec[key]
    for key in ("title_size", "detail_size"):
        if key in spec:
            val = spec[key]
            if isinstance(val, bool) or not isinstance(val, int) or not 6 <= val <= 72:
                raise ValueError("Tamaño del pie de foto fuera de rango")
            clean[key] = val
    for key in ("title_color", "detail_color"):
        if key in spec:
            val = spec[key]
            if not isinstance(val, str) or len(val) != 7 or val[0] != "#" or any(ch not in "0123456789ABCDEFabcdef" for ch in val[1:]):
                raise ValueError("Color de pie de foto incorrecto")
            clean[key] = val.upper()
    if "align" in spec:
        if spec["align"] not in CAPTION_ALIGNMENTS:
            raise ValueError("Alineación del pie de foto desconocida")
        clean["align"] = spec["align"]
    if "photo_scale" in spec:
        val=spec["photo_scale"]
        if isinstance(val,bool) or not isinstance(val,(int,float)) or not .25 <= val <= 1.0:
            raise ValueError("Escala de fotografía fuera de rango")
        clean["photo_scale"]=round(float(val),4)
    for key in ("title_x", "title_y", "detail_x", "detail_y"):
        if key in spec:
            val = spec[key]
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not 0 <= val <= 1:
                raise ValueError("Posición de pie de foto fuera de rango")
            clean[key] = round(float(val), 5)
    return clean


def has_caption(spec: dict | None) -> bool:
    # La escala de la fotografía también es una modificación reversible,
    # aunque todavía no se haya escrito un pie de foto.
    return bool(spec and (spec.get("title") or spec.get("detail") or
                          abs(float(spec.get('photo_scale',1.0))-1.0)>0.001))


def template_rects(box: tuple[int, int, int, int], gap_x: int, gap_y: int,
                   *, template: str, count: int, landscape: bool) -> list[tuple[int, int, int, int]]:
    """Rectángulos físicos con huecos; usa proporciones para mosaicos de tres fotos."""
    if template not in TEMPLATES:
        raise ValueError("Plantilla de composición desconocida")
    if template not in ("Cuadrícula", "Diseño libre") and count != 3:
        raise ValueError("Las composiciones asimétricas necesitan tres fotografías")
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    if template == "Diseño libre":
        template = "Cuadrícula"  # Fallback; dibujo libre está en processor.
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


def _font(size: int, bold: bool = False, family: str = "Georgia"):
    return font_family(max(9, int(size)), bold=bold, family=family)


def _px_size(spec: dict, key: str, mm_to_px: float, cell_width: int) -> int:
    pt = spec.get(key, 12 if key == 'title_size' else 9)
    # Tamaño en puntos tipográficos. Reducción proporcional en celdas pequeñas,
    # para que una hoja de 3, 6 o 9 fotos no termine dominada por texto.
    return max(9, min(round(pt * mm_to_px * 25.4 / 72),
                      max(9, round(cell_width * (.075 if key == 'title_size' else .062)))))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int) -> list[str]:
    """División en líneas sin fondos ni truncado prematuro; limita al espacio."""
    lines: list[str] = []
    for paragraph in text.splitlines() or ['']:
        words = paragraph.split()
        if not words:
            lines.append('')
            continue
        current = ''
        for word in words:
            candidate = (current + ' ' + word).strip()
            if draw.textlength(candidate, font=font) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                    current = ''
                # Palabra excesivamente larga: cortar dentro de la celda.
                for char in word:
                    if current and draw.textlength(current + char, font=font) > width:
                        lines.append(current)
                        current = ''
                    current += char
        if current:
            lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + '…', font=font) > width:
            last = last[:-1]
        lines[-1] = last + '…'
    return lines


def footer_height_px(cell_height: int, px_per_mm: float, spec: dict | None) -> int:
    if not spec or not (spec.get('title') or spec.get('detail')) or spec.get("placement") != "Debajo":
        return 0
    has_two = bool(spec.get('title')) and bool(spec.get('detail'))
    title_size = _px_size(spec, 'title_size', px_per_mm, max(20, cell_height))
    detail_size = _px_size(spec, 'detail_size', px_per_mm, max(20, cell_height))
    ideal = round(px_per_mm * (15 if has_two else 9))
    # Deja al menos 68 % de la celda para la imagen.
    return max(14, min(round(cell_height*.32), max(ideal, title_size+detail_size+8)))


def _draw_text_region(draw: ImageDraw.ImageDraw, text: str, font, color: str,
                      region: tuple[int,int,int,int], *, align: str, max_lines: int,
                      family: str = 'Georgia', bold: bool = False) -> None:
    x0,y0,x1,y1 = region
    width, height = x1-x0, y1-y0
    if not text or width <= 10 or height <= 8:
        return
    for _ in range(20):
        line_height = max(10, round(font.size*1.19))
        lines = _wrap_text(draw, text, font, width, max_lines=max_lines)
        if len(lines)*line_height <= height or font.size <= 9:
            break
        font = _font(max(9,font.size-1), family=family, bold=bold)
    start_y = y0 + max(0, (height - len(lines)*line_height)//2)
    for index, line in enumerate(lines):
        length=round(draw.textlength(line,font=font))
        if align == "Derecha":
            x = x1-length
        elif align == "Centro":
            x = x0 + (width-length)//2
        else:
            x=x0
        draw.text((x,start_y+index*line_height),line,fill=color,font=font)


def draw_caption(sheet: Image.Image, rect: tuple[int,int,int,int], spec: dict | None,
                 *, mode: str, px_per_mm: float,
                 below_start_y: int | None = None) -> None:
    """Texto sin paneles opacos, dentro de su celda y sin invadir otras fotos."""
    if not spec or not (spec.get('title') or spec.get('detail')):
        return
    x0,y0,x1,y1 = rect
    w,h = x1-x0,y1-y0
    if min(w,h) < 18:
        return
    spec = validate_caption(spec)
    # Dibujo sobre una copia de la celda: evita que textos muy largos salgan
    # de ella y tapen otras fotografías en composiciones asimétricas.
    tile = sheet.crop(rect)
    try:
        draw=ImageDraw.Draw(tile)
        pad=max(4, round(px_per_mm*1.2))
        max_width=w-2*pad
        align=spec.get('align','Centro' if mode == 'Personalizado' else 'Izquierda')
        title=spec.get('title','')
        detail=spec.get('detail','')
        sizes={}
        fonts={}
        for key in ('title','detail'):
            sizes[key]=_px_size(spec,key+'_size',px_per_mm,w)
            fonts[key]=_font(sizes[key],bold=(key=='title'),family=spec.get(key+'_font','Georgia'))
        if mode=='Personalizado':
            for key,txt in (('title',title),('detail',detail)):
                if not txt:
                    continue
                px=round(w*spec.get(key+'_x',.5))
                py=round(h*spec.get(key+'_y',.85 if key=='title' else .93))
                height=min(h-2*pad,max(sizes[key]*4,round(h*.22)))
                rw=min(max_width,max(40,round(w*.86)))
                # Centro del bloque visual = coordenadas arrastradas.
                left=max(pad,min(w-pad-rw,px-rw//2))
                top=max(pad,min(h-pad-height,py-height//2))
                _draw_text_region(draw,txt,fonts[key],spec.get(key+'_color','#FFFFFF'),
                                  (left,top,left+rw,top+height),align=align,max_lines=3,
                                  family=spec.get(key+'_font','Georgia'),bold=(key=='title'))
        else:
            # El espacio de texto inferior se reserva únicamente en «Debajo».
            # Cuando está superpuesto, se usa la parte baja de la foto misma.
            block_h=footer_height_px(h,px_per_mm,spec) if mode=='Debajo' else min(round(h*.30), max(24,round(px_per_mm*15)))
            start=max(pad,h-block_h)
            if mode == 'Debajo' and below_start_y is not None:
                start=max(pad,min(h-pad-12,below_start_y-y0))
                block_h=max(12,min(h-start,footer_height_px(h,px_per_mm,spec)))
            if title and detail:
                end=min(h-pad,start+block_h)
                split=max(start+9,min(end-8,start+round(block_h*.52)))
                regions=((title,(pad,start,w-pad,split)),(detail,(pad,split,w-pad,end)))
            elif title:
                regions=((title,(pad,start,w-pad,min(h-pad,start+block_h))),)
            else:
                regions=((detail,(pad,start,w-pad,min(h-pad,start+block_h))),)
            for key,(text, region) in zip(('title','detail') if title and detail else (('title',) if title else ('detail',)),regions):
                _draw_text_region(draw,text,fonts[key],spec.get(key+'_color','#FFFFFF' if mode=='Sobre foto' else '#253447'),
                                  region,align=align,max_lines=2,
                                  family=spec.get(key+'_font','Georgia'),bold=(key=='title'))
        sheet.paste(tile,(x0,y0))
    finally:
        tile.close()


def draw_page_number(sheet: Image.Image, number: int | None, *,
                     placement: str, physical_mm: tuple[float,float], page_index: int,
                     number_format: str = "1") -> None:
    if number is None:
        return
    if placement not in NUMBER_POSITIONS:
        raise ValueError("Posición de numeración no reconocida")
    if number_format not in NUMBER_FORMATS:
        raise ValueError("Formato de numeración no reconocido")
    w_mm,h_mm = physical_mm
    w,h = sheet.size
    scale = w/w_mm
    font=_font(max(11, round(scale*3.0)), bold=True)
    drawing=ImageDraw.Draw(sheet)
    label={"1":str(number),"-1-":f"-{number}-","[1]":f"[{number}]",
           "(1)":f"({number})","· 1 ·":f"· {number} ·"}[number_format]
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
    # Numeración impresa directamente sobre el papel, sin pastilla de fondo.
    bbox=drawing.textbbox((0,0),label,font=font)
    tw=bbox[2]-bbox[0]
    text_x=max(3,min(w-tw-3,round(center_x-tw/2)))
    baseline_y=h-max(round(scale*5.2),13)
    text_y=max(2,min(h-(bbox[3]-bbox[1])-2,round(baseline_y-(bbox[3]-bbox[1])/2-bbox[1])))
    # Sin cajita: contraste automático para que se lea también sobre fotos oscuras.
    crop=sheet.crop((max(0,text_x),max(0,text_y),min(w,text_x+tw),
                     min(h,text_y+max(9,bbox[3]-bbox[1]))))
    from PIL import ImageStat
    lightness=ImageStat.Stat(crop.convert('L')).mean[0]
    crop.close()
    drawing.text((text_x,text_y),label,
                 fill=(249,249,246) if lightness<118 else (23,49,64),font=font)
