# Configuration

This page documents the current TOML configuration schema used by the `mqtt-sim` CLI.

Quick Navigation:
[Quick Start](#quick-start) •
[Top Level](#top-level) •
[Brokers](#brokers) •
[Protocol Notes](#protocol-notes) •
[Clients](#clients) •
[Streams](#streams) •
[QoS and Retain](#qos-and-retain) •
[Schedule Modes](#schedule-modes) •
[Payload Types](#payload-types) •
[JSON Generators](#json-generators)

## Quick Start

Start with the TOML example:

- [`examples/basic.toml`](../examples/basic.toml)
- The broader example library in [`examples/README.md`](../examples/README.md)
  uses the same schema.

Validate a config without connecting to a broker:

```shell
uv run mqtt-sim validate -c examples/basic.toml
```

Run the simulator:

```shell
uv run mqtt-sim run -c examples/basic.toml
```

Minimal example:

```toml
config_version = 1

[brokers.main]
host = "localhost"
port = 1883

[clients.main]
broker = "main"
id = "sim-${device_id}"

[[streams]]
client = "main"
topic = "devices/${device_id}/status"
every = "1s"

[streams.expand]
device_id = { range = [1, 3] }

[streams.payload.json]
device_id = "${device_id}"
ok = { toggle = true }
temperature_c = { random = { type = "float", min = 18, max = 32, precision = 1 } }
```

## Top Level

The root config supports:

- `config_version = 1`
- `name` optional
- `seed` optional
- `[brokers.<name>]`
- `[clients.<name>]`
- `[[streams]]`

Unknown keys are rejected.

## Brokers

Brokers define MQTT transport and connection settings.

```toml
[brokers.main]
host = "localhost"
port = 1883
keepalive = 60
protocol = "3.1.1"
transport = "tcp"

[brokers.main.auth]
username = "demo"
password_env = "MQTT_PASSWORD"

[brokers.main.tls]
enabled = true
ca_file = "/etc/mqtt/ca.pem"
cert_file = "/etc/mqtt/client.crt"
key_file = "/etc/mqtt/client.key"
```

Supported broker fields:

- `host` required
- `port` optional, default `1883`
- `keepalive` optional, default `60`
- `protocol` optional, `"3.1.1"` or `"5.0"`
- `transport` optional, `"tcp"` or `"websockets"`
- `auth` optional
- `tls` optional

## Protocol Notes

The simulator can connect with either:

- `protocol = "3.1.1"`
- `protocol = "5.0"`

> [!IMPORTANT]
> Nothing in the current config schema is MQTT 5-only.
> Stream publishing, lifecycle messages, QoS, retain, Last Will, TLS, and the
> payload system all work with both MQTT `3.1.1` and MQTT `5.0`.
>
> In other words: using `qos = 1`, `qos = 2`, or `lifecycle.will` does not mean
> you need `protocol = "5.0"`.

So when should you set `protocol = "5.0"`?

- when your broker is configured for MQTT 5
- when you want the simulator connection itself to use MQTT 5 semantics
- when you are testing against infrastructure that expects MQTT 5 clients

> [!NOTE]
> The current schema does not expose MQTT 5-specific publish features like user
> properties, message expiry, response topics, or MQTT 5 reason-code handling.
> In practice, `protocol = "5.0"` is mostly about connection compatibility right
> now, not extra per-message config knobs.

One small naming detail:

- `clean_session = true/false` is the config field in both protocols
- under MQTT `3.1.1`, it is passed through as `clean_session`
- under MQTT `5.0`, the simulator maps that same setting to the client's
  `clean_start` behavior during connect

## Clients

Clients define MQTT session identity and optional lifecycle messages.

```toml
[clients.line_station]
broker = "main"
id = "line-${line_id}-cell-${cell_id}"
clean_session = true

[clients.line_station.lifecycle.online]
topic = "plant/${line_id}/${cell_id}/lifecycle"
retain = true
qos = 1

[clients.line_station.lifecycle.online.payload.json]
state = "online"
ts = { time = "unix" }
```

Supported client fields:

- `broker` required, references `[brokers.<name>]`
- `id` required
- `clean_session` optional, default `true`
- `lifecycle.online` optional
- `lifecycle.offline` optional
- `lifecycle.will` optional

Lifecycle messages use the same inline payload formats as streams.

> [!NOTE]
> `qos` and `retain` inside lifecycle messages behave exactly like they do on
> normal stream publishes. The only special part is when the message is sent.

### Lifecycle behavior

Lifecycle messages are about the MQTT client session itself, not one specific
stream.

- `lifecycle.online`
  Published by `mqtt-sim` right after the client connects successfully.
- `lifecycle.offline`
  Published by `mqtt-sim` during a normal shutdown, before the client
  disconnects.
- `lifecycle.will`
  Configures the broker-side MQTT Last Will and Testament message for that
  client.

That last one is the easy one to misunderstand:

- `will` is not published by the simulator during normal startup or shutdown
- `will` is registered with the broker before the client connects
- if the client disappears unexpectedly, the broker publishes the `will`
  message on the client's behalf
- if the simulator shuts down cleanly, the `will` message is not sent

That makes this a common pattern:

```toml
[clients.line_station.lifecycle.online]
topic = "plant/${line_id}/${cell_id}/lifecycle"
retain = true
qos = 1

[clients.line_station.lifecycle.online.payload.json]
state = "online"
ts = { time = "unix" }

[clients.line_station.lifecycle.offline]
topic = "plant/${line_id}/${cell_id}/lifecycle"
retain = true
qos = 1

[clients.line_station.lifecycle.offline.payload.json]
state = "offline"
reason = "graceful-stop"
ts = { time = "unix" }

[clients.line_station.lifecycle.will]
topic = "plant/${line_id}/${cell_id}/lifecycle"
retain = true
qos = 1

[clients.line_station.lifecycle.will.payload.json]
state = "offline"
reason = "unexpected-disconnect"
ts = { time = "unix" }
```

In plain English:

- on connect, the simulator publishes `online`
- on normal exit, the simulator publishes `offline/graceful-stop`
- on a crash or broken connection, the broker publishes `offline/unexpected-disconnect`

## Streams

Each `[[streams]]` entry defines one publish template.

```toml
[[streams]]
name = "motor_telemetry"
client = "line_station"
topic = "plant/${line_id}/${cell_id}/motor"
every = "500ms"
mode = "fixed-rate"
jitter = "75ms"
qos = 1

[streams.expand]
line_id = { list = ["line-a", "line-b"] }
cell_id = { range = [1, 4] }

[streams.payload.json]
line = "${line_id}"
cell = "${cell_id}"
rpm = { walk = { type = "int", min = 900, max = 1800, step = 50, start = 1100 } }
current_a = { random = { type = "float", min = 2.0, max = 9.8, precision = 2 } }
```

Supported stream fields:

- `name` optional
- `client` required, references `[clients.<name>]`
- `topic` required
- `every` required
- `mode` optional, `fixed-delay`, `fixed-rate`, or `burst`
- `jitter` optional, not allowed for `burst`
- `burst_count` required for `burst`
- `burst_spacing` required for `burst`
- `qos` optional, default `0`
- `retain` optional, default `false`
- `expand` optional
- `payload` required

### QoS and retain

`qos` and `retain` control how the broker handles a publish after the simulator
has built the payload.

#### `qos`

Allowed values are:

- `0`
  At most once. Fastest and cheapest. Good default for disposable telemetry.
- `1`
  At least once. The broker acknowledges the publish, so duplicates are
  possible.
- `2`
  Exactly once. Strongest delivery guarantee, but also the most handshake
  overhead.

The simulator does not emulate the QoS flow itself. It passes the chosen QoS to
the MQTT client library, and the client/broker perform the protocol-level
delivery handshake.

That means:

- higher QoS usually means more reliability
- higher QoS also means more protocol chatter and more latency
- `qos = 1` or `qos = 2` can make fast streams feel less lightweight

Example:

```toml
[[streams]]
client = "main"
topic = "factory/alarm"
every = "1s"
qos = 1

[streams.payload.json]
state = "active"
```

`qos` also works on lifecycle messages:

```toml
[clients.line_station.lifecycle.will]
topic = "plant/${line_id}/${cell_id}/lifecycle"
qos = 1
retain = true
```

#### `retain`

When `retain = true`, the broker stores the last value for that topic and sends
it to future subscribers as the retained message.

Use retain when you want topics to represent the latest known state, for
example:

- device online/offline state
- current thermostat mode
- latest station status

Avoid retain for purely event-like topics unless you really want new
subscribers to immediately receive the last event again.

> [!TIP]
> A common pattern is:
> `retain = true` for state topics and lifecycle topics,
> `retain = false` for transient event streams.

### Schedule Modes

All schedule modes use `every` as the base timing value, but they behave
differently once the simulator is running.

#### `fixed-delay`

This is the default.

After one publish finishes, the simulator waits `every` seconds, applies any
configured `jitter`, and then publishes again.

Use this when you want a simple "publish, wait, publish, wait" loop.

#### `fixed-rate`

This mode tries to hold a steadier cadence.

Instead of waiting `every` seconds after a publish completes, the next publish
is scheduled from the previous due time. In other words, it aims for a clocked
interval instead of a delay-after-work interval.

That means:

- `fixed-rate` is better for telemetry that should look sampled on a cadence
- if a publish runs late, later publishes may happen with less idle time while
  the scheduler catches back up
- `jitter` still works here, and is applied per interval

#### `burst`

Burst mode sends several messages close together, then goes quiet until the
next burst window.

The fields mean:

- `every`
  Time from the start of one burst to the start of the next burst
- `burst_count`
  How many messages are emitted in each burst
- `burst_spacing`
  Delay between messages inside the burst

So this:

```toml
[[streams]]
topic = "plant/alarm"
every = "10s"
mode = "burst"
burst_count = 3
burst_spacing = "250ms"
```

behaves like:

- first message at `t = 0s`
- second message at `t = 0.25s`
- third message at `t = 0.50s`
- next burst starts at `t = 10s`

`burst` does not support `jitter`, because the burst already has its own timing.

### Expansion

Expansion is stream-local and cartesian when multiple variables are present.

Supported operators:

- `device_id = { range = [1, 3] }`
- `device_id = { range = [1, 10, 2] }`
- `site = { list = ["north", "south"] }`

Templates use `${name}` syntax.

## Payload Types

Payloads are always inline and always typed by subtable name.

### `text`

```toml
[streams.payload.text]
value = "hello-${device_id}"
```

### `json`

```toml
[streams.payload.json]
device_id = "${device_id}"
ok = { toggle = true }

[streams.payload.json.metrics]
temp_c = { random = { type = "float", min = 18, max = 32, precision = 1 } }
```

### `sequence`

```toml
[streams.payload.sequence]
format = "json"
loop = true
items = [
  { severity = "info", code = "none", active = false },
  { severity = "critical", code = "e-stop", active = true },
]
```

### `bytes`

```toml
[streams.payload.bytes]
hex = "504c414e542d4f4b"
```

Exactly one of `utf8`, `hex`, or `base64` must be present.

### `file`

```toml
[streams.payload.file]
path = "fixtures/sample.bin"
```

### `pickle`

```toml
[streams.payload.pickle]
path = "fixtures/sample.pkl"
```

`pickle` publishes raw file bytes. It does not unpickle.

## JSON Generators

Dynamic JSON field values are inline tables with exactly one operator.

Supported operators:

- `{ toggle = true }`
- `{ pick = ["idle", "running", "blocked"] }`
- `{ seq = ["closed", "open"] }`
- `{ walk = { type = "int", min = 0, max = 100, step = 5, start = 50 } }`
- `{ random = { type = "float", min = 18, max = 32, precision = 1 } }`
- `{ expr = "(prev or 42.0) + uniform(-0.2, 0.4)" }`
- `{ time = "unix" }`
- `{ uuid = true }`
- `{ counter = { start = 0, step = 1 } }`
- `{ null = true }`

Notes:

- Arrays inside JSON payloads are constant-only in `config_version = 1`.
- Templates use `${name}` syntax, not Python `str.format(...)`.
- Unknown keys are rejected across the schema.
