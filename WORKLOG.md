# Bitácora de trabajo

## 2026-11-06 00:28 — Prueba de viabilidad · Entorno

- Objetivo: verificar la carpeta de trabajo y preparar una prueba aislada de acceso a Vinted.
- Hecho: comprobé `C:\dev\vinted-hunter` y su listado inicial (`AGENTS.md`, `PLAN.md`, `profiles.yaml`). Leí `AGENTS.md` como contexto. Creé `scratch/probe.py` y el entorno Python 3.12.10 en `scratch/.venv`.
- Comandos clave: `Get-Location` y `Get-ChildItem -Force` → carpeta y archivos requeridos presentes (salida 0). `python -c "import curl_cffi"` → `ModuleNotFoundError` (salida 1). `uv venv --python 3.12 scratch/.venv` → bloqueo de la caché predeterminada, `Acceso denegado. (os error 5)` (salida 2). Con `UV_CACHE_DIR=scratch/.uv-cache`, la creación del entorno terminó en verde.
- Problemas y cómo se resolvieron: `uv pip install --python scratch/.venv/Scripts/python.exe curl-cffi` falló al conectar a PyPI dentro del sandbox (`os error 10061`, salida 2). Repetí la instalación con acceso de red autorizado y se instaló `curl-cffi==0.17.0` en el entorno de `scratch/` (salida 0).

## 2026-11-06 00:28 — Prueba de viabilidad · Captura y extracción

- Objetivo: obtener la portada y la búsqueda de Stone Island, y extraer al menos 10 anuncios completos del cuerpo recibido.
- Hecho: ejecuté `scratch/probe.py` con una sola sesión `curl_cffi`, `impersonate="chrome"`, sin iniciar sesión y con una pausa aleatoria de 3 a 8 segundos entre peticiones. Guardé los cuerpos HTML completos sin cabeceras. Añadí `--offline` para desarrollar y verificar el extractor sobre la misma captura sin repetir peticiones a Vinted.
- Comandos clave: `scratch/.venv/Scripts/python.exe -X utf8 scratch/probe.py` (captura inicial, salida 0) → `https://www.vinted.es/` HTTP 200, 1.753.631 bytes; `https://www.vinted.es/catalog?search_text=stone%20island&order=newest_first` HTTP 200, 3.677.094 bytes. Ambas respuestas fueron `text/html; charset=utf-8`.
- Comandos clave: `scratch/.venv/Scripts/python.exe -X utf8 scratch/probe.py --offline` → 96 anuncios únicos con ID, título, precio base, moneda y URL (salida 0). Una comprobación local confirmó que los 96 ID coinciden con los enlaces de las tarjetas del HTML y que una página sin payload produce cero resultados.
- Evidencia: `scratch/home.html` (SHA-256 `6bc9132de20f3ede4e8d0df5f920e884a49669dfd1f593cb20b8bea759c88c94`) y `scratch/catalog.html` (SHA-256 `e7a3e6193fad55a1d51b3cd2d23ec68ffec6cf7a5d6c4cd6bd2c658fd82bd3bc`). El catálogo contiene 59 llamadas a `self.__next_f.push`. Al unir los fragmentos RSC, `items.items[].productItem` contiene `id`, `title`, `price.amount`, `price.currencyCode` y `url`. El script convierte la ruta recibida en una URL absoluta.

## 2026-11-06 08:31 — Fase 0 · Base
- Objetivo: arrancar el paquete y verificar el entorno Windows.
- Hecho: inicialicé Git, instalé el entorno Python 3.12, creé el comando inicial y moví el archivo de perfiles a su ubicación prevista.
- Comandos clave: uv sync con acceso a PyPI → 33 paquetes instalados. uv run --offline vh --help → 0. uv run --offline pytest → 1 pasado. uv run --offline ruff check → 0.
- Evidencia: pyproject.toml, uv.lock, tests/test_cli.py y config/profiles.yaml.
- Problemas y cómo se resolvieron: el archivo de perfiles estaba en la raíz. La instalación inicial falló con Host desconocido (os error 11001) para PyPI y se repitió con red autorizada. Ruff encontró cuatro errores en un script de inspección temporal que quedó fuera del árbol versionado.
