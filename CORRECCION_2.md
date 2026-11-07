# CORRECCION_2.md — recall + limpieza

Mismas reglas de AGENTS.md §0 (autónomo, sin preguntas, WORKLOG al día, commits por tarea, verificación real). Al terminar, push: el bucle de Actions recoge los cambios en su siguiente relevo (o relánzalo de forma controlada si hace falta, sin duplicar bucles).

## Contexto (revisión manual de Carlos)
- **Se nos escapó la joya que buscamos:** https://www.vinted.es/items/10690539539-stone-island-sweater — Stone Island, XL, gris, 60 €, "Muy bueno", crewneck con QR mencionado en la descripción (en neerlandés). Vendida en menos de un día. **Causa probable:** el vendedor la puso en la categoría *Hombre > Ropa > Jerséis y sudaderas > **Jerséis*** (no en Sudaderas), y además la descripción está en neerlandés. Confírmalo con datos (¿la llegamos a ver? ¿en qué gate cayó? ¿o no salió en ninguna búsqueda?) y documéntalo en DECISIONS.md.
- Entre los pendientes sigue habiendo muchísimos zapatos, pantalones y cosas que no son sudaderas (823 pendientes).
- Carlos desactiva Palm Angels y Supreme.

## C2.1 — Perfiles
- [x] `enabled: false` en palm-angels y supreme (y palace sigue en false).

## C2.2 — Estrategia de categoría (arregla las dos cosas a la vez)
- [x] **Todas** las búsquedas (también las de texto) llevan en la URL `catalog_ids` de la categoría padre **Hombre > Ropa > Jerséis y sudaderas** (descubre el ID real y guárdalo en vinted_ids.yaml con evidencia). Así no entran zapatos, pantalones, joyas ni gafas, y sí entran las sudaderas mal puestas en "Jerséis".
- [x] Dentro de esa categoría, que sea sudadera se decide por texto + subcategoría:
  - Subcategorías de sudadera → pasan.
  - Subcategoría "Jerséis" → pasa solo si el título/descripción indica sudadera (sweatshirt, sweater de algodón, crewneck, felpa, sudadera, trui de algodón, sweat…) y NO indica punto (punto, knit, knitted, lana, wool, maglia, maglione, strick, gebreid, cárdigan, cardigan, cuello vuelto/alto…). Si el material de la ficha es lana/punto → descarte `knitwear`.
  - Las demás → descarte `not_sweatshirt`.
- [x] Añade **neerlandés (NL)** y **portugués (PT)** a todas las listas de palabras (tipo de prenda, capucha, punto, réplica, vendedor motivado, desgaste, prueba de compra, QR/Certilogo). Ej. NL: trui, sweater, capuchon, hoodie, gebreid, wol, nieuw, cadeau, past niet, te groot, QR-code, echt, origineel.
- [x] La mención de "QR", "Certilogo", "código de autenticidad" en la descripción (cualquier idioma) suma como señal propia (+10) aunque la visión no lea el QR.
- [x] Purga y re-evalúa la base: todo lo pendiente o aceptado que no sea sudadera según las reglas nuevas → descartado con su razón. Consulta SQL de comprobación antes/después en DECISIONS.md.

## C2.3 — Pendientes bajo control
- [x] Prioridad de enriquecimiento: (1) nuevos de esta pasada, ordenados por perfil prioritario (stone-island primero) y precio relativo al tope; (2) backlog. Sube el presupuesto de enriquecimiento por pasada en la nube si el tiempo de pasada lo permite (objetivo < 5 min por pasada).
- [x] En el tablero, "Todos" no muestra pendientes por defecto; tienen su pestaña.
- [ ] Objetivo medible: tras 3 iteraciones del bucle con las reglas nuevas, pendientes < 100 y 0 no-sudaderas en pendientes (consulta SQL).

## C2.4 — `vh replay <url>` (diagnóstico de anuncios encontrados a mano)
- [x] Comando que, dado un enlace de Vinted, descarga el anuncio (aunque esté vendido), lo pasa por TODO el pipeline como si fuera nuevo (sin guardarlo como visto) y dice: ¿lo habrían encontrado las búsquedas actuales (qué query y por qué sí o no)?, qué gates pasa o falla, señales de visión/texto/vendedor, score y tier final. Salida legible en español.
- [x] Ejecútalo con el anuncio de arriba. **Con las reglas nuevas debe salir como `good` o `top`**; si no, ajusta hasta que salga y explica por qué.

## C2.5 — Batería de recall (que no se vuelva a escapar)
- [x] `tests/recall/`: fixtures reales (ficha completa capturada) de anuncios que DEBEN salir ≥ good. Primer caso: 10690539539. Test que falla si alguno baja de good.
- [x] `tests/precision/`: fixtures reales de cosas que NO deben pasar (zapatos, pantalón, joya, camiseta, jersey de punto Stone Island, foto de catálogo, Palm Angels fake de 28 €). Test que falla si alguno pasa.
- [x] README: cómo añadir un caso a recall/precision con `vh replay <url> --save-fixture recall|precision`.

## C2.6 — Pendientes del mensaje anterior
- [x] Tablero: guardar la clave en localStorage al abrir con `#k=` (try/catch), limpiar el fragmento, descifrar sin fragmento si hay clave guardada, botón "Olvidar clave en este dispositivo", y si la clave guardada no descifra → borrarla y pantalla neutra.
- [x] selftest 8/8: que use candidatos que lleguen a score (o un fixture de recall).

## C2.7 — Verificación final (obligatoria, todo real)
- [x] `ruff`, `pytest` (incluye recall y precision), `pytest -m live`, `vh selftest` 8/8, `vh doctor` en verde.
- [ ] Push y comprobación en Actions de **3 iteraciones del bucle** con el código nuevo: tiempos por pasada, nuevos, descartados por motivo, pendientes. Tablero publicado y abre con la clave.
- [ ] Informe en SESSION_REPORT.md con el embudo de stone-island antes/después y el resultado de `vh replay` del anuncio perdido.
