REVELO v1.7 — MAQUETACIÓN AVANZADA
================================

ESTADO: CANDIDATA A STABLE. Conservar Revelo v1.6.2 STABLE/FROZEN aparte.

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

5. TEXTOS Y PIES DE FOTO
   Cada foto tiene un botón «Texto / pie de foto». Añade un título, una
   descripción/lugar/fecha y elige «Debajo» o «Sobre foto».
   Los textos se añaden solo a la impresión, nunca a las imágenes fuente.
   Puedes borrarlos vaciando ambos campos.

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
3. Sube los archivos de Revelo_v1_7_ACTUALIZACION.zip descomprimidos.
   advanced_layout.py debe quedar junto a main.py.
   test_v17_advanced.py debe quedar dentro de la carpeta tests/.
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
- Añade pies a dos fotos y activa «Numeración» omitiendo una portada.
- Abre «Libro abierto», avanza y vuelve a «Página única».
- Exporta PDF y Word y revisa la maquetación.
- Guarda un proyecto .revelo, ciérralo y vuelve a abrirlo: deben regresar
  el diseño elegido, el orden, las leyendas y los ajustes de numeración.

REVELO v1.6.2 STABLE/FROZEN permanece como referencia segura.
