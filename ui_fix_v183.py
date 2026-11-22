"""REVELO v1.8.3: parche de interfaz reproducible para el repositorio original.

Se ejecuta en GitHub Actions antes de las pruebas y de PyInstaller.
No modifica el motor de impresión ni los datos de los proyectos.
"""
from pathlib import Path
import sys
_FIX07_MARKER = "# REVELO_FIX07_COMPLETADO"
_MAIN_FILE = Path(__file__).resolve().parent / "main.py"
if _MAIN_FILE.exists() and _FIX07_MARKER in _MAIN_FILE.read_text(encoding="utf-8"):
    print("FIX07 ya aplicado; no se repiten sustituciones.")
    sys.exit(0)


def patch(path: str, changes: list[tuple[str, str]]) -> None:
    target = Path(__file__).resolve().parent / path
    content = target.read_text(encoding='utf-8')
    touched = 0
    for before, after in changes:
        if content.count(before) == 0 and after in content:
            continue  # actualización ya aplicada
        if content.count(before) != 1:
            raise RuntimeError(f'No se puede aplicar con seguridad {path}: patrón no único o ausente: {before[:80]!r}')
        content = content.replace(before, after, 1)
        touched += 1
    target.write_text(content, encoding='utf-8')
    print(f'{path}: {touched} actualizaciones aplicadas')


patch('editorial_theme.py', [
    ('    ix = width - image.width\n',
     '    # En la ventana principal reservamos espacio a los botones Abrir/Guardar.\n'
     '    # La montaña queda en el hueco central con proporción original (sin zoom).\n'
     '    ix = max(340, width - image.width - 255) if primary else width - image.width\n'),
    ('        self._image=ImageTk.PhotoImage(banner_raster(w,h))',
     '        self._image=ImageTk.PhotoImage(banner_raster(w,h,primary=not bool(self.heading) and h>=85))'),
    ('    width=max(31,min(290,measured+30))',
     '    # Margen real para Windows HiDPI: evita texto cortado en «Elegir foto».\n'
     '    width=max(42,min(360,measured+46))'),
    ("    height=39 if ('Exportar fotos' in text or 'Guardar' in text) else (32 if measured<160 else 36)",
     "    height=40 if ('Exportar fotos' in text or 'Guardar' in text) else 36"),
    ("    if text in ('×','↑','↓','…'):width=31;height=29",
     "    if text in ('×','↑','↓','…'):width=34;height=32"),
    ('    radius=min(H//3,12*s)', '    radius=min(H//2,15*s)'),
    ("                widget.configure(relief='flat',bd=0,highlightthickness=1,\n"
     "                                 highlightbackground='#46778B',highlightcolor=AQUA,\n"
     "                                 insertbackground=AQUA)\n"
     "            except tk.TclError:pass",
     "                widget.configure(relief='flat',bd=0,highlightthickness=1,\n"
     "                                 highlightbackground='#46778B',highlightcolor=AQUA,\n"
     "                                 insertbackground=AQUA)\n"
     "                if isinstance(widget,tk.Spinbox):\n"
     "                    widget.configure(buttonbackground=SURFACE_2,foreground=TEXT,\n"
     "                                     disabledforeground=MUTED,readonlybackground=SURFACE_2)\n"
     "            except tk.TclError:pass"),
    ("        d.line((8,3,w*3-8,3),fill=outline,width=2)\n"
     "        d.line((3,10,3,h*3-12),fill=outline,width=2)",
     "        # Sin segmentos independientes: ttk los estiraba y podían verse\n"
     "        # como líneas extrañas al actualizar el contenido.\n"
     "        pass"),
])

patch('main.py', [
    ('        setting_outer = tk.Frame(self.root, bg=BG, padx=24)',
     '        setting_outer = tk.Frame(self.root, bg=BG, padx=18)'),
    ('        settings = RoundedCard(setting_outer,fill=SURFACE,outline="#50889A",pad=7)',
     '        settings = RoundedCard(setting_outer,fill=SURFACE,outline="#50889A",pad=5)'),
    ('        content = tk.Frame(self.root, bg=BG, padx=23, pady=5)',
     '        content = tk.Frame(self.root, bg=BG, padx=15, pady=4)'),
    ('        content.grid_columnconfigure(0, weight=5, uniform="grid")\n'
     '        content.grid_columnconfigure(1, weight=6, uniform="grid")',
     '        content.grid_columnconfigure(0, weight=4, uniform="grid")\n'
     '        content.grid_columnconfigure(1, weight=7, uniform="grid")'),
    ('        return RoundedCard(parent,fill=SURFACE,outline="#56899A",pad=7)',
     '        return RoundedCard(parent,fill=SURFACE,outline="#56899A",pad=5)'),
    ('        ordering_top = tk.Frame(right_panel, bg=SURFACE, padx=15, pady=7)',
     '        ordering_top = tk.Frame(right_panel, bg=SURFACE, padx=9, pady=5)'),
    ('        hint = tk.Frame(right_panel, bg="#123D43", padx=12, pady=6,',
     '        hint = tk.Frame(right_panel, bg="#123D43", padx=8, pady=5,'),
    ('        hint.pack(fill="x", padx=12, pady=(10, 2))',
     '        hint.pack(fill="x", padx=7, pady=(6, 2))'),
    ('        self.order_area.pack(fill="both", expand=True, padx=9, pady=9)',
     '        self.order_area.pack(fill="both", expand=True, padx=5, pady=5)'),
])

patch('caption_editor.py', [
    ('VISTA PREVIA DE LA HOJA · EN DIRECTO', 'VISTA PREVIA DE LA HOJA'),
])

# FIX04: En ventanas estrechas, el título de biblioteca ya no comparte la
# misma fila que los botones. Windows dejaba «Vaciar» sin mapear.
# Mantener ambas filas de botones, el texto completo del botón QR y el panel derecho amplio.
patch('main.py', [
    ('        title.pack(side="left")\n        library_heading = tk.Frame(title, bg=SURFACE)',
     '        title.pack(anchor="w")\n        library_heading = tk.Frame(title, bg=SURFACE)'),
    ('        buttons.pack(side="right")\n        files_row = tk.Frame(buttons, bg=SURFACE)',
     '        buttons.pack(fill="x", pady=(3, 0))\n        files_row = tk.Frame(buttons, bg=SURFACE)'),
    ('self.add_btn = self._button(files_row, "+ Añadir fotos / PDF",',
     'self.add_btn = self._button(files_row, "+ Añadir fotos",'),
])


# FIX05 — recuperación de la jerarquía, controles editoriales y supresión
# de líneas ornamentales. Se aplica tras FIX04, sin alterar callbacks.
patch('main.py', [
    # Reparto de paneles original: suficiente sitio para dos miniaturas y la hoja.
    ('        content.grid_columnconfigure(0, weight=4, uniform="grid")\n'
     '        content.grid_columnconfigure(1, weight=7, uniform="grid")',
     '        content.grid_columnconfigure(0, weight=5, uniform="grid")\n'
     '        content.grid_columnconfigure(1, weight=6, uniform="grid")'),
    # Alinear los bordes exteriores de configuración y paneles inferiores.
    ('        setting_outer = tk.Frame(self.root, bg=BG, padx=18)',
     '        setting_outer = tk.Frame(self.root, bg=BG, padx=23)'),
    ('        content = tk.Frame(self.root, bg=BG, padx=15, pady=4)',
     '        content = tk.Frame(self.root, bg=BG, padx=23, pady=4)'),
    # El QR no debe estirarse y dejar «Vaciar» aislado a la derecha.
    ('        self.mobile_btn.pack(side="left", fill="x", expand=True, padx=(0,7))',
     '        self.mobile_btn.pack(side="left", padx=(0, 9))'),
    ('        lower_buttons.pack(fill="x", pady=(7,0))',
     '        lower_buttons.pack(fill="x", pady=(5,0))'),
    # Barra de desplazamiento oscura, con flechas aguamarina y relieve integrado.
    ('        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)',
     '        self.bar = ttk.Scrollbar(self, orient="vertical",\n'
     '                                 style="Revelo.Vertical.TScrollbar",\n'
     '                                 command=self.canvas.yview)'),
    ('        setup_combo_style(self.root)\n        style.configure(\n            "Revelo.Horizontal.TProgressbar"',
     '        setup_combo_style(self.root)\n'
     '        style.configure("Revelo.Vertical.TScrollbar",\n'
     '                        background="#285366", troughcolor="#102A3B",\n'
     '                        arrowcolor="#53E6D0", bordercolor="#173A4D",\n'
     '                        darkcolor="#204759", lightcolor="#366578",\n'
     '                        gripcount=0, width=15, relief="flat")\n'
     '        style.map("Revelo.Vertical.TScrollbar",\n'
     '                  background=[("active", "#367687"), ("pressed", "#428D99")],\n'
     '                  arrowcolor=[("active", "#8FFFF0")])\n'
     '        style.configure(\n            "Revelo.Horizontal.TProgressbar"'),
])

patch('editorial_theme.py', [
    # El «rectángulo fantasma» venía de la tira de luz y su recorte angular.
    # Dejamos una única silueta redondeada, sin otro rectángulo encima.
    ('    # Tira superior de luz suave: no ocupa texto.\n'
     '    if not disabled:\n'
     '        draw.rounded_rectangle((3*s,3*s,W-4*s,min(H//2,H-4*s)),radius=max(2,radius-2*s),fill=hi)\n'
     '        draw.rectangle((3*s,min(H//2,H-4*s)-radius, W-4*s,H//2+2*s),fill=hi)',
     '    # Una única superficie: el texto de tk.Button permanece encima.\n'
     '    # No añadir capas de luz rectangulares sobre las esquinas.'),
    # Retirar el arco decorativo que se veía como rayitas curvas sobre las fotos.
    ('    if h>24:\n'
     '        d.arc((2,1,w-3,max(16,min(36,h//5))),180,360,fill=\'#477B8C\',width=1)',
     '    # Sin arcos decorativos que parezcan artefactos en tarjetas.'),
    # Controles de subir/bajar cuadrados con esquinas ligeras, no píldoras.
    ('    radius=min(H//2,15*s)',
     '    radius=min(H//2,15*s)\n'
     '    if w <= 36 and h <= 36:\n'
     '        radius=5*s'),
    # Mejorar spinboxes sin tocar variables ni límites.
    ('                    widget.configure(buttonbackground=SURFACE_2,foreground=TEXT,\n'
     '                                     disabledforeground=MUTED,readonlybackground=SURFACE_2)',
     '                    widget.configure(buttonbackground="#285366",foreground=TEXT,\n'
     '                                     disabledforeground=MUTED,readonlybackground=SURFACE_2,\n'
     '                                     relief="flat",bd=0)'),
])


# FIX06: integración real del nuevo dibujo de botones y controles responsivos.
# Se ejecuta después de FIX05. El cambio es idempotente.
def replace_section(path: str, opening: str, closing: str, replacement: str) -> None:
    target = Path(__file__).resolve().parent / path
    content = target.read_text(encoding='utf-8')
    if replacement in content:
        return
    if content.count(opening) != 1:
        raise RuntimeError(f'{path}: cabecera a sustituir ausente o repetida')
    beginning = content.index(opening)
    end = content.find(closing, beginning)
    if end == -1:
        raise RuntimeError(f'{path}: fin de bloque ausente')
    result = content[:beginning] + replacement + content[end:]
    target.write_text(result, encoding='utf-8')
    print(f'{path}: rediseño de botones centralizado')


replace_section('editorial_theme.py',
    'def style_button(button: tk.Button, *, accent=None):',
    '\ndef skin_tree(',
    """def style_button(button: tk.Button, *, accent=None):
    # Implementación común: admite .configure(bg=...) sin fondo rectangular.
    from revelo_button_skin import style_button as _polished_style_button
    return _polished_style_button(button, accent=accent)


""")

patch('main.py', [
    ('        files_row.pack(fill="x")',
     '        files_row.pack(side="left")'),
    ('        lower_buttons.pack(fill="x", pady=(5,0))',
     '        lower_buttons.pack(side="left", padx=(9,0))'),
    ('        self.clear_btn.pack(side="left")\n        tk.Frame(left_panel, height=1, bg=BORDER).pack(fill="x")',
     '        self.clear_btn.pack(side="left")\n'
     '        # Pantalla amplia: cuatro acciones en una línea.\n'
     '        # Pantalla compacta: dividir en dos para no esconder ninguna.\n'
     '        self._library_buttons_one_row = True\n'
     '        def align_library_buttons(event=None):\n'
     '            available = buttons.winfo_width()\n'
     '            needed = files_row.winfo_reqwidth() + lower_buttons.winfo_reqwidth() + 12\n'
     '            wide = available >= needed and available > 10\n'
     '            if wide == self._library_buttons_one_row:\n'
     '                return\n'
     '            self._library_buttons_one_row = wide\n'
     '            files_row.pack_forget()\n'
     '            lower_buttons.pack_forget()\n'
     '            if wide:\n'
     '                files_row.pack(side="left")\n'
     '                lower_buttons.pack(side="left", padx=(9,0))\n'
     '            else:\n'
     '                files_row.pack(fill="x")\n'
     '                lower_buttons.pack(fill="x", pady=(5,0))\n'
     '        buttons.bind("<Configure>", align_library_buttons, add="+")\n'
     '        self.root.after_idle(align_library_buttons)\n'
     '        tk.Frame(left_panel, height=1, bg=BORDER).pack(fill="x")'),
])

# FIX07 — coherencia de estados inhabilitados y espacio de edición.
# Todos los botones se dibujan en revelo_button_skin.py; se respeta el
# state real de Tk para no alterar callbacks ni pruebas funcionales.

patch('photo_editor_ui.py', [
    ("self._btn(tools,'Quitar bordes blancos',self._auto_white)",
     "self._btn(tools,'Quitar bordes',self._auto_white)"),
])

patch('custom_editor.py', [
    # Sustituir el único scrollbar nativo de Revelo por el mismo ttk
    # editorial usado en el menú principal.
    ("scroll = tk.Scrollbar(rail,orient='vertical',command=controls_canvas.yview)",
     "scroll = ttk.Scrollbar(rail,orient='vertical',style='Revelo.Vertical.TScrollbar',"
     "command=controls_canvas.yview)"),
    # Las opciones de selección y el modo de foto comparten la primera fila.
    ("    photo_controls = tk.Frame(right,bg=SURFACE)\n"
     "    photo_controls.pack(fill='x',pady=(3,8))",
     "    photo_controls = tk.Frame(pick,bg=SURFACE)\n"
     "    photo_controls.pack(side='left',padx=(9,0))"),
    ("tk.Checkbutton(photo_controls,text='Mantener proporción en escala libre',",
     "tk.Checkbutton(photo_controls,text='Mantener proporción',"),
    ("    tk.Label(right, text='Mueve el elemento elegido. También puedes arrastrar una foto a esta vista desde el Explorador.',\n"
     "             bg=SURFACE, fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w', pady=(0,5))\n",
     ""),
    ("    tk.Label(right,text='Libre: mueve la foto y ajusta ancho/alto. El espacio libre usa el color o difuminado elegido.',\n"
     "             bg=SURFACE,fg=MUTED,font=('Segoe UI',8),wraplength=520,justify='left').pack(anchor='w',pady=(0,5))\n",
     ""),
    ("    pick.pack(fill='x', pady=(8,4))", "    pick.pack(fill='x', pady=(5,5))"),
])

patch('editorial_theme.py', [
    # ttk.Scrollbar de todas las ventanas auxiliares: misma configuración
    # visual que ScrollingArea del menú principal, sin cambiar su comando.
    ("        elif isinstance(widget,ttk.Combobox):",
     "        elif isinstance(widget,ttk.Scrollbar):\n"
     "            try:\n"
     "                if str(widget.cget('orient')) == 'vertical':\n"
     "                    widget.configure(style='Revelo.Vertical.TScrollbar')\n"
     "            except tk.TclError:pass\n"
     "        elif isinstance(widget,ttk.Combobox):"),
    ("    if banner:add_secondary_banner(window,compact=compact)",
     "    # El mismo estilo que la ventana principal, también en diálogos.\n"
     "    style.configure('Revelo.Vertical.TScrollbar',\n"
     "                    background='#285366',troughcolor='#102A3B',\n"
     "                    arrowcolor='#53E6D0',bordercolor='#173A4D',\n"
     "                    darkcolor='#204759',lightcolor='#366578',\n"
     "                    gripcount=0,width=15,relief='flat')\n"
     "    style.map('Revelo.Vertical.TScrollbar',\n"
     "              background=[('active','#367687'),('pressed','#428D99')],\n"
     "              arrowcolor=[('active','#8FFFF0')])\n"
     "    if banner:add_secondary_banner(window,compact=compact)"),
])

# Marcador final: evita ejecutar dos veces los parches acumulados sobre el mismo árbol.
with _MAIN_FILE.open('a', encoding='utf-8') as _main:
    _main.write('\n# REVELO_FIX07_COMPLETADO\n')

# FIX08 — consistencia de miniaturas, escala libre extendida, composición
# de fotografías giradas y coordenadas de pie de foto respecto a toda la hoja.
# Los cambios se aplican exclusivamente sobre el proyecto original en CI.

patch('photo_edits.py', [
    ("'print_scale': (0.25, 1.5)", "'print_scale': (0.05, 8.0)"),
])

patch('photo_editor_ui.py', [
    ("self._range(inside,'Escala de impresión', 'print_scale', .25, 1.50, resolution=.05)",
     "self._range(inside,'Escala de impresión', 'print_scale', .05, 8.00, resolution=.05)"),
])

patch('layout_editor.py', [
    ('photo_scales={p:max(.25,min(1.5,', 'photo_scales={p:max(.05,min(8.0,'),
    ('to=150 if is_free else 80,resolution=1', 'to=800 if is_free else 80,resolution=1'),
    ('to=150 if is_free else 80,', 'to=800 if is_free else 80,'),
    ('photo_scales[paths[i]]=max(.25,min(1.5,val/100))',
     'photo_scales[paths[i]]=max(.05,min(8.0,val/100))'),
    ('photo_scales[paths[index]]=round(max(.25,min(1.5,base*factor)),4)',
     'photo_scales[paths[index]]=round(max(.05,min(8.0,base*factor)),4)'),
])

patch('caption_editor.py', [
    ('photo_scale_slider=tk.Scale(scale_row,from_=25,to=150 if unified else 100',
     'photo_scale_slider=tk.Scale(scale_row,from_=5 if unified else 25,to=800 if unified else 100'),
    ('scale_spin=tk.Spinbox(scale_row,from_=25,to=150 if unified else 100',
     'scale_spin=tk.Spinbox(scale_row,from_=5 if unified else 25,to=800 if unified else 100'),
    ('min(150 if unified else 100,starting+delta*100/width)',
     'min(800 if unified else 100,starting+delta*100/width)'),
    ('round(max(25,min(800 if unified else 100,starting+delta*100/width))))',
     'round(max(5 if unified else 25,min(800 if unified else 100,starting+delta*100/width))))'),
])

patch('main.py', [
    # El diseño y número de fotos forman parte de la identidad visual de
    # la miniatura, aunque el conjunto de fotos no haya cambiado.
    ('        key = (tuple(group), sheet_index, self.paper.get(), self.orientation.get(),',
     '        key = (tuple(group), sheet_index, self.layout_template.get(), self.per_sheet.get(),\n'
     '               self.paper.get(), self.orientation.get(),'),
    ('        self._refresh_layout_button()\n        self.render_order()\n\n    def _on_template_changed',
     '        self._refresh_layout_button()\n        self.sheet_thumbnails.clear()\n        self.render_order()\n\n    def _on_template_changed'),
    ('        self._refresh_layout_button()\n        self.render_order()\n\n    def _on_layout_hint_resize',
     '        self._refresh_layout_button()\n        self.sheet_thumbnails.clear()\n        self.render_order()\n\n    def _on_layout_hint_resize'),
    ("            image = (self._sheet_thumbnail(group, sheet_number[path]-1)\n"
     "                     if (len(group) == 1 or (self.layout_template.get() == 'Diseño libre'\n"
     "                           and any(p in self.layout_items for p in group)))\n"
     "                     else self.thumbnails_small[path])",
     "            # Mostrar siempre la hoja REAL en ambos diseños; cambiar\n"
     "            # libre/cuadrícula no debe dejar la miniatura anterior.\n"
     "            image = self._sheet_thumbnail(group, sheet_number[path]-1)"),
])

patch('advanced_layout.py', [
    # Formato optativo: los proyectos antiguos siguen con coordenadas locales.
    ('    for key in ("title_x", "title_y", "detail_x", "detail_y"):',
     '    if "position_space" in spec:\n'
     '        if spec["position_space"] not in ("page", "photo"):\n'
     '            raise ValueError("Sistema de posición de pie de foto incorrecto")\n'
     '        clean["position_space"] = spec["position_space"]\n'
     '    for key in ("title_x", "title_y", "detail_x", "detail_y"):'),
    # La caja del texto se ajusta a su anchura, en vez de ocupar el 86 % de
    # la hoja: se puede llevar de verdad a cualquier esquina imprimible.
    ('                rw=min(max_width,max(40,round(w*.86)))',
     '                measured=max((draw.textlength(line, font=fonts[key])\n'
     '                              for line in txt.splitlines()), default=0)\n'
     '                rw=min(max_width,max(40,min(round(w*.78),round(measured+pad*3))))'),
])

patch('processor.py', [
    # Capturas personalizadas modernas: coordenadas de la hoja, no de celda.
    ('    lowres=False\n    # Renderizar de atrás hacia delante según z (persistente en proyectos y PDF).',
     '    lowres=False\n    page_captions=[]\n'
     '    # Renderizar de atrás hacia delante según z (persistente en proyectos y PDF).'),
    # Reemplazar el cálculo pesado de una imagen girada por una transformación
    # directa exclusivamente de los píxeles visibles dentro de la hoja.
    ("            photo=(content.resize(usable,Image.Resampling.LANCZOS) if spec.get('stretch',False)\n"
     "                   else ImageOps.contain(content,usable,Image.Resampling.LANCZOS)).convert('RGBA')\n"
     "            try:\n"
     "                rotated=photo.rotate(-float(spec.get('angle',0.)),Image.Resampling.BICUBIC,expand=True)\n"
     "                try:\n"
     "                    px=round(x0+zone_w*cx-rotated.width/2)\n"
     "                    py=round(y0+zone_h*cy-footer/2-rotated.height/2)\n"
     "                    sheet.paste(rotated,(px,py),rotated)\n"
     "                finally:rotated.close()\n"
     "            finally:photo.close()",
     "            from revelo_free_layers import editing_alpha, visible_photo_patch\n"
     "            alpha=editing_alpha(path,opts.photo_edits.get(path),content.size)\n"
     "            try:\n"
     "                visible=visible_photo_patch(content,alpha,(0,0,out_w,out_h),\n"
     "                    (x0+zone_w*cx,y0+zone_h*cy-footer/2),usable,\n"
     "                    float(spec.get('angle',0.)),stretch=bool(spec.get('stretch',False)))\n"
     "                if visible is not None:\n"
     "                    cropped,origin=visible\n"
     "                    try:sheet.paste(cropped,origin,cropped.getchannel('A'))\n"
     "                    finally:cropped.close()\n"
     "            finally:\n"
     "                if alpha is not None:alpha.close()"),
    ("        if has_caption(cap):\n"
     "            left=round(x0+zone_w*cx-bw/2)",
     "        if has_caption(cap):\n"
     "            if cap.get('placement')=='Personalizado' and cap.get('position_space')=='page':\n"
     "                page_captions.append(cap)\n"
     "                continue\n"
     "            left=round(x0+zone_w*cx-bw/2)"),
    ("    draw_page_number(sheet,printed_number,placement=opts.numbering_position,\n"
     "                     physical_mm=physical,page_index=page_index,\n"
     "                     number_format=opts.numbering_format)\n"
     "    return sheet,physical,lowres",
     "    # Los textos libres se dibujan al final, siempre por encima del collage.\n"
     "    for cap in page_captions:\n"
     "        draw_caption(sheet,(0,0,out_w,out_h),cap,mode='Personalizado',\n"
     "                     px_per_mm=out_w/w_mm)\n"
     "    draw_page_number(sheet,printed_number,placement=opts.numbering_position,\n"
     "                     physical_mm=physical,page_index=page_index,\n"
     "                     number_format=opts.numbering_format)\n"
     "    return sheet,physical,lowres"),
    # También en cuadrícula se admite una posición personalizada de página.
    ('    lowres_any = False\n    for idx, path in enumerate(paths):',
     '    lowres_any = False\n    page_captions=[]\n    for idx, path in enumerate(paths):'),
    ('        draw_caption(sheet, (cx0,cy0,cx1,cy1), cap,\n'
     '                     mode=cap.get("placement", "Debajo") if cap else "Debajo",\n'
     '                     px_per_mm=out_w/w_mm, below_start_y=below_caption_start)',
     '        if cap and cap.get("placement")=="Personalizado" and cap.get("position_space")=="page":\n'
     '            page_captions.append(cap)\n'
     '        else:\n'
     '            draw_caption(sheet, (cx0,cy0,cx1,cy1), cap,\n'
     '                         mode=cap.get("placement", "Debajo") if cap else "Debajo",\n'
     '                         px_per_mm=out_w/w_mm, below_start_y=below_caption_start)'),
    ('    draw_page_number(sheet, printed_number, placement=opts.numbering_position,\n'
     '                     physical_mm=(w_mm,h_mm), page_index=page_index, number_format=opts.numbering_format)\n'
     '    return sheet, (w_mm, h_mm), lowres_any',
     '    for cap in page_captions:\n'
     '        draw_caption(sheet,(0,0,out_w,out_h),cap,mode="Personalizado",\n'
     '                     px_per_mm=out_w/w_mm)\n'
     '    draw_page_number(sheet, printed_number, placement=opts.numbering_position,\n'
     '                     physical_mm=(w_mm, h_mm), page_index=page_index,\n'
     '                     number_format=opts.numbering_format)\n'
     '    return sheet, (w_mm, h_mm), lowres_any'),
])

patch('layout_editor.py', [
    # Imágenes del editor y del PDF comparten la máscara; blancos rotados
    # transparentan el fondo de papel, sin introducir un color propio.
    ('    thumbs=[]\n    for p in paths:',
     '    thumbs=[]\n    alpha_thumbs=[]\n    for p in paths:'),
    ('        photo.thumbnail((760,760),Image.Resampling.LANCZOS)\n        thumbs.append(photo)',
     '        photo.thumbnail((760,760),Image.Resampling.LANCZOS)\n'
     '        from revelo_free_layers import editing_alpha\n'
     '        alpha_thumbs.append(editing_alpha(p,opts.photo_edits.get(p),photo.size))\n'
     '        thumbs.append(photo)'),
    ("            fitted=(img.resize((iw,ih),Image.Resampling.BILINEAR) if is_free and state[paths[i]].get('stretch',False)\n"
     "                    else ImageOps.contain(img,(iw,ih),Image.Resampling.BILINEAR))\n"
     "            if is_free and abs(deg)>0.5:\n"
     "                with_alpha=fitted.convert('RGBA')\n"
     "                fitted.close()\n"
     "                fitted=with_alpha.rotate(-deg,Image.Resampling.BICUBIC,expand=True)\n"
     "            rendered=ImageTk.PhotoImage(fitted)\n"
     "            photos.append(rendered)\n"
     "            cx=(unrotated[0]+unrotated[2])//2\n"
     "            cy=(unrotated[1]+unrotated[3])//2\n"
     "            canvas.create_image(cx,cy,image=rendered,anchor='center')\n"
     "            fitted.close()",
     "            cx=(unrotated[0]+unrotated[2])//2\n"
     "            cy=(unrotated[1]+unrotated[3])//2\n"
     "            if is_free:\n"
     "                from revelo_free_layers import visible_photo_patch\n"
     "                visible=visible_photo_patch(img,alpha_thumbs[i],(x,y,x+w,y+h),\n"
     "                    (cx,cy),(iw,ih),deg,stretch=True)\n"
     "                if visible is not None:\n"
     "                    fitted,origin=visible\n"
     "                    try:\n"
     "                        rendered=ImageTk.PhotoImage(fitted)\n"
     "                        photos.append(rendered)\n"
     "                        canvas.create_image(*origin,image=rendered,anchor='nw')\n"
     "                    finally:fitted.close()\n"
     "            else:\n"
     "                fitted=ImageOps.contain(img,(iw,ih),Image.Resampling.BILINEAR)\n"
     "                try:\n"
     "                    rendered=ImageTk.PhotoImage(fitted)\n"
     "                    photos.append(rendered)\n"
     "                    canvas.create_image(cx,cy,image=rendered,anchor='center')\n"
     "                finally:fitted.close()"),
    ('        for photo in thumbs:photo.close()\n        dialog.destroy()',
     '        for photo in thumbs:photo.close()\n'
     '        for alpha in alpha_thumbs:\n'
     '            if alpha is not None:alpha.close()\n'
     '        dialog.destroy()'),
])

patch('caption_editor.py', [
    ('def _edit_positions(parent: tk.Toplevel, path: Path, spec: dict, opts: ExportOptions,\n'
     '                    on_commit) -> None:',
     'def _edit_positions(parent: tk.Toplevel, path: Path, spec: dict, opts: ExportOptions,\n'
     '                    on_commit, *, page_paths=None, page_index=0) -> None:'),
    ('        base, (wmm,hmm), _=render_print_image(path,opts,preview_max_size=(780,570))',
     '        from dataclasses import replace\n'
     '        group=tuple(page_paths or (path,))\n'
     '        # No pintar dos veces el texto que estamos moviendo.\n'
     '        captions=dict(opts.captions)\n'
     '        captions[path]={"title":"","detail":"","placement":"Personalizado"}\n'
     '        base, (wmm,hmm), _=render_layout_page(group,replace(opts,captions=captions),\n'
     '            page_index=page_index,preview_max_size=(780,570))'),
    # Convertir posiciones locales antiguas a coordenadas de hoja al entrar
    # en el editor libre; conservar el formato original si se cancela.
    ('    current_photo=[None]\n    bounds=[0,0,1,1]',
     '    if spec.get("position_space") != "page" and len(group)>1:\n'
     '        if opts.layout_template=="Diseño libre":\n'
     '            from layout_editor import free_default,validate_layout_item\n'
     '            idx=group.index(path)\n'
     '            loc=validate_layout_item(opts.layout_items.get(path)).get(\n'
     '                "rect",free_default(idx,len(group))["rect"])\n'
     '            for label in ("title","detail"):\n'
     '                px=positions[label+"_x"];py=positions[label+"_y"]\n'
     '                positions[label+"_x"]=max(0,min(1,loc[0]+(px-.5)*loc[2]))\n'
     '                positions[label+"_y"]=max(0,min(1,loc[1]+(py-.5)*loc[3]))\n'
     '    current_photo=[None]\n    bounds=[0,0,1,1]'),
    ('            payload=dict(spec,placement=\'Personalizado\',**positions)',
     '            payload=dict(spec,placement=\'Personalizado\',**positions)\n'
     '            payload[\'position_space\']=\'page\''),
    ('            on_commit(dict(positions))',
     '            on_commit(dict(positions, position_space="page"))'),
    ('        _edit_positions(dialog,path,data,opts,saved_pos)',
     '        _edit_positions(dialog,path,data,opts,saved_pos,\n'
     '                        page_paths=page_paths,page_index=page_index)'),
    # Guardar la nueva coordenada sin modificar proyectos antiguos sólo por abrir.
    ("    positions={k:spec.get(k,default) for k,default in (\n"
     "        ('title_x',.5),('title_y',.84),('detail_x',.5),('detail_y',.92))}",
     "    positions={k:spec.get(k,default) for k,default in (\n"
     "        ('title_x',.5),('title_y',.84),('detail_x',.5),('detail_y',.92))}\n"
     "    if spec.get('position_space')=='page':positions['position_space']='page'"),
    # Marco real de la fotografía seleccionada en libre, con giro y escala.
    ('                photo_handle[:]=[right,bottom]\n                preview_canvas.create_rectangle(left,top,right,bottom,outline=ACCENT,width=2)',
     '                if new_opts.layout_template=="Diseño libre":\n'
     '                    from layout_editor import free_default,visible_photo_geometry,validate_layout_item\n'
     '                    from photo_edits import transformed_dimensions\n'
     '                    ls=validate_layout_item(new_opts.layout_items.get(path))\n'
     '                    loc=ls.get("rect",free_default(idx,len(group))["rect"])\n'
     '                    try:\n'
     '                        with Image.open(path) as original:\n'
     '                            iw0,ih0=original.size\n'
     '                            if original.getexif().get(274) in (5,6,7,8):iw0,ih0=ih0,iw0\n'
     '                        sw0,sh0=transformed_dimensions((iw0,ih0),edits.get(path))\n'
     '                    except (OSError,ValueError):sw0,sh0=max(1,int(cw)),max(1,int(ch))\n'
     '                    actual_scale=(float(edits.get(path,{}).get("print_scale",1.0))*\n'
     '                                  float(spec_now.get("photo_scale",1.0)))\n'
     '                    _,outer=visible_photo_geometry(zone,\n'
     '                        [loc[0],loc[1],loc[2]*actual_scale,loc[3]*actual_scale],\n'
     '                        (sw0,sh0),ls.get("angle",0),stretch=ls.get("stretch",False))\n'
     '                    left,top,right,bottom=(xx+outer[0],yy+outer[1],\n'
     '                                           xx+outer[2],yy+outer[3])\n'
     '                photo_handle[:]=[right,bottom]\n'
     '                preview_canvas.create_rectangle(left,top,right,bottom,outline=ACCENT,width=2)'),
])

# Encoger libremente hasta el 5% (nunca una imagen de 0 píxeles).
patch('layout_editor.py', [
    ('size_slider=tk.Scale(toolbar,from_=25 if is_free else 20',
     'size_slider=tk.Scale(toolbar,from_=5 if is_free else 20'),
    ('size_input=tk.Spinbox(toolbar,from_=25 if is_free else 20',
     'size_input=tk.Spinbox(toolbar,from_=5 if is_free else 20'),
    ('current_scale=max(.25,photo_scales[paths[index]])',
     'current_scale=max(.05,photo_scales[paths[index]])'),
])

# Seguridad de memoria: también en vista normal y cuadrícula.
patch('processor.py', [
    ('        if opts.binding and opts.fit == "Ampliar fondo (sin recortar)":',
     '        if print_scale>2.0:\n            from revelo_free_layers import editing_alpha,visible_photo_patch\n            blurred=(opts.fit=="Ampliar fondo (sin recortar)" or\n                     (opts.fit=="Ajustar (sin recortar)" and opts.paper_background=="Difuminado"))\n            page=(_extended_background(working,(out_w,out_h)) if blurred else\n                  Image.new("RGB",(out_w,out_h),paper_background_color(opts)\n                     if opts.fit=="Ajustar (sin recortar)" else "white"))\n            alpha=editing_alpha(path,opts.photo_edits.get(path),working.size)\n            try:\n                scaled=visible_photo_patch(working,alpha,box,\n                    ((box[0]+box[2])/2,(box[1]+box[3])/2),\n                    ((box[2]-box[0])*print_scale,(box[3]-box[1])*print_scale))\n                if scaled is not None:\n                    tile,pos=scaled\n                    try:page.paste(tile,pos,tile.getchannel("A"))\n                    finally:tile.close()\n            finally:\n                if alpha is not None:alpha.close()\n            return page,(w_mm,h_mm),low_resolution\n        if opts.binding and opts.fit == "Ampliar fondo (sin recortar)":'),
    ("            if (cap and cap.get('placement', 'Debajo') == 'Debajo'\n                    and opts.fit == 'Ajustar (sin recortar)'):",
     '            if photo_scale>2.0:\n                from revelo_free_layers import editing_alpha,visible_photo_patch\n                alpha=editing_alpha(path,opts.photo_edits.get(path),content.size)\n                try:\n                    region=visible_photo_patch(content,alpha,\n                        (cx0,cy0,cx1,photo_bottom),\n                        ((cx0+cx1)/2,(cy0+photo_bottom)/2),\n                        (cw*photo_scale,photo_ch*photo_scale))\n                    if region is not None:\n                        tile,pos=region\n                        try:sheet.paste(tile,pos,tile.getchannel("A"))\n                        finally:tile.close()\n                finally:\n                    if alpha is not None:alpha.close()\n            elif (cap and cap.get(\'placement\', \'Debajo\') == \'Debajo\'\n                    and opts.fit == \'Ajustar (sin recortar)\'):'),
])

with _MAIN_FILE.open('a', encoding='utf-8') as _main:
    _main.write('\n# REVELO_FIX08_COMPLETADO\n')


# FIX09 — compatibilidad de pruebas de la antigua escala de 25 %.
# El FIX08 ha ampliado el deslizador libre y el del editor de texto a 5-800 %.
# Dos pruebas antiguas seguían localizando el control por su mínimo de 25 %
# y fallaban ANTES de verificar el guardado. No se eliminan las pruebas:
# se actualiza la identificación del control y se comprueba también su máximo.
patch('tests/test_v175_fix03_shared_views.py', [
    ("if isinstance(w,tk.Scale) and int(float(w.cget('from')))==25:\n"
     "                size_controls.append(w)",
     "if (isinstance(w,tk.Scale) and int(float(w.cget('from')))==5\n"
     "                    and int(float(w.cget('to')))==800):\n"
     "                size_controls.append(w)"),
    ("if isinstance(w,tk.Scale) and int(float(w.cget('from')))==25:\n"
     "                scale_controls.append(w)",
     "if (isinstance(w,tk.Scale) and int(float(w.cget('from')))==5\n"
     "                    and int(float(w.cget('to')))==800):\n"
     "                scale_controls.append(w)"),
])

# FIX10 — renderizado y geometría compartidos. El archivo de aplicación
# falla explícitamente si falta un patrón, antes de lanzar pytest/PyInstaller.
from revelo_fix10_apply import apply_all as _apply_fix10
_apply_fix10(patch, replace_section)
with _MAIN_FILE.open('a', encoding='utf-8') as _main:
    _main.write('\n# REVELO_FIX10_COMPLETADO\n')

# FIX12 — asegurar loopback real para el servidor QR cuando el host es local.
# En producción conserva la escucha por todas las interfaces para iPhone/Wi-Fi.
patch('mobile_import.py', [
    ("self.http = ThreadingHTTPServer(('0.0.0.0', 0), Handler)",
     "self.http = ThreadingHTTPServer((\n"
     "    '127.0.0.1' if self.host == '127.0.0.1' else '0.0.0.0',\n"
     "    0), Handler)"),
])

# Ejercitar la seguridad del QR con una conexión directa al loopback,
# evitando proxies automáticos de urllib en los runners de GitHub Actions.
replace_section('tests/test_mobile_import.py',
    'def test_invalid_file_and_bad_extension_rejected(tmp_path):',
    '\n\ndef test_safe_names_and_revelo_exts():',
'''def test_invalid_file_and_bad_extension_rejected(tmp_path):
    """Cada rechazo HTTP debe responder con su código y no guardar archivos.

    Usamos una conexión directa 127.0.0.1, no el proxy HTTP que pueda estar
    configurado en la máquina de GitHub. Si hay un timeout se reabre el socket;
    nunca se considera aprobado un silencio del servidor.
    """
    from http.client import HTTPConnection
    received = []
    server = PhoneTransferServer(tmp_path / 'incoming', received.append, host='127.0.0.1')
    try:
        assert server.http.server_address[0] == '127.0.0.1'
        for name, contents, expected in [('no_es_una_foto.jpg', b'xxx', 422),
                                          ('script.exe', _image_bytes(), 415)]:
            last_error = None
            for attempt in range(3):
                connection = HTTPConnection('127.0.0.1', server.port, timeout=8)
                try:
                    connection.request('POST', '/upload?t=' + server.token,
                                       body=contents,
                                       headers={'X-Filename': name,
                                                'Content-Type': 'application/octet-stream'})
                    response = connection.getresponse()
                    actual = response.status
                    message = response.read()
                    assert actual == expected, (name, actual, expected, message)
                    assert b'error' in message, (name, message)
                    last_error = None
                    break
                except (TimeoutError, socket.timeout, ConnectionError, OSError) as err:
                    last_error = err
                    if attempt < 2:
                        time.sleep(0.15 * (attempt + 1))
                finally:
                    connection.close()
            if last_error is not None:
                raise AssertionError(f'{name}: el servidor local no respondió tras 3 intentos') from last_error
        assert len(received) == 0
        assert list((tmp_path / 'incoming').iterdir()) == []
    finally:
        server.stop()
''')
