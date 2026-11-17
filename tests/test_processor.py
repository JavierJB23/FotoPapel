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


def test_intelligent_fit_keeps_entire_image_and_fills_edges(tmp_path):
    from PIL import ImageDraw
    photo = tmp_path / 'marcadores.png'
    src = Image.new('RGB', (1200, 750), (25, 55, 80))
    draw = ImageDraw.Draw(src)
    draw.rectangle((0, 0, 30, 749), fill=(250, 5, 5))
    draw.rectangle((1170, 0, 1199, 749), fill=(5, 250, 5))
    src.save(photo)
    opts = ExportOptions(fit='Ajuste inteligente (máx. 5 %)', dpi=150)
    result, _, _ = render_print_image(photo, opts, preview_max_size=(960, 740))
    assert result.size == (960, 679)
    # Se conserva el extremo izquierdo y derecho en la imagen central.
    assert result.getpixel((2, result.height // 2))[0] > 200
    assert result.getpixel((result.width - 3, result.height // 2))[1] > 200
    # Los márgenes superiores no son blancos.
    assert result.getpixel((result.width // 2, 1)) != (255, 255, 255)
    result.close()


def test_extended_background_original_remains_visible(tmp_path):
    from PIL import ImageDraw
    photo = tmp_path / 'colores.png'
    original = Image.new('RGB', (600, 300), (25, 55, 80))
    draw = ImageDraw.Draw(original)
    draw.rectangle((0, 30, 50, 270), fill=(250, 5, 5))
    draw.rectangle((550, 30, 599, 270), fill=(5, 250, 5))
    original.save(photo)
    opts = ExportOptions(fit='Ampliar fondo (sin recortar)', dpi=150)
    result, _, _ = render_print_image(photo, opts, preview_max_size=(800, 700))
    assert result.getpixel((20, result.height // 2))[0] > 200
    assert result.getpixel((result.width - 20, result.height // 2))[1] > 200
    assert result.getpixel((result.width // 2, 2)) != (255, 255, 255)
    result.close()


def test_preview_and_export_physical_dimensions_and_new_modes(tmp_path):
    photo, _ = make_images(tmp_path)
    from PIL import Image
    for fit in ('Ajuste inteligente (máx. 5 %)', 'Ampliar fondo (sin recortar)'):
        opts = ExportOptions(paper='A4', fit=fit, dpi=150)
        preview, measure, warning = render_print_image(photo, opts, preview_max_size=(800, 800))
        final, measure2, warning2 = render_print_image(photo, opts)
        assert preview.width <= 800 and preview.height <= 800
        assert final.size == pixel_size(*measure, opts.dpi)
        assert measure == measure2
        assert warning == warning2
        preview.close()
        final.close()


def test_binding_margins_alternate_and_apply_to_every_fit(tmp_path):
    from processor import printable_box
    pic, _ = make_images(tmp_path)
    opts = ExportOptions(paper="A5", orientation="Horizontal", dpi=150,
                         binding=True, fit="Rellenar (recortar)")
    left, size, _ = render_print_image(pic, opts, page_index=0)
    right, _, _ = render_print_image(pic, opts, page_index=1)
    assert left.size == right.size == pixel_size(210, 148, 150)
    assert left.getpixel((0, left.height // 2)) == (255, 255, 255)
    assert right.getpixel((right.width - 1, right.height // 2)) == (255, 255, 255)
    assert left.getpixel((left.width // 2, left.height // 2))[0] > 200
    a = printable_box(left.size, size, binding=True, page_index=0)
    b = printable_box(left.size, size, binding=True, page_index=1)
    assert a[0] > b[0]  # más margen a la izquierda en la primera página
    assert a[2] > b[2]  # más margen a la derecha en la segunda página
    assert left.getpixel((a[0] + 5, left.height // 2))[0] > 200
    assert right.getpixel((b[2] - 5, right.height // 2))[0] > 200
    left.close()
    right.close()


def test_binding_preview_matches_final(tmp_path):
    pic, _ = make_images(tmp_path)
    opts = ExportOptions(paper="A5", orientation="Horizontal", dpi=150, binding=True,
                         fit="Ampliar fondo (sin recortar)")
    final, dims, _ = render_print_image(pic, opts, page_index=1)
    preview, _, _ = render_print_image(pic, opts, page_index=1, preview_max_size=(630, 480))
    # Con fondo ampliado, los márgenes conservan el fondo difuminado, no blanco.
    assert final.getpixel((final.width - 1, final.height // 2)) != (255, 255, 255)
    assert preview.getpixel((preview.width - 1, preview.height // 2)) != (255, 255, 255)
    assert preview.getpixel((preview.width // 2, preview.height // 2))[0] > 100
    final.close()
    preview.close()


def test_pdf_import_images_and_ordered_mix(tmp_path):
    from pdf_import import import_pdf_pages, matched_paper
    import pypdfium2 as pdfium
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.colors import red, green, blue
    inp = tmp_path / "Recetario original.pdf"
    paper_w, paper_h = 148 * 72/25.4, 210 * 72/25.4
    pdf = Canvas(str(inp), pagesize=(paper_w, paper_h))
    for color, title in ((red, "Receta uno"), (green, "Receta dos"), (blue, "Receta tres")):
        pdf.setFillColor(color)
        pdf.rect(40, 40, 90, 130, fill=1, stroke=0)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(40, 200, title)
        pdf.showPage()
    pdf.save()
    progress = []
    imported, sizes = import_pdf_pages(inp, tmp_path / "temporal", dpi=150,
                                       progress=lambda i,n,name: progress.append((i,n,name)))
    assert len(imported) == 3
    assert [p.name for p in imported] == ["pagina_0001.png", "pagina_0002.png", "pagina_0003.png"]
    assert matched_paper(sizes) == ("A5", False)
    assert progress == [(1, 3, inp.name), (2, 3, inp.name), (3, 3, inp.name)]
    with Image.open(imported[0]) as a, Image.open(imported[1]) as b:
        assert a.getpixel((110, a.height - 120))[0] > a.getpixel((110, a.height - 120))[1]
        assert b.getpixel((110, b.height - 120))[1] > b.getpixel((110, b.height - 120))[0]
    new_img = tmp_path / 'nueva.png'
    Image.new('RGB', (380, 520), 'yellow').save(new_img)
    ordered = [imported[0], new_img, imported[1], imported[2]]
    output, warning_count = export_pdf(
        ordered,
        ExportOptions(paper='A5', dpi=150, binding=True, fit='Ajustar (sin recortar)'),
        tmp_path / 'Recetario actualizado.pdf',
    )
    check = pdfium.PdfDocument(str(output))
    try:
        assert len(check) == 4
        assert abs(check[0].get_size()[0] - paper_w) < 0.6
        assert abs(check[0].get_size()[1] - paper_h) < 0.6
    finally:
        check.close()
    assert inp.exists() and inp.stat().st_size > 0


def test_mixed_pdf_page_sizes_detected(tmp_path):
    from pdf_import import matched_paper
    assert matched_paper([(210, 297), (297, 210)]) == ("A4", False)
    assert matched_paper([(148, 210), (210, 297)]) == ("A5", True)
    assert matched_paper([(132, 192)]) == (None, False)


def test_binding_in_word_and_pdf_image(tmp_path):
    import pypdfium2 as pdfium
    paths = make_images(tmp_path)
    opts = ExportOptions(paper='A5', orientation='Vertical', dpi=150, binding=True,
                         fit='Rellenar (recortar)')
    pdf_path, _ = export_pdf(paths, opts, tmp_path / 'margenes.pdf')
    word_path, _ = export_word(paths, opts, tmp_path / 'margenes.docx')
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        a = pdf[0].render(scale=1).to_pil()
        b = pdf[1].render(scale=1).to_pil()
        assert sum(a.getpixel((5, a.height//2))[:3]) > 700
        assert sum(b.getpixel((b.width-5, b.height//2))[:3]) > 700
    finally:
        pdf.close()
    with ZipFile(word_path) as z:
        content = z.read('word/document.xml')
        assert b'wp:anchor' in content
        media = [n for n in z.namelist() if n.startswith('word/media/')]
        assert len(media) == 2
        from io import BytesIO
        im = Image.open(BytesIO(z.read(media[0])))
        assert sum(im.getpixel((5, im.height//2))[:3]) > 700


def test_binding_extended_background_covers_whole_page_but_foreground_safe(tmp_path):
    from processor import printable_box
    from PIL import ImageDraw

    source = tmp_path / "paisaje.png"
    picture = Image.new("RGB", (1200, 600), (15, 48, 75))
    draw = ImageDraw.Draw(picture)
    draw.rectangle((0, 0, 28, 599), fill=(248, 12, 8))
    draw.rectangle((1172, 0, 1199, 599), fill=(14, 240, 18))
    picture.save(source)
    picture.close()
    settings = ExportOptions(paper="A5", orientation="Horizontal", dpi=150,
                             fit="Ampliar fondo (sin recortar)", binding=True)
    for page_index in (0, 1):
        rendered, dims, _ = render_print_image(source, settings, page_index=page_index)
        safe = printable_box(rendered.size, dims, binding=True, page_index=page_index)
        # Las cuatro esquinas pertenecen al fondo ampliado, no a bandas blancas.
        for point in ((0, 0), (rendered.width-1, 0),
                      (0, rendered.height-1), (rendered.width-1, rendered.height-1)):
            assert rendered.getpixel(point) != (255, 255, 255)
        # Las marcas originales continúan dentro de la caja de seguridad.
        safe_w, safe_h = safe[2]-safe[0], safe[3]-safe[1]
        in_w = safe_w
        in_h = round(600 * in_w / 1200)
        center_y = safe[1] + safe_h // 2
        assert rendered.getpixel((safe[0] + 4, center_y))[0] > 220
        assert rendered.getpixel((safe[2] - 5, center_y))[1] > 210
        rendered.close()


def test_pdf_import_does_not_add_second_frame(tmp_path):
    import pypdfium2 as pdfium
    from pdf_import import import_pdf_pages
    from PIL import ImageChops, ImageStat

    photo = tmp_path / "scene.png"
    Image.new("RGB", (900, 560), (38, 93, 140)).save(photo)
    base_opts = ExportOptions(paper="A5", orientation="Horizontal", dpi=150,
                              fit="Ampliar fondo (sin recortar)", binding=True)
    original_pdf = tmp_path / "recetario_original.pdf"
    export_pdf([photo], base_opts, original_pdf)
    imported, _ = import_pdf_pages(original_pdf, tmp_path / "temp", dpi=150)
    assert len(imported) == 1
    original_page = imported[0]

    # El nuevo documento reescala la página PDF como un todo, sin crear otro fondo.
    mix_opts = ExportOptions(**{**base_opts.__dict__, "pdf_page_paths": frozenset({original_page})})
    reconstructed, _, _ = render_print_image(original_page, mix_opts, page_index=0)
    with Image.open(original_page) as src:
        before = src.convert("RGB").resize(reconstructed.size, Image.Resampling.LANCZOS)
        difference = ImageStat.Stat(ImageChops.difference(before, reconstructed)).mean
        assert max(difference) < 2.0  # sin segunda maqueta: casi igualdad de píxeles
        before.close()
    reconstructed.close()

    # La página PDF sigue siendo una página ya compuesta aunque cambie de orden.
    for index in (0, 1):
        converted, _, _ = render_print_image(original_page, mix_opts, page_index=index)
        assert converted.getpixel((2, converted.height//2)) != (255, 255, 255)
        converted.close()

    # En el documento mixto, la foto nueva sí recibe el encaje y la reserva.
    revised_pdf = tmp_path / "recetario_ampliado.pdf"
    export_pdf([original_page, photo], mix_opts, revised_pdf)
    pdf = pdfium.PdfDocument(str(revised_pdf))
    try:
        assert len(pdf) == 2
        assert pdf[0].get_size() == pdf[1].get_size()
    finally:
        pdf.close()


def test_existing_imported_pdf_can_be_reflowed_with_new_background(tmp_path):
    from PIL import ImageDraw
    from pdf_import import import_pdf_pages

    p = tmp_path / 'original.png'
    scene = Image.new('RGB', (600, 840), 'white')
    draw = ImageDraw.Draw(scene)
    draw.rectangle((55, 65, 545, 775), fill=(34, 71, 101))
    scene.save(p)
    source_opts = ExportOptions(paper='A5', orientation='Vertical', dpi=150,
                                fit='Ajustar (sin recortar)')
    pdf_path = tmp_path / 'old.pdf'
    export_pdf([p], source_opts, pdf_path)
    imported, _ = import_pdf_pages(pdf_path, tmp_path / 'pages', dpi=150)
    opts = ExportOptions(paper='A5', orientation='Vertical', dpi=150,
                         binding=True, fit='Ampliar fondo (sin recortar)',
                         pdf_page_paths=frozenset(imported))
    page, _, _ = render_print_image(imported[0], opts)
    # El viejo borde blanco del PDF desaparece y se rehace la maquetación.
    assert page.getpixel((0, page.height // 2)) != (255, 255, 255)
    # El contenido útil sigue visible en la zona central.
    center = page.getpixel((page.width // 2, page.height // 2))
    assert center[2] > center[0] and center[2] > center[1]
    page.close()
