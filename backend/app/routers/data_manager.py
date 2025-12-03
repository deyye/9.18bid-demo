# backend/app/routers/data_manager.py
import datetime # 确保导入
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from ..db_config import get_db
from ..services.table_service import TableService 
from ..models.business_models import Company 

router = APIRouter(prefix="/api/data", tags=["结构化数据管理"])

# 动态创建 Pydantic 模型用于输入校验 (以 Company 为例)
# 简化：直接使用 Dict[str, Any] 作为输入，让 Service 层处理
class CompanyCreateUpdate(BaseModel):
    company_name: str
    parent_id: Optional[str] = None
    address: Optional[str] = None
    # ... 其他字段

# --- 通用表结构查询 ---
@router.get("/tables")
async def get_available_tables():
    """获取所有可管理的业务表名及描述"""
    return {
        "tables": [
            {"name": "t_company", "description": "公司信息表"},
            {"name": "t_attachment", "description": "系统附件表"},
            {"name": "t_business_certification", "description": "资质认证表"},
            {"name": "t_patent", "description": "专利信息表"},
            {"name": "t_software_copyright", "description": "软件著作权表"},
            {"name": "t_product", "description": "产品信息表"},
            {"name": "t_person", "description": "人员信息表"},
            {"name": "t_education_background", "description": "人员学历表"},
            {"name": "t_qualification_certificate", "description": "人员证书表"},
            {"name": "t_project", "description": "项目投标表"},
            {"name": "t_contract", "description": "合同信息表"},
            {"name": "t_project_person", "description": "项目人员表"},
            {"name": "t_bid", "description": "投标文件表"},
            {"name": "t_bid_catalogue", "description": "投标目录表"},
            {"name": "t_bid_file_subentry", "description": "投标分项表"},
        ]
    }

# --- 通用数据列表查询 ---

@router.get("/{table_name}/list")
async def list_data(
    table_name: str,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """分页获取表数据"""
    service = TableService(db)
    return service.list_records(table_name, limit, offset)

# --- t_company CRUD 示例 ---

@router.post("/t_company")
async def create_company_record(data: CompanyCreateUpdate, db: Session = Depends(get_db)):
    """新增公司记录"""
    service = TableService(db)
    return service.create_company(data.model_dump())

@router.put("/t_company/{record_id}")
async def update_company_record(record_id: str, data: CompanyCreateUpdate, db: Session = Depends(get_db)):
    """更新公司记录"""
    service = TableService(db)
    updated_record = service.update_company(record_id, data.model_dump())
    if not updated_record:
        raise HTTPException(status_code=404, detail="记录未找到")
    return updated_record

@router.delete("/{table_name}/{record_id}")
async def delete_data_record(table_name: str, record_id: str, db: Session = Depends(get_db)):
    """删除任意表记录"""
    service = TableService(db)
    if service.delete_record(table_name, record_id):
        return {"success": True, "message": "删除成功"}
    raise HTTPException(status_code=404, detail="记录未找到")