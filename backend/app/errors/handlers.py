import inspect
import json
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.exceptions import AppException
from app.schemas.common import ProblemDetail, ValidationErrorItem

# Публичные точки с телом: для них разбор тела не требует аутентификации.
PUBLIC_BODY_PATHS = frozenset({"/api/v1/auth/login"})


def _replay_receive(body: bytes):
    """Возвращает канал, отдающий уже прочитанное тело запроса."""

    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _openapi_path_pattern(template: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[^}]+\})", template)
    return re.compile("^" + "".join("[^/]+" if p.startswith("{") else re.escape(p) for p in parts) + "$")


def _allowed_methods(app, path: str) -> str:
    """Разрешённые для пути методы берутся из нормативной OpenAPI-спецификации."""
    try:
        schema = app.openapi()
    except Exception:
        return ""
    servers = schema.get("servers") or []
    prefix = servers[0].get("url", "") if servers else ""
    relative = path[len(prefix) :] if prefix and path.startswith(prefix) else path
    relative = relative or "/"

    methods: set[str] = set()
    for template, operations in (schema.get("paths") or {}).items():
        if not _openapi_path_pattern(template).match(relative):
            continue
        for method in operations:
            if method in ("get", "post", "put", "patch", "delete"):
                methods.add(method.upper())
    return ", ".join(sorted(methods))


async def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@asynccontextmanager
async def _probe_session(request: Request):
    """Сессия для проверки токена: та же, что использует приложение (включая override в тестах)."""
    from app.db.session import SessionManager, get_session

    override = request.app.dependency_overrides.get(get_session)
    if override is not None:
        candidate = override()
        if inspect.isawaitable(candidate):
            candidate = await candidate
        if hasattr(candidate, "__anext__"):
            async for sess in candidate:
                yield sess
                break
        else:
            yield candidate
        return
    session_maker = SessionManager().get_session_maker()
    async with session_maker() as db:
        yield db


async def _is_authenticated(request: Request) -> bool:
    """Проверяет bearer-токен без разбора тела запроса."""
    token = await _bearer_token(request)
    if not token:
        return False
    from app.api.dependencies import resolve_token_user

    async with _probe_session(request) as db:
        return await resolve_token_user(db, token) is not None


def register_error_handlers(app: FastAPI) -> None:

    @app.middleware("http")
    async def content_type_and_protocol_middleware(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type")
            media_type = (content_type or "").partition(";")[0].strip().lower()
            unsupported = bool(content_type and media_type != "application/json")
            malformed = False
            if not unsupported:
                # Тело разбирается до зависимостей аутентификации, поэтому некорректный
                # JSON проверяется здесь и возвращается downstream через повторный канал.
                body = await request.body()
                request.scope["receive"] = _replay_receive(body)
                if body:
                    try:
                        json.loads(body)
                    except ValueError:
                        malformed = True

            if unsupported or malformed:
                # Порядок проверок: аутентификация раньше синтаксиса.
                # Публичные точки (вход) разбираются без аутентификации.
                if request.url.path not in PUBLIC_BODY_PATHS and not await _is_authenticated(request):
                    problem = ProblemDetail(
                        type="https://mini-cmms.example/problems/unauthenticated",
                        title="Unauthenticated",
                        status=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication token is missing.",
                        instance=str(request.url.path),
                        code="UNAUTHENTICATED",
                    )
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content=problem.model_dump(exclude_none=True),
                        headers={"Content-Type": "application/problem+json", "WWW-Authenticate": "Bearer"},
                    )
                if unsupported:
                    problem = ProblemDetail(
                        type="https://mini-cmms.example/problems/unsupported-media-type",
                        title="Unsupported Media Type",
                        status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail=f"Content-Type '{content_type}' is not supported. Use 'application/json'.",
                        instance=str(request.url.path),
                        code="UNSUPPORTED_MEDIA_TYPE",
                    )
                    return JSONResponse(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        content=problem.model_dump(exclude_none=True),
                        headers={"Content-Type": "application/problem+json"},
                    )
                problem = ProblemDetail(
                    type="https://mini-cmms.example/problems/malformed-json",
                    title="Malformed JSON",
                    status=status.HTTP_400_BAD_REQUEST,
                    detail="The request body contains invalid JSON.",
                    instance=str(request.url.path),
                    code="MALFORMED_JSON",
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=problem.model_dump(exclude_none=True),
                    headers={"Content-Type": "application/problem+json"},
                )
        return await call_next(request)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        errors = None
        if exc.errors:
            errors = [
                ValidationErrorItem(
                    field=e.get("field", e.get("name", "")), message=e.get("message", e.get("reason", ""))
                )
                for e in exc.errors
            ]
        problem = ProblemDetail(
            type=exc.type_uri,
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            instance=str(request.url.path),
            code=exc.code,
            errors=errors,
        )
        headers = {"Content-Type": "application/problem+json"}
        headers.update(exc.headers)
        return JSONResponse(
            status_code=exc.status,
            content=problem.model_dump(exclude_none=True),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        for err in exc.errors():
            err_type = err.get("type", "")
            if err_type in ("json_invalid", "json_type"):
                problem = ProblemDetail(
                    type="https://mini-cmms.example/problems/malformed-json",
                    title="Malformed JSON",
                    status=status.HTTP_400_BAD_REQUEST,
                    detail="The request body contains invalid JSON.",
                    instance=str(request.url.path),
                    code="MALFORMED_JSON",
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=problem.model_dump(exclude_none=True),
                    headers={"Content-Type": "application/problem+json"},
                )

        errors = []
        for err in exc.errors():
            loc_parts = [str(x) for x in err.get("loc", []) if str(x) != "body"]
            field_name = ".".join(loc_parts) or "body"
            msg = err.get("msg", "Invalid value")
            errors.append(ValidationErrorItem(field=field_name, message=msg))

        problem = ProblemDetail(
            type="https://mini-cmms.example/problems/validation-error",
            title="Validation Error",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more fields failed validation.",
            instance=str(request.url.path),
            code="VALIDATION_ERROR",
            errors=errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=problem.model_dump(exclude_none=True),
            headers={"Content-Type": "application/problem+json"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHENTICATED",
            403: "ACCESS_DENIED",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            412: "PRECONDITION_FAILED",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "VALIDATION_ERROR",
            428: "PRECONDITION_REQUIRED",
            429: "RATE_LIMITED",
            500: "INTERNAL_SERVER_ERROR",
            503: "DEPENDENCY_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        title = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ").title()

        problem = ProblemDetail(
            type=f"https://mini-cmms.example/problems/{code.lower().replace('_', '-')}",
            title=title,
            status=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
            code=code,
        )
        headers = {"Content-Type": "application/problem+json"}
        if exc.headers:
            headers.update(exc.headers)
        if exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            allow = _allowed_methods(request.app, request.url.path)
            if allow:
                headers["Allow"] = allow
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(exclude_none=True),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        problem = ProblemDetail(
            type="https://mini-cmms.example/problems/internal-server-error",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred on the server.",
            instance=str(request.url.path),
            code="INTERNAL_SERVER_ERROR",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.model_dump(exclude_none=True),
            headers={"Content-Type": "application/problem+json"},
        )
