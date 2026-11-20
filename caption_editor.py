"""Editor de texto/pies de foto de Revelo 1.7.1.

El texto nunca se 'quema' en la fotografía fuente: se guarda como metadatos
reversibles y se compone sobre la página impresa con advanced_layout.
"""
from __future__ import annotations

from pathlib import Path
from tkinter import ttk, colorchooser
import tkinter as tk

from PIL import Image, ImageTk

from advanced_layout import (CAPTION_PLACEMENTS, CAPTION_ALIGNMENTS,
                             validate_caption, draw_caption)
from special_pages import FONT_CHOICES
from processor import render_print_image, ExportOptions
import revelo_dialogs as messages

BG = '#0B1422'
SURFACE = '#142236'
SURFACE_2 = '#1B2D43'
ACCENT = '#4CD9B5'
TEXT = '#F1F6FB'
MUTED = '#A9BED0'


def _button(parent, label, command, *, accent=False):
    return tk.Button(parent,text=label,command=command,bg=ACCENT if accent else SURFACE_2,
                     fg=BG if accent else TEXT,activebackground='#6FE6CB' if accent else '#29425D',
                     activeforeground=BG if accent else TEXT, font=('Segoe UI',10,'bold'),
                     relief='flat',cursor='hand2',padx=12,pady=8)


def _label(parent, text, **kwargs):
    return tk.Label(parent,text=text,bg=BG,fg=MUTED,font=('Segoe UI',9,'bold'),anchor='w',**kwargs)


def _edit_positions(parent: tk.Toplevel, path: Path, spec: dict, opts: ExportOptions,
                    on_commit) -> None:
    """Ventana independiente con arrastre directo y guías centrales."""
    window=tk.Toplevel(parent)
    window.title('Revelo · Posición personalizada del texto')
    window.configure(bg=BG)
    max_h=max(530,window.winfo_screenheight()-110)
    window.geometry(f'970x{min(730,max_h)}')
    window.minsize(620,480)
    choice=tk.StringVar(value='title' if spec.get('title') else 'detail')
    positions={key:float(spec.get(key,default)) for key,default in (
        ('title_x',.5),('title_y',.84),('detail_x',.5),('detail_y',.92))}
    title=tk.Label(window,text='ARRASTRA TÍTULO Y DESCRIPCIÓN',bg=BG,fg=TEXT,
                   font=('Segoe UI',17,'bold'),anchor='w')
    title.pack(fill='x',padx=20,pady=(18,4))
    tk.Label(window,text='Selecciona el texto que deseas mover. Las líneas aguamarina indican el centro.',
             bg=BG,fg=MUTED,font=('Segoe UI',10),anchor='w').pack(fill='x',padx=20,pady=(0,10))
    toggles=tk.Frame(window,bg=BG)
    toggles.pack(fill='x',padx=20,pady=(0,9))
    for key,lab in (('title','Título'),('detail','Descripción')):
        tk.Radiobutton(toggles,text=lab,variable=choice,value=key,bg=BG,fg=TEXT,
                       selectcolor=SURFACE_2,activebackground=BG,
                       activeforeground=ACCENT,font=('Segoe UI',10)).pack(side='left',padx=(0,15))
    canvas=tk.Canvas(window,bg=SURFACE,highlightthickness=0)
    canvas.pack(fill='both',expand=True,padx=20)
    status=tk.StringVar(value='Posición personalizada · No se modificará el archivo original')
    tk.Label(window,textvariable=status,bg=BG,fg=ACCENT,
             font=('Segoe UI',9),anchor='w').pack(fill='x',padx=20,pady=(6,0))
    controls=tk.Frame(window,bg=BG)
    controls.pack(fill='x',padx=20,pady=13)

    try:
        base, (wmm,hmm), _=render_print_image(path,opts,preview_max_size=(780,570))
    except Exception as exc:
        window.destroy()
        messages.showwarning('Vista previa de foto',f'No se pudo abrir la imagen: {exc}',parent=parent)
        return
    current_photo=[None]
    bounds=[0,0,1,1]
    debounce=[None]
    last_guides=[False,False]

    def update_preview():
        debounce[0]=None
        if not window.winfo_exists():
            return
        cw,ch=canvas.winfo_width(),canvas.winfo_height()
        if cw<20 or ch<20:
            return
        scale=min((cw-36)/base.width,(ch-28)/base.height)
        dw=max(1,round(base.width*scale));dh=max(1,round(base.height*scale))
        x0=(cw-dw)//2;y0=(ch-dh)//2
        region=base.resize((dw,dh),Image.Resampling.LANCZOS)
        try:
            payload=dict(spec,placement='Personalizado',**positions)
            # Las posiciones son relativas a la imagen/celda, no a la pantalla.
            draw_caption(region,(0,0,dw,dh),payload,mode='Personalizado',px_per_mm=dw/wmm)
            current_photo[0]=ImageTk.PhotoImage(region)
        finally:
            region.close()
        canvas.delete('all')
        canvas.create_rectangle(x0+6,y0+7,x0+dw+6,y0+dh+7,fill='#080D15',outline='')
        canvas.create_image(x0,y0,image=current_photo[0],anchor='nw')
        canvas.create_rectangle(x0-1,y0-1,x0+dw+1,y0+dh+1,outline=ACCENT,width=1)
        bounds[:]=[x0,y0,dw,dh]
        if last_guides[0]:
            canvas.create_line(x0+dw/2,y0,x0+dw/2,y0+dh,fill=ACCENT,width=2,dash=(5,4))
        if last_guides[1]:
            canvas.create_line(x0,y0+dh/2,x0+dw,y0+dh/2,fill=ACCENT,width=2,dash=(5,4))

    def schedule(_event=None):
        if debounce[0] is not None:
            window.after_cancel(debounce[0])
        debounce[0]=window.after(17,update_preview)

    def set_position(event):
        x0,y0,w,h=bounds
        x=max(0,min(1,(event.x-x0)/max(1,w)))
        y=max(0,min(1,(event.y-y0)/max(1,h)))
        # Ajuste magnético en el eje central, sin obligar a usar una cuadrícula.
        last_guides[:]=[abs(x-.5)<.013,abs(y-.5)<.013]
        if last_guides[0]:x=.5
        if last_guides[1]:y=.5
        key=choice.get()
        positions[key+'_x']=round(x,5)
        positions[key+'_y']=round(y,5)
        status.set(f'{"Título" if key=="title" else "Descripción"}: X {x:.1%} · Y {y:.1%}')
        schedule()

    def close(commit=False):
        if commit:
            on_commit(dict(positions))
        if debounce[0] is not None:
            window.after_cancel(debounce[0])
        base.close()
        window.destroy()
        if parent.winfo_exists():
            parent.grab_set()

    canvas.bind('<Configure>',schedule)
    canvas.bind('<Button-1>',set_position)
    canvas.bind('<B1-Motion>',set_position)
    _button(controls,'Cancelar',lambda:close(False)).pack(side='right')
    _button(controls,'Aplicar posición',lambda:close(True),accent=True).pack(side='right',padx=8)
    window.bind('<Escape>',lambda _evt:close(False))
    window.protocol('WM_DELETE_WINDOW',lambda:close(False))
    window.grab_set()
    schedule()


def edit_caption(parent, path: Path, initial: dict | None,
                 opts: ExportOptions, on_save):
    spec=validate_caption(initial)
    dialog=tk.Toplevel(parent)
    dialog.title('Revelo · Texto y pie de foto')
    dialog.configure(bg=BG)
    height=min(735,max(550,dialog.winfo_screenheight()-105))
    dialog.geometry(f'680x{height}')
    dialog.minsize(510,490)
    title=tk.StringVar(value=spec.get('title',''))
    detail=tk.StringVar(value=spec.get('detail',''))
    placement=tk.StringVar(value=spec.get('placement','Debajo'))
    alignment=tk.StringVar(value=spec.get('align','Centro'))
    title_font=tk.StringVar(value=spec.get('title_font','Georgia'))
    detail_font=tk.StringVar(value=spec.get('detail_font','Georgia'))
    title_size=tk.StringVar(value=str(spec.get('title_size',14)))
    detail_size=tk.StringVar(value=str(spec.get('detail_size',10)))
    title_color=[spec.get('title_color','#FFFFFF' if placement.get()!='Debajo' else '#253447')]
    detail_color=[spec.get('detail_color','#FFFFFF' if placement.get()!='Debajo' else '#3D5160')]
    color_overrides={'title': 'title_color' in spec,'detail':'detail_color' in spec}
    color_buttons={}
    positions={k:spec.get(k,default) for k,default in (
        ('title_x',.5),('title_y',.84),('detail_x',.5),('detail_y',.92))}

    head=tk.Frame(dialog,bg=BG,padx=21,pady=13)
    head.pack(fill='x')
    tk.Label(head,text='TEXTO Y PIE DE FOTO',bg=BG,fg=TEXT,
             font=('Segoe UI',17,'bold')).pack(anchor='w')
    tk.Label(head,text='Texto transparente · Ajusta cada elemento a tu gusto.',
             bg=BG,fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',pady=(4,0))
    holder=tk.Frame(dialog,bg=SURFACE)
    holder.pack(fill='both',expand=True,padx=20,pady=4)
    sc=tk.Canvas(holder,bg=SURFACE,highlightthickness=0)
    scroll=ttk.Scrollbar(holder,orient='vertical',command=sc.yview)
    sc.configure(yscrollcommand=scroll.set)
    sc.pack(side='left',fill='both',expand=True)
    scroll.pack(side='right',fill='y')
    body=tk.Frame(sc,bg=SURFACE,padx=18,pady=14)
    winid=sc.create_window((0,0),window=body,anchor='nw')
    body.bind('<Configure>',lambda _ev:sc.configure(scrollregion=sc.bbox('all')))
    sc.bind('<Configure>',lambda ev:sc.itemconfigure(winid,width=ev.width))

    def heading(text):
        tk.Label(body,text=text,bg=SURFACE,fg=MUTED,anchor='w',
                 font=('Segoe UI',9,'bold')).pack(fill='x',pady=(11,5))

    def entry(var):
        widget=tk.Entry(body,textvariable=var,bg=SURFACE_2,fg=TEXT,
                        insertbackground=ACCENT,relief='flat',font=('Segoe UI',11))
        widget.pack(fill='x',ipady=8)
        return widget

    def combo(var,values):
        widget=ttk.Combobox(body,textvariable=var,values=values,state='readonly')
        widget.pack(fill='x')
        return widget

    def choose_color(color_box, button, label):
        chosen=colorchooser.askcolor(color=color_box[0],parent=dialog,title='Color de letra')[1]
        if chosen:
            color_overrides[label]=True
            color_box[0]=chosen.upper()
            button.configure(bg=chosen,activebackground=chosen,
                             fg='#101F2B' if sum(int(chosen[i:i+2],16) for i in (1,3,5))>380 else '#FFFFFF')

    heading('TÍTULO')
    entry(title)
    heading('DESCRIPCIÓN / LUGAR / FECHA')
    detail_input=tk.Text(body,height=3,bg=SURFACE_2,fg=TEXT,insertbackground=ACCENT,
                         relief='flat',font=('Segoe UI',11),wrap='word',padx=7,pady=6)
    detail_input.insert('1.0',detail.get())
    detail_input.pack(fill='x')
    heading('UBICACIÓN')
    place_combo=combo(placement,CAPTION_PLACEMENTS)
    tk.Label(body,text='Sin recuadros de fondo. En Personalizado puedes arrastrar ambos textos.',
             bg=SURFACE,fg=MUTED,font=('Segoe UI',9),anchor='w').pack(fill='x',pady=(5,0))

    def style_group(text,font_var,size_var,color_box,label):
        heading(text)
        f=tk.Frame(body,bg=SURFACE)
        f.pack(fill='x')
        tk.Label(f,text='Tipografía',bg=SURFACE,fg=MUTED,font=('Segoe UI',9)).pack(side='left')
        sel=ttk.Combobox(f,textvariable=font_var,values=list(FONT_CHOICES),state='readonly',width=23)
        sel.pack(side='left',padx=(12,14),fill='x',expand=True)
        tk.Label(f,text='pt',bg=SURFACE,fg=MUTED,font=('Segoe UI',9)).pack(side='right',padx=(4,0))
        sp=tk.Spinbox(f,from_=6,to=72,increment=1,textvariable=size_var,width=4,
                      bg=SURFACE_2,fg=TEXT,insertbackground=ACCENT,relief='flat',
                      font=('Segoe UI',10))
        sp.pack(side='right')
        b=_button(body,'Color del texto',None)
        b.configure(bg=color_box[0],fg='#111F2A' if sum(int(color_box[0][i:i+2],16) for i in (1,3,5))>380 else 'white',
                    command=lambda:choose_color(color_box,b,label))
        b.pack(anchor='w',pady=(8,2))
        color_buttons[label]=b

    style_group('TIPOGRAFÍA Y TAMAÑO DEL TÍTULO',title_font,title_size,title_color,'title')
    style_group('TIPOGRAFÍA Y TAMAÑO DE LA DESCRIPCIÓN',detail_font,detail_size,detail_color,'detail')
    heading('ALINEACIÓN')
    combo(alignment,CAPTION_ALIGNMENTS)
    custom_btn=_button(body,'◉  Abrir editor visual de posición',lambda:open_positions(),accent=True)
    custom_btn.pack(fill='x',pady=(16,5))

    def collect():
        try:
            data={'title':title.get(),'detail':detail_input.get('1.0','end-1c'),'placement':placement.get(),
                  'title_font':title_font.get(),'detail_font':detail_font.get(),
                  'title_size':int(title_size.get()),'detail_size':int(detail_size.get()),
                  'title_color':title_color[0],'detail_color':detail_color[0],
                  'align':alignment.get(),**positions}
            return validate_caption(data)
        except (ValueError,TypeError) as exc:
            messages.showwarning('Texto y pie de foto',f'Revisa el tamaño, posición o color: {exc}',parent=dialog)
            return None

    def open_positions():
        data=collect()
        if data is None:
            return
        if not (data['title'] or data['detail']):
            messages.showwarning('Texto y pie de foto','Escribe primero un título o una descripción.',parent=dialog)
            return
        dialog.grab_release()
        _edit_positions(dialog,path,data,opts,lambda updated:positions.update(updated))

    def update_custom_button(*_):
        custom_btn.configure(state='normal' if placement.get()=='Personalizado' else 'disabled')
        # Solo cambiar el color automáticamente si el usuario no lo eligió.
        defaults=('#253447','#3D5160') if placement.get()=='Debajo' else ('#FFFFFF','#FFFFFF')
        for label,box,value in (('title',title_color,defaults[0]),('detail',detail_color,defaults[1])):
            if not color_overrides[label]:
                box[0]=value
                btn=color_buttons[label]
                btn.configure(bg=value,fg='#111F2A' if sum(int(value[i:i+2],16) for i in (1,3,5))>380 else '#FFFFFF')

    placement.trace_add('write',update_custom_button)
    update_custom_button()
    place_combo.bind('<<ComboboxSelected>>',lambda _ev:dialog.after(120,open_positions) if placement.get()=='Personalizado' else None)

    # El scroll vertical es del formulario, nunca de los combobox ni spinbox.
    def scroll_panel(ev):
        delta=-1 if ev.delta>0 else 1
        sc.yview_scroll(delta*3,'units')
        return 'break'
    def bind_wheel(w):
        w.bind('<MouseWheel>',scroll_panel)
        for child in w.winfo_children():bind_wheel(child)
    bind_wheel(body)
    body.bind('<Configure>',lambda ev:(sc.configure(scrollregion=sc.bbox('all')),bind_wheel(body)))

    buttons=tk.Frame(dialog,bg=BG,padx=20,pady=13)
    buttons.pack(fill='x')
    def finish(save):
        if save:
            clean=collect()
            if clean is None:
                return
            on_save(clean)
        try:dialog.grab_release()
        except tk.TclError:pass
        dialog.destroy()
    _button(buttons,'Cancelar',lambda:finish(False)).pack(side='right')
    _button(buttons,'Guardar texto',lambda:finish(True),accent=True).pack(side='right',padx=9)
    dialog.bind('<Escape>',lambda _ev:finish(False))
    dialog.protocol('WM_DELETE_WINDOW',lambda:finish(False))
    dialog.grab_set()
    return dialog
