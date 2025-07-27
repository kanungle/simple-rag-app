import os
from typing import List, Dict
import openai
from services.document_service import DocumentService
from services.evaluation_service import EvaluationService
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.document_service = DocumentService()
        self.evaluation_service = EvaluationService()
        
    async def generate_response(self, message: str, conversation_history: List[Dict] = None, evaluate: bool = False) -> Dict:
        """Generate a response using RAG"""
        try:
            # Search for relevant documents
            relevant_chunks = await self.document_service.search_similar_chunks(message, limit=3)
            
            # Prepare context from retrieved chunks
            context = ""
            sources = []
            contexts_text = []
            
            if relevant_chunks:
                context = "Based on the following relevant information:\n\n"
                for i, chunk in enumerate(relevant_chunks):
                    context += f"Source {i+1} ({chunk['source']}):\n{chunk['text']}\n\n"
                    contexts_text.append(chunk['text'])
                    if chunk['source'] not in sources:
                        sources.append(chunk['source'])
            
            # Prepare conversation history
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful AI assistant that answers questions based on the provided context. 
                    If the context contains relevant information, use it to answer the question. 
                    If the context doesn't contain enough information to answer the question, say so clearly.
                    Always be accurate and cite the sources when you use information from the context."""
                }
            ]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-5:]:  # Keep last 5 messages for context
                    messages.append(msg)
            
            # Add current query with context
            current_message = message
            if context:
                current_message = f"{context}\n\nQuestion: {message}"
            
            messages.append({
                "role": "user",
                "content": current_message
            })
            
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            result = {
                "response": response_text,
                "sources": sources
            }
            
            # Add evaluation if requested
            if evaluate and contexts_text:
                try:
                    evaluation = await self.evaluation_service.evaluate_response(
                        query=message,
                        response=response_text,
                        retrieved_contexts=contexts_text,
                        sources=sources
                    )
                    result["evaluation"] = evaluation
                except Exception as e:
                    logger.error(f"Error during evaluation: {str(e)}")
                    result["evaluation"] = {"error": str(e)}
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def format_conversation_history(self, history: List[Dict]) -> List[Dict]:
        """Format conversation history for OpenAI API"""
        formatted_history = []
        for msg in history:
            if msg.get("role") in ["user", "assistant"]:
                formatted_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return formatted_history
