"""Project-wide pytest setup. Pytest guarantees conftest.py files load
before any test module in their scope is collected — a root-level one
like this applies to the whole project, always first.

Needed because DATABASE_URL must be set to an isolated file BEFORE
server.py is ever imported (its own Base.metadata.create_all() runs
unconditionally at import time against whatever DATABASE_URL resolves
to). Putting this in each test file that needs it individually (as
test_worker.py and test_chat.py each originally did) is fragile: Python
only executes a module's top-level code once, so whichever file pytest
happens to collect first "wins" the actual server.py import, and every
other file's own DATABASE_URL assignment silently does nothing — this
was found for real (test users leaking into the actual local
chat_dev.db on a full-suite run, not just a single-file run) rather
than reasoned out in advance. A single root conftest.py, guaranteed to
run before every test file, avoids that class of bug entirely.
"""

import os
import tempfile

# Host shells sometimes export FLASK_ENV=production. Tests must not inherit
# fail-closed production boot (REDIS_URL / ClamAV / OAuth secrets).
for _prod_key in ("FLASK_ENV", "APP_ENV"):
    if (os.environ.get(_prod_key) or "").strip().lower() == "production":
        os.environ[_prod_key] = "testing"
os.environ.setdefault("RATE_LIMIT_MEMORY_OK", "1")
os.environ.setdefault("CLAMAV_OPTIONAL", "1")

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
