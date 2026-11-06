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

## F2.2 · Activación pública del tablero

GitHub devolvió **HTTP 403** al crear el sitio con build_type workflow. El GET antes y después devolvió HTTP 404. El artefacto del tablero está cifrado y el flujo omite el paso de despliegue mientras el sitio no esté habilitado. Hace falta habilitar Pages como dueño o conceder al token el permiso Pages de escritura. [API oficial de Pages](https://docs.github.com/en/rest/pages/pages#create-a-apiname-pages-site)

El enlace del botón Tablero en ntfy depende de una URL HTTPS publicada. Los avisos de prueba llegaron a ambos canales con HTTP 200 y el campo de acción se verificó con HTTP simulado. El modo sombra sigue activo.
