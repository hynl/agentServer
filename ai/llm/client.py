
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    try:
        from langchain_community.chat_models import ChatAnthropic
    except ImportError:
        # 如果都没有，创建一个临时的占位符
        ChatAnthropic = None
from langchain.llms import BaseLLM
from langchain_core.embeddings import Embeddings
from ai.llm.constants import *


class LLMClient:
    _llm_chat: Dict[str, BaseChatModel] = {}
    _llm_embedding: Dict[str, Embeddings] = {}

    @classmethod
    def get_chat_model(cls, provider: Optional[str] = None, model_name: Optional[str] = None, temperature: Optional[float] = None) -> BaseChatModel:
        provider = provider or DEFAULT_CHAT_MODEL_PROVIDER
        provider = provider.upper()
        actual_model_name = model_name or LLM_CONFIGS[provider].get(KEY_CHAT_MODEL_NAME)
        actual_temperature = temperature or float(LLM_CONFIGS[provider].get(KEY_TEMPERATURE, 0.1))

        instance_key = f'{provider}_{actual_model_name}_{actual_temperature}'
        if instance_key in cls._llm_chat:
            return cls._llm_chat[instance_key]
        
        try:
            api_key = LLM_CONFIGS[provider].get(KEY_API_KEY)
            if not api_key:
                raise ValueError(f"API key for provider {provider} is not set.")
            if provider == OPENAI:
                llm = ChatOpenAI(
                    model=actual_model_name,
                    temperature=actual_temperature,
                    openai_api_key=api_key,
                    max_retries=1,  # 设置最大重试次数
                )
            elif provider == GEMINI:
                llm = ChatGoogleGenerativeAI(
                    model=actual_model_name,
                    temperature=actual_temperature,
                    google_api_key=api_key,
                    max_retries=1,  # 设置最大重试次数  
                )

            elif provider == ANTHROPIC:
                llm = ChatAnthropic(
                    model=actual_model_name,
                    temperature=actual_temperature,
                    anthropic_api_key=api_key,
                )
            else :
                raise ValueError(f"Unsupported provider: {provider}")
            
            cls._llm_chat[instance_key] = llm
            return llm
        except Exception as e:
            raise ValueError(f"所有 LLM 提供商都不可用: {provider}") from e

    @classmethod
    def get_embedding_model(cls, provider: Optional[str] = None, model_name: Optional[str] = None) -> Embeddings:
        if provider is None:
            provider = DEFAULT_EMBEDDING_MODEL_PROVIDER
        provider = provider.upper()
        actual_model_name = model_name or LLM_CONFIGS[provider].get(KEY_EMBEDDING_MODEL_NAME)
        
        if not actual_model_name:
            raise ValueError(f"Embedding model name for provider {provider} is not set.")

        instance_key = f'EMBEDDING-{provider}_{actual_model_name}'
        if instance_key in cls._llm_embedding:
            return cls._llm_embedding[instance_key]
        
        api_key = LLM_CONFIGS[provider].get(KEY_API_KEY)

        if not api_key:
            raise ValueError(f"API key for provider {provider} is not set.")
        if provider == OPENAI:
            embedding = OpenAIEmbeddings(
                model=actual_model_name,
                openai_api_key=api_key,
                max_retries=1,  # 设置最大重试次数
            )
        elif provider == GEMINI:
            embedding = GoogleGenerativeAIEmbeddings(
                model=actual_model_name,
                google_api_key=api_key,
                max_retries=1,  # 设置最大重试次数
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        cls._llm_embedding[instance_key] = embedding
        return embedding

    