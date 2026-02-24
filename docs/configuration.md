# Configuration

This page documents the current JSON configuration schema used by the `mqtt-sim` CLI.

Quick Navigation:
[Quick Start](#quick-start) •
[Root Schema](#root-schema) •
[Brokers](#brokers) •
[Streams](#streams) •
[Expansion](#stream-expansion) •
[Payload Kinds](#payload-kinds) •
[`json_fields` Generators](#json_fields-generators) •
[Validation & Troubleshooting](#validation--troubleshooting) •
[Current Limits](#current-limits)

## Quick Start

Start with the shipped examples:

- [`examples/basic.json`](../examples/basic.json)
- [`examples/many_streams.json`](../examples/many_streams.json)
- [`examples/pickle_file.json`](../examples/pickle_file.json)

Validate a config without connecting to a broker:

```shell
uv run mqtt-sim validate -c examples/basic.json
```

Run the simulator:

```shell
uv run mqtt-sim run -c examples/basic.json
```

Minimal example:

```json
{
  "schema_version": 1,
  "brokers": [
    {
      "name": "main",
      "host": "localhost",
      "port": 1883
    }
  ],
  "streams": [
    {
      "broker": "main",
      "topic": "devices/{id}/status",
      "interval": 1.0,
      "expand": {
        "kind": "range",
        "var": "id",
        "start": 1,
        "stop": 3
      },
      "payload": {
        "kind": "json_fields",
        "fields": [
          {
            "name": "ok",
            "generator": { "kind": "bool_toggle", "start": true }
          },
          {
            "name": "temp",
            "generator": {
              "kind": "number_random",
              "numeric_type": "float",
              "min": 20,
              "max": 35,
              "precision": 1
            }
          }
        ]
      }
    }
  ]
}
```

## Root Schema

The root object has three required keys:

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | integer | yes | Must currently be `1` |
| `brokers` | array | yes | Non-empty list of broker objects |
| `streams` | array | yes | Non-empty list of stream templates |

Validation notes:

- `schema_version` must be exactly `1` in the current implementation.
- `brokers` and `streams` must contain at least one item.
- Unknown top-level keys are rejected.

## Brokers

Each broker object defines one MQTT connection target. Streams reference brokers by `name`.

### Broker Fields

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | yes | - | Unique broker identifier used by streams |
| `host` | string | yes | - | Broker hostname or IP |
| `port` | integer | no | `1883` | MQTT broker port |
| `keepalive` | integer | no | `60` | MQTT keepalive seconds |
| `client_id` | string | no | `null` | Optional MQTT client id |
| `username` | string | no | `null` | Optional username |
| `password` | string | no | `null` | Optional password |

### Broker Rules

- Broker names must be unique.
- A stream that references an unknown broker fails validation before any network activity.

## Streams

A stream is a template for one or more publish streams. After optional expansion, each resolved stream
publishes to one topic at a fixed interval.

### Stream Fields

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | no | `null` | Optional stream name used for internal ids |
| `broker` | string | yes | - | Broker `name` to publish through |
| `topic` | string | yes | - | MQTT topic or topic template |
| `interval` | number | yes | - | Publish interval in seconds (`> 0`) |
| `qos` | integer | no | `0` | MQTT QoS (`0`, `1`, `2`) |
| `retain` | boolean | no | `false` | MQTT retain flag |
| `payload` | object | yes | - | Payload spec (see [Payload Kinds](#payload-kinds)) |
| `expand` | object | no | `null` | Optional stream expansion spec (see [Stream Expansion](#stream-expansion)) |

### Topic and Payload Templating

The simulator applies `str.format(...)` templating using the stream expansion context:

- `topic` is templated
- string values inside `payload` are templated recursively

Example:

```json
{
  "topic": "devices/{id}/status",
  "expand": { "kind": "range", "var": "id", "start": 1, "stop": 3 },
  "payload": { "kind": "text", "value": "hello-{id}" }
}
```

This resolves to topics `devices/1/status`, `devices/2/status`, `devices/3/status` and matching
payload strings `hello-1`, `hello-2`, `hello-3`.

If a template references a missing variable, validation fails with an error such as:

- `Missing template variable 'id' in stream template.`

## Stream Expansion

The current implementation supports one expansion spec per stream (`expand`), which means a stream can
use either `range` or `list`, but not nested/cartesian expansion in a single stream.

### `range` Expansion

Expands one stream using an integer range.

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | - | Must be `"range"` |
| `var` | string | yes | - | Template variable name |
| `start` | integer | yes | - | Range start |
| `stop` | integer | yes | - | Range stop |
| `step` | integer | no | `1` | Step (must not be `0`) |
| `inclusive` | boolean | no | `true` | Include the `stop` value if reachable |

Notes:

- Negative `step` values are supported.
- `inclusive: true` is the default behavior.

Example:

```json
{
  "expand": {
    "kind": "range",
    "var": "id",
    "start": 1,
    "stop": 3
  }
}
```

Resolves `id` values: `1`, `2`, `3`.

### `list` Expansion

Expands one stream using a list of values.

| Key | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `kind` | string | yes | - | Must be `"list"` |
| `var` | string | yes | - | Template variable name |
| `values` | array | yes | - | Non-empty list of values |

Example:

```json
{
  "expand": {
    "kind": "list",
    "var": "site",
    "values": ["north", "south", "west"]
  }
}
```

## Payload Kinds

Each stream has a `payload` object with a required `kind`. The payload object is kind-specific.

### `text`

Publishes a UTF-8 string.

Required keys:

- `kind: "text"`
- `value` (string)

Example:

```json
{
  "payload": {
    "kind": "text",
    "value": "hello world"
  }
}
```

### `bytes`

Publishes raw bytes from an inline string using one of three encodings.

Required keys:

- `kind: "bytes"`
- `value` (string)

Optional keys:

- `encoding` (`"utf8"` default, `"hex"`, or `"base64"`)

Examples:

```json
{ "kind": "bytes", "value": "hello", "encoding": "utf8" }
```

```json
{ "kind": "bytes", "value": "68656c6c6f", "encoding": "hex" }
```

### `file`

Publishes file bytes as-is.

Required keys:

- `kind: "file"`
- `path` (string path)

Path behavior:

- Absolute paths are supported.
- Relative paths are resolved relative to the config file directory.

### `pickle_file`

Publishes a `.pkl` (or any file) as raw bytes.

Required keys:

- `kind: "pickle_file"`
- `path` (string path)

Important behavior:

- The simulator **does not unpickle** the file.
- The bytes are read and published as-is.
- Table/log previews show metadata like `<pickle 1234B>` instead of raw bytes.

### `sequence`

Publishes values from a sequence in order.

Required keys:

- `kind: "sequence"`
- `items` (non-empty array)

Optional keys:

- `encoding` (`"text"` default or `"json"`)
- `loop` (`true` default)

Behavior:

- With `loop: true`, the sequence repeats.
- With `loop: false`, the final item is reused after the sequence ends.

### `json_fields`

Builds a JSON object from a list of field generator definitions and publishes it as UTF-8 encoded JSON.

Required keys:

- `kind: "json_fields"`
- `fields` (non-empty array)

Each item in `fields` must contain:

- `name` (string)
- `generator` (object with `kind` and generator-specific keys)

Example:

```json
{
  "payload": {
    "kind": "json_fields",
    "fields": [
      {
        "name": "ok",
        "generator": { "kind": "bool_toggle", "start": true }
      },
      {
        "name": "temp",
        "generator": {
          "kind": "number_random",
          "numeric_type": "float",
          "min": 18,
          "max": 28,
          "precision": 1
        }
      }
    ]
  }
}
```

## `json_fields` Generators

The following generator kinds are currently supported inside `json_fields[].generator`.

### `const`

Always returns the same value.

Keys:

- `kind: "const"`
- `value` (any JSON value)

### `bool_toggle`

Alternates `true`/`false` on each publish.

Keys:

- `kind: "bool_toggle"`
- `start` (optional boolean, default `false`)

### `number_walk`

Walks a numeric value up/down between bounds and reverses direction at the edges.

Keys:

- `kind: "number_walk"`
- `min` (number, default `0`)
- `max` (number, default `100`)
- `step` (number, default `1`, must be `> 0`)
- `numeric_type` (`"float"` default or `"int"`)
- `start` (optional number, defaults to `min`)

Notes:

- `min` must be `<= max`.
- `"int"` output is rounded to an integer before publishing.

### `number_random`

Returns a random number within a configured range.

Keys:

- `kind: "number_random"`
- `min` (number, default `0`)
- `max` (number, default `100`)
- `numeric_type` (`"float"` default or `"int"`)
- `precision` (optional integer, only useful for float mode)

Notes:

- `min` must be `<= max`.
- `"int"` mode uses integer random sampling.

### `choice`

Returns one random item from a list.

Keys:

- `kind: "choice"`
- `values` (non-empty array)

### `sequence`

Returns items in order, optionally looping.

Keys:

- `kind: "sequence"`
- `values` (non-empty array)
- `loop` (optional boolean, default `true`)

### `expression`

Evaluates an expression using a restricted `eval(...)` context. This is a flexible generator for derived values and stateful calculations.

Keys:

- `kind: "expression"`
- `expression` (non-empty string)

Available names in the expression context:

- `prev` (previous generated value, starts as `null`/`None`)
- `count` (number of generated values so far)
- `random` (random float `0..1`)
- `randint` (callable)
- `uniform` (callable)
- `time` (current UNIX time as float)
- `math` (Python `math` module)

Examples:

```json
{ "kind": "expression", "expression": "count * 10" }
```

```json
{ "kind": "expression", "expression": "(prev or 20) + uniform(-0.3, 0.3)" }
```

Safety note:

- This is **trusted-config functionality**. The implementation restricts builtins, but you should still treat expression configs as code-like input authored by trusted users.
- See the [Expression Generator Guide](./math_expression.md) for a deeper walkthrough.

### `timestamp`

Returns the current time in ISO8601 or UNIX-seconds format.

Keys:

- `kind: "timestamp"`
- `mode` (optional `"iso"` default or `"unix"`)

### `uuid`

Returns a UUID4 string.

Keys:

- `kind: "uuid"`

## CLI Behavior

The current CLI commands are:

- `mqtt-sim version`
- `mqtt-sim validate`
- `mqtt-sim run`

### `run` Options (Current)

- `-c, --config PATH`
- `--output auto|table|log`
- `--seed INT`
- `--duration FLOAT`
- `--fail-fast / --keep-going`
- `--verbose`

### Output Modes

- `auto` (default): chooses `table` on TTY and `log` when stdout is not a TTY
- `table`: inline updating table (Rich)
- `log`: line-based progress/errors

Current table columns:

- `TOPIC`
- `STATE`
- `INTERVAL`
- `COUNT`
- `LAST PUB`
- `PAYLOAD`
- `ERR`

### Logging

- File logging is enabled for CLI commands and runtime execution.
- Default log path: `.mqtt-sim/logs/mqtt-sim.log`
- `--verbose` increases file log detail and also enables more detail in log output mode.

### Failure Policy

- `--keep-going` (default): mark errored streams and continue others
- `--fail-fast`: stop the run after the first stream error and return a non-zero exit code

## Validation & Troubleshooting

### Common Validation Errors

Unknown broker reference:

- A stream references a broker name not defined in `brokers`.

Missing template variable:

- A topic or payload string uses `{var}` but the stream expansion does not define `var`.

Unsupported `kind`:

- Payload/generator kinds are validated at runtime build time and will fail with a clear error if unsupported.

Invalid list/range settings:

- Empty `brokers`, `streams`, `fields`, `values`, or invalid `step`/bounds produce validation/build errors.

### Useful Commands

Validate examples:

```shell
uv run mqtt-sim validate -c examples/basic.json
uv run mqtt-sim validate -c examples/many_streams.json
uv run mqtt-sim validate -c examples/pickle_file.json
```

Inspect CLI help:

```shell
uv run mqtt-sim --help
```

Check logs after a run:

```shell
tail -n 100 .mqtt-sim/logs/mqtt-sim.log
```

## Current Limits

The implementation is focused and does not currently include:

- MQTT subscriber/viewer/client UI features
- Cartesian or nested stream expansion (one `expand` spec per stream)
- Plugin system for custom generators
- Iinteractive table controls (sorting/filtering/hotkeys)
