"""Editor visual de portadas de Revelo: fondo libre y textos arrastrables."""
from __future__ import annotations

from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import uuid

from PIL import Image, ImageTk
from special_pages import CUSTOM_THEME, validate_special_spec, render_special_page, KINDS
from processor import printable_box

BG = '#0B1422'
SURFACE = '#142236'
PANEL = '#1B2D43'
ACCENT = '#4CD9B5'
TEXT = '#F1F6FB'
MUTED = '#9CB1C7'


def edit_custom_page(root: tk.Tk, *, initial: dict, image_dir: Path,
                     landscape: bool, binding: bool, on_save):
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

    window = tk.Toplevel(root)
    window.title('Revelo · Personalizar portada o separador')
    window.geometry('1060x790')
    window.minsize(900, 690)
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
    left = tk.Frame(body, bg=SURFACE, width=344, padx=15, pady=12)
    left.pack(side='left', fill='y', padx=(0, 14))
    left.pack_propagate(False)
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
    }
    positions = {key: float(initial[key]) for key in ('title_x', 'title_y', 'subtitle_x', 'subtitle_y')}
    focused = tk.StringVar(value='title')
    refresh_job = [None]
    preview_img = [None]
    page_size = (650, 850) if not landscape else (850, 650)
    canvas_box = [0, 0, 1, 1]
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

    color_button('Color del fondo', 'background_color')
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

    tk.Label(right, text='VISTA PREVIA · ARRASTRA LOS TEXTOS', bg=SURFACE, fg=TEXT,
             font=('Segoe UI', 11, 'bold')).pack(anchor='w')
    pick = tk.Frame(right, bg=SURFACE)
    pick.pack(fill='x', pady=(8,4))
    for text, key in [('Mover título', 'title'), ('Mover subtítulo', 'subtitle')]:
        tk.Radiobutton(pick, text=text, variable=focused, value=key, bg=SURFACE,
                       fg=TEXT, selectcolor=PANEL, activebackground=SURFACE,
                       activeforeground=ACCENT, font=('Segoe UI', 9)).pack(side='left', padx=(0,10))
    tk.Label(right, text='La zona interior protegida aparece con línea discontinua.',
             bg=SURFACE, fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w', pady=(0,5))
    canvas = tk.Canvas(right, bg=PANEL, highlightthickness=0, cursor='fleur')
    canvas.pack(fill='both', expand=True)

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
                safe = printable_box((iw,ih), (210,148) if landscape else (148,210), binding=True)
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
            for key,fg in (('title','#FCE39A'),('subtitle','#8AD9FE')):
                if spec.get('show_'+key) and spec.get(key):
                    cx=ox+x0+max(0,(x1-x0))*positions[key+'_x']
                    cy=oy+y0+max(0,(y1-y0))*positions[key+'_y']
                    radius=10 if focused.get() == key else 6
                    canvas.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,
                                       outline=fg, fill=fg if focused.get()==key else '',width=2)
                    canvas.create_text(cx,cy-16,text='T' if key=='title' else 'S',fill=fg,
                                       font=('Segoe UI', 10, 'bold'))
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
        if not fields['show_'+key].get() or not fields[key].get():
            return
        ox,oy,iw,ih=canvas_box
        if iw<=10 or ih<=10:
            return
        safe=printable_box((iw,ih),(210,148) if landscape else (148,210),binding=True) if binding else (0,0,iw,ih)
        x0,y0,x1,y1=safe
        positions[key+'_x']=round(min(.98,max(.02,(event.x-ox-x0)/max(1,x1-x0))),4)
        positions[key+'_y']=round(min(.98,max(.02,(event.y-oy-y0)/max(1,y1-y0))),4)
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
            test=render_special_page(spec, (360,260) if landscape else (260,360))
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
