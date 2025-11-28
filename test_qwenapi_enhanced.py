"""
Qwen OpenAI兼容接口性能评估框架 - 增强版
评估指标：TTFT、吞吐量、响应时间分位数、生成速度、内容质量等
新增：10+并发测试、30k+ tokens长文本测试
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import numpy as np
from openai import AsyncOpenAI, OpenAI
import aiohttp
import pandas as pd
from collections import defaultdict
import logging
from enum import Enum
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置部分 ====================

class TestConfig:
    """测试配置"""
    BASE_URL = "http://localhost:10086/v1"
    API_KEY = "any"  # OpenAI兼容接口通常不需要真实的API key
    MODEL_NAME = "qwen3-14b"
    
    # 测试参数 - 增强并发测试
    CONCURRENT_REQUESTS = [1, 5, 10, 15, 20, 30, 50]  # 增加更多并发级别
    MAX_TOKENS_OPTIONS = [1280, 2560, 5120, 10240, 20480, 32768]  # 增加超长文本测试
    TEMPERATURE_OPTIONS = [0.0, 0.7, 1.0]  # 不同的温度参数
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒
    
    # 超时配置
    REQUEST_TIMEOUT = 600  # 增加到600秒以支持超长文本生成

# ==================== 数据类定义 ====================

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    request_id: str
    prompt: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    # 时间指标（毫秒）
    ttft: float  # Time to First Token
    total_time: float  # 总响应时间
    
    # 吞吐量指标
    tokens_per_second: float  # 生成速度
    
    # 流式响应指标
    chunk_times: List[float] = field(default_factory=list)  # 每个chunk的时间戳
    chunk_sizes: List[int] = field(default_factory=list)  # 每个chunk的大小
    
    # 响应内容
    response_text: str = ""
    finish_reason: str = ""
    
    # 错误信息
    error: Optional[str] = None
    
    # 元数据
    timestamp: float = field(default_factory=lambda: time.time())
    test_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    """测试结果汇总"""
    test_name: str
    metrics: List[PerformanceMetrics]
    
    # 统计指标
    ttft_stats: Dict[str, float] = field(default_factory=dict)
    latency_stats: Dict[str, float] = field(default_factory=dict)
    throughput_stats: Dict[str, float] = field(default_factory=dict)
    
    # 成功率
    success_rate: float = 0.0
    error_count: int = 0
    
    # 测试配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_statistics(self):
        """计算统计指标"""
        valid_metrics = [m for m in self.metrics if m.error is None]
        
        if not valid_metrics:
            return
        
        # TTFT统计
        ttfts = [m.ttft for m in valid_metrics]
        self.ttft_stats = {
            'min': min(ttfts),
            'max': max(ttfts),
            'mean': statistics.mean(ttfts),
            'median': statistics.median(ttfts),
            'p50': np.percentile(ttfts, 50),
            'p95': np.percentile(ttfts, 95),
            'p99': np.percentile(ttfts, 99),
            'std': statistics.stdev(ttfts) if len(ttfts) > 1 else 0
        }
        
        # 延迟统计
        latencies = [m.total_time for m in valid_metrics]
        self.latency_stats = {
            'min': min(latencies),
            'max': max(latencies),
            'mean': statistics.mean(latencies),
            'median': statistics.median(latencies),
            'p50': np.percentile(latencies, 50),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99),
            'std': statistics.stdev(latencies) if len(latencies) > 1 else 0
        }
        
        # 吞吐量统计
        throughputs = [m.tokens_per_second for m in valid_metrics]
        self.throughput_stats = {
            'min': min(throughputs),
            'max': max(throughputs),
            'mean': statistics.mean(throughputs),
            'median': statistics.median(throughputs),
            'std': statistics.stdev(throughputs) if len(throughputs) > 1 else 0
        }
        
        # 成功率
        self.success_rate = len(valid_metrics) / len(self.metrics) * 100
        self.error_count = len(self.metrics) - len(valid_metrics)

# ==================== 测试用例定义 ====================

class TestPrompts:
    """测试用例提示词"""
    
    # 简单问答
    SIMPLE_QA = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "What are the benefits of exercise?",
        "How does photosynthesis work?",
        "What is machine learning?",
    ]
    
    # 代码生成
    CODE_GENERATION = [
        "Write a Python function to calculate fibonacci numbers.",
        "Create a JavaScript function to reverse a string.",
        "Write a SQL query to find the top 10 customers by purchase amount.",
        "Implement a binary search algorithm in Python.",
        "Create a React component for a todo list.",
    ]
    
    # 创意写作
    CREATIVE_WRITING = [
        "Write a short story about a time traveler.",
        "Compose a poem about artificial intelligence.",
        "Create a product description for a smart watch.",
        "Write a news article about a fictional scientific discovery.",
        "Generate a movie plot synopsis.",
    ]
    
    # 长文本生成
    LONG_FORM = [
        "Write a comprehensive guide on how to start a small business, including market research, business planning, funding options, and marketing strategies.",
        "Explain the history, current state, and future prospects of renewable energy technologies.",
        "Provide a detailed analysis of the pros and cons of remote work for both employees and employers.",
        "Write an in-depth tutorial on machine learning for beginners, covering basic concepts, algorithms, and practical applications.",
        "Create a comprehensive travel guide for Tokyo, including attractions, food, culture, and practical tips.",
    ]
    
    # 超长文本生成 - 新增，用于30k+ tokens测试
    ULTRA_LONG_FORM = [
        """Write an extremely comprehensive and detailed technical documentation for building a complete e-commerce platform from scratch. 
        Include the following sections with extensive details:
        1. System Architecture: Describe microservices architecture, database design, caching strategies, message queues, API gateway design
        2. Frontend Development: React/Vue setup, state management, component architecture, responsive design, accessibility
        3. Backend Development: RESTful API design, authentication/authorization, payment integration, order processing
        4. Database Design: Schema design, indexing strategies, query optimization, data migration
        5. DevOps: CI/CD pipelines, containerization with Docker, Kubernetes orchestration, monitoring and logging
        6. Security: OWASP top 10 mitigation, encryption, secure coding practices, penetration testing
        7. Performance Optimization: Caching strategies, CDN integration, load balancing, database optimization
        8. Testing: Unit testing, integration testing, E2E testing, load testing strategies
        9. Deployment: Cloud deployment (AWS/Azure/GCP), infrastructure as code, scaling strategies
        10. Maintenance: Monitoring, alerting, incident response, backup and recovery
        Please provide code examples, best practices, common pitfalls, and real-world case studies for each section.""",
        
        """Create an exhaustive analysis of climate change covering all aspects:
        1. Scientific Foundations: Greenhouse effect, carbon cycle, atmospheric physics, ocean chemistry, climate feedback loops
        2. Historical Context: Climate throughout Earth's history, ice ages, previous warming periods, paleoclimatology
        3. Current Evidence: Temperature records, ice core data, sea level changes, ocean acidification, extreme weather patterns
        4. Climate Models: GCMs, regional models, scenario planning, uncertainty quantification, model validation
        5. Environmental Impacts: Ecosystem disruption, biodiversity loss, ocean changes, cryosphere melting, weather extremes
        6. Human Impacts: Agriculture effects, water resources, health impacts, economic consequences, migration patterns
        7. Mitigation Strategies: Renewable energy technologies, carbon capture, reforestation, policy mechanisms
        8. Adaptation Measures: Infrastructure resilience, agricultural adaptation, coastal protection, urban planning
        9. International Cooperation: Paris Agreement, IPCC reports, national policies, carbon markets, technology transfer
        10. Future Scenarios: RCP pathways, tipping points, long-term projections, technological solutions
        Provide detailed scientific explanations, data visualizations descriptions, case studies from different regions, and policy recommendations.""",
        
        """Write a complete guide to artificial intelligence and machine learning covering all major topics in depth:
        1. Mathematical Foundations: Linear algebra, calculus, probability theory, statistics, optimization theory
        2. Classical Machine Learning: Supervised learning algorithms, unsupervised learning, reinforcement learning, ensemble methods
        3. Deep Learning: Neural networks, CNNs, RNNs, Transformers, attention mechanisms, modern architectures
        4. Natural Language Processing: Tokenization, embeddings, language models, BERT, GPT, machine translation
        5. Computer Vision: Image classification, object detection, semantic segmentation, GANs, diffusion models
        6. Training Techniques: Backpropagation, optimization algorithms, regularization, batch normalization, hyperparameter tuning
        7. Model Evaluation: Metrics, cross-validation, A/B testing, statistical significance, model interpretability
        8. Production ML: MLOps, model serving, monitoring, versioning, data pipelines, feature stores
        9. Ethics and Fairness: Bias detection, fairness metrics, responsible AI, privacy preservation, explainability
        10. Advanced Topics: Meta-learning, few-shot learning, continual learning, multi-modal learning, neural architecture search
        Include mathematical derivations, code implementations, practical examples, research papers summary, and industry applications.""",
        
        """Provide an encyclopedic overview of world history with extensive details:
        1. Ancient Civilizations: Mesopotamia, Egypt, Indus Valley, China, Greece, Rome - their rise, achievements, and fall
        2. Medieval Period: Feudalism, religious conflicts, trade routes, cultural exchanges, technological advances
        3. Renaissance and Reformation: Artistic achievements, scientific revolution, religious transformations, exploration age
        4. Age of Enlightenment: Philosophical movements, scientific discoveries, political theory, social changes
        5. Industrial Revolution: Technological innovations, urbanization, social impacts, global trade expansion
        6. Modern Era: World Wars, decolonization, Cold War, globalization, technological revolution
        7. Regional Histories: Detailed accounts of Asia, Africa, Americas, Europe, Oceania
        8. Thematic Studies: Economic history, social movements, scientific progress, artistic evolution
        9. Historical Figures: Biographies of influential leaders, thinkers, artists, scientists
        10. Contemporary History: Recent decades, current global challenges, emerging trends
        Include primary source analysis, historiographical debates, archaeological evidence, and cultural context.""",
        
        """Create a comprehensive medical encyclopedia covering human health and disease:
        1. Human Anatomy: Detailed descriptions of all organ systems, cellular biology, tissue types, developmental biology
        2. Physiology: Homeostasis, metabolic processes, endocrine system, nervous system, immune function
        3. Pathology: Disease mechanisms, inflammation, infection, cancer biology, genetic disorders
        4. Diagnostic Methods: Physical examination, laboratory tests, imaging techniques, molecular diagnostics
        5. Pharmacology: Drug mechanisms, pharmacokinetics, adverse effects, drug interactions, therapeutic monitoring
        6. Treatment Approaches: Surgical interventions, medical management, rehabilitation, preventive care
        7. Major Disease Categories: Cardiovascular, respiratory, gastrointestinal, neurological, infectious diseases
        8. Public Health: Epidemiology, health policy, preventive medicine, global health challenges
        9. Mental Health: Psychiatric disorders, psychotherapy, psychopharmacology, neuroscience of behavior
        10. Emerging Fields: Precision medicine, gene therapy, immunotherapy, regenerative medicine, digital health
        Include case studies, treatment protocols, evidence-based guidelines, and latest research findings."""
    ]
    
    # 推理任务
    REASONING = [
        "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning.",
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        "Three friends split a restaurant bill. The bill was $75. They each contributed $25, but the waiter realized there was a $5 discount. He gave them back $5, and they each took $1, giving the waiter a $2 tip. Now each friend paid $24, totaling $72, plus the $2 tip equals $74. Where did the extra dollar go?",
        "In a race, you overtake the person in second place. What position are you in now?",
        "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
    ]
    
    @classmethod
    def get_all_prompts(cls) -> Dict[str, List[str]]:
        """获取所有测试提示词"""
        return {
            'simple_qa': cls.SIMPLE_QA,
            'code_generation': cls.CODE_GENERATION,
            'creative_writing': cls.CREATIVE_WRITING,
            'long_form': cls.LONG_FORM,
            'ultra_long_form': cls.ULTRA_LONG_FORM,  # 新增
            'reasoning': cls.REASONING,
        }

# ==================== 性能测试客户端 ====================

class PerformanceTestClient:
    """性能测试客户端"""
    
    def __init__(self, config: TestConfig = TestConfig()):
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.BASE_URL,
            api_key=config.API_KEY,
            timeout=config.REQUEST_TIMEOUT
        )
    
    async def measure_streaming_performance(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        request_id: Optional[str] = None
    ) -> PerformanceMetrics:
        """测量流式响应性能"""
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        
        start_time = time.time()
        first_token_time = None
        chunks = []
        chunk_times = []
        chunk_sizes = []
        response_text = ""
        finish_reason = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in stream:
                current_time = time.time()
                
                if first_token_time is None:
                    first_token_time = current_time
                
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content = delta.content
                        response_text += content
                        chunks.append(content)
                        chunk_times.append((current_time - start_time) * 1000)
                        chunk_sizes.append(len(content))
                    
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                
                # 获取token使用情况
                if hasattr(chunk, 'usage') and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0
            
            end_time = time.time()
            
            # 如果没有获取到token数，进行估算
            if completion_tokens == 0:
                completion_tokens = len(response_text.split()) * 1.3  # 粗略估算
            if prompt_tokens == 0:
                prompt_tokens = len(prompt.split()) * 1.3
            
            ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
            total_time = (end_time - start_time) * 1000
            tokens_per_second = completion_tokens / (total_time / 1000) if total_time > 0 else 0
            
            return PerformanceMetrics(
                request_id=request_id,
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(prompt_tokens + completion_tokens),
                ttft=ttft,
                total_time=total_time,
                tokens_per_second=tokens_per_second,
                chunk_times=chunk_times,
                chunk_sizes=chunk_sizes,
                response_text=response_text,
                finish_reason=finish_reason,
                test_params={'max_tokens': max_tokens, 'temperature': temperature}
            )
            
        except Exception as e:
            logger.error(f"Error in streaming request {request_id}: {e}")
            return PerformanceMetrics(
                request_id=request_id,
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                ttft=0,
                total_time=0,
                tokens_per_second=0,
                error=str(e),
                test_params={'max_tokens': max_tokens, 'temperature': temperature}
            )
    
    async def measure_non_streaming_performance(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        request_id: Optional[str] = None
    ) -> PerformanceMetrics:
        """测量非流式响应性能"""
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            
            response_text = response.choices[0].message.content if response.choices else ""
            finish_reason = response.choices[0].finish_reason if response.choices else ""
            
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            
            tokens_per_second = completion_tokens / (total_time / 1000) if total_time > 0 else 0
            
            return PerformanceMetrics(
                request_id=request_id,
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                ttft=total_time,  # 对于非流式，TTFT等于总时间
                total_time=total_time,
                tokens_per_second=tokens_per_second,
                response_text=response_text,
                finish_reason=finish_reason,
                test_params={'max_tokens': max_tokens, 'temperature': temperature}
            )
            
        except Exception as e:
            logger.error(f"Error in non-streaming request {request_id}: {e}")
            return PerformanceMetrics(
                request_id=request_id,
                prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                ttft=0,
                total_time=0,
                tokens_per_second=0,
                error=str(e),
                test_params={'max_tokens': max_tokens, 'temperature': temperature}
            )
    
    async def run_concurrent_test(
        self,
        prompts: List[str],
        concurrent_requests: int,
        stream: bool = True,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> List[PerformanceMetrics]:
        """运行并发测试"""
        logger.info(f"Running {concurrent_requests} concurrent requests...")
        
        # 创建足够的任务
        tasks = []
        for i in range(concurrent_requests):
            prompt = prompts[i % len(prompts)]
            request_id = f"concurrent_{concurrent_requests}_{i}"
            
            if stream:
                task = self.measure_streaming_performance(
                    prompt, max_tokens, temperature, request_id
                )
            else:
                task = self.measure_non_streaming_performance(
                    prompt, max_tokens, temperature, request_id
                )
            tasks.append(task)
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        metrics = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed: {result}")
                metrics.append(PerformanceMetrics(
                    request_id=f"concurrent_{concurrent_requests}_{i}",
                    prompt="",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    ttft=0,
                    total_time=0,
                    tokens_per_second=0,
                    error=str(result)
                ))
            else:
                metrics.append(result)
        
        return metrics
    
    async def run_load_test(
        self,
        prompts: List[str],
        duration_seconds: int,
        requests_per_second: float,
        stream: bool = True,
        max_tokens: int = 2048
    ) -> List[PerformanceMetrics]:
        """运行负载测试"""
        logger.info(f"Running load test for {duration_seconds} seconds at {requests_per_second} RPS...")
        
        metrics = []
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            batch_start = time.time()
            
            # 发送一批请求
            prompt = prompts[request_count % len(prompts)]
            request_id = f"load_{request_count}"
            
            if stream:
                metric = await self.measure_streaming_performance(
                    prompt, max_tokens, request_id=request_id
                )
            else:
                metric = await self.measure_non_streaming_performance(
                    prompt, max_tokens, request_id=request_id
                )
            
            metrics.append(metric)
            request_count += 1
            
            # 控制请求速率
            elapsed = time.time() - batch_start
            sleep_time = (1.0 / requests_per_second) - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        logger.info(f"Load test completed. Sent {request_count} requests.")
        return metrics

# ==================== 测试运行器 ====================

class TestRunner:
    """测试运行器"""
    
    def __init__(self, config: TestConfig = TestConfig()):
        self.config = config
        self.client = PerformanceTestClient(config)
    
    async def run_comprehensive_test(self) -> Dict[str, TestResult]:
        """运行综合测试"""
        all_results = {}
        prompts_dict = TestPrompts.get_all_prompts()
        
        # 1. 基本功能测试（不同类型的提示词）
        logger.info("=" * 60)
        logger.info("Running basic functionality tests...")
        for prompt_type, prompts in prompts_dict.items():
            if prompt_type == 'ultra_long_form':  # 超长文本单独测试
                continue
                
            logger.info(f"Testing {prompt_type}...")
            
            # 流式测试
            stream_metrics = []
            for prompt in prompts[:3]:
                metric = await self.client.measure_streaming_performance(prompt)
                stream_metrics.append(metric)
                await asyncio.sleep(0.5)  # 避免过快请求
            
            # 非流式测试
            non_stream_metrics = []
            for prompt in prompts[:3]:
                metric = await self.client.measure_non_streaming_performance(prompt)
                non_stream_metrics.append(metric)
                await asyncio.sleep(0.5)
            
            all_results[f"{prompt_type}_stream"] = TestResult(
                test_name=f"{prompt_type}_stream",
                metrics=stream_metrics,
                config={'type': 'stream', 'prompt_type': prompt_type}
            )
            all_results[f"{prompt_type}_stream"].calculate_statistics()
            
            all_results[f"{prompt_type}_non_stream"] = TestResult(
                test_name=f"{prompt_type}_non_stream",
                metrics=non_stream_metrics,
                config={'type': 'non_stream', 'prompt_type': prompt_type}
            )
            all_results[f"{prompt_type}_non_stream"].calculate_statistics()
        
        # 2. 高并发测试 (10, 15, 20, 30, 50)
        logger.info("=" * 60)
        logger.info("Running HIGH CONCURRENCY tests...")
        high_concurrency_levels = [10, 15, 20, 30, 50]
        for concurrent_count in high_concurrency_levels:
            logger.info(f"Testing with {concurrent_count} CONCURRENT requests...")
            metrics = await self.client.run_concurrent_test(
                prompts=prompts_dict['simple_qa'],
                concurrent_requests=concurrent_count,
                stream=True
            )
            
            test_result = TestResult(
                test_name=f"concurrent_{concurrent_count}",
                metrics=metrics,
                config={'concurrent_requests': concurrent_count, 'type': 'high_concurrency'}
            )
            test_result.calculate_statistics()
            all_results[f"concurrent_{concurrent_count}"] = test_result
            
            # 打印即时结果
            logger.info(f"  Success rate: {test_result.success_rate:.2f}%")
            if test_result.throughput_stats:
                logger.info(f"  Avg throughput: {test_result.throughput_stats['mean']:.2f} tokens/s")
        
        # 3. 超长文本测试 (30k+ tokens)
        logger.info("=" * 60)
        logger.info("Running ULTRA LONG TEXT tests (30k+ tokens)...")
        ultra_long_tokens = [10240, 20480, 32768]  # 目标生成的token数
        
        for max_tokens in ultra_long_tokens:
            logger.info(f"Testing ULTRA LONG generation with max_tokens={max_tokens}...")
            metrics = []
            
            # 使用超长提示词
            for prompt in prompts_dict['ultra_long_form'][:2]:
                logger.info(f"  Starting ultra-long generation (target: {max_tokens} tokens)...")
                metric = await self.client.measure_streaming_performance(
                    prompt, 
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                metrics.append(metric)
                
                if metric.error is None:
                    logger.info(f"  ✓ Completed: {metric.completion_tokens} tokens in {metric.total_time/1000:.2f}s")
                    logger.info(f"    Throughput: {metric.tokens_per_second:.2f} tokens/s")
                    logger.info(f"    TTFT: {metric.ttft:.2f}ms")
                else:
                    logger.error(f"  ✗ Failed: {metric.error}")
                
                await asyncio.sleep(2)  # 超长文本之间等待更长时间
            
            test_result = TestResult(
                test_name=f"ultra_long_{max_tokens}",
                metrics=metrics,
                config={
                    'max_tokens': max_tokens, 
                    'type': 'ultra_long_text',
                    'target_tokens': '30k+'
                }
            )
            test_result.calculate_statistics()
            all_results[f"ultra_long_{max_tokens}"] = test_result
        
        # 4. 混合负载测试：高并发 + 长文本
        logger.info("=" * 60)
        logger.info("Running MIXED LOAD test (concurrent + long text)...")
        mixed_prompts = prompts_dict['simple_qa'][:3] + prompts_dict['long_form'][:2]
        metrics = await self.client.run_concurrent_test(
            prompts=mixed_prompts,
            concurrent_requests=15,
            stream=True,
            max_tokens=4096
        )
        
        mixed_result = TestResult(
            test_name="mixed_load_test",
            metrics=metrics,
            config={
                'concurrent_requests': 15,
                'max_tokens': 4096,
                'type': 'mixed_load'
            }
        )
        mixed_result.calculate_statistics()
        all_results["mixed_load_test"] = mixed_result
        
        # 5. 稳定性测试：持续负载
        logger.info("=" * 60)
        logger.info("Running STABILITY test (sustained load)...")
        stability_metrics = await self.client.run_load_test(
            prompts=prompts_dict['simple_qa'],
            duration_seconds=60,  # 1分钟持续测试
            requests_per_second=3.0,
            stream=True
        )
        
        stability_result = TestResult(
            test_name="stability_test",
            metrics=stability_metrics,
            config={
                'duration': 60, 
                'rps': 3.0,
                'type': 'stability'
            }
        )
        stability_result.calculate_statistics()
        all_results["stability_test"] = stability_result
        
        return all_results
    
    def generate_report(self, results: Dict[str, TestResult]) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 80)
        report.append("QWEN MODEL PERFORMANCE TEST REPORT - ENHANCED")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # 分类显示结果
        categories = {
            'High Concurrency Tests': [],
            'Ultra Long Text Tests (30k+ tokens)': [],
            'Mixed Load Tests': [],
            'Stability Tests': [],
            'Basic Functionality Tests': []
        }
        
        for test_name, test_result in results.items():
            config_type = test_result.config.get('type', 'basic')
            
            if config_type == 'high_concurrency' or 'concurrent_' in test_name:
                categories['High Concurrency Tests'].append((test_name, test_result))
            elif config_type == 'ultra_long_text':
                categories['Ultra Long Text Tests (30k+ tokens)'].append((test_name, test_result))
            elif config_type == 'mixed_load':
                categories['Mixed Load Tests'].append((test_name, test_result))
            elif config_type == 'stability':
                categories['Stability Tests'].append((test_name, test_result))
            else:
                categories['Basic Functionality Tests'].append((test_name, test_result))
        
        for category, tests in categories.items():
            if not tests:
                continue
                
            report.append(f"\n{'#' * 80}")
            report.append(f"# {category}")
            report.append(f"{'#' * 80}")
            
            for test_name, test_result in tests:
                report.append(f"\n## Test: {test_name}")
                report.append("-" * 40)
                
                if test_result.config:
                    report.append(f"Config: {json.dumps(test_result.config, indent=2)}")
                
                report.append(f"Total Requests: {len(test_result.metrics)}")
                report.append(f"Success Rate: {test_result.success_rate:.2f}%")
                report.append(f"Error Count: {test_result.error_count}")
                
                # 显示实际生成的token统计
                valid_metrics = [m for m in test_result.metrics if m.error is None]
                if valid_metrics:
                    total_completion = sum(m.completion_tokens for m in valid_metrics)
                    avg_completion = total_completion / len(valid_metrics)
                    max_completion = max(m.completion_tokens for m in valid_metrics)
                    report.append(f"Avg Completion Tokens: {avg_completion:.0f}")
                    report.append(f"Max Completion Tokens: {max_completion}")
                
                if test_result.ttft_stats:
                    report.append("\n### TTFT (Time to First Token) - milliseconds")
                    for key, value in test_result.ttft_stats.items():
                        report.append(f"  {key}: {value:.2f} ms")
                
                if test_result.latency_stats:
                    report.append("\n### Total Latency - milliseconds")
                    for key, value in test_result.latency_stats.items():
                        report.append(f"  {key}: {value:.2f} ms")
                
                if test_result.throughput_stats:
                    report.append("\n### Throughput - tokens/second")
                    for key, value in test_result.throughput_stats.items():
                        report.append(f"  {key}: {value:.2f} tokens/s")
                
                report.append("")
        
        return "\n".join(report)
    
    def save_results(self, results: Dict[str, TestResult], output_dir: str = "./test_results"):
        """保存测试结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存详细JSON结果
        json_path = f"{output_dir}/results_enhanced_{timestamp}.json"
        with open(json_path, 'w') as f:
            # 转换为可序列化的格式
            serializable_results = {}
            for key, test_result in results.items():
                serializable_results[key] = {
                    'test_name': test_result.test_name,
                    'config': test_result.config,
                    'success_rate': test_result.success_rate,
                    'error_count': test_result.error_count,
                    'ttft_stats': test_result.ttft_stats,
                    'latency_stats': test_result.latency_stats,
                    'throughput_stats': test_result.throughput_stats,
                    'metrics_count': len(test_result.metrics)
                }
            json.dump(serializable_results, f, indent=2)
        
        # 保存文本报告
        report_path = f"{output_dir}/report_enhanced_{timestamp}.txt"
        with open(report_path, 'w') as f:
            f.write(self.generate_report(results))
        
        # 保存CSV格式的详细指标
        csv_path = f"{output_dir}/metrics_enhanced_{timestamp}.csv"
        all_metrics = []
        for test_name, test_result in results.items():
            for metric in test_result.metrics:
                if metric.error is None:
                    all_metrics.append({
                        'test_name': test_name,
                        'test_type': test_result.config.get('type', 'basic'),
                        'ttft': metric.ttft,
                        'total_time': metric.total_time,
                        'tokens_per_second': metric.tokens_per_second,
                        'prompt_tokens': metric.prompt_tokens,
                        'completion_tokens': metric.completion_tokens,
                        'total_tokens': metric.total_tokens,
                        'finish_reason': metric.finish_reason
                    })
        
        if all_metrics:
            df = pd.DataFrame(all_metrics)
            df.to_csv(csv_path, index=False)
        
        logger.info(f"Results saved to {output_dir}/")
        return {
            'json': json_path,
            'report': report_path,
            'csv': csv_path
        }

# ==================== 主函数 ====================

async def main():
    """主测试函数"""
    runner = TestRunner()
    
    try:
        logger.info("Starting Qwen model ENHANCED performance tests...")
        logger.info("Tests include: 10+ concurrency and 30k+ token generation")
        results = await runner.run_comprehensive_test()
        
        # 打印报告
        print("\n" + runner.generate_report(results))
        
        # 保存结果
        saved_files = runner.save_results(results)
        logger.info(f"Test completed. Results saved to: {saved_files}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())