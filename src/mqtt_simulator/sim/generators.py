"""Stateful value generators used by inline JSON payloads."""

from __future__ import annotations

import copy
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from ..errors import PayloadBuildError


class ValueGenerator(Protocol):
    """Protocol for stateful generators that emit one value per publish."""

    def next_value(self) -> Any:
        """Return the next generated value."""


def build_value_generator(spec: dict[str, Any], *, rng: random.Random) -> ValueGenerator:
    """Build a stateful generator from a validated single-operator spec."""

    if len(spec) != 1:
        raise PayloadBuildError("Generator specs must contain exactly one operator")

    operator, data = next(iter(spec.items()))
    if operator == "toggle":
        return BoolToggleGenerator(value=bool(data))
    if operator == "walk":
        return NumberWalkGenerator.from_spec(data)
    if operator == "random":
        return NumberRandomGenerator.from_spec(data, rng=rng)
    if operator == "pick":
        return ChoiceGenerator.from_spec(data, rng=rng)
    if operator == "seq":
        return SequenceGenerator.from_spec(data)
    if operator == "expr":
        return ExpressionGenerator.from_spec(str(data), rng=rng)
    if operator == "time":
        return TimestampGenerator.from_spec(str(data))
    if operator == "uuid":
        return UUIDGenerator()
    if operator == "counter":
        return CounterGenerator.from_spec(data)
    if operator == "null":
        return NullGenerator()
    raise PayloadBuildError(f"Unsupported generator operator: {operator}")


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
        """Construct a walk generator from validated options."""

        minimum = float(data["min"])
        maximum = float(data["max"])
        step = float(data["step"])
        number_type = str(data["type"])
        current = float(data["start"])
        if minimum > maximum:
            raise PayloadBuildError("walk min must be <= max")
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
        """Construct a random-number generator from validated options."""

        minimum = float(data["min"])
        maximum = float(data["max"])
        if minimum > maximum:
            raise PayloadBuildError("random min must be <= max")
        number_type = str(data["type"])
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
    def from_spec(cls, values: list[Any], *, rng: random.Random) -> ChoiceGenerator:
        """Construct a choice generator."""

        return cls(values=list(values), rng=rng)

    def next_value(self) -> Any:
        """Return a random choice."""

        return copy.deepcopy(self.rng.choice(self.values))


@dataclass(slots=True)
class SequenceGenerator:
    """Return a sequence of configured values."""

    values: list[Any]
    loop: bool
    index: int = 0

    @classmethod
    def from_spec(cls, values: list[Any]) -> SequenceGenerator:
        """Construct a sequence generator."""

        return cls(values=list(values), loop=True)

    def next_value(self) -> Any:
        """Return the next sequence value."""

        if self.index >= len(self.values):
            if not self.loop:
                return self.values[-1]
            self.index = 0
        value = self.values[self.index]
        self.index += 1
        return copy.deepcopy(value)


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
    def from_spec(cls, expression: str, *, rng: random.Random) -> ExpressionGenerator:
        """Construct an expression generator."""

        if not expression.strip():
            raise PayloadBuildError("expr generator requires a non-empty expression")
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
    def from_spec(cls, mode: str) -> TimestampGenerator:
        """Construct a timestamp generator."""

        if mode not in {"iso", "unix"}:
            raise PayloadBuildError("time generator mode must be 'iso' or 'unix'")
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


@dataclass(slots=True)
class CounterGenerator:
    """Emit a monotonically increasing numeric counter."""

    current: float
    step: float

    @classmethod
    def from_spec(cls, data: dict[str, Any]) -> CounterGenerator:
        """Construct a counter generator from validated options."""

        return cls(current=float(data["start"]), step=float(data["step"]))

    def next_value(self) -> int | float:
        """Return the current counter value and advance."""

        value = self.current
        self.current += self.step
        if float(value).is_integer() and float(self.step).is_integer():
            return int(value)
        return value


@dataclass(slots=True)
class NullGenerator:
    """Emit JSON null values."""

    def next_value(self) -> None:
        """Return a null-like value."""

        return None
