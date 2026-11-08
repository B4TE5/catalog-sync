"""Anonimización obligatoria de cuerpos HTTP destinados a fixtures."""

import json
import re
from typing import Any

PUBLIC_JWT = re.compile(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
SENSITIVE_NAME = (
    r"(?:authorization|proxy-authorization|cookies?|set-cookie|[a-z0-9_-]*token|"
    r"[a-z0-9_-]*api[_-]?key|(?:x-)?session[_-]?(?:id|key)|password|secret)"
)
SENSITIVE = re.compile(r"(?i)^" + SENSITIVE_NAME + r"$")
PUSH = re.compile(r"(self\.__next_f\.push\()(.+?)(\)\s*</script>)", re.DOTALL)
SECRET_KEY = re.compile(r'(?i)("' + SENSITIVE_NAME + r'"\s*:\s*)')
HEADER = re.compile(
    r"(?im)^((?:authorization|proxy-authorization|cookie|set-cookie|"
    r"x-csrf-token|x-session-id|x-auth-token|x-session-token):)[^\r\n]*"
)
URL_SECRET = re.compile(
    r"(?i)([?&](?:access_token|refresh_token|token|api_key|session_id|signature)=)[^&\s\"'<>\\]+"
)


def _text(value: str) -> str:
    value = PUBLIC_JWT.sub(b"REDACTED", value.encode()).decode()
    parts = []
    cursor = 0
    for match in SECRET_KEY.finditer(value):
        if match.start() < cursor:
            continue
        try:
            _, length = json.JSONDecoder().raw_decode(value[match.end():])
        except json.JSONDecodeError:
            continue
        parts.append(value[cursor:match.end()] + '"REDACTED"')
        cursor = match.end() + length
    value = "".join(parts) + value[cursor:]
    value = HEADER.sub(r"\1 REDACTED", value)
    return URL_SECRET.sub(r"\1REDACTED", value)


def _tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "REDACTED" if SENSITIVE.fullmatch(key) else _tree(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [_tree(item) for item in value]
    return _text(value) if isinstance(value, str) else value


def sanitize_fixture(body: bytes) -> bytes:
    """Conserva datos públicos del parser y retira credenciales y cabeceras."""
    text = body.decode("utf-8")
    try:
        return json.dumps(_tree(json.loads(text)), ensure_ascii=False).encode()
    except json.JSONDecodeError:
        pass

    def push(match: re.Match[str]) -> str:
        try:
            parsed = _tree(json.loads(match[2]))
        except json.JSONDecodeError:
            return _text(match[0])
        return match[1] + json.dumps(parsed, ensure_ascii=False) + match[3]

    return _text(PUSH.sub(push, text)).encode()
