# MQTT Simulator

## Overview

The MQTT Simulator is a Python-based simulator designed to simulate the sending of JSON objects from sensors or devices to an MQTT broker. The simulator uses configurable topics and data, allowing for flexible simulation of various sensor types (e.g., analog values such as temperature, pressure etc, discrete values, raw data, and mathematical expressions). It can be used for testing MQTT-based systems, simulating sensor networks, or stress testing MQTT brokers.

## Features

- **Configurable Topics**: Support for single, multiple, and list-based topics, each with custom data types (e.g., float, bool, raw values, math expressions).
- **MQTT Support**: Simulates MQTT messages and publishes them to an MQTT broker at configurable intervals.
- **Data Types**: Support for numeric ranges, boolean values with configurable probabilities, raw data values, and mathematical expressions.
- **Client Settings**: Adjustable MQTT client settings, including `QoS`, `retain`, `clean session`, and `time interval` between messages.
- **Threaded Simulation**: Each topic runs in its own thread to simulate parallel sensor networks.

## TODOs
# Add make file
# Add/fix docker compose / DockerFile
# Cleaup and doctring

## Getting Started

To get started with the MQTT Simulator, follow the steps below:

### Prerequisites

- Python 3.6 or higher
- A running MQTT broker (e.g., [Mosquitto](https://mosquitto.org/), [HiveMQ](https://www.hivemq.com/))
- Install the necessary dependencies using uv:

```bash
uv install
```

### Setting Up

1. Clone this repository:

2. Create your `settings.json` file. This file will contain the configuration for the topics you want to simulate, as well as the MQTT broker details.

3. Update the `settings.json` file with your topic and broker configurations (explained below).

4. Run the simulator:

```bash
uv run app/main.py
```

The simulator will start sending data to the configured MQTT broker at the specified intervals.

## `settings.json` Configuration

The `settings.json` file allows you to configure the MQTT broker and define the topics you want to simulate. Below is an explanation of the fields available in the `settings.json` file:

### Example `settings.json`

```json
{
  "BROKER_URL": "localhost",
  "BROKER_PORT": 1883,
  "PROTOCOL_VERSION": 4,
  "TOPICS": [
    {
      "TYPE": "single",
      "PREFIX": "sensors/temperature",
      "DATA": [
        {
          "NAME": "temp_value",
          "TYPE": "float",
          "MIN_VALUE": 10,
          "MAX_VALUE": 30
        }
      ],
      "PAYLOAD_ROOT": {
        "sensor": "temperature_sensor"
      },
      "CLEAN_SESSION": true,
      "RETAIN": false,
      "QOS": 1,
      "TIME_INTERVAL": 5
    },
    {
      "TYPE": "multiple",
      "PREFIX": "sensors/boolean_values",
      "DATA": [
        {
          "NAME": "status",
          "TYPE": "bool",
          "TRUE_PROBABILITY": 0.7
        }
      ],
      "PAYLOAD_ROOT": {
        "sensor": "status_sensor"
      },
      "CLEAN_SESSION": true,
      "RETAIN": false,
      "QOS": 1,
      "TIME_INTERVAL": 5
    }
  ]
}
```

### Settings Breakdown

- **BROKER_URL**: The URL or IP address of the MQTT broker. (e.g., `localhost` or `mqtt.example.com`)
- **BROKER_PORT**: The port used by the MQTT broker. Default is `1883`.
- **PROTOCOL_VERSION**: The MQTT protocol version to use. The default is `4` for MQTTv3.1.1. If you need MQTTv5, change it to `5`.
  
### Topics

The `TOPICS` array defines the list of topics that the simulator will use. Each topic object has the following properties:

- **TYPE**: Type of the topic:
  - `single`: A single topic with the format `/PREFIX`
  - `multiple`: Multiple topics with the format `/PREFIX/{id}`, where `id` is a range of integers.
  - `list`: A list of topics with the format `/PREFIX/{item}`, where `item` is a list of custom values.
  
- **PREFIX**: The base name for the topic (e.g., `sensors/temperature` or `sensors/boolean_values`).
  
- **DATA**: The data associated with the topic. This is an array of objects defining the data's type and other properties. Each data object contains:
  - **NAME**: The name of the data (e.g., `temp_value`).
  - **TYPE**: The type of data:
    - `float`: A floating-point number.
    - `int`: An integer.
    - `bool`: A boolean value.
    - `raw_values`: Custom raw data.
    - `math_expression`: A mathematical expression that will be evaluated (e.g., `2 * x + 5`).
  - **MIN_VALUE**: Minimum value for numeric types (only for `float` and `int`).
  - **MAX_VALUE**: Maximum value for numeric types (only for `float` and `int`).
  - **TRUE_PROBABILITY**: Probability of the boolean being `True` (only for `bool`).
  - **VALUE**: Custom raw value (only for `raw_values`).
  - **EXPRESSION**: The math expression to evaluate (only for `math_expression`).

- **PAYLOAD_ROOT**: The base structure of the payload that will be sent along with the topic data. This is optional and can be used to add additional metadata to each published message.

### Client Settings

- **CLEAN_SESSION**: Whether to use a clean session for the MQTT client (true/false).
- **RETAIN**: Whether the message should be retained by the broker (true/false).
- **QOS**: The Quality of Service level (0, 1, or 2).
- **TIME_INTERVAL**: The interval (in seconds) between each message publication.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Forked from

https://github.com/DamascenoRafael/mqtt-simulator