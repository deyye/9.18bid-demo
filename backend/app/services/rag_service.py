import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "chroma_db")

class RagService:
    def __init__(self):
        logger.info("正在初始化 RAG 向量数据库服务 (这可能会占用一些内存)...")
        os.makedirs(DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="shibing624/text2vec-base-chinese"
        )
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base",
            embedding_function=self.embedding_fn
        )
        logger.info(f"RAG Service 初始化完成. 当前知识库条目数: {self.collection.count()}")

    def add_document(self, text: str, source: str, doc_type: str = "general"):
        chunks = self._split_text(text, chunk_size=500, overlap=50)
        if not chunks: return 0
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source, "type": doc_type} for _ in chunks]
        self.collection.add(documents=chunks, metadatas=metadatas, ids=ids)
        return len(chunks)

    def search(self, query: str, n_results: int = 3) -> List[str]:
        if self.collection.count() == 0: return []
        results = self.collection.query(query_texts=[query], n_results=n_results)
        if results and results['documents']: return results['documents'][0]
        return []

    def clear(self):
        self.client.delete_collection("bid_knowledge_base")
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base", embedding_function=self.embedding_fn
        )

    # ✅ 新增：分页列出知识库内容
    def list_documents(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        count = self.collection.count()
        if count == 0:
            return {"total": 0, "items": []}
        
        # 获取数据 (只获取 metadata 和 documents，不获取 embeddings 以节省流量)
        results = self.collection.get(
            limit=limit,
            offset=offset,
            include=["metadatas", "documents"]
        )
        
        items = []
        if results and results['ids']:
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

    # ✅ 新增：按来源文件名删除文档
    def delete_document_by_source(self, source: str):
        # ChromaDB 支持 where 过滤删除
        self.collection.delete(where={"source": source})

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        if not text: return []
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

# 单例模式
_rag_instance = None

def get_rag_service():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagService()
    return _rag_instance