def split_document(document: dict,chunk_size: int,chunk_overlap: int,) -> list[dict]:
    if chunk_size <=0:
        raise ValueError(f"chunk_size必须大于零,chunk_size={chunk_size}")
    if chunk_overlap <0:
        raise ValueError(f"chunk_overlap不得小于零,chunk_overlap={chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap必须小于chunk_size,chunk_overlap={chunk_overlap} chunk_size={chunk_size}")
    content = document["content"]
    metadata = document["metadata"]
    if content == "":
        return []
    step=chunk_size-chunk_overlap
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk_text = content[start:end]
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = chunk_index
        chunk = {"content": chunk_text,"metadata": chunk_metadata,}
        chunks.append(chunk)
        if end == len(content):
            break
        else:
            start += step
            chunk_index += 1
    return chunks
def split_documents(documents: list[dict],chunk_size: int,chunk_overlap: int,) -> list[dict]:
    all_chunks=[]
    for document in documents:
        document_chunks=split_document(document,chunk_size,chunk_overlap)
        all_chunks.extend(document_chunks)
    return all_chunks
