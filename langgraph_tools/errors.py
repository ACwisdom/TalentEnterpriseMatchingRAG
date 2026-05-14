from __future__ import annotations

from typing import Any, Mapping


class ApiError(Exception):
    """Raised when the Java API returns a JSON error body with a `code` field."""

    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")


def map_error_response(payload: Mapping[str, Any]) -> ApiError:
    code = str(payload.get("code") or "UNKNOWN")
    message = str(payload.get("message") or "")
    details = payload.get("details")
    return ApiError(code=code, message=message, details=details)
