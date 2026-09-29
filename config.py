import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("LLM_API_KEY")
    BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    MODEL_NAME = os.getenv("LLM_MODEL", "qwen3-max")
    
    TEMPERATURE = 0.2
    MAX_TOKENS = 4096
    TIMEOUT = 60
    
    MAX_ITERATIONS = 5
    MAX_RECENT_MESSAGES = 6
    MAX_CODE_LENGTH = 50000

    @classmethod
    def validate(cls):
        if not cls.API_KEY:
            raise EnvironmentError(
                "未找到 LLM_API_KEY。请复制 .env.example 为 .env 并填入。"
            )

Config.validate()