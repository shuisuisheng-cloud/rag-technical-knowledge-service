from document_loader import load_markdown_directory
from text_chunker import split_documents


def main():
    chunk_size = 500
    chunk_overlap = 100
    directory_path = "docs_raw"
    chunk_count_by_source = {}

    documents = load_markdown_directory(directory_path)
    chunks=split_documents(documents,chunk_size,chunk_overlap)
    print("chunk总数:",len(chunks))
    print("文档总数：", len(documents))

    for chunk in chunks:
        source=chunk["metadata"]["source"]
        current_count = chunk_count_by_source.get(source, 0)+1
        chunk_count_by_source[source]=current_count
    for source, count in sorted(chunk_count_by_source.items()):
        print(f"{source} -> {count} chunks")
    assert sum(chunk_count_by_source.values()) == len(chunks)
    assert len(documents) > 0
    assert len(chunks) > 0

    assert all("source" in chunk["metadata"]for chunk in chunks)

    assert all("chunk_index" in chunk["metadata"]for chunk in chunks)

    if documents:
        first_document = documents[0]

        print("第一篇标题：", first_document["metadata"].get("title"))
        print("第一篇状态：", first_document["metadata"].get("status"))
        print("第一篇来源：", first_document["metadata"].get("source"))
        print("第一篇类型：", first_document["metadata"].get("file_type"))
        print("第一篇正文预览：")
        print(first_document["content"][:200])

if __name__ == "__main__":
    main()
