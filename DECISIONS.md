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
