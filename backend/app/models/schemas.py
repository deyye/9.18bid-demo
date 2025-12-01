"""数据模型定义"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum


class ConfigRequest(BaseModel):
    """OpenAI配置请求"""
    model_config = {"protected_namespaces": ()}
    
    api_key: str = Field(..., description="OpenAI API密钥")
    base_url: Optional[str] = Field(None, description="Base URL")
    model_name: str = Field("Qwen3-14B", description="模型名称")


class ConfigResponse(BaseModel):
    """配置响应"""
    success: bool
    message: str


class ModelListResponse(BaseModel):
    """模型列表响应"""
    models: List[str]
    success: bool
    message: str = ""


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    message: str
    file_content: Optional[str] = None


class AnalysisType(str, Enum):
    """分析类型"""
    OVERVIEW = "overview"
    REQUIREMENTS = "requirements"


class AnalysisRequest(BaseModel):
    """文档分析请求"""
    file_content: str = Field(..., description="文档内容")
    analysis_type: AnalysisType = Field(..., description="分析类型")


class OutlineItem(BaseModel):
    """目录项"""
    id: str
    title: str
    description: str
    word_count: Optional[int] = Field(None, description="目标字数")  # 新增字段
    children: Optional[List['OutlineItem']] = None
    content: Optional[str] = None


# 解决循环引用
OutlineItem.model_rebuild()


class OutlineResponse(BaseModel):
    """目录响应"""
    outline: List[OutlineItem]


class OutlineRequest(BaseModel):
    """目录生成请求"""
    overview: str = Field(..., description="项目概述")
    requirements: str = Field(..., description="技术评分要求")


class ContentGenerationRequest(BaseModel):
    """内容生成请求"""
    outline: List[Dict[str, Any]] = Field(..., description="目录结构列表")
    project_overview: str = Field("", description="项目概述")


class ChapterContentRequest(BaseModel):
    """单章节内容生成请求"""
    chapter: Dict[str, Any] = Field(..., description="章节信息")
    parent_chapters: Optional[List[Dict[str, Any]]] = Field(None, description="上级章节列表")
    sibling_chapters: Optional[List[Dict[str, Any]]] = Field(None, description="同级章节列表")
    project_overview: str = Field("", description="项目概述")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    result: str

class OutlineItemSchema(BaseModel):
    id: str
    level: int
    title: str
    # 优化点 1: 新增 word_count 字段，用于接收前端设定的章节字数
    word_count: Optional[int] = None 
    children: Optional[List['OutlineItemSchema']] = None
    
    class Config:
        from_attributes = True
        # 允许内部递归引用
        arbitrary_types_allowed = True
        # ⬇️ 修复 NameError：移除在类定义期间引用自身的 json_encoders
        # json_encoders = {
        #     OutlineItemSchema: lambda v: v.dict(exclude_none=True)
        # }

OutlineItemSchema.update_forward_refs()

class OutlineListSchema(BaseModel):
    outline: List[OutlineItemSchema]
    
class ExportRequest(BaseModel):
    content: Dict[str, str] = Field(..., description="章节内容映射 chapter_id -> text")
    outline: List[OutlineItem] = Field(..., description="目录结构")