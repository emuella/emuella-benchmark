#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "${CI:-}" = true ]; then
    nextest_profile=root-ci
else
    nextest_profile=root
fi
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
python3 scripts/run-nextest.py "$nextest_profile" --all-targets
cargo test --doc
python3 -m unittest discover -s tests -p 'test_*.py'
