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


def click_move(paths: list[Path], selected: Path | None, clicked: Path,
               special_pages: dict[Path, dict]) -> tuple[list[Path], Path | None, bool]:
    """Dos clics: primero origen, después destino; la portada permanece fija.

    Retorna (nuevo_orden, siguiente_origen, se_ha_movido). Un clic sobre el
    mismo elemento deselecciona. Hacer clic en una portada sin origen no la
    selecciona, ya que no puede moverse.
    """
    pages = anchored_order(paths, special_pages)
    if clicked not in pages:
        return pages, selected, False
    cover = cover_path(special_pages)
    if selected not in pages:
        return pages, None if clicked == cover else clicked, False
    if selected == clicked:
        return pages, None, False
    if selected == cover:
        return pages, None if clicked == cover else clicked, False
    moved = move_item(pages, selected, pages.index(clicked), special_pages)
    return moved, None, moved != pages
