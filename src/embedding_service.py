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

def embed_texts(texts:list[str]) -> list[list[float]]:
    cleaned_texts=[]
    if not isinstance(texts,list):
        raise TypeError(f"输入类型错误{type(texts)}")
    if not texts:
        raise ValueError(f"输入文本列表块不得为空")
    for serial_text in texts:
        if not isinstance(serial_text,str):
            raise TypeError(f"文本列表块类型错误：{type(serial_text)}")
        cleaned_text=serial_text.strip()
        if cleaned_text=="":
            raise ValueError(f"文本列表块内内容不得为空")
        cleaned_texts.append(cleaned_text)
    response=ollama.embed(model=EMBEDDING_MODEL,input=cleaned_texts)
    embeddings=response.embeddings
    if not embeddings:
        raise RuntimeError("no embeddings returned")
    if len(embeddings) != len(cleaned_texts):
        raise RuntimeError("embedding count mismatch")
    for serial_embedding in embeddings:
        if not serial_embedding:
            raise RuntimeError(f"empty embedding returned")
    return embeddings
