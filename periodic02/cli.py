"""Offline candidate preparation and evidence checks. No scientific execution."""
import argparse
import json
import pathlib
from .io import read_json,freeze_json,digest
from .construct import from_prototype
from .admission import select_engine
from .quality import quality_from_observation,periodic_energy_comparison
from .decisions import freeze_initial_ai_decision,freeze_post_observation_decision


def main():
    p=argparse.ArgumentParser(description='QW P02 offline design/validation (not physics)')
    sub=p.add_subparsers(dest='op',required=True)
    a=sub.add_parser('prepare');a.add_argument('decision');a.add_argument('out')
    b=sub.add_parser('admit');b.add_argument('worldspec')
    c=sub.add_parser('quality');c.add_argument('observation')
    d=sub.add_parser('compare');d.add_argument('first');d.add_argument('second')
    e=sub.add_parser('followup');e.add_argument('prior');e.add_argument('proposal');e.add_argument('out')
    args=p.parse_args()
    if args.op=='prepare':
        sha,art=freeze_initial_ai_decision(read_json(args.decision),args.out)
        print(json.dumps({'status':art['status'],'file_sha256':sha,'candidates':art['candidate_count'],
                          'selected':art['selected_first_candidate_id'],'science_runs':0},indent=2))
    elif args.op=='admit':
        print(json.dumps(select_engine(read_json(args.worldspec)),indent=2))
    elif args.op=='quality':
        print(json.dumps(quality_from_observation(read_json(args.observation)),indent=2))
    elif args.op=='compare':
        print(json.dumps(periodic_energy_comparison(read_json(args.first),read_json(args.second)),indent=2))
    elif args.op=='followup':
        sha,art=freeze_post_observation_decision(read_json(args.prior),read_json(args.proposal),args.out)
        print(json.dumps({'status':art['status'],'file_sha256':sha,'science_runs':0},indent=2))


if __name__=='__main__':
    main()
