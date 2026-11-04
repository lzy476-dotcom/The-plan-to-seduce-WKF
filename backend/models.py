"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel
from typing import Optional, List


class FoodCreate(BaseModel):
    name: str
    kcal_per_100g: float = 0
    protein_per_100g: float = 0
    carbs_per_100g: float = 0
    fat_per_100g: float = 0
    # 每份营养（外卖/一碗饭/一杯等「按份」计量的食物）
    kcal_per_serving: float = 0
    protein_per_serving: float = 0
    carbs_per_serving: float = 0
    fat_per_serving: float = 0


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    kcal_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    kcal_per_serving: Optional[float] = None
    protein_per_serving: Optional[float] = None
    carbs_per_serving: Optional[float] = None
    fat_per_serving: Optional[float] = None


class MealItemCreate(BaseModel):
    """一餐里的一个食物条目。"""
    # 二选一：已有食物用 food_id；新食物用 food_name + 每100g营养字段
    food_id: Optional[int] = None
    food_name: Optional[str] = None
    protein_per_100g: float = 0
    carbs_per_100g: float = 0
    fat_per_100g: float = 0
    # 每份营养（按份计量时用）
    protein_per_serving: float = 0
    carbs_per_serving: float = 0
    fat_per_serving: float = 0
    unit: str = "g"               # "g" = 按克，按 grams 算；"serving" = 按份，按 servings 算
    grams: float = 0               # 按克时的克重
    servings: float = 0            # 按份时的份数


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


class UserProfile(BaseModel):
    """用户身体数据（单行）。"""
    gender: str = "male"          # male / female
    age: int = 25
    height_cm: float = 170
    weight_kg: float = 60
    activity: str = "light"       # sedentary/light/moderate/active/very_active
