"""FIX05: desplazamiento con rueda sin cambiar controles y ventana de altura útil."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pytest

from custom_editor import editor_initial_size, editor_initial_geometry, edit_custom_page


def test_editor_geometry_uses_work_area_not_full_screen():
    for area in ((0, 0, 1366, 728), (0, 0, 1920, 1030), (50, 40, 1450, 940)):
        left, top, right, bottom = area
        geometry = editor_initial_geometry(area)
        dimensions_and_pos = list(map(int, geometry.replace('+', 'x').split('x')))
        w, h, px, py = dimensions_and_pos
        assert 790 <= w <= min(1150, right-left)
        assert h >= 600
        assert left <= px <= right - w
        assert top <= py <= bottom - h
        assert py + h + 40 <= bottom  # hay sitio para el marco nativo


def test_editor_scroll_mouse_wheel_over_combo_scale_and_entry_without_changes(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('No existe display para Tk')
    root.geometry('1200x750+0+0')
    try:
        saved = []
        editor = edit_custom_page(root, initial={'kind': 'Portada', 'theme': 'Crema',
                            'title': 'RECETARIO', 'subtitle': ''}, image_dir=tmp_path,
                            landscape=False, binding=False, on_save=saved.append)
        root.update()
        assert editor.transient() == ''  # ventana nativa: iconificable
        descendants = []
        def walk(w):
            descendants.append(w)
            for child in w.winfo_children():
                walk(child)
        walk(editor)
        canvases = [w for w in descendants if isinstance(w, tk.Canvas)]
        controls_canvas = next(w for w in canvases if len(w.find_all()) > 0 and w.cget('width') == '330')
        combos = [w for w in descendants if isinstance(w, ttk.Combobox)]
        assert combos
        combo = combos[0]
        baseline = combo.get()
        for widget in (combo, next(w for w in descendants if isinstance(w, tk.Scale)),
                       next(w for w in descendants if isinstance(w, tk.Entry))):
            controls_canvas.yview_moveto(0)
            root.update()
            start = controls_canvas.yview()[0]
            before = widget.get() if isinstance(widget, (ttk.Combobox, tk.Entry)) else widget.get()
            widget.event_generate('<MouseWheel>', delta=-120, x=4, y=4)
            root.update()
            assert controls_canvas.yview()[0] > start, type(widget)
            assert widget.get() == before, type(widget)
        assert combo.get() == baseline
        controls_canvas.yview_moveto(0)
        root.update()
        start = controls_canvas.yview()[0]
        combo.event_generate('<Button-5>', x=4, y=4)
        root.update()
        assert controls_canvas.yview()[0] > start
        assert combo.get() == baseline
        editor.iconify()
        root.update()
        # Un Xvfb sin gestor de ventanas puede ignorar el estado 'iconic'.
        # Lo importante aquí es que iconify/deiconify sean permitidos.
        editor.deiconify()
        root.update()
        assert editor.state() == 'normal'
    finally:
        root.destroy()
