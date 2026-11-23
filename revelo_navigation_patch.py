"""Revelo v1.10 · FIX02: navegación entre hojas del editor libre.

Aplicación posterior a los parches estables de QR y fondos. No modifica
proyectos, motor gráfico ni el funcionamiento de las demás ventanas.
"""


def apply_navigation(patch):
    patch('main.py', [
        # Un único punto de entrada: se puede abrir una hoja concreta desde
        # «Siguiente»/«Anterior» sin depender de la selección previa.
        ('    def edit_page_layout(self):\n',
         '    def edit_page_layout(self, *, page_path=None, editor_geometry=None):\n'),
        ('        group=next((g for g in groups if self.order_selected in g),groups[0])\n'
         '        selected_group=list(group)\n',
         '        chosen_path = page_path if page_path is not None else self.order_selected\n'
         '        group=next((g for g in groups if chosen_path in g),groups[0])\n'
         '        group_index=groups.index(group)\n'
         '        selected_group=list(group)\n'),
        # El editor guarda primero, destruye su ventana y solicita la siguiente
        # hoja. El nuevo diálogo se abre en la siguiente vuelta del event loop.
        ('        page_number=next((i for i,g in enumerate(self._groups()) if tuple(g)==tuple(group)),0)\n'
         '        edit_sheet(self.root,selected_group,template,self.layout_items,self._options(),commit_layout,\n'
         '                   page_index=page_number, on_shared_save=save_shared)\n',
         '        page_number=next((i for i,g in enumerate(self._groups()) if tuple(g)==tuple(group)),0)\n'
         '        def navigate_page(direction, geometry):\n'
         '            target_index=group_index+direction\n'
         '            if target_index < 0 or target_index >= len(groups):\n'
         '                return\n'
         '            target_path=groups[target_index][0]\n'
         '            self.order_selected=target_path\n'
         '            def open_next_sheet():\n'
         '                if self.root.winfo_exists() and target_path in self.pages:\n'
         '                    self.edit_page_layout(page_path=target_path, editor_geometry=geometry)\n'
         '            self.root.after_idle(open_next_sheet)\n'
         '        edit_sheet(self.root,selected_group,template,self.layout_items,self._options(),commit_layout,\n'
         '                   page_index=page_number, on_shared_save=save_shared,\n'
         '                   on_navigate=navigate_page if template=="Diseño libre" else None,\n'
         '                   has_previous=group_index>0, has_next=group_index<len(groups)-1,\n'
         '                   editor_geometry=editor_geometry)\n'),
    ])
    patch('layout_editor.py', [
        ('               opts,on_save, *, page_index:int=0, on_shared_save=None):',
         '               opts,on_save, *, page_index:int=0, on_shared_save=None,\n'
         '               on_navigate=None, has_previous=False, has_next=False,\n'
         '               editor_geometry=None):'),
        ("    dialog.geometry('1060x720')",
         "    dialog.geometry(editor_geometry or '1060x720')"),
        ('    def finish(save):\n'
         '        if angle_typing_job[0] is not None:',
         '    def finish(save, navigate=0):\n'
         '        if angle_typing_job[0] is not None:'),
        ('        for photo in thumbs:photo.close()\n'
         '        dialog.destroy()\n\n'
         "    _btn(buttons,'Cancelar',lambda:finish(False)).pack(side='right')",
         '        for photo in thumbs:photo.close()\n'
         '        old_geometry=dialog.geometry() if navigate else None\n'
         '        dialog.destroy()\n'
         '        if navigate and on_navigate is not None:\n'
         '            on_navigate(navigate, old_geometry)\n\n'
         "    _btn(buttons,'Cancelar',lambda:finish(False)).pack(side='right')"),
        ("    _btn(buttons,'Restablecer',reset).pack(side='left')\n"
         "    canvas.bind('<Configure>',lambda _e:draw())",
         "    _btn(buttons,'Restablecer',reset).pack(side='left')\n"
         '    if is_free and on_navigate is not None:\n'
         "        previous_button=_btn(buttons,'Anterior',lambda:finish(True,-1))\n"
         "        previous_button.pack(side='left',padx=(10,0))\n"
         '        if not has_previous:previous_button.configure(state="disabled")\n'
         "        next_button=_btn(buttons,'Siguiente',lambda:finish(True,1))\n"
         "        next_button.pack(side='left',padx=(10,0))\n"
         '        if not has_next:next_button.configure(state="disabled")\n'
         "    canvas.bind('<Configure>',lambda _e:draw())"),
    ])
