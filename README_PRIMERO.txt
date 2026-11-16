FOTOPAPEL — CONVERSOR Y ORGANIZADOR DE FOTOS PARA IMPRIMIR
==========================================================
Programa gratuito para Windows, sin publicidad, sin registro y sin subir fotos a internet.

PARA CONSEGUIR EL .EXE (EL METODO RECOMENDADO, SIN INSTALAR NADA)
----------------------------------------------------------------
Esta entrega incluye el código de la aplicación y una compilación automática
lista para usar en GitHub Actions. El resultado es un FotoPapel.exe autónomo.

 1. Entra en github.com y accede a tu cuenta.
 2. Pulsa '+' > 'New repository'. Ponle el nombre FotoPapel.
 3. Deja marcado 'Public' (para evitar costes de GitHub Actions).
    No añadas archivos iniciales: sin README ni .gitignore.
 4. Pulsa 'Create repository'.
 5. En la pantalla del repositorio, sigue el enlace 'uploading an existing file'.
 6. Abre el ZIP recibido y EXTRAE todos los archivos y carpetas.
 7. IMPORTANTE: sube main.py, processor.py, icono.ico, requirements.txt,
    compilar_en_windows.bat, README_PRIMERO.txt y la carpeta .github (oculta).
    Para que aparezca el workflow, debe quedar así:
       .github/workflows/windows-exe.yml
    Como el navegador puede ocultar carpetas con punto inicial, si falta
    el workflow usa GitHub > Add file > Create new file y escribe la ruta
    '.github/workflows/windows-exe.yml', copiando el contenido del ZIP.
 8. Pulsa 'Commit changes'.
 9. Abre la pestaña 'Actions', entra en 'Crear EXE de FotoPapel'.
    Si no comienza solo, pulsa 'Run workflow' > 'Run workflow'.
10. Cuando termine correctamente (marca verde), abre esa ejecución.
11. En 'Artifacts' descarga 'FotoPapel-Windows-EXE'. Descomprime ese ZIP.
12. ¡LISTO! Dentro está FotoPapel.exe. Abre con doble clic.

No necesitas instalar Python, ni abrir terminal, ni programar.
La compilación del .exe se hace en una máquina Windows de GitHub.

ALTERNATIVA EN TU PROPIO PC
---------------------------
Si ya tienes Python instalado, puedes ejecutar compilar_en_windows.bat.
Esto instala automáticamente las dependencias (gratuitas) y crea el .exe
que aparecerá en la carpeta dist. Si no tienes Python, usa GitHub.

COMO SE USA
-----------
 1. Pulsa '+ Añadir fotos'. Puedes seleccionar una o veinte a la vez.
 2. Elige tamaño: A3, A4, A5, A6, 9x13, 10x15, 11x15, 13x18, etc.
 3. Elige orientación: automática (según cada imagen), vertical u horizontal.
 4. Elige cómo encajar las fotos:
      Ajustar (sin recortar): la foto se ve completa. Si sobra espacio,
      se deja blanco.
      Rellenar (recortar): cubre el papel completamente, sin deformar,
      cortando bordes si las proporciones no coinciden.
 5. Elige resolución: 150, 300 o 600 PPP. Se recomienda 300 PPP.
 6. Elige PDF (un único PDF), Word (un DOCX) o Imágenes (mismo formato).
 7. Para cambiar el orden, ARRASTRA una foto de la izquierda hasta una
    posición numerada a la derecha. También puedes usar las flechas ↑ ↓.
    El orden inicial es el de la carga. 'Orden inicial' lo restaura.
 8. Pulsa 'Exportar fotos' y elige dónde guardar el resultado.

DETALLES DE IMPRESION
---------------------
 - PDF y Word: una foto por página, página del tamaño seleccionado.
 - PDF y Word conservan el orden elegido y admiten páginas horizontales y
   verticales mezcladas si seleccionas orientación automática.
 - Las imágenes separadas se guardan en una CARPETA NUEVA con nombres
   numerados 01, 02, 03, etc. Conservan JPG/PNG/TIFF/WEBP/BMP de origen.
 - Las imágenes se preparan en los píxeles correspondientes a la medida
   elegida y la resolución PPP.
 - JPG, PNG y TIFF incluyen metadatos PPP. Otros formatos como WEBP y BMP
   pueden no almacenar esa medida de manera reconocida por todos los visores.
 - El PDF y Word contienen el tamaño físico exacto de página. Para imprimir
   selecciona 'Tamaño real / 100 %' y desactiva 'Ajustar a página' si quieres
   mantener las dimensiones.
 - Algunas impresoras no imprimen hasta el borde; si ocurre, la impresora
   podrá añadir márgenes o necesitar el modo de impresión sin bordes.
 - Ampliar una fotografía pequeña no recupera detalle. Se te avisará
   si hay imágenes de baja resolución para el tamaño escogido.
 - Jamás se modifican las fotografías originales.

REQUISITOS
----------
Windows 10/11, 64 bits. No hace falta conexión a internet para usar el .exe.

Dependencias gratuitas y de código abierto: Pillow, ReportLab,
python-docx y PyInstaller. La interfaz usa Tkinter (Python).
