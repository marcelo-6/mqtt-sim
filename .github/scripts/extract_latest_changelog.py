"""Extract a released changelog section for GitHub release notes.

This script reads ``CHANGELOG.md`` and writes one release section (the newest released
entry or a specific tag) to stdout or a file. It intentionally skips the ``Unreleased``
section.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
BRACKETED_VERSION_RE = re.compile(r"^\[(?P<label>[^\]]+)\](?:\s+-\s+.*)?$")


@dataclass(slots=True)
class ChangelogSection:
    """A single level-2 changelog section."""

    heading: str
    label: str
    content: str


def parse_sections(markdown: str) -> list[ChangelogSection]:
    """Return level-2 changelog sections from markdown text."""

    lines = markdown.splitlines()
    sections: list[ChangelogSection] = []
    current_heading: str | None = None
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            if current_heading is not None and current_title is not None:
                sections.append(
                    ChangelogSection(
                        heading=current_heading,
                        label=_extract_label(current_title),
                        content="\n".join([current_heading, *current_lines]).rstrip()
                        + "\n",
                    )
                )
            current_heading = line
            current_title = match.group("title")
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None and current_title is not None:
        sections.append(
            ChangelogSection(
                heading=current_heading,
                label=_extract_label(current_title),
                content="\n".join([current_heading, *current_lines]).rstrip() + "\n",
            )
        )

    return sections


def _extract_label(title: str) -> str:
    """Extract the logical section label from a changelog heading title."""

    stripped = title.strip()
    bracketed = BRACKETED_VERSION_RE.match(stripped)
    if bracketed:
        return bracketed.group("label").strip()
    if " - " in stripped:
        return stripped.split(" - ", 1)[0].strip()
    return stripped


def normalize_version_label(value: str) -> str:
    """Normalize a version/tag label for comparisons."""

    normalized = value.strip().strip("[]")
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    return normalized.strip().lower()


def select_section(
    sections: list[ChangelogSection], *, target_tag: str | None = None
) -> ChangelogSection:
    """Choose the newest released section or a specific tag section."""

    released = [
        section
        for section in sections
        if normalize_version_label(section.label) != "unreleased"
    ]
    if not released:
        raise ValueError("No released changelog entries were found.")

    if target_tag is None:
        return released[0]

    target = normalize_version_label(target_tag)
    for section in released:
        if normalize_version_label(section.label) == target:
            return section
    raise ValueError(f"Could not find changelog entry for tag/version: {target_tag}")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract the newest released changelog section (or a specific tag) for "
            "GitHub Release notes."
        )
    )
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to changelog file")
    parser.add_argument("--tag", help="Target tag/version to extract (for example v1.2.3)")
    parser.add_argument("--output", help="Write extracted notes to this file instead of stdout")
    return parser


def main() -> int:
    """CLI entrypoint."""

    args = build_parser().parse_args()
    changelog_path = Path(args.changelog)
    if not changelog_path.exists():
        print(f"Changelog file not found: {changelog_path}", file=sys.stderr)
        return 2

    sections = parse_sections(changelog_path.read_text(encoding="utf-8"))
    try:
        section = select_section(sections, target_tag=args.tag)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(section.content, encoding="utf-8")
    else:
        sys.stdout.write(section.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
