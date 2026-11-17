"""Fuentes originales portables dentro de PDF generados por Revelo.

El PDF sigue siendo imprimible en cualquier visor: las páginas visibles no cambian.
El adjunto es opcional para otros lectores, pero Revelo puede volver a importar
las imágenes fuente sin confundirlas con fondos o márgenes de maquetación.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Collection
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile, BadZipFile
import json
import os

from processor import SUPPORTED_EXTENSIONS, source_dimensions

ATTACHMENT_NAME = "Revelo_fuentes_originales.zip"
FORMAT_NAME = "revelo-original-sources"
FORMAT_VERSION = 1
MAX_IMAGES = 1000
MAX_SOURCE_BYTES = 120 * 1024 * 1024  # no aceptar archivos individuales mayores
MAX_TOTAL_BYTES = 650 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024


def _make_bundle(paths: list[Path], photos_per_page: int,
                 pdf_page_paths: Collection[Path] = ()) -> bytes:
    if not paths or len(paths) > MAX_IMAGES:
        raise ValueError("Demasiadas imágenes para guardar sus originales en el PDF")
    items = []
    total = 0
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED, compresslevel=3, allowZip64=True) as z:
        for index, path in enumerate(paths, 1):
            path = Path(path)
            size = path.stat().st_size
            if size > MAX_SOURCE_BYTES:
                raise ValueError("Una de las imágenes es demasiado grande para el archivo PDF editable")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("Las fotografías originales superan el límite del PDF reversible")
            # Si la fuente viene de un PDF antiguo, su PNG contiene fondo y
            # márgenes artificiales. Los quitamos cuando sea posible ANTES de
            # guardarla como referencia para PDFs posteriores. Nunca modifica
            # el archivo temporal de la importación original.
            normalized = None
            ext = path.suffix.lower()
            if path in pdf_page_paths:
                from PIL import Image
                from processor import _trim_revelo_like_page_background
                with Image.open(path) as page:
                    rgb = page.convert("RGB")
                try:
                    extracted, detected = _trim_revelo_like_page_background(rgb)
                finally:
                    rgb.close()
                try:
                    if detected:
                        data = BytesIO()
                        extracted.save(data, "PNG", optimize=False)
                        normalized = data.getvalue()
                        size = len(normalized)
                        ext = ".png"
                finally:
                    extracted.close()
            if ext not in SUPPORTED_EXTENSIONS:
                ext = ".png"
            key = f"assets/{index:05d}{ext}"
            checksum = sha256()
            if normalized is not None:
                checksum.update(normalized)
                z.writestr(key, normalized)
            else:
                with path.open("rb") as stream, z.open(key, "w") as dst:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        checksum.update(block)
                        dst.write(block)
            if size > MAX_SOURCE_BYTES:
                raise ValueError("Una imagen recuperada es demasiado grande")
            items.append({"name": path.name[:180], "asset": key,
                          "page": (index - 1) // photos_per_page,
                          "sha256": checksum.hexdigest(), "size": size,
                          "recovered_from_flat_pdf": path in pdf_page_paths})
        manifest = {"format": FORMAT_NAME, "version": FORMAT_VERSION,
                    "photos_per_page": photos_per_page, "items": items}
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    return buffer.getvalue()


def attach_sources(pdf_path: Path, paths: list[Path], photos_per_page: int,
                   pdf_page_paths: Collection[Path] = ()) -> None:
    """Inserta fuentes originales en un PDF sin modificar sus páginas visibles.

    Operación segura: el PDF existente solo se sustituye si la copia revisada
    con su adjunto se ha escrito correctamente.
    """
    from pypdf import PdfReader, PdfWriter

    pdf_path = Path(pdf_path)
    content = _make_bundle(paths, photos_per_page, pdf_page_paths)
    writer = PdfWriter()
    reader = PdfReader(str(pdf_path), strict=False)
    writer.append(reader)
    writer.add_metadata({"/Title": f"Revelo - impresión {pdf_path.stem}"})
    writer.add_attachment(ATTACHMENT_NAME, content)
    tmp = None
    try:
        with NamedTemporaryFile(mode="wb", dir=pdf_path.parent,
                                prefix=".revelo_pdf_", suffix=".tmp", delete=False) as handle:
            tmp = Path(handle.name)
            writer.write(handle)
        # El lector debe poder abrir el documento con el nuevo adjunto.
        verify = PdfReader(str(tmp), strict=False)
        if len(verify.pages) != len(reader.pages):
            raise ValueError("Las páginas del PDF han cambiado al guardar los originales")
        os.replace(tmp, pdf_path)
        tmp = None
    finally:
        writer.close()
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def recover_sources(pdf_path: Path, folder: Path, progress=None):
    """Devuelve (paths, pages, per_sheet) si el PDF incluye originales Revelo.

    Si no hay adjunto devuelve None, para permitir importación clásica. Los
    límites de tamaño y nombres impiden la extracción de rutas externas.
    """
    from pypdf import PdfReader

    pdf_path = Path(pdf_path)
    pdf = PdfReader(str(pdf_path), strict=False)
    files = pdf.attachments
    sources = files.get(ATTACHMENT_NAME)
    if not sources:
        return None
    content = sources[0]
    if len(content) > MAX_TOTAL_BYTES + 70 * 1024 * 1024:
        raise ValueError("El adjunto de originales supera el límite permitido")
    items_out = []
    total = 0
    staged = []
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(BytesIO(content)) as z:
            info = {f.filename: f for f in z.infolist()}
            if len(info) != len(z.infolist()):
                raise ValueError("El PDF contiene nombres de archivos duplicados")
            if "manifest.json" not in info or info["manifest.json"].file_size > MAX_MANIFEST_BYTES:
                raise ValueError("El índice de las fotos originales está dañado")
            manifest = json.loads(z.read("manifest.json"))
            if manifest.get("format") != FORMAT_NAME or manifest.get("version") != FORMAT_VERSION:
                raise ValueError("Versión de fotos originales no compatible")
            items = manifest.get("items")
            photos_per_page = manifest.get("photos_per_page")
            if (not isinstance(items, list) or not 0 < len(items) <= MAX_IMAGES
                    or photos_per_page not in (1, 2, 4, 6, 9)
                    or len(info) != len(items) + 1):
                raise ValueError("El índice de originales del PDF no es válido")
            for idx, item in enumerate(items, 1):
                if not isinstance(item, dict):
                    raise ValueError("Entrada de fotografía no válida")
                key = item.get("asset")
                if not isinstance(key, str) or not key.startswith(f"assets/{idx:05d}."):
                    raise ValueError("Ruta de imagen no permitida")
                ext = Path(key).suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS or key not in info or info[key].is_dir():
                    raise ValueError("Imagen del PDF desconocida")
                entry = info[key]
                size = item.get("size")
                checksum = item.get("sha256")
                page = item.get("page")
                if (not isinstance(size, int) or size != entry.file_size
                        or size > MAX_SOURCE_BYTES or size < 1
                        or not isinstance(checksum, str) or len(checksum) != 64
                        or not isinstance(page, int) or page != (idx - 1) // photos_per_page
                        or page >= len(pdf.pages)):
                    raise ValueError("Los originales del PDF no coinciden con su índice")
                total += size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("Las fotografías originales superan el tamaño permitido")
                dest = folder / f"foto_original_{idx:05d}{ext}"
                digest = sha256()
                with z.open(key) as inp, dest.open("wb") as out:
                    for block in iter(lambda: inp.read(1024 * 1024), b""):
                        digest.update(block)
                        out.write(block)
                staged.append(dest)
                if digest.hexdigest() != checksum:
                    raise ValueError("Una de las fotografías originales está dañada")
                try:
                    source_dimensions(dest)
                except Exception as exc:
                    raise ValueError("Una de las imágenes originales no se puede abrir") from exc
                items_out.append(dest)
                if progress:
                    progress(idx, len(items), pdf_path.name)
        # Cada foto conserva la dimensión de papel de la hoja que la alojaba.
        sizes = []
        for item in items:
            page = pdf.pages[item["page"]]
            sizes.append((float(page.mediabox.width) * 25.4 / 72,
                          float(page.mediabox.height) * 25.4 / 72))
        return items_out, sizes, photos_per_page
    except (ValueError, OSError, BadZipFile, json.JSONDecodeError, KeyError):
        for file in staged:
            file.unlink(missing_ok=True)
        raise
