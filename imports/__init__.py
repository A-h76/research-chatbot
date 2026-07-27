"""Import Engine — public entry point.

extract_text(path, mime, name) is a drop-in replacement for the function
of the same name that used to live in server.py: identical signature,
identical return contract. Internally it now resolves through an Importer
registry (one class per format) instead of an if/elif chain — nothing
calling it needs to change.
"""

from .interface import Importer
from .registry import extract_text, resolve

__all__ = ["Importer", "extract_text", "resolve"]
