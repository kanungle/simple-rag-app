from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import List
import logging
from datetime import datetime

from services.document_service import DocumentService
from services.chat_service import ChatService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Chat API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_service = DocumentService()
chat_service = ChatService()

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[str]

@app.on_event("startup")
async def startup_event():
    """Initialize Qdrant collection on startup"""
    await document_service.initialize_collection()
    logger.info("Application started successfully")

@app.get("/")
async def root():
    return {"message": "RAG Chat API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint to verify system status"""
    try:
        # Check Qdrant connection
        collections = document_service.qdrant_client.get_collections()
        qdrant_status = "connected"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {str(e)}")
        qdrant_status = "disconnected"
    
    return {
        "status": "healthy",
        "backend_status": "connected",
        "qdrant_status": qdrant_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the PDF
        result = await document_service.process_pdf(temp_path, file.filename)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {"message": f"Successfully processed {file.filename}", "chunks": result["chunks"]}
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG"""
    try:
        response = await chat_service.generate_response(
            request.message, 
            request.conversation_history
        )
        return response
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all processed documents"""
    try:
        documents = await document_service.list_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{document_name}")
async def delete_document(document_name: str):
    """Delete a document and its chunks"""
    try:
        result = await document_service.delete_document(document_name)
        return {"message": f"Document {document_name} deleted successfully", "deleted_count": result}
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
