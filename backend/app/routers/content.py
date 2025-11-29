from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schemas import ContentGenerationRequest, ChapterContentRequest
from ..services.openai_service import OpenAIService
from ..services.qwen_api import QwenService
from ..utils.config_manager import config_manager
from ..services.memory_manager import ChapterMemoryManager
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


@router.post("/generate")
async def generate_content(request: ContentGenerationRequest, use_qwen: bool = True):
    """为目录结构生成内容（非流式）"""
    try:
        model_service = get_model_service(use_qwen)
        messages = [
            {"role": "system", "content": "你是一名专业的内容生成助手，负责根据大纲生成项目文档。"},
            {"role": "user", "content": f"项目概述：{request.project_overview}\n\n目录大纲：{request.outline}\n\n请逐条生成内容。"}
        ]
        result = await model_service.chat_completion(messages, temperature=0.7)
        clean = re.sub(r"<think>[\s\S]*?</think>", "", result).strip()
        return {"success": True, "result": clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内容生成失败: {str(e)}")


@router.post("/generate-stream")
async def generate_content_stream(request: ContentGenerationRequest, use_qwen: bool = True, stream: bool = True):
    """流式为目录结构生成内容"""
    try:
        model_service = get_model_service(use_qwen)

        messages = [
            {"role": "system", "content": "你是一名专业的内容生成助手，负责根据大纲生成项目文档。"},
            {"role": "user", "content": f"项目概述：{request.project_overview}\n\n目录大纲：{request.outline}\n\n请以投标单位的角度，逐条生成内容。章节内容不少于30000字。"}
        ]

        if stream:
            async def generate():
                try:
                    yield f"data: {json.dumps({'status': 'started', 'message': '开始生成内容...'}, ensure_ascii=False)}\n\n"

                    full_content = ""
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                        clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                        if not clean.strip():
                            continue
                        full_content += clean
                        yield f"data: {json.dumps({'status': 'streaming', 'content': clean, 'full_content': full_content}, ensure_ascii=False)}\n\n"

                    yield f"data: {json.dumps({'status': 'completed', 'content': full_content}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

                # yield "data: [DONE]\n\n"

            return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        else:
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if not clean.strip():
                    continue
                full_content += clean

            return JSONResponse(
                content={
                    "status": "completed",
                    "message": "生成完成",
                    "content": full_content
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内容生成失败: {str(e)}")

# ✅ 核心优化：单章节生成（支持上下文 + 字数控制）
@router.post("/generate-chapter-stream")
async def generate_chapter_content_stream(request: ChapterContentRequest, use_qwen: bool = True, stream: bool = True):
    """
    流式为单个章节生成内容（供 Controller 内部调用或前端单独调用）
    """
    try:
        model_service = get_model_service(use_qwen)

        # === 1. 数据提取 ===
        project_overview = request.project_overview
        chapter = request.chapter
        chapter_id = chapter.get("id", "unknown")
        title = chapter.get("title", "")
        desc = chapter.get("description", "")
        
        # ✅ 获取字数要求
        target_word_count = chapter.get("word_count", 0) or 1000  # 默认1000字
        
        parent_chapters = request.parent_chapters or []
        sibling_chapters = request.sibling_chapters or []

        # === 2. 上下文构建 ===
        parent_text = " > ".join([p['title'] for p in parent_chapters]) or "无（顶级章节）"
        # 仅提供前两个兄弟章节作为参考，避免上下文过长
        sibling_text = ", ".join([s['title'] for s in sibling_chapters[:3]]) or "无"

        # === 3. 提示词工程 (Prompt Engineering) ===
        system_prompt = "你是一名资深的招投标文档撰写专家。请根据提供的项目背景和章节要求，撰写专业、详实、符合逻辑的标书内容。"
        
        # 根据字数动态调整指令
        length_instruction = ""
        if target_word_count > 2000:
            length_instruction = f"本章节非常重要，请务必详细展开，通过增加技术细节、流程图描述、实施方案步骤等方式，确保内容字数接近 {target_word_count} 字。"
        elif target_word_count < 500:
            length_instruction = f"本章节为概述性内容，请言简意赅，字数控制在 {target_word_count} 字左右。"
        else:
            length_instruction = f"请将内容篇幅控制在 {target_word_count} 字左右。"

        user_prompt = f"""
### 项目背景
{project_overview[:800]}... (略)

### 章节定位
- **当前章节**：{chapter_id} {title}
- **上级章节**：{parent_text}
- **兄弟章节**：{sibling_text}
- **章节概要**：{desc}

### 撰写要求
1. **字数要求**：{length_instruction}
2. **内容风格**：使用专业、正式的投标语言（如“我方承诺”、“本项目将采用...”）。
3. **格式规范**：使用 Markdown 格式，适当使用小标题、列表项。
4. **逻辑连贯**：内容必须紧扣章节标题和概要，不要重复兄弟章节的内容。

请开始撰写：
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # === 4. 生成逻辑 ===
        if stream:
            async def generate():
                try:
                    # 发送开始信号
                    yield f"data: {json.dumps({'status': 'started', 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                    full_content = ""
                    # 温度设为 0.7 以保证生成内容的多样性但又不失控
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                        # 过滤思维链标记
                        clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                        if not clean:
                            continue
                        
                        full_content += clean
                        # 实时推送内容片段
                        yield f"data: {json.dumps({'status': 'streaming', 'content': clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                    # 发送完成信号
                    yield f"data: {json.dumps({'status': 'completed', 'content': full_content, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e), 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )

        else:
            # 非流式逻辑（供 Controller 内部调用）
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if clean:
                    full_content += clean

            return JSONResponse(
                content={
                    "success": True,
                    "content": full_content,
                    "chapter_id": chapter_id
                }
            )

    except Exception as e:
        # 捕获错误并返回 JSON，方便上层处理
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "chapter_id": request.chapter.get("id")}
        )

@router.post("/generate-chapter-hierarchical")
async def generate_chapter_content_stream(request: ChapterContentRequest, use_qwen: bool = True, stream=True):
    """
    流式为单个章节生成内容
    """
    try:
        model_service = get_model_service(use_qwen)

        # === 提取结构化数据 ===
        project_overview = request.project_overview
        chapter = request.chapter
        chapter_id = chapter.get("id", "unknown")
        title = chapter.get("title", "")
        desc = chapter.get("description", "")
        parent_chapters = request.parent_chapters or []
        sibling_chapters = request.sibling_chapters or []

        # === 格式化上下文信息 ===
        parent_text = "\n".join([f"{p['id']} {p['title']}: {p.get('description', '')}" for p in parent_chapters]) or "无"
        sibling_text = "\n".join([f"{s['id']} {s['title']}: {s.get('description', '')}" for s in sibling_chapters]) or "无"

        # === 构建提示语 ===
        messages = [
            {"role": "system", "content": "你是一名专业的招标文档章节生成助手，请根据层级结构和上下文连贯地撰写内容。"},
            {"role": "user", "content": f"""
项目概述：{project_overview}

上级章节：
{parent_text}

同级章节：
{sibling_text}

当前章节：
{chapter_id} {title}
章节说明：{desc}

请撰写本章节完整内容，要求：
1. 与上级章节保持逻辑衔接；
2. 语言正式、内容完整；
3. 不要重复兄弟章节内容；
4. 保持风格一致。
"""}
        ]

        # === 流式输出 ===
        if stream:
            async def generate():
                try:
                    yield f"data: {json.dumps({'status': 'started', 'message': '开始生成章节内容...'}, ensure_ascii=False)}\n\n"

                    full_content = ""
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                        clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                        if not clean.strip():
                            continue
                        full_content += clean
                        yield f"data: {json.dumps({'status': 'streaming', 'content': clean}, ensure_ascii=False)}\n\n"

                    yield f"data: {json.dumps({'status': 'completed', 'content': full_content}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        # === 非流式模式 ===
        else:
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if not clean.strip():
                    continue
                full_content += clean

            return JSONResponse(
                content={
                    "status": "completed",
                    "message": "生成完成",
                    "content": full_content
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"章节内容生成失败: {str(e)}")
