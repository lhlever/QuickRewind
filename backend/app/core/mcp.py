"""
MCP (Model Context Protocol) 协议实现

该模块提供了MCP协议的核心实现，用于标准化AI模型与外部工具和服务之间的通信。
MCP协议定义了工具注册、发现和调用的标准接口，使得Agent能够以统一的方式与各种工具交互。
"""

from typing import Dict, Any, List, Callable, Optional
import json
import logging
from pydantic import BaseModel, Field
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    description: str = Field(..., description="参数描述")
    required: bool = Field(default=True, description="是否必需")
    default: Any = Field(default=None, description="默认值")


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: List[ToolParameter] = Field(default_factory=list, description="参数列表")
    returns: Dict[str, Any] = Field(default_factory=dict, description="返回值定义")
    tags: List[str] = Field(default_factory=list, description="工具标签")


class ToolResponse(BaseModel):
    """工具响应"""
    success: bool = Field(..., description="调用是否成功")
    result: Any = Field(None, description="调用结果")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ToolCall(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    id: Optional[str] = Field(None, description="调用ID")


class MCPServer:
    """
    MCP服务器实现
    
    负责管理工具注册表、处理工具调用请求、提供工具发现功能
    """
    
    def __init__(self):
        # 工具注册表，存储所有可用工具
        self._tools: Dict[str, Dict[str, Any]] = {}
        # 资源管理器
        self._resources: Dict[str, Any] = {}
        # 提示词模板库
        self._prompt_templates: Dict[str, str] = {}
        logger.info("MCP Server initialized")
    
    def register_tool(
        self, 
        name: str, 
        func: Callable, 
        description: str, 
        parameters: List[ToolParameter],
        returns: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> None:
        """
        注册工具到MCP服务器
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            parameters: 参数列表
            returns: 返回值定义
            tags: 工具标签
        """
        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")
        
        # 验证参数
        for param in parameters:
            if param.type not in ['string', 'number', 'boolean', 'array', 'object', 'file']:
                logger.error(f"Invalid parameter type {param.type} for {param.name}")
                raise ValueError(f"Invalid parameter type {param.type}")
        
        # 存储工具信息
        self._tools[name] = {
            'function': func,
            'definition': ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                returns=returns or {},
                tags=tags or []
            )
        }
        logger.info(f"Tool registered: {name}")
    
    def get_available_tools(self) -> List[ToolDefinition]:
        """
        获取所有可用工具的定义
        
        Returns:
            工具定义列表
        """
        return [tool['definition'] for tool in self._tools.values()]
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定工具信息
        
        Args:
            name: 工具名称
            
        Returns:
            工具信息或None
        """
        return self._tools.get(name)
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResponse:
        """
        同步调用工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            工具响应
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResponse(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        try:
            # 验证参数
            self._validate_parameters(tool['definition'], parameters)
            
            # 调用工具函数
            result = tool['function'](**parameters)
            
            return ToolResponse(
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return ToolResponse(
                success=False,
                error=str(e)
            )
    
    async def call_tool_async(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResponse:
        """
        异步调用工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            工具响应
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResponse(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        try:
            # 验证参数
            self._validate_parameters(tool['definition'], parameters)
            
            # 判断是否为异步函数
            if asyncio.iscoroutinefunction(tool['function']):
                # 异步调用
                result = await tool['function'](**parameters)
            else:
                # 同步函数转换为异步调用
                result = await asyncio.to_thread(tool['function'], **parameters)
            
            return ToolResponse(
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} asynchronously: {str(e)}")
            return ToolResponse(
                success=False,
                error=str(e)
            )
    
    def _validate_parameters(self, tool_def: ToolDefinition, parameters: Dict[str, Any]) -> None:
        """
        验证工具调用参数
        
        Args:
            tool_def: 工具定义
            parameters: 待验证的参数
            
        Raises:
            ValueError: 参数验证失败
        """
        # 检查必需参数
        required_params = [p.name for p in tool_def.parameters if p.required]
        for param_name in required_params:
            if param_name not in parameters:
                raise ValueError(f"Required parameter {param_name} missing")
    
    def register_resource(self, name: str, resource: Any) -> None:
        """
        注册资源
        
        Args:
            name: 资源名称
            resource: 资源对象
        """
        self._resources[name] = resource
        logger.info(f"Resource registered: {name}")
    
    def get_resource(self, name: str) -> Optional[Any]:
        """
        获取资源
        
        Args:
            name: 资源名称
            
        Returns:
            资源对象或None
        """
        return self._resources.get(name)
    
    def register_prompt_template(self, name: str, template: str) -> None:
        """
        注册提示词模板
        
        Args:
            name: 模板名称
            template: 模板内容
        """
        self._prompt_templates[name] = template
        logger.info(f"Prompt template registered: {name}")
    
    def get_prompt_template(self, name: str) -> Optional[str]:
        """
        获取提示词模板
        
        Args:
            name: 模板名称
            
        Returns:
            模板内容或None
        """
        return self._prompt_templates.get(name)
    
    def render_prompt_template(self, name: str, **kwargs) -> Optional[str]:
        """
        渲染提示词模板
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            渲染后的提示词或None
        """
        template = self.get_prompt_template(name)
        if template:
            try:
                return template.format(**kwargs)
            except Exception as e:
                logger.error(f"Error rendering prompt template {name}: {str(e)}")
        return None


# 创建全局MCP服务器实例
mcp_server = MCPServer()


def tool(
    name: str,
    description: str,
    parameters: List[ToolParameter],
    returns: Dict[str, Any] = None,
    tags: List[str] = None
):
    """
    工具注册装饰器
    
    用于将普通函数注册为MCP工具
    
    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数列表
        returns: 返回值定义
        tags: 工具标签
    """
    def decorator(func: Callable) -> Callable:
        # 注册工具到全局MCP服务器
        mcp_server.register_tool(
            name=name,
            func=func,
            description=description,
            parameters=parameters,
            returns=returns,
            tags=tags
        )
        
        # 保持原始函数不变
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# MCP上下文管理器，用于在需要时访问MCP服务器
class mcp_context:
    """
    MCP上下文管理器
    
    提供对MCP服务器的便捷访问
    """
    
    def __init__(self, server: MCPServer = mcp_server):
        self.server = server
    
    def __enter__(self):
        return self.server
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 不需要特殊清理
        pass


# 导出核心组件
__all__ = [
    'MCPServer',
    'ToolParameter',
    'ToolDefinition',
    'ToolResponse',
    'ToolCall',
    'mcp_server',
    'tool',
    'mcp_context'
]