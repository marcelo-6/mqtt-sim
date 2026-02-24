# MQTT Simulator

A MQTT simulator for publishing to a broker by simulating sensors, devices, and senarios.

[Features](#features) •
[Getting Started](#getting-started) •
[Configuration](#configuration) •
[History and Alternatives](#history-and-alternatives)

![Simulator Running](docs/images/simulator-running.gif)

## Features

* Easy to configure simulator for publishing data to an MQTT broker
* Simple setup with a single JSON configuration file
* Publish data on predefined fixed topics
* Publish data on multiple topics that have a variable id or items at the end
* Simulated random variation of data based on configurable parameters
* Inline updating terminal table output for simulator status (with logs)

## Getting Started

### Running using uv

Run the simulator with [uv](https://github.com/astral-sh/uv):

```shell
uv sync --dev
uv run mqtt-sim run -c examples/new/basic.json
```

### Running using Python

> `uv` Recommended instead

Run the simulator with a config file (`examples/new/basic.json`):

```shell
PYTHONPATH=src python3 -m mqtt_simulator run -c examples/new/basic.json
```

Validate a config before running:

```shell
PYTHONPATH=src python3 -m mqtt_simulator validate -c examples/new/basic.json
```

To install all dependencies with a virtual environment before using:

```shell
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
pip3 install -e .
```

### Running using Docker

Additionally, you can run the simulator via [Docker](https://docs.docker.com/get-docker/) using the provided `Dockerfile`.

Build the image:

```shell
docker build -t mqtt-simulator .
```

Run the container:

```shell
docker run mqtt-simulator -c examples/new/basic.json
```

## Configuration

See the [configuration documentation](./docs/configuration.md) for the current schema and configurable options.

Expression generator details (for `json_fields` payloads) are documented in:

- [docs/math_expression.md](./docs/math_expression.md)

For the schema used by the CLI, start with:

- [examples/new/basic.json](./examples/new/basic.json)
- [examples/new/many_streams.json](./examples/new/many_streams.json)
- [examples/new/pickle_file.json](./examples/new/pickle_file.json)

Below is a minimal configuration file for the implementation. It uses a single broker and range expansion to publish JSON payloads generated from multiple field generators:

```json
{
  "schema_version": 1,
  "brokers": [
    {
      "name": "main",
      "host": "broker.hivemq.com",
      "port": 1883
    }
  ],
  "streams": [
    {
      "broker": "main",
      "topic": "site/{id}/status",
      "interval": 2.0,
      "expand": {
        "kind": "range",
        "var": "id",
        "start": 1,
        "stop": 3
      },
      "payload": {
        "kind": "json_fields",
        "fields": [
          { "name": "ok", "generator": { "kind": "bool_toggle", "start": true } },
          { "name": "temp", "generator": { "kind": "number_random", "numeric_type": "float", "min": 20, "max": 40, "precision": 1 } }
        ]
      }
    }
  ]
}
```

## History and Alternatives

There are already great MQTT tools for quickly publish something to a MQTT broker, but most of them solve a different problem than this project.

A big inspiration here is the original [DamascenoRafael/mqtt-simulator](https://github.com/DamascenoRafael/mqtt-simulator) project that I forked from. I wanted a quick way to simulate various types of devices and payloads close to the real devices I use at work.

Another big inspiration is [EdJoPaTo/mqttui](https://github.com/EdJoPaTo/mqttui), which is a fantastic Rust TUI for MQTT. It is fast, ergonomic, and great for interactive MQTT work in the terminal.

Before that, tools like [MQTT Explorer](https://github.com/thomasnordquist/MQTT-Explorer), [EasyMQTT](https://www.easymqtt.app/), and [`mosquitto_pub` / `mosquitto_sub`](https://mosquitto.org/) were all useful depending on the situation. There are also feature-rich CLI options like [HiveMQ MQTT CLI](https://github.com/hivemq/mqtt-cli) and [MQTTX CLI](https://mqttx.app/docs/cli/get-started). They are great tools, but for my use case they are too complex. I wanted something simple.

That’s why this project exists: a MQTT simulator focused on generating many configurable payload streams (including file/binary payloads) with a inline status view. It is not trying to replace `mqttui` or other MQTT clients/viewers, it is focused on simulation.
