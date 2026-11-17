"""Explicit CPU diagnostics/support or separately released finite execution."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

def main():
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='command',required=True)
    support=commands.add_parser('support-control')
    for flag in ('expected','reference','annotations','output'):support.add_argument('--'+flag,required=True)
    for name in ('execute','worker','score-run'):
        sub=commands.add_parser(name)
        for flag in ('authority','release-path','owner'):sub.add_argument('--'+flag,required=True)
        if name=='worker':
            sub.add_argument('--run-dir',required=True);sub.add_argument('--job',required=True)
        if name=='score-run':
            sub.add_argument('--run',required=True);sub.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='support-control':
        from qualification.coverage_v1.common import load_json,write
        from qualification.coverage_v1.contract import support_control
        write(args.output,support_control(load_json(args.expected),load_json(args.reference),load_json(args.annotations)));return 0
    if args.command=='score-run':
        from qualification.coverage_v1.scoring import score_run
        score_run(args.run,args.output,args.authority,args.release_path,args.owner);return 0
    from qualification.coverage_v1.runtime import execute,worker
    if args.command=='worker':return worker(args.authority,args.release_path,args.owner,args.run_dir,args.job)
    return execute(args.authority,args.release_path,args.owner)

if __name__=='__main__':raise SystemExit(main())
