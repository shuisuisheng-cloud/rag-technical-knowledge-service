from embedding_service import embed_text
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
