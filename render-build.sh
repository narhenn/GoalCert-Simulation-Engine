#!/usr/bin/env bash
set -euo pipefail

echo "=== Building frontend ==="
cd frontend
npm install
npm run build
echo "=== Frontend built ==="

echo "=== Copying dist/ to backend/static/ ==="
rm -rf ../backend/static
cp -r dist ../backend/static
echo "=== Static files ready ==="

echo "=== Installing backend dependencies ==="
cd ../backend
pip install --upgrade pip
pip install .
echo "=== Backend ready ==="
