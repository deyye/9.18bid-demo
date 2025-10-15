from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator, Literal
from vllm import AsyncLLMEngine, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.utils import random_uuid
from transformers import AutoTokenizer
import time
import json
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ["VLLM_USE_MODELSCOPE"] = "true"
# 初始化FastAPI应用
app = FastAPI(title="Qwen Local Model Server")

# 模型配置 - 根据实际环境调整
MODEL_PATH = "/root/.cache/modelscope/hub/models/Qwen/Qwen3-14B"
TENSOR_PARALLEL_SIZE = 2  # GPU数量
GPU_MEMORY_UTILIZATION = 0.8  # GPU内存利用率

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token  # 设置pad token

# 初始化vLLM异步引擎
engine_args = AsyncEngineArgs(
    model=MODEL_PATH,
    tensor_parallel_size=TENSOR_PARALLEL_SIZE,
    gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
    trust_remote_code=True,
    max_num_batched_tokens=32768,  # 批量处理的总Token上限
    
    # # YARN RoPE 缩放配置
    rope_scaling={
        "rope_type": "yarn",          
        "factor": 4.0,               
        "original_max_position_embeddings": 32768  
    },
    
    # # 扩展后的模型最大上下文长度
    max_model_len=131072  # 32768 × 4 = 131072
)
llm_engine = AsyncLLMEngine.from_engine_args(engine_args)

print(f"Qwen模型服务已启动，模型路径: {MODEL_PATH}")

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 记录请求路径和方法
    print(f"\n收到请求: {request.method} {request.url}")
    
    # 记录请求头
    print("请求头:", dict(request.headers))
    
    # 记录请求体（仅对POST/PUT等有body的请求有效）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # 读取请求体（注意：FastAPI中request.body()只能读取一次，需特殊处理）
            body = await request.body()
            if body:
                # 尝试解析为JSON
                body_json = json.loads(body.decode())
                print("请求体:", json.dumps(body_json, indent=2))
            else:
                print("请求体: 空")
        except json.JSONDecodeError:
            print("请求体: 非JSON格式 ->", body.decode())
        except Exception as e:
            print(f"读取请求体失败: {str(e)}")
    
    # 继续处理请求
    response = await call_next(request)
    return response

# 定义请求和响应的数据模型
class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = "你是一个专业的投标书编写专家，根据用户问题和上下文给出回答。"
    temperature: float = 0.6
    max_tokens: int = 131072
    top_p: float = 0.95
    top_k: int = 20
    stream: bool = False

# 新增：为/api/chat接口定义专用的请求模型，可能与客户端匹配
class ChatRequest(BaseModel):
    message: str  # 对应客户端发送的消息内容
    system_prompt: Optional[str] = "你是一个专业的投标书编写专家，根据用户问题和上下文给出回答。"
    temperature: float = 0.6
    max_tokens: int = 131072
    stream: bool = False

# 新增：匹配客户端/chat/completions请求的专用模型（核心修改）
class MessageItem(BaseModel):
    """客户端messages数组中的单个消息结构"""
    role: Literal["system", "user", "assistant"]  # 严格匹配客户端角色类型
    content: str  # 消息内容

class CompletionsRequest(BaseModel):
    """/chat/completions接口的请求模型，完全匹配客户端格式"""
    model: str  # 客户端必传的模型名称字段
    messages: List[MessageItem]  # 客户端的消息列表
    max_tokens: Optional[int] = 131072  # 客户端传递的生成Token上限
    temperature: float = 0.6  # 默认值，允许客户端覆盖
    stream: bool = False  # 流式开关

class GenerateResponse(BaseModel):
    request_id: str
    generated_text: str
    created: int
    finish_reason: Optional[str] = None

class QwenService:
    """Qwen服务类，适配vLLM的异步生成器"""
    
    def __init__(self, engine: AsyncLLMEngine, tokenizer: AutoTokenizer):
        self.engine = engine
        self.tokenizer = tokenizer
    
    def build_prompt(self, prompt: str, system_prompt: str) -> str:
        """构建符合Qwen模型要求的提示词（原功能保留）"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
    
    def build_prompt_from_messages(self, messages: List[Dict]) -> str:
        """新增：从客户端messages列表构建提示词（适配/completions接口）"""
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
    
    async def generate(self, prompt: str, system_prompt: str = "", 
                      temperature: float = 0.6, max_tokens: int = 131072,
                      top_p: float = 0.95, top_k: int = 20) -> GenerateResponse:
        """非流式生成（原功能保留，扩展system_prompt默认值）"""
        request_id = random_uuid()
        created = int(time.time())
        
        # 构建提示词和采样参数
        formatted_prompt = self.build_prompt(prompt, system_prompt) if system_prompt else self.build_prompt_from_messages(prompt)
        sampling_params = SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=self.tokenizer.eos_token,
            skip_special_tokens=True
        )
        
        # 用async for迭代异步生成器，取最后一个结果
        final_output = None
        async for output in self.engine.generate(formatted_prompt, sampling_params, request_id):
            final_output = output
        
        if final_output is None:
            raise ValueError("未获取到模型生成结果")
        
        # 解析最终结果
        generated_text = final_output.outputs[0].text.strip()
        finish_reason = final_output.outputs[0].finish_reason
        
        return GenerateResponse(
            request_id=request_id,
            generated_text=generated_text,
            created=created,
            finish_reason=finish_reason
        )
    
    async def generate_stream(self, prompt: str, system_prompt: str = "",
                             temperature: float = 0.6, max_tokens: int = 131072,
                             top_p: float = 0.95, top_k: int = 20) -> AsyncGenerator[str, None]:
        """流式生成（原功能保留，扩展system_prompt默认值）"""
        request_id = random_uuid()
        created = int(time.time())

        # 构建提示词和采样参数
        formatted_prompt = self.build_prompt(prompt, system_prompt) if system_prompt else self.build_prompt_from_messages(prompt)
        sampling_params = SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=self.tokenizer.eos_token,
            skip_special_tokens=True
        )

        prev_text = ""  # 用来存放历史生成结果
        async for output in self.engine.generate(formatted_prompt, sampling_params, request_id):
            full_text = output.outputs[0].text
            finish_reason = output.outputs[0].finish_reason

            # 只取新增部分
            new_text = full_text[len(prev_text):]
            prev_text = full_text

            if new_text:
                yield json.dumps({
                    "request_id": request_id,
                    "chunk": new_text,
                    "created": created,
                    "finish_reason": finish_reason
                }) + "\n"

            if finish_reason is not None:
                break

# 初始化Qwen服务
qwen_service = QwenService(llm_engine, tokenizer)

# 原有/generate接口（功能完全保留）
@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """生成文本响应的API端点"""
    try:
        if request.stream:
            async def stream_generator():
                async for chunk in qwen_service.generate_stream(
                    prompt=request.prompt,
                    system_prompt=request.system_prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # SSE 格式
                    yield f"data: {chunk}\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            return await qwen_service.generate(
                prompt=request.prompt,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"生成过程出错: {error_details}")
        raise HTTPException(status_code=500, detail=f"模型生成失败: {str(e)}")

# 修改：/chat/completions接口（适配客户端请求格式）
@app.post("/api/chat")
async def chat_completions(request: CompletionsRequest):
    """适配客户端的/chat/completions请求，支持model和messages字段"""
    try:
        # 1. 基础校验：确保包含user消息
        if not request.messages or not any(item.role == "user" for item in request.messages):
            raise HTTPException(status_code=400, detail="请求必须包含至少一条'user'角色的消息")
        
        # 2. 可选：校验模型名称（如果需要限制仅支持Qwen3-14B）
        # if request.model != "Qwen3-14B":
        #     raise HTTPException(status_code=400, detail=f"不支持的模型: {request.model}，仅支持Qwen3-14B")
        
        # 3. 转换消息格式（Pydantic模型转字典列表）
        messages_dict = [{"role": item.role, "content": item.content} for item in request.messages]
        
        # 4. 流式响应处理
        if request.stream:
            async def stream_generator():
                async for chunk in qwen_service.generate_stream(
                    prompt=messages_dict,  # 传入消息列表
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # 转换为客户端易解析的SSE格式
                    yield f"data: {chunk}\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 5. 非流式响应处理
            response = await qwen_service.generate(
                prompt=messages_dict,  # 传入消息列表
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # 6. 返回格式适配（模拟类OpenAI结构，便于客户端解析）
            return {
                "id": f"chatcmpl-{response.request_id}",
                "object": "chat.completion",
                "created": response.created,
                "model": request.model,  # 回传客户端请求的模型名称
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response.generated_text},
                        "finish_reason": response.finish_reason
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}  # 可按需补充Token统计
            }
    except HTTPException:
        raise  # 直接抛出已定义的HTTP异常
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"/chat/completions 接口出错: {error_details}")
        raise HTTPException(status_code=500, detail=f"聊天请求处理失败: {str(e)}")

# 原有/v1/models接口（功能完全保留）
@app.get("/v1/models")
async def list_models():
    """返回可用的模型列表"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen-14b",
                "object": "model",
                "owned_by": "local",
                "permission": [],
            }
        ]
    }

# 原有/health接口（功能完全保留）
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model": MODEL_PATH.split("/")[-1],
        "timestamp": int(time.time())
    }

@app.post("/chat/completions")
async def chat_completions(request: CompletionsRequest):
    """适配客户端的/chat/completions请求，支持model和messages字段"""
    try:
        # 1. 基础校验：确保包含user消息
        if not request.messages or not any(item.role == "user" for item in request.messages):
            raise HTTPException(status_code=400, detail="请求必须包含至少一条'user'角色的消息")
        
        # 2. 可选：校验模型名称（如果需要限制仅支持Qwen3-14B）
        # if request.model != "Qwen3-14B":
        #     raise HTTPException(status_code=400, detail=f"不支持的模型: {request.model}，仅支持Qwen3-14B")
        
        # 3. 转换消息格式（Pydantic模型转字典列表）
        messages_dict = [{"role": item.role, "content": item.content} for item in request.messages]
        request.stream = False
        # 4. 流式响应处理
        if request.stream:
            async def stream_generator():
                async for chunk in qwen_service.generate_stream(
                    prompt=messages_dict,  # 传入消息列表
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # 转换为客户端易解析的SSE格式
                    yield f"data: {chunk}\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 5. 非流式响应处理
            response = await qwen_service.generate(
                prompt=messages_dict,  # 传入消息列表
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            print(response)
            # 6. 返回格式适配（模拟类OpenAI结构，便于客户端解析）
            return response
    except HTTPException:
        raise  # 直接抛出已定义的HTTP异常
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"/chat/completions 接口出错: {error_details}")
        raise HTTPException(status_code=500, detail=f"聊天请求处理失败: {str(e)}")
    
# 启动服务
if __name__ == "__main__":
    try:
        import uvicorn
        logger.info(f"准备启动服务，监听端口: 10086")
        uvicorn.run(app, host="0.0.0.0", port=10086, workers=1, log_level="info")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}", exc_info=True)