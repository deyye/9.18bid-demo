from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator
from vllm import AsyncLLMEngine, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.utils import random_uuid
from transformers import AutoTokenizer
import time
import json

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
    max_num_batched_tokens=32768,
)
llm_engine = AsyncLLMEngine.from_engine_args(engine_args)

print(f"Qwen模型服务已启动，模型路径: {MODEL_PATH}")

# 定义请求和响应的数据模型
class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = "你是一个专业的投标书编写专家，根据用户问题和上下文给出回答。"
    temperature: float = 0.6
    max_tokens: int = 32768
    top_p: float = 0.95
    top_k: int = 20
    stream: bool = False

class GenerateResponse(BaseModel):
    request_id: str
    generated_text: str
    created: int
    finish_reason: Optional[str] = None

class QwenService:
    """修复后的Qwen服务类，适配新版vLLM的异步生成器"""
    
    def __init__(self, engine: AsyncLLMEngine, tokenizer: AutoTokenizer):
        self.engine = engine
        self.tokenizer = tokenizer
    
    def build_prompt(self, prompt: str, system_prompt: str) -> str:
        """构建符合Qwen模型要求的提示词"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """非流式生成（适配新版vLLM的async_generator）"""
        request_id = random_uuid()
        created = int(time.time())
        
        # 构建提示词和采样参数
        prompt = self.build_prompt(request.prompt, request.system_prompt)
        sampling_params = SamplingParams(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            stop=self.tokenizer.eos_token,
            skip_special_tokens=True
        )
        
        # 关键修复：用async for迭代异步生成器，取最后一个结果
        final_output = None
        async for output in self.engine.generate(prompt, sampling_params, request_id):
            final_output = output  # 不断更新为最新批次的结果
        
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
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        request_id = random_uuid()
        created = int(time.time())

        # 构建提示词和采样参数
        prompt = self.build_prompt(request.prompt, request.system_prompt)
        sampling_params = SamplingParams(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            stop=self.tokenizer.eos_token,
            skip_special_tokens=True
        )

        prev_text = ""  # 用来存放历史生成结果
        async for output in self.engine.generate(prompt, sampling_params, request_id):
            full_text = output.outputs[0].text
            finish_reason = output.outputs[0].finish_reason

            # 只取新增部分
            new_text = full_text[len(prev_text):]
            prev_text = full_text

            if new_text:
                yield json.dumps({
                    "request_id": request_id,
                    "chunk": new_text,   # 这里变成逐 token/逐增量输出
                    "created": created,
                    "finish_reason": finish_reason
                }) + "\n"

            if finish_reason is not None:
                break

# 初始化Qwen服务
qwen_service = QwenService(llm_engine, tokenizer)

# 定义API端点
@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """生成文本响应的API端点"""
    try:
        if request.stream:
            async def stream_generator():
                async for chunk in qwen_service.generate_stream(request):
                    # SSE 格式
                    yield f"data: {chunk}\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            return await qwen_service.generate(request)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"生成过程出错: {error_details}")
        raise HTTPException(status_code=500, detail=f"模型生成失败: {str(e)}")
    
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

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model": MODEL_PATH.split("/")[-1],
        "timestamp": int(time.time())
    }

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10086, workers=1)