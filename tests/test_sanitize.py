import gzip
import json
from pathlib import Path

from vinted_hunter.sanitize import sanitize_fixture
from vinted_hunter.sources.vinted.catalog import parse_catalog


def test_sanitizer_preserves_real_catalog_and_embedded_rsc() -> None:
    path = Path(__file__).parent / "fixtures/catalog-parent.html.gz"
    body = gzip.decompress(path.read_bytes())
    before = parse_catalog(body.decode())
    after = parse_catalog(sanitize_fixture(body).decode())
    assert [row.model_dump() for row in before.listings] == [
        row.model_dump() for row in after.listings
    ]


def test_sanitizer_removes_headers_opaque_tokens_and_nested_cookies() -> None:
    raw = json.dumps({
        "headers": {"Cookie": "private-cookie", "Authorization": "Bearer private-auth"},
        "access_token": "opaque-access", "cookies": [{"value": "cookie-value"}],
        "token": "generic-opaque", "clientToken": "client-opaque",
        "value": 'Cookie: secret-line\nhttps://example.org/?token=secret-query&ok=1',
    }).encode()
    clean = sanitize_fixture(raw)
    for secret in (b"private-cookie", b"private-auth", b"opaque-access", b"cookie-value",
                   b"secret-line", b"secret-query", b"generic-opaque", b"client-opaque"):
        assert secret not in clean
    embedded = '<script>self.__next_f.push([1,' + json.dumps(raw.decode()) + '])</script>'
    for secret in (b"private-cookie", b"private-auth", b"opaque-access", b"cookie-value"):
        assert secret not in sanitize_fixture(embedded.encode())
