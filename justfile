set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

coverage_threshold := "70"
semver_tag_pattern := "^v?[0-9]+\\.[0-9]+\\.[0-9]+$"
testpypi_publish_url := "https://test.pypi.org/legacy/"
testpypi_check_url := "https://test.pypi.org/simple/"
docker_image := "mqtt-sim:local"

# Show all available recipes.
default: help

# List available recipes with descriptions.
help:
    @just --list

# Check that common local tools are installed.
doctor:
    @command -v just >/dev/null 2>&1 && echo "just: ok" || echo "just: missing"
    @command -v uv >/dev/null 2>&1 && echo "uv: ok" || echo "uv: missing"
    @command -v git >/dev/null 2>&1 && echo "git: ok" || echo "git: missing"
    @command -v docker >/dev/null 2>&1 && echo "docker: ok" || echo "docker: missing"
    @command -v git-cliff >/dev/null 2>&1 && echo "git-cliff: ok" || echo "git-cliff: missing"

# Sync runtime and dev dependencies with uv.
sync:
    uv sync --dev

# Sync all dependency groups (alias for CI parity and future groups).
sync-all:
    uv sync --all-groups

# Install dependencies (alias for sync).
install: sync

# Run the test suite.
test:
    uv run --no-sync pytest

# Run tests with coverage, emit terminal+XML reports, and enforce threshold.
cov threshold=coverage_threshold:
    uv run --no-sync pytest --cov=src/mqtt_simulator --cov-report=term-missing --cov-report=xml --cov-fail-under {{threshold}}

# Run Ruff lint checks.
lint:
    uv run --no-sync ruff check src tests

# Format source and tests with Ruff.
fmt:
    uv run --no-sync ruff format src tests

# Run local CI parity checks (lint + coverage threshold).
ci-check threshold=coverage_threshold:
    uv run --no-sync ruff check src tests
    just cov {{threshold}}

# Remove local caches and build artifacts.
clean:
    rm -rf .pytest_cache .ruff_cache htmlcov .coverage .coverage.* dist build

# Build a GIF for every example config with VHS helper scripts.
vhs-example-gifs:
    test -x scripts/generate-all-examples.sh || chmod +x scripts/generate-all-examples.sh
    ./scripts/generate-all-examples.sh

# Build the main README GIF with VHS.
vhs-main-gif:
    vhs scripts/cli-gif-gen.tape

# Ensure git-cliff is installed before changelog/release tasks.
[private]
check-git-cliff:
    @command -v git-cliff >/dev/null 2>&1 || { echo "git-cliff is required. Install: https://git-cliff.org/docs/installation/"; exit 1; }

# Ensure Docker is installed before Docker image tasks.
[private]
check-docker:
    @command -v docker >/dev/null 2>&1 || { echo "docker is required."; exit 1; }

# Remove Python package build artifacts.
[private]
dist-clean:
    rm -rf dist

# Ensure a TestPyPI token is available in env vars.
[private]
check-testpypi-token:
    @token="${UV_PUBLISH_TOKEN:-${TEST_PYPI_API_TOKEN:-}}"; \
    if [[ -z "$token" ]]; then \
      echo "Missing TestPyPI token. Set UV_PUBLISH_TOKEN or TEST_PYPI_API_TOKEN."; \
      exit 1; \
    fi

# Ensure a PyPI token is available in env vars.
[private]
check-pypi-token:
    @token="${UV_PUBLISH_TOKEN:-${PYPI_API_TOKEN:-}}"; \
    if [[ -z "$token" ]]; then \
      echo "Missing PyPI token. Set UV_PUBLISH_TOKEN or PYPI_API_TOKEN."; \
      exit 1; \
    fi

# Build and validate Python distribution artifacts (optional version override).
package version="": dist-clean
    requested="{{version}}"; \
    if [[ -n "$requested" ]]; then export PDM_BUILD_SCM_VERSION="${requested#v}"; fi; \
    uv build; \
    uvx twine check --strict dist/*

# Build and validate package artifacts using a synthetic dev version.
package-dev:
    suffix="${GITHUB_RUN_ID:-$(date +%Y%m%d%H%M%S)}${GITHUB_RUN_ATTEMPT:-0}${BASHPID:-$$}"; \
    just package "0.0.0.dev${suffix}"

# Publish package to TestPyPI as a dry run.
publish-testpypi-dry version="": check-testpypi-token
    just package "{{version}}"
    token="${UV_PUBLISH_TOKEN:-${TEST_PYPI_API_TOKEN:-}}"; \
    UV_PUBLISH_TOKEN="$token" uv publish --dry-run --publish-url {{testpypi_publish_url}} --check-url {{testpypi_check_url}}

# Publish package to TestPyPI.
publish-testpypi version="": check-testpypi-token
    just package "{{version}}"
    token="${UV_PUBLISH_TOKEN:-${TEST_PYPI_API_TOKEN:-}}"; \
    UV_PUBLISH_TOKEN="$token" uv publish --publish-url {{testpypi_publish_url}}

# Publish package to PyPI as a dry run.
publish-pypi-dry version="": check-pypi-token
    just package "{{version}}"
    token="${UV_PUBLISH_TOKEN:-${PYPI_API_TOKEN:-}}"; \
    UV_PUBLISH_TOKEN="$token" uv publish --dry-run

# Publish package to PyPI.
publish-pypi version="": check-pypi-token
    just package "{{version}}"
    token="${UV_PUBLISH_TOKEN:-${PYPI_API_TOKEN:-}}"; \
    UV_PUBLISH_TOKEN="$token" uv publish

# Build the local Docker image used by CI/CD and smoke tests.
docker-build tag=docker_image: check-docker
    docker build -t {{tag}} .

# Generate the full changelog into CHANGELOG.md.
changelog: check-git-cliff
    git-cliff --config cliff.toml --tag-pattern '{{semver_tag_pattern}}' --output CHANGELOG.md

# Preview the unreleased changelog section rendered as the next version.
changelog-dry-run: check-git-cliff
    next="$(git-cliff --config cliff.toml --bumped-version --unreleased --tag-pattern '{{semver_tag_pattern}}')"; \
    git-cliff --config cliff.toml --unreleased --tag "${next}" --tag-pattern '{{semver_tag_pattern}}'

# Print the latest released changelog entry (or a specific tag) to stdout.
release-notes-dry-run tag="":
    if [[ -n "{{tag}}" ]]; then \
      python3 .github/scripts/extract_latest_changelog.py --changelog CHANGELOG.md --tag "{{tag}}"; \
    else \
      python3 .github/scripts/extract_latest_changelog.py --changelog CHANGELOG.md; \
    fi

# Extract release notes from CHANGELOG.md into a file for GitHub Release.
release-notes-from-changelog tag output="RELEASE_NOTES.md":
    python3 .github/scripts/extract_latest_changelog.py --changelog CHANGELOG.md --tag "{{tag}}" --output "{{output}}"

# Run a local preflight that approximates CI/CD without uploading or tagging.
cd-preflight:
    just ci-check
    just package-dev
    just changelog-dry-run
    if grep -Eq '^## \\[(v)?[0-9]+\\.[0-9]+\\.[0-9]+\\]' CHANGELOG.md; then \
      just release-notes-dry-run; \
    else \
      echo "Skipping release-notes-dry-run (no released changelog entry yet)."; \
    fi
    just docker-build

# Prepare a release changelog for a version/tag using the repository release script.
release version:
    test -x scripts/release.sh || chmod +x scripts/release.sh
    ./scripts/release.sh {{version}}
