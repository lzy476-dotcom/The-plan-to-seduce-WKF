"""SQLite 连接与建表。

数据库文件保存在 data/diet.db（相对项目根）。
"""
import sqlite3
from pathlib import Path

# 项目根 = backend 的父目录
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "diet.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL UNIQUE,
    kcal_per_100g       REAL NOT NULL DEFAULT 0,   -- 每100g热量(千卡)
    protein_per_100g    REAL NOT NULL DEFAULT 0,   -- 每100g蛋白质(g)
    carbs_per_100g      REAL NOT NULL DEFAULT 0,   -- 每100g碳水(g)
    fat_per_100g        REAL NOT NULL DEFAULT 0,   -- 每100g脂肪(g)
    created_at          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS meals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,             -- 格式 YYYY-MM-DD
    note        TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS meal_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_id     INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_id     INTEGER NOT NULL REFERENCES foods(id),
    grams       REAL NOT NULL DEFAULT 0,   -- 数量：按克时=克重(g)，按份时=份数
    unit        TEXT NOT NULL DEFAULT 'g', -- "g"=按克，"serving"=按份
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date);
CREATE INDEX IF NOT EXISTS idx_meal_items_meal ON meal_items(meal_id);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS plan_phases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    start_date  TEXT NOT NULL,             -- 格式 YYYY-MM-DD
    end_date    TEXT NOT NULL,             -- 格式 YYYY-MM-DD
    kcal        REAL NOT NULL DEFAULT 0,   -- 每日热量目标
    protein     REAL NOT NULL DEFAULT 0,   -- 每日蛋白质目标(g)
    carbs       REAL NOT NULL DEFAULT 0,   -- 每日碳水目标(g)
    fat         REAL NOT NULL DEFAULT 0    -- 每日脂肪目标(g)
);

CREATE INDEX IF NOT EXISTS idx_plan_phases_plan ON plan_phases(plan_id);

CREATE TABLE IF NOT EXISTS user_profile (
    id          INTEGER PRIMARY KEY CHECK (id = 1),  -- 固定单行
    gender      TEXT NOT NULL DEFAULT 'male',        -- male / female
    age         INTEGER NOT NULL DEFAULT 25,
    height_cm   REAL NOT NULL DEFAULT 170,
    weight_kg   REAL NOT NULL DEFAULT 60,
    activity    TEXT NOT NULL DEFAULT 'light'        -- sedentary/light/moderate/active/very_active
);
"""


def get_conn() -> sqlite3.Connection:
    """获取一个连接，开启外键约束。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表（幂等）。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    migrate_db()


# 已有表需要补充的列迁移：foods 表新增「每份营养」4 列
_SERVING_COLUMNS = [
    ("kcal_per_serving", "REAL NOT NULL DEFAULT 0"),
    ("protein_per_serving", "REAL NOT NULL DEFAULT 0"),
    ("carbs_per_serving", "REAL NOT NULL DEFAULT 0"),
    ("fat_per_serving", "REAL NOT NULL DEFAULT 0"),
]


def migrate_db() -> None:
    """幂等迁移：给已有库补充新增列，不破坏原有数据。"""
    conn = get_conn()
    try:
        # foods：每份营养 4 列
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(foods)").fetchall()}
        for col, ddl in _SERVING_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE foods ADD COLUMN {col} {ddl}")
        # meal_items：计量单位 unit 列
        mi_existing = {row["name"] for row in conn.execute("PRAGMA table_info(meal_items)").fetchall()}
        if "unit" not in mi_existing:
            conn.execute("ALTER TABLE meal_items ADD COLUMN unit TEXT NOT NULL DEFAULT 'g'")
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    """读取设置项，不存在时返回 default。"""
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """写入设置项（upsert）。"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()

