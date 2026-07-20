import os, re, glob, sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = (os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db").replace(
    "postgres://", "postgresql://", 1
)
engine = create_engine(url, pool_pre_ping=True)


def split_sql_statements(sql):
    """Splits on ';', except inside $$...$$ / $tag$...$tag$ dollar-quoted
    regions (DO blocks, function bodies) — a plain sql.split(";") cuts a
    DO block's own internal semicolons into broken fragments, which is
    exactly what silently breaks a migration that uses one. Needed as of
    0005's idempotent-constraint fix: Postgres has no ADD CONSTRAINT IF
    NOT EXISTS (verified: it's a syntax error), so the idempotent
    equivalent is a DO $$ ... EXCEPTION WHEN duplicate_object ... END $$
    block, which itself contains a ';'."""
    statements = []
    current = []
    i, n = 0, len(sql)
    dollar_tag = None   # None outside a dollar-quoted region, else its tag (e.g. "$$")
    while i < n:
        ch = sql[i]
        if dollar_tag is None:
            if ch == "$":
                m = re.match(r"\$[A-Za-z0-9_]*\$", sql[i:])
                if m:
                    dollar_tag = m.group(0)
                    current.append(dollar_tag)
                    i += len(dollar_tag)
                    continue
            if ch == ";":
                statements.append("".join(current))
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1
        else:
            if sql.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            current.append(ch)
            i += 1
    tail = "".join(current)
    if tail.strip():
        statements.append(tail)
    return statements

with engine.begin() as conn:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
    )
    applied = {
        row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations"))
    }

for path in sorted(
    glob.glob(os.path.join(os.path.dirname(__file__), "migrations", "*.sql"))
):
    name = os.path.basename(path)
    if name in applied:
        continue
    sql = re.sub(
        r"--[^\n]*", "", open(path).read()
    )  # strip line comments before splitting on ";"
    try:
        with engine.begin() as conn:
            for stmt in split_sql_statements(sql):
                if stmt.strip():
                    conn.execute(text(stmt))
            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:n)"),
                {"n": name},
            )
        print(f"OK    {name}")
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        sys.exit(1)
