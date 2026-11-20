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
