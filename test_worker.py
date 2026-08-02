"""Tests for worker.py's extract_metadata/paper_analysis job handlers —
mocks PromptRegistry/ModelRegistry (per this task's own instruction), so
no real AI call happens even though real credentials are available in
this environment. UserFile/PaperAnalysis/UploadJob are server.py's REAL
model classes, though, against an isolated throwaway SQLite file (not
the real chat_dev.db) — using the real classes means this can't silently
drift from production's actual schema the way hand-rolled stand-ins
elsewhere in this project's test suite could.

worker.py needs `import server` regardless of this test (its DB models
come from there) — see worker.py's own module docstring for why that's
safe (a standalone process, never imported back by server.py itself).

DATABASE_URL isolation (so this never touches the real local chat_dev.db)
lives in the project's root conftest.py, not here — see that file for
why per-file env-var assignment was fragile (it silently didn't work
when this file wasn't the first one pytest happened to collect).

Run: pytest test_worker.py -v
"""

import json
import os

import pytest
from dotenv import load_dotenv

load_dotenv(override=False)  # OPENAI_API_KEY etc. — never overrides conftest.py's DATABASE_URL

import server
import worker
from backend.ai import ModelError


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user(db):
    u = server.User(email=f"wt-{os.urandom(4).hex()}@example.com", name="T", auth_provider="dev")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def uf(db, user):
    f = server.UserFile(
        user_id=user.id,
        name="paper.txt",
        mime="text/plain",
        kind="document",
        path="irrelevant-for-these-tests",
        size=10,
    )
    db.add(f)
    db.commit()
    return f


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    # Handlers call _get_text_for_file(uf) before touching either
    # registry — real storage access isn't what this file tests.
    monkeypatch.setattr(worker, "_get_text_for_file", lambda uf: "FAKE PAPER TEXT")


def _mock_registries(mocker, response_json):
    prompt_registry = mocker.Mock()
    # get_prompt() returns (rendered_text, PromptVersion row) since
    # backend/ai/prompt_registry.py's Prompt Registry extension — the
    # version row is unused by worker.py's handlers (assigned to
    # `_prompt_version`), so a plain Mock() stands in for it.
    prompt_registry.get_prompt.return_value = ("rendered prompt text", mocker.Mock())
    model_registry = mocker.Mock()
    model_registry.call.return_value = {
        "content": json.dumps(response_json),
        "model": "gpt-4o-mini",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "finish_reason": "stop",
        "cost": 0.001,
    }
    mocker.patch.object(worker, "PromptRegistry", return_value=prompt_registry)
    mocker.patch.object(worker, "ModelRegistry", return_value=model_registry)
    return prompt_registry, model_registry


def _mock_failing_registries(mocker, exc):
    prompt_registry = mocker.Mock()
    prompt_registry.get_prompt.return_value = ("rendered prompt text", mocker.Mock())
    model_registry = mocker.Mock()
    model_registry.call.side_effect = exc
    mocker.patch.object(worker, "PromptRegistry", return_value=prompt_registry)
    mocker.patch.object(worker, "ModelRegistry", return_value=model_registry)
    return prompt_registry, model_registry


# ------------------------------------------------------------ extract_metadata (drain shim #17)
def test_extract_metadata_handler_redirects_to_phase1(db, uf, mocker):
    """Leftover extract_metadata jobs must not call the LLM — enqueue phase1."""
    prompt_registry, model_registry = _mock_registries(mocker, {"title": "unused"})
    job = server.UploadJob(
        file_id=uf.id, user_id=uf.user_id, job_type="extract_metadata", status="running"
    )
    db.add(job)
    db.commit()

    with pytest.warns(DeprecationWarning, match="extract_metadata"):
        worker._handle_extract_metadata(db, job)

    prompt_registry.get_prompt.assert_not_called()
    model_registry.call.assert_not_called()
    phase1 = (
        db.execute(
            server.select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "phase1_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert len(phase1) == 1
    assert phase1[0].status == "pending"


def test_extract_metadata_handler_skips_when_meta_already_done(db, uf, mocker):
    uf.meta_status = "done"
    db.commit()
    _, model_registry = _mock_registries(mocker, {"title": "should not be reached"})
    job = server.UploadJob(
        file_id=uf.id, user_id=uf.user_id, job_type="extract_metadata", status="running"
    )
    db.add(job)
    db.commit()

    with pytest.warns(DeprecationWarning, match="extract_metadata"):
        worker._handle_extract_metadata(db, job)

    model_registry.call.assert_not_called()
    phase1 = (
        db.execute(
            server.select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "phase1_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert len(phase1) == 0


# ------------------------------------------------------------ paper_analysis
def _analysis_payload(**overrides):
    base = {
        f: "x"
        for f in (
            "executive_summary",
            "abstract_explained",
            "research_objective",
            "problem_statement",
            "methodology",
            "dataset",
            "experiments",
            "results",
        )
    }
    base.update(
        {
            "key_contributions": ["a"],
            "strengths": ["b"],
            "limitations": ["c"],
            "future_work": ["d"],
            "keywords": ["e"],
            "important_terms": {"x": "y"},
        }
    )
    base.update(overrides)
    return base


def test_paper_analysis_calls_prompt_registry_and_model_registry(db, uf, mocker):
    prompt_registry, model_registry = _mock_registries(mocker, _analysis_payload())
    job = server.UploadJob(file_id=uf.id, user_id=uf.user_id, job_type="paper_analysis", status="running")
    db.add(job)
    db.commit()

    worker._handle_paper_analysis(db, job)

    prompt_registry.get_prompt.assert_called_once()
    assert prompt_registry.get_prompt.call_args[0][0] == "paper_analysis"
    model_registry.call.assert_called_once()
    assert model_registry.call.call_args.kwargs["user_id"] == uf.user_id


def test_paper_analysis_writes_paper_analysis_row(db, uf, mocker):
    _mock_registries(mocker, _analysis_payload(executive_summary="A great paper."))
    job = server.UploadJob(file_id=uf.id, user_id=uf.user_id, job_type="paper_analysis", status="running")
    db.add(job)
    db.commit()

    worker._handle_paper_analysis(db, job)

    pa = db.execute(server.select(server.PaperAnalysis).where(server.PaperAnalysis.file_id == uf.id)).scalar_one()
    assert pa.status == "done"
    assert pa.model == server.UTILITY_MODEL
    data = json.loads(pa.data)
    assert data["executive_summary"] == "A great paper."
    assert data["keywords"] == ["e"]


def test_paper_analysis_normalizes_string_array_fields(db, uf, mocker):
    _mock_registries(mocker, _analysis_payload(keywords="single-keyword-as-string"))
    job = server.UploadJob(file_id=uf.id, user_id=uf.user_id, job_type="paper_analysis", status="running")
    db.add(job)
    db.commit()

    worker._handle_paper_analysis(db, job)

    pa = db.execute(server.select(server.PaperAnalysis).where(server.PaperAnalysis.file_id == uf.id)).scalar_one()
    data = json.loads(pa.data)
    assert data["keywords"] == ["single-keyword-as-string"]


def test_paper_analysis_skips_when_already_done(db, uf, mocker):
    content_hash = worker._sha256("FAKE PAPER TEXT")
    pa = server.PaperAnalysis(file_id=uf.id, user_id=uf.user_id, status="done", content_hash=content_hash)
    db.add(pa)
    db.commit()
    _, model_registry = _mock_registries(mocker, _analysis_payload())
    job = server.UploadJob(file_id=uf.id, user_id=uf.user_id, job_type="paper_analysis", status="running")
    db.add(job)
    db.commit()

    worker._handle_paper_analysis(db, job)

    model_registry.call.assert_not_called()


def test_paper_analysis_sets_failed_status_and_reraises_on_ai_error(db, uf, mocker):
    _mock_failing_registries(mocker, ModelError("bad key", provider="openai", model="gpt-4o-mini"))
    job = server.UploadJob(file_id=uf.id, user_id=uf.user_id, job_type="paper_analysis", status="running")
    db.add(job)
    db.commit()

    with pytest.raises(ModelError):
        worker._handle_paper_analysis(db, job)

    pa = db.execute(server.select(server.PaperAnalysis).where(server.PaperAnalysis.file_id == uf.id)).scalar_one()
    assert pa.status == "failed"


# ------------------------------------------------------------ HANDLERS registration
def test_handlers_dict_includes_pipeline_jobs():
    assert worker.HANDLERS["extract_metadata"] is worker._handle_extract_metadata
    assert worker.HANDLERS["phase1_analysis"] is worker._handle_phase1_analysis
    assert worker.HANDLERS["paper_analysis"] is worker._handle_paper_analysis
    assert worker.HANDLERS["import"] is worker._handle_import


# ------------------------------------------------------------ queue-only wrappers (no daemon threads)
def test_extract_metadata_enqueues_phase1_not_thread(db, uf, mocker):
    """Legacy extract_metadata() must hit the queue, not spawn a thread."""
    thread_spy = mocker.patch("server.threading.Thread")
    with pytest.warns(DeprecationWarning, match="extract_metadata"):
        server.extract_metadata(uf.id, "unused text", "abc123")

    thread_spy.assert_not_called()
    jobs = (
        db.execute(
            server.select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "phase1_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
    events = (
        db.execute(
            server.select(server.OutboxEvent).where(server.OutboxEvent.aggregate_id == jobs[0].id)
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].event_type == "job.enqueued"


def test_trigger_paper_analysis_enqueues_job_not_thread(db, uf, mocker):
    thread_spy = mocker.patch("server.threading.Thread")
    with pytest.warns(DeprecationWarning, match="trigger_paper_analysis"):
        server.trigger_paper_analysis(uf.id, "unused", "hash1", sync=False)

    thread_spy.assert_not_called()
    jobs = (
        db.execute(
            server.select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "paper_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == "pending"


def test_process_document_fallback_enqueues_phase1(db, uf, tmp_path, mocker):
    """When on_processed is omitted, follow-ups go through the queue."""
    paper = tmp_path / "p.txt"
    paper.write_text("This is a long enough academic paper abstract for chunking tests. " * 20)
    mocker.patch("server.extract_text", return_value=paper.read_text())
    mocker.patch("server.embed_texts", return_value=[[0.1, 0.2]] * 5)
    mocker.patch("server.chunk_text", return_value=["chunk a", "chunk b"])
    thread_spy = mocker.patch("server.threading.Thread")

    note = server._process_document(db, uf, str(paper), "p.txt", "text/plain")

    assert note is None
    thread_spy.assert_not_called()
    jobs = (
        db.execute(
            server.select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "phase1_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
