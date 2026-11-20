REVELO v1.6.1 — AJUSTES DEL EDITOR DE PORTADAS Y CORRECCIÓN AUTOMÁTICA
====================================================================

CAMBIOS
- En «Personalizar página», el selector ORIENTACIÓN aparece debajo de TIPO DE PÁGINA
  y está sincronizado con el selector de la ventana principal.
- Cuando FONDO = Color liso, «Elegir foto» y «Editar foto» quedan deshabilitados.
- En modo Fotografía, «Elegir foto» se sitúa antes de PALETA DE COLORES y se
  destaca en aguamarina. «Editar foto» abre el editor fotográfico completo.
- En Windows también puedes arrastrar una imagen desde el Explorador a la vista
  previa; esta función requiere tkinterdnd2, incorporado a la compilación.
- En el editor de fotos aparece «Corrección automática»: mejora de tonos,
  saturación y nitidez moderada, completamente local y reversible. No es el
  algoritmo de Apple Fotos. Puedes activarla o desactivarla con el mismo botón.
- El archivo de imagen original nunca se sustituye. Las instrucciones de
  edición del fondo se conservan en .revelo y en los PDF reversibles.

PARA ACTUALIZAR GITHUB
1. Conserva una copia de tu Revelo v1.6 o checkpoint estable anterior.
2. Sube el contenido de este ZIP, manteniendo la carpeta tests y la ruta
   .github/workflows/windows-exe.yml si viene incluida.
3. Confirma el commit, entra en Actions y descarga Revelo-Windows-EXE.
4. Extrae Revelo.exe y pruébalo. No hay que instalar Python.

PRUEBAS RECOMENDADAS
- Abrir «+ Página > Personalizar», cambiar orientación y ver la hoja adaptarse.
- Probar Color liso: «Elegir foto» debe estar desactivado.
- Marcar Fotografía y elegir una foto o arrastrarla desde el Explorador.
- «Editar foto» > «Corrección automática» > «Guardar edición».
- Guardar .revelo y volver a abrirlo: la fotografía debe conservar sus ajustes.
