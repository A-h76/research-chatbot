"""IdentityLoader + IdentityPack (Sprint 2/3)."""

from __future__ import annotations

import pytest

from backend.ai_core import load_identity_pack
from backend.ai_core.identity import (
    IDENTITY_LAYERS,
    IdentityLoader,
    clear_identity_cache,
    identity_paths,
    load_identity,
)


EXPECTED_ORDER = (
    "identity",
    "evidence_first",
    "scientific_integrity",
    "grounding",
    "citation",
    "reasoning",
    "response_contract",
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_identity_cache()
    yield
    clear_identity_cache()


def test_seven_layers_in_doctrine_order():
    assert tuple(layer_id for layer_id, _, _ in IDENTITY_LAYERS) == EXPECTED_ORDER
    paths = identity_paths()
    assert len(paths) == 7
    for p in paths:
        assert p.is_file()
        assert p.read_text(encoding="utf-8").strip()


def test_identity_loader_pack_fields():
    pack = IdentityLoader().load()
    assert pack.identity.strip()
    assert "Evidence First" in pack.principles
    assert "Citation Policy" in pack.policies
    assert pack.layer_ids == EXPECTED_ORDER
    assert "operating system for scientific research" in pack.identity.lower()
    assert pack.layer("grounding").strip()


def test_load_identity_aliases():
    assert load_identity() is load_identity_pack()


def test_as_system_text_contains_all_layers_in_order():
    text = load_identity_pack().as_system_text()
    assert text.startswith("# Soro Identity Doctrine")
    positions = [text.index(f"## {title}") for _, _, title in IDENTITY_LAYERS]
    assert positions == sorted(positions)
    assert "High" in text and "Medium" in text and "Low" in text


def test_as_system_text_without_preamble():
    text = load_identity_pack().as_system_text(include_preamble=False)
    assert not text.startswith("# Soro Identity Doctrine")
    assert "## Identity" in text


def test_unknown_layer_raises():
    with pytest.raises(KeyError):
        load_identity_pack().layer("not_a_layer")


def test_loader_cache_and_reload():
    loader = IdentityLoader()
    a = loader.load()
    b = loader.load()
    assert a is b
    c = loader.reload()
    assert c is not a
    assert c.identity == a.identity


def test_process_default_cache():
    a = load_identity_pack()
    b = load_identity_pack()
    assert a is b
