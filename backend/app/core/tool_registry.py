"""
工具注册表

该模块负责将项目中的各种服务封装为MCP兼容的工具，并统一注册到MCP服务器。
通过这个注册表，Agent可以发现和调用系统中所有可用的工具。
"""

import logging
from typing import Dict, Any
import asyncio

from app.core.mcp import (
    mcp_server, 
    tool, 
    ToolParameter,
    ToolDefinition,
    ToolResponse
)
from app.services.speech_recognition import speech_recognizer
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


# 语音识别工具封装
@tool(
    name="transcribe_audio",
    description="将音频文件转换为文本",
    parameters=[
        ToolParameter(
            name="audio_path",
            type="string",
            description="音频文件路径",
            required=True
        ),
        ToolParameter(
            name="engine",
            type="string",
            description="语音识别引擎: whisper 或 funasr",
            required=False,
            default="funasr"
        ),
        ToolParameter(
            name="model_name",
            type="string",
            description="模型名称/大小: 对于whisper可选(tiny/base/small/medium/large)，对于funasr可选(paraformer-zh等)",
            required=False,
            default=None
        ),
        ToolParameter(
            name="batch_size_s",
            type="number",
            description="批处理大小（秒），仅FunASR引擎使用",
            required=False,
            default=300
        ),
        ToolParameter(
            name="output_dir",
            type="string",
            description="输出目录",
            required=False,
            default=None
        ),
        ToolParameter(
            name="language",
            type="string",
            description="语言代码，仅Whisper引擎使用",
            required=False,
            default="zh"
        ),
        ToolParameter(
            name="force_cpu",
            type="boolean",
            description="是否强制使用CPU运行模型，设置为true可在无GPU环境中运行",
            required=False,
            default=False
        )
    ],
    returns={
        "text": "识别出的完整文本",
        "segments": "包含时间戳的识别段落",
        "total_segments": "段落总数",
        "engine": "使用的语音识别引擎",
        "model": "使用的模型名称"
    },
    tags=["audio", "speech", "transcription"]
)
async def transcribe_audio_tool(audio_path: str, engine: str = "funasr", model_name: str = None, 
                              batch_size_s: int = 300, output_dir: str = None, 
                              language: str = "zh", force_cpu: bool = False) -> Dict[str, Any]:
    """MCP工具：音频转文本
    
    将语音识别服务封装为MCP兼容的异步工具，支持选择不同的语音识别引擎和模型
    
    Args:
        audio_path: 音频文件路径
        engine: 语音识别引擎，可选 'whisper' 或 'funasr'
        model_name: 模型名称/大小，根据引擎不同有不同选项
        batch_size_s: 批处理大小（秒），仅FunASR使用
        output_dir: 输出目录
        language: 语言代码，仅Whisper引擎使用
        force_cpu: 是否强制使用CPU运行模型
    
    Returns:
        包含识别文本和时间戳的结构化结果
    """
    # 使用线程池执行同步操作，避免阻塞事件循环
    loop = asyncio.get_running_loop()
    
    # 根据参数调用相应的语音识别功能
    # 如果指定了不同的引擎，需要创建新的识别器实例
    if engine != speech_recognizer.engine or (model_name and model_name != speech_recognizer.model_name):
        # 创建新的识别器实例
        from app.services.speech_recognition import SpeechRecognizer
        recognizer = SpeechRecognizer(engine=engine, model_name=model_name, force_cpu=force_cpu)
        
        # 根据引擎类型传递相应参数
        if engine == "whisper":
            result = await loop.run_in_executor(
                None, 
                lambda: recognizer.transcribe(audio_path, language=language)
            )
        else:
            result = await loop.run_in_executor(
                None, 
                lambda: recognizer.transcribe(audio_path, batch_size_s=batch_size_s, output_dir=output_dir)
            )
    else:
        # 如果需要强制使用CPU，但当前识别器没有设置该选项，则创建新实例
        if force_cpu and not hasattr(speech_recognizer, 'force_cpu') or speech_recognizer.force_cpu != force_cpu:
            from app.services.speech_recognition import SpeechRecognizer
            recognizer = SpeechRecognizer(engine=engine, model_name=speech_recognizer.model_name, force_cpu=force_cpu)
            if engine == "whisper":
                result = await loop.run_in_executor(
                    None, 
                    lambda: recognizer.transcribe(audio_path, language=language)
                )
            else:
                result = await loop.run_in_executor(
                    None, 
                    lambda: recognizer.transcribe(audio_path, batch_size_s=batch_size_s, output_dir=output_dir)
                )
        else:
            # 使用全局识别器实例
            if engine == "whisper":
                result = await loop.run_in_executor(
                    None, 
                    lambda: speech_recognizer.transcribe(audio_path, language=language)
                )
            else:
                result = await loop.run_in_executor(
                    None, 
                    lambda: speech_recognizer.transcribe(audio_path, batch_size_s=batch_size_s, output_dir=output_dir)
                )
    
    return result


@tool(
    name="generate_srt",
    description="生成SRT格式字幕",
    parameters=[
        ToolParameter(
            name="recognition_result",
            type="object",
            description="语音识别结果",
            required=True
        ),
        ToolParameter(
            name="output_path",
            type="string",
            description="输出文件路径",
            required=False,
            default=None
        )
    ],
    returns={
        "srt_content": "SRT格式的字幕内容"
    },
    tags=["audio", "subtitles", "srt"]
)
async def generate_srt_tool(recognition_result: Dict[str, Any], output_path: str = None) -> str:
    """
    MCP工具：生成SRT字幕
    
    将字幕生成功能封装为MCP兼容的异步工具
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: speech_recognizer.generate_srt(recognition_result, output_path)
    )
    return result


# LLM服务工具封装
@tool(
    name="generate_text",
    description="使用大语言模型生成文本",
    parameters=[
        ToolParameter(
            name="prompt",
            type="string",
            description="用户提示词",
            required=True
        ),
        ToolParameter(
            name="system_prompt",
            type="string",
            description="系统提示词",
            required=False,
            default=None
        ),
        ToolParameter(
            name="max_tokens",
            type="number",
            description="最大生成令牌数",
            required=False,
            default=2048
        ),
        ToolParameter(
            name="temperature",
            type="number",
            description="生成温度，控制随机性",
            required=False,
            default=0.7
        ),
        ToolParameter(
            name="top_p",
            type="number",
            description="核采样参数",
            required=False,
            default=0.95
        )
    ],
    returns={
        "text": "生成的文本内容"
    },
    tags=["llm", "generation", "text"]
)
async def generate_text_tool(
    prompt: str, 
    system_prompt: str = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.95
) -> str:
    """
    MCP工具：文本生成
    
    将LLM文本生成功能封装为MCP兼容的异步工具
    """
    return await llm_service.generate_async(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
    )


@tool(
    name="generate_summary",
    description="生成文本摘要",
    parameters=[
        ToolParameter(
            name="content",
            type="string",
            description="要摘要的内容",
            required=True
        ),
        ToolParameter(
            name="max_length",
            type="number",
            description="摘要最大长度",
            required=False,
            default=500
        )
    ],
    returns={
        "summary": "生成的摘要"
    },
    tags=["llm", "summary", "content"]
)
async def generate_summary_tool(content: str, max_length: int = 500) -> str:
    """
    MCP工具：文本摘要
    
    将文本摘要功能封装为MCP兼容的异步工具
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: llm_service.generate_summary(content, max_length)
    )
    return result


@tool(
    name="answer_question",
    description="基于内容回答问题",
    parameters=[
        ToolParameter(
            name="content",
            type="string",
            description="参考内容",
            required=True
        ),
        ToolParameter(
            name="question",
            type="string",
            description="用户问题",
            required=True
        )
    ],
    returns={
        "answer": "回答内容"
    },
    tags=["llm", "qa", "question_answering"]
)
async def answer_question_tool(content: str, question: str) -> str:
    """
    MCP工具：问答
    
    将问答功能封装为MCP兼容的异步工具
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: llm_service.answer_question(content, question)
    )
    return result


@tool(
    name="analyze_video_content",
    description="分析视频内容，提取关键信息",
    parameters=[
        ToolParameter(
            name="transcript",
            type="string",
            description="视频字幕文本",
            required=True
        )
    ],
    returns={
        "analysis": "分析结果",
        "topics": "主题",
        "key_points": "关键要点"
    },
    tags=["llm", "video", "analysis"]
)
async def analyze_video_content_tool(transcript: str) -> Dict[str, Any]:
    """
    MCP工具：视频内容分析
    
    将视频内容分析功能封装为MCP兼容的异步工具
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: llm_service.analyze_video_content(transcript)
    )
    return result


# 实用工具封装
@tool(
    name="get_available_tools",
    description="获取所有可用的MCP工具",
    parameters=[],
    returns={
        "tools": "可用工具列表"
    },
    tags=["mcp", "system", "tools"]
)
async def get_available_tools_tool() -> Dict[str, Any]:
    """
    MCP工具：获取可用工具
    
    返回系统中所有已注册的MCP工具信息
    """
    tools = mcp_server.get_available_tools()
    # 转换为可序列化的格式
    tools_dict = [tool.model_dump() for tool in tools]
    return {"tools": tools_dict}


# 注册系统级资源
def register_system_resources():
    """
    注册系统级资源到MCP服务器
    """
    # 注册服务实例作为资源
    mcp_server.register_resource("speech_recognizer", speech_recognizer)
    mcp_server.register_resource("llm_service", llm_service)
    logger.info("System resources registered to MCP server")


# 注册提示词模板
def register_prompt_templates():
    """
    注册常用提示词模板到MCP服务器
    """
    # 视频内容分析模板
    video_analysis_template = """
你是一个专业的视频内容分析师。
请对提供的视频字幕文本进行全面分析，提取关键信息。

分析要求：
1. 视频的主题和主要内容
2. 3-5个关键要点
3. 讨论的主要话题和时间分布
4. 任何重要的结论或建议

字幕内容：
{transcript}

请以JSON格式输出分析结果，包含以下字段：
- topic: 主题
- main_content: 主要内容
- key_points: 关键要点列表
- discussion_topics: 讨论的主题及其时间分布
- conclusions: 结论或建议
"""
    
    # 文本摘要模板
    summary_template = """
你是一个专业的内容摘要助手。
请对提供的内容生成一个简洁、准确的摘要，保留关键信息和要点。

摘要长度要求：不超过{max_length}字。

内容：
{content}

摘要：
"""
    
    # 问答模板
    qa_template = """
你是一个专业的问答助手。
请严格基于提供的参考内容回答用户问题，不要添加额外信息。
如果参考内容中没有相关信息，请明确表示不知道。
回答要准确、简洁、清晰。

参考内容：
{content}

用户问题：{question}

回答：
"""
    
    # 注册模板
    mcp_server.register_prompt_template("video_analysis", video_analysis_template)
    mcp_server.register_prompt_template("summary", summary_template)
    mcp_server.register_prompt_template("qa", qa_template)
      
    logger.info("Prompt templates registered to MCP server")
    
# 视频向量搜索工具
@tool(
    name="search_video_by_vector",
    description="连接向量数据库，使用向量相似度搜索视频内容",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="搜索查询文本",
            required=True
        ),
        ToolParameter(
            name="top_k",
            type="number",
            description="返回结果数量，默认10",
            required=False,
            default=10
        )
    ],
    returns={
        "results": "搜索结果列表",
        "total": "结果总数"
    },
    tags=["video", "search", "vector", "mcp"]
)
async def search_video_by_vector_tool(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    MCP工具：视频向量搜索
    
    使用查询文本生成向量，然后在Milvus向量数据库中搜索相似的视频内容。
    返回包含视频ID、匹配文本和时间戳的搜索结果。
    """
    import numpy as np
    from sqlalchemy.orm import Session
    from app.core.database import SessionLocal
    from app.core.milvus import milvus_context
    from app.services.llm_service import llm_service
    from app.models.video import Video
    import logging
    
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    
    try:
        logger.info(f"开始向量搜索，查询: {query}, top_k: {top_k}")
        
        # 为查询生成向量
        logger.info(f"正在为查询 '{query}' 生成向量表示")
        query_embedding = llm_service.generate_embedding(query)
        logger.info(f"查询向量生成完成，维度: {len(query_embedding)}")
        logger.info(f"查询向量前5个值: {query_embedding[:5]}")
        
        # 使用Milvus进行向量搜索
        with milvus_context() as mc:
            # 搜索所有类型的内容（转录、摘要和字幕段落）
            search_results = mc.search_vectors(
                query_vector=np.array(query_embedding),
                top_k=top_k,
                filters=None  # 不限制内容类型，搜索所有内容
            )
        
        logger.info(f"Milvus搜索完成，返回 {len(search_results)} 个向量结果")
        
        # 去重处理，按视频ID分组
        video_groups = {}
        for result in search_results:
            video_id = result["video_id"]
            if video_id not in video_groups:
                video_groups[video_id] = {
                    "video_id": video_id,
                    "matches": [],
                    "best_match_score": result["distance"],
                    "best_match_content": result["content"],
                    "best_match_start_time": result["start_time"],
                    "best_match_end_time": result["end_time"]
                }
            else:
                # 更新最佳匹配（距离最小的）
                if result["distance"] < video_groups[video_id]["best_match_score"]:
                    video_groups[video_id]["best_match_score"] = result["distance"]
                    video_groups[video_id]["best_match_content"] = result["content"]
                    video_groups[video_id]["best_match_start_time"] = result["start_time"]
                    video_groups[video_id]["best_match_end_time"] = result["end_time"]
            
            # 添加所有匹配项
            video_groups[video_id]["matches"].append({
                "content": result["content"],
                "content_type": result["content_type"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
                "score": 1.0 / (1.0 + result["distance"])  # 转换为相似度分数
            })
        
        # 查询视频元数据并构建最终结果
        final_results = []
        for video_id, group in video_groups.items():
            logger.info("+++++++++++++++++++")
            logger.info(f"正在处理视频ID  : {video_id}")
            logger.info("+++++++++++++++++++")
            video = db.query(Video).filter(Video.id == video_id).first()
            logger.info(f"视频ID {video_id} 元数据: {video.__dict__}")
            if video:
                # 计算相关度百分比
                relevance = round((1.0 / (1.0 + group["best_match_score"])) * 100, 1)
                
                # 构建简化的结果格式，包含所有必要信息，特别是id字段
                final_results.append({
                    "id": video.id,  # 视频ID，这是关键的字段，确保前端能获取正确的ID
                    "video_id": video.id,  # 额外添加video_id字段作为冗余，确保兼容性
                    "link": f"/api/v1/videos/{video.id}/outline",  # 跳转到大纲详情页的连接
                    "title": video.filename,  # 视频标题
                    "similarity": relevance,  # 视频匹配相似度（百分比）
                    "matched_subtitles": group["best_match_content"]  # 匹配到的字幕内容
                })
        
        # 按相似度排序
        final_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"向量搜索处理完成，共 {len(final_results)} 个去重后的视频结果")
        
        # 返回简化格式，只包含是否匹配的标记和匹配的视频列表
        return {
            "is_matched": len(final_results) > 0,  # 是否匹配的标记
            "videos": final_results  # 匹配的视频列表
        }
    
    except Exception as e:
        logger.error(f"视频向量搜索失败: {str(e)}")
        raise
    finally:
        db.close()


# 初始化函数
def initialize():
    """
    初始化工具注册表
    
    1. 注册所有MCP工具
    2. 注册系统资源
    3. 注册提示词模板
    """
    logger.info("Initializing tool registry...")
    
    # 注册系统资源
    register_system_resources()
    
    # 注册提示词模板
    register_prompt_templates()
    
    # 获取并记录已注册的工具数量
    tools = mcp_server.get_available_tools()
    logger.info(f"Tool registry initialized with {len(tools)} tools")
    
    # 记录已注册的工具名称
    tool_names = [tool.name for tool in tools]
    logger.info(f"Registered tools: {', '.join(tool_names)}")


# 导出初始化函数和工具
__all__ = [
    'initialize',
    'transcribe_audio_tool',
    'generate_srt_tool',
    'generate_text_tool',
    'generate_summary_tool',
    'answer_question_tool',
    'analyze_video_content_tool',
    'get_available_tools_tool'
]


# 如果直接运行此模块，执行初始化
if __name__ == "__main__":
    initialize()
    # 打印可用工具
    tools = mcp_server.get_available_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")