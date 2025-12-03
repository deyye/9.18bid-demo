from sqlalchemy import Column, String, DateTime, func, Text, Date, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

# 继承自 db_config.py 中的 Base，但由于我们不修改 db_config.py，这里先临时定义一个 Base
# 实际运行时，必须确保这个 Base 导入自 app.db_config
Base = declarative_base() 
try:
    from ..db_config import Base as AppBase
    Base = AppBase
except ImportError:
    print("Warning: Using local Base. Ensure app.db_config.Base is used in production.")

# ----------------------------------------------------
# 仅以 t_company 为例实现完整的 CRUD 示例
# ----------------------------------------------------

class Company(Base):
    """对应 t_company (公司表) 的 ORM 模型"""
    __tablename__ = 't_company'

    id = Column(String(100), primary_key=True, comment='公司唯一标识')
    company_name = Column(String(300), nullable=False, comment='公司名称')
    parent_id = Column(String(100), comment='父节点ID')
    address = Column(String(500), comment='公司地址')
    
    # 审计字段 (简化处理，只定义字段)
    created_by = Column(String(100), nullable=False, default='system', comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')
    
    def __repr__(self):
        return f"<Company(id='{self.id}', name='{self.company_name}')>"

# ----------------------------------------------------
# 其他核心表模型（仅作占位和示例，需手动补全）
# ----------------------------------------------------

# class Person(Base):
#     __tablename__ = 't_person'
#     ...