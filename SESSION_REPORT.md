# Informe de sesión · Corrección 4

2026-11-08T17:36:44.350673+01:00 · Aplicación f95491d. Todas las casillas de CORRECCION_4.md completadas.

## iPhone y clave

El tablero conserva #k= después de descifrar y recargar. Al entrar desde la URL pública de ntfy, un respaldo válido restaura el fragmento completo. localStorage es respaldo; el enlace privado sigue funcionando tras vaciarlo. No existe manifest ni start_url. Olvidar elimina explícitamente el respaldo y el fragmento actual.

Playwright con WebKit e iPhone 13 contra Pages real: apertura privada, recarga, pestaña nueva pública con respaldo, recarga sin almacenamiento y Olvidar aprobados. La prueba final tardó 10,41 s. No se afirma una operación física de Añadir a pantalla de inicio: los accesos antiguos guardados sin clave deben recrearse desde el enlace completo de vh board-url --qr.

## Avisos y calibración

Solo stone-island tiene notify_enabled=true y exige top. Los otros cuatro perfiles siguen capturándose y apareciendo en el tablero. Se niega su preflight y envío, incluso con score 100. Los avisos de salud conservan su comportamiento.

Mención de autenticación: 20 puntos solo en Stone Island; en los demás conserva 10. El recall 10690539539 alcanza top 75: base 40 + Muy bueno 10 + mención de autenticación 20 + cinco fotos 5. No se ha leído un QR: la señal es texto, se mantiene su nombre y no se convierte en Certilogo validado. No se añadieron reglas por ID ni se rebajó el umbral top=75.

Replay contra la ficha real: top 75, estado sold y generaría aviso como nuevo y activo. No se envía un aviso del artículo vendido. Los seis casos reales de precision siguen rejected 0; el otro recall conserva good 70. Las señales almacenadas y tune respetan los pesos específicos al comparar métricas.

## Prueba real de ntfy en Actions

Workflow_dispatch 42497346203 terminó success. Logs: NTFY_TOPIC presente=true, NTFY_HEALTH_TOPIC presente=true, shadow_mode=false y HTTP 200. La comprobación exige también la política Stone Island/top. Recibo real dqFXVsafVMlr, 2026-11-08T16:00:49+00:00, con botón Tablero público sin clave.

El mensaje era una prueba técnica explícita, sin anuncio ni disponibilidad simulada. Las credenciales llegan desde secrets de Actions, no de un .env del runner. La configuración y el notificador no cambiaron entre ese dispatch y la aplicación final. Los workflows usan el token automático de GitHub; el token personal solo administró los comandos locales autorizados.

## Tallas y datos reales

El estado inicial de nube tenía 1.192 pendientes y cero sin talla. No existía una muestra actual de treinta ausencias. Se localizaron 37 IDs distintos realmente pendientes sin talla en snapshots históricos y se comprobaron treinta: 25 fichas HTTP 200 sin size/size_familiar y cinco 404. Quince se localizaron también en el catálogo. Son accesorios, parches, etiquetas o embalajes; no se les inventa talla. El denominador de tallas publicadas en esa cohorte es cero.

Control independiente: treinta prendas pendientes actuales, treinta fichas HTTP 200 con talla publicada y coincidencia catálogo/ficha en 30/30: **100 %**, por encima del objetivo del 95 %. Se mantienen los campos RSC reales itemBox.secondLine/accessibilityLabel y size/size_familiar. La auditoría completa está en evidence/correction4-sizes.json y las capturas representativas en tests/fixtures/c4.

Se corrigieron dos rutas de pérdida de información: una tarjeta sin talla queda unknown hasta leer ficha; refrescar un pendiente con un campo ausente conserva la talla conocida tanto al guardar como al ordenar el enriquecimiento. La cobertura se informa con su muestra real, sin fabricar casos ni respuestas.

SQL final de nube: 8154 registros; 1224 pendientes; 0 sin talla; presencia 100.00%; integrity_check ok. El prioritario está top 75 y sold. El resto del histórico se conserva.

## Iteraciones finales

| Run | Inicio de captura UTC | Peticiones | Vistos | Resultado |
| --- | --- | ---: | ---: | --- |
| 42499449270 | 2026-11-08T16:21:23Z | 37 | 786 | success |
| 42500316506 | 2026-11-08T16:31:39Z | 38 | 779 | success |

Ambas son pasadas normales del coordinador automático, con aplicación f95491d. Restauraron/guardaron SQLite cifrada y publicaron Pages HTTP 200. El estado descargado y el tablero publicado corresponden al mismo run. La prueba manual de ntfy no se cuenta como iteración normal. El coordinador sigue funcionando.

## Pruebas y límites

Ruff limpio; 144 offline, incluidos recall/precision; cuatro live; selftest 8/8 en 83,69 s, 13 peticiones, 480 vistos y una ficha live puntuada sin fallback. Doctor verde, parser 96 y filtros L/XL 96/96. WebKit/iPhone contra Pages real aprobado. Gitleaks escaneó también las nuevas capturas comprimidas sin hallazgos.

La primera prueba WebKit local falló y su excepción mostró el enlace privado en la salida local de la herramienta. Se corrigió el reporte para que solo conserve el tipo de error, fuera del bloque except; el valor no se incorporó a fixtures, informes, Git ni logs de Actions. Se mantuvo la clave existente. El servidor temporal de prueba está detenido.

La ausencia de treinta pendientes actuales sin talla se documenta como diferencia con el supuesto inicial, no como datos inventados. Se completaron treinta comprobaciones históricas y treinta controles actuales. La prueba móvil es emulación WebKit, no un iPhone físico. Los límites anteriores de precio pagado/hora exacta de venta no públicos permanecen fuera de esta corrección.

WORKLOG.md, DECISIONS.md, BLOCKERS.md y TEST_REPORT.md actualizados. Evidencia: evidence/correction4-validation.json.
