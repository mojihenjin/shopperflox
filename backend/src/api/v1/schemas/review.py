from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import FitFeedback


class CreateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rating: int = Field(ge=1, le=5)
    fit_feedback: FitFeedback | None = None
    comment: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    product_id: UUID
    rating: int
    fit_feedback: FitFeedback | None = None
    comment: str | None = None
    created_at: datetime
