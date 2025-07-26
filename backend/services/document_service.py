import os
import uuid
from typing import List, Dict
import PyPDF2
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self.embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 1000))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 200))
        
    async def initialize_collection(self):
        """Initialize Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 embedding size
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If this isn't the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_endings = ['. ', '! ', '? ', '\n\n']
                best_break = end
                
                for i in range(max(0, end - 100), end):
                    for ending in sentence_endings:
                        if text[i:i+len(ending)] == ending:
                            best_break = i + len(ending)
                
                end = best_break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            
        return chunks

    async def process_pdf(self, pdf_path: str, filename: str) -> Dict:
        """Process PDF file and store embeddings in Qdrant"""
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            # Split into chunks
            chunks = self.chunk_text(text)
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(chunks)
            
            # Prepare points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid.uuid4())
                point = PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "text": chunk,
                        "source": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                )
                points.append(point)
            
            # Upload to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully processed {filename}: {len(chunks)} chunks")
            
            return {
                "filename": filename,
                "chunks": len(chunks),
                "text_length": len(text)
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            raise

    async def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar text chunks"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=limit,
                with_payload=True
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "text": result.payload["text"],
                    "source": result.payload["source"],
                    "score": result.score,
                    "chunk_index": result.payload["chunk_index"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching chunks: {str(e)}")
            raise

    async def list_documents(self) -> List[str]:
        """List all unique document sources in the collection"""
        try:
            # Get all points to extract unique sources
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )
            
            sources = set()
            for point in scroll_result[0]:
                if "source" in point.payload:
                    sources.add(point.payload["source"])
            
            return list(sources)
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise

    async def delete_document(self, document_name: str) -> int:
        """Delete all chunks belonging to a specific document"""
        try:
            # Find all points with the given source
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "source",
                            "match": {"value": document_name}
                        }
                    ]
                },
                limit=1000,
                with_payload=True
            )
            
            # Extract point IDs
            point_ids = [point.id for point in scroll_result[0]]
            
            # Delete points
            if point_ids:
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
            
            logger.info(f"Deleted {len(point_ids)} chunks for document: {document_name}")
            return len(point_ids)
            
        except Exception as e:
            logger.error(f"Error deleting document {document_name}: {str(e)}")
            raise
