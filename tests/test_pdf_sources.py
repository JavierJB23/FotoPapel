"""PDF reversible y recuperación conservadora de PDFs antiguos."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import hashlib

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from processor import ExportOptions, export_pdf, render_print_image
from pdf_sources import ATTACHMENT_NAME, recover_sources
from pdf_import import import_pdf_pages
from pdf_cleanup import detect_blurred_background


def sample_photo(dest: Path, *, width=1300, height=820, tone=(32, 72, 112)):
    im = Image.new("RGB", (width, height), tone)
    d = ImageDraw.Draw(im)
    for y in range(0, height, 25):
        d.line((0, y, width, min(height-1,y+15)), fill=(183, 163, (y*3)%255), width=6)
    for x in range(15, width, 95):
        d.rectangle((x, 90, x+42, 160), fill=(220, 40, 24))
    d.text((70, 350), "REVELO PDF ORIGINAL - IMAGEN NITIDA", fill="white")
    im.save(dest, "PNG")
    im.close()
    return dest


def test_pdf_embeds_and_restores_original_image_losslessly(tmp_path):
    original = sample_photo(tmp_path / 'original.png')
    opts = ExportOptions(paper='A5', orientation='Horizontal', dpi=150,
                         fit='Ampliar fondo (sin recortar)', fmt='PDF')
    pdf, _ = export_pdf([original], opts, tmp_path/'reversible.pdf')
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == 1
    assert ATTACHMENT_NAME in reader.attachments
    recovered = recover_sources(pdf, tmp_path/'restauradas')
    assert recovered is not None
    photos, sizes, grouping = recovered
    assert grouping == 1
    assert len(photos) == 1 and len(sizes) == 1
    assert photos[0].read_bytes() == original.read_bytes()
    assert photos[0].suffix == '.png'
    # A partir de la imagen recuperada ya puede cambiarse el encaje a blanco.
    white_opts = ExportOptions(paper='A5', orientation='Horizontal', dpi=150,
                               fit='Ajustar (sin recortar)', fmt='PDF')
    rendered, _, _ = render_print_image(photos[0], white_opts)
    assert rendered.getpixel((rendered.width//2, 3)) == (255, 255, 255)
    rendered.close()
    # El PDF sigue siendo perfectamente visible en lectores normales.
    with pdfium.PdfDocument(str(pdf)) as doc:
        assert len(doc) == 1
        page = doc[0]
        assert page.get_size()[0] > page.get_size()[1]
        view = page.render(scale=1).to_pil()
        assert view.getpixel((view.width//2, view.height//2)) != (255, 255, 255)


def test_pdf_multiphoto_sources_recovered_individually(tmp_path):
    photos = [sample_photo(tmp_path/f'foto{i}.png', tone=(23+i*35, 70, 125)) for i in range(5)]
    opts = ExportOptions(paper='A4', orientation='Vertical', dpi=110,
                         fit='Ampliar fondo (sin recortar)', photos_per_page=4)
    pdf, _ = export_pdf(photos, opts, tmp_path/'hojas.pdf')
    with pdfium.PdfDocument(str(pdf)) as doc:
        assert len(doc) == 2
    recovered = recover_sources(pdf, tmp_path/'restored')
    assert recovered is not None
    originals, sizes, per_sheet = recovered
    assert len(originals) == 5 and per_sheet == 4
    assert all(a.read_bytes() == b.read_bytes() for a,b in zip(originals, photos))
    assert all(round(d[0]) == 210 and round(d[1]) == 297 for d in sizes)


def test_legacy_pdf_blur_detects_sharp_center_without_attachment(tmp_path):
    original = sample_photo(tmp_path/'art.png', width=1450, height=790)
    opts = ExportOptions(paper='A5', orientation='Horizontal', dpi=180,
                         fit='Ampliar fondo (sin recortar)', fmt='PDF')
    flat, (w_mm, h_mm), _ = render_print_image(original, opts)
    # Simular PDF creado por una versión antigua, sin adjuntar originales.
    legacy = tmp_path/'viejo.pdf'
    canvas = Canvas(str(legacy), pagesize=(w_mm*72/25.4, h_mm*72/25.4))
    buf = BytesIO()
    flat.save(buf, format='JPEG', quality=94)
    canvas.drawImage(ImageReader(BytesIO(buf.getvalue())), 0, 0,
                     width=w_mm*72/25.4, height=h_mm*72/25.4)
    canvas.showPage(); canvas.save(); flat.close()
    assert recover_sources(legacy, tmp_path/'missing') is None
    imported, sizes = import_pdf_pages(legacy, tmp_path/'pages', dpi=180)
    with Image.open(imported[0]) as raster:
        result, did_detect = detect_blurred_background(raster)
        assert did_detect is True
        assert result.height < raster.height * .91
        assert result.width >= raster.width * .97
        result.close()
    white_opts = ExportOptions(paper='A5', orientation='Horizontal', dpi=150,
                                fit='Ajustar (sin recortar)',
                                pdf_page_paths=frozenset(imported))
    rendered, _, _ = render_print_image(imported[0], white_opts)
    assert rendered.getpixel((rendered.width//2, 0)) == (255, 255, 255)
    assert rendered.getpixel((rendered.width//2, rendered.height//2)) != (255, 255, 255)
    rendered.close()


def test_legacy_document_without_blurred_background_untouched(tmp_path):
    original = sample_photo(tmp_path/'without_blur.png', width=1200, height=750)
    with Image.open(original) as im:
        recovered, changed = detect_blurred_background(im)
        assert changed is False
        assert recovered.size == im.size
        recovered.close()
