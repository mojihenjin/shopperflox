from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.utils import get_len


class BaseResponse[T](BaseModel):
    body: T | None = None
    status_code: int = Field(default=200)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResponseGenerator:
    @classmethod
    def answer(
        cls,
        body: Any = None,
        status_code: int = 200,
        errors: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        metadata_update: bool = True,
    ) -> BaseResponse:
        errors = errors or []
        meta = (metadata or {}).copy()

        # Only required data
        meta.update({"length": get_len(body=body)})

        if metadata_update:
            pass

        return BaseResponse(
            body=body, status_code=status_code, errors=errors, metadata=meta
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
