from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
from typing import List
from starlette.responses import JSONResponse
import os
app = FastAPI()

API_KEY = os.getenv("API_KEY")  

class RequestBody(BaseModel):
    documents: str
    questions: List[str]

class ResponseBody(BaseModel):
    answers: List[str]

@app.post("/hackrx/run", response_model=ResponseBody)
async def run_webhook(
    request: Request,
    body: RequestBody,
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    
    token = authorization.split(" ")[1]
    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    dummy_answers = ["This is a dummy answer." for _ in body.questions]
    return {"answers": dummy_answers}