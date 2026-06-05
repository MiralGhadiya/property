from typing import Any, Generic, Optional, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")


class APIResponse(GenericModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: T


def success_response(*, data: Any, message: str = "Success"):
    return {
        "success": True,
        "message": message,
        "data": data,
    }
