from typing import AsyncGenerator, Optional, List, Dict
import aiohttp
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)

class QwenService:
    """
    Qwen服务类（适配 vLLM 原生 OpenAI 兼容接口）
    """
    def __init__(self, base_url: str = "http://localhost:10086"):
        # 确保 base_url 不以 /v1 结尾（我们在请求时自动拼接）
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        
        # 默认参数
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 131071,  # vLLM 支持较大的上下文
            "top_p": 0.95,
            "top_k": 20,
        }
        
        # 缓存模型名称，避免每次请求都查
        self._cached_model_name: Optional[str] = None

    async def _get_running_model(self, session: aiohttp.ClientSession) -> str:
        """
        动态获取 vLLM 当前运行的模型名称
        """
        if self._cached_model_name:
            return self._cached_model_name
            
        try:
            # vLLM 提供标准的 /v1/models 接口
            async with session.get(f"{self.base_url}/v1/models", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # 获取列表中的第一个模型 ID
                    model_id = data["data"][0]["id"]
                    self._cached_model_name = model_id
                    logger.info(f"已自动探测到 vLLM 模型名称: {model_id}")
                    return model_id
        except Exception as e:
            logger.warning(f"无法获取模型列表，将使用默认名称: {e}")
        
        # 如果获取失败，返回一个通用默认值（vLLM 有时对模型名不敏感，但也可能报错）
        return "Qwen/Qwen2.5-14B-Instruct"

    async def chat_completion_stream(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式输出 (Stream=True)
        """
        async with aiohttp.ClientSession() as session:
            # 1. 准备模型名称
            model_name = await self._get_running_model(session)
            
            # 2. 构造 OpenAI 标准请求体
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                "temperature": temperature or self.default_params["temperature"],
                "max_tokens": self.default_params["max_tokens"],
                "top_p": self.default_params["top_p"],
            }

            try:
                # 3. 发起请求
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    await self._check_response_status(response)
                    
                    # 4. 逐行解析 SSE 数据
                    async for line in response.content:
                        decoded_line = line.decode("utf-8").strip()
                        
                        if not decoded_line:
                            continue
                            
                        # OpenAI 格式是以 "data: " 开头
                        if decoded_line.startswith("data:"):
                            data_str = decoded_line[5:].strip() # 去掉 "data:"
                            
                            if data_str == "[DONE]":
                                break
                                
                            try:
                                data_json = json.loads(data_str)
                                # 提取增量内容: choices[0].delta.content
                                choices = data_json.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                                
            except aiohttp.ClientConnectorError:
                raise Exception(f"无法连接到 vLLM 服务 ({self.base_url})，请确认服务已通过 'vllm serve' 启动。")

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None
    ) -> str:
        """
        非流式输出 (Stream=False)
        """
        async with aiohttp.ClientSession() as session:
            model_name = await self._get_running_model(session)
            
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "temperature": temperature or self.default_params["temperature"],
                "max_tokens": self.default_params["max_tokens"],
                "top_p": self.default_params["top_p"],
            }

            try:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    await self._check_response_status(response)
                    
                    data = await response.json()
                    # 提取完整内容: choices[0].message.content
                    return data["choices"][0]["message"]["content"]
                    
            except aiohttp.ClientConnectorError:
                raise Exception(f"无法连接到 vLLM 服务 ({self.base_url})，请确认服务已启动。")

    async def _check_response_status(self, response: aiohttp.ClientResponse) -> None:
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"vLLM API 请求失败 (状态码 {response.status}): {error_text}")