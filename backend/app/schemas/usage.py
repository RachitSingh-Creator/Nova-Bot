from decimal import Decimal
from pydantic import BaseModel


class UsageSummary(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: Decimal
