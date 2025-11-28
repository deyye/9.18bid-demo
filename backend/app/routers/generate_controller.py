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
    采用 Server-Sent Events (SSE) 流式返回，前端需通过流式读取。
    """
    project_overview = request.project_overview
    outline_root = request.outline
    
    if not outline_root:
        raise HTTPException(status_code=400, detail="缺少项目目录结构 outline")

    # 1. 扁平化所有待生成章节的任务
    #    (为了并行，我们牺牲了"章节摘要传递给下一章"的特性，但保留了上下文结构信息)
    tasks_data = []

    def collect_tasks(chapter, parent_stack, sibling_list):
        # 收集当前章节任务
        tasks_data.append({
            "chapter": chapter,
            "parent_chapters": parent_stack,
            "sibling_chapters": sibling_list
        })
        
        # 递归收集子章节
        children = chapter.get("children", [])
        if children:
            for i, child in enumerate(children):
                # 子章节的兄弟是当前子节点列表中的其他节点
                child_siblings = [c for j, c in enumerate(children) if j != i]
                collect_tasks(child, parent_stack + [chapter], child_siblings)

    # 从根节点开始收集（根节点通常是虚节点或总纲，视具体情况而定，这里假设传入的是单个根对象）
    # 如果 request.outline 是列表，请相应调整
    collect_tasks(outline_root, [], [])

    # 2. 定义并发限制 (Semaphore)
    #    本地模型建议设置为 2-4，API模型可设置为 5-10
    MAX_CONCURRENCY = 4 
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def generate_single_chapter_task(task_info):
        """单个章节的生成协程"""
        async with semaphore:
            chapter = task_info["chapter"]
            chapter_id = chapter.get("id")
            title = chapter.get("title")
            
            try:
                request_data = ChapterContentRequest(
                    project_overview=project_overview,
                    parent_chapters=task_info["parent_chapters"],
                    sibling_chapters=task_info["sibling_chapters"],
                    chapter=chapter
                )
                
                # 调用生成服务 (stream=False 表示内部不流式，等生成完一次性拿结果)
                # 注意：这里是等待“当前章节”完全生成好
                response = await generate_chapter_content_stream(request_data, use_qwen=use_qwen, stream=False)
                
                # 解析响应
                content_json = response.body.decode("utf-8") if hasattr(response, "body") else response
                if isinstance(content_json, str):
                    content_data = json.loads(content_json)
                else:
                    content_data = content_json
                
                content = content_data.get("content", "")
                
                # 返回成功结果
                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "title": title,
                    "content": content
                }
            except Exception as e:
                logger.error(f"章节 {chapter_id} 生成失败: {e}")
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "error": str(e)
                }

    # 3. 流式生成器
    async def event_generator():
        # 创建所有异步任务
        pending_tasks = [asyncio.create_task(generate_single_chapter_task(t)) for t in tasks_data]
        
        total_tasks = len(pending_tasks)
        completed_count = 0

        # 使用 as_completed 获取最先完成的任务
        for coro in asyncio.as_completed(pending_tasks):
            result = await coro
            completed_count += 1
            
            # 构造 SSE 数据包
            # 格式: data: {...json...}\n\n
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

        # 发送结束信号
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )