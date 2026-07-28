"""Errores transportables sin filtrar excepciones internas."""


class PublicApiError(RuntimeError):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        correlation_id: str,
        category: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.category = category or _category(status_code)
        self.message = message
        self.correlation_id = correlation_id
        self.details = details or {}


def _category(status_code: int) -> str:
    if status_code == 401:
        return "authentication"
    if status_code == 403:
        return "authorization"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if 400 <= status_code < 500:
        return "validation"
    return "internal"
