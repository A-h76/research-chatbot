import pytest
import importlib.util
import os


def find_flask_app():
    """Finds your Flask app by scanning common filenames."""
    possible_files = ["app.py", "run.py", "main.py", "wsgi.py", "backend/app.py"]
    for filename in possible_files:
        if os.path.exists(filename):
            spec = importlib.util.spec_from_file_location("app_module", filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "app"):
                return module.app
            if hasattr(module, "application"):
                return module.application
    raise Exception("Could not find your Flask app! Please check your main filename.")


def get_db(app):
    """Safely gets the SQLAlchemy db instance from the app."""
    # Method 1: Check if 'db' is attached directly to the app
    if hasattr(app, "db"):
        return app.db

    # Method 2: Check Flask extensions (recommended)
    if "sqlalchemy" in app.extensions:
        return app.extensions["sqlalchemy"].db

    return None


@pytest.fixture(scope="session")
def app():
    """Create a test app with in-memory DB."""
    app = find_flask_app()

    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STORAGE_BACKEND": "local",
            "WTF_CSRF_ENABLED": False,
            "LOGIN_DISABLED": True,
            "SERVER_NAME": "localhost",
            "SECRET_KEY": "test-secret-key",
            "RATELIMIT_ENABLED": False,
        }
    )

    with app.app_context():
        db = get_db(app)
        if db:
            db.create_all()
        yield app
        # Cleanup after tests
        if db:
            db.drop_all()


@pytest.fixture
def client(app):
    """Return a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Return a CLI runner."""
    return app.test_cli_runner()
