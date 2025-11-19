import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ..models.schemas import ChapterContentRequest, ContentGenerationRequest
from .content import generate_chapter_content_stream, get_model_service
import asyncio
import logging

logger = logging.getLogger(__file__)

router = APIRouter(prefix="/api/content")

@router.post("/generate-full-project")
async def generate_full_project(request: ContentGenerationRequest, use_qwen: bool = True, stream: bool = True):
    """
    自动递归生成整本项目文档
    请求示例：
    {
        "project_overview": "xxx",
        "outline": {
            "id": "1",
            "title": "项目总体",
            "description": "说明项目概况",
            "children": [...]
        }
    }
    """
    try:
        project_overview = request.project_overview
        outline = request.outline
        if not outline:
            raise HTTPException(status_code=400, detail="缺少项目目录结构 outline")

        # 存放生成结果与摘要
        generated_content = {}
        chapter_summaries = {}

        async def process_chapter(chapter, parent_stack, sibling_list):
            """
            递归处理单章节（含其子章节）
            """
            chapter_id = chapter.get("id")
            title = chapter.get("title")
            description = chapter.get("description", "")
            children = chapter.get("children", [])

            # === 构造请求 ===
            request_data = ChapterContentRequest(
                project_overview=project_overview,
                parent_chapters=parent_stack,
                sibling_chapters=sibling_list,
                chapter=chapter
            )
            logger.info(f"当前章节请求信息 {request_data}")

            # === 调用章节生成 ===
            response = await generate_chapter_content_stream(request_data, use_qwen=True, stream=False)
            content_json = response.body.decode("utf-8") if hasattr(response, "body") else response
            content_data = json.loads(content_json) if isinstance(content_json, str) else content_json
            content = content_data.get("content", "")

            # === 保存章节内容 ===
            generated_content[chapter_id] = {
                "title": title,
                "description": description,
                "content": content
            }

            # === 生成简短摘要记忆（传递给后续章节） ===
            summary_prompt = f"请总结以下章节的关键要点（不超过100字）：\n{content}"
            summary_messages = [
                {"role": "system", "content": "你是一名内容摘要助手。"},
                {"role": "user", "content": summary_prompt}
            ]
            summary_service = get_model_service(True)
            summary_text = ""
            async for chunk in summary_service.chat_completion_stream(summary_messages, temperature=0.3):
                summary_text += chunk
            chapter_summaries[chapter_id] = summary_text.strip()

            # === 递归子章节 ===
            if children:
                for i, child in enumerate(children):
                    siblings = [c for j, c in enumerate(children) if j != i]
                    await process_chapter(
                        child,
                        parent_stack + [chapter],
                        siblings
                    )

        # === 启动根章节生成 ===
        await process_chapter(outline, parent_stack=[], sibling_list=[])

        return JSONResponse(content={
            "status": "completed",
            "message": "全项目章节生成完成",
            # "project_overview": project_overview,
            "contents": generated_content,
            "summaries": chapter_summaries
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成整本项目文档失败: {str(e)}")
