from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
from passlib.context import CryptContext
from jose import jwt, JWTError

from erin.api.core.config import settings
from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models.auth import (
    UserCreate, UserLogin, Token, TokenData, UserResponse,
    MFASetup, MFAVerify, PasswordChange
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_sqlite_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (token_data.username,))
        user = cursor.fetchone()
        if user is None:
            raise credentials_exception
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user.username, user.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        hashed_password = get_password_hash(user.password)
        user_id = secrets.token_urlsafe(16)
        roles = '["VIEWER"]'
        now = datetime.utcnow()
        
        conn.execute(
            """INSERT INTO users (id, username, email, password_hash, roles, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, user.username, user.email, hashed_password, roles, now, now)
        )
        
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        return UserResponse(**dict(user_row))

@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
        user = cursor.fetchone()
        if not user or not verify_password(form_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user["locked_until"] and datetime.utcnow() < datetime.fromisoformat(user["locked_until"]):
            raise HTTPException(status_code=403, detail="Account temporarily locked")
        
        # Check MFA if enabled
        if user["mfa_enabled"] and not form_data.mfa_code:
            raise HTTPException(status_code=400, detail="MFA code required")
        
        # Reset failed attempts on success
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0, last_login = ?, locked_until = NULL WHERE id = ?",
            (datetime.utcnow(), user["id"])
        )
        
        access_token = create_access_token(data={"sub": user["username"]})
        refresh_token = create_refresh_token(data={"sub": user["username"]})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
            user=UserResponse(**dict(user))
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        with sqlite_transaction() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
        
        access_token = create_access_token(data={"sub": username})
        new_refresh_token = create_refresh_token(data={"sub": username})
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
            user=UserResponse(**dict(user))
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/logout")
async def logout(current_user = Depends(get_current_active_user)):
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_active_user)):
    return UserResponse(**dict(current_user))

@router.post("/mfa/setup", response_model=MFASetup)
async def setup_mfa(current_user = Depends(get_current_active_user)):
    import pyotp
    secret = pyotp.random_base32()
    with sqlite_transaction() as conn:
        conn.execute("UPDATE users SET mfa_secret = ?, mfa_enabled = 0 WHERE id = ?", (secret, current_user["id"]))
    
    uri = pyotp.totp.TOTP(secret).provisioning_uri(current_user["username"], issuer_name="ERIN")
    return MFASetup(secret=secret, uri=uri)

@router.post("/mfa/verify", response_model=dict)
async def verify_mfa(verify: MFAVerify, current_user = Depends(get_current_active_user)):
    import pyotp
    with sqlite_transaction() as conn:
        cursor = conn.execute("SELECT mfa_secret FROM users WHERE id = ?", (current_user["id"],))
        user = cursor.fetchone()
        if not user or not user["mfa_secret"]:
            raise HTTPException(status_code=400, detail="MFA not set up")
        
        totp = pyotp.TOTP(user["mfa_secret"])
        if not totp.verify(verify.code):
            raise HTTPException(status_code=400, detail="Invalid MFA code")
        
        conn.execute("UPDATE users SET mfa_enabled = 1 WHERE id = ?", (current_user["id"],))
        return {"message": "MFA enabled successfully"}

@router.post("/password/change", response_model=dict)
async def change_password(change: PasswordChange, current_user = Depends(get_current_active_user)):
    if not verify_password(change.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if change.new_password != change.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    hashed = get_password_hash(change.new_password)
    with sqlite_transaction() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, current_user["id"]))
    return {"message": "Password changed successfully"}

# Missing imports
from typing import Optional
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")