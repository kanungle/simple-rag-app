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
    evaluate: bool = False

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    evaluation: dict = None

class DocumentMetadataUpdate(BaseModel):
    metadata: dict

class DocumentResponse(BaseModel):
    name: str
    filename: str
    file_size: int
    page_count: int
    total_chunks: int
    processed_at: str
    text_length: int
    actual_chunks: int

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
            request.conversation_history,
            request.evaluate
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
        return {
            "message": f"Document {document_name} deleted successfully", 
            "deleted_chunks": result["deleted_chunks"],
            "deleted_at": result["deleted_at"],
            "document_metadata": result["document_metadata"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.get("/documents/{document_name}")
async def get_document(document_name: str):
    """Get detailed information about a specific document"""
    try:
        document = await document_service.get_document(document_name)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_name} not found")
        return document
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")

@app.put("/documents/{document_name}/metadata")
async def update_document_metadata(document_name: str, request: DocumentMetadataUpdate):
    """Update metadata for a document"""
    try:
        result = await document_service.update_document_metadata(document_name, request.metadata)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating document metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating document metadata: {str(e)}")

@app.get("/documents/statistics/overview")
async def get_document_statistics():
    """Get overall statistics about all documents"""
    try:
        stats = await document_service.get_document_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting document statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document statistics: {str(e)}")

@app.get("/evaluation/summary")
async def get_evaluation_summary():
    """Get evaluation metrics summary"""
    try:
        summary = chat_service.evaluation_service.get_evaluation_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting evaluation summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting evaluation summary: {str(e)}")

@app.get("/evaluation/history")
async def get_evaluation_history():
    """Get evaluation history"""
    try:
        history = chat_service.evaluation_service.evaluation_history
        return {"history": history}
    except Exception as e:
        logger.error(f"Error getting evaluation history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting evaluation history: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
