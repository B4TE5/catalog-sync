# AGENTS.md — vinted-hunter

Eres el ingeniero único de este proyecto. Trabajas en modo **autónomo**: el dueño (Carlos) no está delante y no va a responder preguntas durante la sesión.

## 0. Reglas de trabajo (obligatorias)

1. **No hagas preguntas.** Ante cualquier duda, elige la opción más razonable, aplícala y anótala en `DECISIONS.md` (fecha, decisión, alternativas descartadas, por qué).
2. **No pares** hasta que todas las tareas de `PLAN.md` estén marcadas `[x]` o `[!]` (bloqueada). Si algo te bloquea: márcalo `[!]`, documenta el bloqueo en `BLOCKERS.md` (qué intentaste, error exacto, qué haría falta) y **sigue con la siguiente tarea**.
3. **Nunca inventes datos de Vinted** (IDs de marca, talla, categoría, estado, color, rutas, campos JSON). Todo se descubre contra la web real y se guarda con evidencia (`config/vinted_ids.yaml` + fixtures).
4. **Tests con datos reales.** Los fixtures del parser son respuestas reales capturadas de Vinted (`tests/fixtures/`), no JSON escrito a mano.
5. **Commits pequeños y frecuentes** (`git init` si no existe). Un commit por tarea terminada con tests en verde. Mensajes en inglés, formato `feat:/fix:/test:/chore:`.
6. **Nunca** commitees cookies, tokens, `.env`, la base de datos ni la caché de imágenes. Crea `.gitignore` al inicio.
7. **Respeta a Vinted:** sin login, sin cuenta, ritmo humano, presupuesto de peticiones por pasada (ver §4.3), circuit breaker ante 403/429.
8. Debe funcionar en **Windows 11 (nativo)** y Linux. Usa `pathlib`, nada de `fork`, nada de rutas hardcodeadas.
9. Calidad profesional: tipado, `ruff` limpio, `pytest` en verde, README en español.
10. Al terminar la sesión, escribe `SESSION_REPORT.md` (ver PLAN.md, Fase 7).
11. **Trabaja SOLO dentro de la carpeta del proyecto** (la que contiene este AGENTS.md). No leas, crees ni modifiques nada fuera de ella, salvo instalar dependencias (uv/pip/winget) y su caché.
12. **Bitácora auditable obligatoria — `WORKLOG.md`:** cada paso relevante se añade al final, nunca se reescribe lo anterior. Formato por entrada:
    ```
    ## 2026-11-05 21:14 — Fase 1 · Parser de catálogo
    - Objetivo: …
    - Hecho: … (archivos tocados)
    - Comandos clave: `…` → resultado resumido (código de salida, nº de tests, HTTP status)
    - Evidencia: fixture/ruta/commit <hash>
    - Problemas y cómo se resolvieron: …
    ```
    Incluye también los intentos fallidos (qué probaste y por qué no funcionó): son lo más útil para auditar.

## 1. Qué es esto

Un cazador de gangas **originales** de sudaderas en Vinted. Objetivo: ser de los primeros en ver una prenda buena, original y barata subida por alguien que **se la quiere quitar de encima** (no le cabe, se la regalaron, no la usa, limpia armario), y descartar de forma agresiva fakes, revendedores y basura.

Principios de diseño:
- **Embudo:** recall alto en la captura (búsquedas amplias, con errores ortográficos, sin marca), precisión alta al final (filtros duros + scoring).
- **El silencio debe ser fiable:** distinguir siempre "no hay nada nuevo" de "el parser está roto / me están bloqueando".
- **Todo configurable** en YAML (perfiles, pesos, umbrales, palabras clave). Cero números mágicos en el código.
- **Explicable:** cada anuncio guarda los motivos de su score y de su descarte.

**Fuera de alcance en esta sesión (Fase 2 futura, NO implementar ahora):** notificaciones al móvil (ntfy), GitHub Actions, GitHub Pages, feedback por issues, Wallapop. Pero deja las interfaces preparadas (`Notifier` y `StateStore` abstractos, `Source` abstracto) para enchufarlo después sin refactor.

## 2. Stack

- Python 3.12, gestionado con `uv` (`pyproject.toml`, entry point CLI `vh`).
- HTTP: `curl_cffi` con `impersonate="chrome"` (huella TLS real). Sesión única por pasada; cookies obtenidas visitando la home.
- Modelado/validación: `pydantic` v2.
- Persistencia: SQLite (stdlib `sqlite3`), migraciones simples versionadas.
- CLI: `typer` + `rich`.
- Visión clásica (sin modelos de IA): `zxing-cpp` (QR), `opencv-python-headless` (detección QR de respaldo, ORB, CLAHE), `imagehash` + `Pillow` (pHash).
- Texto: normalización con `unidecode`, matching por palabras clave multilingüe (ES/EN/FR/IT/DE).
- Tests: `pytest`, `qrcode` (para generar QR de prueba). Lint: `ruff`.

## 3. Arquitectura

```
vinted_hunter/
  cli.py                # vh run | watch | backfill | board | serve | label | doctor | stats
  config.py             # carga y valida config/*.yaml (pydantic)
  sources/
    base.py             # Source (abstracto)
    vinted/
      client.py         # sesión curl_cffi, cookies, rate limit, circuit breaker
      catalog.py        # búsqueda → lista de anuncios (parseo validado)
      item.py           # ficha completa del anuncio
      user.py           # datos del vendedor + armario
      parse.py          # extracción RSC/JSON embebido; tolerante a cambios
  pipeline/
    models.py           # Listing, Seller, Evidence, ScoreResult (pydantic)
    dedupe.py           # IDs vistos, resubidas, bajadas de precio
    gates.py            # filtros duros → razón de descarte
    enrich.py           # ficha + vendedor + fotos (solo candidatos)
    vision.py           # QR, pHash, ORB
    text.py             # capucha, fake, desgaste, vendedor motivado
    pricing.py          # precio total, estadísticas por marca, oferta sugerida
    score.py            # scoring con pesos de YAML → tier + motivos
  storage/
    base.py             # StateStore (abstracto)
    sqlite_store.py
  notify/
    base.py             # Notifier (abstracto) — implementación real en Fase 2
    console.py          # notificador de consola (rich) para Fase 1
  board/
    build.py            # genera out/board/index.html (+ data embebida)
    template.html
config/
  profiles.yaml         # búsquedas (lo da Carlos)
  scoring.yaml          # pesos, umbrales, palabras clave (lo creas tú)
  vinted_ids.yaml       # IDs descubiertos contra la web real (lo creas tú)
refs/
  <brand>/<part>/*.jpg  # fotos de referencia para ORB (Carlos las añadirá)
  stock/                # fotos oficiales/catálogo → señal de foto de stock
tests/
  fixtures/             # respuestas reales de Vinted
data/                   # SQLite + caché de imágenes (gitignored)
out/                    # tablero generado (gitignored)
```

## 4. Captura (Vinted)

### 4.1 Descubrimiento (primera tarea técnica)
- Investiga cómo sirve Vinted hoy los resultados de `/catalog`. Según fuentes de 2026, `/api/v2/catalog/items` devuelve 404 a clientes web y los datos van en el payload RSC (React Server Components) embebido en el HTML de `/catalog`. **Compruébalo tú.** Prueba en este orden y documenta qué funciona en `DECISIONS.md`:
  1. Payload RSC / JSON embebido en `https://www.vinted.es/catalog?...`
  2. Cualquier endpoint JSON que la web use realmente (inspecciona el HTML/JS).
  3. Fichas `/items/<id>` (RSC/JSON embebido) para el detalle.
  4. `/api/v2/users/<id>` (con cookies de sesión de la home) para el vendedor.
- Descubre y guarda en `config/vinted_ids.yaml`, con un comentario de evidencia (URL de la que salió): `brand_ids` de cada marca de `profiles.yaml`, `size_ids` (L, XL de ropa de hombre), `catalog_ids` de categorías (sudaderas con capucha / sudaderas sin capucha / categoría padre de sudaderas hombre), `status_ids` (Nuevo con etiquetas, Nuevo sin etiquetas, Muy bueno, Bueno, Satisfactorio), `color_ids` (gris).
- Comprueba si el catálogo de vinted.es muestra anuncios de otros países (FR/IT/DE…). Documenta el resultado.
- Captura fixtures reales (HTML/RSC de catálogo, ficha, usuario) en `tests/fixtures/` (comprímelos si pesan).

### 4.2 Búsquedas
- Orden: más reciente primero. Solo página 1 en modo normal; páginas 1–10 en `vh backfill`.
- **Búsqueda combinada por filtros:** Vinted acepta varios `brand_ids[]` en la misma URL. Agrupa los perfiles que comparten talla+categoría en **una sola petición** (p. ej. todos los "L + con capucha"). Stone Island (XL, sin capucha) va en su propia petición.
- **Búsquedas por texto** (`search_text`) sin filtro de marca, para pillar anuncios mal etiquetados: cada perfil define sus `text_queries`. Prioridad: las de `priority: high` en cada pasada; el resto en **rotación round-robin** para respetar el presupuesto.
- Las búsquedas por texto no filtran por talla en la URL → la talla se comprueba después en el gate.

### 4.3 Presupuesto y robustez
- Presupuesto por pasada (configurable): ≤ 12 peticiones de catálogo + ≤ 12 de enriquecimiento. Espera aleatoria 3–8 s entre peticiones.
- Circuit breaker: ante 403/429 → backoff exponencial y abortar la pasada; registrar incidente. 3 pasadas fallidas seguidas → estado `unhealthy` visible en el tablero y en `vh doctor`.
- **Parser roto ≠ sin resultados:** HTTP 200 + 0 anuncios parseados en una búsqueda que normalmente devuelve resultados → `parser_suspect` (registrar y mostrar). Valida con pydantic; campos desconocidos se toleran, los esenciales (id, título, precio, url, foto) son obligatorios.
- Latido: cada pasada guarda `run_log` (inicio, fin, peticiones, vistos, nuevos, descartados por motivo, candidatos, errores).

## 5. Pipeline

`fetch → normalize → dedupe → gates (baratos) → enrich (solo candidatos) → gates (caros) → vision → score → store → board/console`

### 5.1 Dedupe
- IDs ya vistos → fuera.
- **Resubida:** mismo vendedor + pHash de foto principal ≈ igual (Hamming ≤ 6) + ID nuevo → se trata como visto. **Excepción:** si el precio ha bajado → evento `price_drop` (señal positiva fuerte).
- Seguimiento de precio de anuncios ya vistos que siguen activos cuando aparecen en resultados → registrar bajadas.

### 5.2 Gates (descarte duro, cada uno con razón explícita)
Definidos por perfil en `profiles.yaml` + globales en `scoring.yaml`:
- Precio fuera de `[price_floor, price_max]` del perfil (precio del anuncio).
- Talla distinta de la del perfil.
- Capucha:
  - Perfil `hood: without` → descartar solo si hay evidencia **explícita** de capucha (categoría "con capucha" o palabras clave de capucha).
  - Perfil `hood: with` → descartar solo si hay evidencia explícita de **no** capucha (categoría sin capucha, "crewneck", "cuello redondo", "sin capucha"…).
  - Sin evidencia → pasa con flag `hood_unconfirmed` (penaliza un poco, no descarta).
- Estado no permitido por el perfil.
- Palabras de réplica en título/descripción (`replica`, `1:1`, `aaa`, `inspired`, `no original`, `copia`, `fake`, `rep`… multilingüe, con límites de palabra para evitar falsos positivos).
- Reglas específicas de marca (`brand_rules` del perfil), p. ej. Supreme "box logo" por debajo de X € → descarte.
- Vendedor: valoraciones < mínimo del perfil o nota < mínimo.
- QR decodificado que apunta a un dominio que **no** es `certilogo.com` (o subdominio) → descarte (`fake_certilogo_domain`).
- pHash: misma foto en anuncios de **otro vendedor**, o en la lista negra (`label fake`), → descarte.

### 5.3 Enriquecimiento (solo lo que pasa los gates baratos)
- Ficha completa: todas las fotos (máxima resolución disponible), descripción, estado, fecha de subida, favoritos, visitas, precio total si Vinted lo expone (con protección al comprador).
- Vendedor: nº valoraciones, nota, antigüedad de la cuenta si existe, país/ciudad, última conexión, nº de artículos a la venta, si es profesional.
- Armario del vendedor (primera página basta): proporción de artículos de la misma marca, nº de prendas de la marca a la venta, nº de "nuevo con etiquetas" de marcas fakeables.
- Caché de vendedores 24 h; caché de imágenes en disco por hash de URL; máx. 12 fotos por anuncio.

### 5.4 Visión clásica (sin IA)
- **QR:** `zxing-cpp` sobre cada foto; si no lee: reintentar con escala ×2, gris + CLAHE, y teselas (2×2 y 3×3) porque el QR suele salir pequeño. Si zxing no decodifica, usar `cv2.QRCodeDetector.detect` para saber si **hay** un QR aunque no se lea. Resultados: `certilogo_ok` / `qr_detected_unreadable` / `qr_foreign_domain` / `none`.
- **pHash:** de todas las fotos. Índice global en SQLite. Usos: dedupe de resubidas, foto compartida entre vendedores, lista negra, coincidencia con `refs/stock/` (foto de catálogo → penalización).
- **ORB (presencia de partes):** para cada `refs/<brand>/<part>/*.jpg`, ORB + ratio test de Lowe + homografía RANSAC; parte presente si inliers ≥ umbral configurable. Devuelve `parts_present` (p. ej. `neck_label`, `care_label`, `badge`, `badge_buttons`, `certilogo_tag`). Si no hay refs para la marca, el módulo devuelve vacío sin error. Deja `refs/` creado con un README que explique cómo añadir fotos.

### 5.5 Texto
Normalizar (minúsculas, `unidecode`). Listas de palabras en `scoring.yaml`, multilingües:
- **Vendedor motivado (+):** "no me queda", "me queda grande/pequeña", "talla equivocada", "me la regalaron", "regalo", "puesta una vez/dos veces", "no la uso", "no me la pongo", "limpieza de armario", "vacio armario", "liquido", "mudanza", "urge", "acepto ofertas", "negociable"; EN "doesn't fit", "too big", "too small", "gift", "worn once"; FR "trop grand", "porté une fois", "cadeau"; IT "taglia sbagliata", "indossata una volta", "regalo".
- **Desgaste (−):** "bolitas", "pilling", "desgaste", "manchas", "mancha", "agujero", "descolorida", "desteñida", "roto".
- **Prueba de compra (+):** "ticket", "factura", "comprada en", nombre de tienda oficial, temporada/colección.
- **Descripción vacía o de 1 línea (−).**
- **Capucha / sin capucha:** listas para el gate de §5.2.

### 5.6 Precio
- Precio total = precio + protección al comprador + envío estimado. Usa los valores que exponga Vinted; si estimas, márcalo `estimated: true` y pon la fórmula en `scoring.yaml`.
- **Estadísticas por marca:** guarda TODOS los precios observados por perfil (también descartados, con su tier). Calcula mediana y p25 **de los anuncios con score ≥ umbral de "plausible original"**. Muestra en cada tarjeta "X % bajo la mediana". Cuando haya ≥ 30 muestras por marca, `pricing.ganga_threshold = p25` se usa como señal de score (no sustituye al tope del perfil).
- **Oferta sugerida:**
  - Subido hace < 60 min y precio ≤ p25 (o ≤ 80 % del tope si no hay estadística) → "COMPRAR YA, no ofertes".
  - Subido hace ≥ 5 días o con `price_drop` → oferta sugerida = máx(precio × 0,80, p10 de la marca), redondeada a 5 €.
  - Resto → oferta = precio × 0,90 redondeado.

### 5.7 Señales de velocidad ("ser el primero")
- `age_minutes` desde la subida (de la ficha; si no existe el dato, desde el primer avistamiento y márcalo).
- `heat = favoritos / max(age_minutes, 5)` → si supera umbral, flag 🔥 `hot` (hay competencia, decidir rápido).

### 5.8 Scoring (0–100, pesos en `scoring.yaml`)
Valores por defecto (ajustables):

| Señal | Puntos |
|---|---|
| QR → certilogo.com | +35 |
| QR detectado, no legible | +15 |
| Vendedor ≥ 50 valoraciones y nota ≥ 4,8 | +20 |
| Vendedor 10–49 valoraciones | +10 |
| Armario variado (marca < 20 % del armario) | +5 |
| ≥ 3 prendas de la misma marca a la venta | −25 |
| Muchos "nuevo con etiquetas" de marcas fakeables en el armario | −20 |
| Nuevo sin etiquetas / Muy bueno | +10 |
| Nuevo con etiquetas y precio < 75 % del tope | −20 |
| Bueno | 0 · Satisfactorio −10 |
| Vendedor motivado (texto) | +10 |
| Prueba de compra (texto) | +8 |
| Desgaste (texto) | −15 |
| Descripción vacía | −5 |
| ≥ 5 fotos | +5 |
| Cada parte de autenticación fotografiada (ORB) | +5 (máx +15) |
| Foto de stock detectada | −20 |
| `price_drop` | +10 |
| Precio ≤ p25 de la marca (si hay estadística) | +8 |
| `hood_unconfirmed` | −5 |

Base: 40. Recortar a [0, 100].

Tiers (umbrales en YAML):
- 🔥 `top` ≥ 75 · ✅ `good` 60–74 · 👀 `maybe` 45–59 · ❌ `low` < 45 · ⛔ `rejected` (gate) con razón.

Cada resultado guarda la lista de motivos legibles en español, p. ej. `["Certilogo ✓", "142 valoraciones · 4,9", "se la regalaron", "subida hace 6 min"]`.

## 6. Tablero (Fase 1: local)

`vh board` genera `out/board/index.html` **autocontenido** (datos JSON embebidos en el HTML, sin fetch → funciona abriendo el archivo con doble clic). `vh serve` lo sirve en `http://localhost:8787` y regenera tras cada pasada de `watch`.

Diseño — nivel app nativa, nada de plantilla genérica:
- Tema oscuro, tipografía del sistema, mucho aire, esquinas redondeadas, sin librerías externas (ni CDN). HTML+CSS+JS vanilla.
- Cabecera: latido ("Última pasada hace 4 min · 32 vistos · 1 nuevo"), estado de salud (verde/ámbar/rojo), contador por tier.
- Pestañas/filtros: Todos · 🔥 · ✅ · 👀 · ⛔ Descartados · por marca · ordenar por score / recientes / % bajo mediana.
- Tarjeta: foto grande (carrusel de las fotos), marca + título, **precio** grande y total debajo, tier + score, chips de motivos, "subido hace X min", heat 🔥 si aplica, oferta sugerida, vendedor (valoraciones, nota, país), botón **Abrir en Vinted** (URL https del anuncio).
- Descartados: tarjeta compacta con la razón del gate.
- Responsive (se verá también en el móvil más adelante).

## 7. CLI

- `vh run` — una pasada.
- `vh watch --interval 10 --jitter 2` — bucle (minutos), Ctrl+C limpio, regenera tablero.
- `vh backfill --pages 10` — pasada profunda una vez (marca todo como visto sin "nuevo" para no inundar, pero puntúa y lo muestra en el tablero; los de nivel negociable salen marcados).
- `vh board` / `vh serve`.
- `vh label <listing_id> fake|good|meh` — feedback: `fake` añade sus pHash a la lista negra; todo se guarda para calibrar.
- `vh stats` — por marca: muestras, mediana, p25, distribución de tiers, motivos de descarte más comunes.
- `vh doctor` — comprueba conectividad, cookies, que el parser extrae anuncios de una búsqueda conocida, que los IDs de `vinted_ids.yaml` resuelven, estado de salud. Salida clara verde/rojo.

## 8. Observabilidad del scraper (en ejecución)

- Logs estructurados JSONL en `data/logs/run-YYYYMMDD.jsonl` (rotación diaria, retención 14 días): una línea por evento (`run_start`, `request` con URL sin cookies + status + ms, `parse_result`, `gate_reject` con razón, `candidate`, `score`, `error`, `run_end` con resumen).
- Cada anuncio guarda su **rastro de decisión** completo en SQLite: qué gates pasó/falló, señales de visión, señales de texto, desglose de puntos del score. El tablero lo muestra al pulsar "¿Por qué?" en cada tarjeta.
- `vh explain <listing_id>` imprime ese rastro en consola.
- Nunca se loguean cookies ni cabeceras de sesión.

## 9. Pruebas de funcionamiento

Tres niveles, todos obligatorios:
1. **Unitarios/offline** (`pytest`, por defecto): fixtures reales, sin red. Deben pasar siempre.
2. **En vivo** (`pytest -m live`, marcador `live`, excluido por defecto): contra Vinted real — home 200, búsqueda devuelve ≥ 10 anuncios parseados, ficha parseada, vendedor parseado, IDs de `vinted_ids.yaml` filtran correctamente. Detectan cuando Vinted cambia la web.
3. **Extremo a extremo** `vh selftest`: una pasada real completa y acotada (1 búsqueda por perfil activo, máx. 3 candidatos enriquecidos) → gates → visión → score → tablero, y verifica cada etapa con ✅/❌ y tiempos. Debe terminar en verde antes de cerrar la sesión.

Resultados de los tres niveles → `TEST_REPORT.md` (fecha, comando, salida resumida, nº tests ok/fallidos, duración). Se regenera con `vh selftest --report`.

## 10. Calidad

- Tests mínimos: parser con fixtures reales (catálogo, ficha, usuario); gates (cada razón); capucha (con/sin/indeterminado); texto multilingüe; pricing y oferta sugerida; scoring (casos 🔥 y ⛔ completos); dedupe/resubida/bajada de precio; QR (`qrcode` genera uno a `https://www.certilogo.com/...` → ok, y uno a `https://certilogo-check.com/...` → descarte); pHash (misma imagen reescalada → igual).
- `ruff check` sin errores. Tipado en todo el código público.
- README en español: qué hace, instalación con `uv`, comandos, cómo añadir perfiles/refs, cómo calibrar.
