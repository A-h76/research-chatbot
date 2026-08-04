"""Google Drive import — Golden Rule wiring (#23)."""

from __future__ import annotations

import json
from types import SimpleNamespace

from flask import Flask, jsonify, request, session


class _FakeScalars:
    def first(self):
        return None


class _FakeResult:
    def scalars(self):
        return _FakeScalars()


def test_google_drive_import_enqueues_analysis(monkeypatch):
    from backend.library import google_drive as gd

    class FakeDB:
        def __init__(self):
            self.added = []
            self._id = 50

        def execute(self, *_a, **_k):
            return _FakeResult()

        def add(self, obj):
            if getattr(obj, "id", None) is None:
                obj.id = self._id
                self._id += 1
            self.added.append(obj)

        def flush(self):
            pass

    class UserFile:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.id = None

    db = FakeDB()
    enqueued: list[tuple[int, int]] = []

    monkeypatch.setattr(
        gd,
        "download_file",
        lambda token, fid, *, max_bytes=0: (b"%PDF-1.4 x", "paper.pdf", "application/pdf"),
    )

    def fake_apply(db_arg, uf, **kwargs):
        uf.path = "p.pdf"
        uf.size = 9
        if kwargs.get("enqueue_import"):
            kwargs["enqueue_import"](db_arg, kwargs["user_id"], uf.id)
        return {"ok": True, "queued": True, "file_id": uf.id}

    monkeypatch.setattr("backend.library.file_pull.apply_pdf_bytes_to_stub", fake_apply)

    app = Flask(__name__)
    app.secret_key = "t"

    @app.post("/api/library/google_drive/import")
    def google_drive_import():
        from backend.library.file_pull import apply_pdf_bytes_to_stub

        session["user_id"] = 7
        data = request.get_json(silent=True) or {}
        file_ids = [str(x) for x in (data.get("file_ids") or [])]
        uid = 7
        created = []
        queued = 0
        for ext_id in file_ids:
            hit = gd.download_file("tok", ext_id)
            assert hit
            pdf_bytes, filename, content_type = hit
            uf = UserFile(
                user_id=uid,
                name=filename,
                path="",
                size=0,
                external_provider="google_drive",
                external_item_id=ext_id,
                tags=json.dumps(["from-google-drive"]),
                metadata_source="google_drive",
            )
            db.add(uf)
            db.flush()
            applied = apply_pdf_bytes_to_stub(
                db,
                uf,
                data=pdf_bytes,
                filename=filename,
                content_type=content_type,
                storage=SimpleNamespace(),
                upload_dir="/tmp",
                enqueue_import=lambda _db, u, f: enqueued.append((u, f)),
                user_id=uid,
                max_file_mb=25,
            )
            if applied.get("ok"):
                created.append(uf.id)
                if applied.get("queued"):
                    queued += 1
        return jsonify(
            {
                "ok": True,
                "source": "google_drive",
                "created": len(created),
                "created_ids": created,
                "queued": queued,
                "analysis_queued": queued > 0,
            }
        ), 201

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 7
    res = client.post("/api/library/google_drive/import", json={"file_ids": ["file-1"]})
    assert res.status_code == 201, res.get_data(as_text=True)
    body = res.get_json()
    assert body["created"] == 1
    assert body["analysis_queued"] is True
    assert body["source"] == "google_drive"
    assert enqueued == [(7, body["created_ids"][0])]
    assert db.added[0].external_provider == "google_drive"
    assert "from-google-drive" in json.loads(db.added[0].tags)
