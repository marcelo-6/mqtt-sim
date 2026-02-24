"""Log-mode renderer for non-interactive output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TextIO

from rich.console import Console

from ..runtime.models import RuntimeResult, RuntimeSnapshot


@dataclass(slots=True)
class LogRenderer:
    """Emit compact progress and final summaries as plain log lines."""

    stream: TextIO | None = None
    verbose: bool = False
    _console: Console = field(init=False, repr=False)
    _last_seen_counts: dict[str, tuple[int, int]] = field(init=False, repr=False)
    _started: bool = field(init=False, repr=False, default=False)

    def __post_init__(self) -> None:
        """Initialize the Rich console wrapper."""

        self._console = Console(file=self.stream, force_terminal=False)
        self._last_seen_counts: dict[str, tuple[int, int]] = {}

    def start(self, snapshot: RuntimeSnapshot) -> None:
        """Print a one-line session start summary."""

        if self._started:
            return
        self._started = True
        self._console.print(
            f"Starting simulator: streams={len(snapshot.streams)} "
            f"published={snapshot.total_publishes} errors={snapshot.total_errors}"
        )
        self.update(snapshot)

    def update(self, snapshot: RuntimeSnapshot) -> None:
        """Emit error transitions and optional verbose progress lines."""

        for stream in snapshot.streams:
            key = stream.stream_id
            current = (stream.publish_count, stream.error_count)
            previous = self._last_seen_counts.get(key)
            if previous != current:
                self._last_seen_counts[key] = current
                if stream.error_count and (
                    previous is None or previous[1] != stream.error_count
                ):
                    self._console.print(f"ERROR {stream.topic}: {stream.last_error}")
                elif (
                    self.verbose
                    and stream.publish_count
                    and (previous is None or previous[0] != stream.publish_count)
                ):
                    self._console.print(
                        "PUB "
                        f"{stream.topic} count={stream.publish_count} "
                        f"payload={stream.last_payload_preview}"
                    )

    def finish(self, snapshot: RuntimeSnapshot, result: RuntimeResult) -> None:
        """Print the final runtime summary."""

        status = "failed-fast" if result.failed_fast else "done"
        self._console.print(
            f"Finished ({status}): streams={len(snapshot.streams)} "
            f"published={result.total_publishes} errors={result.total_errors} "
            f"duration={result.duration_seconds:.2f}s at "
            f"{datetime.now().isoformat(timespec='seconds')}"
        )

    def close(self) -> None:
        """No-op close method for protocol compatibility."""

        return None
