REVELO v1.4 — PROYECTOS PORTABLES Y VARIAS FOTOS POR HOJA
==========================================================

IMPORTANTE
----------
La versión 1.3 STABLE continúa intacta. Este ZIP es una versión nueva para
probar; no borres tu ejecutable anterior hasta aprobar la v1.4.

NOVEDADES
---------
1. GUARDAR Y ABRIR PROYECTOS
   - Dos botones en la cabecera: Abrir proyecto y Guardar proyecto.
   - Guarda un archivo .revelo que incluye COPIAS de todas las imágenes,
     incluso las páginas importadas desde PDF y las recibidas por QR.
   - Conserva exactamente el orden, las etiquetas, el tamaño elegido, la
     orientación, el encaje, los PPP, la salida, la encuadernación y la
     distribución de fotos por hoja.
   - Permite abrir otro día aunque los archivos originales se hayan borrado.
   - El original no se modifica ni se elimina; al guardar un .revelo existente
     se pide confirmación.
   - No depende de Internet ni de servicios externos.

2. VARIAS FOTOS POR HOJA
   - Nuevo selector "FOTOS POR HOJA" en el panel derecho.
   - Posibilidades: 1, 2, 4, 6 y 9.
   - Las imágenes se agrupan en orden consecutivo (ej.: 10 fotos con 4 por
     hoja = 3 hojas). Para cambiar su posición, arrastra o usa las flechas.
   - La previsualización enseña las HOJAS ya compuestas, no fotos sueltas.
   - Se mantienen tamaño y orientación seleccionados; si la orientación es
     Automática, se toma la de la PRIMERA imagen de cada hoja.
   - Mantiene 3 mm de separación entre fotos y los márgenes de encuadernación
     se calculan por hoja, alternando izquierda/derecha si está activado.
   - Las fotos PDF importadas pueden usarse como elementos de la cuadrícula.
   - Exporta a PDF y Word (una hoja por página de documento).
   - Al exportar como imágenes con 2/4/6/9 fotos por hoja, crea PNG de cada
     hoja completa. En modo 1 se mantiene el formato original de cada foto.

SE MANTIENE TODO LO DE v1.3
--------------------------
Importación QR por Wi-Fi local, HEIC/HEIF, importación de PDF, encuadres,
fondo ampliado, ordenación, previsualización, barra aguamarina y porcentaje,
impresión comercial A3/A4/A5/etc. y exportación a imágenes, PDF y Word.

ACTUALIZAR EL REPOSITORIO (SIN PROGRAMAR)
----------------------------------------
1. Conserva tu antiguo Revelo.exe v1.3.
2. Abre https://github.com/JavierJB23/FotoPapel
3. Pulsa Add file > Upload files.
4. Suba los archivos de este ZIP de actualización descomprimido:
       main.py
       processor.py
       project_io.py        <-- NUEVO Y OBLIGATORIO
       README_PRIMERO.txt
       tests/test_projects_layout.py   <-- nueva prueba
   Arrastra la carpeta tests con su archivo dentro para conservar su ruta.
5. Confirma con Commit changes. No hace falta modificar .github/workflows.
6. En Actions se ejecutará la compilación automática. Cuando aparezca verde,
   abre el trabajo y descarga Artifacts > Revelo-Windows-EXE.
7. Descomprime el ZIP de GitHub y prueba Revelo.exe.

NOTAS
-----
- Si el PDF original tenía márgenes blancos, la detección ya presente en
  v1.3 se conserva en modo de una fotografía por página.
- Una página PDF importada es una imagen de la página; no recupera texto
  editable de forma individual.
- Para añadir fotos a un proyecto reabierto, pulsa + Añadir fotos / PDF o QR.
- Archivo .revelo es un proyecto portable, no un PDF listo para imprenta.
  Para imprimir, usa Exportar fotos y elige PDF o Word.
- El proyecto contiene copias de las fotos y puede ocupar bastante espacio.
- No se ha podido verificar un EXE de Windows directamente en este entorno;
  se compila con GitHub Actions y hay que comprobarlo en el PC.
