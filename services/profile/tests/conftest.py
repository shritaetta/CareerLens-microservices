import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import text

# Ensure service directory and root directory are in sys.path
service_dir = Path(__file__).resolve().parent.parent
root_dir = service_dir.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Configure environment variables for test execution
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/careerlens_auth",
)
os.environ.setdefault(
    "JWT_SECRET",
    "test_super_secret_jwt_key_that_is_at_least_32_bytes_long_careerlens",
)
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

from database import close_db, get_engine, init_db
from fastapi.testclient import TestClient
from main import app
from common.jwt_auth import create_access_token


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database schema is created at start and engine closed at end."""
    init_db()
    yield
    close_db()


@pytest.fixture(autouse=True)
def clean_profiles_table():
    """Truncate profiles table before each test for test isolation."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE profiles CASCADE"))
        conn.commit()
    yield


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def create_token():
    """Factory fixture to create valid Bearer tokens for any user_id."""
    def _create(user_id: str) -> str:
        return create_access_token(user_id)
    return _create
