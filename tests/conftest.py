"""Pytest configuration and fixtures."""
import pytest
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ.setdefault("OPENROUTER_API_KEY", "test_key_for_testing")
os.environ.setdefault("MODEL_NAME", "test/model")
os.environ.setdefault("OCR_USE_GPU", "false")
