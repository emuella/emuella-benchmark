#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
python3 -m unittest discover -s tests -p 'test_*.py'
