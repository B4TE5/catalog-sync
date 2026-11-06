"""Entrada de la herramienta local."""

from typer import Typer

app = Typer(help="Cazador local de sudaderas en Vinted.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    from importlib.metadata import version as installed_version

    print(installed_version("vinted-hunter"))


@app.callback()
def main() -> None:
    """Captura y analiza anuncios públicos."""
