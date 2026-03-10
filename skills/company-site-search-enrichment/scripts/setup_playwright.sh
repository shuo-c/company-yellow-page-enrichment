#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -r "$(dirname "$0")/../requirements.txt"
python3 -m playwright install chromium

echo "Playwright setup complete (Python package + Chromium browser)."
