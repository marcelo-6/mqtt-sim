"""Version helpers for the package."""

from importlib import metadata

from . import __version__ as package_version


def get_version() -> str:
    """Return the installed package version, or the local fallback version."""
    try:
        return metadata.version("mqtt-simulator")
    except metadata.PackageNotFoundError:
        return package_version
