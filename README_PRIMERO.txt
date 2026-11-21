REVELO v1.7.5 FIX03 — SINCRONIZACIÓN DE FONDO Y ESCALA
======================================================================

Esta actualización se instala SOBRE la v1.7.5 FIX02. La versión 1.6.2
STABLE/FROZEN permanece intacta. La v1.7.5 FIX03 es candidata a STABLE.

CAMBIOS
- El tamaño de foto (por ejemplo 0,70) se representa en las miniaturas
  de la biblioteca y del orden, además de la previsualización y exportación.
- Un único valor de escala de impresión conecta «Editar foto»,
  «Texto / pie de foto» y «Diseño libre» (guardar aplica el valor).
- En diseño libre, las esquinas cambian esa escala proporcional;
  las asas laterales conservan la posibilidad de estirar ancho y alto
  independientes, como una transformación adicional del diseño.
- El fondo elegido en la cabecera coincide con el de «Diseño libre».
  Cambiarlo desde el editor y guardar actualiza la cabecera.
- «Fondo del papel» ofrece Blanco, Crema, Aguamarina, Azul noche,
  Difuminado y Personalizado con «Ajustar (sin recortar)».
- Con otros modos de encaje, el fondo queda visiblemente deshabilitado,
  con una explicación en la línea inferior; no se aplica a escondidas.
- Los fondos antiguos específicos de diseños libres se siguen pudiendo
  abrir; al editarlos se convierten al nuevo fondo compartido.

INSTALACIÓN EN GITHUB
1. Descomprime Revelo_v1_7_5_FIX03_ACTUALIZACION.zip.
2. Sube main.py, layout_editor.py, caption_editor.py, processor.py,
   thumbnail_preview.py, README_PRIMERO.txt y el test dentro de tests/.
3. Confirma los cambios (Commit changes) y entra en Actions.
4. Descarga Revelo-Windows-CARPETA después de la compilación en verde.
5. Extrae toda la carpeta: Revelo.exe necesita los demás componentes.
No modificar el workflow ni las dependencias.

PRUEBAS DE LA ACTUALIZACIÓN
172 correctas y 2 omitidas en el entorno Linux con pantalla virtual.
Pendiente de validar en el ejecutable de Windows de GitHub.

NOTAS DE VERSIONES ANTERIORES
======================================================================

REVELO v1.7.5 FIX01 — CABECERA DE AJUSTES COMPACTA
======================================================================

CORRECCIÓN VISUAL (sin cambios en exportación ni cálculos):
- Siete selectores en una sola fila: tamaño, orientación, encaje, calidad,
  exportación, encuadernación y fondo del papel.
- Anchuras adaptadas al texto más largo; se aprovecha el espacio extra
  de las ventanas anchas y también cabe en el mínimo de 1100 píxeles.
- Fondo del papel mantiene sus paletas y el color personalizado mediante
  el botón «…» que aparece al seleccionar «Personalizado».
- La información de tamaño/PPP queda debajo, sin controles nuevos.
- Se conserva la compilación de GitHub en carpeta; no hay dependencias nuevas.

NOTAS DE LA BASE v1.7.5
======================================================================

REVELO v1.7.5 — FONDO DEL PAPEL Y VISTA SINCRONIZADA
======================================================================

ESTADO: CANDIDATA A STABLE. La v1.6.2 STABLE/FROZEN permanece
congelada. La compilación sigue siendo EN CARPETA.

CAMBIOS

1. FONDO EDITABLE EN «AJUSTAR (SIN RECORTAR)»
   En la fila de información del menú principal aparece «FONDO DEL PAPEL».
   Mantiene el encaje sin recortar y permite elegir Blanco (predeterminado),
   Crema, Aguamarina, Azul noche o Personalizado → «Color…».
   No cambia la fotografía original ni su proporción, solo el fondo de la
   hoja y de los huecos. El color se conserva en el proyecto .revelo y se
   aplica por igual a la vista previa, PDF, Word e imágenes.
   El selector se deshabilita cuando se utiliza otro modo de encaje;
   el fondo propio de «Diseño libre» tiene prioridad sobre el general.

2. MINIATURAS EN TIEMPO REAL DE COMPOSICIONES LIBRES
   Al guardar una composición libre, «Orden del contenido» muestra la hoja
   compuesta con las fotografías, las posiciones y el fondo escogido.
   La biblioteca izquierda conserva las miniaturas individuales originales,
   para que sigas identificando qué foto estás ordenando.
   La miniatura se actualiza al cambiar orientación, papel, encaje o fondo.

3. ENTRADA NUMÉRICA DE GIRO
   En «Diseño libre», escribe el ángulo (por ejemplo 31 o -22,5) al lado
   del deslizador. Se aplica automáticamente al terminar de escribir o al
   pulsar Intro, sin necesidad de mover la barra. El giro queda guardado
   en la composición; acepta decimales y mantiene la zona neutra de 0°.

COMPATIBILIDAD Y CUIDADOS

- Los proyectos antiguos sin fondo configurable mantienen Blanco.
- Las portadas y separadores siguen utilizando sus fondos propios.
- Un PDF externo que se conserva como página cerrada no se interpreta
  como una fotografía libremente editable si no contiene originales.
- El programa no reescribe ni modifica archivos de origen.

ACTUALIZAR DESDE v1.7.4 (GITHUB)

1. Descomprime Revelo_v1_7_5_ACTUALIZACION.zip.
2. Sube los seis archivos actualizados a la raíz del repositorio; el archivo
   test_v175_paper_background_and_thumbnail.py va dentro de tests/.
3. Haz «Commit changes» en GitHub.
4. En Actions descarga «Revelo-Windows-CARPETA» cuando termine en verde.
5. Extrae la carpeta completa y abre Revelo.exe con sus dependencias.
   No debes modificar el workflow de GitHub ni instalar Python.

PRUEBAS RECOMENDADAS EN TU WINDOWS

1. Abre Diseño libre con dos fotos, elige fondo Azul noche, guarda y mira
   las miniaturas de la derecha sin abrir Previsualización.
2. Escribe -22,5 en Giro y comprueba que la fotografía rota al confirmar.
3. Elige «Ajustar (sin recortar)», selecciona Crema y exporta PDF y Word.
4. Guarda y reabre un proyecto .revelo: el fondo debe seguir en Crema.

--------------------------------------------------------------------

REVELO v1.7.4 — RECORTE CONFIRMADO Y CONTROLES DE EDICIÓN COHERENTES
======================================================================

ESTADO: CANDIDATA A STABLE. Conserva Revelo v1.6.2 STABLE/FROZEN
como respaldo. La compilación sigue siendo EN CARPETA.

MEJORAS

1. RECORTE CONFIRMADO = NUEVA BASE DE EDICIÓN
   Cuando confirmas «Recortar», Revelo incorpora el corte a un historial
   reversible. Los giros 90°, volteos y enderezados posteriores actúan SOLO
   sobre lo que ha quedado dentro, sin volver a sacar zonas descartadas.
   «Restablecer original» recupera el archivo completo de origen.
   Los proyectos anteriores siguen abriéndose y migran al historial cuando
   guardas una edición nueva. Se conserva el historial en .revelo y PDF.

2. REABRIR UNA FOTO EDITADA
   «Editar fotografía» muestra de entrada el resultado guardado; no vuelve
   a abrir sobre él la antigua selección de recorte. El botón «Modificar
   recorte» permite realizar un nuevo corte sobre la imagen actual.

3. CONTROLES Y RUEDA
   La rueda desplaza los paneles con opciones y no modifica accidentalmente
   los deslizadores. Los ajustes del editor de foto ofrecen valor numérico
   editable; el control tiene una zona magnética en su valor de origen:
   0° para enderezado y 1,00 para brillo/escala/contraste, etcétera.
   Un doble clic en la barra devuelve el control a su valor neutro.
   El tamaño en hoja se puede comprobar en directo con «Ver en hoja».

4. COMPOSICIÓN LIBRE CON OCHO ASAS VISIBLES
   Selecciona una foto y tira de cualquiera de sus cuatro esquinas para
   escalar proporcionalmente, o de los cuatro laterales para cambiar ancho
   y alto por separado. Ya no depende de un único rincón oculto; los
   cambios aparecen en la vista y en el PDF/Word. En diseños irregulares
   también hay un asa para modificar visualmente el reparto de espacio.
   «Doble clic» sigue enviando una fotografía delante de las demás.

5. PERSONALIZACIÓN CONSISTENTE
   Se mantienen los controles directos por arrastre en portada, pie de foto
   y tamaño de hoja, además de los valores numéricos disponibles.
   Los originales siempre permanecen intactos.

INSTALACIÓN EN GITHUB

1. Descomprime Revelo_v1_7_4_ACTUALIZACION.zip.
2. Sube sus archivos a tu repositorio, conservando tests/ y sus rutas.
3. Pulsa «Commit changes»; Actions generará Revelo-Windows-CARPETA.
4. Descarga, extrae todo y abre Revelo.exe sin separar su carpeta.
5. No cambies el workflow ni instales Python en tu PC.

PRUEBA RECOMENDADA

1. Recorta una porción pequeña y confirma el corte.
2. Endereza a +15° y -15°: la imagen de origen exterior no reaparece.
3. Guarda, sal, vuelve a editar: abre sobre el resultado, sin selección vieja.
4. Prueba rueda sobre un slider: se desplaza el panel, no cambia el valor.
5. En Diseño libre estira una foto de lado y de esquina; exporta un PDF.

--------------------------------------------------------------------

REVELO v1.7.3 — ARRASTRE, ESCALA Y COMPOSICIÓN FIELES A LA IMPRESIÓN
======================================================================

ESTADO: CANDIDATA A STABLE. No sustituir todavía el respaldo
Revelo v1.6.2 STABLE/FROZEN. El .exe se genera EN CARPETA (GitHub Actions).

CORRECCIONES

1. RECORTE Y GIROS
   Al girar o reflejar una fotografía que ya has recortado, el área de
   recorte se transforma con ella. El enderezado conserva una aproximación
   de la zona seleccionada sin restablecer automáticamente la imagen entera.
   «Modificar recorte» sigue permitiendo reajustarla.

2. TAMAÑO DE FOTO VISIBLE
   En «Editar fotografía» pulsa «Ver en hoja» para comprobar la escala real
   respecto al papel; puedes cambiarla arrastrando el asa crema de la foto.
   Funciona también con fotos de fondo de portadas personalizadas.
   0,40 significa 40 % del tamaño de maquetación normal (no del archivo).

3. TEXTO / PIE DE FOTO EN DIRECTO
   Ventana con ajustes a la izquierda y la hoja completa a la derecha.
   El texto, la tipografía, el color y el tamaño se actualizan en la vista.
   También se puede estirar/reducir la foto por el asa aguamarina, sin
   tener que fiarse exclusivamente del deslizador. Incluso un tamaño sin
   texto se conserva en el proyecto .revelo y en PDF reversible.

4. DISEÑO LIBRE MÁS INTUITIVO
   El marco rodea la foto VISIBLE, no un rectángulo de destino vacío.
   Arrastra su esquina para escalar, manteniendo proporciones. Un doble clic
   coloca la fotografía seleccionada delante, guardando ese orden de capas.
   Se incorpora «Fondo de la hoja»: Según encaje, Blanco, Crema,
   Aguamarina, Azul noche, Difuminado o Personalizado (cualquier color).
   La vista del editor y el PDF/Word siguen los mismos parámetros.

5. PORTADAS PERSONALIZADAS
   El control de escala del editor fotográfico modifica también el tamaño
   de la imagen en el fondo de una portada. La fotografía se puede estirar
   mediante un asa en el editor de portada, además de usar las barras.

CONSERVACIÓN
   Sin cambios destructivos sobre las fotografías originales; el orden de
   capas y el fondo de diseño libre se guardan en .revelo y PDF reversible.
   Los proyectos antiguos siguen abriéndose con valores predeterminados.

INSTALACIÓN

1. Descomprime «Revelo_v1_7_3_ACTUALIZACION.zip».
2. Sube a GitHub TODOS los archivos del ZIP conservando la carpeta tests.
3. Haz Commit changes.
4. En Actions descarga «Revelo-Windows-CARPETA» al terminar la compilación.
5. Descomprime y ejecuta Revelo.exe conservando sus archivos auxiliares.
   NO modifiques .github/workflows/windows-exe.yml, ni necesitas Python.

PRUEBA EN WINDOWS
   - Recorta una foto, gírala 90° y observa el mismo encuadre.
   - En una portada cambia escala 1,00 a 0,40 en «Ver en hoja».
   - Abre un pie de foto y observa los textos y tamaño sobre el folio.
   - En Diseño libre superpón dos fotos; doble clic cambia cuál va delante.
   - Prueba fondo Crema y Difuminado. Exporta y revisa el PDF.

--------------------------------------------------------------------

REVELO v1.7.2 — DISEÑO LIBRE, TAMAÑOS Y NUMERACIÓN
====================================================

ESTADO: CANDIDATA A STABLE. Conserva Revelo v1.6.2 STABLE/FROZEN intacto.

NOVEDADES DE ESTA ACTUALIZACIÓN

1. TAMAÑO DE FOTO Y PIE DE TEXTO
   En «Editar foto», bajo «TAMAÑO DE FOTO EN LA HOJA», puedes elegir una escala
   de impresión de 0,25 a 1,50. La edición del original sigue siendo reversible.
   En «Texto / pie de foto» aparece «Tamaño de la fotografía en la hoja»,
   con control entre 25 % y 100 %. Reduce la foto manteniendo su proporción
   y sin tocar el archivo original; conserva el texto, fuente y color.

2. TAMAÑO DE FOTOS EN LAS PLANTILLAS DE 3
   La caja «Diseño» es más compacta. Con cualquier diseño irregular
   de tres fotos se habilita el botón «Tamaño de fotos» en la misma fila.
   Se abre la hoja: selecciona una imagen y cambia el reparto de espacio
   mediante la barra o rueda. La estructura (grande arriba, izquierda,
   o abajo) se mantiene. El ajuste solo afecta a esa hoja.

3. DISEÑO LIBRE
   Selecciona «Diseño libre» en el desplegable, con 1, 2, 3, 4, 6 o 9
   fotos por hoja, y pulsa «Editar diseño libre». En el editor:
     - Clic sobre una fotografía para seleccionarla.
     - Arrastra para moverla; usa el cuadrado aguamarina para redimensionar.
     - Rueda para cambiar su tamaño; Mayúsculas + rueda para girarla.
     - Usa el control «Giro» si quieres un ángulo concreto.
     - Puedes colocar y superponer imágenes libremente.
   Las transformaciones son no destructivas y se conservan al exportar.

4. NUMERACIÓN SIN RECUADROS
   En «Numeración…» hay dos cajas compactas en la misma línea: Posición
   y Formato. Opciones: 1, -1-, [1], (1), · 1 ·. No se dibuja ya ninguna
   pastilla beige alrededor del número. El color se adapta a fondos
   claros u oscuros.

5. CONSERVACIÓN DE LOS DISEÑOS
   Se guardan giros, tamaños y posiciones dentro de los proyectos .revelo
   y en los PDF reversibles. Las composiciones se pueden modificar luego.
   Al reimportar un PDF reversible completo, Revelo recupera también
   su modo de composición cuando se abre en una biblioteca vacía.

INSTALACIÓN

1. Descarga y descomprime Revelo_v1_7_2_ACTUALIZACION.zip.
2. En github.com/JavierJB23/FotoPapel pulsa Add file > Upload files.
3. Sube los archivos, respetando la carpeta tests. El nuevo archivo
   layout_editor.py va en la raíz, junto a main.py.
4. Pulsa Commit changes y entra en Actions.
5. Descarga Revelo-Windows-CARPETA cuando la compilación esté en verde.
6. Descomprime y conserva juntos Revelo.exe y todos sus componentes.
   No hace falta cambiar el workflow ni instalar Python.

PRUEBA SUGERIDA

- Carga 4 fotos. Selecciona «Diseño libre» y 4 fotos por hoja.
- Pulsa «Editar diseño libre»; mueve, agranda y gira una fotografía.
- En «Texto / pie de foto» cambia el tamaño de otra fotografía.
- Activa numeración [1] y comprueba que no se ve ningún recuadro.
- Exporta PDF y Word. Guarda y vuelve a abrir un proyecto .revelo.

--------------------------------------------------------------------

REVELO v1.7.1 — REFINADO DE PIES DE FOTO Y LIBRO
================================

ESTADO: CANDIDATA A STABLE. Mantener Revelo v1.6.2 STABLE/FROZEN intacto.

NUEVAS FUNCIONES

1. ARRASTRAR ARCHIVOS DESDE WINDOWS
   Arrastra uno o varios JPG, PNG, HEIC, HEIF, TIFF, WEBP, BMP o PDF
   directamente sobre la ventana o el panel de carga. También puedes
   arrastrar una carpeta: importa las fotografías y PDF de ese nivel.
   La importación sigue el mismo proceso local que el botón «Añadir».
   El arrastre desde el Explorador requiere la versión de Windows compilada
   con TkinterDnD2 (ya incluida en los requisitos y en GitHub Actions).

2. NUMERACIÓN AUTOMÁTICA
   El botón «Numeración...» permite activar/desactivar números, elegir
   posición (exterior, centro, izquierda o derecha), número inicial y
   omisión de portadas y separadores. Los números se generan en la hoja,
   no en los archivos originales. Respeta la posición física de la hoja.

3. VISTA DE LIBRO ABIERTO
   En «Previsualización» pulsa «Libro abierto». La primera página aparece
   sola a la derecha; después se muestran pares izquierda/derecha.
   La portada queda AISLADA a la derecha, con el lado izquierdo libre,
   sin dibujar una falsa página. Los pares siguientes se presentan con
   cantos de papel, sombra y lomo central para dar sensación de libro.
   «Página única» recupera la vista anterior. No modifica el PDF ni imprime
   hojas dobles: es una simulación para revisar un álbum encuadernado.

4. COMPOSICIONES ASIMÉTRICAS
   En «FOTOS POR HOJA», selecciona 3. En «DISEÑO» escoge:
      - Cuadrícula (igualitaria)
      - Grande arriba + 2 abajo
      - Grande izquierda + 2 derecha
      - 2 arriba + grande abajo
   Al seleccionar un diseño asimétrico se seleccionan automáticamente
   tres fotografías por hoja. Los diseños de 1, 2, 4, 6 y 9 fotos siguen
   funcionando exactamente como antes.

5. TEXTOS Y PIES DE FOTO — REFINADOS EN v1.7.1
   En «Texto / pie de foto», puedes añadir título y descripción/lugar/fecha,
   elegir «Debajo», «Sobre foto» o «Personalizado» y seleccionar entre
   las diez tipografías de Revelo, color, tamaño en puntos y alineación.
   El texto ya NO genera recuadros opacos ni bandas beige/negras.
   Al escoger «Personalizado» se abre un editor visual: selecciona título
   o descripción y arrastra el texto libremente sobre la imagen. Aparecen
   guías aguamarina cuando alcanzas el centro. «Aplicar posición» guarda
   las coordenadas en el formulario y «Guardar texto» confirma todo.
   Los textos se pintan en la composición PDF/Word, nunca en el original.
   También funcionan en composiciones asimétricas de varias fotografías;
   Revelo evita que el texto se dibuje sobre celdas vecinas.
   Para quitar el pie, vacía los dos campos y guarda.

COMPATIBILIDAD

- Los ajustes de numeración, diseño y pies de foto se guardan en .revelo.
- Las fotos originales siguen incluidas en proyectos y PDF reversibles.
- Al reimportar un PDF reversible de v1.7 se recuperan también sus pies
  de foto. Los PDF antiguos continúan siendo compatibles.
- Portadas y separadores siguen ocupando su hoja independiente.
- QR, edición fotográfica, Word, PDF y márgenes siguen disponibles.
- Todas las funciones trabajan localmente. Sin anuncios ni suscripción.

INSTALACIÓN EN WINDOWS (GRATIS)

1. Conserva tu copia de Revelo v1.6.2 STABLE/FROZEN sin reemplazar.
2. En github.com/JavierJB23/FotoPapel pulsa Add file > Upload files.
3. Sube los archivos de Revelo_v1_7_1_ACTUALIZACION.zip descomprimidos.
   advanced_layout.py debe quedar junto a main.py.
   book_renderer.py y caption_editor.py son módulos nuevos y van al lado
   de main.py; advanced_layout.py y main.py sustituyen sus versiones.
   test_v171_refinements.py debe quedar en la carpeta tests/.
4. Pulsa Commit changes. Abre la pestaña Actions.
5. Descarga Revelo-Windows-CARPETA si el workflow acaba en verde.
6. Descomprime el ZIP, conserva toda la carpeta y abre Revelo.exe.
   No extraigas solo el ejecutable: necesita los componentes adyacentes.

El workflow del repositorio ya utiliza PyInstaller --onedir. No necesitas
cambiarlo ni instalar Python. El ZIP completo incorpora una copia de
la configuración de compilación por si la necesitas alguna vez.

PRUEBAS SUGERIDAS ANTES DE DECLARAR STABLE

- Arrastra al panel seis fotos y un PDF desde el Explorador.
- Elige «Grande arriba + 2 abajo» y revisa las dos hojas resultantes.
- Añade pies a dos fotos: uno debajo y otro personalizado sobre la imagen.
- Cambia tipografía, tamaño y color y comprueba que no aparecen fondos
  rectangulares detrás del texto. Activa «Numeración» omitiendo la portada.
- Abre «Libro abierto»: verifica que la portada aparece sola a la derecha,
  sin hoja artificial a la izquierda, y después avanza para ver el lomo.
- Exporta PDF y Word y revisa la maquetación.
- Guarda un proyecto .revelo, ciérralo y vuelve a abrirlo: deben regresar
  el diseño elegido, el orden, las leyendas y los ajustes de numeración.

REVELO v1.6.2 STABLE/FROZEN permanece como referencia segura.


FIX02 cabecera compacta: corregida holgura horizontal para Windows/GitHub Actions.
