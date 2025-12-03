from sqlalchemy import Column, String, DateTime, func, Text, Date, DECIMAL, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

# 继承自 db_config.py 中的 Base
Base = declarative_base() 
try:
    from ..db_config import Base as AppBase
    Base = AppBase
except ImportError:
    print("Warning: Using local Base. Ensure app.db_config.Base is used in production.")

# ========================================
# 1. 公司信息模块
# ========================================

class Company(Base):
    """对应 t_company (公司表)"""
    __tablename__ = 't_company'

    id = Column(String(100), primary_key=True, comment='公司唯一标识')
    company_name = Column(String(300), nullable=False, comment='公司名称')
    parent_id = Column(String(100), comment='父节点ID')
    address = Column(String(500), comment='公司地址')
    created_by = Column(String(100), nullable=False, default='system', comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 2. 资质认证模块
# ========================================

class BusinessCertification(Base):
    """对应 t_business_certification (资质表)"""
    __tablename__ = 't_business_certification'

    id = Column(String(100), primary_key=True, comment='资质记录ID')
    company_id = Column(String(100), nullable=False, comment='关联公司ID')
    company_name = Column(String(300), comment='公司名称')
    unified_social_credit_code = Column(String(20), comment='统一社会信用代码')
    certificate_number = Column(String(100), comment='证照编号')
    registered_capital = Column(DECIMAL(15, 2), comment='注册资本')
    certification_type = Column(String(50), comment='资质类型')
    establishment_date = Column(Date, comment='成立日期')
    legal_representative = Column(String(100), comment='法定代表人')
    validity_period = Column(Date, comment='有效期')
    address = Column(String(300), comment='住所')
    issuing_authority = Column(String(300), comment='发证机构')
    business_scope = Column(String(1000), comment='经营范围')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 3. 知识产权模块
# ========================================

class Patent(Base):
    """对应 t_patent (专利表)"""
    __tablename__ = 't_patent'

    id = Column(String(100), primary_key=True, comment='专利记录ID')
    company_id = Column(String(100), nullable=False, comment='关联公司ID')
    company_name = Column(String(300), comment='公司名称')
    patent_type = Column(String(50), comment='专利类型')
    patent_number = Column(String(100), comment='专利号')
    patent_name = Column(String(300), comment='专利名称')
    patentee = Column(String(300), comment='专利人')
    issue_date = Column(Date, comment='发证日期')
    protection_start_date = Column(Date, comment='保护期开始时间')
    protection_end_date = Column(Date, comment='保护期结束时间')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class SoftwareCopyright(Base):
    """对应 t_software_copyright (软件著作权表)"""
    __tablename__ = 't_software_copyright'

    id = Column(String(100), primary_key=True, comment='软件著作权ID')
    company_id = Column(String(100), nullable=False, comment='关联公司ID')
    company_name = Column(String(300), comment='公司名称')
    software_name = Column(String(300), comment='软件名称')
    copyright_owner = Column(String(200), comment='著作权人')
    development_completion_date = Column(Date, comment='开发完成日期')
    first_publication_date = Column(Date, comment='首次发表日期')
    acquisition_method = Column(String(50), comment='授权取得方式')
    power_range = Column(String(100), comment='权力范围')
    registration_number = Column(String(100), comment='登记号')
    issue_date = Column(Date, comment='发证日期')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 4. 产品管理模块
# ========================================

class Product(Base):
    """对应 t_product (产品表)"""
    __tablename__ = 't_product'

    id = Column(String(100), primary_key=True, comment='产品ID')
    company_id = Column(String(100), nullable=False, comment='关联公司ID')
    company_name = Column(String(300), comment='所属公司名称')
    product_type = Column(String(300), comment='产品类型')
    product_name = Column(String(500), comment='产品名称')
    product_model = Column(String(500), comment='产品型号')
    purchase_price = Column(DECIMAL(15, 2), comment='进价（元）')
    selling_price = Column(DECIMAL(15, 2), comment='售卖价（元）')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 5. 人员管理模块
# ========================================

class Person(Base):
    """对应 t_person (人员表)"""
    __tablename__ = 't_person'

    id = Column(String(100), primary_key=True, comment='人员ID')
    company_id = Column(String(100), nullable=False, comment='所属公司ID')
    company_name = Column(String(300), comment='所属公司名称')
    person_name = Column(String(100), nullable=False, comment='人员姓名')
    id_card = Column(String(18), comment='身份证号')
    contact_info = Column(String(30), comment='联系方式')
    position = Column(String(50), comment='岗位')
    professional_title = Column(String(50), comment='职称')
    education = Column(String(50), comment='学历')
    birth_date = Column(Date, comment='出生年月')
    political_status = Column(String(50), comment='政治面貌')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class EducationBackground(Base):
    """对应 t_education_background (人员学历表)"""
    __tablename__ = 't_education_background'

    id = Column(String(100), primary_key=True, comment='学历记录ID')
    person_id = Column(String(100), nullable=False, comment='关联人员ID')
    person_name = Column(String(300), comment='人员姓名')
    education_name = Column(String(100), comment='学历名称')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class QualificationCertificate(Base):
    """对应 t_qualification_certificate (人员资格表)"""
    __tablename__ = 't_qualification_certificate'

    id = Column(String(100), primary_key=True, comment='资格记录ID')
    person_id = Column(String(100), nullable=False, comment='关联人员ID')
    person_name = Column(String(300), comment='人员姓名')
    certificate_name = Column(String(100), comment='资格证书名称')
    certificate_number = Column(String(100), comment='证书编号')
    certificate_type = Column(String(100), comment='证书类型')
    certificate_level = Column(String(100), comment='证书等级')
    issue_date = Column(Date, comment='发证日期')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 6. 项目管理模块
# ========================================

class Project(Base):
    """对应 t_project (项目表)"""
    __tablename__ = 't_project'

    id = Column(String(100), primary_key=True, comment='项目ID')
    project_name = Column(String(300), nullable=False, comment='采购项目名称')
    bid_company_id = Column(String(100), nullable=False, comment='投标公司ID')
    bid_company_name = Column(String(300), comment='投标公司名称')
    project_number = Column(String(300), comment='采购项目编号')
    bid_time = Column(Date, comment='投标时间')
    budget_amount = Column(DECIMAL(15, 2), comment='预算金额')
    bid_quote = Column(DECIMAL(15, 2), comment='投标报价')
    is_win = Column(Boolean, comment='是否中标')
    win_amount = Column(DECIMAL(15, 2), comment='中标金额')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class Contract(Base):
    """对应 t_contract (合同表)"""
    __tablename__ = 't_contract'

    id = Column(String(100), primary_key=True, comment='合同ID')
    project_id = Column(String(100), nullable=False, comment='关联项目ID')
    project_name = Column(String(300), comment='采购项目名称')
    project_number = Column(String(300), comment='采购项目编号')
    company_id = Column(String(100), nullable=False, comment='关联公司ID')
    company_name = Column(String(300), comment='公司名称')
    contract_name = Column(String(300), comment='合同名称')
    party_a = Column(String(300), comment='甲方')
    contract_sign_date = Column(Date, comment='合同签订时间')
    contract_amount = Column(DECIMAL(15, 2), comment='合同金额')
    contract_period = Column(Integer, comment='合同期限（月）')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class ProjectPerson(Base):
    """对应 t_project_person (人员参与项目表)"""
    __tablename__ = 't_project_person'

    id = Column(String(100), primary_key=True, comment='参与记录ID')
    contract_id = Column(String(100), nullable=False, comment='关联合同ID')
    contract_name = Column(String(300), comment='合同名称')
    person_id = Column(String(100), nullable=False, comment='关联人员ID')
    person_name = Column(String(300), comment='人员名称')
    position = Column(String(50), comment='职务')
    qualification_certificate_name = Column(String(300), comment='资格证书名称')
    qualification_certificate_id = Column(String(100), comment='资质证书ID')
    qualification_certificate_number = Column(String(100), comment='资质证书编号')
    remark = Column(String(1000), comment='备注')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

# ========================================
# 7. 招投标管理模块
# ========================================

class Bid(Base):
    """对应 t_bid (投标文件表)"""
    __tablename__ = 't_bid'

    id = Column(String(100), primary_key=True, comment='投标文件ID')
    bid_file_name = Column(String(500), comment='投标文件名称')
    tender_file_name = Column(String(500), comment='招标文件名称')
    tender_file_analysis = Column(Text, comment='招标文件解析')
    bid_catalogue_id = Column(String(100), comment='投标文件目录ID')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class BidCatalogue(Base):
    """对应 t_bid_catalogue (投标文件目录表)"""
    __tablename__ = 't_bid_catalogue'

    id = Column(String(100), primary_key=True, comment='目录ID')
    bid_id = Column(String(100), nullable=False, comment='关联投标文件ID')
    catalogue_name = Column(String(300), comment='目录名称')
    parent_id = Column(String(100), comment='父节点ID')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')

class BidFileSubentry(Base):
    """对应 t_bid_file_subentry (投标文件分项表)"""
    __tablename__ = 't_bid_file_subentry'

    id = Column(String(100), primary_key=True, comment='分项ID')
    bid_id = Column(String(100), nullable=False, comment='关联投标文件ID')
    subentry_name = Column(String(500), comment='分项名称')
    parent_id = Column(String(100), comment='父节点ID')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_time = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_by = Column(String(100), comment='修改人')
    updated_time = Column(DateTime, comment='修改时间')