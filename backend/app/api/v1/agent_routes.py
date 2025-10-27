"""
Agent API路由

该模块提供了与Agent交互的API端点，允许用户通过HTTP请求使用Agent功能。
包括处理用户请求、获取可用工具、测试工具调用等功能。
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import json
from pydantic import BaseModel, Field

from app.services.agent_service import agent_service, AgentConfig
from app.core.mcp import mcp_server, ToolCall, ToolResponse
from app.core.tool_registry import initialize as initialize_tool_registry

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


class AgentResponse(BaseModel):
    """Agent响应模型"""
    success: bool = Field(..., description="处理是否成功")
    response: str = Field(..., description="Agent响应")
    processing_time: Optional[float] = Field(default=None, description="处理时间（秒）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


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
    与Agent进行对话 - 使用REACT模式
    
    接收用户提示，使用REACT模式的Agent处理并返回响应。
    Agent会根据需要自动调用MCP注册的工具来完成任务。
    REACT模式会让Agent思考、推理、决定是否调用工具，并最终生成回答。
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"[REACT模式] 收到Agent请求: {request.message[:100]}...")
        
        # 处理请求 - 使用REACT模式
        response_text = await agent_service.process_request(
            request=request.message,
            chat_history=None,  # 可以根据需要添加聊天历史支持
            config=request.config
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"[REACT模式] Agent响应生成完成，耗时: {processing_time:.2f}s")
        logger.info(f"[REACT模式] 最终返回的回答: {response_text[:100]}...")
        
        return AgentResponse(
            success=True,
            response=response_text,
            processing_time=processing_time,
            metadata={
                "message_length": len(request.message),
                "response_length": len(response_text),
                "agent_mode": "REACT"
            }
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[REACT模式] 处理请求时出错: {error_msg}", exc_info=True)
        # 即使出错也返回有意义的信息，让前端能看到错误
        return AgentResponse(
            success=False,
            response=f"使用REACT模式处理请求时出错: {error_msg}",
            processing_time=time.time() - start_time,
            metadata={"error": error_msg}
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
        tools_dict = [tool.dict() for tool in tools]
        
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
        
        return response.dict()
        
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
            "config": config.dict()
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


# 导出路由器
__all__ = ["router"]