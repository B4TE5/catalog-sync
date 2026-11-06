# PLAN.md — vinted-hunter, sesión 1 (local)

Leyenda: `[x]` pendiente · `[x]` hecho (criterio verificado) · `[!]` bloqueado (ver BLOCKERS.md).
Marca cada casilla en este archivo según avances y haz commit.

## Fase 0 — Base
- [x] `git init`, `.gitignore` (data/, out/, .env, *.sqlite, caché, cookies, .venv), `pyproject.toml` con `uv`, paquete `vinted_hunter`, CLI `vh` operativa (`vh --help`).
- [x] `ruff` + `pytest` configurados y en verde (aunque haya 0 tests).
- [x] `DECISIONS.md`, `BLOCKERS.md`, `WORKLOG.md` creados; primera entrada de WORKLOG escrita.
**Hecho cuando:** `uv run vh --help` lista los comandos y `uv run pytest` pasa.

## Fase 1 — Descubrimiento contra Vinted real
- [ ] Cliente `curl_cffi` (impersonate chrome) que obtiene la home de vinted.es con 200 y cookies.
- [ ] Determinar la fuente de datos real de `/catalog` (RSC/JSON embebido/endpoint) → documentado en DECISIONS.md.
- [ ] Parser de catálogo que extrae ≥ 20 anuncios de una búsqueda real ("stone island") con id, título, precio, moneda, url, foto, marca, talla, estado (si viene), id de vendedor.
- [ ] Parser de ficha `/items/<id>`: todas las fotos, descripción, estado, fecha de subida, favoritos, visitas, precio total si existe.
- [ ] Datos de vendedor (valoraciones, nota, nº artículos, país, etc.) por la vía que funcione.
- [ ] `config/vinted_ids.yaml` con todos los IDs de marcas de `profiles.yaml`, tallas L/XL, categorías (con/sin capucha), estados y color gris — cada uno con URL de evidencia. Verificado haciendo una búsqueda filtrada real que devuelve resultados coherentes.
- [ ] Comprobado si vinted.es incluye anuncios de otros países → documentado.
- [ ] Fixtures reales guardados en `tests/fixtures/` + tests del parser en verde.
**Hecho cuando:** `uv run pytest tests/test_parse*.py` pasa con fixtures reales y una búsqueda filtrada en vivo devuelve anuncios de la marca/talla correctas.

## Fase 2 — Captura robusta + dedupe + almacenamiento
- [ ] Búsquedas combinadas por filtros (varios `brand_ids[]`) + búsquedas por texto con prioridad/round-robin, desde `profiles.yaml`.
- [ ] Presupuesto de peticiones, esperas aleatorias, circuit breaker, detección `parser_suspect`, `run_log`.
- [ ] SQLite: listings, sellers, photos (pHash), price_history, run_log, labels, price_stats.
- [ ] Dedupe por ID, detección de resubidas (pHash + vendedor) y de bajadas de precio.
- [ ] `vh run` y `vh backfill` funcionando en vivo.
**Hecho cuando:** dos `vh run` seguidos → el segundo reporta 0 nuevos (salvo anuncios realmente nuevos); tests de dedupe en verde.

## Fase 3 — Gates + enriquecimiento + texto
- [ ] Todos los gates de AGENTS.md §5.2 con razón explícita, configurables.
- [ ] Lógica de capucha (with/without/unconfirmed) con tests.
- [ ] Enriquecimiento (ficha + vendedor + armario) solo para candidatos, con cachés.
- [ ] Módulo de texto multilingüe (motivado, desgaste, prueba de compra, réplica, capucha) con tests.
**Hecho cuando:** un backfill real produce descartes con razones coherentes al revisarlos (anota 10 ejemplos reales en DECISIONS.md con su razón).

## Fase 4 — Visión clásica
- [ ] QR con zxing-cpp + reintentos (×2, CLAHE, teselas) + detector OpenCV de respaldo; clasificación de dominio. Tests con QR generados.
- [ ] pHash: índice, foto compartida entre vendedores, lista negra, fotos de stock. Tests.
- [ ] ORB contra `refs/<brand>/<part>/`; funciona sin refs (devuelve vacío). `refs/README.md` con instrucciones.
- [ ] Ejecutado sobre candidatos reales de Stone Island: anota en DECISIONS.md cuántos tenían QR legible / detectado / ninguno.
**Hecho cuando:** tests de visión en verde y la pasada real no se ralentiza más de ~60 s por candidato.

## Fase 5 — Precio, velocidad y scoring
- [ ] Precio total, estadísticas por marca (mediana, p25, p10), oferta sugerida.
- [ ] `age_minutes`, `heat`, flag hot.
- [ ] Scoring con pesos de `config/scoring.yaml`, tiers, motivos legibles en español.
- [ ] `vh label` (fake → lista negra pHash) y `vh stats`.
**Hecho cuando:** tests de scoring en verde (al menos un caso 🔥 completo y uno ⛔ por cada gate) y `vh stats` muestra datos reales tras un backfill.

## Fase 6 — Tablero + watch + doctor
- [ ] `vh board` genera HTML autocontenido con el diseño de AGENTS.md §6.
- [ ] `vh serve` en localhost:8787; `vh watch` regenera el tablero tras cada pasada.
- [ ] `vh doctor` con comprobaciones verde/rojo.
- [ ] Verificación visual: si Playwright está disponible, captura `out/board/screenshot.png` (escritorio y móvil) y revisa que se ve bien; corrige lo que no.
**Hecho cuando:** tras un backfill real el tablero muestra tarjetas reales con fotos, motivos y botón a Vinted, y `vh doctor` sale en verde.

## Fase 7 — Cierre
- [ ] Logs JSONL, rastro de decisión por anuncio y `vh explain` funcionando (AGENTS.md §8).
- [ ] Tests en vivo `pytest -m live` en verde y `vh selftest` en verde (AGENTS.md §9); `TEST_REPORT.md` generado.
- [ ] README en español completo.
- [ ] `ruff` limpio, `pytest` en verde, último commit hecho.
- [ ] `WORKLOG.md` completo y coherente con el historial de commits.
- [ ] Ejecutar `vh watch` durante al menos 3 ciclos y anotar resultados.
- [ ] `SESSION_REPORT.md`: qué funciona, qué no, cifras reales (peticiones/pasada, tiempo/pasada, vistos, candidatos, distribución por tier y por marca, top 5 anuncios encontrados con enlace y motivos), decisiones importantes, bloqueos, y los 5 siguientes pasos recomendados (incluida la Fase 2: ntfy + GitHub Actions).

## NO hacer en esta sesión
ntfy / notificaciones móviles, GitHub remoto, GitHub Actions, GitHub Pages, Wallapop, modelos de IA/LLM/CLIP. Solo dejar las interfaces preparadas.
