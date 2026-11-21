"""Editor fotográfico visual de Revelo (Tkinter, totalmente local)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageOps, ImageTk

from photo_edits import DEFAULT, LIMITS, validate_edits, apply_edits, geometry_image, auto_white_crop, legacy_to_operations

BG='#0B1422'; PANEL='#142236'; PANEL2='#1B2D43'; BORDER='#304660'; CREAM='#F6E5C4'
ACCENT='#4CD9B5'; TEXT='#F2F7FC'; MUTED='#9FB6C9'

ASPECTS = {
    'Libre': None,
    'Original': 'original',
    '1:1 · Cuadrado': 1.0,
    '4:3': 4/3,
    '3:4': 3/4,
    '16:9': 16/9,
    '9:16': 9/16,
    'A4/A5 · Vertical': 210/297,
    'A4/A5 · Horizontal': 297/210,
    '10×15 · Vertical': 2/3,
    '10×15 · Horizontal': 3/2,
}


class PhotoEditor(tk.Toplevel):
    def __init__(self, master, path: Path, saved: dict | None, on_save,
                 *, pdf_flattened: bool = False, paper_options=None,
                 cover_spec=None, paper_mm=None):
        super().__init__(master)
        self.title('Revelo · Editar fotografía')
        self.configure(bg=BG)
        self.path=Path(path)
        self.on_save=on_save
        self.spec=legacy_to_operations(saved)
        self._source: Image.Image | None=None
        self._geometry: Image.Image | None=None
        self._display_photo: ImageTk.PhotoImage | None=None
        self._after_job=None
        self._box_px=(0,0,1,1)
        self._drag=None
        self.paper_options=paper_options
        self.cover_spec=cover_spec
        self.paper_mm=paper_mm
        self._page_view=False
        self._resize_start=None
        self._page_handle=(0,0)
        self._compare=False
        self._result=bool(self.spec['ops']) and self.spec['crop'] is None
        self._confirmed_crop=None
        self.crop_mode=tk.StringVar(value='Libre')
        self.status=tk.StringVar(value='Arrastra sobre la foto para recortar; también puedes mover las cuatro esquinas.')
        self.keep_ratio=tk.BooleanVar(value=True)
        self._slider_vars={}
        self._build()
        try:
            with Image.open(self.path) as original:
                self._source=ImageOps.exif_transpose(original).convert('RGB')
            if pdf_flattened:
                # Reutiliza la MISMA limpieza que el motor de impresión;
                # las coordenadas de recorte deben referirse al mismo contenido.
                from processor import _trim_revelo_like_page_background
                cleaned, _ = _trim_revelo_like_page_background(self._source)
                self._source.close()
                self._source = cleaned
            self._source.thumbnail((1650,1650),Image.Resampling.LANCZOS)
            self._render()
        except Exception as exc:
            from revelo_dialogs import showerror
            self.destroy()
            showerror('Editar fotografía',f'No se puede abrir la foto: {exc}')
            return
        self.bind('<Escape>',lambda _e:self.close())
        self.protocol('WM_DELETE_WINDOW',self.close)

    def _btn(self,parent,text,callback,*,accent=False):
        return tk.Button(parent,text=text,command=callback,font=('Segoe UI',10,'bold'),
                         bg=ACCENT if accent else PANEL2, fg=BG if accent else TEXT,
                         activebackground='#83EBD2' if accent else '#34506B',
                         activeforeground=BG if accent else TEXT, relief='flat',bd=0,
                         padx=12,pady=8,cursor='hand2')

    def _text(self,parent,text,*,font=10,color=TEXT,bold=False):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',font,'bold' if bold else 'normal'),anchor='w')

    def _build(self):
        self.update_idletasks()
        width=min(1360,max(980,self.winfo_screenwidth()-100))
        height=min(845,max(640,self.winfo_screenheight()-135))
        self.geometry(f'{width}x{height}+{max(0,(self.winfo_screenwidth()-width)//2)}+{max(0,(self.winfo_screenheight()-height)//2)}')
        self.minsize(875,590)
        header=tk.Frame(self,bg=BG,padx=19,pady=13)
        header.pack(fill='x')
        self._text(header,'EDITAR FOTOGRAFÍA',font=17,bold=True).pack(anchor='w')
        self._text(header,'Cambios reversibles · Los originales no se modifican · Recorta, gira y ajusta antes de imprimir',
                   color=MUTED).pack(anchor='w',pady=(4,0))
        bottom=tk.Frame(self,bg=BG,padx=18,pady=12)
        bottom.pack(side='bottom',fill='x')
        self._btn(bottom,'Guardar edición',self.save,accent=True).pack(side='right')
        self._btn(bottom,'Cancelar',self.close).pack(side='right',padx=(0,8))
        self._btn(bottom,'Restablecer original',self.reset).pack(side='left')
        self._text(bottom,'Mantén pulsado «Original» para comparar',color=MUTED).pack(side='left',padx=(18,0))

        frame=tk.Frame(self,bg=BG,padx=17)
        frame.pack(fill='both',expand=True,pady=(0,7))
        left=tk.Frame(frame,bg=PANEL,width=315)
        left.pack(side='left',fill='y',padx=(0,12))
        left.pack_propagate(False)
        self.scroll_canvas=tk.Canvas(left,bg=PANEL,bd=0,highlightthickness=0)
        bar=ttk.Scrollbar(left,orient='vertical',command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y')
        self.scroll_canvas.pack(side='left',fill='both',expand=True)
        inside=tk.Frame(self.scroll_canvas,bg=PANEL,padx=15,pady=13)
        self._inside=inside
        window=self.scroll_canvas.create_window((0,0),window=inside,anchor='nw')
        inside.bind('<Configure>',lambda _e:self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox('all')))
        self.scroll_canvas.bind('<Configure>',lambda e:self.scroll_canvas.itemconfigure(window,width=e.width))
        def wheel(event):
            self.scroll_canvas.yview_scroll(int(-event.delta/120) if event.delta else 0,'units')
            return 'break'
        self._wheel=wheel
        def bind_wheel(widget):
            widget.bind('<MouseWheel>',wheel)
            for child in widget.winfo_children():bind_wheel(child)
        self._bind_wheel=bind_wheel

        self._text(inside,'RECORTE',font=11,bold=True).pack(fill='x',pady=(0,7))
        self._text(inside,'Proporción de la selección',color=MUTED).pack(fill='x')
        combo=ttk.Combobox(inside,textvariable=self.crop_mode,values=list(ASPECTS),state='readonly',width=25)
        combo.pack(fill='x',pady=(3,8));combo.bind('<<ComboboxSelected>>',self._aspect_changed)
        tools=tk.Frame(inside,bg=PANEL)
        tools.pack(fill='x',pady=(1,6))
        self._btn(tools,'Quitar recorte',self._clear_crop).pack(side='left',padx=(0,5))
        self._btn(tools,'Quitar bordes blancos',self._auto_white).pack(side='left')
        helper=self._text(inside,'Arrastra para definir el recorte. Puedes ajustar sus esquinas.', color=MUTED)
        helper.configure(wraplength=266,justify='left')
        helper.pack(fill='x',pady=(0,12))
        self._text(inside,'ROTAR Y VOLTEAR',font=11,bold=True).pack(fill='x',pady=(0,8))
        rotate=tk.Frame(inside,bg=PANEL)
        rotate.pack(fill='x',pady=(0,8))
        self._btn(rotate,'↶ 90°',lambda:self._transform(-1)).pack(side='left',padx=(0,5))
        self._btn(rotate,'↷ 90°',lambda:self._transform(1)).pack(side='left',padx=(0,5))
        self._btn(rotate,'↔',lambda:self._transform('h')).pack(side='left',padx=(0,5))
        self._btn(rotate,'↕',lambda:self._transform('v')).pack(side='left')
        self._range(inside,'Enderezar', 'straighten', -15, 15, resolution=.1)
        self._text(inside,'TAMAÑO DE FOTO EN LA HOJA',font=11,bold=True).pack(fill='x',pady=(18,6))
        self._range(inside,'Escala de impresión', 'print_scale', .25, 1.50, resolution=.05)
        scale_note=self._text(inside,'1.00 es el tamaño normal. Puedes reducir o ampliar la foto al maquetar, sin modificar sus píxeles.',color=MUTED)
        scale_note.configure(wraplength=270,justify='left')
        scale_note.pack(fill='x',pady=(3,10))
        self._text(inside,'AJUSTES DE IMAGEN',font=11,bold=True).pack(fill='x',pady=(18,6))
        self.auto_btn = self._btn(inside, '', self._toggle_auto)
        self.auto_btn.pack(fill='x', pady=(0, 7))
        self._refresh_auto_button()
        helper_auto = self._text(inside, 'Optimiza iluminación, color y nitidez de forma suave. Puedes desactivarlo.', color=MUTED)
        helper_auto.configure(wraplength=266, justify='left')
        helper_auto.pack(fill='x', pady=(0, 9))
        for key,title in [('brightness','Brillo'),('contrast','Contraste'),('saturation','Saturación'),('sharpness','Nitidez')]:
            low,high=LIMITS[key]
            self._range(inside,title,key,low,high,resolution=.05)
        note=self._text(inside,'100 % = valor original. Ningún ajuste modifica el archivo fuente.',color=MUTED)
        note.configure(wraplength=266,justify='left')
        note.pack(fill='x',pady=(12,8))

        right=tk.Frame(frame,bg=PANEL,padx=11,pady=11)
        right.pack(side='left',fill='both',expand=True)
        top=tk.Frame(right,bg=PANEL)
        top.pack(fill='x')
        self.view_heading=self._text(top,'VISTA PREVIA · ÁREA DE RECORTE',font=11,bold=True)
        self.view_heading.pack(side='left')
        self.page_view_btn=self._btn(top,'Ver en hoja',self._toggle_page_view)
        self.page_view_btn.pack(side='right',padx=(6,0))
        self.result_btn=self._btn(top,'Ver resultado',self._toggle_result)
        self.result_btn.pack(side='right',padx=(7,0))
        self.original_btn=self._btn(top,'Original (mantener)',lambda:None)
        self.original_btn.pack(side='right')
        self.original_btn.bind('<ButtonPress-1>',self._original_press)
        self.original_btn.bind('<ButtonRelease-1>',self._original_release)
        self.original_btn.bind('<Leave>',self._original_release)
        # A la izquierda de Original / Ver resultado: confirma el recorte y
        # presenta inmediatamente la imagen final, sin alterar el original.
        self.crop_btn=self._btn(top,'✂ Recortar',self._confirm_crop)
        self.crop_btn.pack(side='right',padx=(0,7))
        self._refresh_crop_button()
        if self._result:
            self.result_btn.configure(text='Modificar recorte')
        self.canvas=tk.Canvas(right,bg='#0E1929',highlightthickness=0,bd=0,cursor='crosshair')
        self.canvas.pack(fill='both',expand=True,pady=(10,5))
        self.canvas.bind('<Configure>',lambda _e:self._display())
        self.canvas.bind('<ButtonPress-1>',self._crop_press)
        self.canvas.bind('<B1-Motion>',self._crop_move)
        self.canvas.bind('<ButtonRelease-1>',self._crop_release)
        self.help_note=self._text(right,'Marca el área y pulsa «Recortar» (crema) para ver el corte. Puedes volver a modificarlo.',
                                  color=MUTED)
        self.help_note.pack(fill='x')
        tk.Label(self,textvariable=self.status,fg=ACCENT,bg=BG,font=('Segoe UI',10),anchor='w').pack(side='bottom',fill='x',padx=20)
        self._bind_wheel(inside)
        self.scroll_canvas.bind('<MouseWheel>', self._wheel)

    def _range(self,inside,title,key,low,high,*,resolution):
        """Rueda = desplazar opciones; escala + valor editable con retorno magnético al neutro."""
        box=tk.Frame(inside,bg=PANEL);box.pack(fill='x',pady=(3,6))
        line=tk.Frame(box,bg=PANEL);line.pack(fill='x')
        self._text(line,title,color=MUTED).pack(side='left')
        variable=tk.DoubleVar(value=self.spec[key]);self._slider_vars[key]=variable
        display=tk.StringVar(value=f'{variable.get():.1f}' if key=='straighten' else f'{variable.get():.2f}')
        entry=tk.Entry(line,textvariable=display,width=6,fg=ACCENT,bg=PANEL2,insertbackground=TEXT,
                       justify='right',relief='flat',font=('Segoe UI',10,'bold'))
        entry.pack(side='right')
        neutral=0.0 if key=='straighten' else 1.0
        updating=[False]
        def set_value(new):
            if updating[0]:return
            try:new=float(new)
            except (ValueError,TypeError):return
            new=max(low,min(high,new))
            # Zona de atracción magnética de un paso de escala al valor original.
            if abs(new-neutral)<=resolution*1.25:new=neutral
            new=round(new,2)
            if abs(new-float(self.spec[key]))<1e-7:
                display.set(f'{new:.1f}' if key=='straighten' else f'{new:.2f}')
                return
            self.spec[key]=new
            updating[0]=True;variable.set(new);updating[0]=False
            display.set(f'{new:.1f}' if key=='straighten' else f'{new:.2f}')
            if key=='print_scale' and not self._page_view and (self.paper_options is not None or self.cover_spec is not None):
                self._toggle_page_view()
            self._schedule()
        slider=tk.Scale(box,from_=low,to=high,resolution=resolution,orient='horizontal',variable=variable,
                 command=lambda v:set_value(v),showvalue=False,bg=PANEL,fg=TEXT,troughcolor='#28405A',
                 highlightthickness=0,bd=0,activebackground=ACCENT,length=242)
        slider.pack(fill='x')
        variable.trace_add('write',lambda *_:set_value(variable.get()) if not updating[0] else None)
        entry.bind('<Return>',lambda _e:(set_value(display.get()),self.focus_set()))
        entry.bind('<FocusOut>',lambda _e:set_value(display.get()))
        slider.bind('<Double-Button-1>',lambda _e:set_value(neutral))
        # Incluso sobre el control nativo de Tk la rueda solo hace scroll.
        slider.bind('<MouseWheel>',self._wheel)
        entry.bind('<MouseWheel>',self._wheel)

    def _refresh_auto_button(self):
        if hasattr(self, 'auto_btn'):
            active = bool(self.spec['auto_correct'])
            self.auto_btn.configure(
                text='✓ Corrección automática activada' if active else 'Corrección automática',
                bg=ACCENT if active else PANEL2,
                fg=BG if active else TEXT,
            )

    def _toggle_auto(self):
        self.spec['auto_correct'] = not bool(self.spec['auto_correct'])
        self._refresh_auto_button()
        self.status.set('Corrección automática ' + ('activada' if self.spec['auto_correct'] else 'desactivada') + '. Puedes comparar con «Original».')
        self._schedule()

    def _schedule(self):
        if self._after_job:
            self.after_cancel(self._after_job)
        self._after_job=self.after(36,self._render)

    def _render(self):
        self._after_job=None
        if self._source is None or not self.winfo_exists(): return
        try:
            # La vista de edición muestra el fotograma ANTES del recorte para
            # facilitar recolocar sus esquinas; los efectos sí se muestran.
            spec=dict(self.spec);spec['crop']=None
            geom=apply_edits(self._source,spec)
            if self._geometry is not None:self._geometry.close()
            self._geometry=geom
            self._display()
        except Exception as exc:
            self.status.set(f'No se pudo actualizar la vista: {exc}')

    def _display(self):
        if not self.winfo_exists() or self._geometry is None:return
        if self._page_view:
            self._display_page()
            return
        cw,ch=self.canvas.winfo_width(),self.canvas.winfo_height()
        if cw<40 or ch<40:return
        if self._compare:
            image=self._source
        else:
            image=self._geometry
        if self._result and self.spec['crop'] and not self._compare:
            image=apply_edits(self._source,self.spec)
            owned=True
        else:owned=False
        try:
            ratio=min((cw-28)/image.width,(ch-28)/image.height)
            pw=max(1,round(image.width*ratio));ph=max(1,round(image.height*ratio))
            preview=image.resize((pw,ph),Image.Resampling.BILINEAR)
            self._display_photo=ImageTk.PhotoImage(preview)
            preview.close()
            self._box_px=((cw-pw)//2,(ch-ph)//2,pw,ph)
            x,y,_,_=self._box_px
            self.canvas.delete('all')
            self.canvas.create_rectangle(x+6,y+7,x+pw+6,y+ph+7,fill='#08111D',outline='')
            self.canvas.create_image(x,y,anchor='nw',image=self._display_photo)
            if not self._compare and not self._result:
                self._paint_crop()
        finally:
            if owned:image.close()

    def _toggle_page_view(self):
        self._page_view=not self._page_view
        self.page_view_btn.configure(text='Volver al recorte' if self._page_view else 'Ver en hoja')
        self.view_heading.configure(text='VISTA PREVIA · HOJA DE IMPRESIÓN' if self._page_view
                                    else 'VISTA PREVIA · ÁREA DE RECORTE')
        self.canvas.configure(cursor='arrow' if self._page_view else 'crosshair')
        self.help_note.configure(text=('Verás los cambios de tamaño en la hoja. Arrastra el asa crema de la fotografía para escalar.'
                     if self._page_view else 'Marca el área y pulsa «Recortar» (crema) para ver el corte.'))
        self._display()

    def _display_page(self):
        # Reutiliza el mismo motor de salida que los PDF y documentos Word:
        # la escala 0,40/1,00 se ve exactamente en el papel.
        from dataclasses import replace
        from processor import ExportOptions, render_print_image
        cw,ch=self.canvas.winfo_width(),self.canvas.winfo_height()
        if min(cw,ch)<50:return
        try:
            if self.cover_spec:
                from special_pages import render_special_page,validate_special_spec
                mm=self.paper_mm or (210.0,297.0)
                ratio=min((cw-36)/mm[0],(ch-36)/mm[1])
                w=max(50,round(mm[0]*ratio));h=max(50,round(mm[1]*ratio))
                special=validate_special_spec({**self.cover_spec,'background_edits':self.spec})
                sheet=render_special_page(special,(w,h))
            else:
                opts=self.paper_options or ExportOptions()
                edits=dict(opts.photo_edits)
                edits[self.path]=dict(self.spec)
                options=replace(opts,photo_edits=edits)
                sheet,_,_=render_print_image(self.path,options,
                    preview_max_size=(max(100,cw-36),max(100,ch-36)))
        except Exception as exc:
            self.status.set('No se pudo componer la vista de impresión: '+str(exc))
            return
        try:
            self._display_photo=ImageTk.PhotoImage(sheet)
            x=(cw-sheet.width)//2;y=(ch-sheet.height)//2
            self.canvas.delete('all')
            self.canvas.create_rectangle(x+6,y+7,x+sheet.width+6,y+sheet.height+7,
                                         fill='#06111D',outline='')
            self.canvas.create_image(x,y,anchor='nw',image=self._display_photo)
            self.canvas.create_rectangle(x,y,x+sheet.width,y+sheet.height,
                                         outline=ACCENT,width=2)
            # Asa directamente en la fotografía, no en una celda ficticia.
            try:
                from processor import printable_box
                if self.cover_spec:
                    spec=self.cover_spec
                    base=self._source.size
                    from photo_edits import transformed_dimensions
                    sw,sh=transformed_dimensions(base,self.spec)
                    mode=spec.get('image_mode','Cubrir')
                    ratio=(max(sheet.width/sw,sheet.height/sh) if mode=='Cubrir'
                           else min(sheet.width/sw,sheet.height/sh))
                    sx=float(spec.get('image_zoom_x',1.0)) if mode=='Libre' else 1.0
                    sy=float(spec.get('image_zoom_y',1.0)) if mode=='Libre' else 1.0
                    pw=sw*ratio*sx*self.spec['print_scale']
                    ph=sh*ratio*sy*self.spec['print_scale']
                    center_x=x+sheet.width*float(spec.get('image_x',.5)) if mode=='Libre' else x+sheet.width/2
                    center_y=y+sheet.height*float(spec.get('image_y',.5)) if mode=='Libre' else y+sheet.height/2
                else:
                    opts=self.paper_options or ExportOptions()
                    from processor import dimensions_mm
                    phys=dimensions_mm(self.path,opts)
                    bx0,by0,bx1,by1=printable_box(sheet.size,phys,binding=opts.binding)
                    from photo_edits import transformed_dimensions
                    sw,sh=transformed_dimensions(self._source.size,self.spec)
                    bw=bx1-bx0;bh=by1-by0
                    ratio=(max(bw/sw,bh/sh) if opts.fit=='Rellenar (recortar)'
                           else min(bw/sw,bh/sh))
                    pw=sw*ratio*self.spec['print_scale']
                    ph=sh*ratio*self.spec['print_scale']
                    center_x=x+(bx0+bx1)/2
                    center_y=y+(by0+by1)/2
                left=center_x-pw/2;top=center_y-ph/2
                right=center_x+pw/2;bottom=center_y+ph/2
                # En modo «Ver en hoja» se puede redimensionar tirando del asa.
                l=max(x,min(x+sheet.width,left));r=max(x,min(x+sheet.width,right))
                top_clip=max(y,min(y+sheet.height,top));bottom_clip=max(y,min(y+sheet.height,bottom))
                self.canvas.create_rectangle(l,top_clip,r,bottom_clip,
                                             outline=ACCENT,width=2,dash=(5,3))
                hx=max(x+8,min(x+sheet.width-8,r))
                hy=max(y+8,min(y+sheet.height-8,bottom_clip))
                self.canvas.create_rectangle(hx-7,hy-7,hx+7,hy+7,
                                             fill=CREAM,outline=BG,width=2)
                self._page_handle=(hx,hy)
            except Exception:
                self._page_handle=(0,0)
        finally:sheet.close()

    def _paint_crop(self):
        x,y,w,h=self._box_px
        x0,y0,x1,y1=self.spec['crop'] or [0,0,1,1]
        a,b,c,d=x+x0*w,y+y0*h,x+x1*w,y+y1*h
        shade='#0C1827'
        for box in [(x,y,x+w,b),(x,d,x+w,y+h),(x,b,a,d),(c,b,x+w,d)]:
            if box[2]>box[0] and box[3]>box[1]:
                self.canvas.create_rectangle(*box,fill=shade,stipple='gray50',outline='')
        self.canvas.create_rectangle(a,b,c,d,outline=ACCENT,width=2)
        for px,py in ((a,b),(c,b),(a,d),(c,d)):
            self.canvas.create_rectangle(px-5,py-5,px+5,py+5,fill=ACCENT,outline=BG,width=1)

    def _pos(self,event):
        x,y,w,h=self._box_px
        return (min(1,max(0,(event.x-x)/w)),min(1,max(0,(event.y-y)/h)))

    def _aspect(self):
        aspect=ASPECTS[self.crop_mode.get()]
        if aspect=='original':
            if self._geometry:return self._geometry.width/self._geometry.height
            return None
        return aspect

    def _fit_aspect(self,start,end):
        a=self._aspect()
        if a is None or self._geometry is None:return end
        _,_,w,h=self._box_px
        if w<1 or h<1:return end
        x0,y0=start;x1,y1=end
        dx=x1-x0;dy=y1-y0
        # Aspecto objetivo en píxeles reales, no en coordenadas 0..1.
        if abs(dx)*w>abs(dy)*h*a:
            dy=(1 if dy>=0 else -1)*abs(dx)*w/(h*a)
        else:
            dx=(1 if dx>=0 else -1)*abs(dy)*h*a/w
        # Limitar ambos ejes mediante UN factor, para preservar la proporción.
        limit_x=(1-x0) if dx>0 else x0
        limit_y=(1-y0) if dy>0 else y0
        factor=min(1.0, limit_x/abs(dx) if dx else 1.0,
                   limit_y/abs(dy) if dy else 1.0)
        return (max(0,min(1,x0+dx*factor)),max(0,min(1,y0+dy*factor)))

    def _crop_press(self,event):
        if self._page_view:
            rx,ry=self._page_handle
            if abs(event.x-rx)<22 and abs(event.y-ry)<22:
                self._resize_start=(event.x,event.y,self.spec['print_scale'])
            return
        if self._compare or self._result:return
        x,y,w,h=self._box_px
        if w<=0 or h<=0:return
        p=self._pos(event)
        rect=self.spec['crop'] or [0,0,1,1]
        corners=[(rect[0],rect[1]),(rect[2],rect[1]),(rect[0],rect[3]),(rect[2],rect[3])]
        nearby=[i for i,(cx,cy) in enumerate(corners) if abs((p[0]-cx)*w)<13 and abs((p[1]-cy)*h)<13]
        if nearby:
            corner=nearby[0]
            opposite=corners[3-corner]
            self._drag=('corner',opposite)
        else:
            self._drag=('new',p)
        self._crop_move(event)

    def _crop_move(self,event):
        if self._page_view:
            if self._resize_start:
                x,y,scale=self._resize_start
                cw=max(1,self.canvas.winfo_width())
                next_scale=max(.25,min(1.50,scale+(event.x-x)*2.0/cw))
                self._slider_vars['print_scale'].set(round(next_scale/.05)*.05)
            return
        if self._drag is None:return
        kind,start=self._drag
        end=self._fit_aspect(start,self._pos(event))
        x0,x1=sorted((start[0],end[0]));y0,y1=sorted((start[1],end[1]))
        if x1-x0<.01 or y1-y0<.01:return
        self.spec['crop']=[round(x0,5),round(y0,5),round(x1,5),round(y1,5)]
        self._refresh_crop_button()
        self._display()

    def _crop_release(self,_event):
        self._drag=None
        self._resize_start=None

    def _aspect_changed(self,_event=None):
        a=self._aspect()
        if a is None or self._geometry is None:return
        w,h=self._geometry.size
        target=a;src=w/h
        if target>=src:
            rw=1.;rh=min(1,src/target)
        else:
            rh=1.;rw=min(1,target/src)
        self.spec['crop']=[(1-rw)/2,(1-rh)/2,(1+rw)/2,(1+rh)/2]
        self._refresh_crop_button()
        self._display()

    def _clear_crop(self):
        self.spec['crop']=None
        self._confirmed_crop=None
        self._result=False
        self.result_btn.configure(text='Ver resultado')
        self._refresh_crop_button()
        self._display()

    def _auto_white(self):
        if self._source is None:return
        geom=geometry_image(self._source,self.spec)
        try:box=auto_white_crop(geom)
        finally:geom.close()
        if box:
            self.spec['crop']=box
            self.crop_mode.set('Libre')
            self._result=False
            self.result_btn.configure(text='Ver resultado')
            self._refresh_crop_button()
            self.status.set('Borde blanco detectado. Comprueba el recorte y guarda cuando quieras.')
            self._display()
        else:self.status.set('No se ha detectado un marco blanco que pueda quitarse con seguridad.')

    def _transform(self,mode):
        # Una selección pendiente de recorte se confirma primero: lo excluido
        # deja de existir para TODAS las transformaciones posteriores.
        self._commit_crop()
        if mode=='h':self.spec['flip_h']=not self.spec['flip_h']
        elif mode=='v':self.spec['flip_v']=not self.spec['flip_v']
        else:self.spec['turns']=(self.spec['turns']+mode)%4
        self._result=True
        self._refresh_crop_button()
        self.crop_mode.set('Libre')
        self._render()

    def _commit_crop(self):
        box=self.spec.get('crop')
        if box is None:return False
        # Las transformaciones anteriores se registran ANTES del recorte.
        self.spec=legacy_to_operations(self.spec)
        self._confirmed_crop=None
        self._result=True
        self.result_btn.configure(text='Modificar recorte')
        for name,var in self._slider_vars.items():
            if name in self.spec and abs(float(var.get())-float(self.spec[name]))>.001:
                var.set(self.spec[name])
        self._refresh_crop_button()
        return True

    def _refresh_crop_button(self):
        if not hasattr(self, 'crop_btn'):
            return
        selected = tuple(self.spec['crop']) if self.spec['crop'] else None
        ready = selected is not None and selected != self._confirmed_crop
        self.crop_btn.configure(state='normal' if ready else 'disabled',
                                bg=CREAM if ready else '#35445A',
                                fg=BG if ready else '#95A4B7',
                                activebackground='#FFF1D6' if ready else '#35445A',
                                cursor='hand2' if ready else 'arrow')

    def _confirm_crop(self):
        if self._commit_crop():
            self.status.set('Recorte confirmado. Los giros y ajustes actúan SOLO sobre esta imagen. «Restablecer original» recupera la fuente.')
            self._render()

    def _toggle_result(self):
        self._result=not self._result
        self.result_btn.configure(text='Modificar recorte' if self._result else 'Ver resultado')
        self._display()

    def _original_press(self,_event=None):
        self._compare=True;self._display()

    def _original_release(self,_event=None):
        if self._compare:
            self._compare=False;self._display()

    def reset(self):
        self.spec=validate_edits(None)
        self._refresh_auto_button()
        for key,var in self._slider_vars.items():var.set(self.spec[key])
        self.crop_mode.set('Libre')
        self._result=False
        self._confirmed_crop=None
        self._refresh_crop_button()
        self.result_btn.configure(text='Ver resultado')
        self.status.set('Edición restablecida. Tu archivo original sigue intacto.')
        self._render()

    def save(self):
        try:
            self._commit_crop()
            spec=validate_edits(self.spec)
            self.on_save(spec)
        except Exception as exc:
            from revelo_dialogs import showerror
            showerror('Guardar edición',str(exc))
            return
        self.close()

    def close(self):
        if self._after_job:
            self.after_cancel(self._after_job);self._after_job=None
        if self._source:self._source.close();self._source=None
        if self._geometry:self._geometry.close();self._geometry=None
        self.destroy()


def edit_photo(master,path:Path,saved:dict|None,on_save,
               *, pdf_flattened: bool = False, paper_options=None,
               cover_spec=None,paper_mm=None):
    """Abre editor propio; al guardar devuelve parámetros, nunca altera la foto."""
    return PhotoEditor(master,path,saved,on_save,pdf_flattened=pdf_flattened,
                       paper_options=paper_options,cover_spec=cover_spec,
                       paper_mm=paper_mm)
