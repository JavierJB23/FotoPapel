REVELO v1.5.1 — ORDENACIÓN VISUAL Y PÁGINAS PERSONALIZADAS
============================================================
Esta actualización parte de Revelo v1.5. Conserva una copia de tu versión
STABLE v1.4.3 y del ejecutable v1.5 antes de actualizar.

NOVEDADES
---------
1. Panel "Orden del contenido" más ancho; miniaturas y filas mucho más grandes.
2. Selección de biblioteca y selección de orden totalmente independientes.
   - Un clic en la biblioteca selecciona, pero NO desplaza nada.
   - Un clic en una fila de orden marca esa fila en verde aguamarina.
   - Para recolocar: arrastra al número deseado o utiliza las flechas ↑ ↓.
3. La portada ocupa siempre el primer puesto y no puede desplazarse.
   Solo puede existir una portada por composición.
4. "Personalizar" en la selección de color/diseño de "+ Página".
   - Fondo del color exacto que elijas o una fotografía propia.
   - Título y subtítulo opcionales, editables y con cualquier color.
   - Tamaño de letra ajustable por separado.
   - Desplaza los textos arrastrándolos por la hoja; usa "Mover título" o
     "Mover subtítulo" para elegir cuál quieres recolocar.
   - Las páginas prediseñadas (Crema, Blanco, Azul noche y Aguamarina)
     conservan su edición sencilla sin cambio manual de posiciones.
5. Los archivos .revelo y los PDF reversibles incluyen las fotos de fondo
   personalizadas, de modo que puedan recuperarse sin el original.
6. Siguen operativos el QR, Word/PDF, los 4 encajes y los márgenes.

CÓMO CREAR UNA PORTADA PERSONALIZADA
------------------------------------
1. Pulsa "+ Página".
2. Escoge "Portada" o "Separador".
3. En "COLOR / DISEÑO", selecciona "Personalizar" y pulsa "Guardar página".
4. En la nueva ventana elige "Color liso" o "Fotografía". Para subir una imagen,
   pulsa "Elegir foto...". Es posible no poner título ni subtítulo.
5. Escoge el texto que quieras mover (título o subtítulo), pulsa sobre la hoja
   y arrástralo hasta la posición deseada.
6. Cambia los tamaños con los deslizadores y guarda.
La portada quedará anclada en la posición 1 de la lista derecha.

CÓMO ACTUALIZAR EN TU GITHUB
---------------------------
1. Descomprime Revelo_v1_5_1_ACTUALIZACION.zip.
2. Entra en https://github.com/JavierJB23/FotoPapel/upload/main
3. Sube el contenido del ZIP DESCOMPRIMIDO a la raíz del repositorio:
   - main.py                      (reemplazar)
   - special_pages.py             (reemplazar)
   - project_io.py                (reemplazar)
   - pdf_sources.py               (reemplazar)
   - custom_editor.py             (NUEVO)
   - ordering_rules.py            (NUEVO)
   - README_PRIMERO.txt           (reemplazar)
   - tests/test_custom_editor_order.py (NUEVO, dentro de tests)
4. Pulsa "Commit changes". No hace falta tocar .github ni requirements.txt.
5. En la pestaña Actions, descarga "Revelo-Windows-EXE" cuando termine
   con la marca verde y extrae Revelo.exe.
No necesitas instalar Python ni ningún otro entorno en el ordenador.

PRUEBA RECOMENDADA
------------------
- Carga 10 fotos. Selecciona una miniatura izquierda y luego otra derecha.
  Verifica que ninguna se mueve sola y se ilumina la posición seleccionada.
- Añade una portada y prueba las flechas y el arrastre: siempre debe ser la 1.
- Crea una portada con foto propia, título movido y subtítulo opcional.
  Guarda un .revelo, cierra el programa y abre ese proyecto.
- Exporta a PDF, impórtalo y comprueba que puedes editar de nuevo la portada.

NOTAS
-----
Las páginas personalizadas se renderizan de nuevo para cada tamaño comercial.
Una imagen de fondo se escala para cubrir el papel, pudiendo recortarse en sus
bordes. El texto permanece dentro del área segura de encuadernación.
La foto de fondo se conserva en el proyecto o PDF; esto puede aumentar su tamaño.
Los PDF exportados que compartas pueden contener las fotos originales y fondos
adjuntos. El programa funciona localmente, sin enviar fotos a una nube.
