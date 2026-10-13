from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field,field_validator
from rag_service import answer_question
import ollama
import httpx
app=FastAPI()
class QueryRequestion(BaseModel):
    question:str
    top_k:int=Field(default=3,ge=1,le=5,strict=True)
    @field_validator("question")
    @classmethod
    def check_question(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("question 不能为空")
        return cleaned
class SourceItem(BaseModel):
    id:str
    source:str
class QueryResponse(BaseModel):
    question:str
    answer:str
    sources:list[SourceItem]
@app.post("/query",response_model=QueryResponse)
def query(request:QueryRequestion):
    try:
        ruslt=answer_question(request.question,request.top_k)
    except RuntimeError as e:
        if isinstance(
            e.__cause__,
            (ollama.ResponseError, ConnectionError, httpx.TimeoutException)
        ):
            raise HTTPException(
                status_code=503,
                detail="Ollama 服务暂时不可用"
            ) from e
        raise
    return ruslt
