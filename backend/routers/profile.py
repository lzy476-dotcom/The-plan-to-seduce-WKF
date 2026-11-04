"""用户身体数据读写，以及「碳水减降模板」的目标计算。

碳水减降 = 分阶段碳水循环方案，只依赖体重，三大营养素按体重倍率计算：
  - 启动期 10 天：碳水 3.0×，蛋白 1.4×，脂肪 0.4×
  - 高碳日  1 天：碳水 5.0×，蛋白 1.0×，脂肪 0.4×
  - 持续期 12 天：碳水 2.5×，蛋白 1.6×，脂肪 0.5×
  - 高碳日  1 天：碳水 5.0×，蛋白 1.2×，脂肪 0.5×
  - 收尾期 12 天：碳水 2.0×，蛋白 1.8×，脂肪 0.5×
热量按 Atwater 系数自动算：kcal = 碳水×4 + 蛋白×4 + 脂肪×9。
"""
from fastapi import APIRouter

from database import get_conn
from models import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])

# 碳水循环各阶段定义：(名称, 天数, 碳水倍率, 蛋白倍率, 脂肪倍率)
CARB_CYCLE_PHASES = [
    ("启动期", 10, 3.0, 1.4, 0.4),
    ("高碳日", 1, 5.0, 1.0, 0.4),
    ("持续期", 12, 2.5, 1.6, 0.5),
    ("高碳日", 1, 5.0, 1.2, 0.5),
    ("收尾期", 12, 2.0, 1.8, 0.5),
]


def _load(conn) -> dict:
    row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO user_profile (id, gender, age, height_cm, weight_kg, activity) "
            "VALUES (1, 'male', 25, 170, 60, 'light')"
        )
        conn.commit()
        row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    return dict(row)


@router.get("")
def get_profile():
    conn = get_conn()
    profile = _load(conn)
    result = _compute_targets(profile)
    conn.close()
    return {"profile": profile, **result}


@router.put("")
def update_profile(p: UserProfile):
    conn = get_conn()
    conn.execute(
        """UPDATE user_profile
           SET gender = ?, age = ?, height_cm = ?, weight_kg = ?, activity = ?
           WHERE id = 1""",
        (p.gender, p.age, p.height_cm, p.weight_kg, p.activity),
    )
    if conn.total_changes == 0:
        conn.execute(
            "INSERT INTO user_profile (id, gender, age, height_cm, weight_kg, activity) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (p.gender, p.age, p.height_cm, p.weight_kg, p.activity),
        )
    conn.commit()
    profile = _load(conn)
    result = _compute_targets(profile)
    conn.close()
    return {"profile": profile, **result}


def _compute_targets(profile: dict) -> dict:
    """按体重计算碳水减降的完整分阶段目标。"""
    weight = profile.get("weight_kg", 60) or 60

    phases = []
    for name, days, c_mult, p_mult, f_mult in CARB_CYCLE_PHASES:
        carbs = round(weight * c_mult)
        protein = round(weight * p_mult)
        fat = round(weight * f_mult)
        kcal = round(carbs * 4 + protein * 4 + fat * 9)
        phases.append({
            "name": name,
            "days": days,
            "carbs": carbs,
            "protein": protein,
            "fat": fat,
            "kcal": kcal,
            "c_mult": c_mult,
            "p_mult": p_mult,
            "f_mult": f_mult,
        })

    total_days = sum(p["days"] for p in phases)
    return {
        "phases": phases,
        "total_days": total_days,
        "note": "碳水减降：分阶段碳水循环。只按体重计算，启动10天+高碳1天+持续12天+高碳1天+收尾12天，共36天。",
    }
