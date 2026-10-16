import os
from pathlib import Path
import sys
import fakeredis
from fastapi.testclient import TestClient
import pytest

# Ensure services/ml and repo root are in sys.path
service_dir = Path(__file__).resolve().parent.parent
repo_root = service_dir.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

os.environ.setdefault(
    "JWT_SECRET", "test_jwt_secret_for_careerlens_ml_tests_minimum_32_characters"
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("DATASET_PATH", str(repo_root / "data" / "Book2.xlsx"))
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from common.jwt_auth import create_access_token
from data_loader import InternshipDataLoader, MockSentenceTransformer
from feedback_store import RedisFeedbackStore
from main import app
from resume_enhancer import ResumeEnhancer


@pytest.fixture(scope="session")
def shared_loader():
    """Initializes and loads dataset and model for test execution."""
    loader = InternshipDataLoader(file_path=os.environ["DATASET_PATH"])
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        model = MockSentenceTransformer()
    loader.load_data(model=model)
    return loader


@pytest.fixture(scope="session")
def shared_enhancer(shared_loader):
    """Initializes ResumeEnhancer using the shared model."""
    return ResumeEnhancer(shared_loader.model)


@pytest.fixture
def fake_redis():
    """Provides an isolated fake redis instance for testing."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield client
    client.flushall()
    client.close()


@pytest.fixture
def token_factory():
    """Factory fixture to create valid Bearer tokens for any user_id."""
    def _create(user_id: str = "test_user@careerlens.local") -> str:
        return create_access_token(user_id)
    return _create


@pytest.fixture
def client(fake_redis, shared_loader, shared_enhancer):
    """FastAPI TestClient with shared loader and fake redis injected."""
    import main
    main.loader = shared_loader
    main.enhancer = shared_enhancer
    main.feedback_store = RedisFeedbackStore(redis_client=fake_redis)

    with TestClient(app) as test_client:
        yield test_client
