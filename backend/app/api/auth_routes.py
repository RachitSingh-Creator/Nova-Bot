from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User).where(User.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(email=payload.email, full_name=payload.full_name, hashed_password=get_password_hash(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenPair(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    user_id = claims.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenPair(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))
