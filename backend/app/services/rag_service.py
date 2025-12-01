import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# 数据持久化路径
DB_PATH = os.path.join(os.getcwd(), "data", "chroma_db")

class RagService:
    def __init__(self):
        # 1. 确保存储目录存在
        os.makedirs(DB_PATH, exist_ok=True)
        
        # 2. 初始化 ChromaDB 客户端 (持久化模式)
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        # 3. 初始化嵌入模型 
        # 使用适合中文的轻量级模型，首次运行会自动从 HuggingFace 下载
        # 如果下载慢，可以手动下载 'shibing624/text2vec-base-chinese' 并指向本地路径
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="shibing624/text2vec-base-chinese"
        )
        
        # 4. 获取或创建集合 (Collection)
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base",
            embedding_function=self.embedding_fn
        )
        logger.info(f"RAG Service initialized. Collection size: {self.collection.count()}")

    def add_document(self, text: str, source: str, doc_type: str = "general"):
        """
        添加文档到知识库
        :param text: 文档全文
        :param source: 来源文件名
        :param doc_type: 文档类型 (history_bid, product_manual, company_profile)
        """
        # 1. 文本切片 (简单按字符数切分，可优化为按段落切分)
        chunks = self._split_text(text, chunk_size=500, overlap=50)
        
        if not chunks:
            return 0

        # 2. 准备入库数据
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source, "type": doc_type} for _ in chunks]
        
        # 3. 写入向量库 (自动计算 Embedding)
        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(chunks)} chunks from {source}")
        return len(chunks)

    def search(self, query: str, n_results: int = 3) -> List[str]:
        """
        检索相关知识
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # results['documents'] 是 [[doc1, doc2...]] 结构
        if results and results['documents']:
            return results['documents'][0]
        return []

    def clear(self):
        """清空知识库"""
        self.client.delete_collection("bid_knowledge_base")
        self.collection = self.client.get_or_create_collection(
            name="bid_knowledge_base",
            embedding_function=self.embedding_fn
        )

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """简单的滑动窗口切分"""
        if not text: return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            # 移动窗口，保留重叠部分
            start += chunk_size - overlap
            
        return chunks

# 懒加载单例模式
_rag_instance = None

def get_rag_service():
    """获取 RAG 服务单例（懒加载）"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RagService()
    return _rag_instance