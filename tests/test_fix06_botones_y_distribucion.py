"""FIX06: controles vivos sin rectángulos y biblioteca compacta adaptable."""
import tkinter as tk
import pytest

from revelo_button_skin import style_button, _paint


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip('Sin escritorio Tk para probar botones')


@pytest.mark.parametrize('color,foreground', [
    ('#4CE8D4', '#081928'),  # Corrección automática activada
    ('#193A4E', '#F4F8FA'),  # Corrección automática desactivada
    ('#FFFFFF', '#101F2B'),  # Color del texto claro
    ('#253447', '#FFFFFF'),  # Color del texto oscuro
    ('#F6E5C4', '#081928'),  # Recorte listo
])
def test_cambio_color_pinta_pildora_sin_fondo_rectangular(color, foreground):
    root = _root()
    try:
        panel = tk.Frame(root, bg='#103044')
        panel.pack()
        btn = tk.Button(panel, text='Color del texto', bg='#193A4E',
                        fg='#F4F8FA', font=('Segoe UI', 10, 'bold'))
        btn.pack()
        style_button(btn)
        btn.configure(bg=color, fg=foreground, activebackground=color)
        root.update()
        assert btn.cget('bg').upper() == '#103044'
        assert btn.cget('activebackground').upper() == '#103044'
        assert btn._editorial_requested_bg.upper() == color
        assert btn._editorial_requested_fg == foreground
        assert len(btn._editorial_assets) == 3
        assert btn.winfo_ismapped()
        assert btn.cget('command') == ''  # El rediseño no añade acciones
    finally:
        root.destroy()


def test_toggle_modifica_ancho_y_color_sin_romper_comando():
    root = _root()
    calls = []
    try:
        panel = tk.Frame(root, bg='#103044')
        panel.pack()
        btn = tk.Button(panel, text='Corrección automática',
                        command=lambda: calls.append(True), bg='#193A4E')
        btn.pack()
        style_button(btn)
        previous = btn._editorial_assets[0].width()
        btn.configure(text='✓ Corrección automática activada',
                      bg='#4CE8D4', fg='#081928')
        root.update()
        assert btn._editorial_assets[0].width() >= previous
        assert btn.cget('bg') == panel.cget('bg')
        assert btn.cget('command')
        btn.invoke()
        assert calls == [True]
        btn.configure(text='Corrección automática',bg='#193A4E',fg='#F4F8FA')
        root.update()
        assert btn.cget('bg') == panel.cget('bg')
    finally:
        root.destroy()


def test_esquinas_realmente_transparentes_y_boton_orden_cuadrado():
    normal = _paint(160, 36, accent=False, swatch=None, hover=False, disabled=False)
    active = _paint(160, 36, accent=True, swatch=None, hover=False, disabled=False)
    white = _paint(160, 36, accent=False, swatch='#FFFFFF', hover=False, disabled=False)
    updown = _paint(34, 32, accent=False, swatch=None, hover=False, disabled=False)
    for image in (normal, active, white, updown):
        assert image.mode == 'RGBA'
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((image.width-1, 0))[3] == 0
        assert image.getpixel((image.width//2, image.height//2))[3] > 245
    assert updown.width == 34 and updown.height == 32


def test_revelo_biblioteca_una_fila_cuando_hay_espacio():
    from main import ReveloApp
    root = _root()
    try:
        app = ReveloApp(root)
        root.geometry('1600x900+0+0')
        root.update()
        for button in (app.add_btn, app.special_btn, app.mobile_btn, app.clear_btn):
            assert button.winfo_ismapped(), f'Botón oculto: {button.cget("text")}'
        # Si el runner limita físicamente el ancho, la interfaz usa 2 filas.
        files_row = app.add_btn.master
        qr_row = app.mobile_btn.master
        required_width = files_row.winfo_reqwidth() + qr_row.winfo_reqwidth() + 12
        if files_row.master.winfo_width() >= required_width:
            ys = {b.winfo_rooty() for b in
                  (app.add_btn, app.special_btn, app.mobile_btn, app.clear_btn)}
            assert len(ys) == 1, f'Botones desalineados en pantalla ancha: {ys}'
        root.geometry('1100x730+0+0')
        root.update()
        for button in (app.add_btn, app.special_btn, app.mobile_btn, app.clear_btn):
            assert button.winfo_ismapped(), f'Botón desaparecido: {button.cget("text")}'
        assert app.mobile_btn.cget('text') == 'Importar desde móvil · QR'
    finally:
        root.destroy()


def test_photo_editor_real_usa_botones_sin_fondo_rectangular(tmp_path):
    """Prueba de integración: botón auténtico de Corrección automática."""
    from PIL import Image
    from photo_editor_ui import PhotoEditor
    root = _root()
    photo = tmp_path / 'original.png'
    Image.new('RGB', (120, 80), '#3D7999').save(photo)
    editor = None
    try:
        editor = PhotoEditor(root, photo, None, lambda _spec: None)
        root.update()
        assert editor.auto_btn.cget('bg') == editor.auto_btn.master.cget('bg')
        editor._toggle_auto()
        root.update()
        assert 'activada' in editor.auto_btn.cget('text')
        assert editor.auto_btn.cget('bg') == editor.auto_btn.master.cget('bg')
        assert editor.auto_btn._editorial_requested_bg.upper() == '#4CE8D4'
        editor._toggle_auto()
        root.update()
        assert editor.auto_btn.cget('bg') == editor.auto_btn.master.cget('bg')
    finally:
        if editor and editor.winfo_exists():
            editor.close()
        root.destroy()
