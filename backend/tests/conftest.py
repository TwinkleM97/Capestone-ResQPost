import os
import pytest

# Force a fast, isolated DB for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app as flask_app, db  # uses DATABASE_URL above

@pytest.fixture(scope="function")
def app():
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=os.environ["DATABASE_URL"],
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    with flask_app.app_context():
        db.create_all()
    yield flask_app
    with flask_app.app_context():
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()
