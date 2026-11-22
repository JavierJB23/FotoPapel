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
