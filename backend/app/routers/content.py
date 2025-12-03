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
            model_name=config.get("model_name", "qwen3")
        )

# ==========================================
# 专业招投标文档生成提示词模板
# ==========================================

def build_bidding_system_prompt() -> str:
    """构建招投标文档专用系统提示词"""
    return """你是一位资深的招投标文档撰写专家，具备以下核心能力：

**角色定位**：
- 精通政府采购、企业招标的合规要求与评分标准
- 擅长技术方案设计、项目管理、风险控制
- 熟悉ISO标准、CMMI体系、行业最佳实践

**核心原则**：
1. **需求导向**：精准理解并响应招标需求，避免泛泛而谈
2. **结构化表达**：采用清晰的层级结构、表格、图表
3. **可执行性**：所有方案必须可落地、可验证、可追溯
4. **专业术语**：使用行业标准术语，体现专业性
5. **数据支撑**：用具体数据、案例、标准替代空洞承诺

**禁止事项**：
- ❌ 避免"确保100%"等绝对承诺
- ❌ 避免"打造一流"等空洞口号
- ❌ 避免冗长的客套话和过渡语
- ❌ 避免未经验证的技术路线
- ❌ 避免缺乏细节的笼统描述

**输出质量标准**：
- 内容必须与招标需求直接对应
- 方案必须包含可量化的交付物
- 风险必须有具体的应对措施
- 所有承诺必须有依据支撑"""

def build_bidding_user_prompt(
    project_overview: str,
    chapter_id: str,
    title: str,
    desc: str,
    parent_text: str,
    target_word_count: int,
    rag_context: str = ""
) -> str:
    """构建符合招投标规范的用户提示词"""
    
    # 根据字数确定详细程度策略
    if target_word_count >= 2000:
        length_guide = f"""
**篇幅要求**：目标字数 {target_word_count}+ 字（深度详尽型）

**扩写策略**：
- 必须包含多级子标题（至少3层结构）
- 添加详细的技术参数、配置清单、流程步骤
- 使用表格展示资源配置、时间计划、责任矩阵
- 提供具体案例、数据对比、效果验证
- 增加风险矩阵、应急预案、质量检查点"""
    elif target_word_count <= 500:
        length_guide = f"""
**篇幅要求**：目标字数 {target_word_count} 字左右（精简概述型）

**精简策略**：
- 采用要点式呈现，每个要点1-2句话
- 突出核心价值和关键差异点
- 使用简洁的列表或表格
- 省略过程描述，聚焦结果"""
    else:
        length_guide = f"""
**篇幅要求**：目标字数 {target_word_count} 字左右（标准详实型）

**撰写策略**：
- 结构完整：包含背景-方案-保障-成果
- 内容充实：每个要点有具体说明和支撑
- 数据量化：关键指标必须数字化"""

    # 构建RAG上下文提示
    rag_section = ""
    if rag_context:
        rag_section = f"""
### 📚 企业知识库参考资料

**重要**：以下资料来自企业内部知识库，请优先引用其中的：
- 具体参数、配置、标准
- 成功案例、项目数据
- 技术架构、工具清单
- 管理流程、模板文档

{rag_context}

⚠️ 引用时请确保：
1. 数据准确性（直接引用，不要修改参数）
2. 案例相关性（选择与当前章节匹配的案例）
3. 标注来源（如提及"根据公司XXX项目经验"）
"""

    # 主提示词
    return f"""
# 招投标文档撰写任务

## 一、项目背景与招标需求
{project_overview[:1000]}
{"..." if len(project_overview) > 1000 else ""}

## 二、当前章节定位
- **章节编号**：{chapter_id}
- **章节标题**：{title}
- **章节描述**：{desc}
- **上级章节**：{parent_text}

{rag_section}

## 三、撰写要求

{length_guide}

### 必须遵循的输出结构

根据章节性质，选择合适的结构模板：

#### 【方案类章节】结构模板：
```
1. 需求分析与痛点识别
   - 招标需求条款映射（逐条对应）
   - 现状问题与挑战分析
   
2. 解决方案设计
   - 总体架构/流程/方法论
   - 技术路线与工具选型（含版本/参数）
   - 实施步骤与里程碑
   
3. 组织与资源保障
   - 人员配置表（角色-资质-职责）
   - 时间计划甘特图/关键节点
   - 设备/软件/材料清单
   
4. 质量与风险控制
   - 质量标准（KPI/SLA指标）
   - 风险识别矩阵（风险-影响-应对措施）
   - 检查点与评审机制
   
5. 可验证交付成果
   - 交付物清单（名称-格式-验收标准）
   - 成功案例数据（含量化指标）
   - 符合的国家/行业标准
```

#### 【技术类章节】结构模板：
```
1. 技术需求理解
   - 功能性需求清单
   - 非功能性需求（性能/安全/兼容）
   
2. 技术架构设计
   - 系统架构图（层次/模块/接口）
   - 技术栈选型依据
   - 关键技术实现方案
   
3. 性能与安全保障
   - 性能指标承诺（响应时间/并发/容量）
   - 安全防护措施（等保/加密/审计）
   - 容灾备份方案
   
4. 技术验证
   - 测试方案（单元/集成/压力/安全）
   - 参考案例技术指标
   - 符合的技术标准/认证
```

#### 【管理类章节】结构模板：
```
1. 管理目标与依据
   - 管理目标分解
   - 参考标准（PMBOK/CMMI/ISO等）
   
2. 管理体系与流程
   - 组织架构与职责分工
   - 核心管理流程图
   - 管理制度与规范
   
3. 监控与保障措施
   - 监控指标与频率
   - 沟通协调机制
   - 问题升级机制
   
4. 管理工具与表单
   - 管理工具清单
   - 关键表单模板
   - 输出文档规范
```

### 格式规范

**Markdown要求**：
- 使用 ## 到 #### 的标题层级（不要用 #）
- 使用表格展示结构化数据（人员、时间、资源）
- 使用有序/无序列表呈现要点
- 使用代码块展示配置/参数
- 使用引用块标注重要说明

**表格示例格式**：
```markdown
| 阶段 | 关键任务 | 交付物 | 工期 | 责任人 |
|------|---------|--------|------|--------|
| 需求调研 | 现场访谈、流程梳理 | 需求规格说明书 | 5天 | 需求分析师 |
```

**数据呈现要求**：
- 性能指标必须量化（如"响应时间 ≤ 2秒"而非"快速响应"）
- 时间计划必须明确（如"第3-5工作日"而非"初期阶段"）
- 人员配置必须具体（如"2名高级工程师（5年以上经验）"）

### 专业性要求

**术语使用**：
- 技术术语：使用行业标准缩写（如RESTful API、OAuth 2.0、MySQL 8.0）
- 管理术语：使用PMBOK术语（如WBS、关键路径、风险登记册）
- 质量术语：使用ISO/国标术语（如PDCA、6σ、CMMI）

**避免的表述**：
- ❌ "我们将全力以赴" → ✅ "配置3名专职项目成员，每日工作时长不少于8小时"
- ❌ "确保100%成功" → ✅ "参照ISO 9001质量管理体系，设置5个关键检查点"
- ❌ "业界领先" → ✅ "性能指标：并发1000用户，响应时间<2秒，可用性99.9%"

## 四、输出指令

请严格按照上述结构和规范，直接输出该章节的完整内容。

**注意事项**：
1. ✅ 直接输出正文内容，不要有"好的""明白了"等开场白
2. ✅ 章节标题使用 ## {title}
3. ✅ 如果引用了知识库资料，需自然融入文中
4. ✅ 数据、参数、案例必须真实可信
5. ✅ 每个承诺必须有对应的保障措施

现在开始撰写：
"""

def clean_final_text(text: str) -> str:
    """清洗LLM输出文本"""
    if not text:
        return ""
    
    # 移除思考标签
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL)
    
    # 移除常见的开场白（更全面的匹配）
    opening_patterns = [
        r"^(好的|明白了|没问题|当然可以|收到|了解|OK|Sure|Here is|Here's)[\s,，。]*",
        r"^(我将|让我|下面|接下来|现在)[\s,，。]*为您.*?[\n\r]",
        r"^根据.*?要求[\s,，。]*",
    ]
    for pattern in opening_patterns:
        text = re.sub(pattern, "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    
    # 移除结尾的客套话
    closing_patterns = [
        r"(如有.*?问题.*?联系|希望.*?满意|以上.*?供.*?参考)[\s\S]*$",
    ]
    for pattern in closing_patterns:
        text = re.sub(pattern, "", text.strip(), flags=re.IGNORECASE)
    
    return text.strip()

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
    【核心生成函数】为单个章节生成内容 (集成 RAG + 招投标专业提示词)
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
        parent_text = " > ".join([p['title'] for p in parent_chapters]) or "无(顶级章节)"

        # 3. 🔍 RAG 检索增强
        rag_query = f"撰写章节 '{title}' (内容概要: {desc}) 的相关企业资料和历史案例，项目要求：{project_overview[:100]}..."
        rag_service = get_rag_service()
        retrieved_docs = rag_service.search(rag_query, n_results=5) # 检索 top 5 知识片段
        
        rag_context_str = ""
        if retrieved_docs:
            # 格式化检索结果，将其 source 和 content 整合
            rag_context_str = "\n".join([f"- 【来源:{doc.get('source', 'unknown')}】片段: {doc['content']}" for doc in retrieved_docs])
            rag_context_str = f"\n### 💡 参考资料 (企业知识库)\n请优先基于以下企业内部资料撰写，确保参数和案例的准确性：\n{rag_context_str}\n"
        else:
            rag_context_str = "\n### 💡 参考资料 (企业知识库)\n未检索到相关知识片段，请基于项目概述和章节要求进行生成。\n"

        # 3. 动态构建 Prompt (将 RAG 结果注入 Prompt)
        length_instruction = ""
        if target_word_count >= 2000:
            length_instruction = f"【⭐⭐⭐ 篇幅要求：极详】目标字数：{target_word_count}字以上。策略：必须深度扩写！请增加技术细节、流程步骤、数据表格。"
        elif target_word_count <= 500:
            length_instruction = f"【⭐ 篇幅要求：精简】目标字数：{target_word_count}字左右。策略：语言精练，直击要点。"
        else:
            length_instruction = f"【⭐⭐ 篇幅要求：适中】目标字数：{target_word_count}字左右。内容充实，逻辑清晰。"
            
        # 4. 构建专业招投标提示词
        system_prompt = build_bidding_system_prompt()
        user_prompt = build_bidding_user_prompt(
            project_overview=project_overview,
            chapter_id=chapter_id,
            title=title,
            desc=desc,
            parent_text=parent_text,
            target_word_count=length_instruction,
            rag_context=rag_context_str
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 5. 执行生成
        if stream:
            async def generate():
                try:
                    yield f"data: {json.dumps({'status': 'started', 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                    
                    full_content = ""
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                        # 实时清除思考标签
                        clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                        if not clean:
                            continue
                        
                        full_content += clean
                        yield f"data: {json.dumps({'status': 'streaming', 'content': clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                    
                    # 最终清洗
                    final_clean = clean_final_text(full_content)
                    yield f"data: {json.dumps({'status': 'completed', 'content': final_clean, 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e), 'chapter_id': chapter_id}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                generate(), 
                media_type="text/event-stream", 
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式模式
            full_content = ""
            async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                clean = re.sub(r"<think>[\s\S]*?</think>", "", chunk)
                if clean:
                    full_content += clean
            
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
            content={
                "success": False, 
                "error": str(e), 
                "chapter_id": request.chapter.get("id", "unknown")
            }
        )