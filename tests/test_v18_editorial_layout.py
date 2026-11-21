"""Rediseño editorial: mismas acciones, paneles amplios y sin solapamientos."""
import tkinter as tk
import pytest

from main import ReveloApp


@pytest.mark.parametrize("width,height", [(1100, 730), (1270, 845), (1600, 900)])
def test_editorial_layout_keeps_work_areas_and_all_controls_visible(width, height):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("El entorno no dispone de pantalla")
    try:
        app = ReveloApp(root)
        root.geometry(f"{width}x{height}+0+0")
        root.update()
        # Todas las opciones de impresión siguen en la misma fila.
        panels = app.settings_controls_row.winfo_children()
        assert len(panels) == 7
        assert len({panel.winfo_y() for panel in panels}) == 1
        assert panels[-1].winfo_rootx() + panels[-1].winfo_width() <= root.winfo_rootx() + width
        # El área que el usuario necesita para ordenar no desaparece por el estilo.
        assert app.order_area.winfo_height() >= (230 if height == 730 else 340)
        assert app.library_area.winfo_height() >= 250
        for button in (app.add_btn, app.special_btn, app.mobile_btn, app.clear_btn,
                       app.layout_edit_btn, app.numbers_btn, app.reset_btn,
                       app.preview_btn, app.export_btn, app.open_btn):
            assert button.winfo_ismapped(), str(button)
            assert button.winfo_rootx() + button.winfo_width() <= root.winfo_rootx() + width + 2
            assert button.winfo_rooty() + button.winfo_height() <= root.winfo_rooty() + height + 2
        # El editor responde al diseño elegido sin alterar su callback.
        app.layout_template.set('Diseño libre')
        root.update()
        assert app.layout_edit_btn.cget('state') == 'normal'
        assert app.layout_edit_btn.cget('text') in ('Editar', 'Editar diseño libre')
        # El encabezado decorativo no requiere una descarga ni cambia el motor.
        assert app.editorial_header_image.width() > 0
    finally:
        root.destroy()


def test_editorial_labels_and_background_still_connected():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("El entorno no dispone de pantalla")
    try:
        app = ReveloApp(root)
        root.update()
        assert str(app.paper_background_combo.cget('state')) == 'readonly'
        app.fit.set('Rellenar (recortar)')
        root.update()
        assert str(app.paper_background_combo.cget('state')) == 'disabled'
        app.fit.set('Ajustar (sin recortar)')
        root.update()
        assert str(app.paper_background_combo.cget('state')) == 'readonly'
    finally:
        root.destroy()
