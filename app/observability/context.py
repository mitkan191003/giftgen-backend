from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_context(request_id: str | None) -> None:
    _request_id.set(request_id)


def set_user_id(user_id: str | None) -> None:
    _user_id.set(user_id)


def get_request_id() -> str | None:
    return _request_id.get()


def get_user_id() -> str | None:
    return _user_id.get()


def clear_request_context() -> None:
    set_request_context(None)
    set_user_id(None)
