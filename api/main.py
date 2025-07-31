from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
from typing import List, Union
from starlette.responses import JSONResponse
import os
import aiohttp
import tempfile
import asyncio
from urllib.parse import urlparse
import mimetypes

app = FastAPI()

API_KEY = os.getenv("API_KEY")

class RequestBody(BaseModel):
    documents: Union[str, List[str]]  # Can be single URL string or list of URLs
    questions: List[str]

class ResponseBody(BaseModel):
    answers: List[str]

class DocumentDownloader:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def download_document(self, url: str) -> dict:
        """Download a document from URL and return file info"""
        try:
            session = await self.get_session()
            
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {url}")
            
            # Download the document
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to download document from {url}. Status: {response.status}"
                    )
                
                content = await response.read()
                content_type = response.headers.get('content-type', '')
                
                # Determine file extension from URL or content type
                file_extension = self._get_file_extension(url, content_type)
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                return {
                    "url": url,
                    "file_path": temp_file_path,
                    "content_type": content_type,
                    "size": len(content),
                    "extension": file_extension
                }
                
        except aiohttp.ClientError as e:
            raise HTTPException(status_code=400, detail=f"Network error downloading {url}: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error downloading {url}: {str(e)}")
    
    def _get_file_extension(self, url: str, content_type: str) -> str:
        """Determine file extension from URL or content type"""
        # Try to get extension from URL
        parsed_url = urlparse(url)
        if parsed_url.path:
            _, ext = os.path.splitext(parsed_url.path)
            if ext:
                return ext.lower()
        
        # Try to get extension from content type
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(';')[0])
            if ext:
                return ext.lower()
        
        return '.bin'  # Default extension
    
    async def close(self):
        if self.session:
            await self.session.close()

# Global downloader instance
downloader = DocumentDownloader()

@app.on_event("shutdown")
async def shutdown_event():
    await downloader.close()

@app.get("/")
async def root():
    return {
        "message": "Document Processing Webhook API", 
        "endpoint": "/hackrx/run",
        "status": "running"
    }

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

    try:
        # Handle documents input - can be string or list
        if isinstance(body.documents, str):
            document_urls = [body.documents]
        else:
            document_urls = body.documents
        
        if not document_urls:
            raise HTTPException(status_code=400, detail="No documents provided")
        
        # Download all documents
        downloaded_docs = []
        for url in document_urls:
            try:
                doc_info = await downloader.download_document(url)
                downloaded_docs.append(doc_info)
                print(f"Downloaded: {doc_info['url']} -> {doc_info['file_path']} ({doc_info['size']} bytes)")
            except Exception as e:
                print(f"Failed to download {url}: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to download document: {url}")
        
        # Process documents (placeholder for now)
        processed_content = []
        for doc in downloaded_docs:
            # For now, just collect basic info about downloaded files
            processed_content.append(f"Downloaded {doc['extension']} file from {doc['url']} ({doc['size']} bytes)")
        
        # Generate answers based on questions and downloaded documents
        answers = []
        for i, question in enumerate(body.questions):
            # Placeholder logic - will be enhanced in Checkpoint 2
            if downloaded_docs:
                doc_info = downloaded_docs[0]  # Use first document for now
                answer = f"Based on downloaded {doc_info['extension']} document ({doc_info['size']} bytes): This is a placeholder answer for '{question}'"
            else:
                answer = f"No documents available to answer: {question}"
            answers.append(answer)
        
        # Clean up temporary files
        for doc in downloaded_docs:
            try:
                os.unlink(doc['file_path'])
            except:
                pass  # Ignore cleanup errors
        
        return {"answers": answers}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "document-processing-webhook"}