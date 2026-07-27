"""Tests for project ownership resolution (PR2)."""

from security.authz import project_owned_by_user, resolve_owned_project_id


class _Proj:
    def __init__(self, pid, user_id):
        self.id = pid
        self.user_id = user_id


class _Db:
    def __init__(self, rows):
        self._rows = {p.id: p for p in rows}

    def get(self, _model, pid):
        return self._rows.get(pid)


def test_resolve_owned_project_id_ok():
    db = _Db([_Proj(1, 42)])
    pid, denied = resolve_owned_project_id(db, object, 1, 42)
    assert pid == 1 and not denied


def test_resolve_owned_project_id_denied_cross_user():
    db = _Db([_Proj(1, 99)])
    pid, denied = resolve_owned_project_id(db, object, 1, 42)
    assert pid is None and denied


def test_resolve_owned_project_id_missing():
    db = _Db([])
    pid, denied = resolve_owned_project_id(db, object, 7, 42)
    assert pid is None and denied


def test_resolve_owned_project_id_empty():
    db = _Db([_Proj(1, 42)])
    pid, denied = resolve_owned_project_id(db, object, None, 42)
    assert pid is None and not denied


def test_project_owned_by_user():
    assert project_owned_by_user(_Proj(1, 5), 5)
    assert not project_owned_by_user(_Proj(1, 5), 6)
    assert not project_owned_by_user(None, 5)
