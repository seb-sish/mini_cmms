from typing import Any, Optional

class AppException(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        detail: str,
        type_uri: Optional[str] = None,
        invalid_params: Optional[list[dict[str, str]]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri or f"https://mini-cmms.example/errors/{code.lower().replace('_', '-')}"
        self.invalid_params = invalid_params
        self.headers = headers or {}
