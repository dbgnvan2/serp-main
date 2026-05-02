#!/bin/bash

# Phase 1 Testing Script for Configuration Manager
# Tests validators, config manager initialization, and serp-me.py integration

set -e

echo "==================================================================="
echo "Phase 1: Configuration Manager Testing"
echo "==================================================================="
echo ""

# Activate venv
echo "[1/4] Activating virtual environment..."
source venv/bin/activate
echo "✓ venv activated"
echo ""

# Check Phase 1 deliverables exist
echo "[2/4] Verifying Phase 1 deliverables..."
required_files=(
    "config_validators.py"
    "config_manager.py"
    "tests/test_config_validators.py"
    "tests/test_config_manager.py"
)

all_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "ERROR: Some Phase 1 deliverables are missing!"
    exit 1
fi
echo "✓ All deliverables present"
echo ""

# Run validator tests
echo "[3/4] Running validator tests..."
python3 -m pytest tests/test_config_validators.py -v --tb=short
echo ""

# Run config manager tests
echo "[4/4] Running config manager tests..."
python3 -m pytest tests/test_config_manager.py -v --tb=short
echo ""

echo "==================================================================="
echo "Phase 1 Testing Complete!"
echo "==================================================================="
echo ""
echo "To test the GUI manually:"
echo "  1. source venv/bin/activate"
echo "  2. python3 serp-me.py"
echo "  3. Click 'Edit Configuration' button"
echo ""
echo "To run full test suite:"
echo "  python3 -m pytest test_*.py tests/ -q"
echo ""
