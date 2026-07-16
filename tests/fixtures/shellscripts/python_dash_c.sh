#!/bin/bash
set -euo pipefail

# Single-line python3 -c with double quotes
VERSION=$(oc version -o json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['openshiftVersion'].rsplit('.',1)[0])")

# Multi-line python3 -c with double quotes
ITEMS=$(oc get pods -o json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('items', []):
    finalizers = item.get('metadata', {}).get('finalizers', [])
    if finalizers:
        print(item['metadata']['name'])
" 2>/dev/null || echo "")

# Single-line python3 -c with single quotes
TOKEN=$(curl -s "$AUTH_URL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

# python3 -m should be ignored
python3 -m json.tool < data.json
