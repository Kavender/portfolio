#!/bin/bash

# Install the package in development mode
pip install -e .

echo "Package installed in development mode. You can now use simplified imports."
echo "Example: from utils.logger import setup_logger (instead of from src.utils.logger import setup_logger)"
echo ""
echo "If you're using a different virtual environment (like .venv), make sure to activate it first:"
echo "source .venv/bin/activate"
echo "Then run this script again to install the package in that environment."