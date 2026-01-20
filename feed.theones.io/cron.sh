#!/bin/bash
# Cron script for feed.theones.io news collection
# Run 4x daily: 00:00, 06:00, 12:00, 18:00 UTC

set -e

SCRIPT_DIR="/home/vizi/feed.theones.io/collector"
LOG_FILE="/home/vizi/feed.theones.io/logs/collect.log"
VENV_PATH="/home/vizi/feed.theones.io/venv"

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Set environment variables
export AGENTZERO_API_URL="http://194.181.240.37:50001/api_message"
export AGENTZERO_API_KEY="4B9112TjgQDCcW6K"

# Run collector
echo "=== $(date -u +"%Y-%m-%d %H:%M:%S UTC") ===" >> "$LOG_FILE"
python3 "$SCRIPT_DIR/collect.py" >> "$LOG_FILE" 2>&1

# Keep only last 1000 lines of log
tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
