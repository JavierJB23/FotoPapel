"""Integración de fondos de página y por foto sobre la base STABLE v1.9.0.

Los anclajes son exactos y verificables: una coincidencia errónea aborta la
compilación antes de iniciar la batería de pruebas, sin alterar el ejecutable.
"""


def apply_v110(patch, replace_section):
    patch('processor.py', [
        ('    paper_background_color: str = "#FFFFFF"\n\n    def validate(self) -> None:',
         '    paper_background_color: str = "#FFFFFF"\n'
         '    # Fondos voluntarios que no alteran el comportamiento de proyectos antiguos.\n'
         '    background_global: dict = field(default_factory=dict)\n'
         '    background_overrides: dict[Path, dict] = field(default_factory=dict)\n\n'
         '    def validate(self) -> None:'),
        ('        if self.fmt not in ("Imagenes", "PDF", "Word"):',
         '        from revelo_backgrounds import validate_background_spec\n'
         '        validate_background_spec(self.background_global)\n'
         '        for value in self.background_overrides.values():\n'
         '            validate_background_spec(value)\n'
         '        if self.fmt not in ("Imagenes", "PDF", "Word"):'),
        ('    return export_word(paths, opts, dest, progress)\n',
'''    return export_word(paths, opts, dest, progress)


# v1.10: capa de fondo optativa alrededor del motor estable. Si el proyecto
# no tiene capas, la ruta original se ejecuta sin reprocesar ningún píxel.
_stable_render_print_image = render_print_image
_stable_render_layout_page = render_layout_page


def render_print_image(path, opts, *, preview_max_size=None, page_index=0):
    from revelo_backgrounds import active_backgrounds, compose_backgrounds
    if not active_backgrounds((path,), opts):
        return _stable_render_print_image(path, opts,
                         preview_max_size=preview_max_size, page_index=page_index)
    return compose_backgrounds((path,), opts,
        lambda options: _stable_render_print_image(path, options,
                   preview_max_size=preview_max_size, page_index=page_index),
        page_index=page_index)


def render_layout_page(paths, opts, *, preview_max_size=None, page_index=0,
                       printed_number=None):
    from revelo_backgrounds import active_backgrounds, compose_backgrounds
    if not active_backgrounds(paths, opts):
        return _stable_render_layout_page(paths, opts,
                 preview_max_size=preview_max_size, page_index=page_index,
                 printed_number=printed_number)
    return compose_backgrounds(paths, opts,
        lambda options: _stable_render_layout_page(paths, options,
                   preview_max_size=preview_max_size, page_index=page_index,
                   printed_number=printed_number), page_index=page_index)
'''),
    ])

    patch('thumbnail_preview.py', [
        ('    with Image.open(path) as raw:\n',
'''    # Una capa personalizada necesita el motor de composición compartido.
    # La ruta rápida antigua se conserva intacta en proyectos sin capas.
    from revelo_backgrounds import active_backgrounds
    if active_backgrounds((path,), opts):
        from processor import render_print_image
        preview, _, _ = render_print_image(path, opts,
                                preview_max_size=max_size, page_index=page_index)
        return preview
    with Image.open(path) as raw:
'''),
    ])

    patch('main.py', [
        ('        self.layout_items: dict[Path,dict] = {}\n',
         '        self.layout_items: dict[Path,dict] = {}\n'
         '        self.background_global: dict = {}\n'
         '        self.background_overrides: dict[Path,dict] = {}\n'
         '        self.background_window: tk.Toplevel | None = None\n'),
        ('        self._label(editorial_heading, "Configuración de impresión", size=15,\n'
         '                    family="Georgia", weight="bold").pack(side="left")',
         '        self._label(editorial_heading, "Configuración de impresión", size=15,\n'
         '                    family="Georgia", weight="bold").pack(side="left")\n'
         '        self.background_btn = self._button(\n'
         '            editorial_heading, "Fondos por foto · opacidad", self.open_backgrounds, small=True)\n'
         '        self.background_btn.pack(side="right")'),
        ('    def _update_paper_background_controls(self):\n',
'''    def open_backgrounds(self, path=None):
        """Editor de fondos; conserva el resto de la configuración de impresión."""
        from revelo_background_ui import open_background_editor
        return open_background_editor(self, path)

    def _update_paper_background_controls(self):
'''),
        ('        for button in (self.add_btn, self.special_btn, self.mobile_btn,\n',
         '        for button in (self.background_btn, self.add_btn, self.special_btn, self.mobile_btn,\n'),
        ('            layout_items={path:dict(spec) for path,spec in self.layout_items.items()},\n',
         '            layout_items={path:dict(spec) for path,spec in self.layout_items.items()},\n'
         '            background_global=dict(self.background_global),\n'
         '            background_overrides={path:dict(spec) for path,spec in self.background_overrides.items()},\n'),
        ('        self.layout_items.pop(path, None)\n        if self.selected == path:',
         '        self.layout_items.pop(path, None)\n'
         '        self.background_overrides.pop(path, None)\n'
         '        if self.selected == path:'),
        ('            self.layout_items.clear()\n            self.selected = None',
         '            self.layout_items.clear()\n'
         '            self.background_overrides.clear()\n'
         '            self.background_global = {}\n'
         '            self.selected = None'),
        ('        layout_changed = dict(self.layout_items)\n\n        def worker():',
         '        layout_changed = dict(self.layout_items)\n'
         '        background_global = dict(self.background_global)\n'
         '        background_overrides = {p:dict(s) for p,s in self.background_overrides.items()}\n\n'
         '        def worker():'),
        ('                             captions=captions_changed, layout_items=layout_changed)',
         '                             captions=captions_changed, layout_items=layout_changed,\n'
         '                             background_global=background_global,\n'
         '                             background_overrides=background_overrides)'),
        ('        self.layout_items = loaded.get("layout_items", {})\n',
         '        self.layout_items = loaded.get("layout_items", {})\n'
         '        self.background_global = loaded.get("background_global", {})\n'
         '        self.background_overrides = loaded.get("background_overrides", {})\n'),
        ('        self._close_mobile_import()\n        self._close_qr_mode()\n        self._close_mobile_export()\n        self.mobile_temp.cleanup()\n',
         '        self._close_mobile_import()\n'
         '        self._close_qr_mode()\n'
         '        self._close_mobile_export()\n'
         '        if self.background_window is not None and self.background_window.winfo_exists():\n'
         '            self.background_window.destroy()\n'
         '        self.mobile_temp.cleanup()\n'),
        # El fondo común y los individuales comparten caché: al generar una nueva
        # hoja siempre usamos el mapa vigente, aun después de un cambio de estilo.
        ('               repr([self.layout_items.get(p, {}) for p in group]),\n',
         '               repr([self.layout_items.get(p, {}) for p in group]),\n'
         '               repr(self.background_global),\n'
         '               repr([self.background_overrides.get(p, {}) for p in group]),\n'),
    ])

    # Añadir el acceso junto al editor de texto de cada foto, conservando
    # los botones existentes y sin modificar su comportamiento.
    patch('main.py', [
        ('                self._button(card, "Texto / pie de foto" + (" ✓" if has_caption(self.captions.get(path)) else ""),\n'
         '                             lambda p=path: self.caption_dialog(p), small=True).pack(fill="x", pady=(4,0))',
         '                self._button(card, "Texto / pie de foto" + (" ✓" if has_caption(self.captions.get(path)) else ""),\n'
         '                             lambda p=path: self.caption_dialog(p), small=True).pack(fill="x", pady=(4,0))\n'
         '                self._button(card, "Fondo individual" + (" ✓" if self.background_overrides.get(path) else ""),\n'
         '                             lambda p=path: self.open_backgrounds(p), small=True).pack(fill="x", pady=(4,0))'),
    ])

    patch('project_io.py', [
        ('    layout_items: dict[Path, dict] | None = None,\n) -> Path:',
         '    layout_items: dict[Path, dict] | None = None,\n'
         '    background_global: dict | None = None,\n'
         '    background_overrides: dict[Path, dict] | None = None,\n) -> Path:'),
        ('    manifest = {\n        "format": "Revelo", "version": PROJECT_VERSION,',
'''    from revelo_background_project import pack_layers
    layer_global, layer_global_asset, layer_records, layer_assets = pack_layers(
        paths, background_global, background_overrides, total_bytes)
    for record, (layer_spec, layer_meta) in zip(records, layer_records):
        if layer_spec:
            record['paper_layer'] = layer_spec
            if layer_meta is not None:
                record['paper_layer_asset'] = layer_meta
    manifest = {
        "format": "Revelo", "version": PROJECT_VERSION,'''),
        ('        "settings": settings,\n    }\n    tempname:',
         '        "settings": settings,\n'
         '        "background_global": layer_global,\n'
         '        "background_global_asset": layer_global_asset,\n'
         '    }\n    tempname:'),
        ('            zipout.writestr(\'manifest.json\', json.dumps(manifest, ensure_ascii=False, indent=2))',
         '            for background_path, archive_name in layer_assets:\n'
         '                zipout.write(background_path, archive_name)\n'
         '            zipout.writestr(\'manifest.json\', json.dumps(manifest, ensure_ascii=False, indent=2))'),
        ("            if len(infos) > MAX_ITEMS * 2 + 1 or not any(i.filename == 'manifest.json' for i in infos):",
         "            if len(infos) > MAX_ITEMS * 3 + 3 or not any(i.filename == 'manifest.json' for i in infos):"),
        ('            count_bg = sum(bool(r.get(\'background_asset\')) for r in records if isinstance(r, dict))\n'
         '            if len(entries) != len(infos) or len(infos) != len(records) + count_bg + 1:',
         '            count_bg = sum(bool(r.get(\'background_asset\')) for r in records if isinstance(r, dict))\n'
         '            count_layers = sum(bool(r.get(\'paper_layer_asset\')) for r in records if isinstance(r, dict))\n'
         '            count_global = int(bool(manifest.get(\'background_global_asset\')))\n'
         '            if len(entries) != len(infos) or len(infos) != len(records) + count_bg + count_layers + count_global + 1:'),
        ('            layout_items = {}\n            from layout_editor import validate_layout_item',
         '            layout_items = {}\n'
         '            background_overrides = {}\n'
         '            from revelo_background_project import unpack_layer\n'
         '            from layout_editor import validate_layout_item'),
        ("                if kind == 'pdf_page':\n", 
'''                layer, layer_size = unpack_layer(archive, entries,
                    record.get('paper_layer'), record.get('paper_layer_asset'),
                    folder, f'{idx:05d}')
                total += layer_size
                if total > MAX_TOTAL_BYTES:
                    raise ProjectError('Los fondos superan el tamaño permitido')
                if layer:
                    background_overrides[path] = layer
                if kind == 'pdf_page':
'''),
        ('            # valida ajustes antes de alterar el estado de la aplicación\n',
'''            background_global, global_size = unpack_layer(archive, entries,
                manifest.get('background_global'), manifest.get('background_global_asset'),
                folder, 'global')
            total += global_size
            if total > MAX_TOTAL_BYTES:
                raise ProjectError('El proyecto supera el tamaño máximo permitido')
            # valida ajustes antes de alterar el estado de la aplicación
'''),
        ('                    layout_items=layout_items,\n                ).validate()',
         '                    layout_items=layout_items,\n'
         '                    background_global=background_global,\n'
         '                    background_overrides=background_overrides,\n'
         '                ).validate()'),
        ('                "layout_items": layout_items,\n                "settings": settings,',
         '                "layout_items": layout_items,\n'
         '                "background_global": background_global,\n'
         '                "background_overrides": background_overrides,\n'
         '                "settings": settings,'),
    ])

    # El motor estable de miniaturas no debe volver a dibujar otra paleta
    # distinta de la que se aplica en el papel compuesto.
