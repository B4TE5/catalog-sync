"""Presentación del resumen en consola."""

from typing import Any

from rich.console import Console

from vinted_hunter.notify.base import Notifier


class ConsoleNotifier(Notifier):
    def publish(self, summary: dict[str, Any]) -> None:
        Console().print(
            f"{summary['requests']} peticiones · {summary['seen']} vistos · "
            f"{summary['new']} nuevos · {summary['candidates']} candidatos · "
            f"{summary['scored']} puntuados · {summary['duration']:.1f} s",
        )
        for error in summary["errors"]:
            Console().print(f"[red]{error}[/red]", highlight=False)
