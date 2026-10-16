from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

try:
    from database import close_db, get_db, init_db
    from models import Profile
except ImportError:
    from .database import close_db, get_db, init_db
    from .models import Profile

try:
    from services.common.jwt_auth import get_current_user_id
except ImportError:
    try:
        from common.jwt_auth import get_current_user_id
    except ImportError:
        from .common.jwt_auth import get_current_user_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan to initialize database schema on startup and clean up on shutdown."""
    init_db()
    yield
    close_db()


app = FastAPI(
    title="CareerLens Profile Service",
    description="Profile persistence and retrieval service for CareerLens",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Preserve {"error": "..."} shape consumed by the frontend."""
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": str(exc.detail), "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Preserve {"error": "..."} shape for request validation errors."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid request body") if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": first_msg, "detail": errors},
    )


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/profile/{user_id}")
def get_user_profile(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Fetches user profile. Requires Bearer JWT. user_id must equal token sub."""
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: cannot access another user's profile",
        )

    profile = db.get(Profile, user_id)
    if not profile:
        return {"error": "Profile not found"}
    return {"user_id": user_id, "profile_data": profile.profile_data}


@app.post("/profile/{user_id}")
def save_user_profile(
    user_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Saves or updates user profile. Requires Bearer JWT. user_id must equal token sub."""
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: cannot modify another user's profile",
        )

    profile = db.get(Profile, user_id)
    now = datetime.now(timezone.utc)
    if profile:
        profile.profile_data = payload
        profile.updated_at = now
    else:
        profile = Profile(
            user_id=user_id,
            profile_data=payload,
            updated_at=now,
        )
        db.add(profile)

    db.commit()
    return {"status": "success"}
