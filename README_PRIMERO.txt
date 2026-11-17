REVELO v1.4.2 — CORRECCIÓN DE TRANSICIÓN ENTRE FOTOGRAFÍAS Y FONDO
=================================================================

QUÉ SE HA CORREGIDO
------------------
Al utilizar «Ampliar fondo (sin recortar)» con varias imágenes por hoja,
la versión 1.4.1 creaba un fondo para toda la hoja, pero después pegaba
cada imagen junto a OTRO fondo propio con límites rectangulares visibles.
Eso producía el efecto de "parche" que se veía debajo de las recetas.

Ahora se crea UN SOLO fondo compartido para toda la hoja. Encima se colocan
las imágenes originales manteniendo sus proporciones y suavizando únicamente
una pequeña transición en los bordes, sin pegar un segundo fondo rectangular.
La zona central y los textos permanecen nítidos y no se recorta contenido.

Este sistema continúa siendo un fondo extendido desenfocado, NO una
reconstrucción generativa de la fotografía: el límite entre fotografía nítida
y fondo desenfocado puede seguir apreciándose ligeramente. Lo importante es
que ya no existe el corte recto tipo copia-pega.

SE MANTIENE TODO LO ANTERIOR
---------------------------
* 1, 2, 4, 6 o 9 imágenes por hoja, con la opción de 1 sin cambios.
* Encajes «Ajustar», «Rellenar», «Ajuste inteligente» y «Ampliar fondo».
* Márgenes de encuadernación, ordenación, previsualización.
* Importación de fotos/PDF y transferencia por QR desde el móvil.
* Proyectos portables .revelo con las imágenes incluidas.
* Exportación a imágenes, Word y PDF.

ACTUALIZAR REVELO v1.4 O v1.4.1 (SIN NECESIDAD DE INSTALAR v1.4.1)
-------------------------------------------------------------------
1. Conserva una copia del Revelo.exe que funciona actualmente.
2. Descomprime el ZIP de actualización v1.4.2.
3. Abre https://github.com/JavierJB23/FotoPapel
4. En «Add file» > «Upload files», sustituye estos tres archivos,
   MANTENIENDO la ruta de tests/test_projects_layout.py:
      processor.py
      README_PRIMERO.txt
      tests/test_projects_layout.py
5. Pulsa «Commit changes».
6. En Actions comprueba que se completan los tests y la compilación.
7. Descarga el artefacto «Revelo-Windows-EXE», extráelo y abre Revelo.exe.

No hay que cambiar main.py, el logo, el QR, project_io.py ni el workflow.
El ejecutable debe validarse en un ordenador Windows después de compilarlo.

ESTADO: v1.4.2 CANDIDATA A STABLE. Conserva la v1.3 STABLE como respaldo.
