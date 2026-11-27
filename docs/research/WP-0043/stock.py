"""CPU JSON entries and separately gated stock runner entry."""
import argparse
import json
import sys
from capture import load_json


def main():
    parser=argparse.ArgumentParser()
    commands=parser.add_subparsers(dest="command",required=True)
    commands.add_parser("capture").add_argument("case")
    cli=commands.add_parser("score")
    cli.add_argument("evidence")
    cli.add_argument("contract")
    commands.add_parser("plan")
    commands.add_parser("run")
    commands.add_parser("score-native")
    args=parser.parse_args()
    if args.command=="capture":
        from analogue import capture_analogue
        result=capture_analogue(load_json(args.case))
    elif args.command=="score":
        from scorer import score
        result=score(load_json(args.evidence),load_json(args.contract))
    elif args.command=="score-native":
        from native_score import score_native
        result=score_native()
    elif args.command=="plan":
        from native import plan
        result=plan()
    else:
        from native import run
        result=run()
    print(json.dumps(result,allow_nan=False,separators=(",",":")))


if __name__=="__main__":
    main()
