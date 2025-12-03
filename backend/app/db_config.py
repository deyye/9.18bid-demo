import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 确保 data 目录存在
os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
# 使用 SQLite 数据库文件，用于存储附件元数据
DATABASE_URL = f"sqlite:///./data/bid_system_attachment.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} 
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