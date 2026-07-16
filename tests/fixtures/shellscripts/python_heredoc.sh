#!/bin/bash
set -euo pipefail

DATA_FILE="$1"

# Heredoc with quoted delimiter (no variable expansion)
python3 <<'PYEOF'
import json, sys

with open("data.json", "r") as f:
    data = json.load(f)

for item in data.get("items", []):
    print(item["name"])
PYEOF

# Stdin heredoc with arguments
python3 - "$DATA_FILE" "$BUILD_NUMBER" <<'REGEOF'
import json, sys

data_file = sys.argv[1]
build_num = int(sys.argv[2])

with open(data_file, "r") as f:
    data = json.load(f)

for env in data.get("environments", []):
    if env["id"] == build_num:
        sys.exit(0)

data["environments"].append({"id": build_num})
with open(data_file, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
REGEOF

echo "Done"
