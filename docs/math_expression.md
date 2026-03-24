# Expression Generator (`expr`)

This page documents the inline JSON expression generator used by the current
TOML schema.

For the full schema, see [configuration.md](./configuration.md). For a
commented real-world example, see
[`examples/smart_home/home_climate_and_lighting.toml`](../examples/smart_home/home_climate_and_lighting.toml).

## Where Expressions Live

Expressions live inside `[streams.payload.json]` as a single inline operator:

```toml
[[streams]]
client = "main"
topic = "lab/reactor/temperature"
every = "1s"

[streams.payload.json]
temperature_c = { expr = "round((prev or 21.5) + uniform(-0.15, 0.15), 2)" }
```

The same format works in nested JSON tables too:

```toml
[streams.payload.json.metrics]
drift_score = { expr = "round((prev or 0.02) + uniform(-0.005, 0.01), 4)" }
```

## Required Format

`expr` must be:

- an inline table
- with exactly one operator
- where the operator is `expr`
- and the value is a non-empty string

Valid:

```toml
signal = { expr = "count * 5" }
```

Invalid:

```toml
signal = { expr = "" }
signal = { expr = "count * 5", random = { type = "int", min = 1, max = 3 } }
```

## Available Names

Expressions run with a restricted evaluation context. These names are available:

| Name | Type | Description |
| --- | --- | --- |
| `prev` | any | Previous generated value for this field (`None` on the first run) |
| `count` | integer | Number of values already generated for this field |
| `random` | number | Random float in `[0, 1)` |
| `randint` | function | Random integer helper |
| `uniform` | function | Random float helper |
| `time` | number | Current UNIX time in seconds |
| `math` | module | Python `math` module |

Notes:

- `prev` and `count` are stateful per resolved field generator.
- each resolved stream gets its own generator state
- random behavior participates in the simulator seed flow when you set `seed`

## Useful Patterns

Simple ramp:

```toml
[streams.payload.json]
step_value = { expr = "count * 5" }
```

Jitter around the previous value:

```toml
[streams.payload.json]
temperature_c = { expr = "round((prev or 100) + uniform(-1.5, 1.5), 2)" }
```

Wave-like signal:

```toml
[streams.payload.json]
signal = { expr = "round(50 + 10 * math.sin(count / 5), 2)" }
```

Wall-clock-derived phase:

```toml
[streams.payload.json]
phase = { expr = "round(math.sin(time), 4)" }
```

## Practical Example

```toml
[[streams]]
name = "ambient_sensor"
client = "main"
topic = "building/floor-1/ambient"
every = "1s"

[streams.payload.json]
temperature_c = { expr = "round((prev or 21.5) + uniform(-0.15, 0.15), 2)" }
humidity_pct = { random = { type = "float", min = 35, max = 55, precision = 1 } }
ts = { time = "iso" }
```

This keeps `temperature_c` near the previous reading while still drifting over
time.

## Trust Model

The current implementation evaluates expressions with Python `eval(...)` using:

- restricted builtins
- a small explicit context (`math`, `prev`, `count`, random helpers, and `time`)

That makes accidental access harder, but expressions are still
trusted-config functionality. Treat them like code:

- only run expressions from trusted users or repos
- review expressions before using them in production-like environments

## Troubleshooting

If an expression fails, the simulator reports it in:

- log output
- the table renderer `ERR` column
- the file log at `.mqtt-sim/logs/mqtt-sim.log`

Common causes:

- syntax errors in the expression string
- using names that are not available in the expression context
- math domain errors
- mixing incompatible types when `prev` is still `None`

Tips:

- use `(prev or <default>)` when referencing `prev`
- start small, then add complexity
- validate the whole config first:

```shell
uv run mqtt-sim validate -c examples/smart_home/home_climate_and_lighting.toml
```

Schema validation happens during `validate`; runtime expression failures show up
when you `run` the simulator.
