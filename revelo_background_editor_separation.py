"""Revelo v1.10 BLOCK02 FIX06: edición libre = geometría, fondos = su editor.

Esta revisión se ejecuta DESPUÉS de FIX05, por lo que sus anclajes se comprueban
contra el código efectivamente parcheado, no contra una versión antigua.
El esquema .revelo, el QR y los ajustes fotográficos permanecen intactos.
"""


def apply_fix06(patch, replace_section):
    # 1) Retirar físicamente el selector duplicado. Conservamos la cabecera,
    # barras de tamaño/giro y navegación de una sola ventana.
    replace_section(
        'layout_editor.py',
        "    if is_free:\n        bg_row=tk.Frame(dialog,bg=PANEL,padx=15,pady=7)\n",
        "    canvas=tk.Canvas(dialog,bg='#1B2F47',highlightthickness=0)",
        "    # Los fondos son de SOLO LECTURA en Composición libre.\n"
        "    # Se editan únicamente con 'Fondos por foto · opacidad'.\n",
    )

    # 2) El render del editor NO puede construir un fondo alternativo ni
    # sobrescribir las excepciones de las fotos por un selector de hoja.
    # Debe reproducir exactamente las capas del ExportOptions del documento.
    patch('revelo_shared_layout.py', [
        (
            "    if template == 'Diseño libre':\n"
            "        # Una ventana antigua puede tener un fondo específico en el primer\n"
            "        # elemento; la selección actual del usuario manda en la vista previa.\n"
            "        layouts[paths[0]].update(background=background,\n"
            "                                 background_color=color)\n"
            "    else:\n"
            "        layouts[paths[0]].update(ratios)\n",
            "    # Nunca generar cambios de fondo temporales desde Diseño libre.\n"
            "    if template != 'Diseño libre':\n"
            "        layouts[paths[0]].update(ratios)\n",
        ),
        (
            "    paper_background = (background if background not in ('Según encaje','Personalizado')\n"
            "                        else opts.paper_background)\n",
            "    # El papel general siempre procede de opts, igual que en exportación.\n",
        ),
        (
            "    overrides = dict(getattr(opts, 'background_overrides', {}))\n"
            "    if template == 'Diseño libre' and background_dirty:\n"
            "        from revelo_navigation_seamless import with_page_background\n"
            "        overrides = with_page_background(overrides, paths, background, color)\n"
            "    return replace(opts, layout_template=template, layout_items=layouts,\n"
            "                   photo_edits=photo_edits, captions=captions,\n"
            "                   background_overrides=overrides,\n"
            "                   paper_background=paper_background,\n"
            "                   paper_background_color=color if background=='Personalizado'\n"
            "                   else opts.paper_background_color)",
            "    # El editor muestra las capas realmente almacenadas, sean comunes,\n"
            "    # individuales, imágenes o marcas de agua con opacidad parcial.\n"
            "    return replace(opts, layout_template=template, layout_items=layouts,\n"
            "                   photo_edits=photo_edits, captions=captions)",
        ),
    ])

    # 3) Guardar posición/orden/tamaño/giro NO cambia ni el fondo global ni
    # los overrides existentes, tampoco al navegar o cerrar el editor.
    patch('main.py', [
        # La antigua migración de fondos se activaba incluso con solo ABRIR
        # el editor: podía tocar la opción global y abrir una confirmación.
        # El motor ya sabe leer los ajustes legados sin modificar el proyecto.
        (
            "        # Migración del antiguo fondo específico de hoja: al abrir su editor\n"
            "        # pasa a ser un fondo del papel visible en el menú principal.\n"
            "        old_sheet=self.layout_items.get(group[0], {})\n"
            "        old_background=old_sheet.get('background')\n"
            "        if (self.fit.get()=='Ajustar (sin recortar)' and\n"
            "                old_background not in (None,'Según encaje')):\n"
            "            if old_background=='Personalizado':\n"
            "                self.paper_background_color.set(old_sheet.get('background_color','#FFFFFF'))\n"
            "            self.paper_background.set(old_background)\n",
            "        # Diseño libre NO interviene en fondos, incluidos los legados.\n",
        ),
        (
            "            # «Fondo de la hoja» es LOCAL en Diseño libre. Una simple\n"
            "            # navegación/guardado sin cambios nunca debe alterar los fondos\n"
            "            # individuales de otra hoja ni el desplegable global del menú.\n"
            "            if (background_modified and background_choice is not None and\n"
            "                    self.fit.get() == 'Ajustar (sin recortar)'):\n"
            "                from revelo_navigation_seamless import with_page_background\n"
            "                bg, color = background_choice\n"
            "                self.background_overrides = with_page_background(\n"
            "                    self.background_overrides, selected_group, bg, color)\n",
            "            # Fondo global e individuales son propiedad exclusiva de\n"
            "            # 'Fondos por foto · opacidad': no modificarlos aquí.\n",
        ),
    ])

    # 4) Dos tests heredados siguen obligando a modificar un fondo desde
    # Composición libre. NO se eliminan: se actualizan para comprobar con
    # pruebas gráficas la ausencia de controles duplicados y el aislamiento.
    replace_section(
        'tests/test_v175_fix03_shared_views.py',
        'def test_free_background_change_updates_only_active_sheet_not_main(tmp_path):',
        '\ndef test_caption_editor_scale_uses_master_print_scale(tmp_path):',
        '''def test_free_editor_backgrounds_are_read_only_and_render_unchanged(tmp_path):
    from main import ReveloApp
    from PIL import ImageChops
    photo=image(tmp_path)
    root=_tk_window_for_test('1200x880')
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo];app.details[photo]=(600,400)
        app.layout_template.set('Diseño libre')
        app.fit.set('Ajustar (sin recortar)')
        app.paper_background.set('Azul noche')
        individual={'mode':'Color','color':'#F6EBDC','opacity':55}
        app.background_overrides[photo]=dict(individual)
        before,_,_=render_layout_page((photo,),app._options(),preview_max_size=(330,240))
        try:
            app.render_library();app.render_order();app.edit_page_layout();root.update()
            editor=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            from tkinter import ttk
            def walk(w):
                yield w
                for child in w.winfo_children():yield from walk(child)
            children=list(walk(editor))
            assert not any(isinstance(w,tk.Label) and w.cget('text')=='Fondo de la hoja'
                           for w in children)
            assert not any(isinstance(w,ttk.Combobox) and 'Crema' in w.cget('values')
                           for w in children)
            assert not any(isinstance(w,tk.Button) and w.cget('text')=='Elegir color…'
                           for w in children)
            save=next(w for w in children if isinstance(w,tk.Button)
                      and w.cget('text')=='Guardar composición')
            save.invoke();root.update()
            assert app.paper_background.get()=='Azul noche'
            assert app.background_overrides[photo]==individual
            assert 'background' not in app.layout_items.get(photo,{})
            after,_,_=render_layout_page((photo,),app._options(),preview_max_size=(330,240))
            try: assert ImageChops.difference(before,after).getbbox() is None
            finally: after.close()
        finally: before.close()
    finally: root.destroy()
''',
    )

    replace_section(
        'tests/test_v110_fix04_navegacion_organica_y_fondos_aislados.py',
        'def test_new_palette_on_one_sheet_does_not_change_other_sheet_or_global(tmp_path, monkeypatch):',
        '\ndef test_render_page_2_identical_before_and_after_editing_page_1(tmp_path):',
        '''def test_seamless_navigation_retains_per_photo_backgrounds_and_global(tmp_path, monkeypatch):
    """Cambiar de hoja o guardar geometría nunca toca los fondos individuales."""
    from processor import source_dimensions
    from main import ReveloApp
    root=_root()
    dialog=None
    try:
        app=ReveloApp(root)
        paths=_photos(tmp_path,4)
        app.paths=list(paths); app.pages=list(paths)
        app.details={p:source_dimensions(p) for p in paths}
        app.path_labels={p:p.name for p in paths}
        app.paper_background.set('Azul noche')
        app.background_overrides={
            paths[0]:{'mode':'Color','color':'#AABBCC','opacity':35},
            paths[1]:{'mode':'Difuminado','opacity':80},
            paths[2]:{'mode':'Color','color':'#CC4488','opacity':55},
        }
        before={p:dict(v) for p,v in app.background_overrides.items()}
        monkeypatch.setattr(app,'render_library',lambda:None)
        monkeypatch.setattr(app,'render_order',lambda:None)
        app.per_sheet.set('2');app.layout_template.set('Diseño libre')
        app.edit_page_layout();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel)
                    and 'Diseño libre' in w.title())
        ident=str(dialog)
        assert not any(isinstance(w,tk.Label) and w.cget('text')=='Fondo de la hoja'
                       for w in _walk(dialog))
        _button(dialog,'Siguiente').invoke();root.update()
        assert str(dialog)==ident and dialog.winfo_exists()
        assert app.background_overrides==before
        _button(dialog,'Anterior').invoke();root.update()
        assert app.background_overrides==before
        _button(dialog,'Guardar composición').invoke();root.update()
        assert app.background_overrides==before
        assert app.paper_background.get()=='Azul noche'
    finally:
        if dialog is not None and dialog.winfo_exists():dialog.destroy()
        root.destroy()
''',
    )
