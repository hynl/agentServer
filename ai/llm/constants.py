from django.conf import settings
from agentrtw.settings import NEWS_NEWS_API_KEY
from agentrtw.settings import OPENAI_API_KEY as settings_OPENAI_API_KEY
from agentrtw.settings import DEEPSEEK_API_KEY as settings_DEEPSEEK_API_KEY
from agentrtw.settings import GEMINI_API_KEY as settings_GEMINI_API_KEY
from agentrtw.settings import ANTHROPIC_API_KEY as settings_ANTHROPIC_API_KEY
import os

# Constants for LLM providers and configurations
OPENAI = 'openai'
LLAMA = 'llama'
GEMINI = 'gemini'
ANTHROPIC = 'anthropic'
DEEPSEEK = 'deepseek'

KEY_CHAT_MODEL_NAME = 'chat_model'
KEY_EMBEDDING_MODEL_NAME = 'embedding_model'
KEY_API_KEY = 'api_key'
KEY_TEMPERATURE = 'temperature'

# API keys for different LLM providers
OPENAI_API_KEY = settings_OPENAI_API_KEY
DEEPSEEK_API_KEY = settings_DEEPSEEK_API_KEY
GEMINI_API_KEY = settings_GEMINI_API_KEY
ANTHROPIC_API_KEY = settings_ANTHROPIC_API_KEY

DEFAULT_CHAT_MODEL_PROVIDER = "DEFAULT_CHAT_MODEL_PROVIDER"
DEFAULT_EMBEDDING_MODEL_PROVIDER = "DEFAULT_EMBEDDING_MODEL_PROVIDER"

LLM_CONFIGS = {
    "DEFAULT_CHAT_MODEL_PROVIDER": OPENAI,
    "DEFAULT_EMBEDDING_MODEL_PROVIDER": OPENAI,

    OPENAI: {
        KEY_CHAT_MODEL_NAME: 'gpt-3.5-turbo',
        KEY_EMBEDDING_MODEL_NAME: 'gpt-4',
        KEY_API_KEY: OPENAI_API_KEY,
        KEY_TEMPERATURE: '0.1',
    },

    DEEPSEEK: {
        KEY_CHAT_MODEL_NAME: 'deepseek-chat-1',
        KEY_EMBEDDING_MODEL_NAME: 'deepseek-embedding-1',
        KEY_API_KEY: DEEPSEEK_API_KEY,
        KEY_TEMPERATURE: '0.1',
    },

    GEMINI: {
        KEY_CHAT_MODEL_NAME: 'gemini-1.5-flash',
        KEY_EMBEDDING_MODEL_NAME: 'gemini-1.5-flash-embedding',
        KEY_API_KEY: GEMINI_API_KEY,
        KEY_TEMPERATURE: '0.1',
    },

    ANTHROPIC: {
        KEY_CHAT_MODEL_NAME: 'claude-2',
        KEY_EMBEDDING_MODEL_NAME: 'claude-embed-20240229',
        KEY_API_KEY: ANTHROPIC_API_KEY,
        KEY_TEMPERATURE: '0.1',
    }
}

# LLM provider configuration
LLM_PROVIDER = OPENAI


LLM_CACHE_ENABLED = True
