#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   epic_can_bus/scripts/epic_call.sh <function_name> [arg_u32] [iface]
# Env overrides:
#   DEST (default 0), SRC (default 1)

FUNC_NAME=${1:-}
ARG_U32=${2:-0}
IFACE=${3:-can0}
DEST=${DEST:-0}
SRC=${SRC:-1}

if [[ -z "$FUNC_NAME" ]]; then
  echo "usage: $0 <function_name> [arg_u32] [iface]" >&2
  exit 1
fi

JSON_DIR="$(dirname "$0")/.."
JSON_DIR="$(cd "$JSON_DIR" && pwd)"
JSON_FILE="$JSON_DIR/functions_v1.json"

if [[ ! -f "$JSON_FILE" ]]; then
  echo "functions_v1.json not found at $JSON_FILE" >&2
  exit 2
fi

# awk parser: capture id preceding the matching luaName
FUNC_ID=$(awk -v tgt="$FUNC_NAME" '
  /"id"[[:space:]]*:/ {
    if (match($0, /[0-9]+/, m)) last_id=m[0];
  }
  /"luaName"[[:space:]]*:/ {
    if (match($0, /"luaName"[[:space:]]*:[[:space:]]*"([^"]+)"/, a)) {
      if (a[1]==tgt) { print last_id; exit 0 }
    }
  }
  END { if (NR>0) exit 1 }
' "$JSON_FILE") || true

if [[ -z "${FUNC_ID:-}" ]]; then
  echo "function not found: $FUNC_NAME (check $JSON_FILE)" >&2
  exit 3
fi

# Format fields
printf -v FID_BE "%04X" "$FUNC_ID"
printf -v DEST_HEX "%02X" "$DEST"
printf -v SRC_HEX "%02X" "$SRC"

# Normalize ARG_U32 (supports hex with 0x prefix)
if [[ "$ARG_U32" =~ ^0[xX][0-9a-fA-F]+$ ]]; then
  ARG_VAL=$((ARG_U32))
else
  ARG_VAL=$((ARG_U32+0))
fi
printf -v ARG_BE "%08X" "$ARG_VAL"

DATA_HEX="${FID_BE}${DEST_HEX}${SRC_HEX}${ARG_BE}"

echo "cansend $IFACE 740#${DATA_HEX}" >&2
cansend "$IFACE" "740#${DATA_HEX}"


