"""Rich inline table renderer used as the default TTY output mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TextIO

from rich.console import Console
from rich.live import Live
from rich.table import Table

from ..runtime.models import RuntimeResult, RuntimeSnapshot, StreamStatus


@dataclass(slots=True)
class TableRenderer:
    """Render runtime snapshots as an inline-updating table."""

    stream: TextIO | None = None
    _console: Console = field(init=False, repr=False)
    _live: Live | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        """Create the console and initialize live rendering state."""

        self._console = Console(file=self.stream)

    def start(self, snapshot: RuntimeSnapshot) -> None:
        """Start the Rich live display."""

        if self._live is None:
            self._live = Live(
                self._build_table(snapshot),
                console=self._console,
                refresh_per_second=8,
            )
            self._live.start()
        else:
            self._live.update(self._build_table(snapshot))

    def update(self, snapshot: RuntimeSnapshot) -> None:
        """Update the live table with the latest snapshot."""

        if self._live is None:
            self.start(snapshot)
            return
        self._live.update(self._build_table(snapshot))

    def finish(self, snapshot: RuntimeSnapshot, result: RuntimeResult) -> None:
        """Render the final table state and a short footer summary."""

        if self._live is not None:
            self._live.update(self._build_table(snapshot))
        status = "failed-fast" if result.failed_fast else "done"
        self._console.print(
            f"\n{status}: published={result.total_publishes} "
            f"errors={result.total_errors} duration={result.duration_seconds:.2f}s"
        )

    def close(self) -> None:
        """Stop the live renderer if it is running."""

        if self._live is not None:
            self._live.stop()
            self._live = None

    def _build_table(self, snapshot: RuntimeSnapshot) -> Table:
        """Build the current rich table for a runtime snapshot."""

        table = Table(title=self._build_title(snapshot))
        table.add_column("TOPIC", overflow="fold")
        table.add_column("STATE")
        table.add_column("INTERVAL", justify="right")
        table.add_column("COUNT", justify="right")
        table.add_column("LAST PUB")
        table.add_column("PAYLOAD", overflow="fold")
        table.add_column("ERR", overflow="fold")
        for stream in snapshot.streams:
            table.add_row(*self._row(stream))
        return table

    def _build_title(self, snapshot: RuntimeSnapshot) -> str:
        """Build the table title with overall runtime counts."""

        return (
            "MQTT Simulator "
            f"(streams={len(snapshot.streams)} published={snapshot.total_publishes} "
            f"errors={snapshot.total_errors})"
        )

    def _row(self, stream: StreamStatus) -> tuple[str, str, str, str, str, str, str]:
        """Format one stream status row for the table."""

        return (
            stream.topic,
            stream.state,
            f"{stream.interval:.2f}s",
            str(stream.publish_count),
            _format_ts(stream.last_publish_ts),
            stream.last_payload_preview,
            stream.last_error,
        )


def _format_ts(value: float | None) -> str:
    """Format a wall-clock timestamp for the table."""

    if value is None:
        return "-"
    return datetime.fromtimestamp(value).strftime("%H:%M:%S")
