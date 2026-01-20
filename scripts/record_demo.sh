#!/usr/bin/env bash
# Demo recording script for AgentZero CLI
# This creates a scripted demo session

set -e

DEMO_DIR="/tmp/agentzero_demo"
rm -rf "$DEMO_DIR"
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

# Create a sample Python file to work with
cat > hello.py << 'EOF'
def greet(name):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")
EOF

echo "Demo environment ready in $DEMO_DIR"
echo "Files created: hello.py"
echo ""
echo "Now run: asciinema rec demo.cast"
echo "Then manually:"
echo "  1. cd /tmp/agentzero_demo"
echo "  2. a0"
echo "  3. Type: list files in current directory"
echo "  4. Approve the ls command"
echo "  5. Type: read hello.py"
echo "  6. Type: /quit"
echo ""
echo "After recording: agg demo.cast demo.gif"
