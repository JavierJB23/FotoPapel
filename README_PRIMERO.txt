REVELO v1.3 — IMPORTAR FOTOS DEL MÓVIL POR QR
============================================

Versión de uso personal, gratuita, local y sin servicios en la nube.
Partimos de Revelo v1.2.4 (versión estable). Se conservan todos sus formatos
A4/A5/10x15, los cuatro modos de encaje, encuadernación, PDF/Word,
previsualización y ordenación de páginas.

NOVEDADES v1.3
--------------
* Cabecera limpia: sin número de versión ni rótulo lateral.
* R del logotipo con los colores invertidos dentro de la aplicación.
* Botón «Importar desde móvil · QR» en el panel «Fotos y PDF cargados».
* QR temporal que abre una página local en el navegador del móvil (sin app).
* Transferencia de muchas fotos, una detrás de otra, con barra de progreso.
* Recepción automática en Revelo, en orden, junto a las fotos y PDF del PC.
* Lectura de formatos habituales del iPhone, incluidos HEIC y HEIF.
* El fichero recibido se guarda íntegro, sin conversión ni recompresión
  DURANTE LA TRANSFERENCIA. La maquetación/exportación sí cambia tamaño
  o formato según lo seleccionado, como ya ocurría en Revelo.

CÓMO IMPORTAR FOTOS DEL IPHONE
-----------------------------
1. Abre Revelo.exe en tu ordenador Windows.
2. Comprueba que PC y iPhone estén en el mismo router/red doméstica.
   Puede ser el PC por cable Ethernet y el iPhone por Wi-Fi.
3. Pulsa «Importar desde móvil · QR».
4. Si Windows Defender pregunta por firewall, permite acceso a REDES PRIVADAS.
   No es necesario permitir acceso a redes públicas.
5. Escanea el QR con la cámara del iPhone y abre el enlace en Safari.
6. Pulsa Seleccionar archivos/fotos, elige varias de la galería.
7. Pulsa «Enviar fotos». Verás el progreso del lote.
8. Las fotos llegarán automáticamente a «Fotos y PDF cargados» y podrás
   reordenarlas, previsualizarlas y exportarlas a PDF, Word o imágenes.
9. Cierra la ventana del QR cuando termines; así se apaga el servidor local.

IMPORTANTE: la primera ejecución puede activar una pregunta del firewall.
Si el iPhone no abre el enlace, revisa que ambos aparatos estén en la misma
red, que no sea una Wi-Fi de invitados aislada y que Windows permita Revelo
en redes privadas. En algunos routers hay 'aislamiento de clientes'.
No requiere cuenta, nube ni Internet, pero sí conectividad de red local.

SEGURIDAD Y PRIVACIDAD
---------------------
* El servidor local solo permanece activo mientras está abierta la ventana QR.
* El QR incluye un token aleatorio diferente en cada sesión. Sin él, no se
  pueden cargar fotos. No compartas el QR fuera de la red doméstica.
* Se comprueba que los archivos recibidos sean imágenes válidas y se pone
  un límite de 120 MB por foto, 500 fotos y 3 GB por sesión.
* No se utiliza ni se consulta ninguna API externa.
* Los archivos temporales recibidos del móvil se eliminan al cerrar Revelo.
  No es un sistema de copia de seguridad: conserva tus fotos en el iPhone y
  guarda siempre el PDF/Word/imágenes exportados antes de cerrar la app.

ACTUALIZAR TU REPOSITORIO DESDE v1.2.4
--------------------------------------
1. Descarga y descomprime el ZIP de Revelo v1.3.
2. En https://github.com/JavierJB23/FotoPapel/upload/main sube estos archivos
   y sustituye los que ya existen:
      main.py
      processor.py
      pdf_import.py
      mobile_import.py     <- archivo NUEVO
      requirements.txt
      README_PRIMERO.txt
      compilar_en_windows.bat
      logo_cabecera.png   <- archivo NUEVO
      tests/test_processor.py
      tests/test_mobile_import.py <- archivo NUEVO
3. Pulsa «Commit changes».
4. ACTUALIZA EL WORKFLOW (es necesario para empaquetar el icono y HEIC):
   abre https://github.com/JavierJB23/FotoPapel/edit/main/.github/workflows/windows-exe.yml
   y pega el contenido de «WORKFLOW_REVELO_v1_3_PARA_GITHUB.txt» que viene
   junto al ZIP. Confirma con «Commit changes».
5. En GitHub > Actions > «Crear EXE de Revelo» espera el icono verde.
6. En «Artifacts», descarga «Revelo-Windows-EXE», descomprime el archivo y
   ejecuta «Revelo.exe» con doble clic. No necesitas Python ni programar.

Si la compilación falla en Actions, comparte una captura de la pestaña
«Compilar Revelo.exe» y lo corregimos.

NOTAS
-----
* El título de la ventana no muestra la versión, pero esta distribución es v1.3.
* No he podido ejecutar aquí un .exe de Windows: la compilación real se hace
  en GitHub Actions, sobre Windows. He probado Python y la interfaz sobre
  Linux, con transferencias HTTP locales y exportación posterior a PDF.
* Los archivos originales existentes en tu PC no se modifican.
* El uso de pillow-heif para HEIC/HEIF se verifica al compilar en Windows,
  ya que no estaba instalado en este entorno de pruebas.
