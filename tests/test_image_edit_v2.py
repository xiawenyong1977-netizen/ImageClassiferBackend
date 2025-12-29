"""
图像编辑API v2版本测试
"""

import pytest
import json
import io
from PIL import Image
from httpx import AsyncClient
from app.main import app
from app.services.async_task_service import async_task_service
from app.models.schemas_v2 import TaskStatus
from app.database import db


class TestImageEditV2Batch:
    """测试批量图像编辑提交接口"""
    
    def _create_test_image(self) -> io.BytesIO:
        """创建测试用的图片"""
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    @pytest.mark.asyncio
    async def test_batch_edit_empty_prompt(self, async_client):
        """测试 prompt 为空"""
        image_bytes = self._create_test_image()
        metadata = {
            "items": [{"index": 0, "image_uri": "test://image1.jpg"}],
            "prompt": "",
            "user_id": None
        }
        
        files = {"images": ("test.jpg", image_bytes, "image/jpeg")}
        data = {"image_metadata": json.dumps(metadata)}
        
        response = await async_client.post(
            "/api/v2/image-edit/batch",
            files=files,
            data=data
        )
        assert response.status_code == 400
        assert "prompt字段不能为空" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_batch_edit_no_images(self, async_client):
        """测试没有上传图片"""
        metadata = {
            "items": [],
            "prompt": "test prompt",
            "user_id": None
        }
        
        files = {}
        data = {"image_metadata": json.dumps(metadata)}
        
        response = await async_client.post(
            "/api/v2/image-edit/batch",
            files=files,
            data=data
        )
        # FastAPI 在参数验证阶段就会返回 422（因为 images 是必需的）
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_batch_edit_too_many_images(self, async_client):
        """测试图片数量超过限制（>9张）"""
        # 创建10张图片的文件列表
        image_files = []
        for i in range(10):
            image_bytes = self._create_test_image()
            image_files.append(("images", (f"test{i}.jpg", image_bytes, "image/jpeg")))
        
        metadata = {
            "items": [{"index": i, "image_uri": f"test://image{i}.jpg"} for i in range(10)],
            "prompt": "test prompt",
            "user_id": None
        }
        
        data = {"image_metadata": json.dumps(metadata)}
        
        # 使用 files 参数传递多个文件
        response = await async_client.post(
            "/api/v2/image-edit/batch",
            files=image_files,
            data=data
        )
        # 应该返回400，因为图片数量超过9张
        assert response.status_code == 400
        assert "最多9张图片" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_batch_edit_invalid_image_format(self, async_client):
        """测试无效的图片格式"""
        metadata = {
            "items": [{"index": 0, "image_uri": "test://image1.jpg"}],
            "prompt": "test prompt",
            "user_id": None
        }
        
        # 创建一个无效的图片文件（文本文件）
        invalid_image = io.BytesIO(b"not an image")
        
        files = {"images": ("test.txt", invalid_image, "text/plain")}
        data = {"image_metadata": json.dumps(metadata)}
        
        response = await async_client.post(
            "/api/v2/image-edit/batch",
            files=files,
            data=data
        )
        # 应该返回400，因为图片验证失败
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_batch_edit_success(self, async_client, setup_test_db):
        """测试成功提交批量编辑任务"""
        image_bytes = self._create_test_image()
        metadata = {
            "items": [{"index": 0, "image_uri": "test://image1.jpg"}],
            "prompt": "test prompt",
            "user_id": None
        }
        
        files = {"images": ("test.jpg", image_bytes, "image/jpeg")}
        data = {"image_metadata": json.dumps(metadata)}
        
        # 发送请求（不等待后台任务完成）
        print("DEBUG: 开始发送请求...")
        try:
            response = await async_client.post(
                "/api/v2/image-edit/batch",
                files=files,
                data=data,
                timeout=10.0  # 设置10秒超时，避免卡住
            )
            print(f"DEBUG: 请求完成，status_code={response.status_code}")
        except Exception as e:
            print(f"ERROR: 请求失败: {type(e).__name__}: {e}")
            raise
        
        # 验证响应结构
        print("DEBUG: 开始验证响应...")
        if response.status_code != 200:
            print(f"ERROR: 响应状态码不是200，实际为: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"ERROR: 错误响应内容: {error_detail}")
            except Exception:
                print(f"ERROR: 无法解析错误响应，原始内容: {response.text[:500]}")
        assert response.status_code == 200, f"期望状态码200，实际为{response.status_code}"
        print("DEBUG: status_code 验证通过")
        
        try:
            response_data = response.json()
            print(f"DEBUG: response.json() 完成，task_id={response_data.get('task_id')}")
        except Exception as e:
            print(f"ERROR: 解析响应JSON失败: {type(e).__name__}: {e}")
            print(f"ERROR: 原始响应内容: {response.text[:500]}")
            raise
        
        if "task_id" not in response_data:
            print(f"ERROR: 响应中缺少task_id字段，实际字段: {list(response_data.keys())}")
        assert "task_id" in response_data, f"响应中缺少task_id字段，实际字段: {list(response_data.keys())}"
        
        if "total_images" not in response_data:
            print(f"ERROR: 响应中缺少total_images字段，实际字段: {list(response_data.keys())}")
        assert "total_images" in response_data, f"响应中缺少total_images字段，实际字段: {list(response_data.keys())}"
        
        if "request_id" not in response_data:
            print(f"ERROR: 响应中缺少request_id字段，实际字段: {list(response_data.keys())}")
        assert "request_id" in response_data, f"响应中缺少request_id字段，实际字段: {list(response_data.keys())}"
        
        if "error_type" not in response_data:
            print(f"ERROR: 响应中缺少error_type字段，实际字段: {list(response_data.keys())}")
        assert "error_type" in response_data, f"响应中缺少error_type字段，实际字段: {list(response_data.keys())}"
        
        if response_data.get("error_type") != "success":
            print(f"ERROR: error_type不是'success'，实际为: {response_data.get('error_type')}")
            print(f"ERROR: 完整响应数据: {response_data}")
        assert response_data["error_type"] == "success", f"期望error_type='success'，实际为'{response_data.get('error_type')}'"
        
        if response_data.get("total_images") != 1:
            print(f"ERROR: total_images不是1，实际为: {response_data.get('total_images')}")
        assert response_data["total_images"] == 1, f"期望total_images=1，实际为{response_data.get('total_images')}"
        
        print("DEBUG: 所有断言通过，测试即将结束")
        
        # 给后台任务一点时间完成（最多等待2秒）
        # 如果后台任务还在运行，pytest-asyncio 会等待它们完成，导致测试卡住
        # 这里我们等待一小段时间，让后台任务有机会完成
        import asyncio
        print("DEBUG: 等待后台任务完成（最多2秒）...")
        try:
            await asyncio.wait_for(asyncio.sleep(2), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        print("DEBUG: 等待完成，测试结束")
    
    @pytest.mark.asyncio
    async def test_batch_edit_with_user_id(self, async_client, setup_test_db):
        """测试带 user_id 的提交"""
        # 先清理可能存在的旧数据，然后创建测试绑定数据和用户记录
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 清理可能存在的旧任务（避免干扰）
                await cursor.execute("DELETE FROM async_tasks WHERE task_id LIKE 'task_%' AND user_id = 'test_user_edit'")
                # 清理可能存在的旧绑定数据
                await cursor.execute("DELETE FROM wechat_qrcode_bindings WHERE client_id = 'test_user_edit'")
                # 创建绑定数据
                await cursor.execute("""
                    INSERT INTO wechat_qrcode_bindings 
                    (client_id, scene_id, openid, status, completed_at)
                    VALUES 
                    ('test_user_edit', 'test_scene', 'test_openid_edit', 'completed', NOW())
                """)
                # 清理并创建用户记录（用于额度检查）- 先删除再插入，确保数据一致
                await cursor.execute("DELETE FROM wechat_users WHERE openid = 'test_openid_edit'")
                await cursor.execute("""
                    INSERT INTO wechat_users 
                    (openid, remaining_credits, used_credits, is_member, member_expire_at)
                    VALUES 
                    ('test_openid_edit', 100, 0, 0, NULL)
                """)
                await conn.commit()
        
        image_bytes = self._create_test_image()
        metadata = {
            "items": [{"index": 0, "image_uri": "test://image1.jpg"}],
            "prompt": "test prompt",
            "user_id": "test_user_edit"
        }
        
        files = {"images": ("test.jpg", image_bytes, "image/jpeg")}
        data = {"image_metadata": json.dumps(metadata)}
        
        # 发送请求（不等待后台任务完成）
        print("DEBUG: 开始发送请求...")
        try:
            response = await async_client.post(
                "/api/v2/image-edit/batch",
                files=files,
                data=data,
                headers={"X-User-ID": "test_user_edit"},
                timeout=10.0  # 设置10秒超时，避免卡住
            )
            print(f"DEBUG: 请求完成，status_code={response.status_code}")
        except Exception as e:
            print(f"ERROR: 请求失败: {type(e).__name__}: {e}")
            raise
        
        # 验证响应结构
        print("DEBUG: 开始验证响应...")
        if response.status_code != 200:
            print(f"ERROR: 响应状态码不是200，实际为: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"ERROR: 错误响应内容: {error_detail}")
            except Exception:
                print(f"ERROR: 无法解析错误响应，原始内容: {response.text[:500]}")
        assert response.status_code == 200, f"期望状态码200，实际为{response.status_code}"
        print("DEBUG: status_code 验证通过")
        
        try:
            response_data = response.json()
            print(f"DEBUG: response.json() 完成，task_id={response_data.get('task_id')}")
        except Exception as e:
            print(f"ERROR: 解析响应JSON失败: {type(e).__name__}: {e}")
            print(f"ERROR: 原始响应内容: {response.text[:500]}")
            raise
        
        if "task_id" not in response_data:
            print(f"ERROR: 响应中缺少task_id字段，实际字段: {list(response_data.keys())}")
        assert "task_id" in response_data, f"响应中缺少task_id字段，实际字段: {list(response_data.keys())}"
        
        if response_data.get("error_type") != "success":
            print(f"ERROR: error_type不是'success'，实际为: {response_data.get('error_type')}")
            print(f"ERROR: 完整响应数据: {response_data}")
        assert response_data["error_type"] == "success", f"期望error_type='success'，实际为'{response_data.get('error_type')}'"
        
        if response_data.get("total_images") != 1:
            print(f"ERROR: total_images不是1，实际为: {response_data.get('total_images')}")
        assert response_data["total_images"] == 1, f"期望total_images=1，实际为{response_data.get('total_images')}"
        
        print("DEBUG: 所有断言通过，测试即将结束")
        
        # 给后台任务一点时间完成（最多等待2秒）
        # 如果后台任务还在运行，pytest-asyncio 会等待它们完成，导致测试卡住
        # 这里我们等待一小段时间，让后台任务有机会完成
        import asyncio
        print("DEBUG: 等待后台任务完成（最多2秒）...")
        try:
            await asyncio.wait_for(asyncio.sleep(2), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        print("DEBUG: 等待完成，测试结束")
        
        # 给后台任务一点时间完成（最多等待2秒）
        # 如果后台任务还在运行，pytest-asyncio 会等待它们完成，导致测试卡住
        # 这里我们等待一小段时间，让后台任务有机会完成
        import asyncio
        print("DEBUG: 等待后台任务完成（最多2秒）...")
        try:
            await asyncio.wait_for(asyncio.sleep(2), timeout=2.0)
        except asyncio.TimeoutError:
            pass
        print("DEBUG: 等待完成，测试结束")
        
        # 注意：测试数据会在下次测试开始时清理并重新创建，确保每次测试都从干净状态开始


class TestImageEditV2TaskStatus:
    """测试任务状态查询接口"""
    
    @pytest.fixture
    async def cleanup(self):
        """测试后清理数据"""
        yield
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("DELETE FROM async_tasks WHERE task_id LIKE 'test_%'")
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, async_client):
        """测试查询不存在的任务"""
        response = await async_client.get("/api/v2/image-edit/task/nonexist_task_id")
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_task_status_success(self, async_client, setup_test_db, cleanup):
        """测试成功查询任务状态"""
        # 先创建一个测试任务
        task_id = "test_task_status_1"
        await async_task_service.create_task(
            task_id=task_id,
            task_type="image_edit",
            total_items=2,
            task_params={"prompt": "test prompt"},
            user_id="test_user",
            openid="test_openid"
        )
        
        # 更新任务状态和结果
        await async_task_service.update_task(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            completed_items=2,
            results=[
                {
                    "index": 0,
                    "image_uri": "test://image1.jpg",
                    "status": "completed",
                    "result_url": "https://example.com/result1.jpg",
                    "from_cache": False
                },
                {
                    "index": 1,
                    "image_uri": "test://image2.jpg",
                    "status": "completed",
                    "result_url": "https://example.com/result2.jpg",
                    "from_cache": True
                }
            ]
        )
        
        # 查询任务状态
        response = await async_client.get(f"/api/v2/image-edit/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert data["total_images"] == 2
        assert data["completed_images"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["index"] == 0
        assert data["results"][0]["status"] == "completed"
        assert data["results"][0]["result_url"] == "https://example.com/result1.jpg"
        assert data["results"][0]["from_cache"] is False
        assert data["results"][1]["index"] == 1
        assert data["results"][1]["status"] == "completed"
        assert data["results"][1]["result_url"] == "https://example.com/result2.jpg"
        assert data["results"][1]["from_cache"] is True
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_task_status_pending(self, async_client, setup_test_db, cleanup):
        """测试查询 pending 状态的任务"""
        task_id = "test_task_status_2"
        await async_task_service.create_task(
            task_id=task_id,
            task_type="image_edit",
            total_items=1,
            task_params={"prompt": "test prompt"}
        )
        
        response = await async_client.get(f"/api/v2/image-edit/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"
        assert data["total_images"] == 1
        assert data["completed_images"] == 0
    
    @pytest.mark.asyncio
    async def test_get_task_status_processing(self, async_client, setup_test_db, cleanup):
        """测试查询 processing 状态的任务"""
        task_id = "test_task_status_3"
        await async_task_service.create_task(
            task_id=task_id,
            task_type="image_edit",
            total_items=2,
            task_params={"prompt": "test prompt"}
        )
        
        await async_task_service.update_status(task_id, TaskStatus.PROCESSING)
        await async_task_service.update_task(
            task_id=task_id,
            completed_items=1,
            results=[
                {
                    "index": 0,
                    "image_uri": "test://image1.jpg",
                    "status": "completed",
                    "result_url": "https://example.com/result1.jpg"
                },
                {
                    "index": 1,
                    "image_uri": "test://image2.jpg",
                    "status": "processing"
                }
            ]
        )
        
        response = await async_client.get(f"/api/v2/image-edit/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "processing"
        assert data["total_images"] == 2
        assert data["completed_images"] == 1
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "completed"
        assert data["results"][1]["status"] == "processing"
    
    @pytest.mark.asyncio
    async def test_get_task_status_failed(self, async_client, setup_test_db, cleanup):
        """测试查询 failed 状态的任务"""
        task_id = "test_task_status_4"
        await async_task_service.create_task(
            task_id=task_id,
            task_type="image_edit",
            total_items=1,
            task_params={"prompt": "test prompt"}
        )
        
        await async_task_service.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED,
            completed_items=1,
            results=[
                {
                    "index": 0,
                    "image_uri": "test://image1.jpg",
                    "status": "failed",
                    "error": "处理失败"
                }
            ]
        )
        
        response = await async_client.get(f"/api/v2/image-edit/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "failed"
        assert data["total_images"] == 1
        assert data["completed_images"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "failed"
        assert data["results"][0]["error"] == "处理失败"

