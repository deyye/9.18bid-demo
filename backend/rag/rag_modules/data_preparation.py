"""
投标文件数据准备模块
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import uuid

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class TenderDataPreparationModule:
    """投标文件数据准备模块 - 负责投标文件的加载、清洗和预处理"""
    # 投标文件核心分类
    CATEGORY_MAPPING = {
        'technical': '技术方案',
        'commercial': '商务报价',
        'qualification': '资质证明',
        'legal': '法律文件',
        'supporting': '辅助材料'
    }
    CATEGORY_LABELS = list(set(CATEGORY_MAPPING.values()))
    # 投标文件关键章节类型
    SECTION_TYPES = ['投标函', '技术参数', '实施方案', '服务承诺', '报价明细', '资质证件']
    
    def __init__(self, data_path: str):
        """
        初始化投标文件数据准备模块
        
        Args:
            data_path: 投标文件文件夹路径
        """
        self.data_path = data_path
        self.documents: List[Document] = []  # 父文档（完整投标文件）
        self.chunks: List[Document] = []     # 子文档（按章节分割的小块）
        self.parent_child_map: Dict[str, str] = {}  # 子块ID -> 父文档ID的映射
    
    def load_documents(self) -> List[Document]:
        """
        加载投标文件（支持Markdown和纯文本）
        
        Returns:
            加载的文档列表
        """
        logger.info(f"正在从 {self.data_path} 加载投标文件...")
        
        documents = []
        data_path_obj = Path(self.data_path)

        # 支持的文件类型：.md .txt .docx（简化处理，实际可增加python-docx解析）
        for file in data_path_obj.rglob("*"):
            if file.suffix not in ['.md', '.txt', '.docx']:
                continue
                
            try:
                # 读取文件内容（docx此处简化为文本读取，实际需专用库）
                if file.suffix == '.docx':
                    content = self._read_docx(file)
                else:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()

                # 生成父文档唯一ID（基于相对路径）
                try:
                    data_root = Path(self.data_path).resolve()
                    relative_path = file.resolve().relative_to(data_root).as_posix()
                except Exception:
                    relative_path = file.as_posix()
                parent_id = hashlib.md5(relative_path.encode("utf-8")).hexdigest()

                # 创建Document对象
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(file),
                        "parent_id": parent_id,
                        "file_type": file.suffix,
                        "doc_type": "parent"  # 标记为父文档
                    }
                )
                documents.append(doc)

            except Exception as e:
                logger.warning(f"读取文件 {file} 失败: {e}")
        
        # 增强文档元数据
        for doc in documents:
            self._enhance_metadata(doc)
        
        self.documents = documents
        logger.info(f"成功加载 {len(documents)} 个投标文件")
        return documents
    
    def _read_docx(self, file_path: Path) -> str:
        """读取docx文件内容（需安装python-docx）"""
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        except ImportError:
            raise ImportError("请安装python-docx库以处理docx文件：pip install python-docx")
        except Exception as e:
            logger.error(f"解析docx文件失败：{e}")
            return ""
    
    def _enhance_metadata(self, doc: Document):
        """
        增强投标文件元数据
        
        提取信息：文件分类、项目名称、文档版本等
        """
        file_path = Path(doc.metadata.get('source', ''))
        path_parts = file_path.parts
        
        # 提取文件分类（基于路径关键词）
        doc.metadata['category'] = '其他'
        for key, value in self.CATEGORY_MAPPING.items():
            if key in [part.lower() for part in path_parts]:
                doc.metadata['category'] = value
                break
        
        # 提取项目名称（简化：从文件名提取，实际可从内容解析）
        doc.metadata['project_name'] = self._extract_project_name(file_path.stem, doc.page_content)
        
        # 提取文档版本
        doc.metadata['version'] = self._extract_version(doc.page_content)

        # 提取创建日期（从文件属性获取）
        try:
            doc.metadata['created_time'] = file_path.stat().st_ctime
        except Exception:
            doc.metadata['created_time'] = None

    def _extract_project_name(self, file_stem: str, content: str) -> str:
        """从文件名或内容提取项目名称"""
        # 简化逻辑：优先从文件名提取，再从内容前1000字符提取
        if '项目' in file_stem:
            return file_stem
        for line in content[:1000].split('\n'):
            if '项目名称' in line:
                return line.split('：')[-1].strip()
        return '未知项目'
    
    def _extract_version(self, content: str) -> str:
        """提取文档版本号（如V1.0）"""
        import re
        match = re.search(r'版本\s*[:：]\s*([Vv\d.]+)', content[:500])
        if match:
            return match.group(1)
        return '未知版本'

    @classmethod
    def get_supported_categories(cls) -> List[str]:
        """对外提供支持的分类标签列表"""
        return cls.CATEGORY_LABELS

    def chunk_documents(self) -> List[Document]:
        """
        投标文件结构化分块（优先按标题分割，其次按字符长度）

        Returns:
            分块后的文档列表
        """
        logger.info("正在进行投标文件结构化分块...")

        if not self.documents:
            raise ValueError("请先加载文档")

        # 混合分块策略：Markdown标题分割 + 递归字符分割
        chunks = []
        for doc in self.documents:
            if doc.metadata.get('file_type') == '.md':
                # Markdown文件优先按标题分割
                md_chunks = self._markdown_header_split(doc)
                chunks.extend(md_chunks)
            else:
                # 其他文件按章节+字符长度分割
                text_chunks = self._text_section_split(doc)
                chunks.extend(text_chunks)

        # 完善子块元数据
        for i, chunk in enumerate(chunks):
            if 'chunk_id' not in chunk.metadata:
                chunk.metadata['chunk_id'] = str(uuid.uuid4())
            chunk.metadata['batch_index'] = i
            chunk.metadata['chunk_size'] = len(chunk.page_content)
            chunk.metadata['section_type'] = self._identify_section_type(chunk.page_content)

        self.chunks = chunks
        logger.info(f"分块完成，共生成 {len(chunks)} 个子块")
        return chunks

    def _markdown_header_split(self, doc: Document) -> List[Document]:
        """Markdown格式投标文件按标题分割"""
        headers_to_split_on = [
            ("#", "章"),      # 一级章节（如"一、技术方案"）
            ("##", "节"),     # 二级章节（如"1.1 实施方案"）
            ("###", "条")     # 三级条款（如"1.1.1 实施步骤"）
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False  # 保留标题便于上下文理解
        )

        try:
            md_chunks = markdown_splitter.split_text(doc.page_content)
            parent_id = doc.metadata["parent_id"]

            for i, chunk in enumerate(md_chunks):
                child_id = str(uuid.uuid4())
                # 合并元数据
                chunk.metadata.update(doc.metadata)
                chunk.metadata.update({
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "doc_type": "child",
                    "chunk_index": i,
                    "split_method": "markdown_header"
                })
                self.parent_child_map[child_id] = parent_id

            return md_chunks
        except Exception as e:
            logger.warning(f"Markdown分割失败，降级为字符分割: {e}")
            return self._text_section_split(doc)

    def _text_section_split(self, doc: Document) -> List[Document]:
        """纯文本投标文件按章节+字符长度分割"""
        # 针对投标文件的分隔符（章节标题模式）
        separators = [
            r'\n第[一二三四五六七八九十]+章',  # 中文章节
            r'\n\d+\.\s',                       # 数字编号（1. 2.）
            r'\n[A-Z]\.\s',                     # 字母编号（A. B.）
            r'\n===+\n',                        # 分割线
            '\n\n'                              # 段落分隔
        ]

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,        # 子块大小（可根据投标文件复杂度调整）
            chunk_overlap=100,      # 重叠部分保留上下文
            separators=separators,
            length_function=len
        )

        try:
            text_chunks = text_splitter.split_documents([doc])
            parent_id = doc.metadata["parent_id"]

            for i, chunk in enumerate(text_chunks):
                child_id = str(uuid.uuid4())
                chunk.metadata.update({
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "doc_type": "child",
                    "chunk_index": i,
                    "split_method": "text_section"
                })
                self.parent_child_map[child_id] = parent_id

            return text_chunks
        except Exception as e:
            logger.error(f"文本分割失败: {e}")
            return [doc]  # 分割失败则保留原文档

    def _identify_section_type(self, content: str) -> str:
        """识别子块所属章节类型（如报价明细、技术参数等）"""
        content_lower = content.lower()
        for section in self.SECTION_TYPES:
            if section in content_lower:
                return section
        return '其他章节'

    def filter_documents_by_category(self, category: str) -> List[Document]:
        """按文件分类过滤（如技术方案/商务报价）"""
        return [doc for doc in self.documents if doc.metadata.get('category') == category]
    
    def filter_chunks_by_section(self, section_type: str) -> List[Document]:
        """按章节类型过滤子块（如报价明细/技术参数）"""
        return [chunk for chunk in self.chunks if chunk.metadata.get('section_type') == section_type]

    def get_statistics(self) -> Dict[str, Any]:
        """获取投标文件统计信息"""
        if not self.documents:
            return {}

        categories = {}
        section_types = {}

        for doc in self.documents:
            category = doc.metadata.get('category', '未知')
            categories[category] = categories.get(category, 0) + 1

        for chunk in self.chunks:
            section = chunk.metadata.get('section_type', '未知')
            section_types[section] = section_types.get(section, 0) + 1

        return {
            'total_documents': len(self.documents),
            'total_chunks': len(self.chunks),
            'categories': categories,
            'section_types': section_types,
            'avg_chunk_size': sum(chunk.metadata.get('chunk_size', 0) for chunk in self.chunks) / len(self.chunks) if self.chunks else 0
        }
    
    def export_metadata(self, output_path: str):
        """导出投标文件元数据到JSON"""
        import json
        
        metadata_list = []
        for doc in self.documents:
            metadata_list.append({
                'source': doc.metadata.get('source'),
                'project_name': doc.metadata.get('project_name'),
                'category': doc.metadata.get('category'),
                'version': doc.metadata.get('version'),
                'created_time': doc.metadata.get('created_time'),
                'content_length': len(doc.page_content)
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, ensure_ascii=False, indent=2)
        
        logger.info(f"投标文件元数据已导出到: {output_path}")

    def get_parent_documents(self, child_chunks: List[Document]) -> List[Document]:
        """根据检索到的子块获取完整投标文件（去重并按相关性排序）"""
        parent_relevance = {}
        parent_docs_map = {}

        for chunk in child_chunks:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id:
                parent_relevance[parent_id] = parent_relevance.get(parent_id, 0) + 1
                if parent_id not in parent_docs_map:
                    for doc in self.documents:
                        if doc.metadata.get("parent_id") == parent_id:
                            parent_docs_map[parent_id] = doc
                            break

        # 按匹配次数排序（相关度高的在前）
        sorted_parent_ids = sorted(parent_relevance.keys(),
                                 key=lambda x: parent_relevance[x],
                                 reverse=True)

        parent_docs = [parent_docs_map[pid] for pid in sorted_parent_ids if pid in parent_docs_map]
        logger.info(f"从 {len(child_chunks)} 个子块中找到 {len(parent_docs)} 个关联投标文件")
        return parent_docs