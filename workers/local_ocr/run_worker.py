"""CLI entry point for the eLedgerCare production local OCR worker."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# F2-S1-01: Under CPython `-I` (isolated mode, which enables `-P` safe_path), the script's directory
# is omitted from sys.path when launched from an external attempt run directory. Prepend only the
# resolved worker root while keeping `-I` isolation (no cwd, PYTHONPATH, or user-site on sys.path).
WORKER_ROOT = Path(__file__).resolve().parent
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from local_ocr.worker import execute_request_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="eLedgerCare local OCR worker")
    parser.add_argument("--request", required=True, help="Absolute path to the attempt request.json file")
    args = parser.parse_args(argv)
    return execute_request_file(Path(args.request))


if __name__ == "__main__":
    sys.exit(main())
