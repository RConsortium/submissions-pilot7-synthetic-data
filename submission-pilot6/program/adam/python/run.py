#!/usr/bin/env python3
"""Check/build Pilot 6 ADSL, optionally requiring an official comparison."""

import argparse
from pathlib import Path

import yamaa

from compare import compare_domain

STUDY = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='validate the project without saving output')
    mode.add_argument('--compare', action='store_true', help='build and require the official reference to match')
    args = parser.parse_args()
    project = yamaa.project(STUDY / 'spec/yamaa/project.yaml')
    check = project.check()
    print(check)
    if check.status != 'succeeded':
        print(check.issues)
        return 1
    if args.check:
        return 0
    runs = project.run('adam')
    print(runs)
    if runs.status != 'succeeded':
        print(runs.issues)
        return 1
    runs.save()
    if args.compare:
        try:
            return int(not compare_domain()['ok'])
        except (FileNotFoundError, ValueError) as error:
            print(f'FAIL: {error}')
            return 1
    print('Built ADSL. Official reference comparison was not requested; use --compare to require it.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
