"""Ajuste magnético de posiciones para el editor de portadas de Revelo.

Lógica geométrica sin dependencias gráficas: puntos de anclaje en centro y
bordes, con histéresis en píxeles para que no se despeguen accidentalmente.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Guide:
    position: float  # coordenada normalizada de la línea que se dibuja
    value: float     # posición normalizada del centro del elemento
    name: str


def guides_for_axis(*, extent: float = 0.0) -> tuple[Guide, ...]:
    """Centros y bordes, teniendo en cuenta el tamaño del objeto (0..1).

    Un texto anclado a su centro (extent=0) se mantiene dentro de la zona
    segura por su renderizador. Para una foto, extent permite alinear sus bordes.
    """
    result = [Guide(0.5, 0.5, 'centro')]
    if 0 < extent < 1:
        result += [Guide(0.0, extent / 2, 'inicio'), Guide(1.0, 1 - extent / 2, 'fin')]
    elif extent == 0:
        result += [Guide(0.0, 0.0, 'inicio'), Guide(1.0, 1.0, 'fin')]
    return tuple(result)


def magnetic_axis(value: float, dimension_px: int, guides: tuple[Guide, ...],
                  previous: Guide | None = None, *, enter_px: float = 9,
                  release_px: float = 22) -> tuple[float, Guide | None]:
    """Retiene un anclaje hasta alejar el ratón más de ``release_px``.

    Devuelve la nueva posición *del centro del objeto* y la guía activa.
    Es la resistencia de Word, sin saltos ni temporizadores.
    """
    value = max(0.0, min(1.0, value))
    if previous is not None and abs(value - previous.value) * dimension_px <= release_px:
        return previous.value, previous
    nearest = min(guides, key=lambda item: abs(value - item.value), default=None)
    if nearest is not None and abs(value - nearest.value) * dimension_px <= enter_px:
        return nearest.value, nearest
    return value, None
