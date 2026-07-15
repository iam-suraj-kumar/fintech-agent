from langchain_openai import OpenAIEmbeddings

from core.llm import portkey_kwargs

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_embeddings(model: str = DEFAULT_EMBEDDING_MODEL, **kwargs) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(**portkey_kwargs(model, "EMBEDDING_MODEL"), **kwargs)
