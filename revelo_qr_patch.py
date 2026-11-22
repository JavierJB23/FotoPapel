"""Incorporación del QR bidireccional sobre la base estable FIX13.

Correcciones aplicadas antes de las pruebas y de PyInstaller; no se parchea
el servidor existente de importación desde iPhone.
"""

def apply_all(patch):
    patch('main.py', [
        ('self.mobile_btn = self._button(lower_buttons, "Importar desde móvil · QR", self.open_mobile_import, small=True)',
         'self.mobile_btn = self._button(lower_buttons, "Conectar móvil QR", self.open_mobile_connection, small=True)'),
        ('        self._close_preview()\n        self._close_mobile_import()\n        self.mobile_temp.cleanup()',
         '        self._close_preview()\n        self._close_mobile_import()\n        self._close_qr_mode()\n        self._close_mobile_export()\n        self.mobile_temp.cleanup()'),
        ('\ndef main():',
         '\n# Instalación de los métodos QR tras definir ReveloApp.\n'
         'from revelo_qr_bidirectional import install as _install_revelo_qr\n'
         '_install_revelo_qr(ReveloApp)\n\n'
         'def main():'),
    ])
    # Pruebas antiguas: el nombre del botón del menú principal ha cambiado
    # por petición expresa del usuario, pero su funcionalidad de importación
    # permanece accesible desde el diálogo de selección.
    patch('tests/test_v181_editorial_ui.py', [
        ("assert 'Importar desde móvil · QR'==app.mobile_btn.cget('text')",
         "assert 'Conectar móvil QR'==app.mobile_btn.cget('text')"),
    ])
    patch('tests/test_fix06_botones_y_distribucion.py', [
        ("assert app.mobile_btn.cget('text') == 'Importar desde móvil · QR'",
         "assert app.mobile_btn.cget('text') == 'Conectar móvil QR'"),
    ])
