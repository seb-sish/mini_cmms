from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


@pytest.mark.contract
def test_openapi_spec_metadata(openapi_spec: dict[str, Any]):
    """Verifies basic OpenAPI 3.1.1 spec requirements."""
    assert openapi_spec.get("openapi") == "3.1.1", "Spec must target OpenAPI 3.1.1"
    servers = openapi_spec.get("servers", [])
    assert len(servers) > 0, "Spec must define servers"
    assert servers[0].get("url") == "/api/v1", "Base path must be /api/v1"


@pytest.mark.contract
def test_all_component_schemas_are_valid_draft202012(openapi_spec: dict[str, Any]):
    """Ensures every schema declared in components.schemas conforms to Draft 2020-12."""
    schemas = openapi_spec.get("components", {}).get("schemas", {})
    assert len(schemas) > 0, "No schemas found in openapi_spec"

    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            pytest.fail(f"Schema '{name}' is not valid Draft 2020-12 schema: {exc}")


@pytest.mark.contract
def test_operation_examples_validate_successfully(
    openapi_spec: dict[str, Any], schema_validator: Callable[[dict[str, Any], Any], list[str]]
):
    """Ensures examples declared on operations in paths pass validation."""
    validated_examples = 0

    for path, path_item in openapi_spec.get("paths", {}).items():
        for method, op in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            oid = op.get("operationId", f"{method} {path}")

            # Request body examples
            request_body = op.get("requestBody", {})
            for content in request_body.get("content", {}).values():
                schema = content.get("schema", {})
                for ex_name, example in content.get("examples", {}).items():
                    val = example.get("value")
                    errors = schema_validator(schema, val)
                    assert not errors, f"{oid} request example '{ex_name}' failed: {errors}"
                    validated_examples += 1

            # Response examples
            for status, resp in op.get("responses", {}).items():
                for content in resp.get("content", {}).values():
                    schema = content.get("schema", {})
                    for ex_name, example in content.get("examples", {}).items():
                        val = example.get("value")
                        errors = schema_validator(schema, val)
                        assert not errors, f"{oid} response {status} example '{ex_name}' failed: {errors}"
                        validated_examples += 1

    assert validated_examples > 50, f"Expected >50 examples validated, got {validated_examples}"


@pytest.mark.contract
def test_negative_probes_detect_schema_violations(
    openapi_spec: dict[str, Any], schema_validator: Callable[[dict[str, Any], Any], list[str]]
):
    """Verifies that schema_validator strictly rejects schema violations and mutations."""
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    user_schema = schemas.get("User")
    assert user_schema is not None

    user_example = {
        "id": "33333333-3333-4333-8333-333333333333",
        "login": "tech.ivanov",
        "role": "TECHNICIAN",
        "status": "ACTIVE",
        "created_at": "2026-10-23T14:00:00Z",
        "updated_at": "2026-10-23T14:00:00Z",
        "version": 1,
    }

    # Positive baseline
    base_errors = schema_validator(user_schema, user_example)
    assert not base_errors, f"Base example must be valid: {base_errors}"

    # Probe A: Extra forbidden property
    mutated_extra = deepcopy(user_example)
    mutated_extra["unknown_payload_field"] = "hacked"
    errors = schema_validator(user_schema, mutated_extra)
    assert errors, "Validator must reject unknown extra property"

    # Probe B: Invalid enum value for role
    mutated_enum = deepcopy(user_example)
    mutated_enum["role"] = "SUPER_USER"
    errors = schema_validator(user_schema, mutated_enum)
    assert errors, "Validator must reject invalid enum value"

    # Probe C: Missing required field
    mutated_missing = deepcopy(user_example)
    mutated_missing.pop("id", None)
    errors = schema_validator(user_schema, mutated_missing)
    assert errors, "Validator must reject missing required field 'id'"

    # Probe D: Invalid date-time without timezone / malformed
    mutated_date = deepcopy(user_example)
    mutated_date["created_at"] = "2026-10-25 12:00:00"  # Missing T and Z
    errors = schema_validator(user_schema, mutated_date)
    assert errors, "Validator must reject malformed date-time"

    # Probe E: Invalid UUID format
    mutated_uuid = deepcopy(user_example)
    mutated_uuid["id"] = "not-a-valid-uuid"
    errors = schema_validator(user_schema, mutated_uuid)
    assert errors, "Validator must reject invalid UUID"
