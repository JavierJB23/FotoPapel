"""Núcleo de impresión y exportación de Revelo.

Dependencias: Pillow, reportlab y python-docx. No utiliza servicios web.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence
import math
import re

from PIL import Image, ImageOps, ImageFilter, ImageStat, ImageDraw, ImageChops, UnidentifiedImageError


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

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
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
    """Intenta aislar el contenido útil de una página PDF ya exportada.

    Se usa al reimportar PDFs creados previamente por Revelo. Si la página
    contiene un gran borde uniforme (normalmente blanco o gris muy claro),
    lo recorta para poder volver a aplicar el encaje elegido en la sesión
    actual. Si no detecta un marco suficientemente claro y uniforme, deja la
    página intacta.
    """
    if source.width < 40 or source.height < 40:
        return source.copy(), False

    thumb = source.convert("RGB")
    scale = min(1.0, 420 / max(thumb.width, thumb.height))
    if scale < 1.0:
        thumb = thumb.resize((max(1, round(thumb.width * scale)),
                              max(1, round(thumb.height * scale))),
                             Image.Resampling.BILINEAR)
    try:
        w, h = thumb.size
        strip = max(4, min(w, h) // 40)
        corners = [
            thumb.crop((0, 0, strip, strip)),
            thumb.crop((w - strip, 0, w, strip)),
            thumb.crop((0, h - strip, strip, h)),
            thumb.crop((w - strip, h - strip, w, h)),
        ]
        means = [ImageStat.Stat(part).mean[:3] for part in corners]
        bg = tuple(round(sum(m[i] for m in means) / len(means)) for i in range(3))
        border_parts = [
            thumb.crop((0, 0, w, strip)),
            thumb.crop((0, h - strip, w, h)),
            thumb.crop((0, 0, strip, h)),
            thumb.crop((w - strip, 0, w, h)),
        ]
        std = max(max(ImageStat.Stat(part).stddev[:3]) for part in border_parts)
        brightness = sum(bg) / 3
        if brightness < 205 or std > 16:
            return source.copy(), False

        solid = Image.new("RGB", thumb.size, bg)
        diff = ImageChops.difference(thumb, solid)
        mask = diff.convert("L").point(lambda value: 255 if value > 18 else 0)
        bbox = mask.getbbox()
        if not bbox:
            return source.copy(), False
        left, top, right, bottom = bbox
        margin_left, margin_top = left, top
        margin_right, margin_bottom = w - right, h - bottom
        min_margin = max(8, round(min(w, h) * 0.035))
        if min(margin_left, margin_top, margin_right, margin_bottom) < min_margin:
            return source.copy(), False
        # Evita recortes exagerados cuando el contenido útil ocupa muy poco.
        if (right - left) < w * 0.45 or (bottom - top) < h * 0.45:
            return source.copy(), False
        scale_x = source.width / w
        scale_y = source.height / h
        crop = (
            max(0, math.floor(left * scale_x)),
            max(0, math.floor(top * scale_y)),
            min(source.width, math.ceil(right * scale_x)),
            min(source.height, math.ceil(bottom * scale_y)),
        )
        if crop[2] - crop[0] >= source.width - 4 and crop[3] - crop[1] >= source.height - 4:
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
    with Image.open(path) as raw:
        im = _flatten_rgb(ImageOps.exif_transpose(raw))
    try:
        working = im
        trimmed_pdf_border = False
        if path in opts.pdf_page_paths:
            working, trimmed_pdf_border = _trim_revelo_like_page_background(im)
        try:
            sw, sh = working.size
            fill_factor = max(use_w / sw, use_h / sh)
            contain_factor = min(use_w / sw, use_h / sh)
            low_resolution = (fill_factor if opts.fit == "Rellenar (recortar)" else contain_factor) > 1.25

            # Si el PDF importado no parece tener un borde artificial grande,
            # se conserva entero como página cerrada para no alterar su diseño.
            if path in opts.pdf_page_paths and not trimmed_pdf_border:
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
                inside = ImageOps.contain(working, (box[2] - box[0], box[3] - box[1]),
                                          method=Image.Resampling.LANCZOS)
                try:
                    x = box[0] + ((box[2] - box[0]) - inside.width) // 2
                    y = box[1] + ((box[3] - box[1]) - inside.height) // 2
                    full_bleed.paste(inside, (x, y))
                finally:
                    inside.close()
                return full_bleed, (w_mm, h_mm), low_resolution

            result_inner = _render_inside(working, (box[2] - box[0], box[3] - box[1]), opts.fit)
        finally:
            if working is not im:
                working.close()
        if not opts.binding:
            return result_inner, (w_mm, h_mm), low_resolution
        try:
            paper = Image.new("RGB", (out_w, out_h), "white")
            paper.paste(result_inner, (box[0], box[1]))
        finally:
            result_inner.close()
        return paper, (w_mm, h_mm), low_resolution
    finally:
        im.close()


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
    for i, path in enumerate(paths, 1):
        rendered, _, lowres = render_print_image(path, opts, page_index=i - 1)
        lowres_count += int(lowres)
        out_base = _safe_basename(f"{i:02d}_{path.stem}_{label}")
        _save_original_format(rendered, folder / out_base, path, opts.dpi)
        rendered.close()
        if progress:
            progress(i, len(paths), path.name)
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
        for i, path in enumerate(paths, 1):
            rendered, (w_mm, h_mm), lowres = render_print_image(path, opts, page_index=i - 1)
            lowres_count += int(lowres)
            w_pt, h_pt = w_mm * 72 / 25.4, h_mm * 72 / 25.4
            document.setPageSize((w_pt, h_pt))
            stream = _jpeg_stream(rendered, opts.dpi)
            document.drawImage(ImageReader(stream), 0, 0, width=w_pt, height=h_pt)
            document.showPage()
            rendered.close()
            stream.close()
            if progress:
                progress(i, len(paths), path.name)
        document.save()
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
    for i, path in enumerate(paths, 1):
        rendered, (w_mm, h_mm), lowres = render_print_image(path, opts, page_index=i - 1)
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
            progress(i, len(paths), path.name)
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
