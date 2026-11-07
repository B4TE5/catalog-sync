# Informe de pruebas

2026-11-06T20:20:23.261573+01:00

- `vh selftest --report` · 8/8 etapas · 115.67 s · 20 peticiones.
  - ✅ Home y cookies · sesión pública
  - ✅ Catálogo · 45.58 s
  - ✅ Gates · embudo
  - ✅ Ficha · 2 enriquecidos
  - ✅ Visión · 2 evaluados
  - ✅ Score · 2 puntuados
  - ✅ Tablero · 0.05 s
  - ✅ Pasada sin incidentes · 69.55 s de procesamiento

## pytest offline

Salida 0.

```text
........................................................                 [100%]
56 passed, 4 deselected in 3.30s

```

## pytest -m live

Salida 0.

```text
....                                                                     [100%]
4 passed, 56 deselected in 34.23s

```

- Corrección sobre SQLite real · 2.164 anuncios reevaluados offline. Consulta de prendas fuera de perfil fuera de Descartados · 121 antes, 0 después. Chromium local · panel, JSON plegado, pendientes y aviso de mercado verificados. Ruff limpio y 57 pruebas offline en el cierre de corrección.

## Fase 2 · Evidencia inicial

- Pasada normal con CDN concurrente · 25 peticiones, 884 vistos y 117,31 s. Los candidatos tardaron 16,38 y 17,39 s.
- Sondas Actions · runs 42279884459, 42280627200 y 42281374832. Tres HTTP 200 con 96 anuncios. Intervalos de despacho de 302 s. Logs por API revisados sin coincidencias de secretos.
- ntfy · los dos POST reales de prueba devolvieron HTTP 200. El modo sombra, los cambios de salud y la deduplicación pasaron las pruebas con HTTP simulado.
- Chromium local · pantalla neutra sin clave, clave errónea rechazada, descifrado con clave válida y enlaces de feedback correctos. El primer intento de QA consultó el iframe antes de completar el descifrado y se repitió con espera explícita.
- Pages · HTTP 403 al activar y HTTP 404 al consultar el sitio. [Bloqueo](BLOCKERS.md)

## Fase 2 · Cierre remoto

- `uv run --offline ruff check` · salida 0. `uv run --offline pytest -q` · salida 0, 69 aprobadas y 4 excluidas, 4,63 s.
- `uv run --offline vh doctor` · salida 0, HTTP 200 y 95 anuncios en la búsqueda base. Marcas combinadas y tallas L/XL · 96 en cada comprobación.
- `uv run --offline vh selftest` · salida 0, 8/8 etapas, 15 peticiones, 669 vistos y 76,3 s.
- `uv run --offline pytest -q -m live` · salida 0, 4 aprobadas y 69 excluidas, 37,89 s.
- Manual 42282635097 · verde. Estado de un commit cifrado y artefacto cifrado comprobado.
- Feedback · issues 1 y 2 cerrados automáticamente. La etiqueta válida quedó guardada. El rechazo no cambió el estado.
- Cron · 0 ejecuciones completadas en la ventana. Bloqueada la validación de tres pasadas programadas. La API devolvió HTTP 200 y total 0 al cierre de la ventana.

## Validación de Pages y ntfy · 2026-11-06 22:29

- Ruff · salida 0. Pytest offline · 71 pasadas, 4 excluidas, 5,23 s.
- Pytest live · 4 pasadas, 71 excluidas, 40,88 s. `vh selftest` · 8/8 etapas, 15 peticiones y 82,3 s.
- Actions · run 42296435101 en verde, incluido `deploy-pages`. Artefacto 13542332390 y HTML servido con el mismo SHA-256. Logs auditados sin coincidencias de secretos.
- Chromium · HTTP 200 en los tres casos. Pantalla neutra sin clave, clave incorrecta rechazada y 48 tarjetas con `vh board-url`.
- `vh notify-test` · dos HTTP 200. La API de suscripción devolvió ambos avisos con la acción `view` Tablero y la URL pública sin fragmento. [API de ntfy](https://docs.ntfy.sh/subscribe/api/#poll-for-messages)

## Bucle y relevo · 2026-11-07 17:55

- `uv run --offline ruff check` · salida 0. `uv run --offline pytest -q` · 82 aprobadas, 4 excluidas, 4,78 s.
- `uv run --offline pytest -q -m live` · 4 aprobadas, 80 excluidas en esa revisión, 40,75 s.
- Regresiones · carreras de inicio y relevo, continuación tras un fallo, duración de 340 minutos, despacho de respuesta incierta, reintento de lectura y cancelación de una pasada agotada. Las pruebas de ntfy mantienen las transiciones de incidencia y recuperación.
- Actions · coordinador 42391701686 y 3 Snapshots en verde, con estado y Pages actualizados en cada uno. Intervalos de 498.57 s, 646.96 s. Sucesor 42393577665 creado por Actions y despertar duplicado 42391821189 omitido. Logs auditados sin coincidencias de los secretos locales.
- `vh selftest` · salidas 1 con 6/8 en 75,0 s y 15 peticiones, 7/8 en 91,9 s y 17 peticiones, y 7/8 en 99,8 s y 17 peticiones. Tres fichas por muestra, descartadas antes de score. Se conserva la verificación pendiente en BLOCKERS.md.

## CORRECCION_2 · Revisión correction-2.2 · 2026-11-07

- `uv run --offline ruff check` · salida 0.
- `uv run --offline pytest -q` · salida 0, **106 aprobadas**, 4 excluidas, **8,40 s**. Incluye recall, precisión, prioridad, recuperación de backlog, filtros padre 79, NL/PT, material y conservación de la tilde portuguesa.
- `uv run --offline pytest -q -m live` · salida 0, **4 aprobadas**, 106 excluidas, **39,86 s**. Catálogo, fichas, vendedor/armario y tallas reales.
- `uv run --offline vh selftest` · salida 0, **8/8**, **75,0 s**, 13 peticiones, 480 vistos y tres fichas enriquecidas. Las tres se descartaron antes de score; visión y score se verificaron con el caso real capturado 10653233816, **good 70**, identificado expresamente en la salida. Tablero temporal generado. Las primeras verificaciones de la corrección alcanzaron también 8/8 con score en vivo.
- `uv run --offline vh doctor` · salida 0. Home/cookies HTTP 200, 96 anuncios parseados, marcas activas combinadas válidas, L y XL con 96 Stone Island de la talla solicitada, salud healthy.
- Salida local de estos comandos conservada en `data/correction2-release-checks.log`, sin credenciales. La observación final de Actions y la consulta SQL se incorporan a continuación al completarse.
