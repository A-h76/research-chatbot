"""Load and assemble Soro identity doctrine.

Load order (every AI feature inherits this stack)::

    Identity
    → Evidence First
    → Scientific Integrity
    → Grounding Rules
    → Citation Policy
    → Reasoning Style
    → Response Contract

``IdentityLoader`` is the only component that reads markdown files.
PromptBuilder / PromptRouter must consume ``IdentityPack`` — never open
these files directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from backend.ai_core.versions import IDENTITY_VERSION

_IDENTITY_DIR = Path(__file__).resolve().parent

# (layer_id, filename, human title) — fixed order is part of the product contract.
IDENTITY_LAYERS: tuple[tuple[str, str, str], ...] = (
    ("identity", "identity.md", "Identity"),
    ("evidence_first", "evidence_first.md", "Evidence First"),
    ("scientific_integrity", "scientific_integrity.md", "Scientific Integrity"),
    ("grounding", "grounding.md", "Grounding Rules"),
    ("citation", "citation.md", "Citation Policy"),
    ("reasoning", "reasoning.md", "Reasoning Style"),
    ("response_contract", "response_contract.md", "Response Contract"),
)

# Groupings for consumers that want the classic identity / principles / policies split.
_PRINCIPLES_LAYER_IDS = (
    "evidence_first",
    "scientific_integrity",
    "grounding",
    "reasoning",
)
_POLICIES_LAYER_IDS = (
    "citation",
    "response_contract",
)


@dataclass(frozen=True)
class IdentityPack:
    """Doctrine pack — strings only; no file handles.

    ``identity`` / ``principles`` / ``policies`` are the stable PromptBuilder-facing
    fields. ``layers`` preserves the full seven-layer stack for routers/validators.
    """

    identity: str
    principles: str
    policies: str
    layers: Mapping[str, str]
    version: str = IDENTITY_VERSION

    def layer(self, layer_id: str) -> str:
        try:
            return self.layers[layer_id]
        except KeyError as exc:
            raise KeyError(f"unknown identity layer: {layer_id!r}") from exc

    def as_system_text(self, *, include_preamble: bool = True) -> str:
        """Flat system preamble in doctrine load order."""
        title_by_id = {layer_id: title for layer_id, _, title in IDENTITY_LAYERS}
        parts: list[str] = []
        if include_preamble:
            parts.append(
                "# Soro Identity Doctrine\n\n"
                "You are Soro — the operating system for scientific research. "
                "The following doctrine is mandatory and overrides conflicting "
                "task instructions when they would cause fabrication, ungrounded "
                "certainty, or invented citations.\n"
            )
        for layer_id, _, _ in IDENTITY_LAYERS:
            title = title_by_id[layer_id]
            body = self.layers[layer_id].strip()
            parts.append(f"## {title}\n\n{body}\n")
        return "\n".join(parts).strip() + "\n"

    @property
    def layer_ids(self) -> tuple[str, ...]:
        return tuple(layer_id for layer_id, _, _ in IDENTITY_LAYERS)


def identity_paths() -> tuple[Path, ...]:
    """Doctrine files in load order."""
    return tuple(_IDENTITY_DIR / filename for _, filename, _ in IDENTITY_LAYERS)


def _join_layers(layers: Mapping[str, str], layer_ids: tuple[str, ...]) -> str:
    title_by_id = {lid: title for lid, _, title in IDENTITY_LAYERS}
    chunks: list[str] = []
    for lid in layer_ids:
        chunks.append(f"## {title_by_id[lid]}\n\n{layers[lid].strip()}\n")
    return "\n".join(chunks).strip() + "\n"


class IdentityLoader:
    """Load identity markdown once; cache; never leak Path into PromptBuilder.

    Hot-reload: call ``reload()`` (or ``clear()`` then ``load()``).
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else _IDENTITY_DIR
        self._cache: IdentityPack | None = None

    def load(self) -> IdentityPack:
        if self._cache is not None:
            return self._cache
        self._cache = self._read()
        return self._cache

    def reload(self) -> IdentityPack:
        """Drop cache and read files again (future hot-reload / tests)."""
        self._cache = None
        return self.load()

    def clear(self) -> None:
        self._cache = None

    def _read(self) -> IdentityPack:
        raw: dict[str, str] = {}
        for layer_id, filename, _title in IDENTITY_LAYERS:
            path = self._root / filename
            if not path.is_file():
                raise FileNotFoundError(f"identity layer missing: {path}")
            body = path.read_text(encoding="utf-8")
            if not body.strip():
                raise ValueError(f"identity layer empty: {path}")
            raw[layer_id] = body
        layers = MappingProxyType(raw)
        return IdentityPack(
            identity=raw["identity"].strip() + "\n",
            principles=_join_layers(layers, _PRINCIPLES_LAYER_IDS),
            policies=_join_layers(layers, _POLICIES_LAYER_IDS),
            layers=layers,
        )


_default_loader = IdentityLoader()


def load_identity_pack() -> IdentityPack:
    """Process-default cached load (PromptBuilder should use this or inject a loader)."""
    return _default_loader.load()


def load_identity() -> IdentityPack:
    """Alias for ``load_identity_pack``."""
    return load_identity_pack()


def clear_identity_cache() -> None:
    """Test helper — clear the process-default loader cache."""
    _default_loader.clear()
