"""The installed plugin version, used to cache-bust the plugin's static files."""
from functools import lru_cache
from importlib import metadata


@lru_cache(maxsize=1)
def version():
    try:
        return metadata.version("prblm-builder")
    except metadata.PackageNotFoundError:
        return "dev"
