"""Núcleo de impresión y exportación de Revelo.

Dependencias: Pillow, reportlab y python-docx. No utiliza servicios web.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence
import math
import re

from PIL import Image, ImageOps, ImageFilter, ImageStat, ImageDraw, UnidentifiedImageError
from advanced_layout import (TEMPLATES, NUMBER_POSITIONS, NUMBER_FORMATS, validate_caption, has_caption,
                             template_rects, numbers_for_groups, draw_caption, footer_height_px, draw_page_number)

# Compatibilidad con las fotografías HEIC/HEIF originales del iPhone.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # La distribución Windows incluye la dependencia; tests sin HEIC siguen funcionando.


# Anchura x altura en milímetros (orientación vertical).
PAPER_SIZES: dict[str, tuple[float, float]] = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "9 × 13 cm": (90, 130),
    "10 × 15 cm": (100, 150),
    "11 × 15 cm": (110, 150),
    "13 × 18 cm": (130, 180),
    "15 × 20 cm": (150, 200),
    "15 × 21 cm": (150, 210),
    "20 × 25 cm": (200, 250),
    "20 × 30 cm": (200, 300),
    "30 × 40 cm": (300, 400),
    "30 × 45 cm": (300, 450),
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
Progress = Callable[[int, int, str], None]
FIT_MODES = (
    "Ajustar (sin recortar)",
    "Rellenar (recortar)",
    "Ajuste inteligente (máx. 5 %)",
    "Ampliar fondo (sin recortar)",
)



@dataclass(frozen=True)
class ExportOptions:
    paper: str = "A4"
    orientation: str = "Automática"  # Automática / Vertical / Horizontal
    fit: str = "Ajustar (sin recortar)"  # Mantener proporción, recortar, suave, fondo extendido
    dpi: int = 300
    fmt: str = "PDF"  # Imagenes / PDF / Word
    binding: bool = False  # Reserva canal interior para encuadernación
    # Una página de PDF importada ya está maquetada. No añadirle un segundo encaje.
    pdf_page_paths: frozenset[Path] = frozenset()
    photos_per_page: int = 1  # 1, 2, 4, 6 o 9; 1 conserva el funcionamiento de v1.3
    special_pages: dict[Path, dict] = field(default_factory=dict)  # portadas, títulos, hojas en blanco
    photo_edits: dict[Path, dict] = field(default_factory=dict)  # cambios no destructivos
    layout_template: str = "Cuadrícula"
    captions: dict[Path, dict] = field(default_factory=dict)
    numbering_enabled: bool = False
    numbering_position: str = "Exterior"
    numbering_skip_special: bool = True
    numbering_start: int = 1
    numbering_format: str = "1"
    # Geometrías opcionales de fotografías, por imagen; se conservan en .revelo.
    layout_items: dict[Path, dict] = field(default_factory=dict)

    def validate(self) -> None:
        if self.paper not in PAPER_SIZES:
            raise ValueError("Tamaño de papel no reconocido")
        if self.orientation not in ("Automática", "Vertical", "Horizontal"):
            raise ValueError("Orientación no reconocida")
        if self.fit not in FIT_MODES:
            raise ValueError("Modo de encaje no reconocido")
        if not (72 <= self.dpi <= 600):
            raise ValueError("Los PPP deben estar entre 72 y 600")
        if not isinstance(self.binding, bool):
            raise ValueError("Márgenes de encuadernación no reconocidos")
        if self.photos_per_page not in (1, 2, 3, 4, 6, 9):
            raise ValueError("Número de fotos por hoja no reconocido")
        if self.layout_template not in TEMPLATES:
            raise ValueError("Diseño de página no reconocido")
        if self.layout_template not in ("Cuadrícula", "Diseño libre") and self.photos_per_page != 3:
            raise ValueError("Las plantillas asimétricas requieren 3 fotos por hoja")
        if not isinstance(self.numbering_enabled, bool) or not isinstance(self.numbering_skip_special, bool):
            raise ValueError("Numeración incorrecta")
        if (self.numbering_position not in NUMBER_POSITIONS or self.numbering_format not in NUMBER_FORMATS
                or not (1 <= self.numbering_start <= 999999)):
            raise ValueError("Opciones de numeración incorrectas")
        from layout_editor import validate_layout_item
        for spec in self.layout_items.values():
            validate_layout_item(spec)
        for cap in self.captions.values():
            validate_caption(cap)
        from special_pages import validate_special_spec
        for spec in self.special_pages.values():
            validate_special_spec(spec)
        from photo_edits import validate_edits
        for spec in self.photo_edits.values():
            validate_edits(spec)
        if self.fmt not in ("Imagenes", "PDF", "Word"):
            raise ValueError("Formato de salida no reconocido")


def dimensions_mm(path: Path, opts: ExportOptions) -> tuple[float, float]:
    """Orientación automática basada en los píxeles visibles tras EXIF."""
    w, h = PAPER_SIZES[opts.paper]
    if opts.orientation == "Horizontal":
        return h, w
    if opts.orientation == "Vertical":
        return w, h
    with Image.open(path) as source:
        # EXIF 5,6,7,8 implican rotación de ejes.
        exif_orientation = source.getexif().get(274)
        sw, sh = source.size
        if exif_orientation in (5, 6, 7, 8):
            sw, sh = sh, sw
    if path in opts.photo_edits:
        from photo_edits import transformed_dimensions
        sw, sh = transformed_dimensions((sw, sh), opts.photo_edits[path])
    return (h, w) if sw > sh else (w, h)


def pixel_size(w_mm: float, h_mm: float, dpi: int) -> tuple[int, int]:
    return (max(1, round(w_mm / 25.4 * dpi)), max(1, round(h_mm / 25.4 * dpi)))


def source_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        w, h = im.size
        if im.getexif().get(274) in (5, 6, 7, 8):
            return h, w
        return w, h


def _flatten_rgb(im: Image.Image) -> Image.Image:
    if im.mode == "RGB":
        return im.copy()
    # Los JPG y PDF no admiten canal alfa; fondo de papel blanco.
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        rgba = im.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        return white.convert("RGB")
    return im.convert("RGB")


def _soft_edge_background(inside: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Extiende los colores de los bordes en las bandas sobrantes.

    El original se superpone encima y nunca se modifica. Mantiene los colores
    de las franjas parecidos a los de la fotografía, sin bordes blancos.
    """
    out_w, out_h = size
    in_w, in_h = inside.size
    x = (out_w - in_w) // 2
    y = (out_h - in_h) // 2
    t = max(1, min(in_w, in_h) // 150)

    def average_color(box: tuple[int, int, int, int]) -> tuple[int, int, int]:
        return tuple(round(v) for v in ImageStat.Stat(inside.crop(box)).mean[:3])

    top = average_color((0, 0, in_w, t))
    bottom = average_color((0, in_h - t, in_w, in_h))
    left = average_color((0, 0, t, in_h))
    right = average_color((in_w - t, 0, in_w, in_h))
    result = Image.new("RGB", size, top)
    drawing = ImageDraw.Draw(result)
    if y > 0:
        drawing.rectangle((0, y + in_h, out_w, out_h), fill=bottom)
    if x > 0:
        drawing.rectangle((0, 0, x, out_h), fill=left)
        drawing.rectangle((x + in_w, 0, out_w, out_h), fill=right)
    return result


def _trim_revelo_like_page_background(source: Image.Image) -> tuple[Image.Image, bool]:
    """Aísla una foto de bandas blancas opuestas en un PDF importado.

    Un PDF previo con «Ajustar sin recortar» suele tener bandas *solo*
    arriba/abajo o izquierda/derecha, pues la foto toca los otros dos bordes.
    Por ello, cada eje se analiza independientemente. Solo se elimina una
    pareja de bandas si ambas son grandes y el borde interior está ocupado
    mayoritariamente por contenido, para no recortar documentos de texto.
    La detección es conservadora: cuando hay dudas, mantiene la página.
    """
    if source.width < 80 or source.height < 80:
        return source.copy(), False

    ratio = min(1.0, 520 / max(source.width, source.height))
    thumb_size = (max(1, round(source.width * ratio)),
                  max(1, round(source.height * ratio)))
    with source.convert("RGB") as converted:
        thumb = (converted.resize(thumb_size, Image.Resampling.BILINEAR)
                 if thumb_size != converted.size else converted.copy())
    try:
        w, h = thumb.size
        # El blanco del papel tras rasterizar un PDF puede ser algo gris por
        # interpolación, así que toleramos pequeñas diferencias del blanco.
        luminance = thumb.convert("L")
        white_mask = [value >= 243 for value in luminance.tobytes()]

        def row_white(y: int) -> float:
            # Ignoramos solo un borde mínimo: la foto puede llegar a los lados.
            start = max(1, round(w * .008))
            end = w - start
            return sum(white_mask[y * w + start:y * w + end]) / (end - start)

        def column_white(x: int) -> float:
            margin = max(1, round(h * .008))
            return sum(white_mask[y * w + x] for y in range(margin, h - margin)) / (h - 2 * margin)

        def leading_blank(length: int, sample, *, reverse: bool = False) -> int:
            bound = int(length * .36)  # no quitar media página accidentalmente
            for n in range(bound):
                pos = length - 1 - n if reverse else n
                if sample(pos) < .975:
                    return n
            return bound

        top = leading_blank(h, row_white)
        bottom = leading_blank(h, row_white, reverse=True)
        left = leading_blank(w, column_white)
        right = leading_blank(w, column_white, reverse=True)
        # Una pareja debe tener suficiente grosor en ambos lados.
        min_v = max(5, round(h * .025))
        min_h = max(5, round(w * .025))
        vertical = min(top, bottom) >= min_v and top + bottom < h * .60
        horizontal = min(left, right) >= min_h and left + right < w * .60

        # Aseguramos que el borde interior es realmente una fotografía o
        # ilustración ocupando el ancho/alto, no una línea de texto flotante.
        def occupancy_rows(first: int, last: int) -> float:
            ys = [min(h - 1, first + 2), min(h - 1, first + 4),
                  max(0, last - 3), max(0, last - 5)]
            return min(1 - row_white(y) for y in ys)

        def occupancy_columns(first: int, last: int) -> float:
            xs = [min(w - 1, first + 2), min(w - 1, first + 4),
                  max(0, last - 3), max(0, last - 5)]
            return min(1 - column_white(x) for x in xs)

        if vertical and occupancy_rows(top, h - bottom) < .55:
            vertical = False
        if horizontal and occupancy_columns(left, w - right) < .55:
            horizontal = False
        if not (vertical or horizontal):
            # PDFs antiguos con fondo ampliado tienen franjas difuminadas en
            # lugar de blancas: intentamos aislar solo el núcleo nítido.
            from pdf_cleanup import detect_blurred_background
            return detect_blurred_background(source)
        x0 = left if horizontal else 0
        x1 = w - right if horizontal else w
        y0 = top if vertical else 0
        y1 = h - bottom if vertical else h

        # Escalamos la caja de recorte del análisis a la resolución original;
        # nunca alteramos el PNG temporal ni el PDF original del usuario.
        crop = (max(0, math.floor(x0 * source.width / w)),
                max(0, math.floor(y0 * source.height / h)),
                min(source.width, math.ceil(x1 * source.width / w)),
                min(source.height, math.ceil(y1 * source.height / h)))
        if crop[2] - crop[0] < source.width * .4 or crop[3] - crop[1] < source.height * .4:
            return source.copy(), False
        return source.crop(crop), True
    finally:
        thumb.close()

def _extended_background(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Fondo local difuminado para encajar sin recortes ni deformación.

    La base es una ampliación desenfocada de la propia foto; el centro se
    recubre con su versión íntegra y proporcionada. No es IA generativa.
    Se prepara una base reducida para no gastar cientos de MB a 600 PPP.
    """
    out_w, out_h = size
    ratio = min(1.0, 1350 / max(out_w, out_h))
    work = (max(1, round(out_w * ratio)), max(1, round(out_h * ratio)))
    backdrop = ImageOps.fit(source, work, method=Image.Resampling.LANCZOS)
    radius = max(8, round(max(work) * 0.025))
    blurred = backdrop.filter(ImageFilter.GaussianBlur(radius))
    backdrop.close()
    if work != size:
        result = blurred.resize(size, Image.Resampling.BICUBIC)
        blurred.close()
        return result
    return blurred


# Márgenes de seguridad en papel cuando hay encuadernación a doble cara.
INNER_MARGIN_MM = 12.0
OUTER_MARGIN_MM = 3.0


def printable_box(size: tuple[int, int], physical_mm: tuple[float, float], *,
                  binding: bool = False, page_index: int = 0) -> tuple[int, int, int, int]:
    """Área imprimible (x0, y0, x1, y1). Páginas impares: canal a la izquierda.

    Coordenadas proporcionales al papel: idéntica geometría en previsualización
    y salida final, con independencia de la resolución escogida.
    """
    w, h = size
    if not binding:
        return 0, 0, w, h
    w_mm, h_mm = physical_mm
    left_mm, right_mm = ((INNER_MARGIN_MM, OUTER_MARGIN_MM)
                         if page_index % 2 == 0 else (OUTER_MARGIN_MM, INNER_MARGIN_MM))
    x0 = round(left_mm / w_mm * w)
    x1 = w - round(right_mm / w_mm * w)
    y0 = round(OUTER_MARGIN_MM / h_mm * h)
    y1 = h - round(OUTER_MARGIN_MM / h_mm * h)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("El papel es demasiado pequeño para los márgenes de encuadernación")
    return x0, y0, x1, y1


def _prepared_photo(path: Path, opts: ExportOptions) -> tuple[Image.Image, bool]:
    """Contenido original limpio + edición reversible, sin escribir el origen."""
    from photo_edits import apply_edits
    with Image.open(path) as raw:
        original = _flatten_rgb(ImageOps.exif_transpose(raw))
    try:
        if path in opts.pdf_page_paths:
            prepared, trimmed = _trim_revelo_like_page_background(original)
        else:
            prepared, trimmed = original.copy(), False
    finally:
        original.close()
    if path in opts.photo_edits:
        try:
            edited = apply_edits(prepared, opts.photo_edits[path])
        finally:
            prepared.close()
        return edited, trimmed
    return prepared, trimmed


def _render_inside(im: Image.Image, size: tuple[int, int], fit: str) -> Image.Image:
    """Compone la foto en un rectángulo disponible, sin conocer el papel."""
    out_w, out_h = size
    if fit == "Rellenar (recortar)":
        return ImageOps.fit(im, (out_w, out_h), method=Image.Resampling.LANCZOS,
                            centering=(0.5, 0.5))
    inside = ImageOps.contain(im, (out_w, out_h), method=Image.Resampling.LANCZOS)
    if fit == "Ajuste inteligente (máx. 5 %)":
        new_w = min(out_w, max(1, round(inside.width * 1.05)))
        new_h = min(out_h, max(1, round(inside.height * 1.05)))
        if (new_w, new_h) != inside.size:
            resized = inside.resize((new_w, new_h), Image.Resampling.LANCZOS)
            inside.close()
            inside = resized
        result = _soft_edge_background(inside, (out_w, out_h))
    elif fit == "Ampliar fondo (sin recortar)":
        result = _extended_background(im, (out_w, out_h))
    else:
        result = Image.new("RGB", (out_w, out_h), "white")
    result.paste(inside, ((out_w - inside.width) // 2, (out_h - inside.height) // 2))
    inside.close()
    return result


def _paste_clipped_to_box(dest:Image.Image,src:Image.Image,origin:tuple[int,int],box:tuple[int,int,int,int]):
    """Pega el zoom dentro de la región, sin tapar otras fotos ni la encuadernación."""
    ox,oy=origin;x0,y0,x1,y1=box
    left=max(ox,x0,0);top=max(oy,y0,0)
    right=min(ox+src.width,x1,dest.width);bottom=min(oy+src.height,y1,dest.height)
    if right>left and bottom>top:
        region=src.crop((left-ox,top-oy,right-ox,bottom-oy))
        try:dest.paste(region,(left,top))
        finally:region.close()


def render_print_image(
    path: Path, opts: ExportOptions, *, preview_max_size: tuple[int, int] | None = None,
    page_index: int = 0,
) -> tuple[Image.Image, tuple[float, float], bool]:
    """Prepara la imagen final o una previsualización de idéntico encaje.

    El margen de encuadernación protege el contenido. En modo «Ampliar fondo»,
    el fondo difuminado también se extiende detrás de ese margen, sin colocar
    texto ni la fotografía principal en la zona de la espiral.

    Las páginas procedentes de PDF pueden venir de una exportación anterior de
    Revelo. Si detectamos un gran borde uniforme añadido en aquella exportación,
    se recorta primero para volver a aplicar el modo de encaje actual. Si no
    hay un borde claro y uniforme, se conserva la página entera.
    """
    opts.validate()
    w_mm, h_mm = dimensions_mm(path, opts)
    out_w, out_h = pixel_size(w_mm, h_mm, opts.dpi)
    full_w, full_h = out_w, out_h
    full_box = printable_box((out_w, out_h), (w_mm, h_mm),
                             binding=opts.binding, page_index=page_index)
    if preview_max_size is not None:
        max_w, max_h = preview_max_size
        if max_w <= 0 or max_h <= 0:
            raise ValueError("Las dimensiones de previsualización deben ser positivas")
        scale = min(1.0, max_w / out_w, max_h / out_h)
        out_w, out_h = max(1, round(out_w * scale)), max(1, round(out_h * scale))
    box = printable_box((out_w, out_h), (w_mm, h_mm),
                        binding=opts.binding, page_index=page_index)
    use_w, use_h = full_box[2] - full_box[0], full_box[3] - full_box[1]
    working, trimmed_pdf_border = _prepared_photo(path, opts)
    try:
        sw, sh = working.size
        print_scale=float(opts.photo_edits.get(path,{}).get('print_scale',1.0))
        fill_factor = max(use_w / sw, use_h / sh)
        contain_factor = min(use_w / sw, use_h / sh)
        low_resolution = (fill_factor if opts.fit == "Rellenar (recortar)" else contain_factor) > 1.25

        # Si el PDF importado no parece tener un borde artificial grande,
        # se conserva entero como página cerrada para no alterar su diseño.
        if path in opts.pdf_page_paths and not trimmed_pdf_border and path not in opts.photo_edits:
            whole = ImageOps.contain(working, (out_w, out_h), method=Image.Resampling.LANCZOS)
            if whole.size == (out_w, out_h):
                return whole, (w_mm, h_mm), low_resolution
            paper = Image.new("RGB", (out_w, out_h), "white")
            paper.paste(whole, ((out_w - whole.width)//2, (out_h - whole.height)//2))
            whole.close()
            return paper, (w_mm, h_mm), low_resolution

        # El fondo puede ocupar el canal de encuadernación, porque lo importante
        # es reservar ese espacio libre de contenido legible, no libre de tinta.
        if opts.binding and opts.fit == "Ampliar fondo (sin recortar)":
            full_bleed = _extended_background(working, (out_w, out_h))
            inside = ImageOps.contain(working, (max(8,round((box[2]-box[0])*print_scale)),
                                               max(8,round((box[3]-box[1])*print_scale))),
                                      method=Image.Resampling.LANCZOS)
            try:
                x = box[0] + ((box[2] - box[0]) - inside.width) // 2
                y = box[1] + ((box[3] - box[1]) - inside.height) // 2
                _paste_clipped_to_box(full_bleed,inside,(x,y),box)
            finally:
                inside.close()
            return full_bleed, (w_mm, h_mm), low_resolution

        if abs(print_scale-1.0)>0.002:
            # Zoom de página: no modifica la fuente ni crea un segundo marco
            # alrededor de la foto. Los límites se mantienen dentro del área.
            use_size=(max(8,round((box[2]-box[0])*print_scale)),
                      max(8,round((box[3]-box[1])*print_scale)))
            if opts.fit == 'Ampliar fondo (sin recortar)':
                paper = _extended_background(working,(out_w,out_h))
                photo=ImageOps.contain(working,use_size,Image.Resampling.LANCZOS)
                try:
                    x=round((box[0]+box[2]-photo.width)/2)
                    y=round((box[1]+box[3]-photo.height)/2)
                    _paste_clipped_to_box(paper,photo,(x,y),box)
                finally:photo.close()
            else:
                paper=Image.new('RGB',(out_w,out_h),'white')
                tile=_render_inside(working,use_size,opts.fit)
                try:
                    x=round((box[0]+box[2]-tile.width)/2)
                    y=round((box[1]+box[3]-tile.height)/2)
                    _paste_clipped_to_box(paper,tile,(x,y),box)
                finally:tile.close()
            return paper,(w_mm,h_mm),low_resolution

        result_inner = _render_inside(working, (box[2] - box[0], box[3] - box[1]), opts.fit)
        if not opts.binding:
            return result_inner, (w_mm, h_mm), low_resolution
        try:
            paper = Image.new("RGB", (out_w, out_h), "white")
            paper.paste(result_inner, (box[0], box[1]))
        finally:
            result_inner.close()
        return paper, (w_mm, h_mm), low_resolution
    finally:
        working.close()


def page_groups(paths: Sequence[Path], per_page: int,
                special_pages: dict[Path, dict] | None = None) -> list[tuple[Path, ...]]:
    """Agrupa fotos, pero una portada/separador ocupa siempre su hoja entera."""
    if per_page not in (1, 2, 3, 4, 6, 9):
        raise ValueError("Número de fotos por hoja no reconocido")
    specials = special_pages or {}
    groups: list[tuple[Path, ...]] = []
    pending: list[Path] = []
    for path in paths:
        if path in specials:
            if pending:
                groups.append(tuple(pending))
                pending.clear()
            groups.append((path,))
        else:
            pending.append(path)
            if len(pending) >= per_page:
                groups.append(tuple(pending))
                pending.clear()
    if pending:
        groups.append(tuple(pending))
    return groups


def _grid_shape(count: int, landscape: bool) -> tuple[int, int]:
    if count == 2:
        return (2, 1) if landscape else (1, 2)
    if count == 6:
        return (3, 2) if landscape else (2, 3)
    if count == 3:
        return (3, 1) if landscape else (1, 3)
    side = {4: 2, 9: 3}.get(count, 1)
    return side, side


def _extended_layout_background(
    paths: Sequence[Path], opts: ExportOptions,
    page_size: tuple[int, int], cell_rects: Sequence[tuple[int, int, int, int]],
    cols: int, rows: int,
) -> Image.Image:
    """Fondo difuminado de hoja COMPLETA para composiciones de varias fotos.

    El fondo utiliza una miniatura de cada imagen distribuyéndola por su zona
    de la página; se difumina ANTES de colocar las imágenes nítidas. De este
    modo también cubre los márgenes de encuadernación y los huecos entre fotos.
    No borra, recorta ni deforma las fotografías originales del primer plano.
    """
    out_w, out_h = page_size
    reduction = min(1.0, 1350 / max(out_w, out_h))
    small_w = max(1, round(out_w * reduction))
    small_h = max(1, round(out_h * reduction))
    small = Image.new("RGB", (small_w, small_h), (40, 50, 55))
    prepared: list[Image.Image] = []
    try:
        # La miniatura se calcula una sola vez por fuente, incluso cuando
        # una cuadrícula incompleta requiere repetirla para cubrir el fondo.
        for path in paths:
            prepared_image, _ = _prepared_photo(path, opts)
            prepared_image.thumbnail((1050, 1050), Image.Resampling.LANCZOS)
            prepared.append(prepared_image)

        # Cada fotografía extiende sus propios colores hasta la mitad del
        # hueco con la siguiente y hasta el borde exterior del papel.
        boundaries_x = [0]
        for col in range(1, cols):
            previous_right = cell_rects[col - 1][2]
            next_left = cell_rects[col][0]
            boundaries_x.append((previous_right + next_left) // 2)
        boundaries_x.append(out_w)
        boundaries_y = [0]
        for row in range(1, rows):
            previous_bottom = cell_rects[(row - 1) * cols][3]
            next_top = cell_rects[row * cols][1]
            boundaries_y.append((previous_bottom + next_top) // 2)
        boundaries_y.append(out_h)

        def to_small(coord: int, dimension: int, small_dimension: int) -> int:
            return round(coord * small_dimension / dimension)

        for row in range(rows):
            for col in range(cols):
                slot = row * cols + col
                source = prepared[min(slot, len(prepared) - 1)]
                left = to_small(boundaries_x[col], out_w, small_w)
                right = to_small(boundaries_x[col + 1], out_w, small_w)
                top = to_small(boundaries_y[row], out_h, small_h)
                bottom = to_small(boundaries_y[row + 1], out_h, small_h)
                if right <= left or bottom <= top:
                    continue
                patch = ImageOps.fit(source, (right - left, bottom - top),
                                     method=Image.Resampling.LANCZOS)
                try:
                    small.paste(patch, (left, top))
                finally:
                    patch.close()

        # Un suavizado común elimina cortes duros en el fondo, sin alterar
        # los contenidos nítidos que se colocarán encima más tarde.
        blurred = small.filter(ImageFilter.GaussianBlur(max(8, round(max(small_w, small_h) * .03))))
        if (small_w, small_h) == page_size:
            return blurred
        try:
            return blurred.resize(page_size, Image.Resampling.BICUBIC)
        finally:
            blurred.close()
    finally:
        for prepared_image in prepared:
            prepared_image.close()
        small.close()


def _blend_unaltered_photo_into_background(
    backdrop: Image.Image, image: Image.Image, target: tuple[int, int, int, int],
) -> None:
    """Une la foto nítida con un fondo extendido sin un borde rectangular duro.

    Solo difumina una franja exterior muy pequeña de la foto sobre el fondo.
    La mayor parte de la imagen permanece sin modificación, incluidos los
    textos y otros detalles importantes para imprimir.
    """
    left, top, right, bottom = target
    width, height = right - left, bottom - top
    if (width, height) != image.size:
        raise ValueError("Dimensiones inconsistentes para el encaje")
    # La transición no depende de los PPP: es un porcentaje de la fotografía.
    feather = max(3, min(42, round(min(width, height) * 0.035)))
    alpha = Image.new("L", (width, height), 255)
    # Generar degradados de alfa independientes en los cuatro bordes.
    # smoothstep evita cambios repentinos de pendiente visibles al imprimir.
    values = [round(255 * (x / feather) ** 2 * (3 - 2 * (x / feather)))
              for x in range(feather)]
    draw = ImageDraw.Draw(alpha)
    for i, opacity in enumerate(values):
        draw.line((i, i, width-1-i, i), fill=opacity)
        draw.line((i, height-1-i, width-1-i, height-1-i), fill=opacity)
        draw.line((i, i, i, height-1-i), fill=opacity)
        draw.line((width-1-i, i, width-1-i, height-1-i), fill=opacity)
    backdrop.paste(image, (left, top), alpha)
    alpha.close()


def _render_free_sheet(paths: Sequence[Path],opts: ExportOptions,
                       size:tuple[int,int],physical:tuple[float,float],
                       safe:tuple[int,int,int,int],page_index:int,
                       printed_number:int|None):
    """Collage con posiciones, tamaños y rotaciones individuales.

    Los archivos originales permanecen sin editar; la rotación se efectúa
    sobre una capa RGBA transparente de la hoja preparada.
    """
    from layout_editor import free_default,validate_layout_item
    out_w,out_h=size
    w_mm,h_mm=physical
    from layout_editor import free_sheet_background, visible_photo_geometry
    sheet_spec=validate_layout_item(opts.layout_items.get(paths[0]))
    sheet=free_sheet_background(paths,opts,size,
                sheet_spec.get('background','Según encaje'),
                sheet_spec.get('background_color','#FFFFFF'))
    x0,y0,x1,y1=safe
    zone_w=max(1,x1-x0);zone_h=max(1,y1-y0)
    lowres=False
    # Renderizar de atrás hacia delante según z (persistente en proyectos y PDF).
    indices=sorted(range(len(paths)),key=lambda index:(
        validate_layout_item(opts.layout_items.get(paths[index])).get('z',index),index))
    for index in indices:
        path=paths[index]
        spec=validate_layout_item(opts.layout_items.get(path))
        geom=spec.get('rect',free_default(index,len(paths))['rect'])
        cx,cy,rw,rh=geom
        bw=max(10,round(zone_w*rw));bh=max(10,round(zone_h*rh))
        cap=opts.captions.get(path)
        footer=footer_height_px(bh,out_w/w_mm,cap)
        img_height=max(10,bh-footer)
        content,_=_prepared_photo(path,opts)
        try:
            sw,sh=content.size
            scale=(float(cap.get('photo_scale',1.0)) if cap else 1.0)*float(opts.photo_edits.get(path,{}).get('print_scale',1.0))
            usable=(max(8,round(bw*scale)),max(8,round(img_height*scale)))
            lowres|=min(usable[0]/sw,usable[1]/sh)>1.25
            # Rotar una capa transparente ya encajada: las esquinas fuera del
            # rectángulo no tapan otras fotos ni la hoja de fondo.
            photo=ImageOps.contain(content,usable,Image.Resampling.LANCZOS).convert('RGBA')
            try:
                rotated=photo.rotate(-float(spec.get('angle',0.)),Image.Resampling.BICUBIC,expand=True)
                try:
                    px=round(x0+zone_w*cx-rotated.width/2)
                    py=round(y0+zone_h*cy-footer/2-rotated.height/2)
                    sheet.paste(rotated,(px,py),rotated)
                finally:rotated.close()
            finally:photo.close()
        finally:content.close()
        if has_caption(cap):
            left=round(x0+zone_w*cx-bw/2)
            top=round(y0+zone_h*cy-bh/2)
            # La leyenda conserva la orientación horizontal de lectura.
            # En modo libre superpuesto no se convierte en un cartel opaco.
            rect=(max(0,left),max(0,top),min(out_w,left+bw),min(out_h,top+bh))
            if rect[2]>rect[0] and rect[3]>rect[1]:
                draw_caption(sheet,rect,cap,mode=cap.get('placement','Debajo'),
                             px_per_mm=out_w/w_mm)
    draw_page_number(sheet,printed_number,placement=opts.numbering_position,
                     physical_mm=physical,page_index=page_index,
                     number_format=opts.numbering_format)
    return sheet,physical,lowres


def render_layout_page(
    paths: Sequence[Path], opts: ExportOptions, *,
    preview_max_size: tuple[int, int] | None = None, page_index: int = 0,
    printed_number: int | None = None,
) -> tuple[Image.Image, tuple[float, float], bool]:
    """Renderiza una hoja con todas las fotografías indicadas.

    Una sola imagen en modo 1 mantiene el comportamiento de Revelo v1.3.
    Las páginas con varias fotos dejan 3 mm entre celdas y respetan el canal
    de encuadernación de la hoja completa.
    """
    opts.validate()
    if not paths:
        raise ValueError("La página no contiene fotografías")
    if len(paths) == 1 and paths[0] in opts.special_pages:
        from special_pages import render_special_page
        w_mm, h_mm = dimensions_mm(paths[0], opts)
        out_w, out_h = pixel_size(w_mm, h_mm, opts.dpi)
        if preview_max_size is not None:
            max_w, max_h = preview_max_size
            if max_w <= 0 or max_h <= 0:
                raise ValueError("Previsualización no válida")
            scale = min(1.0, max_w/out_w, max_h/out_h)
            out_w, out_h = max(1, round(out_w*scale)), max(1, round(out_h*scale))
        safe = printable_box((out_w, out_h), (w_mm, h_mm),
                             binding=opts.binding, page_index=page_index)
        special_result = render_special_page(opts.special_pages[paths[0]], (out_w, out_h), safe)
        draw_page_number(special_result, printed_number, placement=opts.numbering_position,
                         physical_mm=(w_mm,h_mm), page_index=page_index, number_format=opts.numbering_format)
        return special_result, (w_mm,h_mm), False
    if any(path in opts.special_pages for path in paths):
        raise ValueError("Las portadas y separadores deben ocupar una hoja completa")
    if opts.photos_per_page == 1 and opts.layout_template != "Diseño libre" and not has_caption(opts.captions.get(paths[0])):
        single, phys, lowres = render_print_image(paths[0], opts, preview_max_size=preview_max_size,
                                                   page_index=page_index)
        draw_page_number(single, printed_number, placement=opts.numbering_position,
                         physical_mm=phys, page_index=page_index, number_format=opts.numbering_format)
        return single, phys, lowres
    if len(paths) > opts.photos_per_page:
        raise ValueError("Demasiadas fotografías para la hoja seleccionada")
    w_mm, h_mm = dimensions_mm(paths[0], opts)
    out_w, out_h = pixel_size(w_mm, h_mm, opts.dpi)
    if preview_max_size:
        if min(preview_max_size) <= 0:
            raise ValueError("Previsualización no válida")
        scale = min(1.0, preview_max_size[0] / out_w, preview_max_size[1] / out_h)
        out_w, out_h = max(1, round(out_w * scale)), max(1, round(out_h * scale))
    if opts.binding:
        x0, y0, x1, y1 = printable_box((out_w, out_h), (w_mm, h_mm),
                                       binding=True, page_index=page_index)
    else:
        margin = max(1, round(out_w * 3 / w_mm))
        margin_y = max(1, round(out_h * 3 / h_mm))
        x0, y0, x1, y1 = margin, margin_y, out_w-margin, out_h-margin_y
    gap_x = max(1, round(out_w * 3 / w_mm))
    gap_y = max(1, round(out_h * 3 / h_mm))
    template = (opts.layout_template if opts.photos_per_page == 3 or
                opts.layout_template == 'Diseño libre' else 'Cuadrícula')
    if template == 'Diseño libre':
        return _render_free_sheet(paths,opts,(out_w,out_h),(w_mm,h_mm),
                                  (x0,y0,x1,y1),page_index,printed_number)
    if template != 'Cuadrícula' and len(paths) == 3:
        from layout_editor import editable_template_rects
        cell_rects = editable_template_rects((x0,y0,x1,y1),gap_x,gap_y,template,
                                              opts.layout_items.get(paths[0],{}))
    else:
        cell_rects = template_rects((x0, y0, x1, y1), gap_x, gap_y,
                                     template='Cuadrícula', count=opts.photos_per_page,
                                     landscape=w_mm > h_mm)
    cols, rows = _grid_shape(opts.photos_per_page, w_mm > h_mm)
    if opts.fit == "Ampliar fondo (sin recortar)":
        if template != "Cuadrícula":
            first, _ = _prepared_photo(paths[0], opts)
            try:
                sheet = _extended_background(first, (out_w, out_h))
            finally:
                first.close()
        else:
            sheet = _extended_layout_background(paths, opts, (out_w, out_h),
                                                cell_rects, cols, rows)
    else:
        sheet = Image.new("RGB", (out_w, out_h), "white")
    lowres_any = False
    for idx, path in enumerate(paths):
        cx0, cy0, cx1, cy1 = cell_rects[idx]
        cw, ch = cx1 - cx0, cy1 - cy0
        cap = opts.captions.get(path)
        photo_scale=(float(cap.get('photo_scale',1.0)) if cap else 1.0)*float(opts.photo_edits.get(path,{}).get('print_scale',1.0))
        footer_px = footer_height_px(ch, out_w / w_mm, cap)
        photo_bottom = cy1-footer_px
        photo_ch = photo_bottom-cy0
        if photo_ch < 10:
            raise ValueError("No queda espacio para la foto con ese pie de foto")
        content, _ = _prepared_photo(path, opts)
        below_caption_start = None
        try:
            sw, sh = content.size
            factor = (max(cw / sw, photo_ch / sh) if opts.fit == "Rellenar (recortar)"
                      else min(cw / sw, photo_ch / sh))
            lowres_any |= factor > 1.25
            if (cap and cap.get('placement', 'Debajo') == 'Debajo'
                    and opts.fit == 'Ajustar (sin recortar)'):
                # Foto y pie como un bloque visual. Evita una franja enorme
                # entre la imagen centrada y su texto en celdas altas.
                photo = ImageOps.contain(content, (max(8,round(cw*photo_scale)),
                                                   max(8,round(photo_ch*photo_scale))),
                                          method=Image.Resampling.LANCZOS)
                try:
                    space=max(3,round(out_w/w_mm * 1.5))
                    total=photo.height+footer_px+space
                    top=cy0+max(0,(ch-total)//2)
                    left=cx0+(cw-photo.width)//2
                    sheet.paste(photo,(left,top))
                    below_caption_start=top+photo.height+space
                finally:
                    photo.close()
            elif opts.fit == "Ampliar fondo (sin recortar)":
                # La propia hoja ya tiene un fondo común; pegar una celda
                # con su fondo particular crea un rectángulo perfectamente
                # visible. Solo superponemos la foto nítida y fundimos sus
                # bordes en el fondo de la hoja.
                photo = ImageOps.contain(content, (max(8,round(cw*photo_scale)),
                                                   max(8,round(photo_ch*photo_scale))),
                                          method=Image.Resampling.LANCZOS)
                try:
                    left = cx0 + (cw - photo.width) // 2
                    top = cy0 + (photo_ch - photo.height) // 2
                    if photo_scale>1:
                        _paste_clipped_to_box(sheet,photo,(left,top),(cx0,cy0,cx1,photo_bottom))
                    else:
                        _blend_unaltered_photo_into_background(
                            sheet, photo, (left, top, left+photo.width, top+photo.height))
                finally:
                    photo.close()
            else:
                tile_w=max(8,round(cw*photo_scale));tile_h=max(8,round(photo_ch*photo_scale))
                tile = _render_inside(content, (tile_w, tile_h), opts.fit)
                try:
                    _paste_clipped_to_box(sheet,tile,(cx0+(cw-tile_w)//2,cy0+(photo_ch-tile_h)//2),
                                           (cx0,cy0,cx1,photo_bottom))
                finally:
                    tile.close()
        finally:
            content.close()
        draw_caption(sheet, (cx0,cy0,cx1,cy1), cap,
                     mode=cap.get("placement", "Debajo") if cap else "Debajo",
                     px_per_mm=out_w/w_mm, below_start_y=below_caption_start)
    draw_page_number(sheet, printed_number, placement=opts.numbering_position,
                     physical_mm=(w_mm,h_mm), page_index=page_index, number_format=opts.numbering_format)
    return sheet, (w_mm, h_mm), lowres_any


def _safe_basename(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .") or "foto"


def _distinct_file(folder: Path, basename: str, suffix: str) -> Path:
    name = folder / (basename + suffix)
    i = 2
    while name.exists():
        name = folder / f"{basename}_{i}{suffix}"
        i += 1
    return name


def _save_original_format(im: Image.Image, path: Path, source_path: Path, dpi: int) -> Path:
    ext = source_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        ext = ".png"
    target = _distinct_file(path.parent, path.stem, ext)
    options: dict = {}
    if ext in (".jpg", ".jpeg"):
        options.update(format="JPEG", quality=95, subsampling=0, dpi=(dpi, dpi), optimize=True)
    elif ext == ".png":
        options.update(format="PNG", dpi=(dpi, dpi), optimize=True)
    elif ext == ".webp":
        options.update(format="WEBP", quality=95, method=5, dpi=(dpi, dpi))
    elif ext in (".tif", ".tiff"):
        options.update(format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    elif ext in (".heic", ".heif"):
        options.update(format="HEIF", quality=95)  # requiere pillow-heif (incluido)
    elif ext == ".bmp":
        options.update(format="BMP")  # BMP no conserva DPI de forma uniforme.
    im.save(target, **options)
    return target


def _jpeg_stream(im: Image.Image, dpi: int) -> BytesIO:
    stream = BytesIO()
    im.save(stream, format="JPEG", quality=94, subsampling=0, dpi=(dpi, dpi))
    stream.seek(0)
    return stream


def export_images(paths: Sequence[Path], opts: ExportOptions, dest: Path, progress: Progress | None = None) -> tuple[Path, int]:
    """Exporta a carpeta nueva en la ubicación escogida (sin pisar originales)."""
    opts.validate()
    if not paths:
        raise ValueError("No hay fotos para exportar")
    dest.mkdir(parents=True, exist_ok=True)
    label = _safe_basename(opts.paper.replace(" × ", "x").replace(" ", ""))
    folder = _distinct_file(dest, f"Revelo_{label}_{datetime.now():%Y%m%d_%H%M%S}", "")
    folder.mkdir()
    lowres_count = 0
    groups = page_groups(paths, opts.photos_per_page, opts.special_pages)
    numbers = numbers_for_groups(groups, opts.special_pages,
                                 enabled=opts.numbering_enabled, start=opts.numbering_start,
                                 skip_special=opts.numbering_skip_special)
    for i, group in enumerate(groups, 1):
        rendered, _, lowres = render_layout_page(group, opts, page_index=i - 1,
                                                 printed_number=numbers[i-1])
        lowres_count += int(lowres)
        if opts.photos_per_page == 1 and group[0] not in opts.special_pages:
            out_base = _safe_basename(f"{i:02d}_{group[0].stem}_{label}")
            _save_original_format(rendered, folder / out_base, group[0], opts.dpi)
        else:
            # Varias fotografías pueden tener formatos distintos: la hoja
            # completa se guarda en PNG sin pérdida, no como un falso JPG/HEIC.
            target = folder / f"{i:02d}_pagina_{label}.png"
            rendered.save(target, format="PNG", dpi=(opts.dpi, opts.dpi), optimize=True)
        rendered.close()
        if progress:
            progress(i, len(groups), f"Hoja {i}")
    return folder, lowres_count


def export_pdf(paths: Sequence[Path], opts: ExportOptions, target: Path, progress: Progress | None = None) -> tuple[Path, int]:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    opts.validate()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = Canvas(str(target), pagesize=(595, 842), pageCompression=1)
    document.setTitle(f"Revelo · {opts.paper}")
    lowres_count = 0
    try:
        groups = page_groups(paths, opts.photos_per_page, opts.special_pages)
        numbers = numbers_for_groups(groups, opts.special_pages,
                                     enabled=opts.numbering_enabled, start=opts.numbering_start,
                                     skip_special=opts.numbering_skip_special)
        for i, group in enumerate(groups, 1):
            rendered, (w_mm, h_mm), lowres = render_layout_page(group, opts, page_index=i - 1,
                                                                 printed_number=numbers[i-1])
            lowres_count += int(lowres)
            w_pt, h_pt = w_mm * 72 / 25.4, h_mm * 72 / 25.4
            document.setPageSize((w_pt, h_pt))
            stream = _jpeg_stream(rendered, opts.dpi)
            document.drawImage(ImageReader(stream), 0, 0, width=w_pt, height=h_pt)
            document.showPage()
            rendered.close()
            stream.close()
            if progress:
                progress(i, len(groups), f"Hoja {i}")
        document.save()
        # Guardar fuentes originales dentro de la copia PDF: futuras importaciones
        # pueden recuperar cada fotografía, sin confundirla con los fondos borrosos.
        from pdf_sources import attach_sources
        attach_sources(target, list(paths), opts.photos_per_page, opts.pdf_page_paths,
                       special_pages=opts.special_pages, photo_edits=opts.photo_edits,
                       captions=opts.captions, layout_template=opts.layout_template,
                       layout_items=opts.layout_items)
        if progress:
            progress(len(groups), len(groups), "Originales incluidos en el PDF")
    except Exception:
        try:
            document.save()
        except Exception:
            pass
        target.unlink(missing_ok=True)
        raise
    return target, lowres_count


def _add_page_image_as_anchor(paragraph, jpeg: BytesIO, w_mm: float, h_mm: float) -> None:
    """Imagen anclada a la esquina superior izquierda de la página, sin márgenes.

    Los elementos flotantes evitan que Word genere una segunda página por
    considerar que la altura de la imagen + la línea superan la hoja.
    """
    from copy import deepcopy
    from docx.shared import Mm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    run = paragraph.add_run()
    inline_shape = run.add_picture(jpeg, width=Mm(w_mm), height=Mm(h_mm))
    inline = inline_shape._inline
    anchor = OxmlElement("wp:anchor")
    for name, value in {
        "distT": "0", "distB": "0", "distL": "0", "distR": "0",
        "simplePos": "0", "relativeHeight": "0", "behindDoc": "1",
        "locked": "0", "layoutInCell": "1", "allowOverlap": "1",
    }.items():
        anchor.set(name, value)

    simple = OxmlElement("wp:simplePos")
    simple.set("x", "0")
    simple.set("y", "0")
    anchor.append(simple)
    for axis in ("H", "V"):
        pos = OxmlElement(f"wp:position{axis}")
        pos.set("relativeFrom", "page")
        offset = OxmlElement("wp:posOffset")
        offset.text = "0"
        pos.append(offset)
        anchor.append(pos)
    anchor.append(deepcopy(inline.extent))
    anchor.append(OxmlElement("wp:wrapNone"))
    for child in inline:
        if child.tag in (qn("wp:docPr"), qn("wp:cNvGraphicFramePr"), qn("a:graphic")):
            anchor.append(deepcopy(child))
    inline.getparent().replace(inline, anchor)


def export_word(paths: Sequence[Path], opts: ExportOptions, target: Path, progress: Progress | None = None) -> tuple[Path, int]:
    from docx import Document
    from docx.enum.section import WD_SECTION_START
    from docx.shared import Mm, Pt

    opts.validate()
    target.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    style = document.styles["Normal"]
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = Pt(1)
    lowres_count = 0
    groups = page_groups(paths, opts.photos_per_page, opts.special_pages)
    numbers = numbers_for_groups(groups, opts.special_pages,
                                 enabled=opts.numbering_enabled, start=opts.numbering_start,
                                 skip_special=opts.numbering_skip_special)
    for i, group in enumerate(groups, 1):
        rendered, (w_mm, h_mm), lowres = render_layout_page(group, opts, page_index=i - 1,
                                                             printed_number=numbers[i-1])
        lowres_count += int(lowres)
        if i == 1:
            section = document.sections[0]
        else:
            # Cada hoja es una sección: permite orientaciones mixtas.
            section = document.add_section(WD_SECTION_START.NEW_PAGE)
        section.page_width = Mm(w_mm)
        section.page_height = Mm(h_mm)
        section.top_margin = Mm(0)
        section.bottom_margin = Mm(0)
        section.left_margin = Mm(0)
        section.right_margin = Mm(0)
        section.header_distance = Mm(0)
        section.footer_distance = Mm(0)
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = Pt(1)
        stream = _jpeg_stream(rendered, opts.dpi)
        _add_page_image_as_anchor(paragraph, stream, w_mm, h_mm)
        stream.close()
        rendered.close()
        if progress:
            progress(i, len(groups), f"Hoja {i}")
    document.core_properties.title = f"Revelo · {opts.paper}"
    document.save(str(target))
    return target, lowres_count


def export(paths: Sequence[Path], opts: ExportOptions, dest: Path, progress: Progress | None = None) -> tuple[Path, int]:
    if not paths:
        raise ValueError("Añade al menos una foto")
    if opts.fmt == "Imagenes":
        return export_images(paths, opts, dest, progress)
    if opts.fmt == "PDF":
        return export_pdf(paths, opts, dest, progress)
    return export_word(paths, opts, dest, progress)
