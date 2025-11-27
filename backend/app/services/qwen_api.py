from typing import AsyncGenerator, Optional, List, Dict, Any
import aiohttp
import json
import logging

logger = logging.getLogger(__name__)

class QwenService:
    """
    Qwen服务类（适配 OpenAI 兼容接口，完美支持 qwen_openai.py）
    """
    def __init__(self, base_url: str = "http://localhost:10086"):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 131072,
            "top_p": 0.95,
            "top_k": 20,
        }
        self._cached_model_name: Optional[str] = None

    async def _get_running_model(self, session: aiohttp.ClientSession) -> str:
        """动态获取当前运行的模型名称"""
        if self._cached_model_name:
            return self._cached_model_name
        try:
            async with session.get(f"{self.base_url}/v1/models", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    model_id = data["data"][0]["id"]
                    self._cached_model_name = model_id
                    return model_id
        except Exception as e:
            logger.warning(f"获取模型名失败，使用默认值: {e}")
        return "Qwen3-14B"

    async def chat_completion_stream(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        **kwargs  # ✅ 新增：接收 response_format 等额外参数，防止报错
    ) -> AsyncGenerator[str, None]:
        async with aiohttp.ClientSession() as session:
            model_name = await self._get_running_model(session)
            
            # 构造 Payload
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                "temperature": temperature or self.default_params["temperature"],
                "max_tokens": self.default_params["max_tokens"],
                "top_p": self.default_params["top_p"],
            }
            
            # 注意：我们这里故意不把 kwargs (如 response_format) 传给 payload
            # 因为 qwen_openai.py 可能不支持这些参数，传了反而会报 422 错误。
            # Qwen 模型通常通过 Prompt 指令就能很好地输出 JSON，不需要强制 response_format。

            try:
                async with session.post(f"{self.base_url}/v1/chat/completions", headers=self.headers, json=payload) as response:
                    await self._check_response_status(response)
                    async for line in response.content:
                        decoded_line = line.decode("utf-8").strip()
                        if not decoded_line or decoded_line == "data: [DONE]": continue
                        if decoded_line.startswith("data:"):
                            try:
                                data_json = json.loads(decoded_line[5:])
                                # 兼容 OpenAI 格式
                                choices = data_json.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content", "")
                                    if content: yield content
                            except: continue
            except Exception as e:
                raise Exception(f"流式请求失败: {e}")

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        **kwargs  # ✅ 新增：接收 response_format 等额外参数
    ) -> str:
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
            # 同样忽略 kwargs 中的 response_format

            try:
                async with session.post(f"{self.base_url}/v1/chat/completions", headers=self.headers, json=payload) as response:
                    await self._check_response_status(response)
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                raise Exception(f"请求失败: {e}")

    async def _check_response_status(self, response: aiohttp.ClientResponse) -> None:
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"API 错误 ({response.status}): {error_text}")