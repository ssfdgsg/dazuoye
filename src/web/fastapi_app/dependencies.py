"""依赖注入"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import get_settings

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.access_token_expire_days))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None, alias="session_token"),
) -> Optional[dict]:
    """获取当前用户（可选，未登录返回 None）"""
    token = None
    if credentials:
        token = credentials.credentials
    elif session_token:
        token = session_token
    
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    return {"user_id": payload.get("user_id"), "username": payload.get("username")}


async def get_current_user(
    user: Optional[dict] = Depends(get_current_user_optional),
) -> dict:
    """获取当前用户（必须登录）"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
