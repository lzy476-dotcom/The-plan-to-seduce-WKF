"""饮食记录软件后端入口。

启动：在 backend 目录下执行
    uvicorn main:app --reload --port 8000
然后浏览器打开 http://127.0.0.1:8000 即为前端页面。
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import foods, meals, settings, plans

# 启动时建表
init_db()

app = FastAPI(title="饮食记录")

app.include_router(foods.router)
app.include_router(meals.router)
app.include_router(settings.router)
app.include_router(plans.router)

# 挂载前端静态文件
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}
