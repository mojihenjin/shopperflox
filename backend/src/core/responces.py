from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field


class BaseResponse[T](BaseModel):
    body: T
    status_code: int = Field(default=200)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResponseGenerator:
    @classmethod
    def answer(
        cls,
        body: str | Iterable | None = None,
        status_code: int = 200,
        errors: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        metadata_update: bool = True,
    ) -> BaseResponse:
        body = body or []
        errors = errors or []
        metadata = metadata or {}

        # Only required data
        metadata.update({"length": len(body) if isinstance(body, Iterable) else 0})

        if metadata_update:
            pass

        return BaseResponse(
            body=body, status_code=status_code, errors=errors, metadata=metadata
        )
