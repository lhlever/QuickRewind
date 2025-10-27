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


# AgentState类已被移除，因为我们使用简化的实现
# 不再需要复杂的状态管理


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


# 简化的工具处理函数 - 获取基本的工具信息
def get_available_tools_info() -> str:
    """
    获取可用工具的信息字符串
    
    Returns:
        str: 包含所有工具信息的字符串
    """
    try:
        # 获取所有MCP注册的工具
        mcp_tools = mcp_server.get_available_tools()
        if not mcp_tools:
            return "目前没有可用工具"
        
        tools_info = []
        for i, tool in enumerate(mcp_tools):
            try:
                # 安全访问工具名称和描述
                tool_name = getattr(tool, 'name', f'工具{i+1}')
                tool_desc = getattr(tool, 'description', '无描述')
                tools_info.append(f"- {tool_name}: {tool_desc[:100]}..." if len(tool_desc) > 100 else f"- {tool_name}: {tool_desc}")
            except Exception:
                # 忽略无法处理的工具
                continue
        
        if not tools_info:
            return "无法获取工具详细信息"
        
        return "\n".join(tools_info)
    except Exception:
        # 如果无法获取工具列表，返回通用信息
        return "工具列表获取失败"


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
            print(result)
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
        self.logger = logger.getChild(f"agent.{self.config.name}")
        
        # 初始化Agent执行器
        self.agent_executor = self._create_agent_executor()
        
        self.logger.info(f"Simplified Agent initialized: {self.config.name}")
    
    def _create_agent_executor(self) -> object:
        """
        创建基于React模式的Agent执行器
        
        Returns:
            object: 真正的React模式Agent执行器
        """
        try:
            # 获取所有可用的MCP工具
            mcp_tools = mcp_server.get_available_tools()
            
            # 转换MCP工具为LangChain工具
            langchain_tools = []
            
            for tool in mcp_tools:
                # 为每个工具单独创建包装函数
                tool_name = getattr(tool, 'name', 'unknown_tool')
                tool_desc = getattr(tool, 'description', '无描述')
                
                # 创建同步工具函数
                @langchain_tool
                def create_tool_function(tool_obj=tool, **kwargs):
                    # 调用MCP工具
                    try:
                        # 使用同步方式调用异步的MCP工具
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        tool_call = ToolCall(
                            name=getattr(tool_obj, 'name', 'unknown_tool'),
                            parameters=kwargs
                        )
                        
                        # 同步运行异步函数
                        result = loop.run_until_complete(
                            mcp_server.call_tool(tool_call)
                        )
                        return result.result
                    except Exception as e:
                        logger.error(f"Tool {getattr(tool_obj, 'name', 'unknown')} call failed: {str(e)}")
                        return f"工具调用失败: {str(e)}"
                    finally:
                        loop.close()
                
                # 更新函数的名称和描述
                create_tool_function.__name__ = tool_name
                create_tool_function.__doc__ = tool_desc
                
                # 添加到工具列表
                langchain_tools.append(create_tool_function)
            
            # 创建系统提示
            system_prompt = f"""
            你是{self.config.name}，一个{self.config.role}。
            
            你的任务是基于用户的请求，决定是：
            1. 直接回答用户（如果信息足够）
            2. 调用适当的工具获取更多信息后再回答
            
            请根据以下决策路径分析用户请求：
            - 如果用户请求明确需要使用工具（如搜索视频、分析内容等），请调用相应工具
            - 如果用户请求是一般性问题且不需要额外信息，请直接回答
            - 如果缺少必要参数，请向用户提问以获取信息
            
            以下是你可用的工具：
            {get_available_tools_info()}
            
            请按照严格的React思考过程进行决策，首先分析用户需求，然后决定是否调用工具。
            """
            
            # 创建React风格的提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # 初始化LLM包装器
            llm = VolcLLMWrapper(temperature=self.config.temperature)
            
            # 如果有工具可用，创建真正的React Agent
            if langchain_tools:
                # 创建React Agent
                agent = create_react_agent(
                    llm=llm,
                    tools=langchain_tools,
                    prompt=prompt
                )
                
                # 创建执行器
                executor = AgentExecutor(
                    agent=agent,
                    tools=langchain_tools,
                    max_iterations=self.config.max_steps,
                    handle_parsing_errors=True,
                    verbose=True
                )
                
                return executor
            else:
                # 无工具可用，返回简单执行器
                self.logger.warning("No tools available for React agent")
                
            # 即使没有工具可用，也要保持REACT模式的一致性
            # 创建一个模拟REACT思考过程的执行器
            self.logger.warning("没有工具可用，但仍保持REACT模式")
            
            # 获取工具信息
            tools_info_str = get_available_tools_info()
            
            # 创建一个符合REACT模式的执行器
            class ReactModeExecutor:
                def __init__(self, config, tools_info):
                    self.config = config
                    self.tools_info = tools_info
                    self.llm_service = VolcLLMService()  # 初始化LLM服务
                
                async def ainvoke(self, inputs):
                    user_input = inputs.get("input", "")
                    
                    # 使用火山引擎大模型生成回答
                    try:
                        # 准备REACT模式的系统提示
                        system_prompt = f"""
                        你是{self.config.name}，一个{self.config.role}。
                        
                        请按照REACT思考过程回答用户问题：
                        1. 首先分析问题（思考）
                        2. 决定是否需要调用工具（推理）
                        3. 由于当前没有可用工具，直接基于你的知识回答（回答）
                        
                        请以[思考]、[推理]、[回答]的格式输出。
                        """
                        
                        # 调用火山引擎大模型
                        self.logger.info(f"[REACT模式] 调用火山引擎大模型回答问题: {user_input[:50]}...")
                        response = await self.llm_service.generate_async(
                            prompt=user_input,
                            system_prompt=system_prompt,
                            temperature=0.7,
                            max_tokens=2048
                        )
                        
                        self.logger.info(f"[REACT模式] 火山引擎大模型返回结果: {response[:50]}...")
                        
                        # 如果响应中包含[思考]、[推理]、[回答]格式，直接返回
                        if "[思考]" in response and "[推理]" in response and "[回答]" in response:
                            return {"output": response}
                        else:
                            # 确保返回符合REACT模式的格式
                            react_format_answer = f"""[思考] 分析用户问题：{user_input}
[推理] 我需要评估是否需要调用工具来回答这个问题。由于当前系统没有可用的工具，我将基于我的知识直接回答。
[回答] {response}

注意：这是基于大模型自身知识的回答。"""
                            return {"output": react_format_answer}
                            
                    except Exception as e:
                        # 错误处理：即使LLM调用失败也返回有意义的回答
                        error_msg = str(e)
                        self.logger.error(f"[REACT模式] 调用火山引擎大模型失败: {error_msg}")
                        
                        # 备用回答，确保保持REACT模式
                        fallback_answer = f"""[思考] 分析用户问题：{user_input}
[推理] 尝试调用大模型时遇到错误，需要提供备用回答。
[回答] 抱歉，在处理您的问题时遇到了一些技术困难。我无法使用大模型来回答这个问题。

当前系统支持的功能：
{self.tools_info}

请稍后再试，或者尝试一个不同的问题。"""
                        return {"output": fallback_answer}
            
            return ReactModeExecutor(self.config, tools_info_str)
            
        except Exception as e:
            self.logger.error(f"[REACT模式] 创建REACT agent执行器失败: {str(e)}")
            
            # 即使在异常情况下，也要保持REACT模式并尝试调用大模型
            tools_info_str = get_available_tools_info()
            
            class FallbackReactExecutor:
                def __init__(self, config, tools_info):
                    self.config = config
                    self.tools_info = tools_info
                    self.llm_service = VolcLLMService()  # 初始化LLM服务
                
                async def ainvoke(self, inputs):
                    user_input = inputs.get("input", "")
                    
                    # 尝试调用火山引擎大模型生成回答
                    try:
                        # 准备REACT模式的系统提示
                        system_prompt = f"""
                        你是{self.config.name}，一个{self.config.role}。
                        
                        请按照REACT思考过程回答用户问题：
                        1. 首先分析问题（思考）
                        2. 决定是否需要调用工具（推理）
                        3. 由于系统初始化异常，直接基于你的知识回答（回答）
                        
                        请以[思考]、[推理]、[回答]的格式输出。
                        """
                        
                        # 调用火山引擎大模型
                        self.logger.info(f"[REACT模式-异常恢复] 调用火山引擎大模型回答问题: {user_input[:50]}...")
                        response = await self.llm_service.generate_async(
                            prompt=user_input,
                            system_prompt=system_prompt,
                            temperature=0.7,
                            max_tokens=2048
                        )
                        
                        self.logger.info(f"[REACT模式-异常恢复] 火山引擎大模型返回结果: {response[:50]}...")
                        
                        return {"output": response}
                        
                    except Exception as e:
                        # 如果大模型调用也失败，提供最后的备用回答
                        self.logger.error(f"[REACT模式-异常恢复] 调用火山引擎大模型失败: {str(e)}")
                        
                        # 返回符合REACT模式的fallback回答
                        return {"output": f"[思考] 分析用户问题：{user_input}\n[推理] 系统在初始化REACT agent过程中遇到错误，并且尝试调用大模型也失败了\n[回答] 非常抱歉，系统在处理您的请求时遇到了严重的技术问题。我无法为您提供关于'{user_input}'的具体回答。请稍后再试，或者尝试重启系统。"}
            
            return FallbackReactExecutor(self.config, tools_info_str)
    
    async def process_request(self, request: str, chat_history: Optional[List[Dict]] = None, db=None) -> str:
        """
        处理用户请求 - React模式实现
        
        Args:
            request: 用户请求文本
            chat_history: 聊天历史记录，用于上下文理解
            db: 数据库会话（可选）
            
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"[REACT模式] 开始处理请求: {request}")
            
            # 对于日期和时间类问题，我们可以直接获取系统时间
            request_lower = request.lower()
            if '今天几号' in request_lower or '日期' in request_lower:
                import datetime
                today = datetime.datetime.now().strftime('%Y年%m月%d日')
                direct_answer = f"今天是{today}"
                self.logger.info(f"[系统回答] 日期问题: {direct_answer}")
                return direct_answer
            elif '现在几点' in request_lower or '时间' in request_lower:
                import datetime
                current_time = datetime.datetime.now().strftime('%H:%M:%S')
                direct_answer = f"现在是{current_time}"
                self.logger.info(f"[系统回答] 时间问题: {direct_answer}")
                return direct_answer
            
            # 所有其他问题都使用REACT模式的Agent执行器处理
            try:
                self.logger.info(f"[REACT模式] 使用大模型和REACT流程处理问题")
                
                # 准备执行器输入 - 符合REACT模式的要求
                inputs = {
                    "input": request
                }
                
                # 如果提供了聊天历史，添加到输入中
                if chat_history:
                    inputs["chat_history"] = chat_history
                
                self.logger.info(f"[REACT模式] 调用Agent执行器 (React模式), 输入: {inputs}")
                
                # 直接调用Agent执行器 - 这是REACT模式的核心
                response = await self.agent_executor.ainvoke(inputs)
                
                self.logger.info(f"[REACT模式] Agent执行器返回结果: {response}")
                
                # 从REACT模式的执行结果中提取输出
                direct_answer = response.get("output", "")
                
                self.logger.info(f"[REACT模式] 从REACT结果中提取的回答: '{direct_answer}'")
                
                # 确保有有效回答
                if not direct_answer or direct_answer.strip() == "" or direct_answer == "无法生成响应":
                    self.logger.warning(f"[REACT模式] 回答无效，使用备用回复")
                    direct_answer = f"根据您的问题: {request}，我无法提供具体回答。请尝试提供更多细节或换一种方式提问。"
                
                # 直接返回REACT模式生成的回答
                return direct_answer
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[REACT模式] 调用失败: {error_msg}", exc_info=True)
                # 即使失败也返回有意义的错误信息
                return f"处理您的问题时遇到错误: {error_msg}。系统使用的是REACT模式的Agent，但调用过程中出现了问题。"
            
            # 从MCP服务器获取所有可用工具进行分析和调用（如果不是简单问题）
            if not direct_answer:
                try:
                    mcp_tools = mcp_server.get_available_tools()
                    for tool in mcp_tools:
                        tool_name = getattr(tool, 'name', 'unknown_tool')
                        tool_desc = getattr(tool, 'description', '')
                        
                        # 简单匹配逻辑：检查工具名称和描述是否与用户请求相关
                        request_lower = request.lower()
                        tool_name_lower = tool_name.lower()
                        tool_desc_lower = tool_desc.lower()
                        
                        # 如果工具名称或描述中包含用户请求的关键词，可能需要调用
                        if (any(keyword in request_lower for keyword in [tool_name_lower, '搜索', '查询', '分析', '总结']) or
                            any(keyword in request_lower for keyword in tool_desc_lower.split())):
                            prepared_tools.append(tool_name)
                            
                            # 实际调用匹配的工具
                            try:
                                # 创建工具调用参数
                                tool_call = ToolCall(
                                    name=tool_name,
                                    parameters={'query': request}  # 传递用户查询作为参数
                                )
                                
                                # 调用工具并获取结果
                                result = await mcp_server.call_tool(tool_call)
                                tool_call_results[tool_name] = result.result
                                self.logger.info(f"Successfully called tool {tool_name}")
                            except Exception as e:
                                error_msg = f"调用工具 {tool_name} 失败: {str(e)}"
                                tool_call_results[tool_name] = error_msg
                                self.logger.error(error_msg)
                except Exception as e:
                    self.logger.error(f"Error getting MCP tools: {str(e)}")
            
            # 准备响应内容
            response_content = ""
            
            # 如果有直接回答，优先显示直接回答
            if direct_answer:
                response_content = f"💡 直接回答：\n{direct_answer}"
            # 如果有工具调用结果，显示工具调用结果
            elif tool_call_results:
                response_content = "📊 工具调用结果："
                for tool_name, result in tool_call_results.items():
                    response_content += f"\n\n**{tool_name}**:\n{result}"
            # 如果没有匹配的工具，显示通用信息
            else:
                response_content = "您的问题不需要特定工具回答，这是一个可以直接回答的问题。"
            
            # 添加工具信息
            response_content += f"\n\n🔧 所有支持的工具：\n{available_tools}"
            response_content += f"\n\n📋 根据您的请求，准备调用的工具：\n{', '.join(prepared_tools) if prepared_tools else '暂无匹配的工具'}"
            
            # 记录处理结果
            self.logger.info(f"Request processing completed successfully. Response content prepared.")
            
            return response_content
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            # 返回错误信息，同时包含支持的工具信息
            try:
                available_tools = get_available_tools_info()
                return f"处理您的请求时遇到了问题：{str(e)}。\n\n🔧 所有支持的工具：\n{available_tools}"
            except:
                return f"处理您的请求时遇到了问题：{str(e)}"

    
    def reset(self):
        """
        重置Agent状态 - 简化版本
        """
        # 简单地重新创建Agent执行器
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
    
    async def process_request(self, request: str, chat_history: Optional[List[Dict]] = None, config: Optional[AgentConfig] = None) -> str:
        """
        处理请求的便捷方法
        
        Args:
            request: 用户请求
            chat_history: 聊天历史记录，用于上下文理解
            config: Agent配置
            
        Returns:
            处理结果
        """
        agent = self.create_agent(config)
        result = await agent.process_request(request, chat_history)
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