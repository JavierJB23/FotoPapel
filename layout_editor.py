"""Diseño de hojas de Revelo: particiones editables y lienzo libre.

Todas las coordenadas son proporciones de la zona imprimible. Este módulo
nunca modifica los originales y las geometrías se serializan como JSON.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk, colorchooser
from PIL import Image, ImageOps, ImageTk, ImageDraw
from advanced_layout import template_rects

NAVY='#0B1626'
PANEL='#14243A'
MUTED='#9BB4C7'
AQUA='#4FD9BC'
CREAM='#F2DAB0'


def validate_layout_item(spec: dict | None) -> dict:
    if spec is None:
        return {}
    if not isinstance(spec, dict):
        raise ValueError('Diseño de fotografía incorrecto')
    out={}
    if 'rect' in spec:
        rect=spec['rect']
        if not isinstance(rect,(list,tuple)) or len(rect)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not -1<=x<=2 for x in rect):
            raise ValueError('Rectángulo libre incorrecto')
        x,y,w,h=map(float,rect)
        if not (0<=x<=1 and 0<=y<=1 and .05<=w<=1.5 and .05<=h<=1.5):
            raise ValueError('Dimensiones del diseño fuera de rango')
        out['rect']=[round(v,5) for v in (x,y,w,h)]
    if 'stretch' in spec:
        if type(spec['stretch']) is not bool:raise ValueError('Distorsión libre no válida')
        out['stretch']=spec['stretch']
    if 'angle' in spec:
        angle=spec['angle']
        if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not -180<=angle<=180:
            raise ValueError('Rotación libre incorrecta')
        out['angle']=round(float(angle),3)
    if 'z' in spec:
        z=spec['z']
        if type(z) is not int or not 0 <= z <= 10000:
            raise ValueError('Orden de superposición incorrecto')
        out['z']=z
    if 'background' in spec:
        allowed=('Según encaje','Blanco','Crema','Aguamarina','Azul noche','Difuminado','Personalizado')
        if spec['background'] not in allowed:
            raise ValueError('Fondo de composición desconocido')
        out['background']=spec['background']
    if 'background_color' in spec:
        import re
        val=spec['background_color']
        if not isinstance(val,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',val):
            raise ValueError('Color de composición no válido')
        out['background_color']=val.upper()
    for name in ('split_main','split_small'):
        if name in spec:
            val=spec[name]
            if isinstance(val,bool) or not isinstance(val,(int,float)) or not .2<=val<=.8:
                raise ValueError('Reparto de plantilla incorrecto')
            out[name]=round(float(val),4)
    return out


def free_default(index:int,count:int)->dict:
    """Distribución inicial sin solapes completos; libre después de abrir editor."""
    cols=2 if count<=4 else 3
    rows=(count+cols-1)//cols
    col=index%cols;row=index//cols
    width=.84/cols
    height=.84/rows
    cx=.08+(col+.5)*(.84/cols)
    cy=.08+(row+.5)*(.84/rows)
    return {'rect':[round(cx,4),round(cy,4),round(width,4),round(height,4)], 'angle':0.0}


def visible_photo_geometry(zone, bounds, image_size, angle=0.0, *, stretch=False):
    """La selección rodea SOLO la fotografía renderizada, no su celda vacía.

    Devuelve rectángulo real sin girar y rectángulo exterior tras el giro.
    """
    from math import radians, cos, sin
    x0,y0,x1,y1=zone
    cx,cy,rw,rh=bounds
    width=max(10,round((x1-x0)*rw))
    height=max(10,round((y1-y0)*rh))
    sw,sh=image_size
    ratio=min(width/max(1,sw),height/max(1,sh))
    iw=width if stretch else max(1,round(sw*ratio))
    ih=height if stretch else max(1,round(sh*ratio))
    px=round(x0+(x1-x0)*cx);py=round(y0+(y1-y0)*cy)
    photo=(px-iw//2,py-ih//2,px+(iw+1)//2,py+(ih+1)//2)
    a=radians(angle)
    extw=round(abs(iw*cos(a))+abs(ih*sin(a)))
    exth=round(abs(iw*sin(a))+abs(ih*cos(a)))
    outer=(px-extw//2,py-exth//2,px+(extw+1)//2,py+(exth+1)//2)
    return photo,outer


def editable_template_rects(box, gap_x, gap_y, template, params):
    """Las fotos de 3 celdas conservan su orden estructural al ajustar divisiones."""
    x0,y0,x1,y1=box
    width=x1-x0; height=y1-y0
    major=float((params or {}).get('split_main',.6 if template!='2 arriba + grande abajo' else .4))
    minor=float((params or {}).get('split_small',.5))
    major=max(.2,min(.8,major)); minor=max(.2,min(.8,minor))
    if template=='Grande arriba + 2 abajo':
        cut_y=y0+round((height-gap_y)*major)
        cut_x=x0+round((width-gap_x)*minor)
        return [(x0,y0,x1,cut_y),(x0,cut_y+gap_y,cut_x,y1),(cut_x+gap_x,cut_y+gap_y,x1,y1)]
    if template=='Grande izquierda + 2 derecha':
        cut_x=x0+round((width-gap_x)*major)
        cut_y=y0+round((height-gap_y)*minor)
        return [(x0,y0,cut_x,y1),(cut_x+gap_x,y0,x1,cut_y),(cut_x+gap_x,cut_y+gap_y,x1,y1)]
    if template=='2 arriba + grande abajo':
        cut_y=y0+round((height-gap_y)*major)
        cut_x=x0+round((width-gap_x)*minor)
        return [(x0,y0,cut_x,cut_y),(cut_x+gap_x,y0,x1,cut_y),(x0,cut_y+gap_y,x1,y1)]
    return template_rects(box,gap_x,gap_y,template='Cuadrícula',count=3,landscape=width>height)


LAYOUT_BACKGROUNDS={
    'Blanco':'#FFFFFF', 'Crema':'#F6EBDC',
    'Aguamarina':'#DDF8EF', 'Azul noche':'#0B1928',
}


def free_sheet_background(paths, opts, size, background='Según encaje', custom='#FFFFFF',
                          *, first_source=None):
    """El mismo fondo en editor, previsualización, PDF y Word."""
    from processor import _extended_background, _prepared_photo
    if background == 'Difuminado' or (background == 'Según encaje' and
                                       opts.fit == 'Ampliar fondo (sin recortar)'):
        opened=None
        if first_source is None:
            opened,_=_prepared_photo(paths[0],opts)
        try:
            return _extended_background(first_source if first_source is not None else opened,size)
        finally:
            if opened is not None:opened.close()
    color = custom if background=='Personalizado' else LAYOUT_BACKGROUNDS.get(background,'#FFFFFF')
    return Image.new('RGB',size,color)


def _btn(parent,label,callback,accent=False):
    return tk.Button(parent,text=label,command=callback,bg=AQUA if accent else '#20334A',
                     fg=NAVY if accent else '#FFFFFF',font=('Segoe UI',10,'bold'),
                     relief='flat',bd=0,padx=12,pady=9,activebackground=CREAM)


def edit_sheet(parent,paths:list[Path],template:str,initial:dict[Path,dict],
               opts,on_save, *, page_index:int=0):
    """Editor independiente de hoja; clic para seleccionar, arrastre y rueda.

    Las plantillas irregulares ajustan sus dos divisiones; el diseño libre usa
    coordenadas, escalas y rotaciones individuales no destructivas.
    """
    if not paths:
        return None
    from processor import PAPER_SIZES, _prepared_photo
    is_free=template=='Diseño libre'
    wmm,hmm=PAPER_SIZES[opts.paper]
    if opts.orientation=='Horizontal' or (opts.orientation=='Automática' and _automatic_landscape(paths[0],opts)):
        wmm,hmm=hmm,wmm
    state={p:validate_layout_item(initial.get(p)) for p in paths}
    if is_free:
        for i,p in enumerate(paths):
            if 'rect' not in state[p]:state[p]={**state[p],**free_default(i,len(paths))}
            state[p].setdefault('z',i)
    bg_spec=state[paths[0]]
    background=tk.StringVar(value=bg_spec.get('background','Según encaje'))
    custom_color=[bg_spec.get('background_color','#FFFFFF')]
    ratios={key:float(state[paths[0]].get(key,.4 if key=='split_main' and template=='2 arriba + grande abajo' else .6 if key=='split_main' else .5))
            for key in ('split_main','split_small')}
    dialog=tk.Toplevel(parent)
    dialog.title('Revelo · Tamaño de fotos' if not is_free else 'Revelo · Diseño libre')
    dialog.geometry('1060x720')
    dialog.minsize(720,550)
    dialog.configure(bg=NAVY)
    tk.Label(dialog,text='TAMAÑO DE FOTOGRAFÍAS' if not is_free else 'COMPOSICIÓN LIBRE',
             font=('Segoe UI',17,'bold'),fg='white',bg=NAVY).pack(anchor='w',padx=20,pady=(17,4))
    guide=('Haz clic en una fotografía para seleccionarla. Usa la barra para modificar su espacio.' if not is_free
           else 'Arrastra la foto para moverla · Tira de esquinas (proporcional) o laterales (ancho/alto) · Doble clic: delante.')
    tk.Label(dialog,text=guide,bg=NAVY,fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',padx=20,pady=(0,11))
    toolbar=tk.Frame(dialog,bg=PANEL,padx=15,pady=10)
    toolbar.pack(fill='x',padx=18)
    selected=tk.IntVar(value=0)
    selected_label=tk.StringVar(value='Foto 1')
    tk.Label(toolbar,textvariable=selected_label,fg=AQUA,bg=PANEL,font=('Segoe UI',11,'bold')).pack(side='left',padx=(0,18))
    size=tk.DoubleVar(value=100 if is_free else round(ratios['split_main']*100))
    tk.Label(toolbar,text='Tamaño',fg='white',bg=PANEL).pack(side='left')
    size_slider=tk.Scale(toolbar,from_=35 if is_free else 20,to=160 if is_free else 80,resolution=1,
                         orient='horizontal',showvalue=True,variable=size,length=240,
                         bg=PANEL,fg=CREAM,activebackground=AQUA,highlightthickness=0,
                         troughcolor='#2F455D')
    size_slider.pack(side='left',padx=8)
    size_input=tk.Spinbox(toolbar,from_=35 if is_free else 20,to=160 if is_free else 80,
                          increment=1,textvariable=size,width=5,bg=PANEL,fg=AQUA,
                          insertbackground='white',relief='flat',justify='center')
    size_input.pack(side='left',padx=(0,5))
    size_input.bind('<Return>',lambda _e:(slider_changed(),dialog.focus_set()))
    size_input.bind('<FocusOut>',lambda _e:slider_changed())
    size_input.bind('<MouseWheel>',lambda _e:'break')
    angle=tk.DoubleVar(value=0)
    angle_label=tk.Label(toolbar,text='Giro °',fg='white',bg=PANEL)
    angle_label.pack(side='left',padx=(18,5))
    angle_slider=tk.Scale(toolbar,from_=-180,to=180,orient='horizontal',resolution=1,
                          variable=angle,length=175,showvalue=True,
                          bg=PANEL,fg=CREAM,activebackground=AQUA,highlightthickness=0,
                          troughcolor='#2F455D')
    angle_slider.pack(side='left')
    angle_entry=tk.Entry(toolbar,textvariable=angle,width=6,fg=AQUA,bg=PANEL,
                         insertbackground='white',relief='flat',justify='center')
    angle_entry.pack(side='left',padx=(7,0))
    angle_entry.bind('<Return>',lambda _ev:dialog.focus_set())
    angle_entry.bind('<MouseWheel>',lambda _ev:'break')
    angle_slider.bind('<MouseWheel>',lambda _ev:'break')
    size_slider.bind('<MouseWheel>',lambda _ev:'break')
    size_slider.bind('<Double-Button-1>',lambda _e:size.set(100 if is_free else
                                  60 if (selected.get()==0 if template!='2 arriba + grande abajo' else selected.get()==2)
                                  else 50))
    angle_slider.bind('<Double-Button-1>',lambda _e:angle.set(0))
    if not is_free:
        angle_label.pack_forget();angle_slider.pack_forget();angle_entry.pack_forget()
    if is_free:
        bg_row=tk.Frame(dialog,bg=PANEL,padx=15,pady=7)
        bg_row.pack(fill='x',padx=18,pady=(7,0))
        tk.Label(bg_row,text='Fondo de la hoja',bg=PANEL,fg='white',
                 font=('Segoe UI',10,'bold')).pack(side='left',padx=(0,10))
        bg_combo=ttk.Combobox(bg_row,textvariable=background,state='readonly',width=22,
            values=('Según encaje','Blanco','Crema','Aguamarina','Azul noche','Difuminado','Personalizado'))
        bg_combo.pack(side='left')
        color_btn=_btn(bg_row,'Elegir color…',lambda:None)
        color_btn.pack(side='left',padx=9)
        def choose_free_color():
            chosen=colorchooser.askcolor(color=custom_color[0],parent=dialog,
                                          title='Color de la composición')[1]
            if chosen:
                custom_color[0]=chosen.upper();background.set('Personalizado')
                draw()
        color_btn.configure(command=choose_free_color)
        def change_bg(_=None):
            color_btn.configure(state='normal' if background.get()=='Personalizado' else 'disabled')
            draw()
        bg_combo.bind('<<ComboboxSelected>>',change_bg)
        color_btn.configure(state='normal' if background.get()=='Personalizado' else 'disabled')
    canvas=tk.Canvas(dialog,bg='#1B2F47',highlightthickness=0)
    canvas.pack(fill='both',expand=True,padx=18,pady=(12,6))
    info=tk.StringVar(value='Cada foto conservará su proporción y el orden del documento.')
    tk.Label(dialog,textvariable=info,font=('Segoe UI',9),bg=NAVY,fg=MUTED).pack(anchor='w',padx=20)
    buttons=tk.Frame(dialog,bg=NAVY,padx=18,pady=14)
    buttons.pack(fill='x')
    thumbs=[]
    for p in paths:
        photo,_=_prepared_photo(p,opts)
        photo.thumbnail((760,760),Image.Resampling.LANCZOS)
        thumbs.append(photo)
    photos=[]
    sheet_photo=[None]
    geometry=[None]*len(paths)
    unrotated_geometry=[None]*len(paths)
    page=[0,0,1,1]
    safe_frame=[0,0,1,1]
    drag={'start':None,'initial':None,'mode':None}
    frozen=[False]

    def normalized_rect(index):
        if is_free:return state[paths[index]]['rect']
        return None

    def page_geometry():
        cw,ch=canvas.winfo_width(),canvas.winfo_height()
        if cw<50 or ch<50:return None
        scale=min((cw-64)/wmm,(ch-42)/hmm)
        width=max(15,round(wmm*scale));height=max(15,round(hmm*scale))
        left=(cw-width)//2;top=(ch-height)//2
        return left,top,width,height

    def resize_handles(rect):
        l,t,r,b=rect;mx=(l+r)/2;my=(t+b)/2
        return {'nw':(l,t),'n':(mx,t),'ne':(r,t),'e':(r,my),
                'se':(r,b),'s':(mx,b),'sw':(l,b),'w':(l,my)}

    def handle_hit(mx,my,rect):
        for name,(hx,hy) in resize_handles(rect).items():
            if abs(mx-hx)<=12 and abs(my-hy)<=12:return name
        return None

    def _make_stretch(index):
        spec=state[paths[index]]
        if spec.get('stretch'):return
        # Convertir una celda de encaje antigua en el tamaño real de su foto.
        rect=unrotated_geometry[index]
        if rect is None:return
        x0,y0,x1,y1=safe_frame;aw=max(1,x1-x0);ah=max(1,y1-y0)
        spec['rect']=[spec['rect'][0],spec['rect'][1],
                     max(.05,min(1.5,(rect[2]-rect[0])/aw)),
                     max(.05,min(1.5,(rect[3]-rect[1])/ah))]
        spec['stretch']=True

    def draw():
        if not dialog.winfo_exists():return
        frame=page_geometry()
        if frame is None:return
        x,y,w,h=frame;page[:]=frame
        canvas.delete('all')
        photos.clear()
        canvas.create_rectangle(x+6,y+7,x+w+6,y+h+7,fill='#0A111D',outline='')
        # Igual que el motor de salida: el fondo seleccionado cubre toda la hoja.
        if is_free:
            base=free_sheet_background(paths,opts,(w,h),background.get(),custom_color[0],
                                        first_source=thumbs[0])
            try:
                sheet_photo[0]=ImageTk.PhotoImage(base)
                canvas.create_image(x,y,image=sheet_photo[0],anchor='nw')
            finally:base.close()
        else:
            canvas.create_rectangle(x,y,x+w,y+h,fill='white',outline='',width=0)
        canvas.create_rectangle(x,y,x+w,y+h,outline=AQUA,width=2)
        from processor import printable_box
        if opts.binding:
            sx,sy,sr,sb=printable_box((w,h),(wmm,hmm),binding=True,page_index=page_index)
        else:
            mx=max(1,round(w*3/wmm));my=max(1,round(h*3/hmm))
            sx,sy,sr,sb=mx,my,w-mx,h-my
        zone=(x+sx,y+sy,x+sr,y+sb)
        safe_frame[:]=zone
        zx,zy,zr,zb=zone;zw=zr-zx;zh=zb-zy
        if not is_free:
            gap=max(2,round(min(w,h)*.014))
            rects=editable_template_rects(zone,gap,gap,template,ratios)
        # El número z decide qué fotografía aparece DELANTE. No depende del
        # orden en que fueron movidas por última vez.
        indices=(sorted(range(len(thumbs)),key=lambda i:(state[paths[i]].get('z',i),i))
                 if is_free else range(len(thumbs)))
        for i in indices:
            img=thumbs[i]
            if is_free:
                bounds=state[paths[i]]['rect'];deg=state[paths[i]].get('angle',0.0)
                cap=opts.captions.get(paths[i],{})
                scale=float(cap.get('photo_scale',1.0))*float(opts.photo_edits.get(paths[i],{}).get('print_scale',1.0))
                scaled_bounds=[bounds[0],bounds[1],bounds[2]*scale,bounds[3]*scale]
                unrotated,rect=visible_photo_geometry(zone,scaled_bounds,img.size,deg,
                                                       stretch=bool(state[paths[i]].get('stretch',False)))
            else:
                rect=rects[i];unrotated=rect;deg=0.0
            geometry[i]=rect
            unrotated_geometry[i]=unrotated
            l,t,r,b=rect
            if is_free:
                iw=max(1,unrotated[2]-unrotated[0]);ih=max(1,unrotated[3]-unrotated[1])
            else:
                iw=max(10,r-l);ih=max(10,b-t)
            fitted=(img.resize((iw,ih),Image.Resampling.BILINEAR) if is_free and state[paths[i]].get('stretch',False)
                    else ImageOps.contain(img,(iw,ih),Image.Resampling.BILINEAR))
            if is_free and abs(deg)>0.5:
                with_alpha=fitted.convert('RGBA')
                fitted.close()
                fitted=with_alpha.rotate(-deg,Image.Resampling.BICUBIC,expand=True)
            rendered=ImageTk.PhotoImage(fitted)
            photos.append(rendered)
            cx=(unrotated[0]+unrotated[2])//2
            cy=(unrotated[1]+unrotated[3])//2
            canvas.create_image(cx,cy,image=rendered,anchor='center')
            fitted.close()
            color=AQUA if i==selected.get() else '#9BB4C7'
            canvas.create_rectangle(l,t,r,b,outline=color,width=2 if i==selected.get() else 1,
                                    dash=() if i==selected.get() else (3,4))
            canvas.create_text(l+5,t+5,anchor='nw',text=str(i+1),fill=CREAM,
                               font=('Segoe UI',10,'bold'))
            if not is_free and i==selected.get():
                canvas.create_rectangle(r-7,b-7,r+7,b+7,fill=AQUA,outline=NAVY,width=2)
            if is_free and i==selected.get():
                for hx,hy in resize_handles(rect).values():
                    canvas.create_rectangle(hx-6,hy-6,hx+6,hy+6,fill=AQUA,outline=NAVY,width=2)
        if not is_free:
            info.set('Las divisiones cambian de tamaño, sin romper la disposición '+template.lower()+'.')

    def sync_controls():
        frozen[0]=True
        i=selected.get()
        selected_label.set(f'Foto {i+1} de {len(paths)} · {paths[i].name[:25]}')
        if is_free:
            spec=state[paths[i]]
            size.set(round(100*spec['rect'][2]/free_default(i,len(paths))['rect'][2]))
            angle.set(spec.get('angle',0))
        else:
            if template == '2 arriba + grande abajo':
                axis,inverse=('split_small',False) if i==0 else (('split_small',True) if i==1 else ('split_main',True))
            else:
                axis,inverse=('split_main',False) if i==0 else ('split_small',i==2)
            size.set(round((1-ratios[axis] if inverse else ratios[axis])*100))
        frozen[0]=False

    def slider_changed(_=None):
        if frozen[0]:return
        i=selected.get()
        try:val=float(size.get())
        except (ValueError,tk.TclError):return
        # Resistencia suave en 100 % (libre) o reparto predeterminado.
        special=i==0 if template!='2 arriba + grande abajo' else i==2
        neutral=100 if is_free else 60 if special else 50
        if abs(val-neutral)<=2 and val!=neutral:
            frozen[0]=True;size.set(neutral);frozen[0]=False
            val=float(neutral)
        if is_free:
            _make_stretch(i)
            spec=state[paths[i]]
            initial_spec=free_default(i,len(paths))['rect']
            old=spec['rect'];new_w=max(.05,min(1.5,initial_spec[2]*val/100))
            aspect=old[3]/max(.01,old[2])
            new_h=max(.05,min(1.5,new_w*aspect))
            spec['rect']=[old[0],old[1],round(new_w,5),round(new_h,5)]
        else:
            if template == '2 arriba + grande abajo':
                axis,inverse=('split_small',False) if i==0 else (('split_small',True) if i==1 else ('split_main',True))
            else:
                axis,inverse=('split_main',False) if i==0 else ('split_small',i==2)
            ratios[axis]=max(.2,min(.8,1-val/100 if inverse else val/100))
        draw()

    def angle_changed(_=None):
        if not frozen[0] and is_free:
            deg=float(angle.get())
            if abs(deg)<2.1:deg=0.;angle.set(0.)
            state[paths[selected.get()]]['angle']=deg
            draw()

    def hit_test(mx,my):
        order=sorted(range(len(paths)),key=lambda i:(state[paths[i]].get('z',i),i),reverse=True) if is_free else range(len(paths)-1,-1,-1)
        for i in order:
            rect=geometry[i]
            if rect and rect[0]<=mx<=rect[2] and rect[1]<=my<=rect[3]:return i
        return None

    def press(event):
        found=None;handle=None
        if is_free:
            # Un asa seleccionada prevalece incluso bajo una foto superpuesta.
            i=selected.get()
            if geometry[i]:
                handle=handle_hit(event.x,event.y,geometry[i])
                if handle:found=i
            if found is None:
                for i in sorted(range(len(paths)),key=lambda k:state[paths[k]].get('z',k),reverse=True):
                    if geometry[i] and (h:=handle_hit(event.x,event.y,geometry[i])):
                        found=i;handle=h;break
        if found is None:found=hit_test(event.x,event.y)
        if found is None:
            drag['start']=None;return
        selected.set(found)
        if is_free and handle:
            _make_stretch(found)
        sync_controls()
        if is_free:
            mode='resize:'+handle if handle else 'move'
        else:
            r=geometry[found]
            mode='template_resize' if abs(event.x-r[2])<20 and abs(event.y-r[3])<20 else 'select'
        drag.update(start=(event.x,event.y),initial=list(state[paths[found]].get('rect',[])),
                    initial_size=float(size.get()),mode=mode)
        draw()

    def moving(event):
        if drag['start'] is None:return
        if not is_free:
            if drag.get('mode')=='template_resize':
                i=selected.get();x0,y0,x1,y1=safe_frame
                dx=(event.x-drag['start'][0])/max(1,x1-x0)*100
                dy=(event.y-drag['start'][1])/max(1,y1-y0)*100
                horizontal=(template=='Grande izquierda + 2 derecha' and i==0) or (
                    template in ('Grande arriba + 2 abajo','2 arriba + grande abajo') and
                    (i != 0 if template=='Grande arriba + 2 abajo' else i != 2))
                change=dx if horizontal else dy
                size.set(max(20,min(80,round(drag['initial_size']+change))))
            return
        index=selected.get()
        x0,y0,x1,y1=safe_frame
        aw=max(1,x1-x0);ah=max(1,y1-y0)
        dx=(event.x-drag['start'][0])/aw;dy=(event.y-drag['start'][1])/ah
        cx,cy,rw,rh=drag['initial']
        mode=drag['mode']
        if mode and mode.startswith('resize:'):
            _make_stretch(index)
            if not state[paths[index]].get('stretch'):
                return
            handle=mode.partition(':')[2]
            # En los laterales se puede estirar horizontal o verticalmente.
            # Esquinas: conserva las proporciones de la imagen visible.
            if len(handle)==2:
                delta_x=(dx if 'e' in handle else -dx)*2
                delta_y=(dy if 's' in handle else -dy)*2
                factor=1+max(delta_x/max(.05,rw),delta_y/max(.05,rh),
                             min(delta_x/max(.05,rw),delta_y/max(.05,rh)))
                factor=max(.15,min(1.5/max(rw,rh),factor))
                rw=max(.05,min(1.5,rw*factor));rh=max(.05,min(1.5,rh*factor))
            else:
                if handle in ('e','w'):
                    rw=max(.05,min(1.5,rw+(dx if handle=='e' else -dx)*2))
                elif handle in ('s','n'):
                    rh=max(.05,min(1.5,rh+(dy if handle=='s' else -dy)*2))
        elif mode=='move':
            cx=max(0,min(1,cx+dx));cy=max(0,min(1,cy+dy))
            if abs(cx-.5)<.012:cx=.5
            if abs(cy-.5)<.012:cy=.5
        state[paths[index]]['rect']=[round(q,5) for q in (cx,cy,rw,rh)]
        draw()
        if mode=='move':
            l,t,pw,ph=page
            if cx==.5:canvas.create_line(l+pw/2,t,l+pw/2,t+ph,fill=AQUA,width=2,dash=(4,4))
            if cy==.5:canvas.create_line(l,t+ph/2,l+pw,t+ph/2,fill=AQUA,width=2,dash=(4,4))

    def raise_photo(event):
        if not is_free:return
        found=hit_test(event.x,event.y)
        if found is None:return
        # Clic en cualquier parte visible de la foto para traerla delante.
        selected.set(found)
        top=max(state[p].get('z',i) for i,p in enumerate(paths))
        if top>=9999:
            for z,i in enumerate(sorted(range(len(paths)),key=lambda i:state[paths[i]].get('z',i))):
                state[paths[i]]['z']=z
            top=len(paths)-1
        state[paths[found]]['z']=top+1
        sync_controls();draw()
        info.set(f'Foto {found+1} colocada delante. Doble clic sobre otra para cambiar las capas.')

    def release(_event):drag['start']=None
    def wheel(event):
        # La rueda nunca cambia ajustes por accidente. Para dimensionar, asas o barra.
        return 'break'

    def reset():
        if is_free:
            for i,p in enumerate(paths):state[p]=free_default(i,len(paths))
        else:
            ratios.update(split_main=.4 if template=='2 arriba + grande abajo' else .6,split_small=.5)
        sync_controls();draw()
    def finish(save):
        if save:
            if is_free:
                out={p:validate_layout_item(spec) for p,spec in state.items()}
                out[paths[0]]['background']=background.get()
                out[paths[0]]['background_color']=custom_color[0]
            else:
                out={paths[0]:{**validate_layout_item(state.get(paths[0])), **ratios}}
                # Limpiar solo las antiguas divisiones de este grupo.
                for p in paths[1:]:out[p]={k:v for k,v in state[p].items() if k not in ('split_main','split_small')}
            on_save(out)
        for photo in thumbs:photo.close()
        dialog.destroy()

    _btn(buttons,'Cancelar',lambda:finish(False)).pack(side='right')
    _btn(buttons,'Guardar composición',lambda:finish(True),True).pack(side='right',padx=(0,12))
    _btn(buttons,'Restablecer',reset).pack(side='left')
    canvas.bind('<Configure>',lambda _e:draw())
    canvas.bind('<ButtonPress-1>',press)
    canvas.bind('<B1-Motion>',moving)
    canvas.bind('<Double-Button-1>',raise_photo)
    canvas.bind('<ButtonRelease-1>',release)
    canvas.bind('<MouseWheel>',wheel)
    size_slider.configure(command=slider_changed)
    angle_slider.configure(command=angle_changed)
    dialog.after(100,lambda:(sync_controls(),draw()))
    dialog.protocol('WM_DELETE_WINDOW',lambda:finish(False))
    return dialog


def _automatic_landscape(path:Path,opts)->bool:
    try:
        from processor import dimensions_mm
        w,h=dimensions_mm(path,opts)
        return w>h
    except Exception:return False
