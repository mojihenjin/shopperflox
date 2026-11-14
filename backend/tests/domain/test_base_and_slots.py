from dataclasses import dataclass
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.domain.models.base import BaseDomain


@dataclass(slots=True, kw_only=True)
class DummyDomain(BaseDomain):
    id: UUID
    name: str

    def some_method(self) -> str:
        return self.name


def test_base_domain_to_dict():
    dummy_id = uuid7()
    dummy = DummyDomain(id=dummy_id, name="Test")

    data = dummy.to_dict()
    assert data == {"id": dummy_id, "name": "Test"}
    assert "some_method" not in data


def test_base_domain_to_dict_with_exclude():
    dummy_id = uuid7()
    dummy = DummyDomain(id=dummy_id, name="Test")

    data = dummy.to_dict(exclude={"name"})
    assert data == {"id": dummy_id}


def test_slots_prevent_arbitrary_attributes():
    dummy_id = uuid7()
    dummy = DummyDomain(id=dummy_id, name="Test")

    with pytest.raises(AttributeError):
        dummy.unknown_field = "value"  # type: ignore
