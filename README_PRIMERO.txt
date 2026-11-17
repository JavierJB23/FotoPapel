REVELO v1.5 — PORTADAS, SEPARADORES Y PÁGINAS EN BLANCO
======================================================
Versión candidata. Conserva Revelo v1.4.3 STABLE como respaldo.

QUÉ CAMBIA
----------
El botón «+ Página» permite añadir:
 - Portada con título y subtítulo opcional.
 - Separador con título de capítulo (por ejemplo, «Postres»).
 - Página en blanco (también puede llevar fondo crema, azul noche o aguamarina).

Puedes elegir colores Blanco, Crema, Azul noche y Aguamarina.
Pulsa «Editar página» debajo de una miniatura para cambiar sus textos y colores.

Las páginas especiales ocupan SIEMPRE una hoja completa, aunque selecciones
2, 4, 6 o 9 fotografías por hoja. Se pueden mover con flechas o arrastrando,
como las imágenes. Los márgenes de encuadernación se siguen respetando.

El título se compone de nuevo al tamaño de papel seleccionado antes de exportar:
A4, A5, A6, 10x15 y el resto de formatos admitidos por Revelo.

GUARDAR Y RECUPERAR
------------------
Los proyectos .revelo conservan textos, estilos, posiciones, fotos y páginas PDF.
Los proyectos hechos con v1.4.3 también se pueden abrir.

Los PDF creados por Revelo contienen el adjunto reversible de originales y
las características de las páginas especiales. Al importarlos de nuevo, Revelo
recupera los títulos como páginas independientes, además de las fotografías.

CÓMO ACTUALIZAR TU EJECUTABLE WINDOWS
------------------------------------
1. Conserva una copia del anterior Revelo.exe v1.4.3 STABLE.
2. Descomprime Revelo_v1_5_ACTUALIZACION.zip.
3. En tu repositorio de GitHub «JavierJB23/FotoPapel», pulsa Add file > Upload files.
4. Sube el contenido descomprimido del ZIP, no el ZIP en sí. Los archivos son:
     main.py
     processor.py
     project_io.py
     pdf_sources.py
     special_pages.py  (NUEVO)
     README_PRIMERO.txt
     tests/test_special_pages.py  (NUEVO; debe estar dentro de tests)
5. Pulsa Commit changes.
6. En Actions se generará el nuevo Revelo.exe automáticamente.
7. Cuando la compilación esté verde, abre el trabajo y descarga
   el archivo Revelo-Windows-EXE. Descomprímelo y abre Revelo.exe.

No hay que instalar Python en Windows ni modificar la configuración de Actions:
las dependencias actuales de la v1.4.3 siguen siendo suficientes.

PRUEBA RECOMENDADA
-----------------
1. Abre Revelo, pon «Fotos por hoja: 4» y carga cuatro fotos.
2. Pulsa «+ Página» y crea un separador «Postres» en fondo Crema.
3. Añade otras cuatro fotos. Ordena la lista para que el separador quede en medio.
4. En Previsualización deberían salir TRES hojas (4 fotos, separador, 4 fotos).
5. Exporta a PDF. Guarda además un archivo .revelo.
6. Cierra y abre el proyecto guardado. Comprueba los títulos, colores y orden.

NOTAS
-----
La «Página en blanco» se exporta como hoja completa y puede usarse para ajustar
la paginación de una encuadernación.
El contenido nuevo se crea y procesa en tu ordenador. No usa una nube.
Los PDF que compartas pueden contener sus imágenes originales como adjuntos;
comprueba el documento antes de distribuirlo a otras personas.
