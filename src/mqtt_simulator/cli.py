"""Typer CLI bootstrap for MQTT Simulator."""

import typer

from .version import get_version

app = typer.Typer(help="MQTT Simulator", add_completion=False)


@app.callback()
def main() -> None:
    """MQTT Simulator CLI."""
    return None


@app.command()
def version() -> None:
    """Print the CLI version."""
    typer.echo(get_version())


if __name__ == "__main__":
    app()
