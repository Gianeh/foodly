from __future__ import annotations
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

class AddToPantry(BaseModel):
    food_id: int
    qty_g: float = Field(..., gt=0)
    package_g: Optional[float] = Field(None, gt=0)
    location: Optional[str] = None
    best_before: Optional[str] = Field(None, description="YYYY-MM-DD")

class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class Consume(BaseModel):
    food_id: int
    grams: float = Field(..., gt=0)
    meal: MealType = MealType.snack
    note: Optional[str] = None

class FindFood(BaseModel):
    query: str
    limit: int = 10

class Summary(BaseModel):
    date_str: Optional[str] = None

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ChatRequest(BaseModel):
    user_message: str
    date_str: Optional[str] = None
    use_rule_based: bool = True
    dry_run: bool = False
    require_confirm: bool = True
    idempotency_key: Optional[str] = None

class ChatResponse(BaseModel):
    actions: List[ToolCall]
    results: Dict[str, Any]
    message: str
