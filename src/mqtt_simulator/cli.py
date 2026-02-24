"""Typer CLI for the MQTT simulator."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import typer

from .app import prepare_simulation, validate_config_file
from .cli_errors import handle_cli_exception
from .logging_config import configure_logging, shutdown_logging
from .mqtt.paho_adapter import PahoBrokerAdapter
from .render import LogRenderer, OutputMode, TableRenderer, resolve_output_mode
from .runtime.engine import SimulationEngine
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


@app.command()
def validate(
    config: Path = typer.Option(
        ..., "--config", "-c", help="Path to JSON config file."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Enable verbose file logging."
    ),
) -> None:
    """Validate a config file and print a compact summary."""

    logging_ctx = configure_logging(verbose=verbose, output_mode=OutputMode.LOG.value)
    logger = logging_ctx.logger.getChild("cli.validate")
    try:
        _, summary_text = validate_config_file(config)
        logger.info("Config validation succeeded for %s", config)
        typer.echo(summary_text)
        if verbose:
            typer.echo(f"Log file: {logging_ctx.log_path}")
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 - centralized CLI mapping
        result = handle_cli_exception(exc, logger)
        typer.echo(result.message, err=True)
        raise typer.Exit(code=result.exit_code) from exc
    finally:
        shutdown_logging()


@app.command()
def run(
    config: Path = typer.Option(
        ..., "--config", "-c", help="Path to JSON config file."
    ),
    output: str = typer.Option(
        "auto", "--output", help="Output mode: auto, table, or log."
    ),
    seed: int | None = typer.Option(
        None, "--seed", help="Optional deterministic base seed."
    ),
    duration: float | None = typer.Option(
        None,
        "--duration",
        min=0.0,
        help="Optional run duration in seconds for demos/tests.",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast/--keep-going",
        help="Stop on the first stream error (default keeps running other streams).",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Enable verbose file logging."
    ),
) -> None:
    """Run the simulator and render a table (TTY) or log output (non-TTY)."""

    logger = logging.getLogger("mqtt_simulator.cli.run")
    logging_ctx = None
    try:
        is_tty = sys.stdout.isatty()
        resolved_output = resolve_output_mode(output, is_tty=is_tty)
        logging_ctx = configure_logging(
            verbose=verbose, output_mode=resolved_output.value
        )
        logger = logging_ctx.logger.getChild("cli.run")
        if resolved_output is OutputMode.TABLE:
            renderer = TableRenderer()
        else:
            renderer = LogRenderer(verbose=verbose)
        if verbose:
            typer.echo(
                f"Log file: {logging_ctx.log_path}",
                err=(resolved_output is OutputMode.TABLE),
            )

        prepared = prepare_simulation(config, seed=seed, logger=logger)

        def adapter_factory(broker_config):
            return PahoBrokerAdapter(broker_config, logger=logger)

        engine = SimulationEngine(
            brokers=prepared.brokers,
            streams=prepared.streams,
            adapter_factory=adapter_factory,
            renderer=renderer,
            logger=logger.getChild("runtime"),
            fail_fast=fail_fast,
            duration=duration,
        )
        result = asyncio.run(engine.run())
        logger.info(
            "Run finished exit_code=%s publishes=%s errors=%s",
            result.exit_code,
            result.total_publishes,
            result.total_errors,
        )
        if result.exit_code:
            raise typer.Exit(code=result.exit_code)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 - centralized CLI mapping
        result = handle_cli_exception(exc, logger)
        typer.echo(result.message, err=True)
        raise typer.Exit(code=result.exit_code) from exc
    finally:
        if logging_ctx is not None:
            shutdown_logging()


if __name__ == "__main__":
    app()
