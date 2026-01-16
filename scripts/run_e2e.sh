#!/bin/bash
# Run E2E suite with mock Agent Zero server.
set -euo pipefail

python -m pytest tests/test_e2e.py
