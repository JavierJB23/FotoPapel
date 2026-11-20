"""Regresión v1.6.2: confirmación de recorte, orientación y guías magnéticas."""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk

import pytest
from PIL import Image

from alignment_guides import Guide, guides_for_axis, magnetic_axis
from photo_edits import DEFAULT, apply_edits


def test_magnet_center_holds_until_mouse_has_moved_far_enough():
    rules = guides_for_axis()
    x, guide = magnetic_axis(.507, 900, rules)
    assert x == .5 and guide == Guide(.5, .5, 'centro')
    # La guía no deja ir el objeto con desplazamientos minúsculos.
    x2, guide2 = magnetic_axis(.518, 900, rules, guide)
    assert x2 == .5 and guide2 is guide
    x3, guide3 = magnetic_axis(.55, 900, rules, guide2)
    assert x3 == .55 and guide3 is None


def test_magnet_photo_aligns_real_edges_and_center():
    anchors = guides_for_axis(extent=.6)
    assert [(a.value, a.position) for a in anchors] == [(.5, .5), (.3, 0), (.7, 1)]
    center, guide = magnetic_axis(.306, 800, anchors)
    assert center == .3 and guide.name == 'inicio'
    other, guide2 = magnetic_axis(.695, 800, anchors)
    assert other == .7 and guide2.name == 'fin'
    assert magnetic_axis(.91, 800, guides_for_axis(extent=1.1))[1] is None


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere una ventana gráfica')
def test_crop_button_confirms_and_disables_until_selection_changes(tmp_path):
    from photo_editor_ui import PhotoEditor, CREAM
    src = tmp_path / 'photo.png'
    Image.new('RGB', (840, 500), '#12476A').save(src)
    before = src.read_bytes()
    root = tk.Tk()
    root.geometry('1200x850+0+0')
    stored = []
    win = None
    try:
        win = PhotoEditor(root, src, None, stored.append)
        root.update()
        assert win.crop_btn.cget('state') == 'disabled'
        # Simula un recorte auténtico con el ratón, no un estado inyectado.
        win._display()
        x,y,w,h = win._box_px
        assert w > 10 and h > 10
        win.canvas.event_generate('<ButtonPress-1>', x=int(x+w*.14), y=int(y+h*.14))
        win.canvas.event_generate('<B1-Motion>', x=int(x+w*.82), y=int(y+h*.83))
        win.canvas.event_generate('<ButtonRelease-1>', x=int(x+w*.82), y=int(y+h*.83))
        root.update()
        assert win.crop_btn.cget('state') == 'normal'
        win.spec['crop'] = [0.1,0.1,0.8,0.8]
        win._refresh_crop_button()
        assert win.crop_btn.cget('state') == 'normal'
        assert win.crop_btn.cget('bg').lower() == CREAM.lower()
        win.crop_btn.invoke()
        root.update()
        assert win._result is True
        assert win.result_btn.cget('text') == 'Modificar recorte'
        assert win.crop_btn.cget('state') == 'disabled'
        assert win._confirmed_crop == (0.1,0.1,0.8,0.8)
        # El recorte se ve inmediatamente pero permanece reversible.
        with Image.open(src) as original:
            rendered = apply_edits(original, win.spec)
            assert rendered.size == (588,350)
            rendered.close()
        win._toggle_result()
        assert win._result is False
        win.spec['crop'] = [0.2,0.2,0.7,0.7]
        win._refresh_crop_button()
        assert win.crop_btn.cget('state') == 'normal'
        win._clear_crop()
        assert win.crop_btn.cget('state') == 'disabled'
        win.spec['crop'] = [0.2,0.2,0.7,0.7]
        win._refresh_crop_button(); win.crop_btn.invoke()
        win.save(); root.update()
        assert stored[0]['crop'] == [0.2,0.2,0.7,0.7]
        assert src.read_bytes() == before
    finally:
        if win and win.winfo_exists():win.close()
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere una ventana gráfica')
def test_both_panels_follow_paper_orientation_with_cover_and_regular_photo(tmp_path):
    from main import ReveloApp
    from special_pages import save_special_thumbnail
    photo = tmp_path / 'scene.png'
    cover = tmp_path / 'cover.png'
    Image.new('RGB', (900, 460), '#45758D').save(photo)
    spec = {'kind': 'Portada', 'theme': 'Crema', 'title':'RECETARIO','subtitle':''}
    save_special_thumbnail(cover, spec, landscape=True)
    root = tk.Tk()
    root.geometry('1280x810+0+0')
    app = None
    try:
        app = ReveloApp(root)
        app.paths = [cover, photo]
        app.pages = [cover, photo]
        app.details = {cover:(840,600), photo:(900,460)}
        app.special_pages = {cover:spec}
        app.path_labels = {cover:'Portada',photo:'Foto'}
        app.orientation.set('Horizontal')
        app._refresh_page_thumbnails()
        root.update()
        # Horizontal: la hoja llega a los dos lados del recuadro de 150x108.
        for item in (photo, cover):
            name=str(app.thumbnails[item])
            assert root.tk.call(name, 'get', 5, 54) != (29,45,67)
            assert str(app.thumbnails_small[item])
        app.orientation.set('Vertical')
        app._refresh_page_thumbnails()
        root.update()
        for item in (photo, cover):
            name=str(app.thumbnails[item])
            assert root.tk.call(name, 'get', 5, 54) == (29,45,67)
            assert root.tk.call(name, 'get', 75, 54) != (29,45,67)
        # No se toca la imagen base al cambiar la orientación.
        with Image.open(cover) as im:
            assert im.size == (840,600)
    finally:
        if app:
            app._close_preview()
            app._close_mobile_import()
            for key in ('pdf_temp','special_temp','mobile_temp','project_temp'):
                getattr(app,key).cleanup()
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere una ventana gráfica')
def test_alignment_guides_appear_while_dragging_and_disappear_on_release(tmp_path):
    from custom_editor import edit_custom_page
    root = tk.Tk()
    root.geometry('1290x850+0+0')
    window = None
    try:
        window = edit_custom_page(root,initial={
            'kind':'Portada','theme':'Personalizar','title':'ÁLBUM','subtitle':'',
            'background_type':'color','background_color':'#F6EBDC',
            'show_title':True,'show_subtitle':False},image_dir=tmp_path,
            landscape=False,binding=False,on_save=lambda *_: None)
        root.update()
        root.after(75,root.quit)
        root.mainloop()  # permitir el primer repintado y fijar el tamaño real
        canvases=[w for w in _walk_widgets(window) if isinstance(w,tk.Canvas) and w.cget('cursor')=='fleur']
        assert len(canvases)==1
        canvas=canvases[0]
        x=canvas.winfo_width()//2; y=canvas.winfo_height()//2
        canvas.event_generate('<ButtonPress-1>',x=x,y=y)
        canvas.event_generate('<B1-Motion>',x=x+3,y=y+2)
        root.after(35,root.quit)
        root.mainloop()
        assert len(canvas.find_withtag('guia-alineacion')) >= 2
        canvas.event_generate('<ButtonRelease-1>',x=x+3,y=y+2)
        root.after(280,root.quit)
        root.mainloop()
        assert len(canvas.find_withtag('guia-alineacion')) == 0
    finally:
        if window and window.winfo_exists():window.destroy()
        root.destroy()


def _walk_widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from _walk_widgets(child)
