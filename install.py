#!/usr/bin/env python3
"""Deprecated installer.

This repository is already structured and does not require file generation.
Use:
  - python -m venv venv
  - source venv/bin/activate
  - pip install -r requirements.txt
  - copy config.example.yaml to config.yaml
"""


def main() -> int:
    print("install.py is deprecated. See README.md for setup instructions.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
