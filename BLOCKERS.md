# Bloqueos

## Fase 1 · Taxonomía de talla, condición, color y capucha

- Intentos. Se leyó `catalogTree`, el estado `initialCatalogState`, la ficha pública y los recursos JavaScript enlazados. Se verificó el catálogo de marcas y se consultaron seis fichas para contrastar los atributos.
- Resultado. Vinted usa 267 para «Sudaderas y sudaderas con capucha», bajo 79, y expone 1812 para sudaderas con cremallera. La evidencia agrupa prendas con y sin capucha. El RSC de ficha usa 515 para el atributo de interfaz tanto en L como en XL, y 50 para cinco estados. El color «Gris» aparece sin ID en la ficha.
- Error comprobado. El endpoint antiguo `/api/v2/catalog/items` y las rutas probadas de `/svc-filters/filters` y `/svc-filters/filters/search` devolvieron HTTP 404. El filtro público con 515 devolvió HTTP 200 con cero tarjetas tanto para Stone Island como para Supreme, incluso sin limitar categoría en Stone Island.
- Qué haría falta. Capturar una selección funcional del filtro de Vinted y comprobar cada ID con su respuesta real. Mientras tanto, el programa conserva las marcas verificadas y comprueba la talla, la condición, el color y la evidencia de capucha localmente.

## Fase 1 · Visitas en ficha pública

- Intentos. Se inspeccionaron el HTML y el RSC públicos de la ficha. Se extrajeron la descripción, las fotos, el estado, el color, los favoritos y el texto relativo de publicación.
- Resultado. La respuesta capturada contiene `favourite_count`. No contiene los campos de visitas buscados (`view_count` y `viewCount`). El parser conserva visitas como valor ausente y el precio con protección publicado en el catálogo.
- Qué haría falta. Una respuesta pública que exponga visitas y una captura real para añadir la extracción.

## Fases 6 y 7 · Doctor y verificación en vivo del filtro

- Intentos. `vh doctor`, `pytest -m live` y `vh selftest --report` se ejecutaron contra Vinted.
- Resultado. La portada, las cookies, el parser de catálogo, la combinación de marcas, la ficha, el vendedor y el armario respondieron. `doctor` devolvió salida 1 con «Filtro real · 0 Stone Island XL» y la lista de IDs pendientes. El test en vivo del filtro devolvió `AssertionError: Stone Island XL: el filtro público devolvió 0 tarjetas`. Pasaron dos de las tres pruebas en vivo y las ocho etapas del extremo a extremo.
- Qué haría falta. Resolver y probar los IDs de filtros pendientes. `selftest --report` devuelve salida 1 cuando su suite en vivo falla.
