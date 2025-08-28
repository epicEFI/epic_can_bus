#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from EpicECU import can_socket, call_function


def main():
    if len(sys.argv) < 2:
        # List available functions from functions_v1.json
        base = Path(__file__).resolve().parents[2]
        cfg = base / 'functions_v1.json'
        try:
            data = json.loads(cfg.read_text(encoding='utf-8')) if cfg.exists() else []
        except Exception as e:
            print(f'error reading {cfg}: {e}')
            data = []
        print('Available functions:')
        for it in data:
            _id = it.get('id')
            name = it.get('luaName', '')
            arg = it.get('arg', 'NONE')
            ret = it.get('ret', 'NONE')
            print(f"  {_id:>3}  {name:<28} arg={arg:<7} ret={ret}")
        print('usage: call_func.py <dest_ecu:0..15> <func_id:int|name> [arg_f32:float] [arg2_i16:int]')
        return 0
    if len(sys.argv) < 3:
        print('usage: call_func.py <dest_ecu:0..15> <func_id:int|name> [arg_f32:float] [arg2_i16:int]')
        return 1
    dest = int(sys.argv[1], 0)
    func_token = sys.argv[2]
    arg = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    arg2 = int(sys.argv[4], 0) if len(sys.argv) > 4 else None
    s = can_socket()
    ret = call_function(s, func_token, arg, dest=dest, arg2_i16=arg2)
    print(ret)


if __name__ == '__main__':
    raise SystemExit(main())
