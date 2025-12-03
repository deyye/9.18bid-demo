from sqlalchemy import Column, String, DateTime, func
from .db_config import Base

# 对应 deepseek_sql_20251114_625c41.sql 中的 t_attachment 表结构
class Attachment(Base):
    __tablename__ = 't_attachment'
    
    id = Column(String(100), primary_key=True, comment='附件唯一标识')
    external_id = Column(String(100), nullable=False, comment='外部表ID/关联ID')
    external_type = Column(String(50), nullable=False, comment='关联类型（如：knowledge_doc, project_bid, company_qual）')
    file_url = Column(String(300), nullable=False, comment='附件地址/本地路径')
    file_type = Column(String(50), nullable=False, comment='附件类型')
    
    # 审计字段
    created_by = Column(String(100), nullable=False, default='system', comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

    def __repr__(self):
        return f"<Attachment(id='{self.id}', external_id='{self.external_id}', url='{self.file_url}')>"