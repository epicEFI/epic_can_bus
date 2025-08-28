#!/usr/bin/env python3
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'epic_can_bus' / 'variables.json'

SRC_OUTPUT = ROOT / 'firmware' / 'controllers' / 'lua' / 'generated' / 'output_lookup_generated.cpp'
SRC_CONFIG = ROOT / 'firmware' / 'controllers' / 'lua' / 'generated' / 'value_lookup_generated.cpp'

def parse_hash_map(path: Path):
    entries = []
    if not path.exists():
        return entries
    rx = re.compile(r'^\s*//\s*(?P<name>[A-Za-z0-9_\.]+)\s*$')
    rx_case = re.compile(r'^\s*case\s+(?P<hash>-?\d+)\s*:\s*$')
    current_name = None
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        m = rx.match(line)
        if m:
            current_name = m.group('name')
            continue
        c = rx_case.match(line)
        if c and current_name:
            entries.append((current_name, int(c.group('hash'))))
            current_name = None
    return entries

def main():
    entries = []
    entries += parse_hash_map(SRC_OUTPUT)
    entries += parse_hash_map(SRC_CONFIG)

    # Build JSON list
    output_names = {n for (n, _) in parse_hash_map(SRC_OUTPUT)}
    data = []
    for name, h in sorted(set(entries), key=lambda x: (x[0].lower(), x[1])):
        source = 'output' if name in output_names else 'config'
        data.append({"name": name, "hash": h, "source": source})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()


