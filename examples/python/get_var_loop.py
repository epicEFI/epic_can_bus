#!/usr/bin/env python3
import sys
import signal
from pathlib import Path
from EpicECU import can_socket, get_variable, get_variable_by_name


def list_variables():
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
    print('usage: get_var_loop.py <ecu_addr:0..15> <var_name | hash:int>  # Ctrl-C to stop')


def main():
    if len(sys.argv) == 1:
        list_variables()
        return 0
    if len(sys.argv) != 3:
        print('usage: get_var_loop.py <ecu_addr:0..15> <var_name | hash:int>  # Ctrl-C to stop')
        return 1

    ecu_addr = int(sys.argv[1], 0)
    token = sys.argv[2]

    # Handle Ctrl-C cleanly
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    s = can_socket()

    # Fast loop: request/receive and print values continuously
    try:
        # Try integer hash once to avoid repeated exceptions
        var_hash = int(token, 0)
        while True:
            val = get_variable(s, var_hash, dest=ecu_addr)
            print(val, flush=True)
    except ValueError:
        while True:
            val = get_variable_by_name(s, token, dest=ecu_addr)
            print(val, flush=True)


if __name__ == '__main__':
    raise SystemExit(main())




