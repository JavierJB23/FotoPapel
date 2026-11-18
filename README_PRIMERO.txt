REVELO v1.5.2 — EDICIÓN LIBRE Y ORDENACIÓN POR DOS CLICS
========================================================
Esta es una actualización de Revelo v1.5.1. Guarda el EXE anterior como respaldo.
No modifica el QR, el motor de PDF ni la estructura del proyecto.

CAMBIOS EN ESTA VERSIÓN
----------------------
1. Todos los avisos, errores y preguntas de confirmación del programa pasan
   a usar ventanas oscuras con la estética de Revelo (no las ventanas de
   advertencia estándar de Windows). Los selectores de archivos y colores
   siguen siendo los nativos de Windows por comodidad.
2. ORDENACIÓN SIN ARRASTRAR:
   - Haz clic en la imagen que quieres mover en el panel DERECHO. Su número
     se ilumina en aguamarina y queda seleccionado.
   - Desplázate con la rueda del ratón tanto como necesites.
   - Haz clic en la posición DESTINO dentro del mismo panel derecho.
     Revelo moverá el elemento y retirará la selección.
   - Si pulsas otra vez el mismo elemento, cancelas la selección.
   - El panel izquierdo es independiente y no mueve elementos al hacer clic.
   - La portada seguirá anclada en el primer puesto.
   - Las flechas ↑ ↓ siguen siendo una alternativa.
3. EDITOR DE PORTADAS Y SEPARADORES PERSONALIZADOS:
   - Puedes colocar título y subtítulo en cualquier punto del área segura
     haciendo clic o arrastrando sobre la vista previa, sin nodos ni rejilla.
   - Puedes seleccionar «Fotografía» para mover también la imagen de fondo.
   - Opciones de foto: «Encajar», «Cubrir» y «Libre».
   - En «Libre» puedes modificar de forma independiente el ancho y el alto,
     mantener o desbloquear la proporción y desplazar la foto libremente.
   - El color de fondo elegido aparece detrás de la foto cuando no llena
     toda la hoja (útil para superponer el logo sobre otro color).
   - Los ajustes son reversibles y se guardan en el .revelo y en los PDF
     generados por Revelo. Los diseños predefinidos no cambian.
4. Se conserva el funcionamiento anterior: QR, fotos y PDF, Word, proyectos,
   cuatro modos de encaje, márgenes, hoja múltiple y recuperación de imágenes.

CÓMO ACTUALIZAR EN WINDOWS (SIN PROGRAMAR)
-----------------------------------------
1. Descarga y descomprime el ZIP de actualización v1.5.2.
2. Abre https://github.com/JavierJB23/FotoPapel/upload/main
3. Arrastra los archivos del ZIP, respetando la carpeta tests:
   - main.py                  (reemplazar)
   - special_pages.py         (reemplazar)
   - custom_editor.py         (reemplazar)
   - ordering_rules.py        (reemplazar)
   - revelo_dialogs.py        (NUEVO)
   - README_PRIMERO.txt       (reemplazar)
   - tests/test_v152_improvements.py  (NUEVO, dentro de tests)
4. Pulsa Commit changes. No es necesario cambiar las dependencias ni el
   archivo oculto .github/workflows/windows-exe.yml.
5. En Actions, descarga Revelo-Windows-EXE cuando termine en verde, extrae
   Revelo.exe y utiliza el nuevo.

RECOMENDACIÓN DE PRUEBA
-----------------------
- Carga unas 15 fotos. Haz clic en la foto 3 del panel derecho, baja por
  la lista y pulsa la posición 12. Debe moverse SIN arrastrar.
- Intenta mover una portada: debe permanecer en el puesto 1.
- Crea una portada personalizada con fondo crema y una imagen propia:
  cambia a «Libre», reduce el ancho a 0.6, desbloquea la proporción,
  aumenta el alto, arrastra la imagen y mueve título/subtítulo.
- Guarda el proyecto .revelo, vuelve a abrirlo y exporta PDF; comprueba
  la misma composición en la previsualización y en el PDF.

NOTAS
-----
El modo libre puede deformar una foto si el ancho y el alto tienen escalas
independientes. El color de fondo siempre se conserva debajo de ella.
Un PDF reversible o .revelo puede ocupar más espacio al guardar originales.
No enviamos las fotografías a Internet: la función QR utiliza tu Wi-Fi local.
