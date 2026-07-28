from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def error_payload(
    message: str,
    code: str = "error",
    fields: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": message, "code": code}
    if fields:
        payload["fields"] = fields
    if request_id:
        payload["request_id"] = request_id
    return payload


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_payload(f"{resource} not found", "not_found"))


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_payload(message, "conflict"))


def bad_request(message: str, code: str = "bad_request") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_payload(message, code))


def unauthorized(message: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_payload(message, "unauthorized"))


def forbidden(message: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_payload(message, "forbidden"))
