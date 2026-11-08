# Informe de pruebas

2026-11-08T16:57:56.460942+01:00

- `vh selftest --report` · 8/8 etapas · 83.69 s · 13 peticiones.
  - ✅ Home y cookies · sesión pública
  - ✅ Catálogo · 37.20 s
  - ✅ Gates · embudo
  - ✅ Ficha · 3 enriquecidos
  - ✅ Visión · 1 evaluados
  - ✅ Score · 1 puntuados
  - ✅ Tablero · 0.06 s
  - ✅ Pasada sin incidentes · 45.86 s de procesamiento

## pytest offline

Salida 0.

```text
........................................................................ [ 50%]
........................................................................ [100%]
144 passed, 5 deselected in 18.71s

```

## pytest -m live

Salida 0.

```text
....                                                                     [100%]
4 passed, 145 deselected in 32.09s

```

## Cierre C4 · 2026-11-08T17:36:44.350673+01:00

- Ruff limpio. Offline: 144 aprobadas, cinco excluidas. Live: cuatro aprobadas. Selftest: 8/8, 83,69 s y 13 peticiones, una ficha live puntuada; sin fallback.
- Doctor real: healthy, HTTP 200/cookies, parser 96 y filtros L/XL 96/96. Replay real prioritario top 75, sold, simulación de aviso como nuevo activo afirmativa.
- Recall/precision: 10690539539 top 75; 10653233816 good 70; seis casos negativos siguen rejected 0. Tests de bloqueo de envío para otros perfiles y good.
- WebKit/iPhone 13 en Pages real: una aprobada en 10,41 s; #k visible al abrir/recargar y restaurado en pestaña nueva pública desde respaldo; sin manifest, recarga sin localStorage y Olvidar.
- Workflow_dispatch 42497346203: ambos secrets de ntfy presentes, shadow_mode=false, HTTP 200 y recibo verificado. Mensaje técnico sin anuncio simulado.
- Tallas: treinta históricos sin talla (25 fichas sin atributo y cinco 404), más treinta controles actuales con talla publicada: concordancia y cobertura 30/30, 100 %. Tres fichas y tres catálogos reales sanitizados; regresiones de respaldo a11y y conservación de talla en pendientes.
- SQL final: 1224 pendientes, 0 sin talla; integridad ok. Gitleaks de fixtures: 15,17 MB analizados, cero hallazgos; CI de aplicación final en verde.

| Run | Inicio UTC | Peticiones | Vistos | Resultado |
| --- | --- | ---: | ---: | --- |
| 42499449270 | 2026-11-08T16:21:23Z | 37 | 786 | success |
| 42500316506 | 2026-11-08T16:31:39Z | 38 | 779 | success |

Las dos iteraciones finales guardaron el estado y publicaron Pages; ninguna se sustituye por el dispatch manual. La emulación de iPhone verifica el navegador, no la acción física de guardar un acceso. El error inicial de WebKit se documenta sin repetir la clave; el reporte de errores suprime su cadena original.
