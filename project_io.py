"""Proyectos portables de Revelo (.revelo): ZIP con imágenes embebidas y orden.

No se ejecutan archivos del proyecto. Los elementos se extraen solo mediante rutas
internas generadas por la aplicación, con límites de tamaño y verificación SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Callable, Iterable
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

from processor import SUPPORTED_EXTENSIONS, ExportOptions, source_dimensions

PROJECT_VERSION = 1
MAX_ITEMS = 1000
MAX_SINGLE_FILE = 300 * 1024 * 1024
MAX_TOTAL_BYTES = 3 * 1024 * 1024 * 1024
NAME_PATTERN = re.compile(r"^assets/[0-9]{5}\.(jpg|jpeg|png|webp|bmp|tif|tiff|heic|heif)$")
Progress = Callable[[int, int], None]


class ProjectError(ValueError):
    """El archivo de proyecto no es válido o supera los límites de seguridad."""


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_project(
    target: Path, paths: Iterable[Path], ordered: Iterable[Path],
    labels: dict[Path, str], pdf_origins: dict[Path, Path],
    settings: dict, progress: Progress | None = None,
    *, special_pages: dict[Path, dict] | None = None,
) -> Path:
    """Guarda todo dentro de UN archivo; no depende de rutas originales."""
    paths = list(paths)
    ordered = list(ordered)
    if not paths or len(paths) > MAX_ITEMS or len(set(paths)) != len(paths):
        raise ProjectError("El proyecto no contiene elementos válidos")
    if sorted(map(str, paths)) != sorted(map(str, ordered)):
        raise ProjectError("El orden no coincide con la biblioteca")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    from special_pages import validate_special_spec
    special_pages = special_pages or {}
    records = []
    names = {}
    total_bytes = 0
    for index, path in enumerate(paths):
        path = Path(path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS or not path.is_file():
            raise ProjectError(f"No se puede incluir: {path.name}")
        size = path.stat().st_size
        total_bytes += size
        if size > MAX_SINGLE_FILE or total_bytes > MAX_TOTAL_BYTES:
            raise ProjectError("El proyecto supera el límite de tamaño permitido")
        arcname = f"assets/{index + 1:05d}{path.suffix.lower()}"
        names[path] = index
        records.append({
            "asset": arcname,
            "label": str(labels.get(path, path.name))[:300],
            "kind": "special_page" if path in special_pages else ("pdf_page" if path in pdf_origins else "image"),
            "special": validate_special_spec(special_pages[path]) if path in special_pages else None,
            "pdf_origin": str(pdf_origins[path]) if path in pdf_origins else None,
            "size": size,
            "sha256": _digest_file(path),
        })
    manifest = {
        "format": "Revelo", "version": PROJECT_VERSION,
        "items": records,
        "order": [names[path] for path in ordered],
        "settings": settings,
    }
    tempname: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.revelo_', suffix='.tmp',
                                         dir=target.parent, delete=False) as tmp:
            tempname = tmp.name
        with ZipFile(tempname, 'w', ZIP_DEFLATED, compresslevel=3, allowZip64=True) as zipout:
            for idx, (path, record) in enumerate(zip(paths, records), 1):
                zipout.write(path, record['asset'])
                if progress:
                    progress(idx, len(paths))
            zipout.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(tempname, target)
        tempname = None
        return target
    finally:
        if tempname is not None:
            Path(tempname).unlink(missing_ok=True)


def load_project(source: Path, folder: Path, progress: Progress | None = None) -> dict:
    """Carga con validación, sin aceptar rutas del ZIP como rutas de extracción."""
    source = Path(source)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(source, 'r') as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ITEMS + 1 or not any(i.filename == 'manifest.json' for i in infos):
                raise ProjectError("Este archivo no es un proyecto de Revelo válido")
            if archive.getinfo('manifest.json').file_size > 2 * 1024 * 1024:
                raise ProjectError("El índice del proyecto es demasiado grande")
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('format') != 'Revelo' or manifest.get('version') != PROJECT_VERSION:
                raise ProjectError("Versión de proyecto desconocida")
            records = manifest.get('items')
            indices = manifest.get('order')
            settings = manifest.get('settings')
            if (not isinstance(records, list) or not 0 < len(records) <= MAX_ITEMS
                    or not isinstance(indices, list) or len(indices) != len(records)
                    or sorted(indices) != list(range(len(records)))
                    or not isinstance(settings, dict)):
                raise ProjectError("El índice del proyecto contiene datos no válidos")
            entries = {info.filename: info for info in infos}
            if len(entries) != len(infos) or len(infos) != len(records) + 1:
                raise ProjectError("El proyecto tiene archivos duplicados o inesperados")
            total = 0
            loaded = []
            labels = {}
            pdf_origins = {}
            special_pages = {}
            from special_pages import validate_special_spec
            for idx, record in enumerate(records, 1):
                if not isinstance(record, dict):
                    raise ProjectError("Elemento del proyecto no válido")
                arcname = record.get('asset')
                if (not isinstance(arcname, str) or not NAME_PATTERN.fullmatch(arcname)
                        or arcname not in entries or entries[arcname].is_dir()):
                    raise ProjectError("Ruta de imagen no válida dentro del proyecto")
                info = entries[arcname]
                total += info.file_size
                if (info.file_size > MAX_SINGLE_FILE or total > MAX_TOTAL_BYTES
                        or info.file_size != record.get('size')):
                    raise ProjectError("El tamaño de alguna imagen no coincide")
                kind = record.get('kind')
                if kind not in ('image', 'pdf_page', 'special_page'):
                    raise ProjectError("Tipo de elemento desconocido")
                label = record.get('label')
                if not isinstance(label, str) or len(label) > 300:
                    raise ProjectError("Nombre de imagen inválido")
                expected = record.get('sha256')
                if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                    raise ProjectError("Huella de imagen no válida")
                path = folder / f"{idx:05d}{Path(arcname).suffix}"
                hasher = hashlib.sha256()
                with archive.open(info) as inp, path.open('wb') as out:
                    while True:
                        chunk = inp.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        hasher.update(chunk)
                if hasher.hexdigest() != expected:
                    raise ProjectError(f"La imagen {idx} está dañada")
                try:
                    source_dimensions(path)  # verifica la imagen antes de usarla
                except Exception as exc:
                    raise ProjectError(f"No se puede abrir la imagen {idx}") from exc
                loaded.append(path)
                labels[path] = label
                if kind == 'special_page':
                    try:
                        special_pages[path] = validate_special_spec(record.get('special'))
                    except ValueError as exc:
                        raise ProjectError('Página especial del proyecto no válida') from exc
                if kind == 'pdf_page':
                    origin = record.get('pdf_origin')
                    if not isinstance(origin, str) or len(origin) > 1024:
                        raise ProjectError("Origen PDF inválido")
                    pdf_origins[path] = Path(origin)
                if progress:
                    progress(idx, len(records))
            # valida ajustes antes de alterar el estado de la aplicación
            try:
                ExportOptions(
                    paper=settings['paper'], orientation=settings['orientation'],
                    fit=settings['fit'], dpi=int(settings['dpi']),
                    fmt=settings['fmt'], binding=settings['binding'],
                    photos_per_page=int(settings['photos_per_page']),
                ).validate()
            except (KeyError, TypeError, ValueError) as exc:
                raise ProjectError("Los ajustes guardados no son compatibles") from exc
            return {
                "paths": loaded,
                "pages": [loaded[i] for i in indices],
                "labels": labels,
                "pdf_origins": pdf_origins,
                "special_pages": special_pages,
                "settings": settings,
            }
    except (BadZipFile, OSError, json.JSONDecodeError, KeyError) as exc:
        raise ProjectError(f"No se puede abrir el proyecto: {exc}") from exc
