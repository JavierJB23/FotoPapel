"""Botones redondeados de Revelo sin fondos rectangulares nativos.

Los cambios posteriores mediante .configure(bg=..., fg=..., text=..., state=...)
se reflejan en el dibujo redondeado. Se mantienen los tk.Button y sus comandos.
"""
from __future__ import annotations

from functools import lru_cache
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk, ImageColor

NAVY = '#081928'
NORMAL = '#193A4E'
AQUA = '#4CE8D4'

_NEUTRALS = {
    '#193a4e', '#103044', '#081928', '#071625', '#1b4054', '#102d42',
    '#20334a', '#304256', '#35445a', '#203244', '#1a2b38', '#102a3b',
    '#274e63', '#1a3548', '#152637', '#29425d', '#34506b'
}
_ACCENTS = {'#4ce8d4', '#4cd9b5', '#53f0dc', '#32dfc6', '#1bc9b4',
            '#20c9b3', '#74f5e2'}


def _hex_color(value: str) -> str:
    try:
        rgb = ImageColor.getrgb(str(value))
        return '#%02X%02X%02X' % rgb[:3]
    except (ValueError, TypeError):
        return str(value)


def _blend(color: str, other: str, amount: float) -> str:
    a = ImageColor.getrgb(color)
    b = ImageColor.getrgb(other)
    return '#%02X%02X%02X' % tuple(int(a[i]*(1-amount)+b[i]*amount) for i in range(3))


@lru_cache(maxsize=1000)
def _paint(width: int, height: int, *, accent: bool, swatch: str | None,
           hover: bool, disabled: bool) -> Image.Image:
    """Una sola figura redondeada con alpha real en las cuatro esquinas."""
    w = max(25, int(width))
    h = max(24, int(height))
    s = 3
    W, H = w*s, h*s
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if disabled:
        # Igual que el selector «Fondo del papel» cuando está inhabilitado:
        # oscuro, sin aguamarina ni efectos de atenuación por tramado.
        fill = '#172637'
        stroke = '#30495A'
    elif swatch:
        fill = _blend(swatch, '#FFFFFF', .07) if hover else swatch
        stroke = '#7DA9BB' if swatch.lower() == '#ffffff' else '#5F9DAE'
    elif accent:
        fill = '#57F1DE' if hover else '#28DAC4'
        stroke = '#96FFF0' if hover else '#4CE8D4'
    else:
        fill = '#23495E' if hover else '#132F44'
        stroke = '#6FA5B5' if hover else '#4C8194'
    radius = 5*s if w <= 39 and h <= 39 else min(H//2, 15*s)
    draw.rounded_rectangle((s, s, W-2*s, H-2*s), radius=radius,
                           fill=fill, outline=stroke, width=s)
    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def _appearance(requested_bg: str, fallback_accent: bool) -> tuple[bool, str | None]:
    color = _hex_color(requested_bg)
    low = color.casefold()
    if low in _ACCENTS:
        return True, None
    if low in _NEUTRALS:
        return False, None
    if low.startswith('#') and len(low) == 7:
        return False, color
    return fallback_accent, None


def style_button(button: tk.Button, *, accent=None):
    """Reviste cualquier botón Tk, incluidos los que cambian de color en caliente.

    La opción bg nativa permanece SIEMPRE igual al fondo de su padre;
    si una herramienta pide bg nuevo, ese color se pinta dentro de la silueta.
    Esto impide los rectángulos alrededor de «Corrección automática», las
    muestras de color del texto, «Elegir foto» y demás botones.
    """
    if not isinstance(button, tk.Button):
        return button
    if getattr(button, '_editorial_skinned', False):
        return button
    try:
        parent_bg = button.master.cget('bg')
        requested_bg = button.cget('bg')
        requested_fg = button.cget('fg')
        button.cget('text')
    except tk.TclError:
        return button

    native = button.configure
    button._editorial_native_configure = native
    button._editorial_requested_bg = requested_bg
    button._editorial_requested_fg = requested_fg
    button._editorial_parent_bg = parent_bg
    button._editorial_fallback_accent = (bool(accent) if accent is not None else
                                          _hex_color(requested_bg).casefold() in _ACCENTS)
    button._editorial_hovered = False
    button._editorial_skinned = True

    def redraw():
        if not button.winfo_exists():
            return
        try:
            label = str(button.cget('text'))
            try:
                measured = int(button.tk.call('font', 'measure', button.cget('font'), label))
            except tk.TclError:
                measured = len(label)*9
            # En el panel de recorte caben dos botones en la misma fila;
            # respetar el ancho medido de la fuente sin márgenes excesivos.
            extra = 24 if label in ('Quitar recorte', 'Quitar bordes') else 46
            width = max(42, min(480, measured+extra))
            height = 40 if ('Exportar fotos' in label or 'Guardar' in label) else 36
            if label in ('×', '↑', '↓', '…', '↕', '↔'):
                width, height = 34, 32
            is_accent, swatch = _appearance(button._editorial_requested_bg,
                                            button._editorial_fallback_accent)
            images = [ImageTk.PhotoImage(_paint(width, height, accent=is_accent,
                          swatch=swatch, hover=hover, disabled=disabled), master=button)
                      for hover, disabled in ((False, False), (True, False), (False, True))]
            button._editorial_assets = images
            button._editorial_text = label
            disabled = str(button.cget('state')) == 'disabled'
            selected = 2 if disabled else (1 if button._editorial_hovered else 0)
            native(image=images[selected], compound='center',
                   bg=button._editorial_parent_bg,
                   activebackground=button._editorial_parent_bg,
                   fg=button._editorial_requested_fg,
                   activeforeground=button._editorial_requested_fg,
                   bd=0, relief='flat', highlightthickness=0,
                   padx=0, pady=0, disabledforeground='#718693',
                   cursor='arrow' if disabled else 'hand2')

            # Tk/Windows aplica un tramado sobre TODA la imagen cuando el
            # botón nativo está desactivado (incluidas esquinas transparentes).
            # Un Label SIN estado disabled, hijo del propio botón y con el
            # MISMO fondo de la tarjeta, muestra la figura neutra sin tramado.
            # El Button original conserva state='disabled' y NO ejecuta comandos.
            overlay = getattr(button, '_editorial_disabled_overlay', None)
            if disabled:
                if overlay is None or not overlay.winfo_exists():
                    overlay = tk.Label(button, bg=button._editorial_parent_bg,
                                       fg='#718693', bd=0, relief='flat',
                                       highlightthickness=0)
                    button._editorial_disabled_overlay = overlay
                overlay.configure(image=images[2], text=label,
                                  compound='center', font=button.cget('font'),
                                  fg='#718693', bg=button._editorial_parent_bg)
                overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                overlay.lift()
            elif overlay is not None and overlay.winfo_exists():
                overlay.place_forget()
        except tk.TclError:
            return

    def configure(*args, **kwargs):
        # Conservar el contrato de Tk para consultar opciones con configure().
        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                kwargs = {**args[0], **kwargs}
            else:
                return native(*args, **kwargs)
        if not kwargs:
            return native()
        new_bg = kwargs.pop('bg', kwargs.pop('background', None))
        new_fg = kwargs.pop('fg', kwargs.pop('foreground', None))
        kwargs.pop('activebackground', None)
        kwargs.pop('activeforeground', None)
        if new_bg is not None:
            button._editorial_requested_bg = new_bg
        if new_fg is not None:
            button._editorial_requested_fg = new_fg
        # Un color no debe activarse detrás de la imagen; mantener el padre.
        kwargs['bg'] = button._editorial_parent_bg
        kwargs['activebackground'] = button._editorial_parent_bg
        if new_fg is not None:
            kwargs['fg'] = new_fg
        result = native(**kwargs)
        if (new_bg is not None or new_fg is not None or
                any(k in kwargs for k in ('text', 'textvariable', 'font', 'state'))):
            redraw()
        return result

    button.configure = configure
    button.config = configure
    button.bind('<Enter>', lambda _event: set_hover(True), add='+')
    button.bind('<Leave>', lambda _event: set_hover(False), add='+')

    def set_hover(value: bool):
        button._editorial_hovered = value
        if not button.winfo_exists():
            return
        try:
            native(image=button._editorial_assets[
                2 if str(button.cget('state')) == 'disabled' else (1 if value else 0)])
        except (tk.TclError, AttributeError):
            pass

    redraw()
    return button
