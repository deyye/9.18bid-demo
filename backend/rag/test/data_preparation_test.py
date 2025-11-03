import os
import logging
from typing import List

# 添加模块路径
from pathlib import Path
import sys

# 获取当前脚本的绝对路径 → 上一级目录 → 转为字符串
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from dotenv import load_dotenv
from config import DEFAULT_CONFIG, RAGConfig
from rag_modules import (
    TenderDataPreparationModule,
    GenerationIntegrationModule,
    IndexConstructionModule
)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TenderRAGSystem:
    """投标RAG系统主类"""

    def __init__(self, config: RAGConfig = None):
        """
        初始化投标RAG系统

        Args:
            config: 投标RAG系统配置，默认使用DEFAULT_CONFIG
        """
        self.config = config or DEFAULT_CONFIG
        self.data_module = None
        self.index_module = None
        self.retrieval_module = None
        self.generation_module = None

        # 检查数据路径
        if not Path(self.config.data_path).exists():
            raise FileNotFoundError(f"数据路径不存在: {self.config.data_path}")

    def initialize_system(self):
        """初始化模块"""
        print("🚀 正在初始化RAG系统...")

        # 1. 初始化数据准备模块
        print("初始化数据准备模块...")
        self.data_module = TenderDataPreparationModule(self.config.data_path)
        # 2. 初始化索引构建模块
        
        print("初始化索引构建模块...")
        self.index_module = IndexConstructionModule(
            model_name=self.config.embedding_model,
            index_save_path=self.config.index_save_path
        )

        # 3. 初始化生成集成模块
        print("🤖 初始化生成集成模块...")
        self.generation_module = GenerationIntegrationModule(
            model_name=self.config.llm_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        print("✅ 系统初始化完成！")
    
    
    def build_knowledge_base(self):
        """构建知识库"""
        print("\n正在构建知识库...")

        # 1. 尝试加载已保存的索引
        vectorstore = self.index_module.load_index()

        if vectorstore is not None:
            print("✅ 成功加载已保存的向量索引！")
            # 仍需要加载文档和分块用于检索模块
            print("加载投标文档...")
            self.data_module.load_documents()
            print("进行文本分块...")
            chunks = self.data_module.chunk_documents()
        else:
            print("未找到已保存的索引，开始构建新索引...")

            # 2. 加载文档
            print("加载食谱文档...")
            self.data_module.load_documents()

            # 3. 文本分块
            print("进行文本分块...")
            chunks = self.data_module.chunk_documents()

            # 4. 构建向量索引
            print("构建向量索引...")
            vectorstore = self.index_module.build_vector_index(chunks)

            # 5. 保存索引
            print("保存向量索引...")
            self.index_module.save_index()

        # 7. 显示统计信息
        stats = self.data_module.get_statistics()
        print(f"\n📊 知识库统计:")
        print(f"   文档总数: {stats['total_documents']}")
        print(f"   文本块数: {stats['total_chunks']}")
        print(f"   菜品分类: {list(stats['categories'].keys())}")
        print(f"   难度分布: {stats['difficulties']}")

        print("✅ 知识库构建完成！")
    
    def run_interactive(self):
        """运行交互式问答"""
        print("=" * 60)
        print("🍽️  尝尝咸淡RAG系统 - 交互式问答  🍽️")
        print("=" * 60)
        print("💡 解决您的选择困难症，告别'今天吃什么'的世纪难题！")
        
        # 初始化系统
        self.initialize_system()
        
        # 构建知识库
        self.build_knowledge_base()
    
def main():
    """主函数"""
    try:
        # 创建RAG系统
        rag_system = TenderRAGSystem()
        
        # 运行交互式问答
        rag_system.run_interactive()
        
    except Exception as e:
        logger.error(f"系统运行出错: {e}")
        print(f"系统错误: {e}")

if __name__ == "__main__":
    main()