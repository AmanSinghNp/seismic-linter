#!/bin/bash
# Quick setup script for development environment

echo "🚀 Setting up seismic-linter development environment..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run initial tests
pytest

echo "✅ Setup complete! Start coding with 'source venv/bin/activate'"
