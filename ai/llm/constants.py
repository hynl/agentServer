from django.conf import settings
from agentrtw.settings import NEWS_NEWS_API_KEY
from agentrtw.settings import OPENAI_API_KEY as settings_OPENAI_API_KEY
from agentrtw.settings import DEEPSEEK_API_KEY as settings_DEEPSEEK_API_KEY
from agentrtw.settings import GEMINI_API_KEY as settings_GEMINI_API_KEY
from agentrtw.settings import ANTHROPIC_API_KEY as settings_ANTHROPIC_API_KEY
import os

# Constants for LLM providers and configurations
OPENAI = 'OPENAI'
LLAMA = 'LLAMA'
GEMINI = 'GEMINI'
ANTHROPIC = 'ANTHROPIC'
DEEPSEEK = 'DEEPSEEK'

KEY_CHAT_MODEL_NAME = 'chat_model'
KEY_EMBEDDING_MODEL_NAME = 'embedding_model'
KEY_API_KEY = 'api_key'
KEY_TEMPERATURE = 'temperature'

# API keys for different LLM providers
OPENAI_API_KEY = settings_OPENAI_API_KEY
DEEPSEEK_API_KEY = settings_DEEPSEEK_API_KEY
GEMINI_API_KEY = settings_GEMINI_API_KEY
ANTHROPIC_API_KEY = settings_ANTHROPIC_API_KEY

# 直接指向提供商常量，而不是字符串
DEFAULT_CHAT_MODEL_PROVIDER = GEMINI
DEFAULT_EMBEDDING_MODEL_PROVIDER = GEMINI

LLM_CONFIGS = {
    OPENAI: {  # 使用大写常量
        KEY_CHAT_MODEL_NAME: 'gpt-3.5-turbo',
        KEY_EMBEDDING_MODEL_NAME: 'text-embedding-ada-002',
        KEY_API_KEY: OPENAI_API_KEY,
        KEY_TEMPERATURE: 0.1,
    },

    DEEPSEEK: {
        KEY_CHAT_MODEL_NAME: 'deepseek-chat',
        KEY_EMBEDDING_MODEL_NAME: 'deepseek-embedding',
        KEY_API_KEY: DEEPSEEK_API_KEY,
        KEY_TEMPERATURE: 0.1,
    },

    GEMINI: {
        KEY_CHAT_MODEL_NAME: 'gemini-2.0-flash',
        KEY_EMBEDDING_MODEL_NAME: 'models/text-embedding-004',
        KEY_API_KEY: GEMINI_API_KEY,
        KEY_TEMPERATURE: 0.1,
    },

    ANTHROPIC: {
        KEY_CHAT_MODEL_NAME: 'claude-3-sonnet-20240229',
        KEY_EMBEDDING_MODEL_NAME: None,
        KEY_API_KEY: ANTHROPIC_API_KEY,
        KEY_TEMPERATURE: 0.1,
    }
}

# LLM provider configuration
LLM_PROVIDER = OPENAI

LLM_CACHE_ENABLED = True