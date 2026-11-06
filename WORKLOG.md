# Bitácora de trabajo

## 2026-11-06 00:28 — Prueba de viabilidad · Entorno

- Objetivo: verificar la carpeta de trabajo y preparar una prueba aislada de acceso a Vinted.
- Hecho: comprobé `C:\dev\vinted-hunter` y su listado inicial (`AGENTS.md`, `PLAN.md`, `profiles.yaml`). Leí `AGENTS.md` como contexto. Creé `scratch/probe.py` y el entorno Python 3.12.10 en `scratch/.venv`.
- Comandos clave: `Get-Location` y `Get-ChildItem -Force` → carpeta y archivos requeridos presentes (salida 0). `python -c "import curl_cffi"` → `ModuleNotFoundError` (salida 1). `uv venv --python 3.12 scratch/.venv` → bloqueo de la caché predeterminada, `Acceso denegado. (os error 5)` (salida 2). Con `UV_CACHE_DIR=scratch/.uv-cache`, la creación del entorno terminó en verde.
- Problemas y cómo se resolvieron: `uv pip install --python scratch/.venv/Scripts/python.exe curl-cffi` falló al conectar a PyPI dentro del sandbox (`os error 10061`, salida 2). Repetí la instalación con acceso de red autorizado y se instaló `curl-cffi==0.17.0` en el entorno de `scratch/` (salida 0).

## 2026-11-06 00:28 — Prueba de viabilidad · Captura y extracción

- Objetivo: obtener la portada y la búsqueda de Stone Island, y extraer al menos 10 anuncios completos del cuerpo recibido.
- Hecho: ejecuté `scratch/probe.py` con una sola sesión `curl_cffi`, `impersonate="chrome"`, sin iniciar sesión y con una pausa aleatoria de 3 a 8 segundos entre peticiones. Guardé los cuerpos HTML completos sin cabeceras. Añadí `--offline` para desarrollar y verificar el extractor sobre la misma captura sin repetir peticiones a Vinted.
- Comandos clave: `scratch/.venv/Scripts/python.exe -X utf8 scratch/probe.py` (captura inicial, salida 0) → `https://www.vinted.es/` HTTP 200, 1.753.631 bytes; `https://www.vinted.es/catalog?search_text=stone%20island&order=newest_first` HTTP 200, 3.677.094 bytes. Ambas respuestas fueron `text/html; charset=utf-8`.
- Comandos clave: `scratch/.venv/Scripts/python.exe -X utf8 scratch/probe.py --offline` → 96 anuncios únicos con ID, título, precio base, moneda y URL (salida 0). Una comprobación local confirmó que los 96 ID coinciden con los enlaces de las tarjetas del HTML y que una página sin payload produce cero resultados.
- Evidencia: `scratch/home.html` (SHA-256 `6bc9132de20f3ede4e8d0df5f920e884a49669dfd1f593cb20b8bea759c88c94`) y `scratch/catalog.html` (SHA-256 `e7a3e6193fad55a1d51b3cd2d23ec68ffec6cf7a5d6c4cd6bd2c658fd82bd3bc`). El catálogo contiene 59 llamadas a `self.__next_f.push`. Al unir los fragmentos RSC, `items.items[].productItem` contiene `id`, `title`, `price.amount`, `price.currencyCode` y `url`. El script convierte la ruta recibida en una URL absoluta.

## 2026-11-06 08:31 — Fase 0 · Base
- Objetivo: arrancar el paquete y verificar el entorno Windows.
- Hecho: inicialicé Git, instalé el entorno Python 3.12, creé el comando inicial y moví el archivo de perfiles a su ubicación prevista.
- Comandos clave: uv sync con acceso a PyPI → 33 paquetes instalados. uv run --offline vh --help → 0. uv run --offline pytest → 1 pasado. uv run --offline ruff check → 0.
- Evidencia: pyproject.toml, uv.lock, tests/test_cli.py y config/profiles.yaml.
- Problemas y cómo se resolvieron: el archivo de perfiles estaba en la raíz. La instalación inicial falló con Host desconocido (os error 11001) para PyPI y se repitió con red autorizada. Ruff encontró cuatro errores en un script de inspección temporal que quedó fuera del árbol versionado.

## 2026-11-06 08:35 — Fase 1 · Catálogo, ficha y vendedor
- Objetivo: verificar las fuentes públicas y convertir capturas reales en pruebas reproducibles.
- Hecho: parsers de catálogo, ficha y usuario/armario. Compresión de cuatro cuerpos reales. Lectura de taxonomía y de initialCatalogState.
- Comandos clave: diagnóstico curl_cffi → home 200 (7 cookies), ficha 200, API vendedor 200, armario 200 y catálogo API 404. uv run --offline pytest → 5 pasados. Ruff → 0.
- Evidencia: tests/fixtures/README.md y config/profiles.yaml. Commit previo 669096b.
- Problemas y cómo se resolvieron: el primer git add falló al crear .git/index.lock con Permission denied. Git se ejecutó con autorización y una identidad local por comando. La prueba con size_ids[] devolvió 96 Stone Island, de los que 9 eran XL. Se investiga el parámetro actual antes de validar la talla. Un error de comillas en el script temporal de inspección se corrigió y el análisis se repitió.

## 2026-11-06 08:55 — Fase 1 · Depuración de fixtures
- Objetivo: excluir credenciales de los cuerpos comprimidos.
- Hecho: un análisis del HTML completo identificó un JWT de telemetría otelToken en cada captura. Sustituí esos valores por REDACTED y mantuve los fragmentos de datos intactos. Se corrigió el commit local de fixtures antes de seguir.
- Comandos clave: búsqueda de JWT por patrón sobre las capturas descomprimidas → cinco valores de telemetría detectados y retirados. No había cabeceras Set-Cookie.
- Evidencia: tests/fixtures/README.md.
- Problemas y cómo se resolvieron: la primera inspección comprobó claves de sesión en el RSC, pero omitió la clave de telemetría. Se añadió la comprobación de JWT al preparar nuevos fixtures.

## 2026-11-06 08:58 — Fase 2 · Captura, SQLite y dedupe
- Objetivo: ejecutar dos pasadas normales y un backfill de diez páginas con límites efectivos.
- Hecho: planificación combinada y round-robin, base SQLite versionada, historial, dedupe y circuito. Dos pasadas normales y un backfill terminaron con salida 0.
- Comandos clave: vh run → 25 peticiones, 1152 tarjetas, 650 nuevos, 152,60 s. Segunda pasada → 25 peticiones, 1152 tarjetas, 339 nuevos, 138,20 s. vh backfill --pages 10 → 25 peticiones, 1152 tarjetas, 11 candidatos, 142,31 s.
- Evidencia: data/logs/run-20261106.jsonl y data/vh.sqlite, ignorados por Git.
- Problemas y cómo se resolvieron: los dos primeros intentos de ejecución terminaron antes de abrir la red porque YAML 1.1 convirtió 1:1 a 61. Se añadió comillas al valor. La segunda pasada normal cubrió búsquedas rotadas nuevas y mezcló descubrimientos con novedades. Se separaron los contadores y se lanzó watch para verificarlo.

## 2026-11-06 08:58 — Fase 3 · Gates y enriquecimiento
- Objetivo: observar descartes reales tras recuperar ficha y vendedor.
- Hecho: gates baratos y detallados, cachés de armario e imágenes, detección de palabras multilingües.
- Comandos clave: vh backfill --pages 10 → 700 descartes (496 por precio, 201 por talla, tres por color). uv run --offline pytest → tests de gates y texto en verde.
- Evidencia: ejemplos en DECISIONS.md, rastro de cada anuncio en SQLite.
- Problemas y cómo se resolvieron: los anuncios de otras categorías podían llegar por búsqueda textual. El gate detallado comprueba la categoría contra la taxonomía observada, y la prioridad reparte la cuota entre perfiles.

## 2026-11-06 08:58 — Fase 4 · Visión
- Objetivo: comprobar QR, pHash y ORB sobre fotos reales.
- Hecho: el backfill evaluó seis fotos de un Stone Island y detectó un QR ilegible. ORB devolvió cero partes sin referencias.
- Comandos clave: vh explain 10678896375 → seis hashes, QR detectado sin lectura. pytest → casos QR legítimo, dominio ajeno, pHash y ORB sin referencias en verde.
- Evidencia: candidato 10678896375, etapa de enriquecimiento y visión de 54,73 s.
- Problemas y cómo se resolvieron: no había fotos de referencia suministradas. Se verificó que la ausencia no interrumpe el embudo y se documentó cómo aportarlas.

## 2026-11-06 08:58 — Fase 5 · Scoring y estadísticas
- Objetivo: comprobar que el backfill genera puntuaciones y estadísticas reales.
- Hecho: cálculo de precio total, edad, calor, oferta y percentiles. El Stone Island 10678896375 marcó 70 puntos, 50 EUR, total estimado 56,69 EUR, oferta 45 EUR y mediana del perfil 50 EUR con una muestra plausible.
- Comandos clave: vh stats y vh explain 10678896375 → salida 0. uv run --offline pytest → 25 pasados. Ruff → 0.
- Evidencia: config/scoring.yaml, tests/test_pipeline.py, SQLite y rastro del anuncio.
- Problemas y cómo se resolvieron: la primera muestra queda por debajo del mínimo de 30 y no activa la señal p25.

## 2026-11-06 09:03 — Fase 6 · Revisión del tablero
- Objetivo: revisar el tablero real en escritorio y móvil.
- Hecho: se comprobó la apertura por file://, 48 tarjetas visibles, enlaces HTTPS y expansión de ¿Por qué?. Se ajustó la altura de tarjetas en una fila y se embebieron fotos reales cacheadas.
- Comandos clave: Playwright Chromium en 1440 y 390 px → dos PNG, sin desbordamiento ni excepciones JavaScript. pytest → 28 pasados. Ruff → 0.
- Evidencia: out/board/screenshot.png, out/board/screenshot-mobile.png y rastro de los anuncios.
- Problemas y cómo se resolvieron: Chromium tardó en arrancar dentro del sandbox y la verificación local se repitió con acceso autorizado. La inspección mostró un polo de categoría 5492 puntuado en la primera iteración y un título neerlandés con geïnspireerde. Se añadió revalidación de registros enriquecidos y se amplió el vocabulario de réplica. Dos intentos de la prueba de regresión dieron hood antes que replica porque la propia entrada mencionaba hoodie; se aisló la señal que debía probarse.

## 2026-11-06 09:13 — Fases 1 y 6 · Confirmación del filtro combinado
- Objetivo: resolver las marcas que faltaban y contrastar los IDs expuestos en la ficha con el filtro público.
- Hecho: ocho marcas con evidencia. Capturas reales de Rhude y del catálogo combinado. Consulta conjunta en doctor y en el diagnóstico independiente.
- Comandos clave: vh doctor → home 200, 96 anuncios parseados y 96 de Stone Island y Supreme con filtros repetidos. Filtro XL → 0. Sondeo de fichas → seis HTTP 200. pytest → 30 pasados, 3 live excluidos.
- Evidencia: config/vinted_ids.yaml, tests/fixtures/catalog-combined.html.gz, tests/fixtures/item-rhude.html.gz y DECISIONS.md.
- Problemas y cómo se resolvieron: las fichas muestran 515 para L y XL, y 50 para cinco estados distintos. Esos IDs de interfaz se separaron de los IDs de filtro. La primera inspección con Chromium recibió 200 pero no halló los cuatro controles por rol. Los intentos con endpoints públicos de filtros devolvieron 404. Un cambio de tipos dejó temporalmente sin dos puntos la firma de Search.query y falló la recolección de pytest. Se corrigió antes de la autoprueba.

## 2026-11-06 09:13 — Fases 6 y 7 · Validación local y extremo a extremo
- Objetivo: comprobar tablero, servicio, latido y tres ciclos consecutivos.
- Hecho: vh serve respondió en loopback. Playwright verificó imágenes cacheadas, enlaces y ancho de pantalla. Watch reconstruyó el tablero tras cada ciclo. Se revalidaron dos falsos positivos guardados y se revisó de nuevo el tablero.
- Comandos clave: GET localhost:8787 → HTTP 200, 5.442.993 bytes. vh watch --interval 0.15 --jitter 0 --cycles 3 → salida 0, 827 / 879 / 837 vistos, 0 / 1 / 1 nuevos. vh selftest --report → 8/8 etapas, 20 peticiones, 116,17 s y dos puntuados. La suite live del informe devolvió 2 pasados y 1 fallo de filtro.
- Evidencia: out/board/index.html, out/board/screenshot.png, out/board/screenshot-mobile.png, TEST_REPORT.md, data/logs/run-20261106.jsonl. Commits de implementación 8a9bb12, a289cb8, 681e41b, bcd25e2 y 9f24124.
- Problemas y cómo se resolvieron: la autoprueba de embudo pasó; el informe agregado y doctor quedaron en salida 1 por la taxonomía. Se registró el bloqueo y se preservó la búsqueda textual. Se separó el SQL de SQLite del embudo para que StateStore cubra el contrato efectivo.

## 2026-11-06 09:21 — Fase 7 · Cierre y contraste de dedupe
- Objetivo: comprobar dos ejecuciones directas finales, inspeccionar los selectores restantes y cerrar los informes.
- Hecho: dos vh run terminaron en verde. El primero puntuó un Rhude y el segundo puntuó dos anuncios, incluido un Palm Angels con QR en dominio Certilogo. Se revalidó un Rhude cuyo título indicaba S aunque Vinted lo presentaba como L. La sudadera gris Stone Island de control se descartó por nota 4,20.
- Comandos clave: vh run → 25 peticiones, 844 vistos, 67 nuevos, 43 candidatos, 151,30 s. Segundo vh run → 25 peticiones, 835 vistos, nueve avisos, 44 candidatos, 142,25 s. Consulta SQLite de price_history → ocho primeras observaciones y una bajada de 119,99 a 90,00. Ruff → salida 0. Pytest → 31 pasados y 3 live excluidos en 2,04 s.
- Evidencia: data/logs/run-20261106.jsonl, data/vh.sqlite, SESSION_REPORT.md, TEST_REPORT.md, out/board/ y commit 937080b. Auditoría Git → ocho blobs de fixtures alcanzables comprobados, sin JWT de telemetría ni datos de ejecución versionados.
- Problemas y cómo se resolvieron: Chromium recibió HTTP 200 del catálogo, pero tampoco halló selectores visibles por identificador. El bloqueo queda documentado. Playwright generó de nuevo las dos capturas con 1.914 anuncios y validó el carrusel y el rastro. Linux queda pendiente de ejecución.

## 2026-11-06 10:05 — Corrección 1 · Tallas
- Objetivo: comprobar los IDs de sudaderas de hombre.
- Hecho: verifiqué 209/210 en RSC y conservé ambas respuestas depuradas. Doctor y la suite live comprueban L y XL.
- Comandos clave: inspección pública con curl_cffi → dos HTTP 200 y 96 tarjetas coherentes cada uno.
- Evidencia: config/vinted_ids.yaml, tests/fixtures/catalog-size-*.html.gz.
- Problemas y cómo se resolvieron: el 515 de la ficha es un ID de interfaz. Se contrastaron dos candidatos con el catálogo y se exigió confirmación del grupo MEN-DE.

## 2026-11-06 10:07 — Corrección 2 · Gates con datos ausentes
- Objetivo: decidir talla, capucha, estado y color con la ficha.
- Hecho: esos gates se aplazan. Una ausencia se registra como no confirmada y no descarta. El parser de ficha deja de heredar talla y estado de la tarjeta. Se reintentan los descartes históricos afectados cuando reaparecen.
- Comandos clave: pytest → 35 pasados; Ruff → salida 0 tras ordenar importaciones.
- Evidencia: tests/test_pipeline.py y fixture público item.html.gz.
- Problemas y cómo se resolvieron: una tarjeta contradictoria podría contaminar la ficha si faltaba el dato; se eliminó esa mezcla.

## 2026-11-06 10:11 — Corrección 3 · Embudo por perfil
- Objetivo: separar vistos únicos, descartes por causa, fichas y tiers.
- Hecho: stats muestra el inventario y la cohorte del último backfill. El registro de pasada conserva cada ID y su resultado. Las señales de tarjeta ordenan la cola sin decidir los cuatro gates de atributos.
- Comandos clave: pytest → 36 pasados. Ruff → salida 0. Backfill real lanzado con 10 páginas.
- Evidencia: vinted_hunter/pipeline/funnel.py, SQLite run_log y prueba de conservación de la cohorte.
- Problemas y cómo se resolvieron: PowerShell rechazó expansión de rutas estilo Bash antes de ejecutar los cambios. Se repitió con rutas explícitas.

## 2026-11-06 10:14 — Corrección 5 · Heat
- Objetivo: verificar que la actividad solo usa favoritos y edad.
- Hecho: documenté la fórmula existente y añadí un test que cambia las visitas sin alterar el resultado.
- Comandos clave: Ruff → salida 0. Pytest → 46 pasados en el conjunto de correcciones.
- Evidencia: tests/test_heat.py y README.md.
- Problemas y cómo se resolvieron: el campo histórico de visitas no interviene en el cálculo y sigue admitido en datos guardados.

## 2026-11-06 10:14 — Corrección 4 · Comando de visión
- Objetivo: auditar las fotos de una muestra sin gates.
- Hecho: vision-check obtiene fichas por marca y categoría, analiza hasta el máximo de fotos configurado y registra QR, pHash, ORB y tiempos por ID. Divide la red en lotes acotados con pausas.
- Comandos clave: vh vision-check --help y pytest → comprobados. Ruff → salida 0 tras ligar las operaciones a cada anuncio con partial.
- Evidencia: vinted_hunter/vision_check.py y tests/test_vision_check.py.
- Problemas y cómo se resolvieron: un QR de texto decodificado cuenta como legible en la muestra y no se convierte en señal Certilogo.
