
from abc import ABC, abstractmethod
from langchain_core.tools import tool
import logging
from typing import Optional
from anthropic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel

from ai.llm.client import LLMClient

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    
    name: str = "BaseAgent"
    description: str = "This is a base agent class that should be extended by specific agent implementations."
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm or LLMClient.get_chat_model()
        logger.info(f"{self.name} initialized with LLM: {self.llm}")
        
    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Run the agent with the given arguments and keyword arguments.
        """
        pass

    def as_tool(self):
        
        agent_instance = self
        import functools
        
        @functools.wraps(agent_instance.run)
        def _tool_func(*args, **kwargs):
            logger.info(f'{self.__class__.__name__}: Agent 运行 {agent_instance.name} with args: {args}, kwargs: {kwargs}')            
            try:
                result = agent_instance.run(*args, **kwargs)
                
                if isinstance(result, (str, list, dict, BaseModel)):
                    import json
                    return json.dumps(result, ensure_ascii=False)
                elif isinstance(result, (list, tuple)):
                    import json
                    return json.dumps(result, ensure_ascii=False)
                return str(result)
            
            except Exception as e:
                logger.error(f'{self.__class__.__name__}: Agent {agent_instance.name} 运行时出错: {e}')
                raise   
                return f"Error in agent {agent_instance.name}: {e}"
            
        _tool_func.__name__ = agent_instance.name.replace(" ", "_").lower()
        _tool_func.__doc__ = agent_instance.description

        return tool(_tool_func)
