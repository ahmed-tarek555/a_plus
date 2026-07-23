import os
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, status
from jose import jwt, JWTError


SECRET_KEY = os.getenv("TOKEN_SECRET_KEY")
ALGORITHM = os.getenv("TOKEN_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 240


def create_access_token(data: dict) -> str:

    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_jwt

def get_current_user(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

def validate_user(token):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = get_current_user(token)
    user_id = payload["sub"]
    user_role = payload["role"]
    return int(user_id), user_role