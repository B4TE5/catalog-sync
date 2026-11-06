# PLAN_FASE2.md — vinted-hunter, sesión 2 (nube + móvil)

Mismas reglas de AGENTS.md §0 (autónomo, sin preguntas, DECISIONS/BLOCKERS/WORKLOG, commits por tarea, verificación real).
Leyenda: `[ ]` pendiente · `[x]` hecho · `[!]` bloqueado.

Credenciales disponibles en `.env` (gitignored, NUNCA commitear ni imprimir en logs):
`GH_TOKEN` (fine-grained, solo este repo), `GITHUB_REPO` (owner/catalog-sync — usa exactamente este; el repo ya existe, público y vacío), `NTFY_TOPIC`, `NTFY_HEALTH_TOPIC`, `BOARD_KEY` (clave del tablero cifrado; genérala tú si no existe: 32 bytes aleatorios en base64url, guárdala en .env y como secret).

## F2.0 — Rendimiento y prioridad (antes de subir a la nube)
- [x] Las descargas de fotos (CDN de imágenes, host distinto de vinted.es) NO usan la pausa de 3–8 s; concurrencia 4 con timeout y reintento. La pausa humana se mantiene solo para páginas de vinted.es.
- [x] Cola de enriquecimiento con prioridad: anuncios NUEVOS de esta pasada primero (más recientes y más baratos respecto al tope), y el backlog del backfill después con lo que sobre de presupuesto. Un anuncio fresco nunca espera detrás del backlog.
- [x] Medir de nuevo: tiempo por candidato y por pasada → DECISIONS.md. Objetivo: pasada normal < 3 min.
**Hecho cuando:** test de prioridad en verde y medición documentada.

## F2.1 — Viabilidad de GitHub Actions (puerta de todo lo demás)
- [ ] Subir el repo local a `GITHUB_REPO` (ya creado, público y vacío) usando GH_TOKEN como variable de entorno; nunca dentro de la URL del remote ni en .git/config. Verificar antes que .gitignore excluye data/, out/, .env, scratch/.venv, cachés.
- [ ] Workflow `probe.yml` (workflow_dispatch): instala con uv, ejecuta `vh doctor` y una búsqueda real; imprime HTTP status y nº de anuncios parseados. Lanzarlo 3 veces separadas ≥ 5 min y leer resultados vía API.
- [ ] Si alguna da 403/429 sistemático o 0 anuncios → `[!]`, documentar en BLOCKERS.md con evidencia, y saltar a F2.3 implementando ntfy para el modo local (`vh watch` en el PC). No insistir con trucos de evasión.
**Hecho cuando:** 3/3 ejecuciones en Actions devuelven 200 y ≥ 10 anuncios.

## F2.2 — Ejecución programada y estado
- [ ] `hunt.yml`: cron `*/10 * * * *` + workflow_dispatch; `concurrency: {group: hunt, cancel-in-progress: false}`; `timeout-minutes: 8`; `permissions` mínimos; todas las actions fijadas por SHA; caché de uv.
- [ ] Estado persistente: base SQLite comprimida en una rama huérfana `state`, publicada como **un único commit con force-push** en cada pasada (sin historial que crezca). Restaurar al inicio, guardar al final, también si la pasada falla a medias (paso `if: always()` con escritura atómica).
- [ ] Comprobar y documentar si esa actividad evita que GitHub desactive el cron a los 60 días; si no está claro, añadir un keepalive mensual en main.
- [ ] Tablero publicado en GitHub Pages (`actions/deploy-pages`) tras cada pasada, **cifrado**: los datos (JSON) van cifrados con AES-GCM (clave derivada con PBKDF2/scrypt de `BOARD_KEY`, secret del repo); el HTML publicado solo contiene el blob cifrado + el código de descifrado (WebCrypto). La clave se pasa en el **fragmento de la URL** (`#k=...`), que el navegador nunca envía al servidor; sin clave, la página muestra solo una pantalla neutra sin datos ni marcas. `vh board-url` imprime la URL completa con la clave (solo en local). Nada de tokens ni del topic de ntfy en el HTML. Título y metadatos de la página genéricos (sin "Vinted" ni marcas). Añadir `<meta name="robots" content="noindex,nofollow">`.
- [ ] Nombres neutros: ni el repo, ni los workflows, ni el README, ni el título del tablero mencionan nombres de marcas ni la lista de búsqueda.
- [ ] `shadow_mode: true` en `config/scoring.yaml` por defecto.
**Hecho cuando:** 3 ejecuciones programadas seguidas en verde, el estado persiste entre ellas (la 2.ª y la 3.ª no reportan como nuevos los anuncios ya vistos) y la URL de Pages muestra el tablero actualizado.

## F2.3 — Notificaciones ntfy
- [ ] `NtfyNotifier` (implementa `Notifier`), con secrets `NTFY_TOPIC` / `NTFY_HEALTH_TOPIC` (en Actions como secrets del repo; en local desde .env).
- [ ] Mensaje: título `🔥 Stone Island crewneck gris XL · 48 € (51 total) · 82`, cuerpo con 2–3 motivos y "subida hace X min", foto adjunta (URL), `Click` = URL https del anuncio, botón "Tablero" (URL de Pages), prioridad por tier (top=5/urgent, good=4, negociable=3).
- [ ] Reglas: solo tiers top/good (y negociable ≥ 75); nunca dos avisos del mismo anuncio salvo `price_drop` 📉; en `shadow_mode` NO se envían avisos de anuncios (solo salud).
- [ ] Salud: aviso al topic de salud tras 3 pasadas fallidas seguidas (403/429/parser_suspect/excepción), **una sola vez por incidencia**, y aviso de "recuperado" al volver a verde.
- [ ] `vh notify-test` envía un aviso de prueba realista (con un anuncio real del tablero) a cada topic. Ejecutarlo una vez y anotarlo.
**Hecho cuando:** tests del notifier en verde (sin red, con mock HTTP) y `vh notify-test` devuelve 200 de ntfy en ambos topics.

## F2.4 — Feedback desde el tablero (sin tokens en el cliente)
- [ ] Botones Fake / Buena / No me interesa en cada tarjeta → abren `https://github.com/<repo>/issues/new?title=label:<listing_id>:<fake|good|meh>` prellenado.
- [ ] Workflow `feedback.yml` (`on: issues: opened`): solo acepta si `github.event.issue.user.login == github.repository_owner` (el dueño del repo; ignora y cierra el resto sin procesar); valida el formato estrictamente; aplica la etiqueta al estado (fake → lista negra pHash); comenta el resultado y cierra el issue. Concurrencia compartida con `hunt` para no pisar el estado.
**Hecho cuando:** un issue de prueba del dueño se procesa y cierra solo, y uno con formato inválido se rechaza sin tocar el estado (test + prueba real).

## F2.5 — Cierre
- [ ] README actualizado (arquitectura nube, cómo activar avisos: `shadow_mode: false`, cómo etiquetar).
- [ ] Revisión de seguridad: secrets nunca en logs (buscar en los logs de Actions), permisos mínimos por workflow, actions por SHA, issues solo del dueño.
- [ ] Actualizar SESSION_REPORT.md, TEST_REPORT.md, BLOCKERS.md; WORKLOG al día; último commit y push.

## NO hacer
Proxies de pago, evasión agresiva de antibots, Wallapop, modelos de IA, desactivar shadow_mode.
