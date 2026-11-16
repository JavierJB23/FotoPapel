"""Núcleo de impresión y exportación de FotoPapel.

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

from PIL import Image, ImageOps, UnidentifiedImageError


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


@dataclass(frozen=True)
class ExportOptions:
    paper: str = "A4"
    orientation: str = "Automática"  # Automática / Vertical / Horizontal
    fit: str = "Ajustar (sin recortar)"  # Ajustar... / Rellenar (recortar)
    dpi: int = 300
    fmt: str = "PDF"  # Imagenes / PDF / Word

    def validate(self) -> None:
        if self.paper not in PAPER_SIZES:
            raise ValueError("Tamaño de papel no reconocido")
        if self.orientation not in ("Automática", "Vertical", "Horizontal"):
            raise ValueError("Orientación no reconocida")
        if self.fit not in ("Ajustar (sin recortar)", "Rellenar (recortar)"):
            raise ValueError("Modo de encaje no reconocido")
        if not (72 <= self.dpi <= 600):
            raise ValueError("Los PPP deben estar entre 72 y 600")
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


def render_print_image(path: Path, opts: ExportOptions) -> tuple[Image.Image, tuple[float, float], bool]:
    """Devuelve imagen RGB de píxeles exactos, medidas mm y aviso de reescalado."""
    opts.validate()
    w_mm, h_mm = dimensions_mm(path, opts)
    out_w, out_h = pixel_size(w_mm, h_mm, opts.dpi)
    with Image.open(path) as raw:
        im = _flatten_rgb(ImageOps.exif_transpose(raw))
    sw, sh = im.size
    if opts.fit == "Rellenar (recortar)":
        factor = max(out_w / sw, out_h / sh)
        low_resolution = factor > 1.25
        result = ImageOps.fit(im, (out_w, out_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    else:
        factor = min(out_w / sw, out_h / sh)
        low_resolution = factor > 1.25
        inside = ImageOps.contain(im, (out_w, out_h), method=Image.Resampling.LANCZOS)
        result = Image.new("RGB", (out_w, out_h), "white")
        result.paste(inside, ((out_w - inside.width) // 2, (out_h - inside.height) // 2))
    im.close()
    return result, (w_mm, h_mm), low_resolution


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
    folder = _distinct_file(dest, f"FotoPapel_{label}_{datetime.now():%Y%m%d_%H%M%S}", "")
    folder.mkdir()
    lowres_count = 0
    for i, path in enumerate(paths, 1):
        rendered, _, lowres = render_print_image(path, opts)
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
    document.setTitle(f"FotoPapel · {opts.paper}")
    lowres_count = 0
    try:
        for i, path in enumerate(paths, 1):
            rendered, (w_mm, h_mm), lowres = render_print_image(path, opts)
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
        rendered, (w_mm, h_mm), lowres = render_print_image(path, opts)
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
    document.core_properties.title = f"FotoPapel · {opts.paper}"
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
