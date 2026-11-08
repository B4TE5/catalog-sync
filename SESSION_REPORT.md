# Informe de sesión · CORRECCION_2

2026-11-08T01:25:27.673903+01:00

CORRECCION_2 queda completa. El replay real de [10690539539](https://www.vinted.es/items/10690539539-stone-island-sweater) alcanza **good · 65 puntos**. La base operativa tiene **0 pendientes**, **0 no-sudaderas pendientes** y **0 pendientes sin ficha confirmada**. Se acreditaron tres iteraciones normales consecutivas de Actions con correction-2.2, estado guardado y Pages publicado en cada una.

## Anuncio prioritario y causa

La ficha real confirma Jerséis 1811, algodón, XL, gris, 60 EUR y Muy bueno. El neerlandés menciona crewneck y QR-code. Ya estaba capturado tanto en local como en nube; seguía pendiente sin enriquecimiento y sin un gate fallido. El pipeline anterior solo retomaba pendientes que reaparecían en una captura: ahora incorpora también el backlog guardado. La categoría antigua 267 lo excluía de búsquedas filtradas por marca. La entrada por texto es una inferencia: el estado histórico no conserva la query concreta de cada ID.

El resultado final suma base 40, estado +10, autenticación mencionada +10 y cinco fotos +5. La visión devuelve QR none y cero fotos de catálogo; no se afirma que haya leído Certilogo. El vendedor tiene siete valoraciones y nota 4,0. Se bajó el mínimo de Stone Island de 4,5 a 4,0, con efecto general sobre ese perfil y sin excepción por ID. La misma ficha queda puntuada en la base de Actions.

## Cambios aplicados

- Palm Angels y Supreme desactivados; Palace sigue desactivado.
- Todas las búsquedas usan el padre real 79, incluidos los textos. Sudaderas 267 y 1812 pasan por categoría; Jerséis 1811 requiere evidencia de sudadera/algodón y excluye punto/lana. Se parsea el material de la ficha.
- NL/PT en las listas y +10 por mención de QR/Certilogo/código de autenticidad. «Lã» conserva la tilde: la auditoría detectó 65 falsos descartes por confundirla con «la» y las reglas finales los reevaluaron.
- Nuevos antes de backlog, Stone Island prioritario y precio relativo. El backlog se procesa aunque no reaparezca. Cuota cloud de hasta 72 peticiones de enriquecimiento, incluidas fotos, con límite temporal para terminar bajo cinco minutos.
- Pendientes fuera de Todos y en su pestaña. Clave persistente con try/catch, fragmento limpio, reapertura, botón para olvidar y eliminación de claves inválidas.
- Replay sobre copia temporal, explicaciones en español y capturas reales de recall/precisión. Selftest conserva la muestra live y admite un caso real de recall cuando las tres fichas se descartan.

## Limpieza y embudo

La comparación de inventarios usa la instantánea de nube original de 823 pendientes. La actividad del catálogo añadió anuncios durante la sesión, por eso crece el total. «Identificables» cuenta la evidencia disponible en el estado; antes las 823 fichas pendientes carecían de enriquecimiento. La instantánea final validada corresponde a la pasada 2026-11-08T00:15:35.520810+00:00; su cola está confirmada.

| Métrica | Nube antes | Nube final |
| --- | --- | --- |
| Anuncios guardados | 2465 | 3210 |
| Pendientes | 823 | 0 |
| Pendientes sin ficha confirmada | 823 | 0 |
| No-sudaderas identificables en pendientes | 80 | 0 |
| No-sudaderas aceptadas | 0 | 0 |

Para comparar Stone Island sin mezclar nuevos avistamientos se usa la **misma cohorte original de 1368 IDs**, todos conservados:

| Stone Island · misma cohorte | Antes | Después |
| --- | --- | --- |
| Vistos | 1368 | 1368 |
| Con ficha enriquecida | 102 | 321 |
| pending | 366 | 0 |
| rejected | 1002 | 1367 |
| low | 0 | 0 |
| maybe | 0 | 0 |
| good | 0 | 1 |
| top | 0 | 0 |

| Motivo · cohorte original | Antes | Después |
| --- | --- | --- |
| color | 1 | 19 |
| hood | 0 | 7 |
| knitwear | 0 | 77 |
| listing_unavailable | 0 | 34 |
| not_sweatshirt | 364 | 469 |
| price | 629 | 553 |
| replica | 0 | 2 |
| seller_rating | 0 | 1 |
| size | 8 | 120 |
| status | 0 | 4 |
| too_cheap_for_brand | 0 | 81 |

El motivo corresponde al primer gate fallido; al cambiar la evidencia y las reglas, una fila puede pasar del motivo precio a prenda/punto sin que cambie su precio.

El inventario Stone Island completo al cierre contiene 1766 vistos, 471 enriquecidos y tiers {"rejected": 1764, "low": 1, "good": 1}. La consulta SQL y el desglose reproducible están en [DECISIONS.md](DECISIONS.md).

## Tres iteraciones reales de Actions

| Run Snapshot | Inicio Madrid | Segundos | Vistos | Nuevos | Pendientes | Sin ficha |
| --- | --- | --- | --- | --- | --- | --- |
| 42427270371 | 00:53:43 | 77.36 | 781 | 1 | 0 | 0 |
| 42428059280 | 01:04:24 | 88.22 | 766 | 9 | 0 | 0 |
| 42428917006 | 01:15:35 | 89.66 | 820 | 9 | 0 | 0 |

Separación entre comienzos de captura: **641 s y 671 s**. Cada pasada terminó success, restauró y guardó state.enc, conservó una revisión de estado sin padres y publicó Pages HTTP 200. El payload descifrado del tablero coincide con el latido guardado. Los logs auditados no contienen valores de .env. Los nuevos quedan respaldados por primeras observaciones/bajadas reales en price_history.

Descartes por pasada:

- 42427270371: size=1.
- 42428059280: knitwear=1, price=5, size=3.
- 42428917006: not_sweatshirt=3, price=6.

El coordinador 42393577665 siguió activo durante la limpieza y solicitó su relevo. Al revalidar las tres pasadas más recientes está activo su sucesor 42420026075. Las pasadas de mantenimiento compartieron el bloqueo de estado con las normales. Todos los workflows usan el token automático de Actions y los secretos de cifrado/ntfy; el PAT solo se usa desde el equipo para administración/push. Shadow mode sigue activo.

Se verificaron 14 pasadas de mantenimiento; sus checkpoints y resultados están en `evidence/correction2-validation.json`, junto con las tres iteraciones normales finales.

## Pruebas y tablero

- Ruff limpio; 106 pruebas offline aprobadas en 8,26 s, incluidos recall y precisión.
- Live: 4 aprobadas en 35,46 s contra Vinted real.
- Selftest final en base aislada: **8/8**, 67,3 s y 13 peticiones. Catálogo y tres fichas en vivo; al descartarse las tres, visión/score se verificaron con el caso real capturado 10653233816, good 70, indicado en la salida. En verificaciones previas de la corrección hubo score en vivo.
- Doctor verde: home/cookies/parser, marcas activas, L y XL reales, salud healthy.
- Replay real prioritario: salida 0, good 65. Chromium sobre Pages: Todos/Pendientes, paginación, clave guardada, reapertura, olvidar, clave inválida y almacenamiento bloqueado aprobados. Clave mantenida en memoria.

[TEST_REPORT.md](TEST_REPORT.md) conserva comandos, tiempos y verificaciones. [WORKLOG.md](WORKLOG.md) conserva cada paso, incluidos intentos fallidos.

## Estado local y límites

Se sincronizó la base local de trabajo con el estado operativo validado de Actions. La base local anterior de 2445 anuncios y sin etiquetas manuales se conserva íntegra en `data/vh-local-correction2-archive.sqlite`; sus 1586 IDs exclusivos permanecen en ese archivo. No se mezclan pendientes antiguos en la cola ya confirmada. El tablero local se regeneró desde la instantánea validada.

No quedan bloqueos de CORRECCION_2. Siguen los límites opcionales documentados en [BLOCKERS.md](BLOCKERS.md): referencias ORB aún vacías, visitas no expuestas e IDs opcionales sin evidencia. No se fabricaron esos datos.

Las primeras capturas nuevas incluyeron por error doce JWT públicos de telemetría otelToken. Los fixtures actuales están redactados y una prueba impide repetirlo. Las versiones anteriores permanecen en Git con esos JWT, vencidos como máximo el 7 de noviembre a las 19:40:23 Madrid. No eran credenciales de .env; la auditoría no encontró sus valores en historial, logs, remote ni configuración Git.
