from dataclasses import dataclass, field

import pytest

from src.domain.models import BaseDomain


@dataclass()
class DummyDomain(BaseDomain):
    id: int = field(default=0)
    firstname: str = field(default="test")
    lastname: str = field(default="test")


@pytest.mark.parametrize(
    "body, answer",
    (
        ["TEST", 0],
        [[0, 1], 2],
        [{"test": True, "tested": False, "blah": "bruh"}, 3],
        [{"mama", "papa", "sister", "me"}, 4],
        [(0, 1, 2, 3, 4), 5],
        [DummyDomain(), 3],
        [1, 0],
    ),
)
def test_get_len(body, answer):
    from src.utils import get_len

    assert get_len(body) == answer
