"""Version helpers for the package-first."""

from importlib import metadata

from . import __version__ as package_version


def get_version() -> str:
    try:
        return metadata.version("mqtt-simulator")
    except metadata.PackageNotFoundError:
        return package_version
