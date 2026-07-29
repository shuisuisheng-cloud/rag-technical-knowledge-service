import ollama
EMBEDDING_MODEL = "qwen3-embedding:0.6b"
def embed_text(text: str) -> list[float]:
    if not isinstance(text,str):
        raise TypeError(f"text must be str, actual={type(text).__name__}")
    text=text.strip()
    if text == "":
        raise ValueError(f"text can not be empty:{text}")
    response=ollama.embed(model=EMBEDDING_MODEL,input=text)
    embeddings=response.embeddings
    if not embeddings or not embeddings[0]:
        raise RuntimeError(f"embeddings error:{embeddings}")
    return embeddings[0]
