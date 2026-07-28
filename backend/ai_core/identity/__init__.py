"""Dhund identity doctrine.

Public API: ``IdentityLoader``, ``load_identity()`` / ``load_identity_pack()``.

PromptBuilder must never read markdown files directly — only ``IdentityPack``.
"""

from backend.ai_core.identity.loader import (
    IDENTITY_LAYERS,
    IdentityLoader,
    IdentityPack,
    clear_identity_cache,
    identity_paths,
    load_identity,
    load_identity_pack,
)

__all__ = [
    "IDENTITY_LAYERS",
    "IdentityLoader",
    "IdentityPack",
    "clear_identity_cache",
    "identity_paths",
    "load_identity",
    "load_identity_pack",
]
