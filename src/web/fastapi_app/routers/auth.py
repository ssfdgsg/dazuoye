"""认证路由"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Depends
from models.schemas import UserRegister, UserLogin, UserResponse, SessionResponse, Token
from dependencies import get_password_hash, verify_password, create_access_token, get_current_user_optional
from database import get_connection, ensure_tables

router = APIRouter(prefix="/api", tags=["认证"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister, response: Response):
    """用户注册"""
    conn = get_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    ensure_tables(cursor)
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=409, detail="用户名已被注册")
    
    password_hash = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (user.username, password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    # 生成 token
    token = create_access_token({"user_id": user_id, "username": user.username})
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=7 * 24 * 3600)
    
    return UserResponse(success=True, user_id=user_id, username=user.username)


@router.post("/login")
async def login(user: UserLogin, response: Response):
    """用户登录"""
    # 用户名密码登录
    if user.username:
        conn = get_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        ensure_tables(cursor)
        
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (user.username,),
        )
        db_user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not user.password or not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        token = create_access_token({"user_id": db_user["id"], "username": db_user["username"]})
        response.set_cookie(key="session_token", value=token, httponly=True, max_age=7 * 24 * 3600)
        
        return {"success": True, "user_id": db_user["id"], "username": db_user["username"], "access_token": token}
    
    # 兼容旧版 user_id 登录
    if user.user_id:
        conn = get_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)
        cursor.execute(
            "SELECT DISTINCT user_id FROM user_ratings WHERE user_id = %s LIMIT 1",
            (user.user_id,),
        )
        db_user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if db_user:
            token = create_access_token({"user_id": user.user_id})
            response.set_cookie(key="session_token", value=token, httponly=True, max_age=7 * 24 * 3600)
            return {"success": True, "user_id": user.user_id, "access_token": token}
        raise HTTPException(status_code=404, detail="User not found")
    
    raise HTTPException(status_code=400, detail="请提供用户名/密码或 user_id")


@router.post("/logout")
async def logout(response: Response):
    """用户登出"""
    response.delete_cookie(key="session_token")
    return {"success": True}


@router.get("/session", response_model=SessionResponse)
async def get_session(user: Optional[dict] = Depends(get_current_user_optional)):
    """获取当前会话"""
    if user:
        return SessionResponse(logged_in=True, user_id=user.get("user_id"), username=user.get("username"))
    return SessionResponse(logged_in=False, user_id=None, username=None)
