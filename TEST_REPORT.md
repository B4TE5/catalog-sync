# Informe de pruebas

2026-11-06T10:15:00.007856+01:00

- `vh selftest --report` · 8/8 etapas · 112.25 s · 20 peticiones.
  - ✅ Home y cookies · sesión pública
  - ✅ Catálogo · 42.09 s
  - ✅ Gates · embudo
  - ✅ Ficha · 3 enriquecidos
  - ✅ Visión · 2 evaluados
  - ✅ Score · 2 puntuados
  - ✅ Tablero · 0.06 s
  - ✅ Pasada sin incidentes · 69.64 s de procesamiento

## pytest offline

Salida 0.

```text
..............................................                           [100%]
46 passed, 4 deselected in 2.74s

```

## pytest -m live

Salida 0.

```text
....                                                                     [100%]
4 passed, 46 deselected in 33.33s

```

## Verificaciones adicionales

- vh doctor · salida 0. Portada 200, cookies, 96 tarjetas en catálogo general y 96 Stone Island por cada talla L y XL. La combinación Stone Island/Supreme también pasó.
- Pytest offline posterior al ajuste de registros históricos · 47 pasados, 4 live excluidos. Ruff · salida 0.
- vh backfill --pages 10 · salida 0. 25 peticiones, 1.123 IDs vistos, 147,2 s. La cohorte Stone Island registró 1.022 IDs.
- vh vision-check --profile stone-island --limit 30 · 30/30 anuncios, 192 fotos. 10 legibles, 7 detectados sin leer y 13 sin QR. Mediana de 43.97 s por anuncio, rango 11.42–82.53 s. Visión local con mediana de 0.26 s.

- Backfill complementario de Stone Island · salida 0. 21 peticiones y 112,7 s. 558 Stone Island, 10 fichas nuevas, 423 descartes y 135 pendientes.
