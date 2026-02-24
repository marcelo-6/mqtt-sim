"""Rich inline table renderer used as the default TTY output mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import time
from typing import TextIO, Iterable

from rich.console import Console, RenderableType
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich import box
from rich.panel import Panel


# Common-ish states sample
_STATE_BADGES: dict[str, tuple[str, str]] = {
    "running": ("bright_green", "▶"),
    "publishing": ("bright_green", "▶"),
    "ready": ("cyan", "●"),
    "idle": ("cyan", "●"),
    "sleeping": ("yellow", "⏸"),
    "paused": ("yellow", "⏸"),
    "stopped": ("bright_black", "■"),
    "done": ("bright_green", "✔"),
    "error": ("bright_red", "✖"),
    "failed": ("bright_red", "✖"),
}


@dataclass(slots=True)
class TableRenderer:
    """Render runtime snapshots as an inline-updating table."""

    stream: TextIO | None = None
    _console: Console = field(init=False, repr=False)
    _live: Live | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        """Create the console and initialize live rendering state."""
        # Let Rich auto-detect color/TTY; your CLI can pick this renderer only when isatty() is true.
        self._console = Console(file=self.stream, highlight=False)

    def start(self, snapshot) -> None:
        """Start the Rich live display."""
        if self._live is None:
            self._live = Live(
                self._build_table(snapshot),
                console=self._console,
                refresh_per_second=8,
                transient=False,  # keep the final table on screen
            )
            self._live.start()
        else:
            self._live.update(self._build_table(snapshot))

    def update(self, snapshot) -> None:
        """Update the live table with the latest snapshot."""
        if self._live is None:
            self.start(snapshot)
            return
        self._live.update(self._build_table(snapshot))

    def finish(self, snapshot, result) -> None:
        """Render the final table state and a short footer summary."""
        if self._live is not None:
            self._live.update(self._build_table(snapshot))
            self._live.stop()
            self._live = None

        status = "failed-fast" if getattr(result, "failed_fast", False) else "done"
        border = "bright_red" if status != "done" else "bright_green"
        status_style = "bold bright_red" if status != "done" else "bold bright_green"

        body = (
            f"[{status_style}]{status}[/]\n"
            f"[bold]published[/]=[bright_green]{result.total_publishes}[/]   "
            f"[bold]errors[/]=[bright_red]{result.total_errors}[/]   "
            f"[bold]duration[/]=[cyan]{result.duration_seconds:.2f}s[/]"
        )
        self._console.print(Panel(body, border_style=border, padding=(1, 2)))

    def close(self) -> None:
        """Stop the live renderer if it is running."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _build_table(self, snapshot) -> Table:
        """Build the current rich table for a runtime snapshot."""
        now = time.time()

        table = Table(
            title=self._build_title(snapshot),
            caption=self._build_caption(snapshot),
            box=box.ROUNDED,
            border_style="bright_blue",
            header_style="bold white",
            title_style="bold bright_white",
            caption_style="dim",
            show_lines=False,
            row_styles=["", "dim"],
            expand=True,
            pad_edge=False,
        )

        table.add_column("Topic", style="cyan", overflow="ellipsis", ratio=2)
        table.add_column("State", style="white", no_wrap=True)
        table.add_column("Interval", style="magenta", justify="right", no_wrap=True)
        table.add_column(
            "Count", style="bold bright_green", justify="right", no_wrap=True
        )
        table.add_column("Last Pub.", style="bright_black", no_wrap=True)
        table.add_column("Payload", style="white", overflow="ellipsis", ratio=3)
        table.add_column("Error", style="bright_red", overflow="ellipsis", ratio=None)

        for s in snapshot.streams:
            cells = self._row(s, now)
            row_style = "bold bright_red" if getattr(s, "last_error", "") else ""
            table.add_row(*cells, style=row_style)

        return table

    def _build_title(self, snapshot) -> Text:
        """Build the table title with overall runtime counts."""
        streams = len(snapshot.streams)
        pub = snapshot.total_publishes
        err = snapshot.total_errors

        title = Text("MQTT Simulator", style="bold bright_white")
        title.append("  ")
        title.append(f"streams={streams}", style="bold cyan")
        title.append("  ")
        title.append(f"published={pub}", style="bold bright_green")
        title.append("  ")
        title.append(f"errors={err}", style="bold bright_red" if err else "bold green")
        return title

    def _build_caption(self, snapshot) -> Text:
        """Small, low-noise hint line under the table."""
        # Adjust/remove if you prefer no caption.
        return Text("Live view updates in-place. Errors highlight rows.", style="dim")

    def _row(self, stream, now: float) -> tuple[RenderableType, ...]:
        """Format one stream status row for the table."""
        state_cell = _format_state(getattr(stream, "state", ""))
        last_pub = _format_ts(getattr(stream, "last_publish_ts", None), now)

        return (
            Text(str(stream.topic)),
            state_cell,
            Text(f"{stream.interval:.2f}s"),
            Text(str(stream.publish_count)),
            Text(last_pub),
            Text(str(stream.last_payload_preview or "-")),
            Text(str(stream.last_error or "-")),
        )


def _format_state(state: str) -> Text:
    """Return a colored badge for a stream state."""
    key = (state or "").strip().lower()
    color, icon = _STATE_BADGES.get(key, ("white", "•"))
    txt = Text()
    txt.append(icon + " ", style=color)
    txt.append(state if state else "-", style=f"bold {color}")
    return txt


def _format_ts(value: float | None, now: float) -> str:
    """Format a wall-clock timestamp with an 'ago' suffix."""
    if value is None:
        return "-"
    dt = datetime.fromtimestamp(value).strftime("%H:%M:%S")
    ago = max(0.0, now - value)
    if ago < 60:
        return f"{dt} ({ago:>4.1f}s)"
    mins = int(ago // 60)
    secs = int(ago % 60)
    return f"{dt} ({mins}m{secs:02d}s)"
