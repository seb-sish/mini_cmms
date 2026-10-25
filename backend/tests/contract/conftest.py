from collections.abc import Callable
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tests.contract.oracle import load_spec


@pytest.fixture(scope="session")
def openapi_spec() -> dict[str, Any]:
    return load_spec()


@pytest.fixture(scope="session")
def format_checker() -> FormatChecker:
    checker = FormatChecker()
    for name in ("date", "date-time", "uuid", "uri-reference"):
        if name not in checker.checkers:
            raise RuntimeError(f"Missing jsonschema format checker: {name}")
    return checker


@pytest.fixture(scope="session")
def schema_validator(
    openapi_spec: dict[str, Any], format_checker: FormatChecker
) -> Callable[[dict[str, Any], Any], list[str]]:
    """Returns a validator function that validates payload against an OpenAPI schema or sub-schema."""

    def _validate(schema: dict[str, Any], payload: Any) -> list[str]:
        wrapped = {"allOf": [schema], "components": openapi_spec.get("components", {})}
        validator = Draft202012Validator(wrapped, format_checker=format_checker)
        return [f"{list(err.absolute_path)}: {err.message}" for err in validator.iter_errors(payload)]

    return _validate
