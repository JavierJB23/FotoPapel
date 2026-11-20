REVELO v1.6.2 — FIX DE RECORTE, MINIATURAS Y GUÍAS DE ALINEACIÓN
=================================================================

NOVEDADES

1) EDITOR FOTOGRÁFICO — BOTÓN «RECORTAR»
   - Aparece a la izquierda de «Original (mantener)» y «Ver resultado».
   - Sin una selección nueva está desactivado; cuando dibujas o modificas el
     rectángulo de recorte se ilumina en crema.
   - Al pulsar «Recortar» muestra inmediatamente la foto ya recortada.
   - «Modificar recorte» permite volver a ajustar los límites.
   - Los originales siguen intactos: confirma al pulsar «Guardar edición».

2) ORIENTACIÓN SINCRONIZADA EN TODAS LAS VISTAS
   - Las miniaturas de «Fotos y PDF cargados» y de «Orden del contenido»
     reflejan la orientación del papel actual (horizontal/vertical/automática).
   - El refresco ocurre al cambiar orientación, formato de papel, encaje o
     márgenes. No hace falta cerrar ni volver a abrir ninguna foto.
   - Las miniaturas se procesan en resolución reducida para no ralentizar
     los documentos con decenas de fotos; el PDF/Word usa resolución completa.
   - También respeta las portadas personalizadas y las ediciones fotográficas.

3) GUÍAS DE ALINEACIÓN MAGNÉTICAS EN PORTADAS/SEPARADORES
   - Al mover texto o foto por el editor personalizado aparecen líneas
     aguamarina al acercarse a los ejes centrales y a los bordes de la hoja.
   - Existe una pequeña zona de atracción y retención de unos 22 píxeles
     al abandonar cada guía. Así se puede colocar con precisión.
   - Las líneas desaparecen cuando sueltas el ratón; NO se imprimen.
   - No afecta a las posiciones ya guardadas ni a los archivos antiguos.

INSTALAR EN WINDOWS (COMO SIEMPRE)

1. Conserva una copia de tu ejecutable anterior estable.
2. En tu repositorio GitHub de Revelo (JavierJB23/FotoPapel), sube
   los archivos de la actualización sobre los anteriores.
3. Los nuevos alignment_guides.py y thumbnail_preview.py van en la raíz
   junto a main.py; test_v162_usability.py va dentro de tests/.
4. Pulsa Commit changes y entra en Actions.
5. Descarga Revelo-Windows-EXE cuando la compilación termine en verde,
   descomprime el ZIP y abre Revelo.exe.

No cambian las dependencias ni el archivo .github/workflows/windows-exe.yml.
No se necesita instalar Python, ni modificar el QR, ni pagar licencias.

PRUEBA RECOMENDADA
- Arrastra un recorte: confirma que «Recortar» se ilumina en crema;
  púlsalo, comprueba la imagen sin la zona descartada y, si quieres,
  usa «Modificar recorte».
- Abre una portada horizontal; cambia a vertical en el menú principal y
  comprueba que las miniaturas de ambos paneles se actualizan.
- En «Personalizar portada», selecciona título/foto; al acercarla al eje
  horizontal o vertical aparecerá la guía aguamarina. Suelta y verifica
  que la línea no aparece en la exportación.

CHECKPOINT
Versión candidata: Revelo v1.6.2. Conserva la versión STABLE anterior
hasta validar este nuevo EXE en tu ordenador.
