from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schemas import OutlineRequest, OutlineResponse
from ..services.openai_service import OpenAIService
from ..services.qwen_api import QwenService
from ..utils.config_manager import config_manager
import json
import re
from typing import AsyncGenerator, Dict, Any, List

router = APIRouter(prefix="/api/outline", tags=["目录管理"]) 

# ------------------------------
# 公共：提示词构造
# ------------------------------
OUTLINE_JSON_SCHEMA = r"""
{
  "outline": [
    {
      "id": "1",
      "title": "",
      "description": "",
      "children": [
        {
          "id": "1.1",
          "title": "",
          "description": "",
          "children": [
            {
              "id": "1.1.1",
              "title": "",
              "description": "",
              "children": [
                {
                "id": "1.1.1.1",
                "title": "",
                "description": "",
                "children": [
                    {
                    "id": "1.1.1.1.1",
                    "title": "",
                    "description": ""
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
"""

SYSTEM_PROMPT = f"""
你是一名资深的标书编写与评标专家，熟悉政府、企业及信息化项目的技术标结构规范。
请根据**项目概述**与**技术评分要求**，自动生成“技术标部分”的章节目录结构。

---

### 🎯 任务目标
生成一个层次清晰、逻辑严谨、覆盖完整的“技术标章节目录”，
能准确反映评分要点与项目特征，体现专业性、系统性与创新性。

---

### 📘 结构与逻辑要求

1. **自适应层级深度**
   - 根据项目复杂度与评分要求自动调整目录层级（通常为 **2~5级**）：
     - 若项目规模较小、评分项较少：建议生成 **2级目录**；
     - 若项目中等复杂、评分细则较详细：建议生成 **3级目录**；
     - 若项目庞大、评分项繁多或包含多个系统模块：可生成 **4级目录**或**5级目录**；
   - 章节层次需清晰，避免过深嵌套或过度平铺。

2. **章节逻辑结构**
   - 一级目录应与技术评分要求的主要章节或评分维度对应；
   - 二级、三级及更深层目录用于细化评分点、子模块或关键实施要点；
   - 同级章节应保持逻辑一致与结构对称；
   - 若评分标准中未明确列出但属于通用内容（如项目管理、质量保障、安全措施、售后服务等），应自动补充。

3. **内容比例与章节平衡**
   - 各章节应依据项目重点合理分布篇幅与数量：
     - “总体方案”“技术实现”“系统架构”等章节可展开较多子目录；
     - “项目管理”“实施进度”“服务保障”等章节相对简洁；
   - 每个章节的 **description** 应提供简要说明（建议 30~60 字），概括章节核心内容或目标；
   - 禁止生成空描述。

4. **章节宽度自适应与内容比例控制**
   - 每个章节的子目录数量（宽度）应根据内容复杂度与评分细则数量自动调整；
   - 目录宽度不宜固定，应体现结构差异：
     - 高层级章节（如“总体方案”“系统设计”）通常包含 **3~6 个**子目录；
     - 中层章节（如“安全体系”“接口设计”）通常包含 **2~4 个**子目录；
     - 末层章节（如“部署步骤”“维护策略”）通常包含 **1~3 个**子目录；
   - 若评分细则中某一维度权重较高，应增加相应子章节以充分覆盖；
   - 同级章节的子目录数量可不同，以反映重点；
   - 避免所有章节出现固定数量子目录（如全部 2 个），需体现结构差异化与项目特点；
   - 总体结构需保持均衡与层次清晰，符合真实投标文件逻辑。

5. **启发式生成逻辑**
   - 模型应根据输入的项目概述与评分内容，先判断每个一级章节的重要性与复杂度：
     - 若该章节内容广泛或权重高，应展开更多子目录；
     - 若该章节内容集中或权重低，可简化层级；
   - 章节间结构可不对称，但需体现专业逻辑；
   - 输出目录需能支撑后续详细内容撰写。

---

### 🧩 输出格式要求
- 仅输出标准 **JSON**；
- 严格遵守以下字段结构：
  - `id`: 章节编号（如 "1"、"1.2"、"1.2.3"、"1.2.3.4"、"1.2.3.4.5"）；
  - `title`: 章节标题；
  - `description`: 章节概要；
  - `children`: 子章节列表（如无则省略或为空数组）；
- 禁止输出任何与 JSON 无关的文字（包括解释、注释、代码块标记等）。

---

### 🧱 输出模板（字段名必须一致）
{OUTLINE_JSON_SCHEMA}
"""


def build_messages(overview: str, requirements: str) -> List[Dict[str, str]]:
    user_prompt = f"""请基于以下项目信息生成标书目录结构，并**仅以JSON对象**形式输出：
    项目概述：
        {overview}
    技术评分要求：
        {requirements}
    请生成完整的技术标目录结构，确保覆盖所有技术评分要点。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

# ------------------------------
# 公共：服务选择
# ------------------------------

def get_model_service(use_qwen: bool):
    if use_qwen:
        # 本地Qwen服务（例如vLLM/LMDeploy网关），按需调整base_url
        return QwenService(base_url="http://localhost:10086")
    # OpenAI / 兼容OpenAI的服务
    config = config_manager.load_config()
    if not config.get('api_key'):
        raise HTTPException(status_code=400, detail="请先配置OpenAI API密钥")
    return OpenAIService(
        api_key=config['api_key'],
        base_url=config.get('base_url', ''),
        model_name=config.get('model_name', 'gpt-3.5-turbo')
    )


# ------------------------------
# 公共：JSON清洗与解析
# ------------------------------

def _extract_json(text: str) -> Dict[str, Any]:
    """尽量稳健地从模型输出中提取JSON对象。自动去除<think>内容。"""
    if not text:
        raise ValueError("模型未返回内容")

    # 清理掉<think>...</think> ----
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)

    # 移除代码围栏
    text = re.sub(r"^```[a-zA-Z]*|```$", "", text.strip())

    # 找到第一个以'{'开头到最后一个'}'的片段
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("未找到有效JSON片段")

    obj = json.loads(m.group(0))
    if not isinstance(obj, dict) or 'outline' not in obj:
        raise ValueError("JSON结构缺少'outline'字段")

    return obj


# ------------------------------
# 非流式：直接返回JSON
# ------------------------------
@router.post("/generate", response_model=OutlineResponse)
async def generate_outline(request: OutlineRequest, use_qwen: bool = True):
    """生成标书目录结构（非流式，自动去除<think>内容）。"""
    try:
        model_service = get_model_service(use_qwen)
        messages = build_messages(request.overview, request.requirements)

        # 对OpenAI可尝试开启结构化输出，Qwen不一定支持；若服务端不支持会被忽略
        extra_kwargs = {"temperature": 0.3}
        try:
            extra_kwargs["response_format"] = {"type": "json_object"}
        except Exception:
            pass

        result_text = await model_service.chat_completion(messages, **extra_kwargs)

        # 清理掉<think>...</think> ----
        cleaned_text = re.sub(r"<think>[\s\S]*?</think>", "", result_text)

        data = _extract_json(cleaned_text)
        return OutlineResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"目录生成失败: {str(e)}")


# ------------------------------
# 流式：SSE增量输出 + 最终JSON
# ------------------------------
@router.post("/generate-stream")
async def generate_outline_stream(request: OutlineRequest, use_qwen: bool = True, stream: bool = True):
    """
    生成标书目录结构。
    - 当 stream=True 时，使用流式输出（SSE），前端以 EventSource / fetch+ReadableStream 接收；
    - 当 stream=False 时，非流式输出，一次性返回完整 JSON。
    """
    try:
        model_service = get_model_service(use_qwen)
        messages = build_messages(request.overview, request.requirements)

        if stream:
            async def event_gen():
                result_text = ""  # 收集完整输出

                async for chunk in model_service.chat_completion_stream(messages, temperature=0.3):
                    # 过滤 think 标签内容
                    clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                    if not clean.strip():
                        continue

                    result_text += clean
                    # 实时推送给前端
                    yield f"data: {json.dumps({'chunk': clean}, ensure_ascii=False)}\n\n"

                # 流式完成后解析完整 JSON
                try:
                    data = _extract_json(result_text)
                    yield f"data: {json.dumps({'final': data}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'raw': result_text}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                event_gen(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # ========== 非流式输出分支 ==========
        else:
            # 一次性调用模型，直接返回最终结果
            completion = await model_service.chat_completion(messages, temperature=0.3)
            clean_text = re.sub(r"<think>[\s\S]*?</think>", "", completion).strip()

            try:
                data = _extract_json(clean_text)
                return JSONResponse(content={"result": data})
            except Exception as e:
                # 如果解析失败，返回原始文本与错误信息
                return JSONResponse(
                    content={
                        "error": f"解析失败: {str(e)}",
                        "raw": clean_text
                    },
                    status_code=500
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"目录生成失败: {str(e)}")