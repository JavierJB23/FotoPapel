REVELO v1.4.3 — VENTANA DE EXPORTACIÓN Y PDF REUTILIZABLE
========================================================

Esta es una actualización de Revelo v1.4.2 (o de v1.4.x). Conserva el resto de
las funciones, incluida la importación desde iPhone por QR, los proyectos
.revelo, la maquetación de 1/2/4/6/9 imágenes por hoja y los cuatro encajes.

NOVEDAD 1 — EXPORTACIÓN COMPLETADA CON LA ESTÉTICA DE REVELO
-----------------------------------------------------------
Al exportar se abre una ventana propia con los colores azul oscuro y aguamarina,
el número de hojas y elementos, la ruta del archivo, los avisos de resolución y
los botones «Abrir carpeta» y «Aceptar».

NOVEDAD 2 — REUTILIZAR UN PDF SIN CONSERVAR EL FONDO ANTERIOR
------------------------------------------------------------
LOS PDF GENERADOS DESDE v1.4.3:
Revelo guarda también las imágenes fuente dentro del PDF como un adjunto ZIP
interno. Es un PDF normal y se puede visualizar e imprimir en los lectores
habituales. Al importarlo otra vez en Revelo, el programa recupera las imágenes
fuente en su orden, incluso si antes había varias por hoja. Puedes aplicar
«Ajustar (sin recortar)», «Rellenar», «Ajuste inteligente» o «Ampliar fondo»
como si acabaras de cargar esas fotografías por primera vez.

IMPORTANTE: Estos PDF pueden pesar más. Cualquier persona a quien compartas el
archivo podría extraer las fotografías fuente incluidas, incluso las zonas
originales que no se veían en la impresión. Si quieres compartir solo una copia
visual sin esos adjuntos, puedes usar una herramienta para eliminar adjuntos
o imprimir a PDF desde un visor, revisando el resultado antes de enviarlo.

PDF ANTIGUOS GENERADOS ANTES DE v1.4.3:
Como esos archivos no contenían las fotos originales, Revelo intenta reconocer
las franjas blancas o desenfocadas que rodean una imagen y recortarlas antes de
aplicar el encaje seleccionado. La recuperación es aproximada y solo se realiza
cuando el detector tiene confianza. No se pueden garantizar resultados exactos
para PDFs ya aplanados ni recuperar contenido que fue recortado previamente.
En caso de duda, se conserva la página íntegra.

El programa trabaja en local y no altera los documentos de origen.

CÓMO ACTUALIZAR DESDE v1.4.2
---------------------------
1. Conserva tu Revelo.exe actual como respaldo.
2. Descarga y descomprime el ZIP «Revelo_v1_4_3_ACTUALIZACION.zip».
3. Abre el repositorio https://github.com/JavierJB23/FotoPapel
4. Pulsa «Add file» > «Upload files» y sube los siguientes archivos:
     main.py
     processor.py
     pdf_sources.py        (nuevo)
     pdf_cleanup.py        (nuevo)
     requirements.txt
     README_PRIMERO.txt
     tests/test_pdf_sources.py (manteniendo la carpeta tests)
5. Pulsa «Commit changes».
6. GitHub Actions instalará también pypdf desde requirements.txt y compilará
   Revelo.exe; en «Actions» descarga el artefacto «Revelo-Windows-EXE» cuando
   el trabajo aparezca en verde.
7. Descomprime el artefacto, cierra el Revelo anterior y abre el nuevo .exe.

No es necesario subir la carpeta oculta .github para esta actualización.
Si GitHub Actions falla al empaquetar alguna dependencia, puedes usar el archivo
WORKFLOW_REVELO_v1_4_3_PARA_GITHUB.txt incluido aparte, pegándolo en
.github/workflows/windows-exe.yml mediante el editor web de GitHub.

ESTADO: v1.4.3 candidata a STABLE, pendiente de probar el nuevo .exe en Windows.
Conserva v1.3 STABLE y/o v1.4.2 como copia de seguridad.
