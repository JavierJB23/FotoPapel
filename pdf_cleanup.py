"""Detección conservadora de fondos desenfocados en PDFs antiguos de Revelo.

En los PDFs antiguos no se conserva la fuente original. Este análisis busca
una fotografía nítida centrada rodeada de franjas desenfocadas y solo recorta
cuando las dos franjas opuestas pueden identificarse con alta confianza.
"""
from __future__ import annotations

import math
from statistics import median
from PIL import Image, ImageChops, ImageFilter


def _paired_edge(scores: list[float], *, threshold_ratio: float = .33):
    n = len(scores)
    if n < 80:
        return None
    middle = median(scores[int(n * .28):int(n * .72)])
    left_bg = median(scores[:max(5, int(n * .035))])
    right_bg = median(scores[-max(5, int(n * .035)):])
    # Para separar nitidez real de fondo borroso necesitamos diferencia clara.
    if middle < 3.5 or max(left_bg, right_bg) > middle * threshold_ratio:
        return None
    threshold = max(2.0, middle * .35, max(left_bg, right_bg) * 2.8)
    if threshold >= middle * .78:
        return None
    window = max(5, round(n * .014))
    minimum = max(7, round(n * .04))
    max_margin = int(n * .30)

    def scan(reverse: bool = False):
        seq = scores[::-1] if reverse else scores
        for at in range(minimum, max_margin):
            forward = seq[at:at + window]
            backward = seq[at - window:at]
            if (len(forward) == window and len(backward) == window
                    and median(forward) > threshold
                    and median(backward) < threshold * .85):
                return at
        return None

    left = scan()
    right = scan(True)
    if left is None or right is None or left + right > n * .46:
        return None
    return left, n - right


def detect_blurred_background(source: Image.Image):
    """Return (imagen_sin_fondo, detectado) o una copia íntegra si hay dudas."""
    if min(source.size) < 240:
        return source.copy(), False
    scale = min(1.0, 680 / max(source.size))
    w = max(1, round(source.width * scale))
    h = max(1, round(source.height * scale))
    gray = source.convert("L")
    try:
        if gray.size != (w, h):
            thumb = gray.resize((w, h), Image.Resampling.BILINEAR)
        else:
            thumb = gray.copy()
    finally:
        gray.close()
    try:
        softened = thumb.filter(ImageFilter.GaussianBlur(1.5))
        high = ImageChops.difference(thumb, softened)
        softened.close()
        try:
            raw = high.tobytes()
            row_x0, row_x1 = round(w*.20), round(w*.80)
            col_y0, col_y1 = round(h*.20), round(h*.80)
            row_scores = [sum(raw[y*w+row_x0:y*w+row_x1]) / (row_x1-row_x0)
                          for y in range(h)]
            col_scores = [sum(raw[y*w+x] for y in range(col_y0, col_y1)) / (col_y1-col_y0)
                          for x in range(w)]
            vertical = _paired_edge(row_scores)
            horizontal = _paired_edge(col_scores)
            if vertical is None and horizontal is None:
                return source.copy(), False
            left, right = horizontal if horizontal else (0, w)
            top, bottom = vertical if vertical else (0, h)
            if (right - left) < w*.48 or (bottom - top) < h*.48:
                return source.copy(), False
            box = (max(0, math.floor(left * source.width / w)),
                   max(0, math.floor(top * source.height / h)),
                   min(source.width, math.ceil(right * source.width / w)),
                   min(source.height, math.ceil(bottom * source.height / h)))
            return source.crop(box), True
        finally:
            high.close()
    finally:
        thumb.close()
