from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from database import close_db, get_db, init_db
    from models import User
    from security import hash_password, verify_password
except ImportError:
    from .database import close_db, get_db, init_db
    from .models import User
    from .security import hash_password, verify_password

try:
    from services.common.jwt_auth import create_access_token, get_current_user_id
except ImportError:
    try:
        from common.jwt_auth import create_access_token, get_current_user_id
    except ImportError:
        from .common.jwt_auth import create_access_token, get_current_user_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan to initialize database schema on startup and clean up on shutdown."""
    init_db()
    yield
    close_db()


app = FastAPI(
    title="CareerLens Auth Service",
    description="Authentication and JWT Token Service for CareerLens",
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
    """Ensure HTTP exceptions preserve the {"error": "..."} shape frontend consumes."""
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": str(exc.detail), "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Ensure validation errors preserve the {"error": "..."} shape frontend consumes."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid request body") if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": first_msg, "detail": errors},
    )


class SignupRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Registers a new user and returns JWT access token."""
    email_clean = request.email.strip().lower()
    full_name_clean = request.full_name.strip()

    if not email_clean or not request.password or not full_name_clean:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Full name, email, and password are required"},
        )

    # Check if user already exists
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Email already registered"},
        )

    # Hash password with Argon2
    hashed_pwd = hash_password(request.password)
    user = User(
        email=email_clean,
        full_name=full_name_clean,
        password_hash=hashed_pwd,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Email already registered"},
        )

    access_token = create_access_token(user.email)
    return {
        "status": "success",
        "user_id": user.email,
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user and returns JWT access token."""
    email_clean = request.email.strip().lower()

    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid email or password"},
        )

    if not verify_password(user.password_hash, request.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid email or password"},
        )

    access_token = create_access_token(user.email)
    return {
        "status": "success",
        "user_id": user.email,
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/me")
def get_me(current_user_id: str = Depends(get_current_user_id)):
    """Protected endpoint validating JWT token and returning user identity."""
    return {"status": "success", "user_id": current_user_id}
