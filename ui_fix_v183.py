"""REVELO v1.8.3: parche de interfaz reproducible para el repositorio original.

Se ejecuta en GitHub Actions antes de las pruebas y de PyInstaller.
No modifica el motor de impresión ni los datos de los proyectos.
"""
from pathlib import Path


def patch(path: str, changes: list[tuple[str, str]]) -> None:
    target = Path(__file__).resolve().parent / path
    content = target.read_text(encoding='utf-8')
    touched = 0
    for before, after in changes:
        if after in content:
            continue  # parche idempotente
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

# FIX03: En ventanas estrechas, el título de biblioteca ya no comparte la
# misma fila que los botones. Windows dejaba «Vaciar» sin mapear.
# Mantener ambas filas de botones y preservar el área derecha más ancha.
patch('main.py', [
    ('        title.pack(side="left")\n        library_heading = tk.Frame(title, bg=SURFACE)',
     '        title.pack(anchor="w")\n        library_heading = tk.Frame(title, bg=SURFACE)'),
    ('        buttons.pack(side="right")\n        files_row = tk.Frame(buttons, bg=SURFACE)',
     '        buttons.pack(fill="x", pady=(3, 0))\n        files_row = tk.Frame(buttons, bg=SURFACE)'),
    ('self.add_btn = self._button(files_row, "+ Añadir fotos / PDF",',
     'self.add_btn = self._button(files_row, "+ Añadir fotos",'),
    ('self.mobile_btn = self._button(lower_buttons, "Importar desde móvil · QR",',
     'self.mobile_btn = self._button(lower_buttons, "Móvil · QR",'),
])
