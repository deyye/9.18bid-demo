from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schemas import ContentGenerationRequest, ChapterContentRequest
from ..services.openai_service import OpenAIService
from ..services.qwen_api import QwenService
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
    【核心生成函数】为单个章节生成内容
    - 优化：流式传输时不处理正则，生成完毕后统一清洗
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

        # 3. 动态构建 Prompt
        length_instruction = ""
        if target_word_count >= 2000:
            length_instruction = f"""
            【⭐⭐⭐ 篇幅要求：极详 (Very Long)】
            - 目标字数：**{target_word_count}字以上**。
            - 策略：必须深度扩写！请增加具体实施步骤、技术参数表、引用标准、风险分析等细节。
            - 严禁简略，每一条论点都需要充分展开。
            """
        elif target_word_count <= 500:
            length_instruction = f"""
            【⭐ 篇幅要求：精简 (Concise)】
            - 目标字数：**{target_word_count}字左右**。
            - 策略：语言精练，直击要点，不要废话。
            """
        else:
            length_instruction = f"""
            【⭐⭐ 篇幅要求：适中 (Standard)】
            - 目标字数：**{target_word_count}字左右**。
            - 内容充实，逻辑清晰。
            """

        system_prompt = "你是一名资深的招投标文档撰写专家。请严格根据提供的项目背景、章节定位和字数要求，撰写专业、详实、符合逻辑的标书内容。"

        user_prompt = f"""
### 1. 项目背景
{project_overview[:1200]}...

### 2. 当前章节定位
- **章节编号**：{chapter_id}
- **章节标题**：{title}
- **章节概要**：{desc}
- **上级章节**：{parent_text}
- **兄弟章节**：{sibling_text}

### 3. 核心指令
{length_instruction}

### 4. 格式规范
- 使用标准 Markdown 格式。
- 使用专业、正式的投标语言。
- **不要**输出“好的”、“根据您的要求”等客套话，直接输出正文内容。

请开始撰写：
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # -------------------------------------------------------
        # 定义统一的清洗函数 (Post-Processing)
        # -------------------------------------------------------
        def clean_final_text(text: str) -> str:
            if not text: return ""
            # 1. 去除 <think>...</think> 思维链 (支持跨行)
            text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL)
            
            # 2. 去除开头的客套话 (如 "好的，...", "Sure, ...")
            # 匹配行首的客套话，直到换行符
            text = re.sub(r"^(好的|没问题|当然可以|Here is|Sure|Okay).*?[\n\r]", "", text.strip(), flags=re.IGNORECASE)
            
            return text.strip()

        # 4. 执行生成
        if stream:
            async def generate():
                try:
                    yield f"data: {json.dumps({'status': 'started', 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                    full_content = ""
                    # 适当调高 temperature
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.75):
                        # ✅ 优化：流式阶段不做正则处理，直接累积
                        # 如果需要，可以在这里做简单的字符串检测来决定是否推送给前端(比如暂不推送<think>内容)
                        # 但为了简单和性能，建议前端展示 raw，或者忍受暂时的乱码，最终以 completed 事件为准
                        full_content += chunk
                        
                        # 实时推送 (包含 raw content)
                        yield f"data: {json.dumps({'status': 'streaming', 'content': chunk, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                    # ✅ 优化：生成结束后，进行全量清洗
                    final_clean = clean_final_text(full_content)

                    # 发送完成信号 (包含最终清洗后的完美内容)
                    yield f"data: {json.dumps({'status': 'completed', 'content': final_clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e), 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )

        else:
            # 非流式逻辑（供 Controller 内部调用，用于“一键生成所有”）
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.75):
                # ✅ 优化：同样不做实时清洗，只累积
                full_content += chunk

            # ✅ 优化：全量清洗
            final_clean = clean_final_text(full_content)

            return JSONResponse(
                content={
                    "success": True,
                    "content": final_clean,
                    "chapter_id": chapter_id
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "chapter_id": request.chapter.get("id")}
        )