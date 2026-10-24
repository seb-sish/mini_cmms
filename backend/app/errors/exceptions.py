from typing import Any, Optional

class AppException(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        detail: Optional[str] = None,
        title: Optional[str] = None,
        type_uri: Optional[str] = None,
        invalid_params: Optional[list[dict[str, str]]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        actual_detail = detail or code.replace("_", " ").title()
        super().__init__(actual_detail)
        self.status = status
        self.code = code
        self.title = title or code.replace("_", " ").title()
        self.detail = actual_detail
        self.type_uri = type_uri or f"https://mini-cmms.example/errors/{code.lower().replace('_', '-')}"
        self.invalid_params = invalid_params
        self.headers = headers or {}
