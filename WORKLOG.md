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

## 2026-11-06 10:14 — Corrección 6 · Auditoría de pruebas
- Objetivo: contrastar la suite con la lista de AGENTS.md §10.
- Hecho: los parsers de catálogo, ficha, vendedor y armario ya tenían capturas reales. Se ampliaron las reglas dependientes de estado, los idiomas, las ofertas normal y por bajada, el dedupe por ID en el pipeline y la reapertura de descartes históricos. Permanecen cubiertos pHash, resubidas, dominios QR y tiers top/rejected.
- Comandos clave: uv run --offline pytest -q → 46 pasados, 4 live excluidos. Ruff → salida 0.
- Evidencia: tests/test_pipeline.py, tests/test_heat.py y tests/test_vision_check.py.
- Problemas y cómo se resolvieron: el test previo de dedupe comprobaba comparaciones y no la transición del pipeline con un ID ya visto; se añadió esa transición con SQLite temporal y una tarjeta real.

## 2026-11-06 10:19 — Corrección 2 · Revalidación histórica
- Objetivo: evitar un descarte por atributos guardados antes de distinguir ficha y catálogo.
- Hecho: la revalidación exige un rastro de ficha para esos cuatro gates y para las reglas de marca condicionadas al estado.
- Comandos clave: Ruff → salida 0. Pytest → 47 pasados, 4 live excluidos.
- Evidencia: test_revalidate_requires_ficha_evidence_for_attribute_rejects.
- Problemas y cómo se resolvieron: en registros previos la talla podía haberse heredado de la tarjeta. La revalidación aplaza el descarte hasta disponer de evidencia confirmada.

## 2026-11-06 10:32 — Correcciones 3 y 7 · Backfill y validación pública
- Objetivo: medir el embudo con datos de Vinted y comprobar el cierre en vivo.
- Hecho: el backfill general guardó 1.022 IDs Stone Island con su motivo o estado. Doctor confirmó las dos tallas. Selftest con informe completó 8/8 etapas y la suite live pasó 4/4.
- Comandos clave: vh backfill --pages 10 → salida 0, 25 peticiones, 1.123 vistos y 147,2 s. vh doctor → salida 0. vh selftest --report → salida 0, 20 peticiones, 112,25 s. pytest -m live incluido en el informe → 4 pasados en 33,33 s.
- Evidencia: DECISIONS.md, TEST_REPORT.md y run_log.
- Problemas y cómo se resolvieron: la primera pasada agotó la cuota de fotos en otro perfil. La cohorte Stone Island conserva cuatro fichas previas y 297 pendientes. Se preparó una segunda medición centrada en Stone Island tras vision-check.

## 2026-11-06 10:41 — Correcciones 3, 4 y 7 · Medición final y cierre
- Objetivo: terminar la muestra de 30 anuncios y comprobar los gates con un backfill focalizado.
- Hecho: vision-check analizó 192 fotos. Hubo 10 QR legibles de Certilogo, 7 detectados sin lectura y 13 sin QR. El backfill focalizado vio 558 Stone Island, cargó 10 fichas nuevas, rechazó 423 por motivos guardados y dejó 135 pendientes.
- Comandos clave: vh vision-check --profile stone-island --limit 30 → salida 0, 242 peticiones en 19 lotes, mediana total 43,97 s y local 0,26 s. Motor de backfill con 2 páginas y Stone Island aislado → salida 0, 21 peticiones y 112,7 s. Ruff → salida 0. Pytest offline final → 47 pasados.
- Evidencia: out/vision-check-stone-island.json, DECISIONS.md, SESSION_REPORT.md y TEST_REPORT.md. El tablero local se regeneró.
- Problemas y cómo se resolvieron: el rango total llegó a 82,53 s por anuncio con pausas y descargas. ORB devolvió cero partes por falta de referencias. El primer intento del script local de informes falló por escapes del texto y se repitió con el comando simplificado. Los IDs opcionales de estado, gris y capucha siguen pendientes.

## 2026-11-06 10:42 — Corrección 3 · Recuperación del resumen focalizado
- Objetivo: contrastar que stats mostrara el último backfill focalizado.
- Hecho: recuperé de run_end el resumen exacto de la pasada focalizada y lo guardé en run_log. Actualicé los informes y el tablero.
- Comandos clave: inspección SQLite y JSONL → 558 vistos del perfil, 423 descartes, 135 pendientes, 12 con ficha y 10 cargadas en esa pasada.
- Evidencia: run_end de 2026-11-06T09:39:17.385776+00:00 y la cohorte persistida.
- Problemas y cómo se resolvieron: el script local lanzó SystemExit dentro del contexto de SQLite. Se guardaron las fichas confirmadas durante la pasada, pero el contexto revirtió el último resumen. Se recuperó el evento original sin repetir peticiones y se movió la salida fuera del contexto.

## 2026-11-06 20:21 — C1–C6 · Precisión y tablero
- Objetivo: depurar tipo de prenda, precio, fotos, mercado y explicación antes de Fase 2.
- Hecho: se inspeccionó el esquema de todos los fixtures de catálogo. El título filtra de forma temprana y la categoría de la ficha confirma la prenda. Se aplicaron los suelos, la heurística visual, el límite de tier y el cálculo de mercado limpio. Pendiente queda sin puntuación ni oferta.
- Comandos clave: vh rescore → 2.164 filas sin red. Consulta SQLite → 121 prendas fuera de perfil antes, 0 después. Chromium local → panel, técnico plegado, pestañas y aviso de mercado verificados. Ruff → 0. Pytest → 57 pasados.
- Evidencia: DECISIONS.md, scratch/correction1-*.json y el anuncio 10685333948, foto principal de catálogo y tier descartado.
- Problemas y cómo se resolvieron: tres tests representaban la política anterior de precio, categoría y compra. Se actualizaron y se añadieron regresiones. Para registros guardados bajo el suelo se exige evidencia cacheada de Certilogo legible.

## 2026-11-06 20:21 — C7 · Cierre de la corrección
- Objetivo: completar y verificar la corrección antes de iniciar Fase 2.
- Hecho: tabla antes/después, informe de pruebas, informe de sesión y plan de corrección actualizados.
- Comandos clave: vh selftest --report → salida 0, 8/8 etapas, 20 peticiones, 115,7 s. Pytest live → 4 pasados.
- Evidencia: TEST_REPORT.md, CORRECCION_1.md, commits 5907c4b y 4f15b3d.
- Problemas y cómo se resolvieron: para evitar contaminar el mercado se excluyeron también las piezas bajo el suelo que solo pasan a Revisar por su QR.

## 2026-11-06 20:27 — F2.0 · Rendimiento
- Objetivo: separar la cadencia de páginas y fotos y dar prioridad a los anuncios frescos.
- Hecho: cuatro trabajadores de CDN sin cookies ni pausa, timeout y un reintento dentro del presupuesto. Los anuncios de la pasada preceden al backlog.
- Comandos clave: vh run → salida 0, 25 peticiones, 884 vistos y 117,3 s. Pytest → 58 pasados.
- Evidencia: tiempos por candidato en DECISIONS.md y run_log.
- Problemas y cómo se resolvieron: las fotos conservan sus posiciones aun cuando falten bytes. Se mantiene el circuit breaker para CDN y páginas.

## 2026-11-06 20:33 — F2.3 · Notificador
- Objetivo: preparar avisos locales y de salud bajo shadow_mode.
- Hecho: envío JSON de ntfy, prioridad, dedupe persistente y transición de incidencia y recuperación. Los avisos de anuncios quedan desactivados por defecto.
- Comandos clave: Ruff → 0. Pytest → 61 pasados, incluidas las pruebas HTTP simuladas.
- Evidencia: tests/test_ntfy.py y vinted_hunter/notify/ntfy.py.
- Problemas y cómo se resolvieron: la deduplicación reclama la transición en SQLite antes del envío. Así se evita repetir avisos ante un resultado de transporte incierto.

## 2026-11-06 20:44 — F2.1 · Puerta de Actions
- Objetivo: verificar acceso desde el runner sin publicar credenciales.
- Hecho: destino público exacto confirmado, historial auditado y tres sondas con 302 s entre despachos.
- Comandos clave: Git push → 0. Dispatch → HTTP 200 tres veces. Runners → 3/3 con HTTP 200 y 96 anuncios.
- Evidencia: runs 42279884459, 42280627200 y 42281374832. Logs descargados por API y contrastados sin coincidencias de secretos.
- Problemas y cómo se resolvieron: el destino local incluía sufijo .git. Se normalizó el formato sin mostrar el valor. La API de administración devolvió 403 y el GET de Pages 404.

## 2026-11-06 20:44 — F2.2 y F2.4 · Estado, panel y feedback
- Objetivo: programar capturas, conservar estado cifrado y admitir etiquetas del dueño.
- Hecho: flujos con SHAs, permisos acotados, instantánea gzip cifrada y force-with-lease, y artefacto de Pages con descifrado WebCrypto. Se añadió latido mensual y validación estricta de feedback.
- Comandos clave: API GitHub secretos → 201 para los tres. Crear Pages → HTTP 403. Ruff → 0. Pytest → 69 pasados. Render local cifrado → 0.
- Evidencia: .github/workflows, tests/test_cloud.py y out/pages/index.html.
- Problemas y cómo se resolvieron: se omitirá el deploy si Pages carece de sitio configurado. El estado y los artefactos de prueba pueden seguir ejecutándose.

## 2026-11-06 20:54 — F2.2–F2.5 · Validación manual y seguridad
- Objetivo: comprobar estado remoto, cifrado, feedback y ausencia de credenciales en los artefactos.
- Hecho: la ejecución manual guardó el estado cifrado en un commit sin padres. El artefacto real contiene solo un HTML neutro cifrado. Los issues 1 y 2 se cerraron y el segundo no cambió el estado. El botón de ntfy elimina query y fragmento de la URL configurada.
- Comandos clave: run manual 42282635097 → verde, 25 peticiones, 938 vistos y 760 nuevos de primera pasada. Feedback → dos HTTP 201 y cierre automático. Notify-test → HTTP 200 en ambos canales. Pytest → 69 pasados.
- Evidencia: logs de Actions vía API, artefacto github-pages y rama state. Sin coincidencias de los valores sensibles buscados.
- Problemas y cómo se resolvieron: Chromium consultó el iframe antes de finalizar el descifrado. La segunda verificación esperó su carga y pasó. Pages sigue en 404 porque la activación respondió 403.

## 2026-11-06 21:27 — F2.5 · Verificación final local
- Objetivo: comprobar el código de Fase 2 con Vinted real y repetir la auditoría local.
- Hecho: Ruff, suite offline, diagnóstico, autoprueba y suite live aprobados. Se comprobó que .env sigue ignorado y sin rastrear y que .git/config no contiene valores sensibles.
- Comandos clave: Ruff → 0. Pytest offline → 69 pasados en 4,63 s. Doctor → HTTP 200 y 95 anuncios en la búsqueda base. Selftest → 8/8 etapas, 15 peticiones y 76,3 s. Pytest live → 4 pasados en 37,89 s.
- Evidencia: TEST_REPORT.md y salida de los comandos de cierre.
- Problemas y cómo se resolvieron: una lectura diagnóstica interpretó el tercer valor del helper API como cabeceras y falló con AttributeError. La consulta corregida confirmó el workflow activo y dos ejecuciones manuales en verde.

## 2026-11-06 21:31 — F2.5 · Cierre de comprobaciones remotas
- Objetivo: contrastar la segunda pasada manual, cerrar la observación del cron y registrar el estado de cada tarea.
- Hecho: segunda restauración cifrada verificada con 963 vistos y 49 nuevos. El estado conserva la etiqueta de prueba y tiene un único commit huérfano. Plan e informes actualizados.
- Comandos clave: API de Actions → HTTP 200, workflow activo y cero eventos programados tras unos 43 minutos. API de Pages → HTTP 404 al cierre.
- Evidencia: ejecución 42285332221, rama de estado y recuentos de price_history en DECISIONS.md.
- Problemas y cómo se resolvieron: cron y publicación quedan marcados como bloqueados. Se verificaron dos pasadas manuales y el artefacto cifrado.

## 2026-11-06 22:26 — F2.2/F2.3 · Reactivación de Pages y enlace de ntfy
- Objetivo: desplegar el tablero cifrado con Pages habilitado y preparar el botón Tablero.
- Hecho: lanzada la ejecución manual 42296435101. Se comparte la URL pública derivada del repositorio entre `vh board-url` y el notificador. `BOARD_URL` conserva prioridad si está configurada.
- Comandos clave: GET Pages → HTTP 200, modo workflow. Consultar la variable de Actions → HTTP 403. Despacho de hunt → HTTP 200. Ruff → 0. Pytest → 71 aprobadas.
- Evidencia: `vinted_hunter/secrets.py`, `vinted_hunter/notify/ntfy.py` y regresiones de URL local y de Actions en `tests/test_ntfy.py`.
- Problemas y cómo se resolvieron: el token de operación local no puede consultar la variable de Actions. Se deriva la URL pública de `GITHUB_REPOSITORY` en el runner, sin permisos adicionales.

## 2026-11-06 22:29 — F2.2/F2.3 · Publicación y aviso comprobados
- Objetivo: comprobar Pages, el enlace privado, el botón Tablero y la independencia del token personal.
- Hecho: se publicó el artefacto 13542332390. Chromium abrió 48 tarjetas desde el enlace privado. Los dos avisos ntfy incluyeron el botón que apunta al panel público. Los cuatro workflows remotos coinciden con Git y ninguno referencia `GH_TOKEN`.
- Comandos clave: `hunt` 42296435101 → verde, 25 peticiones, 889 vistos, 112 nuevos. `deploy-pages` → verde. Pages → HTTP 200. `vh notify-test` → dos HTTP 200. API de runs programados → HTTP 200, total 0.
- Evidencia: jobs y logs del run 42296435101, coincidencia SHA-256 del HTML servido con el artefacto y lectura de las acciones recibidas mediante la API de ntfy.
- Problemas y cómo se resolvieron: el primer intento de QA usó `scratch/.venv` y falló con `ModuleNotFoundError` para Playwright. La repetición con `.venv` aprobó los tres casos.

## 2026-11-07 17:30 — Bucle · Implementación y regresiones
- Objetivo: sustituir la cadencia por cron por un coordinador continuo con relevo automático.
- Hecho: `hunt.yml` incluye coordinador, comprobación por API, concurrencia y pasadas con guardado y Pages. `cloud_loop.py` programa intervalos, continúa tras fallos y solicita relevo con `gh workflow run hunt.yml`. README actualizado.
- Comandos clave: Ruff → salida 0 tras corregir dos líneas demasiado largas en los tests. Pruebas de carreras de inicio, relevo, fallo de pasada y respuesta de dispatch incierta añadidas.
- Evidencia: `.github/workflows/hunt.yml`, `vinted_hunter/cloud_loop.py` y `tests/test_cloud_loop.py`.
- Problemas y cómo se resolvieron: un bloqueo global durante cinco horas impediría feedback. Se conserva el bloqueo del estado para cada pasada y se usa otro para el coordinador.

## 2026-11-07 17:34 — Bucle · Límites y validación inicial
- Objetivo: verificar duración, respuesta ante fallos y salida de un despertar duplicado.
- Hecho: coordinador 42391701686 iniciado con límite de validación de 35 minutos. El despertar 42391821189 terminó en verde con loop, refresh y deploy omitidos. El intervalo y el jitter se configuran en el YAML. Se probaron el límite de 340 minutos y la cancelación de una pasada que agota su tiempo.
- Comandos clave: Ruff → salida 0. Suite offline inicial → 80 pasadas en 25,62 s. Suite focalizada posterior → 24 pasadas en 1,35 s. Suite live → 4 pasadas en 40,75 s.
- Evidencia: runs de Actions, `tests/test_cloud_loop.py` y `scratch/loop-proof.json`.
- Problemas y cómo se resolvieron: la autoprueba pública completó 6/8 etapas en 75 s. Sus tres fichas se descartaron antes de visión y score. Se conserva ese resultado y se repetirá con la siguiente muestra real de catálogo.

## 2026-11-07 17:55 — Bucle · Verificación remota y relevo
- Objetivo: acreditar al menos tres pasadas, sus intervalos, el guardado y la publicación, y el relevo con el token automático.
- Hecho: 3 pasadas en verde en el coordinador 42391701686. Estado cifrado y tablero coincidieron en cada pasada. El sucesor 42393577665 quedó arrancado. El despertar duplicado 42391821189 salió sin captura. Plan, informes y bloqueos actualizados.
- Comandos clave: Snapshot → 3 verdes con restauración, guardado y deploy-pages. Intervalos → 498.57 s, 646.96 s. Ruff → 0. Pytest → 82 pasadas en 4,78 s. Pytest live → 4 pasadas en 40,75 s.
- Evidencia: runs de la tabla de DECISIONS.md, logs del coordinador, referencias de state, HTML de Pages y `scratch/loop-proof.json`.
- Problemas y cómo se resolvieron: el blob de logs del coordinador activo respondió HTTP 404, por lo que se descargó tras su cierre. La autoprueba quedó en 6/8, 7/8 y 7/8 al descartar sus muestras antes de score. Se documenta esa verificación pendiente.

## 2026-11-07 19:07 — C2.1 · Perfiles y auditoría inicial
- Objetivo: aplicar la selección de marcas y explicar el anuncio perdido con datos reales.
- Hecho: Palm Angels y Supreme desactivadas, Palace desactivada. Capturada la ficha 10690539539, vendedor, armario y cinco fotos. Copia del estado remoto conservada en data/correction2-cloud-before.sqlite.
- Comandos clave: ficha, vendedor y catálogo padre → HTTP 200. Base remota → 823 pendientes y anuncio objetivo pendiente sin enriquecer. Ruff → 0. Pytest → 82 pasadas.
- Evidencia: tests/recall/10690539539, tests/fixtures/catalog-parent.html.gz y consultas de SQLite.
- Problemas y cómo se resolvieron: la ficha confirma Jerséis 1811 y Algodón. El vendedor tiene siete valoraciones y nota 4,0. Se ajusta el mínimo de Stone Island a 4,0 para el recall solicitado y se mantiene la nota visible.

## 2026-11-07 19:26 — C2.2/C2.4/C2.5 · Categoría, replay y batería real
- Objetivo: recuperar la sudadera de Jerséis y comprobar la precisión con capturas reales.
- Hecho: consultas por la categoría padre 79, material parseado, filtro de punto, palabras NL/PT y señal textual de autenticación de +10. `vh replay` conserva el estado principal y permite guardar casos. Dos casos de recall y seis fichas de precisión, con una comprobación adicional de la captura de tienda real.
- Comandos clave: replay de 10690539539 → salida 0, good, 65 puntos. Ruff → 0. Pytest → 99 pasadas. Purga local → 602 a 446 pendientes y 48 a 0 prendas incompatibles. Purga sobre copia de nube → 823 a 357 y 61 a 0.
- Evidencia: tests/recall, tests/precision y tests/fixtures/catalog-parent.html.gz. La captura de Palm Angels comprueba tanto el descarte de 28 EUR como la foto de tienda.
- Problemas y cómo se resolvieron: el primer replay falló al cerrar su directorio temporal por un SQLite abierto en Windows. Se cerraron las conexiones de copia y la repetición aprobó. Rhude 10653233816 es una foto sobre manta, por lo que se movió de la muestra de precisión a recall.

## 2026-11-07 19:31 — C2.3 · Cola y limpieza acotada
- Objetivo: atender nuevos y backlog sin perder la cadencia ni el estado de Actions.
- Hecho: nuevos primero, prioridad Stone Island y precio relativo. El backlog se procesa aunque no reaparezca en catálogo. Cuota cloud de 72 peticiones de enriquecimiento, incluidas fotos, con fin de selección a 225 s y objetivo de pasada bajo 5 min. Añadido `vh run --pending-only` para la limpieza.
- Comandos clave: Ruff → 0. Pytest → 101 pasadas, incluidas prioridad por perfil y entrada del backlog ausente del catálogo. Chromium → Todos excluye pendientes y su pestaña los muestra.
- Evidencia: tests/test_recall_rules.py, pipeline/run.py y el input pending_only del workflow.
- Problemas y cómo se resolvieron: el estado antiguo necesitaba confirmar cientos de tallas en ficha. Las pasadas de limpieza usan el mismo bloqueo, guardado y Pages que las normales. Las fichas con HTTP 404 quedan como no disponibles.

## 2026-11-07 19:32 — C2.6 · Clave persistente y autoprueba
- Objetivo: abrir el tablero sin reenviar el fragmento y completar las ocho etapas de verificación.
- Hecho: clave en localStorage con try/catch, fragmento borrado, reapertura, botón para olvidar y limpieza de clave inválida. Selftest dispone de fallback con un caso real de recall que también se guarda en su tablero temporal. URLs de captura normalizadas con el canonical real de la ficha. README y diagnóstico actualizados.
- Comandos clave: Chromium → todos los casos aprobados, incluido almacenamiento bloqueado. Doctor → salida 0 y catálogo HTTP 200 con 96 anuncios. Live → 4 pasadas en 37,45 s. Selftest → salida 0, 8/8, 17 peticiones y 76,0 s, con un score de la muestra en vivo.
- Evidencia: encrypted.html, selftest.py y capturas reales de recall. El fallback no fue necesario en esta ejecución en vivo.
- Problemas y cómo se resolvieron: la primera QA comprobó el borrado antes de finalizar el descifrado de la clave inválida. Se añadió espera explícita a localStorage vacío y pasó. La primera ejecución sin elevación quedó esperando al navegador y se repitió con el entorno autorizado.

## 2026-11-07 19:38 — C2.4 · Explicación de replay
- Objetivo: hacer legible el diagnóstico sin cambiar su resultado ni el estado principal.
- Hecho: nombres de gates en español, señales de texto, cantidad de pHash, partes ORB y resumen de armario. Las consultas incompatibles detallan si falla el texto, la talla o la categoría.
- Comandos clave: Ruff → 0. Pruebas focalizadas de CLI, recall y precisión → 20 pasadas en 4,04 s.
- Evidencia: cli.py y replay.py.
- Problemas y cómo se resolvieron: la primera salida conservaba claves internas en inglés. Se tradujeron manteniendo los códigos en el rastro persistido.

## 2026-11-07 19:45 — C2.3/C2.7 · Primer checkpoint real y contadores
- Objetivo: medir pendientes y descartes de cada pasada desde el estado publicado.
- Hecho: limpieza 42401964117 en verde, Pages actualizado, 319 pendientes y 0 incompatibles conocidos. Se añade el total y el desglose de pendientes por perfil a cada run_log y el total a consola. QA del tablero público aprobada.
- Comandos clave: limpieza → 226,47 s, 34 fichas enriquecidas y 36 peticiones de enriquecimiento. Ruff → 0. Pytest → 101 pasadas en 7,70 s.
- Evidencia: scratch/correction2-actions.json y el checkpoint cifrado correspondiente. Descartes de la limpieza, 10 por talla, 16 por prenda, 5 por punto, 2 por ficha no disponible, 1 por capucha y 2 por color.
- Problemas y cómo se resolvieron: los contadores históricos de pendientes no estaban en run_log. Se guardan ahora al cerrar la pasada para poder cotejar las tres iteraciones sin inferir estados intermedios.

## 2026-11-07 19:58 — C2.2 · Recuperación de fichas antiguas sin material
- Objetivo: evitar que el caché anterior mantenga descartadas sudaderas de algodón mal categorizadas.
- Hecho: se localizaron 45 fichas de Jerséis sin material en la instantánea original de nube y una en la base local. Las que se descartaron por prenda vuelven a pendientes para obtener una ficha actual. El gate barato difiere esa decisión cuando falta material. La revisión de reglas pasa a correction-2.1.
- Comandos clave: consulta SQLite sobre categoría 1811 y material NULL → 45 y 1 filas. Ruff → 0. Pytest → 102 pasadas en 8,34 s.
- Evidencia: tests/test_recall_rules.py, rescore.py y gates.py.
- Problemas y cómo se resolvieron: el modelo anterior no almacenaba material. Mantener su descarte impediría aplicar la regla nueva de algodón aunque el catálogo ampliado volviera a mostrar el anuncio.

## 2026-11-07 20:12 — C2.3/C2.7 · Confirmación del tipo pendiente
- Objetivo: acreditar el tipo de los pendientes con datos de ficha, además del filtro textual.
- Hecho: se cuenta pending_unconfirmed al cerrar cada pasada. La limpieza exige que los pendientes restantes ya estén enriquecidos antes de terminar, con menos de 35 como margen de validación. Los nuevos motivos de punto, perfil desactivado y ficha no disponible tienen etiquetas legibles en el tablero.
- Comandos clave: Ruff → 0. Pytest → 102 pasadas en 8,25 s.
- Evidencia: run_log y los monitores de Actions.
- Problemas y cómo se resolvieron: cero incompatibles textuales no acredita el tipo de una ficha nunca descargada. Se separa ese contador para verificar también los pendientes sin ficha.

## 2026-11-07 20:25 — C2.5 · Redacción de telemetría en las capturas
- Objetivo: aplicar a las capturas nuevas la misma anonimización que a los fixtures anteriores.
- Hecho: se redactaron doce JWT públicos de telemetría en cuerpos HTML y se añadió la redacción a replay. Se conserva el contenido de catálogo, ficha, vendedor y fotos que usa el pipeline. Guardia de tests para todos los gzip.
- Comandos clave: auditoría descomprimida → sin coincidencias de GH_TOKEN, BOARD_KEY ni topics configurados. Ruff → 0. Pytest → 103 pasadas en 8,22 s.
- Evidencia: fixtures actuales y test_captured_fixtures_exclude_telemetry_jwt. Los JWT de las revisiones anteriores vencieron como máximo a las 19:40:23 del 7 de noviembre, hora de Madrid.
- Problemas y cómo se resolvieron: guardé las primeras capturas sin aplicar la redacción de otelToken. Se corrigieron las capturas y el comando de captura. Las versiones previas permanecen en el historial auditable y contienen únicamente esos JWT públicos ya vencidos.

## 2026-11-07 20:38 — C2.6/C2.7 · Diagnóstico de perfiles activos y latido de limpieza
- Objetivo: que el diagnóstico y el tablero describan la configuración y la pasada reales.
- Hecho: doctor comprueba las marcas activas combinadas en vez de exigir Supreme desactivada. El latido distingue la limpieza de fichas de una captura de catálogo. Se documenta la procedencia de la taxonomía y de los casos reales.
- Comandos clave: doctor real → salida 0, HTTP 200, 96 anuncios parseados y filtros L/XL válidos. Ruff → 0. Pruebas focalizadas de CLI y reglas → 12 pasadas en 1,41 s.
- Evidencia: diagnostics.py, board/template.html y tests/fixtures/README.md.
- Problemas y cómo se resolvieron: un latido de limpieza mostraba cero vistos aunque estuviera procesando fichas. Ahora muestra fichas enriquecidas y pendientes. La explicación histórica del anuncio distingue el hecho de haberlo visto de la inferencia sobre su consulta de origen.

## 2026-11-07 20:46 — C2.2 · Colisión de «lã» con el artículo «la»
- Objetivo: evitar falsos descartes al incorporar portugués sin perder la detección de lana.
- Hecho: auditoría real de 185 descartes knitwear detectó 65 con «lã» como única coincidencia tras quitar tildes. Se separa knitwear_exact, con comparación Unicode NFC que conserva la tilde. La revisión correction-2.2 reevaluará el estado automáticamente. El rastro usa la misma comparación.
- Comandos clave: Ruff → 0. Pytest → 106 pasadas, 4 excluidas, en 8,40 s; casos «la vendo», «LÃ», material Lã y tilde descompuesta aprobados.
- Evidencia: pipeline/text.py, gates.py, run.py, scoring.yaml y tests/test_recall_rules.py; auditoría sobre la instantánea real data/loop-proof.sqlite.
- Problemas y cómo se resolvieron: la transliteración general confundía una palabra portuguesa con un artículo de otros idiomas. Las demás listas conservan la búsqueda sin tildes. Un comando de inspección anterior intentó llamar a close en SQLiteStore; la consulta se había completado y se corrigió usando su conexión/context manager. No cambió datos.

## 2026-11-07 20:51 — C2.7 · Pruebas reales con las reglas finales
- Objetivo: repetir los tres niveles y el diagnóstico después de corregir la colisión de tildes.
- Hecho: suite offline completa, suite live, selftest y doctor aprobados con correction-2.2; BLOCKERS y TEST_REPORT reflejan la resolución de la autoprueba.
- Comandos clave: Ruff → 0; pytest → 106 pasadas y 4 excluidas en 8,40 s; live → 4 pasadas y 106 excluidas en 39,86 s; selftest → salida 0, 8/8, 75,0 s y 13 peticiones; doctor → salida 0, HTTP 200 y filtros L/XL válidos.
- Evidencia: data/correction2-release-checks.log y TEST_REPORT.md. La autoprueba usó catálogo y tres fichas en vivo; al descartarse las tres, verificó visión/score con el caso real de recall 10653233816 (good 70), indicando el fallback.
- Problemas y cómo se resolvieron: la muestra de tres anuncios no garantiza uno puntuable. Se conserva la comprobación real del descarte y se usa el caso capturado permitido, sin sustituir la fase live.

## 2026-11-07 20:54 — C2.3/C2.4/C2.6 · Replay final y décima limpieza
- Objetivo: acreditar el anuncio prioritario y el comportamiento del tablero publicado mientras progresa la cola real.
- Hecho: replay real repetido con correction-2.2 → good 65; las diez primeras limpiezas de Actions terminaron en verde. El último estado dejó 52 pendientes, todavía con revisión 2.1. La limpieza 11 y la siguiente captura tomarán las reglas 2.2 y reevaluarán los falsos negativos.
- Comandos clave: replay → salida 0; Chromium sobre Pages → salida 0, Todos/Pendientes, clave persistente, fragmento limpio, olvidar, clave inválida y almacenamiento bloqueado aprobados. Limpieza 42407702784 → 232,43 s, 52 pendientes, 0 incompatibles conocidos y sin errores.
- Evidencia: data/correction2-replay-final.log, scratch/correction2-actions.json, run 42407702784 y QA del sitio público.
- Problemas y cómo se resolvieron: la primera QA nueva comparaba el total de pendientes con solo las 48 tarjetas de la primera página. Se recorrió el botón de paginación antes de comparar. El producto funcionaba correctamente.

## 2026-11-07 21:03 — C2.3/C2.7 · Migración final en la nube
- Objetivo: reevaluar los falsos negativos y medir la cola con las reglas definitivas.
- Hecho: Snapshot normal 42408130027 aplicó correction-2.2, guardó estado cifrado y publicó Pages. Quedaron 131 pendientes tras reabrir decisiones antiguas. La limpieza 11 redujo a 92, con 0 incompatibles conocidos; continúa la confirmación de fichas.
- Comandos clave: normal → success, 826 vistos, 9 nuevos, 226,69 s; limpieza 42408403346 → success, 225,85 s, 20 not_sweatshirt, 18 listing_unavailable y 1 size. Sin incidentes en ambas.
- Evidencia: scratch/correction2-actions.json, scratch/correction2-validation.json y los runs de Actions.
- Problemas y cómo se resolvieron: una reducción de pendientes anterior a corregir falsos negativos no basta. La acreditación final exige tres índices consecutivos, correction-2.2, cero fichas pendientes sin confirmar y comienzos separados 8–12 minutos.

## 2026-11-07 21:22 — C2.2/C2.3 · Cola confirmada y limpieza terminada
- Objetivo: terminar el enriquecimiento de la cola sin ocultar prendas desconocidas.
- Hecho: catorce limpiezas reales completadas en verde, cada una con restauración, guardado, cifrado y Pages. La última 42410212943 deja 0 pendientes, 0 incompatibles pendientes/aceptados y 0 fichas pendientes sin confirmar. El coordinador continúa activo y la observación de tres pasadas normales sigue abierta.
- Comandos clave: última limpieza → success, 45,04 s, 7 descartes por talla y 2 por prenda. Auditoría del conjunto → 14 success y todos los pasos persistidos/publicados, sin coincidencias de secretos; máximo observado de limpieza 232,43 s.
- Evidencia: scratch/correction2-actions.json y SQLite real data/loop-proof.sqlite. La cohorte original de 1.368 Stone Island conserva todos sus IDs, 321 enriquecidos, 1 good (10690539539, 65 puntos) y 1.367 rechazados con razón.
- Problemas y cómo se resolvieron: la migración final reabrió falsos negativos y fichas antiguas sin material; se confirmaron con Vinted real. No se cambió el ritmo humano ni se detuvo el coordinador. Se aclara en la documentación que los casos rechazados antes de consultar vendedor/fotos solo guardan la ficha realmente consultada.

## 2026-11-08 01:19 — C2.3/C2.7 · Reanudación tras el corte
- Objetivo: revisar el punto exacto del corte, resolver cambios parciales y continuar por la primera casilla pendiente.
- Hecho: git status solo mostró un borrador provisional de SESSION_REPORT. Se descartó ese borrador desactualizado para regenerarlo con el cierre real. El código ya estaba comprometido; no había implementaciones parciales. El monitor terminó durante el corte y guardó tres iteraciones normales consecutivas con 0 pendientes y 0 fichas sin confirmar.
- Comandos clave: Ruff → 0; pytest → 106 pasadas, 4 excluidas, 8,26 s. Monitor → salida 0; runs 42410718931, 42411565308 y 42412300711, intervalos de captura 632 y 563 s, todos success con restauración/guardado/cifrado/Pages.
- Evidencia: scratch/correction2-validation.json y log final de la sesión nativa del monitor. .env sigue ignorado y git ls-files no lo muestra.
- Problemas y cómo se resolvieron: el informe parcial conservaba cifras anteriores a la limpieza completa; se sustituirá por el informe final. Se verificará además el estado operativo actual tras varias horas de funcionamiento autónomo.


## 2026-11-08 01:25 — C2.3/C2.7 · Cierre real y estado confirmado
- Objetivo: cerrar la cola, acreditar tres iteraciones y conservar informes reproducibles.
- Hecho: 0 pendientes, 0 incompatibles pendientes/aceptados y 0 fichas pendientes sin confirmar. Base local sincronizada con la nube validada y ensayo local anterior archivado íntegro. Todos los checks de CORRECCION_2 completados; informes actualizados.
- Comandos clave: tres Snapshots success 42427270371, 42428059280, 42428917006; duraciones 77.36, 88.22, 89.66 s; intervalos 641 y 671 s. SQL antes/después y descifrado real de Pages aprobados.
- Evidencia: evidence/correction2-validation.json, SESSION_REPORT, TEST_REPORT, DECISIONS y commit de estado 7d39031ce6225737cccb75943cc52acce7815c13.
- Problemas y cómo se resolvieron: las nuevas fichas y la recuperación de falsos negativos hicieron crecer temporalmente la cola; las limpiezas acotadas la confirmaron sin detener el coordinador. La instantánea local anterior se conserva en data/vh-local-correction2-archive.sqlite para evitar perder su histórico exclusivo.

## 2026-11-08 01:27 — C2.7 · Pruebas finales, auditoría y entrega
- Objetivo: cerrar con verificación actual tras la reanudación y preparar commit/push de todos los informes.
- Hecho: nuevas pruebas en vivo y replay sobre la base local sincronizada en verde. Informe de sesión regenerado, TEST_REPORT actualizado, BLOCKERS resuelto y CORRECCION_2 completamente marcado. Evidencia compacta real de las tres iteraciones recientes y catorce limpiezas incorporada al repositorio.
- Comandos clave: Ruff → 0; offline → 106 pasadas, 4 excluidas, 8,26 s; live → 4 pasadas, 106 excluidas, 35,46 s; selftest → salida 0, 8/8, 67,3 s y 13 peticiones; doctor → salida 0; replay real → salida 0, good 65. Chromium público → salida 0 en todos los casos de clave/filtros. Auditoría de credenciales y git diff --check → salida 0.
- Evidencia: data/correction2-resume-checks.log, evidence/correction2-validation.json e informes finales. La base sincronizada conserva una etiqueta de nube y pasa integrity_check; el ensayo local anterior queda íntegro archivado.
- Problemas y cómo se resolvieron: las tres fichas live de selftest se descartaron; completó visión/score con el caso real de recall 10653233816, good 70, identificado en la salida. Las capturas actuales están redactadas y libres de JWT; los JWT públicos caducados del historial anterior siguen documentados. .env permanece ignorado y fuera del índice; sus valores no aparecen en informes, evidencia, fixtures, remote ni configuración Git.

## 2026-11-08 02:25 — C3.0 · Inicio y política de captura
- Objetivo: ejecutar CORRECCION_3 y verificar primero sus prioridades sin activar avisos prematuramente.
- Hecho: leídos AGENTS y CORRECCION_3; estado limpio salvo el nuevo documento de instrucciones. .env ignorado y fuera del índice. Se añadieron tests del límite inclusivo de 60 EUR independiente de comisiones y de los tres estados permitidos en todos los perfiles activos.
- Comandos clave: Ruff → 0; pytest → 108 aprobadas, 4 excluidas, 8,30 s. Captura real de home/catálogo/ficha vendida/ficha activa → HTTP 200; catálogo 96/96 tallas conocidas. SQL local inicial → 3.210 anuncios, 75 sin talla, todos descartados.
- Evidencia: tests/test_c3_policy.py, data/c3-probes y ficha 10690539539. Su can_buy es false y el HTML visible dice Vendido; la ficha activa tiene can_buy true y botón item-buy-button.
- Problemas y cómo se resolvieron: el primer comando SQL inline falló por comillas de PowerShell, sin modificar datos. Se usó un script de inspección. Los avisos se activarán tras implementar la comprobación de disponibilidad. La talla ya se parseaba del secondLine real; se auditará su conservación y presentación.

## 2026-11-08 02:28 — C3.7 · Capturas saneadas y scripts fuera de Git
- Objetivo: exigir la anonimización antes de persistir fixtures y dejar los scripts de investigación en local.
- Hecho: sanitize_fixture procesa JSON y cadenas RSC, redacta JWT, valores opacos de token, cookies anidadas, cabeceras de sesión y parámetros sensibles de URL. replay usa ese punto único. scratch completo queda ignorado; probe.py se conserva localmente pero sale del índice.
- Comandos clave: Ruff → 0; pytest → 110 aprobadas, 4 excluidas, 8,49 s. Un catálogo real conserva exactamente todos los anuncios/campos tras el saneado. Tests de cabeceras y cookies anidadas dentro de RSC aprobados.
- Evidencia: sanitize.py, tests/test_sanitize.py y .gitignore.
- Problemas y cómo se resolvieron: Ruff detectó imports sobrantes al extraer el sanitizador; se corrigieron. Se reforzó el primer patrón para redactar también cookies representadas como arrays/objetos, no solo strings. El CI de gitleaks se implementará como la siguiente parte de seguridad.

## 2026-11-08 02:32 — C3.9 · Reglas de producto por perfil
- Objetivo: permitir futuros productos mediante YAML conservando los casos actuales de sudaderas.
- Hecho: categorías de búsqueda/aceptación/condicionales/exclusión y palabras de tipo/material trasladadas a defaults de profiles.yaml. Gates, búsquedas, replay, precios y rescore usan cada perfil. Talla y capucha pueden ser null para un futuro perfil que no las necesite. No se añadió ningún perfil activo ni producto.
- Comandos clave: Ruff → 0; pytest → 111 aprobadas, 4 excluidas, 10,74 s, incluidos todos los casos reales de recall/precision. Un caso real de precisión comprueba que la misma ficha puede evaluarse con reglas de tipo distintas por configuración, sin cambiar el código ni guardar un perfil nuevo.
- Evidencia: config.py, profiles.yaml, scoring.yaml, search.py, gates.py y tests/test_c3_policy.py.
- Problemas y cómo se resolvieron: Ruff detectó dos líneas largas al refactorizar; se ajustaron. Las listas se trasladaron conservando todos sus valores, incluidas las exclusiones de material y la tilde de lã.

## 2026-11-08 02:33 — C3.7 · Gitleaks con archivos comprimidos
- Objetivo: escanear el historial en cada push sin licencias ni tokens personales de Actions.
- Hecho: workflow de Gitleaks CLI 8.30.1, binario Linux fijado por SHA-256 oficial, checkout completo y análisis de archivos comprimidos con profundidad 2. La descarga local Windows también se verificó por SHA-256.
- Comandos clave: primer escaneo real → salida 1, exactamente los doce JWT públicos de telemetría ya caducados del commit fbac8cb. Tras registrar exclusivamente sus doce fingerprints históricos → salida 0, 52 commits y 69,88 MB. Guardia stdin con un JWT real fuera de esa huella → salida 1 esperada. Valores siempre redactados.
- Evidencia: .github/workflows/secrets.yml, .gitleaksignore y reportes redactados en data/c3-gitleaks-*.json. Ruff y 111 pruebas aprobadas en la revisión base. La ejecución de CI se verificará tras el push.
- Problemas y cómo se resolvieron: el historial conservaba el incidente ya documentado. No se excluyeron rutas ni reglas completas: la excepción fija commit, ruta, regla y línea; una reintroducción en otro commit sigue fallando. Se descartó reescribir el historial auditable.

## 2026-11-08 02:48 — C3.7 · CI de secretos verificado
- Objetivo: comprobar el escáner real de Actions, no solo su YAML o ejecución local.
- Hecho: Secrets run 42434802591 completó success sobre a77a051, con análisis completo y de gzip. El workflow se ejecuta en cada push y pull request sin token personal.
- Comandos clave: API Actions → HTTP 200, completed/success. Guardia de reintroducción real → salida 1 esperada. Suite local de la base funcional → 116 aprobadas y 4 excluidas en 10,09 s.
- Evidencia: .github/workflows/secrets.yml y run 42434802591.
- Problemas y cómo se resolvieron: se conservan únicamente las doce excepciones históricas auditadas; no se permite omitir fixtures comprimidos del escaneo.

## 2026-11-08 03:31 — C3.2 · Auditoría real de las 75 tallas
- Objetivo: recuperar tallas visibles y distinguir ausencia real de dato pendiente.
- Hecho: 75 fichas comprobadas con el cliente real, en ocho pasadas locales de máximo 10 fichas. Se recuperaron 40 tallas; 32 fichas no publican talla y tres devuelven 404. Cero casos sin comprobar. size y size_familiar se leen de la ficha; el catálogo usa itemBox.secondLine y accessibilityLabel como respaldo. Las tarjetas muestran talla incluso en descartados.
- Comandos clave: SQL antes → 75 sin talla y 75 sin comprobar; después → 35 sin talla, de ellas 32 ausentes y 3 no disponibles, 0 sin comprobar. Ningún descarte por talla tenía el valor ausente. 83 peticiones incluidas ocho portadas, con pausas y cuotas, sin incidentes.
- Evidencia: scratch/c3-size-repair.json; fixtures reales c3/item-size-10705167057.html.gz (M) y 10706690299 (S); config/vinted_ids.yaml.
- Problemas y cómo se resolvieron: la ficha usaba size_familiar y la lectura anterior borraba la talla previa del catálogo. Se acepta el código real alternativo y se conserva el valor conocido cuando la ficha no lo expone. Falta cotejar la persistencia y UI finales en Actions.

## 2026-11-08 03:31 — C3.3/C3.5 · Disponibilidad y feedback persistidos
- Objetivo: conservar transiciones de estado y hacer efectivo el feedback en otros anuncios del vendedor.
- Hecho: migración SQLite 2 con eventos de disponibilidad/etiqueta; estados activo, vendido, reservado, oculto y borrado. Sold requiere banner visible, reservado/oculto flags reales; no se deduce vendido de can_buy=false. Fake bloquea vendedor y fotos; meh lo revierte y good suma confianza de 10 puntos. Los precios de vendidos son los anunciados observados; los intervalos de venta se estiman entre comprobaciones, sin inventar hora ni precio pagado.
- Comandos clave: suite completa → 126 aprobadas y 4 excluidas en 13,75 s. Fixtures activos/vendidos y atributos alternativos reales aprobados; tests de eventos, blacklist/reversión/confianza, límites diarios y regresión local aprobados.
- Evidencia: tests/fixtures/c3, tests/test_availability_feedback.py y tests/test_daily_tune.py. Los avisos tienen preflight compartiendo sesión y cuota, tope de 15 anuncios únicos comprobados y estado HTTP exitoso antes de deduplicar.
- Problemas y cómo se resolvieron: un test de la regla antigua de cinco días falló al aplicar los siete días pedidos; se actualizó el límite y el test de frontera. Se reservará tiempo para estados tras atender candidatos nuevos. Las horas de venta y el precio negociado exactos no aparecen en el contrato público observado; se mantendrán explícitos sus límites.
- Intento de commit: el primer stage parcial del peso de confianza falló por convertir los bytes CRLF/UTF-8 del diff en texto de Windows. El índice no cambió. Se repitió preservando los bytes exactos antes de hacer el commit.

## 2026-11-08 03:35 — C3.6 · QR del enlace móvil
- Objetivo: transportar el fragmento completo de la clave a la cámara del móvil sin publicarlo.
- Hecho: vh board-url --qr mantiene la URL completa como salida local solicitada y genera out/board-url.png. Se captura esa salida en memoria durante la verificación; no se imprime la clave en la bitácora ni en las herramientas. Typer deja de mostrar variables locales en errores.
- Comandos clave: QR real generado y decodificado con zxing-cpp → texto idéntico al enlace completo con #k=. PNG ignorado y fuera del índice. Suite de trabajo → 126 aprobadas, 4 excluidas; Ruff sin errores.
- Evidencia: scratch/c3-qr-proof.json y out/board-url.png (privado, no se publica). qrcode pasa a dependencia de ejecución; tzdata permite el horario de Madrid en Windows y numpy se declara para el ajuste local. Playwright queda declarado como herramienta dev con el navegador ya instalado.
- Problemas y cómo se resolvieron: uv limpió los paquetes auxiliares que no estaban declarados; se añadió Playwright a dev para conservar la QA visual. El PNG queda fuera de out/pages, por lo que el despliegue de Pages no lo incluye.

## 2026-11-08 14:07 — C3 · Reanudación, histórico local y prueba de aviso
- Objetivo: cerrar el código de aplicación y continuar con las comprobaciones reales tras la interrupción.
- Hecho: revisión de git status y bitácora. El histórico archivado y el estado reciente descargado se fusionaron solo localmente: 3.210 → 5.196 anuncios, 1.586 recuperados del archivo y 400 del estado nuevo, sin eliminar IDs ni observaciones. Dos pasadas reales de estados comprobaron 12 anuncios cada una: un vendido y 23 activos, sin errores. Replay real → good 65, sold, generaría aviso en alta nueva activa simulada. vh tune real → 0/50 etiquetas utilizables, sin propuesta ni activación.
- Comandos clave: Ruff → 0; pytest → 127 aprobadas, 4 excluidas, 14,42 s. Chromium móvil → 1 vendido, 15 negociables, 48/48 descartados con talla, sin overflow ni errores JavaScript. Aviso de prueba al topic de anuncios → HTTP 200, con estado activo comprobado antes de enviar.
- Evidencia: scratch/c3-history.json, c3-live-features.json, c3-board-proof.json y recibo ntfy. El PNG privado se decodificó preservando #k= y permanece ignorado.
- Problemas y cómo se resolvieron: la revisión automática rechazó la exportación de una copia cifrada a una rama nueva, al no estar autorizados expresamente esa exportación y destino. No se ejecutó. Se eliminó esa ruta; la fusión queda local y la nube recuperará stock antiguo por el backfill público real, conservando su propia SQLite. No se detuvo el bucle ni se subió una base local.

## 2026-11-08 14:14 — C3.1/C3.3/C3.4/C3.5 · Aplicación lista para nube
- Objetivo: publicar avisos con preflight, revisión de estados y backfill diario dentro del bucle existente.
- Hecho: avisos activados por umbral de perfil, deduplicación tras HTTP 200, comprobación de ficha antes del envío; revisión acotada de estados; backfill diario con cursor persistente y sin reiniciar SQLite; pestañas Vendidos/Negociables, métricas y ajuste local de pesos preparado. README actualizado.
- Comandos clave: ruff check → 0; pytest -q → 127 aprobadas, 4 excluidas, 14,53 s. Recibo ntfy HTTP 200 confirma foto, enlace a Vinted y Tablero público sin fragmento de clave.
- Evidencia: scratch/c3-ntfy-proof.json, tests/test_ntfy.py, test_daily_tune.py y fixtures c3. La verificación de Actions se hará sobre el commit desplegado.
- Problemas y cómo se resolvieron: el contrato público no expone importe pagado ni instante exacto de venta. La interfaz identifica precio anunciado e intervalo estimado; no produce medias con anuncios encontrados ya vendidos sin transición observada.
