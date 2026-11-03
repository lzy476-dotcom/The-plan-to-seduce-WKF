"""全局设置。"""
from fastapi import APIRouter
from pydantic import BaseModel

from database import get_setting, set_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])

# nutrition_lock 默认开启（"1"）
DEFAULT_NUTRITION_LOCK = "1"


class NutritionLockBody(BaseModel):
    enabled: bool


@router.get("/nutrition_lock")
def get_nutrition_lock():
    value = get_setting("nutrition_lock", DEFAULT_NUTRITION_LOCK)
    return {"enabled": value == "1"}


@router.put("/nutrition_lock")
def set_nutrition_lock(body: NutritionLockBody):
    set_setting("nutrition_lock", "1" if body.enabled else "0")
    return {"enabled": body.enabled}
