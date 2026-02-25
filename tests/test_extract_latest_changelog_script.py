from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    script_path = Path(".github/scripts/extract_latest_changelog.py")
    spec = importlib.util.spec_from_file_location("extract_latest_changelog", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_select_latest_released_skips_unreleased() -> None:
    module = _load_module()
    changelog = """
# Changelog

## [Unreleased]

- in progress

## [v1.2.3] - 2026-02-25

- shipped

## [v1.2.2] - 2026-02-20

- previous
""".lstrip()

    sections = module.parse_sections(changelog)
    selected = module.select_section(sections)

    assert selected.label == "v1.2.3"
    assert "shipped" in selected.content
    assert "Unreleased" not in selected.content


def test_select_specific_tag_matches_with_or_without_v_prefix() -> None:
    module = _load_module()
    changelog = """
# Changelog

## [1.0.0] - 2026-02-10

- first
""".lstrip()

    sections = module.parse_sections(changelog)

    selected_with_v = module.select_section(sections, target_tag="v1.0.0")
    selected_without_v = module.select_section(sections, target_tag="1.0.0")

    assert selected_with_v.content == selected_without_v.content
