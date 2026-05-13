#!/usr/bin/env python3
"""一键生成全部教程插图。"""
import sys
import os
import glob
import importlib

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    os.chdir(script_dir)

    scripts = sorted(glob.glob(os.path.join(script_dir, 'draw_*.py')))
    total = 0

    for script_path in scripts:
        module_name = os.path.basename(script_path)[:-3]
        print(f'\n{"="*60}')
        print(f'Running {module_name}...')
        print(f'{"="*60}')
        try:
            module = importlib.import_module(module_name)
            module.main()
        except Exception as e:
            print(f'  [ERROR] {module_name}: {e}')

    output_dir = os.path.join(script_dir, 'output')
    pngs = glob.glob(os.path.join(output_dir, '*.png'))
    print(f'\n{"="*60}')
    print(f'Done! Generated {len(pngs)} diagrams in output/')
    print(f'{"="*60}')

if __name__ == '__main__':
    main()
