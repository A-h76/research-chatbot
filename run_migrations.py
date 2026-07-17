import os, re, glob, sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = (os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db").replace("postgres://", "postgresql://", 1)
engine = create_engine(url, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations "
                      "(filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations"))}

for path in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "migrations", "*.sql"))):
    name = os.path.basename(path)
    if name in applied:
        continue
    sql = re.sub(r"--[^\n]*", "", open(path).read())   # strip line comments before splitting on ";"
    try:
        with engine.begin() as conn:
            for stmt in sql.split(";"):
                if stmt.strip():
                    conn.execute(text(stmt))
            conn.execute(text("INSERT INTO schema_migrations (filename) VALUES (:n)"), {"n": name})
        print(f"OK    {name}")
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        sys.exit(1)
