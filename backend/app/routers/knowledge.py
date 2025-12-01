from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..services.file_service import FileService
from ..services.rag_service import get_rag_service

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])

class KnowledgeResponse(BaseModel):
    success: bool
    message: str
    chunks_added: int = 0

@router.post("/upload", response_model=KnowledgeResponse)
async def upload_knowledge(
    file: UploadFile = File(...),
    doc_type: str = "general" 
):
    """上传企业知识库文件"""
    try:
        file_path = await FileService.save_uploaded_file(file)
        
        text = ""
        if file.content_type == "application/pdf":
            text = FileService.extract_text_from_pdf(file_path)
        elif "wordprocessingml" in file.content_type:
            text = FileService.extract_text_from_docx(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        if not text:
            raise HTTPException(status_code=400, detail="无法提取文本内容")

        rag_service = get_rag_service()
        count = rag_service.add_document(text, source=file.filename, doc_type=doc_type)
        
        FileService._safe_file_cleanup(file_path)

        return KnowledgeResponse(
            success=True, 
            message=f"文件 {file.filename} 已处理并入库", 
            chunks_added=count
        )

    except Exception as e:
        return KnowledgeResponse(success=False, message=f"处理失败: {str(e)}")

@router.post("/reset", response_model=KnowledgeResponse)
async def reset_knowledge():
    get_rag_service().clear()
    return KnowledgeResponse(success=True, message="知识库已清空")

@router.post("/test-search")
async def test_search(query: str):
    results = get_rag_service().search(query)
    return {"query": query, "results": results}

# ✅ 新增：获取列表接口
@router.get("/list")
async def list_knowledge(limit: int = 10, offset: int = 0):
    """分页获取知识库内容"""
    return get_rag_service().list_documents(limit, offset)

# ✅ 新增：删除文件接口
@router.delete("/delete")
async def delete_knowledge_file(source: str):
    """根据文件名删除知识库内容"""
    get_rag_service().delete_document_by_source(source)
    return {"success": True, "message": f"文件 {source} 的相关知识已删除"}