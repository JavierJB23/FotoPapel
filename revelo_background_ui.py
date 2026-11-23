"""Editor de fondos individuales, integrado en el estilo editorial de Revelo."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog

from PIL import Image, ImageTk
from revelo_backgrounds import PRESETS, validate_background_spec
from editorial_theme import apply_window_skin
import revelo_dialogs as messagebox

BG='#081928';SURFACE='#103044';PANEL='#193A4E';ACCENT='#4CE8D4'
TEXT='#F1F6FB';MUTED='#9CB1C7';WARNING='#F8CB82'
INHERIT='Usar fondo general'
CUSTOM='Color personalizado'
PHOTO='Imagen personalizada'
BLUR='Difuminado de la foto'
NONE='Sin fondo adicional'


def _label(parent, text, size=10, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                    font=('Segoe UI',size,'bold' if bold else 'normal'),**kwargs)


def _contrast_fg(background: str) -> str:
    """Texto oscuro sobre colores claros y blanco sobre colores oscuros (sRGB)."""
    from PIL import ImageColor
    red,green,blue=ImageColor.getrgb(background)
    linear=[(v/255/12.92 if v/255<=0.04045 else
             ((v/255+0.055)/1.055)**2.4) for v in (red,green,blue)]
    lightness=.2126*linear[0]+.7152*linear[1]+.0722*linear[2]
    return '#10202D' if lightness>=.36 else '#FFFFFF'


def open_background_editor(app, selected_path=None):
    """Abre la configuración de fondos, sin alterar los datos hasta Guardar."""
    if app.is_busy:
        return
    previous=getattr(app,'background_window',None)
    if previous is not None and previous.winfo_exists():
        previous.lift();previous.focus_set();return previous
    win=tk.Toplevel(app.root)
    app.background_window=win
    win.title('Revelo · Fondos por fotografía')
    win.geometry('1040x700')
    win.minsize(790,570)
    win.configure(bg=BG)
    try:
        from main import app_asset
        import sys
        if sys.platform=='win32' and app_asset('icono.ico').exists():
            win.iconbitmap(str(app_asset('icono.ico')))
    except (OSError,tk.TclError):
        pass
    heading=tk.Frame(win,bg=BG,padx=24,pady=17);heading.pack(fill='x')
    _label(heading,'FONDOS INDIVIDUALES',size=18,bold=True).pack(anchor='w')
    _label(heading,'Un fondo común para todas las fotos, o uno diferente para cada una. '
           'La opacidad permite crear marcas de agua.',size=10,color=MUTED,
           wraplength=940,justify='left').pack(anchor='w',pady=(6,0))

    main=tk.Frame(win,bg=BG,padx=20);main.pack(fill='both',expand=True)
    selector=tk.Frame(main,bg=SURFACE,padx=12,pady=13)
    selector.pack(side='left',fill='y',padx=(0,12))
    _label(selector,'APLICAR A',bold=True,color=ACCENT).pack(anchor='w',pady=(0,8))
    listbox=tk.Listbox(selector,width=25,bg=PANEL,fg=TEXT,
                       selectbackground='#236A6E',selectforeground='white',
                       activestyle='none',relief='flat',borderwidth=0,
                       highlightthickness=0,exportselection=False,font=('Segoe UI',10))
    listbox.pack(fill='both',expand=True)
    photo_paths=[p for p in app.paths if p not in app.special_pages]
    targets=[None,*photo_paths]
    global_spec=[validate_background_spec(getattr(app,'background_global',{}))]
    local_specs={p:validate_background_spec(s) for p,s in
                 getattr(app,'background_overrides',{}).items() if p in photo_paths}
    def row_text(p):
        if p is None:
            return '🌐  Todas las fotografías'
        name=app.path_labels.get(p,p.name)
        return ('●  ' if local_specs.get(p) else '   ')+(name[:29]+'…' if len(name)>30 else name)
    def redraw_names():
        selected=listbox.curselection()
        listbox.delete(0,'end')
        for p in targets:listbox.insert('end',row_text(p))
        listbox.selection_set(selected[0] if selected else 0)
    redraw_names()
    _label(selector,'● = Fondo propio',size=9,color=MUTED).pack(anchor='w',pady=(9,0))
    _label(selector,'Portadas y separadores tienen\nsu propio editor.',size=9,color=MUTED,
           justify='left').pack(anchor='w',pady=(7,0))

    middle=tk.Frame(main,bg=SURFACE,padx=16,pady=13,width=304)
    middle.pack(side='left',fill='y',padx=(0,12));middle.pack_propagate(False)
    _label(middle,'PERSONALIZAR FONDO',color=ACCENT,bold=True).pack(anchor='w',pady=(0,12))
    mode=tk.StringVar(value=INHERIT)
    opacity=tk.IntVar(value=100)
    fit=tk.StringVar(value='Cubrir')
    color=["#FFFFFF"]
    image=[""]
    selected=[None]
    syncing=[False]
    preview_job=[None]
    _label(middle,'ESTILO',size=9,color=MUTED,bold=True).pack(anchor='w',pady=(0,5))
    modes=[INHERIT,*PRESETS.keys(),CUSTOM,PHOTO,BLUR,NONE]
    mode_widget=ttk.Combobox(middle,textvariable=mode,values=modes,state='readonly',width=29)
    mode_widget.pack(fill='x',pady=(0,13))
    _label(middle,'OPACIDAD · 0 % INVISIBLE / 100 % OPACO',size=9,color=MUTED,bold=True,
           wraplength=258,justify='left').pack(anchor='w')
    scale=tk.Scale(middle,from_=0,to=100,variable=opacity,orient='horizontal',
                   resolution=1,bg=SURFACE,fg=ACCENT,troughcolor=PANEL,activebackground=ACCENT,
                   showvalue=True,highlightthickness=0,length=265)
    scale.pack(fill='x',pady=(0,10))
    color_row=tk.Frame(middle,bg=SURFACE);color_row.pack(fill='x',pady=(0,12))
    def update_color_chip():
        """Contraste legible del botón de color, en todos los fondos."""
        foreground=_contrast_fg(color[0])
        chip.configure(bg=color[0],fg=foreground,activeforeground=foreground)

    def choose_color():
        picked=colorchooser.askcolor(color=color[0],parent=win,title='Revelo · Color de fondo')
        if picked and picked[1]:
            color[0]=picked[1].upper();update_color_chip();changed()
    chip=tk.Button(color_row,text='Elegir color…',bg=PANEL,fg=TEXT,
                   activebackground=PANEL,command=choose_color,relief='flat',padx=8,pady=8)
    chip.pack(fill='x')
    chosen_name=tk.StringVar(value='Sin imagen')
    def choose_photo():
        file=filedialog.askopenfilename(parent=win,title='Imagen de fondo',
             filetypes=[('Imágenes','*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.heif')])
        if not file:return
        try:
            from PIL import Image
            path=Path(file)
            if path.stat().st_size>150*1024*1024:
                raise ValueError('El archivo supera 150 MB')
            with Image.open(path) as sample:
                sample.verify()
        except (OSError,ValueError) as exc:
            messagebox.showwarning('Imagen de fondo',str(exc),parent=win)
            return
        image[0]=file;chosen_name.set(path.name);changed()
    choose_btn=tk.Button(middle,text='Elegir imagen de fondo…',command=choose_photo,
                         bg=PANEL,fg=TEXT,activebackground=PANEL,relief='flat',padx=8,pady=8)
    choose_btn.pack(fill='x')
    _label(middle,'',size=9,color=MUTED,textvariable=chosen_name,
           anchor='w',wraplength=260,justify='left').pack(fill='x',pady=(4,12))
    _label(middle,'AJUSTE DE LA IMAGEN DE FONDO',color=MUTED,size=9,bold=True,
           wraplength=250,justify='left').pack(anchor='w',pady=(0,4))
    ttk.Combobox(middle,textvariable=fit,values=['Cubrir','Ajustar'],
                 state='readonly',width=20).pack(fill='x')
    _label(middle,'Cubrir: llena todo el espacio.\nAjustar: mantiene la imagen entera.',
           size=9,color=MUTED,justify='left').pack(anchor='w',pady=(9,0))
    _label(middle,'La imagen original nunca se modifica.',size=9,color=ACCENT,
           wraplength=260,justify='left').pack(anchor='w',side='bottom',pady=(16,0))

    viewer=tk.Frame(main,bg=SURFACE,padx=13,pady=13)
    viewer.pack(side='left',fill='both',expand=True)
    _label(viewer,'VISTA PREVIA REAL',color=ACCENT,bold=True).pack(anchor='w',pady=(0,8))
    canvas=tk.Canvas(viewer,bg='#142A3A',highlightthickness=0)
    canvas.pack(fill='both',expand=True)
    details=tk.StringVar(value='Elige un fondo para ver el resultado.')
    _label(viewer,'',size=9,color=MUTED,textvariable=details,wraplength=330,
           justify='left').pack(fill='x',pady=(8,0))
    preview_image=[None]

    def current_spec():
        value=mode.get()
        if value==INHERIT:return {}
        mapped=({'mode':'Color','color':PRESETS[value]} if value in PRESETS else
                {'mode':'Color','color':color[0]} if value==CUSTOM else
                {'mode':'Imagen','image':image[0],'color':color[0]} if value==PHOTO else
                {'mode':'Difuminado'} if value==BLUR else
                {'mode':'Sin fondo adicional'})
        return validate_background_spec({**mapped,'opacity':opacity.get(),'fit':fit.get()})

    def store(_evt=None):
        if syncing[0]:return
        # Permitir seleccionar Imagen antes de elegir el archivo.
        try:spec=current_spec()
        except ValueError:
            spec={'mode':'Imagen','image':image[0],'opacity':opacity.get(),
                  'fit':fit.get(),'color':color[0]}
        if selected[0] is None:global_spec[0]=spec
        elif spec:local_specs[selected[0]]=spec
        else:local_specs.pop(selected[0],None)
        redraw_names()
        schedule_preview()

    def load(p):
        syncing[0]=True
        selected[0]=p
        spec=global_spec[0] if p is None else local_specs.get(p,{})
        kind=spec.get('mode','Heredar')
        color[0]=spec.get('color','#FFFFFF')
        image[0]=spec.get('image','')
        if kind=='Color':
            label=next((key for key,hexval in PRESETS.items()
                        if hexval.upper()==color[0].upper()),CUSTOM)
        else:label={'Heredar':INHERIT,'Imagen':PHOTO,'Difuminado':BLUR,
                    'Sin fondo adicional':NONE}.get(kind,INHERIT)
        mode.set(label)
        opacity.set(spec.get('opacity',100))
        fit.set(spec.get('fit','Cubrir'))
        chosen_name.set(Path(image[0]).name if image[0] else 'Sin imagen')
        update_color_chip()
        syncing[0]=False
        refresh_controls();schedule_preview()

    def refresh_controls(*_):
        value=mode.get()
        chip.configure(state='normal' if value==CUSTOM else 'disabled')
        choose_btn.configure(state='normal' if value==PHOTO else 'disabled')
        if selected[0] is None and value==NONE:
            mode.set(INHERIT)

    def selected_change(_evt=None):
        if not listbox.curselection():return
        load(targets[listbox.curselection()[0]])

    def preview_now():
        preview_job[0]=None
        if not win.winfo_exists():return
        canvas.delete('all')
        paths=photo_paths
        if not paths:
            canvas.create_text(25,35,text='Añade fotos al proyecto para ver el fondo.',
                               fill=MUTED,anchor='nw',width=max(200,canvas.winfo_width()-40))
            return
        p=selected[0] if selected[0] is not None else paths[0]
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if w<50 or h<50:return
        opts=app._options()
        # Al abrir «Personalizado» desde un color general, la vista previa
        # conserva ese mismo color hasta que el usuario pulse Guardar.
        # Cancelar no modifica ni la hoja ni las excepciones individuales.
        previous=getattr(app,'_background_pending_custom_from',None)
        if previous in PRESETS:
            opts=replace(opts,paper_background='Personalizado',
                         paper_background_color=PRESETS[previous])
        elif previous=='Difuminado':
            opts=replace(opts,paper_background='Difuminado')
        groups=list(app._groups())
        index,group=next(((idx,group) for idx,group in enumerate(groups) if p in group),
                         (0,(p,)))
        proposed_global=global_spec[0]
        proposed_local=local_specs.copy()
        try:
            opts=replace(opts,
                background_global=validate_background_spec(proposed_global),
                background_overrides={k:validate_background_spec(v) for k,v in proposed_local.items()})
            from processor import render_layout_page
            render,_,_=render_layout_page(group,opts,page_index=index,
                                          preview_max_size=(max(60,w-25),max(60,h-25)))
        except (OSError,ValueError,RuntimeError) as exc:
            details.set('Vista previa: '+str(exc))
            return
        try:
            preview_image[0]=ImageTk.PhotoImage(render)
            canvas.create_image(w//2,h//2,anchor='center',image=preview_image[0])
        finally:render.close()
        details.set('Fotografía: '+app.path_labels.get(p,p.name)+
                    ('  ·  Activa «Ajustar (sin recortar)» para ver estos fondos.'
                     if opts.fit!='Ajustar (sin recortar)' else
                     '  ·  Hoja completa: composición idéntica a la exportación.'))

    def schedule_preview(*_):
        if preview_job[0] is not None:
            try:win.after_cancel(preview_job[0])
            except tk.TclError:pass
        preview_job[0]=win.after(110,preview_now)

    def changed(*_):
        refresh_controls()
        store()
    listbox.bind('<<ListboxSelect>>',selected_change)
    mode.trace_add('write',changed)
    opacity.trace_add('write',changed)
    fit.trace_add('write',changed)
    canvas.bind('<Configure>',schedule_preview)

    footer=tk.Frame(win,bg=BG,padx=22,pady=15);footer.pack(fill='x')
    _label(footer,'0 % = invisible · 100 % = completamente visible. '
           'También funciona con colores y fotos de fondo.',size=9,color=MUTED,
           wraplength=580,justify='left').pack(side='left')
    def close():
        if preview_job[0] is not None:
            try:win.after_cancel(preview_job[0])
            except tk.TclError:pass
        app.background_window=None
        from revelo_background_control import cancel_custom_choice
        cancel_custom_choice(app)
        win.destroy()
    def save():
        store()
        try:
            global_saved=validate_background_spec(global_spec[0])
            local_saved={p:validate_background_spec(s) for p,s in local_specs.items()}
            for spec in [global_saved,*local_saved.values()]:
                if spec.get('mode')=='Imagen':
                    path=Path(spec['image'])
                    if not path.is_file() or path.stat().st_size>150*1024*1024:
                        raise ValueError('La fotografía de fondo no existe o es demasiado grande.')
        except (ValueError,OSError) as exc:
            messagebox.showwarning('Fondos individuales',str(exc),parent=win)
            return
        app.background_global=global_saved
        app.background_overrides={p:s for p,s in local_saved.items() if s}
        from revelo_background_control import commit_custom_editor
        commit_custom_editor(app, global_saved, app.background_overrides)
        app.thumbnails.clear();app.thumbnails_small.clear();app.sheet_thumbnails.clear()
        close()
        app.render_library();app.render_order()
        if app.preview_window is not None and app.preview_window.winfo_exists():
            app._show_preview_page()
        app.feedback.set('Fondos individuales y opacidades guardados correctamente.')
    def mkbutton(title,fn,accent=False):
        return tk.Button(footer,text=title,command=fn,bg=ACCENT if accent else PANEL,
                         fg=BG if accent else TEXT,relief='flat',padx=15,pady=8,
                         font=('Segoe UI',10,'bold'),cursor='hand2')
    mkbutton('Guardar fondos',save,True).pack(side='right')
    mkbutton('Cancelar',close).pack(side='right',padx=(0,10))
    win.protocol('WM_DELETE_WINDOW',close)
    index=targets.index(selected_path) if selected_path in targets else 0
    listbox.selection_clear(0,'end');listbox.selection_set(index);listbox.see(index)
    load(targets[index])
    apply_window_skin(win,compact=True)
    return win
