import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_jwt_expire_minutes() -> int:
    try:
        return int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=get_jwt_expire_minutes())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()
    return jwt.decode(token, secret, algorithms=[algorithm])


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """FastAPI dependency to extract and validate current user id from Bearer token."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: missing sub",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(user_id)
