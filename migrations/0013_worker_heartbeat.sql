-- worker_heartbeats: single-row liveness signal written by worker.py once
-- per poll loop iteration, read by GET /api/worker/health in server.py.
-- worker.py is a separate OS process from the Flask app, so this table is
-- the only way server.py can tell whether it's still running.
--
-- IF NOT EXISTS, same reasoning as 0012_model_presets.sql: server.py's own
-- Base.metadata.create_all(engine, checkfirst=True) creates this table on
-- every startup (WorkerHeartbeat is a normal ORM class) before
-- run_migrations.py ever runs against a fresh database.
CREATE TABLE IF NOT EXISTS worker_heartbeats (
    id           integer PRIMARY KEY,
    last_seen_at timestamptz NOT NULL
);
