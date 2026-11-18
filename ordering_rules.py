"""Reglas puras del orden: la portada, si existe, ocupa la primera posición."""
from __future__ import annotations
from pathlib import Path


def cover_path(special_pages: dict[Path, dict], exclude: Path | None = None) -> Path | None:
    return next((path for path, spec in special_pages.items()
                 if path != exclude and spec.get('kind') == 'Portada'), None)


def anchored_order(paths: list[Path], special_pages: dict[Path, dict]) -> list[Path]:
    cover = next((path for path in paths
                  if special_pages.get(path, {}).get('kind') == 'Portada'), None)
    return [cover, *(p for p in paths if p != cover)] if cover is not None else list(paths)


def move_item(paths: list[Path], path: Path, index: int,
              special_pages: dict[Path, dict]) -> list[Path]:
    """Devuelve copia reordenada, respetando la portada anclada."""
    result = anchored_order(paths, special_pages)
    if path not in result or not 0 <= index < len(result):
        return result
    cover = cover_path(special_pages)
    if path == cover:
        return result
    if cover in result:
        index = max(1, index)
    result.remove(path)
    result.insert(index, path)
    return result
