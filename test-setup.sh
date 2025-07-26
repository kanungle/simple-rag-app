#!/bin/bash

# Test script for RAG Chat Application
set -e

echo "🧪 Testing RAG Chat Application Setup"
echo "===================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_passed() {
    echo -e "${GREEN}✓${NC} $1"
}

test_failed() {
    echo -e "${RED}✗${NC} $1"
}

test_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking prerequisites..."

# Check Docker
if command -v docker &> /dev/null; then
    if docker info > /dev/null 2>&1; then
        test_passed "Docker is installed and running"
    else
        test_failed "Docker is installed but not running"
        exit 1
    fi
else
    test_failed "Docker is not installed"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    test_passed "Python 3 is installed (version: $PYTHON_VERSION)"
else
    test_failed "Python 3 is not installed"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    test_passed "Node.js is installed (version: $NODE_VERSION)"
else
    test_failed "Node.js is not installed"
    exit 1
fi

echo ""
echo "2. Checking project structure..."

# Check backend files
if [ -f "backend/requirements.txt" ]; then
    test_passed "Backend requirements.txt exists"
else
    test_failed "Backend requirements.txt missing"
fi

if [ -f "backend/main.py" ]; then
    test_passed "Backend main.py exists"
else
    test_failed "Backend main.py missing"
fi

if [ -f "backend/.env" ]; then
    if grep -q "OPENAI_API_KEY=sk-" backend/.env; then
        test_passed "OpenAI API key is configured"
    else
        test_warning "OpenAI API key not set in backend/.env"
    fi
else
    test_warning "Backend .env file not found (copy from .env.example)"
fi

# Check frontend files
if [ -f "package.json" ]; then
    test_passed "Frontend package.json exists"
else
    test_failed "Frontend package.json missing"
fi

if [ -f "app/page.tsx" ]; then
    test_passed "Frontend page.tsx exists"
else
    test_failed "Frontend page.tsx missing"
fi

if [ -d "node_modules" ]; then
    test_passed "Frontend dependencies installed"
else
    test_warning "Frontend dependencies not installed (run 'npm install')"
fi

echo ""
echo "3. Testing services..."

# Test if services are running
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    test_passed "Qdrant is running on port 6333"
else
    test_warning "Qdrant is not running (run './manage.sh qdrant' to start)"
fi

if curl -s http://localhost:8000 > /dev/null 2>&1; then
    test_passed "Backend is running on port 8000"
else
    test_warning "Backend is not running (run './manage.sh backend' to start)"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    test_passed "Frontend is running on port 3000"
else
    test_warning "Frontend is not running (run './manage.sh frontend' to start)"
fi

echo ""
echo "4. Quick setup guide:"
echo "   1. Copy backend/.env.example to backend/.env and add your OpenAI API key"
echo "   2. Run './manage.sh setup' to install all dependencies"
echo "   3. Run './manage.sh start' to start all services"
echo "   4. Open http://localhost:3000 in your browser"
echo ""
echo "🎉 Setup test complete!"
