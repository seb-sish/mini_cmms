"""Oracle проверки фактических HTTP-ответов по нормативной OpenAPI.

Статические проверки схем не заменяют проверку реального ответа: статус,
тело и заголовки сверяются с контрактом для конкретной операции.
"""

import re
from pathlib import Path
from typing import Any

import yaml
from httpx import Response
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT_ROOT / "docs" / "Mini_CMMS_OpenAPI_3.1.1.yaml"

# Поля, значения которых зависят от времени или окружения и не сверяются.
VOLATILE_RESPONSE_FIELDS = frozenset(
    {
        "access_token",
        "token_type",
        "expires_at",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "checked_at",
        "archived_at",
        "revoked_at",
        "occurred_at",
        "id",
        "number",
        "planned_due_on",
        "next_due_on",
        "detected_on",
        "commissioned_on",
        "instance",
        "detail",
        # Заголовок title — человекочитаемая подпись, контракт её не фиксирует;
        # нормативными остаются type, status и code.
        "title",
    }
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Загрузчик YAML, отвергающий повторяющиеся ключи."""

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate YAML key at line {node.start_mark.line + 1}")
        return super().construct_mapping(node, deep=deep)


def load_spec() -> dict[str, Any]:
    """Читает и проверяет нормативную OpenAPI-спецификацию."""
    spec = yaml.load(SPEC_PATH.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    validate(spec)
    return spec


def build_oracle(spec: dict[str, Any]) -> "ContractOracle":
    """Собирает oracle со встроенным валидатором схем."""
    checker = FormatChecker()
    for name in ("date", "date-time", "uuid", "uri-reference"):
        if name not in checker.checkers:
            raise RuntimeError(f"Missing jsonschema format checker: {name}")

    def _validate(schema: dict[str, Any], payload: Any) -> list[str]:
        wrapped = {"allOf": [schema], "components": spec.get("components", {})}
        validator = Draft202012Validator(wrapped, format_checker=checker)
        return [f"{list(err.absolute_path)}: {err.message}" for err in validator.iter_errors(payload)]

    return ContractOracle(spec, _validate)


class ContractViolation(AssertionError):
    """Фактический ответ не соответствует нормативному контракту."""


class ContractOracle:
    def __init__(self, spec: dict[str, Any], schema_validator) -> None:
        self._spec = spec
        self._validate = schema_validator
        self._servers = spec.get("servers") or []
        self._prefix = self._servers[0].get("url", "") if self._servers else ""
        self._paths: dict[str, dict[str, Any]] = spec.get("paths") or {}
        self._templates = [(self._pattern(template), template) for template in self._paths]

    @staticmethod
    def _pattern(template: str) -> re.Pattern[str]:
        parts = re.split(r"(\{[^}]+\})", template)
        return re.compile("^" + "".join("[^/]+" if p.startswith("{") else re.escape(p) for p in parts) + "$")

    def resolve(self, method: str, path: str) -> tuple[str, dict[str, Any]]:
        """Возвращает шаблон пути и описание операции для фактического запроса."""
        relative = path[len(self._prefix) :] if self._prefix and path.startswith(self._prefix) else path
        relative = relative or "/"
        if relative in self._paths:
            operation = self._paths[relative].get(method.lower())
            if operation is not None:
                return relative, operation
        for pattern, template in self._templates:
            if not pattern.match(relative):
                continue
            operation = self._paths[template].get(method.lower())
            if operation is not None:
                return template, operation
        raise ContractViolation(f"Операция {method.upper()} {path} отсутствует в контракте")

    def assert_response(
        self,
        response: Response,
        method: str,
        path: str,
        *,
        expected_status: int | None = None,
    ) -> dict[str, Any]:
        """Проверяет фактический ответ: статус документирован, тело соответствует схеме."""
        template, operation = self.resolve(method, path)
        responses = operation.get("responses") or {}
        status = str(response.status_code)
        if status not in responses:
            documented = ", ".join(sorted(responses))
            raise ContractViolation(
                f"{method.upper()} {template} вернул недокументированный статус {status} (документированы: {documented})"
            )
        if expected_status is not None and response.status_code != expected_status:
            raise ContractViolation(
                f"{method.upper()} {template}: ожидался статус {expected_status}, получен {response.status_code}"
            )

        response_spec = responses[status] or {}
        content = response_spec.get("content") or {}
        json_content = content.get("application/json") or content.get("application/problem+json") or {}
        schema = json_content.get("schema")

        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError as exc:
                raise ContractViolation(f"{method.upper()} {template}: тело ответа не является JSON: {exc}") from exc

        if schema is not None and payload is not None:
            errors = self._validate(schema, payload)
            if errors:
                raise ContractViolation(f"{method.upper()} {template}: тело не соответствует схеме: {errors}")

        for header_name, header_spec in (response_spec.get("headers") or {}).items():
            if not header_spec.get("required"):
                continue
            if header_name not in response.headers:
                raise ContractViolation(
                    f"{method.upper()} {template}: отсутствует обязательный заголовок {header_name}"
                )

        return payload if isinstance(payload, dict) else {}

    def assert_fields(self, payload: dict[str, Any], expected: dict[str, Any], *, context: str) -> None:
        """Сверяет стабильные поля ожидаемого тела с фактическим (рекурсивно)."""
        self._compare(payload, expected, context=context, path="")

    def _compare(self, payload: Any, expected: Any, *, context: str, path: str) -> None:
        if isinstance(expected, dict):
            if not isinstance(payload, dict):
                raise ContractViolation(
                    f"{context}: ожидался объект по пути '{path or 'body'}', получен {type(payload).__name__}"
                )
            for key, value in expected.items():
                if key in VOLATILE_RESPONSE_FIELDS or key.endswith(("_at", "_on")):
                    continue
                if key not in payload:
                    raise ContractViolation(f"{context}: в ответе нет поля '{path}{key}'")
                self._compare(payload[key], value, context=context, path=f"{path}{key}.")
            return
        if isinstance(expected, list):
            if not isinstance(payload, list) or len(payload) != len(expected):
                raise ContractViolation(f"{context}: список по пути '{path or 'body'}' не совпадает с ожидаемым")
            for index, item in enumerate(expected):
                self._compare(payload[index], item, context=context, path=f"{path}{index}.")
            return
        if payload != expected:
            raise ContractViolation(
                f"{context}: поле '{path[:-1] or 'body'}' ожидалось {expected!r}, получено {payload!r}"
            )
