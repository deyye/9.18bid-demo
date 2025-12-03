from sqlalchemy.orm import Session
from ..db_models import Attachment
import uuid
from typing import Optional

class DBService:
    
    def __init__(self, db: Session):
        self.db = db

    def create_attachment(self, external_id: str, external_type: str, file_url: str, file_type: str, created_by: str = "system") -> Attachment:
        """
        步骤 1 & 3: 创建 t_attachment 记录，实现文件与业务的关联。
        external_id 通常是文件名或关联的业务ID。
        """
        new_id = str(uuid.uuid4())
        db_attachment = Attachment(
            id=new_id,
            external_id=external_id,
            external_type=external_type,
            file_url=file_url,
            file_type=file_type,
            created_by=created_by,
        )
        self.db.add(db_attachment)
        self.db.commit()
        self.db.refresh(db_attachment)
        return db_attachment

    def delete_attachments_by_external_id(self, external_id: str):
        """按 external_id (即 RAG source) 删除附件记录"""
        self.db.query(Attachment).filter(Attachment.external_id == external_id).delete()
        self.db.commit()