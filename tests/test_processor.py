from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image

from processor import ExportOptions, PAPER_SIZES, dimensions_mm, export_images, export_pdf, export_word, pixel_size, render_print_image


def make_images(tmp_path):
    p = tmp_path / 'horizontal.jpg'
    q = tmp_path / 'vertical.png'
    Image.new('RGB', (800, 400), 'red').save(p)
    Image.new('RGB', (400, 800), 'blue').save(q)
    return [p, q]


def test_paper_dimensions():
    assert PAPER_SIZES['A4'] == (210, 297)
    assert pixel_size(210, 297, 300) == (2480, 3508)
    assert pixel_size(100, 150, 300) == (1181, 1772)


def test_auto_orientation(tmp_path):
    horizontal, vertical = make_images(tmp_path)
    opts = ExportOptions(paper='A4', orientation='Automática')
    assert dimensions_mm(horizontal, opts) == (297, 210)
    assert dimensions_mm(vertical, opts) == (210, 297)


def test_fit_modes(tmp_path):
    p, _ = make_images(tmp_path)
    opts = ExportOptions(paper='10 × 15 cm', orientation='Vertical', dpi=150, fit='Ajustar (sin recortar)')
    img, dims, low = render_print_image(p, opts)
    assert img.size == pixel_size(100, 150, 150)
    assert img.getpixel((img.width // 2, 0)) == (255, 255, 255)
    assert img.getpixel((img.width // 2, img.height // 2))[0] > 200
    img.close()
    filled_opts = ExportOptions(**{**opts.__dict__, 'fit':'Rellenar (recortar)'})
    filled, _, _ = render_print_image(p, filled_opts)
    assert filled.getpixel((filled.width // 2, 0))[0] > 200
    filled.close()


def test_image_batch_preserves_extensions_and_numbering(tmp_path):
    paths = make_images(tmp_path)
    out, _ = export_images(paths, ExportOptions(paper='A6', dpi=150, fmt='Imagenes'), tmp_path)
    names = sorted(p.name for p in out.iterdir())
    assert len(names) == 2
    assert names[0].startswith('01_') and names[0].endswith('.jpg')
    assert names[1].startswith('02_') and names[1].endswith('.png')
    with Image.open(out / names[0]) as im:
        assert im.info['dpi'] == (150, 150)


def test_pdf_and_word(tmp_path):
    paths = make_images(tmp_path)
    opts = ExportOptions(paper='A5', dpi=150)
    pdf, _ = export_pdf(paths, opts, tmp_path / 'result.pdf')
    word, _ = export_word(paths, opts, tmp_path / 'result.docx')
    assert pdf.stat().st_size > 1000 and word.stat().st_size > 1000
    with ZipFile(word) as z:
        assert len([n for n in z.namelist() if n.startswith('word/media/')]) == 2
    try:
        import fitz
    except ImportError:
        return
    document = fitz.open(pdf)
    assert len(document) == 2
    assert document[0].rect.width > document[0].rect.height
    assert document[1].rect.width < document[1].rect.height
