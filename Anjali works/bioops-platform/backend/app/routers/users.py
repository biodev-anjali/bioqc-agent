from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.all_models import User
from app.schemas.all_schemas import UserOut, UserUpdate, PasswordUpdate
from app.core.security import verify_password, hash_password
from app.core.exceptions import UnauthorizedError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
async def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/me/password", status_code=204)
async def update_password(body: PasswordUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect.")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()