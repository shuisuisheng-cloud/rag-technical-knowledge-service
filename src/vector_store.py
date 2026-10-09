import chromadb
from document_loader import load_markdown
from text_chunker import split_document
from embedding_service import embed_text,embed_texts

def create_chromadb(collection_name:str):
    client=chromadb.PersistentClient(path="data/chroma")
    collection=client.get_or_create_collection(name=collection_name)
    return collection
def build_chunk_id(chunk: dict) -> str:
    chunk_id=f"{chunk["metadata"]["source"]}::chunk_{chunk["metadata"]["chunk_index"]}"
    return chunk_id
def prepare_metadata_for_chroma(metadata: dict) -> dict:
    metadata_copy=metadata.copy()
    last_time=metadata_copy["last_updated"]
    if not isinstance(last_time,str):
        metadata_copy["last_updated"]=str(last_time)
    return metadata_copy
def prepare_chunk_records(chunks: list[dict]):
    ids=[]
    documents=[]
    metadatas=[]
    for chunk in chunks:
        chunk_id=build_chunk_id(chunk)
        documents.append(chunk["content"])
        metadatas.append(prepare_metadata_for_chroma(chunk["metadata"]))
        ids.append(chunk_id)
    return ids,documents,metadatas

def filter_pending_records(ids: list[str],documents: list[str],metadatas: list[dict],existing_ids: set[str]):
    if not len(ids)==len(documents)==len(metadatas):
        raise ValueError("Record fields length mismatch")
    pending_ids=[]
    pending_documents=[]
    pending_metadatas=[]
    for index,chunk_id in enumerate(ids):
        if chunk_id not in existing_ids:
            pending_ids.append(chunk_id)
            pending_documents.append(documents[index])
            pending_metadatas.append(metadatas[index])
    return pending_ids,pending_documents,pending_metadatas
def add_real_chunk():
    document=load_markdown("docs_raw/linux_gateway_day60_full_system_integration.md")
    chunks=split_document(document,500,100)
    # for chunk in chunks:
    #     chunk_id=build_chunk_id(chunk)
    first_chunk = chunks[0]
    first_chunk_id=build_chunk_id(first_chunk)
    raw_metadata = first_chunk["metadata"]
    chroma_metadata = prepare_metadata_for_chroma(raw_metadata)
    embedding=embed_text(first_chunk["content"])
    print("before value:", raw_metadata["last_updated"])
    print("before type:", type(raw_metadata["last_updated"]))
    print("after value:", chroma_metadata["last_updated"])
    print("after type:", type(chroma_metadata["last_updated"]))
    print(chunks[0])
    print("embedding type:", type(embedding))
    print("embedding length:", len(embedding))
    print("embedding first 5:", embedding[:5])
    collection=create_chromadb("day13_real_test")
    collection.add(ids=[first_chunk_id],documents=[first_chunk["content"]],embeddings=[embedding],
                   metadatas=[chroma_metadata])
    record=collection.get(ids=[first_chunk_id],include=["documents","metadatas","embeddings"])
    print("id:", record["ids"][0])

    print(
    "document preview:",
    record["documents"][0][:100]
)

    print(
    "source:",
    record["metadatas"][0]["source"]
)

    print(
    "chunk_index:",
    record["metadatas"][0]["chunk_index"]
)

    print(
    "embedding count:",
    len(record["embeddings"])
)

    print(
    "embedding length:",
    len(record["embeddings"][0])
)
    return record

def prepare_document_records(path:str):
    document=load_markdown(path)
    chunks=split_document(document,500,100)
    ids,documents,metadatas=prepare_chunk_records(chunks)
    embeddings=embed_texts(documents)
    return ids,documents,metadatas,embeddings

def add_real_chunks():
    ids,documents,metadatas,embeddings=prepare_document_records("docs_raw/linux_gateway_day60_full_system_integration.md")
    collection=create_chromadb("day13_batch_test")
    collection.add(ids=ids,documents=documents,metadatas=metadatas,embeddings=embeddings)
    num=collection.count()
    print(num)
    record = collection.get(
    ids=[ids[0]],
    include=["documents", "metadatas", "embeddings"])
    print("stored count:", num)
    print("id:", record["ids"][0])
    print("document preview:", record["documents"][0][:100])
    print("source:", record["metadatas"][0]["source"])
    print("chunk_index:", record["metadatas"][0]["chunk_index"])
    print("embedding length:", len(record["embeddings"][0]))
    return
if __name__ == "__main__":
    add_real_chunks()

# test_chunk = {
#     "content": "STM32 UART recovery",
#     "metadata": {
#         "source": "docs_raw/test.md",
#         "chunk_index": 0,
#     }
# }
# chunk_id=build_chunk_id(test_chunk)
# print(chunk_id)
# def test_add_record():
#     client=chromadb.PersistentClient(path="data/chroma")
#     collection=client.get_or_create_collection(name="day13__test")
#     collection.add(ids=["test_001"],documents=["STM32 uses UART for communication."],embeddings=[[0.1, 0.2, 0.3]],
#                    metadatas=[{"source": "day13_test","chunk_index": 0}])
#     record=collection.get(ids=["test_001"],include=["documents","metadatas","embeddings"])
#     print(record)
#     return collection



# if __name__ == "__main__":
#     collection = create_chromadb()
#     test_collection=test_add_record()
#     print("collection:", collection.name,"test_collection:",test_collection.name)
