"""配置相关API路由"""
from fastapi import APIRouter, HTTPException
from ..models.schemas import ConfigRequest, ConfigResponse, ModelListResponse
from ..services.openai_service import OpenAIService
from ..utils.config_manager import config_manager
import httpx
from typing import List, Optional
import aiohttp
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["配置管理"])
# 数据模型定义
class ConfigRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    use_local_qwen: bool = True

class ModelInfo(BaseModel):
    id: str
    name: str

class ModelListResponse(BaseModel):
    models: List[ModelInfo]
    success: bool
    message: str
# Qwen服务类（处理10086端口的本地模型）
class QwenService:
    def __init__(self, port: int = 10086):
        self.base_url = f"http://localhost:{port}"
        self.models = [
            ModelInfo(id="qwen-4b", name="Qwen 4B"),
            ModelInfo(id="qwen-14b", name="Qwen 14B"),
        ]
    async def get_available_models(self) -> List[ModelInfo]:
        """获取本地qwen模型列表"""
        try:
            # 尝试从本地服务获取模型列表
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        # 假设返回格式与OpenAI类似
                        return [ModelInfo(id=m["id"], name=m["name"]) for m in data.get("data", [])]
        except Exception:
            # 获取失败，返回预设的模型列表
            return self.models
        return self.models

@router.post("/save", response_model=ConfigResponse)
async def save_config(config: ConfigRequest):
    """保存OpenAI配置"""
    try:
        success = config_manager.save_config(
            api_key=config.api_key,
            base_url=config.base_url or "",
            model_name=config.model_name
        )
        
        if success:
            return ConfigResponse(success=True, message="配置保存成功")
        else:
            return ConfigResponse(success=False, message="配置保存失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置时发生错误: {str(e)}")


@router.get("/load", response_model=dict)
async def load_config():
    """加载保存的配置"""
    try:
        config = config_manager.load_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载配置时发生错误: {str(e)}")


@router.post("/models", response_model=ModelListResponse)
async def get_available_models(config: ConfigRequest):
    """获取可用的模型列表，包括10086端口的qwen模型"""
    try:
        models = []
        if (config.api_key == 'qwen') and config.use_local_qwen:
            qwen_service = QwenService(port=10086)
            qwen_models = await qwen_service.get_available_models()
            models.extend(qwen_models)
            return ModelListResponse(
                models=models,
                success=False,
                message=f"获取到 {len(models)} 个模型"
            )
        
        # 提供了OpenAI的API Key，获取OpenAI模型
        if config.api_key:
            openai_service = OpenAIService(
                api_key=config.api_key,
                base_url=config.base_url,
                model_name=config.model_name
            )
            openai_models = await openai_service.get_available_models()
            models.extend(openai_models)
        
        if not models:
            return ModelListResponse(
                models=[],
                success=False,
                message="未配置任何可用模型"
            )
        
        return ModelListResponse(
            models=models,
            success=True,
            message=f"获取到 {len(models)} 个模型"
        )
        
    except Exception as e:
        return ModelListResponse(
            models=[],
            success=False,
            message=f"获取模型列表失败: {str(e)}"
        )