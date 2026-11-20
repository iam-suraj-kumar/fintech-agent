import os

from langchain_core.language_models.chat_models import BaseChatModel

# "gemini" (default) or "openai"; each provider has its own default model.
_DEFAULT_MODEL = {"gemini": "gemini-3.5-flash", "openai": "gpt-4o-mini"}


def llm_provider() -> str:
    # Read at call time, not import time, so a later load_dotenv() still takes effect.
    return (os.environ.get("LLM_PROVIDER") or "gemini").lower()


def llm_model() -> str:
    return os.environ.get("LLM_MODEL") or _DEFAULT_MODEL.get(llm_provider(), "")


# Gemini's free tier allows only a few requests per minute and the three specialists
# run in parallel, so rate-limit (429) errors are retried with backoff instead of failing.
_MAX_RETRIES = 6
_TIMEOUT_SECONDS = 60


def get_llm(**kwargs) -> BaseChatModel:
    """Chat model for the configured provider (LLM_PROVIDER), model from LLM_MODEL or the provider default.

    Returns a LangChain chat model, so tool calling (create_react_agent) and
    with_structured_output() work the same with either provider.
    """
    provider = llm_provider()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=llm_model(),
            google_api_key=os.environ["GEMINI_API_KEY"],
            # Thinking tokens add latency and cost; these agents make short tool calls.
            thinking_budget=0,
            max_retries=_MAX_RETRIES,
            timeout=_TIMEOUT_SECONDS,
            **kwargs,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=llm_model(),
            api_key=os.environ["OPENAI_API_KEY"],
            max_retries=_MAX_RETRIES,
            timeout=_TIMEOUT_SECONDS,
            **kwargs,
        )
    raise ValueError(f"Unknown LLM_PROVIDER {provider!r}: use 'gemini' or 'openai'")
