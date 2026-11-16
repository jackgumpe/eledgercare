"""CLI entry point for the eLedgerCare production local OCR worker."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from local_ocr.worker import execute_request_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="eLedgerCare local OCR worker")
    parser.add_argument("--request", required=True, help="Absolute path to the attempt request.json file")
    args = parser.parse_args(argv)
    return execute_request_file(Path(args.request))


if __name__ == "__main__":
    sys.exit(main())
