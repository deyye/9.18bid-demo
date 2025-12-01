from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schemas import ContentGenerationRequest, ChapterContentRequest
from ..services.openai_service import OpenAIService
from ..services.qwen_api import QwenService
from ..services.rag_service import get_rag_service
from ..utils.config_manager import config_manager
import json, re

router = APIRouter(prefix="/api/content", tags=["内容管理"])

def get_model_service(use_qwen: bool = True):
    """根据配置返回模型服务实例"""
    if use_qwen:
        return QwenService(base_url="http://localhost:10086")
    else:
        config = config_manager.load_config()
        if not config.get("api_key"):
            raise HTTPException(status_code=400, detail="请先配置OpenAI API密钥")
        return OpenAIService(
            api_key=config["api_key"],
            base_url=config.get("base_url", ""),
            model_name=config.get("model_name", "gpt-3.5-turbo")
        )

# ==========================================
# 核心生成逻辑
# ==========================================

@router.post("/generate-chapter-stream")
async def generate_chapter_content_stream(
    request: ChapterContentRequest, 
    use_qwen: bool = True, 
    stream: bool = True
):
    """
    【核心生成函数】为单个章节生成内容 (集成 RAG)
    """
    try:
        model_service = get_model_service(use_qwen)

        # 1. 提取基础信息
        project_overview = request.project_overview
        chapter = request.chapter
        chapter_id = chapter.get("id", "unknown")
        title = chapter.get("title", "")
        desc = chapter.get("description", "")
        
        target_word_count = chapter.get("wordCount") or chapter.get("word_count")
        try:
            target_word_count = int(target_word_count)
        except (TypeError, ValueError):
            target_word_count = 1000 

        # 2. 构建上下文文本
        parent_chapters = request.parent_chapters or []
        sibling_chapters = request.sibling_chapters or []
        parent_text = " > ".join([p['title'] for p in parent_chapters]) or "无（顶级章节）"
        sibling_text = ", ".join([s['title'] for s in sibling_chapters[:3]]) or "无"

        # 3. 🔍 RAG 检索增强
        # 构造检索语句：结合章节标题和描述
        query = f"{title} {desc} {project_overview[:50]}"
        
        # 按需获取实例进行搜索
        # 注意：这里可能会有些许延迟（如果是第一次调用），但不会阻塞服务启动
        rag_service = get_rag_service()
        retrieved_docs = rag_service.search(query, n_results=3)
        
        rag_context_str = ""
        if retrieved_docs:
            rag_context_str = "\n".join([f"- {doc}" for doc in retrieved_docs])
            rag_context_str = f"\n### 💡 参考资料 (企业知识库)\n请优先基于以下企业内部资料撰写，确保参数和案例的准确性：\n{rag_context_str}\n"

        # 4. 动态构建 Prompt
        length_instruction = ""
        if target_word_count >= 2000:
            length_instruction = f"【⭐⭐⭐ 篇幅要求：极详】目标字数：{target_word_count}字以上。策略：必须深度扩写！请增加技术细节、流程步骤、数据表格。"
        elif target_word_count <= 500:
            length_instruction = f"【⭐ 篇幅要求：精简】目标字数：{target_word_count}字左右。策略：语言精练，直击要点。"
        else:
            length_instruction = f"【⭐⭐ 篇幅要求：适中】目标字数：{target_word_count}字左右。内容充实，逻辑清晰。"

        system_prompt = "你是一名资深的招投标文档撰写专家。请严格根据提供的项目背景、参考资料和章节要求，撰写专业、详实、符合逻辑的标书内容。"

        user_prompt = f"""
### 1. 项目背景
{project_overview[:800]}...

### 2. 当前章节定位
- **章节编号**：{chapter_id}
- **章节标题**：{title}
- **章节概要**：{desc}
- **上级章节**：{parent_text}

{rag_context_str}

### 4. 撰写指令
{length_instruction}

### 5. 格式规范
- 使用标准 Markdown 格式。
- **直接输出内容**，不要包含“好的”等客套话。
- 如果参考资料中有具体参数或案例，请直接引用。

请开始撰写：
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 5. 清洗函数
        def clean_final_text(text: str) -> str:
            if not text: return ""
            text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL)
            text = re.sub(r"^(好的|没问题|当然可以|Here is|Sure).*?[\n\r]", "", text.strip(), flags=re.IGNORECASE)
            return text.strip()

        # 6. 执行生成
        if stream:
            async def generate():
                try:
                    yield f"data: {json.dumps({'status': 'started', 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                    full_content = ""
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.75):
                        clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                        if not clean: continue
                        full_content += clean
                        yield f"data: {json.dumps({'status': 'streaming', 'content': clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                    
                    final_clean = clean_final_text(full_content)
                    yield f"data: {json.dumps({'status': 'completed', 'content': final_clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e), 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
        else:
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.75):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if clean: full_content += clean
            final_clean = clean_final_text(full_content)
            return JSONResponse(content={"success": True, "content": final_clean, "chapter_id": chapter_id})

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e), "chapter_id": request.chapter.get("id")})