REVELO v1.6 — EDITOR FOTOGRÁFICO (CANDIDATA A STABLE)
=======================================================

Esta versión parte exactamente del checkpoint Revelo v1.5.2 FIX05 STABLE.
NO borres el ejecutable anterior hasta comprobar v1.6 en Windows.

NOVEDADES
1. En "FOTOS Y PDF CARGADOS" hay un botón "Editar foto" en cada imagen.
   Las portadas y separadores conservan su editor específico.
2. Recorte libre arrastrando un rectángulo y ajustando sus cuatro esquinas.
   Recortes guiados: original, 1:1, 4:3, 3:4, 16:9, 9:16, A4/A5 y 10×15.
3. Girar a izquierda/derecha, voltear y enderezar entre -15 y +15 grados.
4. Controles de brillo, contraste, saturación y nitidez.
5. "Quitar bordes blancos" intenta detectar un borde claro exterior.
   Comprueba la selección antes de guardar: no todos los blancos son un marco.
6. "Ver resultado" muestra el recorte final, y mantener pulsado "Original"
   permite comparar con la fuente.
7. Edición reversible: se guardan los parámetros, no una foto sustituida.
   "Restablecer original" revierte todos los cambios.
8. El proyecto .revelo y los PDF reversibles conservan los originales
   y sus parámetros de edición. Las páginas especiales siguen funcionando.

ACTUALIZAR EL PROGRAMA EN GITHUB (SIN INSTALAR NADA EN TU PC)
1. Descarga y descomprime el ZIP de ACTUALIZACIÓN v1.6.
2. Ve a https://github.com/JavierJB23/FotoPapel/upload/main
3. Sube todos los archivos del ZIP. En la raíz se sustituyen:
   main.py, processor.py, project_io.py, pdf_sources.py y README_PRIMERO.txt.
   Se añaden photo_edits.py y photo_editor_ui.py en la misma raíz.
   En tests/ se añade tests/test_photo_editor_v16.py.
4. Pulsa "Commit changes".
5. Abre https://github.com/JavierJB23/FotoPapel/actions
6. Abre la compilación reciente; cuando aparezca verde, baja hasta "Artifacts"
   y descarga "Revelo-Windows-EXE". Extrae el archivo y abre Revelo.exe.
   No cambies el workflow ni instales Python en tu equipo.

PRUEBA RECOMENDADA
- Importa una foto por QR o desde tu PC. Abre "Editar foto".
- Selecciona 10×15 horizontal y arrastra el recorte. Modifica saturación.
- Comprueba "Original" y "Ver resultado". Guarda la edición.
- Previsualiza y exporta PDF. Guarda un .revelo, ciérralo y vuelve a abrirlo.
- Asegúrate de que la miniatura y el documento conservan el recorte.

LIMITACIONES
- La vista del editor usa una copia reducida para ir fluida; el documento
  final se crea a partir del original a su resolución real.
- Si conviertes una fotografía en PDF o Word corriente fuera de Revelo,
  el archivo externo puede perder el historial editable. Los PDF reversibles
  creados por Revelo sí conservan los datos, mientras se mantenga el adjunto.
- En PDF antiguos aplanados no se pueden recuperar datos originales perdidos.

--------------------------------------------------------------------
DOCUMENTACIÓN DEL CHECKPOINT ANTERIOR
--------------------------------------------------------------------

REVELO v1.5.2 FIX05 — SCROLL Y VENTANA DEL EDITOR
====================================================

Corrección incremental sobre Revelo v1.5.2 FIX04. No modifica la maquetación,
el QR, las páginas personalizadas ni las exportaciones.

CAMBIOS
1. El panel de opciones del editor personalizado responde a la rueda del ratón
   aunque el cursor esté sobre un desplegable, barra, campo o botón.
   Los desplegables y tamaños NO se modifican con la rueda. Para cambiar sus
   valores se usa clic, teclado o el control que corresponda.
2. El editor se abre casi a toda la altura útil del monitor, dejando libre la
   barra de tareas y los botones de Guardar/Cancelar siempre visibles.
3. Se usa la ventana normal de Windows en lugar de una ventana transitoria,
   permitiendo el botón Minimizar junto a los controles habituales de la barra
   de título. Minimizar NO descarta el contenido sin guardar.
4. Sigue siendo un editor NO modal: se pueden modificar los ajustes de papel
   en Revelo sin cerrar el editor.

ACTUALIZACIÓN EN GITHUB
1. Descomprime el ZIP de FIX05.
2. Ve a https://github.com/JavierJB23/FotoPapel/upload/main
3. Sube custom_editor.py y README_PRIMERO.txt a la raíz, sustituyendo los
   anteriores, y los dos archivos de test dentro de tests/.
4. Pulsa Commit changes. Abre Actions y descarga Revelo-Windows-EXE cuando
   el trabajo termine en verde. No cambies el archivo de compilación.

PRUEBA RECOMENDADA
- Abre Personalizar. Desplázate con la rueda sobre cualquier desplegable:
  el valor debe quedar intacto mientras baja/sube el panel izquierdo.
- Confirma que abre alto, deja ver Guardar y Cancelar y tiene botón minimizar.
- Minimiza, vuelve al editor y comprueba que no perdió los cambios.

--------------------------------------------------------------------
DOCUMENTACIÓN ANTERIOR
--------------------------------------------------------------------

REVELO v1.5.2 FIX04 — TIPOGRAFÍAS Y PALETAS EN PERSONALIZAR
=========================================================

Actualización incremental sobre v1.5.2 FIX03. No modifica el QR, el gestor de
PDF, la ordenación ni el sistema de exportación. Conserva el editor no modal,
las imágenes de fondo, el difuminado y el arrastre fluido.

NOVEDADES
1. DIEZ TIPOGRAFÍAS PARA PORTADAS Y SEPARADORES PERSONALIZADOS
   - Georgia, Arial, Calibri, Segoe UI, Times New Roman, Verdana,
     Trebuchet MS, Courier New, Comic Sans MS e Impact.
   - Título y subtítulo se configuran por separado.
   - El tamaño puede ajustarse mediante la barra o escribiendo un número
     exacto. Son porcentajes relativos al área segura de texto.
   - El editor, las miniaturas, Word y PDF usan el mismo motor de texto.
   - No se distribuyen fuentes: Revelo usa las instaladas en Windows.
     Si falta alguna fuente, usa una alternativa para no bloquear la edición.

2. COLORES DE LOS DISEÑOS CLÁSICOS EN EL MODO PERSONALIZAR
   - Blanco, Crema, Aguamarina y Azul noche aparecen en un desplegable.
   - Al escoger una paleta se asignan fondo, título y subtítulo con colores
     legibles. Puedes cambiar después los colores de texto individualmente.
   - «Otro color…» abre el selector de color de Windows.
   - Funciona con «Color liso», con fotografía de fondo y con el relleno
     difuminado. No limita el movimiento de títulos ni la escala de fotos.

COMPATIBILIDAD
 - Los proyectos anteriores siguen abriéndose. Sus textos personalizados
   conservan Georgia si no tenían una fuente elegida explícitamente.
 - Los proyectos .revelo y PDF reversibles nuevos guardan fuente, color y tamaño.
 - Las plantillas prediseñadas no cambian: solo se amplía «Personalizar».

INSTALAR EL FIX04
1. Descarga y descomprime el ZIP de actualización.
2. Abre https://github.com/JavierJB23/FotoPapel/upload/main
3. Sube custom_editor.py, special_pages.py y README_PRIMERO.txt directamente
   a la raíz, sustituyendo los existentes.
4. Sube tests/test_editor_fonts_palettes.py dentro de la carpeta tests.
5. Pulsa Commit changes. Cuando la nueva ejecución de Actions esté verde,
   descarga Revelo-Windows-EXE y extrae Revelo.exe.
6. Conserva el ejecutable anterior hasta verificar las dos mejoras en Windows.

PRUEBA SUGERIDA
 - Crea una portada Personalizar y selecciona Azul noche.
 - Cambia el título a Impact, el subtítulo a Courier New y los tamaños a
   19 y 8. Mueve los textos y comprueba la previsualización.
 - Guarda la portada, exporta a PDF y guárdala en un proyecto .revelo.
 - Reabre el proyecto y comprueba que mantiene tipografías y colores.

--------------------------------------------------------------------
DOCUMENTACIÓN DE LAS VERSIONES ANTERIORES
--------------------------------------------------------------------

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
