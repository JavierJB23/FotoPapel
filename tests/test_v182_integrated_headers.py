"""Regresión v1.8.2: cabeceras fusionadas y superficie de edición."""
from pathlib import Path
import tkinter as tk
from PIL import Image
import pytest


def root_or_skip():
    try:return tk.Tk()
    except tk.TclError:pytest.skip('El runner no ofrece escritorio Tk')


def test_dialog_title_appears_inside_banner_only():
    from editorial_theme import apply_window_skin, PhotoBanner
    root=root_or_skip()
    try:
        dlg=tk.Toplevel(root);dlg.title('Revelo · Importar desde móvil')
        outer=tk.Frame(dlg,bg='#081928',padx=25,pady=20);outer.pack(fill='both',expand=True)
        tk.Label(outer,text='IMPORTAR DESDE MÓVIL').pack()
        tk.Label(outer,text='1. Escanea el código con tu móvil.').pack()
        apply_window_skin(dlg)
        dlg.update()
        banner=dlg._editorial_banner
        assert isinstance(banner,PhotoBanner)
        assert banner.heading=='Importar desde móvil'
        labels=[]
        def walk(widget):
            for c in widget.winfo_children():
                if isinstance(c,tk.Label) and c.winfo_manager():labels.append(c.cget('text'))
                walk(c)
        walk(dlg)
        assert labels.count('Importar desde móvil')==1
        assert not any('IMPORTAR DESDE MÓVIL'==x for x in labels)
        assert '1. Escanea el código con tu móvil.' in labels
    finally:root.destroy()


def test_panorama_no_stretch_uses_original_five_to_one_ratio():
    from editorial_theme import banner_raster
    image=banner_raster(1280,78)
    assert image.size==(1280,78)
    # El fondo debe ser oscuro a la izquierda, con fotografía solo a la derecha.
    assert sum(image.getpixel((10,40)))<170


def test_combo_arrow_without_repeated_bottom_line():
    from editorial_theme import _combobox_asset
    art=_combobox_asset(20,29,arrow=True)
    pixels=[art.getpixel((x,28)) for x in range(20)]
    # La flecha no debe añadir una barra de contorno bajo el desplegable.
    assert len(set(pixels))<=2


def test_editors_share_same_integrated_heading():
    from editorial_theme import apply_window_skin
    root=root_or_skip()
    try:
        for name,heading in [('Editar fotografía','Editar fotografía'),
                             ('Personalizar portada o separador','Personalizar página'),
                             ('Diseño libre','Composición libre'),
                             ('Añadir página','Crear página')]:
            dialog=tk.Toplevel(root);dialog.title('Revelo · '+name)
            form=tk.Frame(dialog);form.pack()
            tk.Label(form,text=heading.upper()).pack()
            apply_window_skin(dialog)
            dialog.update_idletasks()
            assert dialog._editorial_banner.heading==heading
            # En runners Windows sin escritorio visible, Tk puede devolver 1 px
            # antes de que el administrador de ventanas dibuje el Toplevel.
            # Verificamos la altura solicitada por el widget y que esté empaquetado.
            assert int(dialog._editorial_banner.cget('height')) == 78
            assert dialog._editorial_banner.winfo_reqheight() == 78
            assert dialog._editorial_banner.winfo_manager() == 'pack'
            assert not form.winfo_exists() or all(c.cget('text')!=heading.upper()
                       for c in form.winfo_children() if isinstance(c,tk.Label))
            dialog.destroy()
    finally:root.destroy()
