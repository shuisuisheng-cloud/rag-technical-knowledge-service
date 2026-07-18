from text_chunker import split_document,split_documents
from document_loader import load_markdown
document = {
    "content": "abcdefghij",
    "metadata": {
        "title": "短文本",
        "source": "short.md",
    },
}
chunks = split_document(document, 20, 5)

assert len(chunks) == 1
assert chunks[0]["content"] == "abcdefghij"
assert chunks[0]["metadata"]["chunk_index"] == 0
document = {
    "content": "abcdefghijklmnopqrst",
    "metadata": {
        "title": "重叠测试",
        "source": "overlap.md",
    },
}
chunks=split_document(document,8,2)
i=0
for chunk in chunks:
    print(
        chunk["metadata"]["chunk_index"],
        chunk["content"],
    )
    assert chunks[i]["metadata"]["chunk_index"]==i
    i+=1
assert [chunk["content"] for chunk in chunks] == [
    "abcdefgh",
    "ghijklmn",
    "mnopqrst",
]
assert chunks[0]["metadata"] is not chunks[1]["metadata"]
assert chunks[0]["metadata"] is not document["metadata"]
assert "chunk_index" not in document["metadata"]
empty_document = {
    "content": "",
    "metadata": {
        "title": "空文本",
        "source": "empty.md",
    },
}

empty_chunks = split_document(
    empty_document,
    chunk_size=10,
    chunk_overlap=2,
)

assert empty_chunks == []
try:
    split_document(document, 0, 0)
except ValueError as error:
    print("成功捕获：", error)
else:
    raise AssertionError("chunk_size=0 应该抛出 ValueError")
try:
    split_document(document,1,-1)
except ValueError as error:
    print("成功捕获",error)
else:
    raise AssertionError("chunk_overlap=-1 应该抛出 ValueError")
try:
    split_document(document,8,8)
except ValueError as error:
    print("成功捕获",error)
else:
    raise AssertionError("chunk_overlap=chunk_size 应该抛出 ValueError")
print("所有文本切分测试通过")
real_document = load_markdown(
    "docs_raw/leetcode_day05_two_sum.md"
)

real_chunks = split_document(
    real_document,
    chunk_size=500,
    chunk_overlap=100,
)
print("真实文档标题：", real_document["metadata"]["title"])
print("真实文档长度：", len(real_document["content"]))
print("真实 Chunk 数量：", len(real_chunks))
assert len(real_chunks) > 0

assert all(
    len(chunk["content"]) <= 500
    for chunk in real_chunks
)

assert all(
    chunk["metadata"]["source"]
    == real_document["metadata"]["source"]
    for chunk in real_chunks
)

assert [
    chunk["metadata"]["chunk_index"]
    for chunk in real_chunks
] == list(range(len(real_chunks)))

documents = [
    {
        "content": "abcdefghij",
        "metadata": {
            "title": "文档 A",
            "source": "a.md",
        },
    },
    {
        "content": "12345",
        "metadata": {
            "title": "文档 B",
            "source": "b.md",
        },
    },
]
batch_chunks = split_documents(
    documents,
    chunk_size=6,
    chunk_overlap=2,
)
assert len(batch_chunks) == 3
assert isinstance(batch_chunks[0], dict)
assert [
    chunk["content"]
    for chunk in batch_chunks
] == [
    "abcdef",
    "efghij",
    "12345",
]
assert [
    chunk["metadata"]["source"]
    for chunk in batch_chunks
] == [
    "a.md",
    "a.md",
    "b.md",
]
assert [
    chunk["metadata"]["chunk_index"]
    for chunk in batch_chunks
] == [
    0,
    1,
    0,
]
assert "chunk_index" not in documents[0]["metadata"]
assert "chunk_index" not in documents[1]["metadata"]
empty_batch_chunks = split_documents(
    [],
    chunk_size=6,
    chunk_overlap=2,
)

assert empty_batch_chunks == []
print("所有批量文本切分测试通过")
