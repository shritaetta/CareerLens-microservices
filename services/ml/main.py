from contextlib import asynccontextmanager
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from services.common.jwt_auth import get_current_user_id
except ImportError:
    try:
        from common.jwt_auth import get_current_user_id
    except ImportError:
        from .common.jwt_auth import get_current_user_id

from data_loader import InternshipDataLoader
from feedback_store import RedisFeedbackStore
from resume_enhancer import ResumeEnhancer

loader = InternshipDataLoader()
feedback_store = RedisFeedbackStore()
enhancer: Optional[ResumeEnhancer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler:
    1. Loads dataset from DATASET_PATH.
    2. Initializes SentenceTransformer model and computes/loads cached embeddings.
    3. Initializes ResumeEnhancer.
    4. Connects to Redis for feedback persistence.
    """
    global enhancer
    dataset_path = os.getenv("DATASET_PATH", "data/Book2.xlsx")
    print(f"Lifespan startup: loading dataset from {dataset_path}...")
    loader.load_data(file_path=dataset_path)
    enhancer = ResumeEnhancer(loader.model)

    try:
        feedback_store.client.ping()
        print("Lifespan startup: Redis connection confirmed.")
    except Exception as e:
        print(f"Lifespan startup Redis connection notice: {e}")

    yield

    # Shutdown logic
    print("Lifespan shutdown: closing Redis connection...")
    feedback_store.close()


app = FastAPI(
    title="CareerLens ML Recommendation & Enhancement Service",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfileRequest(BaseModel):
    user_id: Optional[str] = "default_user"  # Ignored; token sub takes precedence
    skills: List[str] = []
    education: Optional[str] = ""
    achievements: Optional[str] = ""
    resume_text: Optional[str] = ""
    certificate_text: Optional[str] = ""


class FeedbackRequest(BaseModel):
    user_id: Optional[str] = "default_user"  # Ignored; token sub takes precedence
    internship_id: str
    reason: str
    metadata: Dict[str, Any] = {}


class ATSEvaluationRequest(BaseModel):
    resume_text: str
    internship_id: str
    user_skills: List[str]


@app.get("/health")
def health():
    """Returns 200 only after the model, dataset, and embeddings are loaded."""
    if loader.is_ready():
        return {"status": "ok"}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"status": "not ready", "error": "Model or embeddings not loaded"},
    )


@app.get("/internships/light")
def get_lightweight_internships(
    current_user_id: str = Depends(get_current_user_id),
):
    """Returns only ID and Title for dropdowns."""
    if not loader.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model and dataset not ready",
        )
    return loader.get_all_light()


@app.post("/evaluate_ats")
def evaluate_resume_ats(
    request: ATSEvaluationRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """ATS scoring comparing resume text and skills against target internship."""
    if not loader.is_ready():
        return {"error": "Model not loaded"}
    return loader.evaluate_ats(
        resume_text=request.resume_text,
        internship_id=request.internship_id,
        user_skills=request.user_skills,
    )


@app.post("/enhance_profile")
def enhance_profile(
    payload: Dict[str, Any],
    current_user_id: str = Depends(get_current_user_id),
):
    """Processes profile data to categorize skills, improve action verbs, etc."""
    if not enhancer:
        return {"error": "Enhancer not initialized"}
    try:
        enhanced = enhancer.process_profile(payload)
        return {"status": "success", "enhanced_profile": enhanced}
    except Exception as e:
        return {"error": str(e)}


@app.post("/feedback")
def handle_feedback(
    feedback: FeedbackRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Records negative feedback constraint into Redis under feedback:{user_id}.
    Ignores feedback.user_id in body and strictly binds to current_user_id from JWT sub.
    """
    uid = current_user_id
    user_constraints = feedback_store.record_feedback(
        user_id=uid,
        internship_id=feedback.internship_id,
        reason=feedback.reason,
        metadata=feedback.metadata,
    )
    return {
        "status": "success",
        "constraints_updated": True,
        "active_constraints": user_constraints,
    }


@app.post("/recommend")
def recommend_internships(
    profile: ProfileRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Generates top 3 recommendations filtered against user constraints in Redis.
    Ignores profile.user_id in body and strictly binds to current_user_id from JWT sub.
    """
    unified_text_parts = []

    if profile.skills:
        unified_text_parts.append(f"Skills: {', '.join(profile.skills)}")
    if profile.education:
        unified_text_parts.append(f"Education: {profile.education}")
    if profile.achievements:
        unified_text_parts.append(f"Achievements: {profile.achievements}")
    if profile.resume_text:
        unified_text_parts.append(f"Resume: {profile.resume_text}")
    if profile.certificate_text:
        unified_text_parts.append(f"Certificates: {profile.certificate_text}")

    unified_profile_text = " | ".join(unified_text_parts)

    # Ignore user_id in payload, use JWT sub
    uid = current_user_id
    constraints = feedback_store.get_constraints(uid)

    recommendations = loader.get_recommendations(
        unified_profile_text,
        top_n=3,
        constraints=constraints,
    )
    return recommendations
