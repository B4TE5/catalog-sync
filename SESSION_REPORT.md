# Informe de sesión · Vinted Hunter

## Sesión de corrección

2026-11-06T10:41:37.257582+01:00

- **Tallas.** L = 209 y XL = 210, grupo MEN-DE. Vinted devolvió 96 Stone Island de cada talla. Las dos capturas se guardaron como fixtures.
- **Gates.** Talla, capucha, color y estado se deciden con la ficha. Una ausencia queda como no confirmada. Las tarjetas antiguas afectadas se reabren al reaparecer.
- **Embudo.** El backfill general de diez páginas registró 1.022 Stone Island, 725 descartados y 297 pendientes. Los motivos e IDs están en [DECISIONS.md](DECISIONS.md).
- **Contraste focalizado.** 558 Stone Island, 423 descartados, 12 con ficha y 10 fichas nuevas. Tiers {'rejected': 423, 'pending': 135}.
- **Visión.** 30/30 anuncios, 192 fotos, 10 legibles, 7 detectados sin leer y 13 sin QR. Mediana de 43.97 s por anuncio, rango 11.42–82.53 s. Visión local con mediana de 0.26 s. El JSON local conserva el resultado y los tiempos por anuncio.
- **Heat.** Favoritos divididos por la edad con un mínimo configurable de cinco minutos. Se comprobó la invariancia ante visitas y el tratamiento de favoritos ausentes.
- **Cierre.** Doctor salió 0. Selftest con informe completó 8/8 etapas y su suite en vivo pasó 4/4. La comprobación offline final pasó 47 pruebas. [TEST_REPORT.md](TEST_REPORT.md)

## Primera sesión (histórico)

2026-11-06 09:20 +0100

## Resultado

Implementación local en Python 3.12, probada en Windows. El catálogo usa RSC, la ficha se enriquece con el perfil y el armario públicos, y SQLite conserva observaciones, puntuaciones y rastros. El tablero funciona por archivo y en localhost.

Las consultas públicas de marcas funcionan. Los IDs públicos de talla, condición, gris y separación por capucha siguen pendientes. Se aplican gates sobre las etiquetas de catálogo y ficha. La ficha pública examinada carece de contador de visitas.

## Pasadas contra Vinted

| Pasada | Peticiones | Vistos | Nuevos | Candidatos | Puntuados | Duración |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Run inicial | 25 | 1152 | 650 | 44 | 0 | 152.62 s |
| Segundo run inicial | 25 | 1152 | 339 | 68 | 0 | 138.17 s |
| Backfill (10 páginas) | 25 | 1152 | 0 | 11 | 1 | 142.31 s |
| Watch 1 | 25 | 827 | 0 | 34 | 1 | 151.66 s |
| Watch 2 | 25 | 879 | 1 | 58 | 2 | 131.78 s |
| Watch 3 | 25 | 837 | 1 | 42 | 2 | 146.38 s |
| Run final 1 | 25 | 844 | 67 | 43 | 1 | 151.30 s |
| Run final 2 | 25 | 835 | 9 | 44 | 2 | 142.25 s |
| Selftest, base separada | 20 | 672 | 611 | 73 | 2 | 116,17 s |

Las primeras tres filas cuentan tarjetas por consulta. Las posteriores cuentan IDs únicos por pasada. El contador inicial mezclaba el primer barrido de consultas rotadas con novedades. Se separaron ambos conceptos antes de los ciclos de watch.

El límite observado por pasada normal fue de 25 peticiones, incluida la portada. El backfill completó diez páginas de la consulta principal y dos consultas adicionales. Registró 700 descartes inicialmente. La posterior revisión excluyó además un polo de manga corta que se había puntuado y otro anuncio que contenía «geïnspireerde».

En el segundo run final hubo ocho primeras observaciones y una bajada confirmada de 119,99 € a 90 € para el anuncio 10685108670. La distinción se contrastó con price_history.

## Inventario final de la base principal

1914 anuncios, 6275 observaciones de precio y 0 etiquetas manuales.

| Perfil | Top | Good | Maybe | Low | Descartados | Pendientes | Precios |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heron-preston | 0 | 0 | 0 | 0 | 84 | 11 | 380 |
| palm-angels | 1 | 0 | 0 | 0 | 96 | 10 | 306 |
| rhude | 0 | 1 | 0 | 0 | 77 | 20 | 290 |
| stone-island | 0 | 0 | 0 | 0 | 1216 | 6 | 3618 |
| supreme | 3 | 0 | 0 | 0 | 140 | 12 | 731 |
| twojeys | 0 | 0 | 0 | 0 | 86 | 12 | 478 |
| yzy-gap | 1 | 0 | 0 | 0 | 127 | 11 | 472 |

## Mejores anuncios observados

- 100/100 · 25.00 EUR · Certilogo ✓, 222 valoraciones · 5.00, Armario variado, Muy buen estado, Descripción breve, 5 fotos. [Felpa Oversize con Cappuccio Palm Angels Nero Washed – Taglia L](https://www.vinted.es/items/10675297635-felpa-oversize-con-cappuccio-palm-angels-nero-washed-taglia-l)
- 80/100 · 85.00 EUR · 63 valoraciones · 5.00, Armario variado, Muy buen estado, 8 fotos. [Supreme Navy Back logo Hoodie  – Large (L)](https://www.vinted.es/items/10677514167-supreme-navy-back-logo-hoodie-large-l)
- 80/100 · 68.50 EUR · 327 valoraciones · 4.80, Armario variado, Muy buen estado, 8 fotos. [Suprème hoodie size l](https://www.vinted.es/items/10674890952-supreme-hoodie-size-l)
- 75/100 · 50.00 EUR · 73 valoraciones · 4.90, Armario variado, Muy buen estado. [Pull à capuche Suprême](https://www.vinted.es/items/10680953134-pull-a-capuche-supreme)
- 75/100 · 60.00 EUR · 118 valoraciones · 5.00, Armario variado, Nuevo sin etiquetas. [Yeezy X GAP Hoodie](https://www.vinted.es/items/9766029639-yeezy-x-gap-hoodie)

## Verificación y decisiones

- Ruff limpio y 31 pruebas offline en verde. La suite live pasó catálogo, ficha, vendedor y armario. El filtro devolvió cero Stone Island XL y dejó en rojo el test live y doctor.
- La autoprueba completó 8/8 etapas. El comando con informe devolvió salida 1 por su suite live. El servicio en localhost devolvió HTTP 200. Las capturas de 1440 px y 390 px están en `out/board/`.
- Se comprobó que Vinted España incluye vendedores de Italia. Los parámetros repetidos de marca devolvieron 96 tarjetas de Stone Island y Supreme. Los IDs de interfaz 515 y 50 no se usan para filtrar.
- El candidato Stone Island de talla XL, gris y categoría 267 de la prueba dirigida fue descartado por una nota de 4,20 frente al mínimo de 4,50. Se mantuvo el corte antes de descargar fotos.
- Verificación nativa en Windows. Linux queda pendiente de ejecución en ese entorno.

Los incidentes, evidencias y decisiones están en [BLOCKERS.md](BLOCKERS.md), [DECISIONS.md](DECISIONS.md), [WORKLOG.md](WORKLOG.md) y [TEST_REPORT.md](TEST_REPORT.md).

## Siguientes cinco pasos

1. Capturar y comprobar el contrato público de filtros para talla, condición y color. Completar los IDs con evidencia y repetir doctor.
2. Reunir referencias fotográficas permitidas y medir Certilogo y ORB sobre sudaderas Stone Island que superen los gates.
3. Acumular 30 muestras plausibles por marca, añadir etiquetas manuales y calibrar los pesos y el estimador de envío.
4. Repetir el arranque, las pruebas y varios ciclos en Linux para comprobar la portabilidad.
5. En la fase futura, evaluar ntfy y GitHub Actions a través de las interfaces de fuente, estado y notificación.
