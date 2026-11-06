# Informe de pruebas

2026-11-06T09:06:22.278971+01:00

- `vh selftest --report` · 8/8 etapas · 116.17 s · 20 peticiones.
  - ✅ Home y cookies · sesión pública
  - ✅ Catálogo · 44.55 s
  - ✅ Gates · embudo
  - ✅ Ficha · 2 enriquecidos
  - ✅ Visión · 2 evaluados
  - ✅ Score · 2 puntuados
  - ✅ Tablero · 0.06 s
  - ✅ Pasada sin incidentes · 71.05 s de procesamiento

## pytest offline

Salida 0.

```text
.............................                                            [100%]
29 passed, 3 deselected in 1.89s

```

## pytest -m live

Salida 1.

```text
..F                                                                      [100%]
================================== FAILURES ===================================
_________________________ test_live_filtered_catalog __________________________

client = <vinted_hunter.sources.vinted.client.VintedClient object at 0x000001167F20B230>

    def test_live_filtered_catalog(client: VintedClient) -> None:
        ids = load_config(ROOT).ids
        size = ids.size_ids.get("XL") or ids.item_size_ids["XL"]
        response = client.get(
            "/catalog",
            "catalog",
            {
                "catalog[]": ids.catalog_ids["sweatshirts"],
                "brand_ids[]": ids.brand_ids["Stone Island"][0],
                "size_ids[]": size,
                "order": "newest_first",
            },
        )
        result = parse_catalog(response.text, client.base)
>       assert result.listings, (
            f"Stone Island XL: el filtro público devolvió {result.raw_count} tarjetas. "
            f"Taxonomía pendiente: {', '.join(configured_ids(ROOT))}"
        )
E       AssertionError: Stone Island XL: el filtro público devolvió 0 tarjetas. Taxonomía pendiente: talla L, talla XL, categoría with, categoría without, estado new_with_tags, estado new_without_tags, estado good, estado satisfactory, color gris
E       assert []
E        +  where [] = SearchResult(listings=[], raw_count=0, invalid_count=0).listings

tests\test_live.py:67: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_live.py::test_live_filtered_catalog - AssertionError: Stone...
1 failed, 2 passed, 29 deselected in 33.87s

```

## Comprobaciones posteriores

- `uv run --offline pytest -q` · 30 pasados, 3 live excluidos · 2,44 s. Incluye el fixture real de marcas combinadas.
- `uv run --offline ruff check` · salida 0.
- `vh doctor` · salida 1. Portada HTTP 200, cookies presentes, 96 anuncios en catálogo y 96 anuncios de Stone Island y Supreme con las dos marcas. Filtro Stone Island XL con el atributo de prueba 515 · 0 tarjetas.
- `vh serve` y GET local · HTTP 200. Playwright verificó apertura por archivo en 1440 px y 390 px, enlaces, imágenes cacheadas y rastro desplegable.

## Verificación final

- `uv run --offline pytest -q` · 31 pasados, 3 live excluidos · 2,04 s.
- `uv run --offline ruff check` · salida 0.
- Dos ejecuciones de `vh run` · salida 0 y 25 peticiones cada una. La segunda registró 835 IDs vistos, ocho primeras observaciones y una bajada confirmada. Puntuó dos candidatos en 142,25 s.
- Captura final con Playwright · 1.914 anuncios en el tablero, 48 tarjetas visibles por página, sin desbordamiento en ambos tamaños. Se verificaron el carrusel, el rastro desplegable, las fotos cacheadas y el enlace del anuncio.
