from dataclasses import fields, is_dataclass
from typing import Any

from pydantic import BaseModel


def get_len(body: Any) -> int:
    if isinstance(body, list | dict | set | tuple):
        return len(body)
    if isinstance(body, BaseModel):
        return len(type(body).model_fields)
    if is_dataclass(body) and not isinstance(body, type):
        return len(fields(body))

    return 0
