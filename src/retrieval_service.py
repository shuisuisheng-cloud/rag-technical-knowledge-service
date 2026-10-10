import chromadb
from embedding_service import embed_text
def retrieve(question: str, top_k: int = 3) -> list[dict]:
    retrieved_records = []
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be int")
    if top_k<=0:
        raise ValueError(f"top_k can not below zero")
    if not isinstance(question,str):
        raise TypeError(f"question type should be str")
    question_test=question.strip()
    if question_test=="":
        raise ValueError(f"question can not be empty")
    client = chromadb.PersistentClient(path="data/chroma")
    collection = client.get_collection(name="technical_knowledge")
    question_embedding=embed_text(question_test)
    results=collection.query(query_embeddings=[question_embedding],n_results=top_k,include=["documents","metadatas","distances"])
    for record_id, document, metadata, distance in zip(results["ids"][0],results["documents"][0],results["metadatas"][0],results["distances"][0]):
        record={}
        record["id"] = record_id
        record["text"] = document
        record["source"] = metadata["source"]
        record["metadata"] = metadata
        record["distance"] = distance
        retrieved_records.append(record)
    return retrieved_records


if __name__ == "__main__":
    questions = [
    "STM32 如何向网关返回 ACK?",
    "MQTT 的 LWT 有什么作用？",
    "为什么 ChromaDB 的 last_updated 要转换成字符串？"
]

    for question in questions:
        print(f"\nQuestion: {question}")

        records = retrieve(question, top_k=3)

        for index, record in enumerate(records, start=1):
            print(f"\nResult {index}")
            print("Source:", record["source"])
            print("Distance:", record["distance"])
            print("Text:", record["text"][:120])
