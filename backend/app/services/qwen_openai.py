from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, AsyncGenerator, Literal, Union
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
app = FastAPI(title="OpenAI Compatible API Server", version="1.0.0")

# 模型配置
MODEL_PATH = "/root/.cache/modelscope/hub/models/Qwen/Qwen3-8B"
MODEL_NAME = "Qwen3-14B"  # OpenAI兼容的模型名称
TENSOR_PARALLEL_SIZE = 2
GPU_MEMORY_UTILIZATION = 0.8
MAX_TOKENS = 32768 * 4

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 初始化vLLM异步引擎
engine_args = AsyncEngineArgs(
    model=MODEL_PATH,
    tensor_parallel_size=TENSOR_PARALLEL_SIZE,
    gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
    trust_remote_code=True,
    max_num_batched_tokens=32768,
    rope_scaling={
        "rope_type": "yarn",
        "factor": 4.0,
        "original_max_position_embeddings": 32768
    },
    max_model_len=131072
)
llm_engine = AsyncLLMEngine.from_engine_args(engine_args)

logger.info(f"模型服务已启动，模型路径: {MODEL_PATH}")


# ============ OpenAI 标准数据模型 ============

class Message(BaseModel):
    """OpenAI标准消息格式"""
    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI /v1/chat/completions 请求格式"""
    model: str
    messages: List[Message]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1, le=1)  # 目前只支持1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=MAX_TOKENS, ge=1)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


class ChatCompletionResponseChoice(BaseModel):
    """OpenAI响应中的单个选择"""
    index: int
    message: Message
    finish_reason: Optional[str] = None


class ChatCompletionResponseStreamChoice(BaseModel):
    """OpenAI流式响应中的单个选择"""
    index: int
    delta: Dict[str, str]
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    """Token使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI /v1/chat/completions 响应格式"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: UsageInfo


class ChatCompletionStreamResponse(BaseModel):
    """OpenAI流式响应格式"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionResponseStreamChoice]


class ModelCard(BaseModel):
    """模型信息卡片"""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ModelList(BaseModel):
    """模型列表"""
    object: Literal["list"] = "list"
    data: List[ModelCard]


# ============ 服务类 ============

class OpenAICompatibleService:
    """OpenAI兼容的服务类"""

    def __init__(self, engine: AsyncLLMEngine, tokenizer: AutoTokenizer):
        self.engine = engine
        self.tokenizer = tokenizer

    def _build_prompt(self, messages: List[Message]) -> str:
        """将消息列表转换为模型所需的提示词格式"""
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
        return self.tokenizer.apply_chat_template(
            messages_dict,
            tokenize=False,
            add_generation_prompt=True
        )

    def _count_tokens(self, text: str) -> int:
        """统计文本的token数量"""
        return len(self.tokenizer.encode(text))

    async def create_chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """非流式聊天补全"""
        request_id = f"chatcmpl-{random_uuid()}"
        created = int(time.time())

        # 构建提示词
        formatted_prompt = self._build_prompt(request.messages)
        prompt_tokens = self._count_tokens(formatted_prompt)

        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stop=request.stop if request.stop else [self.tokenizer.eos_token],
            skip_special_tokens=True,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty
        )

        # 生成响应
        final_output = None
        async for output in self.engine.generate(formatted_prompt, sampling_params, request_id):
            final_output = output

        if final_output is None:
            raise ValueError("未获取到模型生成结果")

        # 解析结果
        generated_text = final_output.outputs[0].text.strip()
        finish_reason = final_output.outputs[0].finish_reason
        completion_tokens = self._count_tokens(generated_text)

        # 构建OpenAI标准响应
        return ChatCompletionResponse(
            id=request_id,
            created=created,
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=generated_text),
                    finish_reason=finish_reason
                )
            ],
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )

    async def create_chat_completion_stream(
        self,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        request_id = f"chatcmpl-{random_uuid()}"
        created = int(time.time())

        # 构建提示词
        formatted_prompt = self._build_prompt(request.messages)

        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stop=request.stop if request.stop else [self.tokenizer.eos_token],
            skip_special_tokens=True,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty
        )

        # 流式生成
        prev_text = ""
        async for output in self.engine.generate(formatted_prompt, sampling_params, request_id):
            full_text = output.outputs[0].text
            finish_reason = output.outputs[0].finish_reason

            # 计算新增文本
            new_text = full_text[len(prev_text):]
            prev_text = full_text

            if new_text:
                # 构建流式响应
                chunk = ChatCompletionStreamResponse(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[
                        ChatCompletionResponseStreamChoice(
                            index=0,
                            delta={"role": "assistant", "content": new_text},
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {chunk.model_dump_json()}\n\n"

            # 发送结束标记
            if finish_reason is not None:
                final_chunk = ChatCompletionStreamResponse(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[
                        ChatCompletionResponseStreamChoice(
                            index=0,
                            delta={},
                            finish_reason=finish_reason
                        )
                    ]
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                break


# 初始化服务
service = OpenAICompatibleService(llm_engine, tokenizer)


# ============ API 端点 ============

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """
    OpenAI标准的聊天补全接口
    兼容 OpenAI Python SDK 和其他标准客户端
    """
    try:
        # 验证消息列表
        if not request.messages:
            raise HTTPException(status_code=400, detail="消息列表不能为空")

        # 流式响应
        if request.stream:
            return StreamingResponse(
                service.create_chat_completion_stream(request),
                media_type="text/event-stream"
            )

        # 非流式响应
        response = await service.create_chat_completion(request)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天补全失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.get("/v1/models")
async def list_models() -> ModelList:
    """
    OpenAI标准的模型列表接口
    返回可用的模型信息
    """
    return ModelList(
        data=[
            ModelCard(
                id=MODEL_NAME,
                created=int(time.time()),
                owned_by="local"
            )
        ]
    )


@app.get("/v1/models/{model_id}")
async def retrieve_model(model_id: str) -> ModelCard:
    """
    OpenAI标准的获取单个模型信息接口
    """
    if model_id != MODEL_NAME:
        raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")

    return ModelCard(
        id=MODEL_NAME,
        created=int(time.time()),
        owned_by="local"
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "timestamp": int(time.time())
    }


# ============ 中间件 ============

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    logger.info(f"收到请求: {request.method} {request.url}")

    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                body_json = json.loads(body.decode())
                logger.info(f"请求体: {json.dumps(body_json, indent=2)}")
        except Exception as e:
            logger.warning(f"无法解析请求体: {str(e)}")

    response = await call_next(request)
    return response


# ============ 启动服务 ============

if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("准备启动OpenAI兼容API服务，监听端口: 10086")
        uvicorn.run(app, host="0.0.0.0", port=10086, workers=1, log_level="info")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}", exc_info=True)