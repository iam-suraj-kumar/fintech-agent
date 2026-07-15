import os

from langchain_openai import ChatOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders
from pydantic import SecretStr


def portkey_kwargs(model: str, override_env: str) -> dict:
    """Shared connection kwargs for routing an OpenAI-compatible client through Portkey.

    Provider credentials live in Portkey's Model Catalog (looked up via the
    @provider/model slug), so no OpenAI key is needed here. If `override_env`
    (e.g. LLM_MODEL) is set, it's used as-is as a fully-qualified @provider/model
    string; otherwise `model` is passed through unchanged.
    """
    return {
        "api_key": SecretStr("portkey"),
        "base_url": PORTKEY_GATEWAY_URL,
        "default_headers": createHeaders(api_key=os.environ["PORTKEY_API_KEY"]),
        "model": os.environ.get(override_env, model),
    }


def get_llm(model: str, **kwargs) -> ChatOpenAI:
    return ChatOpenAI(**portkey_kwargs(model, "LLM_MODEL"), **kwargs)
