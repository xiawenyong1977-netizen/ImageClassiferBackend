"""
发行版本上传接口
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from datetime import datetime
import os
import aiofiles

from app.auth import get_current_user
from loguru import logger

router = APIRouter(prefix="/api/v1/release", tags=["release"])

# 目标目录
RELEASE_DIR = "/var/www/xintuxiangce/dist"


@router.post("/upload", summary="上传发行版本")
async def upload_release(
    file: UploadFile = File(..., description="发行版本zip文件"),
    current_user: str = Depends(get_current_user)
):
    """
    上传发行版本zip文件到服务器
    
    文件会保存到 /var/www/xintuxiangce/dist 目录
    文件名格式：xtxc{YYYYMMDDHHMM}.zip
    
    **需要认证**
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="只支持zip文件")
        
        # 确保目标目录存在
        os.makedirs(RELEASE_DIR, exist_ok=True)
        
        # 生成文件名：xtxc + 日期时分.zip
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        filename = f"xtxc{timestamp}.zip"
        file_path = os.path.join(RELEASE_DIR, filename)
        
        # 读取上传的文件
        contents = await file.read()
        file_size = len(contents)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(contents)
        
        logger.info(f"发行版本上传成功: {filename}, 大小: {file_size / 1024 / 1024:.2f}MB, 操作者: {current_user}")
        
        return {
            "success": True,
            "message": "发行版本上传成功",
            "filename": filename,
            "file_path": file_path,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "upload_time": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发行版本上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/list", summary="获取发行版本列表")
async def list_releases(current_user: str = Depends(get_current_user)):
    """
    获取已上传的发行版本列表
    
    **需要认证**
    """
    try:
        if not os.path.exists(RELEASE_DIR):
            return {
                "success": True,
                "releases": [],
                "total": 0
            }
        
        # 获取所有zip文件
        files = []
        for filename in os.listdir(RELEASE_DIR):
            if filename.startswith('xtxc') and filename.endswith('.zip'):
                file_path = os.path.join(RELEASE_DIR, filename)
                stat = os.stat(file_path)
                
                files.append({
                    "filename": filename,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 按文件名降序排序（最新的在前）
        files.sort(key=lambda x: x['filename'], reverse=True)
        
        return {
            "success": True,
            "releases": files,
            "total": len(files)
        }
        
    except Exception as e:
        logger.error(f"获取发行版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


