"""Regresión v1.8.1: el rediseño es una piel, no cambia los datos."""
from __future__ import annotations
from pathlib import Path
import tkinter as tk
import pytest
from PIL import Image


def root_or_skip():
    try:return tk.Tk()
    except tk.TclError:pytest.skip('Este runner no ofrece un escritorio Tk completo')


def test_main_panorama_seven_fields_and_workspace():
    from main import ReveloApp
    root=root_or_skip()
    try:
        app=ReveloApp(root)
        root.geometry('1270x845');root.update()
        assert len(app.settings_controls_row.winfo_children())==7
        # El escritorio virtual del runner Windows puede limitar la ventana
        # a menos de los 845 píxeles solicitados. Con pantalla suficiente,
        # exigimos los mismos 340 px; con pantalla pequeña, medimos el área
        # relativa disponible sin dejar que desaparezca el panel de orden.
        available_height = min(root.winfo_height(), root.winfo_screenheight())
        minimum_order = 340 if available_height >= 825 else max(230, min(340, int(available_height * .35)))
        assert app.order_area.winfo_height() >= minimum_order, (
            f"Orden: {app.order_area.winfo_height()}px; requerido: {minimum_order}px; "
            f"pantalla {root.winfo_screenwidth()}x{root.winfo_screenheight()}; "
            f"ventana {root.winfo_width()}x{root.winfo_height()}"
        )
        assert 'Importar desde móvil · QR'==app.mobile_btn.cget('text')
        assert app.add_btn.cget('command')
        assert hasattr(app.add_btn,'_editorial_assets')
        assert len(app.add_btn._editorial_assets)==3
        assert len([w for w in root.winfo_children() if w.__class__.__name__=='PhotoBanner'])==1
    finally:root.destroy()


def test_caption_window_has_only_one_visible_heading_and_photo_banner(tmp_path):
    from main import ReveloApp
    photo=tmp_path/'sample.png'
    Image.new('RGB',(500,330),'#246D76').save(photo)
    root=root_or_skip()
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo];app.details[photo]=(500,330)
        app.caption_dialog(photo)
        root.update()
        dialogs=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)]
        assert len(dialogs)==1
        dialog=dialogs[0]
        assert hasattr(dialog,'_editorial_banner')
        # v1.8.2: el título se integra dentro del banner fotográfico;
        # no debe reservar otra fila debajo ni repetirse el nombre del programa.
        banner_labels=[w.cget('text') for w in dialog._editorial_banner.winfo_children()
                       if isinstance(w,tk.Label) and w.cget('text').strip()]
        assert banner_labels==['Texto y pie de foto']
        labels=[]
        def walk(w):
            for child in w.winfo_children():
                if isinstance(child,tk.Label):labels.append(child.cget('text'))
                walk(child)
        walk(dialog)
        assert labels.count('Texto y pie de foto')==1
        assert 'Revelo' not in labels
        assert any('VISTA PREVIA DE LA HOJA' in name for name in labels)
    finally:root.destroy()


def test_no_banner_repeats_brand_in_secondary_windows():
    from editorial_theme import add_secondary_banner,apply_window_skin,PhotoBanner
    root=root_or_skip()
    try:
        dialog=tk.Toplevel(root)
        dialog.title('Revelo · Herramienta')
        label=tk.Label(dialog,text='Herramienta',bg='#081928')
        label.pack()
        apply_window_skin(dialog,compact=True)
        dialog.update()
        banner=dialog._editorial_banner
        assert isinstance(banner,PhotoBanner)
        assert banner.winfo_height()==78
        assert [child.cget('text') for child in banner.winfo_children()
                if isinstance(child,tk.Label) and child.cget('text')]==['Herramienta']
        assert banner._image is not None
    finally:root.destroy()
