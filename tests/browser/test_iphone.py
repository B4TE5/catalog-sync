import os
from pathlib import Path
from urllib.parse import quote, urldefrag

import pytest
from playwright.sync_api import sync_playwright

from vinted_hunter.cloud import require_key
from vinted_hunter.secrets import board_address

ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.browser


def test_iphone_preserves_private_fragment_across_reload() -> None:
    public = os.environ.get("VH_BROWSER_URL") or board_address(ROOT)
    if public is None:
        pytest.skip("Se requiere el tablero configurado")
    private = public + "#k=" + quote(require_key(ROOT), safe="")
    failure = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch()
            device = dict(playwright.devices["iPhone 13"])
            device.pop("default_browser_type", None)
            context = browser.new_context(**device)
            page = context.new_page()
            page.route("https://**/*", lambda route: route.continue_()
                       if route.request.is_navigation_request()
                       and urldefrag(route.request.url).url == public else route.abort())
            page.goto(private, wait_until="domcontentloaded")
            page.frame_locator("iframe").locator("#cards").wait_for(timeout=30000)
            preserved = page.url == private
            assert preserved, "El descifrado debe conservar el fragmento"
            assert page.locator('link[rel="manifest"]').count() == 0
            page.reload(wait_until="domcontentloaded")
            page.frame_locator("iframe").locator("#cards").wait_for(timeout=30000)
            preserved = page.url == private
            assert preserved, "La recarga debe conservar el fragmento"
            # Entrada desde el botón público: el respaldo restaura la URL completa.
            page.goto(public, wait_until="domcontentloaded")
            page.frame_locator("iframe").locator("#cards").wait_for(timeout=30000)
            preserved = page.url == private
            assert preserved, "La clave de respaldo debe restaurar el fragmento"
            # El enlace sigue funcionando aunque se pierda la copia de localStorage.
            page.evaluate("localStorage.clear()")
            page.reload(wait_until="domcontentloaded")
            page.frame_locator("iframe").locator("#cards").wait_for(timeout=30000)
            preserved = page.url == private
            assert preserved
            page.get_by_role("button", name="Olvidar clave en este dispositivo").click()
            page.get_by_text("Abre el enlace con su clave.").wait_for(timeout=30000)
            assert not page.evaluate("Boolean(location.hash)")
            browser.close()
    except Exception as error:
        # Los errores de navegación de Playwright pueden incluir la URL privada.
        failure = type(error).__name__
    if failure:
        # Fuera de except para impedir que pytest publique la excepción original.
        pytest.fail(f"Verificación iPhone fallida: {failure}", pytrace=False)
