# Capturas anónimas de Vinted España

- `catalog-stone-island.html.gz` — [búsqueda Stone Island](https://www.vinted.es/catalog?search_text=stone%20island&order=newest_first), 2026-11-06 00:28 (Madrid), HTTP 200.
- `item.html.gz` — [ficha 10682766478](https://www.vinted.es/items/10682766478-felpa-stone-ilsland-uomo), 2026-11-06, HTTP 200.
- `seller.json.gz` — [perfil JSON](https://www.vinted.es/api/v2/users/3139641830), 2026-11-06, HTTP 200.
- `seller.html.gz` — [armario público](https://www.vinted.es/member/3139641830), 2026-11-06, HTTP 200.

Cuerpos HTTP comprimidos, sin cabeceras ni cookies de la sesión. Se reemplazó el JWT otelToken de telemetría por REDACTED, fuera de los datos que lee el parser.

- `catalog-brand-only.html.gz` — [marca Stone Island en la categoría 267](https://www.vinted.es/catalog/267-hoodies-and-sweaters/brand/73306-stone-island?size_ids%5B%5D=515&order=newest_first). La ruta de marca aplica la marca, pero ignora la talla.
- `catalog-empty-size.html.gz` — [marca y talla en el catálogo general](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&size_ids%5B%5D=515&order=newest_first). El estado aplica ambos filtros y muestra cero resultados.


- `item-rhude.html.gz` — [ficha de Rhude en talla L](https://www.vinted.es/items/10682608341-sudadera-rhude-talla-s-oversize). El mismo ID de atributo 515 aparece en la ficha XL de Stone Island. El atributo 50 dice «Nuevo sin etiquetas» aquí y «Muy bueno» en Stone Island.
- `catalog-combined.html.gz` — [Stone Island y Supreme, dos claves repetidas](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&brand_ids%5B%5D=14969&order=newest_first). HTTP 200, 96 tarjetas de las dos marcas.

- `catalog-size-L.html.gz` y `catalog-size-XL.html.gz` conservan las respuestas de las URLs de talla en `config/vinted_ids.yaml`. HTTP 200, 96 Stone Island de la talla pedida en cada caso. RSC declara grupo MEN-DE y opciones 209 (L) y 210 (XL). JWT de telemetría redactado.

- `catalog-parent.html.gz` — [padre de jerséis y sudaderas de hombre](https://www.vinted.es/catalog?catalog%5B%5D=79&order=newest_first), 2026-11-07, HTTP 200. Conserva la taxonomía real: padre 79, jerséis 1811, sudaderas 267, sudaderas con cremallera 1812 y punto grueso 1815. JWT de telemetría redactado.

Los casos de `tests/recall/` y `tests/precision/` guardan la ficha real y, cuando superan los gates previos, el vendedor, armario y fotos consultados. Cada `capture.json` identifica su procedencia; los HTML se anonimizan igual que estas capturas. Se añaden mediante `vh replay <url> --save-fixture recall|precision`.
