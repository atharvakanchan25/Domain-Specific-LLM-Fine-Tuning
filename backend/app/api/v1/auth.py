from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import ConflictError, UnauthorizedError
from app.repositories.user import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise ConflictError("Email already registered")
    if await repo.get_by_username(body.username):
        raise ConflictError("Username already taken")
    user = await repo.create(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedError("Invalid credentials")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
