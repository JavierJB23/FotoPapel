"""Control coherente del fondo general y de las excepciones por fotografía.

La lista de la cabecera es el modo común; cambiarla no puede borrar fondos
individuales inadvertidamente. «Personalizado» abre el editor de capas y
«Imagen para todas» permite escoger una foto como fondo de página.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from revelo_backgrounds import PRESETS, validate_background_spec

CUSTOM = 'Personalizado'
ALL_IMAGE = 'Imagen para todas'
GENERAL_CHOICES = (*PRESETS, 'Difuminado')


def _silent_choice(app, choice: str) -> None:
    app._background_choice_guard = True
    try:
        app.paper_background.set(choice)
    finally:
        app._background_choice_guard = False
    app._background_choice_previous = choice


def _refresh(app) -> None:
    """Invalidar las imágenes precomputadas; no altera proyectos ni originales."""
    app.thumbnails.clear()
    app.thumbnails_small.clear()
    app.sheet_thumbnails.clear()
    if app.paths and not app.is_busy:
        app.render_library()
        app.render_order()
    if app.preview_window is not None and app.preview_window.winfo_exists():
        app._show_preview_page()


def _confirm_override(app, new_name: str) -> bool:
    if not (app.background_global or app.background_overrides):
        return True
    import revelo_dialogs as messagebox
    return bool(messagebox.askyesno(
        'Revelo · Sustituir fondos',
        'Hay fondos individuales o una imagen de fondo personalizados.\n\n'
        f'Si aplicas «{new_name}» a todo el documento, esos fondos se sustituirán '
        'por el nuevo fondo general.\n\n'
        '¿Quieres hacer el cambio y eliminar las excepciones individuales?',
        parent=app.root))


def _choose_image(app) -> str | None:
    from tkinter import filedialog
    import revelo_dialogs as messagebox
    selected = filedialog.askopenfilename(
        parent=app.root, title='Imagen de fondo para todas las fotografías',
        filetypes=[('Fotografías', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.heif')])
    if not selected:
        return None
    try:
        path = Path(selected).expanduser().resolve()
        if not path.is_file() or path.stat().st_size > 150 * 1024 * 1024:
            raise ValueError('La imagen no existe o supera los 150 MB.')
        with Image.open(path) as im:
            if im.width * im.height > 220_000_000:
                raise ValueError('La imagen de fondo tiene demasiados píxeles.')
            im.verify()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        messagebox.showwarning('Revelo · Imagen de fondo', str(exc), parent=app.root)
        return None
    return str(path)


def on_choice(app) -> None:
    """Callback del desplegable; cancela sin alterar el documento."""
    if getattr(app, '_background_choice_guard', False):
        return
    new = app.paper_background.get()
    old = getattr(app, '_background_choice_previous', 'Blanco')
    if getattr(app, '_restoring_project', False):
        app._background_choice_previous = new
        return
    if new == old:
        return
    if getattr(app, 'background_window', None) is not None and app.background_window.winfo_exists():
        _silent_choice(app, old)
        import revelo_dialogs as messagebox
        messagebox.showinfo('Revelo · Fondos',
                            'Guarda o cancela el editor de fondos antes de cambiar el fondo general.',
                            parent=app.root)
        return

    if new == CUSTOM:
        # No se borra ninguna elección anterior. Si se cancela, se restaura.
        app._background_pending_custom_from = old
        app.root.after_idle(app.open_backgrounds)
        app._background_choice_previous = CUSTOM
        return

    if new == ALL_IMAGE:
        image = _choose_image(app)
        if not image or not _confirm_override(app, 'Imagen para todas'):
            _silent_choice(app, old)
            return
        if old in PRESETS:
            app.paper_background_color.set(PRESETS[old])
        app.background_global = validate_background_spec(
            {'mode': 'Imagen', 'image': image, 'opacity': 100, 'fit': 'Cubrir'})
        app.background_overrides.clear()
        _silent_choice(app, CUSTOM)
        app._sync_free_background_from_main()
        _refresh(app)
        return

    if new in GENERAL_CHOICES:
        if not _confirm_override(app, new):
            _silent_choice(app, old)
            return
        app.background_global = {}
        app.background_overrides.clear()
        app._background_pending_custom_from = None
        app._background_choice_previous = new
        app._sync_free_background_from_main()
        _refresh(app)
        return

    _silent_choice(app, old)


def cancel_custom_choice(app) -> None:
    """Cancelar el editor abierto desde «Personalizado» restaura el combo."""
    old = getattr(app, '_background_pending_custom_from', None)
    if old is not None:
        app._background_pending_custom_from = None
        _silent_choice(app, old)


def commit_custom_editor(app, global_spec: dict, overrides: dict) -> None:
    """Al guardar, marcar Personalizado sin perder el color común heredado."""
    from_mode = (getattr(app, '_background_pending_custom_from', None)
                 or getattr(app, '_background_choice_previous', 'Blanco'))
    # Al pasar desde un fondo prefijado a uno personalizado, conservar ese
    # mismo color como base bajo las transparencias y fotografías.
    if from_mode in PRESETS:
        app.paper_background_color.set(PRESETS[from_mode])
    if from_mode == 'Difuminado' and not global_spec:
        app.background_global = {'mode': 'Difuminado', 'opacity': 100,
                                 'color': '#FFFFFF', 'image': '', 'fit': 'Cubrir'}
    app._background_pending_custom_from = None
    if global_spec or overrides or from_mode == CUSTOM:
        _silent_choice(app, CUSTOM)
    else:
        _silent_choice(app, from_mode)


def choose_custom_color(app) -> None:
    """El selector «…» también respeta los fondos individuales ya guardados."""
    from tkinter import colorchooser
    selected=colorchooser.askcolor(color=app.paper_background_color.get(),
                                   parent=app.root,title='Revelo · Color del papel')
    if not selected or not selected[1]:
        return
    if not _confirm_override(app, 'Color personalizado'):
        return
    app.background_global={}
    app.background_overrides.clear()
    app.paper_background_color.set(selected[1].upper())
    _silent_choice(app, CUSTOM)
    app._sync_free_background_from_main()
    _refresh(app)
