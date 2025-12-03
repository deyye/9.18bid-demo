from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session 
import os, uuid

from ..services.file_service import FileService
from ..services.rag_service import get_rag_service
from ..services.db_service import DBService 
from ..db_config import get_db 

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])

class KnowledgeResponse(BaseModel):
    success: bool
    message: str
    chunks_added: int = 0
    attachment_id: Optional[str] = None 

@router.post("/upload", response_model=KnowledgeResponse)
async def upload_knowledge(
    file: UploadFile = File(...),
    doc_type: str = "general", # external_type
    db: Session = Depends(get_db) 
):
    """
    步骤 1 & 2 & 3: 上传文件，保存到本地，存储元数据到 t_attachment，并添加到 RAG 知识库。
    """
    temp_file_path = None
    try:
        # 1. 保存文件到本地
        temp_file_path = await FileService.save_uploaded_file(file)
        
        # 2. 提取文本
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext == ".pdf":
            text = FileService.extract_text_from_pdf(temp_file_path)
        elif file_ext in [".doc", ".docx"]:
            text = FileService.extract_text_from_docx(temp_file_path)
        else:
            with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        if not text:
            raise HTTPException(status_code=400, detail="无法提取文本内容，请检查文件格式")

        # 3. 存储元数据到 t_attachment (步骤 1 & 3)
        db_service = DBService(db)
        
        # 使用文件名作为 external_id (即 RAG 的 source)，用于关联和删除
        attachment_record = db_service.create_attachment(
            external_id=file.filename,         
            external_type=doc_type,            
            file_url=temp_file_path,           
            file_type=file.content_type or file_ext,
            created_by="user_upload"
        )

        # 4. 动态知识库构建 (Indexing) (步骤 2)
        rag_service = get_rag_service()
        # 将文件名作为 RAG 的 source
        count = rag_service.add_document(text, source=file.filename, doc_type=doc_type)
        
        return KnowledgeResponse(
            success=True, 
            message=f"文件 {file.filename} 已处理并入库", 
            chunks_added=count,
            attachment_id=attachment_record.id
        )

    except HTTPException:
        # 异常时清理文件（如果文件路径存在且未被清理）
        if temp_file_path and os.path.exists(temp_file_path): FileService._safe_file_cleanup(temp_file_path)
        raise
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path): FileService._safe_file_cleanup(temp_file_path)
        return KnowledgeResponse(success=False, message=f"处理失败: {str(e)}")


@router.delete("/delete")
async def delete_knowledge_file(source: str, db: Session = Depends(get_db)):
    """根据文件名（即 RAG source/external_id）删除知识库内容及附件记录"""
    # 1. 删除 RAG 索引
    get_rag_service().delete_document_by_source(source)
    
    # 2. 删除附件记录 (步骤 3 维护一致性)
    db_service = DBService(db)
    db_service.delete_attachments_by_external_id(source) 
    
    return {"success": True, "message": f"文件 {source} 的相关知识已删除"}


@router.post("/reset", response_model=KnowledgeResponse)
async def reset_knowledge():
    get_rag_service().clear()
    return KnowledgeResponse(success=True, message="知识库已清空")

@router.post("/test-search")
async def test_search(query: str):
    # 确保 rag_service.search 返回的 List[str] 被正确包装
    results = get_rag_service().search(query)
    # 将 List[str] 转换为 List[Dict] 以便前端处理，但由于 rag_service.py 返回的是 List[str]，
    # 这里直接返回纯文本列表
    return {"query": query, "results": results}

@router.get("/list")
async def list_knowledge(limit: int = 10, offset: int = 0):
    """分页获取知识库内容"""
    return get_rag_service().list_documents(limit, offset)