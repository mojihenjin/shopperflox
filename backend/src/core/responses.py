from collections.abc import Iterable
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class BaseResponse[T](BaseModel):
    body: T | None = None
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
        if body is None:
            body = []

        errors = errors or []
        metadata = metadata or {}
        meta = metadata.copy()

        # Only required data
        meta.update(
            {"length": len(body) if isinstance(body, list | tuple | set | dict) else 0}
        )

        if metadata_update:
            pass

        return BaseResponse(
            body=body, status_code=status_code, errors=errors, metadata=metadata
        )

    @classmethod
    def json_error(
        cls,
        status_code: int,
        errors: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> JSONResponse:
        payload = cls.answer(
            body=None,
            status_code=status_code,
            errors=errors,
            metadata=metadata,
            metadata_update=False,
        )
        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(mode="json"),
        )
