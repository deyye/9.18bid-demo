from typing import AsyncGenerator, Optional
import aiohttp
import json

class QwenService:
    """Qwen服务类，支持流式输出和非流式输出"""
    def __init__(self, base_url: str = "http://localhost:10086"):
        self.base_url = base_url.rstrip("/")  # 确保URL末尾无斜杠，避免拼接错误
        self.headers = {"Content-Type": "application/json"}
        # 统一请求参数默认值（流式/非流式共用）
        self.default_params = {
            "temperature": 0.3,
            "max_tokens": 131072,
            "top_p": 0.95,
            "top_k": 20,
        }

    async def chat_completion_stream(
        self, 
        messages: list[dict], 
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式输出：调用Qwen接口，逐字符返回响应
        
        Args:
            messages: 对话列表，格式为 [{"role": "system/user", "content": "prompt"}]
            temperature: 生成随机性（优先级：传入值 > 默认值）
        
        Yields:
            逐字符的响应内容，最后返回 "[DONE]" 结束标志
        """
        # 1. 解析prompt和合并参数
        system_prompt, user_prompt = self._parse_messages(messages)
        actual_temp = temperature or self.default_params["temperature"]

        # 2. 构造流式请求体（stream=True）
        qwen_request = {
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "temperature": actual_temp,
            "max_tokens": self.default_params["max_tokens"],
            "stream": True,  # 流式核心参数
            "top_p": self.default_params["top_p"],
            "top_k": self.default_params["top_k"]
        }

        # 3. 异步调用流式接口并逐行解析
        timeout = aiohttp.ClientTimeout(total=60*15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url=f"{self.base_url}/generate",
                headers=self.headers,
                json=qwen_request
            ) as response:
                self._check_response_status(response)  # 复用响应状态检查
                async for line_bytes in response.content:
                    line = line_bytes.decode("utf-8").strip()
                    if not line:
                        continue

                    # 处理SSE格式前缀（data: ...）
                    if line.startswith("data:"):
                        line = line[len("data:"):].strip()
                    # 结束标志处理
                    if line == "[DONE]":
                        break

                    # 解析chunk并逐字符返回
                    try:
                        chunk_data = json.loads(line)
                        current_chunk = chunk_data.get("chunk", "")
                        if current_chunk:
                            for ch in current_chunk:
                                yield ch
                        # 若接口返回结束原因，提前终止
                        if chunk_data.get("finish_reason") is not None:
                            break
                    except json.JSONDecodeError as e:
                        raise Exception(f"Qwen流式响应解析失败：{str(e)}，原始内容：{line}")

        yield "[DONE]"  # 流式结束标识

    async def chat_completion(
        self, 
        messages: list[dict], 
        temperature: Optional[float] = None
    ) -> str:
        """
        非流式输出：调用Qwen接口，直接返回完整响应文本
        
        Args:
            messages: 对话列表，格式为 [{"role": "system/user", "content": "prompt"}]
            temperature: 生成随机性（优先级：传入值 > 默认值）
        
        Returns:
            完整的Qwen响应文本
        
        Raises:
            Exception: 请求失败、响应解析错误时抛出异常
        """
        # 1. 复用prompt解析逻辑，避免代码冗余
        system_prompt, user_prompt = self._parse_messages(messages)
        actual_temp = temperature or self.default_params["temperature"]

        # 2. 构造非流式请求体（stream=False）
        qwen_request = {
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "temperature": actual_temp,
            "max_tokens": self.default_params["max_tokens"],
            "stream": False,  # 非流式核心参数：关闭分块返回
            "top_p": self.default_params["top_p"],
            "top_k": self.default_params["top_k"]
        }

        # 3. 异步调用非流式接口并获取完整结果
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"{self.base_url}/generate",  # 复用接口路径（Qwen通常同一接口支持stream切换）
                headers=self.headers,
                json=qwen_request
            ) as response:
                self._check_response_status(response)  # 复用响应状态检查
                response_text = await response.text()  # 获取完整响应文本

                # 4. 解析非流式响应（假设接口返回 {"text": "完整结果", "finish_reason": "..."}）
                try:
                    response_data = json.loads(response_text)
                    # 优先取"text"字段（非流式通常返回完整文本），兼容流式的"chunk"字段兜底
                    full_result = response_data.get("generated_text", response_data.get("chunk", ""))
                    if not full_result:
                        raise Exception(f"Qwen非流式响应无有效内容：{response_data}")
                    return full_result
                except json.JSONDecodeError as e:
                    raise Exception(f"Qwen非流式响应解析失败：{str(e)}，原始内容：{response_text}")

    def _parse_messages(self, messages: list[dict]) -> tuple[str, str]:
        """
        复用方法：从对话列表中提取system prompt和user prompt
        
        Args:
            messages: 对话列表
        
        Returns:
            (system_prompt, user_prompt)：解析后的系统提示和用户提示
        """
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                user_prompt = content
        # 若未找到system/user prompt，返回空字符串（避免接口报错）
        return system_prompt, user_prompt

    def _check_response_status(self, response: aiohttp.ClientResponse) -> None:
        """
        复用方法：检查HTTP响应状态码，非200时抛出异常
        
        Args:
            response: aiohttp响应对象
        
        Raises:
            Exception: 响应状态码非200时抛出
        """
        if response.status != 200:
            error_detail = response.text()  # 获取错误详情
            raise Exception(f"Qwen服务请求失败（状态码：{response.status}）：{error_detail}")