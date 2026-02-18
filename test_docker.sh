#!/bin/bash

# Docker Build and Test Script for OCRion API

set -e

echo "========================================="
echo "  OCRion Docker Build & Test"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Set environment variables for testing
export OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-test_key_for_docker_build}
export MODEL_NAME=${MODEL_NAME:-anthropic/claude-sonnet-4-20250514}
export OCR_USE_GPU=false

# Build the Docker image
echo "Building Docker image..."
docker build -t ocrion:latest .

echo ""
echo "Docker image built successfully!"
echo ""

# Run tests in Docker
echo "Running tests in Docker..."
docker run --rm \
  -e OPENROUTER_API_KEY=test_key_12345 \
  -e MODEL_NAME=test/model \
  -e OCR_USE_GPU=false \
  ocrion:latest \
  python -m pytest tests/test_unit_isolated.py tests/test_schemas.py -v

echo ""
echo "========================================="
echo "  Running health check on container"
echo "========================================="

# Start container and test health endpoint
docker run -d --name ocrion-test \
  -e OPENROUTER_API_KEY=test_key \
  -e MODEL_NAME=test/model \
  -e OCR_USE_GPU=false \
  -p 8001:8000 \
  ocrion:latest

# Wait for container to start
sleep 5

# Test health endpoint
echo "Testing /health endpoint..."
curl -s http://localhost:8001/health | python -m json.tool

# Stop container
docker stop ocrion-test
docker rm ocrion-test

echo ""
echo "========================================="
echo "  Docker test completed successfully!"
echo "========================================="
echo ""
echo "To run the container:"
echo "  docker run -p 8000:8000 -e OPENROUTER_API_KEY=your_key ocrion:latest"
echo ""
echo "To use docker-compose:"
echo "  docker-compose up -d"
