REVELO v1.5.2 FIX03 — EDITOR LIBRE Y FONDO DIFUMINADO
=====================================================

Actualización sobre v1.5.2 FIX02 (confirmado en Windows).

QUÉ CAMBIA
1. EL EDITOR YA NO BLOQUEA LA VENTANA PRINCIPAL
   - Puedes moverlo a un lado, elegir otro tamaño de papel u orientación en
     Revelo y regresar al editor SIN cerrarlo ni perder el trabajo sin guardar.
   - También se actualizan los márgenes de encuadernación.
   - Los diseños antiguos siguen abriéndose. El cambio se guarda cuando pulsas
     «Guardar página personalizada»; «Cancelar» no cambia el documento.

2. NUEVO RELLENO EN PORTADAS/SEPARADORES CON FOTO
   - En «RELLENO DEL ESPACIO LIBRE» puedes elegir «Color liso» o «Difuminado».
   - Difuminado genera un fondo usando los colores de la fotografía y suaviza
     gradualmente los bordes entre la foto nítida y el fondo.
   - El efecto funciona con foto Encajar, Cubrir o Libre, sin conexión a Internet.
   - Los proyectos .revelo y PDF reversibles guardan esa elección. En diseños
     antiguos se mantiene «Color liso» para no cambiar su apariencia.

3. MÁS SUAVIDAD AL MOVER FOTO Y TEXTOS
   - Objetivo de repintado cada 16 ms, evitando la espera antigua de 130 ms.
   - Las vistas usan una miniatura ligera en memoria; mover el texto NO vuelve
     a abrir ni recalcular la fotografía. La exportación sigue utilizando
     siempre la imagen original de calidad máxima.
   - La velocidad real depende de Windows y del tamaño de las fotografías.

ACTUALIZAR EN GITHUB (NO HAY QUE INSTALAR NADA EN EL PC)
1. Descarga y descomprime el ZIP de actualización FIX03.
2. Abre https://github.com/JavierJB23/FotoPapel/upload/main
3. Sube main.py, custom_editor.py, special_pages.py y README_PRIMERO.txt
   sustituyendo sus versiones anteriores.
4. Sube además tests/test_editor_live_blur.py conservando la carpeta tests.
5. Pulsa Commit changes. En la pestaña Actions descarga el nuevo Revelo.exe
   desde el artifact Revelo-Windows-EXE cuando la ejecución salga en verde.

PRUEBA RECOMENDADA
1. Abre una portada personalizada. Mueve la ventana a un lado.
2. Sin cerrarla, cambia A4 Horizontal a A5 Vertical en Revelo.
3. Comprueba que la hoja del editor cambia al momento y que puedes seguir
   editando la misma portada. No se debe perder el título ni el fondo.
4. Elige una foto y relleno Difuminado; cambia su posición y arrastra el título.
5. Guarda, cierra y reabre el proyecto .revelo. Comprueba el fondo en PDF.

------------------------------------------------------------
DOCUMENTACIÓN DE LA VERSIÓN ANTERIOR
------------------------------------------------------------

REVELO v1.5.2 FIX02 — ORIENTACIÓN DE PORTADAS Y SEPARADORES
============================================================

Corrección sobre v1.5.2 FIX01.

QUÉ CAMBIA
- Una orientación Horizontal o Vertical seleccionada en Revelo tiene
  prioridad, incluso al editar una portada o separador creado anteriormente.
- Con Orientación Automática, se conserva la orientación de la página previa.
- La vista previa del editor utiliza la proporción real del tamaño de papel
  activo (A4, A5, 10x15, etc.) en lugar de una proporción fija.
- Al guardar la página, la miniatura se actualiza a la orientación elegida.
- No se alteran el QR, PDF, Word, fondos, proyectos ni demás funciones.

INSTALACIÓN EN EL REPOSITORIO ACTUAL
1. Descarga y descomprime el ZIP de actualización.
2. En GitHub: JavierJB23/FotoPapel > Add file > Upload files.
3. Sube main.py y custom_editor.py y conserva tests/test_orientation_special_editor.py
   dentro de la carpeta tests.
4. Haz Commit changes. En Actions, descarga el nuevo Revelo-Windows-EXE.

PRUEBA EN WINDOWS
1. Selecciona A4 y Horizontal.
2. Edita una portada creada antes en vertical.
3. La hoja de Personalizar página debe verse horizontal.
4. Guarda y comprueba la miniatura y la vista previa de impresión.
5. Cambia a Vertical y comprueba el comportamiento inverso.

Se conservan las instrucciones de la versión base a continuación.

REVELO v1.5.2 FIX01 — VENTANA DE PERSONALIZACIÓN MÁS COMPACTA
===============================================================
Corrección visual sobre Revelo v1.5.2, sin cambios funcionales.
- Editor más pequeño al abrirse y ajustado a la resolución de pantalla.
- «Guardar página personalizada» y «Cancelar» siguen visibles en el pie.
- Las propiedades conservan la barra de desplazamiento vertical.
- Se mantiene la vista previa y su opción de ampliar la ventana.

INSTALACIÓN DEL FIX
-------------------
Desde v1.5.2, sube solo el archivo custom_editor.py actualizado a
la raíz de tu repositorio en GitHub, sustituyendo el anterior.
Pulsa Commit changes y descarga el nuevo Revelo.exe desde Actions.
No hay que modificar .github, las dependencias ni el resto del programa.

INFORMACIÓN DE LA VERSIÓN BASE
------------------------------
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
