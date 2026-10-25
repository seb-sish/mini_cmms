from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate YAML key at line {node.start_mark.line + 1}")
        return super().construct_mapping(node, deep=deep)


@pytest.fixture(scope="session")
def openapi_spec() -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    spec_path = project_root / "docs" / "Mini_CMMS_OpenAPI_3.1.1.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"OpenAPI spec file not found at {spec_path}")
    
    spec = yaml.load(spec_path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    validate(spec)
    return spec


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
