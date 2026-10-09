from document_loader import load_markdown_directory
from text_chunker import split_documents
from vector_store import prepare_chunk_records, create_chromadb,filter_pending_records

docs_a=load_markdown_directory("docs_raw")
docs_b=load_markdown_directory("notes")
docs_all=docs_a+docs_b
print(f"docs_a:{len(docs_a)}  docs_b:{len(docs_b)}  docs_all:{len(docs_all)}")

chunks=split_documents(docs_all,500,100)
print(f"chunks:{len(chunks)}  first:{chunks[0]["metadata"]["source"]}  last:{chunks[-1]["metadata"]["source"]}")

ids,documents,metadatas=prepare_chunk_records(chunks)
print(f"{len(ids)}   {len(documents)}      {len(metadatas)}")

batch_size=16
for start in range(0,len(ids),batch_size):
    batch_ids=ids[start:start+batch_size]
    batch_documents=documents[start:start+batch_size]
    batch_metadatas=metadatas[start:start+batch_size]
    print(f"start={start}, "f"ids={len(batch_ids)}, "f"documents={len(batch_documents)}, "f"metadatas={len(batch_metadatas)}")
collection = create_chromadb("technical_knowledge")

print("existing records:", collection.count())
existing_records = collection.get(ids=ids, include=[])
existing_ids = set(existing_records["ids"])
# test_existing_ids = {"B"}
# print(filter_pending_records(["A","B","C"],["正文A","正文B","正文C"],[{"source":"A"},{"source":"B"},{"source":"C"}],test_existing_ids))
pending_ids, pending_documents, pending_metadatas = (filter_pending_records(ids,documents,metadatas,existing_ids))
print(f"{len(pending_ids)}  {len(pending_documents)}  {len(pending_metadatas)}")
