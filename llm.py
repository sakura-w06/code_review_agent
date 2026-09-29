import time
import logging
from openai import (
    OpenAI, RateLimitError, APITimeoutError,
    AuthenticationError, BadRequestError
)
from config import Config
from exceptions import LLMCallError

logger = logging.getLogger(__name__)

client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
RETRYABLE = (RateLimitError, APITimeoutError)


def call_llm(messages, tools=None, max_retries=3, backoff=2):
    """
    通用 LLM 调用。
    - 支持任意 OpenAI 兼容 API
    - 分类重试
    - 若模型不支持 Function Calling，自动降级去掉 tools 重试
    """
    current_tools = tools  # 本地变量，降级时置空，不影响调用方

    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": Config.MODEL_NAME,
                "messages": messages,
                "temperature": Config.TEMPERATURE,
                "max_tokens": Config.MAX_TOKENS,
                "timeout": Config.TIMEOUT,
            }
            if current_tools:
                kwargs["tools"] = current_tools

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message

        except BadRequestError as e:
            err_msg = str(e).lower()
            # 模型不支持 tools → 降级重试
            if current_tools and ("tools" in err_msg or "function" in err_msg):
                logger.warning(
                    f"模型 {Config.MODEL_NAME} 不支持 Function Calling，"
                    f"降级为纯 Prompt 模式"
                )
                current_tools = None
                continue
            raise LLMCallError(f"请求参数错误: {e}")

        except RETRYABLE as e:
            if attempt == max_retries - 1:
                raise LLMCallError(f"重试{max_retries}次后失败: {e}")
            wait = backoff ** attempt
            logger.warning(f"第{attempt+1}次失败，{wait}秒后重试: {e}")
            time.sleep(wait)

        except AuthenticationError:
            raise LLMCallError("API Key 无效，请检查 .env 中的 LLM_API_KEY")