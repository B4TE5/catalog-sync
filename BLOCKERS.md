# Bloqueos

## Resueltos en la corrección

- **Tallas de hombre.** El RSC del catálogo de sudaderas 267 confirma L = 209 y XL = 210 en el grupo MEN-DE. Las dos consultas públicas devolvieron 96 Stone Island de la talla pedida. [Evidencia y URLs](config/vinted_ids.yaml)
- **Diagnóstico y suite en vivo.** Doctor y los cuatro tests live terminaron con salida 0. La autoprueba completó las ocho etapas. [Informe de pruebas](TEST_REPORT.md)
- **Visitas en el heat.** La señal depende de favoritos y edad. La prueba de regresión verifica que variar las visitas deja el resultado igual. [Prueba](tests/test_heat.py)

- **Muestra de visión.** Se completó sobre 30 anuncios de Stone Island y 192 fotos, con 10 QR legibles en el dominio Certilogo, siete detectados sin lectura y 13 sin QR. [Medición por anuncio](DECISIONS.md)

## Limitaciones que permanecen

- **Taxonomía opcional.** La categoría 267 agrupa sudaderas con y sin capucha. Los IDs públicos separados para capucha, los de condición y el de gris quedan pendientes. El catálogo funciona con marca, categoría y talla verificadas. La ficha aporta las etiquetas para los demás gates. [Evidencia anterior](DECISIONS.md)
- **Visitas públicas.** Las capturas de ficha carecen de `view_count` y `viewCount`. Para extraer el contador haría falta una fuente pública real que lo exponga.
- **Referencias ORB.** El directorio de referencias carece de imágenes de autenticación. La ejecución de ORB devuelve una lista vacía de partes. [Formato de referencias](refs/README.md)

## Resueltos · F2.2 Pages y F2.3 botón Tablero

GitHub devolvió **HTTP 403** al crear el sitio con build_type workflow. El GET antes y después devolvió HTTP 404. Tras la activación manual por el dueño, la API de configuración devolvió HTTP 200 y `actions/deploy-pages` publicó el artefacto en la ejecución 42296435101. En Chromium, el HTML público coincidió con el artefacto. El enlace de `vh board-url` mostró 48 tarjetas y la URL pública mostró la pantalla neutra. [API oficial de Pages](https://docs.github.com/en/rest/pages/pages#create-a-apiname-pages-site)

El botón Tablero deriva la dirección pública de Pages. Ambos avisos de prueba devolvieron HTTP 200 y la API de ntfy devolvió la acción con la URL sin clave en cada canal. El modo sombra sigue activo.

## Resuelto · Cadencia mediante bucle de Actions

Se consultó la API de runs con `event=schedule` entre aproximadamente las 20:47 y las 21:30 del 6 de noviembre (hora de Madrid). El workflow de `main` estaba `active` y la última consulta devolvió HTTP 200 con `total_count: 0`. En esa sesión quedó pendiente observar tres ejecuciones programadas en verde y cotejar sus novedades con el estado restaurado. Las dos pasadas manuales y los issues confirmaron la persistencia cifrada. GitHub documenta posibles retrasos y omisiones en eventos programados. La API carece de un motivo para esta ventana. [Eventos programados de GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

La petición del 7 de noviembre sustituye la cadencia del cron por un bucle y relevo. Se verificaron 3 iteraciones completas del coordinador 42391701686, con intervalos de 498.57 s, 646.96 s, guardado cifrado y Pages en cada una. El sucesor 42393577665 se inició con la identidad automática de Actions. El despertar duplicado 42391821189 omitió la captura y el bucle. El criterio anterior de tres eventos schedule queda sustituido por esta verificación del bucle.

## Resuelto · Autoprueba con tres candidatos

Las tres autopruebas anteriores terminaron en 6/8, 7/8 y 7/8 porque las fichas se descartaban antes de score. CORRECCION_2 añade el fallback permitido a un caso real de recall, identificado en la salida y guardado en el tablero temporal. La verificación final de correction-2.2 completó 8/8 en 75,0 s: catálogo en vivo, tres fichas reales y visión/score del caso capturado 10653233816, good con 70 puntos. Las ejecuciones previas de esta corrección también alcanzaron 8/8 con un score de la muestra en vivo. La suite live final aprobó cuatro casos y doctor terminó en verde.
