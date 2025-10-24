"""
基于LangChain的Agent服务实现

该模块使用LangChain框架提供了AI Agent的核心实现，负责与MCP协议交互，完成工具选择、调用和结果处理。
Agent能够基于用户请求和可用工具，自主决策调用哪些工具来完成任务。
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
import json
import asyncio
from functools import wraps

# LangChain 导入
from langchain_core.tools import tool as langchain_tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from app.core.mcp import mcp_server, ToolDefinition, ToolCall, ToolResponse
from app.services.llm_service import VolcLLMService

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Agent配置"""
    name: str = Field(default="QuickRewind Agent", description="Agent名称")
    role: str = Field(default="视频处理助手", description="Agent角色")
    description: str = Field(
        default="你是一个视频处理助手，能够帮助用户分析视频内容、提取关键信息、生成摘要等。",
        description="Agent描述"
    )
    max_steps: int = Field(default=10, description="最大执行步骤")
    temperature: float = Field(default=0.7, description="生成温度")


class AgentState(BaseModel):
    """Agent状态"""
    current_step: int = Field(default=0, description="当前执行步骤")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="执行历史")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


# 异步工具包装器
def async_to_sync_wrapper(async_func: Callable) -> Callable:
    """
    将异步函数包装为同步函数，用于LangChain的工具调用
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# 将MCP工具转换为LangChain工具
def convert_mcp_to_langchain_tools() -> List:
    """
    将MCP注册的工具转换为LangChain工具
    
    Returns:
        List: LangChain工具列表
    """
    langchain_tools = []
    
    # 获取所有MCP注册的工具
    mcp_tools = mcp_server.get_available_tools()
    
    for mcp_tool in mcp_tools:
        # 创建工具函数
        @langchain_tool
        def create_tool_func(*args, tool_name=mcp_tool.name, **kwargs):
            """动态创建的工具函数"""
            logger.info(f"LangChain calling MCP tool: {tool_name} with args: {args}, kwargs: {kwargs}")
            
            # 构建参数字典
            params = kwargs.copy()
            if args:
                # 处理位置参数（如果有）
                for i, arg in enumerate(args):
                    if i < len(mcp_tool.parameters):
                        param_name = mcp_tool.parameters[i].name
                        params[param_name] = arg
            
            # 异步调用MCP工具
            async def call_mcp_tool():
                result = await mcp_server.call_tool_async(
                    tool_name=tool_name,
                    parameters=params
                )
                if result.success:
                    return result.result
                else:
                    raise Exception(f"工具调用失败: {result.error}")
            
            # 使用同步包装器执行异步调用
            return async_to_sync_wrapper(call_mcp_tool)()
        
        # 设置工具函数的名称和文档
        create_tool_func.__name__ = mcp_tool.name
        create_tool_func.__doc__ = mcp_tool.description
        
        # 添加到工具列表
        langchain_tools.append(create_tool_func)
    
    logger.info(f"Converted {len(langchain_tools)} MCP tools to LangChain tools")
    return langchain_tools


class VolcLLMWrapper:
    """
    火山引擎LLM包装器，适配LangChain接口
    """
    
    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature
        self.llm_service = VolcLLMService()
    
    def invoke(self, messages: List[Dict[str, str]]) -> str:
        """
        调用LLM模型
        
        Args:
            messages: 消息列表，每个消息包含role和content
            
        Returns:
            str: 生成的文本
        """
        # 提取系统提示和用户提示
        system_prompt = None
        user_prompts = []
        
        for message in messages:
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
            elif message.get("role") == "user":
                user_prompts.append(message.get("content", ""))
        
        # 合并用户提示
        prompt = "\n".join(user_prompts)
        
        # 调用LLM服务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.llm_service.generate(
                    system_prompt=system_prompt,
                    prompt=prompt,
                    temperature=self.temperature
                )
            )
            return result
        finally:
            loop.close()
    
    async def ainvoke(self, messages: List[Dict[str, str]]) -> str:
        """
        异步调用LLM模型
        
        Args:
            messages: 消息列表，每个消息包含role和content
            
        Returns:
            str: 生成的文本
        """
        # 提取系统提示和用户提示
        system_prompt = None
        user_prompts = []
        
        for message in messages:
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
            elif message.get("role") == "user":
                user_prompts.append(message.get("content", ""))
        
        # 合并用户提示
        prompt = "\n".join(user_prompts)
        
        # 调用LLM服务
        result = await self.llm_service.generate(
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=self.temperature
        )
        return result


class Agent:
    """
    基于LangChain的AI Agent实现
    
    负责解析用户请求，选择合适的工具，调用工具并处理结果，最终生成响应。
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化Agent
        
        Args:
            config: Agent配置
        """
        self.config = config or AgentConfig()
        self.state = AgentState()
        self.logger = logger.getChild(f"agent.{self.config.name}")
        
        # 创建LLM包装器
        self.llm = VolcLLMWrapper(temperature=self.config.temperature)
        
        # 初始化LangChain Agent
        self.agent_executor = self._create_agent_executor()
        
        self.logger.info(f"LangChain Agent initialized: {self.config.name}")
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        创建LangChain Agent执行器
        
        Returns:
            AgentExecutor: LangChain Agent执行器
        """
        # 获取工具列表
        tools = convert_mcp_to_langchain_tools()
        
        # 创建提示模板（ReAct风格）
        system_prompt = f"""
你是{self.config.name}，{self.config.role}。
{self.config.description}

你有以下工具可用：
{[f"{tool.name}: {tool.description}" for tool in tools]}

使用以下格式来回应：

思考过程:
[分析用户请求和可用工具，决定下一步操作]

调用工具:
工具名称 参数1=值1 参数2=值2

或者，如果决定直接回答用户：

直接回答:
[你的回答内容]

请根据用户请求，分析需要调用哪些工具来完成任务。
如果你需要更多信息，请向用户提问。
请保持回答简洁明了，直接针对用户的问题提供帮助。
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 创建ReAct Agent (兼容当前LangChain版本的工具调用方式)
        agent = create_react_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt
        )
        
        # 创建Agent执行器
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,  # 详细日志
            max_iterations=self.config.max_steps,
            early_stopping_method="generate"
        )
        
        return agent_executor
    
    async def process_request(self, request: str) -> str:
        """
        处理用户请求
        
        Args:
            request: 用户请求文本
            
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"Processing request: {request}")
            
            # 重置状态
            self.state = AgentState()
            
            # 使用LangChain Agent处理请求
            response = await self.agent_executor.ainvoke({
                "input": request
            })
            
            # 提取最终回答
            final_response = response.get("output", "无法生成响应")
            
            # 更新状态
            self.state.is_completed = True
            self.state.current_step = len(response.get("intermediate_steps", []))
            
            # 记录工具调用历史
            for step in response.get("intermediate_steps", []):
                if len(step) >= 2:
                    action = step[0]
                    observation = step[1]
                    self.state.history.append({
                        "type": "tool_call",
                        "tool": action.tool,
                        "parameters": action.tool_input,
                        "response": {
                            "success": True,
                            "result": observation
                        }
                    })
            
            self.logger.info(f"Request processing completed in {self.state.current_step} steps")
            return final_response
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return f"处理请求时出错: {str(e)}"
    
    def reset(self):
        """
        重置Agent状态
        """
        self.state = AgentState()
        # 重新创建Agent执行器以清除内部状态
        self.agent_executor = self._create_agent_executor()
        self.logger.info("Agent state reset")


class AgentService:
    """
    Agent服务类
    
    提供统一的API接口，管理Agent实例
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.agents = {}
        return cls._instance
    
    def create_agent(self, config: Optional[AgentConfig] = None) -> Agent:
        """
        创建Agent实例
        
        Args:
            config: Agent配置
            
        Returns:
            Agent实例
        """
        agent = Agent(config)
        # 存储Agent实例
        self.agents[id(agent)] = agent
        return agent
    
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        """
        获取Agent实例
        
        Args:
            agent_id: Agent实例ID
            
        Returns:
            Agent实例或None
        """
        return self.agents.get(agent_id)
    
    async def process_request(self, request: str, config: Optional[AgentConfig] = None) -> str:
        """
        处理请求的便捷方法
        
        Args:
            request: 用户请求
            config: Agent配置
            
        Returns:
            处理结果
        """
        agent = self.create_agent(config)
        result = await agent.process_request(request)
        return result
    
    def reset_agent(self, agent_id: int):
        """
        重置指定的Agent实例
        
        Args:
            agent_id: Agent实例ID
        """
        agent = self.get_agent(agent_id)
        if agent:
            agent.reset()
            self.logger.info(f"Reset agent: {agent_id}")
    
    def clear_agents(self):
        """
        清除所有Agent实例
        """
        self.agents.clear()
        self.logger.info("All agents cleared")


# 创建全局Agent服务实例
agent_service = AgentService()


# 导出核心组件
__all__ = [
    'Agent',
    'AgentConfig',
    'AgentState',
    'AgentService',
    'agent_service'
]