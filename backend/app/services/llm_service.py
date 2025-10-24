from typing import Dict, Any, Optional, List
import logging
import uuid
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

# 条件导入火山引擎SDK
try:
    # 只导入必要的Ark模块，不再依赖volcenginesdkcore
    from volcenginesdkarkruntime import Ark
    HAS_VOLC_SDK = True
    logger.info("火山引擎SDK导入成功")
except ImportError as e:
    HAS_VOLC_SDK = False
    logger.warning(f"火山引擎SDK导入失败: {str(e)}，LLM功能将使用模拟模式")


class VolcLLMService:
    """火山引擎LLM服务封装"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """初始化火山引擎客户端"""
        try:
            if not HAS_VOLC_SDK:
                logger.warning("火山引擎SDK不可用，使用模拟模式")
                self.client = "mock_client"
                return
                
            # 创建客户端 - 使用官方推荐方式
            self.client = Ark(
                api_key=settings.volcengine_api_key,
            )
            
            logger.info(f"火山引擎LLM客户端初始化成功，模型: {settings.volcengine_model}")
        except Exception as e:
            logger.error(f"火山引擎LLM客户端初始化失败: {str(e)}")
            # 初始化失败时使用模拟客户端
            logger.warning("使用模拟客户端")
            self.client = "mock_client"
    
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
        # 模拟模式
        if self.client == "mock_client":
            mock_response = f"[模拟模式] 您的请求已收到: {prompt[:50]}..."
            if system_prompt:
                mock_response += f"\n系统提示: {system_prompt[:30]}..."
            logger.info(f"使用模拟LLM响应，输入长度: {len(prompt)}")
            return mock_response
            
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 调用API
            response = self.client.chat.completions.create(
                model=settings.volcengine_model,
                # 添加自定义请求ID
                extra_headers={"X-Client-Request-Id": f"quickrewind-{uuid.uuid4()}"},
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            
            # 提取结果
            content = response.choices[0].message.content
            logger.info(f"LLM生成成功，输入长度: {len(prompt)}, 输出长度: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"LLM生成失败: {str(e)}")
            # 返回模拟响应
            return f"[错误恢复模式] 无法连接到LLM服务: {str(e)}"
    
    async def generate_async(self, prompt: str, 
                           system_prompt: Optional[str] = None,
                           max_tokens: int = 2048,
                           temperature: float = 0.7,
                           top_p: float = 0.95,
                           **kwargs) -> str:
        """异步生成文本响应"""
        # 注意：火山引擎SDK可能不支持异步，这里使用同步调用包装
        # 实际项目中可以使用线程池或其他异步方案
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            **kwargs
        )
    
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
    
    def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量表示
        """
        try:
            # 注意：火山引擎可能有专门的嵌入模型API
            # 这里使用通用方法，实际项目中应使用专门的嵌入API
            system_prompt = """你是一个文本嵌入生成器。
请将输入文本转换为固定维度的向量表示。
输出格式应为JSON数组，包含768个浮点数。"""
            
            prompt = f"""请生成以下文本的嵌入向量：

{text}

嵌入向量："""
            
            response = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=settings.milvus_dim * 8,  # 预估的token数
                temperature=0.0
            )
            
            # 解析JSON响应
            embedding = json.loads(response)
            
            # 确保维度正确
            if len(embedding) != settings.milvus_dim:
                logger.warning(f"嵌入向量维度不正确: {len(embedding)}，期望: {settings.milvus_dim}")
                # 截断或填充到指定维度
                if len(embedding) > settings.milvus_dim:
                    embedding = embedding[:settings.milvus_dim]
                else:
                    embedding += [0.0] * (settings.milvus_dim - len(embedding))
            
            return embedding
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {str(e)}")
            raise
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
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