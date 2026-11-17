"""Importa páginas PDF como imágenes temporales para reorganizarlas en Revelo.

La importación es completamente local. Cada página se rasteriza a 300 PPP,
conservando el contenido visible pero no su estructura de texto editable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from processor import PAPER_SIZES

IMPORT_DPI = 300
MAX_PDF_PAGES = 500


def matched_paper(page_sizes: list[tuple[float, float]]) -> tuple[str | None, bool]:
    """Devuelve tamaño comercial si la primera página coincide (±2 mm).

    `mixed` indica páginas con medidas diferentes, independientemente de la orientación.
    """
    if not page_sizes:
        return None, False
    first_w, first_h = page_sizes[0]
    ordered = sorted((first_w, first_h))
    paper = next((name for name, dims in PAPER_SIZES.items()
                  if all(abs(a - b) <= 2.0 for a, b in zip(ordered, sorted(dims)))), None)
    mixed = any(any(abs(a - b) > 2.0 for a, b in zip(ordered, sorted(other)))
                for other in page_sizes[1:])
    return paper, mixed


def import_pdf_pages(
    source: Path,
    folder: Path,
    *,
    dpi: int = IMPORT_DPI,
    progress: Callable[[int, int, str], None] | None = None,
) -> tuple[list[Path], list[tuple[float, float]]]:
    """Convierte cada página a PNG sin alterar nunca el PDF original.

    Los archivos producidos son solo temporales; el llamador se encarga de
    mantener vivo y limpiar su directorio de trabajo.
    """
    import pypdfium2 as pdfium

    source = Path(source)
    folder.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    sizes: list[tuple[float, float]] = []
    pdf = None
    try:
        try:
            pdf = pdfium.PdfDocument(str(source))
        except Exception as exc:
            raise ValueError(f"No se puede abrir «{source.name}». Si tiene contraseña o está dañado, no puede importarse.") from exc
        total = len(pdf)
        if total == 0:
            raise ValueError(f"El PDF «{source.name}» no tiene páginas")
        if total > MAX_PDF_PAGES:
            raise ValueError(f"«{source.name}» tiene {total} páginas (máximo {MAX_PDF_PAGES} por PDF)")
        for index in range(total):
            page = pdf[index]
            try:
                w_pt, h_pt = page.get_size()
                sizes.append((w_pt * 25.4 / 72, h_pt * 25.4 / 72))
                # PNG sin pérdida: protege letras, ilustraciones y fotografías.
                bitmap = page.render(scale=dpi / 72, rotation=0)
                try:
                    image = bitmap.to_pil().convert("RGB")
                    try:
                        target = folder / f"pagina_{index + 1:04d}.png"
                        image.save(target, "PNG")
                    finally:
                        image.close()
                finally:
                    bitmap.close()
                created.append(target)
                if progress:
                    progress(index + 1, total, source.name)
            finally:
                page.close()
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    finally:
        if pdf is not None:
            pdf.close()
    return created, sizes
