import os

from langchain_core.embeddings import Embeddings

# Defaults to the same provider as the LLM. Only the fraud-case search
# (tools/mock_apis.py) embeds text, into an in-memory Chroma store rebuilt each
# run, so switching provider needs no re-indexing.
_DEFAULT_MODEL = {"gemini": "models/gemini-embedding-001", "openai": "text-embedding-3-small"}


def embedding_provider() -> str:
    # Read at call time, not import time, so a later load_dotenv() still takes effect.
    return (os.environ.get("EMBEDDING_PROVIDER") or os.environ.get("LLM_PROVIDER") or "gemini").lower()


def embedding_model() -> str:
    return os.environ.get("EMBEDDING_MODEL") or _DEFAULT_MODEL.get(embedding_provider(), "")


def get_embeddings(**kwargs) -> Embeddings:
    """Embedding model for the configured provider (EMBEDDING_PROVIDER, else LLM_PROVIDER)."""
    provider = embedding_provider()
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=embedding_model(), google_api_key=os.environ["GEMINI_API_KEY"], **kwargs)
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=embedding_model(), api_key=os.environ["OPENAI_API_KEY"], **kwargs)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER {provider!r}: use 'gemini' or 'openai'")
