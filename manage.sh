#!/bin/bash

# RAG Chat Application Manager
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ first."
        exit 1
    fi
}

check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi
}

setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    cd ..
    print_success "Backend setup complete!"
}

setup_frontend() {
    print_status "Setting up frontend..."
    
    if [ ! -d "node_modules" ]; then
        print_status "Installing Node.js dependencies..."
        npm install
    fi
    
    print_success "Frontend setup complete!"
}

start_qdrant() {
    print_status "Starting Qdrant vector database..."
    
    # Stop existing container if running
    docker stop qdrant-rag 2>/dev/null || true
    docker rm qdrant-rag 2>/dev/null || true
    
    # Start new container
    docker run -d \
        --name qdrant-rag \
        -p 6333:6333 \
        -p 6334:6334 \
        -v $(pwd)/backend/qdrant_storage:/qdrant/storage \
        qdrant/qdrant:latest
    
    # Wait for Qdrant to be ready
    print_status "Waiting for Qdrant to be ready..."
    until curl -s http://localhost:6333/health > /dev/null 2>&1; do
        sleep 2
    done
    
    print_success "Qdrant is ready at http://localhost:6333"
}

start_backend() {
    print_status "Starting FastAPI backend..."
    
    cd backend
    source venv/bin/activate
    
    # Check if .env file exists and has OpenAI API key
    if [ ! -f ".env" ] || ! grep -q "OPENAI_API_KEY=sk-" .env; then
        print_warning "Please set your OpenAI API key in backend/.env file"
        print_warning "Copy backend/.env to create your local environment file and add:"
        print_warning "OPENAI_API_KEY=your_openai_api_key_here"
    fi
    
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    
    cd ..
    print_success "Backend started at http://localhost:8000"
    
    # Wait a bit for the server to start
    sleep 3
}

start_frontend() {
    print_status "Starting Next.js frontend..."
    
    npm run dev &
    FRONTEND_PID=$!
    
    print_success "Frontend started at http://localhost:3000"
}

stop_services() {
    print_status "Stopping services..."
    
    # Stop frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Stop backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Stop Qdrant
    docker stop qdrant-rag 2>/dev/null || true
    
    print_success "All services stopped"
}

show_help() {
    echo "RAG Chat Application Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Setup backend and frontend dependencies"
    echo "  start     - Start all services (Qdrant, backend, frontend)"
    echo "  stop      - Stop all services"
    echo "  qdrant    - Start only Qdrant database"
    echo "  backend   - Start only backend server"
    echo "  frontend  - Start only frontend server"
    echo "  status    - Check status of services"
    echo "  help      - Show this help message"
    echo ""
}

check_status() {
    print_status "Checking service status..."
    
    # Check Qdrant
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        print_success "Qdrant is running on port 6333"
    else
        print_warning "Qdrant is not running"
    fi
    
    # Check Backend
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        print_success "Backend is running on port 8000"
    else
        print_warning "Backend is not running"
    fi
    
    # Check Frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend is running on port 3000"
    else
        print_warning "Frontend is not running"
    fi
}

# Handle Ctrl+C
trap stop_services EXIT

case "${1:-help}" in
    setup)
        check_python
        check_node
        check_docker
        setup_backend
        setup_frontend
        ;;
    start)
        check_docker
        check_python
        check_node
        start_qdrant
        start_backend
        start_frontend
        print_success "All services started successfully!"
        print_status "Access the application at http://localhost:3000"
        print_status "API documentation at http://localhost:8000/docs"
        print_status "Qdrant dashboard at http://localhost:6333/dashboard"
        print_status "Press Ctrl+C to stop all services"
        wait
        ;;
    stop)
        stop_services
        ;;
    qdrant)
        check_docker
        start_qdrant
        ;;
    backend)
        check_python
        start_backend
        wait
        ;;
    frontend)
        check_node
        start_frontend
        wait
        ;;
    status)
        check_status
        ;;
    help|*)
        show_help
        ;;
esac
