"""Общие примитивы строгой валидации по нормативному контракту.

Контракт требует точных JSON-типов и ограничений, проверяемых после
нормализации: строковое поле не принимает число, дата — только формат
YYYY-MM-DD, а ограничения длины проверяются на обрезанном значении.
"""

import re
from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator, StrictInt, StrictStr

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Строка без неявных преобразований: число или bool в строковое поле не принимаются.
StrictText = StrictStr

# Целое число без неявных преобразований: "5" и true не принимаются.
StrictInteger = StrictInt


def strict_date(value: Any) -> date:
    """Принимает дату в формате YYYY-MM-DD (объект date допускается из кода)."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError("date must be a string in YYYY-MM-DD format")
    return date.fromisoformat(value)


# Проверка выполняется до разбора: принимается только строка YYYY-MM-DD.
StrictDate = Annotated[date, BeforeValidator(strict_date)]


def _trimmed(min_length: int, max_length: int) -> Callable[[str], str]:
    def validate(value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < min_length:
            raise ValueError(f"value must contain at least {min_length} characters after trimming")
        if len(cleaned) > max_length:
            raise ValueError(f"value must contain at most {max_length} characters after trimming")
        return cleaned

    return validate


def Trimmed(min_length: int, max_length: int) -> Any:
    """Строгая строка, проверяемая по длине после обрезки пробелов."""
    return Annotated[StrictStr, AfterValidator(_trimmed(min_length, max_length))]
