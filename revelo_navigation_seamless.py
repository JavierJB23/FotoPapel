"""Revelo v1.10.0 BLOCK02 FIX04 — navegación continua con aislamiento de hojas.

Se ejecuta DESPUÉS de FIX03 y los módulos de fondos anteriores. No cambia el
formato de proyectos: los fondos asociados a fotos ya se guardan en .revelo.
Se conservan los contratos antiguos de edit_sheet sin seamless_navigation.
"""


def with_page_background(current, paths, choice, color):
    """Copia los fondos y modifica SOLO las fotos de la hoja elegida.

    Usar el mismo fondo en todas las fotos de una hoja de diseño libre hace que
    sus regiones de fondo cubran el papel sin tocar las fotografías ni textos.
    """
    from revelo_backgrounds import PRESETS, validate_background_spec

    result = {p: dict(spec) for p, spec in current.items()}
    if choice == 'Según encaje':
        spec = {}
    elif choice == 'Personalizado':
        spec = validate_background_spec({'mode': 'Color', 'color': color,
                                         'opacity': 100})
    elif choice in PRESETS:
        spec = validate_background_spec({'mode': 'Color',
                                         'color': PRESETS[choice], 'opacity': 100})
    elif choice == 'Difuminado':
        spec = validate_background_spec({'mode': 'Difuminado', 'opacity': 100})
    else:
        raise ValueError('Fondo de hoja no reconocido: ' + str(choice))
    for p in paths:
        if spec:
            result[p] = dict(spec)
        else:
            result.pop(p, None)
    return result


def apply_seamless(patch):
    """Cambios de integración posteriores a FIX03, conservando compatibilidad."""
    patch('main.py', [
        ('    def edit_page_layout(self, *, page_path=None, editor_geometry=None):\n',
         '    def edit_page_layout(self, *, page_path=None, editor_geometry=None, editor_window=None):\n'),
        ('''        def save(result, *, photo_scales=None, background_choice=None):''',
         '''        def save(result, *, photo_scales=None, background_choice=None,
                 background_modified=False):'''),
        ('''            if background_choice is not None and self.fit.get() == 'Ajustar (sin recortar)':
                bg, color = background_choice
                if bg != 'Según encaje':
                    self.paper_background_color.set(color)
                    self.paper_background.set(bg)
''',
         '''            # «Fondo de la hoja» es LOCAL en Diseño libre. Una simple
            # navegación/guardado sin cambios nunca debe alterar los fondos
            # individuales de otra hoja ni el desplegable global del menú.
            if (background_modified and background_choice is not None and
                    self.fit.get() == 'Ajustar (sin recortar)'):
                from revelo_navigation_seamless import with_page_background
                bg, color = background_choice
                self.background_overrides = with_page_background(
                    self.background_overrides, selected_group, bg, color)
'''),
        ('''        def save_shared(scales, background):
            shared['photo_scales'] = scales
            shared['background_choice'] = background
''',
         '''        def save_shared(scales, background, background_modified=False):
            shared['photo_scales'] = scales
            shared['background_choice'] = background
            shared['background_modified'] = background_modified
'''),
        ('''        def navigate_page(direction, geometry):
            target_index=group_index+direction
            if target_index < 0 or target_index >= len(groups):
                return
            target_path=groups[target_index][0]
            self.order_selected=target_path
            def open_next_sheet():
                if self.root.winfo_exists() and target_path in self.pages:
                    self.edit_page_layout(page_path=target_path, editor_geometry=geometry)
            self.root.after_idle(open_next_sheet)
''',
         '''        def navigate_page(direction, geometry):
            target_index=group_index+direction
            if target_index < 0 or target_index >= len(groups):
                return
            target_path=groups[target_index][0]
            self.order_selected=target_path
            if hasattr(geometry, 'winfo_exists'):
                # Mismo Toplevel: ni cerrar ni abrir ventanas. Los controles
                # internos se reconstruyen de forma síncrona en esta hoja.
                if geometry.winfo_exists() and target_path in self.pages:
                    self.edit_page_layout(page_path=target_path, editor_window=geometry)
            else:
                # Compatibilidad con consumidores/pruebas antiguas que pasan
                # la geometría como cadena y esperan la apertura diferida.
                def open_next_sheet():
                    if self.root.winfo_exists() and target_path in self.pages:
                        self.edit_page_layout(page_path=target_path, editor_geometry=geometry)
                self.root.after_idle(open_next_sheet)
'''),
        ('''                   on_navigate=navigate_page if template=="Diseño libre" else None,
                   has_previous=group_index>0, has_next=group_index<len(groups)-1,
                   editor_geometry=editor_geometry)''',
         '''                   on_navigate=navigate_page if template=="Diseño libre" else None,
                   has_previous=group_index>0, has_next=group_index<len(groups)-1,
                   editor_geometry=editor_geometry, reuse_dialog=editor_window,
                   seamless_navigation=template=="Diseño libre")'''),
    ])
    patch('layout_editor.py', [
        ('''               on_navigate=None, has_previous=False, has_next=False,
               editor_geometry=None):''',
         '''               on_navigate=None, has_previous=False, has_next=False,
               editor_geometry=None, reuse_dialog=None, seamless_navigation=False):'''),
        ('''    custom_color=[opts.paper_background_color]
''',
         '''    custom_color=[opts.paper_background_color]
    # Una hoja puede tener un fondo común sin convertirlo en fondo GLOBAL.
    # Si hay dos fondos distintos u opacidades especiales, se conservan tal
    # cual: NO se unifican por abrir/cambiar de página.
    if is_free:
        from revelo_backgrounds import PRESETS
        _page_specs = [opts.background_overrides.get(p, {}) for p in paths]
        if (_page_specs and _page_specs[0] and
                all(s == _page_specs[0] for s in _page_specs) and
                _page_specs[0].get('opacity',100) == 100):
            _spec = _page_specs[0]
            if _spec.get('mode') == 'Color':
                _hex = _spec.get('color', '#FFFFFF').upper()
                custom_color[0] = _hex
                background.set(next((key for key,value in PRESETS.items()
                                     if value.upper() == _hex), 'Personalizado'))
            elif _spec.get('mode') == 'Difuminado':
                background.set('Difuminado')
    background_dirty=[False]
    background.trace_add('write', lambda *_: background_dirty.__setitem__(0, True))
'''),
        ('''    dialog=tk.Toplevel(parent)
    dialog.title('Revelo · Tamaño de fotos' if not is_free else 'Revelo · Diseño libre')
    dialog.geometry(editor_geometry or '1060x720')''',
         '''    # Una sola ventana física: la navegación cambia SU contenido.
    # El bucle de eventos repinta todo al finalizar el callback, sin un cierre
    # o una ventana nueva que produzcan saltos visuales en Windows.
    if reuse_dialog is not None and reuse_dialog.winfo_exists():
        dialog=reuse_dialog
        for child in list(dialog.winfo_children()):
            child.destroy()
    else:
        dialog=tk.Toplevel(parent)
    dialog.title('Revelo · Tamaño de fotos' if not is_free else 'Revelo · Diseño libre')
    if reuse_dialog is None:
        dialog.geometry(editor_geometry or '1060x720')'''),
        ('''                    on_shared_save(dict(photo_scales),
                                   (background.get(),custom_color[0]))''',
         '''                    on_shared_save(dict(photo_scales),
                                   (background.get(),custom_color[0]),
                                   background_dirty[0])'''),
        ('''        old_geometry=dialog.geometry() if navigate else None
        dialog.destroy()
        if navigate and on_navigate is not None:
            on_navigate(navigate, old_geometry)''',
         '''        if navigate and on_navigate is not None and seamless_navigation:
            # Los datos y máscaras ya están liberados. Reutilizar el Toplevel
            # en el mismo callback evita la sensación de cerrar/abrir.
            on_navigate(navigate, dialog)
        else:
            old_geometry=dialog.geometry() if navigate else None
            dialog.destroy()
            if navigate and on_navigate is not None:
                on_navigate(navigate, old_geometry)'''),
        ('''                photo_scales,background.get(),custom_color[0],(w,h),
                page_index=page_index)''',
         '''                photo_scales,background.get(),custom_color[0],(w,h),
                page_index=page_index, background_dirty=background_dirty[0])'''),
    ])
    patch('revelo_shared_layout.py', [
        ('''def editor_options(opts, paths, template, state, ratios, scales, background, color):''',
         '''def editor_options(opts, paths, template, state, ratios, scales,
                   background, color, background_dirty=False):'''),
        ('''    return replace(opts, layout_template=template, layout_items=layouts,
                   photo_edits=photo_edits, captions=captions,
                   paper_background=paper_background,
                   paper_background_color=color if background=='Personalizado'
                   else opts.paper_background_color)''',
         '''    overrides = dict(getattr(opts, 'background_overrides', {}))
    if template == 'Diseño libre' and background_dirty:
        from revelo_navigation_seamless import with_page_background
        overrides = with_page_background(overrides, paths, background, color)
    return replace(opts, layout_template=template, layout_items=layouts,
                   photo_edits=photo_edits, captions=captions,
                   background_overrides=overrides,
                   paper_background=paper_background,
                   paper_background_color=color if background=='Personalizado'
                   else opts.paper_background_color)'''),
        ('''                        color, size, *, page_index=0):''',
         '''                        color, size, *, page_index=0, background_dirty=False):'''),
        ('''                             background, color)
''',
         '''                             background, color, background_dirty)
'''),
    ])
