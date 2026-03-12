# app/common.py

from typing import Generic, List, TypeVar
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")

class Pagination(BaseModel):
    page: int = 1
    limit: int | None = None
    total: int

class PaginatedResponse(GenericModel, Generic[T]):
    data: List[T]
    pagination: Pagination