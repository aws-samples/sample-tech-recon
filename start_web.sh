#!/bin/bash

# Tech Recon Web Application Starter Script

echo "=========================================="
echo "Tech Recon Web Application Starter"
echo "=========================================="

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Sync dependencies and install Flask packages
echo "Syncing dependencies..."
uv sync > /dev/null 2>&1

echo "Installing web packages..."
uv pip install flask flask-socketio python-socketio --quiet 2>/dev/null

echo ""
echo "=========================================="
echo "Starting Web Server..."
echo "=========================================="
echo ""

# Run web application with .venv Python
.venv/bin/python web_app.py
