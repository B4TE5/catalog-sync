# Informe de pruebas · CORRECCION_2

2026-11-08T01:25:27.673903+01:00 · Revisión correction-2.2. Verificación local nativa en Windows y pasadas reales en Ubuntu de Actions. Todas las comprobaciones terminaron en verde.

| Comando | Resultado | Duración |
| --- | --- | --- |
| `uv run --offline ruff check` | salida 0 | — |
| `uv run --offline pytest -q` | 106 aprobadas, 4 excluidas | 8,26 s |
| `uv run --offline pytest -q -m live` | 4 aprobadas, 106 excluidas | 35,46 s |
| `uv run --offline vh selftest` | salida 0, 8/8 etapas | 67,3 s |
| `uv run --offline vh doctor` | salida 0, todos los checks verdes | — |
| `uv run --offline vh replay https://www.vinted.es/items/10690539539-stone-island-sweater` | salida 0, good 65 | — |

## Alcance de las pruebas

- Offline: parser con capturas reales, gates y datos desconocidos, NL/PT, algodón/punto y colisión lã/la, prioridad y backlog, dedupe, precios, scoring, QR/pHash/ORB, recall/precisión, estado cifrado, notifier y coordinación de Actions.
- Live: catálogo, ficha, vendedor/armario y filtros L/XL contra Vinted real.
- Selftest en base aislada: home/cookies, 480 vistos, gates, tres fichas enriquecidas, visión, score, tablero y pasada sin incidentes. Usó 13 peticiones. Las tres fichas se descartaron antes de score; visión/score se verificaron con el caso real de recall 10653233816, good 70, indicado expresamente en la salida. Se generó su tablero temporal.
- Doctor: home/cookies HTTP 200, parser con 96 anuncios, marcas activas combinadas y filtros reales L/XL con 96 Stone Island de la talla solicitada; salud healthy.
- Replay prioritario: todos los gates aprobados, vendedor con siete valoraciones y nota 4,0, cinco pHash, QR none, cero fotos de catálogo y ninguna coincidencia ORB. Compatibilidad de filtros/texto explicada por query; no se inventa una posición histórica del anuncio vendido.
- Chromium sobre Pages real: Todos excluye pendientes, pestaña Pendientes y paginación; clave guardada, fragmento limpio, reapertura, olvidar, borrado de clave inválida y descifrado con localStorage bloqueado. La clave se mantuvo en memoria.
- Integridad de SQLite comprobada al archivar el ensayo local y copiar el estado operativo validado. La etiqueta de feedback de nube se conserva.

Salida de las verificaciones tras la reanudación en `data/correction2-resume-checks.log`. Fixtures reales en `tests/fixtures`, `tests/recall` y `tests/precision`. Las pruebas de límites y fallos de red usan dobles de HTTP; las capturas del parser y de recall/precisión proceden de Vinted real.

## Tres iteraciones normales recientes de Actions

| Run Snapshot | Inicio Madrid | Segundos | Vistos | Nuevos | Pendientes | Sin ficha |
| --- | --- | --- | --- | --- | --- | --- |
| 42427270371 | 00:53:43 | 77.36 | 781 | 1 | 0 | 0 |
| 42428059280 | 01:04:24 | 88.22 | 766 | 9 | 0 | 0 |
| 42428917006 | 01:15:35 | 89.66 | 820 | 9 | 0 | 0 |

Tres índices consecutivos, actor automático de Actions, intervalos **641 y 671 s**, revisión correction-2.2, sin errores. Restauración, guardado cifrado, artefacto cifrado y deploy-pages verificados en cada una. Estado con cero padres y un único state.enc; Pages HTTP 200 y payload descifrado con el mismo latido. Nuevos respaldados por primeras observaciones/bajadas en price_history. Logs sin coincidencias de valores de .env.

Descartes por pasada:

- 42427270371: size=1.
- 42428059280: knitwear=1, price=5, size=3.
- 42428917006: not_sweatshirt=3, price=6.

La primera terna acreditada antes del corte fue 42410718931, 42411565308 y 42412300711: también dejó cero pendientes en las tres. Se revalidó la terna reciente al retomar.

## SQL sobre la base real

| Métrica | Nube antes | Nube final |
| --- | --- | --- |
| Anuncios guardados | 2465 | 3210 |
| Pendientes | 823 | 0 |
| Pendientes sin ficha confirmada | 823 | 0 |
| No-sudaderas identificables en pendientes | 80 | 0 |
| No-sudaderas aceptadas | 0 | 0 |

Consulta con la función de clasificación del proyecto y reglas finales sobre ambos estados. La instantánea final validada corresponde a 2026-11-08T00:15:35.520810+00:00. Las 823 fichas pendientes originales estaban sin enriquecer. Se completaron 14 limpiezas, todas success con guardado y Pages; máximo observado 232,43 s. El objetivo queda acreditado con cero pendientes, cero no-sudaderas pendientes/aceptadas y cero pendientes sin ficha.

Comandos SQL, cohorte fija de Stone Island y decisiones en [DECISIONS.md](DECISIONS.md). Evidencia compacta sin secretos en [evidence/correction2-validation.json](evidence/correction2-validation.json); resultados y límites en [SESSION_REPORT.md](SESSION_REPORT.md).
