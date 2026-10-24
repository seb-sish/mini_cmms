from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.exceptions import AppException
from app.schemas.common import ProblemDetail, ValidationErrorItem

def register_error_handlers(app: FastAPI) -> None:

    @app.middleware("http")
    async def content_type_and_protocol_middleware(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type")
            # If Content-Type is specified and not json/problem+json
            if content_type and not (
                content_type.startswith("application/json") or content_type.startswith("application/problem+json")
            ):
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
        return await call_next(request)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        errors = None
        if exc.errors:
            errors = [
                ValidationErrorItem(field=e.get("field", e.get("name", "")), message=e.get("message", e.get("reason", "")))
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
