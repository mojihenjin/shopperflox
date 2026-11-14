from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True, kw_only=True)
class BaseDomain:
    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        exclude = exclude or set()

        return {
            key: value
            for key, value in asdict(self).items()
            if key not in exclude and not callable(value)
        }
