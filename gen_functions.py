#!/usr/bin/env python3
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'firmware' / 'controllers' / 'can' / 'epic_can.cpp'
OUT = ROOT / 'epic_can_bus' / 'functions_v1.json'

def parse_functions_from_cpp(text: str):
    entries = []
    # Matches lines like: { 35, "setDacVoltage", 1, false, fn_setDacVoltage },
    rx = re.compile(r"\{\s*(?P<id>\d+)\s*,\s*\"(?P<name>[^\"]+)\"\s*,\s*(?P<argc>\d+)\s*,\s*(?P<ret>true|false)\s*,")
    for line in text.splitlines():
        m = rx.search(line)
        if not m:
            continue
        func_id = int(m.group('id'))
        name = m.group('name')
        argc = int(m.group('argc'))
        ret_bool = (m.group('ret') == 'true')
        arg = 'NONE' if argc == 0 else ('F32' if argc == 1 else 'F32_I16')
        ret = 'F32' if ret_bool else 'NONE'
        entries.append({
            'id': func_id,
            'luaName': name,
            'arg': arg,
            'ret': ret,
        })
    # sort by id
    entries.sort(key=lambda x: x['id'])
    return entries

def main():
    if not SRC.exists():
        raise SystemExit(f'source not found: {SRC}')
    text = SRC.read_text(encoding='utf-8', errors='ignore')
    funcs = parse_functions_from_cpp(text)
    OUT.write_text(json.dumps(funcs, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()


