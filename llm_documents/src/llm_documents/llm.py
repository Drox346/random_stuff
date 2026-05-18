from ollama import Client


DEFAULT_MODEL = "qwen2.5:0.5b"
LOCAL_OLLAMA_URL = "http://127.0.0.1:11434"


def chat_with_ollama(*, messages: list[dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    """Call the local Ollama chat API and return plain response content."""
    response = Client(host=LOCAL_OLLAMA_URL).chat(
        model=model,
        messages=messages,
        options={"temperature": 0},
    )
    return response.message.content or ""
