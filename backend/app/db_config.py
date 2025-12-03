import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# =========================================================
# 切换为 MySQL 配置
# =========================================================

# 请根据实际 MySQL 配置修改以下信息
MYSQL_USER = "root"          # 数据库用户名
MYSQL_PASSWORD = "123456"    # 数据库密码
MYSQL_HOST = "10.11.30.18"   # 数据库IP
MYSQL_PORT = "3306"          # 数据库端口
MYSQL_DB = "enterprise_management_system" # 数据库名（对应上传的SQL文件）

# 构建 MySQL 连接字符串
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"

# os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
# DATABASE_URL = f"sqlite:///./data/bid_system_attachment.db"

# 创建数据库引擎
# 注意：MySQL通常不需要 connect_args={"check_same_thread": False}，这是SQLite专用的
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,        # 每个进程维持5个空闲连接
    max_overflow=0,     # 超过pool_size后不创建新连接（或者设为很小的值如2）
    pool_timeout=30     # 等待连接的超时时间
)

# 创建 SessionLocal 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 依赖函数，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()