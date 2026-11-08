# CORRECCION_3.md — avisos, tallas, vendidos, histórico, feedback, acceso móvil

Mismas reglas de AGENTS.md §0 (autónomo, sin preguntas, WORKLOG al día, commits por tarea, verificación con datos reales). Al terminar: push y verificación en Actions.

## C3.0 — Objetivo (criterio para cualquier decisión dudosa)
El scraper existe para dos cosas, en este orden:
1. **Stone Island, XL, sin capucha, original, precio de anuncio ≤ 60 € (inclusive), nueva o muy buen estado, a precio de ganga** — exactamente como 10690539539 (60 €, Muy bueno, gris, crewneck, QR en la descripción). Perder una así es el peor fallo posible; un falso positivo de vez en cuando es aceptable.
2. **Sudaderas con capucha talla L de TwoJeys, YZY Gap, Heron Preston y Rhude, originales y a precio de ganga.**
Solo Vinted. Nada de Wallapop ni otras fuentes. Estados válidos: Nuevo sin etiquetas, Muy bueno, y Nuevo con etiquetas solo si pasa los gates de precio y vendedor (ya existe). "Bueno" y "Satisfactorio" no pasan.
- [x] Verifica que el tope de precio es **inclusivo** y se aplica al **precio del anuncio** (60,00 € pasa; el total con comisión no cuenta para el tope). Test con 60,00 €.
- [x] Verifica que los estados permitidos son exactamente los de arriba en todos los perfiles activos. Test.

## C3.1 — Avisos activados
- [ ] `shadow_mode: false`.
- [ ] `notify_min_tier` por perfil en profiles.yaml: stone-island → `good` (≥60); resto → `top` (≥75).
- [ ] `vh replay https://www.vinted.es/items/10690539539-stone-island-sweater` debe indicar "generaría aviso" (aunque esté vendido, simulando que estuviera activo).
- [ ] Envía un aviso de prueba con el formato final al topic de anuncios.
- [ ] Nunca avisar de un anuncio vendido, reservado u oculto (comprobar estado justo antes de enviar).

## C3.2 — Tallas en todos los anuncios
- [ ] Hoy la talla se lee bien en top/good (que están enriquecidos), pero en descartados y en los no enriquecidos sale como desconocida, aunque el anuncio la muestre. Extrae la talla del `productItem` del catálogo (RSC: localiza el campo real con fixtures) para TODOS los anuncios, y de la ficha cuando se enriquece.
- [ ] Re-evalúa la base: ningún anuncio con talla visible en Vinted debe quedar como desconocida (consulta SQL antes/después en DECISIONS.md). Revisa también si algún descarte fue por talla mal leída y corrígelo.

## C3.3 — Vendidos
- [ ] En cada pasada, re-comprueba el estado de los anuncios top/good/revisar (máx. 15 por pasada, priorizando los mejores y los más recientes). Si están vendidos, reservados o borrados → estado `sold`/`reserved`/`gone`, fuera de las pestañas principales y dentro de una pestaña **Vendidos** con su precio final y cuánto duraron (subida → vendida).
- [ ] Usa esos datos de vendidos como señal de mercado: duración media hasta la venta por marca y precio. Mostrarla en `vh stats` y en el tablero.

## C3.4 — Histórico y stock que ya estaba subido
- [ ] El tablero solo tiene lo visto desde el último reinicio de la base. Añade un **backfill profundo diario** en el bucle de la nube (de madrugada, una vez cada 24 h): páginas 1–10 de cada búsqueda activa, con el mismo presupuesto y las mismas pausas, para captar sudaderas que llevan semanas o meses subidas y siguen a la venta.
- [ ] Los anuncios con ≥ 7 días subidos que pasen los filtros salen en una pestaña **Negociables**, con la oferta sugerida. No generan aviso salvo que tengan `price_drop`.
- [ ] Las pestañas Top y Buenas siguen siendo solo lo mejor y activo; el resto de datos se conserva (no borrar nada; histórico completo en SQLite).

## C3.5 — Feedback que aprende
- [ ] Al marcar `fake`: fotos a la lista negra (ya existe) + **vendedor a la lista negra** (sus anuncios futuros se descartan con razón `seller_blacklisted`). Se puede revertir con `vh label <id> meh`.
- [ ] Al marcar `good`: el vendedor entra en una lista de confianza (+10 en futuros anuncios).
- [ ] Contadores de etiquetas por tipo y por marca en el tablero.
- [ ] Prepara (sin activar) un módulo de ajuste de pesos: cuando haya ≥ 50 etiquetas, `vh tune` propone nuevos pesos del scoring (regresión logística sobre las señales ya calculadas, sin modelos de IA externos) y muestra precisión y recall antes/después. Nunca se aplica automáticamente: genera una propuesta en `config/scoring.proposed.yaml`.

## C3.6 — Acceso desde el iPhone
- [ ] `vh board-url --qr`: imprime en la terminal la URL completa con la clave **y un código QR** de esa URL (ASCII o PNG en `out/board-url.png`, que va en .gitignore). Así se escanea con la cámara del iPhone sin que se pierda el `#k=`.
- [ ] Comprueba que tras abrir una vez con la clave, el tablero se abre sin ella (clave guardada en localStorage) y que el botón "Tablero" de ntfy funciona.

## C3.7 — Seguridad y limpieza
- [ ] gitleaks en CI en cada push (falla si detecta secretos).
- [ ] Sanitizador obligatorio al guardar fixtures (JWT, cookies, tokens, cabeceras de sesión), con test.
- [ ] Saca de Git los scripts de `scratch/` que no hagan falta (y añade scratch/ a .gitignore salvo lo imprescindible).

## C3.9 — Preparado para otros productos de Vinted (sin añadir ninguno)
- [ ] Hoy la lógica de "es sudadera" (categorías, palabras de tipo, punto) está pensada solo para sudaderas. Muévela a configuración **por perfil** (`categories`, `type_keywords_include`, `type_keywords_exclude`) con los valores actuales como valores por defecto de los perfiles de sudaderas. Objetivo: que en el futuro añadir otro producto de Vinted sea solo añadir un perfil en YAML. No añadas perfiles nuevos ahora.
- [ ] Todos los tests de recall/precision siguen en verde tras el cambio.

## C3.8 — Verificación
- [ ] ruff, pytest (incluye recall/precision), `pytest -m live`, `vh selftest` 8/8 y `vh doctor` en verde.
- [ ] Push y 2 iteraciones del bucle verificadas en Actions (incluye la comprobación de vendidos).
- [ ] SESSION_REPORT.md con resultados (tallas antes/después, vendidos detectados, avisos enviados) y BLOCKERS.md actualizado.
