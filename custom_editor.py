"""Editor visual de portadas de Revelo: fondo libre y textos arrastrables."""
from __future__ import annotations

from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import uuid

import revelo_dialogs as messagebox

from PIL import Image, ImageTk
from special_pages import CUSTOM_THEME, validate_special_spec, render_special_page, KINDS
from processor import printable_box

BG = '#0B1422'
SURFACE = '#142236'
PANEL = '#1B2D43'
ACCENT = '#4CD9B5'
TEXT = '#F1F6FB'
MUTED = '#9CB1C7'


def editor_initial_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Calcula un tamaño compacto y deja espacio para la barra de tareas.

    Como las propiedades disponen de scroll, no se pierden controles al
    reducir la altura de la ventana en equipos con escalado de Windows.
    """
    width = min(1030, max(790, round(screen_width * .75)))
    height = min(680, max(510, round(screen_height * .72)))
    return width, height


def edit_custom_page(root: tk.Tk, *, initial: dict, image_dir: Path,
                     landscape: bool, binding: bool, on_save,
                     paper_dimensions_mm: tuple[float, float] | None = None):
    """Abre editor modal; llama on_save(spec) solamente tras pulsar Guardar."""
    image_dir.mkdir(parents=True, exist_ok=True)
    initial = dict(initial)
    initial['theme'] = CUSTOM_THEME
    initial.setdefault('background_type', 'color')
    initial.setdefault('background_image', '')
    initial.setdefault('background_color', '#F6EBDC')
    initial.setdefault('text_color', '#1B2D43')
    initial.setdefault('subtitle_color', '#334C63')
    initial.setdefault('title_size', 12)
    initial.setdefault('subtitle_size', 6)
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
    # Con escalado del 125/150 % el tamaño anterior podía ocultar el pie.
    # La vista previa se adapta y las opciones ya admiten scroll.
    editor_w, editor_h = editor_initial_size(
        window.winfo_screenwidth(), window.winfo_screenheight()
    )
    window.geometry(f'{editor_w}x{editor_h}')
    window.minsize(790, 510)
    window.configure(bg=BG)
    window.transient(root)

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
    def wheel(event):
        controls_canvas.yview_scroll(-int(event.delta / 120) if event.delta else 0, 'units')
    controls_canvas.bind('<MouseWheel>', wheel)
    left.bind('<MouseWheel>',wheel)
    right = tk.Frame(body, bg=SURFACE, padx=12, pady=12)
    right.pack(side='left', fill='both', expand=True)

    fields = {
        'kind': tk.StringVar(value=initial.get('kind', 'Separador')),
        'title': tk.StringVar(value=initial.get('title', '')),
        'subtitle': tk.StringVar(value=initial.get('subtitle', '')),
        'background_type': tk.StringVar(value=initial['background_type']),
        'background_image': tk.StringVar(value=initial['background_image']),
        'background_color': tk.StringVar(value=initial['background_color']),
        'text_color': tk.StringVar(value=initial['text_color']),
        'subtitle_color': tk.StringVar(value=initial['subtitle_color']),
        'title_size': tk.IntVar(value=initial['title_size']),
        'subtitle_size': tk.IntVar(value=initial['subtitle_size']),
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
    # La vista previa reproduce la relación de aspecto del papel elegido;
    # no usa una proporción fija de A5 ni la miniatura de una portada antigua.
    physical_mm = paper_dimensions_mm or ((210.0, 148.0) if landscape else (148.0, 210.0))
    page_size = (max(1, round(physical_mm[0] * 4)),
                 max(1, round(physical_mm[1] * 4)))
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

    def color_button(caption, field):
        row = tk.Frame(left, bg=SURFACE)
        row.pack(fill='x', pady=(6, 0))
        tk.Label(row, text=caption, fg=MUTED, bg=SURFACE,
                 font=('Segoe UI', 9)).pack(side='left')
        chip = tk.Button(row, text='Elegir color', bg=fields[field].get(),
                         fg='#111111' if sum(int(fields[field].get()[i:i+2],16) for i in (1,3,5)) > 425 else '#FFFFFF',
                         relief='flat', padx=8, pady=3, cursor='hand2')
        chip.pack(side='right')
        def choose():
            result = colorchooser.askcolor(color=fields[field].get(), parent=window,
                                          title='Revelo · ' + caption)
            if result and result[1]:
                fields[field].set(result[1].upper())
                chip.configure(bg=result[1],
                               fg='#111111' if sum(int(result[1][i:i+2],16) for i in (1,3,5)) > 425 else '#FFFFFF')
        chip.configure(command=choose)
        return chip

    color_button('Color bajo la foto', 'background_color')
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
    text_input('title', 'TÍTULO (OPCIONAL)')
    color_button('Color del título', 'text_color')
    label('Tamaño del título')
    tk.Scale(left, variable=fields['title_size'], from_=3, to=24, orient='horizontal',
             bg=SURFACE, fg=TEXT, activebackground=ACCENT,
             highlightthickness=0, troughcolor=PANEL).pack(fill='x')
    text_input('subtitle', 'SUBTÍTULO (OPCIONAL)')
    color_button('Color del subtítulo', 'subtitle_color')
    label('Tamaño del subtítulo')
    tk.Scale(left, variable=fields['subtitle_size'], from_=2, to=18, orient='horizontal',
             bg=SURFACE, fg=TEXT, activebackground=ACCENT,
             highlightthickness=0, troughcolor=PANEL).pack(fill='x')

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
    tk.Label(right,text='Libre: mueve la fotografía y ajusta ancho/alto. El color elegido rellena el espacio restante.',
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
            'text_color': fields['text_color'].get(),
            'subtitle_color': fields['subtitle_color'].get(),
            'title_size': fields['title_size'].get(), 'subtitle_size': fields['subtitle_size'].get(),
            'show_title': fields['show_title'].get(), 'show_subtitle': fields['show_subtitle'].get(),
            'image_mode': fields['image_mode'].get(),
            'image_zoom_x': fields['image_zoom_x'].get(),
            'image_zoom_y': fields['image_zoom_y'].get(),
            'image_x': fields['image_x'].get(),
            'image_y': fields['image_y'].get(),
            **positions,
        })

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
            if binding:
                safe = printable_box((iw,ih), physical_mm, binding=True)
            else:
                safe = (0,0,iw,ih)
            page = render_special_page(spec, (iw, ih), safe)
            photo = ImageTk.PhotoImage(page)
            page.close()
            preview_img[0] = photo
            canvas.delete('all')
            ox,oy,_,_ = canvas_box
            canvas.create_image(ox,oy,image=photo,anchor='nw')
            x0,y0,x1,y1 = safe
            canvas.create_rectangle(ox+x0,oy+y0,ox+x1,oy+y1,
                                    outline=ACCENT, dash=(5,5), width=1)
            # Etiqueta discreta del elemento seleccionado fuera del diseño.
            label_key = focused.get()
            active_label = {'title':'TÍTULO','subtitle':'SUBTÍTULO','image':'FOTOGRAFÍA'}[label_key]
            canvas.create_text(ox+9,oy+12,text=active_label,fill=ACCENT,
                               anchor='w',font=('Segoe UI',8,'bold'))
        except Exception:
            canvas.delete('all')
            canvas.create_text(120,80,text='Elige una foto válida para mostrar la vista previa.',
                               fill=MUTED,anchor='w')

    def schedule(*_):
        if refresh_job[0] is not None:
            try:window.after_cancel(refresh_job[0])
            except tk.TclError:pass
        refresh_job[0] = window.after(130, refresh)

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
            spec=draft()
            # Valida también la foto del fondo antes de confirmar.
            test=render_special_page(spec, (round(physical_mm[0]*2), round(physical_mm[1]*2)))
            test.close()
            on_save(spec)
        except Exception as exc:
            messagebox.showwarning('Revelo · Página personalizada', str(exc), parent=window)
            return
        window.destroy()
    tk.Button(buttons, text='Guardar página personalizada', command=save,
              bg=ACCENT, fg=BG, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=20, pady=9).pack(side='right', padx=(0,9))
    window.grab_set()
    window.after(300, refresh)
    return window
