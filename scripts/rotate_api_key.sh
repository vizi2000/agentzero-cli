#!/bin/bash
# Reminder script for rotating API keys.
set -euo pipefail

echo "Rotate your Agent Zero API key:"
echo "1. Revoke the old key on the Agent Zero console."
echo "2. Create a new key and export it:"
echo "   export AGENTZERO_API_KEY=\"new-value\""
echo "3. Update any secrets manager (CI/CD, desktop env)."
echo "4. Restart Agent Zero CLI if running."
