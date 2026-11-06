# Capturas anónimas de Vinted España

- `catalog-stone-island.html.gz` — [búsqueda Stone Island](https://www.vinted.es/catalog?search_text=stone%20island&order=newest_first), 2026-11-06 00:28 (Madrid), HTTP 200.
- `item.html.gz` — [ficha 10682766478](https://www.vinted.es/items/10682766478-felpa-stone-ilsland-uomo), 2026-11-06, HTTP 200.
- `seller.json.gz` — [perfil JSON](https://www.vinted.es/api/v2/users/3139641830), 2026-11-06, HTTP 200.
- `seller.html.gz` — [armario público](https://www.vinted.es/member/3139641830), 2026-11-06, HTTP 200.

Cuerpos HTTP comprimidos, sin cabeceras ni cookies de la sesión. Se reemplazó el JWT otelToken de telemetría por REDACTED, fuera de los datos que lee el parser.

- `catalog-brand-only.html.gz` — [marca Stone Island en la categoría 267](https://www.vinted.es/catalog/267-hoodies-and-sweaters/brand/73306-stone-island?size_ids%5B%5D=515&order=newest_first). La ruta de marca aplica la marca, pero ignora la talla.
- `catalog-empty-size.html.gz` — [marca y talla en el catálogo general](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&size_ids%5B%5D=515&order=newest_first). El estado aplica ambos filtros y muestra cero resultados.

