from datetime import timedelta
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from common.jwt_auth import (
    create_access_token,
    decode_access_token,
    get_current_user_id,
)


def test_create_and_decode_token():
    token = create_access_token("test@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "test@example.com"
    assert "exp" in payload


def test_expired_token_decode():
    token = create_access_token("test@example.com", expires_delta=timedelta(seconds=-5))
    with pytest.raises(HTTPException) as exc_info:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        get_current_user_id(credentials)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_get_current_user_id_success():
    token = create_access_token("verified@example.com")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user_id = get_current_user_id(credentials)
    assert user_id == "verified@example.com"


def test_get_current_user_id_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(None)
    assert exc_info.value.status_code == 401
