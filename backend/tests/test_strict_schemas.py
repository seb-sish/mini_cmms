"""Строгость DTO: точные JSON-типы, обязательные поля, нормализация перед проверкой."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.equipment import EquipmentCreate
from app.schemas.fault import FaultCreate
from app.schemas.maintenance import MaintenancePlanCreate
from app.schemas.user import UserCreate
from app.schemas.work_order import WorkOrderComplete, WorkOrderCreate


def _equipment(**overrides) -> dict:
    payload = {
        "name": "Machine",
        "inventory_number": "EQ-STRICT-1",
        "category": "Machining",
        "location": "Shop",
        "commissioned_on": "2026-01-01",
        "status": "OPERATIONAL",
    }
    payload.update(overrides)
    return payload


def test_equipment_create_requires_status():
    payload = _equipment()
    payload.pop("status")
    with pytest.raises(ValidationError):
        EquipmentCreate(**payload)


def test_equipment_create_rejects_null_status():
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(status=None))


def test_equipment_create_rejects_numeric_date():
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(commissioned_on=20260101))


def test_equipment_create_rejects_datetime_string():
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(commissioned_on="2026-01-01T00:00:00"))


def test_equipment_create_rejects_numeric_string_fields():
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(name=123))
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(category=True))


def test_equipment_create_checks_length_after_trimming():
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(name="  "))
    with pytest.raises(ValidationError):
        EquipmentCreate(**_equipment(location="   "))


def test_plan_create_rejects_string_interval_and_short_name():
    with pytest.raises(ValidationError):
        MaintenancePlanCreate(
            name="Plan",
            scope="CATEGORY",
            category="Machining",
            interval_days="30",
            first_due_on=date(2026, 11, 1),
            checklist=[{"title": "Inspect", "required": True, "order": 1}],
        )
    with pytest.raises(ValidationError):
        MaintenancePlanCreate(
            name="  ",
            scope="CATEGORY",
            category="Machining",
            interval_days=30,
            first_due_on=date(2026, 11, 1),
            checklist=[{"title": "Inspect", "required": True, "order": 1}],
        )


def test_fault_create_rejects_description_shorter_than_minlength_after_trimming():
    with pytest.raises(ValidationError):
        FaultCreate(
            equipment_id="11111111-1111-4111-8111-111111111111",
            description="  abc  ",
            detected_on=date(2026, 1, 1),
            severity="LOW",
        )


def test_work_order_rejects_long_replaced_part():
    with pytest.raises(ValidationError):
        WorkOrderComplete(result="Done", replaced_parts=["p" * 201])


def test_user_create_rejects_numeric_login():
    with pytest.raises(ValidationError):
        UserCreate(login=12345, password="Password123!", role="ENGINEER")


def test_work_order_create_rejects_numeric_title():
    with pytest.raises(ValidationError):
        WorkOrderCreate(
            type="REPAIR",
            equipment_id="11111111-1111-4111-8111-111111111111",
            title=123,
            description="Description",
            priority="NORMAL",
        )
