"""
FastAPI应用主入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

from app.config import settings
from app.database import db
from app.api import classify, stats, health, location, auth, config, release, image_edit, user, payment
# 延迟导入local_classify（避免启动时导入ultralytics导致的问题）
try:
    from app.api import local_classify
except ImportError as e:
    logger.warning(f"本地推理模块导入失败，将禁用本地推理功能: {e}")
    local_classify = None
from app.api.auth import wechat_message_handler, wechat_verify


# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)

# 如果配置了日志文件
if settings.LOG_FILE:
    logger.add(
        settings.LOG_FILE,
        rotation="100 MB",
        retention="30 days",
        level=settings.LOG_LEVEL
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("========================================")
    logger.info("图片分类后端服务启动中...")
    logger.info(f"环境: {settings.APP_ENV}")
    logger.info(f"调试模式: {settings.APP_DEBUG}")
    logger.info(f"大模型提供商: {settings.LLM_PROVIDER}")
    logger.info("========================================")
    
    # 连接数据库
    await db.connect()
    logger.info("数据库连接成功")
    
    yield
    
    # 关闭时
    logger.info("图片分类后端服务关闭中...")
    await db.disconnect()
    logger.info("数据库连接已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="图片分类后端API",
    description="基于大模型的图片分类服务，支持8种预定义分类",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(user.router)  # 用户管理（额度查询）
app.include_router(classify.router)
if local_classify is not None:
    app.include_router(local_classify.router)  # 本地模型推理
app.include_router(config.router)  # 运行时配置
app.include_router(release.router)  # 发行版本上传
app.include_router(stats.router)
app.include_router(health.router)
app.include_router(location.router)
app.include_router(image_edit.router)  # 图像编辑
app.include_router(payment.router)  # 支付功能

# 微信公众号服务器配置验证接口（GET请求）
@app.get("/api/v1/auth/wechat/verify", summary="微信服务器配置验证")
async def wechat_verify_endpoint(
    signature: str,
    timestamp: str,
    nonce: str,
    echostr: str
):
    """微信服务器配置验证接口（GET请求）"""
    return await wechat_verify(signature, timestamp, nonce, echostr)

# 微信公众号消息推送接收接口（POST请求）
@app.post("/api/v1/auth/wechat/verify", summary="微信公众号消息推送")
async def wechat_message_push(request: Request):
    """接收微信公众号的消息推送（POST请求）"""
    return await wechat_message_handler(request)

# 图像编辑结果图片服务（仅保留图片服务，前端页面已迁移到旧服务器）
images_path = os.path.join(os.path.dirname(__file__), "images")
if os.path.exists(images_path):
    app.mount("/images", StaticFiles(directory=images_path), name="images")
    logger.info(f"图像编辑结果图片服务已启用: {images_path}")

# 微信公众号页面静态文件服务
# 注意：虽然Nginx也配置了/wechat/路径，但lighttpd代理到8000端口会直接到FastAPI，所以FastAPI也需要配置
wechat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wechat")
if os.path.exists(wechat_path):
    app.mount("/wechat", StaticFiles(directory=wechat_path), name="wechat")
    logger.info(f"微信页面静态文件服务已启用: {wechat_path}")

# 根路径 - 返回API信息
@app.get("/", tags=["root"])
async def root():
    """根路径 - 返回API服务信息"""
    return {
        "service": "Image Classifier Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
        "api_base": "/api/v1"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG
    )

