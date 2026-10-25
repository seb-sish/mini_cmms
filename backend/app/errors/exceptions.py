class AppException(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        detail: str | None = None,
        title: str | None = None,
        type_uri: str | None = None,
        errors: list[dict[str, str]] | None = None,
        invalid_params: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        actual_detail = detail or code.replace("_", " ").title()
        super().__init__(actual_detail)
        self.status = status
        self.code = code
        self.title = title or code.replace("_", " ").title()
        self.detail = actual_detail
        slug = code.lower().replace("_", "-")
        self.type_uri = type_uri or f"https://mini-cmms.example/problems/{slug}"
        self.errors = errors if errors is not None else invalid_params
        self.headers = headers or {}
