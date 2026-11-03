# 饮食记录（Diet Tracker）

本地单机的饮食记录软件。前端 Web 界面 + FastAPI 后端 + SQLite 存储。

## 技术栈

- 后端：FastAPI + Uvicorn
- 存储：SQLite（`data/diet.db`，首次启动自动生成）
- 前端：原生 HTML / CSS / JS（无构建步骤）

## 环境要求

- Python 3.10+

## 安装

```bash
cd backend
pip install -r requirements.txt
```

## 启动

```bash
cd backend
uvicorn main:app --reload --port 8000
```

然后浏览器打开：<http://127.0.0.1:8000>

- 前端页面：<http://127.0.0.1:8000/>
- 接口文档（自动生成）：<http://127.0.0.1:8000/docs>

## 使用说明

- **添加一餐**：一次可记录多个食物。
  - 每个食物一行，填「食物名称 + 每100g营养 + 吃了多少克」。
  - 输入已有食物名 → 自动带出它的每100g营养（可改）；输入新名字 → 留空填写。
  - 点「＋ 添加食物」加一行，一次提交整餐。
  - 摄入量自动换算：实际摄入 = 每100g营养 × 克重 / 100。
- **今日饮食**：左侧按餐展示，每餐列出各食物及摄入的蛋白/碳水/脂肪/热量，顶部汇总全天总热量和三大营养素。可删除整餐。
- 每餐是独立记录，不区分早餐/午餐/晚餐。

## 目录结构

```
diet/
├── backend/
│   ├── main.py          # 入口，挂载路由与静态文件
│   ├── database.py      # SQLite 连接与建表
│   ├── models.py        # Pydantic 模型
│   ├── routers/
│   │   ├── foods.py     # 食物字典 CRUD
│   │   └── meals.py     # 一餐 CRUD（含多个食物条目）
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── data/                # diet.db 自动生成
```

## 数据模型

- `foods`：食物字典，存每100g营养（热量/蛋白/碳水/脂肪），名称唯一
- `meals`：一餐（日期、备注）
- `meal_items`：餐内食物条目（餐id、食物id、克重）

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/foods` | 食物列表 |
| POST | `/api/foods` | 添加食物（每100g营养） |
| PUT | `/api/foods/{id}` | 修改食物 |
| DELETE | `/api/foods/{id}` | 删除食物 |
| GET | `/api/meals?date=YYYY-MM-DD` | 按日查餐（展开 items 及实际摄入量） |
| POST | `/api/meals` | 提交一餐（`{date, note, items:[{food_name/food_id, 每100g营养, grams}]}`，新食物自动入库，已有食物更新营养） |
| DELETE | `/api/meals/{id}` | 删除一餐 |
