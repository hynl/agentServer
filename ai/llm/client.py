
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.chat_models import ChatOpenAI, ChatAnthropic
from langchain.llms import BaseLLM
from langchain_core.embeddings import Embeddings
# from google.generativeai import ChatGoogleGenerativeAI
from ai.llm.constants import *


class LLMClient:
    _llm_chat: Dict[str, BaseChatModel] = {}
    _llm_embedding: Dict[str, Embeddings] = {}

    @classmethod
    def get_chat_model(cls, provider: Optional[str] = None, model_name: Optional[str] = None, temperature: Optional[float] = None) -> BaseChatModel:
        provider = (provider or LLM_CONFIGS.get(DEFAULT_CHAT_MODEL_PROVIDER)).upper()
        actual_model_name = model_name or LLM_CONFIGS[provider].get(KEY_CHAT_MODEL_NAME)
        actual_temperature = temperature or float(LLM_CONFIGS[provider].get(KEY_TEMPERATURE, 0.1))

        instance_key = f'{provider}_{actual_model_name}_{actual_temperature}'
        if instance_key not in cls._llm_chat:
            return cls._llm_chat[instance_key]
        
        api_key = LLM_CONFIGS[provider].get(KEY_API_KEY)
        if not api_key:
            raise ValueError(f"API key for provider {provider} is not set.")
        if provider == OPENAI:
            llm = ChatOpenAI(
                model_name=actual_model_name,
                temperature=actual_temperature,
                openai_api_key=api_key,
            )
        elif provider == GEMINI:
            llm = ChatGoogleGenerativeAI(
                model_name=actual_model_name,
                temperature=actual_temperature,
                api_key=api_key,
            )

        elif provider == ANTHROPIC:
            llm = ChatAnthropic(
                model_name=actual_model_name,
                temperature=actual_temperature,
                anthropic_api_key=api_key,
            )
        else :
            raise ValueError(f"Unsupported provider: {provider}")
        
        cls._llm_chat[instance_key] = llm
        return llm
    
    @classmethod
    def get_embedding_model(cls, provider: Optional[str], model_name: Optional[str] = None) -> Embeddings:
        provider = (provider or LLM_CONFIGS.get(DEFAULT_EMBEDDING_MODEL_PROVIDER)).upper()
        actual_model_name = model_name or LLM_CONFIGS[provider].get(KEY_EMBEDDING_MODEL_NAME)

        instance_key = f'EMBEDDING-{provider}_{actual_model_name}'
        if instance_key not in cls._llm_embedding:
            return cls._llm_embedding[instance_key]
        
        api_key = LLM_CONFIGS[provider].get(KEY_API_KEY)

        if not api_key:
            raise ValueError(f"API key for provider {provider} is not set.")
        if provider == OPENAI:
            embedding = OpenAIEmbeddings(
                model=actual_model_name,
                openai_api_key=api_key,
            )
        elif provider == GEMINI:
            embedding = GoogleGenerativeAIEmbeddings(
                model=actual_model_name,
                api_key=api_key,
            )
        elif provider == ANTHROPIC:
            embedding = ChatAnthropic(
                model=actual_model_name,
                anthropic_api_key=api_key,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        cls._llm_embedding[instance_key] = embedding
        return embedding

    