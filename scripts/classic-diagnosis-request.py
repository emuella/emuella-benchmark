#!/usr/bin/env python3
"""Construct a future classic diagnosis call from frozen metadata only."""
import argparse
import importlib.util
import json
from pathlib import Path


def refresh_module():
    path = Path(__file__).resolve().with_name('openjpeg-refresh.py')
    spec = importlib.util.spec_from_file_location('classic_diagnosis_refresh', path)
    refresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refresh)
    return refresh


def build(config):
    fields = {'kind', 'asset', 'prepared', 'streams', 'origin', 'codec', 'style',
              'workers', 'round', 'stream_identity'}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError('diagnosis request metadata fields differ')
    return refresh_module().make_existing_stream_call(
        config['kind'], config['asset'], Path(config['prepared']), Path(config['streams']),
        config['origin'], config['codec'], config['style'], config['workers'],
        config['round'], config['stream_identity'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path,
                        help='JSON metadata for one existing-stream call')
    args = parser.parse_args()
    print(json.dumps(build(json.loads(args.config.read_text())), sort_keys=True))


if __name__ == '__main__':
    main()
