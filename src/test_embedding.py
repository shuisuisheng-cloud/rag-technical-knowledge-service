from embedding_service import embed_text,embed_texts
text = "STM32 使用 USART2 接收 Linux 网关下发的控制命令"
embedding=embed_text(text)
assert type(embedding)==list
assert len(embedding)==1024
assert all(isinstance(value, float)for value in embedding)
assert embedding
print("向量类型：", type(embedding))
print("向量长度：", len(embedding))
print("前五个元素：", embedding[:5])
try:
    embed_text("   ")
except ValueError as error:
    print("成功捕获空文本：", error)
else:
    raise AssertionError("空文本应该抛出 ValueError")
try:
    embed_text(123)
except TypeError as e:
    print(f"成功捕获错误类型{e}")
else:
    raise AssertionError("错误类型应该抛出 TypeError")
texts = [
    "STM32 UART recovery",
    "Gateway ACK timeout",
    "RAG batch embedding",
]
embeddings=embed_texts(texts)
assert type(embeddings)==list
assert len(embeddings)==3
assert all(isinstance(embedding,list)for embedding in embeddings)
assert all(len(lenth)==1024 for lenth in embeddings)
assert all(
    all(isinstance(value, float) for value in embedding)
    for embedding in embeddings
)
try:
    embed_texts([])
except ValueError as error:
    print("捕获空列表",error)
else:
    raise AssertionError("空列表应该抛出")
try:
    embed_texts(["hello",123])
except TypeError as error:
    print("捕获类型异常",error)
else:
    raise AssertionError("异常类型应该抛出")
try:
    embed_texts(["hello",""])
except ValueError as error:
    print("捕获列表内存在空内容",error)
else:
    raise AssertionError("异常空内容应该抛出")
