#!/bin/bash
set -euo pipefail

echo "=== Running setup ==="

if ! command -v oc &>/dev/null; then
    echo "oc not found"
    exit 1
fi

oc project my-project
oc apply -f manifests/

echo "=== Setup complete ==="
