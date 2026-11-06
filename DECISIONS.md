# Decisiones

## 2026-11-06 · Fase 0

- Se trasladó `profiles.yaml` a `config/profiles.yaml` conservando su contenido. El archivo suministrado estaba en la raíz. Se descartó duplicarlo para evitar dos fuentes de configuración.
- Se fijó Python a la serie 3.12 y la caché de uv a `.uv-cache` mediante `UV_CACHE_DIR` durante la sesión. La caché predeterminada ya había fallado con el error de acceso 5.

## 2026-11-06 · Fase 1 · Transporte y parsers

- El catálogo se extrae de `self.__next_f.push` → `items.items[].productItem`. Se conservó el camino comprobado por la prueba inicial. `/api/v2/catalog/items?search_text=stone%20island` devolvió HTTP 404.
- La ficha pública del anuncio 10682766478 devuelve RSC. Tiene cinco fotos, texto, estado, color, categoría y favoritos. La fecha es relativa (`hace 8 horas`) y se interpreta como aproximada. La captura carece de visitas y de importe total estructurado en la ficha. Se conserva el importe con protección del catálogo.
- La home devolvió HTTP 200 con siete cookies de sesión. El perfil JSON y el armario HTML devolvieron HTTP 200. La reputación `0.94` se expresa como `4,70/5` y la cuenta indica doce valoraciones y 18 anuncios activos.
- El catálogo español incluye anuncios de Italia. La captura de Stone Island contiene el anuncio 10682766478, cuyo vendedor declara `country_code: IT` en la respuesta pública [del perfil](https://www.vinted.es/api/v2/users/3139641830).
- La taxonomía capturada da la categoría 267 como «Sudaderas y sudaderas con capucha», bajo 79 «Jerséis y sudaderas» de Hombre. El valor 267 no constituye prueba de capucha.
- El primer filtro por talla usó el parámetro histórico `size_ids[]`. Se descartó tras ver que el estado RSC solo reflejaba marca y que las tarjetas tenían tallas XS a XXL.

## 2026-11-06 · Fases 2 a 5 · Decisiones del embudo

- La búsqueda combinada usa `catalog[]`, `brand_ids[]` y, cuando se verifique un ID utilizable, `size_ids[]` en la ruta general `/catalog`. Los perfiles incompletos conservan búsqueda por texto y gates locales. Se descartó usar `attribute_ids[...]` en la URL de la página, pues ese esquema del JavaScript se aplica a su servicio interno y no cambió la búsqueda pública.
- Se guardan por separado los anuncios descubiertos en una consulta nueva y las novedades de búsquedas que ya se habían visto. Las dos primeras pasadas tenían consultas normales distintas y el contador inicial mezclaba ambos casos. Se ajustó el contador sin descartar esos anuncios.
- El presupuesto de enriquecimiento incluye cada GET de foto. Se prefieren los candidatos con talla explícita y señales de la prenda. Se intenta al menos un candidato por perfil disponible antes de agotar la cola de un solo perfil.
- La protección observada se conserva. Los valores de protección y envío que falten se estiman con los parámetros editables de scoring.yaml. El valor de envío es un supuesto de trabajo, sin tarifa oficial atribuida a Vinted.
- Un QR detectado sin decodificar aporta la señal configurada y no se registra como Certilogo verificado. Las partes ORB tienen valor solo si existen referencias locales para compararlas.

## 2026-11-06 · Diez descartes del backfill

- 10685004624 · Pull Stone Island blanc · talla M. [Anuncio](https://www.vinted.es/items/10685004624-pull-stone-island-blanc)
- 10684981816 · Pull stone island · talla M. [Anuncio](https://www.vinted.es/items/10684981816-pull-stone-island)
- 10682697856 · Maglione in cotone Stone island · talla M. [Anuncio](https://www.vinted.es/items/10682697856-maglione-in-cotone-stone-island)
- 10685000267 · Stone Island bodywarmer maat S · 65.00 EUR fuera del rango del perfil. [Anuncio](https://www.vinted.es/items/10685000267-stone-island-bodywarmer-maat-s)
- 10682753363 · Mussola Gommata Stone Island - Uomo - Blu - L · 599.00 EUR fuera del rango del perfil. [Anuncio](https://www.vinted.es/items/10682753363-mussola-gommata-stone-island-uomo-blu-l)
- 10682720860 · Cortavientos Stone Island Nylon Metal / Tyvek Shield – Talla M · 200.00 EUR fuera del rango del perfil. [Anuncio](https://www.vinted.es/items/10682720860-cortavientos-stone-island-nylon-metal-tyvek-shield-talla-m)
- 10682645199 · Maglioncino leggero firmato Stone Island · color Azul marino distinto de gris. [Anuncio](https://www.vinted.es/items/10682645199-maglioncino-leggero-firmato-stone-island)
- 10679431541 · Stone Island sweater · color Menta distinto de gris. [Anuncio](https://www.vinted.es/items/10679431541-stone-island-sweater)
- 10679298183 · Camiseta Stone Island negra logo bordado | Básica premium · color Negro distinto de gris. [Anuncio](https://www.vinted.es/items/10679298183-camiseta-stone-island-negra-logo-bordado-basica-premium)
- 10682720384 · Pull stone island kaki taille 14 ans enfants · 80.00 EUR fuera del rango del perfil. [Anuncio](https://www.vinted.es/items/10682720384-pull-stone-island-kaki-taille-14-ans-enfants)

Stone Island en visión durante este backfill: 0 QR legibles, 1 QR detectado sin lectura y 0 sin QR. 54,73 s para el candidato procesado.

## 2026-11-06 · Confirmación de marcas y atributos

- Las ocho marcas de los perfiles tienen evidencia en páginas públicas. Dos fichas españolas confirmaron Rhude 435315 y Palm Angels 395367. Vinted mostró 96 tarjetas que pertenecían únicamente a Stone Island y Supreme en la consulta de ambas marcas. Se conservaron los parámetros repetidos en la URL. Se descartó enviar un único valor separado por comas. [Consulta combinada](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&brand_ids%5B%5D=14969&order=newest_first).
- El `id: 515` corresponde al atributo de interfaz `size` de tipo `faq`. La ficha Stone Island lo usa para XL y la ficha Rhude para L. El `id: 50` también se repite en los cinco estados diferentes comprobados. Se retiraron como supuestos IDs de filtro. Los valores se conservan bajo `detail_attribute_ids` como evidencia del intento. [Ficha XL](https://www.vinted.es/items/10682766478-felpa-stone-ilsland-uomo) y [ficha L](https://www.vinted.es/items/10682608341-sudadera-rhude-talla-s-oversize).
- Un filtro real con 515 devuelve cero tarjetas, con o sin categoría. La interfaz de ficha muestra «Gris» sin ID. El cliente filtra talla, condición y color por los valores que muestra cada tarjeta o ficha. [Filtro Stone Island](https://www.vinted.es/catalog?brand_ids%5B%5D=73306&size_ids%5B%5D=515&order=newest_first) y [ficha gris](https://www.vinted.es/items/10682246082-maglione-stone-island-grigio-girocollo-patch-compass-nuovo-con-cartellino).
- Se revalidaron las tarjetas de la primera iteración. Se descartaron el polo de manga corta de categoría 5492 y la prenda con la mención neerlandesa «geïnspireerde». La primera observación de QR de Stone Island queda como ensayo técnico sobre una prenda fuera de perfil.

## 2026-11-06 · Talla contradictoria en el título

Una ficha Rhude mostró L en su atributo, pero el propio vendedor escribió «Talla S (Oversize)». Se agregó un gate para títulos que indican una talla de forma explícita y contradicen la solicitada. Se descartó inferir talla de letras sueltas o de la palabra «oversize». Se revalidó la tarjeta ya puntuada. [Ficha Rhude](https://www.vinted.es/items/10682608341-sudadera-rhude-talla-s-oversize).

## 2026-11-06 · Corrección de tallas

L es 209 y XL es 210 en `MEN-DE` («Ropa») de `initialCatalogState.dynamicFilters`. Cada consulta devolvió 96 Stone Island de la talla solicitada y el RSC confirmó la selección. El 515 sigue documentado como atributo de interfaz. Doctor exige los IDs usados en peticiones. Los IDs opcionales de condición, gris y separación por capucha no intervienen en esas peticiones. [L](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&size_ids%5B%5D=209) · [XL](https://www.vinted.es/catalog?catalog%5B%5D=267&brand_ids%5B%5D=73306&size_ids%5B%5D=210)
