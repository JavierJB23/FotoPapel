"""Regresiones FIX07: un estado disabled neutro, scrollbars y espacio útil."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pytest
from PIL import ImageColor

from revelo_button_skin import _paint, style_button


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip('No existe un escritorio Tk para las pruebas visuales')


@pytest.mark.parametrize('initial_bg', ['#4CE8D4', '#193A4E', '#FFFFFF', '#9D034C'])
def test_todos_los_botones_deshabilitados_muestran_silueta_neutra(initial_bg):
    root = _root()
    count = []
    try:
        panel = tk.Frame(root, bg='#103044')
        panel.pack()
        button = tk.Button(panel, text='Abrir editor visual de posición',
                           command=lambda: count.append(1), bg=initial_bg,
                           font=('Segoe UI', 10, 'bold'))
        button.pack()
        style_button(button)
        button.configure(state='disabled')
        root.update()
        overlay = getattr(button, '_editorial_disabled_overlay', None)
        assert button.cget('state') == 'disabled'
        assert overlay is not None and overlay.winfo_ismapped()
        assert overlay.cget('bg').upper() == panel.cget('bg').upper()
        assert overlay.cget('fg').upper() == '#718693'
        assert button.cget('bg').upper() == panel.cget('bg').upper()
        assert _paint(180, 36, accent=True, swatch=None, hover=False,
                      disabled=True).getpixel((0, 0))[3] == 0
        button.invoke()
        assert count == [], 'Un botón inhabilitado jamás debe ejecutar su comando'
        button.configure(state='normal')
        root.update()
        assert not overlay.winfo_ismapped()
        button.invoke()
        assert count == [1]
    finally:
        root.destroy()




def test_boton_creado_ya_deshabilitado_tambien_se_dibuja_neutro():
    root = _root()
    try:
        panel = tk.Frame(root, bg='#103044')
        panel.pack()
        btn = tk.Button(panel, text='Elegir foto…', bg='#4CE8D4', state='disabled')
        btn.pack()
        style_button(btn)
        root.update()
        assert btn.cget('state') == 'disabled'
        assert btn._editorial_disabled_overlay.winfo_ismapped()
        assert btn._editorial_disabled_overlay.cget('bg') == panel.cget('bg')
    finally:
        root.destroy()

def test_el_estado_inhabilitado_no_hereda_el_color_aguamarina():
    disabled_aqua = _paint(180, 36, accent=True, swatch=None,
                           hover=False, disabled=True)
    disabled_white = _paint(180, 36, accent=False, swatch='#FFFFFF',
                            hover=False, disabled=True)
    assert disabled_aqua.getpixel((90, 18)) == disabled_white.getpixel((90, 18))
    expected = ImageColor.getrgb('#172637')
    assert disabled_aqua.getpixel((90, 18))[:3] == expected


def test_dos_botones_de_recorte_caben_sin_invadirse():
    root = _root()
    try:
        rail = tk.Frame(root, width=277, bg='#103044')
        rail.pack()
        rail.pack_propagate(False)
        a = tk.Button(rail, text='Quitar recorte', font=('Segoe UI', 10, 'bold'))
        b = tk.Button(rail, text='Quitar bordes', font=('Segoe UI', 10, 'bold'))
        style_button(a); style_button(b)
        a.pack(side='left', padx=(0,5)); b.pack(side='left')
        root.update()
        assert a.winfo_reqwidth() + b.winfo_reqwidth() + 5 <= rail.winfo_width()
    finally:
        root.destroy()


def test_scrollbars_auxiliares_reciben_el_estilo_editorial():
    from editorial_theme import apply_window_skin
    root = _root()
    try:
        dialog = tk.Toplevel(root)
        sc = ttk.Scrollbar(dialog, orient='vertical')
        sc.pack(side='right',fill='y')
        apply_window_skin(dialog, compact=True)
        dialog.update()
        assert sc.cget('style') == 'Revelo.Vertical.TScrollbar'
        assert ttk.Style(dialog).configure('Revelo.Vertical.TScrollbar', 'background')
    finally:
        root.destroy()


def test_el_editor_libre_no_reserva_lineas_de_ayuda_innecesarias():
    path = Path(__file__).resolve().parents[1] / 'custom_editor.py'
    if not path.exists():
        pytest.skip('El archivo del editor se añade al proyecto principal durante la compilación')
    code = path.read_text(encoding='utf-8')
    assert 'photo_controls = tk.Frame(pick,bg=SURFACE)' in code
    assert 'Mueve el elemento elegido. También puedes arrastrar' not in code
    assert 'Libre: mueve la foto y ajusta ancho/alto.' not in code
    assert "scroll = ttk.Scrollbar(rail,orient='vertical',style='Revelo.Vertical.TScrollbar'" in code


def test_nombre_boton_de_bordes_sin_solapamiento():
    path = Path(__file__).resolve().parents[1] / 'photo_editor_ui.py'
    if not path.exists():
        pytest.skip('El archivo de edición se añade al proyecto principal durante la compilación')
    code = path.read_text(encoding='utf-8')
    assert "self._btn(tools,'Quitar bordes',self._auto_white)" in code
    assert "'Quitar bordes blancos'" not in code
