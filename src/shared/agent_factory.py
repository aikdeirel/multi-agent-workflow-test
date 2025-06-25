import logging
from typing import List, Dict, Any, Type
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain.tools import BaseTool
from langchain.callbacks.base import BaseCallbackHandler

from config import load_json_setting, get_global_settings
from prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)


def create_llm() -> ChatMistralAI:
    """
    Create a standardized LLM instance for operators.
    
    Returns:
        Configured ChatMistralAI instance
    """
    settings = get_global_settings()
    model_config = load_json_setting("model_config")
    
    return ChatMistralAI(
        model=settings.mistral_model,
        temperature=model_config["temperature"],
        max_tokens=model_config["max_tokens"],
        timeout=model_config["timeout"],
    )


def create_react_prompt_template(system_prompt_name: str) -> PromptTemplate:
    """
    Create a standardized ReAct prompt template for operators.
    
    Args:
        system_prompt_name: Name of the system prompt file to load
        
    Returns:
        Configured PromptTemplate
    """
    # Load system prompt
    prompt_manager = get_prompt_manager()
    system_prompt = prompt_manager.get_prompt(system_prompt_name)
    
    # Create standardized ReAct template
    react_template = f"""{system_prompt}

TOOLS:
------

You have access to the following tools:

{{tools}}

To use a tool, you MUST use this EXACT format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL SINGLE-ACTION RULES:
- YOU CAN ONLY PERFORM ONE ACTION PER RESPONSE
- NEVER combine multiple Action/Action Input pairs in a single response
- After generating Action and Action Input, STOP and wait for the Observation
- Do NOT write multiple actions like "Action: ... Action: ..." in the same response
- Do NOT include placeholder text like "(After receiving...)" or "(Then I'll...)"
- Each response must contain EITHER one Action OR one Final Answer, NEVER both
- If you need multiple operations, use them one at a time across multiple responses

IMPORTANT RULES:
- You must EITHER generate an Action OR a Final Answer, NEVER both in the same response
- If you need to use a tool, generate Action and Action Input, then wait for Observation
- Only generate Final Answer when you have all the information needed to answer the question
- Do not include example text like "[After receiving the tool response]" in your actual response

Begin!

Question: {{input}}
Thought:{{agent_scratchpad}}"""

    return PromptTemplate.from_template(react_template)


def create_operator_agent(
    operator_name: str,
    tools: List[BaseTool],
    callback_class: Type[BaseCallbackHandler],
    system_prompt_name: str
) -> AgentExecutor:
    """
    Create a standardized operator agent.
    
    Args:
        operator_name: Name of the operator (for logging)
        tools: List of tools for the agent
        callback_class: Callback handler class to instantiate
        system_prompt_name: Name of the system prompt file
        
    Returns:
        Configured AgentExecutor
    """
    try:
        # Create LLM
        llm = create_llm()
        
        # Create prompt template
        prompt_template = create_react_prompt_template(system_prompt_name)
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=llm, 
            tools=tools, 
            prompt=prompt_template
        )
        
        # Create executor with standardized configuration
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=5,
            max_execution_time=120,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            callbacks=[callback_class()],
        )
        
        logger.info(f"{operator_name} operator agent created successfully")
        return executor
        
    except Exception as e:
        logger.error(f"Error creating {operator_name} operator agent: {str(e)}")
        raise RuntimeError(f"Failed to create {operator_name} operator agent: {str(e)}")