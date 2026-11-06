# CORRECCION_1.md — precisión (hacer ANTES de PLAN_FASE2.md)

Mismas reglas de AGENTS.md §0. Revisión manual de Carlos sobre el tablero real:
- Entre los pendientes se cuelan muchas prendas que no son sudaderas: Stone Island → camisetas y polos; TwoJeys → pulseras y joyas; Heron Preston → camisetas y pantalones; Rhude y Palm Angels → camisetas y gafas. Además, muchas Supreme fake.
- En el top: Palm Angels a 25 € y 28 € con 100 y 95 puntos. La de 28 € usa como foto una **captura de una tienda online** (fondo blanco + interfaz web "Add to Wishlist") y es fake claro. Ninguna Palm Angels original vale 25–28 €.
- La "mediana" por marca está contaminada (se calcula con joyas, camisetas y fakes) y da porcentajes sin sentido.
- "¿Por qué?" muestra JSON en crudo.

## C1 — Filtro de tipo de prenda (lo más importante)
- [x] Revisa si el `productItem` del catálogo (RSC) trae la categoría (`catalog_id` o similar). Si la trae, gate de categoría **en la fase barata**, antes del enriquecimiento: solo se aceptan las categorías de sudaderas de hombre (con/sin capucha según el perfil) que ya están en `vinted_ids.yaml`.
- [x] Prefiltro por título, multilingüe (ES/EN/FR/IT/DE), configurable en `scoring.yaml`:
  - Tipo positivo: sudadera, hoodie, hoody, sweat, sweatshirt, crewneck, felpa, pull, capuche, kapuzenpullover, sweatjacke, zip hoodie…
  - Tipo negativo (descarte inmediato, razón `not_sweatshirt`): camiseta, t-shirt, tee, polo, camisa, pantalón, jogger, chándal (pantalón), shorts, bermuda, gafas, sunglasses, pulsera, bracelet, collar, necklace, anillo, ring, pendiente, earring, gorra, cap, beanie, gorro, calcetines, bolso, cartera, cinturón, zapatillas, chaqueta, abrigo, chaleco…
  - Sin tipo positivo ni negativo → pasa al enriquecimiento y se decide con la categoría de la ficha.
- [x] En el enriquecimiento: si la ficha da una categoría que no es sudadera → descarte `not_sweatshirt`.
- [x] TwoJeys: quita las búsquedas por texto sueltas ("twojeys", "two jeys"), porque es sobre todo marca de joyería. Usa solo la búsqueda con filtro de marca + categoría, y como texto "twojeys hoodie" / "twojeys sudadera".
- [x] Vuelve a evaluar todos los pendientes y anuncios actuales con estas reglas (re-score sin volver a pedir a Vinted lo que ya está en caché).
**Hecho cuando:** sobre la base actual, 0 joyas, gafas, camisetas, polos o pantalones fuera del tab de descartados (incluye una consulta SQL de comprobación en DECISIONS.md con el recuento antes y después).

## C2 — Suelo de precio por marca + tope de tier
- [x] `price_floor` por perfil (estimaciones iniciales, editables): stone-island 30, twojeys 20, yzy-gap 25, heron-preston 35, supreme 45, rhude 45, palm-angels 60, palace 40.
- [x] Por debajo del suelo:
  - Sin Certilogo legible → descarte `too_cheap_for_brand`.
  - Con Certilogo legible → NO se descarta, pero el tier queda **limitado a "Revisar"** con el flag visible "⚠️ Precio sospechoso: escanea el Certilogo antes de comprar" (los fakes copian códigos reales). Nunca top ni COMPRAR YA.
- [x] "COMPRAR YA" solo si el precio está ≥ suelo y pasa todos los gates de vendedor.
- [x] Supreme: `seller_min_feedback: 20` y `min_photos: 5`.

## C3 — Fotos de catálogo / capturas de tienda
- [x] Heurística de visión clásica `catalog_style_photo`: fondo casi blanco o uniforme en ≥ 60 % del borde, producto centrado y recortado, y/o franjas horizontales uniformes típicas de una interfaz web. Configurable y con tests (genera imágenes sintéticas: foto de producto sobre blanco, captura con barra de UI y foto real de ropa sobre cama/suelo).
- [x] Penalización −20 si alguna foto es de catálogo; **descarte `catalog_photos_only`** si lo son todas o si la primera foto lo es y hay ≤ 3 fotos propias.
- [x] Comprueba con el anuncio real de Palm Angels a 28 € que ahora se detecta (anótalo en DECISIONS.md).

## C4 — Estadísticas de precio limpias
- [x] Mediana/p25/p10 por marca calculadas SOLO con anuncios enriquecidos, con categoría confirmada de sudadera, no descartados y con score ≥ 60. Excluye también los etiquetados como `fake`.
- [x] Con menos de 30 muestras válidas, no muestres "% bajo/sobre la mediana": muestra "Sin datos de mercado suficientes (n=X)".

## C5 — Pendientes ≠ puntuados
- [x] Un anuncio no enriquecido no recibe tier: estado "Pendiente", sin score visible ni recomendación de compra. Solo se puntúa tras el enriquecimiento.

## C6 — "¿Por qué?" legible
- [x] Panel en español:
  - ✅/❌ por cada gate con su nombre legible.
  - Tabla de puntos (señal → puntos → total).
  - Señales de visión (QR, foto de catálogo, foto compartida), vendedor (valoraciones, nota, armario) y texto (frases detectadas).
  - Tiempos (subido hace X, estimado o no).
  - JSON en crudo solo tras un "Ver datos técnicos" plegado.

## C7 — Cierre
- [x] Tests nuevos para C1–C5 en verde, `ruff` limpio, `vh selftest` en verde.
- [x] Re-score de toda la base y nuevo recuento por tier y por marca → DECISIONS.md.
- [x] WORKLOG, TEST_REPORT y SESSION_REPORT actualizados; commit.
