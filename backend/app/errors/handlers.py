from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.exceptions import AppException
from app.schemas.common import ProblemDetail

def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        problem = ProblemDetail(
            type=exc.type_uri,
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            instance=str(request.url.path),
            code=exc.code,
            invalid_params=exc.invalid_params,  # type: ignore
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
        invalid_params = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            invalid_params.append({"name": loc, "reason": msg})

        problem = ProblemDetail(
            type="https://mini-cmms.example/errors/validation-error",
            title="Validation Error",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more fields failed validation.",
            instance=str(request.url.path),
            code="VALIDATION_ERROR",
            invalid_params=invalid_params,  # type: ignore
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
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            412: "PRECONDITION_FAILED",
            415: "UNSUPPORTED_MEDIA_TYPE",
            428: "PRECONDITION_REQUIRED",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        title = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
        
        problem = ProblemDetail(
            type=f"https://mini-cmms.example/errors/{code.lower().replace('_', '-')}",
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
            type="https://mini-cmms.example/errors/internal-server-error",
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
