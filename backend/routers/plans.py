"""饮食计划 CRUD，以及"某天落在哪个计划的哪段"查询。"""
from fastapi import APIRouter, HTTPException

from database import get_conn
from models import PlanCreate, PlanUpdate

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _get_plan(conn, plan_id: int) -> dict:
    row = conn.execute(
        "SELECT id, name, created_at FROM plans WHERE id = ?", (plan_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="计划不存在")
    plan = dict(row)
    phases = conn.execute(
        """SELECT id, start_date, end_date, kcal, protein, carbs, fat
           FROM plan_phases WHERE plan_id = ? ORDER BY start_date, id""",
        (plan_id,),
    ).fetchall()
    plan["phases"] = [dict(p) for p in phases]
    return plan


@router.get("")
def list_plans():
    conn = get_conn()
    rows = conn.execute("SELECT id FROM plans ORDER BY id").fetchall()
    result = []
    for r in rows:
        try:
            result.append(_get_plan(conn, r["id"]))
        except HTTPException:
            continue
    conn.close()
    return result


@router.post("")
def create_plan(plan: PlanCreate):
    if not plan.name.strip():
        raise HTTPException(status_code=400, detail="计划名不能为空")
    if not plan.phases:
        raise HTTPException(status_code=400, detail="计划至少需要一个时间段")
    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO plans (name) VALUES (?)", (plan.name.strip(),))
        plan_id = cur.lastrowid
        for ph in plan.phases:
            if ph.start_date > ph.end_date:
                raise HTTPException(status_code=400, detail=f"时间段起止日期不合法：{ph.start_date} ~ {ph.end_date}")
            conn.execute(
                """INSERT INTO plan_phases (plan_id, start_date, end_date, kcal, protein, carbs, fat)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (plan_id, ph.start_date, ph.end_date, ph.kcal, ph.protein, ph.carbs, ph.fat),
            )
        conn.commit()
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    result = _get_plan(conn, plan_id)
    conn.close()
    return result


@router.put("/{plan_id}")
def update_plan(plan_id: int, plan: PlanUpdate):
    conn = get_conn()
    # 确认计划存在
    exists = conn.execute("SELECT id FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if exists is None:
        conn.close()
        raise HTTPException(status_code=404, detail="计划不存在")
    try:
        # 更新名称
        if plan.name is not None:
            if not plan.name.strip():
                raise HTTPException(status_code=400, detail="计划名不能为空")
            conn.execute("UPDATE plans SET name = ? WHERE id = ?", (plan.name.strip(), plan_id))
        # 整段替换：提交 phases 时，删除旧段重建
        if plan.phases is not None:
            if not plan.phases:
                raise HTTPException(status_code=400, detail="计划至少需要一个时间段")
            for ph in plan.phases:
                if ph.start_date > ph.end_date:
                    raise HTTPException(status_code=400, detail=f"时间段起止日期不合法：{ph.start_date} ~ {ph.end_date}")
            conn.execute("DELETE FROM plan_phases WHERE plan_id = ?", (plan_id,))
            for ph in plan.phases:
                conn.execute(
                    """INSERT INTO plan_phases (plan_id, start_date, end_date, kcal, protein, carbs, fat)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (plan_id, ph.start_date, ph.end_date, ph.kcal, ph.protein, ph.carbs, ph.fat),
                )
        conn.commit()
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    result = _get_plan(conn, plan_id)
    conn.close()
    return result


@router.delete("/{plan_id}")
def delete_plan(plan_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/today")
def today_plan(date: str = None):
    """查某天（默认今天）落在哪个计划的哪一段，返回该段的目标值。"""
    if date is None:
        from datetime import date as _date
        date = _date.today().isoformat()
    conn = get_conn()
    row = conn.execute(
        """SELECT p.id AS plan_id, p.name AS plan_name,
                  ph.id AS phase_id, ph.start_date, ph.end_date,
                  ph.kcal, ph.protein, ph.carbs, ph.fat
           FROM plan_phases ph
           JOIN plans p ON p.id = ph.plan_id
           WHERE ? BETWEEN ph.start_date AND ph.end_date
           ORDER BY ph.start_date, p.id
           LIMIT 1""",
        (date,),
    ).fetchone()
    conn.close()
    if row is None:
        return {"active": False, "date": date}
    return {"active": True, "date": date, **dict(row)}


@router.get("/{plan_id}")
def get_plan(plan_id: int):
    """查询单个计划（含完整时间段）。"""
    conn = get_conn()
    result = _get_plan(conn, plan_id)
    conn.close()
    return result
