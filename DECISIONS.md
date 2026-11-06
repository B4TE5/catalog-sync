# Decisiones

## 2026-11-06 · Fase 0

- Se trasladó `profiles.yaml` a `config/profiles.yaml` conservando su contenido. El archivo suministrado estaba en la raíz. Se descartó duplicarlo para evitar dos fuentes de configuración.
- Se fijó Python a la serie 3.12 y la caché de uv a `.uv-cache` mediante `UV_CACHE_DIR` durante la sesión. La caché predeterminada ya había fallado con el error de acceso 5.
