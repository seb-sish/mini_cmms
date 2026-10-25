import pytest
from sqlalchemy import Column, Integer, String

from app.db.base import Base, TimestampMixin, VersionMixin


class DummyModel(Base, TimestampMixin, VersionMixin):
    __tablename__ = "dummy_model"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)


def test_model_mixins():
    instance = DummyModel(id=1, name="test")
    assert instance.version == 1
    assert hasattr(instance, "created_at")
    assert hasattr(instance, "updated_at")
