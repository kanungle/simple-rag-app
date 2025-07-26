#!/bin/bash

# Start Qdrant using Docker
echo "Starting Qdrant vector database..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Stop existing Qdrant container if running
docker stop qdrant-rag 2>/dev/null || true
docker rm qdrant-rag 2>/dev/null || true

# Start Qdrant container
docker run -d \
    --name qdrant-rag \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant:latest

echo "Qdrant is starting on http://localhost:6333"
echo "Web UI available at http://localhost:6333/dashboard"
echo "Waiting for Qdrant to be ready..."

# Wait for Qdrant to be ready
until curl -s http://localhost:6333/health > /dev/null 2>&1; do
    sleep 2
    echo "Waiting for Qdrant..."
done

echo "Qdrant is ready!"
