from document_loader import load_markdown_directory
from vector_store import prepare_chunk_records, create_chromadb,filter_pending_records
from text_chunker import split_documents
from embedding_service import embed_texts

docs_a=load_markdown_directory("docs_raw")
docs_b=load_markdown_directory("notes")
docs_all=docs_a+docs_b
chunks=split_documents(docs_all,500,100)
ids,documents,metadatas=prepare_chunk_records(chunks)
collection = create_chromadb("technical_knowledge")
existing_records = collection.get(ids=ids, include=[])
existing_ids = set(existing_records["ids"])
pending_ids, pending_documents, pending_metadatas = (filter_pending_records(ids,documents,metadatas,existing_ids))
print("Pending records:", len(pending_ids))
batch_size=16
for start in range(0,len(pending_ids),batch_size):
    batch_ids=pending_ids[start:start+batch_size]
    batch_documents=pending_documents[start:start+batch_size]
    batch_metadatas=pending_metadatas[start:start+batch_size]
    batch_embeddings = embed_texts(batch_documents)
    assert len(batch_ids) == len(batch_documents) == len(batch_metadatas) == len(batch_embeddings)
    assert all(len(vector) == 1024 for vector in batch_embeddings)
    collection.add(ids=batch_ids,documents=batch_documents,metadatas=batch_metadatas,embeddings=batch_embeddings)
    print("Saved:", len(batch_ids), "Total:", collection.count())
