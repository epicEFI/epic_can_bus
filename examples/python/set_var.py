#!/usr/bin/env python3
import sys
import struct
from pathlib import Path
from EpicECU import can_socket, set_variable_by_name

def main():
    if len(sys.argv) == 1:
        # Print variables list from JSON similar to get_var.py
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
            # Only show config (writable) variables
            if item.get('source') != 'config':
                continue
            name = item.get('name'); h = item.get('hash'); src = item.get('source')
            print(f"  {name:<32} hash={h!s:<12} source={src}")
        print('usage: set_var.py <ecu_addr:0..15> <var_name> <value_float> [iface]')
        return 0
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print('usage: set_var.py <ecu_addr:0..15> <var_name> <value_float> [iface]')
        return 1
    ecu_addr = int(sys.argv[1], 0)
    name = sys.argv[2]
    value = float(sys.argv[3])
    iface = sys.argv[4] if len(sys.argv) > 4 else 'can0'

    # Enforce that only config variables are writable
    base = Path(__file__).resolve().parents[2]
    vars_json = base / 'variables.json'
    allow = False
    try:
        import json
        data = json.loads(vars_json.read_text(encoding='utf-8')) if vars_json.exists() else []
        lookup = {item.get('name','').lower(): item for item in data}
        it = lookup.get(name.lower())
        if it and it.get('source') == 'config':
            allow = True
    except Exception as e:
        print(f'warning: failed to validate variable writability against {vars_json}: {e}')
        allow = False

    if not allow:
        print(f'error: variable "{name}" is not writable (source is not "config" or not found)')
        return 2

    s = can_socket(iface)
    set_variable_by_name(s, name, value, ecu_addr=ecu_addr)
    print(f'sent set var {name} to {value} (ecu_addr={ecu_addr})')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


