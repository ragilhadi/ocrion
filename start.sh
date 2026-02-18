#!/bin/bash

# OCRion API Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   OCRion API Startup${NC}"
echo -e "${GREEN}========================================${NC}"

# # Load environment variables
# if [ -f .env ]; then
#     echo -e "${GREEN}Loading environment variables from .env${NC}"
#     export $(cat .env | grep -v '^#' | xargs)
# else
#     echo -e "${YELLOW}Warning: .env file not found${NC}"
#     echo -e "${YELLOW}Using default environment variables${NC}"
# fi

# # Activate virtual environment if it exists
# if [ -d "venv" ]; then
#     echo -e "${GREEN}Activating virtual environment${NC}"
#     source venv/bin/activate
# else
#     echo -e "${YELLOW}Warning: venv directory not found${NC}"
#     echo -e "${YELLOW}Create virtual environment: python -m venv venv${NC}"
# fi

# Check if required environment variables are set
# if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
#     echo -e "${RED}Error: OPENROUTER_API_KEY is not set${NC}"
#     echo -e "${YELLOW}Please set OPENROUTER_API_KEY in .env file${NC}"
#     exit 1
# fi

# # Install dependencies if requirements.txt exists and venv was just created
# if [ ! -f "venv/.installed" ] && [ -f "requirements.txt" ]; then
#     echo -e "${GREEN}Installing dependencies${NC}"
#     pip install -r requirements.txt
#     touch venv/.installed
# fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start server with Gunicorn
echo -e "${GREEN}Starting server with Gunicorn...${NC}"
echo -e "${GREEN}Workers: ${WORKERS:-4}${NC}"
echo -e "${GREEN}Port: ${API_PORT:-8000}${NC}"
echo ""

gunicorn app.main:app --config gunicorn.conf.py
