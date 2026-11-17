FOTOPAPEL v1.1 — CONVERSOR Y ORGANIZADOR DE FOTOS PARA IMPRIMIR
==========================================================
Programa gratuito para Windows, sin publicidad, sin registro y sin subir fotos a internet.


NOVEDADES v1.1
--------------
 - Ajuste inteligente (max. 5 %): conserva toda la imagen y permite un
   estiramiento limitado para reducir las bandas; el espacio que quede
   se rellena con colores extraidos de los bordes (no blanco).
 - Ampliar fondo (sin recortar): conserva toda la imagen sin deformarla
   y rellena las bandas con un fondo difuminado derivado de la foto.
   No utiliza IA generativa ni inventa detalles nuevos.
 - Boton Previsualización junto a Exportar fotos: enseña la pagina antes
   de exportar, con flechas para navegar las fotos en el orden elegido.
   Los cambios de encaje o tamaño se reflejan en la previsualización.
 - Barra de avance aguamarina y porcentaje de progreso entre parentesis.
 - 300 PPP como calidad inicial recomendada.

PARA ACTUALIZAR UN REPOSITORIO QUE YA TIENE FOTOPAPEL v1.0
---------------------------------------------------------
 1. Abre el repositorio FotoPapel en GitHub.
 2. Pulsa 'Add file' > 'Upload files'.
 3. Sube main.py, processor.py y README_PRIMERO.txt DE LA VERSION v1.1.
    Confirma la sustitución de los archivos existentes si se solicita.
 4. Pulsa 'Commit changes'.
 5. En 'Actions' se generara automaticamente un NUEVO FotoPapel.exe.
    Abre el trabajo reciente con el icono verde y descarga su artifact.
 6. Descomprime el ZIP de GitHub, cierra el programa antiguo y abre
    FotoPapel.exe nuevo. No hay que instalar nada.
 No hace falta volver a subir la carpeta .github, ni el icono.

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
      Ajuste inteligente (max. 5 %): recorta 0 %, estira un poco como
      maximo y rellena pequeñas bandas con los colores de la imagen.
      Ampliar fondo (sin recortar): conserva foto sin deformar y rellena
      el resto con fondo artificial desenfocado a partir de la imagen.
 5. Elige resolución: 150, 300 o 600 PPP. Se recomienda 300 PPP.
 6. Elige PDF (un único PDF), Word (un DOCX) o Imágenes (mismo formato).
 7. Para cambiar el orden, ARRASTRA una foto de la izquierda hasta una
    posición numerada a la derecha. También puedes usar las flechas ↑ ↓.
    El orden inicial es el de la carga. 'Orden inicial' lo restaura.
 8. Pulsa 'Previsualización' para revisar las paginas una a una antes
    de exportarlas (flechas para moverte entre páginas).
 9. Pulsa 'Exportar fotos' y elige dónde guardar el resultado.
    Veras la barra verde aguamarina y el avance (0 %)-(100 %).

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
