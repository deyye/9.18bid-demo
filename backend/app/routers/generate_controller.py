import json
import asyncio
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from ..models.schemas import ChapterContentRequest, ContentGenerationRequest
from .content import generate_chapter_content_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content")

# ==========================================
# 辅助函数
# ==========================================

def collect_all_chapters(outline_roots: List[Dict]) -> List[Dict[str, Any]]:
    """
    递归收集所有需要生成的章节任务
    
    Args:
        outline_roots: 根节点列表
    
    Returns:
        任务数据列表，每个任务包含 chapter, parent_chapters, sibling_chapters
    """
    tasks_data = []

    def collect_tasks(chapter: Dict, parent_stack: List[Dict], sibling_list: List[Dict]):
        """递归收集任务"""
        # 收集当前章节任务
        tasks_data.append({
            "chapter": chapter,
            "parent_chapters": parent_stack.copy(),  # 使用copy避免引用问题
            "sibling_chapters": sibling_list.copy()
        })
        
        # 递归处理子章节
        children = chapter.get("children", [])
        if children:
            for i, child in enumerate(children):
                # 该子章节的兄弟节点是其他子章节
                child_siblings = [c for j, c in enumerate(children) if j != i]
                collect_tasks(child, parent_stack + [chapter], child_siblings)

    # 遍历所有根节点
    for i, root in enumerate(outline_roots):
        # 根节点的兄弟是其他根节点
        root_siblings = [r for j, r in enumerate(outline_roots) if j != i]
        collect_tasks(root, [], root_siblings)

    return tasks_data

async def generate_chapter_worker(
    task_info: Dict[str, Any],
    project_overview: str,
    use_qwen: bool,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    工作协程：负责生成单个章节
    
    Args:
        task_info: 任务信息字典
        project_overview: 项目概述
        use_qwen: 是否使用Qwen模型
        semaphore: 并发控制信号量
    
    Returns:
        生成结果字典
    """
    async with semaphore:
        chapter = task_info["chapter"]
        chapter_id = chapter.get("id", "unknown")
        chapter_title = chapter.get("title", "无标题")
        
        logger.info(f"开始生成章节: {chapter_id} - {chapter_title}")
        
        try:
            # 构造请求体
            req = ChapterContentRequest(
                project_overview=project_overview,
                parent_chapters=task_info["parent_chapters"],
                sibling_chapters=task_info["sibling_chapters"],
                chapter=chapter
            )
            
            # 调用单章生成函数 (stream=False 表示内部等待完整结果)
            response = await generate_chapter_content_stream(
                req, 
                use_qwen=use_qwen, 
                stream=False
            )
            
            if response.status_code == 200:
                body = json.loads(response.body)
                logger.info(f"章节生成成功: {chapter_id} - {chapter_title}")
                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "content": body.get("content", ""),
                    "title": chapter_title,
                    "word_count": len(body.get("content", ""))
                }
            else:
                body = json.loads(response.body)
                error_msg = body.get("error", "Unknown error")
                logger.error(f"章节生成失败: {chapter_id} - {error_msg}")
                return {
                    "success": False,
                    "chapter_id": chapter_id,
                    "title": chapter_title,
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"章节生成异常: {chapter_id} - {str(e)}", exc_info=True)
            return {
                "success": False,
                "chapter_id": chapter_id,
                "title": chapter_title,
                "error": str(e)
            }

# ==========================================
# API 端点
# ==========================================

@router.post("/generate-full-project")
async def generate_full_project(
    request: ContentGenerationRequest, 
    use_qwen: bool = True,
    max_concurrency: int = 2
):
    """
    【并发优化版】自动并行生成整本项目文档
    
    Args:
        request: 内容生成请求，包含项目概述和目录结构
        use_qwen: 是否使用Qwen模型 (默认True)
        max_concurrency: 最大并发数 (默认2，可根据服务器性能调整)
    
    Returns:
        SSE流式响应，实时返回各章节生成进度
    """
    project_overview = request.project_overview
    outline_roots = request.outline
    
    # 输入验证
    if not outline_roots:
        raise HTTPException(
            status_code=400, 
            detail="缺少项目目录结构 outline"
        )
    
    if not project_overview:
        raise HTTPException(
            status_code=400,
            detail="缺少项目概述 project_overview"
        )

    # 1. 任务扁平化：递归收集所有需要生成的章节
    try:
        tasks_data = collect_all_chapters(outline_roots)
    except Exception as e:
        logger.error(f"收集章节任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"解析目录结构失败: {str(e)}"
        )

    logger.info(f"项目文档生成任务启动:")
    logger.info(f"  - 总章节数: {len(tasks_data)}")
    logger.info(f"  - 并发数: {max_concurrency}")
    logger.info(f"  - 使用模型: {'Qwen' if use_qwen else 'OpenAI'}")

    # 2. 并发限制配置
    semaphore = asyncio.Semaphore(max_concurrency)

    # 3. SSE 流式主逻辑
    async def event_generator():
        """事件生成器：管理并发任务并实时推送结果"""
        try:
            # 发送开始事件
            start_data = {
                'status': 'started',
                'total_chapters': len(tasks_data),
                'max_concurrency': max_concurrency
            }
            yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"

            # 创建所有任务
            tasks = [
                asyncio.create_task(
                    generate_chapter_worker(
                        task_info=t,
                        project_overview=project_overview,
                        use_qwen=use_qwen,
                        semaphore=semaphore
                    )
                )
                for t in tasks_data
            ]
            
            # 实时返回完成的任务
            completed_count = 0
            failed_count = 0
            
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    completed_count += 1
                    
                    if not result.get("success"):
                        failed_count += 1
                    
                    # 添加进度信息
                    result["progress"] = {
                        "completed": completed_count,
                        "total": len(tasks_data),
                        "failed": failed_count,
                        "percentage": round(completed_count / len(tasks_data) * 100, 2)
                    }
                    
                    yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"任务完成时发生异常: {str(e)}", exc_info=True)
                    failed_count += 1
                    error_data = {
                        'success': False,
                        'error': f'任务异常: {str(e)}',
                        'progress': {
                            'completed': completed_count,
                            'total': len(tasks_data),
                            'failed': failed_count
                        }
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

            # 发送完成总结
            summary_data = {
                'status': 'all_completed',
                'total': len(tasks_data),
                'successful': completed_count - failed_count,
                'failed': failed_count,
                'success_rate': round((completed_count - failed_count) / len(tasks_data) * 100, 2)
            }
            yield f"data: {json.dumps(summary_data, ensure_ascii=False)}\n\n"

            # 标准SSE结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"事件生成器异常: {str(e)}", exc_info=True)
            error_data = {
                'status': 'error',
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            "Access-Control-Allow-Origin": "*"  # CORS支持
        }
    )


@router.post("/generate-single-chapter")
async def generate_single_chapter(
    request: ChapterContentRequest,
    use_qwen: bool = True
):
    """
    【单章节生成】生成单个章节内容（适用于编辑/重新生成场景）
    
    Args:
        request: 章节内容生成请求
        use_qwen: 是否使用Qwen模型
    
    Returns:
        StreamingResponse: SSE流式响应
    """
    try:
        logger.info(f"单章节生成请求: {request.chapter.get('id')} - {request.chapter.get('title')}")
        
        # 直接调用核心生成函数
        return await generate_chapter_content_stream(
            request=request,
            use_qwen=use_qwen,
            stream=True
        )
        
    except Exception as e:
        logger.error(f"单章节生成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"章节生成失败: {str(e)}"
        )


@router.get("/generation-stats")
async def get_generation_stats():
    """
    【统计信息】获取生成任务统计（可扩展为实际的任务监控）
    
    Returns:
        当前系统状态和统计信息
    """
    # TODO: 可以接入Redis或数据库记录实际的生成历史
    return {
        "status": "ready",
        "max_concurrency": 2,
        "supported_models": ["qwen", "openai"],
        "features": [
            "RAG增强检索",
            "招投标专业模板",
            "并发批量生成",
            "流式实时输出"
        ]
    }