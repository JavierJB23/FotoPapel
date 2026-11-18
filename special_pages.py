"""Portadas, separadores y páginas en blanco para Revelo.

El estilo es información estructurada: se guarda en los proyectos y se vuelve a
renderizar al tamaño de papel elegido. El PNG temporal solo sirve de miniatura.
"""
from __future__ import annotations

from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps

KINDS = ("Portada", "Separador", "Página en blanco")
THEMES = {
    "Azul noche": {"background": "#0B1928", "text": "#F5F0E6", "accent": "#4CD9B5", "muted": "#B7C9D1"},
    "Crema": {"background": "#F6EBDC", "text": "#443427", "accent": "#AD7548", "muted": "#76665C"},
    "Blanco": {"background": "#FFFFFF", "text": "#20364D", "accent": "#1F9C89", "muted": "#687987"},
    "Aguamarina": {"background": "#DDF8EF", "text": "#153C40", "accent": "#198B78", "muted": "#39716A"},
}


CUSTOM_THEME = "Personalizar"


def _hex(value: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(f"El color de {name} debe ser un valor hexadecimal")
    return value.upper()


def validate_special_spec(spec: dict) -> dict:
    """Valida páginas antiguas y diseños personalizados sin ejecutar datos externos."""
    if not isinstance(spec, dict):
        raise ValueError("La página especial no tiene un formato válido")
    kind = spec.get("kind", "Separador")
    theme = spec.get("theme", "Crema")
    title = spec.get("title", "")
    subtitle = spec.get("subtitle", "")
    if kind not in KINDS or theme not in (*THEMES, CUSTOM_THEME):
        raise ValueError("Tipo o color de página especial no admitido")
    if not isinstance(title, str) or not isinstance(subtitle, str):
        raise ValueError("El título y subtítulo deben ser texto")
    title, subtitle = title.strip(), subtitle.strip()
    if len(title) > 120 or len(subtitle) > 180 or re.search(r"[\x00-\x08\x0b-\x1f]", title + subtitle):
        raise ValueError("El título o subtítulo contiene caracteres no admitidos")
    if theme != CUSTOM_THEME:
        if kind == "Página en blanco":
            title, subtitle = "", ""
        elif not title:
            raise ValueError("Escribe un título para esta portada o separador")
        return {"kind": kind, "theme": theme, "title": title, "subtitle": subtitle}
    bgtype = spec.get("background_type", "color")
    if bgtype not in ("color", "imagen"):
        raise ValueError("Tipo de fondo personalizado desconocido")
    bg_image = spec.get("background_image", "")
    if not isinstance(bg_image, str) or len(bg_image) > 2048:
        raise ValueError("Ruta de imagen de fondo inválida")
    if bgtype == "imagen" and (not bg_image or Path(bg_image).suffix.lower() not in
                               (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif")):
        raise ValueError("Elige una foto de fondo válida")
    out = {"kind": kind, "theme": theme, "title": title, "subtitle": subtitle,
           "background_type": bgtype, "background_image": bg_image,
           "background_color": _hex(spec.get("background_color", "#F6EBDC"), "fondo"),
           "text_color": _hex(spec.get("text_color", "#1B2D43"), "título"),
           "subtitle_color": _hex(spec.get("subtitle_color", "#334C63"), "subtítulo")}
    for key, default, lower, upper in (
        ("title_size", 12, 3, 24), ("subtitle_size", 6, 2, 18),
    ):
        value = spec.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
            raise ValueError(f"Valor de {key} inválido")
        out[key] = int(value)
    for key, default in (
        ("title_x", .5), ("title_y", .42),
        ("subtitle_x", .5), ("subtitle_y", .58),
    ):
        value = spec.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"Posición de {key} inválida")
        out[key] = round(float(value), 5)
    # Transformación de la foto de fondo. Los proyectos antiguos no incluyen
    # estos campos: el valor por defecto «Cubrir» reproduce su resultado.
    mode = spec.get('image_mode', 'Cubrir')
    if mode not in ('Encajar', 'Cubrir', 'Libre'):
        raise ValueError('Modo de ajuste de la foto no reconocido')
    out['image_mode'] = mode
    for key, default in (('image_zoom_x', 1.0), ('image_zoom_y', 1.0)):
        val = spec.get(key, default)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not .25 <= val <= 3.0:
            raise ValueError('Escala de fotografía fuera de rango')
        out[key] = round(float(val), 4)
    for key, default in (('image_x', .5), ('image_y', .5)):
        val = spec.get(key, default)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not 0 <= val <= 1:
            raise ValueError('Posición de fotografía fuera de rango')
        out[key] = round(float(val), 5)
    for key, default in (("show_title", True), ("show_subtitle", True)):
        value = spec.get(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"Campo {key} inválido")
        out[key] = value
    if kind == "Página en blanco":
        out.update(title="", subtitle="", show_title=False, show_subtitle=False)
    if not out["show_title"]:
        out["title"] = ""
    if not out["show_subtitle"]:
        out["subtitle"] = ""
    return out


def _draw_custom_background(canvas: Image.Image, source: Image.Image, spec: dict) -> None:
    """Pega foto sobre el color de base, recortando *antes* de escalar a 600 PPP.

    Admite encajar, cubrir y transformación libre con zoom X/Y independientes
    y centro movible. Nunca crea un bitmap intermedio mayor que la hoja final.
    """
    w, h = canvas.size
    sw, sh = source.size
    if not (w > 0 and h > 0 and sw > 0 and sh > 0):
        return
    mode = spec.get('image_mode','Cubrir')
    base = max(w/sw,h/sh) if mode == 'Cubrir' else min(w/sw,h/sh)
    stretch_x = float(spec.get('image_zoom_x',1.0)) if mode == 'Libre' else 1.0
    stretch_y = float(spec.get('image_zoom_y',1.0)) if mode == 'Libre' else 1.0
    rendered_w = sw*base*stretch_x
    rendered_h = sh*base*stretch_y
    center_x = w*float(spec.get('image_x',.5)) if mode == 'Libre' else w/2
    center_y = h*float(spec.get('image_y',.5)) if mode == 'Libre' else h/2
    x0,y0 = center_x-rendered_w/2,center_y-rendered_h/2
    left,top = max(0,int(round(x0))),max(0,int(round(y0)))
    right,bottom = min(w,int(round(x0+rendered_w))),min(h,int(round(y0+rendered_h)))
    if left >= right or top >= bottom:
        return
    crop = (max(0,int((left-x0)/rendered_w*sw)),
            max(0,int((top-y0)/rendered_h*sh)),
            min(sw,max(1,int((right-x0)/rendered_w*sw)+1)),
            min(sh,max(1,int((bottom-y0)/rendered_h*sh)+1)))
    # Resize sólo del trozo visible: evita memorias enormes con zoom 300 %.
    region = source.crop(crop)
    try:
        visible = region.resize((right-left,bottom-top),Image.Resampling.LANCZOS)
        canvas.paste(visible,(left,top))
        visible.close()
    finally:
        region.close()


def render_custom_page(spec: dict, size: tuple[int, int],
                       safe_box: tuple[int,int,int,int] | None = None) -> Image.Image:
    """Fondo a color/foto y títulos ajustables, dibujados en posiciones relativas."""
    w, h = map(int, size)
    canvas = Image.new("RGB", (w, h), spec["background_color"])
    if spec["background_type"] == "imagen":
        with Image.open(Path(spec['background_image'])) as opened:
            image = ImageOps.exif_transpose(opened).convert('RGB')
        try:
            _draw_custom_background(canvas, image, spec)
        finally:
            image.close()
    if spec["kind"] == "Página en blanco":
        return canvas
    if safe_box is None:
        safe_box = (int(w*.075), int(h*.075), int(w*.925), int(h*.925))
    x0, y0, x1, y1 = safe_box
    # Posiciones relativas al rectángulo seguro, dejando margen de seguridad.
    margin = max(4, round(min(w, h)*.015))
    x0, y0, x1, y1 = x0 + margin, y0 + margin, x1 - margin, y1 - margin
    cw, ch = max(1, x1 - x0), max(1, y1 - y0)
    draw = ImageDraw.Draw(canvas)
    for element in ("title", "subtitle"):
        if not spec.get("show_"+element) or not spec.get(element):
            continue
        size_px = max(9, int(min(cw, ch) * spec[element+"_size"] / 100))
        font = _font(size_px, bold=element == "title")
        lines = _text_lines(draw, spec[element], font, int(cw*.96))
        if not lines:
            continue
        gap = max(2, int(size_px*.28))
        heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
        total = sum(heights) + gap * (len(lines)-1)
        # Alineación central y protección de textos cerca de los márgenes.
        cy = y0 + spec[element+"_y"]*ch
        cursor = min(max(cy - total/2, y0), max(y0, y1-total))
        cx = x0 + spec[element+"_x"]*cw
        for line, height in zip(lines, heights):
            box = draw.textbbox((0, 0), line, font=font)
            width = box[2] - box[0]
            px = min(max(cx - width / 2, x0), x1 - width)
            draw.text((px - box[0], cursor - box[1]), line,
                      fill=spec["text_color"] if element == "title" else spec["subtitle_color"], font=font)
            cursor += height + gap
    return canvas


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
    if spec["theme"] == CUSTOM_THEME:
        return render_custom_page(spec, size, safe_box=safe_box)
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
