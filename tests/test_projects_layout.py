"""Revelo v1.4: proyectos portables y composición múltiple por hoja."""
from pathlib import Path
from zipfile import ZipFile
import json
import math

import pytest
from PIL import Image, ImageDraw

from processor import (ExportOptions, render_layout_page, page_groups, export_pdf,
                       export_word, export_images, printable_box, pixel_size)
from project_io import save_project, load_project, ProjectError


def make_pictures(folder: Path, count=10) -> list[Path]:
    result = []
    for i in range(count):
        pic = Image.new('RGB', (800, 500) if i % 2 == 0 else (500, 800),
                        (20+i*16, 60+i*12, 120))
        ImageDraw.Draw(pic).rectangle((20, 20, 160, 160), fill=(240, 30, 30))
        path = folder / f"foto_{i:02}.png"
        pic.save(path)
        result.append(path)
    return result


@pytest.mark.parametrize('per_sheet,expected_pages', [(1,10),(2,5),(4,3),(6,2),(9,2)])
def test_layout_grouping_pdf_word(tmp_path, per_sheet, expected_pages):
    import pypdfium2
    pics = make_pictures(tmp_path)
    opts = ExportOptions(paper='A5', orientation='Vertical', dpi=100,
                         fmt='PDF', photos_per_page=per_sheet, binding=True,
                         fit='Ampliar fondo (sin recortar)')
    groups = page_groups(pics, per_sheet)
    assert len(groups) == expected_pages
    preview, dims, low = render_layout_page(groups[0], opts,
                                             preview_max_size=(520, 520))
    final, dims2, low2 = render_layout_page(groups[0], opts)
    assert dims == dims2 == (148, 210)
    assert final.size == pixel_size(148, 210, 100)
    assert preview.width <= 520 and preview.height <= 520
    assert low == low2
    preview.close(); final.close()
    result, _ = export_pdf(pics, opts, tmp_path / 'out.pdf')
    pdf = pypdfium2.PdfDocument(str(result))
    try:
        assert len(pdf) == expected_pages
    finally:
        pdf.close()
    docx, _ = export_word(pics, opts, tmp_path / 'out.docx')
    with ZipFile(docx) as z:
        assert len([n for n in z.namelist() if n.startswith('word/media/')]) == expected_pages


def test_layout_images_export_png_and_original_one_per_page(tmp_path):
    paths = make_pictures(tmp_path, 5)
    opts = ExportOptions(paper='A5', dpi=100, fmt='Imagenes', photos_per_page=4)
    folder, _ = export_images(paths, opts, tmp_path)
    images = list(folder.glob('*.png'))
    assert len(images) == 2
    with Image.open(images[0]) as page:
        assert page.size == pixel_size(210,148,100)  # auto orientation of first image
    opts1 = ExportOptions(paper='A5', dpi=100, fmt='Imagenes', photos_per_page=1)
    folder1, _ = export_images(paths, opts1, tmp_path)
    assert len(list(folder1.glob('*.png'))) == 5


def test_layout_binding_alternates_on_sheets_not_photos(tmp_path):
    paths = make_pictures(tmp_path, 8)
    opts = ExportOptions(paper='A5', orientation='Vertical', dpi=100,
                         photos_per_page=4, binding=True, fit='Rellenar (recortar)')
    first, dims, _ = render_layout_page(paths[:4], opts, page_index=0)
    second, _, _ = render_layout_page(paths[4:], opts, page_index=1)
    a = printable_box(first.size, dims, binding=True, page_index=0)
    b = printable_box(second.size, dims, binding=True, page_index=1)
    assert a[0] > b[0]
    assert first.getpixel((5, first.height//2)) == (255,255,255)
    assert second.getpixel((second.width-5, second.height//2)) == (255,255,255)
    first.close(); second.close()


def test_project_portable_roundtrip_delete_original_and_export(tmp_path):
    from pypdfium2 import PdfDocument
    source_dir = tmp_path / 'originales'
    source_dir.mkdir()
    paths = make_pictures(source_dir, 5)
    labels = {p: f'Fotografía {i}' for i, p in enumerate(paths)}
    order = [paths[2], paths[0], paths[4], paths[1], paths[3]]
    # Emula una página ya importada de PDF.
    origins = {paths[2]: tmp_path/'Recetario Antiguo.pdf'}
    settings = {'paper':'A5','orientation':'Horizontal','fit':'Ampliar fondo (sin recortar)',
                'dpi':150,'fmt':'PDF','binding':True,'photos_per_page':4}
    destination = tmp_path/'Mi recetario.revelo'
    save_project(destination, paths, order, labels, origins, settings)
    assert destination.exists()
    for p in paths:
        p.unlink()
    result = load_project(destination, tmp_path/'recuperado')
    assert [result['labels'][p] for p in result['pages']] == [labels[p] for p in order]
    assert result['settings'] == settings
    assert len(result['pdf_origins']) == 1
    assert all(p.exists() for p in result['paths'])
    opts = ExportOptions(**settings,
                         pdf_page_paths=frozenset(result['pdf_origins']))
    newpdf, _ = export_pdf(result['pages'], opts, tmp_path/'recetario nuevo.pdf')
    check = PdfDocument(str(newpdf))
    try:
        assert len(check) == 2
    finally:
        check.close()


def test_project_rejects_unexpected_entries_and_corruption(tmp_path):
    p = make_pictures(tmp_path,1)[0]
    settings = {'paper':'A4','orientation':'Automática','fit':'Ajustar (sin recortar)',
                'dpi':300,'fmt':'PDF','binding':False,'photos_per_page':1}
    file = tmp_path / 'ok.revelo'
    save_project(file,[p],[p],{}, {},settings)
    fake = tmp_path/'bad.revelo'
    with ZipFile(file) as src, ZipFile(fake,'w') as out:
        for item in src.infolist():
            out.writestr(item, src.read(item))
        out.writestr('../../evil.txt','no')
    with pytest.raises(ProjectError):
        load_project(fake, tmp_path/'unpacked')
    assert not (tmp_path/'evil.txt').exists()
    with ZipFile(file) as src, ZipFile(fake,'w') as out:
        for item in src.infolist():
            data = src.read(item)
            if item.filename.startswith('assets/'):
                data = data + b'tampered'
            out.writestr(item.filename, data)
    with pytest.raises(ProjectError):
        load_project(fake, tmp_path/'unpacked2')
