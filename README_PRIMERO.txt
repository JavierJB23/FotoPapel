REVELO v1.2.4 — FOTOS, PDF Y DOCUMENTOS LISTOS PARA IMPRIMIR
==========================================================

ACTUALIZACIÓN v1.2.4 — QUITAR BANDAS BLANCAS DE PDF ANTIGUOS
------------------------------------------------------------
- Corregido el fallo de v1.2.3: el detector anterior requería bandas blancas
  en los cuatro lados, aunque una foto ajustada suele tenerlas solo ARRIBA y
  ABAJO o solo a IZQUIERDA y DERECHA.
- Ahora detecta parejas opuestas de franjas blancas grandes. Si parecen
  procedentes de la maquetación anterior, recorta solo esos márgenes para
  volver a aplicar el encaje elegido al importar un PDF de Revelo.
- Con «Ampliar fondo (sin recortar)», las imágenes recuperadas de PDF antiguos
  reciben un fondo difuminado igual que las fotografías nuevas.
- Si no identifica franjas claras, la página PDF se conserva completa para
  evitar recortes en documentos de texto o maquetaciones poco habituales.
- La importación y el procesamiento son locales y nunca modifican originales.

CÓMO ACTUALIZAR DESDE v1.2.3
---------------------------
 1. Descomprime Revelo_v1_2_4_correccion_bandas_PDF.zip.
 2. En https://github.com/JavierJB23/FotoPapel/upload/main sube los archivos
    main.py, processor.py y README_PRIMERO.txt, así como tests/test_processor.py.
 3. Confirma la sustitución con «Commit changes».
 4. En GitHub Actions, descarga el nuevo artefacto Revelo-Windows-EXE.
 No necesitas tocar .github/workflows ni el icono. Tampoco instalar Python.

Aplicación gratuita para Windows, totalmente local: tus fotografías y PDF
no se suben a Internet. No necesita registro ni suscripción.

QUÉ HA CAMBIADO DESDE FOTOPAPEL v1.1
-----------------------------------
- El programa se llama Revelo. El ejecutable será Revelo.exe y lleva el nuevo icono R.
- Nuevo desplegable "MÁRGENES DE ENCUADERNACIÓN" con Sí y No.
  Al elegir Sí, reserva 12 mm en el lado de la encuadernación y 3 mm en el
  resto. En páginas impares va a la izquierda y en páginas pares a la
  derecha, pensado para impresión a doble cara y espiral a la izquierda.
  Se aplica también en Rellenar (recortar), PDF, Word, JPG/PNG y vista previa.
- Nuevo botón "+ Añadir fotos / PDF". Elige fotos, uno o varios PDF o ambos.
  Cada página PDF aparece individualmente con miniatura, manteniendo su orden.
  Después puedes añadir fotos, moverlas a cualquier posición y exportar otro PDF.
- Si empiezas importando un PDF con tamaño comercial reconocible (A4, A5,
  etc.), Revelo ajusta automáticamente el desplegable de tamaño. Si el PDF
  trae páginas con tamaños diferentes, muestra un aviso.
- Quitados los prefijos 01 y 02 de los títulos de los dos paneles.
- Continúan los 4 encajes de v1.1, la previsualización y el progreso aguamarina.

IMPORTANTE SOBRE LOS PDF
-----------------------
Cada página se carga como PNG temporal renderizado a 300 PPP. Si detectamos
bandas blancas de relleno grandes, podemos separarlas y remaquetar la imagen;
en caso contrario, preservamos la composición de la página. No recupera las fotografías
originales por separado ni los textos como elementos editables. Al exportar,
las páginas se vuelven a generar: si son documentos de texto muy pequeño,
revisa el resultado en la previsualización y exporta a 300 PPP o más.

Los originales NO se modifican. Revelo impide expresamente que se sobrescriba
el PDF que has importado: tendrás que guardar una copia con otro nombre.
Las páginas PNG temporales se borran al cerrar el programa.
Los PDF protegidos con contraseña no se importan en esta versión.

Si importas un PDF con márgenes diseñados deliberadamente, comprueba la
previsualización: la detección automática de bandas nunca es infalible.
En documentos con texto o diagramas, conviene comprobar que no falte nada.

CÓMO USARLO PARA TU RECETARIO
----------------------------
1. Abre Revelo.exe.
2. Pulsa "+ Añadir fotos / PDF" y elige el PDF antiguo.
3. Verás una miniatura por página, con el mismo orden del PDF original.
4. Pulsa de nuevo "+ Añadir fotos / PDF" y elige las recetas nuevas.
5. Arrastra las fotos a las posiciones deseadas o usa las flechas.
6. Elige A5, calidad 300 PPP y encaje que prefieras.
7. Márgenes de encuadernación = Sí si quieres reservar el canal interior.
8. Pulsa "Previsualización" para revisar cada página.
9. Exporta como PDF (o Word). Pon un nombre NUEVO y guárdalo.

PARA ACTUALIZAR TU REPOSITORIO DE GITHUB (DESDE v1.1)
---------------------------------------------------
Necesitas actualizar 6 archivos de la carpeta principal del repositorio:
  main.py
  processor.py
  pdf_import.py                 (nuevo)
  requirements.txt
  icono.ico                    (la imagen del icono es nueva)
  README_PRIMERO.txt

Pasos:
 A. Abre tu repositorio: https://github.com/JavierJB23/FotoPapel
 B. Add file > Upload files. Sube esos 6 archivos DESCOMPRIMIDOS.
 C. Pulsa Commit changes. Ignora la compilación intermedia si se inicia.
 D. Edita también el archivo oculto que ya existe en GitHub:
    .github/workflows/windows-exe.yml
    - Entra en el archivo, pulsa el lápiz (Edit this file).
    - Sustituye su contenido por el archivo Windows_Workflow_Revelo.txt
      incluido en la entrega de Revelo v1.2.
    - Pulsa Commit changes.
 E. Entra en la pestaña Actions. Selecciona la ejecución más reciente
    llamada "Crear EXE de Revelo" y comprueba que tiene marca verde.
 F. En Artifacts descarga "Revelo-Windows-EXE".
    Descomprime el ZIP y abre Revelo.exe con doble clic.

No necesitas Python ni instalar programas de desarrollo en tu PC.
La compilación automática se ejecuta en Windows dentro de GitHub Actions.

ALTERNATIVA TÉCNICA (NO NECESARIA)
---------------------------------
Si ya tienes Python en Windows, ejecuta compilar_en_windows.bat para crear
Revelo.exe en la carpeta dist, después de instalar las dependencias gratuitas.

COMPONENTES LIBRES Y GRATUITOS
----------------------------
Python, tkinter, Pillow, ReportLab, python-docx, pypdfium2 y PyInstaller.
Solo uso personal. No se envían imágenes a ningún servicio remoto.
