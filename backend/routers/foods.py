"""食物字典 CRUD（营养按每100g计）。"""
from fastapi import APIRouter, HTTPException

from database import get_conn
from models import FoodCreate, FoodUpdate

router = APIRouter(prefix="/api/foods", tags=["foods"])


@router.get("")
def list_foods():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM foods ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
def create_food(food: FoodCreate):
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO foods (name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g,
                                  kcal_per_serving, protein_per_serving, carbs_per_serving, fat_per_serving)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (food.name, food.kcal_per_100g, food.protein_per_100g,
             food.carbs_per_100g, food.fat_per_100g,
             food.kcal_per_serving, food.protein_per_serving,
             food.carbs_per_serving, food.fat_per_serving),
        )
        conn.commit()
        fid = cur.lastrowid
    except Exception as e:  # 名称重复等
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    row = conn.execute("SELECT * FROM foods WHERE id = ?", (fid,)).fetchone()
    conn.close()
    return dict(row)


@router.put("/{food_id}")
def update_food(food_id: int, food: FoodUpdate):
    conn = get_conn()
    fields = food.model_dump(exclude_unset=True)
    if not fields:
        conn.close()
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE foods SET {sets} WHERE id = ?", (*fields.values(), food_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="食物不存在")
    return dict(row)


@router.delete("/{food_id}")
def delete_food(food_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
