"""CPU-only reference validation or policy scoring; no model/runtime entry point."""
import argparse
import importlib.abc
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'triton', 'pypdfium2') or fullname == 'q0harness.backend_torch':
            raise RuntimeError('CPU protocol prohibits model/renderer imports: ' + fullname)


sys.meta_path.insert(0, NoModelImports())
from qualification.mapping_v2.protocol.common import load, write, verify_pins
from qualification.mapping_v2.protocol.contract import validate, validate_catalog
from qualification.mapping_v2.protocol.scoring import score_policy


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'score-policy'):
        command = sub.add_parser(name)
        for flag in ('expected', 'reference', 'policy', 'output'):
            command.add_argument('--' + flag, required=True)
        if name == 'score-policy':
            command.add_argument('--prediction', required=True)
            command.add_argument('--completion', default='completed')
    args = parser.parse_args(); verify_pins(); validate_catalog()
    inputs = [load(getattr(args, k)) for k in ('expected', 'reference', 'policy')]
    result = validate(*inputs) if args.command == 'validate' else score_policy(load(args.prediction), *inputs, args.completion)
    write(args.output, result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
