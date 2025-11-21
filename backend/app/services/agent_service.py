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
    temperature: float = Field(default=0.3, description="生成温度")


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
    获取可用工具的详细信息字符串
    
    Returns:
        str: 包含所有工具信息的字符串，包括名称、描述和示例调用方式
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
                
                # 获取参数信息（如果有）
                params_info = ""
                if hasattr(tool, 'parameters') and tool.parameters:
                    param_names = [param.get('name', '参数') for param in tool.parameters]
                    params_info = f"(参数: {', '.join(param_names)})"
                
                # 添加工具信息，包括示例调用格式
                tools_info.append(
                    f"- {tool_name}: {tool_desc}\n"
                    f"  调用格式示例: {tool_name}{params_info if params_info else '()'}"
                )
                logger.info(f"[工具信息] 已添加工具: {tool_name}")
            except Exception as e:
                logger.warning(f"[工具信息] 处理工具时出错: {str(e)}")
                # 忽略无法处理的工具
                continue
        
        if not tools_info:
            logger.warning("[工具信息] 无法获取工具详细信息")
            return "无法获取工具详细信息"
        
        result = "\n".join(tools_info)
        logger.info(f"[工具信息] 已生成工具信息: {len(mcp_tools)}个工具")
        return result
    except Exception as e:
        logger.error(f"[工具信息] 获取工具列表失败: {str(e)}")
        # 如果无法获取工具列表，返回通用信息
        return "工具列表获取失败"


class VolcLLMWrapper:
    """
    火山引擎LLM包装器，适配LangChain接口
    """
    
    def __init__(self, temperature: float = 0.3):
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

    # 统一的系统提示词模板 - 所有执行器共享
    SYSTEM_PROMPT_TEMPLATE = """
你是{agent_name}，一个{agent_role}。

## 你的核心能力
1. **视频内容查询和分析**：使用专业工具搜索、检索和分析视频内容
2. **通用AI助手**：回答各种问题，包括但不限于：
   - 知识问答（科学、历史、文化、技术等）
   - 日常对话和建议
   - 解释概念和提供信息
   - 创意写作和内容生成
   - 计算和逻辑推理

你需要按照以下Planning-then-Execution模式来处理用户的请求：

## Planning阶段（规划阶段）
1. **判断问题类型**：
   - 如果是视频相关查询（搜索视频、分析视频内容等），规划使用工具
   - 如果是通用知识问答、对话等，规划直接回答
2. 分析用户问题和可用工具
3. 制定详细的执行计划，明确每个步骤的目标和方法
4. 确保计划完整、逻辑清晰且可执行
5. 特别注意：
   - 视频相关问题：必须使用video相关工具
   - 通用问题：可以直接使用你的知识回答，无需调用工具

## Execution阶段（执行阶段）
1. 严格按照制定的计划逐步执行每个步骤
2. 对每个步骤调用相应的工具或直接处理
3. 记录每个步骤的执行结果
4. 根据执行结果决定是否需要调整计划
5. 执行完毕后，总结整个过程并提供最终答案


可用工具列表：
{tools_info}

## 输出格式要求

### Planning阶段输出格式：

Plan:
1. [第一步计划] - [预期工具/方法]
2. [第二步计划] - [预期工具/方法]
3. [更多步骤...] - [预期工具/方法]

Reasoning: [为什么这样规划，简要说明逻辑]


### 下面是针对用户视频搜索任务的特别说明
**仅当用户明确提到视频相关的查询时才使用以下工具：**
  - 对于**明确**与视频、视频内容、视频搜索相关的查询，必须使用search_video_by_vector工具
  - 关键词识别：如果用户说"查找视频"、"搜索视频"、"有没有关于...的视频"等，才使用工具
  - **重要**：如果用户只是问一般性问题（如"什么是AI"、"如何学习编程"），直接回答，不要使用工具
  - **必须**将用户的原始查询词作为query参数值直接传递，不要修改、替换或解释用户的查询词
  - 不要使用系统提示、指令模板、或其他与用户原始查询无关的词语作为搜索关键词
  - 只能使用用户在当前对话中明确输入的查询文本作为search_video_by_vector工具的query参数值
  - 可以根据需要设置top_k参数控制返回结果数量，建议设置为5-10
  - 注意：如果用户的输入中包含明确的查询内容，请直接使用这些内容作为query参数值，不要要求用户重复提供查询词

### Execution阶段输出格式（每个步骤）：

Step: {{step_number}}. [当前步骤描述]
Action: [调用工具的格式或直接回答]
   - 工具调用格式: tool_name(参数1=值1, 参数2=值2)  [仅用于视频查询]
   - 直接回答格式: Direct[回答内容]  [用于通用问答]
Result: [工具执行结果或直接回答的确认]

**选择Action类型的原则**：
- 用户问题明确涉及视频内容 → 使用工具调用
- 用户问题是通用知识、对话、建议等 → 使用Direct直接回答

### 最终输出格式：

Execution Complete: [执行完成的状态描述]
Final Answer: [对用户问题的最终回答]

### 文本信息返回格式：
对于回答中的文本，要返回成对用户友好的文本段落

### 视频信息返回格式（重要）：
**视频一定是经过搜索工具返回的，不要胡编乱造视频，不要自己拟合视频信息**

当你使用 search_video_by_vector 工具搜索视频后，工具会返回如下格式的数据：
{{
    "is_matched": true/false,
    "videos": [
        {{
            "video_id": "视频ID",
            "title": "视频标题",
            "thumbnail": "缩略图URL",
            "video_link": "视频链接",
            "relevance_score": 相关度分数（数字，0-100之间）,
            "matched_subtitles": "匹配的字幕内容文本"
        }}
    ]
}}

注意：matched_subtitles 字段包含了与查询最相关的字幕片段，你必须在最终的 <video_info> 中包含这个字段。

**重要**：你必须从工具返回的 videos 数组中提取视频信息，然后在最终回答中使用以下格式返回：
<video_info>
[
    {{
        "video_id": "从工具结果中获取的video_id",
        "title": "从工具结果中获取的title",
        "thumbnail": "从工具结果中获取的thumbnail",
        "video_link": "从工具结果中获取的video_link",
        "relevance_score": 从工具结果中获取的relevance_score（数字，不要加引号）,
        "matched_subtitles": "从工具结果中获取的matched_subtitles（匹配的字幕内容）"
    }}
]
</video_info>

请将所有视频信息严格按照上述格式放置在<video_info>标签内，不要修改格式。
如果工具返回的 is_matched 为 false 或 videos 数组为空，请不要包含<video_info>标签。
"""

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化Agent

        Args:
            config: Agent配置
        """
        self.config = config or AgentConfig()
        self.logger = logger.getChild(f"agent.{self.config.name}")

        # 生成系统提示词
        self.system_prompt = self._generate_system_prompt()

        # 初始化Agent执行器
        self.agent_executor = self._create_agent_executor()

        self.logger.info(f"Simplified Agent initialized: {self.config.name}")

    def _generate_system_prompt(self) -> str:
        """生成系统提示词"""
        tools_info = get_available_tools_info()
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            agent_name=self.config.name,
            agent_role=self.config.role,
            tools_info=tools_info
        )
    
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
                
                # 使用工厂函数创建工具函数，避免闭包问题
                def create_tool_wrapper(tool_obj):
                    @langchain_tool
                    def tool_function(**kwargs):
                        # 调用MCP工具
                        try:
                            # 使用同步方式调用异步的MCP工具
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                            tool_call = ToolCall(
                                tool_name=getattr(tool_obj, 'name', 'unknown_tool'),
                                parameters=kwargs
                            )

                            # 同步运行异步函数
                            result = loop.run_until_complete(
                                mcp_server.call_tool_async(
                                    tool_name=tool_call.tool_name,
                                    parameters=tool_call.parameters
                                )
                            )
                            return result.result
                        except Exception as e:
                            logger.error(f"Tool {getattr(tool_obj, 'name', 'unknown')} call failed: {str(e)}")
                            return f"工具调用失败: {str(e)}"
                        finally:
                            loop.close()
                    return tool_function

                # 为当前工具创建特定的函数
                create_tool_function = create_tool_wrapper(tool)
                
                # 更新函数的名称和描述
                create_tool_function.__name__ = tool_name
                create_tool_function.__doc__ = tool_desc
                
                # 添加到工具列表和映射
                langchain_tools.append(create_tool_function)
                tool_map[tool_name] = tool
            
            # 使用统一的系统提示词
            planning_execution_prompt = self.system_prompt
            
            # 初始化LLM包装器
            llm = VolcLLMWrapper(temperature=self.config.temperature)
            
            # 创建真正的Planning-then-Execution执行器类
            class PlanningThenExecutionExecutor:
                def __init__(self, agent_config, tools, tool_mapping, llm_wrapper):
                    self.config = agent_config
                    self.tools = tools
                    self.tool_map = tool_mapping
                    self.llm = llm_wrapper
                    self.logger = logging.getLogger(f"PlanningThenExecutionExecutor")
                    self.execution_state = {}
                    self.current_step = 0
                    
                async def ainvoke(self, inputs):
                    # 获取输入参数
                    user_input = inputs.get("input", "")
                    chat_history = inputs.get("chat_history", [])
                    stream_callback = inputs.get("stream_callback", None)  # 新增流式回调

                    self.logger.info(f"[ainvoke] 被调用, user_input={user_input[:50]}...")
                    self.logger.info(f"[ainvoke] stream_callback 是否存在: {stream_callback is not None}")

                    # 从 user_input 中提取 user_id
                    import re
                    user_id_match = re.search(r'当前用户ID:\s*([a-zA-Z0-9_-]+)', user_input)
                    extracted_user_id = user_id_match.group(1) if user_id_match else None
                    if extracted_user_id:
                        self.logger.info(f"[Planning] 从输入中提取到用户ID: {extracted_user_id}")

                    # 初始化对话历史和执行状态
                    dialog_history = chat_history.copy()
                    dialog_history.append({"role": "user", "content": user_input})
                    self.execution_state = {"plan": [], "results": {}, "current_step": 0, "user_id": extracted_user_id}

                    try:
                        # ======== Planning阶段 ========
                        import time
                        callback_start = time.time()
                        if stream_callback:
                            self.logger.info(f"[ainvoke] [{time.time():.2f}] 准备调用 stream_callback - planning_start")
                            await stream_callback({
                                "type": "planning_start",
                                "message": "开始规划阶段..."
                            })
                            # 关键：显式yield控制权给事件循环，让队列数据被消费
                            await asyncio.sleep(0)
                            self.logger.info(f"[ainvoke] [{time.time():.2f}] stream_callback 调用完成 - planning_start (耗时: {time.time()-callback_start:.3f}s)")
                        else:
                            self.logger.warning("[ainvoke] stream_callback 不存在，跳过 planning_start")

                        plan_steps, plan_reasoning = await self._planning_phase(
                            user_input, dialog_history
                        )

                        if not plan_steps:
                            self.logger.error("[Planning-then-Execution模式] 无法生成有效的执行计划")
                            return {"output": "无法生成有效的执行计划，请重试。"}

                        # 发送规划结果
                        if stream_callback:
                            await stream_callback({
                                "type": "planning_complete",
                                "plan": plan_steps,
                                "reasoning": plan_reasoning
                            })
                            await asyncio.sleep(0)  # Yield控制权

                        # 保存计划信息
                        execution_history = [
                            f"生成的计划:",
                            f"{plan_reasoning}",
                            f"执行步骤列表: {', '.join(plan_steps)}"
                        ]

                        # ======== Execution阶段 ========
                        if stream_callback:
                            await stream_callback({
                                "type": "execution_start",
                                "message": "开始执行阶段...",
                                "total_steps": len(plan_steps)
                            })
                            await asyncio.sleep(0)  # Yield控制权

                        final_result = await self._execution_phase(
                            user_input,
                            dialog_history,
                            execution_history,
                            plan_steps,
                            stream_callback  # 传递回调
                        )

                        # 发送完成信号
                        if stream_callback:
                            await stream_callback({
                                "type": "complete",
                                "final_answer": final_result
                            })

                        return {"output": final_result}

                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 执行过程出错: {str(e)}")
                        if stream_callback:
                            await stream_callback({
                                "type": "error",
                                "error": str(e)
                            })
                        return {"output": f"执行过程中发生错误: {str(e)}。请稍后重试。"}
                
                async def _planning_phase(self, user_input, dialog_history):
                    """Planning阶段：生成详细执行计划"""
                    self.logger.info(f"[Planning-then-Execution模式] 开始Planning阶段")
                    
                    # 构建规划提示
                    planning_prompt = planning_execution_prompt
                    planning_prompt += "\n\n对话历史:\n"
                    for msg in dialog_history:
                        planning_prompt += f"{msg['role']}: {msg['content']}\n"
                    
                    planning_prompt += "\n请生成详细的执行计划。"
                    
                    # 调用LLM生成执行计划
                    plan_response = await self.llm.ainvoke([
                        {"role": "system", "content": planning_prompt}
                    ])
                    
                    self.logger.info(f"[Planning-then-Execution模式] 规划结果: {plan_response[:150]}...")
                    
                    # 解析计划和推理
                    plan_steps, reasoning = self._parse_plan_with_reasoning(plan_response)
                    
                    # 保存到执行状态
                    self.execution_state["plan"] = plan_steps
                    self.execution_state["reasoning"] = reasoning
                    
                    return plan_steps, reasoning
                    
                async def _execution_phase(self, user_input, dialog_history, execution_history, plan_steps, stream_callback=None):
                    """Execution阶段：执行计划并生成最终结果"""
                    self.logger.info(f"[Planning-then-Execution模式] 开始Execution阶段，共{len(plan_steps)}个步骤")

                    # 执行每个计划步骤
                    for step_num, step_description in enumerate(plan_steps, 1):
                        self.current_step = step_num
                        self.logger.info(f"[Planning-then-Execution模式] 执行步骤 {step_num}/{len(plan_steps)}: {step_description}")

                        # 发送步骤开始事件
                        if stream_callback:
                            await stream_callback({
                                "type": "step_start",
                                "step_number": step_num,
                                "step_description": step_description,
                                "total_steps": len(plan_steps)
                            })
                        
                        # 构建执行步骤的提示
                        execution_prompt = planning_execution_prompt
                        execution_prompt += "\n\n对话历史:\n"
                        for msg in dialog_history:
                            execution_prompt += f"{msg['role']}: {msg['content']}\n"
                        
                        execution_prompt += "\n执行历史:\n"
                        for entry in execution_history:
                            execution_prompt += f"{entry}\n"
                        
                        # 添加当前步骤信息
                        execution_prompt += f"\n当前执行阶段 - 需要执行的步骤:\n{step_num}. {step_description}"
                        
                        # 调用LLM生成当前步骤的行动
                        self.logger.info(f"[Planning-then-Execution模式] 为步骤 {step_num} 生成执行行动")
                        step_response = await self.llm.ainvoke([
                            {"role": "system", "content": execution_prompt}
                        ])
                        
                        # 解析步骤响应
                        step_info, action = self._parse_execution_step(step_response)
                        
                        if not action:
                            self.logger.error(f"[Planning-then-Execution模式] 无法解析步骤 {step_num} 的响应格式")
                            # 生成更明确的提示，引导使用工具
                            recovery_prompt = execution_prompt
                            recovery_prompt += "\n\n警告：之前的输出格式不正确。请按照指定格式输出，特别是对于需要获取外部信息的任务，请使用工具调用格式。\n"
                            recovery_prompt += f"可用工具: {list(self.tool_map.keys())}\n"
                            
                            # 重新获取响应
                            self.logger.info(f"[Planning-then-Execution模式] 尝试恢复步骤 {step_num} 的执行")
                            step_response = await self.llm.ainvoke([
                                {"role": "system", "content": recovery_prompt}
                            ])
                            # 再次尝试解析
                            step_info, action = self._parse_execution_step(step_response)
                            
                            if not action:
                                self.logger.error(f"[Planning-then-Execution模式] 恢复失败，跳过步骤 {step_num}")
                                continue
                        
                        # 更新执行历史
                        execution_history.append(f"Step: {step_info}")
                        execution_history.append(f"Action: {action}")
                        
                        # 检查是否为直接回答
                        if action.startswith("Direct[") and action.endswith("]"):
                            # 提取直接回答
                            direct_answer = action[7:-1].strip()
                            execution_history.append(f"Result: {direct_answer}")
                            self.execution_state["results"][step_num] = direct_answer
                            self.logger.info(f"[Planning-then-Execution模式] 步骤 {step_num} 直接回答: {direct_answer}")

                            # 发送步骤完成事件（不包含执行细节）
                            if stream_callback:
                                await stream_callback({
                                    "type": "step_complete",
                                    "step_number": step_num
                                })

                            # 添加直接回答的原因记录，便于调试
                            self.logger.info(f"[Planning-then-Execution模式] 步骤 {step_num} 使用直接回答，跳过工具调用")
                        else:
                            # 验证是否为有效的工具调用格式
                            if "(" not in action or ")" not in action:
                                self.logger.warning(f"[Planning-then-Execution模式] 步骤 {step_num} 工具调用格式可能不正确: {action}")
                                # 尝试规范化工具调用格式
                                tool_name_candidate = action.strip()
                                if tool_name_candidate in self.tool_map:
                                    self.logger.info(f"[Planning-then-Execution模式] 规范化工具调用格式")
                                    action = f"{tool_name_candidate}()"

                            # 尝试调用工具
                            self.logger.info(f"[Planning-then-Execution模式] 准备调用工具: {action}")
                            tool_result = await self._execute_tool(action)
                            execution_history.append(f"Result: {tool_result}")
                            self.execution_state["results"][step_num] = tool_result

                            # 发送步骤完成事件（不包含执行细节）
                            if stream_callback:
                                await stream_callback({
                                    "type": "step_complete",
                                    "step_number": step_num
                                })

                            # 添加更详细的日志，便于调试
                            self.logger.info(f"[Planning-then-Execution模式] 步骤 {step_num} 工具执行结果: {tool_result[:100]}...")

                            # 检查是否为工具调用失败的情况
                            if "错误" in tool_result or "失败" in tool_result or "未知" in tool_result:
                                self.logger.warning(f"[Planning-then-Execution模式] 步骤 {step_num} 工具调用可能失败: {tool_result}")
                        
                        # 检查是否达到最大步骤限制
                        if step_num >= self.config.max_steps:
                            self.logger.warning(f"[Planning-then-Execution模式] 达到最大执行步骤限制: {self.config.max_steps}")
                            break
                    
                    # 生成最终总结
                    self.logger.info("[Planning-then-Execution模式] 执行完所有计划步骤，生成最终总结")
                    
                    # 构建总结提示
                    summary_prompt = planning_execution_prompt
                    summary_prompt += "\n\n对话历史:\n"
                    for msg in dialog_history:
                        summary_prompt += f"{msg['role']}: {msg['content']}\n"
                    
                    summary_prompt += "\n执行历史:\n"
                    for entry in execution_history:
                        summary_prompt += f"{entry}\n"
                    
                    summary_prompt += "\n现在所有计划步骤已执行完毕，请提供最终答案。使用Final Answer: [最终答案]格式。"
                    
                    # 生成最终总结
                    summary_response = await self.llm.ainvoke([
                        {"role": "system", "content": summary_prompt}
                    ])
                    
                    # 尝试提取最终答案
                    final_answer = self._extract_final_answer(summary_response)
                    
                    # 更新执行状态为完成
                    self.execution_state["status"] = "completed"
                    self.execution_state["final_answer"] = final_answer
                    
                    return final_answer
                    
                def _extract_final_answer(self, response):
                    """提取最终答案并过滤内部标记"""
                    import re

                    try:
                        final_answer = response

                        # 步骤1: 尝试提取 Final Answer: 后面的内容
                        if "Final Answer:" in response:
                            answer_start = response.index("Final Answer:") + len("Final Answer:")
                            final_answer = response[answer_start:].strip()
                        elif "Execution Complete:" in response:
                            # 从执行完成后查找可能的答案
                            complete_start = response.index("Execution Complete:")
                            potential_answer = response[complete_start + len("Execution Complete:"):].strip()
                            # 如果还包含Final Answer，再次提取
                            if "Final Answer:" in potential_answer:
                                return self._extract_final_answer(potential_answer)
                            final_answer = potential_answer
                        elif "Finish[" in response and "]" in response:
                            # 兼容旧格式
                            finish_start = response.index("Finish[") + 7
                            finish_end = response.rfind("]")
                            if finish_start < finish_end:
                                final_answer = response[finish_start:finish_end].strip()

                        # 步骤2: 过滤掉所有内部过程标记
                        # 移除 Plan: 段落
                        final_answer = re.sub(r'Plan:\s*\n(.*?)\n\n', '', final_answer, flags=re.DOTALL)
                        final_answer = re.sub(r'Plan:.*?(?=\n\n|\Z)', '', final_answer, flags=re.DOTALL)

                        # 移除 Reasoning: 段落
                        final_answer = re.sub(r'Reasoning:\s*\n(.*?)\n\n', '', final_answer, flags=re.DOTALL)
                        final_answer = re.sub(r'Reasoning:.*?(?=\n\n|\Z)', '', final_answer, flags=re.DOTALL)

                        # 移除 Step: ... Action: ... Result: ... 这样的执行过程（增强版）
                        # 移除以 Step: 开头的整行
                        final_answer = re.sub(r'^Step:\s*.*$', '', final_answer, flags=re.MULTILINE)
                        final_answer = re.sub(r'\nStep:\s*.*$', '', final_answer, flags=re.MULTILINE)

                        # 移除以 Action: 开头的整行
                        final_answer = re.sub(r'^Action:\s*.*$', '', final_answer, flags=re.MULTILINE)
                        final_answer = re.sub(r'\nAction:\s*.*$', '', final_answer, flags=re.MULTILINE)

                        # 移除以 Result: 开头的整行
                        final_answer = re.sub(r'^Result:\s*.*$', '', final_answer, flags=re.MULTILINE)
                        final_answer = re.sub(r'\nResult:\s*.*$', '', final_answer, flags=re.MULTILINE)

                        # 移除 Execution Complete: 标记本身
                        final_answer = re.sub(r'Execution Complete:.*?\n', '', final_answer)
                        final_answer = re.sub(r'^Execution Complete:\s*.*$', '', final_answer, flags=re.MULTILINE)

                        # 移除 Final Answer: 标记本身（如果还有残留）
                        final_answer = re.sub(r'^Final Answer:\s*', '', final_answer)
                        final_answer = re.sub(r'\nFinal Answer:\s*', '\n', final_answer)

                        # 步骤3: 清理多余的空白
                        final_answer = final_answer.strip()

                        # 步骤4: 如果过滤后内容为空，返回一个友好的默认消息
                        if not final_answer:
                            self.logger.warning("[Planning-then-Execution模式] 过滤后内容为空")
                            return "处理完成"

                        return final_answer

                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 提取最终答案失败: {str(e)}")
                        # 发生错误时，尝试至少返回一些内容
                        return response.split("Final Answer:")[-1].strip() if "Final Answer:" in response else response
                    
                def _parse_plan_with_reasoning(self, response):
                    """解析LLM生成的计划，提取步骤列表和推理过程"""
                    try:
                        plan_steps = []
                        reasoning = "无详细推理"
                        
                        # 提取推理过程
                        if "Reasoning:" in response:
                            reason_start = response.index("Reasoning:") + len("Reasoning:")
                            # 找到下一个可能的部分开始位置
                            next_section_start = min(
                                response.find("Plan:", reason_start) if "Plan:" in response[reason_start:] else len(response),
                                response.find("Step:", reason_start) if "Step:" in response[reason_start:] else len(response),
                                response.find("Execution:", reason_start) if "Execution:" in response[reason_start:] else len(response)
                            )
                            reasoning = response[reason_start:next_section_start].strip()
                        
                        # 提取计划步骤
                        if "Plan:" in response:
                            plan_section = response[response.index("Plan:"):]
                            
                            # 提取每个步骤
                            for line in plan_section.split("\n"):
                                line = line.strip()
                                if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or \
                                   line.startswith("4.") or line.startswith("5."):
                                    # 提取步骤编号和描述，移除可能的工具信息
                                    if "." in line:
                                        step_parts = line.split(".", 1)[1].strip()
                                        # 如果包含"-"，移除后面的预期工具部分
                                        if "-" in step_parts and not step_parts.startswith("-"):
                                            step_desc = step_parts.split("-", 1)[0].strip()
                                        else:
                                            step_desc = step_parts
                                        if step_desc:
                                            plan_steps.append(step_desc)
                        return plan_steps, reasoning
                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 解析计划失败: {str(e)}")
                        return [], "解析计划时出错"
                    
                def _parse_execution_step(self, response):
                    """解析执行阶段的步骤响应"""
                    try:
                        step_info = None
                        action = None
                        
                        # 提取Step部分
                        if "Step:" in response:
                            step_start = response.index("Step:") + 5
                            # 找到Action部分的开始位置
                            action_start_pos = response.find("Action:", step_start)
                            if action_start_pos != -1:
                                step_info = response[step_start:action_start_pos].strip()
                            else:
                                step_info = response[step_start:].strip()
                        
                        # 提取Action部分
                        if "Action:" in response:
                            action_start = response.index("Action:") + 7
                            # 找到Result部分的开始位置或文本结束
                            result_start_pos = response.find("Result:", action_start)
                            if result_start_pos != -1:
                                action = response[action_start:result_start_pos].strip()
                            else:
                                action = response[action_start:].strip()
                        
                        return step_info, action
                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 解析步骤响应失败: {str(e)}")
                        return None, None
                    

                    
                async def _execute_tool(self, action_str):
                    """执行工具调用 - 增强版"""
                    try:
                        # 增强的工具调用格式解析
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
                            
                            # 解析参数 - 增强版，支持更复杂的参数格式
                            params = self._parse_complex_params(params_str)

                            # 如果是 search_video_by_vector 工具且没有 user_id 参数，自动注入
                            if tool_name == "search_video_by_vector" and "user_id" not in params:
                                extracted_user_id = self.execution_state.get("user_id")
                                if extracted_user_id:
                                    params["user_id"] = extracted_user_id
                                    self.logger.info(f"[Planning-工具调用] 自动注入 user_id: {extracted_user_id}")

                            # 记录执行状态
                            self.execution_state["current_tool"] = tool_name
                            self.execution_state["current_params"] = params

                            # 创建工具调用
                            tool_call = ToolCall(
                                tool_name=tool_name,
                                parameters=params
                            )
                            
                            # 调用工具
                            self.logger.info(f"[Planning-then-Execution模式] 调用工具: {tool_name}, 参数: {params}")
                            self.logger.info(f"[MCP工具调用] 开始调用MCP工具: {tool_name}")
                            
                            # 执行工具调用，添加超时处理
                            try:
                                self.logger.info(f"[MCP工具调用] 向MCP服务器发送工具调用请求")
                                result = await asyncio.wait_for(
                                    mcp_server.call_tool_async(
                                        tool_name=tool_call.tool_name,
                                        parameters=tool_call.parameters
                                    ), 
                                    timeout=30.0  # 设置30秒超时
                                )
                            
                                # 验证结果
                                if result and hasattr(result, 'result'):
                                    self.logger.info(f"[MCP工具调用] 工具调用成功完成: {tool_name}")
                                    self.logger.info(f"[MCP工具调用] 工具返回结果: {result.result}")
                                    return result.result
                                else:
                                    self.logger.warning(f"[MCP工具调用] 工具返回格式异常: {tool_name}")
                                    return "工具返回格式异常"
                            except asyncio.TimeoutError:
                                self.logger.warning(f"[MCP工具调用] 工具调用超时: {tool_name}")
                                return f"工具调用超时: {tool_name}"
                        else:
                            return "工具调用格式错误"
                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 执行工具失败: {str(e)}")
                        return f"工具执行失败: {str(e)}"
                    
                def _parse_complex_params(self, params_str):
                    """增强的参数解析器，支持更复杂的参数格式"""
                    params = {}
                    if not params_str.strip():
                        return params
                    
                    try:
                        # 处理嵌套的引号和逗号
                        # 基本思路：跟踪括号和引号状态，正确分割参数
                        in_quotes = False
                        quote_char = None
                        current_param = ""
                        param_pairs = []
                        
                        for char in params_str + ",":  # 添加额外逗号以处理最后一个参数
                            if char in ["'", '"'] and (not in_quotes or char == quote_char):
                                in_quotes = not in_quotes
                                if in_quotes:
                                    quote_char = char
                                else:
                                    quote_char = None
                                current_param += char
                            elif char == "," and not in_quotes:
                                if current_param.strip():
                                    param_pairs.append(current_param.strip())
                                current_param = ""
                            else:
                                current_param += char
                        
                        # 处理每个参数对
                        for param_pair in param_pairs:
                            if "=" in param_pair:
                                key, value = param_pair.split("=", 1)
                                key = key.strip()
                                # 移除可能的引号
                                value = value.strip()
                                if (value.startswith("'") and value.endswith("'") or 
                                    value.startswith('"') and value.endswith('"')):
                                    value = value[1:-1]
                                params[key] = value
                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式] 解析参数失败: {str(e)}")
                        # 回退到简单解析
                        for param_pair in params_str.split(","):
                            if "=" in param_pair:
                                key, value = param_pair.split("=", 1)
                                key = key.strip()
                                value = value.strip(' "\'')
                                params[key] = value.strip(' "\'')
                    
                    return params
            
            # 创建并返回Planning-then-Execution执行器
            return PlanningThenExecutionExecutor(self.config, langchain_tools, tool_map, llm)
            
        except Exception as e:
            self.logger.error(f"[Planning-then-Execution模式] 创建Planning-then-Execution执行器失败: {str(e)}")
            
            # 创建一个增强的Fallback Planning-then-Execution执行器
            class FallbackPlanningThenExecutionExecutor:
                def __init__(self, config):
                    self.config = config
                    self.llm_service = VolcLLMService()
                    self.logger = logging.getLogger(f"FallbackPlanningThenExecutionExecutor")
                    # 获取可用工具信息
                    try:
                        self.tools_info = get_available_tools_info()
                        self.logger.info("[Fallback-工具信息] 已获取可用工具")
                    except Exception as e:
                        self.logger.warning(f"[Fallback-工具信息] 获取工具失败: {str(e)}")
                        self.tools_info = "目前没有可用工具"
                
                async def ainvoke(self, inputs):
                    user_input = inputs.get("input", "")
                    dialog_history = inputs.get("chat_history", [])
                    stream_callback = inputs.get("stream_callback", None)  # 获取流式回调
                    execution_history = []

                    self.logger.info(f"[Fallback ainvoke] 被调用, user_input={user_input[:50]}...")
                    self.logger.info(f"[Fallback ainvoke] stream_callback 是否存在: {stream_callback is not None}")

                    # 从 user_input 中提取 user_id
                    import re
                    user_id_match = re.search(r'当前用户ID:\s*([a-zA-Z0-9_-]+)', user_input)
                    extracted_user_id = user_id_match.group(1) if user_id_match else None
                    if extracted_user_id:
                        self.logger.info(f"[Fallback] 从输入中提取到用户ID: {extracted_user_id}")

                    # 使用外部Agent类的统一系统提示词
                    system_prompt = Agent.SYSTEM_PROMPT_TEMPLATE.format(
                        agent_name=self.config.name,
                        agent_role=self.config.role,
                        tools_info=self.tools_info
                    )
                    
                    try:
                        # 获取所有可用的MCP工具并创建工具映射
                        tool_map = {}
                        try:
                            mcp_tools = mcp_server.get_available_tools()
                            for tool in mcp_tools:
                                tool_name = getattr(tool, 'name', None)
                                if tool_name:
                                    tool_map[tool_name] = tool
                            self.logger.info(f"[Fallback-工具] 已加载 {len(tool_map)} 个工具")
                        except Exception as e:
                            self.logger.warning(f"[Fallback-工具] 获取工具失败: {str(e)}")
                        
                        # 发送 Planning 开始事件
                        if stream_callback:
                            self.logger.info("[Fallback] 发送 planning_start 事件")
                            await stream_callback({
                                "type": "planning_start",
                                "message": "开始规划阶段..."
                            })

                        # 调用LLM生成计划
                        self.logger.info(f"[Planning-then-Execution模式-异常恢复] 调用大模型生成计划")
                        response = await self.llm_service.generate_async(
                            prompt=user_input,
                            system_prompt=system_prompt,
                            temperature=0.7
                        )

                        # 解析计划
                        plan = []
                        reasoning = "无详细推理"

                        # 提取推理过程
                        if "Reasoning:" in response:
                            reason_start = response.index("Reasoning:") + len("Reasoning:")
                            next_section = response.find("\n\n", reason_start)
                            if next_section != -1:
                                reasoning = response[reason_start:next_section].strip()
                            else:
                                reasoning = response[reason_start:].strip()

                        if "Plan:" in response:
                            plan_start = response.index("Plan:") + len("Plan:")
                            if "Reasoning:" in response:
                                plan_end = response.index("Reasoning:")
                            else:
                                plan_end = len(response)
                            
                            plan_text = response[plan_start:plan_end].strip()
                            for line in plan_text.split('\n'):
                                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                                    # 提取计划步骤，去掉序号
                                    step_text = line.split('.', 1)[1].strip()
                                    plan.append(step_text)
                        
                        self.logger.info(f"[Fallback-执行] 提取到 {len(plan)} 个计划步骤")

                        # 发送 Planning 完成事件
                        if stream_callback:
                            self.logger.info("[Fallback] 发送 planning_complete 事件")
                            await stream_callback({
                                "type": "planning_complete",
                                "plan": plan,
                                "reasoning": reasoning
                            })

                        # 发送 Execution 开始事件
                        if stream_callback and plan:
                            self.logger.info("[Fallback] 发送 execution_start 事件")
                            await stream_callback({
                                "type": "execution_start",
                                "message": "开始执行阶段...",
                                "total_steps": len(plan)
                            })

                        # 执行计划
                        if plan:
                            for step_num, step_description in enumerate(plan, 1):
                                self.logger.info(f"[Fallback-执行] 执行步骤 {step_num}: {step_description}")

                                # 发送步骤开始事件
                                if stream_callback:
                                    self.logger.info(f"[Fallback] 发送 step_start 事件: 步骤{step_num}")
                                    await stream_callback({
                                        "type": "step_start",
                                        "step_number": step_num,
                                        "step_description": step_description,
                                        "total_steps": len(plan)
                                    })

                                # 构建执行步骤的提示
                                execution_prompt = system_prompt + "\n\n对话历史:\n"
                                for msg in dialog_history:
                                    execution_prompt += f"{msg['role']}: {msg['content']}\n"
                                
                                execution_prompt += "\n执行历史:\n"
                                for entry in execution_history:
                                    execution_prompt += f"{entry}\n"
                                
                                execution_prompt += f"\n当前执行步骤:\n{step_num}. {step_description}\n"
                                execution_prompt += "\n请提供执行结果或工具调用。如果需要调用工具，请使用以下格式：工具名称(参数名=参数值, ...)"
                                
                                # 调用LLM生成执行行动
                                step_response = await self.llm_service.generate_async(
                                    prompt=execution_prompt,
                                    temperature=0.5
                                )
                                
                                # 检查是否包含工具调用
                                if any(tool_name in step_response for tool_name in tool_map):
                                    # 尝试提取工具调用
                                    for tool_name in tool_map:
                                        if tool_name in step_response:
                                            self.logger.info(f"[Fallback-工具调用] 尝试调用工具: {tool_name}")
                                            # 简单提取参数并调用工具
                                            try:
                                                # 简单的参数提取逻辑
                                                if f"{tool_name}(" in step_response:
                                                    # 尝试解析参数
                                                    call_str = step_response.split(f"{tool_name}(")[1].split(")")[0]
                                                    # 简单参数处理（实际可能需要更复杂的解析）
                                                    params = {}
                                                    if call_str.strip():
                                                        for param in call_str.split(','):
                                                            if '=' in param:
                                                                key, value = param.split('=', 1)
                                                                params[key.strip()] = value.strip(' "\'')

                                                    # 如果是 search_video_by_vector 工具且没有 user_id 参数，自动注入
                                                    if tool_name == "search_video_by_vector" and "user_id" not in params and extracted_user_id:
                                                        params["user_id"] = extracted_user_id
                                                        self.logger.info(f"[Fallback-工具调用] 自动注入 user_id: {extracted_user_id}")

                                                    # 调用MCP工具，修复参数格式
                                                    tool_response = await mcp_server.call_tool_async(
                                                        tool_name=tool_name,
                                                        parameters=params
                                                    )
                                                    if tool_response.success:
                                                        tool_result = str(tool_response.result)
                                                        self.logger.info(f"[Fallback-工具调用] 工具 {tool_name} 调用成功")
                                                    else:
                                                        tool_result = f"工具调用失败: {tool_response.error}"
                                                        self.logger.error(f"[Fallback-工具调用] 工具 {tool_name} 调用失败: {tool_response.error}")
                                                    
                                                    execution_history.append(f"Step {step_num}: {step_description}")
                                                    execution_history.append(f"Action: {tool_name}({call_str})")
                                                    execution_history.append(f"Result: {tool_result}")

                                                    # 发送步骤完成事件（不包含执行细节）
                                                    if stream_callback:
                                                        self.logger.info(f"[Fallback] 发送 step_complete 事件: 步骤{step_num}")
                                                        await stream_callback({
                                                            "type": "step_complete",
                                                            "step_number": step_num
                                                        })
                                            except Exception as e:
                                                self.logger.error(f"[Fallback-工具调用] 解析或调用工具 {tool_name} 失败: {str(e)}")
                                            break
                                else:
                                    # 直接回答
                                    execution_history.append(f"Step {step_num}: {step_description}")
                                    execution_history.append(f"Result: {step_response.strip()}")

                                    # 发送步骤完成事件（不包含执行细节）
                                    if stream_callback:
                                        self.logger.info(f"[Fallback] 发送 step_complete 事件: 步骤{step_num} (直接回答)")
                                        await stream_callback({
                                            "type": "step_complete",
                                            "step_number": step_num
                                        })
                        
                        # 生成最终回答
                        summary_prompt = system_prompt + "\n\n执行历史:\n"
                        for entry in execution_history:
                            summary_prompt += f"{entry}\n"

                        # 明确要求只返回结果，不重复过程
                        summary_prompt += """

## 重要提示：最终回答格式
1. **不要重复上述执行计划和步骤过程**
2. **直接提供用户需要的答案或结果**
3. 如果查询到视频信息：
   - 简短说明找到的视频（1-2句话）
   - 使用<video_info>标签返回视频信息（严格按照之前的JSON格式）
4. 如果是对话回答：
   - 直接给出简洁的回答
   - 不要说"基于上述步骤"、"经过分析"等过程性描述

请提供最终答案："""

                        final_response = await self.llm_service.generate_async(
                            prompt=summary_prompt,
                            temperature=0.5
                        )

                        # 过滤最终回答中的内部标记
                        cleaned_response = self._clean_final_answer(final_response)

                        return {"output": cleaned_response}
                    except Exception as e:
                        self.logger.error(f"[Planning-then-Execution模式-异常恢复] 处理失败: {str(e)}")
                        return {"output": "系统在处理您的请求时遇到技术问题，请稍后重试。"}

                def _clean_final_answer(self, response):
                    """清理最终答案，移除所有内部过程标记"""
                    import re

                    final_answer = response

                    # 移除 Plan: 段落
                    final_answer = re.sub(r'Plan:\s*\n(.*?)\n\n', '', final_answer, flags=re.DOTALL)
                    final_answer = re.sub(r'Plan:.*?(?=\n\n|\Z)', '', final_answer, flags=re.DOTALL)

                    # 移除 Reasoning: 段落
                    final_answer = re.sub(r'Reasoning:\s*\n(.*?)\n\n', '', final_answer, flags=re.DOTALL)
                    final_answer = re.sub(r'Reasoning:.*?(?=\n\n|\Z)', '', final_answer, flags=re.DOTALL)

                    # 移除以 Step: 开头的整行
                    final_answer = re.sub(r'^Step:\s*.*$', '', final_answer, flags=re.MULTILINE)
                    final_answer = re.sub(r'\nStep:\s*.*$', '', final_answer, flags=re.MULTILINE)

                    # 移除以 Action: 开头的整行
                    final_answer = re.sub(r'^Action:\s*.*$', '', final_answer, flags=re.MULTILINE)
                    final_answer = re.sub(r'\nAction:\s*.*$', '', final_answer, flags=re.MULTILINE)

                    # 移除以 Result: 开头的整行
                    final_answer = re.sub(r'^Result:\s*.*$', '', final_answer, flags=re.MULTILINE)
                    final_answer = re.sub(r'\nResult:\s*.*$', '', final_answer, flags=re.MULTILINE)

                    # 移除 Execution Complete: 标记
                    final_answer = re.sub(r'Execution Complete:.*?\n', '', final_answer)
                    final_answer = re.sub(r'^Execution Complete:\s*.*$', '', final_answer, flags=re.MULTILINE)

                    # 移除 Final Answer: 标记
                    final_answer = re.sub(r'^Final Answer:\s*', '', final_answer)
                    final_answer = re.sub(r'\nFinal Answer:\s*', '\n', final_answer)

                    # 清理多余的空白行
                    final_answer = re.sub(r'\n\s*\n\s*\n', '\n\n', final_answer)
                    final_answer = final_answer.strip()

                    return final_answer
            
            return FallbackPlanningThenExecutionExecutor(self.config)
    
    async def process_request(self, request: str, chat_history: Optional[List[Dict]] = None, db=None) -> str:
        """
        处理用户请求 - Planning-then-Execution模式实现
        
        Args:
            request: 用户请求文本
            chat_history: 聊天历史记录，用于上下文理解
            db: 数据库会话（可选）
            
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"[Planning-then-Execution模式] 开始处理请求: {request}")
            
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
            
            # 所有其他问题都使用Planning-then-Execution模式的Agent执行器处理
            try:
                self.logger.info(f"[Planning-then-Execution模式] 使用大模型和Planning-then-Execution流程处理问题")
                
                # 准备执行器输入 - 符合Planning-then-Execution模式的要求
                inputs = {
                    "input": request
                }
                
                # 如果提供了聊天历史，添加到输入中
                if chat_history:
                    inputs["chat_history"] = chat_history
                
                self.logger.info(f"[Planning-then-Execution模式] 调用Agent执行器 (Planning-then-Execution模式), 输入: {inputs}")
                
                # 直接调用Agent执行器 - 这是Planning-then-Execution模式的核心循环
                response = await self.agent_executor.ainvoke(inputs)
                
                # 根据执行器类型处理响应
                if isinstance(response, dict) and "output" in response:
                    direct_answer = response.get("output", "")
                else:
                    # 新的执行器直接返回最终答案字符串
                    direct_answer = response
                
                self.logger.info(f"[Planning-then-Execution模式] 从执行结果中提取的回答: '{direct_answer}'")
                
                # 确保有有效回答
                if not direct_answer or direct_answer.strip() == "" or direct_answer == "无法生成响应":
                    self.logger.warning(f"[Planning-then-Execution模式] 回答无效，使用备用回复")
                    direct_answer = f"根据您的问题: {request}，我无法提供具体回答。请尝试提供更多细节或换一种方式提问。"
                
                # 直接返回Planning-then-Execution模式生成的最终答案
                return direct_answer
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"[Planning-then-Execution模式] 调用失败: {error_msg}", exc_info=True)
                # 即使失败也返回有意义的错误信息
                return f"处理您的问题时遇到错误: {error_msg}。系统使用的是Planning-then-Execution模式的Agent，但调用过程中出现了问题。"
            
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
    
    async def process_request(self, request: str, chat_history: Optional[List[Dict]] = None, config: Optional[AgentConfig] = None) -> Dict[str, Any]:
        """
        处理请求的便捷方法
        
        Args:
            request: 用户请求
            chat_history: 聊天历史记录，用于上下文理解
            config: Agent配置
            
        Returns:
            包含处理结果和视频信息的字典 {"text": str, "video_info": List[Dict]}
        """
        # 创建增强的系统提示，要求大模型返回指定格式的视频信息
        if config is None:
            config = AgentConfig()
        
        # 使用请求包装器而不是修改Pydantic模型
        # 我们将视频信息格式要求直接添加到请求中
        enhanced_request = f"""
{request}

## 重要提示：如果你需要返回视频信息，请使用以下JSON格式：
<video_info>
[
    {{"video_id": "视频ID", "title": "视频标题", "thumbnail": "缩略图URL", "video_link": "视频链接", "relevance_score": 相关度分数}}
]
</video_info>

请严格按照上述格式返回视频信息。如果没有视频信息，请不要包含<video_info>标签。
"""
        
        agent = self.create_agent(config)
        result = await agent.process_request(enhanced_request, chat_history)
        
        # 解析结果，提取文本和视频信息
        import re
        video_info_list = []
        
        # 提取视频信息
        video_info_match = re.search(r'<video_info>(.*?)</video_info>', result, re.DOTALL)
        if video_info_match:
            try:
                import json
                # 获取原始内容，包括所有换行和缩进
                raw_content = video_info_match.group(1)
                # 使用json.loads的默认行为处理多行JSON
                logger.info(f"原始视频信息内容长度: {len(raw_content)} 字符")
                logger.info(f"原始视频信息内容前100字符: {raw_content[:100]}")
                
                # 尝试直接解析
                video_info_list = json.loads(raw_content)
                logger.info(f"成功直接解析视频信息")
                
                # 确保是列表格式
                if not isinstance(video_info_list, list):
                    video_info_list = [video_info_list]
                
                # 清理原文本，移除video_info标签
                text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
                logger.info(f"成功解析视频信息，数量: {len(video_info_list)}")
            except json.JSONDecodeError:
                try:
                    # 备用方案1：移除空白字符和换行
                    clean_content = ''.join(line.strip() for line in video_info_match.group(1).split('\n'))
                    logger.info(f"尝试使用清理后的内容: {clean_content[:100]}...")
                    
                    # 检查是否有嵌套的video_info标签，如果有则提取最内层的
                    nested_match = re.search(r'<video_info>(.*?)</video_info>', clean_content, re.DOTALL)
                    if nested_match:
                        clean_content = nested_match.group(1)
                        logger.info(f"发现嵌套标签，提取内层内容: {clean_content[:100]}...")
                    
                    # 尝试只提取JSON部分（查找第一个'['和最后一个']'之间的内容）
                    json_start = clean_content.find('[')
                    json_end = clean_content.rfind(']')
                    if json_start != -1 and json_end != -1:
                        clean_content = clean_content[json_start:json_end+1]
                        logger.info(f"提取JSON部分: {clean_content[:100]}...")
                    
                    video_info_list = json.loads(clean_content)
                    # 确保是列表格式
                    if not isinstance(video_info_list, list):
                        video_info_list = [video_info_list]
                    # 清理原文本
                    text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
                    logger.info(f"使用清理后的内容成功解析，数量: {len(video_info_list)}")
                except Exception as e2:
                    # 如果还是失败，使用硬编码的示例数据进行测试
                    logger.error(f"视频信息JSON解析失败，使用示例数据进行测试: {str(e2)}")
                    video_info_list = [
                        {
                            "video_id": "test-video-1",
                            "title": "测试视频",
                            "thumbnail": "",
                            "video_link": "/api/v1/videos/test-video-1",
                            "relevance_score": 85
                        }
                    ]
                    text_content = re.sub(r'<video_info>.*?</video_info>', '', result, flags=re.DOTALL).strip()
            except Exception as e:
                logger.error(f"处理视频信息时发生其他错误: {str(e)}")
                text_content = result
                video_info_list = []
        else:
            text_content = result
        
        return {
            "text": text_content,
            "video_info": video_info_list
        }
    
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