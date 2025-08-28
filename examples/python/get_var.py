#!/usr/bin/env python3
import sys
from pathlib import Path
from EpicECU import can_socket, get_variable, get_variable_by_name


def main():
    if len(sys.argv) == 1:
        # List available variables from generated JSON
        base = Path(__file__).resolve().parents[2]
        vars_json = base / 'variables.json'
        try:
            import json
            data = json.loads(vars_json.read_text(encoding='utf-8')) if vars_json.exists() else []
        except Exception as e:
            print(f'error reading {vars_json}: {e}')
            data = []
        print('Available variables:')
        for item in data:
            name = item.get('name'); h = item.get('hash'); src = item.get('source')
            print(f"  {name:<32} hash={h!s:<12} source={src}")
        print('usage: get_var.py <ecu_addr:0..15> <var_name | hash:int>  # hash may be negative (signed 32-bit)')
        return 0
    if len(sys.argv) < 3 or len(sys.argv) > 3:
        print('usage: get_var.py <ecu_addr:0..15> <var_name | hash:int>  # hash may be negative (signed 32-bit)')
        return 1
    ecu_addr = int(sys.argv[1], 0)
    token = sys.argv[2]
    s = can_socket()
    try:
        var_hash = int(token, 0)
        # For get, ecu_addr is used as destination ECU in request
        val = get_variable(s, var_hash, dest=ecu_addr)
    except ValueError:
        val = get_variable_by_name(s, token, dest=ecu_addr)
    print(val)


if __name__ == '__main__':
    raise SystemExit(main())


