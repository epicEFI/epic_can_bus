#!/usr/bin/env bash
set -euo pipefail
IF=${1:-can0}
RATE=${2:-500000}
sudo ip link set ${IF} down || true
sudo ip link set ${IF} type can bitrate ${RATE}
sudo ip link set ${IF} up
ip -details -statistics link show ${IF}

