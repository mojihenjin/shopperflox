from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Uuid
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: Uuid(as_uuid=True),
        datetime: TIMESTAMP(timezone=True).with_variant(
            DateTime(timezone=True), "sqlite"
        ),
        dict[str, Any]: JSONB().with_variant(JSON(), "sqlite"),
        list[str]: JSONB().with_variant(JSON(), "sqlite"),
    }
