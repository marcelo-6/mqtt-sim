# MQTT Simulator - Expression Generator (`json_fields`)

This page documents the expression generator used inside `json_fields`
payloads.

For the full configuration schema, see [configuration.md](./configuration.md).

## Where Expressions Live in the Schema

Expressions are configured as a generator inside a `json_fields` payload field:

```json
{
  "payload": {
    "kind": "json_fields",
    "fields": [
      {
        "name": "temperature",
        "generator": {
          "kind": "expression",
          "expression": "(prev or 21) + uniform(-0.2, 0.2)"
        }
      }
    ]
  }
}
```

## Required Keys

For the expression generator itself:

- `kind: "expression"`
- `expression` (non-empty string)

If `expression` is missing or empty, payload building fails with a clear runtime error.

## Available Names in the Expression Context

The simulator evaluates the expression with a restricted context. These names are available:

| Name | Type | Description |
| --- | --- | --- |
| `prev` | any | Previous generated value for this field (`None` on first run) |
| `count` | integer | Number of values already generated for this field |
| `random` | number | Random float in `[0, 1)` |
| `randint` | function | Random integer function |
| `uniform` | function | Random float function |
| `time` | number | Current UNIX time in seconds |
| `math` | module | Python `math` module |

Notes:

- `prev` and `count` are stateful per generator instance.
- Each resolved stream gets its own generator state.
- Random behavior participates in the simulator seed flow (`--seed`), so runs can be more reproducible.

## How State Works (`prev` and `count`)

The generator stores:

- `prev`: the last computed result
- `count`: how many times the expression has run

This makes it easy to build:

- ramps
- bounded random walks
- smoothing / inertia-like values
- sequence-like state machines

Example (simple ramp):

```json
{
  "kind": "expression",
  "expression": "count * 5"
}
```

Example (jitter around previous value):

```json
{
  "kind": "expression",
  "expression": "(prev or 100) + uniform(-1.5, 1.5)"
}
```

Example (sine wave-ish signal):

```json
{
  "kind": "expression",
  "expression": "20 + 5 * math.sin(count / 10)"
}
```

## Practical Examples

### Example 1 - Temperature Drift with Noise

```json
{
  "kind": "json_fields",
  "fields": [
    {
      "name": "temperature",
      "generator": {
        "kind": "expression",
        "expression": "round((prev or 21.5) + uniform(-0.15, 0.15), 2)"
      }
    }
  ]
}
```

This keeps temperature near the previous value and adds small random drift.

### Example 2 - Periodic Signal

```json
{
  "kind": "json_fields",
  "fields": [
    {
      "name": "signal",
      "generator": {
        "kind": "expression",
        "expression": "round(50 + 10 * math.sin(count / 5), 2)"
      }
    }
  ]
}
```

This uses `count` as the progression variable and `math.sin(...)` for a wave-like pattern.

### Example 3 - Timestamp-Derived Value

```json
{
  "kind": "json_fields",
  "fields": [
    {
      "name": "phase",
      "generator": {
        "kind": "expression",
        "expression": "round(math.sin(time), 4)"
      }
    }
  ]
}
```

This uses wall-clock time directly. It is less deterministic than `count`-based expressions.

## Safety / Trust Model (Important)

The current implementation evaluates expressions using Python `eval(...)` with:

- restricted builtins (`__builtins__` removed)
- a small explicit context (`math`, `prev`, `count`, random helpers, `time`)

This reduces accidental access to Python internals, but it is still **trusted-config functionality**.

Treat expression configs as code-like input:

- only use expressions from trusted users/sources
- review expressions before running in production-like environments

## Troubleshooting Expression Errors

If an expression fails, the simulator records a payload/generator error and shows it in:

- log mode output (`ERROR ...`)
- table `ERR` column
- file log at `.mqtt-sim/logs/mqtt-sim.log`

Common causes:

- syntax errors in the expression string
- calling names that are not available in the expression context
- math domain errors (for example invalid square root input)
- mixing incompatible types (`prev` starts as `None`)

Tips:

- use `(prev or <default>)` when referencing `prev`
- start with simple expressions, then add complexity
- validate the full config first:

```shell
uv run mqtt-sim validate -c examples/new/basic.json
```

Note: `validate` checks schema structure, but expression execution errors appear during `run`.
