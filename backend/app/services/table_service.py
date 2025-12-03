from sqlalchemy.orm import Session
from sqlalchemy import exc, update, delete, func
from sqlalchemy.sql import text
import uuid
import logging
from typing import List, Dict, Any, Type
import datetime

from ..models.business_models import (
    Company, BusinessCertification, Patent, SoftwareCopyright,
    Product, Person, EducationBackground, QualificationCertificate,
    Project, Contract, ProjectPerson, Bid, BidCatalogue, BidFileSubentry
)
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class TableService:
    """
    通用数据库表操作服务，以 t_company 为主要实现示例。
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_table_model(self, table_name: str) -> Type[Any] | None:
        """根据表名返回对应的 ORM 模型"""
        mapping = {
            't_company': Company,
            't_business_certification': BusinessCertification,
            't_patent': Patent,
            't_software_copyright': SoftwareCopyright,
            't_product': Product,
            't_person': Person,
            't_education_background': EducationBackground,
            't_qualification_certificate': QualificationCertificate,
            't_project': Project,
            't_contract': Contract,
            't_project_person': ProjectPerson,
            't_bid': Bid,
            't_bid_catalogue': BidCatalogue,
            't_bid_file_subentry': BidFileSubentry
        }
        
        return mapping.get(table_name)

    # --- 通用查询逻辑 ---
    
    def list_records(self, table_name: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """分页查询指定表的记录"""
        Model = self.get_table_model(table_name)
        if Model is None:
            raise ValueError(f"不支持的表名: {table_name}")

        try:
            # 总数查询
            total_count = self.db.query(Model).count()
            
            # 数据查询
            records = self.db.query(Model).limit(limit).offset(offset).all()
            
            # 转换为字典列表
            items = []
            for record in records:
                # SQLAlchemy 记录转字典，注意处理 DateTime 等非 JSON 格式
                item_dict = {c.name: getattr(record, c.name) for c in record.__table__.columns}
                
                # 简单格式化日期时间
                for key, value in item_dict.items():
                    if isinstance(value, (datetime.date, datetime.datetime)):
                        item_dict[key] = value.isoformat()
                
                items.append(item_dict)

            return {
                "total": total_count,
                "items": items
            }
        except exc.SQLAlchemyError as e:
            logger.error(f"查询表 {table_name} 失败: {e}")
            raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")

    # --- 通用 CRUD 逻辑 (以 t_company 为例) ---

    def create_company(self, data: Dict[str, Any]) -> Dict[str, Any]:
        new_id = str(uuid.uuid4())
        data['id'] = new_id
        data['created_by'] = data.get('created_by', 'api_user')
        
        # 移除模型中不存在的键
        Model = Company
        valid_keys = {c.name for c in Model.__table__.columns}
        record_data = {k: v for k, v in data.items() if k in valid_keys}
        
        new_record = Model(**record_data)
        self.db.add(new_record)
        self.db.commit()
        self.db.refresh(new_record)
        
        # 转换为字典并返回
        return {c.name: getattr(new_record, c.name) for c in new_record.__table__.columns}

    def update_company(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any] | None:
        # 过滤掉不可修改的字段
        data.pop('id', None)
        data.pop('created_time', None)
        data.pop('created_by', None)
        
        record = self.db.query(Company).filter(Company.id == record_id).first()
        if not record:
            return None
        
        for key, value in data.items():
            setattr(record, key, value)
        
        record.updated_by = data.get('updated_by', 'api_user')
        record.updated_time = func.now()
        
        self.db.commit()
        self.db.refresh(record)
        return {c.name: getattr(record, c.name) for c in record.__table__.columns}

    def delete_record(self, table_name: str, record_id: str) -> bool:
        Model = self.get_table_model(table_name)
        if Model is None:
            raise ValueError(f"不支持的表名: {table_name}")

        result = self.db.query(Model).filter(Model.id == record_id).delete()
        self.db.commit()
        return result > 0