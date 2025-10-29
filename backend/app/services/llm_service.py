from typing import Dict, Any, Optional, List
import logging
import uuid
import time
import numpy as np
import asyncio
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

# 条件导入火山引擎SDK
try:
    # 只导入必要的Ark模块
    from volcenginesdkarkruntime import Ark
    HAS_VOLC_SDK = True
    HAS_EMBEDDING_SDK = True  # 使用Ark客户端的embeddings方法，不需要单独导入
    logger.info("火山引擎SDK导入成功")
except ImportError as e:
    HAS_VOLC_SDK = False
    HAS_EMBEDDING_SDK = False
    logger.info(f"火山引擎SDK导入失败: {str(e)}，将使用HTTP API")

# 尝试导入requests用于HTTP请求
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests库未安装，无法使用HTTP请求")


class VolcLLMService:
    """火山引擎LLM服务封装"""
    
    def __init__(self):
        self.client = None
        self.embeddings_client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """初始化火山引擎客户端（使用单一连接）"""
        try:
            # 无论SDK是否可用，都确保客户端已初始化
            if HAS_VOLC_SDK:
                # 创建单一客户端实例（只使用API密钥）
                self.client = Ark(
                    api_key=settings.volcengine_api_key
                )
                logger.info(f"火山引擎SDK客户端初始化成功，模型: {settings.volcengine_model}")
            else:
                # 当SDK不可用时，设置一个标志而不是模拟客户端
                self.client = "http_api_client"
                logger.info("使用HTTP API模式初始化客户端")
            
            # 对于embeddings，我们将使用主客户端的embeddings方法
            if HAS_VOLC_SDK:
                # 直接使用主客户端的embeddings功能，不需要单独的embeddings客户端
                logger.info("火山引擎embeddings功能初始化完成")
            else:
                # 当SDK不可用时，设置一个标志表示使用HTTP API
                self.embeddings_client = "http_api_client"
                logger.info("使用HTTP API模式初始化embeddings功能")
                
        except Exception as e:
            logger.error(f"火山引擎客户端初始化失败: {str(e)}")
            # 设置为HTTP API模式，而不是抛出异常
            self.client = "http_api_client"
            self.embeddings_client = "http_api_client"
            logger.info("降级到HTTP API模式")
    
    def generate(self, prompt: str, 
                 system_prompt: Optional[str] = None,
                 max_tokens: int = 2048,
                 temperature: float = 0.7,
                 top_p: float = 0.95,
                 **kwargs) -> str:
        """生成文本响应
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            max_tokens: 最大令牌数
            temperature: 温度参数
            top_p: 核采样参数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        # 确保客户端已初始化，如果未初始化则使用HTTP API模式
        if self.client is None:
            self.client = "http_api_client"
            logger.info("客户端未初始化，使用HTTP API模式")
        
        try:
            # 准备消息列表
            messages = []
            
            # 添加系统提示（如果有）
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 添加用户提示
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 根据客户端类型选择不同的调用方式
            if self.client == "http_api_client":
                # 使用HTTP API调用
                if not HAS_REQUESTS:
                    logger.error("requests库未安装，无法使用HTTP API")
                    raise ImportError("请安装requests库: pip install requests")
                
                headers = {
                    "Authorization": f"Bearer {settings.volcengine_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # 使用配置中的完整URL，不再进行拼接
                url = f"{settings.volcengine_region}/chat/completions"
                
                data = {
                    "model": settings.volcengine_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    **kwargs
                }
                
                logger.info(f"使用HTTP API调用LLM: {url}")
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=60  # 增加超时时间以适应较长的生成过程
                )
                
                response.raise_for_status()  # 检查HTTP错误
                result = response.json()
                
                if "choices" in result and result["choices"] and "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                    generated_text = result["choices"][0]["message"]["content"]
                    logger.info(f"HTTP API LLM生成成功，输入长度: {len(prompt)}，输出长度: {len(generated_text)}")
                    return generated_text
                else:
                    raise ValueError(f"Invalid LLM response structure: {result}")
            else:
                # 使用SDK调用
                response = self.client.chat.completions.create(
                    model=settings.volcengine_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    **kwargs
                )
                
                # 提取生成的文本
                generated_text = response.choices[0].message.content
                logger.info(f"SDK LLM生成成功，输入长度: {len(prompt)}，输出长度: {len(generated_text)}")
                return generated_text
            
        except Exception as e:
            logger.error(f"LLM生成失败: {str(e)}")
            raise
    
    async def generate_async(self, prompt: str, 
                           system_prompt: Optional[str] = None,
                           max_tokens: int = 2048,
                           temperature: float = 0.7,
                           top_p: float = 0.95,
                           **kwargs) -> str:
        """异步生成文本响应
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            max_tokens: 最大令牌数
            temperature: 温度参数
            top_p: 核采样参数
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        # 确保客户端已初始化，如果未初始化则使用HTTP API模式
        if self.client is None:
            self.client = "http_api_client"
            logger.info("客户端未初始化，使用HTTP API模式")
        
        try:
            # 准备消息列表
            messages = []
            
            # 添加系统提示（如果有）
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 添加用户提示
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 对于异步生成，我们需要使用线程池来执行同步操作
            loop = asyncio.get_event_loop()
            
            # 根据客户端类型选择不同的调用方式
            if self.client == "http_api_client":
                # 使用HTTP API调用
                if not HAS_REQUESTS:
                    logger.error("requests库未安装，无法使用HTTP API")
                    raise ImportError("请安装requests库: pip install requests")
                
                # 定义HTTP API调用函数
                def http_api_call():
                    headers = {
                        "Authorization": f"Bearer {settings.volcengine_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    # 使用配置中的完整URL，不再进行拼接
                    url = f"{settings.volcengine_region}/chat/completions"
                    
                    data = {
                        "model": settings.volcengine_model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                        **kwargs
                    }
                    
                    logger.info(f"异步使用HTTP API调用LLM: {url}")
                    response = requests.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=60
                    )
                    
                    response.raise_for_status()
                    return response.json()
                
                # 执行HTTP API调用
                result = await loop.run_in_executor(None, http_api_call)
                
                if "choices" in result and result["choices"] and "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                    generated_text = result["choices"][0]["message"]["content"]
                    logger.info(f"异步HTTP API LLM生成成功，输入长度: {len(prompt)}，输出长度: {len(generated_text)}")
                    return generated_text
                else:
                    raise ValueError(f"Invalid LLM response structure: {result}")
            else:
                # 使用SDK调用
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=settings.volcengine_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        **kwargs
                    )
                )
                
                # 提取生成的文本
                generated_text = response.choices[0].message.content
                logger.info(f"异步SDK LLM生成成功，输入长度: {len(prompt)}，输出长度: {len(generated_text)}")
                return generated_text
            
        except Exception as e:
            logger.error(f"异步LLM生成失败: {str(e)}")
            raise
    
    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """生成文本摘要
        
        Args:
            content: 要摘要的内容
            max_length: 摘要最大长度
            
        Returns:
            摘要文本
        """
        system_prompt = f"""你是一个专业的内容摘要助手。
请对提供的内容生成一个简洁、准确的摘要，保留关键信息和要点。
摘要长度不超过{max_length}字。"""
        
        prompt = f"""请对以下内容生成摘要：

{content}

摘要："""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_length + 100,
            temperature=0.3
        )
    
    def answer_question(self, content: str, question: str) -> str:
        """基于内容回答问题
        
        Args:
            content: 参考内容
            question: 用户问题
            
        Returns:
            回答
        """
        system_prompt = """你是一个专业的问答助手。
请严格基于提供的参考内容回答用户问题，不要添加额外信息。
如果参考内容中没有相关信息，请明确表示不知道。
回答要准确、简洁、清晰。"""
        
        prompt = f"""参考内容：

{content}

用户问题：{question}

回答："""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.3
        )
    
    def generate_video_outline(self, srt_content: str) -> Dict[str, Any]:
        """根据SRT字幕内容生成视频大纲
        
        Args:
            srt_content: SRT格式的字幕内容
            
        Returns:
            结构化的视频大纲，包含主要章节、子章节和时间戳
        """
        system_prompt = """你是一个专业的视频内容分析专家。
请基于提供的SRT字幕内容，生成一个详细的视频大纲。
大纲应该包含主要章节和子章节，并提供每个章节对应的时间戳。

输出格式必须是严格的JSON格式，包含以下结构：
{
    "title": "视频标题",
    "main_sections": [
        {
            "title": "主要章节1标题",
            "summary": "主要章节1的简短总结",
            "start_time": "00:00:00",
            "end_time": "00:10:30",
            "subsections": [
                {
                    "title": "子章节1.1标题",
                    "content": "子章节1.1的详细内容摘要",
                    "start_time": "00:00:00",
                    "end_time": "00:05:15"
                }
            ]
        }
    ],
    "video_duration": "01:20:45"
}
"""
        
        prompt = f"""请基于以下SRT字幕内容，生成一个详细的视频大纲：

{srt_content}

请按照要求的JSON格式输出完整的视频大纲，确保包含正确的时间戳。"""
        
        try:
            outline_text = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=3000,
                temperature=0.3
            )
            
            if '{' in outline_text and '}' in outline_text:
                json_start = outline_text.find('{')
                json_end = outline_text.rfind('}') + 1
                json_content = outline_text[json_start:json_end]
                
                try:
                    outline_data = json.loads(json_content)
                    logger.info(f"视频大纲生成成功，包含 {len(outline_data.get('main_sections', []))} 个主要章节")
                    return outline_data
                except json.JSONDecodeError:
                    logger.error("解析生成的大纲JSON失败")
                    return {
                        "title": "视频内容大纲",
                        "main_sections": [
                            {
                                "title": "章节1",
                                "summary": "基于字幕分析的内容总结",
                                "start_time": "00:00:00",
                                "end_time": "未知",
                                "subsections": []
                            }
                        ],
                        "video_duration": "未知"
                    }
            else:
                logger.warning("生成的大纲不是JSON格式")
                return {
                    "title": "视频内容大纲",
                    "main_sections": [
                        {
                            "title": "内容概览",
                            "summary": outline_text[:200] + "...",
                            "start_time": "00:00:00",
                            "end_time": "未知",
                            "subsections": []
                        }
                    ],
                    "video_duration": "未知"
                }
                
        except Exception as e:
            logger.error(f"生成视频大纲失败: {str(e)}")
            return {
                "title": "视频内容大纲",
                "main_sections": [],
                "video_duration": "未知"
            }
    
    def generate_embedding(self, text: str, retry_attempts: int = 3, retry_delay: int = 1, detect_network_error: bool = False) -> List[float]:
        """生成文本嵌入向量，使用火山引擎专门的embedding API
        
        Args:
            text: 输入文本
            retry_attempts: 重试次数
            retry_delay: 初始重试延迟（秒）
            
        Returns:
            向量表示
        """
        # 确保embeddings客户端已初始化，如果未初始化则使用HTTP API模式
        if self.embeddings_client is None:
            self.embeddings_client = "http_api_client"
            logger.info("embeddings客户端未初始化，使用HTTP API模式")
        
        # 清理文本，移除多余的空白字符
        text = text.strip()
        if not text:
            logger.warning("尝试对空文本生成embedding")
            return list(np.zeros(settings.milvus_dim))
        
        for attempt in range(retry_attempts):
            try:
                # 检查是否需要使用HTTP API
                if self.embeddings_client == "http_api_client" or not (HAS_EMBEDDING_SDK and self.embeddings_client):
                    # 优先使用HTTP请求调用embedding API
                    if not HAS_REQUESTS:
                        logger.error("requests库未安装，无法使用HTTP API")
                        raise ImportError("请安装requests库: pip install requests")
                    
                    headers = {
                        "Authorization": f"Bearer {settings.volcengine_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    # 使用配置中的完整URL，不再进行拼接
                    url = f"{settings.volcengine_region}/embeddings"
                    
                    data = {
                        "model": settings.volcengine_embedding_model,
                        "input": text
                    }
                    
                    logger.info(f"使用HTTP请求调用embedding API: {url}")
                    response = requests.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=30
                    )
                    
                    response.raise_for_status()  # 检查HTTP错误
                    result = response.json()
                    
                    if "data" in result and result["data"] and "embedding" in result["data"][0]:
                        embedding = result["data"][0]["embedding"]
                        logger.info(f"使用HTTP请求成功生成embedding，维度: {len(embedding)}")
                        return embedding
                    else:
                        raise ValueError(f"Invalid embedding response structure: {result}")
                else:
                    # 使用主客户端的embeddings方法
                    response = self.client.embeddings.create(
                        model=settings.volcengine_embedding_model,
                        input=[text]  # 确保输入是列表格式
                    )
                    embedding = response.data[0].embedding
                    logger.info(f"使用SDK成功生成embedding，维度: {len(embedding)}")
                    return embedding
                    
            except Exception as e:
                logger.error(f"生成embedding失败 (尝试 {attempt + 1}/{retry_attempts}): {str(e)}")
                if attempt < retry_attempts - 1:
                    # 指数退避重试
                    delay = retry_delay * (2 ** attempt)
                    logger.info(f"将在 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error("所有重试都失败")
                    raise  # 抛出最后一次异常而不是返回模拟向量
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        # 确保客户端已初始化，如果未初始化则使用HTTP API模式
        if self.client is None:
            self.client = "http_api_client"
            logger.info("客户端未初始化，使用HTTP API模式")
        
        embeddings = []
        
        # 处理所有文本
        for i, text in enumerate(texts, 1):
            try:
                logger.info(f"正在生成第 {i}/{len(texts)} 个文本的embedding")
                # 正常调用API，使用HTTP API或SDK
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
                
                # 添加短暂延迟避免API限流
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"生成第 {i} 个文本的embedding失败: {str(e)}")
                raise  # 抛出异常而不是使用模拟向量
        
        logger.info(f"批量embedding生成完成，共处理 {len(embeddings)}/{len(texts)} 个文本")
        return embeddings
    
    def analyze_video_content(self, transcript: str) -> Dict[str, Any]:
        """分析视频内容，提取关键信息
        
        Args:
            transcript: 视频字幕文本
            
        Returns:
            分析结果，包含主题、关键论点、时间点等
        """
        system_prompt = """你是一个专业的视频内容分析师。
请对提供的视频字幕文本进行全面分析，提取关键信息。"""
        
        prompt = f"""请分析以下视频字幕内容，提供：
1. 视频的主题和主要内容
2. 3-5个关键要点
3. 讨论的主要话题和时间分布
4. 任何重要的结论或建议

字幕内容：
{transcript}

分析结果："""
        
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.3
        )
        
        # 解析结果
        try:
            # 尝试JSON解析，如果模型输出JSON格式
            if response.strip().startswith('{') and response.strip().endswith('}'):
                return json.loads(response)
            else:
                # 否则返回文本格式
                return {"analysis": response}
        except json.JSONDecodeError:
            return {"analysis": response}


# 创建全局LLM服务实例
llm_service = VolcLLMService()