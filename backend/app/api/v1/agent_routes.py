"""
Agent API路由

该模块提供了与Agent交互的API端点，允许用户通过HTTP请求使用Agent功能。
包括处理用户请求、获取可用工具、测试工具调用等功能。
"""

from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, List, Optional
import logging
import json
import asyncio
from pydantic import BaseModel, Field

from app.services.agent_service import agent_service, AgentConfig
from app.core.mcp import mcp_server, ToolCall, ToolResponse
from app.core.tool_registry import initialize as initialize_tool_registry
from app.core.security import verify_token

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/agent",
    tags=["agent"]
)


# 初始化工具注册表
# 注意：在实际项目中，这个初始化可能应该在应用启动时进行
initialize_tool_registry()


# 请求/响应模型
class AgentRequest(BaseModel):
    """Agent请求模型"""
    message: str = Field(..., description="用户消息")
    config: Optional[AgentConfig] = Field(default=None, description="Agent配置")


class VideoInfo(BaseModel):
    """视频信息模型"""
    video_id: Optional[str] = Field(default=None, description="视频ID")
    title: Optional[str] = Field(default=None, description="视频标题")
    timestamp: Optional[float] = Field(default=None, description="时间戳（秒）")
    thumbnail: Optional[str] = Field(default=None, description="缩略图URL")
    video_link: Optional[str] = Field(default=None, description="完整视频链接，用于前端跳转到大纲页面")
    relevance_score: Optional[float] = Field(default=None, description="相关性得分")


class AgentResponse(BaseModel):
    """Agent响应模型"""
    success: bool = Field(..., description="处理是否成功")
    response: str = Field(..., description="Agent响应文本")
    processing_time: Optional[float] = Field(default=None, description="处理时间（秒）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    video_info: Optional[List[VideoInfo]] = Field(default=None, description="相关视频信息列表")


class ToolCallRequest(BaseModel):
    """工具调用请求模型"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class AvailableToolsResponse(BaseModel):
    """可用工具响应模型"""
    tools: List[Dict[str, Any]] = Field(..., description="工具列表")
    total: int = Field(..., description="工具总数")


# API端点
@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: AgentRequest) -> AgentResponse:
    """
    与Agent进行对话 - 使用Planning-then-Execution模式

    接收用户提示，使用Planning-then-Execution模式的Agent处理并返回响应。
    Agent会根据需要自动调用MCP注册的工具来完成任务。
    Planning-then-Execution模式会让Agent思考、推理、决定是否调用工具，并最终生成回答。
    """
    import time
    import re
    start_time = time.time()

    try:
        logger.info(f"[Planning-then-Execution模式-改造] 收到Agent请求，将使用流式模式: {request.message[:100]}...")

        # 收集流式事件
        all_events = []

        async def collect_callback(event_data):
            """收集所有流式事件"""
            all_events.append(event_data)
            logger.info(f"[Planning-改造] 收集事件: {event_data.get('type')}")

        # 创建agent配置
        config = request.config or AgentConfig()

        # 增强请求格式
        enhanced_request = f"""
{request.message}

## 重要提示：如果你需要返回视频信息，请使用以下JSON格式：
<video_info>
[
    {{"video_id": "视频ID", "title": "视频标题", "thumbnail": "缩略图URL", "video_link": "视频链接", "relevance_score": 相关度分数}}
]
</video_info>

请严格按照上述格式返回视频信息。如果没有视频信息，请不要包含<video_info>标签。
"""

        # 创建agent
        agent = agent_service.create_agent(config)

        # 准备输入（包含流式回调）
        inputs = {
            "input": enhanced_request,
            "stream_callback": collect_callback
        }

        logger.info("[Planning-改造] 调用agent执行器")

        # 调用agent执行器
        response = await agent.agent_executor.ainvoke(inputs)

        logger.info("[Planning-改造] agent执行器调用完成")
        logger.info(f"[Planning-改造] 收集到 {len(all_events)} 个事件")

        # 提取结果
        if isinstance(response, dict) and "output" in response:
            result = response.get("output", "")
        else:
            result = response

        # 解析视频信息
        video_info_list = []
        text_content = result

        video_info_match = re.search(r'<video_info>(.*?)</video_info>', result, re.DOTALL)
        if video_info_match:
            try:
                raw_content = video_info_match.group(1)
                video_info_list = json.loads(raw_content)
                if not isinstance(video_info_list, list):
                    video_info_list = [video_info_list]
                text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
            except Exception as e:
                logger.error(f"[Planning-改造] 解析视频信息失败: {str(e)}")

        response_text = text_content
        
        processing_time = time.time() - start_time
        
        logger.info(f"[Planning-then-Execution模式] Agent响应生成完成，耗时: {processing_time:.2f}s")
        logger.info(f"[Planning-then-Execution模式] 最终返回的回答: {response_text[:100]}...")
        logger.info("----------------------")
        logger.info(response_text)
        logger.info("----------------------")
        
        # 记录视频信息
        if video_info_list:
            logger.info(f"[Planning-then-Execution模式] 从响应中提取到 {len(video_info_list)} 个视频信息")
        else:
            logger.info("[Planning-then-Execution模式] 响应中没有视频信息")
        
        
        
        # 如果没有找到视频信息，尝试从metadata中提取（如果agent_service.process_request支持返回额外信息）
        # 注意：这里可能需要修改agent_service.process_request方法以支持返回视频信息
        
        # 打印AgentResponse对象的详细信息
        response_obj = AgentResponse(
            success=True,
            response=response_text,
            processing_time=processing_time,
            metadata={
                "message_length": len(request.message),
                "response_length": len(response_text),
                "agent_mode": "Planning-then-Execution",
                "video_info_found": len(video_info_list) > 0,
                "stream_events": all_events  # 包含所有收集的流式事件
            },
            video_info=video_info_list if video_info_list else None
        )
        logger.info(f"[Planning-改造] 在metadata中返回 {len(all_events)} 个流式事件")
        logger.info(f"[DEBUG] 返回的AgentResponse对象: {response_obj.model_dump()}")
        logger.info(f"[DEBUG] video_info_list长度: {len(video_info_list) if video_info_list else 0}")
        
        # 返回构建好的响应对象
        return response_obj
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Planning-then-Execution模式] 处理请求时出错: {error_msg}", exc_info=True)
        # 即使出错也返回有意义的信息，让前端能看到错误
        return AgentResponse(
            success=False,
            response=f"使用Planning-then-Execution模式处理请求时出错: {error_msg}",
            processing_time=time.time() - start_time,
            metadata={"error": error_msg},
            video_info=None
        )


@router.get("/tools", response_model=AvailableToolsResponse)
async def get_available_tools() -> AvailableToolsResponse:
    """
    获取所有可用的MCP工具
    
    返回系统中已注册的所有MCP工具的详细信息，包括名称、描述、参数等。
    """
    try:
        tools = mcp_server.get_available_tools()
        
        # 转换为可序列化的格式
        tools_dict = [tool.model_dump() for tool in tools]
        
        return AvailableToolsResponse(
            tools=tools_dict,
            total=len(tools_dict)
        )
        
    except Exception as e:
        logger.error(f"Error getting available tools: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工具列表时出错: {str(e)}")


@router.post("/tools/call")
async def call_tool(request: ToolCallRequest) -> Dict[str, Any]:
    """
    直接调用指定的MCP工具
    
    允许直接测试或使用注册在MCP服务器上的工具。
    """
    try:
        logger.info(f"Tool call request: {request.tool_name} with params: {request.parameters}")
        
        # 异步调用工具
        response = await mcp_server.call_tool_async(
            tool_name=request.tool_name,
            parameters=request.parameters
        )
        
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"Error calling tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调用工具时出错: {str(e)}")


@router.post("/config/test")
async def test_agent_config(config: AgentConfig) -> Dict[str, Any]:
    """
    测试Agent配置
    
    验证Agent配置的有效性，并返回配置信息。
    """
    try:
        logger.info(f"Testing agent config: {config.name}")
        
        # 验证配置
        if config.max_steps <= 0:
            raise ValueError("最大步骤必须大于0")
        
        if not 0 <= config.temperature <= 1:
            raise ValueError("温度参数必须在0到1之间")
        
        # 返回配置信息
        return {
            "success": True,
            "message": "配置有效",
            "config": config.model_dump()
        }
        
    except ValueError as e:
        logger.warning(f"Invalid agent config: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error testing agent config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试配置时出错: {str(e)}")


@router.get("/health")
async def agent_health_check() -> Dict[str, Any]:
    """
    Agent服务健康检查
    
    检查Agent服务和MCP服务器的状态。
    """
    try:
        # 检查MCP服务器状态
        tools = mcp_server.get_available_tools()
        
        return {
            "status": "healthy",
            "agent_service": "online",
            "mcp_server": "online",
            "registered_tools": len(tools),
            "tool_names": [tool.name for tool in tools]
        }
        
    except Exception as e:
        logger.error(f"Agent health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务不可用: {str(e)}")


# 示例路由，展示如何使用Agent处理特定任务
@router.post("/tasks/video-analysis")
async def analyze_video_task(transcript: str) -> Dict[str, Any]:
    """
    视频内容分析任务
    
    使用Agent分析视频内容，提取关键信息。
    """
    try:
        # 构建专用提示
        prompt = f"请分析这段视频字幕，提取关键信息：\n\n{transcript}"
        
        # 创建专用配置
        config = AgentConfig(
            name="视频分析助手",
            role="专业视频内容分析师",
            description="专门用于分析视频内容，提取关键信息的AI助手。",
            max_steps=15,
            temperature=0.3  # 分析任务使用较低温度
        )
        
        # 处理请求
        response = await agent_service.process_request(
            request=prompt,
            config=config
        )
        
        return {
            "success": True,
            "analysis": response
        }
        
    except Exception as e:
        logger.error(f"Error analyzing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析视频时出错: {str(e)}")


@router.post("/chat/stream")
async def chat_with_agent_stream(request: AgentRequest):
    """
    与Agent进行对话 - SSE流式返回（使用原始Response）

    使用Server-Sent Events实时返回planning和execution过程
    """
    from starlette.responses import Response

    async def event_generator():
        """生成SSE事件流 - 真正的流式"""
        import time
        import re

        start_time = time.time()

        logger.info("[SSE-Stream-v2] 开始SSE流式响应")

        # 立即发送连接成功事件
        connected_data = f"data: {json.dumps({'type': 'connected', 'message': '连接成功'}, ensure_ascii=False)}\n\n"
        padding = ": " + ("." * 8000) + "\n"
        yield (connected_data + padding).encode('utf-8')
        logger.info(f"[SSE-Stream-v2] [{time.time() - start_time:.3f}s] 已发送connected事件")

        # 事件队列
        event_queue = asyncio.Queue()

        # 流式回调函数
        async def stream_callback(event_data: Dict[str, Any]):
            """将事件推送到队列"""
            current_time = time.time() - start_time
            logger.info(f"[SSE-Stream] [{current_time:.3f}s] 推送事件到队列: {event_data.get('type')}")
            await event_queue.put(event_data)

        # 创建agent处理任务
        async def process_agent():
            try:
                logger.info(f"[SSE-Stream] 收到Agent请求: {request.message[:100]}...")

                # 创建agent配置
                config = request.config or AgentConfig()

                # 增强请求格式，包含视频信息要求
                enhanced_request = f"""
{request.message}

## 重要提示：如果你需要返回视频信息，请使用以下JSON格式：
<video_info>
[
    {{"video_id": "视频ID", "title": "视频标题", "thumbnail": "缩略图URL", "video_link": "视频链接", "relevance_score": 相关度分数}}
]
</video_info>

请严格按照上述格式返回视频信息。如果没有视频信息，请不要包含<video_info>标签。
"""

                # 创建agent
                agent = agent_service.create_agent(config)

                # 准备输入
                inputs = {
                    "input": enhanced_request,
                    "stream_callback": stream_callback
                }

                logger.info("[SSE-Stream] 开始调用agent执行器")
                logger.info(f"[SSE-Stream] stream_callback 是否为 None: {stream_callback is None}")
                logger.info(f"[SSE-Stream] inputs 内容: {list(inputs.keys())}")

                # 调用agent执行器
                response = await agent.agent_executor.ainvoke(inputs)

                logger.info("[SSE-Stream] agent执行器调用完成")

                # 提取结果
                if isinstance(response, dict) and "output" in response:
                    result = response.get("output", "")
                else:
                    result = response

                # 解析视频信息
                video_info_list = []
                text_content = result

                video_info_match = re.search(r'<video_info>(.*?)</video_info>', result, re.DOTALL)
                if video_info_match:
                    try:
                        raw_content = video_info_match.group(1)
                        video_info_list = json.loads(raw_content)
                        if not isinstance(video_info_list, list):
                            video_info_list = [video_info_list]
                        text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
                    except Exception as e:
                        logger.error(f"[SSE-Stream] 解析视频信息失败: {str(e)}")

                processing_time = time.time() - start_time

                # 发送最终完成事件（包含视频信息）
                await event_queue.put({
                    "type": "complete",
                    "final_answer": text_content,
                    "video_info": video_info_list,
                    "processing_time": processing_time
                })
                logger.info("[SSE-Stream] 已发送完成事件")

            except Exception as e:
                logger.error(f"[SSE-Stream] 处理失败: {str(e)}", exc_info=True)
                await event_queue.put({
                    "type": "error",
                    "error": str(e)
                })
            finally:
                # 发送结束标记
                await event_queue.put(None)

        # 启动处理任务
        task = asyncio.create_task(process_agent())

        try:
            # 持续从队列中获取事件并发送
            while True:
                # 使用超时等待，避免无限阻塞
                try:
                    event_data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # 发送心跳保持连接（使用字节）
                    yield b": heartbeat\n\n"
                    continue

                # None 表示结束
                if event_data is None:
                    logger.info("[SSE-Stream] 收到结束标记")
                    break

                # 格式化为SSE格式（使用字节）
                sse_data = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                current_time = time.time() - start_time
                logger.info(f"[SSE-Stream] [{current_time:.3f}s] 实际 yield 事件: {event_data.get('type')}")

                # 添加大量填充数据（8KB）以强制HTTP缓冲区和浏览器立即刷新
                # 使用注释形式的填充，不影响SSE解析
                padding = ": " + ("." * 8000) + "\n"

                # 统一转换为字节并发送
                full_data = (sse_data + padding).encode('utf-8')
                yield full_data

        except Exception as e:
            logger.error(f"[SSE-Stream] 事件生成器错误: {str(e)}")
            error_event = f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield error_event.encode('utf-8')

        finally:
            # 确保任务完成
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info("[SSE-Stream] 流结束")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
            "Transfer-Encoding": "chunked"  # 明确使用分块传输
        }
    )


@router.websocket("/ws/chat")
async def chat_with_agent_websocket(websocket: WebSocket):
    """
    与Agent进行对话 - WebSocket实时流式返回

    使用WebSocket协议实现真正的实时双向通信，不受localhost TCP缓冲影响
    """
    from app.core.database import SessionLocal
    from app.core.security import verify_token
    from app.models.user import User
    from app.models.video import Video

    await websocket.accept()
    logger.info("[WebSocket] 客户端连接成功")

    try:
        # 接收客户端消息
        data = await websocket.receive_json()
        message = data.get("message", "")
        config_data = data.get("config", None)
        token = data.get("token", None)  # 获取认证令牌

        logger.info(f"[WebSocket] 收到消息: {message[:100]}...")

        # 发送连接确认
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket连接成功"
        })

        # 获取用户信息
        user_id = None
        logger.info(f"[WebSocket] 收到token: {token}")
        logger.info(f"[WebSocket] token类型: {type(token)}, token是否为None: {token is None}, token是否为空: {not token}")

        if token:
            logger.info(f"[WebSocket] 开始调用 verify_token...")
            user_id = verify_token(token)
        else:
            logger.warning(f"[WebSocket] token为空，跳过用户认证")

        # 设置当前用户ID到上下文变量中
        from app.core.context import set_current_user_id
        if user_id:
            set_current_user_id(user_id)
            logger.info(f"[WebSocket] 已设置 contextvar user_id: {user_id}")

        # 创建agent配置
        if config_data:
            config = AgentConfig(**config_data)
        else:
            config = AgentConfig()

        # 增强请求格式，包含用户ID信息
        user_video_info = ""
        if user_id:
            user_video_info = f"""

## 用户视频范围限制
当前用户ID: {user_id}
**重要**: 在调用 search_video_by_vector 工具时，必须传入 user_id 参数，值为: "{user_id}"
这样可以确保只搜索用户自己上传的视频。

调用示例:
search_video_by_vector(query="用户的搜索词", top_k=10, user_id="{user_id}")
"""

        enhanced_request = f"""
{message}

## 重要提示：如果你需要返回视频信息，请使用以下JSON格式：
<video_info>
[
    {{"video_id": "视频ID", "title": "视频标题", "thumbnail": "缩略图URL", "video_link": "视频链接", "relevance_score": 相关度分数}}
]
</video_info>

请严格按照上述格式返回视频信息。如果没有视频信息，请不要包含<video_info>标签。
{user_video_info}
"""

        # WebSocket回调函数 - 直接发送！
        async def ws_callback(event_data: Dict[str, Any]):
            """实时发送事件到WebSocket客户端"""
            try:
                await websocket.send_json(event_data)
                logger.info(f"[WebSocket] 已发送事件: {event_data.get('type')}")
            except Exception as e:
                logger.error(f"[WebSocket] 发送事件失败: {str(e)}")

        # 创建agent并调用
        agent = agent_service.create_agent(config)

        inputs = {
            "input": enhanced_request,
            "stream_callback": ws_callback  # 使用WebSocket回调
        }

        logger.info("[WebSocket] 开始调用agent执行器")

        # 调用agent执行器（所有stream_callback会实时通过WebSocket发送）
        response = await agent.agent_executor.ainvoke(inputs)

        logger.info("[WebSocket] agent执行器调用完成")

        # 提取结果
        if isinstance(response, dict) and "output" in response:
            result = response.get("output", "")
        else:
            result = response

        # 解析视频信息
        import re
        video_info_list = []
        text_content = result

        video_info_match = re.search(r'<video_info>(.*?)</video_info>', result, re.DOTALL)
        if video_info_match:
            try:
                raw_content = video_info_match.group(1)
                video_info_list = json.loads(raw_content)
                if not isinstance(video_info_list, list):
                    video_info_list = [video_info_list]
                text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
            except Exception as e:
                logger.error(f"[WebSocket] 解析视频信息失败: {str(e)}")

        # 强制过滤掉Plan和Reasoning等过程性内容
        # 策略：移除以"Plan:"开头的段落和"Reasoning:"开头的段落
        lines = text_content.split('\n')
        filtered_lines = []
        skip_mode = False

        for line in lines:
            line_stripped = line.strip()
            # 检查是否是Plan或Reasoning的开始
            if line_stripped.lower().startswith('plan:') or line_stripped.lower().startswith('reasoning:'):
                skip_mode = True
                continue
            # 如果遇到两个连续空行，结束skip模式
            if skip_mode and line_stripped == '':
                skip_mode = False
                continue
            # 如果不在skip模式，保留这一行
            if not skip_mode:
                filtered_lines.append(line)

        text_content = '\n'.join(filtered_lines).strip()

        # 再次移除可能残留的<video_info>标签
        text_content = re.sub(r'<video_info>.*?</video_info>', '', text_content, flags=re.DOTALL).strip()

        # 如果移除后内容为空，使用默认消息
        if not text_content and video_info_list:
            text_content = f"找到 {len(video_info_list)} 个相关视频"
        elif not text_content:
            text_content = "处理完成"

        # 发送最终完成事件
        await websocket.send_json({
            "type": "complete",
            "final_answer": text_content,
            "video_info": video_info_list
        })

        logger.info("[WebSocket] 处理完成，发送complete事件")

    except WebSocketDisconnect:
        logger.info("[WebSocket] 客户端断开连接")
    except Exception as e:
        logger.error(f"[WebSocket] 处理失败: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
            logger.info("[WebSocket] 连接已关闭")
        except:
            pass


# 导出路由器
__all__ = ["router"]