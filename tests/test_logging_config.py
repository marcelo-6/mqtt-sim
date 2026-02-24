from __future__ import annotations

import logging

from mqtt_simulator.logging_config import configure_logging, shutdown_logging


def test_configure_logging_creates_file_and_writes_records(tmp_path) -> None:
    ctx = configure_logging(verbose=True, output_mode="log", log_dir=tmp_path / "logs")
    logger = logging.getLogger("mqtt_simulator.test")
    logger.info("hello from test")
    shutdown_logging()

    content = ctx.log_path.read_text(encoding="utf-8")

    assert ctx.log_path.exists()
    assert "hello from test" in content
