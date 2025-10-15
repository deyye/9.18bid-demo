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
            {"role": "user", "content": f"项目概述：{request.project_overview}\n\n目录大纲：{request.outline}\n\n请逐条生成内容,每个目录不少于300字。"}
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

                yield "data: [DONE]\n\n"

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

                yield "data: [DONE]\n\n"

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
