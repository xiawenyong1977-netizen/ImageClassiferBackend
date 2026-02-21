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
from app.api import health_v2
# 延迟导入local_classify（避免启动时导入ultralytics导致的问题）
try:
    from app.api import local_classify
except ImportError as e:
    logger.warning(f"本地推理模块导入失败，将禁用本地推理功能: {e}")
    local_classify = None
# 导入v2版本分类接口
try:
    from app.api import classify_v2
except ImportError as e:
    logger.warning(f"v2分类接口模块导入失败，v2接口不可用: {e}")
    classify_v2 = None
# 导入v2版本图像编辑接口
try:
    from app.api import image_edit_v2
except ImportError as e:
    logger.warning(f"v2图像编辑接口模块导入失败，v2接口不可用: {e}")
    image_edit_v2 = None
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
    try:
        logger.add(
            settings.LOG_FILE,
            rotation="100 MB",
            retention="30 days",
            level=settings.LOG_LEVEL
        )
    except (PermissionError, OSError) as e:
        # 在CI环境或没有权限的情况下，跳过文件日志配置
        logger.warning(f"无法创建日志文件 {settings.LOG_FILE}: {e}，将仅使用控制台日志")


async def startup_health_check(app: FastAPI, pid: int):
    """启动后自检：检查关键组件状态"""
    checks = {
        "数据库": False,
        "模型API配置": False,
        "路由注册": False
    }
    
    # 1. 检查数据库连接
    try:
        async with db.get_cursor() as cursor:
            await cursor.execute("SELECT 1")
            checks["数据库"] = True
    except Exception as e:
        logger.error(f"Worker [{pid}] 自检失败 - 数据库连接异常: {e}")
        checks["数据库"] = False
    
    # 2. 检查模型API配置
    if settings.LLM_API_KEY:
        checks["模型API配置"] = True
    else:
        logger.warning(f"Worker [{pid}] 自检警告 - 模型API密钥未配置")
        checks["模型API配置"] = False
    
    # 3. 检查路由注册（简单检查关键路由是否存在）
    try:
        routes = [route.path for route in app.routes]
        key_routes = ["/api/v1/health", "/api/v2/health", "/"]
        if any(route in routes for route in key_routes):
            checks["路由注册"] = True
        else:
            checks["路由注册"] = False
    except Exception as e:
        logger.warning(f"Worker [{pid}] 自检警告 - 路由检查异常: {e}")
        checks["路由注册"] = False
    
    # 输出自检结果（合并为一行，避免多worker时日志交错）
    all_ok = all(checks.values())
    status_icon = "✅" if all_ok else "⚠️"
    
    # 构建检查项状态字符串
    check_items = []
    for component, status in checks.items():
        icon = "✓" if status else "✗"
        check_items.append(f"{icon}{component}")
    
    check_summary = " | ".join(check_items)
    logger.info(f"Worker [{pid}] 启动自检 {status_icon} | {check_summary}")
    
    if not all_ok:
        failed_components = [comp for comp, status in checks.items() if not status]
        logger.warning(f"Worker [{pid}] 启动自检发现异常组件: {', '.join(failed_components)}")
    
    return all_ok


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import os
    pid = os.getpid()
    
    # 启动时（简化日志，添加进程ID）
    logger.info(f"Worker [{pid}] 启动中 | 环境: {settings.APP_ENV} | 调试: {settings.APP_DEBUG} | LLM: {settings.LLM_PROVIDER}")
    
    # 连接数据库
    try:
        await db.connect()
        logger.debug(f"Worker [{pid}] 数据库连接成功")
    except Exception as e:
        logger.error(f"Worker [{pid}] 数据库连接失败: {e}")
        raise
    
    # 启动后自检
    try:
        await startup_health_check(app, pid)
    except Exception as e:
        logger.error(f"Worker [{pid}] 启动自检异常: {e}")
        # 自检失败不阻止启动，只记录错误
    
    yield
    
    # 关闭时
    logger.info(f"Worker [{pid}] 关闭中...")
    await db.disconnect()
    logger.debug(f"Worker [{pid}] 数据库连接已关闭")


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
app.include_router(classify.router)  # v1版本分类接口
if classify_v2 is not None:
    app.include_router(classify_v2.router)  # v2版本分类接口
if local_classify is not None:
    app.include_router(local_classify.router)  # 本地模型推理
app.include_router(config.router)  # 运行时配置
app.include_router(release.router)  # 发行版本上传
app.include_router(stats.router)
app.include_router(health.router)  # 健康检查 v1
app.include_router(health_v2.router)  # 健康检查 v2
app.include_router(location.router)
try:
    from app.api import location_v2
    app.include_router(location_v2.router)  # 地理位置API v2版本
except ImportError:
    logger.warning("location_v2模块导入失败，v2接口不可用")

# 导入v3版本地理位置接口（需要scikit-learn依赖）
try:
    # 先检查scikit-learn依赖
    import sklearn
    from sklearn.cluster import DBSCAN
    from app.api import location_v3
    app.include_router(location_v3.router)  # 地理位置API v3版本（基于大模型）
    logger.info("✓ V3逆地址编码接口已启用（需要scikit-learn依赖）")
except ImportError as e:
    if "sklearn" in str(e) or "scikit-learn" in str(e):
        logger.error(f"✗ V3逆地址编码接口需要scikit-learn依赖，请安装: pip install scikit-learn>=1.3.0")
        raise ImportError(
            "V3逆地址编码接口需要scikit-learn依赖，请安装: pip install scikit-learn>=1.3.0"
        ) from e
    else:
        logger.warning(f"v3地理位置接口模块导入失败，v3接口不可用: {e}")
        location_v3 = None
app.include_router(image_edit.router)  # 图像编辑（v1版本）
if image_edit_v2 is not None:
    app.include_router(image_edit_v2.router)  # 图像编辑（v2版本）
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

