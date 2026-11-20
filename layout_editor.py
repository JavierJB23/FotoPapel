"""Diseño de hojas de Revelo: particiones editables y lienzo libre.

Todas las coordenadas son proporciones de la zona imprimible. Este módulo
nunca modifica los originales y las geometrías se serializan como JSON.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
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
    if 'angle' in spec:
        angle=spec['angle']
        if isinstance(angle,bool) or not isinstance(angle,(int,float)) or not -180<=angle<=180:
            raise ValueError('Rotación libre incorrecta')
        out['angle']=round(float(angle),3)
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
           else 'Arrastra para mover · Arrastra la esquina aguamarina para escalar · Rueda: tamaño · Shift + rueda: giro.')
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
    angle=tk.DoubleVar(value=0)
    angle_label=tk.Label(toolbar,text='Giro °',fg='white',bg=PANEL)
    angle_label.pack(side='left',padx=(18,5))
    angle_slider=tk.Scale(toolbar,from_=-180,to=180,orient='horizontal',resolution=1,
                          variable=angle,length=175,showvalue=True,
                          bg=PANEL,fg=CREAM,activebackground=AQUA,highlightthickness=0,
                          troughcolor='#2F455D')
    angle_slider.pack(side='left')
    if not is_free:
        angle_label.pack_forget();angle_slider.pack_forget()
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
    geometry=[None]*len(paths)
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

    def draw():
        if not dialog.winfo_exists():return
        frame=page_geometry()
        if frame is None:return
        x,y,w,h=frame;page[:]=frame
        canvas.delete('all')
        photos.clear()
        canvas.create_rectangle(x+6,y+7,x+w+6,y+h+7,fill='#0A111D',outline='')
        canvas.create_rectangle(x,y,x+w,y+h,fill='white',outline=AQUA,width=2)
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
        for i,img in enumerate(thumbs):
            if is_free:
                cx,cy,rw,rh=state[paths[i]]['rect'];deg=state[paths[i]].get('angle',0.0)
                bx=round(zx+zw*cx);by=round(zy+zh*cy)
                target_w=max(12,round(zw*rw));target_h=max(12,round(zh*rh))
                left=bx-target_w//2;top=by-target_h//2
                rect=(left,top,left+target_w,top+target_h)
            else:
                rect=rects[i];deg=0
            geometry[i]=rect
            l,t,r,b=rect
            iw=max(10,r-l);ih=max(10,b-t)
            fitted=ImageOps.contain(img,(iw,ih),Image.Resampling.BILINEAR)
            if is_free and abs(deg)>0.5:
                with_alpha=fitted.convert('RGBA')
                fitted.close()
                fitted=with_alpha.rotate(-deg,Image.Resampling.BICUBIC,expand=True)
            rendered=ImageTk.PhotoImage(fitted)
            photos.append(rendered)
            canvas.create_image((l+r)//2,(t+b)//2,image=rendered,anchor='center')
            fitted.close()
            color=AQUA if i==selected.get() else '#9BB4C7'
            canvas.create_rectangle(l,t,r,b,outline=color,width=2 if i==selected.get() else 1,
                                    dash=() if i==selected.get() else (3,4))
            canvas.create_text(l+5,t+5,anchor='nw',text=str(i+1),fill=CREAM,
                               font=('Segoe UI',10,'bold'))
            if is_free and i==selected.get():
                canvas.create_rectangle(r-7,b-7,r+7,b+7,fill=AQUA,outline=NAVY,width=2)
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
        i=selected.get();val=float(size.get())
        if is_free:
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
            state[paths[selected.get()]]['angle']=float(angle.get())
            draw()

    def hit_test(mx,my):
        for i in range(len(paths)-1,-1,-1):
            rect=geometry[i]
            if rect and rect[0]<=mx<=rect[2] and rect[1]<=my<=rect[3]:return i
        return None

    def press(event):
        found=hit_test(event.x,event.y)
        if found is None:return
        selected.set(found);sync_controls()
        rect=geometry[found]
        mode=('resize' if is_free and abs(event.x-rect[2])<18 and abs(event.y-rect[3])<18
              else 'move' if is_free else 'select')
        drag.update(start=(event.x,event.y),initial=list(state[paths[found]].get('rect',[])),mode=mode)
        draw()

    def moving(event):
        if not is_free or drag['start'] is None:return
        index=selected.get()
        x0,y0,x1,y1=safe_frame
        aw=max(1,x1-x0);ah=max(1,y1-y0)
        dx=(event.x-drag['start'][0])/aw;dy=(event.y-drag['start'][1])/ah
        cx,cy,rw,rh=drag['initial']
        if drag['mode']=='resize':
            rw=max(.05,min(1.5,rw+dx*2));rh=max(.05,min(1.5,rh+dy*2))
        elif drag['mode']=='move':
            cx=max(0,min(1,cx+dx));cy=max(0,min(1,cy+dy))
            if abs(cx-.5)<.012:cx=.5
            if abs(cy-.5)<.012:cy=.5
        state[paths[index]]['rect']=[round(q,5) for q in (cx,cy,rw,rh)]
        draw()
        if drag['mode']=='move':
            l,t,pw,ph=page
            if cx==.5:canvas.create_line(l+pw/2,t,l+pw/2,t+ph,fill=AQUA,width=2,dash=(4,4))
            if cy==.5:canvas.create_line(l,t+ph/2,l+pw,t+ph/2,fill=AQUA,width=2,dash=(4,4))

    def release(_event):drag['start']=None
    def wheel(event):
        direction=1 if event.delta>0 else -1
        if not is_free:
            size.set(min(80,max(20,int(size.get())+direction)))
        elif event.state & 0x1:
            angle.set(max(-180,min(180,int(angle.get())+direction*5)))
        else:
            size.set(max(35,min(160,int(size.get())+direction*5)))
        return 'break'

    def reset():
        if is_free:
            for i,p in enumerate(paths):state[p]=free_default(i,len(paths))
        else:
            ratios.update(split_main=.4 if template=='2 arriba + grande abajo' else .6,split_small=.5)
        sync_controls();draw()
    def finish(save):
        if save:
            if is_free:out={p:validate_layout_item(spec) for p,spec in state.items()}
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
