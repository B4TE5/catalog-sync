# Informe de sesión · CORRECCION_3

2026-11-08T15:40:43.550211+01:00 · Código de aplicación 4e34ea7.

CORRECCION_3 queda cerrada con todas sus casillas [x] o [!]. La única casilla parcialmente bloqueada es C3.3: el importe pagado y la hora exacta de venta no son públicos. Se implementaron el seguimiento, los eventos, la pestaña Vendidos, el último precio anunciado y los intervalos estimados. Los límites están en BLOCKERS.md.

El replay real de 10690539539 devuelve **good · 65** y «generaría aviso como anuncio nuevo y activo». Su estado real es sold y no recibió aviso. El precio de 60 EUR es inclusivo y el total con comisiones no se usa como tope. Los perfiles activos admiten exactamente nuevo sin etiquetas, muy bueno y nuevo con etiquetas sujeto a sus reglas de precio/vendedor.

## Avisos y bucle real

shadow_mode está desactivado. Stone Island avisa desde good; los otros cuatro perfiles desde top. El preflight comparte sesión/cuota y falla cerrado si no confirma que la ficha está activa. Los anuncios de siete días o más no avisan salvo price_drop. Se confirma la deduplicación tras HTTP 200 para permitir reintentos fallidos.

ntfy aceptó 5 avisos automáticos y un aviso de prueba adicional. Los cinco primeros recibos automáticos se cotejaron con fichas activas; el ejemplo de prueba tenía foto y acción Tablero pública sin clave. No se cuentan mensajes de salud como avisos de prendas.

Estas dos iteraciones normales del coordinador, con el código final, terminaron en verde:

| Run | Inicio de captura UTC | Peticiones | Vistos | Resultado |
| --- | --- | ---: | ---: | --- |
| 42489721321 | 2026-11-08T14:29:08Z | 38 | 820 | success · estado + Pages |
| 42490550896 | 2026-11-08T14:35:36Z | 39 | 853 | success · estado + Pages |

Cada una restauró y guardó SQLite cifrada, generó el artefacto y publicó Pages HTTP 200. Sus logs no contienen los valores de los secretos configurados. La identidad automática del coordinador y los workflows usan GITHUB_TOKEN, con los secretos de ntfy/clave; ningún workflow depende del token personal de administración local. Las pasadas de mantenimiento comparten el bloqueo: sus colas pueden separar el instante de dispatch del inicio de captura. La pasada 42488165596 falló por catalog: Timeout y availability: Timeout, conservó estado y publicó Pages; la siguiente 42488842985 terminó en verde. La incidencia y su recuperación quedan registradas. El coordinador continúa activo.

La captura profunda reveló una cola de 690 Stone Island con 106 XL. La prioridad anterior situaba otras tallas baratas en los doce primeros puestos. Se añadió preferencia de talla tras novedad/perfil, sin descartar candidatas ni usar el catálogo como confirmación de talla para un gate. La comparación reproducible sobre una instantánea real está en evidence/correction3-priority.json.

## Tallas e histórico

| Base | Registros | Sin talla | Sin comprobar | Ausencia real | No disponible |
| --- | ---: | ---: | ---: | ---: | ---: |
| Local inicial | 3210 | 75 | 75 | 0 | 0 |
| Local tras archivo y auditoría | 5196 | 104 | 0 | 89 | 15 |
| Nube antes de C3 | 3644 | 75 | 75 | 0 | 0 |
| Nube final comprobada | 7938 | 35 | 0 | 31 | 4 |

La primera auditoría recuperó 40 de las 75 tallas consultando sus fichas. La unión local recuperó 1586 IDs del archivo y 400 del estado descargado, sin borrar el histórico. Se revisaron también las ausencias añadidas por esa unión. La talla del catálogo se extrae de los campos RSC reales; size_familiar complementa size en ficha. Una talla solo de catálogo se muestra pero no confirma un descarte si la ficha no publica el atributo.

No quedan descartes por talla con valor ausente ni tallas pendientes de comprobar en ninguna base auditada. Las fichas realmente sin talla se muestran como No indicada; las borradas como No disponible. SQL y pasos intermedios están en DECISIONS.md.

La nube conserva los 3610 IDs de la instantánea anterior comparada, además de lo capturado después; integrity_check da ok. Tiene 1204 candidatos a enriquecer, con **cero no-sudaderas identificables pendientes**. Capturar stock no equivale a declarar todos esos candidatos válidos antes de leer ficha, vendedor y fotos.

## Backfill diario y mercado

El recorrido real se completó: **150/150 posiciones**, quince búsquedas activas y páginas 1–10 previstas para cada una. Hubo 107 peticiones profundas nuevas; 41 páginas posteriores se omitieron tras una página vacía real, y las respuestas idénticas disponibles en la pasada se reutilizaron. Inicio observado: 2026-11-08T13:18:14.139097+00:00; fin: 2026-11-08T14:12:03.335419+00:00. Las cuotas siguen en máximo 12 catálogos por pasada y el límite de enriquecimiento configurado, con pausas de 3–8 s. Se guarda y publica cada incremento.

La instalación inicial arrancó el primer recorrido por la tarde. Se corrigió la ventana automática a 03:00–05:00 Europe/Madrid. La continuación es reanudable fuera de la ventana; la verificación manual también conserva el mínimo de 24 h entre inicios. No se antedató ninguna ejecución para aparentar una prueba nocturna.

Hay 15 anuncios activos aceptados de al menos siete días en Negociables. Sus ofertas se refrescan al publicar sin modificar el trace histórico. Top/Buenas muestran solo activos. El inventario conserva 28 vendidos, 0 reservados, 5 borrados y 0 ocultos, incluidos descartados; solo los candidatos aceptados aparecen en Vendidos. Stats y tablero agrupan ventas aceptadas por marca y precio observado. No se crea una media de duración a partir de anuncios encontrados ya vendidos sin transición activa anterior.

## Feedback, móvil y seguridad

Fake bloquea fotos y vendedor, meh revierte y good suma +10 al vendedor. Se verificó sobre una copia aislada de los 5196 registros reales; no se etiquetaron vendedores de producción para simular entrenamiento. Los contadores aparecen globalmente y por perfil/marca. vh tune está preparado, sin activarse: 0/50 etiquetas utilizables; no se generaron etiquetas ni pesos ficticios.

El PNG de board-url --qr contiene la URL completa con #k= y está ignorado. Se decodificó y se abrió Pages real en Chromium móvil 390×844. La clave queda en localStorage, se limpia del fragmento y la acción Tablero de ntfy abre después sin clave. También pasan olvidar clave, purga de clave inválida y localStorage bloqueado. Sin errores JavaScript ni overflow. Se verificó el navegador y el enlace; no se afirma una prueba sobre un iPhone físico.

Gitleaks pasa en Actions con historial completo y gzip; el sanitizador es obligatorio al capturar fixtures. Scratch queda fuera del índice. .env está ignorado y fuera de git status; sus valores no aparecen en .git/config. Todas las categorías y reglas de producto viven por perfil, sin añadir productos ni fuentes.

La revisión automática rechazó exportar una copia cifrada a una rama nueva por no estar autorizados expresamente la exportación y el destino; no se ejecutó. La alternativa mantiene la unión histórica local y conserva la base existente de nube, recuperando stock público por backfill. Se informan ambas bases por separado.

## Pruebas

Ruff limpio; 132 offline; cuatro live; selftest 8/8, 73,33 s y 13 peticiones; doctor en verde. El selftest final puntuó una ficha live (10131292014), sin fallback. Replay prioritario good 65. QA de Pages y QR aprobada. TEST_REPORT.md contiene la salida generada y las comprobaciones adicionales.

Evidencia compacta sin secretos: evidence/correction3-validation.json. Fixtures reales en tests/fixtures/c3; bitácora completa en WORKLOG.md.
