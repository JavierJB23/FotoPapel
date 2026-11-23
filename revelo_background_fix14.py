"""FIX14 · Menú de fondos coherente: general, imagen y excepciones.

Se ejecuta después de BLOCK02 y antes de pytest/PyInstaller. Todos los
anclajes son únicos y fallan explícitamente ante cambios de la base.
"""


def apply_v110_fix14(patch):
    patch('main.py', [
        # Inicializar el estado del desplegable antes de registrar sus traces.
        ('        self.background_window: tk.Toplevel | None = None\n',
         '        self.background_window: tk.Toplevel | None = None\n'
         '        self._background_choice_previous = "Blanco"\n'
         '        self._background_choice_guard = False\n'
         '        self._background_pending_custom_from = None\n'),
        # Personalizado abre editor; Imagen para todas permite añadir una
        # foto general directamente, sin modificar el esquema ExportOptions.
        ('["Blanco", "Crema", "Aguamarina", "Azul noche", "Difuminado", "Personalizado"], 140),',
         '["Blanco", "Crema", "Aguamarina", "Azul noche", "Difuminado", "Personalizado", "Imagen para todas"], 140),'),
        # NO borrar fondos al entrar en el combo sin aceptar el diálogo.
        ('        self.paper_background.trace_add("write", self._sync_free_background_from_main)\n',
         '        self.paper_background.trace_add("write", self._background_choice_changed)\n'),
        ('    def _update_paper_background_controls(self):\n',
         '    def _background_choice_changed(self, *_):\n'
         '        from revelo_background_control import on_choice\n'
         '        on_choice(self)\n\n'
         '    def _update_paper_background_controls(self):\n'),
        # El botón «…» del color personalizado también debe avisar al
        # sustituir capas individuales. Se conserva el selector nativo.
        ("    def choose_paper_background_color(self):\n"
         "        chosen = colorchooser.askcolor(color=self.paper_background_color.get(),\n"
         "                                       parent=self.root, title='Revelo · Color del papel')[1]\n"
         "        if chosen:\n"
         "            self.paper_background_color.set(chosen.upper())\n"
         "            self.paper_background.set('Personalizado')\n",
         "    def choose_paper_background_color(self):\n"
         "        from revelo_background_control import choose_custom_color\n"
         "        choose_custom_color(self)\n"),
        # Después de recuperar un proyecto, usar su selector como punto de
        # partida real para cualquier modificación posterior.
        ('        self._restoring_project = False\n        self.project_path = source\n',
         '        self._restoring_project = False\n'
         '        self._background_choice_previous = self.paper_background.get()\n'
         '        self._background_pending_custom_from = None\n'
         '        self.project_path = source\n'),
    ])
