import pytest

from core import embeddings, llm


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("LLM_PROVIDER", "LLM_MODEL", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


def test_gemini_is_the_default():
    model = llm.get_llm(temperature=0)
    assert type(model).__name__ == "ChatGoogleGenerativeAI"
    assert model.model.endswith("gemini-3.5-flash")
    assert type(embeddings.get_embeddings()).__name__ == "GoogleGenerativeAIEmbeddings"


def test_openai_provider_and_model_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    model = llm.get_llm(temperature=0)
    assert type(model).__name__ == "ChatOpenAI"
    assert model.model_name == "gpt-4o"
    # embeddings follow LLM_PROVIDER unless EMBEDDING_PROVIDER is set
    assert type(embeddings.get_embeddings()).__name__ == "OpenAIEmbeddings"


def test_embedding_provider_can_differ(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "gemini")
    assert type(embeddings.get_embeddings()).__name__ == "GoogleGenerativeAIEmbeddings"


def test_settings_are_read_at_call_time(monkeypatch):
    assert llm.llm_provider() == "gemini"
    monkeypatch.setenv("LLM_PROVIDER", "openai")  # e.g. set by a later load_dotenv()
    assert llm.llm_provider() == "openai" and llm.llm_model() == "gpt-4o-mini"


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError, match="gemini"):
        llm.get_llm()
