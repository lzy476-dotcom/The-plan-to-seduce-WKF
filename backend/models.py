"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel
from typing import Optional, List


class FoodCreate(BaseModel):
    name: str
    kcal_per_100g: float = 0
    protein_per_100g: float = 0
    carbs_per_100g: float = 0
    fat_per_100g: float = 0


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    kcal_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None


class MealItemCreate(BaseModel):
    """一餐里的一个食物条目。"""
    # 二选一：已有食物用 food_id；新食物用 food_name + 每100g营养字段
    food_id: Optional[int] = None
    food_name: Optional[str] = None
    protein_per_100g: float = 0
    carbs_per_100g: float = 0
    fat_per_100g: float = 0
    grams: float = 0               # 本次吃掉的克重


class MealCreate(BaseModel):
    date: str                      # YYYY-MM-DD
    note: str = ""
    items: List[MealItemCreate]


class PlanPhaseCreate(BaseModel):
    """一个时间段的目标。"""
    start_date: str                # YYYY-MM-DD
    end_date: str                  # YYYY-MM-DD
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0


class PlanCreate(BaseModel):
    name: str
    phases: List[PlanPhaseCreate]


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    phases: Optional[List[PlanPhaseCreate]] = None
