# Catalog Sync

Radar local de sudaderas en un catálogo público. Busca por filtros públicos y por texto,
recuerda lo ya visto y analiza los candidatos por precio, talla, estado, vendedor,
texto y fotos. Cada resultado conserva su rastro de decisión en SQLite.

## Instalación

Necesitas Python 3.12 y [uv](https://docs.astral.sh/uv/). Ejecuta los comandos desde
la raíz del proyecto. En Windows puedes usar la caché local si la predeterminada
da un error de permisos.

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv sync --python 3.12
uv run vh --help
```

En Linux, la variable equivalente es `export UV_CACHE_DIR="$PWD/.uv-cache"`.

## Uso

| Comando | Función |
| --- | --- |
| `uv run vh run` | Hace una pasada con las búsquedas de primera página. |
| `uv run vh watch --interval 10 --jitter 2` | Repite la pasada y regenera el tablero. Ctrl+C termina el bucle. |
| `uv run vh backfill --pages 10` | Recorre hasta diez páginas de la búsqueda principal y dedica la cuota restante a otras búsquedas. Guarda resultados sin contarlos como nuevos. |
| `uv run vh board` | Genera `out/board/index.html`. Ábrelo con doble clic. |
| `uv run vh serve` | Sirve el tablero local en [localhost:8787](http://localhost:8787). Puedes ejecutar `watch` en otra terminal. |
| `uv run vh stats` | Muestra precios y el embudo por perfil, con el inventario y la cohorte del último backfill. |
| `uv run vh vision-check --profile PERFIL --limit 30` | Mide QR, pHash y ORB en los anuncios recientes de la marca y categoría, con cualquier talla y precio. Guarda los tiempos por anuncio en `out/vision-check-PERFIL.json`. |
| `uv run vh explain 123` | Muestra los gates y señales de un anuncio guardado. |
| `uv run vh label 123 fake` | Etiqueta un anuncio e incorpora a la lista negra las huellas de sus fotos guardadas. También admite `good` y `meh`. |
| `uv run vh doctor` | Comprueba la salud persistida, la sesión pública, el parser y los filtros. |
| `uv run vh selftest --report` | Ejecuta una pasada acotada con base de datos separada y regenera `TEST_REPORT.md` con las pruebas offline y en vivo. |

Cada pasada usa una sesión anónima. Los límites configurados son 12 consultas
de catálogo y 12 de enriquecimiento, incluidas las fotos, además de la portada.
El enriquecimiento se reanuda cuando los anuncios pendientes reaparecen en
otra búsqueda. Un 403 o 429 abre el circuito. Los estados del parser y los
incidentes quedan en `data/logs/` y en el tablero.

Las consultas rotan. Cuando una consulta se usa por primera vez después de la
pasada inicial, sus anuncios se registran como descubiertos. Las búsquedas ya
observadas y las bajadas de precio alimentan el contador de nuevos.

## Perfiles y calibración

- Edita `config/profiles.yaml` para activar perfiles, variar precios, talla, capucha,
  estados, vendedor mínimo y búsquedas de texto. Las búsquedas prioritarias van
  en cada pasada y las demás rotan con un cursor persistente.
- Añade IDs a `config/vinted_ids.yaml` solo después de comprobar la URL y sus
  resultados reales. Los perfiles sin un ID verificado siguen buscándose por texto.
  Los gates de talla, capucha, color y estado esperan a la ficha. Un atributo ausente queda como no confirmado.
- Usa `config/scoring.yaml` para ajustar palabras, pesos, umbrales, presupuesto y
  estimaciones. El total usa la protección publicada por el catálogo cuando existe y suma
  el envío estimado configurado. En su defecto se estima la protección con la fórmula
  del YAML. Revisa el impacto de los cambios con `stats`, `explain` y las etiquetas.
- Añade referencias locales de etiquetas, parches y fotos de catálogo según
  [refs/README.md](refs/README.md). ORB detecta partes visualmente similares.

La base de datos, la caché y los logs se guardan en `data/`. El tablero inserta
los datos y las fotos cacheadas de los candidatos dentro del HTML. Las fotos sin
caché se muestran desde sus URLs públicas cuando hay conexión.

La señal de actividad usa `favoritos / max(edad_en_minutos, heat_min_age)`.
La edad sale de la publicación o, si falta, de la primera observación.
Los favoritos ausentes aportan cero.

## Pruebas

```text
uv run ruff check
uv run pytest
uv run pytest -m live
uv run vh selftest --report
```

Las pruebas offline del parser usan capturas reales anonimizadas. Las pruebas
en vivo consumen parte del presupuesto de peticiones, así que ejecútalas fuera
de un ciclo de `watch`. Consulta [TEST_REPORT.md](TEST_REPORT.md),
[BLOCKERS.md](BLOCKERS.md) y [SESSION_REPORT.md](SESSION_REPORT.md) para ver
la validación y los límites observados en esta sesión.


## Captura programada y avisos

El flujo programado y el manual restauran la instantánea cifrada de SQLite de
la rama de estado. Después de capturar, sustituyen su única revisión. El
artefacto del panel usa AES-GCM y WebCrypto. Una vez habilitado Pages, el comando
local `uv run vh board-url` prepara un enlace privado para abrir en el navegador.
La pantalla pública tiene metadatos genéricos y requiere la clave en el fragmento.

En local, `uv run vh watch` usa los topics configurados en `.env`. En Actions,
los mismos nombres se leen desde los secretos del repositorio. El modo sombra
envía únicamente transiciones de salud. Para activar avisos de anuncios en una
configuración futura, cambia `shadow_mode` a `false`. El comando `vh notify-test`
envía un ejemplo a cada topic. El botón Tablero usa el enlace público de Pages
del repositorio. `BOARD_URL` permite usar otro enlace HTTPS. Para abrir los datos
cifrados, usa el enlace privado que genera `vh board-url`.

Los botones Fake, Buena y No me interesa abren una solicitud prellenada en
GitHub. El flujo de feedback acepta solicitudes válidas del dueño del repositorio
y comparte la exclusión mutua con la captura. En local se puede usar `vh label`.
