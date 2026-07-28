import os
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server


def _fixture():
    path = Path(__file__).resolve().parent / "contracts" / "writing_documents_contract.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _with_datetimes(payload: dict):
    fixed = dict(payload)
    for key in ("last_opened_at", "created_at", "updated_at"):
        if key in fixed and fixed[key]:
            fixed[key] = datetime.fromisoformat(fixed[key])
    return fixed


def _version_with_datetimes(payload: dict):
    fixed = dict(payload)
    if fixed.get("created_at"):
        fixed["created_at"] = datetime.fromisoformat(fixed["created_at"])
    return fixed


def test_writing_document_serializer_matches_contract_keys():
    fx = _fixture()["document"]
    doc = SimpleNamespace(**_with_datetimes(fx))
    payload = server._writing_doc_to_dict(doc)
    assert set(payload.keys()) == set(fx.keys())


def test_writing_version_serializer_matches_contract_keys():
    fx = _fixture()["version"]
    version = SimpleNamespace(**_version_with_datetimes(fx))
    payload = server._writing_doc_version_to_dict(version)
    assert set(payload.keys()) == set(fx.keys())


def test_version_conflict_payload_matches_contract_fixture():
    from backend.writing.services.version_service import build_version_conflict_payload

    assert build_version_conflict_payload(4) == _fixture()["version_conflict"]

