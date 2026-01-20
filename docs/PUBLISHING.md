# Publishing to PyPI

## Prerequisites

1. PyPI account: https://pypi.org/account/register/
2. API token: https://pypi.org/manage/account/token/

## One-time Setup

```bash
# Store your PyPI token
# Create ~/.pypirc file:
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE
EOF

chmod 600 ~/.pypirc
```

## Publishing Steps

```bash
cd ~/Projects/active/agentzerocli

# 1. Clean previous builds
rm -rf dist build *.egg-info

# 2. Activate venv
source venv/bin/activate

# 3. Build package
python -m build

# 4. Check package
twine check dist/*

# 5. Upload to PyPI
twine upload dist/*
```

## After Publishing

Users can install with:
```bash
pip install agentzero-cli
```

And run with:
```bash
a0      # TUI mode
a0cli   # CLI mode
```

## Version Bump

Before publishing new version:

1. Update `pyproject.toml`:
   ```toml
   version = "0.2.1"  # bump version
   ```

2. Update `agentzero_cli/__init__.py`:
   ```python
   __version__ = "0.2.1"
   ```

3. Update `CHANGELOG.md`

4. Commit and tag:
   ```bash
   git add -A
   git commit -m "release: v0.2.1"
   git tag v0.2.1
   git push origin main --tags
   ```

## Test PyPI (Optional)

To test before real release:

```bash
# Upload to test PyPI
twine upload --repository testpypi dist/*

# Install from test PyPI
pip install --index-url https://test.pypi.org/simple/ agentzero-cli
```
