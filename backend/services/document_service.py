import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import PyPDF2
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        self.collection_name = os.getenv("COLLECTION_NAME", "documents")
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
                        size=1536,  # OpenAI text-embedding-ada-002 size
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
            
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        try:
            # Filter out empty texts
            valid_texts = [text.strip() for text in texts if text.strip()]
            
            if not valid_texts:
                raise ValueError("No valid text chunks provided for embedding generation")
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=valid_texts
            )
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    async def process_pdf(self, pdf_path: str, filename: str, metadata: Dict = None) -> Dict:
        """Process PDF file and store embeddings in Qdrant with enhanced metadata"""
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")

            # Get file stats
            file_stats = os.stat(pdf_path)
            file_size = file_stats.st_size
            
            # Count pages
            page_count = 0
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    page_count = len(pdf_reader.pages)
            except Exception as e:
                logger.warning(f"Could not count pages: {str(e)}")

            # Split into chunks
            chunks = self.chunk_text(text)
            
            if not chunks:
                raise ValueError("No valid text chunks could be created from the PDF")

            # Filter out empty chunks
            valid_chunks = [chunk for chunk in chunks if chunk.strip()]
            
            if not valid_chunks:
                raise ValueError("No valid text chunks after filtering")

            # Generate embeddings
            embeddings = self.get_embeddings(valid_chunks)
            
            # Ensure we have the same number of chunks and embeddings
            if len(valid_chunks) != len(embeddings):
                raise ValueError(f"Mismatch between chunks ({len(valid_chunks)}) and embeddings ({len(embeddings)})")

            # Create document metadata
            document_metadata = {
                "filename": filename,
                "file_size": file_size,
                "page_count": page_count,
                "total_chunks": len(valid_chunks),
                "processed_at": datetime.now().isoformat(),
                "text_length": len(text),
                **(metadata or {})
            }

            # Prepare points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(valid_chunks, embeddings)):
                point_id = str(uuid.uuid4())
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "source": filename,
                        "chunk_index": i,
                        "total_chunks": len(valid_chunks),
                        "document_metadata": document_metadata,
                        "chunk_length": len(chunk),
                        "created_at": datetime.now().isoformat()
                    }
                )
                points.append(point)

            # Upload to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully processed {filename} with {len(valid_chunks)} chunks")
            
            return {
                "chunks": len(valid_chunks),
                "embeddings": len(embeddings),
                "filename": filename,
                "file_size": file_size,
                "page_count": page_count,
                "text_length": len(text),
                "processed_at": document_metadata["processed_at"]
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            raise

    async def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar text chunks using vector similarity"""
        try:
            # Generate embedding for the query
            query_embedding = self.get_embeddings([query])[0]
            
            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )
            
            results = []
            for result in search_result:
                results.append({
                    "text": result.payload.get("text", ""),
                    "source": result.payload.get("source", "Unknown"),
                    "score": result.score,
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "chunk_length": result.payload.get("chunk_length", 0)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise

    async def list_documents(self) -> List[Dict]:
        """List all documents with detailed metadata"""
        try:
            # Get all points to extract unique sources with metadata
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )
            
            documents = {}
            for point in scroll_result[0]:
                if "source" in point.payload:
                    source = point.payload["source"]
                    
                    if source not in documents:
                        # Initialize document info
                        doc_metadata = point.payload.get("document_metadata", {})
                        documents[source] = {
                            "name": source,
                            "filename": doc_metadata.get("filename", source),
                            "file_size": doc_metadata.get("file_size", 0),
                            "page_count": doc_metadata.get("page_count", 0),
                            "total_chunks": doc_metadata.get("total_chunks", 0),
                            "processed_at": doc_metadata.get("processed_at"),
                            "text_length": doc_metadata.get("text_length", 0),
                            "chunks": []
                        }
                    
                    # Add chunk info
                    documents[source]["chunks"].append({
                        "id": point.id,
                        "chunk_index": point.payload.get("chunk_index", 0),
                        "chunk_length": point.payload.get("chunk_length", 0),
                        "created_at": point.payload.get("created_at"),
                        "text_preview": point.payload.get("text", "")[:100] + "..." if len(point.payload.get("text", "")) > 100 else point.payload.get("text", "")
                    })
            
            # Sort chunks by index for each document
            for doc in documents.values():
                doc["chunks"].sort(key=lambda x: x["chunk_index"])
                doc["actual_chunks"] = len(doc["chunks"])
            
            return list(documents.values())
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise

    async def get_document(self, document_name: str) -> Optional[Dict]:
        """Get detailed information about a specific document"""
        try:
            # Get all chunks for this document
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=document_name)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True
            )
            
            if not scroll_result[0]:
                return None
            
            chunks = []
            document_metadata = None
            
            for point in scroll_result[0]:
                if document_metadata is None:
                    document_metadata = point.payload.get("document_metadata", {})
                
                chunks.append({
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "chunk_index": point.payload.get("chunk_index", 0),
                    "chunk_length": point.payload.get("chunk_length", 0),
                    "created_at": point.payload.get("created_at")
                })
            
            # Sort chunks by index
            chunks.sort(key=lambda x: x["chunk_index"])
            
            return {
                "name": document_name,
                "filename": document_metadata.get("filename", document_name),
                "file_size": document_metadata.get("file_size", 0),
                "page_count": document_metadata.get("page_count", 0),
                "total_chunks": document_metadata.get("total_chunks", len(chunks)),
                "processed_at": document_metadata.get("processed_at"),
                "text_length": document_metadata.get("text_length", 0),
                "actual_chunks": len(chunks),
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Error getting document {document_name}: {str(e)}")
            raise

    async def update_document_metadata(self, document_name: str, metadata: Dict) -> Dict:
        """Update metadata for a document"""
        try:
            # Get all chunks for this document
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=document_name)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True
            )
            
            if not scroll_result[0]:
                raise ValueError(f"Document {document_name} not found")
            
            # Update metadata for all chunks
            points_to_update = []
            for point in scroll_result[0]:
                # Merge new metadata with existing document metadata
                current_doc_metadata = point.payload.get("document_metadata", {})
                updated_doc_metadata = {**current_doc_metadata, **metadata, "updated_at": datetime.now().isoformat()}
                
                # Update the point payload
                updated_payload = {**point.payload, "document_metadata": updated_doc_metadata}
                
                points_to_update.append(PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=updated_payload
                ))
            
            # Upsert updated points
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points_to_update
            )
            
            logger.info(f"Updated metadata for {len(points_to_update)} chunks of document: {document_name}")
            
            return {
                "document_name": document_name,
                "updated_chunks": len(points_to_update),
                "updated_metadata": metadata,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating document metadata {document_name}: {str(e)}")
            raise

    async def delete_document(self, document_name: str) -> Dict:
        """Delete all chunks belonging to a specific document"""
        try:
            # Find all points with the given source
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=document_name)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True
            )
            
            # Extract point IDs
            point_ids = [point.id for point in scroll_result[0]]
            
            if not point_ids:
                raise ValueError(f"Document {document_name} not found")
            
            # Get document metadata before deletion
            doc_metadata = scroll_result[0][0].payload.get("document_metadata", {}) if scroll_result[0] else {}
            
            # Delete points
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
            
            logger.info(f"Deleted {len(point_ids)} chunks for document: {document_name}")
            
            return {
                "document_name": document_name,
                "deleted_chunks": len(point_ids),
                "deleted_at": datetime.now().isoformat(),
                "document_metadata": doc_metadata
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_name}: {str(e)}")
            raise

    async def get_document_statistics(self) -> Dict:
        """Get overall statistics about all documents"""
        try:
            # Get all points
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )
            
            total_chunks = len(scroll_result[0])
            total_documents = len(set(point.payload.get("source", "") for point in scroll_result[0]))
            total_size = sum(point.payload.get("document_metadata", {}).get("file_size", 0) for point in scroll_result[0])
            total_text_length = sum(point.payload.get("chunk_length", 0) for point in scroll_result[0])
            
            # Calculate average chunk size
            avg_chunk_size = total_text_length / total_chunks if total_chunks > 0 else 0
            
            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "total_file_size": total_size,
                "total_text_length": total_text_length,
                "average_chunk_size": avg_chunk_size,
                "collection_name": self.collection_name,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting document statistics: {str(e)}")
            raise
