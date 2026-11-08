# Informe de pruebas

2026-11-08T15:19:46.296807+01:00

- `vh selftest --report` · 8/8 etapas · 73.33 s · 13 peticiones.
  - ✅ Home y cookies · sesión pública
  - ✅ Catálogo · 32.86 s
  - ✅ Gates · embudo
  - ✅ Ficha · 3 enriquecidos
  - ✅ Visión · 1 evaluados
  - ✅ Score · 1 puntuados
  - ✅ Tablero · 0.05 s
  - ✅ Pasada sin incidentes · 39.89 s de procesamiento

## pytest offline

Salida 0.

```text
........................................................................ [ 54%]
............................................................             [100%]
132 passed, 4 deselected in 13.96s

```

## pytest -m live

Salida 0.

```text
....                                                                     [100%]
4 passed, 132 deselected in 41.20s

```

## Cierre CORRECCION_3 · 2026-11-08T15:40:43.550211+01:00

- Ruff sin errores. Suite de configuración, disponibilidad, feedback, backfill diario, ofertas envejecidas, historial, QR y sanitizador incluida en los 132 tests.
- Doctor final: HTTP 200, cookies, 96 anuncios parseados; marcas activas combinadas; L/XL 96/95 y salud healthy. Salida 0.
- Replay real 10690539539: good 65; sold; generaría aviso como nuevo activo. Salida 0.
- Selftest final: visión y score de la ficha live 10131292014; no necesitó fallback.
- QR privado decodificado idéntico al enlace completo; Pages real, localStorage, botón ntfy público, fragmento limpio, olvidar/clave inválida/storage bloqueado; viewport 390×844, sin errores JS ni overflow.
- Un aviso de prueba HTTP 200 y 5 avisos automáticos. Guardias de vendido/reservado/oculto/desconocido y reintento tras fallo cubiertas por tests.
- Base local: 5196 registros; 0 tallas sin comprobar. Nube: 7938 registros; 0 tallas sin comprobar; ningún descarte por talla ausente ni no-sudadera identificable pendiente.
- Backfill real 150/150, quince búsquedas: 107 peticiones nuevas y 41 páginas omitidas tras vacíos reales. La primera ejecución fue de instalación por la tarde; la ventana nocturna 03:00–05:00 se valida por tests y la continuación real.
- Revisión literal de AGENTS §10: parsers catálogo/ficha/usuario con capturas; cada gate y desconocidos; capucha; texto multilingüe; precios/ofertas; scoring top/rejected; dedupe/resubida/bajada; QR legítimo y dominio falso; pHash reescalado. Las regresiones de recall/precisión forman parte de la suite completa.
- Gitleaks en CI escanea todo el historial y gzip con redacción. Solo doce fingerprints históricos exactos de JWT públicos caducados están exceptuados; la guardia de reintroducción detecta el mismo JWT fuera de esa procedencia.

## Iteraciones normales con aplicación final

| Run | Inicio de captura UTC | Peticiones | Vistos | Resultado |
| --- | --- | ---: | ---: | --- |
| 42489721321 | 2026-11-08T14:29:08Z | 38 | 820 | success · estado + Pages |
| 42490550896 | 2026-11-08T14:35:36Z | 39 | 853 | success · estado + Pages |

Las dos restauraron/guardaron estado, sellaron artefacto y desplegaron Pages HTTP 200. Detalle de límites y estados por pasada en evidence/correction3-validation.json. Las capturas del parser son reales; los casos de frontera usan variantes controladas de modelos reales y los tests matemáticos de ajuste no inventan respuestas de Vinted.

## Incidencia de nube

Snapshot 42488165596 terminó con `catalog: Timeout` y `availability: Timeout`.
Conservó el estado cifrado y publicó Pages. El siguiente Snapshot 42488842985
terminó en verde. La evidencia conserva ese fallo y lo distingue de las dos
iteraciones finales exitosas.

## Límites

El importe pagado y el instante exacto de venta no se publican. Se muestran precio anunciado e intervalos estimados, sin inventar duración para un anuncio encontrado ya vendido. vh tune permanece sin activar hasta reunir 50 etiquetas reales utilizables. Referencias ORB siguen sin aportarse. La QA móvil usa Chromium, no un iPhone físico.
