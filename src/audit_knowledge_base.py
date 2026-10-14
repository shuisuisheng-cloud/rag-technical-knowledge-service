import chromadb
from pydantic import BaseModel, Field, ValidationError, ConfigDict
class MetadataItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    source: str = Field(min_length=1, strict=True)
    chunk_index: int = Field(ge=0, strict=True)
def audit_collection(collection, batch_size: int = 100) -> dict:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise TypeError("batch_size must be int")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    total=collection.count()
    checked=0
    seen_id=set()
    invalid_records=[]
    duplicate_ids=[]
    embedding_dimension_errors=[]
    report={}
    for offset in range(0,total,batch_size):
        records=collection.get(limit=batch_size,offset=offset,include=["documents","metadatas","embeddings"])
        ids = records["ids"]
        documents = records["documents"]
        metadatas = records["metadatas"]
        embeddings = records["embeddings"]
        if ids is None or documents is None or metadatas is None or embeddings is None or not(len(ids)==len(documents)==len(metadatas)==len(embeddings)):
            raise ValueError(f"Record fields not aligned at offset={offset}")
        for index,record_id in enumerate(records["ids"]):
            checked+=1
            if not isinstance(record_id,str) or not record_id.strip():
                invalid_records.append({"id": record_id,"reason": "invalid_id"})
                continue
            if record_id not in seen_id:
                seen_id.add(record_id)
            else:
                duplicate_ids.append({"ids":record_id,"reason":"duplicate_id"})
                continue
            document=records["documents"][index]
            metadata=records["metadatas"][index]
            vector=records["embeddings"][index]
            if not isinstance(document, str) or not document.strip():
                invalid_records.append({"id":record_id,"reason":"doucument is empty"})
            try:
                valid_metadata = MetadataItem.model_validate(metadata)
            except ValidationError as e:
                invalid_records.append({"id": record_id,"reason": "invalid_metadata","detail": str(e)})
            else:
                expected_id=f"{valid_metadata.source}::"f"chunk_{valid_metadata.chunk_index}"
                if expected_id !=record_id:
                    invalid_records.append({"id": record_id,"reason": "id_metadata_mismatch"})
            if vector is None or len(vector) != 1024:
                embedding_dimension_errors.append({"id":record_id,"reason":"embedding error"})
    report["total"]=total
    report["checked"]=checked
    report["invalid_records"]=invalid_records
    report["duplicate_ids"]=duplicate_ids
    report["embedding_dimension_errors"]=embedding_dimension_errors
    return report
if __name__ == "__main__":
    client = chromadb.PersistentClient(path="data/chroma")
    collection = client.get_collection(
        name="technical_knowledge"
    )

    report = audit_collection(collection)
    print(report)
