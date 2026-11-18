"""Regresiones de las tipografías y las paletas en el editor personalizado."""
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image, ImageChops

from special_pages import FONT_CHOICES, THEMES, validate_special_spec, render_special_page
from project_io import save_project, load_project
from processor import ExportOptions, export_pdf
from pdf_sources import recover_sources


def spec(**changes):
    base = {
        'kind': 'Portada', 'theme': 'Personalizar',
        'background_type': 'color', 'background_color': '#F6EBDC',
        'title': 'MIS VIAJES', 'subtitle': 'Recuerdos de verano',
        'title_font': 'Georgia', 'subtitle_font': 'Georgia',
        'title_size': 12, 'subtitle_size': 6,
    }
    base.update(changes)
    return validate_special_spec(base)


def test_ten_font_choices_and_defaults():
    assert len(FONT_CHOICES) == 10
    assert len(set(FONT_CHOICES)) == len(FONT_CHOICES)
    old = spec()
    assert old['title_font'] == old['subtitle_font'] == 'Georgia'
    for name in FONT_CHOICES:
        choice = spec(title_font=name, subtitle_font=name)
        assert choice['title_font'] == name
        assert choice['subtitle_font'] == name
    with pytest.raises(ValueError):
        spec(title_font='No existe')
    with pytest.raises(ValueError):
        spec(subtitle_font='../../extra.ttf')


def test_change_font_and_size_changes_printed_pixels():
    first = render_special_page(spec(), (920, 640))
    second = render_special_page(spec(title_font='Arial',
                                      subtitle_font='Courier New'), (920, 640))
    third = render_special_page(spec(title_size=20, subtitle_size=12), (920, 640))
    try:
        assert ImageChops.difference(first, second).getbbox() is not None
        assert ImageChops.difference(first, third).getbbox() is not None
    finally:
        first.close()
        second.close()
        third.close()


def test_custom_colors_can_reuse_all_four_original_palettes():
    assert set(THEMES) == {'Blanco', 'Crema', 'Aguamarina', 'Azul noche'}
    for name, palette in THEMES.items():
        out = render_special_page(spec(title='', subtitle='',
                                       background_color=palette['background']), (600, 840))
        try:
            assert out.getpixel((0, 0)) == tuple(bytes.fromhex(palette['background'][1:]))
        finally:
            out.close()


def test_fonts_and_palette_survive_revelo_project_and_pdf(tmp_path):
    page = tmp_path / 'portada.png'
    chosen = spec(background_color=THEMES['Azul noche']['background'],
                  title_font='Impact', subtitle_font='Courier New',
                  title_size=19, subtitle_size=8)
    from special_pages import save_special_thumbnail
    save_special_thumbnail(page, chosen, landscape=True)
    settings = {'paper':'A5','orientation':'Horizontal',
                'fit':'Ajustar (sin recortar)','dpi':90, 'fmt':'PDF',
                'binding':False, 'photos_per_page':1}
    project = tmp_path / 'album.revelo'
    save_project(project, [page], [page], {page:'Portada'}, {}, settings,
                 special_pages={page:chosen})
    output_pdf = tmp_path / 'album.pdf'
    export_pdf([page], ExportOptions(**settings, special_pages={page: chosen}), output_pdf)
    page.unlink()
    recovered = load_project(project, tmp_path/'from_project')
    saved = next(iter(recovered['special_pages'].values()))
    assert (saved['title_font'], saved['subtitle_font'], saved['title_size']) == ('Impact', 'Courier New', 19)
    assert saved['background_color'] == THEMES['Azul noche']['background']
    pdf_paths, _, _, pages = recover_sources(output_pdf, tmp_path/'from_pdf', include_specials=True)
    assert len(pdf_paths) == 1
    embedded = pages[pdf_paths[0]]
    assert embedded['title_font'] == 'Impact'
    assert embedded['subtitle_font'] == 'Courier New'
    assert embedded['title_size'] == 19
    assert embedded['background_color'] == THEMES['Azul noche']['background']


@pytest.mark.skipif(not __import__('os').environ.get('DISPLAY'), reason='Necesita interfaz gráfica X11')
def test_editor_exposes_font_selectors_and_palette(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from custom_editor import edit_custom_page
    root = tk.Tk()
    root.withdraw()
    saved = []
    try:
        win = edit_custom_page(root, initial=spec(), image_dir=tmp_path,
                               landscape=True, binding=False, on_save=saved.append)
        root.update()
        def widgets(parent):
            for child in parent.winfo_children():
                yield child
                yield from widgets(child)
        combos = [w for w in widgets(win) if isinstance(w, ttk.Combobox)]
        font_selectors = [c for c in combos if tuple(c.cget('values')) == FONT_CHOICES]
        palettes = [c for c in combos if 'Azul noche' in c.cget('values')]
        assert len(font_selectors) == 2
        assert len(palettes) == 1
        palettes[0].set('Azul noche')
        palettes[0].event_generate('<<ComboboxSelected>>')
        font_selectors[0].set('Impact')
        font_selectors[1].set('Courier New')
        root.update()
        assert font_selectors[0].get() == 'Impact'
        save = next(w for w in widgets(win)
                    if isinstance(w, tk.Button) and w.cget('text') == 'Guardar página personalizada')
        save.invoke()
        assert saved and saved[0]['title_font'] == 'Impact'
        assert saved[0]['subtitle_font'] == 'Courier New'
        assert saved[0]['background_color'] == THEMES['Azul noche']['background']
    finally:
        for child in root.winfo_children():
            child.destroy()
        root.destroy()
