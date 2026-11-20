"""Regresiones del editor de portadas y corrección automática v1.6.1."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

from photo_edits import DEFAULT, validate_edits, apply_edits, automatic_photo_correction
from special_pages import validate_special_spec, render_special_page, save_special_thumbnail
from project_io import save_project, load_project
from pdf_sources import recover_sources
from processor import ExportOptions, export_pdf


def test_auto_correction_is_reversible_and_rejects_invalid_payload(tmp_path):
    photo = tmp_path / 'sin_corregir.png'
    image = Image.new('RGB', (400, 250))
    draw = ImageDraw.Draw(image)
    for row in range(250):
        value = 50 + round(row * 125 / 250)
        draw.line((0, row, 399, row), fill=(value, round(value*.65), round(value*.45)))
    image.save(photo)
    untouched = photo.read_bytes()
    original = Image.open(photo).convert('RGB')
    edited = apply_edits(original, dict(DEFAULT, auto_correct=True))
    assert edited.size == original.size
    assert ImageChops.difference(original, edited).getbbox() is not None
    assert photo.read_bytes() == untouched
    assert validate_edits({'auto_correct': True})['auto_correct'] is True
    with pytest.raises(ValueError):
        validate_edits({'auto_correct': 'on'})
    edited.close(); original.close(); image.close()


def test_special_background_edits_are_preserved_in_portable_files(tmp_path):
    source = tmp_path / 'fondo.jpg'
    Image.new('RGB', (820, 530), (100, 72, 45)).save(source)
    spec = validate_special_spec({
        'kind': 'Portada', 'theme': 'Personalizar', 'title': 'RECETAS',
        'background_type': 'imagen', 'background_image': str(source),
        'background_color': '#F6EBDC',
        'image_mode': 'Encajar', 'background_edits': {'turns': 1, 'auto_correct': True, 'brightness': 1.1},
    })
    assert spec['background_edits']['auto_correct'] is True
    with pytest.raises(ValueError):
        validate_special_spec(dict(spec, background_edits={'bad_parameter': 13}))
    a = render_special_page(spec, (640, 900))
    b = render_special_page(dict(spec, background_edits=dict(DEFAULT)), (640, 900))
    assert ImageChops.difference(a, b).getbbox() is not None
    a.close(); b.close()
    cover = tmp_path / 'cover.png'
    save_special_thumbnail(cover, spec)
    settings = {'paper': 'A5', 'orientation': 'Vertical', 'fit': 'Ajustar (sin recortar)',
                'dpi': 100, 'fmt': 'PDF', 'binding': False, 'photos_per_page': 1}
    project = tmp_path / 'Album.revelo'
    output_pdf = tmp_path / 'Album.pdf'
    save_project(project, [cover], [cover], {cover: 'Portada'}, {}, settings,
                 special_pages={cover: spec})
    export_pdf([cover], ExportOptions(**settings, special_pages={cover: spec}), output_pdf)
    source.unlink(); cover.unlink()
    loaded = load_project(project, tmp_path / 'restored')
    restored = next(iter(loaded['special_pages'].values()))
    assert restored['background_edits']['auto_correct'] is True
    assert restored['background_edits']['turns'] == 1
    assert Path(restored['background_image']).exists()
    paths, _, _, specials = recover_sources(output_pdf, tmp_path / 'from_pdf', include_specials=True)
    assert len(paths) == 1
    assert specials[paths[0]]['background_edits']['auto_correct'] is True


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere interfaz gráfica')
def test_editor_photo_button_states_orientation_and_file_drop(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from custom_editor import edit_custom_page
    root = tk.Tk()
    root.geometry('1250x820+0+0')
    orientation = tk.StringVar(master=root, value='Vertical')
    photo = tmp_path / 'Foto de prueba.png'
    Image.new('RGB', (600, 350), '#36587C').save(photo)
    saved = []
    initial = {'kind': 'Portada', 'theme': 'Personalizar', 'title': 'MI ALBUM',
               'background_type': 'color', 'background_color': '#F6EBDC'}
    try:
        def settings():
            return ((297, 210) if orientation.get() == 'Horizontal' else (210, 297), False)
        win = edit_custom_page(root, initial=initial, image_dir=tmp_path/'temp',
                               landscape=False, binding=False, on_save=saved.append,
                               page_settings=settings, orientation_var=orientation,
                               settings_vars=(orientation,))
        root.update()
        def all_widgets(widget):
            for w in widget.winfo_children():
                yield w
                yield from all_widgets(w)
        photo_btn = next(w for w in all_widgets(win)
                         if isinstance(w, tk.Button) and w.cget('text') == 'Elegir foto…')
        edit_btn = next(w for w in all_widgets(win)
                        if isinstance(w, tk.Button) and w.cget('text') == 'Editar foto ✎')
        assert photo_btn.cget('state') == 'disabled'
        assert edit_btn.cget('state') == 'disabled'
        orient_combo = next(w for w in all_widgets(win) if isinstance(w, ttk.Combobox)
                            and tuple(w.cget('values')) == ('Automática', 'Vertical', 'Horizontal'))
        orient_combo.set('Horizontal')
        root.update()
        assert orientation.get() == 'Horizontal'
        assert win.revelo_page_mm == (297, 210)
        # TkDND entrega una cadena TCL entre llaves si el nombre contiene espacios.
        assert win.revelo_drop_image('{' + str(photo) + '}') is True
        root.update()
        assert photo_btn.cget('state') == 'normal'
        assert edit_btn.cget('state') == 'normal'
        edit_btn.invoke()
        root.update()
        child = next(w for w in win.winfo_children() if isinstance(w, tk.Toplevel))
        button = next(w for w in all_widgets(child)
                      if isinstance(w, tk.Button) and w.cget('text') == 'Corrección automática')
        button.invoke(); root.update()
        save_edit = next(w for w in all_widgets(child)
                         if isinstance(w, tk.Button) and w.cget('text') == 'Guardar edición')
        save_edit.invoke(); root.update()
        save_page = next(w for w in all_widgets(win)
                         if isinstance(w, tk.Button) and w.cget('text') == 'Guardar página personalizada')
        save_page.invoke(); root.update()
        assert saved and saved[0]['background_edits']['auto_correct'] is True
        assert saved[0]['background_type'] == 'imagen'
    finally:
        for child in root.winfo_children():
            child.destroy()
        root.destroy()
