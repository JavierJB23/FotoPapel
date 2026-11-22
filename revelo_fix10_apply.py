"""FIX10: coordenadas, renderizador común, portada de 8 asas y transparencia.

Se invoca desde ui_fix_v183.py DESPUÉS de FIX09. Todos los reemplazos fallan
explícitamente si el origen no coincide; no desactiva pruebas de GitHub.
"""


def apply_all(patch, replace_section):
    # Editor de hoja: renderizado único para ambas plantillas; los controles
    # (asas, números, barras) quedan como superposición, no repintan fotos.
    replace_section('layout_editor.py',
        '    def draw():', '\n    def sync_controls():',
'''    def draw():
        if not dialog.winfo_exists():
            return
        frame=page_geometry()
        if frame is None:
            return
        x,y,w,h=frame
        page[:]=frame
        canvas.delete('all')
        photos.clear()
        canvas.create_rectangle(x+6,y+7,x+w+6,y+h+7,
                                fill='#0A111D',outline='')
        # LO QUE SE VE ES LO QUE SE IMPRIME: la misma función de composición
        # produce editor, miniatura de la hoja, vista previa, PDF y Word.
        from revelo_shared_layout import render_editor_sheet
        try:
            sheet, _, _ = render_editor_sheet(paths,opts,template,state,ratios,
                photo_scales,background.get(),custom_color[0],(w,h),
                page_index=page_index)
        except (OSError, ValueError, RuntimeError) as exc:
            info.set('No puede componerse esta hoja: '+str(exc))
            return
        try:
            sheet_photo[0]=ImageTk.PhotoImage(sheet)
            canvas.create_image(x+(w-sheet.width)//2,y+(h-sheet.height)//2,
                                image=sheet_photo[0],anchor='nw')
        finally:
            sheet.close()
        canvas.create_rectangle(x,y,x+w,y+h,outline=AQUA,width=2)
        from processor import printable_box
        sx,sy,sr,sb=printable_box((w,h),(wmm,hmm),
                                 binding=opts.binding,page_index=page_index)
        zone=(x+sx,y+sy,x+sr,y+sb)
        safe_frame[:]=zone
        if not is_free:
            gap=max(2,round(min(w,h)*.014))
            rects=editable_template_rects(zone,gap,gap,template,ratios)
        for i,img in enumerate(thumbs):
            if is_free:
                bounds=state[paths[i]]['rect']
                scale=photo_scales[paths[i]]
                scaled=[bounds[0],bounds[1],bounds[2]*scale,bounds[3]*scale]
                unrotated,rect=visible_photo_geometry(zone,scaled,img.size,
                    state[paths[i]].get('angle',0.0),
                    stretch=bool(state[paths[i]].get('stretch',False)))
            else:
                rect=rects[i]
                unrotated=rect
            geometry[i]=rect
            unrotated_geometry[i]=unrotated
            l,t,r,b=rect
            color=AQUA if i==selected.get() else '#7A9EAC'
            canvas.create_rectangle(l,t,r,b,outline=color,
                width=2 if i==selected.get() else 1,
                dash=() if i==selected.get() else (3,4))
            canvas.create_text(l+5,t+5,anchor='nw',text=str(i+1),fill=CREAM,
                               font=('Segoe UI',10,'bold'))
            if not is_free and i==selected.get():
                canvas.create_rectangle(r-7,b-7,r+7,b+7,fill=AQUA,
                                        outline=NAVY,width=2)
            if is_free and i==selected.get():
                for hx,hy in resize_handles(rect).values():
                    canvas.create_rectangle(hx-6,hy-6,hx+6,hy+6,
                                            fill=AQUA,outline=NAVY,width=2)
        if not is_free:
            info.set('Las divisiones cambian de tamaño, sin romper la disposición '
                     +template.lower()+'.')
''')

    # Barra lateral del editor de portada: el rango y el recorte físico se
    # ajustan como las fotos corrientes; sin un tope de 300 % escondido.
    patch('special_pages.py', [
        ("not .25 <= val <= 3.0", "not .05 <= val <= 8.0"),
    ])
    patch('custom_editor.py', [
        ("tk.Scale(zoom_controls,from_=.25,to=3.0,resolution=.05,variable=fields['image_zoom_x']",
         "tk.Scale(zoom_controls,from_=.05,to=8.0,resolution=.05,variable=fields['image_zoom_x']"),
        ("tk.Scale(zoom_controls,from_=.25,to=3.0,resolution=.05,variable=fields['image_zoom_y']",
         "tk.Scale(zoom_controls,from_=.05,to=8.0,resolution=.05,variable=fields['image_zoom_y']"),
        ('try:target=max(.25,min(3.0,float(v.get().replace(\',\',\'.\'))))',
         'try:target=max(.05,min(8.0,float(v.get().replace(\',\',\'.\'))))'),
        ("    image_handle = [(0,0)]", "    image_handle = [(0,0)]\n    image_handles = {}"),
        ("    tk.Label(buttons, text='Puedes mover esta ventana y cambiar el papel en Revelo.',\n"
         "             bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='left')\n",
         "    # La nota informativa ocupaba una fila sin añadir una herramienta.\n"),
    ])

    # En la portada/separador hay 8 tiradores auténticos. Uno por lado y
    # cuatro esquinas. El movimiento de cada borde conserva el opuesto.
    replace_section('custom_editor.py',
        "            if label_key=='image' and fields['background_type'].get()=='imagen' and source_cache[1] is not None:",
        '            # Guías inteligentes visibles SOLO al alinear o arrastrar.',
'''            if label_key=='image' and fields['background_type'].get()=='imagen' and source_cache[1] is not None:
                ww,hh=_image_extent()
                cx=float(fields['image_x'].get()) if fields['image_mode'].get()=='Libre' else .5
                cy=float(fields['image_y'].get()) if fields['image_mode'].get()=='Libre' else .5
                a=ox+iw*(cx-ww/2);b=oy+ih*(cy-hh/2)
                c=ox+iw*(cx+ww/2);d=oy+ih*(cy+hh/2)
                image_handle[0]=(c,d)
                image_handles.clear()
                xm=(a+c)/2;ym=(b+d)/2
                for name,(hx,hy) in {
                    'nw':(a,b),'n':(xm,b),'ne':(c,b),'e':(c,ym),
                    'se':(c,d),'s':(xm,d),'sw':(a,d),'w':(a,ym)
                }.items():
                    image_handles[name]=(hx,hy)
                    canvas.create_rectangle(hx-6,hy-6,hx+6,hy+6,
                                            fill=ACCENT,outline=BG,width=2)
                canvas.create_rectangle(a,b,c,d,outline=ACCENT,width=2)
            else:
                image_handles.clear()
''')

    replace_section('custom_editor.py',
        '    def begin_drag(event):', '    def on_drag(event):',
'''    def begin_drag(event):
        if guide_hide_job[0] is not None:
            window.after_cancel(guide_hide_job[0])
            guide_hide_job[0]=None
        alignment[:]=[None,None]
        if focused.get()=='image' and fields['background_type'].get()=='imagen':
            chosen=None
            for name,(hx,hy) in image_handles.items():
                if abs(event.x-hx)<=14 and abs(event.y-hy)<=14:
                    chosen=name
                    break
            if chosen is not None and source_cache[1] is not None:
                ox,oy,iw,ih=canvas_box
                old_w,old_h=_image_extent()
                old_cx=float(fields['image_x'].get()) if fields['image_mode'].get()=='Libre' else .5
                old_cy=float(fields['image_y'].get()) if fields['image_mode'].get()=='Libre' else .5
                if fields['image_mode'].get()!='Libre':
                    source=source_cache[1]
                    contain=min(iw/max(1,source.width),ih/max(1,source.height))
                    scale=float(background_edits[0].get('print_scale',1.0))
                    basic_w=max(.00001,source.width*contain*scale/iw)
                    basic_h=max(.00001,source.height*contain*scale/ih)
                    fields['image_mode'].set('Libre')
                    fields['image_zoom_x'].set(max(.05,min(8.0,old_w/basic_w)))
                    fields['image_zoom_y'].set(max(.05,min(8.0,old_h/basic_h)))
                    fields['image_x'].set(.5)
                    fields['image_y'].set(.5)
                    old_cx=old_cy=.5
                image_drag[0]={
                    'handle':chosen,'start':(event.x,event.y),
                    'rect':(old_cx-old_w/2,old_cy-old_h/2,
                            old_cx+old_w/2,old_cy+old_h/2),
                    'zoom':(fields['image_zoom_x'].get(),
                            fields['image_zoom_y'].get())}
                return
        on_drag(event)

''')

    replace_section('custom_editor.py',
        "        if key == 'image':", "        else:\n            if not fields['show_'+key].get()",
'''        if key == 'image':
            if fields['background_type'].get()!='imagen':
                return
            if image_drag[0] is not None:
                data=image_drag[0]
                sx,sy=data['start']
                left,top,right,bottom=data['rect']
                old_w=max(.0001,right-left);old_h=max(.0001,bottom-top)
                dx=(event.x-sx)/max(1,iw)
                dy=(event.y-sy)/max(1,ih)
                handle=data['handle']
                if 'e' in handle:right+=dx
                if 'w' in handle:left+=dx
                if 's' in handle:bottom+=dy
                if 'n' in handle:top+=dy
                # Las esquinas mantienen relación de aspecto cuando procede.
                # Los tiradores centrales estiran un solo eje.
                if len(handle)==2 and linked_scale.get():
                    factor_w=(right-left)/old_w
                    factor_h=(bottom-top)/old_h
                    factor=factor_w if abs(factor_w-1)>=abs(factor_h-1) else factor_h
                    factor=max(.01,factor)
                    if 'e' in handle:right=left+old_w*factor
                    else:left=right-old_w*factor
                    if 's' in handle:bottom=top+old_h*factor
                    else:top=bottom-old_h*factor
                new_w=max(.01,right-left);new_h=max(.01,bottom-top)
                zx,zy=data['zoom']
                target_x=max(.05,min(8.0,zx*new_w/old_w))
                target_y=max(.05,min(8.0,zy*new_h/old_h))
                if len(handle)==1 and linked_scale.get():
                    # Los puntos centrales estiran un solo eje. Reflejarlo
                    # también en la casilla de proporción bloqueada.
                    linked_scale.set(False)
                syncing[0]=True
                try:
                    fields['image_zoom_x'].set(round(target_x,4))
                    fields['image_zoom_y'].set(round(target_y,4))
                finally:syncing[0]=False
                fields['image_x'].set(round(max(0,min(1,(left+right)/2)),5))
                fields['image_y'].set(round(max(0,min(1,(top+bottom)/2)),5))
                schedule()
                return
            raw_x=(event.x-ox)/iw
            raw_y=(event.y-oy)/ih
            # Cambiar de «Cubrir/Encajar» a «Libre» no debe dar un salto
            # brusco de tamaño al mover la fotografía por primera vez.
            if fields['image_mode'].get()!='Libre' and source_cache[1] is not None:
                old_w,old_h=_image_extent()
                src=source_cache[1]
                factor=min(iw/max(1,src.width),ih/max(1,src.height))
                scale=float(background_edits[0].get('print_scale',1.0))
                base_w=max(.00001,src.width*factor*scale/iw)
                base_h=max(.00001,src.height*factor*scale/ih)
                fields['image_mode'].set('Libre')
                syncing[0]=True
                try:
                    fields['image_zoom_x'].set(round(max(.05,min(8.,old_w/base_w)),4))
                    fields['image_zoom_y'].set(round(max(.05,min(8.,old_h/base_h)),4))
                finally:syncing[0]=False
            width,height=_image_extent()
            x,alignment[0]=magnetic_axis(raw_x,iw,guides_for_axis(extent=width),alignment[0])
            y,alignment[1]=magnetic_axis(raw_y,ih,guides_for_axis(extent=height),alignment[1])
            fields['image_x'].set(round(max(0,min(1,x)),5))
            fields['image_y'].set(round(max(0,min(1,y)),5))
''')

    # Pie de foto: las coordenadas antiguas siguen siendo locales, pero las
    # nuevas de hoja permiten situar el título/leyenda hasta cada borde.
    patch('advanced_layout.py', [
        ("                height=min(h-2*pad,max(sizes[key]*4,round(h*.22)))\n"
         "                measured=max((draw.textlength(line, font=fonts[key])\n"
         "                              for line in txt.splitlines()), default=0)\n"
         "                rw=min(max_width,max(40,min(round(w*.78),round(measured+pad*3))))",
         "                # La posición se aplica al bloque de texto real; no a una\n"
         "                # caja invisible del 22 % de la altura de la página.\n"
         "                measured=max((draw.textlength(line, font=fonts[key])\n"
         "                              for line in txt.splitlines()), default=0)\n"
         "                rw=min(max_width,max(40,min(round(w*.78),round(measured+pad*3))))\n"
         "                line_h=max(10,round(fonts[key].size*1.19))\n"
         "                count=max(1,len(_wrap_text(draw,txt,fonts[key],rw,max_lines=3)))\n"
         "                height=min(h,max(line_h+4,count*line_h+4))"),
        ("                left=max(pad,min(w-pad-rw,px-rw//2))\n"
         "                top=max(pad,min(h-pad-height,py-height//2))",
         "                if spec.get('position_space')=='page':\n"
         "                    left=max(0,min(w-rw,px-rw//2))\n"
         "                    top=max(0,min(h-height,py-height//2))\n"
         "                else:\n"
         "                    left=max(pad,min(w-pad-rw,px-rw//2))\n"
         "                    top=max(pad,min(h-pad-height,py-height//2))"),
    ])

    # La vista de título en hoja puede responder a un clic sobre cualquier
    # punto del papel, no solo a la antigua caja de su fotografía.
    patch('caption_editor.py', [
        ("        x=max(0,min(1,(event.x-x0)/max(1,w)))\n"
         "        y=max(0,min(1,(event.y-y0)/max(1,h)))",
         "        # Coordenadas del papel completo, no de la imagen elegida.\n"
         "        x=max(0,min(1,(event.x-x0)/max(1,w)))\n"
         "        y=max(0,min(1,(event.y-y0)/max(1,h)))"),
    ])

    # Motor final: las esquinas generadas al enderezar NO son píxeles blancos
    # impresos; usan una máscara y dejan ver el fondo real del papel.
    patch('processor.py', [
        ("        # Si el PDF importado no parece tener un borde artificial grande,",
'''        if opts.fit=='Ajustar (sin recortar)' and path not in opts.pdf_page_paths:
            from revelo_free_layers import editing_alpha, visible_photo_patch
            alpha=editing_alpha(path,opts.photo_edits.get(path),working.size)
            if alpha is not None:
                try:
                    if opts.paper_background=='Difuminado':
                        sheet=_extended_background(working,(out_w,out_h))
                    else:
                        sheet=Image.new('RGB',(out_w,out_h),paper_background_color(opts))
                    try:
                        region=visible_photo_patch(working,alpha,box,
                            ((box[0]+box[2])/2,(box[1]+box[3])/2),
                            ((box[2]-box[0])*print_scale,
                             (box[3]-box[1])*print_scale))
                        if region is not None:
                            layer,where=region
                            try:sheet.paste(layer,where,layer.getchannel('A'))
                            finally:layer.close()
                        return sheet,(w_mm,h_mm),low_resolution
                    except Exception:
                        sheet.close()
                        raise
                finally:alpha.close()
        # Si el PDF importado no parece tener un borde artificial grande,'''),
        ("            if photo_scale>2.0:\n"
         "                from revelo_free_layers import editing_alpha,visible_photo_patch",
'''            # Una máscara de edición (enderezado/PNG) exige componer sobre
            # el fondo de la página a CUALQUIER escala, no solo por encima
            # de 200 %. El resto sigue su camino existente.
            from revelo_free_layers import editing_alpha
            mask=(editing_alpha(path,opts.photo_edits.get(path),content.size)
                  if opts.fit=='Ajustar (sin recortar)' else None)
            if mask is not None:
                try:
                    from revelo_free_layers import visible_photo_patch
                    center_x=(cx0+cx1)/2
                    center_y=(cy0+photo_bottom)/2
                    if cap and cap.get('placement')=='Debajo':
                        contain=ImageOps.contain(content,
                            (max(8,round(cw*photo_scale)),
                             max(8,round(photo_ch*photo_scale))),
                            Image.Resampling.LANCZOS)
                        try:
                            gap=max(3,round(out_w/w_mm*1.5))
                            total=contain.height+footer_px+gap
                            top=cy0+max(0,(ch-total)//2)
                            center_y=top+contain.height/2
                            below_caption_start=top+contain.height+gap
                        finally:contain.close()
                    region=visible_photo_patch(content,mask,
                        (cx0,cy0,cx1,photo_bottom),
                        (center_x,center_y),
                        (cw*photo_scale,photo_ch*photo_scale))
                    if region is not None:
                        layer,where=region
                        try:sheet.paste(layer,where,layer.getchannel('A'))
                        finally:layer.close()
                finally:mask.close()
            elif photo_scale>2.0:
                from revelo_free_layers import editing_alpha,visible_photo_patch'''),
    ])

    # La biblioteca NO debe usar un cuarto renderizador simplificado cuando
    # se endereza la foto o tiene transparencia: su miniatura usa el motor final.
    patch('thumbnail_preview.py', [
        ("    with Image.open(path) as raw:\n"
         "        raw.draft('RGB', (900, 900))",
         "    editing=opts.photo_edits.get(path)\n"
         "    transparent=False\n"
         "    if path.suffix.lower() in ('.png','.webp','.tif','.tiff'):\n"
         "        with Image.open(path) as sample:\n"
         "            transparent=('A' in sample.getbands() or\n"
         "                         'transparency' in sample.info)\n"
         "    if editing:\n"
         "        from photo_edits import validate_edits\n"
         "        ops=validate_edits(editing)\n"
         "        transparent=(transparent or\n"
         "                     any(op['kind']=='straighten' for op in ops['ops']) or\n"
         "                     abs(ops['straighten'])>.001)\n"
         "    if transparent:\n"
         "        from processor import render_print_image\n"
         "        result,_,_=render_print_image(path,opts,\n"
         "            preview_max_size=max_size,page_index=page_index)\n"
         "        return result\n"
         "    with Image.open(path) as raw:\n"
         "        raw.draft('RGB', (900, 900))"),
    ])
