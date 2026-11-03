"""一餐的 CRUD。一餐含多个食物条目，摄入量 = 每100g营养 × grams / 100。"""
from fastapi import APIRouter, HTTPException

from database import get_conn, get_setting
from models import MealCreate, MealItemCreate

router = APIRouter(prefix="/api/meals", tags=["meals"])

# 营养锁定：开启后食物首次录入即固定营养，之后再记同名食物不覆盖
DEFAULT_NUTRITION_LOCK = "1"

# 热量由三大营养素自动计算（Atwater 系数）：kcal = 蛋白×4 + 碳水×4 + 脂肪×9
KCAL_PROTEIN = 4.0
KCAL_CARBS = 4.0
KCAL_FAT = 9.0


def _nutrition_locked() -> bool:
    return get_setting("nutrition_lock", DEFAULT_NUTRITION_LOCK) == "1"


def _calc_kcal(protein: float, carbs: float, fat: float) -> float:
    """由每100g三大营养素计算每100g热量（千卡）。"""
    return protein * KCAL_PROTEIN + carbs * KCAL_CARBS + fat * KCAL_FAT


def _resolve_food_id(conn, item: MealItemCreate) -> int:
    """按 item 解析食物 id：优先 food_id，否则按名字"不存在则入库，存在则复用/锁定"。"""
    if item.food_id is not None:
        return item.food_id
    if not item.food_name:
        raise HTTPException(status_code=400, detail="每个食物需要 food_id 或 food_name")
    name = item.food_name.strip()
    kcal_per_100g = _calc_kcal(item.protein_per_100g, item.carbs_per_100g, item.fat_per_100g)
    row = conn.execute("SELECT id FROM foods WHERE name = ?", (name,)).fetchone()
    if row is None:
        cur = conn.execute(
            """INSERT INTO foods (name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g)
               VALUES (?, ?, ?, ?, ?)""",
            (name, kcal_per_100g, item.protein_per_100g, item.carbs_per_100g, item.fat_per_100g),
        )
        return cur.lastrowid
    else:
        # 同名复用：未锁定时用本次提交的营养值更新字典（热量重算）；锁定时保持字典值不变
        if not _nutrition_locked():
            conn.execute(
                """UPDATE foods
                   SET kcal_per_100g = ?, protein_per_100g = ?, carbs_per_100g = ?, fat_per_100g = ?
                   WHERE id = ?""",
                (kcal_per_100g, item.protein_per_100g, item.carbs_per_100g, item.fat_per_100g, row["id"]),
            )
        return row["id"]


def _calc(item: dict, grams: float) -> dict:
    """为一条 item 补充实际摄入量字段。"""
    item["kcal"] = item["kcal_per_100g"] * grams / 100
    item["protein"] = item["protein_per_100g"] * grams / 100
    item["carbs"] = item["carbs_per_100g"] * grams / 100
    item["fat"] = item["fat_per_100g"] * grams / 100
    return item


@router.post("")
def create_meal(meal: MealCreate):
    if not meal.items:
        raise HTTPException(status_code=400, detail="一餐至少需要一个食物")
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO meals (date, note) VALUES (?, ?)",
            (meal.date, meal.note),
        )
        meal_id = cur.lastrowid
        for item in meal.items:
            food_id = _resolve_food_id(conn, item)
            conn.execute(
                "INSERT INTO meal_items (meal_id, food_id, grams) VALUES (?, ?, ?)",
                (meal_id, food_id, item.grams),
            )
        conn.commit()
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    result = _get_meal(conn, meal_id)
    conn.close()
    return result


def _get_meal(conn, meal_id: int) -> dict:
    row = conn.execute(
        "SELECT id, date, note, created_at FROM meals WHERE id = ?", (meal_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="该餐不存在")
    meal = dict(row)
    items = conn.execute(
        """SELECT i.id, i.grams,
                  f.id AS food_id, f.name AS food_name,
                  f.kcal_per_100g, f.protein_per_100g, f.carbs_per_100g, f.fat_per_100g
           FROM meal_items i
           JOIN foods f ON f.id = i.food_id
           WHERE i.meal_id = ?
           ORDER BY i.id""",
        (meal_id,),
    ).fetchall()
    meal["items"] = [_calc(dict(i), i["grams"]) for i in items]
    meal["kcal"] = sum(i["kcal"] for i in meal["items"])
    meal["protein"] = sum(i["protein"] for i in meal["items"])
    meal["carbs"] = sum(i["carbs"] for i in meal["items"])
    meal["fat"] = sum(i["fat"] for i in meal["items"])
    return meal


@router.get("")
def list_meals(date: str = None):
    conn = get_conn()
    if date:
        rows = conn.execute(
            "SELECT id FROM meals WHERE date = ? ORDER BY id", (date,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT id FROM meals ORDER BY date DESC, id DESC").fetchall()
    result = []
    for r in rows:
        try:
            result.append(_get_meal(conn, r["id"]))
        except HTTPException:
            continue
    conn.close()
    return result


@router.delete("/{meal_id}")
def delete_meal(meal_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
