set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

coverage_threshold := "70"

default: help

help:
    @just --list

sync:
    uv sync --dev

install: sync

test:
    uv run --no-sync pytest

cov threshold=coverage_threshold:
    uv run --no-sync pytest --cov=src/mqtt_simulator --cov-report=term-missing --cov-fail-under {{threshold}}

lint:
    uv run --no-sync ruff check src tests

fmt:
    uv run --no-sync ruff format src tests

ci-check threshold=coverage_threshold:
    uv run --no-sync ruff check src tests
    just cov {{threshold}}

clean:
    rm -rf .pytest_cache .ruff_cache htmlcov .coverage .coverage.*
