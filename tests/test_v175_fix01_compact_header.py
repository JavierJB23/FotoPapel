"""El fondo del papel debe compartir fila con los demás ajustes."""
import tkinter as tk
import pytest
from main import ReveloApp


@pytest.mark.parametrize('width', [1100, 1270, 1500])
def test_compact_header_one_row_at_supported_window_widths(width):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('La prueba de interfaz necesita una pantalla')
    try:
        app = ReveloApp(root)
        root.geometry(f'{width}x845+0+0')
        root.update()
        row = app.settings_controls_row
        panels = row.winfo_children()
        assert len(panels) == 7
        assert len({panel.winfo_y() for panel in panels}) == 1
        assert panels[-1].winfo_children()[0].cget('text') == 'FONDO DEL PAPEL'
        # Reservar un pequeño margen: Windows puede medir las fuentes de
        # forma distinta y la fila debe caber incluso en el runner de 1024 px.
        assert panels[-1].winfo_x() + panels[-1].winfo_width() <= row.winfo_width() - 8
        assert all(panel.winfo_width() > 45 for panel in panels)
        assert all(panel.winfo_x() + panel.winfo_width() < panels[i+1].winfo_x()
                   for i, panel in enumerate(panels[:-1]))
        assert str(app.paper_background_combo.cget('state')) == 'readonly'
        app.fit.set('Rellenar (recortar)')
        root.update()
        assert str(app.paper_background_combo.cget('state')) == 'disabled'
        app.fit.set('Ajustar (sin recortar)')
        app.paper_background.set('Personalizado')
        root.update()
        assert app.paper_background_button.winfo_ismapped()
        # Reservar un pequeño margen: Windows puede medir las fuentes de
        # forma distinta y la fila debe caber incluso en el runner de 1024 px.
        assert panels[-1].winfo_x() + panels[-1].winfo_width() <= row.winfo_width() - 8
    finally:
        root.destroy()
