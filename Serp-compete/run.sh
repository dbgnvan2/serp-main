#!/bin/bash

# Serp-comp Runner Script

# Exit on error
set -e

echo "--- 1. Setting up environment ---"
# Check if spaCy model is downloaded
if ! python3 -c "import spacy; spacy.load('en_core_web_sm')" &>/dev/null; then
    echo "Downloading spaCy model..."
    python3 -m spacy download en_core_web_sm
fi

echo "--- 2. Running Tests ---"
export PYTHONPATH=.
pytest tests/

echo "--- 3. Running SEO Audit ---"
python3 src/main.py

echo "--- Audit Complete ---"
