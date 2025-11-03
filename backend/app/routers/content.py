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
            {"role": "user", "content": f"项目概述：{request.project_overview}\n\n目录大纲：{request.outline}\n\n请以投标单位的角度，逐条生成内容。"}
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


@router.post("/generate-chapter-stream")
async def generate_chapter_content_stream(request: ChapterContentRequest, use_qwen: bool = True, stream = True):
    """流式为单个章节生成内容"""
    try:
        model_service = get_model_service(use_qwen)

        messages = [
            {"role": "system", "content": "你是一名专业的内容生成助手，负责撰写章节。"},
            {"role": "user", "content": f"项目概述：{request.project_overview}\n\n父章节：{request.parent_chapters}\n兄弟章节：{request.sibling_chapters}\n当前章节：{request.chapter}\n\n请生成本章节内容。"}
        ]

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
        raise HTTPException(status_code=500, detail=f"章节内容生成失败: {str(e)}")

@router.post("/generate-chapter-hierarchical")
async def generate_chapter_content_stream(request: ChapterContentRequest, use_qwen: bool = True, stream=True):
    """
    流式生成单个章节内容 + 自动摘要 + 章节记忆缓存
    """
    try:
        model_service = get_model_service(use_qwen)
        project_id = request.project_id or "default_project"
        memory = ChapterMemoryManager(project_id)

        # === 加载历史上下文记忆 ===
        parent_summary = memory.get_chapter_summary(request.parent_id) if request.parent_id else ""
        sibling_summaries = memory.get_sibling_summaries(request.parent_id, request.chapter["id"])

        # === 构建 Prompt ===
        messages = [
            {"role": "system", "content": "你是一名专业的章节写作助手，请根据上下文连贯撰写内容。"},
            {"role": "user", "content": f"""
项目概述：{request.project_overview}

父章节摘要：
{parent_summary or "无"}

兄弟章节摘要：
{sibling_summaries or "无"}

当前章节标题：{request.chapter['title']}
章节描述：{request.chapter['description']}

请生成本章节完整内容，语言连贯，风格统一。
"""}
        ]

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

                    # === 生成章节摘要 ===
                    summary_prompt = [
                        {"role": "system", "content": "请为以下章节生成简洁摘要（约200字）："},
                        {"role": "user", "content": full_content}
                    ]
                    summary = await model_service.chat_completion(summary_prompt)

                    # === 保存章节记忆 ===
                    memory.save_chapter(
                        request.chapter["id"],
                        request.chapter["title"],
                        full_content,
                        summary
                    )

                    yield f"data: {json.dumps({'status': 'completed', 'content': full_content, 'summary': summary}, ensure_ascii=False)}\n\n"
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

        # 非流式模式
        else:
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if not clean.strip():
                    continue
                full_content += clean

            # === 自动摘要与存储 ===
            summary_prompt = [
                {"role": "system", "content": "请为以下章节生成简洁摘要（约200字）："},
                {"role": "user", "content": full_content}
            ]
            summary = await model_service.chat_completion(summary_prompt)

            memory.save_chapter(request.chapter["id"], request.chapter["title"], full_content, summary)

            return JSONResponse(
                content={
                    "status": "completed",
                    "message": "章节生成完成",
                    "content": full_content,
                    "summary": summary
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"章节内容生成失败: {str(e)}")