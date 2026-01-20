#!/bin/bash
# Cleanup helper for workspace uploads folder.

UPLOAD_DIR="${AGENTZERO_UPLOAD_DIR:-uploads}"

if [ ! -d "$UPLOAD_DIR" ]; then
    echo "Uploads directory not found: $UPLOAD_DIR"
    exit 0
fi

find "$UPLOAD_DIR" -type f -mtime +30 -print -delete
echo "Old uploads removed from $UPLOAD_DIR"
