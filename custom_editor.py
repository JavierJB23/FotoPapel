"""Editor visual de portadas de Revelo: fondo libre y textos arrastrables."""
from __future__ import annotations

from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import uuid
import sys
from collections.abc import Callable, Sequence

import revelo_dialogs as messagebox

from PIL import Image, ImageOps, ImageTk
from special_pages import (CUSTOM_THEME, validate_special_spec, render_special_page,
                           render_custom_background, draw_custom_text, KINDS, THEMES, FONT_CHOICES)
from processor import printable_box

BG = '#0B1422'
SURFACE = '#142236'
PANEL = '#1B2D43'
ACCENT = '#4CD9B5'
TEXT = '#F1F6FB'
MUTED = '#9CB1C7'
PREVIEW_FRAME_MS = 16  # Límite de repintado objetivo (~60 Hz); no una garantía de FPS.


def editor_initial_size(screen_width: int, available_height: int) -> tuple[int, int]:
    """Editor casi a altura completa, sin sobrepasar el área utilizable.

    `available_height` es la altura libre de la barra de tareas; se reserva una
    holgura para el marco y la barra de título para que el pie y los bordes de la ventana se vean enteros.
    """
    width = min(1150, max(790, round(screen_width * .83)))
    height = max(420, available_height - 72)
    return width, height


def editor_work_area(window: tk.Toplevel) -> tuple[int, int, int, int]:
    """Área útil del monitor: en Windows excluye la barra de tareas.

    Evita confundir la altura total del monitor con el espacio real disponible.
    En otros sistemas se deja una holgura conservadora para paneles y docks.
    """
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                            ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

            rect = RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0,
                                                           ctypes.byref(rect), 0):
                left = max(0, rect.left)
                top = max(0, rect.top)
                right = min(screen_w, rect.right)
                bottom = min(screen_h, rect.bottom)
                if right - left >= 790 and bottom - top >= 480:
                    return left, top, right, bottom
        except (OSError, AttributeError, ValueError):
            pass
    return 0, 0, screen_w, max(480, screen_h - 55)


def editor_initial_geometry(area: tuple[int, int, int, int]) -> str:
    """Ubica el editor completo en pantalla, con la barra de tareas libre."""
    left, top, right, bottom = area
    available_w, available_h = right - left, bottom - top
    width, height = editor_initial_size(available_w, available_h)
    width = min(width, available_w)
    height = min(height, available_h)
    x = left + max(0, (available_w - width) // 2)
    y = top + min(24, max(0, available_h - height))
    return f'{width}x{height}+{x}+{y}'


def edit_custom_page(root: tk.Tk, *, initial: dict, image_dir: Path,
                     landscape: bool, binding: bool, on_save,
                     paper_dimensions_mm: tuple[float, float] | None = None,
                     page_settings: Callable[[], tuple[tuple[float, float], bool]] | None = None,
                     settings_vars: Sequence[tk.Variable] = ()):
    """Abre un editor NO modal y guarda el diseño sólo con «Guardar».

    Cuando se proporciona page_settings, la orientación, el papel y los
    márgenes del programa principal se reflejan en el editor sin cerrarlo.
    """
    image_dir.mkdir(parents=True, exist_ok=True)
    initial = dict(initial)
    original_theme = initial.get('theme', 'Crema')
    # Pasar de una página prediseñada a Personalizar conserva sus colores.
    if original_theme in THEMES:
        initial.setdefault('background_color', THEMES[original_theme]['background'])
        initial.setdefault('text_color', THEMES[original_theme]['text'])
        initial.setdefault('subtitle_color', THEMES[original_theme]['muted'])
    initial['theme'] = CUSTOM_THEME
    initial.setdefault('background_type', 'color')
    initial.setdefault('background_image', '')
    initial.setdefault('background_color', '#F6EBDC')
    initial.setdefault('background_fill', 'color')
    initial.setdefault('text_color', '#1B2D43')
    initial.setdefault('subtitle_color', '#334C63')
    initial.setdefault('title_size', 12)
    initial.setdefault('subtitle_size', 6)
    initial.setdefault('title_font', 'Georgia')
    initial.setdefault('subtitle_font', 'Georgia')
    initial.setdefault('title_x', .5)
    initial.setdefault('title_y', .42)
    initial.setdefault('subtitle_x', .5)
    initial.setdefault('subtitle_y', .58)
    initial.setdefault('show_title', True)
    initial.setdefault('show_subtitle', True)
    initial.setdefault('image_mode', 'Cubrir' if initial['background_type']=='imagen' else 'Libre')
    initial.setdefault('image_zoom_x', 1.0)
    initial.setdefault('image_zoom_y', 1.0)
    initial.setdefault('image_x', .5)
    initial.setdefault('image_y', .5)

    window = tk.Toplevel(root)
    window.title('Revelo · Personalizar portada o separador')
    # La geometría usa el área de trabajo real (sin barra de tareas).
    # NO marcar como ventana "transient": en Windows eso oculta el botón
    # Minimizar del marco nativo. Conservamos el editor NO modal.
    window.geometry(editor_initial_geometry(editor_work_area(window)))
    window.minsize(790, 470)
    window.configure(bg=BG)

    frame = tk.Frame(window, bg=BG, padx=18, pady=15)
    frame.pack(fill='both', expand=True)
    tk.Label(frame, text='PERSONALIZAR PÁGINA', bg=BG, fg=TEXT,
             font=('Segoe UI', 16, 'bold')).pack(anchor='w')
    tk.Label(frame, text='Elige un fondo, activa los textos que quieras y arrástralos sobre la hoja para colocarlos.',
             bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 12))

    buttons = tk.Frame(frame, bg=BG)
    buttons.pack(side='bottom', fill='x', pady=(12, 0))
    tk.Button(buttons, text='Cancelar', command=window.destroy,
              bg=PANEL, fg=TEXT, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=18, pady=9).pack(side='right')

    body = tk.Frame(frame, bg=BG)
    body.pack(fill='both', expand=True)
    # Panel de propiedades desplazable: los controles nuevos no se cortan en
    # pantallas pequeñas, sin robar espacio a la hoja de previsualización.
    rail = tk.Frame(body, bg=SURFACE, width=352)
    rail.pack(side='left', fill='y', padx=(0,14))
    rail.pack_propagate(False)
    controls_canvas = tk.Canvas(rail,bg=SURFACE,highlightthickness=0,width=330)
    scroll = tk.Scrollbar(rail,orient='vertical',command=controls_canvas.yview)
    controls_canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y')
    controls_canvas.pack(side='left',fill='both',expand=True)
    left = tk.Frame(controls_canvas,bg=SURFACE,padx=15,pady=12)
    scroll_window = controls_canvas.create_window((0,0),window=left,anchor='nw')
    left.bind('<Configure>',lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox('all')))
    controls_canvas.bind('<Configure>',lambda e: controls_canvas.itemconfigure(scroll_window,width=e.width))
    # Clase de eventos propia y prioritaria: atrapa la rueda ANTES de que
    # ttk.Combobox, tk.Scale y tk.Spinbox cambien valores por defecto.
    # Funciona sobre todos los hijos del panel, no solo sobre el Canvas.
    wheel_tag = f'ReveloWheel_{id(window)}'
    def wheel(event):
        if getattr(event, 'num', 0) in (4, 5):  # X11 / Linux
            steps = -3 if event.num == 4 else 3
        else:
            delta = getattr(event, 'delta', 0)
            if not delta:
                return 'break'
            direction = -1 if delta > 0 else 1
            steps = direction * (3 * max(1, round(abs(delta) / 120))
                                 if abs(delta) >= 120 else 1)
        controls_canvas.yview_scroll(steps, 'units')
        return 'break'
    for wheel_event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
        window.bind_class(wheel_tag, wheel_event, wheel)

    def register_scroll_widgets(widget):
        tags = widget.bindtags()
        if wheel_tag not in tags:
            widget.bindtags((wheel_tag,) + tags)
        for child in widget.winfo_children():
            register_scroll_widgets(child)
    right = tk.Frame(body, bg=SURFACE, padx=12, pady=12)
    right.pack(side='left', fill='both', expand=True)

    fields = {
        'kind': tk.StringVar(value=initial.get('kind', 'Separador')),
        'title': tk.StringVar(value=initial.get('title', '')),
        'subtitle': tk.StringVar(value=initial.get('subtitle', '')),
        'background_type': tk.StringVar(value=initial['background_type']),
        'background_image': tk.StringVar(value=initial['background_image']),
        'background_color': tk.StringVar(value=initial['background_color']),
        'background_fill': tk.StringVar(value=initial['background_fill']),
        'text_color': tk.StringVar(value=initial['text_color']),
        'subtitle_color': tk.StringVar(value=initial['subtitle_color']),
        'title_size': tk.IntVar(value=initial['title_size']),
        'subtitle_size': tk.IntVar(value=initial['subtitle_size']),
        'title_font': tk.StringVar(value=initial['title_font']),
        'subtitle_font': tk.StringVar(value=initial['subtitle_font']),
        'show_title': tk.BooleanVar(value=initial['show_title']),
        'show_subtitle': tk.BooleanVar(value=initial['show_subtitle']),
        'image_mode': tk.StringVar(value=initial['image_mode']),
        'image_zoom_x': tk.DoubleVar(value=initial['image_zoom_x']),
        'image_zoom_y': tk.DoubleVar(value=initial['image_zoom_y']),
        'image_x': tk.DoubleVar(value=initial['image_x']),
        'image_y': tk.DoubleVar(value=initial['image_y']),
    }
    positions = {key: float(initial[key]) for key in ('title_x', 'title_y', 'subtitle_x', 'subtitle_y')}
    focused = tk.StringVar(value='title')
    linked_scale = tk.BooleanVar(value=True)
    refresh_job = [None]
    preview_img = [None]
    bg_cache = [None, None]  # (parámetros de foto/fondo, PIL.Image)
    sample_image = [None, None]  # (archivo de origen, JPEG de vista ligera)
    source_cache = [None, None]  # JPEG abierto en memoria, no se reabre por arrastre
    blurred_cache = [None, None]  # fondo desenfocado independiente de la posición de foto
    # La vista previa reproduce la relación de aspecto del papel elegido;
    # no usa una proporción fija de A5 ni la miniatura de una portada antigua.
    physical_mm = paper_dimensions_mm or ((210.0, 148.0) if landscape else (148.0, 210.0))
    if page_settings is not None:
        physical_mm, binding = page_settings()
    page_size = (max(1, round(physical_mm[0] * 4)),
                 max(1, round(physical_mm[1] * 4)))
    window.revelo_page_mm = physical_mm  # Útil para diagnóstico y pruebas de UI.
    setting_traces: list[tuple[tk.Variable, str]] = []
    canvas_box = [0, 0, 1, 1]
    image_drag = [None]
    drag_text = [None]
    label_color = MUTED

    def label(text):
        tk.Label(left, text=text, bg=SURFACE, fg=label_color,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(10, 3))

    def select(caption, var, values):
        label(caption)
        combo = ttk.Combobox(left, values=values, textvariable=var, state='readonly')
        combo.pack(fill='x')
        return combo

    select('TIPO DE PÁGINA', fields['kind'], list(KINDS))
    label('FONDO')
    row_bg = tk.Frame(left, bg=SURFACE)
    row_bg.pack(fill='x')
    for title, value in [('Color liso', 'color'), ('Fotografía', 'imagen')]:
        tk.Radiobutton(row_bg, text=title, variable=fields['background_type'], value=value,
                       bg=SURFACE, fg=TEXT, activebackground=SURFACE,
                       activeforeground=ACCENT, selectcolor=PANEL,
                       font=('Segoe UI', 9)).pack(side='left', padx=(0,8))

    # Los cuatro colores clásicos también aparecen dentro de Personalizar.
    # La selección de paleta cambia fondo y colores legibles del texto, pero
    # después se pueden modificar independientemente los títulos y posiciones.
    palette_names = [*THEMES, 'Otro color…']
    existing = fields['background_color'].get().upper()
    chosen_palette = next((name for name, theme in THEMES.items()
                           if theme['background'].upper() == existing), 'Otro color…')
    palette = tk.StringVar(value=chosen_palette)
    palette_widget = select('PALETA DE COLORES', palette, palette_names)

    def color_button(caption, field):
        row = tk.Frame(left, bg=SURFACE)
        row.pack(fill='x', pady=(6, 0))
        tk.Label(row, text=caption, fg=MUTED, bg=SURFACE,
                 font=('Segoe UI', 9)).pack(side='left')
        chip = tk.Button(row, text='Elegir color…', bg=fields[field].get(),
                         relief='flat', padx=8, pady=3, cursor='hand2')
        chip.pack(side='right')

        def color_changed(*_):
            value = fields[field].get()
            chip.configure(bg=value,
                           fg='#111111' if sum(int(value[i:i+2],16) for i in (1,3,5)) > 425 else '#FFFFFF')
        fields[field].trace_add('write', color_changed)
        color_changed()

        def choose():
            result = colorchooser.askcolor(color=fields[field].get(), parent=window,
                                          title='Revelo · ' + caption)
            if result and result[1]:
                fields[field].set(result[1].upper())
                if field == 'background_color':
                    palette.set('Otro color…')
        chip.configure(command=choose)
        return chip

    background_chip = color_button('Color bajo la foto', 'background_color')

    def palette_selected(event=None):
        name = palette.get()
        if name in THEMES:
            values = THEMES[name]
            fields['background_color'].set(values['background'].upper())
            fields['text_color'].set(values['text'].upper())
            fields['subtitle_color'].set(values['muted'].upper())
        elif name == 'Otro color…':
            background_chip.invoke()

    # Evento de selección humana (no un trace) para no reabrir el selector
    # al elegir un color manualmente en el diálogo de Windows.
    palette_widget.bind('<<ComboboxSelected>>', palette_selected)
    label('RELLENO DEL ESPACIO LIBRE')
    fill_controls = tk.Frame(left, bg=SURFACE)
    fill_controls.pack(fill='x')
    for caption, value in [('Color liso', 'color'), ('Difuminado', 'blurred')]:
        tk.Radiobutton(fill_controls, text=caption, variable=fields['background_fill'],
                       value=value, bg=SURFACE, fg=TEXT, selectcolor=PANEL,
                       activebackground=SURFACE, activeforeground=ACCENT,
                       font=('Segoe UI', 9)).pack(side='left', padx=(0, 12))
    image_info = tk.StringVar(value=Path(fields['background_image'].get()).name or 'Sin fotografía')

    def choose_image():
        filename = filedialog.askopenfilename(parent=window, title='Elegir fondo de portada',
            filetypes=[('Fotografías', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.heif')])
        if not filename:
            return
        try:
            src = Path(filename)
            with Image.open(src) as image:
                image.verify()
            dest = image_dir / f'fondo_{uuid.uuid4().hex}{src.suffix.lower()}'
            shutil.copyfile(src, dest)
            fields['background_image'].set(str(dest))
            fields['background_type'].set('imagen')
            image_info.set(src.name)
        except Exception as exc:
            messagebox.showerror('Fondo de página', f'No se pudo abrir la fotografía: {exc}', parent=window)
    row_image = tk.Frame(left, bg=SURFACE)
    row_image.pack(fill='x', pady=(5,0))
    tk.Button(row_image, text='Elegir foto…', command=choose_image,
              bg=PANEL, fg=TEXT, relief='flat', padx=9, pady=5, cursor='hand2').pack(side='left')
    tk.Label(row_image, textvariable=image_info, bg=SURFACE, fg=MUTED,
             font=('Segoe UI', 8), width=21, anchor='w').pack(side='left', padx=(7,0))

    def text_input(element, caption):
        label(caption)
        row = tk.Frame(left, bg=SURFACE)
        row.pack(fill='x')
        tk.Checkbutton(row, text='Mostrar', variable=fields['show_' + element],
                       bg=SURFACE, fg=TEXT, activebackground=SURFACE,
                       activeforeground=TEXT, selectcolor=PANEL).pack(side='left')
        ent = tk.Entry(left, textvariable=fields[element], bg=PANEL, fg=TEXT,
                       insertbackground=ACCENT, relief='flat', font=('Segoe UI', 10))
        ent.pack(fill='x', ipady=5)
        return ent
    def size_control(element, caption, smallest, largest):
        label(caption + ' (% de la zona de texto)')
        row = tk.Frame(left, bg=SURFACE)
        row.pack(fill='x')
        slider = tk.Scale(row, variable=fields[element + '_size'], from_=smallest, to=largest,
                          showvalue=False, orient='horizontal', bg=SURFACE, fg=TEXT,
                          activebackground=ACCENT, highlightthickness=0, troughcolor=PANEL)
        slider.pack(side='left', fill='x', expand=True)
        tk.Spinbox(row, from_=smallest, to=largest, increment=1,
                   textvariable=fields[element + '_size'], width=3,
                   bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                   buttonbackground=PANEL, relief='flat', justify='center',
                   font=('Segoe UI', 10)).pack(side='right', padx=(9,0))

    text_input('title', 'TÍTULO (OPCIONAL)')
    select('TIPOGRAFÍA DEL TÍTULO', fields['title_font'], list(FONT_CHOICES))
    color_button('Color del título', 'text_color')
    size_control('title', 'Tamaño del título', 3, 24)
    text_input('subtitle', 'SUBTÍTULO (OPCIONAL)')
    select('TIPOGRAFÍA DEL SUBTÍTULO', fields['subtitle_font'], list(FONT_CHOICES))
    color_button('Color del subtítulo', 'subtitle_color')
    size_control('subtitle', 'Tamaño del subtítulo', 2, 18)

    tk.Label(right, text='VISTA PREVIA · POSICIÓN LIBRE', bg=SURFACE, fg=TEXT,
             font=('Segoe UI', 11, 'bold')).pack(anchor='w')
    pick = tk.Frame(right, bg=SURFACE)
    pick.pack(fill='x', pady=(8,4))
    for text, key in [('Título', 'title'), ('Subtítulo', 'subtitle'), ('Fotografía', 'image')]:
        tk.Radiobutton(pick, text=text, variable=focused, value=key, bg=SURFACE,
                       fg=TEXT, selectcolor=PANEL, activebackground=SURFACE,
                       activeforeground=ACCENT, font=('Segoe UI', 9)).pack(side='left', padx=(0,10))
    tk.Label(right, text='Haz clic donde quieras colocar el elemento elegido y arrástralo con precisión.',
             bg=SURFACE, fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w', pady=(0,5))
    photo_controls = tk.Frame(right,bg=SURFACE)
    photo_controls.pack(fill='x',pady=(3,8))
    tk.Label(photo_controls,text='FOTO:',bg=SURFACE,fg=MUTED,font=('Segoe UI',9,'bold')).pack(side='left')
    ttk.Combobox(photo_controls,values=['Encajar','Cubrir','Libre'],state='readonly',
                 textvariable=fields['image_mode'],width=12).pack(side='left',padx=(8,12))
    tk.Checkbutton(photo_controls,text='Mantener proporción en escala libre',
                   variable=linked_scale,bg=SURFACE,fg=TEXT,selectcolor=PANEL,
                   activebackground=SURFACE,activeforeground=ACCENT,
                   font=('Segoe UI',9)).pack(side='left')

    zoom_controls = tk.Frame(right,bg=SURFACE)
    zoom_controls.pack(fill='x',pady=(0,6))
    tk.Label(zoom_controls,text='Ancho',bg=SURFACE,fg=MUTED,font=('Segoe UI',9)).grid(row=0,column=0,sticky='w')
    tk.Scale(zoom_controls,from_=.25,to=3.0,resolution=.05,variable=fields['image_zoom_x'],
             orient='horizontal',bg=SURFACE,fg=TEXT,troughcolor=PANEL,
             highlightthickness=0,length=165).grid(row=0,column=1,sticky='ew')
    tk.Label(zoom_controls,text='Alto',bg=SURFACE,fg=MUTED,font=('Segoe UI',9)).grid(row=0,column=2,sticky='w',padx=(12,0))
    tk.Scale(zoom_controls,from_=.25,to=3.0,resolution=.05,variable=fields['image_zoom_y'],
             orient='horizontal',bg=SURFACE,fg=TEXT,troughcolor=PANEL,
             highlightthickness=0,length=165).grid(row=0,column=3,sticky='ew')
    zoom_controls.columnconfigure(1,weight=1)
    zoom_controls.columnconfigure(3,weight=1)
    tk.Label(right,text='Libre: mueve la foto y ajusta ancho/alto. El espacio libre usa el color o difuminado elegido.',
             bg=SURFACE,fg=MUTED,font=('Segoe UI',8),wraplength=520,justify='left').pack(anchor='w',pady=(0,5))
    canvas = tk.Canvas(right, bg=PANEL, highlightthickness=0, cursor='fleur')
    canvas.pack(fill='both', expand=True)

    syncing = [False]
    def sync_zoom(source,target):
        if syncing[0] or not linked_scale.get() or fields['image_mode'].get() != 'Libre':
            return
        syncing[0] = True
        try:fields[target].set(fields[source].get())
        finally:syncing[0] = False
    fields['image_zoom_x'].trace_add('write',lambda *_:sync_zoom('image_zoom_x','image_zoom_y'))
    fields['image_zoom_y'].trace_add('write',lambda *_:sync_zoom('image_zoom_y','image_zoom_x'))


    def draft():
        return validate_special_spec({
            'kind': fields['kind'].get(), 'theme': CUSTOM_THEME,
            'title': fields['title'].get(), 'subtitle': fields['subtitle'].get(),
            'background_type': fields['background_type'].get(),
            'background_image': fields['background_image'].get(),
            'background_color': fields['background_color'].get(),
            'background_fill': fields['background_fill'].get(),
            'text_color': fields['text_color'].get(),
            'subtitle_color': fields['subtitle_color'].get(),
            'title_size': fields['title_size'].get(), 'subtitle_size': fields['subtitle_size'].get(),
            'title_font': fields['title_font'].get(),
            'subtitle_font': fields['subtitle_font'].get(),
            'show_title': fields['show_title'].get(), 'show_subtitle': fields['show_subtitle'].get(),
            'image_mode': fields['image_mode'].get(),
            'image_zoom_x': fields['image_zoom_x'].get(),
            'image_zoom_y': fields['image_zoom_y'].get(),
            'image_x': fields['image_x'].get(),
            'image_y': fields['image_y'].get(),
            **positions,
        })

    def preview_source(source_name: str) -> str:
        """Una imagen ligera solo para la vista; nunca se guarda en el proyecto."""
        if sample_image[0] == source_name and sample_image[1] is not None:
            return str(sample_image[1])
        if sample_image[1] is not None:
            try: sample_image[1].unlink(missing_ok=True)
            except OSError: pass
            sample_image[:] = [None, None]
        if not source_name:
            return ''
        with Image.open(source_name) as original:
            small = ImageOps.exif_transpose(original).convert('RGB')
            small.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        dest = image_dir / f'_vista_editor_{uuid.uuid4().hex}.jpg'
        try:
            small.save(dest, 'JPEG', quality=93)
        finally:
            small.close()
        sample_image[:] = [source_name, dest]
        return str(dest)

    def refresh():
        refresh_job[0] = None
        if not canvas.winfo_exists():
            return
        try:
            spec = draft()
            ww = max(40, canvas.winfo_width()-12)
            hh = max(40, canvas.winfo_height()-12)
            p_w, p_h = page_size
            scale = min(ww / p_w, hh / p_h)
            iw, ih = max(80,int(p_w * scale)), max(80,int(p_h * scale))
            canvas_box[:] = ((canvas.winfo_width()-iw)//2, (canvas.winfo_height()-ih)//2, iw, ih)
            safe = printable_box((iw,ih), physical_mm, binding=True) if binding else (0,0,iw,ih)
            preview_spec = dict(spec)
            img_for_render = None
            blurred_for_render = None
            if spec['background_type'] == 'imagen':
                preview_path = preview_source(spec['background_image'])
                preview_spec['background_image'] = preview_path
                if source_cache[0] != preview_path:
                    if source_cache[1] is not None:
                        source_cache[1].close()
                    with Image.open(preview_path) as loaded:
                        source_cache[1] = loaded.convert('RGB')
                    source_cache[0] = preview_path
                    if blurred_cache[1] is not None:
                        blurred_cache[1].close()
                        blurred_cache[:] = [None, None]
                img_for_render = source_cache[1]
                if spec['background_fill'] == 'blurred':
                    blur_key = (preview_path, iw, ih)
                    if blur_key != blurred_cache[0] or blurred_cache[1] is None:
                        from special_pages import _blurred_page_base
                        new_blur = _blurred_page_base(img_for_render, (iw,ih))
                        if blurred_cache[1] is not None:
                            blurred_cache[1].close()
                        blurred_cache[:] = [blur_key, new_blur]
                    blurred_for_render = blurred_cache[1]
            bg_fields = ('background_type', 'background_color', 'background_fill',
                         'background_image', 'image_mode', 'image_zoom_x', 'image_zoom_y',
                         'image_x', 'image_y')
            signature = ((iw, ih), tuple(preview_spec.get(key) for key in bg_fields))
            if signature != bg_cache[0] or bg_cache[1] is None:
                fresh = render_custom_background(preview_spec, (iw, ih),
                                                  source_image=img_for_render,
                                                  blurred_base=blurred_for_render)
                if bg_cache[1] is not None:
                    bg_cache[1].close()
                bg_cache[:] = [signature, fresh]
            # Mover el texto ya NO vuelve a abrir ni a ampliar la fotografía.
            page = bg_cache[1].copy()
            try:
                draw_custom_text(page, spec, safe)
                photo = ImageTk.PhotoImage(page)
            finally:
                page.close()
            preview_img[0] = photo
            canvas.delete('all')
            ox,oy,_,_ = canvas_box
            canvas.create_image(ox,oy,image=photo,anchor='nw')
            x0,y0,x1,y1 = safe
            canvas.create_rectangle(ox+x0,oy+y0,ox+x1,oy+y1,
                                    outline=ACCENT, dash=(5,5), width=1)
            label_key = focused.get()
            active_label = {'title':'TÍTULO','subtitle':'SUBTÍTULO','image':'FOTOGRAFÍA'}[label_key]
            canvas.create_text(ox+9,oy+12,text=active_label,fill=ACCENT,
                               anchor='w',font=('Segoe UI',8,'bold'))
        except Exception:
            canvas.delete('all')
            canvas.create_text(120,80,text='Elige una foto válida para mostrar la vista previa.',
                               fill=MUTED,anchor='w')

    def schedule(*_):
        # Un único fotograma en cola: no esperar 130 ms tras el ÚLTIMO evento.
        # Los arrastres rápidos reciben respuesta continua sin saturar Tk.
        if refresh_job[0] is None and window.winfo_exists():
            refresh_job[0] = window.after(PREVIEW_FRAME_MS, refresh)

    def sync_page_settings(*_):
        nonlocal physical_mm, page_size, binding
        if page_settings is None or not window.winfo_exists():
            return
        new_mm, new_binding = page_settings()
        if new_mm == physical_mm and new_binding == binding:
            return
        physical_mm = tuple(new_mm)
        binding = bool(new_binding)
        page_size = (max(1, round(physical_mm[0]*4)),
                     max(1, round(physical_mm[1]*4)))
        window.revelo_page_mm = physical_mm
        schedule()

    def on_drag(event):
        key = focused.get()
        ox,oy,iw,ih = canvas_box
        if iw <= 10 or ih <= 10:
            return
        if key == 'image':
            if fields['background_type'].get() != 'imagen':
                return
            fields['image_mode'].set('Libre')
            fields['image_x'].set(round(min(1,max(0,(event.x-ox)/iw)),5))
            fields['image_y'].set(round(min(1,max(0,(event.y-oy)/ih)),5))
        else:
            if not fields['show_'+key].get() or not fields[key].get():
                return
            safe=printable_box((iw,ih),physical_mm,binding=True) if binding else (0,0,iw,ih)
            x0,y0,x1,y1=safe
            # Sin cuadrículas, nodos ni pasos: píxeles continuos de la vista.
            positions[key+'_x']=round(min(1,max(0,(event.x-ox-x0)/max(1,x1-x0))),5)
            positions[key+'_y']=round(min(1,max(0,(event.y-oy-y0)/max(1,y1-y0))),5)
        schedule()

    canvas.bind('<Button-1>', on_drag)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<Configure>', schedule)
    for var in fields.values():
        var.trace_add('write', schedule)
    focused.trace_add('write', schedule)

    def save():
        try:
            sync_page_settings()
            spec=draft()
            # Valida también la foto del fondo antes de confirmar.
            test=render_special_page(spec, (round(physical_mm[0]*2), round(physical_mm[1]*2)))
            test.close()
            on_save(spec)
        except Exception as exc:
            messagebox.showwarning('Revelo · Página personalizada', str(exc), parent=window)
            return
        window.destroy()

    def editor_destroyed(event):
        if event.widget is not window:
            return
        for wheel_event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            try: window.unbind_class(wheel_tag, wheel_event)
            except tk.TclError: pass
        for var, trace in setting_traces:
            try: var.trace_remove('write', trace)
            except tk.TclError: pass
        if refresh_job[0] is not None:
            try:window.after_cancel(refresh_job[0])
            except tk.TclError:pass
            refresh_job[0] = None
        if bg_cache[1] is not None:
            bg_cache[1].close()
            bg_cache[1] = None
        if source_cache[1] is not None:
            source_cache[1].close()
            source_cache[1] = None
        if blurred_cache[1] is not None:
            blurred_cache[1].close()
            blurred_cache[1] = None
        if sample_image[1] is not None:
            try: sample_image[1].unlink(missing_ok=True)
            except OSError: pass

    window.bind('<Destroy>', editor_destroyed, add='+')
    for var in settings_vars:
        setting_traces.append((var, var.trace_add('write', sync_page_settings)))
    tk.Label(buttons, text='Puedes mover esta ventana y cambiar el papel en Revelo.',
             bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='left')
    tk.Button(buttons, text='Guardar página personalizada', command=save,
              bg=ACCENT, fg=BG, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=20, pady=9).pack(side='right', padx=(0,9))
    register_scroll_widgets(rail)
    window.after(30, refresh)
    return window
