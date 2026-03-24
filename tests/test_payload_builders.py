from __future__ import annotations

import base64
import pickle
from pathlib import Path

from mqtt_simulator.config.expand import ResolvedStreamConfig
from mqtt_simulator.config.models import PayloadConfig
from mqtt_simulator.sim.registry import build_payload_builder


def _resolved_stream(payload: dict[str, object], *, stream_id: str = "s1") -> ResolvedStreamConfig:
    return ResolvedStreamConfig(
        stream_id=stream_id,
        name=stream_id,
        client_session_id="session-1",
        client_name="main",
        topic="demo/topic",
        mode="fixed-delay",
        every=0.1,
        jitter=None,
        burst_count=None,
        burst_spacing=None,
        schedule_label="fixed-delay 100ms",
        qos=0,
        retain=False,
        payload=PayloadConfig.model_validate(payload),
        context={},
    )


def test_text_payload_builder_encodes_utf8(tmp_path: Path) -> None:
    builder = build_payload_builder(
        _resolved_stream({"text": {"value": "hello"}}),
        config_dir=tmp_path,
        seed=123,
    )

    result = builder.build()

    assert result.payload_bytes == b"hello"
    assert result.preview == "hello"


def test_bytes_payload_builder_supports_base64(tmp_path: Path) -> None:
    raw = b"\x00\x01demo"
    builder = build_payload_builder(
        _resolved_stream(
            {"bytes": {"base64": base64.b64encode(raw).decode("ascii")}}
        ),
        config_dir=tmp_path,
        seed=1,
    )

    result = builder.build()

    assert result.payload_bytes == raw
    assert result.preview.startswith("<bytes ")


def test_file_and_pickle_payloads_publish_raw_bytes(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "payload.bin"
    pickle_path = data_dir / "payload.pkl"
    file_path.write_bytes(b"abc")
    pickle_payload = {"x": 1}
    pickle_path.write_bytes(pickle.dumps(pickle_payload))

    file_builder = build_payload_builder(
        _resolved_stream({"file": {"path": str(Path("data") / "payload.bin")}}),
        config_dir=tmp_path,
        seed=None,
    )
    pickle_builder = build_payload_builder(
        _resolved_stream({"pickle": {"path": str(Path("data") / "payload.pkl")}}),
        config_dir=tmp_path,
        seed=None,
    )

    file_result = file_builder.build()
    pickle_result = pickle_builder.build()

    assert file_result.payload_bytes == b"abc"
    assert pickle_result.payload_bytes == pickle.dumps(pickle_payload)
    assert pickle_result.preview.startswith("<pickle ")


def test_json_payload_builder_is_seeded_per_stream(tmp_path: Path) -> None:
    payload = {
        "json": {
            "temp": {"random": {"type": "int", "min": 1, "max": 3}},
            "ok": {"toggle": True},
            "metrics": {
                "amps": {"random": {"type": "float", "min": 2.0, "max": 3.0, "precision": 2}}
            },
        }
    }
    builder_a = build_payload_builder(
        _resolved_stream(payload, stream_id="stream-a"),
        config_dir=tmp_path,
        seed=7,
    )
    builder_b = build_payload_builder(
        _resolved_stream(payload, stream_id="stream-a"),
        config_dir=tmp_path,
        seed=7,
    )

    first_a = builder_a.build()
    first_b = builder_b.build()

    assert first_a.payload_bytes == first_b.payload_bytes
    assert first_a.preview.startswith("{")
