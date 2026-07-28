from types import SimpleNamespace

import pytest

from backend.writing.api.errors import WritingDomainError
from backend.writing.services.permission_service import require_owned_document, require_owned_project


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def get(self, model, key):
        return self.rows.get((model, int(key)))


def test_require_owned_project_passes():
    Project = object()
    db = _FakeDB({(Project, 5): SimpleNamespace(id=5, user_id=12)})
    p = require_owned_project(db, Project, user_id=12, project_id=5)
    assert p.id == 5


def test_require_owned_project_raises_on_wrong_owner():
    Project = object()
    db = _FakeDB({(Project, 5): SimpleNamespace(id=5, user_id=9)})
    with pytest.raises(WritingDomainError):
        require_owned_project(db, Project, user_id=12, project_id=5)


def test_require_owned_document_raises_on_missing():
    Doc = object()
    db = _FakeDB({})
    with pytest.raises(WritingDomainError):
        require_owned_document(db, Doc, user_id=1, document_id=99)

