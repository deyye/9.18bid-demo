from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schemas import ContentGenerationRequest, ChapterContentRequest
from ..services.openai_service import OpenAIService
from ..services.qwen_api import QwenService
from ..services.rag_service import get_rag_service
from ..utils.config_manager import config_manager
import json, re, logging
import os
from ..db_config import get_db
import asyncio
from ..services.table_service import TableService
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
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
    rag_context: str = "",
    db_context: str = ""
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
    context_section = ""
    if db_context or rag_context:
        context_section = "### 📚 企业内部参考资料（动静结合）\n\n"
        
        if db_context:
            context_section += f"**【数据库-历史业绩事实】** (数据绝对准确，请直接引用)：\n{db_context}\n\n"
            
        if rag_context:
            context_section += f"**【知识库-相关文档细节】** (基于历史项目文档检索)：\n{rag_context}\n\n"
            
        context_section += "⚠️ **引用要求**：请将上述历史项目的参数、金额、时间等事实自然融入到方案中，作为公司实力的佐证。\n"

    # 主提示词
    return f"""
# 招投标文档撰写任务

## 一、项目背景与招标需求
{project_overview}

## 二、当前章节定位
- **章节编号**：{chapter_id}
- **章节标题**：{title}
- **章节描述**：{desc}
- **上级章节**：{parent_text}

{context_section}

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

# 🟢 新增：重写专用的 Prompt 构建函数
def build_regeneration_user_prompt(
    project_overview: str,
    chapter_id: str,
    title: str,
    desc: str,
    original_content: str,
    user_instruction: str,
    rag_context: str = ""
) -> str:
    """构建用于重新生成的 Prompt"""
    rag_section = ""
    if rag_context:
        rag_section = f"\n### 💡 企业知识库参考\n{rag_context}\n"

    return f"""
# 章节内容修订任务

## 背景信息
- **项目背景**：{project_overview[:200]}...
- **当前章节**：{chapter_id} {title}
- **章节概要**：{desc}
{rag_section}

## 📝 原有内容 (待修改)
```markdown
{original_content}
```

## ✍️ 修改指令
用户要求：{user_instruction}

## 执行要求
1. 请根据用户的修改指令，对原有内容进行重写或优化
2. 如果用户指令是补充内容，请在原有基础上扩展；如果是修改风格，请重写全文
3. 保持专业标书的严谨性，使用Markdown格式
4. 直接输出修改后的完整内容，不要输出"好的"、"修改如下"等无关文字
5. 确保输出内容完整，不要截断

请开始修改："""


# ==========================================
# 🟢 核心修复：流式过滤器
# ==========================================
@dataclass
class StreamFilter:
    """
    用于过滤流式输出中的 <think> 标签和开场白
    """
    in_think_block: bool = False
    buffer: str = ""
    has_started_output: bool = False
    is_regeneration: bool = False  # 新增：标识是否为重写模式

    def process(self, chunk: str) -> str:
        if not chunk: return ""
        
        # 将新块加入缓冲区
        self.buffer += chunk
        output = ""

        # 1. 处理 <think> 块的开始
        if not self.in_think_block:
            if "<think>" in self.buffer:
                self.in_think_block = True
                # 把 <think> 之前的内容（如果有）拿出来
                parts = self.buffer.split("<think>", 1)
                pre_think = parts[0]
                output += pre_think
                # 缓冲区保留 <think> 之后的部分
                self.buffer = parts[1] if len(parts) > 1 else ""
        
        # 2. 处理 <think> 块的结束
        if self.in_think_block:
            if "</think>" in self.buffer:
                self.in_think_block = False
                # 丢弃 </think> 之前的所有内容（思考过程）
                parts = self.buffer.split("</think>", 1)
                # 保留 </think> 之后的内容
                self.buffer = parts[1] if len(parts) > 1 else ""
            else:
                # 还在思考块中，不输出任何内容
                return output

        # 3. 如果不在思考块中，处理开场白过滤 (仅在刚开始输出时)
        if not self.in_think_block and not self.has_started_output:
            # ✅ 重写模式下跳过开场白过滤
            if self.is_regeneration:
                self.has_started_output = True
            else:
                # 如果缓冲区还很短，可能还没把废话吐完，先攒一攒
                if len(self.buffer) < 30 and self.buffer.strip(): 
                    return output  # 提前返回，等待更多内容
                
                # 常见的废话正则
                patterns = [
                    r"^(好的|明白了|没问题|Sure|Here is).*?[\n\r]", 
                    r"^.*?(为您|如下).*?[:：][\n\r]",
                    r"^根据.*?要求"
                ]
                
                # 尝试清洗
                temp_buf = self.buffer
                for p in patterns:
                    match = re.match(p, temp_buf, re.IGNORECASE | re.DOTALL)
                    if match:
                        temp_buf = temp_buf[match.end():]
                
                if temp_buf != self.buffer:
                    self.buffer = temp_buf
                    self.has_started_output = True
        
        # 4. 输出缓冲区内容
        if not self.in_think_block:
            # 为了防止 <think> 标签被切断（如 "<thi"），保留最后几个字符
            safe_len = 10
            if len(self.buffer) > safe_len: 
                to_yield = self.buffer[:-safe_len]
                self.buffer = self.buffer[-safe_len:]
                output += to_yield
                self.has_started_output = True
        
        return output

    def flush(self) -> str:
        """最后清空缓冲区"""
        if self.in_think_block: return ""
        return self.buffer
    
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

        # 1. 基础信息
        title = request.chapter.get("title", "")
        desc = request.chapter.get("description", "")
        project_overview = request.project_overview or ""
        
        regeneration_prompt = request.regeneration_prompt
        original_content = request.original_content
        
        # 2. 初始化服务
        db_gen = get_db()
        db = next(db_gen)
        table_service = TableService(db)
        rag_service = get_rag_service()
        
        db_context_str = ""
        rag_context_str = ""
        
        try:
            # 3. 🟢 优化的动静结合逻辑
            
            # (A) 判定是否为"业绩/经验"类章节
            trigger_words = ["业绩", "案例", "经验", "证明", "同类项目", "成功", "交付"]
            exclude_words = ["背景", "目标", "需求", "现状", "原则", "总体", "架构"] 
            
            # 简单评分法判断
            score = 0
            for w in trigger_words: 
                if w in title: score += 1
            for w in exclude_words:
                if w in title: score -= 10
            
            # 标题修正：如果标题包含"公司"和"实力/介绍"，通常也需要业绩
            if "公司" in title and ("实力" in title or "介绍" in title or "概况" in title):
                score += 5

            if score > 0:
                logger.info(f"章节 [{title}] 判定为业绩类章节，触发数据库检索...")
                
                # (B) 智能提取检索关键词
                search_kw = ""
                first_sentence = project_overview[:50]
                if "智慧" in first_sentence: search_kw = "智慧"
                elif "云" in first_sentence: search_kw = "云"
                elif "平台" in first_sentence: search_kw = "平台"
                elif "系统" in first_sentence: search_kw = "系统"
                
                # 策略2：如果启发式太泛，尝试用 LLM 提取
                try:
                    extract_prompt = [
                        {"role": "system", "content": "提取1个核心业务领域关键词(如:智慧城市)，仅输出词。"},
                        {"role": "user", "content": f"项目概述：{project_overview[:200]}"}
                    ]
                    kw_res = await model_service.chat_completion(extract_prompt, temperature=0.1)
                    clean_kw = re.sub(r'[^\w]', '', kw_res).strip()
                    if clean_kw and len(clean_kw) < 10:
                        search_kw = clean_kw
                        logger.info(f"AI提取检索关键词: {search_kw}")
                except Exception as e:
                    logger.warning(f"关键词提取失败，回退到模糊搜索: {e}")
                    if not search_kw: search_kw = "项目"

                # (C) 执行检索
                search_result = table_service.search_projects_and_attachments(search_kw)
                projects = search_result.get("projects", [])
                file_sources = search_result.get("file_sources", [])
                
                if projects:
                    db_context_str = "\n".join([
                        f"- 项目：{p['name']} (金额：{p['amount']}元, 时间：{p['date']}, 客户：{p['company']})"
                        for p in projects
                    ])
                
                # 3.2 查知识库
                rag_filter = {"source": {"$in": file_sources}} if file_sources else None
                query_text = f"{title} {search_kw} 实施难点 解决方案"
                retrieved_docs = rag_service.search(query_text, n_results=3, filter=rag_filter)
                
                if retrieved_docs:
                    rag_context_str = "\n".join([f"- (来源:{doc['source']}) {doc['content']}" for doc in retrieved_docs])
            
            else:
                # 非业绩类章节：常规 RAG 检索
                query_text = f"{title} {desc} {project_overview[:50]}"
                retrieved_docs = rag_service.search(query_text, n_results=3)
                if retrieved_docs:
                    rag_context_str = "\n".join([f"- {doc['content']}" for doc in retrieved_docs])

        finally:
            db.close()

        # 4. 构建 Prompt
        target_word_count = request.chapter.get("word_count", 1000)
        try: target_word_count = int(target_word_count)
        except: target_word_count = 1000

        parent_text = " > ".join([p['title'] for p in (request.parent_chapters or [])])

        # 🟢 分支逻辑：重写 vs 初次生成 (✅ 修复后的版本)
        if regeneration_prompt:
            logger.info(f"🔄 进入重写模式，用户指令: {regeneration_prompt}")
            system_prompt = "你是一名专业的标书编辑，擅长根据用户反馈修改和润色文档。"
            user_prompt = build_regeneration_user_prompt(
                project_overview=project_overview,
                chapter_id=request.chapter.get("id", ""),
                title=title,
                desc=desc,
                original_content=original_content or "(无原有内容)",
                user_instruction=regeneration_prompt,
                rag_context=rag_context_str
            )
        else:
            logger.info(f"✨ 进入初次生成模式")
            system_prompt = build_bidding_system_prompt()
            user_prompt = build_bidding_user_prompt(
                project_overview=project_overview,
                chapter_id=request.chapter.get("id", ""),
                title=title,
                desc=desc,
                parent_text=parent_text,
                target_word_count=target_word_count,
                rag_context=rag_context_str,
                db_context=db_context_str
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 5. 执行生成
        if stream:
            async def generate():
                stream_filter = StreamFilter()
                stream_filter.is_regeneration = bool(regeneration_prompt)  # ✅ 设置重写标识
                full_content = ""
                try:
                    yield f"data: {json.dumps({'status': 'started', 'chapter_id': request.chapter.get('id')}, ensure_ascii=False)}\n\n"
                    
                    async for chunk in model_service.chat_completion_stream(messages, temperature=0.7):
                        filtered_chunk = stream_filter.process(chunk)
                        
                        if filtered_chunk:
                            full_content += filtered_chunk
                            yield f"data: {json.dumps({'status': 'streaming', 'content': filtered_chunk, 'chapter_id': request.chapter.get('id')}, ensure_ascii=False)}\n\n"
                    
                    # 🟢 处理缓冲区剩余内容
                    remaining = stream_filter.flush()
                    if remaining:
                        full_content += remaining
                        logger.info(f"💡 缓冲区剩余内容长度: {len(remaining)}")
                        yield f"data: {json.dumps({'status': 'streaming', 'content': remaining, 'chapter_id': request.chapter.get('id')}, ensure_ascii=False)}\n\n"

                    # 最终清洗
                    final_clean = clean_final_text(full_content)
                    logger.info(f"✅ 完整内容长度: {len(full_content)} → 清洗后: {len(final_clean)}")
                    
                    # 发送完成事件
                    completion_data = {
                        'status': 'completed', 
                        'content': final_clean, 
                        'chapter_id': request.chapter.get('id'),
                        'content_length': len(final_clean),
                        'is_regeneration': bool(regeneration_prompt),
                        'word_count': len(final_clean)
                    }
                    yield f"data: {json.dumps(completion_data, ensure_ascii=False)}\n\n"

                except asyncio.CancelledError:
                    logger.info(f"Chapter generation cancelled for {request.chapter.get('id')}")
                    return
                except Exception as e:
                    logger.error(f"Stream error: {e}", exc_info=True)
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
                
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
                    "chapter_id": request.chapter.get('id')
                }
            )

    except Exception as e:
        logger.error(f"生成失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, 
            content={
                "success": False, 
                "error": str(e), 
                "chapter_id": request.chapter.get("id", "unknown")
            }
        )