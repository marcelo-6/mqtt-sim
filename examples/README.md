<!-- markdownlint-disable MD033 -->
# Example Library

Every config in this folder uses the current TOML schema and is intentionally
commented.

## Quick Start

Validate an example:

```bash
uv run mqtt-sim validate -c examples/basic.toml
```

Run an example for a short session:

```bash
uv run mqtt-sim run -c examples/basic.toml --duration 10
```

Most examples target a local broker at `localhost:1883`. Start one quickly with
Mosquitto:

```bash
docker run --rm -it -p 1883:1883 eclipse-mosquitto
```

## Start Here

| File | What it demonstrates |
| --- | --- |
| [`basic.toml`](./basic.toml) | The smallest useful config: one broker, one client, one expanding stream, and one inline JSON payload |
| [`many_streams.toml`](./many_streams.toml) | Shows mixed stream templates, both `list` and `range` expansion, and a text `sequence` payload |
| [`industrial/packaging_line_advanced.toml`](./industrial/packaging_line_advanced.toml) | Best advanced showcase for lifecycle messages, nested JSON, templated client ids, and richer schedules |
| [`file_transfer/binary_payload_examples.toml`](./file_transfer/binary_payload_examples.toml) | Quick tour of `bytes`, `file`, and `pickle` payload kinds |
| [`pickle_file.toml`](./pickle_file.toml) | `pickle_file` payload (publishes raw file bytes, no unpickling) |

## Domain

<details>

<summary>Smart Home</summary>

### Smart Home

| File | Highlights |
| --- | --- |
| [`smart_home/home_climate_and_lighting.toml`](./smart_home/home_climate_and_lighting.toml) | Thermostat, lights, humidity, occupancy, `expr`, `toggle`, and mixed numeric generators |
| [`smart_home/access_and_security.toml`](./smart_home/access_and_security.toml) | Door lock, garage door, motion, doorbell events, window contact, and JSON `sequence` payloads |
| [`smart_home/energy_devices.toml`](./smart_home/energy_devices.toml) | Smart plug, EV charger, solar inverter, battery, and grid telemetry |

![home_climate_and_lighting](../docs/images/examples/home_climate_and_lighting.gif)
![access_and_security](../docs/images/examples/access_and_security.gif)
![energy_devices](../docs/images/examples/energy_devices.gif)

</details>

<details>

<summary>Wearables</summary>

### Wearables

| File | Highlights |
| --- | --- |
| [`wearables/fitness_trackers.toml`](./wearables/fitness_trackers.toml) | One template expanded across multiple trackers with `expr`, `walk`, and fleet-style topics |
| [`wearables/smartwatch_health_streams.toml`](./wearables/smartwatch_health_streams.toml) | SpO2, stress, sleep, activity, GPS, `uuid`, and timestamp generators |

![fitness_trackers](../docs/images/examples/fitness_trackers.gif)
![smartwatch_health_streams](../docs/images/examples/smartwatch_health_streams.gif)

</details>


<details>

<summary>Connected Appliances</summary>

### Connected Appliances

| File | Highlights |
| --- | --- |
| [`appliances/kitchen_appliances.toml`](./appliances/kitchen_appliances.toml) | Fridge, oven, dishwasher, coffee machine, and microwave state streams |
| [`appliances/laundry_room.toml`](./appliances/laundry_room.toml) | Washer and dryer cycle state, leak sensor, vibration, and room telemetry |

![kitchen_appliances](../docs/images/examples/kitchen_appliances.gif)
![laundry_room](../docs/images/examples/laundry_room.gif)

</details>

<details>

<summary>Industrial</summary>

### Industrial

| File | Highlights |
| --- | --- |
| [`industrial/machine_condition_monitoring.toml`](./industrial/machine_condition_monitoring.toml) | Vibration, bearing temp, RPM, power draw, and machine-state telemetry |
| [`industrial/environmental_conditions.toml`](./industrial/environmental_conditions.toml) | One template expanded across multiple zones with ambient telemetry |
| [`industrial/line_station_status.toml`](./industrial/line_station_status.toml) | Station state machine, cycle time, rejects, throughput, and alarm events |
| [`industrial/packaging_line_advanced.toml`](./industrial/packaging_line_advanced.toml) | Lifecycle messages, templated clients, nested JSON, `fixed-rate`, and `burst` schedules |

![machine_condition_monitoring](../docs/images/examples/machine_condition_monitoring.gif)
![environmental_conditions](../docs/images/examples/environmental_conditions.gif)
![line_station_status](../docs/images/examples/line_station_status.gif)

</details>

<details>

<summary>Pharma / Bioprocess</summary>

### Pharma / Bioprocess

| File | Highlights |
| --- | --- |
| [`pharma/bioreactor_core_signals.toml`](./pharma/bioreactor_core_signals.toml) | Bioreactor temperature, pH, dissolved oxygen, agitation, and batch state |
| [`pharma/pumps_valves_and_flows.toml`](./pharma/pumps_valves_and_flows.toml) | Pumps, valves, line pressure, flow, and transfer-state telemetry |
| [`pharma/uv_and_process_skid.toml`](./pharma/uv_and_process_skid.toml) | UV absorbance, process temperatures, flow rates, and skid state machines |

![bioreactor_core_signals](../docs/images/examples/bioreactor_core_signals.gif)
![pumps_valves_and_flows](../docs/images/examples/pumps_valves_and_flows.gif)
![uv_and_process_skid](../docs/images/examples/uv_and_process_skid.gif)

</details>

<details>

<summary>ML / Inference</summary>

### ML / Inference

| File | Highlights |
| --- | --- |
| [`ml/inference_results_stream.toml`](./ml/inference_results_stream.toml) | Inference outputs, latency, routing decisions, service health, and batch summaries |
| [`ml/model_monitoring_and_drift.toml`](./ml/model_monitoring_and_drift.toml) | Drift scores, feature stats, distributions, route mix, and alerting |

![inference_results_stream](../docs/images/examples/inference_results_stream.gif)
![model_monitoring_and_drift](../docs/images/examples/model_monitoring_and_drift.gif)

</details>

<details>

<summary>File Transfer / Binary Payloads</summary>

### File Transfer / Binary Payloads

| File | Highlights |
| --- | --- |
| [`file_transfer/file_drop_events.toml`](./file_transfer/file_drop_events.toml) | Metadata, status, checksum, retry, and completion event streams |
| [`file_transfer/binary_payload_examples.toml`](./file_transfer/binary_payload_examples.toml) | `bytes` (`utf8` / `hex` / `base64`), `file`, and `pickle` payload kinds |
| [`file_transfer/chunked_transfer_simulation.toml`](./file_transfer/chunked_transfer_simulation.toml) | Session start, chunk metadata, raw chunk bytes, ACKs, and completion |

![file_drop_events](../docs/images/examples/file_drop_events.gif)
![binary_payload_examples](../docs/images/examples/binary_payload_examples.gif)
![chunked_transfer_simulation](../docs/images/examples/chunked_transfer_simulation.gif)

</details>

<details>

<summary>Shared Data Files</summary>

## Shared Data Files

These fixture files are referenced by the file and binary payload examples:

| File | Used by |
| --- | --- |
| [`data/sample.pkl`](./data/sample.pkl) | [`pickle_file.toml`](./pickle_file.toml), [`file_transfer/binary_payload_examples.toml`](./file_transfer/binary_payload_examples.toml) |
| [`data/sample.bin`](./data/sample.bin) | [`file_transfer/binary_payload_examples.toml`](./file_transfer/binary_payload_examples.toml) |
| [`data/firmware_chunk_001.bin`](./data/firmware_chunk_001.bin) | [`file_transfer/chunked_transfer_simulation.toml`](./file_transfer/chunked_transfer_simulation.toml) |

</details>

## Notes

- Most examples keep a single named client because that is easier to read and copy into a new config.
- `pickle_file` publishes raw bytes from disk. It does not unpickle.