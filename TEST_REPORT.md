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
