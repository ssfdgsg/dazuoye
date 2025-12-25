"""电影推荐系统 FastAPI 应用入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings
from routers import auth, movies, recommendations, ratings
from services.als_worker import start_recompute_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：启动后台 ALS 重算线程
    start_recompute_worker()
    print("✓ ALS 后台重算线程已启动")
    yield
    # 关闭时：清理资源（如需要）
    print("✓ 应用关闭")


app = FastAPI(
    title="电影推荐系统 API",
    description="基于 ALS 协同过滤和 TF-IDF 内容推荐的电影推荐系统",
    version="1.0.1",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(recommendations.router)
app.include_router(ratings.router)

# 静态文件服务
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(static_path, "index.html"))
    
    @app.get("/img/{filename:path}")
    async def serve_image(filename: str):
        return FileResponse(os.path.join(static_path, "img", filename))


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
