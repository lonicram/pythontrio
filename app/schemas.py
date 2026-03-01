"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel


class ItemBase(BaseModel):
    """Base schema for Item with common attributes."""

    name: str
    description: str | None = None


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    pass


class ItemResponse(ItemBase):
    """Schema for item response with database fields."""

    id: int

    class Config:
        from_attributes = True
