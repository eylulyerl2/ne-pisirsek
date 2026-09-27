import uuid
from datetime import datetime

from pydantic import BaseModel


class ShoppingItemResponse(BaseModel):
    item_id: uuid.UUID
    ingredient_id: uuid.UUID
    name: str
    quantity: float | None = None
    unit: str | None = None
    estimated_price: float | None = None
    is_checked: bool


class ShoppingListResponse(BaseModel):
    list_id: uuid.UUID
    plan_id: uuid.UUID
    created_at: datetime | None = None
    items: list[ShoppingItemResponse]


class ShoppingItemUpdate(BaseModel):
    is_checked: bool
