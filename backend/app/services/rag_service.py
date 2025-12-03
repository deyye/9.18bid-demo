import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "chroma_db")

# 更改为本地模型路径
LOCAL_MODEL_PATH = "/home/star/81/8.11rag_kefu/embedding" 
EMBEDDING_MODEL_NAME = LOCAL_MODEL_PATH 

class RagService:
    def __init__(self):
        logger.info("正在初始化 RAG 向量数据库服务 (这可能会占用一些内存)...")
        os.makedirs(DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        try:
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME
            )
        except Exception as e:
            logger.error(f"RAG EMBEDDING 初始化失败，请检查模型路径是否正确: {EMBEDDING_MODEL_NAME}. 错误: {e}")
            # 如果加载失败，使用一个默认的占位函数，但功能将失效
            def placeholder_fn(texts):
                raise RuntimeError("Embedding Model load failed. RAG is non-functional.")
            self.embedding_fn = placeholder_fn
        
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base",
            embedding_function=self.embedding_fn
        )
        logger.info(f"RAG Service 初始化完成. 当前知识库条目数: {self.collection.count()}")

    def add_document(self, text: str, source: str, doc_type: str = "general"):
        chunks = self._split_text(text, chunk_size=500, overlap=50)
        if not chunks: return 0
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source, "type": doc_type, "content_type": "text"} for _ in chunks] # 修正metadata结构
        self.collection.add(documents=chunks, metadatas=metadatas, ids=ids)
        return len(chunks)

    def search(self, query: str, n_results: int = 3) -> List[str]:
        if self.collection.count() == 0: return []
        
        # 修正：确保在查询时只返回 documents
        results = self.collection.query(
            query_texts=[query], 
            n_results=n_results,
            include=["documents", "metadatas"] # 需要包含 metadatas 才能在 routers/content.py 中格式化
        )
        
        # 修正：返回结构化数据，包含来源和内容，以便 content.py 中使用
        if results and results.get('documents'):
            retrieved_data = []
            for i in range(len(results['documents'][0])):
                doc_content = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                retrieved_data.append({
                    "content": doc_content,
                    "source": metadata.get("source", "unknown"),
                    "type": metadata.get("type", "general")
                })
            return retrieved_data
        return []

    def clear(self):
        self.client.delete_collection("bid_knowledge_base")
        # 重新创建 collection，但需要确保 embedding_fn 已经初始化
        if hasattr(self, 'embedding_fn'):
            self.collection = self.client.get_or_create_collection(
                name="bid_knowledge_base", embedding_function=self.embedding_fn
            )
        else:
             self.collection = self.client.get_or_create_collection(name="bid_knowledge_base")


    # 修正 list_documents 接口，确保返回与前端预期一致
    def list_documents(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        count = self.collection.count()
        if count == 0:
            return {"total": 0, "items": []}
        
        results = self.collection.get(
            limit=limit,
            offset=offset,
            include=["metadatas", "documents"]
        )
        
        items = []
        if results and results.get('ids'):
            for i, id in enumerate(results['ids']):
                meta = results['metadatas'][i] if results['metadatas'] else {}
                doc = results['documents'][i] if results['documents'] else ""
                items.append({
                    "id": id,
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "type": meta.get("type", "general")
                })
        
        return {
            "total": count,
            "items": items
        }

    def delete_document_by_source(self, source: str):
        self.collection.delete(where={"source": source})
        
    def search(self, query: str, n_results: int = 3, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        检索知识库
        :param filter: ChromaDB 的 where 过滤条件，例如 {"source": "filename.pdf"} 或 {"source": {"$in": [...]}}
        """
        if self.collection.count() == 0: return []
        
        try:
            results = self.collection.query(
                query_texts=[query], 
                n_results=n_results,
                where=filter, # ✅ 传入过滤条件
                include=["documents", "metadatas"]
            )
            
            if results and results.get('documents'):
                retrieved_data = []
                for i in range(len(results['documents'][0])):
                    doc_content = results['documents'][0][i]
                    metadata = results['metadatas'][0][i]
                    retrieved_data.append({
                        "content": doc_content,
                        "source": metadata.get("source", "unknown"),
                        "type": metadata.get("type", "general")
                    })
                return retrieved_data
        except Exception as e:
            logger.error(f"RAG Search Error: {e}")
            return []
        return []

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        if not text: return []
        # 使用更简单的基于字符数的切割，因为我们没有 LangChain 文档加载器
        chunks = []
        text_len = len(text)
        start = 0
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

# 单例模式
_rag_instance = None
def get_rag_service():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagService()
    return _rag_instance