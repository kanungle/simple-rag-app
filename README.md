# RAG Chat Application

A Retrieval Augmented Generation (RAG) chat application that allows users to upload PDF documents and ask questions about their content. The app uses FastAPI for the backend, Qdrant as the vector database, OpenAI for chat completions, and Next.js for the frontend.

## Features

- 📄 **PDF Upload**: Upload PDF documents to build your knowledge base with progress tracking
- 💬 **Interactive Chat**: Ask questions about your uploaded documents
- 🔍 **Source Attribution**: See which documents were used to answer your questions
- 🚀 **Real-time Processing**: Fast document ingestion and retrieval
- 🎯 **Semantic Search**: Find relevant information using vector similarity
- 📊 **Status Indicators**: Real-time backend and database connection status
- 🔄 **Progress Tracking**: Visual upload and processing progress bars
- ⚡ **Health Monitoring**: Automatic system health checks every 30 seconds
- 📈 **RAG Evaluation**: Comprehensive evaluation system with 5 quality metrics
  - **Relevance**: How well the response addresses the user's query
  - **Faithfulness**: Whether the response is grounded in retrieved context
  - **Completeness**: How thoroughly the response addresses the query
  - **Clarity**: How clear and well-structured the response is
  - **Retrieval Quality**: Quality and diversity of retrieved contexts
- 🎛️ **Metrics Toggle**: Enable/disable evaluation for each chat interaction
- 📊 **Evaluation Dashboard**: View evaluation summary and trends in the sidebar

## Architecture

- **Frontend**: Next.js 15 with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python 3.13.0
- **Vector Database**: Qdrant (local Docker instance)
- **Embeddings**: OpenAI text-embedding-ada-002 (1536 dimensions)
- **LLM**: OpenAI GPT models
- **PDF Processing**: PyPDF2

## Prerequisites

- Python 3.12+ (3.13.0 recommended)
- Node.js 18+
- Docker (for Qdrant)
- OpenAI API key

## Setup Instructions

### 1. Clone and Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env .env.local
# Edit .env.local and add your OpenAI API key:
# OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Start Qdrant Vector Database

```bash
# From the backend directory
./start_qdrant.sh
```

This will start Qdrant in a Docker container on port 6333. The web UI will be available at http://localhost:6333/dashboard.

### 3. Start Backend Server

```bash
# From the backend directory
./start_server.sh
```

The FastAPI server will start on http://localhost:8000. You can view the API documentation at http://localhost:8000/docs.

### 4. Setup and Start Frontend

```bash
# From the root directory
npm install
npm run dev
```

The Next.js frontend will start on http://localhost:3000.

## Usage

1. **Start all services**: Make sure Qdrant, the FastAPI backend, and Next.js frontend are all running
2. **Upload PDFs**: Click the "Upload PDF" button in the top right to upload your documents
3. **Ask questions**: Type your questions in the chat interface
4. **View sources**: See which documents were used to answer your questions

## API Endpoints

- `POST /upload-pdf` - Upload and process a PDF file
- `POST /chat` - Send a chat message and get a response with sources
- `GET /documents` - List all processed documents
- `DELETE /documents/{document_name}` - Delete a document and its chunks

## Configuration

You can modify the following environment variables in `backend/.env`:

- `OPENAI_API_KEY` - Your OpenAI API key
- `QDRANT_HOST` - Qdrant host (default: localhost)
- `QDRANT_PORT` - Qdrant port (default: 6333)
- `COLLECTION_NAME` - Qdrant collection name (default: documents)
- `EMBEDDING_MODEL` - Sentence transformer model (default: all-MiniLM-L6-v2)
- `CHUNK_SIZE` - Text chunk size for processing (default: 1000)
- `CHUNK_OVERLAP` - Overlap between chunks (default: 200)

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Development

```bash
npm run dev
```

## Troubleshooting

### Common Issues

1. **Qdrant connection error**: Make sure Docker is running and Qdrant container is started
2. **OpenAI API errors**: Check that your API key is correctly set in the `.env` file
3. **PDF upload errors**: Ensure the uploaded file is a valid PDF
4. **Port conflicts**: Make sure ports 3000, 6333, and 8000 are available

### Logs

- Backend logs: Check the terminal where the FastAPI server is running
- Qdrant logs: `docker logs qdrant-rag`
- Frontend logs: Check the browser console and Next.js terminal

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.
