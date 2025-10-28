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
                self.llm_service.generate_async(
                    system_prompt=system_prompt,
                    prompt=prompt,
                    temperature=self.temperature
                )
            )
            logger.info(f"[VolcLLMWrapper-sync] 大模型返回结果: 长度={len(result)}")
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
        
        # 调用LLM服务的异步方法
        logger.info(f"[VolcLLMWrapper] 调用火山引擎大模型: prompt长度={len(prompt)}, 有系统提示={system_prompt is not None}")
        result = await self.llm_service.generate_async(
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=self.temperature
        )
        logger.info(f"[VolcLLMWrapper] 大模型返回结果: 长度={len(result)}")
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
            
            # 工具名称到工具对象的映射，用于后续直接调用
            tool_map = {}
            
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
                
                # 添加到工具列表和映射
                langchain_tools.append(create_tool_function)
                tool_map[tool_name] = tool
            
            # 创建系统提示 - 标准Planning模式提示词
            planning_prompt = f"""
            你是{self.config.name}，一个{self.config.role}。
            
            你需要按照以下Planning模式来处理用户的请求：
            1. 分析问题并制定详细的执行计划
            2. 按照计划逐步执行每个步骤
            3. 根据执行结果调整计划（如有必要）
            
            首先，你需要制定一个详细的执行计划，列出解决问题所需的步骤。然后按照计划逐步执行。
            
            可用工具列表：
            {get_available_tools_info()}
            
            请严格按照以下格式输出你的初始计划：
            
            Plan:
            1. [第一步计划]
            2. [第二步计划]
            3. [更多步骤...] (根据需要添加)
            
            然后按照计划逐步执行，每一步都输出：
            Step: [当前执行的步骤编号和描述]
            Action: [调用工具的格式或直接回答]
               - 工具调用格式: tool_name(参数1=值1, 参数2=值2)
               - 直接回答格式: Finish[最终答案]
            """
            
            # 初始化LLM包装器
            llm = VolcLLMWrapper(temperature=self.config.temperature)
            
            # 创建真正的Planning执行器类
            class PlanningExecutor:
                def __init__(self, agent_config, tools, tool_mapping, llm_wrapper):
                    self.config = agent_config
                    self.tools = tools
                    self.tool_map = tool_mapping
                    self.llm = llm_wrapper
                    self.logger = logging.getLogger(f"PlanningExecutor")
                    
                async def ainvoke(self, inputs):
                    # 获取输入参数
                    user_input = inputs.get("input", "")
                    chat_history = inputs.get("chat_history", [])
                    
                    # 初始化对话历史
                    dialog_history = chat_history.copy()
                    dialog_history.append({"role": "user", "content": user_input})
                    
                    # 构建初始规划提示
                    initial_prompt = planning_prompt
                    initial_prompt += "\n\n对话历史:\n"
                    for msg in dialog_history:
                        initial_prompt += f"{msg['role']}: {msg['content']}\n"
                    
                    # 第一步：生成执行计划
                    self.logger.info(f"[Planning模式] 生成执行计划")
                    plan_response = await self.llm.ainvoke([
                        {"role": "system", "content": initial_prompt}
                    ])
                    
                    self.logger.info(f"[Planning模式] 计划响应: {plan_response[:100]}...")
                    
                    # 解析计划
                    plan_steps = self._parse_plan(plan_response)
                    if not plan_steps:
                        self.logger.error("[Planning模式] 无法解析生成的计划")
                        return {"output": "无法生成有效的执行计划，请重试。"}
                    
                    # 保存计划信息
                    execution_history = [f"生成的计划: {', '.join(plan_steps)}"]
                    
                    # 第二步：按照计划逐步执行
                    for step_num, step_description in enumerate(plan_steps, 1):
                        self.logger.info(f"[Planning模式] 执行步骤 {step_num}/{len(plan_steps)}: {step_description}")
                        
                        # 构建执行步骤的提示
                        execution_prompt = planning_prompt
                        execution_prompt += "\n\n对话历史:\n"
                        for msg in dialog_history:
                            execution_prompt += f"{msg['role']}: {msg['content']}\n"
                        
                        execution_prompt += "\n执行历史:\n"
                        for entry in execution_history:
                            execution_prompt += f"{entry}\n"
                        
                        # 添加当前步骤信息
                        execution_prompt += f"\n当前需要执行的步骤:\n{step_num}. {step_description}"
                        
                        # 调用LLM生成当前步骤的行动
                        self.logger.info(f"[Planning模式] 为步骤 {step_num} 生成行动")
                        step_response = await self.llm.ainvoke([
                            {"role": "system", "content": execution_prompt}
                        ])
                        
                        # 解析步骤响应中的Action
                        step_info, action = self._parse_step_response(step_response)
                        
                        if not action:
                            self.logger.error(f"[Planning模式] 无法解析步骤 {step_num} 的响应格式")
                            return {"output": f"无法解析步骤 {step_num} 的响应格式，请重试。"}
                        
                        # 更新执行历史
                        execution_history.append(f"Step: {step_info}")
                        execution_history.append(f"Action: {action}")
                        
                        # 检查是否为直接回答
                        if action.startswith("Finish[") and action.endswith("]"):
                            # 提取最终答案
                            final_answer = action[7:-1].strip()
                            self.logger.info(f"[Planning模式] 达到最终答案: {final_answer}")
                            return {"output": final_answer}
                        
                        # 尝试调用工具
                        tool_result = await self._execute_tool(action)
                        self.logger.info(f"[Planning模式] 工具执行结果: {tool_result[:100]}...")
                        
                        # 将工具结果添加到执行历史
                        execution_history.append(f"Result: {tool_result}")
                        
                        # 检查是否达到最大步骤限制
                        if step_num >= self.config.max_steps:
                            break
                    
                    # 如果执行完所有计划步骤或达到最大步数，生成总结
                    self.logger.info("[Planning模式] 执行完所有计划步骤，生成最终总结")
                    
                    # 构建总结提示
                    summary_prompt = planning_prompt
                    summary_prompt += "\n\n对话历史:\n"
                    for msg in dialog_history:
                        summary_prompt += f"{msg['role']}: {msg['content']}\n"
                    
                    summary_prompt += "\n执行历史:\n"
                    for entry in execution_history:
                        summary_prompt += f"{entry}\n"
                    
                    summary_prompt += "\n请根据以上执行历史，总结最终结果，使用Finish[最终答案]格式输出。"
                    
                    # 生成最终总结
                    summary_response = await self.llm.ainvoke([
                        {"role": "system", "content": summary_prompt}
                    ])
                    
                    # 尝试提取总结中的最终答案
                    if "Finish[" in summary_response and "]" in summary_response:
                        finish_start = summary_response.index("Finish[") + 7
                        finish_end = summary_response.rfind("]")
                        if finish_start < finish_end:
                            final_answer = summary_response[finish_start:finish_end].strip()
                            return {"output": final_answer}
                    
                    # 如果无法提取，直接返回总结
                    return {"output": summary_response}
                    
                def _parse_plan(self, response):
                    """解析LLM生成的计划，提取步骤列表"""
                    try:
                        plan_steps = []
                        if "Plan:" in response:
                            plan_section = response[response.index("Plan:"):]
                            
                            # 提取每个步骤
                            for line in plan_section.split("\n"):
                                line = line.strip()
                                if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or \
                                   line.startswith("4.") or line.startswith("5."):
                                    # 提取步骤编号和描述
                                    if "." in line:
                                        step_desc = line.split(".", 1)[1].strip()
                                        if step_desc:
                                            plan_steps.append(step_desc)
                        return plan_steps
                    except Exception as e:
                        self.logger.error(f"[Planning模式] 解析计划失败: {str(e)}")
                        return []
                    
                def _parse_step_response(self, response):
                    """解析LLM步骤响应，提取步骤信息和Action"""
                    try:
                        step_info = None
                        action = None
                        
                        # 提取Step部分
                        if "Step:" in response:
                            step_start = response.index("Step:") + 5
                            step_end = response.find("Action:", step_start)
                            if step_end != -1:
                                step_info = response[step_start:step_end].strip()
                            else:
                                step_info = response[step_start:].strip()
                        
                        # 提取Action部分
                        if "Action:" in response:
                            action_start = response.index("Action:") + 7
                            action = response[action_start:].strip()
                        
                        return step_info, action
                    except Exception as e:
                        self.logger.error(f"[Planning模式] 解析步骤响应失败: {str(e)}")
                        return None, None
                    
                async def _execute_tool(self, action_str):
                    """执行工具调用"""
                    try:
                        # 简单的工具调用格式解析
                        # 格式: tool_name(param1=value1, param2=value2)
                        if "(" in action_str and ")" in action_str:
                            # 提取工具名称
                            tool_name_end = action_str.find("(")
                            if tool_name_end == -1:
                                return "工具调用格式错误"
                            
                            tool_name = action_str[:tool_name_end].strip()
                            
                            # 检查工具是否存在
                            if tool_name not in self.tool_map:
                                return f"未知工具: {tool_name}"
                            
                            # 提取参数部分
                            params_str = action_str[tool_name_end+1:-1].strip()
                            
                            # 解析参数
                            params = {}
                            if params_str:
                                # 简单的参数解析
                                for param_pair in params_str.split(","):
                                    if "=" in param_pair:
                                        key, value = param_pair.split("=", 1)
                                        key = key.strip()
                                        # 移除可能的引号
                                        value = value.strip().strip("'\" ")
                                        params[key] = value
                            
                            # 创建工具调用
                            tool_call = ToolCall(
                                name=tool_name,
                                parameters=params
                            )
                            
                            # 调用工具
                            self.logger.info(f"[React模式] 调用工具: {tool_name}, 参数: {params}")
                            result = await mcp_server.call_tool(tool_call)
                            return result.result
                        else:
                            return "工具调用格式错误"
                    except Exception as e:
                        self.logger.error(f"[React模式] 执行工具失败: {str(e)}")
                        return f"工具执行失败: {str(e)}"
            
            # 创建并返回Planning执行器
            return PlanningExecutor(self.config, langchain_tools, tool_map, llm)
            
        except Exception as e:
            self.logger.error(f"[Planning模式] 创建Planning执行器失败: {str(e)}")
            
            # 创建一个简化的Fallback Planning执行器
            class FallbackPlanningExecutor:
                def __init__(self, config):
                    self.config = config
                    self.llm_service = VolcLLMService()
                    self.logger = logging.getLogger(f"FallbackPlanningExecutor")
                
                async def ainvoke(self, inputs):
                    user_input = inputs.get("input", "")
                    
                    # 准备简化的Planning模式系统提示
                    system_prompt = f"""
                    你是{self.config.name}，一个{self.config.role}。
                    
                    请按照Planning模式思考并回答问题：
                    1. 首先制定简单的计划
                    2. 然后直接给出最终答案
                    
                    请严格按照以下格式输出：
                    Plan: [简单的执行计划]
                    Action: Finish[最终答案]
                    """
                    
                    try:
                        # 调用LLM生成回答
                        self.logger.info(f"[Planning模式-异常恢复] 调用大模型回答问题")
                        response = await self.llm_service.generate_async(
                            prompt=user_input,
                            system_prompt=system_prompt,
                            temperature=0.7
                        )
                        
                        # 解析响应，提取最终答案
                        if "Action: Finish[" in response and "]" in response:
                            finish_start = response.index("Action: Finish[") + 15
                            finish_end = response.rfind("]")
                            if finish_start < finish_end:
                                final_answer = response[finish_start:finish_end].strip()
                                return {"output": final_answer}
                        
                        # 如果解析失败，返回完整响应
                        return {"output": response}
                    except Exception as e:
                        self.logger.error(f"[Planning模式-异常恢复] 调用大模型失败: {str(e)}")
                        return {"output": "系统在处理您的请求时遇到技术问题，请稍后重试。"}
            
            return FallbackPlanningExecutor(self.config)
    
    async def process_request(self, request: str, chat_history: Optional[List[Dict]] = None, db=None) -> str:
        """
        处理用户请求 - Planning模式实现
        
        Args:
            request: 用户请求文本
            chat_history: 聊天历史记录，用于上下文理解
            db: 数据库会话（可选）
            
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"[Planning模式] 开始处理请求: {request}")
            
            # 对于日期和时间类问题，我们可以直接获取系统时间（快速路径）
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
            
            # 所有其他问题都使用Planning模式的Agent执行器处理
            try:
                self.logger.info(f"[Planning模式] 使用大模型和Planning流程处理问题")
                
                # 准备执行器输入 - 符合Planning模式的要求
                inputs = {
                    "input": request
                }
                
                # 如果提供了聊天历史，添加到输入中
                if chat_history:
                    inputs["chat_history"] = chat_history
                
                self.logger.info(f"[Planning模式] 调用Agent执行器 (Planning模式), 输入: {inputs}")
                
                # 直接调用Agent执行器 - 这是Planning模式的核心循环
                response = await self.agent_executor.ainvoke(inputs)
                
                self.logger.info(f"[Planning模式] Agent执行器返回结果: {response}")
                
                # 从Planning模式的执行结果中提取输出
                direct_answer = response.get("output", "")
                
                self.logger.info(f"[Planning模式] 从Planning结果中提取的回答: '{direct_answer}'")
                
                # 确保有有效回答
                if not direct_answer or direct_answer.strip() == "" or direct_answer == "无法生成响应":
                    self.logger.warning(f"[Planning模式] 回答无效，使用备用回复")
                    direct_answer = f"根据您的问题: {request}，我无法提供具体回答。请尝试提供更多细节或换一种方式提问。"
                
                # 直接返回Planning模式生成的最终答案
                return direct_answer
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[Planning模式] 调用失败: {error_msg}", exc_info=True)
                # 即使失败也返回有意义的错误信息
                return f"处理您的问题时遇到错误: {error_msg}。系统使用的是Planning模式的Agent，但调用过程中出现了问题。"
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            # 返回简洁的错误信息
            return f"处理您的请求时遇到了问题：{str(e)}。请稍后重试。"

    
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
    'AgentService',
    'agent_service'
]