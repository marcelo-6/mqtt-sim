"""Stateful value generators used by ``json_fields`` payloads."""

from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from ..config.models import KindedSpec
from ..errors import PayloadBuildError


class ValueGenerator(Protocol):
    """Protocol for stateful generators that emit one value per publish."""

    def next_value(self) -> Any:
        """Return the next generated value."""


def build_value_generator(spec: KindedSpec, *, rng: random.Random) -> ValueGenerator:
    """Build a stateful generator from a generic kinded spec."""

    kind = spec.kind
    data = _spec_data(spec)
    if kind == "const":
        return ConstGenerator(value=data.get("value"))
    if kind == "bool_toggle":
        return BoolToggleGenerator(value=bool(data.get("start", False)))
    if kind == "number_walk":
        return NumberWalkGenerator.from_spec(data)
    if kind == "number_random":
        return NumberRandomGenerator.from_spec(data, rng=rng)
    if kind == "choice":
        return ChoiceGenerator.from_spec(data, rng=rng)
    if kind == "sequence":
        return SequenceGenerator.from_spec(data)
    if kind == "expression":
        return ExpressionGenerator.from_spec(data, rng=rng)
    if kind == "timestamp":
        return TimestampGenerator.from_spec(data)
    if kind == "uuid":
        return UUIDGenerator()
    raise PayloadBuildError(f"Unsupported generator kind: {kind}")


def _spec_data(spec: KindedSpec) -> dict[str, Any]:
    """Return a flat spec dictionary including extra keys."""

    dumped = spec.model_dump(mode="python")
    return dumped


@dataclass(slots=True)
class ConstGenerator:
    """Return a constant value every time."""

    value: Any

    def next_value(self) -> Any:
        """Return the configured constant."""
        return self.value


@dataclass(slots=True)
class BoolToggleGenerator:
    """Toggle a boolean value on every publish."""

    value: bool = False

    def next_value(self) -> bool:
        """Return the current value and flip it for the next call."""
        current = self.value
        self.value = not self.value
        return current


@dataclass(slots=True)
class NumberWalkGenerator:
    """Walk a numeric value back and forth within a min/max range."""

    minimum: float
    maximum: float
    step: float
    number_type: str = "float"
    current: float | None = None
    direction: int = 1

    @classmethod
    def from_spec(cls, data: dict[str, Any]) -> NumberWalkGenerator:
        """Construct a walk generator from a generic spec dict."""

        minimum = float(data.get("min", 0))
        maximum = float(data.get("max", 100))
        step = float(data.get("step", 1))
        if step <= 0:
            raise PayloadBuildError("number_walk step must be > 0")
        number_type = str(data.get("numeric_type", "float"))
        start = data.get("start")
        current = float(start) if start is not None else minimum
        if minimum > maximum:
            raise PayloadBuildError("number_walk min must be <= max")
        return cls(
            minimum=minimum,
            maximum=maximum,
            step=step,
            number_type=number_type,
            current=current,
        )

    def next_value(self) -> int | float:
        """Return the next stepped value and reverse at bounds."""

        assert self.current is not None
        value = self.current
        next_value = value + (self.step * self.direction)
        if next_value > self.maximum or next_value < self.minimum:
            self.direction *= -1
            next_value = value + (self.step * self.direction)
            next_value = min(self.maximum, max(self.minimum, next_value))
        self.current = next_value
        if self.number_type == "int":
            return int(round(value))
        return float(value)


@dataclass(slots=True)
class NumberRandomGenerator:
    """Emit random numbers inside a configured range."""

    minimum: float
    maximum: float
    number_type: str
    precision: int | None
    rng: random.Random = field(repr=False)

    @classmethod
    def from_spec(
        cls, data: dict[str, Any], *, rng: random.Random
    ) -> NumberRandomGenerator:
        """Construct a random-number generator from spec data."""

        minimum = float(data.get("min", 0))
        maximum = float(data.get("max", 100))
        if minimum > maximum:
            raise PayloadBuildError("number_random min must be <= max")
        number_type = str(data.get("numeric_type", "float"))
        precision = data.get("precision")
        return cls(
            minimum=minimum,
            maximum=maximum,
            number_type=number_type,
            precision=int(precision) if precision is not None else None,
            rng=rng,
        )

    def next_value(self) -> int | float:
        """Return a random number in range."""

        if self.number_type == "int":
            return self.rng.randint(int(self.minimum), int(self.maximum))
        value = self.rng.uniform(self.minimum, self.maximum)
        if self.precision is not None:
            value = round(value, self.precision)
        return value


@dataclass(slots=True)
class ChoiceGenerator:
    """Choose one value at random from a list."""

    values: list[Any]
    rng: random.Random = field(repr=False)

    @classmethod
    def from_spec(cls, data: dict[str, Any], *, rng: random.Random) -> ChoiceGenerator:
        """Construct a choice generator."""

        values = data.get("values")
        if not isinstance(values, list) or not values:
            raise PayloadBuildError("choice generator requires a non-empty values list")
        return cls(values=list(values), rng=rng)

    def next_value(self) -> Any:
        """Return a random choice."""

        return self.rng.choice(self.values)


@dataclass(slots=True)
class SequenceGenerator:
    """Return a sequence of configured values."""

    values: list[Any]
    loop: bool
    index: int = 0

    @classmethod
    def from_spec(cls, data: dict[str, Any]) -> SequenceGenerator:
        """Construct a sequence generator."""

        values = data.get("values")
        if not isinstance(values, list) or not values:
            raise PayloadBuildError(
                "sequence generator requires a non-empty values list"
            )
        loop = bool(data.get("loop", True))
        return cls(values=list(values), loop=loop)

    def next_value(self) -> Any:
        """Return the next sequence value."""

        if self.index >= len(self.values):
            if not self.loop:
                return self.values[-1]
            self.index = 0
        value = self.values[self.index]
        self.index += 1
        return value


@dataclass(slots=True)
class ExpressionGenerator:
    """Evaluate a small expression with previous value and RNG context.

    This is intentionally limited and uses ``eval`` with restricted globals.
    It is a pragmatic first implementation, not a fully sandboxed expression
    engine, and should be treated as trusted-config functionality.
    """

    expression: str
    rng: random.Random = field(repr=False)
    prev: Any = None
    count: int = 0

    @classmethod
    def from_spec(
        cls, data: dict[str, Any], *, rng: random.Random
    ) -> ExpressionGenerator:
        """Construct an expression generator."""

        expression = data.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise PayloadBuildError(
                "expression generator requires a non-empty expression"
            )
        return cls(expression=expression, rng=rng)

    def next_value(self) -> Any:
        """Evaluate the expression and store the returned value as ``prev``."""

        local_vars = {
            "prev": self.prev,
            "count": self.count,
            "random": self.rng.random(),
            "randint": self.rng.randint,
            "uniform": self.rng.uniform,
            "time": time.time(),
        }
        try:
            value = eval(  # noqa: S307
                self.expression,
                {"__builtins__": {}, "math": math},
                local_vars,
            )
        except Exception as exc:  # pragma: no cover - exact errors vary by expression
            raise PayloadBuildError(f"expression generator failed: {exc}") from exc
        self.prev = value
        self.count += 1
        return value


@dataclass(slots=True)
class TimestampGenerator:
    """Generate timestamps in ISO8601 or UNIX seconds format."""

    mode: str = "iso"

    @classmethod
    def from_spec(cls, data: dict[str, Any]) -> TimestampGenerator:
        """Construct a timestamp generator."""

        mode = str(data.get("mode", "iso"))
        if mode not in {"iso", "unix"}:
            raise PayloadBuildError("timestamp generator mode must be 'iso' or 'unix'")
        return cls(mode=mode)

    def next_value(self) -> str | int:
        """Return the current timestamp in the configured format."""

        now = datetime.now(UTC)
        if self.mode == "unix":
            return int(now.timestamp())
        return now.isoformat()


@dataclass(slots=True)
class UUIDGenerator:
    """Generate UUID4 strings."""

    def next_value(self) -> str:
        """Return a new UUID string."""

        return str(uuid.uuid4())
