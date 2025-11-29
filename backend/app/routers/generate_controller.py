# backend/app/routers/generate_controller.py

import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..models.schemas import ChapterContentRequest, ContentGenerationRequest
from .content import generate_chapter_content_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content")

@router.post("/generate-full-project")
async def generate_full_project(request: ContentGenerationRequest, use_qwen: bool = True):
    """
    【并发优化版】自动并行生成整本项目文档
    """
    project_overview = request.project_overview
    outline_roots = request.outline # 现在这是一个列表
    
    if not outline_roots:
        raise HTTPException(status_code=400, detail="缺少项目目录结构 outline")

    # 1. 任务扁平化：递归收集所有需要生成的章节
    tasks_data = []

    def collect_tasks(chapter, parent_stack, sibling_list):
        # 收集当前章节任务
        tasks_data.append({
            "chapter": chapter,
            "parent_chapters": parent_stack,
            "sibling_chapters": sibling_list
        })
        
        children = chapter.get("children", [])
        if children:
            for i, child in enumerate(children):
                child_siblings = [c for j, c in enumerate(children) if j != i]
                collect_tasks(child, parent_stack + [chapter], child_siblings)

    # ✅ 修正：遍历根节点列表
    for i, root in enumerate(outline_roots):
        # 根节点的兄弟是其他根节点
        root_siblings = [r for j, r in enumerate(outline_roots) if j != i]
        collect_tasks(root, [], root_siblings)

    logger.info(f"共收集到 {len(tasks_data)} 个章节生成任务")

    # 2. 并发限制配置
    MAX_CONCURRENCY = 4
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def worker(task_info):
        """工作协程：负责生成单个章节"""
        async with semaphore:
            chapter = task_info["chapter"]
            chapter_id = chapter.get("id")
            
            try:
                # 构造请求体
                req = ChapterContentRequest(
                    project_overview=project_overview,
                    parent_chapters=task_info["parent_chapters"],
                    sibling_chapters=task_info["sibling_chapters"],
                    chapter=chapter
                )
                
                # 调用单章生成函数 (stream=False 表示内部等待完整结果)
                response = await generate_chapter_content_stream(req, use_qwen=use_qwen, stream=False)
                
                if response.status_code == 200:
                    body = json.loads(response.body)
                    return {
                        "success": True,
                        "chapter_id": chapter_id,
                        "content": body.get("content", ""),
                        "title": chapter.get("title")
                    }
                else:
                    body = json.loads(response.body)
                    return {
                        "success": False,
                        "chapter_id": chapter_id,
                        "error": body.get("error", "Unknown error")
                    }
            except Exception as e:
                logger.error(f"Worker exception for {chapter_id}: {e}")
                return {"success": False, "chapter_id": chapter_id, "error": str(e)}

    # 3. SSE 流式主逻辑
    async def event_generator():
        tasks = [asyncio.create_task(worker(t)) for t in tasks_data]
        
        # 实时返回完成的任务
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )