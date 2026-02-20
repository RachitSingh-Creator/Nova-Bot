from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usage import UsageLog
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.usage import UsageSummary
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/usage/summary", response_model=UsageSummary)
async def usage_summary(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(UsageLog.completion_tokens), 0),
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.coalesce(func.sum(UsageLog.estimated_cost_usd), Decimal("0.0")),
        ).where(UsageLog.user_id == user.id)
    )
    prompt_tokens, completion_tokens, total_tokens, total_cost = result.one()
    return UsageSummary(
        total_prompt_tokens=int(prompt_tokens),
        total_completion_tokens=int(completion_tokens),
        total_tokens=int(total_tokens),
        total_estimated_cost_usd=total_cost,
    )
